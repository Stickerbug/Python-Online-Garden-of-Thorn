# -*- coding: utf-8 -*-
"""生成《原子参数表》（``docs/原子参数表.md``）：游戏原子 + 参数 + 默认值 + 真实用例 + 使用次数 + 扩展点。

只读源码与卡数据，可重复运行（幂等；不写时间戳）：

    python tools/atom_parameter_table.py            # 写 docs/原子参数表.md
    python tools/atom_parameter_table.py --check    # 只校验，不写文件（数字与 mod_atom_report 不一致时非零退出）
    python tools/atom_parameter_table.py --stdout   # 打到标准输出

数据来源

1. ``mod_spec_v2.VALID_LOGIC_OPS`` —— 原子 / op 全集（350）。
2. ``atomic_registry.engine_atomic_ops()`` —— 有 ``_atomic_*`` 实现的 op（213）。
3. ``mod_runtime_v2.run_v2_step`` / ``eval_v2_value`` / ``check_v2_condition`` ——
   运行时原生的步骤 / 值表达式 / 条件 op，以及它们各自读的参数键。
4. ``game_engine*.py`` 的 ``_atomic_*`` 方法，以及它们调用的共享助手里的 ``params.get(...)``。
5. ``mods/*.gtnmod`` 的根 ``mod.json`` —— 真实用例（首次出现的卡 id + 最小 JSON 片段）与使用次数。
6. ``docs/引擎原子与数据步骤清单.md`` —— 分类与语义（本表不重新发明语义；清单里抽不到的标"需人工"）。

判定口径与 ``tools/mod_atom_report.py`` 完全一致：同一个步骤遍历器、同一份 ``_CORE_LOGIC_OPS``。
"""

from __future__ import annotations

import argparse
import ast
import collections
import json
import pathlib
import re
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import atomic_registry  # noqa: E402
import mod_atom_report  # noqa: E402
import mod_runtime_v2  # noqa: E402
import mod_spec_v2  # noqa: E402

DOC_LIST = ROOT / "docs" / "引擎原子与数据步骤清单.md"
DEFAULT_OUT = ROOT / "docs" / "原子参数表.md"
ENGINE_FILES = ("game_engine.py", "game_engine_2v2.py", "game_engine_urf.py")
MODS_DIR = ROOT / "mods"

# 表达式求值包装：被这些函数包住的 ``params.get(...)`` 参数支持"取值表达式"。
EVAL_WRAPPERS = {
    "eval_v2_value",
    "_eval_int",
    "_eval_expr",
    "_step_text_value",
    "_to_int",
    "_to_number",
}
PARAM_OBJECTS = ("params", "expr", "cond", "step", "node")
STEP_LIST_KEYS = mod_atom_report.STEP_LIST_KEYS
ALIAS_LABELS = {
    "runtime": "运行时",
    "engine": "引擎",
    "expr": "表达式",
    "cond": "条件",
    "hook": "时点",
}
# Round 25：登记名按"真实执行路径"分五类（``mod_spec_v2.LOGIC_OP_GROUPS``）。
# 铺不满登记表时剩下的名字落到这个兜底类——正确值是 0 个。
LEGACY_GROUP_LABEL = "遗留登记名（仅登记、无实现）"


def op_group_label(op: str) -> str:
    """op 属于五类里的哪一类；不属于任何一类时返回兜底类名。"""

    return mod_spec_v2.logic_op_group(op) or LEGACY_GROUP_LABEL


def group_labels() -> list[str]:
    return [label for label, _names in mod_spec_v2.LOGIC_OP_GROUPS] + [LEGACY_GROUP_LABEL]


def group_counts() -> dict[str, int]:
    counts = {label: len(names) for label, names in mod_spec_v2.logic_op_groups().items()}
    counts[LEGACY_GROUP_LABEL] = len(getattr(mod_spec_v2, "UNCLASSIFIED_LOGIC_OPS", ()) or ())
    return counts


# ---------------------------------------------------------------------------
# 通用小工具


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def literal_text(value) -> str | None:
    """把字面量渲染成表里能读的一小段文本；不是字面量返回 None。"""

    if value is None:
        return "`None`"
    if isinstance(value, bool):
        return "`True`" if value else "`False`"
    if isinstance(value, str):
        return f"`{json.dumps(value, ensure_ascii=False)}`"
    if isinstance(value, (int, float)):
        return f"`{value!r}`"
    return None


def default_node_text(node: ast.AST | None) -> tuple[str, str]:
    """返回 ``(显示文本, 形态)``；形态 ∈ literal / same-param / const-name / expr / 空。"""

    if node is None:
        return "", ""
    try:
        value = ast.literal_eval(node)
    except Exception:  # noqa: BLE001
        value = None
    else:
        if value is not None or isinstance(node, ast.Constant):
            text = literal_text(value)
            if text:
                return text, "literal"
    if isinstance(node, ast.Name):
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", node.id):
            return f"常量 `{node.id}`", "const-name"
        return "", "expr"
    if isinstance(node, ast.Attribute):
        return f"常量 `{ast.unparse(node)}`", "const-name"
    if isinstance(node, ast.Dict):
        return "`{…}`", "literal"
    if isinstance(node, (ast.List, ast.Tuple)):
        return "`[…]`", "literal"
    return "", "expr"


def param_get_key(node: ast.AST, objects, bindings=None) -> list[str] | None:
    """``params.get('key', …)`` / ``params.get(<绑定到键名列表的变量>, …)`` → 键名列表。"""

    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return None
    if node.func.attr != "get" or not isinstance(node.func.value, ast.Name):
        return None
    if node.func.value.id not in objects:
        return None
    if not node.args:
        return None
    first = node.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return [first.value]
    if isinstance(first, ast.Name) and bindings and first.id in bindings:
        return list(bindings[first.id])
    return None


def module_constants(paths) -> dict:
    """模块级 ``NAME = ("a", "b", …)`` 形态的常量表（模块级键名列表）。"""

    constants: dict[str, list[str]] = {}
    for path in paths:
        if not path.is_file():
            continue
        try:
            tree = ast.parse(read_text(path))
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.Assign) or not isinstance(node.value, (ast.Tuple, ast.List, ast.Set)):
                continue
            values = []
            for element in node.value.elts:
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    values.append(element.value)
            if not values or len(values) != len(node.value.elts):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    constants.setdefault(target.id, values)
    return constants


def module_literal_constants(paths) -> dict:
    r"""``NAME = <字面量>`` 常量表（含类属性；用于把「常量 FOR_EACH_LIMIT」显示成实际值）。"""

    values: dict[str, str] = {}
    for path in paths:
        if not path.is_file():
            continue
        try:
            tree = ast.parse(read_text(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not isinstance(node.targets[0], ast.Name):
                continue
            try:
                value = ast.literal_eval(node.value)
            except Exception:  # noqa: BLE001
                continue
            text = literal_text(value)
            if text:
                values.setdefault(node.targets[0].id, text)
    return values


def iter_keys(node: ast.AST, constants: dict, bindings: dict) -> list[str]:
    """``for key in keys:`` 里 ``keys`` 能解析出来的键名列表。"""

    if isinstance(node, ast.Name):
        if node.id in bindings:
            return list(bindings[node.id])
        return list(constants.get(node.id, ()))
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        values = [element.value for element in node.elts
                  if isinstance(element, ast.Constant) and isinstance(element.value, str)]
        return values if len(values) == len(node.elts) else []
    return []


def signature_bindings(node: ast.FunctionDef, constants: dict) -> dict:
    """函数签名默认值里的键名常量：``def f(..., keys=SELECTOR_TARGET_KEYS)``。"""

    bindings: dict[str, list[str]] = {}
    args = list(node.args.args) + list(node.args.kwonlyargs)
    defaults = list(node.args.defaults) + list(node.args.kw_defaults)
    for arg, default in zip(args[-len(defaults):], defaults) if defaults else ():
        if isinstance(default, ast.Name) and default.id in constants:
            bindings[arg.arg] = constants[default.id]
    return bindings


def local_default_nodes(scope: ast.AST) -> dict:
    """函数/块内的 ``name = <表达式>`` 赋值（用于解析 ``params.get('amount', default_amount)``）。"""

    nodes: dict[str, ast.AST] = {}
    for node in ast.walk(scope):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            nodes.setdefault(node.targets[0].id, node.value)
    return nodes


def describe_default(node: ast.AST, objects, bindings: dict, locals_map: dict, depth: int = 2,
                     constant_values: dict | None = None):
    """默认值节点 → ``(显示文本, 回落键列表)``。"""

    constant_values = constant_values or {}
    if node is None:
        return "", []
    if isinstance(node, ast.Name) and depth > 0 and node.id in locals_map:
        inner = locals_map[node.id]
        keys = param_get_key(inner, objects, bindings) or []
        if keys:
            return "", keys
        return describe_default(inner, objects, bindings, locals_map, depth - 1, constant_values)
    if isinstance(node, ast.Name) and node.id in constant_values:
        return f"{constant_values[node.id]}（常量 `{node.id}`）", []
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
        if node.attr in constant_values:
            return f"{constant_values[node.attr]}（常量 `{node.attr}`）", []
    if isinstance(node, ast.IfExp):
        texts, keys = [], []
        for branch in (node.body, node.orelse):
            text, branch_keys = describe_default(branch, objects, bindings, locals_map, depth - 1,
                                                 constant_values)
            keys.extend(branch_keys)
            if text:
                texts.append(text)
        if keys:
            return "", keys
        if texts:
            return " / ".join(sorted(set(texts))), []
        return "", []
    text, kind = default_node_text(node)
    if kind == "same-param":
        return "", []
    return text, []


def collect_param_hits(scope: ast.AST, objects, *, via: str = "", path: str = "",
                       constants: dict | None = None, bindings: dict | None = None,
                       constant_values: dict | None = None) -> dict:
    """收集一段 AST 里读到的参数键。

    每条记录：``defaults``（形态 → 显示文本）、``expr``（是否被表达式求值包装）、
    ``bare``（有没有 ``params.get('k')`` 无默认值 / ``params['k']``）、``via``、``path``。
    """

    hits: dict[str, dict] = {}
    constants = constants or {}
    base_bindings = dict(bindings or {})
    if isinstance(scope, ast.FunctionDef):
        base_bindings.update(signature_bindings(scope, constants))
    locals_map = local_default_nodes(scope)

    def record(keys, default_node, expr: bool, bare: bool) -> None:
        for key in keys:
            entry = hits.setdefault(
                key,
                {"defaults": {}, "expr": False, "bare": False, "via": set(), "paths": set(),
                 "by_path": {}},
            )
            text = None
            if default_node is not None:
                fallback = param_get_key(default_node, objects, base_bindings)
                if fallback:
                    entry.setdefault("fallback", set()).update(fallback)
                else:
                    text, fallback = describe_default(default_node, objects, base_bindings, locals_map,
                                                      constant_values=constant_values)
                    if fallback:
                        entry.setdefault("fallback", set()).update(fallback)
                        text = None
                if text:
                    entry["defaults"][text] = True
                elif not fallback:
                    entry["defaults"]["（表达式）"] = True
                    text = "（表达式）"
            else:
                entry["bare"] = True
                text = "（无默认值）"
            if expr:
                entry["expr"] = True
            if via:
                entry["via"].add(via)
            if path:
                entry["paths"].add(path)
                if text:
                    entry["by_path"].setdefault(path, set()).add(text)

    def walk(node, expr_depth: int = 0, local_bindings=None) -> None:
        local_bindings = base_bindings if local_bindings is None else local_bindings
        if isinstance(node, (ast.For, ast.AsyncFor)):
            walk(node.iter, expr_depth, local_bindings)
            extra = iter_keys(node.iter, constants, local_bindings)
            inner = dict(local_bindings)
            if isinstance(node.target, ast.Name) and extra:
                inner[node.target.id] = extra
            for statement in list(node.body) + list(node.orelse):
                walk(statement, expr_depth, inner)
            return
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in EVAL_WRAPPERS:
                for arg in node.args:
                    walk(arg, expr_depth + 1, local_bindings)
                for keyword in node.keywords:
                    walk(keyword.value, expr_depth + 1, local_bindings)
                return
            keys = param_get_key(node, objects, local_bindings)
            if keys:
                default_node = node.args[1] if len(node.args) > 1 else None
                fallback = param_get_key(default_node, objects, local_bindings) if default_node is not None else None
                if fallback:
                    record(keys, None, expr_depth > 0, bare=False)
                    for key in keys:
                        hits[key].setdefault("fallback", set()).update(fallback)
                else:
                    record(keys, default_node, expr_depth > 0, bare=default_node is None)
            for arg in node.args:
                walk(arg, expr_depth, local_bindings)
            for keyword in node.keywords:
                walk(keyword.value, expr_depth, local_bindings)
            return
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            if node.value.id in objects and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                record([node.slice.value], None, expr_depth > 0, bare=True)
        for child in ast.iter_child_nodes(node):
            walk(child, expr_depth, local_bindings)

    walk(scope)
    # 别名键（``params.get('a', params.get('b', X))``）默认值向下传递。
    for key, entry in hits.items():
        for fallback in sorted(entry.get("fallback", ())):
            other = hits.get(fallback)
            if other:
                for text in other["defaults"]:
                    entry["defaults"].setdefault(text, True)
    return hits


def merge_hits(target: dict, extra: dict) -> None:
    for key, entry in extra.items():
        slot = target.setdefault(
            key,
            {"defaults": {}, "expr": False, "bare": False, "via": set(), "paths": set(),
             "by_path": {}},
        )
        slot["defaults"].update(entry.get("defaults", {}))
        slot["expr"] = slot["expr"] or bool(entry.get("expr"))
        slot["bare"] = slot["bare"] or bool(entry.get("bare"))
        slot["via"].update(entry.get("via", ()))
        slot["paths"].update(entry.get("paths", ()))
        for path, values in (entry.get("by_path") or {}).items():
            slot["by_path"].setdefault(path, set()).update(values)
        if entry.get("fallback"):
            slot.setdefault("fallback", set()).update(entry["fallback"])


# ---------------------------------------------------------------------------
# 1. 运行时原生 op（步骤 / 表达式 / 条件）


def ops_of_test(node: ast.AST) -> list[str]:
    """从 ``if op == "x":`` / ``if op in ("x", "y"):`` 的测试表达式取 op 名。"""

    ops: list[str] = []
    if not isinstance(node, ast.Compare):
        return ops
    if not isinstance(node.left, ast.Name) or node.left.id != "op":
        return ops
    for comparator in node.comparators:
        values = comparator.elts if isinstance(comparator, (ast.Tuple, ast.List)) else [comparator]
        for value in values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                ops.append(value.value)
    return ops


def function_defs(tree: ast.AST, name: str) -> list[ast.FunctionDef]:
    return [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name]


def follow_module_helpers(hits: dict, source: str, node: ast.AST, functions: dict, constants: dict, *,
                          path_label: str, depth: int = 3, constant_values: dict | None = None) -> tuple[str, list[str]]:
    """跟随 ``helper(params)`` 形态的模块级助手（最多 ``depth`` 层）。"""

    seen: list[str] = []
    frontier = [node]
    for _ in range(depth):
        next_frontier = []
        for current in frontier:
            for call in [n for n in ast.walk(current) if isinstance(n, ast.Call)]:
                if not isinstance(call.func, ast.Name):
                    continue
                name = call.func.id
                helper = functions.get(name)
                if not helper or name in seen:
                    continue
                if not helper["has_params"]:
                    # 只用来解释"参数缺省时取什么"（``if raw is None: return X``）。
                    merge_none_guard_defaults(hits, call, helper["node"], path_label, constant_values)
                    continue
                seen.append(name)
                merge_hits(hits, collect_param_hits(helper["node"], {"params"}, via=name,
                                                    path=path_label, constants=constants,
                                                    constant_values=constant_values))
                merge_none_guard_defaults(hits, call, helper["node"], path_label, constant_values)
                source += "\n" + helper["text"]
                next_frontier.append(helper["node"])
        frontier = next_frontier
    return source, seen


def none_guard_defaults(func: ast.FunctionDef, constant_values: dict | None = None) -> dict:
    """``if <参数> is None: return <字面量>`` → ``{参数名: 默认值文本}``。"""

    out: dict[str, str] = {}
    for node in ast.walk(func):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        test = node.test
        left = test.left
        comparators = test.comparators
        if not (isinstance(left, ast.Name) and len(comparators) == 1
                and isinstance(comparators[0], ast.Constant) and comparators[0].value is None):
            continue
        for statement in node.body:
            if isinstance(statement, ast.Return) and statement.value is not None:
                text, _keys = describe_default(statement.value, set(), {}, {}, constant_values=constant_values)
                if text:
                    out.setdefault(left.id, text)
    return out


def merge_none_guard_defaults(hits: dict, call: ast.Call, func: ast.FunctionDef, path_label: str,
                              constant_values: dict | None = None) -> None:
    """把被调用助手里的 ``is None`` 默认值，归到调用处 ``params.get('key')`` 的键上。"""

    guards = none_guard_defaults(func, constant_values)
    if not guards:
        return
    parameter_names = [arg.arg for arg in func.args.args]
    for index, argument in enumerate(call.args):
        if index >= len(parameter_names):
            break
        keys = param_get_key(argument, {"params"}) or []
        text = guards.get(parameter_names[index])
        if not keys or not text:
            continue
        for key in keys:
            entry = hits.setdefault(key, {"defaults": {}, "expr": False, "bare": False,
                                          "via": set(), "paths": set(), "by_path": {}})
            entry["defaults"][text] = True
            entry["by_path"].setdefault(path_label, set()).add(text)


def runtime_branch_index(path: pathlib.Path, function: str, objects, *, path_label: str,
                         constants=None, functions=None, constant_values=None) -> dict:
    """把函数体里 ``if op == …`` 分支的参数键按 op 归位。"""

    text = read_text(path)
    lines = text.splitlines()
    tree = ast.parse(text)
    constants = constants or {}
    functions = functions or {}
    result: dict[str, dict] = {}
    for fn in function_defs(tree, function):
        for stmt in fn.body:
            if not isinstance(stmt, ast.If):
                continue
            ops = ops_of_test(stmt.test)
            if not ops:
                continue
            body = "\n".join(lines[stmt.lineno - 1: stmt.end_lineno])
            hits = collect_param_hits(stmt, objects, path=path_label, constants=constants,
                                      constant_values=constant_values)
            body, _helpers = follow_module_helpers(hits, body, stmt, functions, constants,
                                                   path_label=path_label, constant_values=constant_values)
            for op in ops:
                slot = result.setdefault(op, {"hits": {}, "source": "", "line": stmt.lineno})
                merge_hits(slot["hits"], hits)
                slot["source"] = (slot["source"] + "\n" + body).strip()
                slot["line"] = min(slot["line"], stmt.lineno)
    return result


# ---------------------------------------------------------------------------
# 2. 引擎原子（``_atomic_*`` + 它们调用的共享助手）


def engine_method_index() -> dict:
    """``方法名 → {file, node, text, params_signature}``（只看带 ``params`` 形参的方法）。"""

    index: dict[str, dict] = {}
    for name in ENGINE_FILES:
        path = ROOT / name
        if not path.is_file():
            continue
        text = read_text(path)
        lines = text.splitlines()
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            args = [a.arg for a in node.args.args]
            index.setdefault(node.name, {
                "file": name,
                "node": node,
                "text": "\n".join(lines[node.lineno - 1: node.end_lineno]),
                "line": node.lineno,
                "has_params": "params" in args,
            })
    return index


def runtime_function_index(path: pathlib.Path) -> dict:
    """``mod_runtime_v2`` 的模块级函数（``listener_body_from_params`` 这类助手）。"""

    text = read_text(path)
    lines = text.splitlines()
    tree = ast.parse(text)
    index: dict[str, dict] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        args = [a.arg for a in node.args.args]
        index[node.name] = {
            "node": node,
            "text": "\n".join(lines[node.lineno - 1: node.end_lineno]),
            "has_params": "params" in args,
        }
    return index


def engine_atom_index(methods: dict, *, constants=None, runtime_functions=None,
                      constant_values=None) -> dict:
    """``op → {file, line, hits, source, helpers}``，跟随 ``self._helper(...)`` 收集共享参数。"""

    constants = constants or {}
    runtime_functions = runtime_functions or {}
    result: dict[str, dict] = {}
    for name, info in methods.items():
        if not name.startswith("_atomic_"):
            continue
        op = name[len("_atomic_"):]
        hits = collect_param_hits(info["node"], {"params"}, path="engine", constants=constants,
                                  constant_values=constant_values)
        source = info["text"]
        helpers: list[str] = []
        seen = {name}
        frontier = [info]
        depth = 0
        while frontier and depth < 2:
            depth += 1
            next_frontier = []
            for current in frontier:
                for call in [n for n in ast.walk(current["node"]) if isinstance(n, ast.Call)]:
                    func = call.func
                    if not isinstance(func, ast.Attribute) or not isinstance(func.value, ast.Name):
                        continue
                    if func.value.id != "self":
                        continue
                    helper = func.attr
                    if helper in seen:
                        continue
                    target = methods.get(helper)
                    if not target or not target["has_params"] or helper.startswith("_atomic_"):
                        continue
                    seen.add(helper)
                    helpers.append(helper)
                    merge_hits(hits, collect_param_hits(target["node"], {"params"}, via=helper, path="engine",
                                                        constants=constants,
                                                        constant_values=constant_values))
                    source += "\n" + target["text"]
                    next_frontier.append(target)
            frontier = next_frontier
        # 引擎原子也会调用 mod_runtime_v2 的模块级助手（循环体 / 监听体解析等）。
        source, module_helpers = follow_module_helpers(
            hits, source, info["node"], runtime_functions, constants, path_label="engine",
            constant_values=constant_values,
        )
        helpers.extend(module_helpers)
        result[op] = {
            "file": info["file"],
            "line": info["line"],
            "hits": hits,
            "source": source,
            "helpers": helpers,
        }
    return result


def engine_alias_map() -> dict:
    """``game_engine._EFFECT_ALIASES``（非恒等项）。"""

    text = read_text(ROOT / "game_engine.py")
    tree = ast.parse(text)
    mapping: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "_EFFECT_ALIASES" and isinstance(node.value, ast.Dict):
                for key, value in zip(node.value.keys, node.value.values):
                    if isinstance(key, ast.Constant) and isinstance(value, ast.Constant) and key.value != value.value:
                        mapping[key.value] = value.value
    return mapping


# ---------------------------------------------------------------------------
# 3. 清单文档：分类与语义


HEADING_RE = re.compile(r"^(#{2,3})\s+(\d+(?:\.\d+)?)\.?\s+(.*)$")
CODE_SPAN_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")


def split_row(line: str) -> list[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", text)]


def is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", cell.replace(" ", "")) for cell in cells if cell != "")


def op_names_in(cell: str) -> list[str]:
    """取单元格里反引号包着的 op 名；``~~删除线~~`` 里的跳过。"""

    cleaned = re.sub(r"~~.*?~~", "", cell)
    names = []
    for name in CODE_SPAN_RE.findall(cleaned):
        if name not in names:
            names.append(name)
    return names


def clip_text(text: str, limit: int) -> str:
    """按句号/分号截断到 ``limit`` 字以内，尽量不留半句话。"""

    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    window = text[:limit]
    for mark in ("。", "；", "，", "、", " "):
        position = window.rfind(mark)
        if position >= limit // 2:
            return window[:position].rstrip() + "…"
    return window.rstrip() + "…"


def doc_param_defaults(cell: str) -> dict:
    """§6 参数列里 ``\\`amount\\`(6)`` / ``\\`stack_name\\`(默认 \\`X\\`)`` 形态的默认值。"""

    found = {}
    for name, raw in re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`\s*[（(]([^（()）]{1,24})[）)]", cell):
        value = raw.strip()
        explicit = value.startswith("默认")
        if explicit:
            value = value[len("默认"):].strip()
        if explicit:
            pass
        elif not re.fullmatch(r"-?\d+(\.\d+)?|True|False|None", value):
            continue
        value = value.strip().strip("`").strip()
        if value:
            found.setdefault(name, value)
    return found


def parse_runtime_sections(lines: list[str]) -> dict:
    """解析 §5.x 小节：``- 参数：`` / ``- 语义：`` / ``- 用例：`` 与参数默认值表。"""

    result: dict[str, dict] = {}
    current: dict | None = None

    def flush() -> None:
        if not current:
            return
        for op in current["ops"]:
            entry = result.setdefault(op, {"params": [], "defaults": {}})
            own = current.get("op_semantics", {}).get(op)
            if not entry.get("semantics") and (own or current.get("semantics")):
                entry["semantics"] = clip_text(own or current["semantics"], 240)
            if current.get("usage") and not entry.get("usage"):
                entry["usage"] = current["usage"]
            if current.get("params") and not entry.get("params"):
                entry["params"] = list(current["params"])
            for key, value in current.get("defaults", {}).items():
                entry["defaults"].setdefault(key, value)
            entry["section"] = f"§{current['no']}"

    for line in lines:
        heading = HEADING_RE.match(line)
        if heading:
            flush()
            current = None
            if heading.group(2).startswith("5."):
                current = {
                    "no": heading.group(2),
                    "ops": CODE_SPAN_RE.findall(heading.group(3)),
                    "params": [],
                    "defaults": {},
                    "semantics": "",
                    "op_semantics": {},
                    "usage": "",
                }
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.startswith("- 语义："):
            current["semantics"] = stripped[len("- 语义："):].strip()
        elif stripped.startswith("- 用例："):
            current["usage"] = stripped[len("- 用例："):].strip()
        elif stripped.startswith("- 参数："):
            current["params"].extend(op_names_in(stripped))
        elif stripped.startswith("- ") and CODE_SPAN_RE.match(stripped[2:].strip()):
            first = CODE_SPAN_RE.match(stripped[2:].strip())
            if first and first.group(1) in current["ops"]:
                current["op_semantics"].setdefault(first.group(1), stripped[2:].strip())
        elif stripped.startswith("|"):
            cells = split_row(stripped)
            if len(cells) < 2 or is_separator(cells):
                continue
            names = op_names_in(cells[0])
            if names and re.fullmatch(r"(`[^`]+`)(\s*/\s*`[^`]+`)*", cells[0].strip()):
                for name in names:
                    current["defaults"].setdefault(name, cells[1])
    flush()
    return result


def parse_doc_index(path: pathlib.Path) -> dict:
    """从清单文档抽出 ``op → {category, semantics, doc_params, doc_example, doc_usage, section}``。"""

    lines = read_text(path).splitlines()
    index: dict[str, dict] = {}
    section = ""
    section_title = ""
    runtime_sections = parse_runtime_sections(lines)
    for number, line in enumerate(lines, 1):
        heading = HEADING_RE.match(line)
        if heading:
            section = heading.group(2)
            section_title = heading.group(3).strip()
            continue
        if not line.startswith("|"):
            continue
        cells = split_row(line)
        if len(cells) < 2 or is_separator(cells):
            continue
        names = op_names_in(cells[0])
        if not names:
            continue
        if section.startswith("6.") and len(cells) < 3:
            continue
        if section.startswith("6."):
            category = f"{section} {section_title}"
            for name in names:
                entry = index.setdefault(name, {})
                rank = 3 if names == [name] else (2 if name == names[0] else 1)
                if rank > entry.get("rank", 0):
                    # 这个 op 是这一行的主角：用它覆盖"只是被顺带提到"的旧记录。
                    defaults = doc_param_defaults(cells[1])
                    entry.update({
                        "category": category,
                        "semantics": cells[2],
                        "doc_params": op_names_in(cells[1]),
                        "section": f"§{section}",
                        "rank": rank,
                    })
                    if defaults:
                        entry["doc_defaults"] = defaults
                    if len(cells) > 3:
                        entry["doc_example"] = cells[3]
                    if len(cells) > 4:
                        entry["doc_usage"] = cells[4]
                    continue
                entry.setdefault("category", category)
                entry.setdefault("semantics", cells[2])
                entry.setdefault("doc_params", op_names_in(cells[1]))
                for key, value in doc_param_defaults(cells[1]).items():
                    entry.setdefault("doc_defaults", {}).setdefault(key, value)
                if len(cells) > 3:
                    entry.setdefault("doc_example", cells[3])
                if len(cells) > 4:
                    entry.setdefault("doc_usage", cells[4])
                entry.setdefault("section", f"§{section}")
        elif section in ("3", "4"):
            category = "3 值表达式（`eval_v2_value`）" if section == "3" else "4 条件（`check_v2_condition`）"
            for name in names:
                entry = index.setdefault(name, {})
                rank = 2 if name == names[0] else 1
                if rank > entry.get("rank", 0):
                    entry.update({
                        "category": category,
                        "semantics": cells[2],
                        "doc_params": op_names_in(cells[1]),
                        "section": f"§{section}",
                        "rank": rank,
                    })
                    continue
                entry.setdefault("category", category)
                entry.setdefault("semantics", cells[2])
                entry.setdefault("doc_params", op_names_in(cells[1]))
                entry.setdefault("section", f"§{section}")
        elif section == "1":
            for name in names:
                entry = index.setdefault(name, {})
                entry.setdefault("category", "1 事件时点")
                entry.setdefault("semantics", cells[1])
                entry.setdefault("doc_usage", cells[2] if len(cells) > 2 else "")
                entry.setdefault("section", "§1")
        elif section == "1.1":
            for name in names:
                entry = index.setdefault(name, {})
                entry.setdefault("category", "1.1 被动声明块")
                entry.setdefault("semantics", cells[3] if len(cells) > 3 else "")
                entry.setdefault("doc_params", op_names_in(cells[2]) if len(cells) > 2 else [])
                entry.setdefault("section", "§1.1")
        elif section.startswith("7"):
            targets = op_names_in(cells[1]) if len(cells) > 1 else []
            for name in names + [item for item in targets if item not in names]:
                entry = index.setdefault(name, {})
                entry.setdefault("category", "7 兼容别名")
                entry.setdefault("section", f"§{section}")
                if targets:
                    prefix = "兼容别名：" if name in names else "别名目标（实现名）："
                    entry.setdefault(
                        "semantics",
                        prefix + "、".join(f"`{item}`" for item in names)
                        + " → " + "、".join(f"`{item}`" for item in targets),
                    )

    # §5.x 小节标题里的运行时原生 op
    for line in lines:
        heading = HEADING_RE.match(line)
        if not heading or not heading.group(2).startswith("5."):
            continue
        for name in CODE_SPAN_RE.findall(heading.group(3)):
            entry = index.setdefault(name, {})
            entry.setdefault("category", "5 v2 运行时原生 op")
            entry.setdefault("section", f"§{heading.group(2)}")
    for name, info in runtime_sections.items():
        entry = index.setdefault(name, {})
        entry.setdefault("category", "5 v2 运行时原生 op")
        entry.setdefault("section", info.get("section", ""))
        if info.get("semantics"):
            entry.setdefault("semantics", info["semantics"])
        if info.get("usage"):
            entry.setdefault("doc_usage", info["usage"])
        if info.get("params"):
            entry.setdefault("doc_params", info["params"])
        if info.get("defaults"):
            entry.setdefault("doc_defaults", {}).update(info["defaults"])

    # 其余：按"文档里第一次以代码片段提到它的位置"给一个参考段落
    seen_line: dict[str, int] = {}
    for number, line in enumerate(lines, 1):
        for name in CODE_SPAN_RE.findall(line):
            seen_line.setdefault(name, number)
    for name, number in seen_line.items():
        entry = index.setdefault(name, {})
        if "section" not in entry:
            section = "（散见）"
            for back in reversed(lines[:number]):
                heading = HEADING_RE.match(back)
                if heading:
                    section = f"§{heading.group(2)}"
                    break
            entry["section"] = section
            if section.startswith("§8"):
                entry.setdefault("category", "8 历史兼容旧名（无实现，见 §8.2/§8.3）")
            else:
                entry.setdefault("category", "9 其它（清单文档散见，需人工）")
            entry.setdefault("semantics", lines[number - 1].strip().replace("|", "\\|")[:160])
    return index


# ---------------------------------------------------------------------------
# 4. 卡数据：使用次数与真实用例


def compact_step(step, max_len: int = 132) -> str:
    """把一步渲染成一段"最小 JSON 片段"：嵌套步骤列表缩成 ``[...N 步...]``。"""

    def trim(node):
        if isinstance(node, dict):
            out = {}
            for key, value in node.items():
                if key in STEP_LIST_KEYS and isinstance(value, list) and any(isinstance(i, dict) for i in value):
                    out[key] = f"[…{len(value)} 步…]"
                elif key in ("condition", "cond", "unless", "run_if") and isinstance(value, dict):
                    out[key] = "{…}"
                else:
                    out[key] = trim(value)
            return out
        if isinstance(node, list):
            return [trim(item) for item in node]
        return node

    text = json.dumps(trim(step), ensure_ascii=False, separators=(",", ":"))
    text = text.replace("|", "\\|")
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    return text


def step_weight(step) -> int:
    try:
        return len(compact_step(step, max_len=100000))
    except Exception:  # noqa: BLE001
        return 10 ** 6


def scan_usage(mods_dir: pathlib.Path) -> dict:
    """``op → {steps, cards(set), first(package, card_id, snippet)}``。"""

    usage: dict[str, dict] = {}
    for path in sorted(mods_dir.glob("*.gtnmod")):
        try:
            with zipfile.ZipFile(path) as archive:
                payload = json.loads(archive.read("mod.json"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(payload, dict):
            continue
        for _registry, resource in mod_atom_report.iter_registry_resources(payload):
            lists: list = []
            mod_atom_report.root_step_lists(resource, lists)
            if not lists:
                continue
            card_id = str(resource.get("id") or "")
            local: dict[str, list] = {}

            def visit(step, op, _local=local):
                if op:
                    _local.setdefault(op, []).append(step)

            for steps in lists:
                mod_atom_report.walk_steps(steps, visit)
            for op, steps in local.items():
                entry = usage.setdefault(op, {"steps": 0, "cards": set(), "first": None})
                entry["steps"] += len(steps)
                entry["cards"].add((path.name, card_id))
                if entry["first"] is None:
                    best = min(steps, key=step_weight)
                    entry["first"] = (path.name, card_id, compact_step(best))
    return usage


# ---------------------------------------------------------------------------
# 5. 组装


def build(model: dict | None = None) -> dict:
    universe = sorted(mod_spec_v2.VALID_LOGIC_OPS)
    engine_ops = set(atomic_registry.engine_atomic_ops())
    engine_aliases = engine_alias_map()
    advanced = set(mod_runtime_v2.ADVANCED_ATOMIC_OPS)
    runtime_path = ROOT / "mod_runtime_v2.py"
    source_paths = [runtime_path, ROOT / "cards.py"] + [ROOT / name for name in ENGINE_FILES]
    constants = module_constants(source_paths)
    constant_values = module_literal_constants(source_paths)
    runtime_functions = runtime_function_index(runtime_path)
    runtime_step = runtime_branch_index(runtime_path, "run_v2_step", {"params", "step"},
                                        path_label="runtime", constants=constants,
                                        functions=runtime_functions, constant_values=constant_values)
    runtime_expr = runtime_branch_index(runtime_path, "eval_v2_value", {"expr"},
                                        path_label="expr", constants=constants,
                                        functions=runtime_functions, constant_values=constant_values)
    runtime_cond = runtime_branch_index(runtime_path, "check_v2_condition", {"cond"},
                                        path_label="cond", constants=constants,
                                        functions=runtime_functions, constant_values=constant_values)
    methods = engine_method_index()
    engine_atoms = engine_atom_index(methods, constants=constants,
                                     runtime_functions=runtime_functions,
                                     constant_values=constant_values)
    doc = parse_doc_index(DOC_LIST)
    usage = scan_usage(MODS_DIR)

    summary = mod_atom_report.build_summary(mod_atom_report.collect(MODS_DIR))

    if model is not None:
        model.clear()
        model.update({
            "universe": universe,
            "engine_ops": engine_ops,
            "engine_aliases": engine_aliases,
            "advanced": advanced,
            "runtime_step": runtime_step,
            "runtime_expr": runtime_expr,
            "runtime_cond": runtime_cond,
            "engine_atoms": engine_atoms,
            "doc": doc,
            "usage": usage,
            "summary": summary,
        })
        return model

    return {
        "universe": universe,
        "engine_ops": engine_ops,
        "engine_aliases": engine_aliases,
        "advanced": advanced,
        "runtime_step": runtime_step,
        "runtime_expr": runtime_expr,
        "runtime_cond": runtime_cond,
        "engine_atoms": engine_atoms,
        "doc": doc,
        "usage": usage,
        "summary": summary,
    }


def op_paths(model: dict, op: str) -> dict:
    """一个 op 的执行路径：运行时原生 / 引擎原子 / 别名 / 表达式 / 条件 / 时点。"""

    engine_ops = model["engine_ops"]
    runtime_alias = mod_runtime_v2.ATOMIC_OP_ALIASES.get(op)
    engine_alias = model["engine_aliases"].get(op)
    resolved_runtime = runtime_alias or op
    resolved_engine = engine_alias or resolved_runtime
    paths = {
        "runtime": op in model["runtime_step"],
        "engine": op in engine_ops or resolved_engine in engine_ops,
        "expr": op in model["runtime_expr"],
        "cond": op in model["runtime_cond"],
        "alias": None,
        "hook": bool(model["doc"].get(op, {}).get("category", "").startswith(("1 ", "1.1"))),
    }
    if runtime_alias and runtime_alias != op:
        paths["alias"] = (runtime_alias, "ATOMIC_OP_ALIASES")
    elif engine_alias and engine_alias != op:
        paths["alias"] = (engine_alias, "_EFFECT_ALIASES")
    paths["dispatchable"] = bool(
        paths["runtime"]
        or resolved_engine in engine_ops
        or resolved_runtime in model["advanced"]
        or resolved_engine in model["advanced"]
        or paths["expr"]
        or paths["cond"]
        or paths["hook"]
    )
    return paths


def op_params(model: dict, op: str) -> dict:
    """合并两条执行路径的参数读取记录。"""

    merged: dict[str, dict] = {}
    for source in (model["runtime_step"], model["runtime_expr"], model["runtime_cond"]):
        entry = source.get(op)
        if entry:
            merge_hits(merged, entry["hits"])
    names = [op]
    runtime_alias = mod_runtime_v2.ATOMIC_OP_ALIASES.get(op)
    engine_alias = model["engine_aliases"].get(op)
    for alias in (runtime_alias, engine_alias):
        if alias and alias not in names:
            names.append(alias)
    for name in names:
        atom = model["engine_atoms"].get(name)
        if atom:
            merge_hits(merged, atom["hits"])
    return merged


DYNAMIC_MARKS = ("（表达式）", "（无默认值）")


def default_text(entry: dict, doc_default: str = "") -> str:
    """一个参数的默认值展示：源码字面量 → 文档口径 → 无/动态。"""

    by_path = {path: {value for value in values if value not in DYNAMIC_MARKS}
               for path, values in (entry.get("by_path") or {}).items()}
    by_path = {path: values for path, values in by_path.items() if values}
    if len({tuple(sorted(values)) for values in by_path.values()}) > 1:
        parts = []
        for path in sorted(by_path, key=lambda name: (name != "runtime", name)):
            parts.append(f"{ALIAS_LABELS.get(path, path)} {' / '.join(sorted(by_path[path]))}")
        return "，".join(parts) + " ⚠ 默认值不一致"
    concrete = sorted({value for values in by_path.values() for value in values}
                      or {value for value in entry.get("defaults", {}) if value not in DYNAMIC_MARKS})
    if concrete:
        return (" / ".join(concrete) + (" ⚠" if len(concrete) > 1 else ""))
    doc_default = str(doc_default or "").strip().strip("`").strip()
    if doc_default in ("—", "-", "无", "None"):
        doc_default = ""
    if doc_default:
        return f"`{doc_default}`（清单文档口径，源码里是动态值）"
    if entry.get("bare") or "（无默认值）" in entry.get("defaults", {}):
        return "无（不写就是空）"
    if "（表达式）" in entry.get("defaults", {}):
        return "由代码/局部变量决定"
    return "—"


def render_params(cell: dict, doc_defaults: dict | None = None) -> str:
    if not cell:
        return "—"
    doc_defaults = doc_defaults or {}
    parts = []
    for name in sorted(cell):
        entry = cell[name]
        bits = [f"默认 {default_text(entry, doc_defaults.get(name, ''))}"]
        if entry.get("expr"):
            bits.append("可写表达式")
        parts.append(f"`{name}`（{'，'.join(bits)}）")
    return "；".join(parts)


def render_doc_only_params(entry: dict) -> str:
    """源码里没抽到读取点时，退回清单文档的参数列（明确标注，不当成源码事实）。"""

    names = entry.get("doc_params") or []
    if not names:
        return "—"
    section = entry.get("section") or "清单文档"
    listed = "、".join(f"`{name}`" for name in names[:12])
    if len(names) > 12:
        listed += "…"
    return f"源码未抽到参数读取点；{section} 参数列记为 {listed}"


def render_extensions(model: dict, op: str, params: dict, paths: dict) -> str:
    flags = []
    expr_params = sorted(name for name, entry in params.items() if entry.get("expr"))
    if expr_params:
        flags.append("表达式：" + "/".join(f"`{name}`" for name in expr_params[:4]))
    source = ""
    atom = model["engine_atoms"].get(op)
    runtime = model["runtime_step"].get(op)
    if atom:
        source += atom["source"]
    if runtime:
        source += runtime["source"]
    if re.search(r"_resolve_targets\(|_resolve_step_targets\(|_as_player_list\(|_list_effect_targets\(|"
                 r"_wide_strike_target_ids\(|resolve_v2_target\(", source):
        flags.append("多目标（选择器按集合解析）")
    if re.search(r"params\.get\('(body|steps|effects)'|_run_effect_list\(|run_v2_steps\(|"
                 r"listener_body_from_params\(|loop_body_from_params\(", source):
        flags.append("`body` 子步骤")
    hooks = [key for key in ("on_hit", "on_hit_once", "on_crit") if key in params]
    if hooks:
        flags.append("回调：" + "/".join(f"`{key}`" for key in hooks))
    if re.search(r"step_is_silent\(|log is False|params\.get\('silent'|params\.get\('no_log'|_render_step_log\(", source):
        flags.append("`log`/`silent` 开关")
    if op not in mod_runtime_v2.CONDITION_OWNED_OPS and (paths["runtime"] or paths["engine"]):
        flags.append("`condition`/`unless` 门控")
    elif op in mod_runtime_v2.CONDITION_OWNED_OPS:
        flags.append("门控用 `run_if`/`unless`")
    helpers = []
    atom = model["engine_atoms"].get(op)
    if atom:
        helpers = atom.get("helpers") or []
    if helpers:
        flags.append("共享实现 " + "、".join(f"`{name}`" for name in helpers[:3]))
    return "、".join(flags) if flags else "—"


def op_usage_cell(usage: dict, op: str, doc_entry: dict) -> tuple[str, str]:
    entry = usage.get(op)
    if not entry:
        stale = (doc_entry.get("doc_usage") or "").strip()
        case = "—（未在现卡数据中使用）"
        if stale and not any(token in stale for token in
                             ("未在现卡数据中使用", "未使用", "未在当期卡数据", "未用")):
            case += f"；清单文档记为 {stale.rstrip('。')}"
        return "0 张 / 0 步", case
    packages = sorted({package for package, _card in entry["cards"]})
    count = f"{len(entry['cards'])} 张 / {entry['steps']} 步"
    first = entry["first"]
    case = f"`{first[1]}`（{first[0]}）<br>`{first[2]}`"
    if len(packages) > 1:
        case += f"<br>共 {len(packages)} 个包"
    return count, case


def op_badges(model: dict, op: str, paths: dict) -> str:
    if paths["alias"]:
        return f"别名→`{paths['alias'][0]}`"
    badges = []
    if paths["runtime"]:
        badges.append("运行时")
    if paths["engine"]:
        badges.append("引擎")
    if paths["expr"]:
        badges.append("表达式")
    if paths["cond"]:
        badges.append("条件")
    if paths["hook"]:
        badges.append("时点")
    if not badges:
        resolved = model["engine_aliases"].get(op, op)
        if resolved in model["engine_ops"]:
            badges.append("引擎")
    if not badges:
        badges.append("⚠无实现")
    return "＋".join(badges)


def unresolved_reasons(model: dict, op: str, params: dict, paths: dict) -> list[str]:
    reasons = []
    doc = model["doc"].get(op, {})
    if not doc.get("semantics"):
        reasons.append("清单文档里没有结构化语义")
    if not params and (paths["runtime"] or paths["engine"]):
        reasons.append("源码里没抽到任何参数键（可能是无参数原子，需人工确认）")
    if not paths["dispatchable"]:
        reasons.append("白名单里有、引擎/运行时都没有实现（写了会报 unsupported v2 op）")
    return reasons


def default_conflicts(model: dict, op: str) -> list[str]:
    merged = op_params(model, op)
    out = []
    for key, entry in sorted(merged.items()):
        defaults = sorted(entry.get("defaults", {}))
        if len(defaults) > 1:
            out.append(f"`{key}`：{'、'.join(defaults)}")
    return out


def normalize_default(text: str) -> str:
    text = str(text or "").strip()
    text = text.strip("`").strip()
    return "" if text in ("—", "-", "无", "None", "未定") else text


def doc_default_conflicts(model: dict, op: str, params: dict) -> list[str]:
    """文档 §5.x 参数表里写的默认值 vs 源码抽出来的默认值。"""

    documented = (model["doc"].get(op, {}) or {}).get("doc_defaults") or {}
    out = []
    for key, doc_value in sorted(documented.items()):
        entry = params.get(key)
        if not entry:
            continue
        values = [normalize_default(value) for value in sorted(entry.get("defaults") or ())]
        values = [value for value in values if value]
        want = normalize_default(doc_value)
        if want and values and want not in values:
            out.append(f"`{key}`：文档 `{doc_value}` / 源码 {'、'.join(values)}")
    return out


def category_sort_key(category: str) -> tuple:
    match = re.match(r"(\d+)(?:\.(\d+))?", category)
    if not match:
        return (99, 99, category)
    return (int(match.group(1)), int(match.group(2) or 0), category)


# Round 21 抽样校对：逐条对过源码，结论写进报告 ``.codex-tmp/round21/rd21.md``。
# 参数不在 ``_atomic_*`` / 运行时分支里读的 op（人工核对过，附录 F）。
OUT_OF_ATOM_PARAMS = (
    ("request_target",
     "`allowed`（`any`/`self`/`enemy`/`friendly`…，默认 `any`）、`alive_only`",
     "`game_engine._pick_auto_target` 读 `_get_choice_request` 返回的这一步（`game_engine.py` 第 19385 行附近）"),
    ("request_card",
     "`filter` 全套：`zone`/`owner`/`card_type`/`require_selectable`/`exclude_self`/`affordable`/`pay_ratio`/`min_count`…",
     "`game_engine._choice_request_satisfied` 与选牌 UI 组装（`game_engine.py` 第 7396 行起）"),
)
SAMPLE_SPOT_CHECKS = (
    ("request_target", "无参数；只写 `context['target_player']`", "一致"),
    ("deal_damage", "运行时 `amount` 默认 0 / 引擎默认 6，`target` 默认 `target` / `enemy`", "本表标 ⚠，见附录 C"),
    ("direct_damage", "`source_text` 三级回落（`source_text`→`source_name`→`label`）", "一致"),
    ("status_add_named", "`status`/`statuses`/`amount`/`stack`/`target`（共享 `_apply_status_add_family`）", "一致"),
    ("heal", "`amount` 默认 0、`target` 默认 `self`（引擎）/`source`（运行时）、`log`/`log_positive_only`", "一致"),
    ("draw_cards", "`amount` 回落 `count`（默认 1）、`target` 默认 `self`/`source`", "一致"),
    ("for_each", "`source/items/targets/list/collection/values`、`as/var/name`、`limit` 默认 200", "一致"),
    ("timed_effect", "`trigger`/`duration`/`effects`/`body`（运行时 `effects`→`body` 双向兼容）", "一致"),
    ("auto_play_card", "`card`/`target`/`auto_choice`/`no_cost`/`source_name`", "一致"),
    ("move_cards_to_deck", "`cards`/`zone`/`position`/`target`（共享移动助手）", "一致"),
    ("place_as_equip", "`card`/`owner`/`effect_target`，71 处使用（签名冻结）", "一致"),
    ("request_card", "整套 `filter`（zone/owner/card_type/…）同时驱动候选集、提交校验与 `play_requires`", "一致"),
    ("var_set", "`target`/`name`/`value`（引擎版 `name` 回落 `var`）", "一致"),
    ("log", "`message` 回落 `text`/`msg`，`amount` 可写表达式", "一致"),
    ("gain_e", "`amount`/`target`/`log_positive_only`", "一致"),
    ("register_play_listener", "`scope`/`duration`/`body`/`exclude_card_ids`", "一致"),
    ("queue_auto_play", "`card`/`source`/`target`/`each_turn`/`cost`/`exile` 等 12 个键", "一致"),
    ("absorb_attack_damage", "`scope`/`body`/`once`（body 里读 `absorbed_damage`）", "一致"),
    ("settle_status", "`status`/`decay`/`fill_from`/`body`/`silent`", "一致"),
    ("untargetable_layers", "`target`/`amount`（唯一带成就与默认文案的层数原子）", "一致"),
)


def render(model: dict) -> str:
    summary = model["summary"]
    universe = model["universe"]
    usage = model["usage"]
    doc = model["doc"]

    rows_by_category: dict[str, list[tuple[int, str]]] = collections.defaultdict(list)
    rows_by_group: dict[str, list[tuple[tuple, int, str]]] = collections.defaultdict(list)
    param_total = 0
    unresolved: dict[str, list[str]] = {}
    doc_mismatch: list[tuple[str, list[str], list[str]]] = []
    doc_default_mismatch: list[tuple[str, list[str]]] = []
    conflicts: list[tuple[str, list[str]]] = []
    for op in universe:
        paths = op_paths(model, op)
        params = op_params(model, op)
        param_total += len(params)
        category = doc.get(op, {}).get("category") or "9 其它（清单文档散见，需人工）"
        steps = usage.get(op, {}).get("steps", 0)
        rows_by_category[category].append((-steps, op))
        rows_by_group[op_group_label(op)].append((category_sort_key(category), -steps, op))
        reasons = unresolved_reasons(model, op, params, paths)
        if reasons:
            unresolved[op] = reasons
        if doc.get(op, {}).get("doc_params"):
            doc_only = sorted(set(doc[op]["doc_params"]) - set(params))
            src_only = sorted(set(params) - set(doc[op]["doc_params"]))
            if doc_only or src_only:
                doc_mismatch.append((op, doc_only, src_only))
        conflict = default_conflicts(model, op)
        if conflict:
            conflicts.append((op, conflict))
        doc_conflict = doc_default_conflicts(model, op, params)
        if doc_conflict:
            doc_default_mismatch.append((op, doc_conflict))

    lines: list[str] = []
    lines.append("# 原子参数表（GTN Mod Spec v2）")
    lines.append("")
    lines.append("> 由 `python tools/atom_parameter_table.py` 生成，**不要手改**（改生成器再重跑）。")
    lines.append("> 数据来源：当前工作区源码 + `mods/*.gtnmod` 根 `mod.json` + "
                 "`docs/引擎原子与数据步骤清单.md`（分类与语义取自该清单，本表不重写语义）。")
    lines.append("> 统计口径与 `python tools/mod_atom_report.py` 相同：同一个步骤遍历器、同一份 `_CORE_LOGIC_OPS`。")
    lines.append("")
    lines.append("## 0. 总数")
    lines.append("")
    lines.append("| 指标 | 数值 | 口径 |")
    lines.append("|---|---|---|")
    lines.append(f"| 策展通用清单 `_CORE_LOGIC_OPS` | {summary['core_ops']} | `mod_spec_v2` |")
    lines.append(f"| 运行时白名单 `VALID_LOGIC_OPS` | {summary['valid_ops']} | 清单 ∪ `_atomic_*` |")
    lines.append(f"| `_atomic_*` 实现 | {summary['engine_ops']} | `atomic_registry.engine_atomic_ops()` |")
    lines.append(f"| 未登记原子 / 悬空 op / 旧写法步骤 | "
                 f"{summary['unregistered_atoms']} / {len(summary['dangling'])} / {summary['legacy_step_count']} | "
                 f"`tools/mod_atom_report.py` 同口径 |")
    lines.append(f"| 含逻辑的卡资源 / 步骤总数 | {summary['cards_total']} / {summary['steps_total']} | 20 个官方包根 `mod.json` |")
    lines.append(f"| 步骤里出现的 op 种类 | {summary['distinct_ops_used']} | 同上 |")
    lines.append(f"| **本表覆盖的原子 / op** | **{len(universe)}** | 每个原子一行 |")
    lines.append(f"| **本表抽到的参数条目** | **{param_total}** | 源码里读到的参数键去重后求和 |")
    lines.append(f"| 没有实现的登记名（写了会报错） | {len([op for op in universe if not op_paths(model, op)['dispatchable']])} | 见 §{len(group_labels())} 与附录 A |")
    lines.append("")
    lines.append("**Round 25：登记名按真实执行路径分五类**（`mod_spec_v2.LOGIC_OP_GROUPS`；")
    lines.append("`_CORE_LOGIC_OPS` 仍是五类的并集，所有可用名字一个都没变）：")
    lines.append("")
    lines.append("| 分类 | 数量 | 口径 |")
    lines.append("|---|---|---|")
    counts = group_counts()
    sources = {
        "真原子（引擎 `_atomic_*` 实现）": "`ENGINE_ATOM_OPS` = `atomic_registry.engine_atomic_ops()`",
        "运行时原生步骤（`run_v2_step`）": "`RUNTIME_STEP_OPS`，引擎没有同名 `_atomic_*`",
        "表达式算子（`eval_v2_value`）": "`EXPRESSION_OPS`，只能写在取值位置",
        "条件算子（`check_v2_condition`）": "`CONDITION_OPS`，只能写在门控位置",
        "事件与声明键（`events` / `_EFFECT_ALIASES`）": "`EVENT_HOOK_OPS`，事件时点与声明键",
        LEGACY_GROUP_LABEL: "`UNCLASSIFIED_LOGIC_OPS`，**应为 0**",
    }
    for label in group_labels():
        lines.append(f"| {label} | {counts.get(label, 0)} | {sources.get(label, '—')} |")
    lines.append(f"| **合计** | **{sum(counts.get(label, 0) for label in group_labels())}** | "
                 f"= `_CORE_LOGIC_OPS` {summary['core_ops']} |")
    lines.append("")
    lines.append("重新生成（只读源码与卡数据，不碰引擎、卡数据、编辑器）：")
    lines.append("")
    lines.append("```powershell")
    lines.append("python tools\\atom_parameter_table.py            # 写 docs/原子参数表.md")
    lines.append("python tools\\atom_parameter_table.py --check    # 只校验：数字与 mod_atom_report 对不上就非零退出")
    lines.append("```")
    lines.append("")
    lines.append("### 怎么读这张表")
    lines.append("")
    lines.append("- **分类**（§0 的表 + 正文五个小节）= 这个 op 的真实执行路径：")
    lines.append("  真原子走 `game_engine._atomic_*`；运行时原生步骤走 `mod_runtime_v2.run_v2_step`；")
    lines.append("  表达式 / 条件算子只出现在取值与门控位置；事件与声明键写在卡数据的 `events` 里。")
    lines.append("  分类口径由 `python .codex-tmp\\round25\\rd25_classify_final.py` 按真实分派代码复核。")
    lines.append("- **原子**列 = op 名 + 执行路径徽标：")
    lines.append("  `运行时` = `mod_runtime_v2.run_v2_step` 直接执行；`引擎` = `game_engine._atomic_*`；")
    lines.append("  `表达式` / `条件` = 只能出现在取值表达式 / 条件位置；`时点` = 卡数据 `events` 里的声明块键；")
    lines.append("  `别名→X` = 先被别名表改写成 X 再执行（`ATOMIC_OP_ALIASES` 或 `_EFFECT_ALIASES`）。")
    lines.append("  `⚠无实现` = 白名单里有登记、但引擎与运行时都没有实现，写进卡数据会报 `unsupported v2 op`。")
    lines.append("- **参数**列 = 实现里真正读的键（`params.get('k', 默认值)` / `expr.get('k')` / `params['k']`）：")
    lines.append("  `默认` 取源码里的默认值；`可写表达式` = 该参数被 `eval_v2_value` / `_eval_int` / `_step_text_value` 包着求值；")
    lines.append("  两条执行路径默认值不同时显示 `A / B ⚠`（全部清单见附录 C）；")
    lines.append("  `共享实现 _helper` = 参数是在共享助手里读的，两条路径同一份语义。")
    lines.append("- **语义**列抄自清单文档；抽不到结构化语义的原子标 `未验证：…`，不猜。")
    lines.append("- **真实用例** = 卡数据里首次出现该 op 的卡 id + 该卡里最短的一步 JSON 片段；")
    lines.append("  嵌套步骤列表缩成 `[…N 步…]`、条件缩成 `{…}`，只保留能说明用法的骨架。")
    lines.append("- **使用次数** = 多少张卡 / 多少步（步骤级扫描；只出现在表达式或条件里的 op 记 0）。")
    lines.append("- **扩展点** = 源码里能判定的扩展方式（表达式参数 / 多目标集合 / `body` 子步骤 / `on_hit` 回调 /")
    lines.append("  `log`·`silent` 开关 / 步骤门控）。判定不了的不写，宁缺毋滥。")
    lines.append("- 所有**非控制流**步骤都能加步骤门控 `condition`/`unless`（§14.1）；控制流 op 用 `run_if`/`unless`。")
    lines.append("")

    # Round 25：正文按"真原子 / 运行时步骤 / 表达式 / 条件 / 事件与声明键"分节，
    # 每节内部仍按清单文档的分类顺序排（语义列里的 §x 就是清单文档的章节）。
    for index, group in enumerate(group_labels(), 1):
        rows = sorted(rows_by_group.get(group, []))
        lines.append(f"## {index} {group} — {len(rows)} 个")
        lines.append("")
        if group == LEGACY_GROUP_LABEL and not rows:
            lines.append("（无：五类恰好铺满 `_CORE_LOGIC_OPS`，没有只登记不实现的名字）")
            lines.append("")
            continue
        lines.append("| 原子 | 参数（含默认值） | 语义 | 真实用例 | 使用次数 | 扩展点 |")
        lines.append("|---|---|---|---|---|---|")
        for _sort_key, _weight, op in rows:
            paths = op_paths(model, op)
            params = op_params(model, op)
            entry = doc.get(op, {})
            semantics = (entry.get("semantics") or "").replace("|", "\\|").strip() or "未验证：清单文档里没有结构化语义，需人工"
            if entry.get("section"):
                semantics = f"{semantics}（{entry['section']}）"
            count, case = op_usage_cell(usage, op, entry)
            params_cell = render_params(params, entry.get("doc_defaults"))
            if not params:
                params_cell = render_doc_only_params(entry)
            lines.append("| `{}`（{}） | {} | {} | {} | {} | {} |".format(
                op, op_badges(model, op, paths), params_cell, semantics, case, count,
                render_extensions(model, op, params, paths),
            ))
        lines.append("")

    lines.append("## 附录 A：未验证 / 需人工清单")
    lines.append("")
    lines.append("生成器只报「源码里读到的」和「文档里写了的」；下面这些是它判定不了、需要人工确认的：")
    lines.append("")
    groups: dict[str, list[str]] = collections.defaultdict(list)
    for op, reasons in sorted(unresolved.items()):
        for reason in reasons:
            groups[reason].append(op)
    for reason, names in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        lines.append(f"### {reason}（{len(names)} 个）")
        lines.append("")
        lines.append("、".join(f"`{name}`" for name in names))
        lines.append("")
    if not groups:
        lines.append("（无）")
        lines.append("")

    lines.append("## 附录 B：文档参数 ↔ 源码抽取的差异（需人工复核）")
    lines.append("")
    lines.append("以清单文档 §6 的「参数」列为文档口径，和本表从实现里抽到的键对比；")
    lines.append("两边不一致不一定是错（文档可能写的是别名键、或参数在更深一层的共享助手里），但值得人工过一眼。")
    lines.append("")
    if doc_mismatch:
        lines.append("| 原子 | 只在文档里 | 只在源码里 |")
        lines.append("|---|---|---|")
        for op, doc_only, src_only in doc_mismatch:
            lines.append("| `{}` | {} | {} |".format(
                op,
                "、".join(f"`{name}`" for name in doc_only) or "—",
                "、".join(f"`{name}`" for name in src_only) or "—",
            ))
    else:
        lines.append("（无差异）")
    lines.append("")
    lines.append("§5.x 参数表里写了默认值的 op，再和源码抽出来的默认值对一遍：")
    lines.append("")
    if doc_default_mismatch:
        lines.append("| 原子 | 参数：文档 / 源码 |")
        lines.append("|---|---|")
        for op, items in doc_default_mismatch:
            lines.append("| `{}` | {} |".format(op, "；".join(items)))
    else:
        lines.append("（无差异）")
    lines.append("")

    lines.append("## 附录 C：同名参数默认值不一致（两条执行路径）")
    lines.append("")
    lines.append("写卡时按「两条路径取交集」最安全；这一节列的是运行时分支与引擎原子对同一个键给了不同默认值的地方。")
    lines.append("")
    if conflicts:
        lines.append("| 原子 | 参数与默认值 |")
        lines.append("|---|---|")
        for op, items in conflicts:
            lines.append("| `{}` | {} |".format(op, "；".join(items)))
    else:
        lines.append("（无）")
    lines.append("")

    lines.append("## 附录 D：抽样校对（Round 21，逐条对过源码）")
    lines.append("")
    lines.append("| 原子 | 校对点 | 结论 |")
    lines.append("|---|---|---|")
    for op, point, verdict in SAMPLE_SPOT_CHECKS:
        lines.append(f"| `{op}` | {point} | {verdict} |")
    lines.append("")
    lines.append("## 附录 E：参数不在原子实现里读的 op（人工核对）")
    lines.append("")
    lines.append("这些 op 的参数由引擎的其它管线消费，生成本表时抽不到，单独登记：")
    lines.append("")
    lines.append("| op | 参数 | 读取位置 |")
    lines.append("|---|---|---|")
    for op, params_text, where in OUT_OF_ATOM_PARAMS:
        lines.append(f"| `{op}` | {params_text} | {where} |")
    lines.append("")

    lines.append("## 附录 F：怎么写新原子 / 新参数")
    lines.append("")
    lines.append("沿用清单文档 §12（把新机制数据化）与 §14（步骤级门控与通用参数）：")
    lines.append("")
    lines.append("1. **先定语义与参数**，再动代码：op 名、每个参数的默认值、战报行为、未知参数怎么处理；")
    lines.append("   能写成「数据步骤序列」的优先改数据，不要新增引擎原子（§12.1）。")
    lines.append("2. **两条路径同步实现**：`mod_runtime_v2.run_v2_step`（顶层步骤）与 `game_engine._atomic_<op>`")
    lines.append("   （嵌套 body / 定时器 / 旧写法走这条）；同名参数默认值必须一致，否则按 §5.4 改名或统一。")
    lines.append("3. **能挂现成挂点就别造新词**：`on_play` / `on_owner_turn_start` / `on_equipment_trigger` /")
    lines.append("   `on_damage_taken` / `on_response` / `timed_effect` / `register_play_listener`（§12.1 第 3 步）。")
    lines.append("4. **参数按通用约定写**：数值/文本参数直接吃取值表达式（§14.2 列出了已覆盖的 op 与参数键）；")
    lines.append("   步骤门控用 `condition`/`unless`（控制流 op 用 `run_if`/`unless`，§14.1）；")
    lines.append("   默认文案用 `log`，关掉用 `log: false` / `silent: true`（§14.3）。")
    lines.append("5. **别名只加不删、且单向**：旧名进 `ATOMIC_OP_ALIASES`（运行时）或 `_EFFECT_ALIASES`（引擎），")
    lines.append("   目标必须是真实实现；删除的名字进 `mod_spec_v2.REMOVED_ATOMIC_OPS` 并给显式报错（§5.4）。")
    lines.append("6. **登记与验收**：op 进 `mod_spec_v2._CORE_LOGIC_OPS`；跑")
    lines.append("   `python tools\\mod_atom_report.py --check --strict`、`python tools\\atom_parameter_table.py --check`、")
    lines.append("   `python tools\\op_long_tail_report.py`、`python .codex-tmp\\smoke_all_cards.py`，")
    lines.append("   并在 `.codex-tmp/roundNN/rdNN.md` 写报告（§8.3 的六步流程）。")
    lines.append("")

    lines.append("## 附录 G：兼容别名（旧名 → 规范名）")
    lines.append("")
    lines.append("旧名照写仍然可用：运行时 `ATOMIC_OP_ALIASES` 或引擎 `_EFFECT_ALIASES` 会先改写再执行。")
    lines.append("")
    lines.append("| 旧名 | 规范名 | 别名表 |")
    lines.append("|---|---|---|")
    alias_rows = [(alias, target, "ATOMIC_OP_ALIASES")
                  for alias, target in sorted(getattr(mod_runtime_v2, "ATOMIC_OP_ALIASES", {}).items())]
    alias_rows += [(alias, target, "_EFFECT_ALIASES")
                   for alias, target in sorted(model["engine_aliases"].items()) if target != alias]
    for alias, target, source in alias_rows:
        lines.append(f"| `{alias}` | `{target}` | `{source}` |")
    lines.append("")
    lines.append("已经撤销的旧名（Round 22 / Round 25 收敛，写出来报显式错误）：")
    lines.append("")
    lines.append("、".join(
        f"`{alias}` → `{target}`" for alias, target in sorted(mod_spec_v2.RENAMED_ATOMIC_OPS.items())
    ) or "（无）")
    lines.append("")
    return "\n".join(lines)


def check(model: dict, text: str, out_path: pathlib.Path) -> int:
    summary = model["summary"]
    problems = []
    recomputed = mod_atom_report.build_summary(mod_atom_report.collect(MODS_DIR))
    for key in ("core_ops", "valid_ops", "engine_ops", "unregistered_atoms", "cards_total", "steps_total",
                "distinct_ops_used", "legacy_step_count"):
        if summary[key] != recomputed[key]:
            problems.append(f"{key}: {summary[key]} != {recomputed[key]}")
    # Round 25：五类必须恰好铺满登记表（分类口径的直接校验）。
    core_ops = set(mod_spec_v2._CORE_LOGIC_OPS)
    covered = set()
    for label, names in mod_spec_v2.logic_op_groups(include_empty=False).items():
        overlap = covered & set(names)
        if overlap:
            problems.append(f"分类重叠（{label}）：{sorted(overlap)[:5]}")
        covered |= set(names)
    unclassified = sorted(core_ops - covered)
    if unclassified:
        problems.append(f"分类没铺满 _CORE_LOGIC_OPS，剩 {len(unclassified)} 个：{unclassified[:5]}")
    stray = sorted(covered - core_ops)
    if stray:
        problems.append(f"分类里有不在 _CORE_LOGIC_OPS 的名字：{stray[:5]}")
    if getattr(mod_spec_v2, "UNCLASSIFIED_LOGIC_OPS", None):
        problems.append(
            f"UNCLASSIFIED_LOGIC_OPS 非空：{sorted(mod_spec_v2.UNCLASSIFIED_LOGIC_OPS)[:5]}"
        )
    if len(summary["dangling"]):
        problems.append(f"悬空 op {len(summary['dangling'])} 个")
    if out_path.is_file():
        on_disk = read_text(out_path).replace("\r\n", "\n")
        if on_disk != text.replace("\r\n", "\n"):
            problems.append(f"{out_path.name} 与重新生成的内容不一致（跑一次不带 --check 的命令即可刷新）")
    for problem in problems:
        print(f"[check] {problem}", file=sys.stderr)
    return 1 if problems else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="生成《原子参数表》（只读源码与卡数据）。")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="输出文件，默认 docs/原子参数表.md")
    parser.add_argument("--stdout", action="store_true", help="打到标准输出，不写文件")
    parser.add_argument("--check", action="store_true", help="只校验（数字与 mod_atom_report 一致、文件是最新的）")
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

    model = build()
    text = render(model) + "\n"
    out_path = pathlib.Path(args.out)

    if args.stdout:
        print(text, end="")
        return 0
    if args.check:
        return check(model, text, out_path)

    out_path.write_text(text, encoding="utf-8", newline="\n")
    summary = model["summary"]
    param_total = sum(len(op_params(model, op)) for op in model["universe"])
    print(f"written: {out_path} ({out_path.stat().st_size} bytes)")
    print(f"原子: {len(model['universe'])} | 参数条目: {param_total} | "
          f"_CORE_LOGIC_OPS: {summary['core_ops']} | _atomic_*: {summary['engine_ops']} | "
          f"悬空 op: {len(summary['dangling'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
