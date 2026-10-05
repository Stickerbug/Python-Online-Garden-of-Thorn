import unittest

from cards import CardInstance
from game_engine import EquipmentInstance, GameEngine


def _make_engine(engine_cls):
    engine = engine_cls()
    engine.phase = 'action'
    engine.current_player = 0
    engine.players[0].elixir = 10
    return engine


def _equip(engine, pid, def_id='Disc'):
    eq = EquipmentInstance(CardInstance(def_id), owner=pid)
    engine.players[pid].equipment.append(eq)
    return eq


class SewageTargetingTests(unittest.TestCase):
    def test_own_equipment_target_is_destroyed(self):
        engine = _make_engine(GameEngine)
        own = _equip(engine, 0)
        sewage = CardInstance('Sewage')
        engine.players[0].hand.append(sewage)

        result = engine.play_card(0, sewage.instance_id, {'target_instance_id': own.card_instance.instance_id})

        self.assertTrue(result.get('success'))
        self.assertEqual(len(engine.players[0].equipment), 0)

    def test_opponent_equipment_target_still_destroyed(self):
        engine = _make_engine(GameEngine)
        enemy = _equip(engine, 1)
        sewage = CardInstance('Sewage')
        engine.players[0].hand.append(sewage)

        result = engine.play_card(0, sewage.instance_id, {'target_instance_id': enemy.card_instance.instance_id})

        self.assertTrue(result.get('success'))
        self.assertEqual(len(engine.players[1].equipment), 0)

    def test_empty_field_blocks_play(self):
        engine = _make_engine(GameEngine)
        sewage = CardInstance('Sewage')
        engine.players[0].hand.append(sewage)

        can_play, reason = engine.can_play_card(0, sewage)

        self.assertFalse(can_play)
        self.assertIn('没有可摧毁的装备', reason)

    def test_own_equipment_only_still_allows_play(self):
        engine = _make_engine(GameEngine)
        _equip(engine, 0)
        sewage = CardInstance('Sewage')

        can_play, reason = engine.can_play_card(0, sewage)

        self.assertTrue(can_play, reason)

    def test_auto_choice_only_hits_enemy_side(self):
        engine = _make_engine(GameEngine)
        _equip(engine, 0)
        enemy = _equip(engine, 1)
        sewage = CardInstance('Sewage')
        engine.players[0].hand.append(sewage)

        result = engine.play_card(0, sewage.instance_id)

        self.assertTrue(result.get('success'))
        self.assertEqual(len(engine.players[0].equipment), 1)
        self.assertEqual(engine.players[1].equipment, [])

    def test_indestructible_only_field_blocks_play(self):
        engine = _make_engine(GameEngine)
        enemy = _equip(engine, 1)
        enemy.card_instance.instance_flags.add('indestructible')
        sewage = CardInstance('Sewage')
        engine.players[0].hand.append(sewage)

        result = engine.play_card(0, sewage.instance_id, {'target_instance_id': enemy.card_instance.instance_id})

        self.assertFalse(result.get('success'))
        self.assertIn('没有可摧毁的装备', result.get('error', ''))

    def test_indestructible_target_keeps_other_equipment_destroyable(self):
        engine = _make_engine(GameEngine)
        enemy = _equip(engine, 1)
        enemy.card_instance.instance_flags.add('indestructible')
        other = _equip(engine, 1)
        sewage = CardInstance('Sewage')
        engine.players[0].hand.append(sewage)

        can_play, _ = engine.can_play_card(0, sewage)
        self.assertTrue(can_play)
        result = engine.play_card(0, sewage.instance_id, {'target_instance_id': enemy.card_instance.instance_id})

        self.assertTrue(result.get('success'))
        self.assertEqual(len(engine.players[1].equipment), 2)


class TargetedCardPlayGateTests(unittest.TestCase):
    """同类问题排查：目标选择牌空目标时的服务端出牌门槛（UI 之外的兜底）。"""

    def _engine_with_hand(self, *def_ids):
        engine = GameEngine()
        engine.phase = 'action'
        engine.current_player = 0
        engine.players[0].elixir = 20
        engine.players[0].magic = 20
        hand = [CardInstance(def_id) for def_id in def_ids]
        engine.players[0].hand.extend(hand)
        return engine, hand

    def test_fission_without_attack_card_is_rejected(self):
        engine, hand = self._engine_with_hand('Fission', 'Rose')
        can_play, reason = engine.can_play_card(0, hand[0])
        self.assertFalse(can_play)
        self.assertIn('没有可选择的目标牌', reason)

    def test_fission_with_attack_card_is_allowed(self):
        engine, hand = self._engine_with_hand('Fission', 'Basic')
        can_play, reason = engine.can_play_card(0, hand[0])
        self.assertTrue(can_play, reason)

    def test_fusion_without_pair_is_rejected(self):
        engine, hand = self._engine_with_hand('Fusion', 'Basic', 'Thorn')
        can_play, reason = engine.can_play_card(0, hand[0])
        self.assertFalse(can_play)
        self.assertIn('同名攻击牌', reason)

    def test_fusion_with_pair_is_allowed(self):
        engine, hand = self._engine_with_hand('Fusion', 'Basic', 'Basic')
        can_play, reason = engine.can_play_card(0, hand[0])
        self.assertTrue(can_play, reason)

    def test_mimic_without_other_card_is_rejected(self):
        engine, hand = self._engine_with_hand('Mimic')
        can_play, reason = engine.can_play_card(0, hand[0])
        self.assertFalse(can_play)
        self.assertIn('没有可复制的牌', reason)

    def test_mimic_with_other_card_is_allowed(self):
        engine, hand = self._engine_with_hand('Mimic', 'Rose')
        can_play, reason = engine.can_play_card(0, hand[0])
        self.assertTrue(can_play, reason)

    def test_chromosome_with_empty_discard_is_rejected(self):
        engine, hand = self._engine_with_hand('Chromosome')
        can_play, reason = engine.can_play_card(0, hand[0])
        self.assertFalse(can_play)
        self.assertIn('弃牌堆没有可选择的目标牌', reason)

    def test_chromosome_with_discard_card_is_allowed(self):
        engine, hand = self._engine_with_hand('Chromosome')
        engine.players[0].discard.append(CardInstance('Rose'))
        can_play, reason = engine.can_play_card(0, hand[0])
        self.assertTrue(can_play, reason)

    def test_magicsewage_without_equipment_is_rejected(self):
        engine, hand = self._engine_with_hand('MagicSewage')
        can_play, reason = engine.can_play_card(0, hand[0])
        self.assertFalse(can_play)
        self.assertIn('没有可摧毁的装备', reason)

    def test_magicsewage_with_equipment_is_allowed(self):
        engine, hand = self._engine_with_hand('MagicSewage')
        _equip(engine, 1)
        can_play, reason = engine.can_play_card(0, hand[0])
        self.assertTrue(can_play, reason)


if __name__ == '__main__':
    unittest.main()
