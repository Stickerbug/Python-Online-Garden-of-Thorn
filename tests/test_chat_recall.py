"""聊天撤回：软删除 + 原位占位 + 2 分钟撤回窗口（管理员不限时）。"""

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
SHARED_CHAT_JS = (ROOT / 'static' / 'js' / 'shared-chat-actions.js').read_text(encoding='utf-8')


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
        placeholders = [entry for entry in entries if int(entry['id']) == self.message_id]
        self.assertEqual(len(placeholders), 1)
        self.assertEqual(int(placeholders[0]['recalled']), 1)
        self.assertEqual(placeholders[0]['text'], '')
        self.assertEqual(placeholders[0]['nickname'], 'TestUser')
        self.assertIsNone(db.recall_chat_message(999999))

    def test_batch_recall_by_sender(self):
        for _ in range(3):
            db.record_chat_message('lobby:release', 'public', None, 'Spammer', 'spam', '{}', 0)
        ids = db.recall_chat_messages_from_sender('Spammer', limit=10)
        self.assertEqual(len(ids), 3)
        for message_id in ids:
            self.assertIsNotNone(db.recall_chat_message(message_id, actor_name='Eric'))
        self.assertEqual(db.recall_chat_messages_from_sender('Spammer', limit=10), [])
        # 已撤回的消息不再出现在可撤回名单里，但历史里保留占位。
        entries = db.list_lobby_chat_entries(beta_mode=False, limit=50)
        self.assertTrue(all(entry['text'] == '' for entry in entries if entry.get('recalled')))

    def test_broadcast_chat_recall_reports_count(self):
        import app

        total = app.broadcast_chat_recall('Eric', [{
            'room_id': 'lobby:release',
            'sender_name': 'TestUser',
            'message_ids': [self.message_id],
        }])
        self.assertEqual(total, 1)

    def test_lobby_cache_marks_recalled_in_place(self):
        """撤回要把大厅内存缓存里的条目原位标记（占位跨刷新保留，而不是删掉）。"""
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
            marked = [item for item in remaining if int(item.get('message_id') or 0) == self.message_id]
            self.assertEqual(len(marked), 1)
            self.assertEqual(int(marked[0]['recalled']), 1)
            self.assertEqual(marked[0]['text'], '')
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
                mock.patch.object(gtn, 'user_role_type', return_value='admin'),
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
            self.assertEqual(recalled['actor_name'], 'LobbyAdmin')
            self.assertEqual(recalled['actor_role'], 'admin')
            self.assertEqual(recalled['target_role'], 'admin')
            self.assertTrue(recalled['self_recall'])
            self.assertIn('ts', recalled)
            entries = db.list_lobby_chat_entries(beta_mode=False, limit=20)
            placeholders = [entry for entry in entries if int(entry['id']) == message_id]
            self.assertEqual(len(placeholders), 1)
            self.assertEqual(int(placeholders[0]['recalled']), 1)
            self.assertEqual(placeholders[0]['text'], '')
            with gtn._lock:
                cached = gtn._lobby_chat_recent_locked(beta_mode=False)
            marked = [item for item in cached if int(item.get('message_id') or 0) == message_id]
            self.assertEqual(len(marked), 1)
            self.assertEqual(int(marked[0]['recalled']), 1)
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
            mock.patch.object(gtn, 'user_role_type', return_value='admin'),
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
        placeholders = [entry for entry in entries if int(entry['id']) == self.message_id]
        self.assertEqual(len(placeholders), 1)
        self.assertEqual(int(placeholders[0]['recalled']), 1)
        self.assertEqual(placeholders[0]['text'], '')

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


class ChatRecallPermissionTests(unittest.TestCase):
    def _fresh(self, info=None, age_seconds=10):
        import time as time_module

        payload = dict(info or {})
        payload.setdefault('created_ts', time_module.time() - age_seconds)
        return payload

    def test_recall_permissions_follow_actor_and_target_roles(self):
        """Staff 只能撤回玩家和自己的消息；Admin 谁都行；玩家只能撤回自己的。

        非管理员的消息必须在 2 分钟撤回窗口内（夹具统一给 created_ts）。
        """
        import app as gtn

        roles = {1: 'admin', 2: 'staff', 3: 'staff', 4: 'player', 5: 'player'}
        with mock.patch.object(gtn, 'user_role_type', side_effect=lambda uid: roles.get(int(uid), 'none')):
            admin = {'user_id': 1, 'name': 'Admin1', 'role': 'admin'}
            staff = {'user_id': 2, 'name': 'Staff1', 'role': 'staff'}
            player = {'user_id': 4, 'name': 'Player1', 'role': 'player'}
            player_message = self._fresh({'sender_user_id': 5, 'sender_name': 'Player2'})
            own_message = self._fresh({'sender_user_id': 4, 'sender_name': 'Player1'})
            other_staff_message = self._fresh({'sender_user_id': 3, 'sender_name': 'Staff2'})
            admin_message = self._fresh({'sender_user_id': 1, 'sender_name': 'Admin1'})

            self.assertTrue(gtn._chat_recall_message_allowed(admin, other_staff_message))
            self.assertTrue(gtn._chat_recall_message_allowed(admin, player_message))
            self.assertTrue(gtn._chat_recall_message_allowed(staff, player_message))
            self.assertTrue(gtn._chat_recall_message_allowed(staff, own_message))
            self.assertFalse(gtn._chat_recall_message_allowed(staff, other_staff_message))
            self.assertFalse(gtn._chat_recall_message_allowed(staff, admin_message))
            self.assertTrue(gtn._chat_recall_message_allowed(player, own_message))
            self.assertFalse(gtn._chat_recall_message_allowed(player, player_message))
            self.assertFalse(gtn._chat_recall_message_allowed(player, admin_message))

    def test_recall_window_blocks_late_recall_except_admin(self):
        """超过 2 分钟：玩家/_staff 都不能再撤回（包括自己的），管理员不受限制。"""
        import app as gtn

        roles = {1: 'admin', 2: 'staff', 4: 'player'}
        with mock.patch.object(gtn, 'user_role_type', side_effect=lambda uid: roles.get(int(uid), 'none')):
            admin = {'user_id': 1, 'name': 'Admin1', 'role': 'admin'}
            staff = {'user_id': 2, 'name': 'Staff1', 'role': 'staff'}
            player = {'user_id': 4, 'name': 'Player1', 'role': 'player'}
            old_own = self._fresh({'sender_user_id': 4, 'sender_name': 'Player1'}, age_seconds=300)
            old_other = self._fresh({'sender_user_id': 4, 'sender_name': 'Player1'}, age_seconds=300)

            self.assertFalse(gtn._chat_recall_message_allowed(player, old_own))
            self.assertFalse(gtn._chat_recall_message_allowed(staff, old_other))
            self.assertTrue(gtn._chat_recall_message_allowed(admin, old_own))
            self.assertTrue(gtn._chat_recall_message_allowed(admin, old_other))

    def test_recall_window_boundary_is_inclusive(self):
        """窗口边界：2 分钟内仍可撤回；缺少时间信息的按不可撤回处理。"""
        import app as gtn

        with mock.patch.object(gtn, 'user_role_type', return_value='player'):
            player = {'user_id': 4, 'name': 'Player1', 'role': 'player'}
            edge = self._fresh({'sender_user_id': 4, 'sender_name': 'Player1'},
                               age_seconds=gtn.CHAT_RECALL_WINDOW_SECONDS - 1)
            no_time = {'sender_user_id': 4, 'sender_name': 'Player1'}
            self.assertTrue(gtn._chat_recall_message_allowed(player, edge))
            self.assertFalse(gtn._chat_recall_message_allowed(player, no_time))

    def test_recall_window_enforced_end_to_end_for_player(self):
        """数据库端到端：把消息时间改到 3 分钟前，玩家身份撤回被拒，管理员成功。"""
        from datetime import timedelta

        import app as gtn

        old_id = db.record_chat_message(
            'lobby:release', 'public', 4, 'OldPlayer', 'late message', '{}', 0,
        )
        with db.get_db_connection() as conn:
            row = conn.execute(
                'SELECT created_at FROM chat_messages WHERE id = ?', (old_id,),
            ).fetchone()
            created = db.datetime.fromisoformat(str(row['created_at']).replace('Z', '+00:00'))
            conn.execute(
                'UPDATE chat_messages SET created_at = ? WHERE id = ?',
                ((created - timedelta(seconds=180)).isoformat().replace('+00:00', 'Z'), old_id),
            )
            conn.commit()
        result = gtn.recall_chat_messages_for_actor(
            {'user_id': 4, 'name': 'OldPlayer', 'role': 'player'}, [old_id],
        )
        self.assertEqual(result, {'recalled': 0, 'denied': 1})
        result = gtn.recall_chat_messages_for_actor(
            {'user_id': 1, 'name': 'Admin1', 'role': 'admin'}, [old_id],
        )
        self.assertEqual(result['recalled'], 1)

    def test_room_chat_history_marks_recalled_in_place(self):
        """房间内存历史：撤回后条目原位变占位（不删除），折叠部分命中保留剩余。"""
        import collections

        import app as gtn

        room = type('RoomStub', (), {})()
        room.chat_history = collections.deque(maxlen=50)
        room.chat_history.append({
            'type': 'chat',
            'id': 1,
            'nickname': 'Player1',
            'text': 'hello',
            'message_id': 101,
            'message_ids': [101],
            'ts': 100.0,
        })
        room.chat_history.append({
            'type': 'chat',
            'id': 2,
            'nickname': 'Player1',
            'text': 'spam',
            'message_id': 103,
            'message_ids': [102, 103],
            'repeat_count': 2,
            'ts': 101.0,
        })
        gtn._mark_room_chat_history_recalled(room, [101, 102], 'Admin1')
        first, second = list(room.chat_history)
        self.assertEqual(int(first['recalled']), 1)
        self.assertEqual(first['text'], '')
        self.assertEqual(first['recalled_by'], 'Admin1')
        # 折叠两条只撤回一条：剩下一条照常显示，不再带被撤回的 id。
        self.assertNotIn('recalled', second)
        self.assertEqual(second['message_ids'], ['103'])
        self.assertEqual(second['repeat_count'], 1)

    def test_chat_role_labels_default_to_player_for_plain_accounts(self):
        import app as gtn

        with mock.patch.object(gtn, 'user_role_type', side_effect=lambda uid: {7: 'staff'}.get(int(uid), 'none')):
            self.assertEqual(gtn._chat_role_for_account(7), 'staff')
            self.assertEqual(gtn._chat_role_for_account(8), 'player')
            self.assertEqual(gtn._chat_role_for_account(None, {'is_admin_player': True}), 'admin')


class ChatRecallUiTests(unittest.TestCase):
    """统一撤回机制：shared-chat-actions 是唯一实现，各聊天窗口只做接入。"""

    def test_shared_module_is_the_single_recall_implementation(self):
        self.assertIn('window.GtnChatRecall = {', SHARED_CHAT_JS)
        self.assertIn('CHAT_RECALL_WINDOW_MS = 120 * 1000', SHARED_CHAT_JS)
        self.assertIn('function chatRecallAllowed(entry = {}, viewer = {}, nowMs = Date.now())', SHARED_CHAT_JS)
        self.assertIn('function chatRecallDeadlineMs(entry = {}, viewer = {})', SHARED_CHAT_JS)
        self.assertIn('data-recall-deadline', SHARED_CHAT_JS)
        self.assertIn('function applyRecallToEntryList(entries, notice = {})', SHARED_CHAT_JS)
        self.assertIn('function chatRecallPlaceholderText(entry = {}, custom = {})', SHARED_CHAT_JS)
        self.assertIn('function startChatRecallExpiryWatcher()', SHARED_CHAT_JS)
        # 非管理员的按钮要带过期时刻，过期后由 watcher 移除；管理员不限时。
        self.assertIn("String((viewer && viewer.role) || '').toLowerCase() === 'admin'", SHARED_CHAT_JS)
        self.assertIn('.chat-recall-btn', SHARED_CHAT_CSS)
        self.assertIn('.chat-recall-entry', SHARED_CHAT_CSS)

    def test_index_loads_shared_module_before_game_js(self):
        index_html = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
        shared_pos = index_html.find('shared-chat-actions.js')
        game_pos = index_html.find('game.js')
        self.assertGreater(shared_pos, 0)
        self.assertGreater(game_pos, 0)
        self.assertLess(shared_pos, game_pos)

    def test_lobby_and_battle_chat_use_shared_recall(self):
        self.assertIn('function createRecallChatButton(entry = {})', GAME_JS)
        self.assertIn('actions.createChatRecallButton(entry, chatRecallViewer(), {', GAME_JS)
        self.assertGreaterEqual(GAME_JS.count('const recallBtn = createRecallChatButton(entry);'), 2)
        self.assertIn('function applyChatRecall(data = {})', GAME_JS)
        self.assertIn('applyRecallToEntryList', GAME_JS)
        self.assertIn('function chatRecallPlaceholderText(entry = {})', GAME_JS)
        self.assertIn("bindSocketEvent('chat_recall'", GAME_JS)
        self.assertIn("bindSocketEvent('admin_chat_recall_result'", GAME_JS)
        self.assertIn('function dropDanglingChatTimeSeparators(', GAME_JS)
        # 大厅与对局渲染都识别 recalled 占位（原位显示，不再过滤删除）。
        self.assertIn('if (entry.recalled) {', GAME_JS)
        self.assertIn('entry && entry.recalled,', GAME_JS)

    def test_story_chat_uses_shared_recall(self):
        self.assertIn("storyChatSocket.on('chat_recall'", STORY_JS)
        self.assertIn("storyChatSocket.on('admin_chat_recall_result'", STORY_JS)
        self.assertIn('function createStoryChatRecallButton(entry = {})', STORY_JS)
        self.assertIn('actions.createChatRecallButton(entry, {', STORY_JS)
        self.assertIn('function applyStoryChatRecall(data = {})', STORY_JS)
        self.assertIn('applyRecallToEntryList(storyChatEntries, {', STORY_JS)
        self.assertIn("recallRow.className = 'story-chat-message chat-msg chat-recall-entry';", STORY_JS)
        self.assertIn('function dropDanglingStoryChatTimeSeparators(', STORY_JS)

    def test_minigame_chat_marks_rows_in_place(self):
        minigame_js = (ROOT / 'static' / 'js' / 'minigame-chat.js').read_text(encoding='utf-8')
        self.assertIn('GtnChatRecall.markEntryRecalled', minigame_js)
        self.assertIn('recallApi.placeholderText', minigame_js)
        self.assertIn('row.classList.add(\'chat-recall-entry\')', minigame_js)
        self.assertIn('if (item.recalled) {', minigame_js)


if __name__ == '__main__':
    unittest.main()
