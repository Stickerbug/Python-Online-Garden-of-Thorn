# -*- coding: utf-8 -*-
import io, json, pathlib, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import app
import mod_loader
from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine

mod_loader.merge_mod_cards_to_card_defs()
loadout = app.build_mod_loadout()
engine = GameEngine()
app.apply_v2_loadout_to_engine(engine, {"v2_loadout": loadout["v2_loadout"],
                                        "v2_ui_components": loadout["v2_ui_components"]})
engine.phase = "action"
engine.current_player = 0
for player in engine.players:
    player.hand = []
    player.deck = [CardInstance("Sewage") for _ in range(6)]
    player.discard = []
    player.exile = []
    player.equipment = []
    player.health = 100
    player.max_health = 100
    player.elixir = 99
    player.magic = 99
    player.custom_statuses = {}
    player.custom_vars = {}
print(json.dumps(CARD_DEFS["Lightning"].v2_events, ensure_ascii=False))
card = CardInstance("Lightning")
engine.players[0].hand = [card]
engine.players[1].hand = [CardInstance("Sewage") for _ in range(3)]
result = engine.play_card(0, card.instance_id, {})
print("play:", {k: v for k, v in result.items() if k != "card"})
while engine.pending_choice is not None:
    pending = engine.pending_choice
    choice = engine._default_choice_for_pending(pending)
    print("choice:", pending.get("choice_type"), json.dumps(choice, ensure_ascii=False)[:200])
    result = engine.resolve_choice(0, choice)
    print("  ->", {k: v for k, v in result.items() if k not in ("card", "state")})
print("self health:", engine.players[0].health)
print("target hand charges:", [(c.def_id, c.charge_value) for c in engine.players[1].hand])
print("log:", engine.log[-6:])
