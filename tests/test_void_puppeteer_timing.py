import unittest
from pathlib import Path
from unittest.mock import patch

from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "mods" / "Void Card Addition.gtnmod"


def target_choice(player_id):
    return {
        "target_player": player_id,
        "target_player_id": player_id,
        "target_id": player_id,
    }


class VoidPuppeteerTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mod = load_mod(str(PACKAGE))
        if mod.errors:
            raise AssertionError(mod.errors)
        cls.puppeteer_def = next(card for card in mod.cards if card.id == "Puppeteer").to_card_def()

    def setUp(self):
        self.previous_def = CARD_DEFS.get("Puppeteer")
        CARD_DEFS["Puppeteer"] = self.puppeteer_def

    def tearDown(self):
        if self.previous_def is None:
            CARD_DEFS.pop("Puppeteer", None)
        else:
            CARD_DEFS["Puppeteer"] = self.previous_def

    @staticmethod
    def action_engine(engine_type=GameEngine):
        engine = engine_type()
        engine.phase = "action"
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.max_health = 100
            player.elixir = 20
            player.magic = 20
            player.hand = []
            player.deck = []
            player.discard = []
            player.exile = []
            player.equipment = []
            player.custom_statuses = {}
            player.custom_vars = {}
            player.honey_control_turns = 0
        return engine

    @staticmethod
    def play(engine, card, target_id):
        choice = target_choice(target_id)
        if isinstance(engine, GameEngine2v2):
            return engine.play_card(0, card.instance_id, target_id, choice)
        return engine.play_card(0, card.instance_id, choice)

    def test_passing_magic_bubble_window_does_not_activate_self_target_immediately(self):
        engine = self.action_engine()
        puppeteer = CardInstance("Puppeteer")
        engine.players[0].hand = [puppeteer]
        engine.players[1].hand = [CardInstance("MagicBubble")]

        result = self.play(engine, puppeteer, 0)
        self.assertTrue(result.get("needs_response"), result)
        resolved = engine.handle_response(1, None)

        self.assertTrue(resolved.get("success"), resolved)
        self.assertEqual(engine.current_player, 0)
        self.assertEqual(engine.players[0].honey_control_turns, 0)
        self.assertEqual(engine.players[0].custom_vars.get("void_puppeteer_pending_turns"), 1)
        self.assertNotIn("void_puppeteer_damage_multiplier", engine.players[0].custom_vars)

    def test_magic_nazar_response_still_queues_puppeteer_for_next_turn(self):
        engine = self.action_engine()
        puppeteer = CardInstance("Puppeteer")
        magic_nazar = CardInstance("MagicNazar")
        engine.players[0].hand = [puppeteer]
        engine.players[1].hand = [magic_nazar]

        result = self.play(engine, puppeteer, 0)
        self.assertTrue(result.get("needs_response"), result)
        resolved = engine.handle_response(1, magic_nazar.instance_id)

        self.assertTrue(resolved.get("success"), resolved)
        self.assertEqual(engine.current_player, 0)
        self.assertEqual(engine.players[0].honey_control_turns, 0)
        self.assertEqual(engine.players[0].custom_vars.get("void_puppeteer_pending_turns"), 1)
        self.assertNotIn("void_puppeteer_damage_multiplier", engine.players[0].custom_vars)

    def test_pending_puppeteer_activates_when_target_enters_action_phase(self):
        engine = self.action_engine()
        target = engine.players[1]
        target.custom_vars["void_puppeteer_pending_turns"] = 1
        engine.current_player = 1

        with patch.object(engine, "_continue_turn_start_auto_settlement") as continue_settlement:
            engine._enter_player_action_phase(1)

        self.assertEqual(target.honey_control_turns, 1)
        self.assertEqual(target.custom_vars.get("void_puppeteer_damage_multiplier"), 1.5)
        self.assertTrue(target.custom_vars.get("honey_lowest_enemy"))
        self.assertNotIn("void_puppeteer_pending_turns", target.custom_vars)
        continue_settlement.assert_called_once_with(1)

    def test_2v2_response_resume_does_not_activate_self_target_immediately(self):
        engine = self.action_engine(GameEngine2v2)
        puppeteer = CardInstance("Puppeteer")
        engine.players[0].hand = [puppeteer]
        engine.players[2].hand = [CardInstance("MagicBubble")]

        result = self.play(engine, puppeteer, 0)
        self.assertTrue(result.get("needs_response"), result)
        resolved = engine.handle_response(2, None)

        self.assertTrue(resolved.get("success"), resolved)
        self.assertEqual(engine.current_player, 0)
        self.assertEqual(engine.players[0].honey_control_turns, 0)
        self.assertEqual(engine.players[0].custom_vars.get("void_puppeteer_pending_turns"), 1)


if __name__ == "__main__":
    unittest.main()
