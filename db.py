import json
import os
import secrets
import re
import sqlite3
from datetime import datetime, timezone

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


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


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
            CREATE TABLE IF NOT EXISTS friendships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requester_id INTEGER NOT NULL,
                addressee_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(requester_id, addressee_id),
                FOREIGN KEY(requester_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(addressee_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_friendships_requester ON friendships(requester_id, status)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_friendships_addressee ON friendships(addressee_id, status)')
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
            existing_ids = [row['player_id'] for row in conn.execute('SELECT player_id FROM users WHERE player_id IS NOT NULL').fetchall()]
            player_id = generate_player_id(existing_ids)
            cur = conn.execute(
                '''
                INSERT INTO users (username, username_lower, password_hash, created_at, player_id)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (name, name.lower(), password_hash, now, player_id),
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
        row = conn.execute('SELECT * FROM users WHERE username_lower = ?', (name.lower(),)).fetchone()
        if row is None or not check_password_hash(row['password_hash'], str(password or '')):
            return None, '用户名或密码错误'
        is_banned = bool(row['banned']) if 'banned' in row.keys() else False
        if is_banned:
            reason = (row['ban_reason'] if 'ban_reason' in row.keys() else '') or ''
            return None, f'账号已被封禁：{reason}' if reason else '账号已被封禁'
        now = utc_now()
        conn.execute('UPDATE users SET last_login_at = ? WHERE id = ?', (now, row['id']))
        conn.commit()
        row = conn.execute('SELECT * FROM users WHERE id = ?', (row['id'],)).fetchone()
        return row_to_user(row), None


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
                row = conn.execute('SELECT * FROM users WHERE username_lower = ?', (name.lower(),)).fetchone()
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
        return row_to_user(conn.execute('SELECT * FROM users WHERE username_lower = ?', (name.lower(),)).fetchone())


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
        return conn.execute(
            'SELECT * FROM users WHERE username_lower = ? AND searchable_by_nickname = 1',
            (name.lower(),),
        ).fetchone()
    return None


def list_friends(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    with get_db_connection() as conn:
        self_row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if self_row is None:
            return None, '请先登录账号'
        rows = conn.execute(
            '''
            SELECT f.*, u1.username AS requester_name, u1.player_id AS requester_player_id,
                   u2.username AS addressee_name, u2.player_id AS addressee_player_id
            FROM friendships f
            JOIN users u1 ON u1.id = f.requester_id
            JOIN users u2 ON u2.id = f.addressee_id
            WHERE f.requester_id = ? OR f.addressee_id = ?
            ORDER BY f.updated_at DESC, f.id DESC
            ''',
            (uid, uid),
        ).fetchall()
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
                'direction': 'incoming' if row['addressee_id'] == uid else 'outgoing',
                'user': _public_social_user(other),
                'matches': _recent_matches_for_username(conn, other['username'], 5) if row['status'] == 'accepted' else [],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
            }
            if row['status'] == 'accepted':
                friends.append(item)
            elif row['status'] == 'pending' and row['addressee_id'] == uid:
                incoming.append(item)
            elif row['status'] == 'pending':
                outgoing.append(item)
        return {
            'settings': get_user_social_settings(uid),
            'friends': friends,
            'incoming': incoming,
            'outgoing': outgoing,
        }, None


def add_friend_request(user_id, identifier):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    now = utc_now()
    with get_db_connection() as conn:
        requester = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if requester is None:
            return None, '请先登录账号'
        target = _find_social_target(conn, identifier)
        if target is None:
            return None, '账号不存在'
        if int(target['id']) == uid:
            return None, '不能添加自己为好友'
        if not bool(target['accept_friend_requests']):
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
                    'UPDATE friendships SET status = ?, updated_at = ? WHERE id = ?',
                    ('accepted', now, existing['id']),
                )
                conn.commit()
                return list_friends(uid)[0], None
            return list_friends(uid)[0], None
        conn.execute(
            '''
            INSERT INTO friendships (requester_id, addressee_id, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (uid, target['id'], 'pending', now, now),
        )
        conn.commit()
    return list_friends(uid)[0], None


def respond_friend_request(user_id, request_id, action):
    try:
        uid = int(user_id)
        rid = int(request_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    normalized = 'accepted' if str(action or '').lower() == 'accept' else 'declined'
    now = utc_now()
    with get_db_connection() as conn:
        row = conn.execute(
            'SELECT * FROM friendships WHERE id = ? AND addressee_id = ? AND status = ?',
            (rid, uid, 'pending'),
        ).fetchone()
        if row is None:
            return None, '好友请求不存在'
        if normalized == 'accepted':
            conn.execute(
                'UPDATE friendships SET status = ?, updated_at = ? WHERE id = ?',
                ('accepted', now, rid),
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
    winner_lowers = {sanitize_username(name).lower() for name in winners if sanitize_username(name)}
    is_draw = str(result or '').lower() == 'draw'
    with get_db_connection() as conn:
        for name in names:
            row = conn.execute('SELECT id, username_lower FROM users WHERE username_lower = ?', (name.lower(),)).fetchone()
            if row is None:
                continue
            if is_draw:
                conn.execute(
                    'UPDATE users SET games_played = games_played + 1, draws = draws + 1 WHERE id = ?',
                    (row['id'],),
                )
            elif row['username_lower'] in winner_lowers:
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
