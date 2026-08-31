import copy

import pytest

from story_coop import build_initial_coop_story_state
from story_coop_combat import CoopCombatError, apply_coop_combat_command
from story_coop_live import (
    COOP_INTRO_COMBAT_ID,
    COOP_INTRO_ENEMY_DEF_ID,
    COOP_STAGE1_REST_CONTENT_VERSION,
    _draw_cards,
    prepare_intro_coop_round,
    project_coop_events,
    project_coop_run_for_viewer,
    resolve_intro_coop_action,
    start_intro_coop_combat,
)


MEMBERS = [
    {'user_id': 101, 'username': 'coop-one', 'display_name': 'Coop One'},
    {'user_id': 202, 'username': 'coop-two', 'display_name': 'Coop Two'},
]


def _combat_state(seed='coop-live-seed'):
    source = build_initial_coop_story_state(seed, MEMBERS)
    state, events = start_intro_coop_combat(source, run_seed=seed)
    return source, state, events


def _move_card_to_hand(state, seat, def_id):
    seat_state = state['combat']['seat_states'][str(seat)]
    for zone_name in ('hand', 'draw_pile', 'discard_pile', 'exile_pile'):
        zone = seat_state[zone_name]
        for card in list(zone):
            if card.get('def_id') != def_id:
                continue
            if zone_name != 'hand':
                zone.remove(card)
                seat_state['hand'].append(card)
            return card
    raise AssertionError(f'missing starter card {def_id}')


def _command(state, user_id, action_id, action_type, payload):
    return apply_coop_combat_command(
        state,
        authenticated_user_id=user_id,
        action_id=action_id,
        action_type=action_type,
        payload=payload,
        run_seed='coop-live-seed',
        combat_id=COOP_INTRO_COMBAT_ID,
        combat_round=int(state['combat']['round']),
        expected_sequence=int(state['coordination']['action_sequence']),
        hero_action_resolver=resolve_intro_coop_action,
        round_start_resolver=prepare_intro_coop_round,
    )


def test_intro_is_deterministic_playable_and_does_not_mutate_setup_state():
    source, state, events = _combat_state()
    repeated = start_intro_coop_combat(source, run_seed='coop-live-seed')[0]

    assert source['phase'] == 'journey_setup'
    assert source.get('combat') is None
    assert state == repeated
    assert state['phase'] == 'combat'
    assert state['combat']['id'] == COOP_INTRO_COMBAT_ID
    assert state['combat']['enemies'][0]['def_id'] == COOP_INTRO_ENEMY_DEF_ID
    assert state['combat']['enemies'][0]['health'] == 72
    assert any(event['type'] == 'coop_combat_started' for event in events)
    all_card_ids = []
    for seat_state in state['combat']['seat_states'].values():
        assert len(seat_state['hand']) == 5
        assert len(seat_state['draw_pile']) == 5
        assert seat_state['elixir'] == 3
        card_ids = [
            card['instance_id']
            for zone in ('hand', 'draw_pile', 'discard_pile', 'exile_pile')
            for card in seat_state[zone]
        ]
        assert len(card_ids) == len(set(card_ids)) == 10
        all_card_ids.extend(card_ids)
    assert len(all_card_ids) == len(set(all_card_ids)) == 20


def test_public_projection_is_viewer_specific_and_strips_server_only_fields():
    _, state, _ = _combat_state()
    state['party']['rules']['server_only'] = {'seed': 'never-project'}
    state['combat']['seat_states']['0']['equipment'].append({
        'instance_id': 'equipment-public-1',
        'def_id': 'test-equipment',
        'server_secret': 'never-project',
    })
    state['combat']['enemies'][0]['server_secret'] = 'never-project'
    state['last_events'].append({
        'type': 'coop_test_event',
        'actor_seat': 0,
        'seed': 'never-project',
    })
    run = {
        'id': 'a' * 32,
        'party_id': 'b' * 32,
        'status': 'active',
        'schema_version': 10,
        'content_version': state['content_version'],
        'revision': 1,
        'seed': 'server-seed',
        'state': state,
        'created_at': '2026-08-23T00:00:00Z',
        'updated_at': '2026-08-23T00:00:00Z',
        'completed_at': None,
    }

    public = project_coop_run_for_viewer(run, 101)
    serialized = repr(public)

    assert public['snapshot']['viewer_seat'] == 0
    assert all(isinstance(player['hand'], list) for player in public['snapshot']['players'])
    assert 'seed' not in public
    assert 'state' not in public
    assert 'rng_streams' not in public['snapshot']
    assert 'action_receipts' not in public['snapshot']
    assert 'draw_pile' not in serialized
    assert 'server_secret' not in serialized
    assert 'never-project' not in serialized
    assert public['snapshot']['players'][0]['equipment'] == [{
        'instance_id': 'equipment-public-1',
        'def_id': 'test-equipment',
    }]

    with pytest.raises(CoopCombatError) as exc_info:
        project_coop_run_for_viewer(run, 999)
    assert exc_info.value.code == 'NOT_PARTY_MEMBER'


def test_public_event_projection_redacts_personal_chest_amount_only():
    events = project_coop_events([
        {
            'type': 'coop_chest_gold_claimed',
            'actor_seat': 0,
            'room_id': 'chest:stage1-f9-n0',
            'amount': 57,
        },
        {
            'type': 'coop_enemy_hit',
            'target_seat': 1,
            'amount': 7,
        },
    ])

    assert events[0] == {
        'type': 'coop_chest_gold_claimed',
        'actor_seat': 0,
        'room_id': 'chest:stage1-f9-n0',
    }
    assert events[1]['amount'] == 7


def test_previous_stage_one_content_version_remains_readable_but_not_current():
    _, state, _ = _combat_state()
    state['content_version'] = COOP_STAGE1_REST_CONTENT_VERSION
    run = {
        'id': 'a' * 32,
        'party_id': 'b' * 32,
        'status': 'active',
        'schema_version': 10,
        'content_version': COOP_STAGE1_REST_CONTENT_VERSION,
        'revision': 1,
        'seed': 'server-seed',
        'state': state,
        'created_at': '2026-08-23T00:00:00Z',
        'updated_at': '2026-08-23T00:00:00Z',
        'completed_at': None,
    }

    public = project_coop_run_for_viewer(run, 101)
    assert public['content_version'] == COOP_STAGE1_REST_CONTENT_VERSION
    assert public['snapshot']['phase'] == 'combat'


def test_basic_rose_and_amulet_use_authoritative_card_rules():
    _, basic_state, _ = _combat_state()
    basic = _move_card_to_hand(basic_state, 0, 'basic')
    before_health = basic_state['combat']['enemies'][0]['health']
    basic_state, _, basic_receipt = _command(
        basic_state,
        101,
        'live-basic-0001',
        'play_card',
        {
            'card_instance_id': basic['instance_id'],
            'target_enemy_id': 'intro-soldier-ant',
        },
    )
    assert basic_state['combat']['enemies'][0]['health'] == before_health - 6
    assert basic_state['combat']['seat_states']['0']['elixir'] == 2
    assert basic_receipt['actor_seat'] == 0

    _, rose_state, _ = _combat_state()
    rose = _move_card_to_hand(rose_state, 1, 'rose')
    rose_state, _, _ = _command(
        rose_state,
        202,
        'live-rose-00001',
        'play_card',
        {'card_instance_id': rose['instance_id']},
    )
    assert rose_state['combat']['seat_states']['1']['shield'] == 5
    assert rose_state['combat']['seat_states']['1']['elixir'] == 2

    _, amulet_state, _ = _combat_state()
    amulet = _move_card_to_hand(amulet_state, 0, 'amulet')
    discard = next(
        card
        for card in amulet_state['combat']['seat_states']['0']['hand']
        if card['instance_id'] != amulet['instance_id']
    )
    before = copy.deepcopy(amulet_state)
    with pytest.raises(CoopCombatError) as missing_discard:
        _command(
            amulet_state,
            101,
            'live-amulet-bad',
            'play_card',
            {
                'card_instance_id': amulet['instance_id'],
                'target_enemy_id': 'intro-soldier-ant',
            },
        )
    assert missing_discard.value.code == 'INVALID_CARD_SELECTION'
    assert amulet_state == before

    amulet_state, events, _ = _command(
        amulet_state,
        101,
        'live-amulet-good',
        'play_card',
        {
            'card_instance_id': amulet['instance_id'],
            'target_enemy_id': 'intro-soldier-ant',
            'discard_card_instance_ids': [discard['instance_id']],
        },
    )
    assert amulet_state['combat']['enemies'][0]['health'] == 56
    assert amulet_state['combat']['seat_states']['0']['elixir'] == 1
    assert {event['type'] for event in events} >= {
        'coop_card_played',
        'coop_card_discarded',
        'enemy_damage',
    }


def test_demo_reward_multihit_and_wide_cards_use_their_declared_effects():
    _, sand_state, _ = _combat_state()
    sand_state['combat']['seat_states']['0']['hand'].append({
        'instance_id': 'coop-test-sand-0001',
        'def_id': 'sand',
        'upgraded': False,
        'upgrade_level': 0,
    })
    before = sand_state['combat']['enemies'][0]['health']
    sand_state, sand_events, _ = _command(
        sand_state,
        101,
        'live-sand-00001',
        'play_card',
        {
            'card_instance_id': 'coop-test-sand-0001',
            'target_enemy_id': 'intro-soldier-ant',
        },
    )
    assert sand_state['combat']['enemies'][0]['health'] == before - 5
    assert sum(event['type'] == 'enemy_damage' for event in sand_events) == 5

    _, wide_state, _ = _combat_state()
    wide_state['combat']['enemies'].append({
        'id': 'intro-second-target',
        'def_id': 'coop-test-target',
        'name': {'zh': '测试目标', 'en': 'Test Target'},
        'health': 20,
        'max_health': 20,
        'intent': {
            'kind': 'attack',
            'amount': 1,
            'hits': 1,
            'target_seat': 1,
        },
    })
    wide_state['combat']['seat_states']['0']['hand'].append({
        'instance_id': 'coop-test-lightning-0001',
        'def_id': 'lightning',
        'upgraded': False,
        'upgrade_level': 0,
    })
    wide_state, wide_events, _ = _command(
        wide_state,
        101,
        'live-wide-00001',
        'play_card',
        {'card_instance_id': 'coop-test-lightning-0001'},
    )
    assert [enemy['health'] for enemy in wide_state['combat']['enemies']] == [66, 14]
    assert sum(event['type'] == 'enemy_damage' for event in wide_events) == 4


def test_coop_multihit_stops_immediately_after_target_is_defeated():
    _, state, _ = _combat_state('coop-live-multihit-lethal')
    target = state['combat']['enemies'][0]
    target['health'] = 2
    target['max_health'] = 2
    target['shield'] = 0
    state['combat']['seat_states']['0']['hand'].append({
        'instance_id': 'coop-test-lethal-sand-0001',
        'def_id': 'sand',
        'upgraded': False,
        'upgrade_level': 0,
    })

    state, events, _ = _command(
        state,
        101,
        'live-lethal-sand-0001',
        'play_card',
        {
            'card_instance_id': 'coop-test-lethal-sand-0001',
            'target_enemy_id': target['id'],
        },
    )

    damage = [
        event for event in events
        if event.get('type') == 'enemy_damage'
        and event.get('enemy_id') == target['id']
    ]
    defeats = [
        event for event in events
        if event.get('type') == 'enemy_defeated'
        and event.get('enemy_id') == target['id']
    ]
    assert len(damage) == 2
    assert damage[-1]['lethal'] is True
    assert damage[-1]['after'] == 0
    assert len(defeats) == 1
    assert not any(
        event.get('type') == 'enemy_damage'
        for event in events[events.index(defeats[0]) + 1:]
    )


def test_shared_draw_resolves_after_active_discard_and_can_redraw_that_card():
    _, state, _ = _combat_state()
    seat_state = state['combat']['seat_states']['0']
    torch = {
        'instance_id': 'coop-test-torch-0001',
        'def_id': 'torch',
        'upgraded': False,
        'upgrade_level': 0,
    }
    seat_state['hand'].append(torch)
    selected = next(card for card in seat_state['hand'] if card is not torch)
    seat_state['exile_pile'].extend(seat_state['draw_pile'])
    seat_state['draw_pile'] = []
    seat_state['discard_pile'] = []

    state, events, _ = _command(
        state,
        101,
        'live-torch-order-0001',
        'play_card',
        {
            'card_instance_id': torch['instance_id'],
            'target_enemy_id': 'intro-soldier-ant',
            'discard_card_instance_ids': [selected['instance_id']],
        },
    )

    seat_state = state['combat']['seat_states']['0']
    event_types = [event['type'] for event in events]
    assert event_types.index('coop_card_discarded') < event_types.index('coop_cards_drawn')
    assert any(card['instance_id'] == selected['instance_id'] for card in seat_state['hand'])
    assert any(card['instance_id'] == torch['instance_id'] for card in seat_state['discard_pile'])


def test_coop_draw_stops_at_hand_limit_without_burning_or_reshuffling():
    _, state, _ = _combat_state('coop-full-hand-stops-draw')
    seat_state = state['combat']['seat_states']['0']
    all_cards = [
        card
        for zone_name in ('hand', 'draw_pile', 'discard_pile', 'exile_pile')
        for card in seat_state[zone_name]
    ]
    seat_state['hand'] = all_cards[:10]
    top_card = {
        'instance_id': 'coop-full-hand-top-card',
        'def_id': 'rose',
        'upgraded': False,
        'upgrade_level': 0,
    }
    discard_card = {
        'instance_id': 'coop-full-hand-discard-card',
        'def_id': 'basic',
        'upgraded': False,
        'upgrade_level': 0,
    }
    seat_state['draw_pile'] = [top_card]
    seat_state['discard_pile'] = [discard_card]
    seat_state['exile_pile'] = []
    streams_before = copy.deepcopy(state.get('rng_streams'))
    events = []

    _draw_cards(state, 0, 'coop-full-hand-stops-draw', 4, events)

    assert len(seat_state['hand']) == 10
    assert seat_state['draw_pile'] == [top_card]
    assert seat_state['discard_pile'] == [discard_card]
    assert state.get('rng_streams') == streams_before
    assert not any(event.get('type') in {'coop_cards_drawn', 'coop_discard_shuffled'} for event in events)


def test_coop_batch_draw_only_fills_remaining_hand_capacity():
    _, state, _ = _combat_state('coop-partial-hand-capacity')
    seat_state = state['combat']['seat_states']['0']
    all_cards = [
        card
        for zone_name in ('hand', 'draw_pile', 'discard_pile', 'exile_pile')
        for card in seat_state[zone_name]
    ]
    seat_state['hand'] = all_cards[:9]
    first_card = {
        'instance_id': 'coop-capacity-first-card',
        'def_id': 'rose',
        'upgraded': False,
        'upgrade_level': 0,
    }
    second_card = {
        'instance_id': 'coop-capacity-second-card',
        'def_id': 'basic',
        'upgraded': False,
        'upgrade_level': 0,
    }
    seat_state['draw_pile'] = [first_card, second_card]
    seat_state['discard_pile'] = []
    seat_state['exile_pile'] = []
    events = []

    _draw_cards(state, 0, 'coop-partial-hand-capacity', 3, events)

    assert len(seat_state['hand']) == 10
    assert seat_state['hand'][-1] == first_card
    assert seat_state['draw_pile'] == [second_card]
    assert seat_state['discard_pile'] == []
    draw_event = next(event for event in events if event.get('type') == 'coop_cards_drawn')
    assert draw_event['card_instance_ids'] == [first_card['instance_id']]
    assert draw_event['count'] == 1


def test_coop_card_draw_effect_does_not_burn_cards_while_hand_is_full():
    _, state, _ = _combat_state('coop-full-hand-card-draw')
    seat_state = state['combat']['seat_states']['0']
    all_cards = [
        card
        for zone_name in ('hand', 'draw_pile', 'discard_pile', 'exile_pile')
        for card in seat_state[zone_name]
    ]
    feather = {
        'instance_id': 'coop-full-hand-feather',
        'def_id': 'feather',
        'upgraded': False,
        'upgrade_level': 0,
    }
    seat_state['hand'] = [feather] + all_cards[:9]
    top_card = {
        'instance_id': 'coop-full-hand-next-card',
        'def_id': 'rose',
        'upgraded': False,
        'upgrade_level': 0,
    }
    seat_state['draw_pile'] = [top_card]
    seat_state['discard_pile'] = []
    seat_state['exile_pile'] = []
    seat_state['elixir'] = 10

    state, events, _ = _command(
        state,
        101,
        'coop-full-hand-feather-action',
        'play_card',
        {'card_instance_id': feather['instance_id']},
    )

    seat_state = state['combat']['seat_states']['0']
    assert len(seat_state['hand']) == 10
    assert seat_state['hand'][-1] == top_card
    assert seat_state['draw_pile'] == []
    assert any(card['instance_id'] == feather['instance_id'] for card in seat_state['discard_pile'])
    draw_event = next(event for event in events if event.get('type') == 'coop_cards_drawn')
    assert draw_event['card_instance_ids'] == [top_card['instance_id']]
    assert draw_event['count'] == 1


def test_shared_elixir_effect_is_applied_after_cost_and_exile_tag_is_honored():
    _, state, _ = _combat_state()
    seat_state = state['combat']['seat_states']['0']
    coffee = {
        'instance_id': 'coop-test-coffee-0001',
        'def_id': 'coffee',
        'upgraded': False,
        'upgrade_level': 0,
    }
    seat_state['hand'].append(coffee)

    state, events, _ = _command(
        state,
        101,
        'live-coffee-00001',
        'play_card',
        {'card_instance_id': coffee['instance_id']},
    )

    seat_state = state['combat']['seat_states']['0']
    assert seat_state['elixir'] == 5
    assert any(card['instance_id'] == coffee['instance_id'] for card in seat_state['exile_pile'])
    gain = next(event for event in events if event['type'] == 'coop_elixir_gained')
    assert gain['before'] == 2
    assert gain['amount'] == 3
    assert gain['after'] == 5


def test_ready_barrier_runs_enemy_once_then_discards_draws_and_restores_elixir():
    _, state, _ = _combat_state()
    state['combat']['seat_states']['0']['shield'] = 5
    state['combat']['seat_states']['0']['magic'] = 7
    state['combat']['seat_states']['1']['magic'] = 9
    starting_total_health = sum(player['health'] for player in state['players'].values())

    state, first_events, _ = _command(state, 101, 'live-ready-0001', 'combat_ready', {})
    assert state['combat']['round'] == 1
    assert state['coordination']['combat_ready_seats'] == [0]
    assert not any(event['type'] == 'enemy_phase_started' for event in first_events)

    state, events, _ = _command(state, 202, 'live-ready-0002', 'combat_ready', {})
    assert state['combat']['round'] == 2
    assert state['coordination']['combat_ready_seats'] == []
    assert state['coordination']['action_sequence'] == 2
    assert sum(player['health'] for player in state['players'].values()) <= starting_total_health
    assert sum(event['type'] == 'enemy_phase_started' for event in events) == 1
    assert any(event['type'] == 'hero_phase_started' for event in events)
    for seat_key, seat_state in state['combat']['seat_states'].items():
        assert seat_state['elixir'] == 3
        assert seat_state['magic'] == {'0': 7, '1': 9}[seat_key]
        assert seat_state['shield'] == 0
        assert len(seat_state['hand']) == 5


def test_intro_reaches_authoritative_victory_and_defeat_states():
    _, victory, _ = _combat_state()
    basic = _move_card_to_hand(victory, 0, 'basic')
    victory['combat']['enemies'][0]['health'] = 6
    victory, events, _ = _command(
        victory,
        101,
        'live-win-000001',
        'play_card',
        {
            'card_instance_id': basic['instance_id'],
            'target_enemy_id': 'intro-soldier-ant',
        },
    )
    assert victory['combat']['outcome'] == 'victory'
    assert victory['combat']['turn'] == 'ended'
    assert any(event['type'] == 'combat_victory' for event in events)

    _, defeat, _ = _combat_state()
    for player in defeat['players'].values():
        player['health'] = 1
    defeat['combat']['enemies'][0]['intent'] = {
        'kind': 'attack_all',
        'amount': 1,
        'hits': 1,
    }
    defeat, _, _ = _command(defeat, 101, 'live-loss-0001', 'combat_ready', {})
    defeat, events, _ = _command(defeat, 202, 'live-loss-0002', 'combat_ready', {})
    assert defeat['phase'] == 'game_over'
    assert defeat['combat']['outcome'] == 'defeat'
    assert all(player['health'] == 0 for player in defeat['players'].values())
    assert any(event['type'] == 'party_defeated' for event in events)
