# -*- coding: utf-8 -*-
"""游戏结束直接奖励（设计 2026-10-09）：2048=floor(分数/50)，suika=floor(分数/10)。

覆盖：结算金额与账本、每局只发一次的幂等、重开后新一局可再发、
suika 未结束时上报不发。全部跑在独立临时库上，不碰真实荆露。
"""

from __future__ import annotations

import random
import sqlite3
import unittest

import minigame_2048 as g
import minigame_2048_service as svc
import minigame_suika_service as suika


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
    suika.ensure_schema(conn)
    conn.execute("INSERT INTO users (id, username) VALUES (1, 'tester1')")
    conn.commit()
    return conn


def dew_free(conn, user_id=1) -> int:
    row = conn.execute("SELECT thorn_dew_free FROM users WHERE id = ?", (user_id,)).fetchone()
    return int(row["thorn_dew_free"])


def play_2048_to_game_over(seed, limit=6000):
    """本地随机玩到终局，返回 (操作序列, 终局分数)。"""

    state = g.initial_state(seed)
    rng = random.Random(seed)
    ops = []
    for _ in range(limit):
        if g.is_game_over(state["cells"]):
            break
        moved = False
        for direction in rng.sample(range(4), 4):
            result = g.step(state, direction)
            if result["changed"]:
                ops.append(direction)
                state = result
                moved = True
                break
        if not moved:
            break
    assert g.is_game_over(state["cells"]), "随机对局应在有限步内结束"
    return ops, int(state["score"])


class GameOverDew2048Tests(unittest.TestCase):
    def test_game_over_awards_score_div_50_once(self):
        conn = make_conn()
        state = svc.load_state(conn, 1)["game"]
        ops, final_score = play_2048_to_game_over(state["seed"])
        self.assertGreater(final_score, 0)

        result = svc.sync_progress(
            conn, 1, state["game_uid"], 0, ops,
            claimed_score=final_score,
        )
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["game_over"])
        expected = final_score // svc.GAME_OVER_DEW_DIVISOR
        self.assertEqual(expected, final_score // 50)
        self.assertEqual(result["dew_awarded"], expected)
        self.assertEqual(dew_free(conn), expected)

        ledger = conn.execute(
            "SELECT * FROM user_currency_transactions WHERE source_type = 'minigame_2048_gameover'"
        ).fetchall()
        self.assertEqual(len(ledger), 1)
        self.assertEqual(int(ledger[0]["free_delta"]), expected)

        # 重复同步同一局（服务端已终局、无新操作）：不再发。
        again = svc.sync_progress(
            conn, 1, state["game_uid"], result["op_index"], [],
            claimed_score=final_score,
        )
        self.assertEqual(again["status"], "ok")
        self.assertTrue(again["game_over"])
        self.assertEqual(again["dew_awarded"], 0)
        self.assertEqual(dew_free(conn), expected)

    def test_new_game_after_restart_can_award_again(self):
        conn = make_conn()
        first = svc.load_state(conn, 1)["game"]
        ops, score = play_2048_to_game_over(first["seed"])
        r1 = svc.sync_progress(conn, 1, first["game_uid"], 0, ops, claimed_score=score)
        self.assertEqual(r1["dew_awarded"], score // 50)

        restarted = svc.restart_game(conn, 1)["game"]
        self.assertNotEqual(str(restarted["game_uid"]), str(first["game_uid"]))
        ops2, score2 = play_2048_to_game_over(restarted["seed"])
        r2 = svc.sync_progress(conn, 1, restarted["game_uid"], 0, ops2, claimed_score=score2)
        self.assertEqual(r2["dew_awarded"], score2 // 50)
        self.assertEqual(dew_free(conn), score // 50 + score2 // 50)


class GameOverDewSuikaTests(unittest.TestCase):
    def _drops(self, count, step_ms=1000.0):
        return [{"t": float(i * step_ms), "x": 0.5} for i in range(count)]

    def test_game_over_awards_score_div_10_once(self):
        conn = make_conn()
        state = suika.load_state(conn, 1)
        result = suika.sync_progress(
            conn, 1, state["game_uid"], 0, self._drops(5),
            claimed_score=1234, claimed_max_tier=3, game_over=True,
        )
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["verified"])
        self.assertEqual(result["dew_awarded"], 123)
        self.assertEqual(dew_free(conn), 123)

        # 重复上报结束标记：同一局只发一次。
        again = suika.sync_progress(
            conn, 1, state["game_uid"], 5, [],
            claimed_score=1234, claimed_max_tier=3, game_over=True,
        )
        self.assertEqual(again["status"], "ok")
        self.assertEqual(again["dew_awarded"], 0)
        self.assertEqual(dew_free(conn), 123)

        # 账本
        ledger = conn.execute(
            "SELECT * FROM user_currency_transactions WHERE source_type = 'minigame_suika_gameover'"
        ).fetchall()
        self.assertEqual(len(ledger), 1)
        self.assertEqual(int(ledger[0]["free_delta"]), 123)

    def test_no_game_over_flag_no_award(self):
        conn = make_conn()
        state = suika.load_state(conn, 1)
        result = suika.sync_progress(
            conn, 1, state["game_uid"], 0, self._drops(3),
            claimed_score=500, claimed_max_tier=2, game_over=False,
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["dew_awarded"], 0)
        self.assertEqual(dew_free(conn), 0)

    def test_restart_new_game_awards_again(self):
        conn = make_conn()
        first = suika.load_state(conn, 1)
        r1 = suika.sync_progress(
            conn, 1, first["game_uid"], 0, self._drops(4),
            claimed_score=800, claimed_max_tier=3, game_over=True,
        )
        self.assertEqual(r1["dew_awarded"], 80)
        restarted = suika.restart_game(conn, 1)
        r2 = suika.sync_progress(
            conn, 1, restarted["game_uid"], 0, self._drops(4),
            claimed_score=300, claimed_max_tier=2, game_over=True,
        )
        self.assertEqual(r2["dew_awarded"], 30)
        self.assertEqual(dew_free(conn), 110)


class PlayerHistoryTests(unittest.TestCase):
    def test_history_merges_both_games(self):
        conn = make_conn()
        ce = svc.load_state(conn, 1)["game"]
        svc.sync_progress(conn, 1, ce["game_uid"], 0, [], claimed_score=0)
        sk = suika.load_state(conn, 1)
        suika.sync_progress(
            conn, 1, sk["game_uid"], 0, [{"t": float(i * 1000), "x": 0.5} for i in range(4)],
            claimed_score=987, claimed_max_tier=4, game_over=True,
        )
        history = svc.player_history(conn, 1, limit=10)
        kinds = {item["game"] for item in history}
        self.assertEqual(kinds, {"2048", "suika"})
        by_game = {item["game"]: item for item in history}
        self.assertEqual(by_game["suika"]["score"], 987)
        self.assertEqual(by_game["suika"]["best_kind"], "tier")
        self.assertEqual(by_game["suika"]["dew"], 98)
        self.assertEqual(by_game["2048"]["best_kind"], "tile")
        self.assertEqual(by_game["2048"]["status"], "active")
        # 无记录账号返回空列表
        self.assertEqual(svc.player_history(conn, 999, limit=10), [])


if __name__ == "__main__":
    unittest.main()
