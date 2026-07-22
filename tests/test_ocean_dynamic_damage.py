import unittest
from unittest.mock import patch

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import GameEngine


def make_card_def(def_id, *, flags=None):
    return CardDef(
        def_id,
        def_id,
        def_id,
        0,
        0,
        'thorn',
        1,
        'Common',
        '',
        '',
        flags=set(flags or []),
    )


class OceanDynamicDamageTests(unittest.TestCase):
    def setUp(self):
        self.test_ids = {'test:ocean_trident', 'test:ocean_magic_trident'}
        self.previous_defs = {key: CARD_DEFS.get(key) for key in self.test_ids}
        CARD_DEFS['test:ocean_trident'] = make_card_def(
            'test:ocean_trident',
            flags={'precision'},
        )
        CARD_DEFS['test:ocean_magic_trident'] = make_card_def(
            'test:ocean_magic_trident',
            flags={'precision'},
        )

    def tearDown(self):
        for key, old_value in self.previous_defs.items():
            if old_value is None:
                CARD_DEFS.pop(key, None)
            else:
                CARD_DEFS[key] = old_value

    @staticmethod
    def make_fission_card(def_id):
        card = CardInstance(def_id)
        card.fission_level = 3
        card.fission_count = 2
        return card

    def test_trident_dynamic_damage_is_split_between_fission_hits(self):
        engine = GameEngine()
        engine._active_choice = {'target_player': 1}
        engine.players[1].poison = 1
        card = self.make_fission_card('test:ocean_trident')

        with patch.object(engine, 'deal_attack_damage', return_value=11) as deal_damage:
            for _ in range(3):
                engine._atomic_ocean_status_tag_damage(
                    0,
                    card,
                    {'target': 'target', 'base': 21, 'per_status': 5, 'per_tag': 5},
                    '',
                    engine._active_choice,
                    {},
                )

        self.assertEqual(deal_damage.call_count, 3)
        self.assertEqual([call.args[1] for call in deal_damage.call_args_list], [11, 11, 11])

    def test_magic_trident_dynamic_damage_is_split_between_fission_hits(self):
        engine = GameEngine()
        engine._active_choice = {'target_player': 1}
        engine.players[0].custom_vars['ocean_active_discards'] = 2
        card = self.make_fission_card('test:ocean_magic_trident')

        with patch.object(engine, 'deal_attack_damage', return_value=10) as deal_damage:
            for _ in range(3):
                engine._atomic_ocean_discard_count_damage(
                    0,
                    card,
                    {'target': 'target', 'base': 20, 'per': 5},
                    '',
                    engine._active_choice,
                    {},
                )

        self.assertEqual(deal_damage.call_count, 3)
        self.assertEqual([call.args[1] for call in deal_damage.call_args_list], [10, 10, 10])


if __name__ == '__main__':
    unittest.main()
