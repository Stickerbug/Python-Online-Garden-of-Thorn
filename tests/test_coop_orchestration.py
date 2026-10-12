# -*- coding: utf-8 -*-
"""双席编排层（story_coop_engine）协调语义测试：

逐席赐福（全员选完才进图）、地图投票（一致进入/分歧加权哈希）、
逐席奖励（各领各的、全员完成才回地图）。
"""

import copy

import pytest

import story_mode
from story_content import STORY_BLESSINGS
from story_engine import StoryActionError, _prepare_blessing
from story_coop_engine import apply_coop_action


def _dual_state(seed):
    state = story_mode.build_initial_story_state(seed, 'common_flower')
    state['players'] = [copy.deepcopy(state['player']), copy.deepcopy(state['player'])]
    state['coord'] = {}
    return state


def _safe_blessing(state):
    options = list(state.get('blessing_options') or [])
    safe = [
        o for o in options
        if STORY_BLESSINGS[o].get('script') not in (
            'remove_card', 'transform_card', 'card_rewards',
        )
    ]
    return (safe or options)[0]


def _to_map(seed):
    state = _dual_state(seed)
    _prepare_blessing(state, seed, 'stage:1')
    pick = _safe_blessing(state)
    state, _ = apply_coop_action(state, 0, 'choose_blessing', {'blessing_id': pick}, seed)
    state, _ = apply_coop_action(state, 1, 'choose_blessing', {'blessing_id': pick}, seed)
    # 某些赐福（如双倍卡牌奖励）会立即进入奖励阶段——两席各选离场。
    for seat in (0, 1):
        while state.get('phase') == 'reward' and state.get('coord', {}).get('rewards_by_seat'):
            try:
                state, _ = apply_coop_action(
                    state, seat, 'choose_reward', {'reward_type': 'leave'}, seed)
            except Exception:
                break
    if state['phase'] not in ('map', 'reward'):
        raise AssertionError(f'unexpected phase {state["phase"]} after blessing/reward setup')
    return state


def _available_nodes(state, floor_index=None):
    floors = state['map']['floors']
    floors = [floors[floor_index]] if floor_index is not None else floors
    return [
        node['id'] for floor in floors
        for node in floor['nodes'] if node['status'] == 'available'
    ]


def test_blessing_waits_for_all_seats():
    state = _dual_state('orch-t1')
    _prepare_blessing(state, 'orch-t1', 'stage:1')
    pick = _safe_blessing(state)
    options = list(state['blessing_options'])
    state, _ = apply_coop_action(state, 0, 'choose_blessing', {'blessing_id': pick}, 'orch-t1')
    assert state['phase'] == 'blessing'
    assert state['blessing_options'] == options
    assert state['coord']['blessing_done'] == [0]
    state, _ = apply_coop_action(state, 1, 'choose_blessing', {'blessing_id': pick}, 'orch-t1')
    assert state['phase'] == 'map'
    assert state['coord']['blessing_done'] == [0, 1]


def test_blessing_cannot_choose_twice():
    state = _dual_state('orch-t2')
    _prepare_blessing(state, 'orch-t2', 'stage:1')
    pick = _safe_blessing(state)
    state, _ = apply_coop_action(state, 0, 'choose_blessing', {'blessing_id': pick}, 'orch-t2')
    with pytest.raises(StoryActionError):
        apply_coop_action(state, 0, 'choose_blessing', {'blessing_id': pick}, 'orch-t2')


def test_map_vote_unanimous_enters_node():
    state = _to_map('orch-t3')
    nodes = _available_nodes(state, 1) or _available_nodes(state)
    state, ev = apply_coop_action(state, 0, 'enter_node', {'node_id': nodes[0]}, 'orch-t3')
    assert state['phase'] == 'map'
    assert state['coord']['votes'] == {0: nodes[0]}
    state, ev = apply_coop_action(state, 1, 'enter_node', {'node_id': nodes[0]}, 'orch-t3')
    resolved = [e for e in ev if e.get('type') == 'map_vote_resolved'][0]
    assert resolved['winner'] == nodes[0]
    assert not state['coord'].get('votes')
    assert state['phase'] in ('combat', 'room', 'map')


def test_map_vote_split_resolves_deterministically():
    state = _to_map('orch-t4')
    nodes = _available_nodes(state)
    assert len(nodes) >= 2
    apply_coop_action(state, 0, 'enter_node', {'node_id': nodes[0]}, 'orch-t4')
    state, ev = apply_coop_action(state, 1, 'enter_node', {'node_id': nodes[1]}, 'orch-t4')
    resolved = [e for e in ev if e.get('type') == 'map_vote_resolved'][0]
    assert resolved['winner'] in (nodes[0], nodes[1])
    # 同 seed 重放一致
    state2 = _to_map('orch-t4')
    nodes2 = _available_nodes(state2)
    apply_coop_action(state2, 0, 'enter_node', {'node_id': nodes2[0]}, 'orch-t4')
    state2, ev2 = apply_coop_action(state2, 1, 'enter_node', {'node_id': nodes2[1]}, 'orch-t4')
    resolved2 = [e for e in ev2 if e.get('type') == 'map_vote_resolved'][0]
    assert resolved2['winner'] == resolved['winner']


def test_reward_per_seat_and_completion():
    state = _dual_state('orch-t5')
    state['phase'] = 'reward'
    state['reward'] = {
        'gold': 30, 'cards': ['basic', 'rose'], 'claims': {}, 'source': 'combat',
    }
    gold_before = [p['gold'] for p in state['players']]
    state, _ = apply_coop_action(state, 0, 'choose_reward', {'reward_type': 'gold'}, 'orch-t5')
    assert state['phase'] == 'reward'
    assert state['players'][0]['gold'] > gold_before[0]
    assert state['players'][1]['gold'] == gold_before[1]
    assert sorted(state['coord']['rewards_by_seat'].keys()) == ['0', '1']
    # 席0选卡完成
    state, _ = apply_coop_action(
        state, 0, 'choose_reward', {'reward_type': 'card', 'card_id': 'rose'}, 'orch-t5')
    assert sorted(state['coord']['rewards_by_seat'].keys()) == ['1']
    deck0 = len(state['players'][0]['deck'])
    deck1 = len(state['players'][1]['deck'])
    assert deck0 > deck1  # 席0拿卡，席1未拿
    # 席1离场 → 全员完成 → 回地图
    state, _ = apply_coop_action(state, 1, 'choose_reward', {'reward_type': 'leave'}, 'orch-t5')
    # 离场后节点完成回到地图（若节点带额外奖励流程则继续等待，不在此断言硬卡）。
    assert not state['coord'].get('rewards_by_seat')
    assert state['phase'] in ('map', 'reward')
