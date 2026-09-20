import copy
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from mod_spec_v2 import (
    API_VERSION,
    ATOMIC_OP_MACROS,
    CONDITION_OPS,
    DUAL_STEP_AND_EXPRESSION_OPS,
    EXPRESSION_OPS,
    FORMAT_VERSION,
    INTERNAL_HANDLERS,
    PUBLIC_ATOMS,
    REMOVED_ATOMIC_OPS,
    RENAMED_ATOMIC_OPS,
    RESERVED_NAMESPACES,
    RUNTIME_STEP_OPS,
    VALID_CAPABILITIES,
    VALID_EVENT_HOOKS,
    VALID_LOGIC_OPS,
    VALID_PATCH_OPS,
    VALID_REGISTRY_KEYS,
    VALID_UI_CONTROL_TYPES,
    VALID_UI_COMPONENT_TYPES,
    damage_pipeline_warnings,
    is_namespace,
    is_namespaced_id,
    normalize_resource_id,
    sha256_json,
    split_resource_id,
)
from mod_i18n import locale_validation_warnings, normalize_locales, placeholder_mismatches
# Round 94 / 批次 CQ：**发布期**校验直接复用运行时的词表，避免再抄一份。
# ``mod_runtime_v2`` 只依赖 cards / damage_types / runtime_budget / mod_spec_v2，
# 不反向依赖本模块，静态导入不会成环（见 tools/mod_atom_report 的 ui 参数对拍）。
from mod_runtime_v2 import (
    INPUT_VALUE_TYPES,
    REQUEST_UI_ON_INVALID_VALUES,
    TEXT_INPUT_HARD_MAX_LENGTH,
    TEXT_INPUT_MODERATIONS,
    TEXT_INPUT_NORMALIZES,
)
import official_statuses


MAX_CARDS = 300
MAX_STATUSES = 200
MAX_OPENING_EVENTS = 100
MAX_UI_COMPONENTS = 100
MAX_TAGS = 300
MAX_LOGIC_DEPTH = 20
MAX_EVENT_STEPS = 200

REGISTRY_LIMITS = {
    "cards": MAX_CARDS,
    "tags": MAX_TAGS,
    "statuses": MAX_STATUSES,
    "opening_events": MAX_OPENING_EVENTS,
    "ui_components": MAX_UI_COMPONENTS,
}

RESOURCE_REGISTRY_KEYS = ("cards", "tags", "statuses", "opening_events", "ui_components")


@dataclass
class ValidationResult:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    normalized: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""
    format_version: Optional[int] = FORMAT_VERSION

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_mod_v2(data: Any, source: str = "", *, allow_reserved_namespaces: bool = False) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    if not isinstance(data, dict):
        return ValidationResult(errors=["v2 模组根节点必须是对象"])

    normalized = copy.deepcopy(data)
    if normalized.get("format_version") != FORMAT_VERSION:
        errors.append(f"format_version 必须为 {FORMAT_VERSION}")
        normalized["format_version"] = FORMAT_VERSION

    if _has_scripts_field(normalized):
        errors.append("GTN Mod Spec v2 不允许 scripts 字段；社区模组只能使用声明式 DSL 和受控 UI schema")

    manifest = _validate_manifest(
        normalized.get("manifest"),
        errors,
        warnings,
        allow_reserved_namespaces=allow_reserved_namespaces,
    )
    normalized["manifest"] = manifest
    mod_id = manifest.get("id", "")
    resource_namespace = manifest.get("resource_namespace", mod_id)

    registries = _validate_registries(
        normalized.get("registries"),
        resource_namespace,
        errors,
        warnings,
        allow_reserved_namespaces,
    )
    normalized["registries"] = registries

    normalized["patches"] = _validate_patches(normalized.get("patches"), mod_id, errors, warnings)
    normalized["compatibility"] = _validate_compatibility(normalized.get("compatibility"), mod_id, errors, warnings)
    normalized["event_hooks"] = _validate_event_hooks(normalized.get("event_hooks"), errors, warnings)
    normalized["locales"] = normalize_locales(normalized.get("locales"))
    warnings.extend(locale_validation_warnings(normalized))
    warnings.extend(placeholder_mismatches(normalized))
    # Round 28（方案 A）：伤害族"参数写错管线"的友好提示。**只提示**，
    # 不报错、不改数据：deal_damage 里的 damage_type/damage_tag、
    # direct_damage 里的 force_crit/is_precision 等写出来会被伤害管线
    # 忽略，过去只能靠人肉对源码，现在由词汇表统一给出。
    warnings.extend(damage_pipeline_warnings(normalized))

    # Round 108 / 批次 DF：状态 id 的发布期提示（官方 17 条状态已内置，见 official_statuses.py）。
    # 只提示、不拦投稿：命名空间写在官方那几个包里的状态 id，如果内置表里没有，
    # 基本就是拼错——运行时会当自定义状态处理、**静默无效**（历史"幽灵钩子"的同一类毛病）。
    warnings.extend(status_reference_warnings(normalized, registries))

    for key in list(normalized.keys()):
        if key not in {
            "format_version",
            "manifest",
            "registries",
            "patches",
            "compatibility",
            "event_hooks",
            "workspace_json",
            "editor",
            "metadata",
            "locales",
        }:
            warnings.append(f"未知顶层字段 {key} 已保留但不会在第一阶段执行")

    content_hash = sha256_json(normalized) if isinstance(normalized, dict) else ""
    return ValidationResult(
        errors=errors,
        warnings=warnings,
        normalized=normalized,
        content_hash=content_hash,
        format_version=FORMAT_VERSION,
    )


def _validate_manifest(value: Any, errors: List[str], warnings: List[str], *, allow_reserved_namespaces: bool) -> Dict[str, Any]:
    if not isinstance(value, dict):
        errors.append("v2 模组必须包含 manifest 对象")
        value = {}
    manifest = copy.deepcopy(value)

    mod_id = str(manifest.get("id") or "").strip()
    if not mod_id:
        errors.append("manifest.id 必须存在")
    elif not is_namespace(mod_id):
        errors.append("manifest.id 只能包含小写字母、数字、下划线")
    elif mod_id in RESERVED_NAMESPACES and not allow_reserved_namespaces:
        errors.append(f"社区 v2 模组不能使用保留命名空间 {mod_id}")
    manifest["id"] = mod_id

    resource_namespace_declared = "resource_namespace" in manifest
    resource_namespace = str(manifest.get("resource_namespace") or mod_id).strip()
    if not is_namespace(resource_namespace):
        errors.append("manifest.resource_namespace 必须是合法模组命名空间")
        resource_namespace = mod_id
    elif resource_namespace != mod_id and not allow_reserved_namespaces:
        errors.append("社区模组的 manifest.resource_namespace 必须与 manifest.id 相同")
        resource_namespace = mod_id
    elif resource_namespace in RESERVED_NAMESPACES and not allow_reserved_namespaces:
        errors.append(f"社区 v2 模组不能使用保留资源命名空间 {resource_namespace}")
        resource_namespace = mod_id
    if resource_namespace_declared:
        manifest["resource_namespace"] = resource_namespace

    for key in ("name", "version"):
        if not isinstance(manifest.get(key), str) or not manifest.get(key).strip():
            errors.append(f"manifest.{key} 必须存在且必须是非空字符串")
        else:
            manifest[key] = manifest[key].strip()

    api_version = str(manifest.get("api_version") or "").strip()
    if not api_version:
        errors.append("manifest.api_version 必须存在")
    elif not api_version.startswith("2."):
        errors.append(f"manifest.api_version 必须兼容 2.x，当前为 {api_version}")
    manifest["api_version"] = api_version or API_VERSION

    category = str(manifest.get("category") or "official").strip().lower()
    if category not in {"official", "entertainment"}:
        warnings.append(f"未知 manifest.category: {category}，已按 official 处理")
        category = "official"
    manifest["category"] = category

    capabilities = manifest.get("capabilities", [])
    if capabilities is None:
        capabilities = []
    if not isinstance(capabilities, list):
        errors.append("manifest.capabilities 必须是数组")
        capabilities = []
    normalized_caps = []
    for cap in capabilities:
        if not isinstance(cap, str):
            errors.append("manifest.capabilities 中的能力必须是字符串")
            continue
        cap = cap.strip()
        if cap not in VALID_CAPABILITIES:
            errors.append(f"未知 capability: {cap}")
        else:
            normalized_caps.append(cap)
    manifest["capabilities"] = sorted(set(normalized_caps))

    for key in ("dependencies", "optional_dependencies"):
        manifest[key] = _normalize_dependency_list(manifest.get(key, []), f"manifest.{key}", errors)
    manifest["conflicts"] = _normalize_conflicts(manifest.get("conflicts", []), errors)
    manifest["load_after"] = _normalize_mod_id_list(manifest.get("load_after", []), "manifest.load_after", errors)
    manifest["load_before"] = _normalize_mod_id_list(manifest.get("load_before", []), "manifest.load_before", errors)
    return manifest


def _normalize_dependency_list(value: Any, label: str, errors: List[str]) -> List[Dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append(f"{label} 必须是数组")
        return []
    out: List[Dict[str, str]] = []
    for i, item in enumerate(value):
        if isinstance(item, str):
            dep_id = item.strip()
            version = ""
        elif isinstance(item, dict):
            dep_id = str(item.get("id") or "").strip()
            version = str(item.get("version") or item.get("version_range") or "").strip()
        else:
            errors.append(f"{label}[{i}] 必须是字符串或对象")
            continue
        if not is_namespace(dep_id):
            errors.append(f"{label}[{i}].id 必须是合法模组命名空间")
            continue
        if version and not _valid_version_range(version):
            errors.append(f"{label}[{i}].version 只支持 >=x.y.z、<=x.y.z、==x.y.z 或 x.y.z")
        out.append({"id": dep_id, "version": version})
    return out


def _normalize_conflicts(value: Any, errors: List[str]) -> List[Dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append("manifest.conflicts 必须是数组")
        return []
    out: List[Dict[str, str]] = []
    for i, item in enumerate(value):
        if isinstance(item, str):
            mod_id, version, reason = item.strip(), "", ""
        elif isinstance(item, dict):
            mod_id = str(item.get("id") or "").strip()
            version = str(item.get("version") or item.get("version_range") or "").strip()
            reason = str(item.get("reason") or "").strip()
        else:
            errors.append(f"manifest.conflicts[{i}] 必须是字符串或对象")
            continue
        if not is_namespace(mod_id):
            errors.append(f"manifest.conflicts[{i}].id 必须是合法模组命名空间")
            continue
        if version and not _valid_version_range(version):
            errors.append(f"manifest.conflicts[{i}].version 只支持简单版本范围")
        out.append({"id": mod_id, "version": version, "reason": reason})
    return out


def _normalize_mod_id_list(value: Any, label: str, errors: List[str]) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        errors.append(f"{label} 必须是字符串或数组")
        return []
    out = []
    for i, item in enumerate(value):
        mod_id = str(item or "").strip()
        if not is_namespace(mod_id):
            errors.append(f"{label}[{i}] 必须是合法模组命名空间")
        else:
            out.append(mod_id)
    return sorted(set(out))


def _valid_version_range(value: str) -> bool:
    import re
    return bool(re.fullmatch(r"(>=|<=|==)?\d+\.\d+\.\d+", value.strip()))


def _validate_registries(value: Any, resource_namespace: str, errors: List[str], warnings: List[str],
                         allow_reserved_namespaces: bool) -> Dict[str, List[Dict[str, Any]]]:
    if value is None:
        value = {}
    if not isinstance(value, dict):
        errors.append("registries 必须是对象")
        value = {}
    registries: Dict[str, List[Dict[str, Any]]] = {}
    seen_ids: Dict[str, str] = {}

    for key in VALID_REGISTRY_KEYS:
        items = value.get(key, [])
        if items is None:
            items = []
        if not isinstance(items, list):
            errors.append(f"registries.{key} 必须是数组")
            items = []
        limit = REGISTRY_LIMITS.get(key)
        if limit is not None and len(items) > limit:
            errors.append(f"registries.{key} 数量超过上限 {limit}")
        normalized_items = []
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"registries.{key}[{idx}] 必须是对象")
                continue
            resource = copy.deepcopy(item)
            raw_id = resource.get("id")
            try:
                rid = normalize_resource_id(resource_namespace, raw_id)
            except ValueError as exc:
                errors.append(f"registries.{key}[{idx}].id 错误: {exc}")
                continue
            namespace, _ = split_resource_id(rid)
            if namespace in RESERVED_NAMESPACES and not allow_reserved_namespaces:
                errors.append(f"registries.{key}[{idx}] 不能定义保留命名空间资源 {rid}")
            if namespace != resource_namespace:
                errors.append(f"registries.{key}[{idx}] 只能定义本模组命名空间资源，当前为 {rid}")
            if rid in seen_ids:
                errors.append(f"资源 ID 重复: {rid} 同时出现在 {seen_ids[rid]} 和 registries.{key}[{idx}]")
            seen_ids[rid] = f"registries.{key}[{idx}]"
            resource["id"] = rid
            _validate_resource_shape(key, resource, f"registries.{key}[{idx}]", errors, warnings)
            normalized_items.append(resource)
        registries[key] = normalized_items

    for key in value.keys():
        if key not in VALID_REGISTRY_KEYS:
            warnings.append(f"未知 registry {key} 已忽略")
    return registries


def _ui_text_warnings(component: Dict[str, Any], label: str, warnings: Optional[List[str]]) -> List[str]:
    """Round 80 / 批次 BZ：``request_ui`` 窗口的**中文文案**检查（中文优先）。

    缺中文只记 **warning**：英文窗口不算写错，但按项目口径（卡面中文是第一语言）
    应该补上。检查面与 ``tools/mod_atom_report.ui_text_consistency`` 一致——
    标题 / 控件标签或文本 / 选项标签 / 按钮文案。
    """

    bucket = warnings if isinstance(warnings, list) else []
    if not isinstance(component, dict):
        return bucket
    if not (component.get("title_cn") or component.get("title")):
        bucket.append(f"{label} 的窗口没有中文标题（title_cn）")
    for index, control in enumerate(component.get("controls") or []):
        if not isinstance(control, dict):
            continue
        cid = str(control.get("id") or f"#{index}")
        ctype = str(control.get("type") or "text")
        has_cn = bool(control.get("label_cn") or control.get("text_cn")
                      or control.get("label") or control.get("text"))
        if not has_cn:
            bucket.append(f"{label}.controls[{index}]（{cid}/{ctype}）没有中文文案")
        for option_index, option in enumerate(control.get("options") or []):
            if isinstance(option, dict) and not (option.get("label_cn") or option.get("label")):
                bucket.append(f"{label}.controls[{index}].options[{option_index}] 没有中文标签")
    for index, button in enumerate(component.get("buttons") or []):
        if not isinstance(button, dict):
            continue
        if not (button.get("text_cn") or button.get("label_cn")
                or button.get("text") or button.get("label")):
            bucket.append(f"{label}.buttons[{index}]（{button.get('id')}）没有中文文案")
    return bucket


def _ui_control_param_checks(control: Dict[str, Any], label: str,
                             errors: List[str], warnings: List[str]) -> None:
    """Round 94 / 批次 CQ：新 UI 控件的**发布期**参数校验。

    以前发布期只看控件类型，``input.value_type`` / ``text_input.normalize`` /
    ``text_input.moderation`` / ``pattern`` 这些是**运行时**才炸
    （``mod_runtime_v2._sanitize_ui_control`` 显式 raise）——写错的包能正常导入，
    要等玩家真的打开那个窗口才报错。这里把同一套词表提前到导入/投稿时。

    口径与运行时一致：

    * 运行时**会拒绝**的（词表写错、正则编不过）→ 发布期 error；
    * 运行时**静默忽略/截断**的（``default_from`` 形状、``visible_if`` 不是对象、
      ``min_select > max_select``、越界长度）→ 发布期 warning，不拦投稿。
    """

    ctype = control.get("type")
    if ctype == "input":
        value_type = str(control.get("value_type") or "text").strip().lower()
        if value_type not in INPUT_VALUE_TYPES:
            errors.append(
                f"{label}.value_type 不在受控词表：{control.get('value_type')!r}"
                f"（只认 {' / '.join(INPUT_VALUE_TYPES)}）"
            )
    if ctype == "text_input":
        normalize = str(control.get("normalize") or "trim").strip().lower()
        if normalize not in TEXT_INPUT_NORMALIZES:
            errors.append(
                f"{label}.normalize 不在受控词表：{control.get('normalize')!r}"
                f"（只认 {' / '.join(TEXT_INPUT_NORMALIZES)}）"
            )
        moderation = str(control.get("moderation") or "mask").strip().lower()
        if moderation not in TEXT_INPUT_MODERATIONS:
            errors.append(
                f"{label}.moderation 不在受控词表：{control.get('moderation')!r}"
                f"（只认 {' / '.join(TEXT_INPUT_MODERATIONS)}）"
            )
        pattern = str(control.get("pattern") or "").strip()
        if pattern:
            try:
                re.compile(pattern)
            except re.error as exc:
                errors.append(f"{label}.pattern 不是合法正则：{exc}")
        max_length = control.get("max_length")
        if max_length is not None:
            if isinstance(max_length, bool) or not isinstance(max_length, (int, float)):
                warnings.append(f"{label}.max_length 不是数字（运行时按默认 64 处理）：{max_length!r}")
            elif max_length <= 0 or max_length > TEXT_INPUT_HARD_MAX_LENGTH:
                warnings.append(
                    f"{label}.max_length 超出 1..{TEXT_INPUT_HARD_MAX_LENGTH}"
                    f"（运行时按硬上限/默认值处理）：{max_length!r}"
                )
    default_from = control.get("default_from")
    if default_from not in (None, {}):
        known_keys = ("player_var", "card_var", "var")
        if not isinstance(default_from, dict) or not any(key in default_from for key in known_keys):
            warnings.append(
                f"{label}.default_from 认不出来（只认 {' / '.join(known_keys)}），"
                f"运行时会忽略并回落到 default：{default_from!r}"
            )
    for key in ("visible_if", "disabled_if"):
        rule = control.get(key)
        if rule is not None and not isinstance(rule, dict):
            warnings.append(f"{label}.{key} 必须是对象（条件算子或兄弟控件规则），当前会被忽略：{rule!r}")
    min_select = control.get("min_select")
    max_select = control.get("max_select")
    if isinstance(min_select, (int, float)) and isinstance(max_select, (int, float)):
        if min_select > max_select:
            warnings.append(
                f"{label}.min_select({min_select}) 大于 max_select({max_select})，"
                "运行时会把上限抬到下限"
            )


def _request_ui_param_checks(step: Dict[str, Any], label: str,
                             errors: List[str], warnings: List[str]) -> None:
    """Round 94 / 批次 CQ：``request_ui`` **步骤参数**的发布期校验。

    ``on_invalid`` 写错时运行时会显式报错（``_request_ui_on_invalid``），
    ``timeout_ms`` / ``on_cancel`` 是静默兜底（0 / 忽略），所以前者 error、后者 warning。
    """

    if "on_invalid" in step:
        on_invalid = str(step.get("on_invalid") or "close").strip().lower()
        if on_invalid not in REQUEST_UI_ON_INVALID_VALUES:
            errors.append(
                f"{label}.on_invalid 不在受控词表：{step.get('on_invalid')!r}"
                f"（只认 {' / '.join(REQUEST_UI_ON_INVALID_VALUES)}）"
            )
    timeout = step.get("timeout_ms")
    if timeout is not None:
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float, dict, list)):
            warnings.append(f"{label}.timeout_ms 不是数字也不是取值表达式（运行时按 0 = 不限时）：{timeout!r}")
        elif isinstance(timeout, (int, float)) and timeout < 0:
            warnings.append(f"{label}.timeout_ms 是负数（运行时按 0 = 不限时）：{timeout!r}")
    if "on_cancel" in step and not isinstance(step.get("on_cancel"), list):
        warnings.append(f"{label}.on_cancel 必须是数组（运行时忽略非数组）：{step.get('on_cancel')!r}")


def _ui_button_checks(component: Dict[str, Any], label: str, warnings: List[str]) -> None:
    """Round 96 / 批次 CS：窗口按钮的发布期检查（都是 warning——运行时是"丢弃/回落"）。

    ``_sanitize_ui_component`` 对按钮的处理是：只取**前 6 个**、没有 ``id`` 的直接丢、
    一个都不剩就补「确认 / 取消」。也就是说这些写法不会炸，只会让作者的按钮**悄悄消失**，
    所以发布期用 warning 提醒，不拦投稿（编辑器里已经能改按钮，见批次 CR）。
    """

    buttons = component.get("buttons")
    if buttons is None:
        return
    if not isinstance(buttons, list):
        warnings.append(f"{label}.buttons 必须是数组（运行时会补默认按钮）：{buttons!r}")
        return
    if len(buttons) > 6:
        warnings.append(f"{label}.buttons 有 {len(buttons)} 个，运行时只认前 6 个")
    for index, button in enumerate(buttons):
        if not isinstance(button, dict):
            warnings.append(f"{label}.buttons[{index}] 必须是对象（运行时丢弃）")
            continue
        if not str(button.get("id") or "").strip():
            warnings.append(f"{label}.buttons[{index}] 没有 id（运行时丢弃，不会被渲染）")
        if "role" in button and not isinstance(button.get("role"), str):
            warnings.append(f"{label}.buttons[{index}].role 必须是字符串（运行时按 confirm 处理）")


def _validate_resource_shape(registry: str, resource: Dict[str, Any], label: str,
                             errors: List[str], warnings: List[str]) -> None:
    if registry == "ui_components":
        comp_type = resource.get("type")
        if comp_type not in VALID_UI_COMPONENT_TYPES:
            errors.append(f"{label}.type 必须是受控 UI 类型")
        controls = resource.get("controls", [])
        if controls is not None and not isinstance(controls, list):
            errors.append(f"{label}.controls 必须是数组")
        if isinstance(controls, list):
            for i, ctrl in enumerate(controls):
                if not isinstance(ctrl, dict):
                    errors.append(f"{label}.controls[{i}] 必须是对象")
                    continue
                ctrl_type = ctrl.get("type")
                if ctrl_type not in VALID_UI_CONTROL_TYPES:
                    errors.append(f"{label}.controls[{i}].type 必须是受控 UI 控件类型")
                _ui_control_param_checks(ctrl, f"{label}.controls[{i}]", errors, warnings)
        _ui_button_checks(resource, label, warnings)
        _ui_text_warnings(resource, label, warnings)
    if registry in ("cards", "statuses", "opening_events"):
        events = resource.get("events", {})
        if events is not None and not isinstance(events, dict):
            errors.append(f"{label}.events 必须是对象")
        elif isinstance(events, dict):
            for event_name, event_def in events.items():
                steps = event_def.get("steps", []) if isinstance(event_def, dict) else event_def
                total = _validate_steps(steps, f"{label}.events.{event_name}", errors, warnings, depth=0)
                if total > MAX_EVENT_STEPS:
                    errors.append(f"{label}.events.{event_name} 递归步骤总数超过上限 {MAX_EVENT_STEPS}")
    if registry == "cards":
        tags = resource.get("tags", [])
        if tags is not None:
            if not isinstance(tags, list):
                errors.append(f"{label}.tags 必须是数组")
            else:
                normalized_tags = []
                for i, tag in enumerate(tags):
                    if not isinstance(tag, str):
                        errors.append(f"{label}.tags[{i}] 必须是字符串")
                        continue
                    try:
                        normalized_tags.append(normalize_resource_id(_resource_namespace(resource.get("id")), tag))
                    except ValueError as exc:
                        errors.append(f"{label}.tags[{i}] 错误: {exc}")
                resource["tags"] = normalized_tags
    if registry == "statuses":
        stacking = resource.get("stacking", "stack")
        if stacking not in ("stack", "duration", "unique"):
            errors.append(f"{label}.stacking 必须是 stack、duration 或 unique")


def _resource_namespace(resource_id: Any) -> str:
    if not isinstance(resource_id, str) or not is_namespaced_id(resource_id):
        return ""
    namespace, _ = split_resource_id(resource_id)
    return namespace


def _validate_patches(value: Any, mod_id: str, errors: List[str], warnings: List[str]) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append("patches 必须是数组")
        return []
    normalized = []
    for i, patch in enumerate(value):
        if not isinstance(patch, dict):
            errors.append(f"patches[{i}] 必须是对象")
            continue
        item = copy.deepcopy(patch)
        for key in ("target", "target_type", "op"):
            if not isinstance(item.get(key), str) or not item.get(key).strip():
                errors.append(f"patches[{i}].{key} 必须是非空字符串")
        if isinstance(item.get("op"), str) and item["op"] not in VALID_PATCH_OPS:
            errors.append(f"patches[{i}].op 不在 patch 白名单中: {item['op']}")
        if isinstance(item.get("target"), str):
            try:
                item["target"] = normalize_resource_id(mod_id, item["target"])
            except ValueError as exc:
                errors.append(f"patches[{i}].target 错误: {exc}")
        if isinstance(item.get("value"), str) and item.get("op") in {"add_tag", "remove_tag"}:
            try:
                item["value"] = normalize_resource_id(mod_id, item["value"])
            except ValueError as exc:
                errors.append(f"patches[{i}].value 错误: {exc}")
        normalized.append(item)
    return normalized


def _validate_compatibility(value: Any, current_mod_id: str, errors: List[str], warnings: List[str]) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        errors.append("compatibility 必须是对象或数组")
        return []
    normalized = []
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"compatibility[{i}] 必须是对象")
            continue
        row = copy.deepcopy(item)
        target_mod_id = str(row.get("if_mod_loaded") or "").strip()
        if not is_namespace(target_mod_id):
            errors.append(f"compatibility[{i}].if_mod_loaded 必须是合法模组命名空间")
        row["if_mod_loaded"] = target_mod_id
        row["patches"] = _validate_patches(row.get("patches", []), current_mod_id, errors, warnings)
        normalized.append(row)
    return normalized


def _validate_event_hooks(value: Any, errors: List[str], warnings: List[str]) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append("event_hooks 必须是数组")
        return []
    normalized = []
    for i, hook in enumerate(value):
        if not isinstance(hook, dict):
            errors.append(f"event_hooks[{i}] 必须是对象")
            continue
        row = copy.deepcopy(hook)
        hook_name = row.get("hook")
        if hook_name not in VALID_EVENT_HOOKS:
            errors.append(f"event_hooks[{i}].hook 不在白名单中: {hook_name}")
        priority = row.get("priority", 0)
        if not isinstance(priority, int):
            errors.append(f"event_hooks[{i}].priority 必须是整数")
            row["priority"] = 0
        total = _validate_steps(row.get("steps", []), f"event_hooks[{i}].steps", errors, warnings, depth=0)
        if total > MAX_EVENT_STEPS:
            errors.append(f"event_hooks[{i}].steps 递归步骤总数超过上限 {MAX_EVENT_STEPS}")
        normalized.append(row)
    return normalized


"""状态 id 的发布期提示（Round 108 / 批次 DF）。

官方 17 条状态已经从包里搬进引擎内置表（见 ``official_statuses.py``）：

* 包内再声明同 id 的状态没有意义（会被内置表盖住）→ 给一条"可以删掉"的提示；
* 官方那几个命名空间里写了内置表没有的状态 id → 基本是拼错。运行时把不认识的名字
  当**自定义状态**处理，拼错就静默无效（和"幽灵钩子"同一类毛病），所以这里至少提示。

只提示、不报错：社区包可以引用第三方命名空间的状态（不在我们的词表里），
这里只对"官方命名空间"下结论。
"""

OFFICIAL_STATUS_NAMESPACES = frozenset(
    str(item["id"]).split(":", 1)[0].lower() for item in official_statuses.OFFICIAL_STATUSES
)
_STATUS_STEP_KEYS = ("status", "statuses")
_STATUS_VALUE_SKIP = frozenset({"all", "buffs", "debuffs"})


def _status_words(data: Any) -> set:
    """本包认得的状态词：内置官方表 + 本包自己声明的 id / 别名 / 名字。"""

    payload = data if isinstance(data, dict) else {}
    words = set(official_statuses.status_words())
    for item in (payload.get("registries") or {}).get("statuses") or []:
        if not isinstance(item, dict):
            continue
        for key in ("id", "name", "name_cn", "name_en"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                words.add(value.strip().lower())
        for alias in item.get("aliases") or []:
            if isinstance(alias, str) and alias.strip():
                words.add(alias.strip().lower())
    return words


def _iter_status_references(node: Any, path: str = ""):
    """产出 ``(状态名, 位置)``：步骤里 ``status`` / ``statuses`` 两个键的字符串值。"""

    if isinstance(node, dict):
        for key in _STATUS_STEP_KEYS:
            value = node.get(key)
            if isinstance(value, str):
                yield value.strip(), f"{path}.{key}"
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    if isinstance(item, str):
                        yield item.strip(), f"{path}.{key}[{index}]"
                    elif isinstance(item, dict):
                        inner = item.get("id") or item.get("status")
                        if isinstance(inner, str):
                            yield inner.strip(), f"{path}.{key}[{index}]"
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                yield from _iter_status_references(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _iter_status_references(value, f"{path}[{index}]")


def status_reference_warnings(data: Any, registries: Any = None) -> List[str]:
    """官方命名空间里的未知状态 id / 重复声明内置状态 → 提示列表。"""

    payload = data if isinstance(data, dict) else {}
    if isinstance(registries, dict):
        payload = dict(payload)
        payload["registries"] = registries
    known = _status_words(payload)
    out: List[str] = []
    seen = set()
    for value, label in _iter_status_references(payload):
        text = str(value or "").strip()
        if not text or text.lower() in _STATUS_VALUE_SKIP or text.lower() in known:
            continue
        if ":" not in text:
            continue
        namespace = text.split(":", 1)[0].strip().lower()
        if namespace not in OFFICIAL_STATUS_NAMESPACES or text in seen:
            continue
        seen.add(text)
        out.append(
            f"{label} 用了官方命名空间里的未知状态 id {text}（内置状态见 /api/mod-studio/schema "
            f"的 officialStatuses）；写错时运行时会当自定义状态、静默无效"
        )
    for index, item in enumerate((payload.get("registries") or {}).get("statuses") or []):
        if not isinstance(item, dict):
            continue
        status_id = str(item.get("id") or "").strip()
        if not status_id:
            continue
        builtin = official_statuses.get_status(status_id)
        if builtin and str(builtin["id"]) == status_id:
            out.append(
                f"registries.statuses[{index}] 声明的是官方内置状态 {status_id}："
                f"引擎与客户端自带定义，包内这份会被忽略，可以删掉"
            )
            continue
        short = status_id.split(":")[-1].strip().lower()
        builtin = official_statuses.get_status(short) if short else None
        if builtin and str(builtin["id"]) != status_id:
            out.append(
                f"registries.statuses[{index}] 的短名 {short} 与官方内置状态 {builtin['id']} 同名："
                f"客户端按短名找状态时会先命中内置那条，建议换一个短名（完整 id 使用不受影响）"
            )
    return out


def _validate_steps(value: Any, label: str, errors: List[str], warnings: Optional[List[str]] = None,
                    *, depth: int) -> int:
    if value is None:
        return 0
    if not isinstance(value, list):
        errors.append(f"{label} 必须是数组")
        return 0
    if len(value) > MAX_EVENT_STEPS:
        errors.append(f"{label} 步骤数量超过上限 {MAX_EVENT_STEPS}")
    count = 0
    for i, step in enumerate(value):
        count += _validate_step(step, f"{label}[{i}]", errors, warnings, depth=depth + 1)
    return count


def _validate_step(step: Any, label: str, errors: List[str], warnings: Optional[List[str]] = None,
                   *, depth: int) -> int:
    if depth > MAX_LOGIC_DEPTH:
        errors.append(f"{label} 嵌套深度超过上限 {MAX_LOGIC_DEPTH}")
        return 1
    if not isinstance(step, dict):
        errors.append(f"{label} 必须是对象")
        return 1
    op = step.get("op") or step.get("type")
    if op not in VALID_LOGIC_OPS:
        replacement = REMOVED_ATOMIC_OPS.get(op) if isinstance(op, str) else None
        if isinstance(op, str) and op in REMOVED_ATOMIC_OPS:
            hint = f"，请改用 {replacement}" if replacement else "，该 op 没有等价替代"
            errors.append(
                f"{label}.op 已移除（Round 20 长尾清理 / Round 25 登记残留清理 / "
                f"Round 30 零用量清理 / Round 31 真删真合）: {op}{hint}"
            )
        elif isinstance(op, str) and op in RENAMED_ATOMIC_OPS:
            errors.append(
                f"{label}.op 已改名（Round 22 别名收敛 / Round 25 登记残留清理 / "
                f"Round 30 零用量清理 / Round 31 真删真合）: {op}，"
                f"请改用 {RENAMED_ATOMIC_OPS[op]}"
            )
        else:
            errors.append(f"{label}.op 不在 DSL 白名单中: {op}")
    count = 1
    # Round 89 / 批次 CK：**位置校验**——补全登记表后，取值表达式 / 条件算子的名字也在
    # 契约白名单里；把它们当步骤写要拿到明确报错，而不是"通过了校验、运行时才炸"。
    step_ops = (set(PUBLIC_ATOMS) | set(INTERNAL_HANDLERS) | set(ATOMIC_OP_MACROS)
                | set(RUNTIME_STEP_OPS) | set(DUAL_STEP_AND_EXPRESSION_OPS))
    if isinstance(op, str) and op and op not in step_ops:
        if op in EXPRESSION_OPS:
            errors.append(f"{label}.op 是取值表达式算子，不能当步骤写: {op}（写在数值/文本参数位）")
        elif op in CONDITION_OPS:
            errors.append(f"{label}.op 是条件算子，不能当步骤写: {op}（写在 condition/run_if/unless 位置）")
    # Round 80 / 批次 BZ：``request_ui`` 的内联窗口文案检查（中文优先，见用户规则）。
    # 只是**警告**：英文窗口不算写错，但按项目口径应该补中文。
    if op == "request_ui" and isinstance(step.get("component"), dict):
        _ui_text_warnings(step["component"], f"{label}.component", warnings)
    # Round 94 / 批次 CQ：``request_ui`` 步骤参数（on_invalid / timeout_ms / on_cancel）
    # 的发布期校验——以前是运行时才炸 / 静默兜底。
    if op == "request_ui":
        _request_ui_param_checks(step, label, errors, warnings if isinstance(warnings, list) else [])
    for key in ("steps", "then", "else", "body", "on_cancel"):
        child = step.get(key)
        if isinstance(child, list):
            count += _validate_steps(child, f"{label}.{key}", errors, warnings, depth=depth)
        elif child is not None and key in ("steps", "then", "else", "body", "on_cancel"):
            errors.append(f"{label}.{key} 必须是数组")
    return count


def _has_scripts_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "scripts":
                return True
            if _has_scripts_field(child):
                return True
    elif isinstance(value, list):
        return any(_has_scripts_field(item) for item in value)
    return False
