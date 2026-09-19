from pathlib import Path
import json
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")
STYLE_CSS = (ROOT / "static" / "css" / "style.css").read_text(encoding="utf-8")


def source_between(source: str, start: str, end: str) -> str:
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


def test_normal_hand_spreads_desktop_but_keeps_seven_columns_on_touch():
    """反馈 #142：桌面端列数与手牌数对齐（最多 10 槽），触屏/窄屏仍是 7 列。"""
    layout_source = source_between(
        GAME_JS,
        "function calculateMinimalHandLayout(",
        "function updateMinimalHandLayout(",
    )
    assert "Math.max(1, Math.min(10, count || 0))" in layout_source
    assert "count > 21 ? Math.ceil(count / 3) : (mobileHandLayout ? 7 : desktopSlots)" in layout_source
    assert "Math.ceil(count / Math.max(1, columns))" in layout_source
    assert "Math.max(columns, mobileHandLayout ? 7 : desktopSlots)" in layout_source


def test_normal_hand_never_exceeds_three_rows_for_any_count():
    node = shutil.which("node")
    assert node, "node is required for this behaviour test"
    layout_source = source_between(
        GAME_JS,
        "function calculateMinimalHandLayout(",
        "function measureMinimalHandAvailableHeight(",
    )
    counts = [1, 2, 3, 5, 7, 8, 10, 11, 14, 20, 21, 22, 25, 30, 45, 60]
    script = f'''
{layout_source}
const result = {{}};
for (const count of {json.dumps(counts)}) {{
    const desktop = calculateMinimalHandLayout(count, 'normal', 1280, false, 620, false);
    const touch = calculateMinimalHandLayout(count, 'normal', 1280, true, 620, false);
    result[count] = {{
        desktopRows: desktop.rows,
        touchCols: touch.columns,
        touchRows: touch.rows,
        dense: desktop.layout,
    }};
}}
console.log(JSON.stringify(result));
'''
    completed = subprocess.run([node, "-e", script], capture_output=True, text=True, encoding="utf-8")
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout.strip())
    for count, values in result.items():
        total = int(count)
        assert values["desktopRows"] <= 3, (count, values)
        assert values["touchRows"] <= 3, (count, values)
        if total <= 21:
            assert values["touchCols"] == 7, (count, values)
        else:
            # 超过 21 张走紧凑排版：列数 = ceil(count / 3)，保证最多 3 行
            assert values["touchCols"] == -(-total // 3), (count, values)
            assert values["touchRows"] == 3, (count, values)
        assert values["dense"] == ("normal-dense" if total > 21 else "normal-7"), (count, values)


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
    assert "grid-template-columns: repeat(" in layout_css
    assert "var(--hand-card-columns, 7)" in layout_css
    assert "minmax(0, var(--minimal-hand-card-width, 140px))" in layout_css
    assert "minmax(0, 1fr)" not in layout_css
    assert "justify-content: start" in layout_css
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
