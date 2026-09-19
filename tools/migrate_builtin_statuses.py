# -*- coding: utf-8 -*-
"""把官方包里的状态声明搬到内置表（Round 107 / 批次 DE，方案 B）。

做的事：删掉 ``mods/*.gtnmod`` 里 ``registries.statuses`` 中**已内置**的条目
（``official_statuses.py`` 的 17 条），并清掉 ``locales/*.json`` 里对应的
``statuses`` 文案——这些文案已经进内置表，留着就是第二个来源。

形式逻辑 DLC（``formal_logic:*``）不在内置范围，原样保留。

用法::

    python tools/migrate_builtin_statuses.py            # 迁移（幂等，可重复跑）
    python tools/migrate_builtin_statuses.py --check     # 只检查有没有残留声明
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import official_statuses  # noqa: E402

MODS = ROOT / "mods"


def builtin_ids() -> set:
    return {str(item["id"]) for item in official_statuses.OFFICIAL_STATUSES}


def rewrite_package(path: pathlib.Path, builtin: set) -> dict:
    with zipfile.ZipFile(path) as archive:
        members = [(info.filename, archive.read(info.filename)) for info in archive.infolist()]
    changes = {"statuses": [], "locales": []}
    payload = json.loads(dict(members)["mod.json"].decode("utf-8-sig"))
    registries = payload.get("registries") or {}
    statuses = registries.get("statuses")
    if isinstance(statuses, list):
        kept = []
        for item in statuses:
            status_id = str((item or {}).get("id") or "") if isinstance(item, dict) else ""
            if status_id and status_id in builtin:
                changes["statuses"].append(status_id)
                continue
            kept.append(item)
        if changes["statuses"]:
            registries["statuses"] = kept
    for name, content in members:
        if not name.startswith("locales/") or not name.endswith(".json"):
            continue
        document = json.loads(content.decode("utf-8-sig"))
        entries = document.get("statuses")
        if not isinstance(entries, dict) or not entries:
            continue
        for status_id in [key for key in entries if key in builtin]:
            entries.pop(status_id, None)
            changes["locales"].append(f"{name}:{status_id}")
        if not entries:
            document.pop("statuses", None)
    if not changes["statuses"] and not changes["locales"]:
        return changes
    new_members = []
    for name, content in members:
        if name == "mod.json":
            content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        elif name.startswith("locales/") and name.endswith(".json"):
            document = json.loads(content.decode("utf-8-sig"))
            entries = document.get("statuses")
            if isinstance(entries, dict):
                for status_id in [key for key in entries if key in builtin]:
                    entries.pop(status_id, None)
                if not entries:
                    document.pop("statuses", None)
            content = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
        new_members.append((name, content))
    handle, temp_name = tempfile.mkstemp(suffix=".gtnmod", dir=str(path.parent))
    os.close(handle)
    temp_path = pathlib.Path(temp_name)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, content in new_members:
                archive.writestr(name, content)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只检查残留，不写文件")
    args = parser.parse_args()

    builtin = builtin_ids()
    leftovers = []
    total_statuses = 0
    total_locales = 0
    for path in sorted(MODS.glob("*.gtnmod")):
        with zipfile.ZipFile(path) as archive:
            payload = json.loads(archive.read("mod.json").decode("utf-8-sig"))
        declared = [
            str((item or {}).get("id") or "")
            for item in (payload.get("registries") or {}).get("statuses") or []
            if isinstance(item, dict)
        ]
        stale = [status_id for status_id in declared if status_id in builtin]
        if args.check:
            if stale:
                leftovers.append((path.name, stale))
            continue
        if not stale:
            continue
        changes = rewrite_package(path, builtin)
        total_statuses += len(changes["statuses"])
        total_locales += len(changes["locales"])
        print(f"{path.name}: 删除声明 {len(changes['statuses'])} 条，"
              f"locales 文案 {len(changes['locales'])} 条")
    if args.check:
        if leftovers:
            for name, stale in leftovers:
                print(f"残留内置状态声明：{name} → {stale}", file=sys.stderr)
            return 1
        print(f"官方包已无内置状态声明（内置 {len(builtin)} 条）")
        return 0
    print(f"完成：删除声明 {total_statuses} 条，locales 文案 {total_locales} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
