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

    def test_magic_sewage_response_lists_every_equipment_being_destroyed(self):
        engine = GameEngine()
        first = EquipmentInstance(CardInstance('Disc'), owner=1)
        second = EquipmentInstance(CardInstance('Disc'), owner=1)
        engine.players[1].equipment.extend([first, second])
        magic_sewage = CardInstance('MagicSewage')
        engine.pending_response = {
            'card': magic_sewage.to_dict(),
            'player_id': 0,
            'target_player_id': 1,
            'original_choice': None,
        }
        engine.build_response_damage_prediction = None

        payload = app.build_response_request_payload(
            engine,
            responder_id=1,
            played_card=magic_sewage.to_dict(),
            player_id=0,
            counter_cards=[CardInstance('GoldenNazar')],
            target_player_id=1,
        )

        destroyed = payload.get('destroy_target_equipments') or []
        self.assertEqual(len(destroyed), 2)
        self.assertEqual(
            {item['card_instance']['instance_id'] for item in destroyed},
            {
                first.card_instance.instance_id,
                second.card_instance.instance_id,
            },
        )
        self.assertNotIn('destroy_target_equipment', payload)

    def test_magic_sewage_response_excludes_surviving_equipment(self):
        engine = GameEngine()
        armored = EquipmentInstance(CardInstance('Disc'), owner=1)
        armored.armor = 1
        protected = EquipmentInstance(CardInstance('Disc'), owner=1)
        engine.players[1].equipment.extend([armored, protected])
        engine.players[1].equipment_protection = 1
        indestructible = EquipmentInstance(CardInstance('Disc'), owner=1)
        indestructible.card_instance.instance_flags.add('indestructible')
        engine.players[1].equipment.append(indestructible)
        magic_sewage = CardInstance('MagicSewage')
        engine.pending_response = {
            'card': magic_sewage.to_dict(),
            'player_id': 0,
            'target_player_id': 1,
            'original_choice': None,
        }
        engine.build_response_damage_prediction = None

        payload = app.build_response_request_payload(
            engine,
            responder_id=1,
            played_card=magic_sewage.to_dict(),
            player_id=0,
            counter_cards=[CardInstance('GoldenNazar')],
            target_player_id=1,
        )

        self.assertNotIn('destroy_target_equipment', payload)
        self.assertNotIn('destroy_target_equipments', payload)

        protected.card_instance.instance_flags.add('indestructible')
        engine.players[1].equipment_protection = 0
        payload = app.build_response_request_payload(
            engine,
            responder_id=1,
            played_card=magic_sewage.to_dict(),
            player_id=0,
            counter_cards=[CardInstance('GoldenNazar')],
            target_player_id=1,
        )
        self.assertNotIn('destroy_target_equipment', payload)
        self.assertNotIn('destroy_target_equipments', payload)

    def test_magic_sewage_response_applies_shared_protection_in_order(self):
        engine = GameEngine()
        first = EquipmentInstance(CardInstance('Disc'), owner=1)
        second = EquipmentInstance(CardInstance('Disc'), owner=1)
        third = EquipmentInstance(CardInstance('Disc'), owner=1)
        engine.players[1].equipment.extend([first, second, third])
        engine.players[1].equipment_protection = 1
        magic_sewage = CardInstance('MagicSewage')
        engine.pending_response = {
            'card': magic_sewage.to_dict(),
            'player_id': 0,
            'target_player_id': 1,
            'original_choice': None,
        }
        engine.build_response_damage_prediction = None

        payload = app.build_response_request_payload(
            engine,
            responder_id=1,
            played_card=magic_sewage.to_dict(),
            player_id=0,
            counter_cards=[CardInstance('GoldenNazar')],
            target_player_id=1,
        )

        destroyed = payload.get('destroy_target_equipments') or []
        self.assertEqual(len(destroyed), 2)
        self.assertEqual(
            [item['card_instance']['instance_id'] for item in destroyed],
            [
                second.card_instance.instance_id,
                third.card_instance.instance_id,
            ],
        )
        self.assertNotIn('destroy_target_equipment', payload)

    def test_single_destroy_target_keeps_legacy_field_for_compatibility(self):
        engine = GameEngine()
        selected = EquipmentInstance(CardInstance('Disc'), owner=1)
        engine.players[1].equipment.append(selected)
        sewage = CardInstance('Sewage')
        engine.pending_response = {
            'card': sewage.to_dict(),
            'player_id': 0,
            'target_player_id': 1,
            'original_choice': {
                'target_player_id': 1,
                'target_instance_id': selected.card_instance.instance_id,
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

        destroyed = payload.get('destroy_target_equipments') or []
        self.assertEqual(len(destroyed), 1)
        self.assertEqual(
            destroyed[0]['card_instance']['instance_id'],
            selected.card_instance.instance_id,
        )
        self.assertEqual(
            payload['destroy_target_equipment']['card_instance']['instance_id'],
            selected.card_instance.instance_id,
        )


if __name__ == '__main__':
    unittest.main()
