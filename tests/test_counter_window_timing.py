# -*- coding: utf-8 -*-
"""2v2 反制窗口（9.22 #零-5 修订）：5s 上限 + 全员提前表态立即结算。"""

import unittest

import app  # noqa: F401  装载模组（2v2 声明式反制需要）
from game_engine import CardInstance
from game_engine_2v2 import GameEngine2v2


def target_choice(player_id):
    return {'target_player': player_id, 'target_player_id': player_id, 'target_id': player_id}


class CounterWindowTimingTests(unittest.TestCase):
    def build_engine(self):
        engine = GameEngine2v2()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.elixir = 10
            player.magic = 10
            player.hand = []
        return engine

    def test_window_upper_bound_is_five_seconds(self):
        engine = self.build_engine()
        self.assertEqual(engine.FORCED_RESPONSE_WINDOW_SECONDS, 5.0)
        skill = CardInstance('ManaOrb')
        engine.players[0].hand = [skill]
        engine.play_card(0, skill.instance_id, 0, target_choice(0))
        pending = engine.pending_response
        self.assertIsNotNone(pending)
        self.assertIsNotNone(pending.get('window_deadline'))
        # deadline 与现在差约 5s（允许调度误差）
        import time
        remaining = pending['window_deadline'] - time.time()
        self.assertGreater(remaining, 3.5)
        self.assertLessEqual(remaining, 5.0)

    def test_pending_carries_responder_ids_and_passed_set(self):
        engine = self.build_engine()
        skill = CardInstance('ManaOrb')
        engine.players[0].hand = [skill]
        engine.play_card(0, skill.instance_id, 0, target_choice(0))
        pending = engine.pending_response
        self.assertIn(2, pending.get('responder_ids') or [])
        self.assertIn(3, pending.get('responder_ids') or [])
        self.assertEqual(pending.get('passed_responder_ids'), [])

    def test_forced_wait_window_responders_tracked(self):
        # 精准牌（对手无反制牌）→ forced_wait 窗，responder_ids 仍要存全集
        engine = self.build_engine()
        thorn = CardInstance('Stinger')
        engine.players[0].hand = [thorn]
        result = engine.play_card(0, thorn.instance_id, 2, target_choice(2))
        pending = engine.pending_response
        self.assertIsNotNone(pending)
        self.assertTrue(pending.get('forced_wait'))
        self.assertIn(2, pending.get('responder_ids') or [])

    def test_forced_wait_all_pass_resolves_immediately(self):
        engine = self.build_engine()
        thorn = CardInstance('Stinger')
        target = engine.players[2]
        health_before = target.health
        engine.players[0].hand = [thorn]
        result = engine.play_card(0, thorn.instance_id, 2, target_choice(2))
        pending = engine.pending_response
        self.assertTrue(pending.get('forced_wait'))
        response = engine.pass_forced_wait_response(2)
        # 全部响应者（只有玩家2）表态 → 立即结算：无 pending、伤害已生效
        self.assertTrue(response.get('success'))
        self.assertIsNone(engine.pending_response)
        self.assertLess(target.health, health_before)

    def test_forced_wait_partial_pass_keeps_window(self):
        # 广域技能牌（非攻击）→ 敌方全体（玩家2、3）都是响应者。
        engine = self.build_engine()
        skill = CardInstance('ManaOrb')
        engine.players[0].hand = [skill]
        engine.play_card(0, skill.instance_id, 0, target_choice(0))
        pending = engine.pending_response
        self.assertTrue(pending.get('forced_wait'))
        self.assertEqual(set(pending.get('responder_ids') or []), {2, 3})
        response = engine.pass_forced_wait_response(3)
        # 玩家3表态，玩家2未表态：窗口保持
        self.assertTrue(response.get('success'))
        self.assertTrue(response.get('response_passed'))
        self.assertIsNotNone(engine.pending_response)
        self.assertIn(3, engine.pending_response.get('passed_responder_ids') or [])
        # 玩家2再表态 → 立即结算
        response = engine.pass_forced_wait_response(2)
        self.assertTrue(response.get('success'))
        self.assertIsNone(engine.pending_response)

    def test_pass_forced_wait_rejects_non_responder(self):
        engine = self.build_engine()
        thorn = CardInstance('Stinger')
        engine.players[0].hand = [thorn]
        engine.play_card(0, thorn.instance_id, 2, target_choice(2))
        response = engine.pass_forced_wait_response(1)  # 队友，不是响应者
        self.assertFalse(response.get('success'))
        self.assertIsNotNone(engine.pending_response)


if __name__ == '__main__':
    unittest.main()
