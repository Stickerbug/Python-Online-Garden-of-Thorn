import json
import re
import unittest
from pathlib import Path
from unittest import mock

import app as gtn


ROOT = Path(__file__).resolve().parents[1]
STORY_JS = (ROOT / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')
STORY_CSS = (ROOT / 'static' / 'css' / 'story.css').read_text(encoding='utf-8')


class StoryTitleIdentityTests(unittest.TestCase):
    def setUp(self):
        gtn.app.config.update(TESTING=True)
        self.client = gtn.app.test_client()
        self.user = {
            'id': 8401,
            'username': 'StoryTitleTester',
            'display_name': 'StoryTitleTester',
            'player_id': 'STORY8401',
            'skin': {},
            'keybindings': {},
        }

    def test_story_page_includes_rich_title_and_name_paint(self):
        profile = {
            'equipped_titles': [{
                'id': 'test:rainbow',
                'name': 'RainbowTitle',
                'color': '#123456',
                'style': {
                    'segments': [{
                        'id': 'rainbow',
                        'text': 'RainbowTitle',
                        'paint': {
                            'kind': 'gradient',
                            'colors': ['#FF0000', '#00FF00', '#0000FF'],
                            'angle': 90,
                        },
                    }],
                },
            }],
            'name_style': {
                'title_id': 'test:rainbow',
                'segment_id': 'rainbow',
                'paint': {'kind': 'solid', 'color': '#345678'},
            },
            'name_color': '#345678',
        }
        with (
            mock.patch.object(gtn, '_current_account_user', return_value=self.user),
            mock.patch.object(gtn, 'get_user_role_profile', return_value=profile),
            mock.patch.object(gtn, 'feedback_is_staff', return_value=False),
        ):
            response = self.client.get('/story')

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        match = re.search(r'window\.__STORY_ACCOUNT__ = (.*?);\s*\n', html)
        self.assertIsNotNone(match)
        account = json.loads(match.group(1))
        self.assertEqual(account['equipped_titles'][0]['id'], 'test:rainbow')
        self.assertEqual(
            account['equipped_titles'][0]['style']['segments'][0]['paint']['kind'],
            'gradient',
        )
        self.assertEqual(account['name_style']['paint']['color'], '#345678')
        self.assertIn('id="story-player-name"', html)

    def test_story_client_supports_rich_title_paints_in_combat_and_chat(self):
        self.assertIn('function renderStoryPlayerIdentity()', STORY_JS)
        self.assertIn('function appendStoryStyledTitle(', STORY_JS)
        self.assertIn('identity?.name_style?.paint', STORY_JS)
        self.assertIn("element.classList.add('title-paint-gradient')", STORY_JS)
        self.assertIn("epic: '#861FDE'", STORY_JS)
        self.assertIn("legendary: '#DE1F1F'", STORY_JS)
        self.assertIn("unique: '#555555'", STORY_JS)
        self.assertIn('.title-paint-gradient', STORY_CSS)
        self.assertIn(":root[data-theme='dark'] .title-paint-theme", STORY_CSS)


if __name__ == '__main__':
    unittest.main()
