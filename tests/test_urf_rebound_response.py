import pytest

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine_urf import GameEngineInfiniteFire


REBOUND_CARD_ID = "__test_urf_rebound_response__"


def setup_module():
    CARD_DEFS[REBOUND_CARD_ID] = CardDef(
        id=REBOUND_CARD_ID,
        name_en="Rebound Response Test",
        name_cn="回转响应测试",
        cost_e=1,
        cost_m=0,
        card_type="thorn",
        count=1,
        quality="test",
        description="",
        effect_text="",
        flags={"rebound"},
        damage=1,
    )


def teardown_module():
    CARD_DEFS.pop(REBOUND_CARD_ID, None)


def make_action_engine():
    engine = GameEngineInfiniteFire()
    engine.phase = "action"
    engine.round_num = 1
    engine.first_player = 0
    engine.current_player = 0
    engine.infinite_card_pool = [REBOUND_CARD_ID, "Bubble"]
    engine.infinite_card_weights = [1, 1]
    engine.infinite_by_type = {
        "thorn": {"ids": [REBOUND_CARD_ID], "weights": [1]},
        "guard": {"ids": ["Bubble"], "weights": [1]},
    }
    for player in engine.players:
        player.health = 100
        player.max_health = 100
        player.elixir = 100
        player.magic = 100
        player.hand = []
        player.deck = []
        player.discard = []
        player.exile = []
        player.equipment = []
    return engine


@pytest.mark.parametrize("use_counter", [False, True])
def test_rebound_returns_before_infinite_fire_replenishes_after_response(use_counter):
    engine = make_action_engine()
    played = CardInstance(REBOUND_CARD_ID)
    counter = CardInstance("Bubble")
    engine.players[0].hand = [played] + [CardInstance("Basic") for _ in range(9)]
    engine.players[1].hand = [counter]

    play_result = engine.play_card(0, played.instance_id, {"target_player": 1})

    assert play_result["success"]
    assert play_result["needs_response"]
    assert len(engine.players[0].hand) == 9

    response_result = engine.handle_response(1, counter.instance_id if use_counter else None)

    assert response_result["success"]
    returned = engine.players[0].find_hand_card(played.instance_id)
    assert returned is not None
    assert returned.def_id == REBOUND_CARD_ID
    assert len(engine.players[0].hand) == 10
    assert len(engine.players[0].discard) == 1
    assert engine.players[0].discard[0].def_id == REBOUND_CARD_ID
    if use_counter:
        assert len(engine.players[1].hand) == 1
        assert engine.players[1].hand[0].def_id == "Bubble"
