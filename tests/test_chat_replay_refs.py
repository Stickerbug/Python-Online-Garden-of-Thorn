# -*- coding: utf-8 -*-
"""聊天对局编号校验：存在/前缀/30天窗口/pending 语义。"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@unittest.skipIf(os.environ.get('GTN_TEST_SKIP_APP'), 'app import skipped')
class ChatReplayRefTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import db
        import app as gtn
        cls.db = db
        cls.gtn = gtn
        cls.old_path = db.DB_PATH
        cls.tmp = tempfile.TemporaryDirectory()
        db.DB_PATH = os.path.join(cls.tmp.name, 't.sqlite3')
        db.init_db()

    @classmethod
    def tearDownClass(cls):
        cls.db.release_wal_keeper()
        cls.db.DB_PATH = cls.old_path
        import gc
        gc.collect()
        try:
            cls.tmp.cleanup()
        except OSError:
            pass  # Windows 下 WAL 句柄偶尔迟放

    def _insert_replay(self, replay_id, prefix='R', days_ago=0):
        created = (datetime.now(timezone.utc) - timedelta(days=days_ago)) \
            .strftime('%Y-%m-%dT%H:%M:%SZ')
        with self.db.get_db_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO match_replays"
                " (id, match_id, created_at, mode, player_names_json, replay_version,"
                "  replay_sha256, replay_size, replay_prefix, replay_blob)"
                " VALUES (?, ?, ?, '1v1', '[]', 2, ?, 1, ?, x'00')",
                (replay_id, replay_id, created, 'x' * 64, prefix),
            )
            conn.commit()

    def test_valid_recent_ref(self):
        self._insert_replay(12345, 'R', days_ago=1)
        result = self.gtn.validate_chat_replay_refs(['R-12345'])
        self.assertEqual(result, {'R-12345': True})

    def test_nonexistent_ref(self):
        result = self.gtn.validate_chat_replay_refs(['R-99999'])
        self.assertEqual(result, {'R-99999': False})

    def test_wrong_prefix_rejected(self):
        self._insert_replay(22222, 'P', days_ago=0)
        result = self.gtn.validate_chat_replay_refs(['R-22222'])
        self.assertEqual(result, {'R-22222': False})

    def test_expired_ref_rejected(self):
        self._insert_replay(33333, 'R', days_ago=31)
        result = self.gtn.validate_chat_replay_refs(['R-33333'])
        self.assertEqual(result, {'R-33333': False})

    def test_boundary_29_days_accepted(self):
        self._insert_replay(44444, 'R', days_ago=29)
        result = self.gtn.validate_chat_replay_refs(['R-44444'])
        self.assertEqual(result, {'R-44444': True})

    def test_attach_pending_and_valid(self):
        self._insert_replay(12345, 'R', days_ago=1)
        chat_data = {}
        self.gtn.attach_chat_replay_refs(chat_data, '看这局 R-12345 和未来的 R-88888')
        self.assertEqual(chat_data['replay_refs']['v'], ['R-12345'])
        self.assertEqual(chat_data['replay_refs']['p'], ['R-88888'])

    def test_attach_no_refs_untouched(self):
        chat_data = {'text': '普通消息'}
        self.gtn.attach_chat_replay_refs(chat_data, '普通消息')
        self.assertNotIn('replay_refs', chat_data)

    def test_pattern_matches_client_shape(self):
        text = 'RP-12345 XR-12345 R-12345 P-54321 R-123456'
        found = self.gtn.CHAT_REPLAY_REF_PATTERN.findall(text)
        self.assertEqual(found, ['R-12345', 'P-54321'])


if __name__ == '__main__':
    unittest.main()
