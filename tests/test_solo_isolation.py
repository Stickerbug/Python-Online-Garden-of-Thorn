import copy
import unittest
from unittest.mock import patch

import app
from runtime_budget import ActionWorkBudgetExceeded


class SoloIsolationTests(unittest.TestCase):
    def setUp(self):
        self.sid = f'solo-isolation-{id(self)}'
        self.engine = app.create_solo_engine(
            ['Basic'] * 15,
            ['Basic'] * 15,
        )
        app.solo_sessions[self.sid] = self.engine
        app.tutorial_sessions.discard(self.sid)

    def tearDown(self):
        with app._lock:
            app._drop_solo_session_locked(self.sid)

    def test_compact_snapshot_restores_state_and_reuses_static_loadout(self):
        shared_loadout = {'large_static_payload': 'x' * 200_000}
        self.engine.v2_loadout = shared_loadout
        original_health = self.engine.players[0].health

        snapshot = app._solo_engine_snapshot(self.engine)

        self.assertIsInstance(snapshot, bytes)
        self.assertLess(len(snapshot), 32_000)
        self.engine.players[0].health = 1
        self.engine.log.append('mutated')
        self.assertTrue(app._solo_restore_snapshot(self.engine, snapshot))
        self.assertEqual(self.engine.players[0].health, original_health)
        self.assertNotIn('mutated', self.engine.log)
        self.assertIs(self.engine.v2_loadout, shared_loadout)
        self.assertIs(self.engine.players[0]._draw_callback.__self__, self.engine)

        simulation = copy.deepcopy(self.engine)
        self.assertIs(simulation.v2_loadout, shared_loadout)
        self.assertIsNot(simulation.players[0], self.engine.players[0])
        self.assertIs(simulation.players[0]._draw_callback.__self__, simulation)

    def test_history_is_bounded_and_compact(self):
        for index in range(app.SOLO_HISTORY_LIMIT + 5):
            snapshot = app._solo_engine_snapshot(self.engine)
            app._solo_commit_undo_snapshot(self.engine, snapshot)
            self.engine.players[0].health = 100 - (index % 50)

        snapshots = list(self.engine._solo_undo_stack)
        self.assertEqual(len(snapshots), app.SOLO_HISTORY_LIMIT)
        self.assertTrue(all(isinstance(item, bytes) for item in snapshots))
        self.assertLess(sum(len(item) for item in snapshots), 2_000_000)

    def test_budget_overflow_rolls_back_without_enabling_budget_globally(self):
        original_budget = app.SOLO_ACTION_WORK_BUDGET
        original_health = self.engine.players[0].health
        app.SOLO_ACTION_WORK_BUDGET = 1_000
        try:
            def mutate_past_budget():
                self.engine.players[0].health = 1
                for _ in range(1_001):
                    self.engine._consume_action_work()

            with self.assertRaises(ActionWorkBudgetExceeded):
                app._solo_mutate_engine(self.sid, self.engine, mutate_past_budget)
        finally:
            app.SOLO_ACTION_WORK_BUDGET = original_budget

        self.assertEqual(self.engine.players[0].health, original_health)
        self.assertFalse(hasattr(self.engine, '_action_work_budget_remaining'))
        self.engine._consume_action_work(10**9)

    def test_duplicate_action_for_same_session_is_soft_rejected(self):
        first_lock = app._try_acquire_solo_action(self.sid, 'test_action')
        self.assertIsNotNone(first_lock)
        try:
            with patch.object(app, 'soft_reject') as reject:
                second_lock = app._try_acquire_solo_action(self.sid, 'test_action')
            self.assertIsNone(second_lock)
            reject.assert_called_once()
            self.assertEqual(reject.call_args.args[2], 'ACTION_BUSY')
        finally:
            first_lock.release()

    def test_cpu_worker_does_not_hold_the_global_state_lock(self):
        def probe_global_lock():
            acquired = app._lock.acquire(blocking=False)
            if acquired:
                app._lock.release()
            return acquired

        ok, acquired = app._solo_safe_cpu_call(
            self.sid,
            'test_global_lock_probe',
            probe_global_lock,
        )
        self.assertTrue(ok)
        self.assertTrue(acquired)

    def test_official_loadout_is_reused_between_guest_sessions(self):
        disabled_mods = ['test-disabled-mod.gtnmod']
        with app._SOLO_LOADOUT_CACHE_LOCK:
            app._SOLO_LOADOUT_CACHE.clear()
        with patch.object(app, 'build_mod_loadout', wraps=app.build_mod_loadout) as build:
            first = app._cached_official_solo_loadout(disabled_mods)
            second = app._cached_official_solo_loadout(disabled_mods)
        self.assertIs(first, second)
        self.assertEqual(build.call_count, 1)

    def test_solo_deck_limit_accepts_50_and_rejects_51_cards(self):
        valid_deck = ['Basic'] * 50
        self.assertEqual(app.validate_solo_deck_entries(valid_deck), valid_deck)
        with self.assertRaises(ValueError):
            app.validate_solo_deck_entries(valid_deck + ['Basic'])


class SoloSocketFlowTests(unittest.TestCase):
    def test_start_play_and_undo_round_trip(self):
        client = app.socketio.test_client(app.app)
        try:
            client.emit('solo_start', {
                'deck0': ['Basic'] * 15,
                'deck1': ['Basic'] * 15,
            })
            events = client.get_received()
            state = [
                event['args'][0]
                for event in events
                if event['name'] == 'solo_state'
            ][-1]
            initial_health = state['opponent']['health']
            card = state['you']['hand'][0]

            client.emit('solo_play_card', {
                'card_instance_id': card['instance_id'],
                'target_player_id': 1,
                'choice': {
                    'target_player': 1,
                    'target_player_id': 1,
                    'target_id': 1,
                },
            })
            events = client.get_received()
            state = [
                event['args'][0]
                for event in events
                if event['name'] == 'solo_state'
            ][-1]
            self.assertLess(state['opponent']['health'], initial_health)

            client.emit('solo_undo', {})
            events = client.get_received()
            state = [
                event['args'][0]
                for event in events
                if event['name'] == 'solo_state'
            ][-1]
            self.assertEqual(state['opponent']['health'], initial_health)
        finally:
            client.disconnect()

    def test_response_preview_is_prepared_without_losing_the_window(self):
        client = app.socketio.test_client(app.app)
        try:
            client.emit('solo_start', {
                'deck0': ['Basic'] * 15,
                'deck1': ['Bubble'] * 15,
            })
            events = client.get_received()
            state = [
                event['args'][0]
                for event in events
                if event['name'] == 'solo_state'
            ][-1]
            card = state['you']['hand'][0]

            client.emit('solo_play_card', {
                'card_instance_id': card['instance_id'],
                'target_player_id': 1,
                'choice': {
                    'target_player': 1,
                    'target_player_id': 1,
                    'target_id': 1,
                },
            })
            events = client.get_received()
            requests = [
                event['args'][0]
                for event in events
                if event['name'] == 'response_request'
            ]
            self.assertEqual(len(requests), 1)
            self.assertTrue(requests[0]['counter_cards'])
            self.assertIn('damage_prediction', requests[0])
        finally:
            client.disconnect()


if __name__ == '__main__':
    unittest.main()
