# -*- coding: utf-8 -*-
"""表15 轨道使/召唤师引擎回归：轨道上轨与旋转、召唤与号令、出牌门槛。

注意：apply_story_action 采用恢复点语义，返回**新的** state——断言必须始终
跟随返回值重新取 state['combat']，不能持有旧引用。
"""

import pytest

from story_content import STORY_CARDS, STORY_SUMMONS
from story_engine import (
    _card_values,
    _new_card,
    _start_combat,
    apply_story_action,
    _is_card_playable,
    _rotate_orbit,
    _rotate_orbit_full,
    _summon,
    _summons,
    _order_summons,
    SUMMON_SLOT_LIMIT,
)
from story_mode import build_initial_story_state


def _orbiter_combat(seed='orbit-test'):
    state = build_initial_story_state(seed, 'orbiter')
    events = []
    _start_combat(state, {'type': 'combat'}, seed, events)
    return state


def _play(state, card, payload=None, seed='orbit-test'):
    payload = dict(payload or {})
    payload['card_instance_id'] = card['instance_id']
    if state['combat']['enemies']:
        payload.setdefault('target_id', state['combat']['enemies'][0]['id'])
    return apply_story_action(state, 'play_card', payload, seed)


class TestOrbit:
    def test_orbit_card_adds_petal_and_triggers_on_rotation(self):
        state = _orbiter_combat()
        web = _new_card(state, 'web', False)
        state['combat']['hand'] = [web]
        state, _ = apply_story_action(state, 'play_card', {'card_instance_id': web['instance_id']}, 'orbit-test')
        combat = state['combat']
        orbit = combat['orbit']
        assert [(p['def_id'], p['durability']) for p in orbit['petals']] == [('web', 99)]
        assert combat['shield'] == 3

        faster = _new_card(state, 'faster', False)
        combat['hand'] = [faster]
        state, _ = _play(state, faster)
        combat = state['combat']
        orbit = combat['orbit']
        # 更快：5D + 旋转1次 → 网花瓣触发 +3S、耐久-1
        assert combat['shield'] == 6
        assert orbit['petals'][0]['durability'] == 98
        assert orbit['rotations_this_combat'] == 1
        assert int(combat['enemies'][0]['health']) < int(combat['enemies'][0]['max_health'])

    def test_petal_expires_when_durability_reaches_zero(self):
        state = _orbiter_combat('orbit-expire')
        knife = _new_card(state, 'knife', False)
        state['combat']['hand'] = [knife]
        state, _ = _play(state, knife, seed='orbit-expire')
        combat = state['combat']
        petal = next(p for p in combat['orbit']['petals'] if p['def_id'] == 'knife')
        petal['durability'] = 1
        _rotate_orbit(state, 1, 'orbit-expire', [], source='test')
        assert all(p['def_id'] != 'knife' for p in combat['orbit']['petals'])

    def test_rotate_full_triggers_each_petal_once(self):
        state = _orbiter_combat('orbit-full')
        for card_id in ('web', 'wing'):
            card = _new_card(state, card_id, False)
            state['combat']['hand'] = [card]
            state, _ = _play(state, card, seed='orbit-full')
        combat = state['combat']
        orbit = combat['orbit']
        assert len(orbit['petals']) == 2
        shield_before = int(combat['shield'])
        _rotate_orbit_full(state, 'orbit-full', [], source='test')
        assert int(combat['shield']) == shield_before + 3  # 只有网给护盾
        assert orbit['rotations_this_combat'] == 2

    def test_turn_end_does_not_rotate_without_talent(self):
        """表15 天赋表：回合结束不自动旋转——旋转来自环绕轨道天赋。"""
        state = _orbiter_combat('orbit-turnend')
        state['player']['relics'] = [
            r for r in state['player']['relics'] if r != 'orbital_surround'
        ]
        web = _new_card(state, 'web', False)
        state['combat']['hand'] = [web]
        state, _ = apply_story_action(state, 'play_card', {'card_instance_id': web['instance_id']}, 'orbit-turnend')
        durability_before = state['combat']['orbit']['petals'][0]['durability']
        state, _ = apply_story_action(state, 'end_turn', {}, 'orbit-turnend')
        if state.get('phase') == 'combat':
            assert state['combat']['orbit']['petals'][0]['durability'] == durability_before

    def test_orbital_surround_rotates_once(self):
        """表15 天赋表：环绕轨道=回合结束时轨道旋转一次（不是一圈）。"""
        from story_engine import _prepare_player_turn_end

        state = _orbiter_combat('orbit-surround')
        assert 'orbital_surround' in state['player']['relics']
        for _ in range(2):
            card = _new_card(state, 'web', False)
            state['combat']['hand'] = [card]
            state, _ = _play(state, card, seed='orbit-surround')
        combat = state['combat']
        shield_before = int(combat['shield'])
        _prepare_player_turn_end(state, 'orbit-surround', [])
        assert int(combat['shield']) == shield_before + 3  # 只触发最右侧1个网花瓣
        assert combat['orbit']['rotations_this_combat'] == 1

    def test_magic_relativity_requires_empty_orbit(self):
        state = _orbiter_combat('orbit-empty')
        rel = _new_card(state, 'magic_relativity', False)
        web = _new_card(state, 'web', False)
        state['combat']['hand'] = [rel]
        assert _is_card_playable(state, rel) is True
        state['combat']['hand'] = [rel, web]
        state, _ = _play(state, web, seed='orbit-empty')
        assert _is_card_playable(state, rel) is False

    def test_demon_plague_must_be_played_first(self):
        state = _orbiter_combat('plague-gate')
        plague = _new_card(state, 'demon_plague', False)
        web = _new_card(state, 'web', False)
        state['combat']['hand'] = [plague, web]
        state['combat']['elixir'] = 10  # 恶魔的瘟疫 4E，可支付时才强制
        assert _is_card_playable(state, web) is False
        assert _is_card_playable(state, plague) is True
        state['combat']['elixir'] = 3  # 低于4E：瘟疫不可支付，不再强制
        assert _is_card_playable(state, web) is True

    def test_demon_plague_applies_and_settles(self):
        state = _orbiter_combat('plague-apply')
        plague = _new_card(state, 'demon_plague', False)
        state['combat']['hand'] = [plague]
        state['combat']['elixir'] = 10
        state, _ = _play(state, plague, seed='plague-apply')
        enemy = state['combat']['enemies'][0]
        assert int(enemy.get('toxic_poison') or 0) == 6
        assert int(enemy.get('poison') or 0) >= 0

    def test_enemy_targeted_petals_hit_enemies_not_player(self):
        """GB-394 + 表15 I232：敌向花瓣触发时打随机敌方目标，不能落到玩家。"""
        state = _orbiter_combat('petal-dir')
        core = _new_card(state, 'reactor_core', False)
        state['combat']['hand'] = [core]
        state, _ = _play(state, core, seed='petal-dir')
        combat = state['combat']
        petal = next(p for p in combat['orbit']['petals'] if p['def_id'] == 'reactor_core')
        assert petal.get('target') == 'enemy'
        poison_before = {
            enemy['id']: int(enemy.get('poison') or 0)
            for enemy in combat['enemies']
        }
        _rotate_orbit(state, 1, 'petal-dir', [], source='test')
        # I232：默认目标改为随机敌方——只要有一个敌人中毒即符合规则。
        assert any(
            int(enemy.get('poison') or 0) > poison_before[enemy['id']]
            for enemy in combat['enemies']
        )
        assert int(combat.get('poison') or 0) == 0  # 玩家不中毒

    def test_carrot_free_when_orbit_card_played(self):
        """GB-395：胡萝卜是免费打出（0E 可打），不是先付后退。"""
        state = _orbiter_combat('carrot-free')
        web = _new_card(state, 'web', False)
        state['combat']['hand'] = [web]
        state, _ = apply_story_action(
            state, 'play_card', {'card_instance_id': web['instance_id']}, 'carrot-free',
        )
        combat = state['combat']
        carrot = _new_card(state, 'carrot', False)
        combat['hand'] = [carrot]
        combat['elixir'] = 0
        assert _is_card_playable(state, carrot) is True
        state, _ = apply_story_action(
            state, 'play_card', {'card_instance_id': carrot['instance_id']}, 'carrot-free',
        )
        assert int(state['combat']['elixir']) == 0  # 没扣也没退

        state2 = _orbiter_combat('carrot-paid')
        carrot2 = _new_card(state2, 'carrot', False)
        state2['combat']['hand'] = [carrot2]
        state2['combat']['elixir'] = 0
        assert _is_card_playable(state2, carrot2) is False  # 没用过轨道牌时 0E 打不出

    def test_splitter_extra_trigger(self):
        state = _orbiter_combat('orbit-split')
        splitter = _new_card(state, 'orbit_splitter', False)
        state['combat']['hand'] = [splitter]
        state, _ = _play(state, splitter, seed='orbit-split')
        combat = state['combat']
        assert any(eq.get('def_id') == 'orbit_splitter' for eq in combat['equipment'])
        web = _new_card(state, 'web', False)
        combat['hand'] = [web]
        state, _ = _play(state, web, seed='orbit-split')
        combat = state['combat']
        shield_after_play = int(combat['shield'])
        _rotate_orbit(state, 1, 'orbit-split', [], source='test')
        # 分裂器在场：花瓣被转到时额外结算一次（+3S×2）
        assert int(combat['shield']) == shield_after_play + 3 * 2


class TestSummons:
    def test_summon_slots_and_overflow_sacrifice(self):
        state = _orbiter_combat('summon-slots')
        combat = state['combat']
        _summon(state, 'ant_larva', 3, seed='summon-slots')
        assert len(_summons(combat)) == SUMMON_SLOT_LIMIT
        _summon(state, 'sandstorm', 1, seed='summon-slots')
        assert len(_summons(combat)) == SUMMON_SLOT_LIMIT
        assert _summons(combat)[-1]['def_id'] == 'sandstorm'  # 新召唤物进末槽
        assert _summons(combat)[0]['def_id'] == 'ant_larva'  # 队首被牺牲后前移

    def test_order_triggers_head_active_and_moves_to_tail(self):
        state = _orbiter_combat('summon-order')
        combat = state['combat']
        _summon(state, 'ant_larva', 1, seed='summon-order')
        _summon(state, 'sunflower', 1, seed='summon-order')
        assert [s['def_id'] for s in _summons(combat)] == ['ant_larva', 'sunflower']
        _order_summons(state, 1, 'summon-order', [])
        assert [s['def_id'] for s in _summons(combat)] == ['sunflower', 'ant_larva']

    def test_honey_card_deals_damage_and_orders(self):
        state = _orbiter_combat('summon-honey')
        combat = state['combat']
        _summon(state, 'ant_larva', 1, seed='summon-honey')
        honey = _new_card(state, 'honey', False)
        combat['hand'] = [honey]
        enemy_before = int(combat['enemies'][0]['health'])
        state, _ = _play(state, honey, seed='summon-honey')
        assert int(state['combat']['enemies'][0]['health']) == enemy_before - 4


class TestOrbiterDeck:
    def test_orbiter_starter_deck_and_relic(self):
        state = build_initial_story_state('orbiter-deck', 'orbiter')
        deck = state['player']['deck']
        ids = [card['def_id'] for card in deck]
        assert ids.count('basic') == 4
        assert ids.count('rose') == 5
        assert ids.count('orbit_glass') == 1
        assert ids.count('faster') == 1
        assert state['player']['relics'] == ['orbital_surround']

    def test_orbiter_cards_have_images_registered(self):
        missing = [
            card_id for card_id, definition in STORY_CARDS.items()
            if definition.get('owner') == 'orbiter'
            and definition.get('rarity') in ('common', 'rare', 'ultra')
            and not definition.get('image_url')
        ]
        assert missing == [], missing

    def test_summon_definitions_exist(self):
        for summon_id in ('ant_larva', 'sandstorm', 'sunflower'):
            assert summon_id in STORY_SUMMONS
            assert STORY_SUMMONS[summon_id].get('passive')
