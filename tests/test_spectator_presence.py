import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app


class SpectatorPresenceTests(unittest.TestCase):
    def test_lobby_lists_spectator_with_the_watched_mode(self):
        sid = f'spectator-list-{id(self)}'
        room_id = 900_000 + (id(self) % 10_000)
        room = SimpleNamespace(room_id=room_id, mode='random_deck', spectators=[sid])
        with app._lock:
            app.rooms[room_id] = room
            app.players[sid] = {
                'nickname': 'ListSpectator',
                'status': 'spectating',
                'spectating_room': room_id,
                'mode': '1v1',
            }
        try:
            listed = next(item for item in app.get_lobby_list() if item['sid'] == sid)
            self.assertEqual(listed['status'], 'spectating')
            self.assertEqual(listed['spectating_mode'], 'random_deck')
            self.assertEqual(app.room_spectator_players(room)[0]['nickname'], 'ListSpectator')
        finally:
            with app._lock:
                app.players.pop(sid, None)
                app.rooms.pop(room_id, None)

    def test_disconnect_removes_spectator_and_refreshes_room(self):
        client = app.socketio.test_client(app.app)
        room_id = 910_000 + (id(self) % 10_000)
        room = SimpleNamespace(room_id=room_id, mode='1v1', spectators=[])
        try:
            client.emit('login', {
                'nickname': f'Spec{id(self) % 100000}',
                'mode': '1v1',
            })
            login_events = [
                event['args'][0]
                for event in client.get_received()
                if event['name'] == 'login_ok'
            ]
            self.assertTrue(login_events)
            sid = login_events[-1]['sid']
            with app._lock:
                player = app.players[sid]
                player['status'] = 'spectating'
                player['spectating_room'] = room_id
                room.spectators.append(sid)
                app.rooms[room_id] = room

            with (
                patch.object(app, 'broadcast_game_state') as broadcast_state,
                patch.object(app, 'broadcast_lobby') as broadcast_lobby,
            ):
                client.disconnect()

            self.assertNotIn(sid, room.spectators)
            self.assertNotIn(sid, app.players)
            broadcast_state.assert_called_once_with(room)
            broadcast_lobby.assert_called()
        finally:
            if client.is_connected():
                client.disconnect()
            with app._lock:
                app.rooms.pop(room_id, None)

    def test_return_lobby_clears_spectator_presence(self):
        client = app.socketio.test_client(app.app)
        room_id = 920_000 + (id(self) % 10_000)
        room = SimpleNamespace(room_id=room_id, mode='1v1', spectators=[])
        try:
            client.emit('login', {
                'nickname': f'ReturnSpec{id(self) % 10000}',
                'mode': '1v1',
            })
            login_events = [
                event['args'][0]
                for event in client.get_received()
                if event['name'] == 'login_ok'
            ]
            self.assertTrue(login_events)
            sid = login_events[-1]['sid']
            with app._lock:
                player = app.players[sid]
                player['status'] = 'spectating'
                player['spectating_room'] = room_id
                room.spectators.append(sid)
                app.rooms[room_id] = room

            with (
                patch.object(app, 'broadcast_game_state') as broadcast_state,
                patch.object(app, 'broadcast_lobby') as broadcast_lobby,
            ):
                client.emit('return_lobby', {})

            received_names = [event['name'] for event in client.get_received()]
            self.assertIn('spectate_leave', received_names)
            self.assertNotIn(sid, room.spectators)
            self.assertEqual(app.players[sid]['status'], 'lobby')
            self.assertIsNone(app.players[sid].get('spectating_room'))
            broadcast_state.assert_called_once_with(room)
            broadcast_lobby.assert_called_once()
        finally:
            if client.is_connected():
                client.disconnect()
            with app._lock:
                app.rooms.pop(room_id, None)


if __name__ == '__main__':
    unittest.main()
