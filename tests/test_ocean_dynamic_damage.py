import unittest
from unittest.mock import patch

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import GameEngine


def make_card_def(def_id, *, flags=None, cost_e=0, cost_m=0, v2_events=None):
    return CardDef(
        def_id,
        def_id,
        def_id,
        cost_e,
        cost_m,
        'thorn',
        1,
        'Common',
        '',
        '',
        flags=set(flags or []),
        v2_events=v2_events or {},
    )


class OceanDynamicDamageTests(unittest.TestCase):
    def setUp(self):
        self.test_ids = {
            'test:ocean_trident',
            'test:ocean_magic_trident',
            'test:ocean_auto_pearl',
        }
        self.previous_defs = {key: CARD_DEFS.get(key) for key in self.test_ids}
        CARD_DEFS['test:ocean_trident'] = make_card_def(
            'test:ocean_trident',
            flags={'precision'},
            v2_events={'on_play': {'steps': [{
                'op': 'deal_damage',
                'target': 'target',
                'amount': {
                    'op': 'add',
                    'values': [
                        21,
                        {'op': 'mul', 'values': [5, {'op': 'status_count', 'target': 'target'}]},
                        {'op': 'mul', 'values': [5, {
                            'op': 'count',
                            'of': {'op': 'card_prop', 'card': 'current_card', 'prop': 'flags'},
                        }]},
                    ],
                },
            }]}},
        )
        CARD_DEFS['test:ocean_magic_trident'] = make_card_def(
            'test:ocean_magic_trident',
            flags={'precision'},
            v2_events={'on_play': {'steps': [{
                'op': 'deal_damage',
                'target': 'target',
                'amount': {
                    'op': 'add',
                    'values': [20, {
                        'op': 'mul',
                        'values': [5, {'op': 'player_var', 'target': 'source',
                                       'name': 'ocean_active_discards'}],
                    }],
                },
            }]}},
        )
        CARD_DEFS['test:ocean_auto_pearl'] = make_card_def(
            'test:ocean_auto_pearl',
            cost_e=1,
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
                engine._apply_card_effect(0, card, engine._active_choice)

        self.assertEqual(deal_damage.call_count, 3)
        self.assertEqual([call.args[1] for call in deal_damage.call_args_list], [11, 11, 11])

    def test_magic_trident_dynamic_damage_is_split_between_fission_hits(self):
        engine = GameEngine()
        engine._active_choice = {'target_player': 1}
        engine.players[0].custom_vars['ocean_active_discards'] = 2
        card = self.make_fission_card('test:ocean_magic_trident')

        with patch.object(engine, 'deal_attack_damage', return_value=10) as deal_damage:
            for _ in range(3):
                # Fission plays the card effect once per hit; the card data now
                # owns the base + per-discard formula.
                engine._apply_card_effect(0, card, engine._active_choice)

        self.assertEqual(deal_damage.call_count, 3)
        self.assertEqual([call.args[1] for call in deal_damage.call_args_list], [10, 10, 10])

    def _fill_hand(self, engine):
        player = engine.players[0]
        while player.rule_hand_size() < player.hand_limit():
            player.hand.append(CardInstance('Basic'))
        return player

    def _mark_auto_pearl(self, player):
        player.custom_vars['ocean_auto_cards'] = [{
            'def_id': 'test:ocean_auto_pearl',
            'target_id': 1,
            'swift_value': 0,
            'magic_swift_value': 0,
        }]

    def test_auto_pearl_copy_plays_without_overflowing_a_full_hand(self):
        engine = GameEngine()
        engine.phase = 'action'
        engine.current_player = 0
        player = self._fill_hand(engine)
        player.elixir = 10
        original_hand_ids = [card.instance_id for card in player.hand]
        self._mark_auto_pearl(player)

        engine._run_ocean_auto_cards_turn_start(0)

        self.assertEqual([card.instance_id for card in player.hand], original_hand_ids)
        self.assertEqual(player.discard, [])
        self.assertEqual(
            [card.def_id for card in player.exile],
            ['test:ocean_auto_pearl'],
        )

    def test_auto_pearl_copy_with_unpayable_effective_cost_enters_no_zone(self):
        engine = GameEngine()
        engine.phase = 'action'
        engine.current_player = 0
        player = self._fill_hand(engine)
        player.elixir = 1
        player.cards_played_this_turn['test:ocean_auto_pearl'] = 1
        original_hand_ids = [card.instance_id for card in player.hand]
        self._mark_auto_pearl(player)

        engine._run_ocean_auto_cards_turn_start(0)

        self.assertEqual([card.instance_id for card in player.hand], original_hand_ids)
        self.assertEqual(player.elixir, 1)
        self.assertEqual(player.discard, [])
        self.assertEqual(player.exile, [])


if __name__ == '__main__':
    unittest.main()
