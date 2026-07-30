import json
import unittest
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from cards import CARD_DEFS, CardInstance, normalize_card_flag
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import ModCard, load_mod


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "mods" / "Garden Cards Addition.gtnmod"
NEW_CARD_IDS = {
    "MoonRock",
    "Avocado",
    "MagicPollen",
    "MagicAntennae",
    "CatEars",
    "Sunflower",
    "Beeswax",
    "MagicAvocado",
    "MagicRice",
    "MagicDisc",
    "MagicCutter",
    "Kale",
    "Daisy",
    "Coal",
    "Grass",
    "Candle",
}


class GardenNewCardsTests(unittest.TestCase):
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
            player.elixir = 50
            player.magic = 50
            player.health = 100
            player.max_health = 100
            player.armor = 0
            player.fire = 0
            player.fracture = 0
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

    def equip(self, engine, card_id, owner_id, target_id):
        card = CardInstance(card_id)
        engine.current_player = owner_id
        engine.players[owner_id].hand = [card]
        if isinstance(engine, GameEngine2v2):
            result = engine.play_card(
                owner_id,
                card.instance_id,
                target_id,
                self.target_choice(target_id),
            )
        else:
            result = engine.play_card(owner_id, card.instance_id, self.target_choice(target_id))
        self.assertTrue(result.get("success"), result)
        return engine.players[owner_id].equipment[-1]

    def test_package_metadata_cards_assets_and_locales(self):
        self.assertEqual(self.mod.info.author, "NetherDog, Eric, AArcC")
        self.assertEqual(self.mod.info.version, "1.1.0")
        self.assertTrue(NEW_CARD_IDS <= self.mod_cards.keys())
        expected_counts = {
            "MoonRock": 2,
            "Avocado": 3,
            "MagicPollen": 2,
            "MagicAntennae": 2,
            "CatEars": 3,
            "Sunflower": 3,
            "Beeswax": 3,
            "MagicAvocado": 2,
            "MagicRice": 3,
            "MagicDisc": 2,
            "MagicCutter": 2,
            "Kale": 1,
            "Daisy": 1,
            "Coal": 1,
            "Grass": 1,
            "Candle": 1,
        }
        for card_id, expected_count in expected_counts.items():
            self.assertEqual(self.mod_cards[card_id].count, expected_count)
        grass = self.mod_cards["Grass"]
        self.assertEqual(grass.trigger_cost_e, 1)
        self.assertTrue(grass.v2_resource.get("trigger_uses_effect_target"))
        self.assertEqual(
            grass.v2_events["on_equipment_trigger"].get("max_uses_per_turn"),
            1,
        )
        magic_pollen = self.mod_cards["MagicPollen"]
        self.assertEqual(magic_pollen.hits, 3)
        self.assertTrue(magic_pollen.upgraded_image_url)

        with zipfile.ZipFile(PACKAGE) as archive:
            files = set(archive.namelist())
            spec = json.loads(archive.read("mod.json"))
            new_specs = [
                card for card in spec["registries"]["cards"]
                if card.get("legacy_id") in NEW_CARD_IDS
            ]
            self.assertEqual(len(new_specs), len(NEW_CARD_IDS))
            magic_pollen_spec = next(
                card for card in new_specs
                if card.get("legacy_id") == "MagicPollen"
            )
            self.assertEqual(
                magic_pollen_spec["assets"]["upgraded_image"],
                "card-art/magic pollen+1.svg",
            )
            for card in new_specs:
                image = card["assets"]["image"]
                self.assertIn(image, files)
                self.assertGreater(len(archive.read(image)), 100)
            self.assertIn("card-art/magic pollen+1.svg", files)
            self.assertGreater(len(archive.read("card-art/magic pollen+1.svg")), 100)
            for language in ("zh", "en", "fr", "ja"):
                locale = json.loads(archive.read(f"locales/{language}.json"))
                card_text = locale.get("cards", locale)
                for card in new_specs:
                    self.assertIn(card["id"], card_text)

    def test_new_card_art_uses_padded_square_canvases(self):
        expected_view_boxes = {
            "card-art/grass.svg": "-29.10302 -14.33804 100.36627 100.36627",
            "card-art/coal.svg": "-8.03678 -9.02168 56.25749 56.25749",
            "card-art/kale.svg": "-10.88653 -11.18671 76.20570 76.20570",
            "card-art/daisy.svg": "-32.45311,-32.45311,113.81244,113.81244",
        }
        with zipfile.ZipFile(PACKAGE) as archive:
            for asset, expected_view_box in expected_view_boxes.items():
                root = ET.fromstring(archive.read(asset))
                self.assertEqual(root.get("viewBox"), expected_view_box)
                self.assertEqual(root.get("width"), root.get("height"))

    def test_card_tags_survive_without_duplicate_flags(self):
        card = ModCard({
            "id": "TagOnlyCard",
            "flags": [],
            "tags": ["sprout", "arctic:ready"],
        })
        self.assertEqual(card.flags, {"sprout", "arctic:ready"})
        self.assertIn("arctic:ready", self.mod_cards["Candle"].flags)
        self.assertEqual(normalize_card_flag("vanilla:sublime"), "sublime")

    def test_core_cross_mod_tag_has_frontend_fallback(self):
        source = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")
        self.assertIn("const core = CORE_REGISTRY_I18N[normalized];", source)
        self.assertIn("if (!core || core.kind !== 'tag') return null;", source)
        self.assertIn("color: '#3F83B8'", source)

    def test_third_eye_grants_precision_then_stealth_without_extra_log(self):
        engine = self.action_engine()
        target = CardInstance("Basic")
        params = {"card": {"ref": "current_card"}}
        original_log = list(engine.log)

        engine._atomic_third_eye_precision_or_hidden(
            0, target, params, "不应显示的精准日志", None, {}
        )
        self.assertIn("precision", target.instance_flags)
        self.assertEqual(engine.log, original_log)

        engine._atomic_third_eye_precision_or_hidden(
            0, target, params, "不应显示的隐匿日志", None, {}
        )
        self.assertIn("stealth", target.instance_flags)
        self.assertEqual(engine.log, original_log)

    def test_magic_pollen_spends_owner_magic_and_applies_fracture(self):
        engine = self.action_engine()
        self.equip(engine, "MagicPollen", 0, 1)
        magic_before = engine.players[0].magic
        engine._run_garden_magic_pollen_owner_turn_end(0)
        self.assertEqual(engine.players[0].magic, magic_before - 1)
        self.assertEqual(engine.players[1].fracture, 3)

        engine.players[0].magic = 0
        engine._run_garden_magic_pollen_owner_turn_end(0)
        self.assertEqual(engine.players[1].fracture, 3)

        upgraded_engine = self.action_engine()
        upgraded_engine.opening_event_picks[0] = 9
        magic_pollen = CardInstance("MagicPollen")
        upgraded_engine._apply_setup_modifiers_to_card(0, magic_pollen)
        self.assertEqual(magic_pollen.extra_hits, 1)
        self.assertIn("multi_petal", magic_pollen.setup_modifiers)
        upgraded_engine.players[0].hand = [magic_pollen]
        result = upgraded_engine.play_card(
            0,
            magic_pollen.instance_id,
            self.target_choice(1),
        )
        self.assertTrue(result.get("success"), result)
        upgraded_engine._run_garden_magic_pollen_owner_turn_end(0)
        self.assertEqual(upgraded_engine.players[1].fracture, 4)

    def test_sunflower_prevents_natural_shield_decay(self):
        engine = self.action_engine()
        self.equip(engine, "Sunflower", 0, 1)
        engine._set_custom_status_alias_group(1, "jungle:shield", ("jungle:shield", "shield"), 9)
        engine._apply_jungle_turn_start_statuses(1)
        self.assertEqual(engine._custom_status_value(1, "jungle:shield", "shield"), 9)

    def test_declarative_bloom_and_equipment_effects(self):
        engine = self.action_engine()
        moon_rock = CardInstance("MoonRock")
        engine.players[0].hand = [moon_rock]
        result = engine.play_card(0, moon_rock.instance_id, self.target_choice(1))
        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine._custom_status_value(1, "jungle:shield", "shield"), 40)
        self.assertEqual(engine.players[1].skip_turn, 1)

        engine = self.action_engine()
        self.equip(engine, "Avocado", 0, 1)
        engine.players[1].health = 90
        engine.deal_attack_damage(
            1,
            10,
            1,
            attacker_id=0,
            source_card=CardInstance("Basic"),
        )
        self.assertEqual(engine.players[1].health, 82)

        engine = self.action_engine()
        self.equip(engine, "MagicAvocado", 0, 1)
        engine.deal_attack_damage(
            1,
            10,
            1,
            attacker_id=0,
            source_card=CardInstance("Basic"),
        )
        self.assertEqual(engine._custom_status_value(1, "jungle:shield", "shield"), 3)

        engine = self.action_engine()
        beeswax = CardInstance("Beeswax")
        engine.players[0].hand = [beeswax]
        result = engine.play_card(0, beeswax.instance_id, self.target_choice(1))
        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine._custom_status_value(1, "jungle:shield", "shield"), 15)
        self.assertEqual(engine.players[1].honey_control_turns, 1)

    def test_magic_rice_returns_to_deck_top_and_candle_auto_plays(self):
        engine = self.action_engine()
        engine.players[0].magic = 0
        rice = CardInstance("MagicRice")
        engine.players[0].hand = [rice]
        result = engine.play_card(0, rice.instance_id, self.target_choice(1))
        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[1].health, 99)
        self.assertEqual(engine.players[0].magic, 2)
        self.assertEqual(engine.players[0].deck[0], rice)
        self.assertNotIn(rice, engine.players[0].discard)

        engine = self.action_engine()
        candle = CardInstance("Candle")
        engine.players[0].hand = [candle]
        engine._run_arctic_ready_cards_turn_start(0)
        self.assertEqual(engine.players[1].bleed, 1)
        self.assertEqual(engine.players[1].vulnerable, 1)
        self.assertIn(candle, engine.players[0].discard)

    def test_magic_disc_armor_tracks_shield_and_equipment_removal(self):
        engine = self.action_engine()
        equipment = self.equip(engine, "MagicDisc", 0, 1)
        engine._refresh_equipment_derived_player_flags(1)
        self.assertEqual(engine.players[1].armor, 1)

        engine._set_custom_status_alias_group(1, "jungle:shield", ("jungle:shield", "shield"), 2)
        self.assertEqual(engine.players[1].armor, 3)
        engine._set_custom_status_alias_group(1, "jungle:shield", ("jungle:shield", "shield"), 0)
        self.assertEqual(engine.players[1].armor, 1)

        self.assertTrue(engine._destroy_equipment(0, equipment, check_protection=False))
        engine._refresh_equipment_derived_player_flags(1)
        self.assertEqual(engine.players[1].armor, 0)

    def test_cat_ears_returns_only_first_eligible_card_each_target_turn(self):
        engine = self.action_engine()
        self.equip(engine, "CatEars", 0, 1)
        engine.current_player = 1
        engine.phase = "action"
        engine._turn_boundary_id = 12
        first = CardInstance("Basic")
        second = CardInstance("Basic")
        engine.players[1].hand = [first, second]

        first_result = engine.play_card(1, first.instance_id, self.target_choice(0))
        self.assertTrue(first_result.get("success"), first_result)
        self.assertIn(first, engine.players[1].hand)

        second_result = engine.play_card(1, second.instance_id, self.target_choice(0))
        self.assertTrue(second_result.get("success"), second_result)
        self.assertIn(second, engine.players[1].discard)
        self.assertNotIn(second, engine.players[1].hand)

    def test_magic_cutter_rewards_each_enemy_hit_and_not_friendly_hits(self):
        engine = self.action_engine()
        self.equip(engine, "MagicCutter", 0, 0)
        attack = CardInstance("Basic")
        engine.players[0].hand = [attack]
        result = engine.play_card(0, attack.instance_id, self.target_choice(1))
        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine._custom_status_value(0, "jungle:shield", "shield"), 2)

        team_engine = self.action_engine(GameEngine2v2)
        self.equip(team_engine, "MagicCutter", 0, 0)
        team_engine._garden_magic_cutter_after_hit(0, 1, 3)
        self.assertEqual(team_engine._custom_status_value(0, "jungle:shield", "shield"), 0)
        team_engine._garden_magic_cutter_after_hit(0, 2, 3)
        self.assertEqual(team_engine._custom_status_value(0, "jungle:shield", "shield"), 2)

    def test_kale_and_coal_use_dynamic_damage(self):
        engine = self.action_engine()
        engine.players[1].health = 20
        kale = CardInstance("Kale")
        engine.players[0].hand = [kale]
        result = engine.play_card(0, kale.instance_id, self.target_choice(1))
        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[1].health, -16)

        engine = self.action_engine()
        engine.players[0].fire = 2
        coal = CardInstance("Coal")
        engine.players[0].hand = [coal]
        result = engine.play_card(0, coal.instance_id, self.target_choice(1))
        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[1].health, 81)

    def test_daisy_delayed_damage_uses_original_player_as_attacker(self):
        engine = self.action_engine()
        daisy = CardInstance("Daisy")
        engine.players[0].hand = [daisy]
        result = engine.play_card(0, daisy.instance_id, self.target_choice(1))
        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[1].health, 98)
        engine._run_timed_effects_for_turn(1)
        self.assertEqual(engine.players[1].health, 83)

    def test_grass_uses_standard_once_per_turn_equipment_trigger(self):
        engine = self.action_engine()
        equipment = self.equip(engine, "Grass", 0, 1)
        equipment.turns_equipped = 1
        engine.players[1].health = 50
        engine.players[1].untargetable = True
        engine.players[0].elixir = 3
        engine.current_player = 0
        engine.phase = "action"

        result = engine.use_trigger(0, equipment.card_instance.instance_id)
        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[0].elixir, 2)
        self.assertEqual(engine.players[1].health, 55)
        self.assertEqual(equipment.uses_this_turn, 1)

        repeated = engine.use_trigger(0, equipment.card_instance.instance_id)
        self.assertFalse(repeated.get("success"))
        self.assertIn("本回合最多触发1次", repeated.get("error", ""))
        self.assertEqual(engine.players[0].elixir, 2)
        self.assertEqual(engine.players[1].health, 55)

    def test_2v2_grass_keeps_its_equipped_target_on_team_turn(self):
        engine = self.action_engine(GameEngine2v2)
        equipment = self.equip(engine, "Grass", 0, 2)
        equipment.turns_equipped = 1
        engine.players[0].elixir = 3
        engine.players[2].health = 50
        engine.current_player = 1

        result = engine.use_trigger(0, equipment.card_instance.instance_id)

        self.assertTrue(result.get("success"), result)
        self.assertFalse(result.get("needs_ally_consent"))
        self.assertEqual(engine.players[0].elixir, 2)
        self.assertEqual(engine.players[2].health, 55)

    def test_magic_antennae_reveal_is_private_and_tokenized(self):
        engine = self.action_engine()
        engine._garden_initial_decks = [
            [CardInstance("Basic").to_dict()],
            [CardInstance("Rose").to_dict(), CardInstance("Rose").to_dict()],
        ]
        antennae = CardInstance("MagicAntennae")
        engine.players[0].hand = [antennae]
        result = engine.play_card(0, antennae.instance_id, self.target_choice(1))
        self.assertTrue(result.get("success"), result)

        own_state = engine.get_public_state(0)
        other_state = engine.get_public_state(1)
        reveal = own_state.get("garden_initial_deck_reveal")
        self.assertEqual(reveal.get("target_player_id"), 1)
        self.assertEqual(len(reveal.get("cards", [])), 2)
        self.assertIsNone(other_state.get("garden_initial_deck_reveal"))

    def test_frontend_and_local_worker_have_garden_support(self):
        game_js = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")
        worker_js = (ROOT / "static" / "js" / "local_solo_worker.js").read_text(encoding="utf-8")
        self.assertIn("maybeShowGardenInitialDeckReveal(data)", game_js)
        self.assertIn("createClassicCardTile(card", game_js)
        self.assertIn("['Kale', 'garden:kale']", game_js)
        self.assertIn("['Coal', 'garden:coal']", game_js)
        self.assertIn("effect_garden_show_initial_deck", worker_js)
        self.assertIn("runGardenMagicPollenOwnerTurnEnd", worker_js)
        self.assertIn("gardenReturnFirstPlayedCard", worker_js)
        self.assertNotIn("gardenQueueGrassTrigger", worker_js)
        self.assertIn("equipmentTriggerUsesEffectTarget", worker_js)
        self.assertIn("equipmentTriggerUsesEffectTarget", game_js)


if __name__ == "__main__":
    unittest.main()
