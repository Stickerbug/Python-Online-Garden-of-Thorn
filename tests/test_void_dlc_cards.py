import json
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from cards import CARD_DEFS, CardInstance
from game_engine import EquipmentInstance, GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod
from mod_runtime_v2 import resolve_v2_target


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {
    "Bio Cards DLC.gtnmod": (5, "huanxiang0273, Eric, XinYu, AArcC"),
    "Factory Cards DLC.gtnmod": (6, "Eric, XinYu, AArcC"),
    "Void Cards DLC.gtnmod": (25, "Eric, AArcC"),
}
PREEXISTING_DLC_CARD_IDS = {"CyanidePill", "StemCell", "Mitochondria", "Lithium"}


class VoidDlcCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mods = [load_mod(str(ROOT / "mods" / filename)) for filename in PACKAGES]
        errors = [error for mod in cls.mods for error in mod.errors]
        if errors:
            raise AssertionError(errors)
        cls.mod_cards = {card.id: card for mod in cls.mods for card in mod.cards}

    def setUp(self):
        self.previous_defs = {card_id: CARD_DEFS.get(card_id) for card_id in self.mod_cards}
        for card_id, card in self.mod_cards.items():
            CARD_DEFS[card_id] = card.to_card_def()

    def tearDown(self):
        for card_id, previous in self.previous_defs.items():
            if previous is None:
                CARD_DEFS.pop(card_id, None)
            else:
                CARD_DEFS[card_id] = previous

    @staticmethod
    def action_engine(engine_class=GameEngine):
        engine = engine_class()
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

    @staticmethod
    def equip(engine, owner_id, target_id, def_id):
        equipment = EquipmentInstance(CardInstance(def_id), owner_id)
        equipment.effect_target = target_id
        engine.players[owner_id].equipment.append(equipment)
        return equipment

    def test_packages_have_complete_locales_and_normalized_art(self):
        for filename, (expected_count, expected_author) in PACKAGES.items():
            package = ROOT / "mods" / filename
            mod = next(item for item in self.mods if item.filename == filename)
            self.assertEqual(len(mod.cards), expected_count)
            self.assertEqual(mod.info.author, expected_author)
            with zipfile.ZipFile(package) as archive:
                members = set(archive.namelist())
                spec = json.loads(archive.read("mod.json"))
                resource_ids = {card["id"] for card in spec["registries"]["cards"]}
                for language in ("zh", "en", "fr", "ja"):
                    locale = json.loads(archive.read(f"locales/{language}.json"))
                    self.assertTrue(resource_ids <= set(locale["cards"]))
                for card in spec["registries"]["cards"]:
                    image = (card.get("assets") or {}).get("image")
                    self.assertIn(image, members)
                    if card.get("legacy_id") in PREEXISTING_DLC_CARD_IDS:
                        continue
                    root = ET.fromstring(archive.read(image))
                    self.assertEqual(root.attrib.get("viewBox"), "0 0 100 100")

    def test_copper_rod_absorbs_responded_attack_damage_as_charge(self):
        engine = self.action_engine()
        attack = CardInstance("Basic")
        copper_rod = CardInstance("CopperRod")
        other_card = CardInstance("Basic")
        engine.players[0].hand = [attack]
        engine.players[1].hand = [copper_rod, other_card]

        result = engine.play_card(0, attack.instance_id, self.target_choice(1))
        self.assertTrue(result.get("needs_response"), result)
        response = engine.handle_response(1, copper_rod.instance_id)

        self.assertTrue(response.get("success"), response)
        self.assertEqual(engine.players[1].health, 100)
        self.assertGreater(other_card.charge_value, 0)
        self.assertIn("charge", other_card.flags)
        self.assertIn(copper_rod, engine.players[1].discard)

    def test_magic_copper_rod_absorbs_one_electric_hit(self):
        engine = self.action_engine()
        self.equip(engine, 0, 0, "MagicCopperRod")
        charged = CardInstance("Basic")
        charged.charge_value = 2
        charged.instance_flags.add("charge")
        engine.players[0].hand = [charged]

        result = engine._deal_direct_damage(
            0,
            7,
            "电伤",
            1,
            damage_type="magic",
            damage_tag="battery",
        )

        self.assertEqual(result, 0)
        self.assertIsNone(engine.pending_v2_ui)
        self.assertEqual(engine.players[0].health, 100)
        self.assertEqual(engine.players[0].magic, 49)
        self.assertEqual(charged.charge_value, 9)

    def test_magic_copper_rod_can_answer_enemy_electric_attack_path(self):
        engine = self.action_engine()
        self.equip(engine, 0, 0, "MagicCopperRod")

        result = engine.deal_attack_damage(
            0,
            7,
            1,
            is_battery=True,
            attacker_id=1,
        )

        self.assertEqual(result, 0)
        self.assertIsNone(engine.pending_v2_ui)
        self.assertEqual(engine.players[0].health, 100)
        self.assertEqual(engine.players[0].magic, 49)

    def test_magic_copper_rod_absorbs_each_hit_while_magic_is_enough(self):
        engine = self.action_engine()
        self.equip(engine, 0, 0, "MagicCopperRod")

        engine.deal_attack_damage(0, 7, 2, is_battery=True, attacker_id=1)

        self.assertIsNone(engine.pending_v2_ui)
        self.assertEqual(engine.players[0].health, 100)
        self.assertEqual(engine.players[0].magic, 48)

    def test_capacitor_starts_with_three_charge_without_resetting_saved_zero(self):
        engine = self.action_engine()
        capacitor = CardInstance("Capacitor")

        self.assertEqual(self.mod_cards["Capacitor"].charge_value, 3)
        self.assertEqual(CARD_DEFS["Capacitor"].charge_value, 3)
        self.assertEqual(capacitor.charge_value, 3)
        engine.players[0].add_to_hand(capacitor)
        self.assertEqual(capacitor.charge_value, 3)
        self.assertIn("charge", capacitor.flags)

        capacitor.charge_value = 0
        restored = CardInstance.from_dict(capacitor.to_dict())
        self.assertEqual(restored.charge_value, 0)

    def test_masks_no_longer_project_reduced_visible_layers(self):
        engine = self.action_engine()
        self.equip(engine, 0, 1, "Mask")
        self.equip(engine, 0, 1, "MagicMask")
        target = engine.players[1]
        target.toxic = 3
        target.blind = 2
        target.custom_statuses["jungle:toxic_poison"] = 4

        public = engine.get_public_state(1)["you"]

        self.assertEqual(public["toxic"], 3)
        self.assertEqual(public["blind"], 2)
        self.assertEqual(public["custom_statuses"]["jungle:toxic_poison"], 4)
        self.assertEqual(target.toxic, 3)
        self.assertEqual(target.blind, 2)
        self.assertEqual(target.custom_statuses["jungle:toxic_poison"], 4)

    def test_mask_projection_no_longer_changes_2v2_public_state(self):
        engine = self.action_engine(GameEngine2v2)
        self.equip(engine, 0, 2, "MagicMask")
        engine.players[2].blind = 1
        engine.players[2].toxic = 2
        engine.players[2].custom_statuses["jungle:toxic_poison"] = 2

        public = engine.get_public_state(2)["you"]

        self.assertEqual(public["blind"], 1)
        self.assertEqual(public["toxic"], 2)
        self.assertEqual(public["custom_statuses"]["jungle:toxic_poison"], 2)

    def test_magic_slime_ball_copies_gain_magic_swift_two(self):
        engine = self.action_engine()
        original = CardInstance("MagicSlimeBall")

        engine.players[0].add_to_hand(original)

        copies = [card for card in engine.players[0].hand if card is not original]
        self.assertEqual(len(copies), 2)
        for copy_card in copies:
            self.assertEqual(copy_card.magic_swift_value, 2)
            self.assertIn("exile", copy_card.flags)
            self.assertNotIn("copy", copy_card.flags)

    def test_pipe_bomb_deals_fixed_damage_to_wide_targets_and_ends_turn(self):
        engine = self.action_engine()
        pipe_bomb = CardInstance("PipeBomb")
        engine.players[0].hand = [pipe_bomb]

        result = engine.play_card(0, pipe_bomb.instance_id, {})

        self.assertTrue(result.get("success"), result)
        self.assertEqual([player.health for player in engine.players], [100, 84])
        self.assertEqual(engine.current_player, 1)

    def test_illuminati_applies_all_statuses_then_clears_target_statuses(self):
        engine = self.action_engine()
        triangle = CardInstance("IlluminatiTriangle")
        engine.players[0].hand = [triangle]
        engine.players[1].health = 80

        result = engine.play_card(0, triangle.instance_id, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[1].health, 100)
        self.assertEqual(engine.players[1].skip_turn, 1)
        self.assertEqual(engine.players[1].poison, 1)
        engine.end_turn(0)
        self.assertEqual(engine.players[1].skip_turn, 0)
        self.assertEqual(engine.players[1].poison, 0)

    def test_cicada_starts_with_two_card_discard_picker(self):
        engine = self.action_engine()
        cicada = CardInstance("Cicada3301")
        first = CardInstance("Basic")
        second = CardInstance("Basic")
        engine.players[0].hand = [cicada, first, second]

        result = engine.play_card(0, cicada.instance_id, {})

        self.assertTrue(result.get("needs_v2_ui"), result)
        controls = engine.pending_v2_ui["component"]["controls"]
        self.assertEqual(controls[0]["type"], "multi_card_picker")
        self.assertEqual(controls[0]["min_select"], 2)
        self.assertEqual(controls[0]["max_select"], 2)

    def test_eyeball_forces_random_player_targets_in_1v1_and_v2_runtime(self):
        engine = self.action_engine()
        self.equip(engine, 0, 1, "Eyeball")

        self.assertEqual(engine._resolve_targets(0, "random_player"), [1])
        self.assertEqual(
            resolve_v2_target(engine, {"source_player": 0, "_rng_index": 0}, "random_player"),
            1,
        )

    def test_eyeball_forces_random_targets_in_2v2(self):
        engine = self.action_engine(GameEngine2v2)
        self.equip(engine, 0, 3, "Eyeball")

        self.assertEqual(engine._resolve_targets(0, "random_enemy"), [3])
        self.assertEqual(engine._resolve_targets(2, "random_friendly"), [3])

    def test_eyeball_forces_targeted_cards_to_equipment_owner(self):
        engine = self.action_engine(GameEngine2v2)
        engine.current_player = 2
        self.equip(engine, 0, 2, "Eyeball")
        attack = CardInstance("Basic")
        engine.players[2].hand = [attack]

        result = engine.play_card(2, attack.instance_id, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[0].health, 94)
        self.assertEqual(engine.players[1].health, 100)


if __name__ == "__main__":
    unittest.main()
