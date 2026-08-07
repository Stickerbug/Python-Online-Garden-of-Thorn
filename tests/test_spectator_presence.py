import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app


class SpectatorPresenceTests(unittest.TestCase):
    def test_game_over_cleanup_returns_current_spectator_to_lobby(self):
        spectator_sid = f'spectator-cleanup-{id(self)}'
        room_id = 890_000 + (id(self) % 10_000)
        room = SimpleNamespace(
            room_id=room_id,
            match_seq=1,
            created_at=1,
            player_sids=[],
            spectators=[spectator_sid],
            _game_over_cleanup_timer=None,
        )
        with app._lock:
            app.players[spectator_sid] = {
                'nickname': 'CleanupSpectator',
                'status': 'spectating',
                'room_id': None,
                'spectating_room': room_id,
                'spectate_perspective': 1,
            }
            app.rooms[room_id] = room
        try:
            with patch.object(app.threading, 'Timer') as timer_class:
                timer = timer_class.return_value
                app._schedule_game_over_cleanup(room)
                cleanup = timer_class.call_args.args[1]

            with (
                patch.object(app.socketio, 'emit') as socket_emit,
                patch.object(app, 'broadcast_lobby') as broadcast_lobby,
                patch.object(app, 'admin_event'),
            ):
                cleanup()

            player = app.players[spectator_sid]
            self.assertEqual(player['status'], 'lobby')
            self.assertIsNone(player['spectating_room'])
            self.assertEqual(player['spectate_perspective'], 0)
            self.assertNotIn(room_id, app.rooms)
            self.assertTrue(any(
                call.args and call.args[0] == 'spectate_leave'
                for call in socket_emit.call_args_list
            ))
            broadcast_lobby.assert_called_once()
        finally:
            room._game_over_cleanup_timer = None
            with app._lock:
                app.players.pop(spectator_sid, None)
                app.rooms.pop(room_id, None)

    def test_spectate_entry_repairs_orphaned_spectator_state(self):
        spectator_sid = f'spectator-repair-{id(self)}'
        with app._lock:
            app.players[spectator_sid] = {
                'nickname': 'RepairSpectator',
                'status': 'spectating',
                'room_id': None,
                'spectating_room': 999_999_999,
                'spectate_perspective': 3,
            }
        try:
            with patch.object(app, 'admin_event') as admin_event:
                with app._lock:
                    repaired = app.repair_stale_spectator_state_locked(spectator_sid)

            player = app.players[spectator_sid]
            self.assertTrue(repaired)
            self.assertEqual(player['status'], 'lobby')
            self.assertIsNone(player['room_id'])
            self.assertIsNone(player['spectating_room'])
            self.assertEqual(player['spectate_perspective'], 0)
            admin_event.assert_called_once()
        finally:
            with app._lock:
                app.players.pop(spectator_sid, None)

    def test_spectate_repair_does_not_touch_current_spectator(self):
        spectator_sid = f'spectator-current-{id(self)}'
        room_id = 895_000 + (id(self) % 10_000)
        room = SimpleNamespace(room_id=room_id, spectators=[spectator_sid])
        with app._lock:
            app.rooms[room_id] = room
            app.players[spectator_sid] = {
                'nickname': 'CurrentSpectator',
                'status': 'spectating',
                'room_id': None,
                'spectating_room': room_id,
                'spectate_perspective': 1,
            }
        try:
            with app._lock:
                repaired = app.repair_stale_spectator_state_locked(spectator_sid)
            self.assertFalse(repaired)
            self.assertEqual(app.players[spectator_sid]['status'], 'spectating')
            self.assertEqual(app.players[spectator_sid]['spectating_room'], room_id)
        finally:
            with app._lock:
                app.players.pop(spectator_sid, None)
                app.rooms.pop(room_id, None)

    def test_new_spectate_request_can_leave_a_still_live_old_spectate_room(self):
        client = app.socketio.test_client(app.app)
        old_room_id = 896_000 + (id(self) % 1_000)
        new_room_id = old_room_id + 1
        old_room = SimpleNamespace(
            room_id=old_room_id,
            match_seq=1,
            created_at=1,
            mode='1v1',
            beta_mode=False,
            player_sids=[],
            spectators=[],
            engine=SimpleNamespace(phase='action', player_names=[]),
        )
        new_room = SimpleNamespace(
            room_id=new_room_id,
            match_seq=1,
            created_at=2,
            mode='1v1',
            beta_mode=False,
            player_sids=[],
            spectators=[],
            engine=SimpleNamespace(phase='action', player_names=[]),
        )
        sid = None
        try:
            client.emit('login', {
                'nickname': f'SwitchSpec{id(self) % 100000}',
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
                player['room_id'] = None
                player['spectating_room'] = old_room_id
                player['spectate_perspective'] = 0
                old_room.spectators.append(sid)
                app.rooms[old_room_id] = old_room
                app.rooms[new_room_id] = new_room

            with (
                patch.object(app, '_send_spectate_state_internal'),
                patch.object(app, 'broadcast_game_state') as broadcast_state,
                patch.object(app, 'broadcast_lobby') as broadcast_lobby,
            ):
                client.emit('spectate', {'room_id': new_room_id})

            received_names = [event['name'] for event in client.get_received()]
            self.assertIn('spectate_enter', received_names)
            self.assertNotIn('server_error', received_names)
            self.assertNotIn(sid, old_room.spectators)
            self.assertIn(sid, new_room.spectators)
            self.assertEqual(app.players[sid]['status'], 'spectating')
            self.assertEqual(app.players[sid]['spectating_room'], new_room_id)
            broadcast_state.assert_any_call(old_room)
            broadcast_state.assert_any_call(new_room)
            broadcast_lobby.assert_called_once()
        finally:
            if client.is_connected():
                client.disconnect()
            with app._lock:
                app.rooms.pop(old_room_id, None)
                app.rooms.pop(new_room_id, None)

    def test_spectators_share_the_automatic_afk_activity_timer(self):
        spectator_sid = f'spectator-afk-{id(self)}'
        game_sid = f'player-afk-{id(self)}'
        with app._lock:
            app.players[spectator_sid] = {
                'nickname': 'IdleSpectator',
                'status': 'spectating',
                'spectating_room': 123,
            }
            app.players[game_sid] = {
                'nickname': 'ActivePlayer',
                'status': 'in_game',
                'room_id': 123,
            }
        try:
            with patch.object(app.random, 'uniform', return_value=420):
                app.mark_afk_activity(spectator_sid, now=1000)
                app.mark_afk_activity(game_sid, now=1000)
            self.assertEqual(app.players[spectator_sid]['last_lobby_activity_at'], 1000)
            self.assertEqual(app.players[spectator_sid]['next_lobby_afk_check_at'], 1420)
            self.assertNotIn('next_lobby_afk_check_at', app.players[game_sid])
            self.assertTrue(app._player_uses_automatic_afk_check(app.players[spectator_sid]))
            self.assertFalse(app._player_uses_automatic_afk_check(app.players[game_sid]))
        finally:
            with app._lock:
                app.players.pop(spectator_sid, None)
                app.players.pop(game_sid, None)

    def test_passive_state_sync_does_not_count_as_spectator_activity(self):
        self.assertIn('request_game_state', app.AFK_ACTIVITY_IGNORED_EVENTS)
        self.assertIn('request_pregame_state', app.AFK_ACTIVITY_IGNORED_EVENTS)
        self.assertNotIn('chat', app.AFK_ACTIVITY_IGNORED_EVENTS)
        self.assertNotIn('switch_spectate_perspective', app.AFK_ACTIVITY_IGNORED_EVENTS)

    def test_automatic_afk_prompt_can_target_spectators_but_not_players_in_game(self):
        spectator_sid = f'spectator-afk-prompt-{id(self)}'
        game_sid = f'player-afk-prompt-{id(self)}'
        with app._lock:
            app.players[spectator_sid] = {
                'nickname': 'PromptSpectator',
                'status': 'spectating',
                'spectating_room': 456,
            }
            app.players[game_sid] = {
                'nickname': 'PromptPlayer',
                'status': 'in_game',
                'room_id': 456,
            }
        try:
            with (
                patch.object(app.socketio, 'emit') as emit,
                patch.object(app.socketio, 'start_background_task') as start_task,
                patch.object(app, 'admin_event'),
            ):
                result, error = app.send_afk_check_to_player(
                    spectator_sid,
                    reason='auto_spectator_idle',
                    lobby_only=True,
                )
                skipped, skipped_error = app.send_afk_check_to_player(
                    game_sid,
                    reason='auto_lobby_idle',
                    lobby_only=True,
                )
            self.assertIsNone(error)
            self.assertEqual(result['sid'], spectator_sid)
            self.assertIsNone(skipped)
            self.assertIsNone(skipped_error)
            emit.assert_called_once()
            start_task.assert_called_once()
        finally:
            with app._lock:
                app.PENDING_AFK_CHECKS.pop(spectator_sid, None)
                app.PENDING_AFK_CHECKS.pop(game_sid, None)
                app.players.pop(spectator_sid, None)
                app.players.pop(game_sid, None)

    def test_spectator_operation_resets_afk_timer_but_state_sync_does_not(self):
        client = app.socketio.test_client(app.app)
        room_id = 905_000 + (id(self) % 10_000)
        room = SimpleNamespace(
            room_id=room_id,
            mode='1v1',
            player_sids=['player-a', 'player-b'],
            spectators=[],
        )
        sid = None
        try:
            client.emit('login', {
                'nickname': f'AfkSpec{id(self) % 100000}',
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
                player['next_lobby_afk_check_at'] = 123
                room.spectators.append(sid)
                app.rooms[room_id] = room

            with patch.object(app, 'send_spectate_state_to'):
                client.emit('request_game_state', {})
            self.assertEqual(app.players[sid]['next_lobby_afk_check_at'], 123)

            with patch.object(app.random, 'uniform', return_value=420):
                client.emit('afk_activity', {})
            self.assertGreater(app.players[sid]['next_lobby_afk_check_at'], 123)

            app.players[sid]['next_lobby_afk_check_at'] = 123
            with (
                patch.object(app, '_send_spectate_state_internal'),
                patch.object(app.random, 'uniform', return_value=420),
            ):
                client.emit('switch_spectate_perspective', {})
            self.assertGreater(app.players[sid]['next_lobby_afk_check_at'], 123)
        finally:
            with app._lock:
                if sid in app.players:
                    app.players[sid]['status'] = 'lobby'
                    app.players[sid]['spectating_room'] = None
                if sid in room.spectators:
                    room.spectators.remove(sid)
                app.rooms.pop(room_id, None)
            if client.is_connected():
                client.disconnect()

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

    def test_leave_spectate_ignores_stale_match_context(self):
        client = app.socketio.test_client(app.app)
        room_id = 930_000 + (id(self) % 10_000)
        room = SimpleNamespace(
            room_id=room_id,
            match_seq=4,
            created_at=12.5,
            spectators=[],
        )
        sid = None
        try:
            client.emit('login', {
                'nickname': f'StaleSpec{id(self) % 1000}',
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
                client.emit('leave_spectate', {
                    'room_id': room_id + 1,
                    'match_key': 'stale-match-key',
                })

            received = client.get_received()
            self.assertIn('spectate_leave', [event['name'] for event in received])
            self.assertFalse(any(
                event['name'] == 'action_rejected'
                and event.get('args')
                and event['args'][0].get('code') == 'STATE_VERSION_OLD'
                for event in received
            ))
            self.assertEqual(app.players[sid]['status'], 'lobby')
            self.assertIsNone(app.players[sid].get('spectating_room'))
            self.assertNotIn(sid, room.spectators)
            broadcast_state.assert_called_once_with(room)
            broadcast_lobby.assert_called_once()
        finally:
            if client.is_connected():
                client.disconnect()
            with app._lock:
                if sid is not None:
                    app.players.pop(sid, None)
                app.rooms.pop(room_id, None)


if __name__ == '__main__':
    unittest.main()
