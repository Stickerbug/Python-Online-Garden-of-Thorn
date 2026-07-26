import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_PY = (ROOT / 'app.py').read_text(encoding='utf-8')
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')


def source_between(source, start, end):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


class ChangelogStateTests(unittest.TestCase):
    def test_version_depends_on_content_not_deployment_timestamp(self):
        section = source_between(
            APP_PY,
            'def changelog_version():',
            'def is_instance_draining():',
        )
        self.assertIn("open(CHANGELOG_PATH, 'rb')", section)
        self.assertIn('hashlib.sha256(', section)
        self.assertNotIn('st_mtime', section)

    def test_opening_waits_for_an_inflight_refresh_before_marking_read(self):
        section = source_between(
            GAME_JS,
            'async function loadChangelog(',
            'function initChangelogBadge(',
        )
        loading_check = section.index('if (changelogLoadingPromise)')
        cached_check = section.index('if (changelogLoaded && !force)')
        self.assertLess(loading_check, cached_check)
        toggle = source_between(
            GAME_JS,
            'function toggleChangelogPopover(',
            'function closeAbout(',
        )
        self.assertIn('Promise.resolve(loadChangelog()).then(markChangelogRead)', toggle)


if __name__ == '__main__':
    unittest.main()
