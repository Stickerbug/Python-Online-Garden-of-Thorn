import unittest

from cards import CardInstance
from game_engine import EquipmentInstance
from game_engine_2v2 import GameEngine2v2


class DeadPlayerActionTests(unittest.TestCase):
    @staticmethod
    def _prime_two_vs_two() -> GameEngine2v2:
        engine = GameEngine2v2()
        engine.phase = 'action'
        engine.round_num = 3
        engine.turn_order = [0, 2, 1, 3]
        engine.turn_index = 1
        engine.current_player = 2
        for player in engine.players:
            player.health = 100
            player.elixir = 20
            player.magic = 20
            player.hand = []
            player.deck = []
            player.discard = []
        return engine

    def test_counter_kill_cleans_up_and_advances_to_next_living_player(self):
        engine = self._prime_two_vs_two()
        played_card = CardInstance('Basic')
        counter_card = CardInstance('Bubble')
        follow_up = CardInstance('Light')
        engine.players[2].hand.extend([played_card, follow_up])
        engine.players[0].hand.append(counter_card)
        engine.players[2].equipment.append(EquipmentInstance(CardInstance('Leaf'), 2))

        play_result = engine.play_card(
            2,
            played_card.instance_id,
            target_player_id=0,
            choice={'target_player': 0, 'target_player_id': 0, 'target_id': 0},
        )
        self.assertTrue(play_result.get('needs_response'))

        def lethal_counter(_responder_id, _counter_card, _original_card, original_player_id=None,
                           _pending_damage_prediction=None):
            engine.players[original_player_id].health = 0

        engine._execute_counter_effect = lethal_counter
        response_result = engine.handle_response(0, counter_card.instance_id)

        self.assertTrue(response_result.get('success'))
        self.assertEqual(engine.players[2].health, 0)
        self.assertEqual(engine.players[2].equipment, [])
        self.assertEqual(engine.current_player, 1)
        self.assertEqual(engine.turn_index, 2)
        self.assertEqual(
            sum('已阵亡，跳过剩余行动' in line for line in engine.log),
            1,
        )

        rejected = engine.play_card(
            2,
            follow_up.instance_id,
            target_player_id=0,
            choice={'target_player': 0, 'target_player_id': 0, 'target_id': 0},
        )
        self.assertFalse(rejected.get('success'))
        self.assertEqual(rejected.get('error'), '阵亡玩家无法行动')
        self.assertIsNotNone(engine.players[2].find_hand_card(follow_up.instance_id))

    def test_dead_current_player_end_turn_only_repairs_turn_order(self):
        engine = self._prime_two_vs_two()
        engine.players[2].health = 0
        engine.players[2].fracture = 5

        result = engine.end_turn(2)

        self.assertTrue(result.get('success'))
        self.assertTrue(result.get('dead_player_skipped'))
        self.assertEqual(engine.current_player, 1)
        self.assertEqual(engine.players[2].fracture, 5)

    def test_dead_teammate_cannot_trigger_equipment(self):
        engine = self._prime_two_vs_two()
        engine.current_player = 0
        engine.turn_index = 0
        engine.players[1].health = 0

        result = engine.use_trigger(1, 999999, target_player_id=0)

        self.assertFalse(result.get('success'))
        self.assertEqual(result.get('error'), '阵亡玩家无法行动')


if __name__ == '__main__':
    unittest.main()
