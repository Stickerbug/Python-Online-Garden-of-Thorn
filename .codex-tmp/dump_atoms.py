# -*- coding: utf-8 -*-
"""Dump every remaining card-specific atom body into one text file."""

import io
import pathlib
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = ("game_engine.py", "game_engine_2v2.py", "game_engine_urf.py")
PREFIXES = (
    "hel", "arctic", "jungle", "bio", "ocean", "desert", "sewers", "garden",
    "jurassic", "void",
)
out = []
for filename in FILES:
    src = (ROOT / filename).read_text(encoding="utf-8")
    lines = src.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"\s*def _atomic_([A-Za-z0-9_]+)\(", line)
        if not match:
            continue
        name = match.group(1)
        if name.split("_")[0] not in PREFIXES:
            continue
        body = []
        for offset in range(index, len(lines)):
            if offset > index and lines[offset].startswith("    def "):
                break
            body.append("%5d %s" % (offset + 1, lines[offset]))
        out.append("\n".join(body))
target = ROOT / ".codex-tmp" / "atoms_dump.txt"
target.write_text("\n\n".join(out), encoding="utf-8")
print("atoms:", len(out), "->", target)
print("lines:", len(target.read_text(encoding="utf-8").splitlines()))
