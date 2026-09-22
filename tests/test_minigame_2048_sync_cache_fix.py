# -*- coding: utf-8 -*-
"""Craft Eternal 限流 / 刷新丢档修复的静态回归。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_rate_limit_is_per_account_not_proxy_loopback():
    app = (ROOT / 'app.py').read_text(encoding='utf-8')
    assert "_minigame_2048_rate_limited(request.remote_addr" not in app
    assert "f'u{identity[0]}', 'minigame2048_state', limit=1200" in app
    assert "f'u{identity[0]}', 'minigame2048_sync', limit=3000" in app
    # 榜单（服务端已有 15 秒缓存，这是兜底）与 restart 也按账号限流（与 suika 同口径）
    assert "f'u{identity[0]}', 'minigame2048_leaderboard', limit=300" in app
    assert "f'u{identity[0]}', 'minigame2048_restart', limit=60" in app


def test_service_worker_does_not_cache_user_specific_document():
    sw = (ROOT / 'static' / 'minigame-2048' / 'sw.js').read_text(encoding='utf-8')
    assert "const CACHE = 'gtn-mg2048-v3';" in sw
    assert "if (url.pathname === '/minigame/2048' || request.destination === 'document') return;" in sw
    shell_block = sw.split('const SHELL = [', 1)[1].split('];', 1)[0]
    assert "'/minigame/2048'" not in shell_block


def test_client_keeps_local_game_when_state_request_fails():
    js = (ROOT / 'static' / 'js' / 'minigame_2048.js').read_text(encoding='utf-8')
    assert 'const SYNC_DEBOUNCE_MS = 1000;' in js
    assert 'replace_active: state.replaceActive === true,' in js
    assert 'startLocalGame(undefined, { replaceActive: true });' in js
    # /state 的失败响应绝不能再交给 adoptServerState 当成存档
    assert 'if (!response.ok) {' in js
    assert '服务器繁忙，本地进度已保留，稍后自动校验' in js


def test_boot_reconciles_stale_local_new_with_server_progress():
    js = (ROOT / 'static' / 'js' / 'minigame_2048.js').read_text(encoding='utf-8')
    assert 'state.localNew === true && serverHasProgress && state.replaceActive !== true' in js
    assert '已回到服务器上的上一局' in js
