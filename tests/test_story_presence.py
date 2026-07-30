import time
import unittest
from unittest import mock

import app as gtn


class StoryPresenceTests(unittest.TestCase):
    def setUp(self):
        gtn.app.config.update(TESTING=True)
        self.client = gtn.app.test_client()
        self.original_players = dict(gtn.players)
        with gtn._STORY_PRESENCE_LOCK:
            self.original_presences = dict(gtn._STORY_PRESENCES)
            gtn._STORY_PRESENCES.clear()
        gtn.players.clear()

    def tearDown(self):
        gtn.players.clear()
        gtn.players.update(self.original_players)
        with gtn._STORY_PRESENCE_LOCK:
            gtn._STORY_PRESENCES.clear()
            gtn._STORY_PRESENCES.update(self.original_presences)

    @staticmethod
    def user(user_id=41, username='StoryTester', player_id='STORY01'):
        return {
            'id': user_id,
            'username': username,
            'display_name': username,
            'player_id': player_id,
        }

    def test_story_tabs_are_deduplicated_by_account(self):
        user = self.user()
        with mock.patch.object(gtn, 'is_beta_instance', return_value=False):
            self.assertTrue(gtn._touch_story_presence(user, 'story-client-one', '203.0.113.7'))
            self.assertTrue(gtn._touch_story_presence(user, 'story-client-two', '203.0.113.7'))
            active = gtn._active_story_presences(beta_mode=False)

        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]['user_id'], user['id'])

    def test_story_presence_merges_with_socket_player(self):
        user = self.user()
        gtn.players['socket-one'] = {
            'nickname': user['username'],
            'user_id': user['id'],
            'account_player_id': user['player_id'],
            'status': 'lobby',
            'mode': '1v1',
            'beta_mode': False,
            'mods_list': [],
            'ip': '203.0.113.7',
        }
        with mock.patch.object(gtn, 'is_beta_instance', return_value=False):
            gtn._touch_story_presence(user, 'story-client-one', '203.0.113.7')
            rows = gtn.build_admin_players(beta_mode=False)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['status'], 'lobby')
        self.assertTrue(rows[0]['story_online'])
        self.assertTrue(rows[0]['kickable'])

    def test_story_only_player_is_visible_but_not_kickable(self):
        user = self.user()
        with mock.patch.object(gtn, 'is_beta_instance', return_value=False):
            gtn._touch_story_presence(user, 'story-client-one', '203.0.113.7')
            rows = gtn.build_admin_players(beta_mode=False)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['status'], 'story')
        self.assertEqual(rows[0]['mode'], 'story')
        self.assertFalse(rows[0]['kickable'])
        self.assertEqual(rows[0]['player_id'], user['player_id'])

    def test_stale_story_presence_is_pruned(self):
        with gtn._STORY_PRESENCE_LOCK:
            gtn._STORY_PRESENCES[(41, 'story-client-old')] = {
                'user_id': 41,
                'nickname': 'OldStoryPlayer',
                'account_player_id': 'OLD0001',
                'client_id': 'story-client-old',
                'ip': '203.0.113.8',
                'last_seen': time.time() - gtn.STORY_PRESENCE_TIMEOUT_SECONDS - 1,
                'beta_mode': False,
            }
        self.assertEqual(gtn._active_story_presences(beta_mode=False), [])

    def test_presence_endpoint_records_story_entry_ip(self):
        user = self.user()
        with (
            mock.patch.object(gtn, '_current_account_user', return_value=user),
            mock.patch.object(gtn, 'is_beta_instance', return_value=False),
            mock.patch.object(gtn, 'record_account_ip_event_async') as record_ip,
        ):
            response = self.client.post(
                '/api/story/presence',
                json={'client_id': 'story-client-route'},
                headers={'X-Forwarded-For': '203.0.113.9, 10.0.0.1'},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['online_count'], 1)
        self.assertEqual(payload['story_online_count'], 1)
        record_ip.assert_called_once_with(
            user['id'],
            user['username'],
            '203.0.113.9',
            source='story_enter',
        )


if __name__ == '__main__':
    unittest.main()
