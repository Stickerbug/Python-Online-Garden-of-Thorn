import copy
import json

import pytest

from story_coop import build_initial_coop_story_state
from story_coop_combat import (
    COOP_COMBAT_ENDED,
    COOP_COMBAT_HERO_TURN,
    CoopCombatError,
    apply_coop_combat_command,
    damage_coop_enemy,
    initialize_coop_combat,
    validate_coop_combat_state,
)


MEMBERS = [
    {'user_id': 101, 'username': 'thorn-one', 'display_name': 'Thorn One'},
    {'user_id': 202, 'username': 'bloom-two', 'display_name': 'Bloom Two'},
]


def _seat_state(card_damage):
    return {
        'elixir': 3,
        'magic': 0,
        'shield': 0,
        'statuses': {},
        'hand': [{
            'instance_id': 'same-instance-id',
            'def_id': 'headless-strike',
            'damage': card_damage,
        }],
        'draw_pile': [],
        'discard_pile': [],
        'exile_pile': [],
        'equipment': [],
    }


def _combat_state(*, enemies=None, health=(80, 80), run_seed='coop-combat-seed'):
    state = build_initial_coop_story_state(run_seed, MEMBERS)
    for seat, value in enumerate(health):
        state['players'][str(seat)]['health'] = value
        state['players'][str(seat)]['max_health'] = 80
        state['players'][str(seat)]['relics'] = []
    if enemies is None:
        enemies = [{
            'id': 'enemy-1',
            'health': 40,
            'max_health': 40,
            'intent': {'kind': 'attack', 'amount': 7, 'hits': 1, 'target_seat': 0},
        }]
    return initialize_coop_combat(
        state,
        combat_id='combat-0001',
        enemies=enemies,
        run_seed=run_seed,
        seat_states={'0': _seat_state(6), '1': _seat_state(11)},
    )[0]


def _play_card_resolver(state, actor_seat, action_type, payload, run_seed, events):
    if action_type != 'play_card':
        raise CoopCombatError('UNSUPPORTED_TEST_ACTION', '测试解析器仅支持出牌')
    seat_state = state['combat']['seat_states'][str(actor_seat)]
    card_id = str(payload.get('card_instance_id') or '')
    card = next((item for item in seat_state['hand'] if item.get('instance_id') == card_id), None)
    if card is None:
        raise CoopCombatError('CARD_NOT_IN_ACTOR_HAND', '行动席位手牌中不存在该牌')
    seat_state['hand'].remove(card)
    seat_state['discard_pile'].append(card)
    events.append({
        'type': 'coop_card_played',
        'actor_seat': actor_seat,
        'card_instance_id': card_id,
    })
    damage_coop_enemy(
        state,
        actor_seat=actor_seat,
        enemy_id=payload.get('target_enemy_id'),
        amount=int(card['damage']),
        events=events,
        source=card['def_id'],
    )


def _command(state, user_id, action_id, action_type='play_card', payload=None, **overrides):
    kwargs = {
        'authenticated_user_id': user_id,
        'action_id': action_id,
        'action_type': action_type,
        'payload': payload or {},
        'run_seed': 'coop-combat-seed',
        'combat_id': 'combat-0001',
        'combat_round': int(state['combat']['round']),
        'expected_sequence': int(state['coordination']['action_sequence']),
        'hero_action_resolver': _play_card_resolver,
    }
    kwargs.update(overrides)
    return apply_coop_combat_command(state, **kwargs)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def test_two_seats_share_hero_phase_and_actor_comes_from_authenticated_user():
    state = _combat_state()
    before_seat_one = copy.deepcopy(state['combat']['seat_states']['1'])

    next_state, events, receipt = _command(
        state,
        101,
        'actor-0001',
        payload={'card_instance_id': 'same-instance-id', 'target_enemy_id': 'enemy-1'},
    )

    assert state['combat']['seat_states']['0']['hand']
    assert next_state['combat']['seat_states']['0']['hand'] == []
    assert next_state['combat']['seat_states']['1'] == before_seat_one
    assert next_state['combat']['enemies'][0]['health'] == 34
    assert receipt['actor_seat'] == 0
    assert all(event['action_sequence'] == 1 for event in events)
    assert {event.get('actor_seat') for event in events if 'actor_seat' in event} == {0}

    second_state, _, second_receipt = _command(
        next_state,
        202,
        'actor-0002',
        payload={'card_instance_id': 'same-instance-id', 'target_enemy_id': 'enemy-1'},
    )
    assert second_state['combat']['enemies'][0]['health'] == 23
    assert second_receipt['actor_seat'] == 1
    assert second_state['coordination']['action_sequence'] == 2


def test_client_cannot_forge_actor_fields_and_rejection_is_atomic():
    state = _combat_state()
    before = copy.deepcopy(state)

    with pytest.raises(CoopCombatError) as exc_info:
        _command(
            state,
            101,
            'forged-0001',
            payload={
                'actor_seat': 1,
                'card_instance_id': 'same-instance-id',
                'target_enemy_id': 'enemy-1',
            },
        )

    assert exc_info.value.code == 'FORGED_ACTOR'
    assert state == before


def test_each_accepted_command_increments_sequence_once_including_barrier():
    state = _combat_state()
    state, _, first = _command(
        state,
        101,
        'sequence-0001',
        payload={'card_instance_id': 'same-instance-id', 'target_enemy_id': 'enemy-1'},
    )
    state, _, second = _command(state, 101, 'sequence-0002', action_type='combat_ready')
    state, events, third = _command(state, 202, 'sequence-0003', action_type='combat_ready')

    assert [first['action_sequence'], second['action_sequence'], third['action_sequence']] == [1, 2, 3]
    assert state['coordination']['action_sequence'] == 3
    assert state['combat']['round'] == 2
    assert any(event['type'] == 'enemy_phase_started' for event in events)
    assert all(event['action_sequence'] == 3 for event in events)


def test_duplicate_action_returns_original_receipt_without_second_mutation():
    state = _combat_state()
    payload = {'card_instance_id': 'same-instance-id', 'target_enemy_id': 'enemy-1'}
    state, events, receipt = _command(state, 101, 'duplicate-0001', payload=payload)
    before_retry = copy.deepcopy(state)

    retried, retry_events, retry_receipt = _command(
        state,
        101,
        'duplicate-0001',
        payload=payload,
        expected_sequence=0,
    )

    assert events
    assert retry_events == []
    assert retry_receipt == receipt
    assert retried == before_retry
    assert state == before_retry

    with pytest.raises(CoopCombatError) as conflict:
        _command(
            state,
            101,
            'duplicate-0001',
            payload={'card_instance_id': 'same-instance-id', 'target_enemy_id': 'different-enemy'},
        )
    assert conflict.value.code == 'ACTION_ID_CONFLICT'
    assert state == before_retry


@pytest.mark.parametrize(
    ('user_id', 'payload', 'code'),
    [
        (999, {'card_instance_id': 'same-instance-id', 'target_enemy_id': 'enemy-1'}, 'NOT_PARTY_MEMBER'),
        (101, {'card_instance_id': 'same-instance-id', 'target_enemy_id': 'missing'}, 'INVALID_ENEMY_TARGET'),
    ],
)
def test_unknown_actor_and_invalid_target_are_atomic_rejections(user_id, payload, code):
    state = _combat_state()
    before = copy.deepcopy(state)

    with pytest.raises(CoopCombatError) as exc_info:
        _command(state, user_id, f'reject-{user_id:04d}', payload=payload)

    assert exc_info.value.code == code
    assert state == before


def test_dead_enemy_is_not_an_implicit_target_fallback():
    state = _combat_state(enemies=[
        {'id': 'dead-enemy', 'health': 0, 'max_health': 10, 'intent': {'kind': 'idle'}},
        {'id': 'living-enemy', 'health': 10, 'max_health': 10, 'intent': {'kind': 'idle'}},
    ])
    before = copy.deepcopy(state)

    with pytest.raises(CoopCombatError) as exc_info:
        _command(
            state,
            101,
            'dead-target-01',
            payload={'card_instance_id': 'same-instance-id', 'target_enemy_id': 'dead-enemy'},
        )

    assert exc_info.value.code == 'INVALID_ENEMY_TARGET'
    assert state == before


def test_ready_barrier_runs_enemy_phase_once_after_all_living_seats_ready():
    state = _combat_state()
    state, first_events, _ = _command(state, 101, 'ready-000001', action_type='combat_ready')
    assert state['players']['0']['health'] == 80
    assert state['combat']['round'] == 1
    assert not any(event['type'] == 'enemy_phase_started' for event in first_events)

    before_repeat = copy.deepcopy(state)
    with pytest.raises(CoopCombatError) as repeat_error:
        _command(state, 101, 'ready-000002', action_type='combat_ready')
    assert repeat_error.value.code == 'ACTOR_ALREADY_READY'
    assert state == before_repeat

    state, events, receipt = _command(state, 202, 'ready-000003', action_type='combat_ready')
    assert state['players']['0']['health'] == 73
    assert state['combat']['round'] == 2
    assert state['coordination']['combat_ready_seats'] == []
    assert sum(event['type'] == 'enemy_phase_started' for event in events) == 1

    before_retry = copy.deepcopy(state)
    retried, retry_events, retry_receipt = apply_coop_combat_command(
        state,
        authenticated_user_id=202,
        action_id='ready-000003',
        action_type='combat_ready',
        payload={},
        run_seed='coop-combat-seed',
        combat_id='combat-0001',
        combat_round=1,
        expected_sequence=1,
    )
    assert retried == before_retry
    assert retry_events == []
    assert retry_receipt == receipt


def test_enemy_retargets_in_seat_order_after_prior_enemy_downs_target():
    state = _combat_state(enemies=[
        {
            'id': 'enemy-first',
            'health': 20,
            'max_health': 20,
            'intent': {'kind': 'attack', 'amount': 80, 'hits': 1, 'target_seat': 1},
        },
        {
            'id': 'enemy-second',
            'health': 20,
            'max_health': 20,
            'intent': {'kind': 'attack', 'amount': 5, 'hits': 1, 'target_seat': 1},
        },
    ])
    state, _, _ = _command(state, 101, 'retarget-001', action_type='combat_ready')
    state, events, _ = _command(state, 202, 'retarget-002', action_type='combat_ready')

    assert state['players']['1']['health'] == 0
    assert state['players']['0']['health'] == 75
    reassigned = [
        event for event in events
        if event['type'] == 'enemy_target_reassigned'
        and event['enemy_id'] == 'enemy-second'
    ]
    assert len(reassigned) == 1
    assert reassigned[0]['original_target_seat'] == 1
    assert reassigned[0]['target_seat'] == 0
    second_damage = next(
        event for event in events
        if event['type'] == 'player_damage' and event['enemy_id'] == 'enemy-second'
    )
    assert second_damage['target_seat'] == 0
    assert second_damage['original_target_seat'] == 1


def test_one_downed_seat_does_not_end_party_and_is_excluded_from_barrier():
    state = _combat_state(health=(80, 0))
    before = copy.deepcopy(state)

    with pytest.raises(CoopCombatError) as down_error:
        _command(state, 202, 'downed-00001', action_type='combat_ready')
    assert down_error.value.code == 'ACTOR_DOWN'
    assert state == before

    state, events, _ = _command(state, 101, 'living-00001', action_type='combat_ready')
    assert state['phase'] == 'combat'
    assert state['combat']['round'] == 2
    assert state['players']['0']['health'] == 73
    assert state['players']['1']['health'] == 0
    assert sum(event['type'] == 'enemy_phase_started' for event in events) == 1


def test_all_downed_seats_end_run_once_and_stop_remaining_enemies():
    state = _combat_state(enemies=[
        {
            'id': 'enemy-seat-zero',
            'health': 20,
            'max_health': 20,
            'intent': {'kind': 'attack', 'amount': 80, 'hits': 1, 'target_seat': 0},
        },
        {
            'id': 'enemy-seat-one',
            'health': 20,
            'max_health': 20,
            'intent': {'kind': 'attack', 'amount': 80, 'hits': 1, 'target_seat': 1},
        },
        {
            'id': 'enemy-never-acts',
            'health': 20,
            'max_health': 20,
            'intent': {'kind': 'attack_all', 'amount': 1, 'hits': 1},
        },
    ])
    state, _, _ = _command(state, 101, 'defeat-00001', action_type='combat_ready')
    state, events, _ = _command(state, 202, 'defeat-00002', action_type='combat_ready')

    assert state['phase'] == 'game_over'
    assert state['combat']['turn'] == COOP_COMBAT_ENDED
    assert state['combat']['outcome'] == 'defeat'
    assert state['players']['0']['health'] == 0
    assert state['players']['1']['health'] == 0
    assert sum(event['type'] == 'party_defeated' for event in events) == 1
    assert not any(event.get('enemy_id') == 'enemy-never-acts' for event in events)
    assert not any(event['type'] in {'combat_victory', 'player_revived'} for event in events)


def test_victory_revives_only_downed_seat_to_ceil_twenty_percent():
    state = _combat_state(
        health=(0, 61),
        enemies=[{'id': 'last-enemy', 'health': 5, 'max_health': 5, 'intent': {'kind': 'idle'}}],
    )
    state['players']['0']['max_health'] = 81
    state, events, receipt = _command(
        state,
        202,
        'victory-0001',
        payload={'card_instance_id': 'same-instance-id', 'target_enemy_id': 'last-enemy'},
    )

    assert state['combat']['turn'] == COOP_COMBAT_ENDED
    assert state['combat']['outcome'] == 'victory'
    assert state['players']['0']['health'] == 17
    assert state['players']['1']['health'] == 61
    assert receipt['action_sequence'] == 1
    event_types = [event['type'] for event in events]
    assert event_types.count('combat_victory') == 1
    assert event_types.count('player_revived') == 1
    assert event_types.index('combat_victory') < event_types.index('player_revived')


def test_simultaneous_last_hero_and_last_enemy_defeat_prefers_party_loss():
    state = _combat_state(
        health=(0, 5),
        enemies=[{'id': 'last-enemy', 'health': 5, 'max_health': 5, 'intent': {'kind': 'idle'}}],
    )

    def mutual_ko_resolver(next_state, actor_seat, action_type, payload, run_seed, events):
        damage_coop_enemy(
            next_state,
            actor_seat=actor_seat,
            enemy_id='last-enemy',
            amount=5,
            events=events,
            source='mutual_ko',
        )
        next_state['players'][str(actor_seat)]['health'] = 0
        events.append({'type': 'player_down', 'target_seat': actor_seat, 'source': 'mutual_ko'})

    state, events, _ = _command(
        state,
        202,
        'mutual-ko-001',
        action_type='mutual_ko',
        hero_action_resolver=mutual_ko_resolver,
    )

    assert state['phase'] == 'game_over'
    assert state['combat']['outcome'] == 'defeat'
    assert sum(event['type'] == 'party_defeated' for event in events) == 1
    assert not any(event['type'] in {'combat_victory', 'player_revived'} for event in events)


def test_stale_round_and_sequence_rejections_do_not_mutate_state_or_rng():
    state = _combat_state()
    before = copy.deepcopy(state)

    with pytest.raises(CoopCombatError) as round_error:
        _command(state, 101, 'stale-round-1', combat_round=2, action_type='combat_ready')
    assert round_error.value.code == 'STALE_COMBAT_ROUND'
    assert state == before

    with pytest.raises(CoopCombatError) as sequence_error:
        _command(state, 101, 'stale-seq-001', expected_sequence=4, action_type='combat_ready')
    assert sequence_error.value.code == 'STALE_ACTION_SEQUENCE'
    assert state == before


def test_same_seed_and_command_trace_is_fully_deterministic():
    enemies = [{
        'id': 'random-target-enemy',
        'health': 30,
        'max_health': 30,
        'intent': {'kind': 'attack', 'amount': 3, 'hits': 1},
    }]
    first = _combat_state(enemies=enemies)
    second = _combat_state(enemies=enemies)
    assert _canonical(first) == _canonical(second)

    first_outputs = []
    second_outputs = []
    for user_id, action_id in ((101, 'trace-ready-01'), (202, 'trace-ready-02')):
        first, events, receipt = _command(first, user_id, action_id, action_type='combat_ready')
        first_outputs.append((events, receipt))
        second, events, receipt = _command(second, user_id, action_id, action_type='combat_ready')
        second_outputs.append((events, receipt))

    assert _canonical(first) == _canonical(second)
    assert _canonical(first_outputs) == _canonical(second_outputs)
    assert validate_coop_combat_state(first)


@pytest.mark.parametrize(
    ('mutator', 'code'),
    [
        (lambda state: state['combat'].__setitem__('id', ' combat-0001 '), 'INVALID_COMBAT_ID'),
        (
            lambda state: state['combat']['enemies'][0]['intent'].__setitem__('kind', 'ATTACK'),
            'INVALID_ENEMY_INTENT',
        ),
        (
            lambda state: state['combat']['enemies'][0]['intent'].pop('kind'),
            'INVALID_ENEMY_INTENT',
        ),
    ],
)
def test_combat_validation_rejects_noncanonical_stored_values(mutator, code):
    state = _combat_state()
    mutator(state)

    with pytest.raises(CoopCombatError) as exc_info:
        validate_coop_combat_state(state)

    assert exc_info.value.code == code


def test_combat_validation_requires_complete_typed_private_seat_state():
    state = _combat_state()

    malformed_states = []
    for field in ('elixir', 'magic', 'shield', 'statuses'):
        malformed = copy.deepcopy(state)
        del malformed['combat']['seat_states']['0'][field]
        malformed_states.append(malformed)
    for field in ('elixir', 'magic', 'shield'):
        malformed = copy.deepcopy(state)
        malformed['combat']['seat_states']['0'][field] = True
        malformed_states.append(malformed)
    malformed = copy.deepcopy(state)
    malformed['combat']['seat_states']['0']['statuses'] = []
    malformed_states.append(malformed)
    for zone in ('hand', 'draw_pile', 'discard_pile', 'exile_pile', 'equipment'):
        missing = copy.deepcopy(state)
        del missing['combat']['seat_states']['0'][zone]
        malformed_states.append(missing)
        wrong_type = copy.deepcopy(state)
        wrong_type['combat']['seat_states']['0'][zone] = {}
        malformed_states.append(wrong_type)

    for malformed in malformed_states:
        with pytest.raises(CoopCombatError) as exc_info:
            validate_coop_combat_state(malformed)
        assert exc_info.value.code == 'INVALID_SEAT_STATES'


def test_malformed_receipt_is_rejected_before_duplicate_lookup():
    state = _combat_state()
    state, _, _ = _command(state, 101, 'receipt-0001', action_type='combat_ready')
    receipt_key = '101:receipt-0001'
    state['coordination']['action_receipts'][receipt_key] = 'not-a-receipt'
    before = copy.deepcopy(state)

    with pytest.raises(CoopCombatError) as exc_info:
        _command(state, 101, 'receipt-0001', action_type='combat_ready')

    assert exc_info.value.code == 'INVALID_ACTION_RECEIPTS'
    assert state == before


def test_receipt_fields_and_actor_identity_are_strictly_validated():
    state = _combat_state()
    state, _, _ = _command(state, 101, 'receipt-0002', action_type='combat_ready')
    receipt_key = '101:receipt-0002'

    malformed_fingerprint = copy.deepcopy(state)
    malformed_fingerprint['coordination']['action_receipts'][receipt_key][
        'request_fingerprint'
    ] = 'not-a-sha256'
    with pytest.raises(CoopCombatError) as fingerprint_error:
        validate_coop_combat_state(malformed_fingerprint)
    assert fingerprint_error.value.code == 'INVALID_ACTION_RECEIPTS'

    forged_actor = copy.deepcopy(state)
    forged_actor['coordination']['action_receipts'][receipt_key]['actor_seat'] = 1
    with pytest.raises(CoopCombatError) as actor_error:
        validate_coop_combat_state(forged_actor)
    assert actor_error.value.code == 'INVALID_ACTION_RECEIPTS'


def test_combat_phase_must_match_active_victory_and_defeat_outcomes():
    active = _combat_state()
    active['phase'] = 'map'
    with pytest.raises(CoopCombatError) as active_error:
        validate_coop_combat_state(active)
    assert active_error.value.code == 'INVALID_COMBAT_PHASE'

    victory = _combat_state()
    victory['combat']['turn'] = COOP_COMBAT_ENDED
    victory['combat']['outcome'] = 'victory'
    victory['combat']['enemies'][0]['health'] = 0
    victory['coordination']['combat_ready_seats'] = []
    victory['coordination']['combat_ready_round'] = None
    victory['phase'] = 'game_over'
    with pytest.raises(CoopCombatError) as victory_error:
        validate_coop_combat_state(victory)
    assert victory_error.value.code == 'INVALID_COMBAT_PHASE'

    defeat = _combat_state()
    defeat['combat']['turn'] = COOP_COMBAT_ENDED
    defeat['combat']['outcome'] = 'defeat'
    defeat['players']['0']['health'] = 0
    defeat['players']['1']['health'] = 0
    defeat['coordination']['combat_ready_seats'] = []
    defeat['coordination']['combat_ready_round'] = None
    defeat['phase'] = 'combat'
    with pytest.raises(CoopCombatError) as defeat_error:
        validate_coop_combat_state(defeat)
    assert defeat_error.value.code == 'INVALID_COMBAT_PHASE'


def test_single_target_multi_hit_retargets_remaining_hits_in_seat_order():
    state = _combat_state(
        health=(5, 80),
        enemies=[{
            'id': 'multi-hit-enemy',
            'health': 30,
            'max_health': 30,
            'intent': {'kind': 'attack', 'amount': 5, 'hits': 3, 'target_seat': 0},
        }],
    )
    state, _, _ = _command(state, 101, 'multi-hit-001', action_type='combat_ready')
    state, events, _ = _command(state, 202, 'multi-hit-002', action_type='combat_ready')

    assert state['players']['0']['health'] == 0
    assert state['players']['1']['health'] == 70
    damage_events = [event for event in events if event['type'] == 'player_damage']
    assert [event['target_seat'] for event in damage_events] == [0, 1, 1]
    assert [event['hit_index'] for event in damage_events] == [1, 2, 3]
    assert all(event['hit_count'] == 3 for event in damage_events)
    assert all(event['original_target_seat'] == 0 for event in damage_events)
    reassigned = [
        event for event in events
        if event['type'] == 'enemy_target_reassigned'
        and event.get('reason') == 'target_down_during_multi_hit'
    ]
    assert len(reassigned) == 1
    assert reassigned[0]['original_target_seat'] == 0
    assert reassigned[0]['target_seat'] == 1
    assert reassigned[0]['hit_index'] == 2
    assert state['combat']['enemies'][0]['intent']['target_seat'] == 1
