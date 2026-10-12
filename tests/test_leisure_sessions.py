# -*- coding: utf-8 -*-
"""休闲花园服务端对局会话守卫（2026-10-12 安全增强）单元测试。

规则：开局由服务器开始 10 分钟计时；超时或心跳失联强制结算；
活跃局内不允许开新一局（restart 先结算旧局再拒绝）。
"""

import time

import leisure_sessions as ls


def _clear_all():
    with ls._lock:
        ls._sessions.clear()


def test_begin_and_active_session():
    _clear_all()
    session, created = ls.begin_session(101, 'suika', 'uid-a')
    assert created and session['game_uid'] == 'uid-a'
    active = ls.active_session(101)
    assert active and active['service'] == 'suika'
    assert ls.active_session(102) is None


def test_no_second_game_while_active():
    _clear_all()
    ls.begin_session(101, 'suika', 'uid-a')
    existing, created = ls.begin_session(101, '2048', 'uid-b')
    assert not created and existing['game_uid'] == 'uid-a'


def test_time_limit_forces_settlement():
    _clear_all()
    now = time.time()
    ls.begin_session(101, 'suika', 'uid-a', now=now)
    ls.heartbeat(101, now=now + 590)  # 临近超时仍保持心跳在线
    assert not ls.due_sessions(now=now + 595)
    due = ls.due_sessions(now=now + ls.LEISURE_SESSION_LIMIT_SECONDS + 1)
    assert len(due) == 1 and due[0][2] == 'time_limit'
    ls.clear_session(101)


def test_heartbeat_timeout_marks_offline():
    _clear_all()
    now = time.time()
    ls.begin_session(101, '2048', 'uid-b', now=now)
    assert not ls.due_sessions(now=now + 10)
    due = ls.due_sessions(now=now + ls.LEISURE_HEARTBEAT_TIMEOUT_SECONDS + 1)
    assert len(due) == 1 and due[0][2] == 'offline'
    # 心跳刷新后不再失联
    ls.heartbeat(101, now=now + ls.LEISURE_HEARTBEAT_TIMEOUT_SECONDS + 2)
    later = now + ls.LEISURE_HEARTBEAT_TIMEOUT_SECONDS + 10  # 心跳刚刷新，不再失联
    assert not ls.due_sessions(now=later)
    ls.clear_session(101)


def test_clear_and_no_session_settle():
    _clear_all()
    assert ls.force_settle_now(999) == {'settled': False, 'reason': 'no_session'}
