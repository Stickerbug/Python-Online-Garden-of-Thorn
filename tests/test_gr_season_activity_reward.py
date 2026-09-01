import gc
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import db


OLD_SEASON_ID = 'S209901'
NEXT_SEASON = {
    'id': 'S209902',
    'name': 'S209902',
    'starts_at': '2099-01-31T16:00:00Z',
    'ends_at': '2099-02-28T15:59:59Z',
    'next_starts_at': '2099-02-28T16:00:00Z',
}


class GrSeasonActivityRewardTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'gr-season-activity.sqlite3')
        db.init_db()
        self.user, error = db.create_user('SeasonGRTester', 'Aa1!aaaa')
        self.assertIsNone(error)
        self.assertIsNotNone(self.user)

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def set_old_season(self, season_gr, thorn_dew=0):
        with db.get_db_connection() as conn:
            conn.execute(
                '''
                UPDATE users
                SET season_gr = ?,
                    season_ranked_games = 12,
                    gr_season_id = ?,
                    thorn_dew_free = ?,
                    thorn_dew_paid = 7
                WHERE id = ?
                ''',
                (season_gr, OLD_SEASON_ID, thorn_dew, self.user['id']),
            )
            conn.commit()

    def settle(self, valid_matches=20, random_value=0.5):
        counts = {int(self.user['id']): int(valid_matches)}
        with (
            patch.object(db, 'current_gr_season', return_value=NEXT_SEASON),
            patch.object(
                db,
                '_gr_season_valid_match_counts_for_conn',
                return_value=counts,
            ),
            patch.object(db, '_gr_season_activity_random', return_value=random_value),
        ):
            db.ensure_current_gr_season([self.user['id']])

    def read_settlement(self):
        with db.get_db_connection() as conn:
            user = conn.execute(
                'SELECT * FROM users WHERE id = ?',
                (self.user['id'],),
            ).fetchone()
            transactions = conn.execute(
                '''
                SELECT * FROM user_currency_transactions
                WHERE user_id = ? AND source_type = 'season_activity_reward'
                ORDER BY id
                ''',
                (self.user['id'],),
            ).fetchall()
            rewards = conn.execute(
                '''
                SELECT * FROM gr_season_activity_rewards
                WHERE user_id = ?
                ORDER BY season_id
                ''',
                (self.user['id'],),
            ).fetchall()
            return user, transactions, rewards

    def test_eligible_user_receives_formula_reward(self):
        self.set_old_season(1400, thorn_dew=25)

        self.settle(valid_matches=20, random_value=0.5)

        user, transactions, rewards = self.read_settlement()
        self.assertEqual(user['season_gr'], 1200)
        self.assertEqual(user['season_ranked_games'], 0)
        self.assertEqual(user['gr_season_id'], NEXT_SEASON['id'])
        self.assertEqual(user['thorn_dew_free'], 31425)
        self.assertEqual(user['thorn_dew_paid'], 7)
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0]['free_delta'], 31400)
        self.assertEqual(transactions[0]['source_id'], OLD_SEASON_ID)
        self.assertIn('赛季活跃奖励', transactions[0]['reason'])
        self.assertEqual(len(rewards), 1)
        self.assertEqual(rewards[0]['season_gr'], 1400)
        self.assertEqual(rewards[0]['valid_matches'], 20)
        self.assertAlmostEqual(rewards[0]['random_value'], 0.5)
        self.assertEqual(rewards[0]['reward_dew'], 31400)

    def test_repeat_season_checks_do_not_award_twice(self):
        self.set_old_season(1400)
        self.settle()
        self.settle(random_value=0.9)

        user, transactions, rewards = self.read_settlement()
        self.assertEqual(user['thorn_dew_free'], 31400)
        self.assertEqual(len(transactions), 1)
        self.assertEqual(len(rewards), 1)
        self.assertAlmostEqual(rewards[0]['random_value'], 0.5)

    def test_nineteen_valid_matches_are_not_eligible(self):
        self.set_old_season(1400, thorn_dew=30)

        self.settle(valid_matches=19)

        user, transactions, rewards = self.read_settlement()
        self.assertEqual(user['season_gr'], 1200)
        self.assertEqual(user['thorn_dew_free'], 30)
        self.assertEqual(transactions, [])
        self.assertEqual(rewards, [])

    def test_low_rating_still_receives_activity_reward(self):
        self.set_old_season(800, thorn_dew=30)

        self.settle()

        user, transactions, rewards = self.read_settlement()
        self.assertEqual(user['season_gr'], 900)
        self.assertEqual(user['thorn_dew_free'], 1130)
        self.assertEqual(transactions[0]['free_delta'], 1100)
        self.assertEqual(rewards[0]['reward_dew'], 1100)

    def test_reward_is_capped_at_one_hundred_thousand(self):
        self.set_old_season(1800)

        self.settle()

        user, transactions, rewards = self.read_settlement()
        self.assertEqual(user['season_gr'], 1250)
        self.assertEqual(user['thorn_dew_free'], 100000)
        self.assertEqual(transactions[0]['free_delta'], 100000)
        self.assertEqual(rewards[0]['reward_dew'], 100000)

    def test_formula_rounds_up_to_hundreds(self):
        self.assertEqual(db._calculate_gr_season_activity_reward(0, 0.0), 100)
        self.assertEqual(db._calculate_gr_season_activity_reward(1000, 0.5), 3100)
        self.assertEqual(db._calculate_gr_season_activity_reward(1800, 0.5), 100000)

    def test_formula_clamps_random_value_and_handles_non_finite_input(self):
        self.assertEqual(
            db._calculate_gr_season_activity_reward(1000, -1),
            db._calculate_gr_season_activity_reward(1000, 0),
        )
        self.assertEqual(
            db._calculate_gr_season_activity_reward(1000, 2),
            db._calculate_gr_season_activity_reward(1000, 1),
        )
        self.assertEqual(
            db._calculate_gr_season_activity_reward(1000, float('nan')),
            db._calculate_gr_season_activity_reward(1000, 0),
        )
        self.assertEqual(
            db._calculate_gr_season_activity_reward(1000, float('inf')),
            db._calculate_gr_season_activity_reward(1000, 0),
        )

    def test_formula_curve_boundary_and_cap_are_stable(self):
        samples = (
            (799.999, 0.0, 1100),
            (800.0, 0.0, 1100),
            (800.001, 0.0, 1100),
            (1799.0, 0.0, 100000),
            (1000000.0, 1.0, 100000),
        )
        for season_gr, random_value, expected in samples:
            with self.subTest(season_gr=season_gr, random_value=random_value):
                self.assertEqual(
                    db._calculate_gr_season_activity_reward(season_gr, random_value),
                    expected,
                )

    def test_valid_match_counter_uses_normal_effective_match_rules(self):
        valid_summary = {
            'mode': '1v1',
            'started_at': '2099-01-10T00:00:00Z',
            'ended_at': '2099-01-10T00:01:00Z',
            'duration_seconds': 60,
            'players': [self.user['username'], 'GuestOpponent'],
            'player_ids': [self.user['id'], None],
            'winner_name': self.user['username'],
            'winner_index': 0,
            'result': 'win',
            'valid_action_counts_by_side': [1, 1],
        }
        db.save_match_summary(valid_summary)
        by_name_summary = dict(valid_summary)
        by_name_summary.update({
            'started_at': '2099-01-11T00:00:00Z',
            'ended_at': '2099-01-11T00:01:00Z',
            'player_ids': [None, None],
        })
        db.save_match_summary(by_name_summary)
        too_short = dict(valid_summary)
        too_short.update({
            'started_at': '2099-01-12T00:00:00Z',
            'ended_at': '2099-01-12T00:00:19Z',
            'duration_seconds': 19,
        })
        db.save_match_summary(too_short)
        no_actions = dict(valid_summary)
        no_actions.update({
            'started_at': '2099-01-13T00:00:00Z',
            'ended_at': '2099-01-13T00:01:00Z',
            'valid_action_counts_by_side': [1, 0],
        })
        db.save_match_summary(no_actions)
        outside_season = dict(valid_summary)
        outside_season.update({
            'started_at': '2099-02-01T00:00:00Z',
            'ended_at': '2099-02-01T00:01:00Z',
        })
        db.save_match_summary(outside_season)

        with db.get_db_connection() as conn:
            counts = db._gr_season_valid_match_counts_for_conn(
                conn,
                [self.user['id']],
                OLD_SEASON_ID,
            )

        self.assertEqual(counts[self.user['id']], 2)

    def test_s1_period_is_preserved_as_july_2026(self):
        self.assertEqual(
            db._gr_season_period('S1'),
            ('2026-06-30T16:00:00Z', '2026-07-31T16:00:00Z'),
        )

    def test_season_changes_at_beijing_month_boundary(self):
        before = db.current_gr_season(
            datetime(2026, 7, 31, 15, 59, 59, tzinfo=timezone.utc)
        )
        after = db.current_gr_season(
            datetime(2026, 7, 31, 16, 0, 0, tzinfo=timezone.utc)
        )

        self.assertEqual(before['id'], 'R1-S202607')
        self.assertEqual(after['id'], 'R1-S202608')
        self.assertEqual(after['starts_at'], '2026-07-31T16:00:00Z')


if __name__ == '__main__':
    unittest.main()
