from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gameover_shows_own_thorn_dew_reward_contract():
    html = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
    js = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
    css = (ROOT / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')

    assert 'id="gameover-dew"' in html
    assert 'function renderGameOverDew' in js
    assert 'renderGameOverDew(gs);' in js
    assert 'summary.thorn_dew_result' in js
    assert 'String(item.user_id) === myId' in js
    assert 'early_surrender' in js
    assert '.gameover-dew-row' in css
    assert '.gameover-dew.hidden' in css
