# -*- coding: utf-8 -*-
"""Find which cards call the given v2 ops and print the call parameters."""

import io
import json
import pathlib
import sys
import zipfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"


def walk(node, op, path, hits):
    if isinstance(node, dict):
        if node.get("op") == op:
            hits.append((path, node))
        for key, value in node.items():
            walk(value, op, "%s.%s" % (path, key), hits)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            walk(value, op, "%s[%d]" % (path, index), hits)


def main():
    targets = set(sys.argv[1:])
    for package in sorted(MODS.glob("*.gtnmod")):
        with zipfile.ZipFile(package) as archive:
            names = [n for n in archive.namelist() if n.endswith("mod.json")]
            if not names:
                continue
            spec = json.loads(archive.read(names[0]))
        registries = spec.get("registries") or {}
        for area, items in registries.items():
            if isinstance(items, dict):
                entries = list(items.items())
            elif isinstance(items, list):
                entries = [
                    (str(item.get("id") or item.get("legacy_id") or index), item)
                    for index, item in enumerate(items)
                    if isinstance(item, dict)
                ]
            else:
                continue
            for resource_id, resource in entries:
                if not isinstance(resource, dict):
                    continue
                for target in targets:
                    hits = []
                    walk(resource, target, "%s:%s" % (area, resource_id), hits)
                    for path, step in hits:
                        print("%-32s %-40s %s" % (package.name, path, json.dumps(step, ensure_ascii=False)))


if __name__ == "__main__":
    main()
