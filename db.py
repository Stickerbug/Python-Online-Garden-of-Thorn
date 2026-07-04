import json
import hashlib
import math
import os
import secrets
import re
import sqlite3
import time
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
DM_RETENTION_DAYS = 60
DM_THREAD_MAX_BYTES = 100 * 1024
RANKING_MIN_DURATION_SECONDS = int(os.environ.get('GTN_RANKING_MIN_DURATION_SECONDS', '20'))
RANKING_MIN_ACTIONS_PER_SIDE = int(os.environ.get('GTN_RANKING_MIN_ACTIONS_PER_SIDE', '1'))
GR_INITIAL = 1000
GR_SOFT_RESET_RATIO = 0.5
GR_SOFT_RESET_MIN = 850
GR_SOFT_RESET_MAX = 1250
GR_SEASON_MIN_GAMES = 8
GR_TOTAL_MIN_GAMES = 20
GR_2V2_FACTOR = 0.85
_DM_MARK_READ_LAST_AT = {}
AUTO_FRIEND_REQUESTER_NAMES = {'stickerbug', 'netherdog', 'eric'}
ROLE_TYPES = {'admin', 'staff', 'contributor', 'sponsor', 'none'}
ROLE_COLOR_TOKENS = {'admin', 'bloom', 'guard', 'thorn', 'root', 'neutral'}
DEFAULT_SKIN_CONFIG = {
    'primary_color': '#FFE763',
    'eye_shape': 'oval',
}
SKIN_EYE_SHAPES = {'oval', 'rectangle', 'diamond', 'hexagon'}
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


def current_week_start():
    today = datetime.now(timezone.utc).date()
    return (today - timedelta(days=today.weekday())).isoformat()


def current_gr_season(now=None):
    dt = now or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    year = dt.year
    month = dt.month
    season_id = 'S1' if year == 2026 and month == 7 else f'S{year}{month:02d}'
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return {
        'id': season_id,
        'name': season_id,
        'starts_at': utc_iso(start),
        'ends_at': utc_iso(end - timedelta(seconds=1)),
        'next_starts_at': utc_iso(end),
    }


def week_start_for_iso(value):
    try:
        text = str(value or '').strip()
        if not text:
            return current_week_start()
        dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
        return (dt.astimezone(timezone.utc).date() - timedelta(days=dt.astimezone(timezone.utc).weekday())).isoformat()
    except Exception:
        return current_week_start()


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


_FRIEND_CLEANUP_LAST_TS = 0.0
_FRIEND_CLEANUP_INTERVAL_SECONDS = 600


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON;')
    try:
        conn.execute('PRAGMA journal_mode=WAL;')
    except sqlite3.OperationalError:
        pass
    conn.execute('PRAGMA busy_timeout=5000;')
    conn.execute('PRAGMA synchronous=NORMAL;')
    conn.execute('PRAGMA temp_store=MEMORY;')
    return conn


def db_slow_log(endpoint='', elapsed_ms=0, sql_tag=''):
    try:
        elapsed = float(elapsed_ms or 0)
    except (TypeError, ValueError):
        elapsed = 0
    if elapsed < 500:
        return
    print(f'[db_slow] endpoint={endpoint or "-"} elapsed_ms={elapsed:.1f} sql_tag={sql_tag or "-"}', flush=True)


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
        if 'skin_json' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN skin_json TEXT')
        if 'last_username_change_at' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN last_username_change_at TEXT')
        if 'deleted_at' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN deleted_at TEXT')
        if 'online_seconds' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN online_seconds INTEGER DEFAULT 0')
        if 'online_session_started_at' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN online_session_started_at TEXT')
        if 'play_seconds' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN play_seconds INTEGER DEFAULT 0')
        if 'thorn_dew_free' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN thorn_dew_free INTEGER DEFAULT 0')
        if 'thorn_dew_paid' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN thorn_dew_paid INTEGER DEFAULT 0')
        if 'password_changed_at' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN password_changed_at TEXT')
        if 'total_gr' not in existing_columns:
            conn.execute(f'ALTER TABLE users ADD COLUMN total_gr REAL DEFAULT {GR_INITIAL}')
        if 'season_gr' not in existing_columns:
            conn.execute(f'ALTER TABLE users ADD COLUMN season_gr REAL DEFAULT {GR_INITIAL}')
        if 'highest_gr' not in existing_columns:
            conn.execute(f'ALTER TABLE users ADD COLUMN highest_gr REAL DEFAULT {GR_INITIAL}')
        if 'total_ranked_games' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN total_ranked_games INTEGER DEFAULT 0')
        if 'season_ranked_games' not in existing_columns:
            conn.execute('ALTER TABLE users ADD COLUMN season_ranked_games INTEGER DEFAULT 0')
        if 'gr_season_id' not in existing_columns:
            conn.execute("ALTER TABLE users ADD COLUMN gr_season_id TEXT DEFAULT 'S1'")
        _assign_missing_player_ids(conn)
        season = current_gr_season()
        conn.execute(
            '''
            UPDATE users
            SET total_gr = COALESCE(total_gr, ?),
                season_gr = COALESCE(season_gr, ?),
                highest_gr = MAX(COALESCE(highest_gr, ?), COALESCE(total_gr, ?), COALESCE(season_gr, ?)),
                total_ranked_games = COALESCE(total_ranked_games, 0),
                season_ranked_games = COALESCE(season_ranked_games, 0),
                gr_season_id = COALESCE(gr_season_id, ?)
            ''',
            (GR_INITIAL, GR_INITIAL, GR_INITIAL, GR_INITIAL, GR_INITIAL, season['id']),
        )
        conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_player_id ON users(player_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_users_stats ON users(games_played, wins, losses, draws)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_users_season_gr ON users(gr_season_id, season_gr, season_ranked_games)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_users_total_gr ON users(total_gr, total_ranked_games)')
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
            CREATE TABLE IF NOT EXISTS user_currency_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                currency TEXT NOT NULL,
                free_delta INTEGER NOT NULL DEFAULT 0,
                paid_delta INTEGER NOT NULL DEFAULT 0,
                reason TEXT,
                source_type TEXT,
                source_id TEXT,
                balance_free_after INTEGER NOT NULL DEFAULT 0,
                balance_paid_after INTEGER NOT NULL DEFAULT 0,
                admin_username TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_currency_tx_user ON user_currency_transactions(user_id, id DESC)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_currency_tx_created ON user_currency_transactions(created_at)')
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
        conn.execute('CREATE INDEX IF NOT EXISTS idx_friendships_updated ON friendships(updated_at)')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT,
                started_at TEXT,
                ended_at TEXT,
                duration_seconds INTEGER,
                player_names_json TEXT,
                player_ids_json TEXT,
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
            CREATE TABLE IF NOT EXISTS card_draft_win_stats (
                mode TEXT NOT NULL,
                card_id TEXT NOT NULL,
                picked_games INTEGER NOT NULL DEFAULT 0,
                win_games INTEGER NOT NULL DEFAULT 0,
                draw_games INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (mode, card_id)
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS gr_match_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                season_id TEXT NOT NULL,
                mode TEXT,
                played_at TEXT NOT NULL,
                participant_ids_json TEXT NOT NULL,
                team_a_ids_json TEXT NOT NULL,
                team_b_ids_json TEXT NOT NULL,
                winner_side INTEGER,
                is_draw INTEGER DEFAULT 0,
                repeat_count INTEGER DEFAULT 0,
                repeat_factor REAL DEFAULT 1.0,
                total_deltas_json TEXT NOT NULL,
                season_deltas_json TEXT NOT NULL,
                before_json TEXT NOT NULL,
                after_json TEXT NOT NULL
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_gr_match_results_played ON gr_match_results(played_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_gr_match_results_season ON gr_match_results(season_id, played_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_gr_match_results_match ON gr_match_results(match_id)')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS gr_daily_snapshots (
                snapshot_date TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                season_id TEXT NOT NULL,
                season_gr REAL NOT NULL,
                total_gr REAL NOT NULL,
                season_ranked_games INTEGER NOT NULL DEFAULT 0,
                total_ranked_games INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                PRIMARY KEY (snapshot_date, user_id)
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_gr_daily_snapshots_user ON gr_daily_snapshots(user_id, snapshot_date)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_card_draft_win_stats_mode ON card_draft_win_stats(mode)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_card_draft_win_stats_rate ON card_draft_win_stats(win_games, picked_games)')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS card_draft_stats_weekly (
                week_start TEXT NOT NULL,
                mode TEXT NOT NULL,
                card_id TEXT NOT NULL,
                shown_count INTEGER NOT NULL DEFAULT 0,
                picked_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (week_start, mode, card_id)
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_card_draft_stats_weekly_week_mode ON card_draft_stats_weekly(week_start, mode)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_card_draft_stats_weekly_rate ON card_draft_stats_weekly(week_start, picked_count, shown_count)')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS card_draft_win_stats_weekly (
                week_start TEXT NOT NULL,
                mode TEXT NOT NULL,
                card_id TEXT NOT NULL,
                picked_games INTEGER NOT NULL DEFAULT 0,
                win_games INTEGER NOT NULL DEFAULT 0,
                draw_games INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (week_start, mode, card_id)
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_card_draft_win_stats_weekly_week_mode ON card_draft_win_stats_weekly(week_start, mode)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_card_draft_win_stats_weekly_rate ON card_draft_win_stats_weekly(week_start, win_games, picked_games)')
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
            CREATE TABLE IF NOT EXISTS ip_bans (
                ip TEXT PRIMARY KEY,
                reason TEXT,
                created_at TEXT NOT NULL,
                banned_by TEXT,
                expires_at TEXT,
                active INTEGER DEFAULT 1
            )
            '''
        )
        match_columns = {row['name'] for row in conn.execute('PRAGMA table_info(matches)').fetchall()}
        if 'player_ids_json' not in match_columns:
            conn.execute('ALTER TABLE matches ADD COLUMN player_ids_json TEXT')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_matches_id_desc ON matches(id DESC)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_matches_started_at ON matches(started_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_matches_ended_at ON matches(ended_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ip_bans_active ON ip_bans(active, expires_at)')
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
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS dm_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_low_id INTEGER NOT NULL,
                user_high_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_low_id, user_high_id),
                FOREIGN KEY(user_low_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(user_high_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_dm_threads_low ON dm_threads(user_low_id, updated_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_dm_threads_high ON dm_threads(user_high_id, updated_at)')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS dm_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL,
                sender_user_id INTEGER NOT NULL,
                recipient_user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                normalized_message TEXT,
                risk_level INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                read_at TEXT,
                hidden INTEGER DEFAULT 0,
                FOREIGN KEY(thread_id) REFERENCES dm_threads(id) ON DELETE CASCADE,
                FOREIGN KEY(sender_user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(recipient_user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_dm_messages_thread ON dm_messages(thread_id, created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_dm_messages_recipient ON dm_messages(recipient_user_id, read_at, created_at)')
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
    width = _display_width(name)
    if width < 3:
        return False, '用户名可见宽度至少为3'
    if _display_width(name) > 16:
        return False, '用户名可见宽度最多为16'
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
        return False, '密码长度应至少为8个字符'
    if len(text) > 32:
        return False, '密码长度应最多为32个字符'
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


def normalize_skin_config(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            value = {}
    if not isinstance(value, dict):
        value = {}
    skin = dict(DEFAULT_SKIN_CONFIG)
    primary = str(value.get('primary_color') or value.get('primaryColor') or '').strip()
    if re.fullmatch(r'#[0-9A-Fa-f]{6}', primary):
        skin['primary_color'] = primary.upper()
    eye_shape = str(value.get('eye_shape') or value.get('eyeShape') or '').strip().lower()
    if eye_shape in SKIN_EYE_SHAPES:
        skin['eye_shape'] = eye_shape
    return skin


def row_to_user(row):
    if row is None:
        return None
    skin_raw = row['skin_json'] if 'skin_json' in row.keys() else None
    data = {
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
        'last_username_change_at': row['last_username_change_at'] if 'last_username_change_at' in row.keys() else None,
        'deleted_at': row['deleted_at'] if 'deleted_at' in row.keys() else None,
        'deleted': bool(row['deleted_at']) if 'deleted_at' in row.keys() else False,
        'online_seconds': int(row['online_seconds'] or 0) if 'online_seconds' in row.keys() else 0,
        'online_session_started_at': row['online_session_started_at'] if 'online_session_started_at' in row.keys() else None,
        'play_seconds': int(row['play_seconds'] or 0) if 'play_seconds' in row.keys() else 0,
        'thorn_dew_free': max(0, int(row['thorn_dew_free'] or 0)) if 'thorn_dew_free' in row.keys() else 0,
        'thorn_dew_paid': max(0, int(row['thorn_dew_paid'] or 0)) if 'thorn_dew_paid' in row.keys() else 0,
        'password_changed_at': row['password_changed_at'] if 'password_changed_at' in row.keys() else None,
        'skin': normalize_skin_config(skin_raw),
        'total_gr': round(float(row['total_gr'] or GR_INITIAL), 1) if 'total_gr' in row.keys() else float(GR_INITIAL),
        'season_gr': round(float(row['season_gr'] or GR_INITIAL), 1) if 'season_gr' in row.keys() else float(GR_INITIAL),
        'highest_gr': round(float(row['highest_gr'] or GR_INITIAL), 1) if 'highest_gr' in row.keys() else float(GR_INITIAL),
        'total_ranked_games': int(row['total_ranked_games'] or 0) if 'total_ranked_games' in row.keys() else 0,
        'season_ranked_games': int(row['season_ranked_games'] or 0) if 'season_ranked_games' in row.keys() else 0,
        'gr_season_id': row['gr_season_id'] if 'gr_season_id' in row.keys() else current_gr_season()['id'],
    }
    data['thorn_dew_total'] = data['thorn_dew_free'] + data['thorn_dew_paid']
    return data


def row_to_admin_user(row):
    user = row_to_user(row)
    if user is None:
        return None
    games = int(user.get('games_played') or 0)
    wins = int(user.get('wins') or 0)
    user['win_rate'] = round(wins / games * 100, 1) if games else 0.0
    return user


def _thorn_dew_payload(row_or_user):
    if row_or_user is None:
        return {'free': 0, 'paid': 0, 'total': 0}
    getter = row_or_user.get if isinstance(row_or_user, dict) else row_or_user.__getitem__
    try:
        free = max(0, int(getter('thorn_dew_free') or 0))
    except Exception:
        free = 0
    try:
        paid = max(0, int(getter('thorn_dew_paid') or 0))
    except Exception:
        paid = 0
    return {'free': free, 'paid': paid, 'total': free + paid}


def get_user_thorn_dew(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return _thorn_dew_payload(None)
    with get_db_connection() as conn:
        row = conn.execute('SELECT thorn_dew_free, thorn_dew_paid FROM users WHERE id = ?', (uid,)).fetchone()
        return _thorn_dew_payload(row)


def adjust_user_thorn_dew(user_id, free_delta=0, paid_delta=0, reason='', source_type='admin', source_id='', admin_username=''):
    try:
        uid = int(user_id)
        free_delta = int(free_delta or 0)
        paid_delta = int(paid_delta or 0)
    except (TypeError, ValueError):
        return None, '参数无效'
    if free_delta == 0 and paid_delta == 0:
        return None, '调整数量不能为0'
    now = utc_now()
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if row is None:
            return None, '账号不存在'
        free_before = max(0, int(row['thorn_dew_free'] or 0)) if 'thorn_dew_free' in row.keys() else 0
        paid_before = max(0, int(row['thorn_dew_paid'] or 0)) if 'thorn_dew_paid' in row.keys() else 0
        free_after = free_before + free_delta
        paid_after = paid_before + paid_delta
        if free_after < 0 or paid_after < 0:
            return None, '余额不足'
        conn.execute(
            'UPDATE users SET thorn_dew_free = ?, thorn_dew_paid = ? WHERE id = ?',
            (free_after, paid_after, uid),
        )
        conn.execute(
            '''
            INSERT INTO user_currency_transactions (
                user_id, currency, free_delta, paid_delta, reason, source_type, source_id,
                balance_free_after, balance_paid_after, admin_username, created_at
            )
            VALUES (?, 'thorn_dew', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                uid,
                free_delta,
                paid_delta,
                str(reason or '')[:300],
                str(source_type or '')[:80],
                str(source_id or '')[:120],
                free_after,
                paid_after,
                str(admin_username or '')[:80],
                now,
            ),
        )
        conn.commit()
        row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        return row_to_user(row), None


def spend_user_thorn_dew(user_id, amount, reason='', source_type='spend', source_id='', admin_username=''):
    try:
        amount = int(amount or 0)
    except (TypeError, ValueError):
        return None, '数量无效'
    if amount <= 0:
        return None, '数量必须大于0'
    balance = get_user_thorn_dew(user_id)
    if balance['total'] < amount:
        return None, '荆露不足'
    free_spent = min(balance['free'], amount)
    paid_spent = amount - free_spent
    return adjust_user_thorn_dew(
        user_id,
        free_delta=-free_spent,
        paid_delta=-paid_spent,
        reason=reason,
        source_type=source_type,
        source_id=source_id,
        admin_username=admin_username,
    )


def list_user_thorn_dew_transactions(user_id, limit=30):
    try:
        uid = int(user_id)
        safe_limit = max(1, min(int(limit or 30), 100))
    except (TypeError, ValueError):
        return []
    with get_db_connection() as conn:
        rows = conn.execute(
            '''
            SELECT * FROM user_currency_transactions
            WHERE user_id = ? AND currency = 'thorn_dew'
            ORDER BY id DESC
            LIMIT ?
            ''',
            (uid, safe_limit),
        ).fetchall()
        return [
            {
                'id': row['id'],
                'free_delta': row['free_delta'],
                'paid_delta': row['paid_delta'],
                'reason': row['reason'],
                'source_type': row['source_type'],
                'source_id': row['source_id'],
                'balance_free_after': row['balance_free_after'],
                'balance_paid_after': row['balance_paid_after'],
                'balance_total_after': int(row['balance_free_after'] or 0) + int(row['balance_paid_after'] or 0),
                'admin_username': row['admin_username'],
                'created_at': row['created_at'],
            }
            for row in rows
        ]


def _soft_reset_gr(value):
    try:
        old_value = float(value)
    except (TypeError, ValueError):
        old_value = float(GR_INITIAL)
    reset = GR_INITIAL + (old_value - GR_INITIAL) * GR_SOFT_RESET_RATIO
    return max(GR_SOFT_RESET_MIN, min(GR_SOFT_RESET_MAX, reset))


def ensure_current_gr_season_for_conn(conn, user_ids=None):
    season = current_gr_season()
    params = []
    where = ''
    if user_ids:
        safe_ids = []
        for value in user_ids:
            try:
                safe_ids.append(int(value))
            except (TypeError, ValueError):
                pass
        if safe_ids:
            where = f"WHERE id IN ({','.join(['?'] * len(safe_ids))})"
            params = safe_ids
    rows = conn.execute(
        f'''
        SELECT id, season_gr, gr_season_id
        FROM users
        {where}
        ''',
        params,
    ).fetchall()
    now = utc_now()
    for row in rows:
        if str(row['gr_season_id'] or '') == season['id']:
            continue
        new_gr = _soft_reset_gr(row['season_gr'])
        conn.execute(
            '''
            UPDATE users
            SET season_gr = ?,
                season_ranked_games = 0,
                gr_season_id = ?
            WHERE id = ?
            ''',
            (new_gr, season['id'], row['id']),
        )
        conn.execute(
            '''
            INSERT OR REPLACE INTO gr_daily_snapshots
                (snapshot_date, user_id, season_id, season_gr, total_gr, season_ranked_games, total_ranked_games, created_at)
            SELECT ?, id, ?, season_gr, total_gr, season_ranked_games, total_ranked_games, ?
            FROM users
            WHERE id = ?
            ''',
            (datetime.now(timezone.utc).date().isoformat(), season['id'], now, row['id']),
        )
    return season


def ensure_current_gr_season(user_ids=None):
    with get_db_connection() as conn:
        season = ensure_current_gr_season_for_conn(conn, user_ids)
        conn.commit()
        return season


def _leaderboard_payload(row, rank=None, scope='season'):
    games = int(row['games_played'] or 0)
    wins = int(row['wins'] or 0)
    losses = int(row['losses'] or 0)
    draws = int(row['draws'] or 0)
    season_gr = float(row['season_gr'] or GR_INITIAL) if 'season_gr' in row.keys() else float(GR_INITIAL)
    total_gr = float(row['total_gr'] or GR_INITIAL) if 'total_gr' in row.keys() else float(GR_INITIAL)
    gr_value = season_gr if scope == 'season' else total_gr
    payload = {
        'id': row['id'],
        'username': row['username'],
        'player_id': row['player_id'],
        'scope': scope,
        'gr': round(gr_value, 1),
        'season_gr': round(season_gr, 1),
        'total_gr': round(total_gr, 1),
        'highest_gr': round(float(row['highest_gr'] or GR_INITIAL), 1) if 'highest_gr' in row.keys() else float(GR_INITIAL),
        'season_ranked_games': int(row['season_ranked_games'] or 0) if 'season_ranked_games' in row.keys() else 0,
        'total_ranked_games': int(row['total_ranked_games'] or 0) if 'total_ranked_games' in row.keys() else 0,
        'gr_season_id': row['gr_season_id'] if 'gr_season_id' in row.keys() else current_gr_season()['id'],
        'games_played': games,
        'wins': wins,
        'losses': losses,
        'draws': draws,
        'win_rate': round(wins / games * 100, 1) if games else 0.0,
    }
    if rank is not None:
        payload['rank'] = int(rank or 0)
    return payload


def list_leaderboard(min_games=None, limit=50, scope='season'):
    scope = 'total' if str(scope or '').lower() == 'total' else 'season'
    min_games = int(min_games if min_games is not None else (GR_TOTAL_MIN_GAMES if scope == 'total' else GR_SEASON_MIN_GAMES))
    min_games = max(1, int(min_games or 1))
    limit = max(1, min(100, int(limit or 50)))
    with get_db_connection() as conn:
        season = ensure_current_gr_season_for_conn(conn)
        games_col = 'total_ranked_games' if scope == 'total' else 'season_ranked_games'
        gr_col = 'total_gr' if scope == 'total' else 'season_gr'
        season_filter = '' if scope == 'total' else 'AND gr_season_id = ?'
        params = [min_games]
        if scope != 'total':
            params.append(season['id'])
        params.append(limit)
        rows = conn.execute(
            f'''
            SELECT id, username, player_id, games_played, wins, losses, draws,
                   season_gr, total_gr, highest_gr, season_ranked_games, total_ranked_games, gr_season_id
            FROM users
            WHERE deleted_at IS NULL
              AND COALESCE(banned, 0) = 0
              AND COALESCE({games_col}, 0) >= ?
              {season_filter}
              ORDER BY
                COALESCE({gr_col}, ?) DESC,
                COALESCE({games_col}, 0) DESC,
                wins DESC,
                username_lower ASC
            LIMIT ?
            ''',
            (*params[:-1], GR_INITIAL, params[-1]),
        ).fetchall()
        conn.commit()
    return [_leaderboard_payload(row, scope=scope) for row in rows]


def get_leaderboard_rank(user_id, min_games=None, scope='season'):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    scope = 'total' if str(scope or '').lower() == 'total' else 'season'
    min_games = int(min_games if min_games is not None else (GR_TOTAL_MIN_GAMES if scope == 'total' else GR_SEASON_MIN_GAMES))
    min_games = max(1, int(min_games or 1))
    with get_db_connection() as conn:
        season = ensure_current_gr_season_for_conn(conn, [uid])
        games_col = 'total_ranked_games' if scope == 'total' else 'season_ranked_games'
        gr_col = 'total_gr' if scope == 'total' else 'season_gr'
        season_filter = '' if scope == 'total' else 'AND gr_season_id = ?'
        row_params = [uid, min_games]
        rank_params = [min_games]
        if scope != 'total':
            row_params.append(season['id'])
            rank_params.append(season['id'])
        row = conn.execute(
            f'''
            SELECT id, username, player_id, games_played, wins, losses, draws,
                   season_gr, total_gr, highest_gr, season_ranked_games, total_ranked_games, gr_season_id
            FROM users
            WHERE id = ?
              AND deleted_at IS NULL
              AND COALESCE(banned, 0) = 0
              AND COALESCE({games_col}, 0) >= ?
              {season_filter}
            ''',
            row_params,
        ).fetchone()
        if row is None:
            conn.commit()
            return None
        ranked_rows = conn.execute(
            f'''
            SELECT id
            FROM users
            WHERE deleted_at IS NULL
              AND COALESCE(banned, 0) = 0
              AND COALESCE({games_col}, 0) >= ?
              {season_filter}
            ORDER BY
              COALESCE({gr_col}, ?) DESC,
              COALESCE({games_col}, 0) DESC,
              wins DESC,
              username_lower ASC
            ''',
            (*rank_params, GR_INITIAL),
        ).fetchall()
        rank = 0
        for idx, ranked in enumerate(ranked_rows, start=1):
            if int(ranked['id']) == uid:
                rank = idx
                break
        conn.commit()
    return _leaderboard_payload(row, rank=rank, scope=scope)


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
        if 'deleted_at' in row.keys() and row['deleted_at']:
            return None, '账号已注销'
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
        now = utc_now()
        row = conn.execute('SELECT online_session_started_at FROM users WHERE id = ?', (uid,)).fetchone()
        add_seconds = 0
        if row is not None and row['online_session_started_at']:
            try:
                start = datetime.fromisoformat(str(row['online_session_started_at']).replace('Z', '+00:00'))
                end = datetime.fromisoformat(now.replace('Z', '+00:00'))
                add_seconds = max(0, int((end - start).total_seconds()))
            except Exception:
                add_seconds = 0
        conn.execute(
            '''
            UPDATE users
            SET last_login_at = ?,
                online_seconds = COALESCE(online_seconds, 0) + ?,
                online_session_started_at = NULL
            WHERE id = ?
            ''',
            (now, add_seconds, uid),
        )
        conn.commit()
        return True


def begin_user_online_session(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return False
    with get_db_connection() as conn:
        row = conn.execute('SELECT online_session_started_at FROM users WHERE id = ?', (uid,)).fetchone()
        if row is None or row['online_session_started_at']:
            return bool(row is not None)
        conn.execute(
            '''
            UPDATE users
            SET online_session_started_at = ?
            WHERE id = ? AND online_session_started_at IS NULL
            ''',
            (utc_now(), uid),
        )
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
        changed_at = utc_now()
        conn.execute(
            'UPDATE users SET password_hash = ?, password_changed_at = ? WHERE id = ?',
            (generate_password_hash(str(new_password)), changed_at, uid),
        )
        conn.execute('DELETE FROM remember_tokens WHERE user_id = ?', (uid,))
        conn.commit()
        row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        return row_to_user(row), None


def change_username(user_id, new_username):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    name = sanitize_username(new_username)
    ok, error = validate_username(name)
    if not ok:
        return None, error
    now_dt = utc_now_dt()
    now = utc_iso(now_dt)
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if row is None or ('deleted_at' in row.keys() and row['deleted_at']):
            return None, '请先登录账号'
        last_change = row['last_username_change_at'] if 'last_username_change_at' in row.keys() else None
        if last_change:
            try:
                last_dt = datetime.fromisoformat(str(last_change).replace('Z', '+00:00'))
            except Exception:
                last_dt = None
            if last_dt is not None:
                remaining = timedelta(days=14) - (now_dt - last_dt)
                if remaining.total_seconds() > 0:
                    return None, f'用户名每14天只能更改一次，还需等待{format_duration_zh(int(remaining.total_seconds()))}'
        existing = _find_user_row_by_username_key(conn, name)
        if existing is not None and int(existing['id']) != uid:
            return None, '用户名已存在'
        conn.execute(
            'UPDATE users SET username = ?, username_lower = ?, last_username_change_at = ? WHERE id = ?',
            (name, normalize_username_key(name), now, uid),
        )
        conn.commit()
        row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        _ensure_builtin_role_for_row(conn, row)
        conn.commit()
        row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        return row_to_user(row), None


def soft_delete_user(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    now = utc_now()
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if row is None:
            return None, '请先登录账号'
        if 'deleted_at' in row.keys() and row['deleted_at']:
            return row_to_user(row), None
        conn.execute(
            '''
            UPDATE users
            SET deleted_at = ?, banned = 1, ban_reason = COALESCE(ban_reason, 'account deleted'), banned_at = ?, ban_until = NULL
            WHERE id = ?
            ''',
            (now, now, uid),
        )
        conn.execute('DELETE FROM remember_tokens WHERE user_id = ?', (uid,))
        conn.commit()
        row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        return row_to_user(row), None


def update_user_skin(user_id, skin_config):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    skin = normalize_skin_config(skin_config)
    skin_json = json.dumps(skin, ensure_ascii=False, separators=(',', ':'))
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if row is None:
            return None, '请先登录账号'
        if str(row['skin_json'] or '') != skin_json:
            conn.execute(
                'UPDATE users SET skin_json = ? WHERE id = ?',
                (skin_json, uid),
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
        changed_at = utc_now()
        conn.execute(
            'UPDATE users SET password_hash = ?, password_changed_at = ? WHERE id = ?',
            (generate_password_hash(str(new_password)), changed_at, user['id']),
        )
        conn.execute('DELETE FROM remember_tokens WHERE user_id = ?', (user['id'],))
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
            duration = min(duration, 60 * 60 * 24 * 1000)
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


def _row_to_ip_ban(row):
    if row is None:
        return None
    return {
        'ip': row['ip'],
        'reason': row['reason'] or '',
        'created_at': row['created_at'],
        'banned_by': row['banned_by'] or '',
        'expires_at': row['expires_at'],
        'active': bool(row['active']),
    }


def _clear_expired_ip_ban(conn, row):
    if row is None or not bool(row['active']):
        return row
    expires_at = row['expires_at'] if 'expires_at' in row.keys() else None
    until_dt = _parse_utc(expires_at)
    if until_dt is not None and until_dt <= utc_now_dt():
        conn.execute('UPDATE ip_bans SET active = 0 WHERE ip = ?', (row['ip'],))
        conn.commit()
        return conn.execute('SELECT * FROM ip_bans WHERE ip = ?', (row['ip'],)).fetchone()
    return row


def set_ip_ban(ip, banned=True, reason='', duration_seconds=None, banned_by=''):
    token = str(ip or '').strip()[:80]
    if not token:
        return None, 'IP 不能为空'
    now = utc_now()
    expires_at = None
    if banned and duration_seconds is not None:
        try:
            duration = int(duration_seconds)
        except (TypeError, ValueError):
            duration = 0
        if duration > 0:
            duration = min(duration, 60 * 60 * 24 * 1000)
            expires_at = utc_iso(utc_now_dt() + timedelta(seconds=duration))
    with get_db_connection() as conn:
        if banned:
            conn.execute(
                '''
                INSERT INTO ip_bans (ip, reason, created_at, banned_by, expires_at, active)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(ip) DO UPDATE SET
                    reason=excluded.reason,
                    created_at=excluded.created_at,
                    banned_by=excluded.banned_by,
                    expires_at=excluded.expires_at,
                    active=1
                ''',
                (token, str(reason or '')[:300], now, str(banned_by or '')[:80], expires_at),
            )
        else:
            conn.execute('UPDATE ip_bans SET active = 0 WHERE ip = ?', (token,))
        conn.commit()
        row = conn.execute('SELECT * FROM ip_bans WHERE ip = ?', (token,)).fetchone()
        return _row_to_ip_ban(row), None


def get_ip_ban_status(ip):
    token = str(ip or '').strip()[:80]
    if not token:
        return {'banned': False}
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM ip_bans WHERE ip = ?', (token,)).fetchone()
        row = _clear_expired_ip_ban(conn, row)
        if row is None or not bool(row['active']):
            return {'banned': False, 'ip': token}
        remaining = _remaining_seconds_until(row['expires_at'])
        return {
            'banned': True,
            'ip': token,
            'reason': row['reason'] or '',
            'banned_by': row['banned_by'] or '',
            'created_at': row['created_at'],
            'expires_at': row['expires_at'],
            'remaining_seconds': remaining,
            'permanent': remaining is None,
        }


def list_ip_bans(active_only=True, limit=100, offset=0):
    limit = max(1, min(int(limit or 100), 300))
    offset = max(0, int(offset or 0))
    where = 'WHERE active = 1' if active_only else ''
    with get_db_connection() as conn:
        rows = conn.execute(
            f'SELECT * FROM ip_bans {where} ORDER BY active DESC, created_at DESC LIMIT ? OFFSET ?',
            (limit, offset),
        ).fetchall()
        cleaned = []
        for row in rows:
            row = _clear_expired_ip_ban(conn, row)
            if active_only and (row is None or not bool(row['active'])):
                continue
            cleaned.append(_row_to_ip_ban(row))
        total = conn.execute(f'SELECT COUNT(*) FROM ip_bans {where}').fetchone()[0]
        return {'items': cleaned, 'total': total, 'limit': limit, 'offset': offset}


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


def resolve_report_entry(
    report_id,
    action,
    moderation_action='none',
    admin_username='',
    note='',
    duration_seconds=None,
    target_moderation_action=None,
    reporter_moderation_action=None,
):
    try:
        rid = int(report_id)
    except (TypeError, ValueError):
        return None, '举报不存在'
    action = str(action or '').strip().lower()
    moderation_action = str(moderation_action or 'none').strip().lower()
    target_moderation_action = str(target_moderation_action if target_moderation_action is not None else moderation_action or 'none').strip().lower()
    reporter_moderation_action = str(reporter_moderation_action if reporter_moderation_action is not None else 'none').strip().lower()
    status_map = {'accept': 'accepted', 'reject': 'rejected', 'abusive': 'abusive'}
    if action not in status_map:
        return None, '处理动作无效'
    valid_moderation_actions = {'none', 'warn', 'mute', 'ban', 'invalidate_match'}
    if moderation_action not in valid_moderation_actions or target_moderation_action not in valid_moderation_actions or reporter_moderation_action not in valid_moderation_actions:
        return None, '处罚动作无效'
    now_dt = utc_now_dt()
    now = utc_iso(now_dt)
    duration = int(duration_seconds or 0) if duration_seconds is not None else None
    if (moderation_action == 'warn' or target_moderation_action == 'warn' or reporter_moderation_action == 'warn') and not duration:
        duration = 60 * 60
    expires_at = utc_iso(now_dt + timedelta(seconds=max(1, duration))) if duration else None
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

        def insert_moderation_action(target_user_id, target_username, action_type):
            action_type = str(action_type or 'none').strip().lower()
            if action_type == 'none':
                return
            action_expires_at = expires_at if action_type in {'mute', 'warn'} and duration else None
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
                    target_user_id,
                    target_username,
                    action_type,
                    str(note or '')[:500],
                    duration,
                    now,
                    action_expires_at,
                    rid,
                ),
            )

        insert_moderation_action(row['target_user_id'], row['target_username'], target_moderation_action)
        insert_moderation_action(row['reporter_user_id'], row['reporter_username'], reporter_moderation_action)
        conn.commit()
    return get_report_detail(rid), None


def get_active_user_warnings(user_id, limit=3):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return []
    now = utc_now()
    with get_db_connection() as conn:
        rows = conn.execute(
            '''
            SELECT id, reason, created_at, expires_at, related_report_id
            FROM moderation_actions
            WHERE target_user_id = ?
              AND action_type = 'warn'
              AND expires_at IS NOT NULL
              AND expires_at > ?
            ORDER BY created_at DESC
            LIMIT ?
            ''',
            (uid, now, max(1, min(int(limit or 3), 10))),
        ).fetchall()
        return [
            {
                'id': row['id'],
                'message': row['reason'] or '请注意游戏内行为',
                'created_at': row['created_at'],
                'expires_at': row['expires_at'],
                'related_report_id': row['related_report_id'],
            }
            for row in rows
        ]


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
        ensure_current_gr_season_for_conn(conn, [uid])
        row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        row = _clear_expired_user_ban(conn, row)
        conn.commit()
        return row_to_user(row)


def get_user_by_username(username):
    name = sanitize_username(username)
    if not name:
        return None
    with get_db_connection() as conn:
        row = _find_user_row_by_username_key(conn, name)
        if row is not None:
            ensure_current_gr_season_for_conn(conn, [row['id']])
            row = conn.execute('SELECT * FROM users WHERE id = ?', (row['id'],)).fetchone()
        row = _clear_expired_user_ban(conn, row)
        conn.commit()
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
        row = conn.execute('SELECT id, deleted_at FROM users WHERE id = ?', (uid,)).fetchone()
        if row is None:
            return ''
        if 'deleted_at' in row.keys() and row['deleted_at']:
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
        cleanup_cutoff_key = '_last_expired_remember_cleanup'
        last_cleanup = getattr(verify_remember_token, cleanup_cutoff_key, 0.0)
        do_cleanup = time.monotonic() - float(last_cleanup or 0) >= 3600
        if do_cleanup:
            conn.execute('DELETE FROM remember_tokens WHERE expires_at < ?', (now,))
            setattr(verify_remember_token, cleanup_cutoff_key, time.monotonic())
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
        is_deleted = bool(row['deleted_at']) if 'deleted_at' in row.keys() else False
        if is_banned or is_deleted:
            conn.execute('DELETE FROM remember_tokens WHERE selector = ?', (selector,))
            conn.commit()
            return None
        try:
            last_used = datetime.fromisoformat(str(row['last_used_at'] or '').replace('Z', '+00:00'))
        except Exception:
            last_used = None
        should_touch = last_used is None or (utc_now_dt() - last_used).total_seconds() >= 3600
        if should_touch:
            conn.execute('UPDATE remember_tokens SET last_used_at = ? WHERE selector = ?', (now, selector))
            conn.commit()
        elif do_cleanup:
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
    'play_seconds': 'play_seconds',
    'win_rate': 'CASE WHEN games_played > 0 THEN CAST(wins AS REAL) / games_played ELSE 0 END',
}


CARD_DRAFT_STAT_SORTS = {
    'mode': 'mode',
    'card_id': 'card_id',
    'shown_count': 'shown_count',
    'picked_count': 'picked_count',
    'pick_rate': 'CASE WHEN shown_count > 0 THEN CAST(picked_count AS REAL) / shown_count ELSE 0 END',
    'picked_games': 'picked_games',
    'win_games': 'win_games',
    'draw_games': 'draw_games',
    'card_win_rate': 'CASE WHEN picked_games > 0 THEN CAST(win_games AS REAL) / picked_games ELSE 0 END',
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
    week_start = current_week_start()
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
            conn.execute(
                '''
                INSERT INTO card_draft_stats_weekly (week_start, mode, card_id, shown_count, picked_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(week_start, mode, card_id) DO UPDATE SET
                    shown_count = shown_count + excluded.shown_count,
                    picked_count = picked_count + excluded.picked_count,
                    updated_at = excluded.updated_at
                ''',
                (week_start, mode_key, card_id, int(shown_inc), int(picked_inc), now),
            )
        conn.commit()
    return True


def record_card_draft_counts(mode, card_counts):
    mode_key = str(mode or '').strip()
    if mode_key not in ('1v1', '2v2') or not isinstance(card_counts, dict):
        return False
    rows = []
    for raw_id, counts in card_counts.items():
        card_id = str(raw_id or '').strip()
        if not card_id:
            continue
        if isinstance(counts, dict):
            shown_inc = counts.get('shown', 0)
            picked_inc = counts.get('picked', 0)
        else:
            try:
                shown_inc, picked_inc = counts
            except Exception:
                continue
        try:
            shown_inc = int(shown_inc or 0)
            picked_inc = int(picked_inc or 0)
        except (TypeError, ValueError):
            continue
        if shown_inc <= 0 and picked_inc <= 0:
            continue
        rows.append((card_id, shown_inc, picked_inc))
    if not rows:
        return False
    now = utc_now()
    week_start = current_week_start()
    with get_db_connection() as conn:
        conn.executemany(
            '''
            INSERT INTO card_draft_stats (mode, card_id, shown_count, picked_count, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(mode, card_id) DO UPDATE SET
                shown_count = shown_count + excluded.shown_count,
                picked_count = picked_count + excluded.picked_count,
                updated_at = excluded.updated_at
            ''',
            [(mode_key, card_id, shown_inc, picked_inc, now) for card_id, shown_inc, picked_inc in rows],
        )
        conn.executemany(
            '''
            INSERT INTO card_draft_stats_weekly (week_start, mode, card_id, shown_count, picked_count, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(week_start, mode, card_id) DO UPDATE SET
                shown_count = shown_count + excluded.shown_count,
                picked_count = picked_count + excluded.picked_count,
                updated_at = excluded.updated_at
            ''',
            [(week_start, mode_key, card_id, shown_inc, picked_inc, now) for card_id, shown_inc, picked_inc in rows],
        )
        conn.commit()
    return True


def record_card_draft_win_result(mode, player_card_ids, winner_indices=None, result='finished'):
    mode_key = str(mode or '').strip()
    if mode_key not in ('1v1', '2v2'):
        return False
    if not isinstance(player_card_ids, (list, tuple)):
        return False
    winner_set = set()
    for raw_idx in winner_indices or []:
        try:
            winner_set.add(int(raw_idx))
        except (TypeError, ValueError):
            continue
    is_draw = str(result or '').lower() == 'draw'
    rows = {}
    for pidx, raw_cards in enumerate(player_card_ids):
        unique_cards = set()
        for raw_id in raw_cards or []:
            card_id = str(raw_id or '').strip()
            if card_id:
                unique_cards.add(card_id)
        for card_id in unique_cards:
            picked_inc, win_inc, draw_inc = rows.get(card_id, (0, 0, 0))
            picked_inc += 1
            if is_draw:
                draw_inc += 1
            elif pidx in winner_set:
                win_inc += 1
            rows[card_id] = (picked_inc, win_inc, draw_inc)
    if not rows:
        return False
    now = utc_now()
    week_start = current_week_start()
    with get_db_connection() as conn:
        conn.executemany(
            '''
            INSERT INTO card_draft_win_stats (mode, card_id, picked_games, win_games, draw_games, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(mode, card_id) DO UPDATE SET
                picked_games = picked_games + excluded.picked_games,
                win_games = win_games + excluded.win_games,
                draw_games = draw_games + excluded.draw_games,
                updated_at = excluded.updated_at
            ''',
            [
                (mode_key, card_id, picked_inc, win_inc, draw_inc, now)
                for card_id, (picked_inc, win_inc, draw_inc) in rows.items()
            ],
        )
        conn.executemany(
            '''
            INSERT INTO card_draft_win_stats_weekly (week_start, mode, card_id, picked_games, win_games, draw_games, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(week_start, mode, card_id) DO UPDATE SET
                picked_games = picked_games + excluded.picked_games,
                win_games = win_games + excluded.win_games,
                draw_games = draw_games + excluded.draw_games,
                updated_at = excluded.updated_at
            ''',
            [
                (week_start, mode_key, card_id, picked_inc, win_inc, draw_inc, now)
                for card_id, (picked_inc, win_inc, draw_inc) in rows.items()
            ],
        )
        conn.commit()
    return True


def _match_draft_card_ids_by_player(summary):
    if not isinstance(summary, dict):
        return []
    candidates = (
        summary.get('draft_card_ids_by_player'),
        summary.get('player_draft_cards'),
        summary.get('draft_picks'),
    )
    for value in candidates:
        if isinstance(value, list):
            rows = []
            for raw_cards in value:
                if isinstance(raw_cards, (list, tuple, set)):
                    rows.append([str(card_id).strip() for card_id in raw_cards if str(card_id or '').strip()])
                else:
                    rows.append([])
            if rows:
                return rows
        if isinstance(value, dict):
            rows = []
            for idx in range(4):
                raw_cards = value.get(idx, value.get(str(idx), []))
                if isinstance(raw_cards, (list, tuple, set)):
                    rows.append([str(card_id).strip() for card_id in raw_cards if str(card_id or '').strip()])
                else:
                    rows.append([])
            while rows and not rows[-1]:
                rows.pop()
            if rows:
                return rows
    return []


def _match_winner_player_indices_for_card_stats(row, summary):
    raw_result = str(row['result'] or summary.get('result') or '').lower()
    if raw_result == 'draw':
        return [], True
    explicit = summary.get('winner_player_indices')
    if isinstance(explicit, list):
        indices = []
        for value in explicit:
            try:
                indices.append(int(value))
            except (TypeError, ValueError):
                pass
        if indices:
            return indices, False
    try:
        winner_index = int(row['winner_index']) if row['winner_index'] is not None else int(summary.get('winner_index'))
    except (TypeError, ValueError):
        winner_index = None
    if winner_index is None or winner_index < 0:
        return [], True
    mode = str(row['mode'] or summary.get('mode') or '').lower()
    if mode == '2v2':
        return {0: [0, 1], 1: [2, 3]}.get(winner_index, []), False
    return [winner_index], False


def rebuild_card_draft_win_stats_from_matches():
    """Rebuild card win-rate stats from persisted match summaries.

    Only summaries that include draft_card_ids_by_player/player_draft_cards can
    be reconstructed. This intentionally does not touch card_draft_stats, which
    stores shown/picked counts.
    """
    now = utc_now()
    totals = {}
    weekly_totals = {}
    with get_db_connection() as conn:
        rows = conn.execute('SELECT * FROM matches ORDER BY id ASC').fetchall()
        scanned_matches = len(rows)
        counted_matches = 0
        skipped_matches = 0
        for row in rows:
            mode = str(row['mode'] or '').strip()
            if mode not in ('1v1', '2v2'):
                skipped_matches += 1
                continue
            raw_result = str(row['result'] or '').lower()
            if raw_result not in ('win', 'draw', 'finished'):
                skipped_matches += 1
                continue
            week_start = week_start_for_iso(row['ended_at'] or row['started_at'])
            summary = _safe_json_loads(row['summary_json'], {})
            player_cards = _match_draft_card_ids_by_player(summary)
            if not player_cards:
                skipped_matches += 1
                continue
            winner_indices, is_draw = _match_winner_player_indices_for_card_stats(row, summary)
            winner_set = set(winner_indices)
            added = False
            for pidx, raw_cards in enumerate(player_cards):
                unique_cards = {str(card_id).strip() for card_id in raw_cards if str(card_id or '').strip()}
                if not unique_cards:
                    continue
                added = True
                for card_id in unique_cards:
                    key = (mode, card_id)
                    picked, wins, draws = totals.get(key, (0, 0, 0))
                    picked += 1
                    if is_draw:
                        draws += 1
                    elif pidx in winner_set:
                        wins += 1
                    totals[key] = (picked, wins, draws)
                    weekly_key = (week_start, mode, card_id)
                    week_picked, week_wins, week_draws = weekly_totals.get(weekly_key, (0, 0, 0))
                    week_picked += 1
                    if is_draw:
                        week_draws += 1
                    elif pidx in winner_set:
                        week_wins += 1
                    weekly_totals[weekly_key] = (week_picked, week_wins, week_draws)
            if added:
                counted_matches += 1
            else:
                skipped_matches += 1
        conn.execute('DELETE FROM card_draft_win_stats')
        conn.execute('DELETE FROM card_draft_win_stats_weekly')
        if totals:
            conn.executemany(
                '''
                INSERT INTO card_draft_win_stats (mode, card_id, picked_games, win_games, draw_games, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                [
                    (mode, card_id, picked, wins, draws, now)
                    for (mode, card_id), (picked, wins, draws) in totals.items()
                ],
            )
        if weekly_totals:
            conn.executemany(
                '''
                INSERT INTO card_draft_win_stats_weekly (week_start, mode, card_id, picked_games, win_games, draw_games, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                [
                    (week_start, mode, card_id, picked, wins, draws, now)
                    for (week_start, mode, card_id), (picked, wins, draws) in weekly_totals.items()
                ],
            )
        conn.commit()
    return {
        'matches': scanned_matches,
        'counted_matches': counted_matches,
        'skipped_matches': skipped_matches,
        'cards': len(totals),
        'picked_games': sum(value[0] for value in totals.values()),
        'win_games': sum(value[1] for value in totals.values()),
        'draw_games': sum(value[2] for value in totals.values()),
        'weekly_cards': len(weekly_totals),
    }


def list_card_draft_stats(mode='', sort='pick_rate', order='desc', limit=300, offset=0, merge_modes=False, scope='total', week_start=None, winner_only=False):
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
    merge = bool(merge_modes)
    mode_filter = mode_key if mode_key in ('1v1', '2v2') else ''
    mode_where = 'WHERE mode = ?' if mode_filter else ''
    mode_params = [mode_filter] if mode_filter else []
    scope_key = 'week' if str(scope or '').lower() in ('week', 'weekly') else 'total'
    draft_table = 'card_draft_stats_weekly' if scope_key == 'week' else 'card_draft_stats'
    win_table = 'card_draft_win_stats_weekly' if scope_key == 'week' else 'card_draft_win_stats'
    winner_filter = bool(winner_only)
    selected_week = week_start_for_iso(week_start) if scope_key == 'week' else ''
    if scope_key == 'week':
        week_clause = 'week_start = ?'
        if mode_filter:
            mode_where = f'WHERE {week_clause} AND mode = ?'
            mode_params = [selected_week, mode_filter]
        else:
            mode_where = f'WHERE {week_clause}'
            mode_params = [selected_week]
    order_clause = f'{sort_expr} {direction}, shown_count DESC, card_id ASC'
    with get_db_connection() as conn:
        if merge:
            base_query = f'''
                WITH draft AS (
                    SELECT
                        'merged' AS mode,
                        card_id,
                        SUM(shown_count) AS shown_count,
                        SUM(picked_count) AS picked_count,
                        MAX(updated_at) AS updated_at
                    FROM {draft_table}
                    {mode_where}
                    GROUP BY card_id
                ),
                wins AS (
                    SELECT
                        'merged' AS mode,
                        card_id,
                        SUM(picked_games) AS picked_games,
                        SUM(win_games) AS win_games,
                        SUM(draw_games) AS draw_games,
                        MAX(updated_at) AS win_updated_at
                    FROM {win_table}
                    {mode_where}
                    GROUP BY card_id
                )
                SELECT
                    {'wins.mode' if winner_filter else 'draft.mode'} AS mode,
                    {'wins.card_id' if winner_filter else 'draft.card_id'} AS card_id,
                    COALESCE(draft.shown_count, 0) AS shown_count,
                    COALESCE(draft.picked_count, 0) AS picked_count,
                    COALESCE(draft.updated_at, '') AS updated_at,
                    COALESCE(wins.picked_games, 0) AS picked_games,
                    COALESCE(wins.win_games, 0) AS win_games,
                    COALESCE(wins.draw_games, 0) AS draw_games,
                    COALESCE(wins.win_updated_at, '') AS win_updated_at,
                    CASE WHEN COALESCE(draft.shown_count, 0) > 0 THEN CAST(COALESCE(draft.picked_count, 0) AS REAL) / draft.shown_count * 100 ELSE 0 END AS pick_rate,
                    CASE WHEN COALESCE(wins.picked_games, 0) > 0 THEN CAST(wins.win_games AS REAL) / wins.picked_games * 100 ELSE 0 END AS card_win_rate
                FROM {'wins LEFT JOIN draft ON draft.card_id = wins.card_id WHERE wins.win_games > 0' if winner_filter else 'draft LEFT JOIN wins ON wins.card_id = draft.card_id'}
            '''
            total = conn.execute(f'SELECT COUNT(*) FROM ({base_query})', mode_params + mode_params).fetchone()[0]
            rows = conn.execute(
                f'''
                SELECT * FROM ({base_query})
                ORDER BY {order_clause}
                LIMIT ? OFFSET ?
                ''',
                mode_params + mode_params + [safe_limit, safe_offset],
            ).fetchall()
        else:
            draft_mode_where = mode_where.replace('week_start', 'draft.week_start').replace('mode', 'draft.mode')
            if winner_filter:
                wins_mode_where = mode_where.replace('week_start', 'wins.week_start').replace('mode', 'wins.mode')
                winner_where = f'{wins_mode_where} AND wins.win_games > 0' if wins_mode_where else 'WHERE wins.win_games > 0'
                base_query = f'''
                    SELECT
                        wins.mode,
                        wins.card_id,
                        COALESCE(draft.shown_count, 0) AS shown_count,
                        COALESCE(draft.picked_count, 0) AS picked_count,
                        COALESCE(draft.updated_at, '') AS updated_at,
                        COALESCE(wins.picked_games, 0) AS picked_games,
                        COALESCE(wins.win_games, 0) AS win_games,
                        COALESCE(wins.draw_games, 0) AS draw_games,
                        COALESCE(wins.updated_at, '') AS win_updated_at,
                        CASE WHEN COALESCE(draft.shown_count, 0) > 0 THEN CAST(COALESCE(draft.picked_count, 0) AS REAL) / draft.shown_count * 100 ELSE 0 END AS pick_rate,
                        CASE WHEN COALESCE(wins.picked_games, 0) > 0 THEN CAST(wins.win_games AS REAL) / wins.picked_games * 100 ELSE 0 END AS card_win_rate
                    FROM {win_table} AS wins
                    LEFT JOIN {draft_table} AS draft
                        ON draft.mode = wins.mode AND draft.card_id = wins.card_id
                        {'AND draft.week_start = wins.week_start' if scope_key == 'week' else ''}
                    {winner_where}
                '''
            else:
                base_query = f'''
                    SELECT
                        draft.mode,
                        draft.card_id,
                        draft.shown_count,
                        draft.picked_count,
                        draft.updated_at,
                        COALESCE(wins.picked_games, 0) AS picked_games,
                        COALESCE(wins.win_games, 0) AS win_games,
                        COALESCE(wins.draw_games, 0) AS draw_games,
                        COALESCE(wins.updated_at, '') AS win_updated_at,
                        CASE WHEN draft.shown_count > 0 THEN CAST(draft.picked_count AS REAL) / draft.shown_count * 100 ELSE 0 END AS pick_rate,
                        CASE WHEN COALESCE(wins.picked_games, 0) > 0 THEN CAST(wins.win_games AS REAL) / wins.picked_games * 100 ELSE 0 END AS card_win_rate
                    FROM {draft_table} AS draft
                    LEFT JOIN {win_table} AS wins
                        ON wins.mode = draft.mode AND wins.card_id = draft.card_id
                        {'AND wins.week_start = draft.week_start' if scope_key == 'week' else ''}
                    {draft_mode_where}
                '''
            total = conn.execute(f'SELECT COUNT(*) FROM ({base_query})', mode_params).fetchone()[0]
            rows = conn.execute(
                f'''
                SELECT * FROM ({base_query})
                ORDER BY {order_clause}
                LIMIT ? OFFSET ?
                ''',
                mode_params + [safe_limit, safe_offset],
            ).fetchall()
    return {
        'items': [
            {
                'mode': row['mode'],
                'card_id': row['card_id'],
                'shown_count': row['shown_count'],
                'picked_count': row['picked_count'],
                'pick_rate': round(float(row['pick_rate'] or 0), 2),
                'picked_games': row['picked_games'],
                'win_games': row['win_games'],
                'draw_games': row['draw_games'],
                'card_win_rate': round(float(row['card_win_rate'] or 0), 2),
                'updated_at': row['updated_at'],
                'win_updated_at': row['win_updated_at'],
            }
            for row in rows
        ],
        'total': total,
        'limit': safe_limit,
        'offset': safe_offset,
        'sort': sort_key if sort_key in CARD_DRAFT_STAT_SORTS else 'pick_rate',
        'order': 'asc' if direction == 'ASC' else 'desc',
        'merge_modes': merge,
        'scope': scope_key,
        'week_start': selected_week,
        'winner_only': winner_filter,
    }


def list_admin_users(query='', sort='last_login_at', order='desc', limit=30, offset=0):
    sort_key = str(sort or 'last_login_at')
    sort_expr = ADMIN_USER_SORTS.get(sort_key, ADMIN_USER_SORTS['last_login_at'])
    direction = 'ASC' if str(order or '').lower() == 'asc' else 'DESC'
    try:
        safe_limit = max(1, min(int(limit), 50))
    except (TypeError, ValueError):
        safe_limit = 30
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


def _match_result_for_user(row, perspective_user_id=None, perspective_username=None, player_names=None, player_ids=None, summary=None):
    if perspective_user_id is not None:
        try:
            uid = int(perspective_user_id)
        except (TypeError, ValueError):
            uid = None
        if uid is not None:
            ids = []
            for value in (player_ids or []):
                try:
                    ids.append(int(value))
                except (TypeError, ValueError):
                    ids.append(None)
            if uid in ids:
                raw_result = str(row['result'] or '').strip()
                try:
                    winner_index = int(row['winner_index']) if row['winner_index'] is not None else None
                except (TypeError, ValueError):
                    winner_index = None
                if raw_result.lower() == 'draw' or winner_index == -1:
                    return 'draw'
                winner_ids = set()
                for value in (summary or {}).get('winner_user_ids') or []:
                    try:
                        winner_ids.add(int(value))
                    except (TypeError, ValueError):
                        pass
                if winner_ids:
                    return 'win' if uid in winner_ids else 'loss'
                if winner_index is not None and winner_index >= 0:
                    mode = str(row['mode'] or (summary or {}).get('mode') or '').lower()
                    if mode == '2v2':
                        team_indices = {0: [0, 1], 1: [2, 3]}.get(winner_index, [])
                        return 'win' if any(0 <= idx < len(ids) and ids[idx] == uid for idx in team_indices) else 'loss'
                    if 0 <= winner_index < len(ids):
                        return 'win' if ids[winner_index] == uid else 'loss'
                return raw_result or 'finished'
    if perspective_username:
        return _match_result_for_username(row, perspective_username, player_names or [], summary or {})
    return row['result']


def _row_to_match_summary(row, perspective_username=None, perspective_user_id=None):
    if row is None:
        return None
    player_names = _safe_json_loads(row['player_names_json'], [])
    player_ids = _safe_json_loads(row['player_ids_json'] if 'player_ids_json' in row.keys() else '[]', [])
    summary = _safe_json_loads(row['summary_json'], {})
    raw_result = row['result']
    result = _match_result_for_user(row, perspective_user_id, perspective_username, player_names, player_ids, summary)
    return {
        'id': row['id'],
        'mode': row['mode'],
        'started_at': row['started_at'],
        'ended_at': row['ended_at'],
        'duration_seconds': row['duration_seconds'],
        'players': player_names,
        'player_ids': player_ids,
        'winner_name': row['winner_name'],
        'winner_index': row['winner_index'],
        'rounds': row['rounds'],
        'mod_source': row['mod_source'],
        'mod_hash': row['mod_hash'],
        'result': result,
        'result_raw': raw_result,
        'valid_for_ranking': bool(summary.get('valid_for_ranking', True)),
        'ranking_invalid_reason': summary.get('ranking_invalid_reason', ''),
        'gr_result': summary.get('gr_result'),
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
        id_pattern = f'%{uid}%'
        name_pattern = f'%"{user["username"]}"%'
        candidate_rows = conn.execute(
            '''
            SELECT * FROM matches
            WHERE player_ids_json LIKE ? OR player_names_json LIKE ?
            ORDER BY id DESC
            LIMIT ?
            ''',
            (id_pattern, name_pattern, safe_match_limit * 5),
        ).fetchall()
        matches = []
        user_key = normalize_username_key(user['username'])
        for match in candidate_rows:
            ids = _safe_json_loads(match['player_ids_json'] if 'player_ids_json' in match.keys() else '[]', [])
            names = _safe_json_loads(match['player_names_json'], [])
            has_id = False
            for value in ids:
                try:
                    if int(value) == uid:
                        has_id = True
                        break
                except (TypeError, ValueError):
                    continue
            has_name = any(normalize_username_key(name) == user_key for name in names)
            if has_id or has_name:
                matches.append(match)
            if len(matches) >= safe_match_limit:
                break
    return {
        'user': user,
        'matches': [_row_to_match_summary(match, perspective_username=user['username'], perspective_user_id=uid) for match in matches],
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


def _user_row_is_deleted(row) -> bool:
    if row is None:
        return True
    try:
        return bool(row['deleted_at']) if 'deleted_at' in row.keys() else False
    except Exception:
        return False


def _cleanup_expired_friend_requests(conn, force=False):
    global _FRIEND_CLEANUP_LAST_TS
    now_ts = time.time()
    if not force and now_ts - _FRIEND_CLEANUP_LAST_TS < _FRIEND_CLEANUP_INTERVAL_SECONDS:
        return
    cutoff = utc_iso(utc_now_dt() - timedelta(days=FRIEND_REQUEST_TTL_DAYS))
    try:
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
        _FRIEND_CLEANUP_LAST_TS = now_ts
    except sqlite3.OperationalError as exc:
        if 'locked' not in str(exc).lower():
            raise
        print(f'[db] skip expired friend request cleanup: {exc}', flush=True)


def cleanup_expired_friend_requests_once(force=False):
    started = time.perf_counter()
    try:
        with get_db_connection() as conn:
            _cleanup_expired_friend_requests(conn, force=force)
            conn.commit()
        db_slow_log('background', (time.perf_counter() - started) * 1000, 'friend_cleanup')
        return True, None
    except sqlite3.OperationalError as exc:
        if 'locked' in str(exc).lower():
            print(f'[db] skip expired friend request cleanup: {exc}', flush=True)
            return False, str(exc)
        raise


def mark_friend_notifications_read_for_user(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return False, '请先登录账号'
    started = time.perf_counter()
    with get_db_connection() as conn:
        row = conn.execute('SELECT id FROM users WHERE id = ?', (uid,)).fetchone()
        if row is None:
            return False, '请先登录账号'
        _mark_friend_notifications_read(conn, uid)
        conn.commit()
    db_slow_log('social', (time.perf_counter() - started) * 1000, 'friend_mark_read')
    return True, None


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
        FROM friendships f
        JOIN users u ON u.id = f.requester_id
        WHERE f.addressee_id = ?
          AND f.addressee_read_at IS NULL
          AND (f.status = ? OR f.notice_type = ?)
          AND u.deleted_at IS NULL
        ''',
        (user_id, 'pending', 'auto_add'),
    ).fetchone()
    return int(row['count'] or 0) if row else 0


def _recent_matches_for_user(conn, user_id, username='', limit=5):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        uid = None
    safe_limit = max(1, min(int(limit or 5), 20))
    rows = []
    if uid is not None:
        candidates = conn.execute(
            '''
            SELECT * FROM matches
            WHERE player_ids_json IS NOT NULL AND player_ids_json != ''
            ORDER BY id DESC
            LIMIT ?
            ''',
            (safe_limit * 8,),
        ).fetchall()
        for row in candidates:
            ids = _safe_json_loads(row['player_ids_json'] if 'player_ids_json' in row.keys() else '[]', [])
            try:
                if uid in {int(value) for value in ids if value is not None}:
                    rows.append(row)
            except (TypeError, ValueError):
                continue
            if len(rows) >= safe_limit:
                break
    if not rows and username:
        pattern = f'%"{username}"%'
        rows = conn.execute(
            '''
            SELECT * FROM matches
            WHERE player_names_json LIKE ?
            ORDER BY id DESC
            LIMIT ?
            ''',
            (pattern, safe_limit),
        ).fetchall()
    return [_row_to_match_summary(row, perspective_username=username, perspective_user_id=uid) for row in rows]


def _recent_matches_for_username(conn, username, limit=5):
    return _recent_matches_for_user(conn, None, username, limit)


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
            'SELECT * FROM users WHERE player_id = ? AND searchable_by_player_id = 1 AND deleted_at IS NULL',
            (player_id,),
        ).fetchone()
        if row is not None:
            return row
    name = sanitize_username(token)
    if name:
        row = _find_user_row_by_username_key(conn, name, searchable_by_nickname=True)
        return None if _user_row_is_deleted(row) else row
    return None


def list_friends(user_id, mark_read=False):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    with get_db_connection() as conn:
        started = time.perf_counter()
        self_row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if self_row is None or _user_row_is_deleted(self_row):
            return None, '请先登录账号'
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
            if other is None or _user_row_is_deleted(other):
                continue
            item = {
                'request_id': row['id'],
                'status': row['status'],
                'notice_type': row['notice_type'] if 'notice_type' in row.keys() else 'request',
                'is_unread': row['addressee_id'] == uid and not (row['addressee_read_at'] if 'addressee_read_at' in row.keys() else None),
                'direction': 'incoming' if row['addressee_id'] == uid else 'outgoing',
                'user': _public_social_user(other) if row['status'] == 'accepted' else _basic_social_user(other),
                'matches': _recent_matches_for_user(conn, other['id'], other['username'], 5) if row['status'] == 'accepted' else [],
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
        result = {
            'settings': {
                'accept_friend_requests': bool(self_row['accept_friend_requests']),
                'searchable_by_nickname': bool(self_row['searchable_by_nickname']),
                'searchable_by_player_id': bool(self_row['searchable_by_player_id']),
            },
            'friends': friends,
            'incoming': incoming,
            'outgoing': outgoing,
            'unread_count': unread_count,
        }
        db_slow_log('social', (time.perf_counter() - started) * 1000, 'friend_list')
        return result, None


def add_friend_request(user_id, identifier):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    now = utc_now()
    return_friend_list = False
    with get_db_connection() as conn:
        requester = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if requester is None or _user_row_is_deleted(requester):
            return None, '请先登录账号'
        target = _find_social_target(conn, identifier)
        if target is None:
            return None, '账号不存在'
        if _user_row_is_deleted(target):
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
                return_friend_list = True
            elif existing['status'] == 'pending' and existing['addressee_id'] == uid:
                conn.execute(
                    'UPDATE friendships SET status = ?, updated_at = ?, addressee_read_at = COALESCE(addressee_read_at, ?) WHERE id = ?',
                    ('accepted', now, now, existing['id']),
                )
                conn.commit()
                return_friend_list = True
            elif auto_add:
                conn.execute(
                    '''
                    UPDATE friendships
                    SET status = ?, updated_at = ?, notice_type = ?, expires_at = NULL, addressee_read_at = NULL
                    WHERE id = ?
                    ''',
                    ('accepted', now, 'auto_add', existing['id']),
                )
                conn.commit()
                return_friend_list = True
            else:
                return_friend_list = True
        else:
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
            return_friend_list = True
    if return_friend_list:
        return list_friends(uid)[0], None
    return None, '添加好友失败'


def respond_friend_request(user_id, request_id, action):
    try:
        uid = int(user_id)
        rid = int(request_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    action_text = str(action or '').lower()
    now = utc_now()
    with get_db_connection() as conn:
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


def _friendship_status(conn, user_a, user_b):
    row = conn.execute(
        '''
        SELECT * FROM friendships
        WHERE ((requester_id = ? AND addressee_id = ?)
            OR (requester_id = ? AND addressee_id = ?))
        ORDER BY id DESC
        LIMIT 1
        ''',
        (user_a, user_b, user_b, user_a),
    ).fetchone()
    return row['status'] if row is not None else ''


def _dm_user_pair(user_a, user_b):
    a = int(user_a)
    b = int(user_b)
    return (a, b) if a < b else (b, a)


def _cleanup_old_dm_messages(conn):
    cutoff = utc_iso(utc_now_dt() - timedelta(days=DM_RETENTION_DAYS))
    conn.execute('DELETE FROM dm_messages WHERE created_at < ?', (cutoff,))


def cleanup_old_dm_messages_once():
    try:
        with get_db_connection() as conn:
            started = time.perf_counter()
            _cleanup_old_dm_messages(conn)
            conn.commit()
            db_slow_log('dm_cleanup', (time.perf_counter() - started) * 1000, 'dm_cleanup')
            return True, None
    except sqlite3.OperationalError as exc:
        return False, str(exc)


def _trim_dm_thread_bytes(conn, thread_id):
    try:
        tid = int(thread_id)
    except (TypeError, ValueError):
        return
    rows = conn.execute(
        'SELECT id, message FROM dm_messages WHERE thread_id = ? ORDER BY id ASC',
        (tid,),
    ).fetchall()
    total = sum(len(str(row['message'] or '').encode('utf-8')) for row in rows)
    if total <= DM_THREAD_MAX_BYTES:
        return
    delete_ids = []
    for row in rows:
        if total <= DM_THREAD_MAX_BYTES or len(rows) - len(delete_ids) <= 1:
            break
        delete_ids.append(row['id'])
        total -= len(str(row['message'] or '').encode('utf-8'))
    if delete_ids:
        placeholders = ','.join('?' for _ in delete_ids)
        conn.execute(f'DELETE FROM dm_messages WHERE id IN ({placeholders})', delete_ids)


def _dm_unread_count_conn(conn, user_id):
    row = conn.execute(
        '''
        SELECT COUNT(*) AS count
        FROM dm_messages m
        JOIN users u ON u.id = m.sender_user_id
        WHERE m.recipient_user_id = ?
          AND m.read_at IS NULL
          AND m.hidden = 0
          AND u.deleted_at IS NULL
        ''',
        (int(user_id),),
    ).fetchone()
    return int(row['count'] or 0) if row else 0


def _get_or_create_dm_thread(conn, user_a, user_b):
    low, high = _dm_user_pair(user_a, user_b)
    now = utc_now()
    row = conn.execute(
        'SELECT * FROM dm_threads WHERE user_low_id = ? AND user_high_id = ?',
        (low, high),
    ).fetchone()
    if row is not None:
        return row
    cur = conn.execute(
        '''
        INSERT INTO dm_threads (user_low_id, user_high_id, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ''',
        (low, high, now, now),
    )
    return conn.execute('SELECT * FROM dm_threads WHERE id = ?', (cur.lastrowid,)).fetchone()


def _dm_message_row_to_dict(row):
    if row is None:
        return None
    return {
        'id': row['id'],
        'thread_id': row['thread_id'],
        'sender_user_id': row['sender_user_id'],
        'recipient_user_id': row['recipient_user_id'],
        'message': row['message'],
        'risk_level': row['risk_level'],
        'created_at': row['created_at'],
        'read_at': row['read_at'],
        'hidden': bool(row['hidden']),
    }


def dm_unread_count(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return 0
    with get_db_connection() as conn:
        row = conn.execute(
            '''
            SELECT COUNT(*) AS count
            FROM dm_messages m
            JOIN users u ON u.id = m.sender_user_id
            WHERE m.recipient_user_id = ?
              AND m.read_at IS NULL
              AND m.hidden = 0
              AND u.deleted_at IS NULL
            ''',
            (uid,),
        ).fetchone()
        return int(row['count'] or 0) if row else 0


def list_dm_threads(user_id, limit=50):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    safe_limit = max(1, min(int(limit or 50), 50))
    with get_db_connection() as conn:
        started = time.perf_counter()
        self_row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if self_row is None or _user_row_is_deleted(self_row):
            return None, '请先登录账号'
        rows = conn.execute(
            '''
            SELECT t.*,
                   (
                       SELECT message FROM dm_messages m
                       WHERE m.thread_id = t.id AND m.hidden = 0
                       ORDER BY m.id DESC LIMIT 1
                   ) AS last_message,
                   (
                       SELECT created_at FROM dm_messages m
                       WHERE m.thread_id = t.id AND m.hidden = 0
                       ORDER BY m.id DESC LIMIT 1
                   ) AS last_message_at,
                   (
                       SELECT COUNT(*) FROM dm_messages m
                       WHERE m.thread_id = t.id AND m.recipient_user_id = ? AND m.read_at IS NULL AND m.hidden = 0
                   ) AS unread_count
            FROM dm_threads t
            WHERE t.user_low_id = ? OR t.user_high_id = ?
            ORDER BY COALESCE(last_message_at, t.updated_at) DESC, t.id DESC
            LIMIT ?
            ''',
            (uid, uid, uid, safe_limit),
        ).fetchall()
        items = []
        for row in rows:
            other_id = row['user_high_id'] if row['user_low_id'] == uid else row['user_low_id']
            other = conn.execute('SELECT * FROM users WHERE id = ?', (other_id,)).fetchone()
            if other is None or _user_row_is_deleted(other):
                continue
            items.append({
                'thread_id': row['id'],
                'user': _basic_social_user(other),
                'last_message': row['last_message'] or '',
                'last_message_at': row['last_message_at'] or row['updated_at'],
                'unread_count': int(row['unread_count'] or 0),
                'friend_status': _friendship_status(conn, uid, other_id),
            })
        total_unread = _dm_unread_count_conn(conn, uid)
        db_slow_log('social', (time.perf_counter() - started) * 1000, 'dm_threads')
        return {'threads': items, 'unread_count': total_unread}, None


def get_dm_messages(user_id, thread_id, mark_read=True, limit=50):
    try:
        uid = int(user_id)
        tid = int(thread_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    safe_limit = max(1, min(int(limit or 50), 50))
    with get_db_connection() as conn:
        thread = conn.execute(
            'SELECT * FROM dm_threads WHERE id = ? AND (user_low_id = ? OR user_high_id = ?)',
            (tid, uid, uid),
        ).fetchone()
        if thread is None:
            return None, '会话不存在'
        other_id = thread['user_high_id'] if thread['user_low_id'] == uid else thread['user_low_id']
        other = conn.execute('SELECT * FROM users WHERE id = ?', (other_id,)).fetchone()
        if other is None or _user_row_is_deleted(other):
            return None, '账号不存在'
        if mark_read:
            mark_key = (uid, tid)
            now_monotonic = time.monotonic()
            last_mark = float(_DM_MARK_READ_LAST_AT.get(mark_key) or 0)
            if now_monotonic - last_mark >= 5:
                unread_row = conn.execute(
                    '''
                    SELECT 1 FROM dm_messages
                    WHERE thread_id = ? AND recipient_user_id = ? AND read_at IS NULL AND hidden = 0
                    LIMIT 1
                    ''',
                    (tid, uid),
                ).fetchone()
                if unread_row is not None:
                    conn.execute(
                        'UPDATE dm_messages SET read_at = ? WHERE thread_id = ? AND recipient_user_id = ? AND read_at IS NULL',
                        (utc_now(), tid, uid),
                    )
                    _DM_MARK_READ_LAST_AT[mark_key] = now_monotonic
        rows = conn.execute(
            '''
            SELECT * FROM dm_messages
            WHERE thread_id = ? AND hidden = 0
            ORDER BY id DESC
            LIMIT ?
            ''',
            (tid, safe_limit),
        ).fetchall()
        conn.commit()
        unread_count = _dm_unread_count_conn(conn, uid)
        return {
            'thread_id': tid,
            'user': _basic_social_user(other),
            'friend_status': _friendship_status(conn, uid, other_id),
            'messages': [_dm_message_row_to_dict(row) for row in reversed(rows)],
            'unread_count': unread_count,
        }, None


def send_dm_message(sender_user_id, target_identifier=None, target_user_id=None, message='', normalized_message='', risk_level=0, hidden=False):
    try:
        sender_id = int(sender_user_id)
    except (TypeError, ValueError):
        return None, '请先登录账号'
    text = str(message or '').strip()
    if not text:
        return None, '消息不能为空'
    with get_db_connection() as conn:
        sender = conn.execute('SELECT * FROM users WHERE id = ?', (sender_id,)).fetchone()
        if sender is None or _user_row_is_deleted(sender):
            return None, '请先登录账号'
        target = None
        if target_user_id is not None:
            try:
                target = conn.execute('SELECT * FROM users WHERE id = ? AND deleted_at IS NULL', (int(target_user_id),)).fetchone()
            except (TypeError, ValueError):
                target = None
        if target is None:
            target = _find_social_target(conn, target_identifier)
        if target is None:
            return None, '账号不存在'
        if _user_row_is_deleted(target):
            return None, '账号不存在'
        target_id = int(target['id'])
        if target_id == sender_id:
            return None, '不能给自己发私信'
        friend_status = _friendship_status(conn, sender_id, target_id)
        thread = _get_or_create_dm_thread(conn, sender_id, target_id)
        if friend_status != 'accepted':
            sent_row = conn.execute(
                '''
                SELECT id FROM dm_messages
                WHERE thread_id = ? AND sender_user_id = ? AND hidden = 0
                LIMIT 1
                ''',
                (thread['id'], sender_id),
            ).fetchone()
            if sent_row is not None:
                return None, '对方尚未同意好友，只能发送一条私信'
        now = utc_now()
        cur = conn.execute(
            '''
            INSERT INTO dm_messages (
                thread_id, sender_user_id, recipient_user_id, message,
                normalized_message, risk_level, created_at, hidden
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                thread['id'], sender_id, target_id, text,
                str(normalized_message or '')[:1000],
                int(risk_level or 0), now, 1 if hidden else 0,
            ),
        )
        conn.execute('UPDATE dm_threads SET updated_at = ? WHERE id = ?', (now, thread['id']))
        _trim_dm_thread_bytes(conn, thread['id'])
        conn.commit()
        row = conn.execute('SELECT * FROM dm_messages WHERE id = ?', (cur.lastrowid,)).fetchone()
        data, _ = get_dm_messages(sender_id, thread['id'], mark_read=False, limit=100)
        data = data or {}
        data['sent_message'] = _dm_message_row_to_dict(row)
        return data, None


def save_match_summary(summary):
    data = dict(summary or {})
    with get_db_connection() as conn:
        cur = conn.execute(
            '''
            INSERT INTO matches (
                mode, started_at, ended_at, duration_seconds, player_names_json, player_ids_json,
                winner_name, winner_index, rounds, mod_source, mod_hash, result, summary_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                data.get('mode'),
                data.get('started_at'),
                data.get('ended_at'),
                data.get('duration_seconds'),
                json.dumps(data.get('players') or [], ensure_ascii=False),
                json.dumps(data.get('player_ids') or [], ensure_ascii=False),
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


def _resolve_user_ids_for_stats(conn, values):
    resolved = []
    seen = set()
    for value in values or []:
        row = None
        try:
            uid = int(value)
            row = conn.execute('SELECT id FROM users WHERE id = ?', (uid,)).fetchone()
        except (TypeError, ValueError):
            name = sanitize_username(value)
            if name:
                row = _find_user_row_by_username_key(conn, name)
        if row is None:
            continue
        uid = int(row['id'])
        if uid in seen:
            continue
        seen.add(uid)
        resolved.append(uid)
    return resolved


def increment_user_stats(users, winners=None, result='finished'):
    if not users:
        return
    is_draw = str(result or '').lower() == 'draw'
    with get_db_connection() as conn:
        user_ids = _resolve_user_ids_for_stats(conn, users)
        winner_values = winners if isinstance(winners, (list, tuple, set)) else [winners]
        winner_ids = set(_resolve_user_ids_for_stats(conn, winner_values))
        if not user_ids:
            return
        for uid in user_ids:
            if is_draw:
                conn.execute(
                    'UPDATE users SET games_played = games_played + 1, draws = draws + 1 WHERE id = ?',
                    (uid,),
                )
            elif uid in winner_ids:
                conn.execute(
                    'UPDATE users SET games_played = games_played + 1, wins = wins + 1 WHERE id = ?',
                    (uid,),
                )
            else:
                conn.execute(
                    'UPDATE users SET games_played = games_played + 1, losses = losses + 1 WHERE id = ?',
                    (uid,),
                )
        conn.commit()


def _gr_k_factor(total_ranked_games):
    games = max(0, int(total_ranked_games or 0))
    if games < 20:
        return 40.0
    if games < 100:
        return 28.0
    return 20.0


def _gr_repeat_factor(repeat_count):
    count = max(0, int(repeat_count or 0))
    ordinal = count + 1
    if ordinal <= 3:
        return 1.0
    if ordinal <= 6:
        return 0.85
    if ordinal <= 10:
        return 0.70
    return 0.50


def _gr_expected(own_rating, opponent_rating):
    return 1.0 / (1.0 + math.pow(10.0, (float(opponent_rating) - float(own_rating)) / 400.0))


def _gr_participants_key(mode, team_a, team_b):
    a = '-'.join(str(v) for v in sorted(team_a))
    b = '-'.join(str(v) for v in sorted(team_b))
    if str(mode or '').lower() == '2v2':
        teams = sorted([a, b])
        return f'2v2:{teams[0]}|{teams[1]}'
    return f'1v1:{min(team_a[0], team_b[0])}-{max(team_a[0], team_b[0])}'


def _gr_match_team_ids(summary):
    raw_ids = summary.get('player_ids') or []
    ids = []
    for value in raw_ids:
        try:
            ids.append(int(value) if value is not None else None)
        except (TypeError, ValueError):
            ids.append(None)
    mode = str(summary.get('mode') or '').lower()
    if mode == '2v2':
        if len(ids) < 4:
            return None, None
        return ids[:2], ids[2:4]
    if len(ids) < 2:
        return None, None
    return [ids[0]], [ids[1]]


def _gr_winner_side_from_summary(summary, team_a, team_b):
    result_text = str(summary.get('result') or '').lower()
    if result_text == 'draw':
        return None, True
    try:
        winner_index = int(summary.get('winner_index')) if summary.get('winner_index') is not None else None
    except (TypeError, ValueError):
        winner_index = None
    if winner_index is not None and winner_index < 0:
        return None, True
    winner_ids = set()
    for value in summary.get('winner_user_ids') or []:
        try:
            if value is not None:
                winner_ids.add(int(value))
        except (TypeError, ValueError):
            pass
    if winner_ids and winner_ids.issubset(set(team_a)):
        return 0, False
    if winner_ids and winner_ids.issubset(set(team_b)):
        return 1, False
    mode = str(summary.get('mode') or '').lower()
    if mode == '2v2' and winner_index in (0, 1):
        return winner_index, False
    if mode != '2v2' and winner_index in (0, 1):
        return winner_index, False
    return None, False


def _gr_prepare_match_summary(conn, row, user_ids, username_key_to_id):
    summary = _safe_json_loads(row['summary_json'], {})
    mode = str(row['mode'] or summary.get('mode') or '').lower()
    summary['mode'] = mode
    summary['result'] = str(row['result'] or summary.get('result') or '').lower()
    summary['winner_index'] = row['winner_index'] if row['winner_index'] is not None else summary.get('winner_index')
    summary['ended_at'] = row['ended_at'] or summary.get('ended_at') or row['started_at'] or summary.get('started_at') or utc_now()
    summary['duration_seconds'] = row['duration_seconds'] or summary.get('duration_seconds') or 0
    normalized_player_ids, recovered = _match_player_ids_for_stats(conn, row, user_ids, username_key_to_id)
    summary['player_ids'] = normalized_player_ids
    winner_ids, is_draw = _match_winner_user_ids_for_stats(row, summary, normalized_player_ids)
    summary['winner_user_ids'] = sorted(winner_ids)
    if is_draw:
        summary['result'] = 'draw'
        summary['winner_index'] = -1
    return summary, recovered


def _simulate_gr_from_matches(conn):
    user_columns = {row['name'] for row in conn.execute('PRAGMA table_info(users)').fetchall()}
    user_where = 'WHERE deleted_at IS NULL' if 'deleted_at' in user_columns else ''
    user_rows = conn.execute(f'SELECT id, username FROM users {user_where}').fetchall()
    user_ids = {int(row['id']) for row in user_rows}
    username_key_to_id = {}
    for row in user_rows:
        key = normalize_username_key(row['username'])
        if key and key not in username_key_to_id:
            username_key_to_id[key] = int(row['id'])
    ratings = {
        uid: {
            'season_gr': float(GR_INITIAL),
            'total_gr': float(GR_INITIAL),
            'highest_gr': float(GR_INITIAL),
            'season_ranked_games': 0,
            'total_ranked_games': 0,
        }
        for uid in user_ids
    }
    skip_reasons = {}
    recovered_player_refs = 0
    counted = 0
    match_results = []
    repeat_counts = {}

    def skip(reason):
        skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

    rows = conn.execute(
        '''
        SELECT * FROM matches
        ORDER BY COALESCE(ended_at, started_at), id
        '''
    ).fetchall()
    season = current_gr_season()
    for row in rows:
        summary, recovered = _gr_prepare_match_summary(conn, row, user_ids, username_key_to_id)
        recovered_player_refs += recovered
        if summary.get('result') not in ('win', 'draw', 'finished'):
            skip('abnormal_result')
            continue
        mode = str(summary.get('mode') or '').lower()
        if mode not in ('1v1', '2v2'):
            skip('unsupported_mode')
            continue
        try:
            duration = int(summary.get('duration_seconds') or 0)
        except (TypeError, ValueError):
            duration = 0
        if duration < RANKING_MIN_DURATION_SECONDS:
            skip('too_short')
            continue
        if _match_has_action_counts_for_stats(summary):
            side_counts = _match_side_action_counts_for_stats(summary, mode)
            if len(side_counts) < 2 or any(int(value or 0) < RANKING_MIN_ACTIONS_PER_SIDE for value in side_counts[:2]):
                skip('not_enough_actions')
                continue
        team_a, team_b = _gr_match_team_ids(summary)
        if not team_a or not team_b:
            skip('missing_player_ids')
            continue
        if any(value is None or value not in user_ids for value in team_a + team_b):
            skip('guest_or_unknown_player')
            continue
        all_ids = team_a + team_b
        if len(set(all_ids)) != len(all_ids):
            skip('duplicate_player')
            continue
        winner_side, is_draw = _gr_winner_side_from_summary(summary, team_a, team_b)
        if winner_side is None and not is_draw:
            skip('unknown_winner')
            continue
        try:
            played_dt = datetime.fromisoformat(str(summary.get('ended_at') or '').replace('Z', '+00:00')).astimezone(timezone.utc)
        except Exception:
            played_dt = datetime.now(timezone.utc)
        played_at = utc_iso(played_dt)
        day_key = played_dt.date().isoformat()
        participant_key = _gr_participants_key(mode, team_a, team_b)
        repeat_key = (day_key, mode, participant_key)
        repeat_count = repeat_counts.get(repeat_key, 0)
        repeat_counts[repeat_key] = repeat_count + 1
        repeat_factor = _gr_repeat_factor(repeat_count)
        mode_factor = GR_2V2_FACTOR if mode == '2v2' else 1.0
        team_a_season = sum(ratings[uid]['season_gr'] for uid in team_a) / len(team_a)
        team_b_season = sum(ratings[uid]['season_gr'] for uid in team_b) / len(team_b)
        team_a_total = sum(ratings[uid]['total_gr'] for uid in team_a) / len(team_a)
        team_b_total = sum(ratings[uid]['total_gr'] for uid in team_b) / len(team_b)
        before = {}
        after = {}
        season_deltas = {}
        total_deltas = {}
        for uid in all_ids:
            on_a = uid in team_a
            season_expected = _gr_expected(team_a_season if on_a else team_b_season, team_b_season if on_a else team_a_season)
            total_expected = _gr_expected(team_a_total if on_a else team_b_total, team_b_total if on_a else team_a_total)
            score = 0.5 if is_draw else (1.0 if (winner_side == 0 and on_a) or (winner_side == 1 and not on_a) else 0.0)
            k = _gr_k_factor(ratings[uid]['total_ranked_games'])
            season_delta = k * mode_factor * repeat_factor * (score - season_expected)
            total_delta = k * mode_factor * repeat_factor * (score - total_expected)
            before[str(uid)] = {
                'season_gr': round(ratings[uid]['season_gr'], 1),
                'total_gr': round(ratings[uid]['total_gr'], 1),
            }
            ratings[uid]['season_gr'] = max(0.0, ratings[uid]['season_gr'] + season_delta)
            ratings[uid]['total_gr'] = max(0.0, ratings[uid]['total_gr'] + total_delta)
            ratings[uid]['season_ranked_games'] += 1
            ratings[uid]['total_ranked_games'] += 1
            ratings[uid]['highest_gr'] = max(ratings[uid]['highest_gr'], ratings[uid]['season_gr'], ratings[uid]['total_gr'])
            after[str(uid)] = {
                'season_gr': round(ratings[uid]['season_gr'], 1),
                'total_gr': round(ratings[uid]['total_gr'], 1),
            }
            season_deltas[str(uid)] = round(season_delta, 1)
            total_deltas[str(uid)] = round(total_delta, 1)
        counted += 1
        result_payload = {
            'applied': True,
            'season_id': season['id'],
            'repeat_count': repeat_count,
            'repeat_factor': repeat_factor,
            'season_deltas': season_deltas,
            'total_deltas': total_deltas,
            'before': before,
            'after': after,
        }
        match_results.append({
            'match_id': int(row['id']),
            'summary': summary,
            'season_id': season['id'],
            'mode': mode,
            'played_at': played_at,
            'participant_ids': all_ids,
            'team_a': team_a,
            'team_b': team_b,
            'winner_side': winner_side,
            'is_draw': is_draw,
            'repeat_count': repeat_count,
            'repeat_factor': repeat_factor,
            'result_payload': result_payload,
        })
    changed = []
    for uid, values in ratings.items():
        if values['total_ranked_games'] <= 0:
            continue
        changed.append({
            'user_id': uid,
            **values,
            'delta': values['total_gr'] - GR_INITIAL,
        })
    changed.sort(key=lambda item: abs(item['delta']), reverse=True)
    return {
        'users': len(user_ids),
        'matches': len(rows),
        'counted_matches': counted,
        'skipped_matches': len(rows) - counted,
        'skip_reasons': skip_reasons,
        'recovered_player_refs': recovered_player_refs,
        'ratings': ratings,
        'changed': changed,
        'match_results': match_results,
        'season': season,
    }


def rebuild_gr_from_matches(dry_run=True):
    with get_db_connection() as conn:
        result = _simulate_gr_from_matches(conn)
        if dry_run:
            preview = dict(result)
            preview.pop('ratings', None)
            preview.pop('match_results', None)
            return preview
        season = result['season']
        conn.execute(f'''
            UPDATE users
            SET total_gr = ?,
                season_gr = ?,
                highest_gr = ?,
                total_ranked_games = 0,
                season_ranked_games = 0,
                gr_season_id = ?
            ''', (GR_INITIAL, GR_INITIAL, GR_INITIAL, season['id']))
        conn.execute('DELETE FROM gr_match_results')
        conn.execute('DELETE FROM gr_daily_snapshots')
        for uid, values in result['ratings'].items():
            conn.execute(
                '''
                UPDATE users
                SET season_gr = ?,
                    total_gr = ?,
                    highest_gr = ?,
                    season_ranked_games = ?,
                    total_ranked_games = ?,
                    gr_season_id = ?
                WHERE id = ?
                ''',
                (
                    values['season_gr'],
                    values['total_gr'],
                    values['highest_gr'],
                    values['season_ranked_games'],
                    values['total_ranked_games'],
                    season['id'],
                    uid,
                ),
            )
        for item in result['match_results']:
            payload = item['result_payload']
            conn.execute(
                '''
                INSERT INTO gr_match_results (
                    match_id, season_id, mode, played_at, participant_ids_json, team_a_ids_json, team_b_ids_json,
                    winner_side, is_draw, repeat_count, repeat_factor, total_deltas_json, season_deltas_json,
                    before_json, after_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    item['match_id'],
                    item['season_id'],
                    item['mode'],
                    item['played_at'],
                    json.dumps(item['participant_ids']),
                    json.dumps(item['team_a']),
                    json.dumps(item['team_b']),
                    item['winner_side'],
                    1 if item['is_draw'] else 0,
                    item['repeat_count'],
                    item['repeat_factor'],
                    json.dumps(payload['total_deltas'], ensure_ascii=False),
                    json.dumps(payload['season_deltas'], ensure_ascii=False),
                    json.dumps(payload['before'], ensure_ascii=False),
                    json.dumps(payload['after'], ensure_ascii=False),
                ),
            )
            summary = dict(item['summary'] or {})
            summary['gr_result'] = payload
            conn.execute(
                'UPDATE matches SET summary_json = ? WHERE id = ?',
                (json.dumps(summary, ensure_ascii=False), item['match_id']),
            )
        today = datetime.now(timezone.utc).date().isoformat()
        for uid, values in result['ratings'].items():
            conn.execute(
                '''
                INSERT OR REPLACE INTO gr_daily_snapshots
                    (snapshot_date, user_id, season_id, season_gr, total_gr, season_ranked_games, total_ranked_games, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    today,
                    uid,
                    season['id'],
                    values['season_gr'],
                    values['total_gr'],
                    values['season_ranked_games'],
                    values['total_ranked_games'],
                    utc_now(),
                ),
            )
        conn.commit()
        preview = dict(result)
        preview.pop('ratings', None)
        preview.pop('match_results', None)
        return preview


def apply_gr_match_result(match_id, summary):
    """Apply Garden Rating (GR) for one completed match.

    Returns a payload suitable for match summaries. Guest-participant matches
    intentionally return a non-scoring reason instead of raising.
    """
    data = dict(summary or {})
    if not data.get('valid_for_ranking', True):
        return {'applied': False, 'reason': data.get('ranking_invalid_reason') or 'not_valid_for_ranking'}
    if str(data.get('result') or '').lower() not in ('win', 'draw', 'finished'):
        return {'applied': False, 'reason': 'abnormal_result'}
    mode = str(data.get('mode') or '').lower()
    if mode not in ('1v1', '2v2'):
        return {'applied': False, 'reason': 'unsupported_mode'}
    team_a, team_b = _gr_match_team_ids(data)
    if not team_a or not team_b:
        return {'applied': False, 'reason': 'missing_player_ids'}
    if any(value is None for value in team_a + team_b):
        return {'applied': False, 'reason': 'guest_participant'}
    all_ids = team_a + team_b
    if len(set(all_ids)) != len(all_ids):
        return {'applied': False, 'reason': 'duplicate_player'}
    season = current_gr_season()
    played_at = data.get('ended_at') or utc_now()
    try:
        played_dt = datetime.fromisoformat(str(played_at).replace('Z', '+00:00')).astimezone(timezone.utc)
    except Exception:
        played_dt = datetime.now(timezone.utc)
        played_at = utc_iso(played_dt)
    day_start = played_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    participant_key = _gr_participants_key(mode, team_a, team_b)
    is_draw = str(data.get('result') or '').lower() == 'draw' or int(data.get('winner_index') if data.get('winner_index') is not None else 0) == -1
    winner_side = None
    if not is_draw:
        winner_ids = set()
        for value in data.get('winner_user_ids') or []:
            try:
                winner_ids.add(int(value))
            except (TypeError, ValueError):
                pass
        if winner_ids and winner_ids.issubset(set(team_a)):
            winner_side = 0
        elif winner_ids and winner_ids.issubset(set(team_b)):
            winner_side = 1
        else:
            try:
                idx = int(data.get('winner_index'))
            except (TypeError, ValueError):
                idx = -1
            winner_side = idx if mode == '2v2' and idx in (0, 1) else (0 if idx == 0 else 1 if idx == 1 else None)
        if winner_side is None:
            return {'applied': False, 'reason': 'unknown_winner'}
    with get_db_connection() as conn:
        ensure_current_gr_season_for_conn(conn, all_ids)
        rows = conn.execute(
            f"SELECT * FROM users WHERE id IN ({','.join(['?'] * len(all_ids))})",
            all_ids,
        ).fetchall()
        by_id = {int(row['id']): row for row in rows}
        if len(by_id) != len(all_ids):
            return {'applied': False, 'reason': 'unknown_user'}
        repeat_rows = conn.execute(
            '''
            SELECT participant_ids_json, team_a_ids_json, team_b_ids_json
            FROM gr_match_results
            WHERE played_at >= ? AND played_at < ? AND mode = ?
            ''',
            (utc_iso(day_start), utc_iso(day_end), mode),
        ).fetchall()
        repeat_count = 0
        for row in repeat_rows:
            try:
                a = [int(v) for v in json.loads(row['team_a_ids_json'] or '[]')]
                b = [int(v) for v in json.loads(row['team_b_ids_json'] or '[]')]
            except Exception:
                continue
            if _gr_participants_key(mode, a, b) == participant_key:
                repeat_count += 1
        repeat_factor = _gr_repeat_factor(repeat_count)
        mode_factor = GR_2V2_FACTOR if mode == '2v2' else 1.0
        team_a_season = sum(float(by_id[uid]['season_gr'] or GR_INITIAL) for uid in team_a) / len(team_a)
        team_b_season = sum(float(by_id[uid]['season_gr'] or GR_INITIAL) for uid in team_b) / len(team_b)
        team_a_total = sum(float(by_id[uid]['total_gr'] or GR_INITIAL) for uid in team_a) / len(team_a)
        team_b_total = sum(float(by_id[uid]['total_gr'] or GR_INITIAL) for uid in team_b) / len(team_b)
        before = {}
        after = {}
        season_deltas = {}
        total_deltas = {}
        for uid in all_ids:
            row = by_id[uid]
            on_a = uid in team_a
            season_expected = _gr_expected(team_a_season if on_a else team_b_season, team_b_season if on_a else team_a_season)
            total_expected = _gr_expected(team_a_total if on_a else team_b_total, team_b_total if on_a else team_a_total)
            if is_draw:
                score = 0.5
            else:
                score = 1.0 if (winner_side == 0 and on_a) or (winner_side == 1 and not on_a) else 0.0
            k = _gr_k_factor(row['total_ranked_games'])
            season_delta = k * mode_factor * repeat_factor * (score - season_expected)
            total_delta = k * mode_factor * repeat_factor * (score - total_expected)
            old_season = float(row['season_gr'] or GR_INITIAL)
            old_total = float(row['total_gr'] or GR_INITIAL)
            new_season = max(0.0, old_season + season_delta)
            new_total = max(0.0, old_total + total_delta)
            before[str(uid)] = {
                'season_gr': round(old_season, 1),
                'total_gr': round(old_total, 1),
            }
            after[str(uid)] = {
                'season_gr': round(new_season, 1),
                'total_gr': round(new_total, 1),
            }
            season_deltas[str(uid)] = round(season_delta, 1)
            total_deltas[str(uid)] = round(total_delta, 1)
            conn.execute(
                '''
                UPDATE users
                SET season_gr = ?,
                    total_gr = ?,
                    highest_gr = MAX(COALESCE(highest_gr, ?), ?, ?),
                    season_ranked_games = COALESCE(season_ranked_games, 0) + 1,
                    total_ranked_games = COALESCE(total_ranked_games, 0) + 1,
                    gr_season_id = ?
                WHERE id = ?
                ''',
                (new_season, new_total, GR_INITIAL, new_season, new_total, season['id'], uid),
            )
            conn.execute(
                '''
                INSERT OR REPLACE INTO gr_daily_snapshots
                    (snapshot_date, user_id, season_id, season_gr, total_gr, season_ranked_games, total_ranked_games, created_at)
                VALUES (?, ?, ?, ?, ?, COALESCE((SELECT season_ranked_games FROM users WHERE id = ?), 0),
                        COALESCE((SELECT total_ranked_games FROM users WHERE id = ?), 0), ?)
                ''',
                (played_dt.date().isoformat(), uid, season['id'], new_season, new_total, uid, uid, utc_now()),
            )
        result_payload = {
            'applied': True,
            'season_id': season['id'],
            'repeat_count': repeat_count,
            'repeat_factor': repeat_factor,
            'season_deltas': season_deltas,
            'total_deltas': total_deltas,
            'before': before,
            'after': after,
        }
        conn.execute(
            '''
            INSERT INTO gr_match_results (
                match_id, season_id, mode, played_at, participant_ids_json, team_a_ids_json, team_b_ids_json,
                winner_side, is_draw, repeat_count, repeat_factor, total_deltas_json, season_deltas_json,
                before_json, after_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                match_id,
                season['id'],
                mode,
                played_at,
                json.dumps(all_ids),
                json.dumps(team_a),
                json.dumps(team_b),
                winner_side,
                1 if is_draw else 0,
                repeat_count,
                repeat_factor,
                json.dumps(total_deltas, ensure_ascii=False),
                json.dumps(season_deltas, ensure_ascii=False),
                json.dumps(before, ensure_ascii=False),
                json.dumps(after, ensure_ascii=False),
            ),
        )
        if match_id:
            data['gr_result'] = result_payload
            conn.execute(
                'UPDATE matches SET summary_json = ? WHERE id = ?',
                (json.dumps(data, ensure_ascii=False), match_id),
            )
        conn.commit()
    return result_payload


def add_user_play_seconds(users, seconds):
    try:
        delta = max(0, int(seconds or 0))
    except (TypeError, ValueError):
        delta = 0
    if not users or delta <= 0:
        return
    with get_db_connection() as conn:
        user_ids = _resolve_user_ids_for_stats(conn, users)
        for uid in user_ids:
            conn.execute(
                'UPDATE users SET play_seconds = COALESCE(play_seconds, 0) + ? WHERE id = ?',
                (delta, uid),
            )
        conn.commit()


def list_user_gr_snapshots(user_id, limit=60):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return []
    safe_limit = max(1, min(int(limit or 60), 180))
    with get_db_connection() as conn:
        ensure_current_gr_season_for_conn(conn, [uid])
        rows = conn.execute(
            '''
            SELECT snapshot_date, season_id, season_gr, total_gr, season_ranked_games, total_ranked_games, created_at
            FROM gr_daily_snapshots
            WHERE user_id = ?
            ORDER BY snapshot_date DESC
            LIMIT ?
            ''',
            (uid, safe_limit),
        ).fetchall()
        if not rows:
            user = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
            if user is not None:
                today = datetime.now(timezone.utc).date().isoformat()
                conn.execute(
                    '''
                    INSERT OR REPLACE INTO gr_daily_snapshots
                        (snapshot_date, user_id, season_id, season_gr, total_gr, season_ranked_games, total_ranked_games, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        today,
                        uid,
                        user['gr_season_id'] if 'gr_season_id' in user.keys() else current_gr_season()['id'],
                        float(user['season_gr'] or GR_INITIAL) if 'season_gr' in user.keys() else GR_INITIAL,
                        float(user['total_gr'] or GR_INITIAL) if 'total_gr' in user.keys() else GR_INITIAL,
                        int(user['season_ranked_games'] or 0) if 'season_ranked_games' in user.keys() else 0,
                        int(user['total_ranked_games'] or 0) if 'total_ranked_games' in user.keys() else 0,
                        utc_now(),
                    ),
                )
                rows = conn.execute(
                    '''
                    SELECT snapshot_date, season_id, season_gr, total_gr, season_ranked_games, total_ranked_games, created_at
                    FROM gr_daily_snapshots
                    WHERE user_id = ?
                    ORDER BY snapshot_date DESC
                    LIMIT ?
                    ''',
                    (uid, safe_limit),
                ).fetchall()
        conn.commit()
    return [
        {
            'date': row['snapshot_date'],
            'season_id': row['season_id'],
            'season_gr': round(float(row['season_gr'] or GR_INITIAL), 1),
            'total_gr': round(float(row['total_gr'] or GR_INITIAL), 1),
            'season_ranked_games': int(row['season_ranked_games'] or 0),
            'total_ranked_games': int(row['total_ranked_games'] or 0),
            'created_at': row['created_at'],
        }
        for row in reversed(rows)
    ]


def _insert_today_gr_snapshot(conn, row):
    if row is None:
        return
    season = current_gr_season()
    conn.execute(
        '''
        INSERT OR REPLACE INTO gr_daily_snapshots
            (snapshot_date, user_id, season_id, season_gr, total_gr, season_ranked_games, total_ranked_games, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            datetime.now(timezone.utc).date().isoformat(),
            int(row['id']),
            row['gr_season_id'] if 'gr_season_id' in row.keys() else season['id'],
            float(row['season_gr'] or GR_INITIAL) if 'season_gr' in row.keys() else GR_INITIAL,
            float(row['total_gr'] or GR_INITIAL) if 'total_gr' in row.keys() else GR_INITIAL,
            int(row['season_ranked_games'] or 0) if 'season_ranked_games' in row.keys() else 0,
            int(row['total_ranked_games'] or 0) if 'total_ranked_games' in row.keys() else 0,
            utc_now(),
        ),
    )


def admin_set_user_gr(identifier, scope='season', value=GR_INITIAL, reason=''):
    user = find_user_for_admin(identifier)
    if not user:
        return None, '账号不存在'
    scope_text = str(scope or 'season').strip().lower()
    if scope_text in ('s', 'season', '赛季', 'season_gr'):
        cols = ('season_gr',)
    elif scope_text in ('t', 'total', 'alltime', '总榜', 'total_gr'):
        cols = ('total_gr',)
    elif scope_text in ('both', 'all', '全部', 'both_gr'):
        cols = ('season_gr', 'total_gr')
    else:
        return None, '范围必须是 season、total 或 both'
    try:
        new_value = max(0.0, float(value))
    except (TypeError, ValueError):
        return None, '花阶分必须是数字'
    with get_db_connection() as conn:
        ensure_current_gr_season_for_conn(conn, [user['id']])
        assignments = ', '.join(f'{col} = ?' for col in cols)
        params = [new_value for _ in cols]
        params.extend([GR_INITIAL, new_value, user['id']])
        conn.execute(
            f'''
            UPDATE users
            SET {assignments},
                highest_gr = MAX(COALESCE(highest_gr, ?), ?)
            WHERE id = ?
            ''',
            params,
        )
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()
        _insert_today_gr_snapshot(conn, row)
        conn.commit()
        return row_to_user(row), None


def admin_adjust_user_gr(identifier, scope='season', delta=0, reason=''):
    user = find_user_for_admin(identifier)
    if not user:
        return None, '账号不存在'
    try:
        amount = float(delta)
    except (TypeError, ValueError):
        return None, '调整值必须是数字'
    scope_text = str(scope or 'season').strip().lower()
    if scope_text in ('s', 'season', '赛季', 'season_gr'):
        return admin_set_user_gr(identifier, 'season', float(user.get('season_gr') or GR_INITIAL) + amount, reason=reason)
    if scope_text in ('t', 'total', 'alltime', '总榜', 'total_gr'):
        return admin_set_user_gr(identifier, 'total', float(user.get('total_gr') or GR_INITIAL) + amount, reason=reason)
    if scope_text in ('both', 'all', '全部', 'both_gr'):
        with get_db_connection() as conn:
            ensure_current_gr_season_for_conn(conn, [user['id']])
            conn.execute(
                '''
                UPDATE users
                SET season_gr = MAX(0, COALESCE(season_gr, ?) + ?),
                    total_gr = MAX(0, COALESCE(total_gr, ?) + ?),
                    highest_gr = MAX(
                        COALESCE(highest_gr, ?),
                        MAX(0, COALESCE(season_gr, ?) + ?),
                        MAX(0, COALESCE(total_gr, ?) + ?)
                    )
                WHERE id = ?
                ''',
                (GR_INITIAL, amount, GR_INITIAL, amount, GR_INITIAL, GR_INITIAL, amount, GR_INITIAL, amount, user['id']),
            )
            row = conn.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()
            _insert_today_gr_snapshot(conn, row)
            conn.commit()
            return row_to_user(row), None
    return None, '范围必须是 season、total 或 both'


def admin_snapshot_user_gr(identifier):
    user = find_user_for_admin(identifier)
    if not user:
        return None, '账号不存在'
    with get_db_connection() as conn:
        ensure_current_gr_season_for_conn(conn, [user['id']])
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()
        _insert_today_gr_snapshot(conn, row)
        conn.commit()
        return row_to_user(row), None


def _match_side_action_counts_for_stats(summary, mode=''):
    side_counts = summary.get('valid_action_counts_by_side')
    if isinstance(side_counts, list) and len(side_counts) >= 2:
        try:
            return [int(side_counts[0] or 0), int(side_counts[1] or 0)]
        except (TypeError, ValueError):
            pass
    counts = summary.get('valid_action_counts')
    if not isinstance(counts, dict):
        return [0, 0]
    def _count_for(index):
        return int(counts.get(index, counts.get(str(index), 0)) or 0)
    if str(mode or '').lower() == '2v2':
        return [_count_for(0) + _count_for(1), _count_for(2) + _count_for(3)]
    return [_count_for(0), _count_for(1)]


def _match_has_action_counts_for_stats(summary):
    side_counts = summary.get('valid_action_counts_by_side')
    if isinstance(side_counts, list) and len(side_counts) >= 2:
        return True
    counts = summary.get('valid_action_counts')
    return isinstance(counts, dict)


def _match_winner_user_ids_for_stats(row, summary, player_ids):
    raw_result = str(row['result'] or summary.get('result') or '').lower()
    if raw_result == 'draw':
        return set(), True
    winner_values = summary.get('winner_user_ids')
    winner_ids = set()
    if isinstance(winner_values, list):
        for value in winner_values:
            try:
                if value is not None:
                    winner_ids.add(int(value))
            except (TypeError, ValueError):
                pass
    if winner_ids:
        return winner_ids, False
    try:
        winner_index = int(row['winner_index']) if row['winner_index'] is not None else None
    except (TypeError, ValueError):
        winner_index = None
    if winner_index is None or winner_index < 0:
        return set(), True
    mode = str(row['mode'] or summary.get('mode') or '').lower()
    indices = {0: [0, 1], 1: [2, 3]}.get(winner_index, []) if mode == '2v2' else [winner_index]
    for idx in indices:
        if 0 <= idx < len(player_ids):
            try:
                if player_ids[idx] is not None:
                    winner_ids.add(int(player_ids[idx]))
            except (TypeError, ValueError):
                pass
    return winner_ids, False


def _match_player_ids_for_stats(conn, row, user_ids, username_key_to_id=None):
    raw_ids = _safe_json_loads(row['player_ids_json'] if 'player_ids_json' in row.keys() else '[]', [])
    raw_names = _safe_json_loads(row['player_names_json'] if 'player_names_json' in row.keys() else '[]', [])
    max_len = max(len(raw_ids) if isinstance(raw_ids, list) else 0, len(raw_names) if isinstance(raw_names, list) else 0)
    normalized = []
    recovered = 0
    for idx in range(max_len):
        uid = None
        if isinstance(raw_ids, list) and idx < len(raw_ids):
            try:
                uid = int(raw_ids[idx]) if raw_ids[idx] is not None else None
            except (TypeError, ValueError):
                uid = None
            if uid not in user_ids:
                uid = None
        if uid is None and isinstance(raw_names, list) and idx < len(raw_names):
            name = sanitize_username(raw_names[idx])
            if name:
                if isinstance(username_key_to_id, dict):
                    uid = username_key_to_id.get(normalize_username_key(name))
                    if uid in user_ids:
                        recovered += 1
                    else:
                        uid = None
                else:
                    row_user = _find_user_row_by_username_key(conn, name)
                    if row_user is not None:
                        uid = int(row_user['id'])
                        if uid in user_ids:
                            recovered += 1
                        else:
                            uid = None
        normalized.append(uid)
    return normalized, recovered


def rebuild_user_stats_from_matches():
    """Recompute account W/L/D from persisted match summaries.

    This is intended for rule migrations, such as making guest-participant
    matches count once they satisfy the normal duration/action thresholds.
    """
    with get_db_connection() as conn:
        user_rows = conn.execute('SELECT id, username FROM users').fetchall()
        user_ids = {int(row['id']) for row in user_rows}
        username_key_to_id = {}
        for row in user_rows:
            key = normalize_username_key(row['username'])
            if key and key not in username_key_to_id:
                username_key_to_id[key] = int(row['id'])
        totals = {uid: {'games_played': 0, 'wins': 0, 'losses': 0, 'draws': 0} for uid in user_ids}
        rows = conn.execute('SELECT * FROM matches ORDER BY id ASC').fetchall()
        counted_matches = 0
        skipped_matches = 0
        recovered_player_refs = 0
        for row in rows:
            summary = _safe_json_loads(row['summary_json'], {})
            if str(row['result'] or summary.get('result') or '').lower() not in ('win', 'draw', 'finished'):
                skipped_matches += 1
                continue
            try:
                duration = int(row['duration_seconds'] or summary.get('duration_seconds') or 0)
            except (TypeError, ValueError):
                duration = 0
            if duration < RANKING_MIN_DURATION_SECONDS:
                skipped_matches += 1
                continue
            if _match_has_action_counts_for_stats(summary):
                side_counts = _match_side_action_counts_for_stats(summary, row['mode'])
                if len(side_counts) < 2 or any(int(value or 0) < RANKING_MIN_ACTIONS_PER_SIDE for value in side_counts[:2]):
                    skipped_matches += 1
                    continue
            normalized_player_ids, recovered = _match_player_ids_for_stats(conn, row, user_ids, username_key_to_id)
            recovered_player_refs += recovered
            participants = [uid for uid in normalized_player_ids if uid in user_ids]
            if not participants:
                skipped_matches += 1
                continue
            winner_ids, is_draw = _match_winner_user_ids_for_stats(row, summary, normalized_player_ids)
            counted_matches += 1
            for uid in participants:
                totals[uid]['games_played'] += 1
                if is_draw:
                    totals[uid]['draws'] += 1
                elif uid in winner_ids:
                    totals[uid]['wins'] += 1
                else:
                    totals[uid]['losses'] += 1
        for uid, stats in totals.items():
            conn.execute(
                'UPDATE users SET games_played = ?, wins = ?, losses = ?, draws = ? WHERE id = ?',
                (stats['games_played'], stats['wins'], stats['losses'], stats['draws'], uid),
            )
        conn.commit()
        return {
            'users': len(totals),
            'matches': len(rows),
            'counted_matches': counted_matches,
            'skipped_matches': skipped_matches,
            'recovered_player_refs': recovered_player_refs,
        }


def rebuild_user_play_seconds_from_matches():
    with get_db_connection() as conn:
        user_rows = conn.execute('SELECT id, username FROM users').fetchall()
        user_ids = {int(row['id']) for row in user_rows}
        username_key_to_id = {}
        for row in user_rows:
            key = normalize_username_key(row['username'])
            if key and key not in username_key_to_id:
                username_key_to_id[key] = int(row['id'])
        totals = {uid: 0 for uid in user_ids}
        rows = conn.execute('SELECT * FROM matches ORDER BY id ASC').fetchall()
        counted_matches = 0
        recovered_player_refs = 0
        for row in rows:
            try:
                duration = max(0, int(row['duration_seconds'] or 0))
            except (TypeError, ValueError):
                duration = 0
            if duration <= 0:
                continue
            player_ids, recovered = _match_player_ids_for_stats(conn, row, user_ids, username_key_to_id)
            recovered_player_refs += recovered
            added = False
            for value in player_ids:
                uid = value
                if uid in totals:
                    totals[uid] += duration
                    added = True
            if added:
                counted_matches += 1
        for uid, seconds in totals.items():
            conn.execute(
                'UPDATE users SET play_seconds = ? WHERE id = ?',
                (int(seconds), uid),
            )
        conn.commit()
        return {
            'users': len(totals),
            'matches': len(rows),
            'counted_matches': counted_matches,
            'total_seconds': sum(totals.values()),
            'recovered_player_refs': recovered_player_refs,
        }
