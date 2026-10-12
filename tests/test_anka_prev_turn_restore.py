# -*- coding: utf-8 -*-
"""安卡回溯（2026-10-12 修复）：自己回合内使用要回到「上个」自己回合开始的状态。

修复前：快照在自己回合开始即被覆盖，自己回合内回退只回到本回合开始；
修复后：保存新快照时旧档挪到 prev_turn_start_snapshot，目标=当前回合玩家
时回退用上一份（首个自己回合无上一份时退回本回合快照）。
"""

import unittest

import app  # noqa: F401  装载模组
from game_engine import CardInstance, GameEngine


class AnkaPrevTurnRestoreTests(unittest.TestCase):
    def build(self):
        engine = GameEngine()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.max_health = 100
            player.hand = []
            player.deck = []
            player.discard = []
        return engine

    def test_self_restore_uses_previous_own_turn_start(self):
        engine = self.build()
        ps = engine.players[0]
        # 第1个自己回合开始：H100/E3/M5
        ps.health, ps.elixir, ps.magic = 100, 3, 5
        engine._save_turn_start_snapshot(0)
        # 回合内漂移 + 回合结束，第2个自己回合开始：H80/E3/M7
        ps.health, ps.magic = 80, 7
        engine._save_turn_start_snapshot(0)
        # 第2回合内被打到 50
        ps.health = 50
        card = CardInstance('Bone')
        engine._restore_turn_start_payload(0, card, {}, None, None, None)
        # 回到上个（第1个）自己回合开始：H100/M5（E 不回满，扣 extra 0）
        self.assertEqual(100, ps.health)
        self.assertEqual(5, ps.magic)

    def test_other_target_still_uses_latest_own_turn_start(self):
        engine = self.build()
        p0, p1 = engine.players[0], engine.players[1]
        p1.health, p1.magic = 90, 2
        engine._save_turn_start_snapshot(1)  # p1 上个回合开始
        p1.health = 40
        engine.current_player = 0
        card = CardInstance('Bone')
        engine._restore_turn_start_payload(0, card, {'target': 1}, None, None, None)
        # 非当前回合玩家：仍回到其最近一次自己回合开始
        self.assertEqual(90, p1.health)

    def test_first_own_turn_falls_back_to_current_snapshot(self):
        engine = self.build()
        ps = engine.players[0]
        engine.current_player = 0
        engine._save_turn_start_snapshot(0)  # 首个回合，无上一份
        ps.health = 30
        card = CardInstance('Bone')
        engine._restore_turn_start_payload(0, card, {}, None, None, None)
        self.assertEqual(100, ps.health)


if __name__ == '__main__':
    unittest.main()
