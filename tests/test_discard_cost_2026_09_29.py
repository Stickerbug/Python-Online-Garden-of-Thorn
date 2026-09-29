# -*- coding: utf-8 -*-
"""弃牌费用不足时弃全部手牌（设计 2026-09-29）。

受影响卡（数据侧已改）：护身符/酸/蝉3301——不再被 play_requires 的
min 门槛禁止打出；效果执行时按 if_else 分流：够 2 张弹 request_ui 选牌，
不足则 zone_random_ids(exclude_current) 弃光其余手牌并照常结算后续。
引擎侧配套：zone_count / zone_random_ids 表达式支持 exclude_current
（排除正在结算的牌，mod_runtime_v2 与引擎 _eval_expr 双路径同口径）。
"""

import unittest

import app  # noqa: F401  装载模组
from game_engine import CARD_DEFS, CardInstance, GameEngine


def target_choice(player_id):
    return {'target_player': player_id, 'target_player_id': player_id, 'target_id': player_id}


def find_card_id(name_cn):
    for key, value in CARD_DEFS.items():
        if value.name_cn == name_cn:
            return key
    raise AssertionError(f'card not found: {name_cn}')


AMULET = find_card_id('护身符')
ACID = find_card_id('酸')
CICADA = find_card_id('蝉3301')


class DiscardCostInsufficientTests(unittest.TestCase):
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

    def play(self, engine, card, other_cards=()):
        engine.players[0].hand = [card] + list(other_cards)
        result = engine.play_card(0, card.instance_id, target_choice(1))
        return result

    def test_amulet_plays_with_one_other_card(self):
        """护身符 1 张其他手牌：允许打出、弃光其余、威力照加。"""
        engine = self.build_engine()
        engine.players[1].hand = [CardInstance('Sand')]
        self.play(engine, CardInstance(AMULET), [CardInstance('Bone')])
        self.assertEqual([], engine.players[0].hand)
        self.assertEqual(2, len(engine.players[0].discard))  # 骨头 + 打出的护身符
        self.assertEqual(5, engine.players[1].hand[0].power_value)

    def test_amulet_plays_with_no_other_card(self):
        engine = self.build_engine()
        engine.players[1].hand = [CardInstance('Sand')]
        self.play(engine, CardInstance(AMULET))
        self.assertEqual([], engine.players[0].hand)
        self.assertEqual(5, engine.players[1].hand[0].power_value)

    def test_amulet_enough_cards_opens_picker(self):
        """2 张其他手牌：弹 request_ui 选牌（不预排队卡死）。"""
        engine = self.build_engine()
        self.play(engine, CardInstance(AMULET), [CardInstance('Bone'), CardInstance('Sand')])
        self.assertIsNotNone(getattr(engine, 'pending_v2_ui', None))
        self.assertEqual('amulet_discard', (engine.pending_v2_ui or {}).get('save_as'))

    def test_acid_discards_all_and_draws_equally(self):
        """酸 1 张其他手牌：弃光、抽等量（1 张）。"""
        engine = self.build_engine()
        engine.players[0].deck = [CardInstance('Wing'), CardInstance('Light')]
        engine.players[1].hand = [CardInstance('Bone')]
        self.play(engine, CardInstance(ACID), [CardInstance('Bone')])
        self.assertEqual(['翅膀'], [c.name_cn for c in engine.players[0].hand])
        self.assertEqual(2, len(engine.players[0].discard))

    def test_cicada_discards_all_and_choice_continues(self):
        """蝉3301 1 张其他手牌：弃光且后续三选一照常弹出。"""
        engine = self.build_engine()
        self.play(engine, CardInstance(CICADA), [CardInstance('Bone')])
        self.assertEqual([], engine.players[0].hand)
        self.assertEqual(2, len(engine.players[0].discard))
        pending = getattr(engine, 'pending_v2_ui', None)
        self.assertIsNotNone(pending)
        self.assertEqual('cicada_mode', (pending or {}).get('save_as'))


if __name__ == '__main__':
    unittest.main()
