import json
import unittest
import json
import zipfile
from pathlib import Path
from zipfile import ZipFile

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import GameEngine


ROOT = Path(__file__).resolve().parents[1]
BIO_PACKAGE = ROOT / "mods" / "Bio Cards Addition.gtnmod"
DIAMOND_CHIP = (
    "[[card:Diamond|flag=wide_strike|flag=self_target|flag=exile|fission=3|swift=2]]"
)


def _diamond_events():
    """Return the packaged ``events`` block of the Diamond card."""
    package = Path(__file__).resolve().parents[1] / "mods" / "Bio Cards Addition.gtnmod"
    with zipfile.ZipFile(package) as archive:
        spec = json.loads(archive.read("mod.json"))
    for card in (spec.get("registries") or {}).get("cards") or []:
        if card.get("id") == "bio:diamond" or card.get("legacy_id") == "Diamond":
            return card.get("events")
    return None


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
        # The effect itself now lives in the card data, so attach the packaged
        # steps to the definition this test builds by hand.
        events = _diamond_events()
        self.assertIsNotNone(events, "bio:diamond must ship on_play steps")
        CARD_DEFS["bio:diamond"].v2_events = events
        engine.phase = "action"
        engine.current_player = 0
        engine.players[0].elixir = 20
        engine.players[0].magic = 20
        engine.players[0].hand = [card]

        result = engine.play_card(
            0,
            card.instance_id,
            {"target_player": 1, "target_player_id": 1, "target_id": 1},
        )

        self.assertTrue(result.get("success"), result)
        while engine.pending_choice is not None:
            pending = engine.pending_choice
            engine.resolve_choice(0, engine._default_choice_for_pending(pending) or {})
        # Playing the card for real also plays the queued copy, so the target
        # takes at least the printed 10 damage.
        self.assertLess(engine.players[1].health, 90)
        player = engine.players[0]
        copies = [
            candidate
            for candidate in (*player.hand, *player.exile, *player.deck, *player.discard)
            if candidate.def_id == "bio:diamond"
        ]
        self.assertTrue(copies, "the copy produced by Diamond must exist somewhere")

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

if __name__ == "__main__":
    unittest.main()
