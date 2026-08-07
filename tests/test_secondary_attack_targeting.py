import unittest
from pathlib import Path
from unittest.mock import patch

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]


def make_counter(def_id, response_trigger):
    return CardDef(
        def_id,
        def_id,
        def_id,
        0,
        0,
        'guard',
        1,
        'Common',
        '',
        '',
        response_trigger=response_trigger,
    )


class SecondaryAttackTargetingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        desert = load_mod(str(ROOT / 'mods' / 'Desert Cards DLC.gtnmod'))
        arctic = load_mod(str(ROOT / 'mods' / 'Arctic Cards Addition.gtnmod'))
        if desert.errors or arctic.errors:
            raise AssertionError([*desert.errors, *arctic.errors])
        cls.marble_def = next(card for card in desert.cards if card.id == 'Marble').to_card_def()
        cls.carrot_def = next(card for card in arctic.cards if card.id == 'Carrot').to_card_def()

    def setUp(self):
        self.test_ids = {
            'Marble',
            'Carrot',
            'test:targeted_counter',
            'test:attack_counter',
        }
        self.previous_defs = {def_id: CARD_DEFS.get(def_id) for def_id in self.test_ids}
        CARD_DEFS['Marble'] = self.marble_def
        CARD_DEFS['Carrot'] = self.carrot_def
        CARD_DEFS['test:targeted_counter'] = make_counter('test:targeted_counter', 'targeted')
        CARD_DEFS['test:attack_counter'] = make_counter('test:attack_counter', 'thorn')

    def tearDown(self):
        for def_id, previous in self.previous_defs.items():
            if previous is None:
                CARD_DEFS.pop(def_id, None)
            else:
                CARD_DEFS[def_id] = previous

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
            player.elixir = 30
            player.magic = 30
            player.health = 100
            player.max_health = 100
        return engine

    def test_fission_marble_prepares_one_nonrepeating_bounce_per_hit(self):
        engine = self.action_engine(GameEngine2v2)
        marble = CardInstance('Marble')
        marble.fission_level = 2
        marble.fission_count = 1
        choice = {'target_player': 2, 'target_player_id': 2, 'target_id': 2}

        with patch('game_engine.random.choice', side_effect=lambda candidates: candidates[0]):
            prepared = engine._prepare_desert_marble_targets(0, marble, choice)

        targets = prepared['_desert_marble_targets']
        self.assertEqual(len(targets), 2)
        self.assertNotEqual(targets[0], 2)
        self.assertNotEqual(targets[1], targets[0])

    def test_fission_marble_applies_extra_damage_to_each_prepared_target(self):
        engine = self.action_engine(GameEngine2v2)
        marble = CardInstance('Marble')
        marble.fission_level = 2
        marble.fission_count = 1
        engine.players[0].hand = [marble]
        choice = {
            'target_player': 2,
            'target_player_id': 2,
            'target_id': 2,
            '_desert_marble_targets': [1, 3],
        }

        result = engine.play_card(0, marble.instance_id, 2, choice)

        self.assertTrue(result.get('success'))
        self.assertEqual(engine.players[2].health, 90)
        self.assertEqual(engine.players[1].health, 88)
        self.assertEqual(engine.players[3].health, 88)

    def test_ricochet_targets_can_offer_both_targeted_counter_types(self):
        engine = self.action_engine(GameEngine2v2)
        carrot = CardInstance('Carrot')
        carrot._paid_e_this_play = 1
        engine.players[2].hand = [
            CardInstance('test:targeted_counter'),
            CardInstance('test:attack_counter'),
        ]
        choice = {
            'target_player': 0,
            'target_player_id': 0,
            'target_id': 0,
            '_arctic_ricochet_targets': [2, 3, 1, 2],
        }

        target_ids = engine._response_target_ids_for_card(0, carrot, choice)
        pending = engine._build_pending_response_for_card(0, carrot, choice)

        self.assertEqual(target_ids, [0, 2, 3, 1])
        self.assertIsNotNone(pending)
        counters = {
            (entry['def_id'], entry['responder_id'])
            for entry in pending.get('counter_cards', [])
        }
        self.assertIn(('test:targeted_counter', 2), counters)
        self.assertIn(('test:attack_counter', 2), counters)

    def test_one_vs_one_ricochet_can_trigger_targeted_response(self):
        engine = self.action_engine(GameEngine)
        carrot = CardInstance('Carrot')
        carrot._paid_e_this_play = 1
        engine.players[1].hand = [CardInstance('test:targeted_counter')]
        choice = {
            'target_player': 0,
            'target_player_id': 0,
            'target_id': 0,
            '_arctic_ricochet_targets': [1, 0, 1, 0],
        }

        result = engine._check_card_response_after_choice(0, carrot, choice)

        self.assertIsNotNone(result)
        self.assertEqual(engine.pending_response.get('target_player_id'), 1)


if __name__ == '__main__':
    unittest.main()
