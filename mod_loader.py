import json
import os
import sys
import copy
import hashlib
from typing import Dict, List, Optional, Any
from mod_validator import (
    VALID_CARD_TYPES,
    VALID_QUALITIES,
    VALID_FLAGS,
    VALID_EFFECTS,
    VALID_EVENT_EFFECTS,
    validate_mod_data,
)

def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

MODS_DIR = os.path.join(_get_base_dir(), 'mods')
GAME_VERSION = 'v0.3.1-alpha'
_MODS_CACHE_SIGNATURE = None
_MODS_CACHE: List['Mod'] = []


class ModCard:
    def __init__(self, data: dict):
        self.id = data.get('id', '')
        self.name_cn = data.get('name_cn', '')
        self.name_en = data.get('name_en', '')
        self.cost_e = data.get('cost_e', 0)
        self.cost_m = data.get('cost_m', 0)
        self.card_type = data.get('card_type', 'thorn')
        try:
            self.count = max(0, int(data.get('count', data.get('weight', 3))))
        except (TypeError, ValueError):
            self.count = 3
        self.quality = data.get('quality', 'Common')
        self.description = data.get('description', '')
        self.effect_text = data.get('effect_text', '')
        self.flags = set(data.get('flags', []))
        self.effects = data.get('effects', [])
        self.scripts = data.get('scripts', {}) if isinstance(data.get('scripts', {}), dict) else {}
        self.trigger_cost_e = data.get('trigger_cost_e', -1)
        self.trigger_effect_text = data.get('trigger_effect_text', '')
        self.trigger_effects = data.get('trigger_effects', [])
        self.damage = data.get('damage', 0)
        self.hits = data.get('hits', 1)
        self.heal = data.get('heal', 0)
        self.draw = data.get('draw', 0)
        self.gain_e = data.get('gain_e', 0)
        self.gain_m = data.get('gain_m', 0)
        self.armor = data.get('armor', 0)
        self.dodge = data.get('dodge', 0)
        self.poison = data.get('poison', 0)
        self.burn = data.get('burn', 0)
        self.response_trigger = data.get('response_trigger', '')
        self.response_title = data.get('response_title', '')
        self.response_content = data.get('response_content', '')

    def to_dict(self) -> dict:
        return {
            'id': self.id, 'name_cn': self.name_cn, 'name_en': self.name_en,
            'cost_e': self.cost_e, 'cost_m': self.cost_m,
            'card_type': self.card_type, 'count': self.count,
            'quality': self.quality, 'description': self.description,
            'effect_text': self.effect_text, 'flags': list(self.flags),
            'effects': self.effects, 'damage': self.damage, 'hits': self.hits,
            'scripts': self.scripts,
            'heal': self.heal, 'draw': self.draw, 'gain_e': self.gain_e,
            'gain_m': self.gain_m, 'armor': self.armor, 'dodge': self.dodge,
            'poison': self.poison, 'burn': self.burn,
            'trigger_cost_e': self.trigger_cost_e,
            'trigger_effect_text': self.trigger_effect_text,
            'trigger_effects': self.trigger_effects,
            'response_trigger': self.response_trigger,
            'response_title': self.response_title,
            'response_content': self.response_content,
        }

    def to_card_def(self):
        from cards import CardDef
        return CardDef(
            id=self.id,
            name_en=self.name_en,
            name_cn=self.name_cn,
            cost_e=self.cost_e,
            cost_m=self.cost_m,
            card_type=self.card_type,
            count=self.count,
            quality=self.quality,
            description=self.description,
            effect_text=self.effect_text,
            flags=self.flags,
            trigger_cost_e=self.trigger_cost_e,
            trigger_effect_text=self.trigger_effect_text,
            response_trigger=self.response_trigger,
            effects=self.effects,
            scripts=self.scripts,
            response_title=self.response_title,
            response_content=self.response_content,
        )


class ModEvent:
    def __init__(self, data: dict):
        self.id = data.get('id', 0)
        self.name_cn = data.get('name_cn', '')
        self.name_en = data.get('name_en', '')
        self.desc = data.get('desc', '')
        self.position = data.get('position', 3)
        self.effects = data.get('effects', [])
        self.params = data.get('params', {})

    def to_dict(self) -> dict:
        return {
            'id': self.id, 'name_cn': self.name_cn, 'name_en': self.name_en,
            'desc': self.desc, 'position': self.position,
            'effects': self.effects, 'params': self.params,
        }


class ModVariable:
    def __init__(self, data: dict):
        self.id = data.get('id', '')
        self.name = data.get('name', self.id)
        self.scope = data.get('scope', 'player')
        self.initial = data.get('initial', 0)
        self.desc = data.get('desc', '')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'scope': self.scope,
            'initial': self.initial,
            'desc': self.desc,
        }


class ModInfo:
    def __init__(self, data: dict):
        self.name = data.get('name', '')
        self.version = data.get('version', '1.0.0')
        self.author = data.get('author', '')
        self.description = data.get('description', '')
        self.game_version = data.get('game_version', '')

    def to_dict(self) -> dict:
        return {
            'name': self.name, 'version': self.version,
            'author': self.author, 'description': self.description,
            'game_version': self.game_version,
        }


class Mod:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.format_version = 1
        self.editor: Dict[str, Any] = {}
        self.info: Optional[ModInfo] = None
        self.cards: List[ModCard] = []
        self.events: List[ModEvent] = []
        self.variables: List[ModVariable] = []
        self.custom_statuses: List[dict] = []
        self.custom_tags: List[dict] = []
        self.scripts: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.validation_hash = ''
        self.enabled = True

    def to_dict(self, include_validation: bool = False) -> dict:
        data = {
            'format_version': self.format_version,
            'editor': self.editor,
            'info': self.info.to_dict() if self.info else {},
            'cards': [c.to_dict() for c in self.cards],
            'events': [e.to_dict() for e in self.events],
            'variables': [v.to_dict() for v in self.variables],
            'custom_statuses': self.custom_statuses,
            'custom_tags': self.custom_tags,
            'scripts': self.scripts,
        }
        if include_validation:
            data['errors'] = list(self.errors)
            data['warnings'] = list(self.warnings)
            data['validation_hash'] = self.validation_hash
        return data


def validate_mod(data: dict) -> List[str]:
    return validate_mod_data(data, strict=False).errors


def _strip_scripts_for_untrusted_mod(data: dict) -> tuple:
    sanitized = copy.deepcopy(data)
    changed = False
    if isinstance(sanitized.get('scripts'), dict) and sanitized.get('scripts'):
        sanitized['scripts'] = {}
        changed = True
    for card in sanitized.get('cards', []) if isinstance(sanitized.get('cards'), list) else []:
        if isinstance(card, dict) and isinstance(card.get('scripts'), dict) and card.get('scripts'):
            card['scripts'] = {}
            changed = True
    return sanitized, changed


def load_mod_from_data(data: dict, source: str = "memory", allow_scripts: bool = True) -> Mod:
    mod = Mod(source or 'memory')
    if not isinstance(data, dict):
        mod.errors.append('模组根节点必须是对象')
        return mod
    if not allow_scripts:
        data, stripped_scripts = _strip_scripts_for_untrusted_mod(data)
        if stripped_scripts:
            mod.warnings.append('社区模组 scripts 已被禁用')
    validation = validate_mod_data(data, strict=False, source=mod.filename)
    mod.errors = validation.errors
    mod.warnings.extend(validation.warnings)
    mod.validation_hash = validation.content_hash
    data = validation.normalized if validation.normalized else data
    if not allow_scripts:
        data, stripped_scripts_after_validation = _strip_scripts_for_untrusted_mod(data)
        if stripped_scripts_after_validation and '社区模组 scripts 已被禁用' not in mod.warnings:
            mod.warnings.append('社区模组 scripts 已被禁用')
    mod.format_version = data.get('format_version', 1)
    mod.editor = data.get('editor', {}) if isinstance(data.get('editor', {}), dict) else {}
    if data.get('info'):
        mod.info = ModInfo(data['info'])
    for cd in data.get('cards', []):
        mod.cards.append(ModCard(cd))
    for ed in data.get('events', []):
        mod.events.append(ModEvent(ed))
    for vd in data.get('variables', []):
        mod.variables.append(ModVariable(vd))
    mod.custom_statuses = data.get('custom_statuses', []) if isinstance(data.get('custom_statuses', []), list) else []
    mod.custom_tags = data.get('custom_tags', []) if isinstance(data.get('custom_tags', []), list) else []
    mod.scripts = data.get('scripts', {}) if isinstance(data.get('scripts', {}), dict) else {}
    return mod


def load_mod(filepath: str) -> Mod:
    mod = Mod(filepath)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        mod.errors.append(f'JSON解析错误: {e}')
        return mod
    except Exception as e:
        mod.errors.append(f'读取失败: {e}')
        return mod
    return load_mod_from_data(data, source=filepath, allow_scripts=True)


def _mods_signature():
    if not os.path.isdir(MODS_DIR):
        return ()
    items = []
    for entry in os.scandir(MODS_DIR):
        if not entry.name.endswith('.json'):
            continue
        try:
            stat = entry.stat()
            items.append((entry.name, stat.st_mtime_ns, stat.st_size))
        except OSError:
            items.append((entry.name, 0, 0))
    return tuple(sorted(items))


def invalidate_mod_cache():
    global _MODS_CACHE_SIGNATURE, _MODS_CACHE
    _MODS_CACHE_SIGNATURE = None
    _MODS_CACHE = []


def load_all_mods(force: bool = False) -> List[Mod]:
    global _MODS_CACHE_SIGNATURE, _MODS_CACHE
    signature = _mods_signature()
    if not force and _MODS_CACHE_SIGNATURE == signature:
        return copy.deepcopy(_MODS_CACHE)
    mods = []
    if not os.path.isdir(MODS_DIR):
        return mods
    for fname in os.listdir(MODS_DIR):
        if fname.endswith('.json'):
            mod = load_mod(os.path.join(MODS_DIR, fname))
            mods.append(mod)
    _MODS_CACHE_SIGNATURE = signature
    _MODS_CACHE = copy.deepcopy(mods)
    return mods


def save_mod(mod: Mod):
    os.makedirs(MODS_DIR, exist_ok=True)
    data = mod.to_dict()
    with open(mod.filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    invalidate_mod_cache()


def delete_mod(filepath: str):
    if os.path.exists(filepath):
        os.remove(filepath)
    invalidate_mod_cache()


def check_conflicts(mods: List[Mod]) -> List[str]:
    conflicts = []
    card_ids = {}
    event_ids = {}
    for mod in mods:
        if not mod.enabled or mod.errors:
            continue
        for card in mod.cards:
            if card.id in card_ids:
                conflicts.append(f'卡牌ID冲突: {card.id} (来自 {card_ids[card.id]} 和 {mod.info.name if mod.info else mod.filename})')
            else:
                card_ids[card.id] = mod.info.name if mod.info else mod.filename
        for event in mod.events:
            key = f"event_{event.id}"
            if key in event_ids:
                conflicts.append(f'事件ID冲突: {event.id} (来自 {event_ids[key]} 和 {mod.info.name if mod.info else mod.filename})')
            else:
                event_ids[key] = mod.info.name if mod.info else mod.filename
    return conflicts


def get_enabled_mods() -> List[Mod]:
    mods = load_all_mods()
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\GardenOfThorn', 0, winreg.KEY_READ)
        disabled_list, _ = winreg.QueryValueEx(key, 'DisabledMods')
        winreg.CloseKey(key)
        disabled = set(disabled_list.split(',')) if disabled_list else set()
    except Exception:
        disabled = set()
    for mod in mods:
        if mod.filename in disabled:
            mod.enabled = False
    return mods


def compute_mods_hash() -> str:
    enabled = get_enabled_mods()
    hasher = hashlib.sha256()
    for mod in sorted(enabled, key=lambda m: m.filename):
        if not mod.enabled or mod.errors:
            continue
        try:
            with open(mod.filepath, 'rb') as f:
                hasher.update(f.read())
        except Exception:
            hasher.update(mod.filename.encode('utf-8'))
    return hasher.hexdigest()


def get_mods_summary() -> dict:
    enabled = get_enabled_mods()
    active = [m for m in enabled if m.enabled and not m.errors]
    return {
        'hash': compute_mods_hash(),
        'mods': [m.info.name if m.info else m.filename for m in active],
        'count': len(active),
    }


def get_active_mod_variables() -> List[dict]:
    variables = []
    for mod in get_enabled_mods():
        if not mod.enabled or mod.errors:
            continue
        for variable in mod.variables:
            variables.append(variable.to_dict())
    return variables


def merge_mod_cards_to_card_defs() -> List[str]:
    from cards import CARD_DEFS, ERROR_CARD_ID
    mods = get_enabled_mods()
    active = [m for m in mods if m.enabled and not m.errors]
    for mod in mods:
        if mod.errors:
            print(f'[模组] 跳过模组 {mod.info.name if mod.info else mod.filename}，验证错误: {mod.errors}')
        elif not mod.enabled:
            print(f'[模组] 跳过已禁用模组 {mod.info.name if mod.info else mod.filename}')
    merged = []
    for mod in active:
        for mc in mod.cards:
            if mc.id == ERROR_CARD_ID:
                continue
            card_def = mc.to_card_def()
            CARD_DEFS[mc.id] = card_def
            merged.append(mc.id)
        print(f'[模组] 已加载模组 {mod.info.name if mod.info else mod.filename}: {len(mod.cards)} 张卡牌')
    if merged:
        print(f'[模组] 共合并 {len(merged)} 张模组卡牌到 CARD_DEFS')
    else:
        print('[模组] 没有模组卡牌被合并（可能没有启用的模组，或所有模组都有验证错误）')
    return merged
