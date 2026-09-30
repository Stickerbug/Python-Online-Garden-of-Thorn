# -*- coding: utf-8 -*-
"""威力层数的伤害预测与实际对拍（玩家反馈预测不符，2026-09-30 核查）。

9.27 口径：威力全部加在第一段；9.29 修订：裂变后续段不带威力。
预测方案是 deepcopy 引擎真实打出——按构造应当一致；本测试对多段/裂变/
单段三种形态做对拍，若将来引擎改动破坏口径，这里会先红。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import app  # noqa: F401,E402  装载模组
from game_engine import CardInstance, GameEngine  # noqa: E402


def target_choice(player_id):
    return {'target_player': player_id, 'target_player_id': player_id, 'target_id': player_id}


class PowerPredictionParityTests(unittest.TestCase):
    def build_engine(self):
        engine = GameEngine()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 200
            player.elixir = 20
            player.magic = 20
            player.hand = []
        return engine

    def _drive_real_pendings(self, engine, player_id=0):
        """真实打出后驱动暂停点：选择→取第一个合法项；响应→无人反制。"""
        for _ in range(12):
            pending = getattr(engine, 'pending_choice', None)
            if pending:
                options = pending.get('options')
                if isinstance(options, list) and options:
                    engine.resolve_choice(player_id, {'option': options[0]})
                else:
                    break
            elif getattr(engine, 'pending_response', None):
                rid = engine.pending_response.get('request_id') if isinstance(engine.pending_response, dict) else None
                engine.resolve_response(rid, None) if rid else None
                if getattr(engine, 'pending_response', None):
                    break
            elif getattr(engine, 'pending_v2_ui', None):
                break
            else:
                break

    def _parity(self, card_id, hits_note=''):
        engine = self.build_engine()
        card = CardInstance(card_id)
        card.power_value = 3
        engine.players[0].hand = [card]
        pred = engine.simulate_card_play_prediction(0, card.instance_id, target_choice(1))
        self.assertTrue(pred['ok'], (card_id, pred))
        log_start = len(engine.log)
        engine.play_card(0, card.instance_id, target_choice(1))
        engine._prediction_drive_pending(0)
        self._drive_real_pendings(engine)
        real_parts = []
        for line in engine.log[log_start:]:
            parsed = engine._parse_damage_taken_log(line)
            if parsed and parsed.get('target') == engine.pn(1):
                real_parts.extend(int(v) for v in parsed.get('parts', []) if int(v) > 0)
        self.assertEqual(
            pred['players'].get('1', {}).get('damage_parts', []),
            real_parts,
            (card_id, hits_note, pred['players'].get('1', {}), real_parts),
        )
        return real_parts

    def test_single_hit_with_power(self):
        parts = self._parity('Bone')
        self.assertTrue(parts, 'Bone 应有伤害分段')

    def test_multi_hit_with_power(self):
        # 沙子：多段攻击，威力只加第一段
        parts = self._parity('Sand')
        self.assertTrue(len(parts) >= 2, ('Sand 应多段', parts))

    def test_fission_with_power(self):
        # 裂变迭代：Bone 挂 2 层裂变 + 3 威力，打出后复制迭代，后续段不带威力
        engine = self.build_engine()
        card = CardInstance('Bone')
        card.power_value = 3
        card.fission_level = 2
        engine.players[0].hand = [card]
        pred = engine.simulate_card_play_prediction(0, card.instance_id, target_choice(1))
        self.assertTrue(pred['ok'], pred)
        log_start = len(engine.log)
        engine.play_card(0, card.instance_id, target_choice(1))
        engine._prediction_drive_pending(0)
        self._drive_real_pendings(engine)
        real_parts = []
        for line in engine.log[log_start:]:
            parsed = engine._parse_damage_taken_log(line)
            if parsed and parsed.get('target') == engine.pn(1):
                real_parts.extend(int(v) for v in parsed.get('parts', []) if int(v) > 0)
        self.assertEqual(pred['players'].get('1', {}).get('damage_parts', []), real_parts,
                         (pred['players'].get('1', {}), real_parts))
        self.assertTrue(real_parts, '裂变迭代应造成伤害')
        # 12 + 3威力 = 15，裂变两段均分（9+6）——总和必须等于基础+威力
        self.assertEqual(sum(real_parts), 15, ('威力应计入总伤（12+3）', real_parts))


if __name__ == '__main__':
    unittest.main()
