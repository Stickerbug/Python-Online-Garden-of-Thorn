# -*- coding: utf-8 -*-
"""Restore selected members of a .gtnmod package from a git revision."""

from __future__ import annotations

import argparse
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", help="package filename inside mods/")
    parser.add_argument("members", nargs="+", help="zip members to restore")
    parser.add_argument("--rev", default="HEAD")
    args = parser.parse_args()
    rel = "mods/%s" % args.package
    blob = subprocess.run(
        ["git", "show", "%s:%s" % (args.rev, rel)], cwd=str(ROOT), capture_output=True
    ).stdout
    if not blob:
        print("no blob for", rel, file=sys.stderr)
        return 1
    with zipfile.ZipFile(io.BytesIO(blob)) as old_zip:
        old_members = {name: old_zip.read(name) for name in args.members if name in set(old_zip.namelist())}
    path = ROOT / "mods" / args.package
    with zipfile.ZipFile(path, "r") as zf:
        members = {item.filename: zf.read(item.filename) for item in zf.infolist()}
    for name, content in old_members.items():
        members[name] = content
    handle, temp_name = tempfile.mkstemp(suffix=".gtnmod", dir=str(path.parent))
    os.close(handle)
    temp_path = pathlib.Path(temp_name)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for name, content in members.items():
                zf.writestr(name, content)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    print("restored", len(old_members), "members in", args.package, "from", args.rev)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
