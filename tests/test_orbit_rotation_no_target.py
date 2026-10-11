# -*- coding: utf-8 -*-
"""轨道旋转 NO_TARGET 软锁死回归（2026-10-11 排查发现）。

场景：回合结束旋转（环绕轨道天赋/魔法齿轮）中，前一个花瓣把最后一个
敌人打死，后续非 wide 敌向花瓣（刀等）在 _card_targets 解析目标时抛
NO_TARGET。该抛出点位于 _orbit_resolve_petal 的效果级 try 之外，
会一路传出 apply_story_action —— end_turn 动作失败且每次重试同样失败，
旅程软锁死。

修复：花瓣触发前的目标解析也纳入 StoryActionError 捕获，记
orbit_petal_skipped 后结束该花瓣的触发，不再向上传播。
"""

import pytest

from story_content import STORY_CARDS
from story_engine import (
    _card_values,
    _new_card,
    _orbit_new_petal,
    _start_combat,
    apply_story_action,
)
from story_mode import build_initial_story_state


def _turn_end_with_petals(petal_ids, enemy_hp, seed, with_gear=True):
    """构造战斗：装魔法齿轮（回合结束多段旋转），轨道按顺序放花瓣，
    敌人压到低血，然后结束回合。"""
    state = build_initial_story_state(seed, 'orbiter')
    events = []
    _start_combat(state, {'type': 'combat'}, seed, events)
    combat = state['combat']
    for enemy in combat['enemies']:
        enemy['health'] = enemy_hp
    combat['shield'] = 999
    if with_gear:
        gear = _new_card(state, 'magic_gear', False)
        combat['hand'] = [gear]
        state, _ = apply_story_action(state, 'play_card', {
            'card_instance_id': gear['instance_id'],
        }, seed)
        combat = state['combat']
    for cid in petal_ids:
        card = _new_card(state, cid, False)
        _orbit_new_petal(state, combat, cid, _card_values(card), 99, events, source='test')
    return apply_story_action(state, 'end_turn', {}, seed)


def test_turn_end_rotation_survives_enemy_death():
    """击杀花瓣在前、刀在后：结束回合不应抛错，刀记一次跳过。"""
    state, events = _turn_end_with_petals(
        ['snowflake', 'knife'],
        enemy_hp=3,
        seed='turnend-notarget',
    )
    assert state.get('phase') in ('combat', 'reward', 'map')
    skipped = [
        e for e in events
        if e.get('type') == 'orbit_petal_skipped' and e.get('code') == 'NO_TARGET'
    ]
    assert skipped, '敌方全灭后非wide花瓣应记 orbit_petal_skipped(NO_TARGET)'


def test_knife_definition_is_not_wide():
    """刀是非 wide 敌向花瓣——正是会走 _card_targets 抛 NO_TARGET 的类型。"""
    card = STORY_CARDS['knife']
    assert card.get('target') == 'enemy'
    assert 'wide' not in (card.get('tags') or ())
