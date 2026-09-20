# -*- coding: utf-8 -*-
"""生成《状态总表》：`docs/状态总表.md`。

状态现在是**引擎内置 + 包可扩展**两层的结构（Round 107 / 批次 DE 起）：

1. 官方 17 条 → `official_statuses.py`（唯一权威表，客户端 `CORE_STATUS_DEFS` 由它生成）；
2. 引擎内建短状态（poison / fire / nazar / dodge…）→ 运行时的词表与玩家属性字段；
3. 包内声明的状态（目前只有形式逻辑 DLC）→ `registries.statuses`。

写卡的人要一份能查的表：这条状态叫什么、什么颜色、哪来的、规则是什么、
现在有多少张卡在用它。统计口径与 `tools/mod_atom_report.py` 的
``status_id_consistency`` 一致（``status`` / ``statuses`` 两个键）。

用法::

    python tools/status_table.py            # 重写 docs/状态总表.md
    python tools/status_table.py --check     # 只对拍
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import official_statuses  # noqa: E402
import mod_atom_report  # noqa: E402

MODS = ROOT / "mods"
DEFAULT_OUT = ROOT / "docs" / "状态总表.md"
STATUS_STEP_KEYS = ("status", "statuses")


def collect_references() -> tuple:
    """扫所有包的 ``status`` / ``statuses`` 步骤位，统计每个状态名被谁引用。"""

    usage: dict = {}
    for path in sorted(MODS.glob("*.gtnmod")):
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
            resource_id = str(resource.get("id") or "")
            names = set()

            def visit(step, op, _names=names):
                if op not in mod_atom_report.STATUS_OPS and not any(
                        key in step for key in STATUS_STEP_KEYS):
                    return
                for key in STATUS_STEP_KEYS:
                    raw = step.get(key)
                    values = raw if isinstance(raw, list) else [raw]
                    for value in values:
                        name = value
                        if isinstance(value, dict):
                            name = value.get("id") or value.get("status")
                        if isinstance(name, str) and name.strip():
                            _names.add(name.strip())

            for steps in lists:
                mod_atom_report.walk_steps(steps, visit)
            for name in names:
                entry = usage.setdefault(name, {"cards": set(), "packages": set()})
                entry["cards"].add(f"{path.name}::{resource_id or registry}")
                entry["packages"].add(path.name)
    return usage


def engine_builtin_statuses() -> list:
    """引擎内建短状态：运行时词表（``_status_label`` / ``_builtin_status_attr``）。"""

    runtime = (ROOT / "mod_runtime_v2.py").read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(runtime)
    except SyntaxError:
        return []
    tables = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in ("_status_label", "_builtin_status_attr"):
            for item in ast.walk(node):
                if isinstance(item, ast.Dict):
                    for key, value in zip(item.keys, item.values):
                        if isinstance(key, ast.Constant) and isinstance(key.value, str) \
                                and isinstance(value, ast.Constant) and isinstance(value.value, str):
                            tables.setdefault(node.name, {})[key.value] = value.value
    labels = tables.get("_status_label", {})
    attrs = tables.get("_builtin_status_attr", {})
    out = []
    for key, label in sorted(labels.items()):
        out.append({
            "id": key,
            "label": label,
            "attr": attrs.get(key, ""),
        })
    return out


def package_declared_statuses() -> list:
    """包内声明的状态（官方 17 条已内置，这里通常只剩形式逻辑）。"""

    builtin = {str(item["id"]) for item in official_statuses.OFFICIAL_STATUSES}
    out = []
    for path in sorted(MODS.glob("*.gtnmod")):
        try:
            with zipfile.ZipFile(path) as archive:
                payload = json.loads(archive.read("mod.json"))
        except Exception:
            continue
        for item in (payload.get("registries") or {}).get("statuses") or []:
            if not isinstance(item, dict):
                continue
            status_id = str(item.get("id") or "")
            if not status_id or status_id in builtin:
                continue
            out.append({
                "id": status_id,
                "package": path.name,
                "name_cn": str(item.get("name_cn") or item.get("name") or ""),
                "name_en": str(item.get("name_en") or ""),
                "color": str(item.get("color") or ""),
                "stacking": str(item.get("stacking") or "stack"),
                "visible": bool(item.get("visible", True)),
                "description": str(item.get("description") or ""),
            })
    return out


def usage_cell(usage: dict, names) -> str:
    cards = set()
    packages = set()
    for name in names:
        entry = usage.get(name)
        if not entry:
            continue
        cards |= entry["cards"]
        packages |= entry["packages"]
    if not cards:
        return "0"
    sample = sorted(cards)[0].split("::")[-1]
    return f"{len(cards)} 张 / {len(packages)} 包<br>`{sample}`"


def render() -> str:
    usage = collect_references()
    official = official_statuses.OFFICIAL_STATUSES
    lines = [
        "# 状态总表（自动生成）",
        "",
        "> 由 `python tools/status_table.py` 生成，**不要手改**；`--check` 在 CI/批次收尾时对拍。",
        "> 权威数据源：官方状态＝`official_statuses.py`；引擎内建短状态＝`mod_runtime_v2` 词表；",
        "> 包内声明＝各包 `registries.statuses`。客户端内置表 `CORE_STATUS_DEFS` 由",
        "> `tools/sync_core_status_defs.py` 从同一份权威表生成，两边不一致会 fail。",
        "",
        "## 1. 官方内置状态（17 条）",
        "",
        "写卡时直接引用 id 即可（`status_op.status`）；**不需要**在自己的包里再声明。",
        "颜色/图标/文案由内置表提供，官方包与社区包看到的是同一份。",
        "",
        "| id | 中文名 | 英文名 | 颜色 | 图标 | 可见 | 规则要点（中文） | 行为实现 | 现引用 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in official:
        events = item.get("events") or {}
        impl = "状态 events：" + "、".join(sorted(events)) if events else "引擎硬编码"
        desc = item["desc_i18n"]["zh"].replace("|", "\\|")
        names = {item["id"], item["alias"], *item["name_i18n"].values()}
        lines.append(
            f"| `{item['id']}` | {item['name_i18n']['zh']} | {item['name_i18n']['en']} | "
            f"`{item['color'] or '—'}` | `{item['icon'] or '—'}` | "
            f"{'是' if item['visible'] else '否（内部层）'} | {desc} | {impl} | "
            f"{usage_cell(usage, names)} |"
        )
    lines.append("")
    lines.append("## 2. 引擎内建短状态（运行时词表）")
    lines.append("")
    lines.append("这些是引擎自带的状态名（玩家属性字段+自定义层数两张表），写卡同样直接用。")
    lines.append("")
    lines.append("| 名字 / 别名 | 中文名 | 玩家属性字段 | 现引用 |")
    lines.append("|---|---|---|---|")
    for item in engine_builtin_statuses():
        lines.append(
            f"| `{item['id']}` | {item['label']} | "
            f"`{item['attr'] or '（自定义层数 custom_statuses）'}` | "
            f"{usage_cell(usage, [item['id'], item['label']])} |"
        )
    lines.append("")
    lines.append("## 3. 包内声明的状态")
    lines.append("")
    declared = package_declared_statuses()
    if declared:
        lines.append("| id | 来源包 | 中文名 | 英文名 | 颜色 | 叠加 | 可见 | 现引用 |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for item in declared:
            lines.append(
                f"| `{item['id']}` | {item['package']} | {item['name_cn']} | {item['name_en']} | "
                f"`{item['color'] or '—'}` | `{item['stacking']}` | "
                f"{'是' if item['visible'] else '否'} | {usage_cell(usage, [item['id']])} |"
            )
    else:
        lines.append("（当前没有包声明状态；形式逻辑 DLC 除外时会出现在这里。）")
    lines.append("")
    lines.append("## 4. 引用统计口径")
    lines.append("")
    lines.append("与 `tools/mod_atom_report.py` 的 `status_id_consistency` 同口径：")
    lines.append("")
    lines.append("```")
    lines.append("python tools/status_table.py --check        # 本表是否与权威数据一致")
    lines.append("python tools/sync_core_status_defs.py --check  # 客户端内置表是否同步")
    lines.append("python tools/migrate_builtin_statuses.py --check  # 包内是否又声明了内置状态")
    lines.append("python tools/mod_atom_report.py --check --strict   # 状态 id 是否认得（拼错会失败）")
    lines.append("```")
    lines.append("")
    lines.append("`现引用` 列＝扫描 `mods/*.gtnmod` 里 `status` / `statuses` 步骤位得到的"
                 "「资源数 / 包数」，取一条示例资源；短名与中文名一起计入。")
    lines.append("")
    lines.append("**引用 0 不一定是没人用**：由 op 内部施加的状态不会出现在卡数据的 `status` 位上"
                 "（例如 `equipment_op(mode:\"seal\")` 记的是装备变量 `sewers_sealed`，"
                 "对上表里的 `sewers:sealed`），这类状态看的是实现侧而不是卡数据侧。")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="生成《状态总表》（只读源码，写一个 md）。")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--check", action="store_true", help="只对拍，不写文件")
    args = parser.parse_args(argv)

    expected = render()
    out = pathlib.Path(args.out)
    if args.check:
        if not out.is_file():
            print(f"缺少生成物：{out}", file=sys.stderr)
            return 1
        current = out.read_text(encoding="utf-8")
        if current.replace("\r\n", "\n") != expected:
            print(f"[check] {out.name} 与最新生成的内容不一致，跑一次 `python tools/status_table.py` 刷新。",
                  file=sys.stderr)
            return 1
        print(f"状态总表已同步：{out.name}")
        return 0

    out.write_text(expected, encoding="utf-8")
    print(f"written: {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
