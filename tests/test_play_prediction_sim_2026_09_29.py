# -*- coding: utf-8 -*-
"""出牌预测服务端模拟（simulate_card_play_prediction）冒烟与口径测试。

2026-09-29 通用方案：deepcopy 引擎真实打出，日志+状态 diff 取结构化结果。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import app  # noqa: F401,E402  装载模组
from game_engine import CardInstance, GameEngine  # noqa: E402


def target_choice(player_id):
    return {'target_player': player_id, 'target_player_id': player_id, 'target_id': player_id}


class PlayPredictionSimTests(unittest.TestCase):
    def build_engine(self):
        engine = GameEngine()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.elixir = 20
            player.magic = 20
            player.hand = []
        return engine

    def test_basic_attack_prediction(self):
        engine = self.build_engine()
        bone = CardInstance('Bone')
        engine.players[0].hand = [bone]
        before_hp = engine.players[1].health
        pred = engine.simulate_card_play_prediction(0, bone.instance_id, target_choice(1))
        self.assertTrue(pred['ok'], pred)
        self.assertTrue(pred['played'], pred)
        self.assertEqual(pred['def_id'], bone.def_id)
        p1 = pred['players'].get('1', {})
        self.assertTrue(
            p1.get('damage_total', 0) > 0 or p1.get('poison', 0) > 0 or p1.get('fire', 0) > 0,
            pred,
        )
        # 预测不得改动真实引擎
        self.assertEqual(engine.players[1].health, before_hp)
        self.assertIn(bone.instance_id, [c.instance_id for c in engine.players[0].hand])
        self.assertIsNone(engine.pending_response)
        self.assertIsNone(engine.pending_choice)

    def test_prediction_repeat_is_stable(self):
        engine = self.build_engine()
        bone = CardInstance('Bone')
        engine.players[0].hand = [bone]
        a = engine.simulate_card_play_prediction(0, bone.instance_id, target_choice(1))
        b = engine.simulate_card_play_prediction(0, bone.instance_id, target_choice(1))
        self.assertEqual(a['players'], b['players'])
        self.assertEqual(a['players']['1']['damage_parts'], b['players']['1']['damage_parts'])

    def test_real_play_matches_prediction(self):
        """同状态下：先预测，再真实打出——伤害分段一致（跑同一套引擎）。"""
        engine = self.build_engine()
        bone = CardInstance('Bone')
        engine.players[0].hand = [bone]
        pred = engine.simulate_card_play_prediction(0, bone.instance_id, target_choice(1))
        log_start = len(engine.log)
        engine.play_card(0, bone.instance_id, target_choice(1))
        engine._prediction_drive_pending(0)
        real_parts = []
        for line in engine.log[log_start:]:
            parsed = engine._parse_damage_taken_log(line)
            if parsed and parsed.get('target') == engine.pn(1):
                real_parts.extend(int(v) for v in parsed.get('parts', []) if int(v) > 0)
        self.assertEqual(pred['players'].get('1', {}).get('damage_parts', []), real_parts)

    def test_self_effect_resource_prediction(self):
        """资源类：预测与真实出牌的资源变化一致（跑同一套引擎）。"""
        for card_id, target in (('Coffee', 0), ('ManaOrb', 1)):
            engine = self.build_engine()
            card = CardInstance(card_id)
            engine.players[0].hand = [card]
            pred = engine.simulate_card_play_prediction(0, card.instance_id, target_choice(target))
            self.assertTrue(pred['ok'], pred)
            before = (engine.players[0].elixir, engine.players[0].magic,
                      engine.players[1].elixir, engine.players[1].magic)
            engine.play_card(0, card.instance_id, target_choice(target))
            engine._prediction_drive_pending(0)
            after = (engine.players[0].elixir, engine.players[0].magic,
                     engine.players[1].elixir, engine.players[1].magic)
            real = {0: {'elixir': after[0] - before[0], 'magic': after[1] - before[1]},
                    1: {'elixir': after[2] - before[2], 'magic': after[3] - before[3]}}
            # 预测对 p0 补回了卡费（Coffee 0费/ManaOrb 1E），对拍时给真实值也补回
            pred0 = pred['players'].get('0', {})
            self.assertEqual(pred0.get('elixir', 0), real[0]['elixir'] + (1 if card_id == 'ManaOrb' else 0), card_id)
            self.assertEqual(pred0.get('magic', 0), real[0]['magic'], card_id)
            pred1 = pred['players'].get('1', {})
            self.assertEqual(pred1.get('elixir', 0), real[1]['elixir'], card_id)
            self.assertEqual(pred1.get('magic', 0), real[1]['magic'], card_id)

    def test_card_not_in_hand(self):
        engine = self.build_engine()
        pred = engine.simulate_card_play_prediction(0, 999999, None)
        self.assertTrue((not pred['ok']) or pred.get('error') == 'card-not-in-hand', pred)

    def test_sim_with_response_window_pacing(self):
        """response_pacing 房间：预测里 2s 强制窗被驱动到结算，不悬挂。"""
        engine = self.build_engine()
        engine.response_pacing = True
        bone = CardInstance('Bone')
        engine.players[0].hand = [bone]
        pred = engine.simulate_card_play_prediction(0, bone.instance_id, target_choice(1))
        self.assertTrue(pred['ok'], pred)
        self.assertTrue(pred['played'], pred)
        p1 = pred['players'].get('1', {})
        self.assertGreater(p1.get('damage_total', 0), 0, pred)


if __name__ == '__main__':
    unittest.main(verbosity=2)
