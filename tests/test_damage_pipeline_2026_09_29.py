# -*- coding: utf-8 -*-
"""伤害管线修复（设计 2026-09-29）：

1. deal_damage 步骤把实伤写进 event_value——毒刺/针等"每造成X点伤害"
   类卡此前恒得 0。
2. 威力不再按裂变份数切分，统一加在整次出牌的第一段（跨裂变迭代/多目标
   只加一次，_power_applied_this_play 标记）。
用户示例：威力6裂变3沙子 vs 护甲2邪眼 → 第一段 1+6=7 → 护甲2 → 5 →
邪眼(1~9变1) → 1；其余段 1-2=0；总伤 1。
"""

import unittest

import app  # noqa: F401  装载模组
from game_engine import CardInstance, GameEngine


def target_choice(player_id):
    return {'target_player': player_id, 'target_player_id': player_id, 'target_id': player_id}


class DamagePipelineTests(unittest.TestCase):
    def build_engine(self):
        engine = GameEngine()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.max_health = 100
            player.elixir = 20
            player.magic = 20
            player.hand = []
            player.deck = []
            player.discard = []
        return engine

    def play(self, engine, card):
        engine.players[0].hand = [card]
        result = engine.play_card(0, card.instance_id, target_choice(1))
        if getattr(engine, 'pending_response', None):
            engine.handle_response(1, None)
        return result

    def test_poison_stinger_applies_poison_per_damage(self):
        """毒刺 14D → floor(14/3)=4 层 P（event_value 修复前为 0）。"""
        engine = self.build_engine()
        self.play(engine, CardInstance('PoisonStinger'))
        self.assertEqual(14, 100 - engine.players[1].health)
        self.assertEqual(4, engine.players[1].poison)

    def test_power_fission_armor_nazar_pipeline(self):
        """威力6裂变3沙子 vs 护甲2邪眼3 → (1+0×11)，总伤 1。"""
        engine = self.build_engine()
        engine._set_nazar_status_value(1, 3)
        engine.players[1].armor = 2
        sand = CardInstance('Sand')
        sand.power_value = 6
        sand.fission_level = 3
        self.play(engine, sand)
        self.assertEqual(1, 100 - engine.players[1].health)
        # 1~9 段被邪眼变换不消耗层数
        self.assertEqual(3, engine._nazar_status_value(1))

    def test_power_applies_once_across_fission(self):
        """无减免时：威力6裂变3沙子 = (7+1×11)，总伤 18（威力只加一次）。
        裂变把基础 3×4 段切成 3 次迭代×4 段×1D，威力全加在第一次迭代首段。"""
        engine = self.build_engine()
        sand = CardInstance('Sand')
        sand.power_value = 6
        sand.fission_level = 3
        self.play(engine, sand)
        self.assertEqual(18, 100 - engine.players[1].health)

    def test_power_applies_on_each_separate_play(self):
        """两张牌各自享受威力第一段：每张 (3+2)+3×3=14，共 28。"""
        engine = self.build_engine()
        sand1 = CardInstance('Sand')
        sand1.power_value = 2
        sand1.fission_level = 1
        sand2 = CardInstance('Sand')
        sand2.power_value = 2
        sand2.fission_level = 1
        engine.players[0].hand = [sand1, sand2]
        engine.play_card(0, sand1.instance_id, target_choice(1))
        if getattr(engine, 'pending_response', None):
            engine.handle_response(1, None)
        engine.play_card(0, sand2.instance_id, target_choice(1))
        if getattr(engine, 'pending_response', None):
            engine.handle_response(1, None)
        self.assertEqual(28, 100 - engine.players[1].health)


if __name__ == '__main__':
    unittest.main()
