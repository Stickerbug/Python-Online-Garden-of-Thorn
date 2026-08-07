import json
import zipfile
from pathlib import Path

from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"


def localized_card(package, language, card_id):
    with zipfile.ZipFile(MODS / package) as archive:
        locale = json.loads(archive.read(f"locales/{language}.json"))
    return locale["cards"][card_id]


def test_leaf_and_magic_leaf_locales_match_current_trigger_costs():
    for language in ("zh", "en", "fr", "ja"):
        leaf = localized_card("Vanilla Cards.gtnmod", language, "vanilla:leaf")
        magic_leaf = localized_card("Vanilla Cards.gtnmod", language, "vanilla:magicleaf")
        assert "1[[icon:E]]" in leaf["effect_text"]
        assert "8[[icon:D]]" in leaf["effect_text"]
        assert "3[[icon:M]]" in magic_leaf["effect_text"]
        assert "8[[icon:D]]" in magic_leaf["effect_text"]


def test_balance_locales_do_not_keep_old_blood_knife_avocado_or_kale_rules():
    physical_markers = {
        "zh": "实际物理伤害",
        "en": "actual physical damage",
        "fr": "dégâts physiques réels",
        "ja": "実際の物理ダメージ",
    }
    for language, marker in physical_markers.items():
        blood_knife = localized_card(
            "Bio Cards Addition.gtnmod", language, "bio:blood_knife"
        )["effect_text"]
        avocado = localized_card(
            "Garden Cards DLC.gtnmod", language, "garden:avocado"
        )["effect_text"]
        kale = localized_card(
            "Garden Cards DLC.gtnmod", language, "garden:kale"
        )["effect_text"]
        assert "7[[icon:electric_damage]]" in blood_knife
        assert marker in avocado
        assert "30%" in kale.replace(" ", "")


def test_sapphire_locales_refer_to_the_exiled_card_instead_of_a_copy():
    forbidden_copy_words = {
        "zh": "复制",
        "en": "copy",
        "fr": "copie",
        "ja": "コピー",
    }
    for language, copy_word in forbidden_copy_words.items():
        text = localized_card(
            "Ocean Cards Addition.gtnmod", language, "ocean:sapphire"
        )["effect_text"]
        assert copy_word.casefold() not in text.casefold()


def test_sewers_locales_keep_formula_placeholders_in_sync():
    for package in ("Sewers Cards Addition.gtnmod", "Sewers Cards DLC.gtnmod"):
        loaded = load_mod(str(MODS / package))
        assert not loaded.errors
        assert not loaded.warnings
