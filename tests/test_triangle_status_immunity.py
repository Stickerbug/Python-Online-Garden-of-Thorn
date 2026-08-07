from pathlib import Path

import pytest

from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("initial_stacks", "stacks_after_immune_play", "damage_after_immunity"),
    [(2, 3, 15), (4, 4, 18)],
)
def test_triangle_preserves_real_stacks_while_status_immunity_suppresses_damage(
    initial_stacks,
    stacks_after_immune_play,
    damage_after_immunity,
):
    vanilla = load_mod(str(ROOT / "mods" / "Vanilla Cards.gtnmod"))
    assert not vanilla.errors
    triangle_def = next(card for card in vanilla.cards if card.id == "Triangle").to_card_def()
    previous = CARD_DEFS["Triangle"]
    CARD_DEFS["Triangle"] = triangle_def
    try:
        engine = GameEngine()
        engine.phase = "action"
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.max_health = 100
            player.elixir = 100
            player.magic = 100
            player.hand = []
            player.deck = []
            player.discard = []
            player.exile = []
            player.equipment = []
            player.custom_vars = {}
            player.custom_statuses = {}

        attacker = engine.players[0]
        target = engine.players[1]
        attacker.triangle_stacks = initial_stacks
        attacker.custom_vars["三角形层数"] = initial_stacks
        attacker.custom_statuses["status_immune"] = 1

        immune_triangle = CardInstance("Triangle")
        attacker.hand = [immune_triangle]
        result = engine.play_card(0, immune_triangle.instance_id, {"target_player": 1})

        assert result["success"]
        assert target.health == 94
        assert attacker.triangle_stacks == stacks_after_immune_play
        assert attacker.custom_vars["三角形层数"] == stacks_after_immune_play

        attacker.custom_statuses.clear()
        normal_triangle = CardInstance("Triangle")
        attacker.hand = [normal_triangle]
        health_before = target.health
        result = engine.play_card(0, normal_triangle.instance_id, {"target_player": 1})

        assert result["success"]
        assert health_before - target.health == damage_after_immunity
    finally:
        CARD_DEFS["Triangle"] = previous
