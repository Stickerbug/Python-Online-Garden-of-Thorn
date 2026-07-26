import gc
import os
import tempfile
import unittest

import db


class UserKeybindingsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'keybindings.sqlite3')
        db.init_db()
        self.user, error = db.create_user('ShortcutTester', 'Aa1!aaaa')
        self.assertIsNone(error)
        self.assertIsNotNone(self.user)

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def test_row_payload_contains_default_keybinding_config(self):
        user = db.get_user_by_id(self.user['id'])
        self.assertEqual(user['keybindings'], {
            'schema': 1,
            'overrides': {},
            'unbound': [],
            'show_hints': True,
            'revision': 0,
        })

    def test_update_sanitizes_unknown_actions_and_bindings(self):
        config, error = db.update_user_keybindings(
            self.user['id'],
            {
                'overrides': {
                    'end_turn': 'Shift+KeyF',
                    'navigate_left': 'ArrowUp',
                    'navigate_right': 'KeyV',
                    'target_teammate': 'KeyB',
                    'view_log': 'KeyX',
                    'view_spectators': 'KeyC',
                    'select_slot_1': 'Digit2',
                    'refresh': 'Digit3',
                    'toggle_log': 'KeyL',
                    'unknown_action': 'KeyK',
                    'cancel': 'not a key',
                },
                'unbound': ['view_exile', 'unknown_action'],
                'show_hints': False,
            },
            0,
        )
        self.assertIsNone(error)
        self.assertEqual(config['revision'], 1)
        self.assertEqual(config['overrides'], {
            'end_turn': 'Shift+KeyF',
            'navigate_left': 'ArrowUp',
            'navigate_right': 'KeyV',
            'target_teammate': 'KeyB',
            'view_log': 'KeyX',
            'view_spectators': 'KeyC',
        })
        self.assertEqual(config['unbound'], ['view_exile'])
        self.assertFalse(config['show_hints'])

        user = db.get_user_by_id(self.user['id'])
        self.assertEqual(user['keybindings'], config)

    def test_stale_revision_returns_latest_without_overwriting(self):
        first, error = db.update_user_keybindings(
            self.user['id'],
            {'overrides': {'end_turn': 'KeyG'}},
            0,
        )
        self.assertIsNone(error)
        self.assertEqual(first['revision'], 1)

        latest, conflict = db.update_user_keybindings(
            self.user['id'],
            {'overrides': {'end_turn': 'KeyH'}},
            0,
        )
        self.assertEqual(conflict, 'revision_conflict')
        self.assertEqual(latest['revision'], 1)
        self.assertEqual(latest['overrides']['end_turn'], 'KeyG')


if __name__ == '__main__':
    unittest.main()
