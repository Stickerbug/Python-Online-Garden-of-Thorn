"""Server-authoritative story-mode state machine for the alpha vertical slice."""

import copy
import hashlib
import math
import random

from story_content import (
    STORY_BLESSINGS,
    STORY_CARDS,
    STORY_ENEMIES,
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


def _new_card(state, def_id, upgraded=False):
    if def_id not in STORY_CARDS:
        _fail('UNKNOWN_CARD', '未知故事卡牌')
    player = state['player']
    serial = int(player.get('next_card_serial') or 1)
    player['next_card_serial'] = serial + 1
    return {'instance_id': f'sc-{serial:04d}', 'def_id': def_id, 'upgraded': bool(upgraded)}


def _card_def(card):
    definition = STORY_CARDS.get(str(card.get('def_id') or ''))
    if not definition:
        _fail('UNKNOWN_CARD', '未知故事卡牌')
    return definition


def _card_values(card):
    definition = _card_def(card)
    values = dict(definition)
    if card.get('upgraded'):
        upgrade = definition.get('upgrade') or {}
        values.update({key: value for key, value in upgrade.items() if key != 'name'})
    return values


def _draw_cards(state, count, seed, events):
    combat = state['combat']
    drawn = []
    overflowed = []
    for _ in range(max(0, int(count))):
        if not combat['draw_pile']:
            if not combat['discard_pile']:
                break
            combat['draw_pile'] = combat['discard_pile']
            combat['discard_pile'] = []
            _rng(state, seed, 'reshuffle').shuffle(combat['draw_pile'])
        card = combat['draw_pile'].pop()
        if len(combat['hand']) >= int(STORY_RULES['hand_limit']):
            combat['discard_pile'].append(card)
            overflowed.append(card['instance_id'])
        else:
            combat['hand'].append(card)
            drawn.append(card['instance_id'])
    if drawn:
        events.append({'type': 'draw', 'count': len(drawn), 'card_instance_ids': drawn})
    if overflowed:
        events.append({
            'type': 'hand_overflow',
            'count': len(overflowed),
            'card_instance_ids': overflowed,
            'hand_limit': int(STORY_RULES['hand_limit']),
        })


def _damage_hits(amount, hits, power=0, weak=0, vulnerable=0, shield=0):
    """Simulate physical damage exactly as combat resolution applies it."""
    remaining_shield = max(0, int(shield))
    values = []
    for _ in range(max(1, int(hits))):
        value = max(0, int(amount) + int(power))
        if int(weak) > 0:
            value = math.floor(value * 0.75)
        if int(vulnerable) > 0:
            value = math.floor(value * 1.5)
        blocked = min(remaining_shield, value)
        remaining_shield -= blocked
        values.append(value - blocked)
    return values, remaining_shield


def _damage_summary(values):
    values = [max(0, int(value)) for value in values]
    if not values:
        return '0D'
    if len(values) > 1 and len(set(values)) == 1:
        return f'{values[0]}D×{len(values)}'
    if len(values) == 1:
        return f'{values[0]}D'
    return f"({' + '.join(str(value) for value in values)})D"


def _enemy_intent(state, enemy):
    definition = STORY_ENEMIES[enemy['def_id']]
    move = definition['moves'][int(enemy.get('move_index') or 0) % len(definition['moves'])]
    parts = []
    simulated_power = int(enemy.get('power') or 0)
    simulated_weak = int(enemy.get('weak') or 0)
    simulated_vulnerable = int(state.get('combat', {}).get('vulnerable') or 0)
    simulated_shield = int(state.get('combat', {}).get('shield') or 0)
    for effect in move['effects']:
        effect_type = effect['type']
        amount = int(effect.get('amount') or 0)
        hits = int(effect.get('hits') or 1)
        if effect_type == 'damage':
            values, simulated_shield = _damage_hits(
                amount,
                hits,
                power=simulated_power,
                weak=simulated_weak,
                vulnerable=simulated_vulnerable,
                shield=simulated_shield,
            )
            parts.append(_damage_summary(values))
        elif effect_type == 'self_damage':
            parts.append(f'自身受到{amount}D')
        elif effect_type == 'gain_power':
            simulated_power += amount
            parts.append(f'获得{amount}层力量')
        elif effect_type == 'gain_shield':
            parts.append(f'获得{amount}层护盾')
        elif effect_type == 'player_status':
            label = {'vulnerable': '易损', 'weak': '虚弱'}.get(effect.get('status'), effect.get('status'))
            parts.append(f'施加{amount}层{label}')
            if effect.get('status') == 'vulnerable':
                simulated_vulnerable += amount
    return {
        'name': move['name'],
        'summary': '；'.join(parts),
    }


def _card_damage_prediction(state, card, enemy):
    values = _card_values(card)
    if values.get('type') != 'thorn' or not enemy:
        return None
    combat = state['combat']
    simulated_power = int(combat.get('power') or 0)
    simulated_weak = int(combat.get('weak') or 0)
    simulated_vulnerable = int(enemy.get('vulnerable') or 0)
    simulated_shield = int(enemy.get('shield') or 0)
    predicted_hits = []
    for effect in values.get('effects') or ():
        effect_type = effect.get('type')
        amount = int(effect.get('amount') or 0)
        if effect_type == 'damage':
            hit_values, simulated_shield = _damage_hits(
                amount,
                int(effect.get('hits') or 1),
                power=simulated_power,
                weak=simulated_weak,
                vulnerable=simulated_vulnerable,
                shield=simulated_shield,
            )
            predicted_hits.extend(hit_values)
        elif effect_type == 'power':
            simulated_power += amount
        elif effect_type == 'enemy_status' and effect.get('status') == 'vulnerable':
            simulated_vulnerable += amount
    if not predicted_hits:
        return None
    return {
        'total': sum(predicted_hits),
        'hits': predicted_hits,
        'summary': _damage_summary(predicted_hits),
    }


def _refresh_combat_projections(state):
    combat = state.get('combat')
    if not isinstance(combat, dict):
        return
    living_enemy = next(
        (enemy for enemy in combat.get('enemies', []) if int(enemy.get('health') or 0) > 0),
        None,
    )
    combat['damage_predictions'] = {
        card['instance_id']: prediction
        for card in combat.get('hand', [])
        if (prediction := _card_damage_prediction(state, card, living_enemy)) is not None
    }
    for enemy in combat.get('enemies', []):
        enemy['intent'] = _enemy_intent(state, enemy)


def _start_combat(state, node, seed, events):
    room_type = node['type']
    if room_type == 'boss':
        enemy_id = 'digger'
    elif room_type == 'elite':
        enemy_id = 'spider_yuba'
    elif int(state.get('normal_battles') or 0) >= 3:
        enemy_id = 'veteran_ant'
    else:
        enemy_id = 'soldier_ant'
    definition = STORY_ENEMIES[enemy_id]
    draw_pile = copy.deepcopy(state['player']['deck'])
    _rng(state, seed, 'combat_start').shuffle(draw_pile)
    state['combat'] = {
        'round': 1,
        'turn': 'player',
        'elixir': int(state['player']['max_elixir']),
        'magic': int(state['player']['magic']),
        'shield': 0,
        'power': 0,
        'weak': 0,
        'vulnerable': 0,
        'draw_pile': draw_pile,
        'hand': [],
        'discard_pile': [],
        'exile_pile': [],
        'enemies': [{
            'id': 'enemy-1',
            'def_id': enemy_id,
            'name': definition['name'],
            'health': int(definition['max_health']),
            'max_health': int(definition['max_health']),
            'shield': 0,
            'power': 0,
            'weak': 0,
            'vulnerable': 0,
            'move_index': 0,
        }],
    }
    state['phase'] = 'combat'
    draw_count = STORY_RULES['draw_per_turn'] + int(state['player'].get('opening_draw_bonus') or 0)
    _draw_cards(state, draw_count, seed, events)
    _refresh_combat_projections(state)
    events.append({'type': 'combat_start', 'enemy_id': enemy_id})


def _player_damage(state, amount, hits, events, source, attacker_id=None):
    combat = state['combat']
    total = 0
    history = []
    predicted, _ = _damage_hits(
        amount,
        hits,
        vulnerable=combat.get('vulnerable'),
        shield=combat.get('shield'),
    )
    for dealt in predicted:
        value = max(0, int(amount))
        if int(combat.get('vulnerable') or 0) > 0:
            value = math.floor(value * 1.5)
        blocked = value - dealt
        combat['shield'] = max(0, int(combat.get('shield') or 0) - blocked)
        before = int(state['player']['health'])
        state['player']['health'] = max(0, before - dealt)
        total += dealt
        history.append({'before': before, 'after': state['player']['health'], 'blocked': blocked})
    events.append({
        'type': 'player_damage',
        'amount': total,
        'hits': hits,
        'history': history,
        'source': source,
        'attacker_id': attacker_id,
    })


def _enemy_damage(state, enemy, amount, hits, events, source):
    combat = state['combat']
    total = 0
    history = []
    predicted, _ = _damage_hits(
        amount,
        hits,
        power=combat.get('power'),
        weak=combat.get('weak'),
        vulnerable=enemy.get('vulnerable'),
        shield=enemy.get('shield'),
    )
    for dealt in predicted:
        value = max(0, int(amount) + int(combat.get('power') or 0))
        if int(combat.get('weak') or 0) > 0:
            value = math.floor(value * 0.75)
        if int(enemy.get('vulnerable') or 0) > 0:
            value = math.floor(value * 1.5)
        blocked = value - dealt
        enemy['shield'] = max(0, int(enemy.get('shield') or 0) - blocked)
        before = int(enemy['health'])
        enemy['health'] = max(0, before - dealt)
        total += dealt
        history.append({'before': before, 'after': enemy['health'], 'blocked': blocked})
    events.append({'type': 'enemy_damage', 'enemy_id': enemy['id'], 'amount': total, 'hits': hits, 'history': history})


def _reward_choices(state, seed):
    pool = list(STORY_REWARD_CARD_IDS)
    rng = _rng(state, seed, 'card_reward')
    rng.shuffle(pool)
    return pool[:3]


def _finish_combat(state, seed, events):
    node = _node_lookup(state)[state['current_node_id']]
    room_type = node['type']
    rng = _rng(state, seed, 'combat_reward')
    if room_type == 'boss':
        gold = rng.randint(100, 120)
    elif room_type == 'elite':
        gold = rng.randint(25, 35)
    else:
        gold = rng.randint(10, 20)
        state['normal_battles'] = int(state.get('normal_battles') or 0) + 1
    state['player']['gold'] += gold
    state['reward'] = {
        'gold': gold,
        'cards': _reward_choices(state, seed),
        'relic': 'energetic' if room_type in ('elite', 'boss') else None,
        'room_type': room_type,
    }
    state['phase'] = 'reward'
    events.append({'type': 'combat_victory', 'gold': gold})


def _check_combat_end(state, seed, events):
    combat = state['combat']
    if not any(int(enemy.get('health') or 0) > 0 for enemy in combat.get('enemies', [])):
        _finish_combat(state, seed, events)
        return True
    if int(state['player'].get('health') or 0) <= 0:
        state['phase'] = 'game_over'
        events.append({'type': 'game_over'})
        return True
    return False


def _play_card(state, payload, seed, events):
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
    cost_e = int(values.get('cost_e') or 0)
    cost_m = int(values.get('cost_m') or 0)
    if combat['elixir'] < cost_e or combat['magic'] < cost_m:
        _fail('INSUFFICIENT_RESOURCE', '资源不足')
    enemy = next((item for item in combat['enemies'] if int(item.get('health') or 0) > 0), None)
    if values.get('type') == 'thorn' and not enemy:
        _fail('NO_TARGET', '没有可选中的敌人')
    combat['elixir'] -= cost_e
    combat['magic'] -= cost_m
    card_name = _localized(values.get('name'))
    combat['hand'].remove(card)
    events.append({'type': 'card_played', 'card_instance_id': instance_id, 'def_id': card['def_id']})
    for effect in values.get('effects') or ():
        effect_type = effect.get('type')
        amount = int(effect.get('amount') or 0)
        hits = int(effect.get('hits') or 1)
        if effect_type == 'damage':
            _enemy_damage(state, enemy, amount, hits, events, card_name)
        elif effect_type == 'shield':
            combat['shield'] += amount
            events.append({'type': 'shield', 'amount': amount})
        elif effect_type == 'elixir':
            combat['elixir'] += amount
            events.append({'type': 'elixir', 'amount': amount})
        elif effect_type == 'power':
            combat['power'] += amount
        elif effect_type == 'enemy_status':
            status = str(effect.get('status') or '')
            enemy[status] = int(enemy.get(status) or 0) + amount
    destination = combat['exile_pile'] if values.get('exile') else combat['discard_pile']
    destination.append(card)
    _check_combat_end(state, seed, events)


def _enemy_turn(state, seed, events):
    combat = state['combat']
    combat['turn'] = 'enemy'
    for enemy in combat['enemies']:
        if int(enemy.get('health') or 0) <= 0:
            continue
        enemy['shield'] = 0
        definition = STORY_ENEMIES[enemy['def_id']]
        move_index = int(enemy.get('move_index') or 0) % len(definition['moves'])
        move = definition['moves'][move_index]
        events.append({'type': 'enemy_action', 'enemy_id': enemy['id'], 'move_index': move_index})
        for effect in move['effects']:
            effect_type = effect['type']
            amount = int(effect.get('amount') or 0)
            hits = int(effect.get('hits') or 1)
            if effect_type == 'damage':
                value = max(0, amount + int(enemy.get('power') or 0))
                if int(enemy.get('weak') or 0) > 0:
                    value = math.floor(value * 0.75)
                _player_damage(state, value, hits, events, _localized(move['name']), enemy.get('id'))
            elif effect_type == 'self_damage':
                before = int(enemy['health'])
                enemy['health'] = max(0, before - amount)
                events.append({
                    'type': 'enemy_self_damage',
                    'enemy_id': enemy['id'],
                    'amount': before - int(enemy['health']),
                })
            elif effect_type == 'gain_power':
                enemy['power'] += amount
                events.append({
                    'type': 'enemy_gain',
                    'enemy_id': enemy['id'],
                    'kind': 'power',
                    'amount': amount,
                })
            elif effect_type == 'gain_shield':
                enemy['shield'] += amount
                events.append({
                    'type': 'enemy_gain',
                    'enemy_id': enemy['id'],
                    'kind': 'shield',
                    'amount': amount,
                })
            elif effect_type == 'player_status':
                status = str(effect.get('status') or '')
                combat[status] = int(combat.get(status) or 0) + amount
        enemy['move_index'] = (move_index + 1) % len(definition['moves'])
        if _check_combat_end(state, seed, events):
            return
    combat['shield'] = 0
    combat['weak'] = max(0, int(combat.get('weak') or 0) - 1)
    combat['vulnerable'] = max(0, int(combat.get('vulnerable') or 0) - 1)
    for enemy in combat['enemies']:
        enemy['weak'] = max(0, int(enemy.get('weak') or 0) - 1)
        enemy['vulnerable'] = max(0, int(enemy.get('vulnerable') or 0) - 1)
    combat['round'] += 1
    combat['turn'] = 'player'
    combat['elixir'] = int(state['player']['max_elixir'])
    combat['magic'] = int(state['player']['magic'])
    _draw_cards(state, STORY_RULES['draw_per_turn'], seed, events)
    _refresh_combat_projections(state)


def _end_turn(state, seed, events):
    if state.get('phase') != 'combat' or state.get('combat', {}).get('turn') != 'player':
        _fail('END_TURN_NOT_ALLOWED', '当前不能结束回合')
    combat = state['combat']
    if combat['hand']:
        combat['discard_pile'].extend(combat['hand'])
        combat['hand'] = []
    events.append({'type': 'turn_ended'})
    _enemy_turn(state, seed, events)


def _unlock_from_node(state, node_id):
    nodes = _node_lookup(state)
    for target_id in _outgoing_node_ids(state, node_id):
        if target_id in nodes:
            nodes[target_id]['status'] = 'available'


def _complete_current_node(state, events):
    nodes = _node_lookup(state)
    node = nodes[state['current_node_id']]
    node['status'] = 'completed'
    if 'energetic' in state['player'].get('relics', []):
        before = int(state['player']['health'])
        state['player']['health'] = min(int(state['player']['max_health']), before + 4)
        events.append({'type': 'heal', 'amount': state['player']['health'] - before})
    if int(node['floor']) >= int(state.get('map', {}).get('floor_count') or 16):
        state['phase'] = 'complete'
        state['completed'] = True
    else:
        _unlock_from_node(state, node['id'])
        state['phase'] = 'map'
    state['combat'] = None
    state['reward'] = None
    state['room'] = None
    state['player']['elixir'] = int(state['player']['max_elixir'])
    events.append({'type': 'node_completed', 'node_id': node['id']})


def _choose_blessing(state, payload, events):
    if state.get('phase') != 'blessing':
        _fail('NO_BLESSING_CHOICE', '当前不在赐福选择阶段')
    blessing_id = str(payload.get('blessing_id') or '')
    if blessing_id not in STORY_BLESSINGS:
        _fail('INVALID_BLESSING', '不存在该赐福')
    player = state['player']
    player['blessing'] = blessing_id
    if blessing_id == 'titan':
        player['max_health'] += 20
        player['health'] = min(player['max_health'], player['health'] + 20)
    elif blessing_id == 'oracle':
        player['opening_draw_bonus'] = 1
    first = _node_lookup(state)[state['current_node_id']]
    first['status'] = 'completed'
    _unlock_from_node(state, first['id'])
    state['phase'] = 'map'
    events.append({'type': 'blessing_chosen', 'blessing_id': blessing_id})


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
    if node['type'] == 'rest':
        room = {'type': 'rest', 'options': ['heal', 'upgrade']}
    elif node['type'] == 'chest':
        room = {'type': 'chest', 'options': ['claim']}
    elif node['type'] == 'shop':
        choices = _reward_choices(state, seed)[:2]
        room = {'type': 'shop', 'options': ['buy_card', 'heal', 'leave'], 'cards': choices, 'card_price': 50, 'heal_price': 30}
    else:
        room = {'type': 'event', 'options': ['gold', 'heal']}
    state['room'] = room
    state['phase'] = 'room'
    events.append({'type': 'room_entered', 'room_type': node['type']})


def _resolve_room(state, payload, events):
    if state.get('phase') != 'room' or not state.get('room'):
        _fail('NO_ROOM_CHOICE', '当前没有房间选项')
    room = state['room']
    option = str(payload.get('option') or '')
    player = state['player']
    if option not in room.get('options', []):
        _fail('INVALID_ROOM_OPTION', '无效的房间选项')
    if room['type'] == 'rest' and option == 'heal':
        amount = math.ceil(int(player['max_health']) * 0.3)
        before = int(player['health'])
        player['health'] = min(int(player['max_health']), before + amount)
        events.append({'type': 'heal', 'amount': player['health'] - before})
    elif room['type'] == 'rest' and option == 'upgrade':
        instance_id = str(payload.get('card_instance_id') or '')
        card = next((item for item in player['deck'] if item['instance_id'] == instance_id), None)
        if not card or card.get('upgraded'):
            _fail('CARD_NOT_UPGRADABLE', '请选择一张未升级卡牌')
        card['upgraded'] = True
        events.append({'type': 'card_upgraded', 'card_instance_id': instance_id})
    elif room['type'] == 'chest':
        player['gold'] += 50
        if 'energetic' not in player['relics']:
            player['relics'].append('energetic')
        else:
            player['gold'] += 50
        events.append({'type': 'chest_claimed'})
    elif room['type'] == 'event':
        if option == 'gold':
            player['gold'] += 20
            events.append({'type': 'gold', 'amount': 20})
        else:
            before = int(player['health'])
            player['health'] = min(int(player['max_health']), before + 15)
            events.append({'type': 'heal', 'amount': player['health'] - before})
    elif room['type'] == 'shop':
        if option == 'buy_card':
            def_id = str(payload.get('card_id') or '')
            if def_id not in room.get('cards', []):
                _fail('INVALID_SHOP_CARD', '商店中没有这张牌')
            price = int(room.get('card_price') or 50)
            if player['gold'] < price:
                _fail('NOT_ENOUGH_GOLD', '荆露不足')
            player['gold'] -= price
            player['deck'].append(_new_card(state, def_id))
        elif option == 'heal':
            price = int(room.get('heal_price') or 30)
            if player['gold'] < price:
                _fail('NOT_ENOUGH_GOLD', '荆露不足')
            player['gold'] -= price
            player['health'] = min(int(player['max_health']), int(player['health']) + 20)
    _complete_current_node(state, events)


def _choose_reward(state, payload, events):
    if state.get('phase') != 'reward' or not state.get('reward'):
        _fail('NO_REWARD', '当前没有待领取奖励')
    reward = state['reward']
    card_id = str(payload.get('card_id') or '')
    if card_id:
        if card_id not in reward.get('cards', []):
            _fail('INVALID_REWARD_CARD', '奖励中没有这张牌')
        state['player']['deck'].append(_new_card(state, card_id))
        events.append({'type': 'card_gained', 'card_id': card_id})
    relic_id = reward.get('relic')
    if relic_id and relic_id in STORY_RELICS:
        if relic_id not in state['player']['relics']:
            state['player']['relics'].append(relic_id)
        else:
            state['player']['gold'] += 50
    _complete_current_node(state, events)


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
        'elixir': 9999,
        'magic': 9999,
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
    if 'health' in values:
        player['health'] = values['health']
    if 'elixir' in values:
        player['elixir'] = values['elixir']
    if 'magic' in values:
        player['magic'] = values['magic']
    if 'gold' in values:
        player['gold'] = values['gold']

    combat = state.get('combat')
    if isinstance(combat, dict):
        if 'elixir' in values:
            combat['elixir'] = values['elixir']
        if 'magic' in values:
            combat['magic'] = values['magic']
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
    events.append({
        'type': 'dev_node_jump',
        'node_id': node_id,
        'floor': target_floor,
        'room_type': target.get('type'),
    })
    _enter_node(state, {'node_id': node_id}, seed, events)


def apply_story_action(source_state, action_type, payload, seed):
    state = copy.deepcopy(source_state or {})
    combat = state.get('combat')
    if isinstance(combat, dict):
        combat.pop('log', None)
    payload = payload if isinstance(payload, dict) else {}
    events = []
    action_type = str(action_type or '').strip().lower()
    handlers = {
        'choose_blessing': lambda: _choose_blessing(state, payload, events),
        'enter_node': lambda: _enter_node(state, payload, seed, events),
        'play_card': lambda: _play_card(state, payload, seed, events),
        'end_turn': lambda: _end_turn(state, seed, events),
        'choose_reward': lambda: _choose_reward(state, payload, events),
        'resolve_room': lambda: _resolve_room(state, payload, events),
        'dev_set_values': lambda: _dev_set_values(state, payload, events),
        'dev_jump_node': lambda: _dev_jump_node(state, payload, seed, events),
    }
    handler = handlers.get(action_type)
    if not handler:
        _fail('UNKNOWN_ACTION', '未知故事操作')
    handler()
    _refresh_combat_projections(state)
    state['last_events'] = events[-20:]
    return state, events
