# -*- coding: utf-8 -*-
import io, sys, inspect, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import mod_loader

print(inspect.signature(mod_loader.load_all_mods))
print(inspect.signature(mod_loader.merge_mod_cards_to_card_defs))
print(inspect.getsource(mod_loader.merge_mod_cards_to_card_defs)[:1500])
mods = mod_loader.load_all_mods()
print("mods:", len(mods))
total = 0
for mod in mods:
    cards = getattr(mod, "cards", None)
    if cards:
        total += len(cards)
print("total cards:", total)
print("errors:", [(m.info.filename, m.errors) for m in mods if getattr(m, "errors", None)])
