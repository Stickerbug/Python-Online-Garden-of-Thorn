# -*- coding: utf-8 -*-
"""反馈 #390：2v2 引擎威力按段均分（R-30235 沙子威力1 = 4D×4）——对齐 1v1
的「全部加第一段、只加一次」口径；旧原子路径补 source_card。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_engine_2v2 import GameEngine2v2  # noqa: E402
from game_engine import CardInstance, apply_card_power_value  # noqa: E402


def _engine():
    e = GameEngine2v2()
    e.allowed_card_ids = None
    for pid in range(4):
        e.draft_picks[pid] = ['Stinger'] * 6
    e.start_game(skip_pregame_validation=True, mulligan=False)
    return e


def _play(e, def_id, power, fission=1):
    f = e.first_player
    t = next(pid for pid in e.get_enemies(f) if e.players[pid].health > 0)
    card = CardInstance(def_id)
    if power:
        apply_card_power_value(card, power)
    if fission > 1:
        card.fission_level = fission
        card.fission_count = fission - 1
    e.players[f].hand.insert(0, card)
    e.players[f].elixir = 99
    before = e.players[t].health
    result = e.play_card(f, card.instance_id, t, {'target_player_id': t})
    guard = 0
    while e.pending_response is not None and guard < 8:
        e.resolve_forced_response()
        if e.pending_response is not None:
            e.handle_response(int(e.pending_response.get('player_id', 1)), None)
        guard += 1
    return result, before - e.players[t].health


class Power2v2FirstHitTest(unittest.TestCase):
    def test_sand_power1_first_segment_only(self):
        """沙子(3D×4段) 威力1 → 第一段4、其余3 = 13（修复前 4D×4=16）。"""
        result, dealt = _play(_engine(), 'Sand', 1)
        self.assertTrue(result.get('success'), result.get('error'))
        self.assertEqual(dealt, 13)

    def test_sand_no_power_baseline(self):
        result, dealt = _play(_engine(), 'Sand', 0)
        self.assertTrue(result.get('success'), result.get('error'))
        self.assertEqual(dealt, 12)

    def test_stinger_power_single_hit(self):
        # 旧原子刺基数 20；若此前有测试把模组并入 CARD_DEFS 则是 21——
        # 两种基数下威力都应全额加在唯一段上。
        result, dealt = _play(_engine(), 'Stinger', 5)
        self.assertTrue(result.get('success'), result.get('error'))
        self.assertIn(dealt, (20 + 5, 21 + 5))

    def test_legacy_atoms_pass_source_card(self):
        """旧原子路径（无模组环境）现在也带 source_card：威力不再丢失。"""
        result, dealt = _play(_engine(), 'Sand', 2)
        self.assertTrue(result.get('success'), result.get('error'))
        self.assertEqual(dealt, (3 + 2) + 3 + 3 + 3)


if __name__ == '__main__':
    unittest.main()
