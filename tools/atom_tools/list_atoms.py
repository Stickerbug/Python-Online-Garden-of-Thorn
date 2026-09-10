# -*- coding: utf-8 -*-
"""List engine atoms that still look card/package specific, grouped by prefix."""

import io, re, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

FILES = ("game_engine.py", "game_engine_2v2.py", "game_engine_urf.py")
PREFIXES = (
    "hel", "arctic", "jungle", "bio", "ocean", "desert", "sewers", "garden",
    "jurassic", "void", "factory", "vanilla",
)

names = set()
where = collections.defaultdict(set)
for filename in FILES:
    src = open(filename, encoding="utf-8").read()
    for match in re.finditer(r"def _atomic_([A-Za-z0-9_]+)\(", src):
        names.add(match.group(1))
        where[match.group(1)].add(filename)

groups = collections.defaultdict(list)
for name in sorted(names):
    head = name.split("_")[0]
    groups[head if head in PREFIXES else "(generic)"].append(name)

total = 0
for key in sorted(groups):
    if key == "(generic)":
        continue
    entries = groups[key]
    total += len(entries)
    print("== %s (%d)" % (key, len(entries)))
    for name in entries:
        print("   ", name)
print("card-specific total:", total, " generic:", len(groups.get("(generic)", [])))
