# -*- coding: utf-8 -*-
import io, json, pathlib, sys, zipfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"
WANT = set(sys.argv[1:])
for package in sorted(MODS.glob("*.gtnmod")):
    with zipfile.ZipFile(package) as archive:
        spec = json.loads(archive.read("mod.json"))
    for card in (spec.get("registries") or {}).get("cards") or []:
        if not isinstance(card, dict):
            continue
        if (card.get("legacy_id") or card.get("id")) not in WANT:
            continue
        print("==", card.get("legacy_id"), "type:", card.get("card_type"), "flags:", card.get("flags"))
        print(json.dumps(card.get("events"), ensure_ascii=False))
