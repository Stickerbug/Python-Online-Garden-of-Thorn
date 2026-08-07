import json
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine, reset_card_after_play
from game_engine_2v2 import GameEngine2v2
from game_engine_urf import is_infinite_excluded
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "mods" / "Desert Cards DLC.gtnmod"
NEW_CARD_IDS = {
    "MagicCompass",
    "Marble",
    "Emerald",
    "Topaz",
    "Citron",
    "MagicYggdrasil",
}


class DesertNewCardsTests(unittest.TestCase):
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
            player.elixir = 30
            player.magic = 30
            player.health = 100
            player.max_health = 100
        return engine

    def test_package_metadata_and_card_definitions(self):
        self.assertEqual(self.mod.info.author, "NetherDog, XinYu")
        self.assertTrue(NEW_CARD_IDS <= self.mod_cards.keys())
        expected_counts = {
            "MagicCompass": 5,
            "Marble": 3,
            "Emerald": 3,
            "Topaz": 2,
            "Citron": 2,
            "MagicYggdrasil": 2,
        }
        for card_id, expected_count in expected_counts.items():
            self.assertEqual(self.mod_cards[card_id].count, expected_count)
        self.assertIn("self_target", self.mod_cards["Marble"].flags)
        self.assertEqual(self.mod_cards["MagicYggdrasil"].cost_e, 2)
        self.assertEqual(self.mod_cards["MagicYggdrasil"].cost_m, 10)
        self.assertIn("exile", self.mod_cards["MagicYggdrasil"].flags)
        self.assertIn("infinite_exclude", self.mod_cards["MagicYggdrasil"].flags)
        self.assertTrue(is_infinite_excluded(self.mod_cards["MagicYggdrasil"]))

    def test_new_cards_bundle_their_art(self):
        expected_art = {
            "MagicCompass": "card-art/magic compass.svg",
            "Marble": "card-art/marble.svg",
            "Emerald": "card-art/emerald.svg",
            "Topaz": "card-art/topaz.svg",
            "Citron": "card-art/citron.svg",
            "MagicYggdrasil": "card-art/magic yggdrasil.svg",
        }
        with zipfile.ZipFile(PACKAGE) as archive:
            package_files = set(archive.namelist())
            spec = json.loads(archive.read("mod.json"))
            cards = {
                card["legacy_id"]: card
                for card in spec["registries"]["cards"]
                if card.get("legacy_id") in expected_art
            }
            self.assertEqual(set(cards), set(expected_art))
            for card_id, image_path in expected_art.items():
                self.assertEqual(cards[card_id]["assets"]["image"], image_path)
                self.assertIn(image_path, package_files)
                self.assertGreater(len(archive.read(image_path)), 100)

    def test_magic_compass_accepts_zero_or_moves_selected_cards_to_deck_top(self):
        engine = self.action_engine()
        compass = CardInstance("MagicCompass")
        first = CardInstance("Basic")
        second = CardInstance("Rose")
        engine.players[0].hand = [compass]
        engine.players[0].discard = [first, second]

        queued = engine.play_card(0, compass.instance_id)
        self.assertTrue(queued.get("needs_choice"))
        self.assertEqual(queued.get("choice_type"), "choose_cards_from_discard")

        with patch("game_engine.random.shuffle", side_effect=lambda cards: cards.reverse()):
            result = engine.resolve_choice(
                0,
                {"target_instance_ids": [first.instance_id, second.instance_id]},
            )
        self.assertTrue(result.get("success"))
        self.assertEqual(engine.players[0].deck[:2], [second, first])
        self.assertNotIn(first, engine.players[0].discard)
        self.assertNotIn(second, engine.players[0].discard)

        compass_zero = CardInstance("MagicCompass")
        remaining = CardInstance("Fries")
        engine.players[0].hand.append(compass_zero)
        engine.players[0].discard.append(remaining)
        queued = engine.play_card(0, compass_zero.instance_id)
        self.assertTrue(queued.get("needs_choice"))
        result = engine.resolve_choice(0, {"target_instance_ids": []})
        self.assertTrue(result.get("success"))
        self.assertIn(remaining, engine.players[0].discard)

    def test_marble_triggers_one_random_extra_hit_per_actual_primary_hit(self):
        engine = self.action_engine()
        marble = CardInstance("Marble")
        marble.fission_level = 2
        marble.fission_count = 1
        engine.players[0].hand = [marble]

        with patch("game_engine.random.choice", side_effect=lambda candidates: candidates[0]):
            result = engine.play_card(
                0,
                marble.instance_id,
                {"target_player": 1, "target_player_id": 1, "target_id": 1},
            )

        self.assertTrue(result.get("success"))
        self.assertEqual(engine.players[1].health, 78)
        self.assertEqual(engine.players[0].health, 88)
        self.assertIn("受到12D", "\n".join(engine.log))

    def test_marble_extra_damage_scales_with_fusion_and_power(self):
        engine = self.action_engine()
        marble = CardInstance("Marble")
        marble.fission_level = 2
        marble.fission_count = 1
        marble.fusion_level = 3
        marble.power_value = 4
        engine.players[0].hand = [marble]

        with patch("game_engine.random.choice", side_effect=lambda candidates: candidates[0]):
            result = engine.play_card(
                0,
                marble.instance_id,
                {"target_player": 1, "target_player_id": 1, "target_id": 1},
            )

        self.assertTrue(result.get("success"))
        self.assertEqual(engine.players[1].health, 25)
        self.assertEqual(engine.players[0].health, 61)

    def test_marble_extra_damage_uses_current_precision(self):
        engine = self.action_engine()
        marble = CardInstance("Marble")
        marble.instance_flags.add("precision")
        engine.players[0].dodge = 1
        engine.players[0].hand = [marble]

        with patch("game_engine.random.choice", side_effect=lambda candidates: candidates[0]):
            result = engine.play_card(
                0,
                marble.instance_id,
                {"target_player": 1, "target_player_id": 1, "target_id": 1},
            )

        self.assertTrue(result.get("success"))
        self.assertEqual(engine.players[1].health, 91)
        self.assertEqual(engine.players[0].health, 88)
        self.assertEqual(engine.players[0].dodge, 0)

    def test_emerald_accumulates_actual_energy_spend_per_equipment(self):
        engine = self.action_engine()
        engine.players[0].magic = 0
        emerald = CardInstance("Emerald")
        engine.players[0].hand = [emerald]
        result = engine.play_card(
            0,
            emerald.instance_id,
            {"target_player": 1, "target_player_id": 1, "target_id": 1},
        )
        self.assertTrue(result.get("success"))
        self.assertEqual(engine.players[0].magic, 0)

        engine._spend_resource(1, "elixir", 1)
        self.assertEqual(engine.players[0].magic, 0)
        engine._spend_resource(1, "elixir", 1)
        self.assertEqual(engine.players[0].magic, 1)
        engine._spend_resource(1, "elixir", 5)
        self.assertEqual(engine.players[0].magic, 3)
        eq = engine.players[0].equipment[0]
        self.assertEqual(eq.custom_vars.get("desert_emerald_e_spent"), 1)

    def test_topaz_stacks_and_reverts_derived_armor_and_immunity(self):
        engine = self.action_engine()
        first = CardInstance("Topaz")
        second = CardInstance("Topaz")
        engine.players[0].hand = [first, second]
        target_choice = {"target_player": 1, "target_player_id": 1, "target_id": 1}

        self.assertTrue(engine.play_card(0, first.instance_id, target_choice).get("success"))
        self.assertTrue(engine.play_card(0, second.instance_id, target_choice).get("success"))
        self.assertEqual(engine.players[1].armor, 8)
        self.assertTrue(engine._is_status_immune(1))

        first_eq = engine.players[0].equipment[0]
        self.assertTrue(engine._destroy_equipment(0, first_eq, check_protection=False))
        self.assertEqual(engine.players[1].armor, 4)
        self.assertTrue(engine._is_status_immune(1))
        second_eq = engine.players[0].equipment[0]
        self.assertTrue(engine._destroy_equipment(0, second_eq, check_protection=False))
        self.assertEqual(engine.players[1].armor, 0)
        self.assertFalse(engine._is_status_immune(1))

    def test_citron_grants_temporary_precision_then_stealth(self):
        engine = self.action_engine()
        attack = CardInstance("Basic")
        first = CardInstance("Citron")
        second = CardInstance("Citron")
        for card in (first, second):
            engine.players[0].hand = [card]
            result = engine.play_card(
                0,
                card.instance_id,
                {"target_player": 0, "target_player_id": 0, "target_id": 0},
            )
            self.assertTrue(result.get("success"))

        engine._prepare_desert_citron_play_flags(0, attack)
        flags = engine._effective_card_flags(attack)
        self.assertIn("precision", flags)
        self.assertIn("stealth", flags)
        reset_card_after_play(attack)
        self.assertNotIn("desert_citron_precision_play", attack.setup_modifiers)
        self.assertNotIn("desert_citron_stealth_play", attack.setup_modifiers)

    def test_magic_yggdrasil_uses_normal_hand_overflow(self):
        engine = self.action_engine()
        magic_yggdrasil = CardInstance("MagicYggdrasil")
        engine.players[0].hand = [magic_yggdrasil]
        engine.players[1].hand = [CardInstance("Basic") for _ in range(7)]

        result = engine.play_card(
            0,
            magic_yggdrasil.instance_id,
            {"target_player": 1, "target_player_id": 1, "target_id": 1},
        )
        self.assertTrue(result.get("success"))
        self.assertEqual(len(engine.players[1].hand), 7)
        self.assertEqual(engine.players[1].discard[-1].def_id, "Yggdrasil")
        self.assertIn(magic_yggdrasil, engine.players[0].exile)

    def test_2v2_marble_random_targets_join_response_target_list(self):
        engine = self.action_engine(GameEngine2v2)
        marble = CardInstance("Marble")
        choice = {
            "target_player": 0,
            "target_player_id": 0,
            "target_id": 0,
            "_desert_marble_targets": [2, 2, 3],
        }
        self.assertEqual(
            engine._response_target_ids_for_card(0, marble, choice),
            [0, 2, 3],
        )

    def test_frontend_and_local_worker_have_desert_support(self):
        game_js = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")
        worker_js = (ROOT / "static" / "js" / "local_solo_worker.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "css" / "style.css").read_text(encoding="utf-8")
        self.assertIn("choiceType === 'choose_cards_from_discard'", game_js)
        self.assertIn("distinguishCancel", game_js)
        self.assertIn("effect_desert_magic_compass", worker_js)
        self.assertIn("effect_desert_marble_attack", worker_js)
        self.assertIn("effect_desert_emerald_resource", worker_js)
        self.assertIn("effect_desert_magic_yggdrasil", worker_js)
        self.assertIn('[lang="zh"] .card.card-name-long-zh', css)
        self.assertIn("--card-name-font-scale: 8.9cqi;", css)
        self.assertIn("classic-card-tile-name-wrapped", css)


if __name__ == "__main__":
    unittest.main()
