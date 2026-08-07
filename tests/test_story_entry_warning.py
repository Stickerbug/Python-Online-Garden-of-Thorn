from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")
STYLE_CSS = (ROOT / "static" / "css" / "style.css").read_text(encoding="utf-8")
INDEX_HTML = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")


def source_between(source, start, end):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


def test_story_entry_is_publicly_visible_but_still_requires_an_account():
    assert 'id="story-mode-entry-row" class="form-row">' in INDEX_HTML
    availability = source_between(
        GAME_JS,
        "function updateStoryEntryAvailability()",
        "function storyTestWarningAcknowledged()",
    )
    assert "hiddenFeaturesEnabled()" not in availability
    assert "row.classList.remove('hidden')" in availability
    assert "button.disabled = false" in availability
    assert "button.setAttribute('aria-disabled', 'false')" in availability
    assert "if (!currentAccount) await refreshAuthMe();" in GAME_JS


def test_story_warning_only_persists_after_confirmation():
    warning = source_between(
        GAME_JS,
        "function openStoryMode()",
        "function setHiddenFeaturesEnabled(",
    )
    assert "STORY_TEST_WARNING_ACK_KEY" in warning
    assert "本模式仍然在测试阶段，不保证关卡和进度的安全性，我们可能随时由于更新删除游玩数据。" in warning
    assert "localStorage.setItem(STORY_TEST_WARNING_ACK_KEY, '1')" in warning
    assert "text: lt({ zh: '退出'" in warning
    exit_branch = warning.split("text: lt({ zh: '退出'", 1)[1]
    assert "localStorage.setItem" not in exit_branch
    assert "{ variant: 'danger' }" in warning


def test_story_warning_ack_has_persistent_storage_fallback_and_red_style():
    assert GAME_JS.count("'gtn_story_test_warning_ack_v1'") >= 3
    assert ".game-alert.game-alert-danger .game-alert-inner" in STYLE_CSS
    assert ".game-alert.game-alert-danger .game-alert-title" in STYLE_CSS
