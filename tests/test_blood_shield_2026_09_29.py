# -*- coding: utf-8 -*-
"""2v2 血盾（设计 2026-09-29）：按玩家各自持有、各自回合开始衰减。

开局 floor(2/3×最大生命) → 自己回合开始 → floor(1/3×最大生命) →
再下个自己回合 → 0；血量不会被伤害打到自己的护盾值以下。
"""

import unittest

import app  # noqa: F401  装载模组
from game_engine import CardInstance
from game_engine_2v2 import GameEngine2v2


def target_choice(player_id):
    return {'target_player': player_id, 'target_player_id': player_id, 'target_id': player_id}


class BloodShieldTests(unittest.TestCase):
    def build_engine(self):
        engine = GameEngine2v2()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.max_health = 100
            player.elixir = 10
            player.magic = 10
            player.hand = []
            player.deck = []
            player.discard = []
            player.blood_shield = 0
        return engine

    def test_decay_schedule_per_own_turn(self):
        """100 最大生命：66 → 自己回合开始 33 → 再下个自己回合 0 → 不再变动。"""
        engine = self.build_engine()
        ps = engine.players[1]
        ps.blood_shield = 100 * 2 // 3
        engine._apply_turn_start_effects_2v2(1)
        self.assertEqual(100 // 3, ps.blood_shield)
        engine._apply_turn_start_effects_2v2(1)
        self.assertEqual(0, ps.blood_shield)
        engine._apply_turn_start_effects_2v2(1)
        self.assertEqual(0, ps.blood_shield)

    def test_decay_is_per_player(self):
        """玩家2衰减不影响玩家3的护盾。"""
        engine = self.build_engine()
        p2, p3 = engine.players[2], engine.players[3]
        p2.blood_shield = 66
        p3.blood_shield = 66
        engine._apply_turn_start_effects_2v2(2)
        self.assertEqual(100 // 3, p2.blood_shield)
        self.assertEqual(66, p3.blood_shield)

    def test_health_floor_uses_own_shield(self):
        """伤害结算：血量不会低于自己的护盾值。"""
        engine = self.build_engine()
        ps = engine.players[2]
        ps.blood_shield = 33
        ps.health = 38
        thorn = CardInstance('Bone')
        engine.players[0].hand = [thorn]
        engine.play_card(0, thorn.instance_id, 2, target_choice(2))
        if getattr(engine, 'pending_response', None):
            engine.resolve_forced_response()
        # Bone 12D：38 → 26 低于护盾 33 → 拦在 33
        self.assertEqual(33, ps.health)

    def test_fractional_max_health_floors(self):
        """最大生命 95：floor(2/3)=63 → floor(1/3)=31。"""
        engine = self.build_engine()
        ps = engine.players[0]
        ps.max_health = 95
        ps.health = 95
        ps.blood_shield = 95 * 2 // 3
        self.assertEqual(63, ps.blood_shield)
        engine._apply_turn_start_effects_2v2(0)
        self.assertEqual(95 // 3, ps.blood_shield)
        self.assertEqual(31, ps.blood_shield)


if __name__ == '__main__':
    unittest.main()
