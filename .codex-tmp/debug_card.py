# -*- coding: utf-8 -*-
"""Debug one card: print its v2 events and trace pending prompts."""

import io
import json
import pathlib
import sys
import traceback

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app
import mod_loader
from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine
from smoke_all_cards import repair_choice, auto_v2_ui_values, type_samples

CARD_ID = sys.argv[1] if len(sys.argv) > 1 else "Fission"

mod_loader.merge_mod_cards_to_card_defs()
loadout = app.build_mod_loadout()
player_meta = {
    "v2_loadout": loadout["v2_loadout"],
    "v2_ui_components": loadout["v2_ui_components"],
}

card_def = CARD_DEFS[CARD_ID]
print("card:", CARD_ID, "type:", card_def.card_type)
print(json.dumps(card_def.v2_events, ensure_ascii=False, indent=1)[:4000])

engine = GameEngine()
app.apply_v2_loadout_to_engine(engine, player_meta)
engine.phase = "action"
engine.current_player = 0
for player in engine.players:
    player.hand = []
    player.deck = [CardInstance("Sewage") for _ in range(6)]
    player.discard = [CardInstance("Sewage") for _ in range(3)]
    player.exile = []
    player.equipment = []
    player.health = 100
    player.max_health = 100
    player.elixir = 99
    player.magic = 99
card = CardInstance(CARD_ID)
engine.players[0].hand = [card] + [CardInstance(s) for s in type_samples(CARD_ID) for _ in range(2)]
print("hand:", [c.def_id for c in engine.players[0].hand])
print("play result:", engine.play_card(0, card.instance_id, {}))
for step in range(12):
    if getattr(engine, "pending_v2_ui", None):
        pending = engine.pending_v2_ui
        print(step, "v2ui", pending.get("component_id"), json.dumps(pending.get("component"), ensure_ascii=False)[:500])
        break
    if engine.pending_choice is not None:
        pending = engine.pending_choice
        print(step, "choice", pending.get("choice_type"), json.dumps(pending.get("choice_params"), ensure_ascii=False)[:300])
        choice = engine._default_choice_for_pending(pending)
        choice = repair_choice(engine, pending, choice)
        result = engine.resolve_choice(int(pending.get("player_id", 0)), choice)
        print("   ->", json.dumps(choice, ensure_ascii=False)[:200],
              result if not isinstance(result, dict) else {k: v for k, v in result.items() if k not in ("state", "card")})
        continue
    if engine.pending_response is not None:
        print(step, "response")
        engine.handle_response(1, None)
        continue
    print(step, "idle")
    break
