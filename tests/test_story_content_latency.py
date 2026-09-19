"""故事内容接口的延迟优化：按版本缓存 + ETag 复用 + 冷构建不占事件循环。

`/api/story/content` 过去每次现建 2.8MB（deepcopy 全部卡牌/敌人/事件，实测 ~150ms），
而且是在事件循环里同步跑的；玩家进入故事模式就会按一下整个服务器。
"""

import hashlib
import re
from pathlib import Path

import app


ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
APP_PY = (ROOT / 'app.py').read_text(encoding='utf-8')


def test_story_content_json_is_cached_per_version():
    first_json, first_etag = app._story_content_cached_json()
    second_json, second_etag = app._story_content_cached_json()

    # 命中缓存时直接返回同一个字符串对象（不重新 deepcopy/序列化）
    assert first_json is second_json
    assert first_etag == second_etag
    assert first_etag == hashlib.sha256(first_json.encode('utf-8')).hexdigest()[:32]
    assert first_json.startswith('{') and '"cards"' in first_json
    assert app._STORY_CONTENT_CACHE['key'][0] == app.STORY_CONTENT_VERSION


def test_story_content_cache_key_follows_content_version():
    app._story_content_cached_json()
    original = app._STORY_CONTENT_CACHE['key']
    app._STORY_CONTENT_CACHE['key'] = (original[0], original[1], 'stale-signature')
    _, _ = app._story_content_cached_json()
    assert app._STORY_CONTENT_CACHE['key'] == original


def test_story_content_route_uses_cache_resync_and_etag():
    route = APP_PY.split("def api_story_content_get():", 1)[1].split('@app.route', 1)[0]
    assert 'content_json, etag = run_off_event_loop(_story_content_cached_json)' in route
    assert "request.if_none_match.contains(etag)" in route
    assert "response.headers['Cache-Control'] = 'private, no-cache'" in route
    assert '"content":' in route and '+ content_json' in route


def test_client_resyncs_before_reporting_no_response():
    # 6 秒超时后先补发状态查询，state_update 回来就撤掉兜底提示
    assert 'function requestResyncAfterActionTimeout()' in GAME_JS
    assert "socket.emit('request_game_state');" in GAME_JS
    timeout_block = GAME_JS.split('pendingServerActionTimer = setTimeout(', 1)[1].split('}, timeoutMs);', 1)[0]
    assert 'requestResyncAfterActionTimeout();' in timeout_block
    assert '正在重新同步对局状态' in GAME_JS
    assert 'clearActionResyncTimer();' in GAME_JS
    assert re.search(r"bindSocketEvent\('state_update'[\s\S]{0,400}clearActionResyncTimer\(\);", GAME_JS)
