import copy
import re
from typing import Any, Dict, Iterable, Tuple


SUPPORTED_LANGUAGES = ("zh", "en", "fr", "ja")
LOCALIZED_RESOURCE_FIELDS = {
    "cards": ("name", "effect_text", "description", "trigger_effect_text", "response_title", "response_content"),
    "opening_events": ("name", "description", "desc"),
    "ui_components": ("name", "title", "description", "label", "placeholder"),
    "statuses": ("name", "description"),
    "tags": ("name", "description"),
}
_PLACEHOLDER_RE = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}|\[\[(?:icon|card):[^\]]+\]\]")


def normalize_locale_code(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    aliases = {
        "zh_cn": "zh",
        "zh_hans": "zh",
        "en_us": "en",
        "en_gb": "en",
        "fr_fr": "fr",
        "ja_jp": "ja",
    }
    return aliases.get(text, text if text in SUPPORTED_LANGUAGES else "")


def normalize_locales(value: Any) -> Dict[str, dict]:
    if not isinstance(value, dict):
        return {}
    out: Dict[str, dict] = {}
    for raw_lang, document in value.items():
        lang = normalize_locale_code(raw_lang)
        if lang and isinstance(document, dict):
            out[lang] = copy.deepcopy(document)
    return out


def _resource_candidates(resource_id: str) -> Iterable[str]:
    full = str(resource_id or "").strip()
    local = full.split(":", 1)[-1]
    yield full
    if local != full:
        yield local


def _localized_resource_entry(document: dict, registry: str, resource_id: str) -> dict:
    section = document.get(registry)
    if not isinstance(section, dict):
        return {}
    for candidate in _resource_candidates(resource_id):
        entry = section.get(candidate)
        if isinstance(entry, dict):
            return entry
    return {}


def _legacy_field(resource: dict, field: str, lang: str) -> str:
    suffixes = {
        "zh": ("zh", "cn"),
        "en": ("en",),
        "fr": ("fr",),
        "ja": ("ja", "jp"),
    }.get(lang, (lang,))
    aliases = [field]
    if field == "name":
        aliases.append("title")
    elif field == "description":
        aliases.extend(("desc", "flavor"))
    elif field == "effect_text":
        aliases.append("effect")
    elif field == "trigger_effect_text":
        aliases.append("trigger")
    for alias in aliases:
        for suffix in suffixes:
            value = resource.get(f"{alias}_{suffix}")
            if isinstance(value, str) and value:
                return value
    if lang == "zh":
        value = resource.get(field)
        if isinstance(value, str):
            return value
        if field == "description":
            value = resource.get("desc")
            if isinstance(value, str):
                return value
    return ""


def _fallback_language_order(lang: str, default_language: str) -> Tuple[str, ...]:
    ordered = []
    for candidate in (lang, default_language, "en", "zh"):
        if candidate in SUPPORTED_LANGUAGES and candidate not in ordered:
            ordered.append(candidate)
    return tuple(ordered)


def apply_mod_locales(data: dict) -> dict:
    """Normalize package locale documents into the runtime *_i18n fields."""
    out = copy.deepcopy(data or {})
    locales = normalize_locales(out.get("locales"))
    out["locales"] = locales
    manifest = out.get("manifest") if isinstance(out.get("manifest"), dict) else {}
    default_language = normalize_locale_code(manifest.get("default_language")) or "zh"
    manifest["default_language"] = default_language

    manifest_i18n = {}
    for field in ("name", "description"):
        values = {}
        for lang in SUPPORTED_LANGUAGES:
            document_manifest = locales.get(lang, {}).get("manifest", {})
            if isinstance(document_manifest, dict):
                value = document_manifest.get(field)
                if isinstance(value, str) and value:
                    values[lang] = value
            if lang not in values:
                legacy = _legacy_field(manifest, field, lang)
                if legacy:
                    values[lang] = legacy
        manifest_i18n[field] = {
            lang: next((values[c] for c in _fallback_language_order(lang, default_language) if values.get(c)), "")
            for lang in SUPPORTED_LANGUAGES
        }
        manifest[f"{field}_i18n"] = manifest_i18n[field]
    out["manifest"] = manifest

    registries = out.get("registries") if isinstance(out.get("registries"), dict) else {}
    for registry, fields in LOCALIZED_RESOURCE_FIELDS.items():
        resources = registries.get(registry)
        if not isinstance(resources, list):
            continue
        for resource in resources:
            if not isinstance(resource, dict):
                continue
            resource_id = str(resource.get("id") or "")
            for field in fields:
                values = {}
                existing = resource.get(f"{field}_i18n")
                if isinstance(existing, dict):
                    for raw_lang, value in existing.items():
                        lang = normalize_locale_code(raw_lang)
                        if lang and isinstance(value, str) and value:
                            values[lang] = value
                for lang, document in locales.items():
                    entry = _localized_resource_entry(document, registry, resource_id)
                    value = entry.get(field)
                    if value is None and field == "description":
                        value = entry.get("desc", entry.get("flavor"))
                    elif value is None and field == "effect_text":
                        value = entry.get("effect")
                    elif value is None and field == "trigger_effect_text":
                        value = entry.get("trigger")
                    if isinstance(value, str) and value:
                        values[lang] = value
                for lang in SUPPORTED_LANGUAGES:
                    if lang not in values:
                        legacy = _legacy_field(resource, field, lang)
                        if legacy:
                            values[lang] = legacy
                resource[f"{field}_i18n"] = {
                    lang: next((values[c] for c in _fallback_language_order(lang, default_language) if values.get(c)), "")
                    for lang in SUPPORTED_LANGUAGES
                }
    out["registries"] = registries
    return out


def locale_validation_warnings(data: dict) -> list:
    locales = normalize_locales((data or {}).get("locales"))
    manifest = (data or {}).get("manifest") if isinstance((data or {}).get("manifest"), dict) else {}
    default_language = normalize_locale_code(manifest.get("default_language")) or "zh"
    warnings = []
    if default_language not in locales:
        warnings.append(f"模组未提供 locales/{default_language}.json，将使用旧文本字段作为默认语言")
    registries = (data or {}).get("registries") if isinstance((data or {}).get("registries"), dict) else {}
    cards = registries.get("cards") if isinstance(registries.get("cards"), list) else []
    for lang in SUPPORTED_LANGUAGES:
        missing = 0
        document = locales.get(lang, {})
        for card in cards:
            if not isinstance(card, dict):
                continue
            entry = _localized_resource_entry(document, "cards", str(card.get("id") or ""))
            if not all(isinstance(entry.get(field), str) and entry.get(field) for field in ("name", "effect_text", "description")):
                missing += 1
        if cards and missing:
            warnings.append(f"{lang} 卡牌翻译缺少或不完整: {missing}/{len(cards)}")
    return warnings


def placeholder_mismatches(data: dict) -> list:
    locales = normalize_locales((data or {}).get("locales"))
    baseline = locales.get("zh") or locales.get("en") or {}
    issues = []
    for registry, fields in LOCALIZED_RESOURCE_FIELDS.items():
        base_section = baseline.get(registry) if isinstance(baseline.get(registry), dict) else {}
        for resource_id, base_entry in base_section.items():
            if not isinstance(base_entry, dict):
                continue
            for field in fields:
                base_tokens = sorted(_PLACEHOLDER_RE.findall(str(base_entry.get(field) or "")))
                for lang, document in locales.items():
                    section = document.get(registry) if isinstance(document.get(registry), dict) else {}
                    entry = section.get(resource_id) if isinstance(section.get(resource_id), dict) else {}
                    value = entry.get(field)
                    if value is None:
                        continue
                    tokens = sorted(_PLACEHOLDER_RE.findall(str(value)))
                    if tokens != base_tokens:
                        issues.append(f"{lang}:{registry}.{resource_id}.{field} 的图标/参数占位符与默认语言不一致")
    return issues
