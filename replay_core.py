import hashlib
import json
import os
import sqlite3
import zlib
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from db import DB_PATH, get_db_connection, utc_now


REPLAY_VERSION = 2
DEFAULT_RETENTION_DAYS = int(os.environ.get('GTN_REPLAY_RETENTION_DAYS', '90') or 90)
CLEANUP_HOUR = int(os.environ.get('GTN_CLEANUP_HOUR', '4') or 4)
CLEANUP_MINUTE = int(os.environ.get('GTN_CLEANUP_MINUTE', '30') or 30)
MAX_REPLAY_COMPRESSED_BYTES = int(os.environ.get('GTN_REPLAY_MAX_COMPRESSED_BYTES', '4000000') or 4000000)
MAX_REPLAY_STORED_ACTIONS = int(os.environ.get('GTN_REPLAY_MAX_STORED_ACTIONS', '900') or 900)
REPLAY_ITEM_COLUMNS = '''
    id, match_id, created_at, mode, player_names_json, winner_name, winner_index,
    round_num, duration_ms, replay_version, replay_sha256, replay_size,
    mod_source, mod_hash, community_mod_name
'''
_TIMELINE_CACHE = OrderedDict()
_TIMELINE_CACHE_MAX = 4
_REPLAY_SETUP_ACTION_TYPES = {
    'draft_pick',
    'draft_reroll',
    'select_opening_event',
    'submit_event_sub_choice',
    'reroll_opening_event',
}
_REPLAY_SETUP_PHASES = {'draft', 'event_select', 'event_reveal', 'event_sub_choice', 'sub_choice'}
_OPENING_EVENT_NAMES_CN = {
    '1': '生命强化',
    '2': '魔力转化',
    '3': '光之洗礼',
    '4': '烈焰预兆',
    '5': '命运抽签',
    '6': '能量涌动',
    '7': '先手压制',
    '8': '绝境求生',
}


def _json_bytes(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _compact_replay_state(state):
    if not isinstance(state, dict):
        return {}
    return {
        'compact': True,
        'mode': state.get('mode') or '',
        'phase': state.get('phase') or '',
        'round_num': state.get('round_num') or state.get('round') or 0,
        'current_player': state.get('current_player'),
        'game_over': bool(state.get('game_over')),
        'winner': state.get('winner'),
        'winning_team': state.get('winning_team'),
        'player_names': state.get('player_names') or [],
    }


def _copy_replay_frame(frame, *, keep_state=True, compact_state=False):
    if not isinstance(frame, dict):
        return frame
    copied = dict(frame)
    state = copied.get('state')
    if keep_state:
        if compact_state:
            copied['state'] = _compact_replay_state(state)
    else:
        copied.pop('state', None)
    return copied


def _encode_replay_for_storage(replay):
    replay = dict(replay or {})
    replay.setdefault('meta', {})
    keyframes = replay.get('keyframes') if isinstance(replay.get('keyframes'), list) else []
    actions = replay.get('actions') if isinstance(replay.get('actions'), list) else []

    def encoded(candidate):
        raw = _json_bytes(candidate)
        return raw, zlib.compress(raw, level=6)

    raw, compressed = encoded(replay)
    if len(compressed) <= MAX_REPLAY_COMPRESSED_BYTES:
        return raw, compressed, False

    uses_deltas = any(
        isinstance(frame, dict)
        and isinstance(frame.get('state'), dict)
        and frame['state'].get('delta') is True
        for frame in keyframes + actions
    )
    if uses_deltas:
        # Delta frames form one ordered stream. Removing or compacting any frame
        # makes every following state unreconstructable, so preserve an unusual
        # oversized replay instead of silently turning its latter half into a
        # toolbar-only recording.
        replay['meta'] = dict(replay.get('meta') or {})
        replay['meta']['size_limit_exceeded'] = True
        raw, compressed = encoded(replay)
        return raw, compressed, False

    replay['meta'] = dict(replay.get('meta') or {})
    replay['meta']['truncated'] = True
    replay['meta']['truncated_reason'] = 'replay_size_limit'

    # Keep exact keyframes, but compact most action states. This preserves the
    # playable outline of long replays without letting a single long match hold
    # hundreds of full public-state snapshots in SQLite.
    compacted_actions = []
    for index, action in enumerate(actions):
        keep_state = index < 80 or index == len(actions) - 1 or index % 12 == 0
        compact_state = keep_state and index >= 80
        compacted_actions.append(_copy_replay_frame(action, keep_state=keep_state, compact_state=compact_state))
    replay['actions'] = compacted_actions
    raw, compressed = encoded(replay)
    if len(compressed) <= MAX_REPLAY_COMPRESSED_BYTES:
        return raw, compressed, True

    # If the action list itself is huge, retain the beginning and ending around
    # the decisive section. The match summary remains intact in matches.
    if len(compacted_actions) > MAX_REPLAY_STORED_ACTIONS:
        head_count = max(120, MAX_REPLAY_STORED_ACTIONS // 3)
        tail_count = max(120, MAX_REPLAY_STORED_ACTIONS - head_count)
        replay['actions'] = compacted_actions[:head_count] + compacted_actions[-tail_count:]
        replay['meta']['actions_truncated_from'] = len(compacted_actions)
        raw, compressed = encoded(replay)
    if len(compressed) <= MAX_REPLAY_COMPRESSED_BYTES:
        return raw, compressed, True

    replay['keyframes'] = [_copy_replay_frame(frame, keep_state=True, compact_state=True) for frame in keyframes[:20]]
    replay['actions'] = [_copy_replay_frame(action, keep_state=False) for action in replay.get('actions', [])]
    raw, compressed = encoded(replay)
    return raw, compressed, True


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _cutoff_iso(retention_days=None):
    days = DEFAULT_RETENTION_DAYS if retention_days is None else int(retention_days)
    return (datetime.now(timezone.utc) - timedelta(days=max(1, days))).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _row_dict(row):
    return dict(row) if row is not None else None


def _card_defs_snapshot(card_defs):
    cards = []
    for card_id in sorted((card_defs or {}).keys()):
        cd = card_defs[card_id]
        cards.append({
            'id': getattr(cd, 'id', card_id),
            'name_en': getattr(cd, 'name_en', ''),
            'name_cn': getattr(cd, 'name_cn', ''),
            'cost_e': getattr(cd, 'cost_e', 0),
            'cost_m': getattr(cd, 'cost_m', 0),
            'card_type': getattr(cd, 'card_type', ''),
            'count': getattr(cd, 'count', 0),
            'quality': getattr(cd, 'quality', ''),
            'description': getattr(cd, 'description', ''),
            'effect_text': getattr(cd, 'effect_text', ''),
            'flags': sorted(list(getattr(cd, 'flags', []) or [])),
            'trigger_cost_e': getattr(cd, 'trigger_cost_e', -1),
            'trigger_effect_text': getattr(cd, 'trigger_effect_text', ''),
            'response_trigger': getattr(cd, 'response_trigger', ''),
            'effects': getattr(cd, 'effects', []) or [],
            'scripts': getattr(cd, 'scripts', {}) or {},
            'response_title': getattr(cd, 'response_title', ''),
            'response_content': getattr(cd, 'response_content', ''),
            'ui_effect_size': getattr(cd, 'ui_effect_size', ''),
        })
    return {'cards': cards}


def _store_card_snapshot(conn, card_defs, game_version='', git_sha=''):
    if not card_defs:
        return ''
    raw = _json_bytes(_card_defs_snapshot(card_defs))
    digest = _sha256_bytes(raw)
    conn.execute(
        '''
        INSERT OR IGNORE INTO replay_card_def_snapshots (
            sha256, game_version, git_sha, created_at, json_size, json_blob
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (digest, game_version or '', git_sha or '', utc_now(), len(raw), raw),
    )
    return digest


def _insert_community_mod_blob(conn, *, digest, public_url='', name='', author='', version='', json_data=None, error=''):
    digest = str(digest or '').strip()
    if not digest:
        return ''
    if json_data is None:
        json_data = {
            'sha256': digest,
            'source': 'community',
            'public_url': public_url or '',
            'name': name or '',
            'captured_as': 'metadata_snapshot',
        }
        if error:
            json_data['snapshot_error'] = str(error)
    raw = _json_bytes(json_data)
    conn.execute(
        '''
        INSERT OR IGNORE INTO replay_mod_blobs (
            sha256, source, public_url, name, author, version, created_at, json_size, json_blob
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            digest,
            'community',
            public_url or '',
            name or '',
            author or '',
            version or '',
            utc_now(),
            len(raw),
            raw,
        ),
    )
    return digest


def _store_community_mod_blobs(conn, summary):
    if (summary or {}).get('mod_source') != 'community':
        return []
    hashes = []
    snapshots = summary.get('community_mod_snapshots')
    if isinstance(snapshots, list) and snapshots:
        for item in snapshots:
            if not isinstance(item, dict):
                continue
            digest = _insert_community_mod_blob(
                conn,
                digest=item.get('sha256'),
                public_url=item.get('public_url') or '',
                name=item.get('name') or '',
                author=item.get('author') or '',
                version=item.get('version') or '',
                json_data=item.get('json') if item.get('json') is not None else None,
                error=item.get('snapshot_error') or '',
            )
            if digest:
                hashes.append(digest)
        if hashes:
            return hashes
    entries = summary.get('community_mods') if isinstance(summary.get('community_mods'), list) else []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        digest = _insert_community_mod_blob(
            conn,
            digest=entry.get('sha256'),
            public_url=entry.get('public_url') or '',
            name=entry.get('name') or '',
            author=entry.get('author') or '',
            version=entry.get('version') or '',
        )
        if digest:
            hashes.append(digest)
    if hashes:
        return hashes
    digest = str(summary.get('mod_hash') or '').strip()
    if not digest:
        return []
    stored = _insert_community_mod_blob(
        conn,
        digest=digest,
        public_url=summary.get('community_mod_url') or '',
        name=summary.get('community_mod_name') or '',
        author=summary.get('community_mod_author') or '',
        version=summary.get('community_mod_version') or '',
    )
    return [stored] if stored else []


def save_replay_snapshot(match_id, summary, *, card_defs=None, game_version='', git_sha=''):
    data = dict(summary or {})
    players = data.get('players') or []
    duration_ms = int((data.get('duration_seconds') or 0) * 1000)
    replay_data = data.get('replay') if isinstance(data.get('replay'), dict) else {}
    keyframes = replay_data.get('keyframes') if isinstance(replay_data.get('keyframes'), list) else []
    actions = replay_data.get('actions') if isinstance(replay_data.get('actions'), list) else []
    if not keyframes:
        keyframes = [
            {
                'i': 0,
                't': 0,
                'phase': 'summary',
                'round': 0,
                'state': {'players': players, 'mode': data.get('mode')},
            }
        ]
    replay = {
        'version': REPLAY_VERSION,
        'meta': {
            'match_id': match_id,
            'mode': data.get('mode'),
            'players': players,
            'winner_name': data.get('winner_name'),
            'winner_index': data.get('winner_index'),
            'round_num': data.get('rounds'),
            'duration_ms': duration_ms,
            'created_at': data.get('ended_at') or utc_now(),
            'result': data.get('result'),
            'mod_source': data.get('mod_source') or 'official',
            'mod_hash': data.get('mod_hash') or '',
            'community_mod_name': data.get('community_mod_name') or '',
            'truncated': bool(replay_data.get('truncated')),
            'max_actions': replay_data.get('max_actions'),
        },
        'rules': {
            'game_version': game_version or '',
            'git_sha': git_sha or '',
        },
        'keyframes': keyframes,
        'actions': actions,
    }
    raw, compressed, storage_truncated = _encode_replay_for_storage(replay)
    digest = _sha256_bytes(raw)
    if storage_truncated:
        replay = json.loads(raw.decode('utf-8'))
    created_at = data.get('ended_at') or utc_now()
    with get_db_connection() as conn:
        card_hash = _store_card_snapshot(conn, card_defs, game_version=game_version, git_sha=git_sha)
        mod_hashes = _store_community_mod_blobs(conn, data)
        cur = conn.execute(
            '''
            INSERT INTO match_replays (
                match_id, created_at, mode, player_names_json, winner_name, winner_index,
                round_num, duration_ms, replay_version, replay_sha256, replay_size, replay_blob,
                mod_source, mod_hash, community_mod_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                match_id,
                created_at,
                data.get('mode'),
                json.dumps(players, ensure_ascii=False),
                data.get('winner_name'),
                data.get('winner_index'),
                data.get('rounds'),
                duration_ms,
                REPLAY_VERSION,
                digest,
                len(compressed),
                compressed,
                data.get('mod_source') or 'official',
                data.get('mod_hash') or '',
                data.get('community_mod_name') or '',
            ),
        )
        replay_id = cur.lastrowid
        deps = []
        if card_hash:
            deps.append(('card_defs', card_hash))
        for mod_hash in mod_hashes:
            deps.append(('community_mod', mod_hash))
        for dep_type, dep_hash in deps:
            conn.execute(
                'INSERT INTO replay_dependencies (replay_id, dep_type, dep_hash, created_at) VALUES (?, ?, ?, ?)',
                (replay_id, dep_type, dep_hash, created_at),
            )
        conn.commit()
        return replay_id


def _db_file_size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def storage_summary(retention_days=None):
    days = DEFAULT_RETENTION_DAYS if retention_days is None else int(retention_days)
    cutoff = _cutoff_iso(days)
    db_bytes = _db_file_size(DB_PATH)
    wal_bytes = _db_file_size(f'{DB_PATH}-wal')
    shm_bytes = _db_file_size(f'{DB_PATH}-shm')
    with get_db_connection() as conn:
        replay = conn.execute(
            '''
            SELECT COUNT(*) AS count, COALESCE(SUM(replay_size), 0) AS bytes,
                   MIN(created_at) AS oldest_created_at, MAX(created_at) AS newest_created_at
            FROM match_replays
            '''
        ).fetchone()
        old = conn.execute(
            'SELECT COUNT(*) AS count, COALESCE(SUM(replay_size), 0) AS bytes FROM match_replays WHERE created_at < ?',
            (cutoff,),
        ).fetchone()
        mods = conn.execute(
            '''
            SELECT COUNT(*) AS count, COALESCE(SUM(json_size), 0) AS bytes
            FROM replay_mod_blobs
            '''
        ).fetchone()
        orphan_mods = conn.execute(
            '''
            SELECT COUNT(*) AS count, COALESCE(SUM(json_size), 0) AS bytes
            FROM replay_mod_blobs b
            WHERE NOT EXISTS (
                SELECT 1 FROM replay_dependencies d
                WHERE d.dep_type = 'community_mod' AND d.dep_hash = b.sha256
            )
            '''
        ).fetchone()
        cards = conn.execute(
            'SELECT COUNT(*) AS count, COALESCE(SUM(json_size), 0) AS bytes FROM replay_card_def_snapshots'
        ).fetchone()
        orphan_cards = conn.execute(
            '''
            SELECT COUNT(*) AS count, COALESCE(SUM(json_size), 0) AS bytes
            FROM replay_card_def_snapshots b
            WHERE NOT EXISTS (
                SELECT 1 FROM replay_dependencies d
                WHERE d.dep_type = 'card_defs' AND d.dep_hash = b.sha256
            )
            '''
        ).fetchone()
    return {
        'db': {
            'path': DB_PATH,
            'db_file_bytes': db_bytes,
            'wal_file_bytes': wal_bytes,
            'shm_file_bytes': shm_bytes,
            'total_file_bytes': db_bytes + wal_bytes + shm_bytes,
        },
        'replays': {
            'count': replay['count'],
            'bytes': replay['bytes'],
            'old_count': old['count'],
            'old_bytes': old['bytes'],
            'retention_days': days,
            'oldest_created_at': replay['oldest_created_at'],
            'newest_created_at': replay['newest_created_at'],
        },
        'mod_blobs': {
            'community_count': mods['count'],
            'community_bytes': mods['bytes'],
            'orphan_count': orphan_mods['count'],
            'orphan_bytes': orphan_mods['bytes'],
        },
        'card_snapshots': {
            'count': cards['count'],
            'bytes': cards['bytes'],
            'orphan_count': orphan_cards['count'],
            'orphan_bytes': orphan_cards['bytes'],
        },
    }


def cleanup_orphan_replay_blobs(dry_run=False):
    with get_db_connection() as conn:
        orphan_mods = conn.execute(
            '''
            SELECT sha256, json_size FROM replay_mod_blobs b
            WHERE NOT EXISTS (
                SELECT 1 FROM replay_dependencies d
                WHERE d.dep_type = 'community_mod' AND d.dep_hash = b.sha256
            )
            '''
        ).fetchall()
        orphan_cards = conn.execute(
            '''
            SELECT sha256, json_size FROM replay_card_def_snapshots b
            WHERE NOT EXISTS (
                SELECT 1 FROM replay_dependencies d
                WHERE d.dep_type = 'card_defs' AND d.dep_hash = b.sha256
            )
            '''
        ).fetchall()
        result = {
            'deleted_mod_blobs': len(orphan_mods),
            'deleted_mod_blob_bytes': sum(int(row['json_size'] or 0) for row in orphan_mods),
            'deleted_card_snapshots': len(orphan_cards),
            'deleted_card_snapshot_bytes': sum(int(row['json_size'] or 0) for row in orphan_cards),
        }
        if not dry_run:
            conn.executemany('DELETE FROM replay_mod_blobs WHERE sha256 = ?', [(row['sha256'],) for row in orphan_mods])
            conn.executemany('DELETE FROM replay_card_def_snapshots WHERE sha256 = ?', [(row['sha256'],) for row in orphan_cards])
            conn.commit()
        return result


def _orphan_blob_preview_after_replay_delete(conn, replay_ids):
    ids = [int(value) for value in replay_ids]
    if ids:
        placeholders = ','.join('?' for _ in ids)
        mod_sql = f'''
            SELECT sha256, json_size FROM replay_mod_blobs b
            WHERE NOT EXISTS (
                SELECT 1 FROM replay_dependencies d
                WHERE d.dep_type = 'community_mod'
                  AND d.dep_hash = b.sha256
                  AND d.replay_id NOT IN ({placeholders})
            )
        '''
        card_sql = f'''
            SELECT sha256, json_size FROM replay_card_def_snapshots b
            WHERE NOT EXISTS (
                SELECT 1 FROM replay_dependencies d
                WHERE d.dep_type = 'card_defs'
                  AND d.dep_hash = b.sha256
                  AND d.replay_id NOT IN ({placeholders})
            )
        '''
        orphan_mods = conn.execute(mod_sql, ids).fetchall()
        orphan_cards = conn.execute(card_sql, ids).fetchall()
    else:
        orphan_mods = conn.execute(
            '''
            SELECT sha256, json_size FROM replay_mod_blobs b
            WHERE NOT EXISTS (
                SELECT 1 FROM replay_dependencies d
                WHERE d.dep_type = 'community_mod' AND d.dep_hash = b.sha256
            )
            '''
        ).fetchall()
        orphan_cards = conn.execute(
            '''
            SELECT sha256, json_size FROM replay_card_def_snapshots b
            WHERE NOT EXISTS (
                SELECT 1 FROM replay_dependencies d
                WHERE d.dep_type = 'card_defs' AND d.dep_hash = b.sha256
            )
            '''
        ).fetchall()
    return {
        'deleted_mod_blobs': len(orphan_mods),
        'deleted_mod_blob_bytes': sum(int(row['json_size'] or 0) for row in orphan_mods),
        'deleted_card_snapshots': len(orphan_cards),
        'deleted_card_snapshot_bytes': sum(int(row['json_size'] or 0) for row in orphan_cards),
    }


def cleanup_old_replays(retention_days=None, dry_run=False):
    cutoff = _cutoff_iso(retention_days)
    with get_db_connection() as conn:
        rows = conn.execute('SELECT id, replay_size FROM match_replays WHERE created_at < ?', (cutoff,)).fetchall()
        replay_ids = [row['id'] for row in rows]
        result = {
            'deleted_replays': len(rows),
            'deleted_replay_bytes': sum(int(row['replay_size'] or 0) for row in rows),
            'deleted_mod_blobs': 0,
            'deleted_mod_blob_bytes': 0,
            'deleted_card_snapshots': 0,
            'deleted_card_snapshot_bytes': 0,
            'cutoff': cutoff,
        }
        if dry_run:
            result.update(_orphan_blob_preview_after_replay_delete(conn, replay_ids))
            return result
        else:
            ids = [(replay_id,) for replay_id in replay_ids]
            conn.executemany('DELETE FROM replay_dependencies WHERE replay_id = ?', ids)
            conn.executemany('DELETE FROM match_replays WHERE id = ?', ids)
            conn.commit()
    orphan = cleanup_orphan_replay_blobs(dry_run=dry_run)
    result.update(orphan)
    return result


def checkpoint_db():
    with get_db_connection() as conn:
        rows = conn.execute('PRAGMA wal_checkpoint(TRUNCATE);').fetchall()
        return {'checkpoint': [tuple(row) for row in rows]}


def vacuum_db():
    with get_db_connection() as conn:
        conn.execute('VACUUM;')
    return {'vacuum': True}


def list_replays(limit=50, offset=0, mode='', player='', mod_source='', retention_days=None):
    safe_limit = max(1, min(int(limit or 50), 100))
    safe_offset = max(0, int(offset or 0))
    cutoff = _cutoff_iso(retention_days)
    where = ['created_at >= ?']
    params = [cutoff]
    if mode:
        where.append('mode = ?')
        params.append(str(mode))
    if player:
        where.append('player_names_json LIKE ?')
        params.append(f'%{str(player).strip()}%')
    if mod_source:
        where.append('COALESCE(mod_source, ?) = ?')
        params.extend(['official', str(mod_source)])
    where_sql = ' AND '.join(where)
    with get_db_connection() as conn:
        rows = conn.execute(
            f'''
            SELECT {REPLAY_ITEM_COLUMNS} FROM match_replays
            WHERE {where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
            ''',
            params + [safe_limit + 1, safe_offset],
        ).fetchall()
    items = [_replay_row_to_item(row) for row in rows[:safe_limit]]
    return {
        'items': items,
        'next_offset': safe_offset + len(items),
        'has_more': len(rows) > safe_limit,
        'limit': safe_limit,
        'offset': safe_offset,
    }


def _decode_replay_blob(blob):
    raw = bytes(blob or b'')
    if not raw:
        return {}
    try:
        raw = zlib.decompress(raw)
    except zlib.error:
        pass
    return json.loads(raw.decode('utf-8'))


def _replay_private_card_play_counters(state):
    counters = {}
    cumulative = {}

    def collect(player, fallback_index=None):
        if not isinstance(player, dict):
            return
        try:
            player_index = int(player.get('player_id', fallback_index))
        except (TypeError, ValueError):
            return
        if player_index < 0:
            return
        played = player.get('cards_played_this_turn')
        if isinstance(played, dict):
            total = 0
            for value in played.values():
                try:
                    total += max(0, int(value or 0))
                except (TypeError, ValueError):
                    continue
            counters[player_index] = total
        if 'achievement_total_card_plays' in player:
            try:
                cumulative[player_index] = max(0, int(player.get('achievement_total_card_plays') or 0))
            except (TypeError, ValueError):
                pass

    def collect_view(view, fallback_index=None):
        if not isinstance(view, dict):
            return
        players = view.get('spectate_players')
        if isinstance(players, list):
            for index, player in enumerate(players):
                collect(player, index)
        collect(view.get('you'), view.get('your_id', fallback_index))

    collect_view(state)
    perspectives = state.get('perspectives') if isinstance(state, dict) else None
    if isinstance(perspectives, list):
        for index, perspective in enumerate(perspectives):
            collect_view(perspective, index)
    return counters, cumulative


def recover_cards_played_from_replay_blob(blob, player_count=0):
    """Recover per-player card uses from a stored replay without expanding its full timeline."""
    try:
        replay = _decode_replay_blob(blob)
    except Exception as exc:
        return {'exact': False, 'counts': [], 'source': 'unrecoverable', 'reason': f'decode:{exc}'}
    if not isinstance(replay, dict):
        return {'exact': False, 'counts': [], 'source': 'unrecoverable', 'reason': 'invalid_replay'}

    meta = replay.get('meta') if isinstance(replay.get('meta'), dict) else {}
    try:
        expected_players = max(0, int(player_count or 0))
    except (TypeError, ValueError):
        expected_players = 0
    if expected_players <= 0:
        players = meta.get('players') if isinstance(meta.get('players'), list) else []
        expected_players = len(players)
    if expected_players <= 0:
        return {'exact': False, 'counts': [], 'source': 'unrecoverable', 'reason': 'no_players'}

    refs = _build_timeline_index(replay)
    materialized_state = {}
    round_counters = {}
    response_counts = [0] * expected_players
    final_cumulative = None
    saw_game_over = False
    saw_private_counters = False
    incomplete_private_state = bool(meta.get('truncated'))

    keyframes = replay.get('keyframes') if isinstance(replay.get('keyframes'), list) else []
    actions = replay.get('actions') if isinstance(replay.get('actions'), list) else []
    for ref in refs:
        kind = ref.get('kind')
        if kind == 'setup':
            continue
        source = None
        if kind == 'frame':
            source_index = _safe_int(ref.get('source_index'), -1)
            if 0 <= source_index < len(keyframes):
                source = keyframes[source_index]
        elif kind == 'action':
            source_index = _safe_int(ref.get('source_index'), -1)
            if 0 <= source_index < len(actions):
                source = actions[source_index]
        if not isinstance(source, dict):
            continue

        frame_state = source.get('state')
        if isinstance(frame_state, dict) and frame_state:
            if frame_state.get('truncated'):
                incomplete_private_state = True
            materialized_state = _merge_replay_frame_state(materialized_state, frame_state)
            counters, cumulative = _replay_private_card_play_counters(materialized_state)
            try:
                round_num = int(materialized_state.get('round_num', source.get('round', 0)) or 0)
            except (TypeError, ValueError):
                round_num = 0
            if round_num > 0 and counters:
                saw_private_counters = True
                round_counters.setdefault(round_num, {}).update(counters)

            action_type = str(source.get('type') or '') if kind == 'action' else ''
            is_game_over = action_type == 'game_over' or bool(materialized_state.get('game_over'))
            if is_game_over:
                saw_game_over = True
                if all(index in cumulative for index in range(expected_players)):
                    final_cumulative = [cumulative[index] for index in range(expected_players)]

        if kind != 'action':
            continue
        action_type = str(source.get('type') or '')
        if action_type == 'game_over':
            saw_game_over = True
        if action_type != 'response':
            continue
        payload = source.get('payload') if isinstance(source.get('payload'), dict) else {}
        card_instance_id = payload.get('card_instance_id')
        if card_instance_id in (None, '', 0, '0'):
            continue
        actor = _safe_int(source.get('actor'), -1)
        if 0 <= actor < expected_players:
            response_counts[actor] += 1

    if final_cumulative is not None and not bool(meta.get('truncated')):
        return {
            'exact': True,
            'counts': final_cumulative,
            'source': 'replay_total',
            'reason': '',
        }

    complete_rounds = bool(round_counters) and all(
        all(index in counters for index in range(expected_players))
        for counters in round_counters.values()
    )
    if saw_game_over and saw_private_counters and complete_rounds and not incomplete_private_state:
        counts = [0] * expected_players
        for counters in round_counters.values():
            for index in range(expected_players):
                counts[index] += max(0, int(counters.get(index, 0) or 0))
        for index, count in enumerate(response_counts):
            counts[index] += count
        return {
            'exact': True,
            'counts': counts,
            'source': 'replay_state',
            'reason': '',
        }

    reasons = []
    if not saw_game_over:
        reasons.append('no_game_over')
    if not saw_private_counters:
        reasons.append('no_private_counters')
    if incomplete_private_state:
        reasons.append('truncated')
    if round_counters and not complete_rounds:
        reasons.append('incomplete_players')
    return {
        'exact': False,
        'counts': [],
        'source': 'unrecoverable',
        'reason': ','.join(reasons) or 'incomplete_replay',
    }


def _row_get(row, key, default=None):
    try:
        if key in row.keys():
            return row[key]
    except Exception:
        pass
    return default


def _replay_row_to_item(row):
    players = []
    try:
        players = json.loads(row['player_names_json'] or '[]')
    except Exception:
        players = []
    meta = {}
    if (
        (_row_get(row, 'mod_source') is None or _row_get(row, 'community_mod_name') is None or _row_get(row, 'mod_hash') is None)
        and _row_get(row, 'replay_blob') is not None
    ):
        try:
            meta = _decode_replay_blob(row['replay_blob']).get('meta', {})
        except Exception:
            meta = {}
    return {
        'id': row['id'],
        'match_id': row['match_id'],
        'created_at': row['created_at'],
        'mode': row['mode'],
        'players': players,
        'winner_name': row['winner_name'],
        'winner_index': row['winner_index'],
        'round_num': row['round_num'],
        'duration_ms': row['duration_ms'],
        'replay_size': row['replay_size'],
        'mod_source': _row_get(row, 'mod_source') or meta.get('mod_source') or 'official',
        'community_mod_name': _row_get(row, 'community_mod_name') or meta.get('community_mod_name') or None,
        'mod_hash': _row_get(row, 'mod_hash') or meta.get('mod_hash') or '',
    }


def get_replay(replay_id):
    with get_db_connection() as conn:
        row = conn.execute(f'SELECT {REPLAY_ITEM_COLUMNS} FROM match_replays WHERE id = ?', (int(replay_id),)).fetchone()
    if row is None:
        return None
    return _replay_row_to_item(row)


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _replay_state_from_item(item):
    if not isinstance(item, dict):
        return {}
    state = item.get('state')
    return state if isinstance(state, dict) else {}


def _find_replay_game_start_state(keyframes, actions):
    candidates = []
    for frame in keyframes:
        if isinstance(frame, dict):
            label = str(frame.get('label') or '')
            phase = str(frame.get('phase') or '')
            if label == 'game_start' or phase in ('playing', 'action', 'game_over'):
                candidates.append(frame)
    for action in actions:
        if isinstance(action, dict):
            phase = str(action.get('phase') or '')
            if action.get('type') == 'game_start' or phase in ('playing', 'action', 'game_over'):
                candidates.append(action)
    if candidates:
        candidates.sort(key=lambda item: _safe_int(item.get('t'), 0))
        return _replay_state_from_item(candidates[0])
    for action in actions:
        if isinstance(action, dict) and str(action.get('type') or '') not in _REPLAY_SETUP_ACTION_TYPES:
            state = _replay_state_from_item(action)
            if state:
                return state
    for frame in reversed(keyframes):
        state = _replay_state_from_item(frame)
        if state:
            return state
    return {}


def _perspective_for_player(state, player_index):
    perspectives = state.get('perspectives') if isinstance(state, dict) else None
    if not isinstance(perspectives, list):
        return {}
    if 0 <= player_index < len(perspectives) and isinstance(perspectives[player_index], dict):
        return perspectives[player_index]
    if perspectives and isinstance(perspectives[0], dict):
        players = perspectives[0].get('spectate_players')
        if isinstance(players, list) and 0 <= player_index < len(players):
            return perspectives[0]
    return {}


def _player_state_from_perspective(perspective, player_index):
    if not isinstance(perspective, dict):
        return {}
    players = perspective.get('spectate_players')
    if isinstance(players, list) and 0 <= player_index < len(players) and isinstance(players[player_index], dict):
        return players[player_index]
    if isinstance(perspective.get('you'), dict):
        return perspective.get('you') or {}
    return {}


def _card_summary(card):
    if not isinstance(card, dict):
        return {}
    result = {
        'def_id': card.get('def_id') or card.get('id') or '',
        'instance_id': card.get('instance_id'),
    }
    for key in (
        'instance_flags', 'disabled_flags', 'fission_level', 'fusion_level',
        'held_turns', 'bonus_damage', 'cost_e_override', 'cost_m_override',
        'mimic_discount', 'return_to_hand_turns', 'swift_value',
    ):
        if key in card:
            result[key] = card.get(key)
    return result


def _format_setup_change_value(value):
    if isinstance(value, dict):
        parts = []
        if value.get('source_def_id') or value.get('magic_def_id'):
            parts.append(f"{value.get('source_def_id') or '?'} -> {value.get('magic_def_id') or '?'}")
        elif value.get('target_def_id') or value.get('target_instance_id'):
            parts.append(str(value.get('target_def_id') or value.get('target_instance_id') or ''))
        else:
            for key in sorted(value.keys()):
                parts.append(f"{key}={value.get(key)}")
        return ', '.join(parts)
    if isinstance(value, list):
        return '; '.join(_format_setup_change_value(item) for item in value if item is not None)
    return str(value)


def _extract_setup_actions(actions, player_count):
    selected = [{} for _ in range(player_count)]
    for action in actions:
        if not isinstance(action, dict):
            continue
        actor = action.get('actor')
        if actor is None:
            continue
        actor = _safe_int(actor, -1)
        if actor < 0 or actor >= player_count:
            continue
        payload = action.get('payload') if isinstance(action.get('payload'), dict) else {}
        if action.get('type') == 'select_opening_event':
            event_id = payload.get('event_id')
            selected[actor]['event_id'] = event_id
            selected[actor]['event_name'] = _OPENING_EVENT_NAMES_CN.get(str(event_id), str(event_id or ''))
            if isinstance(payload.get('sub_choice'), dict) and payload.get('sub_choice'):
                selected[actor].setdefault('changes', []).append({
                    'label': '配装变化',
                    'text': _format_setup_change_value(payload.get('sub_choice')),
                })
        elif action.get('type') == 'submit_event_sub_choice':
            sub_choice = payload.get('sub_choice')
            if isinstance(sub_choice, dict) and sub_choice:
                selected[actor].setdefault('changes', []).append({
                    'label': '配装变化',
                    'text': _format_setup_change_value(sub_choice),
                })
    return selected


def _extract_setup_log_changes(state, player_count):
    perspectives = state.get('perspectives') if isinstance(state, dict) else []
    log_source = {}
    if isinstance(perspectives, list):
        log_source = next((p for p in perspectives if isinstance(p, dict) and isinstance(p.get('log'), list)), {}) or {}
    logs = log_source.get('log') if isinstance(log_source, dict) else []
    changes = [[] for _ in range(player_count)]
    if not isinstance(logs, list):
        return changes
    player_names = state.get('player_names') if isinstance(state.get('player_names'), list) else []
    for line in logs:
        text = str(line or '')
        if '【' not in text or '】' not in text:
            continue
        for idx in range(player_count):
            name = str(player_names[idx]) if idx < len(player_names) else ''
            if (
                (name and (text.startswith(f'{name}【') or name in text))
                or f'Player {chr(65 + idx)}' in text
                or f'P{idx + 1}' in text
            ):
                changes[idx].append(text)
                break
    return changes


def _build_setup_summary_frame(keyframes, actions):
    state = _find_replay_game_start_state(keyframes, actions)
    player_names = state.get('player_names') if isinstance(state.get('player_names'), list) else []
    perspectives = state.get('perspectives') if isinstance(state.get('perspectives'), list) else []
    player_count = max(len(player_names), len(perspectives), 2)
    setup_actions = _extract_setup_actions(actions, player_count)
    log_changes = _extract_setup_log_changes(state, player_count)
    first_perspective = perspectives[0] if perspectives and isinstance(perspectives[0], dict) else {}
    picks = first_perspective.get('opening_event_picks') if isinstance(first_perspective.get('opening_event_picks'), list) else state.get('opening_event_picks')
    if not isinstance(picks, list):
        picks = []
    players = []
    for idx in range(player_count):
        perspective = _perspective_for_player(state, idx)
        player_state = _player_state_from_perspective(perspective, idx)
        hand = player_state.get('hand') if isinstance(player_state.get('hand'), list) else []
        event_id = setup_actions[idx].get('event_id')
        if event_id is None and idx < len(picks):
            event_id = picks[idx]
        event_name = setup_actions[idx].get('event_name') or _OPENING_EVENT_NAMES_CN.get(str(event_id), str(event_id or ''))
        changes = list(setup_actions[idx].get('changes') or [])
        for log_line in log_changes[idx]:
            changes.append({'label': '配装结果', 'text': log_line})
        players.append({
            'index': idx,
            'name': player_names[idx] if idx < len(player_names) else f'P{idx + 1}',
            'event_id': event_id,
            'event_name': event_name,
            'hand': [_card_summary(card) for card in hand if isinstance(card, dict)],
            'changes': changes,
        })
    return {
        'i': 0,
        't': 0,
        'phase': 'setup_summary',
        'round': 0,
        'current_player': state.get('current_player'),
        'label': '配装与起手',
        'state': state,
        'setup_summary': {
            'players': players,
            'note': '回放已跳过配装、选牌和开局抽牌过程。',
        },
        'log': [],
    }


def _is_replay_setup_noise_frame(frame):
    if not isinstance(frame, dict):
        return True
    label = str(frame.get('label') or '')
    phase = str(frame.get('phase') or '')
    if label in ('initial', 'event_select_start', 'draft_start', 'game_start'):
        return True
    return phase in _REPLAY_SETUP_PHASES


def _is_replay_setup_noise_action(action):
    if not isinstance(action, dict):
        return True
    action_type = str(action.get('type') or '')
    phase = str(action.get('phase') or '')
    return action_type in _REPLAY_SETUP_ACTION_TYPES or phase in _REPLAY_SETUP_PHASES


def _build_timeline_from_replay(replay):
    refs = _build_timeline_index(replay)
    return _materialize_timeline_slice(replay, refs, 0, len(refs))


def _apply_replay_state_delta(previous, patch):
    if not isinstance(patch, dict):
        return previous
    if '$set' in patch:
        return patch.get('$set')
    if '$list' in patch:
        spec = patch.get('$list') if isinstance(patch.get('$list'), dict) else {}
        base = list(previous) if isinstance(previous, list) else []
        start = max(0, min(len(base), _safe_int(spec.get('start'), 0)))
        items = spec.get('items') if isinstance(spec.get('items'), list) else []
        return base[:start] + items
    if '$items' in patch:
        base = list(previous) if isinstance(previous, list) else []
        changes = patch.get('$items') if isinstance(patch.get('$items'), dict) else {}
        for raw_index, child in changes.items():
            index = _safe_int(raw_index, -1)
            if 0 <= index < len(base):
                base[index] = _apply_replay_state_delta(base[index], child)
        return base
    if '$dict' in patch:
        base = dict(previous) if isinstance(previous, dict) else {}
        for key in patch.get('$remove') or []:
            base.pop(key, None)
        changes = patch.get('$dict') if isinstance(patch.get('$dict'), dict) else {}
        for key, child in changes.items():
            base[key] = _apply_replay_state_delta(base.get(key), child)
        return base
    return previous


def _merge_replay_frame_state(previous_state, frame_state):
    if not isinstance(frame_state, dict) or not frame_state:
        return previous_state or {}
    if frame_state.get('compact') and isinstance(previous_state, dict):
        merged = dict(previous_state)
        merged.update(frame_state)
        return merged
    if frame_state.get('delta') is True:
        return _apply_replay_state_delta(previous_state or {}, frame_state.get('patch') or {})
    return frame_state


def _build_timeline_index(replay):
    """Build a lightweight sorted frame index without copying full states."""
    keyframes = replay.get('keyframes') if isinstance(replay.get('keyframes'), list) else []
    actions = replay.get('actions') if isinstance(replay.get('actions'), list) else []
    refs = [{
        'kind': 'setup',
        'source_index': -1,
        't': 0,
        'order': 0,
        'sort_phase': 0,
    }]
    order = 1
    for source_index, frame in enumerate(keyframes):
        if isinstance(frame, dict) and not _is_replay_setup_noise_frame(frame):
            refs.append({
                'kind': 'frame',
                'source_index': source_index,
                't': int(frame.get('t') or 0),
                'seq': _safe_int(frame.get('seq'), -1) if frame.get('seq') is not None else None,
                'order': order,
                'sort_phase': 1,
            })
            order += 1
    for source_index, action in enumerate(actions):
        if isinstance(action, dict) and not _is_replay_setup_noise_action(action):
            refs.append({
                'kind': 'action',
                'source_index': source_index,
                't': int(action.get('t') or 0),
                'seq': _safe_int(action.get('seq'), -1) if action.get('seq') is not None else None,
                'order': order,
                'sort_phase': 1,
            })
            order += 1
    has_sequence = any(item.get('seq') is not None for item in refs if item.get('kind') != 'setup')
    if has_sequence:
        refs.sort(key=lambda item: (
            item.get('sort_phase', 1),
            item.get('seq') if item.get('seq') is not None else 10 ** 12 + item.get('order', 0),
        ))
    else:
        refs.sort(key=lambda item: (item.get('sort_phase', 1), item.get('t', 0), item.get('order', 0)))
    return refs


def _materialize_timeline_ref(replay, ref, display_index, fallback_state=None):
    kind = ref.get('kind')
    if kind == 'setup':
        keyframes = replay.get('keyframes') if isinstance(replay.get('keyframes'), list) else []
        actions = replay.get('actions') if isinstance(replay.get('actions'), list) else []
        item = _build_setup_summary_frame(keyframes, actions)
    elif kind == 'frame':
        keyframes = replay.get('keyframes') if isinstance(replay.get('keyframes'), list) else []
        frame = keyframes[int(ref.get('source_index') or 0)]
        item = {
            't': int(frame.get('t') or 0),
            'phase': frame.get('phase') or 'summary',
            'round': frame.get('round') or 0,
            'current_player': frame.get('current_player'),
            'state': frame.get('state') or fallback_state or {},
            'log': [],
        }
    else:
        actions = replay.get('actions') if isinstance(replay.get('actions'), list) else []
        action = actions[int(ref.get('source_index') or 0)]
        item = {
            't': int(action.get('t') or 0),
            'phase': action.get('phase') or '',
            'round': action.get('round') or 0,
            'current_player': action.get('current_player'),
            'action': action,
            'state': action.get('state') or fallback_state or {},
            'log': [],
        }
    item['i'] = display_index
    return item


def _materialize_timeline_slice(replay, refs, offset, limit):
    end = min(len(refs), offset + limit)
    timeline = []
    last_state = _build_setup_summary_frame(
        replay.get('keyframes') if isinstance(replay.get('keyframes'), list) else [],
        replay.get('actions') if isinstance(replay.get('actions'), list) else [],
    ).get('state') or {}
    for index in range(0, end):
        ref = refs[index]
        if index < offset:
            source = None
            if ref.get('kind') == 'frame':
                frames = replay.get('keyframes') if isinstance(replay.get('keyframes'), list) else []
                source = frames[int(ref.get('source_index') or 0)] if int(ref.get('source_index') or 0) < len(frames) else None
            elif ref.get('kind') == 'action':
                actions = replay.get('actions') if isinstance(replay.get('actions'), list) else []
                source = actions[int(ref.get('source_index') or 0)] if int(ref.get('source_index') or 0) < len(actions) else None
            if isinstance(source, dict) and source.get('state'):
                last_state = _merge_replay_frame_state(last_state, source.get('state'))
            continue
        item = _materialize_timeline_ref(replay, ref, index, last_state)
        if item.get('state'):
            last_state = _merge_replay_frame_state(last_state, item.get('state'))
            item['state'] = last_state
        timeline.append(item)
    return timeline


def _timeline_cache_store(replay_id, replay_sha, replay, **extra):
    cached = _TIMELINE_CACHE.get(replay_id)
    if cached and cached.get('sha') == replay_sha:
        cached.update(extra)
    else:
        cached = {'sha': replay_sha, 'replay': replay}
        cached.update(extra)
        _TIMELINE_CACHE[replay_id] = cached
    _TIMELINE_CACHE.move_to_end(replay_id)
    while len(_TIMELINE_CACHE) > _TIMELINE_CACHE_MAX:
        _TIMELINE_CACHE.popitem(last=False)
    return cached


def _timeline_cache_get(row):
    replay_id = int(row['id'])
    replay_sha = str(row['replay_sha256'] or '')
    cached = _TIMELINE_CACHE.get(replay_id)
    if cached and cached.get('sha') == replay_sha:
        _TIMELINE_CACHE.move_to_end(replay_id)
        if 'timeline' not in cached:
            cached['timeline'] = _build_timeline_from_replay(cached['replay'])
        return cached['replay'], cached['timeline']
    replay = _decode_replay_blob(row['replay_blob'])
    timeline = _build_timeline_from_replay(replay)
    _timeline_cache_store(replay_id, replay_sha, replay, timeline=timeline)
    return replay, timeline


def _timeline_index_cache_get(row):
    replay_id = int(row['id'])
    replay_sha = str(row['replay_sha256'] or '')
    cached = _TIMELINE_CACHE.get(replay_id)
    if cached and cached.get('sha') == replay_sha:
        _TIMELINE_CACHE.move_to_end(replay_id)
        if 'timeline' in cached:
            return cached['replay'], None, len(cached['timeline'])
        if 'timeline_index' not in cached:
            cached['timeline_index'] = _build_timeline_index(cached['replay'])
        return cached['replay'], cached['timeline_index'], len(cached['timeline_index'])
    replay = _decode_replay_blob(row['replay_blob'])
    timeline_index = _build_timeline_index(replay)
    _timeline_cache_store(replay_id, replay_sha, replay, timeline_index=timeline_index)
    return replay, timeline_index, len(timeline_index)


def replay_timeline(replay_id, offset=None, limit=None):
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM match_replays WHERE id = ?', (int(replay_id),)).fetchone()
    if row is None:
        return None
    sliced = False
    if offset is not None or limit is not None:
        sliced = True
        safe_offset = max(0, int(offset or 0))
        safe_limit = max(1, min(int(limit or 50), 200))
        replay, timeline_index, total_frames = _timeline_index_cache_get(row)
        if timeline_index is None:
            cached = _TIMELINE_CACHE.get(int(row['id']))
            timeline = cached.get('timeline') if cached else []
            response_timeline = timeline[safe_offset:safe_offset + safe_limit]
        else:
            response_timeline = _materialize_timeline_slice(replay, timeline_index, safe_offset, safe_limit)
    else:
        replay, timeline = _timeline_cache_get(row)
        total_frames = len(timeline)
        safe_offset = 0
        safe_limit = total_frames
        response_timeline = timeline
    return {
        'replay': {
            'id': row['id'],
            'meta': replay.get('meta') or {},
            'rules': replay.get('rules') or {},
            'duration_ms': row['duration_ms'],
        },
        'timeline': response_timeline,
        'total_frames': total_frames,
        'offset': safe_offset,
        'limit': safe_limit,
        'has_more': (safe_offset + len(response_timeline)) < total_frames if sliced else False,
        'mismatches': [],
    }
