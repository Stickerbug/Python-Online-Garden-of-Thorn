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
    player.discard = [CardInstance("Sewage") for _ in range(3)]
    player.exile = []
    player.equipment = []
    player.health = 100
    player.max_health = 100
    player.elixir = 99
    player.magic = 99
fused = CardInstance("Fusion")
from smoke_all_cards import type_samples

samples = [CardInstance(s) for s in type_samples("Fusion") for _ in range(2)]
print("samples:", [c.def_id for c in samples])
engine.players[0].hand = [fused] + samples + [CardInstance("Sewage")]
print("play:", engine.play_card(0, fused.instance_id, {}).get("choice_type"))
pending = engine.pending_choice
print("pending keys:", sorted(pending.keys()))
print("params:", json.dumps(pending.get("choice_params"), ensure_ascii=False))
print("hand:", [(c.def_id, c.instance_id, c.card_type,
                 engine._card_selectable_by_action(c)) for c in engine.players[0].hand])
print("default:", engine._default_choice_for_pending(pending))
from smoke_all_cards import repair_choice

repaired = repair_choice(engine, pending, engine._default_choice_for_pending(pending))
print("repaired:", repaired)
result = engine.resolve_choice(0, repaired)
print("resolve:", {k: v for k, v in result.items() if k not in ("state", "card")})
print("after hand:", [c.def_id for c in engine.players[0].hand])
print("pending now:", engine.pending_choice and engine.pending_choice.get("choice_type"))
