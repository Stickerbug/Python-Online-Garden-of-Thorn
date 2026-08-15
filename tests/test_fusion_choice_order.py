import unittest
from pathlib import Path

from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
VANILLA_PACKAGE = ROOT / "mods" / "Vanilla Cards.gtnmod"


class FusionChoiceOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mod = load_mod(str(VANILLA_PACKAGE))
        if mod.errors:
            raise AssertionError(mod.errors)
        cls.mod_cards = {card.id: card for card in mod.cards}

    def setUp(self):
        self.previous_defs = {card_id: CARD_DEFS.get(card_id) for card_id in ("Fusion", "Basic", "Bone")}
        for card_id in self.previous_defs:
            CARD_DEFS[card_id] = self.mod_cards[card_id].to_card_def()

    def tearDown(self):
        for card_id, previous in self.previous_defs.items():
            if previous is None:
                CARD_DEFS.pop(card_id, None)
            else:
                CARD_DEFS[card_id] = previous

    @staticmethod
    def engine_with_cards(*cards):
        engine = GameEngine()
        engine.phase = "action"
        engine.current_player = 0
        engine.players[0].hand = list(cards)
        engine.players[0].deck = []
        engine.players[0].discard = []
        engine.players[0].exile = []
        engine.players[0].equipment = []
        engine.players[0].elixir = 20
        engine.players[0].magic = 20
        return engine

    def test_first_selected_card_is_the_surviving_base(self):
        fusion = CardInstance("Fusion")
        plain = CardInstance("Basic")
        symbiotic = CardInstance("Basic")
        symbiotic.instance_flags.add("symbiosis")
        plain.fission_level = 2
        symbiotic.fission_level = 4
        engine = self.engine_with_cards(fusion, plain, symbiotic)

        result = engine.play_card(
            0,
            fusion.instance_id,
            {"target_instance_ids": [symbiotic.instance_id, plain.instance_id]},
        )

        self.assertTrue(result.get("success"), result)
        self.assertEqual([card.instance_id for card in engine.players[0].hand], [symbiotic.instance_id])
        self.assertIn("symbiosis", engine.players[0].hand[0].instance_flags)
        self.assertEqual(engine.players[0].hand[0].fission_level, 4)
        self.assertEqual(engine.players[0].hand[0].fusion_level, 2)
        self.assertIn(plain.instance_id, [card.instance_id for card in engine.players[0].discard])

    def test_reversing_selection_reverses_which_tags_survive(self):
        fusion = CardInstance("Fusion")
        plain = CardInstance("Basic")
        symbiotic = CardInstance("Basic")
        symbiotic.instance_flags.add("symbiosis")
        engine = self.engine_with_cards(fusion, plain, symbiotic)

        result = engine.play_card(
            0,
            fusion.instance_id,
            {"target_instance_ids": [plain.instance_id, symbiotic.instance_id]},
        )

        self.assertTrue(result.get("success"), result)
        self.assertEqual([card.instance_id for card in engine.players[0].hand], [plain.instance_id])
        self.assertNotIn("symbiosis", engine.players[0].hand[0].instance_flags)

    def test_rejects_invalid_fusion_pairs(self):
        fusion = CardInstance("Fusion")
        basic = CardInstance("Basic")
        bone = CardInstance("Bone")
        engine = self.engine_with_cards(fusion, basic, bone)

        result = engine.play_card(
            0,
            fusion.instance_id,
            {"target_instance_ids": [basic.instance_id, bone.instance_id]},
        )

        self.assertTrue(result.get("needs_choice"), result)
        self.assertIn(fusion, engine.players[0].hand)

    def test_client_and_training_worker_preserve_order(self):
        game_js = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")
        worker_js = (ROOT / "static" / "js" / "local_solo_worker.js").read_text(encoding="utf-8")
        self.assertIn("chooseOrderedFusionCards", game_js)
        self.assertIn("选择聚变后保留的牌", game_js)
        self.assertIn("_selected_card_ids_snapshot", worker_js)


if __name__ == "__main__":
    unittest.main()
