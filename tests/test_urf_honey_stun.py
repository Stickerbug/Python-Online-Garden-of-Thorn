from cards import CardInstance
from game_engine_urf import GameEngineInfiniteFire


def make_action_engine():
    engine = GameEngineInfiniteFire()
    engine.phase = "action"
    engine.round_num = 2
    engine.first_player = 0
    engine.current_player = 0
    for player in engine.players:
        player.health = 100
        player.max_health = 100
        player.elixir = 10
        player.magic = 10
        player.hand = []
        player.deck = []
        player.discard = []
        player.exile = []
        player.equipment = []
        player.custom_statuses = {}
        player.custom_vars = {}
        player.honey_control_turns = 0
    return engine


def test_stun_consumes_honey_control_instead_of_postponing_the_attack():
    engine = make_action_engine()
    controlled = engine.players[1]
    attack = CardInstance("Basic")
    controlled.hand = [attack]
    controlled.skip_turn = 1
    controlled.honey_control_turns = 1
    opponent_health = engine.players[0].health

    engine._start_player_turn(1)

    assert controlled.skip_turn == 0
    assert controlled.honey_control_turns == 0
    assert attack in controlled.hand
    assert engine.players[0].health == opponent_health

    engine._end_player_turn(0)

    assert attack in controlled.hand
    assert engine.players[0].health == opponent_health
