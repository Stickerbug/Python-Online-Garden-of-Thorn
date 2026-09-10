# -*- coding: utf-8 -*-
"""Apply the All Cards balance pass from development workbook 14.

The workbook is description-authoritative. This script updates package card
metadata and embedded locale text by stable card name. Runtime behavior is
implemented separately in the engine atoms.
"""

from __future__ import annotations

import copy
import html
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from sync_mod_locales import _mask_markup, _polish_english, _restore_markup  # noqa: E402


TYPE_MAP = {"T": "thorn", "B": "bloom", "R": "root", "G": "guard"}


# Only fields that actually changed in workbook 14 are listed here.
CARD_PATCHES = {
    "Coffee": {
        "effect_text": "回复目标2[[icon:E]]；本牌获得1层沉重",
    },
    "Heavy": {
        "effect_text": "对目标造成36[[icon:D]]；使自己获得1层眩晕",
    },
    "Shovel": {
        "cost_e": 3,
        "effect_text": "使自己获得1层无法选中；结束你的回合",
    },
    "Missile": {
        "cost_e": 3,
        "effect_text": "对攻击者造成12[[icon:D]]；抽1张牌  响应：被作为攻击牌目标",
    },
    "Antennae": {"cost_e": 1},
    "Faster": {"cost_e": 1},
    "Soil": {
        "effect_text": "使目标[[icon:H]]上限+40，回复目标40[[icon:H]]；向目标抽牌堆加入5张灰尘",
    },
    "Coal": {
        "effect_text": "对目标造成(8+2×自己[[icon:F]]层数)[[icon:D]]",
    },
    "Magic Antennae": {
        "cost_m": 1,
        "effect_text": "向自己展示一次目标本局初始牌组中的所有牌；抽1张牌",
    },
    "Cat Ears": {"cost_e": 1},
    "Grass": {
        "effect_text": "可花费1[[icon:E]]，触发：回复目标6[[icon:H]]；每回合至多触发1次",
    },
    "Mecha Antennae": {
        "effect_text": (
            "选择一种类型，使目标所有区域的该类型牌获得被揭示；"
            "从自己抽牌堆顶展示3张牌，选择1张加入自己手中，其余置入自己弃牌堆"
        ),
    },
    "Goggles": {"cost_e": 0},
    "Ankh": {
        "effect_text": (
            "使所有玩家的[[icon:H]]、[[icon:E]]、[[icon:M]]回到各自对局开始时的数值；"
            "已阵亡玩家以死亡时的位置、状态、手牌和牌堆复活；然后自己-2[[icon:E]]"
        ),
    },
    "Magnet": {
        "effect_text": "造成2[[icon:electric_damage]]；展示目标所有手牌，从目标手牌中选择1张加入自己手牌",
    },
    "Wind": {
        "flags": ["infinite_exclude"],
        "effect_text": "目标下回合的回合开始抽牌结算后，丢弃全场所有[[icon:E]]消耗不超过本次实际花费+1的手牌",
    },
    "Salt": {
        "effect_text": "对攻击者造成向上取整(本牌所响应攻击的首次伤害×60%)[[icon:D]]  响应：被作为攻击牌目标",
    },
    "Dizzy": {
        "effect_text": "装备时和目标回合开始时，使目标获得1层失明；每张装备在目标上的眩晕使其造成的伤害+50%",
    },
    "Marble": {
        "effect_text": (
            "对目标造成9[[icon:D]]；前述伤害每次造成实际伤害时，"
            "随机对除目标外另一名可选中玩家造成23[[icon:D]]"
        ),
    },
    "Citron": {
        "effect_text": "存在期间，目标打出攻击牌前，使该牌暂时获得精准；若该牌已有精准，则改为暂时获得隐匿",
    },
    "Magic Bur": {
        "effect_text": "对攻击者施加向上取整(本次将受伤害/4)层易损  响应：被作为攻击牌目标",
    },
    "Magic Rubber": {
        "effect_text": "使自己手中[[icon:E]]花费最高的一张牌获得暂时迅捷3  响应：被作为攻击牌目标",
    },
    "Rubber": {
        "effect_text": "攻击者本次攻击结算后，使其手中所有牌获得暂时沉重1  响应：被作为攻击牌目标",
    },
    "Dead Leaf": {
        "effect_text": "对目标造成6[[icon:D]]；若目标手中没有反制牌，则对目标施加1层迟缓",
    },
    "Magic Pearl": {
        "flags": ["exile", "sprout"],
        "effect_text": (
            "对目标造成5[[icon:D]]；进入手牌时获得2层威力；"
            "自己回合开始时，若目标可选中且费用满足，"
            "自动对血量最低的可选中敌方玩家打出一张具有魔力迅捷3且不触发此效果的放逐复制"
        ),
    },
    "Magic Trident": {
        "effect_text": "对目标造成18[[icon:D]]；此牌在手牌中时，自己每抽1张牌，此牌获得1层威力",
    },
    "Hot Water": {"card_type": "thorn"},
    "Ink": {"cost_e": 0},
    "Needle": {
        "card_type": "thorn",
        "effect_text": "对目标造成4[[icon:D]]；命中时，对目标施加1层无法反制",
    },
    "Bubble Bomb": {
        "effect_text": "使攻击者无法行动直到其下回合开始，并对其施加1层眩晕  响应：被作为攻击牌目标",
    },
    "Cucumber": {
        "cost_e": 2,
        "flags": ["exile"],
    },
    "Nitro": {
        "effect_text": "使所响应的牌失效，并使其在本次结算后进入放逐区  响应：敌方对自己使用牌",
    },
    "Sponge": {"cost_e": 3},
    "Void": {"cost_e": 99, "cost_m": 99},
    "Magic Antimatter": {
        "effect_text": "所响应的牌生效前，对除自己以外的所有可选中玩家造成25[[icon:D]]  响应：非自己回合将受到致命伤害",
    },
    "Illuminati Triangle": {
        "effect_text": (
            "回复目标20[[icon:H]]，并对目标施加所有类型的状态（除状态免疫和不可选中）；"
            "目标下回合结束时，清除其所有状态"
        ),
    },
    "Copper Rod": {
        "effect_text": "免受所响应攻击牌的伤害，改为将伤害量向上取整平分为自己所有手牌的电荷。  响应：被作为攻击牌目标",
    },
    "Horn": {
        "effect_text": "对所有敌方目标造成10[[icon:D]]，不使所响应伤害失效  响应：自己将受到无来源或来源为自己的伤害",
    },
    "Domino": {
        "effect_text": "使自己获得2层幸运；对目标造成6[[icon:D]]；若本次伤害即将暴击，本次获得暂时精准且最终伤害×2",
    },
    "Blood Dice": {
        "cost_e": 1,
        "flags": ["self_target"],
        "effect_text": "对目标造成6[[icon:D]]，使目标获得10层幸运；本次伤害必定暴击且不消耗幸运",
    },
    "Lava": {"cost_e": 0},
    "Magic Fire": {"cost_m": 4},
    "Bugatti": {
        "cost_e": 1,
        "flags": ["infinite_exclude", "unique"],
        "effect_text": "装备存在时，目标手牌上限-2；目标回合开始正常抽牌后，抽至其手牌上限",
    },
    "Clover": {
        "effect_text": "目标回合开始时，使目标获得4层幸运",
    },
    "Magic Clover": {
        "cost_m": 6,
        "card_type": "bloom",
        "effect_text": "使目标本回合暴击倍率+1×并获得8层幸运",
    },
    "Broccoli": {
        "effect_text": "对目标造成10[[icon:D]]；若此牌被反制，则对目标额外造成3[[icon:D]]×2",
    },
    "Clay": {
        "effect_text": (
            "对目标造成5[[icon:D]]；此牌在手牌中时，自己每受到6点实际伤害，"
            "此牌获得1层威力，最多以此方式获得18层威力"
        ),
    },
    "Light Bulb": {"flags": ["self_only", "team_limited"]},
    "Lotus": {
        "effect_text": (
            "回复目标10[[icon:H]]；目标每有1层[[icon:P]]，改为少回复1[[icon:H]]"
            "并移除1层[[icon:P]]，重复至目标没有[[icon:P]]"
        ),
    },
    "Chitin": {
        "cost_e": 2,
        "effect_text": (
            "目标回合开始时，若目标没有邪眼，则对目标施加1层邪眼；"
            "本装备被摧毁时，清除装备目标的所有邪眼"
        ),
    },
    "Blueberries": {
        "cost_e": 3,
        "effect_text": "对目标造成1[[icon:D]]×4（4子瓣）；每次造成伤害时，对目标施加3层霜冻",
    },
    "Icicle": {
        "effect_text": "对目标造成6[[icon:D]]；造成伤害时，对目标施加3层霜冻；将1张冰锥洗入自己弃牌堆",
    },
    "Magic Cryo Bomb": {
        "card_type": "bloom",
        "flags": ["rebound", "wide_strike"],
    },
    "Nuke": {"cost_e": 0},
    "Ruby": {
        "effect_text": (
            "选择自己手牌中1张可支付实际消耗的攻击牌；支付其[[icon:E]]和[[icon:M]]"
            "实际消耗的1/2（分别向上取整），使其聚变层数+1并获得被揭示；"
            "无法支付时不能选择该牌"
        ),
    },
    "Blood Diamond": {
        "effect_text": "对目标造成3[[icon:D]]×4（4子瓣）；每次造成实际伤害时，对目标施加1层流血",
    },
    "Sugar": {
        "effect_text": "对目标造成2[[icon:D]]×6（6子瓣）；回复目标20[[icon:H]]",
    },
    "Blood Chromosome": {
        "effect_text": (
            "从自己弃牌堆随机将1张牌加入手中，并使其获得共生，然后对自己造成2[[icon:D]]；"
            "重复此过程，直至手牌已满或弃牌堆为空。结算完成后，若自己的[[icon:H]]≤0，再进行死亡结算"
        ),
    },
    "Ransom Money": {
        "effect_text": "选择自己放逐区中1张牌，将其加入弃牌堆",
    },
    "Indictment": {
        "effect_text": "将所响应攻击牌每次造成的物理伤害和电伤分别转化为等量护盾  响应：被作为攻击牌目标",
    },
    "DNA": {"cost_e": 3},
}


MOVES = {
    "Blood Sugar": "Bio Cards Addition.gtnmod",
    "RNA": "Bio Cards Addition.gtnmod",
    "Magic RNA": "Bio Cards Addition.gtnmod",
}


def main_member(zf):
    names = {name.lower(): name for name in zf.namelist()}
    for candidate in ("mod.json", "gtnmod.json"):
        if candidate in names:
            return names[candidate]
    raise ValueError("package has no mod.json")


def read_package(path):
    import zipfile

    with zipfile.ZipFile(path, "r") as zf:
        main = main_member(zf)
        data = json.loads(zf.read(main).decode("utf-8-sig"))
        members = {item.filename: zf.read(item.filename) for item in zf.infolist()}
    locales = {}
    for lang in ("zh", "en", "fr", "ja"):
        member = f"locales/{lang}.json"
        if member in members:
            locales[lang] = json.loads(members[member].decode("utf-8-sig"))
    return data, members, locales


def write_package(path, data, members, locales):
    import zipfile

    main = "mod.json"
    if "mod.json" not in members and "gtnmod.json" in members:
        main = "gtnmod.json"
    members = dict(members)
    members[main] = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    for lang, document in locales.items():
        members[f"locales/{lang}.json"] = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
    handle, temp_name = tempfile.mkstemp(suffix=".gtnmod", dir=str(path.parent))
    os.close(handle)
    temp_path = pathlib.Path(temp_name)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for filename, content in members.items():
                zf.writestr(filename, content)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def find_card(data, name):
    for card in data.get("registries", {}).get("cards", []) or []:
        if str(card.get("name_en") or "") == name or str(card.get("legacy_id") or "") == name:
            return card
    return None


def card_id(card):
    return str(card.get("id") or card.get("legacy_id") or card.get("name_en") or "")


def translate_field(text, lang, cache):
    key = (lang, text)
    if key in cache:
        return cache[key]
    masked, markup = _mask_markup(text)
    query = urllib.parse.urlencode({
        "q": masked,
        "langpair": f"zh-CN|{lang}",
    })
    url = f"https://api.mymemory.translated.net/get?{query}"
    value = ""
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "GTN locale builder/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            value = html.unescape(str(payload.get("responseData", {}).get("translatedText") or ""))
            break
        except Exception:
            if attempt + 1 >= 3:
                value = ""
            else:
                time.sleep(1.0 + attempt)
    if not value:
        value = text
    value = _restore_markup(value, markup)
    if lang == "en":
        value = _polish_english(value)
    cache[key] = value
    return value


def patch_locale(locales, card, effect_text, translate_cache):
    rid = card_id(card)
    for lang in ("zh", "en", "fr", "ja"):
        document = locales.get(lang)
        if not isinstance(document, dict):
            continue
        entry = (document.setdefault("cards", {})).setdefault(rid, {})
        if lang == "zh":
            entry["effect_text"] = effect_text
        else:
            previous = str(entry.get("effect_text") or "")
            translated = translate_field(effect_text, lang, translate_cache)
            if translated:
                entry["effect_text"] = translated
            elif previous:
                entry["effect_text"] = previous


def move_locale_entry(locales, rid, source_doc, target_doc):
    for lang in ("zh", "en", "fr", "ja"):
        source = locales.languages.get(lang)
        if not isinstance(source, dict):
            continue
        entry = (source.get("cards") or {}).pop(rid, None)
        if entry is not None:
            target = target_doc.setdefault("cards", {}).setdefault(rid, {})
            target.clear()
            target.update(entry)


def main():
    packages = {}
    for path in sorted(MODS.glob("*.gtnmod")):
        data, members, locales = read_package(path)
        packages[path.name] = {
            "path": path,
            "data": data,
            "members": members,
            "locales": locales,
        }

    by_name = {}
    for package in packages.values():
        for card in package["data"].get("registries", {}).get("cards", []) or []:
            by_name[str(card.get("name_en") or card.get("legacy_id") or card.get("id") or "")] = (package, card)

    translate_cache = {}
    for name, patch in CARD_PATCHES.items():
        found = by_name.get(name)
        if not found:
            print(f"MISSING {name}")
            continue
        package, card = found
        old_effect = str(card.get("effect_text") or "")
        for field, value in patch.items():
            if field == "card_type" and value in TYPE_MAP:
                value = TYPE_MAP[value]
            card[field] = copy.deepcopy(value)
            if field == "flags":
                # The loader merges both legacy tags and flags. Keep the new
                # canonical list in both places so removed legacy aliases do
                # not survive a package reload.
                card["tags"] = copy.deepcopy(value)
        new_effect = str(card.get("effect_text") or old_effect)
        if new_effect != old_effect:
            patch_locale(package["locales"], card, new_effect, translate_cache)

    # Move the three intentionally reclassified Bio cards.
    source_name = "Bio Cards Addition.gtnmod"
    target_name = "Bio Cards DLC.gtnmod"
    source = packages[source_name]
    target = packages[target_name]
    for name in ("Blood Sugar", "RNA", "Magic RNA"):
        found = by_name.get(name)
        if not found:
            print(f"MOVE MISSING {name}")
            continue
        card = found[1]
        rid = card_id(card)
        if card in target["data"]["registries"]["cards"]:
            continue
        if card not in source["data"]["registries"]["cards"]:
            print(f"MOVE SKIPPED {name}")
            continue
        source["data"]["registries"]["cards"].remove(card)
        target["data"]["registries"]["cards"].append(copy.deepcopy(card))
        assets = card.get("assets") if isinstance(card.get("assets"), dict) else {}
        for key in ("image", "upgraded_image"):
            member = str(assets.get(key) or "").strip()
            if not member:
                continue
            if member in source["members"]:
                target["members"].setdefault(member, source["members"][member])
        for lang in ("zh", "en", "fr", "ja"):
            entry = (source["locales"].get(lang, {}).get("cards") or {}).pop(rid, None)
            if entry is not None:
                target["locales"].setdefault(lang, {}).setdefault("cards", {})[rid] = entry

    for name, package in packages.items():
        write_package(package["path"], package["data"], package["members"], package["locales"])
        print("updated", name)


if __name__ == "__main__":
    main()
