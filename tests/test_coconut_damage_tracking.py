import unittest
from pathlib import Path

from cards import CARD_DEFS, CardInstance
from damage_types import (
    DAMAGE_TAG_FRACTURE,
    DAMAGE_TAG_PHYSICAL,
    DAMAGE_TYPE_MAGIC,
    DAMAGE_TYPE_PHYSICAL,
)
from game_engine import EquipmentInstance, GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "mods" / "Desert Cards Addition.gtnmod"
CARD_IDS = {"Coconut", "MagicSalt"}


class CoconutDamageTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mod = load_mod(str(PACKAGE))
        if mod.errors:
            raise AssertionError(mod.errors)
        cls.mod_cards = {card.id: card for card in mod.cards}

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
            player.health = 100
            player.max_health = 100
            player.elixir = 30
            player.magic = 30
            player.hand = []
            player.deck = []
            player.discard = []
            player.exile = []
            player.equipment = []
            player.custom_statuses = {}
            player.custom_vars = {}
        return engine

    @staticmethod
    def equip_for_target(engine, card_id, owner_id, target_id):
        equipment = EquipmentInstance(CardInstance(card_id), owner_id)
        equipment.effect_target = target_id
        engine.players[owner_id].equipment.append(equipment)
        return equipment

    def test_fracture_damage_from_playing_a_card_adds_coconut_layers(self):
        engine = self.action_engine()
        coconut = self.equip_for_target(engine, "Coconut", 0, 0)
        attack = CardInstance("Basic")
        engine.players[0].hand = [attack]
        engine.players[0].fracture = 6

        result = engine.play_card(
            0,
            attack.instance_id,
            {"target_player": 1, "target_player_id": 1, "target_id": 1},
        )

        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[0].health, 94)
        self.assertEqual(coconut.custom_vars.get("layers"), 6)

    def test_direct_damage_adds_layers_in_2v2(self):
        engine = self.action_engine(GameEngine2v2)
        coconut = self.equip_for_target(engine, "Coconut", 1, 0)

        dealt = engine._deal_direct_damage(
            0,
            7,
            "破损",
            0,
            damage_type=DAMAGE_TYPE_MAGIC,
            damage_tag=DAMAGE_TAG_FRACTURE,
        )

        self.assertEqual(dealt, 7)
        self.assertEqual(coconut.custom_vars.get("layers"), 7)

    def test_fully_absorbed_damage_does_not_add_layers(self):
        engine = self.action_engine()
        coconut = self.equip_for_target(engine, "Coconut", 0, 0)
        engine._set_custom_status_value(0, "jungle:shield", 10)

        dealt = engine._deal_direct_damage(
            0,
            6,
            "破损",
            0,
            damage_type=DAMAGE_TYPE_MAGIC,
            damage_tag=DAMAGE_TAG_FRACTURE,
        )

        self.assertEqual(dealt, 0)
        self.assertEqual(coconut.custom_vars.get("layers", 0), 0)

    def test_magic_salt_still_only_responds_to_attack_damage(self):
        engine = self.action_engine()
        self.equip_for_target(engine, "MagicSalt", 0, 0)

        engine._deal_direct_damage(
            0,
            4,
            "破损",
            0,
            damage_type=DAMAGE_TYPE_MAGIC,
            damage_tag=DAMAGE_TAG_FRACTURE,
        )
        self.assertIsNone(engine.pending_choice)

        engine.deal_attack_damage(
            0,
            4,
            attacker_id=1,
            source_card=CardInstance("Basic"),
        )
        self.assertIsNotNone(engine.pending_choice)
        self.assertEqual(engine.pending_choice.get("choice_type"), "magic_salt_reflect")

    def test_direct_physical_non_attack_does_not_offer_magic_salt(self):
        engine = self.action_engine()
        self.equip_for_target(engine, "MagicSalt", 0, 0)

        engine._deal_direct_damage(
            0,
            4,
            "特殊效果",
            1,
            damage_type=DAMAGE_TYPE_PHYSICAL,
            damage_tag=DAMAGE_TAG_PHYSICAL,
        )

        self.assertIsNone(engine.pending_choice)


if __name__ == "__main__":
    unittest.main()
