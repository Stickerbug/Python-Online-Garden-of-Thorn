# -*- coding: utf-8 -*-
import io, sys, pathlib, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import mod_loader
from cards import CARD_DEFS

mod_loader.merge_mod_cards_to_card_defs()
by_type = collections.defaultdict(list)
for card_id, card_def in CARD_DEFS.items():
    by_type[getattr(card_def, "card_type", "")].append(
        (card_id, getattr(card_def, "cost_e", 0), getattr(card_def, "cost_m", 0), getattr(card_def, "count", 0))
    )
for card_type, entries in sorted(by_type.items()):
    free = [e[0] for e in entries if not e[1] and not e[2]]
    print("%-8s n=%-4d free=%s" % (card_type, len(entries), free[:6]))
print("Fusion type:", CARD_DEFS["Fusion"].card_type, "count:", CARD_DEFS["Fusion"].count)
