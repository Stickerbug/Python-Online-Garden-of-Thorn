"""Performance guards added 2026-09-11 (chat history index + slow-log threshold)."""

import contextlib
import gc
import io
import json
import os
import pathlib
import shutil
import tempfile
import unittest

import db


ROOT = pathlib.Path(__file__).resolve().parents[1]


class ChatHistoryIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'perf.sqlite3')
        db.init_db()
        self.user, error = db.create_user('PerfUser', 'Aa1!aaaa')
        self.assertIsNone(error)

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def test_recent_room_messages_use_the_room_id_index(self):
        # 「按房间取最近 N 条」必须走 (room_id, id DESC)，不能退化成
        # 「读整个房间的消息 + USE TEMP B-TREE FOR ORDER BY」。
        for index in range(40):
            db.record_chat_message(
                f'lobby:release', 'public', self.user['id'], self.user['username'],
                f'message {index}',
            )

        with db.get_db_connection() as conn:
            plan = conn.execute(
                '''
                EXPLAIN QUERY PLAN
                SELECT * FROM chat_messages
                WHERE room_id = ? AND hidden = 0
                ORDER BY id DESC
                LIMIT 20
                ''',
                ('lobby:release',),
            ).fetchall()
        details = ' '.join(str(row['detail']) for row in plan)
        self.assertIn('idx_chat_messages_room_id', details)
        self.assertNotIn('TEMP B-TREE', details)

    def test_slow_log_threshold_defaults_to_250ms_and_is_configurable(self):
        self.assertEqual(db.DB_SLOW_THRESHOLD_MS, 250)
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            db.db_slow_log('endpoint=x', 100, 'tag')
            db.db_slow_log('endpoint=y', 300, 'tag')
        output = stream.getvalue()
        self.assertNotIn('endpoint=x', output)
        self.assertIn('endpoint=y', output)


class WalKeeperConnectionTests(unittest.TestCase):
    """保持一条空闲连接，避免每请求关连接时触发 WAL checkpoint。"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'wal.sqlite3')
        db.init_db()

    def tearDown(self):
        db.release_wal_keeper()
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def test_keeper_is_reused_and_released(self):
        first = db.hold_wal_open()
        self.assertIsNotNone(first)
        self.assertIs(first, db.hold_wal_open())
        db.release_wal_keeper()
        self.assertIsNone(db._WAL_KEEPER_CONN)
        second = db.hold_wal_open()
        self.assertIsNot(first, second)

    def test_keeper_reopens_when_the_database_path_changes(self):
        first = db.hold_wal_open()
        other_dir = tempfile.mkdtemp()
        try:
            db.DB_PATH = os.path.join(other_dir, 'other.sqlite3')
            db.init_db()
            second = db.hold_wal_open()
            self.assertIsNot(first, second)
            # 先关掉 keeper，否则 Windows 上临时目录删不掉。
            db.release_wal_keeper()
        finally:
            # init_db 内部的 with-connection 依赖 GC 关闭，Windows 上先 gc 再删。
            gc.collect()
            shutil.rmtree(other_dir, ignore_errors=True)

    def test_app_startup_holds_the_wal_open(self):
        source = (ROOT / 'app.py').read_text(encoding='utf-8')
        self.assertIn('hold_wal_open()', source)
        self.assertIn('WAL keeper connection failed', source)


class HandlingSearchIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'handling.sqlite3')
        db.init_db()
        self.alice, error = db.create_user('HandlingAlice', 'Aa1!aaaa')
        self.assertIsNone(error)
        self.bob, error = db.create_user('HandlingBob', 'Aa1!aaaa')
        self.assertIsNone(error)

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def _save_match(self):
        return db.save_match_summary({
            'mode': '1v1',
            'started_at': '2026-09-11T00:00:00Z',
            'ended_at': '2026-09-11T00:05:00Z',
            'duration_seconds': 300,
            'players': [self.alice['username'], self.bob['username']],
            'player_ids': [self.alice['id'], self.bob['id']],
            'winner_name': self.alice['username'],
            'winner_index': 0,
            'rounds': 5,
            'mod_source': 'official',
            'mod_hash': 'hash',
            'result': 'win',
            'match_type': 'ranked',
            'valid_for_ranking': True,
        })

    def test_exact_username_search_uses_the_participants_join(self):
        match_id = self._save_match()
        result = db.search_handling_matches(self.alice['username'])
        self.assertEqual(result['total'], 1, result)
        self.assertEqual([item['id'] for item in result['items']], [match_id])

    def test_partial_name_search_keeps_the_like_fallback(self):
        match_id = self._save_match()
        result = db.search_handling_matches('HandlingA')
        self.assertEqual(result['total'], 1, result)
        self.assertEqual([item['id'] for item in result['items']], [match_id])

    def test_unknown_token_returns_empty_without_error(self):
        self._save_match()
        result = db.search_handling_matches('zzz-no-such-player')
        self.assertEqual(result['total'], 0, result)


if __name__ == '__main__':
    unittest.main()
