#!/usr/bin/env python3
"""Build locale files inside bundled .gtnmod packages.

The game never calls a translation service at runtime. Network translation is an
optional authoring aid; generated files are embedded into the package and can be
reviewed like any other asset.
"""

import argparse
import concurrent.futures
import copy
import json
import os
import pathlib
import re
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile


LANGUAGES = ("zh", "en", "fr", "ja")
CARD_FIELDS = (
    "name",
    "effect_text",
    "description",
    "trigger_effect_text",
    "response_title",
    "response_content",
)
MARKUP_RE = re.compile(r"\[\[[^\]]+\]\]")


def _polish_english(text):
    """Normalize machine output to GTN's concise rules vocabulary.

    This is deliberately conservative: it fixes terminology and recurring
    sentence shapes, while card-specific meaning still comes from the current
    Chinese rules text and can be curated in the embedded locale afterwards.
    """
    value = str(text or "").strip()
    if not value:
        return value
    replacements = (
        (r"\bat the beginning of\b", "at the start of"),
        (r"\bAt the beginning of\b", "At the start of"),
        (r"\brounds?\b", lambda m: "turns" if m.group(0).endswith("s") else "turn"),
        (r"\bRound\b", "Turn"),
        (r"\bconsumption\b", "cost"),
        (r"\bupper limit\b", "maximum"),
        (r"\bdraw pile\b", "deck"),
        (r"\bdiscard pile\b", "discard pile"),
        (r"\bnumber of layers\b", "number of stacks"),
        (r"\b1 layer of\b", "1 stack of"),
        (r"\b(\d+) layers of\b", r"\1 stacks of"),
        (r"\bcan be selected\b", "is selectable"),
        (r"\bcannot be selected\b", "is not selectable"),
        (r"\bconditions for use\b", "play requirements"),
        (r"\bcondition for use\b", "play requirement"),
        (r"\bhand cards\b", "cards in hand"),
        (r"\bhand card\b", "card in hand"),
        (r"\bsub-lobes?\b", lambda m: "sub-petals" if m.group(0).endswith("s") else "sub-petal"),
        (r"\bto target\b", "to the target"),
    )
    for pattern, replacement in replacements:
        value = re.sub(pattern, replacement, value, flags=re.IGNORECASE if isinstance(replacement, str) else 0)
    value = re.sub(r"^Causes?\b", "Deal", value)
    value = re.sub(r"^Deals?\b", "Deal", value)
    value = re.sub(r"^Applies?\b", "Apply", value)
    value = re.sub(r"^Restores?\b", "Restore", value)
    value = re.sub(r"^Destroys?\b", "Destroy", value)
    value = re.sub(r"^Exiles?\b", "Exile", value)
    value = re.sub(r"^Selects?\b", "Select", value)
    value = re.sub(r"\s+([,.;:])", r"\1", value)
    return value


def _polish_english_document(document):
    result = copy.deepcopy(document or {})
    manifest = result.get("manifest")
    if isinstance(manifest, dict) and manifest.get("description"):
        manifest["description"] = _polish_english(manifest["description"])
    for entry in (result.get("cards") or {}).values():
        if not isinstance(entry, dict):
            continue
        for field in CARD_FIELDS:
            if field != "name" and entry.get(field):
                entry[field] = _polish_english(entry[field])
    return result


def _markup_token(index):
    value = int(index)
    letters = ""
    while True:
        value, remainder = divmod(value, 26)
        letters = chr(65 + remainder) + letters
        if value == 0:
            return f"⟦{letters}⟧"
        value -= 1


def _mask_markup(text):
    values = []

    def replace(match):
        values.append(match.group(0))
        return f" {_markup_token(len(values) - 1)} "

    return MARKUP_RE.sub(replace, str(text or "")), values


def _restore_markup(text, values):
    out = str(text or "")
    for index, value in enumerate(values):
        token = _markup_token(index)
        # Some translators preserve the brackets but convert the marker's
        # ASCII letters to full-width forms. Match both without normalizing the
        # surrounding translated sentence or its punctuation.
        full_width_token = "".join(
            chr(ord(char) + 0xFEE0) if "A" <= char <= "Z" else char
            for char in token
        )
        alternatives = "|".join(re.escape(item) for item in (token, full_width_token))
        out = re.sub(rf"\s*(?:{alternatives})\s*", value, out, flags=re.IGNORECASE)
    return out.strip()


def _google_translate(text, target, source="zh-CN", attempts=4):
    if not text:
        return ""
    masked, markup = _mask_markup(text)
    query = urllib.parse.urlencode({
        "client": "gtx",
        "sl": source,
        "tl": target,
        "dt": "t",
        "q": masked,
    })
    url = f"https://translate.googleapis.com/translate_a/single?{query}"
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "GTN locale builder/1.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            translated = "".join(str(part[0] or "") for part in payload[0] if part and part[0] is not None)
            return _restore_markup(translated, markup)
        except Exception:
            if attempt + 1 >= attempts:
                raise
            time.sleep(0.5 * (2 ** attempt))
    return text


def _main_member(zf):
    names = {name.lower(): name for name in zf.namelist()}
    for candidate in ("mod.json", "gtnmod.json"):
        if candidate in names:
            return names[candidate]
    raise ValueError("package has no mod.json")


def _card_source(card, field):
    if field == "name":
        return str(card.get("name_cn") or card.get("name") or card.get("name_en") or "")
    if field == "description":
        return str(card.get("description") or card.get("desc") or "")
    return str(card.get(field) or "")


def _english_source(card, field):
    if field == "name":
        return str(card.get("name_en") or card.get("name_cn") or card.get("id") or "")
    # Old effect_text_en fields are often stale after balance updates. Only the
    # stable English card name is authoritative; translate current rules anew.
    return ""


def _base_document(data):
    manifest = data.get("manifest") if isinstance(data.get("manifest"), dict) else {}
    cards = (data.get("registries") or {}).get("cards", [])
    result = {
        "manifest": {
            "name": str(manifest.get("name_cn") or manifest.get("name") or ""),
            "description": str(manifest.get("description_cn") or manifest.get("description") or ""),
        },
        "cards": {},
    }
    for card in cards if isinstance(cards, list) else []:
        if not isinstance(card, dict):
            continue
        resource_id = str(card.get("id") or "")
        if not resource_id:
            continue
        entry = {}
        for field in CARD_FIELDS:
            value = _card_source(card, field)
            if value:
                entry[field] = value
        result["cards"][resource_id] = entry
    return result


def _translation_jobs(data, zh_document):
    manifest = data.get("manifest") if isinstance(data.get("manifest"), dict) else {}
    cards_by_id = {
        str(card.get("id") or ""): card
        for card in ((data.get("registries") or {}).get("cards", []) or [])
        if isinstance(card, dict)
    }
    jobs = []
    for lang in ("en", "fr", "ja"):
        for field, value in zh_document["manifest"].items():
            if value:
                explicit = str(manifest.get(f"{field}_{lang}") or "")
                jobs.append((lang, "manifest", "", field, explicit, value))
        for resource_id, entry in zh_document["cards"].items():
            card = cards_by_id.get(resource_id, {})
            for field, value in entry.items():
                explicit = _english_source(card, field) if lang == "en" else str(card.get(f"{field}_{lang}") or "")
                jobs.append((lang, "cards", resource_id, field, explicit, value))
    return jobs


def _translate_documents(data, zh_document, workers=8):
    documents = {lang: {"manifest": {}, "cards": {}} for lang in ("en", "fr", "ja")}
    jobs = _translation_jobs(data, zh_document)
    unique = {}
    for lang, _, _, _, explicit, source in jobs:
        if explicit:
            continue
        unique.setdefault((lang, source), None)

    target_codes = {"en": "en", "fr": "fr", "ja": "ja"}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(_google_translate, source, target_codes[lang]): (lang, source)
            for lang, source in unique
        }
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            unique[key] = future.result()

    for lang, registry, resource_id, field, explicit, source in jobs:
        value = explicit or unique.get((lang, source)) or source
        if registry == "manifest":
            documents[lang]["manifest"][field] = value
        else:
            documents[lang]["cards"].setdefault(resource_id, {})[field] = value
    return documents


def _write_package(path, data, locale_documents):
    with zipfile.ZipFile(path, "r") as source:
        main_member = _main_member(source)
        members = [(item, source.read(item.filename)) for item in source.infolist()
                   if not item.filename.lower().startswith("locales/")]
    data = copy.deepcopy(data)
    data.setdefault("manifest", {})["default_language"] = "zh"
    encoded_main = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".gtnmod", dir=str(path.parent)) as temp:
        temp_path = pathlib.Path(temp.name)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
            for item, content in members:
                target.writestr(item, encoded_main if item.filename == main_member else content)
            for lang, document in locale_documents.items():
                target.writestr(f"locales/{lang}.json", json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8"))
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def sync_package(path, translate=False, workers=8):
    with zipfile.ZipFile(path, "r") as zf:
        main_member = _main_member(zf)
        data = json.loads(zf.read(main_member).decode("utf-8-sig"))
    zh_document = _base_document(data)
    locale_documents = {"zh": zh_document}
    if translate:
        locale_documents.update(_translate_documents(data, zh_document, workers=workers))
    else:
        with zipfile.ZipFile(path, "r") as zf:
            names = {name.lower(): name for name in zf.namelist()}
            for lang in ("en", "fr", "ja"):
                member = names.get(f"locales/{lang}.json")
                if member:
                    locale_documents[lang] = json.loads(zf.read(member).decode("utf-8-sig"))
    if "en" in locale_documents:
        locale_documents["en"] = _polish_english_document(locale_documents["en"])
    _write_package(path, data, locale_documents)
    return len(zh_document["cards"]), sorted(locale_documents)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mods-dir", default="mods")
    parser.add_argument("--translate", action="store_true", help="fill en/fr/ja using the authoring translation service")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    mods_dir = pathlib.Path(args.mods_dir)
    # Materialize first because replacing a zip mutates the directory iterator on Windows.
    for path in sorted(list(mods_dir.glob("*.gtnmod"))):
        count, languages = sync_package(path, translate=args.translate, workers=args.workers)
        print(f"{path.name}: {count} cards, locales={','.join(languages)}", flush=True)


if __name__ == "__main__":
    main()
