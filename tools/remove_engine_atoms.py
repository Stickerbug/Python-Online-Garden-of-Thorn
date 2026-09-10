# -*- coding: utf-8 -*-
"""Delete card-specific ``_atomic_*`` handlers from the engine files.

Used by the atom refactor: once every package expresses a mechanic with generic
data steps, the bespoke handler is removed so the engine only keeps reusable
atoms. The script refuses to delete a handler that is still referenced
elsewhere in the engine (callers inside other atoms must be rewritten first).
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGETS = ("game_engine.py", "game_engine_2v2.py", "game_engine_urf.py")


def find_block(source: str, name: str):
    match = re.search(r"\n    def _atomic_%s\(" % re.escape(name), source)
    if not match:
        return None
    start = match.start() + 1
    nxt = source.find("\n    def ", match.end())
    end = nxt + 1 if nxt > 0 else len(source)
    return start, end


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="+")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    removed, missing, still_used = [], [], []
    for filename in TARGETS:
        path = ROOT / filename
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        for name in args.names:
            block = find_block(source, name)
            if block is None:
                continue
            start, end = block
            body = source[start:end]
            callers = [
                match for match in re.finditer(r"_atomic_%s\(" % re.escape(name), source)
                if not (start <= match.start() < end)
            ]
            if callers:
                still_used.append((filename, name))
                continue
            source = source[:start] + source[end:]
            removed.append((filename, name))
        if args.apply:
            path.write_text(source, encoding="utf-8")
    for filename, name in removed:
        print("removed", name, "from", filename)
    for filename, name in still_used:
        print("SKIPPED (still called):", name, "in", filename, file=sys.stderr)
    found = sorted({name for _, name in removed} | {name for _, name in still_used})
    for name in args.names:
        if name not in found:
            missing.append(name)
    if missing:
        print("not found:", ", ".join(missing), file=sys.stderr)
    if not args.apply:
        print("(dry run; pass --apply to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
