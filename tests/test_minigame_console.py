# -*- coding: utf-8 -*-
"""休闲花园管理命令：state/score/record/reset/top/periods/settle（内存库，不碰真实数据）。"""

import os
import gc
import tempfile
import unittest

import app
import db
import minigame_2048_service as base2048
import minigame_suika_service as suika


class MinigameConsoleCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        self.old_db_available = app.DB_AVAILABLE
        db.DB_PATH = os.path.join(self.temp_dir.name, 'minigame-console.sqlite3')
        db.init_db()
        app.DB_AVAILABLE = True
        self.user, error = db.create_user('MgConsole', 'Aa1!aaaa')
        self.assertIsNone(error)

    def tearDown(self):
        app.DB_AVAILABLE = self.old_db_available
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def run_command(self, line):
        return app.execute_admin_command(line, actor='test-console')

    def _active_score(self):
        state = base2048.load_state(self._conn(), self.user['id'])
        return int(state['game']['score'])

    def test_state_score_reset_roundtrip(self):
        self.assertEqual(self._active_score(), 0)
        out = self.run_command('minigame score 2048 MgConsole 4321')
        self.assertTrue(out['success'], out)
        self.assertIn('4321', out['output'])
        self.assertEqual(self._active_score(), 4321)
        out = self.run_command('minigame state 2048 MgConsole')
        self.assertTrue(out['success'], out)
        self.assertIn('4321', out['output'])
        out = self.run_command('minigame reset 2048 MgConsole')
        self.assertTrue(out['success'], out)
        self.assertEqual(self._active_score(), 0)
        # 不存在的游戏名/账号
        self.assertFalse(self.run_command('minigame state tetris MgConsole')['success'])
        self.assertFalse(self.run_command('minigame state 2048 NoSuchUser')['success'])

    def _bust_leaderboard_cache(self):
        # 榜单有 15 秒进程内缓存：改完记录后清掉，让 top 立即反映新数据
        try:
            base2048._LEADERBOARD_CACHE.clear()
        except Exception:
            pass

    def test_record_add_clear_and_top(self):
        out = self.run_command(f'minigame record add suika MgConsole 5000 8')
        self.assertTrue(out['success'], out)
        out = self.run_command(f'minigame record add suika MgConsole 900 5')
        self.assertTrue(out['success'], out)
        self._bust_leaderboard_cache()
        top = self.run_command('minigame top suika all 10')
        self.assertTrue(top['success'], top)
        self.assertIn('5000', top['output'])
        # 指定分数清除
        out = self.run_command(f'minigame record clear suika MgConsole 900')
        self.assertTrue(out['success'], out)
        self._bust_leaderboard_cache()
        top = self.run_command('minigame top suika all 10')
        self.assertNotIn('900', top['output'])
        # 清空剩余
        out = self.run_command(f'minigame record clear suika MgConsole')
        self.assertTrue(out['success'], out)
        self._bust_leaderboard_cache()
        top = self.run_command('minigame top suika all 10')
        self.assertNotIn('5000', top['output'])

    def test_settle_and_periods_for_both_games(self):
        for game in ('2048', 'suika'):
            out = self.run_command(f'minigame settle {game}')
            self.assertTrue(out['success'], out)
            out = self.run_command(f'minigame periods {game} 5')
            self.assertTrue(out['success'], out)

    def _conn(self):
        import sqlite3
        conn = sqlite3.connect(db.DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


if __name__ == '__main__':
    unittest.main()
