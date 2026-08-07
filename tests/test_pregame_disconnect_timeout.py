import unittest
from unittest import mock

import app as gtn


class PregameDisconnectTimeoutTests(unittest.TestCase):
    @staticmethod
    def _draft_first_options(engine, player_id, count):
        while len(engine.draft_picks[player_id]) < count:
            option = engine.draft_options[player_id][0]
            result = engine.draft_pick(player_id, option.def_id)
            success = result.get('success') if isinstance(result, dict) else result
            if not success:
                raise AssertionError(f'failed to draft for player {player_id}: {result}')

    def _partial_2v2_room(self):
        room = gtn.GameRoom(
            981_183,
            ['r18183-p0', 'r18183-p1', 'r18183-p2', 'r18183-p3'],
            mode='2v2',
        )
        engine = room.engine
        engine.start_event_select_first()
        for player_id in range(4):
            event_id = engine.opening_event_options[player_id][0]['id']
            self.assertTrue(engine.select_opening_event(player_id, event_id))
        for player_id in range(4):
            self.assertTrue(engine.start_draft_for_player(player_id))

        self._draft_first_options(engine, 0, 9)
        for player_id in range(1, 4):
            self._draft_first_options(engine, player_id, engine.draft_target_count(player_id))
            if engine.needs_sub_choice(player_id):
                engine.opening_event_sub_choices[player_id] = gtn._default_event_sub_choice(engine, player_id)
            engine.player_ready[player_id] = True
        return room

    def test_setup_timeout_finishes_draft_before_killing_player(self):
        room = self._partial_2v2_room()
        engine = room.engine

        with (
            mock.patch.object(gtn, 'record_room_replay_action'),
            mock.patch.object(gtn, 'admin_event'),
        ):
            ended = gtn._mark_disconnect_timeout_loss(room, 0, 'r18183-p0')

        self.assertFalse(ended)
        self.assertEqual(engine.phase, 'draft')
        self.assertFalse(engine._game_start_applied)
        self.assertEqual(len(engine.draft_picks[0]), engine.draft_target_count(0))
        self.assertTrue(engine.player_ready[0])
        self.assertIn(0, room.disconnect_timeout_defeated)

        with (
            mock.patch.object(gtn, 'record_room_replay_keyframe'),
            mock.patch.object(gtn, '_broadcast_game_state_now'),
            mock.patch.object(gtn, 'emit_initial_pending_interaction'),
            mock.patch.object(gtn, 'broadcast_lobby'),
            mock.patch.object(gtn, 'admin_event'),
        ):
            gtn.start_game(room)

        self.assertTrue(engine._game_start_applied)
        self.assertEqual(engine.phase, 'action')
        self.assertFalse(engine.game_over)
        self.assertEqual(engine.players[0].health, 0)
        self.assertTrue(all(engine.players[i].health > 0 for i in range(1, 4)))
        for player in engine.players:
            card_total = sum(len(zone) for zone in (
                player.hand,
                player.deck,
                player.discard,
                player.exile,
                player.equipment,
            ))
            self.assertGreater(card_total, 0)

    def test_direct_setup_death_cannot_advance_an_unstarted_engine(self):
        room = self._partial_2v2_room()
        engine = room.engine
        phase_before = engine.phase
        current_before = engine.current_player
        health_before = engine.players[0].health

        changed = gtn._force_2v2_disconnect_death(room, 0, 'r18183-p0')

        self.assertFalse(changed)
        self.assertEqual(engine.phase, phase_before)
        self.assertEqual(engine.current_player, current_before)
        self.assertEqual(engine.players[0].health, health_before)

    def test_reconnect_timeout_schedules_normal_start_after_auto_draft(self):
        room = self._partial_2v2_room()
        old_sid = room.player_sids[0]
        room.disconnected_players[old_sid] = {
            'player_index': 0,
            'nickname': 'r18183-p0',
            'disconnect_attempt': 1,
            'reconnect_timeout': 120,
        }
        with gtn._lock:
            gtn.rooms[room.room_id] = room
        try:
            with (
                mock.patch.object(gtn, 'record_room_replay_action'),
                mock.patch.object(gtn, 'record_room_replay_keyframe'),
                mock.patch.object(gtn, 'schedule_pregame_state'),
                mock.patch.object(gtn, 'schedule_pregame_status_update'),
                mock.patch.object(gtn, 'schedule_start_game') as schedule_start,
                mock.patch.object(gtn, 'broadcast_lobby'),
                mock.patch.object(gtn, 'admin_event'),
            ):
                gtn.reconnect_timeout(room.room_id, old_sid)
        finally:
            with gtn._lock:
                gtn.rooms.pop(room.room_id, None)

        self.assertEqual(len(room.engine.draft_picks[0]), room.engine.draft_target_count(0))
        self.assertTrue(room.engine.player_ready[0])
        self.assertIn(0, room.disconnect_timeout_defeated)
        self.assertNotIn(old_sid, gtn._room_blocking_player_sids(room))
        schedule_start.assert_called_once_with(room)


if __name__ == '__main__':
    unittest.main()
