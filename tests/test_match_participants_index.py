"""Regression tests for the match↔player lookup index (social panel slowness).

Background: ``list_friends`` used to scan the ``matches`` table once per friend
(falling back to a ``player_names_json LIKE '%name%'`` full scan), which blocked
the single-process eventlet server for seconds.  ``_recent_matches_for_user``
now resolves through ``match_participants(user_id, match_id DESC)``.
"""

import gc
import json
import os
import tempfile
import unittest

import db


class MatchParticipantsIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'match-participants.sqlite3')
        db.init_db()
        self.alice, error = db.create_user('IndexAlice', 'Aa1!aaaa')
        self.assertIsNone(error)
        self.bob, error = db.create_user('IndexBob', 'Aa1!aaaa')
        self.assertIsNone(error)

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def save_match(self, player_ids, names, winner='IndexAlice'):
        return db.save_match_summary({
            'mode': '1v1',
            'started_at': '2026-09-11T00:00:00Z',
            'ended_at': '2026-09-11T00:05:00Z',
            'duration_seconds': 300,
            'players': names,
            'player_ids': player_ids,
            'winner_name': winner,
            'winner_index': 0,
            'rounds': 5,
            'mod_source': 'official',
            'mod_hash': 'hash',
            'result': 'win',
            'valid_for_ranking': False,
        })

    def test_save_match_summary_indexes_every_participant(self):
        match_id = self.save_match(
            [self.alice['id'], self.bob['id']],
            [self.alice['username'], self.bob['username']],
        )

        with db.get_db_connection() as conn:
            rows = conn.execute(
                'SELECT match_id, user_id FROM match_participants ORDER BY user_id'
            ).fetchall()
            self.assertEqual(
                [(int(row['match_id']), int(row['user_id'])) for row in rows],
                [
                    (match_id, int(self.alice['id'])),
                    (match_id, int(self.bob['id'])),
                ],
            )
            recent = db._recent_matches_for_user(
                conn, self.alice['id'], self.alice['username'], 5,
            )
            self.assertEqual([int(row['id']) for row in recent], [match_id])

    def test_recent_matches_are_not_limited_to_the_newest_forty_rows(self):
        # 旧实现只扫最近 40 场，对局被挤出去就查不到，还会退化成整表 LIKE。
        old_match_id = self.save_match(
            [self.alice['id'], self.bob['id']],
            [self.alice['username'], self.bob['username']],
        )
        other_names = [f'Filler{i}' for i in range(60)]
        other_ids = [9000 + i for i in range(60)]
        for index in range(60):
            self.save_match(
                [other_ids[index], other_ids[(index + 1) % 60]],
                [other_names[index], other_names[(index + 1) % 60]],
                winner=other_names[index],
            )

        with db.get_db_connection() as conn:
            recent = db._recent_matches_for_user(
                conn, self.alice['id'], self.alice['username'], 5,
            )
            self.assertEqual([int(row['id']) for row in recent], [old_match_id])

    def test_legacy_matches_are_backfilled_into_the_index(self):
        with db.get_db_connection() as conn:
            cursor = conn.execute(
                '''
                INSERT INTO matches (
                    mode, started_at, ended_at, duration_seconds,
                    player_names_json, player_ids_json, winner_name,
                    winner_index, rounds, mod_source, mod_hash, result, summary_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    '1v1', '2026-09-10T00:00:00Z', '2026-09-10T00:05:00Z', 300,
                    json.dumps(['IndexAlice', 'IndexBob'], ensure_ascii=False),
                    json.dumps([self.alice['id'], self.bob['id']], ensure_ascii=False),
                    'IndexAlice', 0, 5, 'official', 'hash', 'win', '{}',
                ),
            )
            legacy_match_id = int(cursor.lastrowid)
            conn.commit()
            self.assertEqual(
                conn.execute('SELECT COUNT(*) AS n FROM match_participants').fetchone()['n'],
                0,
            )

            created = db._backfill_match_participants_conn(conn)
            self.assertEqual(created, 2)

            recent = db._recent_matches_for_user(conn, self.bob['id'], self.bob['username'], 5)
            self.assertEqual([int(row['id']) for row in recent], [legacy_match_id])

            # 幂等：第二次回填不应该重复插入或报错。
            self.assertEqual(db._backfill_match_participants_conn(conn), 0)

    def test_name_only_legacy_matches_are_backfilled_by_username(self):
        with db.get_db_connection() as conn:
            cursor = conn.execute(
                '''
                INSERT INTO matches (
                    mode, started_at, ended_at, duration_seconds,
                    player_names_json, player_ids_json, winner_name,
                    winner_index, rounds, mod_source, mod_hash, result, summary_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    '1v1', '2026-08-01T00:00:00Z', '2026-08-01T00:05:00Z', 300,
                    json.dumps(['IndexAlice', 'IndexBob'], ensure_ascii=False),
                    '', 'IndexAlice', 0, 5, 'official', 'hash', 'win', '{}',
                ),
            )
            legacy_match_id = int(cursor.lastrowid)
            conn.commit()

            self.assertEqual(db._backfill_match_participants_conn(conn), 2)
            recent = db._recent_matches_for_user(conn, self.alice['id'], self.alice['username'], 5)
            self.assertEqual([int(row['id']) for row in recent], [legacy_match_id])

    def test_lookup_uses_the_participants_index(self):
        self.save_match(
            [self.alice['id'], self.bob['id']],
            [self.alice['username'], self.bob['username']],
        )
        with db.get_db_connection() as conn:
            plan = conn.execute(
                '''
                EXPLAIN QUERY PLAN
                SELECT m.* FROM matches m
                JOIN match_participants p ON p.match_id = m.id
                WHERE p.user_id = ?
                ORDER BY m.id DESC
                LIMIT 5
                ''',
                (self.alice['id'],),
            ).fetchall()
        details = ' '.join(str(row['detail']) for row in plan)
        self.assertIn('idx_match_participants_user', details)


if __name__ == '__main__':
    unittest.main()
