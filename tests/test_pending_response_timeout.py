"""响应窗口的服务端时限。

反馈：打出技能牌后界面一直停在「等待响应」，要等 120 秒挂起看门狗才继续。
原因是响应窗口只有客户端 5 秒倒计时，服务端没有 deadline；对方客户端挂起
（手机切后台/锁屏）时那次倒计时不会跑，出牌方就只能干等。
"""

import time
import unittest
from pathlib import Path
from unittest import mock

import app


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (ROOT / 'app.py').read_text(encoding='utf-8')


class _FakeEngine:
    def __init__(self, pending):
        self.pending_response = pending
        self.phase = 'response'
        self.passes = []

    def handle_response(self, responder_id, card_instance_id):
        self.passes.append((int(responder_id), card_instance_id))
        pending = self.pending_response
        if not isinstance(pending, dict):
            return {'success': True}
        entries = pending.get('counter_cards')
        if isinstance(entries, list):
            pending['counter_cards'] = [
                item for item in entries
                if int(item.get('responder_id', -1)) != int(responder_id)
            ]
        responders = pending.get('responder_ids')
        if isinstance(responders, list):
            pending['responder_ids'] = [
                item for item in responders if int(item) != int(responder_id)
            ]
        if entries is not None and not pending.get('counter_cards') and not pending.get('responder_ids'):
            self.pending_response = None
        return {'success': True}


class _FakeRoom:
    def __init__(self, mode='1v1', player_sids=None, room_id=1, engine=None):
        self.mode = mode
        self.player_sids = list(player_sids or ['sid-a', 'sid-b'])
        self.room_id = room_id
        self.engine = engine


class PendingResponseTimeoutTests(unittest.TestCase):
    def _room_1v1(self, created_offset):
        pending = {
            'player_id': 0,
            'target_player_id': 1,
            'counter_cards': [{'responder_id': 1, 'instance_id': 'c1'}],
            '_created_at': time.time() + created_offset,
        }
        engine = _FakeEngine(pending)
        return _FakeRoom(engine=engine), engine

    def test_response_window_expires_after_server_deadline(self):
        room, engine = self._room_1v1(-(app.RESPONSE_WINDOW_SECONDS + 5))
        self.assertTrue(app._expire_pending_response_locked(room))
        self.assertEqual(engine.passes, [(1, None)])
        self.assertIsNone(engine.pending_response)

    def test_response_window_waits_before_deadline(self):
        room, engine = self._room_1v1(-1)
        self.assertFalse(app._expire_pending_response_locked(room))
        self.assertEqual(engine.passes, [])
        self.assertIsNotNone(engine.pending_response)

    def test_2v2_window_passes_every_pending_responder(self):
        pending = {
            'player_id': 0,
            'responder_ids': [1, 3],
            'counter_cards': [
                {'responder_id': 1, 'instance_id': 'c1'},
                {'responder_id': 3, 'instance_id': 'c2'},
            ],
            '_created_at': time.time() - (app.RESPONSE_WINDOW_SECONDS + 5),
        }
        engine = _FakeEngine(pending)
        room = _FakeRoom(mode='2v2', player_sids=['a', 'b', 'c', 'd'], engine=engine)
        self.assertTrue(app._expire_pending_response_locked(room))
        self.assertEqual([pidx for pidx, _card in engine.passes], [1, 3])
        self.assertIsNone(engine.pending_response)

    def test_client_facing_deadline_is_shorter_than_server_deadline(self):
        # 客户端倒计时最长 5 秒；服务端要留出余量，不能比它短。
        self.assertGreaterEqual(app.RESPONSE_WINDOW_SECONDS, 6)

    def test_room_timer_worker_expires_pending_responses(self):
        self.assertIn("RESPONSE_WINDOW_SECONDS = _env_float('GTN_RESPONSE_WINDOW_SECONDS'", APP_SOURCE)
        self.assertIn('if _expire_pending_response_locked(room, now):', APP_SOURCE)
        self.assertIn("emit_pending_interaction_after_state_change(room, reason='response_expired')", APP_SOURCE)


class ResponderReachabilityTests(unittest.TestCase):
    def test_stale_session_is_not_treated_as_reachable(self):
        room = _FakeRoom(player_sids=['sid-a', 'sid-b'], room_id=7)
        players = {
            'sid-a': {'room_id': 7, 'status': 'playing'},
            'sid-b': {'room_id': 9, 'status': 'playing'},
        }
        with mock.patch.object(app, 'players', players):
            self.assertTrue(app._room_player_index_responder_reachable(room, 0))
            self.assertFalse(app._room_player_index_responder_reachable(room, 1))

    def test_disconnected_responder_is_not_reachable(self):
        room = _FakeRoom(player_sids=['sid-a', 'sid-b'], room_id=7)
        room.disconnected_players = {'sid-b': {'player_index': 1}}
        players = {
            'sid-a': {'room_id': 7, 'status': 'playing'},
            'sid-b': {'room_id': 7, 'status': 'playing'},
        }
        with mock.patch.object(app, 'players', players):
            self.assertTrue(app._room_player_index_responder_reachable(room, 0))
            self.assertFalse(app._room_player_index_responder_reachable(room, 1))


if __name__ == '__main__':
    unittest.main()
