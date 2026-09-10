# -*- coding: utf-8 -*-
"""Dump one card resource (by legacy id or substring) from its package."""

import io, json, pathlib, sys, zipfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"

needle = sys.argv[1]
package_filter = sys.argv[2] if len(sys.argv) > 2 else ""
for package in sorted(MODS.glob("*.gtnmod")):
    if package_filter and package_filter not in package.name:
        continue
    with zipfile.ZipFile(package) as archive:
        spec = json.loads(archive.read("mod.json"))
    for card in (spec.get("registries") or {}).get("cards") or []:
        if not isinstance(card, dict):
            continue
        ids = "%s %s %s" % (card.get("id", ""), card.get("legacy_id", ""), card.get("name_cn", ""))
        if needle.lower() in ids.lower():
            print("#", package.name, card.get("id"), card.get("legacy_id"))
            print(json.dumps(card, ensure_ascii=False, indent=1))
