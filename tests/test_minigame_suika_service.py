# -*- coding: utf-8 -*-
"""合成大花花服务层：立刻落库 + 启发式校验 + 榜单分账（内存库，不碰真实数据）。"""

from __future__ import annotations

import sqlite3
import unittest

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


if __name__ == '__main__':
    unittest.main()
