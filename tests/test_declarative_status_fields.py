"""自定义状态的声明式字段：层数上限、自然衰减、事件上下文。

这一批把「不依赖数值修改钩子」的行为先做成通用能力：

* ``max_stack`` 截断层数（官方霜冻也在用同一字段）；
* ``decay`` / ``decay_timing`` 在自己回合开始/结束按 one/half/clear 衰减；
* 状态事件上下文补上攻击者、受击者与伤害量，供后续迁移「受击时」类状态；
* 官方 ``arctic:frost``、``jungle:fragile``、``bio:debt``、``hel:blazing_fire``
  已经改成靠声明执行，而不是逐条写在引擎里。
"""

import pytest

import official_statuses
from game_engine import ELIXIR_RECOVERY, GameEngine
from game_engine_2v2 import GameEngine2v2
from game_engine_urf import GameEngineInfiniteFire


STATUS_ID = 'probe:charged'


def make_engine(engine_cls=GameEngine, *, round_num=2):
    engine = engine_cls()
    engine.phase = 'action'
    engine.round_num = round_num
    engine.first_player = 0
    engine.current_player = 0
    for player in engine.players:
        player.health = 100
        player.max_health = 100
        player.elixir = 0
        player.magic = 100
        player.fire = 0
        player.poison = 0
        player.hand = []
        player.deck = []
        player.discard = []
        player.exile = []
        player.equipment = []
        player.custom_statuses = {}
    return engine


def apply_status(engine, player_id, status, amount):
    engine._apply_status_op(
        player_id, None, {}, False, 'status_add_named',
        player_id, status, amount,
    )


def test_custom_status_max_stack_clamps_add():
    engine = make_engine()
    engine.v2_status_defs = {
        STATUS_ID: {'id': STATUS_ID, 'stacking': 'stack', 'max_stack': 3},
    }

    apply_status(engine, 0, STATUS_ID, 5)

    assert engine.players[0].custom_statuses[STATUS_ID] == 3


def test_custom_status_flat_decay_timing_removes_one_at_turn_start():
    engine = make_engine()
    engine.v2_status_defs = {
        STATUS_ID: {'id': STATUS_ID, 'stacking': 'stack', 'decay_timing': 'turn_start'},
    }
    engine.players[0].custom_statuses[STATUS_ID] = 3

    engine._apply_declared_status_decay(0, 'turn_start')

    assert engine.players[0].custom_statuses[STATUS_ID] == 2


def test_custom_status_decay_half_and_clear_modes():
    engine = make_engine()
    engine.v2_status_defs = {
        STATUS_ID: {
            'id': STATUS_ID,
            'stacking': 'stack',
            'decay': {'timing': 'turn_end', 'mode': 'half'},
        },
        'probe:short': {
            'id': 'probe:short',
            'stacking': 'stack',
            'decay': {'timing': 'turn_end', 'mode': 'clear'},
        },
    }
    engine.players[0].custom_statuses[STATUS_ID] = 5
    engine.players[0].custom_statuses['probe:short'] = 2

    engine._apply_declared_status_decay(0, 'turn_end')

    assert engine.players[0].custom_statuses[STATUS_ID] == 2
    assert 'probe:short' not in engine.players[0].custom_statuses


def test_official_frost_declares_cap_and_turn_end_halving():
    definition = official_statuses.engine_status_def('arctic:frost')
    assert definition['max_stack'] == 60
    assert definition['decay'] == {'timing': 'turn_end', 'mode': 'half', 'log': 'zero'}

    engine = make_engine()
    # 别名键也要能被衰减归并到规范 id，避免同一个状态留两份层数。
    engine.players[0].custom_statuses['frost'] = 5

    engine._apply_declared_status_decay(0, 'turn_end')

    assert engine.players[0].custom_statuses.get('arctic:frost') == 2
    assert 'frost' not in engine.players[0].custom_statuses


def test_official_frost_zero_keeps_legacy_log():
    engine = make_engine()
    engine.players[0].custom_statuses['arctic:frost'] = 1

    engine._apply_declared_status_decay(0, 'turn_end')

    assert 'arctic:frost' not in engine.players[0].custom_statuses
    assert any('霜冻效果消失' in str(line) for line in engine.log)


def test_official_fragile_clears_at_turn_start_through_declaration():
    definition = official_statuses.engine_status_def('jungle:fragile')
    assert definition['decay'] == {'timing': 'turn_start', 'mode': 'clear'}

    engine = make_engine(round_num=1)
    engine.players[0].custom_statuses['fragile'] = 3

    engine._apply_turn_start_effects(0)

    assert 'fragile' not in engine.players[0].custom_statuses
    assert 'jungle:fragile' not in engine.players[0].custom_statuses


@pytest.mark.parametrize('engine_cls', [GameEngine, GameEngine2v2, GameEngineInfiniteFire])
def test_official_debt_declaration_loses_elixir_after_recovery(engine_cls):
    engine = make_engine(engine_cls)
    engine.players[0].custom_statuses['bio:debt'] = 2

    if engine_cls is GameEngine2v2:
        engine._apply_turn_start_effects_2v2(0)
    else:
        engine._apply_turn_start_effects(0)

    assert engine.players[0].custom_statuses.get('bio:debt') == 1
    assert engine.players[0].elixir == ELIXIR_RECOVERY - 1
    assert any('负债使其失去1E' in str(line) for line in engine.log)


def test_official_debt_does_not_lose_elixir_while_immune_but_still_decays():
    engine = make_engine()
    engine.players[0].custom_statuses['bio:debt'] = 2
    engine.players[0].custom_statuses['status_immune'] = 1

    engine._apply_turn_start_effects(0)

    assert engine.players[0].custom_statuses.get('bio:debt') == 1
    assert engine.players[0].elixir == ELIXIR_RECOVERY
    assert not any('负债使其失去1E' in str(line) for line in engine.log)


def test_status_event_context_exposes_damage_source_and_amount():
    engine = make_engine()
    engine.v2_status_defs = {
        'probe:mark': {
            'id': 'probe:mark',
            'stacking': 'stack',
            'events': {
                'on_damage_taken': [
                    {'op': 'log', 'message': 'probe:{damage_amount}:{event_source_player}:{source}'},
                ],
            },
        },
    }
    engine.players[1].custom_statuses['probe:mark'] = 1

    engine._trigger_v2_damage_status_events(1, 0, 7)

    assert any('probe:7:0:' in str(line) for line in engine.log)
