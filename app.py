try:
    import eventlet
    eventlet.monkey_patch()
except Exception:
    eventlet = None

import sys
import os
import io
import re
import time
import json
import math
import random
import threading
import copy
import shutil
import shlex
import difflib
import hashlib
import secrets
import platform
import subprocess
import sqlite3
import traceback
from functools import wraps
from collections import deque, OrderedDict
from datetime import datetime, timedelta, timezone

from flask import Flask, render_template, jsonify, request, send_from_directory, send_file, session, g
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import check_password_hash
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from game_engine_urf import GameEngineInfiniteFire
from cards import (
    CardDef, CardInstance, CARD_DEFS, DRAFT_RATIO, DECK_SIZE, build_draft_pool, generate_draft_options,
    create_random_weighted_deck_def_ids, ALL_MOD_SHARED_CARD_IDS,
    INITIAL_HEALTH, INITIAL_ELIXIR, INITIAL_MAGIC, FIRST_PLAYER_ELIXIR,
    SECOND_PLAYER_HEALTH, INITIAL_HAND_SIZE, FIRST_PLAYER_HAND_SIZE, ERROR_CARD_ID,
    normalize_card_flag, normalize_card_flags,
)
from mod_loader import (
    GAME_VERSION,
    get_mod_asset,
    invalidate_mod_cache,
    load_all_mods,
    merge_mod_cards_to_card_defs,
    mod_category,
    mod_display_order_key,
    sort_mods_for_display,
)
from mod_loadout_v2 import build_v2_loadout
from mod_spec_v2 import sha256_json
from font_subsets import ensure_community_font_subset
from card_i18n import apply_card_i18n_defaults, card_text, event_text
from runtime_errors import set_mod_runtime_error_logger
from r2_mods import (
    R2ConfigError,
    create_presigned_mod_upload,
    delete_community_mod,
    get_community_index,
    get_r2_health_snapshot,
    list_repository_objects,
    load_community_mod,
    permanently_delete_repository_object,
    record_r2_failure,
    register_community_mod,
    validate_community_mod_url,
    fetch_json_from_public_url,
)
from db import (
    DB_PATH,
    add_user_play_seconds,
    admin_change_username,
    admin_clear_user_role,
    admin_grant_user_achievement,
    admin_adjust_user_gr,
    admin_change_user_password,
    admin_set_user_gr,
    admin_set_user_ban,
    admin_set_user_role,
    admin_snapshot_user_gr,
    adjust_user_thorn_dew,
    award_match_thorn_dew,
    add_friend_request,
    apply_gr_match_result,
    change_username,
    change_user_password,
    cleanup_expired_friend_requests_once,
    cleanup_expired_content_disables_once,
    cleanup_old_dm_messages_once,
    create_report_entry,
    create_remember_token,
    create_user,
    current_gr_season,
    db_slow_log,
    dm_unread_count,
    find_user_for_admin,
    format_duration_zh,
    feedback_is_staff,
    feedback_unread_count,
    get_dm_messages,
    get_feedback_messages,
    get_admin_user_detail,
    get_chat_message_with_context,
    get_db_connection,
    get_leaderboard_rank,
    get_ip_ban_status,
    get_active_user_warnings,
    get_user_ban_status,
    get_user_thorn_dew,
    get_report_detail,
    get_user_by_id,
    get_user_role_profile,
    get_user_by_username,
    get_user_thorn_dew_center,
    get_user_achievement_center,
    is_user_muted_db,
    list_friends,
    list_content_disables,
    list_lobby_chat_entries,
    list_dm_threads,
    list_feedback_threads,
    list_leaderboard,
    list_user_gr_snapshots,
    list_card_draft_stats,
    list_opening_event_stats,
    list_ip_bans,
    list_active_moderation_records,
    list_user_recent_ips,
    list_reports,
    list_user_roles,
    list_user_thorn_dew_transactions,
    claim_user_daily_checkin,
    begin_user_online_session,
    mark_user_last_seen,
    mark_friend_notifications_read_for_user,
    normalize_skin_config,
    normalize_username_key,
    preview_gr_match_result,
    process_live_achievement_flags,
    process_match_achievements,
    record_chat_message,
    record_user_ip_event,
    record_card_draft_counts,
    record_card_draft_win_result,
    record_opening_event_pick_counts,
    record_opening_event_win_result,
    rebuild_card_draft_win_stats_from_matches,
    backfill_achievements_from_matches,
    backfill_match_thorn_dew_from_matches,
    rebuild_gr_from_matches,
    rebuild_user_stats_from_matches,
    rebuild_user_play_seconds_from_matches,
    remove_friend,
    revoke_remember_token,
    resolve_report_entry,
    respond_friend_request,
    increment_user_stats,
    init_db,
    list_admin_users,
    list_achievement_definitions,
    save_match_summary,
    send_dm_message,
    send_feedback_message,
    set_ip_ban,
    set_user_mute,
    spend_user_thorn_dew,
    soft_delete_user,
    upsert_content_disable,
    deactivate_content_disable,
    update_user_skin,
    update_user_social_settings,
    update_feedback_status,
    update_active_ip_ban,
    update_active_user_ban,
    update_user_warning,
    verify_remember_token,
    verify_user,
)
from moderation import (
    REPORT_CATEGORIES,
    VALID_MODERATION_ACTIONS,
    VALID_REPORT_ACTIONS,
    VALID_REPORT_OBJECT_TYPES,
    check_message_risk,
    check_nickname_risk,
    normalize_message,
    report_category_allowed,
)
from replay_core import (
    build_replay_download_package,
    CLEANUP_HOUR,
    CLEANUP_MINUTE,
    DEFAULT_RETENTION_DAYS,
    checkpoint_db,
    cleanup_old_replays,
    cleanup_orphan_replay_blobs,
    export_replay_json_file,
    format_replay_id,
    get_replay,
    get_replay_admin_detail,
    hold_replay,
    list_replays,
    normalize_replay_id,
    release_replay_hold,
    replay_visible_to_user,
    replay_timeline,
    save_replay_snapshot,
    storage_summary,
    vacuum_db,
)
from security import (
    is_muted,
    mute_remaining_seconds,
    mute_user,
    rate_limiter,
    recent_suspicious_events,
    record_illegal_operation,
    record_suspicious_event,
    validate_int,
    validate_str,
)

BASE_CARD_IDS = set(CARD_DEFS.keys())
BASE_CARD_DEFS = copy.deepcopy(CARD_DEFS)
VANILLA_MOD_FILENAME = 'Vanilla Cards.gtnmod'
RETIRED_OFFICIAL_MOD_FILENAMES = {
    'Troll Cards.gtnmod',
    'Thorn Cards.gtnmod',
}
DEFAULT_ENABLED_OFFICIAL_MOD_FILENAMES = {
    VANILLA_MOD_FILENAME,
}
BUILTIN_SETUP_CARD_IDS = set(GameEngine.BUILTIN_SETUP_CARD_IDS)
REQUIRED_CARD_TYPES = ('thorn', 'bloom', 'root', 'guard')
PVP_MODES = ('1v1', '2v2', 'urf', 'random_deck')
DUEL_INVITE_MODES = ('1v1', 'urf', 'random_deck')
CHAT_CACHE_LIMIT = 1000
LOBBY_CHAT_VISIBLE_LIMIT = 300
ADMIN_GAME_CHAT_VISIBLE_LIMIT = 500

try:
    merged = merge_mod_cards_to_card_defs()
    apply_card_i18n_defaults(CARD_DEFS)
    print(f'[startup] mods loaded, merged {len(merged)} cards')
except Exception as e:
    apply_card_i18n_defaults(CARD_DEFS)
    print(f'[startup] mod loading failed: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()

_MODS_SIGNATURE = None
COMMUNITY_CARD_SOURCES = {}

_PUBLIC_DATA_CACHE_SECONDS = 300.0
_PUBLIC_DATA_CACHE_MAX_ENTRIES = 16
_PUBLIC_DATA_CACHE = OrderedDict()
_PUBLIC_DATA_CACHE_LOCK = threading.Lock()


def _public_data_query_key():
    return tuple(
        (key, tuple(request.args.getlist(key)))
        for key in sorted(request.args.keys())
    )


def _public_data_disable_key(rows):
    return tuple(sorted(
        (
            str(row.get('content_type') or ''),
            str(row.get('content_id') or ''),
            str(row.get('scope_mode') or ''),
            str(row.get('expires_at') or ''),
            str(row.get('reason') or ''),
        )
        for row in (rows or [])
    ))


def _public_data_cache_get(namespace, key):
    full_key = (namespace, key)
    now = time.monotonic()
    with _PUBLIC_DATA_CACHE_LOCK:
        entry = _PUBLIC_DATA_CACHE.get(full_key)
        if entry is None or now - float(entry.get('at') or 0) >= _PUBLIC_DATA_CACHE_SECONDS:
            if entry is not None:
                _PUBLIC_DATA_CACHE.pop(full_key, None)
            return None
        _PUBLIC_DATA_CACHE.move_to_end(full_key)
        cached = dict(entry)
    etag = str(cached.get('etag') or '')
    if etag and request.if_none_match.contains(etag):
        response = app.response_class(status=304)
    else:
        response = app.response_class(cached.get('body') or b'{}', mimetype='application/json')
    if etag:
        response.set_etag(etag)
    response.headers['Cache-Control'] = 'private, max-age=60, stale-while-revalidate=300'
    response.headers['X-GTN-Data-Cache'] = 'hit'
    return response


def _public_data_cache_put(namespace, key, payload):
    body = app.json.dumps(payload, separators=(',', ':')).encode('utf-8')
    etag = hashlib.sha256(body).hexdigest()
    full_key = (namespace, key)
    with _PUBLIC_DATA_CACHE_LOCK:
        _PUBLIC_DATA_CACHE[full_key] = {
            'at': time.monotonic(),
            'body': body,
            'etag': etag,
        }
        _PUBLIC_DATA_CACHE.move_to_end(full_key)
        while len(_PUBLIC_DATA_CACHE) > _PUBLIC_DATA_CACHE_MAX_ENTRIES:
            _PUBLIC_DATA_CACHE.popitem(last=False)
    if request.if_none_match.contains(etag):
        response = app.response_class(status=304)
    else:
        response = app.response_class(body, mimetype='application/json')
    response.set_etag(etag)
    response.headers['Cache-Control'] = 'private, max-age=60, stale-while-revalidate=300'
    response.headers['X-GTN-Data-Cache'] = 'miss'
    return response


def current_mods_signature():
    mods_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mods')
    if not os.path.isdir(mods_dir):
        return ()
    items = []
    for filename in sorted(os.listdir(mods_dir)):
        if not filename.endswith(('.json', '.gtnmod')):
            continue
        path = os.path.join(mods_dir, filename)
        try:
            stat = os.stat(path)
            items.append((filename, stat.st_mtime_ns, stat.st_size))
        except OSError:
            items.append((filename, 0, 0))
    return tuple(items)


def reload_mod_card_defs(force=False):
    global _MODS_SIGNATURE
    signature = current_mods_signature()
    if not force and signature == _MODS_SIGNATURE:
        return []
    # File signatures and parsed-package caches are independent. Clear both so
    # replaced locale documents are visible without restarting the process.
    invalidate_mod_cache()
    CARD_DEFS.clear()
    CARD_DEFS.update(copy.deepcopy(BASE_CARD_DEFS))
    COMMUNITY_CARD_SOURCES.clear()
    merged = merge_mod_cards_to_card_defs()
    apply_card_i18n_defaults(CARD_DEFS)
    _MODS_SIGNATURE = signature
    return merged


_MODS_SIGNATURE = current_mods_signature()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'garden_of_thorn_secret')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=int(os.environ.get('GTN_SESSION_DAYS', '30')))
REMEMBER_COOKIE_NAME = 'gtn_remember'


def _normalize_instance(value):
    normalized = str(value or 'release').strip().lower()
    return normalized if normalized in {'release', 'beta'} else 'release'


GTN_INSTANCE = _normalize_instance(os.environ.get('GTN_INSTANCE', 'release'))
GTN_RELEASE_PUBLIC_URL = os.environ.get('GTN_RELEASE_PUBLIC_URL', '').strip()
GTN_BETA_PUBLIC_URL = os.environ.get('GTN_BETA_PUBLIC_URL', '').strip()
_default_bind_host = '127.0.0.1'
GTN_BIND_HOST = os.environ.get('GTN_BIND_HOST', _default_bind_host).strip() or _default_bind_host
GTN_PORT = int(os.environ.get('PORT', os.environ.get('GTN_PORT', '5000')) or 5000)
GTN_INSTANCE_ID = os.environ.get('GTN_INSTANCE_ID', f'{GTN_INSTANCE}-{GTN_PORT}').strip() or f'{GTN_INSTANCE}-{GTN_PORT}'
GTN_VERSION = os.environ.get('GTN_VERSION', GAME_VERSION).strip() or GAME_VERSION
GTN_GIT_SHA = os.environ.get('GTN_GIT_SHA', '').strip()
GTN_STATIC_CACHE_BUST = 'ui-20260719-tutorial-1'
_GTN_STATIC_VERSION_BASE = os.environ.get('GTN_STATIC_VERSION', GTN_VERSION).strip() or GTN_VERSION
GTN_STATIC_VERSION = f'{_GTN_STATIC_VERSION_BASE}-{GTN_STATIC_CACHE_BUST}'
GTN_DRAIN_FILE = os.environ.get('GTN_DRAIN_FILE', os.path.join('/tmp', f'gtn-{GTN_INSTANCE_ID}.drain')).strip()
GTN_DRAINING_ENV = os.environ.get('GTN_DRAINING', '').strip().lower()
_DRAIN_OVERRIDE = None
CHANGELOG_PATH = os.environ.get('GTN_CHANGELOG_PATH', os.path.join(os.path.dirname(__file__), 'CHANGELOG.txt')).strip()


def is_beta_instance():
    return GTN_INSTANCE == 'beta'


def is_release_instance():
    return GTN_INSTANCE == 'release'


_CHANGELOG_DATE_RE = re.compile(r'^\s*(\d{4}-\d{2}-\d{2})\s*$')


def read_changelog_items(limit=20):
    try:
        limit = max(1, min(int(limit or 20), 50))
    except (TypeError, ValueError):
        limit = 20
    try:
        with open(CHANGELOG_PATH, 'r', encoding='utf-8') as fh:
            lines = fh.read().splitlines()
    except FileNotFoundError:
        return []
    except OSError as exc:
        admin_event('error', f'changelog_read_failed path={CHANGELOG_PATH} error={exc}')
        return []

    items = []
    current = None
    body = []
    for line in lines:
        match = _CHANGELOG_DATE_RE.match(line)
        if match:
            if current:
                content = '\n'.join(body).strip()
                if content:
                    items.append({'date': current, 'content': content})
            current = match.group(1)
            body = []
            continue
        if current:
            body.append(line.rstrip())
    if current:
        content = '\n'.join(body).strip()
        if content:
            items.append({'date': current, 'content': content})

    items.sort(key=lambda item: item.get('date', ''), reverse=True)
    return items[:limit]


def changelog_version():
    try:
        st = os.stat(CHANGELOG_PATH)
        return f'{int(st.st_mtime)}-{int(st.st_size)}'
    except Exception:
        return ''


def is_instance_draining():
    if _DRAIN_OVERRIDE is not None:
        return bool(_DRAIN_OVERRIDE)
    if GTN_DRAINING_ENV in {'1', 'true', 'yes', 'on', 'drain', 'draining'}:
        return True
    if GTN_DRAIN_FILE:
        try:
            return os.path.exists(GTN_DRAIN_FILE)
        except OSError:
            return False
    return False


def set_instance_draining(value: bool):
    global _DRAIN_OVERRIDE
    _DRAIN_OVERRIDE = bool(value)
    if GTN_DRAIN_FILE:
        try:
            if value:
                with open(GTN_DRAIN_FILE, 'w', encoding='utf-8') as fh:
                    fh.write(f'{iso_now()} {GTN_INSTANCE_ID}\n')
            elif os.path.exists(GTN_DRAIN_FILE):
                os.remove(GTN_DRAIN_FILE)
        except OSError as exc:
            admin_event('warning', f'failed to update drain file {GTN_DRAIN_FILE}: {exc}')


def drain_reject_payload():
    return {
        'reason': '服务器正在静默更新，旧实例不再接收新对局。请刷新进入新版。',
        'draining': True,
        'instance_id': GTN_INSTANCE_ID,
        'instance_port': GTN_PORT,
        'version': GTN_VERSION,
    }


def instance_payload():
    return {
        'instance': GTN_INSTANCE,
        'instance_id': GTN_INSTANCE_ID,
        'instance_port': GTN_PORT,
        'version': GTN_VERSION,
        'static_version': GTN_STATIC_VERSION,
        'draining': is_instance_draining(),
    }


socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet' if eventlet is not None else 'threading',
    ping_interval=int(os.environ.get('GTN_SOCKET_PING_INTERVAL', '25')),
    ping_timeout=int(os.environ.get('GTN_SOCKET_PING_TIMEOUT', '60')),
)

class TrackedLock:
    """Small wrapper around Lock that exposes non-blocking diagnostics."""

    def __init__(self, name):
        self.name = name
        self._lock = threading.Lock()
        self._meta_lock = threading.Lock()
        self._owner = None
        self._depth = 0
        self._acquired_at = None
        self._stack = None

    def acquire(self, *args, **kwargs):
        owner = threading.get_ident()
        with self._meta_lock:
            if self._owner == owner and self._acquired_at is not None:
                self._depth += 1
                return True
        acquired = self._lock.acquire(*args, **kwargs)
        if acquired:
            try:
                stack = traceback.format_stack(limit=10)
            except Exception:
                stack = []
            with self._meta_lock:
                self._owner = owner
                self._depth = 1
                self._acquired_at = time.time()
                self._stack = stack
        return acquired

    def release(self):
        owner = threading.get_ident()
        with self._meta_lock:
            if self._owner == owner and self._depth > 1:
                self._depth -= 1
                return
            if self._owner is not None and self._owner != owner:
                raise RuntimeError(f'{self.name} lock released by non-owner')
            self._owner = None
            self._depth = 0
            self._acquired_at = None
            self._stack = None
        return self._lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False

    def snapshot(self):
        with self._meta_lock:
            acquired_at = self._acquired_at
            stack = list(self._stack or [])
            return {
                'name': self.name,
                'busy': acquired_at is not None,
                'owner': self._owner,
                'depth': self._depth,
                'held_seconds': round(max(0, time.time() - acquired_at), 3) if acquired_at else 0,
                'stack': stack[-8:],
            }


DB_AVAILABLE = True
DB_INIT_ERROR = ''
try:
    init_db()
except Exception as exc:
    DB_AVAILABLE = False
    DB_INIT_ERROR = str(exc)
    print(f'[startup] database init failed: {type(exc).__name__}: {exc}')

_lock = TrackedLock('global_state')
_replay_cleanup_lock = threading.Lock()
_replay_cleanup_started = False
_lobby_idle_cleanup_started = False
_friend_request_cleanup_started = False
_dm_cleanup_started = False
_event_loop_watchdog_started = False
_pending_interaction_watchdog_started = False
_room_timer_worker_started = False
_next_room_id = 0
_COMMUNITY_API_RATE: dict = {}
PENDING_AFK_CHECKS: dict = {}
SERVER_STARTED_AT = time.time()
RECONNECT_TIMEOUT_SEQUENCE = tuple(
    max(0, int(value.strip()))
    for value in os.environ.get('RECONNECT_TIMEOUT_SEQUENCE', '120,60,30,20,10,5').split(',')
    if value.strip()
) or (120, 60, 30, 20, 10, 5)
RECONNECT_TIMEOUT_SECONDS = int(RECONNECT_TIMEOUT_SEQUENCE[0])
BOTH_DISCONNECTED_CLEANUP_SECONDS = int(os.environ.get('BOTH_DISCONNECTED_CLEANUP_SECONDS', '60'))
GAME_OVER_CLEANUP_SECONDS = int(os.environ.get('GAME_OVER_CLEANUP_SECONDS', '300'))
LOBBY_IDLE_TIMEOUT_SECONDS = int(os.environ.get('LOBBY_IDLE_TIMEOUT_SECONDS', '600'))
LOBBY_IDLE_CHECK_SECONDS = int(os.environ.get('LOBBY_IDLE_CHECK_SECONDS', '60'))
AFK_CHECK_TIMEOUT_SECONDS = int(os.environ.get('AFK_CHECK_TIMEOUT_SECONDS', '60'))
AFK_CHECK_HOLD_MIN_MS = int(os.environ.get('AFK_CHECK_HOLD_MIN_MS', '750'))
AFK_CHECK_HOLD_MAX_MS = int(os.environ.get('AFK_CHECK_HOLD_MAX_MS', '2200'))
AFK_AUTO_MIN_SECONDS = int(os.environ.get('AFK_AUTO_MIN_SECONDS', '300'))
AFK_AUTO_MAX_SECONDS = int(os.environ.get('AFK_AUTO_MAX_SECONDS', '600'))
LOBBY_ACTIVITY_IGNORED_EVENTS = {'set_mode'}
DEFAULT_ADMIN_PASSWORD_HASH = 'pbkdf2:sha256:260000$82e7gAIa0D6034Qq$a0c9a5ad6028ce6c8798abc1314bc74b099b2441c3f39c3b3e6255ea2156f06b'
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', DEFAULT_ADMIN_PASSWORD_HASH)
DEFAULT_ADMIN_CONSOLE_PASSWORD_HASH = 'scrypt:32768:8:1$37ezeWM6dBx97XH0$733f3b74ee3092ac5422eb19df05ff626cb251150a74ed3e03a6e7dd7799607d18123cf6e4b7d518e78e50c1700240f34c9411eb52761b1f9d695ff71c4309af'
ADMIN_CONSOLE_PASSWORD_HASH = os.environ.get('ADMIN_CONSOLE_PASSWORD_HASH', DEFAULT_ADMIN_CONSOLE_PASSWORD_HASH)
DEFAULT_HANDLING_PASSWORD_HASH = 'scrypt:32768:8:1$6XzIIWqGawFYwXIn$7edc14f2c68bde8881dfc98df724aaafa88f04236ff1fa461450d6010422ff0129b1cda604bde7d422b355bd2e5d6bb8126e740251cee2722c53a7443fc4f24a'
HANDLING_PASSWORD_HASH = os.environ.get('HANDLING_PASSWORD_HASH', DEFAULT_HANDLING_PASSWORD_HASH)
DEFAULT_BETA_ACCESS_KEY_HASH = 'scrypt:32768:8:1$GIMYfhSs9RpKMGUK$6f592ac96112ce2f7323012956fc2624890779b9f540c4b7601aff88e3635b3aea26157143eb26874b11cbe30f7da33b25e46285f1f547a846a3f12dc740eb0b'
BETA_ACCESS_KEY_HASH = os.environ.get('BETA_ACCESS_KEY_HASH', DEFAULT_BETA_ACCESS_KEY_HASH)
ADMIN_PLAYER_DISPLAY_NAME = 'Stickerbug'
ADMIN_NICKNAME_RESERVED_REASON = 'Admin nickname reserved'
SPECIAL_ACCOUNT_PROFILES = [
    {
        'key': 'admin',
        'display_name': ADMIN_PLAYER_DISPLAY_NAME,
        'special_role': 'admin',
        'special_role_color': 'admin',
        'special_role_sort': 0,
        'is_admin_player': True,
    },
    {
        'key': 'chief_designer_netherdog',
        'display_name': 'NetherDog',
        'special_role': 'chief_designer',
        'special_role_color': 'bloom',
        'special_role_sort': 1,
        'is_admin_player': False,
    },
    {
        'key': 'chief_designer_eric',
        'display_name': 'Eric',
        'special_role': 'chief_designer',
        'special_role_color': 'bloom',
        'special_role_sort': 1,
        'is_admin_player': False,
    },
    {
        'key': 'right_angle_person_winniepooh',
        'display_name': 'WinniePooh',
        'special_role': 'right_angle_person',
        'special_role_color': 'guard',
        'special_role_sort': 2,
        'is_admin_player': False,
    },
]
SPECIAL_PLAYER_PROFILES = SPECIAL_ACCOUNT_PROFILES
BUILTIN_SPECIAL_ACCOUNT_NAMES = {profile['display_name'].lower() for profile in SPECIAL_ACCOUNT_PROFILES}
ADMIN_EVENTS = deque(maxlen=300)
MATCH_HISTORY = deque(maxlen=120)
ADMIN_LOGIN_FAILURES = {}
BETA_LOGIN_FAILURES = {}
AUTH_LOGIN_FAILURES = {}
LOBBY_CHAT_CACHE = {
    'release': deque(maxlen=500),
    'beta': deque(maxlen=500),
}
ADMIN_GAME_CHAT_CACHE = deque(maxlen=500)
SOCIAL_DM_THREADS_CACHE = {}
AUTH_SKIN_SAVE_LAST_AT = {}
LOBBY_CHAT_RATE = {}
LOBBY_CHAT_SEQUENCE = {
    'release': 0,
    'beta': 0,
}
ADMIN_GAME_CHAT_SEQUENCE = 0
CHAT_RATE_WINDOW_SECONDS = 60
CHAT_RATE_LIMIT = 10
CHAT_DISPLAY_WIDTH_LIMIT = 200
CHAT_IDLE_SEPARATOR_SECONDS = 300
MENTION_RATE_LIMIT = 5
CHAT_EXEMPT_NAMES = set()


def _env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return int(default)


def _env_bool(name, default=True):
    value = os.environ.get(name)
    if value is None:
        return bool(default)
    return str(value).strip().lower() not in {'0', 'false', 'no', 'off'}


def db_maintenance_enabled():
    return _env_bool('GTN_DB_MAINTENANCE_ENABLED', True)


_RESOURCE_BREAKDOWN_CACHE = {'ts': 0.0, 'data': None}
_RESOURCE_BREAKDOWN_CACHE_SECONDS = _env_float('GTN_RESOURCE_BREAKDOWN_CACHE_SECONDS', 120)
_RESOURCE_BREAKDOWN_MAX_FILES = _env_int('GTN_RESOURCE_BREAKDOWN_MAX_FILES', 8000)
_RUNTIME_METRICS_CACHE = {'ts': 0.0, 'data': None}
_RUNTIME_METRICS_LOCK = threading.Lock()
_RUNTIME_METRICS_CACHE_SECONDS = _env_float('GTN_RUNTIME_METRICS_CACHE_SECONDS', 2)
_ADMIN_STATUS_CACHE = {'ts': 0.0, 'data': None}
_ADMIN_STATUS_LOCK = threading.Lock()
_ADMIN_STATUS_CACHE_SECONDS = _env_float('GTN_ADMIN_STATUS_CACHE_SECONDS', 5)
_LEADERBOARD_CACHE_SECONDS = 300
_LEADERBOARD_CACHE = {}
_LEADERBOARD_SELF_RANK_CACHE = {}
_LEADERBOARD_CACHE_LOCK = threading.Lock()


def clear_leaderboard_cache():
    try:
        with _LEADERBOARD_CACHE_LOCK:
            _LEADERBOARD_CACHE.clear()
            _LEADERBOARD_SELF_RANK_CACHE.clear()
    except Exception as exc:
        print(f"[leaderboard] clear cache failed: {exc}", flush=True)
_ADMIN_API_SLOW_MS = _env_float('GTN_ADMIN_API_SLOW_MS', 1000)
_SOCKET_ACTION_SLOW_MS = _env_float('GTN_SOCKET_ACTION_SLOW_MS', 500)
_ROOM_ACTION_LOCK_WAIT_SECONDS = _env_float('GTN_ROOM_ACTION_LOCK_WAIT_SECONDS', 0.25)
RANKING_MIN_DURATION_SECONDS = _env_float('GTN_RANKING_MIN_DURATION_SECONDS', 20)
RANKING_MIN_ACTIONS_PER_SIDE = _env_int('GTN_RANKING_MIN_ACTIONS_PER_SIDE', 1)
ACTION_TURN_SECONDS = _env_float('GTN_ACTION_TURN_SECONDS', 60)
ACTION_TURN_CARD_BONUS_SECONDS = _env_float('GTN_ACTION_TURN_CARD_BONUS_SECONDS', 5)
DRAFT_INITIAL_TIMEOUT_SECONDS = _env_float('GTN_DRAFT_INITIAL_TIMEOUT_SECONDS', 90)
DRAFT_PICK_BONUS_SECONDS = _env_float('GTN_DRAFT_PICK_BONUS_SECONDS', 10)
DRAFT_TIMEOUT_SECONDS = _env_float('GTN_DRAFT_TIMEOUT_SECONDS', 240)
EVENT_SELECT_TIMEOUT_SECONDS = _env_float('GTN_EVENT_SELECT_TIMEOUT_SECONDS', 40)
EVENT_REVEAL_TIMEOUT_SECONDS = _env_float('GTN_EVENT_REVEAL_TIMEOUT_SECONDS', 40)
EVENT_SUB_CHOICE_TIMEOUT_SECONDS = _env_float('GTN_EVENT_SUB_CHOICE_TIMEOUT_SECONDS', 60)
ROOM_TIMER_TICK_SECONDS = _env_float('GTN_ROOM_TIMER_TICK_SECONDS', 1)
PREGAME_STATE_RESEND_SECONDS = _env_float('GTN_PREGAME_STATE_RESEND_SECONDS', 8)
_LOBBY_BROADCAST_LOCK = threading.Lock()
_LOBBY_BROADCAST_PENDING = False
_LOBBY_BROADCAST_DIRTY = False
_LOBBY_BROADCAST_DELAY_SECONDS = _env_float('GTN_LOBBY_BROADCAST_DELAY_SECONDS', 0.12)
LAST_LOBBY_UPDATE_AT = None
RESOURCE_HISTORY = deque(maxlen=720)
_RESOURCE_HISTORY_LAST_TS = 0.0
SOCKET_LATENCY_SAMPLES = deque(maxlen=2000)
SOCKET_ACTION_SAMPLES = deque(maxlen=2000)
SOCKET_BROADCAST_SAMPLES = deque(maxlen=1000)
EVENT_LOOP_LAG_SAMPLES = deque(maxlen=1000)
DRAFT_STATS_FLUSH_SECONDS = _env_float('GTN_DRAFT_STATS_FLUSH_SECONDS', 5)
DRAFT_STATS_FLUSH_MAX_PENDING = _env_int('GTN_DRAFT_STATS_FLUSH_MAX_PENDING', 200)
_DRAFT_STATS_LOCK = threading.Lock()
_DRAFT_STATS_PENDING = {}
_OPENING_EVENT_STATS_PENDING = {}
_DRAFT_STATS_PENDING_EVENTS = 0
_DRAFT_STATS_WORKER_STARTED = False
LAST_SEEN_FLUSH_SECONDS = _env_float('GTN_LAST_SEEN_FLUSH_SECONDS', 10)
LAST_SEEN_FLUSH_MAX_PENDING = _env_int('GTN_LAST_SEEN_FLUSH_MAX_PENDING', 100)
_LAST_SEEN_LOCK = threading.Lock()
_LAST_SEEN_PENDING = set()
_LAST_SEEN_WORKER_STARTED = False

try:
    import psutil
    _PSUTIL_PROCESS = psutil.Process(os.getpid())
    psutil.cpu_percent(interval=None)
    _PSUTIL_PROCESS.cpu_percent(interval=None)
except Exception:
    psutil = None
    _PSUTIL_PROCESS = None

players = {}
rooms = {}
invites = {}
solo_sessions = {}
tutorial_sessions = set()
SOLO_HISTORY_LIMIT = 100
teams = {}
pending_team_matches = {}
v2_ui_timers = {}


def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def admin_display_time(value):
    try:
        if isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(value, timezone.utc)
        else:
            text = str(value or '')
            if text.endswith('Z'):
                text = text[:-1] + '+00:00'
            dt = datetime.fromisoformat(text)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None)
        else:
            dt = dt + timedelta(hours=8)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return str(value or '-')


def admin_event(kind, message, **extra):
    entry = {
        'time': iso_now(),
        'kind': kind,
        'message': message,
    }
    if extra:
        entry.update(extra)
    ADMIN_EVENTS.appendleft(entry)


def _admin_identity_for_log():
    user_id = session.get('user_id')
    username = session.get('username') or ('admin' if session.get('admin_authenticated') else '')
    return user_id, username


def log_admin_api_timing(endpoint, elapsed_ms, **extra):
    try:
        g._admin_api_timing_logged = True
    except Exception:
        pass
    user_id, username = _admin_identity_for_log()
    payload = {
        'endpoint': endpoint,
        'elapsed_ms': round(float(elapsed_ms), 1),
        'user_id': user_id,
        'admin': username,
    }
    payload.update(extra)
    line = 'admin_api ' + ' '.join(f'{k}={v}' for k, v in payload.items() if v is not None and v != '')
    if elapsed_ms >= _ADMIN_API_SLOW_MS:
        admin_event('perf', line, **payload)
    print(line, flush=True)


set_mod_runtime_error_logger(
    lambda message, **extra: admin_event('mod_error', message, **extra)
)


def build_match_achievement_flags(room, player_user_ids, winner_player_indices):
    flags = {}
    try:
        engine = getattr(room, 'engine', None)
        if engine is None:
            return flags
        mode = getattr(room, 'mode', '')
        winner_set = {int(v) for v in (winner_player_indices or [])}
        for pidx in range(len(player_user_ids or [])):
            if not (0 <= pidx < len(player_user_ids)):
                continue
            uid = player_user_ids[pidx]
            if uid is None:
                continue
            user_flags = []
            ps = engine.players[pidx] if hasattr(engine, 'players') and pidx < len(engine.players) else None
            is_winner = pidx in winner_set
            if is_winner and mode == '1v1' and ps is not None and (
                bool(getattr(ps, 'invincible', False))
                or bool(getattr(ps, 'bandage_active', False))
                or bool(getattr(ps, 'bandage_death_pending', False))
            ):
                user_flags.append('flag_backwater_win')
            if ps is not None:
                try:
                    engine._note_achievement_status_peak(pidx)
                except Exception:
                    pass
                try:
                    min_health = int(getattr(ps, 'achievement_min_health', getattr(ps, 'health', 999)) or 999)
                except (TypeError, ValueError):
                    min_health = 999
                try:
                    start_health = int((getattr(ps, 'match_start_snapshot', {}) or {}).get('health', getattr(ps, 'max_health', 0)) or 0)
                except (TypeError, ValueError):
                    start_health = 0
                try:
                    final_health = int(getattr(ps, 'health', 0) or 0)
                except (TypeError, ValueError):
                    final_health = 0
                if is_winner and min_health <= 5 and not bool(getattr(ps, 'achievement_invincible_triggered', False)):
                    user_flags.append('flag_one_hp_win')
                if is_winner and bool(getattr(ps, 'achievement_yggdrasil_revived', False)):
                    user_flags.append('flag_revive_leaf_win')
                enemy_defeated_for_win = False
                try:
                    if mode == '2v2' and hasattr(engine, 'team_of'):
                        own_team = engine.team_of(pidx)
                        enemy_indices = [
                            idx for idx in range(len(engine.players))
                            if idx != pidx and engine.team_of(idx) != own_team
                        ]
                    else:
                        enemy_indices = [idx for idx in range(len(engine.players)) if idx != pidx]
                    enemy_defeated_for_win = any(
                        int(getattr(engine.players[idx], 'health', 1) or 0) <= 0
                        for idx in enemy_indices
                    )
                except Exception:
                    enemy_defeated_for_win = False
                if is_winner and enemy_defeated_for_win and not bool(getattr(ps, 'achievement_played_thorn', False)):
                    user_flags.append('flag_no_thorn_win')
                if is_winner and final_health >= start_health > 0:
                    user_flags.append('flag_a_plus_win')
                if is_winner and min_health >= start_health > 0 and int(getattr(engine, 'round_num', 0) or 0) >= 5:
                    user_flags.append('flag_first_five_rounds_clean')
                if is_winner and int(getattr(engine, 'round_num', 0) or 0) <= 4:
                    user_flags.append('flag_blitz_win')
                if int(getattr(ps, 'achievement_max_single_damage_dealt', 0) or 0) >= 60:
                    user_flags.append('flag_one_hit_60')
                if int(getattr(ps, 'achievement_max_cards_played_turn', 0) or 0) >= 15:
                    user_flags.append('flag_15_cards_turn')
                if int(getattr(ps, 'achievement_max_turn_elixir_gained', 0) or 0) >= 15:
                    user_flags.append('flag_15e_turn')
                if int(getattr(ps, 'achievement_total_healed', 0) or 0) >= 100:
                    user_flags.append('flag_heal_100')
                if int(getattr(ps, 'achievement_max_same_instance_plays', 0) or 0) >= 7:
                    user_flags.append('flag_same_card_10')
                if int(getattr(ps, 'achievement_max_same_name_streak', 0) or 0) >= 5:
                    user_flags.append('flag_same_name_streak_5')
                if int(getattr(ps, 'achievement_max_enemy_fire', 0) or 0) >= 30:
                    user_flags.append('flag_fire_30')
                if int(getattr(ps, 'achievement_max_enemy_poison', 0) or 0) >= 30:
                    user_flags.append('flag_poison_30')
                if int(getattr(ps, 'achievement_max_enemy_status_types', 0) or 0) >= 6:
                    user_flags.append('flag_enemy_6_statuses')
                if int(getattr(ps, 'achievement_equipment_destroyed', 0) or 0) >= 7:
                    user_flags.append('flag_equipment_destroy_7')
                if int(getattr(ps, 'achievement_counter_successes', 0) or 0) >= 6:
                    user_flags.append('flag_counter_6')
                if int(getattr(ps, 'achievement_max_enemy_poison_fire_min', 0) or 0) >= 15:
                    user_flags.append('flag_poison_fire_dual_15')
                if int(getattr(ps, 'achievement_min_enemy_card_total', 999999) or 999999) <= 10:
                    user_flags.append('flag_enemy_cards_10')
                if mode != '2v2' and (
                    bool(getattr(ps, 'achievement_team_double_resources', False))
                    or _achievement_duel_double_resources(engine, pidx)
                ):
                    user_flags.append('flag_team_double_resources')
                if int(getattr(ps, 'achievement_max_enemy_attack_blocked', 0) or 0) >= 5:
                    user_flags.append('flag_enemy_attack_blocked_5')
                if int(getattr(ps, 'achievement_max_untargetable', 0) or 0) >= 3:
                    user_flags.append('flag_untargetable_3')
                if int(getattr(ps, 'achievement_max_equipment_count', 0) or 0) >= 4:
                    user_flags.append('flag_max_equipment_5')
                if int(getattr(ps, 'achievement_max_armor', 0) or 0) >= 20:
                    user_flags.append('flag_armor_20')
                if bool(getattr(ps, 'achievement_self_caused_death', False)):
                    user_flags.append('flag_self_caused_death')
                if int((getattr(ps, 'custom_vars', {}) or {}).get('achievement_creative_mode_mana_pool', 0) or 0) > 0:
                    user_flags.append('flag_creative_mode_mana_pool')
                if is_winner and mode == '1v1':
                    enemies = [eid for eid in range(len(engine.players)) if eid != pidx]
                    if any(int(getattr(engine.players[eid], 'health', 1) or 0) == 0 for eid in enemies):
                        user_flags.append('flag_perfect_zero_win')
                    if (
                        any(int(getattr(engine.players[eid], 'health', 1) or 0) <= 0 for eid in enemies)
                        and int(getattr(ps, 'elixir', 0) or 0) == 0
                        and int(getattr(ps, 'magic', 0) or 0) == 0
                    ):
                        user_flags.append('flag_1v1_zero_resources_win')
                if is_winner and mode == '2v2' and hasattr(engine, 'teams') and hasattr(engine, 'team_of'):
                    try:
                        team = engine.teams[engine.team_of(pidx)]
                        if any(
                            mate != pidx
                            and getattr(engine.players[mate], 'achievement_death_round', None) is not None
                            and int(getattr(engine.players[mate], 'achievement_death_round')) <= 6
                            for mate in team
                        ):
                            user_flags.append('flag_last_one_win')
                    except Exception:
                        pass
            flags[str(uid)] = user_flags
    except Exception as exc:
        admin_event('error', f'achievement flag collection failed: {exc}')
    return flags


def _achievement_duel_double_resources(engine, pidx):
    try:
        if engine is None or len(getattr(engine, 'players', []) or []) != 2:
            return False
        if pidx not in (0, 1):
            return False
        enemy_idx = 1 - int(pidx)

        def _stat(idx, attr):
            try:
                return max(0, int(getattr(engine.players[idx], attr, 0) or 0))
            except (TypeError, ValueError):
                return 0

        achieved = (
            _stat(pidx, 'health') >= 2 * _stat(enemy_idx, 'health')
            and _stat(pidx, 'elixir') >= 2 * _stat(enemy_idx, 'elixir')
            and _stat(pidx, 'magic') >= 2 * _stat(enemy_idx, 'magic')
        )
        if achieved:
            try:
                engine.players[pidx].achievement_team_double_resources = True
            except Exception:
                pass
        return achieved
    except Exception:
        return False


LIVE_ACHIEVEMENT_FLAGS = {
    'flag_one_hit_60',
    'flag_15_cards_turn',
    'flag_15e_turn',
    'flag_heal_100',
    'flag_same_card_10',
    'flag_same_name_streak_5',
    'flag_fire_30',
    'flag_poison_30',
    'flag_enemy_6_statuses',
    'flag_equipment_destroy_7',
    'flag_counter_6',
    'flag_poison_fire_dual_15',
    'flag_enemy_cards_10',
    'flag_team_double_resources',
    'flag_enemy_attack_blocked_5',
    'flag_untargetable_3',
    'flag_max_equipment_5',
    'flag_armor_20',
    'flag_self_caused_death',
    'flag_creative_mode_mana_pool',
}


def build_live_achievement_flags(room):
    flags = {}
    try:
        engine = getattr(room, 'engine', None)
        if engine is None or getattr(engine, 'game_over', False):
            return flags
        for pidx, psid in enumerate(getattr(room, 'player_sids', []) or []):
            profile = room_player_profile(room, psid)
            uid = profile.get('user_id')
            if uid is None:
                continue
            ps = engine.players[pidx] if hasattr(engine, 'players') and pidx < len(engine.players) else None
            if ps is None:
                continue
            try:
                engine._note_achievement_status_peak(pidx)
            except Exception:
                pass
            user_flags = []
            if int(getattr(ps, 'achievement_max_single_damage_dealt', 0) or 0) >= 60:
                user_flags.append('flag_one_hit_60')
            if int(getattr(ps, 'achievement_max_cards_played_turn', 0) or 0) >= 15:
                user_flags.append('flag_15_cards_turn')
            if int(getattr(ps, 'achievement_max_turn_elixir_gained', 0) or 0) >= 15:
                user_flags.append('flag_15e_turn')
            if int(getattr(ps, 'achievement_total_healed', 0) or 0) >= 100:
                user_flags.append('flag_heal_100')
            if int(getattr(ps, 'achievement_max_same_instance_plays', 0) or 0) >= 7:
                user_flags.append('flag_same_card_10')
            if int(getattr(ps, 'achievement_max_same_name_streak', 0) or 0) >= 5:
                user_flags.append('flag_same_name_streak_5')
            if int(getattr(ps, 'achievement_max_enemy_fire', 0) or 0) >= 30:
                user_flags.append('flag_fire_30')
            if int(getattr(ps, 'achievement_max_enemy_poison', 0) or 0) >= 30:
                user_flags.append('flag_poison_30')
            if int(getattr(ps, 'achievement_max_enemy_status_types', 0) or 0) >= 6:
                user_flags.append('flag_enemy_6_statuses')
            if int(getattr(ps, 'achievement_equipment_destroyed', 0) or 0) >= 7:
                user_flags.append('flag_equipment_destroy_7')
            if int(getattr(ps, 'achievement_counter_successes', 0) or 0) >= 6:
                user_flags.append('flag_counter_6')
            if int(getattr(ps, 'achievement_max_enemy_poison_fire_min', 0) or 0) >= 15:
                user_flags.append('flag_poison_fire_dual_15')
            if int(getattr(ps, 'achievement_min_enemy_card_total', 999999) or 999999) <= 10:
                user_flags.append('flag_enemy_cards_10')
            if getattr(room, 'mode', '') != '2v2' and (
                bool(getattr(ps, 'achievement_team_double_resources', False))
                or _achievement_duel_double_resources(engine, pidx)
            ):
                user_flags.append('flag_team_double_resources')
            if int(getattr(ps, 'achievement_max_enemy_attack_blocked', 0) or 0) >= 5:
                user_flags.append('flag_enemy_attack_blocked_5')
            if int(getattr(ps, 'achievement_max_untargetable', 0) or 0) >= 3:
                user_flags.append('flag_untargetable_3')
            if int(getattr(ps, 'achievement_max_equipment_count', 0) or 0) >= 4:
                user_flags.append('flag_max_equipment_5')
            if int(getattr(ps, 'achievement_max_armor', 0) or 0) >= 20:
                user_flags.append('flag_armor_20')
            if bool(getattr(ps, 'achievement_self_caused_death', False)):
                user_flags.append('flag_self_caused_death')
            if int((getattr(ps, 'custom_vars', {}) or {}).get('achievement_creative_mode_mana_pool', 0) or 0) > 0:
                user_flags.append('flag_creative_mode_mana_pool')
            if user_flags:
                flags[str(int(uid))] = user_flags
    except Exception as exc:
        admin_event('error', f'live achievement flag collection failed: {exc}', room_id=getattr(room, 'room_id', None))
    return flags


def check_live_achievements(room):
    if not DB_AVAILABLE or room is None:
        return
    try:
        raw_flags = build_live_achievement_flags(room)
        if not raw_flags:
            return
        seen = getattr(room, '_live_achievement_flags_seen', None)
        if seen is None:
            seen = set()
            room._live_achievement_flags_seen = seen
        pending = {}
        for uid, flags in raw_flags.items():
            for flag in flags:
                if flag not in LIVE_ACHIEVEMENT_FLAGS:
                    continue
                key = (str(uid), str(flag))
                if key in seen:
                    continue
                seen.add(key)
                pending.setdefault(str(uid), []).append(str(flag))
        if not pending:
            return
        result = process_live_achievement_flags(pending)
        emit_achievement_unlocks(room, result)
    except Exception as exc:
        admin_event('error', f'live achievement check failed: {exc}', room_id=getattr(room, 'room_id', None))


def emit_achievement_unlocks(room, achievement_result):
    try:
        unlocked = (achievement_result or {}).get('unlocked') or []
        if not unlocked:
            return
        by_user = {}
        for item in unlocked:
            try:
                uid = int(item.get('user_id'))
            except (TypeError, ValueError):
                continue
            by_user.setdefault(uid, []).append({
                'id': item.get('id') or '',
                'name_cn': item.get('name_cn') or item.get('id') or '',
                'name_en': item.get('name_en') or item.get('name_cn') or item.get('id') or '',
                'name_i18n': dict(item.get('name_i18n') or {}),
                'description_cn': item.get('description_cn') or '',
                'description_en': item.get('description_en') or item.get('description_cn') or '',
                'description_i18n': dict(item.get('description_i18n') or {}),
                'type': item.get('type') or ('hidden' if item.get('hidden') else ''),
                'type_color': item.get('type_color') or item.get('color') or '',
                'hidden': bool(item.get('hidden')),
                'reward_dew': int(item.get('reward_dew') or 0),
            })
        if not by_user:
            return
        for sid in getattr(room, 'player_sids', []) or []:
            player = players.get(sid)
            if not player:
                continue
            try:
                uid = int(player.get('user_id') or 0)
            except (TypeError, ValueError):
                continue
            items = by_user.get(uid)
            if items:
                socketio.emit('achievement_unlocked', {'items': items}, room=sid)
    except Exception as exc:
        admin_event('error', f'achievement unlock emit failed: {exc}', room_id=getattr(room, 'room_id', None))


def _format_achievement_unlocked_items(unlocked):
    items = []
    for item in unlocked or []:
        items.append({
            'id': item.get('id') or '',
            'name_cn': item.get('name_cn') or item.get('id') or '',
            'name_en': item.get('name_en') or item.get('name_cn') or item.get('id') or '',
            'name_i18n': dict(item.get('name_i18n') or {}),
            'description_cn': item.get('description_cn') or '',
            'description_en': item.get('description_en') or item.get('description_cn') or '',
            'description_i18n': dict(item.get('description_i18n') or {}),
            'type': item.get('type') or ('hidden' if item.get('hidden') else ''),
            'type_color': item.get('type_color') or item.get('color') or '',
            'hidden': bool(item.get('hidden')),
            'reward_dew': int(item.get('reward_dew') or 0),
        })
    return items


def _positive_int(value):
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


SOLO_STATUS_TOTAL_ATTRS = (
    'poison', 'fire', 'dodge', 'toxic', 'triangle_stacks', 'overload',
    'foresight', 'fracture', 'stagnation', 'blind', 'heal_block',
    'weakness', 'bleed', 'skip_turn', 'attack_blocked', 'attack_only',
    'magic_blocked', 'honey_control_turns', 'untargetable',
)
SOLO_STATUS_TOTAL_EXCLUDED_CUSTOM_KEYS = {
    'jungle:root', 'jungle:root_status', 'root_status',
    'equipment_protection', 'armor',
}


def _solo_player_status_type_count(ps):
    total = 0
    for attr in SOLO_STATUS_TOTAL_ATTRS:
        if _positive_int(getattr(ps, attr, 0)) > 0:
            total += 1
    if bool(getattr(ps, 'invincible', False)):
        total += 1
    if bool(getattr(ps, 'bandage_active', False)):
        total += 1
    if bool(getattr(ps, 'bandage_death_pending', False)):
        total += 1
    custom = getattr(ps, 'custom_statuses', {}) or {}
    if isinstance(custom, dict):
        for key, value in custom.items():
            if str(key) in SOLO_STATUS_TOTAL_EXCLUDED_CUSTOM_KEYS:
                continue
            if _positive_int(value) > 0:
                total += 1
    return total


def check_solo_achievements(sid, engine):
    if not DB_AVAILABLE or not sid or engine is None or sid in tutorial_sessions:
        return
    player = players.get(sid) or {}
    try:
        uid = int(player.get('user_id') or 0)
    except (TypeError, ValueError):
        uid = 0
    if uid <= 0:
        return
    try:
        total = sum(_solo_player_status_type_count(ps) for ps in getattr(engine, 'players', []) or [])
        if total < 25:
            return
        seen = getattr(engine, '_solo_achievement_flags_seen', None)
        if seen is None:
            seen = set()
            engine._solo_achievement_flags_seen = seen
        key = (uid, 'flag_solo_status_25')
        if key in seen:
            return
        seen.add(key)
        result = process_live_achievement_flags({str(uid): ['flag_solo_status_25']})
        items = _format_achievement_unlocked_items((result or {}).get('unlocked') or [])
        if items:
            socketio.emit('achievement_unlocked', {'items': items}, room=sid)
    except Exception as exc:
        admin_event('error', f'solo achievement check failed: {exc}')


def admin_match_record(room, result='finished'):
    try:
        if getattr(room, '_history_recorded', False):
            return
        e = room.engine
        names = []
        player_user_ids = []
        registered_user_ids = []
        participant_meta = []
        for psid in room.player_sids:
            p = room_player_profile(room, psid)
            names.append(p.get('nickname', '?'))
            participant_meta.append(p)
            uid = p.get('user_id')
            player_user_ids.append(uid if uid is not None else None)
        for meta in participant_meta:
            if meta.get('user_id'):
                registered_user_ids.append(meta['user_id'])
        winner = getattr(e, 'winner', None)
        winner_index = None
        stats_winners = []
        stats_winner_user_ids = []
        stats_winner_player_indices = []
        stats_result = 'draw'
        if getattr(e, 'winning_team', None) is not None and int(getattr(e, 'winning_team', -1)) >= 0:
            winner_index = int(e.winning_team)
            team_members = []
            try:
                team_members = list(e.teams[winner_index])
            except Exception:
                team_members = []
            stats_winners = [names[i] for i in team_members if 0 <= i < len(names)]
            stats_winner_player_indices = [i for i in team_members if 0 <= i < len(names)]
            stats_winner_user_ids = [player_user_ids[i] for i in team_members if 0 <= i < len(player_user_ids) and player_user_ids[i] is not None]
            winner_label = ' / '.join(stats_winners) or f"team {winner_index + 1}"
            stats_result = 'win'
        elif winner is None or winner == -1:
            winner_label = 'draw'
            stats_result = 'draw'
        elif isinstance(winner, int) and 0 <= winner < len(names):
            winner_index = winner
            winner_label = names[winner]
            stats_winners = [winner_label]
            stats_winner_player_indices = [winner]
            if 0 <= winner < len(player_user_ids) and player_user_ids[winner] is not None:
                stats_winner_user_ids = [player_user_ids[winner]]
            stats_result = 'win'
        else:
            winner_label = str(winner)
            stats_winners = [winner_label]
            stats_result = 'win'
        started_ts = getattr(room, 'started_at', None) or getattr(room, 'created_at', time.time())
        created_at = datetime.fromtimestamp(getattr(room, 'created_at', time.time()), timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        started_at = datetime.fromtimestamp(started_ts, timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        ended_at = iso_now()
        duration_seconds = int(time.time() - started_ts)
        first_meta = participant_meta[0] if participant_meta else {}
        mod_source = first_meta.get('mod_source', 'official')
        mod_hash = first_meta.get('loadout_hash') or first_meta.get('community_mod_hash') or first_meta.get('mods_hash') or ''
        community_mod_url = first_meta.get('community_mod_url', '')
        community_mod_name = first_meta.get('community_mod_name', '')
        community_mods = first_meta.get('community_mods', []) if isinstance(first_meta.get('community_mods', []), list) else []
        entertainment_mods = list(first_meta.get('entertainment_mods', []) or [])
        valid_for_ranking, ranking_invalid_reason = is_room_valid_for_ranking(room, result)
        history_entry = {
            'time': iso_now(),
            'room_id': room.room_id,
            'mode': room.mode,
            'players': names,
            'winner': winner_label,
            'round': getattr(e, 'round_num', 0),
            'phase': getattr(e, 'phase', ''),
            'result': result,
            'created_at': created_at,
            'started_at': started_at,
            'ended_at': ended_at,
            'duration_seconds': duration_seconds,
            'valid_for_ranking': valid_for_ranking,
            'ranking_invalid_reason': ranking_invalid_reason,
            'entertainment_mods': entertainment_mods,
        }
        MATCH_HISTORY.appendleft(history_entry)
        summary = {
            'room_id': room.room_id,
            'mode': room.mode,
            'players': names,
            'player_ids': player_user_ids,
            'winner_name': winner_label,
            'winner_user_ids': stats_winner_user_ids,
            'winner_index': winner_index,
            'rounds': getattr(e, 'round_num', 0),
            'phase': getattr(e, 'phase', ''),
            'result': stats_result if result == 'finished' else result,
            'started_at': started_at,
            'ended_at': ended_at,
            'duration_seconds': duration_seconds,
            'mod_source': mod_source,
            'mod_hash': mod_hash,
            'community_mod_url': community_mod_url,
            'community_mod_name': community_mod_name,
            'community_mods': community_mods,
            'entertainment_mods': entertainment_mods,
            'valid_for_ranking': valid_for_ranking,
            'ranking_invalid_reason': ranking_invalid_reason,
            'valid_action_counts': getattr(room, '_valid_action_counts', {}) or {},
            'valid_action_counts_by_side': room_valid_actions_by_side(room),
        }
        cards_played_by_player = []
        dodge_damage_prevented_by_player = []
        achievement_metric_deltas_by_user = {}
        for pidx in range(len(names)):
            try:
                card_plays = max(0, int(e.achievement_total_card_plays(pidx)))
            except Exception:
                ps = e.players[pidx] if pidx < len(getattr(e, 'players', []) or []) else None
                card_plays = max(0, int(getattr(ps, 'achievement_total_card_plays', 0) or 0)) if ps else 0
            cards_played_by_player.append(card_plays)
            ps = e.players[pidx] if pidx < len(getattr(e, 'players', []) or []) else None
            dodge_prevented = max(
                0,
                int(getattr(ps, 'achievement_dodge_damage_prevented', 0) or 0),
            ) if ps else 0
            dodge_damage_prevented_by_player.append(dodge_prevented)
            uid = player_user_ids[pidx] if pidx < len(player_user_ids) else None
            if uid is None:
                continue
            if card_plays > 0 or dodge_prevented > 0:
                user_metrics = achievement_metric_deltas_by_user.setdefault(str(uid), {})
                if card_plays > 0:
                    user_metrics['cards_played_total'] = int(user_metrics.get('cards_played_total', 0) or 0) + card_plays
                if dodge_prevented > 0:
                    user_metrics['dodge_damage_prevented_total'] = (
                        int(user_metrics.get('dodge_damage_prevented_total', 0) or 0)
                        + dodge_prevented
                    )
        summary['cards_played_by_player'] = cards_played_by_player
        summary['dodge_damage_prevented_by_player'] = dodge_damage_prevented_by_player
        summary['achievement_metric_deltas_by_user'] = achievement_metric_deltas_by_user
        raw_draft_picks = getattr(e, 'draft_picks', []) or []
        player_draft_cards = []
        for pidx in range(len(names)):
            if isinstance(raw_draft_picks, dict):
                cards = raw_draft_picks.get(pidx, raw_draft_picks.get(str(pidx), []))
            elif pidx < len(raw_draft_picks):
                cards = raw_draft_picks[pidx]
            else:
                cards = []
            player_draft_cards.append(list(cards or []) if isinstance(cards, (list, tuple, set)) else [])
        summary['draft_card_ids_by_player'] = player_draft_cards
        summary['opening_event_ids_by_player'] = [
            str(event_id) if event_id is not None else ''
            for event_id in (getattr(e, 'opening_event_picks', []) or [])[:len(names)]
        ]
        summary['winner_player_indices'] = stats_winner_player_indices
        summary['achievement_flags_by_user'] = build_match_achievement_flags(room, player_user_ids, stats_winner_player_indices)
        if getattr(e, 'game_over', False):
            replay_actions = getattr(room, '_replay_actions', []) or []
            if not replay_actions or replay_actions[-1].get('type') != 'game_over':
                record_room_replay_action(room, 'game_over', None, {
                    'result': result,
                    'winner_name': winner_label,
                    'winner_index': winner_index,
                })
        replay_data = room_replay_data(room)
        community_snapshots = build_community_replay_snapshots(community_mods) if mod_source == 'community' else []
        if DB_AVAILABLE:
            try:
                match_id = save_match_summary(summary)
                summary['match_id'] = int(match_id)
                try:
                    dew_result = award_match_thorn_dew(match_id, summary)
                    summary['thorn_dew_result'] = dew_result
                except Exception as dew_exc:
                    admin_event('error', f'failed to award thorn dew: {dew_exc}')
                replay_id = save_replay_snapshot(
                    match_id,
                    {**summary, 'replay': replay_data, 'community_mod_snapshots': community_snapshots},
                    card_defs=CARD_DEFS,
                    game_version=GAME_VERSION,
                )
                summary['replay_id'] = int(replay_id)
                history_entry['match_id'] = int(match_id)
                history_entry['replay_id'] = int(replay_id)
                should_score_gr = bool(valid_for_ranking and getattr(e, 'game_over', False) and room.mode in ('1v1', '2v2'))
                if should_score_gr:
                    increment_user_stats(registered_user_ids, stats_winner_user_ids, stats_result)
                    try:
                        gr_result = apply_gr_match_result(match_id, summary)
                        summary['gr_result'] = gr_result
                    except Exception as gr_exc:
                        admin_event('error', f'failed to apply GR result: {gr_exc}')
                elif getattr(e, 'game_over', False) and room.mode in ('1v1', '2v2'):
                    summary['gr_result'] = {
                        'applied': False,
                        'reason': ranking_invalid_reason or 'not_valid_for_ranking',
                    }
                if result == 'finished' and getattr(e, 'game_over', False):
                    try:
                        achievement_result = process_match_achievements(match_id, summary)
                        summary['achievement_result'] = achievement_result
                        emit_achievement_unlocks(room, achievement_result)
                    except Exception as ach_exc:
                        admin_event('error', f'failed to process achievements: {ach_exc}')
                if result == 'finished' and getattr(e, 'game_over', False):
                    add_user_play_seconds(registered_user_ids, duration_seconds)
                if result == 'finished' and getattr(e, 'game_over', False) and room.mode in ('1v1', '2v2'):
                    record_card_draft_win_result(
                        room.mode,
                        player_draft_cards,
                        stats_winner_player_indices,
                        'draw' if stats_result == 'draw' else 'finished',
                    )
                    record_opening_event_win_result(
                        room.mode,
                        summary.get('opening_event_ids_by_player') or [],
                        stats_winner_player_indices,
                        'draw' if stats_result == 'draw' else 'finished',
                    )
            except Exception as db_exc:
                admin_event('error', f'failed to persist match summary: {db_exc}')
        room._match_summary = summary
        room._history_recorded = True
    except Exception as exc:
        admin_event('error', f'failed to record match history: {exc}')


def is_admin_authenticated():
    return bool(session.get('admin_authenticated'))


def is_admin_console_authenticated():
    return bool(session.get('admin_console_authenticated'))


def is_handling_authenticated():
    return bool(session.get('handling_authenticated')) or is_admin_authenticated()


def is_beta_authenticated():
    return bool(session.get('beta_authenticated'))


def admin_unauthorized():
    return jsonify({'success': False, 'error': 'unauthorized'}), 401


def handling_unauthorized():
    return jsonify({'success': False, 'error': 'unauthorized'}), 401


def should_rate_limit_admin_login(ip):
    now = time.time()
    failures = [ts for ts in ADMIN_LOGIN_FAILURES.get(ip, []) if now - ts < 300]
    ADMIN_LOGIN_FAILURES[ip] = failures
    return len(failures) >= 8


def record_admin_login_failure(ip):
    failures = ADMIN_LOGIN_FAILURES.setdefault(ip, [])
    failures.append(time.time())
    ADMIN_LOGIN_FAILURES[ip] = [ts for ts in failures if time.time() - ts < 300]


def should_rate_limit_beta_login(ip):
    now = time.time()
    failures = [ts for ts in BETA_LOGIN_FAILURES.get(ip, []) if now - ts < 300]
    BETA_LOGIN_FAILURES[ip] = failures
    return len(failures) >= 10


def record_beta_login_failure(ip):
    failures = BETA_LOGIN_FAILURES.setdefault(ip, [])
    failures.append(time.time())
    BETA_LOGIN_FAILURES[ip] = [ts for ts in failures if time.time() - ts < 300]


def clear_beta_login_failures(ip):
    BETA_LOGIN_FAILURES.pop(ip, None)


def should_rate_limit_auth_login(ip):
    now = time.time()
    failures = [ts for ts in AUTH_LOGIN_FAILURES.get(ip, []) if now - ts < 300]
    AUTH_LOGIN_FAILURES[ip] = failures
    return len(failures) >= 10


def record_auth_login_failure(ip):
    failures = AUTH_LOGIN_FAILURES.setdefault(ip, [])
    failures.append(time.time())
    AUTH_LOGIN_FAILURES[ip] = [ts for ts in failures if time.time() - ts < 300]


def clear_auth_login_failures(ip):
    AUTH_LOGIN_FAILURES.pop(ip, None)


def moderation_duration_text(remaining_seconds=None, permanent=False):
    if permanent or remaining_seconds is None:
        return '永久'
    return format_duration_zh(max(0, int(remaining_seconds or 0)))


def ban_error_payload(status, *, reason_key='reason'):
    reason = (status or {}).get('reason') or ''
    remaining = (status or {}).get('remaining_seconds')
    permanent = bool((status or {}).get('permanent')) or remaining is None
    duration_text = moderation_duration_text(remaining, permanent)
    message = f'账号已被封禁（剩余{duration_text}）：{reason}' if not permanent and reason else (
        f'账号已被封禁（永久）：{reason}' if reason else (
            f'账号已被封禁（剩余{duration_text}）' if not permanent else '账号已被封禁（永久）'
        )
    )
    payload = {
        reason_key: message,
        'remaining_seconds': remaining,
        'permanent': permanent,
        'ban_until': (status or {}).get('ban_until'),
    }
    if reason:
        payload['ban_reason'] = reason
    return payload


def muted_error_payload(remaining_seconds=0, *, message='你已被禁言，请稍后再试'):
    remaining = max(0, int(remaining_seconds or 0))
    text = f'{message}（剩余{format_duration_zh(remaining)}）' if remaining else message
    return {'message': text, 'remaining_seconds': remaining}


def db_unavailable_response():
    return jsonify({'success': False, 'error': f'数据库不可用: {DB_INIT_ERROR or "unknown"}'}), 503


def replay_api_allowed():
    return bool(is_admin_authenticated() or is_admin_console_authenticated() or session.get('user_id'))


def replay_admin_context_requested():
    requested = str(request.args.get('admin', '')).lower() in ('1', 'true', 'yes')
    return requested and bool(is_admin_authenticated() or is_admin_console_authenticated())


def replay_item_visible_to_current_user(item, admin_context=False):
    user_id = session.get('user_id')
    if admin_context or is_admin_console_authenticated() or (user_id and feedback_is_staff(user_id)):
        return True
    username = str(session.get('username') or '').lower()
    if user_id and (item or {}).get('id'):
        try:
            return replay_visible_to_user(item.get('id'), user_id, username)
        except Exception:
            pass
    if not username:
        return False
    return any(str(name or '').lower() == username for name in (item or {}).get('players', []))


def _replay_download_rate_limit_response(replay_id, item=None, admin_context=False):
    ip = _client_ip()
    user_id = session.get('user_id')
    is_admin_download = bool(admin_context or is_admin_authenticated() or is_admin_console_authenticated())
    replay_size = 0
    try:
        replay_size = int((item or {}).get('replay_size') or 0)
    except Exception:
        replay_size = 0
    if REPLAY_DOWNLOAD_MAX_BYTES and replay_size > REPLAY_DOWNLOAD_MAX_BYTES and not is_admin_download:
        admin_event(
            'warning',
            f'replay_download_blocked_large replay_id={replay_id} size={replay_size} ip={ip} user_id={user_id}',
            user_id=user_id,
        )
        return jsonify({'success': False, 'error': '回放文件过大，请联系管理员下载'}), 413

    actor_key = f'user:{user_id}' if user_id else f'ip:{ip}'
    repeat_window = 5 if is_admin_download else REPLAY_DOWNLOAD_REPEAT_SECONDS
    limits = [
        (f'replay-download:repeat:{actor_key}:{replay_id}', 1, repeat_window),
        (f'replay-download:ip-minute:{ip}', 20 if is_admin_download else REPLAY_DOWNLOAD_IP_PER_MINUTE, 60),
        (f'replay-download:ip-hour:{ip}', 200 if is_admin_download else REPLAY_DOWNLOAD_IP_PER_HOUR, 3600),
    ]
    if user_id:
        limits.extend([
            (f'replay-download:user-minute:{user_id}', 20 if is_admin_download else REPLAY_DOWNLOAD_USER_PER_MINUTE, 60),
            (f'replay-download:user-hour:{user_id}', 200 if is_admin_download else REPLAY_DOWNLOAD_USER_PER_HOUR, 3600),
        ])
    for key, limit, window in limits:
        if not rate_limiter(key, limit=limit, window=window):
            admin_event(
                'warning',
                f'replay_download_rate_limited replay_id={replay_id} key={key} limit={limit}/{window}s ip={ip} user_id={user_id}',
                user_id=user_id,
            )
            return jsonify({'success': False, 'error': '下载过于频繁，请稍后再试'}), 429
    return None


REPLAY_MAX_ACTIONS = int(os.environ.get('GTN_REPLAY_MAX_ACTIONS', '1500') or 1500)
REPLAY_MAX_STATE_BYTES = int(os.environ.get('GTN_REPLAY_MAX_STATE_BYTES', '750000') or 750000)
REPLAY_MAX_FULL_STATE_FRAMES = int(os.environ.get('GTN_REPLAY_MAX_FULL_STATE_FRAMES', '260') or 260)
REPLAY_MAX_TOTAL_STATE_BYTES = int(os.environ.get('GTN_REPLAY_MAX_TOTAL_STATE_BYTES', '18000000') or 18000000)
REPLAY_COMPACT_STATE_INTERVAL = max(1, int(os.environ.get('GTN_REPLAY_COMPACT_STATE_INTERVAL', '8') or 8))
REPLAY_FULL_STATE_INTERVAL = max(20, int(os.environ.get('GTN_REPLAY_FULL_STATE_INTERVAL', '80') or 80))
REPLAY_DOWNLOAD_USER_PER_MINUTE = max(1, int(os.environ.get('GTN_REPLAY_DOWNLOAD_USER_PER_MINUTE', '3') or 3))
REPLAY_DOWNLOAD_USER_PER_HOUR = max(1, int(os.environ.get('GTN_REPLAY_DOWNLOAD_USER_PER_HOUR', '30') or 30))
REPLAY_DOWNLOAD_IP_PER_MINUTE = max(1, int(os.environ.get('GTN_REPLAY_DOWNLOAD_IP_PER_MINUTE', '5') or 5))
REPLAY_DOWNLOAD_IP_PER_HOUR = max(1, int(os.environ.get('GTN_REPLAY_DOWNLOAD_IP_PER_HOUR', '50') or 50))
REPLAY_DOWNLOAD_REPEAT_SECONDS = max(1, int(os.environ.get('GTN_REPLAY_DOWNLOAD_REPEAT_SECONDS', '30') or 30))
REPLAY_DOWNLOAD_MAX_BYTES = max(0, int(os.environ.get('GTN_REPLAY_DOWNLOAD_MAX_BYTES', str(20 * 1024 * 1024)) or 0))
_REPLAY_DELTA_UNCHANGED = object()


def _replay_strip_private_logs(value):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key in ('log', 'logs', 'battle_log', 'battle_logs'):
                continue
            result[key] = _replay_strip_private_logs(item)
        return result
    if isinstance(value, list):
        return [_replay_strip_private_logs(item) for item in value]
    return value


def _replay_json_safe(value):
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except Exception:
        return {'unserializable': True, 'repr': repr(value)[:500]}


def _replay_round(engine):
    return int(getattr(engine, 'round_num', 0) or 0)


def _replay_elapsed_ms(room):
    started = getattr(room, '_replay_zero_at', None) or getattr(room, 'created_at', time.time())
    return max(0, int((time.time() - started) * 1000))


def _replay_capture_state(room):
    engine = getattr(room, 'engine', None)
    if engine is None:
        return {}
    try:
        if 'build_spectate_state' in globals():
            state = build_spectate_state(room, perspective=0)
            state['spectating'] = True
            state['replay_mode'] = True
            # spectate_players already contains every private player snapshot.
            # Keeping you/opponent copies for every perspective multiplied long
            # replay size without adding information.
            for key in ('you', 'opponent', 'opponent2', 'teammate'):
                state.pop(key, None)
            state.pop('room_chat_history', None)
        else:
            state = engine.get_public_state(0)
            state['your_id'] = 0
            state['mode'] = getattr(room, 'mode', '')
    except Exception as exc:
        state = {'error': f'{type(exc).__name__}: {exc}', 'your_id': 0}
    snapshot = {
        'mode': getattr(room, 'mode', ''),
        'phase': getattr(engine, 'phase', ''),
        'round_num': _replay_round(engine),
        'current_player': getattr(engine, 'current_player', None),
        'game_over': bool(getattr(engine, 'game_over', False)),
        'winner': getattr(engine, 'winner', None),
        'winning_team': getattr(engine, 'winning_team', None),
        'player_names': list(getattr(engine, 'player_names', []) or []),
        'perspective_count': len(getattr(room, 'player_sids', []) or []),
        'perspectives': [state],
    }
    safe = _replay_json_safe(snapshot)
    return safe


def _replay_compact_state(room):
    engine = getattr(room, 'engine', None)
    if engine is None:
        return {}
    return {
        'compact': True,
        'mode': getattr(room, 'mode', ''),
        'phase': getattr(engine, 'phase', ''),
        'round_num': _replay_round(engine),
        'current_player': getattr(engine, 'current_player', None),
        'game_over': bool(getattr(engine, 'game_over', False)),
        'winner': getattr(engine, 'winner', None),
        'winning_team': getattr(engine, 'winning_team', None),
        'player_names': list(getattr(engine, 'player_names', []) or []),
    }


def _replay_state_size(state):
    try:
        return len(json.dumps(state, ensure_ascii=False, default=str).encode('utf-8'))
    except Exception:
        return 0


def _replay_state_delta(previous, current):
    if previous == current:
        return _REPLAY_DELTA_UNCHANGED
    if isinstance(previous, dict) and isinstance(current, dict):
        changed = {}
        removed = [key for key in previous if key not in current]
        for key, value in current.items():
            if key not in previous:
                changed[key] = {'$set': value}
                continue
            child = _replay_state_delta(previous.get(key), value)
            if child is not _REPLAY_DELTA_UNCHANGED:
                changed[key] = child
        patch = {'$dict': changed}
        if removed:
            patch['$remove'] = removed
        return patch
    if isinstance(previous, list) and isinstance(current, list):
        if len(previous) == len(current):
            changed = {}
            for index, value in enumerate(current):
                child = _replay_state_delta(previous[index], value)
                if child is not _REPLAY_DELTA_UNCHANGED:
                    changed[str(index)] = child
            return {'$items': changed}
        prefix = 0
        limit = min(len(previous), len(current))
        while prefix < limit and previous[prefix] == current[prefix]:
            prefix += 1
        return {'$list': {'start': prefix, 'items': current[prefix:]}}
    return {'$set': current}


def _replay_capture_budgeted_state(room, frame_index):
    current = _replay_capture_state(room)
    previous = getattr(room, '_replay_last_state', None)
    current_phase = str(current.get('phase') or '') if isinstance(current, dict) else ''
    previous_phase = str(previous.get('phase') or '') if isinstance(previous, dict) else ''
    setup_phases = {'draft', 'event_select', 'event_reveal', 'event_sub_choice', 'sub_choice'}
    entering_play = previous_phase in setup_phases and current_phase not in setup_phases
    force_full = previous is None or entering_play or frame_index % REPLAY_FULL_STATE_INTERVAL == 0
    stored = current
    stored_bytes = None
    is_full = True
    if not force_full:
        patch = _replay_state_delta(previous, current)
        if patch is _REPLAY_DELTA_UNCHANGED:
            patch = {'$dict': {}}
        delta = {'delta': True, 'patch': patch}
        delta_bytes = _replay_state_size(delta)
        # Ordinary action deltas are tiny. Only serialize the complete snapshot
        # again when an unusually large replacement might actually be cheaper.
        if delta_bytes <= REPLAY_MAX_STATE_BYTES or delta_bytes < _replay_state_size(current):
            stored = delta
            stored_bytes = delta_bytes
            is_full = False

    room._replay_last_state = current
    full_frames = int(getattr(room, '_replay_full_state_frames', 0) or 0)
    total_bytes = int(getattr(room, '_replay_state_bytes', 0) or 0)
    state_bytes = stored_bytes if stored_bytes is not None else _replay_state_size(stored)
    if is_full:
        room._replay_full_state_frames = full_frames + 1
    room._replay_state_bytes = total_bytes + state_bytes
    return stored


def reset_room_replay(room):
    now = time.time()
    room._replay_zero_at = now
    room._replay_keyframes = []
    room._replay_actions = []
    room._replay_truncated = False
    room._replay_full_state_frames = 0
    room._replay_state_bytes = 0
    room._replay_last_state = None
    room._replay_frame_seq = 0


def _next_room_replay_seq(room):
    seq = int(getattr(room, '_replay_frame_seq', 0) or 0)
    room._replay_frame_seq = seq + 1
    return seq


def record_room_replay_keyframe(room, label='state'):
    try:
        if getattr(room, '_history_recorded', False):
            return
        seq = _next_room_replay_seq(room)
        frame = {
            'i': len(getattr(room, '_replay_keyframes', []) or []),
            'seq': seq,
            't': _replay_elapsed_ms(room),
            'label': label,
            'phase': getattr(room.engine, 'phase', ''),
            'round': _replay_round(room.engine),
            'current_player': getattr(room.engine, 'current_player', None),
            'state': _replay_capture_budgeted_state(room, seq),
        }
        room._replay_keyframes.append(frame)
    except Exception as exc:
        admin_event('error', f'replay keyframe failed: {exc}')


def ensure_room_replay_keyframe(room):
    if not getattr(room, '_replay_keyframes', None):
        record_room_replay_keyframe(room, 'initial')


def _replay_payload(payload):
    if not isinstance(payload, dict):
        return {}
    data = {}
    for key, value in payload.items():
        if key in ('choice', 'result') and isinstance(value, dict):
            data[key] = _replay_json_safe(value)
        else:
            data[key] = _replay_json_safe(value)
    return data


def record_room_replay_action(room, action_type, actor=None, payload=None):
    try:
        if getattr(room, '_history_recorded', False):
            return
        ensure_room_replay_keyframe(room)
        actions = getattr(room, '_replay_actions', None)
        if actions is None:
            room._replay_actions = []
            actions = room._replay_actions
        if len(actions) >= REPLAY_MAX_ACTIONS:
            room._replay_truncated = True
            return
        seq = _next_room_replay_seq(room)
        action = {
            'i': len(actions),
            'seq': seq,
            't': _replay_elapsed_ms(room),
            'type': action_type,
            'actor': actor,
            'phase': getattr(room.engine, 'phase', ''),
            'round': _replay_round(room.engine),
            'current_player': getattr(room.engine, 'current_player', None),
            'payload': _replay_payload(payload or {}),
            'state': _replay_capture_budgeted_state(room, seq),
        }
        actions.append(action)
    except Exception as exc:
        admin_event('error', f'replay action failed: {exc}')


def room_replay_data(room):
    return {
        'keyframes': getattr(room, '_replay_keyframes', []) or [],
        'actions': getattr(room, '_replay_actions', []) or [],
        'truncated': bool(getattr(room, '_replay_truncated', False)),
        'max_actions': REPLAY_MAX_ACTIONS,
        'state_bytes': int(getattr(room, '_replay_state_bytes', 0) or 0),
        'full_state_frames': int(getattr(room, '_replay_full_state_frames', 0) or 0),
    }


def build_community_replay_snapshots(community_mods):
    snapshots = []
    for entry in community_mods or []:
        if not isinstance(entry, dict):
            continue
        sha256 = str(entry.get('sha256') or '').strip()
        public_url = str(entry.get('public_url') or '').strip()
        if not sha256 or not public_url:
            continue
        try:
            mod = load_community_mod(public_url, sha256)
            data = getattr(mod, 'community_data', None)
            if not isinstance(data, dict):
                data = fetch_json_from_public_url(public_url)
            manifest = data.get('manifest') if isinstance(data.get('manifest'), dict) else {}
            info = data.get('info') if isinstance(data.get('info'), dict) else {}
            snapshots.append({
                'sha256': sha256,
                'source': 'community',
                'public_url': public_url,
                'name': entry.get('name') or manifest.get('name') or info.get('name') or 'Community Mod',
                'author': manifest.get('author') or info.get('author') or '',
                'version': manifest.get('version') or info.get('version') or '',
                'json': data,
            })
        except Exception as exc:
            admin_event('error', f'community mod replay snapshot failed: {exc}', public_url=public_url, sha256=sha256)
            snapshots.append({
                'sha256': sha256,
                'source': 'community',
                'public_url': public_url,
                'name': entry.get('name') or 'Community Mod',
                'author': entry.get('author') or '',
                'version': entry.get('version') or '',
                'json': None,
                'snapshot_error': str(exc),
            })
    return snapshots


@app.before_request
def protect_admin_api():
    path = request.path.rstrip('/')
    if path.startswith('/api/admin/'):
        g._admin_api_started = time.perf_counter()
        g._admin_api_timing_logged = False
    admin_surface = (
        path.startswith('/api/admin/')
        or path.startswith('/api/adminconsole/')
        or path.startswith('/api/handling/')
        or path in {'/admin', '/adminpage', '/adminconsole', '/handling'}
    )
    if DB_AVAILABLE and not admin_surface and not path.startswith('/static/') and not path.startswith('/fonts/') and path != '/favicon.ico':
        try:
            ip_status = get_ip_ban_status(_client_ip())
        except Exception as exc:
            admin_event('error', f'ip ban check failed: {exc}')
            ip_status = {'banned': False}
        if ip_status.get('banned'):
            reason = ip_status.get('reason') or 'IP 已被封禁'
            remaining = ip_status.get('remaining_seconds')
            suffix = '永久' if ip_status.get('permanent') else f'剩余{format_duration_zh(remaining)}'
            if path.startswith('/api/') or request.headers.get('Accept', '').find('application/json') >= 0:
                return jsonify({'success': False, 'error': f'IP 已被封禁（{suffix}）：{reason}', 'ip_banned': True}), 403
            return (f'IP 已被封禁（{suffix}）：{reason}', 403, {'Content-Type': 'text/plain; charset=utf-8'})
    public_paths = {'/api/admin/login', '/api/admin/me'}
    if path.startswith('/api/admin/') and path not in public_paths and not is_admin_authenticated():
        return admin_unauthorized()
    console_public_paths = {'/api/adminconsole/login', '/api/adminconsole/me'}
    if path.startswith('/api/adminconsole/') and path not in console_public_paths and not is_admin_console_authenticated():
        return admin_unauthorized()
    handling_public_paths = {'/api/handling/login', '/api/handling/me'}
    if path.startswith('/api/handling/') and path not in handling_public_paths and not is_handling_authenticated():
        return handling_unauthorized()


@app.after_request
def log_slow_admin_api(response):
    try:
        path = request.path.rstrip('/')
        if path.startswith('/api/admin/') and not getattr(g, '_admin_api_timing_logged', False):
            started = getattr(g, '_admin_api_started', None)
            if started is not None:
                elapsed = (time.perf_counter() - started) * 1000
                if elapsed >= _ADMIN_API_SLOW_MS:
                    log_admin_api_timing(
                        path,
                        elapsed,
                        status=response.status_code,
                        query_count=len(request.args or {}),
                    )
    except Exception:
        pass
    return response


class GameRoom:
    def __init__(self, room_id, player_sids, allowed_card_ids=None, mode='1v1', beta_mode=False):
        self.room_id = room_id
        self.player_sids = list(player_sids)
        self.mode = mode
        self.beta_mode = bool(beta_mode)
        if mode == '2v2':
            self.engine = GameEngine2v2()
        elif mode == 'urf':
            self.engine = GameEngineInfiniteFire()
        else:
            self.engine = GameEngine()
        self.engine.allowed_card_ids = apply_runtime_content_filter(allowed_card_ids, mode) if allowed_card_ids is not None else None
        self.engine.available_builtin_setup_card_ids = apply_runtime_content_filter(BUILTIN_SETUP_CARD_IDS, mode)
        self.spectators = []
        self.disconnected_players = {}
        # Durable per-slot metadata. Socket.IO sid changes on reconnect; this
        # snapshot keeps lobby, spectate, replay, and reconnect matching from
        # degrading to "?" / "P1" if the online player row is deleted first.
        self.player_profiles = {}
        self.reconnect_timers = {}
        self.disconnect_attempt_counts = [0 for _ in self.player_sids]
        self.disconnect_timeout_defeated = set()
        self._rematch_votes = set()
        self._returned_lobby_sids = set()
        self._returned_lobby_names = {}
        self.pending_surrender_request = None
        self.chat_history = deque(maxlen=CHAT_CACHE_LIMIT)
        self.chat_sequence = 0
        self.action_lock = threading.Lock()
        self.state_broadcast_lock = threading.Lock()
        self.state_broadcast_pending = False
        self.state_broadcast_dirty = False
        self.action_timer_player = None
        self.action_timer_remaining = float(ACTION_TURN_SECONDS)
        self.action_timer_last_tick = time.time()
        self.pregame_deadlines = {}
        self.pregame_state_last_resend = 0.0
        self.team_assignments = None
        self._history_recorded = False
        self.created_at = time.time()
        self.match_seq = 1
        self.started_at = None
        reset_room_replay(self)
        if mode == '2v2' and len(player_sids) == 4:
            self.team_assignments = [[0, 1], [2, 3]]
        for idx, psid in enumerate(self.player_sids):
            self.store_player_profile(psid, idx)

    def player_index(self, sid):
        if sid in self.player_sids:
            return self.player_sids.index(sid)
        return -1

    def allocate_reconnect_timeout(self, player_index):
        if player_index < 0:
            return 0, 0
        while len(self.disconnect_attempt_counts) <= player_index:
            self.disconnect_attempt_counts.append(0)
        attempt = max(0, int(self.disconnect_attempt_counts[player_index] or 0)) + 1
        self.disconnect_attempt_counts[player_index] = attempt
        timeout = RECONNECT_TIMEOUT_SEQUENCE[attempt - 1] if attempt <= len(RECONNECT_TIMEOUT_SEQUENCE) else 0
        return attempt, int(timeout)

    def store_player_profile(self, sid, player_index=None, source=None):
        if player_index is None:
            player_index = self.player_index(sid)
        source = source or players.get(sid) or self.disconnected_players.get(sid) or {}
        profile = make_room_player_profile(source, sid=sid, player_index=player_index, room=self)
        self.player_profiles[sid] = profile
        return profile

    def get_player_profile(self, sid):
        if sid in players:
            return make_room_player_profile(players[sid], sid=sid, player_index=self.player_index(sid), room=self)
        if sid in self.disconnected_players:
            return make_room_player_profile(self.disconnected_players[sid], sid=sid, player_index=self.player_index(sid), room=self)
        profile = self.player_profiles.get(sid)
        if profile:
            return profile
        return make_room_player_profile({}, sid=sid, player_index=self.player_index(sid), room=self)


def room_match_key(room):
    return f"{room.room_id}:{getattr(room, 'match_seq', 1)}:{int(getattr(room, 'created_at', 0) * 1000)}"


def room_mod_payload(room):
    first = None
    for psid in getattr(room, 'player_sids', []) or []:
        if psid in players:
            first = players[psid]
            break
        profile = room_player_profile(room, psid)
        if profile and profile.get('nickname') not in ('?', ''):
            first = profile
            break
    if not first:
        return {}
    return {
        'disabled_mods': list(first.get('disabled_mods', [])),
        'mods_hash': first.get('mods_hash', ''),
        'loadout_hash': first.get('loadout_hash', '') or first.get('mods_hash', ''),
        'v2_loadout_hash': first.get('v2_loadout_hash', ''),
        'v2_load_order': list(first.get('v2_load_order', [])),
        'mods_list': list(first.get('mods_list', [])),
        'entertainment_mods': list(first.get('entertainment_mods', [])),
        'mod_source': first.get('mod_source', 'official'),
        'community_mod_url': first.get('community_mod_url', ''),
        'community_mod_hash': first.get('community_mod_hash', ''),
        'community_mod_name': first.get('community_mod_name', ''),
        'community_mods': list(first.get('community_mods', [])),
        'beta_mode': bool(getattr(room, 'beta_mode', False)),
    }


def apply_v2_loadout_to_engine(engine, player_meta=None, runtime_mode=None):
    player_meta = player_meta or {}
    engine.v2_loadout = player_meta.get('v2_loadout')
    registries = {}
    v2_loadout = engine.v2_loadout
    if v2_loadout is not None:
        registries = getattr(v2_loadout, 'registries', {}) or {}
    event_hooks = list(getattr(v2_loadout, 'event_hooks', []) or []) if v2_loadout is not None else []
    disabled_mod_files = runtime_disabled_content(runtime_mode)['mods']
    disabled_mod_ids = set()
    if disabled_mod_files:
        for mod in load_all_mods():
            if mod.filename not in disabled_mod_files:
                continue
            manifest = getattr(mod, 'manifest', None)
            disabled_mod_ids.add(str(getattr(manifest, 'id', '') or '').strip())
        event_hooks = [hook for hook in event_hooks if str(hook.get('_mod_id') or '') not in disabled_mod_ids]
    def enabled_registry(source):
        return {
            key: value for key, value in dict(source or {}).items()
            if str((value or {}).get('_mod_id') or '') not in disabled_mod_ids
        }
    engine.v2_ui_components = enabled_registry(player_meta.get('v2_ui_components') or {})
    engine.v2_tag_defs = enabled_registry(registries.get('tags') or {})
    engine.v2_status_defs = enabled_registry(registries.get('statuses') or {})
    engine.v2_opening_event_defs = enabled_registry(registries.get('opening_events') or {})
    engine.v2_event_hooks = event_hooks


def v2_registry_payload(v2_loadout):
    registries = getattr(v2_loadout, 'registries', {}) if v2_loadout is not None else {}
    return {
        'custom_tags': list((registries.get('tags') or {}).values()),
        'custom_statuses': list((registries.get('statuses') or {}).values()),
        'custom_opening_events': list((registries.get('opening_events') or {}).values()),
    }


def v2_opening_event_payload(resource):
    if not isinstance(resource, dict):
        return None
    event_id = str(resource.get('id') or '').strip()
    if not event_id:
        return None
    name_cn = str(resource.get('name_cn') or resource.get('name') or event_id)
    name_en = str(resource.get('name_en') or resource.get('name') or name_cn)
    desc_cn = str(resource.get('description_cn') or resource.get('description') or resource.get('desc_cn') or resource.get('desc') or '')
    desc_en = str(resource.get('description_en') or resource.get('desc_en') or desc_cn)
    name_i18n = resource.get('name_i18n') if isinstance(resource.get('name_i18n'), dict) else {'zh': name_cn, 'en': name_en}
    desc_i18n = resource.get('description_i18n') if isinstance(resource.get('description_i18n'), dict) else {'zh': desc_cn, 'en': desc_en}
    try:
        position = int(resource.get('position', 2))
    except Exception:
        position = 2
    return {
        'id': event_id,
        'name': name_cn,
        'name_cn': name_cn,
        'name_en': name_en,
        'name_i18n': name_i18n,
        'desc': desc_cn,
        'description': desc_cn,
        'desc_cn': desc_cn,
        'desc_en': desc_en,
        'desc_i18n': desc_i18n,
        'position': position,
        'weight': resource.get('weight', 1),
        'v2': True,
    }


def emit_room_game_phase(room, sid, phase, **extra):
    payload = {
        'phase': phase,
        'mode': room.mode,
        'room_id': room.room_id,
        'match_key': room_match_key(room),
    }
    payload.update(instance_payload())
    payload.update(room_mod_payload(room))
    payload.update(extra)
    socketio.emit('game_phase', payload, room=sid)


def build_choice_request_payload(source):
    source = source or {}
    payload = {
        'choice_type': source.get('choice_type', ''),
        'card': source.get('card', {}),
        'choice_params': source.get('choice_params', {}),
        'target_player_id': source.get('target_player_id'),
    }
    for key in (
        'hand_cards', 'deck_cards', 'discard_cards', 'exile_cards',
        'equipment_cards', 'top_cards', 'max_replace', 'message',
    ):
        value = source.get(key)
        if value is not None and value != [] and value != '':
            payload[key] = value
    return payload


def emit_pending_choice_request(room):
    pending = getattr(getattr(room, 'engine', None), 'pending_choice', None)
    if not pending or getattr(room.engine, 'game_over', False):
        return
    try:
        pidx = int(pending.get('player_id', -1))
    except Exception:
        return
    if pidx < 0 or pidx >= len(getattr(room, 'player_sids', []) or []):
        return
    sid = room.player_sids[pidx]
    if sid in players:
        socketio.emit('choice_request', build_choice_request_payload(pending), room=sid)


def _room_player_dead(room, player_index):
    try:
        if player_index < 0 or player_index >= len(getattr(room.engine, 'players', [])):
            return False
        return getattr(room.engine.players[player_index], 'health', 1) <= 0
    except Exception:
        return False


def _mark_player_defeated_state(room, player_index, state):
    if not isinstance(state, dict):
        return
    defeated = (
        getattr(room, 'mode', None) == '2v2'
        and _room_player_dead(room, player_index)
        and not getattr(room.engine, 'game_over', False)
    )
    state['player_defeated'] = defeated
    state['you_defeated'] = defeated


def _room_blocking_player_sids(room):
    if getattr(room, 'mode', None) == '2v2':
        return [
            psid for idx, psid in enumerate(room.player_sids)
            if not _room_player_dead(room, idx)
        ]
    return list(room.player_sids)


def _room_all_blocking_players_disconnected(room):
    blocking_sids = _room_blocking_player_sids(room)
    return bool(blocking_sids) and all(s in room.disconnected_players for s in blocking_sids)


def _room_has_blocking_disconnect(room):
    if room is None:
        return False
    disconnected = getattr(room, 'disconnected_players', {}) or {}
    if not disconnected:
        return False
    return any(sid in disconnected for sid in _room_blocking_player_sids(room))


def _player_matches_room_participant(room, nickname):
    if not nickname:
        return False
    for psid in room.player_sids:
        if room_player_nickname(room, psid, '') == nickname:
            return True
    for name in getattr(room.engine, 'player_names', []) or []:
        if name == nickname:
            return True
    return False


def _find_disconnected_sid_for_player(room, player):
    """Find a disconnected room slot that belongs to this freshly connected player."""
    if not room or not player:
        return None
    player_user_id = player.get('user_id')
    player_account_id = str(player.get('account_player_id') or '')
    player_name_key = normalize_username_key(player.get('nickname', ''))
    for old_sid, dc_info in list(getattr(room, 'disconnected_players', {}).items()):
        if player_user_id and dc_info.get('user_id') == player_user_id:
            return old_sid
        if player_account_id and player_account_id == str(dc_info.get('account_player_id') or ''):
            return old_sid
        if player_name_key and player_name_key == normalize_username_key(dc_info.get('nickname', '')):
            return old_sid
    for old_sid, profile in list(getattr(room, 'player_profiles', {}).items()):
        if not _profile_slot_is_reconnectable(room, old_sid, profile):
            continue
        if player_user_id and profile.get('user_id') == player_user_id:
            admin_event('player', f'reconnect matched by room profile user_id room={getattr(room, "room_id", "?")}', sid=old_sid)
            return old_sid
        if player_account_id and player_account_id == str(profile.get('account_player_id') or ''):
            admin_event('player', f'reconnect matched by room profile account_id room={getattr(room, "room_id", "?")}', sid=old_sid)
            return old_sid
        if player_name_key and player_name_key == normalize_username_key(profile.get('nickname', '')):
            admin_event('player', f'reconnect matched by room profile nickname room={getattr(room, "room_id", "?")}', sid=old_sid)
            return old_sid
    return None


def _online_room_player_indices(room):
    online = set()
    for idx, psid in enumerate(getattr(room, 'player_sids', []) or []):
        if psid in players:
            online.add(idx)
    return online


def _counter_card_responder_id(counter_card):
    if not isinstance(counter_card, dict):
        return -1
    try:
        return int(counter_card.get('responder_id', -1))
    except Exception:
        return -1


def _resolve_pending_response_for_disconnect(room, player_index):
    """Prevent a disconnected responder from leaving a card permanently pending."""
    engine = getattr(room, 'engine', None)
    pending = getattr(engine, 'pending_response', None) if engine is not None else None
    if not pending:
        return False
    try:
        disconnected_idx = int(player_index)
    except Exception:
        return False

    if room.mode == '2v2':
        counter_cards = [
            c for c in (pending.get('counter_cards') or [])
            if _counter_card_responder_id(c) != disconnected_idx
        ]
        if len(counter_cards) == len(pending.get('counter_cards') or []):
            return False
        pending['counter_cards'] = counter_cards
        online_indices = _online_room_player_indices(room)
        remaining_responders = {
            _counter_card_responder_id(c)
            for c in counter_cards
            if _counter_card_responder_id(c) >= 0
        }
        if any(ridx in online_indices for ridx in remaining_responders):
            return True
        try:
            engine.handle_response(disconnected_idx, None)
        except Exception as exc:
            admin_event('error', f'auto-resolve pending 2v2 response failed: {exc}', room_id=getattr(room, 'room_id', None))
            engine.pending_response = None
        return True

    try:
        player_id = int(pending.get('player_id', -1))
    except Exception:
        player_id = -1
    responder_id = 1 - player_id
    if disconnected_idx != responder_id:
        return False
    try:
        engine.handle_response(responder_id, None)
    except Exception as exc:
        admin_event('error', f'auto-resolve pending response failed: {exc}', room_id=getattr(room, 'room_id', None))
        engine.pending_response = None
    return True


def _resolve_pending_ally_request_for_disconnect(room, player_index):
    engine = getattr(room, 'engine', None)
    req = getattr(engine, 'pending_ally_request', None) if engine is not None else None
    if not req:
        return False
    try:
        disconnected_idx = int(player_index)
    except Exception:
        return False
    if req.get('target_player_id') == disconnected_idx:
        try:
            engine.handle_ally_consent(disconnected_idx, False)
        except Exception as exc:
            admin_event('error', f'auto-decline ally request failed: {exc}', room_id=getattr(room, 'room_id', None))
            engine.pending_ally_request = None
        return True
    if req.get('player_id') == disconnected_idx:
        engine.pending_ally_request = None
        return True
    return False


def _resolve_disconnect_blockers(room, player_index):
    changed = False
    if _resolve_pending_ally_request_for_disconnect(room, player_index):
        changed = True
    if _resolve_pending_response_for_disconnect(room, player_index):
        changed = True
    return changed


def _force_player_death_ignoring_saves(room, player_index, nickname='', reason='强制死亡', log=True, check_game_over=True):
    """Set a player to dead without triggering Bandage, Yggdrasil, or invincible saves."""
    e = getattr(room, 'engine', None)
    if e is None or player_index < 0 or player_index >= len(getattr(e, 'players', [])):
        return False
    ps = e.players[player_index]
    was_alive = int(getattr(ps, 'health', 0) or 0) > 0
    ps.health = 0
    ps.invincible = False
    ps.bandage_active = False
    ps.bandage_death_pending = False
    ps.skip_turn = 0
    if hasattr(e, '_clear_invincible_state'):
        try:
            e._clear_invincible_state(player_index)
        except Exception:
            ps.invincible = False
    old_ygg_check = getattr(e, '_yggdrasil_check', True)
    try:
        e._yggdrasil_check = False
        if getattr(room, 'mode', None) == '2v2' and hasattr(e, '_on_player_death'):
            e._on_player_death(player_index)
        elif check_game_over and hasattr(e, '_check_game_over'):
            e._check_game_over()
    finally:
        e._yggdrasil_check = old_ygg_check
    ps.health = 0
    ps.invincible = False
    ps.bandage_active = False
    ps.bandage_death_pending = False
    if log and was_alive:
        e.log_msg(f"{nickname or e.pn(player_index)}{reason}，已判定阵亡。")
    return was_alive


def _force_2v2_disconnect_death(room, player_index, nickname, reason='断线超时'):
    e = room.engine
    if room.mode != '2v2' or player_index < 0 or player_index >= len(getattr(e, 'players', [])):
        return False
    was_alive = _force_player_death_ignoring_saves(room, player_index, nickname, reason, log=True)
    if not getattr(e, 'game_over', False) and getattr(e, 'current_player', None) == player_index:
        advance = getattr(e, '_advance_turn', None)
        if callable(advance):
            advance()
        else:
            e.phase = 'action'
    elif not getattr(e, 'game_over', False) and getattr(e, 'phase', None) in ('response', 'choice'):
        e.phase = 'action'
    return was_alive


def _clear_room_pending_on_forfeit(room):
    e = room.engine
    e.pending_response = None
    e.pending_choice = None
    if hasattr(e, 'pending_v2_ui'):
        e.pending_v2_ui = None
    if hasattr(e, 'pending_ally_request'):
        e.pending_ally_request = None
    room.pending_surrender_request = None


def _cancel_room_reconnect_timers(room):
    for timer in list(getattr(room, 'reconnect_timers', {}).values()):
        try:
            timer.cancel()
        except Exception:
            pass
    room.reconnect_timers.clear()
    both_timer = getattr(room, 'both_dc_timer', None)
    if both_timer:
        try:
            both_timer.cancel()
        except Exception:
            pass
        room.both_dc_timer = None


def _room_team_for_player(room, player_index):
    e = room.engine
    if room.mode == '2v2' and hasattr(e, 'team_of'):
        try:
            return int(e.team_of(player_index))
        except Exception:
            return -1
    if player_index in (0, 1):
        return int(player_index)
    return -1


def _room_disconnected_teams(room):
    teams_seen = set()
    for dc_info in getattr(room, 'disconnected_players', {}).values():
        try:
            pidx = int(dc_info.get('player_index', -1))
        except Exception:
            pidx = -1
        team = _room_team_for_player(room, pidx)
        if team >= 0:
            teams_seen.add(team)
    return teams_seen


def _disconnect_info_timeout(dc_info):
    try:
        return max(0.0, float((dc_info or {}).get('reconnect_timeout', RECONNECT_TIMEOUT_SECONDS)))
    except (TypeError, ValueError):
        return float(RECONNECT_TIMEOUT_SECONDS)


def _room_timed_out_disconnected_teams(room, now=None):
    """Return teams whose blocking player has been disconnected for the full timeout."""
    now = now or time.time()
    teams_seen = set()
    for dc_info in getattr(room, 'disconnected_players', {}).values():
        try:
            pidx = int(dc_info.get('player_index', -1))
        except Exception:
            pidx = -1
        if pidx < 0:
            continue
        if getattr(room, 'mode', None) == '2v2' and _room_player_dead(room, pidx):
            continue
        try:
            disconnected_at = float(dc_info.get('disconnect_time') or now)
        except Exception:
            disconnected_at = now
        if now - disconnected_at < _disconnect_info_timeout(dc_info):
            continue
        team = _room_team_for_player(room, pidx)
        if team >= 0:
            teams_seen.add(team)
    return teams_seen


def _room_disconnect_state_payload(room, viewer_sid=None):
    now = time.time()
    entries = []
    for dc_sid, dc_info in list((getattr(room, 'disconnected_players', {}) or {}).items()):
        if viewer_sid is not None and dc_sid == viewer_sid:
            continue
        try:
            pidx = int(dc_info.get('player_index', -1))
        except Exception:
            pidx = -1
        if pidx < 0:
            continue
        if getattr(room, 'mode', None) == '2v2' and _room_player_dead(room, pidx):
            continue
        try:
            disconnected_at = float(dc_info.get('disconnect_time') or now)
        except Exception:
            disconnected_at = now
        timeout = _disconnect_info_timeout(dc_info)
        remaining = int(math.ceil(max(0.0, timeout - (now - disconnected_at))))
        entries.append({
            'sid': dc_sid,
            'player_index': pidx,
            'nickname': dc_info.get('nickname') or room_player_nickname(room, dc_sid, f'P{pidx + 1}'),
            'disconnect_time': disconnected_at,
            'remaining': remaining,
            'timeout': int(timeout),
            'attempt': int(dc_info.get('disconnect_attempt', 1) or 1),
        })
    entries.sort(key=lambda item: (item.get('remaining', 0), item.get('player_index', 999)))
    return {
        'disconnect_state': {
            'active': bool(entries),
            'players': entries,
            'reconnect_timeout': min((entry['timeout'] for entry in entries), default=RECONNECT_TIMEOUT_SECONDS),
            'wait_forever': False,
        }
    }


def _start_reconnect_timer_for_disconnected_player(room, old_sid, notify=True):
    if room is None or old_sid not in getattr(room, 'disconnected_players', {}):
        return False
    dc_info = room.disconnected_players.get(old_sid) or {}
    try:
        pidx = int(dc_info.get('player_index', -1))
    except Exception:
        pidx = -1
    if pidx < 0:
        return False
    if getattr(room, 'mode', None) == '2v2' and _room_player_dead(room, pidx):
        return False
    if old_sid in getattr(room, 'reconnect_timers', {}):
        return False
    if 'reconnect_timeout' not in dc_info:
        attempt, timeout = room.allocate_reconnect_timeout(pidx)
        dc_info['disconnect_attempt'] = attempt
        dc_info['reconnect_timeout'] = timeout
    timeout = _disconnect_info_timeout(dc_info)
    dc_info['disconnect_time'] = time.time()
    room.disconnected_players[old_sid] = dict(dc_info)
    timer = threading.Timer(timeout, reconnect_timeout, args=[room.room_id, old_sid])
    room.reconnect_timers[old_sid] = timer
    timer.daemon = True
    timer.start()
    if notify and timeout > 0:
        nickname = dc_info.get('nickname') or room_player_nickname(room, old_sid, f'P{pidx + 1}')
        for other_sid in getattr(room, 'player_sids', []) or []:
            if other_sid != old_sid and other_sid in players:
                try:
                    socketio.emit('opponent_disconnected', {
                        'reconnect_timeout': int(timeout),
                        'disconnect_attempt': int(dc_info.get('disconnect_attempt', 1) or 1),
                        'wait_forever': False,
                        'opponent_nickname': nickname,
                    }, room=other_sid)
                except Exception as exc:
                    admin_event('error', f'revive reconnect timer notify failed: {exc}', room_id=getattr(room, 'room_id', None))
    return True


def _sync_disconnected_revived_players(room):
    """If a dead disconnected 2v2 player is revived, make the slot blocking again."""
    if room is None or getattr(room, 'mode', None) != '2v2':
        return False
    changed = False
    timeout_defeated = getattr(room, 'disconnect_timeout_defeated', set())
    for old_sid, dc_info in list((getattr(room, 'disconnected_players', {}) or {}).items()):
        try:
            pidx = int(dc_info.get('player_index', -1))
        except Exception:
            pidx = -1
        if pidx < 0 or _room_player_dead(room, pidx):
            continue
        if pidx in timeout_defeated:
            timeout_defeated.discard(pidx)
            changed = True
        if _start_reconnect_timer_for_disconnected_player(room, old_sid, notify=True):
            admin_event('player', f'room {getattr(room, "room_id", "?")} revived disconnected player starts reconnect timer p{pidx + 1}', room_id=getattr(room, 'room_id', None))
            changed = True
    room.disconnect_timeout_defeated = timeout_defeated
    return changed


def _set_room_draw(room, log_message):
    e = room.engine
    e.game_over = True
    e.winner = -1
    if hasattr(e, 'winning_team'):
        e.winning_team = -1
    e.phase = 'game_over'
    e.log_msg(log_message)
    return True


def _finish_room_by_health_tiebreak(room, reason='双方中途退出'):
    e = room.engine
    if getattr(e, 'game_over', False):
        return False
    _clear_room_pending_on_forfeit(room)
    if room.mode == '2v2' and hasattr(e, 'teams'):
        try:
            team_h = [
                sum(int(getattr(e.players[pidx], 'health', 0)) for pidx in e.teams[0]),
                sum(int(getattr(e.players[pidx], 'health', 0)) for pidx in e.teams[1]),
            ]
        except Exception:
            team_h = [0, 0]
        if team_h[0] == team_h[1]:
            return _set_room_draw(room, f"{reason}，双方队伍H总和相同（{team_h[0]}），平局！")
        winner_team = 0 if team_h[0] > team_h[1] else 1
        e.game_over = True
        e.winning_team = winner_team
        e.winner = winner_team
        e.phase = 'game_over'
        e.log_msg(f"{reason}，按队伍H总和判定：队伍{winner_team + 1}获胜（{team_h[0]}:{team_h[1]}）！")
        return True
    if len(getattr(e, 'players', [])) < 2:
        return False
    h0 = int(getattr(e.players[0], 'health', 0))
    h1 = int(getattr(e.players[1], 'health', 0))
    if h0 == h1:
        return _set_room_draw(room, f"{reason}，双方H相同（{h0}），平局！")
    winner = 0 if h0 > h1 else 1
    e.game_over = True
    e.winner = winner
    e.phase = 'game_over'
    e.log_msg(f"{reason}，按当前H判定：{e.pn(winner)}获胜（{h0}:{h1}）！")
    return True


def _finish_room_by_forfeit(room, player_index, nickname, reason='中途退出'):
    e = room.engine
    if getattr(e, 'game_over', False):
        return False
    if player_index < 0 or player_index >= len(getattr(e, 'players', [])):
        return False
    _clear_room_pending_on_forfeit(room)
    if room.mode == '2v2' and hasattr(e, 'team_of'):
        losing_team = _room_team_for_player(room, player_index)
        if losing_team < 0:
            return False
        _force_player_death_ignoring_saves(room, player_index, nickname, reason, log=False, check_game_over=False)
        winning_team = 1 - losing_team
        e.game_over = True
        e.winning_team = winning_team
        e.winner = winning_team
        e.phase = 'game_over'
        e.log_msg(f"{nickname}{reason}，队伍{winning_team + 1}获胜！")
        return True
    winner = 1 - player_index
    _force_player_death_ignoring_saves(room, player_index, nickname, reason, log=False, check_game_over=False)
    e.game_over = True
    e.winner = winner
    e.phase = 'game_over'
    e.log_msg(f"{nickname}{reason}，{e.pn(winner)}获胜！")
    return True


def _display_width(s):
    w = 0
    for ch in s:
        if ('\u4e00' <= ch <= '\u9fff' or '\u3040' <= ch <= '\u30ff' or
                '\uac00' <= ch <= '\ud7af' or '\uff00' <= ch <= '\uffef' or
                '\u2000' <= ch <= '\u206f'):
            w += 2
        else:
            w += 1
    return w


def sanitize_nickname(raw):
    name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', raw)
    name = re.sub(r'[\u3000\s]+', '', name)
    name = re.sub(r'[^\w\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\-]', '', name)
    return name.strip()


def _trim_display_width(text, limit):
    if limit <= 0:
        return ''
    out = []
    width = 0
    for ch in str(text or ''):
        ch_width = _display_width(ch)
        if width + ch_width > limit:
            break
        out.append(ch)
        width += ch_width
    return ''.join(out)


def normalize_chat_text(raw, exempt=False):
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', str(raw or ''))
    text = re.sub(r'[\r\n\t]+', ' ', text).strip()
    if not exempt and _display_width(text) > CHAT_DISPLAY_WIDTH_LIMIT:
        text = _trim_display_width(text, CHAT_DISPLAY_WIDTH_LIMIT).rstrip()
    return text


def is_chat_limit_exempt(player):
    if not player:
        return False
    if player.get('chat_exempt') or player.get('is_admin_player'):
        return True
    role_type = str(player.get('role_type') or '').strip().lower()
    if role_type in ('admin', 'staff'):
        return True
    name = str(player.get('nickname') or '').strip().lower()
    return name in CHAT_EXEMPT_NAMES


def chat_rate_key(sid, player):
    if (player or {}).get('user_id'):
        return f"user:{player.get('user_id')}"
    return f"sid:{sid}"


def check_chat_rate_locked(sid, player, now):
    if is_chat_limit_exempt(player):
        return True
    key = chat_rate_key(sid, player)
    bucket = LOBBY_CHAT_RATE.setdefault(key, deque())
    while bucket and now - bucket[0] >= CHAT_RATE_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= CHAT_RATE_LIMIT:
        return False
    bucket.append(now)
    return True


def chat_mute_key(sid, player):
    return f"user:{player.get('user_id')}" if (player or {}).get('user_id') else f"sid:{sid}"


def _chat_exempt_from_user_id(user_id):
    if not DB_AVAILABLE or not user_id:
        return False
    try:
        profile = get_user_role_profile(user_id)
        return bool(profile and profile.get('chat_exempt'))
    except Exception:
        return False


def _validate_chat_text_for_sender(raw_text, *, exempt=False):
    raw = validate_str(raw_text, max_len=1000 if exempt else 200, name='chat text', truncate=True)
    text = normalize_chat_text(raw, exempt=exempt)
    if not text.strip():
        return None, None
    risk = check_message_risk(text)
    risk_level = int(risk.get('risk_level') or 0)
    risk_action = str(risk.get('action') or '')
    normalized_message = risk.get('normalized_message') or normalize_message(text)
    if risk_action == 'mask_flag' or risk_level >= 3:
        text = risk.get('sanitized_text') or text
    return text, {
        'risk': risk,
        'risk_level': risk_level,
        'risk_action': risk_action,
        'matched_rules': list(risk.get('matched_rules') or []),
        'normalized_message': normalized_message,
    }


def _online_lobby_mention_candidates(beta_mode=False):
    items = []
    for target_sid, target in players.items():
        if target.get('status') != 'lobby':
            continue
        if bool(target.get('beta_mode', False)) != bool(beta_mode):
            continue
        name = str(target.get('nickname') or '').strip()
        if not name:
            continue
        items.append({
            'sid': target_sid,
            'user_id': target.get('user_id'),
            'nickname': name,
            'player_id': target.get('player_id') or '',
            'key': normalize_username_key(name),
        })
    return items


def _extract_lobby_mentions(text, beta_mode=False):
    mentions = []
    if not text or '@' not in text:
        return mentions
    candidates = _online_lobby_mention_candidates(beta_mode)
    seen = set()
    for candidate in candidates:
        names = [candidate.get('nickname') or '', candidate.get('player_id') or '']
        for raw_name in names:
            token = str(raw_name or '').strip()
            if not token:
                continue
            pattern = re.compile(r'(?<!\S)@' + re.escape(token) + r'(?![\w\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af-])', re.IGNORECASE)
            if not pattern.search(text):
                continue
            key = candidate.get('user_id') or candidate.get('sid') or candidate.get('nickname')
            if key in seen:
                continue
            seen.add(key)
            mentions.append({
                'sid': candidate.get('sid'),
                'user_id': candidate.get('user_id'),
                'nickname': candidate.get('nickname'),
                'player_id': candidate.get('player_id'),
            })
            break
    return mentions


def _emit_dm_update_for_user(user_id):
    if not user_id:
        return
    try:
        unread = dm_unread_count(user_id) if DB_AVAILABLE else 0
    except Exception:
        unread = 0
    for target_sid, target in list(players.items()):
        if str(target.get('user_id') or '') == str(user_id or ''):
            socketio.emit('dm_update', {'unread_count': unread}, room=target_sid)


def _chat_entry_signature(entry):
    if not isinstance(entry, dict) or entry.get('type') != 'chat':
        return None
    return (
        entry.get('nickname', ''),
        entry.get('text', ''),
        bool(entry.get('system')),
        entry.get('chat_channel', ''),
        entry.get('chat_target_name', ''),
    )


def _lobby_chat_scope_key(beta_mode=False):
    return 'beta' if bool(beta_mode) else 'release'


def _lobby_chat_cache_locked(beta_mode=False):
    key = _lobby_chat_scope_key(beta_mode)
    if key not in LOBBY_CHAT_CACHE:
        LOBBY_CHAT_CACHE[key] = deque(maxlen=CHAT_CACHE_LIMIT)
    return LOBBY_CHAT_CACHE[key]


def _lobby_chat_next_id_locked(beta_mode=False):
    key = _lobby_chat_scope_key(beta_mode)
    if not isinstance(LOBBY_CHAT_SEQUENCE.get(key), int):
        LOBBY_CHAT_SEQUENCE[key] = 0
    LOBBY_CHAT_SEQUENCE[key] += 1
    return LOBBY_CHAT_SEQUENCE[key]


def _lobby_chat_recent_locked(limit=LOBBY_CHAT_VISIBLE_LIMIT, beta_mode=None):
    if beta_mode is None:
        items = []
        for cache in LOBBY_CHAT_CACHE.values():
            items.extend(list(cache))
        items.sort(key=lambda item: float(item.get('ts', 0)) if isinstance(item, dict) else 0)
    else:
        items = list(_lobby_chat_cache_locked(beta_mode))
    if limit and limit > 0:
        items = items[-limit:]
    return [copy.deepcopy(item) for item in items]


def _lobby_chat_history_payload_locked(limit=LOBBY_CHAT_VISIBLE_LIMIT, beta_mode=False):
    cache = _lobby_chat_cache_locked(beta_mode)
    return {
        'items': _lobby_chat_recent_locked(limit, beta_mode),
        'limit': limit,
        'total_cached': len(cache),
    }


def _lobby_chat_time_label(ts):
    return datetime.fromtimestamp(ts, timezone(timedelta(hours=8))).strftime('%H:%M')


def _chat_item_ts(item, default=None):
    default = time.time() if default is None else float(default)
    if isinstance(item, dict):
        for key in ('ts', 'time', 'created_at', 'createdAt'):
            value = item.get(key)
            if value is None or value == '':
                continue
            try:
                if isinstance(value, (int, float)):
                    return float(value)
                return datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()
            except Exception:
                continue
    return default


def restore_lobby_chat_item_locked(item, beta_mode=False):
    if not isinstance(item, dict) or item.get('type') != 'chat':
        return
    cache = _lobby_chat_cache_locked(beta_mode)
    chat_payload = refresh_chat_special_fields(item)
    chat_payload['type'] = 'chat'
    chat_payload['beta_mode'] = bool(beta_mode)
    item_ts = _chat_item_ts(chat_payload)
    chat_payload['ts'] = item_ts
    chat_payload['time'] = datetime.fromtimestamp(item_ts, timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    chat_payload.setdefault('repeat_count', 1)
    last = cache[-1] if cache else None
    last_chat = last if isinstance(last, dict) and last.get('type') == 'chat' else None
    idle = item_ts - float((last_chat or {}).get('ts', item_ts))
    if (
        last_chat is not None
        and idle >= 0
        and idle < CHAT_IDLE_SEPARATOR_SECONDS
        and _chat_entry_signature(last_chat) == _chat_entry_signature(chat_payload)
    ):
        last_chat['repeat_count'] = int(last_chat.get('repeat_count') or 1) + int(chat_payload.get('repeat_count') or 1)
        last_chat['time'] = chat_payload['time']
        last_chat['ts'] = item_ts
        return
    if last_chat is not None and idle >= CHAT_IDLE_SEPARATOR_SECONDS:
        cache.append({
            'type': 'time',
            'id': _lobby_chat_next_id_locked(beta_mode),
            'time': chat_payload['time'],
            'display_time': _lobby_chat_time_label(item_ts),
            'ts': item_ts,
        })
    cache.append(chat_payload)


def lobby_chat_would_fold_locked(payload, now=None, beta_mode=False):
    now = time.time() if now is None else float(now)
    cache = _lobby_chat_cache_locked(beta_mode)
    last = cache[-1] if cache else None
    if not isinstance(last, dict) or last.get('type') != 'chat':
        return False
    probe = copy.deepcopy(payload or {})
    probe['type'] = 'chat'
    idle = now - float(last.get('ts', now))
    return idle < CHAT_IDLE_SEPARATOR_SECONDS and _chat_entry_signature(last) == _chat_entry_signature(probe)


def append_lobby_chat_locked(payload, now=None, beta_mode=False):
    now = time.time() if now is None else float(now)
    cache = _lobby_chat_cache_locked(beta_mode)
    chat_payload = copy.deepcopy(payload or {})
    chat_payload['type'] = 'chat'
    chat_payload['beta_mode'] = bool(beta_mode)
    chat_payload['time'] = datetime.fromtimestamp(now, timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    chat_payload.setdefault('repeat_count', 1)
    last = cache[-1] if cache else None
    last_chat = last if isinstance(last, dict) and last.get('type') == 'chat' else None
    idle = now - float((last_chat or {}).get('ts', now))
    can_fold = (
        last_chat is not None
        and idle < CHAT_IDLE_SEPARATOR_SECONDS
        and _chat_entry_signature(last_chat) == _chat_entry_signature(chat_payload)
    )
    if can_fold:
        last_chat['repeat_count'] = int(last_chat.get('repeat_count') or 1) + 1
        last_chat['time'] = chat_payload['time']
        last_chat['ts'] = now
        return False
    if last_chat is not None and idle >= CHAT_IDLE_SEPARATOR_SECONDS:
        cache.append({
            'type': 'time',
            'id': _lobby_chat_next_id_locked(beta_mode),
            'time': chat_payload['time'],
            'display_time': _lobby_chat_time_label(now),
            'ts': now,
        })
    chat_payload['id'] = _lobby_chat_next_id_locked(beta_mode)
    chat_payload['ts'] = now
    cache.append(chat_payload)
    return True


def lobby_chat_history_payloads_locked(limit=LOBBY_CHAT_VISIBLE_LIMIT, beta_mode=None):
    histories = {}
    payloads = []
    for sid, player in players.items():
        if player.get('status') != 'lobby':
            continue
        player_beta = bool(player.get('beta_mode', False))
        if beta_mode is not None and player_beta != bool(beta_mode):
            continue
        key = _lobby_chat_scope_key(player_beta)
        if key not in histories:
            histories[key] = _lobby_chat_history_payload_locked(limit, player_beta)
        payloads.append((sid, copy.deepcopy(histories[key])))
    return payloads


def load_persisted_lobby_chat_cache():
    if not DB_AVAILABLE:
        return
    try:
        loaded_counts = {}
        with _lock:
            for beta_mode in (False, True):
                key = _lobby_chat_scope_key(beta_mode)
                cache = _lobby_chat_cache_locked(beta_mode)
                cache.clear()
                max_id = 0
                for item in list_lobby_chat_entries(beta_mode=beta_mode, limit=CHAT_CACHE_LIMIT):
                    if not isinstance(item, dict) or item.get('type') != 'chat':
                        continue
                    restore_lobby_chat_item_locked(item, beta_mode)
                    try:
                        max_id = max(max_id, int(item.get('id') or 0))
                    except (TypeError, ValueError):
                        pass
                LOBBY_CHAT_SEQUENCE[key] = max(int(LOBBY_CHAT_SEQUENCE.get(key) or 0), max_id)
                loaded_counts[key] = len(cache)
        print(f"[startup] restored lobby chat cache: {loaded_counts}", flush=True)
    except Exception as exc:
        print(f"[startup] restore lobby chat cache failed: {type(exc).__name__}: {exc}", flush=True)
        try:
            admin_event('error', f'restore lobby chat cache failed: {exc}')
        except Exception:
            pass


def emit_lobby_chat_history_payloads(payloads):
    for sid, payload in payloads or []:
        socketio.emit('lobby_chat_history', payload, room=sid)


def append_admin_game_chat_locked(payload, now=None, scope='global', room_id=None):
    global ADMIN_GAME_CHAT_SEQUENCE
    now = time.time() if now is None else float(now)
    chat_payload = copy.deepcopy(payload or {})
    chat_payload['type'] = 'chat'
    chat_payload['time'] = datetime.fromtimestamp(now, timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    chat_payload.setdefault('repeat_count', 1)
    chat_payload.setdefault('scope', scope or 'global')
    if room_id is not None:
        chat_payload['room_id'] = room_id
    last = ADMIN_GAME_CHAT_CACHE[-1] if ADMIN_GAME_CHAT_CACHE else None
    last_chat = last if isinstance(last, dict) and last.get('type') == 'chat' else None
    idle = now - float((last_chat or {}).get('ts', now))
    if (
        last_chat is not None
        and idle < CHAT_IDLE_SEPARATOR_SECONDS
        and _chat_entry_signature(last_chat) == _chat_entry_signature(chat_payload)
        and last_chat.get('scope') == chat_payload.get('scope')
        and last_chat.get('room_id') == chat_payload.get('room_id')
    ):
        last_chat['repeat_count'] = int(last_chat.get('repeat_count') or 1) + 1
        last_chat['time'] = chat_payload['time']
        last_chat['ts'] = now
        return False
    if last_chat is not None and idle >= CHAT_IDLE_SEPARATOR_SECONDS:
        ADMIN_GAME_CHAT_SEQUENCE += 1
        ADMIN_GAME_CHAT_CACHE.append({
            'type': 'time',
            'id': ADMIN_GAME_CHAT_SEQUENCE,
            'time': chat_payload['time'],
            'display_time': _lobby_chat_time_label(now),
            'ts': now,
        })
    ADMIN_GAME_CHAT_SEQUENCE += 1
    chat_payload['id'] = ADMIN_GAME_CHAT_SEQUENCE
    chat_payload['ts'] = now
    ADMIN_GAME_CHAT_CACHE.append(chat_payload)
    return True


def admin_game_chat_recent_locked(limit=ADMIN_GAME_CHAT_VISIBLE_LIMIT):
    items = list(ADMIN_GAME_CHAT_CACHE)
    if limit and limit > 0:
        items = items[-limit:]
    return [copy.deepcopy(item) for item in items]


def _room_chat_next_id_locked(room):
    room.chat_sequence = int(getattr(room, 'chat_sequence', 0) or 0) + 1
    return room.chat_sequence


def _room_chat_visible_player_ids(room, recipients):
    visible = []
    for target_sid in recipients or []:
        try:
            pidx = room.player_index(target_sid)
        except Exception:
            pidx = -1
        if pidx >= 0 and pidx not in visible:
            visible.append(pidx)
    return visible


def append_room_chat_locked(room, payload, now=None, recipients=None, spectator_visible=False, pregame=False):
    if room is None:
        return None
    now = time.time() if now is None else float(now)
    if not hasattr(room, 'chat_history') or room.chat_history is None:
        room.chat_history = deque(maxlen=CHAT_CACHE_LIMIT)
    chat_payload = copy.deepcopy(payload or {})
    chat_payload['type'] = 'chat'
    chat_payload['time'] = datetime.fromtimestamp(now, timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    chat_payload['ts'] = now
    chat_payload.setdefault('repeat_count', 1)
    chat_payload['pregame'] = bool(pregame)
    chat_payload['spectator_visible'] = bool(spectator_visible)
    chat_payload['visible_player_ids'] = _room_chat_visible_player_ids(room, recipients)
    try:
        chat_payload['log_anchor'] = int(getattr(room.engine, 'log_total', len(getattr(room.engine, 'log', []) or [])) or 0)
    except Exception:
        chat_payload['log_anchor'] = 0
    last = room.chat_history[-1] if room.chat_history else None
    last_chat = last if isinstance(last, dict) and last.get('type') == 'chat' else None
    can_fold = (
        last_chat is not None
        and _chat_entry_signature(last_chat) == _chat_entry_signature(chat_payload)
        and bool(last_chat.get('spectator_visible')) == bool(chat_payload.get('spectator_visible'))
        and list(last_chat.get('visible_player_ids') or []) == list(chat_payload.get('visible_player_ids') or [])
        and bool(last_chat.get('pregame')) == bool(chat_payload.get('pregame'))
        and int(last_chat.get('log_anchor') or 0) == int(chat_payload.get('log_anchor') or 0)
    )
    if can_fold:
        last_chat['repeat_count'] = int(last_chat.get('repeat_count') or 1) + 1
        last_chat['time'] = chat_payload['time']
        last_chat['ts'] = now
        return last_chat.get('id')
    chat_payload['id'] = _room_chat_next_id_locked(room)
    room.chat_history.append(chat_payload)
    return chat_payload.get('id')


def update_room_chat_message_id_locked(room, local_chat_id, message_id):
    if room is None or local_chat_id is None or not message_id:
        return False
    for entry in reversed(list(getattr(room, 'chat_history', []) or [])):
        if not isinstance(entry, dict):
            continue
        if entry.get('id') == local_chat_id:
            entry['message_id'] = message_id
            entry['messageId'] = message_id
            return True
    return False


def room_chat_history_for_sid(room, sid=None, spectator=False, limit=CHAT_CACHE_LIMIT):
    if room is None:
        return {'items': [], 'limit': limit, 'total_cached': 0}
    items = list(getattr(room, 'chat_history', []) or [])
    try:
        pidx = room.player_index(sid) if sid is not None else -1
    except Exception:
        pidx = -1
    visible = []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        if spectator:
            if not (entry.get('spectator_visible') or entry.get('is_spectator')):
                continue
        elif pidx >= 0:
            ids = entry.get('visible_player_ids')
            if isinstance(ids, list) and ids and pidx not in ids:
                continue
        else:
            continue
        item = copy.deepcopy(entry)
        item.pop('visible_player_ids', None)
        item.pop('spectator_visible', None)
        visible.append(item)
    if limit and limit > 0:
        visible = visible[-limit:]
    return {
        'items': visible,
        'limit': limit,
        'total_cached': len(items),
    }


def console_chat_payload(text):
    return {
        'nickname': ADMIN_PLAYER_DISPLAY_NAME,
        'text': text,
        'is_spectator': False,
        'is_admin_player': True,
        'is_special_player': True,
        'special_role': 'console',
        'special_role_color': 'admin',
        'special_role_sort': 0,
        'console_player': True,
        'chat_channel': 'public',
    }


def get_special_player_profile(raw):
    # Legacy secret-nickname login has been removed. Special display is now tied
    # to registered account usernames through get_special_account_profile().
    return None


def get_special_account_profile(username):
    if DB_AVAILABLE:
        try:
            profile = get_user_role_profile(username)
            if profile:
                return profile
        except Exception as exc:
            admin_event('error', f'failed to load account role for {username}: {exc}')
    lower = str(username or '').strip().lower()
    for profile in SPECIAL_ACCOUNT_PROFILES:
        if lower == profile['display_name'].lower():
            return profile
    return None

def special_public_fields(player_or_profile):
    source = player_or_profile or {}
    role = source.get('special_role')
    return {
        'is_admin_player': bool(source.get('is_admin_player')),
        'is_special_player': bool(role),
        'special_role': role or None,
        'role_type': source.get('role_type') or ('admin' if source.get('is_admin_player') else None),
        'special_role_label': source.get('special_role_label') or None,
        'special_role_color': source.get('special_role_color') or ('admin' if source.get('is_admin_player') else None),
        'special_role_sort': int(source.get('special_role_sort', 99)),
        'can_direct_friend': bool(source.get('can_direct_friend')),
        'chat_exempt': bool(source.get('chat_exempt')),
    }


def refresh_chat_special_fields(chat_payload):
    payload = copy.deepcopy(chat_payload or {})
    if not isinstance(payload, dict):
        return {}
    if payload.get('console_player'):
        payload.update(special_public_fields(console_chat_payload(payload.get('text', ''))))
        return payload
    if payload.get('system'):
        return payload
    profile = None
    identifier = payload.get('user_id') or payload.get('sender_user_id') or payload.get('nickname')
    if identifier:
        profile = get_special_account_profile(identifier)
    if profile:
        payload.update(special_public_fields(profile))
        payload['nickname'] = profile.get('display_name') or payload.get('nickname', '')
    else:
        payload.update(special_public_fields({}))
    return payload


def make_room_player_profile(source=None, sid=None, player_index=-1, room=None):
    source = source or {}
    nickname = source.get('nickname') or source.get('name') or ''
    if not nickname and room is not None:
        try:
            names = list(getattr(room.engine, 'player_names', []) or [])
            if 0 <= int(player_index) < len(names):
                nickname = names[int(player_index)]
        except Exception:
            pass
    if not nickname:
        nickname = f'P{int(player_index) + 1}' if isinstance(player_index, int) and player_index >= 0 else '?'
    profile = {
        'sid': sid or source.get('sid') or '',
        'nickname': nickname,
        'player_index': int(player_index) if isinstance(player_index, int) else source.get('player_index', -1),
        'user_id': source.get('user_id'),
        'account_player_id': source.get('account_player_id') or '',
        'is_registered_user': bool(source.get('is_registered_user')),
        'allow_guest_spectators': bool(source.get('allow_guest_spectators')),
        'mod_source': source.get('mod_source', 'official'),
        'disabled_mods': list(source.get('disabled_mods', []) or []),
        'mods_list': list(source.get('mods_list', []) or []),
        'entertainment_mods': list(source.get('entertainment_mods', []) or []),
        'community_mod_hash': source.get('community_mod_hash', ''),
        'community_mod_url': source.get('community_mod_url', ''),
        'community_mod_name': source.get('community_mod_name', ''),
        'community_mods': list(source.get('community_mods', []) or []),
        'mods_hash': source.get('mods_hash', ''),
        'loadout_hash': source.get('loadout_hash', '') or source.get('mods_hash', ''),
        'v2_loadout_hash': source.get('v2_loadout_hash', ''),
        'v2_load_order': list(source.get('v2_load_order', []) or []),
        'skin': public_skin_config(source.get('skin')),
        'skin_look': normalize_skin_look(source.get('skin_look')),
    }
    profile.update(special_public_fields(source))
    return profile


def room_player_profile(room, sid):
    if room is not None and hasattr(room, 'get_player_profile'):
        return room.get_player_profile(sid)
    if sid in players:
        return make_room_player_profile(players[sid], sid=sid, player_index=-1, room=room)
    if room is not None and sid in getattr(room, 'disconnected_players', {}):
        return make_room_player_profile(room.disconnected_players[sid], sid=sid, player_index=-1, room=room)
    return make_room_player_profile({}, sid=sid, player_index=-1, room=room)


def player_special_fields(sid, room=None):
    return special_public_fields(room_player_profile(room, sid))


def room_player_nickname(room, sid, fallback='?'):
    profile = room_player_profile(room, sid)
    return profile.get('nickname') or fallback


def room_allows_guest_spectators(room):
    for psid in list(getattr(room, 'player_sids', []) or []):
        profile = room_player_profile(room, psid)
        if not bool(profile.get('allow_guest_spectators')):
            return False
    return True


def player_accepts_game_invites(player):
    return bool(player) and player.get('accept_game_invites', True) is not False


def player_is_lobby_match_available(sid):
    """Return whether a connected player is genuinely free for a lobby invite.

    Status and room membership can briefly arrive out of order during reconnects,
    so invitation checks must not rely on the public lobby status alone.
    Callers hold ``_lock`` while using this helper.
    """
    player = players.get(sid)
    if not player or player.get('status') != 'lobby':
        return False
    if player.get('room_id') is not None or player.get('spectating_room') is not None:
        return False
    if sid in solo_sessions or sid in tutorial_sessions:
        return False
    for room in rooms.values():
        if sid not in (getattr(room, 'player_sids', []) or []):
            continue
        if getattr(getattr(room, 'engine', None), 'phase', '') != 'game_over':
            return False
    return True


def clear_pending_match_invites_for_sids_locked(sids):
    participant_sids = {sid for sid in (sids or []) if sid}
    if not participant_sids:
        return
    team_leaders = set(participant_sids)
    for sid in participant_sids:
        team = teams.get(sid)
        if team and team.get('leader'):
            team_leaders.add(team['leader'])
    for inviter_sid, target_sid in list(invites.items()):
        if inviter_sid in participant_sids or target_sid in participant_sids:
            del invites[inviter_sid]
    for match_key in list(pending_team_matches):
        if any(leader_sid in team_leaders for leader_sid in match_key):
            del pending_team_matches[match_key]


def is_admin_player_secret(raw):
    return False


def is_reserved_special_nickname(name):
    lower = str(name or '').lower()
    special_names = set(BUILTIN_SPECIAL_ACCOUNT_NAMES)
    return ('sticker' in lower and 'bug' in lower) or lower in special_names


def is_exact_special_account_name(name):
    lower = str(name or '').strip().lower()
    profile = get_special_account_profile(name)
    return bool(profile) or lower in BUILTIN_SPECIAL_ACCOUNT_NAMES


def auth_user_payload(user):
    if not user:
        return None
    payload = dict(user)
    payload.pop('online_seconds', None)
    payload.pop('online_session_started_at', None)
    payload.pop('online_seconds_total', None)
    payload.pop('password_changed_at', None)
    profile = get_special_account_profile(payload.get('username', ''))
    if profile:
        payload['display_name'] = profile['display_name']
        payload.update(special_public_fields(profile))
    else:
        payload['display_name'] = payload.get('username', '')
        payload.update(special_public_fields({}))
    try:
        payload['warnings'] = get_active_user_warnings(payload.get('id'), limit=3) if DB_AVAILABLE else []
    except Exception as exc:
        admin_event('error', f'failed to load user warnings: {exc}')
        payload['warnings'] = []
    try:
        payload['gr_history'] = list_user_gr_snapshots(payload.get('id'), limit=60) if DB_AVAILABLE and payload.get('id') else []
    except Exception as exc:
        admin_event('error', f'failed to load GR history: {exc}')
        payload['gr_history'] = []
    return payload


DEFAULT_PUBLIC_SKIN = normalize_skin_config({})
DEFAULT_SKIN_LOOK = {'x': 0.707, 'y': -0.707}


def public_skin_config(value=None):
    return normalize_skin_config(value or {})


def normalize_skin_look(value=None):
    if not isinstance(value, dict):
        return dict(DEFAULT_SKIN_LOOK)
    try:
        x = float(value.get('x', 0) or 0)
        y = float(value.get('y', 0) or 0)
    except (TypeError, ValueError):
        return dict(DEFAULT_SKIN_LOOK)
    if not (abs(x) < 1000 and abs(y) < 1000):
        return dict(DEFAULT_SKIN_LOOK)
    length = (x * x + y * y) ** 0.5
    if length < 0.001:
        return dict(DEFAULT_SKIN_LOOK)
    return {
        'x': round(max(-1.0, min(1.0, x / length)), 3),
        'y': round(max(-1.0, min(1.0, y / length)), 3),
    }


def player_skin_for_sid(sid, room=None):
    return public_skin_config(room_player_profile(room, sid).get('skin'))


def player_skin_look_for_sid(sid, room=None):
    return normalize_skin_look(room_player_profile(room, sid).get('skin_look'))


def inject_player_skins(state, room, perspective):
    if not isinstance(state, dict) or room is None:
        return state
    player_skins = []
    player_skin_looks = []
    for psid in getattr(room, 'player_sids', []) or []:
        player_skins.append(player_skin_for_sid(psid, room))
        player_skin_looks.append(player_skin_look_for_sid(psid, room))
    state['player_skins'] = player_skins
    state['player_skin_looks'] = player_skin_looks
    try:
        pidx = int(perspective)
    except (TypeError, ValueError):
        pidx = -1
    if 0 <= pidx < len(player_skins):
        if isinstance(state.get('you'), dict):
            state['you']['skin'] = player_skins[pidx]
            state['you']['skin_look'] = player_skin_looks[pidx]
    if getattr(room, 'mode', '') == '2v2':
        engine = getattr(room, 'engine', None)
        teammate_id = getattr(engine, 'get_teammate', lambda _p: -1)(pidx) if pidx >= 0 else -1
        enemy_ids = getattr(engine, 'get_all_enemies', lambda _p: [])(pidx) if pidx >= 0 else []
        if isinstance(state.get('teammate'), dict) and 0 <= teammate_id < len(player_skins):
            state['teammate']['skin'] = player_skins[teammate_id]
            state['teammate']['skin_look'] = player_skin_looks[teammate_id]
        if isinstance(state.get('opponent'), dict) and len(enemy_ids) > 0 and 0 <= enemy_ids[0] < len(player_skins):
            state['opponent']['skin'] = player_skins[enemy_ids[0]]
            state['opponent']['skin_look'] = player_skin_looks[enemy_ids[0]]
        if isinstance(state.get('opponent2'), dict) and len(enemy_ids) > 1 and 0 <= enemy_ids[1] < len(player_skins):
            state['opponent2']['skin'] = player_skins[enemy_ids[1]]
            state['opponent2']['skin_look'] = player_skin_looks[enemy_ids[1]]
    else:
        opp_pidx = 1 - pidx
        if isinstance(state.get('opponent'), dict) and 0 <= opp_pidx < len(player_skins):
            state['opponent']['skin'] = player_skins[opp_pidx]
            state['opponent']['skin_look'] = player_skin_looks[opp_pidx]
    return state


def inject_solo_skins(state, owner_skin=None, perspective=0):
    if not isinstance(state, dict):
        return state
    skins = [public_skin_config(owner_skin), dict(DEFAULT_PUBLIC_SKIN)]
    looks = [dict(DEFAULT_SKIN_LOOK), dict(DEFAULT_SKIN_LOOK)]
    state['player_skins'] = skins
    state['player_skin_looks'] = looks
    try:
        pidx = int(perspective)
    except (TypeError, ValueError):
        pidx = 0
    if isinstance(state.get('you'), dict) and 0 <= pidx < len(skins):
        state['you']['skin'] = skins[pidx]
        state['you']['skin_look'] = looks[pidx]
    opp = 1 - pidx
    if isinstance(state.get('opponent'), dict) and 0 <= opp < len(skins):
        state['opponent']['skin'] = skins[opp]
        state['opponent']['skin_look'] = looks[opp]
    return state


def _user_has_active_player_session_locked(user_id, exclude_sid=None):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return False
    exclude_sid = str(exclude_sid or '')
    for sid, player in players.items():
        if exclude_sid and str(sid) == exclude_sid:
            continue
        try:
            if int(player.get('user_id') or 0) == uid and player.get('is_registered_user'):
                return True
        except (TypeError, ValueError):
            continue
    return False


def _user_has_active_player_session(user_id, exclude_sid=None):
    with _lock:
        return _user_has_active_player_session_locked(user_id, exclude_sid=exclude_sid)


def mark_player_session_last_seen_locked(player, exclude_sid=None):
    if not DB_AVAILABLE or not player:
        return
    if not player.get('is_registered_user') or not player.get('user_id'):
        return
    if _user_has_active_player_session_locked(player.get('user_id'), exclude_sid=exclude_sid):
        return
    try:
        enqueue_user_last_seen(player.get('user_id'))
    except Exception as exc:
        admin_event('error', f"failed to enqueue last seen for user {player.get('user_id')}: {exc}")


def mark_player_session_last_seen(player, exclude_sid=None):
    with _lock:
        mark_player_session_last_seen_locked(player, exclude_sid=exclude_sid)


def public_player_info(sid, player=None):
    p = player if player is not None else players.get(sid, {})
    info = {
        'sid': sid,
        'nickname': p.get('nickname', '?'),
        'mode': p.get('mode', '1v1'),
        'user_id': p.get('user_id'),
        'is_registered_user': bool(p.get('is_registered_user')),
        'season_gr': p.get('season_gr'),
        'total_gr': p.get('total_gr'),
        'skin': public_skin_config(p.get('skin')),
        'skin_look': normalize_skin_look(p.get('skin_look')),
    }
    info.update(special_public_fields(p))
    return info


def mark_lobby_activity(sid, now=None):
    player = players.get(sid)
    if not player or player.get('status') != 'lobby':
        return
    ts = float(now or time.time())
    player['last_lobby_activity_at'] = ts
    player['next_lobby_afk_check_at'] = ts + random.uniform(
        max(60, AFK_AUTO_MIN_SECONDS),
        max(max(60, AFK_AUTO_MIN_SECONDS), AFK_AUTO_MAX_SECONDS),
    )


def _lobby_idle_cleanup_worker():
    while True:
        try:
            try:
                socketio.sleep(max(5, int(LOBBY_IDLE_CHECK_SECONDS)))
            except Exception:
                time.sleep(max(5, int(LOBBY_IDLE_CHECK_SECONDS)))
            now = time.time()
            check_sids = []
            with _lock:
                for sid, player in list(players.items()):
                    if player.get('status') != 'lobby':
                        continue
                    if sid in PENDING_AFK_CHECKS:
                        continue
                    next_at = float(player.get('next_lobby_afk_check_at') or 0)
                    if not next_at:
                        mark_lobby_activity(sid, now)
                        continue
                    if now >= next_at:
                        check_sids.append(sid)
            if not check_sids:
                continue
            sent = 0
            for sid in check_sids:
                result, error = send_afk_check_to_player(sid, reason='auto_lobby_idle', lobby_only=True)
                if result:
                    sent += 1
                elif error:
                    admin_event('error', f'auto lobby afk check failed for {sid}: {error}')
            if sent:
                admin_event('player', f'auto lobby afk check sent to {sent} player(s)')
        except Exception as exc:
            admin_event('error', f'lobby afk check worker error: {exc}')


def ensure_lobby_idle_cleanup_started():
    global _lobby_idle_cleanup_started
    if _lobby_idle_cleanup_started:
        return
    _lobby_idle_cleanup_started = True
    try:
        socketio.start_background_task(_lobby_idle_cleanup_worker)
    except Exception:
        threading.Thread(target=_lobby_idle_cleanup_worker, name='lobby-afk-check', daemon=True).start()


def _afk_check_timeout_worker(sid, request_id, timeout_seconds):
    try:
        try:
            socketio.sleep(max(1, int(timeout_seconds)))
        except Exception:
            time.sleep(max(1, int(timeout_seconds)))
        should_kick = False
        nickname = '?'
        with _lock:
            pending = PENDING_AFK_CHECKS.get(sid)
            if pending and pending.get('id') == request_id:
                PENDING_AFK_CHECKS.pop(sid, None)
                player = players.get(sid) or {}
                nickname = player.get('nickname', '?')
                should_kick = sid in players and not (pending.get('lobby_only') and player.get('status') != 'lobby')
        if should_kick:
            socketio.emit('kicked', {'reason': '挂机检测超时，已断开连接'}, room=sid)
            socketio.server.disconnect(sid)
            admin_event('player', f'afk check timed out: {nickname} sid={sid}')
    except Exception as exc:
        admin_event('error', f'afk check timeout worker failed: {exc}')


def send_afk_check_to_player(sid, reason='admin command', timeout_seconds=None, lobby_only=False):
    timeout_seconds = int(timeout_seconds or AFK_CHECK_TIMEOUT_SECONDS)
    now = time.time()
    request_id = secrets.token_urlsafe(12)
    with _lock:
        player = players.get(sid)
        if not player:
            return None, '未找到在线玩家'
        nickname = player.get('nickname', '?')
        PENDING_AFK_CHECKS[sid] = {
            'id': request_id,
            'created_at': now,
            'expires_at': now + timeout_seconds,
            'reason': reason,
            'min_ms': AFK_CHECK_HOLD_MIN_MS,
            'max_ms': AFK_CHECK_HOLD_MAX_MS,
            'lobby_only': bool(lobby_only),
        }
    payload = {
        'id': request_id,
        'timeout_seconds': timeout_seconds,
        'expires_at': now + timeout_seconds,
        'min_ms': AFK_CHECK_HOLD_MIN_MS,
        'max_ms': AFK_CHECK_HOLD_MAX_MS,
        'reason': reason,
    }
    socketio.emit('afk_check', payload, room=sid)
    try:
        socketio.start_background_task(_afk_check_timeout_worker, sid, request_id, timeout_seconds)
    except Exception:
        threading.Thread(target=_afk_check_timeout_worker, args=(sid, request_id, timeout_seconds), daemon=True).start()
    admin_event('admin', f'afk check sent to {nickname} sid={sid} reason={reason}')
    return {'nickname': nickname, 'sid': sid, 'request_id': request_id, 'timeout_seconds': timeout_seconds}, None


def _friend_request_cleanup_worker():
    while True:
        try:
            try:
                socketio.sleep(600)
            except Exception:
                time.sleep(600)
            if not DB_AVAILABLE:
                continue
            ok, error = cleanup_expired_friend_requests_once(force=True)
            if not ok and error:
                admin_event('db', f'friend request cleanup skipped: {error}')
            expired_count, disable_error = cleanup_expired_content_disables_once()
            if disable_error:
                admin_event('db', f'content disable cleanup skipped: {disable_error}')
            elif expired_count:
                invalidate_content_disable_cache()
                admin_event('admin', f'expired content disables cleared: {expired_count}')
        except Exception as exc:
            admin_event('error', f'friend request cleanup worker error: {exc}')


def ensure_friend_request_cleanup_started():
    global _friend_request_cleanup_started
    if _friend_request_cleanup_started:
        return
    if not db_maintenance_enabled():
        admin_event('db', 'friend request cleanup disabled by GTN_DB_MAINTENANCE_ENABLED=0')
        return
    _friend_request_cleanup_started = True
    try:
        socketio.start_background_task(_friend_request_cleanup_worker)
    except Exception:
        threading.Thread(target=_friend_request_cleanup_worker, name='friend-request-cleanup', daemon=True).start()


def _dm_cleanup_worker():
    while True:
        try:
            try:
                socketio.sleep(1800)
            except Exception:
                time.sleep(1800)
            if not DB_AVAILABLE:
                continue
            ok, error = cleanup_old_dm_messages_once()
            if not ok and error:
                admin_event('db', f'dm cleanup skipped: {error}')
        except Exception as exc:
            admin_event('error', f'dm cleanup worker error: {exc}')


def ensure_dm_cleanup_started():
    global _dm_cleanup_started
    if _dm_cleanup_started:
        return
    if not db_maintenance_enabled():
        admin_event('db', 'dm cleanup disabled by GTN_DB_MAINTENANCE_ENABLED=0')
        return
    _dm_cleanup_started = True
    try:
        socketio.start_background_task(_dm_cleanup_worker)
    except Exception:
        threading.Thread(target=_dm_cleanup_worker, name='dm-cleanup', daemon=True).start()


def _pending_created_at(pending):
    if not isinstance(pending, dict):
        return None
    value = pending.get('_created_at')
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pending_interaction_watchdog_worker():
    while True:
        try:
            try:
                socketio.sleep(10)
            except Exception:
                time.sleep(10)
            now = time.time()
            pending_emits = []
            with _lock:
                for room in list(rooms.values()):
                    engine = getattr(room, 'engine', None)
                    if engine is None or getattr(engine, 'game_over', False):
                        continue
                    _stamp_pending_interactions(room)
                    pending_response = getattr(engine, 'pending_response', None)
                    created = _pending_created_at(pending_response)
                    if pending_response and created:
                        age = now - created
                        last_notice = float(pending_response.get('_last_watchdog_notice', 0) or 0)
                        if age >= 120:
                            try:
                                if room.mode == '2v2':
                                    responders = sorted({
                                        _counter_card_responder_id(c)
                                        for c in (pending_response.get('counter_cards') or [])
                                        if _counter_card_responder_id(c) >= 0
                                    })
                                    responder = responders[0] if responders else int(pending_response.get('player_id', 0))
                                else:
                                    responder = 1 - int(pending_response.get('player_id', 0))
                                engine.handle_response(responder, None)
                                admin_event('warning', f'auto_resolve_pending_response room={room.room_id} age={age:.1f}', room_id=room.room_id)
                                pending_emits.append(('state', room))
                            except Exception as exc:
                                admin_event('error', f'auto_resolve_pending_response failed room={room.room_id}: {exc}', room_id=room.room_id)
                                engine.pending_response = None
                                pending_emits.append(('state', room))
                        elif age >= 60 and now - last_notice >= 20:
                            pending_response['_last_watchdog_notice'] = now
                            admin_event('warning', f'resend_pending_response room={room.room_id} age={age:.1f}', room_id=room.room_id)
                            pending_emits.append(('response', room))

                    pending_choice = getattr(engine, 'pending_choice', None)
                    created = _pending_created_at(pending_choice)
                    if pending_choice and created and now - created >= 120:
                        try:
                            player_id = int(pending_choice.get('player_id', getattr(engine, 'current_player', 0)))
                            result = engine.resolve_choice(player_id, {'cancel': True})
                            admin_event('warning', f'auto_cancel_pending_choice room={room.room_id} result={result}', room_id=room.room_id)
                        except Exception as exc:
                            admin_event('error', f'auto_cancel_pending_choice failed room={room.room_id}: {exc}', room_id=room.room_id)
                            engine.pending_choice = None
                        pending_emits.append(('state', room))

                    pending_ui = getattr(engine, 'pending_v2_ui', None)
                    created = _pending_created_at(pending_ui)
                    if pending_ui and created and now - created >= 120:
                        try:
                            player_id = int(pending_ui.get('player_id', getattr(engine, 'current_player', 0)))
                            request_id = pending_ui.get('request_id')
                            if request_id:
                                _cancel_v2_ui_timeout(('room', room.room_id), request_id)
                            result = engine.handle_v2_ui_response(player_id, request_id, {'button': 'cancel', 'values': {}})
                            admin_event('warning', f'auto_cancel_pending_v2_ui room={room.room_id} result={result}', room_id=room.room_id)
                        except Exception as exc:
                            admin_event('error', f'auto_cancel_pending_v2_ui failed room={room.room_id}: {exc}', room_id=room.room_id)
                            engine.pending_v2_ui = None
                        pending_emits.append(('state', room))
                    for old_sid, dc_info in list((getattr(room, 'disconnected_players', {}) or {}).items()):
                        try:
                            disconnected_pidx = int(dc_info.get('player_index', -1))
                        except Exception:
                            disconnected_pidx = -1
                        if getattr(room, 'mode', None) == '2v2' and _room_player_dead(room, disconnected_pidx):
                            continue
                        try:
                            disconnected_at = float(dc_info.get('disconnect_time') or now)
                        except Exception:
                            disconnected_at = now
                        if now - disconnected_at >= _disconnect_info_timeout(dc_info):
                            admin_event('warning', f'reconnect_timeout watchdog room={room.room_id} sid={old_sid}', room_id=room.room_id)
                            pending_emits.append(('reconnect_timeout', room.room_id, old_sid))
            for item in pending_emits:
                kind = item[0]
                if kind == 'reconnect_timeout':
                    reconnect_timeout(item[1], item[2])
                    continue
                room = item[1]
                if kind == 'response':
                    emit_pending_response_requests(room)
                broadcast_game_state(room)
        except Exception as exc:
            admin_event('error', f'pending interaction watchdog error: {exc}')


def ensure_pending_interaction_watchdog_started():
    global _pending_interaction_watchdog_started
    if _pending_interaction_watchdog_started:
        return
    _pending_interaction_watchdog_started = True
    try:
        socketio.start_background_task(_pending_interaction_watchdog_worker)
    except Exception:
        threading.Thread(target=_pending_interaction_watchdog_worker, name='pending-interaction-watchdog', daemon=True).start()


def _room_current_action_player_disconnected(room, engine) -> bool:
    if room is None or engine is None:
        return False
    try:
        current = int(getattr(engine, 'current_player', -1))
    except Exception:
        current = -1
    sids = list(getattr(room, 'player_sids', []) or [])
    if current < 0 or current >= len(sids):
        return False
    current_sid = sids[current]
    return bool(current_sid and current_sid in getattr(room, 'disconnected_players', {}))


def _pending_player_id(pending, fallback=None):
    if not isinstance(pending, dict):
        return fallback
    for key in ('player_id', 'target_player_id', 'responder_id'):
        if key in pending:
            try:
                return int(pending.get(key))
            except Exception:
                return fallback
    return fallback


def _room_action_timer_paused(engine, room=None):
    try:
        current = int(getattr(engine, 'current_player', -1))
    except Exception:
        current = -1
    pending_choice = getattr(engine, 'pending_choice', None)
    if pending_choice and _pending_player_id(pending_choice, current) != current:
        return True
    pending_v2_ui = getattr(engine, 'pending_v2_ui', None)
    if pending_v2_ui and _pending_player_id(pending_v2_ui, current) != current:
        return True
    return bool(
        getattr(engine, 'pending_response', None)
        or getattr(engine, 'pending_ally_request', None)
        or _room_current_action_player_disconnected(room, engine)
        or _room_has_blocking_disconnect(room)
    )


def _clear_room_action_timer(room):
    room.action_timer_player = None
    room.action_timer_remaining = float(ACTION_TURN_SECONDS)
    room.action_timer_last_tick = time.time()


def _sync_room_action_timer_after_state_change(room, now=None):
    """Reset the turn timer when engine-side auto flow changed the active player."""
    now = now or time.time()
    engine = getattr(room, 'engine', None)
    if engine is None or getattr(engine, 'game_over', False) or getattr(engine, 'phase', None) != 'action':
        _clear_room_action_timer(room)
        return None
    current = getattr(engine, 'current_player', None)
    if current is None or current < 0:
        _clear_room_action_timer(room)
        return None
    if getattr(room, 'action_timer_player', None) != current:
        room.action_timer_player = current
        room.action_timer_remaining = float(ACTION_TURN_SECONDS)
        room.action_timer_last_tick = now
    return current


def _ensure_room_action_timer_locked(room, now=None):
    now = now or time.time()
    engine = getattr(room, 'engine', None)
    if engine is None or getattr(engine, 'game_over', False) or getattr(engine, 'phase', None) != 'action':
        _clear_room_action_timer(room)
        return None
    current = getattr(engine, 'current_player', None)
    if current is None or current < 0:
        _clear_room_action_timer(room)
        return None
    return _sync_room_action_timer_after_state_change(room, now)


def _tick_room_action_timer_locked(room, now=None):
    now = now or time.time()
    engine = getattr(room, 'engine', None)
    current = _ensure_room_action_timer_locked(room, now)
    if current is None:
        return False
    if _room_action_timer_paused(engine, room):
        room.action_timer_last_tick = now
        return False
    elapsed = max(0.0, now - float(getattr(room, 'action_timer_last_tick', now) or now))
    room.action_timer_last_tick = now
    room.action_timer_remaining = max(0.0, float(getattr(room, 'action_timer_remaining', ACTION_TURN_SECONDS) or 0) - elapsed)
    return room.action_timer_remaining <= 0


def _add_room_action_timer_bonus(room, seconds=None, expected_player=None):
    seconds = ACTION_TURN_CARD_BONUS_SECONDS if seconds is None else seconds
    with _lock:
        current = _ensure_room_action_timer_locked(room)
        if current is None:
            return
        if expected_player is not None and current != expected_player:
            return
        room.action_timer_remaining = max(0.0, float(room.action_timer_remaining or 0) + float(seconds))


def _room_timer_payload(room):
    engine = getattr(room, 'engine', None)
    if engine is None or getattr(engine, 'game_over', False) or getattr(engine, 'phase', None) != 'action':
        return {'turn_timer_remaining': None, 'turn_timer_total': int(ACTION_TURN_SECONDS)}
    current = getattr(engine, 'current_player', None)
    if getattr(room, 'action_timer_player', None) != current:
        room.action_timer_player = current
        room.action_timer_remaining = float(ACTION_TURN_SECONDS)
        room.action_timer_last_tick = time.time()
    remaining = int(math.ceil(max(0.0, float(getattr(room, 'action_timer_remaining', ACTION_TURN_SECONDS) or 0))))
    return {
        'turn_timer_remaining': remaining,
        'turn_timer_total': int(ACTION_TURN_SECONDS),
        'turn_timer_player': getattr(room, 'action_timer_player', None),
        'turn_timer_paused': _room_action_timer_paused(engine, room),
    }


def emit_turn_timer_update(room):
    """Send only timer fields so countdown ticks do not re-render the battle UI."""
    try:
        engine = getattr(room, 'engine', None)
        payload = {
            'room_id': getattr(room, 'room_id', None),
            'phase': getattr(engine, 'phase', None),
            'current_player': getattr(engine, 'current_player', None),
            **_room_timer_payload(room),
        }
        for sid in list(getattr(room, 'player_sids', []) or []):
            if sid:
                socketio.emit('turn_timer_update', payload, room=sid)
        for sid in list(getattr(room, 'spectators', []) or []):
            if sid:
                socketio.emit('turn_timer_update', payload, room=sid)
    except Exception as exc:
        admin_event('error', f'turn_timer_update failed room={getattr(room, "room_id", "?")}: {exc}', room_id=getattr(room, 'room_id', None))


def _selected_opening_event_names(engine):
    names = {}
    for idx, picked_id in enumerate(getattr(engine, 'opening_event_picks', []) or []):
        if picked_id is None:
            continue
        ev = _opening_event_by_id(engine, picked_id)
        if ev:
            names[idx] = {
                'id': picked_id,
                'name': ev.get('name') or ev.get('name_cn') or ev.get('name_en') or str(picked_id),
                'name_cn': ev.get('name_cn') or ev.get('name') or str(picked_id),
                'name_en': ev.get('name_en') or ev.get('name') or str(picked_id),
            }
    return names


def _reset_pregame_deadline(room, pidx, status):
    if hasattr(room, 'pregame_deadlines'):
        room.pregame_deadlines.pop((pidx, status), None)


def _pause_pregame_deadlines_locked(room, now=None):
    """Keep pregame countdowns visually frozen while a blocking player reconnects."""
    if room is None or not hasattr(room, 'pregame_deadlines'):
        return
    now = now or time.time()
    last = getattr(room, 'pregame_pause_last_tick', None)
    room.pregame_pause_last_tick = now
    if last is None:
        return
    delta = max(0.0, now - float(last))
    if delta <= 0:
        return
    for key, deadline in list(room.pregame_deadlines.items()):
        try:
            room.pregame_deadlines[key] = float(deadline) + delta
        except Exception:
            continue


def _clear_pregame_deadline_pause(room):
    if room is None:
        return
    if hasattr(room, 'pregame_pause_last_tick'):
        try:
            delattr(room, 'pregame_pause_last_tick')
        except Exception:
            room.pregame_pause_last_tick = None


def _draft_timer_total_for_player(engine, pidx):
    try:
        picks = getattr(engine, 'draft_picks', []) or []
        picked_count = len(picks[pidx] or []) if 0 <= int(pidx) < len(picks) else 0
    except Exception:
        picked_count = 0
    total = float(DRAFT_INITIAL_TIMEOUT_SECONDS) + float(DRAFT_PICK_BONUS_SECONDS) * max(0, picked_count)
    if DRAFT_TIMEOUT_SECONDS is not None:
        total = min(float(DRAFT_TIMEOUT_SECONDS), total)
    return max(1.0, total)


def _pregame_timeout_for_status(status, room=None, pidx=None):
    if status == 'event_select':
        return EVENT_SELECT_TIMEOUT_SECONDS
    if status == 'event_reveal':
        return EVENT_REVEAL_TIMEOUT_SECONDS
    if status == 'drafting':
        if room is not None and pidx is not None:
            engine = getattr(room, 'engine', None)
            if engine is not None:
                return _draft_timer_total_for_player(engine, pidx)
        return DRAFT_TIMEOUT_SECONDS
    if status == 'sub_choice':
        return EVENT_SUB_CHOICE_TIMEOUT_SECONDS
    return None


def _add_draft_pick_time_bonus(room, pidx, now=None):
    if not hasattr(room, 'pregame_deadlines'):
        room.pregame_deadlines = {}
    now = now or time.time()
    key = (pidx, 'drafting')
    deadline = room.pregame_deadlines.get(key)
    if deadline is None:
        deadline = now + _draft_timer_total_for_player(getattr(room, 'engine', None), pidx)
    else:
        deadline = float(deadline) + float(DRAFT_PICK_BONUS_SECONDS)
    max_deadline = now + _draft_timer_total_for_player(getattr(room, 'engine', None), pidx)
    room.pregame_deadlines[key] = min(deadline, max_deadline)


def _pregame_timer_payload(room, pidx, status=None, now=None):
    engine = getattr(room, 'engine', None)
    if engine is None:
        return {'pregame_timer_remaining': None, 'pregame_timer_total': None, 'pregame_timer_status': None, 'pregame_timer_paused': False}
    status = status or (engine.get_player_status(pidx) if hasattr(engine, 'get_player_status') else None)
    timeout = _pregame_timeout_for_status(status, room, pidx)
    if timeout is None:
        return {'pregame_timer_remaining': None, 'pregame_timer_total': None, 'pregame_timer_status': status, 'pregame_timer_paused': _room_has_blocking_disconnect(room)}
    now = now or time.time()
    if not hasattr(room, 'pregame_deadlines'):
        room.pregame_deadlines = {}
    key = (pidx, status)
    deadline = room.pregame_deadlines.get(key)
    if deadline is None:
        deadline = now + float(timeout)
        room.pregame_deadlines[key] = deadline
    return {
        'pregame_timer_remaining': int(math.ceil(max(0.0, float(deadline) - now))),
        'pregame_timer_total': int(timeout),
        'pregame_timer_status': status,
        'pregame_timer_paused': _room_has_blocking_disconnect(room),
    }


def _watched_pregame_timer_payload(room, pidx, now=None):
    engine = getattr(room, 'engine', None)
    if engine is None or not hasattr(engine, 'get_player_status'):
        return {}
    try:
        own_status = engine.get_player_status(pidx)
    except Exception:
        own_status = None
    if own_status != 'ready':
        return {}
    player_count = len(getattr(room, 'player_sids', []) or getattr(engine, 'players', []) or [])
    candidates = []
    for other_idx in range(player_count):
        if other_idx == pidx:
            continue
        try:
            status = engine.get_player_status(other_idx)
        except Exception:
            continue
        if status and status != 'ready':
            candidates.append((other_idx, status))
    if not candidates:
        return {
            'watching_pregame_timers': [],
            'watching_pregame_timer_player': None,
            'watching_pregame_timer_name': None,
            'watching_pregame_timer_status': None,
            'watching_pregame_timer_remaining': None,
            'watching_pregame_timer_total': None,
        }
    status_priority = {
        'event_select': 0,
        'event_reveal': 1,
        'drafting': 2,
        'sub_choice': 3,
    }
    names = getattr(engine, 'player_names', []) or []
    watching_timers = []
    for target_idx, target_status in sorted(
        candidates,
        key=lambda item: (status_priority.get(item[1], 99), item[0]),
    ):
        timer = _pregame_timer_payload(room, target_idx, target_status, now=now)
        watching_timers.append({
            'player': target_idx,
            'name': names[target_idx] if target_idx < len(names) else f'P{target_idx + 1}',
            'status': timer.get('pregame_timer_status'),
            'remaining': timer.get('pregame_timer_remaining'),
            'total': timer.get('pregame_timer_total'),
            'paused': timer.get('pregame_timer_paused'),
        })
    if not watching_timers:
        return {}
    first = watching_timers[0]
    return {
        'watching_pregame_timers': watching_timers,
        'watching_pregame_timer_player': first.get('player'),
        'watching_pregame_timer_name': first.get('name'),
        'watching_pregame_timer_status': first.get('status'),
        'watching_pregame_timer_remaining': first.get('remaining'),
        'watching_pregame_timer_total': first.get('total'),
        'watching_pregame_timer_paused': first.get('paused'),
    }


def emit_pregame_timer_update(room, pidx, status=None):
    try:
        if pidx < 0 or pidx >= len(getattr(room, 'player_sids', []) or []):
            return
        sid = room.player_sids[pidx]
        if not sid:
            return
        payload = {
            'room_id': getattr(room, 'room_id', None),
            'match_key': room_match_key(room),
            'your_id': pidx,
            **_pregame_timer_payload(room, pidx, status),
        }
        payload.update(_watched_pregame_timer_payload(room, pidx))
        socketio.emit('pregame_timer_update', payload, room=sid)
    except Exception as exc:
        admin_event('error', f'pregame_timer_update failed room={getattr(room, "room_id", "?")} pidx={pidx}: {exc}', room_id=getattr(room, 'room_id', None))


def _default_event_sub_choice(engine, pidx):
    event_id = str(getattr(engine, 'opening_event_picks', [None])[pidx])
    if event_id == '5':
        for def_id in list(engine.fated_draw_pool_defs() if hasattr(engine, 'fated_draw_pool_defs') else []):
            if engine._card_allowed_for_fated_draw(str(def_id)):
                return {'add_def_ids': [str(def_id)]}
        return {}
    if event_id == '8':
        for def_id in list(getattr(engine, 'draft_picks', [[]])[pidx] or []):
            if str(def_id) != 'Yggdrasil':
                return {'yggdrasil_convert_def_id': str(def_id)}
        return {}
    if event_id == '11':
        candidates = list(engine.opening_event_topdeck_candidates(pidx)) if hasattr(engine, 'opening_event_topdeck_candidates') else []
        return {'topdeck_def_ids': candidates[:3]}
    return {}


def _auto_complete_draft_locked(room, pidx):
    engine = room.engine
    changed = False
    target_count = engine.draft_target_count(pidx) if hasattr(engine, 'draft_target_count') else DECK_SIZE
    guard = 0
    while len(engine.draft_picks[pidx]) < target_count and guard < max(1, target_count + 5):
        guard += 1
        if not engine.draft_options[pidx]:
            engine._generate_draft_options_for_player(pidx)
        options = engine.draft_options[pidx] or []
        if not options:
            break
        def_id = getattr(options[0], 'def_id', None)
        if not def_id:
            break
        options_before = [getattr(card, 'def_id', '') for card in options]
        pick_result = engine.draft_pick(pidx, def_id)
        success = bool(pick_result.get('success')) if isinstance(pick_result, dict) else bool(pick_result)
        if not success:
            break
        changed = True
        if DB_AVAILABLE and room.mode in ('1v1', '2v2'):
            try:
                enqueue_card_draft_pick(room.mode, options_before, def_id)
            except Exception as exc:
                admin_event('error', f'auto draft stats enqueue failed: {exc}', room_id=room.room_id)
        record_room_replay_action(room, 'draft_pick', pidx, {'def_id': def_id, 'auto': True})
    if changed:
        if len(engine.draft_picks[pidx]) >= target_count and not engine.needs_sub_choice(pidx):
            engine.player_ready[pidx] = True
        _reset_pregame_deadline(room, pidx, 'drafting')
        admin_event('game', f'auto_complete_draft room={room.room_id} pidx={pidx}', room_id=room.room_id)
    return changed


def _auto_select_opening_event_locked(room, pidx):
    engine = room.engine
    if getattr(engine, 'opening_event_picks', [None])[pidx] is not None:
        return False
    options = getattr(engine, 'opening_event_options', [[]])[pidx] or []
    first = next((ev for ev in options if ev), None)
    if not first:
        return False
    event_id = first.get('id')
    if not engine.select_opening_event(pidx, event_id):
        return False
    try:
        enqueue_opening_event_pick(room.mode, [str(ev.get('id')) for ev in options if ev and ev.get('id') is not None], event_id)
    except Exception as exc:
        admin_event('error', f'auto opening event stats enqueue failed: {exc}', room_id=room.room_id)
    record_room_replay_action(room, 'select_opening_event', pidx, {
        'event_id': event_id,
        'sub_choice': None,
        'auto': True,
    })
    _reset_pregame_deadline(room, pidx, 'event_select')
    admin_event('game', f'auto_select_opening_event room={room.room_id} pidx={pidx} event={event_id}', room_id=room.room_id)
    return True


def _auto_confirm_opening_reveal_locked(room, pidx):
    engine = room.engine
    if getattr(engine, 'opening_event_picks', [None])[pidx] is None:
        return False
    if not all(pick is not None for pick in getattr(engine, 'opening_event_picks', [])):
        return False
    started = getattr(engine, 'player_draft_started', [False] * len(getattr(room, 'player_sids', []) or []))
    if pidx < len(started) and started[pidx]:
        return False
    engine.start_draft_for_player(pidx)
    record_room_replay_action(room, 'confirm_opening_reveal', pidx, {'auto': True})
    record_room_replay_keyframe(room, 'draft_start')
    _reset_pregame_deadline(room, pidx, 'event_reveal')
    admin_event('game', f'auto_confirm_opening_reveal room={room.room_id} pidx={pidx}', room_id=room.room_id)
    return True


def _auto_submit_event_sub_choice_locked(room, pidx):
    engine = room.engine
    if bool(getattr(engine, 'player_ready', [False] * len(room.player_sids))[pidx]):
        return False
    if not engine.needs_sub_choice(pidx):
        return False
    sub_choice = _default_event_sub_choice(engine, pidx)
    engine.opening_event_sub_choices[pidx] = sub_choice or {}
    engine.player_ready[pidx] = True
    record_room_replay_action(room, 'submit_event_sub_choice', pidx, {
        'event_id': engine.opening_event_picks[pidx],
        'sub_choice': sub_choice or {},
        'auto': True,
    })
    _reset_pregame_deadline(room, pidx, 'sub_choice')
    admin_event('game', f'auto_submit_event_sub_choice room={room.room_id} pidx={pidx}', room_id=room.room_id)
    return True


def _room_timer_worker():
    while True:
        try:
            try:
                socketio.sleep(max(0.25, ROOM_TIMER_TICK_SECONDS))
            except Exception:
                time.sleep(max(0.25, ROOM_TIMER_TICK_SECONDS))
            now = time.time()
            expired_turns = []
            timer_broadcast_rooms = set()
            pregame_timer_updates = set()
            pregame_updates = set()
            start_rooms = set()
            with _lock:
                for room in list(rooms.values()):
                    engine = getattr(room, 'engine', None)
                    if engine is None or getattr(engine, 'game_over', False):
                        continue
                    was_action = getattr(engine, 'phase', None) == 'action'
                    if _tick_room_action_timer_locked(room, now):
                        expired_turns.append((room, getattr(engine, 'current_player', None)))
                    elif was_action:
                        timer_broadcast_rooms.add(room)
                    player_count = len(getattr(room, 'player_sids', []) or [])
                    if _room_has_blocking_disconnect(room):
                        _pause_pregame_deadlines_locked(room, now)
                        if hasattr(engine, 'get_player_status'):
                            for pidx in range(player_count):
                                try:
                                    status = engine.get_player_status(pidx)
                                except Exception:
                                    status = None
                                if _pregame_timeout_for_status(status, room, pidx) is not None:
                                    pregame_timer_updates.add((room, pidx, status))
                        continue
                    _clear_pregame_deadline_pause(room)
                    pregame_statuses = []
                    for pidx in range(player_count):
                        status = engine.get_player_status(pidx) if hasattr(engine, 'get_player_status') else None
                        pregame_statuses.append(status)
                        timeout = None
                        if status == 'event_select':
                            timeout = EVENT_SELECT_TIMEOUT_SECONDS
                        elif status == 'event_reveal':
                            timeout = EVENT_REVEAL_TIMEOUT_SECONDS
                        elif status == 'drafting':
                            timeout = _draft_timer_total_for_player(engine, pidx)
                        elif status == 'sub_choice':
                            timeout = EVENT_SUB_CHOICE_TIMEOUT_SECONDS
                        if timeout is None:
                            continue
                        key = (pidx, status)
                        deadline = room.pregame_deadlines.get(key) if hasattr(room, 'pregame_deadlines') else None
                        if deadline is None:
                            room.pregame_deadlines[key] = now + float(timeout)
                            pregame_timer_updates.add((room, pidx, status))
                            continue
                        pregame_timer_updates.add((room, pidx, status))
                        if now < deadline:
                            continue
                        changed = False
                        if status == 'event_select':
                            changed = _auto_select_opening_event_locked(room, pidx)
                        elif status == 'event_reveal':
                            changed = _auto_confirm_opening_reveal_locked(room, pidx)
                        elif status == 'drafting':
                            changed = _auto_complete_draft_locked(room, pidx)
                        elif status == 'sub_choice':
                            changed = _auto_submit_event_sub_choice_locked(room, pidx)
                        if changed:
                            for pi in range(len(room.player_sids)):
                                pregame_updates.add((room, pi))
                            if all(engine.player_ready[pi] for pi in range(len(room.player_sids))):
                                start_rooms.add(room)
                    if any(status and status != 'ready' for status in pregame_statuses):
                        for pidx, status in enumerate(pregame_statuses):
                            if status == 'ready':
                                pregame_timer_updates.add((room, pidx, None))
                        last_resend = float(getattr(room, 'pregame_state_last_resend', 0.0) or 0.0)
                        if now - last_resend >= max(1.0, float(PREGAME_STATE_RESEND_SECONDS)):
                            room.pregame_state_last_resend = now
                            for pi in range(len(room.player_sids)):
                                pregame_updates.add((room, pi))
                    elif pregame_statuses and all(status == 'ready' for status in pregame_statuses):
                        if getattr(engine, 'phase', None) in ('event_select', 'event_reveal', 'draft'):
                            start_rooms.add(room)
            for room, pidx in expired_turns:
                if pidx is None:
                    continue
                action_lock = getattr(room, 'action_lock', None)
                acquired = action_lock.acquire(blocking=False) if action_lock is not None else True
                if not acquired:
                    continue
                try:
                    with _lock:
                        engine = getattr(room, 'engine', None)
                        if (
                            engine is None
                            or getattr(engine, 'game_over', False)
                            or getattr(engine, 'phase', None) != 'action'
                            or getattr(engine, 'current_player', None) != pidx
                            or _room_action_timer_paused(engine, room)
                        ):
                            continue
                        pending_choice = getattr(engine, 'pending_choice', None)
                        if pending_choice:
                            try:
                                pending_player_id = int(pending_choice.get('player_id', pidx))
                            except Exception:
                                pending_player_id = pidx
                            if pending_player_id == pidx:
                                result = engine.resolve_choice(pidx, {'cancelled': True})
                                _stamp_pending_interactions(room)
                                admin_event('game', f'auto_cancel_choice_before_end_turn room={room.room_id} pidx={pidx} result={result}', room_id=room.room_id)
                                if getattr(engine, 'pending_choice', None) is not None:
                                    continue
                        pending_ui = getattr(engine, 'pending_v2_ui', None)
                        if pending_ui:
                            try:
                                pending_player_id = int(pending_ui.get('player_id', pidx))
                            except Exception:
                                pending_player_id = pidx
                            if pending_player_id == pidx:
                                request_id = str(pending_ui.get('request_id') or '')
                                if request_id:
                                    _cancel_v2_ui_timeout(('room', room.room_id), request_id)
                                result = engine.handle_v2_ui_response(pidx, request_id, {'button': 'cancel', 'values': {}})
                                _stamp_pending_interactions(room)
                                admin_event('game', f'auto_cancel_v2_ui_before_end_turn room={room.room_id} pidx={pidx} result={result}', room_id=room.room_id)
                                if getattr(engine, 'pending_v2_ui', None) is not None:
                                    continue
                        result = engine.end_turn(pidx)
                        _stamp_pending_interactions(room)
                        _clear_room_action_timer(room)
                        if result.get('success'):
                            _sync_room_action_timer_after_state_change(room)
                    if result.get('success'):
                        record_room_replay_action(room, 'end_turn', pidx, {'auto': True})
                        admin_event('game', f'auto_end_turn room={room.room_id} pidx={pidx}', room_id=room.room_id)
                    broadcast_game_state(room)
                except Exception as exc:
                    admin_event('error', f'auto_end_turn failed room={getattr(room, "room_id", "?")}: {exc}', room_id=getattr(room, 'room_id', None))
                finally:
                    if action_lock is not None:
                        action_lock.release()
            for room in timer_broadcast_rooms:
                if room not in {item[0] for item in expired_turns}:
                    emit_turn_timer_update(room)
            for room, pidx, status in pregame_timer_updates:
                emit_pregame_timer_update(room, pidx, status)
            for room in start_rooms:
                schedule_start_game(room)
            for room, pidx in pregame_updates:
                if room not in start_rooms:
                    schedule_pregame_state(room, pidx, allow_sub_choice=True)
        except Exception as exc:
            admin_event('error', f'room timer worker error: {exc}')


def ensure_room_timer_worker_started():
    global _room_timer_worker_started
    if _room_timer_worker_started:
        return
    _room_timer_worker_started = True
    try:
        socketio.start_background_task(_room_timer_worker)
    except Exception:
        threading.Thread(target=_room_timer_worker, name='room-timer-worker', daemon=True).start()


def player_is_admin(sid, room=None):
    return bool(player_special_fields(sid, room).get('is_admin_player'))


def validate_nickname(name):
    if not name or _display_width(name) > 16:
        return False
    if re.match(r'^[\d]+$', name):
        return False
    if re.match(r'^[\-_]+$', name):
        return False
    if re.search(r'[\-_]{2,}', name):
        return False
    return True


def normalize_disabled_mods(value):
    if value is None:
        return []
    if isinstance(value, str):
        normalized = [x.strip() for x in value.split(',') if x.strip()]
        return [x for x in normalized if x not in RETIRED_OFFICIAL_MOD_FILENAMES]
    if isinstance(value, (list, tuple, set)):
        normalized = [str(x).strip() for x in value if str(x).strip()]
        return [x for x in normalized if x not in RETIRED_OFFICIAL_MOD_FILENAMES]
    return []


def default_disabled_mods():
    disabled = []
    for mod in load_all_mods():
        filename = str(getattr(mod, 'filename', '') or '')
        if filename and filename not in DEFAULT_ENABLED_OFFICIAL_MOD_FILENAMES:
            disabled.append(filename)
    return sorted(set(disabled))


def normalize_disabled_mods_with_default(value):
    if value is None:
        return default_disabled_mods()
    return normalize_disabled_mods(value)


def normalize_mod_source(value):
    return 'community' if str(value or '').strip().lower() == 'community' else 'official'


def _normalize_community_hash(value):
    text = str(value or '').strip().lower()
    return text if re.fullmatch(r'[0-9a-f]{64}', text) else ''


def _normalize_community_mod_entries(value):
    if value is None or value == '':
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            value = json.loads(text)
        except Exception:
            return []
    if not isinstance(value, list):
        return []
    entries = []
    seen = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        public_url = str(item.get('public_url') or item.get('url') or '').strip()
        sha256 = _normalize_community_hash(item.get('sha256') or item.get('hash'))
        if not public_url or not sha256 or sha256 in seen:
            continue
        seen.add(sha256)
        entries.append({
            'public_url': public_url,
            'sha256': sha256,
            'name': str(item.get('name') or '').strip()[:80],
            'uploaded_at': str(item.get('uploaded_at') or '').strip()[:40],
        })
    return entries[:12]


def _community_combined_hash(entries):
    hashes = sorted(str(item.get('sha256') or '').strip().lower() for item in entries if item.get('sha256'))
    if not hashes:
        return ''
    return hashlib.sha256(('|'.join(hashes)).encode('utf-8')).hexdigest()


def _community_combined_names(entries):
    names = [str(item.get('name') or item.get('sha256') or '').strip() for item in entries]
    return ' / '.join([name for name in names if name])[:240]


def _client_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'


SOCKET_EVENT_LIMITS = {
    'login': (8, 60),
    'chat': (10, 60),
    'invite': (12, 60),
    'form_team': (12, 60),
    'invite_team': (10, 60),
    'accept_invite': (12, 60),
    'decline_invite': (20, 60),
    'accept_team': (12, 60),
    'decline_team': (20, 60),
    'leave_team': (12, 60),
    'accept_team_match': (8, 60),
    'decline_team_match': (12, 60),
    'reconnect_accept': (8, 60),
    'reconnect_decline': (8, 60),
    'set_mode': (20, 60),
    'update_mod_settings': (10, 60),
    'draft_pick': (40, 60),
    'draft_reroll': (8, 60),
    'select_opening_event': (10, 60),
    'request_pregame_state': (12, 60),
    'request_game_state': (20, 60),
    'play_card': (30, 30),
    'response': (30, 30),
    'ally_consent_response': (20, 30),
    'resolve_choice': (30, 30),
    'v2_ui_response': (30, 30),
    'use_trigger': (30, 30),
    'urf_replace_card': (12, 60),
    'urf_sell_equipment': (12, 60),
    'end_turn': (20, 30),
    'surrender': (6, 60),
    'surrender_consent_response': (10, 60),
    'rematch': (10, 60),
    'return_lobby': (12, 60),
    'spectate': (20, 60),
    'leave_spectate': (20, 60),
    'switch_spectate_perspective': (30, 60),
    'solo_start': (8, 60),
    'tutorial_start': (6, 60),
    'tutorial_bot_action': (60, 60),
    'solo_play_card': (60, 60),
    'solo_response': (60, 60),
    'solo_resolve_choice': (60, 60),
    'solo_v2_ui_response': (60, 60),
    'solo_use_trigger': (60, 60),
    'solo_end_turn': (60, 60),
    'solo_set_next_draw': (20, 60),
    'solo_undo': (30, 60),
    'solo_redo': (30, 60),
    'solo_pause': (12, 60),
    'skin_look': (80, 10),
}
SOCKET_DEFAULT_LIMIT = (80, 60)
SOCKET_ILLEGAL_KICK_LIMIT = 12
SOCKET_ILLEGAL_WINDOW = 300
SOFT_REJECT_EVENT_NAMES = {
    'play_card',
    'response',
    'resolve_choice',
    'v2_ui_response',
    'use_trigger',
    'end_turn',
    'ally_consent_response',
    'request_game_state',
}
SOFT_REJECT_CODES = {
    'WAITING_FOR_RESPONSE',
    'PENDING_RESPONSE',
    'PENDING_CHOICE',
    'PENDING_V2_UI',
    'ACTION_BUSY',
    'ACTION_TOO_FAST',
    'NOT_YOUR_TURN',
    'NOT_ACTION_PHASE',
    'STATE_VERSION_OLD',
    'NO_PENDING_CHOICE',
    'CHOICE_CANCELLED',
    'RESPONSE_NOT_EXPECTED',
    'CARD_NOT_PLAYABLE_NOW',
    'TRIGGER_NOT_PLAYABLE_NOW',
    'END_TURN_NOT_ALLOWED_NOW',
}
SOFT_REJECT_MESSAGES = {
    'WAITING_FOR_RESPONSE': '正在等待反制响应',
    'PENDING_RESPONSE': '正在等待反制响应',
    'PENDING_CHOICE': '正在等待选择操作',
    'PENDING_V2_UI': '正在等待窗口操作',
    'ACTION_BUSY': '对局正在处理上一个操作，请稍后',
    'ACTION_TOO_FAST': '操作过于频繁，请稍后',
    'NOT_YOUR_TURN': '还没轮到你',
    'NOT_ACTION_PHASE': '当前阶段不能这样操作',
    'STATE_VERSION_OLD': '状态已更新，请按当前界面操作',
    'NO_PENDING_CHOICE': '没有待选择操作',
    'CHOICE_CANCELLED': '选择已取消',
    'RESPONSE_NOT_EXPECTED': '没有待响应的操作',
    'CARD_NOT_PLAYABLE_NOW': '这张牌现在不能打出',
    'TRIGGER_NOT_PLAYABLE_NOW': '这个装备现在不能触发',
    'END_TURN_NOT_ALLOWED_NOW': '当前不能结束回合',
}


def _security_player_for_sid(sid):
    return players.get(sid) or {}


def _security_user_id_for_sid(sid):
    player = _security_player_for_sid(sid)
    return player.get('user_id')


def _security_record(kind, message, *, sid=None, severity='medium', extra=None):
    player = _security_player_for_sid(sid)
    user_id = player.get('user_id') if player else None
    event = record_suspicious_event(
        kind,
        message,
        sid=sid,
        user_id=user_id,
        ip=_client_ip(),
        severity=severity,
        extra=extra,
    )
    try:
        admin_event('suspicious', f"{event['severity']} {event['kind']}: {event['message']}", sid=sid, user_id=user_id)
    except Exception:
        pass
    return event


def _security_illegal(sid, event_name, message, *, severity='medium', emit_error=True, extra=None):
    user_id = _security_user_id_for_sid(sid)
    player = _security_player_for_sid(sid)
    room_id = player.get('room_id') if player else None
    engine_phase = None
    if room_id is not None and room_id in rooms:
        engine_phase = getattr(getattr(rooms.get(room_id), 'engine', None), 'phase', None)
    key = f'user:{user_id}' if user_id else f'sid:{sid}'
    count, should_kick = record_illegal_operation(
        key,
        limit=SOCKET_ILLEGAL_KICK_LIMIT,
        window=SOCKET_ILLEGAL_WINDOW,
    )
    extra_payload = dict(extra or {})
    extra_payload.update({
        'hard_illegal': True,
        'illegal_count': count,
        'event_name': event_name,
        'room_id': room_id,
        'engine_phase': engine_phase,
    })
    _security_record(
        event_name,
        f'{message} (illegal={count})',
        sid=sid,
        severity=severity,
        extra=extra_payload,
    )
    if emit_error:
        emit('server_error', {'message': message})
    if should_kick:
        _security_record('auto_kick', f'frequent illegal operations after {event_name}', sid=sid, severity='high')
        def _kick_later(target_sid):
            try:
                time.sleep(0.05)
                socketio.emit('kicked', {'reason': f'非法操作过多：{event_name}'}, room=target_sid)
                socketio.server.disconnect(target_sid)
            except Exception:
                pass
        socketio.start_background_task(_kick_later, sid)
        return True
    return False


def _soft_reject_context(room=None, pidx=None):
    engine = getattr(room, 'engine', None) if room is not None else None
    return {
        'room_id': getattr(room, 'room_id', None),
        'pidx': pidx,
        'phase': getattr(engine, 'phase', None),
        'current_player': getattr(engine, 'current_player', None),
        'has_pending_response': bool(getattr(engine, 'pending_response', None)) if engine is not None else False,
        'has_pending_choice': bool(getattr(engine, 'pending_choice', None)) if engine is not None else False,
        'has_pending_v2_ui': bool(getattr(engine, 'pending_v2_ui', None)) if engine is not None else False,
    }


def soft_reject(sid, event_name, code, message=None, room=None, pidx=None, send_state=False):
    code = str(code or 'ACTION_BUSY').strip().upper()
    if code not in SOFT_REJECT_CODES:
        code = 'ACTION_BUSY'
    msg = message or SOFT_REJECT_MESSAGES.get(code, '当前操作暂不可用')
    ctx = _soft_reject_context(room, pidx)
    player = players.get(sid) or {}
    user_id = player.get('user_id')
    try:
        admin_event(
            'player',
            (
                f"soft_reject event={event_name} code={code} sid={sid} "
                f"user_id={user_id or '-'} room={ctx.get('room_id')} pidx={pidx} "
                f"phase={ctx.get('phase')} current={ctx.get('current_player')} "
                f"pending_response={ctx.get('has_pending_response')} "
                f"pending_choice={ctx.get('has_pending_choice')} "
                f"pending_v2_ui={ctx.get('has_pending_v2_ui')}"
            ),
            sid=sid,
            user_id=user_id,
            room_id=ctx.get('room_id'),
        )
    except Exception:
        pass
    def _emit_later(target_sid, target_room, target_pidx):
        try:
            socketio.sleep(0)
        except Exception:
            time.sleep(0.01)
        socketio.emit('action_rejected', {'event': event_name, 'code': code, 'message': msg}, room=target_sid)
        socketio.emit('server_error', {'message': msg, 'code': code}, room=target_sid)
        if send_state and target_room is not None:
            if target_pidx is not None and isinstance(target_pidx, int) and target_pidx >= 0:
                send_game_state_to(target_room, target_pidx)
            else:
                broadcast_game_state(target_room)

    try:
        socketio.start_background_task(_emit_later, sid, room, pidx)
    except Exception:
        threading.Thread(target=_emit_later, args=(sid, room, pidx), daemon=True).start()
    return None


def normalize_soft_reject_code(error):
    text = str(error or '').strip()
    if not text:
        return 'ACTION_BUSY'
    lowered = text.lower()
    if text in ('没有待选择操作', 'No pending choice'):
        return 'NO_PENDING_CHOICE'
    if text in ('选择已取消', 'Choice cancelled'):
        return 'CHOICE_CANCELLED'
    if text in ('没有待响应的操作', 'No pending response'):
        return 'RESPONSE_NOT_EXPECTED'
    if '等待对手反制' in text or '等待反制' in text or 'pending response' in lowered or 'response' in lowered and 'waiting' in lowered:
        return 'PENDING_RESPONSE'
    if '待选择' in text or 'pending choice' in lowered:
        return 'PENDING_CHOICE'
    if '窗口' in text or 'pending ui' in lowered or 'v2' in lowered:
        return 'PENDING_V2_UI'
    if '不是你的回合' in text or 'not your turn' in lowered or '还没轮到' in text:
        return 'NOT_YOUR_TURN'
    if '当前阶段' in text or 'phase' in lowered:
        return 'NOT_ACTION_PHASE'
    if '不能打出' in text or '无法打出' in text or 'not playable' in lowered or 'cannot play' in lowered:
        return 'CARD_NOT_PLAYABLE_NOW'
    if '不能触发' in text or '无法触发' in text or 'trigger' in lowered:
        return 'TRIGGER_NOT_PLAYABLE_NOW'
    if '结束回合' in text or 'end turn' in lowered:
        return 'END_TURN_NOT_ALLOWED_NOW'
    return None


def _try_acquire_room_action(room, sid, event_name, pidx=None):
    lock = getattr(room, 'action_lock', None)
    if lock is None:
        lock = threading.Lock()
        room.action_lock = lock
    if not lock.acquire(timeout=max(0.0, _ROOM_ACTION_LOCK_WAIT_SECONDS)):
        soft_reject(sid, event_name, 'ACTION_BUSY', room=room, pidx=pidx, send_state=True)
        return None
    return lock


def _room_action_precheck(engine, pidx, *, event_name):
    if getattr(engine, 'game_over', False):
        return 'NOT_ACTION_PHASE'
    if event_name not in ('response',) and getattr(engine, 'pending_response', None):
        return 'PENDING_RESPONSE'
    if event_name not in ('resolve_choice',) and getattr(engine, 'pending_choice', None):
        return 'PENDING_CHOICE'
    if event_name not in ('v2_ui_response',) and getattr(engine, 'pending_v2_ui', None):
        return 'PENDING_V2_UI'
    if event_name in ('play_card', 'use_trigger', 'end_turn'):
        if getattr(engine, 'phase', None) != 'action':
            return 'NOT_ACTION_PHASE'
        current_player = getattr(engine, 'current_player', None)
        if current_player != pidx:
            friendly_trigger = False
            if event_name == 'use_trigger':
                is_ally = getattr(engine, 'is_ally', None)
                if callable(is_ally):
                    try:
                        friendly_trigger = bool(is_ally(current_player, pidx))
                    except Exception:
                        friendly_trigger = False
            if not friendly_trigger:
                return 'NOT_YOUR_TURN'
    return None


def _stamp_pending_interactions(room):
    now = time.time()
    engine = getattr(room, 'engine', None)
    if engine is None:
        return
    for attr in ('pending_response', 'pending_choice', 'pending_v2_ui'):
        pending = getattr(engine, attr, None)
        if isinstance(pending, dict) and '_created_at' not in pending:
            pending['_created_at'] = now


def _socket_rate_allowed(sid, event_name, *, exempt=False):
    if exempt:
        return True
    limit, window = SOCKET_EVENT_LIMITS.get(event_name, SOCKET_DEFAULT_LIMIT)
    if not rate_limiter(f'socket:sid:{sid}:{event_name}', limit=limit, window=window):
        return False
    user_id = _security_user_id_for_sid(sid)
    if user_id and not rate_limiter(f'socket:user:{user_id}:{event_name}', limit=limit * 2, window=window):
        return False
    return True


def socket_guard(event_name, data=None, *, require_player=True, allow_empty=False, emit_error=True):
    sid = request.sid
    if data is None:
        payload = {}
    elif isinstance(data, dict):
        payload = data
    else:
        _security_illegal(sid, event_name, '参数格式错误', emit_error=emit_error, extra={'data_type': type(data).__name__})
        return None
    player = _security_player_for_sid(sid)
    if require_player and sid not in players:
        if event_name == 'update_mod_settings':
            emit('mod_settings_updated', {
                'ok': False,
                'reason': '连接已失效，请重新进入大厅后再保存模组设置。',
                'disabled_mods': [],
            })
            return None
        _security_illegal(sid, event_name, '玩家未登录', emit_error=emit_error)
        return None
    if not allow_empty and data is None:
        _security_illegal(sid, event_name, '缺少参数', emit_error=emit_error)
        return None
    exempt = is_chat_limit_exempt(player) if event_name == 'chat' else bool(player.get('is_admin_player'))
    if not _socket_rate_allowed(sid, event_name, exempt=exempt):
        if event_name == 'update_mod_settings':
            emit('mod_settings_updated', {
                'ok': False,
                'reason': '模组设置操作过于频繁，请稍后再试。',
                'disabled_mods': player.get('disabled_mods', []) if player else [],
            })
            return None
        if event_name in SOFT_REJECT_EVENT_NAMES:
            soft_reject(sid, event_name, 'ACTION_TOO_FAST')
        else:
            _security_illegal(sid, event_name, '操作过于频繁', emit_error=emit_error, severity='high')
        return None
    if player and player.get('status') == 'lobby' and event_name not in LOBBY_ACTIVITY_IGNORED_EVENTS:
        mark_lobby_activity(sid)
    return payload


def validate_instance_id(value, *, name='instance_id', required=True):
    text = validate_str(value, min_len=1 if required else 0, max_len=80, name=name)
    if text and not re.fullmatch(r'[A-Za-z0-9_.:\-]+', text):
        raise ValueError(f'{name} format is invalid')
    if re.fullmatch(r'\d+', text or ''):
        return validate_int(text, minimum=0, maximum=10**12, name=name)
    return text


def validate_socket_sid(value, *, name='sid'):
    return validate_str(value, min_len=1, max_len=120, pattern=r'[A-Za-z0-9_.:\-]+', name=name)


def validate_card_def_id(value, *, name='def_id'):
    return validate_str(value, min_len=1, max_len=80, pattern=r'[A-Za-z0-9_.:\-/]+', name=name)


def validate_tag_id_list(value, *, name='tags', maximum=12):
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError(f'{name} format is invalid')
    return [
        validate_str(item, min_len=1, max_len=80, pattern=r'[A-Za-z0-9_.:\-/]+', name=name)
        for item in value
    ]

SOLO_TRAINING_MIN_DECK_SIZE = 0
SOLO_TRAINING_MAX_DECK_SIZE = 100


def validate_solo_deck_entries(value, *, name='deck'):
    if (
        not isinstance(value, list)
        or len(value) < SOLO_TRAINING_MIN_DECK_SIZE
        or len(value) > SOLO_TRAINING_MAX_DECK_SIZE
    ):
        raise ValueError(f'{name} must contain {SOLO_TRAINING_MIN_DECK_SIZE}-{SOLO_TRAINING_MAX_DECK_SIZE} cards')
    clean = []
    for index, entry in enumerate(value):
        if isinstance(entry, dict):
            clean.append({
                'def_id': validate_card_def_id(entry.get('def_id'), name=f'{name}[{index}].def_id'),
                'instance_flags': validate_tag_id_list(entry.get('instance_flags'), name=f'{name}[{index}].instance_flags'),
                'disabled_flags': validate_tag_id_list(entry.get('disabled_flags'), name=f'{name}[{index}].disabled_flags'),
            })
        else:
            clean.append(validate_card_def_id(entry, name=f'{name}[{index}]'))
    return clean


def validate_choice_payload(choice, *, depth=0):
    if choice is None:
        return None
    if depth > 4:
        raise ValueError('choice too deep')
    if isinstance(choice, bool):
        return bool(choice)
    if isinstance(choice, int):
        return validate_int(choice, minimum=-1, maximum=1000000, name='choice')
    if isinstance(choice, str):
        return validate_str(choice, max_len=120, name='choice')
    if isinstance(choice, list):
        if len(choice) > 60:
            raise ValueError('choice list too long')
        return [validate_choice_payload(item, depth=depth + 1) for item in choice]
    if isinstance(choice, dict):
        if len(choice) > 30:
            raise ValueError('choice object too large')
        clean = {}
        for key, value in choice.items():
            safe_key = validate_str(key, min_len=1, max_len=64, pattern=r'[A-Za-z0-9_.:\-]+', name='choice key')
            clean[safe_key] = validate_choice_payload(value, depth=depth + 1)
        return clean
    raise ValueError('choice contains unsupported value')


def record_valid_player_action(room, player_index, action):
    if room is None or player_index is None or player_index < 0:
        return
    counts = getattr(room, '_valid_action_counts', None)
    if not isinstance(counts, dict):
        counts = {}
        room._valid_action_counts = counts
    counts[player_index] = int(counts.get(player_index, 0)) + 1
    room._last_valid_action = {
        'player_index': player_index,
        'action': action,
        'time': time.time(),
    }


def room_valid_actions_by_side(room):
    counts = getattr(room, '_valid_action_counts', {}) or {}
    if getattr(room, 'mode', '') == '2v2' and hasattr(getattr(room, 'engine', None), 'teams'):
        return [
            sum(int(counts.get(pidx, 0)) for pidx in team)
            for team in getattr(room.engine, 'teams', [[0, 1], [2, 3]])
        ]
    return [int(counts.get(0, 0)), int(counts.get(1, 0))]


def is_room_valid_for_ranking(room, result='finished'):
    if not room or str(result) != 'finished':
        return False, 'abnormal_result'
    if not getattr(getattr(room, 'engine', None), 'game_over', False):
        return False, 'not_game_over'
    participant_meta = [room_player_profile(room, psid) for psid in getattr(room, 'player_sids', [])]
    if not participant_meta or not any(meta.get('is_registered_user') for meta in participant_meta):
        return False, 'no_registered_player'
    if any(meta.get('entertainment_mods') for meta in participant_meta):
        return False, 'entertainment_mod'
    started_ts = getattr(room, 'started_at', None) or getattr(room, 'created_at', time.time())
    if time.time() - started_ts < RANKING_MIN_DURATION_SECONDS:
        return False, 'too_short'
    side_counts = room_valid_actions_by_side(room)
    if len(side_counts) < 2 or any(count < RANKING_MIN_ACTIONS_PER_SIDE for count in side_counts[:2]):
        return False, 'not_enough_actions'
    return True, ''


def _set_account_session(user):
    if not user:
        return
    session.permanent = True
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['password_changed_at'] = user.get('password_changed_at') or ''


def _clear_account_session():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('password_changed_at', None)


def _account_session_is_current(user):
    if not user:
        return False
    session_stamp = str(session.get('password_changed_at') or '')
    user_stamp = str(user.get('password_changed_at') or '')
    return session_stamp == user_stamp


def _disconnect_account_sockets(user_id, reason, code='account_session_invalidated'):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return 0
    with _lock:
        sids = [sid for sid, player in players.items() if player.get('user_id') == uid]
    payload = {'reason': reason, 'code': code}
    for sid in sids:
        try:
            socketio.emit('account_session_replaced', payload, room=sid)
            socketio.emit('kicked', payload, room=sid)
            socketio.server.disconnect(sid)
        except Exception as exc:
            admin_event('error', f'account session disconnect failed: {exc}', sid=sid)
    return len(sids)


def _attach_remember_cookie(response, user):
    if not DB_AVAILABLE or not user:
        return response
    token = create_remember_token(user.get('id'))
    if token:
        response.set_cookie(
            REMEMBER_COOKIE_NAME,
            token,
            max_age=60 * 60 * 24 * 60,
            httponly=True,
            samesite='Lax',
        )
    return response


def _clear_remember_cookie(response):
    if DB_AVAILABLE:
        try:
            revoke_remember_token(request.cookies.get(REMEMBER_COOKIE_NAME, ''))
        except Exception as exc:
            admin_event('error', f'failed to revoke remember token: {exc}')
    response.delete_cookie(REMEMBER_COOKIE_NAME, samesite='Lax')
    return response


def _current_account_user(allow_remember=True):
    if not DB_AVAILABLE:
        return None
    user = get_user_by_id(session.get('user_id'))
    if user:
        if user.get('deleted'):
            _clear_account_session()
            return None
        if not _account_session_is_current(user):
            _clear_account_session()
            return None
        _set_account_session(user)
        return user
    _clear_account_session()
    if not allow_remember:
        return None
    user = verify_remember_token(request.cookies.get(REMEMBER_COOKIE_NAME, ''))
    if user:
        if user.get('deleted'):
            return None
        _set_account_session(user)
        return user
    return None


def _rate_limited(ip, bucket, limit=3, window=60):
    now = time.time()
    key = (bucket, ip)
    hits = [ts for ts in _COMMUNITY_API_RATE.get(key, []) if now - ts < window]
    if len(hits) >= limit:
        _COMMUNITY_API_RATE[key] = hits
        return True
    hits.append(now)
    _COMMUNITY_API_RATE[key] = hits
    return False


def _json_error(message, status=400, **extra):
    payload = {'success': False, 'error': str(message)}
    payload.update(extra)
    return jsonify(payload), status


def _current_account_identity():
    user = _current_account_user()
    if not user:
        return None, ''
    return user.get('id'), str(user.get('username') or '')


def _current_account_can_manage_all_community_mods():
    profile = get_special_account_profile(session.get('username') or '')
    return bool(profile and profile.get('is_admin_player'))


def _require_account_json():
    user_id, username = _current_account_identity()
    if not user_id:
        return None, None, _json_error('请先登录账号', 401)
    return user_id, username, None


def _report_target_user(target_user_id=None, target_username=''):
    target = None
    if target_user_id not in (None, ''):
        target = get_user_by_id(target_user_id)
    if target is None and target_username:
        target = get_user_by_username(target_username)
    if target:
        return target.get('id'), target.get('username')
    try:
        return int(target_user_id), str(target_username or '')
    except (TypeError, ValueError):
        return None, str(target_username or '')[:80]


def _collect_report_evidence(object_type, object_id, reporter_user_id=None):
    evidence = [{
        'evidence_type': 'request',
        'data': {
            'object_type': object_type,
            'object_id': object_id,
            'reporter_user_id': reporter_user_id,
            'ip': _client_ip(),
            'time': iso_now(),
        },
    }]
    try:
        if object_type == 'chat_message':
            context = get_chat_message_with_context(object_id, context_limit=10)
            if context:
                evidence.append({'evidence_type': 'chat_context', 'data': context})
        elif object_type in ('match', 'replay'):
            oid = str(object_id)
            with _lock:
                history_match = next((item for item in MATCH_HISTORY if str(item.get('room_id')) == oid or str(item.get('id', '')) == oid), None)
                if history_match:
                    evidence.append({'evidence_type': 'match_summary', 'data': history_match})
                if oid.isdigit() and int(oid) in rooms:
                    room = rooms[int(oid)]
                    evidence.append({'evidence_type': 'active_room', 'data': {
                        'room_id': room.room_id,
                        'mode': room.mode,
                        'phase': getattr(room.engine, 'phase', ''),
                        'round': getattr(room.engine, 'round_num', 0),
                        'players': [room_player_nickname(room, psid) for psid in room.player_sids],
                    }})
        elif object_type == 'player':
            with _lock:
                target = str(object_id)
                for psid, player in players.items():
                    if target in {psid, str(player.get('user_id') or ''), str(player.get('nickname') or '')}:
                        evidence.append({'evidence_type': 'player_snapshot', 'data': public_player_info(psid, player)})
                        break
    except Exception as exc:
        evidence.append({'evidence_type': 'collection_error', 'data': {'error': str(exc)[:300]}})
    return evidence


def _online_sids_for_user(user_id=None, username=''):
    found = []
    key = normalize_username_key(username) if username else ''
    for sid, player in players.items():
        if user_id and player.get('user_id') == user_id:
            found.append(sid)
        elif key and normalize_username_key(player.get('nickname', '')) == key:
            found.append(sid)
    return found


def _apply_report_moderation_action(report_detail, moderation_action, duration_seconds=0, note='', party='target'):
    action = str(moderation_action or 'none').strip().lower()
    if action == 'none' or not report_detail:
        return
    party = 'reporter' if str(party or '').strip().lower() == 'reporter' else 'target'
    target_user_id = report_detail.get(f'{party}_user_id')
    target_username = report_detail.get(f'{party}_username') or ''
    if action == 'mute' and target_user_id:
        seconds = max(60, min(int(duration_seconds or 600), 60 * 60 * 24 * 1000))
        set_user_mute(target_user_id, target_username, seconds, note, session.get('username') or ADMIN_PLAYER_DISPLAY_NAME)
        for sid in _online_sids_for_user(target_user_id, target_username):
            mute_user(chat_mute_key(sid, players.get(sid, {})), seconds, note)
            socketio.emit('server_error', muted_error_payload(seconds, message='你已被管理员禁言'), room=sid)
    elif action == 'ban' and (target_user_id or target_username):
        target = target_user_id or target_username
        try:
            duration = int(duration_seconds or 0) if str(duration_seconds or '').strip() else None
        except (TypeError, ValueError):
            duration = None
        user, _ = admin_set_user_ban(target, True, note, duration_seconds=duration)
        clear_leaderboard_cache()
        status = get_user_ban_status(user_id=(user or {}).get('id'), username=target_username) if user else {'banned': True, 'reason': note, 'remaining_seconds': duration, 'permanent': duration is None}
        for sid in _online_sids_for_user(target_user_id, target_username):
            socketio.emit('server_error', {'message': ban_error_payload(status).get('reason', '账号已被封禁')}, room=sid)
            socketio.emit('kicked', {'reason': 'account banned'}, room=sid)
            socketio.server.disconnect(sid)
    elif action == 'warn':
        try:
            duration = int(duration_seconds or 0)
        except (TypeError, ValueError):
            duration = 0
        if duration <= 0:
            duration = 60 * 60
        try:
            expires_at = (datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=duration)).isoformat().replace('+00:00', 'Z')
        except Exception:
            expires_at = ''
        payload = {
            'message': note or '请注意游戏内行为',
            'expires_at': expires_at,
            'duration_seconds': duration,
        }
        for sid in _online_sids_for_user(target_user_id, target_username):
            socketio.emit('account_warning', payload, room=sid)
            socketio.emit('server_error', {'message': f'管理员警告：{payload["message"]}'}, room=sid)


def _community_request_fields(data):
    data = data or {}
    community_mods = _normalize_community_mod_entries(data.get('community_mods'))
    if not community_mods:
        legacy_url = str(data.get('community_mod_url') or '').strip()
        legacy_hash = _normalize_community_hash(data.get('community_mod_hash'))
        if legacy_url and legacy_hash:
            community_mods = [{
                'public_url': legacy_url,
                'sha256': legacy_hash,
                'name': str(data.get('community_mod_name') or '').strip()[:80],
            }]
    source = normalize_mod_source(data.get('mod_source'))
    if community_mods:
        source = 'community'
    combined_hash = _community_combined_hash(community_mods)
    return {
        'mod_source': source,
        'community_mods': community_mods,
        'community_mod_url': community_mods[0]['public_url'] if len(community_mods) == 1 else '',
        'community_mod_hash': combined_hash,
        'community_mod_name': _community_combined_names(community_mods),
    }


def _community_source_hash(source):
    if isinstance(source, dict):
        return str(source.get('hash') or '').strip()
    return str(source or '').strip()


def _community_source_uploaded_at(source):
    if isinstance(source, dict):
        return str(source.get('uploaded_at') or '').strip()
    return ''


def _community_source_upload_order(source):
    if isinstance(source, dict):
        try:
            return float(source.get('upload_order') or 0)
        except Exception:
            return 0.0
    return 0.0


def _community_upload_order(value):
    text = str(value or '').strip()
    if not text:
        return 0.0
    try:
        if text.endswith('Z'):
            text = text[:-1] + '+00:00'
        return datetime.fromisoformat(text).timestamp()
    except Exception:
        return 0.0


def merge_community_mod_to_card_defs(mod):
    if not mod:
        return []
    mod_hash = getattr(mod, 'community_sha256', '') or ''
    uploaded_at = getattr(mod, 'community_uploaded_at', '') or ''
    upload_order = _community_upload_order(uploaded_at) or time.time()
    mod_name = mod.info.name if getattr(mod, 'info', None) and mod.info.name else 'Community Mod'
    merged = []
    for mc in mod.cards:
        if not mc.id or mc.id == ERROR_CARD_ID:
            continue
        existing_source = COMMUNITY_CARD_SOURCES.get(mc.id)
        existing_hash = _community_source_hash(existing_source)
        if existing_hash and existing_hash != mod_hash:
            existing_order = (
                _community_source_upload_order(existing_source)
                or _community_upload_order(_community_source_uploaded_at(existing_source))
            )
            if existing_order > upload_order:
                continue
        CARD_DEFS[mc.id] = mc.to_card_def()
        COMMUNITY_CARD_SOURCES[mc.id] = {
            'hash': mod_hash,
            'url': getattr(mod, 'community_url', '') or '',
            'uploaded_at': uploaded_at,
            'upload_order': upload_order,
            'name': mod_name,
            'sort_name': mod_name,
        }
        merged.append(mc.id)
    if merged:
        apply_card_i18n_defaults(CARD_DEFS)
    return merged


def resolve_community_loadout(data):
    fields = _community_request_fields(data)
    if fields['mod_source'] != 'community':
        return fields, []
    if not fields['community_mods']:
        raise ValueError('缺少社区模组 URL 或 hash')
    reload_mod_card_defs()
    loaded_mods = []
    normalized_entries = []
    for entry in fields['community_mods']:
        mod = load_community_mod(entry['public_url'], entry['sha256'])
        if entry.get('uploaded_at') and not getattr(mod, 'community_uploaded_at', ''):
            mod.community_uploaded_at = entry.get('uploaded_at')
        merge_community_mod_to_card_defs(mod)
        name = entry.get('name') or (mod.info.name if mod.info and mod.info.name else 'Community Mod')
        normalized_entries.append({
            'public_url': entry['public_url'],
            'sha256': entry['sha256'],
            'name': name,
            'uploaded_at': getattr(mod, 'community_uploaded_at', '') or entry.get('uploaded_at', ''),
        })
        loaded_mods.append(mod)
    fields['community_mods'] = normalized_entries
    fields['community_mod_hash'] = _community_combined_hash(normalized_entries)
    fields['community_mod_url'] = normalized_entries[0]['public_url'] if len(normalized_entries) == 1 else ''
    fields['community_mod_name'] = _community_combined_names(normalized_entries)
    return fields, loaded_mods


CONTENT_DISABLE_SCOPES = ('all', '1v1', '2v2', 'urf', 'random_deck', 'solo', 'tutorial')
CONTENT_DISABLE_CACHE_SECONDS = 5.0
CONTENT_DISABLE_FORCE_CARD_IDS = frozenset(BUILTIN_SETUP_CARD_IDS | {'Sewage'})
_CONTENT_DISABLE_CACHE = {'ts': 0.0, 'rows': []}
_CONTENT_DISABLE_CACHE_LOCK = threading.Lock()


def invalidate_content_disable_cache():
    with _CONTENT_DISABLE_CACHE_LOCK:
        _CONTENT_DISABLE_CACHE['ts'] = 0.0
        _CONTENT_DISABLE_CACHE['rows'] = []


def active_content_disables(mode=None, force=False):
    if not DB_AVAILABLE:
        return []
    now = time.time()
    with _CONTENT_DISABLE_CACHE_LOCK:
        if force or now - float(_CONTENT_DISABLE_CACHE.get('ts') or 0) >= CONTENT_DISABLE_CACHE_SECONDS:
            try:
                _CONTENT_DISABLE_CACHE['rows'] = list_content_disables()
                _CONTENT_DISABLE_CACHE['ts'] = now
            except Exception as exc:
                admin_event('error', f'content disable load failed: {exc}')
        rows = [dict(row) for row in (_CONTENT_DISABLE_CACHE.get('rows') or [])]
    scope = str(mode or '').strip().lower()
    if scope == 'any':
        return rows
    if not scope:
        return [row for row in rows if row.get('scope_mode') == 'all']
    return [row for row in rows if row.get('scope_mode') in ('all', scope)]


def runtime_disabled_content(mode=None):
    rows = active_content_disables(mode)
    return {
        'rows': rows,
        'cards': {str(row.get('content_id')) for row in rows if row.get('content_type') == 'card'},
        'mods': {str(row.get('content_id')) for row in rows if row.get('content_type') == 'mod'},
    }


def runtime_disabled_mod_card_ids(mod_filenames):
    disabled = set(mod_filenames or [])
    result = set()
    if not disabled:
        return result
    for mod in load_all_mods():
        if mod.filename not in disabled:
            continue
        result.update(
            card.id for card in mod.cards
            if card.id in CARD_DEFS and card.id not in ALL_MOD_SHARED_CARD_IDS
        )
    return result


def apply_runtime_content_filter(card_ids, mode=None):
    allowed = set(card_ids or [])
    disabled = runtime_disabled_content(mode)
    allowed.difference_update(disabled['cards'])
    allowed.difference_update(runtime_disabled_mod_card_ids(disabled['mods']))
    if VANILLA_MOD_FILENAME in disabled['mods']:
        allowed.difference_update(BUILTIN_SETUP_CARD_IDS)
    return allowed


def runtime_card_pool_issue(card_ids, mode='1v1'):
    if mode not in ('1v1', '2v2', 'random_deck'):
        return ''
    counts = {card_type: 0 for card_type in REQUIRED_CARD_TYPES}
    for card_id in set(card_ids or []):
        card_def = CARD_DEFS.get(card_id)
        if not card_def or card_def.card_type not in counts:
            continue
        counts[card_def.card_type] += max(0, int(getattr(card_def, 'count', 0) or 0))
    missing = [
        f'{card_type} {counts.get(card_type, 0)}/{required}'
        for card_type, required in DRAFT_RATIO.items()
        if counts.get(card_type, 0) < required
    ]
    return '临时停用后牌池不足：' + '，'.join(missing) if missing else ''


def get_enabled_mod_card_type_counts(disabled_mods=None):
    disabled = set(normalize_disabled_mods(disabled_mods))
    counts = {card_type: 0 for card_type in REQUIRED_CARD_TYPES}
    has_enabled_mod = False
    for mod in load_all_mods():
        if mod.errors:
            continue
        if mod.filename in disabled:
            continue
        has_enabled_mod = True
        if getattr(mod, 'format_version', 1) == 2:
            for card in getattr(mod, 'registries', {}).get('cards', []) or []:
                data = card.to_dict() if hasattr(card, 'to_dict') else dict(card or {})
                card_type = _v2_card_type(data.get('card_type', data.get('type', 'bloom')))
                if _v2_int(data.get('count', data.get('weight', 3)), 3) > 0 and card_type in counts:
                    counts[card_type] += 1
        else:
            for card in mod.cards:
                if card.id in CARD_DEFS and card.count > 0 and card.card_type in counts:
                    counts[card.card_type] += 1
    if has_enabled_mod and 'Sewage' in ALL_MOD_SHARED_CARD_IDS and 'Sewage' in CARD_DEFS:
        counts['bloom'] += 1
    return counts


def has_required_mod_card_types(disabled_mods=None):
    counts = get_enabled_mod_card_type_counts(disabled_mods)
    return all(counts.get(card_type, 0) > 0 for card_type in REQUIRED_CARD_TYPES)


def ensure_valid_disabled_mods(disabled_mods=None):
    disabled = set(normalize_disabled_mods(disabled_mods))
    if not has_required_mod_card_types(disabled):
        disabled.discard(VANILLA_MOD_FILENAME)
    return sorted(disabled)


def get_allowed_card_ids(disabled_mods=None):
    disabled = set(ensure_valid_disabled_mods(disabled_mods))
    allowed = {ERROR_CARD_ID}
    if VANILLA_MOD_FILENAME not in disabled:
        allowed.update(BUILTIN_SETUP_CARD_IDS)
    for mod in load_all_mods():
        if mod.errors:
            continue
        if mod.filename in disabled:
            continue
        for card in mod.cards:
            if card.id in CARD_DEFS:
                allowed.add(card.id)
    if len(allowed) > 1:
        allowed.update(card_id for card_id in ALL_MOD_SHARED_CARD_IDS if card_id in CARD_DEFS)
    return allowed


def get_card_mod_sources(disabled_mods=None):
    disabled = set(ensure_valid_disabled_mods(disabled_mods))
    sources = {}
    for mod in load_all_mods():
        if mod.errors or mod.filename in disabled:
            continue
        info = mod.info
        mod_name = info.name if info and info.name else mod.filename
        mod_name_cn = info.name_cn if info and getattr(info, 'name_cn', '') else mod_name
        mod_name_en = info.name_en if info and getattr(info, 'name_en', '') else mod_name
        mod_name_i18n = copy.deepcopy(getattr(info, 'name_i18n', {}) or {}) if info else {}
        mod_sort_name = mod_name or mod.filename
        for card in mod.cards:
            if card.id in CARD_DEFS:
                sources[card.id] = {
                    'filename': mod.filename,
                    'name': mod_name,
                    'name_cn': mod_name_cn,
                    'name_en': mod_name_en,
                    'name_i18n': mod_name_i18n,
                    'sort_name': mod_sort_name,
                    'is_vanilla': mod.filename == VANILLA_MOD_FILENAME,
                }
    return sources


def get_all_mod_shared_card_memberships():
    memberships = {card_id: [] for card_id in ALL_MOD_SHARED_CARD_IDS}
    for mod in sort_mods_for_display(load_all_mods()):
        if mod.errors:
            continue
        info = mod.info
        mod_name = info.name if info and info.name else mod.filename
        mod_name_cn = info.name_cn if info and getattr(info, 'name_cn', '') else mod_name
        mod_name_en = info.name_en if info and getattr(info, 'name_en', '') else mod_name
        mod_name_i18n = copy.deepcopy(getattr(info, 'name_i18n', {}) or {}) if info else {}
        entry = {
            'key': 'vanilla' if mod.filename == VANILLA_MOD_FILENAME else mod.filename,
            'filename': mod.filename,
            'name': mod_name,
            'name_cn': mod_name_cn,
            'name_en': mod_name_en,
            'name_i18n': mod_name_i18n,
            'sort_name': mod_name or mod.filename,
            'is_vanilla': mod.filename == VANILLA_MOD_FILENAME,
            'is_community': False,
        }
        for card_id in memberships:
            memberships[card_id].append(dict(entry))
    return memberships


def _v2_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _v2_card_type(value):
    text = str(value or '').strip().lower()
    return {
        'attack': 'thorn',
        'skill': 'bloom',
        'equipment': 'root',
        'counter': 'guard',
        'thorn': 'thorn',
        'bloom': 'bloom',
        'root': 'root',
        'guard': 'guard',
    }.get(text, 'bloom')


def _v2_card_name_from_id(card_id):
    path = str(card_id or '').split(':')[-1]
    return ' '.join(part.capitalize() for part in path.replace('/', '_').split('_') if part) or str(card_id or 'Card')


def register_v2_loadout_cards(v2_loadout):
    registered = []
    if not v2_loadout or not getattr(v2_loadout, 'ok', False):
        return registered
    cards = getattr(v2_loadout, 'registries', {}).get('cards', {}) or {}
    for card_id, resource in cards.items():
        if not isinstance(resource, dict):
            continue
        runtime_id = str(resource.get('legacy_id') or resource.get('runtime_id') or card_id)
        cost = resource.get('cost') if isinstance(resource.get('cost'), dict) else {}
        flags = normalize_card_flags(resource.get('flags', []) if isinstance(resource.get('flags', []), list) else [])
        if isinstance(resource.get('tags'), list):
            for tag in resource.get('tags') or []:
                tag_text = str(tag)
                if tag_text.startswith('gtn:'):
                    tag_text = tag_text.split(':', 1)[1]
                flags.add(normalize_card_flag(tag_text))
        card_def = CardDef(
            id=runtime_id,
            name_en=str(resource.get('name_en') or resource.get('name') or _v2_card_name_from_id(card_id)),
            name_cn=str(resource.get('name_cn') or resource.get('name') or resource.get('name_en') or _v2_card_name_from_id(card_id)),
            cost_e=_v2_int(resource.get('cost_e', cost.get('e', 0)), 0),
            cost_m=_v2_int(resource.get('cost_m', cost.get('m', 0)), 0),
            card_type=_v2_card_type(resource.get('card_type', resource.get('type', 'bloom'))),
            count=max(0, _v2_int(resource.get('count', resource.get('weight', 3)), 3)),
            quality=str(resource.get('quality') or 'Common'),
            description=str(resource.get('description') or resource.get('description_cn') or ''),
            effect_text=str(resource.get('effect_text') or resource.get('effect_text_cn') or ''),
            name_i18n=dict(resource.get('name_i18n') or {}) if isinstance(resource.get('name_i18n'), dict) else {},
            description_i18n=dict(resource.get('description_i18n') or {}) if isinstance(resource.get('description_i18n'), dict) else {},
            effect_text_i18n=dict(resource.get('effect_text_i18n') or {}) if isinstance(resource.get('effect_text_i18n'), dict) else {},
            flags=flags,
            trigger_cost_e=_v2_int(resource.get('trigger_cost_e', -1), -1),
            trigger_cost_m=_v2_int(resource.get('trigger_cost_m', 0), 0),
            trigger_effect_text=str(resource.get('trigger_effect_text') or ''),
            trigger_effect_text_i18n=dict(resource.get('trigger_effect_text_i18n') or {}) if isinstance(resource.get('trigger_effect_text_i18n'), dict) else {},
            response_trigger=str(resource.get('response_trigger') or ''),
            effects=[],
            scripts={},
            response_title=str(resource.get('response_title') or ''),
            response_content=str(resource.get('response_content') or ''),
            response_title_i18n=dict(resource.get('response_title_i18n') or {}) if isinstance(resource.get('response_title_i18n'), dict) else {},
            response_content_i18n=dict(resource.get('response_content_i18n') or {}) if isinstance(resource.get('response_content_i18n'), dict) else {},
            v2_events=resource.get('events') if isinstance(resource.get('events'), dict) else {},
            v2_resource=dict(resource),
            v2_mod_id=str(resource.get('_mod_id') or ''),
            image=str(resource.get('image') or ''),
            image_url=str(resource.get('image_url') or resource.get('image') or ''),
            upgraded_image=str(resource.get('upgraded_image') or ''),
            upgraded_image_url=str(resource.get('upgraded_image_url') or resource.get('upgraded_image') or ''),
            copy_count=_v2_int(resource.get('copy_count', 0), 0),
            swift_value=_v2_int(resource.get('swift_value', 0), 0),
            magic_swift_value=_v2_int(resource.get('magic_swift_value', 0), 0),
            fission_level=max(1, _v2_int(resource.get('fission_level', _v2_int(resource.get('fission_count', 0), 0) + 1), 1)),
            fusion_level=max(1, _v2_int(resource.get('fusion_level', resource.get('fusion_multiplier', 1)), 1)),
            damage=_v2_int(resource.get('damage', 0), 0),
            hits=_v2_int(resource.get('hits', 1), 1),
            ui_effect_size=str(resource.get('ui_effect_size') or ''),
        )
        CARD_DEFS[runtime_id] = card_def
        registered.append(runtime_id)
    if registered:
        apply_card_i18n_defaults(CARD_DEFS)
    return registered


def build_mod_loadout(disabled_mods=None, community_mod=None, community_hash='', community_mods=None, runtime_mode=None):
    mods = load_all_mods()
    disabled = set(normalize_disabled_mods(disabled_mods))
    counts = {card_type: 0 for card_type in REQUIRED_CARD_TYPES}
    has_enabled_official_mod = False
    for mod in mods:
        if mod.errors or mod.filename in disabled:
            continue
        has_enabled_official_mod = True
        for card in mod.cards:
            if card.id in CARD_DEFS and card.count > 0 and card.card_type in counts:
                counts[card.card_type] += 1
    if has_enabled_official_mod and 'Sewage' in ALL_MOD_SHARED_CARD_IDS and 'Sewage' in CARD_DEFS:
        counts['bloom'] += 1
    if not all(counts.get(card_type, 0) > 0 for card_type in REQUIRED_CARD_TYPES):
        disabled.discard(VANILLA_MOD_FILENAME)
    disabled = sorted(disabled)
    disabled_set = set(disabled)
    runtime_disabled = runtime_disabled_content(runtime_mode)
    import hashlib as _hl
    _h = _hl.sha256()
    active_mods = []
    entertainment_mods = []
    allowed_card_ids = {ERROR_CARD_ID}
    if VANILLA_MOD_FILENAME not in disabled_set:
        allowed_card_ids.update(BUILTIN_SETUP_CARD_IDS)
    v2_mods = []
    for mod in sort_mods_for_display(mods):
        if mod.filename in disabled_set or mod.errors:
            continue
        active_mods.append(mod.info.name if mod.info else mod.filename)
        if mod_category(mod) == 'entertainment':
            entertainment_mods.append(mod.filename)
        _h.update(f'{mod.filename}:{mod.validation_hash or ""}'.encode('utf-8'))
        if getattr(mod, 'format_version', 1) == 2:
            v2_mods.append(mod)
        for card in mod.cards:
            if card.id in CARD_DEFS:
                allowed_card_ids.add(card.id)
    selected_community_mods = []
    if community_mods is not None:
        selected_community_mods = list(community_mods or [])
    elif community_mod:
        selected_community_mods = list(community_mod) if isinstance(community_mod, (list, tuple)) else [community_mod]
    selected_community_mods.sort(key=lambda item: getattr(item, 'community_sha256', '') or '')
    selected_community_hashes = []
    for community_item in selected_community_mods:
        label = community_item.info.name if community_item.info and community_item.info.name else 'Community Mod'
        selected_hash = getattr(community_item, "community_sha256", "") or ''
        selected_community_hashes.append(selected_hash)
        active_mods.append(label)
        _h.update(f'community:{selected_hash}'.encode('utf-8'))
        if getattr(community_item, 'format_version', 1) == 2:
            v2_mods.append(community_item)
        for card in community_item.cards:
            if card.id in CARD_DEFS:
                allowed_card_ids.add(card.id)
    if community_hash and not selected_community_hashes:
        _h.update(f'community:{community_hash}'.encode('utf-8'))
    legacy_hash = _h.hexdigest()
    v2_loadout = build_v2_loadout(v2_mods)
    if not v2_loadout.ok:
        raise ValueError('v2 模组组合错误: ' + '; '.join(v2_loadout.errors))
    v2_card_ids = register_v2_loadout_cards(v2_loadout)
    for card_id in v2_card_ids:
        allowed_card_ids.add(card_id)
    if active_mods:
        allowed_card_ids.update(card_id for card_id in ALL_MOD_SHARED_CARD_IDS if card_id in CARD_DEFS)
    allowed_card_ids = apply_runtime_content_filter(allowed_card_ids, runtime_mode)
    if v2_loadout.warnings:
        for warning in v2_loadout.warnings:
            print(f'[v2 loadout] {warning}')
    combined_loadout_hash = sha256_json({
        'legacy_hash': legacy_hash,
        'v2_loadout_hash': v2_loadout.loadout_hash,
    })
    return {
        'disabled_mods': disabled,
        'mods_hash': legacy_hash,
        'loadout_hash': combined_loadout_hash,
        'v2_loadout_hash': v2_loadout.loadout_hash,
        'v2_load_order': v2_loadout.load_order,
        'v2_mod_hashes': v2_loadout.mod_hashes,
        'v2_ui_components': dict(v2_loadout.registries.get('ui_components') or {}),
        'v2_loadout': v2_loadout,
        'v2_tag_defs': dict(v2_loadout.registries.get('tags') or {}),
        'v2_status_defs': dict(v2_loadout.registries.get('statuses') or {}),
        'v2_opening_event_defs': dict(v2_loadout.registries.get('opening_events') or {}),
        'mods_list': active_mods,
        'entertainment_mods': sorted(entertainment_mods),
        'allowed_card_ids': allowed_card_ids,
        'runtime_disabled_content': runtime_disabled['rows'],
    }


def apply_mod_loadout_to_player(player, loadout, community_fields=None):
    community_fields = community_fields or {}
    player['disabled_mods'] = loadout['disabled_mods']
    player['mods_hash'] = loadout['mods_hash']
    player['loadout_hash'] = loadout['loadout_hash']
    player['v2_loadout_hash'] = loadout.get('v2_loadout_hash', '')
    player['v2_load_order'] = loadout.get('v2_load_order', [])
    player['v2_mod_hashes'] = loadout.get('v2_mod_hashes', {})
    player['v2_ui_components'] = loadout.get('v2_ui_components', {})
    player['v2_loadout'] = loadout.get('v2_loadout')
    player['v2_tag_defs'] = loadout.get('v2_tag_defs', {})
    player['v2_status_defs'] = loadout.get('v2_status_defs', {})
    player['v2_opening_event_defs'] = loadout.get('v2_opening_event_defs', {})
    player['mods_list'] = loadout['mods_list']
    player['entertainment_mods'] = list(loadout.get('entertainment_mods', []))
    player['allowed_card_ids'] = loadout['allowed_card_ids']
    player['mod_source'] = community_fields.get('mod_source', 'official')
    player['community_mod_url'] = community_fields.get('community_mod_url', '')
    player['community_mod_hash'] = community_fields.get('community_mod_hash', '')
    player['community_mod_name'] = community_fields.get('community_mod_name', '')
    player['community_mods'] = community_fields.get('community_mods', [])


def has_mod_loadout_payload(data):
    if not isinstance(data, dict):
        return False
    return any(key in data for key in (
        'disabled_mods',
        'mod_source',
        'community_mod_url',
        'community_mod_hash',
        'community_mod_name',
        'community_mods',
    ))


def resolve_mod_loadout_payload(data):
    community_fields, community_mod = resolve_community_loadout(data or {})
    loadout = build_mod_loadout(
        (data or {}).get('disabled_mods', []),
        community_mod=community_mod,
        community_hash=community_fields.get('community_mod_hash', ''),
        runtime_mode=(data or {}).get('_runtime_mode') or (data or {}).get('mode'),
    )
    return community_fields, loadout


def player_loadout_hash(player):
    if not player:
        return ''
    return player.get('loadout_hash') or player.get('mods_hash') or ''


def player_mod_match_payload(player):
    player = player or {}
    return {
        'disabled_mods': list(player.get('disabled_mods', []) or []),
        'mod_source': player.get('mod_source', 'official') or 'official',
        'community_mods': list(player.get('community_mods', []) or []),
        'community_mod_url': player.get('community_mod_url', '') or '',
        'community_mod_hash': player.get('community_mod_hash', '') or '',
        'community_mod_name': player.get('community_mod_name', '') or '',
        'loadout_hash': player_loadout_hash(player),
        'mods_list': list(player.get('mods_list', []) or []),
        'entertainment_mods': list(player.get('entertainment_mods', []) or []),
    }


def emit_mod_mismatch(target_sid, other_player=None, message='模组组合不一致，无法开始对局'):
    if target_sid not in players:
        return
    payload = {
        'message': message,
        'reason': 'mod_mismatch',
        'your_mods': player_mod_match_payload(players.get(target_sid, {})),
        'other_mods': player_mod_match_payload(other_player or {}),
    }
    socketio.emit('mod_mismatch', payload, room=target_sid)
    socketio.emit('server_error', {'message': message, 'reason': 'mod_mismatch'}, room=target_sid)


def runtime_scope_key(beta_mode=False):
    return 'beta' if bool(beta_mode) else 'release'


def player_runtime_scope(player):
    return runtime_scope_key((player or {}).get('beta_mode', False))


def room_runtime_scope(room):
    return runtime_scope_key(getattr(room, 'beta_mode', False))


def same_runtime_scope_players(*items):
    scopes = set()
    for item in items:
        if isinstance(item, str):
            player = players.get(item)
            if player is None:
                return False
            scopes.add(player_runtime_scope(player))
        elif isinstance(item, dict):
            scopes.add(player_runtime_scope(item))
        elif isinstance(item, GameRoom):
            scopes.add(room_runtime_scope(item))
        else:
            scopes.add(runtime_scope_key(bool(item)))
    return len(scopes) <= 1


def same_runtime_scope_sids(sids):
    return same_runtime_scope_players(*list(sids or []))


def runtime_scope_mismatch_message():
    return '内测版和正式版不能互相联机，请切换到相同入口后再开始对局'


def same_mod_loadout(sids):
    hashes = []
    for sid in sids:
        if sid not in players:
            return False
        hashes.append(player_loadout_hash(players[sid]))
    return len(set(hashes)) <= 1


def emit_match_start_failed(sids, message, reason='mod_mismatch'):
    payload = {'message': message, 'reason': reason}
    for psid in set(sids or []):
        if psid in players:
            socketio.emit('match_start_failed', payload, room=psid)


def has_reconnect_candidate_locked(nickname='', user_id=None, account_player_id='', beta_mode=False,
                                   desired_room_id=None, desired_match_key=''):
    room, old_sid = find_reconnect_candidate_locked(
        nickname=nickname,
        user_id=user_id,
        account_player_id=account_player_id,
        beta_mode=beta_mode,
        desired_room_id=desired_room_id,
        desired_match_key=desired_match_key,
    )
    return bool(room and old_sid)


def _room_can_offer_reconnect(room, beta_mode=False):
    if not room or bool(getattr(room, 'beta_mode', False)) != bool(beta_mode):
        return False
    engine = getattr(room, 'engine', None)
    if engine is None or getattr(engine, 'game_over', False) or getattr(engine, 'phase', '') == 'game_over':
        return False
    return True


def _profile_slot_is_reconnectable(room, profile_sid, profile):
    if not isinstance(profile, dict) or profile_sid in players:
        return False
    try:
        pidx = int(profile.get('player_index', -1))
    except Exception:
        pidx = -1
    current_sids = list(getattr(room, 'player_sids', []) or [])
    if pidx < 0 or pidx >= len(current_sids):
        return False
    current_sid = current_sids[pidx]
    # A profile is only a reconnect hint for its original empty slot.  If the
    # slot is already occupied by an online sid, this is stale finished-match
    # metadata and must not steal reconnect from a current match.
    return current_sid == profile_sid or current_sid not in players


def _room_sort_ts(room):
    for attr in ('started_at', 'created_at'):
        try:
            value = float(getattr(room, attr, 0) or 0)
            if value > 0:
                return value
        except Exception:
            pass
    try:
        return float(getattr(room, 'room_id', 0) or 0)
    except Exception:
        return 0.0


def find_reconnect_candidate_locked(nickname='', user_id=None, account_player_id='', beta_mode=False,
                                    desired_room_id=None, desired_match_key=''):
    name_key = normalize_username_key(nickname or '')
    account_player_id = str(account_player_id or '')
    desired_match_key = str(desired_match_key or '').strip()
    try:
        desired_room_id = int(desired_room_id) if desired_room_id not in (None, '') else None
    except (TypeError, ValueError):
        desired_room_id = None
    candidates = []
    for room in rooms.values():
        if not _room_can_offer_reconnect(room, beta_mode):
            continue
        if desired_room_id is not None and int(getattr(room, 'room_id', -1)) != desired_room_id:
            continue
        valid_match_keys = {
            room_match_key(room),
            f'room:{getattr(room, "room_id", "")}',
        }
        if desired_match_key and desired_match_key not in valid_match_keys:
            continue
        room_ts = _room_sort_ts(room)
        for dc_sid, dc_info in list(getattr(room, 'disconnected_players', {}).items()):
            same_identity = (
                (user_id and dc_info.get('user_id') == user_id)
                or (account_player_id and str(dc_info.get('account_player_id') or '') == account_player_id)
                or (name_key and normalize_username_key(dc_info.get('nickname', '')) == name_key)
            )
            if not same_identity:
                continue
            try:
                disconnect_ts = float(dc_info.get('disconnect_time') or 0)
            except Exception:
                disconnect_ts = 0.0
            candidates.append((2, disconnect_ts, room_ts, getattr(room, 'room_id', 0), room, dc_sid))
        for profile_sid, profile in list(getattr(room, 'player_profiles', {}).items()):
            if not _profile_slot_is_reconnectable(room, profile_sid, profile):
                continue
            same_identity = (
                (user_id and profile.get('user_id') == user_id)
                or (account_player_id and str(profile.get('account_player_id') or '') == account_player_id)
                or (name_key and normalize_username_key(profile.get('nickname', '')) == name_key)
            )
            if not same_identity:
                continue
            try:
                disconnect_ts = float(profile.get('disconnect_time') or 0)
            except Exception:
                disconnect_ts = 0.0
            candidates.append((1, disconnect_ts, room_ts, getattr(room, 'room_id', 0), room, profile_sid))
    if not candidates:
        return None, None
    candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3]), reverse=True)
    return candidates[0][4], candidates[0][5]


def _same_login_identity(player, name_key='', user_id=None, account_player_id='', beta_mode=False):
    if not player or bool(player.get('beta_mode', False)) != bool(beta_mode):
        return False
    if user_id and player.get('user_id') == user_id:
        return True
    account_player_id = str(account_player_id or '')
    if account_player_id and str(player.get('account_player_id') or '') == account_player_id:
        return True
    return bool(name_key and normalize_username_key(player.get('nickname', '')) == name_key)


def _can_take_over_online_session(player, name_key='', user_id=None, account_player_id='', beta_mode=False, client_ip=''):
    if not _same_login_identity(player, name_key, user_id, account_player_id, beta_mode):
        return False
    if user_id or account_player_id:
        return True
    # Guests have no stable account identity.  Only allow replacing a same-IP
    # stale session, which covers network hiccups without letting another user
    # steal an active guest nickname immediately.
    if client_ip and player.get('ip') == client_ip:
        if player.get('status') in {'in_game', 'reconnecting', 'spectating', 'solo', 'tutorial'}:
            return True
        last_seen = float(player.get('last_lobby_activity_at') or player.get('login_at') or 0)
        return time.time() - last_seen >= 15
    return False


def _take_over_online_session_locked(old_sid, reason='login_reconnect'):
    """Remove a stale online sid while preserving room reconnect metadata."""
    if old_sid not in players:
        return None
    player = players[old_sid]
    mark_player_session_last_seen_locked(player, exclude_sid=old_sid)
    room_id = player.get('room_id')
    spectating_room = player.get('spectating_room')
    takeover_info = {
        'sid': old_sid,
        'nickname': player.get('nickname', ''),
        'user_id': player.get('user_id'),
        'account_player_id': player.get('account_player_id') or '',
        'had_room': False,
        'prepared_reconnect': False,
    }
    if room_id is not None and room_id in rooms:
        room = rooms[room_id]
        pidx = room.player_index(old_sid)
        if pidx >= 0 and getattr(room.engine, 'phase', '') != 'game_over':
            takeover_info['had_room'] = True
            profile = room.store_player_profile(old_sid, pidx, player)
            profile['disconnect_time'] = time.time()
            room.disconnected_players[old_sid] = dict(profile)
            takeover_info['prepared_reconnect'] = True
            admin_event('player', f'{reason}: prepared stale session for reconnect room={room_id}', sid=old_sid, room_id=room_id)
        elif pidx < 0:
            player['room_id'] = None
    if spectating_room is not None and spectating_room in rooms:
        room = rooms[spectating_room]
        if old_sid in room.spectators:
            room.spectators.remove(old_sid)
    solo_sessions.pop(old_sid, None)
    tutorial_sessions.discard(old_sid)
    for inv_sid, target_sid in list(invites.items()):
        if inv_sid == old_sid or target_sid == old_sid:
            del invites[inv_sid]
    if old_sid in teams:
        team = teams[old_sid]
        for member_sid in list(team.get('members', [])):
            if member_sid in teams:
                del teams[member_sid]
    del players[old_sid]
    return takeover_info


def reject_new_match_if_draining(sids=None, event_name='match_start'):
    if not is_instance_draining():
        return False
    payload = drain_reject_payload()
    payload['message'] = payload['reason']
    for psid in set(sids or []):
        if psid:
            socketio.emit('match_start_failed', payload, room=psid)
            socketio.emit('server_error', {'message': payload['reason'], 'draining': True}, room=psid)
    admin_event('deploy', f'drain rejected {event_name}', sids=list(set(sids or [])))
    return True


def get_lobby_list(beta_mode=None):
    lobby = []
    for sid, p in players.items():
        if beta_mode is not None and bool(p.get('beta_mode')) != bool(beta_mode):
            continue
        if p['status'] == 'lobby':
            lobby.append(public_player_info(sid, p))
    lobby.sort(key=lambda item: (item.get('special_role_sort', 99), item.get('nickname', '').lower()))
    return lobby


def get_ongoing_games(beta_mode=None):
    games = []
    spectatable_phases = {'action', 'draw', 'playing', 'response', 'choice'}
    for rid, room in rooms.items():
        if beta_mode is not None and bool(getattr(room, 'beta_mode', False)) != bool(beta_mode):
            continue
        phase = room.engine.phase
        if phase in ('action', 'draw', 'response', 'choice', 'playing', 'draft', 'event_select', 'event_reveal'):
            player_names = []
            for s in room.player_sids:
                name = room_player_nickname(room, s, '?')
                if name == '?':
                    admin_event('error', f'room {rid} missing player metadata for sid={s}', room_id=rid)
                player_names.append(name)
            both_disconnected = _room_all_blocking_players_disconnected(room)
            game_info = {
                'room_id': rid,
                'player1': player_names[0] if len(player_names) > 0 else '?',
                'player2': player_names[1] if len(player_names) > 1 else '?',
                'round': room.engine.round_num,
                'phase': phase,
                'both_disconnected': both_disconnected,
                'mode': room.mode,
                'beta_mode': bool(getattr(room, 'beta_mode', False)),
                'can_spectate': phase in spectatable_phases,
            }
            if room.mode == '2v2':
                game_info['player3'] = player_names[2] if len(player_names) > 2 else '?'
                game_info['player4'] = player_names[3] if len(player_names) > 3 else '?'
            games.append(game_info)
    return games


def build_admin_players(beta_mode=None):
    if beta_mode is None:
        beta_mode = is_beta_instance()
    result = []
    for sid, p in players.items():
        if bool(p.get('beta_mode', False)) != bool(beta_mode):
            continue
        result.append({
            'sid': sid,
            'nickname': p.get('nickname', '?'),
            'user_id': p.get('user_id'),
            'player_id': p.get('account_player_id') or '',
            'status': p.get('status', ''),
            'room_id': p.get('room_id'),
            'spectating_room': p.get('spectating_room'),
            'mode': p.get('mode', '1v1'),
            'beta_mode': bool(p.get('beta_mode')),
            'mods': p.get('mods_list', []),
        })
    return result


def build_admin_rooms(beta_mode=None):
    if beta_mode is None:
        beta_mode = is_beta_instance()
    result = []
    for rid, room in rooms.items():
        if bool(getattr(room, 'beta_mode', False)) != bool(beta_mode):
            continue
        e = room.engine
        names = []
        disconnected = []
        for psid in room.player_sids:
            names.append(room_player_nickname(room, psid, '?'))
            disconnected.append(psid not in players)
        result.append({
            'room_id': rid,
            'mode': room.mode,
            'beta_mode': bool(getattr(room, 'beta_mode', False)),
            'players': names,
            'player_sids': list(room.player_sids),
            'disconnected': disconnected,
            'phase': getattr(e, 'phase', ''),
            'round': getattr(e, 'round_num', 0),
            'current_player': getattr(e, 'current_player', None),
            'game_over': bool(getattr(e, 'game_over', False)),
            'winner': getattr(e, 'winner', None),
            'winning_team': getattr(e, 'winning_team', None),
            'spectators': len(room.spectators),
            'log_total': len(getattr(e, 'log', [])),
        })
    return result


def _file_size(path):
    try:
        return os.path.getsize(path) if path and os.path.exists(path) else 0
    except OSError:
        return 0


def _dir_size(path, max_files=None):
    max_files = _RESOURCE_BREAKDOWN_MAX_FILES if max_files is None else max_files
    total = 0
    files = 0
    if not path or not os.path.exists(path):
        return {'path': path, 'bytes': 0, 'files': 0, 'truncated': False}
    for root, dirs, filenames in os.walk(path):
        dirs[:] = [
            d for d in dirs
            if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.pytest_cache', '.mypy_cache'}
        ]
        for filename in filenames:
            try:
                total += os.path.getsize(os.path.join(root, filename))
            except OSError:
                pass
            files += 1
            if files >= max_files:
                return {'path': path, 'bytes': total, 'files': files, 'truncated': True}
    return {'path': path, 'bytes': total, 'files': files, 'truncated': False}


def _db_storage_usage():
    db_path = DB_PATH
    files = [
        {'name': 'sqlite', 'path': db_path, 'bytes': _file_size(db_path)},
        {'name': 'wal', 'path': f'{db_path}-wal', 'bytes': _file_size(f'{db_path}-wal')},
        {'name': 'shm', 'path': f'{db_path}-shm', 'bytes': _file_size(f'{db_path}-shm')},
    ]
    return {
        'path': db_path,
        'bytes': sum(item['bytes'] for item in files),
        'files': files,
    }


def _resource_breakdown():
    now = time.time()
    cached = _RESOURCE_BREAKDOWN_CACHE.get('data')
    if cached is not None and now - float(_RESOURCE_BREAKDOWN_CACHE.get('ts') or 0) < _RESOURCE_BREAKDOWN_CACHE_SECONDS:
        return cached
    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(base_dir, 'static')
    mods_dir = os.path.join(base_dir, 'mods')
    templates_dir = os.path.join(base_dir, 'templates')
    logs_dir = os.path.join(base_dir, 'logs')
    data = {
        'base_dir': base_dir,
        'database': _db_storage_usage(),
        'directories': [
            {'label': '项目代码目录', **_dir_size(base_dir)},
            {'label': '静态资源 static', **_dir_size(static_dir)},
            {'label': '官方模组 mods', **_dir_size(mods_dir)},
            {'label': '页面模板 templates', **_dir_size(templates_dir)},
            {'label': '日志目录 logs', **_dir_size(logs_dir)},
        ],
    }
    _RESOURCE_BREAKDOWN_CACHE['ts'] = now
    _RESOURCE_BREAKDOWN_CACHE['data'] = data
    return data


def _avg(values):
    values = [float(v) for v in values if v is not None]
    return round(sum(values) / len(values), 2) if values else None


def _p95(values):
    values = sorted(float(v) for v in values if v is not None)
    if not values:
        return None
    index = min(len(values) - 1, int(len(values) * 0.95))
    return round(values[index], 2)


def _record_resource_sample(metrics):
    global _RESOURCE_HISTORY_LAST_TS
    now = time.time()
    if now - _RESOURCE_HISTORY_LAST_TS < 5:
        return
    _RESOURCE_HISTORY_LAST_TS = now
    system = metrics.get('system', {})
    process = metrics.get('process', {})
    disk = metrics.get('disk', {})
    RESOURCE_HISTORY.append({
        'ts': now,
        'time': iso_now(),
        'cpu': system.get('cpu_percent'),
        'process_cpu': process.get('cpu_percent'),
        'memory': system.get('memory_percent'),
        'process_memory': process.get('memory_rss'),
        'disk': disk.get('percent'),
        'online': len(players),
        'rooms': len(rooms),
    })


def _resource_history_payload():
    now = time.time()
    windows = {}
    for minutes in (5, 15, 60):
        cutoff = now - minutes * 60
        windows[f'{minutes}m'] = [item for item in RESOURCE_HISTORY if item.get('ts', 0) >= cutoff]
    return {
        'sample_interval_seconds': 5,
        'windows': windows,
    }


def record_socket_latency(sid, rtt_ms, transport=''):
    try:
        value = float(rtt_ms)
    except (TypeError, ValueError):
        return
    if value < 0 or value > 60000:
        return
    SOCKET_LATENCY_SAMPLES.append({
        'ts': time.time(),
        'sid': str(sid or ''),
        'nickname': players.get(sid, {}).get('nickname', '') if sid in players else '',
        'rtt_ms': round(value, 2),
        'transport': str(transport or '')[:24],
    })


def record_socket_action(event_name, duration_ms, sid='', room_id=None, ok=True):
    try:
        value = float(duration_ms)
    except (TypeError, ValueError):
        return
    SOCKET_ACTION_SAMPLES.append({
        'ts': time.time(),
        'event': str(event_name or '')[:40],
        'duration_ms': round(value, 2),
        'sid': str(sid or ''),
        'room_id': room_id,
        'ok': bool(ok),
    })


def record_socket_broadcast(room, duration_ms, recipients=0):
    try:
        value = float(duration_ms)
    except (TypeError, ValueError):
        return
    SOCKET_BROADCAST_SAMPLES.append({
        'ts': time.time(),
        'room_id': getattr(room, 'room_id', None),
        'mode': getattr(room, 'mode', ''),
        'duration_ms': round(value, 2),
        'recipients': int(recipients or 0),
    })


def enqueue_card_draft_pick(mode, option_ids, picked_id):
    global _DRAFT_STATS_PENDING_EVENTS
    if not DB_AVAILABLE:
        return False
    mode_key = str(mode or '').strip()
    if mode_key not in ('1v1', '2v2'):
        return False
    picked = str(picked_id or '').strip()
    if not picked:
        return False
    counts = {}
    for raw_id in option_ids or []:
        card_id = str(raw_id or '').strip()
        if not card_id:
            continue
        counts[card_id] = counts.get(card_id, 0) + 1
    if not counts:
        return False
    with _DRAFT_STATS_LOCK:
        bucket = _DRAFT_STATS_PENDING.setdefault(mode_key, {})
        for card_id, shown_inc in counts.items():
            current = bucket.setdefault(card_id, [0, 0])
            current[0] += int(shown_inc)
            if card_id == picked:
                current[1] += 1
        _DRAFT_STATS_PENDING_EVENTS += 1
    start_draft_stats_worker()
    if _DRAFT_STATS_PENDING_EVENTS >= DRAFT_STATS_FLUSH_MAX_PENDING:
        flush_draft_stats_async()
    return True


def enqueue_opening_event_pick(mode, option_ids, picked_id):
    global _DRAFT_STATS_PENDING_EVENTS
    if not DB_AVAILABLE:
        return False
    mode_key = str(mode or '').strip()
    if mode_key not in ('1v1', '2v2'):
        return False
    picked = str(picked_id or '').strip()
    if not picked:
        return False
    counts = {}
    for raw_id in option_ids or []:
        event_id = str(raw_id or '').strip()
        if not event_id:
            continue
        counts[event_id] = counts.get(event_id, 0) + 1
    if not counts:
        return False
    with _DRAFT_STATS_LOCK:
        bucket = _OPENING_EVENT_STATS_PENDING.setdefault(mode_key, {})
        for event_id, shown_inc in counts.items():
            current = bucket.setdefault(event_id, [0, 0])
            current[0] += int(shown_inc)
            if event_id == picked:
                current[1] += 1
        _DRAFT_STATS_PENDING_EVENTS += 1
    start_draft_stats_worker()
    if _DRAFT_STATS_PENDING_EVENTS >= DRAFT_STATS_FLUSH_MAX_PENDING:
        flush_draft_stats_async()
    return True


def _drain_draft_stats_pending():
    global _DRAFT_STATS_PENDING_EVENTS
    with _DRAFT_STATS_LOCK:
        pending = {mode: {card_id: list(counts) for card_id, counts in cards.items()} for mode, cards in _DRAFT_STATS_PENDING.items()}
        event_pending = {mode: {event_id: list(counts) for event_id, counts in events.items()} for mode, events in _OPENING_EVENT_STATS_PENDING.items()}
        _DRAFT_STATS_PENDING.clear()
        _OPENING_EVENT_STATS_PENDING.clear()
        _DRAFT_STATS_PENDING_EVENTS = 0
    return pending, event_pending


def flush_draft_stats_once():
    pending, event_pending = _drain_draft_stats_pending()
    if not pending and not event_pending:
        return 0
    written = 0
    for mode, card_counts in pending.items():
        try:
            if record_card_draft_counts(mode, card_counts):
                written += len(card_counts)
        except Exception as exc:
            admin_event('error', f'draft stats flush failed: {exc}')
            with _DRAFT_STATS_LOCK:
                bucket = _DRAFT_STATS_PENDING.setdefault(mode, {})
                for card_id, counts in card_counts.items():
                    current = bucket.setdefault(card_id, [0, 0])
                    current[0] += int((counts or [0, 0])[0] or 0)
                    current[1] += int((counts or [0, 0])[1] or 0)
    for mode, event_counts in event_pending.items():
        try:
            if record_opening_event_pick_counts(mode, event_counts):
                written += len(event_counts)
        except Exception as exc:
            admin_event('error', f'opening event stats flush failed: {exc}')
            with _DRAFT_STATS_LOCK:
                bucket = _OPENING_EVENT_STATS_PENDING.setdefault(mode, {})
                for event_id, counts in event_counts.items():
                    current = bucket.setdefault(event_id, [0, 0])
                    current[0] += int((counts or [0, 0])[0] or 0)
                    current[1] += int((counts or [0, 0])[1] or 0)
    return written


def flush_draft_stats_async():
    try:
        socketio.start_background_task(flush_draft_stats_once)
    except Exception:
        threading.Thread(target=flush_draft_stats_once, name='draft-stats-flush', daemon=True).start()


def _draft_stats_worker():
    while True:
        try:
            try:
                socketio.sleep(max(1, DRAFT_STATS_FLUSH_SECONDS))
            except Exception:
                time.sleep(max(1, DRAFT_STATS_FLUSH_SECONDS))
            flush_draft_stats_once()
        except Exception as exc:
            admin_event('error', f'draft stats worker error: {exc}')


def start_draft_stats_worker():
    global _DRAFT_STATS_WORKER_STARTED
    if _DRAFT_STATS_WORKER_STARTED:
        return
    _DRAFT_STATS_WORKER_STARTED = True
    try:
        socketio.start_background_task(_draft_stats_worker)
    except Exception:
        threading.Thread(target=_draft_stats_worker, name='draft-stats-worker', daemon=True).start()


def enqueue_user_last_seen(user_id):
    if not DB_AVAILABLE:
        return False
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return False
    with _LAST_SEEN_LOCK:
        _LAST_SEEN_PENDING.add(uid)
        pending_count = len(_LAST_SEEN_PENDING)
    start_last_seen_worker()
    if pending_count >= LAST_SEEN_FLUSH_MAX_PENDING:
        flush_last_seen_async()
    return True


def _drain_last_seen_pending():
    with _LAST_SEEN_LOCK:
        pending = set(_LAST_SEEN_PENDING)
        _LAST_SEEN_PENDING.clear()
    return pending


def flush_last_seen_once():
    pending = _drain_last_seen_pending()
    if not pending:
        return 0
    failed = set()
    for uid in pending:
        try:
            if _user_has_active_player_session(uid):
                continue
            mark_user_last_seen(uid)
        except Exception as exc:
            failed.add(uid)
            admin_event('error', f'last seen flush failed user={uid}: {exc}')
    if failed:
        with _LAST_SEEN_LOCK:
            _LAST_SEEN_PENDING.update(failed)
    return len(pending) - len(failed)


def flush_last_seen_async():
    try:
        socketio.start_background_task(flush_last_seen_once)
    except Exception:
        threading.Thread(target=flush_last_seen_once, name='last-seen-flush', daemon=True).start()


def _last_seen_worker():
    while True:
        try:
            try:
                socketio.sleep(max(1, LAST_SEEN_FLUSH_SECONDS))
            except Exception:
                time.sleep(max(1, LAST_SEEN_FLUSH_SECONDS))
            flush_last_seen_once()
        except Exception as exc:
            admin_event('error', f'last seen worker error: {exc}')


def start_last_seen_worker():
    global _LAST_SEEN_WORKER_STARTED
    if _LAST_SEEN_WORKER_STARTED:
        return
    _LAST_SEEN_WORKER_STARTED = True
    try:
        socketio.start_background_task(_last_seen_worker)
    except Exception:
        threading.Thread(target=_last_seen_worker, name='last-seen-worker', daemon=True).start()


def record_event_loop_lag(lag_ms):
    try:
        value = float(lag_ms)
    except (TypeError, ValueError):
        return
    if value < 0 or value > 10 * 60 * 1000:
        return
    EVENT_LOOP_LAG_SAMPLES.append({
        'ts': time.time(),
        'lag_ms': round(value, 2),
    })


def _event_loop_watchdog_worker():
    interval = _env_float('GTN_EVENT_LOOP_WATCHDOG_INTERVAL', 1.0)
    warn_ms = _env_float('GTN_EVENT_LOOP_LAG_WARN_MS', 3000)
    last_warn = 0.0
    expected = time.monotonic() + interval
    while True:
        try:
            try:
                socketio.sleep(interval)
            except Exception:
                time.sleep(interval)
            now = time.monotonic()
            lag_ms = max(0.0, (now - expected) * 1000.0)
            record_event_loop_lag(lag_ms)
            if lag_ms >= warn_ms and time.time() - last_warn >= 30:
                last_warn = time.time()
                admin_event('suspicious', f'event loop lag {lag_ms:.0f}ms; Socket.IO may disconnect clients')
            expected = now + interval
        except Exception as exc:
            admin_event('error', f'event loop watchdog error: {exc}')
            expected = time.monotonic() + interval


def ensure_event_loop_watchdog_started():
    global _event_loop_watchdog_started
    if _event_loop_watchdog_started:
        return
    _event_loop_watchdog_started = True
    try:
        socketio.start_background_task(_event_loop_watchdog_worker)
    except Exception:
        threading.Thread(target=_event_loop_watchdog_worker, name='event-loop-watchdog', daemon=True).start()


def _recent_samples(samples, seconds=300):
    cutoff = time.time() - seconds
    return [item for item in samples if item.get('ts', 0) >= cutoff]


def socket_metrics_payload():
    latency = _recent_samples(SOCKET_LATENCY_SAMPLES, 300)
    actions = _recent_samples(SOCKET_ACTION_SAMPLES, 300)
    broadcasts = _recent_samples(SOCKET_BROADCAST_SAMPLES, 300)
    loop_lag = _recent_samples(EVENT_LOOP_LAG_SAMPLES, 300)
    action_by_name = {}
    for item in actions:
        bucket = action_by_name.setdefault(item.get('event') or '?', [])
        bucket.append(item.get('duration_ms'))
    return {
        'latency': {
            'count': len(latency),
            'avg_ms': _avg(item.get('rtt_ms') for item in latency),
            'p95_ms': _p95(item.get('rtt_ms') for item in latency),
            'latest_ms': latency[-1].get('rtt_ms') if latency else None,
            'latest_transport': latency[-1].get('transport') if latency else '',
        },
        'actions': {
            'count': len(actions),
            'avg_ms': _avg(item.get('duration_ms') for item in actions),
            'p95_ms': _p95(item.get('duration_ms') for item in actions),
            'slowest': sorted(actions, key=lambda item: item.get('duration_ms') or 0, reverse=True)[:5],
            'by_event': {
                name: {
                    'count': len(values),
                    'avg_ms': _avg(values),
                    'p95_ms': _p95(values),
                }
                for name, values in sorted(action_by_name.items())
            },
        },
        'broadcasts': {
            'count': len(broadcasts),
            'avg_ms': _avg(item.get('duration_ms') for item in broadcasts),
            'p95_ms': _p95(item.get('duration_ms') for item in broadcasts),
            'latest_ms': broadcasts[-1].get('duration_ms') if broadcasts else None,
        },
        'event_loop': {
            'lag_count': len(loop_lag),
            'lag_avg_ms': _avg(item.get('lag_ms') for item in loop_lag),
            'lag_p95_ms': _p95(item.get('lag_ms') for item in loop_lag),
            'lag_latest_ms': loop_lag[-1].get('lag_ms') if loop_lag else None,
            'lag_max_ms': max([float(item.get('lag_ms') or 0) for item in loop_lag] or [0]),
        },
    }


def measure_socket_action(event_name):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            sid = getattr(request, 'sid', '')
            watched = event_name in {'login', 'play_card', 'end_turn', 'response', 'resolve_choice'}
            ok = True
            if watched:
                try:
                    print(f'event_start event={event_name} sid={sid}', flush=True)
                except Exception:
                    pass
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                ok = False
                traceback.print_exc()
                room_id = None
                user_id = None
                try:
                    if sid in players:
                        room_id = players[sid].get('room_id')
                        user_id = players[sid].get('user_id')
                except Exception:
                    pass
                try:
                    admin_event(
                        'error',
                        f'socket_event_failed event={event_name} sid={sid} room={room_id} error={type(exc).__name__}: {exc}',
                        user_id=user_id,
                        room_id=room_id,
                    )
                except Exception:
                    traceback.print_exc()
                try:
                    socketio.emit('server_error', {'message': '操作失败，请重试。'}, room=sid)
                except Exception:
                    traceback.print_exc()
                return None
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                room_id = None
                try:
                    if sid in players:
                        room_id = players[sid].get('room_id')
                except Exception:
                    room_id = None
                try:
                    record_socket_action(event_name, elapsed_ms, sid=sid, room_id=room_id, ok=ok)
                except Exception:
                    traceback.print_exc()
                try:
                    if watched:
                        print(f'event_done event={event_name} sid={sid} room={room_id} ok={ok} elapsed_ms={elapsed_ms:.1f}', flush=True)
                    if elapsed_ms >= _SOCKET_ACTION_SLOW_MS:
                        admin_event('perf', f'socket_event event={event_name} elapsed_ms={elapsed_ms:.1f} sid={sid} room={room_id} ok={ok}')
                        print(f'socket_event event={event_name} elapsed_ms={elapsed_ms:.1f} sid={sid} room={room_id} ok={ok}', flush=True)
                except Exception:
                    traceback.print_exc()
        return wrapper
    return decorator


def _collect_runtime_metrics():
    uptime = max(0, int(time.time() - SERVER_STARTED_AT))
    metrics_errors = []
    try:
        root_usage = shutil.disk_usage('/')
        disk_payload = {
            'path': '/',
            'total': root_usage.total,
            'used': root_usage.used,
            'free': root_usage.free,
            'percent': round(root_usage.used / root_usage.total * 100, 1) if root_usage.total else None,
            'ephemeral': False,
        }
    except Exception as exc:
        metrics_errors.append(f'disk_usage: {exc}')
        disk_payload = {
            'path': '/',
            'total': None,
            'used': None,
            'free': None,
            'percent': None,
            'ephemeral': False,
            'error': str(exc),
        }
    loadavg = None
    if hasattr(os, 'getloadavg'):
        try:
            loadavg = list(os.getloadavg())
        except OSError:
            loadavg = None
    try:
        storage_breakdown = _resource_breakdown()
    except Exception as exc:
        metrics_errors.append(f'resource_breakdown: {exc}')
        storage_breakdown = {
            'base_dir': os.path.dirname(os.path.abspath(__file__)),
            'database': {'bytes': 0, 'files': []},
            'directories': [],
            'error': str(exc),
        }
    metrics = {
        'time': iso_now(),
        'uptime_seconds': uptime,
        'server_profile': {
            'instance': GTN_INSTANCE,
            'instance_id': GTN_INSTANCE_ID,
            'version': GTN_VERSION,
            'git_sha': GTN_GIT_SHA,
            'static_version': GTN_STATIC_VERSION,
            'draining': is_instance_draining(),
            'drain_file': GTN_DRAIN_FILE,
            'port': GTN_PORT,
            'bind_host': GTN_BIND_HOST,
            'git_branch': os.environ.get('GTN_GIT_BRANCH', 'main').strip() or 'main',
            'service_name': os.environ.get('GTN_SYSTEMD_SERVICE', '').strip(),
            'base_dir': os.path.dirname(os.path.abspath(__file__)),
            'release_url': GTN_RELEASE_PUBLIC_URL,
            'beta_url': GTN_BETA_PUBLIC_URL,
            'provider': os.environ.get('GTN_SERVER_PROVIDER', 'Aliyun'),
            'os': platform.platform(),
            'python': platform.python_version(),
            'machine': platform.machine(),
            'cpu_target': os.environ.get('GTN_SERVER_CPU', '2 Core'),
            'memory_target': os.environ.get('GTN_SERVER_MEMORY', '2G'),
            'disk_target': os.environ.get('GTN_SERVER_DISK', '40G'),
        },
        'disk': disk_payload,
        'loadavg': loadavg,
        'process': {
            'pid': os.getpid(),
            'cpu_percent': None,
            'memory_rss': None,
            'memory_vms': None,
            'threads': None,
            'fds': None,
        },
        'system': {
            'cpu_percent': None,
            'cpu_count': os.cpu_count(),
            'cpu_count_physical': None,
            'memory_total': None,
            'memory_used': None,
            'memory_available': None,
            'memory_percent': None,
            'swap_total': None,
            'swap_used': None,
            'swap_percent': None,
        },
        'network': {
            'bytes_sent': None,
            'bytes_recv': None,
        },
        'storage_breakdown': storage_breakdown,
        'psutil_available': psutil is not None,
    }
    if psutil is not None and _PSUTIL_PROCESS is not None:
        try:
            mem = _PSUTIL_PROCESS.memory_info()
            vm = psutil.virtual_memory()
            swap = psutil.swap_memory()
            try:
                fds = _PSUTIL_PROCESS.num_fds()
            except Exception:
                fds = None
            try:
                net = psutil.net_io_counters()
            except Exception:
                net = None
            metrics['process'].update({
                'cpu_percent': _PSUTIL_PROCESS.cpu_percent(interval=None),
                'memory_rss': mem.rss,
                'memory_vms': getattr(mem, 'vms', None),
                'threads': _PSUTIL_PROCESS.num_threads(),
                'fds': fds,
            })
            metrics['system'].update({
                'cpu_percent': psutil.cpu_percent(interval=None),
                'cpu_count': psutil.cpu_count(logical=True),
                'cpu_count_physical': psutil.cpu_count(logical=False),
                'memory_total': vm.total,
                'memory_used': vm.used,
                'memory_available': vm.available,
                'memory_percent': vm.percent,
                'swap_total': swap.total,
                'swap_used': swap.used,
                'swap_percent': swap.percent,
            })
            if net is not None:
                metrics['network'].update({
                    'bytes_sent': net.bytes_sent,
                    'bytes_recv': net.bytes_recv,
                })
        except Exception as exc:
            metrics_errors.append(f'psutil: {exc}')
    _record_resource_sample(metrics)
    metrics['resource_history'] = _resource_history_payload()
    metrics['socket'] = socket_metrics_payload()
    try:
        metrics['r2'] = get_r2_health_snapshot()
    except Exception as exc:
        metrics_errors.append(f'r2_health: {exc}')
        metrics['r2'] = {'last_error': str(exc)}
    if metrics_errors:
        metrics['metrics_error'] = '; '.join(metrics_errors)
    return metrics


def get_runtime_metrics():
    now = time.time()
    cached = _RUNTIME_METRICS_CACHE.get('data')
    cache_ts = float(_RUNTIME_METRICS_CACHE.get('ts') or 0)
    if cached is not None and now - cache_ts < _RUNTIME_METRICS_CACHE_SECONDS:
        payload = copy.deepcopy(cached)
        payload['cached'] = True
        return payload
    acquired = _RUNTIME_METRICS_LOCK.acquire(blocking=False)
    if not acquired:
        if cached is not None:
            payload = copy.deepcopy(cached)
            payload['cached'] = True
            payload['stale'] = True
            return payload
        _RUNTIME_METRICS_LOCK.acquire()
        acquired = True
    try:
        now = time.time()
        cached = _RUNTIME_METRICS_CACHE.get('data')
        cache_ts = float(_RUNTIME_METRICS_CACHE.get('ts') or 0)
        if cached is not None and now - cache_ts < _RUNTIME_METRICS_CACHE_SECONDS:
            payload = copy.deepcopy(cached)
            payload['cached'] = True
            return payload
        metrics = _collect_runtime_metrics()
        _RUNTIME_METRICS_CACHE['ts'] = now
        _RUNTIME_METRICS_CACHE['data'] = copy.deepcopy(metrics)
        return metrics
    finally:
        if acquired:
            _RUNTIME_METRICS_LOCK.release()


def get_admin_status_payload():
    status_errors = []
    try:
        metrics = get_runtime_metrics()
    except Exception as exc:
        status_errors.append(f'metrics: {exc}')
        metrics = {
            'time': now_iso_z(),
            'uptime_seconds': int(time.time() - SERVER_START_TIME),
            'process': {},
            'system': {},
            'disk': {},
            'metrics_error': str(exc),
        }
    with _lock:
        try:
            player_list = build_admin_players()
        except Exception as exc:
            status_errors.append(f'players: {exc}')
            player_list = []
        try:
            room_list = build_admin_rooms()
        except Exception as exc:
            status_errors.append(f'rooms: {exc}')
            room_list = []
        try:
            spectator_count = sum(1 for p in players.values() if p.get('status') == 'spectating')
        except Exception as exc:
            status_errors.append(f'spectators: {exc}')
            spectator_count = 0
        try:
            events = list(ADMIN_EVENTS)[:120]
        except Exception as exc:
            status_errors.append(f'events: {exc}')
            events = []
        try:
            suspicious = recent_suspicious_events(120)
        except Exception as exc:
            status_errors.append(f'suspicious: {exc}')
            suspicious = []
        try:
            history = list(MATCH_HISTORY)[:80]
        except Exception as exc:
            status_errors.append(f'history: {exc}')
            history = []
    if status_errors:
        metrics['status_errors'] = status_errors
    return {
        'success': True,
        'instance': {
            'name': GTN_INSTANCE,
            'id': GTN_INSTANCE_ID,
            'version': GTN_VERSION,
            'git_sha': GTN_GIT_SHA,
            'port': GTN_PORT,
            'bind_host': GTN_BIND_HOST,
            'draining': is_instance_draining(),
            'drain_file': GTN_DRAIN_FILE,
            'git_branch': os.environ.get('GTN_GIT_BRANCH', 'main').strip() or 'main',
            'service_name': os.environ.get('GTN_SYSTEMD_SERVICE', '').strip(),
            'base_dir': os.path.dirname(os.path.abspath(__file__)),
        },
        'metrics': metrics,
        'summary': {
            'online_players': len(player_list),
            'lobby_players': sum(1 for p in player_list if p.get('status') == 'lobby'),
            'rooms': len(room_list),
            'spectators': spectator_count,
            'history_count': len(history),
        },
        'players': player_list,
        'rooms': room_list,
        'events': events,
        'suspicious_events': suspicious,
        'history': history,
    }


def get_admin_status_payload_light():
    status_errors = []
    try:
        metrics = get_runtime_metrics()
    except Exception as exc:
        status_errors.append(f'metrics: {exc}')
        metrics = {
            'time': now_iso_z(),
            'uptime_seconds': int(time.time() - SERVER_START_TIME),
            'process': {},
            'system': {},
            'disk': {},
            'metrics_error': str(exc),
        }
    with _lock:
        try:
            online_players = len(players)
            lobby_players = sum(1 for p in players.values() if p.get('status') == 'lobby')
            spectator_count = sum(1 for p in players.values() if p.get('status') == 'spectating')
            room_count = len(rooms)
        except Exception as exc:
            status_errors.append(f'summary: {exc}')
            online_players = lobby_players = spectator_count = room_count = 0
        try:
            history_count = len(MATCH_HISTORY)
        except Exception:
            history_count = 0
    if status_errors:
        metrics['status_errors'] = status_errors
    return {
        'success': True,
        'light': True,
        'instance': {
            'name': GTN_INSTANCE,
            'id': GTN_INSTANCE_ID,
            'version': GTN_VERSION,
            'git_sha': GTN_GIT_SHA,
            'port': GTN_PORT,
            'bind_host': GTN_BIND_HOST,
            'draining': is_instance_draining(),
            'drain_file': GTN_DRAIN_FILE,
            'git_branch': os.environ.get('GTN_GIT_BRANCH', 'main').strip() or 'main',
            'service_name': os.environ.get('GTN_SYSTEMD_SERVICE', '').strip(),
            'base_dir': os.path.dirname(os.path.abspath(__file__)),
        },
        'metrics': metrics,
        'summary': {
            'online_players': online_players,
            'lobby_players': lobby_players,
            'rooms': room_count,
            'spectators': spectator_count,
            'history_count': history_count,
        },
    }


def room_rematch_payload(room, sid=None):
    returned_sids = set(getattr(room, '_returned_lobby_sids', set()) or set())
    returned_names = dict(getattr(room, '_returned_lobby_names', {}) or {})
    first_returned_name = ''
    if returned_sids:
        first_sid = next(iter(returned_sids))
        first_returned_name = returned_names.get(first_sid, '')
    return {
        'rematch_votes': len(getattr(room, '_rematch_votes', set()) or set()),
        'rematch_total': len(getattr(room, 'player_sids', []) or []),
        'rematch_has_voted': bool(sid is not None and sid in (getattr(room, '_rematch_votes', set()) or set())),
        'rematch_blocked': bool(returned_sids),
        'rematch_blocked_reason': 'player_returned_lobby' if returned_sids else '',
        'rematch_returned_player_name': first_returned_name,
    }


def get_admin_status_payload_cached():
    now = time.time()
    cached = _ADMIN_STATUS_CACHE.get('data')
    cache_ts = float(_ADMIN_STATUS_CACHE.get('ts') or 0)
    if cached is not None and now - cache_ts < _ADMIN_STATUS_CACHE_SECONDS:
        payload = copy.deepcopy(cached)
        payload['cached'] = True
        return payload
    acquired = _ADMIN_STATUS_LOCK.acquire(blocking=False)
    if not acquired:
        if cached is not None:
            payload = copy.deepcopy(cached)
            payload['cached'] = True
            payload['stale'] = True
            return payload
        _ADMIN_STATUS_LOCK.acquire()
        acquired = True
    try:
        now = time.time()
        cached = _ADMIN_STATUS_CACHE.get('data')
        cache_ts = float(_ADMIN_STATUS_CACHE.get('ts') or 0)
        if cached is not None and now - cache_ts < _ADMIN_STATUS_CACHE_SECONDS:
            payload = copy.deepcopy(cached)
            payload['cached'] = True
            return payload
        payload = get_admin_status_payload()
        _ADMIN_STATUS_CACHE['ts'] = now
        _ADMIN_STATUS_CACHE['data'] = copy.deepcopy(payload)
        return payload
    finally:
        if acquired:
            _ADMIN_STATUS_LOCK.release()


ADMIN_COMMAND_TREE = {
    'help': {
        'summary': '显示命令帮助',
        'usage': 'help [一级命令] [二级命令]',
        'children': {},
    },
    'player': {
        'summary': '在线玩家与连接',
        'usage': 'player <list|get|kick|afkcheck> ...',
        'children': {
            'list': {'summary': '列出在线玩家', 'usage': 'player list'},
            'get': {'summary': '查看在线玩家或注册账号详情', 'usage': 'player get <sid|昵称|ID|注册顺序|用户名>'},
            'kick': {'summary': '踢出在线玩家', 'usage': 'player kick <sid|昵称>'},
            'afkcheck': {'summary': '向在线玩家发送挂机检测', 'usage': 'player afkcheck <sid|昵称|all> [confirm] [原因]'},
        },
    },
    'account': {
        'summary': '账号与持久数据',
        'usage': 'account <get|username|password|achievement|dew|rating|role|ban|unban> ...',
        'children': {
            'get': {'summary': '查看注册账号详情', 'usage': 'account get <ID|注册顺序|用户名>'},
            'username': {'summary': '修改账号用户名', 'usage': 'account username <ID|注册顺序|用户名> <新用户名>'},
            'password': {'summary': '修改账号密码并退出所有设备', 'usage': 'account password <ID|注册顺序|用户名> <新密码>'},
            'achievement': {
                'summary': '查看或发放成就',
                'usage': 'account achievement <list|grant> ...',
                'children': {
                    'list': {'summary': '查看账号成就', 'usage': 'account achievement list <账号>'},
                    'grant': {'summary': '向账号发放成就', 'usage': 'account achievement grant <账号> <成就ID>'},
                },
            },
            'dew': {
                'summary': '管理荆露',
                'usage': 'account dew <get|add|addpaid|spend|tx> ...',
                'children': {
                    'get': {'summary': '查看余额', 'usage': 'account dew get <账号>'},
                    'add': {'summary': '增减普通荆露', 'usage': 'account dew add <账号> <数量> [原因]'},
                    'addpaid': {'summary': '增减充值荆露', 'usage': 'account dew addpaid <账号> <数量> [原因]'},
                    'spend': {'summary': '扣除荆露', 'usage': 'account dew spend <账号> <数量> [原因]'},
                    'tx': {'summary': '查看最近流水', 'usage': 'account dew tx <账号>'},
                },
            },
            'rating': {
                'summary': '管理花阶分',
                'usage': 'account rating <info|set|add|snapshot> ...',
                'children': {
                    'info': {'summary': '查看账号花阶分', 'usage': 'account rating info <账号>'},
                    'set': {'summary': '设置花阶分', 'usage': 'account rating set <账号> <season|total|both> <数值> [原因]'},
                    'add': {'summary': '增减花阶分', 'usage': 'account rating add <账号> <season|total|both> <数值> [原因]'},
                    'snapshot': {'summary': '写入今日分数快照', 'usage': 'account rating snapshot <账号>'},
                },
            },
            'role': {
                'summary': '管理账号身份',
                'usage': 'account role <list|get|set|clear> ...',
                'children': {
                    'list': {'summary': '列出特殊身份', 'usage': 'account role list [搜索]'},
                    'get': {'summary': '查看账号身份', 'usage': 'account role get <账号>'},
                    'set': {'summary': '设置账号身份', 'usage': 'account role set <账号> <身份> [选项]'},
                    'clear': {'summary': '清除特殊身份', 'usage': 'account role clear <账号>'},
                },
            },
            'ban': {'summary': '封禁账号并踢下线', 'usage': 'account ban <账号> [时长] [原因]'},
            'unban': {'summary': '解除账号封禁', 'usage': 'account unban <账号>'},
        },
    },
    'game': {
        'summary': '房间、对局及对局内对象',
        'usage': 'game <list|info|log|chat|state|history|action|player|pending> ...',
        'children': {
            'list': {'summary': '列出当前对局', 'usage': 'game list'},
            'info': {'summary': '查看房间摘要', 'usage': 'game info <房间ID>'},
            'log': {'summary': '查看战斗日志', 'usage': 'game log <房间ID> [数量]'},
            'chat': {'summary': '查看对局聊天', 'usage': 'game chat <房间ID> [数量]'},
            'state': {'summary': '查看精简状态', 'usage': 'game state <房间ID>'},
            'history': {'summary': '查看最近历史对局', 'usage': 'game history [数量]'},
            'action': {
                'summary': '管理回合与对局',
                'usage': 'game action <skip|end> ...',
                'children': {
                    'skip': {'summary': '跳过当前回合', 'usage': 'game action skip <房间ID>'},
                    'end': {'summary': '强制结束对局', 'usage': 'game action end <房间ID> <0|1|draw>'},
                },
            },
            'player': {
                'summary': '修改对局内玩家',
                'usage': 'game player <房间ID> <玩家序号> <info|resource|status|card> ...',
                'children': {
                    'resource': {'summary': '设置或增减H/E/M等数值', 'usage': 'game player <房间> <玩家> resource <set|add> <属性> <数值>'},
                    'status': {'summary': '查看、设置或清除状态', 'usage': 'game player <房间> <玩家> status <list|get|set|add|remove|clear> [...]'},
                    'card': {'summary': '查看、加入或删除牌', 'usage': 'game player <房间> <玩家> card <list|add|remove> [...]'},
                },
            },
            'pending': {'summary': '查看待处理操作', 'usage': 'game pending get <房间ID>'},
        },
    },
    'lobby': {
        'summary': '大厅、聊天与广播',
        'usage': 'lobby <chat|broadcast> ...',
        'children': {
            'chat': {'summary': '查看大厅聊天缓存', 'usage': 'lobby chat [数量]'},
            'broadcast': {'summary': '发送服务器广播', 'usage': 'lobby broadcast <内容>'},
        },
    },
    'moderation': {
        'summary': '处罚与安全记录',
        'usage': 'moderation <mute|ban|unban|ip|report|suspicious> ...',
        'children': {
            'mute': {'summary': '禁言在线玩家', 'usage': 'moderation mute <sid|昵称> [时长]'},
            'ban': {'summary': '封禁账号', 'usage': 'moderation ban <账号> [时长] [原因]'},
            'unban': {'summary': '解除账号封禁', 'usage': 'moderation unban <账号>'},
            'ip': {
                'summary': '管理 IP 封禁',
                'usage': 'moderation ip <list|ban|unban> ...',
                'children': {
                    'list': {'summary': '列出 IP 封禁', 'usage': 'moderation ip list [all]'},
                    'ban': {'summary': '封禁 IP', 'usage': 'moderation ip ban <IP> [时长秒] [原因]'},
                    'unban': {'summary': '解除 IP 封禁', 'usage': 'moderation ip unban <IP>'},
                },
            },
            'report': {
                'summary': '查看或处理举报',
                'usage': 'moderation report <list|get|resolve> ...',
                'children': {
                    'list': {'summary': '列出举报', 'usage': 'moderation report list [pending|resolved|dismissed] [数量]'},
                    'get': {'summary': '查看举报详情', 'usage': 'moderation report get <举报ID>'},
                    'resolve': {'summary': '标记举报处理结果', 'usage': 'moderation report resolve <举报ID> <accept|reject|abusive> [备注]'},
                },
            },
            'suspicious': {'summary': '查看可疑安全事件', 'usage': 'moderation suspicious [数量]'},
        },
    },
    'content': {
        'summary': '临时停用卡牌或模组',
        'usage': 'content <disable|enable|disabled> ...',
        'children': {
            'disable': {
                'summary': '停用卡牌或模组（仅影响新对局）',
                'usage': 'content disable <card|mod> <对象> [duration=1h] [mode=all] [reason=原因] [force]',
            },
            'enable': {
                'summary': '恢复卡牌或模组',
                'usage': 'content enable <card|mod> <对象> [mode=all|all-scopes]',
            },
            'disabled': {
                'summary': '查看或修改停用项',
                'usage': 'content disabled <list|show|edit> ...',
                'children': {
                    'list': {'summary': '列出停用项', 'usage': 'content disabled list [card|mod|all] [active|all]'},
                    'show': {'summary': '查看停用详情', 'usage': 'content disabled show <card|mod> <对象>'},
                    'edit': {'summary': '修改原因、期限或范围', 'usage': 'content disabled edit <card|mod> <对象> [from=原范围] [duration=1h] [mode=新范围] [reason=原因]'},
                },
            },
        },
    },
    'replay': {
        'summary': '按回放 ID 查询和保留对局回放',
        'usage': 'replay <get|open|export|hold|release> ...',
        'children': {
            'get': {'summary': '查看回放摘要', 'usage': 'replay get <R-回放ID>'},
            'open': {'summary': '显示回放接口地址', 'usage': 'replay open <R-回放ID>'},
            'export': {'summary': '导出完整回放 JSON 到事故目录', 'usage': 'replay export <R-回放ID>'},
            'hold': {'summary': '延长回放保存期限', 'usage': 'replay hold <R-回放ID> [天数|permanent] [原因]'},
            'release': {'summary': '解除回放保留', 'usage': 'replay release <R-回放ID>'},
        },
    },
    'data': {
        'summary': '统计、回放与数据库维护',
        'usage': 'data <summary|draftstats|rating|rebuildstats|dewbackfill|achievementbackfill> ...',
        'children': {
            'summary': {'summary': '查看数据库、回放和快照占用', 'usage': 'data summary'},
            'draftstats': {'summary': '查看卡牌选取统计', 'usage': 'data draftstats [1v1|2v2]'},
            'rating': {
                'summary': '查看或重建花阶分数据',
                'usage': 'data rating <season|list|rebuild> ...',
                'children': {
                    'season': {'summary': '查看当前赛季', 'usage': 'data rating season'},
                    'list': {'summary': '查看花阶分排行', 'usage': 'data rating list [season|total] [数量]'},
                    'rebuild': {'summary': '从历史对局重建花阶分', 'usage': 'data rating rebuild <preview|confirm>'},
                },
            },
            'rebuildstats': {'summary': '重建账号统计', 'usage': 'data rebuildstats confirm'},
            'dewbackfill': {'summary': '补发历史对局荆露', 'usage': 'data dewbackfill <preview|confirm>'},
            'achievementbackfill': {'summary': '补发可重算成就', 'usage': 'data achievementbackfill <preview|confirm>'},
        },
    },
    'room': {
        'hidden': True,
        'summary': '房间与对局',
        'usage': 'room <list|get|players|log|chat|state|skip|end|set|history> ...',
        'children': {
            'list': {'summary': '列出当前对局', 'usage': 'room list'},
            'get': {'summary': '查看房间摘要、倒计时、模组和 pending 状态', 'usage': 'room get <房间ID>'},
            'players': {'summary': '显示房间内玩家编号、昵称和状态', 'usage': 'room players <房间ID>'},
            'log': {'summary': '查看房间最近战斗日志', 'usage': 'room log <房间ID> [数量]'},
            'chat': {'summary': '查看房间最近聊天', 'usage': 'room chat <房间ID> [数量]'},
            'state': {'summary': '查看精简房间状态 JSON', 'usage': 'room state <房间ID>'},
            'skip': {'summary': '尝试跳过当前回合', 'usage': 'room skip <房间ID>'},
            'end': {'summary': '强制结束对局', 'usage': 'room end <房间ID> <winner|draw>'},
            'set': {'summary': '修改玩家基础数值', 'usage': 'room set <房间ID> <玩家序号> <h|e|m|armor|dodge|poison|burn|toxic|vulnerable> <数值>'},
            'history': {'summary': '查看最近历史对局', 'usage': 'room history [数量]'},
        },
    },
    'card': {
        'hidden': True,
        'summary': '对局内卡牌操作',
        'usage': 'card <add|remove> ...',
        'children': {
            'add': {'summary': '向玩家手牌加入卡牌', 'usage': 'card add <房间ID> <玩家序号> <卡牌ID> [数量] [tags=tag1,tag2] [fusion=层数] [fission=层数]'},
            'remove': {'summary': '删除玩家卡牌', 'usage': 'card remove <房间ID> <玩家序号> <hand|deck|discard|exile|equipment|all> <卡牌ID|all|#序号|instance=ID> [数量|all]'},
        },
    },
    'mod': {
        'hidden': True,
        'summary': '模组与卡池',
        'usage': 'mod <list|loadout> ...',
        'children': {
            'list': {'summary': '列出已加载模组', 'usage': 'mod list'},
            'loadout': {'summary': '查看玩家或房间的模组组合', 'usage': 'mod loadout <sid|昵称|房间ID>'},
        },
    },
    'rating': {
        'hidden': True,
        'summary': '花阶分与排行榜',
        'usage': 'rating <season|list|info|set|add|snapshot|rebuild> ...',
        'children': {
            'season': {'summary': '查看当前赛季信息', 'usage': 'rating season'},
            'list': {'summary': '查看花阶分排行榜', 'usage': 'rating list [season|total] [数量]'},
            'info': {'summary': '查看账号花阶分详情', 'usage': 'rating info <ID|注册顺序|用户名>'},
            'set': {'summary': '手动设置花阶分', 'usage': 'rating set <ID|注册顺序|用户名> <season|total|both> <数值> [原因]'},
            'add': {'summary': '手动增减花阶分', 'usage': 'rating add <ID|注册顺序|用户名> <season|total|both> <+/-数值> [原因]'},
            'snapshot': {'summary': '写入今天的花阶分曲线快照', 'usage': 'rating snapshot <ID|注册顺序|用户名>'},
            'rebuild': {'summary': '用历史 matches 摘要重建初始花阶分', 'usage': 'rating rebuild <preview|confirm>'},
        },
    },
    'chat': {
        'hidden': True,
        'summary': '聊天与广播',
        'usage': 'chat <broadcast|lobby|mute> ...',
        'children': {
            'broadcast': {'summary': '发送服务器广播', 'usage': 'chat broadcast <内容>'},
            'lobby': {'summary': '查看大厅聊天缓存', 'usage': 'chat lobby [数量]'},
            'mute': {'summary': '禁言在线玩家', 'usage': 'chat mute <sid|昵称> [秒数]'},
        },
    },
    'server': {
        'summary': '服务器状态与维护',
        'usage': 'server <status|drain|pull|logs|suspicious|mod|diagnose|clear> ...',
        'children': {
            'status': {'summary': '显示服务器摘要', 'usage': 'server status'},
            'drain': {'summary': '设置/查看静默更新排空模式', 'usage': 'server drain [on|off|status]'},
            'pull': {'summary': '手动拉取 GitHub origin/main', 'usage': 'server pull'},
            'logs': {'summary': '查看最近管理事件', 'usage': 'server logs [数量]'},
            'suspicious': {'summary': '查看最近可疑安全事件', 'usage': 'server suspicious [数量]'},
            'mod': {
                'summary': '查看模组与加载组合',
                'usage': 'server mod <list|loadout> ...',
                'children': {
                    'list': {'summary': '列出已加载模组', 'usage': 'server mod list'},
                    'loadout': {'summary': '查看玩家或房间的模组组合', 'usage': 'server mod loadout <玩家|房间ID>'},
                },
            },
            'diagnose': {
                'summary': '诊断服务器、房间或玩家',
                'usage': 'server diagnose <server|room|player|stuck> ...',
                'children': {
                    'server': {'summary': '诊断服务器', 'usage': 'server diagnose server'},
                    'room': {'summary': '诊断房间', 'usage': 'server diagnose room <房间ID>'},
                    'player': {'summary': '诊断玩家', 'usage': 'server diagnose player <玩家|账号>'},
                    'stuck': {'summary': '列出疑似卡住的房间', 'usage': 'server diagnose stuck'},
                },
            },
            'clear': {'summary': '清空终端输出', 'usage': 'server clear'},
        },
    },
    'storage': {
        'hidden': True,
        'summary': '数据、统计与回放',
        'usage': 'storage <summary|draftstats|rebuildstats|dewbackfill|achievementbackfill> ...',
        'children': {
            'summary': {'summary': '查看数据库、回放和快照占用', 'usage': 'storage summary'},
            'draftstats': {'summary': '查看卡牌选牌抽取率统计', 'usage': 'storage draftstats [1v1|2v2]'},
            'rebuildstats': {'summary': '按永久 matches 摘要重算账号战绩和总对局时长', 'usage': 'storage rebuildstats confirm'},
            'dewbackfill': {'summary': '按历史 matches 摘要补发旧对局荆露', 'usage': 'storage dewbackfill <preview|confirm>'},
            'achievementbackfill': {'summary': '按历史 matches 摘要补发可重算成就', 'usage': 'storage achievementbackfill <preview|confirm>'},
        },
    },
    'report': {
        'hidden': True,
        'summary': '举报与安全记录',
        'usage': 'report <suspicious> ...',
        'children': {
            'suspicious': {'summary': '查看最近可疑安全事件', 'usage': 'report suspicious [数量]'},
        },
    },
    'diagnose': {
        'hidden': True,
        'summary': '一键诊断',
        'usage': 'diagnose <server|room|player|stuck> ...',
        'children': {
            'server': {'summary': '诊断服务器健康、锁、房间和数据库', 'usage': 'diagnose server'},
            'room': {'summary': '诊断指定房间是否卡住', 'usage': 'diagnose room <房间ID>'},
            'player': {'summary': '诊断玩家连接、账号、房间和模组', 'usage': 'diagnose player <sid|昵称|ID|用户名>'},
            'stuck': {'summary': '列出疑似卡住的房间', 'usage': 'diagnose stuck'},
        },
    },
}

def _usage_for_command(command_path):
    node = ADMIN_COMMAND_TREE
    current = None
    for part in command_path:
        current = node.get(part) if isinstance(node, dict) else None
        if not current:
            return ''
        node = current.get('children', {})
    return (current or {}).get('usage', '')


def render_admin_help(parts=None):
    parts = [str(p or '').lower() for p in (parts or []) if str(p or '').strip()]
    if not parts:
        lines = ['可用一级命令：']
        for name, meta in ADMIN_COMMAND_TREE.items():
            if meta.get('hidden'):
                continue
            lines.append(f"/{name:<8} {meta.get('summary', '')}")
        lines.append('')
        lines.append('输入 /help <命令> 逐级查看子命令，例如：/help game player')
        return '\n'.join(lines)
    visible_roots = {name: meta for name, meta in ADMIN_COMMAND_TREE.items() if not meta.get('hidden')}
    first = parts[0]
    if first not in visible_roots:
        suggestion = difflib.get_close_matches(first, visible_roots.keys(), n=1)
        extra = f"\n你是不是想输入：/{suggestion[0]}" if suggestion else ''
        return f"未知命令：/{first}{extra}"
    meta = visible_roots[first]
    path = [first]
    for token in parts[1:]:
        children = meta.get('children', {})
        child = children.get(token)
        if not child or child.get('hidden'):
            visible_children = [name for name, item in children.items() if not item.get('hidden')]
            suggestion = difflib.get_close_matches(token, visible_children, n=1)
            extra = f"\n你是不是想输入：/{' '.join(path + [suggestion[0]])}" if suggestion else ''
            return f"未知子命令：/{' '.join(path + [token])}{extra}"
        meta = child
        path.append(token)
    command_path = ' '.join(path)
    lines = [f"/{command_path} - {meta.get('summary', '')}", '', f"用法：/{meta.get('usage', command_path)}"]
    children = {name: item for name, item in meta.get('children', {}).items() if not item.get('hidden')}
    if children:
        lines.extend(['', '子命令：'])
        for name, child in children.items():
            lines.append(f"  {name:<12} {child.get('summary', '')}")
        lines.extend(['', f"输入 /help {command_path} <子命令> 继续查看。"])
    return '\n'.join(lines)


def command_error(command, pointer=0, expected='', kind='参数错误'):
    caret = ' ' * max(0, pointer) + '^'
    usage = f'\n用法：/{expected}' if expected else ''
    return f'{kind}\n{command}\n{caret}{usage}'


def unknown_command_error(command, cmd):
    public_commands = [name for name, meta in ADMIN_COMMAND_TREE.items() if not meta.get('hidden')]
    suggestion = difflib.get_close_matches(cmd, public_commands, n=1)
    extra = f'\n你是不是想输入：/{suggestion[0]}' if suggestion else ''
    return f'未知命令：/{cmd}{extra}\n输入 /help 查看可用命令。'


def _quote_admin_parts(parts):
    return ' '.join(shlex.quote(str(part)) for part in parts if str(part) != '')


def _translate_structured_admin_command(parts):
    if not parts:
        return None, None
    cmd = parts[0].lower()
    meta = ADMIN_COMMAND_TREE.get(cmd)
    if not meta or meta.get('hidden') or cmd == 'help':
        return None, None
    sub = parts[1].lower() if len(parts) > 1 else ''
    rest = parts[2:]
    command_map = {
        ('player', 'list'): ['players'],
        ('player', 'get'): ['playerget', *rest],
        ('player', 'kick'): ['kick', *rest],
        ('player', 'afkcheck'): ['afkcheck', *rest],
        ('account', 'get'): ['playerget', *rest],
        ('account', 'username'): ['userrename', *rest],
        ('account', 'password'): ['userpass', *rest],
        ('account', 'dew'): ['dew', *rest],
        ('account', 'role'): ['role', *rest],
        ('account', 'ban'): ['banuser', *rest],
        ('account', 'unban'): ['unbanuser', *rest],
        ('game', 'list'): ['rooms'],
        ('game', 'info'): ['roomget', *rest],
        ('game', 'log'): ['roomlog', *rest],
        ('game', 'chat'): ['roomchat', *rest],
        ('game', 'state'): ['roomstate', *rest],
        ('game', 'history'): ['history', *rest],
        ('lobby', 'broadcast'): ['broadcast', *rest],
        ('lobby', 'chat'): ['lobbychat', *rest],
        ('moderation', 'mute'): ['mutechat', *rest],
        ('moderation', 'ban'): ['banuser', *rest],
        ('moderation', 'unban'): ['unbanuser', *rest],
        ('moderation', 'suspicious'): ['suspicious', *rest],
        ('server', 'status'): ['status'],
        ('server', 'drain'): ['drain', *rest],
        ('server', 'pull'): ['gitpull'],
        ('server', 'logs'): ['logs', *rest],
        ('server', 'suspicious'): ['suspicious', *rest],
        ('server', 'clear'): ['clear'],
        ('data', 'summary'): ['storagesummary'],
        ('data', 'draftstats'): ['draftstats', *rest],
        ('data', 'rebuildstats'): ['rebuildstats', *rest],
        ('data', 'dewbackfill'): ['dewbackfill', *rest],
        ('data', 'achievementbackfill'): ['achievementbackfill', *rest],
        ('replay', 'get'): ['replayget', *rest],
        ('replay', 'open'): ['replayopen', *rest],
        ('replay', 'export'): ['replayexport', *rest],
        ('replay', 'hold'): ['replayhold', *rest],
        ('replay', 'release'): ['replayrelease', *rest],
    }
    if not sub:
        return None, render_admin_help([cmd])
    if cmd == 'account' and sub == 'achievement':
        action = str(rest[0] if rest else '').lower()
        args = rest[1:]
        if action == 'grant':
            return _quote_admin_parts(['achievementgrant', *args]), None
        if action == 'list':
            return _quote_admin_parts(['achievementlist', *args]), None
        return None, render_admin_help(['account', 'achievement'])
    if cmd == 'content':
        if sub == 'disable':
            return _quote_admin_parts(['contentdisable', *rest]), None
        if sub == 'enable':
            return _quote_admin_parts(['contentenable', *rest]), None
        if sub == 'disabled':
            action = str(rest[0] if rest else '').lower()
            args = rest[1:]
            if action in ('list', 'show', 'edit'):
                return _quote_admin_parts([f'content{action}', *args]), None
            return None, render_admin_help(['content', 'disabled'])
        return None, render_admin_help(['content'])
    if cmd == 'account' and sub == 'rating':
        action = str(rest[0] if rest else '').lower()
        args = rest[1:]
        if action in ('info', 'set', 'add', 'snapshot'):
            return _quote_admin_parts([f'rating-{action}', *args]), None
        return None, render_admin_help(['account', 'rating'])
    if cmd == 'data' and sub == 'rating':
        action = str(rest[0] if rest else '').lower()
        args = rest[1:]
        if action in ('season', 'list', 'rebuild'):
            return _quote_admin_parts([f'rating-{action}', *args]), None
        return None, render_admin_help(['data', 'rating'])
    if cmd == 'server' and sub == 'mod':
        action = str(rest[0] if rest else '').lower()
        args = rest[1:]
        if action == 'list':
            return 'modlist', None
        if action == 'loadout':
            return _quote_admin_parts(['modloadout', *args]), None
        return None, render_admin_help(['server', 'mod'])
    if cmd == 'server' and sub == 'diagnose':
        action = str(rest[0] if rest else '').lower()
        args = rest[1:]
        if action in ('server', 'room', 'player', 'stuck'):
            return _quote_admin_parts([f'diagnose-{action}', *args]), None
        return None, render_admin_help(['server', 'diagnose'])
    if cmd == 'moderation' and sub in ('ip', 'report'):
        action = str(rest[0] if rest else '').lower()
        args = rest[1:]
        allowed = ('list', 'ban', 'unban') if sub == 'ip' else ('list', 'get', 'resolve')
        if action in allowed:
            return _quote_admin_parts([f'{sub}{action}', *args]), None
        return None, render_admin_help(['moderation', sub])
    if cmd == 'game' and sub == 'action':
        action = str(rest[0] if rest else '').lower()
        args = rest[1:]
        if action == 'skip':
            return _quote_admin_parts(['skip', *args]), None
        if action == 'end':
            return _quote_admin_parts(['endgame', *args]), None
        return None, render_admin_help(['game', 'action'])
    if cmd == 'game' and sub == 'pending':
        action = str(rest[0] if rest else '').lower()
        args = rest[1:]
        if action == 'get':
            return _quote_admin_parts(['gamepending', action, *args]), None
        return None, render_admin_help(['game', 'pending'])
    if cmd == 'game' and sub == 'player':
        if len(rest) < 3:
            return None, render_admin_help(['game', 'player'])
        room_id, player_index, domain = rest[0], rest[1], str(rest[2]).lower()
        args = rest[3:]
        if domain == 'info':
            return _quote_admin_parts(['gameplayerinfo', room_id, player_index]), None
        if domain == 'resource' and args:
            action = str(args[0]).lower()
            if action == 'set':
                return _quote_admin_parts(['set', room_id, player_index, *args[1:]]), None
            if action == 'add':
                return _quote_admin_parts(['resourceadd', room_id, player_index, *args[1:]]), None
        if domain == 'status':
            return _quote_admin_parts(['gamestatus', room_id, player_index, *args]), None
        if domain == 'card' and args:
            action = str(args[0]).lower()
            if action == 'add':
                return _quote_admin_parts(['givecard', room_id, player_index, *args[1:]]), None
            if action == 'remove':
                return _quote_admin_parts(['delcard', room_id, player_index, *args[1:]]), None
            if action == 'list':
                return _quote_admin_parts(['gamecardlist', room_id, player_index, *args[1:]]), None
        return None, render_admin_help(['game', 'player'])
    target = command_map.get((cmd, sub))
    if target is None:
        return None, render_admin_help([cmd, sub])
    return _quote_admin_parts(target), None


def run_git_command(args, timeout=120):
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    proc = subprocess.run(
        ['git', '-C', repo_dir, *args],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=timeout,
        shell=False,
    )
    stdout = (proc.stdout or '').strip()
    stderr = (proc.stderr or '').strip()
    output = '\n'.join(part for part in (stdout, stderr) if part)
    return proc.returncode, output


def ensure_git_clean_tracked_worktree():
    checks = [
        (['diff', '--quiet', '--ignore-submodules', '--'], '存在未提交的工作区改动'),
        (['diff', '--cached', '--quiet', '--ignore-submodules', '--'], '存在已暂存但未提交的改动'),
    ]
    for args, message in checks:
        code, output = run_git_command(args, timeout=30)
        if code == 1:
            return False, message
        if code != 0:
            return False, output or message
    return True, ''


def run_admin_git_pull_main():
    remote = os.environ.get('GTN_GIT_REMOTE', 'origin').strip() or 'origin'
    branch = os.environ.get('GTN_GIT_BRANCH', 'main').strip() or 'main'
    if not re.fullmatch(r'[A-Za-z0-9._/-]+', remote) or not re.fullmatch(r'[A-Za-z0-9._/-]+', branch):
        return {'success': False, 'output': 'GTN_GIT_REMOTE 或 GTN_GIT_BRANCH 含有非法字符。'}

    code, inside = run_git_command(['rev-parse', '--is-inside-work-tree'], timeout=30)
    if code != 0 or inside.strip().lower() != 'true':
        return {'success': False, 'output': '当前代码目录不是 Git 仓库，无法拉取。'}

    code, current_branch = run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'], timeout=30)
    if code != 0:
        return {'success': False, 'output': current_branch or '无法读取当前 Git 分支。'}
    current_branch = current_branch.strip()
    if current_branch != branch:
        return {
            'success': False,
            'output': f'当前分支是 {current_branch}，不是 {branch}。为避免误合并，已取消。',
        }

    clean, reason = ensure_git_clean_tracked_worktree()
    if not clean:
        return {'success': False, 'output': f'工作区不干净，已取消拉取：{reason}'}

    code, before = run_git_command(['rev-parse', '--short', 'HEAD'], timeout=30)
    if code != 0:
        return {'success': False, 'output': before or '无法读取当前提交。'}

    code, fetch_output = run_git_command(['fetch', '--prune', remote, branch], timeout=180)
    if code != 0:
        return {'success': False, 'output': f'fetch 失败：\n{fetch_output}'}

    target = f'{remote}/{branch}'
    code, merge_output = run_git_command(['merge', '--ff-only', target], timeout=180)
    if code != 0:
        return {'success': False, 'output': f'无法 fast-forward 到 {target}：\n{merge_output}'}

    code, after = run_git_command(['rev-parse', '--short', 'HEAD'], timeout=30)
    if code != 0:
        after = '?'
    before = before.strip()
    after = after.strip()
    changed = before != after
    output = [
        f'仓库：{os.path.dirname(os.path.abspath(__file__))}',
        f'分支：{branch}',
        f'远程：{target}',
        f'提交：{before} -> {after}',
        merge_output or ('已更新。' if changed else '已经是最新。'),
    ]
    if changed:
        output.append('提示：代码已更新。如服务没有自动重启，请手动重启 Python 服务使新代码生效。')
    return {'success': True, 'output': '\n'.join(output)}


def find_player_sid(token):
    if token in players:
        return token
    exact = [sid for sid, p in players.items() if p.get('nickname') == token]
    if len(exact) == 1:
        return exact[0]
    lower = token.lower()
    fuzzy = [sid for sid, p in players.items() if lower in p.get('nickname', '').lower()]
    if len(fuzzy) == 1:
        return fuzzy[0]
    return None


def parse_int_token(value, name):
    try:
        return int(value)
    except Exception:
        raise ValueError(f'需要整数 <{name}>')


def resolve_admin_card_id(token):
    if token in CARD_DEFS:
        return token
    lowered = str(token or '').lower()
    matches = [cid for cid in CARD_DEFS if cid.lower() == lowered]
    if len(matches) == 1:
        return matches[0]
    return None


def parse_givecard_options(tokens):
    count = 1
    tags = []
    fusion = 1
    fission = 1
    for token in tokens:
        if token.isdigit():
            count = parse_int_token(token, 'count')
            continue
        key, sep, value = token.partition('=')
        if not sep:
            raise ValueError(f'无法识别参数：{token}')
        key = key.lower().strip()
        value = value.strip()
        if key in ('count', 'n', '数量'):
            count = parse_int_token(value, 'count')
        elif key in ('tag', 'tags', 'flag', 'flags', '标签'):
            tags.extend([t.strip() for t in value.split(',') if t.strip()])
        elif key in ('fusion', 'fuse', '聚变'):
            fusion = parse_int_token(value, 'fusion')
        elif key in ('fission', 'split', '裂变'):
            fission = parse_int_token(value, 'fission')
        else:
            raise ValueError(f'未知参数：{key}')
    return {
        'count': max(1, min(count, 50)),
        'tags': tags,
        'fusion': max(1, fusion),
        'fission': max(1, fission),
    }


def _parse_bool_option(value):
    text = str(value or '').strip().lower()
    if text in ('1', 'true', 'yes', 'y', 'on', '是', '开'):
        return True
    if text in ('0', 'false', 'no', 'n', 'off', '否', '关'):
        return False
    raise ValueError(f'需要布尔值：{value}')


def parse_role_options(tokens):
    options = {
        'title': '',
        'color': '',
        'sort_order': None,
        'role_key': '',
        'can_direct_friend': None,
        'chat_exempt': None,
    }
    for token in tokens:
        key, sep, value = token.partition('=')
        if not sep:
            if not options['title']:
                options['title'] = token
                continue
            raise ValueError(f'无法识别参数：{token}')
        key = key.lower().strip()
        value = value.strip()
        if key in ('title', 'label', 'name', '称号', '名称'):
            options['title'] = value
        elif key in ('color', 'colour', '颜色'):
            options['color'] = value
        elif key in ('sort', 'order', 'rank', '排序'):
            options['sort_order'] = parse_int_token(value, 'sort')
        elif key in ('key', 'role_key', 'prefix_key'):
            options['role_key'] = value
        elif key in ('direct', 'friend', 'direct_friend', '好友'):
            options['can_direct_friend'] = _parse_bool_option(value)
        elif key in ('chat', 'chat_exempt', '聊天'):
            options['chat_exempt'] = _parse_bool_option(value)
        else:
            raise ValueError(f'未知参数：{key}')
    return options


def format_role_profile(user, profile):
    if not profile:
        return f"{user['username']} (ID:{user.get('player_id') or '-'} 注册顺序：{user['id']}) 无特殊身份"
    perms = []
    if profile.get('is_admin_player'):
        perms.append('最高权限')
    if profile.get('can_direct_friend'):
        perms.append('直接加好友')
    if profile.get('chat_exempt'):
        perms.append('聊天无限制')
    return (
        f"{user['username']} (ID:{user.get('player_id') or '-'} 注册顺序：{user['id']}) "
        f"类型={profile.get('role_type')} 称号={profile.get('special_role_label') or '-'} "
        f"颜色={profile.get('special_role_color') or '-'} 排序={profile.get('special_role_sort')} "
        f"权限={','.join(perms) if perms else '-'}"
    )


def format_thorn_dew_user(user):
    if not user:
        return '账号不存在'
    free = int(user.get('thorn_dew_free') or 0)
    paid = int(user.get('thorn_dew_paid') or 0)
    total = free + paid
    return (
        f"{user.get('username')} (ID:{user.get('player_id') or '-'} 注册顺序：{user.get('id')})\n"
        f"荆露：{total}（普通 {free} / 充值 {paid}）"
    )


def format_rating_value(value):
    try:
        return str(int(round(float(value))))
    except (TypeError, ValueError):
        return '-'


def format_gr_delta_value(value):
    try:
        num = float(value)
    except (TypeError, ValueError):
        num = 0.0
    if abs(num) < 0.05:
        return '±0'
    return f"{num:+.1f}"


def gr_preview_text_for_sids(mode, sids, viewer_sid):
    payload = gr_preview_payload_for_sids(mode, sids, viewer_sid)
    return payload.get('text', '') if payload else ''


def gr_preview_payload_for_sids(mode, sids, viewer_sid):
    if not DB_AVAILABLE:
        return {}
    user_ids = []
    for psid in sids or []:
        player = players.get(psid) or {}
        user_ids.append(player.get('user_id') if player.get('is_registered_user') else None)
    if any((players.get(psid) or {}).get('entertainment_mods') for psid in sids or []):
        return {
            'applied': False,
            'reason': 'entertainment_mod',
            'text': '本局使用娱乐模组，不计花阶分',
        }
    viewer = players.get(viewer_sid) or {}
    viewer_user_id = viewer.get('user_id') if viewer.get('is_registered_user') else None
    try:
        preview = preview_gr_match_result(mode, user_ids, viewer_user_id=viewer_user_id)
    except Exception as exc:
        admin_event('error', f'failed to preview GR invite: {exc}')
        return {}
    if not preview.get('applied'):
        reason = preview.get('reason') or ''
        if reason == 'guest_participant':
            text = '本局包含游客，不计花阶分'
        if reason in ('missing_player_ids', 'unknown_user'):
            return {}
        else:
            text = '本局不计花阶分' if reason != 'guest_participant' else text
        return {
            'applied': False,
            'reason': reason,
            'text': text,
        }
    viewer_preview = preview.get('viewer') or {}
    if not viewer_preview:
        return {}
    win_delta = format_gr_delta_value(viewer_preview.get('win_delta'))
    loss_delta = format_gr_delta_value(viewer_preview.get('loss_delta'))
    draw_delta = format_gr_delta_value(viewer_preview.get('draw_delta'))
    text = f'花阶分预估：胜 {win_delta} / 平 {draw_delta} / 负 {loss_delta}'
    repeat = float(preview.get('repeat_factor') or 1)
    if repeat < 0.999:
        text += f'（重复对局×{repeat:.2f}）'
    return {
        'applied': True,
        'text': text,
        'repeat_factor': repeat,
        'repeat_count': preview.get('repeat_count', 0),
        'viewer': {
            'win_delta': viewer_preview.get('win_delta', 0),
            'draw_delta': viewer_preview.get('draw_delta', 0),
            'loss_delta': viewer_preview.get('loss_delta', 0),
        },
    }


def format_rating_user(user):
    if not user:
        return '账号不存在'
    season = current_gr_season()
    return '\n'.join([
        f"{user.get('username')} (ID:{user.get('player_id') or '-'} 注册顺序：{user.get('id')})",
        f"赛季：{season.get('name')}（{admin_display_time(season.get('starts_at'))} 至 {admin_display_time(season.get('ends_at'))}）",
        f"赛季花阶分：{format_rating_value(user.get('season_gr'))} / 计分局：{int(user.get('season_ranked_games') or 0)}",
        f"总花阶分：{format_rating_value(user.get('total_gr'))} / 计分局：{int(user.get('total_ranked_games') or 0)}",
        f"历史最高：{format_rating_value(user.get('highest_gr'))}",
        f"有效对局：{user.get('games_played', 0)} 胜/负/平={user.get('wins', 0)}/{user.get('losses', 0)}/{user.get('draws', 0)}",
    ])


def admin_rating_list_output(scope='season', limit=20):
    if not DB_AVAILABLE:
        return f'数据库不可用：{DB_INIT_ERROR or "-"}'
    scope_text = 'total' if str(scope or '').lower() in ('total', 'all', '总榜') else 'season'
    try:
        safe_limit = max(1, min(int(limit or 20), 100))
    except (TypeError, ValueError):
        safe_limit = 20
    min_games = 20 if scope_text == 'total' else 8
    rows = list_leaderboard(min_games=min_games, limit=safe_limit, scope=scope_text)
    if not rows:
        return '暂无符合条件的花阶分排行。'
    title = '总榜' if scope_text == 'total' else '赛季榜'
    lines = [f"花阶分{title}（最低计分局 {min_games}）", '排名  账号  花阶分  胜率  计分局  胜/负/平']
    for item in rows:
        ranked_games = item.get('total_ranked_games') if scope_text == 'total' else item.get('season_ranked_games')
        lines.append(
            f"{item.get('rank', '-'):<4}  {item.get('username', '-')}  {format_rating_value(item.get('gr'))}  "
            f"{float(item.get('win_rate') or 0):.1f}%  {ranked_games or 0}  "
            f"{item.get('wins', 0)}/{item.get('losses', 0)}/{item.get('draws', 0)}"
        )
    return '\n'.join(lines)


def admin_rating_rebuild_output(result, dry_run=True):
    skip_reasons = result.get('skip_reasons') or {}
    changed = result.get('changed') or []
    user_names = {}
    if DB_AVAILABLE and changed:
        try:
            for item in changed[:30]:
                user = get_user_by_id(item.get('user_id'))
                if user:
                    user_names[int(item.get('user_id'))] = user.get('username') or str(item.get('user_id'))
        except Exception:
            user_names = {}
    lines = [
        '花阶分历史重建预览' if dry_run else '花阶分历史重建已完成',
        f"历史对局：{result.get('matches', 0)}",
        f"计入对局：{result.get('counted_matches', 0)}",
        f"跳过对局：{result.get('skipped_matches', 0)}",
        f"昵称/ID恢复引用：{result.get('recovered_player_refs', 0)}",
    ]
    if skip_reasons:
        lines.append('跳过原因：' + '，'.join(f"{k}={v}" for k, v in sorted(skip_reasons.items())))
    if changed:
        lines.append('')
        lines.append('变化最大的账号：')
        for item in changed[:10]:
            uid = int(item.get('user_id') or 0)
            name = user_names.get(uid, str(uid))
            lines.append(
                f"{name}#{uid} 总榜 {format_rating_value(item.get('total_gr'))} "
                f"赛季 {format_rating_value(item.get('season_gr'))} "
                f"Δ{float(item.get('delta') or 0):+.1f} 局数={int(item.get('total_ranked_games') or 0)}"
            )
    if dry_run:
        lines.append('')
        lines.append('确认覆盖当前花阶分请输入：/data rating rebuild confirm')
    return '\n'.join(lines)


def admin_dew_backfill_output(result):
    dry_run = bool(result.get('dry_run'))
    lines = [
        '荆露历史补发预览' if dry_run else '荆露历史补发已完成',
        f"扫描对局：{result.get('matches_seen', 0)}",
        f"可补发/已补发对局：{result.get('matches_awarded', 0)}",
        f"补发流水：{result.get('transactions', 0)}",
        f"荆露合计：{result.get('total_dew', 0)}",
        f"昵称恢复账号引用：{result.get('recovered_player_refs', 0)}",
    ]
    skipped = result.get('skipped') or {}
    if skipped:
        lines.append('跳过原因：' + '，'.join(f"{k}={v}" for k, v in sorted(skipped.items())))
    errors = result.get('errors') or []
    if errors:
        lines.append('')
        lines.append(f"错误：{len(errors)} 条")
        for item in errors[:8]:
            lines.append(f"  match#{item.get('match_id')}: {item.get('error')}")
        if len(errors) > 8:
            lines.append(f"  ... 另有 {len(errors) - 8} 条")
    if dry_run:
        lines.append('')
        lines.append('确认补发请输入：/data dewbackfill confirm')
    return '\n'.join(lines)


def admin_achievement_backfill_output(result):
    dry_run = bool(result.get('dry_run'))
    cards = result.get('cards_played_backfill') or {}
    lines = [
        '成就历史补发预览' if dry_run else '成就历史补发已完成',
        f"扫描对局：{result.get('matches_seen', 0)}",
        f"含成就标记的对局：{result.get('matches_with_flags', 0)}",
        f"可补发的一次性成就事件：{result.get('flag_events_seen', 0)}",
        f"已解锁成就：{result.get('unlocked', 0)}",
        f"跳过无成就标记对局：{result.get('skipped_no_flags', 0)}",
        f"跳过累计型隐藏成就事件：{result.get('incremental_flags_skipped', 0)}",
        f"错误：{result.get('skipped_errors', 0)}",
    ]
    if cards:
        lines.extend([
            '',
            '花牌流转补偿：',
            f"  补偿对局/玩家：{cards.get('matches_compensated', 0)}/{cards.get('players_compensated', 0)}",
            f"  恢复或补偿进度：{cards.get('cards_total', 0)}张",
            f"  摘要精确恢复：{cards.get('summary_players', 0)}人次",
            f"  回放精确恢复：{cards.get('replay_players', 0)}人次",
            f"  无法恢复按15张补偿：{cards.get('fallback_players', 0)}人次，共{cards.get('fallback_cards', 0)}张",
            f"  已处理跳过：{cards.get('already_processed_players', 0)}人次",
            f"  恢复历史账号引用：{cards.get('recovered_player_refs', 0)}处",
            (
                f"  预计解锁/奖励：{cards.get('would_unlock', 0)}项/{cards.get('would_reward_dew', 0)}荆露"
                if dry_run else
                f"  实际解锁/奖励：{cards.get('unlocked', 0)}项/{cards.get('reward_dew_awarded', 0)}荆露"
            ),
        ])
        card_errors = cards.get('errors') or []
        if card_errors:
            lines.append(f"  花牌流转补偿错误：{len(card_errors)}条")
    examples = result.get('examples') or []
    if examples:
        lines.append('')
        lines.append('示例：')
        for item in examples[:8]:
            if item.get('unlocked'):
                lines.append(f"  match#{item.get('match_id')}: {', '.join(str(v) for v in item.get('unlocked') or [])}")
            else:
                lines.append(f"  match#{item.get('match_id')}: {item.get('events', 0)} 个可补事件")
    if dry_run:
        lines.append('')
        lines.append('确认补发请输入：/data achievementbackfill confirm')
    return '\n'.join(lines)


def _short_hash(value, length=12):
    text = str(value or '')
    return text[:length] if text else '-'


def _format_loadout_from_meta(meta):
    if not meta:
        return '无模组信息'
    mods = meta.get('mods_list') or []
    order = meta.get('v2_load_order') or []
    lines = [
        f"source={meta.get('mod_source', 'official')}",
        f"loadout={_short_hash(meta.get('loadout_hash') or meta.get('mods_hash'))}",
        f"v2={_short_hash(meta.get('v2_loadout_hash'))}",
        f"disabled={','.join(meta.get('disabled_mods') or []) or '-'}",
        f"mods={', '.join(mods) if mods else '-'}",
    ]
    if order:
        lines.append(f"v2_order={', '.join(order)}")
    if meta.get('community_mods'):
        lines.append(f"community={json.dumps(meta.get('community_mods'), ensure_ascii=False)[:600]}")
    return '\n'.join(lines)


def _find_online_player_for_admin(token):
    sid = find_player_sid(str(token or ''))
    if sid and sid in players:
        return sid, players[sid]
    lowered = str(token or '').strip().lower()
    if not lowered:
        return None, None
    for psid, player in players.items():
        if lowered in (
            str(player.get('account_player_id') or '').lower(),
            str(player.get('user_id') or '').lower(),
        ):
            return psid, player
    return None, None


def _sync_admin_username_to_online_players(user):
    try:
        user_id = int(user.get('id'))
    except (TypeError, ValueError, AttributeError):
        return []
    username = str(user.get('username') or '').strip()
    if not username:
        return []
    updated_sids = []
    with _lock:
        for sid, player in players.items():
            try:
                matches = int(player.get('user_id') or 0) == user_id
            except (TypeError, ValueError):
                matches = False
            if not matches:
                continue
            player['nickname'] = username
            player['display_name'] = username
            updated_sids.append(sid)
        for room in rooms.values():
            for player_index, sid in enumerate(getattr(room, 'player_sids', []) or []):
                profile = players.get(sid) or getattr(room, 'disconnected_players', {}).get(sid) or {}
                try:
                    matches = int(profile.get('user_id') or 0) == user_id
                except (TypeError, ValueError):
                    matches = False
                if not matches:
                    continue
                profile['nickname'] = username
                profile['display_name'] = username
                names = getattr(room.engine, 'player_names', []) or []
                if player_index < len(names):
                    names[player_index] = username
    return updated_sids


def _format_online_player_detail(sid, player):
    lines = [
        f"在线玩家：{player.get('nickname', '?')}",
        f"sid={sid}",
        f"账号ID={player.get('user_id') or '-'} 玩家ID={player.get('account_player_id') or '-'}",
        f"状态={zh_status(player.get('status'))} 模式={player.get('mode', '-')}",
        f"房间={player.get('room_id') if player.get('room_id') is not None else '-'} 观战={player.get('spectating_room') if player.get('spectating_room') is not None else '-'}",
        f"内测={bool(player.get('beta_mode'))}",
        f"loadout={_short_hash(player_loadout_hash(player))}",
    ]
    return '\n'.join(lines)


def admin_player_get_output(identifier):
    sid, player = _find_online_player_for_admin(identifier)
    blocks = []
    if player:
        blocks.append(_format_online_player_detail(sid, player))
    if DB_AVAILABLE:
        user = find_user_for_admin(identifier)
        if user:
            blocks.append(
                '\n'.join([
                    f"注册账号：{user.get('username')}",
                    f"注册顺序={user.get('id')} 玩家ID={user.get('player_id') or '-'}",
                    f"有效对局={user.get('games_played', 0)} 胜/负/平={user.get('wins', 0)}/{user.get('losses', 0)}/{user.get('draws', 0)}",
                    f"花阶分：赛季 {format_rating_value(user.get('season_gr'))}（{int(user.get('season_ranked_games') or 0)}局）/ 总榜 {format_rating_value(user.get('total_gr'))}（{int(user.get('total_ranked_games') or 0)}局）",
                    f"总对局时长={format_duration_zh(user.get('play_seconds') or 0)}",
                    f"荆露={user.get('thorn_dew_total', 0)}（普通 {user.get('thorn_dew_free', 0)} / 充值 {user.get('thorn_dew_paid', 0)}）",
                    f"创建={admin_display_time(user.get('created_at'))} 上次下线={admin_display_time(user.get('last_login_at'))}",
                ])
            )
    if not blocks:
        return f'找不到玩家或账号：{identifier}'
    return '\n\n'.join(blocks)


def admin_room_get_output(room_id):
    rid = int(room_id)
    if rid not in rooms:
        return f'不存在房间：{rid}'
    room = rooms[rid]
    e = room.engine
    lines = [
        f"房间 #{rid} mode={room.mode} beta={bool(getattr(room, 'beta_mode', False))}",
        f"阶段={zh_phase(getattr(e, 'phase', ''))} 回合={getattr(e, 'round_num', 0)} 当前玩家={getattr(e, 'current_player', '-')}",
        f"game_over={bool(getattr(e, 'game_over', False))} winner={getattr(e, 'winner', '-')} winning_team={getattr(e, 'winning_team', '-')}",
        f"观战={len(getattr(room, 'spectators', []) or [])} 日志={len(getattr(e, 'log', []) or [])} 聊天={len(getattr(room, 'chat_history', []) or [])}",
        f"action_timer_player={getattr(room, 'action_timer_player', None)} remaining={int(getattr(room, 'action_timer_remaining', 0) or 0)}s",
        f"pending_response={bool(getattr(e, 'pending_response', None))} pending_choice={bool(getattr(e, 'pending_choice', None))} pending_v2_ui={bool(getattr(e, 'pending_v2_ui', None))}",
        f"disconnected={len(getattr(room, 'disconnected_players', {}) or {})} rematch_votes={len(getattr(room, '_rematch_votes', set()) or set())}",
        '',
        '玩家：',
    ]
    for pidx, psid in enumerate(getattr(room, 'player_sids', []) or []):
        ps = e.players[pidx] if pidx < len(getattr(e, 'players', []) or []) else None
        online = psid in players
        name = room_player_nickname(room, psid, '?')
        hp = f"H={ps.health}/{ps.max_health} E={ps.elixir}/{ps.max_elixir} M={ps.magic}/{ps.max_magic}" if ps else ''
        lines.append(f"  {pidx}: {name} sid={psid} {'在线' if online else '断线/离线'} {hp}")
    lines.extend(['', '模组：', _format_loadout_from_meta(room_mod_payload(room))])
    return '\n'.join(lines)


def admin_room_log_output(room_id, count=40):
    rid = int(room_id)
    if rid not in rooms:
        return f'不存在房间：{rid}'
    try:
        safe_count = max(1, min(int(count or 40), 200))
    except Exception:
        safe_count = 40
    logs = list(getattr(rooms[rid].engine, 'log', []) or [])[-safe_count:]
    return '\n'.join(logs) or '暂无战斗日志。'


def admin_room_chat_output(room_id, count=60):
    rid = int(room_id)
    if rid not in rooms:
        return f'不存在房间：{rid}'
    try:
        safe_count = max(1, min(int(count or 60), 200))
    except Exception:
        safe_count = 60
    items = list(getattr(rooms[rid], 'chat_history', []) or [])[-safe_count:]
    lines = []
    for entry in items:
        if entry.get('type') == 'time':
            lines.append(f"--- {entry.get('display_time') or admin_display_time(entry.get('time'))} ---")
            continue
        repeat = int(entry.get('repeat_count') or 1)
        repeat_text = f" ×{repeat}" if repeat > 1 else ''
        lines.append(f"{admin_display_time(entry.get('time'))} [{entry.get('chat_channel') or 'public'}] {entry.get('nickname', '?')}: {entry.get('text', '')}{repeat_text}")
    return '\n'.join(lines) or '暂无房间聊天。'


def admin_room_state_output(room_id):
    rid = int(room_id)
    if rid not in rooms:
        return f'不存在房间：{rid}'
    room = rooms[rid]
    e = room.engine
    payload = {
        'room_id': rid,
        'mode': room.mode,
        'phase': getattr(e, 'phase', ''),
        'round': getattr(e, 'round_num', 0),
        'current_player': getattr(e, 'current_player', None),
        'game_over': bool(getattr(e, 'game_over', False)),
        'winner': getattr(e, 'winner', None),
        'action_timer': {
            'player': getattr(room, 'action_timer_player', None),
            'remaining': int(getattr(room, 'action_timer_remaining', 0) or 0),
        },
        'pending': {
            'response': bool(getattr(e, 'pending_response', None)),
            'choice': bool(getattr(e, 'pending_choice', None)),
            'v2_ui': bool(getattr(e, 'pending_v2_ui', None)),
        },
        'players': [],
    }
    for pidx, psid in enumerate(getattr(room, 'player_sids', []) or []):
        ps = e.players[pidx] if pidx < len(getattr(e, 'players', []) or []) else None
        payload['players'].append({
            'index': pidx,
            'name': room_player_nickname(room, psid, '?'),
            'sid': psid,
            'online': psid in players,
            'health': getattr(ps, 'health', None),
            'max_health': getattr(ps, 'max_health', None),
            'hand': len(getattr(ps, 'hand', []) or []) if ps else None,
            'deck': len(getattr(ps, 'deck', []) or []) if ps else None,
            'equipment': len(getattr(ps, 'equipment', []) or []) if ps else None,
        })
    return json.dumps(payload, ensure_ascii=False, indent=2)


def admin_mod_list_output():
    mods = load_all_mods()
    if not mods:
        return '没有已加载模组。'
    lines = ['模组  版本  作者  卡牌  来源']
    for mod in mods:
        info = getattr(mod, 'info', {}) or {}
        info_get = info.get if isinstance(info, dict) else lambda key, default=None: getattr(info, key, default)
        name = getattr(mod, 'name', '') or info_get('name_cn') or info_get('name') or getattr(mod, 'id', '?')
        version = getattr(mod, 'version', '') or info_get('version') or '-'
        author = getattr(mod, 'author', '') or info_get('author') or '-'
        cards = len(getattr(mod, 'cards', []) or [])
        source = getattr(mod, 'source', '') or getattr(mod, 'filepath', '') or '-'
        lines.append(f"{name}  {version}  {author}  {cards}  {source}")
    return '\n'.join(lines)


def admin_mod_loadout_output(identifier):
    token = str(identifier or '').strip()
    if not token:
        return '缺少 <sid|昵称|房间ID>'
    if token.isdigit() and int(token) in rooms:
        room = rooms[int(token)]
        return f"房间 #{token} 模组组合：\n{_format_loadout_from_meta(room_mod_payload(room))}"
    sid, player = _find_online_player_for_admin(token)
    if not player:
        return f'找不到在线玩家或房间：{identifier}'
    return f"{player.get('nickname', '?')} 模组组合：\n{_format_loadout_from_meta(player)}"


def admin_storage_summary_output():
    if not DB_AVAILABLE:
        return f'数据库不可用：{DB_INIT_ERROR or "-"}'
    payload = storage_summary()
    db = payload.get('db', {})
    replays = payload.get('replays', {})
    mods = payload.get('mod_blobs', {})
    cards = payload.get('card_snapshots', {})
    return '\n'.join([
        f"DB: {db.get('path', '-')} total={db.get('total_file_bytes', 0)} bytes sqlite={db.get('db_file_bytes', 0)} wal={db.get('wal_file_bytes', 0)} shm={db.get('shm_file_bytes', 0)}",
        f"Replays: count={replays.get('count', 0)} bytes={replays.get('bytes', 0)} old={replays.get('old_count', 0)} old_bytes={replays.get('old_bytes', 0)} retention={replays.get('retention_days', '-')}",
        f"Community mod snapshots: count={mods.get('community_count', 0)} bytes={mods.get('community_bytes', 0)} orphan={mods.get('orphan_count', 0)} orphan_bytes={mods.get('orphan_bytes', 0)}",
        f"Card snapshots: count={cards.get('count', 0)} bytes={cards.get('bytes', 0)} orphan={cards.get('orphan_count', 0)} orphan_bytes={cards.get('orphan_bytes', 0)}",
    ])


def admin_diagnose_stuck_output():
    lines = []
    now = time.time()
    for rid, room in rooms.items():
        e = room.engine
        reasons = []
        if getattr(e, 'pending_response', None):
            reasons.append('pending_response')
        if getattr(e, 'pending_choice', None):
            reasons.append('pending_choice')
        if getattr(e, 'pending_v2_ui', None):
            reasons.append('pending_v2_ui')
        if getattr(room, 'action_lock', None) and room.action_lock.locked():
            reasons.append('action_lock')
        if getattr(room, 'disconnected_players', None):
            reasons.append(f"disconnected={len(room.disconnected_players)}")
        if getattr(room, 'created_at', 0) and now - room.created_at > 7200 and not getattr(e, 'game_over', False):
            reasons.append('long_running')
        if reasons:
            lines.append(f"#{rid} {room.mode} phase={getattr(e, 'phase', '')} round={getattr(e, 'round_num', 0)} reasons={','.join(reasons)}")
    return '\n'.join(lines) or '没有发现明显卡住房间。'


def make_admin_card_instance(card_id, options):
    card = CardInstance(def_id=card_id)
    tags = [t for t in options.get('tags', []) if t]
    if tags:
        card.instance_flags = set(getattr(card, 'instance_flags', set()) or set())
        card.instance_flags.update(normalize_card_flag(tag) for tag in tags)
    fusion = int(options.get('fusion', 1) or 1)
    fission = int(options.get('fission', 1) or 1)
    card.fusion_level = max(1, fusion)
    card.fission_level = max(1, fission)
    card.fusion_multiplier = float(card.fusion_level)
    card.fission_count = max(0, card.fission_level - 1)
    return card


ADMIN_CARD_ZONE_ALIASES = {
    'hand': 'hand', 'h': 'hand', '手牌': 'hand',
    'deck': 'deck', 'draw': 'deck', 'drawpile': 'deck', 'd': 'deck', '牌堆': 'deck', '抽牌堆': 'deck',
    'discard': 'discard', 'discardpile': 'discard', 'grave': 'discard', '弃牌': 'discard', '弃牌堆': 'discard',
    'exile': 'exile', 'banish': 'exile', '放逐': 'exile', '放逐区': 'exile',
    'equipment': 'equipment', 'equip': 'equipment', 'root': 'equipment', '装备': 'equipment', '装备区': 'equipment',
    'all': 'all', '*': 'all', '全部': 'all',
}


def normalize_admin_card_zone(token):
    zone = ADMIN_CARD_ZONE_ALIASES.get(str(token or '').strip().lower())
    if not zone:
        raise ValueError('区域必须是 hand/deck/discard/exile/equipment/all')
    return zone


def parse_delcard_selector(token):
    text = str(token or '').strip()
    lowered = text.lower()
    if lowered in ('all', '*', '全部'):
        return {'type': 'all', 'value': None, 'label': 'all'}
    if lowered.startswith('#'):
        return {'type': 'index', 'value': parse_int_token(lowered[1:], 'index'), 'label': text}
    key, sep, value = text.partition('=')
    if sep:
        key = key.lower().strip()
        value = value.strip()
        if key in ('instance', 'instance_id', 'id', 'iid', '实例'):
            return {'type': 'instance', 'value': parse_int_token(value, 'instance_id'), 'label': text}
        if key in ('index', 'idx', 'i', 'pos', '序号'):
            return {'type': 'index', 'value': parse_int_token(value, 'index'), 'label': text}
        if key in ('card', 'card_id', 'def', 'def_id', '卡牌'):
            card_id = resolve_admin_card_id(value) or value
            return {'type': 'card', 'value': card_id, 'label': card_id}
        raise ValueError(f'未知选择器：{key}')
    if lowered.isdigit():
        return {'type': 'instance', 'value': parse_int_token(lowered, 'instance_id'), 'label': text}
    card_id = resolve_admin_card_id(text) or text
    return {'type': 'card', 'value': card_id, 'label': card_id}


def parse_delcard_count(tokens, selector):
    count = None if selector.get('type') == 'all' else 1
    for token in tokens:
        lowered = str(token or '').strip().lower()
        if lowered in ('all', '*', '全部'):
            count = None
            continue
        key, sep, value = lowered.partition('=')
        if sep:
            if key not in ('count', 'n', '数量'):
                raise ValueError(f'未知参数：{key}')
            lowered = value
        count = parse_int_token(lowered, 'count')
    if count is not None:
        count = max(1, min(int(count), 500))
    return count


def _admin_zone_items(ps, zone):
    if zone == 'equipment':
        return ps.equipment
    return getattr(ps, zone)


def _admin_card_from_item(item):
    return getattr(item, 'card_instance', item)


def _admin_card_label(card):
    if not card:
        return '?'
    cd = CARD_DEFS.get(getattr(card, 'def_id', ''), None)
    name = cd.name_cn if cd else getattr(card, 'def_id', '?')
    return f'{name}#{getattr(card, "instance_id", "?")}'


ADMIN_RESOURCE_ATTRS = {
    'h': 'health', 'health': 'health',
    'maxh': 'max_health', 'max_health': 'max_health',
    'e': 'elixir', 'elixir': 'elixir',
    'maxe': 'max_elixir', 'max_elixir': 'max_elixir',
    'm': 'magic', 'magic': 'magic',
    'maxm': 'max_magic', 'max_magic': 'max_magic',
    'armor': 'armor',
}

ADMIN_STATUS_ATTRS = {
    'poison': 'poison', '中毒': 'poison',
    'fire': 'fire', 'burn': 'fire', '灼烧': 'fire',
    'toxic': 'toxic', '淬毒': 'toxic',
    'triangle': 'triangle_stacks', 'triangle_stacks': 'triangle_stacks', '三角形': 'triangle_stacks',
    'dodge': 'dodge', '闪避': 'dodge',
    'equipment_protection': 'equipment_protection', '装备护甲': 'equipment_protection',
    'invincible': 'invincible', '无敌': 'invincible',
    'skip_turn': 'skip_turn', 'dizzy': 'skip_turn', '眩晕': 'skip_turn',
    'attack_blocked': 'attack_blocked', '禁攻': 'attack_blocked',
    'untargetable': 'untargetable', '无法选中': 'untargetable',
    'sluggish': 'sluggish', '迟缓': 'sluggish',
    'overload': 'overload', '超载': 'overload',
    'foresight': 'foresight', '预知': 'foresight',
    'fracture': 'fracture', '破损': 'fracture',
    'stagnation': 'stagnation', '滞留': 'stagnation',
    'blind': 'blind', '失明': 'blind',
    'heal_block': 'heal_block', '禁疗': 'heal_block',
    'weakness': 'weakness', '虚弱': 'weakness',
    'bleed': 'bleed', '流血': 'bleed',
    'fragment': 'fragment_stacks', 'fragment_stacks': 'fragment_stacks', '碎片': 'fragment_stacks',
}

ADMIN_STATUS_CANONICAL = {
    attr: next(name for name, mapped in ADMIN_STATUS_ATTRS.items() if mapped == attr and name.isascii())
    for attr in set(ADMIN_STATUS_ATTRS.values())
}


def _admin_room_player(room_id, pidx):
    room = rooms.get(int(room_id))
    if room is None:
        return None, None, f'不存在房间：{room_id}'
    try:
        player_index = int(pidx)
    except (TypeError, ValueError):
        return room, None, '玩家序号必须是整数'
    engine_players = getattr(room.engine, 'players', []) or []
    if player_index < 0 or player_index >= len(engine_players):
        return room, None, f'玩家序号必须在 0-{len(engine_players) - 1} 之间'
    return room, engine_players[player_index], ''


def admin_game_player_info_output(room_id, pidx):
    with _lock:
        room, ps, error = _admin_room_player(room_id, pidx)
        if error:
            return error
        player_index = int(pidx)
        player_sids = getattr(room, 'player_sids', []) or []
        sid = player_sids[player_index] if player_index < len(player_sids) else None
        name = room_player_nickname(room, sid, f'Player {player_index}')
        statuses = _admin_status_items(ps)
        return '\n'.join([
            f'房间 #{room_id} 玩家 {player_index}: {name}',
            f'H={ps.health}/{ps.max_health} E={ps.elixir}/{ps.max_elixir} M={ps.magic}/{ps.max_magic} 护甲={ps.armor}',
            f'手牌={len(ps.hand)} 抽牌堆={len(ps.deck)} 弃牌堆={len(ps.discard)} 放逐区={len(ps.exile)} 装备={len(ps.equipment)}',
            '状态：' + (', '.join(f'{key}={value}' for key, value in statuses) if statuses else '无'),
        ])


def _admin_status_items(ps):
    items = []
    for attr, name in sorted(ADMIN_STATUS_CANONICAL.items(), key=lambda item: item[1]):
        value = getattr(ps, attr, 0)
        numeric = int(bool(value)) if isinstance(value, bool) else int(value or 0)
        if numeric:
            items.append((name, numeric))
    for name, value in sorted((getattr(ps, 'custom_statuses', {}) or {}).items()):
        try:
            numeric = int(value or 0)
        except (TypeError, ValueError):
            continue
        if numeric:
            items.append((str(name), numeric))
    return items


def _admin_status_value(ps, status):
    status_key = str(status or '').strip()
    attr = ADMIN_STATUS_ATTRS.get(status_key.lower()) or ADMIN_STATUS_ATTRS.get(status_key)
    if attr:
        value = getattr(ps, attr, 0)
        return int(bool(value)) if isinstance(value, bool) else int(value or 0), attr
    custom = getattr(ps, 'custom_statuses', {}) or {}
    return int(custom.get(status_key, 0) or 0), None


def _set_admin_status_value(engine, ps, status, value):
    status_key = str(status or '').strip()
    attr = ADMIN_STATUS_ATTRS.get(status_key.lower()) or ADMIN_STATUS_ATTRS.get(status_key)
    value = max(0, int(value))
    if attr:
        current = getattr(ps, attr, 0)
        setattr(ps, attr, bool(value) if isinstance(current, bool) else value)
        if attr == 'invincible' and not value:
            ps.invincible_until_player = None
            ps.invincible_granted_round = -1
            ps.invincible_granted_turn_marker = -1
        return ADMIN_STATUS_CANONICAL.get(attr, status_key), value
    ps.custom_statuses = getattr(ps, 'custom_statuses', {}) or {}
    if status_key in ('status_immune', 'immune', '状态免疫'):
        for alias in ('status_immune', 'immune', '状态免疫'):
            ps.custom_statuses.pop(alias, None)
        if value:
            ps.custom_statuses['status_immune'] = 1
        return 'status_immune', 1 if value else 0
    if value:
        ps.custom_statuses[status_key] = value
    else:
        ps.custom_statuses.pop(status_key, None)
    try:
        engine._normalize_status_value(ps, status_key)
    except Exception:
        pass
    return status_key, value


def admin_game_status(room_id, pidx, action, status=None, value=None):
    action = str(action or 'list').lower()
    with _lock:
        room, ps, error = _admin_room_player(room_id, pidx)
        if error:
            return False, error
        if action == 'list':
            items = _admin_status_items(ps)
            return True, '\n'.join(f'{name}={amount}' for name, amount in items) or '无状态。'
        if action == 'get':
            if not status:
                return False, '缺少状态ID'
            amount, _attr = _admin_status_value(ps, status)
            return True, f'{status}={amount}'
        if action == 'clear':
            for attr in ADMIN_STATUS_CANONICAL:
                current = getattr(ps, attr, 0)
                setattr(ps, attr, False if isinstance(current, bool) else 0)
            ps.custom_statuses = {}
            ps.invincible_until_player = None
            ps.invincible_granted_round = -1
            ps.invincible_granted_turn_marker = -1
            changed = '全部状态'
        elif action in ('set', 'add', 'remove'):
            if not status:
                return False, '缺少状态ID'
            current, _attr = _admin_status_value(ps, status)
            amount = 1 if value is None else int(value)
            target = amount if action == 'set' else current + amount if action == 'add' else current - amount
            normalized, final_value = _set_admin_status_value(room.engine, ps, status, target)
            changed = f'{normalized}={final_value}'
        else:
            return False, '操作必须是 list/get/set/add/remove/clear'
        record_room_replay_action(room, 'admin_status_change', None, {
            'player_id': int(pidx), 'action': action, 'status': status, 'value': value,
        })
    broadcast_game_state(room)
    return True, f'已修改房间 {room_id} 玩家 {pidx}：{changed}'


def admin_game_card_list_output(room_id, pidx, zone='all'):
    try:
        normalized_zone = normalize_admin_card_zone(zone or 'all')
    except ValueError as exc:
        return str(exc)
    with _lock:
        _room, ps, error = _admin_room_player(room_id, pidx)
        if error:
            return error
        zones = ['hand', 'deck', 'discard', 'exile', 'equipment'] if normalized_zone == 'all' else [normalized_zone]
        lines = []
        for zone_name in zones:
            items = list(_admin_zone_items(ps, zone_name) or [])
            lines.append(f'[{zone_name}] {len(items)}')
            lines.extend(f'  #{index} {_admin_card_label(_admin_card_from_item(item))}' for index, item in enumerate(items))
        return '\n'.join(lines)


def admin_game_pending_output(room_id):
    with _lock:
        room = rooms.get(int(room_id))
        if room is None:
            return f'不存在房间：{room_id}'
        engine = room.engine
        payload = {
            'phase': getattr(engine, 'phase', None),
            'current_player': getattr(engine, 'current_player', None),
            'pending_response': getattr(engine, 'pending_response', None),
            'pending_choice': getattr(engine, 'pending_choice', None),
            'pending_v2_ui': getattr(engine, 'pending_v2_ui', None),
            'action_lock': bool(getattr(room, 'action_lock', None) and room.action_lock.locked()),
            'timer_player': getattr(room, 'action_timer_player', None),
            'timer_remaining': getattr(room, 'action_timer_remaining', None),
        }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def _admin_selector_matches(item, selector):
    card = _admin_card_from_item(item)
    if selector['type'] == 'all':
        return True
    if selector['type'] == 'instance':
        return getattr(card, 'instance_id', None) == selector['value']
    if selector['type'] == 'card':
        return getattr(card, 'def_id', None) == selector['value']
    return False


def zh_status(value):
    return {
        'lobby': '大厅',
        'in_game': '对局中',
        'spectating': '观战中',
        'reconnecting': '重连中',
        'solo': '单人训练',
        'tutorial': '新手教程',
    }.get(value, value)


def zh_phase(value):
    return {
        'action': '行动',
        'draw': '抽牌',
        'response': '响应',
        'choice': '选择',
        'playing': '进行中',
        'draft': '选牌',
        'event_select': '配装倾向',
        'game_over': '结束',
    }.get(value, value)


def send_system_broadcast(message):
    msg = str(message or '').strip()[:500]
    if not msg:
        return 0
    payload = {
        'nickname': '系统',
        'text': msg,
        'system': True,
        'is_spectator': False,
    }
    now = time.time()
    with _lock:
        append_lobby_chat_locked(payload, now, beta_mode=False)
        append_lobby_chat_locked(payload, now, beta_mode=True)
        append_admin_game_chat_locked(payload, now, scope='system')
        lobby_history_payloads = lobby_chat_history_payloads_locked(LOBBY_CHAT_VISIBLE_LIMIT)
        recipients = [(sid, p.get('status')) for sid, p in players.items()]
    if DB_AVAILABLE:
        for beta_mode in (False, True):
            try:
                record_chat_message(
                    f'lobby:{_lobby_chat_scope_key(beta_mode)}',
                    'system',
                    None,
                    payload.get('nickname', '系统'),
                    payload.get('text', ''),
                    json.dumps({**payload, 'type': 'chat', 'beta_mode': bool(beta_mode)}, ensure_ascii=False),
                    0,
                    hidden=False,
                )
            except Exception as exc:
                admin_event('error', f'failed to persist system lobby chat: {exc}')
    sent = 0
    for sid, status in recipients:
        if status == 'lobby':
            continue
        socketio.emit('chat', payload, room=sid)
        sent += 1
    emit_lobby_chat_history_payloads(lobby_history_payloads)
    socketio.emit('server_broadcast', {'message': f'[系统]{msg}'})
    return sent


def _resolve_content_card(token):
    query = str(token or '').strip().casefold()
    matches = []
    for card_id, card_def in CARD_DEFS.items():
        values = {
            str(card_id).strip().casefold(),
            str(getattr(card_def, 'name_cn', '') or '').strip().casefold(),
            str(getattr(card_def, 'name_en', '') or '').strip().casefold(),
        }
        if query in values:
            matches.append((card_id, card_def))
    if not matches:
        return None, f'找不到卡牌：{token}'
    ids = {item[0] for item in matches}
    if len(ids) > 1:
        return None, '卡牌名称不唯一，请改用 ID：' + '、'.join(sorted(ids))
    return matches[0], None


def _resolve_content_mod(token):
    query = str(token or '').strip().casefold()
    matches = []
    for mod in load_all_mods():
        info = getattr(mod, 'info', None)
        manifest = getattr(mod, 'manifest', None)
        values = {
            str(mod.filename or '').strip().casefold(),
            str(getattr(info, 'id', '') or '').strip().casefold(),
            str(getattr(manifest, 'id', '') or '').strip().casefold(),
            str(getattr(info, 'name', '') or '').strip().casefold(),
            str(getattr(info, 'name_cn', '') or '').strip().casefold(),
            str(getattr(info, 'name_en', '') or '').strip().casefold(),
        }
        if query in values:
            matches.append(mod)
    filenames = {mod.filename for mod in matches}
    if not matches:
        return None, f'找不到模组：{token}'
    if len(filenames) > 1:
        return None, '模组名称不唯一，请改用文件名：' + '、'.join(sorted(filenames))
    return matches[0], None


def _parse_content_duration(value):
    text = str(value or '').strip().lower()
    if text in ('', '0', 'permanent', 'forever', 'manual', '永久'):
        return None
    match = re.fullmatch(r'(\d+)(s|m|h|d|w)?', text)
    if not match:
        raise ValueError('时长格式应为 30m、2h、7d、1w 或 permanent')
    number = int(match.group(1))
    multiplier = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800, None: 1}[match.group(2)]
    seconds = number * multiplier
    if seconds <= 0 or seconds > 10 * 365 * 86400:
        raise ValueError('时长必须大于0且不超过10年')
    return seconds


def _parse_content_options(tokens, default_scope='all'):
    options = {'scope': default_scope, 'source_scope': '', 'duration': None, 'reason': '', 'force': False, 'provided': set()}
    reason_parts = []
    for token in tokens:
        text = str(token or '').strip()
        lower = text.lower()
        if lower == 'force':
            options['force'] = True
        elif lower.startswith('mode='):
            options['scope'] = lower.split('=', 1)[1] or 'all'
            options['provided'].add('scope')
        elif lower.startswith('from='):
            options['source_scope'] = lower.split('=', 1)[1] or 'all'
        elif lower.startswith('duration='):
            options['duration'] = _parse_content_duration(lower.split('=', 1)[1])
            options['provided'].add('duration')
        elif lower.startswith('reason='):
            reason_parts.append(text.split('=', 1)[1])
            options['provided'].add('reason')
        elif re.fullmatch(r'\d+(?:s|m|h|d|w)', lower) or lower in ('permanent', 'forever', '永久'):
            options['duration'] = _parse_content_duration(lower)
            options['provided'].add('duration')
        else:
            reason_parts.append(text)
            options['provided'].add('reason')
    if options['scope'] not in CONTENT_DISABLE_SCOPES and options['scope'] != 'all-scopes':
        raise ValueError('mode 必须是 ' + '、'.join(CONTENT_DISABLE_SCOPES))
    if options['source_scope'] and options['source_scope'] not in CONTENT_DISABLE_SCOPES:
        raise ValueError('from 必须是 ' + '、'.join(CONTENT_DISABLE_SCOPES))
    options['reason'] = ' '.join(part for part in reason_parts if part).strip()
    return options


def _content_object(kind, token):
    kind = str(kind or '').lower()
    if kind == 'card':
        resolved, error = _resolve_content_card(token)
        if error:
            return None, error
        card_id, card_def = resolved
        return {
            'kind': 'card', 'id': card_id,
            'label': f'{card_def.name_cn}/{card_def.name_en} ({card_id})',
            'requires_force': card_id in CONTENT_DISABLE_FORCE_CARD_IDS,
        }, None
    if kind == 'mod':
        mod, error = _resolve_content_mod(token)
        if error:
            return None, error
        info = getattr(mod, 'info', None)
        label = getattr(info, 'name_cn', '') or getattr(info, 'name', '') or mod.filename
        return {
            'kind': 'mod', 'id': mod.filename,
            'label': f'{label} ({mod.filename})',
            'requires_force': mod.filename == VANILLA_MOD_FILENAME,
        }, None
    return None, '类型必须是 card 或 mod'


def _format_content_disable(row):
    active = bool(row.get('active'))
    expires = row.get('expires_at') or '手动恢复前'
    expired = False
    if active and row.get('expires_at'):
        try:
            expired = datetime.fromisoformat(str(row['expires_at']).replace('Z', '+00:00')).timestamp() <= time.time()
        except Exception:
            expired = False
    state_label = '已过期' if expired else ('停用' if active else '已恢复')
    return (
        f"#{row.get('id')} [{state_label}] {row.get('content_type')} "
        f"{row.get('content_id')} mode={row.get('scope_mode')} 到期={expires}\n"
        f"原因：{row.get('reason') or '未填写'} | 操作者：{row.get('disabled_by') or '-'} | 更新：{row.get('updated_at') or '-'}"
    )


def _format_replay_admin_detail(item):
    if not item:
        return '回放不存在或已被清理。'
    players = list(item.get('players') or [])
    player_ids = list(item.get('player_ids') or [])
    participants = []
    for index, name in enumerate(players):
        uid = player_ids[index] if index < len(player_ids) else None
        participants.append(f'{name} (uid={uid})' if uid not in (None, '') else str(name))
    hold = item.get('hold') or {}
    hold_text = '无'
    if hold:
        hold_text = hold.get('expires_at') or '永久'
        if hold.get('reason'):
            hold_text += f"，原因={hold.get('reason')}"
    return '\n'.join([
        f"{format_replay_id(item.get('id'))} | match={item.get('match_id')} | {item.get('mode') or '-'} | {item.get('created_at') or '-'}",
        f"玩家：{' / '.join(participants) or '-'}",
        f"结果：{item.get('result') or '-'} | 胜者={item.get('winner_name') or '-'} | 回合={item.get('round_num') or 0} | 时长={int(item.get('duration_ms') or 0) / 1000:.1f}s",
        f"模组：{item.get('mod_source') or 'official'} {item.get('community_mod_name') or ''}".rstrip(),
        f"大小：{item.get('replay_size') or 0} bytes | 保留：{hold_text}",
    ])


def execute_admin_command(line, _internal=False):
    raw = (line or '').strip()
    if not raw:
        return {'success': False, 'output': command_error('', 0, '指令')}
    if raw.startswith('/'):
        raw = raw[1:].lstrip()
        if not raw:
            return {'success': False, 'output': command_error('/', 1, '指令')}
    try:
        parts = shlex.split(raw)
    except ValueError as exc:
        return {'success': False, 'output': f'指令解析失败：{exc}'}
    cmd = parts[0].lower()
    public_roots = {
        name for name, meta in ADMIN_COMMAND_TREE.items()
        if not meta.get('hidden')
    }
    if not _internal and cmd not in public_roots:
        return {'success': False, 'output': unknown_command_error(raw, cmd)}
    if cmd == 'help':
        return {'success': True, 'output': render_admin_help(parts[1:])}
    translated, structured_error = _translate_structured_admin_command(parts)
    if structured_error:
        return {'success': False, 'output': structured_error}
    if translated:
        return execute_admin_command(translated, _internal=True)
    if cmd == 'clear':
        return {'success': True, 'output': '', 'clear': True}
    if cmd in ('replayget', 'replayopen', 'replayexport', 'replayhold', 'replayrelease'):
        usage = {
            'replayget': 'replay get <R-回放ID>',
            'replayopen': 'replay open <R-回放ID>',
            'replayexport': 'replay export <R-回放ID>',
            'replayhold': 'replay hold <R-回放ID> [天数|permanent] [原因]',
            'replayrelease': 'replay release <R-回放ID>',
        }[cmd]
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), usage)}
        try:
            replay_id = normalize_replay_id(parts[1])
        except ValueError as exc:
            return {'success': False, 'output': str(exc)}
        detail = get_replay_admin_detail(replay_id)
        if not detail:
            return {'success': False, 'output': '回放不存在或已被清理。'}
        if cmd == 'replayget':
            return {'success': True, 'output': _format_replay_admin_detail(detail)}
        if cmd == 'replayopen':
            output = _format_replay_admin_detail(detail)
            output += f'\n摘要接口：/api/replays/{replay_id}?admin=1'
            output += f'\n时间线接口：/api/replays/{replay_id}/timeline?admin=1'
            return {'success': True, 'output': output}
        actor = str(session.get('username') or 'adminconsole')
        if cmd == 'replayexport':
            default_dir = '/root/gtn-incidents' if os.name != 'nt' else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp', 'replay-exports')
            result = export_replay_json_file(replay_id, os.environ.get('GTN_REPLAY_EXPORT_DIR') or default_dir)
            admin_event('admin', f'replay {replay_id} exported path={result.get("path") if result else "-"}')
            return {
                'success': bool(result),
                'output': (
                    f"已导出 {format_replay_id(replay_id)}\n{result.get('path')}\n"
                    f"{result.get('bytes')} bytes | sha256={result.get('sha256')}"
                ) if result else '回放导出失败。',
            }
        if cmd == 'replayrelease':
            released = release_replay_hold(replay_id)
            admin_event('admin', f'replay {replay_id} hold released={released}')
            return {'success': True, 'output': f'{format_replay_id(replay_id)} ' + ('已解除保留。' if released else '原本没有保留记录。')}
        duration = str(parts[2] if len(parts) >= 3 else '180').strip().lower()
        if duration in ('permanent', 'forever', '永久'):
            days = None
        else:
            duration = duration[:-1] if duration.endswith('d') else duration
            try:
                days = max(1, min(int(duration), 3650))
            except ValueError:
                return {'success': False, 'output': '保留期限应为天数或 permanent。'}
        reason = ' '.join(parts[3:]).strip() or '管理员保留'
        hold = hold_replay(replay_id, days=days, reason=reason, created_by=actor)
        admin_event('admin', f'replay {replay_id} held until={(hold or {}).get("expires_at") or "permanent"}')
        return {
            'success': bool(hold),
            'output': f"已保留 {format_replay_id(replay_id)} 至 {(hold or {}).get('expires_at') or '永久'}。",
        }
    if cmd in ('contentdisable', 'contentenable', 'contentshow', 'contentedit'):
        if len(parts) < 3:
            usage = {
                'contentdisable': 'content disable <card|mod> <对象> [duration=1h] [mode=all] [reason=原因] [force]',
                'contentenable': 'content enable <card|mod> <对象> [mode=all|all-scopes]',
                'contentshow': 'content disabled show <card|mod> <对象>',
                'contentedit': 'content disabled edit <card|mod> <对象> [duration=1h] [mode=all] [reason=原因]',
            }[cmd]
            return {'success': False, 'output': command_error(raw, len(raw), usage)}
        if not DB_AVAILABLE:
            return {'success': False, 'output': f'数据库不可用：{DB_INIT_ERROR or "-"}'}
        obj, error = _content_object(parts[1], parts[2])
        if error:
            return {'success': False, 'output': error}
        try:
            options = _parse_content_options(parts[3:])
        except ValueError as exc:
            return {'success': False, 'output': str(exc)}
        if cmd == 'contentshow':
            rows = [
                row for row in list_content_disables(include_inactive=True)
                if row.get('content_type') == obj['kind'] and row.get('content_id') == obj['id']
            ]
            return {'success': True, 'output': '\n\n'.join(_format_content_disable(row) for row in rows) or f'{obj["label"]} 没有停用记录。'}
        if cmd == 'contentenable':
            scope = options['scope'] if 'scope' in options['provided'] else 'all-scopes'
            count = deactivate_content_disable(obj['kind'], obj['id'], scope)
            invalidate_content_disable_cache()
            admin_event('admin', f'content enabled type={obj["kind"]} id={obj["id"]} scope={scope} count={count}')
            return {'success': count > 0, 'output': f'已恢复 {obj["label"]}，停用记录 {count} 条。' if count else '没有匹配的生效中停用记录。'}
        existing_rows = [
            row for row in list_content_disables(include_inactive=False)
            if row.get('content_type') == obj['kind'] and row.get('content_id') == obj['id']
        ]
        if cmd == 'contentdisable' and obj['requires_force'] and not options['force']:
            return {'success': False, 'output': (
                f'{obj["label"]} 是开局流程或基础牌池依赖。\n'
                '确认仍要停用时，在命令末尾加 force。'
            )}
        if cmd == 'contentdisable' and not options['force']:
            check_modes = ('1v1', '2v2', 'random_deck') if options['scope'] == 'all' else (options['scope'],)
            pool_errors = []
            for check_mode in check_modes:
                if check_mode not in ('1v1', '2v2', 'random_deck'):
                    continue
                candidate = set(build_mod_loadout([], runtime_mode=check_mode)['allowed_card_ids'])
                if obj['kind'] == 'card':
                    candidate.discard(obj['id'])
                else:
                    candidate.difference_update(runtime_disabled_mod_card_ids({obj['id']}))
                    if obj['id'] == VANILLA_MOD_FILENAME:
                        candidate.difference_update(BUILTIN_SETUP_CARD_IDS)
                issue = runtime_card_pool_issue(candidate, check_mode)
                if issue:
                    pool_errors.append(f'{check_mode}: {issue}')
            if pool_errors:
                return {'success': False, 'output': '\n'.join(pool_errors) + '\n确认仍要停用时，在命令末尾加 force。'}
        if cmd == 'contentedit':
            source_scope = options['source_scope'] or (options['scope'] if 'scope' in options['provided'] else 'all')
            existing = next((row for row in existing_rows if row.get('scope_mode') == source_scope), None)
            if existing is None and len(existing_rows) == 1 and not options['source_scope']:
                existing = existing_rows[0]
                source_scope = existing.get('scope_mode') or 'all'
            if existing is None:
                return {'success': False, 'output': '找不到要修改的生效中停用记录，请先使用 content disabled show 查看范围。'}
            reason = options['reason'] if 'reason' in options['provided'] else existing.get('reason', '')
            duration = options['duration']
            if 'duration' not in options['provided'] and existing.get('expires_at'):
                try:
                    expires = datetime.fromisoformat(str(existing['expires_at']).replace('Z', '+00:00'))
                    duration = max(1, int(expires.timestamp() - time.time()))
                except Exception:
                    duration = None
            target_scope = options['scope'] if 'scope' in options['provided'] else source_scope
            if target_scope != source_scope:
                deactivate_content_disable(obj['kind'], obj['id'], source_scope)
        else:
            reason = options['reason'] or '临时安全停用'
            duration = options['duration']
            target_scope = options['scope']
        actor = str(session.get('username') or 'adminconsole')
        row = upsert_content_disable(
            obj['kind'], obj['id'], target_scope,
            reason=reason, disabled_by=actor, duration_seconds=duration,
        )
        invalidate_content_disable_cache()
        action_label = '修改停用' if cmd == 'contentedit' else '停用'
        admin_event('admin', f'content {action_label} type={obj["kind"]} id={obj["id"]} scope={target_scope} reason={reason}')
        return {'success': True, 'output': f'已{action_label}（仅影响之后创建的对局）：\n{obj["label"]}\n{_format_content_disable(row)}'}
    if cmd == 'contentlist':
        if not DB_AVAILABLE:
            return {'success': False, 'output': f'数据库不可用：{DB_INIT_ERROR or "-"}'}
        kind = str(parts[1] if len(parts) > 1 else 'all').lower()
        state = str(parts[2] if len(parts) > 2 else 'active').lower()
        if kind not in ('all', 'card', 'mod') or state not in ('active', 'all'):
            return {'success': False, 'output': command_error(raw, len(raw), 'content disabled list [card|mod|all] [active|all]')}
        rows = list_content_disables('' if kind == 'all' else kind, include_inactive=state == 'all')
        return {'success': True, 'output': '\n\n'.join(_format_content_disable(row) for row in rows) or '当前没有匹配的停用项。'}
    if cmd in ('gitpull', 'pullmain', 'updatecode'):
        result = run_admin_git_pull_main()
        admin_event('admin' if result.get('success') else 'error', f"gitpull: {result.get('output', '')[:240]}")
        return result
    if cmd == 'drain':
        action = (parts[1].lower() if len(parts) > 1 else 'status')
        if action in ('on', 'true', '1', 'start', 'enable'):
            set_instance_draining(True)
            admin_event('deploy', f'drain enabled from console instance={GTN_INSTANCE_ID}')
        elif action in ('off', 'false', '0', 'stop', 'disable'):
            set_instance_draining(False)
            admin_event('deploy', f'drain disabled from console instance={GTN_INSTANCE_ID}')
        elif action not in ('status', 'show'):
            return {'success': False, 'output': command_error(raw, len(parts[0]) + 1, 'on|off|status')}
        with _lock:
            room_count = len(rooms)
            player_count = len(players)
        return {'success': True, 'output': (
            f"Drain: {'ON' if is_instance_draining() else 'OFF'}\n"
            f"Instance: {GTN_INSTANCE_ID} | Version: {GTN_VERSION} | Port: {GTN_PORT}\n"
            f"Rooms: {room_count} | Players: {player_count}\n"
            f"Drain file: {GTN_DRAIN_FILE or '-'}"
        )}
    if cmd == 'status':
        payload = get_admin_status_payload()
        summary = payload['summary']
        metrics = payload['metrics']
        profile = metrics.get('server_profile', {})
        socket_metrics = metrics.get('socket', {})
        r2_metrics = metrics.get('r2', {})
        return {'success': True, 'output': (
            f"Instance: {profile.get('instance_id') or profile.get('id') or GTN_INSTANCE_ID} | "
            f"Port: {profile.get('port', GTN_PORT)} | Drain: {'ON' if is_instance_draining() else 'OFF'} | "
            f"Branch: {profile.get('git_branch', os.environ.get('GTN_GIT_BRANCH', 'main'))} | "
            f"Service: {profile.get('service_name') or '-'}\n"
            f"在线：{summary['online_players']} | 大厅：{summary['lobby_players']} | "
            f"对局：{summary['rooms']} | 观战：{summary['spectators']}\n"
            f"运行时间：{metrics['uptime_seconds']} 秒 | "
            f"CPU：进程 {metrics['process']['cpu_percent']}% / 系统 {metrics['system']['cpu_percent']}% | "
            f"进程内存：{metrics['process']['memory_rss']} 字节\n"
            f"Socket RTT均值：{socket_metrics.get('latency', {}).get('avg_ms')} ms | "
            f"操作p95：{socket_metrics.get('actions', {}).get('p95_ms')} ms | "
            f"广播p95：{socket_metrics.get('broadcasts', {}).get('p95_ms')} ms\n"
            f"R2社区模组：{r2_metrics.get('mod_count')} | "
            f"Index均值：{r2_metrics.get('index_avg_ms')} ms | "
            f"上传失败：{r2_metrics.get('upload_failures')}"
        )}
    if cmd == 'players':
        with _lock:
            rows = build_admin_players()
        if not rows:
            return {'success': True, 'output': '当前没有在线玩家。'}
        return {'success': True, 'output': '\n'.join(
            f"{'[内测]' if p.get('beta_mode') else '[正式]'} {p['nickname']} ID:{p.get('player_id') or '-'} [{p['sid']}] 状态={zh_status(p['status'])} 房间={p.get('room_id')}" for p in rows
        )}
    if cmd == 'playerget':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), 'player get <sid|昵称|ID|注册顺序|用户名>')}
        return {'success': True, 'output': admin_player_get_output(parts[1])}
    if cmd == 'rooms':
        with _lock:
            rows = build_admin_rooms()
        if not rows:
            return {'success': True, 'output': '当前没有进行中的对局。'}
        return {'success': True, 'output': '\n'.join(
            f"#{r['room_id']} {r['mode']} 阶段={zh_phase(r['phase'])} 回合={r['round']} 观战={r['spectators']} 玩家={' vs '.join(r['players'])}"
            for r in rows
        )}
    if cmd == 'roomget':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), 'game info <房间ID>')}
        return {'success': True, 'output': admin_room_get_output(parse_int_token(parts[1], 'room_id'))}
    if cmd == 'roomlog':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), 'game log <房间ID> [数量]')}
        count = parse_int_token(parts[2], 'count') if len(parts) > 2 else 40
        return {'success': True, 'output': admin_room_log_output(parse_int_token(parts[1], 'room_id'), count)}
    if cmd == 'roomchat':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), 'game chat <房间ID> [数量]')}
        count = parse_int_token(parts[2], 'count') if len(parts) > 2 else 60
        return {'success': True, 'output': admin_room_chat_output(parse_int_token(parts[1], 'room_id'), count)}
    if cmd == 'roomstate':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), 'game state <房间ID>')}
        return {'success': True, 'output': admin_room_state_output(parse_int_token(parts[1], 'room_id'))}
    if cmd == 'gameplayerinfo':
        if len(parts) < 3:
            return {'success': False, 'output': command_error(raw, len(raw), 'game player <房间> <玩家> info')}
        output = admin_game_player_info_output(parse_int_token(parts[1], 'room_id'), parse_int_token(parts[2], 'player_index'))
        return {'success': not output.startswith(('不存在房间', '玩家序号')), 'output': output}
    if cmd == 'gamecardlist':
        if len(parts) < 3:
            return {'success': False, 'output': command_error(raw, len(raw), 'game player <房间> <玩家> card list [区域]')}
        output = admin_game_card_list_output(parts[1], parts[2], parts[3] if len(parts) > 3 else 'all')
        return {'success': not output.startswith(('不存在房间', '玩家序号', '区域必须')), 'output': output}
    if cmd == 'gamepending':
        if len(parts) < 3 or parts[1].lower() != 'get':
            return {'success': False, 'output': command_error(raw, len(raw), 'game pending get <房间ID>')}
        output = admin_game_pending_output(parse_int_token(parts[2], 'room_id'))
        return {'success': not output.startswith('不存在房间'), 'output': output}
    if cmd == 'gamestatus':
        if len(parts) < 4:
            return {'success': False, 'output': command_error(raw, len(raw), 'game player <房间> <玩家> status <list|get|set|add|remove|clear> [...]')}
        value = parse_int_token(parts[5], 'value') if len(parts) > 5 else None
        ok, output = admin_game_status(parts[1], parts[2], parts[3], parts[4] if len(parts) > 4 else None, value)
        if ok and parts[3].lower() not in ('list', 'get'):
            admin_event('admin', f'game status room={parts[1]} player={parts[2]} action={parts[3]} status={parts[4] if len(parts) > 4 else "-"} value={value}')
        return {'success': ok, 'output': output}
    if cmd in ('roomplayers', 'rplayers', 'rp'):
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), '<房间ID>')}
        room_id = parse_int_token(parts[1], 'room_id')
        with _lock:
            if room_id not in rooms:
                return {'success': False, 'output': f'不存在房间：{room_id}'}
            room = rooms[room_id]
            e = room.engine
            rows = []
            for pidx, sid in enumerate(room.player_sids):
                if sid in players:
                    nickname = players[sid].get('nickname', '?')
                    account_player_id = players[sid].get('account_player_id') or '-'
                    online = '在线'
                elif sid in room.disconnected_players:
                    nickname = room.disconnected_players[sid].get('nickname', '?')
                    account_player_id = room.disconnected_players[sid].get('account_player_id') or '-'
                    online = '断线'
                else:
                    nickname = '?'
                    account_player_id = '-'
                    online = '未知'
                ps = e.players[pidx] if pidx < len(e.players) else None
                team = ''
                if room.mode == '2v2' and hasattr(e, 'team_of'):
                    team = f" 队伍={e.team_of(pidx)}"
                if ps is not None:
                    rows.append(
                        f"{pidx}: {nickname} ID:{account_player_id} [{sid}] {online}{team} "
                        f"H={ps.health}/{ps.max_health} E={ps.elixir}/{ps.max_elixir} M={ps.magic}/{ps.max_magic} 手牌={len(ps.hand)}"
                    )
                else:
                    rows.append(f"{pidx}: {nickname} ID:{account_player_id} [{sid}] {online}{team}")
        return {'success': True, 'output': '\n'.join(rows) or '房间内没有玩家。'}
    if cmd == 'logs':
        count = parse_int_token(parts[1], 'count') if len(parts) > 1 else 20
        rows = list(ADMIN_EVENTS)[:max(1, min(count, 120))]
        return {'success': True, 'output': '\n'.join(f"{admin_display_time(e.get('time'))} [{e['kind']}] {e['message']}" for e in rows) or '暂无日志。'}
    if cmd == 'suspicious':
        count = parse_int_token(parts[1], 'count') if len(parts) > 1 else 30
        rows = recent_suspicious_events(max(1, min(count, 200)))
        return {'success': True, 'output': '\n'.join(
            f"{admin_display_time(e.get('ts'))} [{e.get('severity')}] {e.get('kind')} sid={e.get('sid') or '-'} user={e.get('user_id') or '-'} ip={e.get('ip') or '-'} {e.get('message')}"
            for e in rows
        ) or '暂无可疑安全事件。'}
    if cmd == 'lobbychat':
        count = parse_int_token(parts[1], 'count') if len(parts) > 1 else 200
        with _lock:
            rows = _lobby_chat_recent_locked(max(1, min(count, 200)))
        lines = []
        for entry in rows:
            if entry.get('type') == 'time':
                lines.append(f"--- {entry.get('display_time') or admin_display_time(entry.get('time'))} ---")
                continue
            channel = entry.get('chat_channel') or 'public'
            repeat = int(entry.get('repeat_count') or 1)
            repeat_text = f" x{repeat}" if repeat > 1 else ''
            system_prefix = '[系统]' if entry.get('system') else ''
            lines.append(
                f"{admin_display_time(entry.get('time'))} {system_prefix}{entry.get('nickname', '?')} "
                f"[{channel}]{repeat_text}: {entry.get('text', '')}"
            )
        return {'success': True, 'output': '\n'.join(lines) or '暂无大厅聊天。'}
    if cmd == 'history':
        count = parse_int_token(parts[1], 'count') if len(parts) > 1 else 20
        rows = list(MATCH_HISTORY)[:max(1, min(count, 80))]
        return {'success': True, 'output': '\n'.join(
            f"{admin_display_time(h.get('time'))} #{h['room_id']} {h['mode']} 回合={h['round']} 胜者={h['winner']} 玩家={' vs '.join(h['players'])}"
            for h in rows
        ) or '暂无历史对局。'}
    if cmd == 'rating-season':
        season = current_gr_season()
        return {'success': True, 'output': '\n'.join([
            f"当前赛季：{season.get('name')}",
            f"开始：{admin_display_time(season.get('starts_at'))}",
            f"结束：{admin_display_time(season.get('ends_at'))}",
            '赛季软重置会在玩家数据读取或计分时自动执行。',
        ])}
    if cmd == 'rating-list':
        scope = parts[1] if len(parts) > 1 else 'season'
        count_token = parts[2] if len(parts) > 2 else (parts[1] if len(parts) > 1 and str(parts[1]).isdigit() else '20')
        if str(scope).isdigit():
            scope = 'season'
        count = parse_int_token(count_token, 'count') if str(count_token).strip() else 20
        return {'success': True, 'output': admin_rating_list_output(scope, count)}
    if cmd == 'rating-info':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), 'account rating info <账号>')}
        if not DB_AVAILABLE:
            return {'success': False, 'output': f'数据库不可用：{DB_INIT_ERROR or "-"}'}
        user = find_user_for_admin(parts[1])
        return {'success': bool(user), 'output': format_rating_user(user)}
    if cmd in ('rating-set', 'rating-add'):
        if len(parts) < 4:
            usage = 'account rating set <账号> <season|total|both> <数值> [原因]' if cmd == 'rating-set' else 'account rating add <账号> <season|total|both> <+/-数值> [原因]'
            return {'success': False, 'output': command_error(raw, len(raw), usage)}
        if not DB_AVAILABLE:
            return {'success': False, 'output': f'数据库不可用：{DB_INIT_ERROR or "-"}'}
        reason = ' '.join(parts[4:]).strip() or 'admin command'
        if cmd == 'rating-set':
            user, error = admin_set_user_gr(parts[1], parts[2], parts[3], reason=reason)
            action_label = '设置'
        else:
            user, error = admin_adjust_user_gr(parts[1], parts[2], parts[3], reason=reason)
            action_label = '调整'
        if error:
            return {'success': False, 'output': error}
        admin_event('admin', f"GR {action_label} {user.get('username')}#{user.get('id')} scope={parts[2]} value={parts[3]} reason={reason}")
        return {'success': True, 'output': f'已{action_label}花阶分。\n{format_rating_user(user)}'}
    if cmd == 'rating-snapshot':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), 'account rating snapshot <账号>')}
        if not DB_AVAILABLE:
            return {'success': False, 'output': f'数据库不可用：{DB_INIT_ERROR or "-"}'}
        user, error = admin_snapshot_user_gr(parts[1])
        if error:
            return {'success': False, 'output': error}
        admin_event('admin', f"GR snapshot written for {user.get('username')}#{user.get('id')}")
        return {'success': True, 'output': f'已写入今天的花阶分曲线快照。\n{format_rating_user(user)}'}
    if cmd == 'rating-rebuild':
        if not DB_AVAILABLE:
            return {'success': False, 'output': f'数据库不可用：{DB_INIT_ERROR or "-"}'}
        action = parts[1].lower() if len(parts) > 1 else 'preview'
        if action in ('preview', 'dryrun', 'dry-run', '试算'):
            try:
                result = rebuild_gr_from_matches(dry_run=True)
                return {'success': True, 'output': admin_rating_rebuild_output(result, dry_run=True)}
            except Exception as exc:
                admin_event('error', f'GR rebuild preview failed: {exc}')
                return {'success': False, 'output': f'花阶分重建预览失败：{exc}'}
        if action not in ('confirm', '确认'):
            return {'success': False, 'output': command_error(raw, len(raw), 'data rating rebuild <preview|confirm>')}
        try:
            result = rebuild_gr_from_matches(dry_run=False)
            admin_event('admin', f"GR rebuilt from matches counted={result.get('counted_matches')} skipped={result.get('skipped_matches')}")
            return {'success': True, 'output': admin_rating_rebuild_output(result, dry_run=False)}
        except Exception as exc:
            admin_event('error', f'GR rebuild failed: {exc}')
            return {'success': False, 'output': f'花阶分重建失败：{exc}'}
    if cmd in ('draftstats', 'draftstat', 'pickrate'):
        mode = parts[1] if len(parts) > 1 else ''
        if mode and mode not in ('1v1', '2v2'):
            return {'success': False, 'output': command_error(raw, len(raw), '[1v1|2v2]')}
        if not DB_AVAILABLE:
            return {'success': False, 'output': f'数据库不可用：{DB_INIT_ERROR or "-"}'}
        data = list_card_draft_stats(mode=mode, sort='pick_rate', order='desc', limit=30)
        rows = data.get('items', [])
        if not rows:
            return {'success': True, 'output': '暂无选牌统计。'}
        lines = ['模式  卡牌ID  名称  抽取/刷出  抽取率']
        for item in rows:
            card_def = CARD_DEFS.get(item.get('card_id'))
            name = card_def.name_cn if card_def else item.get('card_id')
            lines.append(
                f"{item['mode']}  {item['card_id']}  {name}  "
                f"{item['picked_count']}/{item['shown_count']}  {item['pick_rate']:.1f}%"
            )
        return {'success': True, 'output': '\n'.join(lines)}
    if cmd == 'storagesummary':
        return {'success': True, 'output': admin_storage_summary_output()}
    if cmd == 'modlist':
        return {'success': True, 'output': admin_mod_list_output()}
    if cmd == 'modloadout':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), 'mod loadout <sid|昵称|房间ID>')}
        return {'success': True, 'output': admin_mod_loadout_output(parts[1])}
    if cmd == 'diagnose-server':
        payload = get_admin_status_payload_light()
        lock_snapshot = _lock.snapshot()
        summary = payload.get('summary', {})
        return {'success': True, 'output': '\n'.join([
            '服务器诊断：',
            f"db_ok={DB_AVAILABLE} db_error={DB_INIT_ERROR or '-'}",
            f"players={summary.get('online_players')} lobby={summary.get('lobby_players')} rooms={summary.get('rooms')} spectators={summary.get('spectators')}",
            f"global_lock held={lock_snapshot.get('held')} held_seconds={lock_snapshot.get('held_seconds')} owner={lock_snapshot.get('owner')}",
            admin_diagnose_stuck_output(),
        ])}
    if cmd == 'diagnose-room':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), 'server diagnose room <房间ID>')}
        rid = parse_int_token(parts[1], 'room_id')
        return {'success': True, 'output': admin_room_get_output(rid) + '\n\n最近日志：\n' + admin_room_log_output(rid, 20)}
    if cmd == 'diagnose-player':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), 'diagnose player <sid|昵称|ID|用户名>')}
        return {'success': True, 'output': admin_player_get_output(parts[1])}
    if cmd == 'diagnose-stuck':
        return {'success': True, 'output': admin_diagnose_stuck_output()}
    if cmd in ('rebuildstats', 'recalcstats', '重算战绩'):
        if not DB_AVAILABLE:
            return {'success': False, 'output': f'数据库不可用：{DB_INIT_ERROR or "-"}'}
        if len(parts) < 2 or parts[1].lower() not in ('confirm', '确认'):
            return {'success': False, 'output': (
                '这是覆盖式重算，会用 matches 摘要表重建账号战绩和总对局时长。\n'
                '它不依赖 3 个月回放，但如果未来删除了 matches 摘要，则不能再安全使用。\n'
                '确认执行请输入：/data rebuildstats confirm'
            )}
        try:
            result = rebuild_user_stats_from_matches()
            play_result = rebuild_user_play_seconds_from_matches()
            admin_event('admin', f"user stats rebuilt from matches: stats={result} play={play_result}")
            return {'success': True, 'output': (
                '已按永久 matches 摘要重算账号统计和总对局时长。\n'
                f"账号数：{result.get('users', 0)}\n"
                f"历史对局：{result.get('matches', 0)}\n"
                f"计入有效对局：{result.get('counted_matches', 0)}\n"
                f"跳过：{result.get('skipped_matches', 0)}\n"
                f"回填对局时间的对局：{play_result.get('counted_matches', 0)}\n"
                f"累计对局秒数：{play_result.get('total_seconds', 0)}"
            )}
        except Exception as exc:
            admin_event('error', f'rebuild user stats failed: {exc}')
            return {'success': False, 'output': f'重算失败：{exc}'}
    if cmd in ('dewbackfill', 'backfilldew', '补发荆露'):
        if not DB_AVAILABLE:
            return {'success': False, 'output': f'数据库不可用：{DB_INIT_ERROR or "-"}'}
        sub = parts[1].lower() if len(parts) > 1 else 'preview'
        if sub in ('preview', 'dryrun', 'dry-run', '试算', '预览'):
            try:
                result = backfill_match_thorn_dew_from_matches(dry_run=True)
                return {'success': True, 'output': admin_dew_backfill_output(result)}
            except Exception as exc:
                admin_event('error', f'thorn dew backfill preview failed: {exc}')
                return {'success': False, 'output': f'荆露补发预览失败：{exc}'}
        if sub in ('confirm', '确认'):
            try:
                result = backfill_match_thorn_dew_from_matches(dry_run=False)
                admin_event(
                    'admin',
                    f"thorn dew backfill confirmed matches={result.get('matches_awarded', 0)} "
                    f"tx={result.get('transactions', 0)} total={result.get('total_dew', 0)}"
                )
                return {'success': True, 'output': admin_dew_backfill_output(result)}
            except Exception as exc:
                admin_event('error', f'thorn dew backfill failed: {exc}')
                return {'success': False, 'output': f'荆露补发失败：{exc}'}
        return {'success': False, 'output': command_error(raw, len(parts[0]) + 1, 'data dewbackfill <preview|confirm>')}
    if cmd in ('achievementbackfill', 'backfillachievements', 'achievementsbackfill', '补发成就'):
        if not DB_AVAILABLE:
            return {'success': False, 'output': f'数据库不可用：{DB_INIT_ERROR or "-"}'}
        sub = parts[1].lower() if len(parts) > 1 else 'preview'
        if sub in ('preview', 'dryrun', 'dry-run', '试算', '预览'):
            try:
                result = backfill_achievements_from_matches(dry_run=True)
                return {'success': True, 'output': admin_achievement_backfill_output(result)}
            except Exception as exc:
                admin_event('error', f'achievement backfill preview failed: {exc}')
                return {'success': False, 'output': f'成就补发预览失败：{exc}'}
        if sub in ('confirm', '确认'):
            try:
                result = backfill_achievements_from_matches(dry_run=False)
                cards = result.get('cards_played_backfill') or {}
                admin_event(
                    'admin',
                    f"achievement backfill confirmed matches={result.get('matches_with_flags', 0)} "
                    f"unlocked={result.get('unlocked', 0)} cards_recovered={cards.get('cards_total', 0)} "
                    f"fallback_players={cards.get('fallback_players', 0)}"
                )
                return {'success': True, 'output': admin_achievement_backfill_output(result)}
            except Exception as exc:
                admin_event('error', f'achievement backfill failed: {exc}')
                return {'success': False, 'output': f'成就补发失败：{exc}'}
        return {'success': False, 'output': command_error(raw, len(parts[0]) + 1, 'data achievementbackfill <preview|confirm>')}
    if cmd == 'broadcast':
        msg = raw[len(parts[0]):].strip()
        if not msg:
            return {'success': False, 'output': command_error(raw, len(raw), '<内容>')}
        sent = send_system_broadcast(msg)
        admin_event('admin', f'broadcast: {msg}')
        return {'success': True, 'output': f'已发送广播：{msg}'}
    if cmd in ('role', 'userrole'):
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), 'role list|get|set|clear')}
        sub = parts[1].lower()
        if sub == 'list':
            query = parts[2] if len(parts) > 2 else ''
            rows = list_user_roles(query=query, limit=120)
            if not rows:
                return {'success': True, 'output': '暂无特殊身份。'}
            lines = ['账号  ID  类型  称号  颜色  排序  权限']
            for row in rows:
                perms = []
                if row.get('role_type') == 'admin':
                    perms.append('最高权限')
                if row.get('can_direct_friend'):
                    perms.append('直接加好友')
                if row.get('chat_exempt'):
                    perms.append('聊天无限制')
                lines.append(
                    f"{row.get('username')}  {row.get('player_id') or '-'}  {row.get('role_type')}  "
                    f"{row.get('title') or '-'}  {row.get('color') or '-'}  {row.get('sort_order')}  "
                    f"{','.join(perms) if perms else '-'}"
                )
            return {'success': True, 'output': '\n'.join(lines)}
        if sub == 'get':
            if len(parts) < 3:
                return {'success': False, 'output': command_error(raw, len(raw), '<ID|注册顺序|用户名>')}
            user = find_user_for_admin(parts[2])
            if not user:
                return {'success': False, 'output': '账号不存在'}
            profile = get_user_role_profile(user['id'])
            return {'success': True, 'output': format_role_profile(user, profile)}
        if sub == 'clear':
            if len(parts) < 3:
                return {'success': False, 'output': command_error(raw, len(raw), '<ID|注册顺序|用户名>')}
            user, error = admin_clear_user_role(parts[2])
            if error:
                return {'success': False, 'output': error}
            admin_event('admin', f"cleared role for account {user['username']}#{user['id']}")
            return {'success': True, 'output': f"已清除 {user['username']} 的特殊身份。"}
        if sub == 'set':
            if len(parts) < 4:
                return {'success': False, 'output': command_error(raw, len(raw), '<ID|注册顺序|用户名> <admin|staff|contributor|sponsor> [title=称号] [color=bloom]')}
            try:
                options = parse_role_options(parts[4:])
            except ValueError as exc:
                return {'success': False, 'output': str(exc)}
            user, profile, error = admin_set_user_role(
                parts[2],
                parts[3],
                title=options.get('title', ''),
                color=options.get('color', ''),
                sort_order=options.get('sort_order'),
                role_key=options.get('role_key', ''),
                can_direct_friend=options.get('can_direct_friend'),
                chat_exempt=options.get('chat_exempt'),
            )
            if error:
                return {'success': False, 'output': error}
            admin_event('admin', f"set role for account {user['username']}#{user['id']} -> {profile.get('role_type') if profile else 'none'}")
            output = format_role_profile(user, profile)
            with _lock:
                for psid, player in players.items():
                    if player.get('user_id') == user['id']:
                        player.update(special_public_fields(profile or {}))
                broadcast_lobby()
            return {'success': True, 'output': output}
        return {'success': False, 'output': command_error(raw, len(raw), 'role list|get|set|clear')}
    if cmd in ('dew', 'thorndew', 'jinglu', '荆露'):
        if len(parts) < 3 or parts[1].lower() not in ('get', 'add', 'addpaid', 'paid', 'spend', 'tx', 'history'):
            return {'success': False, 'output': command_error(raw, len(raw), 'account dew <get|add|addpaid|spend|tx> <账号> [数量] [原因]')}
        sub = parts[1].lower()
        user = find_user_for_admin(parts[2])
        if not user:
            return {'success': False, 'output': '账号不存在'}
        if sub == 'get':
            balance = get_user_thorn_dew(user['id'])
            user = dict(user)
            user['thorn_dew_free'] = balance['free']
            user['thorn_dew_paid'] = balance['paid']
            return {'success': True, 'output': format_thorn_dew_user(user)}
        if sub in ('tx', 'history'):
            rows = list_user_thorn_dew_transactions(user['id'], limit=20)
            lines = [format_thorn_dew_user(user), '', '最近流水：']
            if not rows:
                lines.append('暂无流水。')
            for row in rows:
                free_delta = int(row.get('free_delta') or 0)
                paid_delta = int(row.get('paid_delta') or 0)
                delta_text = []
                if free_delta:
                    delta_text.append(f"普通{free_delta:+d}")
                if paid_delta:
                    delta_text.append(f"充值{paid_delta:+d}")
                lines.append(
                    f"{admin_display_time(row.get('created_at'))} {'/'.join(delta_text) or '0'} "
                    f"余额={row.get('balance_total_after')} 原因={row.get('reason') or '-'}"
                )
            return {'success': True, 'output': '\n'.join(lines)}
        if len(parts) < 4:
            return {'success': False, 'output': command_error(raw, len(raw), '<数量>')}
        try:
            amount = int(parts[3])
        except (TypeError, ValueError):
            return {'success': False, 'output': '数量必须是整数'}
        reason = ' '.join(parts[4:]).strip() or 'admin command'
        admin_name = 'console'
        if sub == 'add':
            updated, error = adjust_user_thorn_dew(user['id'], free_delta=amount, reason=reason, source_type='admin_command', admin_username=admin_name)
        elif sub in ('addpaid', 'paid'):
            updated, error = adjust_user_thorn_dew(user['id'], paid_delta=amount, reason=reason, source_type='admin_command', admin_username=admin_name)
        else:
            updated, error = spend_user_thorn_dew(user['id'], amount, reason=reason, source_type='admin_command', admin_username=admin_name)
        if error:
            return {'success': False, 'output': error}
        admin_event('admin', f"thorn dew {sub} user={user['username']}#{user['id']} amount={amount} reason={reason}")
        return {'success': True, 'output': format_thorn_dew_user(updated)}
    if cmd in ('userpass', 'passwd', 'setpass'):
        if len(parts) < 3:
            return {'success': False, 'output': command_error(raw, len(raw), '<ID|注册顺序|用户名> <新密码>')}
        user, error = admin_change_user_password(parts[1], parts[2])
        if error:
            return {'success': False, 'output': error}
        kicked = _disconnect_account_sockets(
            user.get('id'),
            '密码已由管理员修改，所有已登录设备已退出。\n请重新登录。',
            code='password_changed',
        )
        admin_event('admin', f"changed password for account {user['username']}#{user['id']}")
        return {'success': True, 'output': f"已修改账号 {user['username']} (ID:{user.get('player_id') or '-'} 注册顺序：{user['id']}) 的密码。已退出在线设备 {kicked} 个。"}
    if cmd == 'userrename':
        if len(parts) < 3:
            return {'success': False, 'output': command_error(raw, len(raw), 'account username <账号> <新用户名>')}
        old_user = find_user_for_admin(parts[1])
        user, error = admin_change_username(parts[1], parts[2])
        if error:
            return {'success': False, 'output': error}
        updated_sids = _sync_admin_username_to_online_players(user)
        if updated_sids:
            broadcast_lobby()
        admin_event(
            'admin',
            f"changed username for account #{user['id']} {old_user.get('username') if old_user else parts[1]} -> {user['username']}",
        )
        return {
            'success': True,
            'output': (
                f"已将账号用户名修改为 {user['username']}。\n"
                f"ID:{user.get('player_id') or '-'} 注册顺序：{user['id']} 在线同步：{len(updated_sids)} 个会话。"
            ),
        }
    if cmd == 'achievementgrant':
        if len(parts) < 3:
            return {'success': False, 'output': command_error(raw, len(raw), 'account achievement grant <账号> <成就ID>')}
        result, error = admin_grant_user_achievement(parts[1], parts[2])
        if error:
            return {'success': False, 'output': error}
        user = result['user']
        achievement = result['achievement']
        newly_unlocked = bool(result.get('newly_unlocked'))
        notified = 0
        if newly_unlocked:
            items = _format_achievement_unlocked_items([achievement])
            with _lock:
                target_sids = [
                    sid for sid, player in players.items()
                    if str(player.get('user_id') or '') == str(user.get('id'))
                ]
            for sid in target_sids:
                socketio.emit('achievement_unlocked', {'items': items}, room=sid)
                notified += 1
        admin_event(
            'admin',
            f"achievement grant user={user['username']}#{user['id']} achievement={achievement.get('id')} newly_unlocked={newly_unlocked}",
        )
        state = '已发放' if newly_unlocked else '此前已获得'
        return {
            'success': True,
            'output': (
                f"{state}成就：{achievement.get('name_cn') or achievement.get('id')} "
                f"({achievement.get('id')})\n账号：{user['username']} "
                f"(ID:{user.get('player_id') or '-'} 注册顺序：{user['id']})\n"
                f"荆露奖励：{int(achievement.get('reward_dew') or 0)} 在线提示：{notified} 个会话。"
            ),
        }
    if cmd == 'achievementlist':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), 'account achievement list <账号>')}
        if not DB_AVAILABLE:
            return {'success': False, 'output': f'数据库不可用：{DB_INIT_ERROR or "-"}'}
        user = find_user_for_admin(parts[1])
        if not user:
            return {'success': False, 'output': '账号不存在'}
        center = get_user_achievement_center(user['id'], lang='zh') or {}
        items = center.get('achievements') or center.get('items') or []
        unlocked = [item for item in items if item.get('unlocked') or item.get('completed')]
        lines = [
            f"{user.get('username')} (ID:{user.get('player_id') or '-'} 注册顺序：{user.get('id')})",
            f"成就：{len(unlocked)}/{len(items)}",
        ]
        for item in unlocked:
            lines.append(f"  {item.get('name') or item.get('name_cn') or item.get('id')} ({item.get('id')})")
        return {'success': True, 'output': '\n'.join(lines)}
    if cmd == 'iplist':
        if not DB_AVAILABLE:
            return {'success': False, 'output': f'数据库不可用：{DB_INIT_ERROR or "-"}'}
        active_only = not (len(parts) > 1 and parts[1].lower() == 'all')
        data = list_ip_bans(active_only=active_only, limit=50, offset=0)
        rows = data.get('items') or []
        lines = [f"IP 封禁：{len(rows)}/{data.get('total', len(rows))}"]
        for row in rows:
            state = '生效中' if row.get('active') or row.get('banned') else '已解除'
            lines.append(f"{row.get('ip')}  {state}  {row.get('reason') or '-'}  {row.get('expires_at') or '永久'}")
        return {'success': True, 'output': '\n'.join(lines)}
    if cmd == 'ipban':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), 'moderation ip ban <IP> [时长秒] [原因]')}
        duration = None
        reason_start = 2
        if len(parts) > 2:
            try:
                duration = max(1, int(parts[2]))
                reason_start = 3
            except (TypeError, ValueError):
                duration = None
        reason = ' '.join(parts[reason_start:]).strip()
        row, error = set_ip_ban(parts[1], True, reason, duration_seconds=duration, banned_by='console')
        if error:
            return {'success': False, 'output': error}
        kicked = []
        with _lock:
            for sid, player in list(players.items()):
                if str(player.get('ip') or '') == str(parts[1]):
                    kicked.append(sid)
                    remove_player_by_admin(sid)
        for sid in kicked:
            socketio.emit('server_error', {'message': 'IP 已被封禁'}, room=sid)
            socketio.emit('kicked', {'reason': 'ip banned'}, room=sid)
            socketio.server.disconnect(sid)
        if kicked:
            broadcast_lobby()
        admin_event('moderation', f'console banned ip {parts[1]}: {reason or "-"}')
        return {'success': True, 'output': f'已封禁 IP {parts[1]}，已踢出 {len(kicked)} 个会话。'}
    if cmd == 'ipunban':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), 'moderation ip unban <IP>')}
        _row, error = set_ip_ban(parts[1], False)
        if error:
            return {'success': False, 'output': error}
        admin_event('moderation', f'console unbanned ip {parts[1]}')
        return {'success': True, 'output': f'已解除 IP {parts[1]} 的封禁。'}
    if cmd == 'reportlist':
        if not DB_AVAILABLE:
            return {'success': False, 'output': f'数据库不可用：{DB_INIT_ERROR or "-"}'}
        status = parts[1].lower() if len(parts) > 1 else 'pending'
        limit = parse_int_token(parts[2], 'count') if len(parts) > 2 else 30
        data = list_reports(status=status, limit=max(1, min(limit, 50)), offset=0)
        rows = data.get('items') or []
        lines = [f"举报：{len(rows)}/{data.get('total', len(rows))}"]
        for row in rows:
            lines.append(
                f"#{row.get('id')} [{row.get('status')}] {row.get('reporter_username') or '?'} -> "
                f"{row.get('target_username') or '?'}  {row.get('category') or '-'}  {row.get('reason_text') or '-'}"
            )
        return {'success': True, 'output': '\n'.join(lines)}
    if cmd == 'reportget':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), 'moderation report get <举报ID>')}
        detail = get_report_detail(parse_int_token(parts[1], 'report_id'))
        if not detail:
            return {'success': False, 'output': '举报不存在'}
        return {'success': True, 'output': json.dumps(detail, ensure_ascii=False, indent=2, default=str)}
    if cmd == 'reportresolve':
        if len(parts) < 3:
            return {'success': False, 'output': command_error(raw, len(raw), 'moderation report resolve <举报ID> <accept|reject|abusive> [备注]')}
        action = parts[2].lower()
        if action not in VALID_REPORT_ACTIONS:
            return {'success': False, 'output': '处理动作必须是 accept/reject/abusive'}
        detail, error = resolve_report_entry(
            parse_int_token(parts[1], 'report_id'),
            action,
            moderation_action='none',
            admin_username='console',
            note=' '.join(parts[3:]).strip(),
        )
        if error:
            return {'success': False, 'output': error}
        admin_event('moderation', f'console report #{parts[1]} resolved action={action}')
        return {'success': True, 'output': f'已处理举报 #{parts[1]}：{action}'}
    if cmd in ('banuser', 'banaccount'):
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), '<ID|注册顺序|用户名> [秒数] [原因]')}
        duration = None
        reason_parts = parts[2:]
        if reason_parts:
            try:
                parsed_duration = int(reason_parts[0])
            except (TypeError, ValueError):
                parsed_duration = None
            if parsed_duration is not None and parsed_duration > 0:
                duration = parsed_duration
                reason_parts = reason_parts[1:]
        reason = ' '.join(reason_parts).strip()
        user, error = admin_set_user_ban(parts[1], True, reason, duration_seconds=duration)
        if error:
            return {'success': False, 'output': error}
        clear_leaderboard_cache()
        status = get_user_ban_status(user_id=user['id'])
        kicked = []
        with _lock:
            for sid, player in list(players.items()):
                if player.get('user_id') == user['id']:
                    room_id = player.get('room_id')
                    if room_id is not None and room_id in rooms:
                        admin_match_record(rooms[room_id], result='admin_ban')
                    kicked.append((sid, player.get('nickname', user['username'])))
                    remove_player_by_admin(sid)
        for sid, _nickname in kicked:
            socketio.emit('server_error', {'message': ban_error_payload(status).get('reason', '账号已被封禁')}, room=sid)
            socketio.emit('kicked', {'reason': 'account banned'}, room=sid)
        if kicked:
            broadcast_lobby()
        admin_event('admin', f"banned account {user['username']}#{user['id']}: {reason or '-'}")
        suffix = f" 原因：{reason}" if reason else ''
        duration_label = f"时长：{format_duration_zh(duration)}。" if duration else "时长：永久。"
        return {'success': True, 'output': f"已封禁账号 {user['username']} (ID:{user.get('player_id') or '-'} 注册顺序：{user['id']})。{duration_label}已踢出在线会话 {len(kicked)} 个。{suffix}"}
    if cmd in ('unbanuser', 'unbanaccount'):
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), '<ID|注册顺序|用户名>')}
        user, error = admin_set_user_ban(parts[1], False, '')
        if error:
            return {'success': False, 'output': error}
        clear_leaderboard_cache()
        admin_event('admin', f"unbanned account {user['username']}#{user['id']}")
        return {'success': True, 'output': f"已解除账号 {user['username']} (ID:{user.get('player_id') or '-'} 注册顺序：{user['id']}) 的封禁。"}
    if cmd == 'kick':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), '<sid|昵称>')}
        with _lock:
            sid = find_player_sid(parts[1])
            if not sid:
                return {'success': False, 'output': f"未找到玩家：{parts[1]}"}
            nickname = players[sid]['nickname']
            room_id = players[sid].get('room_id')
            if room_id is not None and room_id in rooms:
                admin_match_record(rooms[room_id], result='admin_kick')
            remove_player_by_admin(sid)
        socketio.emit('kicked', {'reason': 'kicked by admin'}, room=sid)
        broadcast_lobby()
        admin_event('admin', f'kicked {nickname}')
        return {'success': True, 'output': f'已踢出 {nickname}'}
    if cmd in ('afkcheck', 'afk'):
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), '<sid|昵称|all> [confirm] [原因]')}
        target = parts[1]
        extra = parts[2:]
        confirmed = any(str(part).lower() in ('confirm', '--confirm', '-y', '确认') for part in extra)
        reason_parts = [part for part in extra if str(part).lower() not in ('confirm', '--confirm', '-y', '确认')]
        reason = ' '.join(reason_parts).strip() or 'admin command'
        with _lock:
            if target.lower() in ('all', '*', 'online', 'all-online', '全部'):
                target_sids = list(players.keys())
            else:
                sid = find_player_sid(target)
                target_sids = [sid] if sid else []
            if not target_sids:
                return {'success': False, 'output': f"未找到玩家：{target}"}
            non_lobby = [
                (sid, (players.get(sid) or {}).get('nickname', '?'), (players.get(sid) or {}).get('status', '?'))
                for sid in target_sids
                if (players.get(sid) or {}).get('status') != 'lobby'
            ]
        if non_lobby and not confirmed:
            sample = ', '.join(f'{name}({status})' for _sid, name, status in non_lobby[:8])
            more = f' 等 {len(non_lobby)} 人' if len(non_lobby) > 8 else ''
            return {
                'success': False,
                'output': f'目标中包含非大厅玩家：{sample}{more}。\n若确认要发送，请追加 confirm，例如：/player afkcheck {target} confirm {reason}',
            }
        sent = []
        failed = []
        for sid in target_sids:
            result, error = send_afk_check_to_player(sid, reason=reason)
            if error:
                failed.append(f'{sid}:{error}')
            else:
                sent.append(result['nickname'])
        output = f"已向 {len(sent)} 名玩家发送挂机检测：{', '.join(sent[:12])}{'...' if len(sent) > 12 else ''}"
        if failed:
            output += f"\n失败 {len(failed)} 个：{'; '.join(failed[:5])}"
        return {'success': bool(sent), 'output': output}
    if cmd in ('mutechat', 'mute'):
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), '<sid|昵称> [秒数]')}
        seconds = parse_int_token(parts[2], 'seconds') if len(parts) > 2 else 600
        with _lock:
            sid = find_player_sid(parts[1])
            if not sid:
                return {'success': False, 'output': f"未找到玩家：{parts[1]}"}
            player = players[sid]
            nickname = player.get('nickname', '?')
            key = chat_mute_key(sid, player)
            mute_user(key, max(1, min(seconds, 86400)), 'admin command')
        admin_event('admin', f'muted chat for {nickname} {seconds}s')
        return {'success': True, 'output': f'已禁言 {nickname} {seconds} 秒。'}
    if cmd == 'skip':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), 'game action skip <房间ID>')}
        room_id = parse_int_token(parts[1], 'room_id')
        with _lock:
            if room_id not in rooms:
                return {'success': False, 'output': f'不存在房间：{room_id}'}
            room = rooms[room_id]
            e = room.engine
            if e.game_over:
                return {'success': False, 'output': '无法跳过：对局已结束'}
            if e.phase not in ('action', 'draw'):
                return {'success': False, 'output': f'当前阶段不能跳过：{zh_phase(e.phase)}'}
            e._end_player_turn(e.current_player)
            broadcast_game_state(room)
        admin_event('admin', f'skipped room {room_id}')
        return {'success': True, 'output': f'已跳过房间 {room_id} 的当前行动'}
    if cmd == 'endgame':
        if len(parts) < 3:
            return {'success': False, 'output': command_error(raw, len(raw), 'game action end <房间ID> <0|1|draw>')}
        room_id = parse_int_token(parts[1], 'room_id')
        winner_token = parts[2].lower()
        with _lock:
            if room_id not in rooms:
                return {'success': False, 'output': f'不存在房间：{room_id}'}
            room = rooms[room_id]
            e = room.engine
            if winner_token in ('draw', '-1'):
                _clear_room_pending_on_forfeit(room)
                for pidx in range(len(e.players)):
                    _force_player_death_ignoring_saves(room, pidx, e.pn(pidx), '被管理员强制结束', log=False, check_game_over=False)
                _set_room_draw(room, '管理员强制结束：平局')
            else:
                winner = parse_int_token(winner_token, 'winner')
                if room.mode == '2v2':
                    if winner not in (0, 1):
                        return {'success': False, 'output': '2v2 的胜者必须是队伍 0、队伍 1 或 draw'}
                    losing_team = 1 - winner
                    for pidx in e.teams[losing_team]:
                        _force_player_death_ignoring_saves(room, pidx, e.pn(pidx), '被管理员强制结束', log=False, check_game_over=False)
                else:
                    if winner not in (0, 1):
                        return {'success': False, 'output': '胜者必须是 0、1 或 draw'}
                    _force_player_death_ignoring_saves(room, 1 - winner, e.pn(1 - winner), '被管理员强制结束', log=False, check_game_over=False)
                e._check_game_over()
            admin_match_record(room, result='admin_endgame')
            broadcast_game_state(room)
        admin_event('admin', f'endgame room {room_id} winner={winner_token}')
        return {'success': True, 'output': f'已强制结束房间 {room_id}'}
    if cmd == 'set':
        if len(parts) < 5:
            return {'success': False, 'output': command_error(raw, len(raw), 'game player <房间> <玩家> resource set <属性> <数值>')}
        room_id = parse_int_token(parts[1], 'room_id')
        pidx = parse_int_token(parts[2], 'player_index')
        key = parts[3].lower()
        val = parse_int_token(parts[4], 'value')
        ok, output = set_room_player_attr(room_id, pidx, key, val)
        if ok:
            admin_event('admin', f'set room {room_id} player {pidx} {key}={val}')
        return {'success': ok, 'output': output}
    if cmd == 'resourceadd':
        if len(parts) < 5:
            return {'success': False, 'output': command_error(raw, len(raw), 'game player <房间> <玩家> resource add <属性> <数值>')}
        room_id = parse_int_token(parts[1], 'room_id')
        pidx = parse_int_token(parts[2], 'player_index')
        key = parts[3].lower()
        delta = parse_int_token(parts[4], 'value')
        ok, output = add_room_player_attr(room_id, pidx, key, delta)
        if ok:
            admin_event('admin', f'add room {room_id} player {pidx} {key}{delta:+d}')
        return {'success': ok, 'output': output}
    if cmd in ('givecard', 'addcard', 'give'):
        if len(parts) < 4:
            return {'success': False, 'output': command_error(raw, len(raw), 'game player <房间> <玩家> card add <卡牌ID> [数量] [tags=...] [fusion=...] [fission=...]')}
        room_id = parse_int_token(parts[1], 'room_id')
        pidx = parse_int_token(parts[2], 'player_index')
        card_id = resolve_admin_card_id(parts[3])
        if not card_id:
            return {'success': False, 'output': f'未知卡牌ID：{parts[3]}'}
        options = parse_givecard_options(parts[4:])
        ok, output = give_room_player_card(room_id, pidx, card_id, options)
        if ok:
            tag_text = ','.join(options['tags']) if options['tags'] else '-'
            admin_event(
                'admin',
                f"givecard room {room_id} player {pidx} {card_id} x{options['count']} tags={tag_text} fusion={options['fusion']} fission={options['fission']}",
            )
        return {'success': ok, 'output': output}
    if cmd in ('delcard', 'remcard', 'rmcard', 'deletecard'):
        if len(parts) < 5:
            return {'success': False, 'output': command_error(raw, len(raw), 'game player <房间> <玩家> card remove <区域> <卡牌ID|all|#序号|instance=ID> [数量|all]')}
        room_id = parse_int_token(parts[1], 'room_id')
        pidx = parse_int_token(parts[2], 'player_index')
        try:
            zone = normalize_admin_card_zone(parts[3])
            selector = parse_delcard_selector(parts[4])
            count = parse_delcard_count(parts[5:], selector)
        except ValueError as exc:
            return {'success': False, 'output': str(exc)}
        ok, output = delete_room_player_card(room_id, pidx, zone, selector, count)
        if ok:
            admin_event(
                'admin',
                f"delcard room {room_id} player {pidx} zone={zone} selector={selector.get('label')} count={count if count is not None else 'all'}",
            )
        return {'success': ok, 'output': output}
    return {'success': False, 'output': unknown_command_error(raw, cmd)}


def admin_completions(line):
    raw = line or ''
    if raw.lstrip().startswith('/'):
        leading = len(raw) - len(raw.lstrip())
        raw = raw[:leading] + raw.lstrip()[1:].lstrip()
    try:
        parts = shlex.split(raw)
    except ValueError:
        parts = raw.split()
    trailing_space = raw.endswith(' ')
    token = '' if trailing_space else (parts[-1] if parts else '')
    position = len(parts) if trailing_space else max(0, len(parts) - 1)
    def filtered(values, limit=40):
        needle = token.lower()
        seen = set()
        result = []
        for value in values:
            text_value = str(value or '')
            if not text_value or text_value in seen or not text_value.lower().startswith(needle):
                continue
            seen.add(text_value)
            result.append(text_value)
            if len(result) >= limit:
                break
        return result

    def visible_children(node):
        return [name for name, meta in (node.get('children', {}) or {}).items() if not meta.get('hidden')]

    def account_values():
        if not DB_AVAILABLE:
            return []
        try:
            rows = list_admin_users(query=token, sort='username', order='asc', limit=30).get('users', [])
        except Exception:
            return []
        values = []
        for user in rows:
            values.extend((user.get('player_id'), user.get('id'), user.get('username')))
        return values

    def online_values(include_all=False):
        values = ['all'] if include_all else []
        with _lock:
            for sid, player in players.items():
                values.extend((player.get('nickname'), sid, player.get('account_player_id')))
        return values

    def room_values():
        with _lock:
            return [str(room_id) for room_id in rooms]

    def room_player_values(room_token):
        try:
            room_id = int(room_token)
        except (TypeError, ValueError):
            return []
        with _lock:
            room = rooms.get(room_id)
            if not room:
                return []
            return [str(index) for index in range(len(getattr(room.engine, 'players', []) or []))]

    def card_values():
        needle = token.lower()
        matches = []
        for card_id, card_def in CARD_DEFS.items():
            haystacks = (
                str(card_id).lower(),
                str(getattr(card_def, 'name_cn', '') or '').lower(),
                str(getattr(card_def, 'name_en', '') or '').lower(),
            )
            if not needle or any(needle in text_value for text_value in haystacks):
                matches.append(card_id)
        return sorted(matches)

    def status_values():
        values = set(ADMIN_STATUS_ATTRS) | {'status_immune'}
        try:
            for mod in load_all_mods():
                for status in getattr(mod, 'custom_statuses', []) or []:
                    if not isinstance(status, dict):
                        continue
                    values.update(
                        str(status.get(key) or '').strip()
                        for key in ('id', 'name_cn')
                    )
        except Exception:
            pass
        return sorted(value for value in values if value)

    def mod_values():
        values = []
        for mod in sort_mods_for_display(load_all_mods()):
            info = getattr(mod, 'info', None)
            mod_id = str(getattr(info, 'id', '') or '').strip()
            values.append(mod_id if mod_id and ' ' not in mod_id else shlex.quote(mod.filename))
        return values

    public_roots = [name for name, meta in ADMIN_COMMAND_TREE.items() if not meta.get('hidden')]
    if position == 0:
        return filtered(public_roots)
    cmd = parts[0].lower() if parts else ''
    if cmd not in public_roots:
        return []

    if cmd == 'help':
        node = {'children': {name: ADMIN_COMMAND_TREE[name] for name in public_roots}}
        for path_part in parts[1:position]:
            child = (node.get('children', {}) or {}).get(path_part.lower())
            if not child or child.get('hidden'):
                return []
            node = child
        return filtered(visible_children(node))

    root = ADMIN_COMMAND_TREE[cmd]
    if position == 1:
        return filtered(visible_children(root))
    sub = parts[1].lower() if len(parts) > 1 else ''

    if cmd == 'player' and position == 2:
        return filtered(online_values(include_all=sub == 'afkcheck'))

    if cmd == 'account':
        if sub == 'achievement':
            if position == 2:
                return filtered(['list', 'grant'])
            if position == 3:
                return filtered(account_values())
            if position == 4 and len(parts) > 2 and parts[2].lower() == 'grant':
                return filtered([item.get('id') for item in list_achievement_definitions()])
        if sub == 'rating':
            if position == 2:
                return filtered(['info', 'set', 'add', 'snapshot'])
            if position == 3:
                return filtered(account_values())
            if position == 4 and len(parts) > 2 and parts[2].lower() in ('set', 'add'):
                return filtered(['season', 'total', 'both'])
        if sub == 'dew':
            if position == 2:
                return filtered(['get', 'add', 'addpaid', 'spend', 'tx'])
            if position == 3:
                return filtered(account_values())
        if sub == 'role':
            if position == 2:
                return filtered(['list', 'get', 'set', 'clear'])
            if position == 3 and len(parts) > 2 and parts[2].lower() != 'list':
                return filtered(account_values())
            if position == 4 and len(parts) > 2 and parts[2].lower() == 'set':
                return filtered(['admin', 'staff', 'contributor', 'sponsor'])
            if position >= 5 and len(parts) > 2 and parts[2].lower() == 'set':
                return filtered(['title=', 'color=bloom', 'color=guard', 'sort=', 'key=', 'direct=', 'chat='])
        if sub in ('get', 'username', 'password', 'ban', 'unban') and position == 2:
            return filtered(account_values())

    if cmd == 'game':
        room_subcommands = ('info', 'log', 'chat', 'state')
        if sub in room_subcommands and position == 2:
            return filtered(room_values())
        if sub == 'action':
            if position == 2:
                return filtered(['skip', 'end'])
            if position == 3:
                return filtered(room_values())
            if position == 4 and len(parts) > 2 and parts[2].lower() == 'end':
                return filtered(['0', '1', 'draw'])
        if sub == 'pending':
            if position == 2:
                return filtered(['get'])
            if position == 3:
                return filtered(room_values())
        if sub == 'player':
            if position == 2:
                return filtered(room_values())
            if position == 3 and len(parts) > 2:
                return filtered(room_player_values(parts[2]))
            if position == 4:
                return filtered(['info', 'resource', 'status', 'card'])
            domain = parts[4].lower() if len(parts) > 4 else ''
            if domain == 'resource':
                if position == 5:
                    return filtered(['set', 'add'])
                if position == 6:
                    return filtered(['h', 'maxh', 'e', 'maxe', 'm', 'maxm', 'armor'])
            if domain == 'status':
                if position == 5:
                    return filtered(['list', 'get', 'set', 'add', 'remove', 'clear'])
                if position == 6:
                    return filtered(status_values())
            if domain == 'card':
                action = parts[5].lower() if len(parts) > 5 else ''
                if position == 5:
                    return filtered(['list', 'add', 'remove'])
                if action == 'list' and position == 6:
                    return filtered(['hand', 'deck', 'discard', 'exile', 'equipment', 'all'])
                if action == 'add' and position == 6:
                    return card_values()[:40]
                if action == 'add' and position >= 7:
                    return filtered(['count=', 'tags=', 'fusion=', 'fission='])
                if action == 'remove' and position == 6:
                    return filtered(['hand', 'deck', 'discard', 'exile', 'equipment', 'all'])
                if action == 'remove' and position == 7:
                    special = filtered(['all', 'instance=', 'index=', '#0'])
                    return (special + card_values())[:40]

    if cmd == 'lobby' and sub == 'chat' and position == 2:
        return filtered(['50', '100', '300'])
    if cmd == 'content':
        if sub in ('disable', 'enable'):
            if position == 2:
                return filtered(['card', 'mod'])
            if position == 3 and len(parts) > 2:
                return card_values()[:40] if parts[2].lower() == 'card' else filtered(mod_values())
            if position >= 4:
                values = ['mode=all', 'mode=1v1', 'mode=2v2', 'mode=urf', 'mode=random_deck', 'mode=solo']
                if sub == 'disable':
                    values += ['duration=30m', 'duration=2h', 'duration=1d', 'duration=7d', 'duration=permanent', 'reason=', 'force']
                else:
                    values += ['mode=all-scopes']
                return filtered(values)
        if sub == 'disabled':
            if position == 2:
                return filtered(['list', 'show', 'edit'])
            action = parts[2].lower() if len(parts) > 2 else ''
            if action == 'list':
                if position == 3:
                    return filtered(['all', 'card', 'mod'])
                if position == 4:
                    return filtered(['active', 'all'])
            if action in ('show', 'edit'):
                if position == 3:
                    return filtered(['card', 'mod'])
                if position == 4 and len(parts) > 3:
                    return card_values()[:40] if parts[3].lower() == 'card' else filtered(mod_values())
                if action == 'edit' and position >= 5:
                    return filtered(['from=all', 'from=1v1', 'from=2v2', 'mode=all', 'mode=1v1', 'mode=2v2', 'mode=urf', 'mode=random_deck', 'mode=solo', 'duration=30m', 'duration=2h', 'duration=1d', 'duration=7d', 'duration=permanent', 'reason='])
    if cmd == 'moderation':
        if sub == 'mute' and position == 2:
            return filtered(online_values())
        if sub in ('ban', 'unban') and position == 2:
            return filtered(account_values())
        if sub == 'ip':
            if position == 2:
                return filtered(['list', 'ban', 'unban'])
            if position == 3 and len(parts) > 2 and parts[2].lower() == 'list':
                return filtered(['all'])
        if sub == 'report':
            if position == 2:
                return filtered(['list', 'get', 'resolve'])
            if position == 3 and len(parts) > 2 and parts[2].lower() == 'list':
                return filtered(['pending', 'accepted', 'rejected', 'abusive', 'all'])
            if position == 4 and len(parts) > 2 and parts[2].lower() == 'resolve':
                return filtered(['accept', 'reject', 'abusive'])
    if cmd == 'server':
        if sub == 'drain' and position == 2:
            return filtered(['status', 'on', 'off'])
        if sub in ('logs', 'suspicious') and position == 2:
            return filtered(['20', '50', '100'])
        if sub == 'mod':
            if position == 2:
                return filtered(['list', 'loadout'])
            if position == 3 and len(parts) > 2 and parts[2].lower() == 'loadout':
                return filtered([*room_values(), *online_values()])
        if sub == 'diagnose':
            if position == 2:
                return filtered(['server', 'room', 'player', 'stuck'])
            if position == 3 and len(parts) > 2:
                action = parts[2].lower()
                if action == 'room':
                    return filtered(room_values())
                if action == 'player':
                    return filtered([*online_values(), *account_values()])
    if cmd == 'data':
        if sub == 'draftstats' and position == 2:
            return filtered(['1v1', '2v2'])
        if sub in ('rebuildstats', 'dewbackfill', 'achievementbackfill') and position == 2:
            return filtered(['preview', 'confirm'] if sub != 'rebuildstats' else ['confirm'])
        if sub == 'rating':
            if position == 2:
                return filtered(['season', 'list', 'rebuild'])
            if position == 3 and len(parts) > 2 and parts[2].lower() == 'list':
                return filtered(['season', 'total'])
            if position == 3 and len(parts) > 2 and parts[2].lower() == 'rebuild':
                return filtered(['preview', 'confirm'])
    return []


def remove_player_by_admin(sid):
    if sid not in players:
        return None
    mark_player_session_last_seen_locked(players[sid], exclude_sid=sid)
    nickname = players[sid]['nickname']
    room_id = players[sid].get('room_id')
    spectating_room = players[sid].get('spectating_room')
    if room_id is not None and room_id in rooms:
        room = rooms[room_id]
        for other_sid in room.player_sids:
            if other_sid != sid and other_sid in players:
                socketio.emit('opponent_disconnected', {}, room=other_sid)
                players[other_sid]['room_id'] = None
                players[other_sid]['status'] = 'lobby'
        for spid in list(room.spectators):
            if spid in players:
                players[spid]['spectating_room'] = None
                players[spid]['status'] = 'lobby'
                socketio.emit('spectate_leave', {}, room=spid)
        for t in room.reconnect_timers.values():
            t.cancel()
        _cancel_game_over_cleanup_timer(room)
        del rooms[room_id]
    elif spectating_room is not None and spectating_room in rooms:
        room = rooms[spectating_room]
        if sid in room.spectators:
            room.spectators.remove(sid)
    for inv_sid, target_sid in list(invites.items()):
        if inv_sid == sid or target_sid == sid:
            del invites[inv_sid]
    if sid in teams:
        team = teams[sid]
        for member_sid in list(team.get('members', [])):
            if member_sid in teams:
                del teams[member_sid]
            if member_sid in players and member_sid != sid:
                socketio.emit('team_disbanded', {}, room=member_sid)
    del players[sid]
    return nickname


def give_room_player_card(room_id, pidx, card_id, options):
    with _lock:
        if room_id not in rooms:
            return False, f'不存在房间：{room_id}'
        room = rooms[room_id]
        e = room.engine
        if pidx < 0 or pidx >= len(e.players):
            return False, f'玩家序号必须在 0-{len(e.players) - 1} 之间'
        ps = e.players[pidx]
        count = int(options.get('count', 1))
        created = []
        for _ in range(max(1, min(count, 50))):
            card = make_admin_card_instance(card_id, options)
            ps.add_to_hand(card)
            created.append(card)
        broadcast_game_state(room)
    layers = []
    if int(options.get('fusion', 1) or 1) > 1:
        layers.append(f"聚变{options['fusion']}")
    if int(options.get('fission', 1) or 1) > 1:
        layers.append(f"裂变{options['fission']}")
    if options.get('tags'):
        layers.append(f"标签={','.join(options['tags'])}")
    detail = f"（{'；'.join(layers)}）" if layers else ''
    card_name = CARD_DEFS[card_id].name_cn if card_id in CARD_DEFS else card_id
    return True, f'已向房间 {room_id} 的玩家 {pidx} 加入 {len(created)} 张 {card_name}{detail}'


def delete_room_player_card(room_id, pidx, zone, selector, count):
    with _lock:
        if room_id not in rooms:
            return False, f'不存在房间：{room_id}'
        room = rooms[room_id]
        e = room.engine
        if pidx < 0 or pidx >= len(e.players):
            return False, f'玩家序号必须在 0-{len(e.players) - 1} 之间'
        if selector.get('type') == 'index' and zone == 'all':
            return False, '按序号删除时不能使用 all 区域，请指定 hand/deck/discard/exile/equipment'
        ps = e.players[pidx]
        zones = ['hand', 'deck', 'discard', 'exile', 'equipment'] if zone == 'all' else [zone]
        removed = []
        remaining_quota = count
        for zone_name in zones:
            items = _admin_zone_items(ps, zone_name)
            if selector.get('type') == 'index':
                idx = int(selector.get('value'))
                if idx < 0 or idx >= len(items):
                    return False, f'{zone_name} 序号必须在 0-{len(items) - 1} 之间'
                item = items.pop(idx)
                card = _admin_card_from_item(item)
                removed.append((zone_name, card))
                break
            kept = []
            for item in items:
                if _admin_selector_matches(item, selector) and (remaining_quota is None or remaining_quota > 0):
                    card = _admin_card_from_item(item)
                    removed.append((zone_name, card))
                    if remaining_quota is not None:
                        remaining_quota -= 1
                    continue
                kept.append(item)
            items[:] = kept
            if remaining_quota == 0:
                break
        if not removed:
            return False, f'未找到要删除的卡：区域={zone} 选择器={selector.get("label")}'
        record_room_replay_action(room, 'admin_delete_card', None, {
            'player_id': pidx,
            'zone': zone,
            'selector': selector,
            'count': count if count is not None else 'all',
            'removed': [
                {'zone': zone_name, 'def_id': getattr(card, 'def_id', ''), 'instance_id': getattr(card, 'instance_id', None)}
                for zone_name, card in removed
            ],
        })
        broadcast_game_state(room)
    grouped = {}
    for zone_name, card in removed:
        grouped.setdefault(zone_name, []).append(_admin_card_label(card))
    detail = '；'.join(f'{zone_name}: {", ".join(labels[:8])}{"" if len(labels) <= 8 else " ..."}' for zone_name, labels in grouped.items())
    return True, f'已从房间 {room_id} 的玩家 {pidx} 删除 {len(removed)} 张卡。{detail}'


def set_room_player_attr(room_id, pidx, key, val):
    attr = ADMIN_RESOURCE_ATTRS.get(key)
    if not attr:
        return False, f'未知属性：{key}'
    with _lock:
        if room_id not in rooms:
            return False, f'不存在房间：{room_id}'
        room = rooms[room_id]
        e = room.engine
        if pidx < 0 or pidx >= len(e.players):
            return False, f'玩家序号必须在 0-{len(e.players) - 1} 之间'
        ps = e.players[pidx]
        if not hasattr(ps, attr):
            return False, f'玩家没有属性：{attr}'
        if attr == 'health':
            if val <= 0:
                _force_player_death_ignoring_saves(room, pidx, e.pn(pidx), '被管理员强制设为0H', log=True)
            else:
                setattr(ps, attr, val)
                ps.max_health = max(ps.max_health, val)
                e._check_game_over()
        elif attr == 'elixir':
            setattr(ps, attr, val)
            ps.max_elixir = max(ps.max_elixir, val)
        elif attr == 'magic':
            setattr(ps, attr, val)
            ps.max_magic = max(ps.max_magic, val)
        elif attr == 'max_health':
            ps.max_health = max(1, val)
            ps.base_max_health = ps.max_health
            ps.health = min(ps.health, ps.max_health)
        elif attr == 'max_elixir':
            ps.max_elixir = max(0, val)
            ps.elixir = min(ps.elixir, ps.max_elixir)
        elif attr == 'max_magic':
            ps.max_magic = max(0, val)
            ps.magic = min(ps.magic, ps.max_magic)
        else:
            setattr(ps, attr, max(0, val))
        broadcast_game_state(room)
    return True, f'已设置房间 {room_id} 的玩家 {pidx}：{key}={val}'


def add_room_player_attr(room_id, pidx, key, delta):
    attr = ADMIN_RESOURCE_ATTRS.get(key)
    if not attr:
        return False, f'未知属性：{key}'
    with _lock:
        room, ps, error = _admin_room_player(room_id, pidx)
        if error:
            return False, error
        current = int(getattr(ps, attr, 0) or 0)
    return set_room_player_attr(room_id, pidx, key, current + int(delta))


def _build_lobby_update_payloads_locked():
    scope_payload_cache = {}

    def mode_counts_for_scope(beta_mode):
        counts = {mode: 0 for mode in PVP_MODES}
        excluded_statuses = {'solo', 'tutorial', 'spectating'}
        for player in players.values():
            if bool(player.get('beta_mode', False)) != bool(beta_mode):
                continue
            if player.get('status') in excluded_statuses:
                continue
            mode = player.get('mode', '1v1')
            if mode in counts:
                counts[mode] += 1
        return counts

    def team_list_for_scope(beta_mode):
        team_list = []
        seen_teams = set()
        for team in teams.values():
            team_id = id(team)
            if team_id in seen_teams:
                continue
            seen_teams.add(team_id)
            member_sids = [ms for ms in team['members'] if ms in players]
            if not member_sids:
                continue
            if any(bool(players[ms].get('beta_mode')) != bool(beta_mode) for ms in member_sids):
                continue
            member_infos = [public_player_info(ms, players[ms]) for ms in member_sids]
            team_list.append({
                'leader': team['leader'],
                'members': [info['nickname'] for info in member_infos],
                'member_infos': member_infos,
                'member_sids': member_sids,
                'has_admin_player': any(info.get('is_admin_player') for info in member_infos),
                'special_role_sort': min([info.get('special_role_sort', 99) for info in member_infos] or [99]),
            })
        team_list.sort(key=lambda item: (
            item.get('special_role_sort', 99),
            ' '.join(item.get('members') or []).lower()
        ))
        return team_list

    def payload_base_for_scope(beta_mode):
        key = runtime_scope_key(beta_mode)
        if key not in scope_payload_cache:
            scope_payload_cache[key] = {
                'players': get_lobby_list(beta_mode),
                'ongoing_games': get_ongoing_games(beta_mode),
                'teams': team_list_for_scope(beta_mode),
                'mode_counts': mode_counts_for_scope(beta_mode),
                'chat_history': _lobby_chat_history_payload_locked(LOBBY_CHAT_VISIBLE_LIMIT, beta_mode),
            }
        return scope_payload_cache[key]

    payloads = []
    for sid, p in players.items():
        if p['status'] == 'lobby':
            base = copy.deepcopy(payload_base_for_scope(p.get('beta_mode', False)))
            payloads.append((sid, {
                'players': base['players'],
                'your_sid': sid,
                'ongoing_games': base['ongoing_games'],
                'teams': base['teams'],
                'mode_counts': base['mode_counts'],
                'your_team': teams[sid]['members'] if sid in teams else None,
                'your_team_leader': teams[sid]['leader'] if sid in teams else None,
                'your_mode': p.get('mode', '1v1'),
                'beta_mode': bool(p.get('beta_mode', False)),
                'chat_history': base['chat_history'],
            }))
    return payloads


def _broadcast_lobby_worker():
    global _LOBBY_BROADCAST_PENDING, _LOBBY_BROADCAST_DIRTY, LAST_LOBBY_UPDATE_AT
    try:
        while True:
            if _LOBBY_BROADCAST_DELAY_SECONDS > 0:
                try:
                    socketio.sleep(_LOBBY_BROADCAST_DELAY_SECONDS)
                except Exception:
                    time.sleep(_LOBBY_BROADCAST_DELAY_SECONDS)
            try:
                started = time.perf_counter()
                with _lock:
                    payloads = _build_lobby_update_payloads_locked()
                for sid, payload in payloads:
                    socketio.emit('lobby_update', payload, room=sid)
                LAST_LOBBY_UPDATE_AT = iso_now()
                record_socket_broadcast(None, (time.perf_counter() - started) * 1000, recipients=len(payloads))
            except Exception as exc:
                admin_event('error', f'lobby broadcast failed: {exc}')
            with _LOBBY_BROADCAST_LOCK:
                if _LOBBY_BROADCAST_DIRTY:
                    _LOBBY_BROADCAST_DIRTY = False
                    continue
                _LOBBY_BROADCAST_PENDING = False
                break
    except Exception as exc:
        # Ensure _LOBBY_BROADCAST_PENDING is reset even on unexpected errors
        admin_event('error', f'lobby broadcast worker crashed: {exc}')
        with _LOBBY_BROADCAST_LOCK:
            _LOBBY_BROADCAST_PENDING = False


def broadcast_lobby():
    global _LOBBY_BROADCAST_PENDING, _LOBBY_BROADCAST_DIRTY
    with _LOBBY_BROADCAST_LOCK:
        if _LOBBY_BROADCAST_PENDING:
            _LOBBY_BROADCAST_DIRTY = True
            return
        _LOBBY_BROADCAST_PENDING = True
        _LOBBY_BROADCAST_DIRTY = False
    try:
        socketio.start_background_task(_broadcast_lobby_worker)
    except Exception:
        threading.Thread(target=_broadcast_lobby_worker, name='lobby-broadcast', daemon=True).start()


def send_draft_state(room, pidx):
    sid = room.player_sids[pidx]
    if sid not in players:
        return
    engine = room.engine
    options = engine.draft_options[pidx]
    picks = engine.draft_picks[pidx]
    rerolls = engine.draft_rerolls[pidx]
    total_rounds = engine.draft_target_count(pidx) if hasattr(engine, 'draft_target_count') else DECK_SIZE
    others_picks_count = {}
    others_status = {}
    others_total_rounds = {}
    if room.mode == '2v2':
        for i in range(4):
            if i != pidx:
                others_picks_count[i] = len(engine.draft_picks[i])
                others_status[i] = engine.get_player_status(i)
                others_total_rounds[i] = engine.draft_target_count(i) if hasattr(engine, 'draft_target_count') else DECK_SIZE
    else:
        opp_pidx = 1 - pidx
        others_picks_count[opp_pidx] = len(engine.draft_picks[opp_pidx])
        others_status[opp_pidx] = engine.get_player_status(opp_pidx)
        others_total_rounds[opp_pidx] = engine.draft_target_count(opp_pidx) if hasattr(engine, 'draft_target_count') else DECK_SIZE
    payload = {
        'options': [c.to_dict() for c in options],
        'picks': picks,
        'setup_preview_cards': engine.preview_setup_cards(pidx) if hasattr(engine, 'preview_setup_cards') else [],
        'rerolls': rerolls,
        'round': len(picks) + 1,
        'total_rounds': total_rounds,
        'others_picks_count': others_picks_count,
        'others_status': others_status,
        'others_total_rounds': others_total_rounds,
        'opponent_picks_count': next(iter(others_picks_count.values()), 0) if room.mode != '2v2' else 0,
        'mode': room.mode,
        'player_names': engine.player_names,
        'room_id': room.room_id,
        'match_key': room_match_key(room),
        'your_id': pidx,
        'enemy_ids': engine.get_all_enemies(pidx) if room.mode == '2v2' and hasattr(engine, 'get_all_enemies') else ([1 - pidx] if pidx in (0, 1) else []),
        'player_skins': [player_skin_for_sid(psid, room) for psid in room.player_sids],
        'player_skin_looks': [player_skin_look_for_sid(psid, room) for psid in room.player_sids],
        'selected_opening_events': _selected_opening_event_names(engine),
        'room_chat_history': room_chat_history_for_sid(room, sid),
        **_pregame_timer_payload(room, pidx, 'drafting'),
    }
    payload.update(_watched_pregame_timer_payload(room, pidx))
    payload.update(instance_payload())
    payload.update(room_mod_payload(room))
    payload.update(_room_disconnect_state_payload(room, sid))
    socketio.emit('draft_state', payload, room=sid)


def send_pregame_status_update(room, targets=None):
    """Update draft/setup progress without rebuilding another player's UI."""
    engine = room.engine
    if targets is None:
        targets = range(len(room.player_sids))
    for pidx in targets:
        if pidx < 0 or pidx >= len(room.player_sids):
            continue
        sid = room.player_sids[pidx]
        if sid not in players:
            continue
        total_rounds = engine.draft_target_count(pidx) if hasattr(engine, 'draft_target_count') else DECK_SIZE
        others_picks_count = {}
        others_status = {}
        others_total_rounds = {}
        if room.mode == '2v2':
            for i in range(4):
                if i != pidx:
                    others_picks_count[i] = len(engine.draft_picks[i])
                    others_status[i] = engine.get_player_status(i)
                    others_total_rounds[i] = engine.draft_target_count(i) if hasattr(engine, 'draft_target_count') else DECK_SIZE
        else:
            opp_pidx = 1 - pidx
            others_picks_count[opp_pidx] = len(engine.draft_picks[opp_pidx])
            others_status[opp_pidx] = engine.get_player_status(opp_pidx)
            others_total_rounds[opp_pidx] = engine.draft_target_count(opp_pidx) if hasattr(engine, 'draft_target_count') else DECK_SIZE
        payload = {
            'round': len(engine.draft_picks[pidx]) + 1,
            'total_rounds': total_rounds,
            'others_picks_count': others_picks_count,
            'others_status': others_status,
            'others_total_rounds': others_total_rounds,
            'opponent_picks_count': next(iter(others_picks_count.values()), 0) if room.mode != '2v2' else 0,
            'mode': room.mode,
            'player_names': engine.player_names,
            'room_id': room.room_id,
            'match_key': room_match_key(room),
            'your_id': pidx,
            'your_status': engine.get_player_status(pidx),
            'selected_opening_events': _selected_opening_event_names(engine),
            'room_chat_history': room_chat_history_for_sid(room, sid),
            **_pregame_timer_payload(room, pidx, engine.get_player_status(pidx)),
        }
        payload.update(_watched_pregame_timer_payload(room, pidx))
        payload.update(instance_payload())
        payload.update(_room_disconnect_state_payload(room, sid))
        socketio.emit('pregame_status_update', payload, room=sid)


def _start_socket_background_task(fn, *args, **kwargs):
    try:
        socketio.start_background_task(fn, *args, **kwargs)
    except Exception:
        threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True).start()


def schedule_pregame_state(room, pidx, allow_sub_choice=False):
    _start_socket_background_task(send_pregame_state, room, pidx, allow_sub_choice=allow_sub_choice)


def schedule_pregame_status_update(room, targets=None):
    _start_socket_background_task(send_pregame_status_update, room, targets=targets)


def schedule_event_state(room, pidx):
    _start_socket_background_task(send_event_state, room, pidx)


def schedule_start_game(room):
    if getattr(room, '_start_game_scheduled', False):
        return
    room._start_game_scheduled = True
    _start_socket_background_task(start_game, room)


def send_event_state(room, pidx):
    sid = room.player_sids[pidx]
    if sid not in players:
        return
    engine = room.engine
    events = []
    for event in engine.opening_event_options[pidx]:
        payload = dict(event) if isinstance(event, dict) else event
        event_id = payload.get('id') if isinstance(payload, dict) else None
        if isinstance(payload, dict) and str(event_id).isdigit() and int(event_id) in GameEngine.OPENING_EVENTS:
            payload = event_text(int(event_id), payload)
        events.append(payload)
    others_selected = {}
    if room.mode == '2v2':
        for i in range(4):
            if i != pidx:
                others_selected[i] = engine.opening_event_picks[i] is not None
    else:
        opp_idx = 1 - pidx
        others_selected[opp_idx] = engine.opening_event_picks[opp_idx] is not None
    payload = {
        'events': events,
        'others_selected': others_selected,
        'my_pick': engine.opening_event_picks[pidx],
        'magic_options': engine.opening_event_magic_options[pidx],
        'rerolls': engine.draft_rerolls[pidx],
        'draft_picks': engine.draft_picks[pidx],
        'mode': room.mode,
        'player_names': engine.player_names,
        'room_id': room.room_id,
        'match_key': room_match_key(room),
        'your_id': pidx,
        'enemy_ids': engine.get_all_enemies(pidx) if room.mode == '2v2' and hasattr(engine, 'get_all_enemies') else ([1 - pidx] if pidx in (0, 1) else []),
        'player_skins': [player_skin_for_sid(psid, room) for psid in room.player_sids],
        'player_skin_looks': [player_skin_look_for_sid(psid, room) for psid in room.player_sids],
        'selected_opening_events': _selected_opening_event_names(engine),
        'room_chat_history': room_chat_history_for_sid(room, sid),
        **_pregame_timer_payload(room, pidx, 'event_select'),
    }
    payload.update(_watched_pregame_timer_payload(room, pidx))
    payload.update(instance_payload())
    payload.update(room_mod_payload(room))
    payload.update(_room_disconnect_state_payload(room, sid))
    socketio.emit('event_select', payload, room=sid)


def _opening_event_by_id(engine, event_id):
    if event_id is None:
        return None
    text_id = str(event_id)
    for options in getattr(engine, 'opening_event_options', []) or []:
        for ev in options or []:
            if ev and str(ev.get('id')) == text_id:
                payload = dict(ev)
                if text_id.isdigit() and int(text_id) in GameEngine.OPENING_EVENTS:
                    payload = event_text(int(text_id), payload)
                return payload
    base = getattr(engine, 'OPENING_EVENTS', {}).get(int(event_id)) if str(event_id).isdigit() else None
    return event_text(int(event_id), dict(base)) if base else None


def send_event_reveal_state(room, pidx):
    sid = room.player_sids[pidx]
    if sid not in players:
        return
    engine = room.engine
    picks = []
    for idx, picked_id in enumerate(engine.opening_event_picks):
        ev = _opening_event_by_id(engine, picked_id)
        picks.append({
            'player_id': idx,
            'player_name': engine.player_names[idx] if idx < len(engine.player_names) else f'P{idx + 1}',
            'event': ev,
            'ready': bool(getattr(engine, 'player_draft_started', [False] * len(engine.opening_event_picks))[idx]),
        })
    payload = {
        'picks': picks,
        'my_pick': engine.opening_event_picks[pidx],
        'my_ready': bool(getattr(engine, 'player_draft_started', [False] * len(engine.opening_event_picks))[pidx]),
        'mode': room.mode,
        'player_names': engine.player_names,
        'room_id': room.room_id,
        'match_key': room_match_key(room),
        'your_id': pidx,
        'enemy_ids': engine.get_all_enemies(pidx) if room.mode == '2v2' and hasattr(engine, 'get_all_enemies') else ([1 - pidx] if pidx in (0, 1) else []),
        'room_chat_history': room_chat_history_for_sid(room, sid),
    }
    payload.update(_watched_pregame_timer_payload(room, pidx))
    payload.update(instance_payload())
    payload.update(room_mod_payload(room))
    payload.update(_room_disconnect_state_payload(room, sid))
    socketio.emit('event_reveal', payload, room=sid)


ROOM_STATE_BROADCAST_DELAY_SECONDS = _env_float('GTN_ROOM_STATE_BROADCAST_DELAY_SECONDS', 0.06)


def room_spectator_count(room):
    try:
        return sum(1 for sid in (getattr(room, 'spectators', []) or []) if sid in players)
    except Exception:
        return len(getattr(room, 'spectators', []) or [])


def _broadcast_game_state_now(room):
    _broadcast_started = time.perf_counter()
    _broadcast_recipients = 0
    _sync_disconnected_revived_players(room)
    _sync_room_action_timer_after_state_change(room)
    if room.engine.game_over and not getattr(room, '_history_recorded', False):
        admin_match_record(room)
        room._history_recorded = True
        admin_event('game', f'room {room.room_id} finished')
    elif not room.engine.game_over:
        check_live_achievements(room)
    for pidx, sid in enumerate(room.player_sids):
        if sid not in players:
            continue
        state = room.engine.get_public_state(pidx)
        state['your_id'] = pidx
        state['mode'] = room.mode
        state['room_id'] = room.room_id
        state['match_key'] = room_match_key(room)
        state['spectator_count'] = room_spectator_count(room)
        state['room_chat_history'] = room_chat_history_for_sid(room, sid)
        state.update(instance_payload())
        state.update(_room_timer_payload(room))
        state.update(room_mod_payload(room))
        if room.engine.phase == 'game_over' or room.engine.game_over:
            state['match_summary'] = getattr(room, '_match_summary', None)
        if room.engine.phase == 'game_over':
            state.update(room_rematch_payload(room, sid))
        _mark_player_defeated_state(room, pidx, state)
        if room.mode == '2v2':
            engine = room.engine
            teammate_id = engine.get_teammate(pidx)
            enemy_ids = engine.get_all_enemies(pidx)
            state['your_name'] = room_player_nickname(room, sid)
            state['your_is_admin_player'] = player_is_admin(sid, room)
            state['your_special'] = player_special_fields(sid, room)
            if teammate_id >= 0 and teammate_id < len(room.player_sids):
                tm_sid = room.player_sids[teammate_id]
                state['teammate_name'] = room_player_nickname(room, tm_sid)
                state['teammate_is_admin_player'] = player_is_admin(tm_sid, room)
                state['teammate_special'] = player_special_fields(tm_sid, room)
            state['opponent_names'] = []
            state['opponent_admin_flags'] = []
            state['opponent_specials'] = []
            for eid in enemy_ids:
                if eid < len(room.player_sids):
                    e_sid = room.player_sids[eid]
                    state['opponent_names'].append(room_player_nickname(room, e_sid))
                    state['opponent_admin_flags'].append(player_is_admin(e_sid, room))
                    state['opponent_specials'].append(player_special_fields(e_sid, room))
        else:
            opp_pidx = 1 - pidx
            opp_sid = room.player_sids[opp_pidx]
            state['enemy_ids'] = [opp_pidx]
            state['opponent_name'] = room_player_nickname(room, opp_sid)
            state['opponent_is_admin_player'] = player_is_admin(opp_sid, room)
            state['opponent_special'] = player_special_fields(opp_sid, room)
            state['opponent_names'] = [state['opponent_name']]
            state['opponent_admin_flags'] = [state['opponent_is_admin_player']]
            state['opponent_specials'] = [state['opponent_special']]
            state['your_name'] = room_player_nickname(room, sid)
            state['your_is_admin_player'] = player_is_admin(sid, room)
            state['your_special'] = player_special_fields(sid, room)
        inject_player_skins(state, room, pidx)
        socketio.emit('state_update', state, room=sid)
        _broadcast_recipients += 1
    emit_pending_choice_request(room)
    broadcast_spectate_state(room)
    _broadcast_recipients += len(getattr(room, 'spectators', []) or [])
    record_socket_broadcast(room, (time.perf_counter() - _broadcast_started) * 1000, _broadcast_recipients)
    if room.engine.game_over:
        _schedule_game_over_cleanup(room)


def _room_state_broadcast_worker(room):
    try:
        while True:
            if ROOM_STATE_BROADCAST_DELAY_SECONDS > 0:
                try:
                    socketio.sleep(ROOM_STATE_BROADCAST_DELAY_SECONDS)
                except Exception:
                    time.sleep(ROOM_STATE_BROADCAST_DELAY_SECONDS)
            try:
                with _lock:
                    if rooms.get(getattr(room, 'room_id', None)) is not room:
                        return
                action_lock = getattr(room, 'action_lock', None)
                acquired_action_lock = False
                if action_lock is not None:
                    acquired_action_lock = action_lock.acquire(blocking=False)
                    if not acquired_action_lock:
                        with room.state_broadcast_lock:
                            room.state_broadcast_dirty = True
                        continue
                try:
                    _broadcast_game_state_now(room)
                finally:
                    if acquired_action_lock:
                        action_lock.release()
                if not getattr(room, '_live_achievement_checking', False):
                    room._live_achievement_checking = True
                    try:
                        check_live_achievements(room)
                    finally:
                        room._live_achievement_checking = False
            except Exception as exc:
                admin_event('error', f'room state broadcast failed room={getattr(room, "room_id", "?")}: {exc}', room_id=getattr(room, 'room_id', None))
            with room.state_broadcast_lock:
                if room.state_broadcast_dirty:
                    room.state_broadcast_dirty = False
                    continue
                room.state_broadcast_pending = False
                break
    except Exception as exc:
        admin_event('error', f'room state broadcast worker crashed room={getattr(room, "room_id", "?")}: {exc}', room_id=getattr(room, 'room_id', None))
        try:
            with room.state_broadcast_lock:
                room.state_broadcast_pending = False
        except Exception:
            pass


def broadcast_game_state(room):
    if room is None:
        return
    lock = getattr(room, 'state_broadcast_lock', None)
    if lock is None:
        room.state_broadcast_lock = threading.Lock()
        room.state_broadcast_pending = False
        room.state_broadcast_dirty = False
        lock = room.state_broadcast_lock
    with lock:
        if getattr(room, 'state_broadcast_pending', False):
            room.state_broadcast_dirty = True
            return
        room.state_broadcast_pending = True
        room.state_broadcast_dirty = False
    try:
        socketio.start_background_task(_room_state_broadcast_worker, room)
    except Exception:
        threading.Thread(target=_room_state_broadcast_worker, args=(room,), name=f'room-state-broadcast-{getattr(room, "room_id", "?")}', daemon=True).start()


def _schedule_game_over_cleanup(room):
    if getattr(room, '_game_over_cleanup_timer', None) is not None:
        return
    def _cleanup():
        pending_emits = []
        try:
            with _lock:
                rid = room.room_id
                if rid not in rooms:
                    return
                for psid in room.player_sids:
                    if psid in players:
                        players[psid]['room_id'] = None
                        players[psid]['status'] = 'lobby'
                        pending_emits.append(('game_phase', {'phase': 'lobby'}, psid))
                for spid in list(room.spectators):
                    if spid in players:
                        players[spid]['spectating_room'] = None
                        players[spid]['spectate_perspective'] = 0
                        pending_emits.append(('spectate_leave', {}, spid))
                rooms.pop(rid, None)
                admin_event('game', f'room {rid} auto-cleaned after game_over timeout')
        except Exception as exc:
            admin_event('error', f'game_over_cleanup error: {exc}')
        for emit_item in pending_emits:
            try:
                socketio.emit(emit_item[0], emit_item[1], room=emit_item[2])
            except Exception as exc:
                admin_event('error', f'game_over_cleanup emit error: {exc}')
        broadcast_lobby()
    timer = threading.Timer(float(GAME_OVER_CLEANUP_SECONDS), _cleanup)
    timer.daemon = True
    timer.start()
    room._game_over_cleanup_timer = timer


def _cancel_game_over_cleanup_timer(room):
    timer = getattr(room, '_game_over_cleanup_timer', None)
    if timer is not None:
        timer.cancel()
        room._game_over_cleanup_timer = None


def send_game_state_to(room, pidx):
    sid = room.player_sids[pidx]
    if sid not in players:
        return
    phase = room.engine.phase
    if phase in ('event_select', 'event_reveal', 'draft'):
        send_pregame_state(room, pidx, allow_sub_choice=True)
    else:
        emit_room_game_phase(room, sid, phase)
        _sync_disconnected_revived_players(room)
        _sync_room_action_timer_after_state_change(room)
        state = room.engine.get_public_state(pidx)
        state['your_id'] = pidx
        state['mode'] = room.mode
        state['room_id'] = room.room_id
        state['match_key'] = room_match_key(room)
        state['spectator_count'] = room_spectator_count(room)
        state['room_chat_history'] = room_chat_history_for_sid(room, sid)
        state.update(_room_timer_payload(room))
        state.update(room_mod_payload(room))
        state.update(_room_disconnect_state_payload(room, sid))
        if room.engine.phase == 'game_over':
            state.update(room_rematch_payload(room, sid))
        _mark_player_defeated_state(room, pidx, state)
        if room.mode == '2v2':
            engine = room.engine
            teammate_id = engine.get_teammate(pidx)
            enemy_ids = engine.get_all_enemies(pidx)
            state['your_name'] = room_player_nickname(room, sid)
            state['your_is_admin_player'] = player_is_admin(sid, room)
            state['your_special'] = player_special_fields(sid, room)
            if teammate_id >= 0 and teammate_id < len(room.player_sids):
                tm_sid = room.player_sids[teammate_id]
                state['teammate_name'] = room_player_nickname(room, tm_sid)
                state['teammate_is_admin_player'] = player_is_admin(tm_sid, room)
                state['teammate_special'] = player_special_fields(tm_sid, room)
            state['opponent_names'] = []
            state['opponent_admin_flags'] = []
            state['opponent_specials'] = []
            for eid in enemy_ids:
                if eid < len(room.player_sids):
                    e_sid = room.player_sids[eid]
                    state['opponent_names'].append(room_player_nickname(room, e_sid))
                    state['opponent_admin_flags'].append(player_is_admin(e_sid, room))
                    state['opponent_specials'].append(player_special_fields(e_sid, room))
        else:
            opp_pidx = 1 - pidx
            opp_sid = room.player_sids[opp_pidx]
            state['opponent_name'] = room_player_nickname(room, opp_sid)
            state['opponent_is_admin_player'] = player_is_admin(opp_sid, room)
            state['opponent_special'] = player_special_fields(opp_sid, room)
            state['your_name'] = room_player_nickname(room, sid)
            state['your_is_admin_player'] = player_is_admin(sid, room)
            state['your_special'] = player_special_fields(sid, room)
        inject_player_skins(state, room, pidx)
        socketio.emit('state_update', state, room=sid)
        emit_pending_choice_request(room)


def emit_rematch_state(room):
    for psid in room.player_sids:
        if psid not in players:
            continue
        payload = room_rematch_payload(room, psid)
        payload.update({
            'votes': payload['rematch_votes'],
            'total': payload['rematch_total'],
            'has_voted': payload['rematch_has_voted'],
            'mode': room.mode,
        })
        socketio.emit('rematch_state', payload, room=psid)


def start_event_select(room):
    room.pregame_deadlines = {}
    for pi in range(len(room.player_sids)):
        send_event_state(room, pi)


def send_event_sub_choice_state(room, pidx):
    """Send sub-choice state for opening events after draft."""
    sid = room.player_sids[pidx]
    if sid not in players:
        return
    engine = room.engine
    event_id = engine.opening_event_picks[pidx]
    needs_sub = engine.needs_sub_choice(pidx)
    # Find the slot index of the selected event to get its magic_options
    selected_slot = None
    magic_options_for_event = []
    if event_id is not None:
        for j, ev in enumerate(engine.opening_event_options[pidx]):
            if ev and str(ev.get('id')) == str(event_id):
                selected_slot = j
                break
        if selected_slot is not None:
            magic_options_for_event = engine.opening_event_magic_options[pidx][selected_slot]
    payload = {
        'event_id': event_id,
        'needs_sub_choice': needs_sub,
        'draft_picks': engine.draft_picks[pidx],
        'fated_draw_pool': [CardInstance(def_id=def_id).to_dict() for def_id in engine.fated_draw_pool_defs()] if str(event_id) == '5' else [],
        'magic_options': magic_options_for_event,
        'mode': room.mode,
        'player_names': engine.player_names,
        'room_id': room.room_id,
        'match_key': room_match_key(room),
        'your_id': pidx,
        'selected_opening_events': _selected_opening_event_names(engine),
        'room_chat_history': room_chat_history_for_sid(room, sid),
        **_pregame_timer_payload(room, pidx, 'sub_choice'),
    }
    payload.update(_watched_pregame_timer_payload(room, pidx))
    payload.update(instance_payload())
    payload.update(room_mod_payload(room))
    payload.update(_room_disconnect_state_payload(room, sid))
    socketio.emit('event_sub_choice', payload, room=sid)


def send_pregame_state(room, pidx, allow_sub_choice=False):
    """Send the correct pre-game UI for one player.

    Opening setup now allows players in the same room to be in different
    states: one can still be choosing setup while another is already drafting.
    Do not broadcast draft_state blindly, or the setup UI disappears.
    """
    sid = room.player_sids[pidx]
    if sid not in players:
        return
    engine = room.engine
    if getattr(engine, 'phase', None) not in ('event_select', 'event_reveal', 'draft'):
        return
    status = engine.get_player_status(pidx)
    if status == 'event_select':
        emit_room_game_phase(room, sid, 'event_select')
        send_event_state(room, pidx)
        return
    if status == 'event_reveal':
        if not all(pick is not None for pick in getattr(engine, 'opening_event_picks', [])):
            emit_room_game_phase(room, sid, 'event_select')
            send_event_state(room, pidx)
            return
        emit_room_game_phase(room, sid, 'event_reveal')
        send_event_reveal_state(room, pidx)
        return
    if status == 'sub_choice':
        emit_room_game_phase(room, sid, 'draft')
        send_event_sub_choice_state(room, pidx)
        return
    emit_room_game_phase(room, sid, 'draft')
    send_draft_state(room, pidx)


@socketio.on('request_pregame_state')
@measure_socket_action('request_pregame_state')
def on_request_pregame_state(data=None):
    sid = request.sid
    data = socket_guard('request_pregame_state', data, require_player=True, allow_empty=True)
    if data is None:
        return
    with _lock:
        player = players.get(sid)
        if not player:
            return
        room_id = player.get('room_id')
        room = rooms.get(room_id)
        if room is None:
            return
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = getattr(room, 'engine', None)
        if engine is None or getattr(engine, 'phase', None) not in ('event_select', 'event_reveal', 'draft'):
            return
    schedule_pregame_state(room, pidx, allow_sub_choice=True)


@socketio.on('request_game_state')
@measure_socket_action('request_game_state')
def on_request_game_state(data=None):
    sid = request.sid
    data = socket_guard('request_game_state', data, require_player=True, allow_empty=True)
    if data is None:
        return
    room = None
    pidx = -1
    spectating = False
    with _lock:
        player = players.get(sid)
        if not player:
            return
        room_id = player.get('room_id')
        if room_id is not None:
            room = rooms.get(room_id)
            if room is not None:
                pidx = room.player_index(sid)
        if room is None:
            spectate_room_id = player.get('spectating_room')
            room = rooms.get(spectate_room_id)
            spectating = room is not None and sid in (getattr(room, 'spectators', []) or [])
    if room is None:
        return
    if spectating:
        send_spectate_state_to(room, sid)
    elif pidx >= 0:
        send_game_state_to(room, pidx)


def start_game(room):
    try:
        if getattr(room.engine, 'phase', None) not in ('event_select', 'event_reveal', 'draft'):
            return
        for sid in getattr(room, 'player_sids', []) or []:
            if sid in players:
                players[sid]['status'] = 'in_game'
                players[sid]['room_id'] = room.room_id
        if hasattr(room.engine, 'log'):
            room.engine.log = []
        if hasattr(room.engine, '_log_compaction_floor'):
            room.engine._log_compaction_floor = 0
        if room.engine.start_game() is False:
            admin_event('warning', f'ignored duplicate game start room={room.room_id}', room_id=room.room_id)
            return
        room.started_at = time.time()
        admin_event('game', f'room {room.room_id} started mode={room.mode}')
        record_room_replay_keyframe(room, 'game_start')
        for sid in room.player_sids:
            if sid in players:
                emit_room_game_phase(room, sid, 'playing')
        _broadcast_game_state_now(room)
        broadcast_lobby()
    finally:
        room._start_game_scheduled = False


def start_random_deck_room(room):
    deck_def_ids = create_random_weighted_deck_def_ids(DECK_SIZE, getattr(room.engine, 'allowed_card_ids', None))
    if len(deck_def_ids) < DECK_SIZE:
        raise ValueError('当前模组没有足够可用卡牌生成随机卡组')
    if hasattr(room.engine, 'log'):
        room.engine.log = []
    if hasattr(room.engine, '_log_compaction_floor'):
        room.engine._log_compaction_floor = 0
    room.engine.opening_event_picks = [None, None]
    room.engine.opening_event_sub_choices = [None, None]
    room.engine.draft_picks = [list(deck_def_ids), list(deck_def_ids)]
    room.engine.player_ready = [True, True]
    room.engine.player_draft_started = [True, True]
    room.engine.start_game()
    room.started_at = time.time()
    admin_event('game', f'room {room.room_id} started mode={room.mode} random_deck={deck_def_ids}')
    record_room_replay_keyframe(room, 'game_start')
    for sid in room.player_sids:
        if sid in players:
            players[sid]['status'] = 'in_game'
            players[sid]['room_id'] = room.room_id
            emit_room_game_phase(room, sid, 'playing')
    _broadcast_game_state_now(room)
    broadcast_lobby()


def _build_solo_card(entry):
    if isinstance(entry, dict):
        card = CardInstance(def_id=entry.get('def_id'))
        card.instance_flags = set(entry.get('instance_flags', []))
        card.disabled_flags = set(entry.get('disabled_flags', []))
        return card
    return CardInstance(def_id=entry)


def _reset_player_for_solo(ps, deck_entries, is_first):
    ps.health = INITIAL_HEALTH if is_first else SECOND_PLAYER_HEALTH
    ps.max_health = ps.health
    ps.base_max_health = ps.health
    ps.elixir = FIRST_PLAYER_ELIXIR if is_first else INITIAL_ELIXIR
    ps.max_elixir = 10
    ps.magic = INITIAL_MAGIC
    ps.max_magic = 10
    ps.armor = 0
    ps.poison = 0
    ps.fire = 0
    ps.vulnerable = 0
    ps.toxic = 0
    ps.triangle_stacks = 0
    ps.dodge = 0
    ps.nazar_active = False
    ps.nazar_big_hits = 0
    ps.equipment_protection = 0
    ps.magic_battery_m_this_turn = 0
    ps.coffee_first_use = True
    ps.invincible = False
    ps.skip_turn = False
    ps.damage_multiplier = 1.0
    ps.bandage_active = False
    ps.bandage_death_pending = False
    ps.attack_blocked = 0
    ps.untargetable = False
    ps.sponge_active = False
    ps.shovel_active = False
    ps.attack_only = 0
    ps.enemy_draw_reduction = 0
    ps.enemy_e_reduction = 0
    ps.hand = []
    ps.deck = []
    for entry in deck_entries:
        def_id = entry.get('def_id') if isinstance(entry, dict) else entry
        if def_id in CARD_DEFS:
            ps.deck.append(_build_solo_card(entry))
    ps.discard = []
    ps.exile = []
    ps.equipment = []
    ps.cards_played_this_turn = {}
    ps.custom_vars = {
        '\u5496\u5561\u9996\u6b21\u4f7f\u7528': 1,
        '\u4e09\u89d2\u5f62\u5c42\u6570': 0,
        '\u9b54\u6cd5\u7535\u6c60\u672c\u56de\u5408\u56de\u9b54': 0,
    }
    ps.negate_next_skill = False
    ps.is_first_player = is_first


def create_solo_engine(deck0, deck1, event0=None, event1=None, sub0=None, sub1=None, player_names=None, start_label='单人训练场开始', loadout=None):
    engine = GameEngine()
    engine.available_builtin_setup_card_ids = apply_runtime_content_filter(BUILTIN_SETUP_CARD_IDS, 'solo')
    if loadout is not None:
        apply_v2_loadout_to_engine(engine, loadout, 'solo')
        engine.allowed_card_ids = set(loadout.get('allowed_card_ids') or []) or None
    engine.player_names = list(player_names) if player_names else ['Player A', 'Player B']
    engine.phase = 'playing'
    force_first = [idx for idx, event_id in enumerate((event0, event1)) if event_id == 7]
    engine.first_player = force_first[0] if len(force_first) == 1 else 0
    engine.current_player = engine.first_player
    engine.round_num = 1
    engine.opening_event_picks = [event0, event1]
    engine.opening_event_sub_choices = [sub0, sub1]
    engine.log = []
    engine.pending_response = None
    engine.pending_choice = None
    _reset_player_for_solo(engine.players[0], deck0, engine.first_player == 0)
    _reset_player_for_solo(engine.players[1], deck1, engine.first_player == 1)
    if engine.allowed_card_ids is not None:
        for ps in engine.players:
            ps.deck = [card for card in ps.deck if card.def_id in engine.allowed_card_ids]
    for i in range(2):
        if engine.opening_event_picks[i] is not None:
            engine._apply_opening_event(i)
    for i in range(2):
        if i == engine.first_player:
            hand_size = FIRST_PLAYER_HAND_SIZE
            if engine.opening_event_picks[i] == 7 and len(force_first) == 1:
                hand_size = 4
                engine.players[i].elixir += 3
            if engine.opening_event_picks[i] == 5:
                hand_size = max(0, hand_size - 1)
            engine.players[i].draw_cards(hand_size)
        else:
            hand_size = INITIAL_HAND_SIZE
            if engine.opening_event_picks[i] == 5:
                hand_size = max(0, hand_size - 1)
            engine.players[i].draw_cards(hand_size)
    engine.log_msg(f"{start_label}！{engine.pn(engine.first_player)}先手。")
    engine.log_msg(f"=== 第{engine.round_num}回合 ===")
    engine._start_player_turn(engine.first_player)
    init_solo_history(engine)
    return engine


def init_solo_history(engine):
    if engine is None:
        return
    engine._solo_undo_stack = deque(maxlen=SOLO_HISTORY_LIMIT)
    engine._solo_redo_stack = deque(maxlen=SOLO_HISTORY_LIMIT)


def _solo_history_enabled(sid):
    return sid not in tutorial_sessions


def _solo_engine_snapshot(engine):
    if engine is None:
        return None
    saved = {}
    for attr in ('_solo_undo_stack', '_solo_redo_stack'):
        if hasattr(engine, attr):
            saved[attr] = getattr(engine, attr)
            try:
                delattr(engine, attr)
            except Exception:
                pass
    try:
        return copy.deepcopy(engine)
    finally:
        for attr, value in saved.items():
            setattr(engine, attr, value)


def _solo_capture_undo_snapshot(sid, engine):
    if not _solo_history_enabled(sid):
        return None
    if not hasattr(engine, '_solo_undo_stack') or not hasattr(engine, '_solo_redo_stack'):
        init_solo_history(engine)
    return _solo_engine_snapshot(engine)


def _solo_commit_undo_snapshot(engine, snapshot):
    if engine is None or snapshot is None:
        return
    if not hasattr(engine, '_solo_undo_stack') or not hasattr(engine, '_solo_redo_stack'):
        init_solo_history(engine)
    engine._solo_undo_stack.append(snapshot)
    engine._solo_redo_stack.clear()


def _solo_restore_snapshot(engine, snapshot):
    if engine is None or snapshot is None:
        return False
    undo_stack = getattr(engine, '_solo_undo_stack', deque(maxlen=SOLO_HISTORY_LIMIT))
    redo_stack = getattr(engine, '_solo_redo_stack', deque(maxlen=SOLO_HISTORY_LIMIT))
    restored = copy.deepcopy(snapshot)
    engine.__dict__.clear()
    engine.__dict__.update(restored.__dict__)
    engine._solo_undo_stack = undo_stack
    engine._solo_redo_stack = redo_stack
    try:
        engine._bind_player_callbacks()
    except Exception as exc:
        admin_event('error', f'solo restore callbacks failed: {exc}')
    return True


def _solo_emit_pending_after_state(sid, engine):
    if not engine or getattr(engine, 'game_over', False):
        return
    pending = getattr(engine, 'pending_response', None)
    if pending:
        try:
            pending_player = int(pending.get('player_id', getattr(engine, 'current_player', 0)))
            emit_solo_response_request(sid, engine, pending_player, pending.get('card') or {})
        except Exception as exc:
            admin_event('error', f'solo pending response emit failed: {exc}')
        return
    pending_v2 = getattr(engine, 'pending_v2_ui', None)
    if pending_v2:
        try:
            emit_v2_ui_request_to_sid(sid, engine, ('solo', sid))
        except Exception as exc:
            admin_event('error', f'solo pending v2 emit failed: {exc}')


def send_solo_state_with_pending(sid, perspective=None):
    send_solo_state(sid, perspective)
    _solo_emit_pending_after_state(sid, solo_sessions.get(sid))


TUTORIAL_PROGRESS_KEYS = (
    'attack_played',
    'healed_self',
    'equipped_self',
    'turn_ended',
    'counter_used',
    'trigger_used',
    'fission_applied',
    'fissioned_attack_played',
    'fusion_applied',
    'fusioned_attack_played',
)


def _tutorial_progress(engine):
    progress = getattr(engine, 'tutorial_progress', None)
    if not isinstance(progress, dict):
        progress = {}
        engine.tutorial_progress = progress
    for key in TUTORIAL_PROGRESS_KEYS:
        progress[key] = bool(progress.get(key, False))
    return progress


def _tutorial_mark(engine, key):
    if key in TUTORIAL_PROGRESS_KEYS:
        _tutorial_progress(engine)[key] = True


def _tutorial_refresh_progress(engine):
    progress = _tutorial_progress(engine)
    if not getattr(engine, 'players', None):
        return progress
    for card in list(getattr(engine.players[0], 'hand', []) or []):
        if getattr(card, 'card_type', '') != 'thorn':
            continue
        if int(getattr(card, 'fission_level', 1) or 1) > 1:
            progress['fission_applied'] = True
        if int(getattr(card, 'fusion_level', 1) or 1) > 1:
            progress['fusion_applied'] = True
    return progress


def _tutorial_card_before_action(engine, player_id, card_instance_id):
    if not engine or not (0 <= player_id < len(getattr(engine, 'players', []) or [])):
        return None
    card = engine.players[player_id].find_hand_card(card_instance_id)
    return card.to_dict() if card is not None else None


def _tutorial_choice_target(choice, default=-1):
    if not isinstance(choice, dict):
        return default
    for key in ('target_player_id', 'target_player', 'target_id'):
        try:
            if choice.get(key) is not None:
                return int(choice.get(key))
        except (TypeError, ValueError):
            continue
    return default


def _tutorial_note_card_action(engine, player_id, card_before, choice, result):
    if player_id != 0 or not isinstance(card_before, dict) or not isinstance(result, dict):
        return
    if not (
        result.get('success')
        or result.get('needs_response')
        or result.get('needs_choice')
        or result.get('needs_v2_ui')
    ):
        return
    def_id = str(card_before.get('def_id', '') or '')
    card_def = CARD_DEFS.get(def_id)
    card_type = getattr(card_def, 'card_type', '') if card_def else ''
    target_id = _tutorial_choice_target(choice)
    if card_type == 'thorn':
        _tutorial_mark(engine, 'attack_played')
        if int(card_before.get('fission_level', 1) or 1) > 1:
            _tutorial_mark(engine, 'fissioned_attack_played')
        if int(card_before.get('fusion_level', 1) or 1) > 1:
            _tutorial_mark(engine, 'fusioned_attack_played')
    if def_id == 'Rose' and target_id == 0:
        _tutorial_mark(engine, 'healed_self')
    if def_id == 'Leaf' and target_id == 0:
        _tutorial_mark(engine, 'equipped_self')
    _tutorial_refresh_progress(engine)


def send_solo_state(sid, perspective=None):
    engine = solo_sessions.get(sid)
    if not engine:
        return
    is_tutorial = sid in tutorial_sessions
    if perspective is None:
        perspective = 0 if is_tutorial else (engine.current_player if not engine.game_over else 0)
    state = engine.get_public_state(perspective)
    state['your_id'] = perspective
    state['match_key'] = f"solo:{id(engine)}"
    if is_tutorial:
        state['your_name'] = '你'
        state['opponent_name'] = '练习对手'
        state['tutorial'] = True
        state['tutorial_progress'] = dict(_tutorial_refresh_progress(engine))
        state['tutorial_step_total'] = len(TUTORIAL_PROGRESS_KEYS) + 1
    else:
        state['your_name'] = 'Player A' if perspective == 0 else 'Player B'
        state['opponent_name'] = 'Player B' if perspective == 0 else 'Player A'
    owner_skin = players.get(sid, {}).get('skin') if sid in players else None
    inject_solo_skins(state, owner_skin=owner_skin, perspective=perspective)
    state['solo'] = True
    check_solo_achievements(sid, engine)
    socketio.emit('solo_state', state, room=sid)
    # Check if engine has a pending choice (e.g. foresight_replace) and send choice_request
    pending = getattr(engine, 'pending_choice', None)
    if pending and not engine.game_over:
        socketio.emit('choice_request', build_choice_request_payload(pending), room=sid)


def build_response_request_payload(engine, responder_id, played_card, player_id, counter_cards, target_player_id=None):
    serialized_cards = [
        c.to_dict() if hasattr(c, 'to_dict') else c
        for c in (counter_cards or [])
    ]
    pending = getattr(engine, 'pending_response', None) or {}
    if target_player_id is None:
        target_player_id = pending.get('target_player_id')
    display_card = played_card
    is_confusion_disguise = False
    disguise_builder = getattr(engine, '_sewers_confusion_disguise', None)
    if callable(disguise_builder):
        try:
            display_card = disguise_builder(responder_id, played_card) or played_card
            is_confusion_disguise = bool(
                isinstance(display_card, dict) and display_card.get('sewers_confusion_disguise')
            )
        except Exception as exc:
            admin_event('mod_error', f'confusion response disguise failed: {exc}')
    payload = {
        'card': display_card,
        'player_id': player_id,
        'target_player_id': target_player_id,
        'counter_cards': serialized_cards,
    }
    predictor = getattr(engine, 'build_response_damage_prediction', None)
    if is_confusion_disguise:
        predictor = getattr(engine, 'build_sewers_confusion_damage_prediction', predictor)
    if callable(predictor):
        try:
            if is_confusion_disguise:
                payload['damage_prediction'] = predictor(responder_id, played_card, counter_cards or serialized_cards)
            else:
                payload['damage_prediction'] = predictor(responder_id, counter_cards or serialized_cards)
        except Exception as exc:
            admin_event('mod_error', f'response damage prediction failed: {exc}')
    return payload


def _response_trigger_types_for_card(engine, played_card):
    played_def = CARD_DEFS.get((played_card or {}).get('def_id', ''), None)
    trigger_types = []

    def add(trigger_type):
        if trigger_type and trigger_type not in trigger_types:
            trigger_types.append(trigger_type)

    if played_def:
        if played_def.card_type == 'thorn':
            add('thorn')
        elif played_def.card_type == 'bloom':
            add('bloom')
        elif played_def.card_type == 'root':
            add('root')
        try:
            card_instance = CardInstance.from_dict(played_card)
        except Exception:
            card_instance = None
        would_destroy = False
        destroy_checker = getattr(engine, '_would_destroy_equipment', None)
        if callable(destroy_checker) and card_instance is not None:
            try:
                would_destroy = bool(destroy_checker(card_instance))
            except Exception:
                would_destroy = False
        if would_destroy or played_def.id in ('Sewage', 'MagicSewage'):
            add('equipment_destroy')
        heal_checker = getattr(engine, '_would_heal', None)
        if callable(heal_checker) and card_instance is not None:
            try:
                if heal_checker(card_instance):
                    add('heal')
            except Exception:
                pass
        add('targeted')
        add('any')
    return trigger_types


def emit_pending_response_requests(room, only_player_index=None):
    engine = room.engine
    pending = getattr(engine, 'pending_response', None)
    if not pending:
        return 0
    played_card = pending.get('card') or {}
    try:
        player_id = int(pending.get('player_id', -1))
    except Exception:
        player_id = -1
    sent = 0
    if room.mode == '2v2':
        by_responder = {}
        for counter_card in pending.get('counter_cards', []) or []:
            if not isinstance(counter_card, dict):
                continue
            try:
                responder_id = int(counter_card.get('responder_id', -1))
            except Exception:
                responder_id = -1
            if responder_id < 0:
                continue
            if only_player_index is not None and responder_id != only_player_index:
                continue
            by_responder.setdefault(responder_id, []).append(counter_card)
        for responder_id, counter_cards in by_responder.items():
            if 0 <= responder_id < len(room.player_sids):
                responder_sid = room.player_sids[responder_id]
                if responder_sid in players and responder_sid not in getattr(room, 'disconnected_players', {}):
                    socketio.emit('response_request', build_response_request_payload(
                        engine,
                        responder_id,
                        played_card,
                        player_id,
                        counter_cards,
                        pending.get('target_player_id'),
                    ), room=responder_sid)
                    sent += 1
        return sent

    responder_id = 1 - player_id
    if only_player_index is not None and responder_id != only_player_index:
        return 0
    if not (0 <= responder_id < len(room.player_sids)):
        return 0
    trigger_types = _response_trigger_types_for_card(engine, played_card)
    counter_cards = []
    seen_instances = set()
    for trigger_type in trigger_types:
        for counter_card in engine.get_counter_cards(responder_id, trigger_type):
            key = getattr(counter_card, 'instance_id', None)
            if key in seen_instances:
                continue
            seen_instances.add(key)
            counter_cards.append(counter_card)
    responder_sid = room.player_sids[responder_id]
    if responder_sid in players and responder_sid not in getattr(room, 'disconnected_players', {}):
        socketio.emit('response_request', build_response_request_payload(
            engine,
            responder_id,
            played_card,
            player_id,
            counter_cards,
            pending.get('target_player_id', responder_id),
        ), room=responder_sid)
        sent += 1
    return sent


def build_replay_pending_response_requests(room):
    """Capture the response windows players saw without emitting anything."""
    engine = room.engine
    pending = getattr(engine, 'pending_response', None)
    if not pending:
        return []
    played_card = pending.get('card') or {}
    try:
        player_id = int(pending.get('player_id', -1))
    except Exception:
        player_id = -1
    requests = []
    if room.mode == '2v2':
        by_responder = {}
        for counter_card in pending.get('counter_cards', []) or []:
            if not isinstance(counter_card, dict):
                continue
            try:
                responder_id = int(counter_card.get('responder_id', -1))
            except Exception:
                continue
            if responder_id >= 0:
                by_responder.setdefault(responder_id, []).append(counter_card)
        for responder_id, counter_cards in by_responder.items():
            requests.append({
                'responder_id': responder_id,
                'data': build_response_request_payload(
                    engine,
                    responder_id,
                    played_card,
                    player_id,
                    counter_cards,
                    pending.get('target_player_id'),
                ),
            })
        return requests

    responder_id = 1 - player_id
    if responder_id < 0:
        return []
    counter_cards = []
    seen_instances = set()
    for trigger_type in _response_trigger_types_for_card(engine, played_card):
        for counter_card in engine.get_counter_cards(responder_id, trigger_type):
            key = getattr(counter_card, 'instance_id', None)
            if key in seen_instances:
                continue
            seen_instances.add(key)
            counter_cards.append(counter_card)
    requests.append({
        'responder_id': responder_id,
        'data': build_response_request_payload(
            engine,
            responder_id,
            played_card,
            player_id,
            counter_cards,
            pending.get('target_player_id', responder_id),
        ),
    })
    return requests


def enrich_replay_interaction_payload(room, payload, result=None):
    """Attach exact client-visible interaction data for future replay export."""
    data = dict(payload or {})
    result = result if isinstance(result, dict) else {}
    engine = getattr(room, 'engine', None)
    if result.get('needs_response') or getattr(engine, 'pending_response', None):
        try:
            data['response_requests'] = build_replay_pending_response_requests(room)
        except Exception as exc:
            admin_event('error', f'replay response window capture failed: {exc}')
    pending_choice = getattr(engine, 'pending_choice', None) if engine is not None else None
    choice_source = pending_choice or (result if result.get('choice_type') or result.get('needs_choice') else None)
    if choice_source:
        try:
            data['choice_request'] = build_choice_request_payload(choice_source)
        except Exception as exc:
            admin_event('error', f'replay choice window capture failed: {exc}')
    pending_v2 = getattr(engine, 'pending_v2_ui', None) if engine is not None else None
    if pending_v2:
        data['v2_ui_request'] = _replay_json_safe(pending_v2)
    return data


def _pending_response_responder_ids(room, pending):
    if not pending:
        return []
    if getattr(room, 'mode', '') == '2v2':
        responders = []
        for counter_card in pending.get('counter_cards', []) or []:
            responder_id = _counter_card_responder_id(counter_card)
            if responder_id >= 0 and responder_id not in responders:
                responders.append(responder_id)
        return responders
    try:
        player_id = int(pending.get('player_id', -1))
    except Exception:
        player_id = -1
    responder_id = 1 - player_id
    return [responder_id] if 0 <= responder_id < len(getattr(room, 'player_sids', []) or []) else []


def _room_player_index_online(room, player_index):
    try:
        player_index = int(player_index)
    except Exception:
        return False
    sids = getattr(room, 'player_sids', []) or []
    if not (0 <= player_index < len(sids)):
        return False
    psid = sids[player_index]
    return psid in players and psid not in getattr(room, 'disconnected_players', {})


def _auto_resolve_unreachable_pending_response(room, reason='unreachable'):
    engine = getattr(room, 'engine', None)
    pending = getattr(engine, 'pending_response', None) if engine is not None else None
    if not pending:
        return False
    responders = _pending_response_responder_ids(room, pending)
    if any(_room_player_index_online(room, ridx) for ridx in responders):
        return False
    if not responders:
        try:
            player_id = int(pending.get('player_id', -1))
        except Exception:
            player_id = -1
        responders = [1 - player_id] if player_id in (0, 1) else [player_id]
    responder_id = responders[0] if responders else 0
    try:
        engine.handle_response(responder_id, None)
        admin_event('warning', f'auto_resolve_unreachable_pending_response room={getattr(room, "room_id", "?")} responder={responder_id} reason={reason}', room_id=getattr(room, 'room_id', None))
    except Exception as exc:
        admin_event('error', f'auto_resolve_unreachable_pending_response failed room={getattr(room, "room_id", "?")}: {exc}', room_id=getattr(room, 'room_id', None))
        engine.pending_response = None
    return True


def emit_or_resolve_pending_response(room, reason='emit'):
    sent = emit_pending_response_requests(room)
    if sent > 0 or not getattr(getattr(room, 'engine', None), 'pending_response', None):
        return sent
    if _auto_resolve_unreachable_pending_response(room, reason=reason):
        with _lock:
            _sync_room_action_timer_after_state_change(room)
        emit_turn_timer_update(room)
        broadcast_game_state(room)
        if getattr(room.engine, 'pending_response', None):
            emit_or_resolve_pending_response(room, reason=f'{reason}:chain')
        elif getattr(room.engine, 'pending_choice', None):
            emit_pending_choice_request(room)
        elif getattr(room.engine, 'pending_v2_ui', None):
            emit_room_v2_ui_request(room)
    return sent


def emit_pending_interaction_after_state_change(room, reason='state_change'):
    engine = getattr(room, 'engine', None)
    if engine is None or getattr(engine, 'game_over', False):
        return
    if getattr(engine, 'pending_response', None):
        emit_or_resolve_pending_response(room, reason=reason)
        return
    if getattr(engine, 'pending_choice', None):
        emit_pending_choice_request(room)
        return
    if getattr(engine, 'pending_v2_ui', None):
        emit_room_v2_ui_request(room)


def emit_solo_response_request(sid, engine, pidx, played_card):
    opp_pidx = 1 - pidx
    trigger_types = _response_trigger_types_for_card(engine, played_card)
    counter_cards = []
    seen_instances = set()
    for tt in trigger_types:
        for counter_card in engine.get_counter_cards(opp_pidx, tt):
            key = getattr(counter_card, 'instance_id', None)
            if key in seen_instances:
                continue
            seen_instances.add(key)
            counter_cards.append(counter_card)
    socketio.emit('response_request', build_response_request_payload(
        engine,
        opp_pidx,
        played_card,
        pidx,
        counter_cards,
        (engine.pending_response or {}).get('target_player_id', opp_pidx),
    ), room=sid)


def _schedule_v2_ui_timeout(scope, engine, player_id, request_id, timeout_ms):
    try:
        timeout_ms = int(timeout_ms or 0)
    except Exception:
        timeout_ms = 0
    if timeout_ms <= 0 or not request_id or not scope:
        return
    timer_key = (scope[0], scope[1], request_id)
    if timer_key in v2_ui_timers:
        return

    def _timeout():
        with _lock:
            v2_ui_timers.pop(timer_key, None)
            pending = getattr(engine, 'pending_v2_ui', None)
            if not pending or str(pending.get('request_id')) != str(request_id):
                return
            result = engine.handle_v2_ui_response(player_id, request_id, {'button': 'cancel', 'values': {}})
            if scope[0] == 'solo':
                sid = scope[1]
                if sid in solo_sessions and solo_sessions.get(sid) is engine:
                    send_solo_state(sid)
                    if result.get('needs_v2_ui'):
                        emit_v2_ui_request_to_sid(sid, engine, ('solo', sid))
            elif scope[0] == 'room':
                room = rooms.get(scope[1])
                if room and room.engine is engine:
                    broadcast_game_state(room)
                    if result.get('needs_v2_ui'):
                        emit_room_v2_ui_request(room)

    timer = threading.Timer(timeout_ms / 1000.0, _timeout)
    timer.daemon = True
    v2_ui_timers[timer_key] = timer
    timer.start()


def _cancel_v2_ui_timeout(scope, request_id):
    if not scope or not request_id:
        return
    timer = v2_ui_timers.pop((scope[0], scope[1], request_id), None)
    if timer:
        timer.cancel()


def emit_v2_ui_request_to_sid(sid, engine, timeout_scope=None):
    pending = getattr(engine, 'pending_v2_ui', None)
    if not pending:
        return False
    request_id = pending.get('request_id')
    socketio.emit('v2_ui_request', {
        'request_id': request_id,
        'component': pending.get('component') or {},
        'card': pending.get('card'),
        'timeout_ms': pending.get('timeout_ms', 0),
        'player_id': pending.get('player_id'),
    }, room=sid)
    _schedule_v2_ui_timeout(timeout_scope, engine, pending.get('player_id'), request_id, pending.get('timeout_ms', 0))
    return True


def emit_room_v2_ui_request(room):
    pending = getattr(room.engine, 'pending_v2_ui', None)
    if not pending:
        return False
    pidx = pending.get('player_id')
    if isinstance(pidx, int) and 0 <= pidx < len(room.player_sids):
        target_sid = room.player_sids[pidx]
        if target_sid in players:
            return emit_v2_ui_request_to_sid(target_sid, room.engine, ('room', room.room_id))
    return False


def broadcast_spectate_state(room):
    for spid in room.spectators:
        if spid not in players:
            continue
        send_spectate_state_to(room, spid)


def send_spectate_state_to(room, sid):
    if sid not in players:
        return
    perspective = players[sid].get('spectate_perspective', 0)
    state = build_spectate_state(room, perspective=perspective)
    state['your_id'] = -1
    state['spectating'] = True
    if room.engine.phase == 'game_over' or room.engine.game_over:
        state['match_summary'] = getattr(room, '_match_summary', None)
    state['room_chat_history'] = room_chat_history_for_sid(room, sid, spectator=True)
    for i, psid in enumerate(room.player_sids):
        state[f'player{i + 1}_name'] = room_player_nickname(room, psid, '?')
    socketio.emit('state_update', state, room=sid)


def redact_error_cards_from_player_payload(payload):
    if not isinstance(payload, dict):
        return payload
    for zone in ('hand', 'deck', 'discard', 'exile'):
        cards = payload.get(zone)
        if isinstance(cards, list):
            payload[zone] = [
                card for card in cards
                if not (isinstance(card, dict) and card.get('def_id') == ERROR_CARD_ID)
            ]
            payload[f'{zone}_count'] = len(payload[zone])
    return payload


def build_spectate_state(room, perspective=0):
    engine = room.engine
    base = engine.get_public_state(0)
    full_players = []
    for i, ps in enumerate(engine.players):
        if i >= len(room.player_sids):
            break
        psid = room.player_sids[i]
        pdata = ps.to_dict(include_private=True)
        redact_error_cards_from_player_payload(pdata)
        pdata['player_id'] = i
        pdata['name'] = room_player_nickname(room, psid, f'P{i + 1}')
        pdata['skin'] = player_skin_for_sid(psid, room)
        pdata['skin_look'] = player_skin_look_for_sid(psid, room)
        pdata['is_admin_player'] = player_is_admin(psid, room)
        pdata.update(player_special_fields(psid, room))
        full_players.append(pdata)
    base['spectate_players'] = full_players
    base['player_skin_looks'] = [player_skin_look_for_sid(psid, room) for psid in room.player_sids]
    base['player_names'] = [p.get('name', f'P{i + 1}') for i, p in enumerate(full_players)]
    for i, pdata in enumerate(full_players):
        base[f'player{i + 1}_name'] = pdata.get('name', f'P{i + 1}')
    base['mode'] = room.mode
    base['room_id'] = room.room_id
    base['match_key'] = room_match_key(room)
    base['spectator_count'] = room_spectator_count(room)
    base['room_chat_history'] = room_chat_history_for_sid(room, spectator=True)
    base.update(room_mod_payload(room))
    base.update(_room_disconnect_state_payload(room))
    if getattr(engine, 'game_over', False) or getattr(engine, 'phase', None) == 'game_over':
        base['match_summary'] = getattr(room, '_match_summary', None)
    try:
        perspective = int(perspective or 0)
    except (TypeError, ValueError):
        perspective = 0
    if perspective < 0 or perspective >= len(full_players):
        perspective = 0
    base['spectate_perspective'] = perspective
    if room.mode == '2v2' and len(full_players) >= 4:
        teammate_id = engine.get_teammate(perspective) if hasattr(engine, 'get_teammate') else (perspective ^ 1)
        enemy_ids = engine.get_all_enemies(perspective) if hasattr(engine, 'get_all_enemies') else [i for i in range(4) if i not in (perspective, teammate_id)]
        enemy_ids = [i for i in enemy_ids if 0 <= i < len(full_players)]
        if len(enemy_ids) < 2:
            enemy_ids = [i for i in range(len(full_players)) if i not in (perspective, teammate_id)]
        base['you'] = full_players[perspective]
        base['teammate'] = full_players[teammate_id] if 0 <= teammate_id < len(full_players) else {}
        base['opponent'] = full_players[enemy_ids[0]]
        base['opponent2'] = full_players[enemy_ids[1]]
        base['your_id'] = perspective
        base['teammate_id'] = teammate_id
        base['enemy_ids'] = enemy_ids[:2]
        base['your_name'] = full_players[perspective]['name']
        base['your_is_admin_player'] = full_players[perspective].get('is_admin_player', False)
        base['your_special'] = special_public_fields(full_players[perspective])
        teammate_payload = full_players[teammate_id] if 0 <= teammate_id < len(full_players) else {}
        base['teammate_name'] = teammate_payload.get('name', '?')
        base['teammate_is_admin_player'] = teammate_payload.get('is_admin_player', False)
        base['teammate_special'] = special_public_fields(teammate_payload)
        base['opponent_names'] = [full_players[enemy_ids[0]]['name'], full_players[enemy_ids[1]]['name']]
        base['opponent_admin_flags'] = [full_players[enemy_ids[0]].get('is_admin_player', False), full_players[enemy_ids[1]].get('is_admin_player', False)]
        base['opponent_specials'] = [special_public_fields(full_players[enemy_ids[0]]), special_public_fields(full_players[enemy_ids[1]])]
    elif len(full_players) >= 2:
        opponent_id = 1 - perspective if perspective in (0, 1) else 1
        base['you'] = full_players[perspective]
        base['opponent'] = full_players[opponent_id]
        base['your_id'] = perspective
        base['your_name'] = full_players[perspective]['name']
        base['your_is_admin_player'] = full_players[perspective].get('is_admin_player', False)
        base['your_special'] = special_public_fields(full_players[perspective])
        base['opponent_name'] = full_players[opponent_id]['name']
        base['opponent_is_admin_player'] = full_players[opponent_id].get('is_admin_player', False)
        base['opponent_special'] = special_public_fields(full_players[opponent_id])
    return base


def _mark_disconnect_timeout_loss(room, player_index, nickname):
    e = room.engine
    if getattr(e, 'game_over', False):
        return False
    if player_index < 0 or player_index >= len(getattr(e, 'players', [])):
        return False
    # In 2v2 a player who was already dead may leave without blocking or
    # forfeiting the rest of the match. Alive players still use the normal
    # reconnect timeout path in every phase, including draft/setup.
    if getattr(room, 'mode', None) == '2v2' and _room_player_dead(room, player_index):
        return False
    if getattr(room, 'mode', None) == '2v2':
        changed = _force_2v2_disconnect_death(room, player_index, nickname, '断线超时')
        if changed:
            if not hasattr(room, 'disconnect_timeout_defeated'):
                room.disconnect_timeout_defeated = set()
            room.disconnect_timeout_defeated.add(int(player_index))
        return bool(getattr(e, 'game_over', False)) if changed else False
    disconnected_teams = _room_timed_out_disconnected_teams(room)
    if len(disconnected_teams) >= 2:
        return _finish_room_by_health_tiebreak(room, '双方断线超时')
    return _finish_room_by_forfeit(room, player_index, nickname, '断线超时')


def reconnect_timeout(room_id, old_sid):
    global _next_room_id
    pending_emits = []
    try:
        with _lock:
            if room_id not in rooms:
                return
            room = rooms[room_id]
            if old_sid not in room.disconnected_players:
                return
            dc_info = room.disconnected_players[old_sid]
            timed_out_timer = room.reconnect_timers.pop(old_sid, None)
            if timed_out_timer:
                timed_out_timer.cancel()
            ended = _mark_disconnect_timeout_loss(
                room,
                int(dc_info.get('player_index', -1)),
                dc_info.get('nickname', '?'),
            )
            record_room_replay_action(room, 'disconnect_timeout', int(dc_info.get('player_index', -1)), {
                'nickname': dc_info.get('nickname', '?'),
                'game_over': ended,
                'disconnect_attempt': int(dc_info.get('disconnect_attempt', 1) or 1),
                'reconnect_timeout': int(_disconnect_info_timeout(dc_info)),
            })
            if room.mode == '2v2':
                if ended:
                    _cancel_room_reconnect_timers(room)
                    for other_sid in room.player_sids:
                        if other_sid in players:
                            pending_emits.append(('opponent_disconnected', {'timeout': True, 'game_over': True}, other_sid))
                            pending_emits.append(('game_phase', {'phase': 'game_over'}, other_sid))
                else:
                    for other_sid in room.player_sids:
                        if other_sid in players:
                            pending_emits.append(('opponent_disconnected', {
                                'timeout': True,
                                'game_over': False,
                                'stay': True,
                                'player_defeated': True,
                                'opponent_nickname': dc_info.get('nickname', '?'),
                            }, other_sid))
                admin_event('game', f'room {room_id} disconnect timeout result: {dc_info.get("nickname", "?")}')
                pending_emits.append(('broadcast_game_state', room, None))
                pending_emits.append(('broadcast_lobby', None, None))
            else:
                _cancel_room_reconnect_timers(room)
                if ended:
                    for other_sid in room.player_sids:
                        if other_sid in players:
                            pending_emits.append(('opponent_disconnected', {'timeout': True, 'game_over': True}, other_sid))
                            pending_emits.append(('game_phase', {'phase': 'game_over'}, other_sid))
                    admin_event('game', f'room {room_id} disconnect timeout result: {dc_info.get("nickname", "?")}')
                    pending_emits.append(('broadcast_game_state', room, None))
                for sid, p in players.items():
                    if p['status'] == 'reconnecting' and p['nickname'] == dc_info['nickname']:
                        p['status'] = 'lobby'
                        pending_emits.append(('reconnect_timeout', {}, sid))
    except Exception as exc:
        admin_event('error', f'reconnect_timeout error: {exc}')
    # Perform all emits outside the lock
    for emit_item in pending_emits:
        try:
            if emit_item[0] == 'opponent_disconnected':
                socketio.emit('opponent_disconnected', emit_item[1], room=emit_item[2])
            elif emit_item[0] == 'game_phase':
                socketio.emit('game_phase', emit_item[1], room=emit_item[2])
            elif emit_item[0] == 'reconnect_timeout':
                socketio.emit('reconnect_timeout', emit_item[1], room=emit_item[2])
            elif emit_item[0] == 'broadcast_game_state':
                broadcast_game_state(emit_item[1])
            elif emit_item[0] == 'broadcast_lobby':
                broadcast_lobby()
        except Exception as exc:
            admin_event('error', f'reconnect_timeout emit error: {exc}')
    if not pending_emits:
        broadcast_lobby()


def both_disconnected_cleanup(room_id):
    global _next_room_id
    pending_emits = []
    try:
        with _lock:
            if room_id not in rooms:
                return
            room = rooms[room_id]
            _cancel_room_reconnect_timers(room)
            ended = _finish_room_by_health_tiebreak(room, '双方中途退出')
            if ended:
                record_room_replay_action(room, 'both_disconnected_result', None, {'game_over': True})
                admin_event('game', f'room {room_id} both disconnected: health tiebreak')
                pending_emits.append(('broadcast_game_state', room, None))
            if not any(psid in players for psid in room.player_sids) and not getattr(room, 'spectators', []):
                _cancel_game_over_cleanup_timer(room)
                rooms.pop(room_id, None)
    except Exception as exc:
        admin_event('error', f'both_disconnected_cleanup error: {exc}')
    for emit_item in pending_emits:
        try:
            if emit_item[0] == 'broadcast_game_state':
                broadcast_game_state(emit_item[1])
        except Exception as exc:
            admin_event('error', f'both_disconnected_cleanup emit error: {exc}')
    broadcast_lobby()


@app.route('/')
def index():
    if is_beta_instance():
        return beta_entry_response()
    return render_template(
        'index.html',
        beta_mode=False,
        static_version=GTN_STATIC_VERSION,
        instance_id=GTN_INSTANCE_ID,
        instance_port=GTN_PORT,
        app_version=GTN_VERSION,
        changelog_version=changelog_version(),
    )


def beta_entry_response():
    if is_beta_authenticated():
        return render_template(
            'index.html',
            beta_mode=True,
            static_version=GTN_STATIC_VERSION,
            instance_id=GTN_INSTANCE_ID,
            instance_port=GTN_PORT,
            app_version=GTN_VERSION,
            changelog_version=changelog_version(),
        )
    return render_template('beta_gate.html')


def is_card_exporter_authenticated():
    return bool(session.get('card_exporter_authenticated'))


@app.route('/card-exporter')
def card_exporter_page():
    return render_template('card_exporter.html')


@app.route('/api/card-exporter/me')
def api_card_exporter_me():
    return jsonify({'authenticated': is_card_exporter_authenticated()})


@app.route('/api/card-exporter/login', methods=['POST'])
def api_card_exporter_login():
    data = request.get_json(silent=True) or {}
    key = str(data.get('key') or '')
    if key and check_password_hash(BETA_ACCESS_KEY_HASH, key):
        session['card_exporter_authenticated'] = True
        session['card_exporter_login_time'] = time.time()
        admin_event('security', f'card exporter login success from {_client_ip()}')
        return jsonify({'success': True})
    admin_event('security', f'card exporter login failed from {_client_ip()}')
    return jsonify({'success': False, 'error': '密码错误'}), 401


@app.route('/api/card-exporter/logout', methods=['POST'])
def api_card_exporter_logout():
    session.pop('card_exporter_authenticated', None)
    session.pop('card_exporter_login_time', None)
    return jsonify({'success': True})


@app.route('/api/card-exporter/cards')
def api_card_exporter_cards():
    if not is_card_exporter_authenticated():
        return jsonify({'success': False, 'error': '需要密码'}), 401
    try:
        reload_mod_card_defs()
    except Exception as exc:
        admin_event('error', f'card exporter failed to reload mod card defs: {exc}')
    card_mod_sources = get_card_mod_sources([])
    cards = []
    for def_id, card_def in CARD_DEFS.items():
        if str(def_id or '').lower() in {'error', 'gtn:error', 'system:error'}:
            continue
        source = card_mod_sources.get(def_id, {})
        image_url = str(getattr(card_def, 'image_url', '') or getattr(card_def, 'image', '') or '')
        upgraded_image_url = str(getattr(card_def, 'upgraded_image_url', '') or getattr(card_def, 'upgraded_image', '') or '')
        payload = {
            'id': card_def.id,
            'name_en': card_def.name_en,
            'name_cn': card_def.name_cn,
            'source_mod_filename': source.get('filename', ''),
            'source_mod_name': source.get('name', ''),
            'source_mod_name_cn': source.get('name_cn', ''),
            'source_mod_name_en': source.get('name_en', ''),
            'source_mod_name_i18n': source.get('name_i18n', {}),
            'source_mod_sort_name': source.get('sort_name', ''),
            'source_mod_is_vanilla': bool(source.get('is_vanilla', False)),
            'cost_e': card_def.cost_e,
            'cost_m': card_def.cost_m,
            'card_type': card_def.card_type,
            'count': card_def.count,
            'quality': card_def.quality,
            'description': card_def.description,
            'effect_text': card_def.effect_text,
            'flags': list(card_def.flags) if card_def.flags else [],
            'trigger_cost_e': card_def.trigger_cost_e,
            'trigger_cost_m': getattr(card_def, 'trigger_cost_m', 0),
            'trigger_effect_text': card_def.trigger_effect_text,
            'response_trigger': card_def.response_trigger,
            'image': image_url,
            'image_url': image_url,
            'upgraded_image': upgraded_image_url,
            'upgraded_image_url': upgraded_image_url,
            'ui_effect_size': getattr(card_def, 'ui_effect_size', ''),
            'name_i18n': getattr(card_def, 'name_i18n', {}) or {},
            'description_i18n': getattr(card_def, 'description_i18n', {}) or {},
            'effect_text_i18n': getattr(card_def, 'effect_text_i18n', {}) or {},
            'trigger_effect_text_i18n': getattr(card_def, 'trigger_effect_text_i18n', {}) or {},
            'response_title_i18n': getattr(card_def, 'response_title_i18n', {}) or {},
            'response_content_i18n': getattr(card_def, 'response_content_i18n', {}) or {},
        }
        payload.update(card_text(def_id, payload))
        cards.append(payload)
    cards.sort(key=lambda c: (
        mod_display_order_key(c.get('source_mod_filename') or c.get('source_mod_sort_name') or c.get('source_mod_name_en') or c.get('source_mod_name')),
        {'thorn': 0, 'bloom': 1, 'guard': 2, 'root': 3}.get(str(c.get('card_type') or '').lower(), 9),
        str(c.get('id') or '').lower(),
    ))
    return jsonify({'success': True, 'cards': cards})


@app.route('/api/beta/login', methods=['POST'])
def beta_login():
    if is_release_instance():
        return jsonify({
            'success': False,
            'error': '内测服不在当前正式服实例上，请使用独立内测入口',
            'beta_url': GTN_BETA_PUBLIC_URL,
        }), 404
    ip = _client_ip()
    if should_rate_limit_beta_login(ip):
        admin_event('security', f'beta login rate limited from {ip}')
        return jsonify({'success': False, 'error': '尝试次数过多，请稍后再试'}), 429
    data = request.get_json(silent=True) or {}
    key = str(data.get('key') or '')
    if check_password_hash(BETA_ACCESS_KEY_HASH, key):
        session.permanent = True
        session['beta_authenticated'] = True
        session['beta_login_time'] = time.time()
        clear_beta_login_failures(ip)
        admin_event('security', f'beta login success from {ip}')
        return jsonify({'success': True})
    record_beta_login_failure(ip)
    admin_event('security', f'beta login failed from {ip}')
    return jsonify({'success': False, 'error': '内测秘钥错误'}), 401


@app.route('/api/beta/logout', methods=['POST'])
def beta_logout():
    session.pop('beta_authenticated', None)
    session.pop('beta_login_time', None)
    admin_event('security', f'beta logout from {_client_ip()}')
    return jsonify({'success': True})


@app.route('/api/hidden-features/unlock', methods=['POST'])
def hidden_features_unlock():
    try:
        data = request.get_json(silent=True) or {}
        key = str(data.get('key') or '')
        if key and check_password_hash(BETA_ACCESS_KEY_HASH, key):
            admin_event('security', f'hidden features unlocked from {_client_ip()}')
            return jsonify({'success': True})
        admin_event('security', f'hidden features unlock failed from {_client_ip()}')
        return jsonify({'success': False, 'error': '秘钥错误'}), 401
    except Exception as exc:
        admin_event('error', f'hidden features unlock failed: {exc}')
        return jsonify({'success': False, 'error': '解锁失败'}), 500


@app.route('/favicon.ico')
def favicon():
    icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'assets', 'icons')
    response = send_from_directory(icons_dir, 'favicon.ico', mimetype='image/x-icon')
    response.headers['Cache-Control'] = 'public, max-age=604800'
    return response


@app.route('/fonts/<path:filename>')
def serve_font(filename):
    fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'fonts')
    mimetype = 'font/woff2' if filename.endswith('.woff2') else None
    response = send_from_directory(fonts_dir, filename, mimetype=mimetype)
    if filename.endswith('.woff2') or filename.endswith('.ttf'):
        response.headers['Cache-Control'] = 'public, max-age=604800'
    return response


@app.route('/api/mod-assets/<asset_id>')
def api_mod_asset(asset_id):
    asset = get_mod_asset(asset_id)
    if not asset:
        return ('Not found', 404)
    response = send_file(
        io.BytesIO(asset['data']),
        mimetype=asset.get('mime') or 'application/octet-stream',
        download_name=asset.get('filename') or 'asset',
    )
    response.headers['Cache-Control'] = 'public, max-age=604800'
    return response


@app.route('/admin', methods=['GET', 'POST'])
def admin_fake_login():
    return render_template('admin_fake.html', fake_error='密码错误。' if request.method == 'POST' else '')


@app.route('/adminpage')
def admin_page():
    return render_template('adminpage.html')


@app.route('/adminconsole')
def admin_console_page():
    return render_template('adminconsole.html')


@app.route('/handling')
def handling_page():
    return render_template('handling.html')


@app.route('/api/admin/me')
def admin_me():
    return jsonify({'authenticated': is_admin_authenticated()})


@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(silent=True) or {}
    password = data.get('password', '')
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    if should_rate_limit_admin_login(ip):
        admin_event('security', f'admin login rate limited from {ip}')
        return jsonify({'success': False, 'error': 'too many attempts'}), 429
    if password and check_password_hash(ADMIN_PASSWORD_HASH, password):
        session['admin_authenticated'] = True
        session['admin_login_time'] = time.time()
        ADMIN_LOGIN_FAILURES.pop(ip, None)
        admin_event('security', f'admin login success from {ip}')
        return jsonify({'success': True})
    record_admin_login_failure(ip)
    admin_event('security', f'admin login failed from {ip}')
    return jsonify({'success': False, 'error': 'invalid password'}), 401


@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_authenticated', None)
    session.pop('admin_login_time', None)
    admin_event('security', 'admin logout')
    return jsonify({'success': True})


@app.route('/api/adminconsole/me')
def admin_console_me():
    return jsonify({'authenticated': is_admin_console_authenticated(), 'admin': is_admin_authenticated()})


@app.route('/api/adminconsole/login', methods=['POST'])
def admin_console_login():
    data = request.get_json(silent=True) or {}
    password = data.get('password', '')
    ip = _client_ip()
    rate_key = f'adminconsole:{ip}'
    if should_rate_limit_admin_login(rate_key):
        admin_event('security', f'admin console login rate limited from {ip}')
        return jsonify({'success': False, 'error': 'too many attempts'}), 429
    if password and check_password_hash(ADMIN_CONSOLE_PASSWORD_HASH, password):
        session['admin_console_authenticated'] = True
        session['admin_console_login_time'] = time.time()
        ADMIN_LOGIN_FAILURES.pop(rate_key, None)
        admin_event('security', f'admin console login success from {ip}')
        return jsonify({'success': True})
    record_admin_login_failure(rate_key)
    admin_event('security', f'admin console login failed from {ip}')
    return jsonify({'success': False, 'error': 'invalid password'}), 401


@app.route('/api/adminconsole/logout', methods=['POST'])
def admin_console_logout():
    session.pop('admin_console_authenticated', None)
    session.pop('admin_console_login_time', None)
    admin_event('security', 'admin console logout')
    return jsonify({'success': True})


@app.route('/api/handling/me')
def handling_me():
    return jsonify({'authenticated': is_handling_authenticated(), 'admin': is_admin_authenticated()})


@app.route('/api/handling/login', methods=['POST'])
def handling_login():
    data = request.get_json(silent=True) or {}
    password = data.get('password', '')
    ip = _client_ip()
    if should_rate_limit_admin_login(f'handling:{ip}'):
        admin_event('security', f'handling login rate limited from {ip}')
        return jsonify({'success': False, 'error': 'too many attempts'}), 429
    if password and check_password_hash(HANDLING_PASSWORD_HASH, password):
        session['handling_authenticated'] = True
        session['handling_login_time'] = time.time()
        ADMIN_LOGIN_FAILURES.pop(f'handling:{ip}', None)
        admin_event('security', f'handling login success from {ip}')
        return jsonify({'success': True})
    record_admin_login_failure(f'handling:{ip}')
    admin_event('security', f'handling login failed from {ip}')
    return jsonify({'success': False, 'error': 'invalid password'}), 401


@app.route('/api/handling/logout', methods=['POST'])
def handling_logout():
    session.pop('handling_authenticated', None)
    session.pop('handling_login_time', None)
    admin_event('security', 'handling logout')
    return jsonify({'success': True})


@app.route('/api/handling/reports')
def handling_reports():
    started = time.perf_counter()
    if not DB_AVAILABLE:
        return db_unavailable_response()
    try:
        data = list_reports(
            status=request.args.get('status', 'pending'),
            limit=validate_int(request.args.get('limit', 30), default=30, minimum=1, maximum=50, name='limit'),
            offset=validate_int(request.args.get('offset', 0), default=0, minimum=0, maximum=1000000, name='offset'),
        )
        log_admin_api_timing('/api/handling/reports', (time.perf_counter() - started) * 1000, rows=len(data.get('items') or []), total=data.get('total'), limit=data.get('limit'))
        return jsonify({'success': True, **data})
    except Exception as exc:
        admin_event('error', f'handling reports query failed: {exc}')
        log_admin_api_timing('/api/handling/reports', (time.perf_counter() - started) * 1000, error=type(exc).__name__)
        return jsonify({'success': False, 'error': str(exc)}), 500


@app.route('/api/handling/reports/<int:report_id>')
def handling_report_detail(report_id):
    if not DB_AVAILABLE:
        return db_unavailable_response()
    detail = get_report_detail(report_id)
    if not detail:
        return jsonify({'success': False, 'error': '举报不存在'}), 404
    return jsonify({'success': True, 'report': detail})


@app.route('/api/handling/reports/<int:report_id>/resolve', methods=['POST'])
def handling_report_resolve(report_id):
    if not DB_AVAILABLE:
        return db_unavailable_response()
    data = request.get_json(silent=True) or {}
    try:
        action = validate_str(data.get('action', ''), min_len=1, max_len=20, pattern=r'[A-Za-z0-9_.:\-]+', name='action')
        moderation_action = validate_str(data.get('moderation_action', 'none'), min_len=1, max_len=30, pattern=r'[A-Za-z0-9_.:\-]+', name='moderation_action')
        target_moderation_action = validate_str(data.get('target_moderation_action', moderation_action), min_len=1, max_len=30, pattern=r'[A-Za-z0-9_.:\-]+', name='target_moderation_action')
        reporter_moderation_action = validate_str(data.get('reporter_moderation_action', 'none'), min_len=1, max_len=30, pattern=r'[A-Za-z0-9_.:\-]+', name='reporter_moderation_action')
        duration_seconds = validate_int(data.get('duration_seconds', 0), default=0, minimum=0, maximum=60 * 60 * 24 * 1000, name='duration_seconds')
        note = validate_str(data.get('note', ''), max_len=500, name='note', truncate=True)
    except ValueError as exc:
        return _json_error(str(exc), 400)
    if action not in VALID_REPORT_ACTIONS:
        return _json_error('处理动作无效', 400)
    if moderation_action not in VALID_MODERATION_ACTIONS:
        return _json_error('处罚动作无效', 400)
    if target_moderation_action not in VALID_MODERATION_ACTIONS or reporter_moderation_action not in VALID_MODERATION_ACTIONS:
        return _json_error('处罚动作无效', 400)
    detail, error = resolve_report_entry(
        report_id,
        action,
        moderation_action=moderation_action,
        target_moderation_action=target_moderation_action,
        reporter_moderation_action=reporter_moderation_action,
        admin_username=session.get('username') or 'handling',
        note=note,
        duration_seconds=duration_seconds,
    )
    if error:
        return _json_error(error, 400)
    _apply_report_moderation_action(detail, target_moderation_action, duration_seconds=duration_seconds, note=note, party='target')
    _apply_report_moderation_action(detail, reporter_moderation_action, duration_seconds=duration_seconds, note=note, party='reporter')
    admin_event('moderation', f'handling report #{report_id} resolved action={action} target_moderation={target_moderation_action} reporter_moderation={reporter_moderation_action}')
    return jsonify({'success': True, 'report': detail})


@app.route('/api/handling/users')
def handling_users():
    started = time.perf_counter()
    if not DB_AVAILABLE:
        return db_unavailable_response()
    try:
        data = list_admin_users(
            query=request.args.get('query', ''),
            sort=request.args.get('sort', 'last_login_at'),
            order=request.args.get('order', 'desc'),
            limit=validate_int(request.args.get('limit', 20), default=20, minimum=1, maximum=30, name='limit'),
            offset=validate_int(request.args.get('offset', 0), default=0, minimum=0, maximum=1000000, name='offset'),
        )
    except Exception as exc:
        admin_event('error', f'handling users query failed: {exc}')
        log_admin_api_timing('/api/handling/users', (time.perf_counter() - started) * 1000, error=type(exc).__name__)
        return jsonify({'success': False, 'error': '账号数据库不可用'}), 500
    with _lock:
        online = _admin_online_user_map()
    for user in data.get('users', []):
        user['online'] = online.get(str(user.get('username', '')).lower())
        try:
            user['recent_ips'] = list_user_recent_ips(user.get('id'), limit=5)
        except Exception:
            user['recent_ips'] = []
        if user.get('online') and user['online'].get('ip'):
            ip = str(user['online'].get('ip') or '').strip()
            if ip and not any(item.get('ip') == ip for item in user['recent_ips']):
                user['recent_ips'].insert(0, {'ip': ip, 'last_seen_at': iso_now(), 'count': 0, 'related_users': []})
        user.pop('skin', None)
    log_admin_api_timing(
        '/api/handling/users',
        (time.perf_counter() - started) * 1000,
        rows=len(data.get('users') or []),
        total=data.get('total'),
        limit=data.get('limit'),
        offset=data.get('offset'),
    )
    return jsonify({'success': True, **data})


@app.route('/api/handling/users/<int:user_id>/ban', methods=['POST', 'PATCH'])
def handling_user_ban(user_id):
    if not DB_AVAILABLE:
        return db_unavailable_response()
    data = request.get_json(silent=True) or {}
    try:
        banned = bool(data.get('banned', True))
        reason = validate_str(data.get('reason', ''), max_len=300, name='reason', truncate=True)
        duration_seconds = validate_int(data.get('duration_seconds', 0), default=0, minimum=0, maximum=60 * 60 * 24 * 1000, name='duration_seconds')
    except ValueError as exc:
        return _json_error(str(exc), 400)
    if request.method == 'PATCH':
        user, error = update_active_user_ban(user_id, reason, duration_seconds=duration_seconds or None)
        if error:
            return _json_error(error, 400)
        clear_leaderboard_cache()
        admin_event('moderation', f'handling updated user ban {user.get("username") if user else user_id}: {reason or "-"}')
        return jsonify({'success': True, 'user': user, 'kicked': 0})
    user, error = admin_set_user_ban(user_id, banned, reason, duration_seconds=duration_seconds or None)
    if error:
        return _json_error(error, 400)
    clear_leaderboard_cache()
    kicked = []
    if banned:
        status = get_user_ban_status(user_id=user.get('id'), username=user.get('username')) if user else {'banned': True}
        with _lock:
            kicked = list(_online_sids_for_user(user_id=user.get('id'), username=user.get('username') if user else ''))
        for sid in kicked:
            socketio.emit('server_error', {'message': ban_error_payload(status).get('reason', '账号已被封禁')}, room=sid)
            socketio.emit('kicked', {'reason': 'account banned'}, room=sid)
            socketio.server.disconnect(sid)
        if kicked:
            broadcast_lobby()
    admin_event('moderation', f'handling {"banned" if banned else "unbanned"} user {user.get("username") if user else user_id}: {reason or "-"}')
    return jsonify({'success': True, 'user': user, 'kicked': len(kicked)})


@app.route('/api/handling/moderation')
def handling_moderation_records():
    started = time.perf_counter()
    if not DB_AVAILABLE:
        return db_unavailable_response()
    try:
        kind = validate_str(request.args.get('kind', 'all'), min_len=1, max_len=20, pattern=r'[A-Za-z_]+', name='kind')
        data = list_active_moderation_records(
            kind=kind,
            limit=validate_int(request.args.get('limit', 40), default=40, minimum=1, maximum=50, name='limit'),
            offset=validate_int(request.args.get('offset', 0), default=0, minimum=0, maximum=1000000, name='offset'),
        )
        log_admin_api_timing(
            '/api/handling/moderation',
            (time.perf_counter() - started) * 1000,
            rows=len(data.get('items') or []),
            total=data.get('total'),
            limit=data.get('limit'),
        )
        return jsonify({'success': True, **data})
    except Exception as exc:
        admin_event('error', f'handling moderation query failed: {exc}')
        log_admin_api_timing('/api/handling/moderation', (time.perf_counter() - started) * 1000, error=type(exc).__name__)
        return jsonify({'success': False, 'error': '处罚记录暂时不可用'}), 500


@app.route('/api/handling/warnings/<int:warning_id>', methods=['PATCH', 'DELETE'])
def handling_update_warning(warning_id):
    if not DB_AVAILABLE:
        return db_unavailable_response()
    data = request.get_json(silent=True) or {}
    active = request.method != 'DELETE' and bool(data.get('active', True))
    try:
        reason = validate_str(data.get('reason', ''), max_len=500, name='reason', truncate=True)
        duration_seconds = validate_int(
            data.get('duration_seconds', 3600),
            default=3600,
            minimum=0,
            maximum=60 * 60 * 24 * 1000,
            name='duration_seconds',
        )
    except ValueError as exc:
        return _json_error(str(exc), 400)
    item, error = update_user_warning(warning_id, reason, duration_seconds, active=active)
    if error:
        return _json_error(error, 400)
    payload = {
        'id': item.get('id'),
        'message': item.get('reason') or '请注意游戏内行为',
        'expires_at': item.get('expires_at'),
        'created_at': item.get('created_at'),
    }
    with _lock:
        target_sids = list(_online_sids_for_user(item.get('user_id'), item.get('username') or ''))
    for sid in target_sids:
        socketio.emit('account_warning' if active else 'account_warning_removed', payload, room=sid)
    admin_event('moderation', f'handling {"updated" if active else "ended"} warning #{warning_id}: {reason or "-"}')
    return jsonify({'success': True, 'warning': item})


@app.route('/api/handling/ip-bans')
def handling_ip_bans():
    started = time.perf_counter()
    if not DB_AVAILABLE:
        return db_unavailable_response()
    try:
        active_only = str(request.args.get('active', '1')).strip().lower() not in {'0', 'false', 'no', 'all'}
        data = list_ip_bans(
            active_only=active_only,
            limit=validate_int(request.args.get('limit', 30), default=30, minimum=1, maximum=50, name='limit'),
            offset=validate_int(request.args.get('offset', 0), default=0, minimum=0, maximum=1000000, name='offset'),
        )
        log_admin_api_timing('/api/handling/ip-bans', (time.perf_counter() - started) * 1000, rows=len(data.get('items') or []), total=data.get('total'), limit=data.get('limit'))
        return jsonify({'success': True, **data})
    except Exception as exc:
        admin_event('error', f'handling ip ban list failed: {exc}')
        log_admin_api_timing('/api/handling/ip-bans', (time.perf_counter() - started) * 1000, error=type(exc).__name__)
        return jsonify({'success': False, 'error': str(exc)}), 500


@app.route('/api/handling/ip-bans', methods=['POST'])
def handling_set_ip_ban():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    data = request.get_json(silent=True) or {}
    try:
        ip = validate_str(data.get('ip', ''), min_len=1, max_len=80, pattern=r'[A-Za-z0-9_.:\-]+', name='ip')
        reason = validate_str(data.get('reason', ''), max_len=300, name='reason', truncate=True)
        duration_seconds = validate_int(data.get('duration_seconds', 0), default=0, minimum=0, maximum=60 * 60 * 24 * 1000, name='duration_seconds')
    except ValueError as exc:
        return _json_error(str(exc), 400)
    row, error = set_ip_ban(ip, True, reason, duration_seconds=duration_seconds or None, banned_by=session.get('username') or 'handling')
    if error:
        return _json_error(error, 400)
    kicked = []
    with _lock:
        for sid, player in list(players.items()):
            if str(player.get('ip') or '') == ip:
                kicked.append(sid)
                remove_player_by_admin(sid)
    for sid in kicked:
        socketio.emit('server_error', {'message': 'IP 已被封禁'}, room=sid)
        socketio.emit('kicked', {'reason': 'ip banned'}, room=sid)
        socketio.server.disconnect(sid)
    if kicked:
        broadcast_lobby()
    admin_event('moderation', f'handling banned ip {ip}: {reason or "-"}')
    return jsonify({'success': True, 'ip_ban': row, 'kicked': len(kicked)})


@app.route('/api/handling/ip-bans/<path:ip>', methods=['PATCH', 'DELETE'])
def handling_unban_ip(ip):
    if not DB_AVAILABLE:
        return db_unavailable_response()
    if request.method == 'PATCH':
        data = request.get_json(silent=True) or {}
        try:
            reason = validate_str(data.get('reason', ''), max_len=300, name='reason', truncate=True)
            duration_seconds = validate_int(data.get('duration_seconds', 0), default=0, minimum=0, maximum=60 * 60 * 24 * 1000, name='duration_seconds')
        except ValueError as exc:
            return _json_error(str(exc), 400)
        row, error = update_active_ip_ban(ip, reason, duration_seconds=duration_seconds or None)
        if error:
            return _json_error(error, 400)
        admin_event('moderation', f'handling updated ip ban {ip}: {reason or "-"}')
        return jsonify({'success': True, 'ip_ban': row, 'kicked': 0})
    row, error = set_ip_ban(ip, False)
    if error:
        return _json_error(error, 400)
    admin_event('moderation', f'handling unbanned ip {ip}')
    return jsonify({'success': True, 'ip_ban': row})


@app.route('/api/admin/status')
def admin_status():
    started = time.perf_counter()
    full = str(request.args.get('full', '')).lower() in {'1', 'true', 'yes', 'full'}
    try:
        payload = get_admin_status_payload_cached() if full else get_admin_status_payload_light()
        log_admin_api_timing(
            '/api/admin/status/full' if full else '/api/admin/status/light',
            (time.perf_counter() - started) * 1000,
            players=len(payload.get('players') or []),
            rooms=len(payload.get('rooms') or []),
            cached=bool(payload.get('cached')),
            stale=bool(payload.get('stale')),
        )
        return jsonify(payload)
    except Exception as exc:
        admin_event('error', f'admin status failed: {exc}')
        payload = {
            'success': False,
            'error': str(exc),
            'metrics': {
                'time': iso_now(),
                'uptime_seconds': max(0, int(time.time() - SERVER_STARTED_AT)),
                'metrics_error': str(exc),
            },
            'summary': {
                'online_players': 0,
                'lobby_players': 0,
                'rooms': 0,
                'spectators': 0,
                'history_count': 0,
            },
            'players': [],
            'rooms': [],
            'events': list(ADMIN_EVENTS)[:120],
            'suspicious_events': recent_suspicious_events(120),
            'history': list(MATCH_HISTORY)[:80],
        }
        log_admin_api_timing('/api/admin/status', (time.perf_counter() - started) * 1000, error=type(exc).__name__)
    return jsonify(payload)


@app.route('/api/admin/drain', methods=['GET', 'POST'])
def admin_drain():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        value = bool(data.get('draining'))
        set_instance_draining(value)
        admin_event('deploy', f'instance drain set to {value}', instance_id=GTN_INSTANCE_ID)
    return jsonify({
        'success': True,
        'instance': GTN_INSTANCE,
        'instance_id': GTN_INSTANCE_ID,
        'version': GTN_VERSION,
        'port': GTN_PORT,
        'draining': is_instance_draining(),
        'drain_file': GTN_DRAIN_FILE,
        'rooms': len(rooms),
        'players': len(players),
    })


@app.route('/api/admin/security/suspicious')
def admin_security_suspicious():
    if not is_admin_authenticated():
        return jsonify({'success': False, 'error': 'unauthorized'}), 401
    try:
        limit = validate_int(request.args.get('limit', 100), default=100, minimum=1, maximum=500, name='limit')
        return jsonify({'success': True, 'items': recent_suspicious_events(limit)})
    except Exception as exc:
        admin_event('error', f'admin suspicious events failed: {exc}')
        return jsonify({'success': False, 'error': str(exc)}), 500


@app.route('/api/healthz')
def healthz():
    return jsonify({
        'success': True,
        'instance': GTN_INSTANCE,
        'instance_id': GTN_INSTANCE_ID,
        'version': GTN_VERSION,
        'git_sha': GTN_GIT_SHA,
        'port': GTN_PORT,
        'draining': is_instance_draining(),
        'drain_file': GTN_DRAIN_FILE,
        'git_branch': os.environ.get('GTN_GIT_BRANCH', 'main').strip() or 'main',
        'time': iso_now(),
        'uptime_seconds': max(0, int(time.time() - SERVER_STARTED_AT)),
        'players': len(players),
        'rooms': len(rooms),
        'psutil_available': psutil is not None,
    })


@app.route('/api/health/full')
def health_full():
    db_ok = False
    db_error = ''
    try:
        if DB_AVAILABLE:
            with get_db_connection() as conn:
                conn.execute('SELECT 1').fetchone()
            db_ok = True
        else:
            db_error = 'database unavailable'
    except Exception as exc:
        db_error = str(exc)
    global_lock_busy = False
    global_lock_snapshot = _lock.snapshot() if hasattr(_lock, 'snapshot') else {}
    room_count = player_count = lobby_count = 0
    room_action_busy_count = pending_response_count = pending_choice_count = pending_v2_ui_count = 0
    acquired_global_lock = _lock.acquire(blocking=False)
    if acquired_global_lock:
        try:
            room_count = len(rooms)
            player_count = len(players)
            lobby_count = sum(1 for p in players.values() if p.get('status') == 'lobby')
            for room in list(rooms.values()):
                lock = getattr(room, 'action_lock', None)
                if lock is not None:
                    acquired = lock.acquire(blocking=False)
                    if acquired:
                        lock.release()
                    else:
                        room_action_busy_count += 1
                engine = getattr(room, 'engine', None)
                if engine is not None:
                    pending_response_count += 1 if getattr(engine, 'pending_response', None) else 0
                    pending_choice_count += 1 if getattr(engine, 'pending_choice', None) else 0
                    pending_v2_ui_count += 1 if getattr(engine, 'pending_v2_ui', None) else 0
        finally:
            _lock.release()
    else:
        global_lock_busy = True
        global_lock_snapshot = _lock.snapshot() if hasattr(_lock, 'snapshot') else global_lock_snapshot
    last_lobby_age_seconds = None
    if LAST_LOBBY_UPDATE_AT:
        try:
            last_lobby_age_seconds = max(0, int(time.time() - datetime.fromisoformat(str(LAST_LOBBY_UPDATE_AT).replace('Z', '+00:00')).timestamp()))
        except Exception:
            last_lobby_age_seconds = None
    return jsonify({
        'success': True,
        'time': iso_now(),
        'instance': GTN_INSTANCE,
        'instance_id': GTN_INSTANCE_ID,
        'version': GTN_VERSION,
        'git_sha': GTN_GIT_SHA,
        'static_version': GTN_STATIC_VERSION,
        'draining': is_instance_draining(),
        'drain_file': GTN_DRAIN_FILE,
        'db_ok': db_ok,
        'db_error': db_error,
        'socket_ok': True,
        'global_lock_busy': global_lock_busy,
        'global_lock_held_seconds': global_lock_snapshot.get('held_seconds', 0),
        'global_lock_owner': global_lock_snapshot.get('owner'),
        'global_lock_depth': global_lock_snapshot.get('depth', 0),
        'global_lock_stack': global_lock_snapshot.get('stack', []),
        'room_count': room_count,
        'player_count': player_count,
        'lobby_player_count': lobby_count,
        'last_lobby_update_at': LAST_LOBBY_UPDATE_AT,
        'last_lobby_update_age_seconds': last_lobby_age_seconds,
        'room_action_busy_count': room_action_busy_count,
        'pending_response_count': pending_response_count,
        'pending_choice_count': pending_choice_count,
        'pending_v2_ui_count': pending_v2_ui_count,
        'uptime_seconds': max(0, int(time.time() - SERVER_STARTED_AT)),
    })


@app.route('/api/changelog')
def api_changelog():
    return jsonify({
        'success': True,
        'version': changelog_version(),
        'items': read_changelog_items(request.args.get('limit', 20)),
    })


@app.route('/api/report', methods=['POST'])
def api_report():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    user_id, username, error_response = _require_account_json()
    if error_response:
        return error_response
    data = request.get_json(silent=True) or {}
    try:
        object_type = validate_str(data.get('object_type', ''), min_len=1, max_len=40, pattern=r'[A-Za-z0-9_.:\-]+', name='object_type')
        object_id = validate_str(data.get('object_id', ''), min_len=1, max_len=120, name='object_id')
        category = validate_str(data.get('category', ''), min_len=1, max_len=60, pattern=r'[A-Za-z0-9_.:\-]+', name='category')
        reason_text = validate_str(data.get('reason_text', ''), max_len=300, name='reason_text', truncate=True)
    except ValueError as exc:
        return _json_error(str(exc), 400)
    if object_type not in VALID_REPORT_OBJECT_TYPES:
        return _json_error('举报对象类型无效', 400)
    if not report_category_allowed(object_type, category):
        return _json_error('举报分类无效', 400)
    target_user_id, target_username = _report_target_user(data.get('target_user_id'), data.get('target_username', ''))
    risk_level = 0
    evidence = _collect_report_evidence(object_type, object_id, reporter_user_id=user_id)
    for item in evidence:
        if item.get('evidence_type') != 'chat_context':
            continue
        message = (item.get('data') or {}).get('message') or {}
        risk_level = max(risk_level, int(message.get('risk_level') or 0))
        if not target_user_id and message.get('sender_user_id'):
            target_user_id = message.get('sender_user_id')
        if not target_username and message.get('sender_name'):
            target_username = message.get('sender_name')
    report, error = create_report_entry(
        user_id,
        object_type,
        object_id,
        category,
        reason_text=reason_text,
        target_user_id=target_user_id,
        target_username=target_username,
        risk_level=risk_level,
        evidence=evidence,
    )
    if error:
        record_suspicious_event('report_rejected', error, user_id=user_id, ip=_client_ip(), severity='low', extra={
            'object_type': object_type,
            'object_id': object_id,
            'category': category,
        })
        return _json_error(error, 429 if '频繁' in error or '上限' in error or '重复' in error else 400)
    admin_event('report', f"{username} reported {object_type}:{object_id} category={category}", user_id=user_id)
    return jsonify({'success': True, 'report': report})


@app.route('/api/admin/reports')
def admin_reports():
    if not is_admin_authenticated():
        return jsonify({'success': False, 'error': 'unauthorized'}), 401
    if not DB_AVAILABLE:
        return db_unavailable_response()
    try:
        data = list_reports(
            status=request.args.get('status', 'pending'),
            limit=validate_int(request.args.get('limit', 50), default=50, minimum=1, maximum=100, name='limit'),
            offset=validate_int(request.args.get('offset', 0), default=0, minimum=0, maximum=1000000, name='offset'),
        )
        return jsonify({'success': True, **data})
    except Exception as exc:
        admin_event('error', f'admin reports query failed: {exc}')
        return jsonify({'success': False, 'error': str(exc)}), 500


@app.route('/api/admin/reports/<int:report_id>')
def admin_report_detail(report_id):
    if not is_admin_authenticated():
        return jsonify({'success': False, 'error': 'unauthorized'}), 401
    if not DB_AVAILABLE:
        return db_unavailable_response()
    detail = get_report_detail(report_id)
    if not detail:
        return jsonify({'success': False, 'error': '举报不存在'}), 404
    return jsonify({'success': True, 'report': detail})


@app.route('/api/admin/reports/<int:report_id>/resolve', methods=['POST'])
def admin_report_resolve(report_id):
    if not is_admin_authenticated():
        return jsonify({'success': False, 'error': 'unauthorized'}), 401
    if not DB_AVAILABLE:
        return db_unavailable_response()
    data = request.get_json(silent=True) or {}
    try:
        action = validate_str(data.get('action', ''), min_len=1, max_len=20, pattern=r'[A-Za-z0-9_.:\-]+', name='action')
        moderation_action = validate_str(data.get('moderation_action', 'none'), min_len=1, max_len=30, pattern=r'[A-Za-z0-9_.:\-]+', name='moderation_action')
        duration_seconds = validate_int(data.get('duration_seconds', 0), default=0, minimum=0, maximum=60 * 60 * 24 * 30, name='duration_seconds')
        note = validate_str(data.get('note', ''), max_len=500, name='note', truncate=True)
    except ValueError as exc:
        return _json_error(str(exc), 400)
    if action not in VALID_REPORT_ACTIONS:
        return _json_error('处理动作无效', 400)
    if moderation_action not in VALID_MODERATION_ACTIONS:
        return _json_error('处罚动作无效', 400)
    detail, error = resolve_report_entry(
        report_id,
        action,
        moderation_action=moderation_action,
        admin_username=session.get('username') or ADMIN_PLAYER_DISPLAY_NAME,
        note=note,
        duration_seconds=duration_seconds,
    )
    if error:
        return _json_error(error, 400)
    _apply_report_moderation_action(detail, moderation_action, duration_seconds=duration_seconds, note=note)
    admin_event('moderation', f'report #{report_id} resolved action={action} moderation={moderation_action}')
    return jsonify({'success': True, 'report': detail})


def _admin_online_user_map():
    online = {}
    for sid, player in players.items():
        nickname = player.get('nickname')
        if not nickname:
            continue
        online[str(nickname).lower()] = {
            'sid': sid,
            'status': player.get('status', ''),
            'mode': player.get('mode', '1v1'),
            'room_id': player.get('room_id'),
            'spectating_room': player.get('spectating_room'),
        }
    return online


@app.route('/api/admin/users')
def admin_users():
    started = time.perf_counter()
    try:
        data = list_admin_users(
            query=request.args.get('query', ''),
            sort=request.args.get('sort', 'last_login_at'),
            order=request.args.get('order', 'desc'),
            limit=validate_int(request.args.get('limit', 30), default=30, minimum=1, maximum=50, name='limit'),
            offset=validate_int(request.args.get('offset', 0), default=0, minimum=0, maximum=1000000, name='offset'),
        )
    except Exception as exc:
        admin_event('error', f'admin users query failed: {exc}')
        log_admin_api_timing('/api/admin/users', (time.perf_counter() - started) * 1000, error=type(exc).__name__)
        return jsonify({'success': False, 'error': '账号数据库不可用'}), 500
    with _lock:
        online = _admin_online_user_map()
    for user in data.get('users', []):
        user['online'] = online.get(str(user.get('username', '')).lower())
    log_admin_api_timing(
        '/api/admin/users',
        (time.perf_counter() - started) * 1000,
        rows=len(data.get('users') or []),
        total=data.get('total'),
        limit=data.get('limit'),
        offset=data.get('offset'),
    )
    return jsonify({'success': True, **data})


@app.route('/api/admin/users/<int:user_id>')
def admin_user_detail(user_id):
    started = time.perf_counter()
    try:
        detail = get_admin_user_detail(user_id, request.args.get('match_limit', 30))
    except Exception as exc:
        admin_event('error', f'admin user detail failed: {exc}')
        log_admin_api_timing('/api/admin/users/detail', (time.perf_counter() - started) * 1000, user=user_id, error=type(exc).__name__)
        return jsonify({'success': False, 'error': '账号数据库不可用'}), 500
    if not detail:
        log_admin_api_timing('/api/admin/users/detail', (time.perf_counter() - started) * 1000, user=user_id, rows=0)
        return jsonify({'success': False, 'error': '用户不存在'}), 404
    with _lock:
        online = _admin_online_user_map()
    detail['user']['online'] = online.get(str(detail['user'].get('username', '')).lower())
    log_admin_api_timing('/api/admin/users/detail', (time.perf_counter() - started) * 1000, user=user_id, rows=1)
    return jsonify({'success': True, **detail})


@app.route('/api/admin/draft-stats')
def admin_draft_stats():
    started = time.perf_counter()
    if not DB_AVAILABLE:
        return db_unavailable_response()
    try:
        data = list_card_draft_stats(
            mode=request.args.get('mode', ''),
            sort=request.args.get('sort', 'pick_rate'),
            order=request.args.get('order', 'desc'),
            limit=request.args.get('limit', 300),
            offset=request.args.get('offset', 0),
            merge_modes=str(request.args.get('merge_modes', '')).lower() in ('1', 'true', 'yes', 'on'),
            scope=request.args.get('scope', 'total'),
            week_start=request.args.get('week_start'),
            winner_only=str(request.args.get('winner_only', '')).lower() in ('1', 'true', 'yes', 'on'),
        )
    except Exception as exc:
        admin_event('error', f'admin draft stats failed: {exc}')
        log_admin_api_timing('/api/admin/draft-stats', (time.perf_counter() - started) * 1000, error=type(exc).__name__)
        return jsonify({'success': False, 'error': '抽牌统计数据库不可用'}), 500
    for item in data.get('items', []):
        card_def = CARD_DEFS.get(item.get('card_id'))
        item['name_cn'] = card_def.name_cn if card_def else item.get('card_id')
        item['name_en'] = card_def.name_en if card_def else item.get('card_id')
        item['card_type'] = card_def.card_type if card_def else ''
        item['quality'] = card_def.quality if card_def else ''
    log_admin_api_timing(
        '/api/admin/draft-stats',
        (time.perf_counter() - started) * 1000,
        rows=len(data.get('items') or []),
        total=data.get('total'),
        limit=data.get('limit'),
    )
    return jsonify({'success': True, **data})


@app.route('/api/admin/opening-event-stats')
def admin_opening_event_stats():
    started = time.perf_counter()
    if not DB_AVAILABLE:
        return db_unavailable_response()
    try:
        data = list_opening_event_stats(
            mode=request.args.get('mode', ''),
            sort=request.args.get('sort', 'pick_rate'),
            order=request.args.get('order', 'desc'),
            limit=request.args.get('limit', 300),
            offset=request.args.get('offset', 0),
            merge_modes=str(request.args.get('merge_modes', '')).lower() in ('1', 'true', 'yes', 'on'),
            scope=request.args.get('scope', 'total'),
            week_start=request.args.get('week_start'),
            winner_only=str(request.args.get('winner_only', '')).lower() in ('1', 'true', 'yes', 'on'),
        )
    except Exception as exc:
        admin_event('error', f'admin opening event stats failed: {exc}')
        log_admin_api_timing('/api/admin/opening-event-stats', (time.perf_counter() - started) * 1000, error=type(exc).__name__)
        return jsonify({'success': False, 'error': '配装统计数据库不可用'}), 500
    for item in data.get('items', []):
        event = GameEngine.OPENING_EVENTS.get(int(item.get('event_id'))) if str(item.get('event_id')).isdigit() else None
        if not event:
            event = {'name_cn': item.get('event_id'), 'name_en': item.get('event_id')}
        item['name_cn'] = event.get('name_cn') or event.get('name') or item.get('event_id')
        item['name_en'] = event.get('name_en') or event.get('name') or item.get('event_id')
        item['description'] = event.get('desc') or event.get('description') or ''
    log_admin_api_timing(
        '/api/admin/opening-event-stats',
        (time.perf_counter() - started) * 1000,
        rows=len(data.get('items') or []),
        total=data.get('total'),
        limit=data.get('limit'),
    )
    return jsonify({'success': True, **data})


@app.route('/api/admin/draft-stats/rebuild-wins', methods=['POST'])
def admin_rebuild_draft_win_stats():
    started = time.perf_counter()
    if not DB_AVAILABLE:
        return db_unavailable_response()
    try:
        result = rebuild_card_draft_win_stats_from_matches()
        admin_event('admin', f"card draft win stats rebuilt from matches: {result}")
    except Exception as exc:
        admin_event('error', f'admin rebuild draft win stats failed: {exc}')
        log_admin_api_timing('/api/admin/draft-stats/rebuild-wins', (time.perf_counter() - started) * 1000, error=type(exc).__name__)
        return jsonify({'success': False, 'error': '卡牌胜率补齐失败'}), 500
    log_admin_api_timing(
        '/api/admin/draft-stats/rebuild-wins',
        (time.perf_counter() - started) * 1000,
        rows=result.get('cards'),
        total=result.get('matches'),
    )
    return jsonify({'success': True, 'result': result})


@app.route('/api/admin/storage/summary')
def admin_storage_summary():
    started = time.perf_counter()
    if not DB_AVAILABLE:
        return db_unavailable_response()
    try:
        payload = storage_summary()
        log_admin_api_timing('/api/admin/storage/summary', (time.perf_counter() - started) * 1000)
        return jsonify({'success': True, **payload})
    except Exception as exc:
        admin_event('error', f'storage summary failed: {exc}')
        log_admin_api_timing('/api/admin/storage/summary', (time.perf_counter() - started) * 1000, error=type(exc).__name__)
        return jsonify({'success': False, 'error': str(exc)}), 500


@app.route('/api/admin/storage/cleanup-old', methods=['POST'])
def admin_storage_cleanup_old():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    data = request.get_json(silent=True) or {}
    dry_run = bool(data.get('dry_run', False))
    retention_days = data.get('retention_days', DEFAULT_RETENTION_DAYS)
    if not _replay_cleanup_lock.acquire(blocking=False):
        return jsonify({'success': False, 'error': '已有清理任务正在执行'}), 409
    try:
        result = cleanup_old_replays(retention_days=retention_days, dry_run=dry_run)
        admin_event('admin', f'{"试算" if dry_run else "执行"}清理旧回放: {result}')
        return jsonify({'success': True, 'dry_run': dry_run, 'result': result})
    except Exception as exc:
        admin_event('error', f'cleanup old replays failed: {exc}')
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        _replay_cleanup_lock.release()


@app.route('/api/admin/storage/cleanup-orphans', methods=['POST'])
def admin_storage_cleanup_orphans():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    data = request.get_json(silent=True) or {}
    dry_run = bool(data.get('dry_run', False))
    if not _replay_cleanup_lock.acquire(blocking=False):
        return jsonify({'success': False, 'error': '已有清理任务正在执行'}), 409
    try:
        result = cleanup_orphan_replay_blobs(dry_run=dry_run)
        admin_event('admin', f'{"试算" if dry_run else "执行"}清理孤儿快照: {result}')
        return jsonify({'success': True, 'dry_run': dry_run, 'result': result})
    except Exception as exc:
        admin_event('error', f'cleanup orphan replay blobs failed: {exc}')
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        _replay_cleanup_lock.release()


@app.route('/api/admin/storage/vacuum', methods=['POST'])
def admin_storage_vacuum():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    data = request.get_json(silent=True) or {}
    if data.get('confirm') is not True:
        return jsonify({'success': False, 'error': 'VACUUM 需要 confirm=true'}), 400
    if not _replay_cleanup_lock.acquire(blocking=False):
        return jsonify({'success': False, 'error': '已有清理任务正在执行'}), 409
    try:
        checkpoint = checkpoint_db()
        result = vacuum_db()
        admin_event('admin', '手动 VACUUM 数据库')
        return jsonify({'success': True, 'checkpoint': checkpoint, 'result': result})
    except Exception as exc:
        admin_event('error', f'vacuum failed: {exc}')
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        _replay_cleanup_lock.release()


@app.route('/api/admin/community-mods/storage')
def admin_community_mod_storage():
    try:
        data = list_repository_objects(
            prefix=request.args.get('prefix', 'community/'),
            max_keys=request.args.get('limit', 300),
        )
        return jsonify({'success': True, **data})
    except Exception as exc:
        admin_event('error', f'community mod storage list failed: {exc}')
        return jsonify({'success': False, 'error': str(exc)}), 500


@app.route('/api/admin/community-mods/storage/delete', methods=['POST'])
def admin_community_mod_storage_delete():
    data = request.get_json(silent=True) or {}
    key = str(data.get('key') or '').strip()
    if not key:
        return jsonify({'success': False, 'error': '缺少 key'}), 400
    try:
        result = permanently_delete_repository_object(key)
        status = 200 if result.get('success') else 400
        if result.get('success'):
            admin_event('admin', f'彻底删除 R2 对象: {key}')
        return jsonify(result), status
    except Exception as exc:
        admin_event('error', f'community mod object delete failed: {exc}')
        return jsonify({'success': False, 'error': str(exc)}), 500


@app.route('/api/replays')
def api_replays():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    if not replay_api_allowed():
        return jsonify({'success': False, 'error': 'unauthorized'}), 401
    try:
        admin_context = replay_admin_context_requested()
        if not admin_context and not session.get('user_id'):
            return jsonify({'success': False, 'error': 'unauthorized'}), 401
        player_filter = request.args.get('player', '')
        player_user_id = None
        if not admin_context:
            player_filter = ''
            player_user_id = session.get('user_id')
        data = list_replays(
            limit=request.args.get('limit', 50),
            offset=request.args.get('offset', 0),
            mode=request.args.get('mode', ''),
            player=player_filter,
            mod_source=request.args.get('mod_source', ''),
            player_user_id=player_user_id,
        )
        if not admin_context:
            data['items'] = [item for item in data.get('items', []) if replay_item_visible_to_current_user(item)]
        return jsonify({'success': True, **data})
    except Exception as exc:
        admin_event('error', f'replay list failed: {exc}')
        return jsonify({'success': False, 'error': str(exc)}), 500


@app.route('/api/replays/<int:replay_id>')
def api_replay_detail(replay_id):
    if not DB_AVAILABLE:
        return db_unavailable_response()
    if not replay_api_allowed():
        return jsonify({'success': False, 'error': 'unauthorized'}), 401
    admin_context = replay_admin_context_requested()
    if not admin_context and not session.get('user_id'):
        return jsonify({'success': False, 'error': 'unauthorized'}), 401
    item = get_replay(replay_id)
    if not item:
        return jsonify({'success': False, 'error': '回放不存在'}), 404
    if not replay_item_visible_to_current_user(item, admin_context=admin_context):
        return jsonify({'success': False, 'error': 'forbidden'}), 403
    return jsonify({'success': True, 'replay': item})


@app.route('/api/replays/<int:replay_id>/download')
def api_replay_download(replay_id):
    if not DB_AVAILABLE:
        return db_unavailable_response()
    if not replay_api_allowed():
        return jsonify({'success': False, 'error': 'unauthorized'}), 401
    admin_context = replay_admin_context_requested()
    if not admin_context and not session.get('user_id'):
        return jsonify({'success': False, 'error': 'unauthorized'}), 401
    item = get_replay(replay_id)
    if not item:
        return jsonify({'success': False, 'error': '回放不存在'}), 404
    if not replay_item_visible_to_current_user(item, admin_context=admin_context):
        return jsonify({'success': False, 'error': 'forbidden'}), 403
    limited_response = _replay_download_rate_limit_response(replay_id, item=item, admin_context=admin_context)
    if limited_response is not None:
        return limited_response
    try:
        package = build_replay_download_package(replay_id)
    except Exception as exc:
        admin_event('error', f'replay download failed replay_id={replay_id}: {exc}')
        return jsonify({'success': False, 'error': '回放下载失败'}), 500
    if not package:
        return jsonify({'success': False, 'error': '回放不存在'}), 404
    response = send_file(
        io.BytesIO(package['payload']),
        mimetype='application/vnd.gtn.replay',
        as_attachment=True,
        download_name=package['filename'],
        max_age=0,
    )
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-GTN-Replay-SHA256'] = str(package.get('sha256') or '')
    return response


@app.route('/api/replays/<int:replay_id>/timeline')
def api_replay_timeline(replay_id):
    if not DB_AVAILABLE:
        return db_unavailable_response()
    if not replay_api_allowed():
        return jsonify({'success': False, 'error': 'unauthorized'}), 401
    admin_context = replay_admin_context_requested()
    if not admin_context and not session.get('user_id'):
        return jsonify({'success': False, 'error': 'unauthorized'}), 401
    item = get_replay(replay_id)
    if not item:
        return jsonify({'success': False, 'error': '回放不存在'}), 404
    if not replay_item_visible_to_current_user(item, admin_context=admin_context):
        return jsonify({'success': False, 'error': 'forbidden'}), 403
    try:
        has_slice_args = 'offset' in request.args or 'limit' in request.args
        data = replay_timeline(
            replay_id,
            offset=request.args.get('offset', 0) if has_slice_args else None,
            limit=request.args.get('limit', 50) if has_slice_args else None,
        )
    except Exception as exc:
        admin_event('error', f'replay timeline failed: {exc}')
        return jsonify({'success': False, 'error': str(exc)}), 500
    if not data:
        return jsonify({'success': False, 'error': '回放不存在'}), 404
    return jsonify({'success': True, **data})


@app.route('/api/admin/command', methods=['POST'])
def admin_command():
    data = request.get_json(silent=True) or {}
    line = data.get('line', '')
    try:
        result = execute_admin_command(line)
    except ValueError as exc:
        result = {'success': False, 'output': str(exc)}
    except Exception as exc:
        admin_event('error', f'command failed: {line}: {exc}')
        result = {'success': False, 'output': f'Command failed: {type(exc).__name__}: {exc}'}
    return jsonify(result)


@app.route('/api/admin/complete')
def admin_complete():
    return jsonify({'success': True, 'items': admin_completions(request.args.get('line', ''))})


@app.route('/api/adminconsole/command', methods=['POST'])
def admin_console_command():
    data = request.get_json(silent=True) or {}
    line = data.get('line', '')
    try:
        result = execute_admin_command(line)
    except ValueError as exc:
        result = {'success': False, 'output': str(exc)}
    except Exception as exc:
        admin_event('error', f'admin console command failed: {line}: {exc}')
        result = {'success': False, 'output': f'Command failed: {type(exc).__name__}: {exc}'}
    return jsonify(result)


@app.route('/api/adminconsole/complete')
def admin_console_complete():
    return jsonify({'success': True, 'items': admin_completions(request.args.get('line', ''))})


@app.route('/api/auth/register', methods=['POST'])
def api_auth_register():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    ip = _client_ip()
    if not rate_limiter(f'auth-register:{ip}', limit=5, window=300):
        record_suspicious_event('auth_register_rate', 'register rate limited', ip=ip, severity='high')
        admin_event('security', f'auth register rate limited from {ip}')
        return jsonify({'success': False, 'error': '注册过于频繁，请稍后再试'}), 429
    data = request.get_json(silent=True) or {}
    username = data.get('username', '')
    password = data.get('password', '')
    if 'password_confirm' in data and str(password) != str(data.get('password_confirm', '')):
        return jsonify({'success': False, 'error': '两次输入的密码不一致'}), 400
    user, error = create_user(username, password)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    begin_user_online_session(user.get('id'))
    try:
        record_user_ip_event(user.get('id'), user.get('username'), ip, source='register')
    except Exception as exc:
        admin_event('warning', f'record register ip failed: {exc}')
    user = get_user_by_id(user.get('id')) or user
    _set_account_session(user)
    return _attach_remember_cookie(jsonify({'success': True, 'user': auth_user_payload(user)}), user)


@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    ip = _client_ip()
    if not rate_limiter(f'auth-login:{ip}', limit=30, window=300):
        record_suspicious_event('auth_login_rate', 'login request rate limited', ip=ip, severity='high')
        admin_event('security', f'auth login rate limited from {ip}')
        return jsonify({'success': False, 'error': '登录过于频繁，请稍后再试'}), 429
    if should_rate_limit_auth_login(ip):
        return jsonify({'success': False, 'error': '登录失败次数过多，请稍后再试'}), 429
    data = request.get_json(silent=True) or {}
    user, error = verify_user(data.get('username', ''), data.get('password', ''))
    if error:
        record_auth_login_failure(ip)
        if str(error).startswith('账号已被封禁'):
            status = get_user_ban_status(username=data.get('username', ''))
            payload = ban_error_payload(status, reason_key='error') if status.get('banned') else {'error': error}
            payload['success'] = False
            return jsonify(payload), 401
        return jsonify({'success': False, 'error': error}), 401
    clear_auth_login_failures(ip)
    begin_user_online_session(user.get('id'))
    try:
        record_user_ip_event(user.get('id'), user.get('username'), ip, source='login')
    except Exception as exc:
        admin_event('warning', f'record login ip failed: {exc}')
    user = get_user_by_id(user.get('id')) or user
    _set_account_session(user)
    return _attach_remember_cookie(jsonify({'success': True, 'user': auth_user_payload(user)}), user)


@app.route('/api/auth/change-password', methods=['POST'])
def api_auth_change_password():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    current_user = _current_account_user(allow_remember=False)
    user_id = current_user.get('id') if current_user else None
    if not user_id:
        return jsonify({'success': False, 'error': '请先登录账号'}), 401
    data = request.get_json(silent=True) or {}
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    if str(new_password) != str(data.get('new_password_confirm', '')):
        return jsonify({'success': False, 'error': '两次输入的密码不一致'}), 400
    user, error = change_user_password(user_id, old_password, new_password)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    kicked = _disconnect_account_sockets(
        user_id,
        '密码已修改，所有已登录设备已退出。\n请重新登录。',
        code='password_changed',
    )
    admin_event('security', f'password changed for account {user.get("username")}#{user_id}; invalidated {kicked} socket session(s)')
    _clear_account_session()
    response = jsonify({
        'success': True,
        'logged_out': True,
        'message': '密码已修改，请重新登录',
        'user': auth_user_payload(user),
        'kicked': kicked,
    })
    return _clear_remember_cookie(response)


@app.route('/api/auth/change-username', methods=['POST'])
def api_auth_change_username():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    current_user = _current_account_user(allow_remember=False)
    user_id = current_user.get('id') if current_user else None
    if not user_id:
        return jsonify({'success': False, 'error': '请先登录账号'}), 401
    data = request.get_json(silent=True) or {}
    user, error = change_username(user_id, data.get('username', data.get('new_username', '')))
    if error:
        return jsonify({'success': False, 'error': error}), 400
    _set_account_session(user)
    payload = auth_user_payload(user)
    normalized_skin = public_skin_config(user.get('skin'))
    updated_sids = []
    acquired = _lock.acquire(timeout=0.05)
    if acquired:
        try:
            for sid, player in players.items():
                if player.get('user_id') == user.get('id'):
                    player['nickname'] = user.get('username')
                    player['display_name'] = payload.get('display_name') or user.get('username')
                    player['skin'] = normalized_skin
                    updated_sids.append(sid)
        finally:
            _lock.release()
    else:
        admin_event('warning', f'skip online username cache update for user {user_id}: lobby lock busy')
    if updated_sids:
        broadcast_lobby()
    return jsonify({'success': True, 'user': payload})


@app.route('/api/auth/delete-account', methods=['POST'])
def api_auth_delete_account():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    current_user = _current_account_user(allow_remember=False)
    user_id = current_user.get('id') if current_user else None
    if not user_id:
        return jsonify({'success': False, 'error': '请先登录账号'}), 401
    user, error = soft_delete_user(user_id)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    _clear_account_session()
    response = jsonify({'success': True, 'user': auth_user_payload(user)})
    return _clear_remember_cookie(response)


@app.route('/api/auth/skin', methods=['POST'])
def api_auth_skin():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    current_user = _current_account_user(allow_remember=False)
    user_id = current_user.get('id') if current_user else None
    if not user_id:
        return jsonify({'success': False, 'error': '请先登录账号'}), 401
    try:
        user_id_int = int(user_id)
    except Exception:
        return jsonify({'success': False, 'error': '请先登录账号'}), 401
    now_mono = time.monotonic()
    last_save = float(AUTH_SKIN_SAVE_LAST_AT.get(user_id_int) or 0)
    if now_mono - last_save < 2:
        user = get_user_by_id(user_id)
        return jsonify({'success': True, 'user': auth_user_payload(user), 'skin': public_skin_config((user or {}).get('skin'))})
    AUTH_SKIN_SAVE_LAST_AT[user_id_int] = now_mono
    data = request.get_json(silent=True) or {}
    skin = data.get('skin', data)
    try:
        user, error = update_user_skin(user_id, skin)
    except Exception as exc:
        admin_event('error', f'update_user_skin failed: {exc}')
        return jsonify({'success': False, 'error': '皮肤保存失败，请稍后重试'}), 503
    if error:
        return jsonify({'success': False, 'error': error}), 400
    _set_account_session(user)
    normalized_skin = public_skin_config(user.get('skin'))
    acquired = _lock.acquire(timeout=0.05)
    if acquired:
        try:
            for sid, player in players.items():
                if player.get('user_id') == user_id:
                    player['skin'] = normalized_skin
        finally:
            _lock.release()
    else:
        admin_event('warning', f'skip online skin cache update for user {user_id}: lobby lock busy')
    return jsonify({'success': True, 'user': auth_user_payload(user), 'skin': normalized_skin})


@app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    if DB_AVAILABLE and session.get('user_id'):
        try:
            user_id = session.get('user_id')
            if not _user_has_active_player_session(user_id):
                enqueue_user_last_seen(user_id)
        except Exception as exc:
            admin_event('error', f"failed to enqueue last seen on logout: {exc}")
    _clear_account_session()
    return _clear_remember_cookie(jsonify({'success': True}))


@app.route('/api/auth/me')
def api_auth_me():
    if not DB_AVAILABLE:
        return jsonify({'authenticated': False, 'db_available': False, 'error': DB_INIT_ERROR})
    user = _current_account_user()
    if not user:
        _clear_account_session()
        return _clear_remember_cookie(jsonify({'authenticated': False, 'db_available': True}))
    if user.get('banned'):
        _clear_account_session()
        status = get_user_ban_status(user_id=user.get('id'), username=user.get('username'))
        payload = ban_error_payload(status, reason_key='error') if status.get('banned') else {'error': '账号已被封禁'}
        payload.update({'authenticated': False, 'db_available': True})
        return _clear_remember_cookie(jsonify(payload))
    user = get_user_by_id(user.get('id')) or user
    _set_account_session(user)
    response = jsonify({'authenticated': True, 'db_available': True, 'user': auth_user_payload(user)})
    if not request.cookies.get(REMEMBER_COOKIE_NAME):
        return _attach_remember_cookie(response, user)
    return response


@app.route('/api/thorn-dew')
def api_thorn_dew():
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': DB_INIT_ERROR}), 503
    user = _current_account_user()
    if not user:
        return jsonify({'success': False, 'error': '请先登录账号'}), 401
    try:
        center = get_user_thorn_dew_center(user.get('id'))
        return jsonify({'success': True, **center})
    except sqlite3.OperationalError as exc:
        admin_event('error', f'thorn dew center failed: {exc}')
        return jsonify({'success': False, 'error': '后台暂时不可用，请稍后再试'}), 503
    except Exception as exc:
        admin_event('error', f'thorn dew center failed: {exc}')
        return jsonify({'success': False, 'error': '荆露信息加载失败'}), 500


@app.route('/api/thorn-dew/checkin', methods=['POST'])
def api_thorn_dew_checkin():
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': DB_INIT_ERROR}), 503
    user = _current_account_user()
    if not user:
        return jsonify({'success': False, 'error': '请先登录账号'}), 401
    try:
        center, error = claim_user_daily_checkin(user.get('id'))
        if error:
            return jsonify({'success': False, 'error': error, **(center or {})})
        fresh = get_user_by_id(user.get('id')) or user
        _set_account_session(fresh)
        return jsonify({'success': True, **(center or {}), 'user': auth_user_payload(fresh)})
    except sqlite3.OperationalError as exc:
        admin_event('error', f'thorn dew checkin failed: {exc}')
        return jsonify({'success': False, 'error': '后台暂时不可用，请稍后再试'}), 503
    except Exception as exc:
        admin_event('error', f'thorn dew checkin failed: {exc}')
        return jsonify({'success': False, 'error': '签到失败'}), 500


@app.route('/api/achievements')
def api_achievements():
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': DB_INIT_ERROR}), 503
    user = _current_account_user()
    if not user:
        return jsonify({'success': False, 'error': '请先登录账号'}), 401
    lang = str(request.args.get('lang') or session.get('lang') or 'zh').lower()
    if lang not in {'zh', 'en', 'fr', 'ja'}:
        lang = 'zh'
    try:
        achievements = get_user_achievement_center(user.get('id'), lang=lang)
        dew = get_user_thorn_dew_center(user.get('id'))
        return jsonify({'success': True, **achievements, 'dew': dew})
    except sqlite3.OperationalError as exc:
        admin_event('error', f'achievements failed: {exc}')
        return jsonify({'success': False, 'error': '后台暂时不可用，请稍后再试'}), 503
    except Exception as exc:
        admin_event('error', f'achievements failed: {exc}')
        return jsonify({'success': False, 'error': '成就加载失败'}), 500


@app.route('/api/leaderboard')
def api_leaderboard():
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'items': [], 'error': DB_INIT_ERROR}), 503
    scope = 'total' if str(request.args.get('scope') or '').lower() == 'total' else 'season'
    default_min_games = 20 if scope == 'total' else 8
    try:
        min_games = int(request.args.get('min_games') or default_min_games)
    except (TypeError, ValueError):
        min_games = default_min_games
    try:
        limit = int(request.args.get('limit') or 50)
    except (TypeError, ValueError):
        limit = 50
    started = time.perf_counter()
    try:
        min_games = max(1, min(int(min_games), 10000))
        limit = min(limit, 50)
        now_ts = time.time()
        window_start = int(now_ts // _LEADERBOARD_CACHE_SECONDS) * _LEADERBOARD_CACHE_SECONDS
        next_refresh_ts = window_start + _LEADERBOARD_CACHE_SECONDS
        cache_key = (window_start, scope, min_games, limit)
        generated_at = window_start
        with _LEADERBOARD_CACHE_LOCK:
            cached_payload = _LEADERBOARD_CACHE.get(cache_key)
        if cached_payload is not None:
            items = copy.deepcopy(cached_payload.get('items') or [])
            generated_at = float(cached_payload.get('generated_at') or window_start)
            list_cached = True
        else:
            items = list_leaderboard(min_games=min_games, limit=limit, scope=scope)
            list_cached = False
            with _LEADERBOARD_CACHE_LOCK:
                _LEADERBOARD_CACHE.clear()
                _LEADERBOARD_SELF_RANK_CACHE.clear()
                _LEADERBOARD_CACHE[cache_key] = {
                    'items': copy.deepcopy(items),
                    'generated_at': now_ts,
                }
            generated_at = now_ts
        self_rank = None
        try:
            user = _current_account_user()
            if user and user.get('id'):
                user_id = int(user.get('id'))
                self_cache_key = (window_start, scope, min_games, limit, user_id)
                with _LEADERBOARD_CACHE_LOCK:
                    self_cached_marker = _LEADERBOARD_SELF_RANK_CACHE.get(self_cache_key, '__missing__')
                if self_cached_marker != '__missing__':
                    rank_payload = copy.deepcopy(self_cached_marker)
                else:
                    rank_payload = get_leaderboard_rank(user_id, min_games=min_games, scope=scope)
                    with _LEADERBOARD_CACHE_LOCK:
                        _LEADERBOARD_SELF_RANK_CACHE[self_cache_key] = copy.deepcopy(rank_payload)
                if rank_payload and int(rank_payload.get('rank') or 0) > limit:
                    self_rank = rank_payload
        except Exception as exc:
            admin_event('error', f'leaderboard self rank failed: {exc}')
        db_slow_log('/api/leaderboard', (time.perf_counter() - started) * 1000, 'leaderboard')
        return jsonify({
            'success': True,
            'items': items,
            'self_rank': self_rank,
            'min_games': min_games,
            'scope': scope,
            'cached': list_cached,
            'generated_at': datetime.fromtimestamp(generated_at, timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
            'next_refresh_at': datetime.fromtimestamp(next_refresh_ts, timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
            'next_refresh_ts': int(next_refresh_ts),
            'refresh_interval_seconds': _LEADERBOARD_CACHE_SECONDS,
            'gr': {
                'initial': 1000,
                'season_min_games': 8,
                'total_min_games': 20,
            },
        })
    except sqlite3.OperationalError as exc:
        if 'locked' in str(exc).lower():
            return jsonify({'success': False, 'items': [], 'error': '后台暂时不可用，请稍后刷新。'}), 503
        raise


def _db_busy_response(exc):
    admin_event('db', f'database busy: {exc}')
    return jsonify({'success': False, 'error': '数据库正忙，请稍后再试'}), 503


@app.route('/api/social/friends')
def api_social_friends():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    user_id, _, auth_error = _require_account_json()
    if auth_error:
        return auth_error
    mark_read = str(request.args.get('mark_read') or '').lower() in ('1', 'true', 'yes')
    try:
        if mark_read:
            _, mark_error = mark_friend_notifications_read_for_user(user_id)
            if mark_error:
                return jsonify({'success': False, 'error': mark_error}), 400
        started = time.perf_counter()
        data, error = list_friends(user_id, mark_read=False)
        db_slow_log('/api/social/friends', (time.perf_counter() - started) * 1000, 'friend_list')
    except sqlite3.OperationalError as exc:
        return _db_busy_response(exc)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, **(data or {})})


@app.route('/api/social/friends/add', methods=['POST'])
def api_social_friend_add():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    user_id, _, auth_error = _require_account_json()
    if auth_error:
        return auth_error
    data = request.get_json(silent=True) or {}
    try:
        started = time.perf_counter()
        result, error = add_friend_request(user_id, data.get('identifier', ''))
        db_slow_log('/api/social/friends/add', (time.perf_counter() - started) * 1000, 'friend_add')
    except sqlite3.OperationalError as exc:
        return _db_busy_response(exc)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, **(result or {})})


@app.route('/api/social/friends/respond', methods=['POST'])
def api_social_friend_respond():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    user_id, _, auth_error = _require_account_json()
    if auth_error:
        return auth_error
    data = request.get_json(silent=True) or {}
    try:
        result, error = respond_friend_request(user_id, data.get('request_id'), data.get('action'))
    except sqlite3.OperationalError as exc:
        return _db_busy_response(exc)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, **(result or {})})


@app.route('/api/social/friends/remove', methods=['POST'])
def api_social_friend_remove():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    user_id, _, auth_error = _require_account_json()
    if auth_error:
        return auth_error
    data = request.get_json(silent=True) or {}
    try:
        result, error = remove_friend(user_id, data.get('user_id'))
    except sqlite3.OperationalError as exc:
        return _db_busy_response(exc)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, **(result or {})})


@app.route('/api/social/settings', methods=['POST'])
def api_social_settings_update():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    user_id, _, auth_error = _require_account_json()
    if auth_error:
        return auth_error
    data = request.get_json(silent=True) or {}
    settings, error = update_user_social_settings(user_id, data)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    with _lock:
        for player in players.values():
            if player.get('user_id') != user_id:
                continue
            player['accept_game_invites'] = bool(settings.get('accept_game_invites', True))
            player['allow_guest_spectators'] = bool(settings.get('allow_guest_spectators', False))
    user = get_user_by_id(user_id)
    return jsonify({'success': True, 'settings': settings, 'user': auth_user_payload(user)})


@app.route('/api/feedback/summary')
def api_feedback_summary():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    user_id, _, auth_error = _require_account_json()
    if auth_error:
        return auth_error
    try:
        return jsonify({
            'success': True,
            'is_staff': bool(feedback_is_staff(user_id)),
            'unread_count': int(feedback_unread_count(user_id) or 0),
        })
    except sqlite3.OperationalError as exc:
        return _db_busy_response(exc)


@app.route('/api/feedback/threads')
def api_feedback_threads():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    user_id, _, auth_error = _require_account_json()
    if auth_error:
        return auth_error
    staff_view = str(request.args.get('staff') or '').lower() in ('1', 'true', 'yes')
    try:
        limit = max(1, min(int(request.args.get('limit', 50) or 50), 100))
    except Exception:
        limit = 50
    try:
        data, error = list_feedback_threads(
            user_id,
            staff_view=staff_view,
            status=request.args.get('status', ''),
            limit=limit,
        )
    except sqlite3.OperationalError as exc:
        return _db_busy_response(exc)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, **(data or {})})


@app.route('/api/feedback/messages')
def api_feedback_messages():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    user_id, _, auth_error = _require_account_json()
    if auth_error:
        return auth_error
    try:
        limit = max(1, min(int(request.args.get('limit', 100) or 100), 200))
    except Exception:
        limit = 100
    mark_read = str(request.args.get('mark_read', '1')).lower() in ('1', 'true', 'yes')
    try:
        data, error = get_feedback_messages(user_id, request.args.get('thread_id'), mark_read=mark_read, limit=limit)
    except sqlite3.OperationalError as exc:
        return _db_busy_response(exc)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, **(data or {})})


@app.route('/api/feedback/send', methods=['POST'])
def api_feedback_send():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    user_id, user, auth_error = _require_account_json()
    if auth_error:
        return auth_error
    muted, mute_info = is_user_muted_db(user_id)
    if muted:
        remaining = 0
        try:
            until_dt = datetime.fromisoformat(str(mute_info.get('muted_until') or '').replace('Z', '+00:00'))
            remaining = max(0, int((until_dt - datetime.now(timezone.utc)).total_seconds()))
        except Exception:
            remaining = 0
        return jsonify({'success': False, **muted_error_payload(remaining)}), 403
    exempt = _chat_exempt_from_user_id(user_id)
    if not exempt:
        if not rate_limiter(f'feedback:{user_id}:fast', limit=1, window=2):
            return jsonify({'success': False, 'error': '发送过快'}), 429
        if not rate_limiter(f'feedback:{user_id}:minute', limit=8, window=60):
            return jsonify({'success': False, 'error': '发送过快'}), 429
    data = request.get_json(silent=True) or {}
    thread_id = data.get('thread_id')
    category = str(data.get('category', 'other') or 'other').strip().lower()
    replay_id = None
    if thread_id in (None, ''):
        raw_replay_id = data.get('replay_id')
        if category == 'appeal' and raw_replay_id in (None, ''):
            return jsonify({'success': False, 'error': '对局申诉需要填写回放 ID'}), 400
        if raw_replay_id not in (None, ''):
            try:
                replay_id = normalize_replay_id(raw_replay_id)
            except ValueError as exc:
                return jsonify({'success': False, 'error': str(exc)}), 400
            if not feedback_is_staff(user_id) and not replay_visible_to_user(replay_id, user_id, user):
                return jsonify({'success': False, 'error': '回放不存在，或你不是该局参与者'}), 403
    try:
        text, chat_risk = _validate_chat_text_for_sender(data.get('text', ''), exempt=exempt)
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    if not text:
        return jsonify({'success': False, 'error': '消息不能为空'}), 400
    risk_level = int(chat_risk.get('risk_level') or 0)
    if str(chat_risk.get('risk_action') or '') == 'reject_mute' or risk_level >= 4:
        try:
            set_user_mute(user_id, user or '', 300, 'severe feedback risk', 'system')
        except Exception as exc:
            admin_event('error', f'failed to persist severe feedback mute: {exc}')
        return jsonify({'success': False, **muted_error_payload(300, message='消息包含高风险内容，已被拦截并临时禁言')}), 403
    try:
        result, error = send_feedback_message(
            user_id,
            text,
            thread_id=thread_id,
            category=category,
            title=data.get('title', '') or (f'对局申诉 {format_replay_id(replay_id)}' if replay_id else ''),
            normalized_message=chat_risk.get('normalized_message') or normalize_message(text),
            risk_level=risk_level,
            replay_id=replay_id,
        )
    except sqlite3.OperationalError as exc:
        return _db_busy_response(exc)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    if replay_id:
        try:
            thread = (result or {}).get('thread') or {}
            hold_replay(
                replay_id,
                days=180,
                reason=f'feedback:{thread.get("id") or "appeal"}',
                created_by=f'user:{user_id}',
            )
        except Exception as exc:
            admin_event('error', f'failed to hold appealed replay {replay_id}: {exc}', user_id=user_id)
    return jsonify({'success': True, **(result or {})})


@app.route('/api/feedback/status', methods=['POST'])
def api_feedback_status():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    user_id, _, auth_error = _require_account_json()
    if auth_error:
        return auth_error
    data = request.get_json(silent=True) or {}
    try:
        result, error = update_feedback_status(user_id, data.get('thread_id'), data.get('status'))
    except sqlite3.OperationalError as exc:
        return _db_busy_response(exc)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, **(result or {})})


@app.route('/api/social/dm/threads')
def api_social_dm_threads():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    user_id, _, auth_error = _require_account_json()
    if auth_error:
        return auth_error
    try:
        limit = max(1, min(int(request.args.get('limit', 50) or 50), 50))
    except Exception:
        limit = 50
    cache_key = (int(user_id), limit)
    now_mono = time.monotonic()
    cached = SOCIAL_DM_THREADS_CACHE.get(cache_key)
    if cached and now_mono - cached.get('at', 0) < 3:
        return jsonify({'success': True, **(cached.get('data') or {})})
    try:
        started = time.perf_counter()
        data, error = list_dm_threads(user_id, limit=limit)
        db_slow_log('/api/social/dm/threads', (time.perf_counter() - started) * 1000, 'dm_threads')
    except sqlite3.OperationalError as exc:
        return _db_busy_response(exc)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    SOCIAL_DM_THREADS_CACHE[cache_key] = {'at': now_mono, 'data': data or {}}
    return jsonify({'success': True, **(data or {})})


@app.route('/api/social/dm/messages')
def api_social_dm_messages():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    user_id, _, auth_error = _require_account_json()
    if auth_error:
        return auth_error
    try:
        limit = max(1, min(int(request.args.get('limit', 50) or 50), 50))
    except Exception:
        limit = 50
    mark_read = str(request.args.get('mark_read', '0')).lower() in ('1', 'true', 'yes')
    try:
        data, error = get_dm_messages(
            user_id,
            request.args.get('thread_id'),
            mark_read=mark_read,
            limit=limit,
        )
    except sqlite3.OperationalError as exc:
        return _db_busy_response(exc)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    if mark_read:
        for key in list(SOCIAL_DM_THREADS_CACHE.keys()):
            try:
                if int(key[0]) == int(user_id):
                    SOCIAL_DM_THREADS_CACHE.pop(key, None)
            except Exception:
                continue
        _emit_dm_update_for_user(user_id)
    return jsonify({'success': True, **(data or {})})


@app.route('/api/social/dm/send', methods=['POST'])
def api_social_dm_send():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    user_id, user, auth_error = _require_account_json()
    if auth_error:
        return auth_error
    muted, mute_info = is_user_muted_db(user_id)
    if muted:
        remaining = 0
        try:
            until_dt = datetime.fromisoformat(str(mute_info.get('muted_until') or '').replace('Z', '+00:00'))
            remaining = max(0, int((until_dt - datetime.now(timezone.utc)).total_seconds()))
        except Exception:
            remaining = 0
        return jsonify({'success': False, **muted_error_payload(remaining)}), 403
    data = request.get_json(silent=True) or {}
    exempt = _chat_exempt_from_user_id(user_id)
    rate_key = f'dm:{user_id}'
    if not exempt:
        if not rate_limiter(f'{rate_key}:fast', limit=1, window=2):
            return jsonify({'success': False, 'error': '聊天发送过快'}), 429
        if not rate_limiter(f'{rate_key}:burst', limit=5, window=10):
            return jsonify({'success': False, 'error': '聊天发送过快'}), 429
        if not rate_limiter(f'{rate_key}:minute', limit=CHAT_RATE_LIMIT, window=CHAT_RATE_WINDOW_SECONDS):
            return jsonify({'success': False, 'error': '聊天发送过快'}), 429
    try:
        text, chat_risk = _validate_chat_text_for_sender(data.get('text', ''), exempt=exempt)
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    if not text:
        return jsonify({'success': False, 'error': '消息不能为空'}), 400
    risk_level = int(chat_risk.get('risk_level') or 0)
    risk_action = str(chat_risk.get('risk_action') or '')
    normalized_message = chat_risk.get('normalized_message') or normalize_message(text)
    if risk_action == 'reject_mute' or risk_level >= 4:
        try:
            set_user_mute(user_id, user or '', 300, 'severe private message risk', 'system')
        except Exception as exc:
            admin_event('error', f'failed to persist severe dm mute: {exc}')
        return jsonify({'success': False, **muted_error_payload(300, message='消息包含高风险内容，已被拦截并临时禁言')}), 403
    try:
        result, error = send_dm_message(
            user_id,
            target_identifier=data.get('identifier'),
            target_user_id=data.get('target_user_id'),
            message=text,
            normalized_message=normalized_message,
            risk_level=risk_level,
            hidden=False,
        )
    except sqlite3.OperationalError as exc:
        return _db_busy_response(exc)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    recipient_id = None
    sent = (result or {}).get('sent_message') or {}
    try:
        recipient_id = int(sent.get('recipient_user_id'))
    except Exception:
        recipient_id = None
    for key in list(SOCIAL_DM_THREADS_CACHE.keys()):
        try:
            if int(key[0]) in (int(user_id), int(recipient_id or -1)):
                SOCIAL_DM_THREADS_CACHE.pop(key, None)
        except Exception:
            continue
    _emit_dm_update_for_user(user_id)
    _emit_dm_update_for_user(recipient_id)
    return jsonify({'success': True, **(result or {})})


@app.route('/api/cards')
def api_cards():
    try:
        reload_mod_card_defs()
    except Exception as exc:
        admin_event('error', f'failed to reload mod card defs: {exc}')
    disable_rows = active_content_disables('any')
    cache_key = (
        current_mods_signature(),
        _public_data_query_key(),
        _public_data_disable_key(disable_rows),
    )
    cached_response = _public_data_cache_get('cards', cache_key)
    if cached_response is not None:
        return cached_response
    disabled_mods = request.args.get('disabled_mods', '')
    try:
        community_fields, community_mod = resolve_community_loadout(request.args)
    except Exception as exc:
        return _json_error(str(exc), 400)
    include_all_mods = str(request.args.get('include_all_mods', '')).strip().lower() in {'1', 'true', 'yes', 'all'}
    runtime_mode = str(request.args.get('mode', '') or '').strip().lower() or None
    loadout = build_mod_loadout(
        disabled_mods,
        community_mod=community_mod,
        community_hash=community_fields.get('community_mod_hash', ''),
        runtime_mode=runtime_mode,
    )
    allowed_card_ids = set(CARD_DEFS.keys()) if include_all_mods else loadout['allowed_card_ids']
    card_mod_sources = get_card_mod_sources([])
    shared_card_memberships = get_all_mod_shared_card_memberships()
    if community_mod:
        selected_hashes = {
            str(entry.get('sha256') or '').strip().lower()
            for entry in community_fields.get('community_mods', [])
        }
        for card_id, existing_source in COMMUNITY_CARD_SOURCES.items():
            source_hash = _community_source_hash(existing_source).lower()
            if source_hash and source_hash in selected_hashes and isinstance(existing_source, dict):
                card_mod_sources[card_id] = {
                    'filename': source_hash,
                    'name': existing_source.get('name') or 'Community Mod',
                    'sort_name': existing_source.get('sort_name') or existing_source.get('name') or 'Community Mod',
                    'is_vanilla': False,
                    'is_community': True,
                }
    result = {}
    for def_id, card_def in CARD_DEFS.items():
        source = card_mod_sources.get(def_id, {})
        card_disable_rows = [
            row for row in disable_rows
            if (row.get('content_type') == 'card' and row.get('content_id') == def_id)
            or (
                def_id not in ALL_MOD_SHARED_CARD_IDS
                and row.get('content_type') == 'mod'
                and row.get('content_id') == source.get('filename')
            )
        ]
        image_url = str(getattr(card_def, 'image_url', '') or getattr(card_def, 'image', '') or '')
        upgraded_image_url = str(getattr(card_def, 'upgraded_image_url', '') or getattr(card_def, 'upgraded_image', '') or '')
        card_payload = {
            'id': card_def.id,
            'visible_in_current_loadout': def_id in allowed_card_ids,
            'temporarily_disabled': bool(card_disable_rows),
            'temporary_disable_reason': next((row.get('reason') for row in card_disable_rows if row.get('reason')), ''),
            'temporary_disable_until': next((row.get('expires_at') for row in card_disable_rows if row.get('expires_at')), None),
            'temporary_disable_scopes': sorted({str(row.get('scope_mode') or 'all') for row in card_disable_rows}),
            'name_en': card_def.name_en,
            'name_cn': card_def.name_cn,
            'source_mod_filename': source.get('filename', ''),
            'source_mod_name': source.get('name', ''),
            'source_mod_name_cn': source.get('name_cn', ''),
            'source_mod_name_en': source.get('name_en', ''),
            'source_mod_name_i18n': source.get('name_i18n', {}),
            'source_mod_sort_name': source.get('sort_name', ''),
            'source_mod_is_vanilla': bool(source.get('is_vanilla', False)),
            'source_mod_is_community': bool(source.get('is_community', False)),
            'source_mod_memberships': shared_card_memberships.get(def_id, []),
            'cost_e': card_def.cost_e,
            'cost_m': card_def.cost_m,
            'card_type': card_def.card_type,
            'count': card_def.count,
            'quality': card_def.quality,
            'description': card_def.description,
            'effect_text': card_def.effect_text,
            'flags': list(card_def.flags) if card_def.flags else [],
            'trigger_cost_e': card_def.trigger_cost_e,
            'trigger_cost_m': getattr(card_def, 'trigger_cost_m', 0),
            'trigger_effect_text': card_def.trigger_effect_text,
            'response_trigger': card_def.response_trigger,
            'response_title': getattr(card_def, 'response_title', ''),
            'response_content': getattr(card_def, 'response_content', ''),
            'effects': card_def.effects,
            'scripts': getattr(card_def, 'scripts', {}) or {},
            'v2_events': getattr(card_def, 'v2_events', {}) or {},
            'damage': getattr(card_def, 'damage', 0),
            'hits': getattr(card_def, 'hits', 1),
            'copy_count': getattr(card_def, 'copy_count', 0),
            'swift_value': getattr(card_def, 'swift_value', 0),
            'magic_swift_value': getattr(card_def, 'magic_swift_value', 0),
            'power_value': getattr(card_def, 'power_value', 0),
            'fission_level': getattr(card_def, 'fission_level', 1),
            'fusion_level': getattr(card_def, 'fusion_level', 1),
            'image': image_url,
            'image_url': image_url,
            'upgraded_image': upgraded_image_url,
            'upgraded_image_url': upgraded_image_url,
            'ui_effect_size': getattr(card_def, 'ui_effect_size', ''),
            'name_i18n': getattr(card_def, 'name_i18n', {}) or {},
            'description_i18n': getattr(card_def, 'description_i18n', {}) or {},
            'effect_text_i18n': getattr(card_def, 'effect_text_i18n', {}) or {},
            'trigger_effect_text_i18n': getattr(card_def, 'trigger_effect_text_i18n', {}) or {},
            'response_title_i18n': getattr(card_def, 'response_title_i18n', {}) or {},
            'response_content_i18n': getattr(card_def, 'response_content_i18n', {}) or {},
        }
        if getattr(card_def, 'v2_mod_id', ''):
            card_payload['v2_mod_id'] = getattr(card_def, 'v2_mod_id', '')
            card_payload['v2_resource'] = getattr(card_def, 'v2_resource', {}) or {}
        card_payload.update(card_text(def_id, card_payload))
        result[def_id] = card_payload
    return _public_data_cache_put('cards', cache_key, result)


@app.route('/api/opening-events')
def api_opening_events():
    try:
        reload_mod_card_defs()
    except Exception as exc:
        admin_event('error', f'failed to reload mod card defs: {exc}')
    cache_key = (current_mods_signature(), _public_data_query_key())
    cached_response = _public_data_cache_get('opening_events', cache_key)
    if cached_response is not None:
        return cached_response
    try:
        community_fields, community_mod = resolve_community_loadout(request.args)
    except Exception as exc:
        return _json_error(str(exc), 400)
    include_all_mods = str(request.args.get('include_all_mods', '')).strip().lower() in {'1', 'true', 'yes', 'all'}
    loadout = build_mod_loadout(
        '' if include_all_mods else request.args.get('disabled_mods', ''),
        community_mod=community_mod,
        community_hash=community_fields.get('community_mod_hash', ''),
    )
    allowed_card_ids = loadout['allowed_card_ids']
    events = []
    for event_id in sorted(GameEngine.OPENING_EVENTS.keys()):
        events.append(event_text(event_id, dict(GameEngine.OPENING_EVENTS[event_id])))
    registries = getattr(loadout.get('v2_loadout'), 'registries', {}) if loadout.get('v2_loadout') is not None else {}
    for resource in (registries.get('opening_events') or {}).values():
        payload = v2_opening_event_payload(resource)
        if payload:
            events.append(payload)
    registry_payload = v2_registry_payload(loadout.get('v2_loadout'))
    return _public_data_cache_put('opening_events', cache_key, {
        'events': events,
        'magic_pool': [],
        **registry_payload,
    })


@app.route('/api/mods')
def api_mods():
    summary_only = str(request.args.get('summary', '')).strip().lower() in {'1', 'true', 'yes'}
    runtime_rows = active_content_disables('any')
    cache_key = (
        current_mods_signature(),
        _public_data_query_key(),
        _public_data_disable_key(runtime_rows),
    )
    cached_response = _public_data_cache_get('mods', cache_key)
    if cached_response is not None:
        return cached_response
    mods = load_all_mods()
    runtime_mod_rows = {}
    for row in runtime_rows:
        if row.get('content_type') == 'mod':
            runtime_mod_rows.setdefault(str(row.get('content_id')), []).append(row)
    shared_payloads = {}
    for mod in mods:
        for card in mod.to_dict(include_validation=False).get('cards', []) or []:
            card_id = str(card.get('legacy_id') or card.get('id') or '')
            if card_id in ALL_MOD_SHARED_CARD_IDS and card_id not in shared_payloads:
                shared_payloads[card_id] = copy.deepcopy(card)
    result = []
    for mod in mods:
        d = mod.to_dict(include_validation=True)
        d['filename'] = mod.filename
        d['is_vanilla'] = mod.filename == VANILLA_MOD_FILENAME
        d['category'] = mod_category(mod)
        runtime_disable = runtime_mod_rows.get(mod.filename, [])
        d['temporarily_disabled'] = bool(runtime_disable)
        d['temporary_disable_reason'] = next((row.get('reason') for row in runtime_disable if row.get('reason')), '')
        d['temporary_disable_until'] = next((row.get('expires_at') for row in runtime_disable if row.get('expires_at')), None)
        d['temporary_disable_scopes'] = sorted({str(row.get('scope_mode') or 'all') for row in runtime_disable})
        cards = list(d.get('cards') or [])
        existing_ids = {str(card.get('legacy_id') or card.get('id') or '') for card in cards}
        shared_ids = []
        for card_id in ALL_MOD_SHARED_CARD_IDS:
            if card_id not in existing_ids and card_id in shared_payloads:
                cards.append(copy.deepcopy(shared_payloads[card_id]))
            if card_id in shared_payloads:
                shared_ids.append(card_id)
        d['cards'] = cards
        d['cards_count'] = len(cards)
        d['shared_card_ids'] = sorted(shared_ids)
        if getattr(mod, 'format_version', 1) == 2:
            d['content_hash'] = getattr(mod, 'content_hash', '') or getattr(mod, 'validation_hash', '')
            if hasattr(mod, 'resource_counts'):
                d['resource_counts'] = mod.resource_counts()
            d['card_type_counts'] = {
                card_type: sum(1 for card in cards if str(card.get('card_type') or '') == card_type and int(card.get('count', 0) or 0) > 0)
                for card_type in REQUIRED_CARD_TYPES
            }
        else:
            d['card_type_counts'] = {
                card_type: sum(1 for card in cards if str(card.get('card_type') or '') == card_type and int(card.get('count', 0) or 0) > 0)
                for card_type in REQUIRED_CARD_TYPES
            }
        if summary_only:
            summary_keys = {
                'format_version', 'info', 'manifest', 'errors', 'warnings',
                'validation_hash', 'content_hash', 'resource_counts', 'filename',
                'is_vanilla', 'category', 'temporarily_disabled',
                'temporary_disable_reason', 'temporary_disable_until',
                'temporary_disable_scopes', 'cards_count', 'shared_card_ids',
                'card_type_counts',
            }
            d = {key: value for key, value in d.items() if key in summary_keys}
        result.append(d)
    return _public_data_cache_put('mods', cache_key, result)


@app.route('/api/community-mods')
def api_community_mods():
    try:
        index = get_community_index()
        mods = index.get('mods', []) if isinstance(index, dict) else []
        user_id, username = _current_account_identity()
        visible_mods = []
        for item in mods:
            if not isinstance(item, dict):
                continue
            row = dict(item)
            owner_user_id = str(row.get('uploader_user_id') or '').strip()
            owner_name = str(row.get('uploader_name') or '').strip()
            can_manage = False
            if user_id and owner_user_id and owner_user_id == str(user_id):
                can_manage = True
            elif user_id and not owner_user_id and owner_name.lower() == str(username or '').strip().lower():
                can_manage = True
            if _current_account_can_manage_all_community_mods():
                can_manage = True
            row.pop('uploader_user_id', None)
            row['can_manage'] = can_manage
            visible_mods.append(row)
        return jsonify({'success': True, 'mods': visible_mods, 'authenticated': bool(user_id)})
    except Exception as exc:
        admin_event('error', f'community mods index failed: {exc}')
        return jsonify({'success': False, 'mods': [], 'error': str(exc)})


@app.route('/api/community-mods/upload-url', methods=['POST'])
def api_community_mod_upload_url():
    _, _, auth_error = _require_account_json()
    if auth_error:
        return auth_error
    ip = _client_ip()
    if _rate_limited(ip, 'community_upload_url'):
        return _json_error('上传过于频繁，请稍后再试', 429)
    data = request.get_json(silent=True) or {}
    filename = str(data.get('filename') or '').strip()
    if not filename.lower().endswith(('.json', '.gtnmod')):
        return _json_error('只允许上传 .json 文件')
    try:
        result = create_presigned_mod_upload(filename)
        return jsonify({'success': True, **result})
    except Exception as exc:
        record_r2_failure('upload_url', exc)
        admin_event('error', f'create community upload url failed: {exc}')
        return _json_error(str(exc), 500 if isinstance(exc, R2ConfigError) else 400)


@app.route('/api/community-mods/register', methods=['POST'])
def api_community_mod_register():
    user_id, username, auth_error = _require_account_json()
    if auth_error:
        return auth_error
    ip = _client_ip()
    if _rate_limited(ip, 'community_register'):
        return _json_error('登记过于频繁，请稍后再试', 429)
    data = request.get_json(silent=True) or {}
    public_url = str(data.get('public_url') or '').strip()
    key = str(data.get('key') or '').strip()
    replace_sha256 = str(data.get('replace_sha256') or '').strip()
    uploader_name = username
    if not public_url or not key:
        return _json_error('缺少 key 或 public_url')
    try:
        result = register_community_mod(
            public_url,
            key,
            uploader_name,
            uploader_user_id=user_id,
            replace_sha256=replace_sha256,
        )
        if not result.get('success'):
            record_r2_failure('register_validation', result.get('errors') or result.get('error') or '')
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as exc:
        record_r2_failure('register', exc)
        admin_event('error', f'register community mod failed: {exc}')
        return _json_error(str(exc), 500 if isinstance(exc, R2ConfigError) else 400)


@app.route('/api/community-mods/<sha256>', methods=['DELETE'])
def api_community_mod_delete(sha256):
    user_id, username, auth_error = _require_account_json()
    if auth_error:
        return auth_error
    ip = _client_ip()
    if _rate_limited(ip, 'community_delete'):
        return _json_error('操作过于频繁，请稍后再试', 429)
    try:
        result = delete_community_mod(
            sha256,
            uploader_user_id=user_id,
            uploader_name=username,
            allow_any=_current_account_can_manage_all_community_mods(),
        )
        if not result.get('success'):
            record_r2_failure('delete', result.get('error', ''))
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as exc:
        record_r2_failure('delete', exc)
        admin_event('error', f'delete community mod failed: {exc}')
        return _json_error(str(exc), 500 if isinstance(exc, R2ConfigError) else 400)


@app.route('/api/community-mods/validate-url', methods=['POST'])
def api_community_mod_validate_url():
    data = request.get_json(silent=True) or {}
    public_url = str(data.get('public_url') or '').strip()
    if not public_url:
        return _json_error('缺少 public_url')
    try:
        result = validate_community_mod_url(public_url)
        return jsonify({'success': result.get('ok', False), **result})
    except Exception as exc:
        admin_event('error', f'validate community mod url failed: {exc}')
        return _json_error(str(exc), 500 if isinstance(exc, R2ConfigError) else 400)


@app.route('/api/font-subsets/community', methods=['POST'])
def api_community_font_subset():
    data = request.get_json(silent=True) or {}
    try:
        community_fields, community_mods = resolve_community_loadout(data)
        if community_fields.get('mod_source') != 'community':
            return jsonify({'success': True, 'font_subset': {'url': '', 'missing_count': 0, 'warnings': []}})
        mod_datas = [
            getattr(mod, 'community_data', None)
            for mod in (community_mods or [])
            if getattr(mod, 'community_data', None) is not None
        ]
        report = ensure_community_font_subset(
            mod_datas,
            hash_key=community_fields.get('community_mod_hash', ''),
            generate=True,
        )
        return jsonify({'success': True, 'font_subset': report})
    except Exception as exc:
        admin_event('error', f'community font subset failed: {exc}')
        return _json_error(str(exc), 500 if isinstance(exc, R2ConfigError) else 400)


@app.route('/api/mods/save', methods=['POST'])
def api_mods_save():
    data = request.get_json(force=True)
    if not data:
        return jsonify({'success': False, 'error': 'invalid data'}), 400
    if data.get('format_version') != 2:
        return jsonify({'success': False, 'errors': ['只接受 GTN Mod Spec v2（format_version 必须为 2）'], 'warnings': []}), 400
    from mod_validator_v2 import validate_mod_v2
    validation = validate_mod_v2(data, source='api_mods_save', allow_reserved_namespaces=True)
    if validation.errors:
        return jsonify({'success': False, 'errors': validation.errors, 'warnings': validation.warnings}), 400
    data = validation.normalized
    mods_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mods')
    manifest = data.get('manifest') if isinstance(data.get('manifest'), dict) else {}
    requested_name = data.get('filename') or os.path.basename(str(data.get('filepath') or f"{manifest.get('id') or 'new_mod'}.json"))
    safe_name = os.path.basename(requested_name).strip() or 'new_mod.json'
    if not safe_name.endswith('.json'):
        safe_name += '.json'
    try:
        os.makedirs(mods_dir, exist_ok=True)
        with open(os.path.join(mods_dir, safe_name), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        from mod_loader import invalidate_mod_cache
        invalidate_mod_cache()
        reload_mod_card_defs(force=True)
        return jsonify({'success': True, 'warnings': validation.warnings})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/ls')
def admin_ls():
    with _lock:
        player_list = []
        for sid, p in players.items():
            player_list.append({
                'sid': sid,
                'nickname': p['nickname'],
                'status': p['status'],
                'room_id': p.get('room_id'),
            })
        room_list = []
        for rid, room in rooms.items():
            e = room.engine
            p_names = []
            for psid in room.player_sids:
                name = room_player_nickname(room, psid, '?')
                p_names.append(name if psid in players else f'{name}(离线)')
            room_list.append({
                'room_id': rid,
                'players': p_names,
                'phase': e.phase,
                'round': e.round_num,
                'spectators': len(room.spectators),
            })
    return jsonify({'players': player_list, 'rooms': room_list})


@app.route('/api/admin/kick', methods=['POST'])
def admin_kick():
    data = request.get_json(force=True)
    sid = data.get('sid', '')
    with _lock:
        if sid not in players:
            return jsonify({'success': False, 'error': 'player not found'}), 404
        room_id = players[sid].get('room_id')
        if room_id is not None and room_id in rooms:
            admin_match_record(rooms[room_id], result='admin_kick')
        nickname = remove_player_by_admin(sid)
    socketio.emit('kicked', {'reason': 'kicked by admin'}, room=sid)
    broadcast_lobby()
    admin_event('admin', f'kicked {nickname}')
    return jsonify({'success': True, 'nickname': nickname})


@app.route('/api/admin/broadcast', methods=['POST'])
def admin_broadcast():
    data = request.get_json(force=True)
    msg = data.get('message', '')
    if not msg.strip():
        return jsonify({'success': False, 'error': 'empty message'}), 400
    send_system_broadcast(msg)
    admin_event('admin', f'broadcast: {msg}')
    return jsonify({'success': True})


@app.route('/api/admin/game-chat')
def admin_game_chat():
    started = time.perf_counter()
    try:
        limit = max(1, min(int(request.args.get('limit', ADMIN_GAME_CHAT_VISIBLE_LIMIT)), ADMIN_GAME_CHAT_VISIBLE_LIMIT))
    except (TypeError, ValueError):
        limit = ADMIN_GAME_CHAT_VISIBLE_LIMIT
    with _lock:
        items = admin_game_chat_recent_locked(limit)
        total_cached = len(ADMIN_GAME_CHAT_CACHE)
    log_admin_api_timing('/api/admin/game-chat', (time.perf_counter() - started) * 1000, rows=len(items), total=total_cached, limit=limit)
    return jsonify({
        'success': True,
        'items': items,
        'limit': limit,
        'total_cached': total_cached,
    })


@app.route('/api/admin/game-chat/send', methods=['POST'])
def admin_game_chat_send():
    data = request.get_json(silent=True) or {}
    text = normalize_chat_text(data.get('text', ''), exempt=True)[:500]
    if not text.strip():
        return jsonify({'success': False, 'error': 'empty message'}), 400
    payload = console_chat_payload(text)
    now = time.time()
    with _lock:
        append_lobby_chat_locked(payload, now, beta_mode=False)
        append_lobby_chat_locked(payload, now, beta_mode=True)
        append_admin_game_chat_locked(payload, now, scope='console')
        lobby_history_payloads = lobby_chat_history_payloads_locked(LOBBY_CHAT_VISIBLE_LIMIT)
        recipients = [(sid, p.get('status')) for sid, p in players.items()]
    if DB_AVAILABLE:
        for beta_mode in (False, True):
            try:
                record_chat_message(
                    f'lobby:{_lobby_chat_scope_key(beta_mode)}',
                    'console',
                    None,
                    payload.get('nickname', '控制台'),
                    payload.get('text', ''),
                    json.dumps({**payload, 'type': 'chat', 'beta_mode': bool(beta_mode)}, ensure_ascii=False),
                    0,
                    hidden=False,
                )
            except Exception as exc:
                admin_event('error', f'failed to persist console lobby chat: {exc}')
    sent = 0
    for sid, status in recipients:
        if status == 'lobby':
            continue
        socketio.emit('chat', payload, room=sid)
        sent += 1
    emit_lobby_chat_history_payloads(lobby_history_payloads)
    admin_event('admin', f'game chat: {text}')
    return jsonify({'success': True, 'sent': sent})


@app.route('/api/admin/room/<int:room_id>/skip', methods=['POST'])
def admin_skip(room_id):
    with _lock:
        if room_id not in rooms:
            return jsonify({'success': False, 'error': 'room not found'}), 404
        room = rooms[room_id]
        e = room.engine
        if e.game_over:
            return jsonify({'success': False, 'error': 'game already over'}), 400
        if e.phase in ('action', 'draw'):
            e._end_player_turn(e.current_player)
            broadcast_game_state(room)
            admin_event('admin', f'skipped room {room_id}')
            return jsonify({'success': True, 'phase': e.phase, 'current_player': e.current_player})
        return jsonify({'success': False, 'error': f'cannot skip during phase {e.phase}'}), 400


@app.route('/api/admin/room/<int:room_id>/endgame', methods=['POST'])
def admin_endgame(room_id):
    data = request.get_json(force=True)
    winner = data.get('winner', 0)
    if winner not in (0, 1):
        return jsonify({'success': False, 'error': 'winner must be 0 or 1'}), 400
    with _lock:
        if room_id not in rooms:
            return jsonify({'success': False, 'error': 'room not found'}), 404
        room = rooms[room_id]
        e = room.engine
        loser = 1 - winner
        _force_player_death_ignoring_saves(room, loser, e.pn(loser), '被管理员强制结束', log=False, check_game_over=False)
        e._check_game_over()
        admin_match_record(room, result='admin_endgame')
        broadcast_game_state(room)
        admin_event('admin', f'endgame room {room_id} winner={winner}')
        return jsonify({'success': True, 'winner': e.winner})


@app.route('/api/admin/room/<int:room_id>/draftfill', methods=['POST'])
def admin_draftfill(room_id):
    with _lock:
        if room_id not in rooms:
            return jsonify({'success': False, 'error': 'room not found'}), 404
        room = rooms[room_id]
        e = room.engine
        if e.phase not in ('draft', 'event_select', 'event_reveal'):
            return jsonify({'success': False, 'error': f'cannot fill draft during phase {e.phase}'}), 400
        filled = 0
        while e.phase == 'draft':
            made_progress = False
            for pidx in range(2):
                target_count = e.draft_target_count(pidx) if hasattr(e, 'draft_target_count') else DECK_SIZE
                if len(e.draft_picks[pidx]) < target_count:
                    options = e.draft_options[pidx]
                    if options:
                        pick = options[0]
                        e.draft_pick(pidx, pick.def_id)
                        filled += 1
                        made_progress = True
            if not made_progress:
                break
        if e.phase == 'event_select':
            for pidx in range(2):
                options = e.opening_event_options[pidx]
                if options and options[0]:
                    e.select_opening_event(pidx, options[0]['id'])
            start_game(room)
        return jsonify({'success': True, 'filled': filled})


@app.route('/api/admin/room/<int:room_id>/set', methods=['POST'])
def admin_set_attr(room_id):
    data = request.get_json(force=True)
    pidx = data.get('player', -1)
    key = data.get('key', '')
    val = data.get('value', 0)
    ok, output = set_room_player_attr(room_id, pidx, key, val)
    if not ok:
        return jsonify({'success': False, 'error': output}), 400
    admin_event('admin', f'set room {room_id} player {pidx} {key}={val}')
    return jsonify({'success': True})


@socketio.on('connect')
def on_connect():
    started = time.perf_counter()
    sid = request.sid
    ok = True
    try:
        ensure_event_loop_watchdog_started()
        ensure_lobby_idle_cleanup_started()
        ensure_pending_interaction_watchdog_started()
        ensure_room_timer_worker_started()
        ip = _client_ip()
        if DB_AVAILABLE:
            try:
                ip_status = get_ip_ban_status(ip)
            except Exception as exc:
                admin_event('error', f'socket ip ban check failed: {exc}')
                ip_status = {'banned': False}
            if ip_status.get('banned'):
                ok = False
                record_suspicious_event('connect_ip_banned', 'banned IP tried to connect', sid=sid, ip=ip, severity='high')
                socketio.server.disconnect(sid)
                return
        if not rate_limiter(f'connect-ip:{_client_ip()}', limit=30, window=60):
            ok = False
            record_suspicious_event('connect_rate_ip', 'Socket connect IP rate limited', sid=sid, ip=_client_ip(), severity='high')
            socketio.server.disconnect(sid)
            return
        join_room(sid)
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        record_socket_action('connect', elapsed_ms, sid=sid, room_id=None, ok=ok)
        if elapsed_ms >= _SOCKET_ACTION_SLOW_MS:
            admin_event('perf', f'socket_event event=connect elapsed_ms={elapsed_ms:.1f} sid={sid} ok={ok}')
            print(f'socket_event event=connect elapsed_ms={elapsed_ms:.1f} sid={sid} ok={ok}', flush=True)


@socketio.on('latency_ping')
def on_latency_ping(data=None):
    sid = request.sid
    if not rate_limiter(f'socket:sid:{sid}:latency_ping', limit=120, window=60):
        _security_record('latency_ping_rate', 'latency ping rate limited', sid=sid, severity='low')
        return
    if data is not None and not isinstance(data, dict):
        _security_illegal(sid, 'latency_ping', '参数格式错误', emit_error=False, severity='low')
        return
    safe_t = None
    try:
        safe_t = validate_int((data or {}).get('t'), default=None, minimum=0, maximum=10**16, name='t') if (data or {}).get('t') is not None else None
    except ValueError:
        safe_t = None
    emit('latency_pong', {
        't': safe_t,
        'server_time': int(time.time() * 1000),
    })


@socketio.on('latency_report')
def on_latency_report(data=None):
    sid = request.sid
    if not rate_limiter(f'socket:sid:{sid}:latency_report', limit=60, window=60):
        _security_record('latency_report_rate', 'latency report rate limited', sid=sid, severity='low')
        return
    if data is not None and not isinstance(data, dict):
        _security_illegal(sid, 'latency_report', '参数格式错误', emit_error=False, severity='low')
        return
    data = data or {}
    try:
        rtt_ms = validate_int(data.get('rtt_ms'), default=0, minimum=0, maximum=60000, name='rtt_ms')
        transport = validate_str(data.get('transport', ''), max_len=32, pattern=r'[A-Za-z0-9_.:\-]*', name='transport')
    except ValueError as exc:
        _security_illegal(sid, 'latency_report', str(exc), emit_error=False, severity='low')
        return
    record_socket_latency(sid, rtt_ms, transport)


@socketio.on('afk_check_response')
def on_afk_check_response(data=None):
    data = socket_guard('afk_check_response', data, require_player=True, allow_empty=False, emit_error=False)
    if data is None:
        return
    sid = request.sid
    request_id = str(data.get('id') or '')
    try:
        hold_ms = int(data.get('hold_ms') or 0)
    except Exception:
        hold_ms = 0
    now = time.time()
    result_payload = None
    passed = False
    nickname = '?'
    with _lock:
        pending = PENDING_AFK_CHECKS.get(sid)
        player = players.get(sid)
        nickname = (player or {}).get('nickname', '?')
        if not pending or pending.get('id') != request_id:
            result_payload = {'success': False, 'retry': False, 'message': '挂机检测已失效'}
        elif now > float(pending.get('expires_at') or 0):
            PENDING_AFK_CHECKS.pop(sid, None)
            result_payload = {'success': False, 'retry': False, 'message': '挂机检测已超时'}
        else:
            min_ms = int(pending.get('min_ms') or AFK_CHECK_HOLD_MIN_MS)
            max_ms = int(pending.get('max_ms') or AFK_CHECK_HOLD_MAX_MS)
            if hold_ms < min_ms:
                result_payload = {'success': False, 'retry': True, 'message': '按得太短了，请重试'}
            elif hold_ms > max_ms:
                result_payload = {'success': False, 'retry': True, 'message': '按得太久了，请重试'}
            else:
                PENDING_AFK_CHECKS.pop(sid, None)
                if player and player.get('status') == 'lobby':
                    player['last_lobby_activity_at'] = now
                    player['next_lobby_afk_check_at'] = now + random.uniform(
                        max(60, AFK_AUTO_MIN_SECONDS),
                        max(max(60, AFK_AUTO_MIN_SECONDS), AFK_AUTO_MAX_SECONDS),
                    )
                result_payload = {'success': True, 'message': '挂机检测已通过'}
                passed = True
    emit('afk_check_result', result_payload or {'success': False, 'retry': False, 'message': '挂机检测失败'})
    if passed:
        admin_event('player', f'afk check passed: {nickname} sid={sid} hold_ms={hold_ms}')


@socketio.on('skin_look')
def on_skin_look(data=None):
    sid = request.sid
    data = socket_guard('skin_look', data, require_player=True, emit_error=False)
    if data is None:
        return
    look = normalize_skin_look(data)
    targets = set()
    payload = None
    with _lock:
        player = players.get(sid)
        if not player:
            return
        player['skin_look'] = look
        room_id = player.get('room_id')
        if room_id is None or room_id not in rooms:
            return
        room = rooms[room_id]
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        payload = {'player_id': pidx, 'look': look}
        targets = {tsid for tsid in room.player_sids if tsid in players}
        targets.update(tsid for tsid in getattr(room, 'spectators', []) if tsid in players)
    for target_sid in targets:
        socketio.emit('skin_look_update', payload, room=target_sid)


@socketio.on('draft_reroll')
@measure_socket_action('draft_reroll')
def on_draft_reroll(data=None):
    sid = request.sid
    data = socket_guard('draft_reroll', data, require_player=True, allow_empty=True)
    if data is None:
        return
    pending_state = None
    pending_status_targets = None
    reject_message = None
    try:
        with _lock:
            if sid not in players:
                return
            player = players[sid]
            room_id = player.get('room_id')
            if room_id is None or room_id not in rooms:
                return
            room = rooms[room_id]
            pidx = room.player_index(sid)
            if pidx < 0:
                return
            engine = room.engine
            result = engine.draft_reroll(pidx)
            success = bool(result.get('success')) if isinstance(result, dict) else bool(result)
            if success:
                record_room_replay_action(room, 'draft_reroll', pidx, {})
                pending_state = (room, pidx)
                pending_status_targets = (
                    room,
                    [pi for pi in range(len(room.player_sids)) if pi != pidx],
                )
            else:
                reject_message = '无法刷新：当前不是选牌阶段或刷新次数已用完'
    except Exception as e:
        import traceback
        traceback.print_exc()
        return
    if pending_state:
        send_pregame_state(pending_state[0], pending_state[1])
    if pending_status_targets:
        send_pregame_status_update(pending_status_targets[0], targets=pending_status_targets[1])
    if reject_message:
        emit('server_error', {'message': reject_message})


@socketio.on('login')
@measure_socket_action('login')
def on_login(data):
    global _next_room_id
    sid = request.sid
    data = socket_guard('login', data, require_player=False, allow_empty=True, emit_error=False)
    if data is None:
        emit('login_fail', {'reason': '请求过于频繁或参数错误'})
        return
    if not rate_limiter(f'login-ip:{_client_ip()}', limit=20, window=60):
        _security_record('login_rate_ip', 'socket login IP rate limited', sid=sid, severity='high')
        emit('login_fail', {'reason': '登录过于频繁，请稍后再试'})
        return
    account_user = _current_account_user() if DB_AVAILABLE else None
    try:
        raw_name = validate_str(data.get('nickname', ''), max_len=64, name='nickname')
        preferred_mode = validate_str(data.get('mode', '1v1'), max_len=16, name='mode')
        desired_instance_id = validate_str(data.get('desired_instance_id', ''), max_len=96, pattern=r'[A-Za-z0-9_.:\-]*', name='desired_instance_id')
        desired_instance_port = validate_str(data.get('desired_instance_port', ''), max_len=8, pattern=r'[0-9]*', name='desired_instance_port')
        desired_room_text = validate_str(data.get('desired_room_id', ''), max_len=12, pattern=r'[0-9]*', name='desired_room_id')
        desired_match_key = validate_str(data.get('desired_match_key', ''), max_len=128, pattern=r'[A-Za-z0-9_.:\-]*', name='desired_match_key')
        desired_room_id = int(desired_room_text) if desired_room_text else None
    except ValueError as exc:
        _security_illegal(sid, 'login', str(exc), emit_error=False)
        emit('login_fail', {'reason': '登录参数错误'})
        return
    if (
        desired_instance_id
        and desired_instance_id != GTN_INSTANCE_ID
        and desired_instance_port
        and desired_instance_port != str(GTN_PORT)
    ):
        emit('login_fail', {
            'reason': 'instance_mismatch',
            'message': '当前对局属于另一个服务实例，正在切回原实例。',
            'requested_instance_id': desired_instance_id,
            'requested_instance_port': desired_instance_port,
            **instance_payload(),
        })
        return
    wants_account_login = bool(data.get('account_login'))
    client_beta_mode = bool(data.get('beta_mode'))
    is_beta_mode = is_beta_instance()
    if is_beta_instance() and not client_beta_mode:
        emit('login_fail', {'reason': 'This server only accepts beta clients'})
        return
    if is_release_instance() and client_beta_mode:
        emit('login_fail', {'reason': 'This server only accepts release clients'})
        return
    if is_beta_mode and not is_beta_authenticated():
        emit('login_fail', {'reason': '内测登录已过期，请重新输入内测秘钥'})
        return
    if account_user and account_user.get('banned'):
        session.pop('user_id', None)
        session.pop('username', None)
        status = get_user_ban_status(user_id=account_user.get('id'), username=account_user.get('username'))
        emit('login_fail', ban_error_payload(status) if status.get('banned') else {'reason': '账号已被封禁'})
        return
    if wants_account_login and not account_user:
        emit('login_fail', {'reason': 'Account session expired'})
        return
    if account_user:
        special_profile = get_special_account_profile(account_user['username'])
        name = special_profile['display_name'] if special_profile else account_user['username']
        is_admin_player = bool(special_profile and special_profile.get('is_admin_player'))
        user_id = account_user['id']
        is_registered_user = True
        skin_config = public_skin_config(account_user.get('skin'))
    else:
        special_profile = get_special_player_profile(raw_name)
        is_admin_player = bool(special_profile and special_profile.get('is_admin_player'))
        if special_profile:
            name = special_profile['display_name']
        else:
            name = sanitize_nickname(raw_name)
        if not special_profile and not validate_nickname(name):
            emit('login_fail', {'reason': 'Invalid nickname. Use 1-16 display-width characters; avoid pure numbers, pure symbols, or repeated -/_.'})
            return
        if not special_profile and check_nickname_risk(name, guest=True).get('blocked'):
            emit('login_fail', {'reason': '昵称中包含违禁词'})
            return
        if not special_profile and DB_AVAILABLE and get_user_by_username(name):
            emit('login_fail', {'reason': 'Registered nickname reserved'})
            return
        if not special_profile and is_reserved_special_nickname(name):
            emit('login_fail', {'reason': ADMIN_NICKNAME_RESERVED_REASON})
            return
        user_id = None
        is_registered_user = False
        skin_config = public_skin_config(data.get('skin'))
    if is_instance_draining():
        reconnect_allowed = False
        if _lock.acquire(timeout=0.2):
            try:
                reconnect_allowed = has_reconnect_candidate_locked(
                    nickname=name,
                    user_id=user_id,
                    account_player_id=account_user.get('player_id') if account_user else '',
                    beta_mode=is_beta_mode,
                    desired_room_id=desired_room_id,
                    desired_match_key=desired_match_key,
                )
            finally:
                _lock.release()
        if not reconnect_allowed:
            emit('login_fail', drain_reject_payload())
            return
    disabled_mods = ensure_valid_disabled_mods(normalize_disabled_mods_with_default(data.get('disabled_mods')))
    if preferred_mode not in PVP_MODES:
        preferred_mode = '1v1'
    try:
        community_fields, community_mod = resolve_community_loadout(data)
        loadout = build_mod_loadout(
            disabled_mods,
            community_mod=community_mod,
            community_hash=community_fields.get('community_mod_hash', ''),
            runtime_mode=preferred_mode,
        )
    except Exception as exc:
        emit('login_fail', {'reason': f'社区模组加载失败: {exc}'})
        return
    stale_disconnect_sessions = []
    if not _lock.acquire(timeout=0.5):
        snapshot = _lock.snapshot() if hasattr(_lock, 'snapshot') else {}
        admin_event('warning', f'login skipped: global lock busy held={snapshot.get("held_seconds", 0)}s')
        emit('login_fail', {'reason': '服务器正在处理上一项操作，请稍后重试'})
        return
    try:
        name_key = normalize_username_key(name)
        takeover_sids = []
        account_player_id = account_user.get('player_id') if account_user else ''
        client_ip = _client_ip()
        for old_sid, p in list(players.items()):
            if _can_take_over_online_session(
                p,
                name_key=name_key,
                user_id=user_id,
                account_player_id=account_player_id,
                beta_mode=is_beta_mode,
                client_ip=client_ip,
            ):
                takeover_sids.append(old_sid)
                continue
            if _same_login_identity(
                p,
                name_key=name_key,
                user_id=user_id,
                account_player_id=account_player_id,
                beta_mode=is_beta_mode,
            ):
                emit('login_fail', {'reason': 'Nickname already exists'})
                return
        for old_sid in takeover_sids:
            takeover_info = _take_over_online_session_locked(old_sid, reason='login_takeover')
            if takeover_info:
                stale_disconnect_sessions.append(takeover_info)
        reconnect_room, reconnect_old_sid = find_reconnect_candidate_locked(
            nickname=name,
            user_id=user_id,
            account_player_id=account_user.get('player_id') if account_user else '',
            beta_mode=is_beta_mode,
            desired_room_id=desired_room_id,
            desired_match_key=desired_match_key,
        )
        if reconnect_room and reconnect_old_sid not in reconnect_room.disconnected_players:
            profile = room_player_profile(reconnect_room, reconnect_old_sid)
            profile['disconnect_time'] = time.time()
            reconnect_room.disconnected_players[reconnect_old_sid] = dict(profile)
            admin_event('player', f'login restored reconnect metadata room={reconnect_room.room_id}', sid=reconnect_old_sid, room_id=reconnect_room.room_id)
        initial_status = 'reconnecting' if reconnect_room else 'lobby'
        login_now = time.time()
        next_lobby_afk_check_at = login_now + random.uniform(
            max(60, AFK_AUTO_MIN_SECONDS),
            max(max(60, AFK_AUTO_MIN_SECONDS), AFK_AUTO_MAX_SECONDS),
        )
        players[sid] = {
            'nickname': name,
            'ip': _client_ip(),
            'room_id': None,
            'status': initial_status,
            'login_at': login_now,
            'last_lobby_activity_at': login_now,
            'next_lobby_afk_check_at': next_lobby_afk_check_at,
            'mods_hash': loadout['mods_hash'],
            'loadout_hash': loadout['loadout_hash'],
            'v2_loadout_hash': loadout.get('v2_loadout_hash', ''),
            'v2_load_order': loadout.get('v2_load_order', []),
            'v2_mod_hashes': loadout.get('v2_mod_hashes', {}),
            'v2_ui_components': loadout.get('v2_ui_components', {}),
            'v2_loadout': loadout.get('v2_loadout'),
            'mods_list': loadout['mods_list'],
            'entertainment_mods': list(loadout.get('entertainment_mods', [])),
            'disabled_mods': loadout['disabled_mods'],
            'allowed_card_ids': loadout['allowed_card_ids'],
            'mode': preferred_mode,
            'is_admin_player': is_admin_player,
            'user_id': user_id,
            'account_player_id': account_user.get('player_id') if account_user else '',
            'is_registered_user': is_registered_user,
            'accept_game_invites': bool(account_user.get('accept_game_invites', True)) if account_user else True,
            'allow_guest_spectators': bool(account_user.get('allow_guest_spectators')) if account_user else False,
            'season_gr': account_user.get('season_gr') if account_user else None,
            'total_gr': account_user.get('total_gr') if account_user else None,
            'mod_source': community_fields.get('mod_source', 'official'),
            'community_mod_url': community_fields.get('community_mod_url', ''),
            'community_mod_hash': community_fields.get('community_mod_hash', ''),
            'community_mod_name': community_fields.get('community_mod_name', ''),
            'community_mods': community_fields.get('community_mods', []),
            'beta_mode': is_beta_mode,
            'skin': skin_config,
            'skin_look': dict(DEFAULT_SKIN_LOOK),
        }
        if special_profile:
            players[sid].update(special_public_fields(special_profile))
        admin_event('player', f'{"[beta] " if is_beta_mode else ""}{name} joined as {initial_status}', sid=sid, mode=preferred_mode)
    finally:
        _lock.release()
    takeover_notice = {
        'reason': '账号在其他位置进入大厅。\n如果该操作不是由本人进行，请修改密码。',
        'code': 'account_entered_elsewhere',
    }
    for takeover_info in stale_disconnect_sessions:
        old_sid = takeover_info.get('sid')
        if not old_sid:
            continue
        try:
            if takeover_info.get('user_id') or takeover_info.get('account_player_id'):
                socketio.emit('account_session_replaced', takeover_notice, room=old_sid)
                socketio.emit('kicked', takeover_notice, room=old_sid)
            socketio.server.disconnect(old_sid)
        except Exception as exc:
            admin_event('error', f'login takeover disconnect old sid failed: {exc}', sid=old_sid)
    if reconnect_room:
        reconnect_info = (
            reconnect_room.disconnected_players.get(reconnect_old_sid)
            or room_player_profile(reconnect_room, reconnect_old_sid)
            or {}
        )
        reconnect_pidx = int(reconnect_info.get('player_index', -1))
        opponent_nickname = '?'
        if reconnect_room.mode == '2v2' and hasattr(reconnect_room.engine, 'get_all_enemies'):
            enemy_ids = reconnect_room.engine.get_all_enemies(reconnect_pidx) if reconnect_pidx >= 0 else []
            opponent_nickname = ' / '.join(
                reconnect_room.engine.player_names[eid]
                for eid in enemy_ids
                if 0 <= eid < len(reconnect_room.engine.player_names)
            ) or '?'
        elif reconnect_pidx in (0, 1) and len(reconnect_room.engine.player_names) >= 2:
            opponent_nickname = reconnect_room.engine.player_names[1 - reconnect_pidx]
        emit('reconnect_available', {
            'room_id': reconnect_room.room_id,
            'old_sid': reconnect_old_sid,
            'opponent_nickname': opponent_nickname,
        })
    try:
        join_room(sid)
    except KeyError:
        # The browser can disconnect between login validation and the room join.
        # Treat it as a stale login attempt instead of letting Flask-SocketIO
        # raise through the handler and add noise during network instability.
        try:
            with _lock:
                players.pop(sid, None)
        except Exception:
            pass
        admin_event('player', 'login aborted: socket disconnected before lobby join', sid=sid)
        return
    login_payload = {
        'sid': sid,
        'nickname': name,
        'status': players.get(sid, {}).get('status', initial_status),
        'authenticated': bool(is_registered_user),
        'disabled_mods': players.get(sid, {}).get('disabled_mods', []),
        'mods_hash': players.get(sid, {}).get('mods_hash', ''),
        'loadout_hash': players.get(sid, {}).get('loadout_hash', '') or players.get(sid, {}).get('mods_hash', ''),
        'v2_loadout_hash': players.get(sid, {}).get('v2_loadout_hash', ''),
        'v2_load_order': players.get(sid, {}).get('v2_load_order', []),
        'mods_list': players.get(sid, {}).get('mods_list', []),
        'mod_source': players.get(sid, {}).get('mod_source', 'official'),
        'community_mod_url': players.get(sid, {}).get('community_mod_url', ''),
        'community_mod_hash': players.get(sid, {}).get('community_mod_hash', ''),
        'community_mod_name': players.get(sid, {}).get('community_mod_name', ''),
        'community_mods': players.get(sid, {}).get('community_mods', []),
        'beta_mode': players.get(sid, {}).get('beta_mode', False),
        'skin': players.get(sid, {}).get('skin', DEFAULT_PUBLIC_SKIN),
    }
    if is_registered_user:
        login_payload['user'] = auth_user_payload(account_user)
    login_payload.update(instance_payload())
    login_payload.update(special_public_fields(players.get(sid, {})))
    emit('login_ok', login_payload)
    broadcast_lobby()


@socketio.on('form_team')
def on_form_team(data):
    sid = request.sid
    data = socket_guard('form_team', data, require_player=True)
    if data is None:
        return
    try:
        target_sid = validate_socket_sid(data.get('target_sid'), name='target_sid')
    except ValueError as exc:
        _security_illegal(sid, 'form_team', str(exc))
        return
    with _lock:
        if sid not in players or target_sid not in players:
            return
        if not player_is_lobby_match_available(sid) or not player_is_lobby_match_available(target_sid):
            emit('server_error', {'message': '只有大厅中的玩家可以组队'})
            return
        if not player_accepts_game_invites(players[target_sid]):
            emit('server_error', {'message': '该玩家已关闭对局邀请', 'reason': 'game_invites_disabled'})
            return
        if players[sid].get('mode') != '2v2' or players[target_sid].get('mode') != '2v2':
            return
        if not same_runtime_scope_players(sid, target_sid):
            emit('server_error', {'message': runtime_scope_mismatch_message()})
            return
        if sid in teams or target_sid in teams:
            return
        socketio.emit('team_invite', {'from_sid': sid, 'from_name': players[sid]['nickname']}, room=target_sid)


@socketio.on('set_mode')
def on_set_mode(data):
    sid = request.sid
    data = socket_guard('set_mode', data, require_player=True)
    if data is None:
        return
    try:
        mode = validate_str(data.get('mode', '1v1'), min_len=1, max_len=16, name='mode')
    except ValueError as exc:
        _security_illegal(sid, 'set_mode', str(exc))
        return
    with _lock:
        if sid not in players:
            return
        if mode not in PVP_MODES:
            return
        players[sid]['mode'] = mode
        if mode != '2v2' and sid in teams:
            team = teams[sid]
            leader = team['leader']
            members = list(team['members'])
            keys_to_remove = [k for k in pending_team_matches if k[0] == leader or k[1] == leader]
            for k in keys_to_remove:
                del pending_team_matches[k]
            for member_sid in members:
                if member_sid in teams:
                    del teams[member_sid]
                if member_sid in players:
                    socketio.emit('team_disbanded', {}, room=member_sid)
        broadcast_lobby()


@socketio.on('update_mod_settings')
@measure_socket_action('update_mod_settings')
def on_update_mod_settings(data):
    sid = request.sid
    data = socket_guard('update_mod_settings', data, require_player=False, allow_empty=True)
    if data is None:
        return
    with _lock:
        if sid not in players:
            emit('mod_settings_updated', {
                'ok': False,
                'reason': '连接已失效，请重新进入大厅后再保存模组设置。',
                'disabled_mods': [],
            })
            return
        player = players[sid]
        if player.get('status') not in ('lobby', 'reconnecting'):
            emit('mod_settings_updated', {
                'ok': False,
                'reason': 'mod_settings_only_lobby',
                'disabled_mods': player.get('disabled_mods', []),
            })
            return
        current_disabled_mods = list(player.get('disabled_mods', []))
        runtime_mode = player.get('mode', '1v1')
    data = dict(data or {})
    data['_runtime_mode'] = runtime_mode
    try:
        community_fields, loadout = resolve_mod_loadout_payload(data)
    except Exception as exc:
        emit('mod_settings_updated', {
            'ok': False,
            'reason': str(exc),
            'disabled_mods': current_disabled_mods,
        })
        return
    with _lock:
        if sid not in players:
            emit('mod_settings_updated', {
                'ok': False,
                'reason': '连接已失效，请重新进入大厅后再保存模组设置。',
                'disabled_mods': current_disabled_mods,
            })
            return
        player = players[sid]
        if player.get('status') not in ('lobby', 'reconnecting'):
            emit('mod_settings_updated', {
                'ok': False,
                'reason': 'mod_settings_only_lobby',
                'disabled_mods': player.get('disabled_mods', []),
            })
            return
        old_hash = player_loadout_hash(player)
        apply_mod_loadout_to_player(player, loadout, community_fields)
        invites.pop(sid, None)
        for inviter_sid, target_sid in list(invites.items()):
            if target_sid == sid:
                del invites[inviter_sid]
        if sid in teams and old_hash != loadout['loadout_hash']:
            team = teams[sid]
            leader = team['leader']
            members = list(team['members'])
            for key in list(pending_team_matches):
                if key[0] == leader or key[1] == leader:
                    del pending_team_matches[key]
            for member_sid in members:
                if member_sid in teams:
                    del teams[member_sid]
                if member_sid in players:
                    socketio.emit('team_disbanded', {}, room=member_sid)
        emit('mod_settings_updated', {
            'ok': True,
            'disabled_mods': loadout['disabled_mods'],
            'loadout_hash': loadout['loadout_hash'],
            'v2_loadout_hash': loadout.get('v2_loadout_hash', ''),
            'v2_load_order': loadout.get('v2_load_order', []),
            'mods_list': loadout['mods_list'],
            'entertainment_mods': list(loadout.get('entertainment_mods', [])),
            'mod_source': player['mod_source'],
            'community_mod_hash': player['community_mod_hash'],
            'community_mod_name': player['community_mod_name'],
            'community_mods': player.get('community_mods', []),
        })
        broadcast_lobby()


@socketio.on('accept_team')
def on_accept_team(data):
    sid = request.sid
    data = socket_guard('accept_team', data, require_player=True)
    if data is None:
        return
    try:
        leader_sid = validate_socket_sid(data.get('from_sid'), name='from_sid')
    except ValueError as exc:
        _security_illegal(sid, 'accept_team', str(exc))
        return
    pending_loadout = None
    if has_mod_loadout_payload(data):
        try:
            pending_loadout = resolve_mod_loadout_payload(data)
        except Exception as exc:
            emit('server_error', {'message': f'模组设置保存失败：{exc}'})
            return
    with _lock:
        if sid not in players or leader_sid not in players:
            return
        if not player_is_lobby_match_available(sid) or not player_is_lobby_match_available(leader_sid):
            emit('server_error', {'message': '组队邀请已失效'})
            return
        if pending_loadout:
            community_fields, loadout = pending_loadout
            apply_mod_loadout_to_player(players[sid], loadout, community_fields)
        if not same_runtime_scope_players(sid, leader_sid):
            emit('server_error', {'message': runtime_scope_mismatch_message()})
            return
        if player_loadout_hash(players[sid]) != player_loadout_hash(players[leader_sid]):
            emit_mod_mismatch(sid, players[leader_sid])
            return
        if sid in teams or leader_sid in teams:
            return
        clear_pending_match_invites_for_sids_locked([leader_sid, sid])
        team_id = f"team_{leader_sid}"
        teams[leader_sid] = {'members': [leader_sid, sid], 'leader': leader_sid}
        teams[sid] = teams[leader_sid]
        for member_sid in [leader_sid, sid]:
            socketio.emit('team_formed', {
                'team_id': team_id,
                'members': [players[ms]['nickname'] for ms in teams[leader_sid]['members']],
                'member_sids': teams[leader_sid]['members'],
                'leader': leader_sid,
            }, room=member_sid)
        broadcast_lobby()


@socketio.on('decline_team')
def on_decline_team(data):
    sid = request.sid
    data = socket_guard('decline_team', data, require_player=True)
    if data is None:
        return
    try:
        leader_sid = validate_socket_sid(data.get('from_sid'), name='from_sid')
    except ValueError as exc:
        _security_illegal(sid, 'decline_team', str(exc))
        return
    with _lock:
        if leader_sid not in players:
            return
        socketio.emit('team_declined', {'from_name': players[sid]['nickname'] if sid in players else '?'}, room=leader_sid)


@socketio.on('leave_team')
def on_leave_team(data=None):
    sid = request.sid
    data = socket_guard('leave_team', data, require_player=True, allow_empty=True)
    if data is None:
        return
    with _lock:
        if sid not in teams:
            return
        team = teams[sid]
        leader = team['leader']
        members = list(team['members'])
        keys_to_remove = [k for k in pending_team_matches if k[0] == leader or k[1] == leader]
        for k in keys_to_remove:
            del pending_team_matches[k]
        for member_sid in members:
            if member_sid in teams:
                del teams[member_sid]
            if member_sid in players:
                socketio.emit('team_disbanded', {}, room=member_sid)
        broadcast_lobby()


@socketio.on('invite_team')
def on_invite_team(data):
    sid = request.sid
    data = socket_guard('invite_team', data, require_player=True)
    if data is None:
        return
    if reject_new_match_if_draining([sid], 'invite_team'):
        return
    try:
        target_team_leader = validate_socket_sid(data.get('target_team_leader'), name='target_team_leader')
    except ValueError as exc:
        _security_illegal(sid, 'invite_team', str(exc))
        return
    with _lock:
        if sid not in teams or target_team_leader not in teams:
            return
        my_team = teams[sid]
        target_team = teams[target_team_leader]
        all_invite_sids = list(my_team['members']) + list(target_team['members'])
        if any(not player_is_lobby_match_available(member_sid) for member_sid in all_invite_sids):
            emit('server_error', {'message': '只有全部位于大厅时才能邀请队伍'})
            return
        if any(
            member_sid in players and not player_accepts_game_invites(players[member_sid])
            for member_sid in target_team['members']
        ):
            emit('server_error', {'message': '对方队伍中有玩家已关闭对局邀请', 'reason': 'game_invites_disabled'})
            return
        if not same_runtime_scope_sids(all_invite_sids):
            emit('server_error', {'message': runtime_scope_mismatch_message()})
            return
        my_team_all_2v2 = all(players.get(ms, {}).get('mode') == '2v2' for ms in my_team['members'] if ms in players)
        target_team_all_2v2 = all(players.get(ms, {}).get('mode') == '2v2' for ms in target_team['members'] if ms in players)
        if not my_team_all_2v2 or not target_team_all_2v2:
            return
        all_match_sids = my_team['members'] + target_team['members']
        if not same_mod_loadout(all_match_sids):
            reference_sid = my_team['leader']
            reference_player = players.get(reference_sid, {})
            for msid in all_match_sids:
                if msid in players and player_loadout_hash(players[msid]) != player_loadout_hash(reference_player):
                    emit_mod_mismatch(msid, reference_player)
            emit_mod_mismatch(sid, players.get(target_team['leader'], reference_player))
            return
        match_key = (min(my_team['leader'], target_team['leader']),
                     max(my_team['leader'], target_team['leader']))
        if match_key in pending_team_matches:
            return
        inviter_preview = gr_preview_payload_for_sids('2v2', all_match_sids, sid)
        if not bool(data.get('confirmed')):
            socketio.emit('team_match_confirm_required', {
                'target_team_leader': target_team_leader,
                'target_team': [players[ms]['nickname'] for ms in target_team['members'] if ms in players],
                'target_team_sids': target_team['members'],
                'gr_preview': inviter_preview,
                'gr_preview_text': inviter_preview.get('text', ''),
            }, room=sid)
            return
        pending_team_matches[match_key] = True
        for member_sid in my_team['members']:
            if member_sid in players:
                preview = gr_preview_payload_for_sids('2v2', all_match_sids, member_sid)
                if preview.get('text'):
                    socketio.emit('invite_gr_preview', {'text': preview.get('text'), 'gr_preview': preview}, room=member_sid)
        for member_sid in target_team['members']:
            if member_sid in players:
                preview = gr_preview_payload_for_sids('2v2', all_match_sids, member_sid)
                socketio.emit('team_match_invite', {
                    'from_leader': my_team['leader'],
                    'from_team': [players[ms]['nickname'] for ms in my_team['members'] if ms in players],
                    'from_team_sids': my_team['members'],
                    'gr_preview_text': preview.get('text', ''),
                    'gr_preview': preview,
                }, room=member_sid)


@socketio.on('accept_team_match')
def on_accept_team_match(data):
    global _next_room_id
    sid = request.sid
    data = socket_guard('accept_team_match', data, require_player=True)
    if data is None:
        return
    try:
        from_leader = validate_socket_sid(data.get('from_leader'), name='from_leader')
    except ValueError as exc:
        _security_illegal(sid, 'accept_team_match', str(exc))
        return
    if reject_new_match_if_draining([sid, from_leader], 'accept_team_match'):
        return
    with _lock:
        if sid not in teams or from_leader not in teams:
            return
        my_team = teams[sid]
        other_team = teams[from_leader]
        if sid not in my_team['members']:
            return
        if from_leader not in other_team['members']:
            return
        match_key = (min(my_team['leader'], other_team['leader']),
                     max(my_team['leader'], other_team['leader']))
        all_sids = other_team['members'] + my_team['members']
        if any(not player_is_lobby_match_available(player_sid) for player_sid in all_sids):
            pending_team_matches.pop(match_key, None)
            emit_match_start_failed(all_sids, '队伍邀请已失效：有玩家已离开大厅')
            return
        pending_team_matches.pop(match_key, None)
        if not same_runtime_scope_sids(all_sids):
            emit_match_start_failed(all_sids, runtime_scope_mismatch_message(), reason='runtime_scope_mismatch')
            return
        if not same_mod_loadout(all_sids):
            reference_sid = all_sids[0]
            reference_player = players.get(reference_sid, {})
            for msid in all_sids:
                if msid in players and player_loadout_hash(players[msid]) != player_loadout_hash(reference_player):
                    emit_mod_mismatch(msid, reference_player)
            emit_match_start_failed(all_sids, '模组组合不一致，无法开始对局')
            return
        for member_sid in my_team['members']:
            if member_sid != sid and member_sid in players:
                socketio.emit('team_match_accepted', {}, room=member_sid)
        room_id = _next_room_id
        _next_room_id += 1
        allowed = None
        first_sid = all_sids[0]
        if first_sid in players and players[first_sid].get('allowed_card_ids'):
            allowed = players[first_sid]['allowed_card_ids']
        if allowed is not None:
            allowed = apply_runtime_content_filter(allowed, '2v2')
            pool_issue = runtime_card_pool_issue(allowed, '2v2')
            if pool_issue:
                emit_match_start_failed(all_sids, pool_issue, reason='content_temporarily_disabled')
                return
        clear_pending_match_invites_for_sids_locked(all_sids)
        room = GameRoom(room_id, all_sids, allowed, mode='2v2', beta_mode=bool(players[first_sid].get('beta_mode', False)))
        apply_v2_loadout_to_engine(room.engine, players.get(first_sid, {}), room.mode)
        rooms[room_id] = room
        admin_event('game', f"room {room_id} created mode=2v2: {' / '.join(players[s]['nickname'] for s in all_sids)}")
        for s in all_sids:
            players[s]['status'] = 'in_game'
            players[s]['room_id'] = room_id
            join_room(room_id)
            if s in teams:
                del teams[s]
        room.engine.player_names = [players[s]['nickname'] for s in all_sids]
        for idx, psid in enumerate(all_sids):
            room.store_player_profile(psid, idx, players.get(psid))
        room.engine.start_event_select_first()
        record_room_replay_keyframe(room, 'event_select_start')
        for i, s in enumerate(all_sids):
            emit_room_game_phase(room, s, 'event_select')
            send_event_state(room, i)
        broadcast_lobby()


@socketio.on('decline_team_match')
def on_decline_team_match(data):
    sid = request.sid
    data = socket_guard('decline_team_match', data, require_player=True)
    if data is None:
        return
    try:
        from_leader = validate_socket_sid(data.get('from_leader'), name='from_leader')
    except ValueError as exc:
        _security_illegal(sid, 'decline_team_match', str(exc))
        return
    with _lock:
        if from_leader not in teams:
            return
        other_team = teams[from_leader]
        my_team = teams.get(sid)
        if my_team:
            match_key = (min(my_team['leader'], other_team['leader']),
                         max(my_team['leader'], other_team['leader']))
            pending_team_matches.pop(match_key, None)
        for member_sid in other_team['members']:
            if member_sid in players:
                socketio.emit('team_match_declined', {'from_name': players[sid]['nickname'] if sid in players else '?'}, room=member_sid)


@socketio.on('disconnect')
def on_disconnect():
    global _next_room_id
    sid = request.sid
    pending_emits = []  # Collect emits to perform outside the lock
    try:
        with _lock:
            if sid not in players:
                return
            player = players[sid]
            mark_player_session_last_seen_locked(player, exclude_sid=sid)
            solo_sessions.pop(sid, None)
            tutorial_sessions.discard(sid)
            room_id = player.get('room_id')
            nickname = player['nickname']
            admin_event('player', f'{nickname} disconnected', sid=sid, room_id=room_id)
            if room_id is not None and room_id in rooms:
                room = rooms[room_id]
                pidx = room.player_index(sid)
                if pidx >= 0 and room.engine.phase not in ('game_over',):
                    profile = room.store_player_profile(sid, pidx, player)
                    profile['disconnect_time'] = time.time()
                    dead_2v2_player = room.mode == '2v2' and _room_player_dead(room, pidx)
                    if not dead_2v2_player:
                        disconnect_attempt, reconnect_timeout_seconds = room.allocate_reconnect_timeout(pidx)
                        profile['disconnect_attempt'] = disconnect_attempt
                        profile['reconnect_timeout'] = reconnect_timeout_seconds
                    room.disconnected_players[sid] = dict(profile)
                    current_phase = getattr(room.engine, 'phase', '')
                    pregame_disconnect = current_phase in ('draft', 'event_select', 'event_reveal')
                    unblocked_pending = False
                    if not dead_2v2_player:
                        unblocked_pending = _resolve_disconnect_blockers(room, pidx)
                    admin_event(
                        'player',
                        f'{nickname} disconnect flow room={room_id} phase={current_phase} pregame={pregame_disconnect} '
                        f'dead_2v2={dead_2v2_player} attempt={profile.get("disconnect_attempt", 0)} '
                        f'timeout={profile.get("reconnect_timeout", 0)}',
                        sid=sid,
                        room_id=room_id,
                    )
                    if not dead_2v2_player:
                        if reconnect_timeout_seconds > 0:
                            for other_sid in room.player_sids:
                                if other_sid != sid and other_sid in players:
                                    pending_emits.append(('opponent_disconnected', {
                                        'reconnect_timeout': reconnect_timeout_seconds,
                                        'disconnect_attempt': disconnect_attempt,
                                        'wait_forever': False,
                                        'opponent_nickname': nickname,
                                    }, other_sid))
                        timer = threading.Timer(float(reconnect_timeout_seconds), reconnect_timeout, args=[room_id, sid])
                        room.reconnect_timers[sid] = timer
                        timer.daemon = True
                        timer.start()
                    del players[sid]
                    if dead_2v2_player or unblocked_pending:
                        pending_emits.append(('broadcast_game_state', room, None))
                        pending_emits.append(('emit_pending_response_requests', room, None))
                    pending_emits.append(('broadcast_lobby', None, None))
                elif pidx >= 0 and room.engine.phase == 'game_over':
                    room._rematch_votes.discard(sid)
                    for other_sid in room.player_sids:
                        if other_sid != sid and other_sid in players:
                            pending_emits.append(('opponent_disconnected', {'timeout': True}, other_sid))
                    if not any(s in room.disconnected_players for s in room.player_sids if s != sid):
                        for t in room.reconnect_timers.values():
                            t.cancel()
                        _cancel_game_over_cleanup_timer(room)
                        del rooms[room_id]
                    else:
                        for other_sid in room.player_sids:
                            if other_sid != sid and other_sid in players:
                                players[other_sid]['room_id'] = None
                                players[other_sid]['status'] = 'lobby'
                        for t in room.reconnect_timers.values():
                            t.cancel()
                        _cancel_game_over_cleanup_timer(room)
                        del rooms[room_id]
                if pidx < 0 and player.get('spectating_room') is not None:
                    spec_room_id = player['spectating_room']
                    if spec_room_id is not None and spec_room_id in rooms:
                        spec_room = rooms[spec_room_id]
                        if sid in spec_room.spectators:
                            spec_room.spectators.remove(sid)
                    player['spectating_room'] = None
                    player['spectate_perspective'] = 0
            for inv_sid, target_sid in list(invites.items()):
                if inv_sid == sid or target_sid == sid:
                    del invites[inv_sid]
            if sid in players:
                del players[sid]
    except Exception as exc:
        admin_event('error', f'on_disconnect error: {exc}')
    # Perform all emits outside the lock
    for emit_item in pending_emits:
        try:
            if emit_item[0] == 'opponent_disconnected':
                socketio.emit('opponent_disconnected', emit_item[1], room=emit_item[2])
            elif emit_item[0] == 'server_error':
                socketio.emit('server_error', emit_item[1], room=emit_item[2])
            elif emit_item[0] == 'game_phase':
                socketio.emit('game_phase', emit_item[1], room=emit_item[2])
            elif emit_item[0] == 'broadcast_game_state':
                broadcast_game_state(emit_item[1])
            elif emit_item[0] == 'emit_pending_response_requests':
                emit_pending_response_requests(emit_item[1])
            elif emit_item[0] == 'broadcast_lobby':
                broadcast_lobby()
        except Exception as exc:
            admin_event('error', f'on_disconnect emit error: {exc}')


@socketio.on('reconnect_accept')
def on_reconnect_accept(data):
    global _next_room_id
    sid = request.sid
    data = socket_guard('reconnect_accept', data, require_player=True)
    if data is None:
        return
    try:
        room_id = validate_int(data.get('room_id'), minimum=0, maximum=10**9, name='room_id')
        old_sid = validate_socket_sid(data.get('old_sid'), name='old_sid')
    except ValueError as exc:
        _security_illegal(sid, 'reconnect_accept', str(exc))
        return
    room = None
    pidx = -1
    other_sids = []
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        if room_id is None or room_id not in rooms:
            player['status'] = 'lobby'
            return
        room = rooms[room_id]
        if bool(getattr(room, 'beta_mode', False)) != bool(player.get('beta_mode', False)):
            player['status'] = 'lobby'
            return
        if getattr(room.engine, 'game_over', False) or getattr(room.engine, 'phase', '') == 'game_over':
            player['status'] = 'lobby'
            player['room_id'] = None
            return
        if old_sid not in room.disconnected_players:
            fallback_old_sid = _find_disconnected_sid_for_player(room, player)
            if fallback_old_sid:
                old_sid = fallback_old_sid
        if old_sid not in room.disconnected_players:
            profile = room_player_profile(room, old_sid)
            if old_sid in getattr(room, 'player_sids', []) and profile.get('nickname') not in ('?', ''):
                room.disconnected_players[old_sid] = dict(profile)
                room.disconnected_players[old_sid]['disconnect_time'] = time.time()
                admin_event('player', f'restored missing disconnected profile for reconnect room={room_id}', sid=old_sid, room_id=room_id)
            else:
                player['status'] = 'lobby'
                admin_event('error', f'reconnect_accept failed: no metadata for old_sid={old_sid} room={room_id}', sid=sid, room_id=room_id)
                return
        dc_info = room.disconnected_players[old_sid]
        same_identity = (
            (player.get('user_id') and dc_info.get('user_id') == player.get('user_id'))
            or (player.get('account_player_id') and str(dc_info.get('account_player_id') or '') == str(player.get('account_player_id') or ''))
            or normalize_username_key(dc_info.get('nickname', '')) == normalize_username_key(player.get('nickname', ''))
        )
        if not same_identity:
            player['status'] = 'lobby'
            return
        if old_sid in room.reconnect_timers:
            room.reconnect_timers[old_sid].cancel()
            del room.reconnect_timers[old_sid]
        if hasattr(room, 'both_dc_timer') and room.both_dc_timer:
            room.both_dc_timer.cancel()
            room.both_dc_timer = None
        pidx = dc_info['player_index']
        room.player_sids[pidx] = sid
        room.player_profiles.pop(old_sid, None)
        room.store_player_profile(sid, pidx, player)
        del room.disconnected_players[old_sid]
        player['room_id'] = room_id
        player['status'] = 'in_game'
        player['skin_look'] = normalize_skin_look(dc_info.get('skin_look'))
        player.update(special_public_fields(dc_info))
        other_sids = [
            other_sid for other_sid in room.player_sids
            if other_sid != sid and other_sid in players
        ]
    # Socket emits and pending-interaction recovery can yield or acquire the
    # global lock again. Keep them outside the state-mutation critical section.
    join_room(room_id)
    for other_sid in other_sids:
        socketio.emit('opponent_reconnected', {}, room=other_sid)
    send_game_state_to(room, pidx)
    emit_pending_interaction_after_state_change(room, reason='player_reconnected')
    broadcast_lobby()


@socketio.on('reconnect_decline')
def on_reconnect_decline(data):
    global _next_room_id
    sid = request.sid
    data = socket_guard('reconnect_decline', data, require_player=True)
    if data is None:
        return
    try:
        room_id = validate_int(data.get('room_id'), minimum=0, maximum=10**9, name='room_id')
        old_sid = validate_socket_sid(data.get('old_sid'), name='old_sid')
    except ValueError as exc:
        _security_illegal(sid, 'reconnect_decline', str(exc))
        return
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        if room_id is None or room_id not in rooms:
            player['status'] = 'lobby'
            return
        room = rooms[room_id]
        if bool(getattr(room, 'beta_mode', False)) != bool(player.get('beta_mode', False)):
            player['status'] = 'lobby'
            player['room_id'] = None
            return
        if room.mode == '2v2':
            dc_info = room.disconnected_players.get(old_sid, {})
            dc_pidx = int(dc_info.get('player_index', -1)) if dc_info else -1
            if _room_player_dead(room, dc_pidx):
                if old_sid in room.reconnect_timers:
                    room.reconnect_timers[old_sid].cancel()
                    del room.reconnect_timers[old_sid]
                room.disconnected_players.pop(old_sid, None)
                player['status'] = 'lobby'
                player['room_id'] = None
                broadcast_lobby()
                return
        if old_sid in room.disconnected_players:
            dc_info = room.disconnected_players.get(old_sid, {})
            dc_pidx = int(dc_info.get('player_index', -1)) if dc_info else -1
            if old_sid in room.reconnect_timers:
                room.reconnect_timers[old_sid].cancel()
                del room.reconnect_timers[old_sid]
            dc_name = dc_info.get('nickname', player.get('nickname', '?'))
            if room.mode == '2v2':
                room.disconnected_players.pop(old_sid, None)
                _force_2v2_disconnect_death(room, dc_pidx, dc_name, '放弃重连')
                ended = bool(getattr(room.engine, 'game_over', False))
                record_room_replay_action(room, 'reconnect_decline', dc_pidx, {
                    'nickname': dc_name,
                    'game_over': ended,
                    'player_defeated': True,
                })
                if ended:
                    _cancel_room_reconnect_timers(room)
                    for other_sid in room.player_sids:
                        if other_sid in players:
                            socketio.emit('opponent_disconnected', {'timeout': True, 'game_over': True}, room=other_sid)
                            socketio.emit('game_phase', {'phase': 'game_over'}, room=other_sid)
                else:
                    for other_sid in room.player_sids:
                        if other_sid in players:
                            socketio.emit('opponent_disconnected', {
                                'timeout': True,
                                'game_over': False,
                                'stay': True,
                                'player_defeated': True,
                                'opponent_nickname': dc_name,
                            }, room=other_sid)
                broadcast_game_state(room)
            else:
                room.disconnected_players.pop(old_sid, None)
                disconnected_teams = _room_disconnected_teams(room)
                if len(disconnected_teams) >= 2:
                    ended = _finish_room_by_health_tiebreak(room, '双方放弃重连')
                else:
                    ended = _finish_room_by_forfeit(
                        room,
                        dc_pidx,
                        dc_name,
                        '放弃重连',
                    )
                record_room_replay_action(room, 'reconnect_decline', dc_pidx, {
                    'nickname': dc_name,
                    'game_over': ended,
                })
                if ended:
                    _cancel_room_reconnect_timers(room)
                    for other_sid in room.player_sids:
                        if other_sid in players:
                            socketio.emit('opponent_disconnected', {'timeout': True, 'game_over': True}, room=other_sid)
                            socketio.emit('game_phase', {'phase': 'game_over'}, room=other_sid)
                    broadcast_game_state(room)
        player['status'] = 'lobby'
        player['room_id'] = None
    broadcast_lobby()


@socketio.on('invite')
def on_invite(data):
    sid = request.sid
    data = socket_guard('invite', data, require_player=True)
    if data is None:
        return
    if reject_new_match_if_draining([sid], 'invite'):
        return
    try:
        target_sid = validate_socket_sid(data.get('target_sid'), name='target_sid')
    except ValueError as exc:
        _security_illegal(sid, 'invite', str(exc))
        return
    target_name = '?'
    inviter_name = '?'
    inviter_mode = '1v1'
    match_sids = [sid, target_sid]
    mod_mismatch_payload = None
    with _lock:
        if sid not in players or target_sid not in players:
            _security_illegal(sid, 'invite', '目标玩家不存在', severity='low')
            emit('server_error', {'message': '目标玩家不存在'})
            return
        if sid == target_sid:
            _security_illegal(sid, 'invite', '不能邀请自己', severity='low')
            return
        if sid in invites:
            return
        inviter = players[sid]
        if not player_is_lobby_match_available(sid):
            emit('server_error', {'message': '只有大厅中的玩家可以发送邀请'})
            return
        target = players[target_sid]
        if not player_is_lobby_match_available(target_sid):
            emit('server_error', {'message': '目标玩家不在大厅'})
            return
        if not player_accepts_game_invites(target):
            emit('server_error', {'message': '该玩家已关闭对局邀请', 'reason': 'game_invites_disabled'})
            return
        if not same_runtime_scope_players(inviter, target):
            emit('server_error', {'message': runtime_scope_mismatch_message()})
            return
        inviter_mode = inviter.get('mode', '1v1')
        target_mode = target.get('mode', '1v1')
        if inviter_mode not in DUEL_INVITE_MODES or target_mode != inviter_mode:
            emit('server_error', {'message': '双方模式不一致，无法邀请'})
            return
        if player_loadout_hash(inviter) != player_loadout_hash(target):
            message = '模组组合不一致，无法开始对局'
            mod_mismatch_payload = {
                'message': message,
                'reason': 'mod_mismatch',
                'your_mods': player_mod_match_payload(inviter),
                'other_mods': player_mod_match_payload(target),
            }
        else:
            inviter_name = inviter.get('nickname', '?')
            target_name = target.get('nickname', '?')
    if mod_mismatch_payload is not None:
        socketio.emit('mod_mismatch', mod_mismatch_payload, room=sid)
        socketio.emit('server_error', {'message': mod_mismatch_payload['message'], 'reason': 'mod_mismatch'}, room=sid)
        return

    inviter_gr_preview = gr_preview_payload_for_sids(inviter_mode, match_sids, sid)
    target_gr_preview = gr_preview_payload_for_sids(inviter_mode, match_sids, target_sid)
    if not bool(data.get('confirmed')):
        socketio.emit('invite_confirm_required', {
            'target_sid': target_sid,
            'target_name': target_name,
            'mode': inviter_mode,
            'gr_preview_text': inviter_gr_preview.get('text', ''),
            'gr_preview': inviter_gr_preview,
        }, room=sid)
        return

    with _lock:
        if sid not in players or target_sid not in players:
            emit('server_error', {'message': '目标玩家不存在'})
            return
        if sid in invites:
            return
        inviter = players[sid]
        target = players[target_sid]
        if not player_is_lobby_match_available(sid):
            emit('server_error', {'message': '只有大厅中的玩家可以发送邀请'})
            return
        if not player_is_lobby_match_available(target_sid):
            emit('server_error', {'message': '目标玩家不在大厅'})
            return
        if not player_accepts_game_invites(target):
            emit('server_error', {'message': '该玩家已关闭对局邀请', 'reason': 'game_invites_disabled'})
            return
        if not same_runtime_scope_players(inviter, target):
            emit('server_error', {'message': runtime_scope_mismatch_message()})
            return
        if inviter.get('mode', '1v1') != inviter_mode or target.get('mode', '1v1') != inviter_mode:
            emit('server_error', {'message': '双方模式不一致，无法邀请'})
            return
        if player_loadout_hash(inviter) != player_loadout_hash(target):
            emit('server_error', {'message': '模组组合不一致，无法开始对局', 'reason': 'mod_mismatch'})
            return
        invites[sid] = target_sid
        inviter_name = inviter.get('nickname', inviter_name)

    if inviter_gr_preview.get('text'):
        socketio.emit('invite_gr_preview', {'text': inviter_gr_preview.get('text'), 'gr_preview': inviter_gr_preview}, room=sid)
    socketio.emit('invite_received', {
        'inviter_sid': sid,
        'inviter_name': inviter_name,
        'gr_preview_text': target_gr_preview.get('text', ''),
        'gr_preview': target_gr_preview,
    }, room=target_sid)

    def _invite_timeout(inviter_sid):
        with _lock:
            if inviter_sid in invites:
                del invites[inviter_sid]

    timer = threading.Timer(30.0, _invite_timeout, args=[sid])
    timer.daemon = True
    timer.start()


@socketio.on('accept_invite')
def on_accept_invite(data):
    global _next_room_id
    sid = request.sid
    data = socket_guard('accept_invite', data, require_player=True)
    if data is None:
        return
    try:
        inviter_sid = validate_socket_sid(data.get('inviter_sid'), name='inviter_sid')
    except ValueError as exc:
        _security_illegal(sid, 'accept_invite', str(exc))
        return
    if reject_new_match_if_draining([sid, inviter_sid], 'accept_invite'):
        return
    pending_loadout = None
    if has_mod_loadout_payload(data):
        try:
            pending_loadout = resolve_mod_loadout_payload(data)
        except Exception as exc:
            emit('server_error', {'message': f'模组设置保存失败：{exc}'})
            return
    with _lock:
        if inviter_sid not in players or sid not in players:
                    return
        if inviter_sid not in invites or invites[inviter_sid] != sid:
                    return
        del invites[inviter_sid]
        inviter = players[inviter_sid]
        accepter = players[sid]
        if not player_is_lobby_match_available(inviter_sid) or not player_is_lobby_match_available(sid):
            emit('server_error', {'message': '邀请已失效：有玩家已离开大厅'})
            return
        if pending_loadout:
            community_fields, loadout = pending_loadout
            apply_mod_loadout_to_player(accepter, loadout, community_fields)
        if not same_runtime_scope_players(inviter, accepter):
            emit_match_start_failed([inviter_sid, sid], runtime_scope_mismatch_message(), reason='runtime_scope_mismatch')
            return
        if player_loadout_hash(inviter) != player_loadout_hash(accepter):
            emit_mod_mismatch(inviter_sid, accepter)
            emit_mod_mismatch(sid, inviter)
            return
        room_id = _next_room_id
        _next_room_id += 1
        allowed_card_ids = inviter.get('allowed_card_ids') or get_allowed_card_ids(inviter.get('disabled_mods', []))
        allowed_card_ids = apply_runtime_content_filter(allowed_card_ids, inviter.get('mode', '1v1'))
        pool_issue = runtime_card_pool_issue(allowed_card_ids, inviter.get('mode', '1v1'))
        if pool_issue:
            emit_match_start_failed([inviter_sid, sid], pool_issue, reason='content_temporarily_disabled')
            return
        clear_pending_match_invites_for_sids_locked([inviter_sid, sid])
        room = GameRoom(room_id, [inviter_sid, sid], allowed_card_ids, mode=inviter.get('mode', '1v1'), beta_mode=bool(inviter.get('beta_mode', False)))
        apply_v2_loadout_to_engine(room.engine, inviter, room.mode)
        rooms[room_id] = room
        admin_event('game', f"room {room_id} created mode={room.mode}: {inviter['nickname']} vs {accepter['nickname']}")
        inviter['room_id'] = room_id
        inviter['status'] = 'in_game'
        accepter['room_id'] = room_id
        accepter['status'] = 'in_game'
        room.engine.player_names = [inviter['nickname'], accepter['nickname']]
        room.store_player_profile(inviter_sid, 0, inviter)
        room.store_player_profile(sid, 1, accepter)
        if room.mode == 'urf':
            room.engine.start_game()
            room.started_at = time.time()
            record_room_replay_keyframe(room, 'game_start')
            admin_event('game', f'room {room_id} started mode={room.mode}')
            for psid in room.player_sids:
                emit_room_game_phase(room, psid, 'playing')
            broadcast_game_state(room)
        elif room.mode == 'random_deck':
            try:
                start_random_deck_room(room)
            except Exception as exc:
                rooms.pop(room_id, None)
                inviter['room_id'] = None
                inviter['status'] = 'lobby'
                accepter['room_id'] = None
                accepter['status'] = 'lobby'
                emit_match_start_failed([inviter_sid, sid], f'随机卡组生成失败：{exc}')
                return
        else:
            room.engine.start_event_select_first()
            record_room_replay_keyframe(room, 'event_select_start')
            for pidx in range(len(room.player_sids)):
                psid = room.player_sids[pidx]
                emit_room_game_phase(room, psid, 'event_select')
                send_event_state(room, pidx)
    broadcast_lobby()


@socketio.on('decline_invite')
def on_decline_invite(data):
    sid = request.sid
    data = socket_guard('decline_invite', data, require_player=True)
    if data is None:
        return
    try:
        inviter_sid = validate_socket_sid(data.get('inviter_sid'), name='inviter_sid')
    except ValueError as exc:
        _security_illegal(sid, 'decline_invite', str(exc))
        return
    with _lock:
        if inviter_sid in invites and invites[inviter_sid] == sid:
            del invites[inviter_sid]
            if inviter_sid in players:
                socketio.emit('invite_declined', {'target_sid': sid}, room=inviter_sid)


@socketio.on('chat')
def on_chat(data):
    sid = request.sid
    data = socket_guard('chat', data, require_player=True, allow_empty=False)
    if data is None:
        return
    now = time.time()
    if not _lock.acquire(timeout=0.2):
        admin_event('warning', 'chat skipped: global lock busy')
        emit('server_error', {'message': '服务器正在处理上一项操作，请稍后重试'})
        return
    try:
        if sid not in players:
            return
        player_snapshot = copy.deepcopy(players[sid])
    finally:
        _lock.release()

    mute_key = chat_mute_key(sid, player_snapshot)
    if is_muted(mute_key):
        emit('server_error', muted_error_payload(mute_remaining_seconds(mute_key)))
        _security_record('chat_muted_attempt', 'muted player tried to chat', sid=sid, severity='low')
        return
    if DB_AVAILABLE and player_snapshot.get('user_id'):
        try:
            muted, mute_info = is_user_muted_db(player_snapshot.get('user_id'))
        except Exception as exc:
            admin_event('error', f'failed to check chat mute: {exc}')
            muted, mute_info = False, {}
        if muted:
            remaining = 0
            try:
                until_dt = datetime.fromisoformat(str(mute_info.get('muted_until') or '').replace('Z', '+00:00'))
                remaining = max(0, int((until_dt - datetime.now(timezone.utc)).total_seconds()))
            except Exception:
                remaining = 0
            emit('server_error', muted_error_payload(remaining))
            _security_record('chat_muted_attempt', 'db-muted player tried to chat', sid=sid, severity='low', extra=mute_info)
            return

    exempt = is_chat_limit_exempt(player_snapshot)
    if not exempt:
        if not rate_limiter(f'chat-fast:{mute_key}', limit=1, window=2):
            _security_record('chat_fast_rate', 'chat sent faster than 1 per 2 seconds', sid=sid, severity='low')
            emit('server_error', {'message': '聊天发送过快'})
            return
        if not rate_limiter(f'chat-burst:{mute_key}', limit=5, window=10):
            _security_record('chat_burst_rate', 'chat sent faster than 5 per 10 seconds', sid=sid, severity='medium')
            emit('server_error', {'message': '聊天发送过快'})
            return
    try:
        text, chat_risk = _validate_chat_text_for_sender(data.get('text', ''), exempt=exempt)
    except ValueError as exc:
        _security_illegal(sid, 'chat', str(exc), severity='low')
        return
    if not text:
        return

    risk = chat_risk.get('risk') or {}
    risk_level = int(chat_risk.get('risk_level') or 0)
    risk_action = str(chat_risk.get('risk_action') or '')
    matched_rules = list(chat_risk.get('matched_rules') or [])
    normalized_message = chat_risk.get('normalized_message') or normalize_message(text)
    if risk_action == 'reject_mute' or risk_level >= 4:
        if DB_AVAILABLE:
            try:
                room_id = player_snapshot.get('room_id')
                spectating_room = player_snapshot.get('spectating_room')
                record_chat_message(
                    f'room:{room_id}' if room_id is not None else ('spectate' if spectating_room is not None else f'lobby:{_lobby_chat_scope_key(player_snapshot.get("beta_mode", False))}'),
                    str(data.get('channel') or 'public')[:40],
                    player_snapshot.get('user_id'),
                    player_snapshot.get('nickname', ''),
                    text,
                    normalized_message,
                    risk_level,
                    hidden=True,
                )
            except Exception as exc:
                admin_event('error', f'failed to record rejected chat: {exc}')
        mute_user(mute_key, 300, 'severe chat risk')
        if DB_AVAILABLE and player_snapshot.get('user_id'):
            try:
                set_user_mute(player_snapshot.get('user_id'), player_snapshot.get('nickname', ''), 300, 'severe chat risk', 'system')
            except Exception as exc:
                admin_event('error', f'failed to persist severe chat mute: {exc}')
        _security_record('chat_rejected', 'severe chat risk rejected', sid=sid, severity='high', extra={'rules': matched_rules})
        emit('server_error', muted_error_payload(300, message='消息包含高风险内容，已被拦截并临时禁言'))
        return
    if risk_action == 'mask_flag' or risk_level >= 3:
        text = risk.get('sanitized_text') or text

    nickname = player_snapshot.get('nickname', '')
    is_spectator = player_snapshot.get('status') == 'spectating'
    chat_data = {
        'nickname': nickname,
        'text': text,
        'is_spectator': is_spectator,
        'risk_level': risk_level,
        'risk_action': risk_action,
        'user_id': player_snapshot.get('user_id'),
    }
    if matched_rules:
        chat_data['matched_rules'] = matched_rules[:5]
    chat_data.update(special_public_fields(player_snapshot))

    def player_name_at(room, pidx):
        if not isinstance(pidx, int) or pidx < 0 or pidx >= len(room.player_sids):
            return '?'
        psid = room.player_sids[pidx]
        return room_player_nickname(room, psid, '?')

    record_room_key = None
    record_channel = 'public'
    recipients = []
    lobby_payloads = None
    error_payload = None
    security_note = None
    security_severity = 'medium'
    room_scope = None
    room_scope_id = None
    room_chat_local_id = None

    if not _lock.acquire(timeout=0.2):
        admin_event('warning', 'chat route skipped: global lock busy')
        emit('server_error', {'message': '服务器正在处理上一项操作，请稍后重试'})
        return
    try:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        spectating_room = player.get('spectating_room')
        if room_id is not None and room_id in rooms:
            room = rooms[room_id]
            pidx = room.player_index(sid)
            recipients = list(room.player_sids) + list(room.spectators)
            channel = str(data.get('channel') or 'public')
            if room.mode == '2v2' and pidx >= 0:
                if channel not in ('public', 'team', 'enemy', 'private'):
                    channel = 'public'
                chat_data['chat_channel'] = channel
                teammate_id = room.engine.get_teammate(pidx) if hasattr(room.engine, 'get_teammate') else -1
                enemy_ids = room.engine.get_all_enemies(pidx) if hasattr(room.engine, 'get_all_enemies') else []
                if channel == 'team':
                    recipients = [sid]
                    if 0 <= teammate_id < len(room.player_sids):
                        recipients.append(room.player_sids[teammate_id])
                elif channel == 'enemy':
                    recipients = [sid] + [room.player_sids[eid] for eid in enemy_ids if 0 <= eid < len(room.player_sids)]
                elif channel == 'private':
                    try:
                        target_pidx = validate_int(data.get('target_player_id'), default=-1, minimum=-1, maximum=16, name='target_player_id')
                    except ValueError:
                        target_pidx = -1
                    if target_pidx not in enemy_ids or target_pidx < 0 or target_pidx >= len(room.player_sids):
                        _security_illegal(sid, 'chat', 'Invalid chat target', severity='medium')
                        return
                    chat_data['chat_target_player_id'] = target_pidx
                    chat_data['chat_target_name'] = player_name_at(room, target_pidx)
                    recipients = [sid, room.player_sids[target_pidx]]
            if not check_chat_rate_locked(sid, player, now):
                security_note = 'room chat rate limited'
                error_payload = {'message': '聊天发送过快'}
                mute_user(mute_key, 60, 'chat rate limit')
            else:
                record_room_key = f'room:{room.room_id}'
                record_channel = chat_data.get('chat_channel') or channel or 'public'
                room_scope = 'room'
                room_scope_id = room.room_id
                append_admin_game_chat_locked(chat_data, now, scope='room', room_id=room.room_id)
                room_chat_local_id = append_room_chat_locked(
                    room,
                    chat_data,
                    now,
                    recipients=recipients,
                    spectator_visible=(record_channel == 'public'),
                    pregame=room.engine.phase in ('draft', 'event_select', 'event_reveal', 'event_sub_choice', 'sub_choice'),
                )
        elif spectating_room is not None and spectating_room in rooms:
            room = rooms[spectating_room]
            if room.mode == '2v2':
                chat_data['chat_channel'] = 'public'
            if not check_chat_rate_locked(sid, player, now):
                security_note = 'spectator chat rate limited'
                error_payload = {'message': '聊天发送过快'}
                mute_user(mute_key, 60, 'chat rate limit')
            else:
                recipients = list(room.player_sids) + list(room.spectators)
                record_room_key = f'room:{room.room_id}:spectate'
                record_channel = chat_data.get('chat_channel') or 'public'
                room_scope = 'spectate'
                room_scope_id = room.room_id
                append_admin_game_chat_locked(chat_data, now, scope='spectate', room_id=room.room_id)
                room_chat_local_id = append_room_chat_locked(
                    room,
                    chat_data,
                    now,
                    recipients=recipients,
                    spectator_visible=True,
                    pregame=room.engine.phase in ('draft', 'event_select', 'event_reveal', 'event_sub_choice', 'sub_choice'),
                )
        else:
            beta_mode = bool(player.get('beta_mode', False))
            mentions = _extract_lobby_mentions(text, beta_mode=beta_mode)
            if mentions and not exempt:
                mention_key = f"mention:{chat_rate_key(sid, player)}"
                if not rate_limiter(mention_key, limit=MENTION_RATE_LIMIT, window=60):
                    security_note = 'lobby mention rate limited'
                    error_payload = {'message': '@发送过快'}
            if not error_payload:
                if mentions:
                    chat_data['mentions'] = [
                        {
                            'user_id': item.get('user_id'),
                            'nickname': item.get('nickname'),
                            'player_id': item.get('player_id'),
                        }
                        for item in mentions
                    ]
                    chat_data['mention_user_ids'] = [item.get('user_id') for item in mentions if item.get('user_id')]
                    chat_data['mention_names'] = [item.get('nickname') for item in mentions if item.get('nickname')]
                will_fold = lobby_chat_would_fold_locked(chat_data, now, beta_mode=beta_mode)
                if not will_fold and not check_chat_rate_locked(sid, player, now):
                    security_note = 'lobby chat rate limited'
                    error_payload = {'message': '聊天发送过快'}
                    mute_user(mute_key, 60, 'chat rate limit')
                else:
                    record_room_key = f'lobby:{_lobby_chat_scope_key(beta_mode)}'
                    record_channel = 'public'
                    append_lobby_chat_locked(chat_data, now, beta_mode=beta_mode)
                    append_admin_game_chat_locked(chat_data, now, scope='lobby')
                    lobby_payloads = lobby_chat_history_payloads_locked(LOBBY_CHAT_VISIBLE_LIMIT, beta_mode=beta_mode)
    finally:
        _lock.release()

    if security_note:
        _security_record('chat_rate', security_note, sid=sid, severity=security_severity)
    if error_payload:
        emit('server_error', error_payload)
        return

    chat_message_id = None
    if DB_AVAILABLE and record_room_key:
        try:
            persisted_chat_payload = refresh_chat_special_fields(chat_data)
            chat_message_id = record_chat_message(
                record_room_key,
                record_channel,
                player_snapshot.get('user_id'),
                nickname,
                text,
                json.dumps(persisted_chat_payload, ensure_ascii=False, separators=(',', ':')),
                risk_level,
                hidden=False,
            )
        except Exception as exc:
            admin_event('error', f'failed to record chat message: {exc}')
    if chat_message_id:
        chat_data['message_id'] = chat_message_id
        if room_scope in ('room', 'spectate') and room_scope_id is not None and room_chat_local_id is not None:
            if _lock.acquire(timeout=0.2):
                try:
                    cached_room = rooms.get(room_scope_id)
                    update_room_chat_message_id_locked(cached_room, room_chat_local_id, chat_message_id)
                finally:
                    _lock.release()
            else:
                admin_event('warning', f'chat message id cache update skipped: lock busy room={room_scope_id}')

    if lobby_payloads is not None:
        emit_lobby_chat_history_payloads(lobby_payloads)
    elif recipients:
        seen = set()
        for target_sid in recipients:
            if target_sid in seen:
                continue
            seen.add(target_sid)
            socketio.emit('chat', chat_data, room=target_sid)


@socketio.on('draft_pick')
@measure_socket_action('draft_pick')
def on_draft_pick(data):
    global _next_room_id
    sid = request.sid
    data = socket_guard('draft_pick', data, require_player=True)
    if data is None:
        return
    try:
        def_id = validate_card_def_id(data.get('def_id'), name='def_id')
    except ValueError as exc:
        _security_illegal(sid, 'draft_pick', str(exc))
        return
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        if room_id is None or room_id not in rooms:
            return
        room = rooms[room_id]
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
        if not def_id:
            return
        draft_options_before = [card.def_id for card in (engine.draft_options[pidx] or [])]
        pick_result = engine.draft_pick(pidx, def_id)
        success = bool(pick_result.get('success')) if isinstance(pick_result, dict) else bool(pick_result)
        if not success:
            if not engine.draft_options[pidx]:
                engine._generate_draft_options_for_player(pidx)
            draft_options_before = [card.def_id for card in (engine.draft_options[pidx] or [])]
            pick_result = engine.draft_pick(pidx, def_id)
        success = bool(pick_result.get('success')) if isinstance(pick_result, dict) else bool(pick_result)
        if success:
            _add_draft_pick_time_bonus(room, pidx)
            if DB_AVAILABLE and room.mode in ('1v1', '2v2'):
                try:
                    enqueue_card_draft_pick(room.mode, draft_options_before, def_id)
                except Exception as exc:
                    admin_event('error', f'draft stats enqueue failed: {exc}')
            record_room_replay_action(room, 'draft_pick', pidx, {'def_id': def_id})
            # Check if THIS player finished drafting
            target_count = engine.draft_target_count(pidx) if hasattr(engine, 'draft_target_count') else DECK_SIZE
            if len(engine.draft_picks[pidx]) >= target_count:
                _reset_pregame_deadline(room, pidx, 'drafting')
                if engine.needs_sub_choice(pidx):
                    # This player needs sub-choice; the per-player pregame
                    # update below will send the correct prompt only to them.
                    pass
                else:
                    # No sub-choice needed, mark as ready
                    engine.player_ready[pidx] = True
            # Check if all players are ready
            if all(engine.player_ready[pi] for pi in range(len(room.player_sids))):
                schedule_start_game(room)
            else:
                # Only the actor needs their full draft/sub-choice UI rebuilt.
                # Other players may still be drafting, so update their progress
                # text without replacing their cards or current setup prompt.
                schedule_pregame_state(room, pidx, allow_sub_choice=True)
                schedule_pregame_status_update(room, targets=[pi for pi in range(len(room.player_sids)) if pi != pidx])
        else:
            socketio.emit('server_error', {'message': '无法选择这张牌'}, room=sid)


@socketio.on('select_opening_event')
@measure_socket_action('select_opening_event')
def on_select_opening_event(data):
    sid = request.sid
    data = socket_guard('select_opening_event', data, require_player=True)
    if data is None:
        return
    try:
        event_id = validate_str(data.get('event_id'), min_len=1, max_len=80, pattern=r'[A-Za-z0-9_.:\-/]+', name='event_id')
        sub_choice = validate_choice_payload(data.get('sub_choice'))
    except ValueError as exc:
        _security_illegal(sid, 'select_opening_event', str(exc))
        return
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        if room_id is None or room_id not in rooms:
            return
        room = rooms[room_id]
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
        if event_id is None:
            return
        option_ids = [str(ev.get('id')) for ev in (getattr(engine, 'opening_event_options', [[]])[pidx] or []) if ev and ev.get('id') is not None]
        success = engine.select_opening_event(pidx, event_id)
        if success:
            enqueue_opening_event_pick(room.mode, option_ids, event_id)
            _reset_pregame_deadline(room, pidx, 'event_select')
            if sub_choice:
                engine.opening_event_sub_choices[pidx] = sub_choice
            record_room_replay_action(room, 'select_opening_event', pidx, {
                'event_id': event_id,
                'sub_choice': sub_choice,
            })
            if all(pick is not None for pick in engine.opening_event_picks):
                record_room_replay_keyframe(room, 'event_reveal')
            for pi in range(len(room.player_sids)):
                schedule_pregame_state(room, pi)


@socketio.on('confirm_opening_reveal')
@measure_socket_action('confirm_opening_reveal')
def on_confirm_opening_reveal(data=None):
    sid = request.sid
    data = socket_guard('confirm_opening_reveal', data, require_player=True, allow_empty=True)
    if data is None:
        return
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        if room_id is None or room_id not in rooms:
            return
        room = rooms[room_id]
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
        if engine.opening_event_picks[pidx] is None:
            return
        if not all(pick is not None for pick in engine.opening_event_picks):
            schedule_pregame_state(room, pidx)
            return
        already_started = bool(getattr(engine, 'player_draft_started', [False] * len(room.player_sids))[pidx])
        if not already_started:
            _reset_pregame_deadline(room, pidx, 'event_reveal')
            engine.start_draft_for_player(pidx)
            record_room_replay_action(room, 'confirm_opening_reveal', pidx, {})
            record_room_replay_keyframe(room, 'draft_start')
        for pi in range(len(room.player_sids)):
            schedule_pregame_state(room, pi)


@socketio.on('reroll_opening_event')
@measure_socket_action('reroll_opening_event')
def on_reroll_opening_event(data=None):
    sid = request.sid
    data = socket_guard('reroll_opening_event', data, require_player=True, allow_empty=True)
    if data is None:
        return
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        if room_id is None or room_id not in rooms:
            return
        room = rooms[room_id]
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
        success = engine.reroll_opening_event(pidx)
        if success:
            schedule_event_state(room, pidx)


@socketio.on('submit_event_sub_choice')
@measure_socket_action('submit_event_sub_choice')
def on_submit_event_sub_choice(data):
    sid = request.sid
    data = socket_guard('submit_event_sub_choice', data, require_player=True)
    if data is None:
        return
    sub_choice = validate_choice_payload(data.get('sub_choice'))
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        if room_id is None or room_id not in rooms:
            return
        room = rooms[room_id]
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
        if getattr(engine, 'phase', None) not in ('event_select', 'event_reveal', 'draft'):
            return
        if bool(getattr(engine, 'player_ready', [False] * len(room.player_sids))[pidx]):
            schedule_pregame_state(room, pidx)
            return
        if str(engine.opening_event_picks[pidx]) == '5':
            raw_ids = []
            if isinstance(sub_choice, dict):
                raw_ids = list(sub_choice.get('add_def_ids') or sub_choice.get('def_ids') or [])
            valid_ids = []
            for def_id in raw_ids[:1]:
                if engine._card_allowed_for_fated_draw(str(def_id)):
                    valid_ids.append(str(def_id))
            if len(valid_ids) != 1:
                schedule_pregame_state(room, pidx, allow_sub_choice=True)
                return
            sub_choice = {'add_def_ids': valid_ids}
        if str(engine.opening_event_picks[pidx]) == '11':
            raw_ids = []
            if isinstance(sub_choice, dict):
                raw_ids = list(sub_choice.get('topdeck_def_ids') or sub_choice.get('def_ids') or [])
            available = list(engine.opening_event_topdeck_candidates(pidx)) if hasattr(engine, 'opening_event_topdeck_candidates') else []
            required = min(3, len(available))
            valid_ids = []
            remaining = list(available)
            for def_id in raw_ids[:3]:
                def_id = str(def_id)
                if def_id not in remaining:
                    continue
                remaining.remove(def_id)
                valid_ids.append(def_id)
            if len(valid_ids) != required or len(raw_ids) != required:
                schedule_pregame_state(room, pidx, allow_sub_choice=True)
                return
            sub_choice = {'topdeck_def_ids': valid_ids}
        event_id_text = str(engine.opening_event_picks[pidx])
        # Built-in setup sub-choices are "choose up to N" or have an engine fallback.
        # An empty/null payload is therefore a valid confirmation for them, not a
        # reason to keep the player stuck in the sub-choice UI.
        if sub_choice is None and event_id_text in ('2', '3', '5', '8', '11'):
            sub_choice = {}
        if sub_choice is None and engine.needs_sub_choice(pidx):
            schedule_pregame_state(room, pidx, allow_sub_choice=True)
            return
        engine.opening_event_sub_choices[pidx] = sub_choice or {}
        _reset_pregame_deadline(room, pidx, 'sub_choice')
        record_room_replay_action(room, 'submit_event_sub_choice', pidx, {
            'event_id': engine.opening_event_picks[pidx],
            'sub_choice': sub_choice or {},
        })
        # Mark this player as ready
        engine.player_ready[pidx] = True
        # Check if all players are ready
        if all(engine.player_ready[pi] for pi in range(len(room.player_sids))):
            schedule_start_game(room)
        else:
            schedule_pregame_state(room, pidx)
            schedule_pregame_status_update(room, targets=[pi for pi in range(len(room.player_sids)) if pi != pidx])


@socketio.on('solo_start')
def on_solo_start(data):
    sid = request.sid
    data = socket_guard('solo_start', data, require_player=False)
    if data is None:
        return
    if reject_new_match_if_draining([sid], 'solo_start'):
        return
    try:
        deck0 = validate_solo_deck_entries(data.get('deck0', []), name='deck0')
        deck1 = validate_solo_deck_entries(data.get('deck1', []), name='deck1')
        event0 = validate_int(data.get('event0'), default=None, minimum=0, maximum=9999, name='event0') if data.get('event0') is not None else None
        event1 = validate_int(data.get('event1'), default=None, minimum=0, maximum=9999, name='event1') if data.get('event1') is not None else None
        sub0 = validate_choice_payload(data.get('sub0'))
        sub1 = validate_choice_payload(data.get('sub1'))
    except ValueError as exc:
        _security_illegal(sid, 'solo_start', str(exc))
        emit('server_error', {'message': '训练场牌组必须各为0-100张'})
        return
    disabled_mods = ensure_valid_disabled_mods(normalize_disabled_mods_with_default(data.get('disabled_mods') if data else None))
    try:
        community_fields, community_mod = resolve_community_loadout(data or {})
        loadout = build_mod_loadout(
            disabled_mods,
            community_mod=community_mod,
            community_hash=community_fields.get('community_mod_hash', ''),
            runtime_mode='solo',
        )
    except Exception as exc:
        emit('server_error', {'message': f'社区模组加载失败: {exc}'})
        return
    allowed_card_ids = loadout['allowed_card_ids']
    if sid in players:
        players[sid]['disabled_mods'] = disabled_mods
        players[sid]['allowed_card_ids'] = allowed_card_ids
    def _valid_entry(entry):
        def_id = entry.get('def_id') if isinstance(entry, dict) else entry
        return def_id in CARD_DEFS and def_id in allowed_card_ids
    if any(not _valid_entry(entry) for entry in deck0 + deck1):
        emit('server_error', {'message': '训练场牌组中包含当前未启用的卡牌'})
        return
    with _lock:
        clear_pending_match_invites_for_sids_locked([sid])
        tutorial_sessions.discard(sid)
        solo_sessions[sid] = create_solo_engine(deck0, deck1, event0, event1, sub0, sub1, loadout=loadout)
        if sid in players:
            players[sid]['status'] = 'solo'
        socketio.emit('game_phase', {'phase': 'playing', 'solo': True}, room=sid)
        send_solo_state(sid)


@socketio.on('tutorial_start')
def on_tutorial_start(data=None):
    sid = request.sid
    data = socket_guard('tutorial_start', data, require_player=False, allow_empty=True)
    if data is None:
        return
    if reject_new_match_if_draining([sid], 'tutorial_start'):
        return
    deck0 = [
        'Basic', 'Rose', 'Leaf', 'Bubble', 'Bone',
        'Fission', 'Triangle', 'Basic', 'Basic', 'Fusion',
        'Rose', 'Leaf', 'Basic', 'Bone', 'Bubble',
    ]
    deck1 = [
        'Basic', 'Battery', 'Leaf', 'Basic', 'Bone',
        'Stinger', 'Fire', 'Disc', 'Bubble', 'Mine',
        'Basic', 'Bone', 'Mark', 'Sewage', 'MagicBubble',
    ]
    tutorial_allowed = apply_runtime_content_filter(CARD_DEFS.keys(), 'tutorial')
    with _lock:
        clear_pending_match_invites_for_sids_locked([sid])
        tutorial_sessions.add(sid)
        solo_sessions[sid] = create_solo_engine(
            deck0,
            deck1,
            None,
            None,
            None,
            None,
            player_names=['你', '练习对手'],
            start_label='新手教程开始',
        )
        engine = solo_sessions[sid]
        engine.tutorial_progress = {key: False for key in TUTORIAL_PROGRESS_KEYS}
        engine.players[0].health = min(int(engine.players[0].max_health), 90)
        engine.players[0].elixir = max(int(engine.players[0].elixir), 5)
        engine.allowed_card_ids = tutorial_allowed
        for ps in engine.players:
            ps.deck = [card for card in ps.deck if card.def_id in tutorial_allowed]
        if sid in players:
            players[sid]['status'] = 'tutorial'
        socketio.emit('game_phase', {'phase': 'playing', 'solo': True, 'tutorial': True}, room=sid)
        send_solo_state(sid, 0)


def _pick_tutorial_bot_card(engine):
    if engine.current_player != 1 or engine.phase != 'action' or engine.game_over:
        return None
    ps = engine.players[1]
    if sum(ps.cards_played_this_turn.values()) >= 1:
        return None
    safe_card_ids = {'Basic', 'Bone', 'Stinger', 'Battery'}
    order = ('thorn', 'root')
    for card_type in order:
        for card in ps.hand:
            card_def = card.card_def
            if card.def_id not in safe_card_ids or card_def.card_type != card_type:
                continue
            if card_def.card_type == 'guard':
                continue
            if card_def.card_type == 'root' and len(ps.equipment) >= 4:
                continue
            can_play, _ = engine.can_play_card(1, card)
            if can_play:
                return card
    return None


@socketio.on('tutorial_bot_action')
def on_tutorial_bot_action(data=None):
    sid = request.sid
    data = socket_guard('tutorial_bot_action', data, require_player=False, allow_empty=True, emit_error=False)
    if data is None:
        return
    with _lock:
        if sid not in tutorial_sessions:
            return
        engine = solo_sessions.get(sid)
        if not engine or engine.game_over:
            send_solo_state(sid, 0)
            return
        if engine.current_player != 1 or engine.pending_response is not None:
            send_solo_state(sid, 0)
            return
        card = _pick_tutorial_bot_card(engine)
        if card:
            result = engine.play_card(1, card.instance_id)
            if result.get('needs_response'):
                send_solo_state(sid, 0)
                emit_solo_response_request(sid, engine, 1, result['card'])
            elif result.get('needs_choice'):
                engine.end_turn(1)
                send_solo_state(sid, 0)
            else:
                send_solo_state(sid, 0)
        else:
            engine.end_turn(1)
            send_solo_state(sid, 0)


@socketio.on('solo_play_card')
def on_solo_play_card(data):
    sid = request.sid
    data = socket_guard('solo_play_card', data, require_player=False)
    if data is None:
        return
    try:
        card_instance_id = validate_instance_id(data.get('card_instance_id'), name='card_instance_id')
        choice = validate_choice_payload(data.get('choice'))
        target_player_id = validate_int(data.get('target_player_id', -1), default=-1, minimum=-1, maximum=16, name='target_player_id')
    except ValueError as exc:
        _security_illegal(sid, 'solo_play_card', str(exc))
        return
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            emit('server_error', {'message': '训练场尚未开始'})
            return
        pidx = engine.current_player
        if target_player_id >= 0:
            choice = dict(choice or {})
            choice.setdefault('target_player', target_player_id)
            choice.setdefault('target_player_id', target_player_id)
            choice.setdefault('target_id', target_player_id)
        tutorial_card_before = _tutorial_card_before_action(engine, pidx, card_instance_id) if sid in tutorial_sessions else None
        undo_snapshot = _solo_capture_undo_snapshot(sid, engine)
        result = engine.play_card(pidx, card_instance_id, choice)
        if sid in tutorial_sessions:
            _tutorial_note_card_action(engine, pidx, tutorial_card_before, choice, result)
        if result.get('needs_response'):
            _solo_commit_undo_snapshot(engine, undo_snapshot)
            if sid in tutorial_sessions and pidx == 0:
                engine.handle_response(1, None)
                send_solo_state(sid, 0)
                return
            send_solo_state(sid, 0 if sid in tutorial_sessions else 1 - pidx)
            emit_solo_response_request(sid, engine, pidx, result['card'])
        elif result.get('needs_choice'):
            _solo_commit_undo_snapshot(engine, undo_snapshot)
            send_solo_state(sid)
            socketio.emit('choice_request', build_choice_request_payload(result), room=sid)
        elif result.get('needs_v2_ui'):
            _solo_commit_undo_snapshot(engine, undo_snapshot)
            send_solo_state(sid)
            emit_v2_ui_request_to_sid(sid, engine, ('solo', sid))
        elif result.get('success'):
            _solo_commit_undo_snapshot(engine, undo_snapshot)
            send_solo_state(sid)
        else:
            emit('server_error', {'message': result.get('error', 'Operation failed')})


@socketio.on('solo_response')
def on_solo_response(data):
    sid = request.sid
    data = socket_guard('solo_response', data, require_player=False, allow_empty=True)
    if data is None:
        return
    try:
        raw_card_id = data.get('card_instance_id') if data else None
        card_instance_id = None if raw_card_id in (None, '', 'none') else validate_instance_id(raw_card_id, name='card_instance_id', required=False)
    except ValueError as exc:
        _security_illegal(sid, 'solo_response', str(exc))
        return
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            return
        had_pending_response = bool(getattr(engine, 'pending_response', None))
        responder = 1 - engine.pending_response['player_id'] if had_pending_response else engine.current_player
        if sid in tutorial_sessions and responder != 0:
            card_instance_id = None
        tutorial_counter = (
            _tutorial_card_before_action(engine, responder, card_instance_id)
            if sid in tutorial_sessions and card_instance_id is not None
            else None
        )
        undo_snapshot = _solo_capture_undo_snapshot(sid, engine) if had_pending_response else None
        response_result = engine.handle_response(responder, card_instance_id)
        if (
            sid in tutorial_sessions
            and responder == 0
            and isinstance(tutorial_counter, dict)
            and tutorial_counter.get('def_id') == 'Bubble'
            and isinstance(response_result, dict)
            and response_result.get('success')
        ):
            _tutorial_mark(engine, 'counter_used')
        if had_pending_response:
            _solo_commit_undo_snapshot(engine, undo_snapshot)
        pending = getattr(engine, 'pending_response', None)
        if pending:
            pending_player = int(pending.get('player_id', engine.current_player))
            if sid in tutorial_sessions and (1 - pending_player) != 0:
                engine.handle_response(1 - pending_player, None)
                send_solo_state(sid)
            else:
                send_solo_state(sid, 0 if sid in tutorial_sessions else 1 - pending_player)
                emit_solo_response_request(sid, engine, pending_player, pending.get('card') or {})
        elif getattr(engine, 'pending_choice', None):
            send_solo_state(sid)
            socketio.emit('choice_request', build_choice_request_payload(engine.pending_choice), room=sid)
        elif getattr(engine, 'pending_v2_ui', None):
            send_solo_state(sid)
            emit_v2_ui_request_to_sid(sid, engine, ('solo', sid))
        else:
            send_solo_state(sid)


@socketio.on('solo_resolve_choice')
def on_solo_resolve_choice(data):
    sid = request.sid
    data = socket_guard('solo_resolve_choice', data, require_player=False, allow_empty=True)
    if data is None:
        return
    try:
        choice = validate_choice_payload(data.get('choice') if data else None)
    except ValueError as exc:
        _security_illegal(sid, 'solo_resolve_choice', str(exc))
        return
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            return
        if not getattr(engine, 'pending_choice', None):
            send_solo_state(sid)
            return
        pidx = engine.pending_choice.get('player_id', engine.current_player) if engine.pending_choice else engine.current_player
        undo_snapshot = _solo_capture_undo_snapshot(sid, engine)
        result = engine.resolve_choice(pidx, choice)
        if sid in tutorial_sessions and pidx == 0 and result.get('success'):
            _tutorial_refresh_progress(engine)
        if result.get('needs_response'):
            _solo_commit_undo_snapshot(engine, undo_snapshot)
            if sid in tutorial_sessions and pidx == 0:
                engine.handle_response(1, None)
                send_solo_state(sid, 0)
                return
            send_solo_state(sid, 0 if sid in tutorial_sessions else 1 - pidx)
            emit_solo_response_request(sid, engine, pidx, result['card'])
        elif result.get('needs_choice'):
            _solo_commit_undo_snapshot(engine, undo_snapshot)
            send_solo_state(sid)
            socketio.emit('choice_request', build_choice_request_payload(result), room=sid)
        elif result.get('needs_v2_ui'):
            _solo_commit_undo_snapshot(engine, undo_snapshot)
            send_solo_state(sid)
            emit_v2_ui_request_to_sid(sid, engine, ('solo', sid))
        else:
            _solo_commit_undo_snapshot(engine, undo_snapshot)
            send_solo_state(sid)


@socketio.on('solo_v2_ui_response')
def on_solo_v2_ui_response(data):
    sid = request.sid
    data = socket_guard('solo_v2_ui_response', data, require_player=False)
    if data is None:
        return
    try:
        request_id = validate_str(data.get('request_id', ''), max_len=80, pattern=r'[A-Za-z0-9_.:\-]*', name='request_id')
        values = validate_choice_payload(data.get('values'))
        button = validate_str(data.get('button', ''), max_len=80, pattern=r'[A-Za-z0-9_.:\-]*', name='button')
        clean_data = dict(data)
        clean_data['request_id'] = request_id
        clean_data['values'] = values
        clean_data['button'] = button
    except ValueError as exc:
        _security_illegal(sid, 'solo_v2_ui_response', str(exc))
        return
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            return
        pending = getattr(engine, 'pending_v2_ui', None)
        if not pending:
            return
        pidx = int(pending.get('player_id', engine.current_player))
        _cancel_v2_ui_timeout(('solo', sid), request_id)
        undo_snapshot = _solo_capture_undo_snapshot(sid, engine)
        result = engine.handle_v2_ui_response(pidx, request_id, clean_data)
        if result.get('needs_v2_ui'):
            _solo_commit_undo_snapshot(engine, undo_snapshot)
            send_solo_state(sid)
            emit_v2_ui_request_to_sid(sid, engine, ('solo', sid))
        elif result.get('success'):
            _solo_commit_undo_snapshot(engine, undo_snapshot)
            send_solo_state(sid)
        else:
            emit('server_error', {'message': result.get('error', 'Operation failed')})
            send_solo_state(sid)


@socketio.on('solo_use_trigger')
def on_solo_use_trigger(data):
    sid = request.sid
    data = socket_guard('solo_use_trigger', data, require_player=False)
    if data is None:
        return
    try:
        equipment_instance_id = validate_instance_id(data.get('equipment_instance_id'), name='equipment_instance_id')
        target_player_id = validate_int(data.get('target_player_id', -1), default=-1, minimum=-1, maximum=16, name='target_player_id')
    except ValueError as exc:
        _security_illegal(sid, 'solo_use_trigger', str(exc))
        return
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            return
        tutorial_equipment_def_id = ''
        if sid in tutorial_sessions and engine.current_player == 0:
            for eq in list(getattr(engine.players[0], 'equipment', []) or []):
                if int(getattr(eq.card_instance, 'instance_id', -1)) == equipment_instance_id:
                    tutorial_equipment_def_id = str(getattr(eq.card_instance, 'def_id', '') or '')
                    break
        undo_snapshot = _solo_capture_undo_snapshot(sid, engine)
        result = engine.use_trigger(engine.current_player, equipment_instance_id, target_player_id=target_player_id)
        if sid in tutorial_sessions and tutorial_equipment_def_id == 'Leaf' and result.get('success'):
            _tutorial_mark(engine, 'trigger_used')
        if result.get('success') or result.get('needs_response') or result.get('needs_choice') or result.get('needs_v2_ui'):
            _solo_commit_undo_snapshot(engine, undo_snapshot)
        if not result.get('success'):
            emit('server_error', {'message': result.get('error', 'Operation failed')})
        send_solo_state_with_pending(sid)


@socketio.on('solo_end_turn')
def on_solo_end_turn(data=None):
    sid = request.sid
    data = socket_guard('solo_end_turn', data, require_player=False, allow_empty=True)
    if data is None:
        return
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            return
        tutorial_player_id = engine.current_player
        undo_snapshot = _solo_capture_undo_snapshot(sid, engine)
        result = engine.end_turn(engine.current_player)
        if sid in tutorial_sessions and tutorial_player_id == 0 and result.get('success'):
            _tutorial_mark(engine, 'turn_ended')
        if result.get('success'):
            _solo_commit_undo_snapshot(engine, undo_snapshot)
        if not result.get('success'):
            emit('server_error', {'message': result.get('error', 'Operation failed')})
        send_solo_state(sid)


@socketio.on('solo_set_next_draw')
def on_solo_set_next_draw(data):
    sid = request.sid
    data = socket_guard('solo_set_next_draw', data, require_player=False)
    if data is None:
        return
    def_ids = []
    try:
        if isinstance(data.get('def_ids'), list):
            if len(data.get('def_ids')) > 10:
                raise ValueError('def_ids too long')
            def_ids = [validate_card_def_id(x, name='def_ids') for x in data.get('def_ids') if x]
        elif data.get('def_id'):
            def_ids = [validate_card_def_id(data.get('def_id'), name='def_id')]
    except ValueError as exc:
        _security_illegal(sid, 'solo_set_next_draw', str(exc))
        return
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine or not def_ids:
            return
        ps = engine.players[engine.current_player]
        picked = []
        for did in def_ids:
            idx2 = next((i for i, c in enumerate(ps.deck) if c.def_id == did), -1)
            if idx2 >= 0:
                picked.append(ps.deck.pop(idx2))
        if not picked:
            emit('server_error', {'message': '设置失败：牌堆中没有这些牌'})
            return
        undo_snapshot = _solo_capture_undo_snapshot(sid, engine)
        for c in reversed(picked):
            ps.deck.insert(0, c)
        names = '、'.join([c.name_cn for c in picked])
        engine.log_msg(f"训练场：{engine.pn(engine.current_player)} 设置下次抽牌：{names}")
        _solo_commit_undo_snapshot(engine, undo_snapshot)
        send_solo_state(sid)
        return
        idx = next((i for i, c in enumerate(ps.deck) if c.def_id == def_id), -1)
        if idx < 0:
            emit('server_error', {'message': '设置失败：牌堆中没有这张牌'})
            return
        card = ps.deck.pop(idx)
        ps.deck.insert(0, card)
        engine.log_msg(f"训练场：{engine.pn(engine.current_player)} 设置下次抽牌：{card.name_cn}")
        send_solo_state(sid)


@socketio.on('solo_undo')
def on_solo_undo(data=None):
    sid = request.sid
    data = socket_guard('solo_undo', data, require_player=False, allow_empty=True)
    if data is None:
        return
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            emit('server_error', {'message': '训练场尚未开始'})
            return
        if sid in tutorial_sessions:
            emit('server_error', {'message': '新手教程不能撤销'})
            return
        if not hasattr(engine, '_solo_undo_stack') or not hasattr(engine, '_solo_redo_stack'):
            init_solo_history(engine)
        if not engine._solo_undo_stack:
            emit('server_error', {'message': '没有可撤销操作'})
            return
        current = _solo_engine_snapshot(engine)
        snapshot = engine._solo_undo_stack.pop()
        if current is not None:
            engine._solo_redo_stack.append(current)
        _solo_restore_snapshot(engine, snapshot)
        send_solo_state_with_pending(sid)


@socketio.on('solo_redo')
def on_solo_redo(data=None):
    sid = request.sid
    data = socket_guard('solo_redo', data, require_player=False, allow_empty=True)
    if data is None:
        return
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            emit('server_error', {'message': '训练场尚未开始'})
            return
        if sid in tutorial_sessions:
            emit('server_error', {'message': '新手教程不能重做'})
            return
        if not hasattr(engine, '_solo_undo_stack') or not hasattr(engine, '_solo_redo_stack'):
            init_solo_history(engine)
        if not engine._solo_redo_stack:
            emit('server_error', {'message': '没有可重做操作'})
            return
        current = _solo_engine_snapshot(engine)
        snapshot = engine._solo_redo_stack.pop()
        if current is not None:
            engine._solo_undo_stack.append(current)
        _solo_restore_snapshot(engine, snapshot)
        send_solo_state_with_pending(sid)


@socketio.on('solo_pause')
def on_solo_pause(data=None):
    sid = request.sid
    data = socket_guard('solo_pause', data, require_player=False, allow_empty=True)
    if data is None:
        return
    solo_sessions.pop(sid, None)
    tutorial_sessions.discard(sid)
    if sid in players:
        players[sid]['status'] = 'lobby'
    socketio.emit('solo_paused', {}, room=sid)


@socketio.on('play_card')
@measure_socket_action('play_card')
def on_play_card(data):
    sid = request.sid
    data = socket_guard('play_card', data, require_player=True)
    if data is None:
        return
    try:
        card_instance_id = validate_instance_id(data.get('card_instance_id'), name='card_instance_id')
        choice = validate_choice_payload(data.get('choice'))
        target_player_id = validate_int(data.get('target_player_id', -1), default=-1, minimum=-1, maximum=16, name='target_player_id')
    except ValueError as exc:
        _security_illegal(sid, 'play_card', str(exc))
        return
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        player_name = player.get('nickname', '?')
        room_id = player.get('room_id')
        room = rooms.get(room_id)
        if room is None:
            return
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
    busy_lock = _try_acquire_room_action(room, sid, 'play_card', pidx)
    if busy_lock is None:
        return
    try:
        reject_code = _room_action_precheck(engine, pidx, event_name='play_card')
        if reject_code:
            soft_reject(sid, 'play_card', reject_code, room=room, pidx=pidx, send_state=True)
            return
        hand = getattr(engine.players[pidx], 'hand', [])
        if not any(str(getattr(c, 'instance_id', '')) == str(card_instance_id) for c in hand):
            soft_reject(sid, 'play_card', 'STATE_VERSION_OLD', room=room, pidx=pidx, send_state=True)
            return
        replay_def_id = ''
        try:
            replay_card = next((c for c in getattr(engine.players[pidx], 'hand', []) if str(getattr(c, 'instance_id', '')) == str(card_instance_id)), None)
            replay_def_id = getattr(replay_card, 'def_id', '') or ''
        except Exception:
            replay_def_id = ''
        if room.mode == '2v2':
            if target_player_id >= 0:
                choice = dict(choice or {})
                choice.setdefault('target_player', target_player_id)
                choice.setdefault('target_player_id', target_player_id)
                choice.setdefault('target_id', target_player_id)
            result = engine.play_card(pidx, card_instance_id, target_player_id=target_player_id, choice=choice)
        else:
            if target_player_id >= 0:
                choice = dict(choice or {})
                choice.setdefault('target_player', target_player_id)
                choice.setdefault('target_player_id', target_player_id)
                choice.setdefault('target_id', target_player_id)
            result = engine.play_card(pidx, card_instance_id, choice)
        _stamp_pending_interactions(room)
    finally:
        busy_lock.release()
    completed_play_for_timer = (
        result.get('needs_response')
        or (
            result.get('success')
            and not result.get('needs_choice')
            and not result.get('needs_v2_ui')
            and not result.get('needs_ally_consent')
        )
    )
    if completed_play_for_timer:
        _add_room_action_timer_bonus(room, expected_player=pidx)
        with _lock:
            _sync_room_action_timer_after_state_change(room)
        emit_turn_timer_update(room)
    if completed_play_for_timer:
        record_valid_player_action(room, pidx, 'play_card')
    if result.get('success') or result.get('needs_ally_consent') or result.get('needs_response') or result.get('needs_v2_ui'):
        replay_action_payload = {
            'card_instance_id': card_instance_id,
            'def_id': replay_def_id,
            'target_player_id': target_player_id,
            'choice': choice,
            'result': result,
        }
        if result.get('needs_ally_consent'):
            replay_action_payload['ally_consent_request'] = {
                'card': result.get('card') or {},
                'from_player': pidx,
                'from_name': player_name,
            }
        replay_action_payload = enrich_replay_interaction_payload(room, replay_action_payload, result)
        record_room_replay_action(room, 'play_card', pidx, replay_action_payload)
    if result.get('needs_ally_consent'):
        broadcast_game_state(room)
        target_pidx = result.get('target_player_id')
        if isinstance(target_pidx, int) and 0 <= target_pidx < len(room.player_sids):
            target_sid = room.player_sids[target_pidx]
            if target_sid in players:
                socketio.emit('ally_consent_request', {
                    'card': result.get('card'),
                    'from_player': pidx,
                    'from_name': player_name,
                }, room=target_sid)
            else:
                room.engine.pending_ally_request = None
                emit('server_error', {'message': 'Teammate is not online'})
    elif result.get('needs_response'):
        broadcast_game_state(room)
        emit_or_resolve_pending_response(room, reason='play_card')
    elif result.get('needs_choice'):
        broadcast_game_state(room)
        emit('choice_request', build_choice_request_payload(result))
    elif result.get('needs_v2_ui'):
        broadcast_game_state(room)
        emit_room_v2_ui_request(room)
    elif result.get('success'):
        broadcast_game_state(room)
    else:
        code = normalize_soft_reject_code(result.get('error')) or 'CARD_NOT_PLAYABLE_NOW'
        soft_reject(sid, 'play_card', code, result.get('error', 'Operation failed'), room=room, pidx=pidx, send_state=True)


@socketio.on('response')
@measure_socket_action('response')
def on_response(data):
    sid = request.sid
    data = socket_guard('response', data, require_player=True)
    if data is None:
        return
    try:
        raw_card_id = data.get('card_instance_id')
        card_instance_id = None if raw_card_id in (None, '', 'none') else validate_instance_id(raw_card_id, name='card_instance_id', required=False)
    except ValueError as exc:
        _security_illegal(sid, 'response', str(exc))
        return
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        room = rooms.get(room_id)
        if room is None:
            return
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
    busy_lock = _try_acquire_room_action(room, sid, 'response', pidx)
    if busy_lock is None:
        return
    try:
        pending_response = getattr(engine, 'pending_response', None)
        if not pending_response:
            soft_reject(sid, 'response', 'RESPONSE_NOT_EXPECTED', room=room, pidx=pidx, send_state=True)
            return
        if room.mode == '2v2':
            allowed = any(int(cc.get('responder_id', -1)) == pidx for cc in (pending_response.get('counter_cards') or []) if isinstance(cc, dict))
        else:
            try:
                allowed = pidx == 1 - int(pending_response.get('player_id', -1))
            except Exception:
                allowed = False
        if not allowed:
            soft_reject(sid, 'response', 'RESPONSE_NOT_EXPECTED', room=room, pidx=pidx, send_state=True)
            return
        replay_def_id = ''
        try:
            replay_card = next((c for c in getattr(engine.players[pidx], 'hand', []) if str(getattr(c, 'instance_id', '')) == str(card_instance_id)), None)
            replay_def_id = getattr(replay_card, 'def_id', '') or ''
        except Exception:
            replay_def_id = ''
        engine.handle_response(pidx, card_instance_id)
        _stamp_pending_interactions(room)
    finally:
        busy_lock.release()
    if card_instance_id:
        record_valid_player_action(room, pidx, 'response')
    record_room_replay_action(room, 'response', pidx, enrich_replay_interaction_payload(room, {
        'card_instance_id': card_instance_id,
        'def_id': replay_def_id,
    }))
    with _lock:
        _sync_room_action_timer_after_state_change(room)
    emit_turn_timer_update(room)
    broadcast_game_state(room)
    emit_pending_interaction_after_state_change(room, reason='response_chain')


@socketio.on('ally_consent_response')
@measure_socket_action('ally_consent_response')
def on_ally_consent_response(data):
    sid = request.sid
    data = socket_guard('ally_consent_response', data, require_player=True, allow_empty=True)
    if data is None:
        return
    accepted = bool(data.get('accepted')) if data else False
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        room = rooms.get(room_id)
        if room is None:
            return
        if room.mode != '2v2':
            return
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
    busy_lock = _try_acquire_room_action(room, sid, 'ally_consent_response', pidx)
    if busy_lock is None:
        return
    try:
        if not getattr(engine, 'pending_ally_request', None):
            soft_reject(sid, 'ally_consent_response', 'NO_PENDING_CHOICE', '没有待同意的队友用牌', room=room, pidx=pidx, send_state=True)
            return
        requester_id = _pending_player_id(getattr(engine, 'pending_ally_request', None), None)
        result = engine.handle_ally_consent(pidx, accepted)
        _stamp_pending_interactions(room)
    finally:
        busy_lock.release()
    if result.get('success') or result.get('needs_response') or result.get('needs_choice') or result.get('needs_v2_ui') or not accepted:
        record_room_replay_action(room, 'ally_consent_response', pidx, enrich_replay_interaction_payload(room, {
            'accepted': accepted,
            'result': result,
        }, result))
    with _lock:
        _sync_room_action_timer_after_state_change(room)
    emit_turn_timer_update(room)
    if result.get('needs_response'):
        _add_room_action_timer_bonus(room, expected_player=requester_id)
        broadcast_game_state(room)
        emit_or_resolve_pending_response(room, reason='ally_consent')
    elif result.get('needs_choice'):
        broadcast_game_state(room)
        requester_sid = room.player_sids[result.get('player_id', engine.current_player)] if result.get('player_id') is not None else sid
        socketio.emit('choice_request', build_choice_request_payload(result), room=requester_sid)
    elif result.get('needs_v2_ui'):
        broadcast_game_state(room)
        emit_room_v2_ui_request(room)
    elif not result.get('success'):
        emit('server_error', {'message': result.get('error', 'Operation failed')})
    else:
        if accepted:
            _add_room_action_timer_bonus(room, expected_player=requester_id)
            emit_turn_timer_update(room)
        broadcast_game_state(room)


@socketio.on('resolve_choice')
@measure_socket_action('resolve_choice')
def on_resolve_choice(data):
    sid = request.sid
    data = socket_guard('resolve_choice', data, require_player=True)
    if data is None:
        return
    try:
        choice = validate_choice_payload(data.get('choice'))
    except ValueError as exc:
        _security_illegal(sid, 'resolve_choice', str(exc))
        return
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        room = rooms.get(room_id)
        if room is None:
            return
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
    busy_lock = _try_acquire_room_action(room, sid, 'resolve_choice', pidx)
    if busy_lock is None:
        return
    try:
        pending = getattr(engine, 'pending_choice', None)
        if not pending:
            admin_event('player', f'ignored stale resolve_choice without pending choice room={room_id}', sid=sid, room_id=room_id)
            send_game_state_to(room, pidx)
            return
        try:
            pending_player_id = int(pending.get('player_id', pidx))
        except Exception:
            pending_player_id = pidx
        if pending_player_id != pidx:
            admin_event('player', f'ignored resolve_choice from non-pending player room={room_id} pending={pending_player_id} got={pidx}', sid=sid, room_id=room_id)
            send_game_state_to(room, pidx)
            return
        result = engine.resolve_choice(pidx, choice)
        _stamp_pending_interactions(room)
    finally:
        busy_lock.release()
    if not result.get('cancelled'):
        record_valid_player_action(room, pidx, 'resolve_choice')
    record_room_replay_action(room, 'resolve_choice', pidx, enrich_replay_interaction_payload(room, {
        'choice': choice,
        'result': result,
    }, result))
    with _lock:
        _sync_room_action_timer_after_state_change(room)
    if result.get('needs_response'):
        _add_room_action_timer_bonus(room, expected_player=pidx)
        emit_turn_timer_update(room)
        broadcast_game_state(room)
        emit_or_resolve_pending_response(room, reason='resolve_choice')
    elif result.get('needs_choice'):
        broadcast_game_state(room)
        emit('choice_request', build_choice_request_payload(result))
    elif result.get('needs_v2_ui'):
        broadcast_game_state(room)
        emit_room_v2_ui_request(room)
    elif result.get('success'):
        _add_room_action_timer_bonus(room, expected_player=pidx)
        emit_turn_timer_update(room)
        broadcast_game_state(room)
    elif result.get('cancelled'):
        broadcast_game_state(room)
    else:
        code = normalize_soft_reject_code(result.get('error')) or 'NO_PENDING_CHOICE'
        if code == 'NO_PENDING_CHOICE':
            admin_event('player', f'ignored stale resolve_choice result room={room_id} error={result.get("error")}', sid=sid, room_id=room_id)
            send_game_state_to(room, pidx)
            return
        soft_reject(sid, 'resolve_choice', code, result.get('error', 'Operation failed'), room=room, pidx=pidx, send_state=True)


@socketio.on('v2_ui_response')
@measure_socket_action('v2_ui_response')
def on_v2_ui_response(data):
    sid = request.sid
    data = socket_guard('v2_ui_response', data, require_player=True)
    if data is None:
        return
    try:
        request_id = validate_str(data.get('request_id', ''), max_len=80, pattern=r'[A-Za-z0-9_.:\-]*', name='request_id')
        values = validate_choice_payload(data.get('values'))
        button = validate_str(data.get('button', ''), max_len=80, pattern=r'[A-Za-z0-9_.:\-]*', name='button')
        clean_data = dict(data)
        clean_data['request_id'] = request_id
        clean_data['values'] = values
        clean_data['button'] = button
    except ValueError as exc:
        _security_illegal(sid, 'v2_ui_response', str(exc))
        return
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        room = rooms.get(room_id)
        if room is None:
            return
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
    busy_lock = _try_acquire_room_action(room, sid, 'v2_ui_response', pidx)
    if busy_lock is None:
        return
    try:
        pending = getattr(engine, 'pending_v2_ui', None)
        if not pending:
            soft_reject(sid, 'v2_ui_response', 'PENDING_V2_UI', '没有待处理窗口', room=room, pidx=pidx, send_state=True)
            return
        try:
            pending_player_id = int(pending.get('player_id', pidx))
        except Exception:
            pending_player_id = pidx
        if pending_player_id != pidx or str(pending.get('request_id', '')) != str(request_id):
            soft_reject(sid, 'v2_ui_response', 'PENDING_V2_UI', '窗口状态已更新', room=room, pidx=pidx, send_state=True)
            return
        _cancel_v2_ui_timeout(('room', room.room_id), request_id)
        result = engine.handle_v2_ui_response(pidx, request_id, clean_data)
        _stamp_pending_interactions(room)
    finally:
        busy_lock.release()
    record_room_replay_action(room, 'v2_ui_response', pidx, enrich_replay_interaction_payload(room, {
        'request_id': request_id,
        'button': button,
        'values': values,
        'result': result,
    }, result))
    with _lock:
        _sync_room_action_timer_after_state_change(room)
    emit_turn_timer_update(room)
    if result.get('needs_v2_ui'):
        broadcast_game_state(room)
        emit_room_v2_ui_request(room)
    elif result.get('success'):
        if not result.get('cancelled') and str(button).lower() not in ('cancel', 'close', 'timeout'):
            _add_room_action_timer_bonus(room, expected_player=pidx)
            emit_turn_timer_update(room)
        broadcast_game_state(room)
    else:
        code = normalize_soft_reject_code(result.get('error')) or 'PENDING_V2_UI'
        soft_reject(sid, 'v2_ui_response', code, result.get('error', 'Operation failed'), room=room, pidx=pidx, send_state=True)


@socketio.on('use_trigger')
@measure_socket_action('use_trigger')
def on_use_trigger(data):
    sid = request.sid
    data = socket_guard('use_trigger', data, require_player=True)
    if data is None:
        return
    try:
        equipment_instance_id = validate_instance_id(data.get('equipment_instance_id'), name='equipment_instance_id')
        target_player_id = validate_int(data.get('target_player_id', -1), default=-1, minimum=-1, maximum=16, name='target_player_id')
    except ValueError as exc:
        _security_illegal(sid, 'use_trigger', str(exc))
        return
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        player_name = player.get('nickname', '?')
        room_id = player.get('room_id')
        room = rooms.get(room_id)
        if room is None:
            return
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
    busy_lock = _try_acquire_room_action(room, sid, 'use_trigger', pidx)
    if busy_lock is None:
        return
    try:
        reject_code = _room_action_precheck(engine, pidx, event_name='use_trigger')
        if reject_code:
            soft_reject(sid, 'use_trigger', reject_code, room=room, pidx=pidx, send_state=True)
            return
        replay_def_id = ''
        try:
            equipment = next((eq for eq in getattr(engine.players[pidx], 'equipment', []) if str(getattr(getattr(eq, 'card_instance', None), 'instance_id', '')) == str(equipment_instance_id)), None)
            replay_def_id = getattr(getattr(equipment, 'card_instance', None), 'def_id', '') or getattr(getattr(equipment, 'card_def', None), 'id', '') or ''
            if equipment is None:
                soft_reject(sid, 'use_trigger', 'STATE_VERSION_OLD', room=room, pidx=pidx, send_state=True)
                return
        except Exception:
            replay_def_id = ''
        result = engine.use_trigger(pidx, equipment_instance_id, target_player_id=target_player_id)
        _stamp_pending_interactions(room)
    finally:
        busy_lock.release()
    if result.get('success') or result.get('needs_ally_consent') or result.get('needs_choice') or result.get('needs_response') or result.get('needs_v2_ui'):
        record_valid_player_action(room, pidx, 'use_trigger')
        trigger_replay_payload = {
            'equipment_instance_id': equipment_instance_id,
            'def_id': replay_def_id,
            'target_player_id': target_player_id,
            'result': result,
        }
        if result.get('needs_ally_consent'):
            trigger_replay_payload['ally_consent_request'] = {
                'card': result.get('card') or {},
                'from_player': pidx,
                'from_name': player_name,
            }
        record_room_replay_action(
            room,
            'use_trigger',
            pidx,
            enrich_replay_interaction_payload(room, trigger_replay_payload, result),
        )
        with _lock:
            _sync_room_action_timer_after_state_change(room)
        emit_turn_timer_update(room)
    if result.get('needs_ally_consent'):
        broadcast_game_state(room)
        target_pidx = result.get('target_player_id')
        if isinstance(target_pidx, int) and 0 <= target_pidx < len(room.player_sids):
            target_sid = room.player_sids[target_pidx]
            if target_sid in players:
                socketio.emit('ally_consent_request', {
                    'card': result.get('card'),
                    'from_player': pidx,
                    'from_name': player_name,
                }, room=target_sid)
            else:
                engine.pending_ally_request = None
                emit('server_error', {'message': 'Teammate is not online'})
    elif result.get('needs_response'):
        _add_room_action_timer_bonus(room, expected_player=pidx)
        broadcast_game_state(room)
        emit_or_resolve_pending_response(room, reason='use_trigger')
    elif result.get('needs_v2_ui'):
        broadcast_game_state(room)
        emit_room_v2_ui_request(room)
    elif result.get('success'):
        broadcast_game_state(room)
    else:
        code = normalize_soft_reject_code(result.get('error')) or 'TRIGGER_NOT_PLAYABLE_NOW'
        soft_reject(sid, 'use_trigger', code, result.get('error', 'Operation failed'), room=room, pidx=pidx, send_state=True)


@socketio.on('urf_replace_card')
@measure_socket_action('urf_replace_card')
def on_urf_replace_card(data):
    sid = request.sid
    data = socket_guard('urf_replace_card', data, require_player=True)
    if data is None:
        return
    try:
        card_instance_id = validate_instance_id(data.get('card_instance_id'), name='card_instance_id')
    except ValueError as exc:
        _security_illegal(sid, 'urf_replace_card', str(exc))
        return
    with _lock:
        if sid not in players:
            return
        room_id = players[sid].get('room_id')
        room = rooms.get(room_id)
        if room is None or room.mode != 'urf':
            return
        pidx = room.player_index(sid)
        if pidx < 0:
            return
    busy_lock = _try_acquire_room_action(room, sid, 'urf_replace_card', pidx)
    if busy_lock is None:
        return
    try:
        result = room.engine.replace_hand_card(pidx, card_instance_id)
        _stamp_pending_interactions(room)
    finally:
        busy_lock.release()
    if result.get('success'):
        record_valid_player_action(room, pidx, 'urf_replace_card')
        record_room_replay_action(room, 'urf_replace_card', pidx, {'card_instance_id': card_instance_id})
        broadcast_game_state(room)
    else:
        code = normalize_soft_reject_code(result.get('error')) or 'CARD_NOT_PLAYABLE_NOW'
        soft_reject(sid, 'urf_replace_card', code, result.get('error', 'Operation failed'), room=room, pidx=pidx, send_state=True)


@socketio.on('urf_sell_equipment')
@measure_socket_action('urf_sell_equipment')
def on_urf_sell_equipment(data):
    sid = request.sid
    data = socket_guard('urf_sell_equipment', data, require_player=True)
    if data is None:
        return
    try:
        equipment_instance_id = validate_instance_id(data.get('equipment_instance_id'), name='equipment_instance_id')
    except ValueError as exc:
        _security_illegal(sid, 'urf_sell_equipment', str(exc))
        return
    with _lock:
        if sid not in players:
            return
        room_id = players[sid].get('room_id')
        room = rooms.get(room_id)
        if room is None or room.mode != 'urf':
            return
        pidx = room.player_index(sid)
        if pidx < 0:
            return
    busy_lock = _try_acquire_room_action(room, sid, 'urf_sell_equipment', pidx)
    if busy_lock is None:
        return
    try:
        result = room.engine.sell_equipment(pidx, equipment_instance_id)
        _stamp_pending_interactions(room)
    finally:
        busy_lock.release()
    if result.get('success'):
        record_valid_player_action(room, pidx, 'urf_sell_equipment')
        record_room_replay_action(room, 'urf_sell_equipment', pidx, {'equipment_instance_id': equipment_instance_id})
        broadcast_game_state(room)
    else:
        code = normalize_soft_reject_code(result.get('error')) or 'TRIGGER_NOT_PLAYABLE_NOW'
        soft_reject(sid, 'urf_sell_equipment', code, result.get('error', 'Operation failed'), room=room, pidx=pidx, send_state=True)


@socketio.on('end_turn')
@measure_socket_action('end_turn')
def on_end_turn(data):
    sid = request.sid
    data = socket_guard('end_turn', data, require_player=True, allow_empty=True)
    if data is None:
        return
    try:
        with _lock:
            if sid not in players:
                player = None
            else:
                player = players[sid]
        if player is None:
            emit('server_error', {'message': '玩家不在对局中'})
            return
        with _lock:
            room_id = player.get('room_id')
            room = rooms.get(room_id)
            if room is None:
                room = None
            else:
                pidx = room.player_index(sid)
                engine = room.engine if pidx >= 0 else None
        if room is None:
            emit('server_error', {'message': '对局不存在'})
            return
        if pidx < 0:
            emit('server_error', {'message': '你不是该对局的玩家'})
            return
        busy_lock = _try_acquire_room_action(room, sid, 'end_turn', pidx)
        if busy_lock is None:
            return
        try:
            reject_code = _room_action_precheck(engine, pidx, event_name='end_turn')
            if reject_code:
                soft_reject(sid, 'end_turn', reject_code, room=room, pidx=pidx, send_state=True)
                return
            result = engine.end_turn(pidx)
            _stamp_pending_interactions(room)
        finally:
            busy_lock.release()
        if result.get('success'):
            record_valid_player_action(room, pidx, 'end_turn')
            record_room_replay_action(room, 'end_turn', pidx, {})
            with _lock:
                _clear_room_action_timer(room)
                _sync_room_action_timer_after_state_change(room)
        broadcast_game_state(room)
        if result.get('success') and getattr(engine, 'pending_response', None):
            emit_or_resolve_pending_response(room, reason='end_turn')
        if result.get('success'):
            emit_turn_timer_update(room)
        if not result.get('success'):
            code = normalize_soft_reject_code(result.get('error')) or 'END_TURN_NOT_ALLOWED_NOW'
            soft_reject(sid, 'end_turn', code, result.get('error', 'Operation failed'), room=room, pidx=pidx, send_state=False)
    except Exception as e:
        import traceback
        traceback.print_exc()
        emit('server_error', {'message': '结束回合失败，请稍后重试'})


@socketio.on('surrender')
@measure_socket_action('surrender')
def on_surrender(data):
    sid = request.sid
    data = socket_guard('surrender', data, require_player=True, allow_empty=True)
    if data is None:
        return
    try:
        with _lock:
            if sid not in players:
                emit('server_error', {'message': '玩家不在对局中'})
                return
            player = players[sid]
            room_id = player.get('room_id')
            if room_id is None or room_id not in rooms:
                emit('server_error', {'message': '对局不存在'})
                return
            room = rooms[room_id]
            pidx = room.player_index(sid)
            if pidx < 0:
                emit('server_error', {'message': '你不是该对局的玩家'})
                return
            engine = room.engine
            def finalize_surrender(skip_reason=None):
                result = engine.surrender(pidx)
                if result.get('success'):
                    replay_payload = {'result': result}
                    if skip_reason:
                        replay_payload['teammate_consent_skipped'] = skip_reason
                    record_room_replay_action(room, 'surrender', pidx, replay_payload)
                    broadcast_game_state(room)
                    for psid in room.player_sids:
                        if psid in players:
                            socketio.emit('game_phase', {'phase': 'game_over'}, room=psid)
                else:
                    emit('server_error', {'message': result.get('error', '投降失败')})
                return result

            if room.mode == '2v2':
                teammate_id = engine.get_teammate(pidx) if hasattr(engine, 'get_teammate') else -1
                if teammate_id < 0 or teammate_id >= len(room.player_sids):
                    emit('server_error', {'message': 'Surrender requires a teammate'})
                    return
                teammate_sid = room.player_sids[teammate_id]
                teammate_offline = teammate_sid not in players or teammate_sid in room.disconnected_players
                teammate_dead = False
                try:
                    teammate_dead = engine.players[teammate_id].health <= 0
                except Exception:
                    teammate_dead = teammate_id in getattr(room, 'disconnect_timeout_defeated', set())
                if teammate_offline and teammate_dead:
                    skip_reason = 'dead_teammate_offline'
                    if teammate_id in getattr(room, 'disconnect_timeout_defeated', set()):
                        skip_reason = 'disconnect_timeout_defeated'
                    finalize_surrender(skip_reason=skip_reason)
                    return
                if teammate_offline:
                    emit('server_error', {'message': 'Teammate is not online'})
                    return
                now = time.time()
                pending = getattr(room, 'pending_surrender_request', None)
                if pending:
                    if now - float(pending.get('time', 0)) < 15:
                        emit('server_error', {'message': 'A surrender request is already pending'})
                        return
                    room.pending_surrender_request = None
                room.pending_surrender_request = {
                    'player_id': pidx,
                    'target_player_id': teammate_id,
                    'time': now,
                }
                socketio.emit('surrender_consent_waiting', {}, room=sid)
                socketio.emit('surrender_consent_request', {
                    'from_player': pidx,
                    'from_name': player.get('nickname', f'Player {pidx + 1}'),
                }, room=teammate_sid)
                return
            finalize_surrender()
    except Exception as e:
        import traceback
        traceback.print_exc()
        emit('server_error', {'message': '投降失败，请稍后重试'})


@socketio.on('surrender_consent_response')
@measure_socket_action('surrender_consent_response')
def on_surrender_consent_response(data):
    sid = request.sid
    data = socket_guard('surrender_consent_response', data, require_player=True, allow_empty=True)
    if data is None:
        return
    accepted = bool((data or {}).get('accepted'))
    try:
        with _lock:
            if sid not in players:
                emit('server_error', {'message': 'Player is not in a match'})
                return
            player = players[sid]
            room_id = player.get('room_id')
            if room_id is None or room_id not in rooms:
                emit('server_error', {'message': 'Match does not exist'})
                return
            room = rooms[room_id]
            if room.mode != '2v2':
                emit('server_error', {'message': 'Surrender consent is only used in 2v2'})
                return
            pidx = room.player_index(sid)
            if pidx < 0:
                emit('server_error', {'message': 'You are not a player in this match'})
                return
            pending = getattr(room, 'pending_surrender_request', None)
            if not pending or pending.get('target_player_id') != pidx:
                emit('server_error', {'message': 'No pending surrender request'})
                return
            if time.time() - float(pending.get('time', 0)) > 15:
                room.pending_surrender_request = None
                emit('server_error', {'message': 'No pending surrender request'})
                return
            room.pending_surrender_request = None
            requester_id = int(pending.get('player_id', -1))
            requester_sid = room.player_sids[requester_id] if 0 <= requester_id < len(room.player_sids) else None
            if not accepted:
                if requester_sid and requester_sid in players:
                    socketio.emit('surrender_consent_result', {'accepted': False}, room=requester_sid)
                emit('surrender_consent_result', {'accepted': False})
                return
            result = room.engine.surrender(requester_id)
            if result.get('success'):
                record_room_replay_action(room, 'surrender', requester_id, {
                    'consented_by': pidx,
                    'result': result,
                })
                if requester_sid and requester_sid in players:
                    socketio.emit('surrender_consent_result', {'accepted': True}, room=requester_sid)
                emit('surrender_consent_result', {'accepted': True})
                broadcast_game_state(room)
                for psid in room.player_sids:
                    if psid in players:
                        socketio.emit('game_phase', {'phase': 'game_over'}, room=psid)
            else:
                message = result.get('error', 'Surrender failed')
                if requester_sid and requester_sid in players:
                    socketio.emit('server_error', {'message': message}, room=requester_sid)
                emit('server_error', {'message': message})
    except Exception as e:
        import traceback
        traceback.print_exc()
        emit('server_error', {'message': 'Surrender failed'})


@socketio.on('rematch')
@measure_socket_action('rematch')
def on_rematch(data=None):
    sid = request.sid
    data = socket_guard('rematch', data, require_player=True, allow_empty=True)
    if data is None:
        return
    try:
        with _lock:
            if sid not in players:
                return
            player = players[sid]
            room_id = player.get('room_id')
            if room_id is None or room_id not in rooms:
                return
            room = rooms[room_id]
            if room.engine.phase != 'game_over':
                return
            if is_instance_draining():
                socketio.emit('server_error', {'message': drain_reject_payload()['reason'], 'draining': True}, room=sid)
                emit_rematch_state(room)
                return
            if getattr(room, '_returned_lobby_sids', set()):
                socketio.emit('server_error', {'message': '有玩家已返回大厅'}, room=sid)
                emit_rematch_state(room)
                return
            already_voted = sid in room._rematch_votes
            room._rematch_votes.add(sid)
            emit_rematch_state(room)
            if not already_voted and room.mode != '2v2':
                for other_sid in room.player_sids:
                    if other_sid != sid and other_sid in players:
                        socketio.emit('rematch_requested', {
                            'player_name': player['nickname'],
                            'mode': room.mode,
                            'votes': len(room._rematch_votes),
                            'total': len(room.player_sids),
                        }, room=other_sid)
            if len(room._rematch_votes) == len(room.player_sids):
                stored_allowed = set()
                if room.player_sids and room.player_sids[0] in players:
                    stored_allowed = set(players[room.player_sids[0]].get('allowed_card_ids', []))
                next_allowed = apply_runtime_content_filter(stored_allowed, room.mode) if stored_allowed else None
                pool_issue = runtime_card_pool_issue(next_allowed, room.mode) if next_allowed is not None else ''
                if pool_issue:
                    room._rematch_votes = set()
                    emit_match_start_failed(room.player_sids, pool_issue, reason='content_temporarily_disabled')
                    emit_rematch_state(room)
                    return
                room._rematch_votes = set()
                room._returned_lobby_sids = set()
                room._returned_lobby_names = {}
                room.pending_surrender_request = None
                _cancel_game_over_cleanup_timer(room)
                if room.mode == '2v2':
                    room.engine = GameEngine2v2()
                elif room.mode == 'urf':
                    room.engine = GameEngineInfiniteFire()
                else:
                    room.engine = GameEngine()
                room.engine.available_builtin_setup_card_ids = apply_runtime_content_filter(BUILTIN_SETUP_CARD_IDS, room.mode)
                room._history_recorded = False
                room.match_seq = int(getattr(room, 'match_seq', 1) or 1) + 1
                room.created_at = time.time()
                room.started_at = None
                room.pregame_deadlines = {}
                room.pregame_state_last_resend = 0.0
                room.disconnect_attempt_counts = [0 for _ in room.player_sids]
                room.chat_history = []
                room.chat_sequence = 0
                reset_room_replay(room)
                if room.player_sids and room.player_sids[0] in players:
                    room.engine.allowed_card_ids = next_allowed
                    apply_v2_loadout_to_engine(room.engine, players[room.player_sids[0]], room.mode)
                names = []
                for pidx, psid in enumerate(room.player_sids):
                    names.append(room_player_nickname(room, psid, f'Player {pidx + 1}'))
                room.engine.player_names = names
                if room.mode == 'urf':
                    if hasattr(room.engine, 'log'):
                        room.engine.log = []
                    if hasattr(room.engine, '_log_compaction_floor'):
                        room.engine._log_compaction_floor = 0
                    room.engine.start_game()
                    room.started_at = time.time()
                    record_room_replay_keyframe(room, 'game_start')
                    for psid in room.player_sids:
                        if psid in players:
                            emit_room_game_phase(room, psid, 'playing')
                    broadcast_game_state(room)
                elif room.mode == 'random_deck':
                    try:
                        start_random_deck_room(room)
                    except Exception as exc:
                        admin_event('error', f'random deck rematch failed room={room.room_id}: {exc}')
                        for psid in room.player_sids:
                            if psid in players:
                                socketio.emit('server_error', {'message': f'随机卡组生成失败：{exc}'}, room=psid)
                else:
                    room.engine.start_event_select_first()
                    record_room_replay_keyframe(room, 'event_select_start')
                    for pidx in range(len(room.player_sids)):
                        psid = room.player_sids[pidx]
                        if psid in players:
                            send_pregame_state(room, pidx)
    except Exception as e:
        import traceback
        traceback.print_exc()

@socketio.on('return_lobby')
def on_return_lobby(data=None):
    global _next_room_id
    sid = request.sid
    data = socket_guard('return_lobby', data, require_player=True, allow_empty=True)
    if data is None:
        return
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        admin_event(
            'player',
            f'{player.get("nickname", "?")} requested return_lobby status={player.get("status")} room_id={player.get("room_id")}',
            sid=sid,
            room_id=player.get('room_id'),
        )
        if player.get('spectating_room') is not None:
            _handle_leave_spectate_internal(sid)
            return
        room_id = player.get('room_id')
        if room_id is not None and room_id in rooms:
            room = rooms[room_id]
            room_phase = getattr(room.engine, 'phase', '')
            admin_event(
                'player',
                f'return_lobby handling room={room_id} room_phase={room_phase} game_over={getattr(room.engine, "game_over", False)}',
                sid=sid,
                room_id=room_id,
            )
            pidx = room.player_index(sid)
            if pidx >= 0 and not getattr(room.engine, 'game_over', False):
                current_team = _room_team_for_player(room, pidx)
                disconnected_teams = set(_room_disconnected_teams(room))
                if current_team >= 0:
                    disconnected_teams.add(current_team)
                if len(disconnected_teams) >= 2:
                    ended = _finish_room_by_health_tiebreak(room, '双方中途退出')
                else:
                    ended = _finish_room_by_forfeit(room, pidx, player.get('nickname', '?'), '中途退出')
                record_room_replay_action(room, 'player_exit', pidx, {
                    'nickname': player.get('nickname', '?'),
                    'game_over': ended,
                })
                if ended:
                    _cancel_room_reconnect_timers(room)
                    for other_sid in room.player_sids:
                        if other_sid in players:
                            payload = {'timeout': True, 'game_over': True}
                            if other_sid != sid:
                                socketio.emit('opponent_disconnected', payload, room=other_sid)
                            socketio.emit('game_phase', {'phase': 'game_over'}, room=other_sid)
                    broadcast_game_state(room)
            elif pidx >= 0 and getattr(room.engine, 'game_over', False):
                room._rematch_votes.discard(sid)
                if sid not in getattr(room, '_returned_lobby_sids', set()):
                    room._returned_lobby_sids.add(sid)
                    room._returned_lobby_names[sid] = player.get('nickname', '?')
                    payload = {
                        'player_name': player.get('nickname', '?'),
                        'reason': 'player_returned_lobby',
                    }
                    for other_sid in room.player_sids:
                        if other_sid != sid and other_sid in players and players[other_sid].get('room_id') == room_id:
                            socketio.emit('player_returned_lobby', payload, room=other_sid)
                    emit_rematch_state(room)
            if not any(psid != sid and psid in players and players[psid].get('room_id') == room_id for psid in room.player_sids) and not getattr(room, 'spectators', []):
                _cancel_game_over_cleanup_timer(room)
                rooms.pop(room_id, None)
        player['room_id'] = None
        player['status'] = 'lobby'
    broadcast_lobby()


@socketio.on('spectate')
def on_spectate(data):
    sid = request.sid
    data = socket_guard('spectate', data, require_player=True)
    if data is None:
        return
    try:
        room_id = validate_int(data.get('room_id'), minimum=0, maximum=10**9, name='room_id')
    except ValueError as exc:
        _security_illegal(sid, 'spectate', str(exc))
        return
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        if player['status'] != 'lobby':
            emit('server_error', {'message': '只有在大厅中才能观战'})
            return
        if room_id is None or room_id not in rooms:
            emit('server_error', {'message': '对局不存在'})
            return
        room = rooms[room_id]
        if bool(getattr(room, 'beta_mode', False)) != bool(player.get('beta_mode', False)):
            emit('server_error', {'message': runtime_scope_mismatch_message()})
            return
        if _player_matches_room_participant(room, player.get('nickname')):
            emit('server_error', {'message': '请返回自己的对局，不能观战自己的对局'})
            return
        if not player.get('user_id') and not room_allows_guest_spectators(room):
            emit('server_error', {'message': '本场对局有玩家开启了禁止游客观战'})
            return
        phase = room.engine.phase
        if phase in ('draft', 'event_select', 'event_reveal'):
            emit('server_error', {'message': '选牌或配装倾向阶段暂不能观战'})
            return
        if phase not in ('action', 'draw', 'playing', 'response', 'choice'):
            emit('server_error', {'message': '该对局当前不能观战'})
            return
        player['status'] = 'spectating'
        player['spectating_room'] = room_id
        player['spectate_perspective'] = 0
        if sid not in room.spectators:
            room.spectators.append(sid)
        p1 = '?'
        p2 = '?'
        if len(room.player_sids) > 0:
            p1 = room_player_nickname(room, room.player_sids[0], '?')
        if len(room.player_sids) > 1:
            p2 = room_player_nickname(room, room.player_sids[1], '?')
        emit('spectate_enter', {
            'room_id': room_id,
            'player1': p1,
            'player2': p2,
        })
        _send_spectate_state_internal(sid, room)


def _send_spectate_state_internal(spid, room):
    perspective = players.get(spid, {}).get('spectate_perspective', 0)
    state = build_spectate_state(room, perspective=perspective)
    state['your_id'] = -1
    state['spectating'] = True
    state['room_chat_history'] = room_chat_history_for_sid(room, spid, spectator=True)
    for i, psid in enumerate(room.player_sids):
        state[f'player{i + 1}_name'] = room_player_nickname(room, psid, '?')
        state[f'player{i + 1}_is_admin_player'] = player_is_admin(psid, room)
        state[f'player{i + 1}_special'] = player_special_fields(psid, room)
    socketio.emit('state_update', state, room=spid)


def _handle_leave_spectate_internal(sid):
    if sid not in players:
        return
    player = players[sid]
    room_id = player.get('spectating_room')
    if room_id is not None and room_id in rooms:
        room = rooms[room_id]
        if sid in room.spectators:
            room.spectators.remove(sid)
    player['spectating_room'] = None
    player['spectate_perspective'] = 0
    player['status'] = 'lobby'
    socketio.emit('spectate_leave', {}, room=sid)


@socketio.on('leave_spectate')
def on_leave_spectate(data=None):
    sid = request.sid
    data = socket_guard('leave_spectate', data, require_player=True, allow_empty=True)
    if data is None:
        return
    with _lock:
        _handle_leave_spectate_internal(sid)
    broadcast_lobby()


@socketio.on('switch_spectate_perspective')
def on_switch_spectate_perspective(data=None):
    sid = request.sid
    data = socket_guard('switch_spectate_perspective', data, require_player=True, allow_empty=True)
    if data is None:
        return
    with _lock:
        player = players.get(sid)
        if not player:
            return
        room_id = player.get('spectating_room')
        if room_id not in rooms:
            emit('server_error', {'message': 'not_spectating'})
            return
        room = rooms[room_id]
        total = len(room.player_sids)
        if total <= 0:
            return
        current = player.get('spectate_perspective', 0)
        try:
            current = int(current or 0)
        except (TypeError, ValueError):
            current = 0
        next_index = None
        if isinstance(data, dict) and data.get('perspective') is not None:
            try:
                requested = validate_int(data.get('perspective'), minimum=0, maximum=16, name='perspective')
                if 0 <= requested < total:
                    next_index = requested
            except (TypeError, ValueError):
                next_index = None
        if next_index is None:
            next_index = (current + 1) % total
        player['spectate_perspective'] = next_index
        _send_spectate_state_internal(sid, room)


def _seconds_until_cleanup_time():
    now = datetime.now()
    target = now.replace(hour=CLEANUP_HOUR, minute=CLEANUP_MINUTE, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return max(60, int((target - now).total_seconds()))


def _replay_cleanup_worker():
    time.sleep(60)
    while True:
        try:
            if DB_AVAILABLE and _replay_cleanup_lock.acquire(blocking=False):
                try:
                    result = cleanup_old_replays(retention_days=DEFAULT_RETENTION_DAYS, dry_run=False)
                    if result.get('deleted_replays') or result.get('deleted_mod_blobs') or result.get('deleted_card_snapshots'):
                        admin_event('admin', f'自动清理旧回放: {result}')
                finally:
                    _replay_cleanup_lock.release()
        except Exception as exc:
            admin_event('error', f'auto replay cleanup failed: {exc}')
        time.sleep(_seconds_until_cleanup_time())


def start_replay_cleanup_thread():
    global _replay_cleanup_started
    if _replay_cleanup_started:
        return
    if not db_maintenance_enabled():
        admin_event('db', 'replay cleanup disabled by GTN_DB_MAINTENANCE_ENABLED=0')
        return
    cleanup_enabled = str(os.environ.get('GTN_REPLAY_CLEANUP_ENABLED', '1')).strip().lower()
    if cleanup_enabled in {'0', 'false', 'no', 'off'}:
        return
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'false':
        return
    _replay_cleanup_started = True
    thread = threading.Thread(target=_replay_cleanup_worker, name='replay-cleanup', daemon=True)
    thread.start()


load_persisted_lobby_chat_cache()
start_replay_cleanup_thread()
ensure_friend_request_cleanup_started()
ensure_dm_cleanup_started()


if __name__ == '__main__':
    print(
        f"Starting GTN instance={GTN_INSTANCE} id={GTN_INSTANCE_ID} "
        f"version={GTN_VERSION} sha={GTN_GIT_SHA or '-'} "
        f"bind={GTN_BIND_HOST}:{GTN_PORT} draining={is_instance_draining()}",
        flush=True,
    )
    socketio.run(app, host=GTN_BIND_HOST, port=GTN_PORT, debug=False)
