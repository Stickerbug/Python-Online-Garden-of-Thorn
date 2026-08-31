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
            mock.patch.object(gtn, 'GTN_AI_PUBLIC_ENTRY_ENABLED', True),
            mock.patch.object(gtn, '_ai_test_active_count_locked', return_value=0),
        ):
            response = self.client.get('/api/ai-1v1/status')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Cache-Control'), 'no-store')
        self.assertEqual(response.get_json(), {
            'success': True,
            'authenticated': False,
            'enabled': True,
            'public_entry_enabled': True,
            'available': False,
            'active': 0,
            'capacity': gtn.GTN_AI_1V1_MAX_ACTIVE,
            'busy': False,
        })

    def test_hidden_feature_unlock_does_not_grant_ai_access(self):
        with self.client.session_transaction() as session:
            session['hidden_features_unlocked'] = True
        with (
            mock.patch.object(gtn, 'GTN_AI_1V1_TEST_ENABLED', True),
            mock.patch.object(gtn, 'GTN_AI_PUBLIC_ENTRY_ENABLED', True),
        ):
            response = self.client.get('/api/ai-1v1/status')
        self.assertFalse(response.get_json()['authenticated'])
        self.assertFalse(response.get_json()['available'])
        hidden_status = self.client.get('/api/hidden-features/status').get_json()
        self.assertNotIn('ai_1v1_test', hidden_status)

    def test_logged_in_session_receives_access_when_server_enables_ai(self):
        with self.client.session_transaction() as session:
            session['user_id'] = 42
        with (
            mock.patch.object(gtn, 'GTN_AI_1V1_TEST_ENABLED', True),
            mock.patch.object(gtn, 'GTN_AI_PUBLIC_ENTRY_ENABLED', True),
        ):
            response = self.client.get('/api/ai-1v1/status')
        payload = response.get_json()
        self.assertTrue(payload['authenticated'])
        self.assertTrue(payload['enabled'])
        self.assertTrue(payload['available'])

    def test_server_flag_stays_authoritative_for_logged_in_session(self):
        with self.client.session_transaction() as session:
            session['user_id'] = 42
        with (
            mock.patch.object(gtn, 'GTN_AI_1V1_TEST_ENABLED', False),
            mock.patch.object(gtn, 'GTN_AI_PUBLIC_ENTRY_ENABLED', True),
        ):
            response = self.client.get('/api/ai-1v1/status')
        self.assertFalse(response.get_json()['available'])

    def test_public_entry_flag_defaults_off_and_is_reported_separately(self):
        source = Path(gtn.__file__).read_text(encoding='utf-8')
        self.assertIn("os.environ.get('GTN_AI_PUBLIC_ENTRY_ENABLED', '0')", source)
        with (
            mock.patch.object(gtn, 'GTN_AI_1V1_TEST_ENABLED', True),
            mock.patch.object(gtn, 'GTN_AI_PUBLIC_ENTRY_ENABLED', False),
        ):
            response = self.client.get('/api/ai-1v1/status')
        payload = response.get_json()
        self.assertTrue(payload['enabled'])
        self.assertFalse(payload['public_entry_enabled'])
        self.assertFalse(payload['available'])

    def test_lobby_entry_is_not_rendered_while_public_flag_is_off(self):
        with mock.patch.object(gtn, 'GTN_AI_PUBLIC_ENTRY_ENABLED', False):
            response = self.client.get('/')
        self.assertNotIn('id="ai-1v1-test-entry"', response.get_data(as_text=True))

    def test_lobby_entry_can_be_restored_without_readding_the_markup(self):
        with mock.patch.object(gtn, 'GTN_AI_PUBLIC_ENTRY_ENABLED', True):
            response = self.client.get('/')
        self.assertIn(
            'id="ai-1v1-test-entry" class="ai-1v1-test-entry hidden"',
            response.get_data(as_text=True),
        )

    def test_disabled_public_socket_entry_returns_stable_error_code(self):
        http_client = gtn.app.test_client()
        with http_client.session_transaction() as session:
            session['user_id'] = 42
        client = gtn.socketio.test_client(gtn.app, flask_test_client=http_client)
        room_map = gtn.socketio.server.manager.rooms['/'][None]
        sid = next(key for key, value in room_map.items() if value == client.eio_sid)
        gtn.players[sid] = {
            'nickname': 'Disabled AI Entry Test',
            'user_id': 42,
            'is_registered_user': True,
            'status': 'lobby',
            'room_id': None,
            'mode': '1v1',
        }
        try:
            with (
                mock.patch.object(gtn, 'GTN_AI_1V1_TEST_ENABLED', True),
                mock.patch.object(gtn, 'GTN_AI_PUBLIC_ENTRY_ENABLED', False),
                mock.patch.object(gtn, '_start_ai_test_background_task') as start_task,
            ):
                client.get_received()
                client.emit('ai_1v1_start', {})
                received = client.get_received()
            payload = next(
                event['args'][0]
                for event in received
                if event['name'] == 'ai_1v1_status'
            )
            self.assertEqual(payload['code'], 'AI_TEMPORARILY_DISABLED')
            self.assertNotIn(sid, gtn.ai_test_starting)
            start_task.assert_not_called()
            with (
                mock.patch.object(gtn, 'GTN_AI_1V1_TEST_ENABLED', True),
                mock.patch.object(gtn, 'GTN_AI_PUBLIC_ENTRY_ENABLED', False),
            ):
                client.emit('ai_1v1_rematch', {})
                rematch_received = client.get_received()
            rematch_payload = next(
                event['args'][0]
                for event in rematch_received
                if event['name'] == 'ai_1v1_status'
            )
            self.assertEqual(rematch_payload['code'], 'AI_TEMPORARILY_DISABLED')
            start_task.assert_not_called()
        finally:
            gtn.ai_test_starting.discard(sid)
            gtn.players.pop(sid, None)
            client.disconnect()

    def test_lobby_entry_remains_secondary_when_restored(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / 'templates' / 'index.html').read_text(encoding='utf-8')
        script = (root / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
        self.assertIn('{% if ai_public_entry_enabled %}', template)
        self.assertIn('id="ai-1v1-test-entry" class="ai-1v1-test-entry hidden"', template)
        self.assertNotIn('class="mode-tab" data-mode="ai', template)
        self.assertIn("activeMode === '1v1'", script)
        self.assertIn("fetch('/api/ai-1v1/status'", script)
        self.assertIn('ai1v1TestGate.authenticated', script)
        self.assertIn('data.enabled && data.public_entry_enabled', script)
        self.assertIn("socket.emit('ai_1v1_start'", script)
        self.assertNotIn('ai-1v1-test-badge', template)
        self.assertNotIn('尚未接入实际对局', script)


if __name__ == '__main__':
    unittest.main()
