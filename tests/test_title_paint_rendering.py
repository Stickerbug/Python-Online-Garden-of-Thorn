from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
STORY_JS = (ROOT / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')
TITLE_EDITOR_JS = (ROOT / 'static' / 'js' / 'titleeditor.js').read_text(encoding='utf-8')
STYLE_CSS = (ROOT / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')
STORY_CSS = (ROOT / 'static' / 'css' / 'story.css').read_text(encoding='utf-8')
TITLE_EDITOR_CSS = (ROOT / 'static' / 'css' / 'titleeditor.css').read_text(encoding='utf-8')
APP_PY = (ROOT / 'app.py').read_text(encoding='utf-8')


def test_legacy_solid_title_paint_explicitly_restores_visible_text():
    assert "className: 'title-paint-solid'" in GAME_JS
    assert '-webkit-text-fill-color:currentColor' in GAME_JS
    assert "el.style.removeProperty('-webkit-text-fill-color')" in GAME_JS
    assert "el.style.removeProperty('background-image')" in GAME_JS


def test_story_and_editor_solid_title_paints_cannot_inherit_transparency():
    assert "element.style.removeProperty('-webkit-text-fill-color')" in STORY_JS
    assert "element.style.webkitTextFillColor = 'currentColor'" in STORY_JS
    assert "'-webkit-text-fill-color': 'currentColor'" in TITLE_EDITOR_JS

    for stylesheet in (STYLE_CSS, STORY_CSS, TITLE_EDITOR_CSS):
        solid_rule = stylesheet.split('.title-paint-solid,', 1)[1].split('}', 1)[0]
        assert 'background-image: none !important' in solid_rule
        assert '-webkit-text-fill-color: currentColor' in solid_rule


def test_title_color_fix_has_a_static_cache_version():
    assert 'title-solid-color-1' in APP_PY
