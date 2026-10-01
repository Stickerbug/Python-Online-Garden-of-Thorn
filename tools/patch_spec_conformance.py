# -*- coding: utf-8 -*-
"""描述规范一致性补丁（2026-10-01，对照 docs/卡牌描述规范.md）：
- 触发句式统一：若已装备一回合 → 已装备1回合时（规范9.1/2.2 阿拉伯数字+"时"）
- 黄金叶换标准模板（费用不再藏括号，规范2.2）
- formal_logic:mp「装备1回合后可触发」→「已装备1回合时，可触发」
- 自身→自己（规范2.1.1）
- 对自己施加状态→使自己获得（规范2.1.1）
中文权威；en/fr/ja 语义一致不动（黄金叶 zh 换模板后费用语义不变）。
"""
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODS = ROOT / 'mods'

PATCHES = {
    'Leaf': {'zh': [('若已装备一回合，可花费1[[icon:E]]，触发：', '已装备1回合时，可花费1[[icon:E]]，触发：')]},
    'Mark': {'zh': [('若已装备一回合，可花费0[[icon:E]]，触发：', '已装备1回合时，可花费0[[icon:E]]，触发：')]},
    'StemCell': {'zh': [('若已装备一回合，可花费6[[icon:M]]，触发：', '已装备1回合时，可花费6[[icon:M]]，触发：')]},
    'Mine': {'zh': [('若已装备一回合，可花费0[[icon:E]]，触发：', '已装备1回合时，可花费0[[icon:E]]，触发：')]},
    'GoldenLeaf': {'zh': [('已装备一回合可触发（0[[icon:E]]）：', '已装备1回合时，可花费0[[icon:E]]，触发：')]},
    'formal_logic:mp': {'zh': [('装备1回合后可触发：', '已装备1回合时，可触发：')]},
    'Yggdrasil': {'zh': [('自身受到致命伤害时，将自身[[icon:H]]设为5', '自己受到致命伤害时，将自己[[icon:H]]设为5')]},
    'GoldenNazar': {'zh': [('所有自身装备获得', '所有自己的装备获得'), ('响应：自身装备即将被摧毁', '响应：自己的装备即将被摧毁')]},
    'MagicHeavy': {'zh': [('对自己施加1层眩晕', '使自己获得1层眩晕')]},
    'MagicSlimeBall': {'zh': [('对自己施加1层迟缓', '使自己获得1层迟缓')]},
    'MagicBloodScythe': {'zh': [('对自己施加3层[[icon:F]]、霜冻和[[icon:P]]', '使自己获得3层[[icon:F]]、霜冻和[[icon:P]]')]},
}


def patch():
    for path in sorted(MODS.glob('*.gtnmod')):
        with zipfile.ZipFile(path) as z:
            entries = {n: z.read(n) for n in z.namelist()}
        mod_data = json.loads(entries['mod.json'].decode('utf-8'))
        cards = (mod_data.get('registries') or {}).get('cards', [])
        card_ids = {c.get('legacy_id') or c.get('id') for c in cards}
        if not any(cid in card_ids for cid in PATCHES):
            continue
        backup = path.with_suffix('.gtnmod.bak-spec')
        shutil.copy2(path, backup)
        total = 0
        for card in cards:
            legacy = card.get('legacy_id') or card.get('id')
            langs = PATCHES.get(legacy)
            if not langs:
                continue
            for lang, pairs in langs.items():
                for field in ('effect_text', 'effect_text_cn'):
                    if field in card and card[field]:
                        for old, new in pairs:
                            if old in card[field]:
                                card[field] = card[field].replace(old, new)
                                total += 1
                i18n = card.get('effect_text_i18n')
                if isinstance(i18n, dict) and i18n.get(lang):
                    for old, new in pairs:
                        if old in i18n[lang]:
                            i18n[lang] = i18n[lang].replace(old, new)
                            total += 1
        entries['mod.json'] = json.dumps(mod_data, ensure_ascii=False, indent=1).encode('utf-8')
        for lang in ('zh',):
            key = f'locales/{lang}.json'
            if key in entries:
                loc = json.loads(entries[key].decode('utf-8'))
                ns = loc.get('cards') or {}
                for card in cards:
                    legacy = card.get('legacy_id') or card.get('id')
                    langs = PATCHES.get(legacy)
                    entry = ns.get(card.get('id'))
                    if not langs or not isinstance(entry, dict) or not entry.get('effect_text'):
                        continue
                    for old, new in langs.get(lang, []):
                        if old in entry['effect_text']:
                            entry['effect_text'] = entry['effect_text'].replace(old, new)
                            total += 1
                entries[key] = json.dumps(loc, ensure_ascii=False, indent=2).encode('utf-8')
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, blob in entries.items():
                z.writestr(name, blob)
        print(f'{path.name}: {total} replacements')
        if total == 0:
            shutil.copy2(backup, path)
            print('  WARNING: no replacements, restored')


if __name__ == '__main__':
    patch()
