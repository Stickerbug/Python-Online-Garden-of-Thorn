# -*- coding: utf-8 -*-
"""List every void_dlc_action call site with its action name and full step."""

import io, json, pathlib, sys, zipfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"


def walk(node, hits, path=""):
    if isinstance(node, dict):
        if node.get("op") == "void_dlc_action":
            hits.append((path, node))
        for key, value in node.items():
            walk(value, hits, "%s.%s" % (path, key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            walk(value, hits, "%s[%d]" % (path, index))


groups = {}
for package in sorted(MODS.glob("*.gtnmod")):
    with zipfile.ZipFile(package) as archive:
        spec = json.loads(archive.read("mod.json"))
    for card in (spec.get("registries") or {}).get("cards") or []:
        if not isinstance(card, dict):
            continue
        hits = []
        walk({"events": card.get("events") or {}}, hits)
        for path, step in hits:
            action = str(step.get("action"))
            groups.setdefault(action, []).append(
                (package.name, card.get("legacy_id") or card.get("id"), path, json.dumps(step, ensure_ascii=False))
            )
for action in sorted(groups):
    print("== %s (%d)" % (action, len(groups[action])))
    for package, card_id, path, step in groups[action]:
        print("   %-28s %-18s %s" % (card_id, package.replace(".gtnmod", ""), step))
