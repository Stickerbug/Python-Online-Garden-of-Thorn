# -*- coding: utf-8 -*-
"""抽取卡面文字的"关键词着色"规则，供模组编辑器预览使用。

游戏的卡牌效果文本会经过 ``colorizeCardText()``：关键词变成带颜色的 chip、
``[[icon:D]]`` 这类标记变成小图标。编辑器要看起来一样，就得拿到同一份规则，
而不是自己写一套近似实现。

本脚本从 ``static/js/game.js`` 里抽出：

* ``CARD_TEXT_TOKEN_RULES`` —— 关键词 → CSS 类 + 正则（77 条）；
* ``INLINE_ICON_DATA_URLS`` —— 内嵌图标（data URL）；
* ``getInlineIconUrl`` 的 uiIcons / statusIcons 映射；
* ``getIconTokenClass`` / ``getCardTextTokenIconKey`` 的类名映射；

并把 ``static/assets/ui-icons``、``static/assets/status-icons`` 复制到编辑器侧，
最后写出一个 JS 文件（不是 JSON——编辑器可能直接用 file:// 打开，fetch 会失败）。

    python tools/extract_card_text_rules.py
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re
import shutil
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = ROOT / "static" / "js" / "game.js"
EDITOR = ROOT.parent / "模组编辑器" / "src" / "generated"
MODS = ROOT / "mods"


def extract_card_index() -> dict:
    """官方包里的卡牌索引：id / legacy_id / 名称 / 类型。

    效果文字里的 ``[[card:DefId]]`` 标记要靠它查出卡名和类型色——编辑器本来也需要
    这份索引来做选牌器和校验。
    """

    index = {}
    for path in sorted(glob.glob(str(MODS / "*.gtnmod"))):
        try:
            with zipfile.ZipFile(path) as archive:
                payload = json.loads(archive.read("mod.json"))
        except Exception:
            continue
        for card in (payload.get("registries") or {}).get("cards") or []:
            if not isinstance(card, dict):
                continue
            full_id = str(card.get("id") or "")
            if not full_id:
                continue
            entry = {
                "id": full_id,
                "short": full_id.split(":")[-1],
                "legacy_id": str(card.get("legacy_id") or ""),
                "name_cn": str(card.get("name_cn") or ""),
                "name_en": str(card.get("name_en") or ""),
                "type": str(card.get("card_type") or ""),
            }
            for key in (entry["legacy_id"], entry["short"], full_id):
                if key:
                    index.setdefault(key, entry)
    return index


def extract_demo_cards(limit: int = 14) -> list:
    """挑一批真实卡牌（含四语言文本）给编辑器线框图当样本数据。

    优先选带 ``[[icon:]]`` / ``[[card:]]`` 标记的卡，这样关键词着色、内联图标、
    内联卡牌 chip 三种渲染都能在预览里看到；再补几张纯文本卡。
    """

    cards = []
    for path in sorted(glob.glob(str(MODS / "*.gtnmod"))):
        try:
            with zipfile.ZipFile(path) as archive:
                payload = json.loads(archive.read("mod.json"))
                locales = {}
                for name in archive.namelist():
                    if name.startswith("locales/") and name.endswith(".json"):
                        locales[name.split("/")[-1].split(".")[0]] = json.loads(archive.read(name))
        except Exception:
            continue
        for card in (payload.get("registries") or {}).get("cards") or []:
            if not isinstance(card, dict):
                continue
            full_id = str(card.get("id") or "")
            if not full_id:
                continue
            entry = {
                "id": full_id,
                "legacy_id": str(card.get("legacy_id") or ""),
                "type": str(card.get("card_type") or ""),
                "cost_e": int(card.get("cost_e") or 0),
                "cost_m": int(card.get("cost_m") or 0),
                "count": int(card.get("count") or 1),
                "tags": [str(t) for t in (card.get("tags") or []) if isinstance(t, (str, int))],
                # 真实步骤树：编辑器把 on_play 的步骤还原成"效果行"，
                # 描述是这些行的产物（逻辑为源、描述为果）。
                "events": card.get("events") or {},
            }
            for lang in ("zh", "en", "fr", "ja"):
                localized = ((locales.get(lang) or {}).get("cards") or {}).get(full_id) or {}
                entry[lang] = {
                    "name": str(localized.get("name") or ""),
                    "text": str(localized.get("effect_text") or ""),
                    "flavor": str(localized.get("description") or ""),
                }
            text = entry["zh"]["text"] or entry["en"]["text"] or ""
            entry["_score"] = text.count("[[card:") * 10 + text.count("[[icon:") * 3
            cards.append(entry)

    cards.sort(key=lambda item: (-item["_score"], item["id"]))
    picked = cards[: max(1, limit - 3)] + [c for c in cards if c["_score"] == 0][:3]
    for entry in picked:
        entry.pop("_score", None)
    return picked


def extract_status_labels() -> dict:
    """各模组在 registries.statuses 里定义的状态名（含中文），例如 hel:luck → 幸运。

    卡面描述里不能出现内部 id，所以编辑器要把这些 id 翻成玩家看的词。
    """

    labels = {}
    for path in sorted(glob.glob(str(MODS / "*.gtnmod"))):
        try:
            with zipfile.ZipFile(path) as archive:
                payload = json.loads(archive.read("mod.json"))
        except Exception:
            continue
        for status in (payload.get("registries") or {}).get("statuses") or []:
            if not isinstance(status, dict):
                continue
            status_id = str(status.get("id") or "")
            label = str(status.get("name_cn") or status.get("label") or status.get("name_en") or "")
            if status_id and label:
                labels[status_id] = label
                labels.setdefault(status_id.split(":")[-1], label)
    return labels


def extract_tag_labels(js: str) -> dict:
    """标签 id → 中文（游戏 UI 表里的 flag_* 条目，例如 flag_exile: '放逐'）。"""

    labels = {}
    for match in re.finditer(r"flag_([a-z0-9_]+):\s*'([^']*)'", js):
        key, value = match.group(1), match.group(2)
        if not value or key in labels:
            continue
        # 四张语言表里只有中文表含汉字，用它当权威
        if re.search(r"[\u4e00-\u9fff]", value):
            labels[key] = value
    return labels


def _slice_block(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        return ""
    end = text.find(end_marker, start)
    if end < 0:
        return ""
    return text[start:end]


def _function_body(text: str, name: str) -> str:
    """取出 ``def name(...)`` 到下一个顶层 def 之间的源码。"""

    start = text.find(f"def {name}(")
    if start < 0:
        return ""
    end = text.find("\ndef ", start + 1)
    return text[start:end if end > 0 else len(text)]


def _returned_dict(body: str) -> str:
    """取出函数体里 ``return { ... }.get(...)`` 的字典部分。"""

    start = body.find("return {")
    if start < 0:
        return body
    end = body.find("}", start)
    return body[start:end] if end > start else body


def extract_status_catalog() -> tuple:
    """返回 ``(catalog, aliases)``。

    * ``catalog``：状态 id → 中文，编辑器下拉用（**存 id、显示中文**）；
    * ``aliases``：各种写法 → 规范 id（burn→fire、灼烧→fire…），导入老数据时归一用。

    来源：运行时的 ``_status_label``（id→中文）与 ``_builtin_status_attr``（别名→属性名），
    再加上官方包 ``registries.statuses``（``extract_status_labels``）。
    """

    catalog = {}
    aliases = {}
    runtime = ROOT / "mod_runtime_v2.py"
    if runtime.is_file():
        text = runtime.read_text(encoding="utf-8")
        body = _returned_dict(_function_body(text, "_status_label"))
        raw_labels = {key: value for key, value in re.findall(r'"([^"]+)":\s*"([^"]*)"', body) if value}
        alias_body = _returned_dict(_function_body(text, "_builtin_status_attr"))
        for source, target in re.findall(r'"([^"]+)":\s*"([^"]+)"', alias_body):
            if source == target:
                continue
            if target in raw_labels:
                aliases[source] = target
            # 别名不单独进下拉（burn/f/p/dizzy… 都归到 fire/poison/skip_turn）
            raw_labels.pop(source, None)
        catalog.update(raw_labels)
    # 官方包定义的状态不进下拉（编辑器会按当前草稿里的 registries.statuses 追加），
    # 只留别名关系：短 id → 带命名空间的 id。
    for key, value in extract_status_labels().items():
        if ":" in key:
            aliases.setdefault(key.split(":")[-1], key)
    # 中文写法也能被认出来（老草稿里可能直接存了"灼烧"）
    for key, value in list(catalog.items()):
        aliases.setdefault(value, key)
    # 去掉中文键与大小写重的条目，避免下拉里出现"邪眼=邪眼"这种重复
    catalog = {
        key: value for key, value in catalog.items()
        if not re.search(r"[\u4e00-\u9fff]", key) and key == key.lower()
    }
    # 同一个中文名只留第一个（status_immune=状态免疫 与 immune=状态免疫 这类）
    seen_labels = set()
    deduped = {}
    for key, value in catalog.items():
        if value in seen_labels:
            aliases.setdefault(key, next(k for k, v in catalog.items() if v == value))
            continue
        seen_labels.add(value)
        deduped[key] = value
    catalog = deduped
    aliases = {key: value for key, value in aliases.items() if key != value}
    return catalog, aliases


def _parse_map(block: str) -> dict:
    """解析 ``{ 'a': 'b', c: 'd' }`` 形式的映射。"""

    pairs = re.findall(r"(?:'([^']+)'|([A-Za-z_][A-Za-z0-9_]*))\s*:\s*'([^']*)'", block)
    return {(quoted or bare): value for quoted, bare, value in pairs}


def extract_token_rules(js: str) -> list:
    block = _slice_block(js, "const CARD_TEXT_TOKEN_RULES = [", "\n];")
    rules = []
    for match in re.finditer(
        r"\{\s*cls:\s*'([^']+)'\s*,\s*re:\s*/((?:\\.|[^/\\])*)/([a-z]*)", block
    ):
        rules.append({"cls": match.group(1), "source": match.group(2), "flags": match.group(3)})
    return rules


def extract_inline_icons(js: str) -> dict:
    block = _slice_block(js, "INLINE_ICON_DATA_URLS = {", "\n};")
    return dict(re.findall(r"'([^']+)':\s*'(data:[^']*)'", block))


def extract_function_map(js: str, function_name: str, map_name: str) -> dict:
    start = js.find(f"function {function_name}")
    if start < 0:
        return {}
    block = js[start:start + 4000]
    inner = _slice_block(block, f"{map_name} = {{", "};")
    return _parse_map(inner)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="抽取卡面关键词着色规则。")
    parser.add_argument("--game-js", default=str(GAME_JS))
    parser.add_argument("--out-dir", default=str(EDITOR))
    args = parser.parse_args(argv)

    game_js = pathlib.Path(args.game_js)
    if not game_js.is_file():
        print(f"找不到 game.js: {game_js}")
        return 2
    out_dir = pathlib.Path(args.out_dir)
    js = game_js.read_text(encoding="utf-8")

    status_catalog, status_aliases = extract_status_catalog()
    payload = {
        "tokenRules": extract_token_rules(js),
        "inlineIcons": extract_inline_icons(js),
        "uiIcons": extract_function_map(js, "getInlineIconUrl", "uiIcons"),
        "statusIcons": extract_function_map(js, "getInlineIconUrl", "statusIcons"),
        "iconClasses": extract_function_map(js, "getIconTokenClass", "map"),
        "tokenIconKeys": extract_function_map(js, "getCardTextTokenIconKey", "statusMap"),
        # 图标资源相对于本文件所在目录（生成物与 assets/ 同级）
        "assetBase": "assets/",
        "cardIndex": extract_card_index(),
        "demoCards": extract_demo_cards(),
        "statusLabels": extract_status_labels(),
        "statusCatalog": status_catalog,
        "statusAliases": status_aliases,
        "tagLabels": extract_tag_labels(js),
    }

    assets_src = ROOT / "static" / "assets"
    for folder in ("ui-icons", "status-icons"):
        source = assets_src / folder
        if source.is_dir():
            shutil.copytree(source, out_dir / "assets" / folder, dirs_exist_ok=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "card-text-rules.js"
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # 输出成 ES 模块：编辑器（Vite）和线框图（原生 module script）都能直接 import，
    # 避免"一份给 window、一份给打包器"的双份数据。
    target.write_text(
        "/* 从 Python联机版/static/js/game.js 与各官方包自动提取，\n"
        "   由 Python联机版/tools/extract_card_text_rules.py 生成。\n"
        "   游戏改版后重新运行脚本同步；不要手改。 */\n"
        f"export default {body};\n",
        encoding="utf-8",
    )
    print("token rules:", len(payload["tokenRules"]))
    print("inline icons:", len(payload["inlineIcons"]))
    print("ui icons:", len(payload["uiIcons"]), "| status icons:", len(payload["statusIcons"]))
    print("card index:", len(payload["cardIndex"]))
    print("demo cards:", len(payload["demoCards"]))
    print("status labels:", len(payload["statusLabels"]))
    print("status catalog:", len(payload["statusCatalog"]))
    print("status aliases:", len(payload["statusAliases"]))
    print("tag labels:", len(payload["tagLabels"]))
    print(f"written: {target} ({target.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
