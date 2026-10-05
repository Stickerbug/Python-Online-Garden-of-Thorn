# -*- coding: utf-8 -*-
"""AI 入口自选血量（50-1000，仅 AI 一侧）：引擎 start_game 覆写生效。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_engine import GameEngine  # noqa: E402


def _start_engine(overrides):
    engine = GameEngine()
    engine.player_health_overrides = overrides
    # mulligan=False：跳过调度阶段直接完成开局（快照在 _finish_game_start 保存）
    engine.start_game(skip_pregame_validation=True, mulligan=False)
    return engine


class AiHealthOverrideTest(unittest.TestCase):
    def test_override_applies_to_ai_seat(self):
        engine = _start_engine({1: 350})
        ps = engine.players[1]
        self.assertEqual(ps.health, 350)
        self.assertEqual(ps.max_health, 350)
        self.assertEqual(ps.base_max_health, 350)
        # 对手（玩家侧）保持默认 100
        human = engine.players[0]
        self.assertEqual(human.health, 100)
        self.assertEqual(human.max_health, 100)
        self.assertEqual(human.base_max_health, 100)

    def test_override_works_for_either_seat(self):
        engine = _start_engine({0: 80})
        self.assertEqual(engine.players[0].health, 80)
        self.assertEqual(engine.players[1].health, 100)

    def test_override_beats_second_player_health(self):
        # 后手本会被赋 SECOND_PLAYER_HEALTH；覆写在其后应用，必须胜出
        for seat in (0, 1):
            engine = _start_engine({seat: 500})
            self.assertEqual(engine.players[seat].health, 500, f'seat {seat}')

    def test_no_override_keeps_default(self):
        engine = _start_engine({})
        for seat in (0, 1):
            self.assertEqual(engine.players[seat].health, 100)
            self.assertEqual(engine.players[seat].max_health, 100)

    def test_match_start_snapshot_follows_override(self):
        engine = _start_engine({1: 350})
        snap = engine.players[1].match_start_snapshot
        self.assertEqual(snap['health'], 350)

    def test_validator_bounds(self):
        # 与 app._validate_ai_test_health 相同的边界（不导入 app，独立复现校验）
        def validate(value):
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                return None
            return parsed if 50 <= parsed <= 1000 else None

        self.assertEqual(validate(50), 50)
        self.assertEqual(validate(1000), 1000)
        self.assertEqual(validate(100), 100)
        self.assertIsNone(validate(49))
        self.assertIsNone(validate(1001))
        self.assertIsNone(validate('abc'))
        self.assertIsNone(validate(None))
        self.assertIsNone(validate('100.5'))
        self.assertEqual(validate(100.5), 100)  # 数值型小数被截断，无害


if __name__ == '__main__':
    unittest.main()
