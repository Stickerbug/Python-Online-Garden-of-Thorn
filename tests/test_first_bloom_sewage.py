import unittest
from unittest.mock import patch

from cards import CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2


class FirstBloomSewageTests(unittest.TestCase):
    @staticmethod
    def prepare_engine(engine, previous_types=None):
        previous_types = list(previous_types or [])
        engine.phase = 'draft'
        engine.player_draft_started[0] = True
        engine.draft_type_order = previous_types + ['bloom']
        engine.draft_picks[0] = ['Basic'] * len(previous_types)
        engine.draft_pool = [
            CardInstance(def_id='Rose'),
            CardInstance(def_id='Fries'),
            CardInstance(def_id='ManaOrb'),
            CardInstance(def_id='Sewage'),
        ]
        return engine

    def test_first_bloom_replaces_rightmost_option_in_both_engines(self):
        for engine_type, module_name in (
            (GameEngine, 'game_engine.generate_draft_options'),
            (GameEngine2v2, 'game_engine_2v2.generate_draft_options'),
        ):
            with self.subTest(engine=engine_type.__name__):
                engine = self.prepare_engine(engine_type(), previous_types=['thorn'])
                generated = [
                    CardInstance(def_id='Rose'),
                    CardInstance(def_id='Fries'),
                    CardInstance(def_id='ManaOrb'),
                ]
                with patch(module_name, return_value=generated):
                    engine._generate_draft_options_for_player(0)
                self.assertEqual(
                    [card.def_id for card in engine.draft_options[0]],
                    ['Rose', 'Fries', 'Sewage'],
                )

    def test_existing_sewage_is_not_moved_or_duplicated(self):
        engine = self.prepare_engine(GameEngine())
        generated = [
            CardInstance(def_id='Sewage'),
            CardInstance(def_id='Fries'),
            CardInstance(def_id='ManaOrb'),
        ]
        with patch('game_engine.generate_draft_options', return_value=generated):
            engine._generate_draft_options_for_player(0)
        self.assertEqual(
            [card.def_id for card in engine.draft_options[0]],
            ['Sewage', 'Fries', 'ManaOrb'],
        )

    def test_later_bloom_round_keeps_weighted_options(self):
        engine = self.prepare_engine(GameEngine(), previous_types=['bloom'])
        generated = [
            CardInstance(def_id='Rose'),
            CardInstance(def_id='Fries'),
            CardInstance(def_id='ManaOrb'),
        ]
        with patch('game_engine.generate_draft_options', return_value=generated):
            engine._generate_draft_options_for_player(0)
        self.assertEqual(
            [card.def_id for card in engine.draft_options[0]],
            ['Rose', 'Fries', 'ManaOrb'],
        )

    def test_reroll_of_first_bloom_returns_to_weighted_options(self):
        for engine_type, module_name in (
            (GameEngine, 'game_engine.generate_draft_options'),
            (GameEngine2v2, 'game_engine_2v2.generate_draft_options'),
        ):
            with self.subTest(engine=engine_type.__name__):
                engine = self.prepare_engine(engine_type())
                engine.draft_options[0] = [
                    CardInstance(def_id='Rose'),
                    CardInstance(def_id='Fries'),
                    CardInstance(def_id='Sewage'),
                ]
                generated = [
                    CardInstance(def_id='ManaOrb'),
                    CardInstance(def_id='Coffee'),
                    CardInstance(def_id='Chilli'),
                ]
                with patch(module_name, return_value=generated):
                    result = engine.draft_reroll(0)
                success = result.get('success') if isinstance(result, dict) else result
                self.assertTrue(success)
                self.assertEqual(
                    [card.def_id for card in engine.draft_options[0]],
                    ['ManaOrb', 'Coffee', 'Chilli'],
                )


if __name__ == '__main__':
    unittest.main()
