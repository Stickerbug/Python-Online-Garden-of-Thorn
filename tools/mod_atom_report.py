# -*- coding: utf-8 -*-
"""只读报告：引擎原子能力与已发布卡数据的对照。

用途是给"卡专用原子 → 通用数据步骤"的重构当进度表和防错网。它只读文件，
不修改任何东西，可以随时重复运行。

报告内容：

1. 悬空 op      —— 卡数据里用到、但运行时已不认识的 op（运行时会报错）。
2. 未登记原子   —— 引擎实现了、但没有登记进 ``_CORE_LOGIC_OPS`` 通用词汇表的原子。
3. 仍在使用     —— 上面这些原子里，仍被卡数据引用的（长尾的实际阻塞项）。
4. 未被卡数据引用 —— 再按"有没有被其他代码/状态映射间接引用"分成两组，
   只有哪一组都没有的才是真正的删除候选。
5. 旧写法       —— 仍使用 ``{"type": ..., "params": {...}}`` 而不是 ``{"op": ...}`` 的步骤。

判定规则直接取自运行时与校验器：

* 步骤的 op 名是 ``step.get("op") or step.get("type")``；
* 嵌套步骤只出现在 ``steps`` / ``body`` / ``then`` / ``else`` /
  ``on_hit`` / ``on_hit_once`` / ``on_crit`` / ``on_cancel`` 这些容器里。

条件、表达式、UI 组件都不是步骤，不会被统计——这一点是它与
``.codex-tmp`` 里那份即席脚本的关键区别。

用法::

    python tools/mod_atom_report.py               # 完整报告
    python tools/mod_atom_report.py --check       # 发现悬空 op（会导致运行时报错）时非零退出
    python tools/mod_atom_report.py --check --strict   # 连旧写法残留一起卡
    python tools/mod_atom_report.py --json        # 机器可读
    python tools/mod_atom_report.py --only "Arctic*"
"""

from __future__ import annotations

import argparse
import collections
import fnmatch
import json
import os
import pathlib
import re
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import atomic_registry  # noqa: E402
import mod_spec_v2  # noqa: E402

# 运行时执行 / 校验器检查的嵌套步骤容器。
STEP_LIST_KEYS = (
    "steps",
    "body",
    "then",
    "else",
    "on_hit",
    "on_hit_once",
    "on_crit",
    "on_cancel",
)


def step_op(step) -> str:
    """返回步骤的 op 名；``""`` 表示这个对象没有可执行的 op。"""

    if not isinstance(step, dict):
        return ""
    op = step.get("op") or step.get("type")
    return str(op) if isinstance(op, str) else ""


def step_params(step):
    """步骤参数：``{"type": x, "params": {...}}`` 取内层，其余取步骤本身。"""

    params = step.get("params") if isinstance(step, dict) else None
    return params if isinstance(params, dict) else step


def walk_steps(steps, visit) -> None:
    """深度优先遍历步骤树，对每个步骤调用 ``visit(step, op)``。"""

    if not isinstance(steps, list):
        return
    for step in steps:
        if not isinstance(step, dict):
            continue
        op = step_op(step)
        visit(step, op)
        containers = [step]
        params = step_params(step)
        if params is not step:
            containers.append(params)
        for container in containers:
            for key in STEP_LIST_KEYS:
                child = container.get(key)
                if isinstance(child, list):
                    walk_steps(child, visit)
                elif isinstance(child, dict):
                    walk_steps([child], visit)


def root_step_lists(node, out) -> None:
    """收集资源定义里的顶层 ``steps`` 数组（嵌套的由 walk_steps 处理）。"""

    if isinstance(node, dict):
        for key, value in node.items():
            if key == "steps" and isinstance(value, list):
                out.append(value)
            else:
                root_step_lists(value, out)
    elif isinstance(node, list):
        for value in node:
            root_step_lists(value, out)


def iter_registry_resources(payload):
    """产出 (registry, resource) 二元组，覆盖所有会带 steps 的注册表。"""

    registries = payload.get("registries")
    if isinstance(registries, dict):
        for registry, items in registries.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        yield registry, item
    hooks = payload.get("event_hooks")
    if isinstance(hooks, list):
        for item in hooks:
            if isinstance(item, dict):
                yield "event_hooks", item


def scan_package(path: pathlib.Path, report, *, package: str = "") -> None:
    """把一个 ``.gtnmod`` 的步骤统计合并进 report。"""

    name = package or path.name
    try:
        with zipfile.ZipFile(path) as archive:
            payload = json.loads(archive.read("mod.json"))
    except Exception as exc:  # noqa: BLE001
        report["errors"].append({"package": name, "error": str(exc)})
        return
    if not isinstance(payload, dict):
        report["errors"].append({"package": name, "error": "mod.json 不是对象"})
        return

    manifest = payload.get("manifest") if isinstance(payload.get("manifest"), dict) else {}
    report["packages"][name] = {
        "mod_id": manifest.get("id") or "",
        "default_language": manifest.get("default_language") or "",
    }

    for registry, resource in iter_registry_resources(payload):
        lists = []
        root_step_lists(resource, lists)
        if not lists:
            continue
        resource_id = str(resource.get("id") or "")
        uses = set()
        legacy = 0
        step_total = 0

        def visit(step, op, _uses=uses, _registry=registry):
            nonlocal legacy, step_total
            step_total += 1
            if op:
                _uses.add(op)
            if op and is_legacy_encoding(step):
                legacy += 1

        for steps in lists:
            walk_steps(steps, visit)

        for op in uses:
            entry = report["op_usage"].setdefault(op, {"cards": 0, "packages": set(), "legacy": 0})
            entry["cards"] += 1
            entry["packages"].add(name)
        if legacy:
            report["legacy_steps"].append(
                {
                    "package": name,
                    "registry": registry,
                    "resource": resource_id,
                    "steps": legacy,
                }
            )
        report["resources_with_logic"] += 1
        report["steps_total"] += step_total


def is_legacy_encoding(step) -> bool:
    return isinstance(step, dict) and "op" not in step


def collect(mods_dir: pathlib.Path, *, only: str = "") -> dict:
    report = {
        "packages": {},
        "op_usage": {},
        "legacy_steps": [],
        "errors": [],
        "resources_with_logic": 0,
        "steps_total": 0,
    }
    for path in sorted(mods_dir.glob("*.gtnmod")):
        if only and not fnmatch.fnmatch(path.name, only):
            continue
        scan_package(path, report)
    return report


SOURCE_SCAN_FILES = (
    "game_engine.py",
    "game_engine_2v2.py",
    "game_engine_urf.py",
    "mod_runtime_v2.py",
    "mod_spec_v2.py",
    "atomic_registry.py",
    "cards.py",
    "mod_loader.py",
    "app.py",
)


def load_source_corpus(extra_dirs=("tests", "tools")) -> list:
    """读取用于查找"间接引用"的源码，返回 [(路径, 文本)]。"""

    paths = [ROOT / name for name in SOURCE_SCAN_FILES]
    for directory in extra_dirs:
        base = ROOT / directory
        if base.is_dir():
            paths.extend(sorted(base.rglob("*.py")))
    corpus = []
    for path in paths:
        try:
            corpus.append((path, path.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return corpus


TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def build_reference_index(corpus) -> dict:
    """把源码切成"标识符 → 出现位置"的索引，避免对每个 op 重扫全部文件。"""

    index = collections.defaultdict(list)
    for path, text in corpus:
        rel = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)
        for number, line in enumerate(text.splitlines(), 1):
            for token in set(TOKEN_RE.findall(line)):
                index[token].append((rel, number, line))
    return index


def find_indirect_references(name: str, corpus) -> list:
    """找出 ``_atomic_<name>`` 定义行以外的引用位置（每个文件最多报一处）。"""

    index = corpus if isinstance(corpus, dict) else build_reference_index(corpus)
    definition = f"def _atomic_{name}("
    hits = []
    seen = set()
    for rel, number, line in index.get(name, ()):
        if definition in line or rel in seen:
            continue
        seen.add(rel)
        hits.append(f"{rel}:{number}")
    return hits


def build_summary(report: dict, *, corpus=None) -> dict:
    core_ops = set(getattr(mod_spec_v2, "_CORE_LOGIC_OPS", set()) or set())
    valid_ops = set(getattr(mod_spec_v2, "VALID_LOGIC_OPS", set()) or set())
    engine_ops = set(atomic_registry.engine_atomic_ops())
    unregistered = engine_ops - core_ops

    usage = report["op_usage"]
    used_ops = set(usage)
    dangling = sorted(op for op in used_ops if op not in valid_ops)
    still_used = sorted(
        (op for op in unregistered if op in used_ops),
        key=lambda op: (-usage[op]["cards"], op),
    )
    unreferenced = sorted(unregistered - used_ops)
    indirect = []
    orphan = []
    if corpus is None:
        corpus = load_source_corpus()
    index = corpus if isinstance(corpus, dict) else build_reference_index(corpus)
    for op in unreferenced:
        hits = find_indirect_references(op, index)
        if hits:
            indirect.append({"op": op, "references": hits})
        else:
            orphan.append(op)

    return {
        "core_ops": len(core_ops),
        "valid_ops": len(valid_ops),
        "engine_ops": len(engine_ops),
        "unregistered_atoms": len(unregistered),
        "cards_total": report["resources_with_logic"],
        "steps_total": report["steps_total"],
        "distinct_ops_used": len(used_ops),
        "dangling": dangling,
        "still_used": [
            {
                "op": op,
                "cards": usage[op]["cards"],
                "packages": sorted(usage[op]["packages"]),
            }
            for op in still_used
        ],
        "unreferenced": unreferenced,
        "indirect": indirect,
        "orphan": orphan,
        "legacy_steps": sorted(
            report["legacy_steps"], key=lambda item: (-item["steps"], item["resource"])
        ),
        "legacy_step_count": sum(item["steps"] for item in report["legacy_steps"]),
        "errors": report["errors"],
    }


def render_text(summary: dict) -> str:
    lines = []
    lines.append("== 引擎能力 ==")
    lines.append(f"  策展通用清单(_CORE_LOGIC_OPS): {summary['core_ops']}")
    lines.append(f"  运行时白名单(VALID_LOGIC_OPS): {summary['valid_ops']}")
    lines.append(f"  _atomic_* 处理器:              {summary['engine_ops']}")
    lines.append(f"  未登记进通用清单的原子:        {summary['unregistered_atoms']}")
    lines.append("")
    lines.append("== 卡数据 ==")
    lines.append(f"  含逻辑的资源: {summary['cards_total']}  |  步骤总数: {summary['steps_total']}"
                 f"  |  出现的 op 种类: {summary['distinct_ops_used']}")
    lines.append("")

    lines.append(f"== 悬空 op（运行时会报错）: {len(summary['dangling'])} ==")
    for op in summary["dangling"]:
        lines.append(f"  {op}")
    lines.append("")

    lines.append(f"== 仍在使用的未登记原子（长尾阻塞项）: {len(summary['still_used'])} ==")
    for item in summary["still_used"]:
        packages = "、".join(item["packages"])
        lines.append(f"  {item['cards']:3d} 张卡  {item['op']:34s} {packages}")
    lines.append("")

    lines.append(
        f"== 未被卡数据引用: {len(summary['unreferenced'])}"
        f"（其中 {len(summary['indirect'])} 个被代码间接引用，{len(summary['orphan'])} 个零引用）=="
    )
    lines.append("  零引用（可删候选）:")
    width = max([len(name) for name in summary["orphan"]] + [0]) + 2
    for index in range(0, len(summary["orphan"]), 4):
        chunk = summary["orphan"][index:index + 4]
        lines.append("  " + "".join(f"{name:<{width}}" for name in chunk).rstrip())
    lines.append("  有间接引用（删前必须确认）:")
    for item in summary["indirect"]:
        lines.append(f"    {item['op']:34s} {item['references'][0]}")
    lines.append("")

    lines.append(f"== 旧写法步骤（type/params）: {summary['legacy_step_count']} ==")
    for item in summary["legacy_steps"][:20]:
        lines.append(f"  {item['steps']:3d} 步  {item['package']} / {item['resource']}")
    if len(summary["legacy_steps"]) > 20:
        lines.append(f"  ...另有 {len(summary['legacy_steps']) - 20} 项")
    lines.append("")

    if summary["errors"]:
        lines.append("== 读取失败 ==")
        for item in summary["errors"]:
            lines.append(f"  {item['package']}: {item['error']}")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="报告卡专用原子与卡数据的对照关系（只读）。")
    parser.add_argument("--mods-dir", default=str(ROOT / "mods"), help="模组目录，默认 <仓库>/mods")
    parser.add_argument("--only", default="", help="只扫描匹配的包名，例如 \"Arctic*\"")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument(
        "--check",
        action="store_true",
        help="发现悬空 op 时以非零状态退出（用于 CI）",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="配合 --check 使用，把旧写法步骤也算作失败",
    )
    args = parser.parse_args(argv)

    mods_dir = pathlib.Path(args.mods_dir)
    if not mods_dir.is_dir():
        print(f"模组目录不存在: {mods_dir}", file=sys.stderr)
        return 2

    summary = build_summary(collect(mods_dir, only=args.only))
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(render_text(summary))

    if args.check and (summary["dangling"] or (args.strict and summary["legacy_step_count"])):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
