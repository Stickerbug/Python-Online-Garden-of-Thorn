# -*- coding: utf-8 -*-
"""合作模式待选牌操作（裂解/升级/删除等窗口）席位隔离测试。

2026-10-18 修复：state['pending_deck_operations'] 原为旅程级共享队列——
一席拾取触发选牌的遗物时，另一席也弹窗且能用自己的牌结算别人的操作。
"""
import copy

import pytest

import story_mode as sm
from story_coop_engine import apply_coop_action, mount_coop_deck_ops_view
from story_engine import StoryActionError


def _dual(seed):
    state = sm.build_initial_story_state(seed, 'common_flower')
    state['players'] = [copy.deepcopy(state['player']), copy.deepcopy(state['player'])]
    state['coord'] = {}
    return state


def _fake_op(op_id, seat=None):
    op = {
        'id': op_id, 'kind': 'make_wide', 'source': 'split_wide',
        'count': 1, 'minimum': 1, 'maximum': 1, 'candidate_ids': ['c1'],
    }
    if seat is not None:
        op['seat'] = seat
    return op


def test_seat1_pending_op_not_visible_to_seat0():
    state = _dual('ops-t1')
    state['phase'] = 'map'
    # 席1有一个待选牌操作（如拾取裂解）
    state['pending_deck_operations'] = [_fake_op('op-1', seat=1)]
    # 席0读视角：不应看到席1的操作
    mount_coop_deck_ops_view(state, 0)
    assert state['pending_deck_operations'] == []
    # 席1读视角：看到自己的操作
    mount_coop_deck_ops_view(state, 1)
    assert [op['id'] for op in state['pending_deck_operations']] == ['op-1']
    # 完整队列在 coord 账本
    assert set(state['coord']['deck_ops_by_seat'].keys()) == {'1'}


def test_shared_queue_migrates_by_seat_mark():
    # 旧对局升级路径：无标记归席0，有标记按标记分组
    state = _dual('ops-t2')
    state['phase'] = 'map'
    state['pending_deck_operations'] = [_fake_op('op-a'), _fake_op('op-b', seat=1)]
    mount_coop_deck_ops_view(state, 1)
    assert [op['id'] for op in state['pending_deck_operations']] == ['op-b']
    mount_coop_deck_ops_view(state, 0)
    assert [op['id'] for op in state['pending_deck_operations']] == ['op-a']


def test_action_filters_to_own_ops_and_syncs_back():
    state = _dual('ops-t3')
    state['phase'] = 'map'
    state['pending_deck_operations'] = [_fake_op('op-mine', seat=0), _fake_op('op-theirs', seat=1)]
    # 席0行动（地图阶段选赐福会抛错，用于验证外壳的过滤/写回不破坏账本）
    with pytest.raises(StoryActionError):
        apply_coop_action(state, 0, 'choose_blessing', {'blessing_id': 'x'}, 'ops-t3')
    # 行动期间挂的是本席队列；行动后账本完整
    ledger = state['coord']['deck_ops_by_seat']
    assert set(ledger.keys()) == {'0', '1'}
    assert [op['id'] for op in ledger['0']] == ['op-mine']
    assert [op['id'] for op in ledger['1']] == ['op-theirs']


def test_single_seat_untouched():
    state = sm.build_initial_story_state('ops-solo', 'common_flower')
    op = _fake_op('op-solo')
    state['pending_deck_operations'] = [op]
    mount_coop_deck_ops_view(state, 0)
    # 单席：不引入 coord 账本，队列原样
    assert state['pending_deck_operations'] == [op]
    assert not (state.get('coord') or {}).get('deck_ops_by_seat')
