# -*- coding: utf-8 -*-
"""休闲花园门票（Ticket）系统。

获取渠道与限额（设计 2026-09-26）：
- 每日签到：+1（并入现有签到，库存满 5 时不发不补）；
  每 7 天连续签到额外 +1（同样受上限约束）。
- 其他渠道：每一种每天最多 1 张（达成但当日已领满则完全不发）：
  - 天梯（ranked）胜场 >= 3 且本局无人被扣信誉分；
  - 故事模式通关一次（非 EZ 难度）。
- 库存上限 5 张，存 users 表（跨设备一致）。

使用：进入休闲花园消耗 1 张门票换取 10 分钟游玩期（断线暂停倒计时）。
2026-10-09 起取消工作日免费开放时段，任何时间都需要门票。
"""

from datetime import datetime, timedelta, timezone

import db

TICKET_CAP = 5
SIGNIN_TICKETS = 1
STREAK_BONUS_EVERY_DAYS = 7
DAILY_CHANNEL_CAP = 1

PLAY_SESSION_SECONDS = 10 * 60
# 免费开放时段（设计 2026-10-09 取消）：任何时间进入休闲花园都需要门票。
# 常量与函数签名保留，把 FREE_ENTRY_ENABLED 置回 True 即可恢复免费时段。
FREE_ENTRY_ENABLED = False
FREE_WINDOW_SECONDS = 2 * 60 * 60
# UTC+8 免费时段起点（小时）：08:00-10:00、15:00-17:00（工作日）。
FREE_WINDOW_START_HOURS = (8, 15)

CHANNEL_LADDER = 'ladder'
CHANNEL_STORY = 'story'
DAILY_CHANNELS = (CHANNEL_LADDER, CHANNEL_STORY)

_CN_TZ = timezone(timedelta(hours=8))


class TicketError(Exception):
    """带用户可读文案的门票错误。"""

    def __init__(self, message, code='TICKET_ERROR'):
        super().__init__(message)
        self.code = code


def ensure_ticket_columns(conn):
    columns = {row['name'] for row in conn.execute('PRAGMA table_info(users)').fetchall()}
    if 'leisure_tickets' not in columns:
        conn.execute('ALTER TABLE users ADD COLUMN leisure_tickets INTEGER NOT NULL DEFAULT 0')
    if 'leisure_ticket_signin_date' not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN leisure_ticket_signin_date TEXT")
    if 'leisure_ticket_signin_streak' not in columns:
        conn.execute('ALTER TABLE users ADD COLUMN leisure_ticket_signin_streak INTEGER NOT NULL DEFAULT 0')
    if 'leisure_ticket_channel_date' not in columns:
        conn.execute('ALTER TABLE users ADD COLUMN leisure_ticket_channel_date TEXT')
    if 'leisure_ticket_channels' not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN leisure_ticket_channels TEXT NOT NULL DEFAULT ''")


def _now_cn():
    return datetime.now(_CN_TZ)


def _date_key(moment=None):
    return (moment or _now_cn()).strftime('%Y-%m-%d')


def is_free_entry_now(moment=None):
    """免费开放判定（2026-10-09 起取消：恒为 False，休闲花园始终需要门票）。

    原规则为工作日 UTC+8 的 08:00-10:00 / 15:00-17:00 免费开放；
    恢复时把 FREE_ENTRY_ENABLED 置回 True 即可。
    """
    if not FREE_ENTRY_ENABLED:
        return False
    if moment is None:
        moment = _now_cn()
    elif moment.tzinfo is None:
        moment = moment.replace(tzinfo=_CN_TZ)
    else:
        moment = moment.astimezone(_CN_TZ)
    if moment.weekday() >= 5:  # 周六/周日
        return False
    minute_of_day = moment.hour * 60 + moment.minute
    for start_hour in FREE_WINDOW_START_HOURS:
        start = start_hour * 60
        end = start + int(FREE_WINDOW_SECONDS / 60)
        if start <= minute_of_day < end:
            return True
    return False


def get_ticket_balance(conn, user_id):
    ensure_ticket_columns(conn)
    row = conn.execute(
        'SELECT leisure_tickets FROM users WHERE id = ? AND deleted_at IS NULL',
        (int(user_id),),
    ).fetchone()
    if row is None:
        return 0
    return max(0, int(row['leisure_tickets'] or 0))


def grant_tickets(conn, user_id, amount, *, floor_one=False):
    """发门票（受上限 5 约束）；返回实际入账数量。"""
    if int(amount) <= 0:
        return 0
    ensure_ticket_columns(conn)
    row = conn.execute(
        'SELECT leisure_tickets FROM users WHERE id = ?', (int(user_id),),
    ).fetchone()
    if row is None:
        return 0
    balance = max(0, int(row['leisure_tickets'] or 0))
    granted = min(int(amount), TICKET_CAP - balance)
    if granted <= 0:
        return 0
    conn.execute(
        'UPDATE users SET leisure_tickets = ? WHERE id = ?',
        (balance + granted, int(user_id)),
    )
    return granted


def _channel_state(conn, user_id):
    ensure_ticket_columns(conn)
    row = conn.execute(
        'SELECT leisure_ticket_channel_date, leisure_ticket_channels FROM users WHERE id = ?',
        (int(user_id),),
    ).fetchone()
    today = _date_key()
    if row is None:
        return today, set()
    date_key = str(row['leisure_ticket_channel_date'] or '')
    if date_key != today:
        return today, set()
    claimed = str(row['leisure_ticket_channels'] or '')
    return today, {item for item in claimed.split(',') if item}


def claim_daily_channel_ticket(conn, user_id, channel):
    """每日渠道票：每种渠道每天最多 1 张，达成但已领满则不发。

    返回 (granted: bool, reason: str)。reason: granted / cap / already_claimed /
    unknown_channel。
    """
    if channel not in DAILY_CHANNELS:
        return False, 'unknown_channel'
    today, claimed = _channel_state(conn, user_id)
    if channel in claimed:
        return False, 'already_claimed'
    if len(claimed) >= DAILY_CHANNEL_CAP + len(DAILY_CHANNELS):
        # 防御：不可能的分支（渠道数固定），保持语义清晰
        return False, 'cap'
    granted = grant_tickets(conn, user_id, 1)
    if granted <= 0:
        return False, 'cap'
    claimed.add(channel)
    conn.execute(
        '''
        UPDATE users
        SET leisure_ticket_channel_date = ?, leisure_ticket_channels = ?
        WHERE id = ?
        ''',
        (today, ','.join(sorted(claimed)), int(user_id)),
    )
    return True, 'granted'


def grant_checkin_tickets(conn, user_id, streak_day):
    """签到并发门票：每天签到 +1；每 7 天连续签到额外 +1。

    库存满则不发不补（设计确认 #4）。返回 (granted, streak_bonus)。
    """
    today = _date_key()
    ensure_ticket_columns(conn)
    row = conn.execute(
        'SELECT leisure_ticket_signin_date, leisure_ticket_signin_streak FROM users WHERE id = ?',
        (int(user_id),),
    ).fetchone()
    if row is None:
        return 0, 0
    last_date = str(row['leisure_ticket_signin_date'] or '')
    stored_streak = int(row['leisure_ticket_signin_streak'] or 0)
    if last_date == today:
        return 0, 0  # 今天已经发过
    streak = max(1, int(streak_day or 1))
    streak_bonus = 1 if streak > 0 and streak % STREAK_BONUS_EVERY_DAYS == 0 else 0
    total = SIGNIN_TICKETS + streak_bonus
    granted = grant_tickets(conn, user_id, total)
    conn.execute(
        '''
        UPDATE users
        SET leisure_ticket_signin_date = ?, leisure_ticket_signin_streak = ?
        WHERE id = ?
        ''',
        (today, streak, int(user_id)),
    )
    return granted, streak_bonus


def consume_ticket(conn, user_id):
    """消耗一张门票，返回是否成功。"""
    ensure_ticket_columns(conn)
    row = conn.execute(
        'SELECT leisure_tickets FROM users WHERE id = ?', (int(user_id),),
    ).fetchone()
    if row is None:
        return False
    balance = max(0, int(row['leisure_tickets'] or 0))
    if balance <= 0:
        return False
    conn.execute(
        'UPDATE users SET leisure_tickets = ? WHERE id = ?',
        (balance - 1, int(user_id)),
    )
    return True


def ticket_payload(conn, user_id):
    balance = get_ticket_balance(conn, user_id)
    _, claimed = _channel_state(conn, user_id)
    return {
        'tickets': balance,
        'cap': TICKET_CAP,
        'free_entry': is_free_entry_now(),
        'free_windows': [
            {'start_hour': hour, 'minutes': int(FREE_WINDOW_SECONDS / 60)}
            for hour in FREE_WINDOW_START_HOURS
        ] if FREE_ENTRY_ENABLED else [],
        'play_seconds': PLAY_SESSION_SECONDS,
        'channels_claimed': sorted(claimed),
    }


# ===== 10 分钟游玩期（服务端权威计时，断线暂停）=====

def _session_table(conn):
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS leisure_play_sessions (
            user_id INTEGER PRIMARY KEY,
            started_at TEXT NOT NULL,
            elapsed_seconds REAL NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            best_score_ce INTEGER NOT NULL DEFAULT 0,
            best_tier_ce INTEGER NOT NULL DEFAULT 0,
            best_score_cf INTEGER NOT NULL DEFAULT 0,
            best_tier_cf INTEGER NOT NULL DEFAULT 0,
            rewards_granted TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        )
        ''',
    )


def start_play_session(user_id, resume_only=False):
    """消耗一张门票开启 10 分钟游玩期。返回会话信息。

    反馈 #371：存在「暂停中且还有剩余时间」的会话时恢复它，而不是另扣一张
    票并把剩余时间清零（旧逻辑下刷新/离开再回来 = 白丢剩余时间 + 多扣票）。
    resume_only=True（tab 切回时的静默恢复）：无可恢复会话时返回 None，不扣票。
    """
    now = db.utc_now()
    with db.get_db_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        _session_table(conn)
        existing = conn.execute(
            'SELECT * FROM leisure_play_sessions WHERE user_id = ?', (int(user_id),),
        ).fetchone()
        if existing is not None and int(existing['active'] or 0):
            # 已有活动会话：不重复扣票（断线重连恢复）。
            conn.commit()
            return session_payload_from_row(existing)
        if existing is not None and float(existing['elapsed_seconds'] or 0) < PLAY_SESSION_SECONDS:
            # 暂停中的会话还有剩余时间：恢复倒计时，不扣票。
            conn.execute(
                '''
                UPDATE leisure_play_sessions
                SET started_at = ?, active = 1, updated_at = ?
                WHERE user_id = ?
                ''',
                (now, now, int(user_id)),
            )
            conn.commit()
            row = conn.execute(
                'SELECT * FROM leisure_play_sessions WHERE user_id = ?', (int(user_id),),
            ).fetchone()
            return session_payload_from_row(row)
        if resume_only:
            conn.commit()
            return None
        if not consume_ticket(conn, user_id):
            conn.rollback()
            raise TicketError('门票不足', 'NO_TICKET')
        if existing is not None:
            conn.execute(
                '''
                UPDATE leisure_play_sessions
                SET started_at = ?, elapsed_seconds = 0, active = 1,
                    best_score_ce = 0, best_tier_ce = 0,
                    best_score_cf = 0, best_tier_cf = 0,
                    rewards_granted = '', updated_at = ?
                WHERE user_id = ?
                ''',
                (now, now, int(user_id)),
            )
        else:
            conn.execute(
                '''
                INSERT INTO leisure_play_sessions
                    (user_id, started_at, elapsed_seconds, active, updated_at)
                VALUES (?, ?, 0, 1, ?)
                ''',
                (int(user_id), now, now),
            )
        conn.commit()
        row = conn.execute(
            'SELECT * FROM leisure_play_sessions WHERE user_id = ?', (int(user_id),),
        ).fetchone()
        return session_payload_from_row(row)


def pause_play_session(user_id):
    """断线：暂停倒计时（累计已玩秒数）。"""
    now = db.utc_now()
    with db.get_db_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        _session_table(conn)
        row = conn.execute(
            'SELECT * FROM leisure_play_sessions WHERE user_id = ?', (int(user_id),),
        ).fetchone()
        if row is None or not int(row['active'] or 0):
            conn.commit()
            return None
        started = db.datetime.fromisoformat(str(row['started_at']).replace('Z', '+00:00'))
        elapsed = float(row['elapsed_seconds'] or 0) + (db.utc_now_dt() - started).total_seconds()
        conn.execute(
            'UPDATE leisure_play_sessions SET elapsed_seconds = ?, active = 0, updated_at = ? WHERE user_id = ?',
            (elapsed, now, int(user_id)),
        )
        conn.commit()
        return {'paused': True, 'elapsed': elapsed}


def resume_play_session(user_id):
    """重连：恢复倒计时。"""
    now = db.utc_now()
    with db.get_db_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        _session_table(conn)
        row = conn.execute(
            'SELECT * FROM leisure_play_sessions WHERE user_id = ?', (int(user_id),),
        ).fetchone()
        if row is None or not int(row['active'] or 0):
            conn.commit()
            return None
        elapsed = float(row['elapsed_seconds'] or 0)
        if elapsed >= PLAY_SESSION_SECONDS:
            conn.commit()
            return finish_play_session(user_id)
        conn.execute(
            'UPDATE leisure_play_sessions SET started_at = ?, active = 1, updated_at = ? WHERE user_id = ?',
            (now, now, int(user_id)),
        )
        conn.commit()
        return {'resumed': True, 'elapsed': elapsed}


def session_remaining_seconds(conn, user_id):
    """剩余秒数；<=0 表示已用完（调用方负责结算踢出）。"""
    _session_table(conn)
    row = conn.execute(
        'SELECT * FROM leisure_play_sessions WHERE user_id = ?', (int(user_id),),
    ).fetchone()
    if row is None:
        return None
    elapsed = float(row['elapsed_seconds'] or 0)
    if int(row['active'] or 0):
        started = db.datetime.fromisoformat(str(row['started_at']).replace('Z', '+00:00'))
        elapsed += (db.utc_now_dt() - started).total_seconds()
    return max(0.0, PLAY_SESSION_SECONDS - elapsed)


def finish_play_session(user_id):
    """结束会话（时间用尽或主动退出）：返回最终统计。"""
    now = db.utc_now()
    with db.get_db_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        _session_table(conn)
        row = conn.execute(
            'SELECT * FROM leisure_play_sessions WHERE user_id = ?', (int(user_id),),
        ).fetchone()
        if row is None:
            conn.commit()
            return None
        elapsed = float(row['elapsed_seconds'] or 0)
        if int(row['active'] or 0):
            started = db.datetime.fromisoformat(str(row['started_at']).replace('Z', '+00:00'))
            elapsed += (db.utc_now_dt() - started).total_seconds()
        conn.execute(
            'UPDATE leisure_play_sessions SET elapsed_seconds = ?, active = 0, updated_at = ? WHERE user_id = ?',
            # #371：结算后的会话视为时间已用尽（elapsed 记满），与「暂停」
            # （保留真实 elapsed 供恢复）区分——否则 finish 过的会话还能被
            # start_play_session 的恢复分支免费续时间。
            (max(elapsed, PLAY_SESSION_SECONDS), now, int(user_id)),
        )
        conn.commit()
        return session_payload_from_row(conn.execute(
            'SELECT * FROM leisure_play_sessions WHERE user_id = ?', (int(user_id),),
        ).fetchone())


def session_payload_from_row(row):
    elapsed = float(row['elapsed_seconds'] or 0)
    if int(row['active'] or 0):
        started = db.datetime.fromisoformat(str(row['started_at']).replace('Z', '+00:00'))
        elapsed += (db.utc_now_dt() - started).total_seconds()
    remaining = max(0.0, PLAY_SESSION_SECONDS - elapsed)
    return {
        'active': bool(int(row['active'] or 0)),
        'elapsed': round(elapsed, 1),
        'remaining': round(remaining, 1),
        'best_score_ce': int(row['best_score_ce'] or 0),
        'best_tier_ce': int(row['best_tier_ce'] or 0),
        'best_score_cf': int(row['best_score_cf'] or 0),
        'best_tier_cf': int(row['best_tier_cf'] or 0),
        'rewards_granted': str(row['rewards_granted'] or ''),
    }


def record_play_result(user_id, game_key, score, best_tier):
    """更新本游玩期内的最高分/最高合成档。返回是否刷新了纪录。"""
    score = max(0, int(score or 0))
    best_tier = max(0, int(best_tier or 0))
    now = db.utc_now()
    with db.get_db_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        _session_table(conn)
        row = conn.execute(
            'SELECT * FROM leisure_play_sessions WHERE user_id = ?', (int(user_id),),
        ).fetchone()
        if row is None or not int(row['active'] or 0):
            conn.commit()
            return False
        if str(game_key or '') == '2048':
            score_col, tier_col = 'best_score_ce', 'best_tier_ce'
            old_score, old_tier = int(row['best_score_ce'] or 0), int(row['best_tier_ce'] or 0)
        else:
            score_col, tier_col = 'best_score_cf', 'best_tier_cf'
            old_score, old_tier = int(row['best_score_cf'] or 0), int(row['best_tier_cf'] or 0)
        improved = score > old_score or best_tier > old_tier
        if improved:
            conn.execute(
                f'UPDATE leisure_play_sessions SET {score_col} = ?, {tier_col} = ?, updated_at = ? WHERE user_id = ?',
                (max(score, old_score), max(best_tier, old_tier), now, int(user_id)),
            )
        conn.commit()
        return improved
