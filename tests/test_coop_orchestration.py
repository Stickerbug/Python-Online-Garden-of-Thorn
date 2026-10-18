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
    # 2026-10-14：全员完成后清完成名单（残留会让下一幕赐福全员已选）。
    assert state['coord']['blessing_done'] == []


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
    # 2026-10-18 设计：投票不一致→重投（清空票箱，全员重选直到一致）。
    state = _to_map('orch-t4')
    nodes = _available_nodes(state)
    assert len(nodes) >= 2
    apply_coop_action(state, 0, 'enter_node', {'node_id': nodes[0]}, 'orch-t4')
    state, ev = apply_coop_action(state, 1, 'enter_node', {'node_id': nodes[1]}, 'orch-t4')
    assert [e for e in ev if e.get('type') == 'map_vote_revote'], '分歧必须产生重投事件'
    assert not state['coord'].get('votes'), '分歧后票箱必须清空'
    assert state['coord'].get('vote_revote_count') == 1
    assert state['phase'] == 'map', '分歧后停留在地图等待重投'
    # 重投达成一致 → 正常进入
    state, ev = apply_coop_action(state, 0, 'enter_node', {'node_id': nodes[0]}, 'orch-t4')
    state, ev = apply_coop_action(state, 1, 'enter_node', {'node_id': nodes[0]}, 'orch-t4')
    resolved = [e for e in ev if e.get('type') == 'map_vote_resolved'][0]
    assert resolved['winner'] == nodes[0]
    assert state['phase'] in ('combat', 'room', 'map')


def test_reward_per_seat_and_completion():
    state = _dual_state('orch-t5')
    state['phase'] = 'reward'
    state['reward'] = {
        'gold': 30, 'cards': ['basic', 'rose'], 'claims': {}, 'source': 'combat',
    }
    gold_before = [p['gold'] for p in state['players']]
    state, _ = apply_coop_action(state, 0, 'choose_reward', {'reward_type': 'gold'}, 'orch-t5')
    assert state['phase'] == 'reward'
    assert state['players'][0]['gold'] > gold_before[0], '行动席（席0）的金币必须进席0'
    assert state['players'][1]['gold'] == gold_before[1]
    assert sorted(state['coord']['rewards_by_seat'].keys()) == ['0', '1']
    # 2026-10-18 双席奖励区分：各席随机内容独立重掷（金币区间/卡牌三选）。
    own_cards_0 = state['coord']['rewards_by_seat']['0']['cards']
    assert isinstance(own_cards_0[0], dict), '卡牌奖励已重掷为标准选项结构'
    claim_id_0 = (own_cards_0[0].get('card_id') if isinstance(own_cards_0[0], dict) else own_cards_0[0])
    # 席0选卡：领完不等于完成（2026-10-13 口径），要点「继续」才出队
    state, _ = apply_coop_action(
        state, 0, 'choose_reward', {'reward_type': 'card', 'card_id': claim_id_0}, 'orch-t5')
    assert sorted(state['coord']['rewards_by_seat'].keys()) == ['0', '1']
    state, _ = apply_coop_action(state, 0, 'choose_reward', {'reward_type': 'continue'}, 'orch-t5')
    assert sorted(state['coord']['rewards_by_seat'].keys()) == ['1']
    deck0 = len(state['players'][0]['deck'])
    deck1 = len(state['players'][1]['deck'])
    assert deck0 > deck1  # 席0拿卡，席1未拿
    # 席1离场（最终席）→ 全员完成 → 节点推进回地图
    state, _ = apply_coop_action(state, 1, 'choose_reward', {'reward_type': 'leave'}, 'orch-t5')
    assert not state['coord'].get('rewards_by_seat')
    assert state['phase'] == 'map', '全员完成后必须推进出奖励阶段'


def test_reward_view_projection_for_waiting_seat():
    """一席完成奖励后，另一席读视角（GET/响应投影）必须能看到自己的待选奖励。"""
    from story_coop_engine import mount_coop_reward_view
    state = _dual_state('orch-t6')
    state['phase'] = 'reward'
    state['reward'] = {
        'gold': 30, 'cards': ['basic', 'rose'], 'claims': {}, 'source': 'combat',
    }
    # 席0领金币+选卡+继续 → 完成；共享 reward 被清空、仅席1待选。
    state, _ = apply_coop_action(state, 0, 'choose_reward', {'reward_type': 'gold'}, 'orch-t6')
    cards0 = state['coord']['rewards_by_seat']['0']['cards']
    claim0 = cards0[0].get('card_id') if isinstance(cards0[0], dict) else cards0[0]
    state, _ = apply_coop_action(
        state, 0, 'choose_reward', {'reward_type': 'card', 'card_id': claim0}, 'orch-t6')
    state, _ = apply_coop_action(state, 0, 'choose_reward', {'reward_type': 'continue'}, 'orch-t6')
    assert state['reward'] is None
    assert sorted(state['coord']['rewards_by_seat'].keys()) == ['1']
    # 席1读视角投影：看到本席待选奖励（2026-10-18 起为本席重掷副本）。
    mount_coop_reward_view(state, 1)
    projected = state.get('reward')
    own = state['coord']['rewards_by_seat']['1']
    assert projected and projected.get('gold') == own.get('gold')
    def _card_ids(items):
        return {i.get('card_id') if isinstance(i, dict) else i for i in (items or [])}
    assert _card_ids(projected.get('cards')) == _card_ids(own.get('cards'))
    # 投影是副本：不影响协调账本里席1的正本。
    assert _card_ids(own.get('cards')) == _card_ids(state['coord']['rewards_by_seat']['1']['cards'])
    # 已完成的席0读视角：清空（不残留席1的投影副本，等待 UI 由前端负责）。
    mount_coop_reward_view(state, 0)
    assert state['reward'] is None
    # 席1基于投影后的状态正常离场完成 → 全员完成。
    state, _ = apply_coop_action(state, 1, 'choose_reward', {'reward_type': 'leave'}, 'orch-t6')
    assert not state['coord'].get('rewards_by_seat')


def test_room_per_seat_choices_and_independent_leave():
    """房间（休息/事件/商店）逐席独立（2026-10-13 重写）：
    修复前动作直通共享房间——第一人的选择即消费房间（他人无法选择），
    第一人离场即全员被踢出。"""
    state = _dual_state('orch-room')
    state['phase'] = 'room'
    state['room'] = {'type': 'rest', 'choices': [{'id': 'heal'}, {'id': 'gold'}]}
    state['players'][0]['health'] = 30  # 先扣血，治疗才可观测
    health0 = int(state['players'][0]['health'])
    # 席0 选择治疗后，席1 仍可选择
    state, _ = apply_coop_action(state, 0, 'resolve_room', {'option': 'heal'}, 'orch-room')
    assert state['phase'] == 'room', '席1未完成时保持房间阶段'
    assert sorted(state['coord']['rooms_by_seat'].keys()) == ['1']
    assert int(state['players'][0]['health']) > health0, '席0的治疗只作用于席0'
    state, _ = apply_coop_action(state, 1, 'resolve_room', {'option': 'gold'}, 'orch-room')
    assert state['phase'] != 'room', '全员完成后应推进'
    assert not state['coord'].get('rooms_by_seat')


def test_room_shop_one_seat_leave_does_not_kick_other():
    state = _dual_state('orch-shop')
    state['phase'] = 'room'
    state['room'] = {'type': 'shop', 'choices': [{'id': 'leave'}], 'wares': []}
    state, _ = apply_coop_action(state, 0, 'resolve_room', {'option': 'leave'}, 'orch-shop')
    assert state['phase'] == 'room', '一人离场不应把另一人踢出房间'
    assert sorted(state['coord']['rooms_by_seat'].keys()) == ['1']
    state, _ = apply_coop_action(state, 1, 'resolve_room', {'option': 'leave'}, 'orch-shop')
    assert state['phase'] != 'room'
    assert not state['coord'].get('rooms_by_seat')


def test_seat1_reward_lands_in_seat1_deck_only():
    """席1的奖励必须写进席1：normalize 无战斗分支曾把别名绑回 players[0]，
    导致席1选卡/金币进席0（2026-10-12 修复）。"""
    state = _dual_state('orch-t7')
    len0 = len(state['players'][0]['deck'])
    len1 = len(state['players'][1]['deck'])
    gold0 = int(state['players'][0]['gold'] or 0)
    gold1 = int(state['players'][1]['gold'] or 0)
    state['phase'] = 'reward'
    state['reward'] = {'gold': 25, 'cards': ['basic'], 'claims': {}, 'source': 'combat'}
    state, _ = apply_coop_action(state, 1, 'choose_reward', {'reward_type': 'gold'}, 'orch-t7')
    cards1 = state['coord']['rewards_by_seat']['1']['cards']
    claim1 = cards1[0].get('card_id') if isinstance(cards1[0], dict) else cards1[0]
    state, _ = apply_coop_action(
        state, 1, 'choose_reward', {'reward_type': 'card', 'card_id': claim1}, 'orch-t7')
    assert len(state['players'][0]['deck']) == len0, '席0卡组被席1的奖励改动'
    assert int(state['players'][0]['gold'] or 0) == gold0, '席1的金币进了席0'
    assert len(state['players'][1]['deck']) == len1 + 1, '席1未拿到所选卡牌'
    assert int(state['players'][1]['gold'] or 0) > gold1, '席1未领到金币'
