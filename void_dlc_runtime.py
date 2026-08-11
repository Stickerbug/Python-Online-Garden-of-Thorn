from __future__ import annotations

import copy
import math
import random
import uuid
from typing import Any, Dict, Iterable, List, Optional

from cards import CARD_DEFS, CardInstance, clamp_card_layer, clamp_card_power
from damage_types import (
    DAMAGE_TAG_BATTERY,
    DAMAGE_TAG_FIRE,
    DAMAGE_TAG_PHYSICAL,
    DAMAGE_TAG_POISON,
    DAMAGE_TYPE_MAGIC,
    DAMAGE_TYPE_PHYSICAL,
)


VOID_CARD_ID = "void:void"
NUT_IDS = {"Nut", "void:nut"}
MASK_IDS = {"Mask", "bio:mask"}
MAGIC_MASK_IDS = {"MagicMask", "bio:magic_mask"}
FAN_IDS = {"Fan", "void:fan"}
SCHIZO_IDS = {"Schizo", "void:schizo"}
MAGIC_COPPER_ROD_IDS = {"MagicCopperRod", "void:magic_copper_rod"}
HORN_IDS = {"Horn", "void:horn"}
DAMAGE_QUEUE_KEY = "void_dlc_deferred_damage_queue"
LIGHTNING_ROD_ABSORB_KEY = "void_dlc_lightning_rod_absorb_targets"
LIGHTNING_ROD_ABSORB_EVENTS_KEY = "void_dlc_lightning_rod_absorb_events"
CICADA_PENDING_BLIND_KEY = "void_dlc_cicada_pending_blind"

ILLUMINATI_STATUSES = (
    "poison",
    "fire",
    "toxic",
    "dodge",
    "sluggish",
    "overload",
    "foresight",
    "fracture",
    "stagnation",
    "blind",
    "heal_block",
    "weakness",
    "bleed",
    "attack_blocked",
    "attack_only",
    "magic_blocked",
    "skip_turn",
    "jungle:fragile",
    "jungle:shield",
    "jungle:turn_heal_turns",
    "jungle:turn_magic_turns",
    "jungle:toxic_poison",
    "ocean:blood_debt",
    "ocean:unable_counter",
    "arctic:frost",
    "hel:luck",
    "hel:blazing_fire",
    "bio:debt",
    "bio:extra_healing",
    "bio:shield_conversion",
)
CORE_ILLUMINATI_STATUS_COUNT = 17
TOXIC_POISON_ALIASES = ("jungle:toxic_poison", "toxic_poison", "剧毒")


def _valid_player(engine, player_id: Any) -> bool:
    try:
        player_id = int(player_id)
    except (TypeError, ValueError):
        return False
    return 0 <= player_id < len(getattr(engine, "players", []) or [])


def _card_is(engine, card: Optional[CardInstance], *ids: str) -> bool:
    checker = getattr(engine, "_card_is", None)
    if callable(checker):
        return bool(checker(card, *ids))
    return bool(card is not None and str(getattr(card, "def_id", "")) in set(ids))


def _equipment_is(engine, equipment, *ids: str) -> bool:
    checker = getattr(engine, "_equipment_is", None)
    if callable(checker):
        return bool(checker(equipment, *ids))
    return _card_is(engine, getattr(equipment, "card_instance", None), *ids)


def _active_equipment(engine, equipment) -> bool:
    checker = getattr(engine, "_non_stack_equipment_is_active", None)
    if callable(checker):
        return bool(checker(equipment))
    checker = getattr(engine, "_equipment_runtime_active", None)
    return bool(checker(equipment)) if callable(checker) else True


def _equipment_target(engine, equipment, owner_id: int) -> int:
    helper = getattr(engine, "_equipment_effect_target_id", None)
    if callable(helper):
        try:
            return int(helper(equipment, owner_id))
        except Exception:
            pass
    try:
        target_id = int(getattr(equipment, "effect_target", owner_id))
    except (TypeError, ValueError):
        target_id = owner_id
    return target_id if _valid_player(engine, target_id) else owner_id


def _choice_target(choice: Optional[dict], fallback: int = -1) -> int:
    if isinstance(choice, dict):
        for key in ("target_player", "target_player_id", "target_id"):
            try:
                if choice.get(key) is not None:
                    return int(choice.get(key))
            except (TypeError, ValueError):
                continue
    return fallback


def _action_targets(engine, player_id: int, card: Optional[CardInstance], choice, context) -> List[int]:
    context = context if isinstance(context, dict) else {}
    wide_targets = context.get("wide_strike_targets", context.get("target_players"))
    if isinstance(wide_targets, list):
        return list(dict.fromkeys(
            int(target_id) for target_id in wide_targets if _valid_player(engine, target_id)
        ))
    target_id = _choice_target(choice, -1)
    if target_id < 0:
        for key in ("target_player", "target_id"):
            try:
                target_id = int(context.get(key, -1))
            except (TypeError, ValueError):
                target_id = -1
            if target_id >= 0:
                break
    if target_id < 0 and card is not None and "wide_strike" in engine._effective_card_flags(card):
        return list(engine._wide_strike_target_ids(player_id, card))
    return [target_id] if _valid_player(engine, target_id) else []


def _target_selectable(engine, actor_id: int, target_id: int, *, allow_self: bool = True) -> bool:
    if not _valid_player(engine, actor_id) or not _valid_player(engine, target_id):
        return False
    checker = getattr(engine, "_target_can_be_selected", None)
    if callable(checker):
        try:
            return bool(checker(actor_id, target_id, allow_self=allow_self))
        except TypeError:
            return bool(checker(actor_id, target_id, allow_self))
    return engine.players[target_id].health > 0 and (allow_self or actor_id != target_id)


def _selectable_card(engine, card: Optional[CardInstance]) -> bool:
    if card is None:
        return False
    checker = getattr(engine, "_card_selectable_by_action", None)
    return bool(checker(card)) if callable(checker) else "sublime" not in card.flags


def _add_status(engine, target_id: int, status: str, amount: int = 1) -> None:
    if not _valid_player(engine, target_id) or int(amount or 0) == 0:
        return
    engine._atomic_status_add_named(
        target_id,
        None,
        {"target": target_id, "status": str(status), "amount": int(amount)},
        "",
        None,
        {"target_id": target_id},
    )


def _status_value(engine, target_id: int, status: str) -> int:
    if not _valid_player(engine, target_id):
        return 0
    return max(0, int(engine._get_status_count(target_id, status) or 0))


def _remove_status_layers(engine, target_id: int, status: str, amount: int) -> None:
    if not _valid_player(engine, target_id) or amount <= 0:
        return
    ps = engine.players[target_id]
    aliases = {
        "poison": "poison", "fire": "fire", "toxic": "toxic", "dodge": "dodge",
        "sluggish": "sluggish", "overload": "overload", "foresight": "foresight",
        "fracture": "fracture", "stagnation": "stagnation", "blind": "blind",
        "heal_block": "heal_block", "weakness": "weakness", "bleed": "bleed",
        "attack_blocked": "attack_blocked", "attack_only": "attack_only", "skip_turn": "skip_turn",
    }
    attr = aliases.get(status)
    if attr:
        setattr(ps, attr, max(0, int(getattr(ps, attr, 0) or 0) - amount))
        engine._normalize_status_value(ps, status)
        return
    current = _status_value(engine, target_id, status)
    setter = getattr(engine, "_set_custom_status_alias_group", None)
    if callable(setter):
        setter(target_id, status, (status,), max(0, current - amount))
    else:
        engine._set_custom_status_value(target_id, status, max(0, current - amount))


def _attack(engine, player_id: int, card: CardInstance, target_id: int, base: int,
            *, hits: int = 1, precision: Optional[bool] = None,
            split_power_for_fission: bool = True) -> int:
    if not _valid_player(engine, target_id):
        return 0
    amount = max(0, int(engine._modified_attack_damage(int(base), card)))
    total_hits = engine._card_total_hits(card, max(1, int(hits)))
    if precision is None:
        precision = "precision" in engine._effective_card_flags(card)
    original_power = clamp_card_power(getattr(card, "power_value", 0) or 0)
    if split_power_for_fission and original_power:
        fission_level = max(1, int(getattr(card, "fission_level", 1) or 1))
        card.power_value = int(math.ceil(original_power / fission_level))
    try:
        return int(engine.deal_attack_damage(
            target_id,
            amount,
            total_hits,
            is_precision=bool(precision),
            attacker_id=player_id,
            source_card=card,
        ) or 0)
    finally:
        card.power_value = original_power


def _direct_damage(engine, target_id: int, amount: int, source: str, source_id: int,
                   *, electric: bool = False, physical: bool = False,
                   damage_tag: Optional[str] = None) -> int:
    damage_type = DAMAGE_TYPE_PHYSICAL if physical else DAMAGE_TYPE_MAGIC
    resolved_tag = damage_tag or (
        DAMAGE_TAG_BATTERY if electric else (DAMAGE_TAG_PHYSICAL if physical else None)
    )
    return int(engine._deal_direct_damage(
        target_id,
        max(0, int(amount)),
        source,
        source_id,
        damage_type=damage_type,
        damage_tag=resolved_tag,
    ) or 0)


def _add_charge(card: CardInstance, amount: int) -> None:
    amount = max(0, int(amount or 0))
    if amount <= 0:
        return
    card.charge_value = max(0, int(getattr(card, "charge_value", 0) or 0)) + amount
    card.instance_flags.add("charge")


def _find_card(engine, instance_id: Any) -> Optional[CardInstance]:
    finder = getattr(engine, "_find_card_by_instance_id", None)
    if callable(finder):
        try:
            return finder(int(instance_id))
        except (TypeError, ValueError):
            return None
    return None


def _find_equipment(engine, instance_id: Any):
    finder = getattr(engine, "_find_equipment_by_card_instance_id", None)
    if not callable(finder):
        return None, None
    try:
        return finder(int(instance_id))
    except (TypeError, ValueError):
        return None, None


def _is_electric_damage(source: str, damage_tag: Optional[str]) -> bool:
    text = f"{source or ''} {damage_tag or ''}".casefold()
    return (
        str(damage_tag or "") == DAMAGE_TAG_BATTERY
        or "electric" in text
        or "battery" in text
        or "电伤" in text
        or "電傷" in text
        or "电击" in text
        or "電擊" in text
        or "电网" in text
        or "電網" in text
    )


def _damage_queue(engine) -> List[dict]:
    queue = engine.custom_vars.get(DAMAGE_QUEUE_KEY)
    if not isinstance(queue, list):
        queue = []
        engine.custom_vars[DAMAGE_QUEUE_KEY] = queue
    return queue


def _damage_response_options(engine, event: dict) -> tuple[int, List[dict]]:
    target_id = int(event.get("target_id", -1))
    attempted = {int(value) for value in event.get("attempted_responders", [])}
    by_responder: Dict[int, List[dict]] = {}
    try:
        source_id = int(event.get("source_id", -1))
    except (TypeError, ValueError):
        source_id = -1
    if (
        target_id not in attempted
        and _valid_player(engine, target_id)
        and engine.players[target_id].health > 0
        and (source_id < 0 or source_id == target_id)
    ):
        for hand_card in list(engine.players[target_id].hand):
            if (
                _card_is(engine, hand_card, *HORN_IDS)
                and engine._can_pay_counter_card(target_id, hand_card)
            ):
                by_responder.setdefault(target_id, []).append({
                    "kind": "horn",
                    "instance_id": int(hand_card.instance_id),
                    "card": hand_card.to_dict(),
                })
    if not by_responder:
        return -1, []
    responder_id = sorted(by_responder, key=lambda value: (value != target_id, value))[0]
    return responder_id, by_responder[responder_id]


def _apply_deferred_damage(engine, event: dict) -> int:
    depth = max(0, int(getattr(engine, "_void_dlc_damage_resume_depth", 0) or 0))
    game_over_depth = max(0, int(getattr(engine, "_game_over_defer_depth", 0) or 0))
    engine._void_dlc_damage_resume_depth = depth + 1
    engine._game_over_defer_depth = game_over_depth + 1
    try:
        if event.get("kind") == "attack":
            card_data = event.get("source_card")
            source_card = CardInstance.from_dict(card_data) if isinstance(card_data, dict) else None
            try:
                attacker_id = int(event.get("source_id", -1))
            except (TypeError, ValueError):
                attacker_id = -1
            return int(engine.deal_attack_damage(
                int(event.get("target_id", -1)),
                max(0, int(event.get("amount", 0) or 0)),
                max(1, int(event.get("hits", 1) or 1)),
                is_battery=bool(event.get("is_battery")),
                is_precision=bool(event.get("is_precision")),
                attacker_id=attacker_id,
                source_card=source_card,
                ignore_untargetable=bool(event.get("ignore_untargetable")),
            ) or 0)
        return int(engine._deal_direct_damage(
            int(event.get("target_id", -1)),
            max(0, int(event.get("amount", 0) or 0)),
            str(event.get("source") or ""),
            event.get("source_id"),
            damage_type=event.get("damage_type"),
            damage_tag=event.get("damage_tag"),
        ) or 0)
    finally:
        engine._void_dlc_damage_resume_depth = depth
        engine._game_over_defer_depth = game_over_depth


def _finish_damage_queue(engine) -> dict:
    engine.custom_vars.pop(DAMAGE_QUEUE_KEY, None)
    if max(0, int(getattr(engine, "_card_resolution_depth", 0) or 0)) == 0:
        alive_before = getattr(engine, "_deferred_card_alive_before", None)
        if alive_before is not None:
            engine._deferred_card_alive_before = None
            engine._card_resolution_target_snapshot = None
            depth = max(0, int(getattr(engine, "_game_over_defer_depth", 0) or 0))
            engine._game_over_defer_depth = depth + 1
            try:
                engine._finalize_deferred_card_deaths(alive_before)
            finally:
                engine._game_over_defer_depth = depth
    engine._check_game_over()
    return {"success": True}


def _run_damage_queue(engine) -> dict:
    queue = _damage_queue(engine)
    while queue:
        event = queue[0]
        responder_id, options = _damage_response_options(engine, event)
        if responder_id < 0 or not options:
            queue.pop(0)
            _apply_deferred_damage(engine, event)
            continue
        state = {
            "kind": "damage_queue",
            "player_id": responder_id,
            "event_id": str(event.get("id") or ""),
        }
        card_options = [{
            "value": "pass",
            "label_cn": "不响应",
            "label_en": "Do not respond",
        }]
        for option in options:
            card_options.append({
                "value": f"{option['kind']}:{option['instance_id']}",
                "label_cn": "使用此响应",
                "label_en": "Use this response",
                "card": option["card"],
            })
        control = {
            "id": "response",
            "type": "card_catalog_picker",
            "label_cn": "选择响应",
            "label_en": "Choose a response",
            "options": card_options,
        }
        return _pause(
            engine,
            state,
            player_id=responder_id,
            purpose="damage_response",
            component=_choice_component(
                title_cn="伤害响应",
                title_en="Damage Response",
                text_cn=f"即将受到{max(0, int(event.get('amount', 0) or 0))}点伤害",
                text_en=f"Incoming damage: {max(0, int(event.get('amount', 0) or 0))}",
                control=control,
                cancellable=True,
            ),
            control_id="response",
            timeout_ms=30000,
        )
    return _finish_damage_queue(engine)


def maybe_defer_direct_damage(engine, target_id: int, amount: int, source: str,
                              source_id: Any, damage_type: Any, damage_tag: Any) -> bool:
    if (
        max(0, int(getattr(engine, "_void_dlc_damage_resume_depth", 0) or 0)) > 0
        or not _valid_player(engine, target_id)
        or int(amount or 0) <= 0
    ):
        return False
    event = {
        "id": str(uuid.uuid4()),
        "kind": "direct",
        "target_id": int(target_id),
        "amount": max(0, int(amount or 0)),
        "source": str(source or ""),
        "source_id": source_id,
        "damage_type": damage_type,
        "damage_tag": damage_tag,
        "attempted_responders": [],
    }
    responder_id, options = _damage_response_options(engine, event)
    if responder_id < 0 or not options:
        return False
    queue = _damage_queue(engine)
    queue.append(event)
    if getattr(engine, "pending_v2_ui", None) is None:
        _run_damage_queue(engine)
    return True


def maybe_defer_attack_damage(engine, target_id: int, amount: int, hits: int,
                              attacker_id: int, source_card: Optional[CardInstance],
                              *, is_battery: bool, is_precision: bool,
                              ignore_untargetable: bool) -> bool:
    try:
        normalized_attacker_id = int(attacker_id)
    except (TypeError, ValueError):
        normalized_attacker_id = -1
    if (
        max(0, int(getattr(engine, "_void_dlc_damage_resume_depth", 0) or 0)) > 0
        or not _valid_player(engine, target_id)
        or int(amount or 0) <= 0
        or int(hits or 0) <= 0
        or (
            not is_battery
            and normalized_attacker_id >= 0
            and normalized_attacker_id != int(target_id)
        )
    ):
        return False
    event = {
        "id": str(uuid.uuid4()),
        "kind": "attack",
        "target_id": int(target_id),
        "amount": max(0, int(amount or 0)),
        "hits": max(1, int(hits or 1)),
        "source_id": normalized_attacker_id,
        "source_card": source_card.to_dict() if source_card is not None else None,
        "is_battery": bool(is_battery),
        "is_precision": bool(is_precision),
        "ignore_untargetable": bool(ignore_untargetable),
        "attempted_responders": [],
    }
    responder_id, options = _damage_response_options(engine, event)
    if responder_id < 0 or not options:
        return False
    queue = _damage_queue(engine)
    queue.append(event)
    if getattr(engine, "pending_v2_ui", None) is None:
        _run_damage_queue(engine)
    return True


def _remove_from_zones(engine, card: CardInstance) -> Optional[int]:
    owner_id, zone_name, _ = engine._find_card_location(card)
    if owner_id is None or zone_name is None:
        return owner_id
    zone = getattr(engine.players[owner_id], zone_name, None)
    if isinstance(zone, list) and card in zone:
        zone.remove(card)
    return owner_id


def _play_damage_targets(engine, player_id: int, card: CardInstance, choice, context,
                         base: int, *, status_after: Optional[Iterable[tuple]] = None) -> int:
    total = 0
    for target_id in _action_targets(engine, player_id, card, choice, context):
        dealt = _attack(engine, player_id, card, target_id, base)
        total += dealt
        for status, amount, require_hit in status_after or []:
            if not require_hit or dealt > 0:
                _add_status(engine, target_id, status, amount)
    return total


def _clear_all_statuses(engine, target_id: int) -> None:
    if not _valid_player(engine, target_id):
        return
    ps = engine.players[target_id]
    for attr in (
        "poison", "fire", "toxic", "dodge", "sluggish", "overload", "foresight",
        "fracture", "stagnation", "blind", "heal_block", "weakness", "bleed",
        "attack_blocked", "attack_only", "magic_blocked", "skip_turn",
    ):
        if hasattr(ps, attr):
            setattr(ps, attr, 0)
    ps.custom_statuses = {}
    normalizer = getattr(engine, "_normalize_statuses", None)
    if callable(normalizer):
        normalizer(target_id)


def _distribute_charge_to_hand(engine, target_id: int, total: int) -> int:
    if not _valid_player(engine, target_id):
        return 0
    hand = list(getattr(engine.players[target_id], "hand", []) or [])
    if not hand:
        return 0
    amount = int(math.ceil(max(0, int(total or 0)) / len(hand)))
    if amount <= 0:
        return 0
    for hand_card in hand:
        _add_charge(hand_card, amount)
    return amount


def consume_lightning_rod_absorb(engine, target_id: int, source_card: Optional[CardInstance], damage: int) -> bool:
    if damage <= 0 or not _valid_player(engine, target_id):
        return False
    card_key = str(getattr(source_card, "instance_id", "") or "") if source_card is not None else ""
    absorb_events = getattr(engine, "custom_vars", {}).get(LIGHTNING_ROD_ABSORB_EVENTS_KEY)
    if isinstance(absorb_events, dict):
        matched_key = None
        targets_map = {}
        for candidate_key in (card_key, "_any"):
            if not candidate_key:
                continue
            candidate_map = dict(absorb_events.get(candidate_key, {}) or {})
            if str(target_id) in candidate_map:
                matched_key = candidate_key
                targets_map = candidate_map
                break
        if matched_key is not None:
            targets_map.pop(str(target_id), None)
            if targets_map:
                absorb_events[matched_key] = targets_map
            else:
                absorb_events.pop(matched_key, None)
            engine.custom_vars[LIGHTNING_ROD_ABSORB_EVENTS_KEY] = absorb_events
            amount = _distribute_charge_to_hand(engine, target_id, damage)
            engine.log_msg(f"{engine.pn(target_id)}的铜棒吸收了{damage}点伤害，使每张手牌获得{amount}层电荷")
            return True
    if source_card is None:
        return False
    custom = getattr(source_card, "custom_vars", {}) or {}
    targets_map = dict(custom.get(LIGHTNING_ROD_ABSORB_KEY, {}) or {})
    if str(target_id) not in targets_map:
        return False
    targets_map.pop(str(target_id), None)
    custom[LIGHTNING_ROD_ABSORB_KEY] = targets_map
    source_card.custom_vars = custom
    amount = _distribute_charge_to_hand(engine, target_id, damage)
    engine.log_msg(f"{engine.pn(target_id)}的铜棒吸收了{damage}点伤害，使每张手牌获得{amount}层电荷")
    return True


def try_magic_copper_rod_absorb(engine, target_id: int, damage: int) -> bool:
    if damage <= 0 or not _valid_player(engine, target_id):
        return False
    for owner_id, owner in enumerate(getattr(engine, "players", []) or []):
        for equipment in list(getattr(owner, "equipment", []) or []):
            if (
                _active_equipment(engine, equipment)
                and _equipment_target(engine, equipment, owner_id) == target_id
                and _equipment_is(engine, equipment, *MAGIC_COPPER_ROD_IDS)
                and int(getattr(engine.players[owner_id], "magic", 0) or 0) >= 1
            ):
                engine._spend_resource(owner_id, "magic", 1, equipment.card_instance)
                amount = _distribute_charge_to_hand(engine, target_id, damage)
                engine.log_msg(
                    f"{engine.pn(owner_id)}的魔法铜棒消耗1M，吸收{engine.pn(target_id)}受到的{damage}点伤害，"
                    f"使其每张手牌获得{amount}层电荷"
                )
                return True
    return False


def _run_simple_action(engine, player_id: int, card: CardInstance, action: str,
                       params: dict, choice, context) -> bool:
    targets = _action_targets(engine, player_id, card, choice, context)
    if action == "bomb_attack":
        _play_damage_targets(engine, player_id, card, choice, context, int(params.get("damage", 6)),
                             status_after=(
                                 ("overload", 1, bool(params.get("require_hit"))),
                                 ("weakness", 1, bool(params.get("require_hit"))),
                             ))
    elif action == "fire_bomb_attack":
        status_name = "fire" if "fire" in params else "hel:blazing_fire"
        status_amount = int(params.get("fire", params.get("blaze", 3)) or 0)
        _play_damage_targets(engine, player_id, card, choice, context, int(params.get("damage", 16)),
                             status_after=((status_name, status_amount, bool(params.get("require_hit"))),))
    elif action == "magic_bomb_attack":
        _play_damage_targets(engine, player_id, card, choice, context, int(params.get("damage", 20)),
                             status_after=(("skip_turn", 1, False),))
    elif action == "pipe_bomb_attack":
        _play_damage_targets(engine, player_id, card, choice, context, int(params.get("damage", 16) or 16))
        if params.get("end_turn") and not getattr(engine, "game_over", False):
            end_turn = getattr(engine, "end_turn", None)
            if callable(end_turn):
                end_turn(player_id)
            else:
                engine._end_player_turn(player_id)
    elif action == "dvd_attack":
        _play_damage_targets(engine, player_id, card, choice, context, int(params.get("damage", 6)),
                             status_after=(("fire", 1, bool(params.get("require_hit"))),))
    elif action == "dvd_return":
        owner_id, zone_name, _ = engine._find_card_location(card)
        if owner_id == player_id and zone_name == "discard" and card in engine.players[player_id].discard:
            engine.players[player_id].discard.remove(card)
            engine.players[player_id].add_to_hand(card)
            engine.log_msg(f"{engine.pn(player_id)}的{card.name_cn}回到手中")
    elif action == "fan_play":
        for target_id in targets:
            _add_status(engine, target_id, "fire", 2)
            if not engine._is_status_immune(target_id) and engine.players[target_id].fire > 0:
                _direct_damage(engine, target_id, engine.players[target_id].fire, "灼烧", player_id, damage_tag=DAMAGE_TAG_FIRE)
                engine._decay_fire_after_turn_start(target_id)
            engine.players[target_id].gain_elixir(4)
            engine.log_msg(f"{engine.pn(target_id)}因扇子获得4E")
    elif action in ("fan_turn_start", "schizo_turn_start"):
        pass
    elif action == "seed_charge":
        _add_charge(card, int(params.get("amount", 1) or 1))
    elif action == "charge_hand":
        cancelled = set((getattr(card, "custom_vars", {}) or {}).pop("void_dlc_charge_cancelled_targets", []) or [])
        for target_id in targets:
            if target_id in cancelled:
                continue
            for hand_card in list(engine.players[target_id].hand):
                _add_charge(hand_card, int(params.get("amount", 1) or 1))
            if engine.players[target_id].hand:
                engine.log_msg(f"{engine.pn(target_id)}的所有手牌获得{int(params.get('amount', 1) or 1)}层电荷")
    elif action in ("copper_rod_response", "lightning_rod_response"):
        original = context.get("original_card") if isinstance(context, dict) else None
        if original is not None:
            card_key = str(getattr(original, "instance_id", "") or "")
            if card_key:
                absorb_events = engine.custom_vars.setdefault(LIGHTNING_ROD_ABSORB_EVENTS_KEY, {})
                if not isinstance(absorb_events, dict):
                    absorb_events = {}
                    engine.custom_vars[LIGHTNING_ROD_ABSORB_EVENTS_KEY] = absorb_events
                targets_map = dict(absorb_events.get(card_key, {}) or {})
                targets_map[str(player_id)] = max(0, int((context.get("incoming_damage") or {}).get("total", 0) or 0))
                absorb_events[card_key] = targets_map
            any_map = dict(engine.custom_vars.setdefault(LIGHTNING_ROD_ABSORB_EVENTS_KEY, {}).get("_any", {}) or {})
            any_map[str(player_id)] = max(0, int((context.get("incoming_damage") or {}).get("total", 0) or 0))
            engine.custom_vars[LIGHTNING_ROD_ABSORB_EVENTS_KEY]["_any"] = any_map
            custom = getattr(original, "custom_vars", {}) or {}
            targets_map = dict(custom.get(LIGHTNING_ROD_ABSORB_KEY, {}) or {})
            targets_map[str(player_id)] = max(0, int((context.get("incoming_damage") or {}).get("total", 0) or 0))
            custom[LIGHTNING_ROD_ABSORB_KEY] = targets_map
            original.custom_vars = custom
        engine.log_msg(f"{engine.pn(player_id)}的铜棒将吸收本次攻击牌伤害")
    elif action == "plasma_attack":
        amount = int(params.get("amount", 4) or 4)
        damage = int(params.get("damage", 4) or 4)
        electric = int(params.get("electric", 4) or 4)
        for target_id in targets:
            _add_status(engine, target_id, "poison", amount)
            _add_status(engine, target_id, "fire", amount)
            selectable = [item for item in engine.players[target_id].hand if _selectable_card(engine, item)]
            if selectable:
                _add_charge(random.choice(selectable), amount)
            _attack(engine, player_id, card, target_id, damage)
            _direct_damage(engine, target_id, electric, "等离子体电伤", player_id, electric=True)
    elif action == "apply_status":
        for target_id in targets:
            _add_status(engine, target_id, str(params.get("status", "")), int(params.get("amount", 1) or 1))
    elif action == "magic_slime_ball":
        for target_id in targets:
            _add_status(engine, target_id, "skip_turn", 1)
        _add_status(engine, player_id, "sluggish", 1)
    elif action == "illuminati_triangle":
        cleanup = engine.custom_vars.setdefault("void_dlc_illuminati_cleanup", [])
        if not isinstance(cleanup, list):
            cleanup = []
            engine.custom_vars["void_dlc_illuminati_cleanup"] = cleanup
        for target_id in targets:
            heal_amount = int(params.get("heal", 20) or 20)
            if heal_amount > 0:
                before = engine.players[target_id].health
                engine.players[target_id].heal(heal_amount)
                recovered = max(0, int(engine.players[target_id].health or 0) - int(before or 0))
                engine.log_msg(f"{engine.pn(target_id)}回复{recovered}H")
            for status in ILLUMINATI_STATUSES:
                _add_status(engine, target_id, status, 1)
            cleanup.append({"source_id": player_id, "target_id": target_id, "clear_all": True})
    elif action == "heated_thorn":
        dealt = _play_damage_targets(engine, player_id, card, choice, context, int(params.get("damage", 6)),
                                     status_after=(("hel:blazing_fire", 1, False),))
        custom = getattr(card, "custom_vars", {}) or {}
        if dealt > 0 and not custom.get("void_dlc_no_heated_thorn_spawn"):
            spawned = CardInstance(card.def_id)
            spawned.fission_level = clamp_card_layer(3)
            spawned.fission_count = 2
            spawned.instance_flags.add("wide_strike")
            spawned.instance_flags.add("self_target")
            spawned.custom_vars["void_dlc_no_heated_thorn_spawn"] = True
            engine._bio_queue_auto_play(player_id, spawned, {}, no_cost=True, source="heated_thorn")
    elif action == "comb_statuses":
        for target_id in targets:
            for status in ("hel:blazing_fire", "fire", "jungle:toxic_poison", "poison"):
                _add_status(engine, target_id, status, 1)
    elif action == "magic_nut_attack":
        spent = max(0, int(engine.players[player_id].elixir or 0))
        engine._spend_resource(player_id, "elixir", spent, card)
        _play_damage_targets(engine, player_id, card, choice, context,
                             int(params.get("base", 10) or 10) + spent * int(params.get("per_e", 5) or 5))
    elif action == "one_ring":
        for target_id in targets:
            _add_status(engine, target_id, "hel:blazing_fire", int(params.get("blaze", 2) or 2))
            _add_status(engine, target_id, "fire", int(params.get("fire", 1) or 1))
    elif action == "magic_stardust":
        for target_id in targets:
            raw_toxic = _status_value(engine, target_id, "jungle:toxic_poison")
            if raw_toxic <= 0:
                _add_status(engine, target_id, "jungle:toxic_poison", 1)
            toxic = effective_toxic_poison(engine, target_id)
            ps = engine.players[target_id]
            if ps.poison <= 0 and toxic > 0:
                ps.poison += toxic
            if ps.poison > 0 and not engine._is_status_immune(target_id):
                _direct_damage(
                    engine,
                    target_id,
                    ps.poison,
                    "中毒",
                    player_id,
                    damage_tag=DAMAGE_TAG_POISON,
                )
            engine._decay_poison_after_turn_start(target_id)
            engine._apply_toxic_poison_after_poison_settlement(target_id)
    elif action == "horn_response":
        for target_id in range(len(engine.players)):
            if engine._opposite_timer_side(player_id, target_id) and _target_selectable(engine, player_id, target_id, allow_self=False):
                _attack(engine, player_id, card, target_id, int(params.get("damage", 10) or 10))
    elif action == "blood_scythe":
        _play_damage_targets(engine, player_id, card, choice, context, int(params.get("target_damage", 40) or 40))
        _direct_damage(engine, player_id, int(params.get("self_damage", 4) or 4), "血镰刀", player_id, physical=True)
    elif action == "add_void_to_hand":
        def_id = engine._void_resolve_card_def_id(VOID_CARD_ID)
        if def_id in CARD_DEFS and engine._card_allowed(def_id):
            engine.players[player_id].add_to_hand(CardInstance(def_id))
    elif action == "magic_blood_scythe":
        _add_status(engine, player_id, "fire", 3)
        _add_status(engine, player_id, "arctic:frost", 3)
        _add_status(engine, player_id, "poison", 3)
        _play_damage_targets(engine, player_id, card, choice, context, int(params.get("damage", 50) or 50))
    elif action == "magic_blood_scythe_exile":
        selectable = [item for item in list(engine.players[player_id].hand) if _selectable_card(engine, item)]
        if not selectable:
            _add_status(engine, player_id, "bio:debt", 1)
        else:
            for selected in selectable[:2]:
                engine.players[player_id].hand.remove(selected)
                engine._put_card_in_exile(player_id, selected)
    elif action == "hexagram":
        for target_id in targets:
            _attack(engine, player_id, card, target_id, int(params.get("target_damage", 20) or 20))
            _add_status(engine, target_id, "fire", int(params.get("fire", 10) or 10))
        _direct_damage(engine, player_id, int(params.get("self_damage", 5) or 5), "六芒星", player_id, physical=True)
    else:
        return False
    return True


def _choice_component(*, title_cn: str, title_en: str, control: dict,
                      text_cn: str = "", text_en: str = "", cancellable: bool = False) -> dict:
    buttons = [{"id": "confirm", "text_cn": "确认", "text_en": "Confirm", "role": "confirm"}]
    if cancellable:
        buttons.append({"id": "cancel", "text_cn": "取消", "text_en": "Cancel", "role": "cancel"})
    return {
        "type": "modal",
        "title_cn": title_cn,
        "title_en": title_en,
        "text_cn": text_cn,
        "text_en": text_en,
        "controls": [control],
        "buttons": buttons,
        "style": {"accent": "void-dlc"},
    }


def _pause(engine, state: dict, *, player_id: int, purpose: str, component: dict,
           control_id: str, display_card_instance_id: Optional[int] = None,
           timeout_ms: int = 60000) -> dict:
    from mod_runtime_v2 import _sanitize_ui_component

    context = {"source_player": player_id, "target_player": player_id, "vars": {}}
    safe_component = _sanitize_ui_component(engine, context, component)
    state = copy.deepcopy(state)
    state["waiting"] = {"purpose": purpose, "control_id": control_id}
    pause = {
        "request_id": str(uuid.uuid4()),
        "component": safe_component,
        "target_player": player_id,
        "timeout_ms": max(0, int(timeout_ms)),
        "context": context,
        "resume_kind": "void_dlc",
        "resume_state": state,
    }
    engine._store_v2_ui_pause(pause, _find_card(engine, display_card_instance_id))
    return {"success": True, "needs_v2_ui": True}


def _select_control(control_id: str, options: List[dict], label_cn: str, label_en: str) -> dict:
    return {
        "id": control_id,
        "type": "select",
        "label_cn": label_cn,
        "label_en": label_en,
        "options": options,
    }


def _player_control(control_id: str, allowed: Iterable[int], label_cn: str, label_en: str) -> dict:
    return {
        "id": control_id,
        "type": "player_picker",
        "label_cn": label_cn,
        "label_en": label_en,
        "allowed_player_ids": [int(player_id) for player_id in allowed],
    }


def _card_control(control_id: str, owner_id: int, allowed: Iterable[int], *, multi: bool,
                  min_select: int = 0, max_select: int = 1,
                  label_cn: str = "选择牌", label_en: str = "Choose cards") -> dict:
    control = {
        "id": control_id,
        "type": "multi_card_picker" if multi else "card_picker",
        "label_cn": label_cn,
        "label_en": label_en,
        "target": int(owner_id),
        "zone": "hand",
        "allowed_instance_ids": [int(instance_id) for instance_id in allowed],
    }
    if multi:
        control["min_select"] = int(min_select)
        control["max_select"] = int(max_select)
    return control


def _catalog_control(control_id: str, cards: Iterable[CardInstance], label_cn: str, label_en: str) -> dict:
    return {
        "id": control_id,
        "type": "card_catalog_picker",
        "label_cn": label_cn,
        "label_en": label_en,
        "options": [
            {
                "value": str(card.instance_id),
                "label_cn": card.name_cn,
                "label_en": card.name_en,
                "card": card.to_dict(),
            }
            for card in cards
        ],
    }


def _finish_resume_handler(engine, state: dict) -> dict:
    handler_name = str(state.get("resume_handler") or "")
    player_id = int(state.get("turn_player_id", state.get("player_id", 0)) or 0)
    if handler_name:
        handler = getattr(engine, handler_name, None)
        if callable(handler):
            handler(player_id)
    return {"success": True}


def queue_turn_start_choices(engine, player_id: int, resume_handler: str) -> bool:
    if not _valid_player(engine, player_id):
        return False
    pending_blind = max(0, int((getattr(engine.players[player_id], "custom_vars", {}) or {}).pop(CICADA_PENDING_BLIND_KEY, 0) or 0))
    if pending_blind > 0:
        _add_status(engine, player_id, "blind", pending_blind)
        engine.log_msg(f"{engine.pn(player_id)}因蝉3301获得{pending_blind}层失明")
    entries = []
    for owner_id, owner in enumerate(engine.players):
        for equipment in list(getattr(owner, "equipment", []) or []):
            if not _active_equipment(engine, equipment):
                continue
            target_id = _equipment_target(engine, equipment, owner_id)
            if target_id != player_id:
                continue
            if _equipment_is(engine, equipment, *FAN_IDS):
                entries.append({
                    "type": "fan",
                    "owner_id": owner_id,
                    "target_id": target_id,
                    "equipment_instance_id": equipment.card_instance.instance_id,
                })
            elif _equipment_is(engine, equipment, *SCHIZO_IDS) and owner_id == player_id:
                entries.append({
                    "type": "schizo",
                    "owner_id": owner_id,
                    "target_id": target_id,
                    "equipment_instance_id": equipment.card_instance.instance_id,
                })
    if not entries:
        return False
    state = {
        "kind": "turn_start",
        "player_id": player_id,
        "turn_player_id": player_id,
        "resume_handler": str(resume_handler or ""),
        "entries": entries,
    }
    result = _run_turn_start_state(engine, state)
    return bool(isinstance(result, dict) and result.get("needs_v2_ui"))


def _run_turn_start_state(engine, state: dict) -> dict:
    entries = state.get("entries") if isinstance(state.get("entries"), list) else []
    while entries:
        entry = entries.pop(0)
        owner_id = int(entry.get("owner_id", -1))
        target_id = int(entry.get("target_id", -1))
        equipment_owner, equipment = _find_equipment(engine, entry.get("equipment_instance_id"))
        if (
            equipment is None
            or equipment_owner != owner_id
            or not _active_equipment(engine, equipment)
            or _equipment_target(engine, equipment, owner_id) != target_id
        ):
            continue
        if entry.get("type") == "fan":
            if engine.players[owner_id].elixir < 2 or engine.players[target_id].fire <= 0:
                continue
            state["active_entry"] = entry
            control = _select_control("activate", [
                {"value": "yes", "label_cn": "花费2E并移除1层灼烧", "label_en": "Spend 2E and remove 1 Burn"},
                {"value": "no", "label_cn": "不触发", "label_en": "Do not trigger"},
            ], "是否触发扇子？", "Trigger Fan?")
            return _pause(
                engine,
                state,
                player_id=owner_id,
                purpose="fan",
                component=_choice_component(title_cn="扇子", title_en="Fan", control=control),
                control_id="activate",
                display_card_instance_id=entry.get("equipment_instance_id"),
            )
        if entry.get("type") == "schizo":
            if engine.players[owner_id].magic < 2:
                continue
            allowed = [
                target for target in range(len(engine.players))
                if _target_selectable(engine, owner_id, target, allow_self=True)
            ]
            if not allowed:
                continue
            state["active_entry"] = entry
            control = _player_control("target", allowed, "选择展示手牌并受到伤害的目标", "Choose a target")
            return _pause(
                engine,
                state,
                player_id=owner_id,
                purpose="schizo",
                component=_choice_component(
                    title_cn="精神分裂症",
                    title_en="Schizo",
                    text_cn="花费2M，展示目标所有手牌并对其造成10D",
                    text_en="Spend 2M to reveal a target's hand and deal 10D.",
                    control=control,
                    cancellable=True,
                ),
                control_id="target",
                display_card_instance_id=entry.get("equipment_instance_id"),
            )
    return _finish_resume_handler(engine, state)


def _resume_turn_start(engine, state: dict, purpose: str, value: Any, cancelled: bool) -> dict:
    entry = state.pop("active_entry", {}) if isinstance(state.get("active_entry"), dict) else {}
    owner_id = int(entry.get("owner_id", -1))
    equipment_owner, equipment = _find_equipment(engine, entry.get("equipment_instance_id"))
    valid_equipment = (
        equipment is not None
        and equipment_owner == owner_id
        and _active_equipment(engine, equipment)
    )
    if purpose == "fan" and valid_equipment and not cancelled and str(value) == "yes":
        target_id = int(entry.get("target_id", -1))
        if _valid_player(engine, target_id) and engine.players[owner_id].elixir >= 2 and engine.players[target_id].fire > 0:
            engine._spend_resource(owner_id, "elixir", 2, equipment.card_instance)
            engine.players[target_id].fire = max(0, int(engine.players[target_id].fire) - 1)
            engine.log_msg(f"{engine.pn(owner_id)}的扇子消耗2E，使{engine.pn(target_id)}减少1层灼烧")
    elif purpose == "schizo" and valid_equipment and not cancelled:
        try:
            target_id = int(value)
        except (TypeError, ValueError):
            target_id = -1
        if (
            _target_selectable(engine, owner_id, target_id, allow_self=True)
            and engine.players[owner_id].magic >= 2
        ):
            engine._spend_resource(owner_id, "magic", 2, equipment.card_instance)
            for hand_card in engine.players[target_id].hand:
                if _selectable_card(engine, hand_card):
                    hand_card.instance_flags.add("revealed")
            if hasattr(engine, "_antennae_reveal") and owner_id < len(engine._antennae_reveal):
                engine._antennae_reveal[owner_id] = engine._visible_card_dicts(
                    engine.players[target_id].hand,
                    owner_id,
                    target_id,
                )
            if hasattr(engine, "_antennae_reveal_targets") and owner_id < len(engine._antennae_reveal_targets):
                engine._antennae_reveal_targets[owner_id] = target_id
            dealt = _direct_damage(engine, target_id, 10, "精神分裂症", owner_id, physical=True)
            engine.log_msg(f"{engine.pn(owner_id)}的精神分裂症展示{engine.pn(target_id)}的手牌并造成{dealt}D")
    return _run_turn_start_state(engine, state)


def start_cicada(engine, player_id: int, card: CardInstance) -> dict:
    for target_id in range(len(engine.players)):
        if _target_selectable(engine, player_id, target_id, allow_self=True):
            custom = getattr(engine.players[target_id], "custom_vars", {}) or {}
            custom[CICADA_PENDING_BLIND_KEY] = max(0, int(custom.get(CICADA_PENDING_BLIND_KEY, 0) or 0)) + 3
            engine.players[target_id].custom_vars = custom
    selectable = [item for item in engine.players[player_id].hand if _selectable_card(engine, item)]
    if len(selectable) < 2:
        engine.log_msg(f"{engine.pn(player_id)}没有2张可丢弃的其他手牌，蝉3301的后续效果未执行")
        return {"success": True}
    state = {
        "kind": "cicada",
        "player_id": player_id,
        "stage": "discard",
        "display_card_instance_id": int(card.instance_id),
    }
    return _run_cicada_state(engine, state)


def _cicada_mode_options(engine, player_id: int) -> List[dict]:
    options = []
    clear_targets = [target for target in range(len(engine.players)) if _target_selectable(engine, player_id, target, allow_self=True)]
    if clear_targets:
        options.append({"value": "clear", "label_cn": "放逐所有目标的手牌", "label_en": "Exile every target's hand"})
    if any(player.health <= 0 for player in engine.players):
        options.append({"value": "revive", "label_cn": "复活所有目标", "label_en": "Revive every target"})
    deck_cards = [
        card for owner_id, player in enumerate(engine.players)
        for card in player.deck if _selectable_card(engine, card)
    ]
    if deck_cards:
        options.append({"value": "reorder", "label_cn": "重排所有目标的抽牌堆并选牌", "label_en": "Reorder every target deck and choose cards"})
    return options


def _run_cicada_state(engine, state: dict) -> dict:
    player_id = int(state.get("player_id", 0))
    stage = str(state.get("stage") or "discard")
    display_id = state.get("display_card_instance_id")
    if stage == "discard":
        selectable = [item for item in engine.players[player_id].hand if _selectable_card(engine, item)]
        if len(selectable) < 2:
            return {"success": True}
        control = _card_control(
            "cards", player_id, [card.instance_id for card in selectable],
            multi=True, min_select=2, max_select=2,
            label_cn="丢弃2张其他手牌", label_en="Discard 2 other cards",
        )
        return _pause(
            engine, state, player_id=player_id, purpose="cicada_discard",
            component=_choice_component(title_cn="蝉3301", title_en="Cicada 3301", control=control),
            control_id="cards", display_card_instance_id=display_id,
        )
    if stage == "mode":
        options = _cicada_mode_options(engine, player_id)
        if not options:
            return {"success": True}
        control = _select_control("mode", options, "选择一种效果", "Choose an effect")
        return _pause(
            engine, state, player_id=player_id, purpose="cicada_mode",
            component=_choice_component(title_cn="蝉3301", title_en="Cicada 3301", control=control),
            control_id="mode", display_card_instance_id=display_id,
        )
    if stage == "reorder_pick":
        targets_to_pick = state.get("targets_to_pick") if isinstance(state.get("targets_to_pick"), list) else []
        while targets_to_pick:
            source_id = int(targets_to_pick[0])
            if not _valid_player(engine, source_id):
                targets_to_pick.pop(0)
                continue
            cards = [card for card in engine.players[source_id].deck if _selectable_card(engine, card)]
            if not cards:
                targets_to_pick.pop(0)
                continue
            state["active_source_id"] = source_id
            control = _catalog_control("card", cards, "选择1张牌加入手中", "Choose 1 card to add to your hand")
            return _pause(
                engine, state, player_id=player_id, purpose="cicada_reorder_pick",
                component=_choice_component(title_cn="蝉3301", title_en="Cicada 3301", control=control),
                control_id="card", display_card_instance_id=display_id,
            )
        return {"success": True}
    return {"success": True}


def _resume_cicada(engine, state: dict, purpose: str, value: Any, cancelled: bool) -> dict:
    player_id = int(state.get("player_id", 0))
    if purpose == "cicada_discard":
        selected_ids = value if isinstance(value, list) else []
        selected = []
        for raw_id in selected_ids:
            card = engine.players[player_id].find_hand_card(raw_id)
            if card is not None and _selectable_card(engine, card) and card not in selected:
                selected.append(card)
        if len(selected) != 2:
            state["stage"] = "discard"
            return _run_cicada_state(engine, state)
        for card in selected:
            engine.players[player_id].hand.remove(card)
            engine._discard_card(engine.players[player_id], card)
        engine.log_msg(f"{engine.pn(player_id)}因蝉3301丢弃2张牌")
        state["stage"] = "mode"
    elif purpose == "cicada_mode":
        mode = str(value or "")
        if mode == "clear":
            for target_id in range(len(engine.players)):
                if not _target_selectable(engine, player_id, target_id, allow_self=True):
                    continue
                exiled = 0
                for card in list(engine.players[target_id].hand):
                    if not _selectable_card(engine, card):
                        continue
                    engine.players[target_id].hand.remove(card)
                    engine._put_card_in_exile(target_id, card)
                    exiled += 1
                engine.log_msg(f"{engine.pn(target_id)}被蝉3301放逐{exiled}张手牌")
            return {"success": True}
        elif mode == "revive":
            for target_id, target in enumerate(engine.players):
                if target.health > 0:
                    continue
                target.health = max(1, int(math.ceil(max(1, target.max_health) * 0.05)))
                set_invincible = getattr(engine, "_set_invincible_until_next_own_turn_end", None)
                if callable(set_invincible):
                    set_invincible(target_id)
                engine.log_msg(f"{engine.pn(target_id)}被蝉3301复活至{target.health}H并获得1回合无敌")
            return {"success": True}
        elif mode == "reorder":
            for owner_id, player in enumerate(engine.players):
                random.shuffle(player.deck)
            state["targets_to_pick"] = [owner_id for owner_id, player in enumerate(engine.players) if player.deck]
            state["stage"] = "reorder_pick"
        else:
            return {"success": True}
    elif purpose == "cicada_reorder_pick":
        targets_to_pick = state.get("targets_to_pick") if isinstance(state.get("targets_to_pick"), list) else []
        source_id = int(state.pop("active_source_id", targets_to_pick[0] if targets_to_pick else -1))
        try:
            instance_id = int(value)
        except (TypeError, ValueError):
            instance_id = -1
        selected = _find_card(engine, instance_id)
        if selected is not None and _selectable_card(engine, selected):
            owner_id, zone_name, _ = engine._find_card_location(selected)
            if owner_id == source_id and zone_name == "deck":
                engine.players[owner_id].deck.remove(selected)
                engine.players[player_id].add_to_hand(selected)
                engine.log_msg(f"{engine.pn(player_id)}因蝉3301从{engine.pn(owner_id)}的抽牌堆获得1张牌")
        if targets_to_pick and targets_to_pick[0] == source_id:
            targets_to_pick.pop(0)
        state["stage"] = "reorder_pick"
    return _run_cicada_state(engine, state)


def _resume_damage_response(engine, state: dict, value: Any, cancelled: bool) -> dict:
    queue = _damage_queue(engine)
    if not queue:
        return _finish_damage_queue(engine)
    event = queue[0]
    if str(event.get("id") or "") != str(state.get("event_id") or ""):
        return _run_damage_queue(engine)
    responder_id = int(state.get("player_id", -1))
    selected = "pass" if cancelled else str(value or "pass")
    if selected.startswith("copper:"):
        try:
            instance_id = int(selected.split(":", 1)[1])
        except (TypeError, ValueError):
            instance_id = -1
        owner_id, equipment = _find_equipment(engine, instance_id)
        if (
            owner_id == responder_id
            and equipment is not None
            and _active_equipment(engine, equipment)
            and _equipment_is(engine, equipment, *MAGIC_COPPER_ROD_IDS)
            and engine.players[responder_id].magic >= 1
            and _equipment_target(engine, equipment, responder_id) == int(event.get("target_id", -1))
        ):
            engine._spend_resource(responder_id, "magic", 1, equipment.card_instance)
            target_id = int(event.get("target_id", -1))
            for hand_card in engine.players[target_id].hand:
                current = max(0, int(getattr(hand_card, "charge_value", 0) or 0))
                if current > 0:
                    hand_card.charge_value = current - 1
                    if hand_card.charge_value <= 0:
                        hand_card.instance_flags.discard("charge")
            remaining_hits = 0
            if event.get("kind") == "attack":
                remaining_hits = max(0, int(event.get("hits", 1) or 1) - 1)
            if remaining_hits > 0:
                event["hits"] = remaining_hits
                event["attempted_responders"] = []
            else:
                queue.pop(0)
            engine.log_msg(
                f"{engine.pn(responder_id)}的魔法铜棒消耗1M，吸收本次电伤并使"
                f"{engine.pn(target_id)}所有手牌的电荷减少1层"
            )
            return _run_damage_queue(engine)
    elif selected.startswith("horn:"):
        try:
            instance_id = int(selected.split(":", 1)[1])
        except (TypeError, ValueError):
            instance_id = -1
        horn = engine.players[responder_id].find_hand_card(instance_id) if _valid_player(engine, responder_id) else None
        if horn is not None and _card_is(engine, horn, *HORN_IDS) and engine._can_pay_counter_card(responder_id, horn):
            engine._spend_resource(responder_id, "elixir", max(0, int(horn.cost_e or 0)), horn)
            engine._spend_resource(responder_id, "magic", max(0, int(horn.cost_m or 0)), horn)
            removed = engine.players[responder_id].remove_hand_card(instance_id)
            if removed is not None:
                engine.log_msg(f"{engine.pn(responder_id)}使用{removed.name_cn}{engine._card_log_marker(removed)}进行响应！")
                source_card_data = event.get("source_card")
                original_card = (
                    CardInstance.from_dict(source_card_data)
                    if isinstance(source_card_data, dict)
                    else CardInstance(VOID_CARD_ID if VOID_CARD_ID in CARD_DEFS else removed.def_id)
                )
                depth = max(0, int(getattr(engine, "_game_over_defer_depth", 0) or 0))
                engine._game_over_defer_depth = depth + 1
                try:
                    engine._execute_counter_effect(
                        responder_id,
                        removed,
                        original_card,
                        event.get("source_id"),
                        {
                            "total": max(0, int(event.get("amount", 0) or 0)),
                            "parts": [max(0, int(event.get("amount", 0) or 0))],
                        },
                    )
                    queue.pop(0)
                    _apply_deferred_damage(engine, event)
                finally:
                    engine._game_over_defer_depth = depth
                return _run_damage_queue(engine)
    attempted = event.setdefault("attempted_responders", [])
    if responder_id not in attempted:
        attempted.append(responder_id)
    return _run_damage_queue(engine)


def resume_void_dlc_actions(engine, state: dict, clean: dict, *, cancelled: bool = False) -> dict:
    state = copy.deepcopy(state or {})
    waiting = state.pop("waiting", {}) if isinstance(state.get("waiting"), dict) else {}
    purpose = str(waiting.get("purpose") or "")
    control_id = str(waiting.get("control_id") or "choice")
    values = clean.get("values") if isinstance(clean.get("values"), dict) else {}
    value = values.get(control_id)
    if state.get("kind") == "turn_start":
        return _resume_turn_start(engine, state, purpose, value, cancelled)
    if state.get("kind") == "cicada":
        return _resume_cicada(engine, state, purpose, value, cancelled)
    if state.get("kind") == "damage_queue":
        return _resume_damage_response(engine, state, value, cancelled)
    return {"success": True}


def run_action(engine, player_id: int, card: CardInstance, params: dict,
               choice: Optional[dict], context: Optional[dict]):
    action = str(params.get("action") or "")
    if action == "cicada_3301":
        return start_cicada(engine, player_id, card)
    return _run_simple_action(engine, player_id, card, action, params, choice, context)


def cleanup_turn_end(engine, player_id: int) -> None:
    cleanup = engine.custom_vars.get("void_dlc_illuminati_cleanup")
    if not isinstance(cleanup, list):
        return
    remaining = []
    for entry in cleanup:
        if not isinstance(entry, dict) or int(entry.get("source_id", -1)) != player_id:
            remaining.append(entry)
            continue
        if entry.get("clear_all"):
            _clear_all_statuses(engine, int(entry.get("target_id", -1)))
        else:
            _remove_status_layers(
                engine,
                int(entry.get("target_id", -1)),
                str(entry.get("status") or ""),
                max(0, int(entry.get("amount", 0) or 0)),
            )
    if remaining:
        engine.custom_vars["void_dlc_illuminati_cleanup"] = remaining
    else:
        engine.custom_vars.pop("void_dlc_illuminati_cleanup", None)


def refresh_nut_costs(engine) -> None:
    # Nut no longer has dynamic deck-count cost. Clear leftovers from old saves.
    for player in getattr(engine, "players", []) or []:
        for card in [
            card
            for zone_name in ("hand", "deck", "discard", "exile")
            for card in list(getattr(player, zone_name, []) or [])
            if _card_is(engine, card, *NUT_IDS)
        ]:
            if (getattr(card, "custom_vars", {}) or {}).pop("void_dlc_nut_dynamic_cost", None) is not None:
                card.cost_e_override = None


def can_play_extra(engine, player_id: int, card: CardInstance) -> tuple[bool, str]:
    refresh_nut_costs(engine)
    if _card_is(engine, card, "Cicada3301", "void:cicada_3301"):
        selectable = [
            item for item in engine.players[player_id].hand
            if item is not card and _selectable_card(engine, item)
        ]
        if len(selectable) < 2:
            return False, "至少需要2张可丢弃的其他手牌"
    if _card_is(engine, card, "PipeBomb", "factory:pipe_bomb"):
        if len(getattr(engine.players[player_id], "hand", []) or []) % 2 == 0:
            return False, "手牌数量为奇数时才可使用"
    if _card_is(engine, card, "Nut", "void:nut"):
        hand = list(getattr(engine.players[player_id], "hand", []) or [])
        if not any(other is not card and _card_is(engine, other, "Nut", "void:nut") for other in hand):
            return False, "手牌中需要有另一张坚果"
    if _card_is(engine, card, "MagicNut", "void:magic_nut"):
        names = []
        for zone_name in ("hand", "deck", "discard", "exile"):
            for item in list(getattr(engine.players[player_id], zone_name, []) or []):
                if item is card:
                    continue
                names.append(str(getattr(item, "name_cn", "") or getattr(item, "def_id", "")))
        if len(names) != len(set(names)):
            return False, "卡组中所有牌互不相同时才可使用"
    return True, ""


def prepare_copy_card(parent: CardInstance, copy_card: CardInstance) -> None:
    if _card_is_fallback(parent, "MagicSlimeBall", "void:magic_slime_ball"):
        copy_card.magic_swift_value = max(0, int(getattr(copy_card, "magic_swift_value", 0) or 0)) + 2
        copy_card.instance_flags.add("magic_swift")


def _card_is_fallback(card: Optional[CardInstance], *ids: str) -> bool:
    if card is None:
        return False
    values = {str(getattr(card, "def_id", ""))}
    resource = getattr(getattr(card, "card_def", None), "v2_resource", {}) or {}
    values.update(str(resource.get(key, "")) for key in ("id", "legacy_id", "runtime_id"))
    return bool(values & set(ids))


def mask_reduction(engine, player_id: int, *, magic_only: bool = False) -> int:
    if not _valid_player(engine, player_id):
        return 0
    count = 0
    for owner_id, owner in enumerate(engine.players):
        for equipment in list(getattr(owner, "equipment", []) or []):
            if not _active_equipment(engine, equipment):
                continue
            if _equipment_target(engine, equipment, owner_id) != player_id:
                continue
            if _equipment_is(engine, equipment, *MAGIC_MASK_IDS):
                count += 1
            elif not magic_only and _equipment_is(engine, equipment, *MASK_IDS):
                count += 1
    return count


def _has_equipment_targeting(engine, player_id: int, ids: Iterable[str]) -> bool:
    wanted = set(ids)
    if not _valid_player(engine, player_id):
        return False
    for owner_id, owner in enumerate(getattr(engine, "players", []) or []):
        for equipment in list(getattr(owner, "equipment", []) or []):
            if (
                _active_equipment(engine, equipment)
                and _equipment_target(engine, equipment, owner_id) == player_id
                and _equipment_is(engine, equipment, *wanted)
            ):
                return True
    return False


def blocks_special_effect_damage(engine, player_id: int) -> bool:
    return _has_equipment_targeting(engine, player_id, MASK_IDS) or _has_equipment_targeting(engine, player_id, MAGIC_MASK_IDS)


def blocks_special_effect_interference(engine, player_id: int) -> bool:
    return _has_equipment_targeting(engine, player_id, MAGIC_MASK_IDS)


def effective_toxic_poison(engine, player_id: int) -> int:
    raw = engine._custom_status_value(player_id, "jungle:toxic_poison", "toxic_poison", "剧毒")
    return max(0, int(raw))


def effective_poison_coating(engine, player_id: int) -> int:
    if not _valid_player(engine, player_id):
        return 0
    return max(0, int(engine.players[player_id].toxic or 0))


def effective_blind(engine, player_id: int) -> int:
    if not _valid_player(engine, player_id):
        return 0
    return max(0, int(engine.players[player_id].blind or 0))


def project_effective_mask_statuses(engine, player_id: int, payload: dict) -> dict:
    """Mask no longer changes visible status layers."""
    return payload


def card_applies_hand_charge(card: Optional[CardInstance]) -> bool:
    if card is None:
        return False
    events = getattr(getattr(card, "card_def", None), "v2_events", {}) or {}
    play = events.get("on_play") if isinstance(events, dict) else None
    steps = play.get("steps", []) if isinstance(play, dict) else play

    def walk(value) -> bool:
        if isinstance(value, list):
            return any(walk(item) for item in value)
        if not isinstance(value, dict):
            return False
        op = str(value.get("op") or value.get("type") or "")
        if op == "void_dlc_action" and str(value.get("action") or "") == "charge_hand":
            return True
        if op in ("ocean_add_charge_to_hand", "bio_add_charge_to_cards"):
            return True
        return any(walk(value.get(key)) for key in ("steps", "body", "then", "else", "effects"))

    return walk(steps)


def forced_random_target(engine, actor_id: int, candidates: Iterable[int], chosen: int = -1) -> int:
    candidate_ids = [int(target_id) for target_id in candidates if _valid_player(engine, target_id)]
    forced_targets: List[int] = []
    for owner_id, owner in enumerate(engine.players):
        for equipment in list(getattr(owner, "equipment", []) or []):
            if not _active_equipment(engine, equipment) or not _equipment_is(engine, equipment, "Eyeball", "void:eyeball"):
                continue
            forced = _equipment_target(engine, equipment, owner_id)
            if forced in candidate_ids and forced not in forced_targets:
                forced_targets.append(forced)
    if forced_targets:
        return random.choice(forced_targets)
    return chosen if chosen in candidate_ids else (random.choice(candidate_ids) if candidate_ids else -1)


def forced_choice_target(engine, actor_id: int, card: Optional[CardInstance], chosen: int = -1) -> Optional[int]:
    if card is None or not _valid_player(engine, actor_id):
        return None
    try:
        flags = engine._effective_card_flags(card)
    except Exception:
        flags = set(getattr(card, "flags", set()) or set())
    if "wide_strike" in flags or getattr(card, "card_type", "") == "guard":
        return None
    if getattr(engine, "_card_is_self_only", lambda value: False)(card):
        return None
    owner_targets = []
    for owner_id, owner in enumerate(getattr(engine, "players", []) or []):
        for equipment in list(getattr(owner, "equipment", []) or []):
            if (
                _active_equipment(engine, equipment)
                and _equipment_is(engine, equipment, "Eyeball", "void:eyeball")
                and _equipment_target(engine, equipment, owner_id) == actor_id
                and _target_selectable(engine, actor_id, owner_id, allow_self=True)
            ):
                owner_targets.append(owner_id)
    if not owner_targets:
        return None
    if chosen in owner_targets:
        return int(chosen)
    return int(owner_targets[0])
