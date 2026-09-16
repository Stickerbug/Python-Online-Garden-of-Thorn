"""管理员撤回聊天：软删除 + 广播占位（反馈：要能撤回所有人的消息）。"""

import gc
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import db


ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
STORY_JS = (ROOT / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')
SHARED_CHAT_CSS = (ROOT / 'static' / 'css' / 'shared-lobby-chat.css').read_text(encoding='utf-8')


class _AutoRegisterPlayers(dict):
    """测试替身：任意 sid 都当作已登录玩家，并在首次访问时登记真实 sid。"""

    def __init__(self, template):
        super().__init__()
        self._template = dict(template)

    def _ensure(self, key):
        if isinstance(key, str) and not dict.__contains__(self, key):
            dict.__setitem__(self, key, dict(self._template))
        return key

    def __contains__(self, key):
        self._ensure(key)
        return dict.__contains__(self, key)

    def __getitem__(self, key):
        self._ensure(key)
        return dict.__getitem__(self, key)

    def get(self, key, default=None):
        self._ensure(key)
        return dict.get(self, key, default)


class ChatRecallTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'recall.sqlite3')
        db.init_db()
        self.message_id = db.record_chat_message(
            'lobby:release', 'public', None, 'TestUser', '傻逼', '{}', 3,
        )

    def tearDown(self):
        db.release_wal_keeper()
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def test_recall_hides_message_and_returns_scope(self):
        entries = db.list_lobby_chat_entries(beta_mode=False, limit=10)
        self.assertTrue(any(int(entry['id']) == self.message_id for entry in entries))

        info = db.recall_chat_message(self.message_id, actor_user_id=2, actor_name='Eric')
        self.assertIsNotNone(info)
        self.assertEqual(info['message_id'], self.message_id)
        self.assertEqual(info['room_id'], 'lobby:release')
        self.assertEqual(info['sender_name'], 'TestUser')

        entries = db.list_lobby_chat_entries(beta_mode=False, limit=10)
        self.assertFalse(any(int(entry['id']) == self.message_id for entry in entries))
        self.assertIsNone(db.recall_chat_message(999999))

    def test_batch_recall_by_sender(self):
        for _ in range(3):
            db.record_chat_message('lobby:release', 'public', None, 'Spammer', 'spam', '{}', 0)
        ids = db.recall_chat_messages_from_sender('Spammer', limit=10)
        self.assertEqual(len(ids), 3)
        for message_id in ids:
            self.assertIsNotNone(db.recall_chat_message(message_id, actor_name='Eric'))
        self.assertEqual(db.recall_chat_messages_from_sender('Spammer', limit=10), [])

    def test_broadcast_chat_recall_reports_count(self):
        import app

        total = app.broadcast_chat_recall('Eric', [{
            'room_id': 'lobby:release',
            'sender_name': 'TestUser',
            'message_ids': [self.message_id],
        }])
        self.assertEqual(total, 1)

    def test_lobby_cache_carries_message_ids_and_prunes_on_recall(self):
        """撤回要从大厅内存缓存里真的删掉，否则刷新/重连又会冒出来。"""
        import copy

        import app

        original_cache = copy.deepcopy(app.LOBBY_CHAT_CACHE)
        original_sequence = copy.deepcopy(app.LOBBY_CHAT_SEQUENCE)
        try:
            with app._lock:
                app.LOBBY_CHAT_CACHE.clear()
                app.LOBBY_CHAT_SEQUENCE.clear()
                local_id = app.append_lobby_chat_locked(
                    {'nickname': 'TestUser', 'text': '傻逼', 'chat_origin': 'multiplayer'},
                    now=100.0,
                    beta_mode=False,
                )
                self.assertIsNotNone(local_id)
                self.assertTrue(app.update_lobby_chat_message_id_locked(False, local_id, self.message_id))
                cached = app._lobby_chat_recent_locked(beta_mode=False)
            self.assertEqual(int(cached[-1]['message_id']), self.message_id)

            with mock.patch.object(app.socketio, 'emit') as emit_mock:
                total = app.broadcast_chat_recall('Eric', [{
                    'room_id': 'lobby:release',
                    'sender_name': 'TestUser',
                    'message_ids': [self.message_id],
                }])
            self.assertEqual(total, 1)
            with app._lock:
                remaining = app._lobby_chat_recent_locked(beta_mode=False)
            self.assertEqual(remaining, [])
            notified_rooms = [call.kwargs.get('room') for call in emit_mock.call_args_list]
            self.assertIn(app._story_lobby_chat_room(False), notified_rooms)
        finally:
            with app._lock:
                app.LOBBY_CHAT_CACHE.clear()
                app.LOBBY_CHAT_CACHE.update(original_cache)
                app.LOBBY_CHAT_SEQUENCE.clear()
                app.LOBBY_CHAT_SEQUENCE.update(original_sequence)

    def test_lobby_chat_message_gets_id_and_can_be_recalled_from_socket(self):
        """大厅消息落库后要把 id 发回客户端，撤回后缓存与历史里都不该再有它。"""
        import contextlib
        import copy

        import app as gtn

        user = {
            'id': 9101,
            'username': 'LobbyAdmin',
            'display_name': 'LobbyAdmin',
            'player_id': 'ADMIN9101',
        }
        original_cache = copy.deepcopy(gtn.LOBBY_CHAT_CACHE)
        original_sequence = copy.deepcopy(gtn.LOBBY_CHAT_SEQUENCE)
        original_players = gtn.players
        try:
            with gtn._lock:
                gtn.LOBBY_CHAT_CACHE.clear()
                gtn.LOBBY_CHAT_SEQUENCE.clear()
            gtn.players = _AutoRegisterPlayers({
                'nickname': 'LobbyAdmin',
                'status': 'lobby',
                'beta_mode': False,
                'user_id': user['id'],
                'is_admin_player': True,
            })
            patches = (
                mock.patch.object(gtn, 'DB_AVAILABLE', True),
                mock.patch.object(gtn, '_current_account_user', return_value=user),
                mock.patch.object(gtn, 'get_special_account_profile', return_value={'is_admin_player': True}),
                mock.patch.object(gtn, 'feedback_is_staff', return_value=False),
                mock.patch.object(gtn, 'is_beta_instance', return_value=False),
                mock.patch.object(gtn, 'rate_limiter', return_value=True),
                mock.patch.object(gtn, 'check_chat_rate_locked', return_value=True),
                mock.patch.object(gtn, '_extract_lobby_mentions', return_value=[]),
                mock.patch.object(gtn, 'append_admin_game_chat_locked'),
                mock.patch.object(gtn, 'record_socket_action'),
                mock.patch.object(gtn, 'ensure_event_loop_watchdog_started'),
                mock.patch.object(gtn, 'ensure_lobby_idle_cleanup_started'),
                mock.patch.object(gtn, 'ensure_pending_interaction_watchdog_started'),
                mock.patch.object(gtn, 'ensure_room_timer_worker_started'),
                mock.patch.object(gtn, 'admin_event'),
            )
            with contextlib.ExitStack() as stack:
                for patch in patches:
                    stack.enter_context(patch)
                gtn.app.config.update(TESTING=True)
                http_client = gtn.app.test_client()
                socket_client = gtn.socketio.test_client(
                    gtn.app,
                    flask_test_client=http_client,
                )
                self.assertTrue(socket_client.is_connected())
                socket_client.emit('chat', {'text': 'hello lobby'})
                sent_events = socket_client.get_received()
                history_events = [
                    event for event in sent_events
                    if event.get('name') == 'lobby_chat_history'
                ]
                self.assertTrue(history_events)
                items = history_events[-1]['args'][0]['items']
                posted = [item for item in items if item.get('text') == 'hello lobby']
                self.assertTrue(posted)
                message_id = int(posted[-1]['message_id'])

                socket_client.emit('admin_chat_recall', {'message_ids': [message_id]})
                recall_events = socket_client.get_received()
                socket_client.disconnect()

            names = [event.get('name') for event in recall_events]
            self.assertIn('chat_recall', names)
            recalled = [
                event['args'][0] for event in recall_events
                if event.get('name') == 'chat_recall'
            ][-1]
            self.assertEqual(recalled['message_ids'], [message_id])
            self.assertEqual(recalled['target_name'], 'LobbyAdmin')
            entries = db.list_lobby_chat_entries(beta_mode=False, limit=20)
            self.assertFalse(any(int(entry['id']) == message_id for entry in entries))
            with gtn._lock:
                cached = gtn._lobby_chat_recent_locked(beta_mode=False)
            self.assertFalse(any(item.get('message_id') == message_id for item in cached))
        finally:
            with gtn._lock:
                gtn.LOBBY_CHAT_CACHE.clear()
                gtn.LOBBY_CHAT_CACHE.update(original_cache)
                gtn.LOBBY_CHAT_SEQUENCE.clear()
                gtn.LOBBY_CHAT_SEQUENCE.update(original_sequence)
            gtn.players = original_players

    def test_story_chat_socket_admin_can_recall(self):
        """故事模式聊天是独立 socket，管理员也要能撤回并把消息真的软删。"""
        import contextlib

        import app as gtn

        user = {
            'id': 9001,
            'username': 'StoryAdmin',
            'display_name': 'StoryAdmin',
            'player_id': 'ADMIN9001',
        }
        patches = (
            mock.patch.object(gtn, '_current_account_user', return_value=user),
            mock.patch.object(gtn, 'get_special_account_profile', return_value={'is_admin_player': True}),
            mock.patch.object(gtn, 'feedback_is_staff', return_value=False),
            mock.patch.object(gtn, 'is_beta_instance', return_value=False),
            mock.patch.object(gtn, 'rate_limiter', return_value=True),
            mock.patch.object(gtn, 'record_socket_action'),
            mock.patch.object(gtn, 'ensure_event_loop_watchdog_started'),
            mock.patch.object(gtn, 'ensure_lobby_idle_cleanup_started'),
            mock.patch.object(gtn, 'ensure_pending_interaction_watchdog_started'),
            mock.patch.object(gtn, 'ensure_room_timer_worker_started'),
            mock.patch.object(gtn, 'admin_event'),
        )
        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            gtn.app.config.update(TESTING=True)
            http_client = gtn.app.test_client()
            socket_client = gtn.socketio.test_client(
                gtn.app,
                flask_test_client=http_client,
            )
            self.assertTrue(socket_client.is_connected())
            socket_client.emit('admin_chat_recall', {'message_ids': [self.message_id]})
            events = socket_client.get_received()
            socket_client.disconnect()

        results = [
            event['args'][0] for event in events
            if event.get('name') == 'admin_chat_recall_result'
        ]
        self.assertTrue(results)
        self.assertTrue(results[-1]['success'])
        self.assertEqual(results[-1]['recalled'], 1)
        entries = db.list_lobby_chat_entries(beta_mode=False, limit=10)
        self.assertFalse(any(int(entry['id']) == self.message_id for entry in entries))

    def test_folded_lobby_messages_keep_every_message_id(self):
        """连续重复消息会折叠成一条，但每条落库 id 都要留档，撤回才找得到。"""
        import copy

        import app

        original_cache = copy.deepcopy(app.LOBBY_CHAT_CACHE)
        original_sequence = copy.deepcopy(app.LOBBY_CHAT_SEQUENCE)
        try:
            with app._lock:
                app.LOBBY_CHAT_CACHE.clear()
                app.LOBBY_CHAT_SEQUENCE.clear()
                first_id = app.append_lobby_chat_locked(
                    {'nickname': 'Spammer', 'text': 'spam', 'chat_origin': 'multiplayer'},
                    now=100.0,
                    beta_mode=False,
                )
                second_id = app.append_lobby_chat_locked(
                    {'nickname': 'Spammer', 'text': 'spam', 'chat_origin': 'multiplayer'},
                    now=101.0,
                    beta_mode=False,
                )
                self.assertEqual(first_id, second_id)
                app.update_lobby_chat_message_id_locked(False, first_id, 501)
                app.update_lobby_chat_message_id_locked(False, second_id, 502)
                cached = app._lobby_chat_recent_locked(beta_mode=False)
            entry = cached[-1]
            self.assertEqual(entry['message_ids'], [501, 502])
            self.assertEqual(entry['repeat_count'], 2)
        finally:
            with app._lock:
                app.LOBBY_CHAT_CACHE.clear()
                app.LOBBY_CHAT_CACHE.update(original_cache)
                app.LOBBY_CHAT_SEQUENCE.clear()
                app.LOBBY_CHAT_SEQUENCE.update(original_sequence)


class ChatRecallUiTests(unittest.TestCase):
    def test_lobby_chat_has_admin_recall_button(self):
        self.assertIn('function canRecallChatMessages()', GAME_JS)
        self.assertIn('function createRecallChatButton(entry = {})', GAME_JS)
        self.assertEqual(GAME_JS.count('createRecallChatButton(entry)'), 1)
        self.assertIn("socket.emit('admin_chat_recall', { message_ids: [messageId] });", GAME_JS)
        self.assertIn("bindSocketEvent('admin_chat_recall_result'", GAME_JS)

    def test_story_chat_has_admin_recall_button_and_notice(self):
        self.assertIn("storyChatSocket.on('chat_recall'", STORY_JS)
        self.assertIn("storyChatSocket.on('admin_chat_recall_result'", STORY_JS)
        self.assertIn("storyChatSocket.emit('admin_chat_recall', { message_ids: [messageId] });", STORY_JS)
        self.assertIn('function createStoryChatRecallButton(entry = {})', STORY_JS)
        self.assertIn('function applyStoryChatRecall(data = {})', STORY_JS)
        self.assertIn("recallRow.className = 'story-chat-message chat-msg chat-recall-entry';", STORY_JS)
        self.assertIn('.chat-recall-btn', SHARED_CHAT_CSS)
        self.assertIn('.chat-recall-entry', SHARED_CHAT_CSS)


if __name__ == '__main__':
    unittest.main()
