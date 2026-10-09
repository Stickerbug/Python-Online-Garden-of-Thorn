# -*- coding: utf-8 -*-
"""反馈批次 GB-396~406 的回归测试（2026-10-07）。

GB-397 魔法玻璃/更快是起手基础卡，不应出现在战斗奖励池（rarity→primary）。
GB-398/399/405 糖棍花瓣继承整套打出效果（变形+旋转），每次触发都把全场
  花瓣耐久重置回 2 再旋转——花瓣链的 depth 又不增长，形成无限递归
  （RecursionError→"故事模式暂不可用"/结束回合请求挂死）。
GB-401/403 bloom/root 型 wide 卡（氰化物药丸/铀）默认 target=self，目标
  解析先看 target 再看 wide，效果全落到玩家自己身上。
GB-402 泡泡炸弹的 next_turn_shield 在回合边界先入账再清盾，等于白给。
GB-404 魔法相对论随机目标却要求手动选目标（thorn 默认 target=enemy）。
GB-400 蓄势待发（导弹）自动打出只在房间路径接线，单人对局从不触发。
"""

import threading
import unittest

from story_content import STORY_CARDS, story_reward_card_ids
from story_engine import (
    _card_values,
    _new_card,
    _start_combat,
    apply_story_action,
)
from story_mode import build_initial_story_state


def _orbiter_combat(seed):
    state = build_initial_story_state(seed, 'orbiter')
    events = []
    _start_combat(state, {'type': 'combat'}, seed, events)
    state['combat']['elixir'] = 30
    for enemy in state['combat']['enemies']:
        enemy['health'] = 500
    return state


def _play(state, card_id, seed, payload=None):
    card = _new_card(state, card_id, False)
    state['combat']['hand'].append(card)
    play_payload = {'card_instance_id': card['instance_id'], **(payload or {})}
    if (not payload or 'target_id' not in play_payload) and state['combat']['enemies']:
        play_payload.setdefault('target_id', state['combat']['enemies'][0]['id'])
    return apply_story_action(state, 'play_card', play_payload, seed)


class Gb397StarterRarityTests(unittest.TestCase):
    def test_orbit_starters_excluded_from_rewards(self):
        self.assertEqual(STORY_CARDS['orbit_glass']['rarity'], 'primary')
        self.assertEqual(STORY_CARDS['faster']['rarity'], 'primary')
        pool = story_reward_card_ids('orbiter')
        self.assertNotIn('orbit_glass', pool)
        self.assertNotIn('faster', pool)


class Gb399CandyStickTests(unittest.TestCase):
    def test_candy_stick_play_terminates_and_petals_do_not_retransform(self):
        result = {}

        def run():
            state = _orbiter_combat('gb399')
            state, _ = _play(state, 'web', 'gb399')
            state, _ = _play(state, 'web', 'gb399')
            state, _ = _play(state, 'candy_stick', 'gb399')
            result['petals'] = [
                (p['def_id'], p['durability'])
                for p in state['combat']['orbit']['petals']
            ]
            result['effects'] = [
                [e.get('type') for e in p['effects']]
                for p in state['combat']['orbit']['petals']
            ]

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        worker.join(timeout=20)
        self.assertFalse(worker.is_alive(), '糖棍打出后引擎未终止（无限旋转回归）')
        for effect_types in result['effects']:
            self.assertNotIn('orbit_transform_all', effect_types)
            self.assertNotIn('rotate_orbit', effect_types)

    def test_candy_stick_petal_triggers_only_random_damage(self):
        values = _card_values(_new_card(_orbiter_combat('gb399b'), 'candy_stick', False))
        self.assertEqual(
            [e.get('type') for e in values['orbit_effects']],
            ['random_damage'],
        )

    def test_lentil_rotate_into_candy_stick_petals_terminates(self):
        result = {}

        def run():
            state = _orbiter_combat('gb398')
            state, _ = _play(state, 'web', 'gb398')
            state, _ = _play(state, 'web', 'gb398')
            state, _ = _play(state, 'candy_stick', 'gb398')
            state, _ = _play(state, 'lentil', 'gb398')
            pending = state['combat'].get('pending_card_choice')
            result['kind'] = pending and pending.get('kind')
            state, _ = apply_story_action(
                state, 'resolve_card_choice',
                {'selected_petal_id': pending['petals'][0]['petal_id']},
                'gb398',
            )
            state, _ = apply_story_action(state, 'end_turn', {}, 'gb398')
            result['turn'] = state['combat']['turn']

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        worker.join(timeout=20)
        self.assertFalse(worker.is_alive(), '小扁豆旋转糖棍花瓣后引擎未终止')
        self.assertEqual(result['kind'], 'orbit_petal')
        self.assertEqual(result['turn'], 'player')


class Gb401WideSelfCardsTests(unittest.TestCase):
    def test_cyanide_pill_applies_stagnation_to_all_enemies(self):
        state = _orbiter_combat('gb401')
        state, _ = _play(state, 'cyanide_pill', 'gb401')
        enemies = state['combat']['enemies']
        self.assertTrue(enemies)
        for enemy in enemies:
            self.assertEqual(int(enemy.get('stagnation') or 0), 99)
        self.assertNotIn('stagnation', state['combat'])

    def test_uranium_applies_statuses_to_all_enemies(self):
        state = _orbiter_combat('gb403')
        state, _ = _play(state, 'uranium', 'gb403')
        enemies = state['combat']['enemies']
        self.assertTrue(enemies)
        for enemy in enemies:
            self.assertEqual(int(enemy.get('weak') or 0), 1)
            self.assertEqual(int(enemy.get('vulnerable') or 0), 1)
        self.assertEqual(int(state['combat'].get('weak') or 0), 0)
        self.assertEqual(int(state['combat'].get('vulnerable') or 0), 0)


class Gb402BubbleBombTests(unittest.TestCase):
    def test_delayed_shield_survives_turn_boundary(self):
        state = _orbiter_combat('gb402')
        state, _ = _play(state, 'bubble_bomb', 'gb402')
        self.assertEqual(int(state['combat'].get('next_turn_shield') or 0), 7)
        state['combat']['shield'] = 0
        state, _ = apply_story_action(state, 'end_turn', {}, 'gb402')
        self.assertEqual(int(state['combat'].get('shield') or 0), 7)


class Gb404MagicRelativityTests(unittest.TestCase):
    def test_relativity_targets_chosen_enemy(self):
        """表15 红标：魔法相对论从随机目标改为对目标（玩家选定敌人）。"""
        state = _orbiter_combat('gb404')
        values = _card_values(_new_card(state, 'magic_relativity', False))
        self.assertEqual(values.get('target'), 'enemy')
        health_before = sum(
            int(e.get('health') or 0) for e in state['combat']['enemies']
        )
        state, _ = _play(state, 'magic_relativity', 'gb404', payload={})
        health_after = sum(
            int(e.get('health') or 0) for e in state['combat']['enemies']
        )
        self.assertEqual(health_before - health_after, 20)


class Gb400StandReadySoloTests(unittest.TestCase):
    def test_solo_engine_fires_stand_ready_missile(self):
        import app  # noqa: F401  装载模组 CARD_DEFS（garden:missile）
        from game_engine import CardInstance, GameEngine

        engine = GameEngine()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.max_health = 100
            player.elixir = 20
            player.magic = 20
            player.hand = []
            player.deck = []
            player.discard = []
        missile = CardInstance('Missile')
        engine.players[1].hand = [missile]
        attack = CardInstance('Light')
        engine.players[0].hand = [attack]
        engine.play_card(0, attack.instance_id, {'target_player': 1, 'target_player_id': 1, 'target_id': 1})
        self.assertIsNotNone(getattr(engine, 'pending_response', None))
        fired = app._fire_stand_ready_counters_for_engine(engine, mode='1v1')
        self.assertTrue(fired)
        self.assertIsNone(getattr(engine, 'pending_response', None))
        self.assertTrue(
            all(c.instance_id != missile.instance_id for c in engine.players[1].hand),
            '导弹应已自动打出',
        )


if __name__ == '__main__':
    unittest.main()
