import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
INDEX_HTML = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')


def test_appearance_settings_expose_fullscreen_toggle():
    assert 'id="settings-fullscreen-row"' in INDEX_HTML
    assert 'id="btn-settings-fullscreen"' in INDEX_HTML
    assert 'function togglePageFullscreen()' in GAME_JS
    assert 'root.requestFullscreen' in GAME_JS
    assert 'root.webkitRequestFullscreen' in GAME_JS
    assert "document.addEventListener('fullscreenchange'" in GAME_JS
    assert "document.addEventListener('webkitfullscreenchange'" in GAME_JS


def test_fullscreen_toggle_has_all_supported_translations():
    for language in ('en', 'zh', 'fr', 'ja'):
        marker = f'Object.assign(I18N.{language}, {{ settings_landscape_mode:'
        section = GAME_JS[GAME_JS.index(marker):]
        section = section[:section.index('});')]
        assert 'settings_fullscreen:' in section
        assert 'settings_enter_fullscreen:' in section
        assert 'settings_exit_fullscreen:' in section
        assert 'settings_fullscreen_unsupported:' in section
        assert 'settings_fullscreen_failed:' in section
