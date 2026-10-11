# -*- coding: utf-8 -*-
"""轨道花瓣不因等待目标/选择而卡死（2026-10-11 排查结论的回归锁）。

排查背景：用户担心轨道使部分卡牌在轨道上触发时仍要求选择目标导致卡死。
结论与保护机制：
1. 敌向花瓣触发时没有玩家选择——默认随机指向一个存活敌人（GB-394/表15 I232）；
2. 效果结算抛 StoryActionError（如敌人已全部死亡 NO_TARGET）时记 orbit_petal_skipped，
   不中断旋转也不留下待处理状态；
3. 花瓣效果列表中不得出现会创建 pending_card_choice 的效果
   （魔法碎片入轨走 orbit_effects=(draw 2)，升级版同样不触发抉择）。

本测试对全部花瓣卡（基础+升级）模拟旋转触发，锁定以上不变量。
"""

import pytest

import story_content as sc
from story_engine import (
    _card_values,
    _new_card,
    _orbit_new_petal,
    _rotate_orbit,
    _start_combat,
)
from story_mode import build_initial_story_state


def _petal_card_ids():
    return sorted(
        cid for cid, card in sc.STORY_CARDS.items()
        if card.get('owner') == 'orbiter'
        and (card.get('orbit') or card.get('orbit_effects'))
    )


def _trigger_petal(card_id, upgraded, shield=999):
    seed = f'petal-stall-{card_id}-{int(upgraded)}'
    state = build_initial_story_state(seed, 'orbiter')
    events = []
    _start_combat(state, {'type': 'combat'}, seed, events)
    combat = state['combat']
    combat['shield'] = shield
    card = _new_card(state, card_id, upgraded)
    values = _card_values(card)
    petal = _orbit_new_petal(state, combat, card_id, values, 99, events, source='test')
    rotate_events = []
    _rotate_orbit(state, 1, seed, rotate_events)
    return state, petal, rotate_events


@pytest.mark.parametrize('card_id', _petal_card_ids())
@pytest.mark.parametrize('upgraded', [False, True])
def test_petal_trigger_never_stalls(card_id, upgraded):
    state, petal, events = _trigger_petal(card_id, upgraded)
    combat = state['combat']
    assert not combat.get('pending_card_choice'), (
        f"{card_id}(up={upgraded}) 花瓣触发留下了 pending_card_choice："
        f"{combat.get('pending_card_choice')}"
    )
    assert state.get('phase') == 'combat'


@pytest.mark.parametrize('card_id', _petal_card_ids())
@pytest.mark.parametrize('upgraded', [False, True])
def test_petal_effects_contain_no_choice_types(card_id, upgraded):
    """花瓣效果列表不应包含需要玩家交互的效果类型（防止未来新增卡破坏约束）。"""
    choice_types = {
        'choose_effect', 'choose_random_generated', 'inspect_draw_choose',
        'choose_exile', 'active_discard', 'shield_selected', 'draw_selected',
        'retrieve_from_piles',
    }
    state, petal, events = _trigger_petal(card_id, upgraded)
    types = {e.get('type') for e in petal.get('effects') or ()}
    bad = types & choice_types
    assert not bad, f'{card_id}(up={upgraded}) 花瓣效果含交互类型 {bad}'


def test_upgraded_magic_shard_petal_uses_orbit_draw():
    """升级后的魔法碎片花瓣仍走 orbit_effects=(draw 2)，不触发抉择。"""
    state, petal, events = _trigger_petal('magic_shard', True)
    types = [e.get('type') for e in petal.get('effects') or ()]
    assert types == ['draw']
    assert petal['effects'][0]['amount'] == 2


def test_enemy_target_petal_auto_picks_random_enemy():
    """敌向花瓣（如玻璃片）触发时随机指定敌人，不需要玩家选目标。"""
    state, petal, events = _trigger_petal('orbit_glass', False, shield=0)
    hits = [
        e for e in events
        if e.get('type') == 'enemy_damage' or e.get('type') == 'damage'
    ]
    assert hits, '敌向花瓣未造成伤害，目标未自动指定'


def test_dead_enemies_skip_instead_of_stall():
    """敌方全灭后非wide花瓣触发应记 NO_TARGET 跳过，而不是卡死。"""
    seed = 'petal-dead-enemies'
    state = build_initial_story_state(seed, 'orbiter')
    events = []
    _start_combat(state, {'type': 'combat'}, seed, events)
    combat = state['combat']
    for enemy in combat['enemies']:
        enemy['health'] = 0
    combat['shield'] = 999
    card = _new_card(state, 'knife', False)
    _orbit_new_petal(state, combat, 'knife', _card_values(card), 99, events, source='test')
    rotate_events = []
    _rotate_orbit(state, 1, seed, rotate_events)
    skipped = [e for e in rotate_events if e.get('type') == 'orbit_petal_skipped']
    assert skipped, '敌方全灭时应产生 orbit_petal_skipped'
    assert not combat.get('pending_card_choice')
