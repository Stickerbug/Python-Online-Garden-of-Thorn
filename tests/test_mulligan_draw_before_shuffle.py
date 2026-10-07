# -*- coding: utf-8 -*-
"""调度（平衡 2026-10-07）：先抽再洗——补抽发生在所选牌塞回抽牌堆之前，
调度必然拿到新牌；补抽不触发「到手牌时」效果（任何回合，含第一回合）。"""

import unittest

from cards import CardInstance
from game_engine import GameEngine


class MulliganDrawBeforeShuffleTests(unittest.TestCase):
    def build_engine(self):
        engine = GameEngine()
        engine.phase = 'mulligan'
        engine.mulligan_enabled = True
        for player in engine.players:
            player.hand = []
            player.deck = []
            player.discard = []
        engine._finish_game_start = lambda: True
        return engine

    def test_draw_happens_before_stuffing_back(self):
        engine = self.build_engine()
        ps = engine.players[0]
        swap_a = CardInstance('Basic')
        swap_b = CardInstance('Bone')
        fresh_a = CardInstance('Sand')
        fresh_b = CardInstance('Wing')
        ps.hand = [swap_a, swap_b]
        ps.deck = [fresh_a, fresh_b]  # 抽牌堆顶两张
        engine.mulligan_picks = [[swap_a.instance_id, swap_b.instance_id], None]

        engine._resolve_mulligans()

        # 补抽拿到的是抽牌堆顶的新牌，不是刚塞回的牌。
        self.assertIn(fresh_a, ps.hand)
        self.assertIn(fresh_b, ps.hand)
        self.assertNotIn(swap_a, ps.hand)
        self.assertNotIn(swap_b, ps.hand)
        # 所选牌塞回了抽牌堆（且抽牌堆被洗过）。
        self.assertIn(swap_a, ps.deck)
        self.assertIn(swap_b, ps.deck)

    def test_swap_draws_bypass_enter_hand_triggers(self):
        engine = self.build_engine()
        ps = engine.players[0]
        swap_a = CardInstance('Basic')
        fresh_a = CardInstance('Sand')
        fresh_b = CardInstance('Wing')
        ps.hand = [swap_a]
        ps.deck = [fresh_a, fresh_b]
        engine.mulligan_picks = [[swap_a.instance_id], None]
        enter_hand_calls = []
        engine._handle_card_enter_hand = lambda player_id, card: enter_hand_calls.append(card)

        engine._resolve_mulligans()

        # 换 1 张补抽 1 张进入手牌，但一次都不触发「到手牌时」效果。
        self.assertEqual(1, len(ps.hand))
        self.assertIn(fresh_a, ps.hand)
        self.assertEqual([], enter_hand_calls)


if __name__ == '__main__':
    unittest.main()
