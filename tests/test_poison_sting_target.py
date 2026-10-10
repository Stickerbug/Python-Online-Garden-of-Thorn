# -*- coding: utf-8 -*-
"""毒刺目标取向回归（2026-10-10 用户反馈）：

毒刺是 bloom 牌但卡面写「对目标施加5层中毒」——_card 的默认 target 只把
thorn/guard 判为 enemy，bloom 缺省 self，导致中毒结算到玩家自己头上。
修复：story_content 显式声明 target='enemy'。
"""

import pytest

from story_content import STORY_CARDS
from story_engine import _new_card, _start_combat, apply_story_action
from story_mode import build_initial_story_state


def _orbiter_combat(seed='poison-sting-test'):
    state = build_initial_story_state(seed, 'orbiter')
    events = []
    _start_combat(state, {'type': 'combat'}, seed, events)
    return state


class TestPoisonStingTarget:
    def test_card_definition_targets_enemy(self):
        assert STORY_CARDS['poison_sting']['target'] == 'enemy'

    def test_poison_applies_to_chosen_enemy_not_self(self):
        state = _orbiter_combat()
        poison_sting = _new_card(state, 'poison_sting', False)
        state['combat']['hand'] = [poison_sting]
        target_id = state['combat']['enemies'][0]['id']
        state, _ = apply_story_action(state, 'play_card', {
            'card_instance_id': poison_sting['instance_id'],
            'target_id': target_id,
        }, 'poison-sting-test')
        combat = state['combat']
        enemy = next(e for e in combat['enemies'] if e['id'] == target_id)
        statuses = enemy.get('statuses') or {}
        poison = statuses.get('poison') or enemy.get('poison') or 0
        assert int(poison) >= 5
        player_statuses = combat.get('statuses') or {}
        assert not int(player_statuses.get('poison') or 0)
