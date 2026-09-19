# -*- coding: utf-8 -*-
"""Fill card *names* that stayed English inside a localized locale file.

反馈 #176：生化 DLC / 工厂 DLC 里有几张牌的 ``locales/zh.json`` 名字仍写着英文
(``Cyanide Pill`` / ``Stem Cell`` / ``Mitochondria`` / ``Lithium``)，玩家看到的就是
「牌没补中文翻译」，虽然效果与风味文本其实都译好了。这里按 ``mod.json`` 的
``name_cn`` 与既有译名补齐 zh/fr/ja 三个槽位；只有当前值仍是英文（或为空）时才覆盖，
方便重复执行。
"""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"

FIXES = {
    "Bio Cards DLC.gtnmod": {
        "bio:cyanide_pill": {
            "zh": "氰化物药丸",
            "fr": "Pilule de cyanure",
            "ja": "青酸カプセル",
        },
        "bio:stem_cell": {
            "zh": "干细胞",
            "fr": "Cellule souche",
            "ja": "幹細胞",
        },
        "bio:mitochondria": {
            "zh": "线粒体",
            "fr": "Mitochondrie",
            "ja": "ミトコンドリア",
        },
    },
    "Factory Cards DLC.gtnmod": {
        "factory:lithium": {
            "zh": "锂",
            "ja": "リチウム",
        },
    },
}


def has_cjk(text) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in str(text or ""))


def load_package(path: pathlib.Path):
    with zipfile.ZipFile(path, "r") as archive:
        members = {item.filename: archive.read(item.filename) for item in archive.infolist()}
    return members


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


def main() -> int:
    patched = []
    for filename, cards in FIXES.items():
        path = MODS / filename
        members = load_package(path)
        locales = {}
        for language in ("zh", "en", "fr", "ja"):
            key = f"locales/{language}.json"
            if key in members:
                locales[language] = json.loads(members[key].decode("utf-8-sig"))
        changed = False
        for card_id, names in cards.items():
            english = str(((locales.get("en") or {}).get("cards", {}).get(card_id) or {}).get("name") or "")
            for language, value in names.items():
                locale = locales.get(language)
                if not locale:
                    continue
                entry = locale.setdefault("cards", {}).setdefault(card_id, {})
                current = str(entry.get("name") or "")
                if has_cjk(current) or (current and current != english and language == "zh"):
                    continue
                if current == value:
                    continue
                entry["name"] = value
                changed = True
                patched.append(f"{filename}:{card_id}:{language}={value}")
        if changed:
            for language, payload in locales.items():
                members[f"locales/{language}.json"] = (
                    json.dumps(payload, ensure_ascii=False, indent=2)
                ).encode("utf-8")
            write_package(path, members)
    for entry in patched:
        print(entry)
    print(f"patched {len(patched)} name slot(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
