from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from mod_spec_v2 import (
    RESERVED_NAMESPACES,
    VALID_REGISTRY_KEYS,
    canonical_json,
    is_namespaced_id,
    sha256_json,
    split_resource_id,
)


MERGED_REGISTRY_KEYS = ("cards", "tags", "statuses", "opening_events", "ui_components")


@dataclass
class LoadoutResult:
    ok: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    load_order: List[str] = field(default_factory=list)
    registries: Dict[str, Dict[str, Dict[str, Any]]] = field(default_factory=dict)
    patches: List[Dict[str, Any]] = field(default_factory=list)
    event_hooks: List[Dict[str, Any]] = field(default_factory=list)
    compatibility: List[Dict[str, Any]] = field(default_factory=list)
    loadout_hash: str = ""
    mod_hashes: Dict[str, str] = field(default_factory=dict)


def build_v2_loadout(mods: Iterable[Any], enabled_mod_ids: Optional[Iterable[str]] = None) -> LoadoutResult:
    """Merge validated GTN Mod Spec v2 mods into a deterministic loadout.

    This phase sorts, checks, merges registries, applies safe declarative patches,
    and collects event hooks for runtime execution.
    """

    result = LoadoutResult(
        registries={key: {} for key in MERGED_REGISTRY_KEYS},
    )
    enabled_filter = set(str(mid).strip() for mid in enabled_mod_ids or [] if str(mid).strip())
    mod_map: Dict[str, Dict[str, Any]] = {}

    for raw_mod in mods or []:
        record = _coerce_v2_mod(raw_mod)
        if not record:
            continue
        manifest = record["manifest"]
        mod_id = manifest.get("id", "")
        if enabled_filter and mod_id not in enabled_filter:
            continue
        if record["errors"]:
            result.errors.extend(f"{mod_id or record['source']}: {err}" for err in record["errors"])
            continue
        if not mod_id:
            result.errors.append(f"{record['source']}: manifest.id 缺失")
            continue
        if mod_id in mod_map:
            result.errors.append(f"v2 模组 ID 重复: {mod_id}")
            continue
        mod_map[mod_id] = record

    if not mod_map:
        result.loadout_hash = sha256_json({
            "load_order": [],
            "mod_hashes": {},
            "registries": result.registries,
            "patches": [],
            "event_hooks": [],
            "compatibility": [],
        })
        result.ok = not result.errors
        return result

    _check_dependencies(mod_map, result)
    _check_conflicts(mod_map, result)
    load_order = _topological_order(mod_map, result)
    result.load_order = load_order

    if not load_order:
        result.ok = False
        result.loadout_hash = sha256_json({"errors": result.errors})
        return result

    for mod_id in load_order:
        record = mod_map[mod_id]
        result.mod_hashes[mod_id] = record["content_hash"]
        _merge_registries(record, result)
        result.patches.extend(_with_owner(record.get("patches", []), mod_id))
        result.event_hooks.extend(_with_owner(record.get("event_hooks", []), mod_id))
        compatibility_rows = _collect_compatibility(record, mod_map, result)
        result.compatibility.extend(compatibility_rows)
        for row in compatibility_rows:
            if row.get("_active"):
                for patch in _with_owner(row.get("patches", []), mod_id):
                    patch["_compatibility_for"] = row.get("if_mod_loaded", "")
                    result.patches.append(patch)

    _apply_patches(result)

    result.event_hooks.sort(key=lambda hook: (
        str(hook.get("hook", "")),
        int(hook.get("priority", 0) if isinstance(hook.get("priority", 0), int) else 0),
        str(hook.get("_mod_id", "")),
    ))

    result.ok = not result.errors
    result.loadout_hash = sha256_json({
        "load_order": result.load_order,
        "mod_hashes": result.mod_hashes,
        "registries": result.registries,
        "patches": _hashable_patches(result.patches),
        "event_hooks": result.event_hooks,
        "compatibility": _hashable_compatibility(result.compatibility),
    })
    return result


def _coerce_v2_mod(raw_mod: Any) -> Optional[Dict[str, Any]]:
    if raw_mod is None:
        return None
    if isinstance(raw_mod, dict):
        fmt = raw_mod.get("format_version")
        if fmt != 2:
            return None
        manifest = raw_mod.get("manifest") if isinstance(raw_mod.get("manifest"), dict) else {}
        registries = raw_mod.get("registries") if isinstance(raw_mod.get("registries"), dict) else {}
        return {
            "source": raw_mod.get("filename") or raw_mod.get("source") or manifest.get("id") or "memory",
            "manifest": dict(manifest),
            "registries": _registry_dicts(registries),
            "patches": list(raw_mod.get("patches", []) if isinstance(raw_mod.get("patches", []), list) else []),
            "event_hooks": list(raw_mod.get("event_hooks", []) if isinstance(raw_mod.get("event_hooks", []), list) else []),
            "compatibility": list(raw_mod.get("compatibility", []) if isinstance(raw_mod.get("compatibility", []), list) else []),
            "content_hash": str(raw_mod.get("content_hash") or raw_mod.get("validation_hash") or sha256_json(raw_mod)),
            "errors": list(raw_mod.get("errors", []) if isinstance(raw_mod.get("errors", []), list) else []),
        }

    if getattr(raw_mod, "format_version", 1) != 2:
        return None
    manifest_obj = getattr(raw_mod, "manifest", None)
    manifest = manifest_obj.to_dict() if hasattr(manifest_obj, "to_dict") else dict(manifest_obj or {})
    registries = {}
    for key, resources in (getattr(raw_mod, "registries", {}) or {}).items():
        items = []
        for resource in resources or []:
            items.append(resource.to_dict() if hasattr(resource, "to_dict") else dict(resource or {}))
        registries[key] = items
    return {
        "source": getattr(raw_mod, "filename", "") or getattr(raw_mod, "filepath", "") or manifest.get("id", "memory"),
        "manifest": manifest,
        "registries": _registry_dicts(registries),
        "patches": list(getattr(raw_mod, "patches", []) or []),
        "event_hooks": list(getattr(raw_mod, "event_hooks", []) or []),
        "compatibility": list(getattr(raw_mod, "compatibility", []) or []),
        "content_hash": str(getattr(raw_mod, "content_hash", "") or getattr(raw_mod, "validation_hash", "")),
        "errors": list(getattr(raw_mod, "errors", []) or []),
    }


def _registry_dicts(registries: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    out = {}
    for key in VALID_REGISTRY_KEYS:
        items = registries.get(key, [])
        if not isinstance(items, list):
            out[key] = []
            continue
        out[key] = [dict(item) for item in items if isinstance(item, dict)]
    return out


def _check_dependencies(mod_map: Dict[str, Dict[str, Any]], result: LoadoutResult) -> None:
    for mod_id, record in mod_map.items():
        manifest = record["manifest"]
        for dep in manifest.get("dependencies", []) or []:
            dep_id, version = _dep_id_version(dep)
            if not dep_id:
                continue
            if dep_id not in mod_map:
                result.errors.append(f"{mod_id} 缺少依赖模组 {dep_id}")
                continue
            if version and not _version_satisfies(mod_map[dep_id]["manifest"].get("version", ""), version):
                result.errors.append(
                    f"{mod_id} 依赖 {dep_id} 版本 {version}，当前为 {mod_map[dep_id]['manifest'].get('version', '')}"
                )
        for dep in manifest.get("optional_dependencies", []) or []:
            dep_id, version = _dep_id_version(dep)
            if not dep_id:
                continue
            if dep_id not in mod_map:
                result.warnings.append(f"{mod_id} 的可选依赖 {dep_id} 未启用")
                continue
            if version and not _version_satisfies(mod_map[dep_id]["manifest"].get("version", ""), version):
                result.warnings.append(
                    f"{mod_id} 的可选依赖 {dep_id} 版本不匹配：需要 {version}，当前为 {mod_map[dep_id]['manifest'].get('version', '')}"
                )


def _check_conflicts(mod_map: Dict[str, Dict[str, Any]], result: LoadoutResult) -> None:
    for mod_id, record in mod_map.items():
        for conflict in record["manifest"].get("conflicts", []) or []:
            conflict_id, version = _dep_id_version(conflict)
            if not conflict_id or conflict_id not in mod_map:
                continue
            if version and not _version_satisfies(mod_map[conflict_id]["manifest"].get("version", ""), version):
                continue
            reason = conflict.get("reason") if isinstance(conflict, dict) else ""
            suffix = f"：{reason}" if reason else ""
            result.errors.append(f"{mod_id} 与 {conflict_id} 冲突{suffix}")


def _topological_order(mod_map: Dict[str, Dict[str, Any]], result: LoadoutResult) -> List[str]:
    edges: Dict[str, Set[str]] = {mod_id: set() for mod_id in mod_map}
    indegree: Dict[str, int] = {mod_id: 0 for mod_id in mod_map}

    def add_edge(before: str, after: str) -> None:
        if before == after or before not in mod_map or after not in mod_map:
            return
        if after not in edges[before]:
            edges[before].add(after)
            indegree[after] += 1

    for mod_id, record in mod_map.items():
        manifest = record["manifest"]
        for dep in manifest.get("dependencies", []) or []:
            dep_id, _ = _dep_id_version(dep)
            add_edge(dep_id, mod_id)
        for dep in manifest.get("optional_dependencies", []) or []:
            dep_id, _ = _dep_id_version(dep)
            add_edge(dep_id, mod_id)
        for before in manifest.get("load_after", []) or []:
            add_edge(str(before), mod_id)
        for after in manifest.get("load_before", []) or []:
            add_edge(mod_id, str(after))

    ready = sorted([mod_id for mod_id, deg in indegree.items() if deg == 0], key=_mod_sort_key)
    order: List[str] = []
    while ready:
        mod_id = ready.pop(0)
        order.append(mod_id)
        for nxt in sorted(edges[mod_id], key=_mod_sort_key):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
                ready.sort(key=_mod_sort_key)

    if len(order) != len(mod_map):
        cycle = sorted([mod_id for mod_id, deg in indegree.items() if deg > 0])
        result.errors.append(f"v2 模组依赖或加载顺序存在循环: {', '.join(cycle)}")
        return []
    return order


def _mod_sort_key(mod_id: str) -> Tuple[int, str]:
    if mod_id == "gtn":
        return (0, mod_id)
    if mod_id == "core":
        return (1, mod_id)
    if mod_id in RESERVED_NAMESPACES:
        return (2, mod_id)
    return (3, mod_id)


def _merge_registries(record: Dict[str, Any], result: LoadoutResult) -> None:
    mod_id = record["manifest"].get("id", "")
    seen_in_mod: Set[str] = set()
    for key in MERGED_REGISTRY_KEYS:
        for resource in record["registries"].get(key, []) or []:
            resource_id = str(resource.get("id") or "").strip()
            if not resource_id:
                result.errors.append(f"{mod_id} 的 registries.{key} 存在空 ID")
                continue
            if not is_namespaced_id(resource_id):
                result.errors.append(f"{mod_id} 的资源 ID 非法: {resource_id}")
                continue
            namespace, _ = split_resource_id(resource_id)
            if namespace == "gtn" and mod_id != "gtn":
                result.errors.append(f"{mod_id} 不能直接覆盖 gtn 命名空间资源 {resource_id}")
                continue
            if namespace in RESERVED_NAMESPACES and namespace != mod_id:
                result.errors.append(f"{mod_id} 不能定义保留命名空间资源 {resource_id}")
                continue
            if resource_id in seen_in_mod:
                result.errors.append(f"{mod_id} 重复定义资源 {resource_id}")
                continue
            seen_in_mod.add(resource_id)
            existing = result.registries[key].get(resource_id)
            if existing is not None:
                result.errors.append(
                    f"资源 ID 冲突: {resource_id} 同时来自 {existing.get('_mod_id', '?')} 和 {mod_id}"
                )
                continue
            merged = dict(resource)
            merged["_mod_id"] = mod_id
            result.registries[key][resource_id] = merged


def _collect_compatibility(record: Dict[str, Any], mod_map: Dict[str, Dict[str, Any]], result: LoadoutResult) -> List[Dict[str, Any]]:
    mod_id = record["manifest"].get("id", "")
    collected = []
    for item in record.get("compatibility", []) or []:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        row["_mod_id"] = mod_id
        target = str(row.get("if_mod_loaded") or "").strip()
        row["_active"] = bool(target and target in mod_map)
        if target and target not in mod_map:
            result.warnings.append(f"{mod_id} 的兼容补丁目标 {target} 未启用，已跳过")
        collected.append(row)
    return collected


REGISTRY_BY_TARGET_TYPE = {
    "card": "cards",
    "cards": "cards",
    "tag": "tags",
    "tags": "tags",
    "status": "statuses",
    "statuses": "statuses",
    "opening_event": "opening_events",
    "opening_events": "opening_events",
    "event": "opening_events",
    "ui_component": "ui_components",
    "ui_components": "ui_components",
}

PATCH_NUMERIC_FIELDS = {
    "cost_e", "cost_m", "count", "weight", "trigger_cost_e", "position",
    "damage", "hits", "heal", "draw", "gain_e", "gain_m", "armor",
    "dodge", "poison", "burn",
}

PATCH_UI_STYLE_TOKENS = {"accent", "icon", "panel", "size"}


def _apply_patches(result: LoadoutResult) -> None:
    applied: List[Dict[str, Any]] = []
    for patch in result.patches:
        if not isinstance(patch, dict):
            continue
        patch_record = dict(patch)
        ok = _apply_patch(patch_record, result)
        patch_record["_applied"] = bool(ok)
        applied.append(patch_record)
    result.patches = applied


def _strip_runtime_keys(value: Any):
    if isinstance(value, dict):
        return {
            key: _strip_runtime_keys(child)
            for key, child in value.items()
            if not str(key).startswith("_")
        }
    if isinstance(value, list):
        return [_strip_runtime_keys(item) for item in value]
    return value


def _hashable_patches(patches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_strip_runtime_keys(patch) for patch in patches if isinstance(patch, dict)]


def _hashable_compatibility(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_strip_runtime_keys(row) for row in rows if isinstance(row, dict)]


def _apply_patch(patch: Dict[str, Any], result: LoadoutResult) -> bool:
    op = str(patch.get("op") or "").strip()
    if op not in {
        "add_tag",
        "remove_tag",
        "append_event_steps",
        "prepend_event_steps",
        "add_ui_style_token",
        "modify_numeric_field",
        "add_description_line",
    }:
        result.warnings.append(f"未知 v2 patch op，已跳过: {op}")
        return False
    target = str(patch.get("target") or "").strip()
    target_type = str(patch.get("target_type") or "").strip()
    registry_key = REGISTRY_BY_TARGET_TYPE.get(target_type)
    if not registry_key:
        result.warnings.append(f"v2 patch target_type 无效，已跳过: {target_type}")
        return False
    if not is_namespaced_id(target):
        result.warnings.append(f"v2 patch target 不是命名空间 ID，已跳过: {target}")
        return False
    resource = result.registries.get(registry_key, {}).get(target)
    if resource is None:
        result.warnings.append(f"v2 patch target 不存在，已跳过: {target}")
        return False
    owner = str(patch.get("_mod_id") or "")
    target_namespace, _ = split_resource_id(target)
    if target_namespace in RESERVED_NAMESPACES and owner not in RESERVED_NAMESPACES:
        result.warnings.append(f"{owner} 不允许 patch 官方核心资源 {target}，已跳过")
        return False

    if op == "add_tag":
        tag = str(patch.get("value") or patch.get("tag") or "").strip()
        if not is_namespaced_id(tag):
            result.warnings.append(f"v2 add_tag value 无效，已跳过: {tag}")
            return False
        tags = _ensure_list(resource, "tags")
        if tag not in tags:
            tags.append(tag)
        flags = _ensure_list(resource, "flags")
        if tag not in flags:
            flags.append(tag)
        return True

    if op == "remove_tag":
        tag = str(patch.get("value") or patch.get("tag") or "").strip()
        if not tag:
            result.warnings.append("v2 remove_tag 缺少 value，已跳过")
            return False
        for key in ("tags", "flags"):
            if isinstance(resource.get(key), list):
                resource[key] = [item for item in resource[key] if str(item) != tag]
        return True

    if op in ("append_event_steps", "prepend_event_steps"):
        event_name = str(patch.get("event") or patch.get("event_name") or "on_play").strip()
        if not event_name:
            result.warnings.append("v2 event steps patch 缺少 event，已跳过")
            return False
        raw_steps = patch.get("value", patch.get("steps", []))
        steps = raw_steps if isinstance(raw_steps, list) else [raw_steps]
        steps = [step for step in steps if isinstance(step, dict)]
        if not steps:
            result.warnings.append("v2 event steps patch 没有有效 step，已跳过")
            return False
        events = resource.setdefault("events", {})
        if not isinstance(events, dict):
            resource["events"] = events = {}
        event_def = events.setdefault(event_name, {"steps": []})
        if isinstance(event_def, list):
            event_def = {"steps": event_def}
            events[event_name] = event_def
        if not isinstance(event_def, dict):
            event_def = {"steps": []}
            events[event_name] = event_def
        existing = event_def.get("steps")
        if not isinstance(existing, list):
            existing = []
        event_def["steps"] = existing + steps if op == "append_event_steps" else steps + existing
        return True

    if op == "add_ui_style_token":
        token = patch.get("value")
        style = resource.setdefault("style", {})
        if not isinstance(style, dict):
            resource["style"] = style = {}
        if isinstance(token, dict):
            for key, value in token.items():
                key = str(key).strip()
                if key in PATCH_UI_STYLE_TOKENS:
                    style[key] = value
        else:
            key = str(patch.get("field") or patch.get("name") or "").strip()
            if key not in PATCH_UI_STYLE_TOKENS:
                result.warnings.append("v2 add_ui_style_token field/name is not an allowed style token")
                return False
            style[key] = token
        return True

    if op == "modify_numeric_field":
        field = str(patch.get("field") or "").strip()
        if field not in PATCH_NUMERIC_FIELDS:
            result.warnings.append(f"v2 modify_numeric_field 不允许修改字段 {field}，已跳过")
            return False
        try:
            current = float(resource.get(field, 0) or 0)
            value = float(patch.get("value", patch.get("amount", 0)) or 0)
        except Exception:
            result.warnings.append(f"v2 modify_numeric_field 数值无效，已跳过: {target}.{field}")
            return False
        mode = str(patch.get("mode") or patch.get("operator") or "set")
        if mode in ("add", "+"):
            next_value = current + value
        elif mode in ("mul", "*"):
            next_value = current * value
        elif mode in ("sub", "-"):
            next_value = current - value
        else:
            next_value = value
        resource[field] = int(next_value) if float(next_value).is_integer() else next_value
        return True

    if op == "add_description_line":
        field = str(patch.get("field") or "description").strip()
        if field not in {"description", "description_cn", "description_en", "effect_text", "effect_text_cn", "effect_text_en"}:
            result.warnings.append(f"v2 add_description_line 不允许修改字段 {field}，已跳过")
            return False
        line = str(patch.get("value") or patch.get("text") or "").strip()
        if not line:
            result.warnings.append("v2 add_description_line 缺少文本，已跳过")
            return False
        old = str(resource.get(field) or "").rstrip()
        resource[field] = f"{old}\n{line}" if old else line
        return True

    return False


def _ensure_list(resource: Dict[str, Any], key: str) -> List[Any]:
    value = resource.get(key)
    if not isinstance(value, list):
        value = []
        resource[key] = value
    return value


def _with_owner(items: Iterable[Any], mod_id: str) -> List[Dict[str, Any]]:
    out = []
    for item in items or []:
        if isinstance(item, dict):
            row = dict(item)
            row["_mod_id"] = mod_id
            out.append(row)
    return out


def _dep_id_version(dep: Any) -> Tuple[str, str]:
    if isinstance(dep, str):
        return dep.strip(), ""
    if isinstance(dep, dict):
        return str(dep.get("id") or "").strip(), str(dep.get("version") or dep.get("version_range") or "").strip()
    return "", ""


def _version_satisfies(actual: str, requirement: str) -> bool:
    requirement = re.sub(r"\s+", "", str(requirement or ""))
    if not requirement:
        return True
    match = re.fullmatch(r"(>=|<=|==)?(\d+\.\d+\.\d+)", requirement)
    if not match:
        return False
    op = match.group(1) or "=="
    want = _version_tuple(match.group(2))
    have = _version_tuple(actual)
    if have is None:
        return False
    if op == ">=":
        return have >= want
    if op == "<=":
        return have <= want
    return have == want


def _version_tuple(value: str) -> Optional[Tuple[int, int, int]]:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", str(value or ""))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))
