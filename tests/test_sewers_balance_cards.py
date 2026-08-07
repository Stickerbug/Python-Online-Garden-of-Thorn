import unittest
from pathlib import Path

from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "mods" / "Sewers Cards DLC.gtnmod"
CARD_IDS = {"Cheese", "Perfume"}


class SewersBalanceCardsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_mod(str(PACKAGE))
        if cls.mod.errors:
            raise AssertionError(cls.mod.errors)
        cls.mod_cards = {card.id: card for card in cls.mod.cards}

    def setUp(self):
        self.previous_defs = {card_id: CARD_DEFS.get(card_id) for card_id in CARD_IDS}
        for card_id in CARD_IDS:
            CARD_DEFS[card_id] = self.mod_cards[card_id].to_card_def()

    def tearDown(self):
        for card_id, previous in self.previous_defs.items():
            if previous is None:
                CARD_DEFS.pop(card_id, None)
            else:
                CARD_DEFS[card_id] = previous

    @staticmethod
    def action_engine(engine_type=GameEngine):
        engine = engine_type()
        engine.phase = "action"
        engine.current_player = 0
        for player in engine.players:
            player.hand = []
            player.deck = []
            player.discard = []
            player.exile = []
            player.equipment = []
            player.elixir = 50
            player.magic = 50
            player.health = 100
            player.max_health = 100
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

    def equip_cheese(self, engine):
        cheese = CardInstance("Cheese")
        engine.players[0].hand = [cheese]
        if isinstance(engine, GameEngine2v2):
            result = engine.play_card(0, cheese.instance_id, None, {})
        else:
            result = engine.play_card(0, cheese.instance_id, {})
        self.assertTrue(result.get("success"), result)
        self.assertEqual(len(engine.players[0].equipment), 1)
        return engine.players[0].equipment[0]

    def counter_player_zero(self, engine, responder_id):
        attack = CardInstance("Basic")
        counter = CardInstance("Bubble")
        engine.current_player = 0
        engine.phase = "action"
        engine.players[0].hand = [attack]
        engine.players[responder_id].hand = [counter]
        if isinstance(engine, GameEngine2v2):
            result = engine.play_card(
                0,
                attack.instance_id,
                responder_id,
                self.target_choice(responder_id),
            )
        else:
            result = engine.play_card(0, attack.instance_id, self.target_choice(responder_id))
        self.assertTrue(result.get("needs_response"), result)
        response = engine.handle_response(responder_id, counter.instance_id)
        self.assertTrue(response.get("success"), response)

    def test_package_definitions_match_new_equipment_rules(self):
        cheese = self.mod_cards["Cheese"]
        self.assertEqual((cheese.cost_e, cheese.cost_m), (2, 0))
        self.assertEqual(cheese.card_type, "root")
        self.assertEqual(cheese.response_trigger, "")
        self.assertIn("unique", cheese.flags)
        self.assertIn("sewers:confusion", cheese.flags)
        self.assertIn("on_play", cheese.v2_events)

        perfume = self.mod_cards["Perfume"]
        self.assertIn("wide_strike", perfume.flags)
        self.assertIn("team_limited", perfume.flags)

    def test_cheese_destroys_itself_and_forces_the_countering_enemy(self):
        engine = self.action_engine()
        equipment = self.equip_cheese(engine)
        equipment.armor = 2
        engine.players[0].equipment_protection = 2

        self.counter_player_zero(engine, 1)

        self.assertEqual(engine.players[0].equipment, [])
        self.assertIn(equipment.card_instance, engine.players[0].discard)
        self.assertEqual(engine.players[0].equipment_protection, 2)
        self.assertEqual(engine.players[1].honey_control_turns, 1)
        self.assertEqual(
            engine.players[1].custom_vars.get("sewers_cheese_forced_target"),
            0,
        )

        forced_attack = CardInstance("Basic")
        engine.players[1].hand = [forced_attack]
        engine.current_player = 1
        engine.phase = "action"
        before = engine.players[0].health
        engine._continue_honey_control_if_needed(1)
        self.assertLess(engine.players[0].health, before)
        self.assertNotIn(forced_attack, engine.players[1].hand)
        self.assertEqual(engine.players[1].honey_control_turns, 0)

    def test_2v2_cheese_keeps_the_equipment_holder_as_fixed_target(self):
        engine = self.action_engine(GameEngine2v2)
        self.equip_cheese(engine)
        self.counter_player_zero(engine, 2)

        engine.players[0].health = 100
        engine.players[1].health = 1
        forced_attack = CardInstance("Basic")
        engine.players[2].hand = [forced_attack]
        engine.current_player = 2
        engine.phase = "action"
        owner_before = engine.players[0].health
        teammate_before = engine.players[1].health

        engine._continue_honey_control_if_needed(2)

        self.assertLess(engine.players[0].health, owner_before)
        self.assertEqual(engine.players[1].health, teammate_before)


if __name__ == "__main__":
    unittest.main()
