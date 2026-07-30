from pathlib import Path

from cards import CARD_DEFS
from game_engine_urf import GameEngineInfiniteFire, is_infinite_excluded
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_EXCLUSIONS = {
    "Arctic Cards Addition.gtnmod": {"Icicle", "Snowflake"},
    "Bio Cards Addition.gtnmod": {"RansomMoney"},
    "Hel Cards Addition.gtnmod": {"PokerCard", "Bugatti"},
    "Jurassic Cards Addition.gtnmod": {
        "Feather",
        "MagicSoil",
        "MagicChromosome",
        "Blood",
        "Amulet",
        "Azalea",
        "Acid",
        "Torch",
        "MagicTorch",
        "Pyrite",
    },
    "Ocean Cards Addition.gtnmod": {"Needle", "DeadLeaf"},
    "Void Card Addition.gtnmod": {"Balloon", "MagicBalloon", "SlimeBall"},
}


def test_requested_mod_cards_are_excluded_from_infinite_fire():
    for package_name, card_ids in EXPECTED_EXCLUSIONS.items():
        mod = load_mod(str(ROOT / "mods" / package_name))
        assert not mod.errors, f"{package_name}: {mod.errors}"
        cards = {card.id: card for card in mod.cards}
        assert card_ids <= cards.keys()
        for card_id in card_ids:
            card = cards[card_id]
            assert "infinite_exclude" in card.flags
            assert is_infinite_excluded(card)


def test_team_limited_cards_are_excluded_from_every_infinite_fire_pool():
    jungle = load_mod(str(ROOT / "mods" / "Jungle Cards Addition.gtnmod"))
    assert not jungle.errors, jungle.errors
    monstera = next(card for card in jungle.cards if card.id == "Monstera")
    assert "team_limited" in monstera.flags
    assert is_infinite_excluded(monstera)

    engine = GameEngineInfiniteFire()
    previous = engine.allowed_card_ids
    old_monstera = CARD_DEFS.get("Monstera")
    try:
        engine.allowed_card_ids = {"Monstera", "Basic"}
        CARD_DEFS["Monstera"] = monstera.to_card_def()
        engine._build_infinite_pool()
        assert "Basic" in engine.infinite_card_pool
        assert "Monstera" not in engine.infinite_card_pool
        assert all("Monstera" not in pool["ids"] for pool in engine.infinite_by_type.values())
    finally:
        engine.allowed_card_ids = previous
        if old_monstera is None:
            CARD_DEFS.pop("Monstera", None)
        else:
            CARD_DEFS["Monstera"] = old_monstera
