# -*- coding: utf-8 -*-
"""杜鹃花回合结束丢弃：日志要带所有者（{target} 展开）和 CARD marker（客户端 chip）。"""

import unittest

import app  # noqa: F401  装载模组（Azalea 事件来自 Jurassic 包）
import game_engine as ge


class AzaleaTurnEndLogTests(unittest.TestCase):
    def setUp(self):
        self.engine = ge.GameEngine()
        self.engine.players = [ge.PlayerState(i) for i in range(2)]
        self.engine.round_num = 2
        self.logs = []
        self.engine.log_msg = lambda message: self.logs.append(str(message))
        self.azalea = ge.CardInstance('Azalea')
        self.engine.players[0].hand.append(self.azalea)

    def test_turn_end_log_names_the_owner(self):
        self.engine._run_hand_owner_turn_end_events(0)
        self.assertTrue(self.logs)
        self.assertIn('玩家1的杜鹃花', self.logs[-1])
        self.assertNotIn('{target}', self.logs[-1])
        # 牌真的进了弃牌堆
        self.assertNotIn(self.azalea, self.engine.players[0].hand)
        self.assertIn(self.azalea, self.engine.players[0].discard)

    def test_turn_end_log_carries_card_marker_for_chip(self):
        self.engine._run_hand_owner_turn_end_events(0)
        self.assertIn('\u2063CARD:', self.logs[-1])
        clean = self.engine._strip_card_log_markers(self.logs[-1])
        self.assertIn('杜鹃花', clean)


if __name__ == '__main__':
    unittest.main()
