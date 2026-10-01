# -*- coding: utf-8 -*-
"""双加数体系（设计 2026-10-01）卡牌文本同步补丁。

- 普通卡的「威力」状态获得 → 「暂时威力」（四语言）
- 珊瑚/血钻石：删除「此牌打出后不减少裂变层数」句（由「不灭：裂变」标签芯片承担）
- 绿石竹（jungle:dianthus，带 amplify=不灭：威力）不改——其「威力」即永久加数语义

规则：卡名中英不可变；中文权威；effect_text/内联/locales 四语言一起同步；无尾句号。
"""
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODS = ROOT / 'mods'

# (mod 文件, 卡 id, 语言) -> [(旧子串, 新子串), ...]
PATCHES = {
    ('Bio Cards Addition.gtnmod', 'bio:blood_diamond'): {
        'zh': [('；此牌打出后不减少裂变层数', '')],
        'en': [('; playing this card does not reduce its fission', '')],
        'fr': [(' ; jouer cette carte ne réduit pas sa fission', '')],
        'ja': [('。このカードをプレイしても裂変は減少しない', '')],
    },
    ('Jungle Cards Addition.gtnmod', 'jungle:magic_tomato'): {
        'zh': [('此牌威力+2', '此牌暂时威力+2')],
        'en': [('the power of this card will be +2', 'the Temporary Power of this card will be +2')],
        'fr': [('la puissance de cette carte sera de +2', 'la Puissance temporaire de cette carte sera de +2')],
        'ja': [('このカードのパワーは+2される', 'このカードの一時威力は+2される')],
    },
    ('Jungle Cards Addition.gtnmod', 'jungle:tomato'): {
        'zh': [('此牌获得威力3', '此牌获得3层暂时威力')],
        'en': [('this card will gain power 3', 'this card will gain 3 Temporary Power')],
        'fr': [('cette carte gagnera en puissance 3', 'cette carte gagnera 3 Puissance temporaire')],
        'ja': [('このカードのパワーを３し', 'このカードの一時威力を３得')],
    },
    ('Jurassic Cards Addition.gtnmod', 'jurassic:crystal_leaf'): {
        'zh': [('获得2层威力', '获得2层暂时威力')],
        'en': [('gain 2 Power', 'gain 2 Temporary Power')],
        'fr': [('gagnent 2 Puissance', 'gagnent 2 Puissance temporaire')],
        'ja': [('威力を2得る', '一時威力を2得る')],
    },
    ('Jurassic Cards Addition.gtnmod', 'jurassic:magic_crystal_leaf'): {
        'zh': [('获得8层威力', '获得8层暂时威力')],
        'en': [('gain 8 Power', 'gain 8 Temporary Power')],
        'fr': [('gagnent 8 Puissance', 'gagnent 8 Puissance temporaire')],
        'ja': [('威力を8得る', '一時威力を8得る')],
    },
    ('Jurassic Cards Addition.gtnmod', 'jurassic:amber'): {
        'zh': [('清空此牌威力', '清空此牌暂时威力'), ('失去3层威力', '失去3层暂时威力'), ('此牌威力≤-12', '此牌暂时威力≤-12')],
        'en': [('clear its Power', 'clear its Temporary Power'), ('loses 3 Power', 'loses 3 Temporary Power'), ('at -12 Power or lower', 'at -12 Temporary Power or lower')],
        'fr': [('réinitialise sa Puissance', 'réinitialise sa Puissance temporaire'), ('perd 3 Puissance', 'perd 3 Puissance temporaire'), ('à -12 Puissance ou moins', 'à -12 Puissance temporaire ou moins')],
        'ja': [('このカードの威力を0にする', 'このカードの一時威力を0にする'), ('威力を3失い', '一時威力を3失い'), ('威力が-12以下', '一時威力が-12以下')],
    },
    ('Jurassic Cards Addition.gtnmod', 'jurassic:amulet'): {
        'zh': [('获得5层威力', '获得5层暂时威力')],
        'en': [('gain 5 Power', 'gain 5 Temporary Power')],
        'fr': [('gagnent 5 Puissance', 'gagnent 5 Puissance temporaire')],
        'ja': [('威力を5得る', '一時威力を5得る')],
    },
    ('Ocean Cards Addition.gtnmod', 'ocean:magic_trident'): {
        'zh': [('获得1层威力', '获得1层暂时威力')],
        'en': [('gains 1 Power', 'gains 1 Temporary Power')],
        'fr': [('gagne 1 Puissance', 'gagne 1 Puissance temporaire')],
        'ja': [('威力を1獲得する', '一時威力を1獲得する')],
    },
    ('Ocean Cards Addition.gtnmod', 'ocean:coral'): {
        'zh': [('；此牌打出后不减少裂变层数', '')],
        'en': [('; playing this card does not reduce its fission stacks', '')],
        'fr': [(' ; jouer cette carte ne réduit pas ses couches de fission', '')],
        'ja': [('。このカードをプレイしても裂変の層数は減少しない', '')],
    },
    ('Sewers Cards Addition.gtnmod', 'sewers:clay'): {
        'zh': [('获得1层威力，最多以此方式获得18层威力', '获得1层暂时威力，最多以此方式获得18层暂时威力')],
        'en': [('gains 1 Power for every 6 actual damage you take, up to 18 Power gained this way', 'gains 1 Temporary Power for every 6 actual damage you take, up to 18 Temporary Power gained this way')],
        'fr': [('gagne 1 Puissance pour chaque 6 dégâts réels que vous subissez, jusqu\'à 18 Puissance obtenues ainsi', 'gagne 1 Puissance temporaire pour chaque 6 dégâts réels que vous subissez, jusqu\'à 18 Puissance temporaire obtenues ainsi')],
        'ja': [('威力を1獲得する（この方法で最大18層）', '一時威力を1獲得する（この方法で最大18層）')],
    },
    ('Sewers Cards DLC.gtnmod', 'sewers:toilet_paper'): {
        'zh': [('获得1层威力（因本效果至多获得24层）', '获得1层暂时威力（因本效果至多获得24层）')],
        'en': [('gains 1 Power (up to 24 Power from this effect)', 'gains 1 Temporary Power (up to 24 Temporary Power from this effect)')],
        'fr': [('gagne 1 Puissance (jusqu\'à 24 grâce à cet effet)', 'gagne 1 Puissance temporaire (jusqu\'à 24 grâce à cet effet)')],
        'ja': [('威力を1得る（この効果では最大24）', '一時威力を1得る（この効果では最大24）')],
    },
    ('Vanilla Cards.gtnmod', 'vanilla:triangle'): {
        'zh': [('+1威力', '+1暂时威力')],
        'en': [('gain +1 Power', 'gain +1 Temporary Power')],
        'fr': [('gagnent +1 Puissance', 'gagnent +1 Puissance temporaire')],
        'ja': [('威力+1を得る', '一時威力+1を得る')],
    },
}

LANG_FIELDS = {
    'zh': ('effect_text', 'effect_text_cn'),
    'en': ('effect_text_en',),
}


def apply_to_text(text, pairs):
    changed = 0
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new)
            changed += 1
    return text, changed


def patch():
    by_mod = {}
    for (mod, cid), langs in PATCHES.items():
        by_mod.setdefault(mod, {})[cid] = langs
    for mod_name, cards in by_mod.items():
        path = MODS / mod_name
        backup = path.with_suffix('.gtnmod.bak-dual')
        shutil.copy2(path, backup)
        with zipfile.ZipFile(path) as z:
            entries = {n: z.read(n) for n in z.namelist()}
        mod_data = json.loads(entries['mod.json'].decode('utf-8'))
        total = 0
        for card in (mod_data.get('registries') or {}).get('cards', []):
            langs = cards.get(card.get('id'))
            if not langs:
                continue
            for lang, pairs in langs.items():
                fields = list(LANG_FIELDS.get(lang, ())) + ['effect_text']
                for field in fields:
                    if field in card and card[field]:
                        card[field], n = apply_to_text(card[field], pairs)
                        total += n
                i18n = card.get('effect_text_i18n')
                if isinstance(i18n, dict) and i18n.get(lang):
                    i18n[lang], n = apply_to_text(i18n[lang], pairs)
                    total += n
        entries['mod.json'] = json.dumps(mod_data, ensure_ascii=False, indent=1).encode('utf-8')
        for lang in ('zh', 'en', 'fr', 'ja'):
            key = f'locales/{lang}.json'
            if key not in entries:
                continue
            loc = json.loads(entries[key].decode('utf-8'))
            ns = loc.get('cards') or {}
            for cid, langs in cards.items():
                pairs = langs.get(lang)
                entry = ns.get(cid)
                if not pairs or not isinstance(entry, dict) or not entry.get('effect_text'):
                    continue
                entry['effect_text'], n = apply_to_text(entry['effect_text'], pairs)
                total += n
            entries[key] = json.dumps(loc, ensure_ascii=False, indent=2).encode('utf-8')
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, blob in entries.items():
                z.writestr(name, blob)
        print(f'{mod_name}: {total} replacements')
        if total == 0:
            shutil.copy2(backup, path)
            print(f'  WARNING: no replacements, restored backup')


if __name__ == '__main__':
    patch()
