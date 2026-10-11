# -*- coding: utf-8 -*-
"""魔法齿轮（表15 红标 2026-10-11）：回合结束时旋转轨道。

升级前 2 次 / 升级后 3 次；时机在回合结束失去所有费用和卡牌之后
（弃牌事件先于旋转事件）。由原“回合开始时旋转”改版。
"""

import pytest

from story_content import STORY_CARDS
from story_engine import _new_card, _start_combat, apply_story_action
from story_mode import build_initial_story_state


def _orbiter_combat(seed='magic-gear-test'):
    state = build_initial_story_state(seed, 'orbiter')
    events = []
    _start_combat(state, {'type': 'combat'}, seed, events)
    return state


def _equip_and_end(seed, upgraded):
    state = _orbiter_combat(seed)
    web = _new_card(state, 'web', False)
    state['combat']['hand'] = [web]
    state, _ = apply_story_action(state, 'play_card', {'card_instance_id': web['instance_id']}, seed)
    gear = _new_card(state, 'magic_gear', upgraded)
    state['combat']['hand'] = [gear]
    state, _ = apply_story_action(state, 'play_card', {'card_instance_id': gear['instance_id']}, seed)
    assert any(
        eq.get('def_id') == 'magic_gear'
        for eq in state['combat'].get('equipment', [])
    )
    # 手里留一张牌用于验证旋转发生在弃牌之后
    leftover = _new_card(state, 'basic', False)
    state['combat']['hand'] = [leftover]
    state, events = apply_story_action(state, 'end_turn', {}, seed)
    return state, events


class TestMagicGear:
    def test_definition_uses_end_rotate(self):
        card = STORY_CARDS['magic_gear']
        effects = card['effects']
        assert effects[0]['script'] == 'orbit_end_rotate'
        assert effects[0]['amount'] == 2
        assert card['upgrade']['effects'][0]['script'] == 'orbit_end_rotate'
        assert card['upgrade']['effects'][0]['amount'] == 3

    def test_end_turn_rotates_twice_after_discard(self):
        state, events = _equip_and_end('magic-gear-test', False)
        # 环绕轨道天赋也在回合结束旋转（同样在弃牌后，先于齿轮，1 次）。
        gear_rotates = [
            e for e in events
            if e.get('type') == 'orbit_rotate' and e.get('source') == 'equipment:magic_gear'
        ]
        assert len(gear_rotates) == 2
        event_types = [e.get('type') for e in events]
        # 时序：齿轮旋转在弃牌之后、turn_ended 之前（回合结束序列的收尾段；
        # 结束动作返回时已进入下一回合并重新抽牌，故不能用手牌为空断言）。
        assert event_types.index('turn_ended') > max(
            i for i, t in enumerate(event_types) if t == 'orbit_rotate'
        )
        # 花瓣耐久：环绕轨道 1 次 + 齿轮 2 次 = -3（web 99 → 96）
        assert state['combat']['orbit']['petals'][0]['durability'] == 96

    def test_upgraded_rotates_three_times(self):
        state, events = _equip_and_end('magic-gear-up', True)
        gear_rotates = [
            e for e in events
            if e.get('type') == 'orbit_rotate' and e.get('source') == 'equipment:magic_gear'
        ]
        assert len(gear_rotates) == 3
        # 环绕轨道 1 次 + 齿轮 3 次 = -4（web 99 → 95）
        assert state['combat']['orbit']['petals'][0]['durability'] == 95
