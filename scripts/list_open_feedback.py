#!/usr/bin/env python3
"""List public feedback issues that still need fixing, read-only.

Runs against the production database through the local SSH alias so no
feedback status is changed.  By default it lists open bug reports while
excluding finished/closed states such as fixed, in_progress and by_design.
"""

import argparse
import shlex
import shutil
import subprocess
import sys


SSH_ALIAS = 'aliyun-gtn'
DB_PATH = '/var/lib/gtn/gtn.sqlite3'
OPEN_BUG_STATUSES = ('new', 'needs_info', 'confirmed')


def run_query(query):
    ssh = shutil.which('ssh')
    if not ssh:
        sys.exit('ssh not found; this helper needs the configured SSH alias.')
    remote_command = f'sqlite3 -readonly {DB_PATH} {shlex.quote(query)}'
    command = [ssh, SSH_ALIAS, remote_command]
    process = subprocess.run(command, capture_output=True)
    if process.returncode != 0:
        stderr = process.stderr.decode('utf-8', errors='replace').strip()
        sys.exit(stderr or f'SSH/sqlite query failed with exit code {process.returncode}')
    return process.stdout.decode('utf-8', errors='replace')


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except Exception:
            pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--limit',
        type=int,
        default=80,
        help='Maximum number of open bugs to print (default: 80).',
    )
    args = parser.parse_args()

    placeholders = ','.join('?' for _ in OPEN_BUG_STATUSES)
    query = (
        'SELECT id, status, title, substr(created_at,1,19) AS created '
        'FROM public_issues '
        f"WHERE kind='bug' AND visible=1 AND status IN ({placeholders}) "
        'ORDER BY id DESC LIMIT ?;'
    )
    # sqlite3 binds only through its own interface; substitute validated
    # status literals and the integer limit directly instead of parameterizing.
    query = query.replace(placeholders, ', '.join(f"'{s}'" for s in OPEN_BUG_STATUSES))
    query = query.replace('LIMIT ?;', f'LIMIT {max(1, int(args.limit))};')
    output = run_query(query)
    print(f'Open bugs ({SSH_ALIAS}):')
    print(output or '（无）')


if __name__ == '__main__':
    main()
