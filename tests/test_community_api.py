import gc
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import app as gtn
import db


class CommunityApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'community-api.sqlite3')
        db.init_db()
        self.staff, error = db.create_user('CommApiStaff', 'Aa1!aaaa')
        self.assertIsNone(error)
        self.voter, error = db.create_user('CommApiVoter', 'Aa1!aaaa')
        self.assertIsNone(error)
        self.actor = {
            'user_id': self.staff['id'],
            'username': self.staff['username'],
            'role_type': 'staff',
        }
        gtn.app.config.update(TESTING=True)
        self.client = gtn.app.test_client()

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    @staticmethod
    def iso_after(hours):
        return (
            datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=hours)
        ).isoformat().replace('+00:00', 'Z')

    def ops_token(self):
        with mock.patch.object(gtn, 'title_editor_actor', return_value=self.actor):
            response = self.client.get('/api/community/ops/workspace')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Cache-Control'], 'private, no-store, max-age=0')
        return response.get_json()['csrf_token']

    def create_poll(self, *, publish=True):
        token = self.ops_token()
        with mock.patch.object(gtn, 'title_editor_actor', return_value=self.actor):
            response = self.client.post(
                '/api/community/ops/polls',
                headers={'X-Community-Ops-CSRF': token},
                json={
                    'question': '今天玩什么模式？',
                    'options': ['1v1', '2v2'],
                    'ends_at': self.iso_after(2),
                    'reminder_hours': 24,
                    'publish': publish,
                },
            )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        return response.get_json()['poll']

    def test_public_feed_is_anonymous_and_staff_page_is_fail_closed(self):
        response = self.client.get('/api/community/feed')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()['viewer']['authenticated'])
        self.assertEqual(response.get_json()['csrf_token'], '')

        with mock.patch.object(gtn, 'title_editor_actor', return_value=None):
            self.assertEqual(self.client.get('/community-ops').status_code, 403)
        with mock.patch.object(gtn, 'title_editor_actor', return_value=self.actor):
            page = self.client.get('/community-ops')
        self.assertEqual(page.status_code, 200)
        self.assertIn('id="announcement-create-form"', page.get_data(as_text=True))

    def test_ops_csrf_and_boolean_types_are_enforced(self):
        with mock.patch.object(gtn, 'title_editor_actor', return_value=self.actor):
            missing = self.client.post(
                '/api/community/ops/announcements',
                json={'title': '公告', 'body': '正文', 'pinned': False, 'publish': False, 'changelog_draft': False},
            )
        self.assertEqual(missing.status_code, 403)
        self.assertEqual(missing.get_json()['code'], 'CSRF_FAILED')

        token = self.ops_token()
        with mock.patch.object(gtn, 'title_editor_actor', return_value=self.actor):
            invalid = self.client.post(
                '/api/community/ops/announcements',
                headers={'X-Community-Ops-CSRF': token},
                json={'title': '公告', 'body': '正文', 'pinned': 'false', 'publish': False, 'changelog_draft': False},
            )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.get_json()['code'], 'INVALID_REQUEST')

    def test_published_announcement_reaches_public_feed_without_audit_fields(self):
        token = self.ops_token()
        with mock.patch.object(gtn, 'title_editor_actor', return_value=self.actor):
            created = self.client.post(
                '/api/community/ops/announcements',
                headers={'X-Community-Ops-CSRF': token},
                json={
                    'title': '娱乐赛奖励保留',
                    'body': '娱乐模式仍然发放对局奖励。',
                    'pinned': True,
                    'publish': True,
                    'changelog_draft': False,
                },
            )
        self.assertEqual(created.status_code, 201)

        feed = self.client.get('/api/community/feed').get_json()
        self.assertEqual(feed['announcements'][0]['title'], '娱乐赛奖励保留')
        self.assertNotIn('created_by', feed['announcements'][0])
        self.assertNotIn('audit', feed)

    def test_ops_workspace_cannot_create_or_mutate_changelog_drafts(self):
        token = self.ops_token()
        with mock.patch.object(gtn, 'title_editor_actor', return_value=self.actor):
            workspace = self.client.get('/api/community/ops/workspace').get_json()
            create = self.client.post(
                '/api/community/ops/announcements',
                headers={'X-Community-Ops-CSRF': token},
                json={
                    'title': '只发布公告',
                    'body': '不能同步更新日志。',
                    'pinned': False,
                    'publish': True,
                    'changelog_draft': True,
                },
            )
            mutate = self.client.post(
                '/api/community/ops/changelog-drafts/1/action',
                headers={'X-Community-Ops-CSRF': token},
                json={'action': 'discard'},
            )
        self.assertNotIn('changelog_drafts', workspace['workspace'])
        self.assertFalse(workspace['permissions']['can_manage_changelog_drafts'])
        self.assertEqual(create.status_code, 403)
        self.assertEqual(create.get_json()['code'], 'CHANGELOG_DISABLED')
        self.assertEqual(mutate.status_code, 403)
        self.assertEqual(mutate.get_json()['code'], 'CHANGELOG_DISABLED')
        self.assertEqual(gtn.list_community_ops_workspace()['changelog_drafts'], [])

    def test_account_vote_uses_csrf_is_idempotent_and_cannot_change(self):
        poll = self.create_poll()
        option_a, option_b = [item['id'] for item in poll['options']]
        voter_public = {
            'id': self.voter['id'],
            'username': self.voter['username'],
        }
        with (
            mock.patch.object(gtn, '_current_account_user', return_value=voter_public),
            mock.patch.object(gtn, 'title_editor_actor', return_value=None),
        ):
            feed_response = self.client.get('/api/community/feed')
        token = feed_response.get_json()['csrf_token']
        active = feed_response.get_json()['polls'][0]
        self.assertNotIn('vote_count', active['options'][0])

        account_result = (self.voter['id'], self.voter['username'], None)
        with mock.patch.object(gtn, '_require_account_json', return_value=account_result):
            voted = self.client.post(
                f'/api/community/polls/{poll["id"]}/vote',
                headers={'X-Community-CSRF': token},
                json={'option_id': option_a},
            )
            duplicate = self.client.post(
                f'/api/community/polls/{poll["id"]}/vote',
                headers={'X-Community-CSRF': token},
                json={'option_id': option_a},
            )
            conflict = self.client.post(
                f'/api/community/polls/{poll["id"]}/vote',
                headers={'X-Community-CSRF': token},
                json={'option_id': option_b},
            )
        self.assertEqual(voted.status_code, 200)
        self.assertFalse(voted.get_json()['duplicate'])
        self.assertTrue(duplicate.get_json()['duplicate'])
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.get_json()['code'], 'POLL_ALREADY_VOTED')

    def test_admin_console_commands_share_the_persistent_audit_path(self):
        announcement = gtn.execute_admin_command(
            'community announcement create "控制台公告" "正文" publish pin changelog',
            actor='ConsoleTester',
        )
        self.assertTrue(announcement['success'], announcement['output'])
        poll = gtn.execute_admin_command(
            f'community poll create "选择日期" "周六" "周日" end={self.iso_after(2)} publish',
            actor='ConsoleTester',
        )
        self.assertTrue(poll['success'], poll['output'])
        listing = gtn.execute_admin_command('community list', actor='ConsoleTester')
        self.assertTrue(listing['success'])
        self.assertIn('控制台公告', listing['output'])
        self.assertIn('选择日期', listing['output'])
        workspace = gtn.list_community_ops_workspace(audit_limit=10)
        self.assertTrue(any(item['actor_username'] == 'ConsoleTester' for item in workspace['audit']))


if __name__ == '__main__':
    unittest.main()
