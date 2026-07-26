import unittest

from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2


class InvincibleEffectTests(unittest.TestCase):
    @staticmethod
    def _grant_status_immunity(engine, player_id):
        engine.players[player_id].custom_statuses = {'status_immune': 1}

    def test_invincible_is_independent_from_status_immunity(self):
        engine = GameEngine()
        player = engine.players[0]
        player.health = 100
        self._grant_status_immunity(engine, 0)

        engine._set_invincible_until_next_own_turn_end(0)

        self.assertTrue(player.invincible)
        self.assertEqual(engine._get_player_property_value(0, 'invincible'), 1)
        self.assertEqual(engine._get_status_count(0, 'invincible'), 0)
        self.assertTrue(engine._has_fatal_prevention(0))
        self.assertEqual(engine._deal_direct_damage(0, 20, '测试'), 0)
        self.assertEqual(engine.deal_attack_damage(0, 20, attacker_id=1), 0)
        self.assertEqual(player.health, 100)

    def test_clear_named_status_does_not_clear_invincible(self):
        engine = GameEngine()
        self._grant_status_immunity(engine, 0)
        engine._set_invincible_until_next_own_turn_end(0)

        engine._atomic_clear_status(
            0,
            None,
            {'target': 'self', 'status': 'invincible'},
            '',
            None,
            {},
        )

        self.assertTrue(engine.players[0].invincible)

    def test_2v2_invincible_ignores_status_immunity(self):
        engine = GameEngine2v2()
        player = engine.players[0]
        player.health = 100
        self._grant_status_immunity(engine, 0)
        engine._set_invincible_until_next_own_turn_end(0)

        self.assertEqual(engine._deal_direct_damage(0, 20, '测试', source_id=2), 0)
        self.assertEqual(engine.deal_attack_damage(0, 20, attacker_id=2), 0)
        self.assertEqual(player.health, 100)


if __name__ == '__main__':
    unittest.main()
