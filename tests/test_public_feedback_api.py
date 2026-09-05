import unittest
from unittest import mock

import app as gtn


PUBLIC = gtn.public_feedback


class PublicFeedbackRouteTests(unittest.TestCase):
    def setUp(self):
        gtn.app.config.update(TESTING=True)
        self.client = gtn.app.test_client()
        self.db_patch = mock.patch.object(gtn, 'DB_AVAILABLE', True)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.ip_patch = mock.patch.object(
            gtn,
            '_get_ip_ban_status_cached',
            return_value={'banned': False},
        )
        self.ip_patch.start()
        self.addCleanup(self.ip_patch.stop)

    def test_anonymous_list_is_public(self):
        expected = {'items': [], 'total': 0, 'page': 1, 'per_page': 20, 'pages': 1}
        with (
            mock.patch.object(gtn, '_current_account_user', return_value=None),
            mock.patch.object(PUBLIC, 'list_public_issues', return_value=expected),
        ):
            response = self.client.get('/api/public-feedback/issues')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['total'], 0)

    def test_summary_guest_and_staff_counts(self):
        with (
            mock.patch.object(gtn, '_current_account_user', return_value=None),
            mock.patch.object(PUBLIC, 'public_feedback_author_unread_count', return_value=0),
            mock.patch.object(PUBLIC, 'public_feedback_staff_unread_count', return_value=0),
        ):
            guest = self.client.get('/api/public-feedback/summary').get_json()
        self.assertEqual(guest['authenticated'], False)
        self.assertEqual(guest['is_staff'], False)

        with (
            mock.patch.object(gtn, '_current_account_user', return_value={'id': 10}),
            mock.patch.object(gtn, 'feedback_is_staff', return_value=True),
            mock.patch.object(PUBLIC, 'public_feedback_author_unread_count', return_value=0),
            mock.patch.object(PUBLIC, 'public_feedback_staff_unread_count', return_value=3),
        ):
            staff = self.client.get('/api/public-feedback/summary').get_json()
        self.assertTrue(staff['is_staff'])
        self.assertEqual(staff['staff_unread_count'], 3)

    def test_issue_create_requires_account(self):
        response = self.client.post(
            '/api/public-feedback/issues',
            json={'kind': 'bug', 'title': 'x', 'body': 'y'},
        )
        self.assertEqual(response.status_code, 401)

    def test_issue_create_route(self):
        payload = {'id': 7, 'status': 'new', 'kind': 'bug'}
        with (
            mock.patch.object(
                gtn,
                '_require_account_json',
                return_value=(3, 'Player', None),
            ),
            mock.patch.object(gtn, '_public_feedback_mute_error', return_value=None),
            mock.patch.object(gtn, '_chat_exempt_from_user_id', return_value=True),
            mock.patch.object(
                gtn,
                '_validate_public_feedback_content',
                side_effect=[('标题', 'norm-title', 0), ('正文', 'norm-body', 0)],
            ),
            mock.patch.object(PUBLIC, 'create_public_issue', return_value=payload),
        ):
            response = self.client.post(
                '/api/public-feedback/issues',
                json={'kind': 'bug', 'title': '标题', 'body': '正文'},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['issue']['id'], 7)

    def test_vote_route_toggles(self):
        with (
            mock.patch.object(
                gtn,
                '_require_account_json',
                return_value=(3, 'Player', None),
            ),
            mock.patch.object(gtn, 'rate_limiter', return_value=True),
            mock.patch.object(
                PUBLIC,
                'toggle_public_vote',
                return_value={'voted': True, 'vote_count': 2},
            ),
        ):
            response = self.client.post('/api/public-feedback/issues/9/vote')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['vote_count'], 2)
        self.assertTrue(data['voted'])

    def test_staff_status_route_enforces_staff(self):
        with mock.patch.object(
            gtn,
            '_require_staff_account_json',
            return_value=(None, None, ('权限不足', 403)),
        ):
            response = self.client.post('/api/public-feedback/admin/issues/9/status', json={'status': 'confirmed'})
        self.assertEqual(response.status_code, 403)

    def test_staff_status_route_works(self):
        payload = {'id': 9, 'status': 'confirmed'}
        with (
            mock.patch.object(
                gtn,
                '_require_staff_account_json',
                return_value=(10, 'Staff', None),
            ),
            mock.patch.object(PUBLIC, 'set_public_issue_status', return_value=payload),
        ):
            response = self.client.post(
                '/api/public-feedback/admin/issues/9/status',
                json={'status': 'confirmed', 'reason': '可复现'},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['issue']['status'], 'confirmed')

    def test_comment_mutate_requires_owner_route_path(self):
        with (
            mock.patch.object(
                gtn,
                '_require_account_json',
                return_value=(3, 'Player', None),
            ),
            mock.patch.object(gtn, '_public_feedback_mute_error', return_value=None),
            mock.patch.object(gtn, '_chat_exempt_from_user_id', return_value=True),
            mock.patch.object(
                gtn,
                '_validate_public_feedback_content',
                return_value=('新评论', 'norm', 0),
            ),
            mock.patch.object(
                PUBLIC,
                'edit_public_comment',
                return_value={'id': 11, 'body': '新评论'},
            ),
        ):
            response = self.client.patch(
                '/api/public-feedback/comments/11',
                json={'body': '新评论'},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['comment']['id'], 11)


if __name__ == '__main__':
    unittest.main()
