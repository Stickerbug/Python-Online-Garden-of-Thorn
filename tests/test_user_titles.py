import gc
import os
import tempfile
import unittest

import db


class UserTitleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'titles.sqlite3')
        db.init_db()
        self.user, error = db.create_user('TitleTester', 'Aa1!aaaa')
        self.assertIsNone(error)
        self.assertIsNotNone(self.user)

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def grant(self, name, color, **kwargs):
        user, center, error = db.admin_grant_user_title(
            self.user['id'],
            name,
            color,
            **kwargs,
        )
        self.assertIsNone(error)
        self.assertEqual(user['id'], self.user['id'])
        return center

    def test_title_color_accepts_rgb_hsv_and_hex(self):
        self.assertEqual(db.normalize_title_color('#3aF'), '#33AAFF')
        self.assertEqual(db.normalize_title_color('RGB(47,128,200)'), '#2F80C8')
        self.assertEqual(db.normalize_title_color('HSV(0,100,100)'), '#FF0000')
        self.assertEqual(db.normalize_title_color('HSV(120,1,1)'), '#00FF00')
        self.assertEqual(db.normalize_title_color('thorn'), 'thorn')
        self.assertEqual(db.normalize_title_color('curse'), 'curse')
        self.assertEqual(db.normalize_title_color('health'), 'health')
        self.assertEqual(db.normalize_title_color('super'), 'super')
        self.assertIsNone(db.normalize_title_color('not-a-color'))

    def test_multiple_titles_can_be_equipped_reordered_and_compacted(self):
        self.grant('甲', '#AA1122', title_id='test:first', equip=True)
        self.grant('乙', 'RGB(20,40,60)', title_id='test:second', equip=True)
        self.grant('丙', 'HSV(200,50,80)', title_id='test:third', equip=True)
        center = self.grant('丁', '#445566', title_id='test:fourth', equip=True)

        self.assertEqual(center['equipped'], ['test:first', 'test:second', 'test:third'])
        self.assertEqual(len(center['items']), 4)

        center, error = db.set_user_equipped_titles(
            self.user['id'],
            ['test:third', 'test:first', 'test:fourth'],
        )
        self.assertIsNone(error)
        self.assertEqual(center['equipped'], ['test:third', 'test:first', 'test:fourth'])

        _, too_many_error = db.set_user_equipped_titles(
            self.user['id'],
            ['test:first', 'test:second', 'test:third', 'test:fourth'],
        )
        self.assertIn('最多佩戴3个称号', too_many_error)

        _, unowned_error = db.set_user_equipped_titles(
            self.user['id'],
            ['test:not-owned'],
        )
        self.assertIn('只能佩戴自己拥有', unowned_error)

        _, center, error = db.admin_remove_user_title(self.user['id'], 'test:first')
        self.assertIsNone(error)
        self.assertEqual(center['equipped'], ['test:third', 'test:fourth'])
        slots = {
            item['id']: item['equipped_slot']
            for item in center['items']
            if item['equipped_slot'] is not None
        }
        self.assertEqual(slots, {'test:third': 1, 'test:fourth': 2})

    def test_identity_does_not_create_or_replace_titles(self):
        self.grant('自定义', '#345678', title_id='test:custom', equip=True)
        _, profile, error = db.admin_set_user_role(
            self.user['id'],
            'contributor',
        )
        self.assertIsNone(error)
        self.assertEqual(profile['equipped_titles'][0]['id'], 'test:custom')
        self.assertEqual(profile['special_role_label'], '')
        self.assertIsNone(profile['name_color'])

        center = db.get_user_title_center(self.user['id'])
        segment_id = center['items'][0]['style']['segments'][0]['id']
        center, error = db.set_user_title_name_style(self.user['id'], 'test:custom', segment_id)
        self.assertIsNone(error)
        self.assertEqual(center['name_style']['paint']['color'], '#345678')
        profile = db.get_user_role_profile(self.user['username'])
        self.assertEqual(profile['name_color'], '#345678')

        self.assertEqual([item['id'] for item in center['items']], ['test:custom'])

        _, clear_error = db.admin_clear_user_role(self.user['id'])
        self.assertIsNone(clear_error)
        remaining = db.get_user_title_center(self.user['id'])
        self.assertEqual([item['id'] for item in remaining['items']], ['test:custom'])

    def test_admin_role_is_limited_to_the_three_developer_accounts(self):
        for index, username in enumerate(('Stickerbug', 'Eric', 'NetherDog'), start=1):
            candidate, error = db.create_user(f'AdminCandidate{index}', 'Aa1!aaaa')
            self.assertIsNone(error)
            with db.get_db_connection() as conn:
                conn.execute(
                    'UPDATE users SET username = ?, username_lower = ? WHERE id = ?',
                    (username, db.normalize_username_key(username), candidate['id']),
                )
                conn.commit()
            _, profile, error = db.admin_set_user_role(candidate['id'], 'admin')
            self.assertIsNone(error)
            self.assertEqual(profile['role_type'], 'admin')

        _, profile, error = db.admin_set_user_role(self.user['id'], 'admin')
        self.assertIsNone(profile)
        self.assertIn('Stickerbug、Eric 或 NetherDog', error)

    def test_init_removes_legacy_role_generated_titles(self):
        with db.get_db_connection() as conn:
            now = db.utc_now()
            conn.execute(
                '''
                INSERT INTO title_catalog (
                    title_id, name, color, source_type, source_ref,
                    purchasable, active, created_at, updated_at
                ) VALUES (?, ?, ?, 'role', 'staff', 0, 1, ?, ?)
                ''',
                ('role:legacy', '旧身份称号', 'bloom', now, now),
            )
            conn.execute(
                '''
                INSERT INTO user_titles (
                    user_id, title_id, acquired_source, acquired_ref, acquired_at, equipped_slot
                ) VALUES (?, ?, 'role', 'staff', ?, 1)
                ''',
                (self.user['id'], 'role:legacy', now),
            )
            conn.commit()

        db.init_db()
        self.assertEqual(db.get_user_title_center(self.user['id'])['items'], [])

    def test_future_achievement_can_grant_a_title(self):
        definition = {
            'id': 'test_achievement_title',
            'reward_title': {
                'id': 'achievement:test-title',
                'name': '先行者',
                'color': 'HSV(45,80,90)',
            },
        }
        with db.get_db_connection() as conn:
            granted = db._award_achievement_title_conn(conn, self.user['id'], definition)
            conn.commit()
        self.assertTrue(granted)

        center = db.get_user_title_center(self.user['id'])
        self.assertEqual(len(center['items']), 1)
        self.assertEqual(center['items'][0]['id'], 'achievement:test-title')
        self.assertEqual(center['items'][0]['acquired_source'], 'achievement')
        self.assertIsNone(center['items'][0]['equipped_slot'])

    def test_rich_title_style_duplicate_inventory_and_duplicate_equip(self):
        center = self.grant(
            '双色称号',
            '{color:#FF0000|id=left}双色{/}{gradient:90deg,#00FF00>#0000FF|id=right}称号{/}',
            title_id='test:styled',
            quantity=2,
        )
        item = center['items'][0]
        self.assertEqual(item['quantity'], 2)
        self.assertEqual([segment['id'] for segment in item['style']['segments']], ['left', 'right'])

        center, error = db.set_user_equipped_titles(
            self.user['id'], ['test:styled', 'test:styled'],
        )
        self.assertIsNone(error)
        self.assertEqual(center['equipped'], ['test:styled', 'test:styled'])
        self.assertEqual(center['items'][0]['equipped_slots'], [1, 2])

        center, error = db.set_user_title_name_style(self.user['id'], 'test:styled', 'right')
        self.assertIsNone(error)
        self.assertEqual(center['name_style']['paint']['kind'], 'gradient')

        _, error = db.set_user_equipped_titles(
            self.user['id'], ['test:styled', 'test:styled', 'test:styled'],
        )
        self.assertIn('只能佩戴自己拥有', error)

    def test_console_catalog_changes_keep_editor_revision_integrity(self):
        before = db.get_title_editor_workspace(self.user['id'])
        center = self.grant(
            '修订测试',
            '{color:#FF0000|id=left}修订{/}{color:#0000FF|id=right}测试{/}',
            title_id='test:revisioned',
        )
        catalog_update = center.get('_catalog_update') or {}
        self.assertGreater(
            int(catalog_update.get('revision_id') or 0),
            int(before['current_revision']['revision_id']),
        )

        center, error = db.set_user_title_name_style(
            self.user['id'], 'test:revisioned', 'right',
        )
        self.assertIsNone(error)
        self.assertIsNotNone(center['name_style'])

        item, error = db.admin_set_title_catalog_style(
            'test:revisioned',
            '{gradient:90deg,#00AA66>#3366FF|id=main}修订测试{/}',
        )
        self.assertIsNone(error)
        self.assertGreater(
            int((item.get('_catalog_update') or {}).get('revision_id') or 0),
            int(catalog_update.get('revision_id') or 0),
        )
        self.assertIsNone(db.get_user_title_center(self.user['id'])['name_style'])
        after = db.get_title_editor_workspace(self.user['id'])
        self.assertTrue(after['integrity_ok'])


if __name__ == '__main__':
    unittest.main()
