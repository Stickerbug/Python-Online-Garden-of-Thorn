# -*- coding: utf-8 -*-
"""配装倾向「魔力加速」（事件 10，设计 2026-09-29）：

每回合打出的第奇数张（第1/3/5…张）不消耗 M 的牌，回复 1M。
计数按"本回合的无M费出牌"计、自己回合开始清零；带 M 消耗的牌不计数。
旧口径：跨回合 mod-2 计数（每2张回1M）。
"""

import unittest

import app  # noqa: F401  装载模组
from game_engine import CardInstance, GameEngine


class MagicAccelerationTests(unittest.TestCase):
    def build_engine(self):
        engine = GameEngine()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.max_health = 100
            player.elixir = 20
            player.magic = 0
            player.max_magic = 10
            player.hand = []
            player.deck = []
            player.discard = []
        engine.opening_event_picks[0] = 10
        engine.players[0].custom_vars['setup_magic_acceleration'] = 1
        engine.players[0].custom_vars['setup_magic_acceleration_play_count'] = 0
        return engine

    def test_odd_plays_gain_within_turn(self):
        """同回合第 1/3 张回魔，第 2/4 张不回。"""
        engine = self.build_engine()
        card = CardInstance('Bone')
        gains = []
        for _ in range(4):
            engine._apply_magic_acceleration_after_play(0, card)
            gains.append(engine.players[0].magic)
        self.assertEqual([1, 1, 2, 2], gains)

    def test_counter_resets_each_turn(self):
        """回合开始清零：新回合第 1 张又回魔。"""
        engine = self.build_engine()
        card = CardInstance('Bone')
        engine._apply_magic_acceleration_after_play(0, card)  # +1
        engine._apply_magic_acceleration_after_play(0, card)  # 不回
        engine._reset_magic_acceleration_turn_count(0)
        engine._apply_magic_acceleration_after_play(0, card)
        self.assertEqual(2, engine.players[0].magic)

    def test_magic_cost_cards_do_not_count(self):
        engine = self.build_engine()
        engine._apply_magic_acceleration_after_play(0, CardInstance('MagicPoisonStinger'))
        self.assertEqual(0, engine.players[0].custom_vars.get('setup_magic_acceleration_play_count', 0))
        self.assertEqual(0, engine.players[0].magic)

    def test_turn_start_effect_resets_counter(self):
        """_apply_turn_start_effects 挂钩清零（1v1 与 2v2 同）。"""
        engine = self.build_engine()
        engine.players[0].custom_vars['setup_magic_acceleration_play_count'] = 2
        engine._apply_turn_start_effects(0)
        self.assertNotIn('setup_magic_acceleration_play_count', engine.players[0].custom_vars)

    def test_event_text_updated(self):
        self.assertIn('第奇数张', GameEngine.OPENING_EVENTS[10]['desc'])


if __name__ == '__main__':
    unittest.main()
