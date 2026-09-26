# -*- coding: utf-8 -*-
"""休闲花园门票系统核心逻辑测试（设计 2026-09-26）。"""

import gc
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

import db
import leisure_ticket
import leisure_ticket_settlement
import story_score


class _TempDbCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'ticket.sqlite3')
        db.init_db()
        self.user, _ = db.create_user('TicketUser', 'Passw0rd!xyz')

    def tearDown(self):
        db.release_wal_keeper()
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()


class TicketBalanceTests(_TempDbCase):
    def test_grant_respects_cap(self):
        with db.get_db_connection() as conn:
            granted = leisure_ticket.grant_tickets(conn, self.user['id'], 3)
            self.assertEqual(granted, 3)
            granted = leisure_ticket.grant_tickets(conn, self.user['id'], 4)
            self.assertEqual(granted, 2)  # 上限 5
            self.assertEqual(leisure_ticket.get_ticket_balance(conn, self.user['id']), 5)

    def test_consume_ticket(self):
        with db.get_db_connection() as conn:
            leisure_ticket.grant_tickets(conn, self.user['id'], 2)
            self.assertTrue(leisure_ticket.consume_ticket(conn, self.user['id']))
            self.assertEqual(leisure_ticket.get_ticket_balance(conn, self.user['id']), 1)
            self.assertTrue(leisure_ticket.consume_ticket(conn, self.user['id']))
            self.assertFalse(leisure_ticket.consume_ticket(conn, self.user['id']))


class FreeWindowTests(unittest.TestCase):
    def test_free_windows_weekday_cn_time(self):
        # 2026-09-28 是周一
        moment = datetime(2026, 9, 28, 9, 0, tzinfo=leisure_ticket._CN_TZ)
        self.assertTrue(leisure_ticket.is_free_entry_now(moment))
        moment = datetime(2026, 9, 28, 16, 30, tzinfo=leisure_ticket._CN_TZ)
        self.assertTrue(leisure_ticket.is_free_entry_now(moment))
        moment = datetime(2026, 9, 28, 10, 0, tzinfo=leisure_ticket._CN_TZ)
        self.assertFalse(leisure_ticket.is_free_entry_now(moment))
        moment = datetime(2026, 9, 28, 12, 0, tzinfo=leisure_ticket._CN_TZ)
        self.assertFalse(leisure_ticket.is_free_entry_now(moment))

    def test_weekend_not_free(self):
        # 2026-09-26 是周六
        moment = datetime(2026, 9, 26, 9, 0, tzinfo=leisure_ticket._CN_TZ)
        self.assertFalse(leisure_ticket.is_free_entry_now(moment))

    def test_utc_input_maps_to_cn_window(self):
        # UTC 01:30 = UTC+8 的 09:30 → 免费
        moment = datetime(2026, 9, 28, 1, 30, tzinfo=timezone.utc)
        self.assertTrue(leisure_ticket.is_free_entry_now(moment))


class SigninTicketTests(_TempDbCase):
    def test_signin_grants_ticket_and_streak_bonus(self):
        with db.get_db_connection() as conn:
            granted, bonus = leisure_ticket.grant_checkin_tickets(conn, self.user['id'], 7)
            self.assertEqual((granted, bonus), (2, 1))
            granted, bonus = leisure_ticket.grant_checkin_tickets(conn, self.user['id'], 7)
            self.assertEqual((granted, bonus), (0, 0))  # 同日不重复发

    def test_signin_skipped_when_full(self):
        with db.get_db_connection() as conn:
            leisure_ticket.grant_tickets(conn, self.user['id'], 5)
            granted, _ = leisure_ticket.grant_checkin_tickets(conn, self.user['id'], 1)
            self.assertEqual(granted, 0)


class DailyChannelTests(_TempDbCase):
    def test_channel_once_per_day(self):
        with db.get_db_connection() as conn:
            ok, reason = leisure_ticket.claim_daily_channel_ticket(
                conn, self.user['id'], leisure_ticket.CHANNEL_LADDER,
            )
            self.assertEqual((ok, reason), (True, 'granted'))
            ok, reason = leisure_ticket.claim_daily_channel_ticket(
                conn, self.user['id'], leisure_ticket.CHANNEL_LADDER,
            )
            self.assertEqual((ok, reason), (False, 'already_claimed'))

    def test_channel_denied_when_full(self):
        with db.get_db_connection() as conn:
            leisure_ticket.grant_tickets(conn, self.user['id'], 5)
            ok, reason = leisure_ticket.claim_daily_channel_ticket(
                conn, self.user['id'], leisure_ticket.CHANNEL_STORY,
            )
            self.assertEqual((ok, reason), (False, 'cap'))


class PlaySessionTests(_TempDbCase):
    def test_session_consumes_ticket_and_finishes(self):
        with db.get_db_connection() as conn:
            leisure_ticket.grant_tickets(conn, self.user['id'], 1)
        session = leisure_ticket.start_play_session(self.user['id'])
        self.assertTrue(session['active'])
        with db.get_db_connection() as conn:
            self.assertEqual(leisure_ticket.get_ticket_balance(conn, self.user['id']), 0)
        info = leisure_ticket.finish_play_session(self.user['id'])
        self.assertFalse(info['active'])
        # 无票时再开失败
        with self.assertRaises(leisure_ticket.TicketError):
            leisure_ticket.start_play_session(self.user['id'])

    def test_no_duplicate_charge_on_reenter(self):
        with db.get_db_connection() as conn:
            leisure_ticket.grant_tickets(conn, self.user['id'], 2)
        leisure_ticket.start_play_session(self.user['id'])
        leisure_ticket.start_play_session(self.user['id'])  # 活动会话不重复扣票
        with db.get_db_connection() as conn:
            self.assertEqual(leisure_ticket.get_ticket_balance(conn, self.user['id']), 1)

    def test_record_best(self):
        with db.get_db_connection() as conn:
            leisure_ticket.grant_tickets(conn, self.user['id'], 1)
        leisure_ticket.start_play_session(self.user['id'])
        self.assertTrue(leisure_ticket.record_play_result(self.user['id'], '2048', 900, 1024))
        self.assertFalse(leisure_ticket.record_play_result(self.user['id'], '2048', 100, 512))
        self.assertTrue(leisure_ticket.record_play_result(self.user['id'], '2048', 1500, 2048))


class RewardSettlementTests(_TempDbCase):
    def test_ce_tier_rewards_granted_once(self):
        with db.get_db_connection() as conn:
            leisure_ticket.grant_tickets(conn, self.user['id'], 1)
        leisure_ticket.start_play_session(self.user['id'])
        result = leisure_ticket_settlement.record_result_and_grant(self.user['id'], '2048', 5000, 2048)
        amounts = sorted(item['amount'] for item in result['granted'])
        self.assertEqual(amounts, [50, 500, 2000])  # 三档全达 → 全发
        # 第二次同档不重复发
        result = leisure_ticket_settlement.record_result_and_grant(self.user['id'], '2048', 9000, 4096)
        self.assertEqual(result['granted'], [])

    def test_cf_tier_rewards(self):
        with db.get_db_connection() as conn:
            leisure_ticket.grant_tickets(conn, self.user['id'], 1)
        leisure_ticket.start_play_session(self.user['id'])
        result = leisure_ticket_settlement.record_result_and_grant(self.user['id'], 'suika', 3000, 10)
        amounts = sorted(item['amount'] for item in result['granted'])
        self.assertEqual(amounts, [50, 250, 1000])


class StoryScoreTests(unittest.TestCase):
    def _state(self, **overrides):
        state = {
            'stage': 3,
            'completed': True,
            'difficulty': 'normal',
            'normal_battles': 10,
            'encounter_history': {'elite': {'garden': [0, 1], 'desert': [0]}},
            'player': {
                'gold': 25,
                'deck': [{'def_id': 'a'}, {'def_id': 'b'}],
                'relics': ['r1', 'r2'],
                'enchantment_books': [{'id': 'b1'}],
            },
        }
        state.update(overrides)
        return state

    def test_base_score(self):
        # 阶段 3×100 + 三阶段额外 100 + 小怪 10×10 + 精英 3×30 + 金币 25//5×1=5
        # + 卡 2×3 + 天赋 2×5 + 书 1×10
        base = story_score.compute_base_score(self._state())
        self.assertEqual(base, 621)

    def test_difficulty_multipliers(self):
        state = self._state()
        cases = {'easy': 0.5, 'normal': 1.0, 'hard': 1.5, 'lunatic': 2.0}
        for difficulty, mult in cases.items():
            total, _ = story_score.compute_score(state, difficulty, 0)
            self.assertEqual(total, int(621 * mult * 1.5))

    def test_sl_penalty_and_no_sl_bonus(self):
        state = self._state()
        # 无 SL：×1.5；有 SL：max(100-N, 80)/100
        no_sl, _ = story_score.compute_score(state, 'normal', 0)
        five_sl, _ = story_score.compute_score(state, 'normal', 5)
        twelve_sl, _ = story_score.compute_score(state, 'normal', 12)
        self.assertEqual(no_sl, int(621 * 1.5))
        self.assertEqual(five_sl, int(621 * 0.95))
        self.assertEqual(twelve_sl, int(621 * 0.88))

    def test_sl_penalty_floor(self):
        self.assertEqual(story_score.compute_multiplier(50), 0.8)
        self.assertEqual(story_score.compute_multiplier(0), 1.5)


class StorySettlementTests(_TempDbCase):
    def test_settlement_clears_bank_and_grants_dew(self):
        db.set_story_bank(self.user['id'], 500)
        state = {
            'stage': 3,
            'completed': True,
            'difficulty': 'hard',
            'normal_battles': 5,
            'encounter_history': {'elite': {'garden': [0]}},
            'player': {
                'gold': 10,
                'deck': [{'def_id': 'x'}],
                'relics': [],
                'enchantment_books': [],
            },
        }
        with db.get_db_connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            result = story_score.settle_story_clear_conn(
                conn, user_id=self.user['id'], run_id='run-1', state=state,
            )
            conn.commit()
        self.assertEqual(result['bank_cleared'], 500)
        self.assertEqual(db.get_story_bank(self.user['id']), 0)
        self.assertEqual(result['base'], 100 * 3 + 100 + 50 + 30 + 2 + 3)
        self.assertEqual(result['total'], int(result['base'] * 1.5 * 1.5))


if __name__ == '__main__':
    unittest.main()


class LeaderboardPlayModeTests(_TempDbCase):
    """排行榜三类：14d 仅 normal、timed 仅 ticket、all 全计。"""

    _record_seq = 0

    def _insert_record(self, conn, score, play_mode, verified_at=None):
        LeaderboardPlayModeTests._record_seq += 1
        conn.execute(
            '''
            INSERT INTO minigame_2048_records
                (user_id, game_id, score, max_tile, op_index, rules_version,
                 verified_at, source, created_at, game_key, play_mode)
            VALUES (?, 1, ?, 2048, ?, 2, COALESCE(?, datetime('now')), 'online', datetime('now'), '2048', ?)
            ''',
            (self.user['id'], score, LeaderboardPlayModeTests._record_seq, verified_at, play_mode),
        )

    def test_windows_filter_by_play_mode(self):
        import minigame_2048_service as svc
        with db.get_db_connection() as conn:
            svc.ensure_schema(conn)
            self._insert_record(conn, 3000, 'normal')
            self._insert_record(conn, 5000, 'ticket')
            normal_table = svc.leaderboard(conn, window='14d', limit=0)
            timed_table = svc.leaderboard(conn, window='timed', limit=0)
            all_table = svc.leaderboard(conn, window='all', limit=0)
        self.assertEqual([e['score'] for e in normal_table['entries']], [3000])
        self.assertEqual([e['score'] for e in timed_table['entries']], [5000])
        # 总榜全计：每账号一行取最高分（5000）
        self.assertEqual([e['score'] for e in all_table['entries']], [5000])

    def test_two_players_across_modes(self):
        import minigame_2048_service as svc
        other, _ = db.create_user('OtherPlayer', 'Passw0rd!xyz')
        with db.get_db_connection() as conn:
            svc.ensure_schema(conn)
            self._insert_record(conn, 3000, 'normal')
            conn.execute(
                '''
                INSERT INTO minigame_2048_records
                    (user_id, game_id, score, max_tile, op_index, rules_version,
                     verified_at, source, created_at, game_key, play_mode)
                VALUES (?, 2, 9000, 4096, 1, 2, datetime('now'), 'online', datetime('now'), '2048', 'ticket')
                ''',
                (other['id'],),
            )
            normal_table = svc.leaderboard(conn, window='14d', limit=0)
            timed_table = svc.leaderboard(conn, window='timed', limit=0)
            all_table = svc.leaderboard(conn, window='all', limit=0)
        self.assertEqual([e['score'] for e in normal_table['entries']], [3000])
        self.assertEqual([e['score'] for e in timed_table['entries']], [9000])
        self.assertEqual([e['score'] for e in all_table['entries']], [9000, 3000])

    def test_legacy_records_count_as_normal(self):
        import minigame_2048_service as svc
        with db.get_db_connection() as conn:
            svc.ensure_schema(conn)
            # 老记录（补列前的行）play_mode 默认 'normal'
            columns = {row[1] for row in conn.execute('PRAGMA table_info(minigame_2048_records)').fetchall()}
            self.assertIn('play_mode', columns)
            self._insert_record(conn, 2500, 'normal')
            table = svc.leaderboard(conn, window='14d', limit=0)
            self.assertEqual(len(table['entries']), 1)
