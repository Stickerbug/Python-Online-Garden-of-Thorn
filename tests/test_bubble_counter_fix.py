# -*- coding: utf-8 -*-
"""泡泡（Bubble）反制修复（2026-10-12）：

修复前两个症状（用户报告"泡泡会完全闪避卡牌且会放逐它"）：
1. 1v1 引擎 halve_precision 分支的非精准路径写在 return 之后（死代码）——
   被反制的攻击牌效果不结算、也从不进弃牌堆，凭空消失；
2. 反制授予的闪避（dodge）在被反制牌结算期间就已生效——把被泡泡响应的
   那张攻击牌整个闪避掉（clamp_responder_props 在结算后才夹回，太迟）。

修复后语义：被反制的牌正常结算（精准减半、非精准全额），反制授予的闪避
保留给后续攻击。
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

    def baseline_damage(self, attack_id):
        engine = self.build_engine()
        attack = CardInstance(attack_id)
        engine.players[0].hand = [attack]
        engine.play_card(0, attack.instance_id, target_choice(1))
        if getattr(engine, 'pending_response', None):
            engine.handle_response(1, None)
        return 100 - engine.players[1].health

    def countered(self, attack_id):
        engine = self.build_engine()
        attack = CardInstance(attack_id)
        bubble = CardInstance('Bubble')
        engine.players[0].hand = [attack]
        engine.players[1].hand = [bubble]
        engine.play_card(0, attack.instance_id, target_choice(1))
        result = engine.handle_response(1, bubble.instance_id)
        return engine, result, attack, bubble

    def test_non_precision_attack_settles_fully_and_card_is_discarded(self):
        """非精准攻击被泡泡反制：全额结算（修复前 0 伤），牌进弃牌堆（修复前凭空消失）。"""
        engine, result, attack, bubble = self.countered('Basic')
        self.assertEqual(8, 100 - engine.players[1].health, '被反制的非精准攻击应全额结算')
        owner, zone, _ = engine._find_card_location(attack)
        self.assertEqual((0, 'discard'), (owner, zone), '被反制的攻击牌应进攻击方弃牌堆')
        self.assertEqual(1, engine.players[1].dodge, '反制授予的闪避应保留')

    def test_precision_attack_is_halved(self):
        """精准攻击被泡泡反制：伤害减半（修复前被闪避层整个吃掉）。"""
        attack_id = _find_precision_attack()
        base = self.baseline_damage(attack_id)
        engine, result, attack, bubble = self.countered(attack_id)
        dealt = 100 - engine.players[1].health
        self.assertEqual(math.ceil(base / 2), dealt, '精准被泡泡反制应减半')
        owner, zone, _ = engine._find_card_location(attack)
        self.assertEqual((0, 'discard'), (owner, zone))
        self.assertEqual(1, engine.players[1].dodge)

    def test_granted_dodge_dodges_the_next_attack(self):
        """泡泡授予的闪避应作用于下一张攻击（修复前它闪避的是被反制那张）。"""
        engine, _, _, _ = self.countered('Basic')
        self.assertEqual(92, engine.players[1].health)
        nxt = CardInstance('Basic')
        engine.players[0].hand = [nxt]
        engine.play_card(0, nxt.instance_id, target_choice(1))
        if getattr(engine, 'pending_response', None):
            engine.handle_response(1, None)
        self.assertEqual(92, engine.players[1].health, '下一张攻击应被保留的闪避挡下')
        self.assertEqual(0, engine.players[1].dodge, '闪避被消耗')


class BubbleCounter2v2Tests(BubbleCounterTests):
    """2v2 引擎同语义（继承用例，换引擎构造）。"""

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

    def baseline_damage(self, attack_id):
        engine = self.build_engine()
        attack = CardInstance(attack_id)
        # 2v2 空范围反制窗 decline 会拒绝：给目标席一张泡泡让窗口把该席
        # 纳入范围，再弃权（弃权不消耗手牌）。
        filler = CardInstance('Bubble')
        engine.players[0].hand = [attack]
        engine.players[2].hand = [filler]
        engine.play_card(0, attack.instance_id, 2, target_choice(2))
        if getattr(engine, 'pending_response', None):
            engine.handle_response(2, None)
        return 100 - engine.players[2].health

    def test_non_precision_attack_settles_fully_and_card_is_discarded(self):
        engine, result, attack, bubble = self.countered('Basic')
        self.assertEqual(8, 100 - engine.players[2].health, '2v2：被反制的非精准攻击应全额结算')
        owner, zone, _ = engine._find_card_location(attack)
        self.assertEqual((0, 'discard'), (owner, zone))
        self.assertEqual(1, engine.players[2].dodge)

    def test_precision_attack_is_halved(self):
        attack_id = _find_precision_attack()
        base = self.baseline_damage(attack_id)
        engine, result, attack, bubble = self.countered(attack_id)
        dealt = 100 - engine.players[2].health
        self.assertEqual(math.ceil(base / 2), dealt, '2v2：精准被泡泡反制应减半')
        self.assertEqual(1, engine.players[2].dodge)

    def test_granted_dodge_dodges_the_next_attack(self):
        engine, _, _, _ = self.countered('Basic')
        self.assertEqual(92, engine.players[2].health)
        nxt = CardInstance('Basic')
        filler = CardInstance('Bubble')
        engine.players[0].hand = [nxt]
        engine.players[2].hand = [filler]
        engine.play_card(0, nxt.instance_id, 2, target_choice(2))
        if getattr(engine, 'pending_response', None):
            engine.handle_response(2, None)
        self.assertEqual(92, engine.players[2].health, '2v2：下一张攻击应被保留的闪避挡下')
        self.assertEqual(0, engine.players[2].dodge)


if __name__ == '__main__':
    unittest.main()
