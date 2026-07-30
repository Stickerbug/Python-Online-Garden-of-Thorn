import json
import math
import unittest
import zipfile
from pathlib import Path

from cards import CARD_DEFS, CardInstance
from game_engine import EquipmentInstance, GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "mods" / "Bio Cards Addition.gtnmod"
JURASSIC_PACKAGE = ROOT / "mods" / "Jurassic Cards Addition.gtnmod"
LOCAL_WORKER = (ROOT / "static" / "js" / "local_solo_worker.js").read_text(encoding="utf-8")
GAME_JS = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")
NEW_CARD_IDS = {"CyanidePill", "StemCell", "Mitochondria"}


class BioNewCardsTests(unittest.TestCase):
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
            player.health = 100
            player.max_health = 100
            player.base_max_health = 100
            player.elixir = 30
            player.magic = 30
            player.armor = 0
            player.poison = 0
            player.fire = 0
            player.heal_block = 0
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

    def test_package_metadata_assets_status_and_locales(self):
        self.assertEqual(self.mod.info.author, "huanxiang0273, Eric, XinYu")
        self.assertEqual(self.mod.info.version, "1.1.0")
        self.assertTrue(NEW_CARD_IDS <= self.mod_cards.keys())
        self.assertEqual(self.mod_cards["CyanidePill"].count, 3)
        self.assertEqual(self.mod_cards["StemCell"].count, 3)
        self.assertEqual(self.mod_cards["Mitochondria"].count, 3)
        self.assertTrue({"wide_strike", "self_target"} <= self.mod_cards["CyanidePill"].flags)
        self.assertEqual(self.mod_cards["StemCell"].trigger_cost_m, 6)

        with zipfile.ZipFile(PACKAGE) as archive, zipfile.ZipFile(JURASSIC_PACKAGE) as jurassic:
            self.assertIsNone(archive.testzip())
            files = set(archive.namelist())
            self.assertTrue({
                "card-art/cyanide pill.svg",
                "card-art/stem cell.svg",
                "card-art/mitochondria.svg",
                "status-icons/shield_conversion.svg",
            } <= files)
            self.assertEqual(
                archive.read("status-icons/shield_conversion.svg"),
                jurassic.read("card-art/amulet.svg"),
            )
            self.assertEqual(
                (ROOT / "static" / "assets" / "status-icons" / "shield_conversion.svg").read_bytes(),
                jurassic.read("card-art/amulet.svg"),
            )
            spec = json.loads(archive.read("mod.json"))
            statuses = {item["id"]: item for item in spec["registries"]["statuses"]}
            self.assertEqual(statuses["bio:shield_conversion"]["icon"], "shield_conversion")
            for locale in ("zh", "en", "fr", "ja"):
                translated = json.loads(archive.read(f"locales/{locale}.json"))
                self.assertIn("bio:shield_conversion", translated["statuses"])
                for card_id in ("bio:cyanide_pill", "bio:stem_cell", "bio:mitochondria"):
                    self.assertIn(card_id, translated["cards"])

    def test_cyanide_pill_clears_poison_and_fire_from_every_target(self):
        engine = self.action_engine()
        for player in engine.players:
            player.poison = 12
            player.fire = 8
        engine.players[1].custom_statuses["status_immune"] = 1
        card = CardInstance("CyanidePill")
        engine.players[0].hand = [card]

        result = engine.play_card(0, card.instance_id, {})

        self.assertTrue(result.get("success"), result)
        self.assertEqual([(p.poison, p.fire) for p in engine.players], [(0, 0), (0, 0)])

    def test_stem_cell_tracks_actual_health_loss_and_uses_its_fixed_target(self):
        engine = self.action_engine()
        card = CardInstance("StemCell")
        equipment = EquipmentInstance(card, owner=0)
        equipment.effect_target = 1
        engine.players[0].equipment.append(equipment)
        engine.players[1].armor = 3

        engine.deal_attack_damage(1, 10, attacker_id=0)
        engine._set_custom_status_alias_group(1, "jungle:shield", ("jungle:shield", "shield"), 4)
        engine._deal_direct_damage(1, 10, "测试", 0)

        self.assertEqual(engine.players[1].health, 87)
        self.assertEqual(equipment.custom_vars.get("layers"), 13)

        engine.players[1].health = 20
        equipment.custom_vars["layers"] = 5
        equipment.turns_equipped = 1
        engine.players[0].magic = 10
        result = engine.use_trigger(0, card.instance_id, target_player_id=0)

        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[1].health, 20 + math.ceil(5 * 0.75))
        self.assertEqual(engine.players[0].magic, 4)
        self.assertNotIn(equipment, engine.players[0].equipment)

    def test_stem_cell_tracks_cross_player_damage_in_2v2(self):
        engine = self.action_engine(GameEngine2v2)
        card = CardInstance("StemCell")
        equipment = EquipmentInstance(card, owner=0)
        equipment.effect_target = 2
        engine.players[0].equipment.append(equipment)
        engine._set_custom_status_alias_group(2, "jungle:shield", ("jungle:shield", "shield"), 3)

        engine._deal_direct_damage(2, 8, "测试", 1)

        self.assertEqual(engine.players[2].health, 95)
        self.assertEqual(equipment.custom_vars.get("layers"), 5)

    def test_shield_conversion_runs_after_heal_reduction_and_before_health_cap(self):
        engine = self.action_engine()
        target = engine.players[1]
        target.health = 50
        engine._bio_set_status_value(1, "extra_healing", 2)
        engine._bio_set_status_value(1, "shield_conversion", 2)

        target.heal(5)

        self.assertEqual(target.health, 50)
        self.assertEqual(engine._custom_status_value(1, "jungle:shield", "shield"), 14)
        self.assertEqual(engine._bio_status_value(1, "shield_conversion"), 0)

        target.heal_block = 2
        engine._bio_set_status_value(1, "shield_conversion", 2)
        target.heal(5)
        self.assertEqual(engine._bio_status_value(1, "shield_conversion"), 2)
        self.assertEqual(engine._custom_status_value(1, "jungle:shield", "shield"), 14)

    def test_status_immunity_suspends_but_does_not_clear_shield_conversion(self):
        engine = self.action_engine()
        target = engine.players[1]
        target.health = 50
        engine._bio_set_status_value(1, "shield_conversion", 2)
        target.custom_statuses["status_immune"] = 1

        target.heal(5)

        self.assertEqual(target.health, 55)
        self.assertEqual(engine._bio_status_value(1, "shield_conversion"), 2)
        self.assertEqual(engine._custom_status_value(1, "jungle:shield", "shield"), 0)

    def test_local_solo_worker_contains_matching_bio_hooks(self):
        self.assertIn("bioStemCellAfterHealthLoss(targetId, amount)", LOCAL_WORKER)
        self.assertIn("shield_conversion: ['bio:shield_conversion'", LOCAL_WORKER)
        self.assertIn("effect_bio_add_shield_conversion(", LOCAL_WORKER)
        self.assertIn("this.bioStemCellAfterHealthLoss(playerId, healthLost);", LOCAL_WORKER)
        self.assertIn("this.bioStemCellAfterHealthLoss(targetId, healthLost);", LOCAL_WORKER)
        self.assertIn("'shield_conversion'", GAME_JS)
        self.assertIn("'bio_clear_poison_fire'", LOCAL_WORKER)


if __name__ == "__main__":
    unittest.main()
