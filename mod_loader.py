import json
import os
import sys
import copy
import hashlib
from typing import Dict, List, Optional, Any

def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

MODS_DIR = os.path.join(_get_base_dir(), 'mods')
GAME_VERSION = 'v0.3.1-alpha'

VALID_CARD_TYPES = {'thorn', 'bloom', 'root', 'guard'}
VALID_QUALITIES = {'Common', 'Unusual', 'Epic', 'Ultra', 'Super'}
VALID_FLAGS = {'exile', 'precision', 'indestructible', 'non_stack', 'non_stackable', 'sprout', 'symbiosis', 'uncancellable'}
VALID_EFFECTS = {
    'deal_damage', 'deal_damage_multi', 'heal', 'draw', 'gain_e', 'gain_m', 'gain_armor', 'gain_dodge',
    'apply_poison', 'apply_burn', 'apply_toxic', 'apply_vulnerable',
    'reveal_enemy_hand', 'steal_enemy_card',
    'choose_from_deck', 'choose_from_discard', 'choose_from_exile',
    'set_health', 'set_invincible', 'set_untargetable',
    'block_enemy_attacks', 'force_enemy_attacks_only', 'block_own_actions',
    'counter_dodge', 'counter_nazar', 'counter_negate_skill',
    'counter_equip_protect', 'counter_block_enemy_attacks',
    'counter_set_invincible_then_die',
    'equip_sponge', 'equip_reduce_enemy_draw', 'equip_reduce_enemy_e',
    'equip_reduce_own_draw', 'equip_reduce_own_e',
    'equip_add_toxic', 'equip_set_health',
    'equip_on_destroy_remove_poison_damage',
    'on_fatal_invincible_then_die', 'on_fatal_set_health_exile',
    'log',
    'damage', 'damage_multi', 'poison', 'burn', 'vulnus', 'toxic',
    'add_armor', 'remove_armor', 'set_armor', 'dodge_this', 'dodge_permanent',
    'clear_buffs', 'clear_debuffs', 'clear_all_effects', 'clear_status',
    'cost_e', 'cost_m', 'mod_e_regen', 'mod_m_regen', 'mod_draw',
    'discard', 'reveal_deck_top', 'steal_card', 'copy_card',
    'random_discard_from_hand', 'put_card_to_deck', 'shuffle_discard_into_deck',
    'give_card_to_hand', 'give_card_to_deck', 'give_card_to_discard',
    'remove_specific_card',
    'destroy_random_equip', 'destroy_all_equip', 'destroy_all_field_equip',
    'equip_protection', 'remove_equip_protection', 'place_as_equip',
    'block_action', 'block_card_type', 'force_card_type', 'nullify_current_card',
    'invincible', 'untargetable', 'skip_turn', 'extra_turn', 'force_end_turn',
    'mark_self_damage_source',
    'fission', 'multiply_next_damage', 'reduce_next_cost', 'increase_next_cost',
    'fusion', 'add_tag', 'remove_tag', 'transform_card',
    'gain_durability', 'lose_durability', 'set_durability',
    'record_play_count', 'record_equip_turns', 'reset_counter', 'create_counter',
    'exile_this', 'move_to_discard', 'move_to_deck',
    'global_damage_mult', 'global_heal_mult', 'global_cost_mult',
    'swap_health', 'swap_hands', 'broadcast_event', 'modify_damage',
    'trigger_on_enemy_use_type', 'trigger_on_friendly_use_type',
    'trigger_on_self_magic_heal_cumulative', 'trigger_manual', 'response_declare',
    'trigger_on_event',
}
VALID_EQUIP_EFFECTS = {
    'per_card_played', 'per_e_spent', 'per_m_spent',
    'per_health_recover', 'per_health_consume',
    'on_damage_dealt', 'on_damage_taken',
}
VALID_EVENT_EFFECTS = {
    'max_health_mod', 'convert_to_magic', 'convert_to_light',
    'apply_burn', 'draw_to_full', 'gain_e_per_turn', 'first_strike',
    'convert_to_yggdrasil',
}


class ModCard:
    def __init__(self, data: dict):
        self.id = data.get('id', '')
        self.name_cn = data.get('name_cn', '')
        self.name_en = data.get('name_en', '')
        self.cost_e = data.get('cost_e', 0)
        self.cost_m = data.get('cost_m', 0)
        self.card_type = data.get('card_type', 'thorn')
        self.count = data.get('count', 1)
        self.quality = data.get('quality', 'Common')
        self.description = data.get('description', '')
        self.effect_text = data.get('effect_text', '')
        self.flags = set(data.get('flags', []))
        self.effects = data.get('effects', [])
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

    def to_dict(self) -> dict:
        return {
            'id': self.id, 'name_cn': self.name_cn, 'name_en': self.name_en,
            'cost_e': self.cost_e, 'cost_m': self.cost_m,
            'card_type': self.card_type, 'count': self.count,
            'quality': self.quality, 'description': self.description,
            'effect_text': self.effect_text, 'flags': list(self.flags),
            'effects': self.effects, 'damage': self.damage, 'hits': self.hits,
            'heal': self.heal, 'draw': self.draw, 'gain_e': self.gain_e,
            'gain_m': self.gain_m, 'armor': self.armor, 'dodge': self.dodge,
            'poison': self.poison, 'burn': self.burn,
            'trigger_cost_e': self.trigger_cost_e,
            'trigger_effect_text': self.trigger_effect_text,
            'trigger_effects': self.trigger_effects,
            'response_trigger': self.response_trigger,
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
        self.info: Optional[ModInfo] = None
        self.cards: List[ModCard] = []
        self.events: List[ModEvent] = []
        self.errors: List[str] = []
        self.enabled = True

    def to_dict(self) -> dict:
        return {
            'info': self.info.to_dict() if self.info else {},
            'cards': [c.to_dict() for c in self.cards],
            'events': [e.to_dict() for e in self.events],
        }


def validate_mod(data: dict) -> List[str]:
    errors = []
    info = data.get('info', {})
    if not info.get('name'):
        errors.append('模组缺少名称')
    for i, card in enumerate(data.get('cards', [])):
        if not card.get('id'):
            errors.append(f'卡牌#{i + 1}缺少ID')
        if card.get('card_type') not in VALID_CARD_TYPES:
            errors.append(f'卡牌#{i + 1}类型无效: {card.get("card_type")}')
        if card.get('quality') not in VALID_QUALITIES:
            errors.append(f'卡牌#{i + 1}品质无效: {card.get("quality")}')
        for flag in card.get('flags', []):
            if flag not in VALID_FLAGS:
                errors.append(f'卡牌#{i + 1}标签无效: {flag}')
        for eff in card.get('effects', []):
            if isinstance(eff, str) and eff not in VALID_EFFECTS:
                errors.append(f'卡牌#{i + 1}效果无效: {eff}')
            elif isinstance(eff, dict):
                if eff.get('type') not in VALID_EFFECTS:
                    errors.append(f'卡牌#{i + 1}效果类型无效: {eff.get("type")}')
    for i, event in enumerate(data.get('events', [])):
        if not event.get('name_cn') and not event.get('name_en'):
            errors.append(f'事件#{i + 1}缺少名称')
        for eff in event.get('effects', []):
            if isinstance(eff, str) and eff not in VALID_EVENT_EFFECTS:
                errors.append(f'事件#{i + 1}效果无效: {eff}')
            elif isinstance(eff, dict):
                if eff.get('type') not in VALID_EVENT_EFFECTS:
                    errors.append(f'事件#{i + 1}效果类型无效: {eff.get("type")}')
    return errors


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
    errors = validate_mod(data)
    mod.errors = errors
    if data.get('info'):
        mod.info = ModInfo(data['info'])
    for cd in data.get('cards', []):
        mod.cards.append(ModCard(cd))
    for ed in data.get('events', []):
        mod.events.append(ModEvent(ed))
    return mod


def load_all_mods() -> List[Mod]:
    mods = []
    if not os.path.isdir(MODS_DIR):
        return mods
    for fname in os.listdir(MODS_DIR):
        if fname.endswith('.json'):
            mod = load_mod(os.path.join(MODS_DIR, fname))
            mods.append(mod)
    return mods


def save_mod(mod: Mod):
    os.makedirs(MODS_DIR, exist_ok=True)
    data = mod.to_dict()
    with open(mod.filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def delete_mod(filepath: str):
    if os.path.exists(filepath):
        os.remove(filepath)


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


def merge_mod_cards_to_card_defs() -> List[str]:
    from cards import CARD_DEFS
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
            card_def = mc.to_card_def()
            CARD_DEFS[mc.id] = card_def
            merged.append(mc.id)
        print(f'[模组] 已加载模组 {mod.info.name if mod.info else mod.filename}: {len(mod.cards)} 张卡牌')
    if merged:
        print(f'[模组] 共合并 {len(merged)} 张模组卡牌到 CARD_DEFS')
    else:
        print('[模组] 没有模组卡牌被合并（可能没有启用的模组，或所有模组都有验证错误）')
    return merged
