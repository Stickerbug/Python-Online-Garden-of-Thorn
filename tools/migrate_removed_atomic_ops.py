# -*- coding: utf-8 -*-
"""把官方模组包里残留的「已移除原子」迁移成规范写法。

反馈 #186：批次 DD 把 ``player_status_layers`` 并进 ``status_op`` 并删除旧原子，但
``mods/Ocean Cards Addition.gtnmod`` 的黄瓜（``ocean:cucumber``）还在用它，
上线后黄瓜的「1层无法选中」直接报错失效。批次 DD 的文档（引擎原子与数据步骤清单 §90.2）
只迁移了 ``void:cicada_3301``，漏了这张。

``player_status_layers(status:X, amount:N)`` → ``status_op(action:"add", status:X, amount:N)``
（无法选中 = ``untargetable``、无敌 = ``invincible``，与 §90.2 给出的替代写法一致）。
脚本幂等，重复执行无副作用。
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"


def load_package(path: pathlib.Path):
    with zipfile.ZipFile(path, "r") as archive:
        return {item.filename: archive.read(item.filename) for item in archive.infolist()}


def write_package(path: pathlib.Path, members: dict) -> None:
    handle, temp_name = tempfile.mkstemp(suffix=".gtnmod", dir=str(path.parent))
    os.close(handle)
    temp_path = pathlib.Path(temp_name)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, content in members.items():
                archive.writestr(name, content)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def migrate_node(value, notes, where="") -> None:
    if isinstance(value, dict):
        if value.get("op") == "player_status_layers":
            status = str(value.get("status") or "").strip()
            amount = value.get("amount", 1)
            value.clear()
            value.update({
                "op": "status_op",
                "action": "add",
                "status": status,
                "amount": amount,
            })
            notes.append(where + " -> status_op(add, " + status + ")")
        for key, item in value.items():
            migrate_node(item, notes, where + "." + str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            migrate_node(item, notes, where + "[" + str(index) + "]")


def main() -> int:
    changed = []
    for path in sorted(MODS.glob("*.gtnmod")):
        members = load_package(path)
        raw = members["mod.json"].decode("utf-8-sig")
        if "player_status_layers" not in raw:
            continue
        data = json.loads(raw)
        notes = []
        for card in (data.get("registries") or {}).get("cards") or []:
            migrate_node(card, notes, str(card.get("id")))
        if not notes:
            continue
        members["mod.json"] = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        write_package(path, members)
        for note in notes:
            changed.append(path.name + ": " + note)
            print(path.name + ": " + note)
    print("patched " + str(len(changed)) + " step(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
