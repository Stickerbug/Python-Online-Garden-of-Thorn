#!/usr/bin/env python3
"""Generate static achievement locales from the authoritative definitions."""

import ast
import concurrent.futures
import json
import pathlib

from sync_mod_locales import _google_translate


ROOT = pathlib.Path(__file__).resolve().parents[1]
DB_FILE = ROOT / "db.py"
OUTPUT_FILE = ROOT / "achievement_i18n.json"
LOCALE_OVERRIDES = {
    "creative_mode_mana_pool": {
        "name": {
            "fr": "Le Bassin éternel de la culpabilité",
            "ja": "永遠なる罪の魔力池",
        },
    },
}


def read_definitions():
    tree = ast.parse(DB_FILE.read_text(encoding="utf-8"), filename=str(DB_FILE))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "ACHIEVEMENT_DEFS" for target in node.targets):
            continue
        return ast.literal_eval(node.value)
    raise RuntimeError("ACHIEVEMENT_DEFS not found")


def build_locales(workers=8):
    definitions = read_definitions()
    documents = {}
    jobs = {}
    for item in definitions:
        achievement_id = str(item.get("id") or "")
        if not achievement_id:
            continue
        documents[achievement_id] = {
            "name": {
                "zh": str(item.get("name_cn") or achievement_id),
                "en": str(item.get("name_en") or item.get("name_cn") or achievement_id),
            },
            "description": {
                "zh": str(item.get("description_cn") or ""),
                "en": str(item.get("description_en") or item.get("description_cn") or ""),
            },
        }
        for field in ("name", "description"):
            source = documents[achievement_id][field]["zh"]
            for lang, target in (("fr", "fr"), ("ja", "ja")):
                if source:
                    jobs.setdefault((lang, source), target)
    translated = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(_google_translate, source, target): (lang, source)
            for (lang, source), target in jobs.items()
        }
        for future in concurrent.futures.as_completed(futures):
            translated[futures[future]] = future.result()
    for entry in documents.values():
        for field in ("name", "description"):
            source = entry[field]["zh"]
            entry[field]["fr"] = translated.get(("fr", source), entry[field]["en"])
            entry[field]["ja"] = translated.get(("ja", source), entry[field]["en"])
    for achievement_id, fields in LOCALE_OVERRIDES.items():
        entry = documents.get(achievement_id)
        if not entry:
            continue
        for field, values in fields.items():
            if field in entry and isinstance(values, dict):
                entry[field].update(values)
    return documents


def main():
    document = {
        "schema_version": 1,
        "languages": ["zh", "en", "fr", "ja"],
        "achievements": build_locales(),
    }
    OUTPUT_FILE.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(document['achievements'])} achievements to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
