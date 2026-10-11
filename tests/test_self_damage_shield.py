# -*- coding: utf-8 -*-
"""自伤与护盾（2026-10-11 用户反馈）：

「刀」与「荆棘」花瓣的自伤原为 lose_health（直接失去生命，无视护盾），
卡面写的是「对自己造成 D」——应按受到伤害结算，可被护盾阻挡。
修复：两者改用 self_damage，走 _player_raw_damage（护盾/魔法护盾管线）；
赎身钱等「失去 H」文案的卡不受影响，仍直接扣生命。
"""

import pytest

from story_content import STORY_CARDS
from story_engine import (
    _new_card,
    _rotate_orbit,
    _start_combat,
    apply_story_action,
)
from story_mode import build_initial_story_state


def _orbiter_combat(seed='self-damage-test'):
    state = build_initial_story_state(seed, 'orbiter')
    events = []
    _start_combat(state, {'type': 'combat'}, seed, events)
    return state


def _player_health(state):
    return int(state['player']['health'])


class TestKnifeSelfDamage:
    def test_card_definition_uses_self_damage(self):
        effects = STORY_CARDS['knife']['effects']
        assert effects[0]['type'] == 'self_damage'
        assert effects[0]['amount'] == 2

    def test_knife_self_damage_blocked_by_shield(self):
        state = _orbiter_combat()
        combat = state['combat']
        combat['shield'] = 5
        health_before = _player_health(state)
        target_id = combat['enemies'][0]['id']
        enemy_before = int(combat['enemies'][0]['health'])

        knife = _new_card(state, 'knife', False)
        combat['hand'] = [knife]
        state, events = apply_story_action(state, 'play_card', {
            'card_instance_id': knife['instance_id'],
            'target_id': target_id,
        }, 'self-damage-test')

        assert _player_health(state) == health_before
        combat = state['combat']  # apply_story_action 返回新快照，需重取引用
        assert int(combat['shield']) == 3  # 5 - 2
        enemy = next(e for e in combat['enemies'] if e['id'] == target_id)
        assert int(enemy['health']) == enemy_before - 12
        damage_events = [
            e for e in events
            if e.get('type') == 'player_damage' and e.get('source') == 'knife'
        ]
        assert damage_events and damage_events[0]['history'][0]['blocked'] == 2

    def test_knife_self_damage_without_shield_hits_health(self):
        state = _orbiter_combat('knife-noshield')
        combat = state['combat']
        combat['shield'] = 0
        health_before = _player_health(state)
        target_id = combat['enemies'][0]['id']

        knife = _new_card(state, 'knife', False)
        combat['hand'] = [knife]
        state, events = apply_story_action(state, 'play_card', {
            'card_instance_id': knife['instance_id'],
            'target_id': target_id,
        }, 'knife-noshield')

        assert _player_health(state) == health_before - 2


class TestOrbitThornPetal:
    def test_petal_definition_uses_self_damage(self):
        effects = STORY_CARDS['orbit_thorn']['orbit_effects']
        assert effects[0]['type'] == 'self_damage'
        assert effects[0]['amount'] == 1

    def test_thorn_petal_damage_blocked_by_shield(self):
        state = _orbiter_combat('thorn-shield')
        combat = state['combat']
        # 血羽毛：抽2张牌，将1个轨道3荆棘花瓣加入轨道
        feather = _new_card(state, 'blood_feather', False)
        combat['hand'] = [feather]
        state, _ = apply_story_action(state, 'play_card', {
            'card_instance_id': feather['instance_id'],
        }, 'thorn-shield')
        petals = state['combat']['orbit']['petals']
        assert [p['def_id'] for p in petals] == ['orbit_thorn']

        combat = state['combat']
        combat['shield'] = 2
        health_before = _player_health(state)
        events = []
        # 荆棘耐久3：转3次——前2次被护盾挡住，第3次破防扣1生命。
        for _ in range(3):
            _rotate_orbit(state, 1, 'thorn-shield', events)

        assert int(combat['shield']) == 0
        assert _player_health(state) == health_before - 1
        sources = [
            e.get('source') for e in events
            if e.get('type') == 'player_damage' and e.get('source') == 'orbit_thorn'
        ]
        assert len(sources) == 3

    def test_thorn_petal_without_shield_hits_health(self):
        state = _orbiter_combat('thorn-noshield')
        combat = state['combat']
        feather = _new_card(state, 'blood_feather', False)
        combat['hand'] = [feather]
        state, _ = apply_story_action(state, 'play_card', {
            'card_instance_id': feather['instance_id'],
        }, 'thorn-noshield')

        combat = state['combat']
        combat['shield'] = 0
        health_before = _player_health(state)
        events = []
        _rotate_orbit(state, 1, 'thorn-noshield', events)
        assert _player_health(state) == health_before - 1


class TestRansomMoneyUnchanged:
    def test_redemption_money_still_loses_health_directly(self):
        """赎身钱文案为「失去H」，保持直接扣生命、无视护盾。"""
        effects = STORY_CARDS['redemption_money']['effects']
        assert effects[0]['type'] == 'lose_health'
        assert effects[0]['amount'] == 5
