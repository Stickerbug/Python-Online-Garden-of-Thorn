import unittest
from pathlib import Path

from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'mods' / 'Hel Cards Addition.gtnmod'
CARD_ID = 'Domino'


class HelDominoPrecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mod = load_mod(str(PACKAGE))
        if mod.errors:
            raise AssertionError(mod.errors)
        cls.card_def = next(card for card in mod.cards if card.id == CARD_ID).to_card_def()

    def setUp(self):
        self.previous_def = CARD_DEFS.get(CARD_ID)
        CARD_DEFS[CARD_ID] = self.card_def

    def tearDown(self):
        if self.previous_def is None:
            CARD_DEFS.pop(CARD_ID, None)
        else:
            CARD_DEFS[CARD_ID] = self.previous_def

    @staticmethod
    def action_engine(engine_type):
        engine = engine_type()
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
        return engine

    @staticmethod
    def target_choice(target_id):
        return {
            'target_player': target_id,
            'target_player_id': target_id,
            'target_id': target_id,
        }

    def play_domino(self, engine, target_id, initial_luck):
        domino = CardInstance(CARD_ID)
        engine.players[0].hand.append(domino)
        engine._hel_set_luck_value(0, initial_luck)
        engine.players[target_id].dodge = 1
        choice = self.target_choice(target_id)
        if isinstance(engine, GameEngine2v2):
            result = engine.play_card(0, domino.instance_id, target_id, choice)
        else:
            result = engine.play_card(0, domino.instance_id, choice)
        return domino, result

    def test_critical_domino_gains_precision_before_dodge_in_both_modes(self):
        for engine_type, target_id in ((GameEngine, 1), (GameEngine2v2, 2)):
            with self.subTest(engine=engine_type.__name__):
                engine = self.action_engine(engine_type)

                domino, result = self.play_domino(engine, target_id, initial_luck=4)

                self.assertTrue(result.get('success'), result)
                self.assertEqual(90, engine.players[target_id].health)
                self.assertEqual(0, engine.players[target_id].dodge)
                self.assertEqual(0, engine._hel_luck_value(0))
                self.assertIn('precision', domino.instance_flags)
                self.assertIn(domino, engine.players[0].discard)

    def test_noncritical_domino_remains_fully_dodged(self):
        engine = self.action_engine(GameEngine)

        domino, result = self.play_domino(engine, 1, initial_luck=0)

        self.assertTrue(result.get('success'), result)
        self.assertEqual(100, engine.players[1].health)
        self.assertEqual(0, engine.players[1].dodge)
        self.assertEqual(2, engine._hel_luck_value(0))
        self.assertNotIn('precision', domino.instance_flags)

    def test_bubble_response_uses_domino_precision_when_the_hit_crits(self):
        engine = self.action_engine(GameEngine)
        domino = CardInstance(CARD_ID)
        bubble = CardInstance('Bubble')
        engine.players[0].hand.append(domino)
        engine.players[1].hand.append(bubble)
        engine._hel_set_luck_value(0, 4)

        pending = engine.play_card(0, domino.instance_id, self.target_choice(1))
        self.assertTrue(pending.get('needs_response'), pending)
        prediction = engine.build_response_damage_prediction(1, [bubble])
        self.assertEqual(18, prediction['no_counter']['total'])
        self.assertEqual(
            10,
            prediction['counters'][str(bubble.instance_id)]['after']['total'],
        )
        result = engine.handle_response(1, bubble.instance_id)

        self.assertTrue(result.get('success'), result)
        self.assertEqual(90, engine.players[1].health)
        self.assertEqual(0, engine.players[1].dodge)
        discarded_domino = next(
            card for card in engine.players[0].discard
            if card.instance_id == domino.instance_id
        )
        self.assertIn('precision', discarded_domino.instance_flags)
        self.assertIn(bubble, engine.players[1].discard)

    def test_critical_domino_keeps_precision_when_shield_absorbs_all_damage(self):
        engine = self.action_engine(GameEngine)
        engine.players[1].custom_statuses['jungle:shield'] = 99

        domino, result = self.play_domino(engine, 1, initial_luck=4)

        self.assertTrue(result.get('success'), result)
        self.assertEqual(100, engine.players[1].health)
        self.assertIn('precision', domino.instance_flags)


if __name__ == '__main__':
    unittest.main()
