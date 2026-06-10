"""Build GTN chat moderation rules from vendored third-party word lists.

This script is intentionally a build-time importer. The game server does not
depend on a third-party repository at runtime; it only reads the generated
static/data/moderation_rules.json file.
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THIRD_PARTY = ROOT / "third_party" / "moderation" / "sensitive-stop-words"
OUTPUT = ROOT / "static" / "data" / "moderation_rules.json"

ACTION_BY_LEVEL = {
    0: "allow",
    1: "allow_log",
    2: "allow_flag",
    3: "mask_flag",
    4: "reject_mute",
}

SOURCE_FILES = {
    "advertising": "广告.txt",
    "sexual": "色情类.txt",
    "weapon_explosive_illegal": "涉枪涉爆违法信息关键词.txt",
    "url_blacklist": "网址.txt",
    "political": "政治类.txt",
}

STOPWORD_FILENAME = "stopword.dic"


def normalize_term(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    kept = []
    for ch in value:
        category = unicodedata.category(ch)
        if category[0] in {"P", "Z", "C"}:
            continue
        kept.append(ch)
    value = "".join(kept)
    value = re.sub(r"(.)\1{2,}", r"\1\1", value)
    return value.strip()


def read_terms(path: Path) -> list[str]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8-sig", errors="ignore")
    parts = re.split(r"[\n\r,，]+", content)
    terms = []
    seen = set()
    for part in parts:
        term = part.strip().strip("\ufeff")
        if not term or term.startswith("#"):
            continue
        normalized = normalize_term(term)
        if len(normalized) < 2:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        terms.append(term)
    return terms


def read_domain_terms(path: Path) -> list[str]:
    terms = []
    seen = set()
    for term in read_terms(path):
        cleaned = term.strip().casefold()
        cleaned = re.sub(r"^https?://", "", cleaned)
        cleaned = cleaned.strip("/ \t\r\n")
        if len(cleaned) < 4:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        terms.append(cleaned)
    return terms


def card_allowlist() -> list[str]:
    values = {
        "Garden of Thorn",
        "Garden of Thorn 荆棘花园",
        "荆棘花园",
        "Stickerbug",
        "NetherDog",
        "Nether_Dog",
        "Eric",
        "46namknat",
        "WinniePooh",
        "CommonGoldIngot",
        "Thorn",
        "Bloom",
        "Root",
        "Guard",
        "Health",
        "Elixir",
        "Magic",
        "Damage",
        "Poison",
        "Fire",
        "Toxic",
        "Armor",
        "生命",
        "能量",
        "魔力",
        "伤害",
        "中毒",
        "灼烧",
        "淬毒",
        "护甲",
        "裂变",
        "聚变",
        "子瓣",
        "反制",
        "装备",
        "配装倾向",
    }
    sys.path.insert(0, str(ROOT))
    try:
        from card_i18n import CARD_I18N, LANGS, card_id_to_english  # type: ignore

        for card_id, entry in CARD_I18N.items():
            values.add(str(card_id))
            values.add(card_id_to_english(card_id))
            names = (entry or {}).get("name") or {}
            desc = (entry or {}).get("desc") or {}
            effect = (entry or {}).get("effect") or {}
            for lang in LANGS:
                if names.get(lang):
                    values.add(str(names[lang]))
            # Keep only short project-specific snippets from desc/effect to avoid
            # adding general natural language to the allowlist.
            for text in [desc.get("zh"), effect.get("zh"), effect.get("en")]:
                if isinstance(text, str):
                    for token in re.split(r"[\s,，;；。:：()（）]+", text):
                        if 2 <= len(normalize_term(token)) <= 16:
                            values.add(token)
    except Exception:
        pass
    return sorted({item for item in values if normalize_term(item)})


def manual_severe_sexual_terms(sexual_terms: list[str]) -> list[str]:
    severe_needles = {
        "幼女",
        "幼交",
        "强奸",
        "迷奸",
        "轮奸",
        "儿童色情",
        "未成年",
    }
    selected = []
    seen = set()
    for term in sexual_terms:
        normalized = normalize_term(term)
        if any(normalize_term(needle) in normalized for needle in severe_needles):
            if normalized not in seen:
                selected.append(term)
                seen.add(normalized)
    for needle in severe_needles:
        normalized = normalize_term(needle)
        if normalized not in seen:
            selected.append(needle)
            seen.add(normalized)
    return selected


def rule(rule_id: str, *, level: int, category: str, rtype: str = "term_list",
         target: str = "normalized", terms: list[str] | None = None,
         pattern: str | None = None, source: str = "gtn") -> dict:
    data = {
        "id": rule_id,
        "category": category,
        "type": rtype,
        "target": target,
        "level": level,
        "action": ACTION_BY_LEVEL[level],
        "source": source,
    }
    if terms is not None:
        data["terms"] = terms
    if pattern is not None:
        data["pattern"] = pattern
    return data


def build_rules() -> dict:
    missing = []
    source_paths = {key: THIRD_PARTY / filename for key, filename in SOURCE_FILES.items()}
    for key, path in source_paths.items():
        if not path.exists():
            missing.append(str(path))
    if missing:
        raise FileNotFoundError("Missing third-party moderation files: " + ", ".join(missing))
    stopword_path = THIRD_PARTY / STOPWORD_FILENAME

    ad_terms = read_terms(source_paths["advertising"])
    sexual_terms = read_terms(source_paths["sexual"])
    illegal_weapon_terms = read_terms(source_paths["weapon_explosive_illegal"])
    url_terms = read_domain_terms(source_paths["url_blacklist"])
    political_terms = read_terms(source_paths["political"])
    severe_sexual_terms = manual_severe_sexual_terms(sexual_terms)

    rules = [
        rule("builtin.xss_tag", category="security", rtype="regex", target="raw", level=3,
             pattern=r"<\s*/?\s*(script|iframe|object|embed|svg)\b[^>]*>"),
        rule("builtin.xss_js_url", category="security", rtype="regex", target="raw", level=3,
             pattern=r"javascript\s*:"),
        rule("builtin.massive_mentions", category="spam", rtype="regex", target="raw", level=4,
             pattern=r"(@\S+\s*){8,}"),
        rule("builtin.repeated_chars", category="spam", rtype="regex", target="raw", level=1,
             pattern=r"(.)(\1){9,}"),
        rule("builtin.generic_url", category="url", rtype="regex", target="raw", level=2,
             pattern=r"(https?://|www\.)\S{8,}"),
        rule("builtin.contact_hint", category="privacy", rtype="regex", target="raw", level=2,
             pattern=r"(qq|vx|微信|手机号)\s*[:：]?\s*[0-9A-Za-z_\-]{5,}"),
        rule("builtin.trade_contact_pattern", category="advertising", rtype="regex", target="raw", level=3,
             pattern=r"(外挂|代练|交易|收号|卖号|群|加群|联系方式).{0,16}(qq|vx|微信|q群|群号|手机号|http|www)"),
        rule("third_party.advertising", category="advertising", level=2, terms=ad_terms,
             source="fwwdn/sensitive-stop-words:广告.txt"),
        rule("third_party.sexual", category="sexual", level=2, terms=sexual_terms,
             source="fwwdn/sensitive-stop-words:色情类.txt"),
        rule("manual.sexual_severe", category="sexual", level=4, terms=severe_sexual_terms,
             source="GTN manually maintained severe subset"),
        rule("third_party.weapon_explosive_illegal", category="illegal_goods", level=4,
             terms=illegal_weapon_terms, source="fwwdn/sensitive-stop-words:涉枪涉爆违法信息关键词.txt"),
        rule("third_party.url_blacklist", category="url", rtype="domain_list", target="raw", level=2,
             terms=url_terms, source="fwwdn/sensitive-stop-words:网址.txt"),
        rule("third_party.political_log_only", category="political", level=1, terms=political_terms,
             source="fwwdn/sensitive-stop-words:政治类.txt"),
    ]

    return {
        "schema_version": 1,
        "generated_by": "scripts/build_moderation_rules.py",
        "source": {
            "name": "fwwdn/sensitive-stop-words",
            "url": "https://github.com/fwwdn/sensitive-stop-words",
            "license": "Apache-2.0",
            "local_path": str(THIRD_PARTY.relative_to(ROOT)).replace(os.sep, "/"),
            "excluded_files": [str(stopword_path.relative_to(ROOT)).replace(os.sep, "/")],
        },
        "actions": ACTION_BY_LEVEL,
        "policy": {
            "level_0": "allow",
            "level_1": "allow_log",
            "level_2": "allow_flag",
            "level_3": "mask_flag",
            "level_4": "reject_mute",
            "notes": [
                "广告、色情、网址默认只标记或打码，不全量拦截。",
                "政治类默认 level 1，仅后台记录。",
                "stopword.dic 不作为敏感词导入。",
            ],
        },
        "allowlist": card_allowlist(),
        "rules": rules,
        "reject_rules": [],
    }


def main() -> int:
    data = build_rules()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    counts = {
        rule_item["id"]: len(rule_item.get("terms") or [])
        for rule_item in data["rules"]
        if "terms" in rule_item
    }
    print(f"Wrote {OUTPUT}")
    print(json.dumps(counts, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
