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
import ast
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


def _quoted_names(block: str) -> set:
    return set(re.findall(r"[\"']([a-z0-9_]+)[\"']", block or ""))


HOOK_DISPATCH_CALLS = (
    "_run_v2_event_hooks",
    "_run_v2_play_hook",
    "_run_card_event_package_hook",   # 卡级事件镜像（批次 BE）
    "_fire_window_open_hook",         # 选择/响应窗口建立前（批次 BF）
)
HOOK_SOURCE_FILES = ("game_engine.py", "game_engine_2v2.py", "game_engine_urf.py", "mod_runtime_v2.py")


def _dispatched_event_hook_names() -> set:
    """真正被当作**包级钩子**派发的名字（Round 67 / 批次 BE 改成 AST 判定）。

    以前只做子串搜索，于是卡级事件名（``on_equipment_trigger`` /
    ``on_resource_spent`` / ``on_player_stat_changed`` / ``on_damage_taken`` …）
    因为出现在 ``EVENT_EFFECT_TYPES``、``SCRIPT_ENTRY_ALIASES`` 这些**别的表**里
    就被误判成"已触发"，写进 ``event_hooks`` 其实静默无效。

    现在只认两种真派发：
      * ``_run_v2_event_hooks('X', …)`` / ``_run_v2_play_hook('X', …)`` 的实参
        （含 ``'on_status_added' if delta > 0 else 'on_status_removed'`` 这种
        条件表达式里的两个常量）；
      * ``for hook_name in ('before_damage', 'modify_damage')`` 这类循环元组里
        的名字，且循环体里真的有派发调用。
    """

    found = set()
    for filename in HOOK_SOURCE_FILES:
        path = ROOT / filename
        if not path.is_file():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func
            name = getattr(func, "attr", None) or getattr(func, "id", None)
            if name not in HOOK_DISPATCH_CALLS:
                continue
            argument = node.args[0]
            if isinstance(argument, ast.Name):
                # 循环变量：把所在 for 的常量元组全算进来（循环体里就是派发）。
                for loop in ast.walk(tree):
                    if not isinstance(loop, ast.For):
                        continue
                    target = loop.target
                    if not (isinstance(target, ast.Name) and target.id == argument.id):
                        continue
                    for item in ast.walk(loop.iter):
                        if isinstance(item, ast.Constant) and isinstance(item.value, str):
                            found.add(item.value)
                continue
            for item in ast.walk(argument):
                if isinstance(item, ast.Constant) and isinstance(item.value, str):
                    found.add(item.value)
    return found


def _event_hook_synonym_groups() -> list:
    """``game_engine._v2_hooks_for`` 里的同义钩子组（组内任意名字注册都生效）。"""

    path = ROOT / "game_engine.py"
    if not path.is_file():
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    groups = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "_v2_hooks_for":
            continue
        for statement in node.body:
            if not isinstance(statement, ast.Assign):
                continue
            targets = [getattr(target, "id", None) for target in statement.targets]
            if "groups" not in targets or not isinstance(statement.value, (ast.Tuple, ast.List)):
                continue
            for element in statement.value.elts:
                if not isinstance(element, (ast.Tuple, ast.List)):
                    continue
                group = tuple(
                    item.value for item in element.elts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                )
                if group:
                    groups.append(group)
    return groups


def event_hook_consistency() -> dict:
    """``VALID_EVENT_HOOKS``（包级 event_hooks 白名单）里的每个名字，必须真的在
    引擎源码里按**包级钩子**被派发——否则写出来是静默无效果（Round 56 / 批次 AT
    立规矩，Round 67 / 批次 BE 把判定升级成 AST 真派发）。
    """

    hooks = sorted(getattr(mod_spec_v2, "VALID_EVENT_HOOKS", set()) or set())
    dispatched = _dispatched_event_hook_names()
    triggerable = set(dispatched)
    for group in _event_hook_synonym_groups():
        if any(name in dispatched for name in group):
            triggerable.update(group)
    missing = [name for name in hooks if name not in triggerable]
    problems = []
    if missing:
        problems.append(f"登记了但引擎从不触发的事件钩子（写出来静默无效）：{missing}")
    return {
        "declared": len(hooks),
        "dispatched": len(dispatched),
        "synonym_groups": [list(group) for group in _event_hook_synonym_groups()],
        "missing": missing,
        "problems": problems,
    }


def ui_type_consistency() -> dict:
    """Round 55：`request_ui` 的三层类型表一致性。

    * 声明：``mod_spec_v2.VALID_UI_COMPONENT_TYPES`` / ``VALID_UI_CONTROL_TYPES``
    * 运行时白名单：``mod_runtime_v2._sanitize_ui_component`` /
      ``_sanitize_ui_control`` 里的 ``if ctype not in {…}``
    * 客户端渲染：``static/js/game.js`` 的 ``showV2UiRequest`` 里
      ``type === '…'`` 分支

    三层对不上时返回 ``problems``（``--check`` 会当失败项）。以前这三张表是
    各写各的——声明 29 种、运行时认 14 种，按清单写会运行时报错。
    """

    runtime_text = (ROOT / "mod_runtime_v2.py").read_text(encoding="utf-8", errors="replace")
    declared_components = set(getattr(mod_spec_v2, "VALID_UI_COMPONENT_TYPES", set()) or set())
    declared_controls = set(getattr(mod_spec_v2, "VALID_UI_CONTROL_TYPES", set()) or set())
    problems = []

    def runtime_set(function_name: str) -> set:
        match = re.search(
            r"def " + re.escape(function_name) + r"\(.*?if ctype not in \{([^}]*)\}",
            runtime_text,
            re.S,
        )
        return _quoted_names(match.group(1)) if match else set()

    runtime_components = runtime_set("_sanitize_ui_component")
    runtime_controls = runtime_set("_sanitize_ui_control")
    if not runtime_components or not runtime_controls:
        problems.append("没能从 mod_runtime_v2 里解析出 UI 白名单（正则或实现结构变了？）")
    client_controls = set()
    client_path = ROOT / "static" / "js" / "game.js"
    if client_path.is_file():
        client_text = client_path.read_text(encoding="utf-8", errors="replace")
        start = client_text.find("function showV2UiRequest")
        if start >= 0:
            end = client_text.find("\nfunction ", start + 10)
            body = client_text[start:end if end > start else start + 20000]
            client_controls = set(re.findall(r"type === '([a-z0-9_]+)'", body))
            client_controls |= set(re.findall(r'type === "([a-z0-9_]+)"', body))
    else:
        problems.append("找不到 static/js/game.js（客户端渲染分支没法核对）")
    if declared_components != runtime_components:
        problems.append(
            "窗口类型：声明与运行时白名单不一致；只多 "
            f"{sorted(declared_components - runtime_components)}；只少 "
            f"{sorted(runtime_components - declared_components)}"
        )
    if declared_controls != runtime_controls:
        problems.append(
            "控件类型：声明与运行时白名单不一致；只多 "
            f"{sorted(declared_controls - runtime_controls)}；只少 "
            f"{sorted(runtime_controls - declared_controls)}"
        )
    missing_client = sorted(runtime_controls - client_controls)
    if missing_client:
        problems.append(f"运行时认、客户端没有渲染分支的控件：{missing_client}")
    return {
        "declared_components": len(declared_components),
        "declared_controls": len(declared_controls),
        "runtime_components": len(runtime_components),
        "runtime_controls": len(runtime_controls),
        "client_controls": len(client_controls),
        "problems": problems,
    }


def target_selector_consistency(mods_dir: pathlib.Path) -> dict:
    """Round 72 / 批次 BM：卡数据里 ``target``/``viewer``/``owner`` 的**字符串**值
    必须落在两层选择器词表 ``mod_runtime_v2.PLAYER_SELECTOR_STRINGS`` 里。

    写错名字的后果是**静默命中错误目标**——最糟的时候静默变成"自己"
    （``health_op(mode:"lose", target:"enmey")`` 是自伤）。这条按**信息项**常驻
    报告：词表外的名字连同用它的包一起列出来；只有真的写了错名字才在
    ``problems`` 里出现（``--check`` 会失败）。
    """

    try:
        import mod_runtime_v2  # noqa: PLC0415

        vocabulary = set(getattr(mod_runtime_v2, "PLAYER_SELECTOR_STRINGS", set()) or set())
    except Exception as exc:  # noqa: BLE001
        return {"checked": 0, "vocabulary": 0, "unknown": [], "problems": [f"读不到选择器词表：{exc}"]}
    if not vocabulary:
        return {"checked": 0, "vocabulary": 0, "unknown": [], "problems": ["选择器词表是空的（PLAYER_SELECTOR_STRINGS 丢了？）"]}

    keys = ("target", "viewer", "owner")
    values = collections.defaultdict(set)
    checked = 0
    for path in sorted(mods_dir.glob("*.gtnmod")):
        try:
            with zipfile.ZipFile(path) as archive:
                payload = json.loads(archive.read("mod.json"))
        except Exception:
            continue
        for registry, resource in iter_registry_resources(payload):
            lists = []
            root_step_lists(resource, lists)
            if not lists:
                continue
            resource_id = f"{path.name}:{registry}:{resource.get('id')}"

            def visit(step, _op, _rid=resource_id):
                nonlocal checked
                for key in keys:
                    value = step.get(key)
                    if isinstance(value, str) and value.strip():
                        checked += 1
                        values[value.strip()].add(_rid)

            for steps in lists:
                walk_steps(steps, visit)
    unknown = [
        {"value": value, "resources": sorted(values[value])[:4]}
        for value in sorted(values)
        if value.lower() not in vocabulary
    ]
    problems = []
    if unknown:
        problems.append(
            "卡数据里用了选择器词表外的 target/viewer/owner 名字"
            "（写错会静默命中错误目标）："
            + ", ".join(f"{item['value']!r} @ {item['resources'][:1]}" for item in unknown[:6])
        )
    return {"checked": checked, "vocabulary": len(vocabulary), "unknown": unknown, "problems": problems}


def build_summary(report: dict, *, corpus=None, mods_dir: pathlib.Path | None = None) -> dict:
    core_ops = set(getattr(mod_spec_v2, "_CORE_LOGIC_OPS", set()) or set())
    valid_ops = set(getattr(mod_spec_v2, "VALID_LOGIC_OPS", set()) or set())
    engine_ops = set(atomic_registry.engine_atomic_ops())
    unregistered = engine_ops - core_ops

    usage = report["op_usage"]
    used_ops = set(usage)
    dangling = sorted(op for op in used_ops if op not in valid_ops)
    # Round 47 / 批次 AK：口径分层——公开原子 / 内部处理器 / 宏。
    public_atoms = set(getattr(mod_spec_v2, "PUBLIC_ATOMS", set()) or set())
    internal_handlers = set(getattr(mod_spec_v2, "INTERNAL_HANDLERS", set()) or set())
    macros = dict(getattr(mod_spec_v2, "ATOMIC_OP_MACROS", {}) or {})
    runtime_steps = set(getattr(mod_spec_v2, "RUNTIME_STEP_OPS", set()) or set())
    secret_used = sorted(op for op in used_ops if op in internal_handlers)
    macro_used = sorted(op for op in used_ops if op in macros)
    step_ops = engine_ops | runtime_steps
    layer_missing = sorted(
        op for op in step_ops
        if op not in public_atoms and op not in internal_handlers and op not in macros
    )
    layer_overlap = sorted(
        (public_atoms & internal_handlers)
        | (public_atoms & set(macros))
        | (internal_handlers & set(macros))
    )
    retired_public = sorted(public_atoms & (set(mod_spec_v2.REMOVED_ATOMIC_OPS) | set(mod_spec_v2.RENAMED_ATOMIC_OPS)))
    layer_problems = []
    if layer_missing:
        layer_problems.append(f"三层口径没铺满步骤 op（漏 {len(layer_missing)} 个）：{layer_missing[:6]}")
    if layer_overlap:
        layer_problems.append(f"三层口径有重叠：{layer_overlap[:6]}")
    if retired_public:
        layer_problems.append(f"公开原子里混进了已退役名字：{retired_public[:6]}")
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
        "public_atoms": len(public_atoms),
        "public_atom_names": sorted(public_atoms),
        "internal_handlers": len(internal_handlers),
        "internal_handler_names": sorted(internal_handlers),
        "macros": len(macros),
        "macro_map": dict(sorted(macros.items())),
        "layer_problems": layer_problems,
        "ui_types": ui_type_consistency(),
        "event_hooks": event_hook_consistency(),
        # Round 72 / 批次 BM：卡数据的 target/viewer/owner 名字必须落在选择器词表里。
        "target_selectors": target_selector_consistency(
            mods_dir if mods_dir is not None else ROOT / "mods"
        ),
        "secret_ops_used": [
            {"op": op, "cards": usage[op]["cards"], "packages": sorted(usage[op]["packages"])}
            for op in secret_used
        ],
        "macro_ops_used": [
            {"op": op, "cards": usage[op]["cards"], "replacement": macros[op],
             "packages": sorted(usage[op]["packages"])}
            for op in macro_used
        ],
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


def logic_group_lines() -> list:
    """Round 25：登记名按真实执行路径分五类（`mod_spec_v2.LOGIC_OP_GROUPS`）。

    类别口径见 `docs/引擎原子与数据步骤清单.md` §23；这里的数字必须和
    `tools/atom_parameter_table.py --check` 的一致。
    """

    getter = getattr(mod_spec_v2, "logic_op_groups", None)
    if not callable(getter):
        return []
    counts = {label: len(names) for label, names in getter().items()}
    lines = ["  登记名分类（Round 25，五类并集 = 上面的策展通用清单）:"]
    for label, _names in getattr(mod_spec_v2, "LOGIC_OP_GROUPS", ()):
        lines.append(f"    {label}: {counts.get(label, 0)}")
    legacy = len(getattr(mod_spec_v2, "UNCLASSIFIED_LOGIC_OPS", ()) or ())
    lines.append(f"    仅登记、无实现（应为 0）: {legacy}")
    return lines


def atom_layer_lines(summary: dict) -> list:
    """Round 47：三层口径——"原子到底有多少个"看这里，不看 `_CORE_LOGIC_OPS`。"""

    lines = ["  原子口径分层（Round 47，卡数据只该写第一层 + 宏）:"]
    lines.append(f"    公开原子（可写进卡数据的步骤 op）: {summary['public_atoms']}")
    lines.append(f"    内部处理器（保留实现，数据写不出来）: {summary['internal_handlers']}")
    lines.append(f"    宏（写出来即改写为规范 op）: {summary['macros']}")
    return lines


def render_text(summary: dict) -> str:
    lines = []
    lines.append("== 引擎能力 ==")
    lines.append(f"  策展通用清单(_CORE_LOGIC_OPS): {summary['core_ops']}")
    lines.append(f"  运行时白名单(VALID_LOGIC_OPS): {summary['valid_ops']}")
    lines.append(f"  _atomic_* 处理器:              {summary['engine_ops']}")
    lines.append(f"  未登记进通用清单的原子:        {summary['unregistered_atoms']}")
    lines.extend(atom_layer_lines(summary))
    lines.extend(logic_group_lines())
    lines.append("")
    lines.append("== 卡数据 ==")
    lines.append(f"  含逻辑的资源: {summary['cards_total']}  |  步骤总数: {summary['steps_total']}"
                 f"  |  出现的 op 种类: {summary['distinct_ops_used']}")
    lines.append("")

    lines.append(f"== 悬空 op（运行时会报错）: {len(summary['dangling'])} ==")
    for op in summary["dangling"]:
        lines.append(f"  {op}")
    lines.append("")

    lines.append(f"== 卡数据里的内部处理器（写出来会显式报错）: {len(summary['secret_ops_used'])} ==")
    for item in summary["secret_ops_used"]:
        lines.append(f"  {item['cards']:3d} 张卡  {item['op']:34s} {'、'.join(item['packages'])}")
    lines.append("")

    lines.append(f"== 卡数据里的宏（建议改成规范 op）: {len(summary['macro_ops_used'])} ==")
    for item in summary["macro_ops_used"]:
        lines.append(
            f"  {item['cards']:3d} 张卡  {item['op']:34s} → {item['replacement']}"
            f"  {'、'.join(item['packages'])}"
        )
    lines.append("")

    if summary["layer_problems"]:
        lines.append("== 三层口径不变量（Round 47）: 失败 ==")
        for problem in summary["layer_problems"]:
            lines.append(f"  {problem}")
        lines.append("")

    ui = summary.get("ui_types") or {}
    hooks = summary.get("event_hooks") or {}
    selectors = summary.get("target_selectors") or {}
    if selectors:
        lines.append(
            f"== 目标选择器词表对拍（target/viewer/owner）: 看到 "
            f"{selectors.get('checked', 0)} 处，词表 {selectors.get('vocabulary', 0)} 个名字，"
            f"词表外的 {len(selectors.get('unknown') or [])} 个 =="
        )
        for item in selectors.get("unknown") or []:
            lines.append(f"  [失败] {item['value']!r} @ {item['resources'][:2]}")
        lines.append("")
    if hooks:
        lines.append(
            f"== 包级事件钩子（event_hooks 白名单）: 登记 {hooks['declared']} 个，"
            f"真派发 {hooks.get('dispatched', '?')} 个 + 同义组 "
            f"{len(hooks.get('synonym_groups') or [])} 组，引擎从不触发的 "
            f"{len(hooks['missing'])} 个 =="
        )
        for problem in hooks.get("problems") or []:
            lines.append(f"  [失败] {problem}")
        lines.append("")
    if ui:
        lines.append(
            "== request_ui 类型表（声明 / 运行时 / 客户端）: "
            f"{ui['declared_components']} / {ui['runtime_components']} / 控件 "
            f"{ui['declared_controls']} / {ui['runtime_controls']} / {ui['client_controls']} =="
        )
        for problem in ui.get("problems") or []:
            lines.append(f"  [失败] {problem}")
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

    summary = build_summary(collect(mods_dir, only=args.only), mods_dir=mods_dir)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(render_text(summary))

    if args.check and (
        summary["dangling"]
        or (args.strict and summary["legacy_step_count"])
        # Round 47 / 批次 AK：口径分层的不变量与"数据写了内部处理器"都算失败。
        or summary["layer_problems"]
        or summary["secret_ops_used"]
        # Round 55 / 批次 AS：UI 三层类型表必须一致。
        or (summary.get("ui_types") or {}).get("problems")
        # Round 56 / 批次 AT：包级事件钩子白名单里的名字必须真的会被触发。
        or (summary.get("event_hooks") or {}).get("problems")
        # Round 72 / 批次 BM：卡数据的选择器名字必须在两层词表里。
        or (summary.get("target_selectors") or {}).get("problems")
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
