import gc
import os
import tempfile
import unittest
from unittest.mock import patch

import db


NEXT_SEASON = {
    'id': 'S-test-next',
    'name': 'S-test-next',
    'starts_at': '2099-02-01T00:00:00Z',
    'ends_at': '2099-02-28T23:59:59Z',
    'next_starts_at': '2099-03-01T00:00:00Z',
}


class GrSeasonResetDewTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'gr-season-reset.sqlite3')
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
                    gr_season_id = 'S-test-old',
                    thorn_dew_free = ?,
                    thorn_dew_paid = 7
                WHERE id = ?
                ''',
                (season_gr, thorn_dew, self.user['id']),
            )
            conn.commit()

    def read_user_and_transactions(self):
        with db.get_db_connection() as conn:
            user = conn.execute(
                'SELECT * FROM users WHERE id = ?',
                (self.user['id'],),
            ).fetchone()
            transactions = conn.execute(
                '''
                SELECT * FROM user_currency_transactions
                WHERE user_id = ? AND source_type = 'gr_season_reset'
                ORDER BY id
                ''',
                (self.user['id'],),
            ).fetchall()
            return user, transactions

    def test_actual_rating_reduction_awards_fifty_free_dew_per_point(self):
        self.set_old_season(1400, thorn_dew=25)

        with patch.object(db, 'current_gr_season', return_value=NEXT_SEASON):
            db.ensure_current_gr_season([self.user['id']])

        user, transactions = self.read_user_and_transactions()
        self.assertEqual(user['season_gr'], 1200)
        self.assertEqual(user['season_ranked_games'], 0)
        self.assertEqual(user['gr_season_id'], NEXT_SEASON['id'])
        self.assertEqual(user['thorn_dew_free'], 10025)
        self.assertEqual(user['thorn_dew_paid'], 7)
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0]['free_delta'], 10000)
        self.assertEqual(transactions[0]['source_id'], 'S-test-old->S-test-next')
        self.assertIn('1400.0→1200.0', transactions[0]['reason'])

    def test_repeat_season_checks_do_not_award_twice(self):
        self.set_old_season(1400)

        with patch.object(db, 'current_gr_season', return_value=NEXT_SEASON):
            db.ensure_current_gr_season([self.user['id']])
            db.ensure_current_gr_season([self.user['id']])

        user, transactions = self.read_user_and_transactions()
        self.assertEqual(user['thorn_dew_free'], 10000)
        self.assertEqual(len(transactions), 1)

    def test_rating_increase_from_soft_reset_has_no_reward(self):
        self.set_old_season(800, thorn_dew=30)

        with patch.object(db, 'current_gr_season', return_value=NEXT_SEASON):
            db.ensure_current_gr_season([self.user['id']])

        user, transactions = self.read_user_and_transactions()
        self.assertEqual(user['season_gr'], 900)
        self.assertEqual(user['thorn_dew_free'], 30)
        self.assertEqual(transactions, [])

    def test_zero_rating_is_not_mistaken_for_the_initial_rating(self):
        self.set_old_season(0, thorn_dew=30)

        with patch.object(db, 'current_gr_season', return_value=NEXT_SEASON):
            db.ensure_current_gr_season([self.user['id']])

        user, transactions = self.read_user_and_transactions()
        self.assertEqual(user['season_gr'], 850)
        self.assertEqual(user['thorn_dew_free'], 30)
        self.assertEqual(transactions, [])

    def test_soft_reset_cap_uses_the_full_actual_reduction(self):
        self.set_old_season(1800)

        with patch.object(db, 'current_gr_season', return_value=NEXT_SEASON):
            db.ensure_current_gr_season([self.user['id']])

        user, transactions = self.read_user_and_transactions()
        self.assertEqual(user['season_gr'], 1250)
        self.assertEqual(user['thorn_dew_free'], 27500)
        self.assertEqual(transactions[0]['free_delta'], 27500)


if __name__ == '__main__':
    unittest.main()
