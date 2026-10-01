# -*- coding: utf-8 -*-
"""GS-250/252：风（desert_cards_addition:wind）第一回合不生效。

「目标下回合的回合开始抽牌结算后」的延时效果此前挂在 round_num > 1 的
抽牌分支里——首回合没有抽牌，整个 after_turn_start_draw 阶段被跳过，
风的弃牌要晚一整轮才结算。修复后：计时效果在首回合照常触发；装备类
事件（布加迪：「正常抽牌后」）维持首回合不触发。
"""

import unittest

import app  # noqa: F401  装载模组
from game_engine import CardInstance, GameEngine


def target_choice(player_id):
    return {'target_player': player_id, 'target_player_id': player_id, 'target_id': player_id}


class WindFirstTurnTests(unittest.TestCase):
    def build_engine(self):
        engine = GameEngine()
        engine.phase = 'action'
        engine.current_player = 0
        engine.round_num = 1
        for player in engine.players:
            player.health = 100
            player.max_health = 100
            player.elixir = 20
            player.magic = 20
            player.hand = []
            player.deck = []
            player.discard = []
        return engine

    def test_wind_fires_on_target_round_one_turn_start(self):
        """首回合：玩家0对玩家1出风（2026-10-01 平衡后 2E），玩家1的首回合
        开始即应弃掉手牌中 E 费 ≤3（花费+1）的牌——仙人掌（3E）也被吹走。"""
        engine = self.build_engine()
        light = CardInstance('Light')      # 0E → 应被吹走
        basic = CardInstance('Basic')      # 1E → 应被吹走
        cactus = CardInstance('Cactus')    # 3E > 2 → 保留
        engine.players[1].hand = [light, basic, cactus]
        wind = CardInstance('Wind')        # 2E，阈值 = 2+1 = 3
        engine.players[0].hand = [wind]
        engine.play_card(0, wind.instance_id, target_choice(1))
        if getattr(engine, 'pending_response', None):
            engine.handle_response(1, None)
        engine.end_turn(0)
        remaining = [c.card_def.name_cn for c in engine.players[1].hand]
        self.assertEqual([], remaining)
        discarded = sorted(c.card_def.name_cn for c in engine.players[1].discard)
        self.assertEqual(['仙人掌', '基本', '轻'], discarded)

    def test_bugatti_equipment_still_waits_for_normal_draw(self):
        """布加迪文案是「正常抽牌后」：首回合（无正常抽牌）装备事件不触发。"""
        engine = self.build_engine()
        bugatti = CardInstance('Bugatti')
        engine.players[0].hand = [bugatti]
        engine.play_card(0, bugatti.instance_id, target_choice(1))
        if getattr(engine, 'pending_response', None):
            engine.handle_response(1, None)
        hand_before = len(engine.players[1].hand)
        engine.end_turn(0)  # 玩家1首回合开始：不应触发布加迪补抽
        self.assertEqual(hand_before, len(engine.players[1].hand))


if __name__ == '__main__':
    unittest.main()
