# -*- coding: utf-8 -*-
"""One-off: point Cyanide Pill's clear_status steps at the wide-strike target set."""

import io, json, pathlib, sys, zipfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.refactor_card_atoms import write_package  # noqa: E402

package = ROOT / "mods" / "Bio Cards DLC.gtnmod"
with zipfile.ZipFile(package) as archive:
    members = {item.filename: archive.read(item.filename) for item in archive.infolist()}
spec = json.loads(members["mod.json"].decode("utf-8-sig"))
changed = 0
for card in spec["registries"]["cards"]:
    if card.get("legacy_id") != "CyanidePill":
        continue
    for group in (card.get("events") or {}).values():
        for step in (group.get("steps") if isinstance(group, dict) else []) or []:
            if isinstance(step, dict) and step.get("op") == "clear_status":
                step["target"] = "wide_strike_targets"
                changed += 1
    print(json.dumps(card.get("events"), ensure_ascii=False))
if changed:
    members["mod.json"] = json.dumps(spec, ensure_ascii=False, indent=2).encode("utf-8")
    write_package(package, members)
print("patched steps:", changed)
