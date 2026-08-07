import json
import zipfile
from pathlib import Path

from mod_loader import OFFICIAL_MOD_DISPLAY_ORDER, load_mod
from mod_loadout_v2 import build_v2_loadout
from mod_validator_v2 import validate_mod_v2


ROOT = Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"
GAME_JS = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")
APP_PY = (ROOT / "app.py").read_text(encoding="utf-8")

MERGED_DLC = {
    "Arctic": (
        {"Pinecone", "Ruby"},
        "arctic",
        "huanxiang0273, Eric, XinYu",
        {"card-art/pinecone.svg", "card-art/ruby.svg"},
    ),
    "Factory": (
        {"Lithium"},
        "factory",
        "Eric, XinYu",
        {"card-art/Lithium.svg"},
    ),
    "Hel": (
        {"Deliverance"},
        "hel",
        "Eric, AArcC",
        {"card-art/deliverance.svg"},
    ),
    "Ocean": (
        {"BubbleBomb", "Shell"},
        "ocean",
        "huanxiang0273, XinYu",
        {"card-art/bubble bomb.svg", "card-art/shell.svg"},
    ),
}

DLC_SPLITS = {
    "Bio": ({"CyanidePill", "StemCell", "Mitochondria"}, "bio", "bio_dlc"),
    "Desert": ({"MagicCompass", "Marble", "Emerald", "Topaz", "Citron", "MagicYggdrasil"}, "desert_cards_addition", "desert_dlc"),
    "Garden": ({"MoonRock", "Avocado", "MagicPollen", "MagicAntennae", "CatEars", "Sunflower", "Beeswax", "MagicAvocado", "MagicRice", "MagicDisc", "MagicCutter", "Kale", "Daisy", "Coal", "Grass", "Candle"}, "garden", "garden_dlc"),
    "Jungle": ({"Monstera", "Dianthus", "Maple"}, "jungle", "jungle_dlc"),
    "Sewers": ({"Iodine", "Cheese", "Perfume", "AcidBomb", "Dung", "Chitin", "Whiskers", "Neem", "Basil", "Neurotoxin", "ToiletPaper", "Quartz"}, "sewers", "sewers_dlc"),
}

PARENT_AUTHORS = {
    "Bio": "huanxiang0273, Eric",
    "Desert": "NetherDog",
    "Garden": "NetherDog",
    "Jungle": "Eric",
    "Sewers": "NetherDog",
}


def read_spec(path):
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read("mod.json")), set(archive.namelist())


def test_selected_dlc_cards_are_merged_into_v110_parent_packages():
    for family, (expected_cards, namespace, author, expected_assets) in MERGED_DLC.items():
        parent_path = MODS / f"{family} Cards Addition.gtnmod"
        retired_dlc_path = MODS / f"{family} Cards DLC.gtnmod"
        parent = load_mod(str(parent_path))
        assert not parent.errors, (parent_path.name, parent.errors)
        assert not retired_dlc_path.exists()
        assert expected_cards <= {card.id for card in parent.cards}
        assert parent.info.version == "1.1.0"
        assert parent.info.author == author
        assert build_v2_loadout([parent]).ok

        spec, members = read_spec(parent_path)
        cards = spec["registries"]["cards"]
        merged_cards = [card for card in cards if card.get("legacy_id") in expected_cards]
        assert {card["legacy_id"] for card in merged_cards} == expected_cards
        assert all(card["id"].startswith(f"{namespace}:") for card in merged_cards)
        assert expected_assets <= members
        with zipfile.ZipFile(parent_path) as archive:
            resource_ids = {card["id"] for card in merged_cards}
            for language in ("zh", "en", "fr", "ja"):
                locale = json.loads(archive.read(f"locales/{language}.json"))
                assert resource_ids <= set(locale.get("cards") or {})


def test_unmerged_dlc_cards_remain_in_independent_packages():
    for family, (expected_cards, namespace, mod_id) in DLC_SPLITS.items():
        parent_path = MODS / f"{family} Cards Addition.gtnmod"
        dlc_path = MODS / f"{family} Cards DLC.gtnmod"
        parent = load_mod(str(parent_path))
        dlc = load_mod(str(dlc_path))
        assert not parent.errors, (parent_path.name, parent.errors)
        assert not dlc.errors, (dlc_path.name, dlc.errors)

        parent_ids = {card.id for card in parent.cards}
        dlc_ids = {card.id for card in dlc.cards}
        assert dlc_ids == expected_cards
        assert parent_ids.isdisjoint(expected_cards)
        assert parent.info.version == "1.0.0"
        assert parent.info.author == PARENT_AUTHORS[family]

        manifest = dlc.manifest.to_dict()
        assert manifest["id"] == mod_id
        assert manifest["resource_namespace"] == namespace
        assert manifest["dependencies"] == []
        assert manifest["optional_dependencies"] == []
        assert manifest["load_after"] == []
        assert manifest["load_before"] == []
        assert dlc.info.version == "1.0.0"
        assert build_v2_loadout([dlc]).ok
        assert build_v2_loadout([parent, dlc]).ok


def test_unmerged_dlc_packages_keep_card_ids_locales_and_assets_intact():
    for family, (expected_cards, namespace, _) in DLC_SPLITS.items():
        path = MODS / f"{family} Cards DLC.gtnmod"
        spec, members = read_spec(path)
        cards = spec["registries"]["cards"]
        assert {card["legacy_id"] for card in cards} == expected_cards
        assert all(card["id"].startswith(f"{namespace}:") for card in cards)
        for card in cards:
            image = (card.get("assets") or {}).get("image")
            if image:
                assert image in members
        with zipfile.ZipFile(path) as archive:
            resource_ids = {card["id"] for card in cards}
            for language in ("zh", "en", "fr", "ja"):
                locale = json.loads(archive.read(f"locales/{language}.json"))
                assert resource_ids <= set(locale.get("cards") or {})


def test_each_remaining_dlc_is_adjacent_to_its_parent_and_default_disabled():
    for family in DLC_SPLITS:
        parent = f"{family} Cards Addition.gtnmod"
        dlc = f"{family} Cards DLC.gtnmod"
        parent_index = OFFICIAL_MOD_DISPLAY_ORDER.index(parent)
        assert OFFICIAL_MOD_DISPLAY_ORDER[parent_index + 1] == dlc
        assert GAME_JS.index(f"'{parent}'") < GAME_JS.index(f"'{dlc}'")
        assert f"'{dlc}'" in GAME_JS[GAME_JS.index("const FALLBACK_DEFAULT_DISABLED_MODS"):]


def test_merged_dlc_filenames_are_retired_but_remain_display_aliases():
    order_section = GAME_JS.split("const OFFICIAL_MOD_DISPLAY_ORDER = [", 1)[1].split("];", 1)[0]
    client_retired = GAME_JS.split("const RETIRED_OFFICIAL_MOD_FILENAMES", 1)[1].split("]);", 1)[0]
    server_retired = APP_PY.split("RETIRED_OFFICIAL_MOD_FILENAMES = {", 1)[1].split("}", 1)[0]
    alias_section = GAME_JS.split("const OFFICIAL_MOD_DISPLAY_ALIASES = [", 1)[1].split("];", 1)[0]
    for family in MERGED_DLC:
        retired = f"{family} Cards DLC.gtnmod"
        assert retired not in order_section
        assert retired in client_retired
        assert retired in server_retired
        assert retired.casefold() in alias_section


def test_resource_namespace_alias_is_reserved_for_trusted_packages():
    payload = {
        "format_version": 2,
        "manifest": {
            "id": "example_dlc",
            "resource_namespace": "example_parent",
            "name": "Example DLC",
            "version": "1.0.0",
            "api_version": "2.0",
        },
        "registries": {
            "cards": [{"id": "example_parent:card"}],
        },
    }
    trusted = validate_mod_v2(payload, allow_reserved_namespaces=True)
    community = validate_mod_v2(payload, allow_reserved_namespaces=False)
    assert trusted.ok, trusted.errors
    assert any("resource_namespace" in error for error in community.errors)
