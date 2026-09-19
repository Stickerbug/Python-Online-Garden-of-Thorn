# -*- coding: utf-8 -*-
"""把官方牌里「摧毁此装备」统一成描述规范的写法「摧毁本装备；」。

反馈 #60/#165 修完之后，`tests/test_vanilla_self_destroy_descriptions.py` 里的自毁
描述契约测试暴露出两类历史遗留：

1. 同一个牌面里前面写「本装备获得…」、触发处却写「摧毁此装备，」；
2. 触发格式与 `docs/卡牌描述规范.md` §9.1 的 `触发：摧毁本装备；选择一个目标……`
   不一致（逗号 vs 分号）。

另外 `jungle:flower` 还留着一份旧的 `trigger_effect_text`（牌面已经写全了触发，
规范要求触发只写在牌面）。这个脚本只做这两件事，重复执行无副作用。
"""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"
# 内置兜底牌表与其多语言表也带着同一段旧文案（mod 数据缺失时的回退用）
SOURCE_FILES = ("cards.py", "card_i18n.py")

TEXT_FIELDS = ("effect_text", "trigger_effect_text")
REPLACEMENTS = (
    ("摧毁此装备，", "摧毁本装备；"),
    ("摧毁此装备；", "摧毁本装备；"),
    ("摧毁此装备", "摧毁本装备"),
    ("摧毁本装备，", "摧毁本装备；"),
)
# 牌面已写明触发的牌，不再保留重复的 trigger_effect_text
DROP_TRIGGER_EFFECT_TEXT = {
    "Jungle Cards Addition.gtnmod": {"jungle:flower"},
}


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


def normalize_text(text: str) -> str:
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    return text


def main() -> int:
    changed_notes = []
    for relative in SOURCE_FILES:
        source_path = ROOT / relative
        original = source_path.read_text(encoding="utf-8")
        updated = normalize_text(original)
        if updated != original:
            source_path.write_text(updated, encoding="utf-8")
            changed_notes.append(f"{relative}:builtin-effect-text")

    for path in sorted(MODS.glob("*.gtnmod")):
        members = load_package(path)
        mod_data = json.loads(members["mod.json"].decode("utf-8-sig"))
        locales = {
            language: json.loads(members[f"locales/{language}.json"].decode("utf-8-sig"))
            for language in ("zh",)
            if f"locales/{language}.json" in members
        }
        changed = False

        for card in (mod_data.get("registries") or {}).get("cards") or []:
            for field in TEXT_FIELDS:
                value = card.get(field)
                if isinstance(value, str):
                    new_value = normalize_text(value)
                    if new_value != value:
                        card[field] = new_value
                        changed = True
                        changed_notes.append(f"{path.name}:{card.get('id')}:{field}")
            if card.get("id") in DROP_TRIGGER_EFFECT_TEXT.get(path.name, set()):
                if "trigger_effect_text" in card:
                    card.pop("trigger_effect_text", None)
                    changed = True
                    changed_notes.append(f"{path.name}:{card.get('id')}:drop-trigger-effect-text")

        for locale in locales.values():
            for card_id, entry in (locale.get("cards") or {}).items():
                if not isinstance(entry, dict):
                    continue
                for field in TEXT_FIELDS:
                    value = entry.get(field)
                    if isinstance(value, str):
                        new_value = normalize_text(value)
                        if new_value != value:
                            entry[field] = new_value
                            changed = True
                            changed_notes.append(f"{path.name}:{card_id}:{field}:locale")
                if card_id in DROP_TRIGGER_EFFECT_TEXT.get(path.name, set()):
                    if "trigger_effect_text" in entry:
                        entry.pop("trigger_effect_text", None)
                        changed = True
                        changed_notes.append(f"{path.name}:{card_id}:drop-trigger-effect-text:locale")

        if not changed:
            continue
        members["mod.json"] = json.dumps(mod_data, ensure_ascii=False, indent=2).encode("utf-8")
        for language, payload in locales.items():
            members[f"locales/{language}.json"] = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        write_package(path, members)

    for note in changed_notes:
        print(note)
    print(f"patched {len(changed_notes)} field(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
