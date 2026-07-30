import gc
import os
import tempfile
import unittest
from contextlib import closing

import db


class UserIpEventTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'ip-events.sqlite3')
        db.init_db()
        self.user, error = db.create_user('IpEventUser', 'Aa1!aaaa')
        self.assertIsNone(error)

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def event_rows(self):
        with closing(db.get_db_connection()) as conn:
            return conn.execute(
                '''
                SELECT user_id, username, ip, source
                FROM user_ip_events
                ORDER BY id
                '''
            ).fetchall()

    def test_game_entry_source_is_recorded(self):
        recorded = db.record_user_ip_event(
            self.user['id'],
            self.user['username'],
            '203.0.113.8',
            source='game_enter',
            dedupe_seconds=60,
        )

        self.assertTrue(recorded)
        rows = self.event_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['user_id'], self.user['id'])
        self.assertEqual(rows[0]['username'], self.user['username'])
        self.assertEqual(rows[0]['ip'], '203.0.113.8')
        self.assertEqual(rows[0]['source'], 'game_enter')

    def test_duplicate_game_entry_is_suppressed_inside_window(self):
        for _ in range(2):
            self.assertTrue(db.record_user_ip_event(
                self.user['id'],
                self.user['username'],
                '203.0.113.8',
                source='game_enter',
                dedupe_seconds=60,
            ))

        self.assertEqual(len(self.event_rows()), 1)

    def test_different_sources_are_kept(self):
        self.assertTrue(db.record_user_ip_event(
            self.user['id'],
            self.user['username'],
            '203.0.113.8',
            source='login',
            dedupe_seconds=60,
        ))
        self.assertTrue(db.record_user_ip_event(
            self.user['id'],
            self.user['username'],
            '203.0.113.8',
            source='game_enter',
            dedupe_seconds=60,
        ))

        self.assertEqual(
            [row['source'] for row in self.event_rows()],
            ['login', 'game_enter'],
        )


if __name__ == '__main__':
    unittest.main()
