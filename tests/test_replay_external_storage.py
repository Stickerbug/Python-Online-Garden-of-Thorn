import gc
import json
import os
import struct
import tempfile
import unittest

import db
import replay_core
from scripts import migrate_replay_blobs


class ReplayExternalStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        self.old_blob_dir = os.environ.get('GTN_REPLAY_BLOB_DIR')
        db.DB_PATH = os.path.join(self.temp_dir.name, 'gtn.sqlite3')
        os.environ['GTN_REPLAY_BLOB_DIR'] = os.path.join(self.temp_dir.name, 'replay-blobs')
        replay_core._TIMELINE_CACHE.clear()
        db.init_db()

    def tearDown(self):
        replay_core._TIMELINE_CACHE.clear()
        db.DB_PATH = self.old_db_path
        if self.old_blob_dir is None:
            os.environ.pop('GTN_REPLAY_BLOB_DIR', None)
        else:
            os.environ['GTN_REPLAY_BLOB_DIR'] = self.old_blob_dir
        gc.collect()
        self.temp_dir.cleanup()

    def _summary(self, ended_at='2026-07-31T00:00:00Z'):
        return {
            'mode': '1v1',
            'players': ['ReplayOne', 'ReplayTwo'],
            'winner_name': 'ReplayOne',
            'winner_index': 0,
            'rounds': 2,
            'duration_seconds': 30,
            'ended_at': ended_at,
            'replay': {
                'keyframes': [{
                    'seq': 0,
                    'round': 1,
                    'state': {'round_num': 1, 'players': ['ReplayOne', 'ReplayTwo']},
                }],
                'actions': [{
                    'seq': 1,
                    'round': 2,
                    'type': 'game_over',
                    'state': {'round_num': 2, 'game_over': True},
                }],
            },
        }

    def test_new_replay_uses_external_blob_and_remains_readable(self):
        replay_id = replay_core.save_replay_snapshot(1, self._summary())
        with db.get_db_connection() as conn:
            row = conn.execute(
                '''
                SELECT replay_blob, replay_blob_path, replay_size
                FROM match_replays WHERE id = ?
                ''',
                (replay_id,),
            ).fetchone()

        self.assertEqual(bytes(row['replay_blob']), b'')
        self.assertTrue(row['replay_blob_path'])
        self.assertEqual(len(replay_core.load_replay_blob(row)), row['replay_size'])

        package = replay_core.build_replay_download_package(replay_id)
        self.assertTrue(package['payload'].startswith(replay_core.REPLAY_DOWNLOAD_MAGIC))
        timeline = replay_core.replay_timeline(replay_id)
        self.assertGreaterEqual(timeline['total_frames'], 1)

    def test_phelren_replay_keeps_its_prefix_in_lists_timeline_and_download(self):
        summary = self._summary()
        summary['replay_prefix'] = 'P'
        replay_id = replay_core.save_replay_snapshot(7, summary)

        item = replay_core.get_replay(replay_id)
        self.assertEqual(item['replay_prefix'], 'P')
        self.assertEqual(item['replay_ref'], f'P-{replay_id}')

        timeline = replay_core.replay_timeline(replay_id)
        self.assertEqual(timeline['replay']['replay_prefix'], 'P')
        self.assertEqual(timeline['replay']['replay_ref'], f'P-{replay_id}')

        package = replay_core.build_replay_download_package(replay_id)
        self.assertEqual(package['filename'], f'GTN-P-{replay_id}.gtnreplay')
        header_start = len(replay_core.REPLAY_DOWNLOAD_MAGIC)
        header_size = struct.unpack(
            '>I',
            package['payload'][header_start:header_start + 4],
        )[0]
        header = json.loads(
            package['payload'][header_start + 4:header_start + 4 + header_size].decode('utf-8')
        )
        self.assertEqual(header['replay_prefix'], 'P')
        self.assertEqual(header['replay_ref'], f'P-{replay_id}')

    def test_regular_and_phelren_replays_share_one_non_repeating_sequence(self):
        regular_id = replay_core.save_replay_snapshot(10, self._summary())
        phelren_summary = self._summary()
        phelren_summary['replay_prefix'] = 'P'
        phelren_id = replay_core.save_replay_snapshot(11, phelren_summary)
        next_regular_id = replay_core.save_replay_snapshot(12, self._summary())

        self.assertGreater(regular_id, 0)
        self.assertEqual(phelren_id, regular_id + 1)
        self.assertEqual(next_regular_id, phelren_id + 1)

        with db.get_db_connection() as conn:
            conn.execute('DELETE FROM match_replays WHERE id = ?', (phelren_id,))
            conn.commit()

        later_phelren_summary = self._summary()
        later_phelren_summary['replay_prefix'] = 'P'
        later_phelren_id = replay_core.save_replay_snapshot(13, later_phelren_summary)
        self.assertEqual(later_phelren_id, next_regular_id + 1)

    def test_replay_reference_prefix_must_match_stored_prefix(self):
        regular_id = replay_core.save_replay_snapshot(20, self._summary())
        phelren_summary = self._summary()
        phelren_summary['replay_prefix'] = 'P'
        phelren_id = replay_core.save_replay_snapshot(21, phelren_summary)

        self.assertEqual(replay_core.get_replay(f'R-{regular_id}')['id'], regular_id)
        self.assertEqual(replay_core.get_replay(f'P-{phelren_id}')['id'], phelren_id)
        self.assertIsNone(replay_core.get_replay(f'P-{regular_id}'))
        self.assertIsNone(replay_core.get_replay(f'R-{phelren_id}'))

    def test_cleanup_removes_external_blob_file(self):
        replay_id = replay_core.save_replay_snapshot(
            1,
            self._summary(ended_at='2020-01-01T00:00:00Z'),
        )
        with db.get_db_connection() as conn:
            row = conn.execute(
                'SELECT replay_blob_path FROM match_replays WHERE id = ?',
                (replay_id,),
            ).fetchone()
        blob_path = replay_core._replay_blob_full_path(row['replay_blob_path'])
        self.assertTrue(os.path.isfile(blob_path))

        result = replay_core.cleanup_old_replays(retention_days=1)

        self.assertEqual(result['deleted_replays'], 1)
        self.assertEqual(result['deleted_external_files'], 1)
        self.assertFalse(os.path.exists(blob_path))

    def test_legacy_sqlite_blob_still_loads(self):
        payload = b'legacy-replay'
        row = {
            'replay_blob': payload,
            'replay_blob_path': None,
            'replay_size': len(payload),
        }
        self.assertEqual(replay_core.load_replay_blob(row), payload)

    def test_migration_externalizes_legacy_sqlite_blob(self):
        payload = b'legacy-compressed-replay'
        with db.get_db_connection() as conn:
            replay_id = conn.execute(
                '''
                INSERT INTO match_replays (
                    match_id, created_at, replay_version, replay_sha256,
                    replay_size, replay_blob
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (1, '2026-07-31T00:00:00Z', 2, 'legacy-sha', len(payload), payload),
            ).lastrowid
            conn.commit()

        result = migrate_replay_blobs.migrate(batch_size=1)

        self.assertEqual(result['migrated'], 1)
        with db.get_db_connection() as conn:
            row = conn.execute(
                '''
                SELECT replay_blob, replay_blob_path, replay_size
                FROM match_replays WHERE id = ?
                ''',
                (replay_id,),
            ).fetchone()
        self.assertEqual(bytes(row['replay_blob']), b'')
        self.assertTrue(row['replay_blob_path'])
        self.assertEqual(replay_core.load_replay_blob(row), payload)


if __name__ == '__main__':
    unittest.main()
