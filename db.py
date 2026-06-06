import json
import hashlib
import os
import secrets
import re
import sqlite3
from datetime import datetime, timedelta, timezone

from werkzeug.security import check_password_hash, generate_password_hash


DEFAULT_DB_PATH = '/var/lib/gtn/gtn.sqlite3'
DB_PATH = os.environ.get('GTN_DB_PATH', DEFAULT_DB_PATH)
PLAYER_ID_ALPHABET = '0123456789ABCDEFGHJKLMNPQRSTUVWXYZ'
PLAYER_ID_RE = re.compile(r'^[0-9A-HJ-NP-Z]{6}$')
PLAYER_ID_BLACKLIST_PATH = os.environ.get(
    'GTN_PLAYER_ID_BLACKLIST_PATH',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'playerid_blacklist.txt'),
)
_PLAYER_ID_BLACKLIST_CACHE = None
FRIEND_REQUEST_TTL_DAYS = 30
REMEMBER_TOKEN_DAYS = 60
AUTO_FRIEND_REQUESTER_NAMES = {'stickerbug', 'netherdog', 'eric'}


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def utc_now_dt():
    return datetime.now(timezone.utc).replace(microsecond=0)


def utc_iso(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON;')
    return conn


def _load_player_id_blacklist():
    global _PLAYER_ID_BLACKLIST_CACHE
    if _PLAYER_ID_BLACKLIST_CACHE is not None:
        return _PLAYER_ID_BLACKLIST_CACHE
    items = set()
    try:
        with open(PLAYER_ID_BLACKLIST_PATH, 'r', encoding='utf-8', errors='ignore') as handle:
            for line in handle:
                token = str(line or '').strip().upper()
                if token and len(token) <= 6:
                    items.add(token)
    except OSError:
        items = set()
    _PLAYER_ID_BLACKLIST_CACHE = tuple(sorted(items, key=lambda value: (-len(value), value)))
    return _PLAYER_ID_BLACKLIST_CACHE


def validate_player_id(player_id):
    text = str(player_id or '').strip().upper()
    if not PLAYER_ID_RE.fullmatch(text):
        return False
    for idx in range(len(text) - 1):
        if text[idx] == text[idx + 1]:
            return False

    digit_run = 0
    letter_run = 0
    for ch in text:
        if ch.isdigit():
            digit_run += 1
            letter_run = 0
        else:
            letter_run += 1
            digit_run = 0
        if digit_run > 3 or letter_run > 2:
            return False

    for idx in range(len(text) - 2):
        segment = text[idx:idx + 3]
        if not segment.isdigit():
            continue
        numbers = [int(ch) for ch in segment]
        if numbers[1] - numbers[0] == 1 and numbers[2] - numbers[1] == 1:
            return False
        if numbers[1] - numbers[0] == -1 and numbers[2] - numbers[1] == -1:
            return False

    for bad in _load_player_id_blacklist():
        if bad in text:
            return False
    return True


def _make_player_id_candidate():
    return ''.join(secrets.choice(PLAYER_ID_ALPHABET) for _ in range(6))


def generate_player_id(existing=None):
    used = {str(item or '').upper() for item in (existing or []) if item}
    for _ in range(20000):
        candidate = _make_player_id_candidate()
        if candidate not in used and validate_player_id(candidate):
            return candidate
    raise RuntimeError('unable to generate player id')


def _assign_missing_player_ids(conn):
    rows = conn.execute('SELECT id, player_id FROM users').fetchall()
    counts = {}
    for row in rows:
        current = str(row['player_id'] or '').strip().upper()
        if current:
            counts[current] = counts.get(current, 0) + 1
    existing = set(counts)
    for row in rows:
        current = str(row['player_id'] or '').strip().upper()
        if current and validate_player_id(current) and counts.get(current, 0) == 1:
            continue
        player_id = generate_player_id(existing)
        existing.add(player_id)
        conn.execute('UPDATE users SET player_id = ? WHERE id = ?', (player_id, row['id']))


def init_db():
    parent = os.path.dirname(os.path.abspath(DB_PATH))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with get_db_connection() as conn:
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                username_lower TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login_at TEXT,
                games_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0
            )
            '''
        )
        existing_columns = {row['name'] for row in conn.execute('PRAGMA table_info(users)').fetchall()}
        if 'banned' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0')
        if 'ban_reason' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN ban_reason TEXT')
        if 'banned_at' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN banned_at TEXT')
        if 'player_id' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN player_id TEXT')
        if 'accept_friend_requests' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN accept_friend_requests INTEGER DEFAULT 1')
        if 'searchable_by_nickname' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN searchable_by_nickname INTEGER DEFAULT 1')
        if 'searchable_by_player_id' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN searchable_by_player_id INTEGER DEFAULT 1')
        _assign_missing_player_ids(conn)
        conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_player_id ON users(player_id)')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS remember_tokens (
                selector TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_used_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_remember_tokens_user ON remember_tokens(user_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_remember_tokens_expires ON remember_tokens(expires_at)')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS friendships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requester_id INTEGER NOT NULL,
                addressee_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT,
                addressee_read_at TEXT,
                notice_type TEXT DEFAULT 'request',
                UNIQUE(requester_id, addressee_id),
                FOREIGN KEY(requester_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(addressee_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        friendship_columns = {row['name'] for row in conn.execute('PRAGMA table_info(friendships)').fetchall()}
        if 'expires_at' not in friendship_columns:
            conn.execute('ALTER TABLE friendships ADD COLUMN expires_at TEXT')
        if 'addressee_read_at' not in friendship_columns:
            conn.execute('ALTER TABLE friendships ADD COLUMN addressee_read_at TEXT')
        if 'notice_type' not in friendship_columns:
            conn.execute("ALTER TABLE friendships ADD COLUMN notice_type TEXT DEFAULT 'request'")
        conn.execute('CREATE INDEX IF NOT EXISTS idx_friendships_requester ON friendships(requester_id, status)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_friendships_addressee ON friendships(addressee_id, status)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_friendships_unread ON friendships(addressee_id, status, addressee_read_at)')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT,
                started_at TEXT,
                ended_at TEXT,
                duration_seconds INTEGER,
                player_names_json TEXT,
                winner_name TEXT,
                winner_index INTEGER,
                rounds INTEGER,
                mod_source TEXT,
                mod_hash TEXT,
                result TEXT,
                summary_json TEXT
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS match_replays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                created_at TEXT NOT NULL,
                mode TEXT,
                player_names_json TEXT,
                winner_name TEXT,
                winner_index INTEGER,
                round_num INTEGER,
                duration_ms INTEGER,
                replay_version INTEGER NOT NULL,
                replay_sha256 TEXT NOT NULL,
                replay_size INTEGER NOT NULL,
                replay_blob BLOB NOT NULL,
                mod_source TEXT,
                mod_hash TEXT,
                community_mod_name TEXT
            )
            '''
        )
        replay_columns = {row['name'] for row in conn.execute('PRAGMA table_info(match_replays)').fetchall()}
        if 'mod_source' not in replay_columns:
            conn.execute('ALTER TABLE match_replays ADD COLUMN mod_source TEXT')
        if 'mod_hash' not in replay_columns:
            conn.execute('ALTER TABLE match_replays ADD COLUMN mod_hash TEXT')
        if 'community_mod_name' not in replay_columns:
            conn.execute('ALTER TABLE match_replays ADD COLUMN community_mod_name TEXT')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS replay_mod_blobs (
                sha256 TEXT PRIMARY KEY,
                source TEXT,
                public_url TEXT,
                name TEXT,
                author TEXT,
                version TEXT,
                created_at TEXT NOT NULL,
                json_size INTEGER NOT NULL,
                json_blob BLOB NOT NULL
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS replay_card_def_snapshots (
                sha256 TEXT PRIMARY KEY,
                game_version TEXT,
                git_sha TEXT,
                created_at TEXT NOT NULL,
                json_size INTEGER NOT NULL,
                json_blob BLOB NOT NULL
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS replay_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                replay_id INTEGER NOT NULL,
                dep_type TEXT NOT NULL,
                dep_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_match_replays_created_at ON match_replays(created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_match_replays_mode ON match_replays(mode)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_replay_dependencies_replay_id ON replay_dependencies(replay_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_replay_dependencies_hash ON replay_dependencies(dep_type, dep_hash)')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS card_draft_stats (
                mode TEXT NOT NULL,
                card_id TEXT NOT NULL,
                shown_count INTEGER NOT NULL DEFAULT 0,
                picked_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (mode, card_id)
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_card_draft_stats_mode ON card_draft_stats(mode)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_card_draft_stats_rate ON card_draft_stats(picked_count, shown_count)')
        conn.commit()


def _display_width(s):
    width = 0
    for ch in str(s or ''):
        code = ord(ch)
        if (
            0x4E00 <= code <= 0x9FFF
            or 0x3040 <= code <= 0x30FF
            or 0xAC00 <= code <= 0xD7AF
            or 0xFF00 <= code <= 0xFFEF
            or 0x2000 <= code <= 0x206F
        ):
            width += 2
        else:
            width += 1
    return width


def sanitize_username(raw):
    name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(raw or ''))
    name = re.sub(r'[\u3000\s]+', '', name)
    name = re.sub(r'[^\w\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\-]', '', name)
    return name.strip()


def normalize_username_key(raw):
    name = sanitize_username(raw)
    return re.sub(r'[-_]+', '', name).casefold()


def _find_user_row_by_username_key(conn, username, searchable_by_nickname=None):
    key = normalize_username_key(username)
    if not key:
        return None
    rows = conn.execute('SELECT * FROM users').fetchall()
    for row in rows:
        if normalize_username_key(row['username']) != key:
            continue
        if searchable_by_nickname is not None and bool(row['searchable_by_nickname']) != bool(searchable_by_nickname):
            continue
        return row
    return None


def validate_username(username):
    name = sanitize_username(username)
    if not name:
        return False, '用户名不能为空'
    if _display_width(name) > 16:
        return False, '用户名过长'
    if re.match(r'^[\d]+$', name):
        return False, '用户名不能全为数字'
    if not re.search(r'[\w\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', name):
        return False, '用户名不能全为符号'
    if re.match(r'^[\-_]+$', name):
        return False, '用户名不能全为符号'
    if re.search(r'[\-_]{2,}', name):
        return False, '- 和 _ 不能连续出现'
    return True, ''


def validate_password(password):
    text = str(password or '')
    if len(text) < 6:
        return False, '密码至少需要 6 位'
    if len(text) > 72:
        return False, '密码最多 72 位'
    return True, ''


def row_to_user(row):
    if row is None:
        return None
    return {
        'id': row['id'],
        'username': row['username'],
        'player_id': row['player_id'] if 'player_id' in row.keys() else None,
        'created_at': row['created_at'],
        'last_login_at': row['last_login_at'],
        'games_played': row['games_played'],
        'wins': row['wins'],
        'losses': row['losses'],
        'draws': row['draws'],
        'accept_friend_requests': bool(row['accept_friend_requests']) if 'accept_friend_requests' in row.keys() else True,
        'searchable_by_nickname': bool(row['searchable_by_nickname']) if 'searchable_by_nickname' in row.keys() else True,
        'searchable_by_player_id': bool(row['searchable_by_player_id']) if 'searchable_by_player_id' in row.keys() else True,
        'banned': bool(row['banned']) if 'banned' in row.keys() else False,
        'ban_reason': row['ban_reason'] if 'ban_reason' in row.keys() else None,
        'banned_at': row['banned_at'] if 'banned_at' in row.keys() else None,
    }


def row_to_admin_user(row):
    user = row_to_user(row)
    if user is None:
        return None
    games = int(user.get('games_played') or 0)
    wins = int(user.get('wins') or 0)
    user['win_rate'] = round(wins / games * 100, 1) if games else 0.0
    return user


def create_user(username, password):
    name = sanitize_username(username)
    ok, error = validate_username(name)
    if not ok:
        return None, error
    ok, error = validate_password(password)
    if not ok:
        return None, error
    now = utc_now()
    password_hash = generate_password_hash(str(password))
    try:
        with get_db_connection() as conn:
            if _find_user_row_by_username_key(conn, name) is not None:
                return None, '用户名已存在'
            existing_ids = [row['player_id'] for row in conn.execute('SELECT player_id FROM users WHERE player_id IS NOT NULL').fetchall()]
            player_id = generate_player_id(existing_ids)
            cur = conn.execute(
                '''
                INSERT INTO users (username, username_lower, password_hash, created_at, player_id)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (name, normalize_username_key(name), password_hash, now, player_id),
            )
            conn.commit()
            row = conn.execute('SELECT * FROM users WHERE id = ?', (cur.lastrowid,)).fetchone()
            return row_to_user(row), None
    except sqlite3.IntegrityError:
        return None, '用户名已存在'


def verify_user(username, password):
    name = sanitize_username(username)
    if not name:
        return None, '用户名或密码错误'
    with get_db_connection() as conn:
        row = _find_user_row_by_username_key(conn, name)
        if row is None or not check_password_hash(row['password_hash'], str(password or '')):
            return None, '用户名或密码错误'
        is_banned = bool(row['banned']) if 'banned' in row.keys() else False
        if is_banned:
            reason = (row['ban_reason'] if 'ban_reason' in row.keys() else '') or ''
            return None, f'账号已被封禁：{reason}' if reason else '账号已被封禁'
        return row_to_user(row), None


def mark_user_last_seen(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return False
    with get_db_connection() as conn:
        conn.execute('UPDATE users SET last_login_at = ? WHERE id = ?', (utc_now(), uid))
        conn.commit()
        return True


def change_user_password(user_id, old_password, new_password):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    ok, error = validate_password(new_password)
    if not ok:
        return None, error
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if row is None:
            return None, '请先登录账号'
        if not check_password_hash(row['password_hash'], str(old_password or '')):
            return None, '原密码错误'
        conn.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (generate_password_hash(str(new_password)), uid),
        )
        conn.commit()
        row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        return row_to_user(row), None


def find_user_for_admin(identifier):
    token = str(identifier or '').strip()
    if not token:
        return None
    with get_db_connection() as conn:
        row = None
        if token.isdigit():
            row = conn.execute('SELECT * FROM users WHERE id = ?', (int(token),)).fetchone()
        if row is None and PLAYER_ID_RE.fullmatch(token.upper()):
            row = conn.execute('SELECT * FROM users WHERE player_id = ?', (token.upper(),)).fetchone()
        if row is None:
            name = sanitize_username(token)
            if name:
                row = _find_user_row_by_username_key(conn, name)
        return row_to_user(row)


def admin_change_user_password(identifier, new_password):
    user = find_user_for_admin(identifier)
    if not user:
        return None, '账号不存在'
    ok, error = validate_password(new_password)
    if not ok:
        return None, error
    with get_db_connection() as conn:
        conn.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (generate_password_hash(str(new_password)), user['id']),
        )
        conn.commit()
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()
        return row_to_user(row), None


def admin_set_user_ban(identifier, banned=True, reason=''):
    user = find_user_for_admin(identifier)
    if not user:
        return None, '账号不存在'
    reason_text = str(reason or '').strip()[:200]
    banned_at = utc_now() if banned else None
    with get_db_connection() as conn:
        conn.execute(
            '''
            UPDATE users
            SET banned = ?, ban_reason = ?, banned_at = ?
            WHERE id = ?
            ''',
            (1 if banned else 0, reason_text if banned else None, banned_at, user['id']),
        )
        conn.commit()
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()
        return row_to_user(row), None


def get_user_by_id(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    with get_db_connection() as conn:
        return row_to_user(conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone())


def get_user_by_username(username):
    name = sanitize_username(username)
    if not name:
        return None
    with get_db_connection() as conn:
        return row_to_user(_find_user_row_by_username_key(conn, name))


def _remember_token_hash(token):
    return hashlib.sha256(str(token or '').encode('utf-8')).hexdigest()


def _split_remember_cookie(value):
    text = str(value or '').strip()
    if not text or '.' not in text:
        return '', ''
    selector, token = text.split('.', 1)
    return selector.strip(), token.strip()


def create_remember_token(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return ''
    selector = secrets.token_urlsafe(18)
    token = secrets.token_urlsafe(32)
    now = utc_now()
    expires_at = utc_iso(utc_now_dt() + timedelta(days=REMEMBER_TOKEN_DAYS))
    with get_db_connection() as conn:
        row = conn.execute('SELECT id FROM users WHERE id = ?', (uid,)).fetchone()
        if row is None:
            return ''
        conn.execute(
            '''
            INSERT INTO remember_tokens (selector, user_id, token_hash, created_at, expires_at, last_used_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (selector, uid, _remember_token_hash(token), now, expires_at, now),
        )
        conn.commit()
    return f'{selector}.{token}'


def verify_remember_token(cookie_value):
    selector, token = _split_remember_cookie(cookie_value)
    if not selector or not token:
        return None
    now = utc_now()
    with get_db_connection() as conn:
        conn.execute('DELETE FROM remember_tokens WHERE expires_at < ?', (now,))
        row = conn.execute(
            '''
            SELECT rt.*, u.*
            FROM remember_tokens rt
            JOIN users u ON u.id = rt.user_id
            WHERE rt.selector = ?
            ''',
            (selector,),
        ).fetchone()
        if row is None or row['token_hash'] != _remember_token_hash(token):
            conn.commit()
            return None
        is_banned = bool(row['banned']) if 'banned' in row.keys() else False
        if is_banned:
            conn.execute('DELETE FROM remember_tokens WHERE selector = ?', (selector,))
            conn.commit()
            return None
        conn.execute('UPDATE remember_tokens SET last_used_at = ? WHERE selector = ?', (now, selector))
        conn.commit()
        return row_to_user(row)


def revoke_remember_token(cookie_value):
    selector, _ = _split_remember_cookie(cookie_value)
    if not selector:
        return False
    with get_db_connection() as conn:
        conn.execute('DELETE FROM remember_tokens WHERE selector = ?', (selector,))
        conn.commit()
    return True


ADMIN_USER_SORTS = {
    'id': 'id',
    'player_id': 'player_id',
    'username': 'username_lower',
    'created_at': 'created_at',
    'last_login_at': 'last_login_at',
    'games_played': 'games_played',
    'wins': 'wins',
    'losses': 'losses',
    'draws': 'draws',
    'win_rate': 'CASE WHEN games_played > 0 THEN CAST(wins AS REAL) / games_played ELSE 0 END',
}


CARD_DRAFT_STAT_SORTS = {
    'mode': 'mode',
    'card_id': 'card_id',
    'shown_count': 'shown_count',
    'picked_count': 'picked_count',
    'pick_rate': 'CASE WHEN shown_count > 0 THEN CAST(picked_count AS REAL) / shown_count ELSE 0 END',
    'updated_at': 'updated_at',
}


def record_card_draft_pick(mode, option_ids, picked_id):
    mode_key = str(mode or '').strip()
    if mode_key not in ('1v1', '2v2'):
        return False
    picked = str(picked_id or '').strip()
    counts = {}
    for raw_id in option_ids or []:
        card_id = str(raw_id or '').strip()
        if not card_id:
            continue
        counts[card_id] = counts.get(card_id, 0) + 1
    if not counts or not picked:
        return False
    now = utc_now()
    with get_db_connection() as conn:
        for card_id, shown_inc in counts.items():
            picked_inc = 1 if card_id == picked else 0
            conn.execute(
                '''
                INSERT INTO card_draft_stats (mode, card_id, shown_count, picked_count, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(mode, card_id) DO UPDATE SET
                    shown_count = shown_count + excluded.shown_count,
                    picked_count = picked_count + excluded.picked_count,
                    updated_at = excluded.updated_at
                ''',
                (mode_key, card_id, int(shown_inc), int(picked_inc), now),
            )
        conn.commit()
    return True


def list_card_draft_stats(mode='', sort='pick_rate', order='desc', limit=300, offset=0):
    mode_key = str(mode or '').strip()
    sort_key = str(sort or 'pick_rate')
    sort_expr = CARD_DRAFT_STAT_SORTS.get(sort_key, CARD_DRAFT_STAT_SORTS['pick_rate'])
    direction = 'ASC' if str(order or '').lower() == 'asc' else 'DESC'
    try:
        safe_limit = max(1, min(int(limit), 1000))
    except (TypeError, ValueError):
        safe_limit = 300
    try:
        safe_offset = max(0, int(offset))
    except (TypeError, ValueError):
        safe_offset = 0
    where = ''
    params = []
    if mode_key in ('1v1', '2v2'):
        where = 'WHERE mode = ?'
        params.append(mode_key)
    order_clause = f'{sort_expr} {direction}, shown_count DESC, card_id ASC'
    with get_db_connection() as conn:
        total = conn.execute(f'SELECT COUNT(*) FROM card_draft_stats {where}', params).fetchone()[0]
        rows = conn.execute(
            f'''
            SELECT
                mode,
                card_id,
                shown_count,
                picked_count,
                updated_at,
                CASE WHEN shown_count > 0 THEN CAST(picked_count AS REAL) / shown_count * 100 ELSE 0 END AS pick_rate
            FROM card_draft_stats
            {where}
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
            ''',
            params + [safe_limit, safe_offset],
        ).fetchall()
    return {
        'items': [
            {
                'mode': row['mode'],
                'card_id': row['card_id'],
                'shown_count': row['shown_count'],
                'picked_count': row['picked_count'],
                'pick_rate': round(float(row['pick_rate'] or 0), 2),
                'updated_at': row['updated_at'],
            }
            for row in rows
        ],
        'total': total,
        'limit': safe_limit,
        'offset': safe_offset,
        'sort': sort_key if sort_key in CARD_DRAFT_STAT_SORTS else 'pick_rate',
        'order': 'asc' if direction == 'ASC' else 'desc',
    }


def list_admin_users(query='', sort='last_login_at', order='desc', limit=100, offset=0):
    sort_key = str(sort or 'last_login_at')
    sort_expr = ADMIN_USER_SORTS.get(sort_key, ADMIN_USER_SORTS['last_login_at'])
    direction = 'ASC' if str(order or '').lower() == 'asc' else 'DESC'
    try:
        safe_limit = max(1, min(int(limit), 300))
    except (TypeError, ValueError):
        safe_limit = 100
    try:
        safe_offset = max(0, int(offset))
    except (TypeError, ValueError):
        safe_offset = 0

    name = sanitize_username(query)
    where = ''
    params = []
    if name:
        where = 'WHERE username_lower LIKE ? OR player_id LIKE ?'
        params.extend([f'%{name.lower()}%', f'%{str(query or "").strip().upper()}%'])

    null_rank = 'CASE WHEN last_login_at IS NULL THEN 1 ELSE 0 END'
    if sort_key == 'last_login_at' and direction == 'DESC':
        order_clause = f'{null_rank} ASC, {sort_expr} {direction}, id DESC'
    elif sort_key == 'last_login_at':
        order_clause = f'{null_rank} ASC, {sort_expr} {direction}, id ASC'
    else:
        order_clause = f'{sort_expr} {direction}, id DESC'

    with get_db_connection() as conn:
        total = conn.execute(f'SELECT COUNT(*) FROM users {where}', params).fetchone()[0]
        rows = conn.execute(
            f'''
            SELECT * FROM users
            {where}
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
            ''',
            params + [safe_limit, safe_offset],
        ).fetchall()
    return {
        'users': [row_to_admin_user(row) for row in rows],
        'total': total,
        'limit': safe_limit,
        'offset': safe_offset,
        'sort': sort_key if sort_key in ADMIN_USER_SORTS else 'last_login_at',
        'order': 'asc' if direction == 'ASC' else 'desc',
    }


def _row_to_match_summary(row):
    if row is None:
        return None
    try:
        player_names = json.loads(row['player_names_json'] or '[]')
    except Exception:
        player_names = []
    try:
        summary = json.loads(row['summary_json'] or '{}')
    except Exception:
        summary = {}
    return {
        'id': row['id'],
        'mode': row['mode'],
        'started_at': row['started_at'],
        'ended_at': row['ended_at'],
        'duration_seconds': row['duration_seconds'],
        'players': player_names,
        'winner_name': row['winner_name'],
        'winner_index': row['winner_index'],
        'rounds': row['rounds'],
        'mod_source': row['mod_source'],
        'mod_hash': row['mod_hash'],
        'result': row['result'],
        'room_id': summary.get('room_id'),
    }


def get_admin_user_detail(user_id, match_limit=30):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    try:
        safe_match_limit = max(1, min(int(match_limit), 100))
    except (TypeError, ValueError):
        safe_match_limit = 30
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if row is None:
            return None
        user = row_to_admin_user(row)
        pattern = f'%"{user["username"]}"%'
        matches = conn.execute(
            '''
            SELECT * FROM matches
            WHERE player_names_json LIKE ?
            ORDER BY id DESC
            LIMIT ?
            ''',
            (pattern, safe_match_limit),
        ).fetchall()
    return {
        'user': user,
        'matches': [_row_to_match_summary(match) for match in matches],
    }


def _public_social_user(row):
    user = row_to_admin_user(row)
    if not user:
        return None
    return {
        'id': user['id'],
        'username': user['username'],
        'player_id': user.get('player_id'),
        'created_at': user.get('created_at'),
        'last_login_at': user.get('last_login_at'),
        'games_played': user.get('games_played') or 0,
        'wins': user.get('wins') or 0,
        'losses': user.get('losses') or 0,
        'draws': user.get('draws') or 0,
        'win_rate': user.get('win_rate') or 0.0,
    }


def _basic_social_user(row):
    user = row_to_user(row)
    if not user:
        return None
    return {
        'id': user['id'],
        'username': user['username'],
        'player_id': user.get('player_id'),
    }


def _cleanup_expired_friend_requests(conn):
    cutoff = utc_iso(utc_now_dt() - timedelta(days=FRIEND_REQUEST_TTL_DAYS))
    conn.execute(
        '''
        DELETE FROM friendships
        WHERE status = ? AND (
            (expires_at IS NOT NULL AND expires_at < ?)
            OR (expires_at IS NULL AND created_at < ?)
        )
        ''',
        ('pending', cutoff, cutoff),
    )


def _friend_request_expires_at():
    return utc_iso(utc_now_dt() + timedelta(days=FRIEND_REQUEST_TTL_DAYS))


def _is_auto_friend_requester(row):
    name = row['username'] if row is not None and 'username' in row.keys() else ''
    return normalize_username_key(name) in AUTO_FRIEND_REQUESTER_NAMES


def _mark_friend_notifications_read(conn, user_id):
    now = utc_now()
    conn.execute(
        '''
        UPDATE friendships
        SET addressee_read_at = COALESCE(addressee_read_at, ?)
        WHERE addressee_id = ?
          AND addressee_read_at IS NULL
          AND (status = ? OR notice_type = ?)
        ''',
        (now, user_id, 'pending', 'auto_add'),
    )


def _friend_unread_count(conn, user_id):
    row = conn.execute(
        '''
        SELECT COUNT(*) AS count
        FROM friendships
        WHERE addressee_id = ?
          AND addressee_read_at IS NULL
          AND (status = ? OR notice_type = ?)
        ''',
        (user_id, 'pending', 'auto_add'),
    ).fetchone()
    return int(row['count'] or 0) if row else 0


def _recent_matches_for_username(conn, username, limit=5):
    pattern = f'%"{username}"%'
    rows = conn.execute(
        '''
        SELECT * FROM matches
        WHERE player_names_json LIKE ?
        ORDER BY id DESC
        LIMIT ?
        ''',
        (pattern, max(1, min(int(limit or 5), 20))),
    ).fetchall()
    return [_row_to_match_summary(row) for row in rows]


def get_user_social_settings(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return None
    return {
        'accept_friend_requests': bool(user.get('accept_friend_requests')),
        'searchable_by_nickname': bool(user.get('searchable_by_nickname')),
        'searchable_by_player_id': bool(user.get('searchable_by_player_id')),
    }


def update_user_social_settings(user_id, settings):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    allowed = {
        'accept_friend_requests',
        'searchable_by_nickname',
        'searchable_by_player_id',
    }
    updates = []
    params = []
    for key in allowed:
        if key in (settings or {}):
            updates.append(f'{key} = ?')
            params.append(1 if bool(settings.get(key)) else 0)
    if not updates:
        return get_user_social_settings(uid), None
    params.append(uid)
    with get_db_connection() as conn:
        row = conn.execute('SELECT id FROM users WHERE id = ?', (uid,)).fetchone()
        if row is None:
            return None, '请先登录账号'
        conn.execute(f'UPDATE users SET {", ".join(updates)} WHERE id = ?', params)
        conn.commit()
    return get_user_social_settings(uid), None


def _find_social_target(conn, identifier):
    token = str(identifier or '').strip()
    if not token:
        return None
    player_id = token.upper()
    if PLAYER_ID_RE.fullmatch(player_id):
        row = conn.execute(
            'SELECT * FROM users WHERE player_id = ? AND searchable_by_player_id = 1',
            (player_id,),
        ).fetchone()
        if row is not None:
            return row
    name = sanitize_username(token)
    if name:
        return _find_user_row_by_username_key(conn, name, searchable_by_nickname=True)
    return None


def list_friends(user_id, mark_read=False):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    with get_db_connection() as conn:
        self_row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if self_row is None:
            return None, '请先登录账号'
        _cleanup_expired_friend_requests(conn)
        if mark_read:
            _mark_friend_notifications_read(conn, uid)
        conn.commit()
        rows = conn.execute(
            '''
            SELECT f.*
            FROM friendships f
            WHERE f.requester_id = ? OR f.addressee_id = ?
            ORDER BY f.updated_at DESC, f.id DESC
            ''',
            (uid, uid),
        ).fetchall()
        unread_count = _friend_unread_count(conn, uid)
        friends = []
        incoming = []
        outgoing = []
        for row in rows:
            other_id = row['addressee_id'] if row['requester_id'] == uid else row['requester_id']
            other = conn.execute('SELECT * FROM users WHERE id = ?', (other_id,)).fetchone()
            if other is None:
                continue
            item = {
                'request_id': row['id'],
                'status': row['status'],
                'notice_type': row['notice_type'] if 'notice_type' in row.keys() else 'request',
                'is_unread': row['addressee_id'] == uid and not (row['addressee_read_at'] if 'addressee_read_at' in row.keys() else None),
                'direction': 'incoming' if row['addressee_id'] == uid else 'outgoing',
                'user': _public_social_user(other) if row['status'] == 'accepted' else _basic_social_user(other),
                'matches': _recent_matches_for_username(conn, other['username'], 5) if row['status'] == 'accepted' else [],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'expires_at': row['expires_at'] if 'expires_at' in row.keys() else None,
            }
            if row['status'] == 'accepted':
                friends.append(item)
                if item['notice_type'] == 'auto_add' and row['addressee_id'] == uid:
                    incoming.append({**item, 'status': 'notice'})
            elif row['status'] == 'pending' and row['addressee_id'] == uid:
                incoming.append(item)
            elif row['status'] == 'pending':
                outgoing.append(item)
        return {
            'settings': get_user_social_settings(uid),
            'friends': friends,
            'incoming': incoming,
            'outgoing': outgoing,
            'unread_count': unread_count,
        }, None


def add_friend_request(user_id, identifier):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    now = utc_now()
    with get_db_connection() as conn:
        _cleanup_expired_friend_requests(conn)
        requester = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if requester is None:
            return None, '请先登录账号'
        target = _find_social_target(conn, identifier)
        if target is None:
            return None, '账号不存在'
        if int(target['id']) == uid:
            return None, '不能添加自己为好友'
        auto_add = _is_auto_friend_requester(requester)
        if not auto_add and not bool(target['accept_friend_requests']):
            return None, '对方暂不接受好友请求'
        existing = conn.execute(
            '''
            SELECT * FROM friendships
            WHERE (requester_id = ? AND addressee_id = ?)
               OR (requester_id = ? AND addressee_id = ?)
            ORDER BY id DESC
            LIMIT 1
            ''',
            (uid, target['id'], target['id'], uid),
        ).fetchone()
        if existing is not None:
            if existing['status'] == 'accepted':
                return list_friends(uid)[0], None
            if existing['status'] == 'pending' and existing['addressee_id'] == uid:
                conn.execute(
                    'UPDATE friendships SET status = ?, updated_at = ?, addressee_read_at = COALESCE(addressee_read_at, ?) WHERE id = ?',
                    ('accepted', now, now, existing['id']),
                )
                conn.commit()
                return list_friends(uid)[0], None
            if auto_add:
                conn.execute(
                    '''
                    UPDATE friendships
                    SET status = ?, updated_at = ?, notice_type = ?, expires_at = NULL, addressee_read_at = NULL
                    WHERE id = ?
                    ''',
                    ('accepted', now, 'auto_add', existing['id']),
                )
                conn.commit()
                return list_friends(uid)[0], None
            return list_friends(uid)[0], None
        status = 'accepted' if auto_add else 'pending'
        notice_type = 'auto_add' if auto_add else 'request'
        expires_at = None if auto_add else _friend_request_expires_at()
        conn.execute(
            '''
            INSERT INTO friendships (
                requester_id, addressee_id, status, created_at, updated_at,
                expires_at, addressee_read_at, notice_type
            )
            VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
            ''',
            (uid, target['id'], status, now, now, expires_at, notice_type),
        )
        conn.commit()
    return list_friends(uid)[0], None


def respond_friend_request(user_id, request_id, action):
    try:
        uid = int(user_id)
        rid = int(request_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    action_text = str(action or '').lower()
    now = utc_now()
    with get_db_connection() as conn:
        _cleanup_expired_friend_requests(conn)
        row = conn.execute(
            'SELECT * FROM friendships WHERE id = ? AND addressee_id = ? AND status = ?',
            (rid, uid, 'pending'),
        ).fetchone()
        if row is None:
            return None, '好友请求不存在'
        if action_text == 'ignore':
            conn.execute(
                'UPDATE friendships SET addressee_read_at = COALESCE(addressee_read_at, ?), updated_at = ? WHERE id = ?',
                (now, now, rid),
            )
        elif action_text == 'accept':
            conn.execute(
                'UPDATE friendships SET status = ?, updated_at = ?, addressee_read_at = COALESCE(addressee_read_at, ?) WHERE id = ?',
                ('accepted', now, now, rid),
            )
        else:
            conn.execute('DELETE FROM friendships WHERE id = ?', (rid,))
        conn.commit()
    return list_friends(uid)[0], None


def remove_friend(user_id, friend_user_id):
    try:
        uid = int(user_id)
        fid = int(friend_user_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    with get_db_connection() as conn:
        conn.execute(
            '''
            DELETE FROM friendships
            WHERE status = ? AND (
                (requester_id = ? AND addressee_id = ?)
                OR (requester_id = ? AND addressee_id = ?)
            )
            ''',
            ('accepted', uid, fid, fid, uid),
        )
        conn.commit()
    return list_friends(uid)[0], None


def save_match_summary(summary):
    data = dict(summary or {})
    with get_db_connection() as conn:
        cur = conn.execute(
            '''
            INSERT INTO matches (
                mode, started_at, ended_at, duration_seconds, player_names_json,
                winner_name, winner_index, rounds, mod_source, mod_hash, result, summary_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                data.get('mode'),
                data.get('started_at'),
                data.get('ended_at'),
                data.get('duration_seconds'),
                json.dumps(data.get('players') or [], ensure_ascii=False),
                data.get('winner_name'),
                data.get('winner_index'),
                data.get('rounds'),
                data.get('mod_source'),
                data.get('mod_hash'),
                data.get('result'),
                json.dumps(data, ensure_ascii=False),
            ),
        )
        conn.commit()
        return cur.lastrowid


def increment_user_stats(usernames, winner_name=None, result='finished'):
    names = [sanitize_username(name) for name in (usernames or [])]
    names = [name for name in names if name]
    if not names:
        return
    winners = winner_name if isinstance(winner_name, (list, tuple, set)) else [winner_name]
    winner_keys = {normalize_username_key(name) for name in winners if sanitize_username(name)}
    is_draw = str(result or '').lower() == 'draw'
    with get_db_connection() as conn:
        for name in names:
            row = _find_user_row_by_username_key(conn, name)
            if row is None:
                continue
            if is_draw:
                conn.execute(
                    'UPDATE users SET games_played = games_played + 1, draws = draws + 1 WHERE id = ?',
                    (row['id'],),
                )
            elif normalize_username_key(row['username']) in winner_keys:
                conn.execute(
                    'UPDATE users SET games_played = games_played + 1, wins = wins + 1 WHERE id = ?',
                    (row['id'],),
                )
            else:
                conn.execute(
                    'UPDATE users SET games_played = games_played + 1, losses = losses + 1 WHERE id = ?',
                    (row['id'],),
                )
        conn.commit()
