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

    def test_read_markers_use_persistent_fallbacks(self):
        storage_section = source_between(
            GAME_JS,
            'const GTN_COOKIE_FALLBACK_KEYS',
            'const GTN_COOKIE_FALLBACK_PREFIXES',
        )
        for key in (
            'gtn_changelog_read_version_v1',
            'gtn_changelog_read_latest_date_v1',
            'gtn_changelog_boot_version_v1',
        ):
            self.assertIn(key, storage_section)

        cookie_reader = source_between(
            GAME_JS,
            'function readStorageFallbackCookie(',
            'function writeStorageFallbackCookie(',
        )
        self.assertIn(".split(';')", cookie_reader)
        self.assertIn('.map(item => item.trim())', cookie_reader)

        marker_section = source_between(
            GAME_JS,
            'function readChangelogMarker(',
            'function currentChangelogCacheVersion(',
        )
        cookie_read = marker_section.index('readStorageFallbackCookie(storageKey)')
        local_read = marker_section.index('localStorage.getItem(storageKey)')
        self.assertLess(cookie_read, local_read)
        self.assertIn('window.sessionStorage.getItem(storageKey)', marker_section)
        self.assertIn('window.sessionStorage.setItem(storageKey, text)', marker_section)
        self.assertIn('writeStorageFallbackCookie(', marker_section)
        self.assertIn('function readChangelogReadReceipt()', marker_section)
        self.assertIn('.sort((left, right)', marker_section)

    def test_mark_read_is_also_saved_in_cached_changelog(self):
        section = source_between(
            GAME_JS,
            'function markChangelogRead(',
            'function loadCachedChangelog(',
        )
        self.assertIn('changelogCache = { ...changelogCache, readVersion, readDate }', section)
        self.assertIn('writeChangelogReadReceipt(readVersion, readDate)', section)
        self.assertIn('localStorage.setItem(CHANGELOG_CACHE_KEY', section)

    def test_stale_response_cannot_poison_current_changelog_cache(self):
        helper = source_between(
            GAME_JS,
            'function isCurrentChangelogCache(',
            'async function loadChangelog(',
        )
        self.assertIn("serverVersion === expectedVersion", helper)
        self.assertIn("cache: 'no-store'", helper)
        self.assertIn('serverVersion !== expectedVersion', helper)
        self.assertIn('fetchCurrentChangelog(expectedVersion, true)', helper)

        loader = source_between(
            GAME_JS,
            'async function loadChangelog(',
            'function initChangelogBadge(',
        )
        mismatch_check = helper.index('serverVersion !== expectedVersion')
        cache_write = loader.index('localStorage.setItem(CHANGELOG_CACHE_KEY')
        self.assertGreaterEqual(mismatch_check, 0)
        self.assertGreaterEqual(cache_write, 0)
        self.assertIn('writeChangelogMarker(CHANGELOG_BOOT_VERSION_KEY, cacheVersion)', loader)

    def test_boot_marker_is_not_written_before_refresh_succeeds(self):
        section = source_between(
            GAME_JS,
            'function initChangelogBadge(',
            'function openAbout(',
        )
        self.assertIn('isCurrentChangelogCache(cached, cacheVersion)', section)
        marker_write = section.index('writeChangelogMarker(CHANGELOG_BOOT_VERSION_KEY, cacheVersion)')
        refresh = section.index('loadChangelog(true, { silent: true })')
        self.assertLess(marker_write, refresh)

    def test_changelog_api_disables_http_caching(self):
        section = source_between(
            APP_PY,
            "@app.route('/api/changelog')",
            "@app.route('/api/report'",
        )
        self.assertIn("response.headers['Cache-Control'] = 'private, no-store, max-age=0'", section)
        self.assertIn("response.headers['X-GTN-Changelog-Version'] = version", section)


if __name__ == '__main__':
    unittest.main()
