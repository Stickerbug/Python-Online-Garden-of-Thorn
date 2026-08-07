import json
import unittest
import zipfile
from pathlib import Path

from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
ARCTIC_PACKAGE = ROOT / "mods" / "Arctic Cards Addition.gtnmod"
FACTORY_PACKAGE = ROOT / "mods" / "Factory Cards Addition.gtnmod"
NEW_CARD_IDS = {"Pinecone", "Ruby", "Lithium", "Assembler"}


class ArcticFactoryNewCardsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arctic = load_mod(str(ARCTIC_PACKAGE))
        cls.factory = load_mod(str(FACTORY_PACKAGE))
        if cls.arctic.errors or cls.factory.errors:
            raise AssertionError(cls.arctic.errors + cls.factory.errors)
        cls.mod_cards = {
            card.id: card
            for card in [*cls.arctic.cards, *cls.factory.cards]
        }

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
    def action_engine():
        engine = GameEngine()
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

    def test_package_metadata_assets_and_locales(self):
        self.assertEqual(self.arctic.info.author, "huanxiang0273, Eric, XinYu")
        self.assertEqual(self.arctic.info.version, "1.1.0")
        self.assertEqual(self.factory.info.author, "Eric, XinYu")
        self.assertEqual(self.factory.info.version, "1.1.0")
        self.assertEqual(self.mod_cards["Pinecone"].count, 3)
        self.assertEqual(self.mod_cards["Ruby"].count, 3)
        self.assertEqual(self.mod_cards["Lithium"].count, 3)

        expected_assets = {
            ARCTIC_PACKAGE: {"card-art/pinecone.svg", "card-art/ruby.svg"},
            FACTORY_PACKAGE: {"card-art/Lithium.svg"},
        }
        expected_locale_ids = {
            ARCTIC_PACKAGE: {"arctic:pinecone", "arctic:ruby"},
            FACTORY_PACKAGE: {"factory:lithium"},
        }
        for package, assets in expected_assets.items():
            with zipfile.ZipFile(package) as archive:
                names = set(archive.namelist())
                self.assertTrue(assets <= names)
                for locale in ("zh", "en", "fr", "ja"):
                    payload = json.loads(archive.read(f"locales/{locale}.json"))
                    self.assertTrue(expected_locale_ids[package] <= payload["cards"].keys())

    def test_pinecone_extra_copy_does_not_recurse_and_schedules_fragile_per_hit(self):
        engine = self.action_engine()
        pinecone = CardInstance("Pinecone")
        engine.players[0].hand = [pinecone]

        result = engine.play_card(0, pinecone.instance_id, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[0].health, 91)
        self.assertEqual(engine.players[1].health, 84)
        self.assertEqual(len(engine.players[0].exile), 1)
        self.assertIn(
            "arctic_pinecone_copy",
            engine.players[0].exile[0].setup_modifiers,
        )
        self.assertFalse(engine.custom_vars.get("bio_auto_play_queue"))
        self.assertEqual(len(engine.timed_effects), 7)

        engine._run_timed_effects_for_turn(1, "after_status_clear")
        self.assertEqual(
            engine._custom_status_value(1, "jungle:fragile", "fragile"),
            4,
        )
        engine._run_timed_effects_for_turn(0, "after_status_clear")
        self.assertEqual(
            engine._custom_status_value(0, "jungle:fragile", "fragile"),
            3,
        )

    def test_pinecone_does_nothing_extra_when_damage_is_fully_blocked(self):
        engine = self.action_engine()
        pinecone = CardInstance("Pinecone")
        engine.players[0].hand = [pinecone]
        engine.players[1].armor = 7

        result = engine.play_card(0, pinecone.instance_id, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[1].health, 100)
        self.assertEqual(engine.players[1].armor, 7)
        self.assertFalse(engine.players[0].exile)
        self.assertFalse(engine.custom_vars.get("bio_auto_play_queue"))
        self.assertFalse(engine.timed_effects)

    def test_ruby_filters_by_actual_cost_and_spends_before_adding_fusion(self):
        engine = self.action_engine()
        ruby = CardInstance("Ruby")
        attack = CardInstance("Pinecone")
        attack.cost_e_override = 3
        attack.cost_m_override = 2
        engine.players[0].elixir = 7
        engine.players[0].magic = 5
        engine.players[0].hand = [ruby, attack]

        self.assertEqual(engine._arctic_ruby_selectable_attacks(0, ruby), [attack])
        result = engine.play_card(
            0,
            ruby.instance_id,
            {"target_instance_id": attack.instance_id},
        )

        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[0].elixir, 4)
        self.assertEqual(engine.players[0].magic, 3)
        self.assertEqual(attack.fusion_level, 2)
        self.assertEqual(attack.fusion_multiplier, 2.0)
        self.assertIn(ruby, engine.players[0].exile)

        unaffordable_ruby = CardInstance("Ruby")
        unaffordable_attack = CardInstance("Pinecone")
        unaffordable_attack.cost_e_override = 99
        engine.players[0].hand = [unaffordable_ruby, unaffordable_attack]
        can_play, reason = engine.can_play_card(0, unaffordable_ruby)
        self.assertFalse(can_play)
        self.assertIn("没有可支付消耗", reason)

    def test_lithium_damages_on_play_and_owner_turn_start(self):
        engine = self.action_engine()
        lithium = CardInstance("Lithium")
        engine.players[0].hand = [lithium]

        result = engine.play_card(0, lithium.instance_id, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[1].health, 95)
        self.assertEqual(len(engine.players[0].equipment), 1)
        equipment = engine.players[0].equipment[0]
        self.assertEqual(equipment.effect_target, 1)

        engine._run_card_event(
            0,
            equipment.card_instance,
            "owner_turn_start",
            None,
            {"source_id": 0, "target_id": 1},
        )
        self.assertEqual(engine.players[1].health, 90)

    def test_assembler_choice_keeps_only_one_card_use_log(self):
        engine = self.action_engine()
        assembler = CardInstance("Assembler")
        target_card = CardInstance("Basic")
        engine.players[0].hand = [assembler]
        engine.players[1].hand = [target_card]

        play_result = engine.play_card(
            0,
            assembler.instance_id,
            self.target_choice(1),
        )
        self.assertTrue(play_result.get("needs_choice"), play_result)

        resolve_result = engine.resolve_choice(
            0,
            {"target_instance_id": target_card.instance_id},
        )

        self.assertTrue(resolve_result.get("success"), resolve_result)
        visible_log = [engine._strip_card_log_markers(line) for line in engine.log]
        use_lines = [line for line in visible_log if line.startswith("玩家1使用了重构机")]
        self.assertEqual(use_lines, ["玩家1使用了重构机"])
        self.assertFalse(any("重构机×2" in line for line in visible_log))

    def test_local_solo_worker_has_matching_handlers_and_choice_validation(self):
        source = (ROOT / "static" / "js" / "local_solo_worker.js").read_text(encoding="utf-8")
        self.assertIn("effect_arctic_pinecone_copy(", source)
        self.assertIn("drainArcticPineconeAutoPlayQueue(", source)
        self.assertIn("effect_arctic_ruby_fuse(", source)
        self.assertIn("choiceType === 'choose_arctic_ruby'", source)


if __name__ == "__main__":
    unittest.main()
