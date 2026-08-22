from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_rich_player_names_have_descender_safe_line_boxes():
    for relative_path in (
        "static/css/style.css",
        "static/css/story.css",
        "static/css/shared-lobby-chat.css",
    ):
        css = (ROOT / relative_path).read_text(encoding="utf-8")
        assert ".player-name-value {" in css
        assert "display: inline-block;" in css
        assert "line-height: 1.3;" in css
        assert "overflow: visible;" in css


def test_plain_nickname_surfaces_keep_descender_line_height():
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")
    for selector in (
        ".title-preview-name",
        ".title-shop-preview-name",
        ".account-nickname-display",
        ".account-replay-setup-player-name",
        ".replay-player-name",
    ):
        assert selector in css
    assert "line-height: 1.3;" in css
