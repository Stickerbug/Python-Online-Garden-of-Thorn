"""Server-authoritative story-mode state machine."""

import copy
import hashlib
import math
import random

from story_content import (
    STORY_BLESSINGS,
    STORY_CARDS,
    STORY_ENCOUNTERS,
    STORY_ENEMIES,
    STORY_PLAYER_ATTACK_EFFECT_TYPES,
    STORY_RELICS,
    STORY_REWARD_CARD_IDS,
    STORY_RULES,
)


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
    restored = copy.deepcopy(snapshot)
    state.clear()
    state.update(restored)
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


def _rng(state, seed, namespace):
    counter = int(state.get('rng_counter') or 0)
    state['rng_counter'] = counter + 1
    digest = hashlib.sha256(f'{seed}:{namespace}:{counter}'.encode('utf-8')).digest()
    return random.Random(int.from_bytes(digest[:16], 'big'))


def _localized(value, lang='zh'):
    if isinstance(value, dict):
        return value.get(lang) or value.get('en') or value.get('zh') or ''
    return str(value or '')


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
    if modifiers:
        card['modifiers'] = copy.deepcopy(modifiers)
    if (
        state.get('phase') == 'combat'
        and _has_relic(state, 'steady')
        and STORY_CARDS[def_id].get('rarity') == 'primary'
    ):
        card.setdefault('modifiers', {})['primary_bonus'] = int(
            STORY_RELICS['steady']['amount']
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
    if card.get('upgraded'):
        values.update(copy.deepcopy(definition.get('upgrade') or {}))
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
    return values


def _card_tags(values):
    return set(str(tag) for tag in values.get('tags', ()))


def _living_enemies(combat):
    return [enemy for enemy in combat.get('enemies', []) if int(enemy.get('health') or 0) > 0]


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
    card = _new_card(state, card_id, upgraded)
    card.get('modifiers', {}).pop('primary_bonus', None)
    if not card.get('modifiers'):
        card.pop('modifiers', None)
    state['player']['deck'].append(card)
    if _has_relic(state, 'diligent'):
        _heal_player(
            state,
            int(STORY_RELICS['diligent']['amount']),
            events,
            source='diligent',
        )
    events.append({
        'type': 'card_gained',
        'card_id': card_id,
        'upgraded': bool(upgraded),
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
        'vulnerable', 'fragile', 'evade', 'poison', 'stun',
        'reflection', 'wither', 'broken', 'rockfall',
    )
    return sum(1 for key in keys if int(unit.get(key) or 0) > 0)


def _apply_status(state, target, status, amount, events, source='card'):
    amount = int(amount)
    if not status or not amount:
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
    })
    if status == 'vulnerable' and target_id != 'player':
        for _, effect in _equipment_effects(state['combat'], 'vulnerable_shield'):
            _gain_shield(state, int(effect.get('amount') or 0), events)


def _notify_exiled(state, card, events, seed):
    combat = state['combat']
    events.append({'type': 'card_exiled', 'card_instance_id': card['instance_id'], 'def_id': card['def_id']})
    for _, effect in _equipment_effects(combat):
        script = effect.get('script')
        if script == 'pearl' and card.get('def_id') != 'light':
            light = _new_card(state, 'light', modifiers={'generated': True})
            light.setdefault('modifiers', {})['retain'] = True
            light['modifiers']['force_exile'] = True
            _put_in_hand(state, light, events)
        elif script == 'magic_pearl':
            combat['power'] = int(combat.get('power') or 0) + 1
            events.append({'type': 'status', 'target_id': 'player', 'status': 'power', 'amount': 1})
        elif script == 'magic_acid':
            _draw_cards(state, 1, seed, events)
    values = _card_values(card)
    script = values.get('script')
    if script in ('azalea', 'azalea_plus'):
        amount = 4 if script == 'azalea_plus' else 3
        _gain_shield(state, amount, events)
        combat['discard_pile'].append(_new_card(state, card['def_id'], card.get('upgraded')))


def _put_in_hand(state, card, events):
    combat = state['combat']
    if len(combat['hand']) >= int(STORY_RULES['hand_limit']):
        combat['discard_pile'].append(card)
        events.append({'type': 'hand_overflow', 'count': 1, 'card_instance_ids': [card['instance_id']]})
        return False
    combat['hand'].append(card)
    events.append({'type': 'card_created', 'card_instance_id': card['instance_id'], 'def_id': card['def_id']})
    return True


def _on_card_drawn(state, card, seed, events, autoplay_depth):
    values = _card_values(card)
    if values.get('script') == 'slimed':
        alternatives = [item for item in state['combat']['hand'] if item is not card]
        if alternatives:
            victim = _rng(state, seed, 'slimed_discard').choice(alternatives)
            state['combat']['hand'].remove(victim)
            state['combat']['discard_pile'].append(victim)
            events.append({'type': 'card_discarded', 'card_instance_id': victim['instance_id'], 'reason': 'slimed'})
    if 'ready' in _card_tags(values) and autoplay_depth < 24:
        if _is_card_playable(state, card):
            target = min(_living_enemies(state['combat']), key=lambda item: (int(item['health']), item['id']), default=None)
            _play_card(
                state,
                {'card_instance_id': card['instance_id'], 'target_id': target and target['id'], 'automatic': True},
                seed,
                events,
                autoplay_depth=autoplay_depth + 1,
            )


def _draw_cards(state, count, seed, events, autoplay_depth=0):
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
        card = combat['draw_pile'].pop()
        if len(combat['hand']) >= int(STORY_RULES['hand_limit']):
            combat['discard_pile'].append(card)
            overflowed.append(card['instance_id'])
        else:
            combat['hand'].append(card)
            drawn.append(card['instance_id'])
            _on_card_drawn(state, card, seed, events, autoplay_depth)
    if drawn:
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
                and _is_card_playable(state, item)
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
        + int(attacker.get('temporary_power') or 0),
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
    if _has_relic(state, 'fearless_pain'):
        amount = max(0, amount - int(STORY_RELICS['fearless_pain']['amount']))
    shield = int(combat.get('shield') or 0)
    blocked = min(shield, amount)
    combat['shield'] = shield - blocked
    dealt = amount - blocked
    if _equipment_effects(combat, 'sponge'):
        poison = math.ceil(dealt / 2)
        if poison:
            _apply_status(state, combat, 'poison', poison, events, source='sponge')
        dealt = 0
    before = health_before
    state['player']['health'] = before - dealt
    combat['damage_taken'] = int(combat.get('damage_taken') or 0) + dealt
    if dealt and not combat.get('first_damage_taken'):
        combat['first_damage_taken'] = True
        if _has_relic(state, 'solid_barrier'):
            _gain_elixir(state, int(STORY_RELICS['solid_barrier']['amount']), events)
    return dealt, blocked, before


def _player_raw_damage(state, amount, events, source):
    amount = max(0, int(amount))
    combat = state['combat']
    shield = int(combat.get('shield') or 0)
    blocked = min(shield, amount)
    combat['shield'] = shield - blocked
    dealt = amount - blocked
    before = int(state['player']['health'])
    state['player']['health'] = before - dealt
    combat['damage_taken'] = int(combat.get('damage_taken') or 0) + dealt
    if dealt and not combat.get('first_damage_taken'):
        combat['first_damage_taken'] = True
        if _has_relic(state, 'solid_barrier'):
            _gain_elixir(state, int(STORY_RELICS['solid_barrier']['amount']), events)
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
            _enemy_raw_damage(state, attacker, combat_reflection, events, 'reflection')
        salt_multipliers = state['combat'].get('salt_multipliers') or []
        if dealt > 0 and attacker and int(attacker.get('health') or 0) > 0 and salt_multipliers:
            multiplier = max(1, int(salt_multipliers.pop(0)))
            _enemy_raw_damage(state, attacker, dealt * multiplier, events, 'salt')
    return total


def _enemy_raw_damage(state, enemy, amount, events, source, propagate=False):
    if not enemy or int(enemy.get('health') or 0) <= 0:
        return 0
    amount = max(0, int(amount))
    shield = int(enemy.get('shield') or 0)
    blocked = min(shield, amount)
    enemy['shield'] = shield - blocked
    dealt = amount - blocked
    before = int(enemy['health'])
    enemy['health'] = before - dealt
    events.append({
        'type': 'enemy_damage',
        'enemy_id': enemy['id'],
        'amount': dealt,
        'hits': 1,
        'hit_index': 1,
        'hit_count': 1,
        'history': [{'before': before, 'after': int(enemy['health']), 'blocked': blocked}],
        'before': before,
        'after': int(enemy['health']),
        'source': source,
    })
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
    elif effect_type == 'damage_from_shield':
        base_amount = int(combat.get('shield') or 0) * amount
        hits = 1
    elif effect_type == 'damage_per_elixir':
        base_amount = amount
        hits = int(context.get('x_cost') or 0)
    else:
        return None
    attack_multiplier = float(context.get('attack_multiplier') or 1)
    return max(0, math.floor(base_amount * attack_multiplier)), max(0, hits)


def _player_attack_hit_amount(state, enemy, base_amount, effect=None):
    """Apply shared player-side and target-side modifiers to one physical hit."""
    combat = state['combat']
    effect = effect or {}
    power_scale = int(effect.get('power_scale') or 1)
    power = int(combat.get('power') or 0) + int(combat.get('temporary_power') or 0)
    amount = max(0, int(base_amount) + power * power_scale)
    if int(combat.get('weak') or 0) > 0:
        amount = math.floor(amount * 0.75)
    if int(enemy.get('vulnerable') or 0) > 0:
        amount = math.floor(amount * 1.5)
    if effect.get('damage_multiplier'):
        amount = math.floor(amount * float(effect['damage_multiplier']))
    return max(0, amount)


def _enemy_physical_damage(state, enemy, base_amount, hits, events, source, values=None):
    combat = state['combat']
    values = values or {}
    hit_count = max(0, int(hits))
    if hit_count <= 0:
        return 0
    amount = _player_attack_hit_amount(state, enemy, base_amount, values)
    total = 0
    for hit_index in range(1, hit_count + 1):
        shield = int(enemy.get('shield') or 0)
        blocked = min(shield, amount)
        enemy['shield'] = shield - blocked
        dealt = amount - blocked
        before = int(enemy['health'])
        enemy['health'] = before - dealt
        total += dealt
        after = int(enemy['health'])
        events.append({
            'type': 'enemy_damage',
            'enemy_id': enemy['id'],
            'amount': dealt,
            'hits': 1,
            'hit_index': hit_index,
            'hit_count': hit_count,
            'history': [{'before': before, 'after': after, 'blocked': blocked}],
            'before': before,
            'after': after,
            'source': source,
        })
        reflection = int(enemy.get('reflection') or 0)
        if reflection > 0 and amount > 0:
            _player_damage(state, reflection, 1, events, 'reflection')
        if dealt and STORY_ENEMIES[enemy['def_id']].get('script') == 'swell':
            enemy['temporary_power'] = int(enemy.get('temporary_power') or 0) + 1
        if dealt and STORY_ENEMIES[enemy['def_id']].get('script') == 'centipede':
            enemies = combat['enemies']
            index = enemies.index(enemy)
            for adjacent_index in (index - 1, index + 1):
                if 0 <= adjacent_index < len(enemies):
                    adjacent = enemies[adjacent_index]
                    if STORY_ENEMIES[adjacent['def_id']].get('script') == 'centipede':
                        _enemy_raw_damage(state, adjacent, math.floor(dealt / 2), events, 'linked', propagate=True)
    return total


def _resolve_player_death(state, events):
    if int(state['player'].get('health') or 0) > 0:
        return False
    if _has_relic(state, 'world_tree_leaf') and not state.get('flags', {}).get('world_tree_leaf_used'):
        state.setdefault('flags', {})['world_tree_leaf_used'] = True
        state['player']['health'] = int(state['player']['max_health'])
        combat = state.get('combat') or {}
        for key in ('weak', 'vulnerable', 'fragile', 'poison', 'stun', 'broken'):
            combat[key] = 0
        events.append({'type': 'revive', 'source': 'world_tree_leaf'})
        return False
    state['player']['health'] = 0
    state['phase'] = 'game_over'
    events.append({'type': 'game_over'})
    return True


def _is_card_playable(state, card):
    combat = state.get('combat') or {}
    values = _card_values(card)
    tags = _card_tags(values)
    if (
        'unplayable' in tags
        or combat.get('turn') != 'player'
        or combat.get('opening_redraw_pending')
    ):
        return False
    if combat.get('card_play_limit') is not None and int(combat.get('cards_played_this_turn') or 0) >= int(combat['card_play_limit']):
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
        selected.append(card)
        seen.add(instance_id)
    return selected


def _validate_card_selections(combat, card, values, payload):
    for effect in values.get('effects') or ():
        effect_type = effect.get('type')
        if effect_type in ('choose_exile', 'copy_hand_card'):
            selected = _selected_cards(combat, payload, card)
            maximum = max(1, int(effect.get('amount') or 1))
            exact = effect_type == 'copy_hand_card' or bool(effect.get('exact'))
            available = len([item for item in combat['hand'] if item is not card])
            if exact and available < maximum:
                _fail('CARD_NOT_PLAYABLE', '没有足够的可选择手牌')
            if exact and len(selected) != maximum:
                _fail('CARD_SELECTION_REQUIRED', f'请选择{maximum}张牌')
            if len(selected) > maximum:
                _fail('TOO_MANY_CARDS_SELECTED', '选择的牌过多')
        elif effect_type == 'discard_to_draw_top':
            selected = _selected_cards(combat, payload, card, key='selected_discard_ids', pile='discard_pile')
            if combat['discard_pile'] and len(selected) != 1:
                _fail('CARD_SELECTION_REQUIRED', '请选择1张弃牌')


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


def _card_targets(combat, values, payload):
    living = _living_enemies(combat)
    if values.get('target') != 'enemy':
        return [combat]
    if 'wide' in _card_tags(values):
        return living
    target = _find_enemy(combat, str(payload.get('target_id') or ''))
    if target is None and len(living) == 1:
        target = living[0]
    if target is None:
        _fail('NO_TARGET', '请选择一个可选中的敌人')
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
            _enemy_physical_damage(
                state,
                target,
                hit_amount,
                hits,
                events,
                _localized(values.get('name')),
                values=effect,
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
        for selected_card in selected:
            combat['hand'].remove(selected_card)
            combat['exile_pile'].append(selected_card)
            _notify_exiled(state, selected_card, events, seed)
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
    elif effect_type == 'next_attack_multiplier':
        combat['next_attack_multiplier'] = max(float(combat.get('next_attack_multiplier') or 1), float(amount))
    elif effect_type == 'next_skill_repeats':
        combat['next_skill_repeats'] = max(int(combat.get('next_skill_repeats') or 0), int(amount))
    elif effect_type == 'temporary_effect':
        combat[str(effect.get('script') or '')] = True
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
    if not _is_card_playable(state, card):
        _fail('CARD_NOT_PLAYABLE', '当前无法打出这张牌')
    _validate_card_selections(combat, card, values, payload)
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
    if int(combat.get('broken') or 0) > 0:
        _player_raw_damage(state, int(combat['broken']), events, 'broken')

    is_attack = values.get('type') == 'thorn'
    is_skill = values.get('type') == 'bloom'
    attack_multiplier = float(combat.get('next_attack_multiplier') or 1) if is_attack else 1
    if is_attack:
        combat['next_attack_multiplier'] = 1
        if _has_relic(state, 'blade') and not combat.get('blade_used'):
            combat['blade_used'] = True
            for target in targets:
                _apply_status(state, target, 'vulnerable', 1, events, source='blade')
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
        'reserved_discard_cards': reserved_discard_cards,
    }
    for repeat_index in range(repeats):
        for effect_index, effect in enumerate(values.get('effects') or ()):
            effect_event_start = len(events)
            _resolve_effect(state, card, values, effect, targets, payload, seed, events, context)
            effect_events = events[effect_event_start:]
            direct_target_ids = {
                str(target.get('id') or 'player')
                for target in targets
            }
            group_prefix = (
                f'card:{instance_id}:repeat:{repeat_index}:effect:{effect_index}'
            )
            for event in effect_events:
                event.setdefault('actor_id', 'player')
                event.setdefault('source_card_instance_id', instance_id)
                event.setdefault('source_definition_id', card['def_id'])
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
        events.append({'type': 'equipment_added', 'card_instance_id': card['instance_id'], 'def_id': card['def_id']})
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
    _check_combat_end(state, seed, events)


def _enemy_intent(state, enemy):
    definition = STORY_ENEMIES[enemy['def_id']]
    move = _next_enemy_move(state, enemy)
    parts = []
    entries = []
    for effect in move['effects']:
        effect_type = effect['type']
        amount = int(effect.get('amount') or 0)
        hits = int(effect.get('hits') or 1)
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
            entries.append({
                'kind': 'status',
                'status': str(effect.get('status') or ''),
                'amount': amount,
                'target': 'self',
            })
            parts.append(f"获得{amount}层{effect.get('status')}")
        elif effect_type == 'player_status':
            labels = {'vulnerable': '易伤', 'weak': '虚弱', 'fragile': '脆弱', 'broken': '破损'}
            entries.append({
                'kind': 'status',
                'status': str(effect.get('status') or ''),
                'amount': amount,
                'target': 'player',
            })
            parts.append(f"施加{amount}层{labels.get(effect.get('status'), effect.get('status'))}")
        elif effect_type.startswith('summon'):
            entries.append({
                'kind': 'summon',
                'enemy_id': effect.get('enemy_id'),
                'amount': amount or 1,
                'target': 'self',
            })
            parts.append('召唤')
        elif effect_type in ('allies_power', 'allies_shield', 'allies_heal'):
            labels = {'allies_power': '力量', 'allies_shield': '护盾', 'allies_heal': 'H'}
            entry_kind = 'heal' if effect_type == 'allies_heal' else (
                'defend' if effect_type == 'allies_shield' else 'buff'
            )
            entries.append({
                'kind': entry_kind,
                'stat': labels[effect_type],
                'amount': amount,
                'target': 'all_enemies',
            })
            parts.append(f"全体友方+{amount}{labels[effect_type]}")
        elif effect_type in ('lowest_ally_shield', 'adjacent_shield'):
            entries.append({
                'kind': 'defend',
                'stat': 'shield',
                'amount': amount,
                'target': effect_type,
            })
            parts.append(f'友方获得{amount}层护盾')
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
            parts.append('吞噬友方')
        else:
            entries.append({'kind': 'special', 'effect_type': effect_type, 'amount': amount})
            parts.append(str(effect_type))
    return {'name': move['name'], 'entries': entries, 'summary': '；'.join(parts)}


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
    shield = int(enemy.get('shield') or 0)
    for effect in values.get('effects') or ():
        segment = _player_attack_effect_segment(state, effect, enemy, context)
        if segment is None:
            continue
        base_amount, hits = segment
        value = _player_attack_hit_amount(state, enemy, base_amount, effect)
        for _ in range(max(0, hits)):
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
        for enemy in living:
            prediction = _card_damage_prediction(state, card, enemy)
            if prediction:
                by_target[enemy['id']] = prediction
        if by_target:
            first = next(iter(by_target.values()))
            predictions[card['instance_id']] = {**first, 'by_target': by_target}
    combat['damage_predictions'] = predictions
    for enemy in combat.get('enemies', []):
        if int(enemy.get('health') or 0) > 0:
            enemy['intent'] = _enemy_intent(state, enemy)


def _encounter_specs(state, room_type, seed):
    biome = str(state.get('biome') or 'garden')
    groups = STORY_ENCOUNTERS.get(biome) or STORY_ENCOUNTERS['garden']
    if room_type == 'boss':
        category = 'boss'
    elif room_type == 'elite':
        category = 'elite'
    elif int(state.get('normal_battles') or 0) < 3:
        category = 'simple'
    else:
        category = 'hard'
    encounter = _rng(state, seed, f'encounter:{category}').choice(groups[category])
    return [spec if isinstance(spec, dict) else {'def_id': spec} for spec in encounter]


def _start_combat(state, node, seed, events, encounter_override=None):
    specs = encounter_override or _encounter_specs(state, node['type'], seed)
    draw_pile = copy.deepcopy(state['player']['deck'])
    if _has_relic(state, 'steady'):
        primary_bonus = int(STORY_RELICS['steady']['amount'])
        for card in draw_pile:
            if STORY_CARDS[card['def_id']].get('rarity') == 'primary':
                card.setdefault('modifiers', {})['primary_bonus'] = primary_bonus
    _rng(state, seed, 'combat_start').shuffle(draw_pile)
    enemies = []
    for index, spec in enumerate(specs):
        definition = STORY_ENEMIES[spec['def_id']]
        enemy = {
            'id': f'enemy-{index + 1}',
            'def_id': spec['def_id'],
            'name': definition['name'],
            'health': int(spec.get('health') or definition['max_health']),
            'max_health': int(definition['max_health']),
            'shield': 0,
            'power': 0,
            'temporary_power': 0,
            'weak': 0,
            'vulnerable': 0,
            'fragile': 0,
            'stun': 0,
            'reflection': int(spec.get('reflection') or 0),
            'wither': int(spec.get('wither') or 0),
            'move_index': int(spec.get('move_index') or 0),
        }
        if definition.get('script') == 'opening_reflection':
            enemy['reflection'] = 2
        enemies.append(enemy)
    state['combat'] = {
        'round': 1,
        'turn': 'player',
        'turn_kind': 'normal',
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
        'broken': 0,
        'draw_pile': draw_pile,
        'hand': [],
        'discard_pile': [],
        'exile_pile': [],
        'equipment': [],
        'enemies': enemies,
        'cards_played_this_turn': 0,
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
    }
    state['phase'] = 'combat'
    combat = state['combat']
    if _has_relic(state, 'ruthless'):
        combat['power'] += 1
    if _has_relic(state, 'firm_defense'):
        combat['endurance'] += 1
    for enemy in enemies:
        if _has_relic(state, 'opening_lightning'):
            event_offset = len(events)
            _enemy_raw_damage(state, enemy, int(STORY_RELICS['opening_lightning']['amount']), events, 'opening_lightning')
            for event in events[event_offset:]:
                if event.get('type') == 'enemy_damage':
                    event['parallel_group'] = 'opening_lightning'
    draw_count = int(STORY_RULES['draw_per_turn']) + int(state['player'].get('opening_draw_bonus') or 0)
    if _has_relic(state, 'prepared'):
        draw_count += int(STORY_RELICS['prepared']['amount'])
    if _has_relic(state, 'support'):
        draw_count -= 1
    if _has_relic(state, 'dandelion_blessing'):
        _gain_shield(
            state,
            int(STORY_RELICS['dandelion_blessing']['amount']),
            events,
        )
    _draw_cards(state, draw_count, seed, events)
    _refresh_combat_projections(state)
    events.append({'type': 'combat_start', 'enemy_ids': [enemy['def_id'] for enemy in enemies]})


def _next_enemy_move(state, enemy):
    definition = STORY_ENEMIES[enemy['def_id']]
    moves = definition['moves']
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
    return moves[move_index]


def _summon_enemy(
    state,
    enemy_id,
    events,
    move_index=0,
    wither=0,
    actor_id=None,
    source_definition_id=None,
):
    combat = state['combat']
    definition = STORY_ENEMIES[enemy_id]
    serial = int(combat.get('next_enemy_serial') or (len(combat['enemies']) + 1))
    combat['next_enemy_serial'] = serial + 1
    enemy = {
        'id': f'enemy-{serial}',
        'def_id': enemy_id,
        'name': definition['name'],
        'health': int(definition['max_health']),
        'max_health': int(definition['max_health']),
        'shield': 0,
        'power': 0,
        'temporary_power': 0,
        'weak': 0,
        'vulnerable': 0,
        'fragile': 0,
        'stun': 0,
        'reflection': 0,
        'wither': int(wither),
        'move_index': int(move_index),
    }
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
    return enemy


def _resolve_enemy_effect(state, enemy, effect, move, seed, events):
    combat = state['combat']
    effect_type = effect['type']
    amount = int(effect.get('amount') or 0)
    if effect_type == 'damage':
        _player_damage(state, amount, int(effect.get('hits') or 1), events, _localized(move['name']), enemy)
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
    elif effect_type == 'summon':
        for _ in range(amount):
            _summon_enemy(
                state,
                effect.get('enemy_id'),
                events,
                effect.get('move_index', 0),
                effect.get('wither', 0),
                actor_id=enemy['id'],
                source_definition_id=enemy['def_id'],
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


def _enemy_move_target_ids(combat, enemy, move):
    targets = []
    effect_types = {
        str(effect.get('type') or '')
        for effect in move.get('effects') or ()
    }
    if effect_types.intersection({'damage', 'player_status', 'add_draw_card'}):
        targets.append('player')
    if effect_types.intersection({
        'self_damage',
        'gain_power',
        'gain_shield',
        'gain_status',
        'self_heal',
        'consume_allies',
    }):
        targets.append(str(enemy['id']))
    if effect_types.intersection({
        'allies_power',
        'allies_shield',
        'allies_heal',
        'lowest_ally_shield',
        'adjacent_shield',
    }):
        targets.extend(str(ally['id']) for ally in _living_enemies(combat))
    return list(dict.fromkeys(targets))


def _enemy_turn(state, seed, events):
    combat = state['combat']
    combat['turn'] = 'enemy'
    action_order = list(combat['enemies'])
    for enemy in action_order:
        if int(enemy.get('health') or 0) <= 0:
            continue
        definition = STORY_ENEMIES[enemy['def_id']]
        if definition.get('script') != 'persistent_shield':
            enemy['shield'] = 0
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
            if _check_combat_end(state, seed, events):
                return
            continue
        move = _next_enemy_move(state, enemy)
        move_index = definition['moves'].index(move)
        has_attack = any(
            effect.get('type') == 'damage'
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
        if definition.get('script') == 'garden_rock':
            enemy['move_index'] = 1
        elif definition.get('script') == 'worker_ant':
            enemy['move_index'] = 2 if len(_living_enemies(combat)) <= 1 else (move_index + 1) % 2
        elif definition.get('script') == 'ant_queen' and move_index == 3:
            enemy['move_index'] = 0
        else:
            enemy['move_index'] = (move_index + 1) % len(definition['moves'])
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
        if 'void' in tags:
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
            if not modifiers:
                card.pop('modifiers', None)


def _run_turn_start_equipment(state, seed, events):
    combat = state['combat']
    for _, effect in list(_equipment_effects(combat)):
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


def _turn_boundary(state, seed, events, extra=False):
    combat = state['combat']
    combat['temporary_power'] = 0
    combat['disc_active'] = False
    combat['cannot_draw'] = False
    combat['next_attack_multiplier'] = 1
    combat['next_skill_repeats'] = 0
    _clear_temporary_card_modifiers(combat)
    for enemy in combat['enemies']:
        enemy['temporary_power'] = 0
        enemy['weak'] = max(0, int(enemy.get('weak') or 0) - 1)
        enemy['vulnerable'] = max(0, int(enemy.get('vulnerable') or 0) - 1)
        enemy['fragile'] = max(0, int(enemy.get('fragile') or 0) - 1)
        if int(enemy.get('wither') or 0) > 0:
            enemy['wither'] -= 1
            if enemy['wither'] <= 0:
                enemy['health'] = 0
                events.append({'type': 'enemy_withered', 'enemy_id': enemy['id']})
        if int(enemy.get('poison') or 0) > 0:
            _enemy_raw_damage(state, enemy, int(enemy['poison']), events, 'poison')
            enemy['poison'] = math.floor(int(enemy['poison']) / 2)
    combat['evade'] = max(0, int(combat.get('evade') or 0) - 1)
    if int(combat.get('poison') or 0) > 0:
        _player_raw_damage(state, int(combat['poison']), events, 'poison')
        combat['poison'] = math.floor(int(combat['poison']) / 2)
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
    combat['card_play_limit'] = combat.pop('next_extra_play_limit', None) if extra else None
    combat['shield'] = 0
    # Story resources do not carry between player turns. Restore the run's
    # per-turn baseline before resolving turn-start equipment and other gains.
    combat['elixir'] = 0
    combat['magic'] = int(state['player'].get('magic') or 0)
    _gain_elixir(state, int(state['player']['max_elixir']), events)
    if _has_relic(state, 'accumulate') and int(combat['round']) == 2:
        combat['temporary_power'] += int(STORY_RELICS['accumulate']['amount'])
    if _has_relic(state, 'support'):
        _gain_shield(state, int(STORY_RELICS['support']['amount']), events)
    _run_turn_start_equipment(state, seed, events)
    for equipment in combat.get('equipment', []):
        equipment['turns_equipped'] = int(equipment.get('turns_equipped') or 0) + 1
    _play_ready_cards_in_hand(state, seed, events)
    if state.get('phase') != 'combat':
        return
    _draw_cards(state, STORY_RULES['draw_per_turn'], seed, events)
    if int(combat.get('stun') or 0) > 0:
        combat['stun'] = max(0, int(combat['stun']) - 1)
        events.append({'type': 'player_skipped', 'reason': 'stun'})
        _discard_hand_at_turn_end(state, seed, events)
        _enemy_turn(state, seed, events)


def _end_turn(state, seed, events):
    if state.get('phase') != 'combat' or state.get('combat', {}).get('turn') != 'player':
        _fail('END_TURN_NOT_ALLOWED', '当前不能结束回合')
    combat = state['combat']
    if combat.get('opening_redraw_pending'):
        _fail('OPENING_REDRAW_PENDING', '请先处理冷却效果')
    for status in ('weak', 'vulnerable', 'fragile'):
        combat[status] = max(0, int(combat.get(status) or 0) - 1)
    if int(combat.get('broken') or 0) > 0:
        combat['broken'] = 0
        events.append({'type': 'status_cleared', 'target_id': 'player', 'status': 'broken'})
    _discard_hand_at_turn_end(state, seed, events)
    events.append({'type': 'turn_ended', 'turn_kind': combat.get('turn_kind')})
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


def _reward_rarity(room_type, rng):
    value = rng.random()
    if room_type == 'boss':
        return 'ultra'
    if room_type == 'elite':
        return 'common' if value < 0.40 else ('rare' if value < 0.90 else 'ultra')
    return 'common' if value < 0.70 else ('rare' if value < 0.95 else 'ultra')


def _reward_choices(state, seed, room_type='combat', count=3):
    rng = _rng(state, seed, f'card_reward:{room_type}')
    choices = []
    for _ in range(count):
        rarity = _reward_rarity(room_type, rng)
        pool = [
            card_id for card_id in STORY_REWARD_CARD_IDS
            if STORY_CARDS[card_id]['rarity'] == rarity
        ]
        if not pool:
            pool = list(STORY_REWARD_CARD_IDS)
        available = [card_id for card_id in pool if card_id not in choices] or pool
        card_id = rng.choice(available)
        upgraded_chance = {1: 0, 2: 0.25, 3: 0.5, 4: 1}.get(int(state.get('stage') or 1), 0)
        choices.append({'card_id': card_id, 'upgraded': rng.random() < upgraded_chance})
    return choices


def _random_relic(state, seed):
    owned = set(state['player'].get('relics', []))
    pool = [
        relic_id
        for relic_id, relic in STORY_RELICS.items()
        if relic_id not in owned and relic.get('rarity') != 'special'
    ]
    if not pool:
        return None
    rng = _rng(state, seed, 'relic_reward')
    roll = rng.random()
    rarity = 'common' if roll < 0.50 else ('rare' if roll < 0.83 else 'ultra')
    rarity_pool = [item for item in pool if STORY_RELICS[item].get('rarity') == rarity]
    return rng.choice(rarity_pool or pool)


def _gain_relic(state, relic_id, seed, events):
    if not relic_id or relic_id not in STORY_RELICS or relic_id in state['player']['relics']:
        return
    player = state['player']
    player['relics'].append(relic_id)
    relic = STORY_RELICS[relic_id]
    script = relic.get('script')
    amount = int(relic.get('amount') or 0)
    if script == 'gain_gold':
        player['gold'] += amount
    elif script == 'gain_max_health':
        player['max_health'] += amount
        player['health'] += amount
    elif script == 'gain_upgrade':
        candidates = [card for card in player['deck'] if not card.get('upgraded') and STORY_CARDS[card['def_id']].get('upgrade')]
        _rng(state, seed, 'relic_upgrade').shuffle(candidates)
        for card in candidates[:amount]:
            card['upgraded'] = True
    events.append({'type': 'relic_gained', 'relic_id': relic_id})


def _new_reward(gold, cards, relic, room_type):
    gold = max(0, int(gold or 0))
    cards = list(cards or [])
    return {
        'gold': gold,
        'cards': cards,
        'relic': relic,
        'room_type': room_type,
        'claims': {
            'gold': gold <= 0,
            'card': not cards,
            'relic': not bool(relic),
        },
        'selected_card_id': None,
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
    claims['relic'] = bool(claims.get('relic')) or not bool(reward.get('relic'))
    return claims


def _finish_combat(state, seed, events):
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
    rng = _rng(state, seed, 'combat_reward')
    if room_type == 'boss':
        gold = rng.randint(100, 120)
    elif room_type == 'elite':
        gold = rng.randint(25, 35)
    else:
        gold = rng.randint(10, 20)
        state['normal_battles'] = int(state.get('normal_battles') or 0) + 1
    for _, effect in _equipment_effects(state['combat'], 'victory_gold'):
        gold += int(effect.get('amount') or 0)
    if (
        room_type == 'combat'
        and _has_relic(state, 'indomitable')
        and int(state['combat'].get('damage_taken') or 0) > int(STORY_RELICS['indomitable']['amount'])
    ):
        candidates = [
            card for card in state['player']['deck']
            if not card.get('upgraded') and STORY_CARDS[card['def_id']].get('upgrade')
        ]
        if candidates:
            upgraded = _rng(state, seed, 'indomitable_upgrade').choice(candidates)
            upgraded['upgraded'] = True
            events.append({
                'type': 'card_upgraded',
                'card_instance_id': upgraded['instance_id'],
                'source': 'indomitable',
            })
    state['reward'] = _new_reward(
        gold,
        _reward_choices(state, seed, room_type),
        _random_relic(state, seed) if room_type == 'elite' else None,
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


def _resolve_enemy_death_hooks(state, events):
    combat = state.get('combat') or {}
    defeated = [
        enemy
        for enemy in list(combat.get('enemies', []))
        if int(enemy.get('health') or 0) <= 0
    ]
    newly_defeated = [
        enemy for enemy in defeated
        if not enemy.get('defeat_event_emitted')
    ]
    defeat_group = (
        f'enemy-defeat:{len(events)}'
        if len(newly_defeated) > 1
        else None
    )
    for enemy in newly_defeated:
        _emit_enemy_defeat(state, enemy, events, defeat_group)
    for enemy in defeated:
        if enemy.get('death_hook_resolved'):
            continue
        enemy['death_hook_resolved'] = True
        if STORY_ENEMIES[enemy['def_id']].get('script') == 'hive':
            _summon_enemy(
                state,
                'wasp',
                events,
                move_index=1,
                wither=4,
                actor_id=enemy['id'],
                source_definition_id=enemy['def_id'],
            )
            events.append({
                'type': 'enemy_death_trigger',
                'enemy_id': enemy['id'],
                'script': 'hive',
            })


def _check_combat_end(state, seed, events):
    combat = state.get('combat')
    if not combat:
        return False
    _resolve_enemy_death_hooks(state, events)
    if _resolve_player_death(state, events):
        return True
    if not _living_enemies(combat):
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
    if _has_relic(state, 'energetic'):
        _heal_player(state, int(STORY_RELICS['energetic']['amount']), events, source='energetic')
    for equipment in (state.get('combat') or {}).get('equipment', []):
        equipment.pop('turns_equipped', None)
    if int(node['floor']) >= int(state.get('map', {}).get('floor_count') or 16):
        if int(state.get('stage') or 1) < len(STORY_STAGES):
            next_stage = int(state.get('stage') or 1) + 1
            state['phase'] = 'stage_choice'
            state['room'] = {
                'type': 'stage_choice',
                'stage': next_stage,
                'biomes': list(STORY_STAGES[next_stage - 1]['biomes']),
            }
        else:
            state['phase'] = 'complete'
            state['completed'] = True
    else:
        _unlock_from_node(state, node['id'])
        state['phase'] = 'map'
        state['room'] = None
    state['combat'] = None
    state['reward'] = None
    state.pop('recovery_checkpoint', None)
    state['player']['elixir'] = int(state['player']['max_elixir'])
    events.append({'type': 'node_completed', 'node_id': node['id']})


def _complete_blessing_node(state):
    first = _node_lookup(state)[state['current_node_id']]
    first['status'] = 'completed'
    _unlock_from_node(state, first['id'])
    state['phase'] = 'map'
    state['room'] = None
    state['reward'] = None


def _record_blessing(player, blessing_id):
    history = player.get('blessings')
    if not isinstance(history, list):
        previous = str(player.get('blessing') or '')
        history = [previous] if previous else []
        player['blessings'] = history
    history.append(blessing_id)
    player['blessing'] = blessing_id


def _new_blessing_card_reward(state, seed, round_index, round_total):
    reward = _new_reward(
        0,
        _reward_choices(state, seed, 'blessing'),
        None,
        'blessing',
    )
    reward.update({
        'source': 'blessing',
        'round_index': int(round_index),
        'round_total': int(round_total),
    })
    return reward


def _choose_blessing(state, payload, seed, events):
    if state.get('phase') != 'blessing':
        _fail('NO_BLESSING_CHOICE', '当前不在赐福选择阶段')
    blessing_id = str(payload.get('blessing_id') or '')
    blessing = STORY_BLESSINGS.get(blessing_id)
    if not blessing:
        _fail('INVALID_BLESSING', '不存在该赐福')
    player = state['player']
    script = str(blessing.get('script') or '')
    amount = max(0, int(blessing.get('amount') or 0))

    if script in ('transform_card', 'remove_card'):
        card = _deck_card(player, payload)
        if script == 'remove_card':
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
    _complete_blessing_node(state)
    events.append({'type': 'blessing_chosen', 'blessing_id': blessing_id})


def _shop_price(state, base, rng, neutral=False):
    value = int(round(base * rng.uniform(0.9, 1.1)))
    if neutral:
        value = math.ceil(value * 1.2)
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
            card_id for card_id in STORY_REWARD_CARD_IDS
            if STORY_CARDS[card_id]['rarity'] == rarity and STORY_CARDS[card_id]['owner'] == owner
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
        pool = [
            relic_id for relic_id, relic in STORY_RELICS.items()
            if relic.get('rarity') == rarity and relic_id not in state['player']['relics']
        ]
        if pool:
            relics.append({
                'id': f'shop-relic-{len(relics)}',
                'relic_id': rng.choice(pool),
                'price': _shop_price(state, base, rng),
                'rarity': rarity,
                'base_price': base,
                'sold': False,
            })
    return {
        'type': 'shop',
        'options': ['buy_card', 'buy_relic', 'remove_card', 'upgrade_card', 'leave'],
        'cards': cards,
        'relics': relics,
        'remove_price': 75 + 25 * int(state.get('shop_removals') or 0),
        'upgrade_price': 75 + 25 * int(state.get('shop_upgrades') or 0),
    }


def _event_option(
    option_id,
    zh,
    en,
    description_zh='',
    description_en='',
    *,
    requires_confirmation=False,
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


def _make_story_event(state, seed):
    event_id = _rng(state, seed, 'story_event').choice((
        'creature_struggle',
        'mystery_lottery',
        'occultist',
        'ant_tools',
    ))
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
                    '获得1张无情。',
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
                _event_option('lottery_inspect', '观察机器构造', 'Inspect the Machine', '升级自己1张牌。'),
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
                    '获得标记，并将2张惊吓加入牌组。',
                    requires_confirmation=True,
                ),
                _event_option(
                    'occult_flee',
                    '被吓到并逃跑',
                    'Flee',
                    '将1张疲劳加入牌组。',
                    requires_confirmation=True,
                ),
            ],
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
                '获得80G与1张无情。',
                requires_confirmation=True,
            ),
            _event_option('leave', '离开', 'Leave'),
        ],
    )


def _enter_event_node(state, node, seed, events):
    streak = max(0, int(state.get('event_miss_streak') or 0))
    multiplier = min(5, streak + 1)
    roll = _rng(state, seed, 'event_room_type').random()
    conversions = (
        ('combat', 0.10 * multiplier),
        ('shop', 0.05 * multiplier),
        ('elite', 0.03 * multiplier),
        ('chest', 0.02 * multiplier),
    )
    cursor = 0.0
    converted = None
    for room_type, probability in conversions:
        cursor += probability
        if roll < cursor:
            converted = room_type
            break
    if converted in ('combat', 'elite'):
        state['event_miss_streak'] = 0
        _start_combat(state, {'type': converted}, seed, events)
        state['combat']['reward_room_type'] = converted
        events.append({'type': 'event_converted', 'room_type': converted})
        return
    if converted == 'shop':
        state['event_miss_streak'] = 0
        state['room'] = _make_shop(state, seed)
    elif converted == 'chest':
        state['event_miss_streak'] = 0
        state['room'] = {
            'type': 'chest',
            'options': ['claim'],
            'gold': _rng(state, seed, 'event_chest_gold').randint(40, 60),
            'relic': _random_relic(state, seed),
        }
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
    if node['type'] in ('combat', 'elite', 'boss'):
        _start_combat(state, node, seed, events)
        return
    if node['type'] == 'event':
        _enter_event_node(state, node, seed, events)
        return
    if node['type'] == 'rest':
        options = ['heal', 'upgrade']
        if _has_relic(state, 'greedy'):
            options.append('gold')
        if (
            not _has_relic(state, 'dandelion_blessing')
            and any(card.get('def_id') == 'dandelion_seed' for card in state['player']['deck'])
        ):
            options.append('plant_dandelion')
        room = {'type': 'rest', 'options': options}
    elif node['type'] == 'chest':
        room = {
            'type': 'chest',
            'options': ['claim'],
            'gold': _rng(state, seed, 'chest_gold').randint(40, 60),
            'relic': _random_relic(state, seed),
        }
    elif node['type'] == 'shop':
        room = _make_shop(state, seed)
    else:
        room = _make_story_event(state, seed)
    state['room'] = room
    state['phase'] = 'room'
    events.append({'type': 'room_entered', 'room_type': node['type']})


def _resolve_stage_choice(state, payload, seed, events):
    from story_mode import generate_story_map

    room = state.get('room') or {}
    biome = str(payload.get('biome') or '')
    if state.get('phase') != 'stage_choice' or biome not in room.get('biomes', []):
        _fail('INVALID_STAGE_CHOICE', '无法选择该区域')
    stage = int(room['stage'])
    _heal_player(
        state,
        int(state['player'].get('max_health') or 1),
        events,
        source='stage_transition',
    )
    state['stage'] = stage
    state['biome'] = biome
    state['map'] = generate_story_map(seed, stage, biome)
    first = state['map']['floors'][0]['nodes'][0]
    state['current_floor'] = 1
    state['current_node_id'] = first['id']
    state['room'] = None
    if stage == 2:
        state['phase'] = 'blessing'
    else:
        first['status'] = 'completed'
        _unlock_from_node(state, first['id'])
        state['phase'] = 'map'
    events.append({'type': 'stage_started', 'stage': stage, 'biome': biome})


def _restock_shop_item(state, item, seed, events, item_type):
    if not _has_relic(state, 'circulation'):
        return
    rng = _rng(state, seed, f'shop_restock:{item_type}')
    if item_type == 'card':
        rarity = item.get('rarity')
        owner = item.get('owner')
        pool = [
            card_id for card_id in STORY_REWARD_CARD_IDS
            if STORY_CARDS[card_id]['rarity'] == rarity
            and STORY_CARDS[card_id]['owner'] == owner
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
        pool = [
            relic_id for relic_id, relic in STORY_RELICS.items()
            if relic.get('rarity') == rarity
            and relic_id not in state['player']['relics']
        ]
        if not pool:
            return
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


def _upgrade_random_cards(state, count, seed, events, namespace):
    candidates = [
        card for card in state['player']['deck']
        if not card.get('upgraded') and STORY_CARDS[card['def_id']].get('upgrade')
    ]
    _rng(state, seed, namespace).shuffle(candidates)
    for card in candidates[:max(0, int(count))]:
        card['upgraded'] = True
        events.append({
            'type': 'card_upgraded',
            'card_instance_id': card['instance_id'],
            'source': namespace,
        })
    return len(candidates[:max(0, int(count))])


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
    option = str(payload.get('option') or '')
    player = state['player']
    if option not in _room_option_ids(room):
        _fail('INVALID_ROOM_OPTION', '无效的房间选项')
    complete = True
    if room['type'] == 'rest' and option == 'heal':
        _heal_player(state, math.ceil(int(player['max_health']) * 0.3), events, source='rest')
    elif room['type'] == 'rest' and option == 'upgrade':
        card = _deck_card(player, payload)
        if card.get('upgraded') or not STORY_CARDS[card['def_id']].get('upgrade'):
            _fail('CARD_NOT_UPGRADABLE', '请选择一张可升级的牌')
        card['upgraded'] = True
        events.append({'type': 'card_upgraded', 'card_instance_id': card['instance_id']})
    elif room['type'] == 'rest' and option == 'gold':
        player['gold'] += int(STORY_RELICS['greedy']['amount'])
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
        player['gold'] += int(room.get('gold') or 0)
        _gain_relic(state, room.get('relic'), seed, events)
        events.append({'type': 'chest_claimed'})
    elif room['type'] == 'event':
        event_id = room.get('event_id')
        if option in ('fight_help_spider', 'fight_help_yoba', 'fight_both'):
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
            if card.get('upgraded') or not STORY_CARDS[card['def_id']].get('upgrade'):
                _fail('CARD_NOT_UPGRADABLE', '请选择一张可升级的牌')
            card['upgraded'] = True
            events.append({'type': 'card_upgraded', 'card_instance_id': card['instance_id'], 'source': 'lottery_inspect'})
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
                result = {'zh': f'获得了{_localized(STORY_CARDS[card_id]["name"])}。', 'en': 'You won a Rare card.'}
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
            price_key = 'remove_price' if option == 'remove_card' else 'upgrade_price'
            _pay_gold(player, int(room[price_key]))
            card = _deck_card(player, payload)
            if option == 'remove_card':
                player['deck'].remove(card)
                state['shop_removals'] = int(state.get('shop_removals') or 0) + 1
            else:
                if card.get('upgraded') or not STORY_CARDS[card['def_id']].get('upgrade'):
                    _fail('CARD_NOT_UPGRADABLE', '请选择一张可升级的牌')
                card['upgraded'] = True
                state['shop_upgrades'] = int(state.get('shop_upgrades') or 0) + 1
            room[price_key] += 25
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
        relic_id = reward.get('relic')
        _gain_relic(state, relic_id, seed, events)
        claims['relic'] = True
        events.append({
            'type': 'reward_claimed',
            'reward_type': 'relic',
            'relic_id': relic_id,
        })

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
    elif reward_type == 'relic':
        claim_relic()
    elif reward_type == 'continue':
        if not all(claims.values()):
            _fail('REWARD_INCOMPLETE', '请先处理全部奖励')
        if reward.get('source') == 'blessing':
            round_index = max(1, int(reward.get('round_index') or 1))
            round_total = max(round_index, int(reward.get('round_total') or 1))
            if round_index < round_total:
                state['reward'] = _new_blessing_card_reward(
                    state,
                    seed,
                    round_index + 1,
                    round_total,
                )
                events.append({
                    'type': 'blessing_card_reward_started',
                    'round_index': round_index + 1,
                    'round_total': round_total,
                })
            else:
                _complete_blessing_node(state)
        else:
            _complete_current_node(state, events)
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
    payload = payload if isinstance(payload, dict) else {}
    events = []
    action_type = str(action_type or '').strip().lower()
    previous_phase = str(state.get('phase') or '')
    handlers = {
        'choose_blessing': lambda: _choose_blessing(state, payload, seed, events),
        'enter_node': lambda: _enter_node(state, payload, seed, events),
        'resume_node': lambda: _restore_recovery_checkpoint(state, events),
        'opening_redraw': lambda: _resolve_opening_redraw(state, payload, seed, events),
        'play_card': lambda: _play_card(state, payload, seed, events),
        'end_turn': lambda: _end_turn(state, seed, events),
        'choose_reward': lambda: _choose_reward(state, payload, seed, events),
        'resolve_room': lambda: _resolve_room(state, payload, seed, events),
        'choose_stage': lambda: _resolve_stage_choice(state, payload, seed, events),
        'dev_set_values': lambda: _dev_set_values(state, payload, events),
        'dev_jump_node': lambda: _dev_jump_node(state, payload, seed, events),
    }
    handler = handlers.get(action_type)
    if not handler:
        _fail('UNKNOWN_ACTION', '未知故事操作')
    handler()
    _refresh_combat_projections(state)
    phase = str(state.get('phase') or '')
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
        if checkpoint_kind:
            _capture_recovery_checkpoint(state, checkpoint_kind)
    else:
        state.pop('recovery_checkpoint', None)
    events = _finalize_story_events(state, events)
    state['last_events'] = events[-40:]
    return state, events
