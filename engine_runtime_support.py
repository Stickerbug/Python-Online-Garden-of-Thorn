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
* card level play gates (``play_requires``), copy-card preparation and
  hand-charge detection

Rounds 3-4 moved these helpers here without renaming them, and the persisted
``custom_vars`` keys are unchanged, so pauses stored by a running server keep
resuming through the same code paths.

Round 5 replaced the per-card id constant sets with **data marks**: the packs
declare ``mark:<card id>`` inside the card ``flags`` array and the helpers below
ask ``engine._card_has_mark`` instead of comparing card names.

Round 6a removed the remaining hard coded card names from these mechanisms.  The
packs now own the mechanism *parameters*, the helpers below only resolve them:

* damage queue responses are declared by the hand card's ``response_trigger``
  (``self_or_sourceless_damage``) plus its ``on_response`` steps, and the card's
  ``negates_damage`` flag says whether the responded hit is cancelled;
* incoming damage absorption is declared by a passive ``on_damage_absorb``
  block on the equipment card (scope / cost / charge spread / log);
* the Eyeball style target restriction is declared by a passive
  ``on_target_restrict`` block (``from`` / ``to`` player selectors).

Round 6b generalized the last four mechanism families the same way:

* turn start equipment choices are declared by a passive
  ``on_turn_start_choice`` block (UI control + cost + steps), the queue below
  only schedules / pauses / resumes them;
* dynamic cost refreshes are declared by ``on_cost_refresh`` and extra play
  gates by the card's ``play_requires`` rules (``filter``/``min``,
  ``count_parity``, ``unique_names``);
* exiled copies are prepared by the parent card's ``on_create_copy`` steps;
* effective status projections resolve the ``on_effective_status``
  declarations of the cards that own the status (``sources``/``combine``/
  ``visible``) through :func:`effective_status_value`;
* "does this card charge the hand" is the ``applies_hand_charge`` flag instead
  of a scan for charge-adding step ops.

Round 10 finished the sweep: the last card-name branches that the *engine*
still owned are gone.  Card data is authoritative there too (``property_caps``
resets, the ``blocks_cheap_attacks`` / ``absorb_damage_with_power`` /
``dna_turn_transform`` / ``skip_legacy_snowball_replay`` flags, the
``engine_effect`` ritual selector and ``request_target.alive_only``), and the
``BUILTIN_*`` tables below keep three situations working that never load the
shipped ``mod.json``: synthetic ``CardDef`` objects created by unit tests,
legacy saves/replays written before the declaration existed, and third party
packs that copied a card id without the new declaration.  Every entry is
registered with reason / impact / revisit condition in
``docs/引擎原子与数据步骤清单.md`` §13.1.
"""
from __future__ import annotations

import copy
import contextlib
import math
import random
import uuid
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Tuple

from cards import CARD_DEFS, CardInstance, normalize_card_flags


VOID_CARD_ID = "void:void"
DAMAGE_QUEUE_KEY = "void_dlc_deferred_damage_queue"

# Data declarations (card ``events`` blocks) that these helpers resolve.  They
# are plain data: the engine never matches the card id itself.
DAMAGE_ABSORB_EVENT = "on_damage_absorb"
TARGET_RESTRICT_EVENT = "on_target_restrict"
TURN_START_CHOICE_EVENT = "on_turn_start_choice"
COST_REFRESH_EVENT = "on_cost_refresh"
COPY_EVENT = "on_create_copy"
STATUS_PROJECTION_EVENT = "on_effective_status"
ELIXIR_RECOVERY_AURA_EVENT = "on_elixir_recovery"
PLAY_SUMMARY_EVENT = "on_play_summary"
EQUIPMENT_PROJECTION_EVENT = "on_equipment_projection"

# Card flag that declares "playing this card puts charge on hand cards" (the
# Copper Rod may respond to such a play).  Round 6b replaced the scan for
# charge-adding step ops with this data flag.
HAND_CHARGE_FLAG = "applies_hand_charge"

# Shield flags: an equipment attached to a player declares which special-effect
# protections it grants.  Round 8 replaced the CardName tests in
# ``blocks_special_effect_damage`` / ``blocks_special_effect_interference`` with
# these data flags (the mask / magic mask declare them in their card data).
SPECIAL_DAMAGE_SHIELD_FLAG = "blocks_special_effect_damage"
SPECIAL_INTERFERENCE_SHIELD_FLAG = "blocks_special_effect_interference"

# Resource aliases accepted inside a declaration ``cost`` block.
_RESOURCE_COST_KEYS = (
    ("e", "elixir"), ("elixir", "elixir"), ("cost_e", "elixir"),
    ("m", "magic"), ("magic", "magic"), ("cost_m", "magic"),
)

# Built-in fallbacks for the effective status projections.  A pack that owns a
# status may declare its own ``events.on_effective_status`` block; these tables
# keep the historical wording working for data that does not (yet) declare it.
_DEFAULT_STATUS_PROJECTIONS = {
    "blind": [{"player_status": "blind"}],
    "poison_coating": [{"player_status": "toxic"}],
    "toxic_poison": [{"custom_status": ["jungle:toxic_poison", "toxic_poison", "剧毒"]}],
}

# ``response_trigger`` values that may answer a *queued* damage event, mapped to
# the damage shapes each one covers.  ``self_or_sourceless_damage`` is the Horn
# wording: damage without a source, or damage whose source is the victim.
DAMAGE_QUEUE_RESPONSE_TRIGGERS = {
    "self_or_sourceless_damage": "sourceless_or_self",
}

# Option id prefix used by the damage queue's response picker.  Legacy saves
# rendered by older builds used ``horn:``; the resume path still accepts it.
DAMAGE_RESPONSE_KIND = "response"

# ---------------------------------------------------------------------------
# Round 10: built-in fallback table (引擎内建回落表, B 类)
# ---------------------------------------------------------------------------
# The tables hold *legacy identifiers only*; no branch logic lives here.  The
# engine asks for a mechanism key (``blocks_cheap_attacks``) and this module
# answers which historical marks/ids still stand for it when the card data
# cannot be read.  Diagnostics: docs §13.1.

# mechanism key -> marks a pre-Round-10 card definition may carry instead of
# the declarative flag of the same name.
BUILTIN_LEGACY_MARKS: Dict[str, Tuple[str, ...]] = {
    "blocks_cheap_attacks": ("Plank", "jungle:plank"),
    "absorb_damage_with_power": ("jurassic:amber",),
    "dna_turn_transform": ("bio:dna",),
    "skip_legacy_snowball_replay": ("arctic:snowball",),
    "legacy_yggdrasil_ritual": ("vanilla:yggdrasil",),
    "dead_target_play": ("Yggdrasil", "vanilla:yggdrasil"),
}

# slot -> runtime def_id used when a legacy record carries no card payload.
BUILTIN_LEGACY_DEF_IDS: Dict[str, str] = {"snowball": "Snowball"}

# runtime def_id -> property caps for definitions without a data resource.
BUILTIN_PROPERTY_CAPS: Dict[str, Dict[str, int]] = {
    "Tomato": {"held_turns": 6, "bonus_damage": 18, "power_value": 18},
}

# runtime def_id -> properties zeroed when the card leaves play.
BUILTIN_RESET_PROPERTIES: Dict[str, Tuple[str, ...]] = {
    "Tomato": ("bonus_damage", "held_turns"),
}

# ``engine_effect`` value declared by the card data -> engine handler method.
BUILTIN_ENGINE_EFFECTS: Dict[str, str] = {"yggdrasil": "_effect_yggdrasil"}

# Only consulted when the card declares no ``play_requires`` at all:
# (mark, engine checker method, refusal message).
BUILTIN_PLAY_REQUIREMENT_FALLBACKS: Tuple[Tuple[str, str, str], ...] = (
    ("ocean:sapphire", "_ocean_sapphire_selectable_attacks", "手中没有可选择的攻击牌"),
    ("arctic:ruby", "_arctic_ruby_selectable_attacks", "手中没有可支付消耗的攻击牌"),
)


def declared_card_value(card_or_def: Any, key: str, default: Any = None) -> Any:
    """Raw top level key of the card's data resource (``mod.json``)."""
    card_def = getattr(card_or_def, "card_def", card_or_def)
    resource = getattr(card_def, "v2_resource", None)
    if isinstance(resource, dict) and key in resource:
        return resource.get(key)
    value = getattr(card_def, key, None)
    return default if value is None else value


def card_runtime_id(card_or_def: Any) -> str:
    """Runtime ``def_id`` of a card instance / definition (legacy id)."""
    if card_or_def is None:
        return ""
    runtime_id = str(getattr(card_or_def, "def_id", "") or "")
    if runtime_id:
        return runtime_id
    card_def = getattr(card_or_def, "card_def", card_or_def)
    return str(getattr(card_def, "id", "") or "")


def builtin_legacy_marks(key: str) -> Tuple[str, ...]:
    """Marks that stood for the mechanism ``key`` before the data flag existed."""
    return tuple(BUILTIN_LEGACY_MARKS.get(str(key), ()))


def builtin_legacy_def_id(key: str, default: str = "") -> str:
    """Fallback runtime def_id for a legacy record without a card payload."""
    value = BUILTIN_LEGACY_DEF_IDS.get(str(key), default)
    return str(value or default or "")


def card_property_caps(card_or_def: Any) -> Dict[str, int]:
    """``property_caps`` declared by the card data, else the built-in fallback."""
    caps: Dict[str, int] = {}
    declared = declared_card_value(card_or_def, "property_caps")
    if isinstance(declared, dict):
        for prop, value in declared.items():
            try:
                caps[str(prop)] = int(value)
            except (TypeError, ValueError):
                continue
    if caps:
        return caps
    fallback = BUILTIN_PROPERTY_CAPS.get(card_runtime_id(card_or_def))
    if not fallback:
        return {}
    return {str(prop): int(value) for prop, value in fallback.items()}


def card_reset_properties(card_or_def: Any) -> Tuple[str, ...]:
    """Properties zeroed when the card leaves play (data, else built-in table)."""
    declared = declared_card_value(card_or_def, "reset_properties")
    if isinstance(declared, (list, tuple)):
        names = tuple(str(item) for item in declared if str(item))
        if names:
            return names
    return tuple(BUILTIN_RESET_PROPERTIES.get(card_runtime_id(card_or_def), ()))


def engine_effect_handler(engine: Any, card_or_def: Any) -> str:
    """Handler method for the card's declared ``engine_effect`` ritual."""
    name = str(declared_card_value(card_or_def, "engine_effect", "") or "").strip()
    handler = BUILTIN_ENGINE_EFFECTS.get(name, "")
    if handler:
        return handler
    checker = getattr(engine, "_card_has_mark", None)
    if not callable(checker):
        return ""
    for mark in builtin_legacy_marks("legacy_yggdrasil_ritual"):
        if checker(card_or_def, mark):
            return BUILTIN_ENGINE_EFFECTS["yggdrasil"]
    return ""


def _valid_player(engine, player_id: Any) -> bool:
    try:
        player_id = int(player_id)
    except (TypeError, ValueError):
        return False
    return 0 <= player_id < len(getattr(engine, "players", []) or [])


def _mark_flag(mark: Any) -> str:
    """Normalize a mark name to the ``mark:<name>`` flag stored in card data."""
    text = str(mark or "").strip().lower()
    if not text:
        return ""
    return text if text.startswith("mark:") else "mark:" + text


def _card_has_mark(engine, card: Optional[CardInstance], mark: str) -> bool:
    """True when the card declares ``mark:<name>`` in its flags."""
    checker = getattr(engine, "_card_has_mark", None)
    if callable(checker):
        return bool(checker(card, mark))
    wanted = _mark_flag(mark)
    if not wanted or card is None:
        return False
    return wanted in normalize_card_flags(getattr(card, "flags", set()) or set())


def _equipment_has_mark(engine, equipment, mark: str) -> bool:
    """True when the equipped card declares ``mark:<name>`` in its flags."""
    checker = getattr(engine, "_equipment_has_mark", None)
    if callable(checker):
        return bool(checker(equipment, mark))
    return _card_has_mark(engine, getattr(equipment, "card_instance", None), mark)


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


def _damage_event_matches_response_trigger(event: dict, trigger: Any) -> bool:
    """Does the queued damage *event* match the ``response_trigger`` wording?

    ``response_trigger`` is card data.  Cards that answer the deferred damage
    queue declare the damage shape they cover here; the engine keeps the
    vocabulary (see :data:`DAMAGE_QUEUE_RESPONSE_TRIGGERS`).
    """
    shape = DAMAGE_QUEUE_RESPONSE_TRIGGERS.get(str(trigger or "").strip().lower())
    if not shape:
        return False
    try:
        target_id = int(event.get("target_id", -1))
    except (TypeError, ValueError):
        target_id = -1
    try:
        source_id = int(event.get("source_id", -1))
    except (TypeError, ValueError):
        source_id = -1
    if shape == "sourceless_or_self":
        return source_id < 0 or source_id == target_id
    return False


def _damage_response_negates(card: Optional[CardInstance]) -> bool:
    """Does the responding card cancel the queued damage?

    The card's ``on_response`` block may declare ``negates_damage``; the Horn
    wording ("不使所响应伤害失效") leaves it at the default ``False`` so the
    answered hit still lands after the response resolves.
    """
    events = getattr(getattr(card, "card_def", None), "v2_events", None)
    block = events.get("on_response") if isinstance(events, dict) else None
    if isinstance(block, dict) and "negates_damage" in block:
        return bool(block.get("negates_damage"))
    return False


def _damage_response_options(engine, event: dict) -> tuple[int, List[dict]]:
    target_id = int(event.get("target_id", -1))
    attempted = {int(value) for value in event.get("attempted_responders", [])}
    by_responder: Dict[int, List[dict]] = {}
    if (
        target_id not in attempted
        and _valid_player(engine, target_id)
        and engine.players[target_id].health > 0
    ):
        for hand_card in list(engine.players[target_id].hand):
            trigger = getattr(getattr(hand_card, "card_def", None), "response_trigger", "")
            if not _damage_event_matches_response_trigger(event, trigger):
                continue
            if not engine._can_pay_counter_card(target_id, hand_card):
                continue
            by_responder.setdefault(target_id, []).append({
                "kind": DAMAGE_RESPONSE_KIND,
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


def _data_declaration(card_def, event_name: str) -> Optional[dict]:
    """Return a passive declaration block from a card's ``events`` data."""
    events = getattr(card_def, "v2_events", None)
    block = events.get(event_name) if isinstance(events, dict) else None
    return block if isinstance(block, dict) else None


def _declared_target_id(engine, equipment, owner_id: int, selector: Any) -> int:
    """Resolve a declaration target selector to a player id.

    Selectors are data: ``equipment_target`` (the player the equipment is
    attached to), ``owner``/``self`` (the equipment's owner) or a literal id.
    """
    text = str(selector if selector is not None else "equipment_target").strip().lower()
    if text in ("equipment_target", "attached", "attached_player", "target"):
        return int(_equipment_target(engine, equipment, owner_id))
    if text in ("owner", "equipment_owner", "self", "source"):
        return int(owner_id)
    try:
        return int(text)
    except (TypeError, ValueError):
        return -1


def _resource_cost_map(raw: Any) -> Dict[str, int]:
    """Resolve a declaration ``cost`` block into ``resource -> amount``."""
    costs: Dict[str, int] = {}
    if not isinstance(raw, dict):
        return costs
    for key, resource in _RESOURCE_COST_KEYS:
        if key not in raw:
            continue
        try:
            amount = max(0, int(raw.get(key) or 0))
        except (TypeError, ValueError):
            amount = 0
        if amount:
            costs[resource] = max(costs.get(resource, 0), amount)
    return costs


def _can_pay_resources(engine, owner_id: int, costs: Dict[str, int]) -> bool:
    if not _valid_player(engine, owner_id):
        return False
    return all(
        int(getattr(engine.players[owner_id], resource, 0) or 0) >= amount
        for resource, amount in costs.items()
    )


def _spend_resources(engine, owner_id: int, costs: Dict[str, int], card=None) -> None:
    for resource, amount in costs.items():
        engine._spend_resource(owner_id, resource, amount, card)


def _declared_steps(declaration: Any, key: str = "steps") -> List[dict]:
    if not isinstance(declaration, dict):
        return []
    steps = declaration.get(key)
    return list(steps) if isinstance(steps, list) else []


def _v2_context(engine, *, source_id: int, target_id: Optional[int] = None,
                card: Optional[CardInstance] = None, event: str = "",
                vars: Optional[dict] = None,
                choice: Optional[dict] = None) -> dict:
    """Runtime context for declaration steps that run outside a card play."""
    context = {
        "source_player": int(source_id),
        "target_player": int(target_id if target_id is not None else source_id),
        "target_player_explicit": True,
        "card": card,
        "room": getattr(engine, "room", None),
        "loadout": getattr(engine, "v2_loadout", None),
        "vars": dict(vars or {}),
        "last_damage": 0,
        "current_event": str(event or ""),
        "current_action": {},
    }
    if isinstance(choice, dict):
        context["choice"] = choice
        context["current_action"] = {"choice": choice}
    return context


@contextlib.contextmanager
def _effect_context(engine, context: dict):
    """Publish *context* the way ``engine._run_effect_list`` does.

    Equipment selectors (``equipment_target``/``equipment_owner``) resolve
    through ``engine._active_effect_context``, so declarations evaluated
    outside a card play need the same bookkeeping.
    """
    prev_context = getattr(engine, "_active_effect_context", None)
    prev_choice = getattr(engine, "_active_choice", None)
    engine._active_effect_context = context
    choice = context.get("choice") if isinstance(context, dict) else None
    if isinstance(choice, dict):
        engine._active_choice = choice
    try:
        yield context
    finally:
        engine._active_effect_context = prev_context
        engine._active_choice = prev_choice


def _run_declared_steps(engine, context: dict, steps: Any) -> None:
    """Run a declaration's v2 steps through the shared mod runtime."""
    if not isinstance(steps, list) or not steps:
        return
    from mod_runtime_v2 import run_v2_steps

    with _effect_context(engine, context):
        result = run_v2_steps(engine, context, steps)
    if isinstance(result, dict) and result.get("needs_v2_ui"):
        engine._store_v2_ui_pause(result.get("v2_ui_pause") or {})


def _distribute_charge_to_hand(engine, target_id: int, total: int, mode: str = "ceil_even") -> int:
    """Spread *total* charge over every hand card of *target_id*.

    ``ceil_even`` (the historical copper rod wording) gives every card
    ``ceil(total / hand size)`` layers, ``exact`` floors the division and
    ``fixed`` is handled by the caller.  Charge is written without touching
    ``disabled_flags`` -- that is the behaviour the pre-6a helper had, and the
    A/B run compares against it.
    """
    if not _valid_player(engine, target_id):
        return 0
    hand = list(getattr(engine.players[target_id], "hand", []) or [])
    if not hand:
        return 0
    total = max(0, int(total or 0))
    if str(mode or "ceil_even").strip().lower() == "exact":
        amount = total // len(hand)
    else:
        amount = int(math.ceil(total / len(hand)))
    if amount <= 0:
        return 0
    for hand_card in hand:
        _add_charge(hand_card, amount)
    return amount


def _absorb_cost_map(declaration: dict) -> Dict[str, int]:
    """Resolve a declaration ``cost`` block into ``resource -> amount``."""
    return _resource_cost_map(declaration.get("cost"))


def _absorb_when_matches(declaration: dict, kind: str) -> bool:
    when = str(declaration.get("when", "any") or "any").strip().lower()
    if when in ("", "any", "all", "both"):
        return True
    if when in ("attack", "attack_damage", "hits"):
        return str(kind or "").strip().lower() == "attack"
    if when in ("direct", "direct_damage", "effect"):
        return str(kind or "").strip().lower() == "direct"
    return False


def try_declared_damage_absorb(engine, target_id: int, damage: int, kind: str = "any") -> bool:
    """Let data declared equipment absorbers eat incoming *damage*.

    The equipment card owns the declaration (``events.on_damage_absorb``):

    * ``when``   -- ``any`` (default) / ``attack`` / ``direct``;
    * ``target`` -- whose damage is absorbed (``equipment_target`` default);
    * ``cost``   -- resources the equipment owner pays per absorption
                    (``{"m": 1}`` for the Magic Copper Rod);
    * ``charge_to_hand`` -- how the absorbed points turn into hand charge
                    (``{"mode": "ceil_even"}`` is the historical formula);
    * ``log``    -- battle log template ({source} / {target} / {damage} /
                    {amount}).

    The first matching, payable declaration wins, in player/equipment order --
    exactly the order the pre-6a Magic Copper Rod scan used.
    """
    if damage <= 0 or not _valid_player(engine, target_id):
        return False
    for owner_id, owner in enumerate(getattr(engine, "players", []) or []):
        for equipment in list(getattr(owner, "equipment", []) or []):
            if not _active_equipment(engine, equipment):
                continue
            card_def = getattr(getattr(equipment, "card_instance", None), "card_def", None)
            declaration = _data_declaration(card_def, DAMAGE_ABSORB_EVENT)
            if not declaration:
                continue
            if not _absorb_when_matches(declaration, kind):
                continue
            if _declared_target_id(engine, equipment, owner_id, declaration.get("target")) != int(target_id):
                continue
            costs = _absorb_cost_map(declaration)
            if any(
                int(getattr(engine.players[owner_id], resource, 0) or 0) < amount
                for resource, amount in costs.items()
            ):
                continue
            for resource, amount in costs.items():
                engine._spend_resource(owner_id, resource, amount, equipment.card_instance)
            spread = declaration.get("charge_to_hand")
            mode = str((spread or {}).get("mode", "ceil_even")) if isinstance(spread, dict) else "ceil_even"
            charged = _distribute_charge_to_hand(engine, target_id, damage, mode)
            log = declaration.get("log")
            if log:
                engine.log_msg(engine._format_step_log(
                    str(log),
                    source=engine.pn(owner_id),
                    target=engine.pn(target_id),
                    damage=int(damage),
                    total=int(damage),
                    amount=charged,
                ))
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


def _turn_start_choice_declaration(engine, equipment) -> Optional[dict]:
    """The equipment card's passive ``on_turn_start_choice`` block, if any."""
    if equipment is None:
        return None
    card_def = getattr(getattr(equipment, "card_instance", None), "card_def", None)
    return _data_declaration(card_def, TURN_START_CHOICE_EVENT)


def _turn_start_choice_id(declaration: dict) -> str:
    return str(declaration.get("id") or TURN_START_CHOICE_EVENT)


def _turn_start_choice_allowed_players(engine, owner_id: int, declaration: dict) -> List[int]:
    """Player ids the declaration's ``player_picker`` control may offer."""
    control = declaration.get("control") if isinstance(declaration.get("control"), dict) else {}
    allowed = control.get("allowed", "selectable_players")
    if isinstance(allowed, str):
        selector = allowed.strip().lower()
        if selector in ("", "selectable_players", "any", "selectable"):
            return [
                target for target in range(len(engine.players))
                if _target_selectable(engine, owner_id, target, allow_self=True)
            ]
        try:
            allowed = [int(selector)]
        except (TypeError, ValueError):
            return []
    if not isinstance(allowed, (list, tuple, set)):
        return []
    return [int(value) for value in allowed if _valid_player(engine, value)]


def _turn_start_choice_control(engine, owner_id: int, declaration: dict) -> Optional[dict]:
    """Build the UI control a decision block declares (or ``None`` when empty)."""
    control = declaration.get("control") if isinstance(declaration.get("control"), dict) else {}
    kind = str(control.get("type") or "select").strip().lower()
    control_id = str(control.get("id") or "choice")
    label_cn = str(control.get("label_cn") or "")
    label_en = str(control.get("label_en") or "")
    if kind in ("player_picker", "player", "player_select"):
        allowed = _turn_start_choice_allowed_players(engine, owner_id, declaration)
        if not allowed:
            return None
        return _player_control(control_id, allowed, label_cn, label_en)
    options = [
        {
            "value": option.get("value"),
            "label_cn": str(option.get("label_cn") or ""),
            "label_en": str(option.get("label_en") or ""),
        }
        for option in (control.get("options") or [])
        if isinstance(option, dict)
    ]
    if not options:
        return None
    return _select_control(control_id, options, label_cn, label_en)


def _turn_start_choice_ready(engine, owner_id: int, turn_player_id: int, declaration: dict,
                             equipment) -> bool:
    """Can this entry be offered / applied right now?"""
    if declaration.get("owner_is_turn_player") and owner_id != turn_player_id:
        return False
    costs = _resource_cost_map(declaration.get("cost"))
    if costs and not _can_pay_resources(engine, owner_id, costs):
        return False
    when = declaration.get("when")
    if when is None:
        return True
    from mod_runtime_v2 import check_v2_condition

    context = _v2_context(
        engine,
        source_id=owner_id,
        target_id=turn_player_id,
        card=getattr(equipment, "card_instance", None),
        event=TURN_START_CHOICE_EVENT,
    )
    with _effect_context(engine, context):
        return bool(check_v2_condition(engine, context, when))


def _turn_start_choice_branch(declaration: dict, value: Any) -> Optional[dict]:
    """The ``choices`` entry matching a submitted control value."""
    for branch in declaration.get("choices") or []:
        if not isinstance(branch, dict):
            continue
        if str(branch.get("value")) == str(value):
            return branch
    return None


def queue_turn_start_choices(engine, player_id: int, resume_handler: str) -> bool:
    """Queue every ``on_turn_start_choice`` equipment attached to *player_id*.

    The declaration (card data) owns the UI control, the cost, the optional
    ``when`` condition and the effect steps; the engine only schedules the
    entries, pauses for the owner and resumes them one by one.
    """
    if not _valid_player(engine, player_id):
        return False
    entries = []
    for owner_id, owner in enumerate(engine.players):
        for equipment in list(getattr(owner, "equipment", []) or []):
            if not _active_equipment(engine, equipment):
                continue
            declaration = _turn_start_choice_declaration(engine, equipment)
            if not declaration:
                continue
            target_id = _equipment_target(engine, equipment, owner_id)
            if target_id != player_id:
                continue
            entries.append({
                "type": _turn_start_choice_id(declaration),
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
        declaration = _turn_start_choice_declaration(engine, equipment)
        if not declaration:
            continue
        if not _turn_start_choice_ready(engine, owner_id, target_id, declaration, equipment):
            continue
        control = _turn_start_choice_control(engine, owner_id, declaration)
        if control is None:
            continue
        state["active_entry"] = entry
        return _pause(
            engine,
            state,
            player_id=owner_id,
            purpose=_turn_start_choice_id(declaration),
            component=_choice_component(
                title_cn=str(declaration.get("title_cn") or ""),
                title_en=str(declaration.get("title_en") or ""),
                text_cn=str(declaration.get("text_cn") or ""),
                text_en=str(declaration.get("text_en") or ""),
                control=control,
                cancellable=bool(declaration.get("cancellable")),
            ),
            control_id=str(control.get("id") or "choice"),
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
    declaration = _turn_start_choice_declaration(engine, equipment) if valid_equipment else None
    if declaration and not cancelled and _valid_player(engine, owner_id):
        _apply_turn_start_choice(engine, entry, declaration, equipment, value)
    return _run_turn_start_state(engine, state)


def _apply_turn_start_choice(engine, entry: dict, declaration: dict, equipment, value: Any) -> None:
    """Pay the chosen branch's cost and run its declared steps."""
    owner_id = int(entry.get("owner_id", -1))
    turn_player_id = int(entry.get("target_id", -1))
    branch = _turn_start_choice_branch(declaration, value)
    target_id = turn_player_id
    if branch is None:
        control = declaration.get("control") if isinstance(declaration.get("control"), dict) else {}
        kind = str(control.get("type") or "select").strip().lower()
        if kind in ("player_picker", "player", "player_select"):
            try:
                target_id = int(value)
            except (TypeError, ValueError):
                return
            if target_id not in _turn_start_choice_allowed_players(engine, owner_id, declaration):
                return
        elif not any(
            str(option.get("value")) == str(value)
            for option in (control.get("options") or [])
            if isinstance(option, dict)
        ):
            return
        steps = _declared_steps(declaration)
        costs = _resource_cost_map(declaration.get("cost"))
    else:
        steps = _declared_steps(branch)
        costs = _resource_cost_map(branch.get("cost"))
    if not _turn_start_choice_ready(engine, owner_id, turn_player_id, declaration, equipment):
        return
    if costs and not _can_pay_resources(engine, owner_id, costs):
        return
    if not steps and not costs:
        return
    if costs:
        _spend_resources(engine, owner_id, costs, equipment.card_instance)
    context = _v2_context(
        engine,
        source_id=owner_id,
        target_id=target_id,
        card=equipment.card_instance,
        event=TURN_START_CHOICE_EVENT,
        choice={"target_player_id": target_id},
    )
    _run_declared_steps(engine, context, steps)


def _resume_damage_response(engine, state: dict, value: Any, cancelled: bool) -> dict:
    queue = _damage_queue(engine)
    if not queue:
        return _finish_damage_queue(engine)
    event = queue[0]
    if str(event.get("id") or "") != str(state.get("event_id") or ""):
        return _run_damage_queue(engine)
    responder_id = int(state.get("player_id", -1))
    selected = "pass" if cancelled else str(value or "pass")
    response_prefixes = (DAMAGE_RESPONSE_KIND + ":", "horn:")
    if selected.startswith(response_prefixes):
        try:
            instance_id = int(selected.split(":", 1)[1])
        except (TypeError, ValueError):
            instance_id = -1
        responder_card = (
            engine.players[responder_id].find_hand_card(instance_id)
            if _valid_player(engine, responder_id)
            else None
        )
        declared_trigger = getattr(getattr(responder_card, "card_def", None), "response_trigger", "")
        if (
            responder_card is not None
            and _damage_event_matches_response_trigger(event, declared_trigger)
            and engine._can_pay_counter_card(responder_id, responder_card)
        ):
            engine._spend_resource(responder_id, "elixir", max(0, int(responder_card.cost_e or 0)), responder_card)
            engine._spend_resource(responder_id, "magic", max(0, int(responder_card.cost_m or 0)), responder_card)
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
                    if not _damage_response_negates(removed):
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


def refresh_dynamic_costs(engine) -> None:
    """Run every card's declared ``on_cost_refresh`` cleanup.

    A card that used to compute its cost from live state declares the legacy
    keys it may still carry plus the overrides to reset::

        {"events": {"on_cost_refresh": {
            "legacy_vars": ["void_dlc_nut_dynamic_cost"],
            "reset": ["cost_e_override"]}}}

    The helper only walks cards that declare the block, so it never touches the
    cost of unrelated cards (the Nut no longer has a dynamic deck-count cost;
    the block clears overrides stored by older builds / saves).
    """
    for player in getattr(engine, "players", []) or []:
        for zone_name in ("hand", "deck", "discard", "exile"):
            for card in list(getattr(player, zone_name, []) or []):
                declaration = _data_declaration(getattr(card, "card_def", None), COST_REFRESH_EVENT)
                if not declaration:
                    continue
                custom = getattr(card, "custom_vars", None)
                if not isinstance(custom, dict):
                    continue
                legacy_vars = [
                    str(name) for name in (declaration.get("legacy_vars") or []) if str(name or "")
                ]
                if not any(custom.pop(name, None) is not None for name in legacy_vars):
                    continue
                reset = declaration.get("reset") or ["cost_e_override"]
                for attr in reset:
                    if not hasattr(card, str(attr)):
                        continue
                    setattr(card, str(attr), None)


def prepare_copy_card(engine, owner_id: int, parent: CardInstance, copy_card: CardInstance) -> None:
    """Run the parent card's declared ``on_create_copy`` steps on *copy_card*.

    Card data owns what an exiled copy keeps::

        {"events": {"on_create_copy": {"steps": [
            {"op": "card_prop_add", "property": "magic_swift_value", "amount": 2}]}}}

    The steps run with ``card`` bound to the copy, so ``current_card`` refs and
    ``self`` targets address the copy rather than the original.
    """
    if parent is None or copy_card is None:
        return
    declaration = _data_declaration(getattr(parent, "card_def", None), COPY_EVENT)
    if not declaration:
        return
    steps = _declared_steps(declaration, "steps")
    if not steps and isinstance(declaration.get("body"), list):
        steps = list(declaration["body"])
    context = _v2_context(
        engine,
        source_id=int(owner_id),
        target_id=int(owner_id),
        card=copy_card,
        event=COPY_EVENT,
    )
    _run_declared_steps(engine, context, steps)


def _has_equipment_targeting(engine, player_id: int, mark: str) -> bool:
    if not _valid_player(engine, player_id):
        return False
    for owner_id, owner in enumerate(getattr(engine, "players", []) or []):
        for equipment in list(getattr(owner, "equipment", []) or []):
            if (
                _active_equipment(engine, equipment)
                and _equipment_target(engine, equipment, owner_id) == player_id
                and _equipment_has_mark(engine, equipment, mark)
            ):
                return True
    return False


def _has_equipment_targeting_flag(engine, player_id: int, flag: str) -> bool:
    """True when an active equipment attached to ``player_id`` declares ``flag``."""
    if not _valid_player(engine, player_id):
        return False
    for owner_id, owner in enumerate(getattr(engine, "players", []) or []):
        for equipment in list(getattr(owner, "equipment", []) or []):
            if not _active_equipment(engine, equipment):
                continue
            if _equipment_target(engine, equipment, owner_id) != player_id:
                continue
            if card_has_flag(getattr(equipment, "card_instance", None), flag):
                return True
    return False


def blocks_special_effect_damage(engine, player_id: int) -> bool:
    """Special-effect damage immunity, declared by the shield card's flags."""
    return _has_equipment_targeting_flag(engine, player_id, SPECIAL_DAMAGE_SHIELD_FLAG)


def blocks_special_effect_interference(engine, player_id: int) -> bool:
    """Interference immunity (the magic mask), declared by the shield card's flags."""
    return _has_equipment_targeting_flag(engine, player_id, SPECIAL_INTERFERENCE_SHIELD_FLAG)


def _data_declarations(card_def, event_name: str) -> List[dict]:
    """Every declaration block stored under ``events.<event_name>``."""
    events = getattr(card_def, "v2_events", None)
    block = events.get(event_name) if isinstance(events, dict) else None
    if isinstance(block, dict):
        return [block]
    if isinstance(block, list):
        return [item for item in block if isinstance(item, dict)]
    return []


class ElixirRecoveryAura(NamedTuple):
    """Data-declared turn-start aura of an equipment attached to the turn player.

    ``elixir`` adds to the target's elixir recovery, ``overload`` is applied to
    the target before that recovery is granted, and ``log`` (optional) owns the
    battle-log wording for the overload part of the effect.
    """

    elixir: int
    overload: int
    log: Optional[str]


def _declared_int(engine, owner_id: int, raw: Any, card: Optional[CardInstance]) -> int:
    """Resolve a declaration value that may be a literal or a v2 expression."""
    if raw is None or isinstance(raw, bool):
        return int(raw or 0)
    if isinstance(raw, (int, float)):
        return int(raw)
    try:
        return int(engine._eval_int(owner_id, raw, card))
    except Exception:  # noqa: BLE001 - a broken declaration must not break the turn
        return 0


def declared_elixir_recovery_aura(engine, equipment, owner_id: int) -> ElixirRecoveryAura:
    """Resolve an equipment's ``events.on_elixir_recovery`` declaration block.

    The block replaces the CardName tests the turn-start recovery loop used to
    run (for example "Pincer costs its target one overload"): the engine only
    resolves the numbers and the wording, the card data owns the mechanic.
    """
    card_def = getattr(equipment, "card_def", None)
    declaration = _data_declaration(card_def, ELIXIR_RECOVERY_AURA_EVENT)
    if declaration is None:
        for effect in getattr(card_def, "effects", None) or []:
            if isinstance(effect, dict) and effect.get("type") == ELIXIR_RECOVERY_AURA_EVENT:
                params = effect.get("params")
                declaration = params if isinstance(params, dict) else {}
                break
    if not isinstance(declaration, dict):
        return ElixirRecoveryAura(0, 0, None)
    card = getattr(equipment, "card_instance", None)
    elixir = _declared_int(engine, owner_id, declaration.get("elixir"), card)
    overload = max(0, _declared_int(engine, owner_id, declaration.get("overload"), card))
    log = declaration.get("log")
    log = str(log) if isinstance(log, str) and log else None
    return ElixirRecoveryAura(elixir, overload, log)


def play_summary_declaration(card) -> dict:
    """Resolve a card's ``events.on_play_summary`` block (message wording).

    The block owns the battle-log wording a card wants instead of the generic
    per-step lines: ``suppress_detail_logs`` (skip the individual step logs),
    ``suppress_play_log`` (skip the generic "played X" line) and the two
    templates ``plain_log`` / ``discarded_log`` rendered with ``{player}`` and
    ``{count}``.
    """
    card_def = getattr(card, "card_def", None)
    declaration = _data_declaration(card_def, PLAY_SUMMARY_EVENT)
    return declaration if isinstance(declaration, dict) else {}


RESPONSE_EVENT = "on_response"


def response_resolution_declaration(card_or_def) -> dict:
    """Resolve the ``events.on_response.resolution`` block of a counter card.

    Counter cards used to be recognised by name inside ``handle_response`` and
    ``_execute_counter_effect``.  The block now owns that knowledge:

    ``negate_bloom``
        the responded skill card fizzles (Magic Bubble);
    ``negate_responded`` / ``exile_responded``
        the responded card is negated and/or enters exile after it settles
        (Nitro); ``log`` owns the battle-log wording;
    ``halve_precision``
        a precise attack is halved instead of resolved in full (Bubble);
    ``clamp_responder_props``
        props the responder gained from this very counter are clamped back to
        their pre-response value once the responded card settled (Bubble's
        dodge must not dodge the attack it responded to);
    ``suppress_responder_untargetable``
        the responded card still resolves against the responder, so a
        counter-granted "untargetable" is lifted for that resolution
        (Cucumber);
    ``after_resolution``
        steps that run once the responded card settled (Cucumber's +1
        untargetable).
    """
    card_def = getattr(card_or_def, "card_def", card_or_def)
    for declaration in _data_declarations(card_def, RESPONSE_EVENT):
        block = declaration.get("resolution")
        if isinstance(block, dict):
            return dict(block)
    return {}


def run_response_after_resolution(engine, responder_id: int, counter_card, original_card,
                                  steps: Any, *, target_id: Optional[int] = None) -> None:
    """Run the ``after_resolution`` steps of an ``on_response`` declaration."""
    if not isinstance(steps, list) or not steps:
        return
    context = _v2_context(
        engine,
        source_id=int(responder_id),
        target_id=int(responder_id if target_id is None else target_id),
        card=counter_card,
        event="response_after_resolution",
        vars={"original_card_def_id": getattr(original_card, "def_id", "")},
    )
    context["original_card"] = original_card
    _run_declared_steps(engine, context, steps)


STATUS_ALIAS_KEY = "status_aliases"


def status_alias_declarations(engine) -> List[dict]:
    """Every ``status_aliases`` block declared by card data.

    A block names one logical status family:

    ``role`` / ``canonical``
        the name the engine code and the storage use;
    ``aliases``
        alternative spellings other cards/tools may address (for example the
        Chinese name of the card that introduced the status);
    ``legacy``
        old serialised fields of the same status: ``active`` (bool flag),
        ``hits`` (consumed layers) and ``max`` (how many layers ``active``
        used to stand for).
    """
    cached = getattr(engine, "_status_alias_declarations", None)
    if isinstance(cached, list):
        return cached
    out: List[dict] = []
    try:
        card_defs = list(CARD_DEFS.values())
    except Exception:  # noqa: BLE001 - engine may run without the card table
        card_defs = []
    for card_def in card_defs:
        resource = getattr(card_def, "v2_resource", None)
        raw = resource.get(STATUS_ALIAS_KEY) if isinstance(resource, dict) else None
        if raw is None:
            raw = getattr(card_def, STATUS_ALIAS_KEY, None)
        if isinstance(raw, dict):
            out.append(raw)
        elif isinstance(raw, list):
            out.extend(item for item in raw if isinstance(item, dict))
    engine._status_alias_declarations = out
    return out


def status_alias_declaration(engine, key: Any) -> Optional[dict]:
    """The alias declaration matching a role name, canonical name or alias."""
    text = str(key or "").strip().lower()
    if not text:
        return None
    for declaration in status_alias_declarations(engine):
        names = [
            str(declaration.get("role") or "").strip(),
            str(declaration.get("canonical") or "").strip(),
        ]
        names.extend(str(item).strip() for item in (declaration.get("aliases") or []))
        if text in {name.lower() for name in names if name}:
            return declaration
    return None


def status_alias_names(declaration: dict) -> tuple:
    """``(canonical, names)``: the storage name and every readable spelling."""
    canonical = str(declaration.get("canonical") or declaration.get("role") or "").strip()
    names = [
        str(item).strip()
        for item in (declaration.get("aliases") or [])
        if str(item).strip()
    ]
    if canonical and canonical not in names:
        names.insert(0, canonical)
    return canonical, tuple(names)


PLAY_CHOICE_REQUEST_KEY = "play_choice_request"


def play_choice_request_declaration(card) -> dict:
    """The ``play_choice_request`` block declared by a card's data (Round 19).

    The block is a card top-level key (the same place as ``status_aliases``) and
    describes the prompt the engine has to raise *before* resolving a card:

    ``choice_key``
        the choice field the player answers (for example
        ``bio_blood_sugar_mode``); the declaration counts as answered once the
        field carries one of the declared options;
    ``options``
        optional value whitelist when the payload does not list its own
        ``options``;
    ``needs_target``
        the target picker runs first; the prompt is only raised once the play
        choice carries a target;
    ``zones``
        optional zone whitelist (for example ``["hand"]``); outside those zones
        the card does not prompt;
    ``condition``
        optional condition tree (the engine's normal condition evaluator) that
        gates the prompt;
    ``request``
        the payload the client receives, forwarded verbatim.

    Accepts a ``CardDef`` or a ``CardInstance``; an undeclared card returns an
    empty dict so the caller falls back to its previous behaviour.
    """
    card_def = getattr(card, "card_def", card)
    if card_def is None:
        return {}
    containers = [card_def, getattr(card_def, "v2_resource", None)]
    events = getattr(card_def, "v2_events", None)
    if isinstance(events, dict):
        containers.append(events)
    for container in containers:
        if isinstance(container, dict):
            raw = container.get(PLAY_CHOICE_REQUEST_KEY)
        else:
            raw = getattr(container, PLAY_CHOICE_REQUEST_KEY, None)
        if isinstance(raw, dict) and raw:
            return raw
    return {}


# Player attributes an ``on_equipment_projection`` block may grant/revoke while
# the equipment is active.  The declaration stores the *active* delta; suspending
# (封印) applies it and resuming adds it back.
_PROJECTION_ATTRS = ("armor", "max_elixir", "max_magic")


def equipment_projection_declaration(equipment) -> dict:
    """Resolve an equipment's ``events.on_equipment_projection`` block."""
    card_def = getattr(equipment, "card_def", None)
    declaration = _data_declaration(card_def, EQUIPMENT_PROJECTION_EVENT)
    return declaration if isinstance(declaration, dict) else {}


def apply_equipment_projection(engine, owner_id: int, equipment, phase: str, *,
                               run_destroy_event: bool = True,
                               was_sealed: bool = False) -> bool:
    """Apply/revoke the data declared passive stat projection of an equipment.

    ``phase`` is ``suspend`` (sealed), ``resume`` (unsealed again) or
    ``cleanup`` (destroyed / transformed).  ``cleanup`` honours the block's
    ``on_destroy`` / ``on_transform`` switches so a card whose removal is
    already covered by an ``equipment_destroy`` script is not charged twice.
    """
    declaration = equipment_projection_declaration(equipment)
    if not declaration:
        return False
    if phase == "cleanup":
        if was_sealed:
            return False
        if run_destroy_event and declaration.get("on_destroy", True) is False:
            return False
        if not run_destroy_event and declaration.get("on_transform", True) is False:
            return False
    target_id = _equipment_target(engine, equipment, owner_id)
    if not engine._valid_player_id(target_id):
        return False
    player = engine.players[target_id]
    delta_sign = -1 if phase == "resume" else 1
    card = getattr(equipment, "card_instance", None)
    for attr in _PROJECTION_ATTRS:
        raw = declaration.get(attr)
        if raw is None:
            continue
        amount = delta_sign * _declared_int(engine, owner_id, raw, card)
        if not amount:
            continue
        current = int(getattr(player, attr, 0) or 0)
        setattr(player, attr, max(0, current + amount))
        for source, limit in (("elixir", "max_elixir"), ("magic", "max_magic")):
            if attr != limit:
                continue
            pooled = int(getattr(player, source, 0) or 0)
            if pooled > int(getattr(player, limit, 0) or 0):
                setattr(player, source, int(getattr(player, limit, 0) or 0))
    return True


def _status_projection_index(engine) -> Dict[str, List[dict]]:
    """Index the ``on_effective_status`` projections declared by card data.

    The index is per engine instance (card defs are global, but a room can be
    created after a mod reload) and maps ``status key -> declaration blocks``.
    """
    cached = getattr(engine, "_effective_status_index", None)
    if isinstance(cached, dict):
        return cached
    index: Dict[str, List[dict]] = {}
    try:
        card_defs = list(CARD_DEFS.values())
    except Exception:
        card_defs = []
    for card_def in card_defs:
        for declaration in _data_declarations(card_def, STATUS_PROJECTION_EVENT):
            key = str(declaration.get("status") or "").strip().lower()
            if not key:
                continue
            index.setdefault(key, []).append(declaration)
    engine._effective_status_index = index
    return index


def _projection_source_value(engine, player_id: int, source: Any) -> int:
    """Resolve one declared status source to a non-negative layer count."""
    if not isinstance(source, dict):
        return 0
    custom = source.get("custom_status", source.get("custom_statuses"))
    if custom is None and "player_status" not in source and "attr" not in source:
        custom = source.get("status")
    if custom is not None:
        names = custom if isinstance(custom, (list, tuple, set)) else [custom]
        names = [str(name) for name in names if str(name or "")]
        if not names:
            return 0
        try:
            return max(0, int(engine._custom_status_value(player_id, *names) or 0))
        except Exception:
            return 0
    raw_attr = source.get("player_status", source.get("attr"))
    names = raw_attr if isinstance(raw_attr, (list, tuple, set)) else [raw_attr]
    for name in names:
        name = str(name or "")
        if name and hasattr(engine.players[player_id], name):
            try:
                return max(0, int(getattr(engine.players[player_id], name) or 0))
            except (TypeError, ValueError):
                continue
    return 0


def _combine_projection_sources(engine, player_id: int, declaration: dict) -> int:
    sources = declaration.get("sources")
    if not isinstance(sources, list):
        sources = []
    values = [_projection_source_value(engine, player_id, source) for source in sources]
    combine = str(declaration.get("combine") or "max").strip().lower()
    value = sum(values) if combine in ("sum", "add", "total") else (max(values) if values else 0)
    try:
        floor = int(declaration.get("floor", 0) or 0)
    except (TypeError, ValueError):
        floor = 0
    return max(floor, int(value))


def effective_status_value(engine, player_id: int, status_key: str) -> Optional[int]:
    """The declared effective layer count of *status_key*, or ``None``.

    ``None`` means "no card data declares this projection" -- the callers below
    then fall back to the built-in wording so unrelated packs keep working.
    """
    if not _valid_player(engine, player_id):
        return None
    declarations = _status_projection_index(engine).get(str(status_key or "").strip().lower())
    if not declarations:
        return None
    values = [_combine_projection_sources(engine, player_id, item) for item in declarations]
    if any(str(item.get("combine") or "").strip().lower() in ("sum", "add", "total") for item in declarations):
        return max(0, sum(values))
    return max(0, max(values) if values else 0)


def _default_status_value(engine, player_id: int, status_key: str) -> int:
    if not _valid_player(engine, player_id):
        return 0
    sources = _DEFAULT_STATUS_PROJECTIONS.get(status_key) or []
    values = [_projection_source_value(engine, player_id, source) for source in sources]
    return max(0, max(values) if values else 0)


def effective_toxic_poison(engine, player_id: int) -> int:
    """Effective 剧毒 layers (data declared, legacy wording as fallback)."""
    declared = effective_status_value(engine, player_id, "toxic_poison")
    if declared is not None:
        return declared
    return _default_status_value(engine, player_id, "toxic_poison")


def effective_poison_coating(engine, player_id: int) -> int:
    """Effective 淬毒 layers an attack consumes."""
    declared = effective_status_value(engine, player_id, "poison_coating")
    if declared is not None:
        return declared
    return _default_status_value(engine, player_id, "poison_coating")


def effective_blind(engine, player_id: int) -> int:
    """Effective 失明 level (drives the hand shuffle / hand hiding)."""
    declared = effective_status_value(engine, player_id, "blind")
    if declared is not None:
        return declared
    return _default_status_value(engine, player_id, "blind")


def _apply_visible_projection(payload: dict, names: List[str], visible: dict) -> None:
    mode = str(visible.get("mode") or visible.get("op") or "cap").strip().lower()
    try:
        amount = int(visible.get("value", visible.get("amount", 0)) or 0)
    except (TypeError, ValueError):
        amount = 0
    for name in names:
        if name not in payload:
            continue
        try:
            current = max(0, int(payload.get(name) or 0))
        except (TypeError, ValueError):
            continue
        if mode in ("hide", "clear"):
            payload[name] = 0
        elif mode in ("add", "offset", "raise"):
            payload[name] = max(0, current + amount)
        elif mode in ("sub", "subtract", "reduce"):
            payload[name] = max(0, current - amount)
        else:  # "cap" (default)
            payload[name] = min(current, max(0, amount))


def project_effective_mask_statuses(engine, player_id: int, payload: dict) -> dict:
    """Apply data declared *visibility* projections to a serialized player state.

    A card may extend its ``on_effective_status`` declaration with a
    ``"visible"`` clause (``{"status": "poison", "visible": {"mode": "hide"}}``)
    to change what other players see.  No shipped pack declares one -- the Mask
    no longer changes visible status layers -- so payloads pass through
    unchanged, but the hook itself is data driven.
    """
    if not isinstance(payload, dict) or not _valid_player(engine, player_id):
        return payload
    for declaration in _status_projection_index(engine).values():
        for item in declaration:
            visible = item.get("visible")
            if not isinstance(visible, dict) or not visible:
                continue
            for source in item.get("sources") or []:
                if not isinstance(source, dict):
                    continue
                if "player_status" in source or "attr" in source:
                    raw_attr = source.get("player_status", source.get("attr"))
                    names = [str(name) for name in (raw_attr if isinstance(raw_attr, (list, tuple, set)) else [raw_attr]) if name]
                    _apply_visible_projection(payload, names, visible)
                    continue
                custom = source.get("custom_status", source.get("custom_statuses", source.get("status")))
                if custom is None:
                    continue
                custom_statuses = payload.get("custom_statuses")
                if not isinstance(custom_statuses, dict):
                    continue
                names = [str(name) for name in (custom if isinstance(custom, (list, tuple, set)) else [custom]) if name]
                _apply_visible_projection(custom_statuses, names, visible)
    return payload


def card_applies_hand_charge(card: Optional[CardInstance]) -> bool:
    """Does the card declare that playing it puts charge on hand cards?

    The flag (``applies_hand_charge`` in the card's ``flags``) is the data
    declaration; before Round 6b the engine scanned the card's steps for a
    hard coded list of charge-adding ops.
    """
    return card_has_flag(card, HAND_CHARGE_FLAG)


def card_has_flag(card: Optional[CardInstance], flag: str) -> bool:
    """Does the card instance carry ``flag`` (including instance/disabled flags)?"""
    if card is None:
        return False
    card_def = getattr(card, "card_def", None)
    flags = normalize_card_flags(getattr(card_def, "flags", set()) or set())
    flags |= normalize_card_flags(getattr(card, "instance_flags", set()) or set())
    flags -= normalize_card_flags(getattr(card, "disabled_flags", set()) or set())
    return str(flag) in flags


def equipment_target_restriction(engine, equipment, owner_id: int) -> Optional[tuple[int, int]]:
    """Resolve a data declared ``on_target_restrict`` block.

    Returns ``(restricted_player, forced_target)``: while the equipment is
    attached, the *restricted* player may only aim player-target cards at the
    *forced target* (the Eyeball wording: "目标只能指向装备拥有者", declared as
    ``{"from": "equipment_target", "to": "owner"}``).
    """
    card_def = getattr(getattr(equipment, "card_instance", None), "card_def", None)
    declaration = _data_declaration(card_def, TARGET_RESTRICT_EVENT)
    if not declaration:
        return None
    from_id = _declared_target_id(engine, equipment, owner_id, declaration.get("from", "equipment_target"))
    to_id = _declared_target_id(engine, equipment, owner_id, declaration.get("to", "owner"))
    if not _valid_player(engine, from_id) or not _valid_player(engine, to_id):
        return None
    return int(from_id), int(to_id)


def forced_random_target(engine, actor_id: int, candidates: Iterable[int], chosen: int = -1) -> int:
    candidate_ids = [int(target_id) for target_id in candidates if _valid_player(engine, target_id)]
    forced_targets: List[int] = []
    for owner_id, owner in enumerate(engine.players):
        for equipment in list(getattr(owner, "equipment", []) or []):
            if not _active_equipment(engine, equipment):
                continue
            restriction = equipment_target_restriction(engine, equipment, owner_id)
            if restriction is None:
                continue
            forced, _forced_target = restriction
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
            if not _active_equipment(engine, equipment):
                continue
            restriction = equipment_target_restriction(engine, equipment, owner_id)
            if restriction is None:
                continue
            restricted_player, forced_target = restriction
            if (
                restricted_player == actor_id
                and _target_selectable(engine, actor_id, forced_target, allow_self=True)
            ):
                owner_targets.append(forced_target)
    if not owner_targets:
        return None
    if chosen in owner_targets:
        return int(chosen)
    return int(owner_targets[0])
