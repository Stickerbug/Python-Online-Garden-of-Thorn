"""Generic runtime support helpers shared by the Flask game engines.

Round 3 of the card-atom refactor moved the still-live generic mechanisms out of
the deleted ``void_dlc_runtime`` module into this neutrally named one; the pack
specific state machines that were left unreachable (the Void DLC action
dispatcher, the Cicada 3301 flow and their private helpers) were deleted. The
helpers here are pack agnostic:

* forced-target redirection (Eyeball)
* deferred damage + response queue (Horn / MagicCopperRod) and turn-start
  equipment choices (Fan / Schizo)
* effective status projections (toxic poison, poison coating, blind, mask)
* play gating (``can_play_extra``), copy-card preparation, hand-charge detection

Function/constant names and persisted ``custom_vars`` keys are unchanged, so
pauses stored by a running server keep resuming through the same code paths.
"""
from __future__ import annotations

import copy
import math
import random
import uuid
from typing import Any, Dict, Iterable, List, Optional

from cards import CARD_DEFS, CardInstance
from damage_types import (
    DAMAGE_TAG_BATTERY,
    DAMAGE_TAG_PHYSICAL,
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
    if state.get("kind") == "damage_queue":
        return _resume_damage_response(engine, state, value, cancelled)
    return {"success": True}


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
        if op == "card_prop_add_to_zone" and str(value.get("property") or "") == "charge_value":
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
