# -*- coding: utf-8 -*-
"""反制窗口节奏（设计 2026-09-28）：2s 保底 + 5s 上限 + 装备牌豁免 + solo 即时。

- 2v2：有人可反制 5s 窗 / 无人可反制非装备牌 2s 强制等待 / 装备牌直接结算
- 1v1：response_pacing=True（真实房间）才有 2s 等待与 5s 服务端时限；
  默认（solo/AI 训练）保持即时结算
- 2s 内到达的响应由 app 层压到整 2s 再结算（_response_window_hold_seconds）
"""

import unittest

import app  # noqa: F401  装载模组（2v2 声明式反制需要）
from game_engine import CardInstance, GameEngine
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


class EquipmentNoWaitTests(unittest.TestCase):
    """装备牌（root）无人可反制时不开 2s 强制等待，直接结算。"""

    def build_2v2(self):
        engine = GameEngine2v2()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.elixir = 10
            player.magic = 10
            player.hand = []
        return engine

    def test_2v2_equipment_skips_forced_wait(self):
        engine = self.build_2v2()
        leaf = CardInstance('Leaf')
        pending = engine._build_pending_response_for_card(0, leaf, None)
        self.assertIsNone(pending)
        self.assertIsNone(engine.pending_response)

    def test_1v1_equipment_skips_forced_wait_even_with_pacing(self):
        engine = GameEngine()
        engine.response_pacing = True
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.elixir = 10
            player.magic = 10
            player.hand = []
        leaf = CardInstance('Leaf')
        result = engine._check_card_response_after_choice(0, leaf, None)
        self.assertIsNone(result)
        self.assertIsNone(engine.pending_response)


class OneVonePacingTests(unittest.TestCase):
    def build_engine(self, pacing):
        engine = GameEngine()
        engine.response_pacing = pacing
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.elixir = 10
            player.magic = 10
            player.hand = []
        return engine

    def test_paced_no_counter_opens_two_second_wait(self):
        """真实对局：无人可反制的非装备牌也开 2s 纯等待窗。"""
        import time
        engine = self.build_engine(pacing=True)
        thorn = CardInstance('Basic')
        result = engine._check_card_response_after_choice(0, thorn, target_choice(1))
        self.assertIsNotNone(result)
        pending = engine.pending_response
        self.assertTrue(pending.get('forced_wait'))
        remaining = pending['forced_deadline'] - time.time()
        self.assertGreater(remaining, 1.0)
        self.assertLessEqual(remaining, 2.0)
        # 到点结算：直接执行被打出的牌
        health_before = engine.players[1].health
        resolved = engine.resolve_forced_response()
        self.assertTrue(resolved.get('success'))
        self.assertIsNone(engine.pending_response)
        self.assertLess(engine.players[1].health, health_before)

    def test_solo_default_stays_instant(self):
        """solo/AI 默认不开节奏：无人可反制时直接结算（无 pending）。"""
        engine = self.build_engine(pacing=False)
        thorn = CardInstance('Basic')
        result = engine._check_card_response_after_choice(0, thorn, target_choice(1))
        self.assertIsNone(result)
        self.assertIsNone(engine.pending_response)

    def test_paced_counter_window_has_five_second_deadline(self):
        """真实对局：有人可反制时 pending 带服务端 5s 时限。"""
        import time
        engine = self.build_engine(pacing=True)
        thorn = CardInstance('Basic')
        engine.players[1].hand = [CardInstance('Bubble')]
        result = engine._check_card_response_after_choice(0, thorn, target_choice(1))
        self.assertIsNotNone(result)
        pending = engine.pending_response
        self.assertFalse(pending.get('forced_wait'))
        self.assertIsNotNone(pending.get('window_deadline'))
        remaining = pending['window_deadline'] - time.time()
        self.assertGreater(remaining, 3.5)
        self.assertLessEqual(remaining, 5.0)

    def test_unpaced_counter_window_has_no_server_deadline(self):
        """solo/AI：可反制窗口不带服务端时限（保持客户端节奏）。"""
        engine = self.build_engine(pacing=False)
        thorn = CardInstance('Basic')
        engine.players[1].hand = [CardInstance('Bubble')]
        result = engine._check_card_response_after_choice(0, thorn, target_choice(1))
        self.assertIsNotNone(result)
        pending = engine.pending_response
        self.assertFalse(pending.get('forced_wait'))
        self.assertIsNone(pending.get('window_deadline'))


class ResponseWindowHoldTests(unittest.TestCase):
    """2s 保底：窗口开启 2s 内不结算（app 层压到整 2s 处理）。"""

    def test_hold_within_two_seconds(self):
        import time
        pending = {'forced_wait': False, 'window_deadline': time.time() + 5,
                   '_created_at': time.time() - 0.3}
        hold = app._response_window_hold_seconds(pending)
        self.assertGreater(hold, 1.2)
        self.assertLessEqual(hold, 2.0)

    def test_no_hold_after_two_seconds(self):
        import time
        pending = {'forced_wait': False, 'window_deadline': time.time() + 5,
                   '_created_at': time.time() - 2.5}
        self.assertEqual(app._response_window_hold_seconds(pending), 0.0)

    def test_no_hold_for_forced_wait_or_unpaced(self):
        import time
        forced = {'forced_wait': True, 'forced_deadline': time.time() + 2,
                  '_created_at': time.time()}
        self.assertEqual(app._response_window_hold_seconds(forced), 0.0)
        unpaced = {'forced_wait': False, '_created_at': time.time()}
        self.assertEqual(app._response_window_hold_seconds(unpaced), 0.0)


if __name__ == '__main__':
    unittest.main()
