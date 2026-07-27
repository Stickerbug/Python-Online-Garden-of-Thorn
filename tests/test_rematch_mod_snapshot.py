import unittest
from unittest import mock

import app as gtn


class RematchModSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.original_players = dict(gtn.players)
        gtn.players.clear()
        self.runtime_filter = mock.patch.object(
            gtn,
            'apply_runtime_content_filter',
            side_effect=lambda card_ids, mode=None: set(card_ids or []),
        )
        self.runtime_filter.start()

    def tearDown(self):
        self.runtime_filter.stop()
        gtn.players.clear()
        gtn.players.update(self.original_players)

    @staticmethod
    def player_meta(allowed):
        return {
            'nickname': 'SnapshotPlayer',
            'disabled_mods': ['Garden Cards Addition.gtnmod'],
            'mods_hash': 'mods-before-rematch',
            'loadout_hash': 'loadout-before-rematch',
            'v2_loadout_hash': 'v2-before-rematch',
            'v2_load_order': ['vanilla'],
            'mods_list': ['Garden of Thorn Vanilla Cards'],
            'allowed_card_ids': set(allowed),
            'mod_source': 'official',
        }

    def test_rematch_ignores_mutated_player_and_engine_card_pools(self):
        original_allowed = {'Basic', 'Rose'}
        player = self.player_meta(original_allowed)
        gtn.players['player-a'] = player
        room = gtn.GameRoom(901, ['player-a', 'player-b'], original_allowed, mode='1v1')
        gtn.capture_room_match_loadout(room, player)

        player['allowed_card_ids'] = {'UnexpectedModCard'}
        player['disabled_mods'] = []
        room.engine.allowed_card_ids = {'AnotherUnexpectedCard'}

        allowed, profile = gtn.resolve_room_rematch_loadout(room)

        self.assertEqual(allowed, original_allowed)
        self.assertEqual(profile['disabled_mods'], ['Garden Cards Addition.gtnmod'])
        self.assertEqual(gtn.room_mod_payload(room)['loadout_hash'], 'loadout-before-rematch')

    def test_legacy_room_recovers_snapshot_from_existing_engine(self):
        player = self.player_meta({'PlayerTemporaryCard'})
        gtn.players['player-a'] = player
        room = gtn.GameRoom(902, ['player-a', 'player-b'], {'OriginalRoomCard'}, mode='1v1')
        room.match_allowed_card_ids = None
        room.match_mod_profile = {}

        allowed, profile = gtn.resolve_room_rematch_loadout(room)

        self.assertEqual(allowed, {'OriginalRoomCard'})
        self.assertEqual(room.match_allowed_card_ids, frozenset({'OriginalRoomCard'}))
        self.assertEqual(profile['allowed_card_ids'], {'OriginalRoomCard'})

    def test_missing_room_and_player_snapshot_rejects_rematch(self):
        room = gtn.GameRoom(903, ['missing-a', 'missing-b'], None, mode='1v1')
        room.match_allowed_card_ids = None
        room.match_mod_profile = {}
        room.engine.allowed_card_ids = None

        with self.assertRaisesRegex(ValueError, '缺少本局卡池快照'):
            gtn.resolve_room_rematch_loadout(room)

    def test_socket_rematch_builds_new_engine_from_room_snapshot(self):
        clients = [gtn.socketio.test_client(gtn.app), gtn.socketio.test_client(gtn.app)]
        room_id = 904
        try:
            sids = []
            for index, client in enumerate(clients):
                client.emit('login', {
                    'nickname': f'RematchSnapshot{index}',
                    'mode': '1v1',
                })
                login_events = [
                    event['args'][0]
                    for event in client.get_received()
                    if event['name'] == 'login_ok'
                ]
                self.assertTrue(login_events)
                sids.append(login_events[-1]['sid'])

            original_allowed = {'Basic', 'Rose'}
            with gtn._lock:
                room = gtn.GameRoom(room_id, sids, original_allowed, mode='1v1')
                room.engine.player_names = ['RematchSnapshot0', 'RematchSnapshot1']
                room.engine.phase = 'game_over'
                room.engine.game_over = True
                gtn.capture_room_match_loadout(room, gtn.players[sids[0]])
                room.engine.allowed_card_ids = {'MutatedOldEngineCard'}
                gtn.players[sids[0]]['allowed_card_ids'] = {'UnexpectedPlayerCard'}
                gtn.players[sids[0]]['disabled_mods'] = []
                for sid in sids:
                    gtn.players[sid]['room_id'] = room_id
                    gtn.players[sid]['status'] = 'in_game'
                gtn.rooms[room_id] = room

            with (
                mock.patch.object(gtn, 'runtime_card_pool_issue', return_value=''),
                mock.patch.object(gtn, 'send_pregame_state'),
                mock.patch.object(gtn, 'record_room_replay_keyframe'),
            ):
                clients[0].emit('rematch', {})
                clients[1].emit('rematch', {})

            self.assertEqual(gtn.rooms[room_id].engine.allowed_card_ids, original_allowed)
            self.assertEqual(
                gtn.rooms[room_id].match_allowed_card_ids,
                frozenset(original_allowed),
            )
        finally:
            with gtn._lock:
                gtn.rooms.pop(room_id, None)
                for player in gtn.players.values():
                    if player.get('room_id') == room_id:
                        player['room_id'] = None
                        player['status'] = 'lobby'
            for client in clients:
                if client.is_connected():
                    client.disconnect()


if __name__ == '__main__':
    unittest.main()
