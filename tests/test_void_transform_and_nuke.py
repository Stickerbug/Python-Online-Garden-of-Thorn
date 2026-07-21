import unittest

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import EquipmentInstance, GameEngine


def make_card_def(def_id, card_type, *, flags=None, fission_level=1, v2_events=None):
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
        flags=set(flags or []),
        fission_level=fission_level,
        v2_events=dict(v2_events or {}),
    )


class VoidTransformAndNukeTests(unittest.TestCase):
    def setUp(self):
        self.test_ids = {
            'test:old_attack',
            'test:new_coral',
            'test:old_equipment',
            'test:new_equipment',
            'test:nuke',
        }
        self.previous_defs = {key: CARD_DEFS.get(key) for key in self.test_ids}
        CARD_DEFS['test:old_attack'] = make_card_def('test:old_attack', 'thorn')
        CARD_DEFS['test:new_coral'] = make_card_def(
            'test:new_coral',
            'thorn',
            flags={'preserve_fission'},
            fission_level=4,
        )
        CARD_DEFS['test:old_equipment'] = make_card_def('test:old_equipment', 'root')
        CARD_DEFS['test:new_equipment'] = make_card_def(
            'test:new_equipment',
            'root',
            v2_events={
                'on_play': {
                    'steps': [
                        {'op': 'request_target', 'allowed': 'any'},
                        {'op': 'place_as_equip', 'effect_target': 'target'},
                        {'op': 'add_armor', 'target': 'target', 'amount': 2},
                    ]
                }
            },
        )
        CARD_DEFS['test:nuke'] = make_card_def('test:nuke', 'thorn')

    def tearDown(self):
        for key, old_value in self.previous_defs.items():
            if old_value is None:
                CARD_DEFS.pop(key, None)
            else:
                CARD_DEFS[key] = old_value

    def test_scar_transforms_every_zone_into_clean_intrinsic_cards(self):
        engine = GameEngine()
        player = engine.players[0]
        zones = (player.hand, player.deck, player.discard, player.exile)
        for zone in zones:
            old = CardInstance('test:old_attack')
            old.instance_flags.update({'power', 'wide_strike'})
            old.power_value = 9
            old.fission_level = 2
            zone.append(old)

        old_equipment = EquipmentInstance(CardInstance('test:old_equipment'), 0)
        old_equipment.effect_target = 1
        old_equipment.armor = 3
        player.equipment.append(old_equipment)

        engine._void_weighted_card_id = lambda card_type=None, exclude=None: (
            'test:new_equipment' if card_type == 'root' else 'test:new_coral'
        )
        engine._atomic_void_transform_own_cards(0, None, {}, '', None, {})

        for zone in zones:
            self.assertEqual(len(zone), 1)
            transformed = zone[0]
            self.assertEqual(transformed.def_id, 'test:new_coral')
            self.assertEqual(transformed.fission_level, 4)
            self.assertEqual(transformed.power_value, 0)
            self.assertNotIn('wide_strike', transformed.instance_flags)

        self.assertEqual(old_equipment.def_id, 'test:new_equipment')
        self.assertEqual(old_equipment.effect_target, 1)
        self.assertEqual(old_equipment.armor, 3)
        self.assertEqual(engine.players[1].armor, 2)

    def test_nuke_power_only_applies_to_first_attack(self):
        engine = GameEngine()
        engine.players[0].elixir = 2
        engine.players[1].health = 100
        card = CardInstance('test:nuke')
        card.power_value = 6
        card.instance_flags.add('power')

        engine._atomic_arctic_nuke(
            0,
            card,
            {'target': 1, 'health_percent': 0.08, 'minimum': 2},
            '',
            None,
            {},
        )

        self.assertEqual(engine.players[1].health, 79)
        self.assertEqual(card.power_value, 0)
        self.assertNotIn('power', card.instance_flags)


if __name__ == '__main__':
    unittest.main()
