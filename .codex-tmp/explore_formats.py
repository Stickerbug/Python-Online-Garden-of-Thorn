# -*- coding: utf-8 -*-
import io, sys, pathlib, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import mod_loader

mods = mod_loader.load_all_mods()
counts = collections.Counter()
for mod in mods:
    counts[getattr(mod, "format_version", 1)] += 1
print("format versions:", dict(counts))
for mod in mods:
    print(getattr(mod, "format_version", 1), mod.filename, len(mod.cards))
