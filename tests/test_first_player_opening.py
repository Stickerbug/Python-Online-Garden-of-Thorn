# -*- coding: utf-8 -*-
"""多人对战先手开局资源与「先手压制」（2026-10-10 平衡调整）：

- 默认先手：起手 3 张牌、3E
- 先手压制：尽可能获得先手（选择者中随机一人，双选也生效），
  生效者第一回合在先手基础上多 4E（7E）、起手多 1 张牌（4 张）
- 后手不变：5 张牌、5E
- 2v2：所有选择者（不分队伍）中随机一人生效
"""

import unittest

from cards import (
    FIRST_PLAYER_ELIXIR,
    FIRST_PLAYER_HAND_SIZE,
    INITIAL_ELIXIR,
    INITIAL_HAND_SIZE,
)
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2


def _start_engine(opening=(1, 1)):
    engine = GameEngine()
    engine.phase = 'draft'
    for player_id in range(2):
        engine.opening_event_picks[player_id] = opening[player_id]
        engine.player_draft_started[player_id] = True
        engine.opening_event_sub_choices[player_id] = None
        first_allowed = engine.fated_draw_pool_defs()[0]
        engine.draft_picks[player_id] = [first_allowed] * engine.draft_target_count(player_id)
        engine.player_ready[player_id] = True
    engine.start_game(skip_pregame_validation=True, mulligan=False)
    return engine


class FirstPlayerOpeningTests(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(FIRST_PLAYER_HAND_SIZE, 3)
        self.assertEqual(FIRST_PLAYER_ELIXIR, 3)
        self.assertEqual(INITIAL_HAND_SIZE, 5)
        self.assertEqual(INITIAL_ELIXIR, 5)

    def test_default_first_player_gets_3_cards_3e(self):
        engine = _start_engine(opening=(1, 1))
        first = engine.players[engine.first_player]
        second = engine.players[1 - engine.first_player]
        self.assertEqual(len(first.hand), 3)
        self.assertEqual(first.elixir, 3)
        self.assertEqual(len(second.hand), 5)
        self.assertEqual(second.elixir, 5)

    def test_opening_pressure_single_picker(self):
        engine = _start_engine(opening=(7, 1))
        first = engine.players[engine.first_player]
        self.assertEqual(engine.opening_event_picks[engine.first_player], 7)
        self.assertEqual(len(first.hand), 4)
        self.assertEqual(first.elixir, 7)

    def test_opening_pressure_both_pick_still_applies_randomly(self):
        # 双选不再互相抵消：随机一人获得先手并享受效果，另一人按后手结算。
        engine = _start_engine(opening=(7, 7))
        first = engine.players[engine.first_player]
        second = engine.players[1 - engine.first_player]
        self.assertEqual(engine.opening_event_picks[engine.first_player], 7)
        self.assertEqual(len(first.hand), 4)
        self.assertEqual(first.elixir, 7)
        self.assertEqual(len(second.hand), 5)
        self.assertEqual(second.elixir, 5)


class OpeningPressure2v2Tests(unittest.TestCase):
    def _engine_with_picks(self, picks):
        engine = GameEngine2v2()
        for pid, pick in enumerate(picks):
            engine.opening_event_picks[pid] = pick
        return engine

    def test_no_pickers_means_nobody_effective(self):
        engine = self._engine_with_picks([1, 1, 1, 1])
        self.assertEqual(engine._effective_first_pressure_players(), set())

    def test_effective_player_is_randomly_chosen_from_all_pickers(self):
        seen = set()
        for _ in range(60):
            # 两队各一人选择：不再按队伍人数比较，四个选择者都可能生效
            engine = self._engine_with_picks([7, 1, 7, 7])
            effective = engine._effective_first_pressure_players()
            self.assertEqual(len(effective), 1)
            self.assertIn(next(iter(effective)), {0, 2, 3})
            seen.add(next(iter(effective)))
        self.assertTrue({0, 2, 3} <= seen)


if __name__ == '__main__':
    unittest.main()
