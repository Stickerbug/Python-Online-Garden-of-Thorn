# -*- coding: utf-8 -*-
"""Insert the missing space after [[icon:...]] markup in Latin-language text.

Older machine translations glued markup to the following word
(``Deal 8[[icon:D]]to the target``). Japanese keeps its own spacing rules, so
only English and French are touched.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"
LANGS = ("en", "fr")
FIELDS = ("effect_text", "description", "trigger_effect_text", "response_title", "response_content")
PATTERN = re.compile(r"\]\](?=[A-Za-zÀ-ÖØ-öø-ÿ])")


def fix(text: str) -> tuple:
    if not isinstance(text, str) or "]]" not in text:
        return text, 0
    out, count = PATTERN.subn("]] ", text)
    return out, count


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
    total = 0
    for path in sorted(MODS.glob("*.gtnmod")):
        with zipfile.ZipFile(path, "r") as zf:
            members = {item.filename: zf.read(item.filename) for item in zf.infolist()}
        data = json.loads(members["mod.json"].decode("utf-8-sig"))
        counts = {}
        for card in data.get("registries", {}).get("cards", []) or []:
            i18n = card.get("effect_text_i18n")
            if isinstance(i18n, dict):
                for lang in LANGS:
                    value, hits = fix(i18n.get(lang))
                    if hits:
                        i18n[lang] = value
                        counts[lang] = counts.get(lang, 0) + hits
        for lang, document in (
            (lang, json.loads(members["locales/%s.json" % lang].decode("utf-8-sig")))
            for lang in LANGS
            if "locales/%s.json" % lang in members
        ):
            for entry in (document.get("cards") or {}).values():
                if not isinstance(entry, dict):
                    continue
                for field in FIELDS:
                    value, hits = fix(entry.get(field))
                    if hits:
                        entry[field] = value
                        counts[lang] = counts.get(lang, 0) + hits
            members["locales/%s.json" % lang] = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
        if not counts:
            continue
        members["mod.json"] = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        write_package(path, members)
        total += sum(counts.values())
        print("fixed", path.name, counts)
    print("total fixes", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
