# -*- coding: utf-8 -*-
"""中毒结算时机（2026-10-11 调整）：敌人行动前结算。

原在下个玩家回合开始时结算；现移到敌方回合开头、敌人出招之前。
结算口径不变：伤害 → 无滞留则减半 → 剧毒追加。
"""

import pytest

from story_engine import _start_combat, _apply_status, apply_story_action
from story_mode import build_initial_story_state


def _combat_state(seed='poison-timing-test'):
    state = build_initial_story_state(seed, 'orbiter')
    events = []
    _start_combat(state, {'type': 'combat'}, seed, events)
    return state


class TestPoisonTiming:
    def test_poison_settles_before_enemy_actions(self):
        state = _combat_state()
        combat = state['combat']
        enemy = combat['enemies'][0]
        enemy_max = int(enemy['max_health'])
        enemy['health'] = enemy_max
        _apply_status(state, enemy, 'poison', 6, [], source='test')

        state, events = apply_story_action(state, 'end_turn', {}, 'poison-timing-test')

        # 敌人受到 6 点中毒伤害（在敌人行动前）
        new_state = state
        enemy_now = next(
            e for e in new_state['combat']['enemies'] if e['id'] == enemy['id']
        )
        assert int(enemy_now['health']) == enemy_max - 6
        # 中毒减半：6 → 3
        assert int(enemy_now['poison']) == 3
        # 事件时序：poison 伤害事件先于第一个 enemy_action
        poison_idx = next(
            i for i, e in enumerate(events)
            if e.get('type') == 'enemy_damage' and e.get('source') == 'poison'
        )
        action_idx = next(i for i, e in enumerate(events) if e.get('type') == 'enemy_action')
        assert poison_idx < action_idx

    def test_poison_can_kill_enemy_before_it_acts(self):
        state = _combat_state('poison-kill-test')
        combat = state['combat']
        # 只留一个敌人，血量压到 4，上 5 层中毒 → 行动前死亡
        combat['enemies'] = combat['enemies'][:1]
        enemy = combat['enemies'][0]
        enemy['health'] = 4
        _apply_status(state, enemy, 'poison', 5, [], source='test')

        state, events = apply_story_action(state, 'end_turn', {}, 'poison-kill-test')
        enemy_now = state['combat']['enemies'][0]
        assert int(enemy_now['health']) <= 0
        # 死于中毒的敌人不再出招
        assert not any(
            e.get('type') == 'enemy_action' and e.get('enemy_id') == enemy['id']
            for e in events
        )
