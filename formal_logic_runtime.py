from __future__ import annotations

import copy
import math
import random
import uuid
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from cards import CARD_DEFS, CardInstance, _new_instance_id
from formal_logic import (
    FormalLogicError,
    LogicExpr,
    ProofFormula,
    canonicalize_variables,
    constant_card_formula,
    expression_from_data,
    expression_to_data,
    expressions_match,
    format_expression,
    format_formula,
    formula_from_data,
    formula_signature,
    formula_to_data,
    formula_variables,
    formulas_alpha_equivalent,
    formulas_special_equivalent,
    implication_chain,
    modus_ponens,
    next_fresh_variable,
    parse_formula,
    substitute_formula,
    transform_contraposition,
    transform_deduction,
    transform_inverse_deduction,
    validate_formula,
)


MOD_ID = "formal_logic"
SUBSTITUTION_STATUS = "formal_logic:substitution"
INFERENCE_STATUS = "formal_logic:inference"
DEBUT_FLAG = "formal_logic:debut"
INFERENCE_EXILE_FLAG = "formal_logic:inference_exile"
GENERATED_THEOREM_ID = "formal_logic:generated_theorem"
MACRO_EQUIPMENT_ID = "formal_logic:macro_equipment"
MP_ID = "formal_logic:mp"
DEDUCTION_META_ID = "formal_logic:deduction_metatheorem"
GREAT_MATHEMATICIAN_ID = "formal_logic:great_mathematician"

MAX_ACTIONS = 1024
MAX_DYNAMIC_CANDIDATES = 160


def _fresh_card_copy_from_dict(data: dict, fallback_def_id: str = "") -> CardInstance:
    if isinstance(data, dict):
        snapshot = copy.deepcopy(data)
        snapshot["instance_id"] = _new_instance_id()
        return CardInstance.from_dict(snapshot)
    return CardInstance(fallback_def_id or "Error")


def _valid_player(engine, player_id: Any) -> bool:
    try:
        player_id = int(player_id)
    except (TypeError, ValueError):
        return False
    return 0 <= player_id < len(getattr(engine, "players", []) or [])


def _card_formal_resource(card: Optional[CardInstance]) -> Dict[str, Any]:
    if card is None:
        return {}
    resource = getattr(getattr(card, "card_def", None), "v2_resource", {}) or {}
    formal = resource.get("formal_logic") if isinstance(resource, dict) else None
    return dict(formal) if isinstance(formal, dict) else {}


def is_formal_logic_card(card: Optional[CardInstance]) -> bool:
    if card is None:
        return False
    return bool(
        str(getattr(card, "def_id", "")).startswith(f"{MOD_ID}:")
        or _card_formal_resource(card)
        or isinstance((getattr(card, "custom_vars", {}) or {}).get("formal_logic_formula"), dict)
    )


def _formula_from_resource(card: CardInstance) -> Optional[ProofFormula]:
    formal = _card_formal_resource(card)
    raw = formal.get("formula")
    if not raw:
        return None
    return parse_formula(str(raw))


def formula_for_card(card: Optional[CardInstance]) -> Optional[ProofFormula]:
    if card is None:
        return None
    custom = getattr(card, "custom_vars", {}) or {}
    raw = custom.get("formal_logic_formula")
    if isinstance(raw, Mapping):
        try:
            return formula_from_data(raw)
        except FormalLogicError:
            return None
    try:
        return _formula_from_resource(card)
    except FormalLogicError:
        return None


def logical_expression_for_card(card: CardInstance) -> LogicExpr:
    formula = formula_for_card(card)
    if formula is not None:
        return formula.conclusion
    return LogicExpr.constant(str(getattr(card, "def_id", "") or "UnknownCard"))


def _display_formula(formula: ProofFormula, language: str) -> str:
    def localize(expr: LogicExpr) -> LogicExpr:
        if expr.kind == "const" and expr.value in CARD_DEFS:
            card_def = CARD_DEFS[expr.value]
            name = card_def.name_cn if language == "zh" else card_def.name_en
            return LogicExpr.constant(f"[{name}]")
        if not expr.children:
            return expr
        return LogicExpr(expr.kind, expr.value, tuple(localize(child) for child in expr.children))

    localized = ProofFormula(
        tuple(localize(premise) for premise in formula.premises),
        localize(formula.conclusion),
    )
    return format_formula(localized)


def set_card_formula(card: CardInstance, formula: ProofFormula, *, remember_original: bool = True) -> None:
    validate_formula(formula)
    custom = card.custom_vars if isinstance(card.custom_vars, dict) else {}
    card.custom_vars = custom
    if remember_original and "formal_logic_original_formula" not in custom:
        original = formula_for_card(card)
        custom["formal_logic_original_formula"] = formula_to_data(original or formula)
    custom["formal_logic_formula"] = formula_to_data(formula)
    if _card_formal_resource(card).get("formula_name", False) or card.def_id == GENERATED_THEOREM_ID:
        custom["display_name_cn"] = _display_formula(formula, "zh")
        custom["display_name_en"] = _display_formula(formula, "en")


def _reset_card_formula(card: CardInstance) -> None:
    custom = getattr(card, "custom_vars", {}) or {}
    raw = custom.get("formal_logic_original_formula")
    if isinstance(raw, Mapping):
        set_card_formula(card, formula_from_data(raw), remember_original=False)
    custom.pop("formal_logic_bindings", None)
    custom.pop("formal_logic_binding_cards", None)
    custom.pop("formal_logic_stage", None)
    card.disabled_flags.discard("rebound")


def _find_card(engine, instance_id: Any) -> Optional[CardInstance]:
    try:
        iid = int(instance_id)
    except (TypeError, ValueError):
        return None
    finder = getattr(engine, "_find_card_by_instance_id", None)
    if callable(finder):
        return finder(iid)
    for player in getattr(engine, "players", []) or []:
        for zone_name in ("hand", "deck", "discard", "exile"):
            for card in getattr(player, zone_name, []) or []:
                if int(getattr(card, "instance_id", -1)) == iid:
                    return card
        for equipment in getattr(player, "equipment", []) or []:
            card = getattr(equipment, "card_instance", None)
            if card is not None and int(getattr(card, "instance_id", -1)) == iid:
                return card
    return None


def _find_card_location(engine, card: CardInstance) -> Tuple[Optional[int], Optional[str]]:
    finder = getattr(engine, "_find_card_location", None)
    if callable(finder):
        owner_id, zone_name, _ = finder(card)
        return owner_id, zone_name
    for owner_id, player in enumerate(getattr(engine, "players", []) or []):
        for zone_name in ("hand", "deck", "discard", "exile"):
            if card in (getattr(player, zone_name, []) or []):
                return owner_id, zone_name
    return None, None


def _detach_card(engine, card: CardInstance) -> Tuple[Optional[int], Optional[str]]:
    owner_id, zone_name = _find_card_location(engine, card)
    if owner_id is None or zone_name is None:
        return owner_id, zone_name
    zone = getattr(engine.players[owner_id], zone_name, None)
    if isinstance(zone, list) and card in zone:
        zone.remove(card)
    return owner_id, zone_name


def _move_card(engine, card: CardInstance, owner_id: int, zone: str, *, trigger_hand: bool = True) -> None:
    _detach_card(engine, card)
    player = engine.players[owner_id]
    if zone == "hand":
        player.add_to_hand(card, trigger_enter_hand=trigger_hand)
    elif zone == "deck_top":
        player.deck.insert(0, card)
    elif zone == "deck":
        player.deck.append(card)
    elif zone == "exile":
        engine._put_card_in_exile(owner_id, card)
    else:
        engine._discard_card(player, card)


def _selectable(card: CardInstance) -> bool:
    return "sublime" not in getattr(card, "flags", set())


def _zone_cards(engine, owner_id: int, zone: str) -> List[CardInstance]:
    if not _valid_player(engine, owner_id):
        return []
    if zone == "equipment":
        return [eq.card_instance for eq in engine.players[owner_id].equipment]
    value = getattr(engine.players[owner_id], zone, [])
    return list(value) if isinstance(value, list) else []


def _serialize_actions(actions: Iterable[dict]) -> List[dict]:
    return [copy.deepcopy(action) for action in actions if isinstance(action, dict)]


def _action_value(state: dict, value: Any, default=None):
    """Resolve a JSON-serializable action argument.

    Complex formal-logic effects are deliberately expressed as small actions. A
    ``{"var": "name"}`` reference lets a later action consume a value produced
    before a pause without putting live Python objects in the saved state.
    """
    if isinstance(value, Mapping) and set(value) == {"var"}:
        return _current_value(state, str(value.get("var") or ""), default)
    return default if value is None else value


def _action_card(engine, state: dict, action: dict, key: str = "instance_id") -> Optional[CardInstance]:
    value = action.get(key)
    if value is None:
        value = action.get(f"{key}_ref")
    return _find_card(engine, _action_value(state, value))


def _action_player_id(state: dict, value: Any, default: int = 0) -> int:
    resolved = _action_value(state, value, default)
    try:
        return int(resolved)
    except (TypeError, ValueError):
        return int(default)


def _action_formula(state: dict, value: Any) -> Optional[ProofFormula]:
    resolved = _action_value(state, value)
    if isinstance(resolved, ProofFormula):
        return resolved
    if isinstance(resolved, Mapping):
        return formula_from_data(resolved)
    if isinstance(resolved, str) and resolved:
        return parse_formula(resolved)
    return None


def _automatic_play_target(engine, player_id: int, card: CardInstance) -> Tuple[int, dict]:
    """Choose a deterministic target for a card that must be played automatically."""
    flags = set(engine._effective_card_flags(card))
    if engine._card_is_self_only(card):
        target_id = player_id
    elif "wide_strike" in flags or getattr(card, "card_type", "") == "guard":
        target_id = -1
    else:
        needs_target = (
            getattr(card, "card_type", "") == "thorn"
            or engine._v2_play_requires_choice_target(card)
            or engine._root_play_requires_owner_target(card)
        )
        if not needs_target:
            target_id = -1
        else:
            target_id = engine._default_auto_target_choice(
                player_id,
                allow_self="self_target" in flags,
            )
    choice: dict = {}
    if target_id >= 0:
        choice = {
            "target_player_id": target_id,
            "target_player": target_id,
            "target_id": target_id,
        }
    return target_id, choice


def _can_automatically_play(engine, player_id: int, card: CardInstance) -> Tuple[bool, str]:
    previous_actor = getattr(engine, "_allow_out_of_turn_auto_play_for", None)
    engine._allow_out_of_turn_auto_play_for = player_id
    try:
        return engine.can_play_card(player_id, card)
    finally:
        engine._allow_out_of_turn_auto_play_for = previous_actor


def _merge_card_custom_vars(card: CardInstance, values: Any) -> None:
    if not isinstance(values, Mapping):
        return
    if not isinstance(card.custom_vars, dict):
        card.custom_vars = {}
    for key, value in values.items():
        card.custom_vars[str(key)] = copy.deepcopy(value)


def start_formal_logic_actions(
    engine,
    player_id: int,
    actions: Sequence[dict],
    *,
    variables: Optional[Dict[str, Any]] = None,
) -> dict:
    state = {
        "player_id": int(player_id),
        "actions": _serialize_actions(actions),
        "vars": copy.deepcopy(variables or {}),
        "steps": 0,
    }
    return _run_formal_logic_actions(engine, state)


def resume_formal_logic_actions(engine, state: dict, clean: dict, *, cancelled: bool = False) -> dict:
    state = copy.deepcopy(state or {})
    waiting = state.pop("waiting", {}) if isinstance(state.get("waiting"), dict) else {}
    save_as = str(waiting.get("save_as") or "choice")
    if cancelled:
        state.setdefault("vars", {})[save_as] = copy.deepcopy(waiting.get("cancel_value"))
        state["actions"] = _serialize_actions(waiting.get("on_cancel") or []) + _serialize_actions(state.get("actions") or [])
    else:
        values = clean.get("values") if isinstance(clean.get("values"), dict) else {}
        control_id = str(waiting.get("control_id") or "choice")
        state.setdefault("vars", {})[save_as] = copy.deepcopy(values.get(control_id))
        state.setdefault("vars", {})[f"{save_as}_button"] = str(clean.get("button") or "confirm")
    return _run_formal_logic_actions(engine, state)


def _pause_for_choice(engine, state: dict, action: dict) -> dict:
    from mod_runtime_v2 import _sanitize_ui_component

    player_id = int(action.get("player_id", state.get("player_id", 0)))
    control_id = str(action.get("control_id") or "choice")
    choice_type = str(action.get("choice_type") or "card")
    control: Dict[str, Any]
    if choice_type == "player":
        control = {
            "id": control_id,
            "type": "player_picker",
            "label_cn": action.get("label_cn", "选择一个玩家"),
            "label_en": action.get("label_en", "Choose a player"),
            "allowed_player_ids": list(action.get("allowed_player_ids") or []),
        }
    elif choice_type == "catalog_card":
        control = {
            "id": control_id,
            "type": "card_catalog_picker",
            "label_cn": action.get("label_cn", "选择一张牌"),
            "label_en": action.get("label_en", "Choose a card"),
            "options": copy.deepcopy(action.get("options") or []),
        }
    elif choice_type == "option":
        control = {
            "id": control_id,
            "type": "select",
            "label_cn": action.get("label_cn", "选择一项"),
            "label_en": action.get("label_en", "Choose one"),
            "options": copy.deepcopy(action.get("options") or []),
        }
    else:
        multi = bool(action.get("multi"))
        control = {
            "id": control_id,
            "type": "multi_card_picker" if multi else "card_picker",
            "label_cn": action.get("label_cn", "选择牌"),
            "label_en": action.get("label_en", "Choose cards"),
            "target": int(action.get("owner_id", player_id)),
            "zone": str(action.get("zone") or "hand"),
            "allowed_instance_ids": list(action.get("allowed_instance_ids") or []),
        }
        if multi:
            control["min_select"] = int(action.get("min_select", 0))
            control["max_select"] = int(action.get("max_select", len(control["allowed_instance_ids"])))
    component = {
        "type": "modal",
        "title_cn": str(action.get("title_cn") or "形式逻辑推理"),
        "title_en": str(action.get("title_en") or "Formal Logic"),
        "text_cn": str(action.get("text_cn") or ""),
        "text_en": str(action.get("text_en") or ""),
        "controls": [control],
        "buttons": [
            {"id": "confirm", "text_cn": "确认", "text_en": "Confirm", "role": "confirm"},
            {"id": "cancel", "text_cn": "取消", "text_en": "Cancel", "role": "cancel"},
        ],
        "style": {"accent": "formal-logic"},
    }
    context = {"source_player": player_id, "target_player": player_id, "vars": {}}
    component = _sanitize_ui_component(engine, context, component)
    state["waiting"] = {
        "save_as": str(action.get("save_as") or "choice"),
        "control_id": control_id,
        "cancel_value": copy.deepcopy(action.get("cancel_value")),
        "on_cancel": _serialize_actions(action.get("on_cancel") or []),
    }
    pause = {
        "request_id": str(uuid.uuid4()),
        "component": component,
        "target_player": player_id,
        "timeout_ms": max(0, int(action.get("timeout_ms", 60000) or 0)),
        "context": context,
        "resume_kind": "formal_logic",
        "resume_state": state,
    }
    display_card = _find_card(engine, action.get("display_card_instance_id"))
    engine._store_v2_ui_pause(pause, display_card)
    return {"success": True, "needs_v2_ui": True}


def _run_formal_logic_actions(engine, state: dict) -> dict:
    actions = state.get("actions") if isinstance(state.get("actions"), list) else []
    while actions:
        state["steps"] = int(state.get("steps", 0) or 0) + 1
        if state["steps"] > MAX_ACTIONS:
            raise FormalLogicError("形式逻辑动作数量超过限制")
        action = actions.pop(0)
        if not isinstance(action, dict):
            continue
        op = str(action.get("op") or "")
        if op == "choose":
            return _pause_for_choice(engine, state, action)
        if op == "set_var":
            name = str(action.get("name") or "")
            if name:
                state.setdefault("vars", {})[name] = copy.deepcopy(
                    _action_value(state, action.get("value"))
                )
            continue
        if op == "snapshot_card":
            card = _action_card(engine, state, action)
            save_as = str(action.get("save_as") or "card_snapshot")
            state.setdefault("vars", {})[save_as] = card.to_dict() if card is not None else None
            continue
        if op == "log":
            message = str(action.get("message") or "")
            if message:
                engine.log_msg(message)
            continue
        if op == "add_armor":
            target_id = _action_player_id(
                state, action.get("target_id"), int(state.get("player_id", 0))
            )
            if _valid_player(engine, target_id):
                amount = max(0, int(action.get("amount", 0) or 0))
                engine.players[target_id].armor += amount
                note_peak = getattr(engine, "_note_achievement_status_peak", None)
                if callable(note_peak):
                    note_peak(target_id)
                if action.get("log", True) and amount:
                    engine.log_msg(str(action.get("message") or f"{engine.pn(target_id)}获得{amount}护甲"))
            continue
        if op == "heal":
            target_id = _action_player_id(
                state, action.get("target_id"), int(state.get("player_id", 0))
            )
            if _valid_player(engine, target_id):
                amount = max(0, int(_action_value(state, action.get("amount"), 0) or 0))
                if amount:
                    before = int(engine.players[target_id].health)
                    engine.players[target_id].heal(amount)
                    healed = max(0, int(engine.players[target_id].health) - before)
                    save_as = str(action.get("save_as") or "")
                    if save_as:
                        state.setdefault("vars", {})[save_as] = healed
                    if action.get("log", False) and healed:
                        engine.log_msg(str(action.get("message") or f"{engine.pn(target_id)}回复{healed}H"))
            continue
        if op == "move_card":
            card = _action_card(engine, state, action)
            owner_id = _action_player_id(
                state, action.get("owner_id"), int(state.get("player_id", 0))
            )
            if card is not None and _valid_player(engine, owner_id):
                _move_card(
                    engine,
                    card,
                    owner_id,
                    str(action.get("zone") or "discard"),
                    trigger_hand=bool(action.get("trigger_hand", True)),
                )
            continue
        if op == "remove_card":
            card = _action_card(engine, state, action)
            if card is not None:
                _detach_card(engine, card)
            continue
        if op == "create_card":
            snapshot = _action_value(state, action.get("snapshot"))
            def_id = str(_action_value(state, action.get("def_id"), "") or "")
            if isinstance(snapshot, Mapping):
                card = _fresh_card_copy_from_dict(dict(snapshot), def_id)
            elif def_id in CARD_DEFS:
                card = CardInstance(def_id)
            else:
                continue
            _merge_card_custom_vars(card, _action_value(state, action.get("custom_vars"), {}))
            formula = _action_formula(state, action.get("formula"))
            if formula is not None:
                set_card_formula(card, formula, remember_original=False)
                if bool(action.get("formula_is_original", False)):
                    card.custom_vars["formal_logic_original_formula"] = formula_to_data(formula)
            for flag in _action_value(state, action.get("add_instance_flags"), []) or []:
                card.instance_flags.add(str(flag))
            for flag in _action_value(state, action.get("add_disabled_flags"), []) or []:
                card.disabled_flags.add(str(flag))
            owner_id = _action_player_id(
                state, action.get("owner_id"), int(state.get("player_id", 0))
            )
            if _valid_player(engine, owner_id):
                _move_card(
                    engine,
                    card,
                    owner_id,
                    str(action.get("zone") or "hand"),
                    trigger_hand=bool(action.get("trigger_hand", True)),
                )
                save_as = str(action.get("save_as") or "created_card")
                state.setdefault("vars", {})[save_as] = int(card.instance_id)
            continue
        if op == "set_card_formula":
            card = _action_card(engine, state, action)
            formula = _action_formula(state, action.get("formula"))
            if card is not None and formula is not None:
                set_card_formula(card, formula, remember_original=bool(action.get("remember_original", True)))
                if bool(action.get("formula_is_original", False)):
                    card.custom_vars["formal_logic_original_formula"] = formula_to_data(formula)
            continue
        if op == "reset_formal_card":
            card = _action_card(engine, state, action)
            if card is not None:
                _reset_card_formula(card)
            continue
        if op in ("add_card_flag", "remove_card_flag"):
            card = _action_card(engine, state, action)
            flag = str(_action_value(state, action.get("flag"), "") or "")
            if card is not None and flag:
                flags = card.disabled_flags if str(action.get("scope") or "instance") == "disabled" else card.instance_flags
                (flags.add if op == "add_card_flag" else flags.discard)(flag)
            continue
        if op == "set_card_var":
            card = _action_card(engine, state, action)
            name = str(action.get("name") or "")
            if card is not None and name:
                value = copy.deepcopy(_action_value(state, action.get("value")))
                if str(action.get("mode") or "set") == "add":
                    value = int(card.custom_vars.get(name, 0) or 0) + int(value or 0)
                card.custom_vars[name] = value
            continue
        if op == "set_card_cost":
            card = _action_card(engine, state, action)
            if card is not None:
                if "cost_e" in action:
                    card.cost_e_override = int(_action_value(state, action.get("cost_e"), 0) or 0)
                if "cost_m" in action:
                    card.cost_m_override = int(_action_value(state, action.get("cost_m"), 0) or 0)
            continue
        if op == "set_player_var":
            player_id = _action_player_id(
                state, action.get("player_id"), int(state.get("player_id", 0))
            )
            name = str(action.get("name") or "")
            if _valid_player(engine, player_id) and name:
                player_vars = engine.players[player_id].custom_vars
                value = copy.deepcopy(_action_value(state, action.get("value")))
                mode = str(action.get("mode") or "set")
                if mode == "add":
                    value = int(player_vars.get(name, 0) or 0) + int(value or 0)
                elif mode == "append":
                    current = player_vars.setdefault(name, [])
                    if isinstance(current, list):
                        current.append(value)
                        continue
                player_vars[name] = value
            continue
        if op == "set_status":
            player_id = _action_player_id(
                state, action.get("player_id"), int(state.get("player_id", 0))
            )
            status_id = str(action.get("status_id") or "")
            if _valid_player(engine, player_id) and status_id:
                statuses = engine.players[player_id].custom_statuses
                amount = int(_action_value(state, action.get("amount"), 0) or 0)
                if str(action.get("mode") or "set") == "add":
                    amount += int(statuses.get(status_id, 0) or 0)
                setter = getattr(engine, "_set_custom_status_value", None)
                if callable(setter):
                    setter(player_id, status_id, amount)
                elif amount > 0:
                    statuses[status_id] = amount
                else:
                    statuses.pop(status_id, None)
                payload_key = str(action.get("payload_key") or "")
                if payload_key:
                    engine.players[player_id].custom_vars[payload_key] = copy.deepcopy(
                        _action_value(state, action.get("payload"), {})
                    )
            continue
        if op == "adjust_player_stat":
            player_id = _action_player_id(
                state, action.get("player_id"), int(state.get("player_id", 0))
            )
            attr = str(action.get("attr") or "")
            if _valid_player(engine, player_id) and attr in {"health", "elixir", "magic", "armor"}:
                player = engine.players[player_id]
                amount = int(_action_value(state, action.get("amount"), 0) or 0)
                setattr(player, attr, int(getattr(player, attr, 0) or 0) + amount)
            continue
        if op == "swap_player_stats":
            player_id = _action_player_id(
                state, action.get("player_id"), int(state.get("player_id", 0))
            )
            left = str(_action_value(state, action.get("left"), "") or "")
            right = str(_action_value(state, action.get("right"), "") or "")
            allowed = {"health", "elixir", "magic"}
            if _valid_player(engine, player_id) and left in allowed and right in allowed and left != right:
                player = engine.players[player_id]
                left_value, right_value = getattr(player, left), getattr(player, right)
                setattr(player, left, right_value)
                setattr(player, right, left_value)
            continue
        if op == "clear_status":
            player_id = _action_player_id(
                state, action.get("player_id"), int(state.get("player_id", 0))
            )
            if _valid_player(engine, player_id):
                _clear_logic_status(
                    engine.players[player_id],
                    str(action.get("status_id") or ""),
                    str(action.get("payload_key") or ""),
                )
            continue
        if op == "spend_resource":
            player_id = _action_player_id(
                state, action.get("player_id"), int(state.get("player_id", 0))
            )
            amount = max(0, int(_action_value(state, action.get("amount"), 0) or 0))
            resource = str(action.get("resource") or "elixir")
            if resource == "e":
                resource = "elixir"
            elif resource == "m":
                resource = "magic"
            if _valid_player(engine, player_id) and amount:
                engine._spend_resource(player_id, resource, amount, _action_card(engine, state, action, "card_instance_id"))
            continue
        if op == "place_equipment":
            card = _action_card(engine, state, action)
            owner_id = _action_player_id(
                state, action.get("owner_id"), int(state.get("player_id", 0))
            )
            target_id = _action_player_id(state, action.get("target_id"), owner_id)
            if card is not None and _valid_player(engine, owner_id) and _valid_player(engine, target_id):
                engine._atomic_place_as_equip(
                    owner_id,
                    card,
                    {"owner": owner_id, "effect_target": target_id},
                    "",
                    {"target_player_id": target_id},
                    {"target_id": target_id},
                )
            continue
        if op == "destroy_equipment":
            card = _action_card(engine, state, action)
            owner_id = _action_player_id(
                state, action.get("owner_id"), int(state.get("player_id", 0))
            )
            if card is not None and _valid_player(engine, owner_id):
                equipment = engine.players[owner_id].find_equipment(card.instance_id)
                if equipment is not None:
                    engine._destroy_equipment(
                        owner_id,
                        equipment,
                        check_protection=bool(action.get("check_protection", False)),
                    )
            continue
        if op == "play_card":
            card = _action_card(engine, state, action)
            player_id = _action_player_id(
                state, action.get("player_id"), int(state.get("player_id", 0))
            )
            if card is not None and _valid_player(engine, player_id):
                target_id = _action_player_id(state, action.get("target_id"), -1)
                choice = copy.deepcopy(_action_value(state, action.get("choice"), {}) or {})
                if target_id >= 0:
                    choice.update({"target_player_id": target_id, "target_player": target_id, "target_id": target_id})
                previous_actor = getattr(engine, "_allow_out_of_turn_auto_play_for", None)
                previous_choice = getattr(engine, "_auto_resolve_choices_for", None)
                previous_no_cost = getattr(engine, "_auto_play_no_cost_for", None)
                engine._allow_out_of_turn_auto_play_for = player_id
                engine._auto_resolve_choices_for = player_id
                if bool(action.get("no_cost", False)):
                    engine._auto_play_no_cost_for = player_id
                try:
                    result = engine.play_card(player_id, card.instance_id, choice)
                finally:
                    engine._allow_out_of_turn_auto_play_for = previous_actor
                    engine._auto_resolve_choices_for = previous_choice
                    engine._auto_play_no_cost_for = previous_no_cost
                save_as = str(action.get("save_as") or "play_result")
                state.setdefault("vars", {})[save_as] = copy.deepcopy(result)
            continue
        if op == "call":
            handler = _ACTION_HANDLERS.get(str(action.get("name") or ""))
            if handler is None:
                raise FormalLogicError(f"未知形式逻辑动作: {action.get('name')}")
            follow_up = handler(engine, state, action)
            if isinstance(follow_up, list):
                actions[0:0] = _serialize_actions(follow_up)
            elif isinstance(follow_up, dict) and follow_up.get("needs_v2_ui"):
                return follow_up
            continue
        raise FormalLogicError(f"未知形式逻辑原子操作: {op}")
    return {"success": True}


def _current_value(state: dict, name: str, default=None):
    return (state.get("vars") if isinstance(state.get("vars"), dict) else {}).get(name, default)


def _candidate_cards(engine, owner_id: int, predicate, zones: Sequence[str] = ("hand",)) -> List[CardInstance]:
    result: List[CardInstance] = []
    for zone in zones:
        for card in _zone_cards(engine, owner_id, zone):
            if len(result) >= MAX_DYNAMIC_CANDIDATES:
                return result
            if _selectable(card) and predicate(card):
                result.append(card)
    return result


def _is_implication_card(card: CardInstance) -> bool:
    formula = formula_for_card(card)
    return bool(formula and formula.conclusion.kind == "binary" and formula.conclusion.value == ">")


def _is_inverse_deduction_candidate(card: CardInstance) -> bool:
    formula = formula_for_card(card)
    if formula is None:
        return False
    antecedents, _ = implication_chain(formula.conclusion)
    return len(antecedents) >= 2


def _formal_formula_cards(engine, owner_id: int) -> List[CardInstance]:
    return _candidate_cards(engine, owner_id, lambda card: formula_for_card(card) is not None)


def _clone_with_formula(source: CardInstance, formula: ProofFormula) -> CardInstance:
    clone = _fresh_card_copy_from_dict(source.to_dict(), source.def_id)
    set_card_formula(clone, formula)
    clone.custom_vars["formal_logic_binding_cards"] = copy.deepcopy(
        (getattr(source, "custom_vars", {}) or {}).get("formal_logic_binding_cards", {})
    )
    return clone


def _handle_contraposition(engine, state: dict, action: dict) -> List[dict]:
    owner_id = int(state.get("player_id", 0))
    selected = _find_card(engine, _current_value(state, str(action.get("selected_var") or "selected_card")))
    if selected is None or selected not in engine.players[owner_id].hand or not _is_implication_card(selected):
        engine.log_msg("没有可进行逆否变换的牌")
        return []
    transformed = transform_contraposition(formula_for_card(selected))
    transformed_name = format_formula(transformed)
    return [
        {"op": "snapshot_card", "instance_id": selected.instance_id, "save_as": "contraposition_source"},
        {"op": "move_card", "instance_id": selected.instance_id, "owner_id": owner_id, "zone": "discard"},
        {
            "op": "create_card",
            "snapshot": {"var": "contraposition_source"},
            "formula": formula_to_data(transformed),
            "formula_is_original": True,
            "add_instance_flags": [INFERENCE_EXILE_FLAG],
            "owner_id": owner_id,
            "zone": "hand",
            "save_as": "contraposition_result",
        },
        {"op": "log", "message": f"{engine.pn(owner_id)}将{selected.name_cn}变换为{transformed_name}"},
    ]


def _handle_inverse_deduction(engine, state: dict, action: dict) -> List[dict]:
    owner_id = int(state.get("player_id", 0))
    selected = _find_card(engine, _current_value(state, str(action.get("selected_var") or "selected_card")))
    if selected is None or selected not in engine.players[owner_id].hand or not _is_inverse_deduction_candidate(selected):
        engine.log_msg("没有可应用逆演绎元定理的牌")
        return []
    response_actions = _deduction_response_actions(engine, owner_id, selected, "inverse_deduction_finish")
    if response_actions:
        state.setdefault("vars", {})["inverse_selected_instance_id"] = selected.instance_id
        return response_actions
    return _finish_inverse_deduction(engine, state, {"selected_instance_id": selected.instance_id})


def _finish_inverse_deduction(engine, state: dict, action: dict) -> List[dict]:
    owner_id = int(state.get("player_id", 0))
    selected_id = action.get("selected_instance_id", _current_value(state, "inverse_selected_instance_id"))
    selected = _find_card(engine, selected_id)
    if selected is None or selected not in engine.players[owner_id].hand:
        return []
    if bool(_current_value(state, "deduction_invalidated", False)):
        engine.log_msg("逆演绎元定理被反制")
        return []
    transformed = transform_inverse_deduction(formula_for_card(selected))
    transformed_name = format_formula(transformed)
    return [
        {"op": "snapshot_card", "instance_id": selected.instance_id, "save_as": "inverse_source"},
        {"op": "move_card", "instance_id": selected.instance_id, "owner_id": owner_id, "zone": "exile"},
        {
            "op": "create_card",
            "snapshot": {"var": "inverse_source"},
            "formula": formula_to_data(transformed),
            "formula_is_original": True,
            "owner_id": owner_id,
            "zone": "hand",
            "save_as": "inverse_result",
        },
        {"op": "log", "message": f"{engine.pn(owner_id)}通过逆演绎元定理得到{transformed_name}"},
    ]


def _eligible_deduction_responders(engine, actor_id: int) -> List[Tuple[int, CardInstance]]:
    result: List[Tuple[int, CardInstance]] = []
    enemies = (
        list(engine.get_all_enemies(actor_id))
        if hasattr(engine, "get_all_enemies")
        else [1 - actor_id]
    )
    for player_id in enemies:
        if not _valid_player(engine, player_id):
            continue
        for card in engine.players[player_id].hand:
            if card.def_id == DEDUCTION_META_ID and engine._can_pay_counter_card(player_id, card):
                result.append((player_id, card))
    return result


def _deduction_response_actions(engine, actor_id: int, selected: CardInstance, resume_name: str) -> List[dict]:
    responders = _eligible_deduction_responders(engine, actor_id)
    if not responders:
        return []
    responder_id, response_card = responders[0]
    return [
        {
            "op": "choose",
            "choice_type": "card",
            "player_id": responder_id,
            "owner_id": responder_id,
            "zone": "hand",
            "allowed_instance_ids": [response_card.instance_id],
            "save_as": "deduction_response_card",
            "title_cn": "演绎元定理",
            "title_en": "Deduction Metatheorem",
            "text_cn": "可以使用演绎元定理响应本次公式变化。",
            "text_en": "You may respond to this formula change.",
            "cancel_value": None,
            "timeout_ms": 30000,
        },
        {
            "op": "call",
            "name": "deduction_response_resolve",
            "actor_id": actor_id,
            "selected_instance_id": selected.instance_id,
            "resume_name": resume_name,
        },
    ]


def _handle_deduction_response(engine, state: dict, action: dict) -> List[dict]:
    response_id = _current_value(state, "deduction_response_card")
    response_card = _find_card(engine, response_id)
    selected = _find_card(engine, action.get("selected_instance_id"))
    if response_card is None or selected is None:
        return [{"op": "call", "name": str(action.get("resume_name") or "inverse_deduction_finish")}]
    responder_id, zone = _find_card_location(engine, response_card)
    if zone != "hand" or not _valid_player(engine, responder_id):
        return [{"op": "call", "name": str(action.get("resume_name") or "inverse_deduction_finish")}]
    cost_e = max(0, int(response_card.cost_e))
    cost_m = max(0, int(response_card.cost_m))
    player = engine.players[responder_id]
    if player.elixir < cost_e or player.magic < cost_m:
        return [{"op": "call", "name": str(action.get("resume_name") or "inverse_deduction_finish")}]
    operations: List[dict] = [
        {
            "op": "spend_resource", "player_id": responder_id, "resource": "elixir",
            "amount": cost_e, "card_instance_id": response_card.instance_id,
        },
        {
            "op": "spend_resource", "player_id": responder_id, "resource": "magic",
            "amount": cost_m, "card_instance_id": response_card.instance_id,
        },
        {"op": "move_card", "instance_id": response_card.instance_id, "owner_id": responder_id, "zone": "discard"},
        {"op": "log", "message": f"{engine.pn(responder_id)}使用{response_card.name_cn}进行反制"},
    ]
    resume_name = str(action.get("resume_name") or "inverse_deduction_finish")
    formula = formula_for_card(selected)
    if resume_name == "inverse_deduction_finish":
        operations.append({"op": "set_var", "name": "deduction_invalidated", "value": True})
    elif formula is not None and formula.premises:
        operations.append({
            "op": "set_card_formula", "instance_id": selected.instance_id,
            "formula": formula_to_data(transform_deduction(formula, 0)),
        })
    elif formula is not None and formula.conclusion.kind == "binary" and formula.conclusion.value == ">":
        fresh = LogicExpr.variable(next_fresh_variable(formula))
        operations.append({
            "op": "set_card_formula", "instance_id": selected.instance_id,
            "formula": formula_to_data(
                ProofFormula(formula.premises, LogicExpr.binary(">", fresh, formula.conclusion))
            ),
        })
    else:
        operations.append({"op": "set_var", "name": "deduction_invalidated", "value": True})
    operations.append({"op": "call", "name": resume_name})
    return operations


def _handle_macro_create(engine, state: dict, action: dict) -> List[dict]:
    owner_id = int(state.get("player_id", 0))
    selected = _find_card(engine, _current_value(state, str(action.get("selected_var") or "selected_card")))
    if selected is None or selected not in engine.players[owner_id].hand or not _macro_candidate(engine, owner_id, selected):
        engine.log_msg("没有可进行宏定义的牌")
        return []
    snapshot = selected.to_dict()
    macro_vars = {
        "formal_logic_macro_source": snapshot,
        "formal_logic_macro_source_def_id": selected.def_id,
        "formal_logic_macro_heavy": 0,
        "display_name_cn": f"宏定义：{selected.name_cn}",
        "display_name_en": f"Macro: {selected.name_en}",
    }
    return [
        {"op": "move_card", "instance_id": selected.instance_id, "owner_id": owner_id, "zone": "exile"},
        {
            "op": "create_card", "snapshot": snapshot, "owner_id": owner_id,
            "zone": "discard", "trigger_hand": False, "save_as": "macro_discard_copy",
        },
        {
            "op": "create_card", "def_id": MACRO_EQUIPMENT_ID, "owner_id": owner_id,
            "zone": "hand", "trigger_hand": False, "custom_vars": macro_vars,
            "save_as": "macro_equipment",
        },
        {
            "op": "place_equipment", "instance_id": {"var": "macro_equipment"},
            "owner_id": owner_id, "target_id": owner_id,
        },
        {"op": "log", "message": f"{engine.pn(owner_id)}将{selected.name_cn}定义为宏"},
    ]


def _macro_candidate(engine, owner_id: int, card: CardInstance) -> bool:
    if not _selectable(card) or card.def_id in ("formal_logic:macro", MACRO_EQUIPMENT_ID):
        return False
    for equipment in engine.players[owner_id].equipment:
        custom = getattr(equipment.card_instance, "custom_vars", {}) or {}
        if custom.get("formal_logic_macro_source_def_id") == card.def_id:
            return False
    return True


def _handle_macro_trigger(engine, state: dict, action: dict) -> List[dict]:
    owner_id = int(action.get("owner_id", state.get("player_id", 0)))
    equipment_card = _find_card(engine, action.get("equipment_instance_id"))
    if equipment_card is None:
        return []
    custom = getattr(equipment_card, "custom_vars", {}) or {}
    snapshot = custom.get("formal_logic_macro_source")
    if not isinstance(snapshot, dict):
        return []
    source = _fresh_card_copy_from_dict(snapshot, str(snapshot.get("def_id") or ""))
    heavy = max(0, int(custom.get("formal_logic_macro_heavy", 0) or 0))
    proxy_snapshot = source.to_dict()
    proxy_snapshot["temp_heavy_value"] = max(int(proxy_snapshot.get("temp_heavy_value", 0) or 0), heavy)
    proxy_vars = {
        "formal_logic_proxy": True,
        "formal_logic_macro_equipment_instance_id": equipment_card.instance_id,
        "formal_logic_proxy_formula": formula_to_data(
            formula_for_card(source) or constant_card_formula(source.def_id)
        ),
    }
    return [
        {
            "op": "create_card", "snapshot": proxy_snapshot, "owner_id": owner_id,
            "zone": "hand", "custom_vars": proxy_vars, "add_instance_flags": ["void"],
            "save_as": "macro_proxy",
        },
        {"op": "log", "message": f"{engine.pn(owner_id)}通过宏定义获得{source.name_cn}"},
    ]


def _handle_mp(engine, state: dict, action: dict) -> List[dict]:
    owner_id = int(state.get("player_id", 0))
    selected_ids = _current_value(state, str(action.get("selected_var") or "selected_cards"), [])
    if not isinstance(selected_ids, list) or len(selected_ids) != 2:
        engine.log_msg("mp需要选择两张公式牌")
        return []
    first = _find_card(engine, selected_ids[0])
    second = _find_card(engine, selected_ids[1])
    if first is None or second is None or first not in engine.players[owner_id].hand or second not in engine.players[owner_id].hand:
        return []
    formula = None
    for left, right in ((first, second), (second, first)):
        try:
            formula = modus_ponens(formula_for_card(left), formula_for_card(right))
            break
        except (FormalLogicError, TypeError):
            continue
    if formula is None:
        engine.log_msg("所选公式无法使用mp合一")
        return []
    generated = _special_card_for_formula(formula) or _new_generated_theorem(formula)
    equipment = _find_card(engine, action.get("equipment_instance_id"))
    operations = [
        {
            "op": "create_card", "snapshot": generated.to_dict(), "owner_id": owner_id,
            "zone": "hand", "save_as": "mp_result",
        }
    ]
    if equipment is not None:
        operations.append({
            "op": "destroy_equipment", "instance_id": equipment.instance_id,
            "owner_id": owner_id, "check_protection": False,
        })
    operations.append({"op": "log", "message": f"{engine.pn(owner_id)}通过mp得到{generated.name_cn}"})
    return operations


def _new_generated_theorem(formula: ProofFormula) -> CardInstance:
    card = CardInstance(GENERATED_THEOREM_ID)
    set_card_formula(card, canonicalize_variables(formula))
    card.custom_vars["formal_logic_required_substitutions"] = len(formula_variables(formula))
    return card


def _special_card_for_formula(formula: ProofFormula) -> Optional[CardInstance]:
    for card_def in CARD_DEFS.values():
        formal = (getattr(card_def, "v2_resource", {}) or {}).get("formal_logic")
        if not isinstance(formal, dict) or not formal.get("special_formula") or not formal.get("formula"):
            continue
        try:
            if formulas_special_equivalent(parse_formula(str(formal["formula"])), formula):
                return CardInstance(card_def.id)
        except FormalLogicError:
            continue
    return None


def _handle_add_selected_catalog_card(engine, state: dict, action: dict) -> List[dict]:
    owner_id = int(state.get("player_id", 0))
    def_id = str(_current_value(state, str(action.get("selected_var") or "selected_card_def")) or "")
    if def_id in CARD_DEFS and str(def_id).startswith(f"{MOD_ID}:"):
        return [
            {
                "op": "create_card", "def_id": def_id, "owner_id": owner_id,
                "zone": "hand", "save_as": "mathematician_card",
            },
            {
                "op": "set_player_var", "player_id": owner_id,
                "name": "formal_logic_draw_reduction", "value": 1,
            },
        ]
    return []


def _handle_resume_turn_start(engine, state: dict, action: dict) -> List[dict]:
    player_id = int(state.get("player_id", 0))
    if not _valid_player(engine, player_id) or getattr(engine, "game_over", False):
        return []
    engine._start_player_turn(player_id)
    return []


def _handle_set_cost_zero(engine, state: dict, action: dict) -> List[dict]:
    selected = _find_card(engine, _current_value(state, str(action.get("selected_var") or "selected_card")))
    if selected is None:
        return []
    operations: List[dict] = []
    temporary = bool(action.get("temporary"))
    if action.get("zero_e", True):
        operations.append({
            "op": "set_card_var", "instance_id": selected.instance_id,
            "name": "formal_logic_temporary_cost_e" if temporary else "formal_logic_permanent_cost_e",
            "value": 0,
        })
    if action.get("zero_m", False):
        operations.append({
            "op": "set_card_var", "instance_id": selected.instance_id,
            "name": "formal_logic_temporary_cost_m" if temporary else "formal_logic_permanent_cost_m",
            "value": 0,
        })
    return operations


def _handle_swap_stats(engine, state: dict, action: dict) -> List[dict]:
    player_id = int(state.get("player_id", 0))
    option = str(_current_value(state, str(action.get("selected_var") or "stat_pair")) or "")
    if not _valid_player(engine, player_id):
        return []
    attrs = {"h": "health", "e": "elixir", "m": "magic"}
    parts = option.split("_")
    if len(parts) == 2 and all(part in attrs for part in parts):
        return [{
            "op": "swap_player_stats", "player_id": player_id,
            "left": attrs[parts[0]], "right": attrs[parts[1]],
        }]
    return []


_ACTION_HANDLERS = {
    "contraposition_apply": _handle_contraposition,
    "inverse_deduction_apply": _handle_inverse_deduction,
    "inverse_deduction_finish": _finish_inverse_deduction,
    "deduction_response_resolve": _handle_deduction_response,
    "macro_create": _handle_macro_create,
    "macro_trigger": _handle_macro_trigger,
    "mp_apply": _handle_mp,
    "add_selected_catalog_card": _handle_add_selected_catalog_card,
    "resume_turn_start": _handle_resume_turn_start,
    "set_cost_zero": _handle_set_cost_zero,
    "swap_stats": _handle_swap_stats,
}


def _status_payload(player, key: str) -> Optional[dict]:
    value = (getattr(player, "custom_vars", {}) or {}).get(key)
    return value if isinstance(value, dict) else None


def _clear_logic_status(player, status_id: str, payload_key: str) -> None:
    player.custom_statuses.pop(status_id, None)
    player.custom_vars.pop(payload_key, None)


def _card_snapshot(card: CardInstance, choice: Optional[dict], target_id: int) -> dict:
    return {
        "card": card.to_dict(),
        "choice": copy.deepcopy(choice or {}),
        "target_id": int(target_id),
        "expr": expression_to_data(logical_expression_for_card(card)),
    }


def _grant_substitution(engine, target_id: int, source_card: CardInstance) -> None:
    if not _valid_player(engine, target_id):
        return
    formula = formula_for_card(source_card)
    if formula is None:
        return
    player = engine.players[target_id]
    player.custom_statuses[SUBSTITUTION_STATUS] = 1
    player.custom_vars["formal_logic_substitution_state"] = {
        "source_card_instance_id": int(source_card.instance_id),
        "source_formula": formula_to_data(formula),
    }
    engine.log_msg(f"{engine.pn(target_id)}获得1层代入")


def _matching_premise_cards(engine, player_id: int, premises: Sequence[LogicExpr]) -> bool:
    required_premises = [
        _normalize_inference_expression(premise)
        for premise in premises
        if not _is_inference_negation(premise)
    ]
    if not required_premises:
        return True
    candidates: List[Tuple[LogicExpr, str]] = []
    for card in engine.players[player_id].hand:
        candidates.append((logical_expression_for_card(card), f"card:{card.instance_id}"))
    for equipment in engine.players[player_id].equipment:
        custom = getattr(equipment.card_instance, "custom_vars", {}) or {}
        snapshot = custom.get("formal_logic_macro_source")
        if not isinstance(snapshot, dict):
            continue
        try:
            source_card = CardInstance.from_dict(snapshot)
            candidates.append((logical_expression_for_card(source_card), f"macro:{equipment.card_instance.instance_id}"))
        except Exception:
            continue

    def assign(index: int, used: set, bindings: Dict[str, LogicExpr]) -> bool:
        if index >= len(required_premises):
            return True
        for candidate, identity in candidates:
            if identity in used:
                continue
            next_bindings = expressions_match(required_premises[index], candidate, bindings)
            if next_bindings is None:
                continue
            used.add(identity)
            if assign(index + 1, used, next_bindings):
                return True
            used.remove(identity)
        return False

    return assign(0, set(), {})


def _normalize_inference_expression(expr: LogicExpr) -> LogicExpr:
    current = expr
    while (
        current.kind == "unary"
        and current.value == "¬"
        and current.children
        and current.children[0].kind == "unary"
        and current.children[0].value == "¬"
        and current.children[0].children
    ):
        current = current.children[0].children[0]
    return current


def _is_inference_negation(expr: LogicExpr) -> bool:
    normalized = _normalize_inference_expression(expr)
    return normalized.kind == "unary" and normalized.value == "¬"


def _next_inference_index(antecedents: Sequence[LogicExpr], start: int) -> int:
    index = max(0, int(start))
    while index < len(antecedents) and _is_inference_negation(antecedents[index]):
        index += 1
    return index


def _grant_inference(engine, target_id: int, source_card: CardInstance) -> None:
    if not _valid_player(engine, target_id):
        return
    formula = formula_for_card(source_card)
    if formula is None:
        return
    antecedents, conclusion = implication_chain(formula.conclusion)
    player = engine.players[target_id]
    player.custom_statuses[INFERENCE_STATUS] = 1
    inference_index = _next_inference_index(antecedents, 0)
    player.custom_vars["formal_logic_inference_state"] = {
        "source_card_instance_id": int(source_card.instance_id),
        "premises": [expression_to_data(expr) for expr in formula.premises],
        "antecedents": [expression_to_data(expr) for expr in antecedents],
        "conclusion": expression_to_data(conclusion),
        "index": inference_index,
        "binding_cards": copy.deepcopy(
            (getattr(source_card, "custom_vars", {}) or {}).get("formal_logic_binding_cards", {})
        ),
        "inference_exile": INFERENCE_EXILE_FLAG in getattr(source_card, "flags", set()),
        "reset_source_after_inference": str(_card_formal_resource(source_card).get("reset_mode") or "discard") == "after_inference",
    }
    engine.log_msg(f"{engine.pn(target_id)}获得1层推理")
    if inference_index >= len(antecedents):
        start_formal_logic_actions(
            engine,
            target_id,
            _complete_inference(engine, target_id, player.custom_vars["formal_logic_inference_state"]),
        )


def _apply_substitution(engine, player_id: int, played_card: CardInstance, payload: dict) -> List[dict]:
    player = engine.players[player_id]
    operations: List[dict] = [{
        "op": "clear_status", "player_id": player_id,
        "status_id": SUBSTITUTION_STATUS,
        "payload_key": "formal_logic_substitution_state",
    }]
    source = _find_card(engine, payload.get("source_card_instance_id"))
    if source is None:
        operations.append({"op": "log", "message": f"{engine.pn(player_id)}的代入失败：来源牌不存在"})
        return operations
    formula = formula_for_card(source)
    if formula is None:
        operations.append({"op": "log", "message": f"{engine.pn(player_id)}的代入失败：来源公式无效"})
        return operations
    existing_bindings = copy.deepcopy(source.custom_vars.get("formal_logic_bindings", {}))
    if not isinstance(existing_bindings, dict):
        existing_bindings = {}
    variables = [name for name in formula_variables(formula) if name not in existing_bindings]
    if not variables:
        operations.append({"op": "log", "message": f"{engine.pn(player_id)}的代入失败：公式中没有未代入变量"})
        return operations
    variable = variables[0]
    expression = logical_expression_for_card(played_card)
    transformed = substitute_formula(formula, {variable: expression})
    bindings = copy.deepcopy(source.custom_vars.get("formal_logic_binding_cards", {}))
    if not isinstance(bindings, dict):
        bindings = {}
    bindings[variable] = played_card.to_dict()
    existing_bindings[variable] = expression_to_data(expression)
    operations.extend([
        {
            "op": "set_card_formula", "instance_id": source.instance_id,
            "formula": formula_to_data(transformed),
        },
        {
            "op": "set_card_var", "instance_id": source.instance_id,
            "name": "formal_logic_binding_cards", "value": bindings,
        },
        {
            "op": "set_card_var", "instance_id": source.instance_id,
            "name": "formal_logic_bindings", "value": existing_bindings,
        },
        {"op": "log", "message": f"{engine.pn(player_id)}将{played_card.name_cn}代入{variable}"},
    ])
    operations.extend(_deduction_response_actions(engine, player_id, source, "noop"))
    return operations


def _inference_source_snapshot(payload: dict, conclusion: LogicExpr) -> Optional[dict]:
    binding_cards = payload.get("binding_cards") if isinstance(payload.get("binding_cards"), dict) else {}
    for _, snapshot in binding_cards.items():
        if not isinstance(snapshot, dict):
            continue
        try:
            candidate = logical_expression_for_card(CardInstance.from_dict(copy.deepcopy(snapshot)))
        except Exception:
            candidate = LogicExpr.constant(str(snapshot.get("def_id") or ""))
        if expressions_match(conclusion, candidate) is not None and expressions_match(candidate, conclusion) is not None:
            return snapshot
    if conclusion.kind == "const" and conclusion.value in CARD_DEFS:
        return CardInstance(conclusion.value).to_dict()
    return None


def _complete_inference(engine, player_id: int, payload: dict) -> List[dict]:
    player = engine.players[player_id]
    operations: List[dict] = [{
        "op": "clear_status", "player_id": player_id,
        "status_id": INFERENCE_STATUS,
        "payload_key": "formal_logic_inference_state",
    }]
    source = _find_card(engine, payload.get("source_card_instance_id"))
    reset_source_action = None
    if payload.get("reset_source_after_inference") and source is not None:
        reset_source_action = {
            "op": "reset_formal_card",
            "instance_id": source.instance_id,
        }
    source_exile_action = None
    if payload.get("inference_exile") and source is not None:
        owner_id, _ = _find_card_location(engine, source)
        if owner_id is not None:
            source_exile_action = {
                "op": "move_card", "instance_id": source.instance_id,
                "owner_id": owner_id, "zone": "exile",
            }
    conclusion = _normalize_inference_expression(
        expression_from_data(payload.get("conclusion") or {})
    )
    if _is_inference_negation(conclusion):
        if reset_source_action is not None:
            operations.append(reset_source_action)
        if source_exile_action is not None:
            operations.append(source_exile_action)
        operations.append({
            "op": "log",
            "message": f"{engine.pn(player_id)}完成推理；否定结论不打出牌",
        })
        return operations
    snapshot = _inference_source_snapshot(payload, conclusion)
    if snapshot is not None:
        result_card = _fresh_card_copy_from_dict(snapshot, str(snapshot.get("def_id") or ""))
        result_card.custom_vars["formal_logic_formula"] = formula_to_data(ProofFormula((), conclusion))
    else:
        result_card = _special_card_for_formula(ProofFormula((), conclusion)) or _new_generated_theorem(ProofFormula((), conclusion))
    can_play, reason = _can_automatically_play(engine, player_id, result_card)
    if not can_play:
        if reset_source_action is not None:
            operations.append(reset_source_action)
        operations.append({"op": "log", "message": f"{engine.pn(player_id)}的推理失败：{reason}"})
        return operations
    target_id, choice = _automatic_play_target(engine, player_id, result_card)
    operations.extend([
        {
            "op": "create_card", "snapshot": result_card.to_dict(), "owner_id": player_id,
            "zone": "hand", "save_as": "inference_result_card",
        },
        {
            "op": "play_card", "instance_id": {"var": "inference_result_card"},
            "player_id": player_id, "target_id": target_id, "choice": choice,
            "save_as": "inference_play_result",
        },
        {
            "op": "call", "name": "inference_play_finish",
            "result_card_name": result_card.name_cn,
            "source_exile_action": source_exile_action,
            "reset_source_action": reset_source_action,
        },
    ])
    return operations


def _handle_inference_play_finish(engine, state: dict, action: dict) -> List[dict]:
    player_id = int(state.get("player_id", 0))
    result = _current_value(state, "inference_play_result", {})
    result = result if isinstance(result, dict) else {}
    card_id = _current_value(state, "inference_result_card")
    card_name = str(action.get("result_card_name") or "结论牌")
    reset_source_action = action.get("reset_source_action")
    if not result.get("success"):
        operations = [
            {"op": "remove_card", "instance_id": card_id},
            {
                "op": "log",
                "message": f"{engine.pn(player_id)}的推理失败：{result.get('error', '无法打出结论')}",
            },
        ]
        if isinstance(reset_source_action, dict):
            operations.insert(0, reset_source_action)
        return operations
    operations: List[dict] = []
    if isinstance(reset_source_action, dict):
        operations.append(reset_source_action)
    source_exile_action = action.get("source_exile_action")
    if isinstance(source_exile_action, dict):
        operations.append(source_exile_action)
    operations.append({"op": "log", "message": f"{engine.pn(player_id)}完成推理，自动打出{card_name}"})
    return operations


def _apply_inference(engine, player_id: int, played_card: CardInstance, payload: dict) -> List[dict]:
    player = engine.players[player_id]
    premises = [expression_from_data(item) for item in (payload.get("premises") or [])]
    if not _matching_premise_cards(engine, player_id, premises):
        operations = [
            {
                "op": "clear_status", "player_id": player_id,
                "status_id": INFERENCE_STATUS, "payload_key": "formal_logic_inference_state",
            },
            {"op": "log", "message": f"{engine.pn(player_id)}的推理失败：手牌前提不满足"},
        ]
        source = _find_card(engine, payload.get("source_card_instance_id"))
        if payload.get("reset_source_after_inference") and source is not None:
            operations.insert(1, {"op": "reset_formal_card", "instance_id": source.instance_id})
        return operations
    antecedents = [expression_from_data(item) for item in (payload.get("antecedents") or [])]
    index = _next_inference_index(antecedents, int(payload.get("index", 0) or 0))
    if index >= len(antecedents):
        return _complete_inference(engine, player_id, payload)
    candidate = logical_expression_for_card(played_card)
    if expressions_match(antecedents[index], candidate) is None:
        operations = [
            {
                "op": "clear_status", "player_id": player_id,
                "status_id": INFERENCE_STATUS, "payload_key": "formal_logic_inference_state",
            },
            {"op": "log", "message": f"{engine.pn(player_id)}的推理失败：{played_card.name_cn}不符合下一项"},
        ]
        source = _find_card(engine, payload.get("source_card_instance_id"))
        if payload.get("reset_source_after_inference") and source is not None:
            operations.insert(1, {"op": "reset_formal_card", "instance_id": source.instance_id})
        return operations
    payload["index"] = _next_inference_index(antecedents, index + 1)
    if payload["index"] >= len(antecedents):
        return _complete_inference(engine, player_id, payload)
    return [{
        "op": "set_player_var", "player_id": player_id,
        "name": "formal_logic_inference_state", "value": payload,
    }]


def _formal_theorem_play(
    engine,
    player_id: int,
    card: CardInstance,
    target_id: int,
    *,
    suppress_inference: bool = False,
) -> None:
    formal = _card_formal_resource(card)
    required = max(
        0,
        int(
            (getattr(card, "custom_vars", {}) or {}).get(
                "formal_logic_required_substitutions",
                formal.get("substitutions", len(formula_variables(formula_for_card(card))) if formula_for_card(card) else 0),
            )
            or 0
        ),
    )
    stage = max(0, int(card.custom_vars.get("formal_logic_stage", 0) or 0))
    if bool(formal.get("armor_each_play", False)):
        start_formal_logic_actions(engine, player_id, [{
            "op": "add_armor",
            "target_id": player_id,
            "amount": max(0, int(formal.get("armor", 3) or 3)),
        }])
    if stage < required:
        _grant_substitution(engine, target_id, card)
        card.custom_vars["formal_logic_stage"] = stage + 1
        return
    card.disabled_flags.add("rebound")
    if not suppress_inference:
        _grant_inference(engine, target_id, card)


def _start_metatheorem_action(engine, player_id: int, card: CardInstance, kind: str, target_id: int) -> Optional[dict]:
    if kind == "contraposition":
        candidates = _candidate_cards(engine, player_id, _is_implication_card)
        if not candidates:
            engine.log_msg("没有可进行逆否变换的牌")
            return None
        return start_formal_logic_actions(engine, player_id, [
            {
                "op": "choose", "choice_type": "card", "owner_id": player_id, "zone": "hand",
                "allowed_instance_ids": [candidate.instance_id for candidate in candidates],
                "save_as": "selected_card", "display_card_instance_id": card.instance_id,
                "title_cn": "否定爆炸", "title_en": "Contraposition",
                "text_cn": "选择一张蕴含公式牌进行逆否变换。",
                "text_en": "Choose an implication formula to transform.",
            },
            {"op": "call", "name": "contraposition_apply"},
        ])
    if kind == "inverse_deduction":
        candidates = _candidate_cards(engine, player_id, _is_inverse_deduction_candidate)
        if not candidates:
            engine.log_msg("没有可应用逆演绎元定理的牌")
            return None
        return start_formal_logic_actions(engine, player_id, [
            {
                "op": "choose", "choice_type": "card", "owner_id": player_id, "zone": "hand",
                "allowed_instance_ids": [candidate.instance_id for candidate in candidates],
                "save_as": "selected_card", "display_card_instance_id": card.instance_id,
                "title_cn": "逆演绎元定理", "title_en": "Inverse Deduction Metatheorem",
            },
            {"op": "call", "name": "inverse_deduction_apply"},
        ])
    if kind == "macro":
        candidates = _candidate_cards(engine, player_id, lambda candidate: _macro_candidate(engine, player_id, candidate))
        if not candidates:
            engine.log_msg("没有可进行宏定义的牌")
            return None
        return start_formal_logic_actions(engine, player_id, [
            {
                "op": "choose", "choice_type": "card", "owner_id": player_id, "zone": "hand",
                "allowed_instance_ids": [candidate.instance_id for candidate in candidates],
                "save_as": "selected_card", "display_card_instance_id": card.instance_id,
                "title_cn": "宏定义", "title_en": "Macro Definition",
            },
            {"op": "call", "name": "macro_create"},
        ])
    if kind == "generalization":
        return _start_generalization(engine, player_id, card, target_id)
    return None


def on_card_resolved_before_disposition(
    engine,
    player_id: int,
    card: CardInstance,
    target_id: int,
    choice: Optional[dict] = None,
) -> None:
    if not _valid_player(engine, player_id) or card is None:
        return
    player = engine.players[player_id]
    existing_substitution = _status_payload(player, "formal_logic_substitution_state")
    existing_inference = _status_payload(player, "formal_logic_inference_state")
    status_immune = bool(getattr(engine, "_is_status_immune", lambda _pid: False)(player_id))
    if existing_substitution and not status_immune:
        response_actions = _apply_substitution(engine, player_id, card, existing_substitution)
        if response_actions:
            start_formal_logic_actions(engine, player_id, response_actions)
    elif existing_inference and not status_immune:
        inference_actions = _apply_inference(engine, player_id, card, existing_inference)
        if inference_actions:
            start_formal_logic_actions(engine, player_id, inference_actions)

    custom = getattr(card, "custom_vars", {}) or {}
    macro_equipment_id = custom.get("formal_logic_macro_equipment_instance_id")
    if macro_equipment_id is not None:
        macro = _find_card(engine, macro_equipment_id)
        if macro is not None:
            macro.custom_vars["formal_logic_macro_heavy"] = max(
                0, int(macro.custom_vars.get("formal_logic_macro_heavy", 0) or 0)
            ) + 1

    formal = _card_formal_resource(card)
    kind = str(formal.get("kind") or "")
    if not formal_proxy_suppresses_effect(card):
        if kind == "theorem" or card.def_id == GENERATED_THEOREM_ID:
            _formal_theorem_play(
                engine,
                player_id,
                card,
                target_id,
                suppress_inference=bool(existing_inference),
            )
        elif kind in ("contraposition", "inverse_deduction", "macro", "generalization"):
            _start_metatheorem_action(engine, player_id, card, kind, target_id)


def finalize_card_used(engine, player_id: int, card: CardInstance) -> None:
    formal = _card_formal_resource(card)
    kind = str(formal.get("kind") or "")
    if kind == "theorem" and str(formal.get("reset_mode") or "discard") == "discard":
        _, zone = _find_card_location(engine, card)
        if zone == "discard":
            _reset_card_formula(card)


def on_equipment_triggered(engine, owner_id: int, equipment_card: CardInstance) -> None:
    if equipment_card is None or not _valid_player(engine, owner_id):
        return
    if equipment_card.def_id == MP_ID:
        candidates = _formal_formula_cards(engine, owner_id)
        if len(candidates) < 2:
            engine.log_msg("mp需要两张公式牌")
            return
        start_formal_logic_actions(engine, owner_id, [
            {
                "op": "choose", "choice_type": "card", "multi": True,
                "owner_id": owner_id, "zone": "hand", "min_select": 2, "max_select": 2,
                "allowed_instance_ids": [card.instance_id for card in candidates],
                "save_as": "selected_cards", "display_card_instance_id": equipment_card.instance_id,
                "title_cn": "mp", "title_en": "Modus Ponens",
                "text_cn": "选择两张可合一的公式牌。选择顺序决定蕴含式与前件。",
                "text_en": "Choose two unifiable formula cards.",
            },
            {"op": "call", "name": "mp_apply", "equipment_instance_id": equipment_card.instance_id},
        ])
    elif equipment_card.def_id == MACRO_EQUIPMENT_ID:
        start_formal_logic_actions(engine, owner_id, [
            {
                "op": "call", "name": "macro_trigger", "owner_id": owner_id,
                "equipment_instance_id": equipment_card.instance_id,
            }
        ])


def on_card_discarded(engine, owner_id: int, card: CardInstance, *, during_play: bool = False) -> None:
    formal = _card_formal_resource(card)
    if not formal or str(formal.get("reset_mode") or "discard") != "discard" or during_play:
        return
    _reset_card_formula(card)


def can_play_formal_card(engine, player_id: int, card: CardInstance) -> Tuple[bool, str]:
    formal = _card_formal_resource(card)
    kind = str(formal.get("kind") or "")
    if card.def_id == DEDUCTION_META_ID:
        return False, "此牌只能响应公式变化"
    if kind in ("contraposition", "inverse_deduction"):
        predicate = _is_inverse_deduction_candidate if kind == "inverse_deduction" else _is_implication_card
        if not _candidate_cards(engine, player_id, predicate):
            return False, "手中没有可变换的蕴含公式牌"
    if kind == "macro":
        if not _candidate_cards(engine, player_id, lambda candidate: _macro_candidate(engine, player_id, candidate)):
            return False, "手中没有可进行宏定义的牌"
    return True, ""


def _variable_only_in_term_positions(expr: LogicExpr, *, term_position: bool = False) -> bool:
    if expr.kind == "var" and expr.value == "$0":
        return term_position
    if expr.kind == "binary" and expr.value == "=":
        return all(_variable_only_in_term_positions(child, term_position=True) for child in expr.children)
    if expr.kind == "quantifier" and len(expr.children) == 2:
        variable, body = expr.children
        return _variable_only_in_term_positions(variable, term_position=True) and _variable_only_in_term_positions(body)
    return all(_variable_only_in_term_positions(child, term_position=term_position) for child in expr.children)


def _formula_can_be_generalized(formula: ProofFormula) -> bool:
    if "$0" not in formula_variables(formula):
        return False
    return all(_variable_only_in_term_positions(expr) for expr in (*formula.premises, formula.conclusion))


def _generalize_formula(formula: ProofFormula) -> ProofFormula:
    variable = LogicExpr.variable("$0")
    result = ProofFormula(
        tuple(LogicExpr.quantified("∀", variable, premise) for premise in formula.premises),
        LogicExpr.quantified("∀", variable, formula.conclusion),
    )
    validate_formula(result)
    return result


def _generalization_second_targets(engine, actor_id: int, first_target: int) -> List[int]:
    targets = []
    for player_id, player in enumerate(getattr(engine, "players", []) or []):
        if player_id == first_target or int(getattr(player, "health", 0) or 0) <= 0:
            continue
        if (
            len(getattr(engine, "players", []) or []) > 2
            and hasattr(engine, "_same_timer_side")
            and engine._same_timer_side(first_target, player_id)
        ):
            continue
        if engine._target_can_be_selected(actor_id, player_id, allow_self=True):
            targets.append(player_id)
    return targets


def _start_generalization(engine, player_id: int, card: CardInstance, first_target: int) -> Optional[dict]:
    if not _valid_player(engine, first_target):
        engine.log_msg("条件概括元定理缺少第一个目标")
        return None
    second_targets = _generalization_second_targets(engine, player_id, first_target)
    if not second_targets:
        engine.log_msg("条件概括元定理没有可选择的第二个目标")
        return None
    return start_formal_logic_actions(
        engine,
        player_id,
        [
            {
                "op": "choose",
                "choice_type": "player",
                "allowed_player_ids": second_targets,
                "save_as": "generalization_second_target",
                "display_card_instance_id": card.instance_id,
                "title_cn": "条件概括元定理",
                "title_en": "Generalization Metatheorem",
                "text_cn": "选择另一个目标，使其获得对应层数的血债。",
                "text_en": "Choose another target to receive Blood Debt.",
            },
            {
                "op": "call",
                "name": "generalization_apply",
                "first_target": first_target,
            },
        ],
    )


def _handle_generalization_apply(engine, state: dict, action: dict) -> List[dict]:
    first_target = int(action.get("first_target", -1))
    second_target = _current_value(state, "generalization_second_target")
    try:
        second_target = int(second_target)
    except (TypeError, ValueError):
        return []
    if not _valid_player(engine, first_target) or not _valid_player(engine, second_target):
        return []
    changed: List[dict] = []
    operations: List[dict] = []
    for zone in ("hand", "deck", "discard", "exile"):
        for card in _zone_cards(engine, first_target, zone):
            if not _selectable(card):
                continue
            formula = formula_for_card(card)
            if formula is None or not _formula_can_be_generalized(formula):
                continue
            changed.append({"instance_id": card.instance_id, "formula": formula_to_data(formula)})
            operations.append({
                "op": "set_card_formula", "instance_id": card.instance_id,
                "formula": formula_to_data(_generalize_formula(formula)),
                "remember_original": False,
            })
    if changed:
        operations.extend([
            {
                "op": "set_player_var", "player_id": first_target,
                "name": "formal_logic_generalization_effects", "mode": "append",
                "value": {
                    "source_player": int(state.get("player_id", 0)),
                    "restore_on_player_turn_end": first_target,
                    "cards": changed,
                },
            },
            {
                "op": "set_status", "player_id": second_target, "status_id": "blood_debt",
                "amount": len(changed), "mode": "add",
            },
            {
                "op": "log",
                "message": (
                    f"{engine.pn(first_target)}的{len(changed)}张公式牌被概括；"
                    f"{engine.pn(second_target)}获得{len(changed)}层血债"
                ),
            },
        ])
    else:
        operations.append({"op": "log", "message": "没有符合条件概括元定理的公式牌"})
    return operations


def on_turn_end(engine, player_id: int) -> None:
    if not _valid_player(engine, player_id):
        return
    player = engine.players[player_id]
    effects = player.custom_vars.pop("formal_logic_generalization_effects", [])
    for effect in effects if isinstance(effects, list) else []:
        for record in effect.get("cards", []) if isinstance(effect, dict) else []:
            card = _find_card(engine, record.get("instance_id"))
            if card is not None and isinstance(record.get("formula"), Mapping):
                set_card_formula(card, formula_from_data(record["formula"]), remember_original=False)
    for card in list(player.hand) + list(player.deck) + list(player.discard) + list(player.exile):
        custom = getattr(card, "custom_vars", {}) or {}
        custom.pop("formal_logic_temporary_cost_e", None)
        custom.pop("formal_logic_temporary_cost_m", None)


def _catalog_options(def_ids: Iterable[str]) -> List[dict]:
    options = []
    for def_id in def_ids:
        card_def = CARD_DEFS.get(str(def_id))
        if card_def is None:
            continue
        card = CardInstance(card_def.id)
        options.append({
            "value": card_def.id,
            "label_cn": card_def.name_cn,
            "label_en": card_def.name_en,
            "card": card.to_dict(),
        })
    return options[:MAX_DYNAMIC_CANDIDATES]


def _handle_play_catalog_card(engine, state: dict, action: dict) -> List[dict]:
    player_id = int(state.get("player_id", 0))
    def_id = str(_current_value(state, str(action.get("selected_var") or "selected_card_def")) or "")
    if not _valid_player(engine, player_id) or def_id not in CARD_DEFS:
        return []
    card = CardInstance(def_id)
    target_id, choice = _automatic_play_target(engine, player_id, card)
    return [
        {
            "op": "create_card", "snapshot": card.to_dict(), "owner_id": player_id,
            "zone": "hand", "save_as": "debut_catalog_card",
        },
        {
            "op": "play_card", "instance_id": {"var": "debut_catalog_card"},
            "player_id": player_id, "target_id": target_id, "choice": choice,
            "no_cost": True, "save_as": "debut_catalog_play_result",
        },
        {"op": "call", "name": "catalog_play_finish"},
    ]


def _handle_catalog_play_finish(engine, state: dict, action: dict) -> List[dict]:
    result = _current_value(state, "debut_catalog_play_result", {})
    if isinstance(result, dict) and result.get("success"):
        return []
    card_id = _current_value(state, "debut_catalog_card")
    error = result.get("error", "无法自动打出") if isinstance(result, dict) else "无法自动打出"
    return [
        {"op": "remove_card", "instance_id": card_id},
        {"op": "log", "message": f"登场效果失败：{error}"},
    ]


def on_card_enter_hand(engine, player_id: int, card: CardInstance) -> None:
    if not _valid_player(engine, player_id) or card is None:
        return
    player = engine.players[player_id]
    active_generalizations = player.custom_vars.get("formal_logic_generalization_effects")
    if isinstance(active_generalizations, list) and active_generalizations:
        formula = formula_for_card(card)
        if formula is not None and _formula_can_be_generalized(formula) and _selectable(card):
            active_generalizations[-1].setdefault("cards", []).append(
                {"instance_id": card.instance_id, "formula": formula_to_data(formula)}
            )
            set_card_formula(card, _generalize_formula(formula), remember_original=False)

    formal = _card_formal_resource(card)
    debut_effect = str(formal.get("debut_effect") or "")
    if not debut_effect or DEBUT_FLAG not in getattr(card, "flags", set()):
        return
    debuted = player.custom_vars.setdefault("formal_logic_debuted_cards", [])
    first_debut = card.def_id not in debuted
    if first_debut:
        debuted.append(card.def_id)
    if debut_effect == "double_first_card":
        player.custom_vars["formal_logic_double_next_card"] = 1
        return
    candidates = [candidate for candidate in player.hand if candidate is not card and _selectable(candidate)]
    if debut_effect in ("zero_e", "zero_em"):
        if not candidates:
            return
        start_formal_logic_actions(engine, player_id, [
            {
                "op": "choose", "choice_type": "card", "owner_id": player_id, "zone": "hand",
                "allowed_instance_ids": [candidate.instance_id for candidate in candidates],
                "save_as": "selected_card", "display_card_instance_id": card.instance_id,
                "title_cn": "登场", "title_en": "Debut",
                "text_cn": "选择一张牌改变其消耗。",
                "text_en": "Choose a card whose cost will change.",
            },
            {
                "op": "call", "name": "set_cost_zero", "zero_e": True,
                "zero_m": debut_effect == "zero_em", "temporary": not first_debut,
            },
        ])
        return
    if debut_effect == "play_from_pool":
        allowed = getattr(engine, "allowed_card_ids", None)
        def_ids = [
            def_id for def_id, card_def in CARD_DEFS.items()
            if def_id != "Error"
            and (allowed is None or def_id in allowed)
            and int(getattr(card_def, "count", 0) or 0) > 0
            and "sublime" not in getattr(card_def, "flags", set())
        ]
        options = _catalog_options(def_ids)
        if options:
            start_formal_logic_actions(engine, player_id, [
                {
                    "op": "choose", "choice_type": "catalog_card", "options": options,
                    "save_as": "selected_card_def", "display_card_instance_id": card.instance_id,
                    "title_cn": "登场：选择一张牌打出", "title_en": "Debut: Play a card",
                },
                {"op": "call", "name": "play_catalog_card"},
            ])
        return
    if debut_effect == "heal_5":
        start_formal_logic_actions(engine, player_id, [
            {"op": "heal", "target_id": player_id, "amount": 5},
        ])
        return
    if debut_effect == "gain_and_swap":
        start_formal_logic_actions(engine, player_id, [
            {
                "op": "adjust_player_stat", "player_id": player_id, "attr": "health",
                "amount": int(math.ceil(max(0, player.health) / 10.0)),
            },
            {"op": "adjust_player_stat", "player_id": player_id, "attr": "elixir", "amount": 1},
            {"op": "adjust_player_stat", "player_id": player_id, "attr": "magic", "amount": 1},
            {
                "op": "choose", "choice_type": "option", "save_as": "stat_pair",
                "display_card_instance_id": card.instance_id,
                "title_cn": "登场：交换数值", "title_en": "Debut: Swap values",
                "options": [
                    {"value": "h_e", "label_cn": "交换H与E", "label_en": "Swap H and E"},
                    {"value": "h_m", "label_cn": "交换H与M", "label_en": "Swap H and M"},
                    {"value": "e_m", "label_cn": "交换E与M", "label_en": "Swap E and M"},
                ],
            },
            {"op": "call", "name": "swap_stats"},
        ])


def consume_double_resolution(engine, player_id: int) -> bool:
    if not _valid_player(engine, player_id):
        return False
    player = engine.players[player_id]
    count = max(0, int(player.custom_vars.get("formal_logic_double_next_card", 0) or 0))
    if count <= 0:
        return False
    player.custom_vars["formal_logic_double_next_card"] = count - 1
    return True


def _formal_draft_ids() -> List[str]:
    return [
        def_id for def_id, card_def in CARD_DEFS.items()
        if def_id.startswith(f"{MOD_ID}:")
        and int(getattr(card_def, "count", 0) or 0) > 0
        and def_id not in (MACRO_EQUIPMENT_ID, GENERATED_THEOREM_ID)
    ]


def boosted_draft_pool(engine, player_id: int, pool: Sequence[CardInstance]) -> List[CardInstance]:
    picks = getattr(engine, "opening_event_picks", []) or []
    if player_id >= len(picks) or str(picks[player_id]) != GREAT_MATHEMATICIAN_ID:
        return list(pool)
    formal_ids = set(_formal_draft_ids())
    result = []
    for card in pool:
        clone = card.copy()
        clone.draft_weight = float(getattr(card, "draft_weight", 1.0) or 1.0)
        if clone.def_id in formal_ids:
            clone.draft_weight *= 5.0
        result.append(clone)
    return result


def maybe_prompt_great_mathematician(engine, player_id: int) -> bool:
    picks = getattr(engine, "opening_event_picks", []) or []
    if not _valid_player(engine, player_id) or player_id >= len(picks):
        return False
    if str(picks[player_id]) != GREAT_MATHEMATICIAN_ID or int(getattr(engine, "round_num", 1) or 1) <= 1:
        return False
    player = engine.players[player_id]
    marker = f"{int(getattr(engine, 'round_num', 0) or 0)}:{int(player_id)}"
    if player.custom_vars.get("formal_logic_mathematician_turn_marker") == marker:
        return False
    if int(getattr(player, "health", 0) or 0) <= 0:
        return False
    if (
        int(getattr(player, "forced_skip_turn", 0) or 0) > 0
        or int(getattr(player, "skip_turn", 0) or 0) > 0
        or int(player.custom_vars.get("ocean_action_skip_turns", 0) or 0) > 0
    ):
        player.custom_vars["formal_logic_mathematician_turn_marker"] = marker
        return False
    player.custom_vars["formal_logic_mathematician_turn_marker"] = marker
    options = _catalog_options(_formal_draft_ids())
    if not options:
        return False
    actions = [
        {
            "op": "choose", "choice_type": "catalog_card", "options": options,
            "save_as": "selected_card_def", "title_cn": "大数学家", "title_en": "Great Mathematician",
            "text_cn": "可以少抽1张牌，改为从形式逻辑推理包选择1张牌加入手中。",
            "text_en": "You may draw one fewer card and choose a Formal Logic card instead.",
            "cancel_value": None,
            "on_cancel": [{"op": "call", "name": "resume_turn_start"}],
            "timeout_ms": 30000,
        },
        {"op": "call", "name": "add_selected_catalog_card"},
        {"op": "call", "name": "resume_turn_start"},
    ]
    start_formal_logic_actions(engine, player_id, actions)
    return getattr(engine, "pending_v2_ui", None) is not None


def consume_draw_reduction(engine, player_id: int) -> int:
    if not _valid_player(engine, player_id):
        return 0
    return max(0, int(engine.players[player_id].custom_vars.pop("formal_logic_draw_reduction", 0) or 0))


def equipment_trigger_is_formal(card: Optional[CardInstance]) -> bool:
    return bool(card and card.def_id in (MP_ID, MACRO_EQUIPMENT_ID))


def formal_proxy_suppresses_effect(card: Optional[CardInstance]) -> bool:
    return bool(card and (getattr(card, "custom_vars", {}) or {}).get("formal_logic_proxy"))


_ACTION_HANDLERS.update({
    "generalization_apply": _handle_generalization_apply,
    "play_catalog_card": _handle_play_catalog_card,
    "catalog_play_finish": _handle_catalog_play_finish,
    "inference_play_finish": _handle_inference_play_finish,
    "noop": lambda engine, state, action: [],
})
