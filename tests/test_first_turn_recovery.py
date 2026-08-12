import pathlib
import types
import unittest
from unittest import mock

import app as gtn
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from game_engine_urf import GameEngineInfiniteFire


ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
APP_PY = (ROOT / 'app.py').read_text(encoding='utf-8')


def source_between(source, start, end):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


class FirstTurnClientRecoveryTests(unittest.TestCase):
    def test_battle_phase_clears_pregame_runtime_before_switching_phase(self):
        section = source_between(
            GAME_JS,
            "bindSocketEvent('game_phase'",
            "bindSocketEvent('draft_state'",
        )
        cleanup = section.index('prepareRuntimeForBattleEntry(previousPhase, nextPhase)')
        phase_write = section.index('phase = nextPhase')
        self.assertLess(cleanup, phase_write)
        self.assertIn("scheduleBattleStartupResync(data || {}, 'game_phase_playing')", section)

    def test_battle_entry_cancels_stale_setup_overlays_and_action_locks(self):
        section = source_between(
            GAME_JS,
            'function prepareRuntimeForBattleEntry(',
            'function syncPhaseChatMatch(',
        )
        self.assertIn('invalidateChoiceRequest()', section)
        self.assertIn('activeKeyboardReorderController.forceCancel()', section)
        self.assertIn("prompt.classList.contains('active')", section)
        self.assertIn('clearPendingServerAction()', section)
        self.assertIn("document.body.classList.remove('server-action-pending'", section)

    def test_authoritative_state_recovers_a_missing_choice_request(self):
        helper = source_between(
            GAME_JS,
            'function schedulePendingChoiceRecoveryFromState(',
            'let localPregameTimerSnapshot',
        )
        state_handler = source_between(
            GAME_JS,
            "bindSocketEvent('state_update'",
            "bindSocketEvent('turn_timer_update'",
        )
        solo_handler = source_between(
            GAME_JS,
            "bindSocketEvent('solo_state'",
            "bindSocketEvent('response_request'",
        )
        self.assertIn('beginChoiceRequest({', helper)
        self.assertIn('schedulePendingChoiceRecoveryFromState(data)', state_handler)
        self.assertIn('schedulePendingChoiceRecoveryFromState(data)', solo_handler)

    def test_authoritative_state_requests_a_missing_response_window(self):
        helper = source_between(
            GAME_JS,
            'function clearPendingResponseRecovery(',
            'function choiceRequestSignature(',
        )
        state_handler = source_between(
            GAME_JS,
            "bindSocketEvent('state_update'",
            "bindSocketEvent('turn_timer_update'",
        )
        response_handler = source_between(
            GAME_JS,
            "bindSocketEvent('response_request'",
            "bindSocketEvent('ally_consent_request'",
        )
        self.assertIn("requestFullGameState('pending_response_request_missing')", helper)
        self.assertIn('schedulePendingResponseRecoveryFromState(data)', state_handler)
        self.assertIn('clearPendingResponseRecovery()', response_handler)

    def test_stale_pregame_choice_does_not_submit_after_battle_started(self):
        section = source_between(
            GAME_JS,
            'async function handleEventSubChoice(',
            'async function showFatedDrawChoice(',
        )
        guard = section.index('if (isLiveBattleInteractionPhase(phase))')
        submit = section.rindex("socket.emit('submit_event_sub_choice'")
        self.assertLess(guard, submit)


class FirstTurnServerRecoveryTests(unittest.TestCase):
    def test_every_multiplayer_engine_enters_action_before_opening_turn_can_pause(self):
        engines = (
            (GameEngine(), {'skip_pregame_validation': True}),
            (GameEngine2v2(), {'skip_pregame_validation': True}),
            (GameEngineInfiniteFire(), {}),
        )
        for engine, kwargs in engines:
            entered_phases = []

            def pause_opening_turn(player_id, current_engine=engine):
                entered_phases.append(current_engine.phase)
                current_engine.current_player = player_id
                current_engine.pending_choice = {'player_id': player_id, 'choice_type': 'test'}

            engine._start_player_turn = pause_opening_turn
            with self.subTest(engine=type(engine).__name__):
                self.assertTrue(engine.start_game(**kwargs))
                self.assertEqual(entered_phases, ['action'])
                self.assertEqual(engine.phase, 'action')

    def test_timer_recovers_a_completed_start_left_in_playing_phase(self):
        engine = types.SimpleNamespace(
            phase='playing',
            current_player=1,
            players=[object(), object()],
            game_over=False,
            pending_response=None,
            pending_choice={'player_id': 1, 'choice_type': 'opening_choice'},
            pending_v2_ui=None,
            pending_ally_request=None,
        )
        room = types.SimpleNamespace(
            room_id=77,
            engine=engine,
            started_at=123.0,
            action_timer_player=None,
            action_timer_remaining=0,
            action_timer_last_tick=0,
            player_sids=[],
            disconnected_players={},
        )
        with mock.patch.object(gtn, 'admin_event') as event:
            current = gtn._sync_room_action_timer_after_state_change(room, now=456.0)

        self.assertEqual(current, 1)
        self.assertEqual(engine.phase, 'action')
        self.assertEqual(room.action_timer_player, 1)
        self.assertEqual(room.action_timer_remaining, float(gtn.ACTION_TURN_SECONDS))
        self.assertFalse(gtn._room_timer_payload(room)['turn_timer_paused'])
        event.assert_called_once()

    def test_initial_pending_response_is_emitted_after_game_start(self):
        room = types.SimpleNamespace(
            room_id=42,
            engine=types.SimpleNamespace(
                game_over=False,
                pending_response={'player_id': 0},
                pending_choice=None,
                pending_v2_ui=None,
            ),
        )
        with (
            mock.patch.object(gtn, 'emit_or_resolve_pending_response') as emit_response,
            mock.patch.object(gtn, 'emit_room_v2_ui_request') as emit_v2,
        ):
            gtn.emit_initial_pending_interaction(room)

        emit_response.assert_called_once_with(room, reason='game_start')
        emit_v2.assert_not_called()

    def test_initial_pending_v2_request_is_emitted_after_game_start(self):
        room = types.SimpleNamespace(
            room_id=43,
            engine=types.SimpleNamespace(
                game_over=False,
                pending_response=None,
                pending_choice=None,
                pending_v2_ui={'player_id': 0},
            ),
        )
        with (
            mock.patch.object(gtn, 'emit_or_resolve_pending_response') as emit_response,
            mock.patch.object(gtn, 'emit_room_v2_ui_request') as emit_v2,
        ):
            gtn.emit_initial_pending_interaction(room)

        emit_response.assert_not_called()
        emit_v2.assert_called_once_with(room)

    def test_direct_state_sync_recovers_every_pending_interaction_kind(self):
        section = source_between(
            APP_PY,
            'def send_game_state_to(',
            'def emit_rematch_state(',
        )
        self.assertIn("getattr(engine, 'pending_response', None)", section)
        self.assertIn('emit_pending_response_requests(room, only_player_index=pidx)', section)
        self.assertIn('emit_pending_choice_request(room)', section)
        self.assertIn('emit_room_v2_ui_request(room)', section)


if __name__ == '__main__':
    unittest.main()
