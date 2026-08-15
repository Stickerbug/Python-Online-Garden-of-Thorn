import unittest
from pathlib import Path
from unittest import mock

import app as gtn


class Ai1v1TestGateTests(unittest.TestCase):
    def setUp(self):
        gtn.app.config.update(TESTING=True, SECRET_KEY='ai-1v1-gate-test')
        self.client = gtn.app.test_client()

    def test_ai_does_not_become_a_formal_matchmaking_mode(self):
        self.assertEqual(gtn.PVP_MODES, ('1v1', '2v2', 'urf', 'random_deck'))

    def test_anonymous_session_never_receives_public_ai_access(self):
        with (
            mock.patch.object(gtn, 'GTN_AI_1V1_TEST_ENABLED', True),
            mock.patch.object(gtn, '_ai_test_active_count_locked', return_value=0),
        ):
            response = self.client.get('/api/ai-1v1/status')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Cache-Control'), 'no-store')
        self.assertEqual(response.get_json(), {
            'success': True,
            'authenticated': False,
            'enabled': True,
            'available': False,
            'active': 0,
            'capacity': gtn.GTN_AI_1V1_MAX_ACTIVE,
            'busy': False,
        })

    def test_hidden_feature_unlock_does_not_grant_ai_access(self):
        with self.client.session_transaction() as session:
            session['hidden_features_unlocked'] = True
        with mock.patch.object(gtn, 'GTN_AI_1V1_TEST_ENABLED', True):
            response = self.client.get('/api/ai-1v1/status')
        self.assertFalse(response.get_json()['authenticated'])
        self.assertFalse(response.get_json()['available'])
        hidden_status = self.client.get('/api/hidden-features/status').get_json()
        self.assertNotIn('ai_1v1_test', hidden_status)

    def test_logged_in_session_receives_access_when_server_enables_ai(self):
        with self.client.session_transaction() as session:
            session['user_id'] = 42
        with mock.patch.object(gtn, 'GTN_AI_1V1_TEST_ENABLED', True):
            response = self.client.get('/api/ai-1v1/status')
        payload = response.get_json()
        self.assertTrue(payload['authenticated'])
        self.assertTrue(payload['enabled'])
        self.assertTrue(payload['available'])

    def test_server_flag_stays_authoritative_for_logged_in_session(self):
        with self.client.session_transaction() as session:
            session['user_id'] = 42
        with mock.patch.object(gtn, 'GTN_AI_1V1_TEST_ENABLED', False):
            response = self.client.get('/api/ai-1v1/status')
        self.assertFalse(response.get_json()['available'])

    def test_lobby_entry_is_secondary_and_hidden_by_default(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / 'templates' / 'index.html').read_text(encoding='utf-8')
        script = (root / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
        self.assertIn('id="ai-1v1-test-entry" class="ai-1v1-test-entry hidden"', template)
        self.assertNotIn('class="mode-tab" data-mode="ai', template)
        self.assertIn("activeMode === '1v1'", script)
        self.assertIn("fetch('/api/ai-1v1/status'", script)
        self.assertIn('ai1v1TestGate.authenticated', script)
        self.assertIn("socket.emit('ai_1v1_start'", script)
        self.assertNotIn('ai-1v1-test-badge', template)
        self.assertNotIn('尚未接入实际对局', script)


if __name__ == '__main__':
    unittest.main()
