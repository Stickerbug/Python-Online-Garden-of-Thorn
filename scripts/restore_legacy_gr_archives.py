"""Restore pre-R1 Garden Rating values; dry-run unless --confirm is supplied."""

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import db  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='apply the restore in one transaction; omission performs a read-only preview',
    )
    args = parser.parse_args()
    result = db.restore_legacy_gr_archives(dry_run=not args.confirm)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
