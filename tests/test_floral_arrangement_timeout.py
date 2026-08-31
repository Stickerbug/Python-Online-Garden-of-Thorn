import inspect
import types
import unittest
from unittest import mock

import app as gtn
from cards import DECK_SIZE
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2


class FloralArrangementTimeoutTests(unittest.TestCase):
    def setUp(self):
        self.timeout_patch = mock.patch.multiple(
            gtn,
            EVENT_SUB_CHOICE_TIMEOUT_SECONDS=60,
            FLORAL_ARRANGEMENT_TIMEOUT_BONUS_SECONDS=30,
        )
        self.timeout_patch.start()

    def tearDown(self):
        self.timeout_patch.stop()

    @staticmethod
    def _room(engine):
        return types.SimpleNamespace(
            room_id=811,
            mode='1v1',
            engine=engine,
            player_sids=[f'sid-{index}' for index in range(len(engine.players))],
            disconnected_players={},
            pregame_deadlines={},
            record_pregame_stats=False,
        )

    def test_only_floral_arrangement_receives_the_extra_thirty_seconds(self):
        for engine_type in (GameEngine, GameEngine2v2):
            with self.subTest(engine=engine_type.__name__):
                engine = engine_type()
                room = self._room(engine)
                engine.opening_event_picks[0] = 11
                self.assertEqual(gtn._pregame_timeout_for_status('sub_choice', room, 0), 90)

                engine.opening_event_picks[0] = 5
                self.assertEqual(gtn._pregame_timeout_for_status('sub_choice', room, 0), 60)

        self.assertEqual(gtn._pregame_timeout_for_status('sub_choice'), 60)
        self.assertEqual(gtn._pregame_timeout_for_status('event_select'), gtn.EVENT_SELECT_TIMEOUT_SECONDS)

    def test_timer_payload_exposes_ninety_seconds_without_rearming_on_resend(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = '11'
        room = self._room(engine)

        first = gtn._pregame_timer_payload(room, 0, 'sub_choice', now=100.0)
        deadline = room.pregame_deadlines[(0, 'sub_choice')]
        second = gtn._pregame_timer_payload(room, 0, 'sub_choice', now=121.0)

        self.assertEqual(first['pregame_timer_total'], 90)
        self.assertEqual(first['pregame_timer_remaining'], 90)
        self.assertEqual(second['pregame_timer_total'], 90)
        self.assertEqual(second['pregame_timer_remaining'], 69)
        self.assertEqual(room.pregame_deadlines[(0, 'sub_choice')], deadline)

    def test_disconnect_pause_shifts_the_existing_deadline_instead_of_rearming_it(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = 11
        room = self._room(engine)
        gtn._pregame_timer_payload(room, 0, 'sub_choice', now=100.0)
        room.pregame_pause_last_tick = 100.0

        gtn._pause_pregame_deadlines_locked(room, now=130.0)
        resumed = gtn._pregame_timer_payload(room, 0, 'sub_choice', now=130.0)

        self.assertEqual(room.pregame_deadlines[(0, 'sub_choice')], 220.0)
        self.assertEqual(resumed['pregame_timer_total'], 90)
        self.assertEqual(resumed['pregame_timer_remaining'], 90)

    def test_floral_arrangement_timeout_still_auto_submits_the_full_order(self):
        engine = GameEngine()
        engine.phase = 'draft'
        engine.opening_event_picks[0] = 11
        engine.player_draft_started[0] = True
        engine.player_ready[0] = False
        engine.opening_event_sub_choices[0] = None
        engine.draft_picks[0] = ['Basic'] * DECK_SIZE
        room = self._room(engine)
        room.pregame_deadlines[(0, 'sub_choice')] = 1.0

        with (
            mock.patch.object(gtn, 'record_room_replay_action') as replay,
            mock.patch.object(gtn, 'admin_event'),
        ):
            changed = gtn._auto_submit_event_sub_choice_locked(room, 0)

        self.assertTrue(changed)
        self.assertTrue(engine.player_ready[0])
        self.assertEqual(
            engine.opening_event_sub_choices[0],
            {'deck_order_def_ids': ['Basic'] * DECK_SIZE},
        )
        self.assertNotIn((0, 'sub_choice'), room.pregame_deadlines)
        replay.assert_called_once()

    def test_multiplayer_timer_worker_uses_the_shared_timeout_resolver(self):
        source = inspect.getsource(gtn._room_timer_worker)
        self.assertIn('_pregame_timeout_for_status(status, room, pidx)', source)
        self.assertNotIn('timeout = EVENT_SUB_CHOICE_TIMEOUT_SECONDS', source)


if __name__ == '__main__':
    unittest.main()
