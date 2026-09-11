# -*- coding: utf-8 -*-
"""长尾报表：一次跑出"未使用 op / 单点 op / 可合并族 / 未登记 op"。

数据来源（全部只读）：

1. ``mod_spec_v2.VALID_LOGIC_OPS`` / ``_CORE_LOGIC_OPS`` 与
   ``atomic_registry.engine_atomic_ops()`` —— 契约与实现；
2. ``mods/*.gtnmod`` 的 ``mod.json`` —— 步骤级用量（复用 ``mod_atom_report`` 的遍历）
   与"任意位置"用量（含表达式/条件/UI 组件里的 op/ref）；
3. ``game_engine*.py`` 的 ``def _atomic_<op>(`` 函数体 —— 形状相似度，用于找可合并族；
4. ``mod_runtime_v2.ATOMIC_OP_ALIASES`` / ``game_engine._EFFECT_ALIASES`` —— 已登记别名组。

    python tools/op_long_tail_report.py              # 文本报告
    python tools/op_long_tail_report.py --json        # 机器可读
    python tools/op_long_tail_report.py --out x.txt   # 顺便落盘
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import atomic_registry  # noqa: E402
import mod_atom_report  # noqa: E402
import mod_spec_v2  # noqa: E402

ENGINE_FILES = ("game_engine.py", "game_engine_2v2.py", "game_engine_urf.py")
# 家族前缀：形状相近、可以按同一套参数收敛的 op
FAMILY_PREFIXES = (
    "move_to_", "move_cards_", "give_card_", "destroy_", "create_", "reveal_",
    "for_each_", "clear_", "remove_", "add_", "set_", "counter_", "on_", "un_",
)
FAMILY_SUFFIXES = ("_named", "_layers", "_into_deck", "_to_hand", "_from_hand")
STOP_TOKENS = {
    "self", "params", "op", "return", "if", "else", "for", "in", "and", "or", "not",
    "None", "True", "False", "int", "str", "list", "dict", "len", "get", "try",
    "except", "def",
}


def any_position_usage(mods_dir: pathlib.Path) -> dict:
    """递归扫 mod.json 里所有 ``op``/``type``/``ref`` 键（含表达式、条件、UI 组件）。"""

    import zipfile

    counter = collections.Counter()

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("op", "type", "ref") and isinstance(value, str):
                    counter[value] += 1
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for path in sorted(mods_dir.glob("*.gtnmod")):
        try:
            with zipfile.ZipFile(path) as archive:
                payload = json.loads(archive.read("mod.json"))
        except Exception:  # noqa: BLE001
            continue
        walk(payload)
    return dict(counter)


def atomic_bodies() -> dict:
    """``op -> {file, line, lines, tokens}``（按 ``def _atomic_<op>(`` 切函数体）。"""

    bodies = {}
    pattern = re.compile(r"^(\s*)def _atomic_([a-zA-Z0-9_]+)\(", re.MULTILINE)
    for name in ENGINE_FILES:
        path = ROOT / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for match in pattern.finditer(text):
            indent, op = match.group(1), match.group(2)
            start = text.count("\n", 0, match.start()) + 1
            end = len(lines)
            cursor = match.end()
            while True:
                newline = text.find("\n", cursor)
                if newline < 0:
                    break
                cursor = newline + 1
                line = lines[text.count("\n", 0, cursor)]
                if re.match(r"^\s*(def |class )", line) and not line.startswith(indent + "    "):
                    end = text.count("\n", 0, cursor)
                    break
            body = "\n".join(lines[start - 1:max(start, end)])
            tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", body))
            tokens -= STOP_TOKENS
            tokens.discard("_atomic_" + op)
            bodies.setdefault(op, {
                "file": name,
                "line": start,
                "lines": max(1, end - start + 1),
                "tokens": tokens,
            })
    return bodies


def similarity_pairs(bodies: dict, threshold: float, min_lines: int) -> list:
    ops = [op for op, info in bodies.items() if info["lines"] >= min_lines]
    pairs = []
    for index, left in enumerate(ops):
        for right in ops[index + 1:]:
            a, b = bodies[left]["tokens"], bodies[right]["tokens"]
            if not a or not b:
                continue
            score = len(a & b) / len(a | b)
            if score >= threshold:
                pairs.append({
                    "a": left, "b": right, "score": round(score, 3),
                    "lines": [bodies[left]["lines"], bodies[right]["lines"]],
                })
    return sorted(pairs, key=lambda item: (-item["score"], item["a"]))


def alias_groups() -> list:
    """别名表里"别名 → 正式名"的登记项（不含恒等项）。"""

    import mod_runtime_v2

    groups = []
    seen = set()
    for alias, target in sorted(getattr(mod_runtime_v2, "ATOMIC_OP_ALIASES", {}).items()):
        if alias == target or (alias, target) in seen:
            continue
        seen.add((alias, target))
        groups.append({"alias": alias, "target": target, "source": "ATOMIC_OP_ALIASES"})
    engine = (ROOT / "game_engine.py").read_text(encoding="utf-8", errors="replace")
    match = re.search(r"_EFFECT_ALIASES\s*=\s*\{(.*?)\n\}", engine, re.DOTALL)
    if match:
        for alias, target in re.findall(r"'([A-Za-z0-9_]+)'\s*:\s*'([A-Za-z0-9_]+)'", match.group(1)):
            if alias == target or (alias, target) in seen:
                continue
            seen.add((alias, target))
            groups.append({"alias": alias, "target": target, "source": "_EFFECT_ALIASES"})
    return groups


def family_groups(ops: set) -> list:
    families = collections.defaultdict(list)
    for op in sorted(ops):
        for prefix in FAMILY_PREFIXES:
            if op.startswith(prefix) and len(op) > len(prefix):
                families[prefix + "*"].append(op)
                break
        else:
            for suffix in FAMILY_SUFFIXES:
                if op.endswith(suffix) and len(op) > len(suffix):
                    families["*" + suffix].append(op)
                    break
    return [
        {"family": name, "ops": members, "size": len(members)}
        for name, members in sorted(families.items(), key=lambda kv: -len(kv[1]))
        if len(members) >= 4
    ]


def build_report(mods_dir: pathlib.Path, threshold: float) -> dict:
    collected = mod_atom_report.collect(mods_dir)
    summary = mod_atom_report.build_summary(collected)
    step_usage = collected["op_usage"]
    any_usage = any_position_usage(mods_dir)
    valid_ops = set(getattr(mod_spec_v2, "VALID_LOGIC_OPS", set()) or set())
    core_ops = set(getattr(mod_spec_v2, "_CORE_LOGIC_OPS", set()) or set())
    engine_ops = set(atomic_registry.engine_atomic_ops())
    bodies = atomic_bodies()

    used_any = set(any_usage) & valid_ops
    unused = sorted(valid_ops - used_any)
    unused_with_impl = [op for op in unused if op in engine_ops]
    unused_without_impl = [op for op in unused if op not in engine_ops]
    single_point = sorted(
        (op for op, entry in step_usage.items() if entry["cards"] == 1 and op in valid_ops),
    )
    unregistered = sorted(engine_ops - core_ops)
    unregistered_used = [op for op in unregistered if op in step_usage]
    unregistered_idle = [op for op in unregistered if op not in step_usage]

    return {
        "counts": {
            "valid_ops": len(valid_ops),
            "core_ops": len(core_ops),
            "engine_ops": len(engine_ops),
            "used_as_step": len(set(step_usage) & valid_ops),
            "used_anywhere": len(used_any),
            "unused": len(unused),
            "unused_with_impl": len(unused_with_impl),
            "unused_without_impl": len(unused_without_impl),
            "single_point": len(single_point),
            "unregistered": len(unregistered),
            "dangling": len(summary["dangling"]),
            "legacy_steps": summary["legacy_step_count"],
        },
        "unused": {
            "withImpl": unused_with_impl,
            "withoutImpl": unused_without_impl,
        },
        "singlePoint": [
            {
                "op": op,
                "cards": step_usage[op]["cards"],
                "packages": sorted(step_usage[op]["packages"]),
            }
            for op in single_point
        ],
        "merge": {
            "aliases": alias_groups(),
            "similarHandlers": similarity_pairs(bodies, threshold, 6),
            "prefixFamilies": family_groups(set(step_usage) & valid_ops),
        },
        "unregistered": {
            "stillUsed": unregistered_used,
            "idle": unregistered_idle,
            "indirect": [item["op"] for item in summary["indirect"]],
            "orphan": summary["orphan"],
        },
    }


def render(report: dict, threshold: float) -> str:
    counts = report["counts"]
    lines = []
    lines.append("== 概览 ==")
    lines.append(f"  契约 op（VALID_LOGIC_OPS）: {counts['valid_ops']}")
    lines.append(f"  策展清单（_CORE_LOGIC_OPS）: {counts['core_ops']}")
    lines.append(f"  _atomic_* 实现:            {counts['engine_ops']}")
    lines.append(f"  官方包步骤里用到:          {counts['used_as_step']}")
    lines.append(f"  官方包任意位置用到:        {counts['used_anywhere']}")
    lines.append(f"  完全没用过:                {counts['unused']}"
                 f"（有实现 {counts['unused_with_impl']}，无实现 {counts['unused_without_impl']}）")
    lines.append(f"  单点 op（只被 1 张卡用）:   {counts['single_point']}")
    lines.append(f"  未登记原子:                {counts['unregistered']}"
                 f"  |  悬空 op: {counts['dangling']}  |  旧写法步骤: {counts['legacy_steps']}")
    lines.append("")

    lines.append(f"== 未使用 op（{counts['unused']}）==")
    lines.append("  有实现（保留能力，等新卡用）:")
    chunk = report["unused"]["withImpl"]
    width = max([len(op) for op in chunk] + [0]) + 2
    for index in range(0, len(chunk), 4):
        lines.append("    " + "".join(f"{op:<{width}}" for op in chunk[index:index + 4]).rstrip())
    lines.append("  无实现（登记表死重量，优先清理）:")
    lines.append("    " + ("、".join(report["unused"]["withoutImpl"]) or "（无）"))
    lines.append("")

    lines.append(f"== 单点 op（{counts['single_point']}）==")
    for item in report["singlePoint"]:
        lines.append(f"  {item['op']:34s} {'、'.join(item['packages'])}")
    lines.append("")

    merge = report["merge"]
    lines.append("== 可合并族 ==")
    lines.append(f"  A. 别名组（别名表里已登记，数据可以统一写法）: {len(merge['aliases'])} 条")
    for item in merge["aliases"]:
        lines.append(f"     {item['alias']:34s} → {item['target']:28s} ({item['source']})")
    lines.append(f"  B. 同形处理器（token Jaccard ≥ {threshold}，行数 ≥ 6）: {len(merge['similarHandlers'])} 对")
    for item in merge["similarHandlers"]:
        lines.append(f"     {item['score']:.2f}  {item['a']} ({item['lines'][0]} 行) ↔ "
                     f"{item['b']} ({item['lines'][1]} 行)")
    lines.append(f"  C. 前缀族（步骤里用到 ≥4 个同前缀 op）: {len(merge['prefixFamilies'])} 族")
    for item in merge["prefixFamilies"]:
        lines.append(f"     {item['family']:16s} {item['size']:2d} 个: {'、'.join(item['ops'])}")
    lines.append("")

    lines.append(f"== 未登记原子（实现不在 _CORE_LOGIC_OPS，共 {counts['unregistered']}）==")
    lines.append("  仍被卡数据引用（先并入通用清单或补别名）:")
    lines.append("    " + ("、".join(report["unregistered"]["stillUsed"]) or "（无）"))
    lines.append(f"  完全没用过: {len(report['unregistered']['idle'])}"
                 f"（其中被代码间接引用 {len(report['unregistered']['indirect'])}，"
                 f"零引用 {len(report['unregistered']['orphan'])}）")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="长尾报表：未使用/单点/可合并/未登记 op（只读）。")
    parser.add_argument("--mods-dir", default=str(ROOT / "mods"))
    parser.add_argument("--threshold", type=float, default=0.8, help="同形处理器的 Jaccard 阈值")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--out", default="", help="同时写入文件")
    args = parser.parse_args(argv)

    report = build_report(pathlib.Path(args.mods_dir), args.threshold)
    text = json.dumps(report, ensure_ascii=False, indent=2) if args.json else render(report, args.threshold)
    print(text)
    if args.out:
        pathlib.Path(args.out).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
