# -*- coding: utf-8 -*-
"""排优先级：先做哪些"效果行"句型最划算。

把三份数据交叉起来：

1. ``模组编辑器/src/generated/op-schema.json`` —— 运行时 op 清单、旧编辑器的块覆盖、
   ``runtimeOnly``（运行时支持但编辑器还没有块的 op）；
2. 官方包卡数据里的真实使用次数（复用 ``mod_atom_report`` 的步骤遍历，两种写法都认）；
3. 线框图已有的句型表（``prototype/app.js`` 的 ``ROW_TEMPLATES`` 键）。

产出 ``模组编辑器/src/generated/op-priority.json`` 和一份可读报告，回答
"实现前 N 个句型能覆盖多少张卡"。

    python tools/op_priority_report.py
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

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mod_atom_report  # noqa: E402

EDITOR = ROOT.parent / "模组编辑器"
SCHEMA = EDITOR / "src" / "generated" / "op-schema.json"
PROTOTYPE_APP = EDITOR / "prototype" / "app.js"
DEFAULT_OUT = EDITOR / "src" / "generated" / "op-priority.json"


def prototype_templates() -> list:
    """读线框图里已经实现的句型表键名。"""

    if not PROTOTYPE_APP.is_file():
        return []
    text = PROTOTYPE_APP.read_text(encoding="utf-8")
    start = text.find("const ROW_TEMPLATES = {")
    if start < 0:
        return []
    depth = 0
    end = start
    for index in range(text.index("{", start), len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                end = index
                break
    body = text[start:end]
    return sorted(set(re.findall(r"^  ([a-z0-9_]+):\s*\{", body, re.MULTILINE)))


def scan_usage(mods_dir: pathlib.Path):
    """统计每个 op 的使用次数与涉及资源数，并收集每个资源的 op 集合。"""

    usage = collections.defaultdict(lambda: {"uses": 0, "resources": 0, "packages": set()})
    resource_op_sets = []
    for path in sorted(glob.glob(str(mods_dir / "*.gtnmod"))):
        name = pathlib.Path(path).name
        try:
            with zipfile.ZipFile(path) as archive:
                payload = json.loads(archive.read("mod.json"))
        except Exception:
            continue
        for registry, resource in mod_atom_report.iter_registry_resources(payload):
            lists = []
            mod_atom_report.root_step_lists(resource, lists)
            if not lists:
                continue
            ops = []

            def visit(step, op, _ops=ops):
                if op:
                    _ops.append(op)

            for steps in lists:
                mod_atom_report.walk_steps(steps, visit)
            for op in set(ops):
                entry = usage[op]
                entry["uses"] += ops.count(op)
                entry["resources"] += 1
                entry["packages"].add(name)
            if ops:
                resource_op_sets.append(set(ops))
    return usage, resource_op_sets


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="效果行句型的优先级排序。")
    parser.add_argument("--mods-dir", default=str(ROOT / "mods"))
    parser.add_argument("--schema", default=str(SCHEMA))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--top", type=int, default=25)
    args = parser.parse_args(argv)

    schema_path = pathlib.Path(args.schema)
    if not schema_path.is_file():
        print(f"缺少 op schema：{schema_path}，先跑 tools/extract_op_schema.py")
        return 2
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    runtime_ops = set(schema.get("runtimeOnly", [])) | set(schema.get("ops", {}))
    has_block = set(schema.get("ops", {}))
    templates = set(prototype_templates())

    usage, resource_op_sets = scan_usage(pathlib.Path(args.mods_dir))
    total_resources = len(resource_op_sets)
    total_uses = sum(entry["uses"] for entry in usage.values())
    ranked = sorted(
        usage.items(),
        key=lambda item: (-item[1]["resources"], -item[1]["uses"], item[0]),
    )
    max_resources = max((entry["resources"] for _, entry in ranked), default=1)

    rows = []
    cumulative_uses = 0
    for op, entry in ranked:
        cumulative_uses += entry["uses"]
        rows.append({
            "op": op,
            "uses": entry["uses"],
            "resources": entry["resources"],
            "packages": sorted(entry["packages"]),
            "inRuntime": op in runtime_ops,
            "hasBlock": op in has_block,
            "hasTemplate": op in templates,
            "cumulativeUses": cumulative_uses,
        })
    # 用当前累计的 op 集合，回填"累计用量占比"和"能完全表达的卡数"
    seen_ops = set()
    for row in rows:
        seen_ops.add(row["op"])
        row["useShare"] = round(row["cumulativeUses"] / total_uses * 100, 1) if total_uses else 0.0
        row["fullyExpressible"] = sum(1 for ops in resource_op_sets if ops <= seen_ops)

    payload = {
        "runtimeOps": len(runtime_ops),
        "templatedOps": sorted(templates),
        "ranking": rows,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"运行时 op: {len(runtime_ops)} | 线框图已有句型: {len(templates)} | 卡数据出现过的 op: {len(rows)}")
    print(f"{'op':32s} {'卡数':>4s} {'次数':>5s} {'累计用量':>8s} {'可完整表达':>10s}  块 句型")
    for row in rows[: args.top]:
        print(
            f"{row['op']:32s} {row['resources']:4d} {row['uses']:5d}"
            f" {row['useShare']:7.1f}% {row['fullyExpressible']:5d}/{total_resources:<4d}"
            f"  {'有' if row['hasBlock'] else '无'}  {'有' if row['hasTemplate'] else '无'}"
        )
    covered = [row for row in rows if row["hasTemplate"]]
    print()
    print(f"已有句型的 op 覆盖卡数据出现次数: {sum(r['uses'] for r in covered)}"
          f" / {sum(r['uses'] for r in rows)}")
    print(f"written: {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
