# -*- coding: utf-8 -*-
"""故事模式「旅程历史」（2026-10-09）：摘要落库、弃局挂钩、列表与详情。

跑在独立临时库上，不碰真实旅程数据。
"""

from __future__ import annotations

import gc
import os
import tempfile
import unittest

import db
import story_history


def _make_state(phase='journey_setup', character_id='orbiter', floor=12, gold=233):
    return {
        'schema_version': 1,
        'content_version': 'story-redesign-10-test',
        'phase': phase,
        'character_id': character_id,
        'difficulty': 'hard',
        'journey_mode': 'standard',
        'stage': 2,
        'current_floor': floor,
        'current_node_id': 'n-1',
        'journey_seed': 'seed-abc',
        'player': {
            'health': 44,
            'max_health': 80,
            'gold': gold,
            'deck': [
                {'def_id': 'basic', 'upgraded': False},
                {'def_id': 'web', 'upgraded': True},
                {'def_id': 'knife', 'upgraded': True},
            ],
            'relics': ['orbital_surround', 'energetic'],
        },
        'map': {
            'floors': [
                {'nodes': [
                    {'id': 'n-1', 'type': 'combat', 'status': 'completed', 'floor': 1},
                    {'id': 'n-2', 'type': 'elite', 'status': 'available', 'floor': 1},
                ]},
            ],
            'edges': [{'from': 'n-1', 'to': 'n-2'}],
        },
    }


class _TempDbCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'story-history.sqlite3')
        db.init_db()
        self.user_a, _ = db.create_user('HistTesterA', 'Aa1!aaaa')
        self.user_b, _ = db.create_user('HistTesterB', 'Aa1!aaaa')
        self.uid_a = int(self.user_a['id'])
        self.uid_b = int(self.user_b['id'])

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        gc.collect()   # Windows：释放连接池对临时库文件的占用
        self.temp_dir.cleanup()


class StoryHistoryServiceTests(_TempDbCase):
    def test_record_and_list_with_filters(self):
        with db.get_db_connection() as conn:
            story_history.record_run_summary_conn(
                conn, 'run-a', self.uid_a, _make_state(phase='complete'),
                started_at='2026-10-09T01:00:00Z', ended_at='2026-10-09T02:30:00Z',
                result='victory',
            )
            story_history.record_run_summary_conn(
                conn, 'run-b', self.uid_a, _make_state(phase='game_over', character_id='mage', floor=5),
                started_at='2026-10-09T03:00:00Z', ended_at='2026-10-09T03:20:00Z',
                result='defeat',
            )
            conn.commit()
            rows = story_history.list_history(conn, self.uid_a)
        self.assertEqual([row['run_id'] for row in rows], ['run-b', 'run-a'])
        victory = next(row for row in rows if row['run_id'] == 'run-a')
        self.assertEqual(victory['result'], 'victory')
        self.assertEqual(victory['character_id'], 'orbiter')
        self.assertEqual(victory['stage_reached'], 2)
        self.assertEqual(victory['floor_reached'], 12)
        self.assertEqual(victory['deck_size'], 3)
        self.assertEqual(victory['upgrade_count'], 2)
        self.assertEqual(victory['relic_count'], 2)
        self.assertEqual(victory['gold'], 233)
        self.assertEqual(victory['duration_seconds'], 5400)
        with db.get_db_connection() as conn:
            only_defeat = story_history.list_history(conn, self.uid_a, result='defeat')
            only_mage = story_history.list_history(conn, self.uid_a, character_id='mage')
            others = story_history.list_history(conn, 99999)
        self.assertEqual([row['run_id'] for row in only_defeat], ['run-b'])
        self.assertEqual([row['run_id'] for row in only_mage], ['run-b'])
        self.assertEqual(others, [])

    def test_abandon_hook_records_defeat_and_abandoned(self):
        state_over = _make_state(phase='game_over')
        state_mid = _make_state(phase='room', character_id='mage')
        run1, _ = db.create_story_run(self.uid_a, 'seed-1', 'story-redesign-10-test', state_over)
        run2, _ = db.create_story_run(self.uid_b, 'seed-2', 'story-redesign-10-test', state_mid)
        self.assertTrue(db.abandon_story_run(self.uid_a, run1['id']))
        self.assertTrue(db.abandon_story_run(self.uid_b, run2['id']))
        with db.get_db_connection() as conn:
            rows7 = story_history.list_history(conn, self.uid_a)
            rows8 = story_history.list_history(conn, self.uid_b)
        self.assertEqual(len(rows7), 1)
        self.assertEqual(rows7[0]['result'], 'defeat')      # game_over → 战败
        self.assertEqual(len(rows8), 1)
        self.assertEqual(rows8[0]['result'], 'abandoned')   # 中途弃局

    def test_abandon_does_not_overwrite_existing_summary(self):
        state = _make_state(phase='complete')
        run, _ = db.create_story_run(self.uid_a, 'seed-3', 'story-redesign-10-test', state)
        with db.get_db_connection() as conn:
            story_history.record_run_summary_conn(
                conn, run['id'], self.uid_a, state,
                started_at='2026-10-09T01:00:00Z', ended_at='2026-10-09T01:10:00Z',
                result='victory',
            )
            conn.commit()
        db.abandon_story_run(self.uid_a, run['id'])  # 通关后 UI 关闭旧局
        with db.get_db_connection() as conn:
            rows = story_history.list_history(conn, self.uid_a)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['result'], 'victory')      # 不被覆盖

    def test_detail_includes_deck_relics_map_route(self):
        state = _make_state(phase='game_over')
        run, _ = db.create_story_run(self.uid_a, 'seed-4', 'story-redesign-10-test', state)
        db.abandon_story_run(self.uid_a, run['id'])
        with db.get_db_connection() as conn:
            detail = story_history.get_history_detail(conn, self.uid_a, run['id'])
            missing = story_history.get_history_detail(conn, self.uid_a, 'no-such-run')
        self.assertIsNone(missing)
        self.assertEqual(detail['summary']['result'], 'defeat')
        self.assertEqual(len(detail['deck']), 3)
        self.assertEqual(detail['deck'][1], {'def_id': 'web', 'upgraded': True})
        self.assertEqual(detail['relics'], ['orbital_surround', 'energetic'])
        self.assertEqual(detail['map']['current_node_id'], 'n-1')
        self.assertEqual(detail['route']['completed_nodes'], 1)
        self.assertEqual(detail['route']['visited'], [{'floor': 1, 'type': 'combat', 'final': False}])

    def test_detail_appends_unfinished_final_node(self):
        state = _make_state(phase='game_over')
        state['current_node_id'] = 'n-2'
        run, _ = db.create_story_run(self.uid_a, 'seed-5', 'story-redesign-10-test', state)
        db.abandon_story_run(self.uid_a, run['id'])
        with db.get_db_connection() as conn:
            detail = story_history.get_history_detail(conn, self.uid_a, run['id'])
        self.assertEqual(detail['route']['completed_nodes'], 1)
        self.assertEqual(detail['route']['visited'], [
            {'floor': 1, 'type': 'combat', 'final': False},
            {'floor': 1, 'type': 'elite', 'final': True},
        ])


if __name__ == '__main__':
    unittest.main()
