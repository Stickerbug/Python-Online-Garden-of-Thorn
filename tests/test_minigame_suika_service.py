# -*- coding: utf-8 -*-
"""合成大花花服务层：立刻落库 + 启发式校验 + 榜单分账（内存库，不碰真实数据）。"""

from __future__ import annotations

import sqlite3
import unittest
from datetime import timedelta
from unittest import mock

import minigame_2048_service as base
import minigame_suika_service as suika


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, display_name TEXT,"
        " thorn_dew_free INTEGER DEFAULT 0, thorn_dew_paid INTEGER DEFAULT 0);"
    )
    conn.execute("INSERT INTO users (id, username, display_name) VALUES (7, 'probe', 'probe')")
    conn.execute("INSERT INTO users (id, username, display_name) VALUES (8, 'other', 'other')")
    suika.ensure_schema(conn)
    return conn


class SuikaServiceTests(unittest.TestCase):
    def test_new_game_and_verified_sync(self):
        conn = _conn()
        game = suika.load_state(conn, 7, seed=12345)
        self.assertEqual(game['drop_index'], 0)
        result = suika.sync_progress(
            conn, 7, game['game_uid'], 0,
            [{'t': 0, 'x': 300}, {'t': 600, 'x': 320}],
            claimed_score=9, claimed_max_tier=1,
        )
        self.assertEqual(result['status'], 'ok')
        self.assertTrue(result['verified'])
        self.assertEqual(result['verified_score'], 9)
        table = suika.leaderboard(conn, window='all', limit=10)
        self.assertEqual(table['participants'], 1)
        self.assertEqual(table['entries'][0]['score'], 9)
        self.assertEqual(table['entries'][0]['max_tile'], 1)

    def test_cheating_batch_is_stored_but_not_ranked(self):
        conn = _conn()
        game = suika.load_state(conn, 7, seed=1)
        suika.sync_progress(conn, 7, game['game_uid'], 0,
                            [{'t': 0, 'x': 300}, {'t': 600, 'x': 320}],
                            claimed_score=9, claimed_max_tier=1)
        bad = suika.sync_progress(conn, 7, game['game_uid'], 2,
                                  [{'t': 700, 'x': 100}], claimed_score=999999, claimed_max_tier=9)
        self.assertEqual(bad['status'], 'ok')
        self.assertFalse(bad['verified'])
        # 存档分数不被污染、异常投放也不进序列 → 后面的合法上报仍然能上榜
        self.assertEqual(bad['game']['score'], 9)
        self.assertEqual(bad['game']['drop_index'], 2)
        good = suika.sync_progress(conn, 7, game['game_uid'], 2,
                                   [{'t': 1500, 'x': 200}], claimed_score=30, claimed_max_tier=2)
        self.assertTrue(good['verified'])
        self.assertEqual(good['verified_score'], 30)
        table = suika.leaderboard(conn, window='all', limit=10)
        self.assertEqual(table['entries'][0]['score'], 30)

    def test_boards_are_separated_by_game_key(self):
        conn = _conn()
        game = suika.load_state(conn, 7, seed=1)
        suika.sync_progress(conn, 7, game['game_uid'], 0, [{'t': 0, 'x': 300}],
                            claimed_score=5, claimed_max_tier=1)
        # 手工塞一条 2048 的记录：不应该出现在 suika 榜里
        base.ensure_schema(conn)
        conn.execute(
            "INSERT INTO minigame_2048_records"
            " (user_id, game_id, score, max_tile, op_index, rules_version, verified_at, source,"
            "  created_at, game_key) VALUES (8, 999, 4242, 2048, 3, 2, ?, 'online', ?, '2048')",
            (base.now_iso(), base.now_iso()),
        )
        conn.commit()
        self.assertEqual(suika.leaderboard(conn, window='all', limit=10)['entries'][0]['score'], 5)
        self.assertEqual(base.leaderboard(conn, window='all', limit=10)['entries'][0]['score'], 4242)

    def test_period_keys_are_prefixed(self):
        cutoff = base.parse_iso('2026-09-21T00:00:00Z')
        self.assertTrue(suika.base.period_key_for(cutoff, 'suika').startswith('suika-'))
        self.assertTrue(base.period_key_for(cutoff).startswith('2048-'))

    def test_time_anchor_rejects_impossible_pace(self):
        """凭空编时间戳的批量造假：一墙钟秒都没过，却申报了 2.5 分钟的游戏时间。"""
        conn = _conn()
        game = suika.load_state(conn, 7, seed=1)
        first = suika.sync_progress(conn, 7, game['game_uid'], 0,
                                    [{'t': 0, 'x': 300}, {'t': 600, 'x': 320}],
                                    claimed_score=9, claimed_max_tier=1)
        self.assertTrue(first['verified'])
        bad = suika.sync_progress(conn, 7, game['game_uid'], 2,
                                  [{'t': 1000 + i * 500, 'x': 300} for i in range(300)],
                                  claimed_score=1609, claimed_max_tier=3)
        self.assertEqual(bad['status'], 'ok')
        self.assertFalse(bad['verified'])
        self.assertEqual(bad['reason'], '投放节奏与实际时间不符')
        # 与其他校验不通过一样：异常投放不进序列、分数不抬，后续合法批次仍可上榜
        self.assertEqual(bad['game']['drop_index'], 2)
        self.assertEqual(bad['game']['score'], 9)

    def test_time_anchor_allows_realtime_pace(self):
        """墙钟真过了 10 分钟的离线补报（游戏时间只推进 8.4 分钟）不应被拦。"""
        conn = _conn()
        start = base.parse_iso('2026-09-22T00:00:00Z')
        game = suika.load_state(conn, 7, seed=1, now=start)
        first = suika.sync_progress(conn, 7, game['game_uid'], 0,
                                    [{'t': i * 500, 'x': 300} for i in range(10)],
                                    claimed_score=10, claimed_max_tier=1,
                                    now=start + timedelta(seconds=30))
        self.assertTrue(first['verified'])
        second = suika.sync_progress(
            conn, 7, game['game_uid'], 10,
            [{'t': 5000 + i * 500, 'x': 310} for i in range(1000)],
            claimed_score=2010, claimed_max_tier=3,
            now=start + timedelta(minutes=10, seconds=30))
        self.assertTrue(second['verified'], second.get('reason'))
        self.assertEqual(second['game']['drop_index'], 1010)

    def test_total_drops_cap(self):
        conn = _conn()
        game = suika.load_state(conn, 7, seed=1)
        with mock.patch.object(suika, 'MAX_TOTAL_DROPS', 10):
            result = suika.sync_progress(conn, 7, game['game_uid'], 0,
                                         [{'t': i * 500, 'x': 300} for i in range(12)],
                                         claimed_score=12, claimed_max_tier=1)
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['reason'], '投放总数超出上限')
        self.assertEqual(result['game']['drop_index'], 0)

    def test_rules_migration_carries_score_in_same_game(self):
        """规则 v4 迁移：旧档只保留分数——同一云端局 from_index=0 重放新投放，
        分数从旧分继续累计，max_tier 只升不降（不被新盘面的 0 冲掉）。"""
        conn = _conn()
        game = suika.load_state(conn, 7, seed=1)
        suika.sync_progress(conn, 7, game['game_uid'], 0,
                            [{'t': i * 500, 'x': 300} for i in range(4)],
                            claimed_score=777, claimed_max_tier=6)
        # 迁移后第一批：from_index=0（替换投放序列）、分数沿用 777 起步
        result = suika.sync_progress(conn, 7, game['game_uid'], 0,
                                     [{'t': 600, 'x': 210}, {'t': 1400, 'x': 420}],
                                     claimed_score=777 + 9, claimed_max_tier=0)
        self.assertEqual(result['status'], 'ok')
        self.assertTrue(result['verified'])
        self.assertEqual(result['game']['game_uid'], game['game_uid'])  # 不换局
        self.assertEqual(result['game']['drop_index'], 2)               # 投放序列已重置
        self.assertEqual(result['game']['score'], 786)
        self.assertEqual(result['game']['max_tier'], 6)                 # 档位不被 0 冲掉

    def test_leaderboard_cached_matches_uncached(self):
        conn = _conn()
        game = suika.load_state(conn, 7, seed=1)
        suika.sync_progress(conn, 7, game['game_uid'], 0,
                            [{'t': 0, 'x': 300}], claimed_score=5, claimed_max_tier=1)
        base.invalidate_leaderboard_cache()
        cached = suika.leaderboard_cached(conn, window='all', limit=10)
        uncached = suika.leaderboard(conn, window='all', limit=10)
        self.assertEqual(cached['entries'], uncached['entries'])
        me = suika.self_entry_from_table(cached, 7)
        self.assertIsNotNone(me)
        self.assertEqual(me['score'], 5)


if __name__ == '__main__':
    unittest.main()
