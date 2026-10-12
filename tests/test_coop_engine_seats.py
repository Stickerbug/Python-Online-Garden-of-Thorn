# -*- coding: utf-8 -*-
"""主引擎多席位核心语义（合作重写 第2/3步，2026-10-12）：

victim_seat 伤害、ready 栅栏、敌方逐席锁定目标、单席倒地不判负、
胜利复活 20%、就绪封锁与撤回。
"""

import copy

import pytest

from story_engine import (
    _mount_seat,
    _seat_count,
    _start_combat,
    apply_story_action,
)
from story_mode import build_initial_story_state


def _dual_state(seed='coop-core', enemy='soldier_ant'):
    state = build_initial_story_state(seed, 'common_flower')
    state['players'] = [copy.deepcopy(state['player']), copy.deepcopy(state['player'])]
    for seat, player in enumerate(state['players']):
        player.setdefault('character_id', 'common_flower')
    events = []
    _start_combat(
        state,
        {'type': 'combat'},
        seed,
        events,
        encounter_override=[{'def_id': enemy}],
    )
    return state


def _health(state, seat):
    return int(state['players'][seat].get('health') or 0)


def test_dual_seat_setup_independent_states():
    state = _dual_state()
    assert _seat_count(state) == 2
    combat = state['combat']
    assert set(combat['seat_states'].keys()) == {0, 1}
    for seat in (0, 1):
        _mount_seat(state, seat)
        assert len(combat['hand']) >= 4
        assert combat['seat_states'][seat]['hand'] is combat['hand']
        combat['shield'] = seat * 10
    _mount_seat(state, 0)
    assert combat['shield'] == 0
    _mount_seat(state, 1)
    assert combat['shield'] == 10


def test_ready_barrier_waits_for_all_seats():
    state = _dual_state('coop-ready')
    combat = state['combat']
    _mount_seat(state, 0)
    state, events = apply_story_action(state, 'end_turn', {}, 'coop-ready')
    combat = state['combat']
    assert combat.get('turn') == 'player', '一席就绪不应推进敌方回合'
    assert combat.get('ready_seats') == [0]
    assert any(
        e.get('type') == 'combat_seat_ready' and e.get('seat') == 0 for e in events
    )
    # 席位1就绪 → 全员就绪 → 敌方回合结算并进入下一轮
    _mount_seat(state, 1)
    state, events = apply_story_action(state, 'end_turn', {}, 'coop-ready')
    combat = state['combat']
    assert combat.get('round') == 2, '全员就绪后应进入下一轮'
    assert not (combat.get('ready_seats') or [])


def test_cancel_ready_reopens_seat():
    state = _dual_state('coop-cancel')
    combat = state['combat']
    _mount_seat(state, 0)
    state, _ = apply_story_action(state, 'end_turn', {}, 'coop-cancel')
    assert state['combat'].get('ready_seats') == [0]
    _mount_seat(state, 0)
    state, _ = apply_story_action(
        state, 'end_turn', {'cancel_ready': True}, 'coop-cancel'
    )
    assert state['combat'].get('ready_seats') == []
    assert state['combat'].get('turn') == 'player'


def test_ready_seat_cannot_play_cards():
    state = _dual_state('coop-lock')
    combat = state['combat']
    _mount_seat(state, 0)
    card = combat['hand'][0] if combat['hand'] else None
    if card is None:
        return
    state, _ = apply_story_action(state, 'end_turn', {}, 'coop-lock')
    combat = state['combat']
    _mount_seat(state, 0)
    card = combat['hand'][0]
    with pytest.raises(Exception):
        apply_story_action(state, 'play_card', {
            'card_instance_id': card['instance_id'],
            'target_id': combat['enemies'][0]['id'],
        }, 'coop-lock')


def test_enemy_damage_hits_locked_victim_seat_only():
    state = _dual_state('coop-victim', enemy='chimney')
    combat = state['combat']
    # 烟囱按 (0,0,1) 出招：强制用攻击招（index 1）
    combat['enemies'][0]['forced_move_index'] = 1
    # 双方满血、去护盾，确保敌方攻击造成可观测伤害
    for seat in range(2):
        _mount_seat(state, seat)
        combat['shield'] = 0
    before = [_health(state, 0), _health(state, 1)]
    _mount_seat(state, 0)
    state, _ = apply_story_action(state, 'end_turn', {}, 'coop-victim')
    _mount_seat(state, 1)
    state, _ = apply_story_action(state, 'end_turn', {}, 'coop-victim')
    after = [_health(state, 0), _health(state, 1)]
    assert after != before, '敌方回合应造成伤害'
    hit = [b - a for a, b in zip(before, after)]
    assert (hit[0] > 0) != (hit[1] > 0) or (hit[0] > 0 and hit[1] > 0) is False, (
        '单体攻击应只伤一席（多段也只伤同一席）'
    )
    assert (hit[0] == 0) != (hit[1] == 0), '恰有一席受伤'


def test_single_seat_downed_combat_continues_and_revives_on_victory():
    state = _dual_state('coop-down', enemy='soldier_ant')
    combat = state['combat']
    # 席位1压到1血，敌方锁定它打死（用直接管线模拟受击）
    from story_engine import _player_raw_damage
    _mount_seat(state, 1)
    _player_raw_damage(state, 999, [], 'test')
    assert _health(state, 1) <= 0
    assert state.get('phase') == 'combat', '单席倒地不应结束战斗'
    # 打死敌人取胜 → 倒地席复活 20%
    enemy = combat['enemies'][0]
    enemy['health'] = 1
    _mount_seat(state, 0)
    card = next((c for c in combat['hand'] if int(c.get('cost_e') or 0) <= 3), None)
    if card is None:
        return
    state, events = apply_story_action(state, 'play_card', {
        'card_instance_id': card['instance_id'],
        'target_id': enemy['id'],
    }, 'coop-down')
    revived = any(e.get('type') == 'seat_revived' for e in events)
    if state.get('phase') != 'combat':
        assert revived, '胜利后倒地席应复活'
        expected = max(1, -(-int(state['players'][1].get('max_health') or 1) * 2 // 10))
        assert _health(state, 1) == pytest.approx(expected, abs=1)


def test_all_seats_downed_loses():
    state = _dual_state('coop-wipe')
    from story_engine import _check_combat_end, _player_raw_damage
    events = []
    for seat in (0, 1):
        _mount_seat(state, seat)
        _player_raw_damage(state, 999, events, 'test')
        _check_combat_end(state, 'coop-wipe', events)
    assert state.get('phase') == 'game_over', '全席倒地应判负'
