import json
import unittest
from pathlib import Path
from zipfile import ZipFile

from cards import CARD_DEFS


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "mods" / "Vanilla Cards.gtnmod"
# 旧词表（合并前）与现在的统一写法：``equipment_op`` + ``mode:"destroy"`` + ``pick:"self"``
SELF_DESTROY_OPS = {"destroy_self_equipment", "destroy_current_equipment"}
DESTROY_EQUIPMENT_MODES = {"destroy", "break", "smash", "摧毁"}
SELF_PICKS = {"self", "this", "自己", "自身"}
SELF_DESTROY_WORDING = "触发：摧毁本装备；"


def _contains_self_destroy_step(value):
    if isinstance(value, dict):
        if value.get("op") in SELF_DESTROY_OPS:
            return True
        if str(value.get("op") or "") == "equipment_op":
            mode = str(value.get("mode") or value.get("action") or "").strip().lower()
            pick = str(value.get("pick") or "").strip().lower()
            if mode in DESTROY_EQUIPMENT_MODES and pick in SELF_PICKS:
                return True
        return any(_contains_self_destroy_step(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_self_destroy_step(item) for item in value)
    return False


class VanillaSelfDestroyDescriptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with ZipFile(PACKAGE) as package:
            cls.mod_data = json.loads(package.read("mod.json").decode("utf-8"))
            cls.locales = {
                language: json.loads(
                    package.read(f"locales/{language}.json").decode("utf-8")
                )
                for language in ("zh", "en", "fr", "ja")
            }

    def test_every_self_destroying_trigger_discloses_the_destruction(self):
        self_destroying_cards = {
            card["legacy_id"]: card
            for card in self.mod_data["registries"]["cards"]
            if _contains_self_destroy_step(card.get("events", {}))
        }

        self.assertEqual(
            set(self_destroying_cards),
            {"Leaf", "MagicLeaf", "Mark", "Mine"},
        )
        for card_id, card in self_destroying_cards.items():
            with self.subTest(card_id=card_id):
                self.assertIn(SELF_DESTROY_WORDING, card["effect_text"])

    def test_mark_and_magic_leaf_sources_and_locales_stay_in_sync(self):
        cards_by_legacy_id = {
            card["legacy_id"]: card
            for card in self.mod_data["registries"]["cards"]
        }
        for card_id, locale_id in (
            ("MagicLeaf", "vanilla:magicleaf"),
            ("Mark", "vanilla:mark"),
        ):
            with self.subTest(card_id=card_id):
                packaged = cards_by_legacy_id[card_id]
                fallback = CARD_DEFS[card_id]
                zh = self.locales["zh"]["cards"][locale_id]
                self.assertIn(SELF_DESTROY_WORDING, packaged["effect_text"])
                self.assertIn(SELF_DESTROY_WORDING, fallback.effect_text)
                self.assertEqual(zh["effect_text"], packaged["effect_text"])
                self.assertNotIn("trigger_effect_text", packaged)
                self.assertNotIn("trigger_effect_text", zh)
                self.assertEqual(fallback.trigger_effect_text, "")

        translated_effects = {
            language: self.locales[language]["cards"]["vanilla:mark"]["effect_text"]
            for language in ("en", "fr", "ja")
        }
        self.assertIn("destroy this equipment", translated_effects["en"].lower())
        self.assertIn("détruisez cet équipement", translated_effects["fr"].lower())
        self.assertIn("この装備を破壊", translated_effects["ja"])


class AllModSelfDestroyDescriptionTests(unittest.TestCase):
    def test_manual_self_destroy_triggers_only_describe_it_on_the_card_face(self):
        checked = []
        for package_path in sorted((ROOT / "mods").glob("*.gtnmod")):
            with ZipFile(package_path) as package:
                mod_data = json.loads(package.read("mod.json").decode("utf-8"))
            for card in mod_data.get("registries", {}).get("cards", []):
                trigger = card.get("events", {}).get("on_equipment_trigger", {})
                if not _contains_self_destroy_step(trigger):
                    continue
                checked.append((package_path.name, card["id"]))
                with self.subTest(package=package_path.name, card_id=card["id"]):
                    self.assertIn(SELF_DESTROY_WORDING, card.get("effect_text", ""))
                    self.assertNotIn("trigger_effect_text", card)

        # 自毁触发全部改成数据步骤后，这里显式列出应被检出的牌：
        # 词表一旦再次改名（以前就发生过），这条断言会立刻失败而不是静静变成 0 条。
        self.assertEqual(set(checked), {
            ("Bio Cards DLC.gtnmod", "bio:stem_cell"),
            ("Desert Cards Addition.gtnmod", "desert_cards_addition:coconut"),
            ("Jungle Cards Addition.gtnmod", "jungle:flower"),
            ("Sewers Cards DLC.gtnmod", "sewers:iodine"),
            ("Vanilla Cards.gtnmod", "vanilla:leaf"),
            ("Vanilla Cards.gtnmod", "vanilla:magicleaf"),
            ("Vanilla Cards.gtnmod", "vanilla:mark"),
            ("Vanilla Cards.gtnmod", "vanilla:mine"),
            ("Void Card Addition.gtnmod", "void:satan_cross"),
        })


if __name__ == "__main__":
    unittest.main()
