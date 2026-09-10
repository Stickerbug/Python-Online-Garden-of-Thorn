# -*- coding: utf-8 -*-
"""Apply the workbook-14 four-language card text to every bundled package.

Reads tools/allcards14_i18n.py and writes both the inline ``effect_text`` /
``effect_text_i18n`` fields in mod.json and the per-language ``locales/*.json``
entries, so the runtime, the encyclopedia and the mod editor all show the same
authoritative Chinese text plus its EN/FR/JA rewrites.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"
sys.path.insert(0, str(ROOT / "tools"))

from allcards14_i18n import CARD_TEXTS  # noqa: E402

LANGS = ("zh", "en", "fr", "ja")


def main_member(zf: zipfile.ZipFile) -> str:
    names = {name.lower(): name for name in zf.namelist()}
    for candidate in ("mod.json", "gtnmod.json"):
        if candidate in names:
            return names[candidate]
    raise ValueError("package has no mod.json")


def load_package(path: pathlib.Path):
    with zipfile.ZipFile(path, "r") as zf:
        main = main_member(zf)
        data = json.loads(zf.read(main).decode("utf-8-sig"))
        members = {item.filename: zf.read(item.filename) for item in zf.infolist()}
    return data, members, main


def write_package(path: pathlib.Path, data, members, main: str) -> None:
    members = dict(members)
    members[main] = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    handle, temp_name = tempfile.mkstemp(suffix=".gtnmod", dir=str(path.parent))
    os.close(handle)
    temp_path = pathlib.Path(temp_name)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for filename, content in members.items():
                zf.writestr(filename, content)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def apply_texts(data: dict, members: dict):
    matched = []
    changed = []
    locales = {}
    for lang in LANGS:
        key = "locales/%s.json" % lang
        if key in members:
            locales[lang] = json.loads(members[key].decode("utf-8-sig"))
    for card in data.get("registries", {}).get("cards", []) or []:
        texts = CARD_TEXTS.get(str(card.get("name_en") or ""))
        if not texts:
            continue
        matched.append(card.get("name_en"))
        before = card.get("effect_text")
        card["effect_text"] = texts["zh"]
        i18n = card.get("effect_text_i18n")
        if not isinstance(i18n, dict):
            i18n = {}
        for lang in LANGS:
            i18n[lang] = texts[lang]
        card["effect_text_i18n"] = i18n
        for lang in LANGS:
            document = locales.get(lang)
            if not isinstance(document, dict):
                continue
            cards = document.get("cards")
            if not isinstance(cards, dict):
                continue
            entry = cards.get(card.get("id"))
            if not isinstance(entry, dict):
                continue
            entry["effect_text"] = texts[lang]
        if before != texts["zh"]:
            changed.append(card.get("name_en"))
    for lang, document in locales.items():
        members["locales/%s.json" % lang] = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
    return matched, changed


def main() -> int:
    total = []
    matched_all = []
    for path in sorted(MODS.glob("*.gtnmod")):
        data, members, main_name = load_package(path)
        matched, changed = apply_texts(data, members)
        if not matched:
            continue
        write_package(path, data, members, main_name)
        total.extend(changed)
        matched_all.extend(matched)
        print("patched", path.name, "->", len(matched), "cards", "(%d text changes)" % len(changed))
    print("total cards", len(matched_all), "| zh text changes", len(total))
    missing = sorted(set(CARD_TEXTS) - set(matched_all))
    if missing:
        print("NOT FOUND IN PACKAGES:", missing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
