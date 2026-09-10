# -*- coding: utf-8 -*-
import io, json, pathlib, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import mod_loader
from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine

mod_loader.merge_mod_cards_to_card_defs()
package = pathlib.Path(__file__).resolve().parents[1] / "mods" / "Bio Cards Addition.gtnmod"
mod = mod_loader.load_mod(str(package))
for mod_card in mod.cards:
    CARD_DEFS[mod_card.id] = mod_card.to_card_def()
print("steps:", json.dumps(CARD_DEFS["bio:diamond"].v2_events, ensure_ascii=False)[:600])
engine = GameEngine()
engine.phase = "action"
engine.current_player = 0
engine.players[0].elixir = 20
engine.players[0].magic = 20
engine.players[1].health = 100
card = CardInstance("bio:diamond")
engine.players[0].hand = [card]
result = engine.play_card(0, card.instance_id, {"target_player": 1, "target_player_id": 1, "target_id": 1})
print("result:", {k: v for k, v in result.items() if k not in ("card", "state")})
while engine.pending_choice is not None:
    pending = engine.pending_choice
    choice = engine._default_choice_for_pending(pending)
    print("pending:", pending.get("choice_type"), choice)
    engine.resolve_choice(0, choice or {})
print("health:", engine.players[1].health)
print("hand:", [c.def_id for c in engine.players[0].hand])
print("log:", [entry[:60] for entry in engine.log[-4:]])
