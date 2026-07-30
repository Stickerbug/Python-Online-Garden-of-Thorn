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

    def test_story_count_excludes_regular_online_players(self):
        story_user = self.user()
        gtn.players['regular-player'] = {
            'nickname': 'RegularPlayer',
            'user_id': 99,
            'account_player_id': 'REGULAR1',
            'status': 'playing',
            'mode': '1v1',
            'beta_mode': False,
            'mods_list': [],
            'ip': '203.0.113.20',
        }
        with (
            mock.patch.object(gtn, '_current_account_user', return_value=story_user),
            mock.patch.object(gtn, 'is_beta_instance', return_value=False),
            mock.patch.object(gtn, 'record_account_ip_event_async'),
        ):
            response = self.client.post(
                '/api/story/presence',
                json={'client_id': 'story-count-client'},
            )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload['online_count'], 2)
        self.assertEqual(payload['story_online_count'], 1)

    def test_same_account_in_story_and_multiplayer_counts_once_in_story(self):
        user = self.user()
        gtn.players['same-account-player'] = {
            'nickname': user['username'],
            'user_id': user['id'],
            'account_player_id': user['player_id'],
            'status': 'playing',
            'mode': '1v1',
            'beta_mode': False,
            'mods_list': [],
            'ip': '203.0.113.21',
        }
        with (
            mock.patch.object(gtn, '_current_account_user', return_value=user),
            mock.patch.object(gtn, 'is_beta_instance', return_value=False),
            mock.patch.object(gtn, 'record_account_ip_event_async'),
        ):
            response = self.client.post(
                '/api/story/presence',
                json={'client_id': 'story-shared-account-client'},
            )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload['online_count'], 1)
        self.assertEqual(payload['story_online_count'], 1)

    def test_plain_presence_heartbeat_does_not_reset_afk_schedule(self):
        user = self.user()
        with mock.patch.object(gtn, 'is_beta_instance', return_value=False):
            gtn._touch_story_presence(user, 'story-client-heartbeat', '203.0.113.10')
        key = (user['id'], 'story-client-heartbeat')
        with gtn._STORY_PRESENCE_LOCK:
            original_activity = gtn._STORY_PRESENCES[key]['afk_last_activity_at']
            original_check = gtn._STORY_PRESENCES[key]['afk_next_check_at']

        with mock.patch.object(gtn, 'is_beta_instance', return_value=False):
            gtn._touch_story_presence(user, 'story-client-heartbeat', '203.0.113.10')

        with gtn._STORY_PRESENCE_LOCK:
            presence = gtn._STORY_PRESENCES[key]
            self.assertEqual(presence['afk_last_activity_at'], original_activity)
            self.assertEqual(presence['afk_next_check_at'], original_check)

    def test_activity_presence_resets_afk_schedule(self):
        user = self.user()
        with mock.patch.object(gtn, 'is_beta_instance', return_value=False):
            gtn._touch_story_presence(user, 'story-client-activity', '203.0.113.11')
        key = (user['id'], 'story-client-activity')
        with gtn._STORY_PRESENCE_LOCK:
            gtn._STORY_PRESENCES[key]['afk_last_activity_at'] = 10.0
            gtn._STORY_PRESENCES[key]['afk_next_check_at'] = 20.0

        with mock.patch.object(gtn, 'is_beta_instance', return_value=False):
            gtn._touch_story_presence(
                user,
                'story-client-activity',
                '203.0.113.11',
                activity=True,
            )

        with gtn._STORY_PRESENCE_LOCK:
            presence = gtn._STORY_PRESENCES[key]
            self.assertGreater(presence['afk_last_activity_at'], 10.0)
            self.assertGreaterEqual(
                presence['afk_next_check_at'] - presence['afk_last_activity_at'],
                max(60, gtn.AFK_AUTO_MIN_SECONDS),
            )

    def test_presence_endpoint_issues_and_accepts_story_afk_check(self):
        user = self.user()
        client_id = 'story-client-afk-route'
        with mock.patch.object(gtn, 'is_beta_instance', return_value=False):
            gtn._touch_story_presence(user, client_id, '203.0.113.12')
        key = (user['id'], client_id)
        with gtn._STORY_PRESENCE_LOCK:
            gtn._STORY_PRESENCES[key]['afk_next_check_at'] = time.time() - 1

        with (
            mock.patch.object(gtn, '_current_account_user', return_value=user),
            mock.patch.object(gtn, 'is_beta_instance', return_value=False),
        ):
            check_response = self.client.post(
                '/api/story/presence',
                json={'client_id': client_id},
            )
            check_payload = check_response.get_json()
            request_id = check_payload['afk_check']['id']
            too_short_response = self.client.post(
                '/api/story/afk-check',
                json={'client_id': client_id, 'id': request_id, 'hold_ms': 1},
            )
            passed_response = self.client.post(
                '/api/story/afk-check',
                json={
                    'client_id': client_id,
                    'id': request_id,
                    'hold_ms': gtn.AFK_CHECK_HOLD_MIN_MS + 1,
                },
            )

        self.assertEqual(check_response.status_code, 200)
        self.assertIsInstance(check_payload['afk_check'], dict)
        self.assertEqual(too_short_response.status_code, 200)
        self.assertTrue(too_short_response.get_json()['success'])
        self.assertEqual(too_short_response.get_json()['result'], 'too_short')
        self.assertTrue(too_short_response.get_json()['retry'])
        self.assertEqual(passed_response.status_code, 200)
        self.assertEqual(passed_response.get_json()['result'], 'passed')
        with gtn._STORY_PRESENCE_LOCK:
            self.assertIsNone(gtn._STORY_PRESENCES[key]['afk_check'])
            self.assertGreater(gtn._STORY_PRESENCES[key]['afk_next_check_at'], time.time())

    def test_expired_story_afk_check_removes_presence_without_touching_run(self):
        user = self.user()
        client_id = 'story-client-afk-timeout'
        with mock.patch.object(gtn, 'is_beta_instance', return_value=False):
            gtn._touch_story_presence(user, client_id, '203.0.113.13')
        key = (user['id'], client_id)
        with gtn._STORY_PRESENCE_LOCK:
            gtn._STORY_PRESENCES[key]['afk_check'] = {
                'id': 'expired-story-check',
                'created_at': time.time() - 70,
                'expires_at': time.time() - 1,
                'timeout_seconds': 60,
                'min_ms': gtn.AFK_CHECK_HOLD_MIN_MS,
                'max_ms': gtn.AFK_CHECK_HOLD_MAX_MS,
            }

        with (
            mock.patch.object(gtn, '_current_account_user', return_value=user),
            mock.patch.object(gtn, 'is_beta_instance', return_value=False),
        ):
            response = self.client.post(
                '/api/story/presence',
                json={'client_id': client_id},
            )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['afk_timed_out'])
        self.assertEqual(payload['story_online_count'], 0)
        self.assertEqual(gtn._active_story_presences(beta_mode=False), [])


if __name__ == '__main__':
    unittest.main()
