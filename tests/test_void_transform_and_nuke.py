import unittest
from pathlib import Path

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import EquipmentInstance, GameEngine
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
VOID_PACKAGE = ROOT / 'mods' / 'Void Card Addition.gtnmod'
ARCTIC_PACKAGE = ROOT / 'mods' / 'Arctic Cards Addition.gtnmod'


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


def load_package_card(package, card_id):
    """Real card definition straight from the shipped package data."""
    mod = load_mod(str(package))
    if mod.errors:
        raise AssertionError(mod.errors)
    return next(item for item in mod.cards if item.id == card_id).to_card_def()


def target_choice(target_id):
    return {
        'target_player': target_id,
        'target_player_id': target_id,
        'target_id': target_id,
    }


class VoidTransformAndNukeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real_defs = {
            'Scar': load_package_card(VOID_PACKAGE, 'Scar'),
            'Nuke': load_package_card(ARCTIC_PACKAGE, 'Nuke'),
        }

    def setUp(self):
        self.test_ids = {
            'test:old_attack',
            'test:new_coral',
            'test:old_equipment',
            'test:new_equipment',
            'Scar',
            'Nuke',
        }
        self.previous_defs = {key: CARD_DEFS.get(key) for key in self.test_ids}
        CARD_DEFS.update(self.real_defs)
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
                        # Round 50 / 批次 AN：三条老写法都并进伞原子
                        # （``request`` / ``equipment_op`` / ``player_stat_change``）。
                        {'op': 'request', 'type': 'target', 'allowed': 'any'},
                        {'op': 'equipment_op', 'mode': 'place', 'effect_target': 'target'},
                        {'op': 'player_stat_change', 'mode': 'add', 'stat': 'armor',
                         'target': 'target', 'amount': 2},
                    ]
                }
            },
        )

    def tearDown(self):
        for key, old_value in self.previous_defs.items():
            if old_value is None:
                CARD_DEFS.pop(key, None)
            else:
                CARD_DEFS[key] = old_value

    def test_scar_transforms_every_zone_into_clean_intrinsic_cards(self):
        engine = GameEngine()
        engine.phase = 'action'
        engine.current_player = 0
        player = engine.players[0]
        player.elixir = 10
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
        # The transform now lives in the package data; play the real Scar so the
        # shipped ``transform_cards`` steps (and its equip re-run) are exercised.
        scar = CardInstance('Scar')
        player.hand.append(scar)

        result = engine.play_card(0, scar.instance_id, target_choice(1))

        self.assertTrue(result.get('success'), result)
        self.assertEqual(engine.players[1].health, 70)

        for zone in zones:
            transformed = zone[0]
            self.assertEqual(transformed.def_id, 'test:new_coral')
            self.assertEqual(transformed.fission_level, 4)
            self.assertEqual(transformed.power_value, 0)
            self.assertNotIn('wide_strike', transformed.instance_flags)
        # Every zone card was replaced in place; the played Scar itself now
        # sits at the end of the discard pile.
        self.assertEqual([len(zone) for zone in zones], [1, 1, 2, 1])
        self.assertEqual([card.def_id for card in player.discard], ['test:new_coral', 'Scar'])

        self.assertEqual(old_equipment.def_id, 'test:new_equipment')
        self.assertEqual(old_equipment.effect_target, 1)
        self.assertEqual(old_equipment.armor, 3)
        self.assertEqual(engine.players[1].armor, 2)

    def test_nuke_power_only_applies_to_first_attack(self):
        engine = GameEngine()
        engine.phase = 'action'
        engine.current_player = 0
        engine.players[0].elixir = 2
        engine.players[1].health = 100
        engine.players[1].max_health = 100
        card = CardInstance('Nuke')
        card.power_value = 6
        card.instance_flags.add('power')
        engine.players[0].hand = [card]

        # Data driven Nuke: the package spends every E and repeats once per E,
        # with ``power_once`` handling the power bonus on the first attack only.
        result = engine.play_card(0, card.instance_id, target_choice(1))

        self.assertTrue(result.get('success'), result)
        self.assertEqual(engine.players[1].health, 79)
        self.assertEqual(engine.players[0].elixir, 0)
        self.assertEqual(card.power_value, 0)
        self.assertNotIn('power', card.instance_flags)


if __name__ == '__main__':
    unittest.main()
