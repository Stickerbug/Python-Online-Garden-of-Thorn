import json
import unittest
import zipfile
from pathlib import Path

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2


def make_card_def(def_id, card_type, *, flags=None, response_trigger='', cost_e=0, cost_m=0):
    return CardDef(
        def_id,
        def_id,
        def_id,
        cost_e,
        cost_m,
        card_type,
        1,
        'Common',
        '',
        '',
        flags=set(flags or []),
        response_trigger=response_trigger,
    )


class OpeningEventsAndBloodKnifeTests(unittest.TestCase):
    def setUp(self):
        self.test_ids = {
            'test:light_attack',
            'test:light_skill',
            'test:blood_knife',
            'test:order_a',
            'test:order_b',
            'test:order_hidden',
            'test:self_attack',
            'test:thorn_counter',
            'test:magic_cost',
        }
        self.previous_defs = {key: CARD_DEFS.get(key) for key in self.test_ids}
        CARD_DEFS['test:light_attack'] = make_card_def('test:light_attack', 'thorn')
        CARD_DEFS['test:light_skill'] = make_card_def('test:light_skill', 'bloom')
        CARD_DEFS['test:blood_knife'] = make_card_def('test:blood_knife', 'bloom')
        CARD_DEFS['test:order_a'] = make_card_def('test:order_a', 'bloom')
        CARD_DEFS['test:order_b'] = make_card_def('test:order_b', 'bloom')
        CARD_DEFS['test:order_hidden'] = make_card_def(
            'test:order_hidden',
            'bloom',
            flags={'sublime'},
        )
        CARD_DEFS['test:self_attack'] = make_card_def(
            'test:self_attack',
            'thorn',
            flags={'self_target'},
        )
        CARD_DEFS['test:thorn_counter'] = make_card_def(
            'test:thorn_counter',
            'guard',
            response_trigger='thorn',
        )
        CARD_DEFS['test:magic_cost'] = make_card_def(
            'test:magic_cost',
            'bloom',
            cost_m=1,
        )

    def tearDown(self):
        for key, old_value in self.previous_defs.items():
            if old_value is None:
                CARD_DEFS.pop(key, None)
            else:
                CARD_DEFS[key] = old_value

    def test_light_baptism_only_converts_non_attack_cards(self):
        engine = GameEngine()
        engine.players[0].deck = [
            CardInstance('test:light_attack'),
            CardInstance('test:light_skill'),
        ]
        engine.opening_event_picks[0] = 3
        engine.opening_event_sub_choices[0] = {
            'convert_def_ids': ['test:light_attack', 'test:light_skill'],
        }

        engine._apply_opening_event(0)

        self.assertEqual(
            [card.def_id for card in engine.players[0].deck],
            ['test:light_attack', 'Light'],
        )

    def test_multi_petal_adds_three_dust_cards(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = 9
        engine.players[0].deck = []

        engine._apply_opening_event(0)

        dust_cards = [card for card in engine.players[0].deck if card.def_id == 'Dust']
        self.assertEqual(len(dust_cards), 3)
        self.assertTrue(all('exile' in card.flags for card in dust_cards))

    def test_floral_arrangement_reorders_the_full_visible_deck(self):
        engine = GameEngine()
        engine.players[0].deck = [
            CardInstance('test:order_a'),
            CardInstance('test:order_hidden'),
            CardInstance('test:order_b'),
            CardInstance('test:order_a'),
        ]
        engine.opening_event_picks[0] = 11
        engine.opening_event_sub_choices[0] = {
            'deck_order_def_ids': [
                'test:order_b',
                'test:order_a',
                'test:order_a',
            ],
        }

        engine._apply_opening_event(0)

        self.assertEqual(
            [card.def_id for card in engine.players[0].deck],
            [
                'test:order_b',
                'test:order_hidden',
                'test:order_a',
                'test:order_a',
            ],
        )

    def test_flame_omen_applies_four_fire(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = 4

        engine._apply_opening_event(0)

        self.assertEqual(engine.players[1].fire, 4)

    def test_equal_suffering_deals_more_damage_to_enemies(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = 12
        engine.players[0].health = 100
        engine.players[1].health = 100

        engine._apply_equal_suffering_turn_start(0)

        self.assertEqual(engine.players[0].health, 95)
        self.assertEqual(engine.players[1].health, 93)

    def test_equal_suffering_uses_team_damage_in_two_vs_two(self):
        engine = GameEngine2v2()
        engine.opening_event_picks[0] = 12
        for player in engine.players:
            player.health = 100

        engine._apply_equal_suffering_turn_start(0)

        self.assertEqual([player.health for player in engine.players], [95, 95, 93, 93])

    def test_blood_knife_recovers_for_actual_damage_dealt(self):
        engine = GameEngine()
        player = engine.players[0]
        player.health = 100
        player.elixir = 0
        card = CardInstance('test:blood_knife')

        engine._atomic_bio_activate_blood_knife(0, card, {}, '', None, {})

        self.assertEqual(player.health, 95)
        self.assertEqual(player.elixir, 1)

    def test_blood_knife_mod_data_matches_new_rules(self):
        archive = Path(__file__).resolve().parents[1] / 'mods' / 'Bio Cards Addition.gtnmod'
        with zipfile.ZipFile(archive) as package:
            mod_data = json.loads(package.read('mod.json').decode('utf-8'))
        card = next(
            item for item in mod_data['registries']['cards']
            if item.get('id') == 'bio:blood_knife'
        )

        self.assertEqual(card['cost_e'], 0)
        self.assertEqual(card['card_type'], 'bloom')
        self.assertEqual(set(card['flags']), {'self_only', 'rebound', 'symbiosis'})
        self.assertEqual(
            card['effect_text'],
            '对自己造成5[[icon:D]]；每造成3[[icon:D]]，回复自己1[[icon:E]]',
        )

    def test_blood_sugar_does_not_have_self_target(self):
        archive = Path(__file__).resolve().parents[1] / 'mods' / 'Bio Cards Addition.gtnmod'
        with zipfile.ZipFile(archive) as package:
            mod_data = json.loads(package.read('mod.json').decode('utf-8'))
        card = next(
            item for item in mod_data['registries']['cards']
            if item.get('id') == 'bio:blood_sugar'
        )

        self.assertNotIn('self_target', card.get('flags', []))

    def test_self_targeted_attack_does_not_offer_opponent_response(self):
        engine = GameEngine()
        card = CardInstance('test:self_attack')
        engine.players[1].hand = [CardInstance('test:thorn_counter')]

        result = engine._check_card_response_after_choice(
            0,
            card,
            {'target_player': 0, 'target_player_id': 0, 'target_id': 0},
        )

        self.assertIsNone(result)
        self.assertIsNone(engine.pending_response)

    def test_enemy_targeted_attack_still_offers_response(self):
        engine = GameEngine()
        card = CardInstance('test:self_attack')
        engine.players[1].hand = [CardInstance('test:thorn_counter')]

        result = engine._check_card_response_after_choice(
            0,
            card,
            {'target_player': 1, 'target_player_id': 1, 'target_id': 1},
        )

        self.assertTrue(result and result.get('needs_response'))
        self.assertIsNotNone(engine.pending_response)

    def test_two_vs_two_self_targeted_attack_does_not_offer_enemy_response(self):
        engine = GameEngine2v2()
        card = CardInstance('test:self_attack')
        engine.players[2].hand = [CardInstance('test:thorn_counter')]
        engine.players[3].hand = [CardInstance('test:thorn_counter')]

        result = engine._check_card_response_after_choice(
            0,
            card,
            {'target_player': 0, 'target_player_id': 0, 'target_id': 0},
        )

        self.assertIsNone(result)
        self.assertIsNone(engine.pending_response)

    def test_foresight_does_not_disable_magic_block(self):
        for engine_type in (GameEngine, GameEngine2v2):
            for status_key in ('magic_blocked', 'troll_cards:magic_blocked'):
                with self.subTest(engine=engine_type.__name__, status=status_key):
                    engine = engine_type()
                    player = engine.players[0]
                    player.hand = [CardInstance('test:magic_cost')]
                    player.deck = [CardInstance('test:light_skill') for _ in range(8)]
                    player.magic = 10
                    player.foresight = 1
                    player.custom_statuses[status_key] = 1
                    engine.round_num = 2
                    engine.phase = 'draw'

                    engine._start_player_turn(0)
                    self.assertEqual(engine.pending_choice.get('choice_type'), 'foresight_replace')
                    engine.resolve_choice(0, {'selected_instance_ids': []})

                    playable, reason = engine.can_play_card(0, player.hand[0])
                    self.assertFalse(playable)
                    self.assertIn('魔力消耗', reason)
                    self.assertEqual(player.custom_statuses.get(status_key), 1)

    def test_charge_decays_at_turn_end(self):
        engine = GameEngine()
        card = CardInstance('test:light_skill')
        card.charge_value = 2
        card.instance_flags.add('charge')
        engine.players[0].hand = [card]

        engine._decay_ocean_card_charge_turn_end(0)
        self.assertEqual(card.charge_value, 1)
        self.assertIn('charge', card.instance_flags)

        engine._decay_ocean_card_charge_turn_end(0)
        self.assertEqual(card.charge_value, 0)
        self.assertNotIn('charge', card.instance_flags)


if __name__ == '__main__':
    unittest.main()
