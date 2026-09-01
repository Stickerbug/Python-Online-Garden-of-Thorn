"""Playable, server-authoritative cooperative story journey.

The v10 schema and coordination core deliberately stay content-agnostic.  This
module supplies the current two-seat three-stage contract: curated combat,
personal rewards and rooms, shared hidden votes, deterministic map progression,
stage barriers, and the only public projection that cooperative HTTP clients
may receive.
"""

from copy import deepcopy
import hashlib
import json
import math
import re

from story_content import (
    STORY_ENCHANTMENT_BOOKS,
    STORY_RULES,
    story_combat_starting_magic,
)
from story_coop_content import (
    COOP_CHEST_RELIC_IDS,
    COOP_CONTENT_FINGERPRINT,
    COOP_OPENING_BLESSING_IDS,
    COOP_REWARD_CARD_IDS,
    COOP_SHOP_CARD_IDS,
    COOP_SHOP_RELIC_IDS,
    COOP_STORY_CONTENT,
    COOP_SUPPORTED_CARD_IDS,
    COOP_SUPPORTED_RELIC_IDS,
    CoopStoryContentError,
    validate_compiled_coop_event_definition,
)
from story_mode import STORY_CONTENT_VERSION, generate_story_map
from story_coop import (
    COOP_STORY_DEFAULT_RULES,
    story_seat_for_user,
    validate_story_state_v10,
)
from story_coop_combat import (
    COOP_COMBAT_ENDED,
    COOP_COMBAT_HERO_TURN,
    CoopCombatError,
    damage_coop_enemy,
    damage_coop_party_from_enemy,
    initialize_coop_combat,
    validate_coop_combat_state,
)


COOP_INTRO_COMBAT_ID = 'garden-intro-001'
COOP_INTRO_ENCOUNTER_ID = 'garden_soldier_ant'
COOP_INTRO_ENEMY_DEF_ID = 'coop_soldier_ant_scout'
COOP_INTRO_ENEMY_NAME = {'zh': '兵蚁侦察兵', 'en': 'Soldier Ant Scout'}
COOP_SECOND_ENCOUNTER_ID = 'garden_thorn_beetle_pair'
COOP_SECOND_ENEMY_DEF_ID = 'coop_thorn_beetle'
COOP_DEMO_MAX_ENCOUNTERS = 2
COOP_LEGACY_CONTENT_VERSION = STORY_CONTENT_VERSION
COOP_STAGE1_REST_CONTENT_VERSION = f'{STORY_CONTENT_VERSION}-coop-stage1-rest-1'
COOP_STAGE1_GARDEN_V1_CONTENT_VERSION = f'{STORY_CONTENT_VERSION}-coop-stage1-garden-1'
COOP_STAGE1_OPENING_V1_CONTENT_VERSION = f'{STORY_CONTENT_VERSION}-coop-stage1-garden-opening-1'
COOP_SHARED_CONTENT_VERSION_RE = re.compile(
    r'[A-Za-z0-9._:-]+-coop-(?:stage1-shared-content|full-journey)-1-[0-9a-f]{12}'
)
COOP_STAGE1_CONTRACT_VERSION = 3
COOP_STAGE1_MAX_FLOOR = 16
COOP_STAGE1_DIFFICULTIES = ('normal', 'hard', 'lunatic')
COOP_STAGE1_SUPPORTED_NODE_TYPES = frozenset({
    'combat',
    'elite',
    'rest',
    'chest',
    'shop',
    'event',
    'boss',
})
COOP_GARDEN_EVENT_ID = 'coop_garden_crossroads'
COOP_GARDEN_EVENT_OPTIONS = ('mend', 'supplies', 'risk')
COOP_STORY_STAGES = {
    1: {
        'biome': 'garden',
        'name': {'zh': '花园', 'en': 'Garden'},
        'complete_title': {'zh': '花园阶段完成', 'en': 'Garden Stage Complete'},
    },
    2: {
        'biome': 'jungle',
        'name': {'zh': '丛林', 'en': 'Jungle'},
        'complete_title': {'zh': '丛林阶段完成', 'en': 'Jungle Stage Complete'},
    },
    3: {
        'biome': 'factory',
        'name': {'zh': '工厂', 'en': 'Factory'},
        'complete_title': {'zh': '神秘人物', 'en': 'Mysterious Person'},
    },
}
COOP_FINAL_STAGE = max(COOP_STORY_STAGES)
COOP_ADAPTED_EVENT_DEFINITIONS = {
    'jungle': {
        'id': 'coop_jungle_waystation',
        'title': {'zh': '藤蔓驿站', 'en': 'Vine Waystation'},
        'description': {
            'zh': '潮湿的驿站里还留着一些可共同使用的补给。',
            'en': 'A damp waystation still holds supplies the party can share.',
        },
        'speaker': {'zh': '藤蔓驿站', 'en': 'Vine Waystation'},
        'portrait': 'jungle',
        'biomes': ('jungle',),
        'modes': ('coop',),
        'coop': {
            'enabled': True,
            'policy': 'unanimous_required',
            'effect_scope': 'all_players',
        },
        'options': (
            {
                'id': 'rest',
                'label': {'zh': '整顿队伍', 'en': 'Regroup'},
                'description': {'zh': '团队每位成员回复18H。', 'en': 'Each member recovers 18 H.'},
                'effects': ({'type': 'heal', 'amount': 18},),
            },
            {
                'id': 'forage',
                'label': {'zh': '搜寻物资', 'en': 'Forage'},
                'description': {'zh': '团队每位成员获得38G。', 'en': 'Each member gains 38 G.'},
                'effects': ({'type': 'gold', 'amount': 38},),
            },
        ),
    },
    'factory': {
        'id': 'coop_factory_salvage',
        'title': {'zh': '废料传送带', 'en': 'Salvage Conveyor'},
        'description': {
            'zh': '停摆的传送带上散落着还能使用的零件。',
            'en': 'Useful parts remain scattered across a stalled conveyor.',
        },
        'speaker': {'zh': '废料传送带', 'en': 'Salvage Conveyor'},
        'portrait': 'factory',
        'biomes': ('factory',),
        'modes': ('coop',),
        'coop': {
            'enabled': True,
            'policy': 'unanimous_required',
            'effect_scope': 'all_players',
        },
        'options': (
            {
                'id': 'repair',
                'label': {'zh': '修复护具', 'en': 'Repair Gear'},
                'description': {'zh': '团队每位成员回复20H。', 'en': 'Each member recovers 20 H.'},
                'effects': ({'type': 'heal', 'amount': 20},),
            },
            {
                'id': 'salvage',
                'label': {'zh': '拆取零件', 'en': 'Salvage Parts'},
                'description': {'zh': '团队每位成员获得45G。', 'en': 'Each member gains 45 G.'},
                'effects': ({'type': 'gold', 'amount': 45},),
            },
        ),
    },
}
COOP_ADAPTED_ENCOUNTERS = {
    ('jungle', 'combat'): (
        'coop_jungle_patrol',
        ({'slug': 'termite-scout', 'def_id': 'coop_jungle_termite_scout',
          'name': {'zh': '协作白蚁斥候', 'en': 'Co-op Termite Scout'},
          'image_url': '/static/assets/story-enemies/soldier-termite.svg',
          'health': 62, 'intent': {'kind': 'attack', 'amount': 8, 'hits': 1}},),
    ),
    ('jungle', 'elite'): (
        'coop_jungle_elite',
        ({'slug': 'canopy-stalker', 'def_id': 'coop_canopy_stalker',
          'name': {'zh': '协作树冠猎手', 'en': 'Co-op Canopy Stalker'},
          'image_url': '/static/assets/story-enemies/stickbug.svg',
          'health': 150, 'intent': {'kind': 'attack', 'amount': 12, 'hits': 1}},),
    ),
    ('jungle', 'boss'): (
        'coop_jungle_boss',
        ({'slug': 'centipede-warden', 'def_id': 'coop_centipede_warden',
          'name': {'zh': '协作百足守卫', 'en': 'Co-op Centipede Warden'},
          'image_url': '/static/assets/story-enemies/evil-centipede-head.svg',
          'health': 270, 'intent': {'kind': 'attack_all', 'amount': 10, 'hits': 1}},),
    ),
    ('factory', 'combat'): (
        'coop_factory_patrol',
        ({'slug': 'mechanical-crab', 'def_id': 'coop_mechanical_crab_sentry',
          'name': {'zh': '协作机械蟹哨兵', 'en': 'Co-op Mechanical Crab Sentry'},
          'image_url': '/static/assets/story-enemies/mechanical-crab.svg',
          'health': 190, 'intent': {'kind': 'attack', 'amount': 13, 'hits': 1}},),
    ),
    ('factory', 'elite'): (
        'coop_factory_elite',
        ({'slug': 'mechanical-wasp', 'def_id': 'coop_mechanical_wasp_guard',
          'name': {'zh': '协作机械蜂守卫', 'en': 'Co-op Mechanical Wasp Guard'},
          'image_url': '/static/assets/story-enemies/mechanical-wasp.svg',
          'health': 245, 'intent': {'kind': 'attack_all', 'amount': 11, 'hits': 1}},),
    ),
    ('factory', 'boss'): (
        'coop_factory_boss',
        ({'slug': 'mechanical-flower', 'def_id': 'coop_mechanical_flower_core',
          'name': {'zh': '协作机械花核心', 'en': 'Co-op Mechanical Flower Core'},
          'image_url': '/static/assets/story-enemies/mechanical-flower.svg',
          'health': 480, 'intent': {'kind': 'attack_all', 'amount': 15, 'hits': 1}},),
    ),
}
_COOP_ADAPTED_MANIFEST = {
    'events': COOP_ADAPTED_EVENT_DEFINITIONS,
    'encounters': {
        f'{biome}:{room_type}': value
        for (biome, room_type), value in COOP_ADAPTED_ENCOUNTERS.items()
    },
}
COOP_FULL_JOURNEY_FINGERPRINT = hashlib.sha256(
    (
        COOP_CONTENT_FINGERPRINT
        + json.dumps(
            _COOP_ADAPTED_MANIFEST,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(',', ':'),
        )
    ).encode('utf-8')
).hexdigest()
COOP_STORY_CONTENT_VERSION = (
    f'{STORY_CONTENT_VERSION}-coop-full-journey-1-'
    f'{COOP_FULL_JOURNEY_FINGERPRINT[:12]}'
)
COOP_STAGE1_OPENING_CONTENT_VERSIONS = frozenset({
    COOP_STAGE1_OPENING_V1_CONTENT_VERSION,
    COOP_STORY_CONTENT_VERSION,
})
COOP_STAGE1_CONTENT_VERSIONS = frozenset({
    COOP_STAGE1_REST_CONTENT_VERSION,
    COOP_STAGE1_GARDEN_V1_CONTENT_VERSION,
    *COOP_STAGE1_OPENING_CONTENT_VERSIONS,
})
COOP_LEGACY_GARDEN_EVENT_DEFINITION = {
    'title': {'zh': '岔路上的园丁车', 'en': "Gardener's Cart"},
    'description': {
        'zh': '一辆废弃园丁车挡在路边。你们必须共同决定如何利用剩余物资。',
        'en': 'An abandoned gardener cart offers one shared choice.',
    },
    'coop': {
        'policy': 'unanimous_then_seeded_random',
        'effect_scope': 'all_players',
    },
    'options': [
        {
            'id': 'mend',
            'label': {'zh': '修整工具', 'en': 'Mend the Tools'},
            'description': {'zh': '团队每位成员回复15H。', 'en': 'Each member recovers 15 H.'},
            'effects': [{'type': 'heal', 'amount': 15}],
        },
        {
            'id': 'supplies',
            'label': {'zh': '搜集物资', 'en': 'Gather Supplies'},
            'description': {'zh': '团队每位成员获得30G。', 'en': 'Each member gains 30 G.'},
            'effects': [{'type': 'gold', 'amount': 30}],
        },
        {
            'id': 'risk',
            'label': {'zh': '冒险拆解', 'en': 'Risky Salvage'},
            'description': {
                'zh': '团队每位成员失去8H（最低保留1H），并获得60G。',
                'en': 'Each member loses 8 H, but not below 1 H, and gains 60 G.',
            },
            'effects': [
                {'type': 'health_loss', 'amount': 8, 'nonlethal': True},
                {'type': 'gold', 'amount': 60},
            ],
            'requires_confirmation': True,
            'risky': True,
        },
    ],
}
COOP_REWARD_GOLD = 15
COOP_CANONICAL_ENEMY_HEALTH_NUMERATOR = 3
COOP_CANONICAL_ENEMY_HEALTH_DENOMINATOR = 2
# Compatibility name retained for tests and older imports.  The live adapter
# now supports the compiled Garden-stage catalog rather than only starters.
COOP_INTRO_SUPPORTED_CARDS = COOP_SUPPORTED_CARD_IDS
COOP_COMBAT_PUBLIC_RUN_FIELDS = (
    'id',
    'party_id',
    'status',
    'schema_version',
    'content_version',
    'revision',
    'created_at',
    'updated_at',
    'completed_at',
)


def _fail(code, message):
    raise CoopCombatError(code, message)


def _is_shared_content_version(content_version):
    return bool(COOP_SHARED_CONTENT_VERSION_RE.fullmatch(str(content_version or '')))


def _is_opening_content_version(content_version):
    return (
        str(content_version or '') in COOP_STAGE1_OPENING_CONTENT_VERSIONS
        or _is_shared_content_version(content_version)
    )


def _strict_nonnegative_int(value, *, code, label):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _fail(code, f'{label}必须是非负整数')
    return value


def _card_instance_id(card):
    instance_id = str((card or {}).get('instance_id') or '').strip()
    if not instance_id or len(instance_id) > 128:
        _fail('INVALID_CARD_INSTANCE_ID', '卡牌实例标识无效')
    return instance_id


def _card_values(card):
    if not isinstance(card, dict):
        _fail('INVALID_CARD_STATE', '卡牌状态无效')
    def_id = str(card.get('def_id') or '').strip().lower()
    if def_id not in COOP_SUPPORTED_CARD_IDS:
        _fail('UNSUPPORTED_COOP_CARD', f'当前协作章节暂不支持卡牌 {def_id or "?"}')
    definition = COOP_STORY_CONTENT.card_definition(def_id)
    if not isinstance(definition, dict):
        _fail('UNSUPPORTED_COOP_CARD', f'未找到卡牌 {def_id}')
    values = deepcopy(definition)
    upgrade_level = card.get('upgrade_level', 0)
    _strict_nonnegative_int(
        upgrade_level,
        code='INVALID_CARD_STATE',
        label='卡牌升级等级',
    )
    if card.get('upgraded') or upgrade_level > 0:
        values.update(deepcopy(definition.get('upgrade') or {}))
    effects = values.get('effects')
    if not isinstance(effects, (list, tuple)):
        _fail('UNSUPPORTED_COOP_CARD', f'卡牌 {def_id} 缺少可执行效果')
    allowed_effects = {
        'damage', 'shield', 'active_discard', 'draw', 'elixir',
        'heal', 'magic', 'electric_damage',
    }
    if any(str((effect or {}).get('type') or '') not in allowed_effects for effect in effects):
        _fail('UNSUPPORTED_COOP_CARD', f'卡牌 {def_id} 尚未接入协作首战')
    cost_e = values.get('cost_e', 0)
    cost_m = values.get('cost_m', 0)
    _strict_nonnegative_int(cost_e, code='INVALID_CARD_COST', label='卡牌灵药费用')
    _strict_nonnegative_int(cost_m, code='INVALID_CARD_COST', label='卡牌魔法费用')
    values['effects'] = [deepcopy(effect) for effect in effects]
    modifiers = card.get('modifiers') if isinstance(card.get('modifiers'), dict) else {}
    if modifiers:
        values['cost_e'] = max(
            0,
            int(values.get('cost_e') or 0)
            + int(modifiers.get('cost_e_delta') or 0)
            - int(modifiers.get('swift') or 0),
        )
        values['cost_m'] = max(
            0,
            int(values.get('cost_m') or 0)
            + int(modifiers.get('cost_m_delta') or 0)
            - int(modifiers.get('magic_swift') or 0),
        )
        damage_bonus = int(modifiers.get('damage_bonus') or 0)
        shield_bonus = int(modifiers.get('enchantment_shield_bonus_once') or 0)
        for effect in values['effects']:
            if effect.get('type') in {'damage', 'electric_damage'} and damage_bonus:
                effect['amount'] = max(0, int(effect.get('amount') or 0) + damage_bonus)
            if effect.get('type') == 'shield' and shield_bonus:
                effect['amount'] = max(0, int(effect.get('amount') or 0) + shield_bonus)
        tags = set(str(tag) for tag in values.get('tags') or ())
        if modifiers.get('remove_exile'):
            tags.discard('exile')
            tags.discard('void')
        if modifiers.get('force_exile'):
            tags.add('exile')
        if modifiers.get('force_void'):
            tags.add('void')
        if modifiers.get('retain'):
            tags.add('retain')
        tags.update(str(tag) for tag in modifiers.get('extra_tags') or ())
        values['tags'] = sorted(tags)
    return def_id, values


def _validate_persisted_card(card, content_version):
    """Validate old read-only cards without reinterpreting them as new content."""

    if str(content_version or '') == COOP_STORY_CONTENT_VERSION:
        _card_values(card)
        return
    if not isinstance(card, dict):
        _fail('INVALID_CARD_STATE', '卡牌状态无效')
    _card_instance_id(card)
    def_id = str(card.get('def_id') or '').strip().lower()
    if not re.fullmatch(r'[a-z0-9][a-z0-9._:-]{0,127}', def_id):
        _fail('INVALID_CARD_STATE', '卡牌定义标识无效')
    upgraded = card.get('upgraded', False)
    upgrade_level = card.get('upgrade_level', 0)
    if not isinstance(upgraded, bool):
        _fail('INVALID_CARD_STATE', '卡牌升级状态无效')
    _strict_nonnegative_int(
        upgrade_level,
        code='INVALID_CARD_STATE',
        label='卡牌升级等级',
    )


def _coop_book_instance(state, seat, instance_id):
    player = state.get('players', {}).get(str(seat)) or {}
    return next((
        item for item in player.get('enchantment_books') or []
        if str((item or {}).get('instance_id') or '') == str(instance_id or '')
    ), None)


def _remove_coop_enchantment_book(state, seat, instance_id, events, reason):
    player = state['players'][str(seat)]
    books = player.setdefault('enchantment_books', [])
    book = _coop_book_instance(state, seat, instance_id)
    if book is None:
        _fail('INVALID_ENCHANTMENT_BOOK', '未持有该附魔书')
    books.remove(book)
    events.append({
        'type': 'coop_enchantment_book_removed',
        'actor_seat': int(seat),
        'book_id': book['book_id'],
        'book_instance_id': book['instance_id'],
        'reason': str(reason or 'used'),
    })
    return book


def _gain_coop_enchantment_book(
        state, seat, book_id, events, *, source, replace_instance_id=''):
    book_id = str(book_id or '')
    if book_id not in STORY_ENCHANTMENT_BOOKS:
        _fail('UNKNOWN_ENCHANTMENT_BOOK', '未知附魔书')
    player = state['players'][str(seat)]
    books = player.setdefault('enchantment_books', [])
    if len(books) >= int(STORY_RULES['enchantment_book_slots']):
        replacement = _coop_book_instance(state, seat, replace_instance_id)
        if replacement is None:
            _fail('ENCHANTMENT_BOOK_SLOTS_FULL', '附魔书槽已满，请选择要替换的附魔书')
        _remove_coop_enchantment_book(
            state,
            seat,
            replacement['instance_id'],
            events,
            'replaced',
        )
    serial = max(1, int(player.get('next_enchantment_book_serial') or 1))
    player['next_enchantment_book_serial'] = serial + 1
    book = {'instance_id': f'coop-seb-{int(seat)}-{serial:05d}', 'book_id': book_id}
    books.append(book)
    events.append({
        'type': 'coop_enchantment_book_gained',
        'actor_seat': int(seat),
        'book_id': book_id,
        'book_instance_id': book['instance_id'],
        'source': str(source or 'reward'),
    })
    return book


def _coop_enchantment_selected_cards(state, seat, payload, target_kind):
    seat_state = state['combat']['seat_states'][str(seat)]
    raw_ids = payload.get('selected_card_ids')
    if raw_ids is None and payload.get('card_instance_id'):
        raw_ids = [payload.get('card_instance_id')]
    if isinstance(raw_ids, str):
        raw_ids = [raw_ids]
    if not isinstance(raw_ids, list):
        raw_ids = []
    selected = []
    for instance_id in dict.fromkeys(str(item or '') for item in raw_ids if str(item or '')):
        card = next((
            item for item in seat_state.get('hand') or []
            if _card_instance_id(item) == instance_id
        ), None)
        if card is None:
            _fail('INVALID_ENCHANTMENT_CARD', '所选卡牌不在你的手牌中')
        selected.append(card)
    minimum = 3 if target_kind == 'three_cards' else (0 if target_kind == 'any_cards' else 1)
    maximum = len(seat_state.get('hand') or []) if target_kind == 'any_cards' else minimum
    if not minimum <= len(selected) <= maximum:
        _fail('ENCHANTMENT_CARD_SELECTION_REQUIRED', f'请选择{minimum}至{maximum}张手牌')
    if selected:
        _, values = _card_values(selected[0])
        tags = set(values.get('tags') or ())
        if target_kind == 'attack_card' and values.get('type') != 'thorn':
            _fail('INVALID_ENCHANTMENT_CARD_TYPE', '请选择攻击牌')
        if target_kind == 'skill_card' and values.get('type') != 'bloom':
            _fail('INVALID_ENCHANTMENT_CARD_TYPE', '请选择技能牌')
        if target_kind == 'exile_card' and 'exile' not in tags:
            _fail('INVALID_ENCHANTMENT_CARD_TYPE', '请选择具有放逐的牌')
        if target_kind == 'cost_card' and (
            int(values.get('cost_e') or 0) + int(values.get('cost_m') or 0) <= 0
        ):
            _fail('INVALID_ENCHANTMENT_CARD_TYPE', '请选择非0E0M牌')
    return selected


def _resolve_coop_enchantment_book_action(
        state, actor_seat, action_type, payload, run_seed, events):
    if action_type in {'discard_enchantment_book', 'discard_combat_enchantment_book'}:
        if set(payload) - {'book_instance_id'}:
            _fail('INVALID_ACTION_PAYLOAD', '丢弃附魔书包含不支持的字段')
        _remove_coop_enchantment_book(
            state,
            actor_seat,
            payload.get('book_instance_id'),
            events,
            'discarded',
        )
        return
    allowed = {
        'book_instance_id', 'selected_card_ids', 'card_instance_id',
        'target_book_instance_id',
    }
    if set(payload) - allowed:
        _fail('INVALID_ACTION_PAYLOAD', '使用附魔书包含不支持的字段')
    combat = state.get('combat') or {}
    if state.get('phase') != 'combat' or combat.get('turn') != COOP_COMBAT_HERO_TURN:
        _fail('ENCHANTMENT_BOOK_ACTION_NOT_ALLOWED', '当前不能使用附魔书')
    book = _coop_book_instance(state, actor_seat, payload.get('book_instance_id'))
    if book is None:
        _fail('INVALID_ENCHANTMENT_BOOK', '未持有该附魔书')
    definition = STORY_ENCHANTMENT_BOOKS[book['book_id']]
    character_id = str(state['players'][str(actor_seat)].get('character_id') or '')
    if definition.get('character_id') and definition['character_id'] != character_id:
        _fail('ENCHANTMENT_BOOK_CHARACTER_RESTRICTED', '当前角色无法使用该附魔书')
    script = str(definition.get('script') or '')
    if script == 'lethal_guard':
        _fail('ENCHANTMENT_BOOK_AUTOMATIC', '魔法世界树之叶会自动触发')
    if script == 'escape':
        node = _coop_map_nodes(state).get(str(state.get('current_node_id') or '')) or {}
        if node.get('type') == 'boss':
            _fail('BOSS_ESCAPE_FORBIDDEN', '无法逃离首领战')
        _remove_coop_enchantment_book(state, actor_seat, book['instance_id'], events, 'used')
        player = state['players'][str(actor_seat)]
        player['health'] = max(1, int(player.get('health') or 0) - int(definition.get('amount') or 0))
        combat['escaped_without_reward'] = True
        for enemy in combat.get('enemies') or []:
            enemy['health'] = 0
        events.append({'type': 'coop_combat_escaped', 'actor_seat': int(actor_seat)})
        return
    if script == 'copy_book':
        target = _coop_book_instance(state, actor_seat, payload.get('target_book_instance_id'))
        if target is None or target is book:
            _fail('ENCHANTMENT_BOOK_TARGET_REQUIRED', '请选择另一本要复制的附魔书')
        copied_id = target['book_id']
        _remove_coop_enchantment_book(state, actor_seat, book['instance_id'], events, 'used')
        _gain_coop_enchantment_book(
            state,
            actor_seat,
            copied_id,
            events,
            source='unlimited',
        )
        return
    selected = _coop_enchantment_selected_cards(
        state,
        actor_seat,
        payload,
        definition.get('target'),
    )
    amount = max(0, int(definition.get('amount') or 0))
    one_shot_keys = {
        'draw_to_full_once': 'enchantment_draw_to_full_once',
        'disc_once': 'enchantment_disc_once',
        'fire_on_hit_once': 'enchantment_fire_on_hit_once',
        'immunity_once': 'enchantment_immunity_once',
        'repeat_on_kill': 'enchantment_repeat_on_kill',
        'weak_once': 'enchantment_weak_once',
        'double_reward_on_kill': 'enchantment_double_reward_on_kill',
        'repeat_once': 'enchantment_repeat_once',
        'power_once': 'enchantment_power_once',
        'impact_once': 'enchantment_impact_once',
        'retrieve_once': 'enchantment_retrieve_once',
        'reflection_once': 'enchantment_reflection_once',
        'vulnerable_once': 'enchantment_vulnerable_once',
    }
    for card in selected:
        modifiers = card.setdefault('modifiers', {})
        if script == 'damage_bonus':
            modifiers['damage_bonus'] = int(modifiers.get('damage_bonus') or 0) + amount
        elif script == 'shield_bonus_once':
            modifiers['enchantment_shield_bonus_once'] = int(modifiers.get('enchantment_shield_bonus_once') or 0) + amount
        elif script == 'remove_exile':
            modifiers['remove_exile'] = True
        elif script == 'swift':
            modifiers['swift'] = int(modifiers.get('swift') or 0) + amount
        elif script == 'temporary_swift':
            modifiers['swift'] = int(modifiers.get('swift') or 0) + amount
            modifiers['temporary_swift'] = int(modifiers.get('temporary_swift') or 0) + amount
        elif script == 'wide':
            modifiers['extra_tags'] = sorted(set(modifiers.get('extra_tags') or ()) | {'wide'})
        elif script == 'armor_break':
            modifiers['enchantment_armor_break'] = True
        elif script == 'electric_damage':
            modifiers['enchantment_electric_damage'] = int(modifiers.get('enchantment_electric_damage') or 0) + amount
        elif script == 'retain':
            modifiers['retain'] = True
        elif script == 'exile_void':
            modifiers['force_exile'] = True
            modifiers['force_void'] = True
        elif script == 'dense':
            modifiers['damage_bonus'] = int(modifiers.get('damage_bonus') or 0) + amount
            modifiers['cost_e_delta'] = int(modifiers.get('cost_e_delta') or 0) + 1
            modifiers['temporary_heavy'] = int(modifiers.get('temporary_heavy') or 0) + 1
        elif script == 'health_cost':
            _, values = _card_values(card)
            key = 'cost_e_delta' if int(values.get('cost_e') or 0) > 0 else 'cost_m_delta'
            modifiers[key] = int(modifiers.get(key) or 0) - 1
            modifiers['enchantment_health_cost'] = int(modifiers.get('enchantment_health_cost') or 0) + amount
        elif script == 'rebound':
            modifiers['enchantment_rebound'] = True
        elif script in one_shot_keys:
            modifiers[one_shot_keys[script]] = max(1, amount) if amount else True
    _remove_coop_enchantment_book(state, actor_seat, book['instance_id'], events, 'used')
    events.append({
        'type': 'coop_enchantment_book_used',
        'actor_seat': int(actor_seat),
        'book_id': book['book_id'],
        'book_instance_id': book['instance_id'],
        'card_instance_ids': [_card_instance_id(card) for card in selected],
    })


def _compiled_pool_contains(state, card_id, pool):
    content_version = str((state or {}).get('content_version') or '')
    if _is_shared_content_version(content_version) and content_version != COOP_STORY_CONTENT_VERSION:
        return bool(re.fullmatch(r'[a-z0-9][a-z0-9._:-]{0,127}', str(card_id or '')))
    return str(card_id or '') in pool


def _deterministic_shuffle(state, cards, run_seed, namespace):
    streams = state.setdefault('rng_streams', {})
    if not isinstance(streams, dict):
        _fail('INVALID_RNG_STATE', '故事随机流状态无效')
    counter = streams.get(namespace, 0)
    _strict_nonnegative_int(counter, code='INVALID_RNG_STATE', label='随机流计数')
    streams[namespace] = counter + 1
    decorated = []
    for index, card in enumerate(cards):
        instance_id = _card_instance_id(card)
        material = (
            f'{run_seed}|{namespace}|{counter}|{index}|{instance_id}'
        ).encode('utf-8')
        decorated.append((hashlib.sha256(material).digest(), index, deepcopy(card)))
    decorated.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in decorated]


def _draw_cards(state, seat, run_seed, count, events):
    seat_key = str(seat)
    seat_state = state['combat']['seat_states'][seat_key]
    hand = seat_state['hand']
    drawn = []
    hand_limit = max(0, int(STORY_RULES['hand_limit']))
    requested = max(0, int(count))
    while len(drawn) < requested and len(hand) < hand_limit:
        if not seat_state['draw_pile']:
            if not seat_state['discard_pile']:
                break
            namespace = f'coop_intro_shuffle:{state["combat"]["id"]}:{seat}'
            seat_state['draw_pile'] = _deterministic_shuffle(
                state,
                seat_state['discard_pile'],
                run_seed,
                namespace,
            )
            seat_state['discard_pile'] = []
            events.append({
                'type': 'coop_discard_shuffled',
                'actor_seat': seat,
                'draw_count': len(seat_state['draw_pile']),
            })
        card = seat_state['draw_pile'].pop(0)
        hand.append(card)
        drawn.append(_card_instance_id(card))
    if drawn:
        events.append({
            'type': 'coop_cards_drawn',
            'actor_seat': seat,
            'card_instance_ids': drawn,
            'count': len(drawn),
        })


def _intro_seat_states(state, run_seed, combat_id=COOP_INTRO_COMBAT_ID):
    seat_states = {}
    for seat_key in sorted(state['players'], key=int):
        seat = int(seat_key)
        player = state['players'][seat_key]
        opening_magic = sum(
            max(0, int(definition.get('amount') or 0))
            for _, definition in _compiled_player_relics(player, 'turn_magic')
        )
        deck = deepcopy(player.get('deck') or [])
        for index, card in enumerate(deck):
            original_id = _card_instance_id(card)
            stable_suffix = hashlib.sha256(
                f'{run_seed}|{combat_id}|{seat}|{index}|{original_id}'.encode('utf-8')
            ).hexdigest()[:20]
            card['instance_id'] = f'coop-{seat}-{index}-{stable_suffix}'
            _card_values(card)
        shuffled = _deterministic_shuffle(
            state,
            deck,
            run_seed,
            f'coop_opening:{combat_id}:{seat}',
        )
        seat_states[seat_key] = {
            'elixir': max(0, int(player.get('max_elixir') or player.get('elixir') or 0)),
            'magic': story_combat_starting_magic(player) + opening_magic,
            'shield': 0,
            'statuses': {},
            'hand': shuffled[:int(STORY_RULES['draw_per_turn'])],
            'draw_pile': shuffled[int(STORY_RULES['draw_per_turn']):],
            'discard_pile': [],
            'exile_pile': [],
            'equipment': [],
        }
    return seat_states


def _coop_opening_room_id(state):
    return f'opening:{str(state.get("current_node_id") or "").strip()}:blessing'


def _coop_opening_options_for_seat(state, seat, run_seed):
    stage = int(state.get('stage') or 1)
    return _deterministic_value_order(
        state,
        COOP_OPENING_BLESSING_IDS,
        str(run_seed),
        f'coop_opening_blessing:stage:{stage}:seat:{int(seat)}',
    )[:3]


def _coop_stage_definition(stage):
    try:
        stage = int(stage)
    except (TypeError, ValueError):
        _fail('INVALID_COOP_STAGE', '协作旅程阶段无效')
    definition = COOP_STORY_STAGES.get(stage)
    if definition is None:
        _fail('INVALID_COOP_STAGE', '协作旅程阶段无效')
    return stage, definition


def _start_coop_stage_opening(state, *, run_seed, stage):
    """Enter one deterministic stage and create its private blessing barrier."""

    stage, definition = _coop_stage_definition(stage)
    biome = str(definition['biome'])
    state['stage'] = stage
    state['biome'] = biome
    state['map'] = generate_story_map(
        str(run_seed),
        stage=stage,
        biome=biome,
        difficulty=str(state.get('difficulty') or 'normal'),
    )
    first = state['map']['floors'][0]['nodes'][0]
    state['current_floor'] = 1
    state['current_node_id'] = str(first['id'])
    state['phase'] = 'room'
    state['completed'] = False
    state['combat'] = None
    state['last_combat'] = None
    state['shared_reward'] = None
    state['rewards_by_player'] = None
    progression = state.setdefault('coop_progression', {})
    completed_stages = progression.get('completed_stages') or []
    progression.update({
        'contract_version': COOP_STAGE1_CONTRACT_VERSION,
        'chapter': stage,
        'encounter_index': 0,
        'max_floor': int(state['map']['floor_count']),
        'completed_combat_ids': [],
        'completed_node_ids': [],
        'completed_stages': list(completed_stages),
    })
    room_id = _coop_opening_room_id(state)
    state['room'] = {
        'id': room_id,
        'type': 'opening',
        'node_id': str(first['id']),
        'stage': 'blessing',
        'journey_stage': stage,
        'title': {
            'zh': f'第{stage}阶段：选择个人开局赐福',
            'en': f'Stage {stage}: Choose a Personal Starting Blessing',
        },
        'description': {
            'zh': f'进入{definition["name"]["zh"]}前，两名成员分别选择一项赐福。',
            'en': f'Each member chooses a blessing before entering {definition["name"]["en"]}.',
        },
        'policy': 'per_player_private_barrier',
    }
    state['room_states_by_player'] = {
        seat_key: {
            'status': 'pending',
            'stage': 'blessing',
            'options': _coop_opening_options_for_seat(state, int(seat_key), str(run_seed)),
            'selected_option': None,
        }
        for seat_key in sorted(state['players'], key=int)
    }
    state['coordination']['combat_ready_seats'] = []
    state['coordination']['combat_ready_round'] = None
    state['coordination']['map_vote'] = None
    state['coordination']['room_decision'] = {
        'decision_id': room_id,
        'room_id': room_id,
        'policy': 'per_player_private_barrier',
        'resolved_seats': [],
    }
    return [{
        'type': 'coop_opening_started',
        'stage': stage,
        'count': len(state['players']),
    }]


def prepare_coop_stage1_setup(source_state, *, available_difficulties=None):
    """Version a newly-created run for the leader-owned difficulty action."""

    validate_story_state_v10(source_state, expected_mode='coop')
    if source_state.get('phase') != 'journey_setup':
        _fail('COOP_SETUP_NOT_AVAILABLE', '当前旅程不能进入协作开局设置')
    state = deepcopy(source_state)
    state['content_version'] = COOP_STORY_CONTENT_VERSION
    state['completed'] = False
    state['combat'] = None
    state['last_combat'] = None
    state['shared_reward'] = None
    state['rewards_by_player'] = None
    state['room_states_by_player'] = None
    state['coop_progression'] = {
        'contract_version': COOP_STAGE1_CONTRACT_VERSION,
        'chapter': 1,
        'encounter_index': 0,
        'max_floor': int((state.get('map') or {}).get('floor_count') or COOP_STAGE1_MAX_FLOOR),
        'completed_combat_ids': [],
        'completed_node_ids': [],
        'completed_stages': [],
    }
    if available_difficulties is None:
        difficulties = list(COOP_STAGE1_DIFFICULTIES)
    else:
        requested = {
            str(difficulty or '').strip().lower()
            for difficulty in available_difficulties
        }
        difficulties = [
            difficulty
            for difficulty in COOP_STAGE1_DIFFICULTIES
            if difficulty in requested
        ]
    if not difficulties:
        _fail('NO_SHARED_COOP_DIFFICULTY', '队伍成员没有共同可用的协作难度')
    state['room'] = {
        'type': 'journey_setup',
        'stage': 1,
        'biomes': ['garden'],
        'difficulties': difficulties,
        'modes': ['standard'],
        'title': {'zh': '协作旅程设置', 'en': 'Cooperative Journey Setup'},
        'description': {
            'zh': '由队长选择花园第一阶段难度。',
            'en': 'The leader chooses the Garden stage-one difficulty.',
        },
    }
    state['coordination']['combat_ready_seats'] = []
    state['coordination']['combat_ready_round'] = None
    state['coordination']['map_vote'] = None
    state['coordination']['room_decision'] = None
    state['last_events'] = []
    validate_coop_live_state(state)
    return state


def start_coop_stage1_opening(source_state, *, run_seed, difficulty='normal'):
    """Create the private two-seat blessing barrier before the first route vote.

    Easy remains fail-closed until all five per-seat Easy talents are implemented
    by the cooperative combat adapter.  Normal, Hard and Lunatic use the shared
    single-player map generator; later combat/reward adapters apply the supported
    cooperative difficulty modifiers.
    """

    validate_story_state_v10(source_state, expected_mode='coop')
    if source_state.get('phase') != 'journey_setup':
        _fail('COOP_OPENING_NOT_AVAILABLE', '当前旅程不能重新选择协作开局')
    difficulty = str(difficulty or '').strip().lower()
    if difficulty not in COOP_STAGE1_DIFFICULTIES:
        _fail('UNSUPPORTED_COOP_DIFFICULTY', '当前协作版本仅支持普通、困难或疯狂难度')

    state = deepcopy(source_state)
    state['content_version'] = COOP_STORY_CONTENT_VERSION
    state['difficulty'] = difficulty
    state['journey_mode'] = 'standard'
    state['completed_stage'] = None
    state['coop_progression'] = {
        'contract_version': COOP_STAGE1_CONTRACT_VERSION,
        'chapter': 1,
        'encounter_index': 0,
        'max_floor': COOP_STAGE1_MAX_FLOOR,
        'completed_combat_ids': [],
        'completed_node_ids': [],
        'completed_stages': [],
    }
    events = _start_coop_stage_opening(
        state,
        run_seed=str(run_seed),
        stage=1,
    )
    events = [{
        **event,
        'action_sequence': 0,
        'event_index': index,
    } for index, event in enumerate(events)]
    state['last_events'] = deepcopy(events)
    validate_coop_live_state(state)
    return state, events


def start_intro_coop_combat(source_state, *, run_seed):
    """Turn a freshly-created v10 run into the deterministic playable intro."""

    validate_story_state_v10(source_state, expected_mode='coop')
    if source_state.get('phase') != 'journey_setup':
        _fail('COOP_INTRO_NOT_AVAILABLE', '当前旅程不能进入协作首战')
    staging = deepcopy(source_state)
    staging['content_version'] = COOP_STAGE1_GARDEN_V1_CONTENT_VERSION
    # Fail closed if a future map generator adds a node that the current
    # Garden-stage dispatcher does not yet understand.  The known stage-one
    # combat, elite, rest, chest, shop, event and boss nodes remain intact.
    for floor in (staging.get('map') or {}).get('floors') or []:
        for node in floor.get('nodes') or []:
            node_type = str(node.get('type') or '')
            if int(node.get('floor') or 0) <= 1:
                continue
            if node_type not in COOP_STAGE1_SUPPORTED_NODE_TYPES:
                node['type'] = 'combat'
    seat_states = _intro_seat_states(staging, str(run_seed))
    enemy = {
        'id': 'intro-soldier-ant',
        # This is a deliberately simplified teaching encounter, not the full
        # single-player Soldier Ant move set.  A distinct id prevents clients
        # from presenting the 56H production enemy as if its rules were equal.
        'def_id': COOP_INTRO_ENEMY_DEF_ID,
        'name': deepcopy(COOP_INTRO_ENEMY_NAME),
        'health': 72,
        'max_health': 72,
        'intent': {'kind': 'attack', 'amount': 8, 'hits': 1},
    }
    state, events = initialize_coop_combat(
        staging,
        combat_id=COOP_INTRO_COMBAT_ID,
        enemies=[enemy],
        run_seed=str(run_seed),
        seat_states=seat_states,
    )
    state['combat']['encounter_id'] = COOP_INTRO_ENCOUNTER_ID
    state['coop_progression'] = {
        'contract_version': COOP_STAGE1_CONTRACT_VERSION,
        'chapter': 1,
        'encounter_index': 1,
        'max_floor': int((state.get('map') or {}).get('floor_count') or 16),
        'completed_combat_ids': [],
        'completed_node_ids': [],
        'completed_stages': [],
    }
    state['room_states_by_player'] = None
    state['room'] = {
        'type': 'combat',
        'encounter_id': COOP_INTRO_ENCOUNTER_ID,
        'title': {'zh': '协作首战', 'en': 'Cooperative First Battle'},
    }
    opening_events = list(events)
    for seat_key, seat_state in sorted(state['combat']['seat_states'].items(), key=lambda item: int(item[0])):
        opening_events.append({
            'type': 'coop_cards_drawn',
            'actor_seat': int(seat_key),
            'card_instance_ids': [_card_instance_id(card) for card in seat_state['hand']],
            'count': len(seat_state['hand']),
            'action_sequence': 0,
            'event_index': len(opening_events),
        })
    state['last_events'] = opening_events
    validate_coop_combat_state(state)
    return state, deepcopy(opening_events)


def resolve_intro_coop_action(
        state, actor_seat, action_type, payload, run_seed, events,
        *, _replay_card=None, _puncture_depth=0):
    """Resolve one trusted hero command for the curated Garden-stage deck."""

    replaying = _replay_card is not None
    if not replaying and action_type in {
        'use_enchantment_book', 'discard_combat_enchantment_book',
    }:
        if not isinstance(payload, dict):
            _fail('INVALID_ACTION_PAYLOAD', '协作战斗动作数据无效')
        _resolve_coop_enchantment_book_action(
            state,
            actor_seat,
            action_type,
            payload,
            str(run_seed),
            events,
        )
        return
    if action_type != 'play_card':
        _fail('UNSUPPORTED_COMBAT_ACTION', f'当前协作战斗暂不支持动作 {action_type}')
    if not isinstance(payload, dict):
        _fail('INVALID_ACTION_PAYLOAD', '协作战斗动作数据无效')
    allowed_keys = {
        'card_instance_id', 'target_enemy_id', 'discard_card_instance_ids',
        'retrieve_draw_card_id', 'retrieve_discard_card_id',
    }
    if set(payload) - allowed_keys:
        _fail('INVALID_ACTION_PAYLOAD', '协作出牌包含不支持的字段')
    seat_key = str(actor_seat)
    seat_state = state['combat']['seat_states'][seat_key]
    if replaying:
        card = _replay_card
        instance_id = _card_instance_id(card)
    else:
        instance_id = str(payload.get('card_instance_id') or '').strip()
        card = next(
            (item for item in seat_state['hand'] if _card_instance_id(item) == instance_id),
            None,
        )
        if card is None:
            _fail('CARD_NOT_IN_ACTOR_HAND', '行动席位手牌中不存在该牌')
    def_id, values = _card_values(card)
    modifiers = card.get('modifiers') if isinstance(card.get('modifiers'), dict) else {}
    health_cost = max(0, int(modifiers.get('enchantment_health_cost') or 0))
    player = state['players'][seat_key]
    if not replaying and (
        seat_state['elixir'] < values['cost_e']
        or seat_state['magic'] < values['cost_m']
        or int(player.get('health') or 0) <= health_cost
    ):
        _fail('INSUFFICIENT_CARD_RESOURCES', '没有足够的资源打出这张牌')

    discard_effects = [effect for effect in values['effects'] if effect.get('type') == 'active_discard']
    selected_ids = payload.get('discard_card_instance_ids', [])
    if selected_ids is None:
        selected_ids = []
    if not isinstance(selected_ids, list) or any(not isinstance(item, str) for item in selected_ids):
        _fail('INVALID_CARD_SELECTION', '主动丢弃的卡牌选择无效')
    if len(set(selected_ids)) != len(selected_ids) or instance_id in selected_ids:
        _fail('INVALID_CARD_SELECTION', '主动丢弃不能重复或选择正在打出的牌')
    selected_cards = []
    for selected_id in selected_ids:
        selected = next(
            (item for item in seat_state['hand'] if _card_instance_id(item) == selected_id),
            None,
        )
        if selected is None:
            _fail('INVALID_CARD_SELECTION', '主动丢弃的牌不在行动者手牌中')
        selected_cards.append(selected)
    required_minimum = 0
    required_maximum = 0
    for effect in discard_effects:
        amount = effect.get('amount', 0)
        _strict_nonnegative_int(amount, code='INVALID_CARD_EFFECT', label='主动丢弃数量')
        required_maximum += amount
        required_minimum += amount if effect.get('exact') else 0
    if not required_minimum <= len(selected_cards) <= required_maximum:
        _fail('INVALID_CARD_SELECTION', '主动丢弃的卡牌数量不符合要求')
    if not discard_effects and selected_cards:
        _fail('INVALID_CARD_SELECTION', '这张牌不需要主动丢弃')

    tags = set(values.get('tags') or [])
    enemy_effects = [
        effect for effect in values['effects']
        if effect.get('type') in {'damage', 'electric_damage'}
    ]
    target_enemy_id = str(payload.get('target_enemy_id') or '').strip()
    if enemy_effects and 'wide' not in tags and not target_enemy_id:
        _fail('INVALID_ENEMY_TARGET', '攻击牌必须指定一个存活敌人')

    target_ids = (
        [
            str(enemy.get('id') or '')
            for enemy in state['combat']['enemies']
            if int(enemy.get('health') or 0) > 0
        ]
        if 'wide' in tags
        else ([target_enemy_id] if target_enemy_id else [])
    )
    if modifiers.get('enchantment_armor_break'):
        for effect_target_id in target_ids:
            target = next((
                enemy for enemy in state['combat']['enemies']
                if str(enemy.get('id') or '') == effect_target_id
                and int(enemy.get('health') or 0) > 0
            ), None)
            before_shield = int((target or {}).get('shield') or 0)
            if target is not None and before_shield:
                target['shield'] = 0
                events.append({
                    'type': 'coop_enemy_shield_broken',
                    'actor_seat': actor_seat,
                    'enemy_id': effect_target_id,
                    'amount': before_shield,
                    'source': 'armor_break',
                })

    if not replaying:
        seat_state['elixir'] -= values['cost_e']
        seat_state['magic'] -= values['cost_m']
        if health_cost:
            health_before = int(player.get('health') or 0)
            player['health'] = health_before - health_cost
            events.append({
                'type': 'coop_player_health_paid',
                'actor_seat': actor_seat,
                'amount': health_cost,
                'before': health_before,
                'after': int(player['health']),
                'source': 'experience_patch',
            })
        events.append({
            'type': 'coop_card_played',
            'actor_seat': actor_seat,
            'card_instance_id': instance_id,
            'def_id': def_id,
            'cost_e': values['cost_e'],
            'cost_m': values['cost_m'],
        })
    else:
        events.append({
            'type': 'coop_card_replayed',
            'actor_seat': actor_seat,
            'card_instance_id': instance_id,
            'def_id': def_id,
            'source': 'puncture',
            'repeat_index': int(_puncture_depth),
        })
    # Match the single-player reducer: the played card leaves the hand before
    # its effects resolve.  Its vacated slot is therefore available to draw
    # effects, while the card itself reaches its destination only after all
    # effects finish.
    if not replaying:
        seat_state['hand'].remove(card)
    enchantment_event_start = len(events)
    enemy_health_before = {
        str(enemy.get('id') or ''): int(enemy.get('health') or 0)
        for enemy in state['combat']['enemies']
    }
    repeat_count = 1 + max(0, int(modifiers.get('enchantment_repeat_once') or 0))
    effects_to_resolve = list(values['effects']) * repeat_count
    for effect in effects_to_resolve:
        effect_type = effect.get('type')
        amount = effect.get('amount', 0)
        _strict_nonnegative_int(amount, code='INVALID_CARD_EFFECT', label='卡牌效果数值')
        if effect_type in {'damage', 'electric_damage'}:
            hits = effect.get('hits', 1)
            if isinstance(hits, bool) or not isinstance(hits, int) or hits <= 0:
                _fail('INVALID_CARD_EFFECT', '卡牌攻击段数无效')
            target_ids = (
                [
                    str(enemy.get('id') or '')
                    for enemy in state['combat']['enemies']
                    if int(enemy.get('health') or 0) > 0
                ]
                if 'wide' in tags
                else [target_enemy_id]
            )
            for effect_target_id in target_ids:
                for _ in range(hits):
                    target = next(
                        (
                            enemy for enemy in state['combat']['enemies']
                            if str(enemy.get('id') or '') == effect_target_id
                        ),
                        None,
                    )
                    if target is None or int(target.get('health') or 0) <= 0:
                        break
                    if effect_type == 'electric_damage':
                        static = max(0, int(target.get('static') or 0))
                        if static <= 0:
                            target['static'] = amount
                            events.append({
                                'type': 'coop_static_applied',
                                'actor_seat': actor_seat,
                                'enemy_id': effect_target_id,
                                'amount': amount,
                                'source': def_id,
                            })
                            continue
                        target['static'] = 0
                        resolved_amount = amount + static
                        events.append({
                            'type': 'coop_static_triggered',
                            'actor_seat': actor_seat,
                            'enemy_id': effect_target_id,
                            'amount': static,
                            'source': def_id,
                        })
                    else:
                        resolved_amount = amount
                    power = max(0, int((seat_state.get('statuses') or {}).get('power') or 0))
                    resolved_amount += power
                    vulnerable = max(0, int(target.get('vulnerable') or 0))
                    if vulnerable:
                        resolved_amount = max(1, math.ceil(resolved_amount * 1.5))
                    damage_coop_enemy(
                        state,
                        actor_seat=actor_seat,
                        enemy_id=effect_target_id,
                        amount=resolved_amount,
                        events=events,
                        source=def_id,
                    )
        elif effect_type == 'shield':
            before = int(seat_state['shield'])
            seat_state['shield'] = before + amount
            events.append({
                'type': 'coop_shield_gained',
                'actor_seat': actor_seat,
                'amount': amount,
                'before': before,
                'after': int(seat_state['shield']),
                'source': def_id,
            })
        elif effect_type == 'active_discard':
            # Resolve the discard at its canonical effect position.  A later
            # draw effect may therefore reshuffle and immediately draw one of
            # these cards, matching the single-player reducer.
            for selected in selected_cards:
                seat_state['hand'].remove(selected)
                seat_state['discard_pile'].append(selected)
                events.append({
                    'type': 'coop_card_discarded',
                    'actor_seat': actor_seat,
                    'card_instance_id': _card_instance_id(selected),
                    'source': def_id,
                })
            selected_cards = []
        elif effect_type == 'draw':
            _draw_cards(state, actor_seat, str(run_seed), amount, events)
        elif effect_type == 'elixir':
            before = int(seat_state['elixir'])
            seat_state['elixir'] = max(0, before + amount)
            events.append({
                'type': 'coop_elixir_gained',
                'actor_seat': actor_seat,
                'amount': amount,
                'before': before,
                'after': int(seat_state['elixir']),
                'source': def_id,
            })
        elif effect_type == 'magic':
            before = int(seat_state['magic'])
            seat_state['magic'] = max(0, before + amount)
            events.append({
                'type': 'coop_magic_gained',
                'actor_seat': actor_seat,
                'amount': amount,
                'before': before,
                'after': int(seat_state['magic']),
                'source': def_id,
            })
        elif effect_type == 'heal':
            player = state['players'][seat_key]
            before = int(player.get('health') or 0)
            maximum = int(player.get('max_health') or before)
            player['health'] = min(maximum, before + amount)
            events.append({
                'type': 'coop_player_healed',
                'actor_seat': actor_seat,
                'amount': int(player['health']) - before,
                'before': before,
                'after': int(player['health']),
                'source': def_id,
            })

    if selected_cards:
        _fail('INVALID_CARD_EFFECT', '主动丢弃效果没有被协作执行器结算')

    electric = max(0, int(modifiers.get('enchantment_electric_damage') or 0))
    if electric:
        for effect_target_id in target_ids:
            target = next((
                enemy for enemy in state['combat']['enemies']
                if str(enemy.get('id') or '') == effect_target_id
                and int(enemy.get('health') or 0) > 0
            ), None)
            if target is not None:
                static = max(0, int(target.get('static') or 0))
                if static <= 0:
                    target['static'] = electric
                    events.append({
                        'type': 'coop_static_applied',
                        'actor_seat': actor_seat,
                        'enemy_id': effect_target_id,
                        'amount': electric,
                        'source': 'attract_lightning',
                    })
                else:
                    target['static'] = 0
                    before = int(target.get('health') or 0)
                    dealt = min(before, electric + static)
                    target['health'] = before - dealt
                    events.append({
                        'type': 'enemy_damage',
                        'actor_seat': actor_seat,
                        'enemy_id': effect_target_id,
                        'amount': dealt,
                        'blocked': 0,
                        'before': before,
                        'after': int(target['health']),
                        'source': 'attract_lightning',
                        'lethal': before > 0 and int(target['health']) == 0,
                    })
                    events.append({
                        'type': 'coop_static_triggered',
                        'actor_seat': actor_seat,
                        'enemy_id': effect_target_id,
                        'amount': static,
                        'source': 'attract_lightning',
                    })
                    if before > 0 and int(target['health']) == 0:
                        events.append({
                            'type': 'enemy_defeated',
                            'actor_seat': actor_seat,
                            'enemy_id': effect_target_id,
                            'source': 'attract_lightning',
                        })

    damaged_target = next((
        enemy for enemy in state['combat']['enemies']
        if int(enemy.get('health') or 0) > 0
        and any(
            event.get('type') == 'enemy_damage'
            and event.get('enemy_id') == enemy.get('id')
            and int(event.get('amount') or 0) > 0
            for event in events[enchantment_event_start:]
        )
    ), None)
    fire = max(0, int(modifiers.get('enchantment_fire_on_hit_once') or 0))
    if fire and damaged_target is not None:
        damaged_target['fire'] = int(damaged_target.get('fire') or 0) + fire
        modifiers.pop('enchantment_fire_on_hit_once', None)
        events.append({
            'type': 'coop_enemy_status_applied',
            'actor_seat': actor_seat,
            'enemy_id': str(damaged_target.get('id') or ''),
            'amount': fire,
            'source': 'flame_bonus',
        })

    enemy_health_after = {
        str(enemy.get('id') or ''): int(enemy.get('health') or 0)
        for enemy in state['combat']['enemies']
    }
    killed_ids = [
        enemy_id
        for enemy_id, before in enemy_health_before.items()
        if before > 0 and enemy_health_after.get(enemy_id, 0) <= 0
    ]
    if killed_ids and modifiers.get('enchantment_double_reward_on_kill'):
        state['combat']['double_card_reward'] = True

    if (
        killed_ids
        and modifiers.get('enchantment_repeat_on_kill')
        and not discard_effects
        and int(_puncture_depth) < len(state['combat']['enemies'])
    ):
        living_ids = [
            str(enemy.get('id') or '')
            for enemy in state['combat']['enemies']
            if int(enemy.get('health') or 0) > 0
        ]
        if living_ids:
            repeat_index = int(_puncture_depth) + 1
            repeat_target_id = _deterministic_value_order(
                state,
                living_ids,
                str(run_seed),
                (
                    f'coop_enchantment_puncture:{state["combat"]["id"]}:'
                    f'{instance_id}:{repeat_index}'
                ),
            )[0]
            repeat_card = deepcopy(card)
            repeat_modifiers = repeat_card.setdefault('modifiers', {})
            for key in (
                'enchantment_shield_bonus_once', 'enchantment_draw_to_full_once',
                'enchantment_disc_once', 'enchantment_fire_on_hit_once',
                'enchantment_immunity_once', 'enchantment_repeat_once',
                'enchantment_power_once', 'enchantment_impact_once',
                'enchantment_retrieve_once', 'enchantment_reflection_once',
                'enchantment_vulnerable_once', 'enchantment_weak_once',
            ):
                repeat_modifiers.pop(key, None)
            resolve_intro_coop_action(
                state,
                actor_seat,
                'play_card',
                {'target_enemy_id': repeat_target_id},
                str(run_seed),
                events,
                _replay_card=repeat_card,
                _puncture_depth=repeat_index,
            )

    living_targets = [
        enemy for enemy in state['combat']['enemies']
        if str(enemy.get('id') or '') in target_ids and int(enemy.get('health') or 0) > 0
    ]
    status_targets = living_targets if target_ids else [seat_state]
    for target in status_targets:
        weak = max(0, int(modifiers.get('enchantment_weak_once') or 0))
        impact = max(0, int(modifiers.get('enchantment_impact_once') or 0))
        vulnerable = max(0, int(modifiers.get('enchantment_vulnerable_once') or 0))
        target_statuses = (
            target.setdefault('statuses', {}) if target is seat_state else target
        )
        applied = 0
        for status, status_amount in (
            ('weak', weak + impact),
            ('vulnerable', vulnerable + impact),
        ):
            if status_amount <= 0:
                continue
            immunity = max(0, int(target_statuses.get('negative_status_immunity') or 0))
            if immunity:
                target_statuses['negative_status_immunity'] = immunity - 1
                events.append({
                    'type': 'coop_status_blocked',
                    'actor_seat': actor_seat,
                    'target_id': (
                        f'seat:{actor_seat}'
                        if target is seat_state
                        else str(target.get('id') or '')
                    ),
                    'status': status,
                    'amount': status_amount,
                    'source': 'enchantment_book',
                })
                continue
            target_statuses[status] = int(target_statuses.get(status) or 0) + status_amount
            applied += status_amount
        if applied:
            events.append({
                'type': (
                    'coop_player_status_applied'
                    if target is seat_state
                    else 'coop_enemy_status_applied'
                ),
                'actor_seat': actor_seat,
                'target_id': (
                    f'seat:{actor_seat}'
                    if target is seat_state
                    else str(target.get('id') or '')
                ),
                'enemy_id': (
                    None if target is seat_state else str(target.get('id') or '')
                ),
                'amount': applied,
                'source': 'enchantment_book',
            })

    statuses = seat_state.setdefault('statuses', {})
    for key, status in (
        ('enchantment_disc_once', 'disc'),
        ('enchantment_immunity_once', 'negative_status_immunity'),
        ('enchantment_power_once', 'power'),
        ('enchantment_reflection_once', 'reflection'),
    ):
        status_amount = max(0, int(modifiers.get(key) or 0))
        if status_amount:
            statuses[status] = int(statuses.get(status) or 0) + status_amount

    if modifiers.get('enchantment_draw_to_full_once'):
        _draw_cards(
            state,
            actor_seat,
            str(run_seed),
            max(0, int(STORY_RULES['hand_limit']) - len(seat_state['hand'])),
            events,
        )

    if modifiers.get('enchantment_retrieve_once'):
        for pile_key, payload_key in (
            ('draw_pile', 'retrieve_draw_card_id'),
            ('discard_pile', 'retrieve_discard_card_id'),
        ):
            pile = seat_state[pile_key]
            if not pile:
                continue
            selected_id = str(payload.get(payload_key) or '')
            selected = next((
                item for item in pile if _card_instance_id(item) == selected_id
            ), None)
            if selected is None:
                _fail('ENCHANTMENT_RETRIEVE_SELECTION_REQUIRED', '激流需要从抽牌堆和弃牌堆各选择一张牌')
            pile.remove(selected)
            if len(seat_state['hand']) < int(STORY_RULES['hand_limit']):
                seat_state['hand'].append(selected)
            else:
                seat_state['discard_pile'].append(selected)

    for key in (
        'enchantment_shield_bonus_once', 'enchantment_draw_to_full_once',
        'enchantment_disc_once', 'enchantment_immunity_once',
        'enchantment_repeat_once', 'enchantment_power_once',
        'enchantment_impact_once', 'enchantment_retrieve_once',
        'enchantment_reflection_once', 'enchantment_vulnerable_once',
        'enchantment_weak_once',
    ):
        modifiers.pop(key, None)

    destination = (
        'exile_pile'
        if modifiers.get('force_exile') or ('exile' in tags and not modifiers.get('remove_exile'))
        else 'hand'
        if modifiers.get('enchantment_rebound')
        else 'discard_pile'
    )
    if destination == 'hand' and len(seat_state['hand']) >= int(STORY_RULES['hand_limit']):
        destination = 'discard_pile'
    if not replaying:
        seat_state[destination].append(card)


def prepare_intro_coop_round(state, run_seed, events):
    """Discard, reshuffle, redraw and restore resources after enemy actions."""

    combat = state['combat']
    if combat.get('turn') != COOP_COMBAT_HERO_TURN or combat.get('outcome') is not None:
        return
    for enemy in combat.get('enemies') or []:
        if (
            int(enemy.get('health') or 0) <= 0
            or enemy.get('content_source') != 'story_content'
        ):
            continue
        definition = COOP_STORY_CONTENT.enemy_definition(enemy.get('def_id'))
        moves = (definition or {}).get('moves')
        if not isinstance(moves, list) or not moves:
            _fail('UNSUPPORTED_COOP_ENEMY', '权威敌人行动已经不再兼容当前协作执行器')
        enemy['move_index'] = (int(enemy.get('move_index') or 0) + 1) % len(moves)
        enemy['intent'] = _compiled_enemy_intent(state, enemy, definition)
        events.append({
            'type': 'coop_enemy_intent_advanced',
            'enemy_id': str(enemy.get('id') or ''),
            'move_index': int(enemy['move_index']),
        })
        for status in ('weak', 'vulnerable'):
            if int(enemy.get(status) or 0) > 0:
                enemy[status] = max(0, int(enemy[status]) - 1)
    for seat_key in sorted(state['players'], key=int):
        seat = int(seat_key)
        player = state['players'][seat_key]
        seat_state = combat['seat_states'][seat_key]
        for zone in ('hand', 'draw_pile', 'discard_pile', 'exile_pile'):
            for zone_card in seat_state.get(zone) or []:
                modifiers = zone_card.get('modifiers')
                if not isinstance(modifiers, dict):
                    continue
                temporary_swift = max(0, int(modifiers.pop('temporary_swift', 0) or 0))
                temporary_heavy = max(0, int(modifiers.pop('temporary_heavy', 0) or 0))
                if temporary_swift:
                    modifiers['swift'] = max(
                        0,
                        int(modifiers.get('swift') or 0) - temporary_swift,
                    )
                if temporary_heavy:
                    modifiers['cost_e_delta'] = int(modifiers.get('cost_e_delta') or 0) - temporary_heavy
                if not any(value not in (0, False, None, [], {}) for value in modifiers.values()):
                    zone_card.pop('modifiers', None)
        old_shield = int(seat_state.get('shield') or 0)
        seat_state['shield'] = 0
        if old_shield:
            events.append({
                'type': 'coop_shield_cleared',
                'actor_seat': seat,
                'amount': old_shield,
            })
        if seat_state['hand']:
            retained = []
            discarded_cards = []
            voided = []
            for hand_card in seat_state['hand']:
                modifiers = hand_card.get('modifiers') or {}
                if modifiers.get('force_void'):
                    voided.append(hand_card)
                elif modifiers.get('retain'):
                    retained.append(hand_card)
                else:
                    discarded_cards.append(hand_card)
            discarded = [_card_instance_id(card) for card in discarded_cards]
            seat_state['discard_pile'].extend(discarded_cards)
            seat_state['exile_pile'].extend(voided)
            seat_state['hand'] = retained
            events.append({
                'type': 'coop_hand_discarded',
                'actor_seat': seat,
                'card_instance_ids': discarded,
                'count': len(discarded),
            })
        seat_state['elixir'] = max(
            0,
            int(player.get('max_elixir') or player.get('elixir') or 0),
        )
        turn_magic = sum(
            max(0, int(definition.get('amount') or 0))
            for _, definition in _compiled_player_relics(player, 'turn_magic')
        )
        if turn_magic:
            before_magic = int(seat_state.get('magic') or 0)
            seat_state['magic'] = before_magic + turn_magic
            events.append({
                'type': 'coop_magic_gained',
                'actor_seat': seat,
                'amount': turn_magic,
                'before': before_magic,
                'after': int(seat_state['magic']),
                'source': 'turn_start_relic',
            })
        statuses = seat_state.setdefault('statuses', {})
        regeneration = max(0, int(statuses.get('regeneration') or 0))
        if regeneration and int(player.get('health') or 0) > 0:
            before_health = int(player.get('health') or 0)
            player['health'] = min(
                int(player.get('max_health') or before_health),
                before_health + regeneration,
            )
            events.append({
                'type': 'coop_player_healed',
                'actor_seat': seat,
                'amount': int(player['health']) - before_health,
                'before': before_health,
                'after': int(player['health']),
                'source': 'regeneration',
            })
        if int(player.get('health') or 0) > 0:
            _draw_cards(
                state,
                seat,
                str(run_seed),
                int(STORY_RULES['draw_per_turn']),
                events,
            )
        events.append({
            'type': 'coop_seat_turn_started',
            'actor_seat': seat,
            'round': int(combat['round']),
            'elixir': int(seat_state['elixir']),
        })


def _deterministic_value_order(state, values, run_seed, namespace):
    values = list(dict.fromkeys(str(value) for value in values if value))
    streams = state.setdefault('rng_streams', {})
    if not isinstance(streams, dict):
        _fail('INVALID_RNG_STATE', '故事随机流状态无效')
    counter = streams.get(namespace, 0)
    _strict_nonnegative_int(counter, code='INVALID_RNG_STATE', label='随机流计数')
    streams[namespace] = counter + 1
    decorated = []
    for index, value in enumerate(values):
        material = f'{run_seed}|{namespace}|{counter}|{index}|{value}'.encode('utf-8')
        decorated.append((hashlib.sha256(material).digest(), index, value))
    decorated.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in decorated]


def _deterministic_int(state, run_seed, namespace, minimum, maximum):
    if (
        isinstance(minimum, bool)
        or not isinstance(minimum, int)
        or isinstance(maximum, bool)
        or not isinstance(maximum, int)
        or minimum > maximum
    ):
        _fail('INVALID_RNG_RANGE', '协作随机数范围无效')
    streams = state.setdefault('rng_streams', {})
    if not isinstance(streams, dict):
        _fail('INVALID_RNG_STATE', '故事随机流状态无效')
    counter = streams.get(namespace, 0)
    _strict_nonnegative_int(counter, code='INVALID_RNG_STATE', label='随机流计数')
    streams[namespace] = counter + 1
    material = f'{run_seed}|{namespace}|{counter}'.encode('utf-8')
    value = int.from_bytes(hashlib.sha256(material).digest()[:8], 'big')
    return minimum + value % (maximum - minimum + 1)


def _coop_enchantment_book_offer(state, seat, run_seed, namespace, *, node_type=None, rarity=None):
    """Return one deterministic personal book offer, or ``None`` on a missed drop."""

    if rarity is None:
        chance = {'combat': 30, 'elite': 60, 'boss': 100}.get(str(node_type or ''), 0)
        if chance <= 0 or _deterministic_int(
            state,
            str(run_seed),
            f'{namespace}:drop:seat:{int(seat)}',
            1,
            100,
        ) > chance:
            return None
        rarity_roll = _deterministic_int(
            state,
            str(run_seed),
            f'{namespace}:rarity:seat:{int(seat)}',
            1,
            100,
        )
        rarity = 'common' if rarity_roll <= 60 else 'rare' if rarity_roll <= 90 else 'ultra'
    rarity = str(rarity or '')
    pool = [
        book_id
        for book_id, definition in STORY_ENCHANTMENT_BOOKS.items()
        if definition.get('rarity') == rarity
        and (
            not definition.get('character_id')
            or definition.get('character_id')
            == str(state['players'][str(seat)].get('character_id') or '')
        )
    ]
    if not pool:
        _fail('INVALID_ENCHANTMENT_BOOK_POOL', '协作附魔书池无可用内容')
    return _deterministic_value_order(
        state,
        pool,
        str(run_seed),
        f'{namespace}:book:seat:{int(seat)}:{rarity}',
    )[0]


def _coop_map_nodes(state):
    story_map = state.get('map')
    if not isinstance(story_map, dict) or not isinstance(story_map.get('floors'), list):
        _fail('INVALID_COOP_MAP', '协作旅程地图无效')
    nodes = {}
    for floor in story_map['floors']:
        if not isinstance(floor, dict) or not isinstance(floor.get('nodes'), list):
            _fail('INVALID_COOP_MAP', '协作旅程地图节点无效')
        for node in floor['nodes']:
            if not isinstance(node, dict):
                _fail('INVALID_COOP_MAP', '协作旅程地图节点无效')
            node_id = str(node.get('id') or '').strip()
            if not re.fullmatch(r'[A-Za-z0-9._:-]{1,96}', node_id) or node_id in nodes:
                _fail('INVALID_COOP_MAP', '协作旅程地图节点标识无效')
            nodes[node_id] = node
    return nodes


def _validate_current_stage_map(state):
    """Validate the complete current-stage graph before any node transition."""

    story_map = state.get('map')
    if not isinstance(story_map, dict):
        _fail('INVALID_COOP_MAP', '协作旅程地图无效')
    floors = story_map.get('floors')
    content_version = str(state.get('content_version') or '')
    allowed_difficulties = (
        set(COOP_STAGE1_DIFFICULTIES)
        if _is_opening_content_version(content_version)
        else {'normal'}
    )
    difficulty = str(state.get('difficulty') or '')
    stage = state.get('stage')
    stage_definition = (
        COOP_STORY_STAGES.get(stage)
        if not isinstance(stage, bool) and isinstance(stage, int)
        else None
    )
    floor_count = story_map.get('floor_count')
    if (
        stage_definition is None
        or state.get('biome') != stage_definition['biome']
        or difficulty not in allowed_difficulties
        or isinstance(story_map.get('stage'), bool)
        or not isinstance(story_map.get('stage'), int)
        or story_map.get('stage') != stage
        or story_map.get('biome') != stage_definition['biome']
        or story_map.get('difficulty') != difficulty
        or isinstance(floor_count, bool)
        or not isinstance(floor_count, int)
        or floor_count not in ({16, 17} if stage == 3 else {16})
        or not isinstance(floors, list)
        or len(floors) != floor_count
    ):
        _fail('INVALID_COOP_MAP', '协作阶段地图元数据无效')

    nodes = _coop_map_nodes(state)
    nodes_by_floor = {}
    for expected_floor, floor_state in enumerate(floors, start=1):
        floor_nodes = floor_state.get('nodes') if isinstance(floor_state, dict) else None
        width = floor_state.get('width') if isinstance(floor_state, dict) else None
        if (
            not isinstance(floor_state, dict)
            or isinstance(floor_state.get('floor'), bool)
            or not isinstance(floor_state.get('floor'), int)
            or floor_state.get('floor') != expected_floor
            or isinstance(width, bool)
            or not isinstance(width, int)
            or width <= 0
            or not isinstance(floor_nodes, list)
            or len(floor_nodes) != width
        ):
            _fail('INVALID_COOP_MAP', '协作地图楼层结构无效')
        floor_ids = []
        for expected_index, node in enumerate(floor_nodes):
            x = node.get('x') if isinstance(node, dict) else None
            if (
                not isinstance(node, dict)
                or isinstance(node.get('floor'), bool)
                or not isinstance(node.get('floor'), int)
                or node.get('floor') != expected_floor
                or isinstance(node.get('index'), bool)
                or not isinstance(node.get('index'), int)
                or node.get('index') != expected_index
                or isinstance(x, bool)
                or not isinstance(x, (int, float))
                or not 0 < float(x) < 1
            ):
                _fail('INVALID_COOP_MAP', '协作地图节点位置无效')
            floor_ids.append(str(node.get('id') or ''))
        nodes_by_floor[expected_floor] = floor_ids

    if (
        len(nodes_by_floor[1]) != 1
        or nodes[nodes_by_floor[1][0]].get('type') != 'blessing'
        or len(nodes_by_floor[floor_count]) != 1
        or nodes[nodes_by_floor[floor_count][0]].get('type') != 'boss'
        or any(
            nodes[node_id].get('type') in {'blessing', 'boss'}
            for floor in range(2, floor_count)
            for node_id in nodes_by_floor[floor]
        )
    ):
        _fail('INVALID_COOP_MAP', '协作地图起点或终层 Boss 无效')

    edges = story_map.get('edges')
    if not isinstance(edges, list) or not edges:
        _fail('INVALID_COOP_MAP', '协作地图路线无效')
    outgoing = {node_id: [] for node_id in nodes}
    incoming = {node_id: [] for node_id in nodes}
    edge_pairs = []
    for edge in edges:
        if not isinstance(edge, dict) or set(edge) != {'from', 'to'}:
            _fail('INVALID_COOP_MAP', '协作地图路线结构无效')
        source = str(edge.get('from') or '')
        target = str(edge.get('to') or '')
        if (
            source not in nodes
            or target not in nodes
            or int(nodes[target].get('floor') or 0)
            != int(nodes[source].get('floor') or 0) + 1
        ):
            _fail('INVALID_COOP_MAP', '协作地图路线目标无效')
        edge_pairs.append((source, target))
        outgoing[source].append(target)
        incoming[target].append(source)
    if len(edge_pairs) != len(set(edge_pairs)):
        _fail('INVALID_COOP_MAP', '协作地图路线不能重复')

    start_id = nodes_by_floor[1][0]
    boss_id = nodes_by_floor[floor_count][0]
    if any(
        (node_id != boss_id and not outgoing[node_id])
        or (node_id != start_id and not incoming[node_id])
        or (node_id == boss_id and outgoing[node_id])
        or (node_id == start_id and incoming[node_id])
        for node_id in nodes
    ):
        _fail('INVALID_COOP_MAP', '协作地图存在断开的节点')

    reachable = {start_id}
    frontier = [start_id]
    while frontier:
        source = frontier.pop()
        for target in outgoing[source]:
            if target not in reachable:
                reachable.add(target)
                frontier.append(target)
    if reachable != set(nodes):
        _fail('INVALID_COOP_MAP', '协作地图包含不可到达节点')
    can_reach_boss = {boss_id}
    frontier = [boss_id]
    while frontier:
        target = frontier.pop()
        for source in incoming[target]:
            if source not in can_reach_boss:
                can_reach_boss.add(source)
                frontier.append(source)
    if can_reach_boss != set(nodes):
        _fail('INVALID_COOP_MAP', '协作地图包含无法抵达 Boss 的路线')
    return nodes


def _validate_current_rng_streams(state):
    streams = state.get('rng_streams')
    if not isinstance(streams, dict):
        _fail('INVALID_RNG_STATE', '协作随机流状态无效')
    if any(
        not isinstance(namespace, str)
        or not re.fullmatch(r'[A-Za-z0-9._:-]{1,256}', namespace)
        or isinstance(counter, bool)
        or not isinstance(counter, int)
        or counter < 0
        for namespace, counter in streams.items()
    ):
        _fail('INVALID_RNG_STATE', '协作随机流计数无效')


def _coop_outgoing_node_ids(state, node_id):
    story_map = state['map']
    edges = story_map.get('edges')
    if not isinstance(edges, list):
        _fail('INVALID_COOP_MAP', '协作旅程地图路线无效')
    outgoing = []
    for edge in edges:
        if not isinstance(edge, dict):
            _fail('INVALID_COOP_MAP', '协作旅程地图路线无效')
        if str(edge.get('from') or '') == node_id:
            outgoing.append(str(edge.get('to') or ''))
    return list(dict.fromkeys(outgoing))


def _coop_card_pool_for_player(state, seat, pool, *, include_neutral=False):
    player = state['players'].get(str(seat))
    if not isinstance(player, dict):
        _fail('INVALID_PLAYER_STATE', '协作玩家状态无效')
    character_id = str(player.get('character_id') or state.get('character_id') or 'common_flower')
    owner = 'primary' if character_id == 'common_flower' else character_id
    result = []
    for card_id in pool:
        definition = COOP_STORY_CONTENT.card_definition(card_id) or {}
        card_owner = str(definition.get('owner') or '')
        if card_owner == owner or (include_neutral and card_owner == 'neutral'):
            result.append(card_id)
    return tuple(result)


def _reward_options_for_seat(state, seat, run_seed, combat_id, round_index=1):
    pool = _coop_card_pool_for_player(state, seat, COOP_REWARD_CARD_IDS)
    if len(pool) < 3:
        _fail('UNSUPPORTED_COOP_CHARACTER', '该角色没有足够的协作奖励卡牌')
    ordered = _deterministic_value_order(
        state,
        pool,
        run_seed,
        f'coop_reward:{combat_id}:seat:{seat}:round:{int(round_index)}',
    )
    return [
        {'card_id': card_id, 'upgraded': False}
        for card_id in ordered[:3]
    ]


def _strip_event_indexes(events):
    stripped = []
    for raw in events or []:
        if not isinstance(raw, dict):
            continue
        event = deepcopy(raw)
        event.pop('action_sequence', None)
        event.pop('event_index', None)
        stripped.append(event)
    return stripped


def finalize_coop_action_events(events, action_sequence):
    return [
        {
            **event,
            'action_sequence': int(action_sequence),
            'event_index': index,
        }
        for index, event in enumerate(_strip_event_indexes(events))
    ]


def advance_coop_after_victory(state, *, run_seed):
    """Atomically leave a won combat for rewards or enter a stage barrier."""

    validate_coop_combat_state(state)
    combat = state['combat']
    if combat.get('outcome') != 'victory':
        return []
    progression = state.get('coop_progression')
    if not isinstance(progression, dict):
        _fail('INVALID_COOP_PROGRESSION', '协作章节进度无效')
    encounter_index = progression.get('encounter_index')
    if isinstance(encounter_index, bool) or not isinstance(encounter_index, int) or encounter_index <= 0:
        _fail('INVALID_COOP_PROGRESSION', '协作遭遇进度无效')
    combat_id = str(combat.get('id') or '')
    completed = progression.setdefault('completed_combat_ids', [])
    if not isinstance(completed, list) or combat_id in completed:
        _fail('INVALID_COOP_PROGRESSION', '协作战斗结算记录无效')
    completed.append(combat_id)
    summary = {
        'id': combat_id,
        'encounter_id': str(combat.get('encounter_id') or ''),
        'outcome': 'victory',
        'round': int(combat.get('round') or 1),
        'double_card_reward': bool(combat.get('double_card_reward')),
    }
    state['last_combat'] = summary
    state['coordination']['combat_ready_seats'] = []
    state['coordination']['combat_ready_round'] = None
    state['combat'] = None

    contract_version = int(progression.get('contract_version') or 1)
    nodes = _coop_map_nodes(state)
    current_node_id = str(state.get('current_node_id') or '')
    current_node = nodes.get(current_node_id) or {}
    current_floor = int(current_node.get('floor') or 0)
    max_floor = int(
        progression.get('max_floor')
        or (state.get('map') or {}).get('floor_count')
        or 16
    )
    stage_complete = (
        contract_version == COOP_STAGE1_CONTRACT_VERSION
        and str(current_node.get('type') or '') == 'boss'
        and current_floor >= max_floor
    )
    legacy_complete = (
        contract_version == 1
        and encounter_index >= int(progression.get('max_encounters') or COOP_DEMO_MAX_ENCOUNTERS)
    )
    if stage_complete:
        stage = int(state.get('stage') or 1)
        _, stage_definition = _coop_stage_definition(stage)
        current_node['status'] = 'completed'
        completed_nodes = progression.setdefault('completed_node_ids', [])
        if current_node_id in completed_nodes:
            _fail('INVALID_COOP_PROGRESSION', '协作 Boss 节点重复完成')
        completed_nodes.append(current_node_id)
        state['phase'] = 'stage_complete'
        state['completed'] = False
        state['completed_stage'] = stage
        completed_stages = progression.setdefault('completed_stages', [])
        if not isinstance(completed_stages, list) or stage in completed_stages:
            _fail('INVALID_COOP_PROGRESSION', '协作阶段完成记录无效')
        completed_stages.append(stage)
        room_id = f'stage-complete:{stage}'
        state['room'] = {
            'id': room_id,
            'type': 'stage_complete',
            'stage': stage,
            'title': deepcopy(stage_definition['complete_title']),
            'description': (
                {
                    'zh': '两名成员都确认后，将进入下一阶段并分别选择新的开局赐福。',
                    'en': 'Both members must confirm before the next stage and its blessings begin.',
                }
                if stage < COOP_FINAL_STAGE
                else {
                    'zh': '你们遇见了一朵腐化的花花。双方确认后完成本次协作旅程。',
                    'en': 'A corrupted flower awaits. Both members must confirm to finish this journey.',
                }
            ),
            'policy': 'all_members_ready',
        }
        state['shared_reward'] = None
        state['rewards_by_player'] = None
        state['coordination']['map_vote'] = None
        state['room_states_by_player'] = {
            seat_key: {'status': 'pending'}
            for seat_key in sorted(state['players'], key=int)
        }
        state['coordination']['room_decision'] = {
            'decision_id': room_id,
            'room_id': room_id,
            'policy': 'all_members_ready',
            'resolved_seats': [],
        }
        events = [{
            'type': 'coop_stage_completed',
            'combat_id': combat_id,
            'stage': stage,
            'floor': current_floor,
        }]
        validate_coop_live_state(state)
        return events
    if legacy_complete:
        state['phase'] = 'complete'
        state['completed'] = True
        state['room'] = {
            'type': 'coop_complete',
            'title': {'zh': '协作试玩章节完成', 'en': 'Co-op Demo Chapter Complete'},
        }
        state['shared_reward'] = None
        state['rewards_by_player'] = None
        state['coordination']['map_vote'] = None
        events = [{
            'type': 'coop_chapter_completed',
            'combat_id': combat_id,
            'encounter_index': encounter_index,
        }]
        validate_coop_live_state(state)
        return events

    if combat.get('escaped_without_reward'):
        events = [{
            'type': 'coop_combat_escaped_without_reward',
            'combat_id': combat_id,
        }]
        _begin_route_vote(state, events)
        validate_coop_live_state(state)
        return events

    node_type = str(current_node.get('type') or 'combat')
    reward_gold = 25 if node_type == 'elite' else COOP_REWARD_GOLD
    if str(state.get('difficulty') or 'normal') in {'hard', 'lunatic'}:
        reward_gold = (reward_gold * 3) // 4
    rewards = {}
    for seat_key in sorted(state['players'], key=int):
        seat = int(seat_key)
        reward_id = f'reward:{combat_id}:seat:{seat}'
        card_round_total = 2 if summary['double_card_reward'] else 1
        options = _reward_options_for_seat(
            state,
            seat,
            str(run_seed),
            combat_id,
            1,
        )
        book_id = _coop_enchantment_book_offer(
            state,
            seat,
            str(run_seed),
            f'coop_reward:{combat_id}',
            node_type=node_type,
        )
        player = state['players'][seat_key]
        player['gold'] = int(player.get('gold') or 0) + reward_gold
        rewards[seat_key] = {
            'reward_id': reward_id,
            'status': 'pending',
            'card_status': 'pending',
            'card_round_index': 1,
            'card_round_total': card_round_total,
            'card_choices': [],
            'book_status': 'pending' if book_id else 'resolved',
            'gold': reward_gold,
            'options': options,
            'selected_card_id': None,
            'skipped': False,
            'enchantment_book_id': book_id,
            'selected_enchantment_book_id': None,
            'skipped_enchantment_book': False,
        }
    state['phase'] = 'reward'
    state['room'] = {
        'type': 'reward',
        'source': 'combat_victory',
        'combat_id': combat_id,
    }
    state['shared_reward'] = {
        'source': 'combat_victory',
        'combat_id': combat_id,
        'gold_each': reward_gold,
    }
    state['rewards_by_player'] = rewards
    state['coordination']['map_vote'] = None
    events = [{
        'type': 'coop_rewards_started',
        'combat_id': combat_id,
        'count': len(rewards),
        'amount': reward_gold,
    }]
    validate_coop_live_state(state)
    return events


def _heal_coop_players_for_stage_transition(state, events):
    difficulty = str(state.get('difficulty') or 'normal')
    for seat_key, player in sorted(state['players'].items(), key=lambda item: int(item[0])):
        maximum = max(1, int(player.get('max_health') or 1))
        before = max(0, int(player.get('health') or 0))
        target = (
            (maximum * 4 + 4) // 5
            if difficulty in {'hard', 'lunatic'}
            else maximum
        )
        player['health'] = min(maximum, max(before, target))
        if int(player['health']) > before:
            events.append({
                'type': 'coop_player_healed',
                'actor_seat': int(seat_key),
                'amount': int(player['health']) - before,
                'source': 'stage_transition',
            })


def _resolve_stage_ready(state, actor_seat, payload, run_seed, events):
    if set(payload) - {'room_id'}:
        _fail('INVALID_ACTION_PAYLOAD', '阶段确认包含不支持的字段')
    room = state.get('room') or {}
    decision = state.get('coordination', {}).get('room_decision')
    room_states = state.get('room_states_by_player')
    room_id = str(payload.get('room_id') or '').strip()
    if (
        state.get('phase') != 'stage_complete'
        or room.get('type') != 'stage_complete'
        or room_id != str(room.get('id') or '')
        or not isinstance(decision, dict)
        or not isinstance(room_states, dict)
    ):
        _fail('STAGE_READY_NOT_ALLOWED', '当前不能确认协作阶段')
    private = room_states.get(str(actor_seat))
    resolved = decision.get('resolved_seats')
    if not isinstance(private, dict) or private.get('status') != 'pending':
        _fail('STAGE_ALREADY_READY', '你已经确认过当前阶段')
    if not isinstance(resolved, list) or int(actor_seat) in resolved:
        _fail('INVALID_COOP_COMPLETION', '协作阶段确认状态无效')
    private['status'] = 'resolved'
    resolved.append(int(actor_seat))
    resolved.sort()
    stage = int(state.get('stage') or 1)
    events.append({
        'type': 'coop_stage_ready',
        'actor_seat': int(actor_seat),
        'room_id': room_id,
        'stage': stage,
    })
    if set(resolved) != {int(seat) for seat in state['players']}:
        return
    state['room_states_by_player'] = None
    state['coordination']['room_decision'] = None
    if stage < COOP_FINAL_STAGE:
        _heal_coop_players_for_stage_transition(state, events)
        next_stage = stage + 1
        events.extend(_start_coop_stage_opening(
            state,
            run_seed=str(run_seed),
            stage=next_stage,
        ))
        events.append({
            'type': 'coop_stage_started',
            'stage': next_stage,
            'source': 'stage_transition',
        })
        return
    state['phase'] = 'complete'
    state['completed'] = True
    state['room'] = {
        'type': 'coop_complete',
        'stage': COOP_FINAL_STAGE,
        'title': {'zh': '协作旅程完成', 'en': 'Cooperative Journey Complete'},
        'description': {
            'zh': '你们以任意难度通关了全部三个阶段；通关与角色解锁已分别记入双方账号。',
            'en': 'All three stages are complete. Clear and unlock progress is recorded for both accounts.',
        },
    }
    events.append({
        'type': 'coop_journey_completed',
        'stage': COOP_FINAL_STAGE,
    })


def _begin_route_vote(state, events):
    nodes = _coop_map_nodes(state)
    current_id = str(state.get('current_node_id') or '')
    current = nodes.get(current_id)
    if current is None or current.get('status') != 'current':
        _fail('INVALID_COOP_MAP', '协作旅程当前节点无效')
    outgoing = _coop_outgoing_node_ids(state, current_id)
    if not outgoing or any(node_id not in nodes for node_id in outgoing):
        _fail('INVALID_COOP_MAP', '协作旅程没有可用的后续路线')
    if any(str(nodes[node_id].get('type') or '') not in COOP_STAGE1_SUPPORTED_NODE_TYPES for node_id in outgoing):
        _fail('UNSUPPORTED_COOP_ROUTE', '协作路线包含尚未接入的房间类型')
    current['status'] = 'completed'
    completed_nodes = state['coop_progression'].setdefault('completed_node_ids', [])
    if not isinstance(completed_nodes, list) or current_id in completed_nodes:
        _fail('INVALID_COOP_PROGRESSION', '协作节点完成记录无效')
    completed_nodes.append(current_id)
    if state.get('content_version') == COOP_STORY_CONTENT_VERSION:
        for seat_key, player in sorted(state['players'].items(), key=lambda item: int(item[0])):
            healing = sum(
                max(0, int(definition.get('amount') or 0))
                for _, definition in _compiled_player_relics(player, 'floor_heal')
            )
            if healing:
                before = int(player.get('health') or 0)
                player['health'] = min(int(player.get('max_health') or 0), before + healing)
                if int(player['health']) > before:
                    events.append({
                        'type': 'coop_player_healed',
                        'actor_seat': int(seat_key),
                        'amount': int(player['health']) - before,
                        'source': 'node_completion',
                    })
    for node in nodes.values():
        if node.get('status') == 'available':
            node['status'] = 'locked'
    for node_id in outgoing:
        nodes[node_id]['status'] = 'available'
    floor = min(int(nodes[node_id].get('floor') or 0) for node_id in outgoing)
    vote_id = f'route:{current_id}:floor:{floor}'
    state['phase'] = 'map'
    state['room'] = {'type': 'map_vote', 'vote_id': vote_id, 'floor': floor}
    state['rewards_by_player'] = None
    state['shared_reward'] = None
    state['coordination']['map_vote'] = {
        'vote_id': vote_id,
        'from_node_id': current_id,
        'option_node_ids': outgoing,
        'votes_by_seat': {},
        'resolved_node_id': None,
    }
    events.append({
        'type': 'coop_route_vote_started',
        'vote_id': vote_id,
        'count': len(outgoing),
        'floor': floor,
    })


def _compiled_player_relics(player, script=None):
    relics = player.get('relics')
    if not isinstance(relics, list):
        _fail('INVALID_PLAYER_RELICS', '协作玩家遗物状态无效')
    result = []
    for relic_id in relics:
        definition = COOP_STORY_CONTENT.relic_definition(relic_id)
        if relic_id not in COOP_SUPPORTED_RELIC_IDS or not isinstance(definition, dict):
            continue
        if script is None or str(definition.get('script') or '') == script:
            result.append((relic_id, definition))
    return result


def _apply_card_gain_relics(state, seat, events):
    player = state['players'][str(seat)]
    for _, definition in _compiled_player_relics(player, 'gain_card_heal'):
        before = int(player.get('health') or 0)
        maximum = int(player.get('max_health') or 0)
        player['health'] = min(maximum, before + int(definition.get('amount') or 0))
        if events is not None:
            events.append({
                'type': 'coop_player_healed',
                'actor_seat': int(seat),
                'amount': int(player['health']) - before,
                # Relic ownership is private progression data; expose the
                # trigger category, not the personal relic identifier.
                'source': 'card_gain',
            })


def _gain_compiled_relic(state, seat, relic_id, events, source):
    relic_id = str(relic_id or '')
    definition = COOP_STORY_CONTENT.relic_definition(relic_id)
    if relic_id not in COOP_SUPPORTED_RELIC_IDS or not isinstance(definition, dict):
        _fail('UNSUPPORTED_COOP_RELIC', '该遗物尚未接入协作故事')
    player = state['players'][str(seat)]
    relics = player.get('relics')
    if not isinstance(relics, list):
        _fail('INVALID_PLAYER_RELICS', '协作玩家遗物状态无效')
    if relic_id in relics and not definition.get('stackable'):
        _fail('COOP_RELIC_ALREADY_OWNED', '你已经拥有该遗物')
    relics.append(relic_id)
    amount = int(definition.get('amount') or 0)
    script = str(definition.get('script') or '')
    if script == 'gain_gold':
        player['gold'] = int(player.get('gold') or 0) + amount
    elif script == 'gain_max_health':
        player['max_health'] = int(player.get('max_health') or 0) + amount
        player['health'] = min(
            int(player['max_health']),
            int(player.get('health') or 0) + amount,
        )
    elif script not in {'gain_card_heal', 'rest_gold', 'shop_discount'}:
        _fail('UNSUPPORTED_COOP_RELIC', '该遗物效果尚未接入协作故事')
    events.append({
        'type': 'coop_relic_gained',
        'actor_seat': int(seat),
        'source': str(source or 'coop_reward'),
    })
    return relic_id


def _gain_reward_card(state, seat, card_id, upgraded, run_seed, reward_id, events=None):
    player = state['players'][str(seat)]
    deck = player.get('deck')
    if not isinstance(deck, list):
        _fail('INVALID_PLAYER_DECK', '协作玩家卡组无效')
    serial = int(player.get('next_card_serial') or 1)
    existing_ids = {str((card or {}).get('instance_id') or '') for card in deck if isinstance(card, dict)}
    while True:
        suffix = hashlib.sha256(
            f'{run_seed}|{reward_id}|{seat}|{serial}|{card_id}'.encode('utf-8')
        ).hexdigest()[:20]
        instance_id = f'coop-reward-{seat}-{serial}-{suffix}'
        if instance_id not in existing_ids:
            break
        serial += 1
    card = {
        'instance_id': instance_id,
        'def_id': card_id,
        'upgraded': bool(upgraded),
        'upgrade_level': 1 if upgraded else 0,
    }
    _card_values(card)
    deck.append(card)
    player['next_card_serial'] = serial + 1
    _apply_card_gain_relics(state, seat, events)
    return card


def _record_coop_blessing(player, blessing_id):
    history = player.get('blessings')
    if not isinstance(history, list):
        history = []
        player['blessings'] = history
    history.append(blessing_id)
    player['blessing'] = blessing_id


def _apply_coop_opening_blessing(state, actor_seat, blessing_id, run_seed, room_id):
    definition = COOP_STORY_CONTENT.blessing_definition(blessing_id)
    if blessing_id not in COOP_OPENING_BLESSING_IDS or not isinstance(definition, dict):
        _fail('INVALID_OPENING_OPTION', '该赐福尚未接入协作开局')
    player = state['players'][str(actor_seat)]
    script = str(definition.get('script') or '')
    amount = max(0, int(definition.get('amount') or 0))
    if script == 'gain_max_health':
        player['max_health'] = int(player.get('max_health') or 0) + amount
    elif script == 'gain_gold':
        player['gold'] = int(player.get('gold') or 0) + amount
    elif script == 'gain_random_ultra_card':
        ultra_ids = [
            card_id
            for card_id in _coop_card_pool_for_player(
                state,
                actor_seat,
                COOP_REWARD_CARD_IDS,
            )
            if str((COOP_STORY_CONTENT.card_definition(card_id) or {}).get('rarity') or '') == 'ultra'
        ]
        ordered = _deterministic_value_order(
            state,
            ultra_ids,
            str(run_seed),
            f'coop_opening_ultra:{room_id}:seat:{int(actor_seat)}',
        )
        if not ordered:
            _fail('NO_OPENING_REWARD_CARD', '当前没有可用于协作赐福的究极牌')
        _gain_reward_card(
            state,
            actor_seat,
            ordered[0],
            False,
            str(run_seed),
            f'{room_id}:ultra',
        )
    elif script == 'wealth_and_basics':
        player['gold'] = int(player.get('gold') or 0) + amount
        for card_id in ('basic', 'rose'):
            _gain_reward_card(
                state,
                actor_seat,
                card_id,
                False,
                str(run_seed),
                f'{room_id}:{card_id}',
            )
    else:
        _fail('INVALID_OPENING_OPTION', '该赐福尚未接入协作开局')
    _record_coop_blessing(player, blessing_id)


def _resolve_opening_choice(state, actor_seat, payload, run_seed, events):
    if set(payload) - {'room_id', 'option_id'}:
        _fail('INVALID_ACTION_PAYLOAD', '协作开局选择包含不支持的字段')
    room = state.get('room') or {}
    room_id = str(payload.get('room_id') or '').strip()
    if room.get('type') != 'opening' or room_id != str(room.get('id') or ''):
        _fail('STALE_COOP_ROOM', '协作开局标识已经过期')
    room_states = state.get('room_states_by_player')
    decision = state['coordination'].get('room_decision')
    if not isinstance(room_states, dict) or not isinstance(decision, dict):
        _fail('INVALID_COOP_ROOM', '协作开局状态无效')
    private = room_states.get(str(actor_seat))
    if not isinstance(private, dict) or private.get('status') != 'pending':
        _fail('OPENING_ALREADY_RESOLVED', '你已经处理过协作开局选择')
    option_id = str(payload.get('option_id') or '').strip()
    if option_id not in (private.get('options') or []):
        _fail('INVALID_OPENING_OPTION', '该赐福不在你的开局选项中')
    _apply_coop_opening_blessing(
        state,
        actor_seat,
        option_id,
        str(run_seed),
        room_id,
    )
    private['status'] = 'resolved'
    private['selected_option'] = option_id
    resolved = decision.get('resolved_seats')
    if not isinstance(resolved, list):
        _fail('INVALID_COOP_ROOM', '协作开局完成状态无效')
    decision['resolved_seats'] = sorted(set(resolved) | {int(actor_seat)})
    # The option id is intentionally absent: another seat may learn only that
    # this member completed their private opening choice.
    events.append({
        'type': 'coop_opening_resolved',
        'actor_seat': int(actor_seat),
        'room_id': room_id,
        'stage': 1,
    })
    if all(item.get('status') == 'resolved' for item in room_states.values()):
        state['room_states_by_player'] = None
        state['coordination']['room_decision'] = None
        _begin_route_vote(state, events)


def _resolve_reward_choice(state, actor_seat, payload, run_seed, events):
    if set(payload) - {
        'reward_id', 'choice_kind', 'card_id', 'book_id',
        'replace_book_instance_id',
    }:
        _fail('INVALID_ACTION_PAYLOAD', '协作奖励选择包含不支持的字段')
    rewards = state.get('rewards_by_player')
    if not isinstance(rewards, dict) or set(rewards) != set(state['players']):
        _fail('INVALID_COOP_REWARD', '协作奖励状态无效')
    reward = rewards[str(actor_seat)]
    reward_id = str(payload.get('reward_id') or '').strip()
    if reward_id != str(reward.get('reward_id') or ''):
        _fail('STALE_COOP_REWARD', '协作奖励标识已经过期')
    if reward.get('status') != 'pending':
        _fail('REWARD_ALREADY_CHOSEN', '你已经处理过这份奖励')
    legacy_card_choice = 'choice_kind' not in payload
    choice_kind = str(payload.get('choice_kind') or 'card').strip().lower()
    if choice_kind not in {'card', 'enchantment_book'}:
        _fail('INVALID_REWARD_CHOICE', '协作奖励类型无效')
    if choice_kind == 'enchantment_book':
        if set(payload) - {
            'reward_id', 'choice_kind', 'book_id', 'replace_book_instance_id',
        }:
            _fail('INVALID_ACTION_PAYLOAD', '附魔书奖励选择包含不支持的字段')
        if reward.get('book_status') != 'pending':
            _fail('REWARD_ALREADY_CHOSEN', '你已经处理过这份附魔书奖励')
        offered_id = str(reward.get('enchantment_book_id') or '')
        book_id = str(payload.get('book_id') or '').strip().lower()
        if not offered_id:
            _fail('INVALID_ENCHANTMENT_BOOK_REWARD', '当前奖励没有附魔书')
        if book_id:
            if book_id != offered_id:
                _fail('INVALID_ENCHANTMENT_BOOK_REWARD', '该附魔书不在你的协作奖励中')
            _gain_coop_enchantment_book(
                state,
                actor_seat,
                book_id,
                events,
                source='combat_reward',
                replace_instance_id=payload.get('replace_book_instance_id'),
            )
            reward['selected_enchantment_book_id'] = book_id
            reward['skipped_enchantment_book'] = False
        else:
            reward['selected_enchantment_book_id'] = None
            reward['skipped_enchantment_book'] = True
        reward['book_status'] = 'resolved'
        reward['status'] = (
            'resolved'
            if reward.get('card_status') == 'resolved'
            else 'pending'
        )
        events.append({
            'type': 'coop_enchantment_book_reward_resolved',
            'actor_seat': actor_seat,
            'reward_id': reward_id,
            'skipped': not bool(book_id),
        })
        if all(item.get('status') == 'resolved' for item in rewards.values()):
            _begin_route_vote(state, events)
        return
    if set(payload) - {'reward_id', 'choice_kind', 'card_id'}:
        _fail('INVALID_ACTION_PAYLOAD', '卡牌奖励选择包含不支持的字段')
    if reward.get('card_status') != 'pending':
        _fail('REWARD_ALREADY_CHOSEN', '你已经处理过这份卡牌奖励')
    card_id = str(payload.get('card_id') or '').strip().lower()
    options = reward.get('options')
    if not isinstance(options, list):
        _fail('INVALID_COOP_REWARD', '协作奖励选项无效')
    if card_id:
        choice = next(
            (option for option in options if str((option or {}).get('card_id') or '') == card_id),
            None,
        )
        if choice is None:
            _fail('INVALID_REWARD_CARD', '该卡牌不在你的协作奖励中')
        _gain_reward_card(
            state,
            actor_seat,
            card_id,
            bool(choice.get('upgraded')),
            str(run_seed),
            reward_id,
            events,
        )
        reward['selected_card_id'] = card_id
        reward['skipped'] = False
    else:
        reward['selected_card_id'] = None
        reward['skipped'] = True
    card_round_index = int(reward.get('card_round_index') or 1)
    card_round_total = int(reward.get('card_round_total') or 1)
    reward.setdefault('card_choices', []).append({
        'round_index': card_round_index,
        'card_id': card_id or None,
        'skipped': not bool(card_id),
    })
    if legacy_card_choice and reward.get('book_status') == 'pending':
        # Older clients know only the original one-step card reward contract.
        # Preserve their progression by treating an unaddressed book as declined.
        reward['book_status'] = 'resolved'
        reward['selected_enchantment_book_id'] = None
        reward['skipped_enchantment_book'] = True
    if card_round_index < card_round_total:
        reward['card_round_index'] = card_round_index + 1
        reward['options'] = _reward_options_for_seat(
            state,
            actor_seat,
            str(run_seed),
            str((state.get('room') or {}).get('combat_id') or ''),
            card_round_index + 1,
        )
        reward['selected_card_id'] = None
        reward['skipped'] = False
        reward['status'] = 'pending'
        events.append({
            'type': 'coop_reward_round_resolved',
            'actor_seat': actor_seat,
            'reward_id': reward_id,
            'round_index': card_round_index,
            'round_total': card_round_total,
            'skipped': not bool(card_id),
        })
        return
    reward['card_status'] = 'resolved'
    reward['status'] = (
        'resolved'
        if reward.get('book_status') == 'resolved'
        else 'pending'
    )
    # The selected card is deliberately absent from this shared event.  Other
    # party members may see completion, but never another seat's reward choice.
    events.append({
        'type': 'coop_reward_resolved',
        'actor_seat': actor_seat,
        'reward_id': reward_id,
        'skipped': not bool(card_id),
    })
    if all(item.get('status') == 'resolved' for item in rewards.values()):
        _begin_route_vote(state, events)


def _apply_coop_enemy_difficulty(state, enemies):
    """Apply the explicit cooperative Lunatic modifier to curated enemies."""

    if str(state.get('difficulty') or 'normal') != 'lunatic':
        return enemies
    for enemy in enemies:
        if enemy.get('content_source') == 'story_content':
            continue
        health = max(1, int(enemy.get('max_health') or enemy.get('health') or 1))
        scaled_health = (health * 5 + 3) // 4
        enemy['health'] = scaled_health
        enemy['max_health'] = scaled_health
        intent = enemy.get('intent')
        if isinstance(intent, dict) and str(intent.get('kind') or '') in {'attack', 'attack_all'}:
            amount = max(0, int(intent.get('amount') or 0))
            intent['amount'] = (amount * 5 + 3) // 4
    return enemies


def _compiled_enemy_effect_value(state, effect, field='amount'):
    lunatic_field = f'lunatic_{field}'
    if (
        str(state.get('difficulty') or 'normal') == 'lunatic'
        and effect.get(lunatic_field) is not None
    ):
        return int(effect[lunatic_field])
    default = 1 if field == 'hits' else 0
    return int(effect.get(field, default) or default)


def _compiled_enemy_intent(state, enemy, definition=None):
    definition = definition or COOP_STORY_CONTENT.enemy_definition(enemy.get('def_id'))
    moves = (definition or {}).get('moves')
    move_index = enemy.get('move_index')
    if (
        not isinstance(moves, list)
        or not moves
        or isinstance(move_index, bool)
        or not isinstance(move_index, int)
        or not 0 <= move_index < len(moves)
    ):
        _fail('INVALID_COOP_ENEMY', '权威敌人行动状态无效')
    move = moves[move_index]
    damage_effect = next(
        (
            effect for effect in move.get('effects') or []
            if str(effect.get('type') or '') == 'damage'
        ),
        None,
    )
    intent = {
        'kind': 'idle' if damage_effect is None else 'attack',
        'move_name': deepcopy(move.get('name')),
    }
    if damage_effect is not None:
        intent['amount'] = max(
            0,
            _compiled_enemy_effect_value(state, damage_effect)
            + int(enemy.get('power') or 0),
        )
        intent['hits'] = max(1, _compiled_enemy_effect_value(state, damage_effect, 'hits'))
    return intent


def _instantiate_compiled_encounter(state, encounter_id, node_id):
    encounter = COOP_STORY_CONTENT.encounter_definition(encounter_id)
    if not isinstance(encounter, dict):
        _fail('UNSUPPORTED_COOP_ENCOUNTER', '协作遭遇已经不再兼容当前内容编译器')
    enemies = []
    for index, member in enumerate(encounter.get('members') or []):
        definition = COOP_STORY_CONTENT.enemy_definition(member.get('def_id'))
        moves = (definition or {}).get('moves')
        if not isinstance(definition, dict) or not isinstance(moves, list) or not moves:
            _fail('UNSUPPORTED_COOP_ENEMY', '协作遭遇引用了未编译的权威敌人')
        base_health = (
            definition.get('lunatic_max_health', definition.get('max_health'))
            if str(state.get('difficulty') or 'normal') == 'lunatic'
            else definition.get('max_health')
        )
        max_health = max(
            1,
            (
                int(base_health) * COOP_CANONICAL_ENEMY_HEALTH_NUMERATOR
                + COOP_CANONICAL_ENEMY_HEALTH_DENOMINATOR - 1
            ) // COOP_CANONICAL_ENEMY_HEALTH_DENOMINATOR,
        )
        move_index = int(member.get('move_index', member.get('move_step', 0))) % len(moves)
        enemy = {
            'id': f'{node_id}-{member["def_id"]}-{index + 1}',
            'def_id': str(member['def_id']),
            'name': deepcopy(definition.get('name')),
            'image_url': str(definition.get('image_url') or ''),
            'content_source': 'story_content',
            'health': max_health,
            'max_health': max_health,
            'shield': 0,
            'power': 0,
            'move_index': move_index,
        }
        enemy['intent'] = _compiled_enemy_intent(state, enemy, definition)
        enemies.append(enemy)
    if not enemies:
        _fail('UNSUPPORTED_COOP_ENCOUNTER', '协作遭遇没有可执行敌人')
    return enemies


def resolve_compiled_coop_enemy_action(state, enemy, run_seed, events):
    """Execute one strictly compiled canonical story enemy move."""

    if enemy.get('content_source') != 'story_content':
        return False
    definition = COOP_STORY_CONTENT.enemy_definition(enemy.get('def_id'))
    moves = (definition or {}).get('moves')
    move_index = enemy.get('move_index')
    if (
        not isinstance(moves, list)
        or isinstance(move_index, bool)
        or not isinstance(move_index, int)
        or not 0 <= move_index < len(moves)
    ):
        _fail('INVALID_COOP_ENEMY', '权威敌人行动状态无效')
    expected_intent = _compiled_enemy_intent(state, enemy, definition)
    stored_intent = enemy.get('intent') or {}
    if any(stored_intent.get(key) != value for key, value in expected_intent.items()):
        _fail('INVALID_COOP_ENEMY', '权威敌人意图与行动状态不一致')
    events.append({
        'type': 'enemy_action',
        'enemy_id': str(enemy.get('id') or ''),
        'move_index': move_index,
        'name': deepcopy(moves[move_index].get('name')),
    })
    for effect in moves[move_index].get('effects') or []:
        effect_type = str(effect.get('type') or '')
        amount = _compiled_enemy_effect_value(state, effect)
        if effect_type == 'damage':
            damage_coop_party_from_enemy(
                state,
                enemy=enemy,
                amount=max(0, amount + int(enemy.get('power') or 0)),
                hits=max(1, _compiled_enemy_effect_value(state, effect, 'hits')),
                events=events,
            )
        elif effect_type == 'gain_shield':
            before = int(enemy.get('shield') or 0)
            enemy['shield'] = before + amount
            events.append({
                'type': 'enemy_shield_gained',
                'enemy_id': str(enemy.get('id') or ''),
                'amount': amount,
                'before': before,
                'after': int(enemy['shield']),
            })
        elif effect_type == 'gain_power':
            before = int(enemy.get('power') or 0)
            enemy['power'] = before + amount
            events.append({
                'type': 'enemy_power_gained',
                'enemy_id': str(enemy.get('id') or ''),
                'amount': amount,
                'before': before,
                'after': int(enemy['power']),
            })
        elif effect_type == 'self_damage':
            before = int(enemy.get('health') or 0)
            enemy['health'] = max(0, before - amount)
            events.append({
                'type': 'enemy_self_damage',
                'enemy_id': str(enemy.get('id') or ''),
                'amount': min(before, amount),
                'before': before,
                'after': int(enemy['health']),
            })
            if before > 0 and int(enemy['health']) == 0:
                events.append({
                    'type': 'enemy_defeated',
                    'enemy_id': str(enemy.get('id') or ''),
                    'source': 'self_damage',
                })
        else:
            _fail('UNSUPPORTED_COOP_ENEMY_EFFECT', '权威敌人效果不再受协作执行器支持')
    return True


def _adapted_biome_encounter(biome, room_type, node_id, floor):
    """Return explicit co-op adaptations when canonical mechanics are not executable.

    These definitions use distinct ``coop_*`` ids, so clients never present a
    reduced cooperative move set as the exact single-player enemy contract.
    """

    biome = str(biome or '')
    room_type = str(room_type or '')
    entry = COOP_ADAPTED_ENCOUNTERS.get((biome, room_type))
    if entry is None:
        _fail('UNSUPPORTED_COOP_ENCOUNTER', '当前生物群系没有可执行的协作遭遇')
    encounter_prefix, members = entry
    encounter_id = f'{encounter_prefix}_f{int(floor):02d}'
    enemies = []
    for index, member in enumerate(members, start=1):
        health = int(member['health'])
        enemies.append({
            'id': f'{node_id}-{member["slug"]}-{index}',
            'def_id': str(member['def_id']),
            'name': deepcopy(member['name']),
            'image_url': str(member['image_url']),
            'health': health,
            'max_health': health,
            'intent': deepcopy(member['intent']),
        })
    return encounter_id, enemies


def _start_coop_combat_for_node(state, node_id, run_seed):
    nodes = _coop_map_nodes(state)
    node = nodes.get(str(node_id))
    if not isinstance(node, dict):
        _fail('INVALID_COOP_ROUTE', '协作战斗节点不存在')
    floor = int(node.get('floor') or 0)
    room_type = str(node.get('type') or '')
    if room_type not in {'combat', 'elite', 'boss'} or floor <= 0:
        _fail('UNSUPPORTED_COOP_ROUTE', '当前节点不是可执行的协作战斗')
    biome = str(state.get('biome') or 'garden')
    combat_id = f'{biome}-route-{node_id}'
    staging = deepcopy(state)
    seat_states = _intro_seat_states(staging, str(run_seed), combat_id=combat_id)
    if biome != 'garden':
        encounter_id, enemies = _adapted_biome_encounter(
            biome,
            room_type,
            str(node_id),
            floor,
        )
    elif room_type == 'boss':
        encounter_id = f'garden_boss_f{floor:02d}'
        health = 180
        enemies = [{
            'id': f'{node_id}-thorn-warden',
            'def_id': 'coop_thorn_warden',
            'name': {'zh': '荆棘守园者', 'en': 'Thorn Warden'},
            'health': health,
            'max_health': health,
            'intent': {'kind': 'attack_all', 'amount': 7, 'hits': 1},
        }]
    elif room_type == 'elite':
        encounter_id = f'garden_elite_f{floor:02d}'
        health = 82 + floor * 5
        enemies = [{
            'id': f'{node_id}-thorn-elite',
            'def_id': 'coop_thorn_elite',
            'name': {'zh': '荆棘精英', 'en': 'Thorn Elite'},
            'health': health,
            'max_health': health,
            'intent': {'kind': 'attack', 'amount': 8 + floor // 3, 'hits': 1},
        }]
    else:
        preferred_tier = 'hard' if floor >= 10 else 'simple'
        encounter_ids = COOP_STORY_CONTENT.encounter_ids(biome, preferred_tier)
        if not encounter_ids:
            encounter_ids = COOP_STORY_CONTENT.encounter_ids(biome, 'simple')
        ordered_ids = _deterministic_value_order(
            staging,
            encounter_ids,
            str(run_seed),
            f'coop_encounter:{biome}:{preferred_tier}:{node_id}',
        )
        if not ordered_ids:
            _fail('UNSUPPORTED_COOP_ENCOUNTER', '当前生物群系没有可执行的协作遭遇')
        encounter_id = ordered_ids[0]
        enemies = _instantiate_compiled_encounter(staging, encounter_id, str(node_id))
    _apply_coop_enemy_difficulty(staging, enemies)
    next_state, start_events = initialize_coop_combat(
        staging,
        combat_id=combat_id,
        enemies=enemies,
        run_seed=str(run_seed),
        seat_states=seat_states,
    )
    next_state['combat']['encounter_id'] = encounter_id
    next_state['coop_progression']['encounter_index'] = (
        int(next_state['coop_progression'].get('encounter_index') or 0) + 1
    )
    next_state['room'] = {
        'type': 'combat',
        'node_type': room_type,
        'node_id': str(node_id),
        'encounter_id': encounter_id,
        'title': (
            (
                {'zh': '荆棘守园者', 'en': 'Thorn Warden'}
                if room_type == 'boss'
                else (
                    {'zh': '协作精英战', 'en': 'Cooperative Elite Battle'}
                    if room_type == 'elite'
                    else deepcopy(COOP_STORY_STAGES[int(state.get('stage') or 1)]['name'])
                )
            )
        ),
    }
    raw_events = _strip_event_indexes(start_events)
    for seat_key, seat_state in sorted(
        next_state['combat']['seat_states'].items(),
        key=lambda item: int(item[0]),
    ):
        raw_events.append({
            'type': 'coop_cards_drawn',
            'actor_seat': int(seat_key),
            'card_instance_ids': [_card_instance_id(card) for card in seat_state['hand']],
            'count': len(seat_state['hand']),
        })
    return next_state, raw_events


def _start_second_coop_combat(state, node_id, run_seed):
    """Compatibility wrapper retained for older tests and imports."""

    return _start_coop_combat_for_node(state, node_id, run_seed)


def _start_coop_rest_room(state, node_id):
    nodes = _coop_map_nodes(state)
    node = nodes.get(str(node_id))
    if not isinstance(node, dict) or str(node.get('type') or '') != 'rest':
        _fail('UNSUPPORTED_COOP_ROUTE', '当前节点不是协作休息房')
    room_id = f'rest:{node_id}'
    state['phase'] = 'room'
    state['combat'] = None
    state['room'] = {
        'id': room_id,
        'type': 'rest',
        'node_id': str(node_id),
        'title': {'zh': '协作休息处', 'en': 'Cooperative Rest Site'},
        'policy': 'per_player_barrier',
    }
    state['room_states_by_player'] = {
        seat_key: {
            'status': 'pending',
            'options': [
                'heal',
                'upgrade',
                *(
                    ['gold']
                    if _compiled_player_relics(state['players'][seat_key], 'rest_gold')
                    else []
                ),
                'leave',
            ],
            'selected_option': None,
        }
        for seat_key in state['players']
    }
    state['coordination']['room_decision'] = {
        'decision_id': room_id,
        'room_id': room_id,
        'policy': 'per_player_barrier',
        'resolved_seats': [],
    }
    return [{
        'type': 'coop_room_started',
        'room_id': room_id,
        'room_type': 'rest',
        'node_id': str(node_id),
        'floor': int(node.get('floor') or 0),
    }]


def _start_coop_chest_room(state, node_id, run_seed):
    nodes = _coop_map_nodes(state)
    node = nodes.get(str(node_id))
    if not isinstance(node, dict) or str(node.get('type') or '') != 'chest':
        _fail('UNSUPPORTED_COOP_ROUTE', '当前节点不是协作宝箱房')
    room_id = f'chest:{node_id}'
    state['phase'] = 'room'
    state['combat'] = None
    state['room'] = {
        'id': room_id,
        'type': 'chest',
        'node_id': str(node_id),
        'title': {'zh': '协作补给箱', 'en': 'Cooperative Supply Chest'},
        'policy': 'per_player_barrier',
    }
    private_states = {}
    current_content = state.get('content_version') == COOP_STORY_CONTENT_VERSION
    for seat_key in sorted(state['players'], key=int):
        owned = set(state['players'][seat_key].get('relics') or [])
        relic_order = (
            _deterministic_value_order(
                state,
                [
                    relic_id for relic_id in COOP_CHEST_RELIC_IDS
                    if relic_id not in owned
                    or (COOP_STORY_CONTENT.relic_definition(relic_id) or {}).get('stackable')
                ],
                str(run_seed),
                f'coop_chest_relic:{node_id}:seat:{int(seat_key)}',
            )
            if current_content
            else []
        )
        relic_id = relic_order[0] if relic_order else None
        private = {
            'status': 'pending',
            'options': ['claim_gold', *(['claim_relic'] if relic_id else []), 'leave'],
            'gold': _deterministic_int(
                state,
                str(run_seed),
                f'coop_chest:{node_id}:seat:{int(seat_key)}',
                40,
                60,
            ),
            'selected_option': None,
        }
        if current_content:
            private['relic_id'] = relic_id
        private_states[seat_key] = private
    state['room_states_by_player'] = private_states
    state['coordination']['room_decision'] = {
        'decision_id': room_id,
        'room_id': room_id,
        'policy': 'per_player_barrier',
        'resolved_seats': [],
    }
    return [{
        'type': 'coop_room_started',
        'room_id': room_id,
        'room_type': 'chest',
        'node_id': str(node_id),
        'floor': int(node.get('floor') or 0),
    }]


def _shop_discount_ratio(player):
    discounts = _compiled_player_relics(player, 'shop_discount') if player else []
    numerator = 1
    denominator = 1
    for _, definition in discounts:
        discount = min(100, max(0, int(definition.get('amount') or 0)))
        numerator *= 100 - discount
        denominator *= 100
    return numerator, denominator


def _apply_shop_price_rules(value, difficulty='normal', player=None):
    if str(difficulty or 'normal') in {'hard', 'lunatic'}:
        value = (int(value) * 11 + 9) // 10
    numerator, denominator = _shop_discount_ratio(player)
    if numerator < denominator:
        value = max(1, int(value) * numerator // denominator)
    return int(value)


def _shop_card_price(card_id, difficulty='normal', player=None):
    definition = COOP_STORY_CONTENT.card_definition(str(card_id)) or {}
    rarity = str(definition.get('rarity') or 'common')
    prices = {'common': 50, 'rare': 75, 'ultra': 150}
    if rarity not in prices:
        _fail('UNSUPPORTED_COOP_CARD', '协作商店卡牌稀有度无效')
    return _apply_shop_price_rules(prices[rarity], difficulty, player)


def _shop_relic_price(relic_id, difficulty='normal', player=None):
    definition = COOP_STORY_CONTENT.relic_definition(str(relic_id)) or {}
    rarity = str(definition.get('rarity') or '')
    prices = {'common': 175, 'rare': 225, 'ultra': 275}
    if rarity not in prices:
        _fail('UNSUPPORTED_COOP_RELIC', '协作商店遗物稀有度无效')
    return _apply_shop_price_rules(prices[rarity], difficulty, player)


def _shop_enchantment_book_price(
        book_id, difficulty='normal', player=None, *, listed_base=None):
    definition = STORY_ENCHANTMENT_BOOKS.get(str(book_id)) or {}
    rarity = str(definition.get('rarity') or '')
    prices = {'common': 45, 'rare': 70, 'ultra': 130}
    if rarity not in prices:
        _fail('UNKNOWN_ENCHANTMENT_BOOK', '协作商店附魔书稀有度无效')
    base = prices[rarity]
    if listed_base is not None:
        if (
            isinstance(listed_base, bool)
            or not isinstance(listed_base, int)
            or not math.floor(base * 0.9) <= listed_base <= math.ceil(base * 1.1)
        ):
            _fail('INVALID_COOP_ROOM', '协作商店附魔书浮动价格无效')
        base = listed_base
    return _apply_shop_price_rules(base, difficulty, player)


def _refresh_available_shop_prices(private, player, difficulty):
    for offer in private.get('offers') or []:
        if not isinstance(offer, dict) or offer.get('status') != 'available':
            continue
        kind = str(offer.get('kind') or 'card')
        item_id = str(offer.get('item_id') or offer.get('card_id') or '')
        offer['price'] = (
            _shop_card_price(item_id, difficulty, player)
            if kind == 'card'
            else _shop_relic_price(item_id, difficulty, player)
            if kind == 'relic'
            else _shop_enchantment_book_price(
                item_id,
                difficulty,
                player,
                listed_base=offer.get('base_price'),
            )
        )


def _start_coop_shop_room(state, node_id, run_seed):
    nodes = _coop_map_nodes(state)
    node = nodes.get(str(node_id))
    if not isinstance(node, dict) or str(node.get('type') or '') != 'shop':
        _fail('UNSUPPORTED_COOP_ROUTE', '当前节点不是协作商店')
    room_id = f'shop:{node_id}'
    state['phase'] = 'room'
    state['combat'] = None
    state['room'] = {
        'id': room_id,
        'type': 'shop',
        'node_id': str(node_id),
        'title': {'zh': '协作个人商店', 'en': 'Cooperative Personal Shop'},
        'policy': 'per_player_barrier',
    }
    private_states = {}
    current_content = state.get('content_version') == COOP_STORY_CONTENT_VERSION
    for seat_key in sorted(state['players'], key=int):
        seat = int(seat_key)
        player = state['players'][seat_key]
        cards = _deterministic_value_order(
            state,
            _coop_card_pool_for_player(
                state,
                seat,
                COOP_SHOP_CARD_IDS,
                include_neutral=True,
            ),
            str(run_seed),
            f'coop_shop:{node_id}:seat:{seat}',
        )[:3]
        relics = _deterministic_value_order(
            state,
            [
                relic_id for relic_id in COOP_SHOP_RELIC_IDS
                if relic_id not in set(player.get('relics') or [])
                or (COOP_STORY_CONTENT.relic_definition(relic_id) or {}).get('stackable')
            ],
            str(run_seed),
            f'coop_shop_relic:{node_id}:seat:{seat}',
        )[:1] if current_content else []
        books = [
            _coop_enchantment_book_offer(
                state,
                seat,
                str(run_seed),
                f'coop_shop:{node_id}',
                rarity=rarity,
            )
            for rarity in ('common', 'rare', 'ultra')
        ] if current_content else []
        if current_content:
            offers = [
                {
                    'offer_id': f'shop:{node_id}:seat:{seat}:card:{index}:{card_id}',
                    'kind': 'card',
                    'item_id': card_id,
                    'card_id': card_id,
                    'upgraded': False,
                    'price': _shop_card_price(card_id, state.get('difficulty'), player),
                    'status': 'available',
                    'item_instance_id': None,
                }
                for index, card_id in enumerate(cards)
            ]
            offers.extend(
                {
                    'offer_id': f'shop:{node_id}:seat:{seat}:relic:{index}:{relic_id}',
                    'kind': 'relic',
                    'item_id': relic_id,
                    'relic_id': relic_id,
                    'price': _shop_relic_price(relic_id, state.get('difficulty'), player),
                    'status': 'available',
                    'item_instance_id': None,
                }
                for index, relic_id in enumerate(relics)
            )
            for index, book_id in enumerate(books):
                rarity = STORY_ENCHANTMENT_BOOKS[book_id]['rarity']
                base = {'common': 45, 'rare': 70, 'ultra': 130}[rarity]
                listed_base = _deterministic_int(
                    state,
                    str(run_seed),
                    f'coop_shop_book_price:{node_id}:seat:{seat}:{book_id}',
                    math.floor(base * 0.9),
                    math.ceil(base * 1.1),
                )
                offers.append({
                    'offer_id': f'shop:{node_id}:seat:{seat}:enchantment_book:{index}:{book_id}',
                    'kind': 'enchantment_book',
                    'item_id': book_id,
                    'book_id': book_id,
                    'base_price': listed_base,
                    'price': _shop_enchantment_book_price(
                        book_id,
                        state.get('difficulty'),
                        player,
                        listed_base=listed_base,
                    ),
                    'status': 'available',
                    'item_instance_id': None,
                })
        else:
            offers = [
                {
                    'offer_id': f'shop:{node_id}:seat:{seat}:offer:{index}:{card_id}',
                    'card_id': card_id,
                    'upgraded': False,
                    'price': _shop_card_price(card_id, state.get('difficulty')),
                    'status': 'available',
                    'card_instance_id': None,
                }
                for index, card_id in enumerate(cards)
            ]
        private_states[seat_key] = {
            'status': 'pending',
            'options': (
                ['buy_card', *(['buy_relic'] if relics else []), 'leave']
                if not books
                else [
                    'buy_card',
                    *(['buy_relic'] if relics else []),
                    'buy_enchantment_book',
                    'leave',
                ]
                if current_content
                else ['buy_card', 'leave']
            ),
            'offers': offers,
            'selected_option': None,
        }
    state['room_states_by_player'] = private_states
    state['coordination']['room_decision'] = {
        'decision_id': room_id,
        'room_id': room_id,
        'policy': 'per_player_barrier',
        'resolved_seats': [],
    }
    return [{
        'type': 'coop_room_started',
        'room_id': room_id,
        'room_type': 'shop',
        'node_id': str(node_id),
        'floor': int(node.get('floor') or 0),
    }]


def _coop_event_definition_for_state(state, event_id, stored_definition=None):
    if str(state.get('content_version') or '') == COOP_STORY_CONTENT_VERSION:
        adapted = COOP_ADAPTED_EVENT_DEFINITIONS.get(str(state.get('biome') or ''))
        definition = (
            adapted
            if isinstance(adapted, dict) and str(adapted.get('id') or '') == str(event_id or '')
            else COOP_STORY_CONTENT.event_definition(event_id)
        )
        if not isinstance(definition, dict):
            _fail('UNSUPPORTED_COOP_EVENT', '共享故事事件已经不再兼容当前协作执行器')
        if 'id' in definition:
            definition = {key: deepcopy(value) for key, value in definition.items() if key != 'id'}
        try:
            definition = validate_compiled_coop_event_definition(event_id, definition)
        except CoopStoryContentError:
            _fail('UNSUPPORTED_COOP_EVENT', '共享故事事件已经不再兼容当前协作执行器')
        if stored_definition is not None and stored_definition != definition:
            _fail('INVALID_COOP_ROOM', '协作事件快照与当前内容版本不一致')
        return definition
    if stored_definition is not None:
        try:
            return validate_compiled_coop_event_definition(event_id, stored_definition)
        except CoopStoryContentError:
            _fail('INVALID_COOP_ROOM', '历史协作事件快照无效')
    if str(event_id or '') != COOP_GARDEN_EVENT_ID:
        _fail('UNSUPPORTED_COOP_EVENT', '历史协作事件标识无效')
    return deepcopy(COOP_LEGACY_GARDEN_EVENT_DEFINITION)


def _coop_event_option_ids(definition):
    return tuple(
        str(option.get('id') or '')
        for option in (definition or {}).get('options') or ()
        if isinstance(option, dict)
    )


def _start_coop_event_room(state, node_id, run_seed):
    nodes = _coop_map_nodes(state)
    node = nodes.get(str(node_id))
    if not isinstance(node, dict) or str(node.get('type') or '') != 'event':
        _fail('UNSUPPORTED_COOP_ROUTE', '当前节点不是协作事件房')
    room_id = f'event:{node_id}'
    if str(state.get('content_version') or '') == COOP_STORY_CONTENT_VERSION:
        biome = str(state.get('biome') or '')
        event_ids = list(COOP_STORY_CONTENT.event_ids(biome))
        adapted = COOP_ADAPTED_EVENT_DEFINITIONS.get(biome)
        if not event_ids and isinstance(adapted, dict):
            event_ids.append(str(adapted.get('id') or ''))
        if not event_ids:
            _fail('UNSUPPORTED_COOP_EVENT', '当前生物群系没有兼容的共享故事事件')
        content_id = (
            event_ids[0]
            if len(event_ids) == 1
            else _deterministic_value_order(
                state,
                event_ids,
                str(run_seed),
                f'coop_event_content:{node_id}',
            )[0]
        )
    else:
        content_id = COOP_GARDEN_EVENT_ID
    definition = _coop_event_definition_for_state(state, content_id)
    option_ids = _coop_event_option_ids(definition)
    policy = str((definition.get('coop') or {}).get('policy') or '')
    state['phase'] = 'room'
    state['combat'] = None
    state['room'] = {
        'id': room_id,
        'type': 'event',
        'node_id': str(node_id),
        'content_id': content_id,
        'title': deepcopy(definition.get('title')),
        'description': deepcopy(definition.get('description')),
        'policy': policy,
    }
    if str(state.get('content_version') or '') == COOP_STORY_CONTENT_VERSION:
        state['room']['content_snapshot'] = deepcopy(definition)
    state['room_states_by_player'] = {
        seat_key: {
            'status': 'pending',
            'options': list(option_ids),
            'selected_option': None,
        }
        for seat_key in state['players']
    }
    state['coordination']['room_decision'] = {
        'decision_id': room_id,
        'room_id': room_id,
        'policy': policy,
        'resolved_seats': [],
        'votes_by_seat': {},
        'resolved_option_id': None,
    }
    return [{
        'type': 'coop_room_started',
        'room_id': room_id,
        'room_type': 'event',
        'node_id': str(node_id),
        'floor': int(node.get('floor') or 0),
    }]


def _enter_selected_coop_node(state, node_id, run_seed):
    nodes = _coop_map_nodes(state)
    node = nodes.get(str(node_id))
    if not isinstance(node, dict) or node.get('status') != 'available':
        _fail('INVALID_COOP_ROUTE', '该协作路线当前不可进入')
    for candidate in nodes.values():
        if candidate.get('status') == 'available':
            candidate['status'] = 'locked'
    node['status'] = 'current'
    state['current_node_id'] = str(node_id)
    state['current_floor'] = int(node.get('floor') or 0)
    state['coordination']['map_vote'] = None
    node_type = str(node.get('type') or '')
    if node_type in {'combat', 'elite', 'boss'}:
        return _start_coop_combat_for_node(state, node_id, str(run_seed))
    if node_type == 'rest':
        return state, _start_coop_rest_room(state, node_id)
    if node_type == 'chest':
        return state, _start_coop_chest_room(state, node_id, str(run_seed))
    if node_type == 'shop':
        return state, _start_coop_shop_room(state, node_id, str(run_seed))
    if node_type == 'event':
        return state, _start_coop_event_room(state, node_id, run_seed)
    _fail('UNSUPPORTED_COOP_ROUTE', '该协作房间尚未接入')


def _resolve_rest_choice(state, actor_seat, payload, events):
    if set(payload) - {'room_id', 'choice', 'card_instance_id'}:
        _fail('INVALID_ACTION_PAYLOAD', '协作休息选择包含不支持的字段')
    room = state.get('room')
    decision = state.get('coordination', {}).get('room_decision')
    room_states = state.get('room_states_by_player')
    if (
        state.get('phase') != 'room'
        or not isinstance(room, dict)
        or room.get('type') != 'rest'
        or not isinstance(decision, dict)
        or not isinstance(room_states, dict)
    ):
        _fail('ROOM_ACTION_NOT_ALLOWED', '当前不能处理协作休息选择')
    room_id = str(payload.get('room_id') or '').strip()
    if room_id != str(room.get('id') or '') or room_id != str(decision.get('room_id') or ''):
        _fail('STALE_COOP_ROOM', '协作房间标识已经过期')
    seat_key = str(actor_seat)
    private = room_states.get(seat_key)
    if not isinstance(private, dict) or private.get('status') != 'pending':
        _fail('ROOM_ALREADY_RESOLVED', '你已经处理过当前协作房间')
    choice = str(payload.get('choice') or '').strip().lower()
    if choice not in private.get('options', []):
        _fail('INVALID_ROOM_OPTION', '协作休息选项无效')
    if choice != 'upgrade' and payload.get('card_instance_id'):
        _fail('INVALID_ACTION_PAYLOAD', '该休息选项不能携带卡牌')
    player = state['players'][seat_key]
    if choice == 'heal':
        maximum = int(player.get('max_health') or 0)
        before = int(player.get('health') or 0)
        amount = (maximum * 3 + 9) // 10
        player['health'] = min(maximum, before + amount)
        events.append({
            'type': 'coop_player_healed',
            'actor_seat': actor_seat,
            'amount': int(player['health']) - before,
            'source': 'rest',
        })
    elif choice == 'upgrade':
        instance_id = str(payload.get('card_instance_id') or '').strip()
        card = next(
            (
                item for item in player.get('deck') or []
                if _card_instance_id(item) == instance_id
            ),
            None,
        )
        if card is None:
            _fail('INVALID_DECK_CARD', '请选择自己卡组中的牌')
        _card_values(card)
        if bool(card.get('upgraded')) or int(card.get('upgrade_level') or 0) > 0:
            _fail('CARD_NOT_UPGRADABLE', '这张牌已经升级')
        card['upgraded'] = True
        card['upgrade_level'] = 1
        events.append({
            'type': 'coop_card_upgraded',
            'actor_seat': actor_seat,
            'card_instance_id': instance_id,
            'source': 'rest',
        })
    elif choice == 'gold':
        relics = _compiled_player_relics(player, 'rest_gold')
        if not relics:
            _fail('INVALID_ROOM_OPTION', '你没有可在休息处换取金币的遗物')
        amount = sum(int(definition.get('amount') or 0) for _, definition in relics)
        player['gold'] = int(player.get('gold') or 0) + amount
        events.append({
            'type': 'coop_rest_gold_gained',
            'actor_seat': actor_seat,
            'room_id': room_id,
        })
    private['status'] = 'resolved'
    private['selected_option'] = choice
    resolved = decision.get('resolved_seats')
    if not isinstance(resolved, list) or actor_seat in resolved:
        _fail('INVALID_COOP_ROOM', '协作房间完成状态无效')
    resolved.append(actor_seat)
    resolved.sort()
    events.append({
        'type': 'coop_room_seat_resolved',
        'actor_seat': actor_seat,
        'room_id': room_id,
        'room_type': 'rest',
    })
    if set(resolved) == {int(seat) for seat in state['players']}:
        state['room_states_by_player'] = None
        state['coordination']['room_decision'] = None
        _begin_route_vote(state, events)


def _resolve_chest_choice(state, actor_seat, payload, events):
    if set(payload) - {'room_id', 'choice'}:
        _fail('INVALID_ACTION_PAYLOAD', '协作宝箱选择包含不支持的字段')
    room = state.get('room')
    decision = state.get('coordination', {}).get('room_decision')
    room_states = state.get('room_states_by_player')
    if (
        state.get('phase') != 'room'
        or not isinstance(room, dict)
        or room.get('type') != 'chest'
        or not isinstance(decision, dict)
        or not isinstance(room_states, dict)
    ):
        _fail('ROOM_ACTION_NOT_ALLOWED', '当前不能处理协作宝箱选择')
    room_id = str(payload.get('room_id') or '').strip()
    if room_id != str(room.get('id') or '') or room_id != str(decision.get('room_id') or ''):
        _fail('STALE_COOP_ROOM', '协作房间标识已经过期')
    seat_key = str(actor_seat)
    private = room_states.get(seat_key)
    if not isinstance(private, dict) or private.get('status') != 'pending':
        _fail('ROOM_ALREADY_RESOLVED', '你已经处理过当前协作房间')
    choice = str(payload.get('choice') or '').strip().lower()
    if choice not in private.get('options', []):
        _fail('INVALID_ROOM_OPTION', '协作宝箱选项无效')
    if choice == 'claim_gold':
        amount = private.get('gold')
        if isinstance(amount, bool) or not isinstance(amount, int) or not 40 <= amount <= 60:
            _fail('INVALID_COOP_ROOM', '协作宝箱金币状态无效')
        player = state['players'][seat_key]
        player['gold'] = int(player.get('gold') or 0) + amount
        events.append({
            'type': 'coop_chest_gold_claimed',
            'actor_seat': actor_seat,
            'room_id': room_id,
            'amount': amount,
        })
    elif choice == 'claim_relic':
        relic_id = str(private.get('relic_id') or '')
        if relic_id not in COOP_CHEST_RELIC_IDS:
            _fail('INVALID_COOP_ROOM', '协作宝箱遗物状态无效')
        _gain_compiled_relic(
            state,
            actor_seat,
            relic_id,
            events,
            f'chest:{room_id}',
        )
    private['status'] = 'resolved'
    private['selected_option'] = choice
    resolved = decision.get('resolved_seats')
    if not isinstance(resolved, list) or actor_seat in resolved:
        _fail('INVALID_COOP_ROOM', '协作房间完成状态无效')
    resolved.append(actor_seat)
    resolved.sort()
    events.append({
        'type': 'coop_room_seat_resolved',
        'actor_seat': actor_seat,
        'room_id': room_id,
        'room_type': 'chest',
    })
    if set(resolved) == {int(seat) for seat in state['players']}:
        state['room_states_by_player'] = None
        state['coordination']['room_decision'] = None
        _begin_route_vote(state, events)


def _resolve_shop_buy(state, actor_seat, payload, run_seed, events):
    if set(payload) - {'room_id', 'offer_id', 'replace_book_instance_id'}:
        _fail('INVALID_ACTION_PAYLOAD', '协作商店购买包含不支持的字段')
    room = state.get('room')
    room_states = state.get('room_states_by_player')
    if (
        state.get('phase') != 'room'
        or not isinstance(room, dict)
        or room.get('type') != 'shop'
        or not isinstance(room_states, dict)
    ):
        _fail('SHOP_ACTION_NOT_ALLOWED', '当前不能在协作商店购买')
    room_id = str(payload.get('room_id') or '').strip()
    if room_id != str(room.get('id') or ''):
        _fail('STALE_COOP_ROOM', '协作房间标识已经过期')
    private = room_states.get(str(actor_seat))
    if not isinstance(private, dict) or private.get('status') != 'pending':
        _fail('ROOM_ALREADY_RESOLVED', '你已经离开当前协作商店')
    offer_id = str(payload.get('offer_id') or '').strip()
    offer = next(
        (
            item for item in private.get('offers') or []
            if isinstance(item, dict) and item.get('offer_id') == offer_id
        ),
        None,
    )
    if offer is None:
        _fail('INVALID_SHOP_OFFER', '该商品不在你的协作商店中')
    if offer.get('status') != 'available':
        _fail('SHOP_OFFER_ALREADY_PURCHASED', '该商品已经购买')
    current_content = state.get('content_version') == COOP_STORY_CONTENT_VERSION
    kind = str(offer.get('kind') or 'card')
    item_id = str(offer.get('item_id') or offer.get('card_id') or '')
    price = offer.get('price')
    player = state['players'][str(actor_seat)]
    expected_price = (
        _shop_card_price(
            item_id,
            state.get('difficulty'),
            player if current_content else None,
        )
        if kind == 'card'
        else _shop_relic_price(item_id, state.get('difficulty'), player)
        if kind == 'relic'
        else _shop_enchantment_book_price(
            item_id,
            state.get('difficulty'),
            player,
            listed_base=offer.get('base_price'),
        )
        if kind == 'enchantment_book'
        else None
    )
    if price != expected_price:
        _fail('INVALID_COOP_ROOM', '协作商店商品价格无效')
    if int(player.get('gold') or 0) < price:
        _fail('INSUFFICIENT_STORY_GOLD', '金币不足，无法购买该商品')
    player['gold'] = int(player.get('gold') or 0) - price
    if kind == 'card':
        item = _gain_reward_card(
            state,
            actor_seat,
            item_id,
            bool(offer.get('upgraded')),
            str(run_seed),
            offer_id,
            events,
        )
        item_instance_id = _card_instance_id(item)
    elif kind == 'relic':
        _gain_compiled_relic(
            state,
            actor_seat,
            item_id,
            events,
            f'shop:{offer_id}',
        )
        item_instance_id = item_id
    else:
        item = _gain_coop_enchantment_book(
            state,
            actor_seat,
            item_id,
            events,
            source='shop',
            replace_instance_id=payload.get('replace_book_instance_id'),
        )
        item_instance_id = item['instance_id']
    offer['status'] = 'purchased'
    if current_content:
        offer['item_instance_id'] = item_instance_id
        _refresh_available_shop_prices(private, player, state.get('difficulty'))
    else:
        offer['card_instance_id'] = item_instance_id
    events.append({
        'type': 'coop_shop_purchase_completed',
        'actor_seat': actor_seat,
        'room_id': room_id,
    })


def _resolve_shop_leave(state, actor_seat, payload, events):
    if set(payload) - {'room_id', 'choice'}:
        _fail('INVALID_ACTION_PAYLOAD', '协作商店离开动作包含不支持的字段')
    room = state.get('room')
    decision = state.get('coordination', {}).get('room_decision')
    room_states = state.get('room_states_by_player')
    room_id = str(payload.get('room_id') or '').strip()
    if (
        state.get('phase') != 'room'
        or not isinstance(room, dict)
        or room.get('type') != 'shop'
        or not isinstance(decision, dict)
        or not isinstance(room_states, dict)
        or room_id != str(room.get('id') or '')
        or room_id != str(decision.get('room_id') or '')
    ):
        _fail('STALE_COOP_ROOM', '协作商店状态已经过期')
    if str(payload.get('choice') or '').strip().lower() != 'leave':
        _fail('INVALID_ROOM_OPTION', '协作商店只能在购买后选择离开')
    private = room_states.get(str(actor_seat))
    if not isinstance(private, dict) or private.get('status') != 'pending':
        _fail('ROOM_ALREADY_RESOLVED', '你已经离开当前协作商店')
    private['status'] = 'resolved'
    private['selected_option'] = 'leave'
    resolved = decision.get('resolved_seats')
    if not isinstance(resolved, list) or actor_seat in resolved:
        _fail('INVALID_COOP_ROOM', '协作商店完成状态无效')
    resolved.append(actor_seat)
    resolved.sort()
    events.append({
        'type': 'coop_room_seat_resolved',
        'actor_seat': actor_seat,
        'room_id': room_id,
        'room_type': 'shop',
    })
    if set(resolved) == {int(seat) for seat in state['players']}:
        state['room_states_by_player'] = None
        state['coordination']['room_decision'] = None
        _begin_route_vote(state, events)


def _resolve_event_choice(state, actor_seat, payload, run_seed, events):
    if set(payload) - {'room_id', 'choice'}:
        _fail('INVALID_ACTION_PAYLOAD', '协作事件选择包含不支持的字段')
    room = state.get('room')
    decision = state.get('coordination', {}).get('room_decision')
    room_states = state.get('room_states_by_player')
    room_id = str(payload.get('room_id') or '').strip()
    if (
        state.get('phase') != 'room'
        or not isinstance(room, dict)
        or room.get('type') != 'event'
        or not isinstance(decision, dict)
        or not isinstance(room_states, dict)
        or room_id != str(room.get('id') or '')
        or room_id != str(decision.get('room_id') or '')
    ):
        _fail('STALE_COOP_ROOM', '协作事件状态已经过期')
    seat_key = str(actor_seat)
    private = room_states.get(seat_key)
    if not isinstance(private, dict) or private.get('status') != 'pending':
        _fail('ROOM_ALREADY_RESOLVED', '你已经提交过当前协作事件选择')
    choice = str(payload.get('choice') or '').strip().lower()
    if choice not in private.get('options', []):
        _fail('INVALID_ROOM_OPTION', '协作事件选项无效')
    votes = decision.get('votes_by_seat')
    resolved = decision.get('resolved_seats')
    if not isinstance(votes, dict) or not isinstance(resolved, list) or seat_key in votes:
        _fail('INVALID_COOP_ROOM', '协作事件投票状态无效')
    private['status'] = 'resolved'
    private['selected_option'] = choice
    votes[seat_key] = choice
    resolved.append(actor_seat)
    resolved.sort()
    events.append({
        'type': 'coop_event_vote_cast',
        'actor_seat': actor_seat,
        'room_id': room_id,
    })
    if set(votes) != set(state['players']):
        return
    voted_options = sorted(set(votes.values()))
    if len(voted_options) != 1:
        # Shared events change the whole party, so disagreement must never
        # silently force one player's risky choice onto the other.  Once every
        # seat has submitted, clear only this decision round and let the party
        # vote again.  No effect or RNG stream is consumed.
        for seat_private in room_states.values():
            seat_private['status'] = 'pending'
            seat_private['selected_option'] = None
        votes.clear()
        resolved.clear()
        events.append({
            'type': 'coop_event_consensus_required',
            'room_id': room_id,
            'room_type': 'event',
        })
        return
    selected = voted_options[0]
    decision['resolved_option_id'] = selected
    definition = _coop_event_definition_for_state(
        state,
        room.get('content_id'),
        room.get('content_snapshot'),
    )
    option = next(
        (
            candidate for candidate in definition.get('options') or ()
            if str(candidate.get('id') or '') == selected
        ),
        None,
    )
    if not isinstance(option, dict):
        _fail('UNSUPPORTED_COOP_EVENT', '共享故事事件选项已经不再兼容')
    for effect in option.get('effects') or ():
        effect_type = str(effect.get('type') or '')
        amount = int(effect.get('amount') or 0)
        if effect_type == 'heal':
            for player in state['players'].values():
                maximum = int(player.get('max_health') or 0)
                player['health'] = min(maximum, int(player.get('health') or 0) + amount)
        elif effect_type == 'gold':
            for player in state['players'].values():
                player['gold'] = int(player.get('gold') or 0) + amount
        elif effect_type == 'health_loss' and effect.get('nonlethal') is True:
            for player in state['players'].values():
                player['health'] = max(1, int(player.get('health') or 0) - amount)
        else:
            _fail('UNSUPPORTED_COOP_EVENT', '共享故事事件包含未接入的效果')
    events.append({
        'type': 'coop_event_resolved',
        'room_id': room_id,
        'room_type': 'event',
        'choice': selected,
        'content_id': str(room.get('content_id') or ''),
        'reason': 'unanimous',
    })
    state['room_states_by_player'] = None
    state['coordination']['room_decision'] = None
    _begin_route_vote(state, events)


def _resolve_route_vote(state, actor_seat, payload, run_seed, events):
    if set(payload) - {'vote_id', 'node_id'}:
        _fail('INVALID_ACTION_PAYLOAD', '协作路线投票包含不支持的字段')
    vote = state.get('coordination', {}).get('map_vote')
    if not isinstance(vote, dict):
        _fail('INVALID_COOP_MAP_VOTE', '协作路线投票状态无效')
    vote_id = str(payload.get('vote_id') or '').strip()
    if vote_id != str(vote.get('vote_id') or ''):
        _fail('STALE_COOP_MAP_VOTE', '协作路线投票标识已经过期')
    votes = vote.get('votes_by_seat')
    if not isinstance(votes, dict):
        _fail('INVALID_COOP_MAP_VOTE', '协作路线投票状态无效')
    seat_key = str(actor_seat)
    if seat_key in votes:
        _fail('MAP_VOTE_ALREADY_CAST', '你已经提交过本次路线投票')
    node_id = str(payload.get('node_id') or '').strip()
    options = vote.get('option_node_ids')
    if not isinstance(options, list) or node_id not in options:
        _fail('INVALID_COOP_ROUTE', '该路线不在当前可选节点中')
    nodes = _coop_map_nodes(state)
    if node_id not in nodes or nodes[node_id].get('status') != 'available':
        _fail('INVALID_COOP_ROUTE', '该路线当前不可到达')
    votes[seat_key] = node_id
    events.append({
        'type': 'coop_route_vote_cast',
        'actor_seat': actor_seat,
        'vote_id': vote_id,
    })
    if set(votes) != set(state['players']):
        return state
    voted_nodes = sorted(set(votes.values()))
    selected = (
        voted_nodes[0]
        if len(voted_nodes) == 1
        else _deterministic_value_order(
            state,
            voted_nodes,
            str(run_seed),
            f'coop_route_vote:{vote_id}',
        )[0]
    )
    vote['resolved_node_id'] = selected
    events.append({
        'type': 'coop_route_vote_resolved',
        'vote_id': vote_id,
        'node_id': selected,
        'reason': 'unanimous' if len(voted_nodes) == 1 else 'seeded_random',
    })
    next_state, start_events = _enter_selected_coop_node(state, selected, str(run_seed))
    events.extend(start_events)
    return next_state


def _coop_journey_fingerprint(actor_seat, action_type, payload):
    try:
        canonical = json.dumps(
            {
                'actor_seat': int(actor_seat),
                'action_type': str(action_type),
                'payload': payload,
            },
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(',', ':'),
        ).encode('utf-8')
    except (TypeError, ValueError) as exc:
        raise CoopCombatError('INVALID_ACTION_PAYLOAD', '协作旅程动作必须可安全序列化') from exc
    return hashlib.sha256(canonical).hexdigest()


def apply_coop_journey_command(
    source_state,
    *,
    authenticated_user_id,
    action_id,
    action_type,
    payload,
    run_seed,
    expected_sequence,
):
    """Apply one opening, reward, route or personal-room command as a pure action."""

    # This resolver is also used directly by pure tests and future transports;
    # reject corrupted phase-specific state before copying or mutating it.
    validate_coop_live_state(source_state)
    actor_seat = story_seat_for_user(source_state, authenticated_user_id)
    if actor_seat is None:
        _fail('NOT_PARTY_MEMBER', '当前账号不是该协作旅程成员')
    action_id = str(action_id or '').strip()
    if not re.fullmatch(r'[A-Za-z0-9._:-]{8,128}', action_id):
        _fail('INVALID_ACTION_ID', '协作动作标识无效')
    action_type = str(action_type or '').strip().lower()
    if action_type not in {
        'setup_start', 'opening_choose', 'reward_choose', 'map_vote',
        'room_choose', 'shop_buy', 'stage_ready', 'discard_enchantment_book'
    }:
        _fail('UNSUPPORTED_COOP_ACTION', '当前协作旅程不支持该动作')
    if not isinstance(payload, dict):
        _fail('INVALID_ACTION_PAYLOAD', '协作旅程动作数据无效')
    if {'actor_seat', 'actor_user_id'}.intersection(payload):
        _fail('FORGED_ACTOR', '行动者只能由服务器认证信息决定')
    current_sequence = source_state['coordination'].get('action_sequence')
    if (
        isinstance(expected_sequence, bool)
        or not isinstance(expected_sequence, int)
        or expected_sequence < 0
        or expected_sequence != current_sequence
    ):
        _fail('STALE_ACTION_SEQUENCE', '协作旅程动作序号已经过期')
    if action_type == 'reward_choose' and source_state.get('phase') != 'reward':
        _fail('REWARD_ACTION_NOT_ALLOWED', '当前不能处理协作奖励')
    if action_type == 'setup_start' and source_state.get('phase') != 'journey_setup':
        _fail('SETUP_ACTION_NOT_ALLOWED', '当前不能设置协作旅程')
    if action_type == 'opening_choose' and (
        source_state.get('phase') != 'room'
        or (source_state.get('room') or {}).get('type') != 'opening'
    ):
        _fail('OPENING_ACTION_NOT_ALLOWED', '当前不能提交协作开局选择')
    if action_type == 'map_vote' and source_state.get('phase') != 'map':
        _fail('MAP_VOTE_NOT_ALLOWED', '当前不能提交协作路线投票')
    if action_type == 'stage_ready' and source_state.get('phase') != 'stage_complete':
        _fail('STAGE_READY_NOT_ALLOWED', '当前不能确认协作阶段')
    if action_type == 'room_choose' and source_state.get('phase') != 'room':
        _fail('ROOM_ACTION_NOT_ALLOWED', '当前不能提交协作房间选择')
    if action_type == 'shop_buy' and (
        source_state.get('phase') != 'room'
        or (source_state.get('room') or {}).get('type') != 'shop'
    ):
        _fail('SHOP_ACTION_NOT_ALLOWED', '当前不能在协作商店购买')
    if action_type == 'discard_enchantment_book' and source_state.get('phase') == 'combat':
        _fail('ENCHANTMENT_BOOK_ACTION_NOT_ALLOWED', '战斗中请使用战斗附魔书动作')

    state = deepcopy(source_state)
    events = []
    if action_type == 'setup_start':
        if int(actor_seat) != int(source_state['party'].get('leader_seat') or 0):
            _fail('COOP_PARTY_LEADER_REQUIRED', '只有队长可以设置协作旅程')
        if set(payload) != {'difficulty'}:
            _fail('INVALID_ACTION_PAYLOAD', '协作旅程设置只能提交难度')
        state, setup_events = start_coop_stage1_opening(
            state,
            run_seed=str(run_seed),
            difficulty=payload.get('difficulty'),
        )
        events.extend(_strip_event_indexes(setup_events))
    elif action_type == 'opening_choose':
        _resolve_opening_choice(state, actor_seat, payload, str(run_seed), events)
    elif action_type == 'reward_choose':
        _resolve_reward_choice(state, actor_seat, payload, str(run_seed), events)
    elif action_type == 'map_vote':
        state = _resolve_route_vote(state, actor_seat, payload, str(run_seed), events)
    elif action_type == 'stage_ready':
        _resolve_stage_ready(state, actor_seat, payload, str(run_seed), events)
    elif action_type == 'shop_buy':
        _resolve_shop_buy(state, actor_seat, payload, str(run_seed), events)
    elif action_type == 'discard_enchantment_book':
        _resolve_coop_enchantment_book_action(
            state,
            actor_seat,
            action_type,
            payload,
            str(run_seed),
            events,
        )
    elif (state.get('room') or {}).get('type') == 'rest':
        _resolve_rest_choice(state, actor_seat, payload, events)
    elif (state.get('room') or {}).get('type') == 'chest':
        _resolve_chest_choice(state, actor_seat, payload, events)
    elif (state.get('room') or {}).get('type') == 'shop':
        _resolve_shop_leave(state, actor_seat, payload, events)
    else:
        _resolve_event_choice(state, actor_seat, payload, str(run_seed), events)
    accepted_sequence = current_sequence + 1
    state['coordination']['action_sequence'] = accepted_sequence
    receipt = {
        'action_id': action_id,
        'actor_user_id': int(authenticated_user_id),
        'actor_seat': int(actor_seat),
        'action_type': action_type,
        'action_sequence': accepted_sequence,
        'request_fingerprint': _coop_journey_fingerprint(actor_seat, action_type, payload),
    }
    finalized_events = finalize_coop_action_events(events, accepted_sequence)
    validate_coop_live_state(state)
    return state, finalized_events, receipt


def _public_card(card):
    if not isinstance(card, dict):
        _fail('INVALID_CARD_STATE', '公开卡牌状态无效')
    _card_instance_id(card)
    def_id = str(card.get('def_id') or '').strip()
    if not def_id or len(def_id) > 128:
        _fail('INVALID_CARD_STATE', '公开卡牌定义标识无效')
    return {
        key: deepcopy(card[key])
        for key in (
            'instance_id', 'def_id', 'upgraded', 'upgrade_level',
            'charge_value', 'power_value', 'modifiers',
        )
        if key in card
    }


def _public_statuses(statuses):
    if not isinstance(statuses, dict):
        _fail('INVALID_SEAT_STATES', '公开状态集无效')
    public = {}
    for raw_key, value in statuses.items():
        key = str(raw_key or '').strip()
        if not re.fullmatch(r'[A-Za-z0-9._:-]{1,64}', key):
            _fail('INVALID_SEAT_STATES', '公开状态标识无效')
        if isinstance(value, (bool, int, float, str)) or value is None:
            public[key] = deepcopy(value)
    return public


def _public_intent(intent):
    intent = intent if isinstance(intent, dict) else {}
    return {
        key: deepcopy(intent[key])
        for key in ('kind', 'amount', 'hits', 'target_seat', 'move_name')
        if key in intent
    }


def _validate_current_compiled_combat(state, room):
    combat = state.get('combat') or {}
    if (
        str(state.get('content_version') or '') != COOP_STORY_CONTENT_VERSION
        or str(room.get('node_type') or '') != 'combat'
        or not (combat.get('enemies') or [])
        or any(
            enemy.get('content_source') != 'story_content'
            for enemy in combat.get('enemies') or []
        )
    ):
        return
    encounter = COOP_STORY_CONTENT.encounter_definition(combat.get('encounter_id'))
    enemies = combat.get('enemies') or []
    members = (encounter or {}).get('members')
    if (
        not isinstance(encounter, dict)
        or not isinstance(members, list)
        or len(members) != len(enemies)
    ):
        _fail('INVALID_COOP_ENCOUNTER', '协作战斗不再对应已编译的权威遭遇')
    for member, enemy in zip(members, enemies):
        definition = COOP_STORY_CONTENT.enemy_definition(member.get('def_id'))
        if (
            not isinstance(definition, dict)
            or enemy.get('content_source') != 'story_content'
            or enemy.get('def_id') != member.get('def_id')
            or enemy.get('name') != definition.get('name')
            or str(enemy.get('image_url') or '') != str(definition.get('image_url') or '')
        ):
            _fail('INVALID_COOP_ENEMY', '协作敌人不是当前权威内容的规范实例')
        base_health = (
            definition.get('lunatic_max_health', definition.get('max_health'))
            if str(state.get('difficulty') or 'normal') == 'lunatic'
            else definition.get('max_health')
        )
        expected_max_health = (
            int(base_health) * COOP_CANONICAL_ENEMY_HEALTH_NUMERATOR
            + COOP_CANONICAL_ENEMY_HEALTH_DENOMINATOR - 1
        ) // COOP_CANONICAL_ENEMY_HEALTH_DENOMINATOR
        if enemy.get('max_health') != expected_max_health:
            _fail('INVALID_COOP_ENEMY', '协作敌人最大生命与当前权威内容不一致')
        expected_intent = _compiled_enemy_intent(state, enemy, definition)
        if expected_intent.get('kind') == 'attack':
            expected_intent['target_seat'] = (enemy.get('intent') or {}).get('target_seat')
        if enemy.get('intent') != expected_intent:
            _fail('INVALID_COOP_ENEMY', '协作敌人意图与当前权威行动不一致')


def _validate_coop_live_state_legacy(state):
    """Frozen validator for the two-encounter pre-stage contract."""

    validate_story_state_v10(state, expected_mode='coop')
    phase = str(state.get('phase') or '')
    if phase not in {'combat', 'reward', 'map', 'complete', 'game_over'}:
        _fail('INVALID_COOP_PHASE', '协作旅程阶段无效')
    combat = state.get('combat')
    if isinstance(combat, dict):
        validate_coop_combat_state(state)
    elif phase in {'combat', 'game_over'}:
        _fail('INVALID_COMBAT_STATE', '协作战斗状态无效')
    progression = state.get('coop_progression')
    if not isinstance(progression, dict):
        _fail('INVALID_COOP_PROGRESSION', '协作章节进度无效')
    chapter = progression.get('chapter')
    encounter_index = progression.get('encounter_index')
    max_encounters = progression.get('max_encounters')
    completed_combat_ids = progression.get('completed_combat_ids')
    if (
        isinstance(chapter, bool)
        or chapter != 1
        or isinstance(encounter_index, bool)
        or not isinstance(encounter_index, int)
        or encounter_index not in {1, 2}
        or isinstance(max_encounters, bool)
        or not isinstance(max_encounters, int)
        or max_encounters != COOP_DEMO_MAX_ENCOUNTERS
        or not isinstance(completed_combat_ids, list)
        or any(
            not isinstance(combat_id, str)
            or not re.fullmatch(r'[A-Za-z0-9._:-]{1,96}', combat_id)
            for combat_id in completed_combat_ids
        )
        or len(completed_combat_ids) != len(set(completed_combat_ids))
    ):
        _fail('INVALID_COOP_PROGRESSION', '协作遭遇进度无效')
    completed_flag = state.get('completed')
    if not isinstance(completed_flag, bool) or completed_flag != (phase == 'complete'):
        _fail('INVALID_COOP_PROGRESSION', '协作章节完成标记与阶段不一致')
    room = state.get('room')
    if not isinstance(room, dict):
        _fail('INVALID_COOP_ROOM', '协作房间状态无效')
    nodes = _coop_map_nodes(state)
    current_node_id = str(state.get('current_node_id') or '')
    current_node = nodes.get(current_node_id)
    if current_node is None:
        _fail('INVALID_COOP_MAP', '协作旅程当前节点无效')
    current_floor = state.get('current_floor')
    node_floor = current_node.get('floor')
    if (
        isinstance(current_floor, bool)
        or not isinstance(current_floor, int)
        or isinstance(node_floor, bool)
        or not isinstance(node_floor, int)
        or node_floor <= 0
        or current_floor != node_floor
    ):
        _fail('INVALID_COOP_MAP', '协作旅程楼层与当前节点不一致')

    second_combat_id = f'garden-route-{current_node_id}'
    if phase in {'combat', 'game_over'}:
        expected_completed = [] if encounter_index == 1 else [COOP_INTRO_COMBAT_ID]
    elif phase in {'reward', 'map'}:
        expected_completed = [COOP_INTRO_COMBAT_ID]
    else:
        expected_completed = [COOP_INTRO_COMBAT_ID, second_combat_id]
    if completed_combat_ids != expected_completed:
        _fail('INVALID_COOP_PROGRESSION', '协作战斗完成记录与当前阶段不一致')
    if phase in {'reward', 'map'} and encounter_index != 1:
        _fail('INVALID_COOP_PROGRESSION', '协作奖励或路线阶段的遭遇进度无效')
    if phase == 'complete' and encounter_index != COOP_DEMO_MAX_ENCOUNTERS:
        _fail('INVALID_COOP_PROGRESSION', '协作章节完成时的遭遇进度无效')

    last_combat = state.get('last_combat')
    if completed_combat_ids:
        expected_last_id = completed_combat_ids[-1]
        expected_last_encounter = (
            COOP_INTRO_ENCOUNTER_ID
            if expected_last_id == COOP_INTRO_COMBAT_ID
            else COOP_SECOND_ENCOUNTER_ID
        )
        if (
            not isinstance(last_combat, dict)
            or str(last_combat.get('id') or '') != expected_last_id
            or str(last_combat.get('encounter_id') or '') != expected_last_encounter
            or last_combat.get('outcome') != 'victory'
            or isinstance(last_combat.get('round'), bool)
            or not isinstance(last_combat.get('round'), int)
            or last_combat.get('round') <= 0
        ):
            _fail('INVALID_COOP_PROGRESSION', '协作上一场战斗摘要无效')
    elif last_combat is not None:
        _fail('INVALID_COOP_PROGRESSION', '尚未获胜时不能保留战斗摘要')

    ready_seats = state['coordination'].get('combat_ready_seats')
    ready_round = state['coordination'].get('combat_ready_round')
    if phase == 'combat':
        expected_combat_id = COOP_INTRO_COMBAT_ID if encounter_index == 1 else second_combat_id
        expected_encounter_id = (
            COOP_INTRO_ENCOUNTER_ID
            if encounter_index == 1
            else COOP_SECOND_ENCOUNTER_ID
        )
        if (
            combat.get('id') != expected_combat_id
            or combat.get('encounter_id') != expected_encounter_id
            or combat.get('outcome') is not None
            or ready_round != combat.get('round')
            or room.get('type') != 'combat'
            or room.get('encounter_id') != expected_encounter_id
            or current_node.get('status') != 'current'
        ):
            _fail('INVALID_COOP_PROGRESSION', '协作战斗与章节进度不一致')
    elif phase == 'game_over':
        expected_combat_id = COOP_INTRO_COMBAT_ID if encounter_index == 1 else second_combat_id
        expected_encounter_id = (
            COOP_INTRO_ENCOUNTER_ID
            if encounter_index == 1
            else COOP_SECOND_ENCOUNTER_ID
        )
        if (
            combat.get('id') != expected_combat_id
            or combat.get('encounter_id') != expected_encounter_id
            or combat.get('outcome') != 'defeat'
            or ready_seats != []
            or ready_round is not None
            or room.get('type') != 'combat'
            or room.get('encounter_id') != expected_encounter_id
            or current_node.get('status') != 'current'
        ):
            _fail('INVALID_COOP_PROGRESSION', '协作失败状态与章节进度不一致')
    elif ready_seats != [] or ready_round is not None:
        _fail('INVALID_COMBAT_READY_STATE', '非战斗阶段不能保留战斗准备状态')
    for seat_key, player in state['players'].items():
        deck = player.get('deck')
        if not isinstance(deck, list):
            _fail('INVALID_PLAYER_DECK', '协作玩家卡组无效')
        ids = [_card_instance_id(card) for card in deck]
        if len(ids) != len(set(ids)):
            _fail('INVALID_PLAYER_DECK', '同一协作卡组不能包含重复实例')
        for card in deck:
            _validate_persisted_card(card, state.get('content_version'))

    rewards = state.get('rewards_by_player')
    map_vote = state['coordination'].get('map_vote')
    if phase == 'reward':
        if combat is not None or not isinstance(rewards, dict) or set(rewards) != set(state['players']):
            _fail('INVALID_COOP_REWARD', '协作奖励状态与队伍不一致')
        if map_vote is not None:
            _fail('INVALID_COOP_REWARD', '奖励阶段不能同时保留路线投票')
        if (
            room.get('type') != 'reward'
            or room.get('combat_id') != COOP_INTRO_COMBAT_ID
            or current_node.get('status') != 'current'
            or not isinstance(state.get('shared_reward'), dict)
            or state['shared_reward'].get('combat_id') != COOP_INTRO_COMBAT_ID
            or state['shared_reward'].get('gold_each') != COOP_REWARD_GOLD
        ):
            _fail('INVALID_COOP_REWARD', '协作奖励与战斗结算不一致')
        for seat_key, reward in rewards.items():
            if not isinstance(reward, dict) or reward.get('status') not in {'pending', 'resolved'}:
                _fail('INVALID_COOP_REWARD', '协作奖励状态无效')
            reward_id = str(reward.get('reward_id') or '')
            if (
                reward_id != f'reward:{COOP_INTRO_COMBAT_ID}:seat:{int(seat_key)}'
                or reward.get('gold') != COOP_REWARD_GOLD
                or not isinstance(reward.get('options'), list)
                or len(reward['options']) != 3
            ):
                _fail('INVALID_COOP_REWARD', '协作奖励选项无效')
            option_ids = []
            for option in reward['options']:
                if not isinstance(option, dict):
                    _fail('INVALID_COOP_REWARD', '协作奖励选项无效')
                card_id = str(option.get('card_id') or '')
                if card_id not in COOP_REWARD_CARD_IDS or not isinstance(option.get('upgraded'), bool):
                    _fail('INVALID_COOP_REWARD', '协作奖励卡牌无效')
                option_ids.append(card_id)
            if len(option_ids) != len(set(option_ids)):
                _fail('INVALID_COOP_REWARD', '协作奖励选项重复')
            selected_card_id = reward.get('selected_card_id')
            skipped = reward.get('skipped')
            if not isinstance(skipped, bool):
                _fail('INVALID_COOP_REWARD', '协作奖励选择状态无效')
            if reward.get('status') == 'pending' and (selected_card_id is not None or skipped):
                _fail('INVALID_COOP_REWARD', '未处理的协作奖励不能包含选择')
            if reward.get('status') == 'resolved' and (
                (selected_card_id is None) == (not skipped)
                or (selected_card_id is not None and selected_card_id not in option_ids)
            ):
                _fail('INVALID_COOP_REWARD', '已处理的协作奖励选择无效')
    elif rewards is not None or state.get('shared_reward') is not None:
        _fail('INVALID_COOP_REWARD', '非奖励阶段不能保留个人奖励')

    if phase == 'map':
        if combat is not None or not isinstance(map_vote, dict):
            _fail('INVALID_COOP_MAP_VOTE', '协作路线投票状态无效')
        from_node_id = str(map_vote.get('from_node_id') or '')
        options = map_vote.get('option_node_ids')
        votes = map_vote.get('votes_by_seat')
        valid_option_ids = bool(
            isinstance(options, list)
            and options
            and all(
                isinstance(node_id, str)
                and re.fullmatch(r'[A-Za-z0-9._:-]{1,96}', node_id)
                and node_id in nodes
                for node_id in options
            )
        )
        option_floors = [nodes[node_id].get('floor') for node_id in options] if valid_option_ids else []
        valid_option_floors = bool(
            option_floors
            and all(
                not isinstance(floor, bool) and isinstance(floor, int) and floor > 0
                for floor in option_floors
            )
        )
        option_floor = min(option_floors) if valid_option_floors else 0
        if (
            from_node_id not in nodes
            or not valid_option_ids
            or not valid_option_floors
            or len(options) != len(set(options))
            or options != _coop_outgoing_node_ids(state, from_node_id)
            or not isinstance(votes, dict)
            or any(seat not in state['players'] for seat in votes)
            or any(node_id not in options for node_id in votes.values())
            or str(state.get('current_node_id') or '') != from_node_id
            or nodes[from_node_id].get('status') != 'completed'
            or any(nodes[node_id].get('status') != 'available' for node_id in options)
            or any(str(nodes[node_id].get('type') or '') != 'combat' for node_id in options)
            or map_vote.get('resolved_node_id') is not None
            or str(map_vote.get('vote_id') or '') != f'route:{from_node_id}:floor:{option_floor}'
            or room.get('type') != 'map_vote'
            or room.get('vote_id') != map_vote.get('vote_id')
            or room.get('floor') != option_floor
        ):
            _fail('INVALID_COOP_MAP_VOTE', '协作路线投票与地图不一致')
    elif map_vote is not None:
        _fail('INVALID_COOP_MAP_VOTE', '非地图阶段不能保留路线投票')
    if phase == 'complete' and (
        combat is not None
        or room.get('type') != 'coop_complete'
        or current_node.get('status') != 'current'
    ):
        _fail('INVALID_COOP_COMPLETION', '协作章节完成状态无效')
    if phase in {'combat', 'game_over', 'complete'} and (rewards is not None or map_vote is not None):
        _fail('INVALID_COOP_PHASE', '协作旅程阶段保留了不兼容的决策状态')
    return True


def _validated_string_list(value, *, code, label):
    if (
        not isinstance(value, list)
        or any(
            not isinstance(item, str)
            or not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', item)
            for item in value
        )
        or len(value) != len(set(value))
    ):
        _fail(code, f'{label}无效')
    return value


def _validate_current_player_decks(state):
    content_version = str(state.get('content_version') or '')
    character_id = str(state.get('character_id') or 'common_flower')
    if content_version == COOP_STORY_CONTENT_VERSION:
        try:
            character_capability = COOP_STORY_CONTENT.capability('character', character_id)
        except CoopStoryContentError:
            _fail('UNSUPPORTED_COOP_CHARACTER', '协作故事角色不存在')
        if character_capability.get('state') != 'supported':
            _fail('UNSUPPORTED_COOP_CHARACTER', '该角色的协作执行器尚未完成')
    for seat_key, player in state['players'].items():
        health = player.get('health')
        max_health = player.get('max_health')
        gold = player.get('gold')
        if (
            isinstance(health, bool)
            or not isinstance(health, int)
            or isinstance(max_health, bool)
            or not isinstance(max_health, int)
            or max_health <= 0
            or not 0 <= health <= max_health
            or isinstance(gold, bool)
            or not isinstance(gold, int)
            or gold < 0
        ):
            _fail('INVALID_PLAYER_STATE', '协作玩家生命或金币状态无效')
        if str(player.get('character_id') or 'common_flower') != character_id:
            _fail('INVALID_PLAYER_STATE', '协作队伍角色状态不一致')
        deck = player.get('deck')
        if not isinstance(deck, list):
            _fail('INVALID_PLAYER_DECK', '协作玩家卡组无效')
        seat_ids = []
        for card in deck:
            instance_id = _card_instance_id(card)
            _validate_persisted_card(card, content_version)
            seat_ids.append(instance_id)
        if len(seat_ids) != len(set(seat_ids)):
            _fail('INVALID_PLAYER_DECK', f'席位 {seat_key} 的卡组包含重复实例')
        relics = player.get('relics')
        if (
            not isinstance(relics, list)
            or any(
                not isinstance(relic_id, str)
                or not re.fullmatch(r'[a-z0-9][a-z0-9._:-]{0,127}', relic_id)
                for relic_id in relics
            )
        ):
            _fail('INVALID_PLAYER_RELICS', '协作玩家遗物状态无效')
        if content_version == COOP_STORY_CONTENT_VERSION:
            if any(relic_id not in COOP_SUPPORTED_RELIC_IDS for relic_id in relics):
                _fail('UNSUPPORTED_COOP_RELIC', '协作玩家持有未编译的遗物')
            for relic_id in set(relics):
                definition = COOP_STORY_CONTENT.relic_definition(relic_id) or {}
                if relics.count(relic_id) > 1 and not definition.get('stackable'):
                    _fail('INVALID_PLAYER_RELICS', '不可叠加遗物出现了重复实例')
        serial = player.get('next_card_serial')
        if isinstance(serial, bool) or not isinstance(serial, int) or serial <= 0:
            _fail('INVALID_PLAYER_DECK', '协作卡牌实例序号无效')
        books = player.get('enchantment_books')
        book_serial = player.get('next_enchantment_book_serial')
        if (
            not isinstance(books, list)
            or len(books) > int(STORY_RULES['enchantment_book_slots'])
            or isinstance(book_serial, bool)
            or not isinstance(book_serial, int)
            or book_serial <= 0
        ):
            _fail('INVALID_ENCHANTMENT_BOOK_STATE', '协作玩家附魔书状态无效')
        book_instance_ids = []
        for book in books:
            if not isinstance(book, dict):
                _fail('INVALID_ENCHANTMENT_BOOK_STATE', '协作玩家附魔书实例无效')
            instance_id = str(book.get('instance_id') or '')
            book_id = str(book.get('book_id') or '')
            definition = STORY_ENCHANTMENT_BOOKS.get(book_id)
            if (
                not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', instance_id)
                or not isinstance(definition, dict)
                or (
                    definition.get('character_id')
                    and definition.get('character_id') != character_id
                )
            ):
                _fail('INVALID_ENCHANTMENT_BOOK_STATE', '协作玩家附魔书实例无效')
            book_instance_ids.append(instance_id)
        if len(book_instance_ids) != len(set(book_instance_ids)):
            _fail('INVALID_ENCHANTMENT_BOOK_STATE', '协作玩家附魔书实例重复')


def _validate_current_reward_state(state, nodes, current_node, completed_combat_ids):
    rewards = state.get('rewards_by_player')
    shared = state.get('shared_reward')
    room = state.get('room')
    if (
        state.get('combat') is not None
        or not isinstance(rewards, dict)
        or set(rewards) != set(state['players'])
        or not isinstance(shared, dict)
        or not isinstance(room, dict)
        or room.get('type') != 'reward'
        or current_node.get('status') != 'current'
        or not completed_combat_ids
    ):
        _fail('INVALID_COOP_REWARD', '协作奖励状态与旅程不一致')
    combat_id = completed_combat_ids[-1]
    node_type = str(current_node.get('type') or '')
    expected_gold = 25 if node_type == 'elite' else COOP_REWARD_GOLD
    if str(state.get('difficulty') or 'normal') in {'hard', 'lunatic'}:
        expected_gold = (expected_gold * 3) // 4
    if (
        room.get('combat_id') != combat_id
        or shared.get('combat_id') != combat_id
        or shared.get('source') != 'combat_victory'
        or shared.get('gold_each') != expected_gold
    ):
        _fail('INVALID_COOP_REWARD', '协作奖励来源与战斗不一致')
    for seat_key, reward in rewards.items():
        if not isinstance(reward, dict):
            _fail('INVALID_COOP_REWARD', '协作个人奖励无效')
        status = reward.get('status')
        card_status = reward.get('card_status')
        book_status = reward.get('book_status')
        options = reward.get('options')
        card_round_index = reward.get('card_round_index')
        card_round_total = reward.get('card_round_total')
        card_choices = reward.get('card_choices')
        if (
            status not in {'pending', 'resolved'}
            or card_status not in {'pending', 'resolved'}
            or book_status not in {'pending', 'resolved'}
            or (status == 'resolved') != (
                card_status == 'resolved' and book_status == 'resolved'
            )
            or str(reward.get('reward_id') or '')
            != f'reward:{combat_id}:seat:{int(seat_key)}'
            or reward.get('gold') != expected_gold
            or not isinstance(options, list)
            or len(options) != 3
            or isinstance(card_round_index, bool)
            or not isinstance(card_round_index, int)
            or isinstance(card_round_total, bool)
            or not isinstance(card_round_total, int)
            or card_round_total not in {1, 2}
            or not 1 <= card_round_index <= card_round_total
            or not isinstance(card_choices, list)
        ):
            _fail('INVALID_COOP_REWARD', '协作个人奖励状态无效')
        option_ids = []
        character_reward_pool = set(_coop_card_pool_for_player(
            state,
            int(seat_key),
            COOP_REWARD_CARD_IDS,
        ))
        for option in options:
            if not isinstance(option, dict):
                _fail('INVALID_COOP_REWARD', '协作奖励选项无效')
            card_id = str(option.get('card_id') or '')
            if (
                not _compiled_pool_contains(state, card_id, COOP_REWARD_CARD_IDS)
                or (
                    state.get('content_version') == COOP_STORY_CONTENT_VERSION
                    and card_id not in character_reward_pool
                )
                or not isinstance(option.get('upgraded'), bool)
            ):
                _fail('INVALID_COOP_REWARD', '协作奖励卡牌无效')
            option_ids.append(card_id)
        if len(option_ids) != len(set(option_ids)):
            _fail('INVALID_COOP_REWARD', '协作奖励选项重复')
        completed_card_rounds = (
            card_round_total if card_status == 'resolved' else card_round_index - 1
        )
        if len(card_choices) != completed_card_rounds:
            _fail('INVALID_COOP_REWARD', '协作卡牌奖励轮次记录无效')
        for index, card_choice in enumerate(card_choices, 1):
            if (
                not isinstance(card_choice, dict)
                or card_choice.get('round_index') != index
                or not isinstance(card_choice.get('skipped'), bool)
            ):
                _fail('INVALID_COOP_REWARD', '协作卡牌奖励轮次记录无效')
            chosen_id = card_choice.get('card_id')
            if (
                (chosen_id is None) != bool(card_choice.get('skipped'))
                or (
                    chosen_id is not None
                    and str(chosen_id or '') not in character_reward_pool
                )
            ):
                _fail('INVALID_COOP_REWARD', '协作卡牌奖励轮次选择无效')
        selected = reward.get('selected_card_id')
        skipped = reward.get('skipped')
        if not isinstance(skipped, bool):
            _fail('INVALID_COOP_REWARD', '协作奖励选择状态无效')
        if card_status == 'pending' and (selected is not None or skipped):
            _fail('INVALID_COOP_REWARD', '未处理的协作奖励不能包含选择')
        if card_status == 'resolved' and (
            (selected is None and not skipped)
            or (selected is not None and (skipped or selected not in option_ids))
        ):
            _fail('INVALID_COOP_REWARD', '已处理的协作奖励选择无效')
        book_id = reward.get('enchantment_book_id')
        selected_book_id = reward.get('selected_enchantment_book_id')
        skipped_book = reward.get('skipped_enchantment_book')
        if (
            book_id is not None
            and str(book_id or '') not in STORY_ENCHANTMENT_BOOKS
        ) or not isinstance(skipped_book, bool):
            _fail('INVALID_COOP_REWARD', '协作附魔书奖励无效')
        if book_id is None:
            if book_status != 'resolved' or selected_book_id is not None or skipped_book:
                _fail('INVALID_COOP_REWARD', '无附魔书掉落时不能包含附魔书选择')
        elif book_status == 'pending' and (selected_book_id is not None or skipped_book):
            _fail('INVALID_COOP_REWARD', '未处理的附魔书奖励不能包含选择')
        elif book_status == 'resolved' and (
            (selected_book_id is None and not skipped_book)
            or (
                selected_book_id is not None
                and (skipped_book or selected_book_id != book_id)
            )
        ):
            _fail('INVALID_COOP_REWARD', '已处理的附魔书奖励选择无效')


def _validate_current_map_state(state, nodes, current_node):
    vote = state['coordination'].get('map_vote')
    room = state.get('room')
    if (
        state.get('combat') is not None
        or not isinstance(vote, dict)
        or not isinstance(room, dict)
        or room.get('type') != 'map_vote'
        or current_node.get('status') != 'completed'
    ):
        _fail('INVALID_COOP_MAP_VOTE', '协作路线投票状态无效')
    from_node_id = str(vote.get('from_node_id') or '')
    options = vote.get('option_node_ids')
    votes = vote.get('votes_by_seat')
    if (
        from_node_id != str(state.get('current_node_id') or '')
        or from_node_id not in nodes
        or not isinstance(options, list)
        or not options
        or any(not isinstance(node_id, str) or node_id not in nodes for node_id in options)
        or len(options) != len(set(options))
        or options != _coop_outgoing_node_ids(state, from_node_id)
        or any(nodes[node_id].get('status') != 'available' for node_id in options)
        or {
            node_id for node_id, node in nodes.items()
            if node.get('status') == 'available'
        } != set(options)
        or any(str(nodes[node_id].get('type') or '') not in COOP_STAGE1_SUPPORTED_NODE_TYPES for node_id in options)
        or not isinstance(votes, dict)
        or any(seat_key not in state['players'] for seat_key in votes)
        or any(node_id not in options for node_id in votes.values())
        or vote.get('resolved_node_id') is not None
    ):
        _fail('INVALID_COOP_MAP_VOTE', '协作路线投票与地图不一致')
    option_floors = [nodes[node_id].get('floor') for node_id in options]
    if any(isinstance(floor, bool) or not isinstance(floor, int) or floor <= 0 for floor in option_floors):
        _fail('INVALID_COOP_MAP_VOTE', '协作路线楼层无效')
    floor = min(option_floors)
    vote_id = f'route:{from_node_id}:floor:{floor}'
    if (
        str(vote.get('vote_id') or '') != vote_id
        or room.get('vote_id') != vote_id
        or room.get('floor') != floor
    ):
        _fail('INVALID_COOP_MAP_VOTE', '协作路线投票标识无效')


def _validate_current_rest_state(state, nodes, current_node):
    room = state.get('room')
    room_states = state.get('room_states_by_player')
    decision = state['coordination'].get('room_decision')
    current_node_id = str(state.get('current_node_id') or '')
    expected_room_id = f'rest:{current_node_id}'
    if (
        state.get('combat') is not None
        or not isinstance(room, dict)
        or room.get('type') != 'rest'
        or room.get('id') != expected_room_id
        or room.get('node_id') != current_node_id
        or room.get('policy') != 'per_player_barrier'
        or current_node.get('type') != 'rest'
        or current_node.get('status') != 'current'
        or not isinstance(room_states, dict)
        or set(room_states) != set(state['players'])
        or not isinstance(decision, dict)
        or decision.get('decision_id') != expected_room_id
        or decision.get('room_id') != expected_room_id
        or decision.get('policy') != 'per_player_barrier'
    ):
        _fail('INVALID_COOP_ROOM', '协作休息房状态与地图不一致')
    resolved = decision.get('resolved_seats')
    expected_seats = {int(seat_key) for seat_key in state['players']}
    if (
        not isinstance(resolved, list)
        or resolved != sorted(set(resolved))
        or any(isinstance(seat, bool) or not isinstance(seat, int) or seat not in expected_seats for seat in resolved)
        or set(resolved) == expected_seats
    ):
        _fail('INVALID_COOP_ROOM', '协作休息房完成席位无效')
    for seat_key, private in room_states.items():
        seat = int(seat_key)
        expected_options = ['heal', 'upgrade', 'leave']
        if state.get('content_version') == COOP_STORY_CONTENT_VERSION:
            expected_options = [
                'heal',
                'upgrade',
                *(
                    ['gold']
                    if _compiled_player_relics(state['players'][seat_key], 'rest_gold')
                    else []
                ),
                'leave',
            ]
        if (
            not isinstance(private, dict)
            or private.get('options') != expected_options
            or private.get('status') not in {'pending', 'resolved'}
        ):
            _fail('INVALID_COOP_ROOM', '协作休息选项状态无效')
        is_resolved = seat in resolved
        selected = private.get('selected_option')
        if is_resolved != (private.get('status') == 'resolved'):
            _fail('INVALID_COOP_ROOM', '协作休息席位状态不一致')
        if is_resolved and selected not in private['options']:
            _fail('INVALID_COOP_ROOM', '协作休息选择无效')
        if not is_resolved and selected is not None:
            _fail('INVALID_COOP_ROOM', '未完成的协作休息席位不能包含选择')


def _validate_current_chest_state(state, nodes, current_node):
    room = state.get('room')
    room_states = state.get('room_states_by_player')
    decision = state['coordination'].get('room_decision')
    current_node_id = str(state.get('current_node_id') or '')
    expected_room_id = f'chest:{current_node_id}'
    if (
        state.get('combat') is not None
        or not isinstance(room, dict)
        or room.get('type') != 'chest'
        or room.get('id') != expected_room_id
        or room.get('node_id') != current_node_id
        or room.get('policy') != 'per_player_barrier'
        or current_node.get('type') != 'chest'
        or current_node.get('status') != 'current'
        or not isinstance(room_states, dict)
        or set(room_states) != set(state['players'])
        or not isinstance(decision, dict)
        or decision.get('decision_id') != expected_room_id
        or decision.get('room_id') != expected_room_id
        or decision.get('policy') != 'per_player_barrier'
    ):
        _fail('INVALID_COOP_ROOM', '协作宝箱房状态与地图不一致')
    resolved = decision.get('resolved_seats')
    expected_seats = {int(seat_key) for seat_key in state['players']}
    if (
        not isinstance(resolved, list)
        or resolved != sorted(set(resolved))
        or any(isinstance(seat, bool) or not isinstance(seat, int) or seat not in expected_seats for seat in resolved)
        or set(resolved) == expected_seats
    ):
        _fail('INVALID_COOP_ROOM', '协作宝箱完成席位无效')
    for seat_key, private in room_states.items():
        seat = int(seat_key)
        amount = private.get('gold') if isinstance(private, dict) else None
        current_content = state.get('content_version') == COOP_STORY_CONTENT_VERSION
        relic_id = private.get('relic_id') if isinstance(private, dict) else None
        expected_options = (
            ['claim_gold', *(['claim_relic'] if relic_id else []), 'leave']
            if current_content
            else ['claim_gold', 'leave']
        )
        if (
            not isinstance(private, dict)
            or private.get('options') != expected_options
            or private.get('status') not in {'pending', 'resolved'}
            or isinstance(amount, bool)
            or not isinstance(amount, int)
            or not 40 <= amount <= 60
        ):
            _fail('INVALID_COOP_ROOM', '协作宝箱选项状态无效')
        if current_content and (
            (relic_id is not None and relic_id not in COOP_CHEST_RELIC_IDS)
            or (relic_id is None and 'claim_relic' in expected_options)
        ):
            _fail('INVALID_COOP_ROOM', '协作宝箱遗物状态无效')
        is_resolved = seat in resolved
        selected = private.get('selected_option')
        if is_resolved != (private.get('status') == 'resolved'):
            _fail('INVALID_COOP_ROOM', '协作宝箱席位状态不一致')
        if is_resolved and selected not in private['options']:
            _fail('INVALID_COOP_ROOM', '协作宝箱选择无效')
        if not is_resolved and selected is not None:
            _fail('INVALID_COOP_ROOM', '未完成的协作宝箱席位不能包含选择')
        owns_relic = relic_id in (state['players'][seat_key].get('relics') or [])
        relic_definition = COOP_STORY_CONTENT.relic_definition(relic_id) or {}
        if current_content:
            if relic_definition.get('stackable'):
                if selected == 'claim_relic' and not owns_relic:
                    _fail('INVALID_COOP_ROOM', '协作宝箱遗物归属与选择不一致')
            elif owns_relic != (selected == 'claim_relic'):
                _fail('INVALID_COOP_ROOM', '协作宝箱遗物归属与选择不一致')


def _validate_current_shop_state(state, nodes, current_node):
    room = state.get('room')
    room_states = state.get('room_states_by_player')
    decision = state['coordination'].get('room_decision')
    current_node_id = str(state.get('current_node_id') or '')
    expected_room_id = f'shop:{current_node_id}'
    if (
        state.get('combat') is not None
        or not isinstance(room, dict)
        or room.get('type') != 'shop'
        or room.get('id') != expected_room_id
        or room.get('node_id') != current_node_id
        or room.get('policy') != 'per_player_barrier'
        or current_node.get('type') != 'shop'
        or current_node.get('status') != 'current'
        or not isinstance(room_states, dict)
        or set(room_states) != set(state['players'])
        or not isinstance(decision, dict)
        or decision.get('decision_id') != expected_room_id
        or decision.get('room_id') != expected_room_id
        or decision.get('policy') != 'per_player_barrier'
    ):
        _fail('INVALID_COOP_ROOM', '协作商店状态与地图不一致')
    resolved = decision.get('resolved_seats')
    expected_seats = {int(seat_key) for seat_key in state['players']}
    if (
        not isinstance(resolved, list)
        or resolved != sorted(set(resolved))
        or any(isinstance(seat, bool) or not isinstance(seat, int) or seat not in expected_seats for seat in resolved)
        or set(resolved) == expected_seats
    ):
        _fail('INVALID_COOP_ROOM', '协作商店完成席位无效')
    for seat_key, private in room_states.items():
        seat = int(seat_key)
        offers = private.get('offers') if isinstance(private, dict) else None
        safe_offers = offers if isinstance(offers, list) else []
        historical_shared = state.get('content_version') != COOP_STORY_CONTENT_VERSION
        expected_options = (
            ['buy_card', 'leave']
            if historical_shared
            else [
                'buy_card',
                *(
                    ['buy_relic']
                    if any(
                        isinstance(offer, dict) and offer.get('kind') == 'relic'
                        for offer in safe_offers
                    )
                    else []
                ),
                'buy_enchantment_book',
                'leave',
            ]
        )
        if (
            not isinstance(private, dict)
            or private.get('options') != expected_options
            or private.get('status') not in {'pending', 'resolved'}
            or not isinstance(offers, list)
            or (
                len(offers) != 3
                if historical_shared
                else not 6 <= len(offers) <= 7
            )
        ):
            _fail('INVALID_COOP_ROOM', '协作商店个人状态无效')
        offer_ids = []
        item_keys = []
        player = state['players'][seat_key]
        character_shop_pool = set(_coop_card_pool_for_player(
            state,
            seat,
            COOP_SHOP_CARD_IDS,
            include_neutral=True,
        ))
        deck = player.get('deck') or []
        deck_by_id = {
            _card_instance_id(card): card
            for card in deck
            if isinstance(card, dict)
        }
        purchased_bargaining_here = sum(
            isinstance(item, dict)
            and item.get('kind') == 'relic'
            and item.get('item_id') == 'bargaining'
            and item.get('status') == 'purchased'
            for item in offers
        ) if not historical_shared else 0
        kind_indexes = {'card': 0, 'relic': 0, 'enchantment_book': 0}
        for index, offer in enumerate(offers):
            if not isinstance(offer, dict):
                _fail('INVALID_COOP_ROOM', '协作商店商品无效')
            offer_id = str(offer.get('offer_id') or '')
            status = str(offer.get('status') or '')
            price = offer.get('price')
            if (
                status not in {'available', 'purchased'}
                or isinstance(price, bool)
                or not isinstance(price, int)
                or price <= 0
            ):
                _fail('INVALID_COOP_ROOM', '协作商店商品契约无效')
            if historical_shared:
                kind = 'card'
                item_id = str(offer.get('card_id') or '')
                expected_offer_id = f'shop:{current_node_id}:seat:{seat}:offer:{index}:{item_id}'
                if (
                    offer_id != expected_offer_id
                    or not _compiled_pool_contains(state, item_id, COOP_SHOP_CARD_IDS)
                    or offer.get('upgraded') is not False
                ):
                    _fail('INVALID_COOP_ROOM', '协作商店商品契约无效')
                instance_id = offer.get('card_instance_id')
            else:
                kind = str(offer.get('kind') or '')
                item_id = str(offer.get('item_id') or '')
                if kind not in kind_indexes:
                    _fail('INVALID_COOP_ROOM', '协作商店商品类型无效')
                kind_index = kind_indexes[kind]
                kind_indexes[kind] += 1
                expected_offer_id = (
                    f'shop:{current_node_id}:seat:{seat}:{kind}:{kind_index}:{item_id}'
                )
                if offer_id != expected_offer_id:
                    _fail('INVALID_COOP_ROOM', '协作商店商品标识无效')
                if kind == 'card':
                    if (
                        offer.get('card_id') != item_id
                        or offer.get('upgraded') is not False
                        or item_id not in COOP_SHOP_CARD_IDS
                        or item_id not in character_shop_pool
                    ):
                        _fail('INVALID_COOP_ROOM', '协作商店卡牌商品无效')
                    current_price = _shop_card_price(item_id, state.get('difficulty'), player)
                elif kind == 'relic':
                    if (
                        offer.get('relic_id') != item_id
                        or item_id not in COOP_SHOP_RELIC_IDS
                    ):
                        _fail('INVALID_COOP_ROOM', '协作商店遗物商品无效')
                    current_price = _shop_relic_price(item_id, state.get('difficulty'), player)
                else:
                    if (
                        offer.get('book_id') != item_id
                        or item_id not in STORY_ENCHANTMENT_BOOKS
                    ):
                        _fail('INVALID_COOP_ROOM', '协作商店附魔书商品无效')
                    current_price = _shop_enchantment_book_price(
                        item_id,
                        state.get('difficulty'),
                        player,
                        listed_base=offer.get('base_price'),
                    )
                if status == 'available' and price != current_price:
                    _fail('INVALID_COOP_ROOM', '协作商店可购商品价格无效')
                if status == 'purchased':
                    non_bargaining_relics = [
                        relic_id for relic_id in player.get('relics') or []
                        if relic_id != 'bargaining'
                    ]
                    final_bargaining_count = sum(
                        relic_id == 'bargaining'
                        for relic_id in player.get('relics') or []
                    )
                    initial_bargaining_count = max(
                        0,
                        final_bargaining_count - purchased_bargaining_here,
                    )
                    allowed_prices = set()
                    for bargaining_count in range(
                        initial_bargaining_count,
                        final_bargaining_count + 1,
                    ):
                        price_player = deepcopy(player)
                        price_player['relics'] = [
                            *non_bargaining_relics,
                            *(['bargaining'] * bargaining_count),
                        ]
                        historical_price = (
                            _shop_card_price(item_id, state.get('difficulty'), price_player)
                            if kind == 'card'
                            else _shop_relic_price(item_id, state.get('difficulty'), price_player)
                            if kind == 'relic'
                            else _shop_enchantment_book_price(
                                item_id,
                                state.get('difficulty'),
                                price_player,
                                listed_base=offer.get('base_price'),
                            )
                        )
                        allowed_prices.add(historical_price)
                    if price not in allowed_prices:
                        _fail('INVALID_COOP_ROOM', '协作商店成交价格无效')
                instance_id = offer.get('item_instance_id')
            if status == 'available' and instance_id is not None:
                _fail('INVALID_COOP_ROOM', '未购买商品不能绑定实例')
            if status == 'purchased' and kind == 'card':
                stored_card = deck_by_id.get(str(instance_id or ''))
                if not isinstance(stored_card, dict) or stored_card.get('def_id') != item_id:
                    _fail('INVALID_COOP_ROOM', '已购商品与个人卡组不一致')
            if status == 'purchased' and kind == 'relic' and (
                instance_id != item_id or item_id not in (player.get('relics') or [])
            ):
                _fail('INVALID_COOP_ROOM', '已购遗物与个人遗物状态不一致')
            if status == 'purchased' and kind == 'enchantment_book' and not re.fullmatch(
                r'[A-Za-z0-9._:-]{1,128}',
                str(instance_id or ''),
            ):
                _fail('INVALID_COOP_ROOM', '已购附魔书实例无效')
            if status == 'available' and kind == 'relic' and item_id in (player.get('relics') or []):
                definition = COOP_STORY_CONTENT.relic_definition(item_id) or {}
                if not definition.get('stackable'):
                    _fail('INVALID_COOP_ROOM', '已拥有遗物不能继续作为可购商品')
            offer_ids.append(offer_id)
            item_keys.append((kind, item_id))
        if len(offer_ids) != len(set(offer_ids)) or len(item_keys) != len(set(item_keys)):
            _fail('INVALID_COOP_ROOM', '协作商店商品重复')
        is_resolved = seat in resolved
        selected = private.get('selected_option')
        if is_resolved != (private.get('status') == 'resolved'):
            _fail('INVALID_COOP_ROOM', '协作商店席位状态不一致')
        if is_resolved and selected != 'leave':
            _fail('INVALID_COOP_ROOM', '协作商店离开状态无效')
        if not is_resolved and selected is not None:
            _fail('INVALID_COOP_ROOM', '未离开的协作商店席位不能包含结束选择')


def _validate_current_event_state(state, nodes, current_node):
    room = state.get('room')
    room_states = state.get('room_states_by_player')
    decision = state['coordination'].get('room_decision')
    current_node_id = str(state.get('current_node_id') or '')
    expected_room_id = f'event:{current_node_id}'
    content_id = str((room or {}).get('content_id') or '')
    current_content = str(state.get('content_version') or '') == COOP_STORY_CONTENT_VERSION
    adapted = COOP_ADAPTED_EVENT_DEFINITIONS.get(str(state.get('biome') or ''))
    allowed_event_ids = set(COOP_STORY_CONTENT.event_ids(state.get('biome')))
    if isinstance(adapted, dict):
        allowed_event_ids.add(str(adapted.get('id') or ''))
    if current_content and content_id not in allowed_event_ids:
        _fail('INVALID_COOP_ROOM', '协作事件不在当前生物群系内容池中')
    definition = _coop_event_definition_for_state(
        state,
        content_id,
        (room or {}).get('content_snapshot'),
    )
    option_ids = _coop_event_option_ids(definition)
    policy = str((definition.get('coop') or {}).get('policy') or '')
    if (
        state.get('combat') is not None
        or not isinstance(room, dict)
        or room.get('type') != 'event'
        or room.get('id') != expected_room_id
        or room.get('node_id') != current_node_id
        or room.get('title') != definition.get('title')
        or room.get('description') != definition.get('description')
        or (current_content and room.get('content_snapshot') != definition)
        or room.get('policy') != policy
        or current_node.get('type') != 'event'
        or current_node.get('status') != 'current'
        or not isinstance(room_states, dict)
        or set(room_states) != set(state['players'])
        or not isinstance(decision, dict)
        or decision.get('decision_id') != expected_room_id
        or decision.get('room_id') != expected_room_id
        or decision.get('policy') != policy
        or decision.get('resolved_option_id') is not None
    ):
        _fail('INVALID_COOP_ROOM', '协作事件状态与地图不一致')
    resolved = decision.get('resolved_seats')
    votes = decision.get('votes_by_seat')
    expected_seats = {int(seat_key) for seat_key in state['players']}
    if (
        not isinstance(resolved, list)
        or resolved != sorted(set(resolved))
        or any(isinstance(seat, bool) or not isinstance(seat, int) or seat not in expected_seats for seat in resolved)
        or set(resolved) == expected_seats
        or not isinstance(votes, dict)
        or set(votes) != {str(seat) for seat in resolved}
        or any(choice not in option_ids for choice in votes.values())
    ):
        _fail('INVALID_COOP_ROOM', '协作事件投票状态无效')
    for seat_key, private in room_states.items():
        seat = int(seat_key)
        if (
            not isinstance(private, dict)
            or private.get('options') != list(option_ids)
            or private.get('status') not in {'pending', 'resolved'}
        ):
            _fail('INVALID_COOP_ROOM', '协作事件个人状态无效')
        is_resolved = seat in resolved
        selected = private.get('selected_option')
        if is_resolved != (private.get('status') == 'resolved'):
            _fail('INVALID_COOP_ROOM', '协作事件席位状态不一致')
        if is_resolved and (selected not in option_ids or votes.get(seat_key) != selected):
            _fail('INVALID_COOP_ROOM', '协作事件选择与投票不一致')
        if not is_resolved and selected is not None:
            _fail('INVALID_COOP_ROOM', '未投票的协作事件席位不能包含选择')


def _validate_current_opening_state(state, nodes, current_node):
    room = state.get('room')
    room_states = state.get('room_states_by_player')
    decision = state['coordination'].get('room_decision')
    expected_room_id = _coop_opening_room_id(state)
    if (
        not _is_opening_content_version(state.get('content_version'))
        or state.get('current_floor') != 1
        or current_node.get('type') != 'blessing'
        or current_node.get('status') != 'current'
        or not isinstance(room, dict)
        or room.get('id') != expected_room_id
        or room.get('type') != 'opening'
        or room.get('node_id') != state.get('current_node_id')
        or room.get('stage') != 'blessing'
        or room.get('policy') != 'per_player_private_barrier'
        or not isinstance(room_states, dict)
        or set(room_states) != set(state['players'])
        or not isinstance(decision, dict)
        or set(decision) != {
            'decision_id', 'room_id', 'policy', 'resolved_seats'
        }
        or decision.get('decision_id') != expected_room_id
        or decision.get('room_id') != expected_room_id
        or decision.get('policy') != 'per_player_private_barrier'
    ):
        _fail('INVALID_COOP_OPENING', '协作开局状态与第一层不一致')
    resolved = decision.get('resolved_seats')
    expected_seats = {int(seat_key) for seat_key in state['players']}
    if (
        not isinstance(resolved, list)
        or resolved != sorted(set(resolved))
        or any(
            isinstance(seat, bool)
            or not isinstance(seat, int)
            or seat not in expected_seats
            for seat in resolved
        )
        or set(resolved) == expected_seats
    ):
        _fail('INVALID_COOP_OPENING', '协作开局完成席位无效')
    for seat_key, private in room_states.items():
        seat = int(seat_key)
        options = private.get('options') if isinstance(private, dict) else None
        selected = private.get('selected_option') if isinstance(private, dict) else None
        is_resolved = seat in resolved
        if (
            not isinstance(private, dict)
            or set(private) != {'status', 'stage', 'options', 'selected_option'}
            or private.get('stage') != 'blessing'
            or private.get('status') not in {'pending', 'resolved'}
            or not isinstance(options, list)
            or len(options) != 3
            or len(set(options)) != len(options)
            or any(
                not _compiled_pool_contains(state, option, COOP_OPENING_BLESSING_IDS)
                for option in options
            )
            or is_resolved != (private.get('status') == 'resolved')
            or (is_resolved and selected not in options)
            or (not is_resolved and selected is not None)
        ):
            _fail('INVALID_COOP_OPENING', '协作开局个人选项无效')
        player = state['players'][seat_key]
        blessing_history = player.get('blessings')
        stage = int(state.get('stage') or 1)
        expected_previous_count = stage - 1
        if (
            not isinstance(blessing_history, list)
            or (is_resolved and (
                player.get('blessing') != selected
                or len(blessing_history) != expected_previous_count + 1
                or blessing_history[-1:] != [selected]
            ))
            or (not is_resolved and (
                len(blessing_history) != expected_previous_count
                or player.get('blessing') != (
                    blessing_history[-1] if blessing_history else None
                )
            ))
        ):
            _fail('INVALID_COOP_OPENING', '协作开局赐福记录无效')


def _validate_coop_live_state_current(state):
    """Validate the three-stage journey without exposing legacy looseness."""

    validate_story_state_v10(state, expected_mode='coop')
    content_version = str(state.get('content_version') or '')
    if content_version not in COOP_STAGE1_CONTENT_VERSIONS and not _is_shared_content_version(content_version):
        _fail('UNSUPPORTED_COOP_CONTENT_VERSION', '协作旅程内容版本不受支持')
    opening_contract = _is_opening_content_version(content_version)
    phase = str(state.get('phase') or '')
    if phase not in {
        'journey_setup', 'combat', 'reward', 'map', 'room',
        'stage_complete', 'complete', 'game_over'
    }:
        _fail('INVALID_COOP_PHASE', '协作旅程阶段无效')
    if not isinstance(state.get('completed'), bool) or state.get('completed') != (phase == 'complete'):
        _fail('INVALID_COOP_PROGRESSION', '协作旅程完成标记与阶段不一致')
    progression = state.get('coop_progression')
    story_map = state.get('map')
    if not isinstance(progression, dict) or not isinstance(story_map, dict):
        _fail('INVALID_COOP_PROGRESSION', '协作阶段进度无效')
    floor_count = story_map.get('floor_count')
    encounter_index = progression.get('encounter_index')
    stage = state.get('stage')
    stage_definition = (
        COOP_STORY_STAGES.get(stage)
        if not isinstance(stage, bool) and isinstance(stage, int)
        else None
    )
    if stage_definition is None:
        _fail('INVALID_COOP_MAP', '协作阶段地图元数据无效')
    if (
        progression.get('contract_version') != COOP_STAGE1_CONTRACT_VERSION
        or progression.get('chapter') != stage
        or state.get('biome') != stage_definition['biome']
        or isinstance(floor_count, bool)
        or not isinstance(floor_count, int)
        or floor_count <= 1
        or progression.get('max_floor') != floor_count
        or isinstance(encounter_index, bool)
        or not isinstance(encounter_index, int)
        or encounter_index < (0 if opening_contract else 1)
    ):
        _fail('INVALID_COOP_PROGRESSION', '协作阶段进度无效')
    completed_combat_ids = _validated_string_list(
        progression.get('completed_combat_ids'),
        code='INVALID_COOP_PROGRESSION',
        label='协作战斗完成记录',
    )
    completed_node_ids = _validated_string_list(
        progression.get('completed_node_ids'),
        code='INVALID_COOP_PROGRESSION',
        label='协作节点完成记录',
    )
    completed_stages = _validated_string_list(
        [str(value) for value in progression.get('completed_stages', [])]
        if isinstance(progression.get('completed_stages'), list)
        else progression.get('completed_stages'),
        code='INVALID_COOP_PROGRESSION',
        label='协作阶段完成记录',
    )
    try:
        completed_stages = [int(value) for value in completed_stages]
    except (TypeError, ValueError):
        _fail('INVALID_COOP_PROGRESSION', '协作阶段完成记录无效')
    expected_completed_stages = list(range(1, stage))
    if phase in {'stage_complete', 'complete'}:
        expected_completed_stages.append(stage)
    if completed_stages != expected_completed_stages:
        _fail('INVALID_COOP_PROGRESSION', '协作阶段完成记录不是连续旅程')
    expected_encounter_index = len(completed_combat_ids) + (
        1 if phase in {'combat', 'game_over'} else 0
    )
    if (
        encounter_index != expected_encounter_index
        or (
            not opening_contract
            and completed_combat_ids
            and completed_combat_ids[0] != COOP_INTRO_COMBAT_ID
        )
    ):
        _fail('INVALID_COOP_PROGRESSION', '协作遭遇序号与完成记录不一致')
    nodes = _validate_current_stage_map(state)
    _validate_current_rng_streams(state)
    if any(
        str(node.get('type') or '') not in (
            {'blessing'} if int(node.get('floor') or 0) == 1 else COOP_STAGE1_SUPPORTED_NODE_TYPES
        )
        for node in nodes.values()
    ):
        _fail('INVALID_COOP_MAP', '协作地图包含尚未接入的节点')
    if any(node_id not in nodes or nodes[node_id].get('status') != 'completed' for node_id in completed_node_ids):
        _fail('INVALID_COOP_PROGRESSION', '协作节点完成记录与地图不一致')
    current_node_id = str(state.get('current_node_id') or '')
    current_node = nodes.get(current_node_id)
    current_floor = state.get('current_floor')
    if (
        current_node is None
        or isinstance(current_floor, bool)
        or not isinstance(current_floor, int)
        or current_floor != current_node.get('floor')
    ):
        _fail('INVALID_COOP_MAP', '协作当前节点与楼层不一致')
    completed_through_current = phase in {'map', 'stage_complete', 'complete'}
    expected_completed_count = current_floor if completed_through_current else current_floor - 1
    if (
        expected_completed_count < 0
        or len(completed_node_ids) != expected_completed_count
        or any(
            nodes[node_id].get('floor') != expected_floor
            for expected_floor, node_id in enumerate(completed_node_ids, start=1)
            if node_id in nodes
        )
    ):
        _fail('INVALID_COOP_PROGRESSION', '协作已完成节点不是连续楼层路径')
    path_node_ids = list(completed_node_ids)
    if not completed_through_current:
        path_node_ids.append(current_node_id)
    edge_pairs = {
        (str(edge.get('from') or ''), str(edge.get('to') or ''))
        for edge in story_map['edges']
    }
    if any(
        (source, target) not in edge_pairs
        for source, target in zip(path_node_ids, path_node_ids[1:])
    ):
        _fail('INVALID_COOP_PROGRESSION', '协作已完成节点没有形成真实路线')
    allowed_statuses = {'locked', 'available', 'current', 'completed'}
    if any(node.get('status') not in allowed_statuses for node in nodes.values()):
        _fail('INVALID_COOP_MAP', '协作地图节点状态无效')
    map_completed_ids = {
        node_id for node_id, node in nodes.items() if node.get('status') == 'completed'
    }
    if map_completed_ids != set(completed_node_ids):
        _fail('INVALID_COOP_PROGRESSION', '协作节点完成记录与地图状态不一致')
    current_status_ids = {
        node_id for node_id, node in nodes.items() if node.get('status') == 'current'
    }
    expected_current_ids = (
        set() if phase in {'map', 'stage_complete', 'complete'} else {current_node_id}
    )
    if current_status_ids != expected_current_ids:
        _fail('INVALID_COOP_MAP', '协作地图当前节点状态不唯一')
    expected_completed_combat_ids = []
    for node_id in completed_node_ids:
        node = nodes[node_id]
        if not opening_contract and int(node.get('floor') or 0) == 1:
            expected_completed_combat_ids.append(COOP_INTRO_COMBAT_ID)
        elif str(node.get('type') or '') in {'combat', 'elite', 'boss'}:
            expected_completed_combat_ids.append(f'{state["biome"]}-route-{node_id}')
    if phase == 'reward' and current_node_id not in completed_node_ids:
        expected_completed_combat_ids.append(
            COOP_INTRO_COMBAT_ID
            if not opening_contract and current_floor == 1
            else f'{state["biome"]}-route-{current_node_id}'
        )
    if completed_combat_ids != expected_completed_combat_ids:
        _fail('INVALID_COOP_PROGRESSION', '协作战斗完成记录与地图路径不一致')
    _validate_current_player_decks(state)

    combat = state.get('combat')
    ready_seats = state['coordination'].get('combat_ready_seats')
    ready_round = state['coordination'].get('combat_ready_round')
    room = state.get('room')
    if not isinstance(room, dict):
        _fail('INVALID_COOP_ROOM', '协作房间状态无效')
    setup_difficulties = room.get('difficulties') if isinstance(room, dict) else None
    valid_setup_difficulties = (
        isinstance(setup_difficulties, list)
        and bool(setup_difficulties)
        and len(setup_difficulties) == len(set(setup_difficulties))
        and setup_difficulties == [
            difficulty
            for difficulty in COOP_STAGE1_DIFFICULTIES
            if difficulty in set(setup_difficulties)
        ]
    )
    if phase == 'journey_setup' and (
        not opening_contract
        or current_floor != 1
        or current_node.get('type') != 'blessing'
        or current_node.get('status') != 'current'
        or room.get('type') != 'journey_setup'
        or room.get('stage') != 1
        or room.get('biomes') != ['garden']
        or not valid_setup_difficulties
        or room.get('modes') != ['standard']
    ):
        _fail('INVALID_COOP_SETUP', '协作旅程设置状态无效')
    if phase in {'combat', 'game_over'}:
        if not isinstance(combat, dict):
            _fail('INVALID_COMBAT_STATE', '协作战斗状态无效')
        validate_coop_combat_state(state)
        _validate_current_compiled_combat(state, room)
        expected_combat_id = (
            COOP_INTRO_COMBAT_ID
            if not opening_contract and current_floor == 1
            else f'{state["biome"]}-route-{current_node_id}'
        )
        expected_encounter = (
            COOP_INTRO_ENCOUNTER_ID
            if not opening_contract and current_floor == 1
            else str(room.get('encounter_id') or '')
        )
        if (
            combat.get('id') != expected_combat_id
            or combat.get('encounter_id') != expected_encounter
            or room.get('type') != 'combat'
            or current_node.get('status') != 'current'
            or (
                (opening_contract or current_floor > 1)
                and current_node.get('type') not in {'combat', 'elite', 'boss'}
            )
        ):
            _fail('INVALID_COOP_PROGRESSION', '协作战斗与地图进度不一致')
        if phase == 'combat' and (
            combat.get('outcome') is not None
            or ready_round != combat.get('round')
        ):
            _fail('INVALID_COOP_PROGRESSION', '协作战斗回合状态无效')
        if phase == 'game_over' and (
            combat.get('outcome') != 'defeat'
            or ready_seats != []
            or ready_round is not None
        ):
            _fail('INVALID_COOP_PROGRESSION', '协作失败状态无效')
    elif combat is not None or ready_seats != [] or ready_round is not None:
        _fail('INVALID_COOP_PHASE', '非战斗阶段不能保留战斗状态')

    last_combat = state.get('last_combat')
    if completed_combat_ids:
        if (
            not isinstance(last_combat, dict)
            or last_combat.get('id') != completed_combat_ids[-1]
            or last_combat.get('outcome') != 'victory'
            or not isinstance(last_combat.get('encounter_id'), str)
            or isinstance(last_combat.get('round'), bool)
            or not isinstance(last_combat.get('round'), int)
            or last_combat.get('round') <= 0
        ):
            _fail('INVALID_COOP_PROGRESSION', '协作上一场战斗摘要无效')
    elif last_combat is not None:
        _fail('INVALID_COOP_PROGRESSION', '尚未胜利时不能保留战斗摘要')

    rewards = state.get('rewards_by_player')
    shared_reward = state.get('shared_reward')
    map_vote = state['coordination'].get('map_vote')
    room_states = state.get('room_states_by_player')
    room_decision = state['coordination'].get('room_decision')
    if phase == 'reward':
        if map_vote is not None or room_states is not None or room_decision is not None:
            _fail('INVALID_COOP_REWARD', '奖励阶段保留了不兼容的决策状态')
        _validate_current_reward_state(state, nodes, current_node, completed_combat_ids)
    elif rewards is not None or shared_reward is not None:
        _fail('INVALID_COOP_REWARD', '非奖励阶段不能保留个人奖励')
    if phase == 'map':
        if room_states is not None or room_decision is not None:
            _fail('INVALID_COOP_MAP_VOTE', '路线阶段保留了房间私有状态')
        _validate_current_map_state(state, nodes, current_node)
    elif map_vote is not None:
        _fail('INVALID_COOP_MAP_VOTE', '非路线阶段不能保留路线投票')
    if phase == 'room':
        room_type = str(room.get('type') or '')
        if room_type == 'opening':
            _validate_current_opening_state(state, nodes, current_node)
        elif room_type == 'rest':
            _validate_current_rest_state(state, nodes, current_node)
        elif room_type == 'chest':
            _validate_current_chest_state(state, nodes, current_node)
        elif room_type == 'shop':
            _validate_current_shop_state(state, nodes, current_node)
        elif room_type == 'event':
            _validate_current_event_state(state, nodes, current_node)
        else:
            _fail('INVALID_COOP_ROOM', '协作房间类型尚未接入')
    elif phase != 'stage_complete' and (room_states is not None or room_decision is not None):
        _fail('INVALID_COOP_ROOM', '非房间阶段不能保留房间私有状态')
    if phase == 'stage_complete':
        expected_seats = {int(seat_key) for seat_key in state['players']}
        resolved = room_decision.get('resolved_seats') if isinstance(room_decision, dict) else None
        if (
            room.get('type') != 'stage_complete'
            or room.get('id') != f'stage-complete:{stage}'
            or room.get('stage') != stage
            or room.get('policy') != 'all_members_ready'
            or state.get('completed_stage') != stage
            or current_floor != floor_count
            or current_node.get('type') != 'boss'
            or current_node.get('status') != 'completed'
            or current_node_id not in completed_node_ids
            or not isinstance(room_states, dict)
            or set(room_states) != set(state['players'])
            or any(
                not isinstance(private, dict)
                or set(private) != {'status'}
                or private.get('status') not in {'pending', 'resolved'}
                for private in room_states.values()
            )
            or not isinstance(room_decision, dict)
            or set(room_decision) != {
                'decision_id', 'room_id', 'policy', 'resolved_seats'
            }
            or room_decision.get('decision_id') != room.get('id')
            or room_decision.get('room_id') != room.get('id')
            or room_decision.get('policy') != 'all_members_ready'
            or not isinstance(resolved, list)
            or resolved != sorted(set(resolved))
            or any(seat not in expected_seats for seat in resolved)
            or set(resolved) == expected_seats
            or any(
                (private.get('status') == 'resolved') != (int(seat_key) in resolved)
                for seat_key, private in room_states.items()
            )
        ):
            _fail('INVALID_COOP_COMPLETION', '协作阶段完成状态无效')
    elif phase == 'complete':
        if (
            stage != COOP_FINAL_STAGE
            or room.get('type') != 'coop_complete'
            or room.get('stage') != COOP_FINAL_STAGE
            or state.get('completed_stage') != COOP_FINAL_STAGE
            or current_floor != floor_count
            or current_node.get('type') != 'boss'
            or current_node.get('status') != 'completed'
            or room_states is not None
            or room_decision is not None
        ):
            _fail('INVALID_COOP_COMPLETION', '协作完整旅程完成状态无效')
    elif state.get('completed_stage') != (completed_stages[-1] if completed_stages else None):
        _fail('INVALID_COOP_COMPLETION', '协作已完成阶段标记无效')
    if phase in {'combat', 'game_over'} and (
        rewards is not None or map_vote is not None or room_states is not None or room_decision is not None
    ):
        _fail('INVALID_COOP_PHASE', '协作战斗阶段保留了不兼容的决策状态')
    return True


def validate_coop_live_state(state):
    """Route each persisted cooperative contract through its frozen validator."""

    version = str((state or {}).get('content_version') or '') if isinstance(state, dict) else ''
    if version == COOP_LEGACY_CONTENT_VERSION:
        return _validate_coop_live_state_legacy(state)
    if version in COOP_STAGE1_CONTENT_VERSIONS or _is_shared_content_version(version):
        return _validate_coop_live_state_current(state)
    _fail('UNSUPPORTED_COOP_CONTENT_VERSION', '协作旅程内容版本不受支持')


def _public_events(events):
    if not isinstance(events, list):
        return []
    public_fields = {
        'type',
        'action_sequence',
        'event_index',
        'actor_seat',
        'target_seat',
        'original_target_seat',
        'enemy_id',
        'combat_id',
        'round',
        'hit_index',
        'hit_count',
        'amount',
        'blocked',
        'before',
        'after',
        'count',
        'def_id',
        'source',
        'reason',
        'elixir',
        'draw_count',
        'reward_id',
        'vote_id',
        'node_id',
        'floor',
        'skipped',
        'encounter_index',
        'room_id',
        'room_type',
        'stage',
        'choice',
        'content_id',
    }
    projected = [
        {
            key: deepcopy(value)
            for key, value in event.items()
            if key in public_fields
        }
        for event in events[-80:]
        if isinstance(event, dict) and isinstance(event.get('type'), str)
    ]
    for event in projected:
        if event.get('type') != 'coop_event_resolved':
            event.pop('choice', None)
        # Chest contents are personal room state.  Combat events legitimately
        # use ``amount``, so redact it only for the private chest claim event.
        if event.get('type') == 'coop_chest_gold_claimed':
            event.pop('amount', None)
    return projected


def project_coop_events(events):
    """Project one action's event batch through the public event whitelist."""

    return _public_events(events)


def project_coop_state_for_viewer(state, authenticated_user_id):
    """Return a strict public snapshot; never expose seed, RNG or draw order."""

    validate_coop_live_state(state)
    viewer_seat = story_seat_for_user(state, authenticated_user_id)
    if viewer_seat is None:
        _fail('NOT_PARTY_MEMBER', '当前账号不是该协作旅程成员')
    party = state['party']
    hand_visibility = str((party.get('rules') or {}).get('hand_visibility') or 'private')
    ready = set(state['coordination'].get('combat_ready_seats') or [])
    combat = state.get('combat')
    players = []
    for seat_key in sorted(state['players'], key=int):
        seat = int(seat_key)
        player = state['players'][seat_key]
        seat_state = (
            combat.get('seat_states', {}).get(seat_key, {})
            if isinstance(combat, dict)
            else {}
        )
        hand = seat_state.get('hand') if isinstance(seat_state.get('hand'), list) else []
        show_hand = seat == viewer_seat or hand_visibility == 'party'
        players.append({
            'seat': seat,
            'health': int(player.get('health') or 0),
            'max_health': int(player.get('max_health') or 0),
            'gold': int(player.get('gold') or 0),
            'elixir': int(
                seat_state.get('elixir')
                if seat_state.get('elixir') is not None
                else (player.get('elixir') or 0)
            ),
            'magic': int(
                seat_state.get('magic')
                if seat_state.get('magic') is not None
                else (player.get('magic') or 0)
            ),
            'shield': int(seat_state.get('shield') or 0),
            'statuses': _public_statuses(seat_state.get('statuses') or {}),
            'ready': seat in ready,
            'down': int(player.get('health') or 0) <= 0,
            'hand': [_public_card(card) for card in hand] if show_hand else None,
            'hand_count': len(hand),
            'draw_count': len(seat_state.get('draw_pile') or []),
            # Rapids may inspect the set of drawable cards without revealing
            # their authoritative order.  Sort only the viewer's projection.
            'rapids_draw_choices': (
                sorted(
                    [_public_card(card) for card in seat_state.get('draw_pile') or []],
                    key=lambda card: str(card.get('instance_id') or ''),
                )
                if seat == viewer_seat
                else None
            ),
            'discard_pile': [_public_card(card) for card in seat_state.get('discard_pile') or []],
            'exile_pile': [_public_card(card) for card in seat_state.get('exile_pile') or []],
            'equipment': [
                _public_card(card)
                for card in seat_state.get('equipment') or []
            ],
            # Persistent relic ownership is personal progression data.  The
            # viewer needs their own list for rest/shop affordances, while a
            # teammate only receives combat-safe aggregate state.
            'relics': list(player.get('relics') or []) if seat == viewer_seat else None,
            'enchantment_books': (
                deepcopy(player.get('enchantment_books') or [])
                if seat == viewer_seat
                else None
            ),
        })
    snapshot = {
        'schema_version': int(state['schema_version']),
        'content_version': str(state.get('content_version') or ''),
        'mode': 'coop',
        'phase': str(state.get('phase') or ''),
        'character_id': str(state.get('character_id') or 'common_flower'),
        'stage': int(state.get('stage') or 1),
        'biome': str(state.get('biome') or ''),
        'difficulty': str(state.get('difficulty') or ''),
        'current_floor': int(state.get('current_floor') or 1),
        'current_node_id': str(state.get('current_node_id') or ''),
        'viewer_seat': int(viewer_seat),
        'party': {
            'leader_seat': int(party['leader_seat']),
            'max_players': int(party['max_players']),
            'members': deepcopy(party['members']),
            'rules': {
                key: deepcopy((party.get('rules') or {}).get(key, default))
                for key, default in COOP_STORY_DEFAULT_RULES.items()
            },
        },
        'players': players,
        'action_sequence': int(state['coordination'].get('action_sequence') or 0),
        'last_events': _public_events(state.get('last_events')),
        'combat': None,
        'reward': None,
        'map_vote': None,
        'room_state': None,
        'progression': {},
        'room': {
            key: deepcopy((state.get('room') or {}).get(key))
            for key in (
                'id',
                'type',
                'title',
                'encounter_id',
                'source',
                'floor',
                'node_id',
                'node_type',
                'policy',
                'stage',
                'journey_stage',
                'content_id',
                'description',
                'biomes',
                'difficulties',
                'modes',
            )
            if key in (state.get('room') or {})
        },
    }
    progression = state.get('coop_progression') or {}
    if int(progression.get('contract_version') or 1) == COOP_STAGE1_CONTRACT_VERSION:
        snapshot['progression'] = {
            'contract_version': COOP_STAGE1_CONTRACT_VERSION,
            'chapter': int(progression.get('chapter') or 1),
            'encounter_index': int(progression.get('encounter_index', 0)),
            'max_floor': int(progression.get('max_floor') or 1),
            'completed_node_count': len(progression.get('completed_node_ids') or []),
            'completed_stage': state.get('completed_stage'),
            'completed_stages': list(progression.get('completed_stages') or []),
            'completed': bool(state.get('completed')),
        }
    else:
        snapshot['progression'] = {
            'chapter': int(progression.get('chapter') or 1),
            'encounter_index': int(progression.get('encounter_index') or 1),
            'max_encounters': int(progression.get('max_encounters') or 1),
            'completed': bool(state.get('completed')),
        }
    if isinstance(combat, dict):
        snapshot['combat'] = {
            'id': str(combat.get('id') or ''),
            'encounter_id': str(combat.get('encounter_id') or ''),
            'round': int(combat.get('round') or 0),
            'turn': str(combat.get('turn') or ''),
            'outcome': combat.get('outcome'),
            'enemies': [{
                'id': str(enemy.get('id') or ''),
                'def_id': str(enemy.get('def_id') or ''),
                'name': deepcopy(enemy.get('name')) if isinstance(enemy.get('name'), dict) else None,
                'image_url': str(enemy.get('image_url') or ''),
                'health': int(enemy.get('health') or 0),
                'max_health': int(enemy.get('max_health') or 0),
                'shield': int(enemy.get('shield') or 0),
                'power': int(enemy.get('power') or 0),
                'static': int(enemy.get('static') or 0),
                'statuses': {
                    key: int(enemy.get(key) or 0)
                    for key in ('weak', 'vulnerable', 'fire')
                    if int(enemy.get(key) or 0) > 0
                },
                'intent': _public_intent(enemy.get('intent')),
            } for enemy in combat.get('enemies') or []],
        }
    if state.get('phase') == 'reward':
        rewards = state['rewards_by_player']
        viewer_reward = rewards[str(viewer_seat)]
        snapshot['reward'] = {
            'reward_id': str(viewer_reward.get('reward_id') or ''),
            'status': str(viewer_reward.get('status') or ''),
            'card_status': str(viewer_reward.get('card_status') or ''),
            'card_round_index': int(viewer_reward.get('card_round_index') or 1),
            'card_round_total': int(viewer_reward.get('card_round_total') or 1),
            'book_status': str(viewer_reward.get('book_status') or ''),
            'gold': int(viewer_reward.get('gold') or 0),
            'options': [
                {
                    'card_id': str(option.get('card_id') or ''),
                    'upgraded': bool(option.get('upgraded')),
                }
                for option in viewer_reward.get('options') or []
            ],
            'selected_card_id': viewer_reward.get('selected_card_id'),
            'skipped': bool(viewer_reward.get('skipped')),
            'enchantment_book_id': viewer_reward.get('enchantment_book_id'),
            'selected_enchantment_book_id': viewer_reward.get(
                'selected_enchantment_book_id'
            ),
            'skipped_enchantment_book': bool(
                viewer_reward.get('skipped_enchantment_book')
            ),
            'seats': [
                {
                    'seat': int(seat_key),
                    'resolved': reward.get('status') == 'resolved',
                }
                for seat_key, reward in sorted(rewards.items(), key=lambda item: int(item[0]))
            ],
        }
    if state.get('phase') == 'map':
        vote = state['coordination']['map_vote']
        nodes = _coop_map_nodes(state)
        votes = vote.get('votes_by_seat') or {}
        snapshot['map_vote'] = {
            'vote_id': str(vote.get('vote_id') or ''),
            'from_node_id': str(vote.get('from_node_id') or ''),
            'viewer_node_id': votes.get(str(viewer_seat)),
            'options': [
                {
                    'node_id': node_id,
                    'floor': int(nodes[node_id].get('floor') or 0),
                    'type': str(nodes[node_id].get('type') or ''),
                    'x': float(nodes[node_id].get('x') or 0),
                }
                for node_id in vote.get('option_node_ids') or []
            ],
            # Choices stay private until the final vote resolves atomically.
            'seats': [
                {'seat': int(seat_key), 'submitted': seat_key in votes}
                for seat_key in sorted(state['players'], key=int)
            ],
        }
    if state.get('phase') == 'room' and (state.get('room') or {}).get('type') in {
        'opening', 'rest', 'chest', 'shop', 'event'
    }:
        room_states = state.get('room_states_by_player') or {}
        private = room_states.get(str(viewer_seat)) or {}
        decision = state['coordination'].get('room_decision') or {}
        resolved = set(decision.get('resolved_seats') or [])
        room_type = str((state.get('room') or {}).get('type') or '')
        snapshot['room_state'] = {
            'room_id': str((state.get('room') or {}).get('id') or ''),
            'type': room_type,
            'status': str(private.get('status') or ''),
            'options': [str(option) for option in private.get('options') or []],
            'seats': [
                {'seat': int(seat_key), 'resolved': int(seat_key) in resolved}
                for seat_key in sorted(state['players'], key=int)
            ],
        }
        if room_type == 'rest':
            snapshot['room_state']['deck'] = [
                _public_card(card)
                for card in state['players'][str(viewer_seat)].get('deck') or []
            ]
            rest_gold = _compiled_player_relics(
                state['players'][str(viewer_seat)],
                'rest_gold',
            )
            snapshot['room_state']['rest_gold'] = max(
                0,
                sum(int(definition.get('amount') or 0) for _, definition in rest_gold),
            )
        elif room_type == 'chest':
            snapshot['room_state']['gold'] = int(private.get('gold') or 0)
            snapshot['room_state']['relic_id'] = private.get('relic_id')
        elif room_type == 'shop':
            snapshot['room_state']['gold'] = int(
                state['players'][str(viewer_seat)].get('gold') or 0
            )
            snapshot['room_state']['offers'] = [
                {
                    key: deepcopy(offer.get(key))
                    for key in (
                        'offer_id',
                        'kind',
                        'item_id',
                        'card_id',
                        'relic_id',
                        'book_id',
                        'upgraded',
                        'price',
                        'status',
                    )
                    if key in offer
                }
                for offer in private.get('offers') or []
                if isinstance(offer, dict)
            ]
        elif room_type == 'event':
            event_definition = _coop_event_definition_for_state(
                state,
                (state.get('room') or {}).get('content_id'),
                (state.get('room') or {}).get('content_snapshot'),
            )
            snapshot['room_state']['option_definitions'] = [
                {
                    key: deepcopy(option.get(key))
                    for key in (
                        'id', 'label', 'description',
                        'requires_confirmation', 'risky',
                    )
                    if key in option
                }
                for option in event_definition.get('options') or []
                if isinstance(option, dict)
            ]
            snapshot['room_state']['seats'] = [
                {'seat': int(seat_key), 'submitted': int(seat_key) in resolved}
                for seat_key in sorted(state['players'], key=int)
            ]
        elif room_type == 'opening':
            snapshot['room_state']['stage'] = str(private.get('stage') or '')
            snapshot['room_state']['selected_option'] = private.get('selected_option')
            snapshot['room_state']['seats'] = [
                {'seat': int(seat_key), 'resolved': int(seat_key) in resolved}
                for seat_key in sorted(state['players'], key=int)
            ]
    if state.get('phase') == 'stage_complete':
        room_states = state.get('room_states_by_player') or {}
        decision = state['coordination'].get('room_decision') or {}
        resolved = set(decision.get('resolved_seats') or [])
        viewer_state = room_states.get(str(viewer_seat)) or {}
        snapshot['room_state'] = {
            'room_id': str((state.get('room') or {}).get('id') or ''),
            'type': 'stage_complete',
            'status': str(viewer_state.get('status') or ''),
            'options': ['continue'],
            'seats': [
                {'seat': int(seat_key), 'resolved': int(seat_key) in resolved}
                for seat_key in sorted(state['players'], key=int)
            ],
        }
    return snapshot


def project_coop_run_for_viewer(run, authenticated_user_id):
    if run is None:
        return None
    if not isinstance(run, dict) or not isinstance(run.get('state'), dict):
        _fail('INVALID_COOP_RUN', '协作旅程记录无效')
    if str(run.get('content_version') or '') != str(run['state'].get('content_version') or ''):
        _fail('CORRUPT_COOP_CONTENT_VERSION', '协作旅程内容版本与状态不一致')
    projected = {
        field: deepcopy(run.get(field))
        for field in COOP_COMBAT_PUBLIC_RUN_FIELDS
    }
    projected['snapshot'] = project_coop_state_for_viewer(
        run['state'],
        authenticated_user_id,
    )
    return projected


def project_coop_bundle_for_viewer(bundle, authenticated_user_id):
    if bundle is None:
        return {'party': None, 'viewer': None, 'run': None}
    if not isinstance(bundle, dict):
        _fail('INVALID_COOP_BUNDLE', '协作队伍记录无效')
    return {
        'party': deepcopy(bundle.get('party')),
        'viewer': deepcopy(bundle.get('viewer')),
        'run': project_coop_run_for_viewer(bundle.get('run'), authenticated_user_id),
    }


def coop_combat_is_actionable(snapshot):
    combat = (snapshot or {}).get('combat')
    return bool(
        isinstance(combat, dict)
        and combat.get('turn') == COOP_COMBAT_HERO_TURN
        and combat.get('outcome') is None
    )


def coop_combat_is_terminal(snapshot):
    combat = (snapshot or {}).get('combat')
    return bool(isinstance(combat, dict) and combat.get('turn') == COOP_COMBAT_ENDED)
