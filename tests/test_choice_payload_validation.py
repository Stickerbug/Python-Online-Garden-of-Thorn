import unittest

import app


class ChoicePayloadValidationTests(unittest.TestCase):
    def test_card_instance_ids_can_cross_one_million(self):
        payload = {
            'target_instance_id': 1_000_466,
            'selected_instance_ids': [1_000_467, 1_000_468],
        }

        self.assertEqual(app.validate_choice_payload(payload), payload)

    def test_regular_choice_integer_keeps_tighter_limit(self):
        with self.assertRaisesRegex(ValueError, 'must be <= 1000000'):
            app.validate_choice_payload({'selection_index': 1_000_001})

    def test_card_instance_id_still_has_a_finite_limit(self):
        with self.assertRaisesRegex(ValueError, 'must be <= 1000000000000'):
            app.validate_choice_payload({'target_instance_id': 10**12 + 1})


if __name__ == '__main__':
    unittest.main()
