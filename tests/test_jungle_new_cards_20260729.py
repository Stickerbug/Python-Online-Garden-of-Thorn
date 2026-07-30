import json
import unittest
import zipfile
from pathlib import Path

from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "mods" / "Jungle Cards Addition.gtnmod"
NEW_CARD_IDS = {"Monstera", "Dianthus", "Maple"}


class JungleNewCards20260729Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_mod(str(PACKAGE))
        if cls.mod.errors:
            raise AssertionError(cls.mod.errors)
        cls.mod_cards = {card.id: card for card in cls.mod.cards}

    def setUp(self):
        self.previous_defs = {card_id: CARD_DEFS.get(card_id) for card_id in NEW_CARD_IDS}
        for card_id in NEW_CARD_IDS:
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
            player.elixir = 100
            player.magic = 100
            player.health = 1000
            player.max_health = 1000
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

    def test_package_metadata_assets_and_locales(self):
        self.assertEqual(self.mod.info.author, "Eric, AArcC")
        self.assertEqual(self.mod.info.version, "1.1.0")
        self.assertTrue(NEW_CARD_IDS <= self.mod_cards.keys())
        self.assertEqual(self.mod_cards["Monstera"].count, 3)
        self.assertEqual(self.mod_cards["Dianthus"].count, 1)
        self.assertEqual(self.mod_cards["Maple"].count, 3)
        self.assertIn("team_unique", self.mod_cards["Monstera"].flags)
        self.assertIn("team_limited", self.mod_cards["Monstera"].flags)
        self.assertIn("rebound", self.mod_cards["Dianthus"].flags)
        self.assertIn("symbiosis", self.mod_cards["Maple"].flags)

        expected_assets = {
            "Monstera": "card-art/monstera.svg",
            "Dianthus": "card-art/dianthus.svg",
            "Maple": "card-art/maple.svg",
        }
        with zipfile.ZipFile(PACKAGE) as archive:
            files = set(archive.namelist())
            spec = json.loads(archive.read("mod.json"))
            card_specs = {
                card["legacy_id"]: card
                for card in spec["registries"]["cards"]
                if card.get("legacy_id") in NEW_CARD_IDS
            }
            self.assertEqual(set(card_specs), NEW_CARD_IDS)
            for card_id, image_path in expected_assets.items():
                self.assertEqual(card_specs[card_id]["assets"]["image"], image_path)
                self.assertIn(image_path, files)
                self.assertGreater(len(archive.read(image_path)), 100)
            for language in ("zh", "en", "fr", "ja"):
                locale = json.loads(archive.read(f"locales/{language}.json"))
                localized_cards = locale.get("cards", {})
                for card in card_specs.values():
                    self.assertIn(card["id"], localized_cards)

    def test_dianthus_same_instance_grows_after_each_use_and_caps_at_twenty(self):
        engine = self.action_engine()
        dianthus = CardInstance("Dianthus")
        original_instance_id = dianthus.instance_id
        engine.players[0].hand = [dianthus]
        damage_sequence = []

        for expected_power in (5, 10, 15, 20, 20):
            health_before = engine.players[1].health
            result = engine.play_card(
                0,
                original_instance_id,
                self.target_choice(1),
            )
            self.assertTrue(result.get("success"), result)
            damage_sequence.append(health_before - engine.players[1].health)
            self.assertEqual(len(engine.players[0].hand), 1)
            returned = engine.players[0].hand[0]
            self.assertEqual(returned.instance_id, original_instance_id)
            self.assertEqual(returned.power_value, expected_power)
            self.assertEqual(
                returned.custom_vars.get("jungle_dianthus_power"),
                expected_power,
            )

        self.assertEqual(damage_sequence, [8, 13, 18, 23, 28])

    def test_dianthus_uses_other_power_then_clears_only_that_temporary_gain(self):
        engine = self.action_engine()
        dianthus = CardInstance("Dianthus")
        dianthus.power_value = 7
        dianthus.instance_flags.add("power")
        engine.players[0].hand = [dianthus]

        first_health = engine.players[1].health
        result = engine.play_card(0, dianthus.instance_id, self.target_choice(1))
        self.assertTrue(result.get("success"), result)
        self.assertEqual(first_health - engine.players[1].health, 15)
        self.assertEqual(engine.players[0].hand[0].power_value, 5)

        engine.players[0].hand[0].power_value += 3
        second_health = engine.players[1].health
        result = engine.play_card(0, dianthus.instance_id, self.target_choice(1))
        self.assertTrue(result.get("success"), result)
        self.assertEqual(second_health - engine.players[1].health, 16)
        self.assertEqual(engine.players[0].hand[0].power_value, 10)

    def test_maple_adds_a_full_tagged_copy_to_its_owners_hand(self):
        engine = self.action_engine()
        maple = CardInstance("Maple")
        engine.players[0].hand = [maple]

        result = engine.play_card(0, maple.instance_id, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[1].health, 995)
        self.assertEqual(len(engine.players[0].hand), 1)
        generated = engine.players[0].hand[0]
        self.assertEqual(generated.card_def.id, "Maple")
        self.assertNotEqual(generated.instance_id, maple.instance_id)
        self.assertTrue({"symbiosis", "exile", "void"} <= generated.instance_flags)
        self.assertIn("on_play", generated.card_def.v2_events)
        self.assertIn(maple, engine.players[0].discard)

    def test_monstera_triggers_on_equipment_owner_turn_and_heals_target_team(self):
        engine = self.action_engine(GameEngine2v2)
        engine.players[0].health = 75
        engine.players[1].health = 70
        engine.players[2].health = 50
        engine.players[3].health = 60
        monstera = CardInstance("Monstera")
        engine.players[0].hand = [monstera]

        result = engine.play_card(
            0,
            monstera.instance_id,
            2,
            self.target_choice(2),
        )
        self.assertTrue(result.get("success"), result)
        equipment = engine.players[0].equipment[0]
        self.assertEqual(equipment.effect_target, 2)
        self.assertIn("on_any_turn_start", equipment.card_def.v2_events)

        engine.current_player = 2
        engine._run_card_event(
            0,
            equipment.card_instance,
            "any_turn_start",
            extra_context={"source_id": 0, "target_id": 2},
        )
        self.assertEqual([player.health for player in engine.players], [75, 70, 50, 60])

        engine.current_player = 0
        engine.players[2].untargetable = 1
        engine._run_card_event(
            0,
            equipment.card_instance,
            "any_turn_start",
            extra_context={"source_id": 0, "target_id": 0},
        )
        self.assertEqual([player.health for player in engine.players], [75, 70, 54, 64])

    def test_monstera_skips_dead_teammates_and_has_no_1v1_effect(self):
        team_engine = self.action_engine(GameEngine2v2)
        team_engine.players[2].health = 40
        team_engine.players[3].health = 0
        monstera = CardInstance("Monstera")
        team_engine.players[0].hand = [monstera]
        result = team_engine.play_card(
            0,
            monstera.instance_id,
            2,
            self.target_choice(2),
        )
        self.assertTrue(result.get("success"), result)
        equipment = team_engine.players[0].equipment[0]
        team_engine._run_card_event(
            0,
            equipment.card_instance,
            "any_turn_start",
            extra_context={"source_id": 0, "target_id": 0},
        )
        self.assertEqual(team_engine.players[2].health, 44)
        self.assertEqual(team_engine.players[3].health, 0)

        duel_engine = self.action_engine()
        duel_engine.players[0].health = 80
        duel_engine.players[1].health = 70
        duel_engine.current_player = 0
        duel_engine._atomic_jungle_monstera_heal_team(
            0,
            CardInstance("Monstera"),
            {"target": 1, "amount": 4},
            "",
            None,
            {},
        )
        self.assertEqual([player.health for player in duel_engine.players], [80, 70])

    def test_local_training_worker_has_matching_operations(self):
        worker = (ROOT / "static" / "js" / "local_solo_worker.js").read_text(encoding="utf-8")
        self.assertIn("effect_jungle_monstera_heal_team", worker)
        self.assertIn("toInt(this.current_player, -1) !== playerId", worker)
        self.assertIn("effect_jungle_dianthus_record_use", worker)
        self.assertIn("effect_jungle_dianthus_restore_power", worker)
        self.assertIn("effect_jungle_add_maple_to_hand", worker)


if __name__ == "__main__":
    unittest.main()
