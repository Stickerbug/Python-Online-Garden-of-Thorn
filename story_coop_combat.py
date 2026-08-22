"""Deterministic cooperative-story combat coordination.

This module owns only the multiplayer coordination boundary: authenticated
actor resolution, accepted-action ordering, hero readiness, deterministic
enemy targets, party defeat and post-combat revival.  Card and enemy content
resolvers remain separate so unsupported single-player rules cannot silently
run against a multiplayer state.
"""

from copy import deepcopy
import hashlib
import json
import math
import re

from story_coop import story_seat_for_user, validate_story_state_v10


COOP_COMBAT_HERO_TURN = 'heroes'
COOP_COMBAT_ENEMY_TURN = 'enemies'
COOP_COMBAT_ENDED = 'ended'
COOP_COMBAT_REVIVE_RATIO = 0.20

_COMBAT_ID_RE = re.compile(r'^[A-Za-z0-9._:-]{1,96}$')
_ACTION_ID_RE = re.compile(r'^[A-Za-z0-9._:-]{8,128}$')
_ACTION_TYPE_RE = re.compile(r'^[a-z][a-z0-9_]{0,63}$')
_REQUEST_FINGERPRINT_RE = re.compile(r'^[0-9a-f]{64}$')
_ACTION_RECEIPT_FIELDS = frozenset({
    'action_id',
    'actor_user_id',
    'actor_seat',
    'action_type',
    'combat_id',
    'combat_round',
    'action_sequence',
    'request_fingerprint',
})


class CoopCombatError(ValueError):
    """Stable pure-engine failure suitable for transport error mapping."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)


def _fail(code, message):
    raise CoopCombatError(code, message)


def _strict_int(value, *, code, label, minimum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(code, f'{label}必须是整数')
    if minimum is not None and value < minimum:
        _fail(code, f'{label}不能小于 {minimum}')
    return value


def _normalize_combat_id(value):
    combat_id = str(value or '').strip()
    if not _COMBAT_ID_RE.fullmatch(combat_id):
        _fail('INVALID_COMBAT_ID', '协作战斗标识无效')
    return combat_id


def _normalize_action_id(value):
    action_id = str(value or '').strip()
    if not _ACTION_ID_RE.fullmatch(action_id):
        _fail('INVALID_ACTION_ID', '协作动作标识无效')
    return action_id


def _normalize_action_type(value):
    action_type = str(value or '').strip().lower()
    if not _ACTION_TYPE_RE.fullmatch(action_type):
        _fail('INVALID_ACTION_TYPE', '协作战斗动作类型无效')
    return action_type


def _living_seats(state):
    return [
        int(member['seat'])
        for member in state['party']['members']
        if int(state['players'][str(member['seat'])].get('health') or 0) > 0
    ]


def _living_enemies(state):
    return [
        enemy
        for enemy in state['combat']['enemies']
        if int(enemy.get('health') or 0) > 0
    ]


def _default_seat_state(player):
    return {
        'elixir': max(0, int(player.get('max_elixir') or player.get('elixir') or 0)),
        'magic': max(0, int(player.get('magic') or 0)),
        'shield': 0,
        'statuses': {},
        'hand': [],
        'draw_pile': deepcopy(player.get('deck') or []),
        'discard_pile': [],
        'exile_pile': [],
        'equipment': [],
    }


def _validate_seat_state(seat_key, seat_state):
    if not isinstance(seat_state, dict):
        _fail('INVALID_SEAT_STATES', f'席位 {seat_key} 的战斗状态无效')
    for field, label in (('elixir', '灵药'), ('magic', '魔法'), ('shield', '护盾')):
        _strict_int(
            seat_state.get(field),
            code='INVALID_SEAT_STATES',
            label=f'席位 {seat_key} 的{label}',
            minimum=0,
        )
    if not isinstance(seat_state.get('statuses'), dict):
        _fail('INVALID_SEAT_STATES', f'席位 {seat_key} 的状态集无效')
    for zone in ('hand', 'draw_pile', 'discard_pile', 'exile_pile', 'equipment'):
        if not isinstance(seat_state.get(zone), list):
            _fail('INVALID_SEAT_STATES', f'席位 {seat_key} 的 {zone} 区域无效')


def _normalize_seat_states(state, seat_states):
    player_keys = set(state['players'])
    if seat_states is None:
        return {
            seat_key: _default_seat_state(state['players'][seat_key])
            for seat_key in sorted(player_keys, key=int)
        }
    if not isinstance(seat_states, dict) or set(seat_states) != player_keys:
        _fail('INVALID_SEAT_STATES', '战斗席位私有区与队伍席位不一致')
    normalized = deepcopy(seat_states)
    for seat_key, seat_state in normalized.items():
        _validate_seat_state(seat_key, seat_state)
    return normalized


def _normalize_intent(intent):
    if intent is None:
        intent = {'kind': 'idle'}
    if not isinstance(intent, dict):
        _fail('INVALID_ENEMY_INTENT', '敌人意图无效')
    normalized = deepcopy(intent)
    kind = str(normalized.get('kind') or 'idle').strip().lower()
    if kind not in {'attack', 'attack_all', 'idle'}:
        _fail('UNSUPPORTED_ENEMY_INTENT', f'暂不支持敌人意图 {kind}')
    normalized['kind'] = kind
    if kind in {'attack', 'attack_all'}:
        amount = normalized.get('amount', 0)
        hits = normalized.get('hits', 1)
        _strict_int(amount, code='INVALID_ENEMY_INTENT', label='敌人伤害', minimum=0)
        _strict_int(hits, code='INVALID_ENEMY_INTENT', label='敌人攻击次数', minimum=1)
        normalized['amount'] = amount
        normalized['hits'] = hits
    if kind != 'attack':
        normalized.pop('target_seat', None)
    return normalized


def _normalize_enemies(enemies):
    if not isinstance(enemies, (list, tuple)) or not enemies:
        _fail('INVALID_ENEMIES', '协作战斗至少需要一个敌人')
    normalized = []
    seen_ids = set()
    for raw_enemy in enemies:
        if not isinstance(raw_enemy, dict):
            _fail('INVALID_ENEMY', '敌人状态无效')
        enemy = deepcopy(raw_enemy)
        enemy_id = str(enemy.get('id') or '').strip()
        if not _COMBAT_ID_RE.fullmatch(enemy_id) or enemy_id in seen_ids:
            _fail('INVALID_ENEMY_ID', '敌人标识无效或重复')
        seen_ids.add(enemy_id)
        max_health = enemy.get('max_health')
        health = enemy.get('health', max_health)
        _strict_int(max_health, code='INVALID_ENEMY_HEALTH', label='敌人最大生命', minimum=1)
        _strict_int(health, code='INVALID_ENEMY_HEALTH', label='敌人生命', minimum=0)
        if health > max_health:
            _fail('INVALID_ENEMY_HEALTH', '敌人生命不能超过最大生命')
        enemy['id'] = enemy_id
        enemy['max_health'] = max_health
        enemy['health'] = health
        enemy['intent'] = _normalize_intent(enemy.get('intent'))
        normalized.append(enemy)
    return normalized


def _validate_action_receipts(state):
    coordination = state['coordination']
    receipts = coordination.get('action_receipts')
    if not isinstance(receipts, dict):
        _fail('INVALID_ACTION_RECEIPTS', '协作战斗动作回执无效')
    current_sequence = coordination.get('action_sequence')
    member_seats = {
        member['user_id']: member['seat']
        for member in state['party']['members']
    }
    seen_sequences = set()
    for receipt_key, receipt in receipts.items():
        if (
            not isinstance(receipt_key, str)
            or not isinstance(receipt, dict)
            or set(receipt) != _ACTION_RECEIPT_FIELDS
        ):
            _fail('INVALID_ACTION_RECEIPTS', '协作战斗动作回执结构无效')
        action_id = receipt['action_id']
        actor_user_id = receipt['actor_user_id']
        actor_seat = receipt['actor_seat']
        action_type = receipt['action_type']
        combat_id = receipt['combat_id']
        combat_round = receipt['combat_round']
        action_sequence = receipt['action_sequence']
        request_fingerprint = receipt['request_fingerprint']
        if not isinstance(action_id, str) or not _ACTION_ID_RE.fullmatch(action_id):
            _fail('INVALID_ACTION_RECEIPTS', '协作战斗动作回执标识无效')
        if isinstance(actor_user_id, bool) or not isinstance(actor_user_id, int):
            _fail('INVALID_ACTION_RECEIPTS', '协作战斗动作回执账号无效')
        if isinstance(actor_seat, bool) or not isinstance(actor_seat, int):
            _fail('INVALID_ACTION_RECEIPTS', '协作战斗动作回执席位无效')
        if member_seats.get(actor_user_id) != actor_seat:
            _fail('INVALID_ACTION_RECEIPTS', '协作战斗动作回执行动者与队伍不一致')
        if receipt_key != f'{actor_user_id}:{action_id}':
            _fail('INVALID_ACTION_RECEIPTS', '协作战斗动作回执键无效')
        if (
            not isinstance(action_type, str)
            or not _ACTION_TYPE_RE.fullmatch(action_type)
        ):
            _fail('INVALID_ACTION_RECEIPTS', '协作战斗动作回执类型无效')
        if (
            not isinstance(combat_id, str)
            or not _COMBAT_ID_RE.fullmatch(combat_id)
            or combat_id != combat_id.strip()
        ):
            _fail('INVALID_ACTION_RECEIPTS', '协作战斗动作回执战斗标识无效')
        if (
            isinstance(combat_round, bool)
            or not isinstance(combat_round, int)
            or combat_round < 1
        ):
            _fail('INVALID_ACTION_RECEIPTS', '协作战斗动作回执回合无效')
        if (
            isinstance(action_sequence, bool)
            or not isinstance(action_sequence, int)
            or action_sequence < 1
            or action_sequence > current_sequence
            or action_sequence in seen_sequences
        ):
            _fail('INVALID_ACTION_RECEIPTS', '协作战斗动作回执序号无效')
        seen_sequences.add(action_sequence)
        if (
            not isinstance(request_fingerprint, str)
            or not _REQUEST_FINGERPRINT_RE.fullmatch(request_fingerprint)
        ):
            _fail('INVALID_ACTION_RECEIPTS', '协作战斗动作回执指纹无效')


def _seeded_choice(state, run_seed, namespace, options):
    if not options:
        _fail('NO_LIVING_TARGET', '没有可用的存活席位')
    streams = state.setdefault('rng_streams', {})
    if not isinstance(streams, dict):
        _fail('INVALID_RNG_STATE', '故事随机流状态无效')
    counter = streams.get(namespace, 0)
    _strict_int(counter, code='INVALID_RNG_STATE', label='随机流计数', minimum=0)
    streams[namespace] = counter + 1
    material = f'{run_seed}|{namespace}|{counter}'.encode('utf-8')
    index = int.from_bytes(hashlib.sha256(material).digest()[:8], 'big') % len(options)
    return options[index]


def _fallback_target_seat(original_seat, living_seats):
    if not living_seats:
        return None
    ordered = sorted(living_seats)
    for seat in ordered:
        if seat > original_seat:
            return seat
    return ordered[0]


def _lock_enemy_targets(state, run_seed, events):
    living = _living_seats(state)
    if not living:
        return
    combat = state['combat']
    for enemy in _living_enemies(state):
        intent = enemy.get('intent') or {}
        if intent.get('kind') != 'attack':
            continue
        original = intent.get('target_seat')
        if original is None:
            target = _seeded_choice(
                state,
                run_seed,
                f'coop_enemy_target:{combat["id"]}:{combat["round"]}:{enemy["id"]}',
                living,
            )
            intent['target_seat'] = target
            events.append({
                'type': 'enemy_target_locked',
                'enemy_id': enemy['id'],
                'target_seat': target,
                'round': combat['round'],
            })
            continue
        if isinstance(original, bool) or not isinstance(original, int):
            _fail('INVALID_ENEMY_TARGET', '敌人目标席位无效')
        all_seats = {int(key) for key in state['players']}
        if original not in all_seats:
            _fail('INVALID_ENEMY_TARGET', '敌人目标席位不存在')
        if original in living:
            continue
        target = _fallback_target_seat(original, living)
        intent['target_seat'] = target
        events.append({
            'type': 'enemy_target_reassigned',
            'enemy_id': enemy['id'],
            'original_target_seat': original,
            'target_seat': target,
            'round': combat['round'],
        })


def _finalize_events(events, action_sequence):
    finalized = []
    for event_index, raw_event in enumerate(events):
        event = deepcopy(raw_event)
        event['action_sequence'] = action_sequence
        event['event_index'] = event_index
        finalized.append(event)
    return finalized


def initialize_coop_combat(source_state, *, combat_id, enemies, run_seed, seat_states=None):
    """Start a deterministic headless cooperative combat without mutating input."""

    validate_story_state_v10(source_state, expected_mode='coop')
    if source_state.get('combat') is not None or source_state.get('phase') in {'combat', 'game_over'}:
        _fail('COMBAT_ALREADY_ACTIVE', '协作战斗已经开始或旅程已经结束')
    state = deepcopy(source_state)
    combat_id = _normalize_combat_id(combat_id)
    for seat_key, player in state['players'].items():
        if not isinstance(player, dict):
            _fail('INVALID_PLAYER_STATE', f'席位 {seat_key} 的玩家状态无效')
        max_health = player.get('max_health')
        health = player.get('health')
        _strict_int(max_health, code='INVALID_PLAYER_HEALTH', label='玩家最大生命', minimum=1)
        _strict_int(health, code='INVALID_PLAYER_HEALTH', label='玩家生命', minimum=0)
        if health > max_health:
            _fail('INVALID_PLAYER_HEALTH', '玩家生命不能超过最大生命')
    if not _living_seats(state):
        _fail('PARTY_ALREADY_DEFEATED', '所有队伍成员均已倒地')
    state['phase'] = 'combat'
    state['combat'] = {
        'id': combat_id,
        'round': 1,
        'turn': COOP_COMBAT_HERO_TURN,
        'outcome': None,
        'seat_states': _normalize_seat_states(state, seat_states),
        'enemies': _normalize_enemies(enemies),
    }
    if not _living_enemies(state):
        _fail('NO_LIVING_ENEMIES', '协作战斗至少需要一个存活敌人')
    coordination = state['coordination']
    coordination['combat_ready_seats'] = []
    coordination['combat_ready_round'] = 1
    events = [{'type': 'coop_combat_started', 'combat_id': combat_id, 'round': 1}]
    _lock_enemy_targets(state, run_seed, events)
    validate_coop_combat_state(state)
    return state, _finalize_events(events, coordination['action_sequence'])


def validate_coop_combat_state(state):
    """Validate multiplayer combat invariants on a persisted transaction state."""

    validate_story_state_v10(state, expected_mode='coop')
    combat = state.get('combat')
    if not isinstance(combat, dict):
        _fail('INVALID_COMBAT_STATE', '协作战斗状态无效')
    stored_combat_id = combat.get('id')
    normalized_combat_id = _normalize_combat_id(stored_combat_id)
    if stored_combat_id != normalized_combat_id:
        _fail('INVALID_COMBAT_ID', '协作战斗标识必须以规范字符串存储')
    round_number = combat.get('round')
    _strict_int(round_number, code='INVALID_COMBAT_ROUND', label='战斗回合', minimum=1)
    turn = str(combat.get('turn') or '')
    if turn not in {COOP_COMBAT_HERO_TURN, COOP_COMBAT_ENEMY_TURN, COOP_COMBAT_ENDED}:
        _fail('INVALID_COMBAT_TURN', '协作战斗阶段无效')
    outcome = combat.get('outcome')
    if outcome not in {None, 'victory', 'defeat'}:
        _fail('INVALID_COMBAT_OUTCOME', '协作战斗结果无效')
    if (turn == COOP_COMBAT_ENDED) != (outcome is not None):
        _fail('INVALID_COMBAT_OUTCOME', '协作战斗结束状态与结果不一致')
    phase = state.get('phase')
    if outcome is None and phase != 'combat':
        _fail('INVALID_COMBAT_PHASE', '进行中的协作战斗必须处于 combat 阶段')
    if outcome == 'victory' and phase != 'combat':
        _fail('INVALID_COMBAT_PHASE', '已胜利的头部战斗状态必须保留 combat 阶段')
    if outcome == 'defeat' and phase != 'game_over':
        _fail('INVALID_COMBAT_PHASE', '已失败的协作战斗必须处于 game_over 阶段')
    player_keys = set(state['players'])
    seat_states = combat.get('seat_states')
    if not isinstance(seat_states, dict) or set(seat_states) != player_keys:
        _fail('INVALID_SEAT_STATES', '战斗席位私有区与队伍席位不一致')
    for seat_key, player in state['players'].items():
        max_health = player.get('max_health')
        health = player.get('health')
        _strict_int(max_health, code='INVALID_PLAYER_HEALTH', label='玩家最大生命', minimum=1)
        _strict_int(health, code='INVALID_PLAYER_HEALTH', label='玩家生命', minimum=0)
        if health > max_health:
            _fail('INVALID_PLAYER_HEALTH', '玩家生命无效')
        _validate_seat_state(seat_key, seat_states[seat_key])
    enemies = combat.get('enemies')
    if not isinstance(enemies, list) or not enemies:
        _fail('INVALID_ENEMIES', '协作战斗敌人列表无效')
    enemy_ids = []
    for enemy in enemies:
        if not isinstance(enemy, dict):
            _fail('INVALID_ENEMY', '敌人状态无效')
        enemy_id = enemy.get('id')
        if not isinstance(enemy_id, str) or not _COMBAT_ID_RE.fullmatch(enemy_id):
            _fail('INVALID_ENEMY_ID', '敌人标识无效')
        enemy_ids.append(enemy_id)
        max_health = enemy.get('max_health')
        health = enemy.get('health')
        _strict_int(max_health, code='INVALID_ENEMY_HEALTH', label='敌人最大生命', minimum=1)
        _strict_int(health, code='INVALID_ENEMY_HEALTH', label='敌人生命', minimum=0)
        if health > max_health:
            _fail('INVALID_ENEMY_HEALTH', '敌人生命不能超过最大生命')
        stored_intent = enemy.get('intent')
        intent = _normalize_intent(stored_intent)
        if stored_intent != intent:
            _fail('INVALID_ENEMY_INTENT', '敌人意图必须以规范结构存储')
        if intent.get('kind') == 'attack':
            target = intent.get('target_seat')
            if isinstance(target, bool) or not isinstance(target, int) or str(target) not in player_keys:
                _fail('INVALID_ENEMY_TARGET', '单体攻击必须锁定有效席位')
    if len(set(enemy_ids)) != len(enemy_ids):
        _fail('INVALID_ENEMY_ID', '敌人标识不能重复')
    _validate_action_receipts(state)
    coordination = state['coordination']
    ready = coordination.get('combat_ready_seats', [])
    living = _living_seats(state)
    if any(seat not in living for seat in ready):
        _fail('INVALID_COMBAT_READY_STATE', '倒地席位不能处于战斗准备状态')
    ready_round = coordination.get('combat_ready_round')
    if turn == COOP_COMBAT_HERO_TURN and ready_round != round_number:
        _fail('INVALID_COMBAT_READY_STATE', '战斗准备状态不属于当前回合')
    if turn == COOP_COMBAT_ENDED and (ready or ready_round is not None):
        _fail('INVALID_COMBAT_READY_STATE', '已结束战斗不能保留准备状态')
    living_seats = _living_seats(state)
    living_enemies = _living_enemies(state)
    if outcome is None and (not living_seats or not living_enemies):
        _fail('INVALID_COMBAT_OUTCOME', '进行中的战斗必须同时存在存活成员与敌人')
    if outcome == 'victory' and (not living_seats or living_enemies):
        _fail('INVALID_COMBAT_OUTCOME', '协作战斗胜利状态无效')
    if outcome == 'defeat' and living_seats:
        _fail('INVALID_COMBAT_OUTCOME', '协作战斗失败状态无效')
    return True


def damage_coop_enemy(state, *, actor_seat, enemy_id, amount, events, source='hero_action'):
    """Apply trusted, already-computed hero damage to one explicit enemy."""

    _strict_int(actor_seat, code='INVALID_ACTOR_SEAT', label='行动席位', minimum=0)
    _strict_int(amount, code='INVALID_DAMAGE', label='伤害', minimum=1)
    target_id = str(enemy_id or '').strip()
    enemy = next((item for item in state['combat']['enemies'] if item.get('id') == target_id), None)
    if enemy is None or int(enemy.get('health') or 0) <= 0:
        _fail('INVALID_ENEMY_TARGET', '指定敌人不存在或已经被击败')
    before = int(enemy['health'])
    dealt = min(before, amount)
    enemy['health'] = before - dealt
    events.append({
        'type': 'enemy_damage',
        'actor_seat': actor_seat,
        'enemy_id': target_id,
        'amount': dealt,
        'before': before,
        'after': int(enemy['health']),
        'source': str(source or 'hero_action'),
    })
    if before > 0 and int(enemy['health']) == 0:
        events.append({'type': 'enemy_defeated', 'actor_seat': actor_seat, 'enemy_id': target_id})
    return dealt


def _damage_seat(
    state,
    seat,
    amount,
    hits,
    enemy,
    events,
    *,
    attack_all=False,
    original_target_seat=None,
):
    current_seat = seat
    original_target = (
        (enemy.get('intent') or {}).get('target_seat')
        if original_target_seat is None
        else original_target_seat
    )
    for hit_index in range(1, hits + 1):
        if not attack_all and current_seat not in _living_seats(state):
            next_seat = _fallback_target_seat(current_seat, _living_seats(state))
            if next_seat is None:
                break
            previous_seat = current_seat
            current_seat = next_seat
            enemy['intent']['target_seat'] = current_seat
            events.append({
                'type': 'enemy_target_reassigned',
                'enemy_id': enemy['id'],
                'original_target_seat': previous_seat,
                'target_seat': current_seat,
                'round': state['combat']['round'],
                'hit_index': hit_index,
                'reason': 'target_down_during_multi_hit',
            })
        player = state['players'][str(current_seat)]
        seat_state = state['combat']['seat_states'][str(current_seat)]
        if int(player.get('health') or 0) <= 0:
            break
        shield_before = int(seat_state.get('shield') or 0)
        blocked = min(shield_before, amount)
        seat_state['shield'] = shield_before - blocked
        dealt = amount - blocked
        before = int(player['health'])
        player['health'] = max(0, before - dealt)
        events.append({
            'type': 'player_damage',
            'enemy_id': enemy['id'],
            'target_seat': current_seat,
            'original_target_seat': None if attack_all else original_target,
            'amount': min(before, dealt),
            'blocked': blocked,
            'before': before,
            'after': int(player['health']),
            'hit_index': hit_index,
            'hit_count': hits,
        })
        if before > 0 and int(player['health']) == 0:
            events.append({
                'type': 'player_down',
                'target_seat': current_seat,
                'enemy_id': enemy['id'],
            })


def _set_party_defeat(state, events):
    combat = state['combat']
    if combat.get('outcome') == 'defeat':
        return
    combat['turn'] = COOP_COMBAT_ENDED
    combat['outcome'] = 'defeat'
    state['phase'] = 'game_over'
    state['coordination']['combat_ready_seats'] = []
    state['coordination']['combat_ready_round'] = None
    events.append({'type': 'party_defeated', 'combat_id': combat['id'], 'round': combat['round']})


def _set_party_victory(state, events):
    combat = state['combat']
    if combat.get('outcome') == 'victory':
        return
    combat['turn'] = COOP_COMBAT_ENDED
    combat['outcome'] = 'victory'
    state['coordination']['combat_ready_seats'] = []
    state['coordination']['combat_ready_round'] = None
    events.append({'type': 'combat_victory', 'combat_id': combat['id'], 'round': combat['round']})
    for seat in sorted(int(key) for key in state['players']):
        player = state['players'][str(seat)]
        if int(player.get('health') or 0) > 0:
            continue
        revived_health = max(1, math.ceil(int(player['max_health']) * COOP_COMBAT_REVIVE_RATIO))
        player['health'] = min(int(player['max_health']), revived_health)
        events.append({
            'type': 'player_revived',
            'target_seat': seat,
            'amount': int(player['health']),
            'source': 'post_combat',
        })


def _resolve_terminal_state(state, events):
    # Preserve the established single-player simultaneous-KO rule: defeat wins
    # the tie if the final hero and final threat reach zero in one resolution.
    if not _living_seats(state):
        _set_party_defeat(state, events)
        return True
    if not _living_enemies(state):
        _set_party_victory(state, events)
        return True
    return False


def _resolve_enemy_phase(state, run_seed, events):
    combat = state['combat']
    combat['turn'] = COOP_COMBAT_ENEMY_TURN
    events.append({'type': 'enemy_phase_started', 'combat_id': combat['id'], 'round': combat['round']})
    for enemy in list(combat['enemies']):
        if int(enemy.get('health') or 0) <= 0:
            continue
        if _resolve_terminal_state(state, events):
            return
        intent = enemy.get('intent') or {}
        kind = intent.get('kind')
        amount = int(intent.get('amount') or 0)
        hits = int(intent.get('hits') or 1)
        if kind == 'attack':
            original = int(intent['target_seat'])
            living = _living_seats(state)
            target = original if original in living else _fallback_target_seat(original, living)
            if target is None:
                _set_party_defeat(state, events)
                return
            if target != original:
                intent['target_seat'] = target
                events.append({
                    'type': 'enemy_target_reassigned',
                    'enemy_id': enemy['id'],
                    'original_target_seat': original,
                    'target_seat': target,
                    'round': combat['round'],
                })
            _damage_seat(
                state,
                target,
                amount,
                hits,
                enemy,
                events,
                original_target_seat=original,
            )
        elif kind == 'attack_all':
            for target in list(_living_seats(state)):
                _damage_seat(state, target, amount, hits, enemy, events, attack_all=True)
                if not _living_seats(state):
                    break
        elif kind == 'idle':
            events.append({'type': 'enemy_idle', 'enemy_id': enemy['id']})
        else:
            _fail('UNSUPPORTED_ENEMY_INTENT', f'暂不支持敌人意图 {kind}')
        if _resolve_terminal_state(state, events):
            return
    combat['round'] = int(combat['round']) + 1
    combat['turn'] = COOP_COMBAT_HERO_TURN
    state['coordination']['combat_ready_seats'] = []
    state['coordination']['combat_ready_round'] = combat['round']
    _lock_enemy_targets(state, run_seed, events)
    events.append({'type': 'hero_phase_started', 'combat_id': combat['id'], 'round': combat['round']})


def _canonical_request_fingerprint(actor_seat, combat_id, combat_round, action_type, payload):
    body = {
        'actor_seat': actor_seat,
        'combat_id': combat_id,
        'combat_round': combat_round,
        'action_type': action_type,
        'payload': payload,
    }
    try:
        encoded = json.dumps(
            body,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(',', ':'),
        ).encode('utf-8')
    except (TypeError, ValueError) as exc:
        raise CoopCombatError('INVALID_ACTION_PAYLOAD', '协作战斗动作数据必须可安全序列化') from exc
    return hashlib.sha256(encoded).hexdigest()


def apply_coop_combat_command(
    source_state,
    *,
    authenticated_user_id,
    action_id,
    action_type,
    payload,
    run_seed,
    combat_id,
    combat_round,
    expected_sequence=None,
    hero_action_resolver=None,
):
    """Apply one authenticated combat command as an atomic pure transaction.

    ``hero_action_resolver`` is trusted server-side rules code.  Its signature is
    ``resolver(state, actor_seat, action_type, payload, run_seed, events)``.
    Client payloads never select the acting seat.
    """

    validate_coop_combat_state(source_state)
    actor_seat = story_seat_for_user(source_state, authenticated_user_id)
    if actor_seat is None:
        _fail('NOT_PARTY_MEMBER', '当前账号不是该协作旅程成员')
    action_id = _normalize_action_id(action_id)
    action_type = _normalize_action_type(action_type)
    combat_id = _normalize_combat_id(combat_id)
    _strict_int(combat_round, code='INVALID_COMBAT_ROUND', label='战斗回合', minimum=1)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        _fail('INVALID_ACTION_PAYLOAD', '协作战斗动作数据无效')
    if {'actor_seat', 'actor_user_id'}.intersection(payload):
        _fail('FORGED_ACTOR', '行动者只能由服务器认证信息决定')
    payload = deepcopy(payload)
    fingerprint = _canonical_request_fingerprint(
        actor_seat,
        combat_id,
        combat_round,
        action_type,
        payload,
    )
    receipt_key = f'{int(authenticated_user_id)}:{action_id}'
    receipts = source_state['coordination'].get('action_receipts', {})
    existing = receipts.get(receipt_key)
    if existing is not None:
        if existing.get('request_fingerprint') != fingerprint:
            _fail('ACTION_ID_CONFLICT', '同一动作标识不能提交不同内容')
        return deepcopy(source_state), [], deepcopy(existing)

    combat = source_state['combat']
    if combat.get('turn') != COOP_COMBAT_HERO_TURN or combat.get('outcome') is not None:
        _fail('COMBAT_ACTION_NOT_ALLOWED', '当前不是协作英雄行动阶段')
    if combat.get('id') != combat_id:
        _fail('STALE_COMBAT', '协作战斗标识已经过期')
    if int(combat.get('round') or 0) != combat_round:
        _fail('STALE_COMBAT_ROUND', '协作战斗回合已经过期')
    current_sequence = int(source_state['coordination'].get('action_sequence') or 0)
    if expected_sequence is not None:
        _strict_int(
            expected_sequence,
            code='INVALID_EXPECTED_SEQUENCE',
            label='预期动作序号',
            minimum=0,
        )
        if expected_sequence != current_sequence:
            _fail('STALE_ACTION_SEQUENCE', '协作战斗动作序号已经过期')
    if int(source_state['players'][str(actor_seat)].get('health') or 0) <= 0:
        _fail('ACTOR_DOWN', '倒地成员不能执行战斗动作')
    ready = source_state['coordination'].get('combat_ready_seats', [])
    if actor_seat in ready:
        _fail('ACTOR_ALREADY_READY', '已经结束本回合的成员不能继续行动')

    state = deepcopy(source_state)
    events = []
    coordination = state['coordination']
    if action_type == 'combat_ready':
        coordination['combat_ready_seats'] = sorted(
            set(coordination.get('combat_ready_seats', [])) | {actor_seat}
        )
        events.append({
            'type': 'combat_seat_ready',
            'actor_seat': actor_seat,
            'combat_id': combat_id,
            'round': combat_round,
        })
    else:
        if hero_action_resolver is None:
            _fail('UNSUPPORTED_COMBAT_ACTION', f'暂不支持协作战斗动作 {action_type}')
        hero_action_resolver(
            state,
            actor_seat,
            action_type,
            payload,
            run_seed,
            events,
        )

    if not _resolve_terminal_state(state, events):
        living = _living_seats(state)
        coordination['combat_ready_seats'] = [
            seat for seat in coordination.get('combat_ready_seats', []) if seat in living
        ]
        if living and coordination['combat_ready_seats'] == sorted(living):
            _resolve_enemy_phase(state, run_seed, events)

    accepted_sequence = current_sequence + 1
    coordination['action_sequence'] = accepted_sequence
    receipt = {
        'action_id': action_id,
        'actor_user_id': int(authenticated_user_id),
        'actor_seat': actor_seat,
        'action_type': action_type,
        'combat_id': combat_id,
        'combat_round': combat_round,
        'action_sequence': accepted_sequence,
        'request_fingerprint': fingerprint,
    }
    coordination.setdefault('action_receipts', {})[receipt_key] = deepcopy(receipt)
    finalized_events = _finalize_events(events, accepted_sequence)
    validate_coop_combat_state(state)
    return state, finalized_events, receipt
