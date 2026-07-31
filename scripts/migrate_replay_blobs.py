#!/usr/bin/env python3
import argparse
import os
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import db
from replay_core import (
    load_replay_blob,
    remove_replay_blob_external,
    replay_blob_root,
    store_replay_blob_external,
)


def _summary(conn):
    return conn.execute(
        '''
        SELECT
            COUNT(*) AS total_count,
            COALESCE(SUM(replay_size), 0) AS total_bytes,
            SUM(CASE WHEN COALESCE(replay_blob_path, '') <> '' THEN 1 ELSE 0 END)
                AS external_count,
            COALESCE(SUM(LENGTH(replay_blob)), 0) AS sqlite_blob_bytes
        FROM match_replays
        '''
    ).fetchone()


def _format_bytes(value):
    size = float(value or 0)
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if size < 1024 or unit == 'TiB':
            return f'{size:.1f}{unit}'
        size /= 1024
    return f'{size:.1f}TiB'


def migrate(batch_size=25, limit=0, dry_run=False):
    db.init_db()
    with db.get_db_connection() as conn:
        before = _summary(conn)
        pending = conn.execute(
            '''
            SELECT COUNT(*) AS count, COALESCE(SUM(replay_size), 0) AS bytes
            FROM match_replays
            WHERE COALESCE(replay_blob_path, '') = '' AND LENGTH(replay_blob) > 0
            '''
        ).fetchone()
    print(
        'replay migration: '
        f'total={before["total_count"]} '
        f'external={int(before["external_count"] or 0)} '
        f'pending={pending["count"]} '
        f'pending_bytes={_format_bytes(pending["bytes"])} '
        f'root={replay_blob_root()}',
        flush=True,
    )
    if dry_run or int(pending['count'] or 0) == 0:
        return {
            'migrated': 0,
            'bytes': 0,
            'pending': int(pending['count'] or 0),
        }

    safe_batch_size = max(1, min(int(batch_size or 25), 200))
    safe_limit = max(0, int(limit or 0))
    migrated = 0
    migrated_bytes = 0
    started = time.monotonic()
    while True:
        remaining = safe_limit - migrated if safe_limit else safe_batch_size
        if safe_limit and remaining <= 0:
            break
        fetch_limit = min(safe_batch_size, remaining) if safe_limit else safe_batch_size
        with db.get_db_connection() as conn:
            rows = conn.execute(
                '''
                SELECT id, replay_size, replay_sha256, replay_blob, replay_blob_path
                FROM match_replays
                WHERE COALESCE(replay_blob_path, '') = '' AND LENGTH(replay_blob) > 0
                ORDER BY id
                LIMIT ?
                ''',
                (fetch_limit,),
            ).fetchall()
        if not rows:
            break

        staged = []
        try:
            for row in rows:
                payload = load_replay_blob(row)
                relative_path = store_replay_blob_external(payload)
                staged.append((row, relative_path, len(payload)))
            with db.get_db_connection() as conn:
                conn.execute('BEGIN IMMEDIATE')
                for row, relative_path, payload_size in staged:
                    updated = conn.execute(
                        '''
                        UPDATE match_replays
                        SET replay_blob = X'', replay_blob_path = ?
                        WHERE id = ?
                          AND COALESCE(replay_blob_path, '') = ''
                          AND LENGTH(replay_blob) = ?
                        ''',
                        (relative_path, int(row['id']), payload_size),
                    )
                    if int(updated.rowcount or 0) != 1:
                        raise RuntimeError(f'replay changed during migration: {row["id"]}')
                conn.commit()
        except Exception:
            for _row, relative_path, _payload_size in staged:
                try:
                    remove_replay_blob_external(relative_path)
                except (OSError, ValueError):
                    pass
            raise

        migrated += len(staged)
        migrated_bytes += sum(item[2] for item in staged)
        elapsed = max(0.001, time.monotonic() - started)
        print(
            f'migrated={migrated} bytes={_format_bytes(migrated_bytes)} '
            f'rate={migrated / elapsed:.1f}/s',
            flush=True,
        )

    with db.get_db_connection() as conn:
        after = _summary(conn)
    return {
        'migrated': migrated,
        'bytes': migrated_bytes,
        'pending': int(after['total_count'] or 0) - int(after['external_count'] or 0),
        'sqlite_blob_bytes': int(after['sqlite_blob_bytes'] or 0),
    }


def verify_external_files():
    checked = 0
    checked_bytes = 0
    with db.get_db_connection() as conn:
        rows = conn.execute(
            '''
            SELECT id, replay_size, replay_blob, replay_blob_path
            FROM match_replays
            WHERE COALESCE(replay_blob_path, '') <> ''
            ORDER BY id
            '''
        ).fetchall()
    for row in rows:
        payload = load_replay_blob(row)
        checked += 1
        checked_bytes += len(payload)
    print(
        f'verified={checked} bytes={_format_bytes(checked_bytes)}',
        flush=True,
    )
    return {'checked': checked, 'bytes': checked_bytes}


def vacuum_database():
    db_path = os.path.abspath(db.DB_PATH)
    before = os.path.getsize(db_path)
    with db.get_db_connection() as conn:
        conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        conn.execute('VACUUM')
    after = os.path.getsize(db_path)
    print(
        f'vacuum complete: before={_format_bytes(before)} after={_format_bytes(after)}',
        flush=True,
    )
    return {'before': before, 'after': after}


def main():
    parser = argparse.ArgumentParser(
        description='Move compressed replay payloads out of the core GTN SQLite database.'
    )
    parser.add_argument('--batch-size', type=int, default=25)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--vacuum', action='store_true')
    args = parser.parse_args()

    result = migrate(
        batch_size=args.batch_size,
        limit=args.limit,
        dry_run=args.dry_run,
    )
    print(f'migration result: {result}', flush=True)
    if args.verify and not args.dry_run:
        verify_external_files()
    if args.vacuum and not args.dry_run:
        vacuum_database()


if __name__ == '__main__':
    main()
