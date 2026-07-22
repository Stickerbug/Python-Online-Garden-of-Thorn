import json
import gc
import os
import tempfile
import unittest
import zlib

import db
import replay_core
from replay_core import recover_cards_played_from_replay_blob


def encode_replay(replay):
    return zlib.compress(json.dumps(replay, ensure_ascii=False).encode('utf-8'))


class ReplayCardPlayRecoveryTests(unittest.TestCase):
    def test_recovers_round_counters_from_projected_delta_states(self):
        initial_state = {
            'round_num': 1,
            'game_over': False,
            'perspectives': [{
                'spectate_players': [
                    {
                        'player_id': 0,
                        'cards_played_this_turn': {'Basic': 1},
                        'hand': [{'description': 'noise' * 100}],
                    },
                    {
                        'player_id': 1,
                        'cards_played_this_turn': {'Light': 1},
                        'hand': [{'description': 'noise' * 100}],
                    },
                ],
            }],
        }
        counter_patch = {
            '$dict': {
                'perspectives': {
                    '$items': {
                        '0': {
                            '$dict': {
                                'spectate_players': {
                                    '$items': {
                                        '0': {
                                            '$dict': {
                                                'cards_played_this_turn': {
                                                    '$dict': {
                                                        'Basic': {'$set': 2},
                                                        'Orange': {'$set': 1},
                                                    },
                                                },
                                                'hand': {'$set': [{'description': 'more noise' * 100}]},
                                            },
                                        },
                                        '1': {
                                            '$dict': {
                                                'cards_played_this_turn': {
                                                    '$dict': {'Light': {'$set': 2}},
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }
        game_over_patch = {'$dict': {'game_over': {'$set': True}}}
        replay = {
            'meta': {},
            'keyframes': [{'seq': 0, 'round': 1, 'state': initial_state}],
            'actions': [
                {
                    'seq': 1,
                    'round': 1,
                    'type': 'play_card',
                    'actor': 0,
                    'state': {'delta': True, 'patch': counter_patch},
                },
                {
                    'seq': 2,
                    'round': 1,
                    'type': 'response',
                    'actor': 1,
                    'payload': {'card_instance_id': 99},
                    'state': {'delta': True, 'patch': {'$dict': {}}},
                },
                {
                    'seq': 3,
                    'round': 1,
                    'type': 'game_over',
                    'actor': None,
                    'state': {'delta': True, 'patch': game_over_patch},
                },
            ],
        }

        result = recover_cards_played_from_replay_blob(encode_replay(replay), 2)

        self.assertTrue(result['exact'])
        self.assertEqual(result['source'], 'replay_state')
        self.assertEqual(result['counts'], [3, 3])

    def test_prefers_final_cumulative_counters(self):
        state = {
            'round_num': 4,
            'game_over': True,
            'perspectives': [{
                'spectate_players': [
                    {'player_id': 0, 'achievement_total_card_plays': 41},
                    {'player_id': 1, 'achievement_total_card_plays': 37},
                ],
            }],
        }
        replay = {
            'meta': {},
            'keyframes': [],
            'actions': [{'seq': 1, 'round': 4, 'type': 'game_over', 'state': state}],
        }

        result = recover_cards_played_from_replay_blob(encode_replay(replay), 2)

        self.assertTrue(result['exact'])
        self.assertEqual(result['source'], 'replay_total')
        self.assertEqual(result['counts'], [41, 37])

    def test_rejects_oversized_replay_before_decoding(self):
        blob = encode_replay({'meta': {}, 'keyframes': [], 'actions': []})

        result = recover_cards_played_from_replay_blob(
            blob,
            2,
            max_compressed_bytes=max(1, len(blob) - 1),
        )

        self.assertFalse(result['exact'])
        self.assertIn('compressed_too_large', result['reason'])

    def test_rejects_excessive_decoded_size(self):
        blob = encode_replay({
            'meta': {'padding': 'x' * 10000},
            'keyframes': [],
            'actions': [],
        })

        result = recover_cards_played_from_replay_blob(
            blob,
            2,
            max_compressed_bytes=len(blob) + 1,
            max_decoded_bytes=500,
        )

        self.assertFalse(result['exact'])
        self.assertIn('decoded_too_large', result['reason'])


class CardsPlayedBackfillTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'backfill.sqlite3')
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def _create_match(self, first_user, second_user):
        summary = {
            'mode': '1v1',
            'started_at': '2026-07-01T00:00:00Z',
            'ended_at': '2026-07-01T00:10:00Z',
            'duration_seconds': 600,
            'players': [first_user['username'], second_user['username']],
            'player_ids': [first_user['id'], second_user['id']],
            'winner_name': first_user['username'],
            'winner_index': 0,
            'rounds': 2,
            'result': 'win',
            'replay': {
                'keyframes': [],
                'actions': [{
                    'seq': 1,
                    'round': 2,
                    'type': 'game_over',
                    'state': {
                        'round_num': 2,
                        'game_over': True,
                        'perspectives': [{
                            'spectate_players': [
                                {'player_id': 0, 'achievement_total_card_plays': 7},
                                {'player_id': 1, 'achievement_total_card_plays': 9},
                            ],
                        }],
                    },
                }],
            },
        }
        match_id = db.save_match_summary(summary)
        replay_core.save_replay_snapshot(match_id, summary)
        return match_id

    def test_targeted_backfill_is_incremental_and_preserves_other_player(self):
        first_user, error = db.create_user('BackfillOne', 'Aa1!aaaa')
        self.assertIsNone(error)
        second_user, error = db.create_user('BackfillTwo', 'Aa1!aaaa')
        self.assertIsNone(error)
        match_id = self._create_match(first_user, second_user)

        first_result = db.backfill_cards_played_achievements_from_matches(
            dry_run=False,
            limit=20,
            user_id=first_user['id'],
        )
        self.assertEqual(first_result['matches_compensated'], 1)
        self.assertEqual(first_result['cards_total'], 7)
        self.assertEqual(first_result['replay_players'], 1)

        conn = db.get_db_connection()
        try:
            summary = json.loads(conn.execute(
                'SELECT summary_json FROM matches WHERE id = ?',
                (match_id,),
            ).fetchone()['summary_json'])
            first_progress = conn.execute(
                "SELECT progress FROM user_achievements WHERE user_id = ? AND achievement_id = 'cards_played_20000'",
                (first_user['id'],),
            ).fetchone()
            second_progress = conn.execute(
                "SELECT progress FROM user_achievements WHERE user_id = ? AND achievement_id = 'cards_played_20000'",
                (second_user['id'],),
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(summary['cards_played_by_player'], [7, None])
        self.assertEqual(first_progress['progress'], 7)
        self.assertIsNone(second_progress)

        repeated = db.backfill_cards_played_achievements_from_matches(
            dry_run=False,
            limit=20,
            user_id=first_user['id'],
        )
        self.assertEqual(repeated['matches_compensated'], 0)

        second_result = db.backfill_cards_played_achievements_from_matches(
            dry_run=False,
            limit=20,
            user_id=second_user['id'],
        )
        self.assertEqual(second_result['cards_total'], 9)
        conn = db.get_db_connection()
        try:
            summary = json.loads(conn.execute(
                'SELECT summary_json FROM matches WHERE id = ?',
                (match_id,),
            ).fetchone()['summary_json'])
        finally:
            conn.close()
        self.assertEqual(summary['cards_played_by_player'], [7, 9])

    def test_global_backfill_batches_all_players_without_duplicates(self):
        first_user, error = db.create_user('BackfillAllOne', 'Aa1!aaaa')
        self.assertIsNone(error)
        second_user, error = db.create_user('BackfillAllTwo', 'Aa1!aaaa')
        self.assertIsNone(error)
        self._create_match(first_user, second_user)
        self._create_match(first_user, second_user)

        first_batch = db.backfill_cards_played_achievements_from_matches(
            dry_run=False,
            limit=1,
        )
        self.assertEqual(first_batch['matches_compensated'], 1)
        self.assertEqual(first_batch['players_compensated'], 2)
        self.assertEqual(first_batch['cards_total'], 16)
        self.assertTrue(first_batch['batch_limit_reached'])

        second_batch = db.backfill_cards_played_achievements_from_matches(
            dry_run=False,
            limit=1,
        )
        self.assertEqual(second_batch['matches_compensated'], 1)
        self.assertEqual(second_batch['players_compensated'], 2)
        self.assertEqual(second_batch['cards_total'], 16)

        completed = db.backfill_cards_played_achievements_from_matches(
            dry_run=False,
            limit=1,
        )
        self.assertEqual(completed['matches_compensated'], 0)

        conn = db.get_db_connection()
        try:
            event_count = conn.execute(
                "SELECT COUNT(*) AS amount FROM achievement_match_events "
                "WHERE achievement_id = 'metric:cards_played_total'"
            ).fetchone()['amount']
            first_progress = conn.execute(
                "SELECT progress FROM user_achievements WHERE user_id = ? AND achievement_id = 'cards_played_20000'",
                (first_user['id'],),
            ).fetchone()['progress']
            second_progress = conn.execute(
                "SELECT progress FROM user_achievements WHERE user_id = ? AND achievement_id = 'cards_played_20000'",
                (second_user['id'],),
            ).fetchone()['progress']
        finally:
            conn.close()
        self.assertEqual(event_count, 4)
        self.assertEqual(first_progress, 14)
        self.assertEqual(second_progress, 18)


if __name__ == '__main__':
    unittest.main()
