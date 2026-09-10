# -*- coding: utf-8 -*-
"""Apply the verification-report fixes to already-converted card data.

1. ``deal_damage`` callbacks that only apply statuses must run once per damaged
   player (``on_hit_once``) instead of once per hit.
2. ``give_card_to_hand`` of ``void:void`` must skip silently when the card is
   not registered instead of inserting the Error card.
3. Capacitor-style whole-hand charge ignores the ``selectable`` filter.
"""

import io
import json
import pathlib
import sys
import zipfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.refactor_card_atoms import write_package  # noqa: E402

STATUS_OPS = {"status_add_named", "apply_jungle_status", "set_status_named", "clear_status"}


def migrate(node, stats, card_id):
    if isinstance(node, dict):
        if node.get("op") == "deal_damage":
            on_hit = node.get("on_hit")
            if isinstance(on_hit, list) and on_hit and all(
                isinstance(child, dict) and str(child.get("op")) in STATUS_OPS for child in on_hit
            ):
                node["on_hit_once"] = on_hit
                node.pop("on_hit", None)
                stats["on_hit_once"] += 1
                stats["cards"].add(card_id)
        if node.get("op") == "give_card_to_hand" and node.get("card") == "void:void":
            node["missing"] = "skip"
            stats["void_missing"] += 1
            stats["cards"].add(card_id)
        if (
            node.get("op") == "card_prop_add_to_zone"
            and node.get("property") == "charge_value"
            and node.get("target") == "play_targets"
        ):
            node["require_selectable"] = False
            stats["charge_filter"] += 1
            stats["cards"].add(card_id)
        for value in node.values():
            migrate(value, stats, card_id)
    elif isinstance(node, list):
        for value in node:
            migrate(value, stats, card_id)


total = {key: 0 for key in ("on_hit_once", "void_missing", "charge_filter")}
cards = set()
for package in sorted((ROOT / "mods").glob("*.gtnmod")):
    with zipfile.ZipFile(package) as archive:
        members = {item.filename: archive.read(item.filename) for item in archive.infolist()}
    spec = json.loads(members["mod.json"].decode("utf-8-sig"))
    before = json.dumps(spec, ensure_ascii=False)
    stats = {key: 0 for key in total}
    stats["cards"] = set()
    for card in (spec.get("registries") or {}).get("cards") or []:
        migrate(card, stats, card.get("legacy_id") or card.get("id"))
    after = json.dumps(spec, ensure_ascii=False)
    if before == after:
        continue
    for key in total:
        total[key] += stats[key]
    cards |= stats["cards"]
    members["mod.json"] = json.dumps(spec, ensure_ascii=False, indent=2).encode("utf-8")
    write_package(package, members)
    print("migrated", package.name, "->", ", ".join(sorted(stats["cards"])))
print("totals:", total)
print("cards touched:", len(cards))
