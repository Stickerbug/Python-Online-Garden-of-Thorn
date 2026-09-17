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
import mod_runtime_v2  # noqa: E402
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


def _minimal_ui_package(controls: list, step: dict | None = None) -> dict:
    """给发布期校验造一个最小可投稿包（社区命名空间，不与官方撞）。"""

    card_events = {"on_play": {"steps": [step or {"op": "log", "message": "x"}]}}
    return {
        "format_version": 2,
        "manifest": {
            "id": "codexui",
            "resource_namespace": "codexui",
            "name": "Codex UI probe",
            "version": "0.1.0",
            "api_version": mod_spec_v2.API_VERSION,
            "capabilities": ["ui_components", "logic.advanced"],
        },
        "registries": {
            "cards": [{
                "id": "codexui:probe",
                "name_cn": "探针",
                "card_type": "thorn",
                "cost_e": 1,
                "description_cn": "探针。",
                "events": card_events,
            }],
            "ui_components": [{
                "id": "codexui:window",
                "type": "modal",
                "title_cn": "探针窗口",
                "controls": controls,
                "buttons": [{"id": "confirm", "text_cn": "确认", "role": "confirm"}],
            }],
        },
    }


def ui_param_validation_consistency() -> dict:
    """Round 94 / 批次 CQ：**运行时词表**必须都在**发布期**校验里。

    背景：``input.value_type`` / ``text_input.normalize`` / ``text_input.moderation`` /
    ``text_input.pattern`` / ``request_ui.on_invalid`` 这几项以前只有运行时校验
    （``mod_runtime_v2`` 里显式 raise）——包能正常导入，要等玩家打开窗口才炸。
    批次 CQ 把同一套词表提到 ``mod_validator_v2``。

    这条守门用**反例**验证：每个"运行时认不出就会拒绝"的写法，发布期必须拦下；
    同时合法写法必须放行（防止校验过严把好包也拒了）。
    """

    import mod_validator_v2 as validator

    def bad_control(**extra) -> dict:
        control = {"id": "c1", "type": "text", "label_cn": "标签"}
        control.update(extra)
        return control

    cases = [
        ("input.value_type", bad_control(type="input", value_type="intt")),
        ("text_input.normalize", bad_control(type="text_input", normalize="trim_up")),
        ("text_input.moderation", bad_control(type="text_input", moderation="block")),
        ("text_input.pattern", bad_control(type="text_input", pattern="([")),
    ]
    problems = []
    caught = 0
    for name, control in cases:
        package = _minimal_ui_package([control])
        result = validator.validate_mod_v2(package, source="<probe>", allow_reserved_namespaces=True)
        if result.errors:
            caught += 1
        else:
            problems.append(f"发布期没拦下 {name} 的错写法（运行时会 raise）")
    step_case = {"op": "request_ui", "component": "codexui:window",
                 "save_as": "choice", "on_invalid": "retry"}
    step_result = validator.validate_mod_v2(
        _minimal_ui_package([], step=step_case), source="<probe>", allow_reserved_namespaces=True)
    if step_result.errors:
        caught += 1
    else:
        problems.append("发布期没拦下 request_ui.on_invalid 的错写法（运行时会 raise）")

    good_package = _minimal_ui_package([
        bad_control(type="input", value_type="number"),
        {"id": "c2", "type": "text_input", "label_cn": "输入", "normalize": "trim",
         "moderation": "mask", "max_length": 32, "pattern": "^[a-z]+$"},
        {"id": "c3", "type": "multi_select", "label_cn": "多选", "min_select": 1, "max_select": 3,
         "options": [{"value": "a", "label_cn": "A"}]},
    ], step={"op": "request_ui", "component": "codexui:window", "save_as": "choice",
             "on_invalid": "keep", "timeout_ms": 5000, "on_cancel": []})
    good_result = validator.validate_mod_v2(good_package, source="<probe>", allow_reserved_namespaces=True)
    if good_result.errors:
        problems.append(f"合法写法被发布期误拒：{good_result.errors[:3]}")

    # 编辑器面板手抄的四张词表也要与引擎同一份（否则作者在编辑器里选得到、
    # 运行时却拒绝，或者反过来）。编辑器是兄弟仓：整个仓不在时跳过（CI 里只有引擎仓）。
    editor_note = ""
    editor_root = ROOT.parent / "模组编辑器"
    editor_file = editor_root / "src" / "v2Studio.js"
    if not editor_root.is_dir():
        editor_note = "（编辑器仓不在，跳过）"
    elif not editor_file.is_file():
        problems.append(f"找不到编辑器源码 {editor_file}（词表没法对拍）")
    else:
        editor_text = editor_file.read_text(encoding="utf-8", errors="replace")
        engine_lists = {
            "UI_INPUT_VALUE_TYPES": mod_runtime_v2.INPUT_VALUE_TYPES,
            "UI_TEXT_NORMALIZES": mod_runtime_v2.TEXT_INPUT_NORMALIZES,
            "UI_TEXT_MODERATIONS": mod_runtime_v2.TEXT_INPUT_MODERATIONS,
            "UI_REQUEST_ON_INVALID": mod_runtime_v2.REQUEST_UI_ON_INVALID_VALUES,
        }
        for const_name, engine_values in engine_lists.items():
            match = re.search(
                r"const " + re.escape(const_name) + r"\s*=\s*\[(.*?)\]",
                editor_text,
                re.S,
            )
            if not match:
                problems.append(f"编辑器里找不到 {const_name}（对拍失效，常量被改名了？）")
                continue
            editor_values = tuple(re.findall(r"'([^']*)'", match.group(1)))
            if editor_values != tuple(engine_values):
                problems.append(
                    f"{const_name} 与引擎词表不一致：编辑器 {list(editor_values)}，"
                    f"引擎 {list(engine_values)}"
                )
    return {
        "cases": len(cases) + 1,
        "caught": caught,
        "false_positive": len(good_result.errors),
        "editor_note": editor_note,
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
    # Round 77 / 批次 BV：编辑器别名（radio_group / zone_picker / divider …）在运行时
    # 归一到已有控件，声明表把它们算进来、运行时白名单不算——对拍时先减掉别名。
    alias_match = re.search(r"UI_CONTROL_TYPE_ALIASES\s*=\s*\{(.*?)\n\}", runtime_text, re.S)
    aliases = set(re.findall(r'"([a-z0-9_]+)"\s*:', alias_match.group(1))) if alias_match else set()
    declared_controls = declared_controls - aliases
    declared_components = declared_components - aliases
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


def _ui_component_text_issues(component: dict) -> list:
    """某个 ``request_ui`` 组件里"显示不出中文"的地方（Round 76 / 批次 BU）。"""

    issues = []
    if not (component.get("title_cn") or component.get("title")):
        issues.append("组件没有标题（title_cn）")
    for index, control in enumerate(component.get("controls") or []):
        if not isinstance(control, dict):
            continue
        cid = str(control.get("id") or f"#{index}")
        ctype = str(control.get("type") or "text")
        if ctype == "text":
            if not (control.get("text_cn") or control.get("text")):
                issues.append(f"控件 {cid}（text）没有 text_cn")
        elif not (control.get("label_cn") or control.get("label")
                   or control.get("text_cn") or control.get("text")):
            issues.append(f"控件 {cid}（{ctype}）没有 label_cn（界面会没有标题）")
        for option_index, option in enumerate(control.get("options") or []):
            if isinstance(option, dict) and not (option.get("label_cn") or option.get("label")):
                issues.append(f"控件 {cid} 的选项[{option_index}]没有 label_cn")
    for index, button in enumerate(component.get("buttons") or []):
        if not isinstance(button, dict):
            continue
        bid = str(button.get("id") or f"#{index}")
        if not (button.get("text_cn") or button.get("label_cn")
                or button.get("text") or button.get("label")):
            issues.append(f"按钮 {bid} 没有 text_cn（会按角色兜底成“确定”）")
    return issues


# Round 81 / 批次 CA：引擎里"不是通过 ``_status_attr_field`` 映射"的状态名（人工核对过
# 都有读取方）：``all`` 是 clear 的预设关键字，其余是引擎自己的布尔/计数状态。
EXTRA_ENGINE_STATUS_NAMES = frozenset({
    "all", "invincible", "status_immune", "immune", "nazar", "nazar_active",
    "magic_nazar", "magic_blocked", "toxic_poison", "bandage_active", "untargetable",
})

STATUS_STEP_KEYS = ("status", "statuses")
STATUS_OPS = ("status_op", "status_add_named", "status_remove_named", "status_set_named",
              "has_status", "has_status_named", "player_status_layers")


def _engine_status_words() -> set:
    """``_status_attr_field`` 的字符串常量（引擎内建状态 + 中文别名）。"""

    path = ROOT / "game_engine.py"
    if not path.is_file():
        return set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return set()
    words = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_status_attr_field":
            for item in ast.walk(node):
                if isinstance(item, ast.Constant) and isinstance(item.value, str):
                    words.add(item.value.strip().lower())
    return words | {name.lower() for name in EXTRA_ENGINE_STATUS_NAMES}


def status_id_consistency(mods_dir: pathlib.Path) -> dict:
    """Round 81 / 批次 CA：卡数据里的状态 id 必须**认得**。

    引擎把不认识的状态名当**自定义状态**处理：包声明过就有效，拼错的话就静默无效
    （和"幽灵钩子"同一类毛病）。词表 = 引擎内建/别名 ∪ **官方包声明过的** id/别名
    （跨包引用在本地图里是合法的，比如 Garden 的卡用 `jungle:shield`——所以只把
    "哪儿都没声明"的名字当失败，跨包引用单列成提示）。
    """

    engine_words = _engine_status_words()
    checked = 0
    unknown = []
    cross_package = []
    packages_scanned = 0
    payloads = []
    for path in sorted(mods_dir.glob("*.gtnmod")):
        try:
            with zipfile.ZipFile(path) as archive:
                payload = json.loads(archive.read("mod.json"))
        except Exception:
            continue
        packages_scanned += 1
        payloads.append((path, payload))
    declared_all = set()
    declared_by_package: dict = {}
    for path, payload in payloads:
        names = set()
        for item in (payload.get("registries") or {}).get("statuses") or []:
            if isinstance(item, dict) and item.get("id"):
                names.add(str(item["id"]).strip().lower())
                for alias in item.get("aliases") or []:
                    names.add(str(alias).strip().lower())
        declared_by_package[path.name] = names
        declared_all |= names
    for path, payload in payloads:
        declared = set()
        for item in (payload.get("registries") or {}).get("statuses") or []:
            if isinstance(item, dict) and item.get("id"):
                declared.add(str(item["id"]).strip().lower())
                for alias in item.get("aliases") or []:
                    declared.add(str(alias).strip().lower())
        for registry, resource in iter_registry_resources(payload):
            lists = []
            root_step_lists(resource, lists)
            if not lists:
                continue
            source = f"{path.name}:{registry}:{resource.get('id')}"

            def visit(step, op, _source=source, _declared=declared):
                nonlocal checked
                if op not in STATUS_OPS and not any(key in step for key in STATUS_STEP_KEYS):
                    return
                for key in STATUS_STEP_KEYS:
                    raw = step.get(key)
                    values = raw if isinstance(raw, list) else [raw]
                    for value in values:
                        name = value
                        if isinstance(value, dict):
                            name = value.get("id") or value.get("status")
                        if not isinstance(name, str) or not name.strip():
                            continue
                        checked += 1
                        text = name.strip().lower()
                        if text in engine_words or text in declared_all:
                            if text not in declared and text not in engine_words:
                                cross_package.append({"value": name.strip(), "resource": _source})
                            continue
                        unknown.append({"value": name.strip(), "resource": _source})

            for steps in lists:
                walk_steps(steps, visit)
    problems = []
    if unknown:
        seen = {(item["value"], item["resource"]) for item in unknown}
        problems.append(
            "卡数据里用了**没有任何包声明**的状态名（引擎会当自定义状态；拼错就静默无效）："
            + ", ".join(f"{value!r} @ {resource}" for value, resource in sorted(seen)[:6])
        )
    return {"checked": checked, "packages": packages_scanned,
            "vocabulary": len(engine_words) + len(declared_all),
            "declared": len(declared_all),
            "unknown": unknown[:20], "cross_package": len(cross_package),
            "problems": problems}


# Round 87 / 批次 CI：卡面文案里的**内联标记**（``[[card:ID]]`` / ``[[icon:KEY]]``）。
CARD_TEXT_MARKUP_RE = re.compile(r"\[\[([a-z_]+):([^\]|]+)((?:\|[^\]]*)?)\]\]")


def _client_inline_icon_keys() -> set:
    """从 ``static/js/game.js`` 抽 ``[[icon:…]]`` 的词表（``INLINE_ICON_DATA_URLS`` + ``uiIcons``）。"""

    path = ROOT / "static" / "js" / "game.js"
    if not path.is_file():
        return set()
    text = path.read_text(encoding="utf-8", errors="replace")
    keys = set()
    for block_name in ("INLINE_ICON_DATA_URLS", "uiIcons"):
        start = text.find(f"const {block_name} = {{")
        if start < 0:
            start = text.find(f"const {block_name}={{" if False else f"{block_name} = {{")
        if start < 0:
            continue
        end = text.find("\n    };", start)
        if end < 0:
            end = text.find("\n};", start)
        if end < 0:
            end = start + 6000
        for match in re.finditer(r"^\s*'?([A-Za-z0-9_\-]+)'?:\s*'", text[start:end], re.M):
            keys.add(match.group(1))
    return keys


def patch_op_consistency() -> dict:
    """Round 92 / 批次 CO：``VALID_PATCH_OPS`` 里的每个 patch op 必须**真的被应用**。

    patch 由 ``mod_loadout_v2._apply_patch`` 执行；如果某个 op 只登记在白名单里、
    那边没有分支，包写了这条 patch 会被静默跳过（只留一条 warnings 文案）——
    和"幽灵钩子"同一类毛病。这里按源码里的 ``if op == "X"`` / ``if op in ("X", …)``
    分支对拍。
    """

    path = ROOT / "mod_loadout_v2.py"
    declared = sorted(getattr(mod_spec_v2, "VALID_PATCH_OPS", set()) or set())
    if not path.is_file():
        return {"declared": len(declared), "handled": [], "missing": declared,
                "problems": ["找不到 mod_loadout_v2.py，无法核对 patch op"]}
    text = path.read_text(encoding="utf-8", errors="replace")
    start = text.find("def _apply_patch(")
    end = text.find("\ndef ", start + 10) if start >= 0 else -1
    body = text[start:end if end > start else len(text)] if start >= 0 else ""
    handled = set(re.findall(r"if op == ['\"]([a-z_]+)['\"]", body))
    for group in re.findall(r"if op in \(([^)]*)\)", body):
        handled.update(re.findall(r"['\"]([a-z_]+)['\"]", group))
    missing = sorted(set(declared) - handled)
    problems = []
    if missing:
        problems.append(f"登记了但 _apply_patch 没有分支的 patch op（写了会被静默跳过）：{missing}")
    return {"declared": len(declared), "handled": sorted(handled), "missing": missing,
            "problems": problems}


def capability_consistency(mods_dir: pathlib.Path) -> dict:
    """Round 91 / 批次 CN：`manifest.capabilities` 的白名单 vs 官方包实际声明。

    背景：capability 目前是**纯声明元数据**（`mod_validator_v2` 只做白名单校验，
    引擎/应用没有任何门控读取方）。所以这里只守一条：**官方包声明的能力名必须在白名单里**
    （否则它们会被校验器拒收）；反过来"白名单里有、没人声明"的名字只作提示
    （它们是给第三方包预留的名字，删掉会让已经写了这些名字的包直接导入失败）。
    """

    declared = set(getattr(mod_spec_v2, "VALID_CAPABILITIES", set()) or set())
    used = set()
    packages = 0
    for path in sorted(mods_dir.glob("*.gtnmod")):
        try:
            with zipfile.ZipFile(path) as archive:
                payload = json.loads(archive.read("mod.json"))
        except Exception:
            continue
        packages += 1
        for cap in ((payload.get("manifest") or {}).get("capabilities") or []):
            used.add(str(cap))
    unknown = sorted(used - declared)
    problems = []
    if unknown:
        problems.append(f"官方包声明了白名单外的 capability：{unknown}")
    return {
        "declared": len(declared),
        "used": sorted(used),
        "unused": sorted(declared - used),
        "packages": packages,
        "problems": problems,
    }


def card_text_reference_consistency(mods_dir: pathlib.Path) -> dict:
    """Round 87 / 批次 CI：卡面文案引用的卡与图标必须真实存在。

    中文卡面文案是第一权威（见用户规则），里面的 ``[[card:ID]]`` 写错就会渲染成
    普通文字、``[[icon:KEY]]`` 写错会退化成裸字母——都是"看着像对、其实不对"的毛病。
    这里把 20 个官方包的 ``mod.json`` 与 ``locales/*.json`` 里所有字符串扫一遍对拍。
    """

    known_cards = set()
    known_icons = _client_inline_icon_keys()
    payloads = []
    for path in sorted(mods_dir.glob("*.gtnmod")):
        try:
            with zipfile.ZipFile(path) as archive:
                payload = json.loads(archive.read("mod.json"))
                locales = [
                    archive.read(name).decode("utf-8", "replace")
                    for name in archive.namelist()
                    if name.startswith("locales/") and name.endswith(".json")
                ]
        except Exception:
            continue
        payloads.append((path.name, payload, locales))
        for card in (payload.get("registries") or {}).get("cards") or []:
            if not isinstance(card, dict):
                continue
            for key in ("id", "legacy_id"):
                value = str(card.get(key) or "").strip()
                if value:
                    known_cards.add(value)
    checked_cards = 0
    checked_icons = 0
    unknown_cards = []
    unknown_icons = []
    for name, payload, locales in payloads:
        blobs = [json.dumps(payload, ensure_ascii=False)] + locales
        for blob in blobs:
            for kind, value, modifiers in CARD_TEXT_MARKUP_RE.findall(blob):
                if kind == "card":
                    checked_cards += 1
                    if value.strip() not in known_cards:
                        unknown_cards.append({"package": name, "value": value.strip()})
                elif kind == "icon":
                    checked_icons += 1
                    if known_icons and value.strip() not in known_icons:
                        unknown_icons.append({"package": name, "value": value.strip()})
    problems = []
    if unknown_cards:
        seen = sorted({(item["value"], item["package"]) for item in unknown_cards})
        problems.append(
            "卡面文案里 [[card:ID]] 指向不存在的卡："
            + ", ".join(f"{value!r} @ {package}" for value, package in seen[:6])
        )
    if unknown_icons:
        seen = sorted({(item["value"], item["package"]) for item in unknown_icons})
        problems.append(
            "卡面文案里 [[icon:KEY]] 不是客户端认识的图标："
            + ", ".join(f"{value!r} @ {package}" for value, package in seen[:6])
        )
    return {
        "cards": checked_cards,
        "icons": checked_icons,
        "known_cards": len(known_cards),
        "known_icons": len(known_icons),
        "unknown_cards": unknown_cards[:20],
        "unknown_icons": unknown_icons[:20],
        "problems": problems,
    }


def ui_text_consistency(mods_dir: pathlib.Path) -> dict:
    """Round 76 / 批次 BU：官方包里每个 ``request_ui`` 组件都必须有**中文文案**。

    以前按钮只认 ``text*``、控件没文案时回落**控件 id**，于是机械触角窗口里出现了
    ``confirm`` / ``pick``。现在引擎两套键都认、控件不再回落 id，这条检查负责盯住
    "卡数据到底写没写中文"（中文是卡面第一语言，见用户规则）。
    """

    components = 0
    problems = []
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
            resource_id = str(resource.get("id") or "")
            found = []

            def visit(step, op, _found=found, _registry=registry):
                if op == "request_ui" and isinstance(step.get("component"), dict):
                    _found.append(step["component"])

            for steps in lists:
                walk_steps(steps, visit)
            for component in found:
                components += 1
                for issue in _ui_component_text_issues(component):
                    problems.append(f"{path.name}:{registry}:{resource_id} —— {issue}")
    return {"components": components, "problems": problems}


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
        # Round 76 / 批次 BU：request_ui 组件的文案必须有中文（不能显示英文/控件 id）。
        "ui_text": ui_text_consistency(mods_dir if mods_dir is not None else ROOT / "mods"),
        # Round 94 / 批次 CQ：运行时词表必须都在发布期校验里（用反例对拍）。
        "ui_param_validation": ui_param_validation_consistency(),
        # Round 81 / 批次 CA：卡数据的 status id 必须有声明（引擎内建或包 statuses）。
        "status_ids": status_id_consistency(mods_dir if mods_dir is not None else ROOT / "mods"),
        # Round 87 / 批次 CI：卡面文案里的 [[card:ID]] / [[icon:KEY]] 必须真实存在。
        "card_text_refs": card_text_reference_consistency(
            mods_dir if mods_dir is not None else ROOT / "mods"
        ),
        # Round 91 / 批次 CN：官方包声明的 capability 必须在白名单里。
        "capabilities": capability_consistency(
            mods_dir if mods_dir is not None else ROOT / "mods"
        ),
        # Round 92 / 批次 CO：注册的 patch op 必须真的被 mod_loadout_v2 应用。
        "patch_ops": patch_op_consistency(),
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
    ui_text = summary.get("ui_text") or {}
    if ui_text:
        lines.append(
            f"== request_ui 文案（中文优先）: 组件 {ui_text.get('components', 0)} 个，"
            f"缺中文文案的 {len(ui_text.get('problems') or [])} 处 =="
        )
        for problem in (ui_text.get("problems") or [])[:8]:
            lines.append(f"  [失败] {problem}")
        lines.append("")
    status_ids = summary.get("status_ids") or {}
    if status_ids:
        lines.append(
            f"== 状态 id 对拍: 看到 {status_ids.get('checked', 0)} 处，词表 "
            f"{status_ids.get('vocabulary', 0)} 个名字，没声明的 "
            f"{len(status_ids.get('unknown') or [])} 个（跨包引用 "
            f"{status_ids.get('cross_package', 0)} 处，合法）=="
        )
        for problem in (status_ids.get("problems") or [])[:6]:
            lines.append(f"  [失败] {problem}")
        lines.append("")
    card_refs = summary.get("card_text_refs") or {}
    if card_refs:
        lines.append(
            f"== 卡面文案引用对拍: [[card:…]] {card_refs.get('cards', 0)} 处、"
            f"[[icon:…]] {card_refs.get('icons', 0)} 处；"
            f"词表 {card_refs.get('known_cards', 0)} 张卡 / {card_refs.get('known_icons', 0)} 个图标，"
            f"对不上的 {len(card_refs.get('problems') or [])} 类 =="
        )
        for problem in (card_refs.get("problems") or [])[:6]:
            lines.append(f"  [失败] {problem}")
        lines.append("")
    caps = summary.get("capabilities") or {}
    if caps:
        lines.append(
            f"== manifest.capabilities 对拍: 白名单 {caps.get('declared', 0)} 个，"
            f"官方包声明了 {len(caps.get('used') or [])} 个，"
            f"白名单里没人声明的 {len(caps.get('unused') or [])} 个（预留名，只提示）=="
        )
        for problem in (caps.get("problems") or [])[:4]:
            lines.append(f"  [失败] {problem}")
        lines.append("")
    patch_ops = summary.get("patch_ops") or {}
    if patch_ops:
        lines.append(
            f"== patch op 对拍（VALID_PATCH_OPS vs mod_loadout_v2）: 登记 "
            f"{patch_ops.get('declared', 0)} 个，有分支 "
            f"{len(patch_ops.get('handled') or [])} 个，没分支 "
            f"{len(patch_ops.get('missing') or [])} 个 =="
        )
        for problem in (patch_ops.get("problems") or [])[:4]:
            lines.append(f"  [失败] {problem}")
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
    param_check = summary.get("ui_param_validation") or {}
    if param_check:
        lines.append(
            "== request_ui 参数发布期校验（反例对拍）: "
            f"反例 {param_check['caught']} / {param_check['cases']} 拦下，"
            f"合法写法误拒 {param_check['false_positive']} =="
        )
        for problem in param_check.get("problems") or []:
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
        # Round 76 / 批次 BU：request_ui 组件的文案必须有中文。
        or (summary.get("ui_text") or {}).get("problems")
        # Round 94 / 批次 CQ：运行时词表必须都在发布期校验里（反例对拍）。
        or (summary.get("ui_param_validation") or {}).get("problems")
        # Round 81 / 批次 CA：卡数据的 status id 必须有声明（没人声明的按拼错处理）。
        or (summary.get("status_ids") or {}).get("problems")
        # Round 87 / 批次 CI：卡面文案引用的卡/图标必须存在。
        or (summary.get("card_text_refs") or {}).get("problems")
        # Round 91 / 批次 CN：官方包声明的 capability 必须在白名单里。
        or (summary.get("capabilities") or {}).get("problems")
        # Round 92 / 批次 CO：注册的 patch op 必须真的被应用。
        or (summary.get("patch_ops") or {}).get("problems")
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
