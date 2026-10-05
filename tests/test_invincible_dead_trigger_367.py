# -*- coding: utf-8 -*-
"""反馈 #367：触发者阵亡后「无敌直到触发者下回合开始」永不到期→永久无敌。

修复：计时对象（invincible_until_player）已阵亡时，任意回合开始结算都视为
计时完成，无敌立即清除。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_engine import GameEngine  # noqa: E402


def _engine():
    engine = GameEngine()
    engine.allowed_card_ids = None
    engine.draft_picks[0] = ['Stinger', 'Bubble', 'Light', 'Fang', 'Rose', 'Bone'] * 2
    engine.draft_picks[1] = ['Stinger', 'Bubble', 'Light', 'Fang', 'Rose', 'Bone'] * 2
    engine.start_game(skip_pregame_validation=True, mulligan=False)
    return engine


class InvincibleDeadTriggerTest(unittest.TestCase):
    def test_trigger_dead_expires_on_next_turn_start(self):
        engine = _engine()
        # 玩家0（ygg持有者）被玩家1（触发者/攻击者）触发无敌，到玩家1下回合开始止
        engine._set_invincible_until_player_next_turn_start(0, 1)
        self.assertTrue(engine.players[0].invincible)
        # 触发者阵亡（2v2 场景：报告者死了，对局继续）
        engine.players[1].health = 0
        # 推进回合（绕过授予回合的同回合保护）
        engine.round_num += 1
        engine._apply_turn_start_effects(0)
        self.assertFalse(engine.players[0].invincible, '触发者阵亡后无敌必须清除')

    def test_trigger_alive_keeps_invincible_until_his_turn(self):
        engine = _engine()
        engine._set_invincible_until_player_next_turn_start(0, 1)
        engine.round_num += 1
        # 触发者（玩家1）还活着：轮到玩家0开始回合时不应清除
        engine._apply_turn_start_effects(0)
        self.assertTrue(engine.players[0].invincible, '触发者存活时无敌保持')
        # 轮到玩家1（触发者）回合开始时正常到期
        engine._apply_turn_start_effects(1)
        self.assertFalse(engine.players[0].invincible)

    def test_expiry_log_names_holder(self):
        engine = _engine()
        engine._set_invincible_until_player_next_turn_start(0, 1)
        engine.players[1].health = 0
        engine.round_num += 1
        engine._apply_turn_start_effects(1)
        self.assertFalse(engine.players[0].invincible)
        self.assertTrue(any('无敌' in line and '结束' in line for line in engine.log))


if __name__ == '__main__':
    unittest.main()
