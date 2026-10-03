# -*- coding: utf-8 -*-
"""段位结算 2026-10-02 平衡：上限/段位减免/保分卡/双倍卡/共存3倍。"""
import unittest
import rank_system as rs


class RankSettlementTests(unittest.TestCase):
    def test_gain_clamped_between_1_and_10(self):
        # 打高 20 小段的对手：5+20=25 → 封顶 10
        self.assertEqual(rs.match_gain(0, 20), 10)
        # 被低 20 小段的对手打败：5-20=-15 → 保底 1
        self.assertEqual(rs.match_gain(20, 0), 1)
        # 同段位 5
        self.assertEqual(rs.match_gain(10, 10), 5)

    def test_loss_clamped_between_1_and_5(self):
        self.assertEqual(rs.match_loss(20, 10), 5)   # 3+10 → 封顶5
        self.assertEqual(rs.match_loss(0, 20), 1)    # 3-20 → 保底1

    def test_common_never_loses_points_or_demotes(self):
        # common 段内 0 分再输：不掉分不降段
        r = rs.apply_match_result(4, 0, 2, outcome='loss', opponent_tier_avg=6)
        self.assertEqual(r['points'], 0)
        self.assertFalse(r['demoted'])
        self.assertEqual(r['tier_index'], 4)
        self.assertEqual(r['streak'], 0)

    def test_unusual_loss_halved_rounding_up(self):
        # unusual（tier 4-7）：loss=3 → ceil(1.5)=2
        r = rs.apply_match_result(5, 10, 0, outcome='loss', opponent_tier_avg=5)
        self.assertEqual(r['delta'], -2)

    def test_loss_shield_cancels_loss_and_demotion(self):
        r = rs.apply_match_result(12, 0, 3, outcome='loss', opponent_tier_avg=12, loss_shield=True)
        self.assertTrue(r.get('shielded'))
        self.assertEqual(r['delta'], 0)
        self.assertFalse(r['demoted'])
        self.assertEqual(r['streak'], 0)

    def test_double_card_doubles_after_cap(self):
        # 封顶 +10 后翻倍 → +20
        r = rs.apply_match_result(9, 0, 0, outcome='win', opponent_tier_avg=30, double_card=True)
        self.assertEqual(r['delta'], 20)

    def test_daily_and_card_stack_to_triple(self):
        # 共存 ×3：+10 封顶 → +30
        r = rs.apply_match_result(9, 0, 0, outcome='win', opponent_tier_avg=30,
                                  daily_double=True, double_card=True)
        self.assertEqual(r['delta'], 30)
        self.assertTrue(r['daily_double'])
        self.assertTrue(r['double_card'])

    def test_daily_double_alone_still_doubles(self):
        r = rs.apply_match_result(10, 10, 0, outcome='win', opponent_tier_avg=10, daily_double=True)
        self.assertEqual(r['delta'], 10)   # 5 ×2


if __name__ == '__main__':
    unittest.main()
