import sys
import os
import re
import time
import json
import random
import threading
import copy
import shutil
import shlex
from collections import deque
from datetime import datetime, timedelta

from flask import Flask, render_template, jsonify, request, send_from_directory, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import check_password_hash
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from game_engine_urf import GameEngineInfiniteFire
from cards import (
    CardInstance, CARD_DEFS, DRAFT_RATIO, DECK_SIZE, build_draft_pool, generate_draft_options,
    INITIAL_HEALTH, INITIAL_ELIXIR, INITIAL_MAGIC, FIRST_PLAYER_ELIXIR,
    SECOND_PLAYER_HEALTH, INITIAL_HAND_SIZE, FIRST_PLAYER_HAND_SIZE, ERROR_CARD_ID,
)
from mod_loader import merge_mod_cards_to_card_defs, load_all_mods, save_mod, Mod
from card_i18n import apply_card_i18n_defaults, card_text, event_text
from runtime_errors import set_mod_runtime_error_logger
from r2_mods import (
    R2ConfigError,
    create_presigned_mod_upload,
    get_community_index,
    load_community_mod,
    register_community_mod,
    validate_community_mod_url,
)
from db import (
    admin_change_user_password,
    admin_set_user_ban,
    change_user_password,
    create_user,
    find_user_for_admin,
    get_admin_user_detail,
    get_user_by_id,
    get_user_by_username,
    increment_user_stats,
    init_db,
    list_admin_users,
    save_match_summary,
    verify_user,
)

BASE_CARD_IDS = set(CARD_DEFS.keys())
BASE_CARD_DEFS = copy.deepcopy(CARD_DEFS)
VANILLA_MOD_FILENAME = 'VanillaCardsFormatV1.json'
REQUIRED_CARD_TYPES = ('thorn', 'bloom', 'root', 'guard')

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


def current_mods_signature():
    mods_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mods')
    if not os.path.isdir(mods_dir):
        return ()
    items = []
    for filename in sorted(os.listdir(mods_dir)):
        if not filename.endswith('.json'):
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
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

DB_AVAILABLE = True
DB_INIT_ERROR = ''
try:
    init_db()
except Exception as exc:
    DB_AVAILABLE = False
    DB_INIT_ERROR = str(exc)
    print(f'[startup] database init failed: {type(exc).__name__}: {exc}')

_lock = threading.Lock()
_next_room_id = 0
_COMMUNITY_API_RATE: dict = {}
SERVER_STARTED_AT = time.time()
RECONNECT_TIMEOUT_SECONDS = int(os.environ.get('RECONNECT_TIMEOUT_SECONDS', '120'))
BOTH_DISCONNECTED_CLEANUP_SECONDS = int(os.environ.get('BOTH_DISCONNECTED_CLEANUP_SECONDS', '60'))
DEFAULT_ADMIN_PASSWORD_HASH = 'pbkdf2:sha256:260000$82e7gAIa0D6034Qq$a0c9a5ad6028ce6c8798abc1314bc74b099b2441c3f39c3b3e6255ea2156f06b'
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', DEFAULT_ADMIN_PASSWORD_HASH)
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
ADMIN_EVENTS = deque(maxlen=300)
MATCH_HISTORY = deque(maxlen=120)
ADMIN_LOGIN_FAILURES = {}
AUTH_LOGIN_FAILURES = {}

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
teams = {}
pending_team_matches = {}


def iso_now():
    return datetime.utcnow().isoformat(timespec='seconds') + 'Z'


def admin_display_time(value):
    try:
        if isinstance(value, (int, float)):
            dt = datetime.utcfromtimestamp(value)
        else:
            text = str(value or '')
            if text.endswith('Z'):
                text = text[:-1]
            dt = datetime.fromisoformat(text)
        return (dt + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
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


set_mod_runtime_error_logger(
    lambda message, **extra: admin_event('mod_error', message, **extra)
)


def admin_match_record(room, result='finished'):
    try:
        if getattr(room, '_history_recorded', False):
            return
        e = room.engine
        names = []
        registered_usernames = []
        participant_meta = []
        for psid in room.player_sids:
            if psid in players:
                p = players[psid]
                names.append(p['nickname'])
                participant_meta.append(p)
            elif psid in room.disconnected_players:
                p = room.disconnected_players[psid]
                names.append(p['nickname'])
                participant_meta.append(p)
            else:
                names.append('?')
                participant_meta.append({})
        for meta in participant_meta:
            if meta.get('user_id') and meta.get('nickname'):
                registered_usernames.append(meta['nickname'])
        winner = getattr(e, 'winner', None)
        winner_index = None
        stats_winners = []
        stats_result = 'draw'
        if getattr(e, 'winning_team', None) is not None:
            winner_index = int(e.winning_team)
            team_members = []
            try:
                team_members = list(e.teams[winner_index])
            except Exception:
                team_members = []
            stats_winners = [names[i] for i in team_members if 0 <= i < len(names)]
            winner_label = ' / '.join(stats_winners) or f"team {winner_index + 1}"
            stats_result = 'win'
        elif winner is None or winner == -1:
            winner_label = 'draw'
            stats_result = 'draw'
        elif isinstance(winner, int) and 0 <= winner < len(names):
            winner_index = winner
            winner_label = names[winner]
            stats_winners = [winner_label]
            stats_result = 'win'
        else:
            winner_label = str(winner)
            stats_winners = [winner_label]
            stats_result = 'win'
        started_ts = getattr(room, 'started_at', None) or getattr(room, 'created_at', time.time())
        created_at = datetime.utcfromtimestamp(getattr(room, 'created_at', time.time())).isoformat(timespec='seconds') + 'Z'
        started_at = datetime.utcfromtimestamp(started_ts).isoformat(timespec='seconds') + 'Z'
        ended_at = iso_now()
        duration_seconds = int(time.time() - started_ts)
        first_meta = participant_meta[0] if participant_meta else {}
        mod_source = first_meta.get('mod_source', 'official')
        mod_hash = first_meta.get('community_mod_hash') or first_meta.get('mods_hash') or ''
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
        }
        MATCH_HISTORY.appendleft(history_entry)
        summary = {
            'room_id': room.room_id,
            'mode': room.mode,
            'players': names,
            'winner_name': winner_label,
            'winner_index': winner_index,
            'rounds': getattr(e, 'round_num', 0),
            'phase': getattr(e, 'phase', ''),
            'result': stats_result if result == 'finished' else result,
            'started_at': started_at,
            'ended_at': ended_at,
            'duration_seconds': duration_seconds,
            'mod_source': mod_source,
            'mod_hash': mod_hash,
        }
        if DB_AVAILABLE:
            try:
                save_match_summary(summary)
                if result in ('finished', 'admin_endgame') and getattr(e, 'game_over', False):
                    increment_user_stats(registered_usernames, stats_winners, stats_result)
            except Exception as db_exc:
                admin_event('error', f'failed to persist match summary: {db_exc}')
        room._history_recorded = True
    except Exception as exc:
        admin_event('error', f'failed to record match history: {exc}')


def is_admin_authenticated():
    return bool(session.get('admin_authenticated'))


def admin_unauthorized():
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


def db_unavailable_response():
    return jsonify({'success': False, 'error': f'数据库不可用: {DB_INIT_ERROR or "unknown"}'}), 503


@app.before_request
def protect_admin_api():
    path = request.path.rstrip('/')
    public_paths = {'/api/admin/login', '/api/admin/me'}
    if path.startswith('/api/admin/') and path not in public_paths and not is_admin_authenticated():
        return admin_unauthorized()


class GameRoom:
    def __init__(self, room_id, player_sids, allowed_card_ids=None, mode='1v1'):
        self.room_id = room_id
        self.player_sids = list(player_sids)
        self.mode = mode
        if mode == '2v2':
            self.engine = GameEngine2v2()
        elif mode == 'urf':
            self.engine = GameEngineInfiniteFire()
        else:
            self.engine = GameEngine()
        self.engine.allowed_card_ids = set(allowed_card_ids) if allowed_card_ids is not None else None
        self.spectators = []
        self.disconnected_players = {}
        self.reconnect_timers = {}
        self._rematch_votes = set()
        self.pending_surrender_request = None
        self.team_assignments = None
        self._history_recorded = False
        self.created_at = time.time()
        self.started_at = None
        if mode == '2v2' and len(player_sids) == 4:
            self.team_assignments = [[0, 1], [2, 3]]

    def player_index(self, sid):
        if sid in self.player_sids:
            return self.player_sids.index(sid)
        return -1


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


def _player_matches_room_participant(room, nickname):
    if not nickname:
        return False
    for psid in room.player_sids:
        if psid in players and players[psid].get('nickname') == nickname:
            return True
        if psid in room.disconnected_players and room.disconnected_players[psid].get('nickname') == nickname:
            return True
    for name in getattr(room.engine, 'player_names', []) or []:
        if name == nickname:
            return True
    return False


def _force_2v2_disconnect_death(room, player_index, nickname):
    e = room.engine
    if room.mode != '2v2' or player_index < 0 or player_index >= len(getattr(e, 'players', [])):
        return False
    ps = e.players[player_index]
    was_alive = ps.health > 0
    ps.health = 0
    ps.invincible = False
    ps.bandage_active = False
    ps.bandage_death_pending = False
    ps.skip_turn = False
    if hasattr(e, '_on_player_death'):
        e._on_player_death(player_index)
    elif hasattr(e, '_check_game_over'):
        e._check_game_over()
    if was_alive:
        e.log_msg(f"{nickname}\u65ad\u7ebf\u8d85\u65f6\uff0c\u5df2\u5224\u5b9a\u9635\u4ea1\u3002")
    if not getattr(e, 'game_over', False) and getattr(e, 'current_player', None) == player_index:
        advance = getattr(e, '_advance_turn', None)
        if callable(advance):
            advance()
        else:
            e.phase = 'action'
    elif not getattr(e, 'game_over', False) and getattr(e, 'phase', None) in ('response', 'choice'):
        e.phase = 'action'
    return was_alive


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


def get_special_player_profile(raw):
    # Legacy secret-nickname login has been removed. Special display is now tied
    # to registered account usernames through get_special_account_profile().
    return None


def get_special_account_profile(username):
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
        'special_role_color': source.get('special_role_color') or ('admin' if source.get('is_admin_player') else None),
        'special_role_sort': int(source.get('special_role_sort', 99)),
    }


def player_special_fields(sid, room=None):
    if sid in players:
        return special_public_fields(players[sid])
    if room is not None and sid in getattr(room, 'disconnected_players', {}):
        return special_public_fields(room.disconnected_players[sid])
    return special_public_fields({})


def room_player_nickname(room, sid, fallback='?'):
    if sid in players:
        return players[sid].get('nickname', fallback)
    if room is not None and sid in getattr(room, 'disconnected_players', {}):
        return room.disconnected_players[sid].get('nickname', fallback)
    return fallback


def is_admin_player_secret(raw):
    return False


def is_reserved_special_nickname(name):
    lower = str(name or '').lower()
    special_names = {profile['display_name'].lower() for profile in SPECIAL_ACCOUNT_PROFILES}
    return ('sticker' in lower and 'bug' in lower) or lower in special_names


def is_exact_special_account_name(name):
    lower = str(name or '').strip().lower()
    return lower in {profile['display_name'].lower() for profile in SPECIAL_ACCOUNT_PROFILES}


def auth_user_payload(user):
    if not user:
        return None
    payload = dict(user)
    profile = get_special_account_profile(payload.get('username', ''))
    if profile:
        payload['display_name'] = profile['display_name']
        payload.update(special_public_fields(profile))
    else:
        payload['display_name'] = payload.get('username', '')
        payload.update(special_public_fields({}))
    return payload


def public_player_info(sid, player=None):
    p = player if player is not None else players.get(sid, {})
    info = {
        'sid': sid,
        'nickname': p.get('nickname', '?'),
        'mode': p.get('mode', '1v1'),
    }
    info.update(special_public_fields(p))
    return info


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
        return [x.strip() for x in value.split(',') if x.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(x).strip() for x in value if str(x).strip()]
    return []


def normalize_mod_source(value):
    return 'community' if str(value or '').strip().lower() == 'community' else 'official'


def _normalize_community_hash(value):
    text = str(value or '').strip().lower()
    return text if re.fullmatch(r'[0-9a-f]{64}', text) else ''


def _client_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'


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


def _community_request_fields(data):
    data = data or {}
    return {
        'mod_source': normalize_mod_source(data.get('mod_source')),
        'community_mod_url': str(data.get('community_mod_url') or '').strip(),
        'community_mod_hash': _normalize_community_hash(data.get('community_mod_hash')),
        'community_mod_name': str(data.get('community_mod_name') or '').strip()[:80],
    }


def merge_community_mod_to_card_defs(mod):
    if not mod:
        return []
    mod_hash = getattr(mod, 'community_sha256', '') or ''
    merged = []
    conflicts = []
    for mc in mod.cards:
        if not mc.id or mc.id == ERROR_CARD_ID:
            continue
        existing_community_hash = COMMUNITY_CARD_SOURCES.get(mc.id)
        if mc.id in CARD_DEFS and existing_community_hash != mod_hash:
            conflicts.append(mc.id)
            continue
        CARD_DEFS[mc.id] = mc.to_card_def()
        if mod_hash:
            COMMUNITY_CARD_SOURCES[mc.id] = mod_hash
        merged.append(mc.id)
    if conflicts:
        raise ValueError('社区模组卡牌ID与官方卡冲突: ' + ', '.join(sorted(conflicts)[:10]))
    if merged:
        apply_card_i18n_defaults(CARD_DEFS)
    return merged


def resolve_community_loadout(data):
    fields = _community_request_fields(data)
    if fields['mod_source'] != 'community':
        return fields, None
    if not fields['community_mod_url'] or not fields['community_mod_hash']:
        raise ValueError('缺少社区模组 URL 或 hash')
    mod = load_community_mod(fields['community_mod_url'], fields['community_mod_hash'])
    merge_community_mod_to_card_defs(mod)
    if not fields['community_mod_name']:
        fields['community_mod_name'] = mod.info.name if mod.info and mod.info.name else 'Community Mod'
    return fields, mod


def get_enabled_mod_card_type_counts(disabled_mods=None):
    disabled = set(normalize_disabled_mods(disabled_mods))
    counts = {card_type: 0 for card_type in REQUIRED_CARD_TYPES}
    for mod in load_all_mods():
        if mod.errors:
            continue
        if mod.filename in disabled:
            continue
        for card in mod.cards:
            if card.id in CARD_DEFS and card.count > 0 and card.card_type in counts:
                counts[card.card_type] += 1
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
    for mod in load_all_mods():
        if mod.errors:
            continue
        if mod.filename in disabled:
            continue
        for card in mod.cards:
            if card.id in CARD_DEFS:
                allowed.add(card.id)
    return allowed


def get_card_mod_sources(disabled_mods=None):
    disabled = set(ensure_valid_disabled_mods(disabled_mods))
    sources = {}
    for mod in load_all_mods():
        if mod.errors or mod.filename in disabled:
            continue
        info = mod.info
        mod_name = info.name if info and info.name else mod.filename
        mod_sort_name = mod_name or mod.filename
        for card in mod.cards:
            if card.id in CARD_DEFS:
                sources[card.id] = {
                    'filename': mod.filename,
                    'name': mod_name,
                    'sort_name': mod_sort_name,
                    'is_vanilla': mod.filename == VANILLA_MOD_FILENAME,
                }
    return sources


def build_mod_loadout(disabled_mods=None, community_mod=None, community_hash=''):
    mods = load_all_mods()
    disabled = set(normalize_disabled_mods(disabled_mods))
    counts = {card_type: 0 for card_type in REQUIRED_CARD_TYPES}
    for mod in mods:
        if mod.errors or mod.filename in disabled:
            continue
        for card in mod.cards:
            if card.id in CARD_DEFS and card.count > 0 and card.card_type in counts:
                counts[card.card_type] += 1
    if not all(counts.get(card_type, 0) > 0 for card_type in REQUIRED_CARD_TYPES):
        disabled.discard(VANILLA_MOD_FILENAME)
    disabled = sorted(disabled)
    disabled_set = set(disabled)
    import hashlib as _hl
    _h = _hl.sha256()
    active_mods = []
    allowed_card_ids = {ERROR_CARD_ID}
    for mod in sorted(mods, key=lambda m: m.filename):
        if mod.filename in disabled_set or mod.errors:
            continue
        active_mods.append(mod.info.name if mod.info else mod.filename)
        _h.update(f'{mod.filename}:{mod.validation_hash or ""}'.encode('utf-8'))
        for card in mod.cards:
            if card.id in CARD_DEFS:
                allowed_card_ids.add(card.id)
    if community_mod:
        label = community_mod.info.name if community_mod.info and community_mod.info.name else 'Community Mod'
        active_mods.append(label)
        _h.update(f'community:{community_hash or getattr(community_mod, "community_sha256", "")}'.encode('utf-8'))
        for card in community_mod.cards:
            if card.id in CARD_DEFS:
                allowed_card_ids.add(card.id)
    return {
        'disabled_mods': disabled,
        'mods_hash': _h.hexdigest(),
        'mods_list': active_mods,
        'allowed_card_ids': allowed_card_ids,
    }


def same_mod_loadout(sids):
    hashes = []
    for sid in sids:
        if sid not in players:
            return False
        hashes.append((
            players[sid].get('mod_source', 'official'),
            players[sid].get('community_mod_hash', ''),
            players[sid].get('mods_hash'),
        ))
    return len(set(hashes)) <= 1


def get_lobby_list():
    lobby = []
    for sid, p in players.items():
        if p['status'] == 'lobby':
            lobby.append(public_player_info(sid, p))
    lobby.sort(key=lambda item: (item.get('special_role_sort', 99), item.get('nickname', '').lower()))
    return lobby


def get_ongoing_games():
    games = []
    for rid, room in rooms.items():
        phase = room.engine.phase
        if phase in ('action', 'draw', 'response', 'choice', 'playing', 'draft', 'event_select'):
            player_names = []
            for s in room.player_sids:
                if s in players:
                    player_names.append(players[s]['nickname'])
                elif s in room.disconnected_players:
                    player_names.append(room.disconnected_players[s]['nickname'])
                else:
                    player_names.append('?')
            both_disconnected = _room_all_blocking_players_disconnected(room)
            game_info = {
                'room_id': rid,
                'player1': player_names[0] if len(player_names) > 0 else '?',
                'player2': player_names[1] if len(player_names) > 1 else '?',
                'round': room.engine.round_num,
                'phase': phase,
                'both_disconnected': both_disconnected,
                'mode': room.mode,
            }
            if room.mode == '2v2':
                game_info['player3'] = player_names[2] if len(player_names) > 2 else '?'
                game_info['player4'] = player_names[3] if len(player_names) > 3 else '?'
            games.append(game_info)
    return games


def build_admin_players():
    result = []
    for sid, p in players.items():
        result.append({
            'sid': sid,
            'nickname': p.get('nickname', '?'),
            'status': p.get('status', ''),
            'room_id': p.get('room_id'),
            'spectating_room': p.get('spectating_room'),
            'mode': p.get('mode', '1v1'),
            'mods': p.get('mods_list', []),
        })
    return result


def build_admin_rooms():
    result = []
    for rid, room in rooms.items():
        e = room.engine
        names = []
        disconnected = []
        for psid in room.player_sids:
            if psid in players:
                names.append(players[psid].get('nickname', '?'))
                disconnected.append(False)
            elif psid in room.disconnected_players:
                names.append(room.disconnected_players[psid].get('nickname', '?'))
                disconnected.append(True)
            else:
                names.append('?')
                disconnected.append(True)
        result.append({
            'room_id': rid,
            'mode': room.mode,
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


def get_runtime_metrics():
    uptime = max(0, int(time.time() - SERVER_STARTED_AT))
    root_usage = shutil.disk_usage('/')
    metrics = {
        'time': iso_now(),
        'uptime_seconds': uptime,
        'disk': {
            'path': '/',
            'total': root_usage.total,
            'used': root_usage.used,
            'free': root_usage.free,
            'percent': round(root_usage.used / root_usage.total * 100, 1) if root_usage.total else None,
            'ephemeral': True,
        },
        'process': {
            'pid': os.getpid(),
            'cpu_percent': None,
            'memory_rss': None,
        },
        'system': {
            'cpu_percent': None,
            'memory_total': None,
            'memory_used': None,
            'memory_percent': None,
        },
        'psutil_available': psutil is not None,
    }
    if psutil is not None and _PSUTIL_PROCESS is not None:
        try:
            mem = _PSUTIL_PROCESS.memory_info()
            vm = psutil.virtual_memory()
            metrics['process'].update({
                'cpu_percent': _PSUTIL_PROCESS.cpu_percent(interval=None),
                'memory_rss': mem.rss,
            })
            metrics['system'].update({
                'cpu_percent': psutil.cpu_percent(interval=None),
                'memory_total': vm.total,
                'memory_used': vm.used,
                'memory_percent': vm.percent,
            })
        except Exception as exc:
            metrics['metrics_error'] = str(exc)
    return metrics


def get_admin_status_payload():
    with _lock:
        player_list = build_admin_players()
        room_list = build_admin_rooms()
        spectator_count = sum(1 for p in players.values() if p.get('status') == 'spectating')
        return {
            'success': True,
            'metrics': get_runtime_metrics(),
            'summary': {
                'online_players': len(player_list),
                'lobby_players': sum(1 for p in player_list if p['status'] == 'lobby'),
                'rooms': len(room_list),
                'spectators': spectator_count,
                'history_count': len(MATCH_HISTORY),
            },
            'players': player_list,
            'rooms': room_list,
            'events': list(ADMIN_EVENTS)[:120],
            'history': list(MATCH_HISTORY)[:80],
        }


ADMIN_COMMANDS = {
    'help': 'help - 显示可用指令',
    'status': 'status - 显示服务器摘要',
    'players': 'players - 列出在线玩家',
    'rooms': 'rooms - 列出当前对局',
    'roomplayers': 'roomplayers <房间ID> - 显示房间内玩家编号、昵称和状态',
    'logs': 'logs [数量] - 查看最近管理事件',
    'history': 'history [数量] - 查看最近历史对局',
    'broadcast': 'broadcast <内容> - 发送服务器广播',
    'kick': 'kick <sid|昵称> - 踢出玩家',
    'userpass': 'userpass <账号ID|用户名> <新密码> - 管理员修改账号密码',
    'banuser': 'banuser <账号ID|用户名> [原因] - 封禁账号并踢下线',
    'unbanuser': 'unbanuser <账号ID|用户名> - 解除账号封禁',
    'skip': 'skip <房间ID> - 尝试跳过当前回合',
    'endgame': 'endgame <房间ID> <winner|draw> - 强制结束对局；winner 可用 0/1，2v2 表示队伍',
    'set': 'set <房间ID> <玩家序号> <h|e|m|armor|dodge|poison|burn|toxic|vulnerable> <数值>',
    'givecard': 'givecard <房间ID> <玩家序号> <卡牌ID> [数量] [tags=tag1,tag2] [fusion=层数] [fission=层数] - 向玩家手牌加入卡牌',
    'clear': 'clear - 清空终端输出',
}


def command_error(command, pointer=0, expected=''):
    caret = ' ' * max(0, pointer) + '^'
    detail = f'\n需要：{expected}' if expected else ''
    return f'未知或不完整的指令\n{command}\n{caret}{detail}'


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


def make_admin_card_instance(card_id, options):
    card = CardInstance(def_id=card_id)
    tags = [t for t in options.get('tags', []) if t]
    if tags:
        card.instance_flags = set(getattr(card, 'instance_flags', set()) or set())
        card.instance_flags.update(tags)
    fusion = int(options.get('fusion', 1) or 1)
    fission = int(options.get('fission', 1) or 1)
    card.fusion_level = max(1, fusion)
    card.fission_level = max(1, fission)
    card.fusion_multiplier = float(card.fusion_level)
    card.fission_count = max(0, card.fission_level - 1)
    return card


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
        'event_select': '开局事件',
        'game_over': '结束',
    }.get(value, value)


def execute_admin_command(line):
    raw = (line or '').strip()
    if not raw:
        return {'success': False, 'output': command_error('', 0, '指令')}
    try:
        parts = shlex.split(raw)
    except ValueError as exc:
        return {'success': False, 'output': f'指令解析失败：{exc}'}
    cmd = parts[0].lower()
    if cmd == 'help':
        return {'success': True, 'output': '\n'.join(ADMIN_COMMANDS.values())}
    if cmd == 'clear':
        return {'success': True, 'output': '', 'clear': True}
    if cmd == 'status':
        payload = get_admin_status_payload()
        summary = payload['summary']
        metrics = payload['metrics']
        return {'success': True, 'output': (
            f"在线：{summary['online_players']} | 大厅：{summary['lobby_players']} | "
            f"对局：{summary['rooms']} | 观战：{summary['spectators']}\n"
            f"运行时间：{metrics['uptime_seconds']} 秒 | "
            f"CPU：进程 {metrics['process']['cpu_percent']}% / 系统 {metrics['system']['cpu_percent']}% | "
            f"进程内存：{metrics['process']['memory_rss']} 字节"
        )}
    if cmd == 'players':
        with _lock:
            rows = build_admin_players()
        if not rows:
            return {'success': True, 'output': '当前没有在线玩家。'}
        return {'success': True, 'output': '\n'.join(
            f"{p['nickname']} [{p['sid']}] 状态={zh_status(p['status'])} 房间={p.get('room_id')}" for p in rows
        )}
    if cmd == 'rooms':
        with _lock:
            rows = build_admin_rooms()
        if not rows:
            return {'success': True, 'output': '当前没有进行中的对局。'}
        return {'success': True, 'output': '\n'.join(
            f"#{r['room_id']} {r['mode']} 阶段={zh_phase(r['phase'])} 回合={r['round']} 观战={r['spectators']} 玩家={' vs '.join(r['players'])}"
            for r in rows
        )}
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
                    online = '在线'
                elif sid in room.disconnected_players:
                    nickname = room.disconnected_players[sid].get('nickname', '?')
                    online = '断线'
                else:
                    nickname = '?'
                    online = '未知'
                ps = e.players[pidx] if pidx < len(e.players) else None
                team = ''
                if room.mode == '2v2' and hasattr(e, 'team_of'):
                    team = f" 队伍={e.team_of(pidx)}"
                if ps is not None:
                    rows.append(
                        f"{pidx}: {nickname} [{sid}] {online}{team} "
                        f"H={ps.health}/{ps.max_health} E={ps.elixir}/{ps.max_elixir} M={ps.magic}/{ps.max_magic} 手牌={len(ps.hand)}"
                    )
                else:
                    rows.append(f"{pidx}: {nickname} [{sid}] {online}{team}")
        return {'success': True, 'output': '\n'.join(rows) or '房间内没有玩家。'}
    if cmd == 'logs':
        count = parse_int_token(parts[1], 'count') if len(parts) > 1 else 20
        rows = list(ADMIN_EVENTS)[:max(1, min(count, 120))]
        return {'success': True, 'output': '\n'.join(f"{admin_display_time(e.get('time'))} [{e['kind']}] {e['message']}" for e in rows) or '暂无日志。'}
    if cmd == 'history':
        count = parse_int_token(parts[1], 'count') if len(parts) > 1 else 20
        rows = list(MATCH_HISTORY)[:max(1, min(count, 80))]
        return {'success': True, 'output': '\n'.join(
            f"{admin_display_time(h.get('time'))} #{h['room_id']} {h['mode']} 回合={h['round']} 胜者={h['winner']} 玩家={' vs '.join(h['players'])}"
            for h in rows
        ) or '暂无历史对局。'}
    if cmd == 'broadcast':
        msg = raw[len(parts[0]):].strip()
        if not msg:
            return {'success': False, 'output': command_error(raw, len(raw), '<内容>')}
        socketio.emit('server_broadcast', {'message': msg})
        admin_event('admin', f'broadcast: {msg}')
        return {'success': True, 'output': f'已发送广播：{msg}'}
    if cmd in ('userpass', 'passwd', 'setpass'):
        if len(parts) < 3:
            return {'success': False, 'output': command_error(raw, len(raw), '<账号ID|用户名> <新密码>')}
        user, error = admin_change_user_password(parts[1], parts[2])
        if error:
            return {'success': False, 'output': error}
        admin_event('admin', f"changed password for account {user['username']}#{user['id']}")
        return {'success': True, 'output': f"已修改账号 {user['username']} (ID {user['id']}) 的密码。"}
    if cmd in ('banuser', 'banaccount'):
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), '<账号ID|用户名> [原因]')}
        reason = raw.split(None, 2)[2].strip() if len(raw.split(None, 2)) >= 3 else ''
        user, error = admin_set_user_ban(parts[1], True, reason)
        if error:
            return {'success': False, 'output': error}
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
            socketio.emit('kicked', {'reason': 'account banned'}, room=sid)
        if kicked:
            broadcast_lobby()
        admin_event('admin', f"banned account {user['username']}#{user['id']}: {reason or '-'}")
        suffix = f" 原因：{reason}" if reason else ''
        return {'success': True, 'output': f"已封禁账号 {user['username']} (ID {user['id']})。已踢出在线会话 {len(kicked)} 个。{suffix}"}
    if cmd in ('unbanuser', 'unbanaccount'):
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), '<账号ID|用户名>')}
        user, error = admin_set_user_ban(parts[1], False, '')
        if error:
            return {'success': False, 'output': error}
        admin_event('admin', f"unbanned account {user['username']}#{user['id']}")
        return {'success': True, 'output': f"已解除账号 {user['username']} (ID {user['id']}) 的封禁。"}
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
    if cmd == 'skip':
        if len(parts) < 2:
            return {'success': False, 'output': command_error(raw, len(raw), '<房间ID>')}
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
            return {'success': False, 'output': command_error(raw, len(raw), '<房间ID> <winner|draw>')}
        room_id = parse_int_token(parts[1], 'room_id')
        winner_token = parts[2].lower()
        with _lock:
            if room_id not in rooms:
                return {'success': False, 'output': f'不存在房间：{room_id}'}
            room = rooms[room_id]
            e = room.engine
            if winner_token in ('draw', '-1'):
                for ps in e.players:
                    ps.health = 0
            else:
                winner = parse_int_token(winner_token, 'winner')
                if room.mode == '2v2':
                    if winner not in (0, 1):
                        return {'success': False, 'output': '2v2 的胜者必须是队伍 0、队伍 1 或 draw'}
                    losing_team = 1 - winner
                    for pidx in e.teams[losing_team]:
                        e.players[pidx].health = 0
                else:
                    if winner not in (0, 1):
                        return {'success': False, 'output': '胜者必须是 0、1 或 draw'}
                    e.players[1 - winner].health = 0
            e._check_game_over()
            admin_match_record(room, result='admin_endgame')
            broadcast_game_state(room)
        admin_event('admin', f'endgame room {room_id} winner={winner_token}')
        return {'success': True, 'output': f'已强制结束房间 {room_id}'}
    if cmd == 'set':
        if len(parts) < 5:
            return {'success': False, 'output': command_error(raw, len(raw), '<房间ID> <玩家序号> <属性> <数值>')}
        room_id = parse_int_token(parts[1], 'room_id')
        pidx = parse_int_token(parts[2], 'player_index')
        key = parts[3].lower()
        val = parse_int_token(parts[4], 'value')
        ok, output = set_room_player_attr(room_id, pidx, key, val)
        if ok:
            admin_event('admin', f'set room {room_id} player {pidx} {key}={val}')
        return {'success': ok, 'output': output}
    if cmd in ('givecard', 'addcard', 'give'):
        if len(parts) < 4:
            return {'success': False, 'output': command_error(raw, len(raw), '<房间ID> <玩家序号> <卡牌ID> [数量] [tags=tag1,tag2] [fusion=层数] [fission=层数]')}
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
    return {'success': False, 'output': command_error(raw, 0, '有效指令')}


def admin_completions(line):
    raw = line or ''
    try:
        parts = shlex.split(raw)
    except ValueError:
        parts = raw.split()
    trailing_space = raw.endswith(' ')
    token = '' if trailing_space else (parts[-1] if parts else '')
    position = len(parts) if trailing_space else max(0, len(parts) - 1)
    if position == 0:
        return [c for c in ADMIN_COMMANDS if c.startswith(token.lower())]
    cmd = parts[0].lower() if parts else ''
    if cmd in ('kick',) and position == 1:
        values = []
        with _lock:
            for sid, p in players.items():
                values.append(p.get('nickname', ''))
                values.append(sid)
        return [v for v in values if v and v.lower().startswith(token.lower())][:20]
    if cmd in ('skip', 'endgame', 'set', 'givecard', 'addcard', 'give', 'roomplayers', 'rplayers', 'rp') and position == 1:
        with _lock:
            values = [str(rid) for rid in rooms.keys()]
        return [v for v in values if v.startswith(token)]
    if cmd in ('givecard', 'addcard', 'give') and position == 3:
        values = sorted(CARD_DEFS.keys())
        return [v for v in values if v.lower().startswith(token.lower())][:30]
    if cmd in ('givecard', 'addcard', 'give') and position >= 4:
        values = ['tags=', 'fusion=', 'fission=', 'count=']
        return [v for v in values if v.lower().startswith(token.lower())]
    if cmd in ('userpass', 'passwd', 'setpass', 'banuser', 'banaccount', 'unbanuser', 'unbanaccount') and position == 1:
        try:
            rows = list_admin_users(query=token, sort='username', order='asc', limit=30).get('users', [])
            values = []
            for user in rows:
                values.append(str(user.get('id')))
                values.append(user.get('username', ''))
            return [v for v in values if v and v.lower().startswith(token.lower())][:30]
        except Exception:
            return []
    if cmd == 'set' and position == 3:
        values = ['h', 'e', 'm', 'armor', 'dodge', 'poison', 'burn', 'toxic', 'vulnerable']
        return [v for v in values if v.startswith(token.lower())]
    if cmd == 'endgame' and position == 2:
        values = ['0', '1', 'draw']
        return [v for v in values if v.startswith(token.lower())]
    return []


def remove_player_by_admin(sid):
    if sid not in players:
        return None
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


def set_room_player_attr(room_id, pidx, key, val):
    attr_map = {
        'h': 'health', 'e': 'elixir', 'm': 'magic',
        'armor': 'armor', 'dodge': 'dodge', 'poison': 'poison',
        'burn': 'fire', 'toxic': 'toxic', 'vulnerable': 'vulnerable',
    }
    attr = attr_map.get(key)
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
        setattr(ps, attr, val)
        if key == 'h':
            ps.base_max_health = max(ps.base_max_health, val)
            ps.max_health = max(ps.max_health, val)
            e._check_game_over()
        elif key == 'e':
            ps.max_elixir = max(ps.max_elixir, val)
        elif key == 'm':
            ps.max_magic = max(ps.max_magic, val)
        broadcast_game_state(room)
    return True, f'已设置房间 {room_id} 的玩家 {pidx}：{key}={val}'


def broadcast_lobby():
    lobby_list = get_lobby_list()
    ongoing = get_ongoing_games()
    team_list = []
    seen_teams = set()
    for sid, team in teams.items():
        team_id = id(team)
        if team_id not in seen_teams:
            seen_teams.add(team_id)
            member_infos = [public_player_info(ms, players[ms]) for ms in team['members'] if ms in players]
            team_list.append({
                'leader': team['leader'],
                'members': [info['nickname'] for info in member_infos],
                'member_infos': member_infos,
                'member_sids': team['members'],
                'has_admin_player': any(info.get('is_admin_player') for info in member_infos),
                'special_role_sort': min([info.get('special_role_sort', 99) for info in member_infos] or [99]),
            })
    team_list.sort(key=lambda item: (
        item.get('special_role_sort', 99),
        ' '.join(item.get('members') or []).lower()
    ))
    for sid, p in players.items():
        if p['status'] == 'lobby':
            socketio.emit('lobby_update', {
                'players': lobby_list,
                'your_sid': sid,
                'ongoing_games': ongoing,
                'teams': team_list,
                'your_team': teams[sid]['members'] if sid in teams else None,
                'your_team_leader': teams[sid]['leader'] if sid in teams else None,
                'your_mode': p.get('mode', '1v1'),
            }, room=sid)
    print("[server] debug")


def send_draft_state(room, pidx):
    sid = room.player_sids[pidx]
    if sid not in players:
        return
    engine = room.engine
    options = engine.draft_options[pidx]
    picks = engine.draft_picks[pidx]
    rerolls = engine.draft_rerolls[pidx]
    others_picks_count = {}
    if room.mode == '2v2':
        for i in range(4):
            if i != pidx:
                others_picks_count[i] = len(engine.draft_picks[i])
    else:
        opp_pidx = 1 - pidx
        others_picks_count[opp_pidx] = len(engine.draft_picks[opp_pidx])
    socketio.emit('draft_state', {
        'options': [c.to_dict() for c in options],
        'picks': picks,
        'rerolls': rerolls,
        'round': len(picks) + 1,
        'total_rounds': DECK_SIZE,
        'others_picks_count': others_picks_count,
        'mode': room.mode,
        'player_names': engine.player_names,
    }, room=sid)


def send_event_state(room, pidx):
    sid = room.player_sids[pidx]
    if sid not in players:
        return
    engine = room.engine
    events = engine.opening_event_options[pidx]
    others_selected = {}
    if room.mode == '2v2':
        for i in range(4):
            if i != pidx:
                others_selected[i] = engine.opening_event_picks[i] is not None
    else:
        opp_idx = 1 - pidx
        others_selected[opp_idx] = engine.opening_event_picks[opp_idx] is not None
    socketio.emit('event_select', {
        'events': events,
        'others_selected': others_selected,
        'my_pick': engine.opening_event_picks[pidx],
        'magic_options': engine.opening_event_magic_options[pidx],
        'draft_picks': engine.draft_picks[pidx],
        'mode': room.mode,
        'player_names': engine.player_names,
    }, room=sid)


def broadcast_game_state(room):
    for pidx, sid in enumerate(room.player_sids):
        if sid not in players:
            continue
        state = room.engine.get_public_state(pidx)
        state['your_id'] = pidx
        state['mode'] = room.mode
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
        socketio.emit('state_update', state, room=sid)
    broadcast_spectate_state(room)
    if room.engine.game_over and not getattr(room, '_history_recorded', False):
        admin_match_record(room)
        room._history_recorded = True
        admin_event('game', f'room {room.room_id} finished')


def send_game_state_to(room, pidx):
    sid = room.player_sids[pidx]
    if sid not in players:
        return
    phase = room.engine.phase
    socketio.emit('game_phase', {'phase': phase}, room=sid)
    if phase == 'event_select':
        send_event_state(room, pidx)
    elif phase == 'draft':
        send_draft_state(room, pidx)
    else:
        state = room.engine.get_public_state(pidx)
        state['your_id'] = pidx
        state['mode'] = room.mode
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
        socketio.emit('state_update', state, room=sid)


def start_event_select(room):
    for pi in range(len(room.player_sids)):
        send_event_state(room, pi)


def start_game(room):
    room.engine.start_game()
    room.started_at = time.time()
    admin_event('game', f'room {room.room_id} started mode={room.mode}')
    for sid in room.player_sids:
        if sid in players:
            socketio.emit('game_phase', {'phase': 'playing'}, room=sid)
    broadcast_game_state(room)


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


def create_solo_engine(deck0, deck1, event0=None, event1=None, sub0=None, sub1=None, player_names=None, start_label='单人训练场开始'):
    engine = GameEngine()
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
    for i in range(2):
        if engine.opening_event_picks[i] is not None:
            engine._apply_opening_event(i)
    for i in range(2):
        if i == engine.first_player:
            hand_size = FIRST_PLAYER_HAND_SIZE
            if engine.opening_event_picks[i] == 7 and len(force_first) == 1:
                hand_size = 4
                engine.players[i].elixir += 3
            engine.players[i].draw_cards(hand_size)
        else:
            engine.players[i].draw_cards(INITIAL_HAND_SIZE)
    engine.log_msg(f"{start_label}！{engine.pn(engine.first_player)}先手。")
    engine.log_msg(f"=== 第{engine.round_num}回合 ===")
    engine._start_player_turn(engine.first_player)
    return engine


def send_solo_state(sid, perspective=None):
    engine = solo_sessions.get(sid)
    if not engine:
        return
    is_tutorial = sid in tutorial_sessions
    if perspective is None:
        perspective = 0 if is_tutorial else (engine.current_player if not engine.game_over else 0)
    state = engine.get_public_state(perspective)
    state['your_id'] = perspective
    if is_tutorial:
        state['your_name'] = '你'
        state['opponent_name'] = '练习对手'
        state['tutorial'] = True
    else:
        state['your_name'] = 'Player A' if perspective == 0 else 'Player B'
        state['opponent_name'] = 'Player B' if perspective == 0 else 'Player A'
    state['solo'] = True
    socketio.emit('solo_state', state, room=sid)


def emit_solo_response_request(sid, engine, pidx, played_card):
    opp_pidx = 1 - pidx
    played_def = CARD_DEFS.get(played_card.get('def_id', ''), None)
    trigger_types = []
    if played_def:
        if played_def.card_type == 'thorn':
            trigger_types.append('thorn')
        elif played_def.card_type == 'bloom':
            trigger_types.append('bloom')
        elif played_def.card_type == 'root':
            trigger_types.append('root')
        if played_def.id in ('Sewage', 'MagicSewage'):
            trigger_types.append('equipment_destroy')
        trigger_types.append('any')
    counter_cards = []
    for tt in trigger_types:
        counter_cards.extend(engine.get_counter_cards(opp_pidx, tt))
    socketio.emit('response_request', {
        'card': played_card,
        'counter_cards': [c.to_dict() for c in counter_cards],
    }, room=sid)


def broadcast_spectate_state(room):
    for spid in room.spectators:
        if spid not in players:
            continue
        state = build_spectate_state(room)
        state['your_id'] = -1
        state['spectating'] = True
        for i, psid in enumerate(room.player_sids):
            state[f'player{i + 1}_name'] = players[psid]['nickname'] if psid in players else room.disconnected_players.get(psid, {}).get('nickname', '?')
        socketio.emit('state_update', state, room=spid)


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


def build_spectate_state(room):
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
        pdata['name'] = players[psid]['nickname'] if psid in players else room.disconnected_players.get(psid, {}).get('nickname', f'P{i + 1}')
        pdata['is_admin_player'] = player_is_admin(psid, room)
        pdata.update(player_special_fields(psid, room))
        full_players.append(pdata)
    base['spectate_players'] = full_players
    base['player_names'] = [p.get('name', f'P{i + 1}') for i, p in enumerate(full_players)]
    for i, pdata in enumerate(full_players):
        base[f'player{i + 1}_name'] = pdata.get('name', f'P{i + 1}')
    base['mode'] = room.mode
    if room.mode == '2v2' and len(full_players) >= 4:
        base['you'] = full_players[0]
        base['teammate'] = full_players[1]
        base['opponent'] = full_players[2]
        base['opponent2'] = full_players[3]
        base['your_id'] = 0
        base['teammate_id'] = 1
        base['enemy_ids'] = [2, 3]
        base['your_name'] = full_players[0]['name']
        base['your_is_admin_player'] = full_players[0].get('is_admin_player', False)
        base['your_special'] = special_public_fields(full_players[0])
        base['teammate_name'] = full_players[1]['name']
        base['teammate_is_admin_player'] = full_players[1].get('is_admin_player', False)
        base['teammate_special'] = special_public_fields(full_players[1])
        base['opponent_names'] = [full_players[2]['name'], full_players[3]['name']]
        base['opponent_admin_flags'] = [full_players[2].get('is_admin_player', False), full_players[3].get('is_admin_player', False)]
        base['opponent_specials'] = [special_public_fields(full_players[2]), special_public_fields(full_players[3])]
    elif len(full_players) >= 2:
        base['you'] = full_players[0]
        base['opponent'] = full_players[1]
        base['your_id'] = 0
        base['your_name'] = full_players[0]['name']
        base['your_is_admin_player'] = full_players[0].get('is_admin_player', False)
        base['your_special'] = special_public_fields(full_players[0])
        base['opponent_name'] = full_players[1]['name']
        base['opponent_is_admin_player'] = full_players[1].get('is_admin_player', False)
        base['opponent_special'] = special_public_fields(full_players[1])
    return base


def _mark_disconnect_timeout_loss(room, player_index, nickname):
    e = room.engine
    if getattr(e, 'game_over', False):
        return False
    if player_index < 0 or player_index >= len(getattr(e, 'players', [])):
        return False
    e.pending_response = None
    e.pending_choice = None
    if hasattr(e, 'pending_ally_request'):
        e.pending_ally_request = None
    room.pending_surrender_request = None
    if room.mode == '2v2' and hasattr(e, 'team_of'):
        _force_2v2_disconnect_death(room, player_index, nickname)
        return bool(getattr(e, 'game_over', False))
    winner = 1 - player_index
    e.players[player_index].health = 0
    e.game_over = True
    e.winner = winner
    e.phase = 'game_over'
    e.log_msg(f"{nickname}断线超时，{e.pn(winner)}获胜！")
    return True


def reconnect_timeout(room_id, old_sid):
    global _next_room_id
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
        if room.mode == '2v2':
            if ended:
                for t in room.reconnect_timers.values():
                    t.cancel()
                room.reconnect_timers.clear()
                if hasattr(room, 'both_dc_timer') and room.both_dc_timer:
                    room.both_dc_timer.cancel()
                    room.both_dc_timer = None
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
                            'opponent_nickname': dc_info.get('nickname', '?'),
                        }, room=other_sid)
            admin_event('game', f'room {room_id} disconnect timeout death: {dc_info.get("nickname", "?")}')
            broadcast_game_state(room)
            broadcast_lobby()
            return

        for t in room.reconnect_timers.values():
            t.cancel()
        room.reconnect_timers.clear()
        if hasattr(room, 'both_dc_timer') and room.both_dc_timer:
            room.both_dc_timer.cancel()
            room.both_dc_timer = None
        if ended:
            for other_sid in room.player_sids:
                if other_sid in players:
                    socketio.emit('opponent_disconnected', {'timeout': True, 'game_over': True}, room=other_sid)
                    socketio.emit('game_phase', {'phase': 'game_over'}, room=other_sid)
            admin_event('game', f'room {room_id} disconnect timeout loss: {dc_info.get("nickname", "?")}')
            broadcast_game_state(room)
        for sid, p in players.items():
            if p['status'] == 'reconnecting' and p['nickname'] == dc_info['nickname']:
                p['status'] = 'lobby'
                socketio.emit('reconnect_timeout', {}, room=sid)
    broadcast_lobby()


def both_disconnected_cleanup(room_id):
    global _next_room_id
    with _lock:
        if room_id not in rooms:
            return
        room = rooms[room_id]
        for t in room.reconnect_timers.values():
            t.cancel()
        room.reconnect_timers.clear()
        if hasattr(room, 'both_dc_timer'):
            room.both_dc_timer = None
        del rooms[room_id]
    broadcast_lobby()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/fonts/<path:filename>')
def serve_font(filename):
    fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'fonts')
    mimetype = 'font/woff2' if filename.endswith('.woff2') else None
    response = send_from_directory(fonts_dir, filename, mimetype=mimetype)
    if filename.endswith('.woff2') or filename.endswith('.ttf'):
        response.headers['Cache-Control'] = 'public, max-age=604800'
    return response


@app.route('/admin', methods=['GET', 'POST'])
def admin_fake_login():
    return render_template('admin_fake.html', fake_error='密码错误。' if request.method == 'POST' else '')


@app.route('/adminpage')
def admin_page():
    return render_template('adminpage.html')


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


@app.route('/api/admin/status')
def admin_status():
    return jsonify(get_admin_status_payload())


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
    try:
        data = list_admin_users(
            query=request.args.get('query', ''),
            sort=request.args.get('sort', 'last_login_at'),
            order=request.args.get('order', 'desc'),
            limit=request.args.get('limit', 100),
            offset=request.args.get('offset', 0),
        )
    except Exception as exc:
        admin_event('error', f'admin users query failed: {exc}')
        return jsonify({'success': False, 'error': '账号数据库不可用'}), 500
    with _lock:
        online = _admin_online_user_map()
    for user in data.get('users', []):
        user['online'] = online.get(str(user.get('username', '')).lower())
    return jsonify({'success': True, **data})


@app.route('/api/admin/users/<int:user_id>')
def admin_user_detail(user_id):
    try:
        detail = get_admin_user_detail(user_id, request.args.get('match_limit', 30))
    except Exception as exc:
        admin_event('error', f'admin user detail failed: {exc}')
        return jsonify({'success': False, 'error': '账号数据库不可用'}), 500
    if not detail:
        return jsonify({'success': False, 'error': '用户不存在'}), 404
    with _lock:
        online = _admin_online_user_map()
    detail['user']['online'] = online.get(str(detail['user'].get('username', '')).lower())
    return jsonify({'success': True, **detail})


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


@app.route('/api/auth/register', methods=['POST'])
def api_auth_register():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    data = request.get_json(silent=True) or {}
    username = sanitize_nickname(data.get('username', ''))
    password = data.get('password', '')
    if 'password_confirm' in data and str(password) != str(data.get('password_confirm', '')):
        return jsonify({'success': False, 'error': '两次输入的密码不一致'}), 400
    user, error = create_user(username, password)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    session['user_id'] = user['id']
    session['username'] = user['username']
    return jsonify({'success': True, 'user': auth_user_payload(user)})


@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    ip = _client_ip()
    if should_rate_limit_auth_login(ip):
        return jsonify({'success': False, 'error': '登录失败次数过多，请稍后再试'}), 429
    data = request.get_json(silent=True) or {}
    user, error = verify_user(data.get('username', ''), data.get('password', ''))
    if error:
        record_auth_login_failure(ip)
        return jsonify({'success': False, 'error': error}), 401
    clear_auth_login_failures(ip)
    session['user_id'] = user['id']
    session['username'] = user['username']
    return jsonify({'success': True, 'user': auth_user_payload(user)})


@app.route('/api/auth/change-password', methods=['POST'])
def api_auth_change_password():
    if not DB_AVAILABLE:
        return db_unavailable_response()
    user_id = session.get('user_id')
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
    session['user_id'] = user['id']
    session['username'] = user['username']
    return jsonify({'success': True, 'user': auth_user_payload(user)})


@app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return jsonify({'success': True})


@app.route('/api/auth/me')
def api_auth_me():
    if not DB_AVAILABLE:
        return jsonify({'authenticated': False, 'db_available': False, 'error': DB_INIT_ERROR})
    user = get_user_by_id(session.get('user_id'))
    if not user:
        session.pop('user_id', None)
        session.pop('username', None)
        return jsonify({'authenticated': False, 'db_available': True})
    if user.get('banned'):
        session.pop('user_id', None)
        session.pop('username', None)
        reason = user.get('ban_reason') or ''
        return jsonify({
            'authenticated': False,
            'db_available': True,
            'error': f'账号已被封禁：{reason}' if reason else '账号已被封禁',
        })
    session['username'] = user['username']
    return jsonify({'authenticated': True, 'db_available': True, 'user': auth_user_payload(user)})


@app.route('/api/cards')
def api_cards():
    try:
        reload_mod_card_defs()
    except Exception as exc:
        admin_event('error', f'failed to reload mod card defs: {exc}')
    disabled_mods = request.args.get('disabled_mods', '')
    try:
        community_fields, community_mod = resolve_community_loadout(request.args)
    except Exception as exc:
        return _json_error(str(exc), 400)
    loadout = build_mod_loadout(
        disabled_mods,
        community_mod=community_mod,
        community_hash=community_fields.get('community_mod_hash', ''),
    )
    allowed_card_ids = loadout['allowed_card_ids']
    card_mod_sources = get_card_mod_sources(disabled_mods)
    if community_mod:
        community_name = community_mod.info.name if community_mod.info and community_mod.info.name else 'Community Mod'
        for card in community_mod.cards:
            if card.id in CARD_DEFS:
                card_mod_sources[card.id] = {
                    'filename': community_fields.get('community_mod_hash', ''),
                    'name': community_name,
                    'sort_name': community_name,
                    'is_vanilla': False,
                    'is_community': True,
                }
    result = {}
    for def_id, card_def in CARD_DEFS.items():
        if def_id not in allowed_card_ids:
            continue
        source = card_mod_sources.get(def_id, {})
        card_payload = {
            'id': card_def.id,
            'name_en': card_def.name_en,
            'name_cn': card_def.name_cn,
            'source_mod_filename': source.get('filename', ''),
            'source_mod_name': source.get('name', ''),
            'source_mod_sort_name': source.get('sort_name', ''),
            'source_mod_is_vanilla': bool(source.get('is_vanilla', False)),
            'source_mod_is_community': bool(source.get('is_community', False)),
            'cost_e': card_def.cost_e,
            'cost_m': card_def.cost_m,
            'card_type': card_def.card_type,
            'count': card_def.count,
            'quality': card_def.quality,
            'description': card_def.description,
            'effect_text': card_def.effect_text,
            'flags': list(card_def.flags) if card_def.flags else [],
            'trigger_cost_e': card_def.trigger_cost_e,
            'trigger_effect_text': card_def.trigger_effect_text,
            'response_trigger': card_def.response_trigger,
            'response_title': getattr(card_def, 'response_title', ''),
            'response_content': getattr(card_def, 'response_content', ''),
            'effects': card_def.effects,
            'scripts': getattr(card_def, 'scripts', {}) or {},
        }
        card_payload.update(card_text(def_id, card_payload))
        result[def_id] = card_payload
    return jsonify(result)


@app.route('/api/opening-events')
def api_opening_events():
    try:
        reload_mod_card_defs()
    except Exception as exc:
        admin_event('error', f'failed to reload mod card defs: {exc}')
    try:
        community_fields, community_mod = resolve_community_loadout(request.args)
    except Exception as exc:
        return _json_error(str(exc), 400)
    loadout = build_mod_loadout(
        request.args.get('disabled_mods', ''),
        community_mod=community_mod,
        community_hash=community_fields.get('community_mod_hash', ''),
    )
    allowed_card_ids = loadout['allowed_card_ids']
    events = []
    for event_id in sorted(GameEngine.OPENING_EVENTS.keys()):
        events.append(event_text(event_id, dict(GameEngine.OPENING_EVENTS[event_id])))
    return jsonify({
        'events': events,
        'magic_pool': [def_id for def_id in GameEngine.MAGIC_CARD_POOL if def_id in allowed_card_ids],
    })


@app.route('/api/mods')
def api_mods():
    mods = load_all_mods()
    result = []
    for mod in mods:
        d = mod.to_dict(include_validation=True)
        d['filename'] = mod.filename
        d['is_vanilla'] = mod.filename == VANILLA_MOD_FILENAME
        d['card_type_counts'] = {
            card_type: sum(1 for card in mod.cards if card.card_type == card_type and card.count > 0)
            for card_type in REQUIRED_CARD_TYPES
        }
        result.append(d)
    return jsonify(result)


@app.route('/api/community-mods')
def api_community_mods():
    try:
        index = get_community_index()
        mods = index.get('mods', []) if isinstance(index, dict) else []
        return jsonify({'success': True, 'mods': mods})
    except Exception as exc:
        admin_event('error', f'community mods index failed: {exc}')
        return jsonify({'success': False, 'mods': [], 'error': str(exc)})


@app.route('/api/community-mods/upload-url', methods=['POST'])
def api_community_mod_upload_url():
    ip = _client_ip()
    if _rate_limited(ip, 'community_upload_url'):
        return _json_error('上传过于频繁，请稍后再试', 429)
    data = request.get_json(silent=True) or {}
    filename = str(data.get('filename') or '').strip()
    if not filename.lower().endswith('.json'):
        return _json_error('只允许上传 .json 文件')
    try:
        result = create_presigned_mod_upload(filename)
        return jsonify({'success': True, **result})
    except Exception as exc:
        admin_event('error', f'create community upload url failed: {exc}')
        return _json_error(str(exc), 500 if isinstance(exc, R2ConfigError) else 400)


@app.route('/api/community-mods/register', methods=['POST'])
def api_community_mod_register():
    ip = _client_ip()
    if _rate_limited(ip, 'community_register'):
        return _json_error('登记过于频繁，请稍后再试', 429)
    data = request.get_json(silent=True) or {}
    public_url = str(data.get('public_url') or '').strip()
    key = str(data.get('key') or '').strip()
    uploader_name = str(data.get('uploader_name') or '').strip()
    if not public_url or not key:
        return _json_error('缺少 key 或 public_url')
    try:
        result = register_community_mod(public_url, key, uploader_name)
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as exc:
        admin_event('error', f'register community mod failed: {exc}')
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


@app.route('/api/mods/save', methods=['POST'])
def api_mods_save():
    data = request.get_json(force=True)
    if not data:
        return jsonify({'success': False, 'error': 'invalid data'}), 400
    from mod_validator import validate_mod_data
    validation = validate_mod_data(data, strict=False, source='api_mods_save')
    if validation.errors:
        return jsonify({'success': False, 'errors': validation.errors, 'warnings': validation.warnings}), 400
    data = validation.normalized
    mods_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mods')
    requested_name = data.get('filename') or os.path.basename(str(data.get('filepath') or 'new_mod.json'))
    safe_name = os.path.basename(requested_name).strip() or 'new_mod.json'
    if not safe_name.endswith('.json'):
        safe_name += '.json'
    mod = Mod(os.path.join(mods_dir, safe_name))
    mod.format_version = data.get('format_version', 1)
    mod.editor = data.get('editor', {}) if isinstance(data.get('editor', {}), dict) else {}
    if data.get('info'):
        from mod_loader import ModInfo
        mod.info = ModInfo(data['info'])
    if data.get('cards'):
        from mod_loader import ModCard
        for cd in data['cards']:
            mod.cards.append(ModCard(cd))
    if data.get('events'):
        from mod_loader import ModEvent
        for ed in data['events']:
            mod.events.append(ModEvent(ed))
    if data.get('variables'):
        from mod_loader import ModVariable
        for vd in data['variables']:
            mod.variables.append(ModVariable(vd))
    mod.custom_statuses = data.get('custom_statuses', [])
    mod.custom_tags = data.get('custom_tags', [])
    mod.scripts = data.get('scripts', {})
    try:
        save_mod(mod)
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
                if psid in players:
                    p_names.append(players[psid]['nickname'])
                else:
                    p_names.append('(离线玩家)')
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
    socketio.emit('server_broadcast', {'message': msg})
    admin_event('admin', f'broadcast: {msg}')
    return jsonify({'success': True})


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
        e.players[loser].health = 0
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
        if e.phase not in ('draft', 'event_select'):
            return jsonify({'success': False, 'error': f'cannot fill draft during phase {e.phase}'}), 400
        filled = 0
        while e.phase == 'draft':
            made_progress = False
            for pidx in range(2):
                if len(e.draft_picks[pidx]) < DECK_SIZE:
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
    sid = request.sid
    join_room(sid)
    print("[server] debug")


@socketio.on('draft_reroll')
def on_draft_reroll(data=None):
    sid = request.sid
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
            success = engine.draft_reroll(pidx)
            if success:
                for pi in range(len(room.player_sids)):
                    send_draft_state(room, pi)
            else:
                emit('server_error', {'message': '无法重抽：当前不是选牌阶段或重抽次数已用完'})
    except Exception as e:
        print("[server] debug")
        import traceback
        traceback.print_exc()


@socketio.on('login')
def on_login(data):
    global _next_room_id
    data = data or {}
    sid = request.sid
    account_user = get_user_by_id(session.get('user_id')) if DB_AVAILABLE and session.get('user_id') else None
    if session.get('user_id') and not account_user:
        session.pop('user_id', None)
        session.pop('username', None)
    raw_name = data.get('nickname', '')
    wants_account_login = bool(data.get('account_login'))
    if account_user and account_user.get('banned'):
        session.pop('user_id', None)
        session.pop('username', None)
        reason = account_user.get('ban_reason') or ''
        emit('login_fail', {'reason': f'账号已被封禁：{reason}' if reason else '账号已被封禁'})
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
    else:
        special_profile = get_special_player_profile(raw_name)
        is_admin_player = bool(special_profile and special_profile.get('is_admin_player'))
        if special_profile:
            name = special_profile['display_name']
        else:
            name = sanitize_nickname(raw_name)
        if not special_profile and is_reserved_special_nickname(name):
            emit('login_fail', {'reason': ADMIN_NICKNAME_RESERVED_REASON})
            return
        if not special_profile and not validate_nickname(name):
            emit('login_fail', {'reason': 'Invalid nickname. Use 1-16 display-width characters; avoid pure numbers, pure symbols, or repeated -/_.'})
            return
        if not special_profile and DB_AVAILABLE and get_user_by_username(name):
            emit('login_fail', {'reason': 'Registered nickname reserved'})
            return
        user_id = None
        is_registered_user = False
    disabled_mods = ensure_valid_disabled_mods(data.get('disabled_mods', []))
    preferred_mode = data.get('mode', '1v1')
    if preferred_mode not in ('1v1', '2v2', 'urf'):
        preferred_mode = '1v1'
    try:
        community_fields, community_mod = resolve_community_loadout(data)
        loadout = build_mod_loadout(
            disabled_mods,
            community_mod=community_mod,
            community_hash=community_fields.get('community_mod_hash', ''),
        )
    except Exception as exc:
        emit('login_fail', {'reason': f'社区模组加载失败: {exc}'})
        return
    with _lock:
        for p in players.values():
            if p['nickname'] == name:
                emit('login_fail', {'reason': 'Nickname already exists'})
                return
        reconnect_room = None
        reconnect_old_sid = None
        for room in rooms.values():
            for dc_sid, dc_info in room.disconnected_players.items():
                if dc_info['nickname'] == name:
                    reconnect_room = room
                    reconnect_old_sid = dc_sid
                    break
            if reconnect_room:
                break
        initial_status = 'reconnecting' if reconnect_room else 'lobby'
        players[sid] = {
            'nickname': name,
            'room_id': None,
            'status': initial_status,
            'mods_hash': loadout['mods_hash'],
            'mods_list': loadout['mods_list'],
            'disabled_mods': loadout['disabled_mods'],
            'allowed_card_ids': loadout['allowed_card_ids'],
            'mode': preferred_mode,
            'is_admin_player': is_admin_player,
            'user_id': user_id,
            'is_registered_user': is_registered_user,
            'mod_source': community_fields.get('mod_source', 'official'),
            'community_mod_url': community_fields.get('community_mod_url', ''),
            'community_mod_hash': community_fields.get('community_mod_hash', ''),
            'community_mod_name': community_fields.get('community_mod_name', ''),
        }
        if special_profile:
            players[sid].update(special_public_fields(special_profile))
        admin_event('player', f'{name} joined as {initial_status}', sid=sid, mode=preferred_mode)
    if reconnect_room:
        reconnect_info = reconnect_room.disconnected_players.get(reconnect_old_sid, {})
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
    join_room(sid)
    login_payload = {'sid': sid, 'nickname': name, 'authenticated': bool(is_registered_user)}
    if is_registered_user:
        login_payload['user'] = auth_user_payload(account_user)
    login_payload.update(special_public_fields(players.get(sid, {})))
    emit('login_ok', login_payload)
    print("[server] debug")
    broadcast_lobby()


@socketio.on('form_team')
def on_form_team(data):
    sid = request.sid
    target_sid = data.get('target_sid')
    with _lock:
        if sid not in players or target_sid not in players:
            return
        if players[sid]['status'] != 'lobby' or players[target_sid]['status'] != 'lobby':
            return
        if players[sid].get('mode') != '2v2' or players[target_sid].get('mode') != '2v2':
            return
        if sid in teams or target_sid in teams:
            return
        socketio.emit('team_invite', {'from_sid': sid, 'from_name': players[sid]['nickname']}, room=target_sid)


@socketio.on('set_mode')
def on_set_mode(data):
    sid = request.sid
    mode = data.get('mode', '1v1')
    with _lock:
        if sid not in players:
            return
        if mode not in ('1v1', '2v2', 'urf'):
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
def on_update_mod_settings(data):
    sid = request.sid
    data = data or {}
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        if player.get('status') not in ('lobby', 'reconnecting'):
            emit('mod_settings_updated', {
                'ok': False,
                'reason': 'mod_settings_only_lobby',
                'disabled_mods': player.get('disabled_mods', []),
            })
            return
        old_hash = player.get('mods_hash')
        try:
            community_fields, community_mod = resolve_community_loadout(data)
            loadout = build_mod_loadout(
                data.get('disabled_mods', []),
                community_mod=community_mod,
                community_hash=community_fields.get('community_mod_hash', ''),
            )
        except Exception as exc:
            emit('mod_settings_updated', {
                'ok': False,
                'reason': str(exc),
                'disabled_mods': player.get('disabled_mods', []),
            })
            return
        player['disabled_mods'] = loadout['disabled_mods']
        player['mods_hash'] = loadout['mods_hash']
        player['mods_list'] = loadout['mods_list']
        player['allowed_card_ids'] = loadout['allowed_card_ids']
        player['mod_source'] = community_fields.get('mod_source', 'official')
        player['community_mod_url'] = community_fields.get('community_mod_url', '')
        player['community_mod_hash'] = community_fields.get('community_mod_hash', '')
        player['community_mod_name'] = community_fields.get('community_mod_name', '')
        invites.pop(sid, None)
        for inviter_sid, target_sid in list(invites.items()):
            if target_sid == sid:
                del invites[inviter_sid]
        if sid in teams and old_hash != loadout['mods_hash']:
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
            'mods_list': loadout['mods_list'],
            'mod_source': player['mod_source'],
            'community_mod_hash': player['community_mod_hash'],
            'community_mod_name': player['community_mod_name'],
        })
        broadcast_lobby()


@socketio.on('accept_team')
def on_accept_team(data):
    sid = request.sid
    leader_sid = data.get('from_sid')
    with _lock:
        if sid not in players or leader_sid not in players:
            return
        if players[sid]['status'] != 'lobby' or players[leader_sid]['status'] != 'lobby':
            return
        if players[sid].get('mods_hash') != players[leader_sid].get('mods_hash'):
            emit('server_error', {'message': '模组不一致，无法组队'})
            return
        if sid in teams or leader_sid in teams:
            return
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
    leader_sid = data.get('from_sid')
    with _lock:
        if leader_sid not in players:
            return
        socketio.emit('team_declined', {'from_name': players[sid]['nickname'] if sid in players else '?'}, room=leader_sid)


@socketio.on('leave_team')
def on_leave_team(data=None):
    sid = request.sid
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
    target_team_leader = data.get('target_team_leader')
    with _lock:
        if sid not in teams or target_team_leader not in teams:
            return
        my_team = teams[sid]
        target_team = teams[target_team_leader]
        my_team_all_2v2 = all(players.get(ms, {}).get('mode') == '2v2' for ms in my_team['members'] if ms in players)
        target_team_all_2v2 = all(players.get(ms, {}).get('mode') == '2v2' for ms in target_team['members'] if ms in players)
        if not my_team_all_2v2 or not target_team_all_2v2:
            return
        all_match_sids = my_team['members'] + target_team['members']
        if not same_mod_loadout(all_match_sids):
            emit('server_error', {'message': '模组不一致，无法开始2v2'})
            return
        match_key = (min(my_team['leader'], target_team['leader']),
                     max(my_team['leader'], target_team['leader']))
        if match_key in pending_team_matches:
            return
        pending_team_matches[match_key] = True
        for member_sid in target_team['members']:
            if member_sid in players:
                socketio.emit('team_match_invite', {
                    'from_leader': my_team['leader'],
                    'from_team': [players[ms]['nickname'] for ms in my_team['members'] if ms in players],
                    'from_team_sids': my_team['members'],
                }, room=member_sid)


@socketio.on('accept_team_match')
def on_accept_team_match(data):
    global _next_room_id
    sid = request.sid
    from_leader = data.get('from_leader')
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
        pending_team_matches.pop(match_key, None)
        for member_sid in my_team['members']:
            if member_sid != sid and member_sid in players:
                socketio.emit('team_match_accepted', {}, room=member_sid)
        all_sids = other_team['members'] + my_team['members']
        for s in all_sids:
            if s not in players or players[s]['status'] != 'lobby':
                return
        if not same_mod_loadout(all_sids):
            emit('server_error', {'message': '模组不一致，无法开始2v2'})
            return
        room_id = _next_room_id
        _next_room_id += 1
        allowed = None
        first_sid = all_sids[0]
        if first_sid in players and players[first_sid].get('allowed_card_ids'):
            allowed = players[first_sid]['allowed_card_ids']
        room = GameRoom(room_id, all_sids, allowed, mode='2v2')
        rooms[room_id] = room
        admin_event('game', f"room {room_id} created mode=2v2: {' / '.join(players[s]['nickname'] for s in all_sids)}")
        for s in all_sids:
            players[s]['status'] = 'in_game'
            players[s]['room_id'] = room_id
            join_room(room_id)
            if s in teams:
                del teams[s]
        room.engine.player_names = [players[s]['nickname'] for s in all_sids]
        room.engine.start_draft()
        for i, s in enumerate(all_sids):
            send_draft_state(room, i)
        broadcast_lobby()


@socketio.on('decline_team_match')
def on_decline_team_match(data):
    sid = request.sid
    from_leader = data.get('from_leader')
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
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        solo_sessions.pop(sid, None)
        tutorial_sessions.discard(sid)
        room_id = player.get('room_id')
        nickname = player['nickname']
        admin_event('player', f'{nickname} disconnected', sid=sid, room_id=room_id)
        if room_id is not None and room_id in rooms:
            room = rooms[room_id]
            pidx = room.player_index(sid)
            if pidx >= 0 and room.engine.phase not in ('game_over',):
                room.disconnected_players[sid] = {
                    'nickname': nickname,
                    'player_index': pidx,
                    'disconnect_time': time.time(),
                    'user_id': player.get('user_id'),
                    'is_registered_user': bool(player.get('is_registered_user')),
                    'mod_source': player.get('mod_source', 'official'),
                    'community_mod_hash': player.get('community_mod_hash', ''),
                    'mods_hash': player.get('mods_hash', ''),
                }
                room.disconnected_players[sid].update(special_public_fields(player))
                dead_2v2_player = room.mode == '2v2' and _room_player_dead(room, pidx)
                if not dead_2v2_player:
                    for other_sid in room.player_sids:
                        if other_sid != sid and other_sid in players:
                            socketio.emit('opponent_disconnected', {
                                'reconnect_timeout': RECONNECT_TIMEOUT_SECONDS,
                                'opponent_nickname': nickname,
                            }, room=other_sid)
                    timer = threading.Timer(float(RECONNECT_TIMEOUT_SECONDS), reconnect_timeout, args=[room_id, sid])
                    room.reconnect_timers[sid] = timer
                    timer.daemon = True
                    timer.start()
                    both_dc = _room_all_blocking_players_disconnected(room)
                    if both_dc and room.mode != '2v2':
                        for t in room.reconnect_timers.values():
                            t.cancel()
                        room.reconnect_timers.clear()
                        room.both_dc_timer = threading.Timer(float(BOTH_DISCONNECTED_CLEANUP_SECONDS), both_disconnected_cleanup, args=[room_id])
                        room.both_dc_timer.daemon = True
                        room.both_dc_timer.start()
                del players[sid]
                if dead_2v2_player:
                    broadcast_game_state(room)
                broadcast_lobby()
                return
            if pidx >= 0 and room.engine.phase == 'game_over':
                room._rematch_votes.discard(sid)
                for other_sid in room.player_sids:
                    if other_sid != sid and other_sid in players:
                        socketio.emit('opponent_disconnected', {'timeout': True}, room=other_sid)
                if not any(s in room.disconnected_players for s in room.player_sids if s != sid):
                    for t in room.reconnect_timers.values():
                        t.cancel()
                    del rooms[room_id]
                else:
                    for other_sid in room.player_sids:
                        if other_sid != sid and other_sid in players:
                            players[other_sid]['room_id'] = None
                            players[other_sid]['status'] = 'lobby'
                    for t in room.reconnect_timers.values():
                        t.cancel()
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
        del players[sid]
    broadcast_lobby()


@socketio.on('reconnect_accept')
def on_reconnect_accept(data):
    global _next_room_id
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = data.get('room_id')
        old_sid = data.get('old_sid')
        if room_id is None or room_id not in rooms:
            player['status'] = 'lobby'
            return
        room = rooms[room_id]
        if old_sid not in room.disconnected_players:
            player['status'] = 'lobby'
            return
        dc_info = room.disconnected_players[old_sid]
        if dc_info['nickname'] != player['nickname']:
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
        del room.disconnected_players[old_sid]
        player['room_id'] = room_id
        player['status'] = 'in_game'
        player.update(special_public_fields(dc_info))
        join_room(room_id)
        for other_sid in room.player_sids:
            if other_sid != sid and other_sid in players:
                socketio.emit('opponent_reconnected', {}, room=other_sid)
        send_game_state_to(room, pidx)
    broadcast_lobby()


@socketio.on('reconnect_decline')
def on_reconnect_decline(data):
    global _next_room_id
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = data.get('room_id')
        old_sid = data.get('old_sid')
        if room_id is None or room_id not in rooms:
            player['status'] = 'lobby'
            return
        room = rooms[room_id]
        if room.mode == '2v2':
            dc_info = room.disconnected_players.get(old_sid, {})
            dc_pidx = int(dc_info.get('player_index', -1)) if dc_info else -1
            if _room_player_dead(room, dc_pidx) and old_sid in room.reconnect_timers:
                room.reconnect_timers[old_sid].cancel()
                del room.reconnect_timers[old_sid]
            player['status'] = 'lobby'
            player['room_id'] = None
            broadcast_lobby()
            return
        if old_sid in room.disconnected_players:
            if old_sid in room.reconnect_timers:
                room.reconnect_timers[old_sid].cancel()
                del room.reconnect_timers[old_sid]
            del room.disconnected_players[old_sid]
        for other_sid in room.player_sids:
            if other_sid != sid and other_sid in players:
                socketio.emit('opponent_disconnected', {'timeout': True}, room=other_sid)
                players[other_sid]['room_id'] = None
                players[other_sid]['status'] = 'lobby'
        for t in room.reconnect_timers.values():
            t.cancel()
        del rooms[room_id]
        player['status'] = 'lobby'
    broadcast_lobby()


@socketio.on('invite')
def on_invite(data):
    sid = request.sid
    target_sid = data.get('target_sid')
    print("[server] debug")
    with _lock:
        if sid not in players or target_sid not in players:
            print("[server] debug")
            emit('server_error', {'message': '目标玩家不存在'})
            return
        if sid == target_sid:
            return
        if sid in invites:
            print("[server] debug")
            return
        target = players[target_sid]
        if target['status'] != 'lobby':
            emit('server_error', {'message': '目标玩家不在大厅'})
            return
        inviter = players[sid]
        inviter_mode = inviter.get('mode', '1v1')
        target_mode = target.get('mode', '1v1')
        if inviter_mode not in ('1v1', 'urf') or target_mode != inviter_mode:
            emit('server_error', {'message': '双方模式不一致，无法邀请'})
            return
        if inviter.get('mods_hash') != target.get('mods_hash'):
            inviter_mods = inviter.get('mods_list', [])
            target_mods = target.get('mods_list', [])
            inviter_label = ', '.join(inviter_mods) if inviter_mods else 'no mods'
            target_label = ', '.join(target_mods) if target_mods else 'no mods'
            emit('server_error', {'message': f'模组不一致，无法开始对局。你：{inviter_label}；对方：{target_label}'})
            return
        invites[sid] = target_sid
        inviter_name = players[sid]['nickname']
        print("[server] debug")
        result = socketio.emit('invite_received', {
            'inviter_sid': sid,
            'inviter_name': inviter_name,
        }, room=target_sid)
        print("[server] debug")

        def _invite_timeout(inviter_sid):
            with _lock:
                if inviter_sid in invites:
                    del invites[inviter_sid]
                    print("[server] debug")

        timer = threading.Timer(30.0, _invite_timeout, args=[sid])
        timer.daemon = True
        timer.start()


@socketio.on('accept_invite')
def on_accept_invite(data):
    global _next_room_id
    sid = request.sid
    inviter_sid = data.get('inviter_sid')
    print("[server] debug")
    with _lock:
        if inviter_sid not in players or sid not in players:
            print("[server] debug")
            return
        if inviter_sid not in invites or invites[inviter_sid] != sid:
            print("[server] debug")
            return
        del invites[inviter_sid]
        inviter = players[inviter_sid]
        accepter = players[sid]
        if inviter['status'] != 'lobby' or accepter['status'] != 'lobby':
            return
        if inviter.get('mods_hash') != accepter.get('mods_hash'):
            emit('server_error', {'message': '妯＄粍涓嶄竴鑷达紝鏃犳硶寮€濮嬪灞?'})
            return
        room_id = _next_room_id
        _next_room_id += 1
        allowed_card_ids = inviter.get('allowed_card_ids') or get_allowed_card_ids(inviter.get('disabled_mods', []))
        room = GameRoom(room_id, [inviter_sid, sid], allowed_card_ids, mode=inviter.get('mode', '1v1'))
        rooms[room_id] = room
        admin_event('game', f"room {room_id} created mode={room.mode}: {inviter['nickname']} vs {accepter['nickname']}")
        inviter['room_id'] = room_id
        inviter['status'] = 'in_game'
        accepter['room_id'] = room_id
        accepter['status'] = 'in_game'
        room.engine.player_names = [inviter['nickname'], accepter['nickname']]
        if room.mode == 'urf':
            room.engine.start_game()
            room.started_at = time.time()
            admin_event('game', f'room {room_id} started mode={room.mode}')
            print("[server] debug")
            for psid in room.player_sids:
                socketio.emit('game_phase', {'phase': 'playing', 'mode': room.mode}, room=psid)
            broadcast_game_state(room)
        else:
            room.engine.start_draft()
            print("[server] debug")
            for pidx in range(len(room.player_sids)):
                psid = room.player_sids[pidx]
                socketio.emit('game_phase', {'phase': 'draft'}, room=psid)
                send_draft_state(room, pidx)
    broadcast_lobby()


@socketio.on('decline_invite')
def on_decline_invite(data):
    sid = request.sid
    inviter_sid = data.get('inviter_sid')
    with _lock:
        if inviter_sid in invites and invites[inviter_sid] == sid:
            del invites[inviter_sid]
            if inviter_sid in players:
                socketio.emit('invite_declined', {'target_sid': sid}, room=inviter_sid)


@socketio.on('chat')
def on_chat(data):
    sid = request.sid
    data = data or {}
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        spectating_room = player.get('spectating_room')
        text = str(data.get('text', ''))[:200]
        if not text.strip():
            return
        nickname = player['nickname']
        is_spectator = player.get('status') == 'spectating'
        chat_data = {
            'nickname': nickname,
            'text': text,
            'is_spectator': is_spectator,
        }
        chat_data.update(special_public_fields(player))

        def emit_chat_to(recipients, payload):
            seen = set()
            for target_sid in recipients:
                if target_sid in seen:
                    continue
                seen.add(target_sid)
                if target_sid in players:
                    socketio.emit('chat', payload, room=target_sid)

        def player_name_at(room, pidx):
            if not isinstance(pidx, int) or pidx < 0 or pidx >= len(room.player_sids):
                return '?'
            psid = room.player_sids[pidx]
            if psid in players:
                return players[psid]['nickname']
            return room.disconnected_players.get(psid, {}).get('nickname', '?')

        if room_id is not None and room_id in rooms:
            room = rooms[room_id]
            pidx = room.player_index(sid)
            recipients = list(room.player_sids) + list(room.spectators)
            if room.mode == '2v2' and pidx >= 0:
                channel = str(data.get('channel') or 'public')
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
                        target_pidx = int(data.get('target_player_id'))
                    except (TypeError, ValueError):
                        target_pidx = -1
                    if target_pidx not in enemy_ids or target_pidx < 0 or target_pidx >= len(room.player_sids):
                        emit('server_error', {'message': 'Invalid chat target'})
                        return
                    chat_data['chat_target_player_id'] = target_pidx
                    chat_data['chat_target_name'] = player_name_at(room, target_pidx)
                    recipients = [sid, room.player_sids[target_pidx]]
            emit_chat_to(recipients, chat_data)
        elif spectating_room is not None and spectating_room in rooms:
            room = rooms[spectating_room]
            if room.mode == '2v2':
                chat_data['chat_channel'] = 'public'
            emit_chat_to(list(room.player_sids) + list(room.spectators), chat_data)
        else:
            for other_sid, other_p in players.items():
                if other_p['status'] == 'lobby':
                    socketio.emit('chat', chat_data, room=other_sid)


@socketio.on('draft_pick')
def on_draft_pick(data):
    global _next_room_id
    sid = request.sid
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
        def_id = data.get('def_id')
        if not def_id:
            return
        success = engine.draft_pick(pidx, def_id)
        if not success:
            if not engine.draft_options[pidx]:
                engine._generate_draft_options_for_player(pidx)
            success = engine.draft_pick(pidx, def_id)
        if success:
            for pi in range(len(room.player_sids)):
                send_draft_state(room, pi)
            if engine.phase == 'event_select':
                start_event_select(room)
        else:
            emit('server_error', {'message': '无法选择这张牌'})


@socketio.on('select_opening_event')
def on_select_opening_event(data):
    sid = request.sid
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
        event_id = data.get('event_id')
        sub_choice = data.get('sub_choice')
        if event_id is None:
            return
        success = engine.select_opening_event(pidx, event_id)
        if success:
            if sub_choice:
                engine.opening_event_sub_choices[pidx] = sub_choice
            if engine.both_events_selected():
                start_game(room)
            else:
                for pi in range(len(room.player_sids)):
                    send_event_state(room, pi)


@socketio.on('solo_start')
def on_solo_start(data):
    sid = request.sid
    deck0 = data.get('deck0', []) if data else []
    deck1 = data.get('deck1', []) if data else []
    event0 = data.get('event0') if data else None
    event1 = data.get('event1') if data else None
    sub0 = data.get('sub0') if data else None
    sub1 = data.get('sub1') if data else None
    if len(deck0) != DECK_SIZE or len(deck1) != DECK_SIZE:
        emit('server_error', {'message': '训练场牌组必须各为15张'})
        return
    disabled_mods = ensure_valid_disabled_mods(data.get('disabled_mods', [])) if data else []
    try:
        community_fields, community_mod = resolve_community_loadout(data or {})
        loadout = build_mod_loadout(
            disabled_mods,
            community_mod=community_mod,
            community_hash=community_fields.get('community_mod_hash', ''),
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
        tutorial_sessions.discard(sid)
        solo_sessions[sid] = create_solo_engine(deck0, deck1, event0, event1, sub0, sub1)
        if sid in players:
            players[sid]['status'] = 'solo'
        socketio.emit('game_phase', {'phase': 'playing', 'solo': True}, room=sid)
        send_solo_state(sid)


@socketio.on('tutorial_start')
def on_tutorial_start(data=None):
    sid = request.sid
    deck0 = [
        'Basic', 'Rose', 'Leaf', 'Coffee', 'Fission',
        'Triangle', 'Bubble', 'Fusion', 'Basic', 'Basic',
        'Bone', 'Battery', 'Stinger', 'Leaf', 'Bubble',
    ]
    deck1 = [
        'Basic', 'Rose', 'Coffee', 'Battery', 'Rose',
        'Basic', 'Bone', 'Leaf', 'Bubble', 'Basic',
        'Stinger', 'Battery', 'Bubble', 'Triangle', 'Fire',
    ]
    with _lock:
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
    safe_card_ids = {'Basic', 'Bone', 'Fire', 'Rose', 'Coffee', 'Battery'}
    order = ('thorn', 'bloom', 'root')
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
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            emit('server_error', {'message': '训练场尚未开始'})
            return
        pidx = engine.current_player
        result = engine.play_card(pidx, data.get('card_instance_id'), data.get('choice'))
        if result.get('needs_response'):
            if sid in tutorial_sessions and pidx == 0:
                engine.handle_response(1, None)
                send_solo_state(sid, 0)
                return
            send_solo_state(sid, 0 if sid in tutorial_sessions else 1 - pidx)
            emit_solo_response_request(sid, engine, pidx, result['card'])
        elif result.get('needs_choice'):
            send_solo_state(sid)
            socketio.emit('choice_request', {
                'choice_type': result['choice_type'],
                'card': result['card'],
                'choice_params': result.get('choice_params', {}),
                'target_player_id': result.get('target_player_id'),
            }, room=sid)
        elif result.get('success'):
            send_solo_state(sid)
        else:
            emit('server_error', {'message': result.get('error', 'Operation failed')})


@socketio.on('solo_response')
def on_solo_response(data):
    sid = request.sid
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            return
        responder = 1 - engine.pending_response['player_id'] if engine.pending_response else engine.current_player
        card_instance_id = data.get('card_instance_id') if data else None
        if sid in tutorial_sessions and responder != 0:
            card_instance_id = None
        engine.handle_response(responder, card_instance_id)
        send_solo_state(sid)


@socketio.on('solo_resolve_choice')
def on_solo_resolve_choice(data):
    sid = request.sid
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            return
        pidx = engine.pending_choice.get('player_id', engine.current_player) if engine.pending_choice else engine.current_player
        engine.resolve_choice(pidx, data.get('choice') if data else None)
        send_solo_state(sid)


@socketio.on('solo_use_trigger')
def on_solo_use_trigger(data):
    sid = request.sid
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            return
        result = engine.use_trigger(engine.current_player, data.get('equipment_instance_id'))
        if not result.get('success'):
            emit('server_error', {'message': result.get('error', 'Operation failed')})
        send_solo_state(sid)


@socketio.on('solo_end_turn')
def on_solo_end_turn(data=None):
    sid = request.sid
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            return
        result = engine.end_turn(engine.current_player)
        if not result.get('success'):
            emit('server_error', {'message': result.get('error', 'Operation failed')})
        send_solo_state(sid)


@socketio.on('solo_set_next_draw')
def on_solo_set_next_draw(data):
    sid = request.sid
    def_ids = []
    if data:
        if isinstance(data.get('def_ids'), list):
            def_ids = [x for x in data.get('def_ids') if x]
        elif data.get('def_id'):
            def_ids = [data.get('def_id')]
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
        for c in reversed(picked):
            ps.deck.insert(0, c)
        names = '、'.join([c.name_cn for c in picked])
        engine.log_msg(f"训练场：{engine.pn(engine.current_player)} 设置下次抽牌：{names}")
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


@socketio.on('solo_pause')
def on_solo_pause(data=None):
    sid = request.sid
    solo_sessions.pop(sid, None)
    tutorial_sessions.discard(sid)
    if sid in players:
        players[sid]['status'] = 'lobby'
    socketio.emit('solo_paused', {}, room=sid)


@socketio.on('play_card')
def on_play_card(data):
    sid = request.sid
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
        card_instance_id = data.get('card_instance_id')
        choice = data.get('choice')
        target_player_id = data.get('target_player_id', -1)
        try:
            target_player_id = int(target_player_id)
        except (TypeError, ValueError):
            target_player_id = -1
        if card_instance_id is None:
            return
        if room.mode == '2v2':
            result = engine.play_card(pidx, card_instance_id, target_player_id=target_player_id, choice=choice)
        else:
            result = engine.play_card(pidx, card_instance_id, choice)
        if result.get('needs_ally_consent'):
            broadcast_game_state(room)
            target_pidx = result.get('target_player_id')
            if isinstance(target_pidx, int) and 0 <= target_pidx < len(room.player_sids):
                target_sid = room.player_sids[target_pidx]
                if target_sid in players:
                    socketio.emit('ally_consent_request', {
                        'card': result.get('card'),
                        'from_player': pidx,
                        'from_name': players[sid]['nickname'],
                    }, room=target_sid)
                else:
                    room.engine.pending_ally_request = None
                    emit('server_error', {'message': 'Teammate is not online'})
        elif result.get('needs_response'):
            broadcast_game_state(room)
            played_card = result['card']
            played_def = CARD_DEFS.get(played_card.get('def_id', ''), None)
            trigger_types = []
            if played_def:
                if played_def.card_type == 'thorn':
                    trigger_types.append('thorn')
                elif played_def.card_type == 'bloom':
                    trigger_types.append('bloom')
                elif played_def.card_type == 'root':
                    trigger_types.append('root')
                if played_def.id in ('Sewage', 'MagicSewage'):
                    trigger_types.append('equipment_destroy')
                trigger_types.append('any')
            if room.mode == '2v2':
                by_responder = {}
                for c in (engine.pending_response or {}).get('counter_cards', []):
                    by_responder.setdefault(c.get('responder_id'), []).append(c)
                for responder_id, counter_cards in by_responder.items():
                    if isinstance(responder_id, int) and 0 <= responder_id < len(room.player_sids):
                        r_sid = room.player_sids[responder_id]
                        if r_sid in players:
                            socketio.emit('response_request', {
                                'card': played_card,
                                'counter_cards': counter_cards,
                            }, room=r_sid)
            else:
                opp_pidx = 1 - pidx
                counter_cards = []
                for tt in trigger_types:
                    counter_cards.extend(engine.get_counter_cards(opp_pidx, tt))
                opp_sid = room.player_sids[opp_pidx]
                if opp_sid in players:
                    socketio.emit('response_request', {
                        'card': played_card,
                        'counter_cards': [c.to_dict() for c in counter_cards],
                    }, room=opp_sid)
        elif result.get('needs_choice'):
            broadcast_game_state(room)
            emit('choice_request', {
                'choice_type': result['choice_type'],
                'card': result['card'],
                'choice_params': result.get('choice_params', {}),
                'target_player_id': result.get('target_player_id'),
            })
        elif result.get('success'):
            broadcast_game_state(room)
        else:
            emit('server_error', {'message': result.get('error', 'Operation failed')})


@socketio.on('response')
def on_response(data):
    sid = request.sid
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
        card_instance_id = data.get('card_instance_id')
        engine.handle_response(pidx, card_instance_id)
        broadcast_game_state(room)


@socketio.on('ally_consent_response')
def on_ally_consent_response(data):
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        if room_id is None or room_id not in rooms:
            return
        room = rooms[room_id]
        if room.mode != '2v2':
            return
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        accepted = bool(data.get('accepted')) if data else False
        result = room.engine.handle_ally_consent(pidx, accepted)
        if result.get('needs_response'):
            broadcast_game_state(room)
            played_card = result['card']
            by_responder = {}
            for c in (room.engine.pending_response or {}).get('counter_cards', []):
                by_responder.setdefault(c.get('responder_id'), []).append(c)
            for responder_id, counter_cards in by_responder.items():
                if isinstance(responder_id, int) and 0 <= responder_id < len(room.player_sids):
                    r_sid = room.player_sids[responder_id]
                    if r_sid in players:
                        socketio.emit('response_request', {
                            'card': played_card,
                            'counter_cards': counter_cards,
                        }, room=r_sid)
        elif result.get('needs_choice'):
            broadcast_game_state(room)
            requester_sid = room.player_sids[result.get('player_id', room.engine.current_player)] if result.get('player_id') is not None else sid
            socketio.emit('choice_request', {
                'choice_type': result['choice_type'],
                'card': result['card'],
                'choice_params': result.get('choice_params', {}),
                'target_player_id': result.get('target_player_id'),
            }, room=requester_sid)
        elif not result.get('success'):
            emit('server_error', {'message': result.get('error', 'Operation failed')})
        else:
            broadcast_game_state(room)


@socketio.on('resolve_choice')
def on_resolve_choice(data):
    sid = request.sid
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
        choice = data.get('choice')
        engine.resolve_choice(pidx, choice)
        broadcast_game_state(room)


@socketio.on('use_trigger')
def on_use_trigger(data):
    sid = request.sid
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
        equipment_instance_id = data.get('equipment_instance_id')
        if equipment_instance_id is None:
            return
        target_player_id = data.get('target_player_id', -1)
        try:
            target_player_id = int(target_player_id)
        except (TypeError, ValueError):
            target_player_id = -1
        if room.mode == '2v2':
            result = engine.use_trigger(pidx, equipment_instance_id, target_player_id=target_player_id)
        else:
            result = engine.use_trigger(pidx, equipment_instance_id)
        if result.get('needs_ally_consent'):
            broadcast_game_state(room)
            target_pidx = result.get('target_player_id')
            if isinstance(target_pidx, int) and 0 <= target_pidx < len(room.player_sids):
                target_sid = room.player_sids[target_pidx]
                if target_sid in players:
                    socketio.emit('ally_consent_request', {
                        'card': result.get('card'),
                        'from_player': pidx,
                        'from_name': players[sid]['nickname'],
                    }, room=target_sid)
                else:
                    room.engine.pending_ally_request = None
                    emit('server_error', {'message': 'Teammate is not online'})
        elif result.get('success'):
            broadcast_game_state(room)
        else:
            emit('server_error', {'message': result.get('error', 'Operation failed')})


@socketio.on('urf_replace_card')
def on_urf_replace_card(data):
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        room_id = players[sid].get('room_id')
        if room_id is None or room_id not in rooms:
            return
        room = rooms[room_id]
        if room.mode != 'urf':
            return
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        result = room.engine.replace_hand_card(pidx, data.get('card_instance_id'))
        if result.get('success'):
            broadcast_game_state(room)
        else:
            emit('server_error', {'message': result.get('error', 'Operation failed')})


@socketio.on('urf_sell_equipment')
def on_urf_sell_equipment(data):
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        room_id = players[sid].get('room_id')
        if room_id is None or room_id not in rooms:
            return
        room = rooms[room_id]
        if room.mode != 'urf':
            return
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        result = room.engine.sell_equipment(pidx, data.get('equipment_instance_id'))
        if result.get('success'):
            broadcast_game_state(room)
        else:
            emit('server_error', {'message': result.get('error', 'Operation failed')})


@socketio.on('end_turn')
def on_end_turn(data):
    sid = request.sid
    print("[server] debug")
    try:
        with _lock:
            if sid not in players:
                print("[server] debug")
                emit('server_error', {'message': '玩家不在对局中'})
                return
            player = players[sid]
            room_id = player.get('room_id')
            if room_id is None or room_id not in rooms:
                print("[server] debug")
                emit('server_error', {'message': '对局不存在'})
                return
            room = rooms[room_id]
            pidx = room.player_index(sid)
            if pidx < 0:
                print("[server] debug")
                emit('server_error', {'message': '你不是该对局的玩家'})
                return
            engine = room.engine
            print("[server] debug")
            result = engine.end_turn(pidx)
            print("[server] debug")
            broadcast_game_state(room)
            if not result.get('success'):
                emit('server_error', {'message': result.get('error', 'Operation failed')})
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("[server] debug")
        emit('server_error', {'message': '结束回合失败，请稍后重试'})


@socketio.on('surrender')
def on_surrender(data):
    sid = request.sid
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
            if room.mode == '2v2':
                teammate_id = engine.get_teammate(pidx) if hasattr(engine, 'get_teammate') else -1
                if teammate_id < 0 or teammate_id >= len(room.player_sids):
                    emit('server_error', {'message': 'Surrender requires a teammate'})
                    return
                teammate_sid = room.player_sids[teammate_id]
                if teammate_sid not in players or teammate_sid in room.disconnected_players:
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
            result = engine.surrender(pidx)
            if result.get('success'):
                broadcast_game_state(room)
                for psid in room.player_sids:
                    if psid in players:
                        socketio.emit('game_phase', {'phase': 'game_over'}, room=psid)
            else:
                emit('server_error', {'message': result.get('error', '投降失败')})
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("[server] debug")
        emit('server_error', {'message': '投降失败，请稍后重试'})


@socketio.on('surrender_consent_response')
def on_surrender_consent_response(data):
    sid = request.sid
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
            accepted = bool((data or {}).get('accepted'))
            if not accepted:
                if requester_sid and requester_sid in players:
                    socketio.emit('surrender_consent_result', {'accepted': False}, room=requester_sid)
                emit('surrender_consent_result', {'accepted': False})
                return
            result = room.engine.surrender(requester_id)
            if result.get('success'):
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
        print("[server] debug")
        emit('server_error', {'message': 'Surrender failed'})


@socketio.on('rematch')
def on_rematch(data=None):
    sid = request.sid
    try:
        with _lock:
            if sid not in players:
                print("[server] debug")
                return
            player = players[sid]
            room_id = player.get('room_id')
            if room_id is None or room_id not in rooms:
                print("[server] debug")
                return
            room = rooms[room_id]
            room._rematch_votes.add(sid)
            print("[server] debug")
            for other_sid in room.player_sids:
                if other_sid != sid and other_sid in players:
                    socketio.emit('rematch_requested', {'player_name': player['nickname']}, room=other_sid)
            if len(room._rematch_votes) == len(room.player_sids):
                print("[server] debug")
                room._rematch_votes = set()
                room.pending_surrender_request = None
                if room.mode == '2v2':
                    room.engine = GameEngine2v2()
                elif room.mode == 'urf':
                    room.engine = GameEngineInfiniteFire()
                else:
                    room.engine = GameEngine()
                if room.player_sids and room.player_sids[0] in players:
                    room.engine.allowed_card_ids = set(players[room.player_sids[0]].get('allowed_card_ids', [])) or None
                names = []
                for pidx, psid in enumerate(room.player_sids):
                    if psid in players:
                        names.append(players[psid]['nickname'])
                    else:
                        names.append(f'Player {pidx + 1}')
                room.engine.player_names = names
                if room.mode == 'urf':
                    room.engine.start_game()
                    for psid in room.player_sids:
                        if psid in players:
                            socketio.emit('game_phase', {'phase': 'playing', 'mode': room.mode}, room=psid)
                    broadcast_game_state(room)
                else:
                    room.engine.start_draft()
                    for pidx in range(len(room.player_sids)):
                        psid = room.player_sids[pidx]
                        if psid in players:
                            socketio.emit('game_phase', {'phase': 'draft'}, room=psid)
                            send_draft_state(room, pidx)
                print("[server] debug")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("[server] debug")


@socketio.on('return_lobby')
def on_return_lobby(data=None):
    global _next_room_id
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        if player.get('spectating_room') is not None:
            _handle_leave_spectate_internal(sid)
            return
        room_id = player.get('room_id')
        if room_id is not None and room_id in rooms:
            room = rooms[room_id]
            for other_sid in room.player_sids:
                if other_sid != sid and other_sid in players:
                    socketio.emit('opponent_disconnected', {}, room=other_sid)
                    players[other_sid]['room_id'] = None
                    players[other_sid]['status'] = 'lobby'
            for t in room.reconnect_timers.values():
                t.cancel()
            del rooms[room_id]
        player['room_id'] = None
        player['status'] = 'lobby'
    broadcast_lobby()


@socketio.on('spectate')
def on_spectate(data):
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        if player['status'] != 'lobby':
            emit('server_error', {'message': '只有在大厅中才能观战'})
            return
        room_id = data.get('room_id')
        if room_id is None or room_id not in rooms:
            emit('server_error', {'message': '对局不存在'})
            return
        room = rooms[room_id]
        if _player_matches_room_participant(room, player.get('nickname')):
            emit('server_error', {'message': '请返回自己的对局，不能观战自己的对局'})
            return
        phase = room.engine.phase
        if phase in ('draft', 'event_select'):
            emit('server_error', {'message': '选牌或开局事件阶段暂不能观战'})
            return
        if phase not in ('action', 'draw', 'playing', 'response', 'choice'):
            emit('server_error', {'message': '该对局当前不能观战'})
            return
        player['status'] = 'spectating'
        player['spectating_room'] = room_id
        player['spectate_perspective'] = 0
        room.spectators.append(sid)
        p1 = '?'
        p2 = '?'
        if len(room.player_sids) > 0:
            sid0 = room.player_sids[0]
            if sid0 in players:
                p1 = players[sid0]['nickname']
            elif sid0 in room.disconnected_players:
                p1 = room.disconnected_players[sid0]['nickname']
        if len(room.player_sids) > 1:
            sid1 = room.player_sids[1]
            if sid1 in players:
                p2 = players[sid1]['nickname']
            elif sid1 in room.disconnected_players:
                p2 = room.disconnected_players[sid1]['nickname']
        emit('spectate_enter', {
            'room_id': room_id,
            'player1': p1,
            'player2': p2,
        })
        _send_spectate_state_internal(sid, room)


def _send_spectate_state_internal(spid, room):
    state = build_spectate_state(room)
    state['your_id'] = -1
    state['spectating'] = True
    for i, psid in enumerate(room.player_sids):
        state[f'player{i + 1}_name'] = players[psid]['nickname'] if psid in players else room.disconnected_players.get(psid, {}).get('nickname', '?')
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
    print("[server] debug")
    with _lock:
        _handle_leave_spectate_internal(sid)
    broadcast_lobby()


@socketio.on('switch_spectate_perspective')
def on_switch_spectate_perspective(data=None):
    return


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
