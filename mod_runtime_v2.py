from __future__ import annotations

import copy
import math
import random
import re
import uuid
from contextlib import nullcontext
from typing import Any, Dict, Iterable, List, Optional

from cards import (
    CARD_DEFS,
    CardInstance,
    ERROR_CARD_ID,
    clamp_card_extra_hits,
    clamp_card_power,
    clamp_damage_hits,
)
from damage_types import DAMAGE_TYPE_PHYSICAL
from runtime_budget import ActionWorkBudgetExceeded


STEP_BUDGET = 1000
FOR_EACH_LIMIT = 200


ADVANCED_ATOMIC_OPS = {
    "after_all", "random", "break", "continue", "if_else", "repeat", "repeat_until",
    "for_each", "for_each_selected_card", "for_each_list",
    "damage", "damage_multi", "direct_damage", "lifesteal_damage", "triangle_damage",
    "heal", "draw", "gain_e", "gain_m", "add_armor", "remove_armor", "set_armor",
    "poison", "burn", "toxic", "dodge_this",
    "dodge_permanent", "clear_buffs", "clear_debuffs", "clear_all_effects",
    "clear_status", "status_add_named", "status_remove_named", "set_status_named",
    "cost_e", "cost_m", "mod_e_regen", "mod_m_regen", "mod_draw",
    "discard", "choose_from_deck", "choose_from_discard", "choose_from_exile",
    "reveal_enemy_hand", "reveal_hand", "reveal_deck_top", "steal_enemy_card",
    "reveal_hand_cards",
    "steal_card", "copy_card", "copy_choice_with_discount", "random_discard_from_hand",
    "put_card_to_deck", "shuffle_discard_into_deck", "give_card_to_hand",
    "give_card_to_deck", "give_card_to_discard", "remove_specific_card",
    "move_to_hand", "move_to_discard", "move_to_deck", "move_to_exile",
    "destroy_random_equip", "destroy_all_equip", "destroy_all_field_equip",
    "destroy_all_destroyable_equipment", "destroy_self_equipment",
    "destroy_equipment_choice_or_first", "equip_protection", "remove_equip_protection",
    "place_as_equip", "add_equipment_to_zone", "trigger_manual",
    "block_action", "block_card_type", "force_card_type", "nullify_current_card",
    "invincible", "untargetable", "skip_turn", "extra_turn",
    "set_health",
    "force_end_turn", "mark_self_damage_source", "fission", "fusion",
    "multiply_next_damage", "reduce_next_cost", "increase_next_cost",
    "add_tag", "add_tag_to_zone", "remove_tag", "tag_add_named", "tag_remove_named", "clear_tags",
    "transform_card", "gain_durability", "lose_durability", "set_durability",
    "record_play_count", "record_equip_turns", "reset_counter", "create_counter",
    "exile_this", "global_damage_mult", "global_heal_mult", "global_cost_mult",
    "swap_health", "swap_hands", "broadcast_event", "modify_damage",
    "var_set", "var_add", "var_sub", "var_mul", "var_div",
    "list_set", "list_append", "list_insert", "list_delete",
    "list_clear", "for_each_list", "timed_effect", "countdown_var",
    "defer_game_over", "random_zone_card_to_hand", "random_move_card_to_hand",
    "move_random_card_to_hand",
    "seal_equipment", "move_cards_to_deck", "clear_statuses", "settle_status",
    "queue_auto_play", "auto_play_queue_add", "auto_play_zone_top", "ricochet_attack",
    "for_each_target",
    "absorb_attack_damage", "add_charge_to_hand", "register_play_listener",
    "card_var_set", "card_var_add",
    "reveal_card_set",
    "snapshot_card_props", "set_card_prop_random", "restore_card_props",
    "transform_cards",
    "deck_catalog_pick", "deck_catalog_pick_resume",
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
    "plank_immunity",
    "magic_relic_trigger", "electric_web_arm",
    "yin_yang_effect", "flower_burst",
    "draw_to_hand_limit", "magic_salt_reflect", "third_eye_precision_or_hidden",
    "grant_temp_swift_highest_e", "delayed_blind_next_turn",
    "delayed_reveal_hand_next_turn",
    "ocean_for_each_selectable_target",
    "declare_forced_target",
}

# 旧名 → 新名。只保留仍被卡数据、测试或工具引用的条目；已经没有任何引用
# 的别名（add_card_tag / set_card_prop / equip_card / show_initial_deck 等
# 12 条）在 Round 4 移除，见 .codex-tmp/round4/rd4_deadcode.md。
ATOMIC_OP_ALIASES = {
    "gain_armor": "add_armor",
    "apply_poison": "poison",
    "apply_burn": "burn",
    "apply_toxic": "toxic",
    "auto_play_queue_add": "queue_auto_play",
    "queue_auto_play_card": "queue_auto_play",
    "kitty_auto_play": "auto_play_zone_top",
    "bounce_attack": "ricochet_attack",
    "ocean_for_each_selectable_target": "for_each_target",
    "for_each_selectable_target": "for_each_target",
    "garden_show_initial_deck": "reveal_card_set",
    "set_card_var": "card_var_set",
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
    except ActionWorkBudgetExceeded:
        raise
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
    consume = getattr(engine, "_consume_action_work", None)
    if callable(consume):
        consume()
    _consume_budget(context)
    if not isinstance(step, dict):
        raise V2RuntimeError("step must be an object")
    op = step.get("op") or step.get("type")
    params = step.get("params") if isinstance(step.get("params"), dict) else step

    # Step gate: ``condition``/``run_if`` must hold, ``unless``/``skip_if`` must
    # not.  Control-flow ops (``if``/``if_else``/``repeat_until``) keep their own
    # ``condition`` operand and are gated by ``unless``/``run_if`` only.
    # An unreadable gate is logged and the step runs (pre-Round-13 behaviour);
    # a broken gate must never abort the event nor silently drop the step.
    try:
        gate_allows = step_gate_allows(engine, context, step, op, params)
    except ActionWorkBudgetExceeded:
        raise
    except Exception as exc:
        _report_unreadable_gate(engine, context, {"op": f"gate-error:{exc}"})
        gate_allows = True
    if not gate_allows:
        return {"success": True, "skipped": True, "reason": "step_condition"}

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
        if card is not None and hasattr(engine, "_effective_card_flags"):
            try:
                card_flags = engine._effective_card_flags(card) or card_flags
            except Exception:
                pass
        is_precision = bool(params.get("is_precision", params.get("precision", False))) or "precision" in card_flags
        crit_bonus_multiplier = 1.0
        try:
            crit_bonus_multiplier = float(params.get("crit_bonus_multiplier", 1.0) or 1.0)
        except (TypeError, ValueError):
            crit_bonus_multiplier = 1.0
        crit_bonus_damage = max(0, _to_int(eval_v2_value(engine, context, params.get("crit_bonus_damage", 0))))
        if card is not None and params.get("precognition") and not is_precision:
            predictor = getattr(engine, "_attack_will_crit_before_dodge", None)
            if callable(predictor) and predictor(source, amount, hits, card):
                # Temporary Precision for this play only; the bonus multiplier
                # is applied after shields by deal_attack_damage.
                is_precision = True
        force_crit = bool(params.get("force_crit", False))
        no_luck_crit = bool(params.get("no_luck_crit", False))
        prev_crit_hits = getattr(engine, "_hel_current_crit_hits", 0)
        old_force = getattr(card, "_hel_force_crit", False) if card is not None else False
        old_no_luck = getattr(card, "_hel_no_luck_crit", False) if card is not None else False
        if card is not None:
            if force_crit:
                card._hel_force_crit = True
            if no_luck_crit:
                card._hel_no_luck_crit = True
        engine._hel_current_crit_hits = 0
        targets = _as_player_list(engine, resolve_v2_target(engine, context, params.get("target", "target")))
        total = 0
        positive_hits = 0
        for target_id in targets:
            if not _valid_player(engine, target_id):
                continue
            engine._hel_current_crit_hits = 0
            # Fission splits this card's Power bonus across its copies, exactly
            # like the engine's own attack helper does.
            original_power = None
            if card is not None and hasattr(engine, "_effective_card_flags"):
                try:
                    original_power = clamp_card_power(getattr(card, "power_value", 0) or 0)
                    fission_level = max(1, int(getattr(card, "fission_level", 1) or 1))
                    if original_power and fission_level > 1:
                        card.power_value = int(math.ceil(original_power / fission_level))
                except Exception:
                    original_power = None
            try:
                dealt = engine.deal_attack_damage(
                    target_id,
                    amount,
                    hits,
                    is_precision=is_precision,
                    attacker_id=source,
                    source_card=card,
                    ignore_untargetable=bool(params.get("ignore_untargetable", False)),
                    crit_bonus_multiplier=crit_bonus_multiplier,
                    crit_bonus_damage=crit_bonus_damage,
                )
            except TypeError:
                dealt = engine.deal_attack_damage(target_id, amount, hits, is_precision=is_precision)
            finally:
                if original_power is not None:
                    card.power_value = original_power
            crit_hits = int(getattr(engine, "_hel_current_crit_hits", 0) or 0)
            engine._last_attack_crit_hits = crit_hits
            if hasattr(engine, "_last_damage_value"):
                try:
                    engine._last_damage_value[target_id] = int(dealt or 0)
                except Exception:
                    pass
            total += int(dealt or 0)
            target_positive_hits = 0
            try:
                hit_values = getattr(engine, "_last_positive_damage_hits", [])
                target_positive_hits = int(hit_values[target_id] if isinstance(hit_values, list) and target_id < len(hit_values) else 0)
                positive_hits += target_positive_hits
            except Exception:
                if int(dealt or 0) > 0:
                    target_positive_hits = 1
                    positive_hits += 1
            on_hit = params.get("on_hit")
            on_hit_once = params.get("on_hit_once")
            if int(dealt or 0) > 0 and isinstance(on_hit_once, list):
                child_context = dict(context)
                child_vars = dict(context.get("vars") if isinstance(context.get("vars"), dict) else {})
                child_context.update({
                    "event": "on_hit",
                    "source_player": source,
                    "target_player": target_id,
                    "source_id": source,
                    "target_id": target_id,
                    "damage": int(dealt or 0),
                    "damage_amount": int(dealt or 0),
                    "last_damage": int(dealt or 0),
                    "hit_count": max(1, int(target_positive_hits or 1)),
                    "vars": child_vars,
                })
                child_vars.update({
                    "source_id": source,
                    "target_id": target_id,
                    "damage": int(dealt or 0),
                    "last_damage": int(dealt or 0),
                })
                # The callback belongs to one damaged player: a wide-strike play
                # must not fan the hit effect back out to the whole target set.
                _narrow_wide_targets(child_context, child_vars, target_id)
                run_v2_steps(engine, child_context, on_hit_once)
            if int(dealt or 0) > 0 and isinstance(on_hit, list):
                hit_count = max(1, int(target_positive_hits or 1))
                for hit_index in range(hit_count):
                    child_context = dict(context)
                    child_vars = dict(context.get("vars") if isinstance(context.get("vars"), dict) else {})
                    child_context.update({
                        "event": "on_hit",
                        "source_player": source,
                        "target_player": target_id,
                        "source_id": source,
                        "target_id": target_id,
                        "damage": int(dealt or 0),
                        "damage_amount": int(dealt or 0),
                        "last_damage": int(dealt or 0),
                        "hit_index": hit_index,
                        "vars": child_vars,
                    })
                    child_vars.update({
                        "source_id": source,
                        "target_id": target_id,
                        "damage": int(dealt or 0),
                        "last_damage": int(dealt or 0),
                        "hit_index": hit_index,
                    })
                    _narrow_wide_targets(child_context, child_vars, target_id)
                    run_v2_steps(engine, child_context, on_hit)
            on_crit = params.get("on_crit")
            if crit_hits > 0 and isinstance(on_crit, list):
                child_context = dict(context)
                child_vars = dict(context.get("vars") if isinstance(context.get("vars"), dict) else {})
                child_context.update({
                    "event": "on_crit",
                    "source_player": source,
                    "target_player": target_id,
                    "source_id": source,
                    "target_id": target_id,
                    "damage": int(dealt or 0),
                    "last_damage": int(dealt or 0),
                    "crit_hits": crit_hits,
                    "vars": child_vars,
                })
                child_vars.update({
                    "last_crit_hits": crit_hits,
                    "target_id": target_id,
                    "damage": int(dealt or 0),
                })
                run_v2_steps(engine, child_context, on_crit)
        engine._hel_current_crit_hits = prev_crit_hits
        if card is not None:
            if force_crit and not old_force:
                card.__dict__.pop("_hel_force_crit", None)
            if no_luck_crit and not old_no_luck:
                card.__dict__.pop("_hel_no_luck_crit", None)
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
        hits = max(1, _to_int(eval_v2_value(engine, context, params.get("hits", 1))))
        if params.get("inherit_extra_hits", params.get("use_card_extra_hits", False)) is True:
            card = context.get("card")
            if card is not None and hasattr(engine, "_card_total_hits"):
                try:
                    hits = max(1, int(engine._card_total_hits(card, hits)))
                except Exception:
                    pass
        on_hit = params.get("on_hit")
        on_hit_once = params.get("on_hit_once")
        # ``log: false`` (or ``silent: true``) mutes the per-hit "受到N点X伤害"
        # lines so a card can print its own summary line instead.
        silent_damage = bool(params.get("silent")) or (step.get("log") is False if isinstance(step, dict) else False)
        total = 0
        positive_hits = 0
        for target_id in _as_player_list(engine, resolve_v2_target(engine, context, params.get("target", "target"))):
            if not _valid_player(engine, target_id) or not hasattr(engine, "_deal_direct_damage"):
                continue
            target_total = 0
            target_hits = 0
            for _ in range(hits):
                try:
                    dealt = engine._deal_direct_damage(
                        target_id,
                        amount,
                        source_text,
                        source,
                        damage_type=damage_type,
                        damage_tag=damage_tag,
                        silent=silent_damage,
                    )
                except TypeError:
                    dealt = engine._deal_direct_damage(target_id, amount, source_text, source)
                dealt = max(0, _to_int(dealt))
                target_total += dealt
                if dealt > 0:
                    target_hits += 1
            if hasattr(engine, "_last_damage_value"):
                try:
                    engine._last_damage_value[target_id] = int(target_total)
                except Exception:
                    pass
            total += target_total
            positive_hits += target_hits
            if target_total > 0 and isinstance(on_hit_once, list):
                child_context = dict(context)
                child_vars = dict(context.get("vars") if isinstance(context.get("vars"), dict) else {})
                child_context.update({
                    "event": "on_hit",
                    "source_id": source,
                    "target_id": target_id,
                    "damage": int(target_total),
                    "last_damage": int(target_total),
                    "hit_count": max(1, int(target_hits or 1)),
                    "vars": child_vars,
                })
                child_vars.update({
                    "target_id": target_id,
                    "damage": int(target_total),
                    "last_damage": int(target_total),
                })
                _narrow_wide_targets(child_context, child_vars, target_id)
                run_v2_steps(engine, child_context, on_hit_once)
            if target_total > 0 and isinstance(on_hit, list):
                for hit_index in range(max(1, int(target_hits or 1))):
                    child_context = dict(context)
                    child_vars = dict(context.get("vars") if isinstance(context.get("vars"), dict) else {})
                    child_context.update({
                        "event": "on_hit",
                        "source_id": source,
                        "target_id": target_id,
                        "damage": int(target_total),
                        "last_damage": int(target_total),
                        "hit_index": hit_index,
                        "vars": child_vars,
                    })
                    child_vars.update({
                        "target_id": target_id,
                        "damage": int(target_total),
                        "last_damage": int(target_total),
                        "hit_index": hit_index,
                    })
                    _narrow_wide_targets(child_context, child_vars, target_id)
                    run_v2_steps(engine, child_context, on_hit)
        context["last_damage"] = total
        context["last_positive_hits"] = positive_hits
        context.setdefault("vars", {})["last_positive_hits"] = positive_hits
        return {"success": True, "last_damage": total}

    if op == "counter_pending_attack_damage":
        ratio = float(params.get("ratio", params.get("multiplier", 0.5)) or 0)
        vars_dict = context.get("vars", {}) if isinstance(context.get("vars"), dict) else {}
        action_dict = context.get("current_action", {}) if isinstance(context.get("current_action"), dict) else {}
        incoming = _to_int(
            context.get(
                "first_hit_damage",
                context.get(
                    "first_damage",
                    vars_dict.get(
                        "first_hit_damage",
                        vars_dict.get(
                            "first_damage",
                            action_dict.get("first_hit_damage", action_dict.get("first_damage", 0)),
                        ),
                    ),
                ),
            )
        )
        if incoming <= 0:
            parts = context.get("incoming_damage_parts") or vars_dict.get("incoming_damage_parts") or action_dict.get("incoming_damage_parts")
            if isinstance(parts, (list, tuple)) and parts:
                incoming = _to_int(parts[0])
        amount = max(0, int(math.ceil(incoming * ratio)))
        if amount <= 0:
            return {"success": True, "last_damage": 0}
        raw_source = params.get("source", "source")
        source_selector = raw_source if _looks_like_target_selector(raw_source) else "source"
        source = _player_id(engine, resolve_v2_target(engine, context, source_selector))
        source_text = params.get("source_text") or params.get("source_name") or params.get("label")
        if source_text is None and not _looks_like_target_selector(raw_source):
            source_text = raw_source
        source_text = str(source_text or "反击")
        damage_type = str(params.get("damage_type") or DAMAGE_TYPE_PHYSICAL)
        damage_tag = params.get("damage_tag")
        mode = str(params.get("mode", params.get("damage_mode", "direct")) or "direct").lower()
        total = 0
        target_ref = params.get("target", "target")
        if target_ref in ("all_enemies", "enemies"):
            targets = list(engine.get_all_enemies(source)) if hasattr(engine, "get_all_enemies") else [_enemy_id(engine, source)]
        else:
            targets = _as_player_list(engine, resolve_v2_target(engine, context, target_ref))
        for target_id in targets:
            if not _valid_player(engine, target_id):
                continue
            if mode in ("attack", "physical_attack") and hasattr(engine, "deal_attack_damage"):
                dealt = engine.deal_attack_damage(target_id, amount, 1, is_precision=False, attacker_id=source)
            elif hasattr(engine, "_deal_direct_damage"):
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
            else:
                dealt = 0
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
                # ``log_positive_only`` keeps the old "回复N H" wording while
                # staying silent when nothing was healed (no "未回复生命" line).
                if params.get("log_positive_only") and healed <= 0:
                    continue
                rendered = _render_step_log(engine, step, params, {
                    "target": engine.pn(target_id),
                    "source": engine.pn(_player_id(engine, context.get("source_player", target_id))),
                    "amount": healed,
                    "count": healed,
                })
                if rendered is False:
                    continue
                if rendered:
                    engine.log_msg(rendered)
                elif healed:
                    engine.log_msg(f"{engine.pn(target_id)}回复{healed}H")
                else:
                    engine.log_msg(f"{engine.pn(target_id)}未回复生命")
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
                    rendered = _render_step_log(engine, step, params, {
                        "target": engine.pn(target_id),
                        "source": engine.pn(_player_id(engine, context.get("source_player", target_id))),
                        "amount": len(drawn),
                        "count": len(drawn),
                    })
                    if rendered:
                        engine.log_msg(rendered)
                    elif rendered is not False:
                        engine.log_msg(f"{engine.pn(target_id)}抽{len(drawn)}张牌")
        return {"success": True}

    if op in ("gain_e", "gain_m"):
        amount = _to_int(eval_v2_value(engine, context, params.get("amount", 0)))
        for target_id in _as_player_list(engine, resolve_v2_target(engine, context, params.get("target", "source"))):
            if not _valid_player(engine, target_id):
                continue
            player_state = engine.players[target_id]
            if op == "gain_e":
                before_value = int(getattr(player_state, "elixir", 0) or 0)
            else:
                before_value = int(getattr(player_state, "magic", 0) or 0)
            if op == "gain_e":
                if amount < 0:
                    engine.players[target_id].elixir = max(0, int(engine.players[target_id].elixir) + amount)
                else:
                    engine.players[target_id].gain_elixir(amount)
                default_log = f"{engine.pn(target_id)}获得{amount}E"
            else:
                if amount < 0:
                    engine.players[target_id].magic = max(0, int(engine.players[target_id].magic) + amount)
                else:
                    engine.players[target_id].gain_magic(amount)
                default_log = f"{engine.pn(target_id)}获得{amount}M"
            after_value = int(getattr(player_state, "elixir" if op == "gain_e" else "magic", 0) or 0)
            gained = after_value - before_value
            # ``log_positive_only`` mirrors engines atoms that stayed silent
            # when the resource was already at its cap.
            if params.get("log_positive_only") and gained <= 0:
                continue
            rendered = _render_step_log(engine, step, params, {
                "target": engine.pn(target_id),
                "source": engine.pn(_player_id(engine, context.get("source_player", target_id))),
                "amount": amount,
                "count": amount,
                "gained": gained,
            })
            if rendered is False:
                continue
            engine.log_msg(rendered or default_log)
        return {"success": True}

    if op in ("add_status", "remove_status", "set_status"):
        raw_status = params.get("status", params.get("id", ""))
        status_id = str(eval_v2_value(engine, context, raw_status) or "").strip()
        amount = _to_int(eval_v2_value(engine, context, params.get("amount", params.get("stack", 1))))
        for target_id in _as_player_list(engine, resolve_v2_target(engine, context, params.get("target", "target"))):
            if _valid_player(engine, target_id):
                _apply_status(
                    engine, target_id, status_id, amount, op,
                    log=not step_is_silent(step, params),
                )
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

    if op == "deck_catalog_pick":
        return _start_deck_catalog_pick(engine, context, params)

    if op in ("deck_catalog_pick_resume", "_deck_catalog_pick_resume"):
        return _resume_deck_catalog_pick(engine, context, params)

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
        raw_name = params.get("name", params.get("var", step.get("name", step.get("var", ""))))
        name = str(eval_v2_value(engine, context, raw_name) or "")
        if name:
            context.setdefault("vars", {})[name] = eval_v2_value(engine, context, params.get("value", step.get("value", 0)))
        return {"success": True}

    if op == "add_var":
        raw_name = params.get("name", params.get("var", step.get("name", step.get("var", ""))))
        name = str(eval_v2_value(engine, context, raw_name) or "")
        if name:
            delta = eval_v2_value(engine, context, params.get("value", step.get("value", 0)))
            context.setdefault("vars", {})[name] = _to_int(context["vars"].get(name, 0)) + _to_int(delta)
        return {"success": True}

    if op == "log":
        raw_message = params.get("message", params.get("text", params.get("msg", "")))
        message = str(eval_v2_value(engine, context, raw_message) or "")
        if message and step_is_silent(step, params):
            return {"success": True}
        if message:
            raw_amount = params.get("amount")
            amount = eval_v2_value(engine, context, raw_amount) if raw_amount is not None else None
            engine.log_msg(_format_message(
                message,
                context,
                engine=engine,
                card=context.get("card") or context.get("event_card"),
                amount=amount,
                target=params.get("target"),
            ))
        return {"success": True}

    atomic_result = _try_run_engine_atomic_op(engine, context, op, params, step)
    if atomic_result is not None:
        return atomic_result

    raise V2RuntimeError(f"unsupported v2 op: {op}")


def _narrow_wide_targets(context: Dict[str, Any], vars_dict: Dict[str, Any], target_id: int) -> None:
    """Restrict a hit callback to the player that was actually damaged.

    ``on_hit``/``on_hit_once`` run once per damaged player, so a wide-strike
    play must not fan the callback's effects back out to the whole target set.
    """
    for key in ("wide_strike_targets", "target_players"):
        if isinstance(context.get(key), list):
            context[key] = [target_id]
        if isinstance(vars_dict.get(key), list):
            vars_dict[key] = [target_id]


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
        if expr.get("require_selectable"):
            cards = [card for card in cards if _card_selectable_by_action(engine, card)]
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
    if op in ("status_count", "visible_status_count"):
        target = resolve_v2_target(engine, context, expr.get("target", "source"))
        player_id = _player_id(engine, target)
        if not _valid_player(engine, player_id):
            return 0
        ps = engine.players[player_id]
        custom = getattr(ps, "custom_statuses", {}) or {}
        count = sum(1 for value in custom.values() if _to_int(value) > 0)
        for attribute in (
            "poison", "fire", "toxic", "dodge", "sluggish", "overload", "foresight",
            "fracture", "stagnation", "blind", "heal_block", "attack_blocked", "weakness",
            "bleed", "fragment_stacks", "skip_turn",
        ):
            if _to_int(getattr(ps, attribute, 0)) > 0:
                count += 1
        return count
    if op in ("counter_cards_in_hand", "counters_in_hand"):
        target = resolve_v2_target(engine, context, expr.get("target", "source"))
        player_id = _player_id(engine, target)
        if not _valid_player(engine, player_id):
            return 0
        is_counter = getattr(engine, "_is_counter_card", None)
        if not callable(is_counter):
            return 0
        return sum(1 for card in list(getattr(engine.players[player_id], "hand", []) or []) if is_counter(card))
    if op in ("deck_top_ids", "zone_top_ids"):
        target = resolve_v2_target(engine, context, expr.get("target", "source"))
        player_id = _player_id(engine, target)
        zone = str(expr.get("zone") or "deck")
        count = max(0, _to_int(eval_v2_value(engine, context, expr.get("count", 3))))
        cards = _zone(engine, player_id, zone)[:count]
        return [getattr(card, "instance_id", None) for card in cards if getattr(card, "instance_id", None) is not None]
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
    if op == "random_choice":
        raw = expr.get("values", expr.get("options", expr.get("from", [])))
        values = eval_v2_value(engine, context, raw)
        if isinstance(values, dict):
            values = list(values.values())
        if not isinstance(values, list) or not values:
            return expr.get("default", "")
        return random.choice(list(values))
    if op in ("choice_value", "choice_field"):
        choice = _active_choice(context)
        key = str(eval_v2_value(engine, context, expr.get("key", "")) or "")
        if isinstance(choice, dict) and key and choice.get(key) not in (None, ""):
            return choice.get(key)
        return expr.get("default", 0)
    if op == "floor":
        return math.floor(_to_number(eval_v2_value(engine, context, expr.get("value", 0))))
    if op == "ceil":
        return math.ceil(_to_number(eval_v2_value(engine, context, expr.get("value", 0))))
    if op == "last_damage":
        return context.get("last_damage", 0)
    if op in ("last_positive_hits", "positive_hits"):
        return context.get("last_positive_hits", context.get("vars", {}).get("last_positive_hits", 0))
    if op in ("hit_count", "damage_hits"):
        # Positive hit count of the segment that triggered the current
        # on_hit/on_hit_once callback (one entry per damaged player).
        return _to_int(context.get("hit_count", context.get("vars", {}).get("hit_count", 1)))
    if op in ("last_crit_hits", "crit_hits"):
        return context.get("last_crit_hits", context.get("vars", {}).get("last_crit_hits", 0))
    if op in ("play_was_countered", "was_countered"):
        card = context.get("card")
        if card is not None:
            state = getattr(card, "_play_was_countered_this_play", None)
            if state is None:
                state = getattr(card, "_sewers_was_countered_this_play", False)
            return bool(state)
        return bool(context.get("vars", {}).get("play_was_countered", False))
    if op == "event_value":
        return context.get("event_value", context.get("vars", {}).get("event_value", 0))
    if op in ("damage_amount", "current_damage"):
        return context.get("damage_amount", context.get("damage", context.get("event_value", 0)))
    if op in ("damage_source", "source_player"):
        return context.get("damage_source", context.get("source_player", 0))
    if op in ("current_turn_player", "turn_player", "active_player"):
        return _to_int(getattr(engine, "current_player", context.get("source_player", 0)))
    if op in ("card_var", "card_custom_var"):
        card = _resolve_card(engine, context, expr.get("card", "current_card"))
        name = str(expr.get("name") or expr.get("var") or "")
        if card is None or not name:
            return expr.get("default", 0)
        store = getattr(card, "custom_vars", None)
        if not isinstance(store, dict):
            return expr.get("default", 0)
        return store.get(name, expr.get("default", 0))
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
            chosen = chosen_cards[index]
            return chosen if _card_selectable_by_action(engine, chosen) else None
        if 0 <= index < len(ids):
            found = _find_card_by_instance_id(engine, ids[index])
            return found if _card_selectable_by_action(engine, found) else None
        return None
    if op == "status_stack":
        target = resolve_v2_target(engine, context, expr.get("target", "target"))
        return _status_stack(engine, _player_id(engine, target), str(expr.get("status") or ""))
    if op in ("cards_played_this_turn", "played_cards_this_turn", "cards_played"):
        player_id = _player_id(engine, resolve_v2_target(engine, context, expr.get("target", "source")))
        if not _valid_player(engine, player_id):
            player_id = _player_id(engine, context.get("source_player", 0))
        played = getattr(engine.players[player_id], "cards_played_this_turn", {}) if _valid_player(engine, player_id) else {}
        total = 0
        for value in (played or {}).values():
            total += _to_int(value)
        total = max(0, total)
        if expr.get("exclude_current", expr.get("exclude_self", False)):
            actor = _player_id(engine, context.get("source_player", player_id))
            if _valid_player(engine, player_id) and player_id == actor:
                total = max(0, total - 1)
        return total
    if op in ("damage_type", "current_damage_type"):
        return _context_damage_type(context)
    if op in ("card_cost", "actual_card_cost"):
        card = _resolve_card(engine, context, expr.get("card", "current_card"))
        if card is None:
            return 0
        currency = str(expr.get("currency", expr.get("resource", "e")) or "e").strip().lower()
        include_extras = bool(expr.get("include_extras", expr.get("with_extras", False)))
        if include_extras:
            resolver = getattr(engine, "_card_cost_value", None)
            if callable(resolver):
                try:
                    return int(resolver(
                        _player_id(engine, context.get("source_player", 0)),
                        {"card": card, "currency": currency, "include_extras": True},
                        card,
                    ))
                except Exception:
                    pass
        card_def = getattr(card, "card_def", None)
        if currency in ("m", "magic", "mana"):
            override = getattr(card, "cost_m_override", None)
            if override is not None:
                return max(0, _to_int(override))
            return max(0, _to_int(getattr(card_def, "cost_m", 0)))
        override = getattr(card, "cost_e_override", None)
        if override is not None:
            return max(0, _to_int(override))
        return max(0, _to_int(getattr(card_def, "cost_e", 0)))
    return expr


def _deck_catalog_component(engine, cards, params) -> Dict[str, Any]:
    """Picker component listing every (selectable) card of a deck."""
    title_cn = str(params.get("title") or "选择1张牌加入手中")
    title_en = str(params.get("title_en") or "Choose a card to add to your hand")
    return {
        "type": "modal",
        "title_cn": title_cn,
        "title_en": title_en,
        "controls": [{
            "id": "card",
            "type": "card_catalog_picker",
            "label_cn": title_cn,
            "label_en": title_en,
            "options": [
                {
                    "value": str(card.instance_id),
                    "label_cn": card.name_cn,
                    "label_en": card.name_en,
                    "card": card.to_dict(),
                }
                for card in cards
            ],
        }],
        "buttons": [{"id": "confirm", "text_cn": "确认", "text_en": "Confirm", "role": "confirm"}],
        "style": {"accent": "void-dlc"},
    }


def _deck_catalog_candidates(engine, owner_id: int):
    if not _valid_player(engine, owner_id):
        return []
    return [
        card for card in list(getattr(engine.players[owner_id], "deck", []) or [])
        if _card_selectable_by_action(engine, card)
    ]


def _start_deck_catalog_pick(engine, context: Dict[str, Any], params: Dict[str, Any]):
    """Shuffle each target deck, then let the viewer pick one card per deck.

    Generic counterpart of the Cicada 3301 reorder branch.  Because every pick
    needs its own prompt, the loop is suspended through the regular v2 UI pause
    machinery (``remaining_steps`` carries the continuation) instead of relying
    on a data ``for_each``, whose cursor cannot survive a pause.
    """
    source_id = _player_id(engine, resolve_v2_target(engine, context, params.get("source", "source")))
    if not _valid_player(engine, source_id):
        return {"success": True}
    targets = resolve_v2_target(engine, context, params.get("targets", params.get("target", "all_selectable")))
    if not isinstance(targets, (list, tuple)):
        targets = [targets]
    queue = []
    for target in targets:
        try:
            target_id = int(target)
        except (TypeError, ValueError):
            continue
        if _valid_player(engine, target_id) and target_id not in queue:
            queue.append(target_id)
    shuffle_mode = params.get("shuffle", "each")
    if shuffle_mode not in (False, None, "none", "off"):
        for target_id in queue:
            random.shuffle(engine.players[target_id].deck)
    state = {
        "queue": queue,
        "source": source_id,
        "save_as": str(params.get("save_as") or "deck_pick"),
        "params": {
            "pick": max(1, _to_int(params.get("pick", 1))),
            "title": params.get("title"),
            "title_en": params.get("title_en"),
            "log": params.get("log"),
        },
    }
    return _continue_deck_catalog_pick(engine, context, state)


def _continue_deck_catalog_pick(engine, context: Dict[str, Any], state: Dict[str, Any]):
    queue = state.get("queue") if isinstance(state.get("queue"), list) else []
    source_id = _to_int(state.get("source", 0))
    while queue:
        target_id = _to_int(queue[0])
        if not _valid_player(engine, target_id):
            queue.pop(0)
            continue
        cards = _deck_catalog_candidates(engine, target_id)
        if not cards:
            queue.pop(0)
            continue
        state["active"] = target_id
        context.setdefault("vars", {})["_deck_catalog_pick"] = state
        pause = _build_ui_pause(engine, context, {
            "component": _deck_catalog_component(engine, cards, state.get("params") or {}),
            "target_player": source_id,
            "save_as": state.get("save_as") or "deck_pick",
        })
        pause["remaining_steps"] = [{"op": "deck_catalog_pick_resume"}]
        return {"success": True, "needs_v2_ui": True, "v2_ui_pause": pause}
    context.setdefault("vars", {}).pop("_deck_catalog_pick", None)
    return {"success": True}


def _resume_deck_catalog_pick(engine, context: Dict[str, Any], params: Dict[str, Any]):
    state = context.setdefault("vars", {}).pop("_deck_catalog_pick", None)
    if not isinstance(state, dict):
        return {"success": True}
    source_id = _to_int(state.get("source", 0))
    target_id = _to_int(state.get("active", -1))
    values = context.get("vars", {}).get(state.get("save_as") or "deck_pick") or {}
    raw_value = values.get("card") if isinstance(values, dict) else values
    try:
        instance_id = int(raw_value)
    except (TypeError, ValueError):
        instance_id = -1
    selected = _find_card_by_instance_id(engine, instance_id)
    moved = False
    if selected is not None and _card_selectable_by_action(engine, selected):
        owner_id, zone_name, _ = engine._find_card_location(selected)
        if owner_id == target_id and zone_name == "deck":
            engine.players[owner_id].deck.remove(selected)
            engine.players[source_id].add_to_hand(selected)
            moved = True
    queue = state.get("queue") if isinstance(state.get("queue"), list) else []
    if queue and _to_int(queue[0]) == target_id:
        queue.pop(0)
    if moved:
        step_params = state.get("params") or {}
        template = step_params.get("log")
        if isinstance(template, str) and template:
            engine.log_msg(_format_message(
                template,
                {"source_player": source_id, "target_player": target_id, "vars": {}},
                engine=engine,
            ))
    return _continue_deck_catalog_pick(engine, context, state)


def _resolve_random_selectable(engine, context: Dict[str, Any], selector: Dict[str, Any]) -> int:
    """One random selectable player for the generic ``random_selectable`` selector.

    ``exclude`` drops already-chosen players (a selector such as ``"target"`` or a
    list of ids/selectors), ``allow_self`` keeps the actor in the pool and
    ``relation`` narrows it to enemies / friendly players.  Randomness always goes
    through ``forced_random_target`` so the Eyeball-style forced choice still wins.
    """
    selector = selector if isinstance(selector, dict) else {}
    source = _player_id(engine, context.get("source_player", 0))
    if not _valid_player(engine, source):
        source = 0
    allow_self = selector.get("allow_self", True) is not False
    relation = str(selector.get("relation", "any") or "any").strip().lower()
    checker = getattr(engine, "_target_can_be_selected", None)
    candidates: List[int] = []
    for candidate in range(len(getattr(engine, "players", []))):
        if callable(checker):
            try:
                if not checker(source, candidate, allow_self=allow_self):
                    continue
            except TypeError:
                if not checker(source, candidate):
                    continue
        else:
            if candidate == source and not allow_self:
                continue
            if not _valid_player(engine, candidate) or int(getattr(engine.players[candidate], "health", 0) or 0) <= 0:
                continue
        same_side = getattr(engine, "_same_timer_side", None)
        if relation in ("enemy", "enemies", "opponent", "opponents"):
            if candidate == source:
                continue
            if callable(same_side) and same_side(source, candidate):
                continue
        elif relation in ("friendly", "ally", "allies", "team", "same_side"):
            if callable(same_side) and not same_side(source, candidate):
                continue
        candidates.append(candidate)
    raw_exclude = selector.get("exclude")
    if raw_exclude is not None and candidates:
        excluded = set()
        refs = raw_exclude if isinstance(raw_exclude, (list, tuple, set)) else [raw_exclude]
        for item in refs:
            resolved = resolve_v2_target(engine, context, item)
            if isinstance(resolved, list):
                values = resolved
            else:
                values = [resolved]
            for value in values:
                pid = _player_id(engine, value)
                if _valid_player(engine, pid):
                    excluded.add(pid)
        if excluded:
            candidates = [candidate for candidate in candidates if candidate not in excluded]
    if not candidates:
        return -1
    from engine_runtime_support import forced_random_target
    return int(forced_random_target(engine, source, candidates))


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
        if ref in ("random_selectable", "random_selectable_player"):
            return _resolve_random_selectable(engine, context, selector)
        if ref in ("lowest_health_enemy", "lowest_health_enemy_player"):
            resolver = getattr(engine, "_jurassic_lowest_selectable_enemy", None)
            if callable(resolver):
                try:
                    return resolver(int(context.get("source_player", 0)))
                except Exception:
                    return -1
            return -1
        if ref in ("equipment_target", "equip_target", "equipment_effect_target"):
            resolver = getattr(engine, "_resolve_equipment_target_selector", None)
            if callable(resolver):
                try:
                    return resolver(int(context.get("source_player", 0)), selector, context)
                except Exception:
                    return -1
            return int(context.get("target_id", -1))
        if ref in ("equipment_owner", "equip_owner"):
            resolver = getattr(engine, "_resolve_equipment_owner_selector", None)
            if callable(resolver):
                try:
                    return resolver(int(context.get("source_player", 0)))
                except Exception:
                    return int(context.get("source_player", 0))
            return int(context.get("source_player", 0))
        if ref in ("team_members", "team_member", "target_team_members"):
            resolver = getattr(engine, "_resolve_team_members_selector", None)
            if callable(resolver):
                try:
                    return list(resolver(int(context.get("source_player", 0)), selector, context))
                except Exception:
                    return []
            return []
        if ref in ("player_id", "player_at", "raw_player"):
            raw = selector.get("id", selector.get("value", selector.get("player")))
            try:
                return int(eval_v2_value(engine, context, raw))
            except (TypeError, ValueError):
                return -1
        if ref == "var":
            return context.get("vars", {}).get(selector.get("name"))
        return eval_v2_value(engine, context, selector)
    if isinstance(selector, int):
        return selector
    text = str(selector or "").strip()
    if text in ("source", "self"):
        return int(context.get("source_player", 0))
    if text in ("lowest_health_enemy", "lowest_health_enemy_player"):
        resolver = getattr(engine, "_jurassic_lowest_selectable_enemy", None)
        if callable(resolver):
            try:
                return resolver(int(context.get("source_player", 0)))
            except Exception:
                return -1
        return -1
    if text in ("equipment_target", "equip_target", "equipment_effect_target"):
        resolver = getattr(engine, "_resolve_equipment_target_selector", None)
        if callable(resolver):
            try:
                return resolver(int(context.get("source_player", 0)), None)
            except Exception:
                return -1
        return int(context.get("target_id", -1))
    if text in ("equipment_owner", "equip_owner"):
        resolver = getattr(engine, "_resolve_equipment_owner_selector", None)
        if callable(resolver):
            try:
                return resolver(int(context.get("source_player", 0)))
            except Exception:
                return int(context.get("source_player", 0))
        return int(context.get("source_player", 0))
    if text in ("team_members", "team_member", "target_team_members"):
        resolver = getattr(engine, "_resolve_team_members_selector", None)
        if callable(resolver):
            try:
                return list(resolver(int(context.get("source_player", 0)), {"ref": text, "target": "target"}))
            except Exception:
                return []
        return []
    if text in ("event_source", "source_id", "last_actor", "damage_source"):
        return int(context.get("source_id", context.get("damage_source", context.get("source_player", 0))))
    if text == "target":
        wide_targets = context.get("wide_strike_targets")
        if isinstance(wide_targets, list):
            targets = []
            for target_id in wide_targets:
                try:
                    target_id = int(target_id)
                except Exception:
                    continue
                if _valid_player(engine, target_id):
                    targets.append(target_id)
            return targets
        return int(context.get("target_player", _enemy_id(engine, int(context.get("source_player", 0)))))
    if text == "enemy":
        explicit_target = _explicit_target_id(engine, context)
        if explicit_target is not None:
            return explicit_target
        return _enemy_id(engine, int(context.get("source_player", 0)))
    if text == "wide_strike_targets":
        # The engine owns the "chosen by a wide-strike play" target list
        # (``_wide_strike_target_ids`` honours the card's ``self_target`` flag and
        # the play-time target snapshot).  Data steps use this selector instead
        # of ``all_enemies`` so a converted card keeps the exact target set the
        # card-specific wrapper atom used to build.
        source = int(context.get("source_player", 0))
        card = context.get("card")
        if card is None:
            active_context = getattr(engine, "_active_effect_context", None)
            if isinstance(active_context, dict):
                card = active_context.get("card") or active_context.get("event_card")
        if card is None:
            active_damage_card = getattr(engine, "_v2_active_damage_card", None)
            if callable(active_damage_card):
                try:
                    card = active_damage_card()
                except Exception:
                    card = None
        resolver = getattr(engine, "_wide_strike_target_ids", None)
        if not callable(resolver):
            return []
        try:
            return [target_id for target_id in resolver(source, card) if _valid_player(engine, target_id)]
        except Exception:
            return []
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
    if text in ("all_others", "all_except_self", "everyone_else"):
        source = int(context.get("source_player", 0))
        return [idx for idx in range(len(getattr(engine, "players", []))) if idx != source]
    if text in ("random_selectable", "random_selectable_player"):
        return _resolve_random_selectable(engine, context, {})
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
        source = int(context.get("source_player", 0))
        chosen = enemies[0] if enemies else _enemy_id(engine, source)
        from engine_runtime_support import forced_random_target
        return forced_random_target(engine, source, enemies, chosen)
    if text == "random_friendly":
        friends = resolve_v2_target(engine, context, "all_friendlies")
        source = int(context.get("source_player", 0))
        chosen = friends[0] if friends else source
        from engine_runtime_support import forced_random_target
        return forced_random_target(engine, source, friends, chosen)
    if text == "random_player":
        players = list(range(len(getattr(engine, "players", []))))
        if not players:
            return -1
        source = int(context.get("source_player", 0))
        chosen = int(context.get("_rng_index", 0)) % len(players)
        from engine_runtime_support import forced_random_target
        return forced_random_target(engine, source, players, chosen)
    if text in ("hand", "deck", "discard", "exile", "equipment"):
        return _zone(engine, int(context.get("source_player", 0)), text)
    if text in ("choice_target", "selected_target", "chosen_target", "event_target", "target_id"):
        fallback = context.get("target_id", context.get("source_player", 0))
        return int(context.get("target_player", fallback))
    if text in ("chosen_card", "selected_card", "choice_card"):
        chosen = context.get("selected_card") or context.get("chosen_card")
        if chosen is not None:
            return chosen if _card_selectable_by_action(engine, chosen) else None
        action = context.get("current_action") if isinstance(context.get("current_action"), dict) else {}
        choice = action.get("choice") if isinstance(action.get("choice"), dict) else action
        instance_id = choice.get("target_instance_id")
        if instance_id is None and isinstance(choice.get("target_instance_ids"), list) and choice.get("target_instance_ids"):
            instance_id = choice.get("target_instance_ids")[0]
        found = _find_card_by_instance_id(engine, instance_id) if instance_id is not None else None
        return found if _card_selectable_by_action(engine, found) else None
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
    if op in ("card_has_modifier", "card_has_setup_modifier"):
        card = _resolve_card(engine, context, cond.get("card", "current_card"))
        name = str(eval_v2_value(
            engine, context, cond.get("modifier", cond.get("name", "")),
        ) or "").strip()
        modifiers = getattr(card, "setup_modifiers", set()) or set()
        return bool(name and name in modifiers)
    if op in ("has_status", "has_status_named"):
        target = resolve_v2_target(engine, context, cond.get("target", "target"))
        status_id = str(eval_v2_value(engine, context, cond.get("status", cond.get("id", cond.get("name", "")))) or "")
        return _status_stack(engine, _player_id(engine, target), status_id) > 0
    if op in ("has_tag", "card_has_flag"):
        card = _resolve_card(engine, context, cond.get("card", "current_card"))
        tag = str(eval_v2_value(engine, context, cond.get("tag", cond.get("flag", ""))) or "").strip()
        return bool(tag and tag in _card_flags(card))
    if op in ("damage_type_is", "damage_type"):
        expected = str(
            eval_v2_value(engine, context, cond.get("type_name", cond.get("value", cond.get("damage_type", "physical"))))
            or "physical"
        ).strip().lower()
        actual = _context_damage_type(context).strip().lower()
        if expected in ("any", "*", ""):
            return bool(actual)
        return actual == expected
    if op in ("target_selectable", "player_selectable"):
        target = resolve_v2_target(engine, context, cond.get("target", "target"))
        target_id = _player_id(engine, target)
        checker = getattr(engine, "_target_can_be_selected", None)
        if callable(checker):
            try:
                return bool(checker(
                    _player_id(engine, context.get("source_player", 0)),
                    target_id,
                    allow_self=cond.get("allow_self", True),
                ))
            except Exception:
                return False
        return _valid_player(engine, target_id)
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


# ---------------------------------------------------------------------------
# Step gate + step log conventions (Round 13 / batch 1)
# ---------------------------------------------------------------------------
# Ops that already own ``condition``/``cond`` as *their* operand: for these the
# key is control flow (``if`` picks ``then``/``else``, ``repeat_until`` ends the
# loop, ``not``/``and``/``or`` negate/combine).  Every other op treats a
# step-level ``condition`` as a *gate*: the step only runs when it is true.
CONDITION_OWNED_OPS = {
    "if", "if_else", "repeat_until", "repeat_until_steps",
    "and", "or", "not", "any", "all", "count",
}

# ``condition``/``cond`` gate a step; ``run_if`` is the same gate under a second
# name so the control-flow ops above can also be gated positively.
GATE_CONDITION_KEYS = ("condition", "cond", "run_if")
# ``unless``/``skip_if`` invert the gate: a *true* operand skips the step.
GATE_UNLESS_KEYS = ("unless", "skip_if")

# ``log: false``, ``silent: true`` and ``no_log``/``hide_log`` are one and the
# same switch: the step prints no default battle-log line of its own.
SILENT_KEYS = ("silent", "no_log", "hide_log")

# Condition ops that **both** execution paths can evaluate (runtime
# ``check_v2_condition`` and engine ``_eval_condition``).  A gate written with
# anything else -- an engine-only op such as ``equip_turns``, a v2-only op such
# as ``card_has_tag``, a bare value expression or a typo -- is *unreadable*: the
# step still runs (exactly like before step gates existed) and the reason is
# written to the mod-runtime error log.  A gate is never silently skipped.
SHARED_CONDITION_OPS = {
    "compare", "eq", "ne", "gt", "gte", "lt", "lte",
    "==", "!=", ">", ">=", "<", "<=",
    "and", "or", "not",
    "var_compare",
    "has_status", "has_status_named",
    "target_selectable", "player_selectable",
    "hand_full",
    "turn_number",
    "has_tag",
    "damage_type_is", "damage_type",
    "list_contains", "damage_source_relation",
    "zone_contains", "event_card_type",
}

_CONDITION_OPERAND_KEYS = ("conditions", "values", "a", "b", "condition", "value")


def condition_is_readable(condition: Any) -> bool:
    """Can *both* execution paths evaluate this gate condition?"""
    if not isinstance(condition, dict):
        return True
    op = condition.get("op") or condition.get("type")
    if not op:
        # ``{"ref": ...}`` value expressions work in both paths.
        return "ref" in condition
    if op not in SHARED_CONDITION_OPS:
        return False
    if op in ("and", "or", "not"):
        for key in _CONDITION_OPERAND_KEYS:
            nested = condition.get(key)
            if isinstance(nested, list):
                if not all(condition_is_readable(item) for item in nested):
                    return False
            elif isinstance(nested, dict) and not condition_is_readable(nested):
                return False
    return True


def _step_dicts(step: Any, params: Any = None) -> List[Dict[str, Any]]:
    """The dicts a gate/log key may live in: the step itself and its ``params``."""
    out: List[Dict[str, Any]] = []
    if isinstance(step, dict):
        out.append(step)
        nested = step.get("params")
        if isinstance(nested, dict) and nested is not step:
            out.append(nested)
    if isinstance(params, dict) and not any(params is item for item in out):
        out.append(params)
    return out


def step_gate_conditions(step: Any, op: Any = None, params: Any = None):
    """``(must_hold, must_not_hold, unreadable)`` condition lists for one step.

    This is the *shape* half of the step gate and is shared by both execution
    paths; the v2 runtime evaluates the conditions with :func:`check_v2_condition`
    and the engine evaluates them with ``GameEngine._eval_condition``.
    ``unreadable`` holds the conditions written with an op that both evaluators
    cannot read (see :data:`SHARED_CONDITION_OPS`); callers log them and let the
    step run instead of guessing.
    """
    if not isinstance(step, dict):
        return [], [], []
    resolved_op = str(op or step.get("op") or step.get("type") or "")
    condition_keys = ("run_if",) if resolved_op in CONDITION_OWNED_OPS else GATE_CONDITION_KEYS
    must_hold: List[Any] = []
    must_not_hold: List[Any] = []
    unreadable: List[Any] = []
    for source in _step_dicts(step, params):
        for key in condition_keys:
            if key in source and source.get(key) is not None:
                (must_hold if condition_is_readable(source[key]) else unreadable).append(source[key])
        for key in GATE_UNLESS_KEYS:
            if key in source and source.get(key) is not None:
                (must_not_hold if condition_is_readable(source[key]) else unreadable).append(source[key])
    return must_hold, must_not_hold, unreadable


def step_gate_allows(engine, context: Dict[str, Any], step: Any, op: Any = None,
                     params: Any = None) -> bool:
    """Step-level gate for the v2 runtime: ``condition`` holds, ``unless`` does not."""
    must_hold, must_not_hold, unreadable = step_gate_conditions(step, op, params)
    for condition in unreadable:
        _report_unreadable_gate(engine, context, condition)
    if not must_hold and not must_not_hold:
        return True
    for condition in must_hold:
        if not check_v2_condition(engine, context, condition):
            return False
    for condition in must_not_hold:
        if check_v2_condition(engine, context, condition):
            return False
    return True


def _report_unreadable_gate(engine, context: Optional[Dict[str, Any]], condition: Any) -> None:
    """Log a gate whose op neither evaluator understands (the step still runs)."""
    op = condition.get("op") or condition.get("type") if isinstance(condition, dict) else type(condition).__name__
    exc = V2RuntimeError(f"unsupported step condition op: {op!r}")
    context = context if isinstance(context, dict) else {}
    reporter = getattr(engine, "_log_mod_runtime_error", None)
    if callable(reporter):
        reporter(
            "step_condition",
            exc,
            context.get("source_player"),
            context.get("card"),
        )


def step_is_silent(step: Any, params: Any = None) -> bool:
    """``log: false`` == ``silent: true`` == "print no default line for this step"."""
    for source in _step_dicts(step, params):
        if source.get("log") is False:
            return True
        if any(source.get(key) for key in SILENT_KEYS):
            return True
    return False


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
        elif ctype in ("select", "card_catalog_picker"):
            options = _control_options(control)
            allowed = [str(opt.get("value")) for opt in options]
            value = str(raw_value)
            if allowed and value not in allowed:
                raise V2RuntimeError(f"invalid v2 ui select value: {cid}")
            values_out[cid] = value
        elif ctype in ("card_picker", "equipment_picker", "multi_card_picker", "multi_equipment_picker"):
            multi = ctype.startswith("multi_")
            zone = str(control.get("zone") or ("equipment" if "equipment" in ctype else "hand"))
            target_id = _player_id(engine, resolve_v2_target(engine, context, control.get("target", "source")))
            picker_type = "equipment_picker" if "equipment" in ctype else "card_picker"
            allowed_ids = _picker_instance_ids(engine, target_id, zone, picker_type)
            explicit_allowed = control.get("allowed_instance_ids")
            if isinstance(explicit_allowed, list):
                normalized_allowed = set()
                for value in explicit_allowed:
                    try:
                        normalized_allowed.add(int(value))
                    except Exception:
                        continue
                allowed_ids = [instance_id for instance_id in allowed_ids if instance_id in normalized_allowed]
            raw_values = raw_value if isinstance(raw_value, list) else ([] if raw_value in (None, "") else [raw_value])
            instance_ids = []
            for value in raw_values:
                try:
                    instance_id = int(value)
                except Exception:
                    raise V2RuntimeError(f"invalid v2 ui picker value: {cid}")
                if instance_id in instance_ids:
                    continue
                if instance_id not in allowed_ids:
                    raise V2RuntimeError(f"v2 ui picker target not allowed: {cid}")
                instance_ids.append(instance_id)
            min_select = max(0, _to_int(control.get("min_select", 0 if multi else 1)))
            max_select = max(min_select, _to_int(control.get("max_select", len(allowed_ids) if multi else 1)))
            if len(instance_ids) < min_select or len(instance_ids) > max_select:
                raise V2RuntimeError(f"v2 ui picker selection count invalid: {cid}")
            values_out[cid] = instance_ids if multi else (instance_ids[0] if instance_ids else None)
        elif ctype in ("player_picker", "target_picker"):
            try:
                player_id = int(raw_value)
            except Exception:
                raise V2RuntimeError(f"invalid v2 ui player value: {cid}")
            explicit_allowed = control.get("allowed_player_ids")
            normalized_allowed = None
            if isinstance(explicit_allowed, list):
                normalized_allowed = set()
                for value in explicit_allowed:
                    try:
                        normalized_allowed.add(int(value))
                    except Exception:
                        continue
            if not _valid_player(engine, player_id) or (normalized_allowed is not None and player_id not in normalized_allowed):
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
    if ctype not in {"modal", "confirm", "select", "card_catalog_picker", "slider", "number", "number_input", "card_picker", "equipment_picker", "multi_card_picker", "multi_equipment_picker", "player_picker", "target_picker", "text"}:
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
    if ctype not in {"text", "select", "card_catalog_picker", "slider", "number", "number_input", "card_picker", "equipment_picker", "multi_card_picker", "multi_equipment_picker", "player_picker", "target_picker"}:
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
    elif ctype in ("select", "card_catalog_picker"):
        out["options"] = _control_options(control)
    elif ctype in ("card_picker", "equipment_picker", "multi_card_picker", "multi_equipment_picker"):
        picker_type = "equipment_picker" if "equipment" in ctype else "card_picker"
        zone = str(control.get("zone") or ("equipment" if picker_type == "equipment_picker" else "hand"))
        target_id = _player_id(engine, resolve_v2_target(engine, context, control.get("target", "source")))
        options = _picker_options(engine, target_id, zone, picker_type)
        explicit_allowed = control.get("allowed_instance_ids")
        if isinstance(explicit_allowed, dict):
            explicit_allowed = eval_v2_value(engine, context, explicit_allowed)
        if isinstance(explicit_allowed, list):
            allowed = set()
            for value in explicit_allowed:
                try:
                    allowed.add(int(value))
                except Exception:
                    continue
            options = [option for option in options if int(option.get("value", -1)) in allowed]
        out["zone"] = zone
        out["target"] = target_id
        out["options"] = options
        out["allowed_instance_ids"] = [int(option.get("value")) for option in options]
        if ctype.startswith("multi_"):
            min_select = max(0, _to_int(control.get("min_select", 0)))
            max_select = max(min_select, _to_int(control.get("max_select", len(options))))
            out["min_select"] = min(min_select, len(options))
            out["max_select"] = min(max_select, len(options))
    elif ctype in ("player_picker", "target_picker"):
        allowed = None
        if isinstance(control.get("allowed_player_ids"), list):
            allowed = set()
            for value in control.get("allowed_player_ids"):
                try:
                    allowed.add(int(value))
                except Exception:
                    continue
        out["options"] = [
            {"value": idx, "label": engine.pn(idx)}
            for idx in range(len(getattr(engine, "players", [])))
            if allowed is None or idx in allowed
        ]
        out["allowed_player_ids"] = [int(option["value"]) for option in out["options"]]
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
            option = {
                "value": str(value),
                "label": str(label),
                "label_cn": str(item.get("label_cn") or item.get("text_cn") or label),
                "label_en": str(item.get("label_en") or item.get("text_en") or label),
            }
            if isinstance(item.get("card"), dict):
                option["card"] = copy.deepcopy(item.get("card"))
            options.append(option)
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


def _move_card(engine, card: CardInstance, owner_id: int, zone: str, already_detached: bool = False) -> bool:
    if not _valid_player(engine, owner_id):
        return False
    if already_detached and hasattr(engine, "_can_normally_acquire_card"):
        try:
            if not engine._can_normally_acquire_card(owner_id, card):
                engine.log_msg(f"{engine.pn(owner_id)}已拥有唯一牌{card.name_cn}，未获得额外实例")
                return False
        except Exception:
            return False
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
    return True


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
    if prop in ("paid_e", "paid_m"):
        attribute = "_paid_e_this_play" if prop == "paid_e" else "_paid_m_this_play"
        value = getattr(card, attribute, None)
        if value is None:
            card_def = getattr(card, "card_def", None)
            value = getattr(card_def, "cost_e" if prop == "paid_e" else "cost_m", 0)
        return max(0, int(value or 0))
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


def _card_selectable_by_action(engine, card: Any) -> bool:
    if card is None:
        return False
    fn = getattr(engine, "_card_selectable_by_action", None)
    if callable(fn):
        try:
            return bool(fn(card))
        except Exception:
            return False
    fn = getattr(engine, "_card_is_sublime", None)
    if callable(fn):
        try:
            return not bool(fn(card))
        except Exception:
            return False
    return True


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


def _apply_status(engine, player_id: int, status_id: str, amount: int, op: str,
                  log: Any = True) -> None:
    """Apply a named status for the v2 runtime ``add_status`` family.

    ``log=False`` mutes the runtime's own status line (``log: false`` /
    ``silent: true`` on the step); the state change is unaffected.
    """
    def _status_log(message: str) -> None:
        if log is not False:
            engine.log_msg(message)

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
            _status_log(f"{engine.pn(player_id)}获得状态免疫")
        elif op == "remove_status" and before > 0 and after <= 0:
            _status_log(f"{engine.pn(player_id)}失去状态免疫")
        elif op == "set_status":
            _status_log(f"{engine.pn(player_id)}{'获得' if after else '失去'}状态免疫")
        return
    if _status_application_blocked_by_immunity(engine, player_id, status_id, amount, op):
        return
    if status_key in ("nazar", "邪眼", "Nazar"):
        getter = getattr(engine, "_nazar_status_value", None)
        before = int(getter(player_id) or 0) if callable(getter) else int(getattr(ps, "custom_statuses", {}).get("nazar", 0) or 0)
        if op == "remove_status":
            value = max(0, before - max(1, amount))
        elif op == "set_status":
            value = max(0, amount)
        else:
            value = max(0, before + amount)
        setter = getattr(engine, "_set_nazar_status_value", None)
        if callable(setter):
            setter(player_id, value)
        else:
            ps.custom_statuses = getattr(ps, "custom_statuses", {})
            ps.custom_statuses["nazar"] = value
        after = int(getter(player_id) or 0) if callable(getter) else int(getattr(ps, "custom_statuses", {}).get("nazar", 0) or 0)
        delta = after - before
        label = _status_label(status_id)
        if op == "add_status" and delta:
            _status_log(f"{engine.pn(player_id)}+{abs(delta)}层{label}")
        elif op == "remove_status" and delta:
            _status_log(f"{engine.pn(player_id)}-{abs(delta)}层{label}")
        elif op == "set_status":
            _status_log(f"{engine.pn(player_id)}的{label}变为{after}层")
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
        _status_log(f"{engine.pn(player_id)}+{abs(delta)}层{label}")
    elif op == "remove_status" and delta:
        _status_log(f"{engine.pn(player_id)}-{abs(delta)}层{label}")
    elif op == "set_status":
        _status_log(f"{engine.pn(player_id)}的{label}变为{after}层")


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
    if status_key in ("nazar", "邪眼", "Nazar"):
        getter = getattr(engine, "_nazar_status_value", None)
        if callable(getter):
            return int(getter(player_id) or 0)
        return int(getattr(ps, "custom_statuses", {}).get("nazar", 0) or 0)
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
        "dizzy": "skip_turn",
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
        "nazar": "邪眼",
        "Nazar": "邪眼",
        "邪眼": "邪眼",
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
        "dizzy": "眩晕",
        "skip_turn": "眩晕",
        "attack_blocked": "禁攻",
        "禁攻": "禁攻",
        "attack_only": "仅攻击",
        "仅攻击": "仅攻击",
        "magic_blocked": "魔力封锁",
        "魔力封锁": "魔力封锁",
        "unable_counter": "无法反制",
        "无法反制": "无法反制",
        "blood_debt": "血债",
        "血债": "血债",
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
    mutation_scope = nullcontext()
    if resolved_type in {"var_set", "var_add", "var_sub", "var_mul", "var_div"}:
        raw_params = step.get("params") if isinstance(step.get("params"), dict) else step
        name = str(raw_params.get("name") or "var")
        target_selector = raw_params.get("target", "source")
        target_refs = resolve_v2_target(engine, context, target_selector)
        mutation_reader = getattr(engine, "_read_status_var_for_mutation", None)
        if callable(mutation_reader):
            mutation_scope = mutation_reader(target_refs, name)
    with mutation_scope:
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
    if not defer_values:
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
        "last_positive_hits", "positive_hits",
        "hit_count", "damage_hits",
        "status_stack", "get", "deck_top_ids", "zone_top_ids",
        "last_crit_hits", "crit_hits", "status_count", "visible_status_count",
        "counter_cards_in_hand", "counters_in_hand",
        "play_was_countered", "was_countered",
        "random_choice", "choice_value", "choice_field",
        "cards_played_this_turn", "played_cards_this_turn", "cards_played",
        "damage_type", "current_damage_type", "card_cost", "actual_card_cost",
        "current_turn_player", "turn_player", "active_player", "card_var", "card_custom_var",
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


def _format_message(message: str, context: Dict[str, Any], engine=None, card=None,
                    amount: Any = None, target: Any = None) -> str:
    # Substitute the runtime variables one placeholder at a time: a template
    # may mix ``{var_name}`` with engine fields such as ``{source}``/``{target}``
    # and ``str.format`` would refuse the whole string when a name is missing.
    fields_map = dict(context.get("vars") or {})
    fields_map.setdefault("last_damage", context.get("last_damage", 0))
    try:
        text = re.sub(
            r"\{([A-Za-z_][A-Za-z0-9_]*)\}",
            lambda match: str(fields_map[match.group(1)]) if match.group(1) in fields_map else match.group(0),
            message,
        )
    except Exception:
        text = message
    formatter = getattr(engine, "_format_step_log", None)
    if not callable(formatter) or "{" not in text:
        return text
    # Battle-log templates may address the acting player, the current card and
    # the effect amount, the same placeholders the engine's own steps use.
    fields = {}
    if card is not None:
        fields["name"] = getattr(card, "name_cn", "")
        fields["card"] = getattr(card, "name_cn", "")
    source_id = context.get("source_player")
    if isinstance(source_id, int) and callable(getattr(engine, "pn", None)):
        fields.setdefault("source", engine.pn(source_id))
    target_id = context.get("target_player", context.get("target_id"))
    if target is not None and engine is not None:
        try:
            resolved = resolve_v2_target(engine, context, target)
            resolved_list = _as_player_list(engine, resolved)
            if resolved_list:
                target_id = resolved_list[0]
        except Exception:
            pass
    if isinstance(target_id, int) and callable(getattr(engine, "pn", None)):
        fields.setdefault("target", engine.pn(target_id))
    if amount is None:
        amount = context.get("last_damage", 0)
    fields["amount"] = amount
    fields.setdefault("count", fields["amount"])
    return formatter(text, **fields)


def _render_step_log(engine, step: Any, params: Any, fields: Dict[str, Any]):
    """Render a step-provided ``log`` value for a runtime-handled op.

    ``None``/``True`` keeps the caller's default battle-log line, ``False`` mutes
    it and a string is used as a template (``{target}``/``{source}``/``{amount}``/
    ``{count}``/``{name}``) so card data owns the exact wording.

    ``silent: true`` / ``no_log`` / ``hide_log`` are the same switch as
    ``log: false``: the step prints nothing of its own.
    """
    if step_is_silent(step, params):
        return False
    raw = step.get("log") if isinstance(step, dict) else None
    if raw is None and isinstance(params, dict) and params is not step:
        raw = params.get("log")
    if raw is None or raw is True:
        return None
    if raw is False:
        return False
    text = str(raw)
    if not text:
        return None
    formatter = getattr(engine, "_format_step_log", None)
    if callable(formatter):
        return formatter(text, **fields)
    try:
        return text.format(**fields)
    except Exception:
        return text


def _context_damage_type(context: Any) -> str:
    """Damage type carried by the event/damage context that is resolving now."""
    if not isinstance(context, dict):
        return ""
    for key in ("damage_type", "damage_kind"):
        if context.get(key):
            return str(context[key])
    for nested_key in ("current_action", "vars", "action"):
        nested = context.get(nested_key)
        if not isinstance(nested, dict):
            continue
        for key in ("damage_type", "damage_kind"):
            if nested.get(key):
                return str(nested[key])
    return ""
