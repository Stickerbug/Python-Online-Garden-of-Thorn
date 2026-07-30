from unittest.mock import patch

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import EquipmentInstance
from game_engine_urf import GameEngineInfiniteFire


UNIQUE_ID = "__test_urf_unique__"
REGULAR_ID = "__test_urf_regular__"


def make_card_def(card_id: str, *, unique: bool) -> CardDef:
    return CardDef(
        id=card_id,
        name_en=card_id,
        name_cn=card_id,
        cost_e=1,
        cost_m=0,
        card_type="thorn",
        count=1,
        quality="test",
        description="",
        effect_text="",
        flags={"unique"} if unique else set(),
    )


def make_engine() -> GameEngineInfiniteFire:
    engine = GameEngineInfiniteFire()
    engine.infinite_card_pool = [UNIQUE_ID, REGULAR_ID]
    engine.infinite_card_weights = [1, 1]
    engine.infinite_by_type = {
        "thorn": {
            "ids": [UNIQUE_ID, REGULAR_ID],
            "weights": [1, 1],
        }
    }
    return engine


def setup_module():
    CARD_DEFS[UNIQUE_ID] = make_card_def(UNIQUE_ID, unique=True)
    CARD_DEFS[REGULAR_ID] = make_card_def(REGULAR_ID, unique=False)


def teardown_module():
    CARD_DEFS.pop(UNIQUE_ID, None)
    CARD_DEFS.pop(REGULAR_ID, None)


def choose_first(ids, *, weights, k):
    assert weights
    assert k == 1
    return [ids[0]]


def test_unique_card_in_hand_is_excluded_until_it_leaves_hand():
    engine = make_engine()
    player = engine.players[0]
    unique = CardInstance(UNIQUE_ID)
    player.hand = [unique]

    with patch("game_engine_urf.random.choices", side_effect=choose_first):
        drawn = engine.create_infinite_card("thorn", player_id=0)
        assert drawn.def_id == REGULAR_ID

        player.hand.remove(unique)
        player.discard.append(unique)
        drawn = engine.create_infinite_card("thorn", player_id=0)
        assert drawn.def_id == UNIQUE_ID


def test_unique_card_in_equipment_is_excluded_until_destroyed():
    engine = make_engine()
    player = engine.players[0]
    unique_equipment = EquipmentInstance(CardInstance(UNIQUE_ID), owner=0)
    player.equipment = [unique_equipment]

    with patch("game_engine_urf.random.choices", side_effect=choose_first):
        drawn = engine.create_infinite_card(player_id=0)
        assert drawn.def_id == REGULAR_ID

        player.equipment.clear()
        drawn = engine.create_infinite_card(player_id=0)
        assert drawn.def_id == UNIQUE_ID


def test_repeated_draws_immediately_exclude_the_unique_card_just_drawn():
    engine = make_engine()
    player = engine.players[0]

    with patch("game_engine_urf.random.choices", side_effect=choose_first):
        drawn = player.draw_cards(3)

    assert [card.def_id for card in drawn] == [
        UNIQUE_ID,
        REGULAR_ID,
        REGULAR_ID,
    ]
    assert sum(card.def_id == UNIQUE_ID for card in player.hand) == 1


def test_manual_replacement_never_returns_the_same_card():
    engine = make_engine()
    engine.phase = "action"
    engine.current_player = 0
    player = engine.players[0]
    original = CardInstance(REGULAR_ID)
    player.hand = [original]

    with patch("game_engine_urf.random.choices", side_effect=choose_first):
        result = engine.replace_hand_card(0, original.instance_id)

    assert result["success"]
    assert [card.def_id for card in player.hand] == [UNIQUE_ID]
    assert player.discard == [original]
    assert player.urf_replace_available is False


def test_manual_replacement_keeps_the_card_when_no_different_card_exists():
    engine = make_engine()
    engine.phase = "action"
    engine.current_player = 0
    engine.infinite_card_pool = [REGULAR_ID]
    engine.infinite_card_weights = [1]
    engine.infinite_by_type = {
        "thorn": {
            "ids": [REGULAR_ID],
            "weights": [1],
        }
    }
    player = engine.players[0]
    original = CardInstance(REGULAR_ID)
    player.hand = [original]

    result = engine.replace_hand_card(0, original.instance_id)

    assert result == {"success": False, "error": "当前没有不同的同类型牌可供替换"}
    assert player.hand == [original]
    assert player.discard == []
    assert getattr(player, "urf_replace_available", True) is True
