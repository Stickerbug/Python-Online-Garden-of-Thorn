import copy
import unittest
from unittest.mock import Mock, patch

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

    def test_phelren_actions_do_not_compete_with_training_capacity(self):
        app.ai_test_sessions[self.sid] = {'thinking': False}
        self.assertTrue(app._SOLO_ACTION_CAPACITY.acquire(timeout=0.1))
        try:
            ok, value = app._solo_safe_cpu_call(
                self.sid,
                'phelren_capacity_probe',
                lambda: 'ready',
                offload=False,
            )
        finally:
            app._SOLO_ACTION_CAPACITY.release()
        self.assertTrue(ok)
        self.assertEqual(value, 'ready')

    def test_phelren_capacity_is_owned_inside_eventlet_tpool(self):
        app.ai_test_sessions[self.sid] = {
            'thinking': False,
            'session_id': 'phelren-tpool-ownership',
        }
        observed_inflight = []
        with patch(
            'eventlet.tpool.execute',
            side_effect=lambda runner: runner(),
        ) as execute:
            ok, value = app._solo_safe_cpu_call(
                self.sid,
                'phelren_tpool_probe',
                lambda: observed_inflight.append(
                    app._solo_action_inflight_snapshot()['phelren']
                ) or 'ready',
            )

        self.assertTrue(ok)
        self.assertEqual(value, 'ready')
        self.assertEqual(observed_inflight, [1])
        self.assertEqual(app._solo_action_inflight_snapshot()['phelren'], 0)
        execute.assert_called_once()

    def test_phelren_worker_releases_capacity_if_request_greenlet_disappears(self):
        class RequestCancelled(BaseException):
            pass

        app.ai_test_sessions[self.sid] = {
            'thinking': False,
            'session_id': 'phelren-cancelled-request',
        }
        capacity = Mock()
        capacity.acquire.return_value = True

        def execute_after_worker_finishes(runner):
            runner()
            raise RequestCancelled()

        with (
            patch.object(app, '_PHELREN_ACTION_CAPACITY', capacity),
            patch('eventlet.tpool.execute', side_effect=execute_after_worker_finishes),
        ):
            with self.assertRaises(RequestCancelled):
                app._solo_safe_cpu_call(
                    self.sid,
                    'phelren_cancelled_request_probe',
                    lambda: 'finished',
                )

        capacity.release.assert_called_once_with()
        self.assertEqual(app._solo_action_inflight_snapshot()['phelren'], 0)

    @unittest.skipIf(app.eventlet is None, 'Eventlet is not installed')
    def test_real_tpool_worker_survives_request_greenlet_cancellation(self):
        app.ai_test_sessions[self.sid] = {
            'thinking': False,
            'session_id': 'phelren-real-cancel',
        }
        entered = app._NATIVE_THREADING.Event()
        finish = app._NATIVE_THREADING.Event()

        def native_action():
            entered.set()
            finish.wait(5)
            return 'finished-after-cancel'

        request_greenlet = app.eventlet.spawn(
            app._solo_safe_cpu_call,
            self.sid,
            'phelren_real_cancel_probe',
            native_action,
        )
        try:
            for _ in range(200):
                if entered.is_set():
                    break
                app.eventlet.sleep(0.01)
            self.assertTrue(entered.is_set())
            request_greenlet.kill()
            finish.set()
            for _ in range(200):
                if app._solo_action_inflight_snapshot()['phelren'] == 0:
                    break
                app.eventlet.sleep(0.01)
            self.assertEqual(app._solo_action_inflight_snapshot()['phelren'], 0)
            self.assertTrue(app._PHELREN_ACTION_CAPACITY.acquire(timeout=0))
            app._PHELREN_ACTION_CAPACITY.release()
        finally:
            finish.set()
            request_greenlet.kill()

    def test_stale_terminal_generation_rotates_without_cross_releasing(self):
        entered = app._NATIVE_THREADING.Event()
        finish = app._NATIVE_THREADING.Event()
        results = []
        waiter_results = []
        waiter_executed = []
        with app._PHELREN_ACTION_STATE_LOCK:
            self.assertFalse(app._PHELREN_ACTION_INFLIGHT)
            original_capacity = app._PHELREN_ACTION_CAPACITY
            original_generation = app._PHELREN_ACTION_GENERATION
            original_token = app._PHELREN_ACTION_TOKEN
            original_retired_identities = set(app._PHELREN_RETIRED_IDENTITIES)
            original_recovery_count = app._PHELREN_CAPACITY_RECOVERY_COUNT
            original_last_recovery = app._PHELREN_CAPACITY_LAST_RECOVERY_AT
            old_capacity = app._NATIVE_THREADING.BoundedSemaphore(1)
            app._PHELREN_ACTION_CAPACITY = old_capacity
            app._PHELREN_ACTION_GENERATION = original_generation + 100
            app._PHELREN_CAPACITY_RECOVERY_COUNT = 0
            app._PHELREN_CAPACITY_LAST_RECOVERY_AT = 0.0

        identity = {
            'sid': 'retired-phelren-sid',
            'session_id': 'retired-phelren-session',
            'room_id': 987654321,
            'engine_id': -1,
        }

        def blocked_action():
            entered.set()
            finish.wait(5)
            return 'late-result'

        worker = app._NATIVE_THREADING.Thread(
            target=lambda: results.append(
                app._run_phelren_capacity_call(identity, 'retired_probe', blocked_action)
            ),
            daemon=True,
        )
        waiter = app._NATIVE_THREADING.Thread(
            target=lambda: waiter_results.append(
                app._run_phelren_capacity_call(
                    {**identity, 'sid': 'retired-phelren-waiter'},
                    'retired_waiter_probe',
                    lambda: waiter_executed.append(True),
                )
            ),
            daemon=True,
        )
        try:
            with (
                patch.object(app, 'PHELREN_MAX_CONCURRENT_ACTIONS', 1),
                patch.object(app, 'PHELREN_ACTION_STALE_SECONDS', 0.0),
                patch.object(app, 'PHELREN_CAPACITY_RECOVERY_COOLDOWN_SECONDS', 0.0),
                patch.object(app, 'PHELREN_CAPACITY_MAX_RECOVERIES', 2),
            ):
                worker.start()
                self.assertTrue(entered.wait(2))
                waiter.start()
                for _ in range(100):
                    if app._phelren_action_state_snapshot()['current_waiting_count'] == 1:
                        break
                    app.time.sleep(0.01)
                self.assertEqual(
                    app._phelren_action_state_snapshot()['current_waiting_count'],
                    1,
                )
                self.assertTrue(app._recover_stale_phelren_capacity())
                replacement = app._PHELREN_ACTION_CAPACITY
                self.assertIsNot(replacement, old_capacity)
                self.assertTrue(replacement.acquire(timeout=0))
                replacement.release()
                finish.set()
                worker.join(2)
                waiter.join(2)

            self.assertFalse(worker.is_alive())
            self.assertFalse(waiter.is_alive())
            self.assertEqual(results, [(app._PHELREN_CALL_ABANDONED, None)])
            self.assertEqual(waiter_results, [(app._PHELREN_CALL_ABANDONED, None)])
            self.assertEqual(waiter_executed, [])
            self.assertTrue(old_capacity.acquire(timeout=0))
            old_capacity.release()
            self.assertTrue(replacement.acquire(timeout=0))
            replacement.release()
        finally:
            finish.set()
            worker.join(2)
            waiter.join(2)
            with app._PHELREN_ACTION_STATE_LOCK:
                app._PHELREN_ACTION_INFLIGHT.clear()
                app._PHELREN_ACTION_CAPACITY = original_capacity
                app._PHELREN_ACTION_GENERATION = original_generation
                app._PHELREN_ACTION_TOKEN = original_token
                app._PHELREN_RETIRED_IDENTITIES.clear()
                app._PHELREN_RETIRED_IDENTITIES.update(original_retired_identities)
                app._PHELREN_CAPACITY_RECOVERY_COUNT = original_recovery_count
                app._PHELREN_CAPACITY_LAST_RECOVERY_AT = original_last_recovery

    def test_rekeyed_live_session_is_not_treated_as_an_orphan(self):
        app.ai_test_sessions[self.sid] = {
            'thinking': False,
            'session_id': 'stable-logical-session',
            'owner_disconnected': False,
        }
        with app._lock:
            identity = app._phelren_action_identity_locked(self.sid)
        identity['sid'] = 'obsolete-socket-id'

        with app._PHELREN_ACTION_STATE_LOCK:
            self.assertFalse(app._PHELREN_ACTION_INFLIGHT)
            original_capacity = app._PHELREN_ACTION_CAPACITY
            original_generation = app._PHELREN_ACTION_GENERATION
            original_token = app._PHELREN_ACTION_TOKEN
            original_recovery_count = app._PHELREN_CAPACITY_RECOVERY_COUNT
            original_last_recovery = app._PHELREN_CAPACITY_LAST_RECOVERY_AT
            test_capacity = app._NATIVE_THREADING.BoundedSemaphore(1)
            app._PHELREN_ACTION_CAPACITY = test_capacity
            app._PHELREN_ACTION_GENERATION = original_generation + 200
            app._PHELREN_CAPACITY_RECOVERY_COUNT = 0
            app._PHELREN_CAPACITY_LAST_RECOVERY_AT = 0.0

        token = None
        acquired = False
        try:
            token, capacity, generation = app._register_phelren_action_waiter(
                identity,
                'live_rekey_probe',
            )
            acquired = capacity.acquire(timeout=0)
            self.assertTrue(acquired)
            with app._PHELREN_ACTION_STATE_LOCK:
                record = app._PHELREN_ACTION_INFLIGHT[token]
                record['state'] = 'running'
                record['started_at'] = app.time.monotonic() - 60
            with (
                patch.object(app, 'PHELREN_MAX_CONCURRENT_ACTIONS', 1),
                patch.object(app, 'PHELREN_ACTION_STALE_SECONDS', 0.0),
                patch.object(app, 'PHELREN_CAPACITY_RECOVERY_COOLDOWN_SECONDS', 0.0),
                patch.object(app, 'PHELREN_CAPACITY_MAX_RECOVERIES', 2),
            ):
                self.assertFalse(app._recover_stale_phelren_capacity())
                self.assertEqual(app._PHELREN_ACTION_GENERATION, generation)
                self.assertIs(app._PHELREN_ACTION_CAPACITY, test_capacity)
        finally:
            with app._PHELREN_ACTION_STATE_LOCK:
                if token is not None:
                    app._PHELREN_ACTION_INFLIGHT.pop(token, None)
                if acquired:
                    test_capacity.release()
                app._PHELREN_ACTION_CAPACITY = original_capacity
                app._PHELREN_ACTION_GENERATION = original_generation
                app._PHELREN_ACTION_TOKEN = original_token
                app._PHELREN_CAPACITY_RECOVERY_COUNT = original_recovery_count
                app._PHELREN_CAPACITY_LAST_RECOVERY_AT = original_last_recovery

    def test_phelren_busy_message_does_not_refer_to_training(self):
        app.ai_test_sessions[self.sid] = {'thinking': False}
        unavailable = Mock()
        unavailable.acquire.return_value = False
        with (
            patch.object(app, '_PHELREN_ACTION_CAPACITY', unavailable),
            patch.object(app, 'soft_reject') as reject,
            patch('eventlet.tpool.execute', side_effect=lambda runner: runner()),
        ):
            ok, value = app._solo_safe_cpu_call(
                self.sid,
                'phelren_busy_probe',
                lambda: None,
                offload=False,
            )
        self.assertFalse(ok)
        self.assertIsNone(value)
        unavailable.acquire.assert_called_once_with(timeout=app.PHELREN_ACTION_QUEUE_WAIT_SECONDS)
        self.assertEqual(reject.call_args.kwargs['message'], 'Phelren 运算繁忙，请稍后重试')

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
