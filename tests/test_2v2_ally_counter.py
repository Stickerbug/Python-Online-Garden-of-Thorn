import unittest
import uuid
from types import SimpleNamespace
from unittest import mock

import app as gtn
from cards import CardInstance
from game_engine_2v2 import GameEngine2v2


def target_choice(target_id):
    return {
        'target_player': target_id,
        'target_player_id': target_id,
        'target_id': target_id,
    }


class AllyCounterEngineTests(unittest.TestCase):
    @staticmethod
    def engine_with_bubbles(*responder_ids):
        engine = GameEngine2v2()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.hand = []
            player.deck = []
            player.discard = []
            player.exile = []
            player.equipment = []
            player.health = 100
            player.max_health = 100
            player.elixir = 30
            player.magic = 30
            player.dodge = 0
            player.armor = 0
            player.custom_statuses = {}
            player.custom_vars = {}
        attack = CardInstance('Basic')
        engine.players[0].hand.append(attack)
        bubbles = {}
        for responder_id in responder_ids:
            bubble = CardInstance('Bubble')
            engine.players[responder_id].hand.append(bubble)
            bubbles[responder_id] = bubble
        return engine, attack, bubbles

    @staticmethod
    def play_attack(engine, attack, target_id=2):
        return engine.play_card(
            0,
            attack.instance_id,
            target_id,
            target_choice(target_id),
        )

    def test_all_other_living_players_can_receive_matching_counter_window(self):
        engine, attack, bubbles = self.engine_with_bubbles(0, 1, 2, 3)

        result = self.play_attack(engine, attack)

        self.assertTrue(result.get('needs_response'), result)
        responders = {
            int(entry['responder_id'])
            for entry in engine.pending_response['counter_cards']
        }
        self.assertEqual({1, 2, 3}, responders)
        self.assertNotIn(
            bubbles[0].instance_id,
            {int(entry['instance_id']) for entry in engine.pending_response['counter_cards']},
        )

    def test_each_responder_passes_independently_before_action_resolves(self):
        engine, attack, _bubbles = self.engine_with_bubbles(1, 2, 3)
        result = self.play_attack(engine, attack)
        self.assertTrue(result.get('needs_response'), result)
        pending = engine.pending_response

        first_pass = engine.handle_response(1, None)
        self.assertTrue(first_pass.get('needs_response'), first_pass)
        self.assertIs(pending, engine.pending_response)
        self.assertEqual(100, engine.players[2].health)
        self.assertEqual(
            {2, 3},
            {int(entry['responder_id']) for entry in pending['counter_cards']},
        )

        second_pass = engine.handle_response(2, None)
        self.assertTrue(second_pass.get('needs_response'), second_pass)
        self.assertIs(pending, engine.pending_response)
        self.assertEqual(100, engine.players[2].health)

        final_pass = engine.handle_response(3, None)
        self.assertTrue(final_pass.get('success'), final_pass)
        self.assertFalse(final_pass.get('needs_response', False), final_pass)
        self.assertIsNone(engine.pending_response)
        self.assertEqual(92, engine.players[2].health)

    def test_actual_counter_by_actor_teammate_resolves_once(self):
        engine, attack, bubbles = self.engine_with_bubbles(1, 2)
        result = self.play_attack(engine, attack)
        self.assertTrue(result.get('needs_response'), result)

        response = engine.handle_response(1, bubbles[1].instance_id)

        self.assertTrue(response.get('success'), response)
        self.assertIsNone(engine.pending_response)
        self.assertIn(bubbles[1], engine.players[1].discard)
        self.assertIn(bubbles[2], engine.players[2].hand)
        self.assertEqual(92, engine.players[2].health)

    def test_forged_actor_or_unlisted_card_cannot_consume_response_window(self):
        engine, attack, bubbles = self.engine_with_bubbles(1, 2)
        result = self.play_attack(engine, attack)
        self.assertTrue(result.get('needs_response'), result)
        pending = engine.pending_response
        unlisted = CardInstance('Bubble')
        engine.players[1].hand.append(unlisted)

        actor_result = engine.handle_response(0, bubbles[1].instance_id)
        forged_result = engine.handle_response(1, unlisted.instance_id)

        self.assertFalse(actor_result.get('success'), actor_result)
        self.assertFalse(forged_result.get('success'), forged_result)
        self.assertIs(pending, engine.pending_response)
        self.assertEqual(100, engine.players[2].health)
        self.assertIn(bubbles[1], engine.players[1].hand)

    def test_public_pending_response_only_contains_viewers_own_cards(self):
        engine, attack, bubbles = self.engine_with_bubbles(1, 2, 3)
        result = self.play_attack(engine, attack)
        self.assertTrue(result.get('needs_response'), result)

        for viewer_id in range(4):
            with self.subTest(viewer_id=viewer_id):
                public = engine._public_pending_response(viewer_id)
                entries = public.get('counter_cards') or []
                expected = [] if viewer_id == 0 else [bubbles[viewer_id].instance_id]
                self.assertEqual(expected, [int(entry['instance_id']) for entry in entries])
                self.assertEqual(viewer_id != 0, public.get('viewer_can_respond'))
                self.assertEqual([1, 2, 3], public.get('responder_ids'))

    def test_response_prediction_resolves_the_other_players_as_passed(self):
        engine, attack, bubbles = self.engine_with_bubbles(1, 2)
        result = self.play_attack(engine, attack)
        self.assertTrue(result.get('needs_response'), result)
        nonresponder_view = engine._public_pending_response(3)
        self.assertFalse(nonresponder_view.get('viewer_can_respond'))
        self.assertEqual([], nonresponder_view.get('counter_cards'))

        target_prediction = engine.build_response_damage_prediction(2, [bubbles[2]])
        ally_prediction = engine.build_response_damage_prediction(1, [bubbles[1]])

        self.assertEqual(8, target_prediction['no_counter']['total'])
        self.assertEqual(0, target_prediction['counters'][str(bubbles[2].instance_id)]['after']['total'])
        self.assertEqual(8, ally_prediction['no_counter']['total'])
        self.assertEqual(8, ally_prediction['counters'][str(bubbles[1].instance_id)]['after']['total'])

    def test_replay_response_requests_are_partitioned_by_responder(self):
        engine, attack, _bubbles = self.engine_with_bubbles(1, 2, 3)
        result = self.play_attack(engine, attack)
        self.assertTrue(result.get('needs_response'), result)
        room = SimpleNamespace(mode='2v2', engine=engine)

        requests = gtn.build_replay_pending_response_requests(room)

        self.assertEqual({1, 2, 3}, {int(item['responder_id']) for item in requests})
        for item in requests:
            responder_id = int(item['responder_id'])
            self.assertTrue(item['data']['counter_cards'])
            self.assertEqual(
                {responder_id},
                {
                    int(card['responder_id'])
                    for card in item['data']['counter_cards']
                },
            )

        engine.handle_response(1, None)
        remaining = gtn.build_replay_pending_response_requests(room)
        self.assertEqual({2, 3}, {int(item['responder_id']) for item in remaining})

    def test_disconnect_passes_only_unreachable_responders(self):
        engine, attack, _bubbles = self.engine_with_bubbles(1, 2, 3)
        result = self.play_attack(engine, attack)
        self.assertTrue(result.get('needs_response'), result)
        pending = engine.pending_response
        sids = [f'ally-counter-disconnect-{index}-{uuid.uuid4().hex}' for index in range(4)]
        room = SimpleNamespace(
            mode='2v2',
            engine=engine,
            room_id=987001,
            player_sids=sids,
            disconnected_players={},
        )
        gtn.players[sids[2]] = {'status': 'in_game'}
        try:
            self.assertTrue(gtn._resolve_pending_response_for_disconnect(room, 1))
            self.assertIs(pending, engine.pending_response)
            self.assertEqual(
                {2, 3},
                {int(entry['responder_id']) for entry in pending['counter_cards']},
            )
            self.assertEqual(100, engine.players[2].health)

            gtn.players.pop(sids[2], None)
            self.assertTrue(gtn._resolve_pending_response_for_disconnect(room, 2))
            self.assertIsNone(engine.pending_response)
            self.assertEqual(92, engine.players[2].health)
        finally:
            for sid in sids:
                gtn.players.pop(sid, None)

    def test_unreachable_response_window_passes_every_responder_once(self):
        engine, attack, _bubbles = self.engine_with_bubbles(1, 2, 3)
        result = self.play_attack(engine, attack)
        self.assertTrue(result.get('needs_response'), result)
        room = SimpleNamespace(
            mode='2v2',
            engine=engine,
            room_id=987002,
            player_sids=[f'ally-counter-offline-{index}-{uuid.uuid4().hex}' for index in range(4)],
            disconnected_players={},
        )

        self.assertTrue(gtn._auto_resolve_unreachable_pending_response(room, reason='test'))
        self.assertIsNone(engine.pending_response)
        self.assertEqual(92, engine.players[2].health)


class AllyCounterSocketTests(unittest.TestCase):
    def setUp(self):
        self.clients = [gtn.socketio.test_client(gtn.app) for _ in range(4)]
        self.sids = []
        for index, client in enumerate(self.clients):
            client.emit('login', {
                'nickname': f'AC{index}{uuid.uuid4().hex[:5]}',
                'mode': '2v2',
            })
            login_events = [
                event['args'][0]
                for event in client.get_received()
                if event['name'] == 'login_ok'
            ]
            self.assertTrue(login_events)
            self.sids.append(login_events[-1]['sid'])
        self.room_id = 986_000 + (id(self) % 10_000)
        self.room = gtn.GameRoom(
            self.room_id,
            self.sids,
            {'Basic', 'Bubble'},
            mode='2v2',
        )
        engine = self.room.engine
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.hand = []
            player.deck = []
            player.discard = []
            player.exile = []
            player.health = 100
            player.elixir = 30
            player.magic = 30
        self.attack = CardInstance('Basic')
        self.bubble = CardInstance('Bubble')
        engine.players[0].hand.append(self.attack)
        engine.players[1].hand.append(self.bubble)
        result = engine.play_card(
            0,
            self.attack.instance_id,
            2,
            target_choice(2),
        )
        self.assertTrue(result.get('needs_response'), result)
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

    def test_socket_actor_must_be_the_listed_counter_owner(self):
        context = gtn.room_event_context(self.room)
        with (
            mock.patch.object(gtn, 'broadcast_game_state'),
            mock.patch.object(gtn, 'emit_turn_timer_update'),
            mock.patch.object(gtn, 'record_room_replay_action'),
            mock.patch.object(gtn, 'record_valid_player_action'),
        ):
            self.clients[0].emit('response', {
                **context,
                'card_instance_id': self.bubble.instance_id,
            })
            gtn.socketio.sleep(0.02)

            rejected = [
                event['args'][0]
                for event in self.clients[0].get_received()
                if event['name'] == 'action_rejected'
            ]
            self.assertTrue(rejected)
            self.assertIsNotNone(self.room.engine.pending_response)
            self.assertIn(self.bubble, self.room.engine.players[1].hand)

            self.clients[1].emit('response', {
                **context,
                'card_instance_id': self.bubble.instance_id,
            })
            gtn.socketio.sleep(0.02)

        self.assertIsNone(self.room.engine.pending_response)
        self.assertIn(self.bubble, self.room.engine.players[1].discard)
        self.assertEqual(92, self.room.engine.players[2].health)


if __name__ == '__main__':
    unittest.main()
