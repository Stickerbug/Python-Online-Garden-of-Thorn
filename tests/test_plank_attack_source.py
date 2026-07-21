import unittest

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import EquipmentInstance, GameEngine
from game_engine_2v2 import GameEngine2v2


def make_card_def(def_id, card_type, *, cost_e=0):
    return CardDef(
        def_id,
        def_id,
        def_id,
        cost_e,
        0,
        card_type,
        1,
        'Common',
        '',
        '',
    )


class PlankAttackSourceTests(unittest.TestCase):
    def setUp(self):
        self.test_ids = {
            'jungle:plank',
            'test:low_cost_attack',
            'test:low_cost_non_attack',
        }
        self.previous_defs = {key: CARD_DEFS.get(key) for key in self.test_ids}
        CARD_DEFS['jungle:plank'] = make_card_def('jungle:plank', 'root', cost_e=3)
        CARD_DEFS['test:low_cost_attack'] = make_card_def('test:low_cost_attack', 'thorn', cost_e=1)
        CARD_DEFS['test:low_cost_non_attack'] = make_card_def('test:low_cost_non_attack', 'root', cost_e=1)

    def tearDown(self):
        for key, old_value in self.previous_defs.items():
            if old_value is None:
                CARD_DEFS.pop(key, None)
            else:
                CARD_DEFS[key] = old_value

    @staticmethod
    def equip_plank(engine, target_id):
        equipment = EquipmentInstance(CardInstance('jungle:plank'), target_id)
        equipment.effect_target = target_id
        engine.players[target_id].equipment.append(equipment)

    def assert_plank_only_blocks_attack_cards(self, engine, attacker_id, target_id):
        self.equip_plank(engine, target_id)
        engine.players[target_id].health = 100

        engine.deal_attack_damage(
            target_id,
            10,
            attacker_id=attacker_id,
            source_card=CardInstance('test:low_cost_attack'),
        )
        self.assertEqual(engine.players[target_id].health, 100)

        engine.deal_attack_damage(
            target_id,
            10,
            attacker_id=attacker_id,
            source_card=CardInstance('test:low_cost_non_attack'),
        )
        self.assertEqual(engine.players[target_id].health, 90)

    def test_one_vs_one(self):
        self.assert_plank_only_blocks_attack_cards(GameEngine(), 0, 1)

    def test_two_vs_two(self):
        self.assert_plank_only_blocks_attack_cards(GameEngine2v2(), 0, 2)


if __name__ == '__main__':
    unittest.main()
