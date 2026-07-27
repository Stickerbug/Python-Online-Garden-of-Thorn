import unittest

from cards import CardInstance
from game_engine_2v2 import GameEngine2v2


def target_choice(player_id):
    return {
        'target_player': player_id,
        'target_player_id': player_id,
        'target_id': player_id,
    }


class MagicNazar2v2Tests(unittest.TestCase):
    def build_engine(self):
        engine = GameEngine2v2()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.elixir = 10
            player.magic = 10
            player.hand = []
        return engine

    def test_enemy_can_use_magic_nazar_when_skill_targets_its_user(self):
        engine = self.build_engine()
        skill = CardInstance('ManaOrb')
        magic_nazar = CardInstance('MagicNazar')
        engine.players[0].hand = [skill]
        engine.players[2].hand = [magic_nazar]

        result = engine.play_card(0, skill.instance_id, 0, target_choice(0))

        self.assertTrue(result.get('needs_response'))
        self.assertIsNotNone(engine.pending_response)
        responder_ids = {
            int(card['responder_id'])
            for card in engine.pending_response.get('counter_cards', [])
        }
        self.assertEqual(responder_ids, {2})

        response = engine.handle_response(2, magic_nazar.instance_id)

        self.assertTrue(response.get('success'))
        self.assertEqual(engine.players[2].custom_statuses.get('magic_nazar'), 1)
        self.assertTrue(any('被魔法邪眼反制，失效' in line for line in engine.log))

    def test_magic_nazar_status_negates_next_enemy_low_e_skill(self):
        engine = self.build_engine()
        skill = CardInstance('ManaOrb')
        engine.players[0].hand = [skill]
        engine.players[2].custom_statuses['magic_nazar'] = 2
        magic_before = engine.players[0].magic

        result = engine.play_card(0, skill.instance_id, 0, target_choice(0))

        self.assertTrue(result.get('success'))
        self.assertEqual(engine.players[0].magic, magic_before)
        self.assertEqual(engine.players[2].custom_statuses.get('magic_nazar'), 1)
        self.assertTrue(any('被魔法邪眼反制，失效' in line for line in engine.log))

    def test_attack_counter_stays_limited_to_the_attacked_player(self):
        engine = self.build_engine()
        attack = CardInstance('Basic')
        teammate_bubble = CardInstance('Bubble')
        engine.players[0].hand = [attack]
        engine.players[2].hand = [teammate_bubble]

        result = engine.play_card(0, attack.instance_id, 3, target_choice(3))

        self.assertFalse(result.get('needs_response', False))
        self.assertIsNone(engine.pending_response)


if __name__ == '__main__':
    unittest.main()
