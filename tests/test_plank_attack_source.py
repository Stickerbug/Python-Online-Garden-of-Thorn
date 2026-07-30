import unittest

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import EquipmentInstance, GameEngine
from game_engine_2v2 import GameEngine2v2


def make_card_def(def_id, card_type, *, cost_e=0, damage=0, response_trigger=''):
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
        response_trigger=response_trigger,
        damage=damage,
    )


class PlankAttackSourceTests(unittest.TestCase):
    def setUp(self):
        self.test_ids = {
            'jungle:plank',
            'test:low_cost_attack',
            'test:high_cost_attack',
            'test:low_cost_non_attack',
            'test:thorn_counter',
        }
        self.previous_defs = {key: CARD_DEFS.get(key) for key in self.test_ids}
        CARD_DEFS['jungle:plank'] = make_card_def('jungle:plank', 'root', cost_e=3)
        CARD_DEFS['test:low_cost_attack'] = make_card_def(
            'test:low_cost_attack',
            'thorn',
            cost_e=1,
            damage=10,
        )
        CARD_DEFS['test:high_cost_attack'] = make_card_def(
            'test:high_cost_attack',
            'thorn',
            cost_e=3,
            damage=10,
        )
        CARD_DEFS['test:low_cost_non_attack'] = make_card_def('test:low_cost_non_attack', 'root', cost_e=1)
        CARD_DEFS['test:thorn_counter'] = make_card_def(
            'test:thorn_counter',
            'guard',
            response_trigger='thorn',
        )

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

    def test_plank_uses_actual_paid_energy(self):
        for engine, target_id in ((GameEngine(), 1), (GameEngine2v2(), 2)):
            with self.subTest(engine=type(engine).__name__):
                self.equip_plank(engine, target_id)
                engine.players[target_id].health = 100

                discounted = CardInstance('test:high_cost_attack')
                discounted._paid_e_this_play = 1
                engine.deal_attack_damage(
                    target_id,
                    10,
                    attacker_id=0,
                    source_card=discounted,
                )
                self.assertEqual(engine.players[target_id].health, 100)

                penalized = CardInstance('test:low_cost_attack')
                penalized._paid_e_this_play = 2
                engine.deal_attack_damage(
                    target_id,
                    10,
                    attacker_id=0,
                    source_card=penalized,
                )
                self.assertEqual(engine.players[target_id].health, 90)

    def test_actual_paid_energy_survives_response_window(self):
        engine = GameEngine()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.hand = []
            player.deck = []
            player.discard = []
            player.exile = []
            player.elixir = 10
            player.magic = 10
            player.health = 100
        self.equip_plank(engine, 1)
        attack = CardInstance('test:low_cost_attack')
        counter = CardInstance('test:thorn_counter')
        engine.players[0].hand = [attack]
        engine.players[0].cards_played_this_turn[attack.def_id] = 1
        engine.players[1].hand = [counter]

        result = engine.play_card(
            0,
            attack.instance_id,
            {'target_player': 1, 'target_player_id': 1, 'target_id': 1},
        )
        self.assertTrue(result.get('needs_response'))
        self.assertEqual(engine.pending_response.get('paid_e'), 2)

        resolved = engine.handle_response(1, None)
        self.assertTrue(resolved.get('success'))
        self.assertEqual(engine.players[1].health, 90)


if __name__ == '__main__':
    unittest.main()
