import unittest

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import GameEngine


def make_card_def(def_id, card_type, *, v2_events=None):
    return CardDef(
        def_id,
        def_id,
        def_id,
        0,
        0,
        card_type,
        1,
        'Common',
        '',
        '',
        v2_events=dict(v2_events or {}),
    )


class CardPowerRuleTests(unittest.TestCase):
    def setUp(self):
        self.test_ids = {'jurassic:amber', 'sewers:broccoli'}
        self.previous_defs = {key: CARD_DEFS.get(key) for key in self.test_ids}
        CARD_DEFS['jurassic:amber'] = make_card_def(
            'jurassic:amber',
            'thorn',
            v2_events={
                'on_enter_hand': {
                    'steps': [{'op': 'jurassic_clear_self_power'}],
                },
            },
        )
        CARD_DEFS['sewers:broccoli'] = make_card_def('sewers:broccoli', 'thorn')

    def tearDown(self):
        for key, old_value in self.previous_defs.items():
            if old_value is None:
                CARD_DEFS.pop(key, None)
            else:
                CARD_DEFS[key] = old_value

    def test_amber_clears_power_when_entering_hand(self):
        engine = GameEngine()
        card = CardInstance('jurassic:amber')
        card.power_value = -9
        card.instance_flags.add('power')

        engine.players[0].add_to_hand(card)

        self.assertEqual(card.power_value, 0)
        self.assertNotIn('power', card.instance_flags)

    def test_broccoli_power_only_applies_to_first_attack(self):
        engine = GameEngine()
        card = CardInstance('sewers:broccoli')
        card.power_value = 6
        card.instance_flags.add('power')
        card._sewers_was_countered_this_play = True
        engine.players[1].health = 100

        engine._atomic_sewers_broccoli_attack(
            0,
            card,
            {'target': 1},
            '',
            None,
            {'target_id': 1},
        )

        self.assertEqual(engine.players[1].health, 78)
        self.assertEqual(card.power_value, 0)
        self.assertNotIn('power', card.instance_flags)


if __name__ == '__main__':
    unittest.main()
