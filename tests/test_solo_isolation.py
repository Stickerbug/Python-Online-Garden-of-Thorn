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

    @unittest.skipIf(app.eventlet is None, 'Eventlet is not installed')
    def test_first_tpool_setup_cancellation_does_not_install_guard(self):
        from greenlet import GreenletExit

        meta = {
            'thinking': False,
            'session_id': 'phelren-first-tpool-setup-cancel',
        }
        app.ai_test_sessions[self.sid] = meta

        with patch('eventlet.tpool.setup', side_effect=GreenletExit()):
            with self.assertRaises(GreenletExit):
                app._solo_safe_cpu_call(
                    self.sid,
                    'phelren_first_setup_cancel',
                    lambda: {'success': True},
                )

        self.assertNotIn('_phelren_native_completion', meta)
        self.assertNotIn('_pending_human_replay_action', meta)

    @unittest.skipIf(app.eventlet is None, 'Eventlet is not installed')
    def test_human_record_guard_exists_before_bridge_and_is_reused(self):
        meta = {
            'thinking': False,
            'session_id': 'phelren-record-staging-guard',
            'human_player_id': 0,
            'ai_player_id': 1,
            'action_index': 0,
            'diagnostic_metadata': {},
            'diagnostic_finished': True,
        }
        app.ai_test_sessions[self.sid] = meta
        room = app._create_ai_test_replay_room(self.sid, self.engine, meta)
        meta['replay_room'] = room
        observed_completion = []

        worker = Mock()

        def record_external(*_args, **_kwargs):
            completion = meta.get('_phelren_native_completion')
            observed_completion.append(completion)
            self.assertIsInstance(completion, dict)
            self.assertTrue(completion.get('staging'))
            with patch.object(app, 'soft_reject') as reject:
                self.assertIsNone(
                    app._try_acquire_solo_action(
                        self.sid,
                        'phelren_staging_concurrent_retry',
                    )
                )
            reject.assert_called_once()
            return {'decision_id': 'human-stage-1'}

        worker.record_external.side_effect = record_external
        with (
            patch.object(app, 'get_local_ai_worker', return_value=worker),
            patch('eventlet.tpool.execute', side_effect=lambda runner: runner()),
        ):
            self.assertTrue(
                app._record_ai_test_human_action(
                    self.sid,
                    self.engine,
                    'end_turn',
                    {},
                )
            )
            completion = meta.get('_phelren_native_completion')
            self.assertIs(completion, observed_completion[0])
            self.assertTrue(completion.get('staging'))
            ok, value = app._solo_safe_cpu_call(
                self.sid,
                'phelren_staging_handoff',
                lambda: {'success': True},
            )

        self.assertTrue(ok)
        self.assertEqual(value, {'success': True})
        self.assertFalse(completion.get('staging'))
        self.assertNotIn('_phelren_native_completion', meta)
        self.assertNotIn('_pending_human_replay_action', meta)

    def test_guarded_state_send_does_not_read_or_finish_intermediate_engine(self):
        meta = {
            'thinking': False,
            'session_id': 'phelren-guarded-state-send',
            'human_player_id': 0,
            'ai_player_id': 1,
        }
        completion = app._new_phelren_call_completion()
        meta['_phelren_native_completion'] = completion
        app.ai_test_sessions[self.sid] = meta
        self.engine.game_over = True

        with (
            patch.object(self.engine, 'get_public_state') as public_state,
            patch.object(app, '_maybe_finish_ai_test_session') as finish_session,
            patch.object(app, '_solo_emit_pending_after_state') as emit_pending,
        ):
            self.assertFalse(app.send_solo_state_with_pending(self.sid))

        public_state.assert_not_called()
        finish_session.assert_not_called()
        emit_pending.assert_not_called()
        self.assertTrue(meta.get('_phelren_refresh_after_completion'))

    def test_guarded_spectator_state_is_deferred_without_reading_engine(self):
        meta = {
            'thinking': False,
            'session_id': 'phelren-guarded-spectator-state',
            'human_player_id': 0,
            'ai_player_id': 1,
        }
        app.ai_test_sessions[self.sid] = meta
        room = app._create_ai_test_replay_room(self.sid, self.engine, meta)
        meta['replay_room'] = room
        spectator_sid = f'{self.sid}-spectator'
        app.players[spectator_sid] = {
            'nickname': 'Spectator',
            'status': 'spectating',
            'spectating_room': room.room_id,
            'spectate_perspective': 0,
        }
        room.spectators.append(spectator_sid)
        meta['_phelren_native_completion'] = app._new_phelren_call_completion()

        try:
            with (
                patch.object(app, 'build_spectate_state') as build_state,
                patch.object(app, 'broadcast_game_state') as schedule_broadcast,
            ):
                self.assertFalse(app.send_spectate_state_to(room, spectator_sid))
                self.assertFalse(app._send_spectate_state_internal(spectator_sid, room))

            build_state.assert_not_called()
            self.assertEqual(schedule_broadcast.call_count, 2)
            self.assertTrue(meta.get('_phelren_refresh_after_completion'))

            meta.pop('_phelren_native_completion', None)
            action_lock = room.action_lock
            self.assertTrue(action_lock.acquire(blocking=False))
            try:
                with (
                    patch.object(app, 'build_spectate_state') as busy_build_state,
                    patch.object(app, 'broadcast_game_state') as busy_broadcast,
                ):
                    self.assertFalse(app.send_spectate_state_to(room, spectator_sid))
                busy_build_state.assert_not_called()
                busy_broadcast.assert_called_once_with(room)
            finally:
                action_lock.release()
        finally:
            app.players.pop(spectator_sid, None)

    def test_phelren_history_disable_follows_engine_across_socket_rekey(self):
        meta = {
            'thinking': False,
            'session_id': 'phelren-engine-history-disable',
            'human_player_id': 0,
            'ai_player_id': 1,
        }
        app.ai_test_sessions[self.sid] = meta
        app._create_ai_test_replay_room(self.sid, self.engine, meta)

        with patch.object(
            app,
            '_solo_history_enabled',
            side_effect=AssertionError('global sid lookup must be short-circuited'),
        ):
            snapshot = app._solo_capture_undo_snapshot(
                'obsolete-socket-after-rekey',
                self.engine,
            )

        self.assertIsNone(snapshot)
        self.assertTrue(getattr(self.engine, '_solo_history_disabled', False))

    def test_terminal_phelren_session_is_preserved_while_guard_is_pending(self):
        meta = {
            'thinking': False,
            'session_id': 'phelren-terminal-preserve-guard',
            'human_player_id': 0,
            'ai_player_id': 1,
        }
        app.ai_test_sessions[self.sid] = meta
        room = app._create_ai_test_replay_room(self.sid, self.engine, meta)
        meta['replay_room'] = room
        app.rooms[room.room_id] = room
        self.engine.game_over = True
        self.engine.phase = 'game_over'
        meta['_phelren_native_completion'] = app._new_phelren_call_completion()

        with app._lock:
            self.assertTrue(
                app._preserve_ai_test_session_for_reconnect_locked(self.sid)
            )

        self.assertTrue(meta.get('owner_disconnected'))
        self.assertIs(app.rooms.get(room.room_id), room)

    @unittest.skipIf(app.eventlet is None, 'Eventlet is not installed')
    def test_staging_owner_exit_clears_guard_and_unblocks_reconnect_wait(self):
        meta = {
            'thinking': False,
            'session_id': 'phelren-staging-owner-exit',
            'human_player_id': 0,
            'ai_player_id': 1,
            'action_index': 0,
            'diagnostic_metadata': {},
            'diagnostic_finished': True,
        }
        app.ai_test_sessions[self.sid] = meta
        room = app._create_ai_test_replay_room(self.sid, self.engine, meta)
        meta['replay_room'] = room
        app.rooms[room.room_id] = room
        entered = app.eventlet.event.Event()
        release_bridge = app.eventlet.event.Event()
        worker = Mock()

        def blocked_record(*_args, **_kwargs):
            entered.send(True)
            release_bridge.wait()
            return {'decision_id': 'never-committed'}

        worker.record_external.side_effect = blocked_record
        with patch.object(app, 'get_local_ai_worker', return_value=worker):
            owner = app.eventlet.spawn(
                app._record_ai_test_human_action,
                self.sid,
                self.engine,
                'end_turn',
                {},
            )
            self.assertTrue(entered.wait())
            completion = meta.get('_phelren_native_completion')
            self.assertIsInstance(completion, dict)
            self.assertTrue(completion.get('staging'))

            reconnect_wait = app.eventlet.spawn(
                app._wait_for_phelren_staging_handoff,
                room.room_id,
                1.0,
            )
            app.eventlet.sleep(0.05)
            self.assertFalse(reconnect_wait.dead)
            self.assertIn(self.sid, app.ai_test_sessions)

            owner.kill()
            for _ in range(200):
                if '_phelren_native_completion' not in meta:
                    break
                app.eventlet.sleep(0.01)

            self.assertNotIn('_phelren_native_completion', meta)
            self.assertNotIn('_pending_human_replay_action', meta)
            self.assertTrue(reconnect_wait.wait())
            release_bridge.send(True)

    @unittest.skipIf(app.eventlet is None, 'Eventlet is not installed')
    def test_done_finalizer_cancellation_retries_replay_exactly_once(self):
        from greenlet import GreenletExit

        meta = {
            'thinking': False,
            'session_id': 'phelren-finalizer-retry-token',
            'human_player_id': 0,
            'ai_player_id': 1,
            'diagnostic_finished': True,
        }
        app.ai_test_sessions[self.sid] = meta
        room = app._create_ai_test_replay_room(self.sid, self.engine, meta)
        meta['replay_room'] = room
        meta['_pending_human_replay_action'] = {
            'kind': 'end_turn',
            'actor': 0,
            'payload': {},
        }
        original_record = app.record_room_replay_action
        interrupted = False

        def append_then_cancel(*args, **kwargs):
            nonlocal interrupted
            original_record(*args, **kwargs)
            if not interrupted and len(args) > 1 and args[1] == 'end_turn':
                interrupted = True
                raise GreenletExit()

        with patch.object(
            app,
            'record_room_replay_action',
            side_effect=append_then_cancel,
        ):
            request_greenlet = app.eventlet.spawn(
                app._solo_safe_cpu_call,
                self.sid,
                'phelren_finalizer_retry_token',
                lambda: {'success': True},
            )
            try:
                request_greenlet.wait()
            except GreenletExit:
                pass
            for _ in range(300):
                if (
                    '_phelren_native_completion' not in meta
                    and '_pending_human_replay_action' not in meta
                ):
                    break
                app.eventlet.sleep(0.01)

        committed = [
            action
            for action in room._replay_actions
            if action.get('type') == 'end_turn'
            and (action.get('payload') or {}).get('_phelren_replay_commit_token')
        ]
        self.assertTrue(interrupted)
        self.assertEqual(len(committed), 1)
        self.assertNotIn('_phelren_native_completion', meta)
        self.assertNotIn('_pending_human_replay_action', meta)

    @unittest.skipIf(app.eventlet is None, 'Eventlet is not installed')
    def test_completion_claim_is_atomic_for_two_waiting_hub_consumers(self):
        meta = {
            'thinking': False,
            'session_id': 'phelren-atomic-finalizer-claim',
            'human_player_id': 0,
            'ai_player_id': 1,
        }
        completion = app._new_phelren_call_completion()
        completion['status'] = app._PHELREN_CALL_OK
        completion['value'] = {'success': True}
        completion['done'].set()
        meta['_phelren_native_completion'] = completion
        app.ai_test_sessions[self.sid] = meta
        with app._lock:
            identity = app._phelren_action_identity_locked(self.sid)

        with patch.object(
            app,
            '_finish_phelren_completion_guard',
            return_value=True,
        ) as finish_guard:
            # Force both consumers to reach the same occupied global lock.
            # Once released, only the first may atomically claim completion.
            with app._lock:
                first = app.eventlet.spawn(
                    app._finalize_phelren_call_completion,
                    identity,
                    completion,
                )
                second = app.eventlet.spawn(
                    app._finalize_phelren_call_completion,
                    identity,
                    completion,
                )
                app.eventlet.sleep(0)
                app.eventlet.sleep(0)

            self.assertTrue(first.wait())
            self.assertTrue(second.wait())

        finish_guard.assert_called_once_with(
            identity,
            completion,
            accepted=True,
        )
        self.assertTrue(completion.get('claimed'))

    @unittest.skipIf(app.eventlet is None, 'Eventlet is not installed')
    def test_preclaim_lock_wait_cancellation_schedules_independent_finalizer(self):
        meta = {
            'thinking': False,
            'session_id': 'phelren-preclaim-cancel-retry',
            'human_player_id': 0,
            'ai_player_id': 1,
            'diagnostic_finished': True,
        }
        app.ai_test_sessions[self.sid] = meta
        room = app._create_ai_test_replay_room(self.sid, self.engine, meta)
        meta['replay_room'] = room
        meta['_pending_human_replay_action'] = {
            'kind': 'end_turn',
            'actor': 0,
            'payload': {},
        }
        completion = app._new_phelren_call_completion()
        completion['status'] = app._PHELREN_CALL_OK
        completion['value'] = {'success': True}
        completion['done'].set()
        meta['_phelren_native_completion'] = completion
        with app._lock:
            identity = app._phelren_action_identity_locked(self.sid)

        # Cancel the original request while it is queued before owning the
        # completion claim.  Its exception path must launch an independent
        # retry that survives this greenlet and finalizes exactly once.
        with app._lock:
            original = app.eventlet.spawn(
                app._finalize_phelren_call_completion,
                identity,
                completion,
            )
            app.eventlet.sleep(0)
            app.eventlet.sleep(0)
            original.kill()

        for _ in range(300):
            if (
                '_phelren_native_completion' not in meta
                and '_pending_human_replay_action' not in meta
            ):
                break
            app.eventlet.sleep(0.01)

        committed = [
            action
            for action in room._replay_actions
            if action.get('type') == 'end_turn'
            and (action.get('payload') or {}).get('_phelren_replay_commit_token')
        ]
        self.assertEqual(len(committed), 1)
        self.assertTrue(completion.get('finalized'))
        self.assertNotIn('_phelren_native_completion', meta)
        self.assertNotIn('_pending_human_replay_action', meta)

    @unittest.skipIf(app.eventlet is None, 'Eventlet is not installed')
    def test_post_replay_refresh_cancellation_retries_until_guard_clears(self):
        from greenlet import GreenletExit

        meta = {
            'thinking': False,
            'session_id': 'phelren-post-replay-refresh-retry',
            'human_player_id': 0,
            'ai_player_id': 1,
            'diagnostic_finished': True,
            '_phelren_refresh_after_completion': True,
        }
        app.ai_test_sessions[self.sid] = meta
        room = app._create_ai_test_replay_room(self.sid, self.engine, meta)
        meta['replay_room'] = room
        meta['_pending_human_replay_action'] = {
            'kind': 'end_turn',
            'actor': 0,
            'payload': {},
        }
        refresh_calls = []

        def cancel_first_refresh(target_sid):
            refresh_calls.append(target_sid)
            if len(refresh_calls) == 1:
                raise GreenletExit()
            return True

        with (
            patch.object(
                app,
                'send_ai_test_pregame_state',
                side_effect=cancel_first_refresh,
            ),
            patch.object(app, 'schedule_ai_test_match_timer'),
            patch.object(app, 'schedule_ai_test_pregame'),
            patch.object(app, 'schedule_ai_test_turn'),
            patch.object(app, 'broadcast_game_state'),
            patch.object(app, 'broadcast_lobby'),
        ):
            request_greenlet = app.eventlet.spawn(
                app._solo_safe_cpu_call,
                self.sid,
                'phelren_post_replay_refresh_retry',
                lambda: {'success': True},
            )
            try:
                request_greenlet.wait()
            except GreenletExit:
                pass
            for _ in range(300):
                if '_phelren_native_completion' not in meta:
                    break
                app.eventlet.sleep(0.01)

        self.assertEqual(refresh_calls, [self.sid, self.sid])
        self.assertNotIn('_phelren_native_completion', meta)
        self.assertNotIn('_pending_human_replay_action', meta)

    @unittest.skipIf(app.eventlet is None, 'Eventlet is not installed')
    def test_transient_replay_failure_keeps_native_success_and_refreshes_later(self):
        meta = {
            'thinking': False,
            'session_id': 'phelren-transient-replay-retry',
            'human_player_id': 0,
            'ai_player_id': 1,
            'diagnostic_finished': True,
        }
        app.ai_test_sessions[self.sid] = meta
        room = app._create_ai_test_replay_room(self.sid, self.engine, meta)
        meta['replay_room'] = room
        meta['_pending_human_replay_action'] = {
            'kind': 'end_turn',
            'actor': 0,
            'payload': {},
        }
        original_record = app._record_ai_test_replay_action
        attempts = []

        def fail_once_then_record(*args, **kwargs):
            attempts.append(True)
            if len(attempts) == 1:
                return False
            return original_record(*args, **kwargs)

        with (
            patch.object(
                app,
                '_record_ai_test_replay_action',
                side_effect=fail_once_then_record,
            ),
            patch.object(app, 'send_ai_test_pregame_state', return_value=True),
            patch.object(app, 'schedule_ai_test_match_timer'),
            patch.object(app, 'schedule_ai_test_pregame'),
            patch.object(app, 'schedule_ai_test_turn'),
            patch.object(app, 'broadcast_game_state'),
            patch.object(app, 'broadcast_lobby'),
        ):
            ok, value = app._solo_safe_cpu_call(
                self.sid,
                'phelren_transient_replay_retry',
                lambda: {'success': True},
            )
            for _ in range(300):
                if '_phelren_native_completion' not in meta:
                    break
                app.eventlet.sleep(0.01)

        self.assertTrue(ok)
        self.assertEqual(value, {'success': True})
        self.assertEqual(len(attempts), 2)
        self.assertNotIn('_phelren_native_completion', meta)
        self.assertNotIn('_pending_human_replay_action', meta)

    def test_truncated_replay_does_not_leave_completion_guard(self):
        meta = {
            'thinking': False,
            'session_id': 'phelren-truncated-replay-finalize',
            'human_player_id': 0,
            'ai_player_id': 1,
            'diagnostic_finished': True,
        }
        app.ai_test_sessions[self.sid] = meta
        room = app._create_ai_test_replay_room(self.sid, self.engine, meta)
        meta['replay_room'] = room
        room._replay_actions = [
            {'type': 'existing', 'payload': {}}
            for _ in range(app.REPLAY_MAX_ACTIONS)
        ]
        meta['_pending_human_replay_action'] = {
            'kind': 'end_turn',
            'actor': 0,
            'payload': {},
        }

        with patch.object(app, '_record_ai_test_replay_action') as record_action:
            ok, value = app._solo_safe_cpu_call(
                self.sid,
                'phelren_truncated_replay_finalize',
                lambda: {'success': True},
            )

        self.assertTrue(ok)
        self.assertEqual(value, {'success': True})
        self.assertTrue(room._replay_truncated)
        record_action.assert_not_called()
        self.assertNotIn('_phelren_native_completion', meta)
        self.assertNotIn('_pending_human_replay_action', meta)

    @unittest.skipIf(app.eventlet is None, 'Eventlet is not installed')
    def test_phelren_replay_finalizes_on_hub_after_real_tpool_mutation(self):
        meta = {
            'thinking': False,
            'session_id': 'phelren-replay-thread-boundary',
            'human_player_id': 0,
            'ai_player_id': 1,
            'diagnostic_finished': True,
        }
        app.ai_test_sessions[self.sid] = meta
        meta['replay_room'] = app._create_ai_test_replay_room(
            self.sid,
            self.engine,
            meta,
        )
        meta['_pending_human_replay_action'] = {
            'kind': 'end_turn',
            'actor': 0,
            'payload': {},
        }
        request_thread_id = app._NATIVE_THREADING.get_ident()
        worker_thread_ids = []
        flush_thread_ids = []
        original_flush = app._flush_ai_test_human_replay_action

        def observed_flush(*args, **kwargs):
            flush_thread_ids.append(app._NATIVE_THREADING.get_ident())
            self.assertEqual(flush_thread_ids[-1], request_thread_id)
            return original_flush(*args, **kwargs)

        def mutate():
            worker_thread_ids.append(app._NATIVE_THREADING.get_ident())
            return {'success': True}

        with patch.object(
            app,
            '_flush_ai_test_human_replay_action',
            side_effect=observed_flush,
        ):
            ok, outcome = app._solo_safe_cpu_call(
                self.sid,
                'phelren_replay_thread_boundary',
                lambda: app._solo_mutate_engine(self.sid, self.engine, mutate),
            )

        self.assertTrue(ok)
        self.assertEqual(outcome[0], {'success': True})
        self.assertEqual(flush_thread_ids, [request_thread_id])
        self.assertEqual(len(worker_thread_ids), 1)
        self.assertNotEqual(worker_thread_ids[0], request_thread_id)
        self.assertNotIn('_pending_human_replay_action', meta)
        self.assertEqual(meta['replay_room']._replay_actions[-1]['type'], 'end_turn')
        self.assertEqual(app._solo_action_inflight_snapshot()['phelren'], 0)

    @unittest.skipIf(app.eventlet is None, 'Eventlet is not installed')
    def test_phelren_failed_native_mutation_clears_replay_on_hub(self):
        original_health = self.engine.players[0].health
        meta = {
            'thinking': False,
            'session_id': 'phelren-replay-failure-boundary',
            'human_player_id': 0,
            'ai_player_id': 1,
            'diagnostic_finished': True,
            '_pending_human_replay_action': {
                'kind': 'end_turn',
                'actor': 0,
                'payload': {},
            },
        }
        app.ai_test_sessions[self.sid] = meta
        request_thread_id = app._NATIVE_THREADING.get_ident()
        worker_thread_ids = []
        flush_thread_ids = []
        original_flush = app._flush_ai_test_human_replay_action

        def observed_flush(*args, **kwargs):
            flush_thread_ids.append(app._NATIVE_THREADING.get_ident())
            self.assertEqual(flush_thread_ids[-1], request_thread_id)
            return original_flush(*args, **kwargs)

        def fail_after_mutation():
            worker_thread_ids.append(app._NATIVE_THREADING.get_ident())
            self.engine.players[0].health = 1
            raise RuntimeError('expected native mutation failure')

        with (
            patch.object(
                app,
                '_flush_ai_test_human_replay_action',
                side_effect=observed_flush,
            ),
            patch.object(app.traceback, 'print_exc'),
            patch.object(app, 'admin_event'),
            patch.object(app.socketio, 'emit'),
        ):
            ok, outcome = app._solo_safe_cpu_call(
                self.sid,
                'phelren_replay_failure_boundary',
                lambda: app._solo_mutate_engine(
                    self.sid,
                    self.engine,
                    fail_after_mutation,
                ),
            )

        self.assertFalse(ok)
        self.assertIsNone(outcome)
        self.assertEqual(flush_thread_ids, [request_thread_id])
        self.assertEqual(len(worker_thread_ids), 1)
        self.assertNotEqual(worker_thread_ids[0], request_thread_id)
        self.assertNotIn('_pending_human_replay_action', meta)
        self.assertEqual(self.engine.players[0].health, original_health)
        self.assertEqual(app._solo_action_inflight_snapshot()['phelren'], 0)

    @unittest.skipIf(app.eventlet is None, 'Eventlet is not installed')
    def test_cancelled_request_replays_late_success_once_on_hub(self):
        meta = {
            'thinking': False,
            'session_id': 'phelren-cancelled-replay-success',
            'human_player_id': 0,
            'ai_player_id': 1,
            'diagnostic_finished': True,
        }
        app.ai_test_sessions[self.sid] = meta
        room = app._create_ai_test_replay_room(self.sid, self.engine, meta)
        meta['replay_room'] = room
        meta['_pending_human_replay_action'] = {
            'kind': 'end_turn',
            'actor': 0,
            'payload': {},
        }
        original_health = self.engine.players[0].health
        entered = app._NATIVE_THREADING.Event()
        finish = app._NATIVE_THREADING.Event()
        request_thread_id = app._NATIVE_THREADING.get_ident()
        flush_thread_ids = []
        original_flush = app._flush_ai_test_human_replay_action
        replay_count_before = sum(
            1 for action in room._replay_actions if action.get('type') == 'end_turn'
        )

        def observed_flush(*args, **kwargs):
            flush_thread_ids.append(app._NATIVE_THREADING.get_ident())
            self.assertEqual(flush_thread_ids[-1], request_thread_id)
            return original_flush(*args, **kwargs)

        def mutate_then_wait():
            self.engine.players[0].health = original_health - 1
            entered.set()
            finish.wait(5)
            return {'success': True}

        with patch.object(
            app,
            '_flush_ai_test_human_replay_action',
            side_effect=observed_flush,
        ):
            request_greenlet = app.eventlet.spawn(
                app._solo_safe_cpu_call,
                self.sid,
                'phelren_cancelled_replay_success',
                lambda: app._solo_mutate_engine(
                    self.sid,
                    self.engine,
                    mutate_then_wait,
                ),
            )
            try:
                for _ in range(200):
                    if entered.is_set():
                        break
                    app.eventlet.sleep(0.01)
                self.assertTrue(entered.is_set())
                request_greenlet.kill()
                self.assertIn('_pending_human_replay_action', meta)
                with patch.object(app, 'soft_reject') as reject:
                    self.assertIsNone(
                        app._try_acquire_solo_action(
                            self.sid,
                            'phelren_cancelled_replay_retry',
                        )
                    )
                reject.assert_called_once()
                finish.set()
                for _ in range(200):
                    if (
                        '_pending_human_replay_action' not in meta
                        and app._solo_action_inflight_snapshot()['phelren'] == 0
                    ):
                        break
                    app.eventlet.sleep(0.01)
            finally:
                finish.set()
                request_greenlet.kill()

        self.assertEqual(self.engine.players[0].health, original_health - 1)
        self.assertNotIn('_pending_human_replay_action', meta)
        self.assertEqual(flush_thread_ids, [request_thread_id])
        self.assertEqual(
            sum(1 for action in room._replay_actions if action.get('type') == 'end_turn'),
            replay_count_before + 1,
        )
        self.assertEqual(app._solo_action_inflight_snapshot()['phelren'], 0)

    @unittest.skipIf(app.eventlet is None, 'Eventlet is not installed')
    def test_cancelled_request_clears_late_native_failure_on_hub(self):
        meta = {
            'thinking': False,
            'session_id': 'phelren-cancelled-replay-failure',
            'human_player_id': 0,
            'ai_player_id': 1,
            'diagnostic_finished': True,
        }
        app.ai_test_sessions[self.sid] = meta
        room = app._create_ai_test_replay_room(self.sid, self.engine, meta)
        meta['replay_room'] = room
        meta['_pending_human_replay_action'] = {
            'kind': 'end_turn',
            'actor': 0,
            'payload': {},
        }
        original_health = self.engine.players[0].health
        entered = app._NATIVE_THREADING.Event()
        finish = app._NATIVE_THREADING.Event()
        request_thread_id = app._NATIVE_THREADING.get_ident()
        flush_thread_ids = []
        original_flush = app._flush_ai_test_human_replay_action
        replay_count_before = len(room._replay_actions)

        def observed_flush(*args, **kwargs):
            flush_thread_ids.append(app._NATIVE_THREADING.get_ident())
            self.assertEqual(flush_thread_ids[-1], request_thread_id)
            return original_flush(*args, **kwargs)

        def mutate_then_fail():
            self.engine.players[0].health = 1
            entered.set()
            finish.wait(5)
            raise RuntimeError('expected late native failure')

        with patch.object(
            app,
            '_flush_ai_test_human_replay_action',
            side_effect=observed_flush,
        ):
            request_greenlet = app.eventlet.spawn(
                app._solo_safe_cpu_call,
                self.sid,
                'phelren_cancelled_replay_failure',
                lambda: app._solo_mutate_engine(
                    self.sid,
                    self.engine,
                    mutate_then_fail,
                ),
            )
            try:
                for _ in range(200):
                    if entered.is_set():
                        break
                    app.eventlet.sleep(0.01)
                self.assertTrue(entered.is_set())
                request_greenlet.kill()
                self.assertIn('_pending_human_replay_action', meta)
                finish.set()
                for _ in range(200):
                    if (
                        '_pending_human_replay_action' not in meta
                        and app._solo_action_inflight_snapshot()['phelren'] == 0
                    ):
                        break
                    app.eventlet.sleep(0.01)
            finally:
                finish.set()
                request_greenlet.kill()

        self.assertEqual(self.engine.players[0].health, original_health)
        self.assertNotIn('_pending_human_replay_action', meta)
        self.assertEqual(flush_thread_ids, [request_thread_id])
        self.assertEqual(len(room._replay_actions), replay_count_before)
        self.assertEqual(app._solo_action_inflight_snapshot()['phelren'], 0)

    @unittest.skipIf(app.eventlet is None, 'Eventlet is not installed')
    def test_native_completion_replays_once_after_session_rekey(self):
        new_sid = f'{self.sid}-reconnected'
        meta = {
            'thinking': False,
            'session_id': 'phelren-rekey-replay-success',
            'human_player_id': 0,
            'ai_player_id': 1,
            'diagnostic_finished': True,
        }
        app.ai_test_sessions[self.sid] = meta
        room = app._create_ai_test_replay_room(self.sid, self.engine, meta)
        meta['replay_room'] = room
        meta['_pending_human_replay_action'] = {
            'kind': 'end_turn',
            'actor': 0,
            'payload': {},
        }
        entered = app._NATIVE_THREADING.Event()
        finish = app._NATIVE_THREADING.Event()
        replay_count_before = sum(
            1 for action in room._replay_actions if action.get('type') == 'end_turn'
        )

        def mutate_then_wait():
            entered.set()
            finish.wait(5)
            return {'success': True}

        request_greenlet = app.eventlet.spawn(
            app._solo_safe_cpu_call,
            self.sid,
            'phelren_rekey_replay_success',
            lambda: app._solo_mutate_engine(
                self.sid,
                self.engine,
                mutate_then_wait,
            ),
        )
        try:
            for _ in range(200):
                if entered.is_set():
                    break
                app.eventlet.sleep(0.01)
            self.assertTrue(entered.is_set())
            with app._lock:
                self.assertTrue(
                    app._rekey_ai_test_session_locked(
                        self.sid,
                        new_sid,
                        room,
                        0,
                    )
                )
            with patch.object(app, 'soft_reject') as reject:
                self.assertIsNone(
                    app._try_acquire_solo_action(
                        new_sid,
                        'phelren_rekey_concurrent_retry',
                    )
                )
            reject.assert_called_once()
            finish.set()
            ok, outcome = request_greenlet.wait()

            self.assertTrue(ok)
            self.assertEqual(outcome[0], {'success': True})
            self.assertIs(app.ai_test_sessions.get(new_sid), meta)
            self.assertNotIn('_pending_human_replay_action', meta)
            self.assertEqual(
                sum(
                    1 for action in room._replay_actions
                    if action.get('type') == 'end_turn'
                ),
                replay_count_before + 1,
            )
        finally:
            finish.set()
            request_greenlet.kill()
            with app._lock:
                app._drop_solo_session_locked(new_sid)

    @unittest.skipIf(app.eventlet is None, 'Eventlet is not installed')
    def test_completed_native_result_wins_over_tpool_delivery_error(self):
        meta = {
            'thinking': False,
            'session_id': 'phelren-tpool-delivery-recovery',
            'human_player_id': 0,
            'ai_player_id': 1,
            'diagnostic_finished': True,
        }
        app.ai_test_sessions[self.sid] = meta
        room = app._create_ai_test_replay_room(self.sid, self.engine, meta)
        meta['replay_room'] = room
        meta['_pending_human_replay_action'] = {
            'kind': 'end_turn',
            'actor': 0,
            'payload': {},
        }
        original_health = self.engine.players[0].health
        original_execute = app.eventlet.tpool.execute
        replay_count_before = sum(
            1 for action in room._replay_actions if action.get('type') == 'end_turn'
        )

        def fail_after_native_completion(runner):
            original_execute(runner)
            raise RuntimeError('expected tpool delivery failure')

        def mutate():
            self.engine.players[0].health = original_health - 1
            return {'success': True}

        with (
            patch(
                'eventlet.tpool.execute',
                side_effect=fail_after_native_completion,
            ),
            patch.object(app, 'admin_event') as admin_event,
            patch.object(app.socketio, 'emit') as socket_emit,
        ):
            ok, outcome = app._solo_safe_cpu_call(
                self.sid,
                'phelren_tpool_delivery_recovery',
                lambda: app._solo_mutate_engine(self.sid, self.engine, mutate),
            )

        self.assertTrue(ok)
        self.assertEqual(outcome[0], {'success': True})
        self.assertEqual(self.engine.players[0].health, original_health - 1)
        self.assertNotIn('_pending_human_replay_action', meta)
        self.assertNotIn('_phelren_native_completion', meta)
        self.assertEqual(
            sum(1 for action in room._replay_actions if action.get('type') == 'end_turn'),
            replay_count_before + 1,
        )
        self.assertTrue(
            any(
                'tpool delivery error' in str(call.args[1])
                for call in admin_event.call_args_list
                if len(call.args) > 1
            )
        )
        socket_emit.assert_not_called()

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
        app.ai_test_sessions[self.sid] = {
            'thinking': False,
            'session_id': 'phelren-busy-replay-cleanup',
            'diagnostic_finished': True,
            '_pending_human_replay_action': {
                'kind': 'end_turn',
                'actor': 0,
                'payload': {},
            },
        }
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
        self.assertNotIn(
            '_pending_human_replay_action',
            app.ai_test_sessions[self.sid],
        )

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
