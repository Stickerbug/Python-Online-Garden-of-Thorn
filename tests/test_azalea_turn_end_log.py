# -*- coding: utf-8 -*-
"""杜鹃花（9.27 修订）：回合结束自动弃置已删除——手牌中保留，不再产生弃置日志。

保留 {target} 占位符展开与 CARD marker 的通用机制测试（用临时挂载的事件验证）。
"""

import unittest

import app  # noqa: F401  装载模组（Azalea 来自 Jurassic 包）
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

    def test_azalea_no_longer_discards_at_turn_end(self):
        """9.27：删除「回合结束未打出自动弃置」——杜鹃花留在手里。"""
        self.engine._run_hand_owner_turn_end_events(0)
        self.assertEqual(self.logs, [], '杜鹃花不应再产生回合结束弃置日志')
        self.assertIn(self.azalea, self.engine.players[0].hand)
        self.assertNotIn(self.azalea, self.engine.players[0].discard)

    def test_owner_and_marker_mechanism_still_works(self):
        """通用机制回归：{target} 展开 + CARD marker 注入仍正常（临时挂旧版事件验证）。"""
        from game_engine import CARD_DEFS
        card_def = CARD_DEFS.get('Azalea')
        assert card_def is not None
        card_def.v2_events['on_hand_owner_turn_end'] = {
            'steps': [{
                'op': 'move_card',
                'card': {'ref': 'current_card'},
                'zone': 'discard',
                'count_as_active_discard': True,
                'log': '{target}的杜鹃花在回合结束未打出，进入弃牌堆',
            }],
        }
        try:
            self.engine._run_hand_owner_turn_end_events(0)
            self.assertTrue(self.logs)
            self.assertIn('玩家1的杜鹃花', self.logs[-1])
            self.assertNotIn('{target}', self.logs[-1])
            self.assertIn('\u2063CARD:', self.logs[-1])
        finally:
            card_def.v2_events.pop('on_hand_owner_turn_end', None)


if __name__ == '__main__':
    unittest.main()
