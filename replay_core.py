import hashlib
import json
import os
import sqlite3
import zlib
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from db import DB_PATH, get_db_connection, utc_now


REPLAY_VERSION = 1
DEFAULT_RETENTION_DAYS = int(os.environ.get('GTN_REPLAY_RETENTION_DAYS', '90') or 90)
CLEANUP_HOUR = int(os.environ.get('GTN_CLEANUP_HOUR', '4') or 4)
CLEANUP_MINUTE = int(os.environ.get('GTN_CLEANUP_MINUTE', '30') or 30)
REPLAY_ITEM_COLUMNS = '''
    id, match_id, created_at, mode, player_names_json, winner_name, winner_index,
    round_num, duration_ms, replay_version, replay_sha256, replay_size,
    mod_source, mod_hash, community_mod_name
'''
_TIMELINE_CACHE = OrderedDict()
_TIMELINE_CACHE_MAX = 4


def _json_bytes(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


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
    raw = _json_bytes(replay)
    compressed = zlib.compress(raw, level=6)
    digest = _sha256_bytes(raw)
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


def _build_timeline_from_replay(replay):
    keyframes = replay.get('keyframes') if isinstance(replay.get('keyframes'), list) else []
    actions = replay.get('actions') if isinstance(replay.get('actions'), list) else []
    timeline = []
    for index, frame in enumerate(keyframes):
        if isinstance(frame, dict):
            timeline.append({
                'i': len(timeline),
                't': int(frame.get('t') or 0),
                'phase': frame.get('phase') or 'summary',
                'round': frame.get('round') or 0,
                'current_player': frame.get('current_player'),
                'state': frame.get('state') or {},
                'log': [],
            })
    for action in actions:
        if isinstance(action, dict):
            timeline.append({
                'i': len(timeline),
                't': int(action.get('t') or 0),
                'phase': action.get('phase') or '',
                'round': action.get('round') or 0,
                'current_player': action.get('current_player'),
                'action': action,
                'state': action.get('state') or {},
                'log': [],
            })
    timeline.sort(key=lambda item: (item.get('t', 0), item.get('i', 0)))
    for index, item in enumerate(timeline):
        item['i'] = index
    return timeline


def _timeline_cache_get(row):
    replay_id = int(row['id'])
    replay_sha = str(row['replay_sha256'] or '')
    cached = _TIMELINE_CACHE.get(replay_id)
    if cached and cached.get('sha') == replay_sha:
        _TIMELINE_CACHE.move_to_end(replay_id)
        return cached['replay'], cached['timeline']
    replay = _decode_replay_blob(row['replay_blob'])
    timeline = _build_timeline_from_replay(replay)
    _TIMELINE_CACHE[replay_id] = {'sha': replay_sha, 'replay': replay, 'timeline': timeline}
    _TIMELINE_CACHE.move_to_end(replay_id)
    while len(_TIMELINE_CACHE) > _TIMELINE_CACHE_MAX:
        _TIMELINE_CACHE.popitem(last=False)
    return replay, timeline


def replay_timeline(replay_id, offset=None, limit=None):
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM match_replays WHERE id = ?', (int(replay_id),)).fetchone()
    if row is None:
        return None
    replay, timeline = _timeline_cache_get(row)
    total_frames = len(timeline)
    sliced = False
    if offset is not None or limit is not None:
        sliced = True
        safe_offset = max(0, int(offset or 0))
        safe_limit = max(1, min(int(limit or 50), 200))
        response_timeline = timeline[safe_offset:safe_offset + safe_limit]
    else:
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
