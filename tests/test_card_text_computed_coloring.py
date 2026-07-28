from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")


def test_computed_icon_amounts_use_the_final_unit_color():
    assert "function matchComputedCardTextToken(value)" in GAME_JS
    assert "等同于(?:(?![，；。！？\\\\r\\\\n]).)+?的" in GAME_JS
    assert "向上取整|向下取整" in GAME_JS
    assert "层数|数量|数值|消耗|回复量" in GAME_JS
    assert "等量|对应|回复量" in GAME_JS
    assert "不少于|不超过|至多|至少" in GAME_JS
    assert "特殊效果超出初始值的层数总和一半的" in GAME_JS
    assert "renderComputedCardTextTokenHtml(computedToken)" in GAME_JS


def test_computed_tokens_render_nested_icons_without_exposing_markers():
    assert "function renderComputedCardTextTokenContent(value)" in GAME_JS
    assert r"/\[\[icon:([a-zA-Z0-9_:-]+)\]\]/gi" in GAME_JS
    assert "renderInlineIconHtml(match[1], match[1])" in GAME_JS


def test_computed_status_amounts_color_the_whole_phrase():
    assert "的易损层数" in GAME_JS
    assert "cls: 'status-fragile'" in GAME_JS
    assert "的护盾" in GAME_JS
    assert "cls: 'status-shield'" in GAME_JS
