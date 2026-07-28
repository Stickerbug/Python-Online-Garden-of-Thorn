import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
STORY_JS = (ROOT / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')
INDEX_HTML = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
STORY_HTML = (ROOT / 'templates' / 'story.html').read_text(encoding='utf-8')
EXPORTER_JS = (ROOT / 'static' / 'js' / 'card_exporter.js').read_text(encoding='utf-8')


def source_between(source, start, end):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


class SettingsPersistenceTests(unittest.TestCase):
    def test_small_preferences_have_cookie_fallbacks(self):
        section = source_between(
            GAME_JS,
            'const GTN_COOKIE_FALLBACK_KEYS',
            'const gtnConfirmedCookieFallbackKeys',
        )
        for key in (
            'gtn_theme',
            'gtn_lang',
            'gtn_ui_style',
            'gtn_show_english_card_names',
            'gtn_show_card_images',
            'gtn_play_gesture_animation',
            'gtn_landscape_mode',
            'gtn_audio_master',
            'gtn_audio_music',
            'gtn_audio_ui',
            'gtn_audio_sfx',
            'gtn_skin_config',
            'preferred_mode',
        ):
            self.assertIn(f"'{key}'", section)

    def test_large_payloads_are_not_written_to_cookie_fallbacks(self):
        section = source_between(
            GAME_JS,
            'const GTN_COOKIE_FALLBACK_KEYS',
            'const gtnConfirmedCookieFallbackKeys',
        )
        for key in (
            'gtn_solo_decks',
            'gtn_community_mods',
            'gtn_account_user',
            'gtn_changelog_cache_v1',
        ):
            self.assertNotIn(f"'{key}'", section)

    def test_storage_uses_session_and_cookie_after_local_storage_failure(self):
        section = source_between(
            GAME_JS,
            'const gtnStorageMemory',
            'function clampClientCardLayer(',
        )
        self.assertIn('gtnSessionStorage = window.sessionStorage', section)
        self.assertIn('gtnSessionStorage.getItem(mapped)', section)
        self.assertIn('gtnSessionStorage.setItem(mapped, text)', section)
        self.assertIn('writeStorageFallbackCookie(mapped, text)', section)
        self.assertIn('normalizeStorageFallbackKey(value)', section)

    def test_bootstrap_reads_language_theme_from_fallback_storage(self):
        section = source_between(INDEX_HTML, '<script>', '</script>')
        self.assertIn('window.sessionStorage.getItem(key)', section)
        self.assertIn('return readCookie(key)', section)
        self.assertIn("betaKey('gtn_lang')", section)
        self.assertIn("betaKey('gtn_theme')", section)
        self.assertIn("setAttribute('data-theme', theme)", section)

    def test_story_and_exporter_use_the_shared_storage_contract(self):
        self.assertIn('window.GTN_STORAGE || window.localStorage', STORY_JS)
        self.assertIn('window.GTN_STORAGE || window.localStorage', EXPORTER_JS)
        self.assertIn("value === 'gtn_lang'", STORY_HTML)
        self.assertIn("value.startsWith('gtn_keybindings_')", STORY_HTML)
        self.assertIn('sessionStorage.getItem(mapped)', STORY_HTML)
        self.assertIn('return readCookie(mapped)', STORY_HTML)


if __name__ == '__main__':
    unittest.main()
