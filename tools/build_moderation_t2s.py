#!/usr/bin/env python3
"""离线生成违禁词用的繁→简字符映射（static/data/moderation_t2s.json）。

只对词库里真正出现过的字生成映射，运行期零依赖。生成一次即可；
词库大改（换第三方词表、加大量繁体写法）后重跑：

    pip install --user zhconv
    python tools/build_moderation_t2s.py
"""

from __future__ import annotations

import json
from pathlib import Path

try:
    import zhconv
except ImportError:  # pragma: no cover - developer tool
    raise SystemExit('需要先安装 zhconv：pip install --user zhconv')


ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / 'static' / 'data' / 'moderation_rules.json'
MANUAL_PATH = ROOT / 'static' / 'data' / 'moderation_manual.json'
OUTPUT_PATH = ROOT / 'static' / 'data' / 'moderation_t2s.json'


def collect_terms() -> list[str]:
    terms: list[str] = []
    rules = json.loads(RULES_PATH.read_text(encoding='utf-8'))
    for rule in rules.get('rules') or []:
        if str(rule.get('type') or '') not in ('term_list', 'terms'):
            continue
        terms.extend(str(term) for term in rule.get('terms') or [] if term)
    manual = json.loads(MANUAL_PATH.read_text(encoding='utf-8'))
    for spec in (manual.get('categories') or {}).values():
        terms.extend(str(term) for term in spec.get('terms') or [] if term)
    return terms


def main() -> int:
    mapping: dict[str, str] = {}
    for term in collect_terms():
        traditional = zhconv.convert(term, 'zh-hant')
        if traditional == term:
            continue
        for source, target in zip(traditional, term):
            if source != target and source not in mapping:
                mapping[source] = target
    payload = {
        'schema_version': 1,
        'generated_by': 'tools/build_moderation_t2s.py',
        'source': 'zhconv zh-hant -> zh-hans，仅收录词库中出现的字',
        'map': dict(sorted(mapping.items())),
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    print(f'Wrote {OUTPUT_PATH} with {len(mapping)} char mappings')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
