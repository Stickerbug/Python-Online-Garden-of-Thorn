from __future__ import annotations

import copy
import math
import random
import re
import uuid
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
from mod_spec_v2 import REMOVED_ATOMIC_OPS, RENAMED_ATOMIC_OPS


STEP_BUDGET = 1000
FOR_EACH_LIMIT = 200


ADVANCED_ATOMIC_OPS = {
    # Round 30 / 批次 Y：本名单只保留**仍在契约里**的 op（见
    # docs/引擎原子与数据步骤清单.md §8.4 的不变量）。26 条陈旧项（Round 20-29
    # 注销的 ``var_*`` / ``move_to_*`` / ``choose_from_*`` / ``destroy_*_equip`` /
    # ``player_prop_*`` / ``card_var_*`` / ``record_*`` / ``reset_counter`` /
    # ``*_durability``，加上本批注销的 ``damage_multi``）从名单里移出：它们本来
    # 就在 ``run_v2_step`` 的"已移除/已改名"检查**之后**才会被读到，移出后行为
    # 不变，只是不再虚报"白名单里有实现"。
    # Round 32 / 批次 AA：``if``/``repeat_until``/``for_each_list``/
    # ``for_each_selected_card`` 并进 ``if_else`` / ``repeat`` / ``for_each``；
    # 生命族并进 ``health_op``、资源族并进 ``resource_op``、费用族并进
    # ``modify_next_cost``、抽牌族并进 ``draw``、列表族并进 ``list_modify``。
    # Round 37 / 批次 AD-2：``after_all`` 并进 ``on_event(trigger:"after_all")``，
    # 规范名 ``on_event`` 有自己的 ``_atomic_*`` 实现，登记在这里只是保持
    # "伞原子在白名单里"的既有口径。
    "on_event", "random", "break", "continue", "if_else", "repeat",
    "for_each",
    "damage", "direct_damage", "lifesteal_damage", "triangle_damage",
    "health_op", "resource_op", "draw", "modify_next_cost",
    # Round 33 / 批次 AC + Round 35 收尾：装备 / 状态 / 标签 / 自动打出四族的
    # 伞原子（``equipment_op`` / ``status_op`` / ``tag_op`` / ``auto_play``）。
    # ``queue_auto_play`` 仍是可用名（测试断言 ocean:magic_pearl 的步骤形状），
    # 其余旧名进 REMOVED_ATOMIC_OPS，写在下面只会拿到"已移除 + 替代写法"。
    "equipment_op", "status_op", "tag_op", "auto_play",
    # Round 24：护甲/闪避族、状态三兄弟、清状态族、每回合修正族、资源族、
    # 全局倍率族、卡内标签族、装备减抽族各自合并成一条（旧名进
    # mod_spec_v2.REMOVED_ATOMIC_OPS，写出来是显式报错）。
    "player_stat_change",
    # Round 31 / 批次 Z：``clear_status`` / ``set_status_named`` / ``resource_spend``
    # 与玩家的 ``set_untargetable`` / ``untargetable_layers`` / ``set_invincible``
    # 已删除，换成本表里的规范名（``status_add_named`` 的 ``mode``、
    # ``player_status_layers``；``spend_resource`` 本身在 Round 32 又并进
    # ``resource_op(mode:"spend")``）。
    "status_add_named", "status_remove_named",
    "turn_mod_add", "global_mult",
    # Round 33 / 批次 AB：``reveal_enemy_hand`` / ``reveal_hand`` / ``reveal_hand_cards``
    # 并进 ``reveal``；``steal_enemy_card`` / ``steal_card`` / ``give_card_to_hand`` /
    # ``give_card_to_deck`` / ``shuffle_discard_into_deck`` / ``shuffle_hand`` /
    # ``random_zone_card_to_hand`` / ``move_cards_to_deck`` / ``exile_this`` /
    # ``swap_hands`` / ``copy_card_instance`` / ``create_copies_to_deck_top`` /
    # ``snapshot_card_props`` / ``restore_card_props`` / ``restore_*_stats``
    # 并进 ``move_card`` / ``copy_card`` / ``shuffle`` / ``snapshot`` / ``restore``。
    "reveal", "shuffle", "snapshot", "restore",
    "copy_card",
    "remove_specific_card",
    "move_card",
    "destroy_equipment",
    "equip_protection", "remove_equip_protection",
    "place_as_equip", "add_equipment_to_zone",
    # Round 38 / 批次 AD-3：``block_own_actions``（别名 ``block_action``）/
    # ``block_card_type`` / ``force_card_type`` / ``nullify_current_card``
    # 四条行为过滤原子并进 ``action_filter``（``mode`` 选 block_own /
    # block_type / force_type / negate）；旧名进 REMOVED_ATOMIC_OPS。
    "action_filter",
    # Round 38 / 批次 AD-3：``skip_turn`` / ``extra_turn`` / ``force_end_turn``
    # 三条回合控制原子并进 ``turn_control(mode:"skip"|"extra"|"end")``；伞原子
    # 有自己的 ``_atomic_*`` 实现，这里登记只是保持"伞原子在契约白名单里"的
    # 既有口径。旧名进 REMOVED_ATOMIC_OPS，写出来是显式报错。
    "turn_control",
    "player_status_layers",
    "mark_self_damage_source", "fission", "fusion",
    "multiply_next_damage",
    "add_tag", "add_tag_to_zone",
    "transform_card", "card_counter", "create_counter",
    # Round 37 / 批次 AD-2：``broadcast_event`` 并进 ``emit_event``。
    "emit_event", "modify_damage",
    "list_modify", "delayed_effect", "countdown_var",
    # Round 20: ``random_move_card_to_hand`` / ``move_random_card_to_hand``
    # (Round 1 draft names, never used by shipped data) were folded into
    # ``random_zone_card_to_hand``; see ``REMOVED_ATOMIC_OPS``.
    "defer_game_over",
    "seal_equipment", "clear_statuses", "settle_status",
    "queue_auto_play", "auto_play_zone_top", "ricochet_attack",
    "absorb_attack_damage", "add_charge_to_hand",
    "card_var_change",
    "set_card_prop_random",
    "transform_cards",
    "deck_catalog_pick", "deck_catalog_pick_resume",
    "player_prop_change", "card_prop_change",
    "card_damage_multiply", "equipment_prop_set",
    "restore_turn_start_stats", "restore_match_start_stats",
    "counter_pending_attack_damage",
    "equipment_prop_add", "discard_choice_then_draw",
    "activate_corruption",
    "response_declare", "on_any_turn_start",
    "on_enemy_turn_start", "on_owner_turn_start", "on_owner_turn_end", "on_hand_owner_turn_start", "on_hand_owner_turn_end",
    "on_discard_owner_turn_start", "on_equipment_trigger", "on_equipment_destroy",
    "on_damage_taken",
    "cogwheel_mark",
    "goggles_enable",
    # Round 40 / 批次 AE-2：``assembler_effect`` 已下沉成卡数据里的通用步骤
    # （旧名进 REMOVED_ATOMIC_OPS）。
    # Round 36 / 批次 AD-1：请求族四合一 —— 旧 ``request_target`` /
    # ``request_card`` / ``request_confirm`` / ``choose_from_zone`` /
    # ``declare_forced_target`` / ``copy_choice_with_discount`` /
    # ``request_reorder_deck`` 并进 ``request``（``type`` 选类别）；
    # 旧名进 REMOVED_ATOMIC_OPS，写出来是显式报错。
    "request",
    # Round 26：apply_jungle_status / magic_grapes_damage /
    # consume_magic_for_status / yin_yang_effect / flower_burst /
    # draw_to_hand_limit 的公式已搬进卡数据，实现删除（见 REMOVED_ATOMIC_OPS）。
    "apply_turn_regen",
    "plank_immunity",
    "electric_web_arm",
    "magic_salt_reflect", "third_eye_precision_or_hidden",
    "grant_temp_swift_highest_e",
    # Round 37 / 批次 AD-2：``timed_effect`` 与两条 ``delayed_*`` 并进
    # ``delayed_effect(mode:"timed"|"blind"|"reveal_hand")``（登记名见上一行），
    # 旧名进 REMOVED_ATOMIC_OPS，写出来是显式报错。
    # Round 27：`discard` / `random_discard_from_hand` 拆成"取值表达式 + 通用步骤"，
    # 实现删除（见 REMOVED_ATOMIC_OPS 的替代写法）。
}

# 旧名 → 新名。只保留仍被卡数据、测试或工具引用的条目；已经没有任何引用
# 的别名（add_card_tag / set_card_prop / equip_card / show_initial_deck 等
# 12 条）在 Round 4 移除，见 .codex-tmp/round4/rd4_deadcode.md。
#
# Round 22（别名收敛：一个概念一个名字）：卡数据迁完后删掉 11 条——
# apply_poison / apply_toxic / gain_armor / auto_play_queue_add /
# queue_auto_play_card / kitty_auto_play / bounce_attack /
# ocean_for_each_selectable_target / for_each_selectable_target /
# garden_show_initial_deck / set_card_var。它们改用 mod_spec_v2.RENAMED_ATOMIC_OPS
# 给"已改名 + 规范名"的显式报错（不再静默替换）；剩下 1 条 apply_burn 是
# tests/ 锁着的（test_mod_atom_report.py 的步骤夹具写着它），保留不动。
# 见 .codex-tmp/round22/rd22.md。
#
# Round 24：最后一条 ``apply_burn`` 也删掉了——它的规范名 ``burn`` 本身在 C 类
# 合并里并进 ``status_add_named(status="burn")``，两个名字一起进
# mod_spec_v2.REMOVED_ATOMIC_OPS（带完整替代写法）。表保留为空 dict，运行时的
# 查表代码不变。
ATOMIC_OP_ALIASES = {}


class V2RuntimeError(Exception):
    pass


class V2UIPause(Exception):
    def __init__(self, payload: Dict[str, Any]):
        super().__init__("v2 ui request pending")
        self.payload = payload


# ---------------------------------------------------------------------------
# 区域 / 位置词表与选择器参数（Round 14 / 批次 2：选择器与区域统一）
#
# 卡数据里的区域参数只认这一套名字：``hand`` / ``deck`` / ``discard`` /
# ``exile`` / ``equipment``。移动、给牌这类**目的区**不能写 ``equipment``
# （那是 ``place_as_equip`` 的活）；打标签、改属性、变换、随机取牌这类**读区**
# 可以用 ``equipment``（= 装备上的卡实例）。
#
# 位置统一为 ``top`` / ``bottom`` / ``random`` / ``random_top``：
# ``random_top`` 对多张牌是"先把这批牌洗匀再整体放顶"，对单张牌等同 ``top``。
# 历史别名（``draw`` / ``draw_pile`` / ``exile_pile`` / ``shuffled_top`` 等）
# 继续可写，见下两张别名表。
#
# 未知区域/位置一律抛 :class:`V2ZoneError`（Round 14 起不再静默回落成
# "什么也不做"或"进弃牌堆"）：引擎路径由 `_run_effect_list` 记成 mod 运行时
# 错误，运行时路径由 :func:`_log_runtime_error` 记成同一条错误。
# ---------------------------------------------------------------------------
ZONE_NAMES = ("hand", "deck", "discard", "exile", "equipment")
PILE_ZONE_NAMES = ("hand", "deck", "discard", "exile")
ZONE_POSITIONS = ("top", "bottom", "random", "random_top")
ZONE_POSITION_ALIASES = {
    "shuffled_top": "random_top",
    "shuffle_top": "random_top",
    "randomtop": "random_top",
}
ZONE_NAME_ALIASES = {
    "draw": "deck",
    "draw_pile": "deck",
    "drawpile": "deck",
    "deck_pile": "deck",
    "discard_pile": "discard",
    "exile_pile": "exile",
    "equip": "equipment",
    "equipment_zone": "equipment",
}

# 玩家选择器参数：``target`` / ``targets`` / ``owner`` 走同一条解析，
# ``first`` / ``exclude`` / ``relation`` / ``allow_self`` / ``filter`` 是通用修饰键。
# 逐 op 的支持表见 docs/引擎原子与数据步骤清单.md §15。
SELECTOR_TARGET_KEYS = ("target", "targets", "owner")
SELECTOR_FIRST_KEYS = ("first", "first_only", "single")
SELECTOR_FILTER_KEYS = ("filter", "where")


class V2ZoneError(V2RuntimeError):
    """未知区域名 / 位置名（Round 14 / 批次 2 起显式报错）。"""


def zone_vocabulary_text(allow_equipment: bool = True) -> str:
    return "/".join(ZONE_NAMES if allow_equipment else PILE_ZONE_NAMES)


def normalize_zone_name(value, *, allow_equipment: bool = True, op: str = "",
                        param: str = "zone") -> str:
    """Normalise one zone name, raising :class:`V2ZoneError` when unknown."""
    text = str(value).strip().lower() if value not in (None, "") else ""
    canonical = ZONE_NAME_ALIASES.get(text, text)
    allowed = ZONE_NAMES if allow_equipment else PILE_ZONE_NAMES
    if canonical not in allowed:
        raise V2ZoneError(
            f"{op or 'step'} 的 {param} 不支持区域 {value!r}；只支持 {zone_vocabulary_text(allow_equipment)}"
        )
    return canonical


def normalize_zone_names(value, *, allow_equipment: bool = True, op: str = "",
                         param: str = "zones") -> List[str]:
    """Normalise a single zone or a zone list, de-duplicated and order-stable."""
    raw_items = value if isinstance(value, (list, tuple, set)) else [value]
    names: List[str] = []
    for item in raw_items:
        name = normalize_zone_name(item, allow_equipment=allow_equipment, op=op, param=param)
        if name not in names:
            names.append(name)
    return names


def normalize_zone_position(value, *, op: str = "", param: str = "position",
                            default: str = "top") -> str:
    """Normalise a deck position, raising :class:`V2ZoneError` when unknown."""
    text = str(default) if value in (None, "") else str(value).strip().lower()
    canonical = ZONE_POSITION_ALIASES.get(text, text)
    if canonical not in ZONE_POSITIONS:
        raise V2ZoneError(
            f"{op or 'step'} 的 {param} 不支持位置 {value!r}；只支持 {'/'.join(ZONE_POSITIONS)}"
        )
    return canonical


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
    except (LoopBreak, LoopContinue) as exc:
        # ``break``/``continue`` outside a loop: report it exactly like the
        # engine path does instead of aborting the whole event.
        reporter = getattr(engine, "_log_mod_runtime_error", None)
        if callable(reporter):
            reporter("v2_event", RuntimeError(f"{type(exc).__name__} outside loop"),
                     ctx.get("source_player"), ctx.get("card"))
        return {"success": True}
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
        gate_allows = step_gate_allows(
            engine, context, step, ATOMIC_OP_ALIASES.get(str(op), str(op)), params,
        )
    except ActionWorkBudgetExceeded:
        raise
    except Exception as exc:
        _report_unreadable_gate(engine, context, {"op": f"gate-error:{exc}"})
        gate_allows = True
    if not gate_allows:
        return {"success": True, "skipped": True, "reason": "step_condition"}

    # Round 36 / 批次 AD-1：请求族四合一 —— ``request(type:"target")`` 是旧的
    # 运行时原生分支（选目标窗口的结果写进 ``context['target_player']``）；
    # 其余类别（card / confirm / zone / forced_target / discount_copy /
    # reorder_deck）落到下面的引擎原子分派，由 ``_atomic_request`` 承接。
    if op == "request" and str(step.get("type") or "").strip().lower() == "target":
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
            # Round 15 / batch 3: the engine atom already honoured a step-level
            # ``log`` template; the runtime branch used to drop it on the floor.
            rendered = _render_step_log(engine, step, params, {
                "target": engine.pn(target_id),
                "source": engine.pn(source),
                "amount": int(dealt or 0),
                "damage": int(dealt or 0),
                "count": int(dealt or 0),
                "hits": hits,
            })
            if rendered:
                engine.log_msg(rendered)
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
        # Round 28: 走共享的 ``step_is_silent``，``no_log`` / ``hide_log`` 与
        # ``silent`` / ``log: false`` 在两条伤害管线上是同一个开关。
        silent_damage = step_is_silent(step, params)
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
            # Round 15 / batch 3: honour a data-authored summary line, the same
            # contract the engine atom for ``direct_damage`` already had.
            rendered = _render_step_log(engine, step, params, {
                "target": engine.pn(target_id),
                "source": engine.pn(source),
                "amount": int(target_total),
                "damage": int(target_total),
                "count": int(target_total),
                "hits": hits,
            })
            if rendered:
                engine.log_msg(rendered)
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

    # Round 32 / 批次 AA：``heal`` / ``draw_cards`` / ``gain_e`` / ``gain_m``
    # 的运行时原生分支已经删除——它们各自并进引擎原子 ``health_op`` / ``draw`` /
    # ``resource_op``，两条执行路径因此共用同一份实现（默认值、钳位与战报都
    # 只在原子那一处）。旧名字写出来会先撞上下面的 RENAMED_ATOMIC_OPS 显式报错。

    # Round 30 / 批次 Y：运行时侧再没有 ``add_status`` / ``remove_status`` /
    # ``set_status`` 分支——三条旧写法（Round 15 起是"默认播报层数"的运行时
    # 路径）随零用量清理删除，状态族只剩引擎原子
    # （``status_add_named(mode=add|set)`` / ``status_remove_named`` /
    # ``clear_statuses`` / ``settle_status``），两条执行路径因此共用同一份实现
    # （别名组 / 层数上限 / 成就 / 钩子 / 战报）。
    # Round 31 / 批次 Z：``set_status_named`` 与 ``clear_status`` 也并进这条族谱。

    # Round 14 / batch 2: ``move_card`` used to be implemented here with its own
    # hand-full / unknown-zone handling, which made it drift apart from the
    # ``move_to_*`` family.  It now falls through to the engine's
    # ``_atomic_move_card`` so both execution paths share one implementation
    # (zone vocabulary, position and log rules included).

    if op == "create_card":
        card_id = str(eval_v2_value(engine, context, params.get("card_id", params.get("id", ERROR_CARD_ID))) or ERROR_CARD_ID)
        to_zone = str(params.get("to") or params.get("zone") or "hand")
        for target_id in _as_player_list(engine, resolve_v2_target(engine, context, params.get("target", "source"))):
            if _valid_player(engine, target_id):
                new_card = CardInstance(def_id=card_id if card_id in CARD_DEFS else ERROR_CARD_ID)
                _move_card(engine, new_card, target_id, to_zone, already_detached=True)
        return {"success": True}

    # Round 29：``destroy_equipment`` 现在也是引擎真原子（``mode`` 选 choice/random/all，
    # ``scope`` 选 target/field），两条路径共用同一份实现。这里不再拦，让它落到
    # 下面的 ``_try_run_engine_atomic_op``——旧写法 ``destroy_equipment(equipment=...)``
    # 走 ``mode:"choice"`` 的默认值，语义与原来的薄封装一致（点选 → 指定 → 第一件）。

    # Round 32 / 批次 AA：``if`` 并入 ``if_else``。控制流是"语言内置"，这里
    # 和循环族一样保留原生驱动：``then``/``else`` 的嵌套步骤继续由 v2 运行时
    # 逐条执行（取值表达式词表、UI 暂停/恢复与批前逐字一致），引擎效果表与
    # 引擎侧嵌套体走 ``_atomic_if_else``，两边共用 condition/then/else 契约。
    # 旧名 ``if`` 不再有分支，会落到下面的 RENAMED_ATOMIC_OPS 显式报错。
    if op == "if_else":
        branch = step.get("then", []) if check_v2_condition(engine, context, step.get("condition", step.get("cond"))) else step.get("else", [])
        return run_v2_steps(engine, context, branch or [])

    if op == "for_each":
        # Round 16 / batch 4: the runtime branch and the engine atom share the
        # same contract (source/items/targets, as/var/name, limit, condition,
        # break/continue, target rebinding).  Only the body runner differs: the
        # runtime entry point keeps executing v2 steps here, so a UI request
        # inside the body can still pause and resume.
        #
        # Round 32 / 批次 AA：两个"引擎专属"预设在这里直接转交给引擎原子——
        # ``bind:"selected_card"``（旧 ``for_each_selected_card``）与列表来源
        # （``zone_list``/``list_var`` 这类旧 ``for_each_list`` 的来源，运行时
        # 的 ``resolve_v2_target`` 不认识它们）。两个预设原本就走引擎路径，
        # 转交后执行路径与批前逐字一致。
        source_expr = None
        for _key in LOOP_SOURCE_KEYS:
            if isinstance(params, dict) and params.get(_key) is not None:
                source_expr = params.get(_key)
                break
        source_ref = ""
        if isinstance(source_expr, dict):
            source_ref = str(source_expr.get("ref") or source_expr.get("op") or source_expr.get("type") or "")
        _bind_mode = str(params.get("bind") or params.get("binding") or "var").strip().lower()
        if _bind_mode in ("selected_card", "selected_cards", "chosen_card", "card") or source_ref in (
            "zone_list", "list_var", "list_item", "card_def_tags",
        ):
            delegated = _try_run_engine_atomic_op(engine, context, op, params, step)
            if delegated is not None:
                return delegated
            raise V2RuntimeError(f"unsupported v2 op: {op}")
        body = loop_body_from_params(step)
        if not body:
            body = loop_body_from_params(params)
        items, var_name, _limit = plan_loop(engine, context, params, op="for_each")
        condition = loop_condition(params)
        bind_mode = str(params.get("bind") or params.get("binding") or "var").strip().lower()
        bind_target = bind_mode in ("target", "player", "target_player")
        restore_spec = step.get("_loop_restore") if isinstance(step, dict) else None
        vars_dict = context.setdefault("vars", {}) if isinstance(context, dict) else {}
        if isinstance(restore_spec, dict):
            had_old = bool(restore_spec.get("had"))
            old_value = restore_spec.get("value")
        else:
            had_old = var_name in vars_dict
            old_value = vars_dict.get(var_name)
        child_cell: Dict[str, Any] = {}

        def _bind_item(item, index, _vars=vars_dict, _name=var_name):
            if _name:
                _vars[_name] = item

        def _unbind_item(paused, _vars=vars_dict, _name=var_name):
            if paused or not _name:
                return
            if had_old:
                _vars[_name] = old_value
            else:
                _vars.pop(_name, None)

        def _bind_target(item, index, _vars=vars_dict, _name=var_name):
            child_cell["context"] = None
            try:
                target_id = int(item)
            except (TypeError, ValueError):
                return
            if target_id < 0 or target_id >= len(getattr(engine, "players", []) or []):
                return
            # The ``bind: "target"`` preset (the old ``for_each_target`` atom,
            # deleted in Round 31) narrowed the wide-strike list in
            # a *copy* of the effect context, so nothing leaked back to the
            # outer event.  The merged loop keeps that isolation for the
            # ``bind: "target"`` preset.
            child = dict(context)
            child["target_id"] = target_id
            child["target_player"] = target_id
            child.pop("wide_strike_targets", None)
            child.pop("target_players", None)
            child_choice = {
                "target_player_id": target_id,
                "target_player": target_id,
                "target_id": target_id,
            }
            child["choice"] = child_choice
            child["current_action"] = child_choice
            child["target_player_explicit"] = True
            child_vars = dict(child.get("vars") or {})
            child_vars["target_player"] = target_id
            child_vars.pop("wide_strike_targets", None)
            if _name:
                child_vars[_name] = target_id
            child["vars"] = child_vars
            child_cell["context"] = child

        def _run_body(item, index):
            if bind_target:
                body_context = child_cell.get("context")
                if not isinstance(body_context, dict):
                    return None
            else:
                body_context = context
            if condition is not None and not check_v2_condition(engine, body_context, condition):
                return None
            return run_v2_steps(engine, body_context, body)

        def _pause_tail(remaining, item, index):
            tail = {
                "op": "for_each",
                "items": list(remaining),
                "body": list(body),
                "_loop_restore": {"had": had_old, "value": old_value},
            }
            if var_name:
                tail["as"] = var_name
            if bind_target:
                tail["bind"] = "target"
            return tail

        return run_loop_driver(
            engine,
            items,
            run_body=_run_body,
            bind=_bind_target if bind_target else _bind_item,
            unbind=None if bind_target else _unbind_item,
            pause_tail=_pause_tail,
            op="for_each",
        )

    if op in ("break", "loop_break"):
        raise LoopBreak()

    if op in ("continue", "loop_continue"):
        raise LoopContinue()

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

    # Round 22: 别名收敛后的旧名给"已改名 + 规范名"的显式报错（不静默、
    # 也不退化成"什么也没发生"）。检查放在引擎原子分派之前，免得实现名
    # 仍带着 handler 时把旧名照跑。
    renamed = RENAMED_ATOMIC_OPS.get(str(op))
    if renamed:
        raise V2RuntimeError(
            f"atomic op {op!r} 已改名（Round 22/25/29/30/31 词汇表收敛）；"
            f"请改用 {renamed!r}"
        )

    # Round 20 / Round 25: 已移除的原子给"显式 unsupported + 替代写法"，
    # 不退化成静默跳过。
    # Round 29 / 批次 X：这条检查挪到引擎原子分派**之前**——批次 X 给
    # ``var_set`` / ``move_to_hand`` / ``player_prop_*`` / ``card_var_*`` 留了
    # 同名兼容垫片（老测试与引擎内部直呼私有方法），若仍按老顺序分派，
    # v2 运行时会把"已移除"的旧名照跑，与引擎路径的显式报错不一致。
    if str(op) in REMOVED_ATOMIC_OPS:
        replacement = REMOVED_ATOMIC_OPS[str(op)]
        hint = f"；请改用 {replacement}" if replacement else "；该 op 没有等价替代"
        raise V2RuntimeError(
            f"atomic op {op!r} 已移除（Round 20/24/25/29/30/31 原子与词汇表收敛）{hint}"
        )

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


# ---------------------------------------------------------------------------
# Round 16 / batch 4: unified loop driver
#
# ``for_each`` used to have two implementations with different parameter names
# and different nested-body semantics (the runtime branch knew ``items/as``,
# the engine atom knew ``targets`` and bound a player id).  The loop family now
# shares one contract:
#
#   source/items/targets/list/collection -> the iterated values
#   as/var/name                         -> the loop variable (default ``item``)
#   limit                               -> iteration cap (default 200, ``all``
#                                          disables the cap)
#   condition/cond                      -> re-checked before every iteration;
#                                          a false condition skips that one
#   body/steps/effects                  -> the steps run per iteration
#   bind                                -> ``var`` (default) or ``target``
#                                          (rebinds ``target`` to the current
#                                          iterated player; the old
#                                          ``for_each_target`` preset)
#
# ``break`` / ``continue`` are the shared loop signals.  The engine's
# ``ModLoopBreak`` / ``ModLoopContinue`` subclass them (see ``game_engine``), so
# the same driver serves both execution paths.
# ---------------------------------------------------------------------------

class LoopBreak(Exception):
    """``break`` executed inside a loop body."""


class LoopContinue(Exception):
    """``continue`` executed inside a loop body."""


LOOP_LIMIT_ALL = ("all", "全部", "unlimited", "no_limit", "none", "inf", "∞")
LOOP_SOURCE_KEYS = ("source", "items", "targets", "list", "collection", "values")
LOOP_BODY_KEYS = ("body", "steps", "effects")


def loop_body_from_params(params: Any) -> List[Any]:
    """Return the loop's per-iteration step list (``body``/``steps``/``effects``)."""
    if not isinstance(params, dict):
        return []
    for key in LOOP_BODY_KEYS:
        value = params.get(key)
        if isinstance(value, list):
            return value
    return []


def loop_limit_from_params(engine, context: Dict[str, Any], raw: Any, *, op: str = "for_each"):
    """``limit`` -> an int cap, or ``None`` when the loop is explicitly uncapped."""
    if raw is None:
        return FOR_EACH_LIMIT
    if isinstance(raw, str) and raw.strip().lower() in LOOP_LIMIT_ALL:
        return None
    try:
        value = _to_int(eval_v2_value(engine, context, raw))
    except Exception:
        return FOR_EACH_LIMIT
    return max(0, value)


def plan_loop(engine, context: Dict[str, Any], params: Any, *, op: str = "for_each",
              default_source: Any = None, default_var: str = "item",
              source_override: Any = None, items_override: Any = None,
              resolver=None, limit_resolver=None):
    """Resolve the unified loop contract into ``(items, var_name, limit)``."""
    if not isinstance(params, dict):
        params = {}
    source = source_override
    if source is None:
        for key in LOOP_SOURCE_KEYS:
            value = params.get(key)
            if value is not None:
                source = value
                break
    if source is None:
        source = default_source
    if items_override is not None:
        items = items_override
    elif source is None:
        items = []
    else:
        try:
            items = (resolver or resolve_v2_target)(engine, context, source)
        except Exception:
            items = []
    if isinstance(items, tuple):
        items = list(items)
    elif not isinstance(items, list):
        items = [] if items is None else [items]
    else:
        items = list(items)
    raw_var = params.get("as")
    if raw_var in (None, ""):
        raw_var = params.get("var")
    if raw_var in (None, ""):
        raw_var = params.get("name")
    if raw_var is None:
        raw_var = default_var
    var_name = str(raw_var or "")
    if limit_resolver is not None:
        limit = limit_resolver(engine, context, params.get("limit"), op)
    else:
        limit = loop_limit_from_params(engine, context, params.get("limit"), op=op)
    if limit is not None:
        items = items[:limit]
    return items, var_name, limit


def loop_condition(params: Any) -> Any:
    """The per-iteration condition, if the step carries one."""
    if not isinstance(params, dict):
        return None
    for key in ("condition", "cond"):
        value = params.get(key)
        if value is not None:
            return value
    return None


def run_loop_driver(engine, items: Iterable[Any], *, run_body, check_condition=None,
                    bind=None, unbind=None, pause_tail=None,
                    stop_on_game_over: bool = True, op: str = "for_each"):
    """Drive one loop.

    ``bind(item, index)`` / ``unbind(paused)`` own the loop-variable and target
    binding; ``run_body(item, index)`` executes the body once and may return a
    v2 result dict.  ``break``/``continue`` arrive as :class:`LoopBreak` /
    :class:`LoopContinue` (the engine's ``ModLoop*`` exceptions subclass them).

    When a body pauses for UI input the remaining iterations must survive the
    pause: ``pause_tail(remaining_items, item, index)`` builds the continuation
    step that is appended after the body's own remaining steps, so the resumed
    event finishes the current iteration and then walks the rest of the loop.
    """
    items = list(items or [])
    paused = False
    try:
        for index, item in enumerate(items, start=1):
            if stop_on_game_over and getattr(engine, "game_over", False):
                break
            if bind is not None:
                bind(item, index)
            if check_condition is not None and not check_condition(item, index):
                continue
            try:
                body_result = run_body(item, index)
            except LoopContinue:
                continue
            except LoopBreak:
                break
            if isinstance(body_result, dict) and body_result.get("needs_v2_ui"):
                if pause_tail is None:
                    raise V2RuntimeError(
                        f"{op}: UI pause inside the loop body has no resume tail"
                    )
                pause = dict(body_result.get("v2_ui_pause") or {})
                tail = pause_tail(items[index:], item, index)
                if isinstance(tail, dict):
                    pause["remaining_steps"] = list(pause.get("remaining_steps") or []) + [tail]
                paused = True
                return {"success": True, "needs_v2_ui": True, "v2_ui_pause": pause}
        return {"success": True}
    finally:
        if unbind is not None:
            unbind(paused)


def listener_body_from_params(params: Any) -> List[Any]:
    """Unified ``body``/``effects``/``steps`` lookup for the listener family."""
    return loop_body_from_params(params)


def listener_condition_from_params(params: Any) -> Any:
    """Unified ``condition``/``cond`` lookup for the listener family."""
    return loop_condition(params)


LISTENER_TRIGGER_ALIASES = {
    # delayed_effect（旧 timed_effect）
    "turn_start": "target_turn_start",
    "turn_end": "target_turn_end",
    "after_status_clear": "target_turn_start_after_status_clear",
    "after_draw": "target_turn_start_after_draw",
    "start_of_turn": "target_turn_start",
    "end_of_turn": "target_turn_end",
    # on_event（旧 register_play_listener / once_per_play）
    "card_played": "play",
    "owner_play": "play",
    "on_play": "play",
    "current_play": "this_play",
    "on_equipment_trigger": "equipment_trigger",
    # absorb_attack_damage
    "attack": "attack_hit",
    "attacked": "attack_hit",
    "on_attack": "attack_hit",
}

# The trigger vocabulary each listener op implements, after alias normalisation.
# Round 37 / 批次 AD-2：延迟族（``delayed_effect``）与监听族（``on_event``）各
# 一张词表；旧名 ``timed_effect`` / ``once_per_play`` / ``register_play_listener``
# 的条目随实现一起退役（写出来先在 ``_retired_atom_runtime_error`` 被拦下）。
LISTENER_TRIGGERS = {
    "delayed_effect": {
        "target_turn_start", "target_turn_start_after_status_clear",
        "target_turn_start_after_draw", "target_turn_end", "owner_turn_start",
        "owner_turn_end", "friendly_turn_start", "enemy_turn_start",
        "any_turn_start", "any_turn_end",
    },
    "on_event": {"play", "this_play", "after_all", "equipment_trigger"},
    "absorb_attack_damage": {"attack_hit"},
}


def normalize_listener_trigger(op: str, value: Any, *, default: str) -> str:
    """Normalise a listener ``trigger`` (aliases collapse onto the canonical name)."""
    text = str(value or "").strip().lower()
    if not text:
        return default
    return LISTENER_TRIGGER_ALIASES.get(text, text)


def listener_trigger_is_supported(op: str, trigger: str) -> bool:
    allowed = LISTENER_TRIGGERS.get(str(op))
    return allowed is None or str(trigger) in allowed


def normalize_compare_operators(condition: Any) -> Any:
    """Rewrite v2 comparison-operator aliases for the engine evaluator.

    The engine's condition language spells equality ``=`` and inequality
    ``!=``; the v2 spelling accepts ``==``/``<>``.  Loop and listener
    ``condition`` operands go through this before the engine evaluates them, so
    ``operator: "=="`` means equality on both execution paths.
    """
    if isinstance(condition, list):
        return [normalize_compare_operators(item) for item in condition]
    if not isinstance(condition, dict):
        return condition
    out = dict(condition)
    op = str(out.get("op") or out.get("type") or "")
    if op == "compare":
        operator = str(out.get("operator") or "=")
        out["operator"] = {"==": "=", "<>": "!="}.get(operator, operator)
    for key in ("conditions", "values", "condition"):
        if key in out:
            out[key] = normalize_compare_operators(out[key])
    return out


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
        cards = list(_zone(engine, player_id, zone))
        # Round 27：``order``（默认 "top"）让同一个取值算子既能取顶部，也能取
        # 底部。"bottom" 从尾部往前给（与逐张 ``.pop()`` 取出的顺序一致），
        # ``discard`` 这类"从手牌尾部弃 N 张"的效果因此可以写进卡数据。
        order = str(expr.get("order", "top") or "top").strip().lower()
        if order in ("bottom", "tail", "end", "尾部", "底部"):
            cards = list(reversed(cards[-count:])) if count else []
        else:
            cards = cards[:count]
        return [getattr(card, "instance_id", None) for card in cards if getattr(card, "instance_id", None) is not None]
    if op == "zone_random_ids":
        # Round 27：区域里随机 N 张（不重复）的 ``instance_id`` 列表。
        # 抽样过程与旧 ``random_discard_from_hand`` 原子逐字相同——对"当前区域
        # 的快照副本"反复 ``random.choice`` + 移除，所以同一个随机种子下两条
        # 路径抽出的牌完全一致。``count`` 超过区域牌数时自动按可用张数钳位。
        target = resolve_v2_target(engine, context, expr.get("target", "source"))
        player_id = _player_id(engine, target)
        zone = str(expr.get("zone") or "hand")
        count = max(0, _to_int(eval_v2_value(engine, context, expr.get("count", 1))))
        cards = list(_zone(engine, player_id, zone))
        picked = []
        for _ in range(min(count, len(cards))):
            card = random.choice(cards)
            cards.remove(card)
            picked.append(card)
        return [
            getattr(card, "instance_id", None)
            for card in picked
            if getattr(card, "instance_id", None) is not None
        ]
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
    if text in ("play_targets", "action_targets", "chosen_targets", "target_players"):
        # 反馈 #71：卡数据里的"本次打出所选的目标"集合。宽域打击会把
        # ``wide_strike_targets`` 收窄成实际命中的玩家，普通单目标出牌退回
        # ``target``（即本次选定的目标）。此前运行时把裸字符串原样返回，
        # ``_as_player_list`` 会静默丢掉它——扇子的 ``gain_e target=play_targets``
        # 因此对任何目标都不回费（status_add_named 走引擎路径才看起来正常）。
        return resolve_v2_target(engine, context, "target")
    if text in ("all_selectable", "all_targets", "every_selectable"):
        source = int(context.get("source_player", 0))
        checker = getattr(engine, "_target_can_be_selected", None)
        if callable(checker):
            try:
                return [
                    idx for idx in range(len(getattr(engine, "players", []) or []))
                    if checker(source, idx, allow_self=True)
                ]
            except TypeError:
                pass
        return list(range(len(getattr(engine, "players", []) or [])))
    if text == "owner":
        # 装备事件的"拥有者"：运行时的上下文优先（装备触发会往里写
        # ``selected_equipment_owner_id``），再退回引擎的装备拥有者解析。
        for key in ("selected_equipment_owner_id", "equipment_owner_id"):
            value = context.get(key)
            if value is None:
                continue
            try:
                owner_id = int(value)
            except (TypeError, ValueError):
                continue
            if _valid_player(engine, owner_id):
                return owner_id
        resolver = getattr(engine, "_resolve_equipment_owner_selector", None)
        if callable(resolver):
            try:
                return int(resolver(int(context.get("source_player", 0))))
            except Exception:
                pass
        return int(context.get("source_player", 0))
    if text == "enemy":
        explicit_target = _explicit_target_id(engine, context)
        if explicit_target is not None:
            return explicit_target
        return _enemy_id(engine, int(context.get("source_player", 0)))
    if text in ("all", "all_players", "everyone"):
        # Round 15 / batch 3: the engine selector vocabulary always had ``all``
        # (e.g. Pyrite); the runtime used to hand the bare string to the ops
        # below, which silently dropped it.
        return list(range(len(getattr(engine, "players", []) or [])))
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
    # Round 16 / batch 4: the loop family consumes ``condition`` as a
    # per-iteration filter (the whole loop is gated with ``run_if``/``unless``),
    # and the listener family consumes it as a fire-time check.
    "for_each", "for_each_selected_card", "for_each_list",
    "on_event", "delayed_effect", "absorb_attack_damage",
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
    # Round 14 / batch 2: unknown destination zones used to fall through to the
    # discard pile.  They are an explicit error now (this helper backs
    # ``create_card``; ``move_card`` has its own engine atom).
    try:
        zone = normalize_zone_name(zone, allow_equipment=False, op="create_card", param="to")
    except V2ZoneError as exc:
        _log_runtime_error(engine, {"source_player": owner_id}, "create_card", exc)
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
        "magic_nazar": "魔法邪眼",
        "magicNazar": "魔法邪眼",
        "魔法邪眼": "魔法邪眼",
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
    # Round 31 / 批次 Z：``var_set`` / ``var_add`` / ``var_sub`` / ``var_mul`` /
    # ``var_div`` 五个旧名早已进 REMOVED_ATOMIC_OPS（Round 29 合并到
    # ``player_var_change`` 的 mode），这里曾经的"状态变量读取范围"垫片
    # （``_read_status_var_for_mutation``）随之一并删除——它只服务那五个名字，
    # 而 ``run_v2_step`` 在到达这里之前就会对它们抛"已移除 + 替代写法"。
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
    # 键 ``type`` 有两种身份：旧写法 ``{"type": <op 名>}`` 里它是 op 名（要剔除），
    # 而伞原子 ``{"op":"request","type":"target"}`` 里它是判别参数（要保留）。
    reserved_keys = {"op", "log", "then", "else", "steps", "body", "condition", "cond"}
    if not isinstance(step.get("op"), str):
        reserved_keys.add("type")
    raw_params = step.get("params") if isinstance(step.get("params"), dict) else {
        key: value
        for key, value in step.items()
        if key not in reserved_keys
    }
    params = copy.deepcopy(raw_params) if defer_values else _materialize_atomic_value(engine, context, raw_params)
    if not isinstance(params, dict):
        params = {}
    if (
        "type" not in params
        and isinstance(step.get("op"), str)
        and isinstance(step.get("type"), str)
        and step.get("type") != step.get("op")
    ):
        # Round 36：``{"op":"request","type":"card","params":{…}}`` —— 判别参数在
        # 顶层 ``type`` 上、参数体在 ``params`` 里，这里补进引擎效果的参数。
        params["type"] = step["type"]
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
                # Only the damage/status *target* keys carry wide-strike
                # semantics; an ``owner``/``effect_target`` selector must stay a
                # single player.
                params[target_key] = _engine_target_selector(
                    engine, context, params[target_key],
                    wide_ok=target_key in ("target", "targets"),
                )
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
        "status_stack", "get", "deck_top_ids", "zone_top_ids", "zone_random_ids",
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


def _engine_target_selector(engine, context: Dict[str, Any], value: Any, *, wide_ok: bool = True):
    if isinstance(value, list):
        return [_engine_target_selector(engine, context, item, wide_ok=wide_ok) for item in value]
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
        # ``resolve_v2_target`` gives a wide-strike play its whole target list;
        # the engine conversion has to keep that list (or a batch of status /
        # damage steps silently drops every target but one in 3-4 player games).
        wide_targets = context.get("wide_strike_targets") if wide_ok else None
        if isinstance(wide_targets, list):
            if not wide_targets:
                return []
            # Keep the selector symbolic: ``GameEngine._resolve_targets`` reads
            # the same ``wide_strike_targets`` snapshot from its active effect
            # context and expands it itself.
            return value
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
