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
        # 玩家2持有可反制技能的魔导护符 → 有人可反制的 5s 窗口
        engine.players[2].hand = [CardInstance('MagicNazar')]
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
        engine.players[2].hand = [CardInstance('MagicNazar')]
        engine.play_card(0, skill.instance_id, 0, target_choice(0))
        pending = engine.pending_response
        self.assertFalse(pending.get('forced_wait'))
        self.assertIn(2, pending.get('responder_ids') or [])
        self.assertIn(3, pending.get('responder_ids') or [])
        self.assertEqual(pending.get('passed_responder_ids'), [])

    def test_forced_wait_is_silent_two_second_wait(self):
        """无人可反制：纯等待窗（forced_deadline≈2s），不发响应面板。"""
        engine = self.build_engine()
        thorn = CardInstance('Stinger')
        engine.players[0].hand = [thorn]
        engine.play_card(0, thorn.instance_id, 2, target_choice(2))
        pending = engine.pending_response
        self.assertIsNotNone(pending)
        self.assertTrue(pending.get('forced_wait'))
        self.assertIsNone(pending.get('window_deadline'))
        import time
        remaining = pending['forced_deadline'] - time.time()
        self.assertGreater(remaining, 1.0)
        self.assertLessEqual(remaining, 2.0)

    def test_forced_wait_resolves_via_resolve_forced_response(self):
        """纯等待窗到点由 app 层 worker 调 resolve_forced_response 结算。"""
        engine = self.build_engine()
        thorn = CardInstance('Stinger')
        target = engine.players[2]
        health_before = target.health
        engine.players[0].hand = [thorn]
        engine.play_card(0, thorn.instance_id, 2, target_choice(2))
        result = engine.resolve_forced_response()
        self.assertTrue(result.get('success'))
        self.assertIsNone(engine.pending_response)
        self.assertLess(target.health, health_before)


if __name__ == '__main__':
    unittest.main()
