"""Guard: solo and tutorial must reuse the server-side engine only.

The browser used to ship a second JavaScript rules engine
(``static/js/local_solo_worker.js``) that had to be updated in lockstep with the
Python engine. It was never loaded by the page, only by test text assertions,
so rule changes appeared to require two implementations. It is removed: solo
training, the tutorial and every online mode now run on ``GameEngine`` through
socket events, and no browser-side engine may be reintroduced.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")
APP_PY = (ROOT / "app.py").read_text(encoding="utf-8")
INDEX_HTML = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")


def test_local_browser_engine_is_removed():
    assert not (ROOT / "static" / "js" / "local_solo_worker.js").exists()
    assert "new Worker(" not in GAME_JS
    assert "local_solo_worker" not in GAME_JS
    assert "local_solo_worker" not in INDEX_HTML


def test_solo_and_tutorial_use_the_server_engine():
    assert "@socketio.on('solo_start')" in APP_PY
    for event in (
        "solo_play_card",
        "solo_response",
        "solo_resolve_choice",
        "solo_use_trigger",
        "solo_end_turn",
        "tutorial_bot_action",
    ):
        assert f"'{event}'" in APP_PY, event
    assert "emitSoloEvent('solo_start'" in GAME_JS
