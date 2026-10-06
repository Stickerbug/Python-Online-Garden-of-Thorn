# -*- coding: utf-8 -*-
"""#331：开发模式的旅程通关不发放荆露。"""

import os
import sys
import sqlite3
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from story_score import settle_story_clear_conn  # noqa: E402


def _mk_conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('''CREATE TABLE story_bank_accounts (
        user_id INTEGER PRIMARY KEY, deposit INTEGER NOT NULL DEFAULT 0)''')
    conn.execute('''CREATE TABLE story_runs (
        id TEXT PRIMARY KEY, manual_load_count INTEGER NOT NULL DEFAULT 0)''')
    conn.execute('''CREATE TABLE story_run_actions (
        run_id TEXT NOT NULL, sequence INTEGER NOT NULL,
        action_id TEXT NOT NULL, action_type TEXT NOT NULL,
        payload_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT '')''')
    conn.execute('''CREATE TABLE users (
        id INTEGER PRIMARY KEY, thorn_dew_free INTEGER NOT NULL DEFAULT 0,
        thorn_dew_paid INTEGER NOT NULL DEFAULT 0)''')
    conn.execute('''CREATE TABLE user_currency_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        currency TEXT NOT NULL, free_delta INTEGER NOT NULL DEFAULT 0,
        paid_delta INTEGER NOT NULL DEFAULT 0, reason TEXT NOT NULL DEFAULT '',
        source_type TEXT NOT NULL DEFAULT '', source_id TEXT NOT NULL DEFAULT '',
        balance_free_after INTEGER NOT NULL DEFAULT 0,
        balance_paid_after INTEGER NOT NULL DEFAULT 0,
        admin_username TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT '')''')
    return conn


def _completed_state():
    return {
        'completed': True,
        'stage': 3,
        'difficulty': 'normal',
        'normal_battles': 2,
        'player': {'gold': 100, 'deck': [1, 2, 3], 'relics': [1], 'enchantment_books': []},
    }


class StoryDevNoDewTest(unittest.TestCase):
    def test_normal_run_grants_dew(self):
        conn = _mk_conn()
        conn.execute("INSERT INTO users (id) VALUES (1)")
        conn.execute("INSERT INTO story_runs (id) VALUES ('r1')")
        result = settle_story_clear_conn(conn, user_id=1, run_id='r1', state=_completed_state())
        self.assertGreater(result['total'], 0)
        self.assertFalse(result['dev_used'])
        dew = conn.execute('SELECT thorn_dew_free FROM users WHERE id = 1').fetchone()['thorn_dew_free']
        self.assertEqual(dew, result['total'])
        tx = conn.execute(
            'SELECT reason FROM user_currency_transactions ORDER BY id DESC LIMIT 1'
        ).fetchone()
        # 反馈 #378：结算文案要显示难度全局乘数
        self.assertIn('难度normal×1', tx['reason'])
        ledger = conn.execute('SELECT * FROM story_reward_ledger').fetchone()
        self.assertEqual(ledger['dev_used'], 0)
        self.assertEqual(ledger['total_score'], result['total'])

    def test_dev_run_grants_no_dew(self):
        conn = _mk_conn()
        conn.execute("INSERT INTO users (id) VALUES (1)")
        conn.execute("INSERT INTO story_runs (id) VALUES ('r2')")
        conn.execute(
            "INSERT INTO story_run_actions (run_id, sequence, action_id, action_type) "
            "VALUES ('r2', 1, 'a1', 'dev_set_values')")
        conn.execute(
            "INSERT INTO story_run_actions (run_id, sequence, action_id, action_type) "
            "VALUES ('r2', 2, 'a2', 'enter_node')")
        result = settle_story_clear_conn(conn, user_id=1, run_id='r2', state=_completed_state())
        self.assertTrue(result['dev_used'])
        self.assertEqual(result['total'], 0)
        dew = conn.execute('SELECT thorn_dew_free FROM users WHERE id = 1').fetchone()['thorn_dew_free']
        self.assertEqual(dew, 0)
        txs = conn.execute('SELECT COUNT(*) AS n FROM user_currency_transactions').fetchone()['n']
        self.assertEqual(txs, 0)
        ledger = conn.execute('SELECT * FROM story_reward_ledger').fetchone()
        self.assertEqual(ledger['dev_used'], 1)
        self.assertEqual(ledger['total_score'], 0)
        self.assertGreater(ledger['base_score'], 0)

    def test_dev_prefix_not_matched_by_lookalike(self):
        conn = _mk_conn()
        conn.execute("INSERT INTO users (id) VALUES (1)")
        conn.execute("INSERT INTO story_runs (id) VALUES ('r3')")
        conn.execute(
            "INSERT INTO story_run_actions (run_id, sequence, action_id, action_type) "
            "VALUES ('r3', 1, 'a1', 'device_check')")
        result = settle_story_clear_conn(conn, user_id=1, run_id='r3', state=_completed_state())
        self.assertFalse(result['dev_used'])
        self.assertGreater(result['total'], 0)

    def test_legacy_ledger_alter_adds_column(self):
        conn = _mk_conn()
        conn.execute("INSERT INTO users (id) VALUES (1)")
        conn.execute("INSERT INTO story_runs (id) VALUES ('r4')")
        # 模拟旧库：先建无 dev_used 列的表
        conn.execute('''CREATE TABLE story_reward_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            run_id TEXT NOT NULL, difficulty TEXT NOT NULL,
            base_score INTEGER NOT NULL, total_score INTEGER NOT NULL,
            load_count INTEGER NOT NULL, bank_cleared INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')))''')
        result = settle_story_clear_conn(conn, user_id=1, run_id='r4', state=_completed_state())
        self.assertGreater(result['total'], 0)
        ledger = conn.execute('SELECT * FROM story_reward_ledger').fetchone()
        self.assertEqual(ledger['dev_used'], 0)


if __name__ == '__main__':
    unittest.main()
