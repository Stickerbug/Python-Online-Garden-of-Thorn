import pathlib
import types
import unittest
from unittest import mock

import app as gtn
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2


ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
APP_PY = (ROOT / 'app.py').read_text(encoding='utf-8')


def source_between(source, start, end):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


class FatedDrawTimeoutTests(unittest.TestCase):
    @staticmethod
    def _prepare_fated_draw(engine):
        player_id = 0
        engine.phase = 'draft'
        engine.opening_event_picks[player_id] = 5
        engine.player_draft_started[player_id] = True
        engine.player_ready[player_id] = False
        engine.opening_event_sub_choices[player_id] = None
        first_allowed = engine.fated_draw_pool_defs()[0]
        engine.draft_picks[player_id] = [first_allowed] * engine.draft_target_count(player_id)
        return player_id, first_allowed

    def test_timeout_selects_first_allowed_card_and_marks_player_ready(self):
        for engine_type in (GameEngine, GameEngine2v2):
            with self.subTest(engine=engine_type.__name__):
                engine = engine_type()
                player_id, first_allowed = self._prepare_fated_draw(engine)
                room = types.SimpleNamespace(
                    room_id=701,
                    engine=engine,
                    player_sids=[f'sid-{idx}' for idx in range(len(engine.players))],
                    pregame_deadlines={(player_id, 'sub_choice'): 1.0},
                )

                with (
                    mock.patch.object(gtn, 'record_room_replay_action'),
                    mock.patch.object(gtn, 'admin_event'),
                ):
                    changed = gtn._auto_submit_event_sub_choice_locked(room, player_id)

                self.assertTrue(changed)
                self.assertTrue(engine.player_ready[player_id])
                self.assertEqual(
                    engine.opening_event_sub_choices[player_id],
                    {'add_def_ids': [first_allowed]},
                )

    def test_timer_update_uses_current_status_after_timeout(self):
        engine = types.SimpleNamespace(get_player_status=mock.Mock(return_value='ready'))
        room = types.SimpleNamespace(room_id=702, player_sids=['sid-0'], engine=engine)
        timer_payload = {
            'pregame_timer_remaining': None,
            'pregame_timer_total': None,
            'pregame_timer_status': 'ready',
            'pregame_timer_paused': False,
        }
        with (
            mock.patch.object(gtn, '_pregame_timer_payload', return_value=timer_payload) as timer,
            mock.patch.object(gtn, '_watched_pregame_timer_payload', return_value={}),
            mock.patch.object(gtn, 'room_match_key', return_value='702:1'),
            mock.patch.object(gtn.socketio, 'emit') as emit,
        ):
            gtn.emit_pregame_timer_update(room, 0)

        timer.assert_called_once_with(room, 0, 'ready')
        payload = emit.call_args.args[1]
        self.assertEqual(payload['your_status'], 'ready')
        self.assertEqual(payload['pregame_timer_status'], 'ready')

    def test_client_closes_server_completed_choice_and_resyncs_sub_choice_phase(self):
        settle = source_between(
            GAME_JS,
            'function settleServerCompletedEventSubChoice(',
            'async function handleEventSubChoice(',
        )
        resync = source_between(
            GAME_JS,
            'function maybeRequestPregameStateResync(',
            'function updateSelectedEventsSummary(',
        )
        handler = source_between(
            GAME_JS,
            'async function handleEventSubChoice(',
            'async function showFatedDrawChoice(',
        )
        self.assertIn("String(data.your_status || '') !== 'ready'", settle)
        self.assertIn('activeKeyboardReorderController.forceCancel()', settle)
        self.assertIn("'event_sub_choice'", resync)
        self.assertIn('activeEventSubChoiceKey !== subChoiceKey', handler)

    def test_server_resync_recovers_client_that_missed_battle_start(self):
        handler = source_between(
            APP_PY,
            'def on_request_pregame_state(',
            "@socketio.on('request_game_state')",
        )
        self.assertIn("engine_phase in ('playing', 'action', 'draw', 'response', 'choice', 'game_over')", handler)
        self.assertIn('send_game_state_to(room, pidx)', handler)


if __name__ == '__main__':
    unittest.main()
