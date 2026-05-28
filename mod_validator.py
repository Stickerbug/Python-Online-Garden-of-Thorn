import copy
import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


MOD_FORMAT_VERSION = 1
EDITOR_SCHEMA = 'got_mod_format_v1'
VALID_EDITOR_TOOLS = {'Garden of Thorn Mod Editor'}
MAX_MOD_JSON_BYTES = 1024 * 1024
MAX_CARDS = 300
MAX_EVENTS = 100
MAX_VARIABLES = 300
MAX_CUSTOM_DEFINITIONS = 300

VALID_CARD_TYPES = {'thorn', 'bloom', 'root', 'guard'}
VALID_QUALITIES = {'Common', 'Unusual', 'Epic', 'Ultra', 'Super'}
VALID_FLAGS = {
    'exile', 'precision', 'indestructible', 'non_stack', 'non_stackable',
    'sprout', 'symbiosis', 'uncancellable', 'self_only', 'infinite_exclude',
}
VALID_VARIABLE_SCOPES = {'player', 'team', 'global'}
VALID_SCRIPT_KEYS = {
    'onPlay', 'play', 'on_play',
    'onResponse', 'response', 'on_response',
    'onOwnerTurnStart', 'owner_turn_start', 'on_owner_turn_start',
    'onEnemyTurnStart', 'enemy_turn_start', 'on_enemy_turn_start',
    'onAnyTurnStart', 'any_turn_start', 'on_any_turn_start',
    'onDamageTaken', 'damage_taken', 'on_damage_taken',
    'onEquipmentTrigger', 'equipment_trigger', 'on_equipment_trigger',
    'onEquipmentDestroy', 'equipment_destroy', 'on_equipment_destroy',
    'onDestroy', 'destroy', 'on_destroy',
    'onHandOwnerTurnStart', 'hand_owner_turn_start', 'on_hand_owner_turn_start',
    'onDiscardOwnerTurnStart', 'discard_owner_turn_start', 'on_discard_owner_turn_start',
    'onDeckOwnerTurnStart', 'deck_owner_turn_start', 'on_deck_owner_turn_start',
}

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
    'log', 'if', 'if_else', 'repeat', 'repeat_until', 'for_each', 'for_each_list', 'timed_effect', 'after_all', 'random',
    'damage', 'damage_multi', 'poison', 'burn', 'vulnus', 'toxic',
    'add_armor', 'remove_armor', 'set_armor', 'dodge_this', 'dodge_permanent',
    'clear_buffs', 'clear_debuffs', 'clear_all_effects', 'clear_status',
    'cost_e', 'cost_m', 'mod_e_regen', 'mod_m_regen', 'mod_draw',
    'discard', 'reveal_deck_top', 'steal_card', 'copy_card', 'copy_choice_with_discount',
    'random_discard_from_hand', 'put_card_to_deck', 'shuffle_discard_into_deck',
    'give_card_to_hand', 'give_card_to_deck', 'give_card_to_discard',
    'remove_specific_card',
    'destroy_random_equip', 'destroy_all_equip', 'destroy_all_field_equip',
    'equip_protection', 'remove_equip_protection', 'place_as_equip',
    'add_equipment_to_zone',
    'block_action', 'block_card_type', 'force_card_type', 'nullify_current_card',
    'invincible', 'untargetable', 'skip_turn', 'extra_turn', 'force_end_turn',
    'mark_self_damage_source',
    'fission', 'multiply_next_damage', 'reduce_next_cost', 'increase_next_cost',
    'fusion', 'add_tag', 'remove_tag', 'transform_card',
    'gain_durability', 'lose_durability', 'set_durability',
    'record_play_count', 'record_equip_turns', 'reset_counter', 'create_counter',
    'var_set', 'var_add', 'var_sub', 'var_mul', 'var_div', 'countdown_var',
    'list_set', 'list_append', 'list_insert', 'list_delete', 'list_clear',
    'batch_var_add', 'batch_var_sub', 'batch_var_mul', 'batch_var_div',
    'status_add_named', 'status_remove_named', 'tag_add_named', 'tag_remove_named',
    'batch_status_add', 'batch_status_remove', 'batch_tag_add', 'batch_tag_remove',
    'exile_this', 'move_to_discard', 'move_to_hand', 'move_to_deck',
    'global_damage_mult', 'global_heal_mult', 'global_cost_mult',
    'swap_health', 'swap_hands', 'broadcast_event', 'modify_damage',
    'trigger_on_enemy_use_type', 'trigger_on_friendly_use_type',
    'trigger_on_self_magic_heal_cumulative', 'trigger_manual', 'response_declare',
    'trigger_on_event',
    'on_owner_turn_start', 'on_enemy_turn_start', 'on_any_turn_start',
    'on_damage_taken', 'on_equipment_trigger', 'on_equipment_destroy',
    'on_hand_owner_turn_start', 'on_discard_owner_turn_start', 'on_deck_owner_turn_start',
    'aura_enemy_elixir_recovery',
    'direct_damage', 'lifesteal_damage', 'triangle_damage',
    'discard_choice_then_draw', 'coffee_gain_e',
    'destroy_equipment_choice_or_first', 'destroy_all_destroyable_equipment',
    'destroy_self_equipment', 'activate_corruption',
    'request_target', 'request_card', 'request_confirm',
    'for_each_selected_card', 'card_prop_add', 'card_prop_set',
    'equipment_prop_add', 'equipment_prop_set',
    'player_prop_add', 'player_prop_set',
}

VALID_EVENT_EFFECTS = {
    'max_health_mod', 'convert_to_magic', 'convert_to_light',
    'apply_burn', 'draw_to_full', 'gain_e_per_turn', 'first_strike',
    'convert_to_yggdrasil',
}

ID_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,63}$')


@dataclass
class ModValidationResult:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    normalized: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ''
    format_version: Optional[int] = None
    strict: bool = False

    @property
    def ok(self) -> bool:
        return not self.errors


def canonical_mod_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def compute_mod_hash(data: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_mod_json(data).encode('utf-8')).hexdigest()


def validate_raw_mod_json(raw: bytes, *, strict: bool = True, source: str = '') -> ModValidationResult:
    if len(raw) > MAX_MOD_JSON_BYTES:
        return ModValidationResult(
            errors=[f'{source or "mod"} JSON过大，最大允许 {MAX_MOD_JSON_BYTES} 字节'],
            strict=strict,
        )
    try:
        data = json.loads(raw.decode('utf-8-sig'))
    except Exception as exc:
        return ModValidationResult(errors=[f'JSON解析错误: {exc}'], strict=strict)
    return validate_mod_data(data, strict=strict, source=source)


def validate_mod_data(data: Any, *, strict: bool = False, source: str = '') -> ModValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    if not isinstance(data, dict):
        return ModValidationResult(errors=['模组根节点必须是对象'], strict=strict)

    normalized = copy.deepcopy(data)
    version = normalized.get('format_version')
    if version is None:
        if strict:
            errors.append('缺少 format_version，公开导入只接受格式版本1')
        else:
            warnings.append('缺少 format_version，已按格式版本1兼容读取')
        normalized['format_version'] = MOD_FORMAT_VERSION
        version = MOD_FORMAT_VERSION
    elif version != MOD_FORMAT_VERSION:
        errors.append(f'不支持的 format_version: {version}')
    if strict:
        _validate_editor_meta(normalized.get('editor'), errors)

    info = normalized.get('info')
    if info is None:
        info = {}
        normalized['info'] = info
    if not isinstance(info, dict):
        errors.append('info 必须是对象')
        info = {}
        normalized['info'] = info
    if not _valid_text(info.get('name'), 1, 80):
        errors.append('模组缺少名称，或名称过长')
    for key in ('version', 'author', 'description', 'game_version'):
        if key in info and not _valid_text(info.get(key), 0, 500):
            errors.append(f'info.{key} 必须是文本且不能过长')

    for key in ('cards', 'events', 'variables', 'custom_statuses', 'custom_tags'):
        value = normalized.get(key)
        if value is None:
            value = []
            normalized[key] = value
        if not isinstance(value, list):
            errors.append(f'{key} 必须是数组')
            normalized[key] = []
    if not isinstance(normalized.get('scripts', {}), dict):
        errors.append('scripts 必须是对象')
        normalized['scripts'] = {}

    _check_list_limit(normalized['cards'], MAX_CARDS, 'cards', errors)
    _check_list_limit(normalized['events'], MAX_EVENTS, 'events', errors)
    _check_list_limit(normalized['variables'], MAX_VARIABLES, 'variables', errors)
    _check_list_limit(normalized['custom_statuses'], MAX_CUSTOM_DEFINITIONS, 'custom_statuses', errors)
    _check_list_limit(normalized['custom_tags'], MAX_CUSTOM_DEFINITIONS, 'custom_tags', errors)

    custom_tag_ids = _collect_definition_ids(normalized['custom_tags'], 'custom_tags', errors)
    _collect_definition_ids(normalized['custom_statuses'], 'custom_statuses', errors)
    _validate_variables(normalized['variables'], errors)
    _validate_cards(normalized['cards'], custom_tag_ids, errors)
    _validate_events(normalized['events'], errors)
    _validate_root_scripts(normalized.get('scripts', {}), errors, warnings, strict)
    if strict:
        _validate_editor_trace(normalized, errors)

    content_hash = compute_mod_hash(normalized) if isinstance(normalized, dict) else ''
    return ModValidationResult(
        errors=errors,
        warnings=warnings,
        normalized=normalized,
        content_hash=content_hash,
        format_version=version if isinstance(version, int) else None,
        strict=strict,
    )


def validate_public_mod_data(data: Any, *, source: str = '') -> ModValidationResult:
    return validate_mod_data(data, strict=True, source=source)


def _valid_text(value: Any, min_len: int, max_len: int) -> bool:
    if value is None:
        return min_len == 0
    if not isinstance(value, str):
        return False
    length = len(value.strip())
    return min_len <= length <= max_len


def _check_list_limit(value: List[Any], limit: int, label: str, errors: List[str]) -> None:
    if len(value) > limit:
        errors.append(f'{label} 数量过多，最多 {limit} 个')


def _collect_definition_ids(items: List[Any], label: str, errors: List[str]) -> Set[str]:
    seen: Set[str] = set()
    for index, item in enumerate(items):
        item_label = f'{label}#{index + 1}'
        if isinstance(item, str):
            item_id = item
        elif isinstance(item, dict):
            item_id = item.get('id') or item.get('name')
        else:
            errors.append(f'{item_label} 必须是对象或ID文本')
            continue
        if not item_id:
            errors.append(f'{item_label} 缺少ID')
            continue
        if not _valid_id(str(item_id)):
            errors.append(f'{item_label} ID无效: {item_id}')
            continue
        if item_id in seen:
            errors.append(f'{item_label} ID重复: {item_id}')
        seen.add(str(item_id))
    return seen


def _validate_variables(variables: List[Any], errors: List[str]) -> None:
    seen: Set[str] = set()
    for index, variable in enumerate(variables):
        label = f'variable#{index + 1}'
        if not isinstance(variable, dict):
            errors.append(f'{label} 必须是对象')
            continue
        var_id = variable.get('id') or variable.get('name')
        if not var_id:
            errors.append(f'{label} 缺少ID')
        elif not _valid_id(str(var_id)):
            errors.append(f'{label} ID无效: {var_id}')
        elif var_id in seen:
            errors.append(f'{label} ID重复: {var_id}')
        else:
            seen.add(str(var_id))
        if variable.get('scope', 'player') not in VALID_VARIABLE_SCOPES:
            errors.append(f'{label} scope无效: {variable.get("scope")}')
        if not _valid_number(variable.get('initial', 0), -999999, 999999):
            errors.append(f'{label} initial必须是有限数字')


def _validate_cards(cards: List[Any], custom_tag_ids: Set[str], errors: List[str]) -> None:
    seen: Set[str] = set()
    for index, card in enumerate(cards):
        label = f'card#{index + 1}'
        if not isinstance(card, dict):
            errors.append(f'{label} 必须是对象')
            continue
        card_id = card.get('id')
        if not card_id:
            errors.append(f'{label} 缺少ID')
        elif not _valid_id(str(card_id)):
            errors.append(f'{label} ID无效: {card_id}')
        elif card_id in seen:
            errors.append(f'{label} ID重复: {card_id}')
        else:
            seen.add(str(card_id))
        if card.get('card_type') not in VALID_CARD_TYPES:
            errors.append(f'{label} 类型无效: {card.get("card_type")}')
        if card.get('quality', 'Common') not in VALID_QUALITIES:
            errors.append(f'{label} 品质无效: {card.get("quality")}')
        for field_name in ('cost_e', 'cost_m', 'count', 'damage', 'hits', 'heal', 'draw', 'gain_e', 'gain_m', 'armor', 'dodge', 'poison', 'burn', 'trigger_cost_e'):
            if field_name in card and not _valid_number(card.get(field_name), -9999, 9999):
                errors.append(f'{label}.{field_name} 必须是有限数字')
        flags = card.get('flags', [])
        if not isinstance(flags, list):
            errors.append(f'{label}.flags 必须是数组')
        else:
            for flag in flags:
                if flag not in VALID_FLAGS and flag not in custom_tag_ids:
                    errors.append(f'{label} 标签未定义或不受支持: {flag}')
        _validate_effect_list(card.get('effects', []), label, VALID_EFFECTS, errors)
        _validate_effect_list(card.get('trigger_effects', []), f'{label}.trigger_effects', VALID_EFFECTS, errors)
        scripts = card.get('scripts', {})
        if scripts and not isinstance(scripts, dict):
            errors.append(f'{label}.scripts 必须是对象')
        elif isinstance(scripts, dict):
            for script_name, script in scripts.items():
                if script_name not in VALID_SCRIPT_KEYS:
                    errors.append(f'{label}.scripts.{script_name} 不是受支持的触发头')
                    continue
                script_effects = script.get('effects', []) if isinstance(script, dict) else script
                _validate_effect_list(script_effects, f'{label}.scripts.{script_name}', VALID_EFFECTS, errors)


def _validate_events(events: List[Any], errors: List[str]) -> None:
    seen: Set[str] = set()
    for index, event in enumerate(events):
        label = f'event#{index + 1}'
        if not isinstance(event, dict):
            errors.append(f'{label} 必须是对象')
            continue
        event_id = str(event.get('id', index + 1))
        if event_id in seen:
            errors.append(f'{label} ID重复: {event_id}')
        seen.add(event_id)
        if not event.get('name_cn') and not event.get('name_en'):
            errors.append(f'{label} 缺少名称')
        if 'position' in event and not _valid_number(event.get('position'), 1, 9):
            errors.append(f'{label}.position 必须是1到9的数字')
        _validate_effect_list(event.get('effects', []), label, VALID_EVENT_EFFECTS, errors)


def _validate_root_scripts(scripts: Dict[str, Any], errors: List[str], warnings: List[str], strict: bool) -> None:
    for name, value in scripts.items():
        if not isinstance(name, str):
            errors.append('scripts 的键必须是文本')
        if not isinstance(value, dict):
            errors.append(f'scripts.{name} 必须是对象')
            continue
        effects = value.get('effects')
        if effects is not None:
            _validate_effect_list(effects, f'scripts.{name}', VALID_EFFECTS, errors)
        xml = value.get('xml')
        if xml is not None and not isinstance(xml, str):
            errors.append(f'scripts.{name}.xml 必须是文本')
        if strict and not (name.startswith('card:') or name.startswith('event:') or name.startswith('status:') or name.startswith('tag:')):
            warnings.append(f'scripts.{name} 不是标准编辑器脚本键')


def _validate_editor_meta(editor: Any, errors: List[str]) -> None:
    if not isinstance(editor, dict):
        errors.append('缺少 editor 标记，公开导入只接受模组编辑器导出的文件')
        return
    tool = editor.get('tool')
    schema = editor.get('schema')
    if tool not in VALID_EDITOR_TOOLS:
        errors.append(f'editor.tool 无效: {tool}')
    if schema != EDITOR_SCHEMA:
        errors.append(f'editor.schema 无效: {schema}')


def _validate_editor_trace(data: Dict[str, Any], errors: List[str]) -> None:
    for index, card in enumerate(data.get('cards', [])):
        if not isinstance(card, dict):
            continue
        has_runtime_logic = bool(card.get('effects') or card.get('trigger_effects') or card.get('scripts'))
        if not has_runtime_logic:
            continue
        scripts = card.get('scripts')
        if not isinstance(scripts, dict) or not scripts:
            errors.append(f'card#{index + 1} 缺少编辑器脚本，公开导入只接受编辑器格式')
            continue
        if not any(key in VALID_SCRIPT_KEYS for key in scripts.keys()):
            errors.append(f'card#{index + 1} 缺少受支持的触发头，公开导入只接受编辑器格式')


def _validate_effect_list(effects: Any, label: str, valid_effects: Set[str], errors: List[str]) -> None:
    if effects in (None, ''):
        return
    if not isinstance(effects, list):
        errors.append(f'{label} 效果必须是数组')
        return
    for index, effect in enumerate(effects):
        _validate_effect_node(effect, f'{label}.effects#{index + 1}', valid_effects, errors)


def _validate_effect_node(effect: Any, label: str, valid_effects: Set[str], errors: List[str]) -> None:
    if isinstance(effect, str):
        if effect not in valid_effects:
            errors.append(f'{label} 效果无效: {effect}')
        return
    if not isinstance(effect, dict):
        errors.append(f'{label} 必须是效果对象')
        return
    effect_type = effect.get('type')
    if not effect_type:
        errors.append(f'{label} 缺少type')
    elif effect_type not in valid_effects:
        errors.append(f'{label} 效果类型无效: {effect_type}')
    _validate_nested_effects(effect.get('params'), label, valid_effects, errors)


def _validate_nested_effects(value: Any, label: str, valid_effects: Set[str], errors: List[str]) -> None:
    if isinstance(value, list):
        looks_like_effect_list = any(isinstance(item, str) or (isinstance(item, dict) and 'type' in item) for item in value)
        if looks_like_effect_list:
            for index, item in enumerate(value):
                _validate_effect_node(item, f'{label}.nested#{index + 1}', valid_effects, errors)
        else:
            for item in value:
                _validate_nested_effects(item, label, valid_effects, errors)
        return
    if isinstance(value, dict):
        if 'type' in value:
            _validate_effect_node(value, f'{label}.nested', valid_effects, errors)
            return
        for child in value.values():
            _validate_nested_effects(child, label, valid_effects, errors)


def _valid_id(value: str) -> bool:
    return bool(ID_RE.match(value))


def _valid_number(value: Any, minimum: float, maximum: float) -> bool:
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    if not math.isfinite(float(value)):
        return False
    return minimum <= float(value) <= maximum
