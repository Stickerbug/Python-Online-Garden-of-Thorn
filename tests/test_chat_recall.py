"""管理员撤回聊天：软删除 + 广播占位（反馈：要能撤回所有人的消息）。"""

import gc
import os
import tempfile
import unittest

import db


class ChatRecallTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'recall.sqlite3')
        db.init_db()
        self.message_id = db.record_chat_message(
            'lobby:release', 'public', None, 'TestUser', '傻逼', '{}', 3,
        )

    def tearDown(self):
        db.release_wal_keeper()
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def test_recall_hides_message_and_returns_scope(self):
        entries = db.list_lobby_chat_entries(beta_mode=False, limit=10)
        self.assertTrue(any(int(entry['id']) == self.message_id for entry in entries))

        info = db.recall_chat_message(self.message_id, actor_user_id=2, actor_name='Eric')
        self.assertIsNotNone(info)
        self.assertEqual(info['message_id'], self.message_id)
        self.assertEqual(info['room_id'], 'lobby:release')
        self.assertEqual(info['sender_name'], 'TestUser')

        entries = db.list_lobby_chat_entries(beta_mode=False, limit=10)
        self.assertFalse(any(int(entry['id']) == self.message_id for entry in entries))
        self.assertIsNone(db.recall_chat_message(999999))

    def test_batch_recall_by_sender(self):
        for _ in range(3):
            db.record_chat_message('lobby:release', 'public', None, 'Spammer', 'spam', '{}', 0)
        ids = db.recall_chat_messages_from_sender('Spammer', limit=10)
        self.assertEqual(len(ids), 3)
        for message_id in ids:
            self.assertIsNotNone(db.recall_chat_message(message_id, actor_name='Eric'))
        self.assertEqual(db.recall_chat_messages_from_sender('Spammer', limit=10), [])

    def test_broadcast_chat_recall_reports_count(self):
        import app

        total = app.broadcast_chat_recall('Eric', [{
            'room_id': 'lobby:release',
            'sender_name': 'TestUser',
            'message_ids': [self.message_id],
        }])
        self.assertEqual(total, 1)


if __name__ == '__main__':
    unittest.main()
