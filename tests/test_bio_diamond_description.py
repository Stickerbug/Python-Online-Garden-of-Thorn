import json
import unittest
from pathlib import Path
from zipfile import ZipFile

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import GameEngine


ROOT = Path(__file__).resolve().parents[1]
BIO_PACKAGE = ROOT / "mods" / "Bio Cards Addition.gtnmod"
LOCAL_SOLO_WORKER = (ROOT / "static" / "js" / "local_solo_worker.js").read_text(encoding="utf-8")
DIAMOND_CHIP = (
    "[[card:Diamond|flag=wide_strike|flag=self_target|flag=exile|fission=3|swift=2]]"
)


class BioDiamondDescriptionTests(unittest.TestCase):
    def setUp(self):
        self.previous_diamond = CARD_DEFS.get("bio:diamond")
        CARD_DEFS["bio:diamond"] = CardDef(
            "bio:diamond",
            "Diamond",
            "钻石",
            2,
            0,
            "thorn",
            1,
            "Common",
            "",
            "",
        )

    def tearDown(self):
        if self.previous_diamond is None:
            CARD_DEFS.pop("bio:diamond", None)
        else:
            CARD_DEFS["bio:diamond"] = self.previous_diamond

    def test_diamond_copy_has_the_described_modifiers_and_normal_cost_rules(self):
        engine = GameEngine()
        engine.players[1].health = 100
        card = CardInstance("bio:diamond")

        engine._atomic_bio_diamond_attack(
            0,
            card,
            {"target": 1, "amount": 10},
            "",
            {"target_player": 1},
            {"target_id": 1},
        )

        self.assertEqual(engine.players[1].health, 90)
        self.assertEqual(len(engine.players[0].hand), 1)
        copied = engine.players[0].hand[0]
        self.assertEqual(copied.swift_value, 2)
        self.assertEqual(copied.fission_level, 3)
        self.assertTrue({"wide_strike", "self_target", "exile", "swift"}.issubset(copied.instance_flags))
        queued = engine.custom_vars["bio_auto_play_queue"][0]
        self.assertFalse(queued["no_cost"])

    def test_package_uses_a_diamond_chip_and_unambiguous_job_application_text(self):
        with ZipFile(BIO_PACKAGE) as package:
            self.assertIsNone(package.testzip())
            mod_data = json.loads(package.read("mod.json").decode("utf-8"))
            zh_data = json.loads(package.read("locales/zh.json").decode("utf-8"))

        diamond = next(
            card for card in mod_data["registries"]["cards"] if card["id"] == "bio:diamond"
        )
        job_application = next(
            card for card in mod_data["registries"]["cards"] if card["id"] == "bio:job_application"
        )
        self.assertEqual(
            diamond["effect_text"],
            f"对目标造成10[[icon:D]]；造成实际伤害时，额外打出1张{DIAMOND_CHIP}",
        )
        self.assertEqual(
            zh_data["cards"]["bio:diamond"]["effect_text"],
            diamond["effect_text"],
        )
        self.assertEqual(
            job_application["effect_text"],
            "使目标下个回合无法指向本牌打出者",
        )
        self.assertEqual(
            zh_data["cards"]["bio:job_application"]["effect_text"],
            job_application["effect_text"],
        )

    def test_local_solo_diamond_copy_matches_server_modifiers(self):
        start = LOCAL_SOLO_WORKER.index("effect_bio_diamond_attack(")
        end = LOCAL_SOLO_WORKER.index("\n    effect_", start + 1)
        diamond_effect = LOCAL_SOLO_WORKER[start:end]
        self.assertIn(
            "['wide_strike', 'self_target', 'exile', 'swift'].forEach",
            diamond_effect,
        )
        self.assertIn("copied.swift_value = 2;", diamond_effect)
        self.assertNotIn("this._auto_play_no_cost_for = playerId;", diamond_effect)


if __name__ == "__main__":
    unittest.main()
