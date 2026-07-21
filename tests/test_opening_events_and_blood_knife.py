import json
import unittest
import zipfile
from pathlib import Path

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import GameEngine


def make_card_def(def_id, card_type):
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
    )


class OpeningEventsAndBloodKnifeTests(unittest.TestCase):
    def setUp(self):
        self.test_ids = {'test:light_attack', 'test:light_skill', 'test:blood_knife'}
        self.previous_defs = {key: CARD_DEFS.get(key) for key in self.test_ids}
        CARD_DEFS['test:light_attack'] = make_card_def('test:light_attack', 'thorn')
        CARD_DEFS['test:light_skill'] = make_card_def('test:light_skill', 'bloom')
        CARD_DEFS['test:blood_knife'] = make_card_def('test:blood_knife', 'bloom')

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
