# -*- coding: utf-8 -*-
"""统计官方包里"效果行编辑器完全能表达"的卡占比。

判断标准（与 src/effect-editor.js 的实际能力一致）：

* 每个步骤的 op 都要有句型模板（`src/gtn-text/templates.js` 的键）；
* 条件表达式要落在编辑器支持的三种形态里：
  ``compare``（左右两侧都是"可编辑的值表达式"）、``not``、``and``/``or`` 且两侧都支持；
  值表达式 = 字面量 / 取值形态（player_stat、equipment_prop…）/ 算术表达式
  （add/sub/mul/div/min/max/floor/ceil，可递归嵌套）；
* 管道型 op（变量、战报文案、每回合一次）不计入失败——它们不写进描述，编辑器用折叠行承载。

    python tools/editor_coverage_report.py
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import pathlib
import re
import sys
import zipfile
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mod_atom_report  # noqa: E402

TEMPLATES_JS = ROOT.parent / "模组编辑器" / "src" / "gtn-text" / "templates.js"
DEFAULT_BASELINE = ROOT.parent / "模组编辑器" / "src" / "generated" / "editor-coverage.json"

# 与 effect-editor.js 的 LEFT_FORMS 保持一致（Round 17 起两边都能改这些左值的字段）
LEFT_FORMS = {
    "last_damage", "damage_amount", "status_stack", "hand_count", "deck_count", "player_stat",
    "discard_count",
    "player_property", "zone_count", "counter_cards_in_hand", "selected_cards_count",
    "selected_card_index", "last_positive_hits", "hand_full", "current_turn_player",
    "var", "player_var", "card_var", "card_prop",
    "choice_value", "get", "target_player", "source_player", "damage_source",
}

# 右值可以写成变量（effect-editor 的"右值来源=变量"模式能改变量名与归属）
VAR_RIGHT_OPS = {"var", "player_var", "temp_var", "global_var"}
# 右值可以写成"某个玩家的引用"（effect-editor 的"右值来源=玩家"下拉）
PLAYER_RIGHT_OPS = {
    "source_player", "target_player", "current_turn_player", "event_source",
    "damage_source", "attacker", "owner",
}

# effect-editor.js 的 SYMBOL_OPERATORS：把运算符写在 op 上的旧写法
SYMBOL_OPERATORS = {
    ">=", "<=", ">", "<", "==", "=", "!=", "gt", "gte", "lt", "lte", "eq", "ne",
}

# 条件形态：这些 op 的字段都能在效果行里直接改
SIMPLE_CONDITION_OPS = {
    "card_has_tag", "has_tag", "card_has_modifier", "has_status_named",
    "damage_type_is", "target_selectable", "play_was_countered",
    "hand_full", "zone_exists", "card_exists",
}

# effect-editor.js 的 ARITH_FORMS：算术表达式（Round 18 起递归渲染操作数）
ARITHMETIC_OPS = {"add", "sub", "mul", "div", "min", "max", "floor", "ceil"}
# 左右两侧共用的值编辑器额外支持的取值形态
EXTRA_VALUE_FORMS = {"equipment_prop", "equipment_property"}


def _condition_parts(node):
    """and/or 的分支列表：values / conditions / left+right 三种写法都认。"""

    if isinstance(node.get("values"), list):
        return node["values"]
    if isinstance(node.get("conditions"), list):
        return node["conditions"]
    left = node.get("value") if node.get("value") is not None else node.get("left")
    right = node.get("right")
    if isinstance(left, dict) and isinstance(right, dict):
        return [left, right]
    return []


def supported_templates() -> set:
    text = TEMPLATES_JS.read_text(encoding="utf-8")
    start = text.find("return {")
    end = text.find("\n  };", start)
    return set(re.findall(r"^    ([a-z0-9_]+):\s*\{", text[start:end], re.MULTILINE))


def value_supported(node) -> bool:
    """编辑器能不能行内编辑这个值表达式（字面量 / 取值形态 / 算术递归）。"""

    if not isinstance(node, dict):
        return True
    op = str(node.get("op") or node.get("ref") or "")
    if op in ARITHMETIC_OPS:
        if isinstance(node.get("values"), list):
            parts = node["values"]
        elif "value" in node:
            parts = [node.get("value")]
        else:
            parts = [node.get("a"), node.get("b")]
        return bool(parts) and all(value_supported(part) for part in parts)
    if op in LEFT_FORMS or op in VAR_RIGHT_OPS or op in PLAYER_RIGHT_OPS or op in EXTRA_VALUE_FORMS:
        return True
    return False


def condition_supported(node) -> bool:
    if not isinstance(node, dict):
        return True
    op = str(node.get("op") or node.get("ref") or "")
    if op == "compare" or op in SYMBOL_OPERATORS:
        return value_supported(node.get("a")) and value_supported(node.get("b"))
    if op == "not":
        inner = node.get("value") or node.get("cond") or node.get("condition")
        if inner is None and isinstance(node.get("conditions"), list) and node["conditions"]:
            inner = node["conditions"][0]
        return condition_supported(inner) if isinstance(inner, dict) else False
    if op in ("and", "or"):
        parts = _condition_parts(node)
        return len(parts) >= 2 and all(condition_supported(part) for part in parts)
    if op in SIMPLE_CONDITION_OPS:
        return True
    return False


def card_blockers(card, templates, stats) -> list:
    """只遍历真正的步骤（复用 mod_atom_report 的步骤树遍历），
    条件里的表达式节点不算步骤，单独按条件支持度判断。"""

    blockers = []
    lists = []
    mod_atom_report.root_step_lists(card, lists)

    def visit(step, op):
        if op and op not in templates:
            stats["unsupported_ops"][op] += 1
            blockers.append(op)
        if op == "if" and not condition_supported(step.get("condition") or step.get("cond")):
            stats["unsupported_conditions"] += 1
            blockers.append("if:condition")

    for steps in lists:
        mod_atom_report.walk_steps(steps, visit)
    return blockers


def diff_baseline(baseline: dict, current: dict) -> list:
    """对比上次记录，输出给重构当验收指标看的差异。"""

    lines = []
    prev_full = baseline.get("fullyExpressible", 0)
    prev_total = baseline.get("cardsWithLogic", 0)
    now_full = current["fullyExpressible"]
    now_total = current["cardsWithLogic"]
    if prev_total:
        lines.append(
            f"完全可表达：{now_full}/{now_total}"
            f"（{now_full / max(1, now_total) * 100:.1f}%）"
            f"，上次 {prev_full}/{prev_total}（{prev_full / max(1, prev_total) * 100:.1f}%）"
            f"，变化 {now_full - prev_full:+d} 张"
        )

    prev_ops = baseline.get("blockerOps", {})
    now_ops = current["blockerOps"]
    appeared = sorted(set(now_ops) - set(prev_ops))
    disappeared = sorted(set(prev_ops) - set(now_ops))
    if appeared:
        lines.append("新出现的障碍 op：" + "、".join(f"{op}×{now_ops[op]}" for op in appeared[:10]))
    if disappeared:
        lines.append("已消除的障碍 op：" + "、".join(f"{op}×{prev_ops[op]}" for op in disappeared[:10]))

    prev_cards = baseline.get("blockedCards", {})
    now_cards = current["blockedCards"]
    newly_free = sorted(set(prev_cards) - set(now_cards))
    newly_blocked = sorted(set(now_cards) - set(prev_cards))
    if newly_free:
        lines.append(f"新变得可编辑的卡：{len(newly_free)} 张（如 {', '.join(newly_free[:5])}）")
    if newly_blocked:
        lines.append(f"新出现障碍的卡：{len(newly_blocked)} 张（如 {', '.join(newly_blocked[:5])}）")
    if not lines:
        lines.append("与上次记录一致")
    return lines


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="效果行编辑器的覆盖率统计。")
    parser.add_argument("--mods-dir", default=str(ROOT / "mods"))
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE), help="基线文件路径")
    parser.add_argument("--no-save", action="store_true", help="不更新基线，只对比")
    args = parser.parse_args(argv)

    templates = supported_templates()
    stats = {"unsupported_ops": collections.Counter(), "unsupported_conditions": 0}
    total_cards = 0
    fully = 0
    partial = 0
    blocked_cards = []
    blocked_map = {}

    for path in sorted(glob.glob(str(pathlib.Path(args.mods_dir) / "*.gtnmod"))):
        name = pathlib.Path(path).name
        try:
            with zipfile.ZipFile(path) as archive:
                payload = json.loads(archive.read("mod.json"))
        except Exception:
            continue
        for card in (payload.get("registries") or {}).get("cards") or []:
            events = card.get("events") or {}
            if not events:
                continue
            total_cards += 1
            blockers = card_blockers(card, templates, stats)
            if not blockers:
                fully += 1
            else:
                partial += 1
                blocked_map[str(card.get("id") or "")] = sorted(set(blockers))
                if len(blocked_cards) < 12:
                    blocked_cards.append((card.get("id"), sorted(set(blockers))))

    current = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "templates": len(templates),
        "cardsWithLogic": total_cards,
        "fullyExpressible": fully,
        "blocked": partial,
        "unsupportedConditions": stats["unsupported_conditions"],
        "blockerOps": dict(stats["unsupported_ops"].most_common()),
        "blockedCards": blocked_map,
    }

    print(f"句型模板：{len(templates)} 个 op")
    print(f"含逻辑的卡：{total_cards}")
    print(f"  完全可表达：{fully}（{fully / max(1, total_cards) * 100:.1f}%）")
    print(f"  有障碍：    {partial}")
    print()
    print("障碍最多的 op：")
    for op, count in stats["unsupported_ops"].most_common(12):
        print(f"  {count:4d}  {op}")
    print(f"\n无法可视编辑的条件：{stats['unsupported_conditions']} 处")
    print("\n示例障碍卡：")
    for card_id, ops in blocked_cards[:6]:
        print(f"  {card_id}: {', '.join(ops[:4])}")

    # Blockly 退场门槛：达到切换门槛后把效果行设为默认视图，达到移除门槛后再摘画布
    share = fully / max(1, total_cards) * 100
    print()
    print("Blockly 退场门槛：")
    print(f"  切换默认视图（≥85%）：{'已达标' if share >= 85 else f'未达标（还差 {85 - share:.1f} 个百分点）'}")
    print(f"  移除画布（≥90%）：    {'已达标' if share >= 90 else f'未达标（还差 {90 - share:.1f} 个百分点）'}")

    baseline_path = pathlib.Path(args.baseline)
    if baseline_path.is_file():
        try:
            previous = json.loads(baseline_path.read_text(encoding="utf-8"))
        except Exception:
            previous = None
        if previous:
            print("\n与基线对比：")
            for line in diff_baseline(previous, current):
                print("  " + line)
    else:
        print("\n（首次运行，已建立基线）")

    if not args.no_save:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"baseline: {baseline_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
