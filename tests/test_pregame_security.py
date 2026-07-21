import unittest

from cards import DECK_SIZE
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2


class PregameSecurityTests(unittest.TestCase):
    @staticmethod
    def _select_events(engine):
        engine.start_event_select_first()
        for player_id in range(len(engine.players)):
            option = engine.opening_event_options[player_id][0]
            assert engine.select_opening_event(player_id, option['id'])

    @classmethod
    def _complete_draft(cls, engine):
        cls._select_events(engine)
        for player_id in range(len(engine.players)):
            assert engine.start_draft_for_player(player_id)
            while len(engine.draft_picks[player_id]) < engine.draft_target_count(player_id):
                option = engine.draft_options[player_id][0]
                result = engine.draft_pick(player_id, option.def_id)
                success = result.get('success') if isinstance(result, dict) else result
                assert success
            if engine.opening_event_requires_sub_choice(player_id):
                engine.opening_event_sub_choices[player_id] = {}
            engine.player_ready[player_id] = True

    def test_empty_draft_cannot_start_normal_match(self):
        for engine_type in (GameEngine, GameEngine2v2):
            with self.subTest(engine=engine_type.__name__):
                engine = engine_type()
                self._select_events(engine)
                engine.opening_event_sub_choices = [{} for _ in engine.players]
                engine.player_ready = [True for _ in engine.players]

                self.assertFalse(engine.start_game())
                self.assertFalse(engine._game_start_applied)
                self.assertTrue(
                    engine._last_pregame_validation_error['reason'].startswith('draft_not_started:')
                )

    def test_partial_draft_cannot_start_normal_match(self):
        for engine_type in (GameEngine, GameEngine2v2):
            with self.subTest(engine=engine_type.__name__):
                engine = engine_type()
                self._select_events(engine)
                for player_id in range(len(engine.players)):
                    self.assertTrue(engine.start_draft_for_player(player_id))
                engine.player_ready = [True for _ in engine.players]

                self.assertFalse(engine.start_game())
                self.assertTrue(
                    engine._last_pregame_validation_error['reason'].startswith('draft_count_invalid:')
                )

    def test_draft_actions_require_reveal_confirmation(self):
        for engine_type in (GameEngine, GameEngine2v2):
            with self.subTest(engine=engine_type.__name__):
                engine = engine_type()
                self._select_events(engine)
                rerolls_before = engine.draft_rerolls[0]

                pick_result = engine.draft_pick(0, 'Basic')
                pick_success = pick_result.get('success') if isinstance(pick_result, dict) else pick_result
                reroll_result = engine.draft_reroll(0)
                reroll_success = reroll_result.get('success') if isinstance(reroll_result, dict) else reroll_result

                self.assertFalse(pick_success)
                self.assertFalse(reroll_success)
                self.assertEqual(engine.draft_picks[0], [])
                self.assertEqual(engine.draft_rerolls[0], rerolls_before)

    def test_complete_draft_starts_normal_match(self):
        for engine_type in (GameEngine, GameEngine2v2):
            with self.subTest(engine=engine_type.__name__):
                engine = engine_type()
                self._complete_draft(engine)
                valid, reason, details = engine.validate_pregame_ready()
                self.assertTrue(valid, (reason, details))
                self.assertTrue(engine.start_game())
                self.assertEqual(engine.phase, 'action')

    def test_random_deck_can_use_explicit_pregame_bypass(self):
        engine = GameEngine()
        engine.draft_picks = [['Basic'] * DECK_SIZE, ['Basic'] * DECK_SIZE]
        engine.player_ready = [True, True]
        engine.player_draft_started = [True, True]

        self.assertTrue(engine.start_game(skip_pregame_validation=True))
        self.assertEqual(engine.phase, 'action')


if __name__ == '__main__':
    unittest.main()
