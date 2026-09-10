# -*- coding: utf-8 -*-
import io, json, pathlib, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import mod_loader
from cards import CARD_DEFS

mod_loader.merge_mod_cards_to_card_defs()
card_id = sys.argv[1]
print(json.dumps(CARD_DEFS[card_id].v2_events, ensure_ascii=False, indent=1))
