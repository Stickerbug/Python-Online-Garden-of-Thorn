import copy
import unittest
from pathlib import Path
from unittest import mock

import app as gtn


ROOT = Path(__file__).resolve().parents[1]
STORY_TEMPLATE = (ROOT / 'templates' / 'story.html').read_text(encoding='utf-8')
STORY_JS = (ROOT / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')
STORY_CSS = (ROOT / 'static' / 'css' / 'story.css').read_text(encoding='utf-8')
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
GAME_CSS = (ROOT / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')


class SharedStoryChatTests(unittest.TestCase):
    def setUp(self):
        gtn.app.config.update(TESTING=True)
        self.http_client = gtn.app.test_client()
        self.original_players = copy.deepcopy(gtn.players)
        self.original_cache = copy.deepcopy(gtn.LOBBY_CHAT_CACHE)
        self.original_sequence = copy.deepcopy(gtn.LOBBY_CHAT_SEQUENCE)
        with gtn._lock:
            gtn.players.clear()
            gtn.LOBBY_CHAT_CACHE.clear()
            gtn.LOBBY_CHAT_SEQUENCE.clear()

    def tearDown(self):
        with gtn._lock:
            gtn.players.clear()
            gtn.players.update(self.original_players)
            gtn.LOBBY_CHAT_CACHE.clear()
            gtn.LOBBY_CHAT_CACHE.update(self.original_cache)
            gtn.LOBBY_CHAT_SEQUENCE.clear()
            gtn.LOBBY_CHAT_SEQUENCE.update(self.original_sequence)

    @staticmethod
    def user():
        return {
            'id': 7301,
            'username': 'StoryChatTester',
            'display_name': 'StoryChatTester',
            'player_id': 'STORY7301',
        }

    def test_legacy_lobby_chat_defaults_to_multiplayer_origin(self):
        with gtn._lock:
            gtn.restore_lobby_chat_item_locked({
                'type': 'chat',
                'nickname': 'LegacyPlayer',
                'text': 'legacy message',
                'ts': 100.0,
            }, beta_mode=False)
            items = gtn._lobby_chat_recent_locked(beta_mode=False)

        self.assertEqual(items[-1]['chat_origin'], 'multiplayer')

    def test_different_chat_origins_do_not_fold_together(self):
        with gtn._lock:
            gtn.append_lobby_chat_locked({
                'nickname': 'SamePlayer',
                'text': 'same message',
                'chat_origin': 'multiplayer',
            }, now=100.0, beta_mode=False)
            gtn.append_lobby_chat_locked({
                'nickname': 'SamePlayer',
                'text': 'same message',
                'chat_origin': 'story',
            }, now=101.0, beta_mode=False)
            messages = [
                item for item in gtn._lobby_chat_recent_locked(beta_mode=False)
                if item.get('type') == 'chat'
            ]

        self.assertEqual(len(messages), 2)
        self.assertEqual(
            [item['chat_origin'] for item in messages],
            ['multiplayer', 'story'],
        )

    def test_lobby_chat_broadcast_always_includes_story_room(self):
        with gtn._lock:
            payloads = gtn.lobby_chat_history_payloads_locked(
                gtn.LOBBY_CHAT_VISIBLE_LIMIT,
                beta_mode=False,
            )

        recipients = [recipient for recipient, _payload in payloads]
        self.assertIn(gtn._story_lobby_chat_room(False), recipients)

    def test_story_socket_joins_and_sends_to_shared_lobby_history(self):
        user = self.user()
        patches = (
            mock.patch.object(gtn, 'DB_AVAILABLE', False),
            mock.patch.object(gtn, '_current_account_user', return_value=user),
            mock.patch.object(gtn, 'get_special_account_profile', return_value=None),
            mock.patch.object(gtn, 'rate_limiter', return_value=True),
            mock.patch.object(gtn, 'check_chat_rate_locked', return_value=True),
            mock.patch.object(gtn, '_extract_lobby_mentions', return_value=[]),
            mock.patch.object(gtn, 'append_admin_game_chat_locked'),
            mock.patch.object(gtn, '_mark_story_afk_activity'),
            mock.patch.object(gtn, 'record_socket_action'),
            mock.patch.object(gtn, 'ensure_event_loop_watchdog_started'),
            mock.patch.object(gtn, 'ensure_lobby_idle_cleanup_started'),
            mock.patch.object(gtn, 'ensure_pending_interaction_watchdog_started'),
            mock.patch.object(gtn, 'ensure_room_timer_worker_started'),
            mock.patch.object(gtn, 'is_beta_instance', return_value=False),
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], \
                patches[6], patches[7], patches[8], patches[9], patches[10], \
                patches[11], patches[12], patches[13]:
            socket_client = gtn.socketio.test_client(
                gtn.app,
                flask_test_client=self.http_client,
            )
            self.assertTrue(socket_client.is_connected())
            socket_client.emit('story_chat_join', {
                'client_id': 'story-chat-test-client',
            })
            joined_events = socket_client.get_received()
            self.assertIn(
                'story_chat_ready',
                [event.get('name') for event in joined_events],
            )

            socket_client.emit('story_chat_send', {
                'client_id': 'story-chat-test-client',
                'text': 'shared from story',
            })
            sent_events = socket_client.get_received()
            socket_client.disconnect()

        history_events = [
            event for event in sent_events
            if event.get('name') == 'lobby_chat_history'
        ]
        self.assertTrue(history_events)
        items = history_events[-1]['args'][0]['items']
        self.assertEqual(items[-1]['text'], 'shared from story')
        self.assertEqual(items[-1]['chat_origin'], 'story')


def test_story_chat_ui_is_large_collapsible_and_uses_shared_socket_history():
    for element_id in (
        'story-chat-toggle',
        'story-chat-unread',
        'story-chat-panel',
        'story-chat-log',
        'story-chat-input',
        'story-chat-send',
    ):
        assert f'id="{element_id}"' in STORY_TEMPLATE
    assert '/static/vendor/socket.io.min.js' in STORY_TEMPLATE
    assert "storyChatSocket.emit('story_chat_join'" in STORY_JS
    assert "storyChatSocket.emit('story_chat_send'" in STORY_JS
    assert "storyChatSocket.on('lobby_chat_history', renderStoryChatHistory);" in STORY_JS
    assert 'function setStoryChatOpen(open)' in STORY_JS
    assert 'width: min(1040px, 84vw);' in STORY_CSS
    assert 'height: min(760px, 82vh);' in STORY_CSS


def test_chat_origin_prefix_has_its_own_color_and_repeat_identity():
    assert 'chat-origin-prefix' in GAME_JS
    assert "entry.chat_origin || entry.chatOrigin || ''" in GAME_JS
    assert '.chat-origin-multiplayer' in GAME_CSS
    assert '.chat-origin-story' in GAME_CSS
    assert '.story-chat-origin-multiplayer' in STORY_CSS
    assert '.story-chat-origin-story' in STORY_CSS
    assert "name.style.color = nameColor;" in STORY_JS


if __name__ == '__main__':
    unittest.main()
