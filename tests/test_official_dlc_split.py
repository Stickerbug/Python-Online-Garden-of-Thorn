import json
import zipfile
from pathlib import Path

from mod_loader import OFFICIAL_MOD_DISPLAY_ORDER, load_mod
from mod_loadout_v2 import build_v2_loadout
from mod_validator_v2 import validate_mod_v2


ROOT = Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"
GAME_JS = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")

DLC_SPLITS = {
    "Arctic": ({"Pinecone", "Ruby"}, "arctic", "arctic_dlc"),
    "Bio": ({"CyanidePill", "StemCell", "Mitochondria"}, "bio", "bio_dlc"),
    "Desert": ({"MagicCompass", "Marble", "Emerald", "Topaz", "Citron", "MagicYggdrasil"}, "desert_cards_addition", "desert_dlc"),
    "Factory": ({"Lithium"}, "factory", "factory_dlc"),
    "Garden": ({"MoonRock", "Avocado", "MagicPollen", "MagicAntennae", "CatEars", "Sunflower", "Beeswax", "MagicAvocado", "MagicRice", "MagicDisc", "MagicCutter", "Kale", "Daisy", "Coal", "Grass", "Candle"}, "garden", "garden_dlc"),
    "Hel": ({"Deliverance"}, "hel", "hel_dlc"),
    "Jungle": ({"Monstera", "Dianthus", "Maple"}, "jungle", "jungle_dlc"),
    "Ocean": ({"BubbleBomb", "Shell"}, "ocean", "ocean_dlc"),
    "Sewers": ({"Iodine", "Cheese", "Perfume", "AcidBomb", "Dung", "Chitin", "Whiskers", "Neem", "Basil", "Neurotoxin", "ToiletPaper", "Quartz"}, "sewers", "sewers_dlc"),
}
PARENT_AUTHORS = {
    "Arctic": "huanxiang0273, Eric",
    "Bio": "huanxiang0273, Eric",
    "Desert": "NetherDog",
    "Factory": "Eric",
    "Garden": "NetherDog",
    "Hel": "Eric",
    "Jungle": "Eric",
    "Ocean": "huanxiang0273",
    "Sewers": "NetherDog",
}


def read_spec(path):
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read("mod.json")), set(archive.namelist())


def test_added_cards_live_only_in_independent_dlc_packages():
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


def test_dlc_packages_keep_card_ids_locales_and_assets_intact():
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


def test_each_dlc_is_adjacent_to_its_parent_and_default_disabled():
    for family in DLC_SPLITS:
        parent = f"{family} Cards Addition.gtnmod"
        dlc = f"{family} Cards DLC.gtnmod"
        parent_index = OFFICIAL_MOD_DISPLAY_ORDER.index(parent)
        assert OFFICIAL_MOD_DISPLAY_ORDER[parent_index + 1] == dlc
        assert GAME_JS.index(f"'{parent}'") < GAME_JS.index(f"'{dlc}'")
        assert f"'{dlc}'" in GAME_JS[GAME_JS.index("const FALLBACK_DEFAULT_DISABLED_MODS"):]


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
