import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from mod_spec_v2 import (
    API_VERSION,
    FORMAT_VERSION,
    RESERVED_NAMESPACES,
    VALID_CAPABILITIES,
    VALID_EVENT_HOOKS,
    VALID_LOGIC_OPS,
    VALID_PATCH_OPS,
    VALID_REGISTRY_KEYS,
    VALID_UI_COMPONENT_TYPES,
    is_namespace,
    is_namespaced_id,
    normalize_resource_id,
    sha256_json,
    split_resource_id,
)


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

    registries = _validate_registries(normalized.get("registries"), mod_id, errors, warnings, allow_reserved_namespaces)
    normalized["registries"] = registries

    normalized["patches"] = _validate_patches(normalized.get("patches"), mod_id, errors, warnings)
    normalized["compatibility"] = _validate_compatibility(normalized.get("compatibility"), mod_id, errors, warnings)
    normalized["event_hooks"] = _validate_event_hooks(normalized.get("event_hooks"), errors, warnings)

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


def _validate_registries(value: Any, mod_id: str, errors: List[str], warnings: List[str],
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
                rid = normalize_resource_id(mod_id, raw_id)
            except ValueError as exc:
                errors.append(f"registries.{key}[{idx}].id 错误: {exc}")
                continue
            namespace, _ = split_resource_id(rid)
            if namespace in RESERVED_NAMESPACES and not allow_reserved_namespaces:
                errors.append(f"registries.{key}[{idx}] 不能定义保留命名空间资源 {rid}")
            if namespace != mod_id and not (allow_reserved_namespaces and mod_id in RESERVED_NAMESPACES):
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
                if ctrl_type not in VALID_UI_COMPONENT_TYPES:
                    errors.append(f"{label}.controls[{i}].type 必须是受控 UI 类型")
    if registry in ("cards", "statuses", "opening_events"):
        events = resource.get("events", {})
        if events is not None and not isinstance(events, dict):
            errors.append(f"{label}.events 必须是对象")
        elif isinstance(events, dict):
            for event_name, event_def in events.items():
                steps = event_def.get("steps", []) if isinstance(event_def, dict) else event_def
                total = _validate_steps(steps, f"{label}.events.{event_name}", errors, depth=0)
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
        total = _validate_steps(row.get("steps", []), f"event_hooks[{i}].steps", errors, depth=0)
        if total > MAX_EVENT_STEPS:
            errors.append(f"event_hooks[{i}].steps 递归步骤总数超过上限 {MAX_EVENT_STEPS}")
        normalized.append(row)
    return normalized


def _validate_steps(value: Any, label: str, errors: List[str], *, depth: int) -> int:
    if value is None:
        return 0
    if not isinstance(value, list):
        errors.append(f"{label} 必须是数组")
        return 0
    if len(value) > MAX_EVENT_STEPS:
        errors.append(f"{label} 步骤数量超过上限 {MAX_EVENT_STEPS}")
    count = 0
    for i, step in enumerate(value):
        count += _validate_step(step, f"{label}[{i}]", errors, depth=depth + 1)
    return count


def _validate_step(step: Any, label: str, errors: List[str], *, depth: int) -> int:
    if depth > MAX_LOGIC_DEPTH:
        errors.append(f"{label} 嵌套深度超过上限 {MAX_LOGIC_DEPTH}")
        return 1
    if not isinstance(step, dict):
        errors.append(f"{label} 必须是对象")
        return 1
    op = step.get("op") or step.get("type")
    if op not in VALID_LOGIC_OPS:
        errors.append(f"{label}.op 不在 DSL 白名单中: {op}")
    count = 1
    for key in ("steps", "then", "else", "body", "on_cancel"):
        child = step.get(key)
        if isinstance(child, list):
            count += _validate_steps(child, f"{label}.{key}", errors, depth=depth)
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
