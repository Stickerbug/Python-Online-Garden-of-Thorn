# -*- coding: utf-8 -*-
"""2048 规则核心的验收用例（用户验收 1–4；规则 v2：5×5 + 15% 合并失败）。"""

from __future__ import annotations

import unittest

import minigame_2048 as g

SIZE = g.BOARD_SIZE


def board(rows):
    cells = []
    for row in rows:
        assert len(row) == SIZE, row
        cells.extend(row)
    return cells


def rows(cells):
    return [list(cells[index * SIZE:index * SIZE + SIZE]) for index in range(SIZE)]


def find_roll(target):
    """找一个随机状态，让下一次合并判定的 roll 恰好等于 target。"""

    for seed in range(1, 500000):
        _nxt, roll = g.rng_range(seed, 100)
        if roll == target:
            return seed
    raise AssertionError(f"找不到 roll={target} 的随机状态")


def find_state(fail_spec):
    """找一个随机状态，让接下来的合并判定依次命中给定的失败/成功序列。"""

    for seed in range(1, 500000):
        state = seed
        ok = True
        for want_fail in fail_spec:
            state, roll = g.rng_range(state, 100)
            if (roll < g.MERGE_FAIL_PERCENT) != bool(want_fail):
                ok = False
                break
        if ok:
            return seed
    raise AssertionError(f"找不到满足 {fail_spec} 的随机状态")


FAIL, OK = True, False
ROLL_FAIL_MAX = g.MERGE_FAIL_PERCENT - 1          # 14：失败
ROLL_OK_MIN = g.MERGE_FAIL_PERCENT                # 15：成功


def move_line(line, direction="left", rng_state=0):
    """把一行放进空棋盘再滑动，取回那一行（用于验收用例 1）。"""

    cells = board([line] + [[0] * SIZE for _ in range(SIZE - 1)])
    result = g.apply_move(cells, g.DIRECTIONS[direction], rng_state)
    return rows(result["cells"])[0], result["gained"], result["merges"], result["rng_state"]


class BoardShapeTests(unittest.TestCase):
    def test_rules_v2_is_five_by_five(self):
        self.assertEqual(g.RULES_VERSION, 2)
        self.assertEqual(SIZE, 5)
        self.assertEqual(g.CELL_COUNT, 25)
        self.assertEqual(len(g.initial_state(1)["cells"]), 25)


class MergeRuleTests(unittest.TestCase):
    def test_four_twos_merge_into_two_fours_when_both_succeed(self):
        line, gained, merges, _state = move_line([2, 2, 2, 2, 0], rng_state=find_state([OK, OK]))
        self.assertEqual(line, [4, 4, 0, 0, 0])
        self.assertEqual(gained, 8)
        self.assertEqual([item["failed"] for item in merges], [False, False])

    def test_failed_merge_keeps_value_and_does_not_double(self):
        line, gained, merges, _state = move_line([2, 2, 0, 0, 0], rng_state=find_state([FAIL]))
        self.assertEqual(line, [2, 0, 0, 0, 0])          # 只留下一个原值方块
        self.assertEqual(gained, 2)                       # 分数按留下的方块算
        self.assertTrue(merges[0]["failed"])
        self.assertEqual(merges[0]["value"], 2)

    def test_roll_boundary_is_exactly_fifteen_percent(self):
        line, _gained, merges, _state = move_line([2, 2, 0, 0, 0], rng_state=find_roll(ROLL_FAIL_MAX))
        self.assertTrue(merges[0]["failed"], "roll=14 应当失败")
        self.assertEqual(line[0], 2)
        line_ok, _gained_ok, merges_ok, _state_ok = move_line(
            [2, 2, 0, 0, 0], rng_state=find_roll(ROLL_OK_MIN),
        )
        self.assertFalse(merges_ok[0]["failed"], "roll=15 应当成功")
        self.assertEqual(line_ok[0], 4)

    def test_each_merge_consumes_one_roll_in_scan_order(self):
        # 第一次失败、第二次成功：[2,2,2,2] → [2,4]，得分 2+4
        line, gained, merges, _state = move_line([2, 2, 2, 2, 0], rng_state=find_state([FAIL, OK]))
        self.assertEqual(line, [2, 4, 0, 0, 0])
        self.assertEqual(gained, 6)
        self.assertEqual([item["failed"] for item in merges], [True, False])

    def test_two_two_four_keeps_first_merge(self):
        line, gained, _merges, _state = move_line([2, 2, 4, 0, 0], rng_state=find_state([OK]))
        self.assertEqual(line, [4, 4, 0, 0, 0])
        self.assertEqual(gained, 4)

    def test_four_fours_merge_into_two_eights(self):
        line, gained, _merges, _state = move_line([4, 4, 4, 4, 0], rng_state=find_state([OK, OK]))
        self.assertEqual(line, [8, 8, 0, 0, 0])
        self.assertEqual(gained, 16)

    def test_merged_tile_does_not_merge_again_in_the_same_move(self):
        line, gained, _merges, _state = move_line([2, 2, 4, 4, 0], rng_state=find_state([OK, OK]))
        self.assertEqual(line, [4, 8, 0, 0, 0])
        self.assertEqual(gained, 12)

    def test_right_direction_is_mirrored(self):
        line, gained, _merges, _state = move_line(
            [2, 2, 2, 2, 0], "right", rng_state=find_state([OK, OK]),
        )
        self.assertEqual(line, [0, 0, 0, 4, 4])
        self.assertEqual(gained, 8)

    def test_up_and_down_columns(self):
        cells = board([[2, 0, 0, 0, 0], [2, 0, 0, 0, 0], [4, 0, 0, 0, 0],
                       [4, 0, 0, 0, 0], [0] * 5])
        up = g.apply_move(cells, g.DIRECTIONS["up"], find_state([OK, OK]))
        self.assertEqual(rows(up["cells"])[0][0], 4)
        self.assertEqual(rows(up["cells"])[1][0], 8)
        self.assertEqual(up["gained"], 12)
        down = g.apply_move(cells, g.DIRECTIONS["down"], find_state([OK, OK]))
        self.assertEqual(rows(down["cells"])[3][0], 4)
        self.assertEqual(rows(down["cells"])[4][0], 8)

    def test_rng_advances_on_merge_and_stays_on_invalid_move(self):
        state = find_state([FAIL])
        moved = g.apply_move(board([[2, 2, 0, 0, 0]] + [[0] * 5] * 4), g.DIRECTIONS["left"], state)
        self.assertNotEqual(moved["rng_state"], state)
        stuck = board([[2, 4, 8, 16, 32]] + [[0] * 5] * 4)
        still = g.apply_move(stuck, g.DIRECTIONS["left"], state)
        self.assertFalse(still["changed"])
        self.assertEqual(still["rng_state"], state)

    def test_merge_failure_rate_is_about_fifteen_percent(self):
        cells = board([[2, 2, 0, 0, 0]] + [[0] * 5] * 4)
        state = 24681357
        failures = 0
        rounds = 4000
        for _ in range(rounds):
            result = g.apply_move(cells, g.DIRECTIONS["left"], state)
            state = result["rng_state"]
            failures += 1 if result["merges"][0]["failed"] else 0
        ratio = failures / rounds
        self.assertGreater(ratio, 0.12)
        self.assertLess(ratio, 0.18)

    def test_long_names_come_from_the_fixed_palette(self):
        expected = {
            2: ("Common", "#7EEF6D"), 4: ("Unusual", "#FFE65D"), 8: ("Rare", "#4D52E3"),
            16: ("Epic", "#861FDE"), 32: ("Legendary", "#DE1F1F"), 64: ("Mythic", "#1FDBDE"),
            128: ("Ultra", "#FF2B75"), 256: ("Super", "#2BFFA3"), 512: ("Omega", "#F329D9"),
            1024: ("Unique", "#555555"), 2048: ("Eternal", "#EEEEEE"), 4096: ("Fabled", "#FF5500"),
            8192: ("Divine", "#67549C"), 16384: ("Astral", "#046307"), 32768: ("Celestial", "#00BFFF"),
            65536: ("Galactic", "#7F0226"), 131072: ("Apotheotic", "#B3AB56"),
        }
        self.assertEqual(len(g.RARITY_TABLE), 17)
        for value, (name, bg) in expected.items():
            item = g.rarity_for(value)
            self.assertEqual(item["name"], name, value)
            self.assertEqual(item["bg"], bg, value)
        self.assertIsNone(g.rarity_for(262144))          # 超出色表：渲染层退回数字


class SpawnTests(unittest.TestCase):
    def test_only_changed_moves_spawn_and_score(self):
        state = g.initial_state(12345)
        blocked = {"seed": state["seed"], "rng_state": state["rng_state"],
                   "cells": board([[2, 4, 8, 16, 0]] + [[0] * 5] * 4),
                   "score": 10}
        left = g.step(dict(blocked), g.DIRECTIONS["left"])       # 左移无效：第一行已靠左
        self.assertFalse(left["changed"])
        self.assertEqual(left["gained"], 0)
        self.assertEqual(left["score"], 10)
        self.assertEqual(left["rng_state"], blocked["rng_state"])  # 随机状态不动
        self.assertEqual(left["cells"], blocked["cells"])
        right = g.step(dict(blocked), g.DIRECTIONS["right"])     # 有效但没加分：仍要生成
        self.assertTrue(right["changed"])
        self.assertEqual(right["gained"], 0)
        self.assertEqual(right["score"], 10)
        self.assertIsNotNone(right["spawned"])
        self.assertNotEqual(right["rng_state"], blocked["rng_state"])

    def test_spawn_distribution_is_about_90_percent(self):
        cells = [0] * g.CELL_COUNT
        state = 987654321
        twos = 0
        total = 4000
        for _ in range(total):
            cells, state, info = g.spawn_tile(cells, state)
            if info["value"] == 2:
                twos += 1
            cells[info["index"]] = 0          # 清掉，保持"只有一个空格"的稳定抽法
        ratio = twos / total
        self.assertGreater(ratio, 0.87)
        self.assertLess(ratio, 0.93)

    def test_spawn_places_into_empty_cells_only(self):
        cells = board([[2, 4, 2, 4, 2], [4, 2, 4, 2, 4], [2, 4, 2, 4, 2],
                       [4, 2, 4, 2, 4], [2, 4, 2, 4, 0]])
        new_cells, _state, info = g.spawn_tile(cells, 42)
        self.assertEqual(info["index"], 24)
        self.assertIn(new_cells[24], (2, 4))

    def test_game_over_requires_full_board_without_merges(self):
        stuck = board([[2, 4, 2, 4, 2], [4, 2, 4, 2, 4], [2, 4, 2, 4, 2],
                       [4, 2, 4, 2, 4], [2, 4, 2, 4, 2]])
        self.assertTrue(g.is_game_over(stuck))
        mergeable = board([[2, 2, 4, 8, 16], [4, 8, 16, 32, 64], [2, 4, 8, 16, 32],
                           [4, 8, 16, 32, 64], [2, 4, 8, 16, 32]])
        self.assertFalse(g.is_game_over(mergeable))
        roomy = board([[2, 0, 4, 8, 16], [4, 8, 16, 32, 64], [2, 4, 8, 16, 32],
                       [4, 8, 16, 32, 64], [2, 4, 8, 16, 32]])
        self.assertFalse(g.is_game_over(roomy))


class DeterminismTests(unittest.TestCase):
    def test_initial_state_is_deterministic_and_has_two_tiles(self):
        first = g.initial_state(20240920)
        second = g.initial_state(20240920)
        self.assertEqual(first, second)
        self.assertEqual(len([value for value in first["cells"] if value]), 2)

    def test_replay_matches_step_by_step(self):
        seed = 777
        ops = "lurdllur"
        state = g.initial_state(seed)
        for char in ops:
            step_result = g.step(state, g.CHAR_TO_DIRECTION[char])
            state = {"seed": seed, "rng_state": step_result["rng_state"],
                     "cells": step_result["cells"], "score": step_result["score"]}
        replayed = g.replay(seed, ops)
        self.assertEqual(replayed["cells"], state["cells"])
        self.assertEqual(replayed["score"], state["score"])
        self.assertEqual(replayed["rng_state"], state["rng_state"])
        self.assertEqual(replayed["index"], len(ops))

    def test_replay_from_checkpoint_matches_full_replay(self):
        seed = 24680
        ops = "lurdllurdu"
        full = g.replay(seed, ops)
        middle = g.replay(seed, ops, up_to=4)
        checkpoint = {"seed": seed, "rng_state": middle["rng_state"],
                      "cells": middle["cells"], "score": middle["score"]}
        tail = g.replay(seed, ops[4:], start_state=checkpoint)
        self.assertEqual(tail["cells"], full["cells"])
        self.assertEqual(tail["score"], full["score"])
        self.assertEqual(tail["rng_state"], full["rng_state"])

    def test_failure_pattern_is_reproducible_from_seed_and_ops(self):
        ops = "l" * 6 + "u" * 4 + "r" * 3 + "d" * 5
        first = g.replay(31337, ops)
        second = g.replay(31337, ops)
        self.assertEqual(first["cells"], second["cells"])
        self.assertEqual(first["score"], second["score"])
        self.assertEqual(first["rng_state"], second["rng_state"])

    def test_verify_submission_accepts_matching_and_rejects_tampering(self):
        seed = 13579
        ops = "lurd"
        truth = g.replay(seed, ops)
        ok = g.verify_submission(seed, ops, claimed_score=truth["score"],
                                 claimed_cells=truth["cells"])
        self.assertTrue(ok["ok"], ok)
        bad_score = g.verify_submission(seed, ops, claimed_score=truth["score"] + 4)
        self.assertFalse(bad_score["ok"])
        bad_cells = g.verify_submission(seed, ops, claimed_cells=[2] * g.CELL_COUNT)
        self.assertFalse(bad_cells["ok"])
        unknown = g.verify_submission(seed, "lx")
        self.assertFalse(unknown["ok"])

    def test_direction_input_forms_are_equivalent(self):
        self.assertEqual(g.ops_from_list(["left", "up", "right", "down"]), "lurd")
        self.assertEqual(g.ops_from_list([0, 2, 1, 3]), "lurd")
        self.assertEqual(g.ops_from_list("lurd"), "lurd")

    def test_eternal_flag_fires_once_per_reach(self):
        # 直接摆一个 1024+1024 的局面；用"必定成功"的随机状态，合并后应报"首次达成 2048"。
        state = {"seed": 5, "rng_state": find_state([OK]), "score": 0,
                 "cells": board([[1024, 1024, 0, 0, 0]] + [[0] * 5] * 4)}
        result = g.step(state, g.DIRECTIONS["left"])
        self.assertTrue(result["reached_2048"])
        self.assertEqual(result["score"], 2048)
        again = g.step({"seed": 5, "rng_state": result["rng_state"], "score": result["score"],
                        "cells": result["cells"]}, g.DIRECTIONS["down"])
        self.assertFalse(again["reached_2048"])


if __name__ == "__main__":
    unittest.main()
