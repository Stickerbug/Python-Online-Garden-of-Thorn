# -*- coding: utf-8 -*-
"""Make mod.json inline card text match locales/zh.json for a card.

The encyclopedia and the battle UI read ``locales/zh.json`` while the mod
editor reads the inline ``effect_text`` field, so both must stay identical.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", help="package filename inside mods/")
    parser.add_argument("card_ids", nargs="+", help="raw card ids inside the package")
    args = parser.parse_args()
    path = ROOT / "mods" / args.package
    with zipfile.ZipFile(path, "r") as zf:
        members = {item.filename: zf.read(item.filename) for item in zf.infolist()}
    data = json.loads(members["mod.json"].decode("utf-8-sig"))
    locale = json.loads(members["locales/zh.json"].decode("utf-8-sig"))
    changed = 0
    for card in data.get("registries", {}).get("cards", []) or []:
        if card.get("id") not in args.card_ids:
            continue
        entry = (locale.get("cards") or {}).get(card.get("id")) or {}
        text = entry.get("effect_text")
        if not text:
            continue
        card["effect_text"] = text
        i18n = card.get("effect_text_i18n")
        if not isinstance(i18n, dict):
            i18n = {}
        i18n["zh"] = text
        card["effect_text_i18n"] = i18n
        changed += 1
    if not changed:
        print("nothing to sync")
        return 0
    members["mod.json"] = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    handle, temp_name = tempfile.mkstemp(suffix=".gtnmod", dir=str(path.parent))
    os.close(handle)
    temp_path = pathlib.Path(temp_name)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for member, content in members.items():
                zf.writestr(member, content)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    print("synced", changed, "cards in", args.package)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
