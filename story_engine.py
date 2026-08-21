"""Server-authoritative story-mode state machine."""

import copy
import hashlib
import math
import random

from story_content import (
    STORY_BLESSINGS,
    STORY_BIOMES,
    STORY_BOSS_RELIC_IDS,
    STORY_CARDS,
    STORY_EASY_RELIC_IDS,
    STORY_ENCOUNTERS,
    STORY_ENEMIES,
    STORY_PLAYER_ATTACK_EFFECT_TYPES,
    STORY_RELICS,
    STORY_REWARD_CARD_IDS,
    STORY_RULES,
    STORY_SHOP_CARD_IDS,
    STORY_STATUSES,
    STORY_TRAITS,
    STORY_TRAIT_VALUE_KEYS,
)


_NEGATIVE_STATUSES = frozenset({
    'attack_blocked', 'blind', 'bleed', 'blockade', 'broken', 'entangle',
    'fire', 'fragile', 'poison', 'stagnation', 'toxic_poison', 'vulnerable',
    'weak',
})

# The story workbook defines these as start-of-turn decay. Keep the smaller
# end-of-turn list explicit so unrelated statuses never decay by default.
_TURN_START_DECAY_STATUSES = ('weak', 'vulnerable', 'fragile')
_TURN_END_DECAY_STATUSES = ('attack_blocked',)

_PRESENTATION_EFFECT_KEYS = (
    'shield', 'power', 'temporary_power', 'endurance', 'weak',
    'vulnerable', 'fragile', 'evade', 'poison', 'stun', 'reflection',
    'wither', 'broken', 'rockfall', 'blind', 'entangle',
    'negative_status_immunity', 'evil_eye', 'sturdy', 'shelter',
    'hidden', 'turn_shield', 'charging', 'charged', 'frenzy', 'vampire',
    'proliferation', 'regeneration', 'regenerations', 'bandage', 'miracle',
    'toxic_poison', 'stagnation', 'bleed', 'fire', 'blockade',
    'attack_blocked',
    'fragment', 'psionic_connection', 'psionic_sustain', 'psionic_fountain', 'nest_instinct',
    'endurance_shell', 'toxic_conversion', 'bulb', 'hard_shell', 'obstacle',
    'segments', 'magic_shield', 'magic_blessing', 'magic_reflection',
    'magic', 'electric_web', 'super_beam', 'toxic_reflection',
    'reconstruction', 'integration', 'scrap', 'disc', 'toxic_pressure',
)


def _story_presentation_state(state):
    """Return the compact combat state that must track each visual event."""
    combat = state.get('combat')
    if not isinstance(combat, dict):
        return {}
    player = state.get('player') or {}

    def actor_state(actor, include_health=False):
        result = {
            'effects': {
                key: int(actor.get(key) or 0)
                for key in _PRESENTATION_EFFECT_KEYS
            },
        }
        if include_health:
            result['health'] = int(actor.get('health') or 0)
            result['max_health'] = max(1, int(actor.get('max_health') or 1))
        return result

    enemies = {}
    for enemy in combat.get('enemies') or ():
        enemy_id = str(enemy.get('id') or '')
        if enemy_id:
            enemies[enemy_id] = actor_state(enemy, include_health=True)
    return {
        'player': {
            'health': int(player.get('health') or 0),
            'max_health': max(1, int(player.get('max_health') or 1)),
        },
        'combat': {
            'elixir': int(combat.get('elixir') or 0),
            'magic': int(combat.get('magic') or 0),
            **actor_state(combat),
        },
        'enemies': enemies,
    }


def _story_presentation_diff(before, after):
    """Build a small recursive patch; zero values are intentionally retained."""
    if before == after:
        return {}
    if not isinstance(before, dict) or not isinstance(after, dict):
        return copy.deepcopy(after)
    patch = {}
    for key in before.keys() | after.keys():
        if key not in after:
            patch[key] = None
            continue
        if key not in before:
            patch[key] = copy.deepcopy(after[key])
            continue
        if before[key] == after[key]:
            continue
        if isinstance(before[key], dict) and isinstance(after[key], dict):
            child = _story_presentation_diff(before[key], after[key])
            if child:
                patch[key] = child
        else:
            patch[key] = copy.deepcopy(after[key])
    return patch


class _StoryEventList(list):
    """Attach authoritative presentation deltas at the moment events are emitted."""

    def __init__(self, state):
        super().__init__()
        self._state = state
        self._presentation_state = _story_presentation_state(state)

    def append(self, event):
        if isinstance(event, dict):
            current = _story_presentation_state(self._state)
            patch = _story_presentation_diff(self._presentation_state, current)
            if patch:
                event.setdefault('presentation_patch', patch)
            self._presentation_state = current
        super().append(event)

    def capture_pending(self):
        current = _story_presentation_state(self._state)
        if _story_presentation_diff(self._presentation_state, current):
            self.append({'type': 'state_sync'})


def _difficulty(state):
    value = str(state.get('difficulty') or 'normal').lower()
    return value if value in ('easy', 'normal', 'hard', 'lunatic') else 'normal'


def _effect_amount(state, effect):
    if _difficulty(state) == 'lunatic' and effect.get('lunatic_amount') is not None:
        return int(effect['lunatic_amount'])
    return int(effect.get('amount') or 0)


def _effect_hits(state, effect):
    if _difficulty(state) == 'lunatic' and effect.get('lunatic_hits') is not None:
        return max(1, int(effect['lunatic_hits']))
    return max(1, int(effect.get('hits') or 1))


def _normalize_legacy_story_state(state):
    state.setdefault('journey_mode', 'standard')
    state['rng_version'] = 2
    if not isinstance(state.get('rng_streams'), dict):
        state['rng_streams'] = {}
    state.pop('curses', None)
    room = state.get('room')
    if isinstance(room, dict) and room.get('type') == 'journey_setup':
        room.setdefault('modes', ['standard', 'boss_rush'])
    if isinstance(room, dict) and room.get('type') == 'stage_choice':
        room.pop('curses', None)
        room.pop('allow_repeated_curses', None)
    combat = state.get('combat')
    if isinstance(combat, dict):
        combat.pop('locked', None)


def _turn_elixir_baseline(state, combat=None):
    combat = combat or state.get('combat') or {}
    reward_room_type = combat.get('reward_room_type')
    if not reward_room_type:
        current_node = _node_lookup(state).get(state.get('current_node_id')) or {}
        reward_room_type = current_node.get('type')
    amount = max(1, int(state.get('player', {}).get('max_elixir') or 1))
    for relic_id in state.get('player', {}).get('relics', []):
        relic = STORY_RELICS.get(relic_id) or {}
        script = relic.get('script')
        bonus = int(relic.get('amount') or 0)
        if script in {
            'boss_no_bloom', 'boss_no_heal', 'quantized_cost', 'boss_blind',
            'boss_poison', 'skip_shop', 'avoid_elite', 'must_take_cards',
            'decaying_elixir', 'boss_broken', 'boss_no_extra_draw',
            'turn_elixir',
        }:
            amount += bonus
        elif script == 'elite_boss_elixir' and reward_room_type in ('elite', 'boss'):
            amount += bonus
    if _has_relic(state, 'cognitive_bias'):
        amount -= max(0, int(combat.get('cognitive_bias_loss') or 0))
    return max(1, amount)


class StoryActionError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)


def _fail(code, message):
    raise StoryActionError(code, message)


def _checkpoint_snapshot(state):
    snapshot = copy.deepcopy(state)
    snapshot.pop('recovery_checkpoint', None)
    snapshot.pop('floor_entry_checkpoint', None)
    snapshot['last_events'] = []
    return snapshot


def _capture_recovery_checkpoint(state, kind):
    if state.get('phase') not in ('combat', 'room', 'reward'):
        state.pop('recovery_checkpoint', None)
        return
    state['recovery_checkpoint'] = {
        'version': 1,
        'kind': str(kind or 'node_entry'),
        'node_id': state.get('current_node_id'),
        'state': _checkpoint_snapshot(state),
    }


def _restore_recovery_checkpoint(state, events):
    checkpoint = state.get('recovery_checkpoint')
    snapshot = checkpoint.get('state') if isinstance(checkpoint, dict) else None
    if not isinstance(snapshot, dict):
        _fail('NO_RECOVERY_CHECKPOINT', '当前节点没有可恢复的检查点')
    event_counter = int(state.get('presentation_event_counter') or 0)
    floor_entry_checkpoint = copy.deepcopy(state.get('floor_entry_checkpoint'))
    restored = copy.deepcopy(snapshot)
    state.clear()
    state.update(restored)
    if isinstance(floor_entry_checkpoint, dict):
        state['floor_entry_checkpoint'] = floor_entry_checkpoint
    state['presentation_event_counter'] = max(
        event_counter,
        int(state.get('presentation_event_counter') or 0),
    )
    _capture_recovery_checkpoint(state, checkpoint.get('kind'))
    events.append({
        'type': 'checkpoint_restored',
        'checkpoint_kind': checkpoint.get('kind'),
        'node_id': state.get('current_node_id'),
    })


def _capture_floor_entry_checkpoint(state):
    if state.get('phase') not in ('combat', 'room', 'reward'):
        state.pop('floor_entry_checkpoint', None)
        return
    state['floor_entry_checkpoint'] = {
        'version': 1,
        'node_id': state.get('current_node_id'),
        'state': _checkpoint_snapshot(state),
    }


def _restore_floor_entry_checkpoint(state, events):
    checkpoint = state.get('floor_entry_checkpoint')
    snapshot = checkpoint.get('state') if isinstance(checkpoint, dict) else None
    if not isinstance(snapshot, dict):
        _fail('NO_FLOOR_ENTRY_CHECKPOINT', '当前层没有可重新开始的检查点')
    event_counter = int(state.get('presentation_event_counter') or 0)
    restored = copy.deepcopy(snapshot)
    state.clear()
    state.update(restored)
    state['presentation_event_counter'] = max(
        event_counter,
        int(state.get('presentation_event_counter') or 0),
    )
    _capture_floor_entry_checkpoint(state)
    _capture_recovery_checkpoint(state, f'{state.get("phase")}_entry')
    events.append({
        'type': 'floor_restarted',
        'node_id': state.get('current_node_id'),
    })


def _rng(state, seed, namespace):
    namespace = str(namespace or 'default')
    streams = state.get('rng_streams')
    if not isinstance(streams, dict):
        streams = {}
        state['rng_streams'] = streams
    try:
        stream_counter = max(0, int(streams.get(namespace) or 0))
    except (TypeError, ValueError):
        stream_counter = 0
    streams[namespace] = stream_counter + 1

    # Keep the aggregate counter for old saves and diagnostics, but never use it
    # to move another subsystem's random sequence. Combat shuffles or intents
    # must not reroll later rooms, card rewards, or relic rewards.
    try:
        counter = max(0, int(state.get('rng_counter') or 0))
    except (TypeError, ValueError):
        counter = 0
    state['rng_counter'] = counter + 1
    state['rng_version'] = 2
    digest = hashlib.sha256(
        f'{seed}:story-rng-v2:{namespace}:{stream_counter}'.encode('utf-8')
    ).digest()
    return random.Random(int.from_bytes(digest[:16], 'big'))


def _localized(value, lang='zh'):
    if isinstance(value, dict):
        return value.get(lang) or value.get('en') or value.get('zh') or ''
    return str(value or '')


def _story_term_name(key, lang='zh'):
    key = str(key or '')
    for registry in (STORY_STATUSES, STORY_TRAITS):
        definition = registry.get(key)
        if definition:
            name = _localized(definition.get('name'), lang)
            if name:
                return name
    # Enemy state fields and trait ids are not always identical (for example,
    # ``charging`` is rendered by the ``charging_up`` trait). Resolve those
    # aliases here so intent text never falls back to an internal state key.
    for trait_id, value_key in STORY_TRAIT_VALUE_KEYS.items():
        if value_key != key:
            continue
        definition = STORY_TRAITS.get(trait_id)
        if definition:
            name = _localized(definition.get('name'), lang)
            if name:
                return name
    fallback = {
        'health': {'zh': 'H', 'en': 'H'},
        'magic': {'zh': 'M', 'en': 'M'},
        'power': {'zh': '力量', 'en': 'Power'},
        'temporary_power': {'zh': '暂时力量', 'en': 'Temporary Power'},
        'shield': {'zh': '护盾', 'en': 'Shield'},
    }.get(key)
    if fallback:
        return _localized(fallback, lang)
    return '特殊效果' if lang == 'zh' else key.replace('_', ' ').title()


def _node_lookup(state):
    return {
        node['id']: node
        for floor in state.get('map', {}).get('floors', [])
        for node in floor.get('nodes', [])
    }


def _outgoing_node_ids(state, node_id):
    return [
        edge['to'] for edge in state.get('map', {}).get('edges', [])
        if edge.get('from') == node_id
    ]


def _new_card(state, def_id, upgraded=False, modifiers=None):
    if def_id not in STORY_CARDS:
        _fail('UNKNOWN_CARD', '未知故事卡牌')
    player = state['player']
    serial = int(player.get('next_card_serial') or 1)
    player['next_card_serial'] = serial + 1
    card = {
        'instance_id': f'sc-{serial:05d}',
        'def_id': def_id,
        'upgraded': bool(upgraded),
    }
    if (STORY_CARDS[def_id].get('upgrade') or {}).get('infinite'):
        card['upgrade_level'] = 1 if upgraded else 0
    if modifiers:
        card['modifiers'] = copy.deepcopy(modifiers)
    if (
        state.get('phase') == 'combat'
        and _has_relic(state, 'steady')
        and STORY_CARDS[def_id].get('rarity') == 'primary'
    ):
        card.setdefault('modifiers', {})['primary_bonus'] = int(
            _relic_amount(state, 'steady')
        )
    if (
        _has_relic(state, 'return_to_origin')
        and STORY_CARDS[def_id].get('rarity') == 'primary'
    ):
        card.setdefault('modifiers', {})['primary_multiplier'] = max(
            1.0,
            float(STORY_RELICS['return_to_origin']['amount']),
        )
    return card


def _card_def(card):
    definition = STORY_CARDS.get(str(card.get('def_id') or ''))
    if not definition:
        _fail('UNKNOWN_CARD', '未知故事卡牌')
    return definition


def _card_values(card):
    definition = _card_def(card)
    values = copy.deepcopy(definition)
    upgrade_level = max(
        int(card.get('upgrade_level') or 0),
        1 if card.get('upgraded') else 0,
    )
    if upgrade_level:
        values.update(copy.deepcopy(definition.get('upgrade') or {}))
    if (definition.get('upgrade') or {}).get('infinite'):
        damage = 14 + 5 * upgrade_level
        values['effects'] = tuple(
            {**effect, 'amount': damage}
            if effect.get('type') == 'damage'
            else effect
            for effect in values.get('effects') or ()
        )
        values['description'] = {
            'zh': f'对目标造成{damage}D；此牌可无限升级。',
            'en': f'Deal {damage} D. This card can be upgraded indefinitely.',
        }
    modifiers = card.get('modifiers') if isinstance(card.get('modifiers'), dict) else {}
    if modifiers:
        if isinstance(values.get('cost_e'), (int, float)):
            values['cost_e'] = max(0, int(values['cost_e']) + int(modifiers.get('cost_e_delta') or 0))
        if isinstance(values.get('cost_m'), (int, float)):
            values['cost_m'] = max(0, int(values['cost_m']) + int(modifiers.get('cost_m_delta') or 0))
        if int(modifiers.get('swift') or 0) > 0 and isinstance(values.get('cost_e'), (int, float)):
            values['cost_e'] = max(0, int(values['cost_e']) - int(modifiers['swift']))
        if int(modifiers.get('magic_swift') or 0) > 0 and isinstance(values.get('cost_m'), (int, float)):
            values['cost_m'] = max(0, int(values['cost_m']) - int(modifiers['magic_swift']))
        if modifiers.get('free_play'):
            values['cost_e'] = 0
            values['cost_m'] = 0
        if modifiers.get('temporary_free_e'):
            values['cost_e'] = 0
        primary_bonus = int(modifiers.get('primary_bonus') or 0)
        if primary_bonus:
            boosted_effects = []
            for effect in values.get('effects') or ():
                boosted = copy.deepcopy(effect)
                if boosted.get('type') in ('damage', 'shield'):
                    boosted['amount'] = max(
                        0,
                        int(boosted.get('amount') or 0) + primary_bonus,
                    )
                boosted_effects.append(boosted)
            values['effects'] = tuple(boosted_effects)
        damage_bonus = int(modifiers.get('damage_bonus') or 0)
        if damage_bonus:
            values['effects'] = tuple(
                {
                    **effect,
                    'amount': max(0, int(effect.get('amount') or 0) + damage_bonus),
                }
                if effect.get('type') == 'damage'
                else effect
                for effect in values.get('effects') or ()
            )
    if (
        values.get('rarity') == 'primary'
        and modifiers.get('primary_multiplier')
    ):
        multiplier = max(
            1.0,
            float(STORY_RELICS['return_to_origin']['amount']),
        )
        multiplied_effects = []
        for effect in values.get('effects') or ():
            multiplied = copy.deepcopy(effect)
            if multiplied.get('type') in ('damage', 'shield'):
                multiplied['amount'] = max(
                    0,
                    math.floor(int(multiplied.get('amount') or 0) * multiplier),
                )
            multiplied_effects.append(multiplied)
        values['effects'] = tuple(multiplied_effects)
    return values


def _card_tags(values):
    return set(str(tag) for tag in values.get('tags', ()))


def _card_has_tag(card, tag):
    return str(tag) in _card_tags(_card_values(card))


def _card_is_upgradable(card):
    upgrade = STORY_CARDS.get(str(card.get('def_id') or ''), {}).get('upgrade')
    if not upgrade:
        return False
    return bool(upgrade.get('infinite')) or not bool(card.get('upgraded'))


def _ensure_card_removable(card):
    if _card_has_tag(card, 'eternal'):
        _fail('CARD_ETERNAL', '带有永恒的牌无法从牌组中删除')


def _living_enemies(combat):
    return [enemy for enemy in combat.get('enemies', []) if int(enemy.get('health') or 0) > 0]


def _enemy_has_trait(enemy, trait):
    definition = STORY_ENEMIES.get(str(enemy.get('def_id') or ''), {})
    if trait not in definition.get('traits', ()):
        return False
    value_key = STORY_TRAIT_VALUE_KEYS.get(trait)
    return value_key is None or int(enemy.get(value_key) or 0) > 0


def _living_enemies_with_trait(combat, trait):
    return [enemy for enemy in _living_enemies(combat) if _enemy_has_trait(enemy, trait)]


def _enemy_base_health(state, definition, spec=None):
    spec = spec or {}
    if spec.get('health') is not None:
        return max(1, int(spec['health']))
    if _difficulty(state) == 'lunatic':
        return max(
            1,
            int(
                definition.get('lunatic_max_health')
                or definition.get('max_health')
                or 1
            ),
        )
    return max(1, int(definition.get('max_health') or 1))


def _build_enemy(state, def_id, serial, spec=None):
    """Build every encounter and summon through the same rule pipeline."""
    spec = spec if isinstance(spec, dict) else {}
    definition = STORY_ENEMIES[def_id]
    base_health = _enemy_base_health(state, definition, spec)
    max_health = base_health
    initial = copy.deepcopy(definition.get('initial') or {})
    if _difficulty(state) == 'lunatic':
        initial.update(copy.deepcopy(definition.get('lunatic_initial') or {}))
    initial.update({
        key: value
        for key, value in spec.items()
        if key not in {'def_id', 'health', 'max_health'}
    })
    enemy = {
        'id': f'enemy-{serial}',
        'def_id': def_id,
        'name': definition['name'],
        'health': max_health,
        'max_health': max_health,
        'shield': 0,
        'power': 0,
        'temporary_power': 0,
        'weak': 0,
        'vulnerable': 0,
        'fragile': 0,
        'stun': 0,
        'poison': 0,
        'evade': 0,
        'reflection': 0,
        'wither': 0,
        'move_index': int(spec.get('move_index') or 0),
        'move_step': 0,
        'damage_taken_round': 0,
    }
    for key, value in initial.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            enemy[str(key)] = int(value)
        else:
            enemy[str(key)] = copy.deepcopy(value)
    if definition.get('script') == 'evil_centipede':
        enemy['segment_origin'] = max(
            int(enemy.get('segments') or 0),
            int(enemy.get('segment_origin') or 0),
        )
    return enemy


def _find_enemy(combat, enemy_id):
    return next(
        (
            enemy for enemy in combat.get('enemies', [])
            if enemy.get('id') == enemy_id and int(enemy.get('health') or 0) > 0
        ),
        None,
    )


def _equipment_effects(combat, script=None):
    results = []
    for equipment in combat.get('equipment', []):
        values = _card_values(equipment)
        for effect in values.get('effects') or ():
            if effect.get('type') != 'equipment':
                continue
            if script is None or effect.get('script') == script:
                results.append((equipment, effect))
    return results


def _has_relic(state, relic_id):
    return relic_id in state.get('player', {}).get('relics', [])


def _relic_count(state, relic_id):
    return sum(
        1 for item in state.get('player', {}).get('relics', [])
        if item == relic_id
    )


def _relic_amount(state, relic_id):
    relic = STORY_RELICS.get(relic_id) or {}
    return int(relic.get('amount') or 0) * _relic_count(state, relic_id)


def _gain_shield(state, amount, events, source='card', enemy=None):
    amount = max(0, int(amount))
    if enemy is not None:
        before = int(enemy.get('shield') or 0)
        enemy['shield'] = before + amount
        events.append({
            'type': 'enemy_gain',
            'enemy_id': enemy['id'],
            'effect_kind': 'shield',
            'amount': amount,
            'before': before,
            'after': int(enemy['shield']),
            'source': source,
        })
        if (
            amount > 0
            and STORY_ENEMIES.get(enemy.get('def_id'), {}).get('script')
            == 'mechanical_flower'
        ):
            _player_raw_damage(
                state,
                amount,
                events,
                'electronic_shield',
            )
        return amount
    combat = state['combat']
    if source == 'card':
        amount += int(combat.get('endurance') or 0)
        if int(combat.get('fragile') or 0) > 0:
            amount = math.floor(amount * 0.75)
    before = int(combat.get('shield') or 0)
    combat['shield'] = before + amount
    events.append({
        'type': 'shield',
        'amount': amount,
        'before': before,
        'after': int(combat['shield']),
        'source': source,
    })
    return amount


def _heal_player(state, amount, events, source='card'):
    if _has_relic(state, 'last_stand'):
        events.append({
            'type': 'heal_blocked',
            'amount': max(0, int(amount)),
            'source': source,
        })
        return 0
    player = state['player']
    before = int(player.get('health') or 0)
    player['health'] = min(int(player.get('max_health') or 1), before + max(0, int(amount)))
    healed = int(player['health']) - before
    if healed:
        events.append({
            'type': 'heal',
            'amount': healed,
            'before': before,
            'after': int(player['health']),
            'source': source,
        })
    return healed


def _gain_deck_card(state, card_id, events, upgraded=False, source='reward'):
    if _has_relic(state, 'easy_study') and STORY_CARDS[card_id].get('upgrade'):
        upgraded = True
    card = _new_card(state, card_id, upgraded)
    card.get('modifiers', {}).pop('primary_bonus', None)
    if not card.get('modifiers'):
        card.pop('modifiers', None)
    state['player']['deck'].append(card)
    if _has_relic(state, 'diligent'):
        _heal_player(
            state,
            _relic_amount(state, 'diligent'),
            events,
            source='diligent',
        )
    events.append({
        'type': 'card_gained',
        'card_id': card_id,
        'upgraded': bool(card.get('upgraded')),
        'source': source,
    })
    return card


def _gain_elixir(state, amount, events):
    combat = state.get('combat')
    if combat is not None:
        before = int(combat.get('elixir') or 0)
        combat['elixir'] = max(0, before + int(amount))
        after = int(combat['elixir'])
    else:
        before = int(state['player'].get('elixir') or 0)
        state['player']['elixir'] = max(0, before + int(amount))
        after = int(state['player']['elixir'])
    if amount:
        events.append({
            'type': 'elixir',
            'amount': int(amount),
            'before': before,
            'after': after,
        })


def _gain_magic(state, amount, events):
    combat = state.get('combat')
    if combat is not None:
        before = int(combat.get('magic') or 0)
        combat['magic'] = max(0, before + int(amount))
        after = int(combat['magic'])
    else:
        before = int(state['player'].get('magic') or 0)
        state['player']['magic'] = max(0, before + int(amount))
        after = int(state['player']['magic'])
    if amount:
        events.append({
            'type': 'magic',
            'amount': int(amount),
            'before': before,
            'after': after,
        })


def _status_count(unit):
    keys = (
        'shield', 'power', 'temporary_power', 'endurance', 'weak',
        'vulnerable', 'fragile', 'evade', 'poison',
        'reflection', 'wither', 'broken', 'rockfall', 'blind', 'entangle',
        'negative_status_immunity', 'evil_eye', 'toxic_poison', 'stagnation',
        'bleed', 'fire', 'blockade', 'attack_blocked', 'fragment',
    )
    return sum(1 for key in keys if int(unit.get(key) or 0) > 0)


def _apply_status(state, target, status, amount, events, source='card'):
    amount = int(amount)
    if not status or not amount:
        return
    if status in _NEGATIVE_STATUSES and int(target.get('negative_status_immunity') or 0) > 0:
        before_immunity = int(target['negative_status_immunity'])
        target['negative_status_immunity'] = before_immunity - 1
        events.append({
            'type': 'status_blocked',
            'target_id': target.get('id') or 'player',
            'status': status,
            'amount': amount,
            'immunity_before': before_immunity,
            'immunity_after': int(target['negative_status_immunity']),
            'source': source,
        })
        return
    before = int(target.get(status) or 0)
    target[status] = max(0, before + amount)
    target_id = target.get('id') or 'player'
    events.append({
        'type': 'status',
        'target_id': target_id,
        'status': status,
        'amount': amount,
        'before': before,
        'after': int(target[status]),
        'source': source,
        'category': 'action' if status == 'stun' else 'status',
    })
    if status == 'vulnerable' and target_id != 'player':
        for _, effect in _equipment_effects(state['combat'], 'vulnerable_shield'):
            _gain_shield(state, int(effect.get('amount') or 0), events)


def _mechanical_flowers(combat):
    return [
        enemy for enemy in _living_enemies(combat)
        if STORY_ENEMIES.get(enemy.get('def_id'), {}).get('script')
        == 'mechanical_flower'
    ]


def _card_exiled_by_void(card):
    modifiers = card.get('modifiers') or {}
    return bool(modifiers.get('force_void') or 'void' in _card_tags(_card_values(card)))


def _notify_exiled(state, card, events, seed):
    combat = state.get('combat') or {}
    flowers = _mechanical_flowers(combat)
    if flowers and _card_exiled_by_void(card):
        flower = flowers[0]
        if card in combat.get('exile_pile', []):
            combat['exile_pile'].remove(card)
        card['track_persistent'] = False
        card['track_captured'] = True
        flower.setdefault('mechanical_track', []).insert(0, card)
        events.append({
            'type': 'mechanical_track_captured',
            'enemy_id': flower['id'],
            'card_instance_id': card['instance_id'],
            'def_id': card['def_id'],
        })
        return
    events.append({
        'type': 'card_exiled',
        'card_instance_id': card['instance_id'],
        'def_id': card['def_id'],
    })


def _sync_persistent_card_modifier(state, card, key, amount):
    amount = int(amount)
    modifiers = card.setdefault('modifiers', {})
    modifiers[key] = int(modifiers.get(key) or 0) + amount
    instance_id = str(card.get('instance_id') or '')
    deck_card = next(
        (
            item for item in state.get('player', {}).get('deck', [])
            if str(item.get('instance_id') or '') == instance_id
        ),
        None,
    )
    if deck_card is not None and deck_card is not card:
        deck_modifiers = deck_card.setdefault('modifiers', {})
        deck_modifiers[key] = int(deck_modifiers.get(key) or 0) + amount


def _actively_discard_cards(state, cards, seed, events, source='card'):
    combat = state['combat']
    discarded = []
    for card in list(cards):
        if card not in combat.get('hand', []):
            continue
        combat['hand'].remove(card)
        combat['discard_pile'].append(card)
        discarded.append(card)
        combat['active_discards_this_turn'] = int(
            combat.get('active_discards_this_turn') or 0
        ) + 1
        combat['active_discards_this_combat'] = int(
            combat.get('active_discards_this_combat') or 0
        ) + 1
        events.append({
            'type': 'card_discarded',
            'card_instance_id': card['instance_id'],
            'def_id': card['def_id'],
            'reason': 'active',
            'source': source,
        })
        script = _card_values(card).get('script')
        if script in ('azalea', 'azalea_plus'):
            _gain_shield(
                state,
                4 if script == 'azalea_plus' else 3,
                events,
                source=card['def_id'],
            )
        for equipment, effect in list(_equipment_effects(combat)):
            equipment_script = str(effect.get('script') or '')
            if equipment_script == 'pearl':
                enemies = _living_enemies(combat)
                if enemies:
                    target = _rng(state, seed, 'pearl_active_discard').choice(enemies)
                    _enemy_physical_damage(
                        state,
                        target,
                        int(effect.get('amount') or 3),
                        1,
                        events,
                        'pearl',
                        values={'power_scale': 0},
                        seed=seed,
                    )
            elif equipment_script == 'magic_pearl':
                _gain_shield(
                    state,
                    int(effect.get('amount') or 0),
                    events,
                    source=equipment.get('def_id') or 'magic_pearl',
                )
    return discarded


def _put_in_hand(state, card, events):
    combat = state['combat']
    if len(combat['hand']) >= int(STORY_RULES['hand_limit']):
        combat['discard_pile'].append(card)
        events.append({'type': 'hand_overflow', 'count': 1, 'card_instance_ids': [card['instance_id']]})
        return False
    if combat.get('sewage_active'):
        card.setdefault('modifiers', {})['temporary_free_e'] = True
    combat['hand'].append(card)
    events.append({'type': 'card_created', 'card_instance_id': card['instance_id'], 'def_id': card['def_id']})
    return True


def _on_card_drawn(state, card, seed, events, autoplay_depth):
    combat = state['combat']
    if combat.get('sewage_active'):
        card.setdefault('modifiers', {})['temporary_free_e'] = True
    if _has_relic(state, 'quantized'):
        card.setdefault('modifiers', {})['quantized_cost_e'] = _rng(
            state,
            seed,
            f'quantized:{card["instance_id"]}',
        ).randint(0, 3)
        base_cost = _card_def(card).get('cost_e')
        if isinstance(base_cost, int):
            card['modifiers']['cost_e_delta'] = int(card['modifiers']['quantized_cost_e']) - base_cost
    values = _card_values(card)
    if combat.get('turn') == 'player':
        for source_enemy in _living_enemies_with_trait(combat, 'electric_web'):
            _apply_status(
                state,
                combat,
                'entangle',
                1,
                events,
                source=source_enemy['def_id'],
            )
    if values.get('script') == 'slimed':
        alternatives = [item for item in state['combat']['hand'] if item is not card]
        if alternatives:
            victim = _rng(state, seed, 'slimed_discard').choice(alternatives)
            state['combat']['hand'].remove(victim)
            state['combat']['discard_pile'].append(victim)
            events.append({'type': 'card_discarded', 'card_instance_id': victim['instance_id'], 'reason': 'slimed'})
    if values.get('script') == 'static_electricity':
        for hand_card in state['combat']['hand']:
            hand_card.setdefault('modifiers', {})['charge'] = int(
                hand_card.get('modifiers', {}).get('charge') or 0
            ) + 1
        events.append({'type': 'hand_charged', 'amount': 1, 'source': 'static_electricity'})
    if 'ready' in _card_tags(values) and autoplay_depth < 24:
        if _is_card_playable(state, card, automatic=True):
            target = min(_living_enemies(state['combat']), key=lambda item: (int(item['health']), item['id']), default=None)
            _play_card(
                state,
                {'card_instance_id': card['instance_id'], 'target_id': target and target['id'], 'automatic': True},
                seed,
                events,
                autoplay_depth=autoplay_depth + 1,
            )


def _record_cards_drawn(state, card_instance_ids, events):
    combat = state['combat']
    count = len(card_instance_ids)
    if not count:
        return
    combat['cards_drawn_this_combat'] = int(
        combat.get('cards_drawn_this_combat') or 0
    ) + count
    for equipment, effect in list(_equipment_effects(combat, 'draw_power')):
        threshold = max(1, int(effect.get('amount') or 1))
        previous = max(0, int(equipment.get('draw_progress') or 0))
        total = previous + count
        triggers, equipment['draw_progress'] = divmod(total, threshold)
        if triggers:
            before = int(combat.get('power') or 0)
            combat['power'] = before + triggers
            events.append({
                'type': 'status',
                'target_id': 'player',
                'status': 'power',
                'amount': triggers,
                'before': before,
                'after': int(combat['power']),
                'source': equipment.get('def_id') or 'trident',
            })


def _draw_filter_matches(card, filter_name):
    if not filter_name:
        return True
    if filter_name == 'zero_e':
        return int(_card_values(card).get('cost_e') or 0) == 0
    return False


def _apply_machine_learning_void(state, card, events, source):
    combat = state.get('combat') or {}
    flowers = _mechanical_flowers(combat)
    if not flowers:
        return False
    modifiers = card.setdefault('modifiers', {})
    if modifiers.get('force_void') or 'void' in _card_tags(_card_values(card)):
        return False
    modifiers['force_void'] = True
    events.append({
        'type': 'card_modified',
        'card_instance_id': card['instance_id'],
        'modifier': 'force_void',
        'amount': 1,
        'source': source,
        'enemy_id': flowers[0]['id'],
    })
    return True


def _draw_cards(state, count, seed, events, autoplay_depth=0, card_filter=None):
    combat = state['combat']
    if combat.get('cannot_draw'):
        return []
    drawn = []
    overflowed = []
    for _ in range(max(0, int(count))):
        if not combat['draw_pile']:
            if not combat['discard_pile']:
                break
            combat['draw_pile'] = combat['discard_pile']
            combat['discard_pile'] = []
            _rng(state, seed, 'reshuffle').shuffle(combat['draw_pile'])
            events.append({'type': 'reshuffle'})
        draw_index = next(
            (
                index
                for index in range(len(combat['draw_pile']) - 1, -1, -1)
                if _draw_filter_matches(combat['draw_pile'][index], card_filter)
            ),
            None,
        )
        if draw_index is None:
            break
        card = combat['draw_pile'].pop(draw_index)
        if len(combat['hand']) >= int(STORY_RULES['hand_limit']):
            combat['discard_pile'].append(card)
            overflowed.append(card['instance_id'])
        else:
            combat['hand'].append(card)
            drawn.append(card['instance_id'])
            if combat.get('draw_phase_complete'):
                _apply_machine_learning_void(
                    state,
                    card,
                    events,
                    'machine_learning_draw',
                )
            _on_card_drawn(state, card, seed, events, autoplay_depth)
    if drawn:
        _record_cards_drawn(state, drawn, events)
        events.append({'type': 'draw', 'count': len(drawn), 'card_instance_ids': drawn})
    if overflowed:
        events.append({
            'type': 'hand_overflow',
            'count': len(overflowed),
            'card_instance_ids': overflowed,
            'hand_limit': int(STORY_RULES['hand_limit']),
        })
    return drawn


def _play_ready_cards_in_hand(state, seed, events, autoplay_depth=0):
    combat = state.get('combat') or {}
    if combat.get('turn') != 'player' or autoplay_depth >= 24:
        return
    skipped = set()
    while state.get('phase') == 'combat':
        card = next(
            (
                item for item in list(combat.get('hand', []))
                if item['instance_id'] not in skipped
                and 'ready' in _card_tags(_card_values(item))
                and _is_card_playable(state, item, automatic=True)
            ),
            None,
        )
        if card is None:
            return
        values = _card_values(card)
        if any(
            effect.get('type') in ('choose_exile', 'copy_hand_card', 'discard_to_draw_top')
            for effect in values.get('effects') or ()
        ):
            skipped.add(card['instance_id'])
            continue
        target = min(
            _living_enemies(combat),
            key=lambda item: (int(item['health']), item['id']),
            default=None,
        )
        _play_card(
            state,
            {
                'card_instance_id': card['instance_id'],
                'target_id': target and target['id'],
                'automatic': True,
            },
            seed,
            events,
            autoplay_depth=autoplay_depth + 1,
        )


def _damage_summary(values):
    values = [max(0, int(value)) for value in values]
    if not values:
        return '0D'
    if len(values) > 1 and len(set(values)) == 1:
        return f'{values[0]}D×{len(values)}'
    if len(values) == 1:
        return f'{values[0]}D'
    return f"({' + '.join(str(value) for value in values)})D"


def _enemy_physical_hit_amount(state, attacker, base_amount):
    combat = state['combat']
    amount = max(
        0,
        int(base_amount)
        + int(attacker.get('power') or 0)
        + int(attacker.get('temporary_power') or 0)
        + int(attacker.get('charging') or 0),
    )
    if int(attacker.get('weak') or 0) > 0:
        amount = math.floor(amount * 0.75)
    if int(combat.get('vulnerable') or 0) > 0:
        amount = math.floor(amount * 1.5)
    return amount


def _player_physical_hit(state, base_amount, attacker, events, source):
    combat = state['combat']
    amount = _enemy_physical_hit_amount(state, attacker, base_amount)
    health_before = int(state['player'].get('health') or 0)
    if int(combat.get('evade') or 0) > 0:
        combat['evade'] = max(0, int(combat['evade']) - 1)
        events.append({'type': 'evade', 'target_id': 'player', 'amount': amount})
        return 0, amount, health_before
    if combat.get('disc_active'):
        amount = math.floor(amount / 2)
    shield = int(combat.get('shield') or 0)
    blocked = min(shield, amount)
    combat['shield'] = shield - blocked
    dealt = amount - blocked
    if _equipment_effects(combat, 'sponge'):
        poison = math.ceil(dealt / 2)
        if poison:
            _apply_status(state, combat, 'poison', poison, events, source='sponge')
        dealt = 0
    if dealt > 0 and _has_relic(state, 'fearless_pain'):
        reduction = min(dealt, _relic_amount(state, 'fearless_pain'))
        dealt -= reduction
        blocked += reduction
    if dealt > 0 and _has_relic(state, 'phoenix') and not combat.get('phoenix_used'):
        combat['phoenix_used'] = True
        blocked += dealt
        dealt = 0
        events.append({'type': 'damage_prevented', 'source': 'phoenix'})
    before = health_before
    state['player']['health'] = before - dealt
    combat['damage_taken'] = int(combat.get('damage_taken') or 0) + dealt
    if dealt and not combat.get('first_damage_taken'):
        combat['first_damage_taken'] = True
        if _has_relic(state, 'solid_barrier'):
            _gain_elixir(state, _relic_amount(state, 'solid_barrier'), events)
    return dealt, blocked, before


def _player_raw_damage(state, amount, events, source):
    amount = max(0, int(amount))
    combat = state['combat']
    shield = int(combat.get('shield') or 0)
    blocked = min(shield, amount)
    combat['shield'] = shield - blocked
    dealt = amount - blocked
    if dealt > 0 and _has_relic(state, 'fearless_pain'):
        reduction = min(dealt, _relic_amount(state, 'fearless_pain'))
        dealt -= reduction
        blocked += reduction
    if dealt > 0 and _has_relic(state, 'phoenix') and not combat.get('phoenix_used'):
        combat['phoenix_used'] = True
        blocked += dealt
        dealt = 0
        events.append({'type': 'damage_prevented', 'source': 'phoenix'})
    before = int(state['player']['health'])
    state['player']['health'] = before - dealt
    combat['damage_taken'] = int(combat.get('damage_taken') or 0) + dealt
    if dealt and not combat.get('first_damage_taken'):
        combat['first_damage_taken'] = True
        if _has_relic(state, 'solid_barrier'):
            _gain_elixir(state, _relic_amount(state, 'solid_barrier'), events)
    events.append({
        'type': 'player_damage',
        'amount': dealt,
        'hits': 1,
        'hit_index': 1,
        'hit_count': 1,
        'history': [{
            'before': before,
            'after': int(state['player']['health']),
            'blocked': blocked,
        }],
        'source': source,
        'attacker_id': None,
    })
    return dealt


def _player_damage(state, amount, hits, events, source, attacker=None):
    attacker = attacker or {}
    total = 0
    hit_count = max(1, int(hits))
    for hit_index in range(1, hit_count + 1):
        dealt, blocked, before = _player_physical_hit(state, amount, attacker, events, source)
        total += dealt
        after = int(state['player']['health'])
        events.append({
            'type': 'player_damage',
            'amount': dealt,
            'hits': 1,
            'hit_index': hit_index,
            'hit_count': hit_count,
            'history': [{'before': before, 'after': after, 'blocked': blocked}],
            'before': before,
            'after': after,
            'source': source,
            'attacker_id': attacker.get('id'),
        })
        if dealt and int(combat_reflection := state['combat'].get('reflection') or 0) > 0 and attacker:
            _enemy_raw_damage(
                state,
                attacker,
                combat_reflection,
                events,
                'reflection',
                player_caused=True,
            )
        salt_multipliers = state['combat'].get('salt_multipliers') or []
        if dealt > 0 and attacker and int(attacker.get('health') or 0) > 0 and salt_multipliers:
            multiplier = max(1, int(salt_multipliers.pop(0)))
            _enemy_raw_damage(
                state,
                attacker,
                dealt * multiplier,
                events,
                'salt',
                player_caused=True,
            )
        if dealt > 0 and attacker and int(attacker.get('health') or 0) > 0:
            vampire = max(0, int(attacker.get('vampire') or 0))
            if vampire:
                before_health = int(attacker['health'])
                attacker['health'] = min(
                    int(attacker.get('max_health') or before_health),
                    before_health + dealt * vampire,
                )
                events.append({
                    'type': 'enemy_heal',
                    'enemy_id': attacker['id'],
                    'amount': int(attacker['health']) - before_health,
                    'before': before_health,
                    'after': int(attacker['health']),
                    'source': 'vampire',
                })
            if 'bloodthirsty' in STORY_ENEMIES.get(attacker.get('def_id'), {}).get('traits', ()):
                before_power = int(attacker.get('power') or 0)
                attacker['power'] = before_power + 1
                events.append({
                    'type': 'enemy_gain',
                    'enemy_id': attacker['id'],
                    'effect_kind': 'power',
                    'amount': 1,
                    'before': before_power,
                    'after': int(attacker['power']),
                    'source': 'bloodthirsty',
                })
    return total


def _apply_enemy_lethal_rules(state, enemy, before, dealt, events):
    """Apply one-use enemy survival mechanics and return recorded damage."""
    if STORY_ENEMIES.get(enemy.get('def_id'), {}).get('script') == 'broken_machine':
        enemy['health'] = 1
        return 0
    after = before - dealt
    if dealt > 0 and after <= 1 and int(enemy.get('psionic_sustain') or 0) > 0 and any(
        item.get('def_id') == 'termite_mound'
        for item in _living_enemies(state['combat'])
    ):
        enemy['health'] = 1
        if not enemy.get('psionic_sustain_revive_pending'):
            enemy['stun'] = max(2, int(enemy.get('stun') or 0))
            enemy['psionic_sustain_revive_pending'] = True
            events.append({
                'type': 'enemy_survived',
                'enemy_id': enemy['id'],
                'source': 'psionic_sustain',
            })
        return max(0, before - 1)
    if after > 0:
        enemy['health'] = after
        return dealt
    script = STORY_ENEMIES.get(enemy.get('def_id'), {}).get('script')
    if script == 'bandage_beetle' and enemy.get('bandage_triggered'):
        # The durable marker is authoritative even if an older/stale state
        # accidentally restores the visible stack counter.
        enemy['bandage'] = 0
    elif script == 'bandage_beetle' and int(enemy.get('bandage') or 0) > 0:
        enemy['bandage'] = 0
        enemy['health'] = 1
        enemy['bandage_triggered'] = True
        enemy['bandage_invincible_pending'] = True
        enemy['invincible'] = 1
        enemy['forced_move_index'] = 2
        events.append({'type': 'enemy_survived', 'enemy_id': enemy['id'], 'source': 'bandage'})
        return max(0, before - 1)
    if script == 'shiny_ladybug' and not enemy.get('yggdrasil_used'):
        enemy['yggdrasil_used'] = True
        enemy['yggdrasil_revive_pending'] = True
        enemy['invincible'] = 1
        enemy['stun'] = max(1, int(enemy.get('stun') or 0))
        enemy['health'] = 1
        events.append({'type': 'enemy_survived', 'enemy_id': enemy['id'], 'source': 'yggdrasil_power'})
        return max(0, before - 1)
    enemy['health'] = before - dealt
    return dealt


def _connected_enemies(combat, enemy):
    if not _enemy_has_trait(enemy, 'psionic_connection'):
        return []
    connected = _living_enemies_with_trait(combat, 'psionic_connection')
    if len(connected) <= 1:
        return []
    return [enemy] + [item for item in connected if item is not enemy]


def _split_damage(amount, targets):
    if not targets:
        return []
    quotient, remainder = divmod(max(0, int(amount)), len(targets))
    return [quotient + (1 if index < remainder else 0) for index in range(len(targets))]


def _enemy_magic_shield(enemy, amount, events, source):
    amount = max(0, int(amount))
    shield_value = max(0, int(enemy.get('magic_shield') or 0))
    magic = max(0, int(enemy.get('magic') or 0))
    if not amount or not shield_value or not magic or int(enemy.get('magic_shield_disabled') or 0) > 0:
        return amount, 0
    spent = min(magic, math.ceil(amount / shield_value))
    blocked = min(amount, spent * shield_value)
    enemy['magic'] = magic - spent
    events.append({
        'type': 'enemy_magic_shield',
        'enemy_id': enemy['id'],
        'amount': blocked,
        'magic_spent': spent,
        'source': source,
    })
    return amount - blocked, blocked


def _record_enemy_health_damage(enemy, dealt):
    if dealt <= 0:
        return
    enemy['damage_taken_round'] = int(enemy.get('damage_taken_round') or 0) + dealt
    if STORY_ENEMIES.get(enemy.get('def_id'), {}).get('script') == 'fossil':
        enemy['fossil_awaken_pending'] = True


def _reveal_rat_from_cover(state, cover, events):
    for rat in _living_enemies(state['combat']):
        if (
            STORY_ENEMIES.get(rat.get('def_id'), {}).get('script')
            != 'mechanical_rat'
            or rat.get('hidden_cover_id') != cover.get('id')
            or int(rat.get('hidden') or 0) <= 0
        ):
            continue
        before = int(rat['hidden'])
        rat['hidden'] = 0
        rat.pop('hidden_fresh', None)
        events.append({
            'type': 'status_cleared',
            'target_id': rat['id'],
            'status': 'hidden',
            'before': before,
            'source': cover['id'],
        })


def _after_enemy_health_damage(state, enemy, dealt, events):
    if dealt <= 0:
        return
    script = STORY_ENEMIES.get(enemy.get('def_id'), {}).get('script')
    if script != 'chimney':
        return
    progress = max(0, int(enemy.get('smoke_damage_progress') or 0)) + int(dealt)
    summon_count, enemy['smoke_damage_progress'] = divmod(progress, 100)
    for _ in range(summon_count):
        _summon_enemy(
            state,
            'smoke',
            events,
            actor_id=enemy['id'],
            source_definition_id=enemy['def_id'],
        )
    if summon_count:
        events.append({
            'type': 'chimney_smoke_triggered',
            'enemy_id': enemy['id'],
            'count': summon_count,
            'remaining_damage': int(enemy['smoke_damage_progress']),
        })


def _enemy_raw_damage(
    state,
    enemy,
    amount,
    events,
    source,
    propagate=False,
    player_caused=False,
):
    if not enemy or int(enemy.get('health') or 0) <= 0:
        return 0
    amount = max(0, int(amount))
    if player_caused and not propagate and _has_relic(state, 'frenzy_relic'):
        amount = math.floor(
            amount * float(STORY_RELICS['frenzy_relic']['amount'])
        )
    connected = [] if propagate else _connected_enemies(state['combat'], enemy)
    if connected:
        return sum(
            _enemy_raw_damage(
                state,
                target,
                share,
                events,
                source,
                propagate=True,
                player_caused=player_caused,
            )
            for target, share in zip(connected, _split_damage(amount, connected))
        )
    if int(enemy.get('invincible') or 0) > 0:
        events.append({
            'type': 'enemy_damage',
            'enemy_id': enemy['id'],
            'amount': 0,
            'hits': 1,
            'hit_index': 1,
            'hit_count': 1,
            'history': [{'before': int(enemy['health']), 'after': int(enemy['health']), 'blocked': max(0, int(amount))}],
            'before': int(enemy['health']),
            'after': int(enemy['health']),
            'source': source,
        })
        return 0
    amount, magic_blocked = _enemy_magic_shield(enemy, amount, events, source)
    shield = int(enemy.get('shield') or 0)
    blocked = min(shield, amount)
    enemy['shield'] = shield - blocked
    dealt = amount - blocked
    incoming_health_damage = dealt
    before = int(enemy['health'])
    dealt = _apply_enemy_lethal_rules(state, enemy, before, dealt, events)
    _record_enemy_health_damage(enemy, dealt)
    damage_event = {
        'type': 'enemy_damage',
        'enemy_id': enemy['id'],
        'amount': dealt,
        'hits': 1,
        'hit_index': 1,
        'hit_count': 1,
        'history': [{'before': before, 'after': int(enemy['health']), 'blocked': blocked + magic_blocked}],
        'before': before,
        'after': int(enemy['health']),
        'source': source,
    }
    events.append(damage_event)
    if (
        incoming_health_damage > 0
        and STORY_ENEMIES.get(enemy.get('def_id'), {}).get('script')
        == 'broken_machine'
    ):
        _reveal_rat_from_cover(state, enemy, events)
    _after_enemy_health_damage(state, enemy, dealt, events)
    if dealt and STORY_ENEMIES[enemy['def_id']].get('script') == 'swell':
        enemy['temporary_power'] = int(enemy.get('temporary_power') or 0) + 1
    if dealt and STORY_ENEMIES[enemy['def_id']].get('script') == 'centipede' and not propagate:
        enemies = state['combat']['enemies']
        index = enemies.index(enemy)
        for adjacent_index in (index - 1, index + 1):
            if 0 <= adjacent_index < len(enemies):
                adjacent = enemies[adjacent_index]
                if STORY_ENEMIES[adjacent['def_id']].get('script') == 'centipede':
                    _enemy_raw_damage(state, adjacent, math.floor(dealt / 2), events, 'linked', propagate=True)
    return dealt


def _player_attack_effect_segment(state, effect, target, context):
    """Return the base damage and hit count for one card attack effect."""
    combat = state['combat']
    effect_type = str(effect.get('type') or '')
    amount = int(effect.get('amount') or 0)
    if effect_type == 'damage':
        base_amount = amount
        hits = max(1, int(effect.get('hits') or 1))
    elif effect_type == 'damage_per_status':
        base_amount = amount
        hits = int(effect.get('base_hits') or 0) + _status_count(target)
    elif effect_type == 'damage_per_active_discard':
        base_amount = amount + int(combat.get('active_discards_this_combat') or 0)
        hits = 1
    elif effect_type == 'damage_from_shield':
        base_amount = (
            int(combat.get('shield') or 0) * amount
            + int(effect.get('bonus') or 0)
        )
        hits = 1
    elif effect_type == 'damage_per_elixir':
        base_amount = amount
        hits = int(context.get('x_cost') or 0)
    else:
        return None
    return max(0, base_amount), max(0, hits)


def _player_attack_hit_amount(
    state,
    enemy,
    base_amount,
    effect=None,
    attack_multiplier=1,
):
    """Apply shared player-side and target-side modifiers to one physical hit."""
    combat = state['combat']
    effect = effect or {}
    power_scale = int(effect['power_scale']) if 'power_scale' in effect else 1
    power = int(combat.get('power') or 0) + int(combat.get('temporary_power') or 0)
    amount = max(0, int(base_amount) + power * power_scale)
    amount = math.floor(amount * float(attack_multiplier or 1))
    if effect.get('damage_multiplier'):
        amount = math.floor(amount * float(effect['damage_multiplier']))
    if _has_relic(state, 'frenzy_relic'):
        amount = math.floor(
            amount * float(STORY_RELICS['frenzy_relic']['amount'])
        )
    if int(combat.get('weak') or 0) > 0:
        amount = math.floor(amount * 0.75)
    if int(enemy.get('vulnerable') or 0) > 0:
        amount = math.floor(amount * 1.5)
    return max(0, amount)


def _enemy_special_damage_amount(enemy, amount, consume=False):
    amount = max(0, int(amount))
    if amount <= 0:
        return 0
    if int(enemy.get('hidden') or 0) > 0:
        amount = min(amount, 1)
    evil_eye = int(enemy.get('evil_eye') or 0)
    if evil_eye > 0:
        if amount >= 10:
            amount = max(0, amount - 9)
            if consume:
                enemy['evil_eye'] = evil_eye - 1
        else:
            amount = 1
    hard_shell = max(0, int(enemy.get('hard_shell') or 0))
    if hard_shell:
        amount = max(0, amount - hard_shell)
    disc = max(0, int(enemy.get('disc') or 0))
    if disc:
        amount = math.floor(amount / disc)
    return amount


def _trigger_enemy_attack_reactions(state, enemy, amount, events, source):
    if amount <= 0:
        return
    combat = state['combat']
    toxic = max(0, int(enemy.get('toxic_reflection') or 0))
    if toxic:
        _apply_status(state, combat, 'poison', toxic, events, source='toxic_reflection')
    if max(0, int(enemy.get('magic_reflection') or 0)):
        reflection_before = int(enemy['magic_reflection'])
        enemy['magic_reflection'] = reflection_before - 1
        before = int(enemy.get('magic') or 0)
        enemy['magic'] = before + 1
        events.append({
            'type': 'enemy_gain',
            'enemy_id': enemy['id'],
            'effect_kind': 'magic',
            'amount': 1,
            'before': before,
            'after': int(enemy['magic']),
            'source': 'magic_reflection',
        })
        events.append({
            'type': 'status_decay',
            'target_id': enemy['id'],
            'status': 'magic_reflection',
            'before': reflection_before,
            'after': int(enemy['magic_reflection']),
            'source': 'magic_reflection',
        })
    if _enemy_has_trait(enemy, 'nest_instinct'):
        for ally in _living_enemies(combat):
            before = int(ally.get('temporary_power') or 0)
            ally['temporary_power'] = before + 1
            events.append({
                'type': 'enemy_gain',
                'enemy_id': ally['id'],
                'effect_kind': 'temporary_power',
                'amount': 1,
                'before': before,
                'after': int(ally['temporary_power']),
                'source': 'nest_instinct',
            })


def _enemy_physical_damage(
    state,
    enemy,
    base_amount,
    hits,
    events,
    source,
    values=None,
    attack_multiplier=1,
    seed=None,
):
    combat = state['combat']
    values = values or {}
    hit_count = max(0, int(hits))
    if hit_count <= 0:
        return 0
    base_hit_amount = _player_attack_hit_amount(
        state,
        enemy,
        base_amount,
        values,
        attack_multiplier=attack_multiplier,
    )
    tags = _card_tags(values)
    precise = 'precise' in tags
    total = 0
    resolved_hit = False
    for hit_index in range(1, hit_count + 1):
        hit_amount = base_hit_amount
        evade = max(0, int(enemy.get('evade') or 0))
        if evade > 0:
            enemy['evade'] = evade - 1
            if precise:
                reduced = int(math.ceil(hit_amount / 2))
                prevented = max(0, hit_amount - reduced)
                hit_amount = reduced
            else:
                prevented = hit_amount
            events.append({
                'type': 'evade',
                'target_id': enemy['id'],
                'amount': prevented,
                'source': source,
                'precision': precise,
                'hit_index': hit_index,
                'hit_count': hit_count,
            })
            if not precise:
                before = int(enemy['health'])
                events.append({
                    'type': 'enemy_damage',
                    'enemy_id': enemy['id'],
                    'amount': 0,
                    'hits': 1,
                    'hit_index': hit_index,
                    'hit_count': hit_count,
                    'history': [{
                        'before': before,
                        'after': before,
                        'blocked': prevented,
                    }],
                    'before': before,
                    'after': before,
                    'source': source,
                })
                continue
        resolved_hit = True
        amount = _enemy_special_damage_amount(enemy, hit_amount, consume=True)
        connected = _connected_enemies(combat, enemy)
        if connected:
            split_total = 0
            for target, share in zip(connected, _split_damage(amount, connected)):
                split_total += _enemy_raw_damage(
                    state,
                    target,
                    share,
                    events,
                    source,
                    propagate=True,
                    player_caused=False,
                )
            total += split_total
            _trigger_enemy_attack_reactions(state, enemy, amount, events, source)
            continue
        amount, magic_blocked = _enemy_magic_shield(enemy, amount, events, source)
        shield = int(enemy.get('shield') or 0)
        invincible = int(enemy.get('invincible') or 0) > 0
        blocked = amount if invincible else min(shield, amount)
        if not invincible:
            enemy['shield'] = shield - blocked
        dealt = 0 if invincible else amount - blocked
        incoming_health_damage = dealt
        before = int(enemy['health'])
        dealt = _apply_enemy_lethal_rules(state, enemy, before, dealt, events)
        _record_enemy_health_damage(enemy, dealt)
        total += dealt
        after = int(enemy['health'])
        events.append({
            'type': 'enemy_damage',
            'enemy_id': enemy['id'],
            'amount': dealt,
            'hits': 1,
            'hit_index': hit_index,
            'hit_count': hit_count,
            'history': [{'before': before, 'after': after, 'blocked': blocked + magic_blocked}],
            'before': before,
            'after': after,
            'source': source,
        })
        if (
            incoming_health_damage > 0
            and STORY_ENEMIES.get(enemy.get('def_id'), {}).get('script')
            == 'broken_machine'
        ):
            _reveal_rat_from_cover(state, enemy, events)
        _after_enemy_health_damage(state, enemy, dealt, events)
        reflection = int(enemy.get('reflection') or 0)
        if reflection > 0 and amount > 0:
            _player_damage(state, reflection, 1, events, 'reflection')
        _trigger_enemy_attack_reactions(state, enemy, amount, events, source)
        if dealt and STORY_ENEMIES[enemy['def_id']].get('script') == 'centipede':
            enemies = combat['enemies']
            index = enemies.index(enemy)
            for adjacent_index in (index - 1, index + 1):
                if 0 <= adjacent_index < len(enemies):
                    adjacent = enemies[adjacent_index]
                    if STORY_ENEMIES[adjacent['def_id']].get('script') == 'centipede':
                        _enemy_raw_damage(state, adjacent, math.floor(dealt / 2), events, 'linked', propagate=True)
    if not resolved_hit:
        return total
    definition = STORY_ENEMIES[enemy['def_id']]
    if 'swell' in definition.get('traits', ()):
        enemy['temporary_power'] = int(enemy.get('temporary_power') or 0) + 1
    if 'charged' in definition.get('traits', ()):
        charge = max(0, int(enemy.get('charged') or 0))
        if charge:
            for hand_card in combat.get('hand', []):
                hand_card.setdefault('modifiers', {})['charge'] = int(
                    hand_card.get('modifiers', {}).get('charge') or 0
                ) + charge
            events.append({
                'type': 'hand_charged',
                'amount': charge,
                'source': enemy['def_id'],
            })
    if definition.get('script') == 'random_intent' and len(definition.get('moves') or ()) > 1:
        current = int(enemy.get('move_index') or 0) % len(definition['moves'])
        choices = [index for index in range(len(definition['moves'])) if index != current]
        if choices:
            enemy['move_index'] = (
                _rng(state, seed, f'chaos:{enemy["id"]}').choice(choices)
                if seed is not None
                else choices[0]
            )
            events.append({'type': 'enemy_intent_changed', 'enemy_id': enemy['id'], 'reason': 'chaos'})
    return total


def _resolve_player_death(state, events):
    if int(state['player'].get('health') or 0) > 0:
        return False
    if _has_relic(state, 'world_tree_leaf') and not state.get('flags', {}).get('world_tree_leaf_used'):
        state.setdefault('flags', {})['world_tree_leaf_used'] = True
        state['player']['health'] = int(state['player']['max_health'])
        combat = state.get('combat') or {}
        for key in (
            'weak', 'vulnerable', 'fragile', 'poison', 'stun', 'broken',
            'toxic_poison', 'stagnation', 'bleed', 'fire', 'blockade',
        ):
            combat[key] = 0
        events.append({'type': 'revive', 'source': 'world_tree_leaf'})
        return False
    state['player']['health'] = 0
    state['phase'] = 'game_over'
    events.append({'type': 'game_over'})
    return True


def _surrender_run(state, events):
    if state.get('phase') in ('complete', 'game_over'):
        _fail('STORY_RUN_ENDED', '旅程已经结束')
    if state.get('phase') == 'journey_setup':
        _fail('SURRENDER_NOT_ALLOWED', '当前无法投降')
    player = state.setdefault('player', {})
    before = int(player.get('health') or 0)
    player['health'] = 0
    state['phase'] = 'game_over'
    state.pop('pending_deck_operations', None)
    combat = state.get('combat')
    if isinstance(combat, dict):
        combat.pop('pending_card_choice', None)
        combat['turn'] = 'ended'
    state.pop('recovery_checkpoint', None)
    events.append({
        'type': 'player_damage',
        'amount': max(0, before),
        'source': 'surrender',
        'source_definition_id': 'surrender',
        'history': [{'before': before, 'after': 0, 'blocked': 0}],
    })
    events.append({'type': 'story_surrender'})
    events.append({'type': 'game_over'})


def _must_play_attack_card(state, card):
    if not _has_relic(state, 'frenzy_relic'):
        return False
    if _card_values(card).get('type') == 'thorn':
        return False
    return any(
        _card_values(hand_card).get('type') == 'thorn'
        for hand_card in (state.get('combat') or {}).get('hand', [])
    )


def _is_card_playable(state, card, automatic=False):
    combat = state.get('combat') or {}
    values = _card_values(card)
    tags = _card_tags(values)
    if (
        'unplayable' in tags
        or combat.get('turn') != 'player'
        or combat.get('opening_redraw_pending')
        or combat.get('pending_card_choice')
        or (not automatic and _must_play_attack_card(state, card))
        or (
            values.get('type') == 'thorn'
            and int(combat.get('attack_blocked') or 0) > 0
        )
    ):
        return False
    blockade = max(0, int(combat.get('blockade') or 0))
    if blockade and card in combat.get('hand', []):
        hand_index = combat['hand'].index(card)
        if hand_index % 2 == 0 and hand_index // 2 < blockade:
            return False
    selectable_hand = [
        item for item in combat.get('hand', [])
        if item is not card and 'sublime' not in _card_tags(_card_values(item))
    ]
    for effect in values.get('effects') or ():
        effect_type = str(effect.get('type') or '')
        if (
            effect_type in ('active_discard', 'random_active_discard')
            and effect.get('exact')
            and len(selectable_hand) < max(0, int(effect.get('amount') or 0))
        ):
            return False
        if effect_type == 'recover_exiled' and not any(
            'sublime' not in _card_tags(_card_values(item))
            for item in combat.get('exile_pile', [])
        ):
            return False
    if combat.get('card_play_limit') is not None and int(combat.get('cards_played_this_turn') or 0) >= int(combat['card_play_limit']):
        return False
    if values.get('target') == 'enemy' and not _selectable_enemy_targets(combat, values):
        return False
    cost_e = values.get('cost_e')
    if cost_e == 'X':
        cost_e = 0
    return int(combat.get('elixir') or 0) >= int(cost_e or 0) and int(combat.get('magic') or 0) >= int(values.get('cost_m') or 0)


def _selected_cards(combat, payload, source_card, key='selected_card_ids', pile='hand'):
    raw_ids = payload.get(key) or []
    if isinstance(raw_ids, str):
        raw_ids = [raw_ids]
    if not isinstance(raw_ids, list):
        _fail('INVALID_CARD_SELECTION', '卡牌选择无效')
    source = combat.get(pile, [])
    selected = []
    seen = set()
    for raw_id in raw_ids:
        instance_id = str(raw_id or '')
        if not instance_id or instance_id in seen:
            continue
        card = next((item for item in source if item.get('instance_id') == instance_id), None)
        if not card or card is source_card:
            _fail('INVALID_CARD_SELECTION', '所选卡牌不在可选范围内')
        if 'sublime' in _card_tags(_card_values(card)):
            _fail('INVALID_CARD_SELECTION', '带有崇高的牌无法被该行为选中')
        selected.append(card)
        seen.add(instance_id)
    return selected


def _validate_card_selections(combat, card, values, payload):
    for effect in values.get('effects') or ():
        effect_type = effect.get('type')
        if effect_type in ('choose_exile', 'copy_hand_card', 'make_card_free', 'active_discard'):
            selected = _selected_cards(combat, payload, card)
            maximum = max(1, int(effect.get('amount') or 1))
            exact = effect_type in ('copy_hand_card', 'make_card_free') or bool(effect.get('exact'))
            available = len([
                item for item in combat['hand']
                if item is not card and 'sublime' not in _card_tags(_card_values(item))
            ])
            required = 0 if effect_type == 'choose_exile' and available == 0 else maximum
            if exact and available < required:
                _fail('CARD_NOT_PLAYABLE', '没有足够的可选择手牌')
            if exact and len(selected) != required:
                _fail('CARD_SELECTION_REQUIRED', f'请选择{required}张牌')
            if len(selected) > maximum:
                _fail('TOO_MANY_CARDS_SELECTED', '选择的牌过多')
        elif effect_type == 'recover_exiled':
            selected = _selected_cards(
                combat,
                payload,
                card,
                key='selected_exile_ids',
                pile='exile_pile',
            )
            required = max(1, int(effect.get('amount') or 1))
            if len(selected) != required:
                _fail('CARD_SELECTION_REQUIRED', f'请选择{required}张放逐区牌')
        elif effect_type == 'discard_to_draw_top':
            selected = _selected_cards(combat, payload, card, key='selected_discard_ids', pile='discard_pile')
            if combat['discard_pile'] and len(selected) != 1:
                _fail('CARD_SELECTION_REQUIRED', '请选择1张弃牌')


_REPEATED_CARD_SELECTION_KEYS = (
    'selected_card_ids',
    'selected_exile_ids',
    'selected_discard_ids',
)


def _repeated_card_base_payload(payload):
    return {
        key: copy.deepcopy(value)
        for key, value in (payload or {}).items()
        if key not in _REPEATED_CARD_SELECTION_KEYS
    }


def _repeated_card_selection_spec(combat, card, values):
    for effect in values.get('effects') or ():
        effect_type = str(effect.get('type') or '')
        if effect_type in ('choose_exile', 'copy_hand_card', 'make_card_free', 'active_discard'):
            cards = [
                item for item in combat.get('hand', [])
                if item is not card
                and 'sublime' not in _card_tags(_card_values(item))
            ]
            requested = max(1, int(effect.get('amount') or 1))
            exact = (
                effect_type in ('copy_hand_card', 'make_card_free')
                or bool(effect.get('exact'))
            )
            required = (
                0
                if effect_type == 'choose_exile' and not cards
                else (requested if exact else 0)
            )
            return {
                'possible': len(cards) >= required,
                'payload_key': 'selected_card_ids',
                'minimum': required,
                'maximum': min(requested, len(cards)),
                'cards': cards,
            }
        if effect_type == 'recover_exiled':
            cards = [
                item for item in combat.get('exile_pile', [])
                if 'sublime' not in _card_tags(_card_values(item))
            ]
            requested = max(1, int(effect.get('amount') or 1))
            return {
                'possible': len(cards) >= requested,
                'payload_key': 'selected_exile_ids',
                'minimum': requested,
                'maximum': min(requested, len(cards)),
                'cards': cards,
            }
        if effect_type == 'discard_to_draw_top':
            cards = [
                item for item in combat.get('discard_pile', [])
                if 'sublime' not in _card_tags(_card_values(item))
            ]
            required = 1 if combat.get('discard_pile') else 0
            return {
                'possible': len(cards) >= required,
                'payload_key': 'selected_discard_ids',
                'minimum': required,
                'maximum': min(1, len(cards)),
                'cards': cards,
            }
        if effect_type == 'random_active_discard' and effect.get('exact'):
            cards = [
                item for item in combat.get('hand', [])
                if item is not card
            ]
            requested = max(0, int(effect.get('amount') or 0))
            return {
                'possible': len(cards) >= requested,
                'payload_key': '',
                'minimum': 0,
                'maximum': 0,
                'cards': [],
            }
    return None


def _resolve_opening_redraw(state, payload, seed, events):
    if state.get('phase') != 'combat':
        _fail('NOT_IN_COMBAT', '当前不在战斗中')
    combat = state['combat']
    if combat.get('turn') != 'player' or not combat.get('opening_redraw_pending'):
        _fail('NO_OPENING_REDRAW', '当前没有待处理的冷却效果')
    selected = _selected_cards(combat, payload, None)
    for card in selected:
        combat['hand'].remove(card)
        combat['discard_pile'].append(card)
        events.append({
            'type': 'card_discarded',
            'card_instance_id': card['instance_id'],
            'reason': 'cooldown',
        })
    combat['opening_redraw_pending'] = False
    if selected:
        _draw_cards(state, len(selected), seed, events)
    _play_ready_cards_in_hand(state, seed, events)
    events.append({'type': 'opening_redraw_resolved', 'count': len(selected)})


def _resolve_pending_card_choice(state, payload, seed, events):
    if state.get('phase') != 'combat':
        _fail('NOT_IN_COMBAT', '当前不在战斗中')
    combat = state['combat']
    pending = combat.get('pending_card_choice')
    if not isinstance(pending, dict):
        _fail('NO_CARD_CHOICE', '当前没有待处理的卡牌选择')
    raw_ids = payload.get('selected_card_ids')
    if not isinstance(raw_ids, list):
        raw_ids = []
    selected_ids = [str(item or '') for item in raw_ids if str(item or '')]
    if len(selected_ids) != len(set(selected_ids)):
        _fail('DUPLICATE_CARD_SELECTION', '不能重复选择同一张牌')
    minimum = max(0, int(pending.get('minimum') or 0))
    maximum = max(minimum, int(pending.get('maximum') or 0))
    if not minimum <= len(selected_ids) <= maximum:
        _fail('INVALID_CARD_SELECTION_COUNT', f'请选择{minimum}至{maximum}张牌')
    options = pending.get('cards') if isinstance(pending.get('cards'), list) else []
    by_id = {
        str(option.get('instance_id') or ''): option
        for option in options
        if isinstance(option, dict)
    }
    if any(instance_id not in by_id for instance_id in selected_ids):
        _fail('INVALID_CARD_SELECTION', '所选卡牌不属于本次选项')
    kind = str(pending.get('kind') or '')
    after_choice_repeat = pending.get('after_choice_repeat')
    combat.pop('pending_card_choice', None)
    if kind == 'generated_card':
        selected = by_id[selected_ids[0]]
        modifiers = selected.setdefault('modifiers', {})
        modifiers['swift'] = max(99, int(modifiers.get('swift') or 0))
        modifiers['force_exile'] = True
        modifiers['force_void'] = True
        _put_in_hand(state, selected, events)
        events.append({
            'type': 'card_choice_resolved',
            'kind': kind,
            'selected_card_ids': selected_ids,
        })
    elif kind == 'inspect_draw':
        selected_set = set(selected_ids)
        for option in options:
            if str(option.get('instance_id') or '') in selected_set:
                _put_in_hand(state, option, events)
            else:
                combat['discard_pile'].append(option)
        events.append({
            'type': 'card_choice_resolved',
            'kind': kind,
            'selected_card_ids': selected_ids,
        })
    elif kind == 'active_discard':
        hand_by_id = {
            str(item.get('instance_id') or ''): item
            for item in combat.get('hand', [])
        }
        selected = [hand_by_id.get(instance_id) for instance_id in selected_ids]
        if any(item is None for item in selected):
            _fail('INVALID_CARD_SELECTION', '所选卡牌已不在手牌中')
        _actively_discard_cards(
            state,
            selected,
            seed,
            events,
            source=str(pending.get('source') or 'card'),
        )
        events.append({
            'type': 'card_choice_resolved',
            'kind': kind,
            'selected_card_ids': selected_ids,
        })
    elif kind == 'repeat_card_play':
        continuation = pending.get('continuation')
        if not isinstance(continuation, dict):
            _fail('INVALID_CARD_REPEAT', '待继续结算的卡牌数据无效')
        repeat_payload = copy.deepcopy(continuation.get('payload') or {})
        payload_key = str(pending.get('payload_key') or '')
        if payload_key:
            repeat_payload[payload_key] = selected_ids
        _resume_repeated_card_play(
            state,
            continuation,
            repeat_payload,
            seed,
            events,
        )
        return
    else:
        _fail('UNKNOWN_CARD_CHOICE', '无法处理该卡牌选择')
    if isinstance(after_choice_repeat, dict):
        continuation_card = after_choice_repeat.get('card')
        if not isinstance(continuation_card, dict):
            _fail('INVALID_CARD_REPEAT', '待继续结算的卡牌数据无效')
        _continue_repeated_card_play(
            state,
            continuation_card,
            after_choice_repeat.get('target_ids') or [],
            after_choice_repeat.get('payload') or {},
            after_choice_repeat.get('repeat_index') or 0,
            after_choice_repeat.get('repeat_count') or 0,
            after_choice_repeat.get('context') or {},
            bool(after_choice_repeat.get('sewage_was_active')),
            seed,
            events,
        )
        if combat.get('pending_card_choice'):
            return
    _play_ready_cards_in_hand(state, seed, events)
    _check_combat_end(state, seed, events)


def _selectable_enemy_targets(combat, values):
    living = _living_enemies(combat)
    if not living:
        return []
    bulbs = [enemy for enemy in living if int(enemy.get('bulb') or 0) > 0]
    if bulbs:
        living = bulbs
    return living


def _card_targets(combat, values, payload):
    living = _selectable_enemy_targets(combat, values)
    if values.get('target') != 'enemy':
        return [combat]
    if 'wide' in _card_tags(values):
        return living
    target_id = str(payload.get('target_id') or '')
    target = next(
        (enemy for enemy in living if str(enemy.get('id') or '') == target_id),
        None,
    )
    if target is None and len(living) == 1:
        target = living[0]
    if target is None:
        _fail('NO_TARGET', '请选择一个可选中的生物')
    return [target]


def _resolve_effect(state, card, values, effect, targets, payload, seed, events, context):
    combat = state['combat']
    effect_type = str(effect.get('type') or '')
    amount = effect.get('amount', 0)
    if effect_type in STORY_PLAYER_ATTACK_EFFECT_TYPES:
        for target in targets:
            segment = _player_attack_effect_segment(state, effect, target, context)
            if segment is None:
                continue
            hit_amount, hits = segment
            attack_values = copy.deepcopy(effect)
            attack_values['tags'] = tuple(_card_tags(values))
            _enemy_physical_damage(
                state,
                target,
                hit_amount,
                hits,
                events,
                _localized(values.get('name')),
                values=attack_values,
                attack_multiplier=context.get('attack_multiplier', 1),
                seed=seed,
            )
    elif effect_type == 'status':
        for target in targets:
            _apply_status(state, target, str(effect.get('status') or ''), int(amount), events)
    elif effect_type == 'status_self':
        _apply_status(state, combat, str(effect.get('status') or ''), int(amount), events)
    elif effect_type == 'shield':
        _gain_shield(state, int(amount), events)
    elif effect_type == 'power':
        combat['power'] = int(combat.get('power') or 0) + int(amount)
        events.append({'type': 'status', 'target_id': 'player', 'status': 'power', 'amount': int(amount)})
    elif effect_type == 'first_use_power':
        used = combat.setdefault('card_use_counts', {}).get(card['def_id'], 0)
        if used == 0:
            combat['power'] = int(combat.get('power') or 0) + int(amount)
    elif effect_type == 'elixir':
        _gain_elixir(state, int(amount), events)
    elif effect_type == 'magic':
        _gain_magic(state, int(amount), events)
    elif effect_type == 'draw':
        _draw_cards(state, int(amount), seed, events, context.get('autoplay_depth', 0))
    elif effect_type == 'draw_selected':
        _draw_cards(
            state,
            max(0, int(context.get('selected_count') or 0) + int(amount or 0)),
            seed,
            events,
            context.get('autoplay_depth', 0),
            effect.get('filter'),
        )
    elif effect_type == 'draw_to_limit':
        _draw_cards(state, max(0, int(STORY_RULES['hand_limit']) - len(combat['hand'])), seed, events, context.get('autoplay_depth', 0))
    elif effect_type == 'draw_target_status':
        target = targets[0]
        _draw_cards(state, int(target.get(effect.get('status')) or 0), seed, events, context.get('autoplay_depth', 0))
    elif effect_type == 'shield_from_target_status':
        target = targets[0]
        _gain_shield(state, int(target.get(effect.get('status')) or 0) * int(amount), events)
    elif effect_type == 'choose_exile':
        selected = _selected_cards(combat, payload, card)
        context['selected_count'] = len(selected)
        for selected_card in selected:
            combat['hand'].remove(selected_card)
            combat['exile_pile'].append(selected_card)
            _notify_exiled(state, selected_card, events, seed)
    elif effect_type == 'active_discard':
        selected = _selected_cards(combat, payload, card)
        discarded = _actively_discard_cards(
            state,
            selected,
            seed,
            events,
            source=card.get('def_id') or 'card',
        )
        context['selected_count'] = len(discarded)
    elif effect_type == 'random_active_discard':
        candidates = [
            item for item in combat['hand']
            if item is not card and 'sublime' not in _card_tags(_card_values(item))
        ]
        requested = max(0, int(amount))
        if effect.get('exact') and len(candidates) < requested:
            _fail('CARD_NOT_PLAYABLE', '没有足够的可丢弃手牌')
        selected = _rng(state, seed, 'random_active_discard').sample(
            candidates,
            min(requested, len(candidates)),
        )
        discarded = _actively_discard_cards(
            state,
            selected,
            seed,
            events,
            source=card.get('def_id') or 'card',
        )
        context['selected_count'] = len(discarded)
    elif effect_type == 'active_discard_all':
        candidates = [
            item for item in list(combat['hand'])
            if item is not card
            and 'sublime' not in _card_tags(_card_values(item))
            and (
                effect.get('filter') != 'positive_e'
                or int(_card_values(item).get('cost_e') or 0) > 0
            )
        ]
        discarded = _actively_discard_cards(
            state,
            candidates,
            seed,
            events,
            source=card.get('def_id') or 'card',
        )
        context['selected_count'] = len(discarded)
    elif effect_type == 'shield_selected':
        _gain_shield(
            state,
            max(0, int(context.get('selected_count') or 0)) * int(amount),
            events,
        )
    elif effect_type == 'random_exile':
        candidates = [item for item in combat['hand'] if item is not card]
        for selected_card in _rng(state, seed, 'random_exile').sample(candidates, min(int(amount), len(candidates))):
            combat['hand'].remove(selected_card)
            combat['exile_pile'].append(selected_card)
            _notify_exiled(state, selected_card, events, seed)
    elif effect_type == 'exile_hand_for_shield':
        victims = [item for item in list(combat['hand']) if item is not card]
        for selected_card in victims:
            combat['hand'].remove(selected_card)
            combat['exile_pile'].append(selected_card)
            _notify_exiled(state, selected_card, events, seed)
        _gain_shield(state, len(victims) * int(amount), events)
    elif effect_type == 'copy_hand_card':
        selected = _selected_cards(combat, payload, card)
        if selected:
            copied = _new_card(
                state,
                selected[0]['def_id'],
                selected[0].get('upgraded'),
                selected[0].get('modifiers'),
            )
            if int(effect.get('swift') or 0) > 0:
                copied.setdefault('modifiers', {})['swift'] = int(effect['swift'])
            _put_in_hand(state, copied, events)
    elif effect_type == 'recover_exiled':
        selected = _selected_cards(
            combat,
            payload,
            card,
            key='selected_exile_ids',
            pile='exile_pile',
        )
        for selected_card in selected:
            combat['exile_pile'].remove(selected_card)
            modifiers = selected_card.setdefault('modifiers', {})
            modifiers['force_exile'] = True
            modifiers['force_void'] = True
            _put_in_hand(state, selected_card, events)
    elif effect_type == 'make_card_free':
        selected = _selected_cards(combat, payload, card)
        if selected:
            modifiers = selected[0].setdefault('modifiers', {})
            modifiers['free_play'] = True
            modifiers['force_exile'] = True
            events.append({
                'type': 'card_modified',
                'card_instance_id': selected[0]['instance_id'],
                'modifier': 'free_exile',
            })
    elif effect_type == 'next_attack_multiplier':
        combat['next_attack_multiplier'] = max(float(combat.get('next_attack_multiplier') or 1), float(amount))
    elif effect_type == 'next_skill_repeats':
        combat['next_skill_repeats'] = max(int(combat.get('next_skill_repeats') or 0), int(amount))
    elif effect_type == 'temporary_effect':
        script = str(effect.get('script') or '')
        if script == 'sewage':
            combat['sewage_active'] = True
            for hand_card in combat.get('hand', []):
                hand_card.setdefault('modifiers', {})['temporary_free_e'] = True
        elif script == 'disc':
            combat['disc_active'] = True
        elif script:
            combat[script] = True
    elif effect_type == 'temporary_cost_down':
        scope = effect.get('scope')
        for hand_card in combat['hand']:
            hand_values = _card_values(hand_card)
            if scope != 'all' and hand_values.get('type') != scope:
                continue
            current = int(hand_values.get('cost_e') or 0)
            minimum = int(effect.get('minimum') or 0)
            reduction = min(int(amount), max(0, current - minimum))
            if reduction:
                hand_card.setdefault('modifiers', {})['cost_e_delta'] = int(hand_card.get('modifiers', {}).get('cost_e_delta') or 0) - reduction
                hand_card['modifiers']['temporary_cost'] = True
    elif effect_type == 'decaying_shield':
        delta = int(card.get('modifiers', {}).get('shield_value_delta') or 0)
        _gain_shield(state, max(0, int(amount) + delta), events)
        card.setdefault('modifiers', {})['shield_value_delta'] = delta - int(effect.get('decay') or 0)
    elif effect_type == 'delayed_copy':
        combat.setdefault('delayed_copies', []).append({
            'def_id': card['def_id'],
            'upgraded': bool(card.get('upgraded')),
            'turns': 1,
        })
    elif effect_type == 'delayed_player_status':
        combat.setdefault('delayed_player_statuses', []).append({
            'status': str(effect.get('status') or ''),
            'amount': int(amount),
        })
    elif effect_type == 'draw_attack_power':
        drawn_ids = _draw_cards(
            state,
            int(amount),
            seed,
            events,
            context.get('autoplay_depth', 0),
        )
        by_id = {
            item['instance_id']: item
            for pile_name in ('hand', 'discard_pile')
            for item in combat.get(pile_name, [])
        }
        attacks = sum(
            1 for instance_id in drawn_ids
            if instance_id in by_id
            and _card_values(by_id[instance_id]).get('type') == 'thorn'
        )
        power = max(0, int(effect.get('power') or 0)) * (
            attacks if int(amount) > 1 else 1
        )
        if power:
            before = int(combat.get('temporary_power') or 0)
            combat['temporary_power'] = before + power
            events.append({
                'type': 'status',
                'target_id': 'player',
                'status': 'temporary_power',
                'amount': power,
                'before': before,
                'after': int(combat['temporary_power']),
                'source': card.get('def_id'),
            })
        if attacks and int(effect.get('elixir') or 0):
            _gain_elixir(state, int(effect['elixir']), events)
    elif effect_type == 'create_discard_copy':
        created = _new_card(state, card['def_id'], bool(card.get('upgraded')))
        combat['discard_pile'].append(created)
        events.append({
            'type': 'card_created',
            'card_instance_id': created['instance_id'],
            'def_id': created['def_id'],
            'destination': 'discard_pile',
        })
    elif effect_type == 'shield_with_power':
        _gain_shield(
            state,
            int(amount) + int(combat.get('power') or 0) + int(combat.get('temporary_power') or 0),
            events,
        )
    elif effect_type == 'permanent_damage_growth':
        _sync_persistent_card_modifier(state, card, 'damage_bonus', int(amount))
        events.append({
            'type': 'card_modified',
            'card_instance_id': card['instance_id'],
            'modifier': 'damage_bonus',
            'amount': int(amount),
            'permanent': True,
        })
    elif effect_type == 'permanent_swift':
        _sync_persistent_card_modifier(state, card, 'swift', int(amount))
        events.append({
            'type': 'card_modified',
            'card_instance_id': card['instance_id'],
            'modifier': 'swift',
            'amount': int(amount),
            'permanent': True,
        })
    elif effect_type == 'self_swift':
        modifiers = card.setdefault('modifiers', {})
        before = max(0, int(modifiers.get('swift') or 0))
        modifiers['swift'] = before + max(0, int(amount))
        events.append({
            'type': 'card_modified',
            'card_instance_id': card['instance_id'],
            'modifier': 'swift',
            'amount': max(0, int(amount)),
            'before': before,
            'after': int(modifiers['swift']),
        })
    elif effect_type == 'elixir_if_active_discard':
        if int(combat.get('active_discards_this_turn') or 0) > 0:
            _gain_elixir(state, int(amount), events)
    elif effect_type == 'random_damage_per_discards':
        hits = 1 + math.floor(
            int(combat.get('active_discards_this_turn') or 0)
            / max(1, int(effect.get('divisor') or 1))
        )
        attack_values = copy.deepcopy(effect)
        attack_values['tags'] = tuple(_card_tags(values))
        for _ in range(hits):
            living = _living_enemies(combat)
            if not living:
                break
            target = _rng(state, seed, 'maple_random_target').choice(living)
            _enemy_physical_damage(
                state,
                target,
                int(amount),
                1,
                events,
                _localized(values.get('name')),
                values=attack_values,
                attack_multiplier=context.get('attack_multiplier', 1),
                seed=seed,
            )
    elif effect_type == 'choose_random_generated':
        pool = list(STORY_CARDS)
        count = min(max(1, int(amount)), len(pool))
        selected_ids = _rng(state, seed, 'assembler_options').sample(pool, count)
        options = [
            _new_card(
                state,
                card_id,
                bool(effect.get('upgraded') and STORY_CARDS[card_id].get('upgrade')),
            )
            for card_id in selected_ids
        ]
        combat['pending_card_choice'] = {
            'kind': 'generated_card',
            'title': {'zh': '选择1张牌', 'en': 'Choose 1 card'},
            'minimum': 1,
            'maximum': 1,
            'cards': options,
        }
    elif effect_type == 'inspect_draw_choose':
        count = min(max(0, int(amount)), len(combat.get('draw_pile', [])))
        options = [combat['draw_pile'].pop() for _ in range(count)]
        choose = min(max(0, int(effect.get('choose') or 0)), len(options))
        if options:
            combat['pending_card_choice'] = {
                'kind': 'inspect_draw',
                'title': {'zh': f'选择{choose}张牌加入手牌', 'en': f'Choose {choose} cards for your hand'},
                'minimum': choose,
                'maximum': choose,
                'cards': options,
            }
    elif effect_type == 'draw_then_discard':
        _draw_cards(
            state,
            int(amount),
            seed,
            events,
            context.get('autoplay_depth', 0),
        )
        candidates = [
            item for item in combat.get('hand', [])
            if 'sublime' not in _card_tags(_card_values(item))
        ]
        required = min(max(0, int(effect.get('discard') or 0)), len(candidates))
        if required:
            combat['pending_card_choice'] = {
                'kind': 'active_discard',
                'title': {'zh': f'主动丢弃{required}张牌', 'en': f'Actively discard {required} cards'},
                'minimum': required,
                'maximum': required,
                'cards': candidates,
                'source': card.get('def_id'),
            }
    elif effect_type == 'lose_health':
        lost = max(0, int(amount))
        before = int(state['player'].get('health') or 0)
        state['player']['health'] = before - lost
        events.append({
            'type': 'player_damage',
            'amount': lost,
            'hits': 1,
            'hit_index': 1,
            'hit_count': 1,
            'history': [{'before': before, 'after': int(state['player']['health']), 'blocked': 0}],
            'before': before,
            'after': int(state['player']['health']),
            'source': card.get('def_id'),
            'health_loss': True,
        })
    elif effect_type == 'swap_piles_draw':
        combat['draw_pile'], combat['discard_pile'] = (
            combat.get('discard_pile', []),
            combat.get('draw_pile', []),
        )
        events.append({'type': 'piles_swapped'})
        _draw_cards(state, int(amount), seed, events, context.get('autoplay_depth', 0))
    elif effect_type == 'next_turn_draw':
        combat['next_turn_draw_delta'] = int(combat.get('next_turn_draw_delta') or 0) + int(amount)
    elif effect_type == 'immediate_extra_turn':
        combat['immediate_extra_turn'] = True
        combat.setdefault('pending_extra_turn_statuses', []).append({
            'status': 'broken',
            'amount': int(amount),
        })
    elif effect_type == 'discard_to_draw_top':
        selected = context.get('reserved_discard_cards') or []
        if selected:
            combat['draw_pile'].append(selected[0])
    elif effect_type == 'elixir_from_hand':
        _gain_elixir(state, math.floor(len(combat['hand']) * float(amount)), events)
    elif effect_type == 'salt':
        combat.setdefault('salt_multipliers', []).append(int(amount))
    elif effect_type == 'shuffle_hand_redraw':
        shuffled = list(combat['hand'])
        combat['hand'] = []
        combat['draw_pile'].extend(shuffled)
        _rng(state, seed, 'shuffle_hand_redraw').shuffle(combat['draw_pile'])
        events.append({
            'type': 'hand_shuffled',
            'count': len(shuffled),
            'card_instance_ids': [item['instance_id'] for item in shuffled],
        })
        _draw_cards(
            state,
            len(shuffled) + max(0, int(amount)),
            seed,
            events,
            context.get('autoplay_depth', 0),
        )
    elif effect_type == 'equipment':
        pass


def _destination_for_card(values, card):
    modifiers = card.get('modifiers') or {}
    tags = _card_tags(values)
    if 'exile' in tags or modifiers.get('force_exile'):
        return 'exile_pile'
    if values.get('script') == 'return_draw_top':
        return 'draw_pile'
    if values.get('type') == 'root':
        return 'equipment'
    return 'discard_pile'


def _targets_from_repeat_ids(combat, target_ids):
    targets = []
    for raw_target_id in target_ids or ():
        target_id = str(raw_target_id or '')
        if target_id == 'player':
            targets.append(combat)
            continue
        target = next(
            (
                enemy for enemy in combat.get('enemies', [])
                if str(enemy.get('id') or '') == target_id
            ),
            None,
        )
        if target is None:
            _fail('REPEAT_TARGET_MISSING', '待继续结算的目标已不存在')
        targets.append(target)
    return targets


def _resolve_card_effects_once(
        state, card, values, targets, payload, seed, events, base_context,
        repeat_index):
    combat = state['combat']
    _validate_card_selections(combat, card, values, payload)
    context = dict(base_context or {})
    context.pop('selected_count', None)
    reserved_discard_cards = []
    if any(
        effect.get('type') == 'discard_to_draw_top'
        for effect in values.get('effects') or ()
    ):
        reserved_discard_cards = _selected_cards(
            combat,
            payload,
            card,
            key='selected_discard_ids',
            pile='discard_pile',
        )
        for selected_card in reserved_discard_cards:
            combat['discard_pile'].remove(selected_card)
    context['reserved_discard_cards'] = reserved_discard_cards
    direct_target_ids = {
        str(target.get('id') or 'player')
        for target in targets
    }
    instance_id = str(card.get('instance_id') or '')
    for effect_index, effect in enumerate(values.get('effects') or ()):
        effect_event_start = len(events)
        _resolve_effect(
            state,
            card,
            values,
            effect,
            targets,
            payload,
            seed,
            events,
            context,
        )
        effect_events = events[effect_event_start:]
        group_prefix = (
            f'card:{instance_id}:repeat:{repeat_index}:effect:{effect_index}'
        )
        for event in effect_events:
            event.setdefault('actor_id', 'player')
            event.setdefault('source_card_instance_id', instance_id)
            event.setdefault('source_definition_id', card.get('def_id'))
            event.setdefault('effect_index', effect_index)
            event.setdefault('repeat_index', repeat_index)
            event_targets = set(_story_event_target_ids(event))
            if (
                len(direct_target_ids) > 1
                and event_targets.intersection(direct_target_ids)
                and event.get('source') not in ('linked', 'reflection')
            ):
                hit_index = max(0, int(event.get('hit_index') or 0))
                event.setdefault(
                    'parallel_group',
                    f'{group_prefix}:hit:{hit_index}' if hit_index else group_prefix,
                )


def _finalize_played_card(
        state, card, values, seed, events, base_context,
        sewage_was_active):
    combat = state['combat']
    instance_id = str(card.get('instance_id') or '')
    if (
        values.get('script') == 'light_sprout'
        and 'exile' not in _card_tags(values)
        and not (card.get('modifiers') or {}).get('force_exile')
    ):
        generated = _new_card(
            state,
            card['def_id'],
            card.get('upgraded'),
            {'generated': True, 'force_exile': True},
        )
        draw_pile = combat['draw_pile']
        insert_at = _rng(state, seed, 'light_sprout').randrange(len(draw_pile) + 1)
        draw_pile.insert(insert_at, generated)
        events.append({
            'type': 'card_created',
            'card_instance_id': generated['instance_id'],
            'def_id': generated['def_id'],
            'destination': 'draw_pile',
            'actor_id': 'player',
            'source_card_instance_id': instance_id,
            'source_definition_id': card['def_id'],
        })

    destination_event_start = len(events)
    destination = _destination_for_card(values, card)
    if destination == 'equipment':
        card['turns_equipped'] = 0
        combat['equipment'].append(card)
        events.append({
            'type': 'equipment_added',
            'card_instance_id': card['instance_id'],
            'def_id': card['def_id'],
        })
    else:
        combat[destination].append(card)
        if destination == 'exile_pile':
            _notify_exiled(state, card, events, seed)
    for event in events[destination_event_start:]:
        event.setdefault('actor_id', 'player')
        event.setdefault('source_card_instance_id', instance_id)
        event.setdefault('source_definition_id', card['def_id'])
    combat['cards_played_this_turn'] = int(combat.get('cards_played_this_turn') or 0) + 1
    counts = combat.setdefault('card_use_counts', {})
    counts[card['def_id']] = int(counts.get(card['def_id']) or 0) + 1
    if values.get('type') == 'thorn' and int(combat.get('bleed') or 0) > 0:
        bleed = int(combat['bleed'])
        _player_raw_damage(state, bleed, events, 'bleed')
        combat['bleed'] = math.floor(bleed / 2)
        events.append({
            'type': 'status_decay',
            'target_id': 'player',
            'status': 'bleed',
            'before': bleed,
            'after': int(combat['bleed']),
        })
    if values.get('script') == 'factory_waste':
        for target in _living_enemies(combat):
            if target.get('def_id') != 'reconstructor_enemy':
                continue
            target['received_factory_waste'] = True
            target['missed_factory_waste_last_turn'] = False
            before_fragment = int(target.get('fragment') or 0)
            target['fragment'] = before_fragment + 1
            before_power = int(target.get('power') or 0)
            target['power'] = before_power + 1
            if int(target['fragment']) >= 5:
                target['move_index'] = 4
            else:
                target['move_index'] = _rng(
                    state,
                    seed,
                    f'reconstructor_fragment:{target["id"]}',
                ).randrange(3)
            events.extend((
                {
                    'type': 'status',
                    'target_id': target['id'],
                    'status': 'fragment',
                    'amount': 1,
                    'before': before_fragment,
                    'after': int(target['fragment']),
                    'source': 'factory_waste',
                },
                {
                    'type': 'enemy_gain',
                    'enemy_id': target['id'],
                    'effect_kind': 'power',
                    'amount': 1,
                    'before': before_power,
                    'after': int(target['power']),
                    'source': 'factory_waste',
                },
                {
                    'type': 'enemy_intent_changed',
                    'enemy_id': target['id'],
                    'reason': 'reconstruction',
                },
            ))
    if int(combat.get('broken') or 0) > 0:
        _player_raw_damage(state, int(combat['broken']), events, 'broken')
    if sewage_was_active and state.get('phase') == 'combat':
        discard_candidates = [
            item for item in combat.get('hand', [])
            if 'sublime' not in _card_tags(_card_values(item))
        ]
        if discard_candidates:
            discarded = _rng(state, seed, 'sewage_active_discard').choice(
                discard_candidates
            )
            _actively_discard_cards(
                state,
                [discarded],
                seed,
                events,
                source='sewage',
            )
    if _check_combat_end(state, seed, events):
        return
    if combat.pop('immediate_extra_turn', False):
        _prepare_player_turn_end(state, seed, events, reason='immediate_extra_turn')
        if _check_combat_end(state, seed, events):
            return
        _turn_boundary(state, seed, events, extra=True)


def _continue_repeated_card_play(
        state, card, target_ids, base_payload, repeat_index, repeat_count,
        base_context, sewage_was_active, seed, events):
    combat = state['combat']
    repeat_index = max(0, int(repeat_index or 0))
    repeat_count = max(repeat_index, int(repeat_count or 0))
    pending = combat.get('pending_card_choice')
    if isinstance(pending, dict):
        pending['after_choice_repeat'] = {
            'card': copy.deepcopy(card),
            'target_ids': list(target_ids or ()),
            'payload': copy.deepcopy(base_payload or {}),
            'repeat_index': repeat_index,
            'repeat_count': repeat_count,
            'context': copy.deepcopy(base_context or {}),
            'sewage_was_active': bool(sewage_was_active),
        }
        return
    while repeat_index < repeat_count:
        values = _card_values(card)
        selection = _repeated_card_selection_spec(combat, card, values)
        if selection and not selection.get('possible'):
            break
        if selection and int(selection.get('maximum') or 0) > 0:
            card_name_zh = _localized(values.get('name'), 'zh')
            card_name_en = _localized(values.get('name'), 'en')
            combat['pending_card_choice'] = {
                'kind': 'repeat_card_play',
                'operation_id': f'{card.get("instance_id")}:repeat:{repeat_index}',
                'title': {
                    'zh': f'再次结算{card_name_zh}',
                    'en': f'Resolve {card_name_en} again',
                },
                'minimum': int(selection.get('minimum') or 0),
                'maximum': int(selection.get('maximum') or 0),
                'cards': copy.deepcopy(selection.get('cards') or []),
                'payload_key': str(selection.get('payload_key') or ''),
                'continuation': {
                    'card': copy.deepcopy(card),
                    'target_ids': list(target_ids or ()),
                    'payload': copy.deepcopy(base_payload or {}),
                    'repeat_index': repeat_index,
                    'repeat_count': repeat_count,
                    'context': copy.deepcopy(base_context or {}),
                    'sewage_was_active': bool(sewage_was_active),
                },
            }
            return
        repeat_payload = copy.deepcopy(base_payload or {})
        if selection and selection.get('payload_key'):
            repeat_payload[str(selection['payload_key'])] = []
        targets = _targets_from_repeat_ids(combat, target_ids)
        _resolve_card_effects_once(
            state,
            card,
            values,
            targets,
            repeat_payload,
            seed,
            events,
            base_context,
            repeat_index,
        )
        repeat_index += 1
        pending = combat.get('pending_card_choice')
        if isinstance(pending, dict):
            pending['after_choice_repeat'] = {
                'card': copy.deepcopy(card),
                'target_ids': list(target_ids or ()),
                'payload': copy.deepcopy(base_payload or {}),
                'repeat_index': repeat_index,
                'repeat_count': repeat_count,
                'context': copy.deepcopy(base_context or {}),
                'sewage_was_active': bool(sewage_was_active),
            }
            return
    _finalize_played_card(
        state,
        card,
        _card_values(card),
        seed,
        events,
        base_context,
        sewage_was_active,
    )


def _resume_repeated_card_play(state, continuation, payload, seed, events):
    card = continuation.get('card')
    if not isinstance(card, dict) or not card.get('instance_id'):
        _fail('INVALID_CARD_REPEAT', '待继续结算的卡牌数据无效')
    combat = state['combat']
    repeat_index = max(0, int(continuation.get('repeat_index') or 0))
    repeat_count = max(repeat_index + 1, int(continuation.get('repeat_count') or 0))
    target_ids = list(continuation.get('target_ids') or ())
    base_context = copy.deepcopy(continuation.get('context') or {})
    values = _card_values(card)
    targets = _targets_from_repeat_ids(combat, target_ids)
    _resolve_card_effects_once(
        state,
        card,
        values,
        targets,
        payload,
        seed,
        events,
        base_context,
        repeat_index,
    )
    _continue_repeated_card_play(
        state,
        card,
        target_ids,
        continuation.get('payload') or {},
        repeat_index + 1,
        repeat_count,
        base_context,
        bool(continuation.get('sewage_was_active')),
        seed,
        events,
    )


def _play_card(state, payload, seed, events, autoplay_depth=0):
    if state.get('phase') != 'combat':
        _fail('NOT_IN_COMBAT', '当前不在战斗中')
    combat = state['combat']
    if combat.get('turn') != 'player':
        _fail('NOT_PLAYER_TURN', '当前不是玩家回合')
    instance_id = str(payload.get('card_instance_id') or '')
    card = next((item for item in combat['hand'] if item['instance_id'] == instance_id), None)
    if not card:
        _fail('CARD_NOT_IN_HAND', '这张牌不在手牌中')
    values = _card_values(card)
    if not _is_card_playable(state, card, automatic=bool(payload.get('automatic'))):
        _fail('CARD_NOT_PLAYABLE', '当前无法打出这张牌')
    sewage_was_active = bool(combat.get('sewage_active'))
    _validate_card_selections(combat, card, values, payload)
    if int(combat.get('cards_played_this_turn') or 0) == 1:
        for enemy in _living_enemies(combat):
            miracle = max(0, int(enemy.get('miracle') or 0))
            if 'miracle' in STORY_ENEMIES[enemy['def_id']].get('traits', ()) and miracle:
                enemy['miracle'] = miracle - 1
                events.append({
                    'type': 'enemy_gain',
                    'enemy_id': enemy['id'],
                    'effect_kind': 'miracle',
                    'amount': -1,
                    'before': miracle,
                    'after': int(enemy['miracle']),
                    'source': 'miracle',
                })
                _apply_status(state, enemy, 'evade', 1, events, source='miracle')
    targets = _card_targets(combat, values, payload)
    cost_e = values.get('cost_e')
    x_cost = int(combat.get('elixir') or 0) if cost_e == 'X' else int(cost_e or 0)
    cost_m = int(values.get('cost_m') or 0)
    combat['elixir'] = max(0, int(combat.get('elixir') or 0) - x_cost)
    combat['magic'] = max(0, int(combat.get('magic') or 0) - cost_m)
    combat['hand'].remove(card)
    events.append({
        'type': 'card_played',
        'card_instance_id': instance_id,
        'def_id': card['def_id'],
        'target_ids': [target.get('id', 'player') for target in targets],
        'automatic': bool(payload.get('automatic')),
        'actor_id': 'player',
        'source_card_instance_id': instance_id,
        'source_definition_id': card['def_id'],
    })
    charge = max(0, int((card.get('modifiers') or {}).get('charge') or 0))
    if charge:
        _player_raw_damage(state, charge, events, 'charge')
    is_attack = values.get('type') == 'thorn'
    is_skill = values.get('type') == 'bloom'
    attack_multiplier = float(combat.get('next_attack_multiplier') or 1) if is_attack else 1
    if is_attack:
        combat['next_attack_multiplier'] = 1
        if _has_relic(state, 'blade') and not combat.get('blade_used'):
            combat['blade_used'] = True
            for target in targets:
                _apply_status(
                    state,
                    target,
                    'vulnerable',
                    _relic_amount(state, 'blade'),
                    events,
                    source='blade',
                )
        if _has_relic(state, 'sword_strategy'):
            _gain_shield(
                state,
                int(STORY_RELICS['sword_strategy']['amount']),
                events,
                source='sword_strategy',
            )
    if is_skill:
        for enemy in _living_enemies_with_trait(combat, 'endurance_shell'):
            _gain_shield(
                state,
                int(enemy.get('endurance_shell') or 0),
                events,
                source='endurance_shell',
                enemy=enemy,
            )
    consumes_skill_repeats = is_skill and card.get('def_id') != 'fission'
    repeats = 1 + (
        int(combat.get('next_skill_repeats') or 0)
        if consumes_skill_repeats
        else 0
    )
    if consumes_skill_repeats:
        combat['next_skill_repeats'] = 0
    context = {
        'x_cost': x_cost,
        'attack_multiplier': attack_multiplier,
        'autoplay_depth': autoplay_depth,
    }
    _resolve_card_effects_once(
        state,
        card,
        values,
        targets,
        payload,
        seed,
        events,
        context,
        0,
    )
    _continue_repeated_card_play(
        state,
        card,
        [target.get('id', 'player') for target in targets],
        _repeated_card_base_payload(payload),
        1,
        repeats,
        context,
        sewage_was_active,
        seed,
        events,
    )


def _enemy_intent(state, enemy):
    definition = STORY_ENEMIES[enemy['def_id']]
    if definition.get('script') == 'broken_machine':
        return {
            'move_index': -1,
            'name': {'zh': '损坏', 'en': 'Broken'},
            'entries': [],
            'summary': '',
        }
    if definition.get('script') == 'mechanical_flower':
        track = enemy.get('mechanical_track') or []
        if not track:
            return {
                'move_index': 0,
                'name': definition['moves'][0]['name'],
                'entries': [],
                'summary': '',
            }
        card = track[0]
        values = _card_values(card)
        damage, shield, can_draw = _mechanical_track_base_totals(card)
        recycled = damage + shield < 10 and not can_draw
        card_name = values.get('name') or card.get('def_id')
        label = {
            'zh': (
                f'回收{_localized(card_name, "zh")}'
                if recycled
                else f'触发{_localized(card_name, "zh")}'
            ),
            'en': (
                f'Recycle {_localized(card_name, "en")}'
                if recycled
                else f'Resolve {_localized(card_name, "en")}'
            ),
        }
        return {
            'move_index': 0,
            'name': definition['moves'][0]['name'],
            'entries': [{
                'kind': 'card',
                'effect_type': 'mechanical_track',
                'card_id': card.get('def_id'),
                'card': copy.deepcopy(card),
                'amount': 1,
                'target': 'player',
                'label': label,
                'recycled': recycled,
            }],
            'summary': label['zh'],
        }
    move = _next_enemy_move(state, enemy)
    move_index = definition['moves'].index(move)
    parts = []
    entries = []
    for effect in move['effects']:
        effect_type = effect['type']
        amount = _effect_amount(state, effect)
        hits = _effect_hits(state, effect)
        if effect_type == 'damage':
            value = _enemy_physical_hit_amount(state, enemy, amount)
            summary = _damage_summary([value] * hits)
            entries.append({
                'kind': 'attack',
                'amount': value,
                'hits': hits,
                'target': 'player',
                'summary': summary,
            })
            parts.append(summary)
        elif effect_type == 'damage_from_shield':
            divisor = max(1, int(effect.get('divisor') or 1))
            value = _enemy_physical_hit_amount(
                state,
                enemy,
                amount + math.floor(int(enemy.get('shield') or 0) / divisor),
            )
            entries.append({'kind': 'attack', 'amount': value, 'hits': 1, 'target': 'player'})
            parts.append(f'{value}D')
        elif effect_type == 'damage_from_player_status':
            value = _enemy_physical_hit_amount(
                state,
                enemy,
                amount + max(0, int(state['combat'].get(str(effect.get('status') or '')) or 0)),
            )
            entries.append({'kind': 'attack', 'amount': value, 'hits': 1, 'target': 'player'})
            parts.append(f'{value}D')
        elif effect_type == 'consume_status_damage':
            divisor_key = 'lunatic_divisor' if _difficulty(state) == 'lunatic' else 'divisor'
            divisor = max(1, int(effect.get(divisor_key) or effect.get('divisor') or 1))
            value = _enemy_physical_hit_amount(
                state,
                enemy,
                math.floor(max(0, int(enemy.get(str(effect.get('status') or '')) or 0)) / divisor),
            )
            status = str(effect.get('status') or '')
            entries.append({
                'kind': 'attack',
                'amount': value,
                'hits': 1,
                'target': 'player',
                'details': {
                    'zh': f'清除自身{_story_term_name(status)}',
                    'en': f'Clear own {_story_term_name(status, "en")}',
                },
            })
            parts.append(f'{value}D')
        elif effect_type == 'consume_magic_damage':
            value = _enemy_physical_hit_amount(
                state,
                enemy,
                amount + max(0, int(enemy.get('magic') or 0)) * max(0, int(effect.get('multiplier') or 0)),
            )
            entries.append({
                'kind': 'attack',
                'amount': value,
                'hits': 1,
                'target': 'player',
                'details': {'zh': '消耗全部M', 'en': 'Spend all M'},
            })
            parts.append(f'{value}D并消耗全部M')
        elif effect_type == 'self_damage':
            entries.append({
                'kind': 'self_damage',
                'amount': amount,
                'hits': hits,
                'target': 'self',
            })
            parts.append(f'自己受到{amount}D')
        elif effect_type == 'gain_power':
            entries.append({'kind': 'buff', 'stat': 'power', 'amount': amount, 'target': 'self'})
            parts.append(f'获得{amount}层力量')
        elif effect_type == 'gain_shield':
            entries.append({'kind': 'defend', 'stat': 'shield', 'amount': amount, 'target': 'self'})
            parts.append(f'获得{amount}层护盾')
        elif effect_type == 'gain_status':
            status = str(effect.get('status') or '')
            entries.append({
                'kind': 'status',
                'status': status,
                'amount': amount,
                'target': 'self',
            })
            parts.append(f'获得{amount}层{_story_term_name(status)}')
        elif effect_type == 'player_status':
            status = str(effect.get('status') or '')
            entries.append({
                'kind': 'status',
                'status': status,
                'amount': amount,
                'target': 'player',
            })
            parts.append(f'施加{amount}层{_story_term_name(status)}')
        elif effect_type == 'summon_to_ant_count':
            entries.append({
                'kind': 'special',
                'effect_type': effect_type,
                'amount': amount,
                'label': {
                    'zh': f'补充蚂蚁至{amount}只',
                    'en': f'Fill the ant group to {amount}',
                },
                'target': 'self',
            })
            parts.append(f'补充蚂蚁至{amount}只')
        elif effect_type == 'summon_wreckage':
            wreckage_definition = STORY_ENEMIES.get('wreckage') or {}
            entries.append({
                'kind': 'summon',
                'enemy_id': 'wreckage',
                'enemy_name': wreckage_definition.get('name') or '残骸',
                'amount': amount,
                'target': 'self',
                'details': {
                    'zh': '死后依次召唤螃蟹、睡莲与海胆',
                    'en': 'Their deaths summon Crab, Lily Pad, and Urchin in order',
                },
            })
            parts.append(f'召唤{amount}个残骸，死后依次召唤螃蟹、睡莲与海胆')
        elif effect_type == 'summon':
            summoned_id = str(effect.get('enemy_id') or '')
            summoned_definition = STORY_ENEMIES.get(summoned_id) or {}
            summoned_name = _localized(summoned_definition.get('name')) or summoned_id
            summoned_count = amount or 1
            entries.append({
                'kind': 'summon',
                'enemy_id': summoned_id,
                'enemy_name': summoned_definition.get('name') or summoned_name,
                'amount': summoned_count,
                'target': 'self',
            })
            parts.append(f'召唤{summoned_count}只{summoned_name}')
        elif effect_type in ('allies_power', 'allies_shield', 'allies_heal'):
            stats = {'allies_power': 'power', 'allies_shield': 'shield', 'allies_heal': 'health'}
            entry_kind = 'heal' if effect_type == 'allies_heal' else (
                'defend' if effect_type == 'allies_shield' else 'buff'
            )
            entries.append({
                'kind': entry_kind,
                'stat': stats[effect_type],
                'amount': amount,
                'target': 'all_enemies',
            })
            parts.append(f"全体生物+{amount}{_story_term_name(stats[effect_type])}")
        elif effect_type == 'allies_status':
            status = str(effect.get('status') or '')
            entries.append({
                'kind': 'status',
                'status': status,
                'amount': amount,
                'target': 'all_enemies',
            })
            parts.append(f'全体生物获得{amount}层{_story_term_name(status)}')
        elif effect_type == 'named_allies_power':
            named_id = str(effect.get('enemy_id') or '')
            named_definition = STORY_ENEMIES.get(named_id) or {}
            entries.append({
                'kind': 'buff',
                'stat': 'power',
                'amount': amount,
                'target': 'named_enemy',
                'enemy_id': named_id,
                'enemy_name': named_definition.get('name') or named_id,
            })
            parts.append(f'{_localized(named_definition.get("name")) or "指定生物"}获得{amount}层力量')
        elif effect_type == 'heal_named_ally_percent':
            named_id = str(effect.get('enemy_id') or '')
            named_definition = STORY_ENEMIES.get(named_id) or {}
            entries.append({
                'kind': 'heal',
                'amount': amount,
                'target': 'named_enemy',
                'enemy_id': named_id,
                'enemy_name': named_definition.get('name') or named_id,
                'percent': True,
            })
            parts.append(f'{_localized(named_definition.get("name")) or "指定生物"}回复{amount}%H')
        elif effect_type in ('lowest_ally_shield', 'adjacent_shield'):
            entries.append({
                'kind': 'defend',
                'stat': 'shield',
                'amount': amount,
                'target': effect_type,
            })
            parts.append(f'生物获得{amount}层护盾')
        elif effect_type == 'self_heal':
            entries.append({'kind': 'heal', 'stat': 'health', 'amount': amount, 'target': 'self'})
            parts.append(f'回复{amount}H')
        elif effect_type == 'add_draw_card':
            entries.append({
                'kind': 'card',
                'card_id': effect.get('card_id'),
                'amount': amount or 1,
                'target': 'player',
            })
            parts.append('向抽牌堆加入牌')
        elif effect_type == 'consume_allies':
            entries.append({'kind': 'consume', 'target': 'all_enemies'})
            parts.append('吞噬生物')
        elif effect_type in {
            'gain_charged', 'gain_charging', 'gain_frenzy', 'gain_hidden',
            'gain_sturdy',
        }:
            status = {
                'gain_charged': 'charged',
                'gain_charging': 'charging',
                'gain_frenzy': 'frenzy',
                'gain_hidden': 'hidden',
                'gain_sturdy': 'sturdy',
            }[effect_type]
            entries.append({'kind': 'status', 'status': status, 'amount': amount, 'target': 'self'})
            parts.append(f'获得{amount}层{_story_term_name(status)}')
        elif effect_type == 'clear_status':
            status = str(effect.get('status') or '')
            entries.append({'kind': 'clear_status', 'status': status, 'target': 'self'})
            parts.append(f'清除{_story_term_name(status)}')
        elif effect_type == 'delayed_hand_charge':
            entries.append({'kind': 'card', 'effect_type': effect_type, 'amount': amount, 'target': 'player'})
            parts.append(f'下回合使所有手牌获得{amount}层电荷')
        elif effect_type == 'all_cards_charge':
            entries.append({
                'kind': 'card',
                'effect_type': effect_type,
                'amount': amount,
                'target': 'player',
            })
            parts.append(f'使所有牌获得{amount}层电荷')
        elif effect_type == 'halve_player_status':
            status = str(effect.get('status') or '')
            entries.append({
                'kind': 'consume_status',
                'status': status,
                'amount': math.ceil(max(0, int(state['combat'].get(status) or 0)) / 2),
                'target': 'player',
            })
            parts.append(f'清除一半{_story_term_name(status)}')
        elif effect_type == 'delayed_player_status':
            status = str(effect.get('status') or '')
            entries.append({'kind': 'status', 'status': status, 'amount': amount, 'target': 'player', 'delayed': True})
            parts.append(f'下回合施加{amount}层{_story_term_name(status)}')
        elif effect_type == 'gain_magic':
            entries.append({
                'kind': 'resource',
                'resource': 'magic',
                'amount': amount,
                'target': 'self',
            })
            parts.append(f'获得{amount}M')
        elif effect_type == 'disable_magic_shield':
            entries.append({
                'kind': 'special',
                'effect_type': effect_type,
                'amount': amount,
                'target': 'self',
                'label': {
                    'zh': '下回合魔力护盾失效',
                    'en': 'Magic Shield is disabled next turn',
                },
            })
            parts.append('下回合魔力护盾失效')
        elif effect_type == 'consume_status':
            status = str(effect.get('status') or '')
            entries.append({
                'kind': 'consume_status',
                'status': status,
                'amount': amount,
                'target': 'self',
            })
            parts.append(f'消耗{amount}层{_story_term_name(status)}')
        elif effect_type == 'heal_to_full':
            entries.append({'kind': 'heal', 'target': 'self', 'full': True})
            parts.append('回复至满H')
        elif effect_type == 'lose_max_health_percent':
            entries.append({'kind': 'special', 'effect_type': effect_type, 'amount': amount, 'target': 'self'})
            parts.append(f'H上限-{amount}%')
        elif effect_type == 'consume_pearls_damage':
            entries.append({'kind': 'attack', 'amount': amount, 'target': 'player', 'conditional': 'pearls'})
            parts.append(f'每颗珍珠额外造成{amount}D')
        elif effect_type == 'stun_if_player_shield':
            entries.append({'kind': 'status', 'status': 'stun', 'amount': 1, 'target': 'player', 'conditional': 'shield'})
            parts.append('若玩家仍有护盾则施加1层眩晕')
        elif effect_type == 'self_kill':
            entries.append({'kind': 'self_damage', 'target': 'self', 'lethal': True})
            parts.append('自身死亡')
        else:
            label = {
                'zh': '执行特殊行动',
                'en': 'Perform a special action',
            }
            entries.append({
                'kind': 'special',
                'effect_type': effect_type,
                'amount': amount,
                'label': label,
            })
            parts.append(label['zh'])
    return {
        'move_index': move_index,
        'name': move['name'],
        'entries': entries,
        'summary': '；'.join(parts),
    }


def _card_damage_prediction(state, card, enemy):
    if not enemy:
        return None
    values = _card_values(card)
    if values.get('type') != 'thorn':
        return None
    combat = state['combat']
    predicted = []
    cost_e = values.get('cost_e')
    context = {
        'attack_multiplier': float(combat.get('next_attack_multiplier') or 1),
        'x_cost': (
            int(combat.get('elixir') or 0)
            if cost_e == 'X'
            else int(cost_e or 0)
        ),
    }
    simulated_enemy = copy.deepcopy(enemy)
    shield = int(simulated_enemy.get('shield') or 0)
    dodge = max(0, int(simulated_enemy.get('evade') or 0))
    precise = 'precise' in _card_tags(values)
    for effect in values.get('effects') or ():
        segment = _player_attack_effect_segment(state, effect, enemy, context)
        if segment is None:
            continue
        base_amount, hits = segment
        raw_value = _player_attack_hit_amount(
            state,
            simulated_enemy,
            base_amount,
            effect,
            attack_multiplier=context.get('attack_multiplier', 1),
        )
        for _ in range(max(0, hits)):
            hit_value = raw_value
            if dodge > 0:
                dodge -= 1
                if precise:
                    hit_value = int(math.ceil(hit_value / 2))
                else:
                    predicted.append(0)
                    continue
            value = _enemy_special_damage_amount(simulated_enemy, hit_value, consume=True)
            blocked = min(shield, max(0, value))
            shield -= blocked
            predicted.append(max(0, value) - blocked)
    if not predicted:
        return None
    return {'total': sum(predicted), 'hits': predicted, 'summary': _damage_summary(predicted)}


def _refresh_combat_projections(state):
    combat = state.get('combat')
    if not isinstance(combat, dict):
        return
    living = _living_enemies(combat)
    predictions = {}
    for card in combat.get('hand', []):
        by_target = {}
        values = _card_values(card)
        targets = _selectable_enemy_targets(combat, values) if values.get('target') == 'enemy' else living
        for enemy in targets:
            prediction = _card_damage_prediction(state, card, enemy)
            if prediction:
                by_target[enemy['id']] = prediction
        if by_target:
            first = next(iter(by_target.values()))
            predictions[card['instance_id']] = {**first, 'by_target': by_target}
    combat['damage_predictions'] = predictions
    combat['playable_card_ids'] = [
        card['instance_id']
        for card in combat.get('hand', [])
        if _is_card_playable(state, card)
    ]
    for enemy in combat.get('enemies', []):
        if int(enemy.get('health') or 0) > 0:
            enemy['intent'] = _enemy_intent(state, enemy)


def _encounter_specs(state, room_type, seed, category_override=None):
    biome = str(state.get('biome') or 'garden')
    groups = STORY_ENCOUNTERS.get(biome) or STORY_ENCOUNTERS['garden']
    if category_override:
        category = str(category_override)
    elif room_type == 'boss':
        category = 'boss'
    elif room_type == 'elite':
        category = 'elite'
    elif int(state.get('stage_normal_battles') or 0) < 3:
        category = 'simple'
    else:
        category = 'hard'
    pool = list(groups.get(category) or ())
    if not pool:
        _fail('EMPTY_ENCOUNTER_POOL', '当前区域没有可用的战斗配置')
    rng = _rng(state, seed, f'encounter:{category}')
    if category == 'elite':
        history = state.setdefault('encounter_history', {}).setdefault('elite', {})
        seen = {
            int(item) for item in history.get(biome, [])
            if isinstance(item, int) or str(item).isdigit()
        }
        available = [index for index in range(len(pool)) if index not in seen]
        if not available:
            seen.clear()
            available = list(range(len(pool)))
        selected_index = rng.choice(available)
        seen.add(selected_index)
        history[biome] = sorted(seen)
        encounter = pool[selected_index]
    else:
        encounter = rng.choice(pool)
    return [spec if isinstance(spec, dict) else {'def_id': spec} for spec in encounter]


def _initialize_mechanical_track(state, enemy, events):
    if isinstance(enemy.get('mechanical_track'), list):
        return
    track = []
    for card_id in ('mjolnir', 'cogwheel', 'bone'):
        card = _new_card(state, card_id)
        card['track_persistent'] = True
        track.append(card)
    enemy['mechanical_track'] = track
    events.append({
        'type': 'mechanical_track_initialized',
        'enemy_id': enemy['id'],
        'card_ids': [card['def_id'] for card in track],
    })


def _resolve_enemy_entrance(state, enemy, events):
    script = STORY_ENEMIES.get(enemy.get('def_id'), {}).get('script')
    if script == 'mechanical_flower':
        _initialize_mechanical_track(state, enemy, events)
    obstacle = max(0, int(enemy.get('obstacle') or 0))
    if obstacle:
        _apply_status(
            state,
            state['combat'],
            'blockade',
            obstacle,
            events,
            source=enemy.get('def_id'),
        )


def _machine_learning_turn_start(state, seed, events):
    combat = state.get('combat') or {}
    flowers = _mechanical_flowers(combat)
    if not flowers:
        return
    hand = list(combat.get('hand') or ())
    if not hand:
        return
    selected = _rng(state, seed, 'machine_learning_hand').sample(
        hand,
        min(2, len(hand)),
    )
    for card in selected:
        _apply_machine_learning_void(
            state,
            card,
            events,
            'machine_learning_turn_start',
        )


def _start_combat(state, node, seed, events, encounter_override=None):
    specs = encounter_override or _encounter_specs(state, node['type'], seed)
    draw_pile = copy.deepcopy(state['player']['deck'])
    if _has_relic(state, 'steady'):
        primary_bonus = _relic_amount(state, 'steady')
        for card in draw_pile:
            if STORY_CARDS[card['def_id']].get('rarity') == 'primary':
                card.setdefault('modifiers', {})['primary_bonus'] = primary_bonus
    _rng(state, seed, 'combat_start').shuffle(draw_pile)
    enemies = []
    for index, spec in enumerate(specs):
        enemies.append(_build_enemy(state, spec['def_id'], index + 1, spec))
    health_multiplier = max(1, int(node.get('enemy_health_multiplier') or 1))
    if health_multiplier > 1:
        for enemy in enemies:
            enemy['max_health'] = max(1, int(enemy['max_health']) * health_multiplier)
            enemy['health'] = int(enemy['max_health'])
    state['combat'] = {
        'round': 1,
        'turn': 'player',
        'turn_kind': 'normal',
        'reward_room_type': str(node.get('type') or 'combat'),
        'elixir': int(state['player']['max_elixir']),
        'magic': int(state['player']['magic']),
        'shield': 0,
        'power': 0,
        'temporary_power': 0,
        'endurance': 0,
        'weak': 0,
        'vulnerable': 0,
        'fragile': 0,
        'poison': 0,
        'evade': 0,
        'stun': 0,
        'sturdy': 0,
        'broken': 0,
        'blind': 0,
        'blockade': 0,
        'attack_blocked': 0,
        'blind_active': False,
        'draw_pile': draw_pile,
        'hand': [],
        'discard_pile': [],
        'exile_pile': [],
        'equipment': [],
        'enemies': enemies,
        'cards_played_this_turn': 0,
        'cards_drawn_this_combat': 0,
        'active_discards_this_turn': 0,
        'active_discards_this_combat': 0,
        'card_play_limit': None,
        'next_attack_multiplier': 1,
        'next_skill_repeats': 0,
        'salt_multipliers': [],
        'delayed_copies': [],
        'starting_health': int(state['player']['health']),
        'damage_taken': 0,
        'first_damage_taken': False,
        'blade_used': False,
        'opening_redraw_pending': _has_relic(state, 'cooldown'),
        'delayed_hand_charge': 0,
        'delayed_player_statuses': [],
        'next_turn_draw_delta': 0,
        'sewage_active': False,
        'draw_phase_complete': False,
    }
    state['phase'] = 'combat'
    combat = state['combat']
    for enemy in enemies:
        _resolve_enemy_entrance(state, enemy, events)
    if any(enemy.get('def_id') == 'termite_mound' for enemy in enemies):
        for enemy in enemies:
            if int(enemy.get('psionic_connection') or 0) <= 0:
                continue
            enemy['psionic_connection'] = 0
            enemy['psionic_sustain'] = 1
    for enemy in enemies:
        if enemy.get('def_id') == 'reconstructor_enemy':
            enemy['move_index'] = _rng(
                state,
                seed,
                f'reconstructor_start:{enemy["id"]}',
            ).randrange(3)
    combat['elixir'] = _turn_elixir_baseline(state, combat)
    if _has_relic(state, 'easy_godhood'):
        combat['elixir'] += _relic_amount(state, 'easy_godhood')
    if _has_relic(state, 'first_strike'):
        combat['elixir'] += int(STORY_RELICS['first_strike']['amount'])
    if _has_relic(state, 'ruthless'):
        combat['power'] += _relic_amount(state, 'ruthless')
    if _has_relic(state, 'firm_defense'):
        combat['endurance'] += _relic_amount(state, 'firm_defense')
    if _has_relic(state, 'dizzy_relic'):
        _apply_status(state, combat, 'blind', 1, events, source='dizzy_relic')
    if _has_relic(state, 'uranium'):
        _apply_status(state, combat, 'poison', 4, events, source='uranium')
        _player_raw_damage(state, int(combat['poison']), events, 'poison')
        combat['poison'] = math.floor(int(combat['poison']) / 2)
    if _has_relic(state, 'pollen_relic'):
        _apply_status(state, combat, 'broken', 1, events, source='pollen_relic')
    if _has_relic(state, 'easy_peace'):
        _heal_player(
            state,
            _relic_amount(state, 'easy_peace'),
            events,
            source='easy_peace',
        )
    _activate_player_blind(combat, events)
    for enemy in enemies:
        if _has_relic(state, 'opening_lightning'):
            event_offset = len(events)
            _enemy_raw_damage(
                state,
                enemy,
                _relic_amount(state, 'opening_lightning'),
                events,
                'opening_lightning',
                player_caused=True,
            )
            for event in events[event_offset:]:
                if event.get('type') == 'enemy_damage':
                    event['parallel_group'] = 'opening_lightning'
    draw_count = int(STORY_RULES['draw_per_turn']) + int(state['player'].get('opening_draw_bonus') or 0)
    if _has_relic(state, 'prepared'):
        draw_count += _relic_amount(state, 'prepared')
    if _has_relic(state, 'first_strike'):
        draw_count += int(STORY_RELICS['first_strike']['amount'])
    if _has_relic(state, 'grab_every_card'):
        draw_count += 1
    if _has_relic(state, 'support'):
        draw_count -= 1
    if _has_relic(state, 'easy_tiger'):
        draw_count += _relic_amount(state, 'easy_tiger')
    if _has_relic(state, 'dandelion_blessing'):
        _gain_shield(
            state,
            int(STORY_RELICS['dandelion_blessing']['amount']),
            events,
        )
    _machine_learning_turn_start(state, seed, events)
    _draw_cards(state, draw_count, seed, events)
    combat['draw_phase_complete'] = True
    _refresh_combat_projections(state)
    events.append({'type': 'combat_start', 'enemy_ids': [enemy['def_id'] for enemy in enemies]})


def _next_enemy_move(state, enemy):
    definition = STORY_ENEMIES[enemy['def_id']]
    moves = definition['moves']
    if definition.get('script') == 'mechanical_rat':
        return moves[0 if int(enemy.get('hidden') or 0) > 0 else 1]
    forced_move_index = enemy.get('forced_move_index')
    if forced_move_index is not None:
        return moves[int(forced_move_index) % len(moves)]
    if definition.get('script') == 'shiny_ladybug' and enemy.get('yggdrasil_enraged'):
        return moves[2]
    if definition.get('script') == 'worm' and enemy.get('worm_digest_pending'):
        return moves[3]
    order = (
        definition.get('lunatic_move_order')
        if _difficulty(state) == 'lunatic'
        else definition.get('move_order')
    ) or definition.get('move_order')
    if order:
        step = max(0, int(enemy.get('move_step') or 0))
        move_index = int(order[step % len(order)]) % len(moves)
    else:
        move_index = int(enemy.get('move_index') or 0) % len(moves)
    if definition.get('script') == 'worker_ant' and len(_living_enemies(state['combat'])) <= 1:
        move_index = 2
    elif definition.get('script') == 'worker_ant':
        move_index %= 2
    if definition.get('script') == 'garden_rock' and move_index > 0:
        move_index = 1
    if definition.get('script') == 'ant_queen':
        ant_ids = {'soldier_ant', 'young_ant', 'worker_ant', 'ant_queen'}
        ant_count = sum(
            1 for item in _living_enemies(state['combat'])
            if item['def_id'] in ant_ids
        )
        if (
            int(enemy['health']) < math.ceil(int(enemy['max_health']) * 0.4)
            and not enemy.get('nourished')
        ):
            move_index = 3
        elif move_index == 2 and (enemy.get('nourished') or ant_count >= 4):
            move_index = 0
    elif definition.get('script') == 'hive' and move_index == 2 and int(enemy.get('frenzy') or 0) >= 2:
        move_index = 0
    elif definition.get('script') == 'fossil':
        move_index = 1 if (
            enemy.get('fossil_awaken_pending')
            or int(enemy.get('fossil_slumbers') or 0) >= 3
        ) else 0
    elif definition.get('script') == 'starfish':
        threshold = math.ceil(int(enemy.get('max_health') or 1) * 0.30)
        if (
            int(enemy.get('health') or 0) <= threshold
            and int(enemy.get('regenerations') or 0) > 0
            and int(enemy.get('starfish_last_move') or -1) != 2
        ):
            move_index = 2
    elif definition.get('script') == 'desert_centipede' and len(_living_enemies(state['combat'])) <= 1:
        move_index = 3
    elif definition.get('script') == 'termite_worker':
        move_index = 2 if len(_living_enemies(state['combat'])) <= 1 else move_index % 2
    elif definition.get('script') == 'jungle_fly':
        move_index = 0 if len(_living_enemies(state['combat'])) > 1 else 1
    elif definition.get('script') == 'pumpkin':
        move_index = 0 if int(enemy.get('shield') or 0) > 0 else 1
    elif definition.get('script') == 'spider_cave':
        move_index = 0 if int(enemy.get('shield') or 0) > 0 else 1
    elif definition.get('script') == 'stickbug':
        living_sticks = sum(
            item.get('def_id') == 'stick'
            for item in _living_enemies(state['combat'])
        )
        if not enemy.get('sticks_launched') or (
            int(enemy.get('move_index') or 0) == 2 and living_sticks < 2
        ):
            move_index = 0
    elif definition.get('script') == 'evil_centipede':
        lost_segments = max(
            0,
            int(enemy.get('segment_origin') or 0) - int(enemy.get('segments') or 0),
        )
        move_index = min(2, lost_segments)
    elif definition.get('script') == 'uranium_barrel':
        has_ally = len(_living_enemies(state['combat'])) > 1
        move_index = 1 if has_ally and int(enemy.get('last_move_index') or -1) != 1 else 0
    elif definition.get('script') == 'reconstructor_enemy':
        if int(enemy.get('fragment') or 0) >= 5:
            move_index = 4
        elif (
            enemy.get('missed_factory_waste_last_turn')
            and int(enemy.get('last_move_index') or -1) != 3
        ):
            move_index = 3
        else:
            move_index = min(2, int(enemy.get('move_index') or 0))
    elif definition.get('script') == 'mechanical_wasp':
        missiles = [
            item for item in _living_enemies(state['combat'])
            if item.get('def_id') == 'mechanical_missile'
        ]
        if not enemy.get('missile_summoned'):
            move_index = 0
        elif not missiles:
            move_index = 3
        elif int(missiles[0].get('health') or 0) * 2 > int(missiles[0].get('max_health') or 1):
            move_index = 1
        else:
            move_index = 2
    elif definition.get('script') == 'mechanical_missile':
        move_index = 0 if any(
            item.get('def_id') == 'mechanical_wasp'
            for item in _living_enemies(state['combat'])
        ) else 1
    return moves[move_index]


def _advance_enemy_move(state, enemy, move_index, seed):
    definition = STORY_ENEMIES[enemy['def_id']]
    moves = definition['moves']
    script = definition.get('script')
    if enemy.pop('forced_move_index', None) is not None:
        enemy['move_index'] = 0
        enemy['move_step'] = 0
        return
    if script == 'shiny_ladybug' and enemy.get('yggdrasil_enraged'):
        enemy['move_index'] = 2
        return
    if script == 'worm' and move_index == 3:
        enemy['worm_digest_pending'] = False
        enemy['move_index'] = 0
        enemy['move_step'] = 0
        return
    if script == 'fossil':
        if move_index == 0:
            enemy['fossil_slumbers'] = int(enemy.get('fossil_slumbers') or 0) + 1
        else:
            enemy['fossil_slumbers'] = 0
            enemy['fossil_awaken_pending'] = False
        return
    if script == 'starfish' and move_index == 2:
        enemy['regenerations'] = max(0, int(enemy.get('regenerations') or 0) - 1)
        enemy['starfish_last_move'] = move_index
        return
    if script == 'starfish':
        enemy['starfish_last_move'] = move_index
    if script == 'garden_rock':
        enemy['move_index'] = 1
        return
    if script == 'worker_ant':
        enemy['move_index'] = 2 if len(_living_enemies(state['combat'])) <= 1 else (move_index + 1) % 2
        return
    if script == 'termite_worker':
        enemy['move_index'] = 2 if len(_living_enemies(state['combat'])) <= 1 else (move_index + 1) % 2
        return
    if script == 'mechanical_crab':
        enemy['super_beam'] = 4 if move_index == 3 else max(
            1,
            int(enemy.get('super_beam') or 4) - 1,
        )
        enemy['move_step'] = int(enemy.get('move_step') or 0) + 1
        return
    if script in ('jungle_fly', 'pumpkin', 'evil_centipede', 'uranium_barrel', 'mechanical_missile'):
        enemy['last_move_index'] = move_index
        return
    if script == 'stickbug':
        enemy['sticks_launched'] = True
        enemy['move_index'] = 1 if move_index == 0 else (2 if move_index == 1 else 1)
        return
    if script == 'reconstructor_enemy':
        enemy['last_move_index'] = move_index
        enemy['move_index'] = _rng(
            state,
            seed,
            f'reconstructor_move:{enemy["id"]}',
        ).randrange(3)
        return
    if script == 'mechanical_wasp':
        if move_index == 0:
            enemy['missile_summoned'] = True
        return
    if script == 'ant_queen' and move_index == 3:
        return
    if script == 'random_intent':
        choices = [index for index in range(len(moves)) if index != move_index]
        if choices:
            enemy['move_index'] = _rng(state, seed, f'enemy_move:{enemy["id"]}').choice(choices)
        return
    order = (
        definition.get('lunatic_move_order')
        if _difficulty(state) == 'lunatic'
        else definition.get('move_order')
    ) or definition.get('move_order')
    if order:
        step = int(enemy.get('move_step') or 0) + 1
        if script == 'hive' and int(enemy.get('frenzy') or 0) >= 2:
            while int(order[step % len(order)]) == 2:
                step += 1
        enemy['move_step'] = step
        return
    enemy['move_index'] = (move_index + 1) % len(moves)


def _summon_enemy(
    state,
    enemy_id,
    events,
    move_index=0,
    wither=0,
    actor_id=None,
    source_definition_id=None,
    **initial,
):
    combat = state['combat']
    serial = int(combat.get('next_enemy_serial') or (len(combat['enemies']) + 1))
    combat['next_enemy_serial'] = serial + 1
    spec = {'move_index': int(move_index), 'wither': int(wither), **initial}
    enemy = _build_enemy(state, enemy_id, serial, spec)
    combat['enemies'].append(enemy)
    events.append({
        'type': 'enemy_summoned',
        'enemy_id': enemy['id'],
        'def_id': enemy_id,
        'enemy': copy.deepcopy(enemy),
        'actor_id': actor_id,
        'target_id': enemy['id'],
        'source_definition_id': source_definition_id,
    })
    _resolve_enemy_entrance(state, enemy, events)
    return enemy


def _resolve_enemy_effect(state, enemy, effect, move, seed, events):
    combat = state['combat']
    effect_type = effect['type']
    amount = _effect_amount(state, effect)
    if effect_type == 'damage':
        _player_damage(
            state,
            amount,
            _effect_hits(state, effect),
            events,
            _localized(move['name']),
            enemy,
        )
        if int(enemy.get('charging') or 0) > 0:
            before = int(enemy['charging'])
            enemy['charging'] = 0
            events.append({
                'type': 'status_cleared',
                'target_id': enemy['id'],
                'status': 'charging',
                'before': before,
                'source': 'attack',
            })
    elif effect_type == 'self_damage':
        _enemy_raw_damage(state, enemy, amount, events, 'self_damage')
    elif effect_type == 'gain_power':
        before = int(enemy.get('power') or 0)
        enemy['power'] = before + amount
        events.append({
            'type': 'enemy_gain',
            'enemy_id': enemy['id'],
            'effect_kind': 'power',
            'amount': amount,
            'before': before,
            'after': int(enemy['power']),
        })
    elif effect_type == 'gain_shield':
        _gain_shield(state, amount, events, source='enemy', enemy=enemy)
    elif effect_type == 'gain_status':
        _apply_status(state, enemy, effect.get('status'), amount, events, source='enemy')
    elif effect_type == 'allies_status':
        for ally in _living_enemies(combat):
            _apply_status(
                state,
                ally,
                str(effect.get('status') or ''),
                amount,
                events,
                source=enemy['def_id'],
            )
    elif effect_type == 'clear_status':
        status = str(effect.get('status') or '')
        before = int(enemy.get(status) or 0)
        enemy[status] = 0
        if before:
            events.append({
                'type': 'status_cleared',
                'target_id': enemy['id'],
                'status': status,
                'before': before,
                'source': enemy['def_id'],
            })
    elif effect_type in {
        'gain_charged', 'gain_charging', 'gain_frenzy', 'gain_hidden',
        'gain_sturdy',
    }:
        status = {
            'gain_charged': 'charged',
            'gain_charging': 'charging',
            'gain_frenzy': 'frenzy',
            'gain_hidden': 'hidden',
            'gain_sturdy': 'sturdy',
        }[effect_type]
        _apply_status(state, enemy, status, amount, events, source=enemy['def_id'])
    elif effect_type == 'player_status':
        _apply_status(state, combat, effect.get('status'), amount, events, source=enemy['def_id'])
    elif effect_type == 'allies_power':
        for ally in _living_enemies(combat):
            before = int(ally.get('power') or 0)
            ally['power'] = before + amount
            events.append({
                'type': 'enemy_gain',
                'enemy_id': ally['id'],
                'effect_kind': 'power',
                'amount': amount,
                'before': before,
                'after': int(ally['power']),
            })
    elif effect_type == 'allies_shield':
        for ally in _living_enemies(combat):
            _gain_shield(state, amount, events, source='enemy', enemy=ally)
    elif effect_type == 'allies_heal':
        for ally in _living_enemies(combat):
            before = int(ally['health'])
            ally['health'] = min(int(ally['max_health']), before + amount)
            events.append({
                'type': 'enemy_heal',
                'enemy_id': ally['id'],
                'amount': int(ally['health']) - before,
                'before': before,
                'after': int(ally['health']),
            })
    elif effect_type == 'lowest_ally_shield':
        living = _living_enemies(combat)
        if living:
            ally = min(living, key=lambda item: (int(item['health']), item['id']))
            _gain_shield(state, amount, events, source='enemy', enemy=ally)
    elif effect_type == 'named_allies_power':
        for ally in _living_enemies(combat):
            if ally.get('def_id') != effect.get('enemy_id'):
                continue
            before = int(ally.get('power') or 0)
            ally['power'] = before + amount
            events.append({
                'type': 'enemy_gain',
                'enemy_id': ally['id'],
                'effect_kind': 'power',
                'amount': amount,
                'before': before,
                'after': int(ally['power']),
                'source': enemy['def_id'],
            })
    elif effect_type == 'heal_named_ally_percent':
        for ally in _living_enemies(combat):
            if ally.get('def_id') != effect.get('enemy_id'):
                continue
            before = int(ally.get('health') or 0)
            healing = math.ceil(int(ally.get('max_health') or 1) * amount / 100)
            ally['health'] = min(int(ally.get('max_health') or 1), before + healing)
            events.append({
                'type': 'enemy_heal',
                'enemy_id': ally['id'],
                'amount': int(ally['health']) - before,
                'before': before,
                'after': int(ally['health']),
                'source': enemy['def_id'],
            })
    elif effect_type == 'adjacent_shield':
        index = combat['enemies'].index(enemy)
        for ally_index in (index - 1, index, index + 1):
            if 0 <= ally_index < len(combat['enemies']):
                ally = combat['enemies'][ally_index]
                if int(ally.get('health') or 0) > 0:
                    _gain_shield(state, amount, events, source='enemy', enemy=ally)
    elif effect_type == 'add_draw_card':
        created_ids = []
        for _ in range(amount):
            card = _new_card(state, effect.get('card_id'))
            combat['draw_pile'].append(card)
            created_ids.append(card['instance_id'])
        _rng(state, seed, 'enemy_add_draw').shuffle(combat['draw_pile'])
        if created_ids:
            events.append({
                'type': 'enemy_card_added',
                'target_id': 'player',
                'card_id': effect.get('card_id'),
                'card_instance_ids': created_ids,
                'count': len(created_ids),
                'destination': 'draw_pile',
            })
    elif effect_type == 'self_heal':
        before = int(enemy['health'])
        enemy['health'] = min(int(enemy['max_health']), before + amount)
        events.append({
            'type': 'enemy_heal',
            'enemy_id': enemy['id'],
            'amount': int(enemy['health']) - before,
            'before': before,
            'after': int(enemy['health']),
        })
    elif effect_type == 'damage_from_shield':
        divisor = max(1, int(effect.get('divisor') or 1))
        _player_damage(
            state,
            amount + math.floor(int(enemy.get('shield') or 0) / divisor),
            1,
            events,
            _localized(move['name']),
            enemy,
        )
    elif effect_type == 'damage_from_player_status':
        _player_damage(
            state,
            amount + max(0, int(combat.get(str(effect.get('status') or '')) or 0)),
            1,
            events,
            _localized(move['name']),
            enemy,
        )
    elif effect_type == 'consume_status_damage':
        status = str(effect.get('status') or '')
        before = max(0, int(enemy.get(status) or 0))
        divisor_key = 'lunatic_divisor' if _difficulty(state) == 'lunatic' else 'divisor'
        divisor = max(1, int(effect.get(divisor_key) or effect.get('divisor') or 1))
        enemy[status] = 0
        if before:
            events.append({
                'type': 'status_cleared',
                'target_id': enemy['id'],
                'status': status,
                'before': before,
                'source': enemy['def_id'],
            })
        _player_damage(
            state,
            math.floor(before / divisor),
            1,
            events,
            _localized(move['name']),
            enemy,
        )
    elif effect_type == 'consume_status':
        status = str(effect.get('status') or '')
        before = max(0, int(enemy.get(status) or 0))
        enemy[status] = max(0, before - amount)
        events.append({
            'type': 'status_decay',
            'target_id': enemy['id'],
            'status': status,
            'before': before,
            'after': int(enemy[status]),
            'source': enemy['def_id'],
        })
    elif effect_type == 'gain_magic':
        before = max(0, int(enemy.get('magic') or 0))
        enemy['magic'] = before + amount
        events.append({
            'type': 'enemy_gain',
            'enemy_id': enemy['id'],
            'effect_kind': 'magic',
            'amount': amount,
            'before': before,
            'after': int(enemy['magic']),
            'source': enemy['def_id'],
        })
    elif effect_type == 'consume_magic_damage':
        before_magic = max(0, int(enemy.get('magic') or 0))
        enemy['magic'] = 0
        events.append({
            'type': 'enemy_gain',
            'enemy_id': enemy['id'],
            'effect_kind': 'magic',
            'amount': -before_magic,
            'before': before_magic,
            'after': 0,
            'source': enemy['def_id'],
        })
        _player_damage(
            state,
            amount + before_magic * max(0, int(effect.get('multiplier') or 0)),
            1,
            events,
            _localized(move['name']),
            enemy,
        )
    elif effect_type == 'disable_magic_shield':
        enemy['magic_shield_disabled'] = max(
            int(enemy.get('magic_shield_disabled') or 0),
            amount,
        )
        events.append({
            'type': 'status',
            'target_id': enemy['id'],
            'status': 'magic_shield_disabled',
            'amount': amount,
            'source': enemy['def_id'],
        })
    elif effect_type == 'summon':
        for _ in range(amount):
            frenzy = (
                max(0, int(enemy.get('frenzy') or 0))
                if enemy.get('def_id') == 'hive'
                else 0
            )
            summon_initial = {}
            if enemy.get('def_id') == 'hive':
                summon_initial = {
                    'shield': 20 if frenzy >= 1 else 0,
                    'power': 10 if frenzy >= 2 else 0,
                }
            health_percent = max(0, int(effect.get('health_percent') or 0))
            if health_percent:
                summon_definition = STORY_ENEMIES.get(effect.get('enemy_id')) or {}
                summon_initial['health'] = max(
                    1,
                    math.ceil(
                        _enemy_base_health(state, summon_definition)
                        * health_percent
                        / 100
                    ),
                )
            _summon_enemy(
                state,
                effect.get('enemy_id'),
                events,
                effect.get('move_index', 0),
                effect.get('wither', 0),
                actor_id=enemy['id'],
                source_definition_id=enemy['def_id'],
                **summon_initial,
            )
    elif effect_type == 'summon_to_ant_count':
        ant_ids = {'soldier_ant', 'young_ant', 'worker_ant', 'ant_queen'}
        count = sum(1 for item in _living_enemies(combat) if item['def_id'] in ant_ids)
        for _ in range(max(0, amount - count)):
            _summon_enemy(
                state,
                effect.get('enemy_id'),
                events,
                actor_id=enemy['id'],
                source_definition_id=enemy['def_id'],
            )
    elif effect_type == 'consume_allies':
        victims = [item for item in _living_enemies(combat) if item is not enemy]
        power_per_victim = max(1, amount)
        for victim in victims:
            victim_health_before = int(victim['health'])
            victim['health'] = 0
            enemy['power'] = int(enemy.get('power') or 0) + power_per_victim
            before = int(enemy['health'])
            enemy['health'] = min(int(enemy['max_health']), before + int(victim['max_health']))
            events.append({
                'type': 'enemy_consumed',
                'enemy_id': enemy['id'],
                'victim_id': victim['id'],
                'victim_health_before': victim_health_before,
                'before': before,
                'after': int(enemy['health']),
            })
        enemy['nourished'] = True
    elif effect_type == 'delayed_hand_charge':
        combat['delayed_hand_charge'] = int(combat.get('delayed_hand_charge') or 0) + amount
        events.append({'type': 'effect_delayed', 'effect_kind': 'hand_charge', 'amount': amount})
    elif effect_type == 'all_cards_charge':
        charged_ids = []
        for pile_name in (
            'hand', 'draw_pile', 'discard_pile', 'exile_pile', 'equipment',
        ):
            for card in combat.get(pile_name, []):
                modifiers = card.setdefault('modifiers', {})
                modifiers['charge'] = max(0, int(modifiers.get('charge') or 0)) + amount
                charged_ids.append(card['instance_id'])
        events.append({
            'type': 'all_cards_charged',
            'amount': amount,
            'card_instance_ids': charged_ids,
            'source': enemy['def_id'],
        })
    elif effect_type == 'halve_player_status':
        status = str(effect.get('status') or '')
        before = max(0, int(combat.get(status) or 0))
        combat[status] = math.floor(before / 2)
        events.append({
            'type': 'status_decay',
            'target_id': 'player',
            'status': status,
            'before': before,
            'after': int(combat[status]),
            'source': enemy['def_id'],
        })
    elif effect_type == 'delayed_player_status':
        combat.setdefault('delayed_player_statuses', []).append({
            'status': str(effect.get('status') or ''),
            'amount': amount,
        })
        events.append({
            'type': 'effect_delayed',
            'effect_kind': 'player_status',
            'status': str(effect.get('status') or ''),
            'amount': amount,
        })
    elif effect_type == 'heal_to_full':
        before = int(enemy.get('health') or 0)
        enemy['health'] = int(enemy.get('max_health') or before)
        events.append({
            'type': 'enemy_heal',
            'enemy_id': enemy['id'],
            'amount': int(enemy['health']) - before,
            'before': before,
            'after': int(enemy['health']),
        })
    elif effect_type == 'lose_max_health_percent':
        before_max = int(enemy.get('max_health') or 1)
        after_max = max(1, math.floor(before_max * (100 - max(0, amount)) / 100))
        enemy['max_health'] = after_max
        enemy['health'] = min(int(enemy.get('health') or 0), after_max)
        events.append({
            'type': 'enemy_max_health',
            'enemy_id': enemy['id'],
            'amount': after_max - before_max,
            'before': before_max,
            'after': after_max,
        })
    elif effect_type == 'stun_if_player_shield':
        if int(combat.get('shield') or 0) > 0:
            _apply_status(state, combat, 'stun', 1, events, source=enemy['def_id'])
            enemy['worm_digest_pending'] = True
    elif effect_type == 'consume_pearls_damage':
        pearls = [
            item for item in _living_enemies(combat)
            if item.get('def_id') == 'ocean_pearl'
        ]
        for pearl in pearls:
            victim_health_before = int(pearl.get('health') or 0)
            pearl['health'] = 0
            pearl['death_reason'] = 'consumed'
            events.append({
                'type': 'enemy_consumed',
                'enemy_id': enemy['id'],
                'victim_id': pearl['id'],
                'victim_health_before': victim_health_before,
            })
            _player_damage(state, amount, 1, events, _localized(move['name']), enemy)
    elif effect_type == 'summon_wreckage':
        summon_ids = ('crab', 'lily_pad', 'urchin')
        for index in range(max(0, amount)):
            _summon_enemy(
                state,
                'wreckage',
                events,
                actor_id=enemy['id'],
                source_definition_id=enemy['def_id'],
                death_summon=summon_ids[index % len(summon_ids)],
            )
    elif effect_type == 'self_kill':
        enemy['death_reason'] = str(effect.get('reason') or 'self_kill')
        if effect.get('trigger_survival'):
            before = max(1, int(enemy.get('health') or 1))
            _apply_enemy_lethal_rules(state, enemy, before, before, events)
            if int(enemy.get('health') or 0) > 0:
                return
        enemy['health'] = 0
        events.append({
            'type': 'enemy_self_destruct',
            'enemy_id': enemy['id'],
            'reason': enemy['death_reason'],
        })


def _enemy_move_target_ids(combat, enemy, move):
    targets = []
    effect_types = {
        str(effect.get('type') or '')
        for effect in move.get('effects') or ()
    }
    if effect_types.intersection({
        'damage', 'player_status', 'add_draw_card', 'delayed_hand_charge',
        'delayed_player_status', 'stun_if_player_shield',
        'consume_pearls_damage', 'damage_from_shield',
        'damage_from_player_status', 'consume_status_damage',
        'consume_magic_damage', 'all_cards_charge', 'halve_player_status',
    }):
        targets.append('player')
    if effect_types.intersection({
        'self_damage',
        'gain_power',
        'gain_shield',
        'gain_status',
        'self_heal',
        'consume_allies',
        'clear_status',
        'gain_charged',
        'gain_charging',
        'gain_frenzy',
        'gain_hidden',
        'gain_sturdy',
        'heal_to_full',
        'lose_max_health_percent',
        'self_kill',
        'summon_wreckage',
        'gain_magic', 'consume_magic_damage', 'disable_magic_shield',
        'consume_status',
    }):
        targets.append(str(enemy['id']))
    if effect_types.intersection({
        'allies_power',
        'allies_shield',
        'allies_heal',
        'lowest_ally_shield',
        'adjacent_shield',
        'allies_status', 'named_allies_power', 'heal_named_ally_percent',
    }):
        targets.extend(str(ally['id']) for ally in _living_enemies(combat))
    return list(dict.fromkeys(targets))


def _prepare_enemy_turn_defenses(combat):
    """Expire defenses from the previous enemy turn before new actions resolve."""
    for enemy in combat['enemies']:
        if int(enemy.get('health') or 0) <= 0:
            continue
        sturdy = max(0, int(enemy.get('sturdy') or 0))
        if sturdy:
            enemy['sturdy'] = sturdy - 1
        else:
            enemy['shield'] = 0


_MECHANICAL_TRACK_DRAW_EFFECTS = frozenset({
    'draw', 'draw_attack_power', 'draw_selected', 'draw_target_status',
    'draw_then_discard', 'draw_to_limit', 'inspect_draw_choose',
    'swap_piles_draw',
})


def _mechanical_track_base_totals(card):
    values = _card_values(card)
    damage = 0
    shield = 0
    can_draw = False
    for effect in values.get('effects') or ():
        effect_type = str(effect.get('type') or '')
        amount = max(0, int(effect.get('amount') or 0))
        if effect_type in STORY_PLAYER_ATTACK_EFFECT_TYPES:
            damage += amount * max(1, int(effect.get('hits') or 1))
        elif effect_type in {
            'shield', 'decaying_shield', 'shield_with_power',
        }:
            shield += amount
        if effect_type in _MECHANICAL_TRACK_DRAW_EFFECTS:
            can_draw = True
    return damage, shield, can_draw


def _mechanical_track_draw_rotations(state, effect):
    effect_type = str(effect.get('type') or '')
    if effect_type not in _MECHANICAL_TRACK_DRAW_EFFECTS:
        return 0
    amount = max(0, int(effect.get('amount') or 0))
    if effect_type == 'draw_to_limit':
        amount = max(
            0,
            int(STORY_RULES['hand_limit'])
            - len(state['combat'].get('hand') or ()),
        )
    elif effect_type == 'draw_target_status':
        status = str(effect.get('status') or '')
        amount = max(0, int(state['combat'].get(status) or 0))
    return max(0, amount - 1)


def _mechanical_track_gain_power(enemy, amount, events, source):
    amount = int(amount)
    if not amount:
        return
    before = int(enemy.get('power') or 0)
    enemy['power'] = max(0, before + amount)
    events.append({
        'type': 'enemy_gain',
        'enemy_id': enemy['id'],
        'effect_kind': 'power',
        'amount': int(enemy['power']) - before,
        'before': before,
        'after': int(enemy['power']),
        'source': source,
    })


def _mechanical_track_attack_segment(state, enemy, effect):
    combat = state['combat']
    effect_type = str(effect.get('type') or '')
    amount = max(0, int(effect.get('amount') or 0))
    if effect_type == 'damage':
        return amount, max(1, int(effect.get('hits') or 1))
    if effect_type == 'damage_from_shield':
        return (
            int(enemy.get('shield') or 0) * amount
            + int(effect.get('bonus') or 0),
            1,
        )
    if effect_type == 'damage_per_status':
        return amount, max(0, int(effect.get('base_hits') or 0) + _status_count(combat))
    if effect_type == 'damage_per_active_discard':
        return amount + int(combat.get('active_discards_this_combat') or 0), 1
    if effect_type == 'damage_per_elixir':
        return amount, max(0, int(enemy.get('track_elixir') or 0))
    return None


def _resolve_mechanical_track_card(state, enemy, card, seed, events):
    values = _card_values(card)
    card_name = _localized(values.get('name'))
    repeats = 1
    if values.get('type') == 'bloom' and card.get('def_id') != 'fission':
        repeats += max(0, int(enemy.pop('track_skill_repeats', 0) or 0))
    extra_rotations = 0
    for _ in range(repeats):
        for effect in values.get('effects') or ():
            effect_type = str(effect.get('type') or '')
            rotations = _mechanical_track_draw_rotations(state, effect)
            if rotations:
                extra_rotations += rotations
                continue
            attack = _mechanical_track_attack_segment(state, enemy, effect)
            if attack is not None:
                amount, hits = attack
                multiplier = float(enemy.pop('track_attack_multiplier', 1) or 1)
                _player_damage(
                    state,
                    math.floor(amount * multiplier),
                    hits,
                    events,
                    card_name,
                    enemy,
                )
                continue
            amount = int(effect.get('amount') or 0)
            if effect_type in {'shield', 'decaying_shield'}:
                _gain_shield(state, amount, events, source=card['def_id'], enemy=enemy)
            elif effect_type == 'shield_with_power':
                _gain_shield(
                    state,
                    amount + int(enemy.get('power') or 0),
                    events,
                    source=card['def_id'],
                    enemy=enemy,
                )
            elif effect_type == 'shield_from_target_status':
                status = str(effect.get('status') or '')
                _gain_shield(
                    state,
                    max(0, int(state['combat'].get(status) or 0)) * amount,
                    events,
                    source=card['def_id'],
                    enemy=enemy,
                )
            elif effect_type == 'power':
                _mechanical_track_gain_power(enemy, amount, events, card['def_id'])
            elif effect_type == 'status':
                _apply_status(
                    state,
                    state['combat'],
                    str(effect.get('status') or ''),
                    amount,
                    events,
                    source=card['def_id'],
                )
            elif effect_type == 'status_self':
                _apply_status(
                    state,
                    enemy,
                    str(effect.get('status') or ''),
                    amount,
                    events,
                    source=card['def_id'],
                )
            elif effect_type == 'elixir':
                _mechanical_track_gain_power(enemy, amount, events, card['def_id'])
            elif effect_type == 'elixir_if_active_discard':
                if int(state['combat'].get('active_discards_this_turn') or 0) > 0:
                    _mechanical_track_gain_power(enemy, amount, events, card['def_id'])
            elif effect_type == 'lose_health':
                _enemy_raw_damage(state, enemy, amount, events, card['def_id'])
            elif effect_type == 'next_attack_multiplier':
                enemy['track_attack_multiplier'] = max(
                    float(enemy.get('track_attack_multiplier') or 1),
                    float(amount or 1),
                )
            elif effect_type == 'next_skill_repeats':
                enemy['track_skill_repeats'] = max(
                    int(enemy.get('track_skill_repeats') or 0),
                    amount,
                )
            elif effect_type == 'create_discard_copy':
                copied = _new_card(state, card['def_id'], bool(card.get('upgraded')))
                copied['track_persistent'] = False
                enemy.setdefault('mechanical_track', []).append(copied)
                events.append({
                    'type': 'mechanical_track_card_created',
                    'enemy_id': enemy['id'],
                    'card_instance_id': copied['instance_id'],
                    'def_id': copied['def_id'],
                })
    return extra_rotations


def _mechanical_flower_turn(state, enemy, seed, events):
    _initialize_mechanical_track(state, enemy, events)
    track = enemy.setdefault('mechanical_track', [])
    pending_rotations = 2
    resolved = 0
    while track and pending_rotations > 0 and resolved < 64:
        pending_rotations -= 1
        resolved += 1
        card = track.pop(0)
        values = _card_values(card)
        damage, shield, can_draw = _mechanical_track_base_totals(card)
        recycled = damage + shield < 10 and not can_draw
        events.append({
            'type': 'enemy_action',
            'enemy_id': enemy['id'],
            'move_index': 0,
            'actor_id': enemy['id'],
            'target_ids': ['player'],
            'source_definition_id': enemy['def_id'],
            'source_card_instance_id': card['instance_id'],
            'track_card': copy.deepcopy(card),
            'presentation': {'motion': 'gain' if recycled else 'attack'},
        })
        if recycled:
            _mechanical_track_gain_power(enemy, 1, events, 'recycling')
            pending_rotations += 1
            events.append({
                'type': 'mechanical_track_recycled',
                'enemy_id': enemy['id'],
                'card_instance_id': card['instance_id'],
                'def_id': card['def_id'],
            })
        else:
            pending_rotations += _resolve_mechanical_track_card(
                state,
                enemy,
                card,
                seed,
                events,
            )
            if card.get('track_persistent'):
                track.append(card)
        if int(state['player'].get('health') or 0) <= 0:
            break
    if pending_rotations > 0:
        events.append({
            'type': 'mechanical_track_limited',
            'enemy_id': enemy['id'],
            'remaining': pending_rotations,
        })


def _finish_enemy_turn_effects(state, enemy, seed, events):
    """Resolve effects that decay when this creature's own turn ends."""
    disc = max(0, int(enemy.get('disc') or 0))
    if disc:
        enemy['disc'] = disc - 1
        events.append({
            'type': 'status_decay',
            'target_id': enemy['id'],
            'status': 'disc',
            'before': disc,
            'after': int(enemy['disc']),
        })
    if STORY_ENEMIES.get(enemy.get('def_id'), {}).get('script') == 'mechanical_rat':
        covers = [
            item for item in _living_enemies(state['combat'])
            if STORY_ENEMIES.get(item.get('def_id'), {}).get('script')
            == 'broken_machine'
        ]
        if covers:
            cover = _rng(state, seed, f'mechanical_rat_cover:{enemy["id"]}').choice(covers)
            before = max(0, int(enemy.get('hidden') or 0))
            enemy['hidden'] = max(1, before)
            enemy['hidden_cover_id'] = cover['id']
            enemy['hidden_fresh'] = True
            events.append({
                'type': 'enemy_hidden_in_cover',
                'enemy_id': enemy['id'],
                'cover_enemy_id': cover['id'],
                'before': before,
                'after': int(enemy['hidden']),
            })


def _enemy_turn(state, seed, events):
    combat = state['combat']
    combat['turn'] = 'enemy'
    _prepare_enemy_turn_defenses(combat)
    action_order = list(combat['enemies'])
    for enemy in action_order:
        if int(enemy.get('health') or 0) <= 0:
            continue
        definition = STORY_ENEMIES[enemy['def_id']]
        if definition.get('script') == 'reconstructor_enemy':
            received_waste = bool(enemy.pop('received_factory_waste', False))
            turns_processed = max(0, int(enemy.get('reconstructor_turns_processed') or 0))
            has_previous_player_turn = turns_processed > 0 or int(combat.get('round') or 1) > 1
            enemy['missed_factory_waste_last_turn'] = bool(
                has_previous_player_turn and not received_waste
            )
            enemy['reconstructor_turns_processed'] = turns_processed + 1
            _put_in_hand(state, _new_card(state, 'factory_waste'), events)
        if definition.get('script') == 'garden_rock':
            rockfall = int(enemy.get('rockfall') or 0)
            if rockfall > 0:
                _player_damage(state, rockfall, 1, events, '落石', enemy)
            enemy['rockfall'] = rockfall + 2
            events.append({
                'type': 'enemy_gain',
                'enemy_id': enemy['id'],
                'effect_kind': 'rockfall',
                'amount': 2,
                'before': rockfall,
                'after': int(enemy['rockfall']),
            })
        if int(enemy.get('stun') or 0) > 0:
            enemy['stun'] = max(0, int(enemy['stun']) - 1)
            events.append({'type': 'enemy_skipped', 'enemy_id': enemy['id'], 'reason': 'stun'})
            if enemy.get('yggdrasil_revive_pending'):
                before = int(enemy.get('health') or 0)
                enemy['health'] = int(enemy.get('max_health') or 1)
                enemy['yggdrasil_revive_pending'] = False
                enemy['yggdrasil_enraged'] = True
                events.append({
                    'type': 'enemy_revived',
                    'enemy_id': enemy['id'],
                    'amount': int(enemy['health']) - before,
                    'before': before,
                    'after': int(enemy['health']),
                    'source': 'yggdrasil_power',
                })
            if (
                enemy.get('psionic_sustain_revive_pending')
                and int(enemy.get('stun') or 0) <= 0
                and any(
                    item.get('def_id') == 'termite_mound'
                    for item in _living_enemies(combat)
                )
            ):
                before = int(enemy.get('health') or 0)
                enemy['health'] = int(enemy.get('max_health') or 1)
                enemy['psionic_sustain_revive_pending'] = False
                events.append({
                    'type': 'enemy_revived',
                    'enemy_id': enemy['id'],
                    'amount': int(enemy['health']) - before,
                    'before': before,
                    'after': int(enemy['health']),
                    'source': 'psionic_sustain',
                })
                for ally in _living_enemies(combat):
                    ally_before = int(ally.get('power') or 0)
                    ally['power'] = ally_before + 1
                    events.append({
                        'type': 'enemy_gain',
                        'enemy_id': ally['id'],
                        'effect_kind': 'power',
                        'amount': 1,
                        'before': ally_before,
                        'after': int(ally['power']),
                        'source': 'nest_instinct',
                    })
            _finish_enemy_turn_effects(state, enemy, seed, events)
            if _check_combat_end(state, seed, events):
                return
            continue
        if definition.get('script') == 'broken_machine':
            _finish_enemy_turn_effects(state, enemy, seed, events)
            continue
        if definition.get('script') == 'mechanical_flower':
            _mechanical_flower_turn(state, enemy, seed, events)
            _finish_enemy_turn_effects(state, enemy, seed, events)
            if _check_combat_end(state, seed, events):
                return
            continue
        move = _next_enemy_move(state, enemy)
        move_index = definition['moves'].index(move)
        has_attack = any(
            effect.get('type') in {
                'damage', 'damage_from_shield', 'damage_from_player_status',
                'consume_status_damage', 'consume_magic_damage',
            }
            for effect in move.get('effects') or ()
        )
        events.append({
            'type': 'enemy_action',
            'enemy_id': enemy['id'],
            'move_index': move_index,
            'actor_id': enemy['id'],
            'target_ids': _enemy_move_target_ids(combat, enemy, move),
            'source_definition_id': enemy['def_id'],
            'presentation': {
                'motion': 'attack' if has_attack else 'gain',
            },
        })
        for effect_index, effect in enumerate(move['effects']):
            effect_event_start = len(events)
            _resolve_enemy_effect(state, enemy, effect, move, seed, events)
            effect_events = events[effect_event_start:]
            effect_target_ids = {
                target_id
                for event in effect_events
                for target_id in _story_event_target_ids(event)
            }
            group_prefix = (
                f'enemy:{enemy["id"]}:move:{move_index}:effect:{effect_index}'
            )
            for event in effect_events:
                event.setdefault('actor_id', enemy['id'])
                event.setdefault('source_definition_id', enemy['def_id'])
                event.setdefault('effect_index', effect_index)
                if len(effect_target_ids) > 1:
                    hit_index = max(0, int(event.get('hit_index') or 0))
                    event.setdefault(
                        'parallel_group',
                        f'{group_prefix}:hit:{hit_index}' if hit_index else group_prefix,
                    )
        _advance_enemy_move(state, enemy, move_index, seed)
        _finish_enemy_turn_effects(state, enemy, seed, events)
        if (
            definition.get('script') == 'bandage_beetle'
            and enemy.pop('bandage_invincible_pending', False)
        ):
            enemy['invincible'] = 0
        if definition.get('script') == 'shiny_ladybug' and enemy.get('yggdrasil_enraged'):
            enemy['invincible'] = 0
        if _check_combat_end(state, seed, events):
            return
    _check_combat_end(state, seed, events)
    if state.get('phase') != 'combat':
        return
    _turn_boundary(state, seed, events)


def _discard_hand_at_turn_end(state, seed, events):
    combat = state['combat']
    retained = []
    for card in list(combat['hand']):
        values = _card_values(card)
        tags = _card_tags(values)
        modifiers = card.get('modifiers') or {}
        script = values.get('script')
        if script == 'startled':
            _apply_status(state, combat, 'vulnerable', 1, events, source='startled')
        elif script == 'unrelenting':
            _apply_status(state, combat, 'weak', 1, events, source='unrelenting')
        elif script == 'factory_waste':
            _player_raw_damage(state, 8, events, 'factory_waste')
        if 'void' in tags or modifiers.get('force_void'):
            combat['exile_pile'].append(card)
            _notify_exiled(state, card, events, seed)
        elif 'retain' in tags or modifiers.get('retain'):
            retained.append(card)
        else:
            combat['discard_pile'].append(card)
    combat['hand'] = retained


def _clear_temporary_card_modifiers(combat):
    for pile_name in ('hand', 'draw_pile', 'discard_pile', 'exile_pile'):
        for card in combat.get(pile_name, []):
            modifiers = card.get('modifiers')
            if not isinstance(modifiers, dict):
                continue
            if modifiers.pop('temporary_cost', None):
                modifiers.pop('cost_e_delta', None)
            modifiers.pop('temporary_free_e', None)
            if not modifiers:
                card.pop('modifiers', None)


def _run_turn_start_equipment(state, seed, events):
    combat = state['combat']
    for equipment, effect in list(_equipment_effects(combat)):
        script = effect.get('script')
        amount = int(effect.get('amount') or 0)
        if script == 'start_shield':
            _gain_shield(state, amount, events)
        elif script == 'start_power':
            combat['power'] = int(combat.get('power') or 0) + amount
        elif script == 'turn_elixir':
            _gain_elixir(state, amount, events)
        elif script == 'support':
            _gain_shield(state, amount, events)
        elif script == 'start_random_bloom':
            pool = [
                card_id for card_id, definition in STORY_CARDS.items()
                if definition.get('type') == 'bloom'
                and definition.get('rarity') in ('primary', 'common', 'rare', 'ultra', 'super')
                and 'unplayable' not in set(definition.get('tags') or ())
            ]
            if pool:
                card_id = _rng(state, seed, 'magic_assembler_bloom').choice(pool)
                generated = _new_card(
                    state,
                    card_id,
                    bool(effect.get('upgraded') and STORY_CARDS[card_id].get('upgrade')),
                )
                _put_in_hand(state, generated, events)
                events.append({
                    'type': 'equipment_triggered',
                    'card_instance_id': equipment.get('instance_id'),
                    'def_id': equipment.get('def_id'),
                    'generated_def_id': card_id,
                })


def _activate_player_blind(combat, events):
    stacks = max(0, int(combat.get('blind') or 0))
    combat['blind_active'] = stacks > 0
    if not stacks:
        return
    combat['blind'] = stacks - 1
    events.append({
        'type': 'status_decay',
        'target_id': 'player',
        'status': 'blind',
        'before': stacks,
        'after': int(combat['blind']),
    })


def _turn_boundary(state, seed, events, extra=False):
    combat = state['combat']
    combat['blind_active'] = False
    combat['temporary_power'] = 0
    combat['disc_active'] = False
    combat['cannot_draw'] = False
    combat['next_attack_multiplier'] = 1
    combat['next_skill_repeats'] = 0
    _clear_temporary_card_modifiers(combat)
    combat['sewage_active'] = False
    for status in _TURN_START_DECAY_STATUSES:
        combat[status] = max(0, int(combat.get(status) or 0) - 1)
    if not extra:
        if _has_relic(state, 'dizzy_relic'):
            _apply_status(state, combat, 'blind', 1, events, source='dizzy_relic')
        if _has_relic(state, 'uranium'):
            _apply_status(state, combat, 'poison', 4, events, source='uranium')
        if _has_relic(state, 'pollen_relic'):
            _apply_status(state, combat, 'broken', 1, events, source='pollen_relic')
        if _has_relic(state, 'cognitive_bias'):
            combat['cognitive_bias_loss'] = int(combat.get('cognitive_bias_loss') or 0) + 1
    for enemy in combat['enemies']:
        enemy['temporary_power'] = 0
        for status in _TURN_START_DECAY_STATUSES:
            enemy[status] = max(0, int(enemy.get(status) or 0) - 1)
        if int(enemy.get('wither') or 0) > 0:
            enemy['wither'] -= 1
            if enemy['wither'] <= 0:
                enemy['health'] = 0
                events.append({'type': 'enemy_withered', 'enemy_id': enemy['id']})
        poison = max(0, int(enemy.get('poison') or 0))
        if poison:
            if 'toxic_conversion' in STORY_ENEMIES[enemy['def_id']].get('traits', ()):
                before = int(enemy.get('health') or 0)
                enemy['health'] = min(int(enemy.get('max_health') or before), before + poison)
                events.append({
                    'type': 'enemy_heal',
                    'enemy_id': enemy['id'],
                    'amount': int(enemy['health']) - before,
                    'before': before,
                    'after': int(enemy['health']),
                    'source': 'toxic_conversion',
                })
            else:
                _enemy_raw_damage(
                    state,
                    enemy,
                    poison,
                    events,
                    'poison',
                    player_caused=True,
                )
            if int(enemy.get('stagnation') or 0) <= 0:
                enemy['poison'] = math.floor(poison / 2)
            enemy['poison'] = int(enemy.get('poison') or 0) + max(
                0,
                int(enemy.get('toxic_poison') or 0),
            )
        if int(enemy.get('fire') or 0) > 0 and int(enemy.get('health') or 0) > 0:
            _enemy_raw_damage(
                state,
                enemy,
                int(enemy['fire']),
                events,
                'fire',
                player_caused=True,
            )
        enemy['stagnation'] = max(0, int(enemy.get('stagnation') or 0) - 1)
        enemy['electric_web'] = max(0, int(enemy.get('electric_web') or 0) - 1)
        if int(enemy.get('health') or 0) <= 0:
            continue
        enemy['evade'] = max(0, int(enemy.get('evade') or 0) - 1)
        if enemy.pop('hidden_fresh', False):
            pass
        else:
            enemy['hidden'] = max(0, int(enemy.get('hidden') or 0) - 1)
        turn_shield = max(0, int(enemy.get('turn_shield') or 0))
        if turn_shield:
            _gain_shield(state, turn_shield, events, source='turn_shield', enemy=enemy)
        regeneration = max(0, int(enemy.get('regeneration') or 0))
        if regeneration:
            before = int(enemy.get('health') or 0)
            enemy['health'] = min(int(enemy.get('max_health') or before), before + regeneration)
            healed = int(enemy['health']) - before
            if healed:
                events.append({
                    'type': 'enemy_heal',
                    'enemy_id': enemy['id'],
                    'amount': healed,
                    'before': before,
                    'after': int(enemy['health']),
                    'source': 'regeneration',
                })
    shelter_sources = [
        enemy for enemy in _living_enemies(combat)
        if int(enemy.get('shelter') or 0) > 0
        and int(enemy.get('damage_taken_round') or 0) <= 0
    ]
    for source_enemy in shelter_sources:
        shelter = int(source_enemy.get('shelter') or 0)
        for ally in _living_enemies(combat):
            _gain_shield(state, shelter, events, source='shelter', enemy=ally)
    for enemy in combat['enemies']:
        enemy['damage_taken_round'] = 0
    combat['evade'] = max(0, int(combat.get('evade') or 0) - 1)
    if int(combat.get('entangle') or 0) > 0:
        entangle = int(combat['entangle'])
        _player_raw_damage(state, entangle, events, 'entangle')
        combat['entangle'] = 0
        events.append({
            'type': 'status_cleared',
            'target_id': 'player',
            'status': 'entangle',
            'before': entangle,
        })
    poison = max(0, int(combat.get('poison') or 0))
    if poison:
        _player_raw_damage(state, poison, events, 'poison')
        if int(combat.get('stagnation') or 0) <= 0:
            combat['poison'] = math.floor(poison / 2)
        combat['poison'] = int(combat.get('poison') or 0) + max(
            0,
            int(combat.get('toxic_poison') or 0),
        )
    if int(combat.get('fire') or 0) > 0:
        _player_raw_damage(state, int(combat['fire']), events, 'fire')
    combat['stagnation'] = max(0, int(combat.get('stagnation') or 0) - 1)
    for delayed in combat.get('delayed_player_statuses', []):
        _apply_status(
            state,
            combat,
            delayed.get('status'),
            int(delayed.get('amount') or 0),
            events,
            source='delayed',
        )
    combat['delayed_player_statuses'] = []
    for delayed in list(combat.get('delayed_copies', [])):
        delayed['turns'] = int(delayed.get('turns') or 0) - 1
        if delayed['turns'] <= 0:
            _put_in_hand(state, _new_card(state, delayed['def_id'], delayed.get('upgraded')), events)
            combat['delayed_copies'].remove(delayed)
    _check_combat_end(state, seed, events)
    if state.get('phase') != 'combat':
        return
    combat['round'] = int(combat.get('round') or 1) + (0 if extra else 1)
    combat['turn'] = 'player'
    combat['turn_kind'] = 'extra' if extra else 'normal'
    combat['cards_played_this_turn'] = 0
    combat['active_discards_this_turn'] = 0
    combat['card_play_limit'] = combat.pop('next_extra_play_limit', None) if extra else None
    sturdy = max(0, int(combat.get('sturdy') or 0))
    if sturdy:
        combat['sturdy'] = sturdy - 1
    else:
        combat['shield'] = 0
    # Restore the per-turn baseline, then add explicitly retained E.
    retained_elixir = int(combat.get('elixir') or 0) if _has_relic(state, 'easy_godhood') else 0
    retained_elixir = max(retained_elixir, int(combat.pop('retained_elixir', 0) or 0))
    combat['elixir'] = retained_elixir
    combat['magic'] = int(state['player'].get('magic') or 0)
    combat['draw_phase_complete'] = False
    _gain_elixir(state, _turn_elixir_baseline(state, combat), events)
    if _has_relic(state, 'easy_peace'):
        _heal_player(
            state,
            _relic_amount(state, 'easy_peace'),
            events,
            source='easy_peace',
        )
    if _has_relic(state, 'accumulate') and int(combat['round']) == 2:
        combat['temporary_power'] += _relic_amount(state, 'accumulate')
    if _has_relic(state, 'support'):
        _gain_shield(state, int(STORY_RELICS['support']['amount']), events)
    _machine_learning_turn_start(state, seed, events)
    _run_turn_start_equipment(state, seed, events)
    for equipment in combat.get('equipment', []):
        equipment['turns_equipped'] = int(equipment.get('turns_equipped') or 0) + 1
    _activate_player_blind(combat, events)
    for pending_status in combat.pop('pending_extra_turn_statuses', []):
        _apply_status(
            state,
            combat,
            str(pending_status.get('status') or ''),
            int(pending_status.get('amount') or 0),
            events,
            source='extra_turn',
        )
    _play_ready_cards_in_hand(state, seed, events)
    if state.get('phase') != 'combat':
        return
    turn_draw = int(STORY_RULES['draw_per_turn'])
    if _has_relic(state, 'grab_every_card'):
        turn_draw += 1
    if _has_relic(state, 'easy_tiger'):
        turn_draw += _relic_amount(state, 'easy_tiger')
    turn_draw += int(combat.pop('next_turn_draw_delta', 0) or 0)
    _draw_cards(state, turn_draw, seed, events)
    combat['draw_phase_complete'] = True
    if _has_relic(state, 'web_relic'):
        combat['cannot_draw'] = True
    delayed_charge = max(0, int(combat.get('delayed_hand_charge') or 0))
    if delayed_charge:
        for hand_card in combat.get('hand', []):
            hand_card.setdefault('modifiers', {})['charge'] = int(
                hand_card.get('modifiers', {}).get('charge') or 0
            ) + delayed_charge
        combat['delayed_hand_charge'] = 0
        events.append({
            'type': 'hand_charged',
            'amount': delayed_charge,
            'source': 'delayed',
        })
    if int(combat.get('stun') or 0) > 0:
        combat['stun'] = max(0, int(combat['stun']) - 1)
        events.append({'type': 'player_skipped', 'reason': 'stun'})
        _discard_hand_at_turn_end(state, seed, events)
        _enemy_turn(state, seed, events)


def _prepare_player_turn_end(state, seed, events, reason=None):
    combat = state['combat']
    combat['blind_active'] = False
    retain_limits = [
        max(0, int(effect.get('amount') or 0))
        for _, effect in _equipment_effects(combat, 'retain_elixir')
    ]
    if retain_limits:
        combat['retained_elixir'] = min(
            int(combat.get('elixir') or 0),
            max(retain_limits),
        )
    for status in _TURN_END_DECAY_STATUSES:
        combat[status] = max(0, int(combat.get(status) or 0) - 1)
    for enemy in combat.get('enemies', []):
        enemy['magic_shield_disabled'] = 0
    if int(combat.get('broken') or 0) > 0:
        combat['broken'] = 0
        events.append({'type': 'status_cleared', 'target_id': 'player', 'status': 'broken'})
    _discard_hand_at_turn_end(state, seed, events)
    event = {'type': 'turn_ended', 'turn_kind': combat.get('turn_kind')}
    if reason:
        event['reason'] = reason
    events.append(event)


def _end_turn(state, seed, events):
    if state.get('phase') != 'combat' or state.get('combat', {}).get('turn') != 'player':
        _fail('END_TURN_NOT_ALLOWED', '当前不能结束回合')
    combat = state['combat']
    if combat.get('opening_redraw_pending'):
        _fail('OPENING_REDRAW_PENDING', '请先处理冷却效果')
    if combat.get('pending_card_choice'):
        _fail('CARD_CHOICE_PENDING', '请先处理待选择的卡牌')
    _prepare_player_turn_end(state, seed, events)
    if combat.get('turn_kind') == 'normal':
        extra_limits = [
            int(effect.get('amount') or 1)
            for _, effect in _equipment_effects(combat, 'soul_splitter')
        ]
        if extra_limits:
            combat['extra_turn_limits'] = extra_limits
    extra_limits = combat.get('extra_turn_limits') or []
    if extra_limits:
        combat['next_extra_play_limit'] = int(extra_limits.pop(0))
        combat['extra_turn_limits'] = extra_limits
        _turn_boundary(state, seed, events, extra=True)
    else:
        _enemy_turn(state, seed, events)


def _reward_rarity(state, room_type, rng):
    value = rng.random()
    if room_type == 'boss':
        return 'ultra'
    if _difficulty(state) in ('hard', 'lunatic'):
        if room_type == 'elite':
            return 'common' if value < 0.53 else ('rare' if value < 0.93 else 'ultra')
        return 'common' if value < 0.77 else ('rare' if value < 0.97 else 'ultra')
    if room_type == 'elite':
        return 'common' if value < 0.40 else ('rare' if value < 0.90 else 'ultra')
    return 'common' if value < 0.70 else ('rare' if value < 0.95 else 'ultra')


def _reward_choices(state, seed, room_type='combat', count=3):
    rng = _rng(state, seed, f'card_reward:{room_type}')
    choices = []
    eligible_ids = [
        card_id for card_id in STORY_REWARD_CARD_IDS
        if not (
            _has_relic(state, 'coward_defense')
            and STORY_CARDS[card_id].get('type') == 'bloom'
        )
    ]
    for _ in range(count):
        rarity = _reward_rarity(state, room_type, rng)
        pool = [
            card_id for card_id in eligible_ids
            if STORY_CARDS[card_id]['rarity'] == rarity
        ]
        if not pool:
            pool = list(eligible_ids)
        if not pool:
            break
        available = [card_id for card_id in pool if card_id not in choices] or pool
        card_id = rng.choice(available)
        upgraded_chance = {1: 0, 2: 0.25, 3: 0.5, 4: 1}.get(int(state.get('stage') or 1), 0)
        if _difficulty(state) in ('hard', 'lunatic'):
            upgraded_chance *= 0.5
        choices.append({'card_id': card_id, 'upgraded': rng.random() < upgraded_chance})
    return choices


def _natural_relic_pool(state, rarity=None, for_shop=False):
    owned = set(state['player'].get('relics', []))
    return [
        relic_id
        for relic_id, relic in STORY_RELICS.items()
        if relic.get('rarity') != 'special'
        and relic_id not in owned
        and (rarity is None or relic.get('rarity') == rarity)
        and not (for_shop and relic.get('shop_excluded'))
    ]


def _random_relic(state, seed):
    pool = _natural_relic_pool(state)
    if not pool:
        return 'consolation'
    rng = _rng(state, seed, 'relic_reward')
    roll = rng.random()
    rarity = 'common' if roll < 0.50 else ('rare' if roll < 0.83 else 'ultra')
    rarity_pool = [item for item in pool if STORY_RELICS[item].get('rarity') == rarity]
    return rng.choice(rarity_pool or pool)


def _boss_relic_choices(state, seed, count=3):
    owned = set(state['player'].get('relics', []))
    pool = [
        relic_id for relic_id in STORY_BOSS_RELIC_IDS
        if relic_id not in owned
        and not (
            relic_id == 'peaceful_mind'
            and _has_relic(state, 'grab_every_card')
        )
    ]
    _rng(state, seed, 'boss_relic_choices').shuffle(pool)
    choices = pool[:max(0, int(count))]
    return choices or ['consolation']


def _queue_deck_operation(state, kind, source, count, candidate_ids, minimum=None):
    candidate_ids = list(dict.fromkeys(str(item) for item in candidate_ids if item))
    count = min(max(0, int(count or 0)), len(candidate_ids))
    if count <= 0:
        return None
    minimum = count if minimum is None else min(count, max(0, int(minimum)))
    serial = int(state.get('deck_operation_serial') or 0) + 1
    state['deck_operation_serial'] = serial
    operation = {
        'id': f'story-deck-operation-{serial:04d}',
        'kind': str(kind),
        'source': str(source or ''),
        'count': count,
        'minimum': minimum,
        'maximum': count,
        'candidate_ids': candidate_ids,
    }
    state.setdefault('pending_deck_operations', []).append(operation)
    return operation


def _queue_relic_operation(state, relic_id):
    player = state['player']
    relic = STORY_RELICS[relic_id]
    script = str(relic.get('script') or '')
    amount = max(0, int(relic.get('amount') or 0))
    if script == 'gain_upgrade':
        candidates = [
            card['instance_id'] for card in player['deck']
            if _card_is_upgradable(card)
        ]
        return _queue_deck_operation(state, 'upgrade', relic_id, amount, candidates)
    if script == 'gain_remove':
        if _has_relic(state, 'grab_every_card'):
            return None
        return _queue_deck_operation(
            state,
            'remove',
            relic_id,
            amount,
            [
                card['instance_id'] for card in player['deck']
                if not _card_has_tag(card, 'eternal')
            ],
            minimum=0,
        )
    if script == 'enchant_starter':
        candidates = [
            card['instance_id'] for card in player['deck']
            if card.get('def_id') == 'amulet'
        ]
        return _queue_deck_operation(state, 'enchant_amulet', relic_id, amount, candidates)
    return None


def _gain_relic(state, relic_id, seed, events):
    if not relic_id or relic_id not in STORY_RELICS:
        return
    player = state['player']
    if relic_id != 'consolation' and relic_id in player['relics']:
        relic_id = 'consolation'
    relic = STORY_RELICS[relic_id]
    player['relics'].append(relic_id)
    script = relic.get('script')
    raw_amount = relic.get('amount') or 0
    amount = int(raw_amount)
    if script == 'gain_gold':
        player['gold'] += amount
    elif script == 'gain_max_health':
        player['max_health'] += amount
        player['health'] += amount
    elif script == 'gain_max_health_only':
        player['max_health'] += amount
    elif script == 'primary_multiplier':
        multiplier = max(1.0, float(raw_amount))
        for card in player['deck']:
            if STORY_CARDS[card['def_id']].get('rarity') == 'primary':
                card.setdefault('modifiers', {})['primary_multiplier'] = multiplier
    operation = _queue_relic_operation(state, relic_id)
    events.append({'type': 'relic_gained', 'relic_id': relic_id})
    if operation:
        events.append({
            'type': 'deck_operation_required',
            'operation_id': operation['id'],
            'operation_kind': operation['kind'],
            'source': relic_id,
            'count': operation['count'],
        })


def _new_reward(gold, cards, relic, room_type):
    gold = max(0, int(gold or 0))
    cards = list(cards or [])
    relics = (
        [str(item) for item in relic if item]
        if isinstance(relic, (list, tuple))
        else ([str(relic)] if relic else [])
    )
    return {
        'gold': gold,
        'cards': cards,
        'relic': relics[0] if len(relics) == 1 else None,
        'relics': relics,
        'room_type': room_type,
        'claims': {
            'gold': gold <= 0,
            'card': not cards,
            'relic': not bool(relics),
        },
        'selected_card_id': None,
        'selected_relic_id': None,
        'card_skipped': False,
    }


def _reward_claims(reward):
    claims = reward.get('claims')
    if not isinstance(claims, dict):
        # Runs created before layered rewards already received their gold.
        claims = {
            'gold': True,
            'card': not bool(reward.get('cards')),
            'relic': not bool(reward.get('relic')),
        }
        reward['claims'] = claims
    claims['gold'] = bool(claims.get('gold')) or int(reward.get('gold') or 0) <= 0
    claims['card'] = bool(claims.get('card')) or not bool(reward.get('cards'))
    claims['relic'] = bool(claims.get('relic')) or not bool(
        reward.get('relics') or reward.get('relic')
    )
    return claims


def _new_chest_room(state, seed, namespace='chest'):
    gold = _rng(state, seed, f'{namespace}_gold').randint(40, 60)
    relic = _random_relic(state, seed)
    return {
        'type': 'chest',
        'options': ['claim_gold', 'claim_relic', 'leave'],
        'gold': gold,
        'relic': relic,
        'claims': {
            'gold': gold <= 0,
            'relic': not bool(relic),
        },
    }


def _chest_claims(room):
    claims = room.get('claims')
    if not isinstance(claims, dict):
        claims = {'gold': False, 'relic': False}
        room['claims'] = claims
    claims['gold'] = bool(claims.get('gold')) or int(room.get('gold') or 0) <= 0
    claims['relic'] = bool(claims.get('relic')) or not bool(room.get('relic'))
    # Keep the legacy aggregate claim action valid for already-open clients.
    room['options'] = ['claim_gold', 'claim_relic', 'leave', 'claim']
    return claims


def _finish_combat(state, seed, events):
    from story_mode import STORY_STAGES

    node = _node_lookup(state)[state['current_node_id']]
    event_resolution = state['combat'].get('event_resolution')
    if event_resolution == 'fight_help_spider':
        _upgrade_random_cards(state, 2, seed, events, 'creature_help_spider')
        _gain_deck_card(state, 'startled', events, source=event_resolution)
        events.append({'type': 'combat_victory', 'gold': 0, 'source': event_resolution})
        _complete_current_node(state, events)
        return
    if event_resolution == 'fight_help_yoba':
        _gain_relic(state, 'support', seed, events)
        _gain_deck_card(state, 'slimed', events, source=event_resolution)
        events.append({'type': 'combat_victory', 'gold': 0, 'source': event_resolution})
        _complete_current_node(state, events)
        return
    if event_resolution == 'fight_both':
        cards = _reward_choices(state, seed, 'elite')
        for choice in cards:
            choice['upgraded'] = True
        state['reward'] = _new_reward(
            100,
            cards,
            _random_relic(state, seed),
            'event',
        )
        state['phase'] = 'reward'
        events.append({'type': 'combat_victory', 'gold': 100, 'source': event_resolution})
        return
    room_type = state['combat'].get('reward_room_type') or node['type']
    is_standard_final_stage = (
        state.get('journey_mode') != 'boss_rush'
        and int(state.get('stage') or 1) >= len(STORY_STAGES)
    )
    if (
        room_type == 'boss'
        and is_standard_final_stage
        and _difficulty(state) == 'lunatic'
        and int(node.get('floor') or 0) < int(state.get('map', {}).get('floor_count') or 16)
    ):
        events.append({'type': 'combat_victory', 'gold': 0, 'source': 'lunatic_gate_boss'})
        _complete_current_node(state, events)
        return
    if (
        room_type == 'boss'
        and is_standard_final_stage
        and int(node.get('floor') or 0) >= int(state.get('map', {}).get('floor_count') or 16)
    ):
        events.append({'type': 'combat_victory', 'gold': 0, 'source': 'final_boss'})
        _complete_current_node(state, events)
        return
    if room_type == 'avoid_elite':
        events.append({
            'type': 'combat_victory',
            'gold': 0,
            'source': 'avoid_elite',
        })
        _complete_current_node(state, events)
        return
    if state.get('journey_mode') == 'boss_rush' and room_type == 'boss':
        state['reward'] = _new_boss_rush_elite_reward(state, seed)
        state['phase'] = 'reward'
        events.append({
            'type': 'combat_victory',
            'gold': int(state['reward'].get('gold') or 0),
            'source': 'boss_rush_boss',
        })
        return
    rng = _rng(state, seed, 'combat_reward')
    if room_type == 'boss':
        gold = rng.randint(100, 120)
    elif room_type == 'elite':
        gold = rng.randint(25, 35)
    else:
        gold = rng.randint(10, 20)
        state['normal_battles'] = int(state.get('normal_battles') or 0) + 1
        state['stage_normal_battles'] = int(state.get('stage_normal_battles') or 0) + 1
    if _difficulty(state) in ('hard', 'lunatic'):
        gold = math.floor(gold * 0.75)
    for _, effect in _equipment_effects(state['combat'], 'victory_gold'):
        gold += int(effect.get('amount') or 0)
    if (
        room_type == 'combat'
        and _has_relic(state, 'indomitable')
        and int(state['combat'].get('damage_taken') or 0) > int(STORY_RELICS['indomitable']['amount'])
    ):
        _upgrade_random_cards(
            state,
            _relic_count(state, 'indomitable'),
            seed,
            events,
            'indomitable',
        )
    relic = (
        _boss_relic_choices(state, seed)
        if room_type == 'boss'
        else (_random_relic(state, seed) if room_type == 'elite' else None)
    )
    state['reward'] = _new_reward(
        gold,
        _reward_choices(state, seed, room_type),
        relic,
        room_type,
    )
    state['phase'] = 'reward'
    events.append({'type': 'combat_victory', 'gold': gold})


def _enemy_defeat_context(events, enemy_id):
    enemy_id = str(enemy_id)
    for event in reversed(events):
        event_type = str(event.get('type') or '')
        if (
            event_type == 'enemy_damage'
            and str(event.get('enemy_id') or '') == enemy_id
        ):
            return event
        if (
            event_type == 'enemy_consumed'
            and str(event.get('victim_id') or '') == enemy_id
        ):
            return {
                'source': 'consumed',
                'actor_id': event.get('actor_id') or event.get('enemy_id'),
                'source_definition_id': event.get('source_definition_id'),
                'before': event.get('victim_health_before'),
                'after': 0,
            }
    return {}


def _emit_enemy_defeat(state, enemy, events, parallel_group=None):
    if enemy.get('defeat_event_emitted'):
        return
    context = _enemy_defeat_context(events, enemy['id'])
    enemy['defeat_event_emitted'] = True
    events.append({
        'type': 'enemy_defeated',
        'enemy_id': enemy['id'],
        'def_id': enemy['def_id'],
        'actor_id': context.get('actor_id'),
        'target_id': enemy['id'],
        'source': context.get('source'),
        'before': context.get('before'),
        'after': 0,
        'source_card_instance_id': context.get('source_card_instance_id'),
        'source_definition_id': context.get('source_definition_id'),
        'parallel_group': parallel_group,
    })


def _resolve_termite_mound_death(state, mound, seed, events):
    combat = state['combat']
    for termite in list(_living_enemies(combat)):
        if not str(termite.get('def_id') or '').startswith('termite_'):
            continue
        definition = STORY_ENEMIES[termite['def_id']]
        resolve_move = definition['moves'][-1]
        resolve_index = len(definition['moves']) - 1
        events.append({
            'type': 'enemy_action',
            'enemy_id': termite['id'],
            'move_index': resolve_index,
            'actor_id': termite['id'],
            'target_ids': _enemy_move_target_ids(combat, termite, resolve_move),
            'source_definition_id': termite['def_id'],
            'source': 'psionic_fountain',
            'presentation': {'motion': 'attack'},
        })
        for effect_index, effect in enumerate(resolve_move.get('effects') or ()):
            start = len(events)
            _resolve_enemy_effect(state, termite, effect, resolve_move, seed, events)
            for event in events[start:]:
                event.setdefault('actor_id', termite['id'])
                event.setdefault('source_definition_id', termite['def_id'])
                event.setdefault('effect_index', effect_index)
                event.setdefault('source_trigger', 'psionic_fountain')
        termite['psionic_sustain'] = 0
        termite['psionic_sustain_revive_pending'] = False


def _resolve_enemy_death_hooks(state, seed, events):
    combat = state.get('combat') or {}
    while True:
        for enemy in combat.get('enemies', []):
            if (
                int(enemy.get('health') or 0) <= 0
                and STORY_ENEMIES.get(enemy.get('def_id'), {}).get('script')
                == 'broken_machine'
            ):
                enemy['health'] = 1
                enemy['wither'] = 0
                enemy.pop('death_hook_resolved', None)
                enemy.pop('defeat_event_emitted', None)
                events.append({
                    'type': 'enemy_survived',
                    'enemy_id': enemy['id'],
                    'source': 'cover',
                })
        defeated = [
            enemy
            for enemy in list(combat.get('enemies', []))
            if int(enemy.get('health') or 0) <= 0
        ]
        pending = [enemy for enemy in defeated if not enemy.get('death_hook_resolved')]
        if not pending:
            break
        newly_defeated = [enemy for enemy in pending if not enemy.get('defeat_event_emitted')]
        defeat_group = f'enemy-defeat:{len(events)}' if len(newly_defeated) > 1 else None
        for enemy in newly_defeated:
            _emit_enemy_defeat(state, enemy, events, defeat_group)
            poison = max(0, int(enemy.get('poison') or 0))
            if poison:
                for mushroom in _living_enemies_with_trait(combat, 'toxic_conversion'):
                    _apply_status(
                        state,
                        mushroom,
                        'poison',
                        poison,
                        events,
                        source='toxic_conversion',
                    )
            proliferation_sources = [
                ally for ally in _living_enemies(combat)
                if 'proliferation' in STORY_ENEMIES[ally['def_id']].get('traits', ())
            ]
            for source_enemy in proliferation_sources:
                amount = max(0, int(source_enemy.get('proliferation') or 0))
                for ally in _living_enemies(combat):
                    before = int(ally.get('health') or 0)
                    ally['health'] = min(int(ally.get('max_health') or before), before + amount)
                    events.append({
                        'type': 'enemy_heal',
                        'enemy_id': ally['id'],
                        'amount': int(ally['health']) - before,
                        'before': before,
                        'after': int(ally['health']),
                        'source': source_enemy['id'],
                    })
                    _gain_shield(state, amount, events, source='proliferation', enemy=ally)
                    _apply_status(state, ally, 'sturdy', 1, events, source='proliferation')
        for enemy in pending:
            if enemy.get('death_hook_resolved'):
                continue
            enemy['death_hook_resolved'] = True
            script = STORY_ENEMIES[enemy['def_id']].get('script')
            obstacle = max(0, int(enemy.get('obstacle') or 0))
            if obstacle:
                before = max(0, int(combat.get('blockade') or 0))
                combat['blockade'] = max(0, before - obstacle)
                events.append({
                    'type': 'status_decay',
                    'target_id': 'player',
                    'status': 'blockade',
                    'before': before,
                    'after': int(combat['blockade']),
                    'source': 'obstacle',
                })
            toxic_pressure = max(0, int(enemy.get('toxic_pressure') or 0))
            if toxic_pressure:
                _apply_status(
                    state,
                    combat,
                    'toxic_poison',
                    toxic_pressure,
                    events,
                    source=enemy.get('def_id'),
                )
            if script == 'spider_cave':
                summoned = _summon_enemy(
                    state,
                    'spider_yoba',
                    events,
                    actor_id=enemy['id'],
                    source_definition_id=enemy['def_id'],
                    power=max(0, int(enemy.get('frenzy') or 0)),
                )
                events.append({
                    'type': 'enemy_death_trigger',
                    'enemy_id': enemy['id'],
                    'script': 'spider_cave',
                    'summoned_id': summoned['id'],
                })
            elif script == 'evil_centipede' and int(enemy.get('segments') or 0) > 0:
                remaining = int(enemy['segments']) - 1
                summoned = _summon_enemy(
                    state,
                    'evil_centipede',
                    events,
                    actor_id=enemy['id'],
                    source_definition_id=enemy['def_id'],
                    segments=remaining,
                    segment_origin=max(
                        int(enemy.get('segment_origin') or 0),
                        int(enemy.get('segments') or 0),
                    ),
                )
                events.append({
                    'type': 'enemy_death_trigger',
                    'enemy_id': enemy['id'],
                    'script': 'evil_centipede',
                    'summoned_id': summoned['id'],
                    'segments': remaining,
                })
            elif script == 'termite_mound':
                _resolve_termite_mound_death(state, enemy, seed, events)
            elif script == 'hive':
                frenzy = max(0, int(enemy.get('frenzy') or 0))
                _summon_enemy(
                    state,
                    'wasp',
                    events,
                    move_index=1,
                    wither=4,
                    actor_id=enemy['id'],
                    source_definition_id=enemy['def_id'],
                    shield=20 if frenzy >= 1 else 0,
                    power=10 if frenzy >= 2 else 0,
                )
                events.append({
                    'type': 'enemy_death_trigger',
                    'enemy_id': enemy['id'],
                    'script': 'hive',
                })
            elif script == 'wreckage':
                summon_id = str(enemy.get('death_summon') or '')
                if summon_id:
                    summoned = _summon_enemy(
                        state,
                        summon_id,
                        events,
                        actor_id=enemy['id'],
                        source_definition_id=enemy['def_id'],
                    )
                    if (
                        'brittle' in STORY_ENEMIES[enemy['def_id']].get('traits', ())
                        and str(enemy.get('death_reason') or '') != 'burst'
                    ):
                        summoned['max_health'] = max(1, math.ceil(int(summoned['max_health']) / 2))
                        summoned['health'] = int(summoned['max_health'])
                        summoned['stun'] = max(1, int(summoned.get('stun') or 0))
                    events.append({
                        'type': 'enemy_death_trigger',
                        'enemy_id': enemy['id'],
                        'script': 'wreckage',
                        'summoned_id': summoned['id'],
                    })


def _check_combat_end(state, seed, events):
    combat = state.get('combat')
    if not combat:
        return False
    _resolve_enemy_death_hooks(state, seed, events)
    if _resolve_player_death(state, events):
        return True
    threats = [
        enemy for enemy in _living_enemies(combat)
        if STORY_ENEMIES.get(enemy.get('def_id'), {}).get('script')
        != 'broken_machine'
    ]
    if not threats:
        _finish_combat(state, seed, events)
        return True
    return False


def _unlock_from_node(state, node_id):
    nodes = _node_lookup(state)
    for target_id in _outgoing_node_ids(state, node_id):
        if target_id in nodes:
            nodes[target_id]['status'] = 'available'


def _complete_current_node(state, events):
    from story_mode import STORY_STAGES

    nodes = _node_lookup(state)
    node = nodes[state['current_node_id']]
    node['status'] = 'completed'
    for relic_id in state.get('player', {}).get('relics', []):
        relic = STORY_RELICS.get(relic_id) or {}
        amount = max(0, int(relic.get('amount') or 0))
        if relic.get('script') == 'floor_heal':
            _heal_player(state, amount, events, source=relic_id)
        elif relic.get('script') == 'floor_max_health':
            state['player']['max_health'] = int(state['player'].get('max_health') or 1) + amount
            state['player']['health'] = int(state['player'].get('health') or 0) + amount
            events.append({
                'type': 'max_health',
                'amount': amount,
                'source': relic_id,
            })
    for equipment in (state.get('combat') or {}).get('equipment', []):
        equipment.pop('turns_equipped', None)
    if int(node['floor']) >= int(state.get('map', {}).get('floor_count') or 16):
        if state.get('journey_mode') == 'boss_rush':
            next_stage = int(state.get('stage') or 1) + 1
            stage_cycle = STORY_STAGES[(next_stage - 1) % len(STORY_STAGES)]
            state['phase'] = 'stage_choice'
            state['room'] = {
                'type': 'stage_choice',
                'stage': next_stage,
                'biomes': list(stage_cycle['biomes']),
                'boss_rush': True,
            }
        elif int(state.get('stage') or 1) < len(STORY_STAGES):
            next_stage = int(state.get('stage') or 1) + 1
            state['phase'] = 'stage_choice'
            state['room'] = {
                'type': 'stage_choice',
                'stage': next_stage,
                'biomes': list(STORY_STAGES[next_stage - 1]['biomes']),
            }
        else:
            state['phase'] = 'room'
            state['completed'] = False
            state['room'] = _story_event_room(
                'mysterious_person',
                {'zh': '神秘人物', 'en': 'Mysterious Person'},
                {
                    'zh': '你看到了一朵腐化的花花。',
                    'en': 'You see a corrupted flower.',
                },
                {'zh': '神秘人物', 'en': 'Mysterious Person'},
                '!',
                [
                    _event_option(
                        'mysterious_battle',
                        '战斗！',
                        'Fight!',
                        '你对这朵腐化的花花造成了9961伤害，它依旧屹立不倒，你被杀死了。',
                        'You deal 9961 damage to the corrupted flower. It remains standing and kills you.',
                    ),
                ],
                ending_event=True,
            )
    else:
        _unlock_from_node(state, node['id'])
        state['phase'] = 'map'
        state['room'] = None
    state['combat'] = None
    state['reward'] = None
    state.pop('recovery_checkpoint', None)
    state.pop('floor_entry_checkpoint', None)
    state['player']['elixir'] = int(state['player']['max_elixir'])
    events.append({'type': 'node_completed', 'node_id': node['id']})


def _complete_blessing_node(state):
    first = _node_lookup(state)[state['current_node_id']]
    first['status'] = 'completed'
    _unlock_from_node(state, first['id'])
    state['phase'] = 'map'
    state['room'] = None
    state['reward'] = None
    state.pop('floor_entry_checkpoint', None)


def _record_blessing(player, blessing_id):
    history = player.get('blessings')
    if not isinstance(history, list):
        previous = str(player.get('blessing') or '')
        history = [previous] if previous else []
        player['blessings'] = history
    history.append(blessing_id)
    player['blessing'] = blessing_id


def _new_blessing_card_reward(state, seed, round_index, round_total):
    return _new_sequential_card_reward(
        state,
        seed,
        'blessing',
        round_index,
        round_total,
        'blessing',
    )


def _new_sequential_card_reward(
    state,
    seed,
    source,
    round_index,
    round_total,
    room_type='event',
):
    reward = _new_reward(
        0,
        _reward_choices(state, seed, room_type),
        None,
        room_type,
    )
    reward.update({
        'source': str(source),
        'round_index': int(round_index),
        'round_total': int(round_total),
    })
    return reward


def _new_boss_rush_elite_reward(state, seed, round_index=1, round_total=2):
    rng = _rng(state, seed, 'boss_rush_elite_gold')
    gold = rng.randint(25, 35)
    if _difficulty(state) in ('hard', 'lunatic'):
        gold = math.floor(gold * 0.75)
    for _, effect in _equipment_effects(state.get('combat') or {}, 'victory_gold'):
        gold += int(effect.get('amount') or 0)
    reward = _new_reward(
        gold,
        _reward_choices(state, seed, 'elite'),
        _random_relic(state, seed),
        'elite',
    )
    reward.update({
        'source': 'boss_rush_boss_elite',
        'round_index': max(1, int(round_index)),
        'round_total': max(1, int(round_total)),
    })
    return reward


def _roll_blessing_options(state, seed, namespace):
    options = [
        blessing_id for blessing_id in STORY_BLESSINGS
        if not (
            blessing_id == 'remove_card'
            and _has_relic(state, 'grab_every_card')
        )
    ]
    _rng(state, seed, f'blessings:{namespace}').shuffle(options)
    return options[:min(3, len(options))]


def _prepare_blessing(state, seed, namespace):
    state['blessing_options'] = _roll_blessing_options(state, seed, namespace)
    state['phase'] = 'blessing'
    state['room'] = None
    state['reward'] = None


def _prepare_easy_relic_choice(state, seed):
    options = list(STORY_EASY_RELIC_IDS)
    _rng(state, seed, 'easy_relic_options').shuffle(options)
    state['easy_relic_options'] = options[:3]
    state['phase'] = 'easy_relic'
    state['room'] = None
    state['reward'] = None


def _activate_boss_rush_map(state):
    first = state['map']['floors'][0]['nodes'][0]
    first['status'] = 'available'
    state['current_floor'] = int(first['floor'])
    state['current_node_id'] = first['id']
    state['phase'] = 'map'
    state['room'] = None
    state['reward'] = None


def _prepare_boss_rush_start(state, seed):
    state['reward'] = _new_sequential_card_reward(
        state,
        seed,
        'boss_rush_start_cards',
        1,
        10,
        'combat',
    )
    state['phase'] = 'reward'
    state['room'] = None


def _start_journey(state, payload, seed, events):
    from story_mode import generate_boss_rush_map, generate_story_map

    if state.get('phase') != 'journey_setup':
        _fail('JOURNEY_ALREADY_STARTED', '旅程已经开始')
    room = state.get('room') or {}
    biome = str(payload.get('biome') or '')
    difficulty = str(payload.get('difficulty') or '')
    journey_mode = str(payload.get('mode') or 'standard')
    if biome not in room.get('biomes', []):
        _fail('INVALID_BIOME', '无法选择该区域')
    if difficulty not in room.get('difficulties', []):
        _fail('INVALID_DIFFICULTY', '无法选择该难度')
    if journey_mode not in room.get('modes', ['standard']):
        _fail('INVALID_JOURNEY_MODE', '无法选择该旅程模式')
    state['stage'] = 1
    state['biome'] = biome
    state['difficulty'] = difficulty
    state['journey_mode'] = journey_mode
    state['normal_battles'] = 0
    state['stage_normal_battles'] = 0
    state['map'] = (
        generate_boss_rush_map(seed, 1, biome, difficulty)
        if journey_mode == 'boss_rush'
        else generate_story_map(seed, 1, biome, difficulty)
    )
    first = state['map']['floors'][0]['nodes'][0]
    state['current_floor'] = int(first['floor'])
    state['current_node_id'] = first['id']
    if difficulty in ('hard', 'lunatic') and not any(
        card.get('def_id') == 'corruption'
        for card in state['player'].get('deck', [])
    ):
        _gain_deck_card(state, 'corruption', events, source='difficulty')
    if journey_mode == 'boss_rush':
        amulet = next(
            (
                card for card in state['player'].get('deck', [])
                if card.get('def_id') == 'amulet'
            ),
            None,
        )
        state['player']['deck'] = [amulet or _new_card(state, 'amulet')]
        first['status'] = 'locked'
    if difficulty == 'easy':
        _prepare_easy_relic_choice(state, seed)
    elif journey_mode == 'boss_rush':
        _prepare_boss_rush_start(state, seed)
    else:
        _prepare_blessing(state, seed, 'stage:1')
    events.append({
        'type': 'journey_started',
        'stage': 1,
        'biome': biome,
        'difficulty': difficulty,
        'mode': journey_mode,
    })


def _choose_easy_relic(state, payload, seed, events):
    if state.get('phase') != 'easy_relic':
        _fail('NO_EASY_RELIC_CHOICE', '当前不在简单难度天赋选择阶段')
    relic_id = str(payload.get('relic_id') or '')
    offered = state.get('easy_relic_options')
    if relic_id not in STORY_EASY_RELIC_IDS or relic_id not in (offered or []):
        _fail('EASY_RELIC_NOT_OFFERED', '该天赋不在本次选项中')
    _gain_relic(state, relic_id, seed, events)
    state.pop('easy_relic_options', None)
    if state.get('journey_mode') == 'boss_rush':
        _prepare_boss_rush_start(state, seed)
    else:
        _prepare_blessing(state, seed, 'stage:1')
    events.append({'type': 'easy_relic_chosen', 'relic_id': relic_id})


def _choose_blessing(state, payload, seed, events):
    if state.get('phase') != 'blessing':
        _fail('NO_BLESSING_CHOICE', '当前不在赐福选择阶段')
    blessing_id = str(payload.get('blessing_id') or '')
    blessing = STORY_BLESSINGS.get(blessing_id)
    if not blessing:
        _fail('INVALID_BLESSING', '不存在该赐福')
    offered = state.get('blessing_options')
    if isinstance(offered, list) and offered and blessing_id not in offered:
        _fail('BLESSING_NOT_OFFERED', '该赐福不在本次选项中')
    player = state['player']
    script = str(blessing.get('script') or '')
    amount = max(0, int(blessing.get('amount') or 0))

    if script in ('transform_card', 'remove_card'):
        card = _deck_card(player, payload)
        if script == 'remove_card':
            if _has_relic(state, 'grab_every_card'):
                _fail('CARD_REMOVAL_DISABLED', '见牌就抓使你无法删除牌')
            _ensure_card_removable(card)
            player['deck'].remove(card)
            events.append({
                'type': 'card_removed',
                'card_instance_id': card['instance_id'],
                'def_id': card['def_id'],
                'source': 'blessing',
            })
        else:
            pool = [
                card_id
                for card_id in STORY_REWARD_CARD_IDS
                if card_id != card.get('def_id')
            ]
            if not pool:
                _fail('NO_TRANSFORM_CARD', '当前没有可变化为的牌')
            previous_def_id = card['def_id']
            previous_upgraded = bool(card.get('upgraded'))
            card['def_id'] = _rng(state, seed, 'blessing_transform').choice(pool)
            card['upgraded'] = False
            card.pop('modifiers', None)
            events.append({
                'type': 'card_transformed',
                'card_instance_id': card['instance_id'],
                'from_def_id': previous_def_id,
                'from_upgraded': previous_upgraded,
                'to_def_id': card['def_id'],
                'to_upgraded': False,
                'source': 'blessing',
            })
    elif script == 'gain_max_health':
        player['max_health'] = int(player.get('max_health') or 0) + amount
    elif script == 'gain_random_rare_card':
        pool = [
            card_id
            for card_id in STORY_REWARD_CARD_IDS
            if STORY_CARDS[card_id].get('rarity') == 'rare'
        ]
        if not pool:
            _fail('NO_RARE_CARD', '当前没有可获得的稀有牌')
        card_id = _rng(state, seed, 'blessing_rare_card').choice(pool)
        _gain_deck_card(state, card_id, events, source='blessing')
    elif script == 'gain_gold':
        player['gold'] = int(player.get('gold') or 0) + amount
    elif script == 'gain_relic_and_fatigue':
        _gain_relic(state, _random_relic(state, seed), seed, events)
        _gain_deck_card(state, 'fatigued', events, source='blessing')
    elif script == 'card_rewards':
        _record_blessing(player, blessing_id)
        state['reward'] = _new_blessing_card_reward(state, seed, 1, amount)
        state['phase'] = 'reward'
        events.append({'type': 'blessing_chosen', 'blessing_id': blessing_id})
        return
    elif script == 'wealth_and_basics':
        player['gold'] = int(player.get('gold') or 0) + amount
        _gain_deck_card(state, 'basic', events, source='blessing')
        _gain_deck_card(state, 'rose', events, source='blessing')
    else:
        _fail('INVALID_BLESSING_SCRIPT', '该赐福尚未实现')

    _record_blessing(player, blessing_id)
    state.pop('blessing_options', None)
    _complete_blessing_node(state)
    events.append({'type': 'blessing_chosen', 'blessing_id': blessing_id})


def _shop_price(state, base, rng, neutral=False):
    value = int(round(base * rng.uniform(0.9, 1.1)))
    if neutral:
        value = math.ceil(value * 1.2)
    if _difficulty(state) in ('hard', 'lunatic'):
        value = math.ceil(value * 1.1)
    if _has_relic(state, 'bargaining'):
        discount = min(100, max(0, int(STORY_RELICS['bargaining']['amount'])))
        value = math.floor(value * (100 - discount) / 100)
    return max(1, value)


def _make_shop(state, seed):
    rng = _rng(state, seed, 'shop')
    cards = []
    slots = (
        ('common', 'primary', 2, 50),
        ('rare', 'primary', 2, 75),
        ('ultra', 'primary', 1, 150),
        ('rare', 'neutral', 1, 75),
        ('ultra', 'neutral', 1, 150),
    )
    for rarity, owner, count, base in slots:
        pool = [
            card_id for card_id in STORY_SHOP_CARD_IDS
            if STORY_CARDS[card_id]['rarity'] == rarity and STORY_CARDS[card_id]['owner'] == owner
            and not (
                _has_relic(state, 'coward_defense')
                and STORY_CARDS[card_id].get('type') == 'bloom'
            )
        ]
        rng.shuffle(pool)
        for card_id in pool[:count]:
            cards.append({
                'id': f'shop-card-{len(cards)}',
                'card_id': card_id,
                'price': _shop_price(state, base, rng, neutral=owner == 'neutral'),
                'rarity': rarity,
                'owner': owner,
                'base_price': base,
                'sold': False,
            })
    relics = []
    for rarity, base in (('common', 175), ('rare', 225), ('ultra', 275)):
        pool = _natural_relic_pool(state, rarity=rarity, for_shop=True)
        if pool:
            relics.append({
                'id': f'shop-relic-{len(relics)}',
                'relic_id': rng.choice(pool),
                'price': _shop_price(state, base, rng),
                'rarity': rarity,
                'base_price': base,
                'sold': False,
            })
    if not relics and not _natural_relic_pool(state, for_shop=True):
        relics.append({
            'id': 'shop-relic-0',
            'relic_id': 'consolation',
            'price': _shop_price(state, 175, rng),
            'rarity': 'special',
            'base_price': 175,
            'sold': False,
        })
    options = ['buy_card', 'buy_relic', 'upgrade_card', 'leave']
    if not _has_relic(state, 'grab_every_card'):
        options.insert(2, 'remove_card')
    return {
        'type': 'shop',
        'options': options,
        'cards': cards,
        'relics': relics,
        'remove_price': 75 + 25 * int(state.get('shop_removals') or 0),
        'upgrade_price': 50 + 25 * int(state.get('shop_upgrades') or 0),
        'service_used': False,
    }


def _event_option(
    option_id,
    zh,
    en,
    description_zh='',
    description_en='',
    *,
    requires_confirmation=False,
    selection=None,
    cost_gold=0,
    candidate_ids=None,
):
    option = {
        'id': option_id,
        'label': {'zh': zh, 'en': en},
        'description': {
            'zh': description_zh,
            'en': description_en or description_zh,
        },
    }
    if requires_confirmation:
        option['requires_confirmation'] = True
    if selection:
        option['selection'] = str(selection)
    if int(cost_gold or 0) > 0:
        option['cost_gold'] = int(cost_gold)
    if candidate_ids is not None:
        option['candidate_ids'] = [str(item) for item in candidate_ids]
    return option


def _story_event_room(
    event_id,
    title,
    body,
    speaker,
    scene_mark,
    choices,
    **extra,
):
    choices = list(choices or [])
    room = {
        'type': 'event',
        'event_id': event_id,
        'title': title,
        'description': body,
        'scene': {
            'id': event_id,
            'kind': 'symbol',
            'mark': scene_mark,
        },
        'speaker': speaker,
        'body': body,
        'stage_id': 'intro',
        'history': [],
        'choices': choices,
        # Kept during the transition so older clients and saved runs continue
        # to understand the same event room.
        'options': choices,
    }
    room.update(extra)
    return room


def _record_event_progress(room, choice_id, result, stage_id=None):
    history = room.setdefault('history', [])
    history.append({
        'stage_id': str(room.get('stage_id') or 'intro'),
        'choice_id': str(choice_id or ''),
        'result': copy.deepcopy(result),
    })
    if len(history) > 12:
        del history[:-12]
    if stage_id:
        room['stage_id'] = str(stage_id)
    room['last_result'] = copy.deepcopy(result)
    room['body'] = copy.deepcopy(result)


def _choose_story_event_id(state, seed, event_ids):
    event_ids = list(dict.fromkeys(str(item) for item in event_ids if item))
    if not event_ids:
        _fail('EMPTY_EVENT_POOL', '当前没有可用事件')
    history = state.setdefault('encounter_history', {})
    seen = {
        str(item) for item in history.get('event', [])
        if str(item)
    }
    available = [event_id for event_id in event_ids if event_id not in seen]
    if not available:
        seen.difference_update(event_ids)
        available = list(event_ids)
    event_id = _rng(state, seed, 'story_event').choice(available)
    seen.add(event_id)
    history['event'] = sorted(seen)
    return event_id


def _make_story_event(state, seed):
    event_ids = [
        'mystery_lottery',
        'occultist',
        'ant_tools',
        'auction',
        'hive_visit',
        'adventure_master',
        'dandelion_seed_event',
        'farm',
    ]
    deck = list(state.get('player', {}).get('deck', []))
    if deck and int(state.get('player', {}).get('gold') or 0) >= 50:
        event_ids.append('card_trader')
    if str(state.get('biome') or '') == 'garden':
        event_ids.append('creature_struggle')
    event_id = _choose_story_event_id(state, seed, event_ids)
    if event_id == 'creature_struggle':
        return _story_event_room(
            event_id,
            {'zh': '生物争斗', 'en': 'Creature Struggle'},
            {
                'zh': '你发现一只蜘蛛和蜘蛛尤巴正在争斗。',
                'en': 'You find a Spider and Yoba Spider fighting.',
            },
            {'zh': '争斗中的生物', 'en': 'Fighting Creatures'},
            '!',
            [
                _event_option('fight_help_spider', '帮助蜘蛛', 'Help the Spider', '与半血蜘蛛尤巴战斗。'),
                _event_option('fight_help_yoba', '帮助蜘蛛尤巴', 'Help Yoba Spider', '与两只蜘蛛战斗。'),
                _event_option('fight_both', '这样才对', 'Fight Both', '同时挑战蜘蛛与半血蜘蛛尤巴，奖励更好。'),
                _event_option(
                    'fight_leave',
                    '假装无事发生',
                    'Walk Past',
                    '获得1张[[card:unrelenting]]。',
                    'Gain 1 [[card:unrelenting]].',
                    requires_confirmation=True,
                ),
            ],
        )
    if event_id == 'mystery_lottery':
        return _story_event_room(
            event_id,
            {'zh': '神秘抽奖机', 'en': 'Mysterious Lottery'},
            {
                'zh': '你看到一台结构精巧的抽奖机，上面写着“50G一次”。',
                'en': 'A finely built lottery machine reads “50 G per try.”',
            },
            {'zh': '神秘抽奖机', 'en': 'Mysterious Lottery Machine'},
            '?',
            [
                _event_option(
                    'lottery_inspect',
                    '观察机器构造',
                    'Inspect the Machine',
                    '升级自己1张牌。',
                    'Upgrade one of your cards.',
                    selection='upgrade',
                ),
                _event_option(
                    'lottery_draw',
                    '花费50G抽奖',
                    'Pay 50 G',
                    '最多尝试4次。',
                    requires_confirmation=True,
                ),
                _event_option('leave', '离开', 'Leave'),
            ],
            attempts=0,
        )
    if event_id == 'occultist':
        return _story_event_room(
            event_id,
            {'zh': '邪术师', 'en': 'Occultist'},
            {
                'zh': '你遇见一位掌控黑暗力量的花花。',
                'en': 'You meet a flower wielding a dark power.',
            },
            {'zh': '邪术师', 'en': 'Occultist'},
            '*',
            [
                _event_option(
                    'occult_life',
                    '祈求更多生命',
                    'Ask for More Life',
                    '获得世界树之叶，失去30%最大H。',
                    requires_confirmation=True,
                ),
                _event_option(
                    'occult_power',
                    '祈求更大力量',
                    'Ask for More Power',
                    '获得[[card:mark]]，并将2张[[card:startled]]加入牌组。',
                    'Gain [[card:mark]] and add 2 [[card:startled]] to your deck.',
                    requires_confirmation=True,
                ),
                _event_option(
                    'occult_flee',
                    '被吓到并逃跑',
                    'Flee',
                    '将1张[[card:fatigued]]加入牌组。',
                    'Add 1 [[card:fatigued]] to your deck.',
                    requires_confirmation=True,
                ),
            ],
        )
    if event_id == 'auction':
        choices = [
            _event_option(
                'auction_honey',
                '竞拍蜂蜜',
                'Bid on Honey',
                '花费10G，升级1张牌。',
                'Pay 10 G to upgrade a card.',
                selection='upgrade',
                cost_gold=10,
            ),
            _event_option(
                'auction_liquid',
                '竞拍黑色液体',
                'Bid on Black Liquid',
                '花费50G，删除1张牌。',
                'Pay 50 G to remove a card.',
                selection='remove',
                cost_gold=50,
            ),
            _event_option(
                'auction_steal',
                '趁乱抢劫',
                'Steal Amid the Chaos',
                '失去14H，获得109G。',
                'Lose 14 H and gain 109 G.',
                requires_confirmation=True,
            ),
        ]
        if _has_relic(state, 'grab_every_card'):
            choices = [choice for choice in choices if choice['id'] != 'auction_liquid']
        return _story_event_room(
            event_id,
            {'zh': '拍卖会', 'en': 'Auction'},
            {
                'zh': '一场临时拍卖正在热闹地进行。',
                'en': 'A lively impromptu auction is underway.',
            },
            {'zh': '拍卖师', 'en': 'Auctioneer'},
            'G',
            choices,
        )
    if event_id == 'hive_visit':
        return _story_event_room(
            event_id,
            {'zh': '蜂巢', 'en': 'Hive'},
            {
                'zh': '甜蜜的香气从蜂巢深处飘来。',
                'en': 'A sweet scent drifts from deep inside the hive.',
            },
            {'zh': '蜂巢', 'en': 'Hive'},
            '*',
            [
                _event_option(
                    'hive_honey',
                    '饮用蜂蜜',
                    'Drink Honey',
                    '升级1张牌。',
                    'Upgrade a card.',
                    selection='upgrade',
                ),
                _event_option('hive_pollen', '吃下花粉', 'Eat Pollen', '回复40%最大H。', 'Recover 40% of maximum H.'),
                _event_option(
                    'hive_explore',
                    '深入探险',
                    'Explore Deeper',
                    '获得1张[[card:fatigued]]和164G。',
                    'Gain 1 [[card:fatigued]] and 164 G.',
                    requires_confirmation=True,
                ),
            ],
        )
    if event_id == 'adventure_master':
        return _story_event_room(
            event_id,
            {'zh': '冒险大师', 'en': 'Adventure Master'},
            {
                'zh': '一位经验丰富的冒险者愿意指导你。',
                'en': 'An experienced adventurer offers to guide you.',
            },
            {'zh': '冒险大师', 'en': 'Adventure Master'},
            '+',
            [
                _event_option('adventure_learn', '学习技艺', 'Learn Techniques', '依次获得2次卡牌奖励。', 'Receive two card rewards in sequence.'),
                _event_option('adventure_refine', '精进技艺', 'Refine Techniques', '随机升级2张牌。', 'Upgrade two random cards.'),
                _event_option('adventure_rest', '休息', 'Rest', '回复50%最大H。', 'Recover 50% of maximum H.'),
            ],
        )
    if event_id == 'dandelion_seed_event':
        return _story_event_room(
            event_id,
            {'zh': '蒲公英种子', 'en': 'Dandelion Seed'},
            {
                'zh': '一颗蒲公英种子落在你的面前。',
                'en': 'A dandelion seed settles before you.',
            },
            {'zh': '蒲公英种子', 'en': 'Dandelion Seed'},
            '*',
            [
                _event_option('dandelion_eat', '吃下', 'Eat It', '随机升级1张牌。', 'Upgrade a random card.'),
                _event_option(
                    'dandelion_take',
                    '带走',
                    'Take It',
                    '获得1张[[card:dandelion_seed]]。',
                    'Gain 1 [[card:dandelion_seed]].',
                ),
            ],
        )
    if event_id == 'farm':
        return _story_event_room(
            event_id,
            {'zh': '废弃农场', 'en': 'Abandoned Farm'},
            {
                'zh': '荒废的田地让你想起过去，也可能藏着有用之物。',
                'en': 'The abandoned fields stir old memories and may hide something useful.',
            },
            {'zh': '废弃农场', 'en': 'Abandoned Farm'},
            '+',
            [
                _event_option(
                    'farm_reminisce',
                    '回忆',
                    'Reminisce',
                    '获得1张[[card:fatigued]]和1项随机天赋。',
                    'Gain 1 [[card:fatigued]] and a random talent.',
                    requires_confirmation=True,
                ),
                _event_option('farm_search', '搜刮', 'Search', '获得53G。', 'Gain 53 G.'),
            ],
        )
    if event_id == 'card_trader':
        candidates = list(state['player'].get('deck', []))
        _rng(state, seed, 'card_trader_candidates').shuffle(candidates)
        candidate_ids = [card['instance_id'] for card in candidates[:3]]
        choices = []
        if candidate_ids:
            choices.append(_event_option(
                'trade_card',
                '交换卡牌',
                'Trade a Card',
                '从展示的牌中选择1张，随机变化为另一张牌；基础牌需支付50G。',
                'Choose one offered card and transform it into another random card. Primary cards cost 50 G.',
                selection='trade',
                candidate_ids=candidate_ids,
            ))
        return _story_event_room(
            event_id,
            {'zh': '卡牌交换商', 'en': 'Card Trader'},
            {
                'zh': '商人从你的牌组中挑出了3张牌。选择其中1张，将其随机交换为另一张牌；基础牌需支付50G加工费。',
                'en': 'The trader selected 3 cards from your deck. Choose 1 to exchange for another random card. Primary cards cost a 50 G processing fee.',
            },
            {'zh': '卡牌交换商', 'en': 'Card Trader'},
            '?',
            choices,
            trade_candidates=candidate_ids,
        )
    return _story_event_room(
        'ant_tools',
        {'zh': '应对蚂蚁的方法', 'en': 'Handling Ants'},
        {
            'zh': '一位花花正在推销应对蚂蚁的工具。',
            'en': 'A flower is selling tools for dealing with ants.',
        },
        {'zh': '工具商', 'en': 'Tool Merchant'},
        '+',
        [
            _event_option(
                'event_buy',
                '花费35G升级随机卡牌',
                'Pay 35 G to Upgrade',
                requires_confirmation=True,
            ),
            _event_option(
                'event_help',
                '帮忙推销',
                'Help Sell',
                '获得80G与1张[[card:unrelenting]]。',
                'Gain 80 G and 1 [[card:unrelenting]].',
                requires_confirmation=True,
            ),
            _event_option('leave', '离开', 'Leave'),
        ],
    )


def _enter_event_node(state, node, seed, events):
    streak = max(0, int(state.get('event_miss_streak') or 0))
    multiplier = min(5, streak + 1)
    roll = _rng(state, seed, 'event_room_type').random()
    conversions = [
        ('combat', 0.10 * multiplier),
        ('shop', 0.05 * multiplier),
        ('chest', 0.02 * multiplier),
    ]
    if int(state.get('current_floor') or 1) > 9:
        conversions.insert(2, ('elite', 0.03 * multiplier))
    cursor = 0.0
    converted = None
    for room_type, probability in conversions:
        cursor += probability
        if roll < cursor:
            converted = room_type
            break
    if converted in ('combat', 'elite'):
        state['event_miss_streak'] = 0
        if converted == 'elite' and _has_relic(state, 'avoid_elite'):
            encounter = _encounter_specs(
                state,
                'combat',
                seed,
                category_override='hard',
            )
            _start_combat(
                state,
                {'type': 'combat'},
                seed,
                events,
                encounter_override=encounter,
            )
            state['combat']['reward_room_type'] = 'avoid_elite'
        else:
            _start_combat(state, {'type': converted}, seed, events)
            state['combat']['reward_room_type'] = converted
        events.append({'type': 'event_converted', 'room_type': converted})
        return
    if converted == 'shop':
        state['event_miss_streak'] = 0
        if _has_relic(state, 'frugal'):
            events.append({'type': 'room_skipped', 'room_type': 'shop', 'source': 'frugal'})
            _complete_current_node(state, events)
            return
        state['room'] = _make_shop(state, seed)
    elif converted == 'chest':
        state['event_miss_streak'] = 0
        state['room'] = _new_chest_room(state, seed, 'event_chest')
    else:
        state['event_miss_streak'] = streak + 1
        state['room'] = _make_story_event(state, seed)
    state['phase'] = 'room'
    events.append({
        'type': 'room_entered',
        'room_type': state['room']['type'],
        'source': 'event',
    })


def _enter_node(state, payload, seed, events):
    if state.get('phase') != 'map':
        _fail('NOT_ON_MAP', '当前不能选择路线')
    node_id = str(payload.get('node_id') or '')
    nodes = _node_lookup(state)
    node = nodes.get(node_id)
    if not node or node.get('status') != 'available':
        _fail('NODE_NOT_AVAILABLE', '该房间目前不可到达')
    for item in nodes.values():
        if item.get('status') == 'available':
            item['status'] = 'locked'
    node['status'] = 'current'
    state['current_node_id'] = node_id
    state['current_floor'] = int(node['floor'])
    if node['type'] == 'blessing':
        _prepare_blessing(state, seed, f'boss_rush:{state.get("stage", 1)}')
        events.append({'type': 'room_entered', 'room_type': 'blessing'})
        return
    if node['type'] == 'elite' and _has_relic(state, 'avoid_elite'):
        encounter = _encounter_specs(
            state,
            'combat',
            seed,
            category_override='hard',
        )
        _start_combat(
            state,
            {'type': 'combat'},
            seed,
            events,
            encounter_override=encounter,
        )
        state['combat']['reward_room_type'] = 'avoid_elite'
        events.append({'type': 'elite_avoided', 'node_id': node_id})
        return
    if node['type'] in ('combat', 'elite', 'boss'):
        _start_combat(state, node, seed, events)
        return
    if node['type'] == 'event':
        _enter_event_node(state, node, seed, events)
        return
    if node['type'] == 'rest':
        options = ['heal', 'upgrade', 'leave']
        if _has_relic(state, 'greedy'):
            options.append('gold')
        if (
            not _has_relic(state, 'dandelion_blessing')
            and any(card.get('def_id') == 'dandelion_seed' for card in state['player']['deck'])
        ):
            options.append('plant_dandelion')
        room = {'type': 'rest', 'options': options}
    elif node['type'] == 'chest':
        room = _new_chest_room(state, seed, 'chest')
    elif node['type'] == 'shop':
        if _has_relic(state, 'frugal'):
            events.append({'type': 'room_skipped', 'room_type': 'shop', 'source': 'frugal'})
            _complete_current_node(state, events)
            return
        room = _make_shop(state, seed)
    else:
        room = _make_story_event(state, seed)
    state['room'] = room
    state['phase'] = 'room'
    events.append({'type': 'room_entered', 'room_type': node['type']})


def _resolve_stage_choice(state, payload, seed, events):
    from story_mode import generate_boss_rush_map, generate_story_map

    room = state.get('room') or {}
    biome = str(payload.get('biome') or '')
    if state.get('phase') != 'stage_choice' or biome not in room.get('biomes', []):
        _fail('INVALID_STAGE_CHOICE', '无法选择该区域')
    boss_rush = bool(
        room.get('boss_rush')
        or state.get('journey_mode') == 'boss_rush'
    )
    stage = int(room['stage'])
    player = state['player']
    if _difficulty(state) in ('hard', 'lunatic'):
        target_health = math.ceil(int(player.get('max_health') or 1) * 0.8)
        _heal_player(
            state,
            max(0, target_health - int(player.get('health') or 0)),
            events,
            source='stage_transition',
        )
    else:
        _heal_player(
            state,
            int(player.get('max_health') or 1),
            events,
            source='stage_transition',
        )
    state['stage'] = stage
    state['biome'] = biome
    state['stage_normal_battles'] = 0
    if boss_rush:
        state['map'] = generate_boss_rush_map(
            seed,
            stage,
            biome,
            _difficulty(state),
        )
        _activate_boss_rush_map(state)
    else:
        state['map'] = generate_story_map(seed, stage, biome, _difficulty(state))
        first = state['map']['floors'][0]['nodes'][0]
        state['current_floor'] = 1
        state['current_node_id'] = first['id']
        _prepare_blessing(state, seed, f'stage:{stage}')
    events.append({
        'type': 'stage_started',
        'stage': stage,
        'biome': biome,
        'mode': 'boss_rush' if boss_rush else 'standard',
    })


def _restock_shop_item(state, item, seed, events, item_type):
    if not _has_relic(state, 'circulation'):
        return
    rng = _rng(state, seed, f'shop_restock:{item_type}')
    if item_type == 'card':
        rarity = item.get('rarity')
        owner = item.get('owner')
        pool = [
            card_id for card_id in STORY_SHOP_CARD_IDS
            if STORY_CARDS[card_id]['rarity'] == rarity
            and STORY_CARDS[card_id]['owner'] == owner
            and not (
                _has_relic(state, 'coward_defense')
                and STORY_CARDS[card_id].get('type') == 'bloom'
            )
        ]
        if not pool:
            return
        item['card_id'] = rng.choice(pool)
        item['price'] = _shop_price(
            state,
            int(item.get('base_price') or 50),
            rng,
            neutral=owner == 'neutral',
        )
    else:
        rarity = item.get('rarity')
        pool = _natural_relic_pool(state, rarity=rarity, for_shop=True)
        if not pool:
            if _natural_relic_pool(state, for_shop=True):
                return
            item['relic_id'] = 'consolation'
            item['rarity'] = 'special'
        else:
            item['relic_id'] = rng.choice(pool)
        item['price'] = _shop_price(
            state,
            int(item.get('base_price') or 175),
            rng,
        )
    item['sold'] = False
    events.append({
        'type': 'shop_restocked',
        'item_id': item['id'],
        'item_type': item_type,
    })


def _upgrade_cards(state, cards, seed, events, namespace, apply_fast_learning=True):
    upgraded = []
    seen = set()
    for card in cards:
        instance_id = str(card.get('instance_id') or '')
        if (
            not instance_id
            or instance_id in seen
            or not _card_is_upgradable(card)
        ):
            continue
        seen.add(instance_id)
        upgrade = STORY_CARDS[card['def_id']].get('upgrade') or {}
        if upgrade.get('infinite'):
            card['upgrade_level'] = max(
                int(card.get('upgrade_level') or 0),
                1 if card.get('upgraded') else 0,
            ) + 1
        card['upgraded'] = True
        upgraded.append(card)
        event = {
            'type': 'card_upgraded',
            'card_instance_id': instance_id,
            'source': namespace,
        }
        if upgrade.get('infinite'):
            event['upgrade_level'] = int(card['upgrade_level'])
        events.append(event)

    if apply_fast_learning and upgraded and _has_relic(state, 'fast_learning'):
        candidates = [
            card for card in state['player']['deck']
            if _card_is_upgradable(card)
            and card['instance_id'] not in seen
        ]
        _rng(state, seed, f'fast_learning:{namespace}').shuffle(candidates)
        for card in candidates[:len(upgraded)]:
            upgrade = STORY_CARDS[card['def_id']].get('upgrade') or {}
            if upgrade.get('infinite'):
                card['upgrade_level'] = max(
                    int(card.get('upgrade_level') or 0),
                    1 if card.get('upgraded') else 0,
                ) + 1
            card['upgraded'] = True
            event = {
                'type': 'card_upgraded',
                'card_instance_id': card['instance_id'],
                'source': 'fast_learning',
                'trigger_source': namespace,
            }
            if upgrade.get('infinite'):
                event['upgrade_level'] = int(card['upgrade_level'])
            events.append(event)
    return len(upgraded)


def _upgrade_random_cards(state, count, seed, events, namespace):
    candidates = [
        card for card in state['player']['deck']
        if _card_is_upgradable(card)
    ]
    _rng(state, seed, namespace).shuffle(candidates)
    return _upgrade_cards(
        state,
        candidates[:max(0, int(count))],
        seed,
        events,
        namespace,
    )


def _resolve_deck_operation(state, payload, seed, events):
    operations = state.get('pending_deck_operations')
    if not isinstance(operations, list) or not operations:
        _fail('NO_DECK_OPERATION', '当前没有待处理的牌组操作')
    operation = operations[0]
    selected_ids = payload.get('selected_card_ids')
    if not isinstance(selected_ids, list):
        selected_ids = []
    selected_ids = [str(item) for item in selected_ids]
    if len(selected_ids) != len(set(selected_ids)):
        _fail('DUPLICATE_DECK_SELECTION', '不能重复选择同一张牌')
    maximum = max(0, int(operation.get('maximum', operation.get('count')) or 0))
    minimum = min(maximum, max(0, int(operation.get('minimum', maximum) or 0)))
    if len(selected_ids) < minimum or len(selected_ids) > maximum:
        if minimum == maximum:
            _fail('INVALID_DECK_SELECTION_COUNT', f'请选择{maximum}张牌')
        _fail('INVALID_DECK_SELECTION_COUNT', f'请选择至多{maximum}张牌')
    allowed = set(str(item) for item in operation.get('candidate_ids') or [])
    if any(instance_id not in allowed for instance_id in selected_ids):
        _fail('INVALID_DECK_SELECTION', '所选牌不属于本次可选范围')
    player = state['player']
    by_id = {
        str(card.get('instance_id') or ''): card
        for card in player.get('deck', [])
    }
    selected = [by_id.get(instance_id) for instance_id in selected_ids]
    if any(card is None for card in selected):
        _fail('INVALID_DECK_SELECTION', '所选牌已不在牌组中')

    kind = str(operation.get('kind') or '')
    source = str(operation.get('source') or kind)
    if kind == 'upgrade':
        if any(not _card_is_upgradable(card) for card in selected):
            _fail('CARD_NOT_UPGRADABLE', '请选择可升级的牌')
        _upgrade_cards(state, selected, seed, events, source)
    elif kind == 'remove':
        if _has_relic(state, 'grab_every_card'):
            _fail('CARD_REMOVAL_DISABLED', '见牌就抓使你无法删除牌')
        for card in selected:
            _ensure_card_removable(card)
            player['deck'].remove(card)
            events.append({
                'type': 'card_removed',
                'card_instance_id': card['instance_id'],
                'def_id': card['def_id'],
                'source': source,
            })
    elif kind == 'enchant_amulet':
        for card in selected:
            if card.get('def_id') != 'amulet':
                _fail('INVALID_ENCHANT_TARGET', '致臻化境只能选择护身符')
            card['def_id'] = 'enchanted_amulet'
            card.pop('modifiers', None)
            events.append({
                'type': 'card_transformed',
                'card_instance_id': card['instance_id'],
                'from_def_id': 'amulet',
                'to_def_id': 'enchanted_amulet',
                'source': source,
            })
    else:
        _fail('INVALID_DECK_OPERATION', '未知牌组操作')

    operations.pop(0)
    if not operations:
        state.pop('pending_deck_operations', None)
    events.append({
        'type': 'deck_operation_resolved',
        'operation_id': operation.get('id'),
        'operation_kind': kind,
        'source': source,
        'count': len(selected),
    })


def _room_option_ids(room):
    options = room.get('choices')
    if not isinstance(options, list):
        options = room.get('options', [])
    return {
        str(option.get('id') if isinstance(option, dict) else option)
        for option in options
    }


def _resolve_room(state, payload, seed, events):
    if state.get('phase') == 'stage_choice':
        _resolve_stage_choice(state, payload, seed, events)
        return
    if state.get('phase') != 'room' or not state.get('room'):
        _fail('NO_ROOM_CHOICE', '当前没有房间选项')
    room = state['room']
    if room.get('type') == 'chest':
        _chest_claims(room)
    option = str(payload.get('option') or '')
    player = state['player']
    if option not in _room_option_ids(room):
        _fail('INVALID_ROOM_OPTION', '无效的房间选项')
    complete = True
    if room['type'] == 'rest' and option == 'leave':
        events.append({'type': 'room_left', 'room_type': 'rest'})
    elif room['type'] == 'rest' and option == 'heal':
        _heal_player(state, math.ceil(int(player['max_health']) * 0.3), events, source='rest')
    elif room['type'] == 'rest' and option == 'upgrade':
        card = _deck_card(player, payload)
        if not _card_is_upgradable(card):
            _fail('CARD_NOT_UPGRADABLE', '请选择一张可升级的牌')
        _upgrade_cards(state, [card], seed, events, 'rest')
    elif room['type'] == 'rest' and option == 'gold':
        player['gold'] += _relic_amount(state, 'greedy')
    elif room['type'] == 'rest' and option == 'plant_dandelion':
        seed_card = next(
            (
                card
                for card in player['deck']
                if card.get('def_id') == 'dandelion_seed'
            ),
            None,
        )
        if seed_card is None or _has_relic(state, 'dandelion_blessing'):
            _fail('DANDELION_SEED_UNAVAILABLE', '当前没有可种植的蒲公英种子')
        player['deck'].remove(seed_card)
        events.append({
            'type': 'card_removed',
            'card_instance_id': seed_card['instance_id'],
            'def_id': seed_card['def_id'],
            'source': 'plant_dandelion',
        })
        _gain_relic(state, 'dandelion_blessing', seed, events)
    elif room['type'] == 'chest':
        claims = _chest_claims(room)
        if option == 'leave':
            events.append({
                'type': 'room_left',
                'room_type': 'chest',
                'skipped_gold': not claims['gold'],
                'skipped_relic': not claims['relic'],
            })
        elif option in ('claim', 'claim_gold'):
            if claims['gold']:
                _fail('CHEST_REWARD_ALREADY_CLAIMED', '宝箱金币已经领取')
            amount = max(0, int(room.get('gold') or 0))
            player['gold'] += amount
            claims['gold'] = True
            events.append({'type': 'chest_claimed', 'reward_type': 'gold', 'amount': amount})
            if option == 'claim' and not claims['relic']:
                relic_id = room.get('relic')
                _gain_relic(state, relic_id, seed, events)
                claims['relic'] = True
                events.append({'type': 'chest_claimed', 'reward_type': 'relic', 'relic_id': relic_id})
        elif option == 'claim_relic':
            if claims['relic']:
                _fail('CHEST_REWARD_ALREADY_CLAIMED', '宝箱天赋已经领取')
            relic_id = room.get('relic')
            _gain_relic(state, relic_id, seed, events)
            claims['relic'] = True
            events.append({'type': 'chest_claimed', 'reward_type': 'relic', 'relic_id': relic_id})
        complete = option == 'leave' or all(claims.values())
    elif room['type'] == 'event':
        event_id = room.get('event_id')
        if event_id == 'mysterious_person' and option == 'mysterious_battle':
            state['phase'] = 'complete'
            state['completed'] = True
            state['room'] = None
            state['reward'] = None
            events.append({
                'type': 'journey_completed',
                'ending': 'mysterious_person',
                'damage': 9961,
            })
            complete = False
        elif option in ('fight_help_spider', 'fight_help_yoba', 'fight_both'):
            encounters = {
                'fight_help_spider': [
                    {'def_id': 'spider_yoba', 'health': math.ceil(STORY_ENEMIES['spider_yoba']['max_health'] / 2)},
                ],
                'fight_help_yoba': [
                    {'def_id': 'spider'},
                    {'def_id': 'spider', 'move_index': 1},
                ],
                'fight_both': [
                    {'def_id': 'spider'},
                    {'def_id': 'spider_yoba', 'health': math.ceil(STORY_ENEMIES['spider_yoba']['max_health'] / 2)},
                ],
            }
            _start_combat(
                state,
                {'type': 'combat'},
                seed,
                events,
                encounter_override=encounters[option],
            )
            state['combat']['event_resolution'] = option
            complete = False
        elif option == 'fight_leave':
            _gain_deck_card(state, 'unrelenting', events, source='creature_struggle')
        elif option == 'lottery_inspect':
            card = _deck_card(player, payload)
            if not _card_is_upgradable(card):
                _fail('CARD_NOT_UPGRADABLE', '请选择一张可升级的牌')
            _upgrade_cards(state, [card], seed, events, 'lottery_inspect')
        elif option == 'lottery_draw':
            if int(room.get('attempts') or 0) >= 4:
                _fail('LOTTERY_FINISHED', '抽奖机已经无法继续使用')
            _pay_gold(player, 50)
            roll = _rng(state, seed, 'lottery_result').randint(1, 100)
            if roll <= 5:
                pool = [
                    card_id for card_id in STORY_REWARD_CARD_IDS
                    if STORY_CARDS[card_id]['rarity'] == 'rare'
                ]
                card_id = _rng(state, seed, 'lottery_card').choice(pool)
                _gain_deck_card(state, card_id, events, source='lottery')
                result = {
                    'zh': f'获得了[[card:{card_id}]]。',
                    'en': f'You won [[card:{card_id}]].',
                }
            elif roll <= 20:
                _heal_player(state, 20, events, source='lottery')
                result = {'zh': '回复20H。', 'en': 'Recovered 20 H.'}
            elif roll <= 35:
                player['max_health'] += 5
                player['health'] += 5
                result = {'zh': '最大H+5，并回复5H。', 'en': 'Gained 5 maximum H and recovered 5 H.'}
            elif roll <= 50:
                _upgrade_random_cards(state, 1, seed, events, 'lottery_book')
                result = {'zh': '随机升级了1张牌。', 'en': 'Upgraded a random card.'}
            else:
                player['health'] -= 1
                result = {'zh': '没有中奖，失去1H。', 'en': 'No prize. Lost 1 H.'}
            room['attempts'] = int(room.get('attempts') or 0) + 1
            _record_event_progress(
                room,
                option,
                result,
                stage_id=f'attempt_{room["attempts"]}',
            )
            complete = room['attempts'] >= 4
            if complete:
                player['health'] -= 5
                player['gold'] += 100
                events.append({'type': 'lottery_exploded', 'damage': 5, 'gold': 100})
            elif int(player.get('health') or 0) <= 0:
                _resolve_player_death(state, events)
                complete = False
        elif option == 'occult_life':
            _gain_relic(state, 'world_tree_leaf', seed, events)
            player['max_health'] = max(1, math.floor(int(player['max_health']) * 0.7))
            player['health'] = min(int(player['health']), int(player['max_health']))
        elif option == 'occult_power':
            for card_id in ('mark', 'startled', 'startled'):
                _gain_deck_card(state, card_id, events, source='occultist')
        elif option == 'occult_flee':
            _gain_deck_card(state, 'fatigued', events, source='occultist')
        elif option == 'auction_honey':
            card = _deck_card(player, payload)
            if not _card_is_upgradable(card):
                _fail('CARD_NOT_UPGRADABLE', '请选择一张可升级的牌')
            _pay_gold(player, 10)
            _upgrade_cards(state, [card], seed, events, 'auction_honey')
        elif option == 'auction_liquid':
            if _has_relic(state, 'grab_every_card'):
                _fail('CARD_REMOVAL_DISABLED', '见牌就抓使你无法删除牌')
            card = _deck_card(player, payload)
            _ensure_card_removable(card)
            _pay_gold(player, 50)
            player['deck'].remove(card)
            events.append({
                'type': 'card_removed',
                'card_instance_id': card['instance_id'],
                'def_id': card['def_id'],
                'source': 'auction_liquid',
            })
        elif option == 'auction_steal':
            player['health'] = int(player.get('health') or 0) - 14
            player['gold'] = int(player.get('gold') or 0) + 109
            events.append({'type': 'player_health_lost', 'amount': 14, 'source': 'auction_steal'})
            events.append({'type': 'gold_gained', 'amount': 109, 'source': 'auction_steal'})
        elif option == 'hive_honey':
            card = _deck_card(player, payload)
            if not _card_is_upgradable(card):
                _fail('CARD_NOT_UPGRADABLE', '请选择一张可升级的牌')
            _upgrade_cards(state, [card], seed, events, 'hive_honey')
        elif option == 'hive_pollen':
            _heal_player(
                state,
                math.ceil(int(player.get('max_health') or 0) * 0.4),
                events,
                source='hive_pollen',
            )
        elif option == 'hive_explore':
            _gain_deck_card(state, 'fatigued', events, source='hive_explore')
            player['gold'] = int(player.get('gold') or 0) + 164
        elif option == 'adventure_learn':
            state['reward'] = _new_sequential_card_reward(
                state,
                seed,
                'adventure_master',
                1,
                2,
                'event',
            )
            state['phase'] = 'reward'
            events.append({
                'type': 'event_card_reward_started',
                'source': 'adventure_master',
                'round_index': 1,
                'round_total': 2,
            })
            complete = False
        elif option == 'adventure_refine':
            _upgrade_random_cards(state, 2, seed, events, 'adventure_refine')
        elif option == 'adventure_rest':
            _heal_player(
                state,
                math.ceil(int(player.get('max_health') or 0) * 0.5),
                events,
                source='adventure_rest',
            )
        elif option == 'dandelion_eat':
            _upgrade_random_cards(state, 1, seed, events, 'dandelion_eat')
        elif option == 'dandelion_take':
            _gain_deck_card(state, 'dandelion_seed', events, source='dandelion_seed_event')
        elif option == 'farm_reminisce':
            _gain_deck_card(state, 'fatigued', events, source='farm')
            _gain_relic(state, _random_relic(state, seed), seed, events)
        elif option == 'farm_search':
            player['gold'] = int(player.get('gold') or 0) + 53
        elif option == 'trade_card':
            card = _deck_card(player, payload)
            candidate_ids = {
                str(item) for item in room.get('trade_candidates', [])
            }
            if str(card.get('instance_id') or '') not in candidate_ids:
                _fail('INVALID_TRADE_CARD', '该牌不在商人本次展示的选项中')
            if STORY_CARDS[card['def_id']].get('rarity') == 'primary':
                _pay_gold(player, 50)
            pool = [
                card_id for card_id in STORY_REWARD_CARD_IDS
                if card_id != card.get('def_id')
            ]
            if not pool:
                _fail('NO_TRANSFORM_CARD', '当前没有可变化为的牌')
            previous_def_id = card['def_id']
            previous_upgraded = bool(card.get('upgraded'))
            card['def_id'] = _rng(state, seed, 'card_trader_result').choice(pool)
            card['upgraded'] = False
            card.pop('modifiers', None)
            events.append({
                'type': 'card_transformed',
                'card_instance_id': card['instance_id'],
                'from_def_id': previous_def_id,
                'from_upgraded': previous_upgraded,
                'to_def_id': card['def_id'],
                'to_upgraded': False,
                'source': 'card_trader',
            })
            result = {
                'zh': f'[[card:{previous_def_id}]]交换为了[[card:{card["def_id"]}]]。',
                'en': f'[[card:{previous_def_id}]] was exchanged for [[card:{card["def_id"]}]].',
            }
            _record_event_progress(room, option, result, stage_id='result')
            room['choices'] = [
                _event_option('trade_continue', '继续前进', 'Continue'),
            ]
            room['options'] = list(room['choices'])
            complete = False
        elif option == 'trade_continue':
            pass
        elif option == 'event_buy':
            if player['gold'] < 35:
                _fail('NOT_ENOUGH_GOLD', '金币不足')
            player['gold'] -= 35
            _upgrade_random_cards(state, 1, seed, events, 'event_upgrade')
        elif option == 'event_help':
            _gain_deck_card(state, 'unrelenting', events, source=event_id)
            player['gold'] += 80
        elif option == 'leave':
            pass
    elif room['type'] == 'shop':
        complete = option == 'leave'
        if option == 'buy_card':
            item = next((item for item in room['cards'] if item['id'] == payload.get('item_id') and not item.get('sold')), None)
            if not item:
                _fail('INVALID_SHOP_CARD', '商店中没有这张牌')
            _pay_gold(player, item['price'])
            _gain_deck_card(state, item['card_id'], events, source='shop')
            item['sold'] = True
            _restock_shop_item(state, item, seed, events, 'card')
        elif option == 'buy_relic':
            item = next((item for item in room['relics'] if item['id'] == payload.get('item_id') and not item.get('sold')), None)
            if not item:
                _fail('INVALID_SHOP_RELIC', '商店中没有该遗物')
            _pay_gold(player, item['price'])
            _gain_relic(state, item['relic_id'], seed, events)
            item['sold'] = True
            _restock_shop_item(state, item, seed, events, 'relic')
        elif option in ('remove_card', 'upgrade_card'):
            if room.get('service_used'):
                _fail('SHOP_SERVICE_ALREADY_USED', '本店的牌组服务已经使用')
            price_key = 'remove_price' if option == 'remove_card' else 'upgrade_price'
            if option == 'remove_card' and _has_relic(state, 'grab_every_card'):
                _fail('CARD_REMOVAL_DISABLED', '见牌就抓使你无法删除牌')
            _pay_gold(player, int(room[price_key]))
            card = _deck_card(player, payload)
            if option == 'remove_card':
                _ensure_card_removable(card)
                player['deck'].remove(card)
                state['shop_removals'] = int(state.get('shop_removals') or 0) + 1
            else:
                if not _card_is_upgradable(card):
                    _fail('CARD_NOT_UPGRADABLE', '请选择一张可升级的牌')
                _upgrade_cards(state, [card], seed, events, 'shop')
                state['shop_upgrades'] = int(state.get('shop_upgrades') or 0) + 1
            room[price_key] += 25
            room['service_used'] = True
    if int(player.get('health') or 0) <= 0:
        _resolve_player_death(state, events)
        if state.get('phase') == 'game_over':
            return
    if complete:
        _complete_current_node(state, events)


def _deck_card(player, payload):
    instance_id = str(payload.get('card_instance_id') or '')
    card = next((item for item in player['deck'] if item['instance_id'] == instance_id), None)
    if not card:
        _fail('INVALID_DECK_CARD', '请选择卡组中的牌')
    return card


def _pay_gold(player, price):
    if int(player.get('gold') or 0) < int(price):
        _fail('NOT_ENOUGH_GOLD', '金币不足')
    player['gold'] -= int(price)


def _choose_reward(state, payload, seed, events):
    if state.get('phase') != 'reward' or not state.get('reward'):
        _fail('NO_REWARD', '当前没有待领取奖励')
    reward = state['reward']
    claims = _reward_claims(reward)
    reward_type = str(payload.get('reward_type') or '').strip().lower()

    def claim_gold():
        if claims['gold']:
            _fail('REWARD_ALREADY_CLAIMED', '该金币奖励已经领取')
        amount = max(0, int(reward.get('gold') or 0))
        state['player']['gold'] += amount
        claims['gold'] = True
        events.append({'type': 'reward_claimed', 'reward_type': 'gold', 'amount': amount})

    def claim_card():
        if claims['card']:
            _fail('REWARD_ALREADY_CLAIMED', '该卡牌奖励已经处理')
        card_id = str(payload.get('card_id') or '')
        if card_id:
            choice = next(
                (
                    item for item in reward.get('cards', [])
                    if (item.get('card_id') if isinstance(item, dict) else item) == card_id
                ),
                None,
            )
            if choice is None:
                _fail('INVALID_REWARD_CARD', '奖励中没有这张牌')
            upgraded = bool(choice.get('upgraded')) if isinstance(choice, dict) else False
            _gain_deck_card(state, card_id, events, upgraded, source='reward')
            reward['selected_card_id'] = card_id
        else:
            if str(reward.get('source') or '') == 'boss_rush_start_cards':
                _fail('CARD_REWARD_REQUIRED', 'Boss Rush 的起始牌奖励必须选择')
            if _has_relic(state, 'grab_every_card'):
                _fail('CARD_REWARD_REQUIRED', '见牌就抓使你无法跳过卡牌奖励')
            reward['card_skipped'] = True
        claims['card'] = True
        events.append({
            'type': 'reward_claimed',
            'reward_type': 'card',
            'card_id': card_id or None,
            'skipped': not bool(card_id),
        })

    def claim_relic():
        if claims['relic']:
            _fail('REWARD_ALREADY_CLAIMED', '该天赋奖励已经领取')
        available = list(reward.get('relics') or [])
        if not available and reward.get('relic'):
            available = [reward['relic']]
        relic_id = str(payload.get('relic_id') or '')
        if not relic_id and available and (len(available) == 1 or not reward_type):
            relic_id = str(available[0])
        if relic_id not in available:
            _fail('INVALID_REWARD_RELIC', '请选择本次奖励中的天赋')
        _gain_relic(state, relic_id, seed, events)
        reward['selected_relic_id'] = relic_id
        claims['relic'] = True
        events.append({
            'type': 'reward_claimed',
            'reward_type': 'relic',
            'relic_id': relic_id,
        })

    def finish_reward():
        source = str(reward.get('source') or '')
        if source:
            round_index = max(1, int(reward.get('round_index') or 1))
            round_total = max(round_index, int(reward.get('round_total') or 1))
            if source == 'boss_rush_boss_elite' and round_index < round_total:
                state['reward'] = _new_boss_rush_elite_reward(
                    state,
                    seed,
                    round_index + 1,
                    round_total,
                )
                events.append({
                    'type': 'boss_rush_elite_reward_started',
                    'round_index': round_index + 1,
                    'round_total': round_total,
                })
            elif round_index < round_total:
                state['reward'] = _new_sequential_card_reward(
                    state,
                    seed,
                    source,
                    round_index + 1,
                    round_total,
                    str(reward.get('room_type') or 'event'),
                )
                events.append({
                    'type': (
                        'blessing_card_reward_started'
                        if source == 'blessing'
                        else 'sequential_card_reward_started'
                    ),
                    'source': source,
                    'round_index': round_index + 1,
                    'round_total': round_total,
                })
            elif source == 'blessing':
                state.pop('blessing_options', None)
                _complete_blessing_node(state)
            elif source == 'boss_rush_start_cards':
                state['reward'] = _new_reward(
                    0,
                    [],
                    _random_relic(state, seed),
                    'boss_rush',
                )
                state['reward'].update({
                    'source': 'boss_rush_start_relic',
                    'round_index': 1,
                    'round_total': 1,
                })
                events.append({'type': 'boss_rush_start_relic_reward'})
            elif source == 'boss_rush_start_relic':
                _activate_boss_rush_map(state)
            elif source == 'boss_rush_boss_elite':
                _complete_current_node(state, events)
            else:
                _complete_current_node(state, events)
        else:
            _complete_current_node(state, events)

    if not reward_type:
        # Compatibility for old clients and existing engine callers.
        if not claims['gold']:
            claim_gold()
        if not claims['card']:
            claim_card()
        if not claims['relic']:
            claim_relic()
        _complete_current_node(state, events)
        return
    if reward_type == 'gold':
        claim_gold()
    elif reward_type == 'card':
        claim_card()
        if str(reward.get('source') or '') == 'boss_rush_start_cards':
            finish_reward()
    elif reward_type == 'relic':
        claim_relic()
    elif reward_type == 'continue':
        if not all(claims.values()):
            _fail('REWARD_INCOMPLETE', '请先处理全部奖励')
        finish_reward()
    elif reward_type == 'leave':
        if (
            str(reward.get('source') or '') == 'boss_rush_start_cards'
            and not claims['card']
        ):
            _fail('CARD_REWARD_REQUIRED', 'Boss Rush 的起始牌奖励必须选择')
        if _has_relic(state, 'grab_every_card') and not claims['card']:
            _fail('CARD_REWARD_REQUIRED', '见牌就抓使你无法跳过卡牌奖励')
        skipped = [key for key, claimed in claims.items() if not claimed]
        for key in skipped:
            claims[key] = True
        if 'card' in skipped:
            reward['card_skipped'] = True
        events.append({'type': 'reward_left', 'skipped': skipped})
        if (
            str(reward.get('source') or '')
            and str(reward.get('source') or '') != 'boss_rush_boss_elite'
            and int(reward.get('round_index') or 1)
            < int(reward.get('round_total') or 1)
        ):
            reward['round_index'] = int(reward.get('round_total') or 1)
        finish_reward()
    else:
        _fail('INVALID_REWARD_TYPE', '不存在该奖励类型')


def _dev_integer(payload, key, maximum):
    if key not in payload or payload.get(key) in (None, ''):
        return None
    try:
        value = int(payload.get(key))
    except (TypeError, ValueError):
        _fail('INVALID_DEV_VALUE', f'{key} must be an integer')
    if value < 0 or value > maximum:
        _fail('INVALID_DEV_VALUE', f'{key} is outside the allowed range')
    return value


def _dev_set_values(state, payload, events):
    limits = {
        'health': 999999,
        'elixir': 2147483647,
        'magic': 2147483647,
        'gold': 999999999,
    }
    values = {
        key: _dev_integer(payload, key, maximum)
        for key, maximum in limits.items()
    }
    values = {key: value for key, value in values.items() if value is not None}
    if not values:
        _fail('NO_DEV_VALUES', '没有需要修改的数值')
    player = state['player']
    for key in ('health', 'elixir', 'magic', 'gold'):
        if key in values:
            player[key] = values[key]
    combat = state.get('combat')
    if isinstance(combat, dict):
        for key in ('elixir', 'magic'):
            if key in values:
                combat[key] = values[key]
    events.append({'type': 'dev_values_set', 'values': values})


def _dev_jump_node(state, payload, seed, events):
    node_id = str(payload.get('node_id') or '').strip()
    nodes = _node_lookup(state)
    target = nodes.get(node_id)
    if not target:
        _fail('UNKNOWN_DEV_NODE', '不存在该关卡')
    if int(target.get('floor') or 0) <= 1 or target.get('type') == 'blessing':
        _fail('DEV_BLESSING_JUMP_UNSUPPORTED', '第一层请使用重置地图')
    target_floor = int(target['floor'])
    for node in nodes.values():
        node_floor = int(node.get('floor') or 0)
        node['status'] = 'completed' if node_floor < target_floor else 'locked'
    state['phase'] = 'map'
    state['completed'] = False
    state['current_floor'] = target_floor
    state['current_node_id'] = node_id
    state['combat'] = None
    state['room'] = None
    state['reward'] = None
    target['status'] = 'available'
    events.append({'type': 'dev_node_jump', 'node_id': node_id, 'floor': target_floor, 'room_type': target.get('type')})
    _enter_node(state, {'node_id': node_id}, seed, events)


def _story_event_target_ids(event):
    targets = event.get('target_ids')
    if isinstance(targets, (list, tuple)):
        return [str(target) for target in targets if target not in (None, '')]
    if event.get('target_id') not in (None, ''):
        return [str(event['target_id'])]
    event_type = str(event.get('type') or '')
    if event_type in (
        'enemy_damage',
        'enemy_heal',
        'enemy_gain',
        'enemy_summoned',
        'enemy_skipped',
        'enemy_consumed',
        'enemy_death_trigger',
        'enemy_withered',
        'enemy_defeated',
    ) and event.get('enemy_id') not in (None, ''):
        return [str(event['enemy_id'])]
    if event_type in (
        'player_damage',
        'heal',
        'shield',
        'elixir',
        'magic',
        'revive',
        'game_over',
        'enemy_card_added',
        'card_created',
        'card_gained',
        'card_discarded',
        'card_exiled',
        'equipment_added',
    ):
        return ['player']
    return []


def _story_event_actor_id(event):
    if event.get('actor_id') not in (None, ''):
        return str(event['actor_id'])
    event_type = str(event.get('type') or '')
    if event_type in (
        'enemy_action',
        'enemy_gain',
        'enemy_heal',
        'enemy_skipped',
        'enemy_summoned',
        'enemy_consumed',
    ):
        if event.get('enemy_id') not in (None, ''):
            return str(event['enemy_id'])
    if event_type == 'player_damage' and event.get('attacker_id') not in (None, ''):
        return str(event['attacker_id'])
    if event_type in (
        'card_played',
        'enemy_damage',
        'heal',
        'shield',
        'elixir',
        'magic',
        'draw',
        'status',
        'card_created',
        'card_gained',
        'card_discarded',
        'card_exiled',
        'equipment_added',
        'reward_claimed',
    ):
        return 'player'
    return None


def _story_event_presentation(event):
    presentation = event.get('presentation')
    result = dict(presentation) if isinstance(presentation, dict) else {}
    event_type = str(event.get('type') or '')
    defaults = {
        'card_played': {'motion': 'card'},
        'player_damage': {'motion': 'hit', 'float': 'damage'},
        'enemy_damage': {'motion': 'hit', 'float': 'damage'},
        'enemy_gain': {'motion': 'gain', 'float': 'gain'},
        'enemy_heal': {'motion': 'recover', 'float': 'heal'},
        'enemy_summoned': {'motion': 'summon'},
        'enemy_withered': {'motion': 'status', 'float': 'status'},
        'enemy_defeated': {'motion': 'defeat'},
        'heal': {'motion': 'recover', 'float': 'heal'},
        'shield': {'motion': 'gain', 'float': 'shield'},
        'status': {'motion': 'status', 'float': 'status'},
        'draw': {'motion': 'draw'},
        'card_discarded': {'motion': 'discard'},
        'card_exiled': {'motion': 'exile'},
        'equipment_added': {'motion': 'equipment'},
    }
    for key, value in defaults.get(event_type, {}).items():
        result.setdefault(key, value)
    return result


def _finalize_story_events(state, events):
    counter = int(state.get('presentation_event_counter') or 0)
    finalized = []
    for sequence, source_event in enumerate(events, start=1):
        event = source_event
        event_type = str(event.get('type') or 'event')
        counter += 1
        event.setdefault('event_id', f'story-event-{counter:08d}')
        event.setdefault('sequence', sequence)
        event['kind'] = event_type
        actor_id = _story_event_actor_id(event)
        event.setdefault('actor_id', actor_id)
        event.setdefault('target_ids', _story_event_target_ids(event))
        hit_count = max(
            0,
            int(event.get('hit_count') or event.get('hits') or 0),
        )
        event['hit_count'] = hit_count
        event.setdefault('hit_index', 1 if hit_count else 0)
        history = event.get('history')
        if isinstance(history, list) and history:
            if isinstance(history[0], dict):
                event.setdefault('before', history[0].get('before'))
            if isinstance(history[-1], dict):
                event.setdefault('after', history[-1].get('after'))
        event.setdefault('before', None)
        event.setdefault('after', None)
        event.setdefault('amount', None)
        event.setdefault('source_card_instance_id', None)
        event.setdefault('source_definition_id', None)
        event.setdefault('parallel_group', None)
        event['presentation'] = _story_event_presentation(event)
        finalized.append(event)
    state['presentation_event_counter'] = counter
    return finalized


def apply_story_action(source_state, action_type, payload, seed):
    state = copy.deepcopy(source_state or {})
    _normalize_legacy_story_state(state)
    payload = payload if isinstance(payload, dict) else {}
    events = _StoryEventList(state)
    action_type = str(action_type or '').strip().lower()
    previous_phase = str(state.get('phase') or '')
    pending_operations = state.get('pending_deck_operations')
    if (
        isinstance(pending_operations, list)
        and pending_operations
        and action_type not in (
            'resolve_deck_operation',
            'dev_set_values',
            'restart_floor',
            'surrender',
        )
    ):
        _fail('DECK_OPERATION_PENDING', '请先处理待选择的牌组操作')
    pending_card_choice = (state.get('combat') or {}).get('pending_card_choice')
    if (
        isinstance(pending_card_choice, dict)
        and action_type not in (
            'resolve_card_choice',
            'dev_set_values',
            'restart_floor',
            'surrender',
        )
    ):
        _fail('CARD_CHOICE_PENDING', '请先处理待选择的卡牌')
    handlers = {
        'start_journey': lambda: _start_journey(state, payload, seed, events),
        'choose_easy_relic': lambda: _choose_easy_relic(state, payload, seed, events),
        'choose_blessing': lambda: _choose_blessing(state, payload, seed, events),
        'enter_node': lambda: _enter_node(state, payload, seed, events),
        'resume_node': lambda: _restore_recovery_checkpoint(state, events),
        'restart_floor': lambda: _restore_floor_entry_checkpoint(state, events),
        'opening_redraw': lambda: _resolve_opening_redraw(state, payload, seed, events),
        'resolve_card_choice': lambda: _resolve_pending_card_choice(state, payload, seed, events),
        'play_card': lambda: _play_card(state, payload, seed, events),
        'end_turn': lambda: _end_turn(state, seed, events),
        'choose_reward': lambda: _choose_reward(state, payload, seed, events),
        'resolve_room': lambda: _resolve_room(state, payload, seed, events),
        'choose_stage': lambda: _resolve_stage_choice(state, payload, seed, events),
        'resolve_deck_operation': lambda: _resolve_deck_operation(state, payload, seed, events),
        'surrender': lambda: _surrender_run(state, events),
        'dev_set_values': lambda: _dev_set_values(state, payload, events),
        'dev_jump_node': lambda: _dev_jump_node(state, payload, seed, events),
    }
    handler = handlers.get(action_type)
    if not handler:
        _fail('UNKNOWN_ACTION', '未知故事操作')
    handler()
    # A checkpoint restored by this action can itself come from an older run.
    _normalize_legacy_story_state(state)
    _refresh_combat_projections(state)
    phase = str(state.get('phase') or '')
    if action_type in ('enter_node', 'dev_jump_node') and phase in ('combat', 'room', 'reward'):
        _capture_floor_entry_checkpoint(state)
    if phase in ('combat', 'room', 'reward'):
        checkpoint_kind = None
        if action_type in ('enter_node', 'dev_jump_node'):
            checkpoint_kind = f'{phase}_entry'
        elif previous_phase != phase:
            checkpoint_kind = f'{phase}_entry'
        elif phase == 'combat' and action_type != 'resume_node':
            # Every accepted combat action leaves a complete, server-authoritative
            # state. Refresh recovery must resume here instead of rewinding the
            # whole encounter and losing piles such as the exile pile.
            checkpoint_kind = 'combat_progress'
        elif action_type == 'resolve_room' and phase == 'room':
            checkpoint_kind = 'room_progress'
        elif action_type == 'choose_reward' and phase == 'reward':
            checkpoint_kind = 'reward_progress'
        elif action_type == 'resolve_deck_operation' and phase in ('room', 'reward'):
            checkpoint_kind = f'{phase}_progress'
        if checkpoint_kind:
            _capture_recovery_checkpoint(state, checkpoint_kind)
    else:
        state.pop('recovery_checkpoint', None)
    events.capture_pending()
    events = _finalize_story_events(state, events)
    state['last_events'] = events[-40:]
    return state, events
