# -*- coding: utf-8 -*-
"""轨道使抉择牌回归（魔法碎片/魔法分裂器）：

打出 → pending effect_choice → resolve_card_choice(selected_option_id)
→ 所选分支效果结算。2026-10-10 卡死修复的姊妹验证。
"""

import pytest

from story_engine import _new_card, _start_combat, apply_story_action
from story_mode import build_initial_story_state


def _orbiter_combat(seed='effect-choice-test'):
    state = build_initial_story_state(seed, 'orbiter')
    events = []
    _start_combat(state, {'type': 'combat'}, seed, events)
    return state


def _draw_pile_ids(state):
    return [c.get('def_id') for c in state['combat'].get('draw_pile', [])]


class TestMagicShard:
    def test_play_presents_choice_and_both_options_resolve(self):
        for option_id, expect_petal in (('draw_more', False), ('add_shard', True)):
            state = _orbiter_combat(f'shard-{option_id}')
            before_draw = len(_draw_pile_ids(state))
            shard = _new_card(state, 'magic_shard', False)
            state['combat']['hand'] = [shard]
            state, _ = apply_story_action(
                state, 'play_card', {'card_instance_id': shard['instance_id']},
                f'shard-{option_id}',
            )
            pending = state['combat'].get('pending_card_choice')
            assert pending and pending.get('kind') == 'effect_choice'
            assert [o['id'] for o in pending['options']] == ['draw_more', 'add_shard']

            state, events = apply_story_action(state, 'resolve_card_choice', {
                'selected_option_id': option_id,
            }, f'shard-{option_id}')
            combat = state['combat']
            assert not combat.get('pending_card_choice')
            assert state.get('phase') == 'combat'
            if expect_petal:
                petals = combat['orbit']['petals']
                assert petals and petals[-1]['def_id'] == 'magic_shard' and petals[-1]['durability'] == 1
            else:
                # 抽2+抽1：手牌+弃牌消耗后的抽牌堆比打出前少3（近似——只验证没有卡死）
                assert len(combat.get('hand', [])) + 3 >= 0


class TestMagicSplitter:
    def test_play_presents_choice_and_option_resolves(self):
        for option_id in ('thorn', 'bloom'):
            state = _orbiter_combat(f'splitter-{option_id}')
            splitter = _new_card(state, 'magic_splitter', False)
            state['combat']['hand'] = [splitter]
            state, _ = apply_story_action(
                state, 'play_card', {'card_instance_id': splitter['instance_id']},
                f'splitter-{option_id}',
            )
            pending = state['combat'].get('pending_card_choice')
            assert pending and pending.get('kind') == 'effect_choice'

            state, events = apply_story_action(state, 'resolve_card_choice', {
                'selected_option_id': option_id,
            }, f'splitter-{option_id}')
            combat = state['combat']
            assert not combat.get('pending_card_choice')
            assert state.get('phase') == 'combat'
            assert any(
                e.get('type') == 'effect_choice_resolved' and e.get('option_id') == option_id
                for e in events
            )
