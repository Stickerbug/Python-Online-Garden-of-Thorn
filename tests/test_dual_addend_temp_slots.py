# -*- coding: utf-8 -*-
"""补充反馈：裂变/聚变暂时位口径——授予/复制的层数记暂时位，基线回落卡面。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_engine import GameEngine, CardInstance, apply_card_fission_level  # noqa: E402


class DualSlotTempTests(unittest.TestCase):
    def test_add_fission_is_temp(self):
        card = CardInstance('Stinger')
        apply_card_fission_level(card, 3)
        self.assertEqual(card.fission_level, 3)
        self.assertEqual(card.fission_base, 1)

    def test_mimic_copy_layers_are_temp(self):
        engine = GameEngine()
        target = CardInstance('Stinger')
        apply_card_fission_level(target, 5)
        target.fusion_level = 4
        copy_card = engine._make_mimic_copy_card(target)
        # 减半层数记暂时位：level=ceil(5/2)=3，base 回落到卡面 1 → 显示 裂变:1+2
        self.assertEqual(copy_card.fission_level, 3)
        self.assertEqual(copy_card.fission_base, 1)
        self.assertEqual(copy_card.fusion_level, 2)
        self.assertEqual(copy_card.fusion_base, 1)

    def test_granted_copy_fission_resets_after_play(self):
        """造卡授予的裂变打出后回落卡面（旧行为：授予值记基线，打出不回落）。"""
        engine = GameEngine()
        card = CardInstance('Fang')
        card.fission_level = 3
        card.fission_count = 2
        card.fission_base = 1  # 修复后的造卡口径：base=卡面
        from game_engine import reset_card_after_play
        reset_card_after_play(card)
        self.assertEqual(card.fission_level, 1)


if __name__ == '__main__':
    unittest.main()
