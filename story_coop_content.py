"""Compile the shared story catalog into the safe cooperative subset.

The single-player catalog remains the source of truth.  Cooperative reducers
consume only definitions that this module can prove are representable by the
current two-seat executor.  Unsupported scripts and effect shapes fail closed:
they never become playable merely because they were added to a solo pool.
"""

from dataclasses import dataclass
from copy import deepcopy
import hashlib
import json
import re

from story_content import (
    STORY_REWARD_CARD_IDS,
    STORY_SHOP_CARD_IDS,
)
from story_content_model import STORY_CONTENT_REGISTRY, StoryContentRegistry


COOP_STARTER_CARD_IDS = ('basic', 'rose', 'amulet', 'mage_basic')
COOP_CARD_EFFECT_TYPES = frozenset({
    'damage',
    'shield',
    'active_discard',
    'draw',
    'elixir',
    'heal',
    'magic',
    'electric_damage',
})
COOP_CARD_TAGS = frozenset({'exile', 'precise', 'wide'})
COOP_OPENING_BLESSING_SCRIPTS = frozenset({
    'gain_gold',
    'gain_max_health',
    'gain_random_ultra_card',
    'wealth_and_basics',
})
COOP_ENEMY_EFFECT_TYPES = frozenset({
    'damage',
    'gain_power',
    'gain_shield',
    'self_damage',
})
COOP_ENCOUNTER_BIOMES = ('garden', 'jungle', 'factory')
COOP_ENCOUNTER_TIERS = ('simple', 'hard')
COOP_EVENT_EFFECT_TYPES = frozenset({'gold', 'heal', 'health_loss'})
COOP_RELIC_SCRIPTS = frozenset({
    'floor_heal',
    'gain_card_heal',
    'gain_gold',
    'gain_max_health',
    'rest_gold',
    'shop_discount',
    'turn_magic',
})
COOP_REQUIRED_RELIC_IDS = ('energetic', 'magic_source')
COOP_SUPPORTED_TERM_IDS = frozenset({'electric_damage'})
COOP_CAPABILITY_STATES = frozenset({'supported', 'deferred', 'rejected'})
_CARD_ID_RE = re.compile(r'[a-z0-9][a-z0-9._:-]{0,127}')
_CARD_FIELDS = frozenset({
    'source_card_id', 'name', 'description', 'flavor',
    'image_url', 'upgraded_image_url',
    'type', 'rarity', 'owner', 'cost_e', 'cost_m',
    'effects', 'tags', 'target', 'upgrade', 'script', 'coop',
})
_CARD_UPGRADE_FIELDS = frozenset({
    'cost_e', 'cost_m', 'description', 'effects', 'infinite',
    'script', 'tags', 'target',
})


class CoopStoryContentError(ValueError):
    """The canonical story catalog cannot satisfy the cooperative contract."""


@dataclass(frozen=True, slots=True)
class CompiledCoopStoryContent:
    """Immutable compiled identifiers plus a canonical serialized manifest."""

    supported_card_ids: frozenset
    reward_card_ids: tuple
    shop_card_ids: tuple
    opening_blessing_ids: tuple
    supported_enemy_ids: frozenset
    encounter_ids_by_tier: tuple
    event_ids_by_biome: tuple
    supported_relic_ids: frozenset
    chest_relic_ids: tuple
    shop_relic_ids: tuple
    fingerprint: str
    _manifest_json: str

    def manifest(self):
        return json.loads(self._manifest_json)

    def card_definition(self, card_id):
        return deepcopy(self.manifest()['cards'].get(str(card_id)))

    def blessing_definition(self, blessing_id):
        return deepcopy(self.manifest()['blessings'].get(str(blessing_id)))

    def enemy_definition(self, enemy_id):
        return deepcopy(self.manifest()['enemies'].get(str(enemy_id)))

    def encounter_definition(self, encounter_id):
        return deepcopy(self.manifest()['encounters'].get(str(encounter_id)))

    def encounter_ids(self, biome, tier):
        key = f'{str(biome)}:{str(tier)}'
        return tuple(dict(self.encounter_ids_by_tier).get(key, ()))

    def event_ids(self, biome):
        return tuple(dict(self.event_ids_by_biome).get(str(biome), ()))

    def event_definition(self, event_id):
        return deepcopy(self.manifest()['events'].get(str(event_id)))

    def relic_definition(self, relic_id):
        return deepcopy(self.manifest()['relics'].get(str(relic_id)))

    def character_definition(self, character_id):
        return deepcopy(self.manifest()['characters'].get(str(character_id)))

    def capability(self, kind, content_id):
        capabilities = self.manifest().get('capabilities', {})
        entry = capabilities.get(str(kind), {}).get(str(content_id))
        if entry is None:
            raise CoopStoryContentError(
                f'未知协作内容能力 {kind}:{content_id}'
            )
        return deepcopy(entry)


def _strict_nonnegative_int(value):
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _strict_positive_int(value):
    return not isinstance(value, bool) and isinstance(value, int) and value > 0


def _jsonable(value):
    if isinstance(value, dict):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise CoopStoryContentError(f'协作内容包含不能序列化的值：{type(value).__name__}')


def _validate_effect(effect):
    if not isinstance(effect, dict):
        return False
    effect_type = str(effect.get('type') or '')
    if effect_type not in COOP_CARD_EFFECT_TYPES:
        return False
    if not _strict_nonnegative_int(effect.get('amount')):
        return False
    keys = set(effect)
    if effect_type in {'damage', 'electric_damage'}:
        if not keys <= {'type', 'amount', 'hits'}:
            return False
        return 'hits' not in effect or _strict_positive_int(effect.get('hits'))
    if effect_type in {'shield', 'draw', 'elixir', 'heal', 'magic'}:
        return keys <= {'type', 'amount'}
    if not keys <= {'type', 'amount', 'exact'}:
        return False
    return 'exact' not in effect or isinstance(effect.get('exact'), bool)


def _merged_card_variant(definition, upgraded):
    values = deepcopy(definition)
    if upgraded:
        upgrade = definition.get('upgrade')
        if not isinstance(upgrade, dict):
            return None
        values.update(deepcopy(upgrade))
    return values


def _card_compatibility_reason(card_id, definition):
    if not isinstance(card_id, str) or not _CARD_ID_RE.fullmatch(card_id):
        return '卡牌标识无效'
    if not isinstance(definition, dict):
        return '卡牌定义不是对象'
    if not set(definition) <= _CARD_FIELDS:
        return '卡牌定义包含协作编译器未知字段'
    policy = definition.get('coop')
    if policy is False:
        return '卡牌被权威内容显式排除在协作模式之外'
    if policy is not None and policy is not True and not isinstance(policy, dict):
        return '卡牌协作策略无效'
    if isinstance(policy, dict):
        if not set(policy) <= {'enabled', 'required'} or any(
            not isinstance(value, bool) for value in policy.values()
        ):
            return '卡牌协作策略无效'
        if policy.get('enabled') is False:
            return '卡牌被权威内容显式排除在协作模式之外'
    if str(definition.get('script') or ''):
        return '卡牌带有协作执行器尚未支持的脚本'
    tags = definition.get('tags', ())
    if not isinstance(tags, (list, tuple)) or any(
        not isinstance(tag, str) or tag not in COOP_CARD_TAGS
        for tag in tags
    ):
        return '卡牌标签包含协作执行器尚未支持的语义'
    target = str(definition.get('target') or '')
    if target not in {'enemy', 'self'}:
        return '卡牌目标类型尚未支持'
    for upgraded in (False, True):
        if upgraded and 'upgrade' not in definition:
            continue
        if upgraded and (
            not isinstance(definition.get('upgrade'), dict)
            or not set(definition['upgrade']) <= _CARD_UPGRADE_FIELDS
        ):
            return '卡牌升级定义包含协作编译器未知字段'
        values = _merged_card_variant(definition, upgraded)
        if not isinstance(values, dict) or str(values.get('script') or ''):
            return '升级定义带有协作执行器尚未支持的脚本'
        if not _strict_nonnegative_int(values.get('cost_e', 0)):
            return '卡牌E费用无效'
        if not _strict_nonnegative_int(values.get('cost_m', 0)):
            return '卡牌M费用无效'
        effects = values.get('effects')
        if not isinstance(effects, (list, tuple)) or not effects:
            return '卡牌没有可执行效果'
        if not all(_validate_effect(effect) for effect in effects):
            return '卡牌效果形状超出协作执行器能力'
    return None


def _pool_card_is_eligible(definition, *, reward):
    if not isinstance(definition, dict):
        return False
    if str(definition.get('type') or '') in {'curse', 'infect'}:
        return False
    if str(definition.get('rarity') or '') in {'primary', 'super', 'special'}:
        return False
    owner = str(definition.get('owner') or '')
    return owner != 'neutral' if reward else bool(owner)


def _card_manifest(definition):
    fields = (
        'source_card_id', 'name', 'description', 'flavor',
        'image_url', 'upgraded_image_url',
        'type', 'rarity', 'owner', 'cost_e', 'cost_m',
        'effects', 'tags', 'target', 'upgrade', 'coop',
    )
    return _jsonable({key: deepcopy(definition[key]) for key in fields if key in definition})


def _blessing_manifest(definition):
    fields = ('name', 'description', 'script', 'amount', 'order')
    return _jsonable({key: deepcopy(definition[key]) for key in fields if key in definition})


def _blessing_is_compatible(definition):
    if not isinstance(definition, dict):
        return False
    script = str(definition.get('script') or '')
    if script not in COOP_OPENING_BLESSING_SCRIPTS:
        return False
    if not _strict_nonnegative_int(definition.get('amount', 0)):
        return False
    return not (
        definition.get('selection') is not None
        or definition.get('choices') is not None
    )


def _enemy_effect_is_compatible(effect):
    if not isinstance(effect, dict):
        return False
    effect_type = str(effect.get('type') or '')
    if effect_type not in COOP_ENEMY_EFFECT_TYPES:
        return False
    if not set(effect) <= {'type', 'amount', 'lunatic_amount', 'hits', 'lunatic_hits'}:
        return False
    if not _strict_nonnegative_int(effect.get('amount')):
        return False
    if 'lunatic_amount' in effect and not _strict_nonnegative_int(effect.get('lunatic_amount')):
        return False
    if effect_type != 'damage' and ({'hits', 'lunatic_hits'} & set(effect)):
        return False
    if 'hits' in effect and not _strict_positive_int(effect.get('hits')):
        return False
    if 'lunatic_hits' in effect and not _strict_positive_int(effect.get('lunatic_hits')):
        return False
    return True


def _enemy_compatibility_reason(enemy_id, definition):
    if not isinstance(enemy_id, str) or not _CARD_ID_RE.fullmatch(enemy_id):
        return '敌人标识无效'
    if not isinstance(definition, dict):
        return '敌人定义不是对象'
    if not set(definition) <= {
        'name', 'max_health', 'moves', 'script', 'traits',
        'lunatic_max_health', 'image_url',
    }:
        return '敌人定义包含协作编译器未知字段'
    if definition.get('script') not in {None, ''}:
        return '敌人带有协作执行器尚未支持的脚本'
    traits = definition.get('traits', ())
    if not isinstance(traits, (list, tuple)) or traits:
        return '敌人带有协作执行器尚未支持的特性'
    if not _strict_positive_int(definition.get('max_health')):
        return '敌人最大生命无效'
    if (
        'lunatic_max_health' in definition
        and not _strict_positive_int(definition.get('lunatic_max_health'))
    ):
        return '敌人疯狂难度最大生命无效'
    moves = definition.get('moves')
    if not isinstance(moves, (list, tuple)) or not moves:
        return '敌人没有行动'
    for move in moves:
        if not isinstance(move, dict) or not set(move) <= {'name', 'effects'}:
            return '敌人行动包含协作编译器未知字段'
        effects = move.get('effects')
        if not isinstance(effects, (list, tuple)) or not effects:
            return '敌人行动没有可执行效果'
        if not all(_enemy_effect_is_compatible(effect) for effect in effects):
            return '敌人行动效果超出协作执行器能力'
        if sum(str(effect.get('type') or '') == 'damage' for effect in effects) > 1:
            return '敌人单次行动包含多个协作执行器无法区分的攻击段'
    return None


def _enemy_manifest(definition):
    fields = ('name', 'max_health', 'lunatic_max_health', 'moves', 'image_url')
    return _jsonable({key: deepcopy(definition[key]) for key in fields if key in definition})


def _encounter_member(member):
    if isinstance(member, str):
        return {'def_id': member}
    if not isinstance(member, dict) or not set(member) <= {'def_id', 'move_index', 'move_step'}:
        return None
    def_id = str(member.get('def_id') or '')
    result = {'def_id': def_id}
    if 'move_index' in member:
        if not _strict_nonnegative_int(member.get('move_index')):
            return None
        result['move_index'] = int(member['move_index'])
    if 'move_step' in member:
        if not _strict_nonnegative_int(member.get('move_step')):
            return None
        result['move_step'] = int(member['move_step'])
    return result


def _compile_encounters(encounters, supported_enemy_ids):
    compiled = {}
    ids_by_tier = []
    for biome in COOP_ENCOUNTER_BIOMES:
        biome_groups = encounters.get(biome)
        if not isinstance(biome_groups, dict):
            raise CoopStoryContentError(f'故事遭遇缺少生物群系 {biome}')
        for tier in COOP_ENCOUNTER_TIERS:
            groups = biome_groups.get(tier, ())
            if not isinstance(groups, (list, tuple)):
                raise CoopStoryContentError(f'故事遭遇池 {biome}:{tier} 无效')
            tier_ids = []
            for index, raw_group in enumerate(groups):
                if not isinstance(raw_group, (list, tuple)) or not raw_group:
                    continue
                members = [_encounter_member(member) for member in raw_group]
                if any(member is None for member in members):
                    continue
                if any(member['def_id'] not in supported_enemy_ids for member in members):
                    continue
                encounter_id = f'{biome}:{tier}:{index + 1:03d}'
                compiled[encounter_id] = {
                    'biome': biome,
                    'tier': tier,
                    'members': members,
                }
                tier_ids.append(encounter_id)
            ids_by_tier.append((f'{biome}:{tier}', tuple(tier_ids)))
    if not dict(ids_by_tier).get('garden:simple'):
        raise CoopStoryContentError('协作花园普通遭遇池至少需要1个兼容遭遇')
    return compiled, tuple(ids_by_tier)


def _encounters_from_registry(content_registry):
    encounters = {}
    indexed_groups = {}
    for key in content_registry.keys('encounter'):
        content_id = key.split(':', 1)[1]
        definition = content_registry.definition('encounter', content_id)
        try:
            biome = str(definition['biome'])
            tier = str(definition['tier'])
            index = int(content_id.rsplit(':', 1)[1])
            members = deepcopy(definition['members'])
        except (KeyError, TypeError, ValueError) as exc:
            raise CoopStoryContentError(
                f'规范战斗组合 {content_id} 的结构无效'
            ) from exc
        indexed_groups.setdefault((biome, tier), []).append((index, members))
    for (biome, tier), groups in indexed_groups.items():
        encounters.setdefault(biome, {})[tier] = tuple(
            members for _, members in sorted(groups)
        )
    return encounters


def _registry_ids(content_registry, kind):
    return tuple(
        key.split(':', 1)[1]
        for key in content_registry.keys(kind)
    )


def _capability(state, reason):
    if state not in COOP_CAPABILITY_STATES:
        raise CoopStoryContentError(f'未知协作能力状态 {state}')
    entry = {'state': state}
    if reason:
        entry['reason'] = str(reason)
    return entry


def _card_is_explicitly_rejected(definition):
    if not isinstance(definition, dict):
        return False
    policy = definition.get('coop')
    return policy is False or (
        isinstance(policy, dict) and policy.get('enabled') is False
    )


def _event_is_explicitly_rejected(definition):
    if not isinstance(definition, dict):
        return False
    policy = definition.get('coop')
    modes = definition.get('modes')
    return (
        isinstance(policy, dict) and policy.get('enabled') is False
    ) or (
        isinstance(modes, (list, tuple)) and 'coop' not in modes
    )


def _character_manifest_and_capabilities(
    content_registry,
    *,
    supported_card_ids,
    supported_relic_ids,
):
    characters = content_registry.catalog('character')
    manifest = {}
    capabilities = {}
    for character_id in _registry_ids(content_registry, 'character'):
        definition = characters.get(character_id)
        if not isinstance(definition, dict):
            raise CoopStoryContentError(f'角色 {character_id} 定义不是对象')
        status = str(definition.get('implementation_status') or '')
        if status not in {'playable', 'planned'}:
            raise CoopStoryContentError(f'角色 {character_id} 的实现状态无效')
        if status == 'planned' and not _localized_value_is_valid(
            definition.get('unavailable_message')
        ):
            raise CoopStoryContentError(f'未完成角色 {character_id} 缺少提示文本')
        manifest[character_id] = _jsonable(definition)
        starter_card_ids = tuple(
            str(item.get('card_id') or item.get('character_card_id') or '')
            for item in definition.get('starter_deck', ())
            if isinstance(item, dict)
        )
        starter_relic_ids = tuple(
            str(relic_id) for relic_id in definition.get('starter_relics', ())
        )
        missing_cards = [
            card_id for card_id in starter_card_ids
            if not card_id or card_id not in supported_card_ids
        ]
        missing_relics = [
            relic_id for relic_id in starter_relic_ids
            if not relic_id or relic_id not in supported_relic_ids
        ]
        coop_ready = status == 'playable' and not missing_cards and not missing_relics
        reason = ''
        if status != 'playable':
            reason = '角色机制尚未完成'
        elif missing_cards or missing_relics:
            reason = '角色可单人使用，但协作执行器尚未覆盖其初始牌组或天赋'
        capabilities[character_id] = _capability(
            'supported' if coop_ready else 'deferred',
            reason,
        )
    return manifest, capabilities


def _localized_value_is_valid(value):
    return (
        isinstance(value, dict)
        and set(value) == {'zh', 'en'}
        and all(isinstance(text, str) and text.strip() for text in value.values())
    )


def _event_compatibility_reason(event_id, definition):
    if not isinstance(event_id, str) or not _CARD_ID_RE.fullmatch(event_id):
        return '事件标识无效'
    if not isinstance(definition, dict) or set(definition) != {
        'title', 'description', 'speaker', 'portrait', 'biomes', 'modes',
        'coop', 'options',
    }:
        return '事件定义包含协作编译器未知字段'
    if any(
        not _localized_value_is_valid(definition.get(key))
        for key in ('title', 'description', 'speaker')
    ):
        return '事件本地化文本无效'
    if not isinstance(definition.get('portrait'), str) or not definition['portrait']:
        return '事件场景标记无效'
    biomes = definition.get('biomes')
    modes = definition.get('modes')
    if (
        not isinstance(biomes, (list, tuple))
        or not biomes
        or any(str(biome) not in COOP_ENCOUNTER_BIOMES for biome in biomes)
        or not isinstance(modes, (list, tuple))
        or 'coop' not in modes
    ):
        return '事件不能进入当前协作生物群系'
    policy = definition.get('coop')
    if (
        not isinstance(policy, dict)
        or set(policy) != {'enabled', 'policy', 'effect_scope'}
        or policy.get('enabled') is not True
        or policy.get('policy') != 'unanimous_required'
        or policy.get('effect_scope') != 'all_players'
    ):
        return '事件协作策略无效'
    options = definition.get('options')
    if not isinstance(options, (list, tuple)) or len(options) < 2:
        return '事件至少需要两个协作选项'
    option_ids = []
    for option in options:
        if not isinstance(option, dict) or not {
            'id', 'label', 'description', 'effects'
        } <= set(option) or not set(option) <= {
            'id', 'label', 'description', 'effects',
            'requires_confirmation', 'risky',
        }:
            return '事件选项包含协作编译器未知字段'
        option_id = str(option.get('id') or '')
        if not _CARD_ID_RE.fullmatch(option_id):
            return '事件选项标识无效'
        option_ids.append(option_id)
        if any(
            not _localized_value_is_valid(option.get(key))
            for key in ('label', 'description')
        ):
            return '事件选项本地化文本无效'
        if any(
            key in option and not isinstance(option.get(key), bool)
            for key in ('requires_confirmation', 'risky')
        ):
            return '事件选项展示策略无效'
        effects = option.get('effects')
        if not isinstance(effects, (list, tuple)) or not effects:
            return '事件选项没有可执行效果'
        for effect in effects:
            if not isinstance(effect, dict):
                return '事件效果不是对象'
            effect_type = str(effect.get('type') or '')
            if effect_type not in COOP_EVENT_EFFECT_TYPES:
                return '事件效果尚未接入协作执行器'
            if not _strict_nonnegative_int(effect.get('amount')):
                return '事件效果数值无效'
            if effect_type in {'heal', 'gold'} and set(effect) != {'type', 'amount'}:
                return '事件效果包含未知字段'
            if effect_type == 'health_loss' and (
                set(effect) != {'type', 'amount', 'nonlethal'}
                or effect.get('nonlethal') is not True
            ):
                return '协作事件失去生命必须明确为非致命'
    if len(option_ids) != len(set(option_ids)):
        return '事件选项标识不能重复'
    return None


def _event_manifest(definition):
    return _jsonable({
        key: deepcopy(definition[key])
        for key in (
            'title', 'description', 'speaker', 'portrait', 'biomes', 'modes',
            'coop', 'options',
        )
    })


def validate_compiled_coop_event_definition(event_id, definition):
    """Return a normalized safe event snapshot or fail closed.

    Active cooperative rooms persist this small definition so an already
    offered choice keeps its original meaning after the canonical catalog
    changes.  Persisted snapshots still pass the exact same compiler contract
    before they can be executed.
    """

    reason = _event_compatibility_reason(str(event_id or ''), definition)
    if reason:
        raise CoopStoryContentError(f'协作事件快照不兼容：{reason}')
    return _event_manifest(definition)


def _relic_compatibility_reason(relic_id, definition):
    if not isinstance(relic_id, str) or not _CARD_ID_RE.fullmatch(relic_id):
        return '遗物标识无效'
    if not isinstance(definition, dict):
        return '遗物定义不是对象'
    if set(definition) != {
        'name', 'description', 'rarity', 'script', 'amount',
        'stackable', 'shop_excluded',
    }:
        return '遗物定义包含协作编译器未知字段'
    if str(definition.get('script') or '') not in COOP_RELIC_SCRIPTS:
        return '遗物脚本尚未接入协作执行器'
    rarity = str(definition.get('rarity') or '')
    if rarity not in {'common', 'rare', 'ultra'} and not (
        relic_id in COOP_REQUIRED_RELIC_IDS and rarity == 'special'
    ):
        return '遗物稀有度不能进入协作普通奖励池'
    if not _strict_nonnegative_int(definition.get('amount')):
        return '遗物数值无效'
    if not isinstance(definition.get('stackable'), bool):
        return '遗物叠加策略无效'
    if not isinstance(definition.get('shop_excluded'), bool):
        return '遗物商店策略无效'
    return None


def _relic_manifest(definition):
    return _jsonable({
        key: deepcopy(definition[key])
        for key in (
            'name', 'description', 'rarity', 'script', 'amount',
            'stackable', 'shop_excluded',
        )
    })


def _build_capability_manifest(
    *,
    content_registry,
    cards,
    card_reasons,
    supported_card_ids,
    blessings,
    opening_blessing_ids,
    enemy_reasons,
    supported_enemy_ids,
    compiled_encounters,
    events,
    event_reasons,
    supported_event_ids,
    relic_reasons,
    supported_relic_ids,
    character_capabilities,
):
    capabilities = {'character': character_capabilities}
    capabilities['character_card'] = {
        content_id: _capability(
            'supported' if content_id in supported_card_ids else 'deferred',
            '' if content_id in supported_card_ids else '角色卡牌执行器尚未完成',
        )
        for content_id in _registry_ids(content_registry, 'character_card')
    }
    capabilities['character_relic'] = {
        content_id: _capability(
            'supported' if content_id in supported_relic_ids else 'deferred',
            '' if content_id in supported_relic_ids else '角色天赋执行器尚未完成',
        )
        for content_id in _registry_ids(content_registry, 'character_relic')
    }
    capabilities['term'] = {
        content_id: _capability(
            'supported' if content_id in COOP_SUPPORTED_TERM_IDS else 'deferred',
            '' if content_id in COOP_SUPPORTED_TERM_IDS else '术语对应的协作结算尚未完成',
        )
        for content_id in _registry_ids(content_registry, 'term')
    }
    capabilities['card'] = {}
    for content_id in _registry_ids(content_registry, 'card'):
        reason = card_reasons.get(content_id)
        if content_id in supported_card_ids:
            capabilities['card'][content_id] = _capability('supported', '')
        elif _card_is_explicitly_rejected(cards.get(content_id)):
            capabilities['card'][content_id] = _capability(
                'rejected', reason or '权威内容明确禁止协作模式'
            )
        else:
            capabilities['card'][content_id] = _capability(
                'deferred', reason or '尚未进入当前协作卡池'
            )

    capabilities['blessing'] = {
        content_id: _capability(
            'supported' if content_id in opening_blessing_ids else 'deferred',
            '' if content_id in opening_blessing_ids else '协作开局尚未支持该赐福语义',
        )
        for content_id in _registry_ids(content_registry, 'blessing')
        if content_id in blessings
    }
    capabilities['enemy'] = {
        content_id: _capability(
            'supported' if content_id in supported_enemy_ids else 'deferred',
            '' if content_id in supported_enemy_ids else (
                enemy_reasons.get(content_id) or '协作敌人执行器尚未支持'
            ),
        )
        for content_id in _registry_ids(content_registry, 'enemy')
    }
    capabilities['encounter'] = {
        content_id: _capability(
            'supported' if content_id in compiled_encounters else 'deferred',
            '' if content_id in compiled_encounters else '战斗组合包含尚未支持的敌人或语义',
        )
        for content_id in _registry_ids(content_registry, 'encounter')
    }
    capabilities['event'] = {}
    for content_id in _registry_ids(content_registry, 'event'):
        reason = event_reasons.get(content_id)
        if content_id in supported_event_ids:
            capabilities['event'][content_id] = _capability('supported', '')
        elif _event_is_explicitly_rejected(events.get(content_id)):
            capabilities['event'][content_id] = _capability(
                'rejected', reason or '权威内容明确禁止协作模式'
            )
        else:
            capabilities['event'][content_id] = _capability(
                'deferred', reason or '协作事件执行器尚未支持'
            )
    capabilities['relic'] = {
        content_id: _capability(
            'supported' if content_id in supported_relic_ids else 'deferred',
            '' if content_id in supported_relic_ids else (
                relic_reasons.get(content_id) or '协作遗物执行器尚未支持'
            ),
        )
        for content_id in _registry_ids(content_registry, 'relic')
    }
    return _jsonable(capabilities)


def compile_coop_story_content(
    *,
    content_registry=None,
    cards=None,
    reward_card_ids=None,
    shop_card_ids=None,
    blessings=None,
    enemies=None,
    encounters=None,
    relics=None,
    events=None,
    required_card_ids=COOP_STARTER_CARD_IDS,
):
    """Return the safe cooperative projection of the canonical catalog.

    Compatible cards are discovered from the canonical reward and shop pools.
    Starter cards are mandatory and make compilation fail if a future story
    edit gives them semantics the cooperative executor cannot reproduce.
    """

    content_registry = (
        STORY_CONTENT_REGISTRY if content_registry is None else content_registry
    )
    if not isinstance(content_registry, StoryContentRegistry):
        raise CoopStoryContentError('协作内容必须使用规范故事内容注册表')
    cards = content_registry.catalog('card') if cards is None else cards
    if reward_card_ids is None:
        reward_card_ids = tuple(dict.fromkeys((
            *STORY_REWARD_CARD_IDS,
            *(
                card_id for card_id, definition in cards.items()
                if str((definition or {}).get('owner') or '') == 'mage'
                and str((definition or {}).get('rarity') or '') != 'primary'
            ),
        )))
    if shop_card_ids is None:
        shop_card_ids = tuple(dict.fromkeys((
            *STORY_SHOP_CARD_IDS,
            *(
                card_id for card_id, definition in cards.items()
                if str((definition or {}).get('owner') or '') == 'mage'
                and str((definition or {}).get('rarity') or '') != 'primary'
            ),
        )))
    blessings = content_registry.catalog('blessing') if blessings is None else blessings
    enemies = content_registry.catalog('enemy') if enemies is None else enemies
    encounters = (
        _encounters_from_registry(content_registry)
        if encounters is None else encounters
    )
    relics = content_registry.catalog('relic') if relics is None else relics
    events = content_registry.catalog('event') if events is None else events
    if (
        not isinstance(cards, dict)
        or not isinstance(blessings, dict)
        or not isinstance(enemies, dict)
        or not isinstance(encounters, dict)
        or not isinstance(relics, dict)
        or not isinstance(events, dict)
    ):
        raise CoopStoryContentError('故事内容目录必须是对象')

    required = tuple(dict.fromkeys(str(card_id) for card_id in required_card_ids))
    reasons = {
        card_id: _card_compatibility_reason(card_id, cards.get(card_id))
        for card_id in cards
    }
    declared_ids = tuple(
        card_id
        for card_id, definition in cards.items()
        if isinstance(definition, dict)
        and (
            definition.get('coop') is True
            or (
                isinstance(definition.get('coop'), dict)
                and (
                    definition['coop'].get('enabled') is True
                    or definition['coop'].get('required') is True
                )
            )
        )
    )
    for card_id in declared_ids:
        reason = reasons.get(card_id)
        if reason:
            raise CoopStoryContentError(f'声明启用的协作卡牌 {card_id} 不兼容：{reason}')
    for card_id in required:
        reason = _card_compatibility_reason(card_id, cards.get(card_id))
        if reason:
            raise CoopStoryContentError(f'必需协作卡牌 {card_id} 不兼容：{reason}')

    compatible_ids = {
        card_id for card_id, reason in reasons.items()
        if reason is None
    }
    reward_ids = tuple(
        card_id for card_id in dict.fromkeys(str(item) for item in reward_card_ids)
        if card_id in compatible_ids
        and _pool_card_is_eligible(cards.get(card_id), reward=True)
    )
    shop_ids = tuple(
        card_id for card_id in dict.fromkeys(str(item) for item in shop_card_ids)
        if card_id in compatible_ids
        and _pool_card_is_eligible(cards.get(card_id), reward=False)
    )
    if len(reward_ids) < 3:
        raise CoopStoryContentError('协作奖励池至少需要3张兼容卡牌')
    if len(shop_ids) < 3:
        raise CoopStoryContentError('协作商店池至少需要3张兼容卡牌')

    supported_ids = frozenset((*required, *reward_ids, *shop_ids))
    opening_ids = tuple(
        blessing_id
        for blessing_id, definition in sorted(
            blessings.items(),
            key=lambda item: (
                int(item[1].get('order', 0)) if isinstance(item[1], dict) else 0,
                str(item[0]),
            ),
        )
        if _blessing_is_compatible(definition)
    )
    if len(opening_ids) < 3:
        raise CoopStoryContentError('协作开局至少需要3个兼容赐福')

    enemy_reasons = {
        enemy_id: _enemy_compatibility_reason(enemy_id, definition)
        for enemy_id, definition in enemies.items()
    }
    supported_enemy_ids = frozenset(
        enemy_id for enemy_id, reason in enemy_reasons.items()
        if reason is None
    )
    compiled_encounters, encounter_ids_by_tier = _compile_encounters(
        encounters,
        supported_enemy_ids,
    )
    event_reasons = {
        event_id: _event_compatibility_reason(event_id, definition)
        for event_id, definition in events.items()
    }
    for event_id, definition in events.items():
        if (
            isinstance(definition, dict)
            and isinstance(definition.get('coop'), dict)
            and definition['coop'].get('enabled') is True
            and event_reasons.get(event_id)
        ):
            raise CoopStoryContentError(
                f'声明启用的兼容共享事件 {event_id} 不兼容：'
                f'{event_reasons[event_id]}'
            )
    supported_event_ids = frozenset(
        event_id for event_id, reason in event_reasons.items()
        if reason is None
    )
    event_ids_by_biome = tuple(
        (
            biome,
            tuple(
                event_id for event_id, definition in events.items()
                if event_id in supported_event_ids
                and biome in tuple(definition.get('biomes') or ())
            ),
        )
        for biome in COOP_ENCOUNTER_BIOMES
    )
    if not dict(event_ids_by_biome).get('garden'):
        raise CoopStoryContentError('协作花园至少需要1个兼容共享事件')
    relic_reasons = {
        relic_id: _relic_compatibility_reason(relic_id, definition)
        for relic_id, definition in relics.items()
    }
    for relic_id in COOP_REQUIRED_RELIC_IDS:
        reason = _relic_compatibility_reason(relic_id, relics.get(relic_id))
        if reason:
            raise CoopStoryContentError(f'必需协作遗物 {relic_id} 不兼容：{reason}')
    supported_relic_ids = frozenset(
        relic_id for relic_id, reason in relic_reasons.items()
        if reason is None
    )
    chest_relic_ids = tuple(
        relic_id for relic_id in relics
        if relic_id in supported_relic_ids
        and relics[relic_id].get('rarity') in {'common', 'rare', 'ultra'}
    )
    shop_relic_ids = tuple(
        relic_id for relic_id in chest_relic_ids
        if not relics[relic_id].get('shop_excluded')
    )
    if len(chest_relic_ids) < 3 or len(shop_relic_ids) < 3:
        raise CoopStoryContentError('协作遗物池与商店遗物池都至少需要3个兼容遗物')

    characters_manifest, character_capabilities = (
        _character_manifest_and_capabilities(
            content_registry,
            supported_card_ids=supported_ids,
            supported_relic_ids=supported_relic_ids,
        )
    )
    capabilities = _build_capability_manifest(
        content_registry=content_registry,
        cards=cards,
        card_reasons=reasons,
        supported_card_ids=supported_ids,
        blessings=blessings,
        opening_blessing_ids=opening_ids,
        enemy_reasons=enemy_reasons,
        supported_enemy_ids=supported_enemy_ids,
        compiled_encounters=compiled_encounters,
        events=events,
        event_reasons=event_reasons,
        supported_event_ids=supported_event_ids,
        relic_reasons=relic_reasons,
        supported_relic_ids=supported_relic_ids,
        character_capabilities=character_capabilities,
    )

    manifest = {
        'schema_version': 4,
        'content_model_fingerprint': content_registry.fingerprint,
        'characters': characters_manifest,
        'capabilities': capabilities,
        'cards': {
            card_id: _card_manifest(cards[card_id])
            for card_id in sorted(supported_ids)
        },
        'reward_card_ids': list(reward_ids),
        'shop_card_ids': list(shop_ids),
        'blessings': {
            blessing_id: _blessing_manifest(blessings[blessing_id])
            for blessing_id in opening_ids
        },
        'opening_blessing_ids': list(opening_ids),
        'enemies': {
            enemy_id: _enemy_manifest(enemies[enemy_id])
            for enemy_id in sorted(supported_enemy_ids)
        },
        'encounters': compiled_encounters,
        'encounter_ids_by_tier': {
            key: list(value)
            for key, value in encounter_ids_by_tier
        },
        'events': {
            event_id: _event_manifest(events[event_id])
            for event_id in sorted(supported_event_ids)
        },
        'event_ids_by_biome': {
            key: list(value)
            for key, value in event_ids_by_biome
        },
        'relics': {
            relic_id: _relic_manifest(relics[relic_id])
            for relic_id in sorted(supported_relic_ids)
        },
        'chest_relic_ids': list(chest_relic_ids),
        'shop_relic_ids': list(shop_relic_ids),
    }
    manifest_json = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
    )
    fingerprint = hashlib.sha256(manifest_json.encode('utf-8')).hexdigest()
    return CompiledCoopStoryContent(
        supported_card_ids=supported_ids,
        reward_card_ids=reward_ids,
        shop_card_ids=shop_ids,
        opening_blessing_ids=opening_ids,
        supported_enemy_ids=supported_enemy_ids,
        encounter_ids_by_tier=encounter_ids_by_tier,
        event_ids_by_biome=event_ids_by_biome,
        supported_relic_ids=supported_relic_ids,
        chest_relic_ids=chest_relic_ids,
        shop_relic_ids=shop_relic_ids,
        fingerprint=fingerprint,
        _manifest_json=manifest_json,
    )


COOP_STORY_CONTENT = compile_coop_story_content()
COOP_CONTENT_FINGERPRINT = COOP_STORY_CONTENT.fingerprint
COOP_SUPPORTED_CARD_IDS = COOP_STORY_CONTENT.supported_card_ids
COOP_REWARD_CARD_IDS = COOP_STORY_CONTENT.reward_card_ids
COOP_SHOP_CARD_IDS = COOP_STORY_CONTENT.shop_card_ids
COOP_OPENING_BLESSING_IDS = COOP_STORY_CONTENT.opening_blessing_ids
COOP_SUPPORTED_ENEMY_IDS = COOP_STORY_CONTENT.supported_enemy_ids
COOP_SUPPORTED_RELIC_IDS = COOP_STORY_CONTENT.supported_relic_ids
COOP_CHEST_RELIC_IDS = COOP_STORY_CONTENT.chest_relic_ids
COOP_SHOP_RELIC_IDS = COOP_STORY_CONTENT.shop_relic_ids
