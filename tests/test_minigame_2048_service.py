# -*- coding: utf-8 -*-
"""2048 服务层验收（用户用例 5、7、8、10–14）。

全部跑在**独立临时库**（``:memory:``）上，不碰真实账号、真实荆露。
"""

from __future__ import annotations

import sqlite3
import unittest

import minigame_2048 as g
import minigame_2048_service as svc


def make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            thorn_dew_free INTEGER NOT NULL DEFAULT 0,
            thorn_dew_paid INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE user_currency_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            currency TEXT NOT NULL,
            free_delta INTEGER NOT NULL DEFAULT 0,
            paid_delta INTEGER NOT NULL DEFAULT 0,
            reason TEXT,
            source_type TEXT,
            source_id TEXT,
            balance_free_after INTEGER NOT NULL DEFAULT 0,
            balance_paid_after INTEGER NOT NULL DEFAULT 0,
            admin_username TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    svc.ensure_schema(conn)
    for index in range(1, 6):
        conn.execute("INSERT INTO users (id, username) VALUES (?, ?)", (index, f"tester{index}"))
    conn.commit()
    return conn


def valid_ops(seed, count=6):
    """挑一组有效操作（跳过无效方向），保证前缀可重放。"""

    state = g.initial_state(seed)
    ops = []
    direction = 0
    guard = 0
    while len(ops) < count and guard < 200:
        guard += 1
        result = g.step(state, direction % 4)
        if result["changed"]:
            ops.append(g.DIRECTION_CHARS[direction % 4])
            state = {"seed": seed, "rng_state": result["rng_state"],
                     "cells": result["cells"], "score": result["score"]}
        direction += 1
    return "".join(ops)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.state = svc.create_game(self.conn, 1, seed=424242, now="2026-09-20T00:00:00Z")
        self.game = self.state["game"]
        self.ops = valid_ops(self.game["seed"], 6)
        self.assertTrue(self.ops)

    def test_first_batch_verifies_and_records_score(self):
        truth = g.replay(self.game["seed"], self.ops)
        result = svc.sync_progress(self.conn, 1, self.game["game_uid"], 0, self.ops,
                                   now="2026-09-20T01:00:00Z")
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["score"], truth["score"])
        self.assertEqual(result["cells"], truth["cells"])
        self.assertEqual(result["verified"]["score"], truth["score"])
        record = self.conn.execute("SELECT * FROM minigame_2048_records").fetchone()
        self.assertEqual(record["score"], truth["score"])
        self.assertEqual(record["verified_at"], "2026-09-20T01:00:00Z")

    def test_repeat_batch_is_idempotent(self):
        first = svc.sync_progress(self.conn, 1, self.game["game_uid"], 0, self.ops,
                                  now="2026-09-20T01:00:00Z")
        again = svc.sync_progress(self.conn, 1, self.game["game_uid"], 0, self.ops,
                                  now="2026-09-20T02:00:00Z")
        self.assertEqual(again["status"], "ok")
        self.assertEqual(again["applied"], 0)
        self.assertEqual(again["verified"]["score"], first["verified"]["score"])
        rows = self.conn.execute("SELECT * FROM minigame_2048_records").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["verified_at"], "2026-09-20T01:00:00Z")  # 没有刷新窗口

    def test_prefix_conflict_keeps_the_server_branch(self):
        svc.sync_progress(self.conn, 1, self.game["game_uid"], 0, self.ops,
                          now="2026-09-20T01:00:00Z")
        other = "r" if self.ops[0] != "r" else "l"
        conflict = svc.sync_progress(self.conn, 1, self.game["game_uid"], 0,
                                     other + self.ops[1:], now="2026-09-20T03:00:00Z")
        self.assertEqual(conflict["status"], "conflict")
        self.assertEqual(svc.load_state(self.conn, 1)["game"]["ops"], self.ops)

    def test_tampered_score_is_rejected_and_audited(self):
        truth = g.replay(self.game["seed"], self.ops)
        bad = svc.sync_progress(self.conn, 1, self.game["game_uid"], 0, self.ops,
                                claimed_score=truth["score"] + 1000,
                                now="2026-09-20T01:00:00Z")
        self.assertEqual(bad["status"], "rejected")
        self.assertEqual(svc.load_state(self.conn, 1)["game"]["op_index"], 0)
        audit = self.conn.execute("SELECT * FROM minigame_2048_audit").fetchone()
        self.assertEqual(audit["kind"], "verify_failed")

    def test_gap_and_stale_game_are_rejected(self):
        gap = svc.sync_progress(self.conn, 1, self.game["game_uid"], 5, self.ops,
                                now="2026-09-20T01:00:00Z")
        self.assertEqual(gap["status"], "gap")
        stale = svc.sync_progress(self.conn, 1, "old-game-uid", 0, self.ops)
        self.assertEqual(stale["status"], "stale_game")

    def test_restart_keeps_old_records_and_rejects_late_requests(self):
        svc.sync_progress(self.conn, 1, self.game["game_uid"], 0, self.ops,
                          now="2026-09-20T01:00:00Z")
        before = self.conn.execute("SELECT COUNT(*) AS n FROM minigame_2048_records").fetchone()["n"]
        svc.restart_game(self.conn, 1, seed=999, now="2026-09-20T05:00:00Z")
        after = self.conn.execute("SELECT COUNT(*) AS n FROM minigame_2048_records").fetchone()["n"]
        self.assertEqual(before, after)
        old = self.conn.execute("SELECT * FROM minigame_2048_games WHERE game_uid = ?",
                                (self.game["game_uid"],)).fetchone()
        self.assertEqual(old["status"], "closed")
        self.assertEqual(old["ops"], self.ops)
        late = svc.sync_progress(self.conn, 1, self.game["game_uid"], len(self.ops), "l")
        self.assertEqual(late["status"], "stale_game")

    def test_prefs_round_trip(self):
        self.assertEqual(svc.get_prefs(self.conn, 1),
                         {"decline_invites": False, "show_numbers": False})
        svc.set_prefs(self.conn, 1, decline_invites=True, show_numbers=True)
        self.assertTrue(svc.prefs_decline_invites(self.conn, 1))
        self.assertTrue(svc.get_prefs(self.conn, 1)["show_numbers"])

    def test_offline_started_game_is_adopted_and_verified(self):
        """离线自开的局：带种子+完整操作补传，服务端从起点重放后才入库。"""

        client_seed = 777001
        ops = valid_ops(client_seed, 5)
        truth = g.replay(client_seed, ops)
        result = svc.sync_progress(
            self.conn, 1, "local-777001", 0, ops,
            claimed_score=truth["score"], claimed_cells=truth["cells"],
            source="offline", new_game=True, seed=client_seed,
            now="2026-09-20T09:00:00Z",
        )
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["score"], truth["score"])
        game = svc.load_state(self.conn, 1)["game"]
        self.assertEqual(game["game_uid"], "local-777001")
        self.assertEqual(game["source"], "offline")
        record = self.conn.execute("SELECT * FROM minigame_2048_records").fetchone()
        self.assertEqual(record["source"], "offline")
        self.assertEqual(record["score"], truth["score"])
        kinds = {row["kind"] for row in self.conn.execute("SELECT * FROM minigame_2048_audit")}
        self.assertIn("adopt_client_game", kinds)

    def test_offline_adopt_rejects_tampered_score(self):
        client_seed = 555111
        ops = valid_ops(client_seed, 4)
        truth = g.replay(client_seed, ops)
        bad = svc.sync_progress(
            self.conn, 2, "local-555111", 0, ops,
            claimed_score=truth["score"] + 999, source="offline",
            new_game=True, seed=client_seed, now="2026-09-20T09:05:00Z",
        )
        self.assertEqual(bad["status"], "rejected")
        self.assertEqual(svc.load_state(self.conn, 2)["game"]["op_index"], 0)


class LeaderboardTests(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()

    def _record(self, user_id, score, max_tile, verified_at, game_id=None, op_index=10):
        self.conn.execute(
            """INSERT INTO minigame_2048_records
               (user_id, game_id, score, max_tile, op_index, rules_version, verified_at, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'online', ?)""",
            (user_id, game_id or (1000 + user_id), score, max_tile, op_index,
             g.RULES_VERSION, verified_at, verified_at),
        )
        self.conn.commit()

    def test_rolling_window_excludes_old_and_history_keeps_it(self):
        now = "2026-10-01T00:00:00Z"
        self._record(1, 50000, 4096, "2026-09-01T00:00:00Z")   # 30 天前
        self._record(2, 1000, 256, "2026-09-25T00:00:00Z")     # 窗口内
        rolling = svc.leaderboard(self.conn, window="14d", now=now)
        self.assertEqual([item["user_id"] for item in rolling["entries"]], [2])
        history = svc.leaderboard(self.conn, window="all", now=now)
        self.assertEqual([item["user_id"] for item in history["entries"]], [1, 2])

    def test_one_row_per_account_keeps_the_best(self):
        now = "2026-10-01T00:00:00Z"
        self._record(1, 100, 128, "2026-09-25T00:00:00Z", game_id=11)
        self._record(1, 900, 512, "2026-09-26T00:00:00Z", game_id=12)
        table = svc.leaderboard(self.conn, window="14d", now=now)
        self.assertEqual(len(table["entries"]), 1)
        self.assertEqual(table["entries"][0]["score"], 900)

    def test_ties_share_rank_and_max_tile_breaks_it(self):
        now = "2026-10-01T00:00:00Z"
        self._record(1, 500, 256, "2026-09-25T00:00:00Z")
        self._record(2, 500, 256, "2026-09-25T02:00:00Z")
        self._record(3, 500, 512, "2026-09-25T03:00:00Z")
        table = svc.leaderboard(self.conn, window="14d", now=now)
        ranks = {item["user_id"]: item["rank"] for item in table["entries"]}
        self.assertEqual(ranks[3], 1)
        self.assertEqual(ranks[1], 2)
        self.assertEqual(ranks[2], 2)

    def test_self_entry_visible_outside_the_top_list(self):
        now = "2026-10-01T00:00:00Z"
        for index in range(1, 6):
            self._record(index, 100 + index, 128, "2026-09-25T00:00:00Z")
        entry = svc.self_entry(self.conn, 5, window="14d", now=now)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["score"], 105)


class SettlementTests(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()

    def _record(self, user_id, score, max_tile, verified_at):
        self.conn.execute(
            """INSERT INTO minigame_2048_records
               (user_id, game_id, score, max_tile, op_index, rules_version, verified_at, source, created_at)
               VALUES (?, ?, ?, ?, 5, ?, ?, 'online', ?)""",
            (user_id, 500 + user_id, score, max_tile, g.RULES_VERSION, verified_at, verified_at),
        )
        self.conn.commit()

    def test_cutoffs_are_monday_midnight_utc8_and_catch_up(self):
        cutoffs = svc.week_cutoffs("2026-10-05T00:00:00+08:00")
        self.assertEqual([item.strftime("%Y-%m-%d") for item in cutoffs],
                         ["2026-09-21", "2026-09-28", "2026-10-05"])
        self.assertEqual(svc.week_cutoffs("2026-09-20T00:00:00+08:00"), [])

    def test_three_accounts_split_the_pool(self):
        for user_id in (1, 2, 3):
            self._record(user_id, 1000 * user_id, 256 * user_id, "2026-09-25T00:00:00Z")
        results = svc.settle_due(self.conn, now="2026-10-01T00:00:00+08:00")
        # 09-21 那期窗口内还没有成绩 → skipped；09-28 那期发了奖
        self.assertEqual([item["status"] for item in results], ["skipped", "paid"])
        rows = self.conn.execute("SELECT * FROM minigame_2048_periods").fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["status"], "paid")
        self.assertEqual(int(rows[1]["participants"]), 3)
        ledger = self.conn.execute(
            "SELECT SUM(free_delta) AS total FROM user_currency_transactions").fetchone()["total"]
        self.assertEqual(int(ledger), svc.CHAMPION_POOL)

    def test_ties_share_the_pool_exactly(self):
        for user_id in (2, 3, 4):
            self._record(user_id, 777, 256, "2026-09-25T00:00:00Z")
        svc.settle_due(self.conn, now="2026-10-01T00:00:00+08:00")
        rewards = self.conn.execute("SELECT * FROM minigame_2048_rewards").fetchall()
        self.assertEqual(len(rewards), 3)
        self.assertEqual(sum(int(row["amount"]) for row in rewards), svc.CHAMPION_POOL)
        self.assertEqual(sorted(int(row["amount"]) for row in rewards), [100, 100, 100])

    def test_settlement_is_idempotent_and_late_uploads_do_not_rewrite_it(self):
        for user_id in (1, 2, 3):
            self._record(user_id, 1000 * user_id, 256 * user_id, "2026-09-25T00:00:00Z")
        svc.settle_due(self.conn, now="2026-10-01T00:00:00+08:00")
        snapshot = self.conn.execute("SELECT * FROM minigame_2048_periods").fetchone()
        balances = {row["id"]: int(row["thorn_dew_free"])
                    for row in self.conn.execute("SELECT * FROM users").fetchall()}
        second = svc.settle_due(self.conn, now="2026-10-01T00:00:00+08:00")
        self.assertEqual(second[0]["credited"], 0)
        self._record(4, 999999, 8192, "2026-09-29T00:00:00Z")
        svc.settle_due(self.conn, now="2026-10-01T00:00:00+08:00")
        after = self.conn.execute("SELECT * FROM minigame_2048_periods").fetchone()
        self.assertEqual(after["winners_json"], snapshot["winners_json"])
        self.assertEqual(int(after["participants"]), int(snapshot["participants"]))
        self.assertEqual({row["id"]: int(row["thorn_dew_free"])
                          for row in self.conn.execute("SELECT * FROM users").fetchall()},
                         balances)

    def test_two_accounts_are_not_enough(self):
        for user_id in (1, 2):
            self._record(user_id, 500, 256, "2026-09-25T00:00:00Z")
        svc.settle_due(self.conn, now="2026-10-01T00:00:00+08:00")
        period = self.conn.execute(
            "SELECT * FROM minigame_2048_periods ORDER BY cutoff_at DESC LIMIT 1").fetchone()
        self.assertEqual(period["status"], "skipped")
        self.assertIn("不足", period["reason"] or "")
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) AS n FROM minigame_2048_rewards").fetchone()["n"], 0)

    def test_old_verified_scores_can_win_again_next_week(self):
        for user_id in (1, 2, 3):
            self._record(user_id, 100 * user_id, 128 * user_id, "2026-09-25T00:00:00Z")
        svc.settle_due(self.conn, now="2026-10-01T00:00:00+08:00")
        results = svc.settle_due(self.conn, now="2026-10-06T00:00:00+08:00")
        periods = self.conn.execute("SELECT * FROM minigame_2048_periods ORDER BY cutoff_at").fetchall()
        # 09-21 skipped、09-28 paid、10-05 paid（同一批旧成绩仍在 14 天窗口内）
        self.assertEqual([row["period_key"] for row in periods],
                         ["2048-2026-09-21", "2048-2026-09-28", "2048-2026-10-05"])
        self.assertEqual([row["status"] for row in periods], ["skipped", "paid", "paid"])
        self.assertEqual(results[-1]["status"], "paid")


if __name__ == "__main__":
    unittest.main()
