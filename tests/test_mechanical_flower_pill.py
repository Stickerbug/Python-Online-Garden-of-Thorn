# -*- coding: utf-8 -*-
"""机械轨道 × 药丸免疫（2026-10-12 修复）：

机械花轨道执行玩家的「毒刺」（对目标施加中毒）时，负面状态的来源
之前记的是卡牌 id（poison_sting），药丸的 source in STORY_ENEMIES
判定漏过——拥有药丸的玩家会被"自己的毒刺"上毒。
修复：机械轨道对玩家施加状态时来源记为执行敌人。
"""

import story_mode
from story_engine import (
    _apply_status,
    _end_turn,
    _start_combat,
    apply_story_action,
)


def _combat(seed, with_pill):
    state = story_mode.build_initial_story_state(seed, 'common_flower')
    if with_pill:
        state['player']['relics'] = list(state['player'].get('relics') or []) + ['story_pill']
    events = []
    _start_combat(
        state,
        {'type': 'combat'},
        seed,
        events,
        encounter_override=[{'def_id': 'mechanical_flower'}],
    )
    return state


def _run_enemy_phase(state, seed):
    state['combat']['shield'] = 999
    return apply_story_action(state, 'end_turn', {}, seed)


def test_flower_track_poison_sting_blocked_by_pill():
    state = _combat('pill-flower', True)
    combat = state['combat']
    flower = combat['enemies'][0]
    flower['mechanical_track'] = [{
        'instance_id': 'track-poison-sting',
        'def_id': 'poison_sting',
        'upgraded': False,
        'modifiers': {},
        'track_persistent': False,
    }]
    state, events = _run_enemy_phase(state, 'pill-flower')
    combat = state['combat']
    blocked = [
        e for e in events
        if e.get('type') == 'status_blocked' and e.get('source') == 'story_pill'
    ]
    assert blocked, '药丸应拦截机械轨道施加的中毒'
    assert int(combat.get('poison') or 0) == 0, '玩家不应中毒'


def test_flower_track_poison_sting_lands_without_pill():
    state = _combat('nopill-flower', False)
    flower = state['combat']['enemies'][0]
    flower['mechanical_track'] = [{
        'instance_id': 'track-poison-sting',
        'def_id': 'poison_sting',
        'upgraded': False,
        'modifiers': {},
        'track_persistent': False,
    }]
    state, events = _run_enemy_phase(state, 'nopill-flower')
    combat = state['combat']
    applied = [
        e for e in events
        if e.get('type') == 'status'
        and e.get('status') == 'poison'
        and e.get('target_id') == 'player'
        and e.get('source') == 'mechanical_flower'
    ]
    assert applied and applied[0].get('amount') >= 5, '无药丸时机械轨道毒刺应正常给玩家上毒'
    # 敌方回合内的中毒结算会把层数折半，只要求仍有残留。
    assert int(combat.get('poison') or 0) >= 1


def test_player_own_poison_sting_not_affected_by_pill_relic_presence():
    """玩家自己打毒刺（上敌人）不受影响：药丸只挡敌方来源。"""
    state = _combat('pill-own', True)
    from story_engine import _new_card
    sting = _new_card(state, 'poison_sting', False)
    state['combat']['hand'] = [sting]
    state['combat']['elixir'] = 9
    enemy = state['combat']['enemies'][0]
    state, events = apply_story_action(state, 'play_card', {
        'card_instance_id': sting['instance_id'],
        'target_id': enemy['id'],
    }, 'pill-own')
    enemy = next(
        e for e in state['combat']['enemies'] if e.get('def_id') == 'mechanical_flower'
    )
    assert int(enemy.get('poison') or 0) >= 5
