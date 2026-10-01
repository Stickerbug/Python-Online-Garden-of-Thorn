# -*- coding: utf-8 -*-
"""描述冗余清理补丁（2026-10-01）：
- 删触发/统计语境的「实际」二字（数学等价：没造成实际伤害=0去乘=无效果）
- MagicRNA「暂时魔力迅捷」→「魔力迅捷」（引擎写 magic_swift_value 永久位，文本错误）
- 调度阶段「塞入抽牌堆底部」→「塞入抽牌堆」（随后即洗牌，底部无意义）
保留：费用语境（实际E/M消耗）、公式语境（实际伤害×N%）、BloodKnife 实际回复、
RNA「暂时迅捷」（引擎真写 temp_swift_value，与「暂时威力」同理自洽）。
"""
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODS = ROOT / 'mods'

# legacy_id -> {lang: [(old, new), ...]}
PATCHES = {
    'Fang': {
        'zh': [('造成实际伤害时，回复', '造成伤害时，回复')],
        'en': [('when causing actual damage, recover', 'when dealing damage, recover')],
        'fr': [('lorsque vous causez des dégâts réels, récupérez', 'lorsque vous causez des dégâts, récupérez')],
        'ja': [('実ダメージを与えた場合、', 'ダメージを与えた場合、')],
    },
    'Kale': {
        'zh': [('造成实际伤害时，若', '造成伤害时，若')],
        'en': [('after dealing actual damage, if', 'after dealing damage, if')],
        'fr': [('après avoir infligé des dégâts réels, si', "après avoir infligé des dégâts, si")],
        'ja': [('実ダメージを与えた後、', 'ダメージを与えた後、')],
    },
    'Daisy': {
        'zh': [('造成实际伤害时，目标', '造成伤害时，目标')],
        'en': [('when it deals actual damage, at', 'when it deals damage, at')],
        'fr': [('si ces dégâts infligent des dégâts réels, au', 'si ces dégâts infligent des dégâts, au')],
        'ja': [('実ダメージを与えた時、', 'ダメージを与えた時、')],
    },
    'Marble': {
        'zh': [('前述伤害每次造成实际伤害时', '前述伤害每次造成伤害时')],
        'en': [('each time the preceding damage deals actual damage', 'each time the preceding damage deals damage')],
        'fr': [('chaque fois que ces dégâts infligent des dégâts réels', 'chaque fois que ces dégâts infligent des dégâts')],
        'ja': [('このダメージが実際にダメージを与えるたび', 'このダメージがダメージを与えるたび')],
    },
    'HeatedThorn': {
        'zh': [('造成实际伤害时，额外', '造成伤害时，额外')],
        'en': [('When actual damage is dealt, additionally', 'When damage is dealt, additionally')],
        'fr': [('Lorsque des dégâts réels sont infligés, jouez', 'Lorsque des dégâts sont infligés, jouez')],
        'ja': [('実際にダメージを与えた時、', 'ダメージを与えた時、')],
    },
    'Pinecone': {
        'zh': [('造成实际伤害时，使受伤', '造成伤害时，使受伤')],
        'en': [('Whenever this deals actual damage, apply', 'Whenever this deals damage, apply')],
        'fr': [("Chaque fois que cette carte inflige des dégâts réels, applique", "Chaque fois que cette carte inflige des dégâts, applique")],
        'ja': [('実ダメージを与えるたび、', 'ダメージを与えるたび、')],
    },
    'Diamond': {
        'zh': [('造成实际伤害时，额外', '造成伤害时，额外')],
        'en': [('when it deals actual damage, play', 'when it deals damage, play')],
        'fr': [('si cette carte inflige des dégâts réels, jouez', 'si cette carte inflige des dégâts, jouez')],
        'ja': [('実ダメージを与えた時、', 'ダメージを与えた時、')],
    },
    'ElectronMissile': {
        'zh': [('造成实际伤害时，使目标', '造成伤害时，使目标')],
        'en': [('when it deals actual damage, give', 'when it deals damage, give')],
        'fr': [('si cette carte inflige des dégâts réels, donnez', 'si cette carte inflige des dégâts, donnez')],
        'ja': [('実ダメージを与えた時、', 'ダメージを与えた時、')],
    },
    'MagicElectronMissile': {
        'zh': [('造成实际伤害时，使目标', '造成伤害时，使目标')],
        'en': [('when it deals actual damage, give', 'when it deals damage, give')],
        'fr': [('si cette carte inflige des dégâts réels, donnez', 'si cette carte inflige des dégâts, donnez')],
        'ja': [('実ダメージを与えた時、', 'ダメージを与えた時、')],
    },
    'BloodSugar': {
        'zh': [('每次造成实际伤害时', '每次造成伤害时')],
        'en': [('After each instance of actual damage,', 'After each instance of damage,')],
        'fr': [('Après chaque dégât réel,', 'Après chaque dégât,')],
        'ja': [('実ダメージを与えるたび、', 'ダメージを与えるたび、')],
    },
    'Yucca': {
        'zh': [('造成的实际伤害低于10', '造成的伤害低于10')],
        'en': [('the actual damage the target dealt last turn', 'the damage the target dealt last turn')],
        'fr': [('les dégâts réels infligés par la cible au tour précédent', 'les dégâts infligés par la cible au tour précédent')],
        'ja': [('与えた実際のダメージが10未満', '与えたダメージが10未満')],
    },
    'Clay': {
        'zh': [('每受到6点实际伤害', '每受到6点伤害')],
        'en': [('every 6 actual damage you take', 'every 6 damage you take')],
        'fr': [('chaque 6 dégâts réels que vous subissez', 'chaque 6 dégâts que vous subissez')],
        'ja': [('実際に6ダメージを受けるたび', '6ダメージを受けるたび')],
    },
    'MagicFang': {
        'zh': [('每造成3点实际伤害', '每造成3点伤害')],
        'en': [('for every 3 actual damage dealt', 'for every 3 damage dealt')],
        'fr': [('tranche de 3 dégâts réels infligés', 'tranche de 3 dégâts infligés')],
        'ja': [('実際に与えた3ダメージごとに', '与えた3ダメージごとに')],
    },
    'RNA': {
        'zh': [('每受到1次实际伤害', '每受到1次伤害')],
        'en': [('takes actual damage', 'takes damage')],
        'fr': [('subit des dégâts réels', 'subit des dégâts')],
        'ja': [('実ダメージを受けるたび', 'ダメージを受けるたび')],
    },
    'MagicRNA': {
        # 引擎写 magic_swift_value（永久位）——「暂时魔力迅捷」文本错误
        'zh': [('每受到1次实际伤害', '每受到1次伤害'), ('获得2层暂时魔力迅捷', '获得2层魔力迅捷')],
        'en': [('takes actual damage', 'takes damage'), ('Temporary Magic Swift:2', 'Magic Swift:2')],
        'fr': [('subit des dégâts réels', 'subit des dégâts'), ('Rapidité magique temporaire:2', 'Rapidité magique:2')],
        'ja': [('実ダメージを受けるたび', 'ダメージを受けるたび'), ('一時魔力迅捷:2', '魔力迅捷:2')],
    },
    'Scales': {
        'zh': [('累计受到10点实际伤害', '累计受到10点伤害')],
        'en': [('cumulative 10 actual damage', 'cumulative 10 damage')],
        'fr': [('cumul de 10 dégâts réels', 'cumul de 10 dégâts')],
        'ja': [('累計10の実際ダメージ', '累計10のダメージ')],
    },
    'Avocado': {
        'zh': [('受到实际物理伤害时', '受到物理伤害时')],
        'en': [('takes actual physical damage', 'takes physical damage')],
        'fr': [('subit des dégâts physiques réels', 'subit des dégâts physiques')],
        'ja': [('実際の物理ダメージを受けるたび', '物理ダメージを受けるたび')],
    },
    'ToiletPaper': {
        'zh': [('每次受到实际物理伤害后', '每次受到物理伤害后')],
        'en': [('take actual physical damage', 'take physical damage')],
        'fr': [('subissez des dégâts physiques réels', 'subissez des dégâts physiques')],
        'ja': [('実際の物理ダメージを受けるたび', '物理ダメージを受けるたび')],
    },
    'Coconut': {
        'zh': [('获得等同于实际伤害的层数', '获得等同于该伤害的层数')],
        'en': [('stacks equal to the actual damage', 'stacks equal to that damage')],
        'fr': [('égal aux dégâts réels', 'égal à ces dégâts')],
        'ja': [('実ダメージと同じ数の層', 'このダメージと同じ数の層')],
    },
    'Obsidian': {
        'zh': [('等同本次实际伤害层数', '等同本次伤害层数')],
        'en': [('equal to the actual damage dealt', 'equal to the damage dealt')],
        'fr': [('égales aux dégâts réellement infligés', 'égales aux dégâts infligés')],
        'ja': [('実際に与えたダメージに等しい', '与えたダメージに等しい')],
    },
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
    for path in sorted(MODS.glob('*.gtnmod')):
        with zipfile.ZipFile(path) as z:
            entries = {n: z.read(n) for n in z.namelist()}
        mod_data = json.loads(entries['mod.json'].decode('utf-8'))
        cards = (mod_data.get('registries') or {}).get('cards', [])
        card_ids = {c.get('legacy_id') or c.get('id') for c in cards}
        matched = [cid for cid in PATCHES if cid in card_ids]
        if not matched:
            continue
        backup = path.with_suffix('.gtnmod.bak-text')
        shutil.copy2(path, backup)
        total = 0
        for card in cards:
            legacy = card.get('legacy_id') or card.get('id')
            langs = PATCHES.get(legacy)
            if not langs:
                continue
            for lang, pairs in langs.items():
                for field in ('effect_text', 'effect_text_cn', 'effect_text_en'):
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
            for cid_key, card in zip([c.get('legacy_id') or c.get('id') for c in cards], cards):
                langs = PATCHES.get(cid_key)
                entry = ns.get(card.get('id'))
                if not langs or not isinstance(entry, dict) or not entry.get('effect_text'):
                    continue
                pairs = langs.get(lang)
                if pairs:
                    entry['effect_text'], n = apply_to_text(entry['effect_text'], pairs)
                    total += n
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
