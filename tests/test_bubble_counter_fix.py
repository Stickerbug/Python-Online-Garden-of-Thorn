# -*- coding: utf-8 -*-
"""泡泡（Bubble）反制语义（2026-10-12 修正后口径）：

设计：反制授予的闪避在被反制牌结算期间生效——泡泡挡下它所反制的那张
攻击（闪避层被消耗），精准牌只减半；结算后 clamp_responder_props 夹回。
真正修复的是：1v1 引擎 halve_precision 分支的非精准路径此前写在 return
之后（死代码）——被反制的攻击牌效果不结算、也从不进弃牌堆，凭空消失。
"""

import math
import unittest

import app  # noqa: F401  装载模组
from cards import CARD_DEFS
from game_engine import CardInstance, GameEngine


def target_choice(player_id):
    return {'target_player': player_id, 'target_player_id': player_id, 'target_id': player_id}


def _find_precision_attack():
    for cid, d in CARD_DEFS.items():
        if d.card_type == 'thorn' and 'precision' in (d.flags or set()) and (d.damage or 0) >= 6:
            return cid
    raise AssertionError('卡池中找不到带精准标记的攻击牌')


class BubbleCounterTests(unittest.TestCase):
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
            player.exile = []
        return engine

    def countered(self, attack_id):
        engine = self.build_engine()
        attack = CardInstance(attack_id)
        bubble = CardInstance('Bubble')
        engine.players[0].hand = [attack]
        engine.players[1].hand = [bubble]
        engine.play_card(0, attack.instance_id, target_choice(1))
        result = engine.handle_response(1, bubble.instance_id)
        return engine, result, attack, bubble

    def test_non_precision_attack_is_dodged_and_card_discarded(self):
        """非精准攻击被泡泡反制：闪避挡下（0伤），攻击牌进弃牌堆（修复前凭空消失）。"""
        engine, result, attack, bubble = self.countered('Basic')
        self.assertEqual(0, 100 - engine.players[1].health, '被反制的非精准攻击应被闪避挡下')
        owner, zone, _ = engine._find_card_location(attack)
        self.assertEqual((0, 'discard'), (owner, zone), '被反制的攻击牌应进攻击方弃牌堆')
        self.assertEqual(0, engine.players[1].dodge, '闪避层被本次挡下消耗')

    def test_precision_attack_is_halved(self):
        """精准攻击被泡泡反制：伤害减半，闪避层消耗。"""
        attack_id = _find_precision_attack()
        engine, _, attack, bubble = self.countered(attack_id)
        dealt = 100 - engine.players[1].health
        self.assertEqual(math.ceil(21 / 2), dealt, f'精准（{attack_id} 21D）被泡泡反制应减半为11')
        owner, zone, _ = engine._find_card_location(attack)
        self.assertEqual((0, 'discard'), (owner, zone))
        self.assertEqual(0, engine.players[1].dodge)


class BubbleCounter2v2Tests(BubbleCounterTests):
    """2v2 引擎同语义（换引擎构造与目标席位）。"""

    def build_engine(self):
        from game_engine_2v2 import GameEngine2v2
        engine = GameEngine2v2()
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
            player.exile = []
            player.equipment = []
            player.dodge = 0
            player.armor = 0
            player.custom_statuses = {}
            player.custom_vars = {}
        return engine

    def countered(self, attack_id):
        engine = self.build_engine()
        attack = CardInstance(attack_id)
        bubble = CardInstance('Bubble')
        engine.players[0].hand = [attack]
        # 2v2：座位 2 是座位 0 的对手；play_card 第 3 参是目标席位
        engine.players[2].hand = [bubble]
        engine.play_card(0, attack.instance_id, 2, target_choice(2))
        result = engine.handle_response(2, bubble.instance_id)
        return engine, result, attack, bubble

    def test_non_precision_attack_is_dodged_and_card_discarded(self):
        engine, result, attack, bubble = self.countered('Basic')
        self.assertEqual(0, 100 - engine.players[2].health, '2v2：被反制的非精准攻击应被闪避挡下')
        owner, zone, _ = engine._find_card_location(attack)
        self.assertEqual((0, 'discard'), (owner, zone))
        self.assertEqual(0, engine.players[2].dodge)

    def test_precision_attack_is_halved(self):
        attack_id = _find_precision_attack()
        engine, _, attack, bubble = self.countered(attack_id)
        dealt = 100 - engine.players[2].health
        self.assertEqual(math.ceil(21 / 2), dealt, '2v2：精准被泡泡反制应减半')
        self.assertEqual(0, engine.players[2].dodge)


if __name__ == '__main__':
    unittest.main()
