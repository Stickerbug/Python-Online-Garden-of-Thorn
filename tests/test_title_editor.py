import gc
import os
import tempfile
import unittest

import db
from title_styles import parse_title_style


class TitleEditorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        self.old_backup_dir = os.environ.get('GTN_TITLE_CATALOG_BACKUP_DIR')
        db.DB_PATH = os.path.join(self.temp_dir.name, 'title-editor.sqlite3')
        os.environ['GTN_TITLE_CATALOG_BACKUP_DIR'] = os.path.join(self.temp_dir.name, 'backups')
        db.init_db()
        self.admin, error = db.create_user('TitleEditorAdmin', 'Aa1!aaaa')
        self.assertIsNone(error)
        self.actor = {
            'user_id': self.admin['id'],
            'username': self.admin['username'],
            'ip': '127.0.0.1',
        }

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        if self.old_backup_dir is None:
            os.environ.pop('GTN_TITLE_CATALOG_BACKUP_DIR', None)
        else:
            os.environ['GTN_TITLE_CATALOG_BACKUP_DIR'] = self.old_backup_dir
        gc.collect()
        self.temp_dir.cleanup()

    def changed_catalog(self, workspace, suffix='edited'):
        catalog = {
            'schema_version': 1,
            'titles': [dict(item) for item in workspace['catalog']['titles']],
        }
        item = catalog['titles'][0]
        markup = f'{{gradient:90deg,#FF3344>#3478F6|id=main}}{item["name"]}{{/}}'
        item['style'] = parse_title_style(markup)
        item['style_markup'] = markup
        item['source_ref'] = suffix
        item['shop_weight'] = int(item.get('shop_weight') or 0) + 1
        return catalog, item['id']

    def test_draft_publish_backup_and_rollback_lifecycle(self):
        initial = db.get_title_editor_workspace(self.admin['id'])
        initial_revision = initial['current_revision']['revision_id']
        catalog, changed_id = self.changed_catalog(initial)

        draft, error = db.save_title_editor_draft(
            self.admin['id'], initial_revision, catalog,
        )
        self.assertIsNone(error)
        self.assertFalse(draft['stale'])
        self.assertEqual(draft['diff']['changed_count'], 1)
        self.assertEqual(draft['diff']['changed_ids'], [changed_id])

        reloaded = db.get_title_editor_workspace(self.admin['id'])
        self.assertIsNotNone(reloaded['draft'])
        self.assertEqual(reloaded['draft']['base_revision_id'], initial_revision)

        published, error = db.publish_title_editor_draft(
            self.admin['id'], actor=self.actor, message='Editor lifecycle test',
        )
        self.assertIsNone(error)
        self.assertGreater(published['revision_id'], initial_revision)
        self.assertEqual(published['diff']['changed_ids'], [changed_id])
        self.assertFalse(published['backup_errors'])
        backup_files = os.listdir(os.environ['GTN_TITLE_CATALOG_BACKUP_DIR'])
        self.assertTrue(any(name.startswith('revision-') for name in backup_files))
        self.assertTrue(any(name.startswith('daily-') for name in backup_files))

        live = db.get_title_editor_workspace(self.admin['id'])
        changed = next(item for item in live['catalog']['titles'] if item['id'] == changed_id)
        self.assertEqual(changed['source_ref'], 'edited')
        self.assertEqual(changed['style']['segments'][0]['paint']['kind'], 'gradient')
        self.assertIsNone(live['draft'])

        rolled_back, error = db.rollback_title_catalog_revision(
            self.admin['id'], initial_revision, actor=self.actor,
        )
        self.assertIsNone(error)
        self.assertGreater(rolled_back['revision_id'], published['revision_id'])
        restored = db.get_title_editor_workspace(self.admin['id'])
        restored_item = next(item for item in restored['catalog']['titles'] if item['id'] == changed_id)
        initial_item = next(item for item in initial['catalog']['titles'] if item['id'] == changed_id)
        self.assertEqual(restored_item['source_ref'], initial_item['source_ref'])
        self.assertEqual(restored_item['style'], initial_item['style'])

    def test_existing_title_cannot_be_removed_from_editor_catalog(self):
        workspace = db.get_title_editor_workspace(self.admin['id'])
        catalog = {
            'schema_version': 1,
            'titles': workspace['catalog']['titles'][1:],
        }
        draft, error = db.save_title_editor_draft(
            self.admin['id'], workspace['current_revision']['revision_id'], catalog,
        )
        self.assertIsNone(draft)
        self.assertIn('不能永久删除', error)

    def test_stale_draft_cannot_overwrite_a_newer_revision(self):
        second_user, error = db.create_user('TitleEditorStaff', 'Aa1!aaaa')
        self.assertIsNone(error)
        workspace = db.get_title_editor_workspace(self.admin['id'])
        revision = workspace['current_revision']['revision_id']
        first_catalog, _ = self.changed_catalog(workspace, suffix='first')
        second_catalog, _ = self.changed_catalog(workspace, suffix='second')

        _, error = db.save_title_editor_draft(self.admin['id'], revision, first_catalog)
        self.assertIsNone(error)
        _, error = db.save_title_editor_draft(second_user['id'], revision, second_catalog)
        self.assertIsNone(error)
        _, error = db.publish_title_editor_draft(self.admin['id'], actor=self.actor)
        self.assertIsNone(error)

        result, error = db.publish_title_editor_draft(
            second_user['id'],
            actor={'user_id': second_user['id'], 'username': second_user['username']},
        )
        self.assertIsNone(result)
        self.assertIn('其他人', error)
        stale = db.get_title_editor_workspace(second_user['id'])
        self.assertTrue(stale['draft']['stale'])


if __name__ == '__main__':
    unittest.main()
