import pathlib
import unittest
import uuid
from unittest import mock

import app as gtn


ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')


def source_between(source, start, end):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


class MatchContextServerTests(unittest.TestCase):
    def setUp(self):
        self.clients = [gtn.socketio.test_client(gtn.app), gtn.socketio.test_client(gtn.app)]
        self.sids = []
        for index, client in enumerate(self.clients):
            client.emit('login', {
                'nickname': f'MC{index}{uuid.uuid4().hex[:7]}',
                'mode': '1v1',
            })
            login_events = [
                event['args'][0]
                for event in client.get_received()
                if event['name'] == 'login_ok'
            ]
            self.assertTrue(login_events)
            self.sids.append(login_events[-1]['sid'])
        self.room_id = 970_000 + (id(self) % 10_000)
        self.room = gtn.GameRoom(self.room_id, self.sids, {'Basic', 'Rose'}, mode='1v1')
        self.room.engine.phase = 'action'
        self.room.engine.game_over = False
        with gtn._lock:
            gtn.rooms[self.room_id] = self.room
            for sid in self.sids:
                gtn.players[sid]['room_id'] = self.room_id
                gtn.players[sid]['status'] = 'in_game'

    def tearDown(self):
        with gtn._lock:
            gtn.rooms.pop(self.room_id, None)
            for sid in self.sids:
                player = gtn.players.get(sid)
                if player and player.get('room_id') == self.room_id:
                    player['room_id'] = None
                    player['status'] = 'lobby'
        for client in self.clients:
            if client.is_connected():
                client.disconnect()

    def test_stale_return_lobby_cannot_forfeit_current_match(self):
        stale_payload = {
            'room_id': self.room_id - 1,
            'match_key': f'{self.room_id - 1}:1:old',
        }
        with (
            mock.patch.object(gtn, '_finish_room_by_forfeit') as finish_forfeit,
            mock.patch.object(gtn, 'send_game_state_to'),
            mock.patch.object(gtn, 'broadcast_lobby'),
        ):
            self.clients[0].emit('return_lobby', stale_payload)
            gtn.socketio.sleep(0.02)

        finish_forfeit.assert_not_called()
        self.assertEqual(gtn.players[self.sids[0]]['room_id'], self.room_id)
        self.assertEqual(gtn.players[self.sids[0]]['status'], 'in_game')
        self.assertFalse(self.room.engine.game_over)
        rejected = [
            event['args'][0]
            for event in self.clients[0].get_received()
            if event['name'] == 'action_rejected'
        ]
        self.assertTrue(any(item.get('code') == 'STATE_VERSION_OLD' for item in rejected))

    def test_context_free_return_lobby_is_ignored_during_live_match(self):
        with (
            mock.patch.object(gtn, '_finish_room_by_forfeit') as finish_forfeit,
            mock.patch.object(gtn, 'send_game_state_to'),
            mock.patch.object(gtn, 'broadcast_lobby'),
        ):
            self.clients[0].emit('return_lobby', {})
            gtn.socketio.sleep(0.02)

        finish_forfeit.assert_not_called()
        self.assertEqual(gtn.players[self.sids[0]]['room_id'], self.room_id)
        self.assertFalse(self.room.engine.game_over)

    def test_stale_end_turn_never_reaches_current_engine(self):
        stale_payload = {
            'room_id': self.room_id - 1,
            'match_key': f'{self.room_id - 1}:1:old',
        }
        with (
            mock.patch.object(self.room.engine, 'end_turn') as end_turn,
            mock.patch.object(gtn, 'send_game_state_to'),
        ):
            self.clients[0].emit('end_turn', stale_payload)
            gtn.socketio.sleep(0.02)

        end_turn.assert_not_called()
        rejected = [
            event['args'][0]
            for event in self.clients[0].get_received()
            if event['name'] == 'action_rejected'
        ]
        self.assertTrue(any(item.get('code') == 'STATE_VERSION_OLD' for item in rejected))

    def test_old_room_broadcast_skips_sid_that_moved_to_new_room(self):
        new_room_id = self.room_id + 1
        with gtn._lock:
            for sid in self.sids:
                gtn.players[sid]['room_id'] = new_room_id
        try:
            with (
                mock.patch.object(gtn.socketio, 'emit') as socket_emit,
                mock.patch.object(gtn, 'check_live_achievements'),
                mock.patch.object(gtn, 'emit_pending_choice_request'),
                mock.patch.object(gtn, 'broadcast_spectate_state'),
                mock.patch.object(gtn, 'record_socket_broadcast'),
            ):
                gtn._broadcast_game_state_now(self.room)

            state_emits = [
                call for call in socket_emit.call_args_list
                if call.args and call.args[0] == 'state_update'
            ]
            self.assertEqual(state_emits, [])
        finally:
            with gtn._lock:
                for sid in self.sids:
                    if sid in gtn.players:
                        gtn.players[sid]['room_id'] = self.room_id

    def test_old_room_cleanup_does_not_clear_new_room_membership(self):
        new_room_id = self.room_id + 1
        with gtn._lock:
            for sid in self.sids:
                gtn.players[sid]['room_id'] = new_room_id
                gtn.players[sid]['status'] = 'in_game'
        timer_callback = None
        try:
            with mock.patch.object(gtn.threading, 'Timer') as timer_class:
                timer = mock.Mock()
                timer_class.return_value = timer
                gtn._schedule_game_over_cleanup(self.room)
                timer_callback = timer_class.call_args.args[1]

            with (
                mock.patch.object(gtn.socketio, 'emit') as socket_emit,
                mock.patch.object(gtn, 'broadcast_lobby'),
            ):
                timer_callback()

            for sid in self.sids:
                self.assertEqual(gtn.players[sid]['room_id'], new_room_id)
                self.assertEqual(gtn.players[sid]['status'], 'in_game')
            lobby_phase_emits = [
                call for call in socket_emit.call_args_list
                if call.args and call.args[0] == 'game_phase'
            ]
            self.assertEqual(lobby_phase_emits, [])
        finally:
            self.room._game_over_cleanup_timer = None
            with gtn._lock:
                for sid in self.sids:
                    if sid in gtn.players:
                        gtn.players[sid]['room_id'] = self.room_id


class MatchContextClientContractTests(unittest.TestCase):
    def test_return_lobby_has_one_emitter_and_carries_match_context(self):
        self.assertEqual(GAME_JS.count("socket.emit('return_lobby'"), 1)
        section = source_between(
            GAME_JS,
            'function returnToLobbyFromGameOver(',
            'function showOpponentDCWaiting(',
        )
        self.assertIn("phase !== 'game_over'", section)
        self.assertIn("socket.emit('return_lobby', currentMatchActionContext(expectedContext))", section)

    def test_state_update_rejects_retired_match_before_route_mutation(self):
        section = source_between(
            GAME_JS,
            "bindSocketEvent('state_update'",
            "bindSocketEvent('turn_timer_update'",
        )
        context_guard = section.index("shouldAcceptNetworkMatchPayload(data, 'state_update')")
        route_mutation = section.index("rememberActiveMatchRoute(data || {}, 'state_update')")
        self.assertLess(context_guard, route_mutation)

    def test_cross_match_states_are_never_treated_as_sequential_animation(self):
        section = source_between(
            GAME_JS,
            'function areSequentialGameStates(',
            'function getCombatFloatAnchor(',
        )
        self.assertIn('previousMatchKey !== nextMatchKey', section)
        self.assertIn('Number(previous.room_id) !== Number(next.room_id)', section)

    def test_lobby_transition_cancels_old_match_runtime(self):
        section = source_between(
            GAME_JS,
            'function clearNetworkMatchStateForLobby()',
            'function clearTransientMatchRecovery(',
        )
        self.assertIn("retireActiveNetworkMatch('return_to_lobby')", section)
        self.assertIn('resetMatchRuntimeState({ clearGameState: true })', section)

    def test_old_lobby_and_delayed_game_over_payloads_are_guarded(self):
        phase_section = source_between(
            GAME_JS,
            "bindSocketEvent('game_phase'",
            "bindSocketEvent('draft_state'",
        )
        self.assertIn("'game_phase:lobby', { allowSwitch: false }", phase_section)
        game_over_section = source_between(
            GAME_JS,
            'function renderGameOverAfterFinalAnimation(',
            'function normalizeTargetCandidates(',
        )
        self.assertIn('retiredNetworkMatchKeys.has(scheduledMatchKey)', game_over_section)
        self.assertIn('currentMatchKey !== scheduledMatchKey', game_over_section)


if __name__ == '__main__':
    unittest.main()
