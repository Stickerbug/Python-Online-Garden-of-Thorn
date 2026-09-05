import os
import gc
import tempfile
import unittest

import app
import db
import public_feedback as feedback


class PublicFeedbackConsoleCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        self.old_db_available = app.DB_AVAILABLE
        db.DB_PATH = os.path.join(self.temp_dir.name, 'public-feedback.sqlite3')
        db.init_db()
        app.DB_AVAILABLE = True
        self.user1, error = db.create_user('FeedbackUserA', 'Aa1!aaaa')
        self.assertIsNone(error)
        self.user2, error = db.create_user('FeedbackUserB', 'Bb2!bbbb')
        self.assertIsNone(error)
        self.issue = feedback.create_public_issue(
            self.user1['id'],
            kind='bug',
            title='控制台测试漏洞',
            body='详细正文',
        )

    def tearDown(self):
        app.DB_AVAILABLE = self.old_db_available
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def run_command(self, line):
        return app.execute_admin_command(line, actor='test-console')

    def test_list_get_status_priority_note_and_hide(self):
        listed = self.run_command('publicfeedback list bug')
        self.assertTrue(listed['success'], listed['output'])
        self.assertIn('控制台测试漏洞', listed['output'])

        detail = self.run_command(f'publicfeedback get {self.issue["id"]}')
        self.assertTrue(detail['success'], detail['output'])
        self.assertIn('详细正文', detail['output'])

        status = self.run_command(f'publicfeedback status {self.issue["id"]} confirmed 可复现')
        self.assertTrue(status['success'], status['output'])
        self.assertIn('已确认', status['output'])

        priority = self.run_command(f'publicfeedback priority {self.issue["id"]} 2 pin')
        self.assertTrue(priority['success'], priority['output'])
        current = feedback.get_public_issue(None, self.issue['id'], include_hidden=True)
        self.assertEqual(current['priority'], 2)
        self.assertTrue(current['pinned'])

        note = self.run_command(f'publicfeedback note {self.issue["id"]} 控制台内部备注')
        self.assertTrue(note['success'], note['output'])

        hidden = self.run_command(f'publicfeedback hide issue {self.issue["id"]}')
        self.assertTrue(hidden['success'], hidden['output'])
        self.assertFalse(feedback.get_public_issue(None, self.issue['id'], include_hidden=True)['visible'])
        restored = self.run_command(f'publicfeedback hide issue {self.issue["id"]} unhide')
        self.assertTrue(restored['success'], restored['output'])

    def test_vote_invalidate_restore_through_console(self):
        feedback.toggle_public_vote(self.user2['id'], self.issue['id'])
        self.assertEqual(feedback.get_public_issue(None, self.issue['id'])['vote_count'], 1)
        invalid = self.run_command(
            f'publicfeedback votes invalid {self.issue["id"]} {self.user2["username"]}',
        )
        self.assertTrue(invalid['success'], invalid['output'])
        self.assertEqual(feedback.get_public_issue(None, self.issue['id'])['vote_count'], 0)
        restore = self.run_command(
            f'publicfeedback votes restore {self.issue["id"]} {self.user2["id"]}',
        )
        self.assertTrue(restore['success'], restore['output'])
        self.assertEqual(feedback.get_public_issue(None, self.issue['id'])['vote_count'], 1)

    def test_audit_and_oldfeedback_commands(self):
        audit = self.run_command(f'publicfeedback audit {self.issue["id"]}')
        self.assertTrue(audit['success'], audit['output'])
        self.assertIn('投票事件', audit['output'])
        with db.get_db_connection() as conn:
            conn.execute(
                '''
                INSERT INTO feedback_threads(
                    user_id, category, title, status, created_at, updated_at
                ) VALUES (?, 'bug', '旧版标题', 'open', ?, ?)
                ''',
                (self.user1['id'], db.utc_now(), db.utc_now()),
            )
            conn.commit()
        old = self.run_command('publicfeedback oldfeedback list 10')
        self.assertTrue(old['success'], old['output'])
        self.assertIn('旧版标题', old['output'])

    def test_tree_help_and_completion_include_publicfeedback(self):
        self.assertIn('publicfeedback', app.ADMIN_COMMAND_TREE)
        completions = app.admin_console_completion_items('publicfeedback ')
        values = [item['value'] for item in completions]
        self.assertIn('list', values)
        self.assertIn('audit', values)
        self.assertIn('oldfeedback', values)


if __name__ == '__main__':
    unittest.main()
