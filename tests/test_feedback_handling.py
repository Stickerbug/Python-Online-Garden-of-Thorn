import unittest
from unittest import mock

import app


class FeedbackHandlingRouteTests(unittest.TestCase):
    def setUp(self):
        app.app.config.update(TESTING=True)
        self.client = app.app.test_client()

    def authenticate_account(self, user_id=41):
        with self.client.session_transaction() as session:
            session['user_id'] = user_id
            session['username'] = 'StaffTester'

    def test_old_standalone_routes_are_removed(self):
        self.assertEqual(self.client.get('/handling').status_code, 404)
        self.assertEqual(
            self.client.post('/api/handling/login', json={'password': 'unused'}).status_code,
            404,
        )

    def test_handling_pane_requires_staff_account(self):
        self.assertEqual(self.client.get('/feedback/handling-pane').status_code, 403)
        self.authenticate_account()
        with mock.patch.object(app, 'feedback_is_staff', return_value=False):
            self.assertEqual(self.client.get('/feedback/handling-pane').status_code, 403)

    def test_staff_account_can_open_embedded_pane_without_password_form(self):
        self.authenticate_account()
        with mock.patch.object(app, 'feedback_is_staff', return_value=True):
            response = self.client.get('/feedback/handling-pane')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('id="handling-exit"', html)
        self.assertNotIn('id="login-form"', html)
        self.assertNotIn('type="password"', html)

    def test_handling_api_uses_staff_account_authorization(self):
        unauthorized = self.client.get('/api/feedback/handling/reports')
        self.assertEqual(unauthorized.status_code, 403)
        self.assertEqual(unauthorized.get_json()['error'], '权限不足')

        self.authenticate_account()
        report_page = {'items': [], 'total': 0, 'limit': 30, 'offset': 0}
        with (
            mock.patch.object(app, 'feedback_is_staff', return_value=True),
            mock.patch.object(app, 'DB_AVAILABLE', True),
            mock.patch.object(app, 'list_reports', return_value=report_page),
            mock.patch.object(app, 'log_admin_api_timing'),
        ):
            response = self.client.get('/api/feedback/handling/reports?status=pending')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['success'])


if __name__ == '__main__':
    unittest.main()
