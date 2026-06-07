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
ROLE_TYPES = {'admin', 'staff', 'contributor', 'sponsor', 'none'}
ROLE_COLOR_TOKENS = {'admin', 'bloom', 'guard', 'thorn', 'root', 'neutral'}
ROLE_DEFAULTS = {
    'admin': {
        'role_key': 'admin',
        'title': '管理员',
        'color': 'admin',
        'sort_order': 0,
        'can_direct_friend': True,
        'chat_exempt': True,
    },
    'staff': {
        'role_key': 'staff',
        'title': '技术人员',
        'color': 'bloom',
        'sort_order': 1,
        'can_direct_friend': True,
        'chat_exempt': True,
    },
    'contributor': {
        'role_key': 'contributor',
        'title': '贡献者',
        'color': 'guard',
        'sort_order': 2,
        'can_direct_friend': False,
        'chat_exempt': False,
    },
    'sponsor': {
        'role_key': 'sponsor',
        'title': '赞助者',
        'color': 'bloom',
        'sort_order': 3,
        'can_direct_friend': False,
        'chat_exempt': False,
    },
}
BUILTIN_USER_ROLES = {
    'stickerbug': {
        **ROLE_DEFAULTS['admin'],
        'role_type': 'admin',
        'role_key': 'admin',
        'title': '管理员',
    },
    'netherdog': {
        **ROLE_DEFAULTS['staff'],
        'role_type': 'staff',
        'role_key': 'chief_designer',
        'title': '总设计师',
    },
    'eric': {
        **ROLE_DEFAULTS['staff'],
        'role_type': 'staff',
        'role_key': 'chief_designer',
        'title': '总设计师',
    },
    'winniepooh': {
        **ROLE_DEFAULTS['contributor'],
        'role_type': 'contributor',
        'role_key': 'right_angle_person',
        'title': '直角人',
        'color': 'guard',
    },
}


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def utc_now_dt():
    return datetime.now(timezone.utc).replace(microsecond=0)


def utc_iso(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def format_duration_zh(seconds):
    try:
        value = max(0, int(seconds))
    except (TypeError, ValueError):
        value = 0
    days, rem = divmod(value, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days:
        return f'{days}天{hours}小时'
    if hours:
        return f'{hours}小时{minutes}分钟'
    if minutes:
        return f'{minutes}分钟{secs}秒'
    return f'{secs}秒'


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


def _role_defaults(role_type):
    normalized = str(role_type or '').strip().lower()
    return dict(ROLE_DEFAULTS.get(normalized) or ROLE_DEFAULTS['contributor'])


def _normalize_role_color(value, fallback='neutral'):
    text = str(value or '').strip().lower()
    if text in ROLE_COLOR_TOKENS:
        return text
    if re.fullmatch(r'#[0-9a-fA-F]{6}', text):
        return text
    return fallback


def _normalize_role_type(value):
    text = str(value or '').strip().lower()
    return text if text in ROLE_TYPES else ''


def _builtin_role_for_username(username):
    return BUILTIN_USER_ROLES.get(normalize_username_key(username))


def _ensure_builtin_role_for_row(conn, row):
    if row is None:
        return
    builtin = _builtin_role_for_username(row['username'])
    if not builtin:
        return
    existing = conn.execute('SELECT user_id FROM user_roles WHERE user_id = ?', (row['id'],)).fetchone()
    if existing is not None:
        return
    now = utc_now()
    conn.execute(
        '''
        INSERT INTO user_roles (
            user_id, role_type, role_key, title, color, sort_order,
            can_direct_friend, chat_exempt, visible, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        ''',
        (
            row['id'],
            builtin.get('role_type'),
            builtin.get('role_key'),
            builtin.get('title'),
            builtin.get('color'),
            int(builtin.get('sort_order', 99)),
            1 if builtin.get('can_direct_friend') else 0,
            1 if builtin.get('chat_exempt') else 0,
            now,
            now,
        ),
    )


def _seed_builtin_user_roles(conn):
    rows = conn.execute('SELECT * FROM users').fetchall()
    for row in rows:
        _ensure_builtin_role_for_row(conn, row)


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
        if 'ban_until' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN ban_until TEXT')
        if 'player_id' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN player_id TEXT')
        if 'accept_friend_requests' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN accept_friend_requests INTEGER DEFAULT 1')
        if 'searchable_by_nickname' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN searchable_by_nickname INTEGER DEFAULT 1')
        if 'searchable_by_player_id' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN searchable_by_player_id INTEGER DEFAULT 1')
        if 'false_report_count' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN false_report_count INTEGER DEFAULT 0')
        _assign_missing_player_ids(conn)
        conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_player_id ON users(player_id)')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id INTEGER PRIMARY KEY,
                role_type TEXT NOT NULL,
                role_key TEXT,
                title TEXT,
                color TEXT,
                sort_order INTEGER DEFAULT 99,
                can_direct_friend INTEGER DEFAULT 0,
                chat_exempt INTEGER DEFAULT 0,
                visible INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_user_roles_type_sort ON user_roles(role_type, sort_order)')
        _seed_builtin_user_roles(conn)
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
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_user_id INTEGER NOT NULL,
                reporter_username TEXT NOT NULL,
                target_user_id INTEGER,
                target_username TEXT,
                object_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                category TEXT NOT NULL,
                reason_text TEXT,
                status TEXT DEFAULT 'pending',
                risk_level INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                resolved_by TEXT,
                resolution_note TEXT,
                FOREIGN KEY(reporter_user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_reports_status_created ON reports(status, created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_reports_reporter_created ON reports(reporter_user_id, created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_reports_object ON reports(object_type, object_id, category, created_at)')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS report_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                evidence_type TEXT NOT NULL,
                data_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_report_evidence_report ON report_evidence(report_id)')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS moderation_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_username TEXT,
                target_user_id INTEGER,
                target_username TEXT,
                action_type TEXT NOT NULL,
                reason TEXT,
                duration_seconds INTEGER,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                related_report_id INTEGER,
                FOREIGN KEY(target_user_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY(related_report_id) REFERENCES reports(id) ON DELETE SET NULL
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_moderation_actions_target ON moderation_actions(target_user_id, created_at)')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id TEXT,
                channel TEXT,
                sender_user_id INTEGER,
                sender_name TEXT,
                message TEXT NOT NULL,
                normalized_message TEXT,
                risk_level INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                hidden INTEGER DEFAULT 0
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_created ON chat_messages(created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_room ON chat_messages(room_id, created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_sender ON chat_messages(sender_user_id, created_at)')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS muted_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                muted_until TEXT,
                reason TEXT,
                created_at TEXT NOT NULL,
                muted_by TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_muted_users_until ON muted_users(muted_until)')
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
    if len(text) < 8:
        return False, '密码至少需要 8 位'
    if len(text) > 72:
        return False, '密码最多 72 位'
    if any(ord(ch) < 33 or ord(ch) > 126 for ch in text):
        return False, '密码只能使用可见 ASCII 字符，且不能包含空格'
    classes = 0
    classes += 1 if re.search(r'[0-9]', text) else 0
    classes += 1 if re.search(r'[A-Z]', text) else 0
    classes += 1 if re.search(r'[a-z]', text) else 0
    classes += 1 if re.search(r'[^0-9A-Za-z]', text) else 0
    if classes < 2:
        return False, '密码需包含数字、大写字母、小写字母、特殊符号中的任意两类'
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
        'false_report_count': int(row['false_report_count'] or 0) if 'false_report_count' in row.keys() else 0,
        'banned': bool(row['banned']) if 'banned' in row.keys() else False,
        'ban_reason': row['ban_reason'] if 'ban_reason' in row.keys() else None,
        'banned_at': row['banned_at'] if 'banned_at' in row.keys() else None,
        'ban_until': row['ban_until'] if 'ban_until' in row.keys() else None,
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
            row = conn.execute('SELECT * FROM users WHERE id = ?', (cur.lastrowid,)).fetchone()
            _ensure_builtin_role_for_row(conn, row)
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
        row = _clear_expired_user_ban(conn, row)
        ban_status = get_user_ban_status(user_id=row['id'])
        if ban_status.get('banned'):
            reason = ban_status.get('reason') or ''
            remaining = ban_status.get('remaining_seconds')
            if remaining is None:
                suffix = '永久'
            else:
                suffix = f'剩余{format_duration_zh(remaining)}'
            return None, f'账号已被封禁（{suffix}）：{reason}' if reason else f'账号已被封禁（{suffix}）'
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


def admin_set_user_ban(identifier, banned=True, reason='', duration_seconds=None):
    user = find_user_for_admin(identifier)
    if not user:
        return None, '账号不存在'
    reason_text = str(reason or '').strip()[:200]
    banned_at = utc_now() if banned else None
    ban_until = None
    if banned and duration_seconds is not None:
        try:
            duration = int(duration_seconds)
        except (TypeError, ValueError):
            duration = 0
        if duration > 0:
            duration = min(duration, 60 * 60 * 24 * 365)
            ban_until = utc_iso(utc_now_dt() + timedelta(seconds=duration))
    with get_db_connection() as conn:
        conn.execute(
            '''
            UPDATE users
            SET banned = ?, ban_reason = ?, banned_at = ?, ban_until = ?
            WHERE id = ?
            ''',
            (1 if banned else 0, reason_text if banned else None, banned_at, ban_until if banned else None, user['id']),
        )
        conn.commit()
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()
        return row_to_user(row), None


def _parse_utc(value):
    text = str(value or '')
    if not text:
        return None
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _remaining_seconds_until(value):
    until_dt = _parse_utc(value)
    if until_dt is None:
        return None
    return max(0, int((until_dt - utc_now_dt()).total_seconds()))


def _clear_expired_user_ban(conn, row):
    if row is None:
        return None
    is_banned = bool(row['banned']) if 'banned' in row.keys() else False
    if not is_banned:
        return row
    ban_until = row['ban_until'] if 'ban_until' in row.keys() else None
    until_dt = _parse_utc(ban_until)
    if until_dt is not None and until_dt <= utc_now_dt():
        conn.execute(
            'UPDATE users SET banned = 0, ban_reason = NULL, banned_at = NULL, ban_until = NULL WHERE id = ?',
            (row['id'],),
        )
        conn.commit()
        return conn.execute('SELECT * FROM users WHERE id = ?', (row['id'],)).fetchone()
    return row


def get_user_ban_status(user_id=None, username=None):
    with get_db_connection() as conn:
        row = None
        if user_id is not None:
            try:
                uid = int(user_id)
                row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
            except (TypeError, ValueError):
                row = None
        if row is None and username:
            row = _find_user_row_by_username_key(conn, username)
        row = _clear_expired_user_ban(conn, row)
        if row is None:
            return {'banned': False}
        is_banned = bool(row['banned']) if 'banned' in row.keys() else False
        if not is_banned:
            return {'banned': False, 'user': row_to_user(row)}
        ban_until = row['ban_until'] if 'ban_until' in row.keys() else None
        remaining = _remaining_seconds_until(ban_until)
        return {
            'banned': True,
            'user': row_to_user(row),
            'reason': (row['ban_reason'] if 'ban_reason' in row.keys() else '') or '',
            'ban_until': ban_until,
            'remaining_seconds': remaining,
            'permanent': remaining is None,
        }


def record_chat_message(room_id, channel, sender_user_id, sender_name, message, normalized_message='', risk_level=0, hidden=False):
    now = utc_now()
    try:
        uid = int(sender_user_id) if sender_user_id is not None else None
    except (TypeError, ValueError):
        uid = None
    with get_db_connection() as conn:
        cur = conn.execute(
            '''
            INSERT INTO chat_messages (
                room_id, channel, sender_user_id, sender_name, message,
                normalized_message, risk_level, created_at, hidden
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                str(room_id) if room_id is not None else None,
                str(channel or 'public')[:40],
                uid,
                str(sender_name or '')[:80],
                str(message or '')[:1000],
                str(normalized_message or '')[:1000],
                int(risk_level or 0),
                now,
                1 if hidden else 0,
            ),
        )
        conn.commit()
        return cur.lastrowid


def _row_to_chat_message(row):
    if row is None:
        return None
    return {
        'id': row['id'],
        'room_id': row['room_id'],
        'channel': row['channel'],
        'sender_user_id': row['sender_user_id'],
        'sender_name': row['sender_name'],
        'message': row['message'],
        'normalized_message': row['normalized_message'],
        'risk_level': row['risk_level'],
        'created_at': row['created_at'],
        'hidden': bool(row['hidden']),
    }


def get_chat_message_with_context(message_id, context_limit=8):
    try:
        mid = int(message_id)
    except (TypeError, ValueError):
        return None
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM chat_messages WHERE id = ?', (mid,)).fetchone()
        if row is None:
            return None
        room_id = row['room_id']
        created_at = row['created_at']
        if room_id:
            before = conn.execute(
                '''
                SELECT * FROM chat_messages
                WHERE room_id = ? AND created_at <= ?
                ORDER BY created_at DESC
                LIMIT ?
                ''',
                (room_id, created_at, max(1, int(context_limit))),
            ).fetchall()
            after = conn.execute(
                '''
                SELECT * FROM chat_messages
                WHERE room_id = ? AND created_at > ?
                ORDER BY created_at ASC
                LIMIT ?
                ''',
                (room_id, created_at, max(1, int(context_limit // 2))),
            ).fetchall()
        else:
            before = [row]
            after = []
        items = [_row_to_chat_message(item) for item in reversed(before)] + [_row_to_chat_message(item) for item in after]
        return {'message': _row_to_chat_message(row), 'context': items}


def set_user_mute(user_id, username='', seconds=600, reason='', muted_by=''):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None, '账号不存在'
    duration = max(1, min(int(seconds or 600), 60 * 60 * 24 * 30))
    now_dt = utc_now_dt()
    until = utc_iso(now_dt + timedelta(seconds=duration))
    now = utc_iso(now_dt)
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if row is None:
            return None, '账号不存在'
        conn.execute(
            '''
            INSERT INTO muted_users (user_id, username, muted_until, reason, created_at, muted_by)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                muted_until=excluded.muted_until,
                reason=excluded.reason,
                created_at=excluded.created_at,
                muted_by=excluded.muted_by
            ''',
            (uid, str(username or row['username']), until, str(reason or '')[:300], now, str(muted_by or '')[:80]),
        )
        conn.commit()
        return {'user_id': uid, 'username': str(username or row['username']), 'muted_until': until}, None


def is_user_muted_db(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return False, None
    now = utc_now()
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM muted_users WHERE user_id = ?', (uid,)).fetchone()
        if row is None:
            return False, None
        until_dt = _parse_utc(row['muted_until'])
        if until_dt is None or until_dt <= utc_now_dt():
            conn.execute('DELETE FROM muted_users WHERE user_id = ?', (uid,))
            conn.commit()
            return False, None
        return True, {
            'user_id': uid,
            'username': row['username'],
            'muted_until': row['muted_until'],
            'reason': row['reason'],
            'muted_by': row['muted_by'],
            'checked_at': now,
        }


def _row_to_report(row):
    if row is None:
        return None
    return {
        'id': row['id'],
        'reporter_user_id': row['reporter_user_id'],
        'reporter_username': row['reporter_username'],
        'target_user_id': row['target_user_id'],
        'target_username': row['target_username'],
        'object_type': row['object_type'],
        'object_id': row['object_id'],
        'category': row['category'],
        'reason_text': row['reason_text'],
        'status': row['status'],
        'risk_level': row['risk_level'],
        'created_at': row['created_at'],
        'resolved_at': row['resolved_at'],
        'resolved_by': row['resolved_by'],
        'resolution_note': row['resolution_note'],
    }


def create_report_entry(
    reporter_user_id,
    object_type,
    object_id,
    category,
    reason_text='',
    target_user_id=None,
    target_username='',
    risk_level=0,
    evidence=None,
):
    try:
        reporter_id = int(reporter_user_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    now_dt = utc_now_dt()
    now = utc_iso(now_dt)
    ten_min_ago = utc_iso(now_dt - timedelta(minutes=10))
    day_ago = utc_iso(now_dt - timedelta(hours=24))
    object_type = str(object_type or '').strip()[:40]
    object_id = str(object_id or '').strip()[:120]
    category = str(category or '').strip()[:60]
    reason = str(reason_text or '').strip()[:300]
    if not object_type or not object_id or not category:
        return None, '举报对象不完整'
    try:
        target_id = int(target_user_id) if target_user_id not in (None, '') else None
    except (TypeError, ValueError):
        target_id = None
    with get_db_connection() as conn:
        reporter = conn.execute('SELECT * FROM users WHERE id = ?', (reporter_id,)).fetchone()
        if reporter is None:
            return None, '请先登录账号'
        if int(reporter['false_report_count'] or 0) >= 10:
            return None, '举报功能已被限制，请联系管理员'
        recent_10m = conn.execute(
            'SELECT COUNT(*) FROM reports WHERE reporter_user_id = ? AND created_at >= ?',
            (reporter_id, ten_min_ago),
        ).fetchone()[0]
        if recent_10m >= 5:
            return None, '举报过于频繁，请稍后再试'
        recent_day = conn.execute(
            'SELECT COUNT(*) FROM reports WHERE reporter_user_id = ? AND created_at >= ?',
            (reporter_id, day_ago),
        ).fetchone()[0]
        if recent_day >= 30:
            return None, '今日举报次数已达上限'
        duplicate = conn.execute(
            '''
            SELECT id FROM reports
            WHERE reporter_user_id = ? AND object_type = ? AND object_id = ? AND category = ? AND created_at >= ?
            LIMIT 1
            ''',
            (reporter_id, object_type, object_id, category, day_ago),
        ).fetchone()
        if duplicate is not None:
            return None, '24小时内不能重复举报同一对象'
        cur = conn.execute(
            '''
            INSERT INTO reports (
                reporter_user_id, reporter_username, target_user_id, target_username,
                object_type, object_id, category, reason_text, status, risk_level, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            ''',
            (
                reporter_id,
                reporter['username'],
                target_id,
                str(target_username or '')[:80],
                object_type,
                object_id,
                category,
                reason,
                int(risk_level or 0),
                now,
            ),
        )
        report_id = cur.lastrowid
        for item in evidence or []:
            if not isinstance(item, dict):
                continue
            conn.execute(
                'INSERT INTO report_evidence (report_id, evidence_type, data_json, created_at) VALUES (?, ?, ?, ?)',
                (
                    report_id,
                    str(item.get('evidence_type') or item.get('type') or 'context')[:60],
                    json.dumps(item.get('data') if 'data' in item else item, ensure_ascii=False),
                    now,
                ),
            )
        conn.commit()
        row = conn.execute('SELECT * FROM reports WHERE id = ?', (report_id,)).fetchone()
        return _row_to_report(row), None


def list_reports(status='pending', limit=50, offset=0):
    limit = max(1, min(int(limit or 50), 100))
    offset = max(0, int(offset or 0))
    status_text = str(status or 'pending').strip().lower()
    where = ''
    params = []
    if status_text and status_text != 'all':
        where = 'WHERE status = ?'
        params.append(status_text)
    with get_db_connection() as conn:
        total = conn.execute(f'SELECT COUNT(*) FROM reports {where}', params).fetchone()[0]
        rows = conn.execute(
            f'SELECT * FROM reports {where} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?',
            params + [limit, offset],
        ).fetchall()
        return {
            'items': [_row_to_report(row) for row in rows],
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + len(rows) < total,
        }


def get_report_detail(report_id):
    try:
        rid = int(report_id)
    except (TypeError, ValueError):
        return None
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM reports WHERE id = ?', (rid,)).fetchone()
        if row is None:
            return None
        evidence_rows = conn.execute('SELECT * FROM report_evidence WHERE report_id = ? ORDER BY id ASC', (rid,)).fetchall()
        actions = conn.execute('SELECT * FROM moderation_actions WHERE related_report_id = ? ORDER BY id ASC', (rid,)).fetchall()
        reporter_stats = conn.execute(
            '''
            SELECT
                SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) AS accepted_count,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected_count,
                SUM(CASE WHEN status = 'abusive' THEN 1 ELSE 0 END) AS abusive_count
            FROM reports WHERE reporter_user_id = ?
            ''',
            (row['reporter_user_id'],),
        ).fetchone()
        data = _row_to_report(row)
        data['evidence'] = [
            {
                'id': ev['id'],
                'evidence_type': ev['evidence_type'],
                'data': json.loads(ev['data_json'] or '{}'),
                'created_at': ev['created_at'],
            }
            for ev in evidence_rows
        ]
        data['actions'] = [
            {
                'id': action['id'],
                'admin_username': action['admin_username'],
                'target_user_id': action['target_user_id'],
                'target_username': action['target_username'],
                'action_type': action['action_type'],
                'reason': action['reason'],
                'duration_seconds': action['duration_seconds'],
                'created_at': action['created_at'],
                'expires_at': action['expires_at'],
            }
            for action in actions
        ]
        data['reporter_history'] = {
            'accepted': int(reporter_stats['accepted_count'] or 0),
            'rejected': int(reporter_stats['rejected_count'] or 0),
            'abusive': int(reporter_stats['abusive_count'] or 0),
        }
        return data


def resolve_report_entry(report_id, action, moderation_action='none', admin_username='', note='', duration_seconds=None):
    try:
        rid = int(report_id)
    except (TypeError, ValueError):
        return None, '举报不存在'
    action = str(action or '').strip().lower()
    moderation_action = str(moderation_action or 'none').strip().lower()
    status_map = {'accept': 'accepted', 'reject': 'rejected', 'abusive': 'abusive'}
    if action not in status_map:
        return None, '处理动作无效'
    if moderation_action not in {'none', 'warn', 'mute', 'ban', 'invalidate_match'}:
        return None, '处罚动作无效'
    now_dt = utc_now_dt()
    now = utc_iso(now_dt)
    duration = int(duration_seconds or 0) if duration_seconds is not None else None
    expires_at = utc_iso(now_dt + timedelta(seconds=max(1, duration))) if duration and moderation_action == 'mute' else None
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM reports WHERE id = ?', (rid,)).fetchone()
        if row is None:
            return None, '举报不存在'
        conn.execute(
            '''
            UPDATE reports
            SET status = ?, resolved_at = ?, resolved_by = ?, resolution_note = ?
            WHERE id = ?
            ''',
            (status_map[action], now, str(admin_username or '')[:80], str(note or '')[:500], rid),
        )
        if action == 'abusive':
            conn.execute(
                'UPDATE users SET false_report_count = COALESCE(false_report_count, 0) + 1 WHERE id = ?',
                (row['reporter_user_id'],),
            )
        if moderation_action != 'none':
            conn.execute(
                '''
                INSERT INTO moderation_actions (
                    admin_username, target_user_id, target_username, action_type,
                    reason, duration_seconds, created_at, expires_at, related_report_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    str(admin_username or '')[:80],
                    row['target_user_id'],
                    row['target_username'],
                    moderation_action,
                    str(note or '')[:500],
                    duration,
                    now,
                    expires_at,
                    rid,
                ),
            )
        conn.commit()
    return get_report_detail(rid), None


def _role_row_to_profile(user_row, role_row):
    if user_row is None or role_row is None:
        return None
    role_type = str(role_row['role_type'] or '').strip().lower()
    if role_type == 'none' or not bool(role_row['visible']):
        return None
    defaults = _role_defaults(role_type)
    role_key = str(role_row['role_key'] or defaults.get('role_key') or role_type).strip()
    title = str(role_row['title'] or defaults.get('title') or '').strip()
    color = _normalize_role_color(role_row['color'], defaults.get('color') or 'neutral')
    is_admin = role_type == 'admin'
    return {
        'user_id': user_row['id'],
        'display_name': user_row['username'],
        'role_type': role_type,
        'special_role': role_key or role_type,
        'special_role_label': title,
        'special_role_color': color,
        'special_role_sort': int(role_row['sort_order'] if role_row['sort_order'] is not None else defaults.get('sort_order', 99)),
        'is_admin_player': is_admin,
        'can_direct_friend': bool(role_row['can_direct_friend']),
        'chat_exempt': bool(role_row['chat_exempt']),
    }


def get_user_role_profile(identifier):
    token = str(identifier or '').strip()
    if not token:
        return None
    with get_db_connection() as conn:
        user_row = None
        if isinstance(identifier, int) or token.isdigit():
            user_row = conn.execute('SELECT * FROM users WHERE id = ?', (int(token),)).fetchone()
        if user_row is None:
            user_row = _find_user_row_by_username_key(conn, token)
        if user_row is None:
            return None
        _ensure_builtin_role_for_row(conn, user_row)
        conn.commit()
        role_row = conn.execute('SELECT * FROM user_roles WHERE user_id = ?', (user_row['id'],)).fetchone()
        return _role_row_to_profile(user_row, role_row)


def user_role_can_direct_friend(user_row_or_id):
    with get_db_connection() as conn:
        if isinstance(user_row_or_id, sqlite3.Row):
            user_row = user_row_or_id
        else:
            try:
                uid = int(user_row_or_id)
            except (TypeError, ValueError):
                return False
            user_row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if user_row is None:
            return False
        _ensure_builtin_role_for_row(conn, user_row)
        conn.commit()
        role_row = conn.execute('SELECT * FROM user_roles WHERE user_id = ?', (user_row['id'],)).fetchone()
        profile = _role_row_to_profile(user_row, role_row)
        return bool(profile and profile.get('can_direct_friend'))


def list_user_roles(query='', limit=100):
    try:
        safe_limit = max(1, min(int(limit), 300))
    except (TypeError, ValueError):
        safe_limit = 100
    name = sanitize_username(query)
    where = 'WHERE r.role_type <> ?'
    params = ['none']
    if name:
        where += ' AND (u.username_lower LIKE ? OR u.player_id LIKE ? OR r.role_type LIKE ? OR r.title LIKE ?)'
        params.extend([f'%{name.lower()}%', f'%{str(query or "").strip().upper()}%', f'%{name.lower()}%', f'%{name}%'])
    with get_db_connection() as conn:
        _seed_builtin_user_roles(conn)
        conn.commit()
        rows = conn.execute(
            f'''
            SELECT u.*, r.role_type, r.role_key, r.title, r.color, r.sort_order,
                   r.can_direct_friend, r.chat_exempt, r.visible
            FROM user_roles r
            JOIN users u ON u.id = r.user_id
            {where}
            ORDER BY r.sort_order ASC, u.username_lower ASC
            LIMIT ?
            ''',
            params + [safe_limit],
        ).fetchall()
        result = []
        for row in rows:
            if not bool(row['visible']):
                continue
            result.append({
                'user_id': row['id'],
                'username': row['username'],
                'player_id': row['player_id'],
                'role_type': row['role_type'],
                'role_key': row['role_key'],
                'title': row['title'],
                'color': row['color'],
                'sort_order': row['sort_order'],
                'can_direct_friend': bool(row['can_direct_friend']),
                'chat_exempt': bool(row['chat_exempt']),
            })
        return result


def admin_set_user_role(identifier, role_type, title='', color='', sort_order=None, role_key='', can_direct_friend=None, chat_exempt=None, visible=True):
    user = find_user_for_admin(identifier)
    if not user:
        return None, None, '账号不存在'
    normalized_type = _normalize_role_type(role_type)
    if not normalized_type:
        return None, None, '身份类型必须是 admin/staff/contributor/sponsor/none'
    user_key = normalize_username_key(user['username'])
    if normalized_type == 'admin' and user_key != 'stickerbug':
        return None, None, '管理员身份只能授予 Stickerbug'
    if user_key == 'stickerbug' and normalized_type != 'admin':
        return None, None, 'Stickerbug 必须保持管理员身份'
    defaults = _role_defaults(normalized_type)
    title_text = str(title or defaults.get('title') or '').strip()[:32]
    role_key_text = str(role_key or defaults.get('role_key') or normalized_type).strip()[:40]
    color_text = _normalize_role_color(color, defaults.get('color') or 'neutral')
    if sort_order is None:
        order_value = int(defaults.get('sort_order', 99))
    else:
        try:
            order_value = max(0, min(int(sort_order), 99))
        except (TypeError, ValueError):
            return None, None, 'sort 必须是 0-99 的整数'
    direct = defaults.get('can_direct_friend') if can_direct_friend is None else bool(can_direct_friend)
    chat = defaults.get('chat_exempt') if chat_exempt is None else bool(chat_exempt)
    if normalized_type == 'admin':
        direct = True
        chat = True
        order_value = 0
    if normalized_type == 'staff':
        direct = True
        chat = True
        order_value = min(order_value, 1)
    now = utc_now()
    with get_db_connection() as conn:
        conn.execute(
            '''
            INSERT INTO user_roles (
                user_id, role_type, role_key, title, color, sort_order,
                can_direct_friend, chat_exempt, visible, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                role_type = excluded.role_type,
                role_key = excluded.role_key,
                title = excluded.title,
                color = excluded.color,
                sort_order = excluded.sort_order,
                can_direct_friend = excluded.can_direct_friend,
                chat_exempt = excluded.chat_exempt,
                visible = excluded.visible,
                updated_at = excluded.updated_at
            ''',
            (
                user['id'],
                normalized_type,
                role_key_text,
                title_text,
                color_text,
                order_value,
                1 if direct else 0,
                1 if chat else 0,
                1 if visible and normalized_type != 'none' else 0,
                now,
                now,
            ),
        )
        conn.commit()
        user_row = conn.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()
        role_row = conn.execute('SELECT * FROM user_roles WHERE user_id = ?', (user['id'],)).fetchone()
        return row_to_user(user_row), _role_row_to_profile(user_row, role_row), None


def admin_clear_user_role(identifier):
    user = find_user_for_admin(identifier)
    if not user:
        return None, '账号不存在'
    if normalize_username_key(user['username']) == 'stickerbug':
        return None, '不能清除 Stickerbug 的管理员身份'
    _, _, error = admin_set_user_role(user['id'], 'none', title='', color='neutral', sort_order=99, role_key='none', can_direct_friend=False, chat_exempt=False, visible=False)
    if error:
        return None, error
    return user, None


def get_user_by_id(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        row = _clear_expired_user_ban(conn, row)
        return row_to_user(row)


def get_user_by_username(username):
    name = sanitize_username(username)
    if not name:
        return None
    with get_db_connection() as conn:
        row = _find_user_row_by_username_key(conn, name)
        row = _clear_expired_user_ban(conn, row)
        return row_to_user(row)


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


def _safe_json_loads(value, fallback):
    try:
        return json.loads(value or '')
    except Exception:
        return fallback


def _match_winner_keys(row, player_names, summary):
    winner_keys = set()
    winner_name = str(row['winner_name'] or '').strip()
    if winner_name and normalize_username_key(winner_name) not in {'draw', '平局'}:
        if not re.search(r'\s*/\s*|\s*,\s*', winner_name):
            winner_keys.add(normalize_username_key(winner_name))
        for part in re.split(r'\s*/\s*|\s*,\s*', winner_name):
            part_key = normalize_username_key(part)
            if part_key and part_key not in {'draw', '平局'}:
                winner_keys.add(part_key)
    try:
        winner_index = int(row['winner_index']) if row['winner_index'] is not None else None
    except (TypeError, ValueError):
        winner_index = None
    mode = str(row['mode'] or summary.get('mode') or '').lower()
    if winner_index is not None and winner_index >= 0:
        if mode == '2v2':
            for idx in ({0: [0, 1], 1: [2, 3]}.get(winner_index, [])):
                if 0 <= idx < len(player_names):
                    key = normalize_username_key(player_names[idx])
                    if key:
                        winner_keys.add(key)
        elif 0 <= winner_index < len(player_names):
            key = normalize_username_key(player_names[winner_index])
            if key:
                winner_keys.add(key)
    return winner_keys


def _match_result_for_username(row, username, player_names, summary):
    raw_result = str(row['result'] or '').strip()
    lower_result = raw_result.lower()
    winner_name_key = normalize_username_key(row['winner_name'] or '')
    try:
        winner_index = int(row['winner_index']) if row['winner_index'] is not None else None
    except (TypeError, ValueError):
        winner_index = None
    if lower_result == 'draw' or winner_name_key in {'draw', '平局'} or winner_index == -1:
        return 'draw'
    user_key = normalize_username_key(username)
    if not user_key:
        return raw_result
    participant_keys = {normalize_username_key(name) for name in (player_names or []) if normalize_username_key(name)}
    winner_keys = _match_winner_keys(row, player_names, summary)
    if winner_keys:
        return 'win' if user_key in winner_keys else 'loss'
    if user_key not in participant_keys:
        return raw_result
    return raw_result or 'finished'


def _row_to_match_summary(row, perspective_username=None):
    if row is None:
        return None
    player_names = _safe_json_loads(row['player_names_json'], [])
    summary = _safe_json_loads(row['summary_json'], {})
    raw_result = row['result']
    result = _match_result_for_username(row, perspective_username, player_names, summary) if perspective_username else raw_result
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
        'result': result,
        'result_raw': raw_result,
        'valid_for_ranking': bool(summary.get('valid_for_ranking', True)),
        'ranking_invalid_reason': summary.get('ranking_invalid_reason', ''),
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
        'role': get_user_role_profile(user['id']),
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


def _is_auto_friend_requester(row, conn=None):
    if row is None:
        return False
    if conn is not None:
        _ensure_builtin_role_for_row(conn, row)
        role_row = conn.execute('SELECT * FROM user_roles WHERE user_id = ?', (row['id'],)).fetchone()
        profile = _role_row_to_profile(row, role_row)
        return bool(profile and profile.get('can_direct_friend'))
    return user_role_can_direct_friend(row)


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
    return [_row_to_match_summary(row, perspective_username=username) for row in rows]


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
        auto_add = _is_auto_friend_requester(requester, conn)
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
