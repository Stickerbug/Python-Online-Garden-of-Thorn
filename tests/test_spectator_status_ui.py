from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
STYLE_CSS = (ROOT / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')


def test_spectator_turn_status_uses_current_player_name():
    helper = GAME_JS.split(
        'function formatBattlePhaseText',
        1,
    )[1].split(
        'function formatCompactRoundStatus',
        1,
    )[0]

    assert "return tf(key, currentName);" in helper
    assert "getBattleStatePlayerName(gs, gs.current_player)" in helper
    assert "|| '...'" not in helper


def test_game_view_status_is_derived_from_latest_game_state():
    helper = GAME_JS.split(
        'function getViewStatusText',
        1,
    )[1].split(
        'function refreshBaseStatus',
        1,
    )[0]
    flash_helper = GAME_JS.split(
        'function flashStatus',
        1,
    )[1].split(
        'function showActionToast',
        1,
    )[0]

    assert "return formatGameBottomStatus(gameState);" in helper
    assert "updateStatus(getViewStatusText());" in flash_helper
    assert "_prevStatusText" not in GAME_JS


def test_classic_player_names_do_not_collapse_to_ellipsis():
    block = STYLE_CSS.split(
        '.classic-fighter-name {',
        1,
    )[1].split(
        '}',
        1,
    )[0]

    assert 'text-overflow: clip;' in block
    assert 'white-space: normal;' in block
    assert 'overflow-wrap: anywhere;' in block


def test_spectator_hand_never_enters_mobile_play_confirmation():
    selection_helper = GAME_JS.split(
        'function selectPlayCardForConfirm',
        1,
    )[1].split(
        'async function selectClassicPlayCard',
        1,
    )[0]
    playability_helper = GAME_JS.split(
        'function canPlayCard',
        1,
    )[1].split(
        'function getActionLimitStatusValue',
        1,
    )[0]

    assert 'if (isReadOnlyBattleStatus()) {' in selection_helper
    assert 'clearSelectedPlayCard({ skipRender: true });' in selection_helper
    assert 'if (!gs || isReadOnlyBattleStatus(gs)) return false;' in playability_helper
