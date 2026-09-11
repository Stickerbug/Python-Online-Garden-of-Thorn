"""Regression tests for the late-2026-09-11 feedback batch (#84/#85/#90/#95)."""

import unittest
from pathlib import Path

from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"
PACKAGES = (
    "Arctic Cards Addition.gtnmod",
    "Void Cards DLC.gtnmod",
    "Garden Cards Addition.gtnmod",
    "Jurassic Cards Addition.gtnmod",
    "Vanilla Cards.gtnmod",
)


class FeedbackBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.card_defs = {}
        for filename in PACKAGES:
            mod = load_mod(str(MODS / filename))
            if mod.errors:
                raise AssertionError((filename, mod.errors))
            for card in mod.cards:
                cls.card_defs[card.id] = card.to_card_def()

    def setUp(self):
        self.previous_defs = {card_id: CARD_DEFS.get(card_id) for card_id in self.card_defs}
        CARD_DEFS.update(self.card_defs)

    def tearDown(self):
        for card_id, previous in self.previous_defs.items():
            if previous is None:
                CARD_DEFS.pop(card_id, None)
            else:
                CARD_DEFS[card_id] = previous

    @staticmethod
    def action_engine(elixir=7):
        engine = GameEngine()
        engine.phase = "action"
        engine.current_player = 0
        for player in engine.players:
            player.hand = []
            player.deck = []
            player.discard = []
            player.exile = []
            player.equipment = []
            player.elixir = elixir
            player.magic = 20
            player.health = 100
            player.max_health = 100
            player.armor = 0
            player.custom_statuses = {}
            player.custom_vars = {}
        return engine

    @staticmethod
    def target_choice(target_id):
        return {
            "target_player": target_id,
            "target_player_id": target_id,
            "target_id": target_id,
        }

    def test_blueberries_applies_frost_on_every_hit(self):
        # 反馈 #85：描述是"每次造成伤害时施加3层霜冻"，4 段伤害应共 12 层。
        engine = self.action_engine()
        berry = CardInstance("Blueberries")
        engine.players[0].hand = [berry]

        result = engine.play_card(0, berry.instance_id, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[1].custom_statuses.get("arctic:frost"), 12)
        self.assertEqual(engine.players[1].health, 96)

    def test_magic_nut_spends_all_elixir_and_scales_damage(self):
        # 反馈 #95：消耗全部 E（这里 7），伤害 10 + 7×5 = 45。
        engine = self.action_engine(elixir=7)
        nut = CardInstance("MagicNut")
        engine.players[0].hand = [nut]
        engine.players[0].deck = [CardInstance("Basic"), CardInstance("Bone"), CardInstance("Leaf")]

        result = engine.play_card(0, nut.instance_id, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[0].elixir, 0)
        self.assertEqual(engine.players[1].health, 55)

    def test_soil_shuffles_five_dust_into_the_target_deck(self):
        # 反馈 #90：数据用 card_id + amount=5；原子历史上只认 card 且只加 1 张。
        engine = self.action_engine()
        soil = CardInstance("Soil")
        engine.players[0].hand = [soil]

        result = engine.play_card(0, soil.instance_id, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[1].max_health, 140)
        self.assertEqual([card.def_id for card in engine.players[1].deck], ["Dust"] * 5)

    def test_blood_turn_start_log_has_no_raw_placeholders(self):
        # 反馈 #84：`draw` 原子直接把 log 模板打进战报。
        engine = self.action_engine()
        blood = CardInstance("Blood")
        engine.players[0].hand = [blood]
        engine.play_card(0, blood.instance_id, self.target_choice(1))

        engine.end_turn(0)
        engine.end_turn(1)

        blood_lines = [line for line in engine.log if "因血" in line]
        self.assertTrue(blood_lines, engine.log[-6:])
        for line in blood_lines:
            self.assertNotIn("{target}", line)
            self.assertNotIn("{amount}", line)


if __name__ == "__main__":
    unittest.main()
