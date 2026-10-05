# -*- coding: utf-8 -*-
"""休闲分档存档：免费(normal)与门票限时(ticket)活动局互相独立、成绩按对局归属计分。"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db  # noqa: E402
import minigame_2048_service as svc  # noqa: E402
import minigame_suika_service as suika  # noqa: E402


class _TempDbCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.tmp.name, 'gtn.sqlite3')
        db.init_db()
        with db.get_db_connection() as conn:
            svc.ensure_schema(conn)
            suika.ensure_schema(conn)
        with db.get_db_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (id, username, password_hash, created_at)"
                " VALUES (77, 'mode_split_player', 'x', datetime('now'))")
            conn.commit()

    def tearDown(self):
        db.release_wal_keeper()
        db.DB_PATH = self.old_db_path
        import gc
        gc.collect()
        try:
            self.tmp.cleanup()
        except OSError:
            pass  # Windows 下 WAL 句柄偶尔迟放；残留临时目录交由系统清理


class ModeSplit2048Tests(_TempDbCase):
    def test_free_and_ticket_games_are_independent(self):
        with db.get_db_connection() as conn:
            free_state = svc.load_state(conn, 77, play_mode='normal')
            ticket_state = svc.load_state(conn, 77, play_mode='ticket')
            self.assertNotEqual(free_state['game']['game_uid'], ticket_state['game']['game_uid'])
            self.assertEqual(free_state['game']['play_mode'], 'normal')
            self.assertEqual(ticket_state['game']['play_mode'], 'ticket')
            # ticket 局重开不影响 normal 局
            svc.restart_game(conn, 77, play_mode='ticket')
            free_after = svc.load_state(conn, 77, play_mode='normal')
            self.assertEqual(free_after['game']['game_uid'], free_state['game']['game_uid'])

    def test_sync_resolves_by_uid_across_modes(self):
        with db.get_db_connection() as conn:
            ticket_state = svc.load_state(conn, 77, play_mode='ticket')
            uid = ticket_state['game']['game_uid']
            # 当前 normal 模式下同步 ticket 局：按 uid 精确对局，不误判 stale
            result = svc.sync_progress(conn, 77, uid, 0, '', play_mode='normal')
            self.assertEqual(result.get('status'), 'ok')

    def test_record_mode_follows_game(self):
        with db.get_db_connection() as conn:
            ticket_state = svc.load_state(conn, 77, play_mode='ticket')
            game = ticket_state['game']
            uid = game['game_uid']
            # 跨模式同步按 uid 精确对局
            result = svc.sync_progress(conn, 77, uid, 0, '', play_mode='normal')
            self.assertEqual(result.get('status'), 'ok')
            # 记录打点：对局 ticket 档，写入的记录必须带 ticket（归属对局而非同步时刻）
            record = svc._record_progress(
                conn,
                {'user_id': 77, 'game_id': game['game_id'], 'op_index': 3,
                 'rules_version': game['rules_version'], 'score': 0},
                {'score': 40, 'max_tile': 8},
                source='online', play_mode='ticket',
            )
            self.assertIsNotNone(record)
            row = conn.execute(
                "SELECT play_mode FROM minigame_2048_records"
                " WHERE game_id = ? ORDER BY id DESC LIMIT 1",
                (game['game_id'],),
            ).fetchone()
            self.assertEqual(row['play_mode'], 'ticket')


class ModeSplitSuikaTests(_TempDbCase):
    def test_suika_modes_independent(self):
        with db.get_db_connection() as conn:
            free_state = suika.load_state(conn, 77, play_mode='normal')
            ticket_state = suika.load_state(conn, 77, play_mode='ticket')
            # suika 的 load_state 返回裸 game 字典
            self.assertNotEqual(free_state['game_uid'], ticket_state['game_uid'])
            self.assertEqual(free_state['play_mode'], 'normal')
            self.assertEqual(ticket_state['play_mode'], 'ticket')
            # 跨模式按 uid 精确同步
            result = suika.sync_progress(conn, 77, ticket_state['game_uid'], 0, [],
                                         play_mode='normal')
            self.assertEqual(result.get('status'), 'ok')


if __name__ == '__main__':
    unittest.main()
