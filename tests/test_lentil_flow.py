# -*- coding: utf-8 -*-
"""小扁豆（lentil）全流程回归：打出→选花瓣→指针转到位并旋转一次。"""

import pytest

from story_engine import _new_card, _start_combat, apply_story_action
from story_mode import build_initial_story_state


def _orbiter_combat(seed='lentil-test'):
    state = build_initial_story_state(seed, 'orbiter')
    events = []
    _start_combat(state, {'type': 'combat'}, seed, events)
    return state


def test_lentil_play_choice_and_rotate():
    state = _orbiter_combat()
    # 轨道上放两个花瓣：web（耐久高）、knife（耐久高）
    for card_id in ('web', 'knife'):
        card = _new_card(state, card_id, False)
        state['combat']['hand'] = [card]
        state, _ = apply_story_action(state, 'play_card', {'card_instance_id': card['instance_id']}, 'lentil-test')
    orbit = state['combat']['orbit']
    assert len(orbit['petals']) == 2

    lentil = _new_card(state, 'lentil', False)
    state['combat']['hand'] = [lentil]
    state, events = apply_story_action(state, 'play_card', {'card_instance_id': lentil['instance_id']}, 'lentil-test')
    pending = state['combat'].get('pending_card_choice')
    assert pending and pending.get('kind') == 'orbit_petal'

    target_petal_id = orbit['petals'][1]['petal_id']  # 选第二个花瓣
    state, events = apply_story_action(state, 'resolve_card_choice', {
        'selected_petal_id': target_petal_id,
    }, 'lentil-test')
    combat = state['combat']
    assert not combat.get('pending_card_choice')
    # 选刀：指针转到位并旋转（触发刀）；刀花瓣效果含再旋转一次（连带触发网）。
    rotates = [e for e in events if e.get('type') == 'orbit_rotate']
    assert [e['petal']['def_id'] for e in rotates] == ['knife', 'web']
    assert combat['orbit']['pointer'] == 1
    assert state.get('phase') == 'combat'


def test_lentil_with_empty_orbit_does_nothing():
    state = _orbiter_combat('lentil-empty')
    lentil = _new_card(state, 'lentil', False)
    state['combat']['hand'] = [lentil]
    state, events = apply_story_action(state, 'play_card', {'card_instance_id': lentil['instance_id']}, 'lentil-empty')
    assert not state['combat'].get('pending_card_choice')
    assert state.get('phase') == 'combat'
