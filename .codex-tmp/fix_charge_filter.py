# -*- coding: utf-8 -*-
"""Undo the over-broad charge-filter change: only whole-hand charge keeps it off.

Plasma charges *one random selectable* hand card, so it must keep the default
selectable filter; only Capacitor-style "all hand cards" ignores it.
"""

import io, json, pathlib, sys, zipfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.refactor_card_atoms import write_package  # noqa: E402


def walk(node, stats):
    if isinstance(node, dict):
        if (
            node.get("op") == "card_prop_add_to_zone"
            and node.get("property") == "charge_value"
            and (node.get("count") is not None or node.get("random"))
        ):
            if node.pop("require_selectable", None) is not None:
                stats["reverted"] += 1
        for value in node.values():
            walk(value, stats)
    elif isinstance(node, list):
        for value in node:
            walk(value, stats)


for package in sorted((ROOT / "mods").glob("*.gtnmod")):
    with zipfile.ZipFile(package) as archive:
        members = {item.filename: archive.read(item.filename) for item in archive.infolist()}
    spec = json.loads(members["mod.json"].decode("utf-8-sig"))
    before = json.dumps(spec, ensure_ascii=False)
    stats = {"reverted": 0}
    walk(spec, stats)
    if before == json.dumps(spec, ensure_ascii=False):
        continue
    members["mod.json"] = json.dumps(spec, ensure_ascii=False, indent=2).encode("utf-8")
    write_package(package, members)
    print("fixed", package.name, stats)
