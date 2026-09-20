# -*- coding: utf-8 -*-
"""生成编辑器与游戏之间的唯一契约：op schema。

编辑器侧有一份 **op → 标签表**（``模组编辑器/src/generated/op-labels.json``：
块 id / 分类 / 中文标签 / 参数名与种类 / 文档），运行时侧有
``mod_spec_v2.VALID_LOGIC_OPS``（策展清单 ∪ 引擎 ``_atomic_*``）。
两边各有一份 op 知识，长期必然漂移。本脚本把两边取并集，产出
``模组编辑器/src/generated/op-schema.json``：

* 每个 op 的编辑器元数据（块 id、分类、句型、参数名与种类、文档）；
* 每个 op 是否存在于运行时；
* ``runtimeOnly`` —— 运行时支持但编辑器还没有块的 op（编辑器的能力缺口）；
* ``blocksOnly``  —— 编辑器有块、运行时却不认识的 op（陈旧块，会造成"编辑通过、线上报错"）。

    python tools/extract_op_schema.py

Round 93 / 批次 CP：标签来源从"退役的 Blockly 画布文件 `v2BlockRegistry.js`"迁到
``op-labels.json``（纯数据）。迁移用 ``--blocks-from-js <path>`` 还能从旧文件解析，
但默认只读 JSON——编辑器仓库不再背着 2327 行、不进构建的伪代码。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
EDITOR_SRC = ROOT.parent / "模组编辑器" / "src"
BLOCKS_JS = EDITOR_SRC / "v2BlockRegistry.js"      # 迁移用的旧画布文件（批次 CP 后已删除）
LABELS_JSON = EDITOR_SRC / "generated" / "op-labels.json"
DEFAULT_OUT = ROOT.parent / "模组编辑器" / "src" / "generated" / "op-schema.json"


def _match_paren(text: str, start: int) -> int:
    """返回与 ``text[start] == '('`` 配对的右括号下标。"""

    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char == "'":
            index += 1
            while index < len(text) and text[index] != "'":
                index += 2 if text[index] == "\\" else 1
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def _match_bracket(text: str, start: int) -> int:
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char == "'":
            index += 1
            while index < len(text) and text[index] != "'":
                index += 2 if text[index] == "\\" else 1
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def _split_top_level(body: str) -> list:
    parts = []
    depth = 0
    current = []
    index = 0
    while index < len(body):
        char = body[index]
        if char == "'":
            current.append(char)
            index += 1
            while index < len(body) and body[index] != "'":
                current.append(body[index])
                index += 1
            if index < len(body):
                current.append(body[index])
        elif char in "([{":
            depth += 1
            current.append(char)
        elif char in ")]}":
            depth -= 1
            current.append(char)
        elif char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        index += 1
    if current:
        parts.append("".join(current).strip())
    return parts


def _arg_kind(entry: str) -> dict:
    name_match = re.search(r"name:\s*'([A-Za-z0-9_]+)'", entry)
    name = name_match.group(1) if name_match else ""
    if not name:
        call = re.match(r"([A-Za-z]+)\('([A-Za-z0-9_]+)'", entry)
        if call:
            name = call.group(2)
    if "input_statement" in entry:
        return {"name": name, "kind": "statement"}
    if "input_value" in entry:
        check = re.search(r"check:\s*'([A-Za-z0-9_]+)'", entry)
        return {"name": name, "kind": "value", "check": check.group(1) if check else ""}
    if "field_dropdown" in entry:
        return {"name": name, "kind": "dropdown", "options": "unknown"}
    if "field_number" in entry or entry.startswith("fieldNumber"):
        return {"name": name, "kind": "number"}
    if "fieldInput" in entry or "field_input" in entry:
        return {"name": name, "kind": "text"}
    return {"name": name, "kind": "unknown"}


def parse_blocks(path: pathlib.Path) -> dict:
    """**迁移用**：从退役的 ``v2BlockRegistry.js`` 里解析 op → 标签（现已改读 JSON）。"""

    if not path.is_file():
        raise SystemExit(
            f"找不到块定义文件：{path}\n"
            "默认标签来源已经是模组编辑器/src/generated/op-labels.json；"
            "只有做迁移/对比时才需要用 --blocks-from-js 指向旧的画布文件。"
        )
    text = path.read_text(encoding="utf-8")
    ops = {}
    for match in re.finditer(r"\bblock\('([A-Za-z0-9_]+)',\s*'([A-Za-z0-9_]+)'", text):
        start = text.find("(", match.start())
        end = _match_paren(text, start)
        if end < 0:
            continue
        body = text[start:end]
        args_body = ""
        args_at = body.find("args0:")
        if args_at >= 0:
            bracket = body.find("[", args_at)
            close = _match_bracket(body, bracket)
            if close > 0:
                args_body = body[bracket + 1:close]
        message = re.search(r"message0:\s*'([^']*)'", body)
        op_match = re.search(r"op:\s*'([A-Za-z0-9_]+)'", body)
        docs_match = re.search(r"\},\s*\([^)]*\)\s*=>[^,]*,\s*'([^']*)'", body)
        if not op_match:
            # 值/表达式块（数字、文本、目标选择器…）的 op 由求值器处理，
            # 不在这里登记，避免被误判成"陈旧的块"。
            continue
        ops.setdefault(op_match.group(1), {
            "block": match.group(1),
            "category": match.group(2),
            "label": message.group(1) if message else "",
            "docs": docs_match.group(1) if docs_match else "",
            "params": [_arg_kind(entry) for entry in _split_top_level(args_body) if entry],
        })
    return ops


def load_labels(path: pathlib.Path) -> dict:
    """读标签表：``*.json`` 读数据文件，其它后缀按旧画布 JS 解析（迁移用）。"""

    if not path.is_file():
        raise SystemExit(
            f"找不到 op 标签表：{path}\n"
            "它给 schema 里的每个 op 提供块 id / 分类 / 中文标签 / 参数名与种类；"
            "用 --labels 指定别的路径，或从编辑器仓库把它恢复回来。"
        )
    if path.suffix.lower() != ".json":
        return parse_blocks(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    ops = payload.get("ops") if isinstance(payload, dict) else None
    if not isinstance(ops, dict):
        raise SystemExit(f"标签表格式不对（应该是 {{\"ops\": {{op: …}}}}）：{path}")
    return {str(name): dict(entry) for name, entry in ops.items() if isinstance(entry, dict)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="生成 op schema（编辑器 ∩ 运行时）。")
    parser.add_argument("--labels", default=str(LABELS_JSON),
                        help="op → 标签表（JSON；默认读编辑器仓库的 generated/op-labels.json）")
    parser.add_argument("--blocks-from-js", default="",
                        help="迁移用：从旧画布文件 v2BlockRegistry.js 解析标签（覆盖 --labels）")
    parser.add_argument("--blocks", default="", help="--blocks-from-js 的旧名字（兼容）")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import atomic_registry
    import mod_spec_v2
    import official_statuses

    runtime_ops = set(mod_spec_v2.VALID_LOGIC_OPS)
    curated_ops = set(getattr(mod_spec_v2, "_CORE_LOGIC_OPS", set()) or set())
    engine_ops = set(atomic_registry.engine_atomic_ops())

    source = args.blocks_from_js or args.blocks
    blocks = (load_labels(pathlib.Path(source)) if source
              else load_labels(pathlib.Path(args.labels)))
    for op, entry in blocks.items():
        entry["inRuntime"] = op in runtime_ops
        entry["curated"] = op in curated_ops
        entry["engineAtom"] = op in engine_ops

    runtime_only = sorted(runtime_ops - set(blocks))

    # 编辑器有块、但不在步骤白名单里的 op：可能是表达式算子（由求值器处理），
    # 也可能是真的陈旧块。到运行时源码里找一下引用，把两类分开。
    source_files = [
        ROOT / "mod_runtime_v2.py",
        ROOT / "mod_spec_v2.py",
        ROOT / "game_engine.py",
        ROOT / "game_engine_2v2.py",
        ROOT / "game_engine_urf.py",
    ]
    sources = [(path, path.read_text(encoding="utf-8", errors="replace"))
               for path in source_files if path.is_file()]
    needs_review = {}
    for op in sorted(set(blocks) - runtime_ops):
        hit = ""
        quoted = f"'{op}'"
        for path, text in sources:
            offset = text.find(quoted)
            if offset >= 0:
                line = text.count("\n", 0, offset) + 1
                hit = f"{path.name}:{line}"
                break
        needs_review[op] = hit or "no reference"

    payload = {
        "runtimeOps": len(runtime_ops),
        "blockOps": len(blocks),
        "ops": dict(sorted(blocks.items())),
        "runtimeOnly": runtime_only,
        "needsReview": needs_review,
        # Round 108 / 批次 DF：官方状态内置表（`official_statuses.py`）。
        # 编辑器离线时也要有一份与引擎同源的官方状态清单：状态下拉、校验提示、
        # "这条状态已经是内置的，不用再声明" 都靠它，别再去读包里的 registries.statuses。
        "officialStatuses": [
            {
                "id": item["id"],
                "alias": item["alias"],
                "name_zh": item["name_i18n"]["zh"],
                "name_en": item["name_i18n"]["en"],
                "desc_zh": item["desc_i18n"]["zh"],
                "desc_en": item["desc_i18n"]["en"],
                "color": item["color"],
                "icon": item["icon"],
                "stacking": item["stacking"],
                "visible": item["visible"],
                "package": item["package"],
                "tags": list(item.get("tags") or ()),
            }
            for item in official_statuses.OFFICIAL_STATUSES
        ],
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("runtime ops:", len(runtime_ops))
    print("block ops:", len(blocks), "| 其中运行时认识的:", sum(1 for e in blocks.values() if e["inRuntime"]))
    print("runtimeOnly (编辑器还没有块):", len(runtime_only))
    referenced = [op for op, hit in needs_review.items() if hit != "no reference"]
    stale = [op for op, hit in needs_review.items() if hit == "no reference"]
    print("不在步骤白名单的块 op:", len(needs_review),
          f"（{len(referenced)} 个在运行时源码里能找到引用，{len(stale)} 个找不到）")
    print("  找不到引用的:", stale)
    print(f"written: {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
