# -*- coding: utf-8 -*-
"""GS-291：机械导弹（MechaMissile）伤害预测泄露对手反制牌数量。

卡面伤害 = 5 + 目标手牌反制牌数×5，出牌预测是服务端真实引擎模拟，
会拿到确切数字——悬停即可免费反推对手有几张反制牌。修复后：效果
里含「他人手牌的带过滤 zone_count」的卡不提供出牌预测（hidden-info），
普通卡的预测不受影响。
"""

import unittest

import app  # noqa: F401  装载模组
from game_engine import CardInstance, GameEngine


def target_choice(player_id):
    return {'target_player': player_id, 'target_player_id': player_id, 'target_id': player_id}


class HiddenInfoPredictionTests(unittest.TestCase):
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

    def test_mecha_missile_prediction_suppressed(self):
        engine = self.build_engine()
        missile = CardInstance('MechaMissile')
        engine.players[0].hand = [missile]
        engine.players[1].hand = [CardInstance('Cucumber'), CardInstance('Cucumber')]
        result = engine.simulate_card_play_prediction(0, missile.instance_id, target_choice(1))
        self.assertFalse(result.get('ok'))
        self.assertEqual('hidden-info', result.get('error'))

    def test_normal_card_prediction_still_available(self):
        engine = self.build_engine()
        needle = CardInstance('Needle')
        engine.players[0].hand = [needle]
        result = engine.simulate_card_play_prediction(0, needle.instance_id, target_choice(1))
        self.assertTrue(result.get('ok'))
        self.assertEqual(4, result['players']['1']['damage_total'])

    def test_mecha_missile_play_damage_unchanged(self):
        """预测被拦，但实际出牌伤害仍按对手反制牌数量结算（卡面机制不动）。"""
        engine = self.build_engine()
        missile = CardInstance('MechaMissile')
        engine.players[0].hand = [missile]
        engine.players[1].hand = [CardInstance('Cucumber'), CardInstance('Jelly')]
        engine.play_card(0, missile.instance_id, target_choice(1))
        if getattr(engine, 'pending_response', None):
            engine.handle_response(1, None)
        self.assertEqual(15, 100 - engine.players[1].health)


if __name__ == '__main__':
    unittest.main()
