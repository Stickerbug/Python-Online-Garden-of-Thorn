"""烈火在 1v1 / 2v2 / 无限火力回合开始都要转成灼烧。

反馈 #113 时 2v2 的两条回合开始路径与 URF 的覆写漏了硬编码调用。现在烈火已经
迁进 ``official_statuses.py`` 的 ``events.on_turn_start_before_status_damage``，
所以三个模式只要在状态伤害结算前触发同一个阶段事件即可，不再各自调用引擎函数。
"""

from pathlib import Path

import pytest

import official_statuses
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from game_engine_urf import GameEngineInfiniteFire


ROOT = Path(__file__).resolve().parents[1]


def make_engine(engine_cls):
    engine = engine_cls()
    engine.phase = 'action'
    engine.round_num = 1
    engine.first_player = 0
    engine.current_player = 0
    for player in engine.players:
        player.health = 100
        player.max_health = 100
        player.elixir = 100
        player.magic = 100
        player.fire = 0
        player.poison = 0
        player.custom_statuses = {}
        player.hand = []
        player.deck = []
        player.discard = []
        player.exile = []
        player.equipment = []
    return engine


@pytest.mark.parametrize('engine_cls', [GameEngine, GameEngine2v2, GameEngineInfiniteFire])
def test_blazing_fire_converts_to_burn_on_own_turn_start(engine_cls):
    engine = make_engine(engine_cls)
    engine.players[0].custom_statuses['hel:blazing_fire'] = 3

    if engine_cls is GameEngine2v2:
        engine._apply_turn_start_effects_2v2(0)
    else:
        engine._apply_turn_start_effects(0)

    player = engine.players[0]
    assert player.fire == 3
    # 1v1 的既有语义：烈火转换出的 F 在同一回合开始结算。
    assert player.health == 97
    assert any('烈火施加3层灼烧' in str(line) for line in engine.log)
    assert engine.players[1].fire == 0


def test_multiplayer_turn_start_paths_all_call_blazing_fire():
    source_2v2 = (ROOT / 'game_engine_2v2.py').read_text(encoding='utf-8')
    source_urf = (ROOT / 'game_engine_urf.py').read_text(encoding='utf-8')
    phase = "'on_turn_start_before_status_damage'"
    assert source_2v2.count(phase) == 2
    assert source_urf.count(phase) == 1
    definition = official_statuses.engine_status_def('hel:blazing_fire')
    assert definition['events']['on_turn_start_before_status_damage']
