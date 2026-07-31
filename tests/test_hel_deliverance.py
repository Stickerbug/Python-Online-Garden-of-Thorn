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
PACKAGE = ROOT / "mods" / "Hel Cards Addition.gtnmod"
CARD_ID = "Deliverance"


class HelDeliveranceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_mod(str(PACKAGE))
        if cls.mod.errors:
            raise AssertionError(cls.mod.errors)
        cls.card = next(card for card in cls.mod.cards if card.id == CARD_ID)

    def setUp(self):
        self.previous_def = CARD_DEFS.get(CARD_ID)
        CARD_DEFS[CARD_ID] = self.card.to_card_def()

    def tearDown(self):
        if self.previous_def is None:
            CARD_DEFS.pop(CARD_ID, None)
        else:
            CARD_DEFS[CARD_ID] = self.previous_def

    @staticmethod
    def action_engine(engine_type):
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

    def test_package_metadata_asset_and_locales(self):
        self.assertEqual(self.mod.info.author, "Eric, AArcC")
        self.assertEqual(self.mod.info.version, "1.1.0")
        self.assertEqual((self.card.cost_e, self.card.cost_m), (2, 0))
        self.assertEqual(self.card.card_type, "thorn")
        self.assertEqual(self.card.count, 1)
        self.assertEqual(self.card.damage, 2)
        self.assertIn("precision", self.card.flags)
        self.assertIn("stealth", self.card.flags)
        self.assertEqual(self.card.v2_resource.get("tags"), [])

        with zipfile.ZipFile(PACKAGE) as archive:
            self.assertIsNone(archive.testzip())
            root = ET.fromstring(archive.read("card-art/deliverance.svg"))
            self.assertEqual(
                root.attrib.get("viewBox"),
                "-20.02392,-20.02392,100.11960,100.11960",
            )
            spec = json.loads(archive.read("mod.json"))
            self.assertEqual(spec["manifest"]["author"], "Eric, AArcC")
            deliverance = next(
                card
                for card in spec["registries"]["cards"]
                if card.get("legacy_id") == CARD_ID
            )
            self.assertEqual(deliverance["tags"], [])
            self.assertEqual(deliverance["flags"], ["precision", "stealth"])
            for locale in ("zh", "en", "fr", "ja"):
                translated = json.loads(archive.read(f"locales/{locale}.json"))
                self.assertIn("hel:deliverance", translated["cards"])

    def test_deliverance_uses_target_hand_count_without_opening_response(self):
        for engine_type, target_id in ((GameEngine, 1), (GameEngine2v2, 2)):
            with self.subTest(engine=engine_type.__name__):
                engine = self.action_engine(engine_type)
                deliverance = CardInstance(CARD_ID)
                counter = CardInstance("Bubble")
                engine.players[0].hand = [deliverance]
                engine.players[target_id].hand = [counter]

                if engine_type is GameEngine2v2:
                    result = engine.play_card(
                        0,
                        deliverance.instance_id,
                        target_id,
                        self.target_choice(target_id),
                    )
                else:
                    result = engine.play_card(
                        0,
                        deliverance.instance_id,
                        self.target_choice(target_id),
                    )

                self.assertTrue(result.get("success"), result)
                self.assertFalse(result.get("needs_response", False), result)
                self.assertIsNone(engine.pending_response)
                self.assertEqual(engine.players[target_id].health, 96)
                self.assertEqual(engine.players[0].elixir, 28)
                self.assertIn(deliverance, engine.players[0].discard)

    def test_deliverance_counts_every_current_hand_card(self):
        engine = self.action_engine(GameEngine)
        deliverance = CardInstance(CARD_ID)
        engine.players[0].hand = [deliverance]
        engine.players[1].hand = [
            CardInstance("Basic"),
            CardInstance("Rose"),
            CardInstance("Bubble"),
        ]

        result = engine.play_card(
            0,
            deliverance.instance_id,
            self.target_choice(1),
        )

        self.assertTrue(result.get("success"), result)
        self.assertEqual(engine.players[1].health, 92)


if __name__ == "__main__":
    unittest.main()
