import pathlib
import unittest

from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2


ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
SOLO_WORKER_JS = (ROOT / 'static' / 'js' / 'local_solo_worker.js').read_text(encoding='utf-8')


def source_between(source, start, end):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


class DamageReductionOrderTests(unittest.TestCase):
    def build_engine(self, *, armor=0, fragile=0, nazar=1):
        engine = GameEngine()
        target = engine.players[1]
        target.health = 100
        target.armor = armor
        if fragile:
            target.custom_statuses['jungle:fragile'] = fragile
        if nazar:
            target.custom_statuses['nazar'] = nazar
        return engine

    def test_fragile_increases_damage_before_nazar(self):
        engine = self.build_engine(fragile=3)

        dealt = engine.deal_attack_damage(1, 8, attacker_id=0)

        self.assertEqual(dealt, 2)
        self.assertEqual(engine.players[1].health, 98)
        self.assertEqual(engine._nazar_status_value(1), 0)

    def test_armor_reduces_damage_before_nazar(self):
        engine = self.build_engine(armor=5)

        dealt = engine.deal_attack_damage(1, 12, attacker_id=0)

        self.assertEqual(dealt, 1)
        self.assertEqual(engine.players[1].health, 99)
        self.assertEqual(engine._nazar_status_value(1), 1)

    def test_fully_blocked_damage_does_not_consume_nazar(self):
        engine = self.build_engine(armor=10)

        dealt = engine.deal_attack_damage(1, 8, attacker_id=0)

        self.assertEqual(dealt, 0)
        self.assertEqual(engine.players[1].health, 100)
        self.assertEqual(engine._nazar_status_value(1), 1)

    def test_2v2_uses_the_same_reduction_order(self):
        engine = GameEngine2v2()
        target = engine.players[1]
        target.health = 100
        target.custom_statuses['nazar'] = 1
        target.custom_statuses['jungle:fragile'] = 3

        dealt = engine.deal_attack_damage(1, 8, attacker_id=0)

        self.assertEqual(dealt, 2)
        self.assertEqual(target.health, 98)
        self.assertEqual(engine._nazar_status_value(1), 0)

    def test_client_prediction_applies_armor_before_nazar(self):
        section = source_between(
            GAME_JS,
            'function simulateNoCounterAttackHits(',
            'function formatPredictionPart(',
        )
        armor_index = section.index('dmg = Math.max(0, dmg - armor - rootArmor + fragile);')
        nazar_index = section.index('if (dmg > 0 && nazarStacks > 0)')
        self.assertLess(armor_index, nazar_index)

    def test_local_solo_engine_applies_armor_before_nazar(self):
        section = source_between(
            SOLO_WORKER_JS,
            '    dealAttackDamage(',
            '    currentTurnMarker()',
        )
        armor_index = section.index('dmg = Math.max(0, dmg - ps.armor - rootArmor + fragile);')
        nazar_index = section.index('if (dmg > 0 && nazarStacks > 0)')
        self.assertLess(armor_index, nazar_index)


if __name__ == '__main__':
    unittest.main()
