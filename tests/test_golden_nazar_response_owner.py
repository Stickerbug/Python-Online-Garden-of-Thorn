import unittest

from cards import CardInstance
from game_engine import EquipmentInstance, GameEngine
from game_engine_2v2 import GameEngine2v2


def _equip(engine, owner_id, def_id='Disc', *, armor=0):
    equipment = EquipmentInstance(CardInstance(def_id), owner=owner_id)
    equipment.armor = armor
    engine.players[owner_id].equipment.append(equipment)
    return equipment


class GoldenNazarResponseOwnerTests(unittest.TestCase):
    def test_one_vs_one_opponent_cannot_respond_when_only_source_equipment_is_threatened(self):
        engine = GameEngine()
        _equip(engine, 0)
        golden_nazar = CardInstance('GoldenNazar')
        engine.players[1].hand.append(golden_nazar)
        magic_sewage = CardInstance('MagicSewage')

        result = engine._check_card_response_after_choice(
            0,
            magic_sewage,
            {'target_player_id': 0},
        )

        self.assertIsNone(result)
        self.assertIsNone(engine.pending_response)

    def test_one_vs_one_opponent_can_respond_when_own_equipment_is_threatened(self):
        engine = GameEngine()
        _equip(engine, 0)
        _equip(engine, 1)
        golden_nazar = CardInstance('GoldenNazar')
        engine.players[1].hand.append(golden_nazar)
        magic_sewage = CardInstance('MagicSewage')

        result = engine._check_card_response_after_choice(
            0,
            magic_sewage,
            {'target_player_id': 0},
        )

        self.assertTrue(result['needs_response'])
        self.assertIn(
            golden_nazar,
            engine.get_counter_cards(1, 'equipment_destroy'),
        )

    def test_forged_golden_nazar_response_is_rejected_for_unthreatened_owner(self):
        engine = GameEngine()
        source_equipment = _equip(engine, 0)
        golden_nazar = CardInstance('GoldenNazar')
        engine.players[1].hand.append(golden_nazar)
        magic_sewage = CardInstance('MagicSewage')
        engine.pending_response = {
            'card': magic_sewage.to_dict(),
            'player_id': 0,
            'target_player_id': 0,
            'original_choice': {'target_player_id': 0},
        }

        result = engine.handle_response(1, golden_nazar.instance_id)

        self.assertTrue(result['success'])
        self.assertIn(golden_nazar, engine.players[1].hand)
        self.assertEqual([], engine.players[0].equipment)
        self.assertIn(source_equipment.card_instance, engine.players[0].discard)

    def test_existing_armor_or_shared_protection_prevents_false_response(self):
        engine = GameEngine()
        protected = _equip(engine, 1, armor=1)
        golden_nazar = CardInstance('GoldenNazar')
        engine.players[1].hand.append(golden_nazar)
        sewage = CardInstance('Sewage')
        choice = {
            'target_player_id': 1,
            'target_instance_id': protected.card_instance.instance_id,
        }

        self.assertIsNone(engine._check_card_response_after_choice(0, sewage, choice))
        protected.armor = 0
        engine.players[1].equipment_protection = 1
        self.assertIsNone(engine._check_card_response_after_choice(0, sewage, choice))

    def test_magic_sewage_simulates_shared_protection_across_multiple_equipment(self):
        engine = GameEngine()
        _equip(engine, 1)
        _equip(engine, 1)
        engine.players[1].equipment_protection = 1
        golden_nazar = CardInstance('GoldenNazar')
        engine.players[1].hand.append(golden_nazar)

        result = engine._check_card_response_after_choice(
            0,
            CardInstance('MagicSewage'),
            {'target_player_id': 0},
        )

        self.assertTrue(result['needs_response'])

    def test_two_vs_two_only_actual_equipment_owners_are_response_candidates(self):
        engine = GameEngine2v2()
        _equip(engine, 0)
        golden_nazar = CardInstance('GoldenNazar')
        engine.players[2].hand.append(golden_nazar)
        magic_sewage = CardInstance('MagicSewage')

        self.assertNotIn(
            2,
            engine._equipment_destroy_response_player_ids(
                0,
                magic_sewage,
                {'target_player_id': 0},
            ),
        )

    def test_two_vs_two_bloom_responder_path_cannot_readd_unthreatened_golden_nazar(self):
        engine = GameEngine2v2()
        _equip(engine, 0)
        golden_nazar = CardInstance('GoldenNazar')
        engine.players[2].hand.append(golden_nazar)
        magic_sewage = CardInstance('MagicSewage')
        choice = {'target_player_id': 0}

        pending = engine._build_pending_response_for_card(0, magic_sewage, choice)

        self.assertIsNone(pending)
        _equip(engine, 2)
        pending = engine._build_pending_response_for_card(0, magic_sewage, choice)
        self.assertIsNotNone(pending)
        self.assertEqual(
            [golden_nazar.instance_id],
            [card['instance_id'] for card in pending['counter_cards']],
        )
        _equip(engine, 2)
        self.assertIn(
            2,
            engine._equipment_destroy_response_player_ids(
                0,
                magic_sewage,
                {'target_player_id': 0},
            ),
        )


if __name__ == '__main__':
    unittest.main()
