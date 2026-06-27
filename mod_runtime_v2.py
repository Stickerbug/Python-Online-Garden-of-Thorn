from __future__ import annotations

import copy
import math
import random
import uuid
from typing import Any, Dict, Iterable, List, Optional

from cards import CARD_DEFS, CardInstance, ERROR_CARD_ID, clamp_card_extra_hits, clamp_damage_hits
from damage_types import DAMAGE_TYPE_PHYSICAL


STEP_BUDGET = 1000
FOR_EACH_LIMIT = 200


ADVANCED_ATOMIC_OPS = {
    "after_all", "random", "break", "continue", "if_else", "repeat", "repeat_until",
    "for_each", "for_each_selected_card", "for_each_list",
    "damage", "damage_multi", "direct_damage", "lifesteal_damage", "triangle_damage",
    "heal", "draw", "gain_e", "gain_m", "add_armor", "remove_armor", "set_armor",
    "poison", "burn", "toxic", "vulnus", "apply_vulnerable", "dodge_this",
    "dodge_permanent", "clear_buffs", "clear_debuffs", "clear_all_effects",
    "clear_status", "status_add_named", "status_remove_named", "set_status_named",
    "cost_e", "cost_m", "mod_e_regen", "mod_m_regen", "mod_draw",
    "discard", "choose_from_deck", "choose_from_discard", "choose_from_exile",
    "reveal_enemy_hand", "reveal_hand", "reveal_deck_top", "steal_enemy_card",
    "steal_card", "copy_card", "copy_choice_with_discount", "random_discard_from_hand",
    "put_card_to_deck", "shuffle_discard_into_deck", "give_card_to_hand",
    "give_card_to_deck", "give_card_to_discard", "remove_specific_card",
    "move_to_hand", "move_to_discard", "move_to_deck", "move_to_exile",
    "destroy_random_equip", "destroy_all_equip", "destroy_all_field_equip",
    "destroy_all_destroyable_equipment", "destroy_self_equipment",
    "destroy_equipment_choice_or_first", "equip_protection", "remove_equip_protection",
    "place_as_equip", "add_equipment_to_zone", "trigger_manual",
    "block_action", "block_card_type", "force_card_type", "nullify_current_card",
    "cancel_current_card", "invincible", "untargetable", "skip_turn", "extra_turn",
    "set_health",
    "force_end_turn", "mark_self_damage_source", "fission", "fusion",
    "multiply_next_damage", "reduce_next_cost", "increase_next_cost",
    "add_tag", "add_tag_to_zone", "remove_tag", "tag_add_named", "tag_remove_named", "clear_tags",
    "transform_card", "gain_durability", "lose_durability", "set_durability",
    "record_play_count", "record_equip_turns", "reset_counter", "create_counter",
    "exile_this", "global_damage_mult", "global_heal_mult", "global_cost_mult",
    "swap_health", "swap_hands", "broadcast_event", "modify_damage",
    "var_set", "var_add", "var_sub", "var_mul", "var_div", "var_remove",
    "list_set", "list_create", "list_append", "list_insert", "list_delete",
    "list_extend", "list_pop", "list_clear", "for_each_list", "timed_effect", "countdown_var",
    "player_prop_set", "player_prop_add", "card_prop_set", "card_prop_add",
    "card_prop_mul", "card_damage_multiply", "equipment_prop_set",
    "discard_hand_by_paid_e", "restore_turn_start_stats", "restore_match_start_stats",
    "shuffle_hand",
    "counter_pending_attack_damage", "lose_health",
    "equipment_prop_add", "discard_choice_then_draw", "coffee_gain_e",
    "activate_corruption", "request_target", "request_card", "request_confirm",
    "response_declare", "aura_enemy_elixir_recovery", "on_any_turn_start",
    "on_enemy_turn_start", "on_owner_turn_start", "on_owner_turn_end", "on_hand_owner_turn_start", "on_hand_owner_turn_end",
    "on_discard_owner_turn_start", "on_equipment_trigger", "on_equipment_destroy",
    "on_damage_taken", "on_fatal_set_health_exile", "equip_reduce_own_draw",
    "cogwheel_mark",
    "goggles_enable",
    "reveal_tag_hand",
    "assembler_effect",
    "request_reorder_deck",
    "apply_jungle_status", "apply_turn_regen", "magic_grapes_damage",
    "create_copies_to_deck_top", "consume_magic_for_status",
    "jungle_root_gain", "jungle_root_remove_owned", "plank_immunity",
    "magic_relic_trigger", "electric_web_arm",
    "yin_yang_effect", "flower_burst",
}

ATOMIC_OP_ALIASES = {
    "gain_armor": "add_armor",
    "apply_poison": "poison",
    "apply_burn": "burn",
    "apply_toxic": "toxic",
    "add_card_tag": "add_tag",
    "remove_card_tag": "remove_tag",
    "set_player_prop": "player_prop_set",
    "add_player_prop": "player_prop_add",
    "set_card_prop": "card_prop_set",
    "add_card_prop": "card_prop_add",
    "set_equipment_prop": "equipment_prop_set",
    "add_equipment_prop": "equipment_prop_add",
    "equip_card": "place_as_equip",
    "protect_equipment": "equip_protection",
}


class V2RuntimeError(Exception):
    pass


class V2UIPause(Exception):
    def __init__(self, payload: Dict[str, Any]):
        super().__init__("v2 ui request pending")
        self.payload = payload


def run_v2_event(engine, context: Dict[str, Any], event_def: Any):
    ctx = _prepare_context(context)
    try:
        steps = event_def.get("steps", []) if isinstance(event_def, dict) else event_def
        if not isinstance(steps, list):
            raise V2RuntimeError("v2 event must be a list of steps")
        ctx.setdefault("_budget", STEP_BUDGET)
        return run_v2_steps(engine, ctx, steps)
    except V2UIPause as pause:
        return {"success": True, "needs_v2_ui": True, "v2_ui_pause": pause.payload}
    except Exception as exc:
        _log_runtime_error(engine, ctx, "v2_event", exc)
        return {"success": False, "error": str(exc)}


def run_v2_steps(engine, context: Dict[str, Any], steps: Iterable[Any]):
    if not isinstance(steps, list):
        raise V2RuntimeError("steps must be a list")
    result = {"success": True}
    for idx, step in enumerate(steps):
        try:
            result = run_v2_step(engine, context, step) or result
            if isinstance(result, dict) and result.get("needs_v2_ui"):
                pause = dict(result.get("v2_ui_pause") or {})
                nested_remaining = pause.get("remaining_steps") if isinstance(pause.get("remaining_steps"), list) else []
                pause["remaining_steps"] = list(nested_remaining) + list(steps[idx + 1:])
                return {"success": True, "needs_v2_ui": True, "v2_ui_pause": pause}
            if getattr(engine, "game_over", False):
                break
        except V2UIPause as pause_exc:
            pause = dict(pause_exc.payload)
            pause["remaining_steps"] = list(steps[idx + 1:])
            return {"success": True, "needs_v2_ui": True, "v2_ui_pause": pause}
    return result


def run_v2_step(engine, context: Dict[str, Any], step: Any):
    _consume_budget(context)
    if not isinstance(step, dict):
        raise V2RuntimeError("step must be an object")
    op = step.get("op") or step.get("type")
    params = step.get("params") if isinstance(step.get("params"), dict) else step

    if op == "request_target":
        choice = context.get("choice")
        action = context.get("current_action")
        if choice is None and isinstance(action, dict):
            choice = action.get("choice", action)
        target_id = _choice_target_id(choice)
        if target_id is None:
            target_id = _explicit_target_id(engine, context)
        if target_id is None:
            raise V2RuntimeError("target choice is required")
        context["target_player"] = target_id
        context.setdefault("vars", {})["target_player"] = target_id
        if isinstance(action, dict):
            action["target_player_id"] = target_id
        return {"success": True, "target_player": target_id}

    if op == "deal_damage":
        source = _player_id(engine, resolve_v2_target(engine, context, params.get("source", "source")))
        amount = max(0, _to_int(eval_v2_value(engine, context, params.get("amount", 0))))
        hits = clamp_damage_hits(_to_int(eval_v2_value(engine, context, params.get("hits", 1))))
        card = context.get("card")
        inherit_extra_hits = params.get("inherit_extra_hits", params.get("use_card_extra_hits", True)) is not False
        if card is not None and inherit_extra_hits:
            try:
                if hasattr(engine, "_card_total_hits"):
                    hits = clamp_damage_hits(engine._card_total_hits(card, hits))
                else:
                    hits = clamp_damage_hits(hits + clamp_card_extra_hits(getattr(card, "extra_hits", 0)))
            except Exception:
                pass
        if (
            card is not None
            and context.get("current_event") == "on_play"
            and getattr(getattr(card, "card_def", None), "card_type", getattr(card, "card_type", "")) == "thorn"
            and hasattr(engine, "_modified_attack_damage")
        ):
            amount = max(0, _to_int(engine._modified_attack_damage(amount, card)))
        card_flags = getattr(card, "flags", set()) or set()
        is_precision = bool(params.get("is_precision", params.get("precision", False))) or "precision" in card_flags
        targets = _as_player_list(engine, resolve_v2_target(engine, context, params.get("target", "target")))
        total = 0
        positive_hits = 0
        for target_id in targets:
            if not _valid_player(engine, target_id):
                continue
            try:
                dealt = engine.deal_attack_damage(target_id, amount, hits, is_precision=is_precision, attacker_id=source, source_card=card)
            except TypeError:
                dealt = engine.deal_attack_damage(target_id, amount, hits, is_precision=is_precision)
            total += int(dealt or 0)
            try:
                hit_values = getattr(engine, "_last_positive_damage_hits", [])
                positive_hits += int(hit_values[target_id] if isinstance(hit_values, list) and target_id < len(hit_values) else 0)
            except Exception:
                if int(dealt or 0) > 0:
                    positive_hits += 1
        context["last_damage"] = total
        context["last_positive_hits"] = positive_hits
        context.setdefault("vars", {})["last_positive_hits"] = positive_hits
        return {"success": True, "last_damage": total, "last_positive_hits": positive_hits}

    if op in ("direct_damage", "deal_direct_damage"):
        raw_source = params.get("source", "source")
        source_selector = raw_source if _looks_like_target_selector(raw_source) else "source"
        source = _player_id(engine, resolve_v2_target(engine, context, source_selector))
        amount = max(0, _to_int(eval_v2_value(engine, context, params.get("amount", 0))))
        source_text = params.get("source_text") or params.get("source_name") or params.get("label")
        if source_text is None and not _looks_like_target_selector(raw_source):
            source_text = raw_source
        source_text = str(source_text or "效果")
        damage_type = str(params.get("damage_type") or DAMAGE_TYPE_PHYSICAL)
        damage_tag = params.get("damage_tag")
        total = 0
        for target_id in _as_player_list(engine, resolve_v2_target(engine, context, params.get("target", "target"))):
            if not _valid_player(engine, target_id) or not hasattr(engine, "_deal_direct_damage"):
                continue
            try:
                dealt = engine._deal_direct_damage(
                    target_id,
                    amount,
                    source_text,
                    source,
                    damage_type=damage_type,
                    damage_tag=damage_tag,
                )
            except TypeError:
                dealt = engine._deal_direct_damage(target_id, amount, source_text, source)
            total += int(dealt or 0)
        context["last_damage"] = total
        return {"success": True, "last_damage": total}

    if op == "heal":
        amount = max(0, _to_int(eval_v2_value(engine, context, params.get("amount", 0))))
        for target_id in _as_player_list(engine, resolve_v2_target(engine, context, params.get("target", "source"))):
            if _valid_player(engine, target_id):
                before = engine.players[target_id].health
                engine.players[target_id].heal(amount)
                healed = max(0, engine.players[target_id].health - before)
                if healed:
                    engine.log_msg(f"{engine.pn(target_id)}回复{healed}H")
        return {"success": True}

    if op == "draw_cards":
        amount = max(0, _to_int(eval_v2_value(engine, context, params.get("amount", params.get("count", 1)))))
        for target_id in _as_player_list(engine, resolve_v2_target(engine, context, params.get("target", "source"))):
            if _valid_player(engine, target_id):
                if hasattr(engine, "_draw_cards_with_v2_hooks") and context.get("current_event") not in ("before_draw", "after_draw"):
                    drawn = engine._draw_cards_with_v2_hooks(target_id, amount, "v2_runtime")
                else:
                    drawn = engine.players[target_id].draw_cards(amount)
                if not context.get("suppress_detail_logs"):
                    engine.log_msg(f"{engine.pn(target_id)}抽{len(drawn)}张牌")
        return {"success": True}

    if op in ("gain_e", "gain_m"):
        amount = _to_int(eval_v2_value(engine, context, params.get("amount", 0)))
        for target_id in _as_player_list(engine, resolve_v2_target(engine, context, params.get("target", "source"))):
            if not _valid_player(engine, target_id):
                continue
            if op == "gain_e":
                if amount < 0:
                    engine.players[target_id].elixir = max(0, int(engine.players[target_id].elixir) + amount)
                else:
                    engine.players[target_id].gain_elixir(amount)
                engine.log_msg(f"{engine.pn(target_id)}获得{amount}E")
            else:
                if amount < 0:
                    engine.players[target_id].magic = max(0, int(engine.players[target_id].magic) + amount)
                else:
                    engine.players[target_id].gain_magic(amount)
                engine.log_msg(f"{engine.pn(target_id)}获得{amount}M")
        return {"success": True}

    if op in ("add_status", "remove_status", "set_status"):
        status_id = str(params.get("status") or params.get("id") or "").strip()
        amount = _to_int(eval_v2_value(engine, context, params.get("amount", params.get("stack", 1))))
        for target_id in _as_player_list(engine, resolve_v2_target(engine, context, params.get("target", "target"))):
            if _valid_player(engine, target_id):
                _apply_status(engine, target_id, status_id, amount, op)
        return {"success": True}

    if op == "move_card":
        card = _resolve_card(engine, context, params.get("card", "current_card"))
        if card is None:
            return {"success": True}
        to_zone = str(params.get("to") or params.get("zone") or "discard")
        owner = resolve_v2_target(engine, context, params.get("owner", "source"))
        owner_id = _player_id(engine, owner)
        _move_card(engine, card, owner_id, to_zone)
        return {"success": True}

    if op == "create_card":
        card_id = str(eval_v2_value(engine, context, params.get("card_id", params.get("id", ERROR_CARD_ID))) or ERROR_CARD_ID)
        to_zone = str(params.get("to") or params.get("zone") or "hand")
        for target_id in _as_player_list(engine, resolve_v2_target(engine, context, params.get("target", "source"))):
            if _valid_player(engine, target_id):
                new_card = CardInstance(def_id=card_id if card_id in CARD_DEFS else ERROR_CARD_ID)
                _move_card(engine, new_card, target_id, to_zone, already_detached=True)
        return {"success": True}

    if op == "destroy_equipment":
        for target_id in _as_player_list(engine, resolve_v2_target(engine, context, params.get("target", "target"))):
            if not _valid_player(engine, target_id):
                continue
            eq = _resolve_equipment(engine, context, target_id, params.get("equipment"))
            if eq is not None and hasattr(engine, "_destroy_equipment"):
                engine._destroy_equipment(target_id, eq)
        return {"success": True}

    if op == "if":
        branch = step.get("then", []) if check_v2_condition(engine, context, step.get("condition", step.get("cond"))) else step.get("else", [])
        return run_v2_steps(engine, context, branch or [])

    if op == "for_each":
        items = resolve_v2_target(engine, context, step.get("items", step.get("targets", step.get("list", []))))
        if not isinstance(items, list):
            items = [items]
        var_name = str(step.get("as") or step.get("var") or "item")
        old_value = context.setdefault("vars", {}).get(var_name)
        had_old = var_name in context["vars"]
        try:
            for item in items[:FOR_EACH_LIMIT]:
                context["vars"][var_name] = item
                child_result = run_v2_steps(engine, context, step.get("steps", step.get("body", [])) or [])
                if isinstance(child_result, dict) and child_result.get("needs_v2_ui"):
                    return child_result
                if getattr(engine, "game_over", False):
                    break
        finally:
            if had_old:
                context["vars"][var_name] = old_value
            else:
                context["vars"].pop(var_name, None)
        return {"success": True}

    if op == "request_ui":
        raise V2UIPause(_build_ui_pause(engine, context, params))

    if op == "modify_event_value":
        mode = str(params.get("mode") or params.get("operator") or "set")
        value = eval_v2_value(engine, context, params.get("value", params.get("amount", 0)))
        current = context.get("event_value", context.get("vars", {}).get("event_value", 0))
        if mode in ("add", "+"):
            next_value = _to_number(current) + _to_number(value)
        elif mode in ("sub", "-"):
            next_value = _to_number(current) - _to_number(value)
        elif mode in ("mul", "*"):
            next_value = _to_number(current) * _to_number(value)
        elif mode in ("div", "/"):
            divisor = _to_number(value)
            next_value = 0 if divisor == 0 else _to_number(current) / divisor
        elif mode in ("min",):
            next_value = min(_to_number(current), _to_number(value))
        elif mode in ("max",):
            next_value = max(_to_number(current), _to_number(value))
        else:
            next_value = value
        if isinstance(next_value, float) and next_value.is_integer():
            next_value = int(next_value)
        context["event_value"] = next_value
        context.setdefault("vars", {})["event_value"] = next_value
        return {"success": True, "event_value": next_value}

    if op == "set_var":
        name = str(params.get("name") or step.get("name") or "")
        if name:
            context.setdefault("vars", {})[name] = eval_v2_value(engine, context, params.get("value", step.get("value", 0)))
        return {"success": True}

    if op == "add_var":
        name = str(params.get("name") or step.get("name") or "")
        if name:
            delta = eval_v2_value(engine, context, params.get("value", step.get("value", 0)))
            context.setdefault("vars", {})[name] = _to_int(context["vars"].get(name, 0)) + _to_int(delta)
        return {"success": True}

    if op == "log":
        message = str(params.get("message") or params.get("text") or "")
        if message:
            engine.log_msg(_format_message(message, context))
        return {"success": True}

    atomic_result = _try_run_engine_atomic_op(engine, context, op, params, step)
    if atomic_result is not None:
        return atomic_result

    raise V2RuntimeError(f"unsupported v2 op: {op}")


def eval_v2_value(engine, context: Dict[str, Any], expr: Any):
    if isinstance(expr, (int, float, bool)) or expr is None:
        return expr
    if isinstance(expr, str):
        return expr
    if isinstance(expr, list):
        return [eval_v2_value(engine, context, item) for item in expr]
    if not isinstance(expr, dict):
        return expr

    if len(expr) == 1 and "player_stat" in expr and isinstance(expr.get("player_stat"), list):
        parts = expr.get("player_stat") or []
        return eval_v2_value(engine, context, {
            "op": "player_stat",
            "target": parts[0] if parts else "source",
            "stat": parts[1] if len(parts) > 1 else "",
        })
    if len(expr) == 1 and "var" in expr:
        return context.get("vars", {}).get(expr.get("var"), 0)

    op = expr.get("op") or expr.get("ref") or expr.get("type")
    if op in ("const", "literal"):
        return expr.get("value", expr.get("const"))
    if op in ("var", "temp_var"):
        # A plain var is a temporary runtime var.  If a target is supplied, it
        # means a per-player custom var in editor output.
        name = str(expr.get("name") or expr.get("id") or "")
        if "target" in expr:
            target = resolve_v2_target(engine, context, expr.get("target", "source"))
            player_id = _player_id(engine, target)
            if _valid_player(engine, player_id):
                suppressed = getattr(engine, "_is_suppressed_status_var", None)
                if callable(suppressed) and suppressed(player_id, name):
                    return 0
                return getattr(engine.players[player_id], "custom_vars", {}).get(name, expr.get("default", 0))
            return expr.get("default", 0)
        return context.get("vars", {}).get(name, expr.get("default", 0))
    if op in ("player_var", "global_var"):
        target = resolve_v2_target(engine, context, expr.get("target", "source"))
        player_id = _player_id(engine, target)
        name = str(expr.get("name") or expr.get("id") or "")
        if op == "global_var":
            return getattr(engine, "global_vars", {}).get(name, expr.get("default", 0))
        if _valid_player(engine, player_id):
            suppressed = getattr(engine, "_is_suppressed_status_var", None)
            if callable(suppressed) and suppressed(player_id, name):
                return 0
            return getattr(engine.players[player_id], "custom_vars", {}).get(name, expr.get("default", 0))
        return expr.get("default", 0)
    if op == "get":
        obj = eval_v2_value(engine, context, expr.get("object", expr.get("from", {})))
        key = eval_v2_value(engine, context, expr.get("key", ""))
        default = eval_v2_value(engine, context, expr.get("default", 0))
        if isinstance(obj, dict):
            return obj.get(str(key), default)
        if isinstance(obj, list):
            try:
                return obj[int(key)]
            except Exception:
                return default
        return default
    if op in ("player_stat", "player_property"):
        target = resolve_v2_target(engine, context, expr.get("target", expr.get("player", "source")))
        player_id = _player_id(engine, target)
        return _player_stat(engine, player_id, expr.get("stat", expr.get("property", expr.get("field", ""))))
    if op in ("card_prop", "card_property"):
        card = _resolve_card(engine, context, expr.get("card", "current_card"))
        return _card_prop(card, expr.get("prop", expr.get("property", expr.get("field", ""))))
    if op in ("equipment_prop", "equipment_property"):
        owner_id = _player_id(engine, resolve_v2_target(engine, context, expr.get("target", "source")))
        equipment = _resolve_equipment(engine, context, owner_id, expr.get("equipment", "current_equipment"))
        return _equipment_prop(equipment, expr.get("prop", expr.get("property", expr.get("field", ""))))
    if op in ("zone_count", "hand_count", "deck_count", "discard_count", "exile_count", "equipment_count"):
        zone = str(expr.get("zone") or op.replace("_count", ""))
        target = resolve_v2_target(engine, context, expr.get("target", "source"))
        pid = _player_id(engine, target)
        cards = _zone(engine, pid, zone)
        card_type = expr.get("card_type")
        if card_type:
            return sum(1 for c in cards if getattr(c, "card_type", "") == card_type)
        if op == "equipment_count":
            eq_id = expr.get("equipment_id", expr.get("id", ""))
            if eq_id:
                eq_id = str(eval_v2_value(engine, context, eq_id))
                return sum(1 for c in cards if getattr(c, "def_id", "") == eq_id)
        return len(cards)
    if op == "equipment_count_targeting":
        owners = resolve_v2_target(engine, context, expr.get("owners", expr.get("target", "source")))
        if not isinstance(owners, list):
            owners = [owners]
        target_id = _player_id(engine, resolve_v2_target(engine, context, expr.get("effect_target", "source")))
        eq_id = str(eval_v2_value(engine, context, expr.get("equipment_id", expr.get("id", ""))) or "")
        total = 0
        for owner in owners:
            try:
                owner_id = int(owner)
            except Exception:
                continue
            if not _valid_player(engine, owner_id):
                continue
            for eq in getattr(engine.players[owner_id], "equipment", []):
                if eq_id and getattr(eq, "def_id", "") != eq_id:
                    continue
                if int(getattr(eq, "effect_target", owner_id)) != target_id:
                    continue
                total += 1
        return total
    if op == "hand_full":
        target = resolve_v2_target(engine, context, expr.get("target", "source"))
        player_id = _player_id(engine, target)
        ps = engine.players[player_id] if _valid_player(engine, player_id) else None
        if ps is None:
            return False
        can_add = getattr(ps, "can_add_to_hand", None)
        return not bool(can_add()) if callable(can_add) else len(getattr(ps, "hand", [])) >= int(getattr(ps, "max_hand", 0) or 0)
    if op == "count":
        value = resolve_v2_target(engine, context, expr.get("selector", expr.get("of", expr.get("value", []))))
        return len(value) if isinstance(value, list) else (1 if value is not None else 0)
    if op in ("add", "sub", "mul", "div", "min", "max", "+", "-", "*", "/"):
        math_op = {"+": "add", "-": "sub", "*": "mul", "/": "div"}.get(op, op)
        values = expr.get("values")
        if values is None:
            values = [expr.get("a", 0), expr.get("b", 0)]
        nums = [_to_number(eval_v2_value(engine, context, value)) for value in values]
        if math_op == "add":
            return sum(nums)
        if math_op == "sub":
            return nums[0] - sum(nums[1:]) if nums else 0
        if math_op == "mul":
            out = 1
            for num in nums:
                out *= num
            return out
        if math_op == "div":
            if len(nums) < 2 or nums[1] == 0:
                return 0
            return nums[0] / nums[1]
        return min(nums) if math_op == "min" and nums else (max(nums) if nums else 0)
    if op == "clamp":
        value = _to_number(eval_v2_value(engine, context, expr.get("value", 0)))
        lo = _to_number(eval_v2_value(engine, context, expr.get("min", 0)))
        hi = _to_number(eval_v2_value(engine, context, expr.get("max", value)))
        return max(lo, min(hi, value))
    if op == "random":
        lo = _to_int(eval_v2_value(engine, context, expr.get("min", expr.get("a", 1))))
        hi = _to_int(eval_v2_value(engine, context, expr.get("max", expr.get("b", lo))))
        if hi < lo:
            lo, hi = hi, lo
        return random.randint(lo, hi)
    if op == "floor":
        return math.floor(_to_number(eval_v2_value(engine, context, expr.get("value", 0))))
    if op == "ceil":
        return math.ceil(_to_number(eval_v2_value(engine, context, expr.get("value", 0))))
    if op == "last_damage":
        return context.get("last_damage", 0)
    if op in ("last_positive_hits", "positive_hits"):
        return context.get("last_positive_hits", context.get("vars", {}).get("last_positive_hits", 0))
    if op == "event_value":
        return context.get("event_value", context.get("vars", {}).get("event_value", 0))
    if op in ("damage_amount", "current_damage"):
        return context.get("damage_amount", context.get("damage", context.get("event_value", 0)))
    if op in ("damage_source", "source_player"):
        return context.get("damage_source", context.get("source_player", 0))
    if op in ("target_player",):
        return context.get("target_player", 0)
    if op == "selected_cards_count":
        choice = _active_choice(context)
        ids = choice.get("target_instance_ids")
        if isinstance(ids, list):
            return len(ids)
        return 1 if choice.get("target_instance_id") is not None or choice.get("target_def_id") is not None else 0
    if op == "selected_card_index":
        return _to_int(context.get("selected_card_index", context.get("vars", {}).get("selected_card_index", 0)))
    if op in ("current_card", "this_card"):
        return context.get("card")
    if op in ("selected_card", "choice_card", "chosen_card"):
        return resolve_v2_target(engine, context, op)
    if op == "selected_card_at":
        choice = _active_choice(context)
        ids = choice.get("_selected_card_ids_snapshot") or choice.get("target_instance_ids")
        if not isinstance(ids, list):
            ids = [choice.get("target_instance_id")] if choice.get("target_instance_id") is not None else []
        index = _to_int(eval_v2_value(engine, context, expr.get("index", 1))) - 1
        chosen_cards = context.get("chosen_cards")
        if isinstance(chosen_cards, list) and 0 <= index < len(chosen_cards):
            return chosen_cards[index]
        if 0 <= index < len(ids):
            return _find_card_by_instance_id(engine, ids[index])
        return None
    if op == "status_stack":
        target = resolve_v2_target(engine, context, expr.get("target", "target"))
        return _status_stack(engine, _player_id(engine, target), str(expr.get("status") or ""))
    return expr


def resolve_v2_target(engine, context: Dict[str, Any], selector: Any):
    if isinstance(selector, list):
        return selector
    if isinstance(selector, dict):
        if "selector" in selector:
            return resolve_v2_target(engine, context, selector.get("selector"))
        ref = selector.get("ref") or selector.get("type") or selector.get("op")
        if ref in ("hand", "deck", "discard", "exile", "equipment"):
            player_id = _player_id(engine, resolve_v2_target(engine, context, selector.get("target", "source")))
            return _zone(engine, player_id, ref)
        if ref == "zone":
            zone = str(selector.get("zone") or "hand")
            player_id = _player_id(engine, resolve_v2_target(engine, context, selector.get("target", "source")))
            return _zone(engine, player_id, zone)
        if ref == "card_by_instance_id":
            return _find_card_by_instance_id(engine, eval_v2_value(engine, context, selector.get("instance_id")))
        if ref == "equipment_by_instance_id":
            return _find_equipment_by_instance_id(engine, eval_v2_value(engine, context, selector.get("instance_id")))[1]
        if ref == "current_equipment":
            return resolve_v2_target(engine, context, "current_equipment")
        if ref == "var":
            return context.get("vars", {}).get(selector.get("name"))
        return eval_v2_value(engine, context, selector)
    if isinstance(selector, int):
        return selector
    text = str(selector or "").strip()
    if text in ("source", "self"):
        return int(context.get("source_player", 0))
    if text in ("event_source", "source_id", "last_actor", "damage_source"):
        return int(context.get("source_id", context.get("damage_source", context.get("source_player", 0))))
    if text == "target":
        return int(context.get("target_player", _enemy_id(engine, int(context.get("source_player", 0)))))
    if text == "enemy":
        explicit_target = _explicit_target_id(engine, context)
        if explicit_target is not None:
            return explicit_target
        return _enemy_id(engine, int(context.get("source_player", 0)))
    if text in ("friendly", "self_team", "all_friendlies"):
        source = int(context.get("source_player", 0))
        team_of = getattr(engine, "team_of", None)
        if callable(team_of):
            try:
                own_team = team_of(source)
                return [idx for idx in range(len(engine.players)) if team_of(idx) == own_team]
            except Exception:
                pass
        return [source]
    if text == "teammate":
        friends = resolve_v2_target(engine, context, "all_friendlies")
        return [idx for idx in friends if idx != int(context.get("source_player", 0))]
    if text == "all_players":
        return list(range(len(getattr(engine, "players", []))))
    if text == "all_enemies":
        source = int(context.get("source_player", 0))
        if hasattr(engine, "get_all_enemies"):
            try:
                return list(engine.get_all_enemies(source))
            except Exception:
                pass
        return [i for i in range(len(engine.players)) if i != source]
    if text == "random_enemy":
        enemies = resolve_v2_target(engine, context, "all_enemies")
        return enemies[0] if enemies else _enemy_id(engine, int(context.get("source_player", 0)))
    if text == "random_friendly":
        friends = resolve_v2_target(engine, context, "all_friendlies")
        return friends[0] if friends else int(context.get("source_player", 0))
    if text == "random_player":
        return 0 if not getattr(engine, "players", []) else int(context.get("_rng_index", 0)) % len(engine.players)
    if text in ("hand", "deck", "discard", "exile", "equipment"):
        return _zone(engine, int(context.get("source_player", 0)), text)
    if text in ("choice_target", "selected_target", "chosen_target", "event_target", "target_id"):
        fallback = context.get("target_id", context.get("source_player", 0))
        return int(context.get("target_player", fallback))
    if text in ("chosen_card", "selected_card", "choice_card"):
        chosen = context.get("selected_card") or context.get("chosen_card")
        if chosen is not None:
            return chosen
        action = context.get("current_action") if isinstance(context.get("current_action"), dict) else {}
        choice = action.get("choice") if isinstance(action.get("choice"), dict) else action
        instance_id = choice.get("target_instance_id")
        if instance_id is None and isinstance(choice.get("target_instance_ids"), list) and choice.get("target_instance_ids"):
            instance_id = choice.get("target_instance_ids")[0]
        return _find_card_by_instance_id(engine, instance_id) if instance_id is not None else None
    if text in ("last_created_card", "created_card", "last_copied_card"):
        instance_id = context.get("last_created_card_instance_id")
        if instance_id is None:
            instance_id = getattr(engine, "_last_created_card_instance_id", None)
        return _find_card_by_instance_id(engine, instance_id) if instance_id is not None else None
    if text == "current_card":
        return context.get("card")
    if text == "current_equipment":
        current = context.get("current_equipment")
        if current is not None:
            return current
        instance_id = context.get("selected_equipment_instance_id")
        owner_id = context.get("selected_equipment_owner_id", context.get("source_player", 0))
        if instance_id is not None:
            try:
                owner_id = int(owner_id)
            except Exception:
                owner_id = int(context.get("source_player", 0))
            if _valid_player(engine, owner_id):
                for eq in getattr(engine.players[owner_id], "equipment", []):
                    if getattr(getattr(eq, "card_instance", None), "instance_id", None) == instance_id:
                        return eq
            found_owner, found_eq = _find_equipment_by_instance_id(engine, instance_id)
            return found_eq
        return None
    if text in context.get("vars", {}):
        return context["vars"][text]
    return text


def check_v2_condition(engine, context: Dict[str, Any], cond: Any) -> bool:
    if cond is None:
        return False
    if isinstance(cond, bool):
        return cond
    if isinstance(cond, (int, float, str)):
        return bool(cond)
    if not isinstance(cond, dict):
        return False
    op = cond.get("op") or cond.get("type")
    if op in ("and", "or"):
        parts = cond.get("conditions", cond.get("values", []))
        checks = [check_v2_condition(engine, context, item) for item in parts]
        return all(checks) if op == "and" else any(checks)
    if op == "not":
        return not check_v2_condition(engine, context, cond.get("condition", cond.get("value")))
    if op in ("compare", "eq", "ne", "gt", "gte", "lt", "lte", ">", ">=", "<", "<=", "==", "!="):
        a = eval_v2_value(engine, context, cond.get("a"))
        b = eval_v2_value(engine, context, cond.get("b"))
        operator = cond.get("operator") or {
            "eq": "==", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=",
        }.get(op, op)
        return _compare(a, b, operator)
    if op == "card_has_tag":
        card = _resolve_card(engine, context, cond.get("card", "current_card"))
        tag = str(eval_v2_value(engine, context, cond.get("tag", cond.get("id", ""))) or "").strip()
        return bool(tag and tag in _card_flags(card))
    if op in ("has_status", "has_status_named"):
        target = resolve_v2_target(engine, context, cond.get("target", "target"))
        status_id = str(eval_v2_value(engine, context, cond.get("status", cond.get("id", cond.get("name", "")))) or "")
        return _status_stack(engine, _player_id(engine, target), status_id) > 0
    if op in ("has_tag", "card_has_flag"):
        card = _resolve_card(engine, context, cond.get("card", "current_card"))
        tag = str(eval_v2_value(engine, context, cond.get("tag", cond.get("flag", ""))) or "").strip()
        return bool(tag and tag in _card_flags(card))
    if op in ("zone_exists", "card_exists"):
        return bool(resolve_v2_target(engine, context, cond.get("zone", cond.get("selector", []))))
    if op == "var_compare":
        name = str(cond.get("name") or cond.get("var") or "")
        if "target" in cond:
            target = resolve_v2_target(engine, context, cond.get("target", "source"))
            player_id = _player_id(engine, target)
            suppressed = getattr(engine, "_is_suppressed_status_var", None)
            if callable(suppressed) and suppressed(player_id, name):
                a = 0
            elif _valid_player(engine, player_id):
                a = getattr(engine.players[player_id], "custom_vars", {}).get(name, 0)
            else:
                a = 0
        else:
            a = context.get("vars", {}).get(name, 0)
        b = eval_v2_value(engine, context, cond.get("value", cond.get("b", 0)))
        return _compare(a, b, cond.get("operator") or cond.get("op2") or "==")
    return bool(eval_v2_value(engine, context, cond))


def validate_v2_ui_response(engine, context: Dict[str, Any], component: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(component, dict):
        raise V2RuntimeError("missing v2 ui component")
    if not isinstance(response, dict):
        response = {}

    button = str(response.get("button") or response.get("button_id") or "")
    buttons = component.get("buttons") if isinstance(component.get("buttons"), list) else []
    allowed_buttons = [str(btn.get("id")) for btn in buttons if isinstance(btn, dict) and btn.get("id")]
    if not button and allowed_buttons:
        button = allowed_buttons[0]
    if allowed_buttons and button not in allowed_buttons:
        raise V2RuntimeError("invalid v2 ui button")

    values_in = response.get("values") if isinstance(response.get("values"), dict) else {}
    values_out: Dict[str, Any] = {}
    controls = component.get("controls") if isinstance(component.get("controls"), list) else []
    for control in controls:
        if not isinstance(control, dict):
            continue
        cid = str(control.get("id") or "").strip()
        if not cid:
            continue
        ctype = str(control.get("type") or "text")
        if ctype in ("text", "rich_text", "stat_display", "card_preview"):
            continue
        raw_value = values_in.get(cid, control.get("default"))
        if ctype in ("slider", "number", "number_input"):
            min_value = _to_number(eval_v2_value(engine, context, control.get("min", 0)))
            max_value = _to_number(eval_v2_value(engine, context, control.get("max", min_value)))
            step = _to_number(eval_v2_value(engine, context, control.get("step", 1)))
            value = _to_number(raw_value)
            if value < min_value or value > max_value:
                raise V2RuntimeError(f"v2 ui value out of range: {cid}")
            if step > 0:
                offset = (value - min_value) / step
                if abs(offset - round(offset)) > 1e-6:
                    raise V2RuntimeError(f"v2 ui value does not match step: {cid}")
            values_out[cid] = int(value) if float(value).is_integer() else value
        elif ctype == "select":
            options = _control_options(control)
            allowed = [str(opt.get("value")) for opt in options]
            value = str(raw_value)
            if allowed and value not in allowed:
                raise V2RuntimeError(f"invalid v2 ui select value: {cid}")
            values_out[cid] = value
        elif ctype in ("card_picker", "equipment_picker"):
            try:
                instance_id = int(raw_value)
            except Exception:
                raise V2RuntimeError(f"invalid v2 ui picker value: {cid}")
            zone = str(control.get("zone") or ("equipment" if ctype == "equipment_picker" else "hand"))
            target_id = _player_id(engine, resolve_v2_target(engine, context, control.get("target", "source")))
            if instance_id not in _picker_instance_ids(engine, target_id, zone, ctype):
                raise V2RuntimeError(f"v2 ui picker target not allowed: {cid}")
            values_out[cid] = instance_id
        elif ctype in ("player_picker", "target_picker"):
            try:
                player_id = int(raw_value)
            except Exception:
                raise V2RuntimeError(f"invalid v2 ui player value: {cid}")
            if not _valid_player(engine, player_id):
                raise V2RuntimeError(f"invalid v2 ui player target: {cid}")
            values_out[cid] = player_id
        else:
            values_out[cid] = raw_value
    return {"button": button, "values": values_out}


def _prepare_context(context: Dict[str, Any]) -> Dict[str, Any]:
    ctx = context if isinstance(context, dict) else {}
    ctx.setdefault("vars", {})
    ctx.setdefault("last_damage", 0)
    ctx.setdefault("source_player", 0)
    ctx.setdefault("target_player", None)
    return ctx


def _build_ui_pause(engine, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    component = _resolve_ui_component(engine, context, params.get("component") or params.get("component_id"))
    component = _sanitize_ui_component(engine, context, component)
    target_player = _player_id(engine, resolve_v2_target(engine, context, params.get("target_player", "source")))
    return {
        "request_id": str(uuid.uuid4()),
        "component": component,
        "target_player": target_player,
        "save_as": str(params.get("save_as") or "ui_result"),
        "timeout_ms": max(0, _to_int(eval_v2_value(engine, context, params.get("timeout_ms", 0)))),
        "on_cancel": params.get("on_cancel", []) if isinstance(params.get("on_cancel", []), list) else [],
        "context": context,
    }


def _resolve_ui_component(engine, context: Dict[str, Any], component_ref: Any) -> Dict[str, Any]:
    if isinstance(component_ref, dict):
        return copy.deepcopy(component_ref)
    component_id = str(component_ref or "").strip()
    if not component_id:
        raise V2RuntimeError("request_ui requires component")
    components = getattr(engine, "v2_ui_components", {}) or {}
    component = components.get(component_id)
    if component is None:
        loadout = context.get("loadout") or getattr(engine, "v2_loadout", None)
        registries = getattr(loadout, "registries", None)
        if isinstance(registries, dict):
            component = (registries.get("ui_components") or {}).get(component_id)
        elif isinstance(loadout, dict):
            component = ((loadout.get("registries") or {}).get("ui_components") or {}).get(component_id)
    if not isinstance(component, dict):
        raise V2RuntimeError(f"unknown v2 ui component: {component_id}")
    return copy.deepcopy(component)


def _sanitize_ui_component(engine, context: Dict[str, Any], component: Dict[str, Any]) -> Dict[str, Any]:
    allowed_component_keys = {
        "id", "type", "title", "title_cn", "title_en",
        "text", "text_cn", "text_en", "controls", "buttons", "style",
    }
    out = {key: copy.deepcopy(component[key]) for key in allowed_component_keys if key in component}
    ctype = str(out.get("type") or "modal")
    if ctype not in {"modal", "confirm", "select", "slider", "number", "number_input", "card_picker", "equipment_picker", "player_picker", "target_picker", "text"}:
        raise V2RuntimeError(f"unsupported v2 ui component type: {ctype}")
    out["type"] = ctype
    controls = out.get("controls") if isinstance(out.get("controls"), list) else []
    out["controls"] = [_sanitize_ui_control(engine, context, control) for control in controls[:50] if isinstance(control, dict)]
    buttons = out.get("buttons") if isinstance(out.get("buttons"), list) else []
    safe_buttons = []
    for button in buttons[:6]:
        if not isinstance(button, dict):
            continue
        bid = str(button.get("id") or "").strip()
        if not bid:
            continue
        safe_buttons.append({
            "id": bid,
            "text": str(button.get("text") or ""),
            "text_cn": str(button.get("text_cn") or button.get("text") or bid),
            "text_en": str(button.get("text_en") or button.get("text") or bid),
            "role": str(button.get("role") or ("cancel" if bid == "cancel" else "confirm")),
        })
    if not safe_buttons:
        safe_buttons = [
            {"id": "confirm", "text_cn": "确认", "text_en": "Confirm", "role": "confirm"},
            {"id": "cancel", "text_cn": "取消", "text_en": "Cancel", "role": "cancel"},
        ]
    out["buttons"] = safe_buttons
    style = out.get("style") if isinstance(out.get("style"), dict) else {}
    out["style"] = {
        key: str(style.get(key))
        for key in ("accent", "icon", "size", "panel")
        if style.get(key) is not None
    }
    return out


def _sanitize_ui_control(engine, context: Dict[str, Any], control: Dict[str, Any]) -> Dict[str, Any]:
    cid = str(control.get("id") or "").strip()
    ctype = str(control.get("type") or "text")
    if not cid:
        raise V2RuntimeError("ui control id is required")
    if ctype not in {"text", "select", "slider", "number", "number_input", "card_picker", "equipment_picker", "player_picker", "target_picker"}:
        raise V2RuntimeError(f"unsupported v2 ui control type: {ctype}")
    out: Dict[str, Any] = {
        "id": cid,
        "type": ctype,
        "label": str(control.get("label") or ""),
        "label_cn": str(control.get("label_cn") or control.get("label") or cid),
        "label_en": str(control.get("label_en") or control.get("label") or cid),
    }
    if ctype in ("slider", "number", "number_input"):
        min_value = _to_number(eval_v2_value(engine, context, control.get("min", 0)))
        max_value = _to_number(eval_v2_value(engine, context, control.get("max", min_value)))
        step = max(0.000001, _to_number(eval_v2_value(engine, context, control.get("step", 1))))
        default = _to_number(eval_v2_value(engine, context, control.get("default", min_value)))
        if max_value < min_value:
            max_value = min_value
        default = min(max(default, min_value), max_value)
        if step > 0 and default > min_value:
            offset = round((default - min_value) / step)
            default = min(max(min_value + offset * step, min_value), max_value)
        out.update({"min": min_value, "max": max_value, "step": step, "default": default})
    elif ctype == "select":
        out["options"] = _control_options(control)
    elif ctype in ("card_picker", "equipment_picker"):
        zone = str(control.get("zone") or ("equipment" if ctype == "equipment_picker" else "hand"))
        target_id = _player_id(engine, resolve_v2_target(engine, context, control.get("target", "source")))
        out["zone"] = zone
        out["target"] = target_id
        out["options"] = _picker_options(engine, target_id, zone, ctype)
    elif ctype in ("player_picker", "target_picker"):
        out["options"] = [{"value": idx, "label": engine.pn(idx)} for idx in range(len(getattr(engine, "players", [])))]
    else:
        out["text"] = str(control.get("text") or control.get("text_cn") or control.get("label_cn") or "")
        out["text_cn"] = str(control.get("text_cn") or control.get("text") or "")
        out["text_en"] = str(control.get("text_en") or control.get("text") or "")
    return out


def _consume_budget(context: Dict[str, Any]) -> None:
    context["_budget"] = int(context.get("_budget", STEP_BUDGET)) - 1
    if context["_budget"] < 0:
        raise V2RuntimeError("v2 step budget exceeded")


def _log_runtime_error(engine, context: Dict[str, Any], effect_type: str, exc: Exception) -> None:
    card = context.get("card")
    player_id = context.get("source_player")
    import traceback; traceback.print_exc()
    if hasattr(engine, "_log_mod_runtime_error"):
        engine._log_mod_runtime_error(effect_type, exc, player_id, card)
    elif hasattr(engine, "log_msg"):
        engine.log_msg("模组执行出现了一个意外错误。请联系管理员。")


def _valid_player(engine, player_id: int) -> bool:
    return isinstance(player_id, int) and 0 <= player_id < len(getattr(engine, "players", []))


def _looks_like_target_selector(value: Any) -> bool:
    if isinstance(value, (dict, list, tuple)):
        return True
    text = str(value or "").strip().lower()
    return text in {
        "source", "self", "owner", "you", "current_player",
        "event_source", "source_id", "last_actor", "damage_source",
        "target", "event_target", "choice_target", "selected_target", "chosen_target",
        "enemy", "opponent", "all_players", "all_enemies", "all_opponents",
        "allies", "all_friends", "friends", "friend", "ally", "teammate",
        "random_player", "random_enemy", "random_ally",
    }


def _player_id(engine, value: Any) -> int:
    if isinstance(value, list):
        value = value[0] if value else 0
    try:
        player_id = int(value)
    except Exception:
        player_id = 0
    return player_id if _valid_player(engine, player_id) else 0


def _as_player_list(engine, value: Any) -> List[int]:
    values = value if isinstance(value, list) else [value]
    out = []
    for item in values:
        try:
            player_id = int(item)
        except Exception:
            continue
        if _valid_player(engine, player_id):
            out.append(player_id)
    return out


def _choice_target_id(choice: Any) -> Optional[int]:
    if not isinstance(choice, dict):
        return None
    for key in ("target_player", "target_player_id", "target_id"):
        if key not in choice:
            continue
        try:
            target_id = int(choice.get(key))
        except Exception:
            continue
        if target_id >= 0:
            return target_id
    return None


def _explicit_target_id(engine, context: Dict[str, Any]) -> Optional[int]:
    if not isinstance(context, dict) or not context.get("target_player_explicit"):
        return None
    try:
        target_id = int(context.get("target_player"))
    except Exception:
        return None
    return target_id if _valid_player(engine, target_id) else None


def _enemy_id(engine, source: int) -> int:
    target = 1 - source if len(getattr(engine, "players", [])) == 2 else 0
    if target == source and len(getattr(engine, "players", [])) > 1:
        target = 1
    return target


def _zone(engine, player_id: int, zone: str):
    if not _valid_player(engine, player_id):
        return []
    return getattr(engine.players[player_id], zone, []) if zone in {"hand", "deck", "discard", "exile", "equipment"} else []


def _control_options(control: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_options = control.get("options", [])
    if not isinstance(raw_options, list):
        return []
    options = []
    for item in raw_options[:200]:
        if isinstance(item, dict):
            value = item.get("value", item.get("id", item.get("label", "")))
            label = item.get("label", item.get("text", value))
            options.append({
                "value": str(value),
                "label": str(label),
                "label_cn": str(item.get("label_cn") or item.get("text_cn") or label),
                "label_en": str(item.get("label_en") or item.get("text_en") or label),
            })
        else:
            options.append({"value": str(item), "label": str(item), "label_cn": str(item), "label_en": str(item)})
    return options


def _picker_instance_ids(engine, target_id: int, zone: str, picker_type: str) -> List[int]:
    if not _valid_player(engine, target_id):
        return []
    if picker_type == "equipment_picker":
        return [
            int(getattr(getattr(eq, "card_instance", None), "instance_id", -1))
            for eq in getattr(engine.players[target_id], "equipment", [])
        ]
    cards = _zone(engine, target_id, zone)
    return [int(getattr(card, "instance_id", -1)) for card in cards if isinstance(card, CardInstance)]


def _picker_options(engine, target_id: int, zone: str, picker_type: str) -> List[Dict[str, Any]]:
    if not _valid_player(engine, target_id):
        return []
    options = []
    if picker_type == "equipment_picker":
        for eq in getattr(engine.players[target_id], "equipment", []):
            card = getattr(eq, "card_instance", None)
            if card is not None:
                options.append({"value": card.instance_id, "label": card.name_cn, "card": card.to_dict()})
        return options
    for card in _zone(engine, target_id, zone):
        if isinstance(card, CardInstance):
            options.append({"value": card.instance_id, "label": card.name_cn, "card": card.to_dict()})
    return options


def _resolve_card(engine, context: Dict[str, Any], selector: Any):
    value = resolve_v2_target(engine, context, selector)
    if isinstance(value, CardInstance):
        return value
    if isinstance(value, list):
        return value[0] if value and isinstance(value[0], CardInstance) else None
    return None


def _active_choice(context: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(context, dict):
        return {}
    choice = context.get("choice")
    if isinstance(choice, dict):
        return choice
    action = context.get("current_action")
    if isinstance(action, dict):
        nested = action.get("choice")
        if isinstance(nested, dict):
            return nested
        return action
    return {}


def _resolve_equipment(engine, context: Dict[str, Any], owner_id: int, selector: Any):
    if selector in (None, "", "first"):
        return engine.players[owner_id].equipment[0] if engine.players[owner_id].equipment else None
    value = resolve_v2_target(engine, context, selector)
    if value in engine.players[owner_id].equipment:
        return value
    try:
        instance_id = int(value)
    except Exception:
        return None
    for eq in engine.players[owner_id].equipment:
        if getattr(eq.card_instance, "instance_id", None) == instance_id:
            return eq
    return None


def _move_card(engine, card: CardInstance, owner_id: int, zone: str, already_detached: bool = False) -> None:
    if not _valid_player(engine, owner_id):
        return
    if not already_detached:
        _detach_card(engine, card)
    elif hasattr(engine, "_apply_setup_modifiers_to_card"):
        try:
            engine._apply_setup_modifiers_to_card(owner_id, card)
        except Exception:
            pass
    ps = engine.players[owner_id]
    if zone == "hand":
        ps.add_to_hand(card) if ps.can_add_to_hand() or card.def_id == ERROR_CARD_ID else ps.discard.append(card)
    elif zone == "deck":
        ps.deck.append(card)
    elif zone == "exile":
        ps.exile.append(card)
    else:
        ps.discard.append(card)
    if zone in ("hand", "deck", "discard") and hasattr(engine, "_enforce_unique_cards_for_player"):
        try:
            engine._enforce_unique_cards_for_player(owner_id, preferred_card=card)
        except Exception:
            pass


def _detach_card(engine, card: CardInstance) -> None:
    for ps in getattr(engine, "players", []):
        for zone in ("hand", "deck", "discard", "exile"):
            cards = getattr(ps, zone, [])
            if card in cards:
                cards.remove(card)
                return
        for eq in list(getattr(ps, "equipment", [])):
            if getattr(eq, "card_instance", None) is card:
                ps.equipment.remove(eq)
                return


def _player_stat(engine, player_id: int, stat: str):
    if not _valid_player(engine, player_id):
        return 0
    ps = engine.players[player_id]
    aliases = {
        "h": "health",
        "e": "elixir",
        "m": "magic",
        "hand_count": "hand",
        "deck_count": "deck",
        "max_hand": "hand_limit",
        "hand_limit_bonus": "extra_hand_limit_bonus",
    }
    stat = aliases.get(str(stat), str(stat))
    if stat == "hand":
        return len(ps.hand)
    if stat == "deck":
        return len(ps.deck)
    if stat == "discard":
        return len(ps.discard)
    if stat == "exile":
        return len(ps.exile)
    if stat == "equipment":
        return len(ps.equipment)
    if stat == "hand_limit" and hasattr(ps, "hand_limit"):
        return ps.hand_limit()
    return getattr(ps, stat, 0)


def _card_prop(card: Optional[CardInstance], prop: str):
    if card is None:
        return 0
    prop = str(prop or "")
    if prop in ("base_hits", "base_petals", "base_petal_count"):
        card_def = getattr(card, "card_def", None)
        return max(1, int(getattr(card_def, "hits", 1) or 1))
    if prop in ("total_hits", "petals", "petal_count", "子瓣"):
        card_def = getattr(card, "card_def", None)
        base = max(1, int(getattr(card_def, "hits", 1) or 1))
        return max(1, base + max(0, int(getattr(card, "extra_hits", 0) or 0)))
    if hasattr(card, prop):
        return getattr(card, prop)
    card_def = getattr(card, "card_def", None)
    if card_def and hasattr(card_def, prop):
        return getattr(card_def, prop)
    if prop == "id":
        return card.def_id
    if prop == "type":
        return card.card_type
    if prop in ("flags", "tags"):
        return list(_card_flags(card))
    return 0


def _equipment_prop(equipment: Any, prop: str):
    if equipment is None:
        return 0
    prop = str(prop or "")
    if hasattr(equipment, prop):
        return getattr(equipment, prop)
    if isinstance(getattr(equipment, "custom_vars", None), dict) and prop in equipment.custom_vars:
        return equipment.custom_vars.get(prop, 0)
    card = getattr(equipment, "card_instance", None)
    if prop in ("card", "card_instance"):
        return card
    return _card_prop(card, prop)


def _find_card_by_instance_id(engine, instance_id: Any):
    try:
        target_instance_id = int(instance_id)
    except Exception:
        return None
    for ps in getattr(engine, "players", []):
        for zone in ("hand", "deck", "discard", "exile"):
            for card in getattr(ps, zone, []):
                if getattr(card, "instance_id", None) == target_instance_id:
                    return card
        for eq in getattr(ps, "equipment", []):
            card = getattr(eq, "card_instance", None)
            if getattr(card, "instance_id", None) == target_instance_id:
                return card
    return None


def _find_equipment_by_instance_id(engine, instance_id: Any):
    try:
        target_instance_id = int(instance_id)
    except Exception:
        return None, None
    for owner_id, ps in enumerate(getattr(engine, "players", [])):
        for eq in getattr(ps, "equipment", []):
            card = getattr(eq, "card_instance", None)
            if getattr(card, "instance_id", None) == target_instance_id:
                return owner_id, eq
    return None, None


def _card_flags(card: Optional[CardInstance]) -> set:
    if card is None:
        return set()
    card_def = getattr(card, "card_def", None)
    flags = set(getattr(card_def, "flags", set()) or set())
    flags.update(getattr(card, "instance_flags", set()) or set())
    flags.difference_update(getattr(card, "disabled_flags", set()) or set())
    return flags


def _v2_status_definition(engine, status_id: str) -> Dict[str, Any]:
    defs = getattr(engine, "v2_status_defs", {}) or {}
    status = defs.get(str(status_id or ""))
    return status if isinstance(status, dict) else {}


def _apply_status(engine, player_id: int, status_id: str, amount: int, op: str) -> None:
    ps = engine.players[player_id]
    status_key = str(status_id or "").split(":")[-1]
    if status_key in ("status_immune", "immune", "状态免疫"):
        ps.custom_statuses = getattr(ps, "custom_statuses", {})
        before = 1 if any(int(ps.custom_statuses.get(key, 0) or 0) > 0 for key in ("status_immune", "immune", "状态免疫")) else 0
        for key in ("status_immune", "immune", "状态免疫"):
            ps.custom_statuses.pop(key, None)
        if op != "remove_status" and amount > 0:
            ps.custom_statuses["status_immune"] = 1
        after = 1 if int(ps.custom_statuses.get("status_immune", 0) or 0) > 0 else 0
        if op == "add_status" and before <= 0 < after:
            engine.log_msg(f"{engine.pn(player_id)}获得状态免疫")
        elif op == "remove_status" and before > 0 and after <= 0:
            engine.log_msg(f"{engine.pn(player_id)}失去状态免疫")
        elif op == "set_status":
            engine.log_msg(f"{engine.pn(player_id)}{'获得' if after else '失去'}状态免疫")
        return
    if _status_application_blocked_by_immunity(engine, player_id, status_id, amount, op):
        return
    attr = _builtin_status_attr(status_id)
    before = _status_stack(engine, player_id, status_id)
    if attr:
        current = int(getattr(ps, attr, 0) or 0)
        if op == "remove_status":
            value = max(0, current - max(1, amount))
        elif op == "set_status":
            value = max(0, amount)
        else:
            value = max(0, current + amount)
        setattr(ps, attr, value)
    else:
        status_def = _v2_status_definition(engine, status_id)
        stacking = str(status_def.get("stacking") or "stack")
        ps.custom_statuses = getattr(ps, "custom_statuses", {})
        current = int(ps.custom_statuses.get(status_id, 0) or 0)
        if op == "remove_status":
            value = max(0, current - max(1, amount))
        elif op == "set_status":
            value = 1 if stacking == "unique" and amount > 0 else max(0, amount)
        else:
            if stacking == "unique":
                value = 1 if amount > 0 else current
            elif stacking == "duration":
                value = max(current, max(0, amount))
            else:
                value = max(0, current + amount)
        keep_zero = bool(status_def.get("keep_when_zero") or status_def.get("keep_zero"))
        if value <= 0 and not keep_zero:
            ps.custom_statuses.pop(status_id, None)
        else:
            ps.custom_statuses[status_id] = max(0, value)
    after = _status_stack(engine, player_id, status_id)
    if before <= 0 < after and hasattr(engine, "_run_v2_status_event"):
        engine._run_v2_status_event(player_id, status_id, "on_apply", {"amount": after - before})
    if before > 0 and after <= 0 and hasattr(engine, "_run_v2_status_event"):
        engine._run_v2_status_event(player_id, status_id, "on_remove", {"amount": before})
    delta = after - before
    label = _status_label(status_id)
    if op == "add_status" and delta:
        engine.log_msg(f"{engine.pn(player_id)}+{abs(delta)}层{label}")
    elif op == "remove_status" and delta:
        engine.log_msg(f"{engine.pn(player_id)}-{abs(delta)}层{label}")
    elif op == "set_status":
        engine.log_msg(f"{engine.pn(player_id)}的{label}变为{after}层")


def _status_application_blocked_by_immunity(engine, player_id: int, status_id: str, amount: int, op: str) -> bool:
    if not _valid_player(engine, player_id):
        return True
    # 状态免疫不阻止状态写入，只压制状态生效。
    return False


def _status_stack(engine, player_id: int, status_id: str) -> int:
    if not _valid_player(engine, player_id):
        return 0
    immune = getattr(engine, "_is_status_immune", None)
    status_key = str(status_id or "").split(":")[-1]
    if callable(immune) and immune(player_id) and status_key not in ("status_immune", "immune", "状态免疫"):
        return 0
    ps = engine.players[player_id]
    if status_key in ("status_immune", "immune", "状态免疫"):
        return 1 if any(int(getattr(ps, "custom_statuses", {}).get(key, 0) or 0) > 0 for key in ("status_immune", "immune", "状态免疫")) else 0
    attr = _builtin_status_attr(status_id)
    if attr:
        return int(getattr(ps, attr, 0) or 0)
    return int(getattr(ps, "custom_statuses", {}).get(status_id, 0) or 0)


def _builtin_status_attr(status_id: str) -> str:
    text = str(status_id or "").split(":")[-1]
    return {
        "poison": "poison",
        "p": "poison",
        "fire": "fire",
        "burn": "fire",
        "f": "fire",
        "toxic": "toxic",
        "vulnerable": "vulnerable",
        "armor": "armor",
        "dodge": "dodge",
        "sluggish": "sluggish",
        "overload": "overload",
        "foresight": "foresight",
        "预知": "foresight",
        "fracture": "fracture",
        "破损": "fracture",
        "stagnation": "stagnation",
        "滞留": "stagnation",
        "blind": "blind",
        "失明": "blind",
        "heal_block": "heal_block",
        "weakness": "weakness",
        "bleed": "bleed",
        "fragment": "fragment_stacks",
        "fragment_stacks": "fragment_stacks",
        "stunned": "skip_turn",
        "skip_turn": "skip_turn",
        "attack_blocked": "attack_blocked",
        "禁攻": "attack_blocked",
        "attack_only": "attack_only",
        "仅攻击": "attack_only",
        "untargetable": "untargetable",
        "无法选中": "untargetable",
    }.get(text, "")


def _status_label(status_id: str) -> str:
    text = str(status_id or "").split(":")[-1]
    return {
        "poison": "中毒",
        "p": "中毒",
        "fire": "灼烧",
        "burn": "灼烧",
        "f": "灼烧",
        "toxic": "淬毒",
        "vulnerable": "易伤",
        "armor": "护甲",
        "dodge": "闪避",
        "sluggish": "迟缓",
        "overload": "超载",
        "foresight": "预知",
        "fracture": "破损",
        "stagnation": "滞留",
        "blind": "失明",
        "heal_block": "禁疗",
        "weakness": "虚弱",
        "bleed": "流血",
        "fragment": "碎片",
        "fragment_stacks": "碎片",
        "stunned": "眩晕",
        "skip_turn": "眩晕",
        "attack_blocked": "禁攻",
        "禁攻": "禁攻",
        "attack_only": "仅攻击",
        "仅攻击": "仅攻击",
        "untargetable": "无法选中",
        "无法选中": "无法选中",
        "status_immune": "状态免疫",
        "immune": "状态免疫",
        "状态免疫": "状态免疫",
    }.get(text, status_id or "状态")


def _to_number(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _to_int(value: Any) -> int:
    try:
        return int(math.floor(float(value)))
    except Exception:
        return 0


def _compare(a: Any, b: Any, operator: str) -> bool:
    if operator in (">", ">=", "<", "<="):
        left = _to_number(a)
        right = _to_number(b)
        if operator == ">":
            return left > right
        if operator == ">=":
            return left >= right
        if operator == "<":
            return left < right
        return left <= right
    if operator in ("!=", "<>"):
        return a != b
    if operator in ("=", "=="):
        return a == b
    return a == b


def _try_run_engine_atomic_op(engine, context: Dict[str, Any], op: str, params: Dict[str, Any], step: Dict[str, Any]):
    if not op or not hasattr(engine, "_run_effect_list"):
        return None
    effect_type = ATOMIC_OP_ALIASES.get(str(op), str(op))
    engine_aliases = getattr(engine, "_EFFECT_ALIASES", {}) or {}
    resolved_type = engine_aliases.get(effect_type, effect_type)
    if (
        effect_type not in ADVANCED_ATOMIC_OPS
        and resolved_type not in ADVANCED_ATOMIC_OPS
        and not callable(getattr(engine, f"_atomic_{resolved_type}", None))
        and not callable(getattr(engine, f"_atomic_{effect_type}", None))
    ):
        return None

    source_selector = step.get("source_player", params.get("source_player", step.get("actor", params.get("actor", "source"))))
    source_id = _player_id(engine, resolve_v2_target(engine, context, source_selector))
    card = context.get("card")
    choice = context.get("choice")
    action = context.get("current_action")
    if choice is None and isinstance(action, dict):
        choice = action.get("choice", action)
    engine_effect = _engine_effect_from_step(engine, context, step, effect_type)
    engine_context = context
    try:
        engine._run_effect_list(source_id, card, [engine_effect], choice if isinstance(choice, dict) else None, engine_context)
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as exc:
        _log_runtime_error(engine, context, effect_type, exc)
    return {"success": True}


def _engine_effect_from_step(
    engine,
    context: Dict[str, Any],
    step: Dict[str, Any],
    effect_type: Optional[str] = None,
    defer_values: bool = False,
) -> Dict[str, Any]:
    resolved_effect_type = effect_type or ATOMIC_OP_ALIASES.get(
        str(step.get("op") or step.get("type") or ""),
        str(step.get("op") or step.get("type") or ""),
    )
    raw_params = step.get("params") if isinstance(step.get("params"), dict) else {
        key: value
        for key, value in step.items()
        if key not in {"op", "type", "log", "then", "else", "steps", "body", "condition", "cond"}
    }
    params = copy.deepcopy(raw_params) if defer_values else _materialize_atomic_value(engine, context, raw_params)
    if not isinstance(params, dict):
        params = {}
    if "condition" in step or "cond" in step:
        params["condition"] = _normalize_condition_for_engine(engine, context, step.get("condition", step.get("cond")))
    if isinstance(step.get("then"), list):
        params["then"] = [_engine_effect_from_step(engine, context, child, defer_values=True) for child in step.get("then", []) if isinstance(child, dict)]
    if isinstance(step.get("else"), list):
        params["else"] = [_engine_effect_from_step(engine, context, child, defer_values=True) for child in step.get("else", []) if isinstance(child, dict)]
    body = step.get("body", step.get("steps"))
    if isinstance(body, list):
        params["body"] = [_engine_effect_from_step(engine, context, child, defer_values=True) for child in body if isinstance(child, dict)]
        params.setdefault("effects", params["body"])
    for target_key in ("target", "targets", "owner", "effect_target", "target_player"):
        if target_key in params:
            params[target_key] = _engine_target_selector(engine, context, params[target_key])
    return {
        "type": resolved_effect_type,
        "params": params,
        "log": step.get("log"),
    }


def _materialize_atomic_value(engine, context: Dict[str, Any], value: Any):
    if isinstance(value, list):
        return [_materialize_atomic_value(engine, context, item) for item in value]
    if not isinstance(value, dict):
        return value
    marker = value.get("op") or value.get("ref") or value.get("type")
    if marker in {
        "const", "literal", "var", "temp_var", "player_var", "global_var", "player_stat",
        "player_property", "card_prop", "card_property", "equipment_prop", "equipment_property",
        "zone_count", "hand_count", "deck_count", "discard_count", "exile_count",
        "equipment_count_targeting",
        "equipment_count", "hand_full", "count", "add", "sub", "mul", "div", "+", "-",
        "*", "/", "min", "max", "clamp", "floor", "ceil", "last_damage", "event_value",
        "damage_amount", "current_damage", "damage_source", "source_player", "target_player",
        "status_stack", "get",
    }:
        return eval_v2_value(engine, context, value)
    return {key: _materialize_atomic_value(engine, context, item) for key, item in value.items()}


def _normalize_condition_for_engine(engine, context: Dict[str, Any], condition: Any):
    if not isinstance(condition, dict):
        return {"op": "compare", "a": bool(condition), "operator": "==", "b": True}
    op = condition.get("op") or condition.get("type")
    if op in ("and", "or", "not", "compare", "eq", "ne", "gt", "gte", "lt", "lte", ">", ">=", "<", "<=", "==", "!="):
        return condition
    return {"op": "compare", "a": check_v2_condition(engine, context, condition), "operator": "==", "b": True}


def _engine_target_selector(engine, context: Dict[str, Any], value: Any):
    if isinstance(value, list):
        return [_engine_target_selector(engine, context, item) for item in value]
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return value
    source = _player_id(engine, context.get("source_player", 0))
    target = _player_id(engine, context.get("target_player", _enemy_id(engine, source)))
    player_count = len(getattr(engine, "players", []))
    if value in ("source", "self"):
        return "self"
    if value in ("target", "event_target", "chosen_target", "choice_target"):
        explicit_target = _explicit_target_id(engine, context)
        if explicit_target is not None:
            return explicit_target
        if player_count <= 2:
            return "self" if target == source else "enemy"
        return target
    if value == "enemy":
        explicit_target = _explicit_target_id(engine, context)
        if explicit_target is not None and player_count > 2:
            return explicit_target
        return "enemy"
    if value == "all_friendlies":
        return "all_friendlies"
    if value == "all_enemies":
        return "all_enemies"
    return value


def _format_message(message: str, context: Dict[str, Any]) -> str:
    try:
        return message.format(**context.get("vars", {}), last_damage=context.get("last_damage", 0))
    except Exception:
        return message
