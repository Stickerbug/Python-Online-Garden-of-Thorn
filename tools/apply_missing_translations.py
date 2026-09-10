# -*- coding: utf-8 -*-
"""Fill the remaining EN/FR/JA slots for official cards.

Complements tools/apply_allcards_i18n_14.py: that script rewrote the text of
the cards touched by the workbook-14 balance pass, while this one covers cards
whose French/Japanese slots still held English (or Chinese) text.
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

from allcards14_i18n_missing import ALL_NAMES, FORCE_NAMES, lookup  # noqa: E402

LANGS = ("en", "fr", "ja")


def load_package(path: pathlib.Path):
    with zipfile.ZipFile(path, "r") as zf:
        data = json.loads(zf.read("mod.json").decode("utf-8-sig"))
        members = {item.filename: zf.read(item.filename) for item in zf.infolist()}
    return data, members


def write_package(path: pathlib.Path, members: dict) -> None:
    handle, temp_name = tempfile.mkstemp(suffix=".gtnmod", dir=str(path.parent))
    os.close(handle)
    temp_path = pathlib.Path(temp_name)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for name, content in members.items():
                zf.writestr(name, content)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def main() -> int:
    patched = []
    for path in sorted(MODS.glob("*.gtnmod")):
        data, members = load_package(path)
        locales = {}
        for lang in ("zh", "en", "fr", "ja"):
            key = "locales/%s.json" % lang
            if key in members:
                locales[lang] = json.loads(members[key].decode("utf-8-sig"))
        changed = []
        for card in data.get("registries", {}).get("cards", []) or []:
            name = str(card.get("name_en") or "")
            texts = lookup(name)
            if not texts:
                continue
            i18n = card.get("effect_text_i18n")
            if not isinstance(i18n, dict):
                i18n = {}
            zh_text = texts.get("zh")
            if zh_text:
                i18n["zh"] = zh_text
                card["effect_text"] = zh_text
                document = locales.get("zh")
                if isinstance(document, dict):
                    entry = (document.get("cards") or {}).get(card.get("id"))
                    if isinstance(entry, dict):
                        entry["effect_text"] = zh_text
            en_text = i18n.get("en") or str(card.get("effect_text") or "")
            # Only touch cards whose target language slots still repeat the
            # English source (or a Chinese placeholder in the English slot).
            def needs(lang):
                current = (i18n.get(lang) or "")
                if not current:
                    return True
                if current.strip() == en_text.strip():
                    return True
                return lang == "en" and any("\u4e00" <= ch <= "\u9fff" for ch in current)
            for lang in LANGS:
                value = texts.get(lang)
                if not value or not (needs(lang) or name in FORCE_NAMES):
                    continue
                i18n[lang] = value
                document = locales.get(lang)
                if isinstance(document, dict):
                    entry = (document.get("cards") or {}).get(card.get("id"))
                    if isinstance(entry, dict):
                        entry["effect_text"] = value
            card["effect_text_i18n"] = i18n
            changed.append(name)
            members["mod.json"] = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        if not changed:
            continue
        for lang, document in locales.items():
            members["locales/%s.json" % lang] = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
        write_package(path, members)
        patched.extend(changed)
        print("patched", path.name, "->", len(changed), "cards")
    missing = sorted(set(ALL_NAMES) - set(patched))
    print("total", len(set(patched)), "cards; missing:", missing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
