import unittest
from unittest import mock

import app as gtn


class StoryCooperativeAccessTests(unittest.TestCase):
    def setUp(self):
        gtn.app.config.update(TESTING=True)
        self.client = gtn.app.test_client()
        self.user = {
            'id': 41,
            'username': 'StoryTester',
            'display_name': 'StoryTester',
            'skin': {},
            'keybindings': {},
        }

    def _get_story_page(self, *, staff, coop_enabled=True, dev_tools=False):
        with (
            mock.patch.object(gtn, '_current_account_user', return_value=self.user),
            mock.patch.object(gtn, 'feedback_is_staff', return_value=staff),
            mock.patch.object(gtn, 'get_user_role_profile', return_value={}),
            mock.patch.object(gtn, 'STORY_COOP_ENABLED', coop_enabled),
            mock.patch.object(gtn, 'STORY_DEV_TOOLS_ENABLED', dev_tools),
        ):
            return self.client.get('/story')

    def test_regular_account_does_not_receive_cooperative_entry(self):
        response = self._get_story_page(staff=False)

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertNotIn('id="story-coop-entry"', html)
        self.assertNotIn('id="story-coop-preview-dialog"', html)
        self.assertNotIn('id="story-coop-combat-dialog"', html)
        self.assertNotIn('id="story-coop-setup-panel"', html)
        self.assertNotIn('id="story-coop-opening-panel"', html)
        self.assertNotIn('id="story-coop-reward-panel"', html)
        self.assertNotIn('id="story-coop-map-panel"', html)
        self.assertIn('window.__STORY_COOP_ACCESS__ = false;', html)
        self.assertIn('id="story-start"', html)

    def test_staff_account_receives_cooperative_entry_without_dev_tools(self):
        response = self._get_story_page(staff=True, dev_tools=False)

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('id="story-coop-entry"', html)
        self.assertIn('id="story-coop-preview-dialog"', html)
        self.assertIn('id="story-coop-combat-dialog"', html)
        self.assertIn('id="story-coop-setup-panel"', html)
        self.assertIn('id="story-coop-opening-panel"', html)
        self.assertIn('id="story-coop-reward-panel"', html)
        self.assertIn('id="story-coop-map-panel"', html)
        self.assertIn('window.__STORY_COOP_ACCESS__ = true;', html)
        self.assertNotIn('id="story-dev-toggle"', html)

    def test_disabled_feature_hides_entry_from_staff(self):
        response = self._get_story_page(staff=True, coop_enabled=False)

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertNotIn('id="story-coop-entry"', html)
        self.assertIn('window.__STORY_COOP_ACCESS__ = false;', html)

    def test_permission_lookup_failure_is_fail_closed(self):
        with (
            mock.patch.object(gtn, 'feedback_is_staff', side_effect=RuntimeError('role lookup failed')),
            mock.patch.object(gtn, 'STORY_COOP_ENABLED', True),
        ):
            self.assertFalse(gtn._story_coop_allowed(41))

    def test_regular_account_cannot_read_cooperative_bootstrap(self):
        with (
            mock.patch.object(
                gtn,
                '_require_account_json',
                return_value=(41, 'StoryTester', None),
            ),
            mock.patch.object(gtn, 'feedback_is_staff', return_value=False),
            mock.patch.object(gtn, 'STORY_COOP_ENABLED', True),
        ):
            response = self.client.get('/api/story/coop/bootstrap')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()['code'], 'COOP_STORY_DISABLED')

    def test_staff_account_can_read_cooperative_bootstrap(self):
        with (
            mock.patch.object(
                gtn,
                '_require_account_json',
                return_value=(41, 'StoryTester', None),
            ),
            mock.patch.object(gtn, 'feedback_is_staff', return_value=True),
            mock.patch.object(gtn, 'STORY_COOP_ENABLED', True),
        ):
            response = self.client.get('/api/story/coop/bootstrap')

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['schema_version'], 10)
        self.assertEqual(payload['mvp_player_count'], 2)
        self.assertEqual(payload['max_players'], 4)
        self.assertEqual(payload['access'], ['staff', 'admin'])
        self.assertEqual(payload['status'], 'staff_full_journey_experiment')
        self.assertTrue(payload['combat_core_ready'])
        self.assertTrue(payload['combat_api_ready'])
        self.assertTrue(payload['reward_api_ready'])
        self.assertTrue(payload['route_vote_api_ready'])
        self.assertTrue(payload['room_api_ready'])
        self.assertTrue(payload['stage1_map_ready'])
        self.assertTrue(payload['full_journey_ready'])
        self.assertTrue(payload['member_progress_commit_ready'])
        self.assertTrue(payload['public_snapshot_ready'])
        self.assertTrue(payload['party_api_ready'])
        self.assertTrue(payload['run_persistence_ready'])


if __name__ == '__main__':
    unittest.main()
