import unittest

import app
from cards import CardInstance
from game_engine import EquipmentInstance, GameEngine


class ResponseEquipmentTargetTests(unittest.TestCase):
    def test_sewage_response_payload_identifies_selected_equipment(self):
        engine = GameEngine()
        target_equipment = EquipmentInstance(CardInstance('Disc'), owner=1)
        engine.players[1].equipment.append(target_equipment)
        sewage = CardInstance('Sewage')
        engine.pending_response = {
            'card': sewage.to_dict(),
            'player_id': 0,
            'target_player_id': 1,
            'original_choice': {
                'target_player_id': 1,
                'target_instance_id': target_equipment.card_instance.instance_id,
            },
        }
        engine.build_response_damage_prediction = None

        payload = app.build_response_request_payload(
            engine,
            responder_id=1,
            played_card=sewage.to_dict(),
            player_id=0,
            counter_cards=[CardInstance('GoldenNazar')],
            target_player_id=1,
        )

        self.assertEqual(payload['card']['def_id'], 'Sewage')
        self.assertEqual(payload['destroy_target_equipment']['owner_id'], 1)
        self.assertEqual(
            payload['destroy_target_equipment']['card_instance']['instance_id'],
            target_equipment.card_instance.instance_id,
        )
        self.assertEqual(
            payload['destroy_target_equipment']['card_instance']['def_id'],
            'Disc',
        )

    def test_non_destroy_response_does_not_attach_equipment_target(self):
        engine = GameEngine()
        target_equipment = EquipmentInstance(CardInstance('Disc'), owner=1)
        engine.players[1].equipment.append(target_equipment)
        attack = CardInstance('Basic')
        engine.pending_response = {
            'original_choice': {
                'target_player_id': 1,
                'target_instance_id': target_equipment.card_instance.instance_id,
            },
        }
        engine.build_response_damage_prediction = None

        payload = app.build_response_request_payload(
            engine,
            responder_id=1,
            played_card=attack.to_dict(),
            player_id=0,
            counter_cards=[CardInstance('Bubble')],
            target_player_id=1,
        )

        self.assertNotIn('destroy_target_equipment', payload)


if __name__ == '__main__':
    unittest.main()
