from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")
STYLE_CSS = (ROOT / "static" / "css" / "style.css").read_text(encoding="utf-8")


def source_between(source: str, start: str, end: str) -> str:
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


def test_normal_hand_uses_seven_columns_and_never_exceeds_three_rows():
    layout_source = source_between(
        GAME_JS,
        "function calculateMinimalHandLayout(",
        "function updateMinimalHandLayout(",
    )
    assert "count > 21 ? Math.ceil(count / 3) : 7" in layout_source
    assert "Math.ceil(count / Math.max(1, columns))" in layout_source
    assert "Math.max(7, Math.min(10, count || 0))" in layout_source
    assert "mobileHandLayout ? 7 : desktopShrinkSlots" in layout_source


def test_urf_hand_switches_only_between_ten_columns_and_five_columns():
    layout_source = source_between(
        GAME_JS,
        "function calculateMinimalHandLayout(",
        "function updateMinimalHandLayout(",
    )
    assert "const isUrf = mode === 'urf'" in layout_source
    assert "columns = splitIntoFive ? 5 : 10" in layout_source
    assert "'urf-5x2'" in layout_source
    assert "'urf-10x1'" in layout_source


def test_minimal_hand_is_a_bounded_grid_and_side_panels_can_shrink():
    layout_css = source_between(
        STYLE_CSS,
        "/* Minimal hand layout:",
        "/* Dark-theme surface contract.",
    )
    assert "display: grid" in layout_css
    assert "grid-template-columns: repeat(var(--hand-card-columns, 7)" in layout_css
    assert "overflow-x: auto" not in layout_css
    assert ".battle-log-chat-row" in layout_css
    assert "min-width: 0" in layout_css


def test_render_and_resize_paths_refresh_the_layout_with_the_current_mode():
    assert "renderPlayerHand(you, gs.mode)" in GAME_JS
    render_source = source_between(
        GAME_JS,
        "function renderPlayerHand(",
        "function canPlayCard(",
    )
    assert "updateMinimalHandLayout(container, hand.length, mode)" in render_source
    assert "updateMinimalHandLayout();" in GAME_JS
