"""反馈 #91：荆露在结算后要自动刷新，不能等签到/重登。"""

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')


def source_between(source, start, end):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


def test_game_over_schedules_a_thorn_dew_refresh():
    phase_handler = source_between(GAME_JS, "} else if (phase === 'game_over') {", "} else if (phase === 'lobby') {")
    assert 'scheduleThornDewRefreshAfterMatch();' in phase_handler

    scheduler = source_between(
        GAME_JS,
        'function scheduleThornDewRefreshAfterMatch()',
        'async function loadThornDewCenter(',
    )
    assert 'setTimeout(' in scheduler
    assert 'loadThornDewCenter(true)' in scheduler


def test_thorn_dew_center_syncs_the_account_balance_cache():
    loader = source_between(GAME_JS, 'async function loadThornDewCenter(', 'async function onThornDewCheckin()')
    assert 'data.balance' in loader
    assert 'currentAccount.thorn_dew_free' in loader
    assert 'currentAccount.thorn_dew_paid' in loader
    assert 'currentAccount.thorn_dew_total' in loader
    assert 'cacheAccount(currentAccount);' in loader
