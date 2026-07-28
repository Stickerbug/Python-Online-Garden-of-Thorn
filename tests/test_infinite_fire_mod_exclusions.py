from pathlib import Path

from game_engine_urf import is_infinite_excluded
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
