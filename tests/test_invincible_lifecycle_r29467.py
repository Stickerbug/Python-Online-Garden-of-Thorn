# -*- coding: utf-8 -*-
"""R-29467 回归：世界树型无敌的"回合开始到期"标志残留，导致之后绷带等
"到回合结束"型无敌在玩家自己回合开始时被误清除。

场景回放（1v1，玩家0=持有者，玩家1=对手/触发者）：
  1) 玩家1回合内，玩家0受致命伤 → 世界树触发，无敌到玩家1的下个回合开始
  2) 玩家1的下个回合开始 → 该无敌正常到期清除
  3) 同回合内玩家0用绷带反制，绷带触发 → 无敌到玩家0自己回合结束
  4) 玩家0回合开始 → 绷带无敌【不应】在此到期（旧 bug：残留标志误清除）
  5) 玩家0回合结束 → 绷带无敌正常到期
"""
import unittest

from game_engine import GameEngine


class InvincibleLifecycleR29467Tests(unittest.TestCase):
    def _grant_yggdrasil_style(self, engine):
        # 玩家1的回合内（turn marker=1），玩家0的世界树触发
        engine.current_player = 1
        engine.round_num = 7
        engine.turn_index = 71
        engine._set_invincible_until_player_next_turn_start(0, 1)
        self.assertTrue(engine.players[0].invincible)
        self.assertTrue(engine.players[0].invincible_expire_on_turn_start)
        self.assertEqual(engine.players[0].invincible_until_player, 1)

    def test_bandage_invincible_survives_own_turn_start_after_ygg_expiry(self):
        engine = GameEngine()
        self._grant_yggdrasil_style(engine)

        # 玩家1的下个回合开始（turn marker 变化）→ 世界树无敌到期
        engine.turn_index = 81
        expiring = engine._expiring_invincible_player_ids_on_turn_start(1)
        self.assertIn(0, expiring)
        for pid in expiring:
            engine._clear_invincible_state(pid)
        self.assertFalse(engine.players[0].invincible)

        # 同一回合内绷带触发：无敌到玩家0自己回合结束
        engine._set_invincible_until_next_own_turn_end(0)
        self.assertTrue(engine.players[0].invincible)

        # 玩家0的回合开始：绷带无敌不应被清除（R-29467 旧 bug 在这里清除）
        engine.turn_index = 82
        self.assertEqual(
            engine._expiring_invincible_player_ids_on_turn_start(0),
            [],
            '绷带型无敌不应在回合开始到期（标志残留 bug）',
        )
        self.assertTrue(engine.players[0].invincible)

        # 玩家0的回合结束：正常到期
        self.assertTrue(engine._should_expire_invincible_on_turn_end(0))
        engine._clear_invincible_state(0)
        self.assertFalse(engine.players[0].invincible)

    def test_clear_invincible_resets_expire_flag(self):
        engine = GameEngine()
        self._grant_yggdrasil_style(engine)
        self.assertTrue(engine.players[0].invincible_expire_on_turn_start)
        engine._clear_invincible_state(0)
        self.assertFalse(
            engine.players[0].invincible_expire_on_turn_start,
            '清除无敌时必须一并复位回合开始到期标志',
        )

    def test_turn_end_grant_overrides_stale_expire_flag(self):
        """即使标志因旧存档等原因残留，授予"到回合结束"型无敌时也应覆盖。"""
        engine = GameEngine()
        self._grant_yggdrasil_style(engine)
        # 模拟残留：直接再授予回合结束型
        engine._set_invincible_until_next_own_turn_end(0)
        self.assertFalse(engine.players[0].invincible_expire_on_turn_start)
        engine.turn_index = 99
        self.assertEqual(engine._expiring_invincible_player_ids_on_turn_start(0), [])

    def test_yggdrasil_style_still_expires_on_trigger_turn_start(self):
        """修复不改变世界树型无敌本身的到期时点。"""
        engine = GameEngine()
        self._grant_yggdrasil_style(engine)
        # 授予当回合不到期
        self.assertEqual(engine._expiring_invincible_player_ids_on_turn_start(1), [])
        # 触发者的下个回合开始才到期
        engine.turn_index = 90
        self.assertEqual(engine._expiring_invincible_player_ids_on_turn_start(1), [0])

    def test_expire_flag_serialization_roundtrip(self):
        engine = GameEngine()
        self._grant_yggdrasil_style(engine)
        d = engine.players[0].to_dict()
        self.assertTrue(d.get('invincible_expire_on_turn_start'))
        from game_engine import PlayerState
        ps2 = PlayerState.__new__(PlayerState)
        # from_dict 只覆盖字段；给一个最小可用的实例
        ps2.__dict__.update(engine.players[0].__dict__)
        ps2.from_dict(d)
        self.assertTrue(ps2.invincible_expire_on_turn_start)


if __name__ == '__main__':
    unittest.main()
