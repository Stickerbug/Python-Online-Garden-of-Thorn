# -*- coding: utf-8 -*-
"""2v2 选牌上限守卫（幽灵房根源）：2v2 draft_pick 曾缺目标数检查，
双击/重试的多余选牌越过 15 张上限（实测 16/15），开局校验拒绝、整局永久卡死。"""

import unittest

from game_engine_2v2 import GameEngine2v2


class DraftOverPickTests(unittest.TestCase):
    @staticmethod
    def _draft_engine():
        engine = GameEngine2v2()
        engine.start_draft()
        engine.player_draft_started = [True] * 4
        for i in range(4):
            engine._generate_draft_options_for_player(i)
        return engine

    def test_overpick_is_rejected_at_target(self):
        engine = self._draft_engine()
        target = engine.draft_target_count(0)
        self.assertTrue(engine.draft_options[0], '应有可选牌')
        # 选满目标数（每轮选项会刷新，取当前第一项）
        for _ in range(target):
            current = [c.def_id for c in engine.draft_options[0]]
            self.assertTrue(current, '选项不应为空')
            result = engine.draft_pick(0, current[0])
            self.assertTrue(result.get('success'), result)
        self.assertEqual(len(engine.draft_picks[0]), target)
        # 超限选牌必须被拒绝（此前 2v2 缺这道守卫，出现 16/15）
        result = engine.draft_pick(0, engine.draft_options[0][0].def_id if engine.draft_options[0] else engine.draft_picks[0][0])
        self.assertFalse(result.get('success'))
        self.assertEqual(len(engine.draft_picks[0]), target)

    def test_overpick_does_not_block_pregame_start(self):
        """就算历史数据已经超限（16/15），开局校验应自愈裁掉而不是永久拒绝。"""
        engine = self._draft_engine()
        target = engine.draft_target_count(0)
        options = [c.def_id for c in engine.draft_options[0]]
        for _ in range(target):
            engine.draft_pick(0, options[0])
        engine.draft_picks[0].append(options[0])   # 模拟历史脏数据：16/15
        for pidx in range(4):
            while len(engine.draft_picks[pidx]) < engine.draft_target_count(pidx):
                pick_options = engine.draft_options[pidx] or engine.draft_options[0]
                engine.draft_pick(pidx, pick_options[0].def_id)
        valid, reason, details = engine.validate_pregame_ready()
        # 裁剪后不再因 draft_count_invalid 拒绝（其它校验项本测试不涉及）
        self.assertFalse(reason.startswith('draft_count_invalid'), (reason, details))


if __name__ == '__main__':
    unittest.main()
