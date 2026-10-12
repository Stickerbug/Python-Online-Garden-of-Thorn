# -*- coding: utf-8 -*-
"""休闲花园服务端对局会话守卫（2026-10-12 安全增强）。

规则（用户口径）：
1. 玩家开始一局时由**服务器**开始 10 分钟计时（不再信任本地计时）；
2. 计时结束 → 强制结算该局（按服务端已存分数，幂等发结算荆露）；
3. 每 10 秒心跳一次，心跳超时（约 2 个周期没到）视为断线 → 直接结算；
4. 有进行中的局时不允许开新一局/退出（restart 拒绝并先结算旧局）；
5. 玩家退出或游戏失败 → 直接结算（失败走 game_over 同步，退出由心跳停跳兜底）。

会话为进程内存（与房间体系一致，生产为单实例）；结算动作复用各小游戏
service 的 sync_progress(game_over=True)（幂等发奖）+ 关闭活动局行。
"""

import threading
import time

LEISURE_SESSION_LIMIT_SECONDS = 600  # 10 分钟强制结算
LEISURE_HEARTBEAT_TIMEOUT_SECONDS = 25  # 客户端 10s 一跳，两跳半没到判失联

_lock = threading.Lock()
# user_id -> {'service': 'suika'|'2048', 'game_uid': str, 'started_at': ts, 'last_beat': ts}
_sessions = {}


def active_session(user_id):
    with _lock:
        session = _sessions.get(int(user_id))
        return dict(session) if session else None


def begin_session(user_id, service, game_uid, now=None):
    """开始一局：登记服务器计时起点。已有进行中的局返回旧会话（调用方应拒绝）。"""
    now = time.time() if now is None else now
    user_id = int(user_id)
    with _lock:
        existing = _sessions.get(user_id)
        if existing:
            return dict(existing), False
        _sessions[user_id] = {
            'service': str(service),
            'game_uid': str(game_uid),
            'started_at': now,
            'last_beat': now,
        }
        return dict(_sessions[user_id]), True


def heartbeat(user_id, now=None):
    now = time.time() if now is None else now
    with _lock:
        session = _sessions.get(int(user_id))
        if session:
            session['last_beat'] = now
            return dict(session)
        return None


def clear_session(user_id):
    with _lock:
        return _sessions.pop(int(user_id), None)


def due_sessions(now=None):
    """列出应强制结算的会话（超时或失联）。"""
    now = time.time() if now is None else now
    due = []
    with _lock:
        for user_id, session in list(_sessions.items()):
            elapsed = now - float(session['started_at'])
            stale = now - float(session['last_beat'])
            if elapsed >= LEISURE_SESSION_LIMIT_SECONDS or stale >= LEISURE_HEARTBEAT_TIMEOUT_SECONDS:
                due.append((user_id, dict(session),
                            'time_limit' if elapsed >= LEISURE_SESSION_LIMIT_SECONDS else 'offline'))
    return due


def force_settle_now(user_id, session=None):
    """立即强制结算一局（服务端已存分数口径），并清除会话。返回结算结果。"""
    session = session or active_session(user_id)
    if not session:
        return {'settled': False, 'reason': 'no_session'}
    clear_session(user_id)
    service_name = str(session.get('service') or '')
    game_uid = str(session.get('game_uid') or '')
    user_id = int(user_id)
    try:
        from db import get_db_connection
        with get_db_connection() as conn:
            if service_name == 'suika':
                import minigame_suika_service as svc
                result = svc.sync_progress(
                    conn, user_id, game_uid,
                    int(svc.load_state(conn, user_id).get('drop_index') or 0),
                    [], game_over=True, source='server_force',
                )
                conn.execute(
                    "UPDATE minigame_suika_games SET status='closed', closed_at=datetime('now'),"
                    " updated_at=datetime('now') WHERE user_id=? AND game_uid=? AND status='active'",
                    (user_id, game_uid),
                )
                conn.commit()
            elif service_name == '2048':
                # 2048 是服务端重放验证制（无 game_over 同步参数）：
                # 已验证的分数在历次 sync 已入账，强制结算=关闭活动局。
                import minigame_2048_service as svc  # noqa: F401
                conn.execute(
                    "UPDATE minigame_2048_games SET status='closed', closed_at=datetime('now'),"
                    " updated_at=datetime('now') WHERE user_id=? AND game_uid=? AND status='active'",
                    (user_id, game_uid),
                )
                conn.commit()
                result = {'status': 'closed'}
            else:
                return {'settled': False, 'reason': 'unknown_service'}
        return {'settled': True, 'service': service_name, 'game_uid': game_uid,
                'result': result}
    except Exception as exc:  # 结算失败也要清会话，不能卡死玩家
        return {'settled': False, 'reason': f'error: {exc}'}


def sweep(now=None):
    """扫一遍全部会话，结算到期的。供后台线程周期调用。"""
    settled = []
    for user_id, session, reason in due_sessions(now=now):
        outcome = force_settle_now(user_id, session)
        outcome['reason_code'] = reason
        settled.append(outcome)
    return settled
