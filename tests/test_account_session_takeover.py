import pathlib
import unittest
from unittest.mock import patch

import app


ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')


def source_between(source, start, end):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


class AccountSessionTakeoverTests(unittest.TestCase):
    def test_same_socket_account_login_is_not_replaced_or_disconnected(self):
        account = {
            'id': 980_000 + (id(self) % 10_000),
            'username': f'SelfRelogin{id(self) % 100000}',
            'player_id': f'PSELF{id(self) % 100000}',
            'skin': {},
            'accept_game_invites': True,
            'allow_guest_spectators': False,
        }
        client = None
        sid = None
        try:
            with (
                patch.object(app, '_current_account_user', return_value=account),
                patch.object(app, 'auth_user_payload', side_effect=lambda user: dict(user)),
                patch.object(app, 'record_account_game_entry_async'),
                patch.object(app.account_integrity, 'get_reputation_profile', return_value={'value':85,'can_ranked':True}),
            ):
                client = app.socketio.test_client(app.app)
                payload = {
                    'nickname': account['username'],
                    'mode': '1v1',
                    'account_login': True,
                }
                client.emit('login', payload)
                first_events = client.get_received()
                first_login = next(
                    event['args'][0]
                    for event in first_events
                    if event['name'] == 'login_ok'
                )
                sid = first_login['sid']

                client.emit('login', payload)
                second_events = client.get_received()

            event_names = [event['name'] for event in second_events]
            self.assertIn('login_ok', event_names)
            self.assertNotIn('account_session_replaced', event_names)
            self.assertNotIn('kicked', event_names)
            self.assertNotIn('login_fail', event_names)
            self.assertTrue(client.is_connected())
            self.assertEqual(app.players[sid]['user_id'], account['id'])
        finally:
            if client is not None and client.is_connected():
                client.disconnect()
            if sid:
                with app._lock:
                    app.players.pop(sid, None)

    def test_different_socket_still_replaces_the_old_account_session(self):
        account = {
            'id': 990_000 + (id(self) % 10_000),
            'username': f'OtherRelogin{id(self) % 100000}',
            'player_id': f'POTHER{id(self) % 100000}',
            'skin': {},
            'accept_game_invites': True,
            'allow_guest_spectators': False,
        }
        old_client = None
        new_client = None
        old_sid = None
        new_sid = None
        try:
            with (
                patch.object(app, '_current_account_user', return_value=account),
                patch.object(app, 'auth_user_payload', side_effect=lambda user: dict(user)),
                patch.object(app, 'record_account_game_entry_async'),
                patch.object(app.account_integrity, 'get_reputation_profile', return_value={'value':85,'can_ranked':True}),
            ):
                old_client = app.socketio.test_client(app.app)
                new_client = app.socketio.test_client(app.app)
                payload = {
                    'nickname': account['username'],
                    'mode': '1v1',
                    'account_login': True,
                }
                old_client.emit('login', payload)
                old_sid = next(
                    event['args'][0]['sid']
                    for event in old_client.get_received()
                    if event['name'] == 'login_ok'
                )

                new_client.emit('login', payload)
                new_events = new_client.get_received()
                new_sid = next(
                    event['args'][0]['sid']
                    for event in new_events
                    if event['name'] == 'login_ok'
                )

            self.assertNotEqual(old_sid, new_sid)
            self.assertFalse(old_client.is_connected())
            self.assertTrue(new_client.is_connected())
            self.assertNotIn(old_sid, app.players)
            self.assertEqual(app.players[new_sid]['user_id'], account['id'])
        finally:
            for client in (old_client, new_client):
                if client is not None and client.is_connected():
                    client.disconnect()
            with app._lock:
                if old_sid:
                    app.players.pop(old_sid, None)
                if new_sid:
                    app.players.pop(new_sid, None)

    def test_replacement_notice_cannot_clear_or_replace_the_new_socket(self):
        helper = source_between(
            GAME_JS,
            'function isReplacementNoticeForCurrentSocket(data = {})',
            'function connectSocket(serverUrl)',
        )
        self.assertIn("String(data.replacement_sid) === String(socket.id || '')", helper)

        section = source_between(
            GAME_JS,
            "bindSocketEvent('account_session_replaced'",
            "bindSocketEvent('kicked'",
        )
        guard = section.index('isReplacementNoticeForCurrentSocket(data)')
        phase_change = section.index("phase = 'login'")
        self.assertLess(guard, phase_change)
        self.assertNotIn('currentAccount = null', section)
        self.assertNotIn('cacheAccount(null)', section)

        kicked_section = source_between(
            GAME_JS,
            "bindSocketEvent('kicked'",
            "bindSocketEvent('latency_pong'",
        )
        kicked_guard = kicked_section.index('isReplacementNoticeForCurrentSocket(data)')
        kicked_phase_change = kicked_section.index("phase = 'login'")
        self.assertLess(kicked_guard, kicked_phase_change)


if __name__ == '__main__':
    unittest.main()
