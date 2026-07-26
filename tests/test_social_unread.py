import gc
import os
import tempfile
import unittest

import db


class SocialUnreadTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'social.sqlite3')
        db.init_db()
        self.alice, error = db.create_user('SocialAlice', 'Aa1!aaaa')
        self.assertIsNone(error)
        self.bob, error = db.create_user('SocialBob', 'Aa1!aaaa')
        self.assertIsNone(error)

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def unread(self, user):
        counts, error = db.social_unread_counts(user['id'])
        self.assertIsNone(error)
        return counts

    def request_and_accept(self):
        _, error = db.add_friend_request(self.alice['id'], self.bob['username'])
        self.assertIsNone(error)
        bob_friends, error = db.list_friends(self.bob['id'])
        self.assertIsNone(error)
        request = next(item for item in bob_friends['incoming'] if item['status'] == 'pending')
        _, error = db.respond_friend_request(self.bob['id'], request['request_id'], 'accept')
        self.assertIsNone(error)

    def test_friend_request_and_acceptance_have_separate_unread_notices(self):
        _, error = db.add_friend_request(self.alice['id'], self.bob['username'])
        self.assertIsNone(error)
        self.assertEqual(self.unread(self.alice)['friend_unread_count'], 0)
        self.assertEqual(self.unread(self.bob)['friend_unread_count'], 1)

        bob_friends, error = db.list_friends(self.bob['id'])
        self.assertIsNone(error)
        request = next(item for item in bob_friends['incoming'] if item['status'] == 'pending')
        _, error = db.respond_friend_request(self.bob['id'], request['request_id'], 'accept')
        self.assertIsNone(error)

        self.assertEqual(self.unread(self.bob)['friend_unread_count'], 0)
        self.assertEqual(self.unread(self.alice)['friend_unread_count'], 1)
        alice_friends, error = db.list_friends(self.alice['id'])
        self.assertIsNone(error)
        accepted_notices = [
            item for item in alice_friends['incoming']
            if item['status'] == 'notice' and item['notice_type'] == 'accepted'
        ]
        self.assertEqual(len(accepted_notices), 1)

        marked, error = db.mark_friend_notifications_read_for_user(self.alice['id'])
        self.assertTrue(marked)
        self.assertIsNone(error)
        self.assertEqual(self.unread(self.alice)['friend_unread_count'], 0)
        alice_friends, error = db.list_friends(self.alice['id'])
        self.assertIsNone(error)
        self.assertFalse(any(item.get('notice_type') == 'accepted' for item in alice_friends['incoming']))

    def test_social_summary_combines_friend_and_dm_unread(self):
        self.request_and_accept()
        db.mark_friend_notifications_read_for_user(self.alice['id'])

        sent, error = db.send_dm_message(
            self.alice['id'],
            target_user_id=self.bob['id'],
            message='hello',
        )
        self.assertIsNone(error)
        self.assertIsNotNone(sent)
        counts = self.unread(self.bob)
        self.assertEqual(counts['friend_unread_count'], 0)
        self.assertEqual(counts['dm_unread_count'], 1)

        thread_id = sent['thread_id']
        _, error = db.get_dm_messages(self.bob['id'], thread_id, mark_read=True)
        self.assertIsNone(error)
        self.assertEqual(self.unread(self.bob)['dm_unread_count'], 0)

    def test_migration_does_not_turn_existing_friendships_into_new_notices(self):
        now = db.utc_now()
        with db.get_db_connection() as conn:
            conn.execute('DROP TABLE friendships')
            conn.execute(
                '''
                CREATE TABLE friendships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    requester_id INTEGER NOT NULL,
                    addressee_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    addressee_read_at TEXT,
                    notice_type TEXT DEFAULT 'request',
                    UNIQUE(requester_id, addressee_id)
                )
                '''
            )
            conn.execute(
                '''
                INSERT INTO friendships (
                    requester_id, addressee_id, status, created_at, updated_at,
                    addressee_read_at, notice_type
                ) VALUES (?, ?, 'accepted', ?, ?, ?, 'request')
                ''',
                (self.alice['id'], self.bob['id'], now, now, now),
            )
            conn.commit()

        db.init_db()
        with db.get_db_connection() as conn:
            columns = {row['name'] for row in conn.execute('PRAGMA table_info(friendships)').fetchall()}
            row = conn.execute('SELECT requester_read_at FROM friendships').fetchone()
        self.assertIn('requester_read_at', columns)
        self.assertTrue(row['requester_read_at'])
        self.assertEqual(self.unread(self.alice)['friend_unread_count'], 0)


if __name__ == '__main__':
    unittest.main()
