import unittest
from unittest import mock

import app as gtn


class StoryDeveloperPermissionTests(unittest.TestCase):
    def setUp(self):
        gtn.app.config.update(TESTING=True)
        self.client = gtn.app.test_client()
        self.user = {
            "id": 41,
            "username": "StoryTester",
            "display_name": "StoryTester",
            "skin": {},
            "keybindings": {},
        }

    def test_regular_account_does_not_receive_developer_controls(self):
        with (
            mock.patch.object(gtn, "_current_account_user", return_value=self.user),
            mock.patch.object(gtn, "feedback_is_staff", return_value=False),
            mock.patch.object(gtn, "STORY_DEV_TOOLS_ENABLED", True),
        ):
            response = self.client.get("/story")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertNotIn('id="story-dev-toggle"', html)
        self.assertNotIn('id="story-dev-panel"', html)
        self.assertNotIn('id="story-reset-map"', html)

    def test_staff_account_receives_developer_controls(self):
        with (
            mock.patch.object(gtn, "_current_account_user", return_value=self.user),
            mock.patch.object(gtn, "feedback_is_staff", return_value=True),
            mock.patch.object(gtn, "STORY_DEV_TOOLS_ENABLED", True),
        ):
            response = self.client.get("/story")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('id="story-dev-toggle"', html)
        self.assertIn('id="story-dev-panel"', html)
        self.assertIn('id="story-reset-map"', html)

    def test_regular_account_cannot_call_developer_action_api(self):
        payload = {
            "run_id": "test-run",
            "action_id": "test-action",
            "action_type": "dev_set_values",
            "state_version": 1,
            "payload": {"health": 99},
        }
        with (
            mock.patch.object(gtn, "_require_account_json", return_value=(41, "StoryTester", None)),
            mock.patch.object(gtn, "feedback_is_staff", return_value=False),
            mock.patch.object(gtn, "STORY_DEV_TOOLS_ENABLED", True),
        ):
            response = self.client.post("/api/story/run/action", json=payload)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["code"], "DEV_TOOLS_DISABLED")

    def test_regular_account_cannot_reset_story_map(self):
        with (
            mock.patch.object(gtn, "_require_account_json", return_value=(41, "StoryTester", None)),
            mock.patch.object(gtn, "feedback_is_staff", return_value=False),
            mock.patch.object(gtn, "STORY_DEV_TOOLS_ENABLED", True),
        ):
            response = self.client.post("/api/story/run/reset-map", json={"run_id": "test-run"})
        self.assertEqual(response.status_code, 404)

    def test_staff_reset_abandons_the_run_and_returns_to_character_selection(self):
        with (
            mock.patch.object(gtn, "_require_account_json", return_value=(41, "StoryTester", None)),
            mock.patch.object(gtn, "feedback_is_staff", return_value=True),
            mock.patch.object(gtn, "STORY_DEV_TOOLS_ENABLED", True),
            mock.patch.object(gtn, "abandon_story_run", return_value=True) as abandon,
            mock.patch.object(gtn, "_list_story_discoveries_without_blocking", return_value=[]),
        ):
            response = self.client.post(
                "/api/story/run/reset-map",
                json={"run_id": "test-run"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.get_json()["run"])
        abandon.assert_called_once_with(41, "test-run")


if __name__ == "__main__":
    unittest.main()
