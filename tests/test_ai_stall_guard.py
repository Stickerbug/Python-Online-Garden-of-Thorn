# -*- coding: utf-8 -*-
"""AI 死机防护网（_ai_test_stall_fingerprint）：selection-only 停滞检测。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_engine import GameEngine  # noqa: E402
import app  # noqa: E402


def _engine():
    engine = GameEngine()
    engine.allowed_card_ids = None
    engine.draft_picks[0] = ['Stinger', 'Bubble', 'Light', 'Fang', 'Rose', 'Bone'] * 2
    engine.draft_picks[1] = ['Stinger', 'Bubble', 'Light', 'Fang', 'Rose', 'Bone'] * 2
    engine.start_game(skip_pregame_validation=True, mulligan=False)
    return engine


def _open_choice(engine, player_id=0):
    hand = engine.players[player_id].hand
    engine.pending_choice = {
        'card': hand[0].to_dict() if hand else {},
        'player_id': player_id,
        'choice_type': 'choose_cards_from_hand',
        'choice_params': {'target': 'self', 'min_count': 1, 'max_count': 1, 'cancellable': True},
        'original_choice': None,
        'already_paid': False,
    }
    return engine.pending_choice


class AiStallFingerprintTest(unittest.TestCase):
    def test_importable_constants(self):
        self.assertGreaterEqual(app.AI_TEST_STALL_ACTION_LIMIT, 4)
        self.assertTrue(callable(app._ai_test_stall_fingerprint))

    def test_fingerprint_stable_for_no_progress(self):
        engine = _engine()
        _open_choice(engine)
        # 模拟 selection-only 动作：引擎完全没动 → 指纹不变
        self.assertEqual(
            app._ai_test_stall_fingerprint(engine),
            app._ai_test_stall_fingerprint(engine),
        )

    def test_fingerprint_changes_on_progress(self):
        engine = _engine()
        _open_choice(engine)
        before = app._ai_test_stall_fingerprint(engine)
        # 1) 日志增长（真实动作都会写日志）
        engine.log.append('测试：打出一张牌')
        self.assertNotEqual(before, app._ai_test_stall_fingerprint(engine))
        engine.log.pop()
        # 2) 窗口关闭
        engine.pending_choice = None
        self.assertNotEqual(before, app._ai_test_stall_fingerprint(engine))
        # 3) 换成另一个窗口（类型不同）
        other = _open_choice(engine)
        other['choice_type'] = 'choose_target'
        self.assertNotEqual(before, app._ai_test_stall_fingerprint(engine))
        other['choice_type'] = 'choose_cards_from_hand'
        self.assertEqual(before, app._ai_test_stall_fingerprint(engine))
        # 4) 回合数变化
        engine.round_num += 1
        self.assertNotEqual(before, app._ai_test_stall_fingerprint(engine))


if __name__ == '__main__':
    unittest.main()
