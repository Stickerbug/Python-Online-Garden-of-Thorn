# -*- coding: utf-8 -*-
"""2v2 血盾（设计 2026-09-29；调整 2026-10-12 统一减少）：按玩家各自持有，
每个自己回合开始统一减一档——3/4 → 2/4 → 1/4 → 0（档值动态取当前最大生命）。
血量不会被伤害打到自己的护盾值以下。
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
        """100 最大生命：第1回合 75 → 第2回合 50 → 第3回合 25 → 第4回合 0。"""
        engine = self.build_engine()
        ps = engine.players[1]
        ps.blood_shield = 100 * 3 // 4
        engine._apply_turn_start_effects_2v2(1)
        self.assertEqual(75, ps.blood_shield)
        engine._apply_turn_start_effects_2v2(1)
        self.assertEqual(50, ps.blood_shield)
        engine._apply_turn_start_effects_2v2(1)
        self.assertEqual(25, ps.blood_shield)
        engine._apply_turn_start_effects_2v2(1)
        self.assertEqual(0, ps.blood_shield)
        engine._apply_turn_start_effects_2v2(1)
        self.assertEqual(0, ps.blood_shield)

    def test_decay_is_per_player(self):
        """玩家2衰减不影响玩家3的护盾。"""
        engine = self.build_engine()
        p2, p3 = engine.players[2], engine.players[3]
        p2.blood_shield = 75
        p3.blood_shield = 75
        engine._apply_turn_start_effects_2v2(2)
        self.assertEqual(75, p2.blood_shield)  # 第1个自己回合仍是 3/4
        self.assertEqual(75, p3.blood_shield)
        engine._apply_turn_start_effects_2v2(2)
        self.assertEqual(50, p2.blood_shield)
        self.assertEqual(75, p3.blood_shield)

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
        """最大生命 95：3/4=71 → 2/4=47 → 1/4=23（向下取整）。"""
        engine = self.build_engine()
        ps = engine.players[0]
        ps.max_health = 95
        ps.health = 95
        ps.blood_shield = 95 * 3 // 4
        self.assertEqual(71, ps.blood_shield)
        engine._apply_turn_start_effects_2v2(0)
        self.assertEqual(71, ps.blood_shield)  # 第1个自己回合仍是 3/4
        engine._apply_turn_start_effects_2v2(0)
        self.assertEqual(95 * 2 // 4, ps.blood_shield)
        self.assertEqual(47, ps.blood_shield)
        engine._apply_turn_start_effects_2v2(0)
        self.assertEqual(23, ps.blood_shield)


if __name__ == '__main__':
    unittest.main()
