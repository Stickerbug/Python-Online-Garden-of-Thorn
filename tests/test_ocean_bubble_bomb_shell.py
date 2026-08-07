import json
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "mods" / "Ocean Cards Addition.gtnmod"
NEW_CARD_IDS = {"BubbleBomb", "Shell"}


class OceanBubbleBombShellTests(unittest.TestCase):
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
            player.elixir = 30
            player.magic = 30
            player.skip_turn = 0
            player.shovel_active = False
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
        self.assertEqual(self.mod.info.author, "huanxiang0273, XinYu")
        self.assertEqual(self.mod.info.version, "1.1.0")
        self.assertTrue(NEW_CARD_IDS <= self.mod_cards.keys())

        bubble_bomb = self.mod_cards["BubbleBomb"]
        self.assertEqual(bubble_bomb.card_type, "guard")
        self.assertEqual((bubble_bomb.cost_e, bubble_bomb.cost_m, bubble_bomb.count), (4, 0, 3))
        self.assertEqual(bubble_bomb.response_trigger, "thorn")
        self.assertIn("exile", bubble_bomb.flags)

        shell = self.mod_cards["Shell"]
        self.assertEqual(shell.card_type, "bloom")
        self.assertEqual((shell.cost_e, shell.cost_m, shell.count), (1, 0, 3))

        with zipfile.ZipFile(PACKAGE) as archive:
            self.assertIsNone(archive.testzip())
            files = set(archive.namelist())
            expected_assets = {
                "card-art/bubble bomb.svg",
                "card-art/shell.svg",
            }
            self.assertTrue(expected_assets <= files)
            for archive_name in expected_assets:
                ET.fromstring(archive.read(archive_name))

            spec = json.loads(archive.read("mod.json"))
            self.assertEqual(spec["manifest"]["author"], "huanxiang0273, XinYu")
            for locale in ("zh", "en", "fr", "ja"):
                translated = json.loads(archive.read(f"locales/{locale}.json"))
                self.assertIn("ocean:bubble_bomb", translated["cards"])
                self.assertIn("ocean:shell", translated["cards"])

    def test_bubble_bomb_allows_attack_then_locks_and_stuns_attacker(self):
        engine = self.action_engine()
        attack = CardInstance("Basic")
        bubble_bomb = CardInstance("BubbleBomb")
        engine.players[0].hand = [attack]
        engine.players[1].hand = [bubble_bomb]

        result = engine.play_card(0, attack.instance_id, self.target_choice(1))

        self.assertTrue(result.get("needs_response"), result)
        response = engine.handle_response(1, bubble_bomb.instance_id)
        self.assertTrue(response.get("success"), response)
        self.assertLess(engine.players[1].health, 100)
        self.assertTrue(engine.players[0].shovel_active)
        self.assertEqual(engine.players[0].skip_turn, 1)
        self.assertIn(bubble_bomb, engine.players[1].exile)

        second_attack = CardInstance("Basic")
        engine.players[0].hand = [second_attack]
        blocked = engine.play_card(0, second_attack.instance_id, self.target_choice(1))
        self.assertFalse(blocked.get("success", False), blocked)
        self.assertIn(second_attack, engine.players[0].hand)

    def test_bubble_bomb_only_responds_for_attacked_player_in_2v2(self):
        engine = self.action_engine(GameEngine2v2)
        attack = CardInstance("Basic")
        teammate_bomb = CardInstance("BubbleBomb")
        engine.players[0].hand = [attack]
        engine.players[2].hand = [teammate_bomb]

        result = engine.play_card(0, attack.instance_id, 3, self.target_choice(3))

        self.assertFalse(result.get("needs_response", False), result)
        self.assertIsNone(engine.pending_response)
        self.assertLess(engine.players[3].health, 100)

    def test_bubble_bomb_targets_exact_attacker_in_2v2(self):
        engine = self.action_engine(GameEngine2v2)
        attack = CardInstance("Basic")
        bubble_bomb = CardInstance("BubbleBomb")
        engine.players[0].hand = [attack]
        engine.players[2].hand = [bubble_bomb]

        result = engine.play_card(0, attack.instance_id, 2, self.target_choice(2))

        self.assertTrue(result.get("needs_response"), result)
        responders = {
            int(card["responder_id"])
            for card in engine.pending_response.get("counter_cards", [])
        }
        self.assertEqual(responders, {2})

        response = engine.handle_response(2, bubble_bomb.instance_id)
        self.assertTrue(response.get("success"), response)
        self.assertLess(engine.players[2].health, 100)
        self.assertTrue(engine.players[0].shovel_active)
        self.assertEqual(engine.players[0].skip_turn, 1)
        self.assertEqual(
            [(player.shovel_active, player.skip_turn) for player in engine.players[1:]],
            [(False, 0), (False, 0), (False, 0)],
        )

    def test_shell_grants_ten_shield_to_selected_target(self):
        for engine, target_id in ((self.action_engine(), 1), (self.action_engine(GameEngine2v2), 2)):
            shell = CardInstance("Shell")
            engine.players[0].hand = [shell]
            if isinstance(engine, GameEngine2v2):
                result = engine.play_card(
                    0,
                    shell.instance_id,
                    target_id,
                    self.target_choice(target_id),
                )
            else:
                result = engine.play_card(0, shell.instance_id, self.target_choice(target_id))

            self.assertTrue(result.get("success"), result)
            self.assertEqual(
                engine._custom_status_value(target_id, "jungle:shield", "shield"),
                10,
            )


if __name__ == "__main__":
    unittest.main()
