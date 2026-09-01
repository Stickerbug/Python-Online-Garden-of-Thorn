from copy import deepcopy

import pytest

from story_content import STORY_CARDS, STORY_ENEMIES
from story_coop import build_initial_coop_story_state
from story_coop_combat import (
    COOP_COMBAT_ENDED,
    CoopCombatError,
    apply_coop_combat_command,
)
from story_coop_live import (
    COOP_OPENING_BLESSING_IDS,
    COOP_STAGE1_DIFFICULTIES,
    COOP_STORY_CONTENT_VERSION,
    _shop_card_price,
    advance_coop_after_victory,
    apply_coop_journey_command,
    prepare_coop_stage1_setup,
    prepare_intro_coop_round,
    project_coop_state_for_viewer,
    resolve_compiled_coop_enemy_action,
    resolve_intro_coop_action,
    validate_coop_live_state,
)


SEED = 'coop-opening-seed'
MEMBERS = [
    {'user_id': 101, 'username': 'opening-one', 'display_name': 'Opening One'},
    {'user_id': 202, 'username': 'opening-two', 'display_name': 'Opening Two'},
]


def _setup_state(seed=SEED, character_id='common_flower'):
    source = build_initial_coop_story_state(
        seed,
        MEMBERS,
        character_id=character_id,
    )
    state = prepare_coop_stage1_setup(source)
    return source, state


def _journey(state, user_id, action_id, action_type, payload, seed=SEED):
    return apply_coop_journey_command(
        state,
        authenticated_user_id=user_id,
        action_id=action_id,
        action_type=action_type,
        payload=payload,
        run_seed=seed,
        expected_sequence=state['coordination']['action_sequence'],
    )


def _opening_state(difficulty='normal', seed=SEED, character_id='common_flower'):
    _, setup = _setup_state(seed, character_id)
    return _journey(
        setup,
        101,
        f'opening-setup-{difficulty}',
        'setup_start',
        {'difficulty': difficulty},
        seed,
    )[0]


def _first_combat_state(difficulty='normal', seed=SEED, character_id='common_flower'):
    state = _opening_state(difficulty, seed, character_id)
    for seat, user_id in ((0, 101), (1, 202)):
        private = state['room_states_by_player'][str(seat)]
        state = _journey(
            state,
            user_id,
            f'{difficulty}-blessing-{seat}-0001',
            'opening_choose',
            {'room_id': state['room']['id'], 'option_id': private['options'][0]},
            seed,
        )[0]
    vote = state['coordination']['map_vote']
    target = vote['option_node_ids'][0]
    for seat, user_id in ((0, 101), (1, 202)):
        state = _journey(
            state,
            user_id,
            f'{difficulty}-route-{seat}-0001',
            'map_vote',
            {'vote_id': vote['vote_id'], 'node_id': target},
            seed,
        )[0]
    assert state['phase'] == 'combat'
    assert state['current_floor'] == 2
    return state


def _move_combat_card_to_hand(state, seat, def_id):
    seat_state = state['combat']['seat_states'][str(seat)]
    for zone_name in ('hand', 'draw_pile', 'discard_pile', 'exile_pile'):
        for card in list(seat_state[zone_name]):
            if card.get('def_id') != def_id:
                continue
            if zone_name != 'hand':
                seat_state[zone_name].remove(card)
                seat_state['hand'].append(card)
            return card
    raise AssertionError(f'missing cooperative card {def_id}')


def _play_combat_card(
    state,
    user_id,
    action_id,
    card,
    target_enemy_id=None,
    run_seed=SEED,
):
    payload = {'card_instance_id': card['instance_id']}
    if target_enemy_id is not None:
        payload['target_enemy_id'] = target_enemy_id
    return apply_coop_combat_command(
        state,
        authenticated_user_id=user_id,
        action_id=action_id,
        action_type='play_card',
        payload=payload,
        run_seed=run_seed,
        combat_id=state['combat']['id'],
        combat_round=state['combat']['round'],
        expected_sequence=state['coordination']['action_sequence'],
        hero_action_resolver=resolve_intro_coop_action,
        round_start_resolver=prepare_intro_coop_round,
        enemy_action_resolver=resolve_compiled_coop_enemy_action,
    )


@pytest.mark.parametrize('difficulty', COOP_STAGE1_DIFFICULTIES)
def test_leader_setup_is_deterministic_and_builds_the_selected_garden_map(difficulty):
    source, setup = _setup_state()
    before_setup = deepcopy(setup)

    state = _opening_state(difficulty)
    repeated = _opening_state(difficulty)

    assert source['content_version'] != COOP_STORY_CONTENT_VERSION
    assert setup == before_setup
    assert state == repeated
    assert state['content_version'] == COOP_STORY_CONTENT_VERSION
    assert state['phase'] == 'room'
    assert state['room']['type'] == 'opening'
    assert state['difficulty'] == difficulty
    assert state['map']['difficulty'] == difficulty
    assert state['map']['floors'][0]['nodes'][0]['type'] == 'blessing'
    assert state['coop_progression']['encounter_index'] == 0
    assert state['coop_progression']['completed_combat_ids'] == []
    assert state['coop_progression']['completed_node_ids'] == []
    validate_coop_live_state(state)


def test_historical_fingerprinted_run_remains_viewable():
    state = _opening_state()
    state['content_version'] = (
        'story-redesign-99-coop-stage1-shared-content-1-aaaaaaaaaaaa'
    )
    state['players']['0']['deck'][0]['def_id'] = 'retired_coop_card'

    validate_coop_live_state(state)
    snapshot = project_coop_state_for_viewer(state, 101)
    assert snapshot['content_version'] == state['content_version']
    assert snapshot['room_state']['type'] == 'opening'


def test_setup_is_leader_only_easy_is_fail_closed_and_corrupt_setup_is_rejected():
    _, setup = _setup_state()
    before = deepcopy(setup)

    with pytest.raises(CoopCombatError) as member_error:
        _journey(
            setup,
            202,
            'setup-member-0001',
            'setup_start',
            {'difficulty': 'normal'},
        )
    assert member_error.value.code == 'COOP_PARTY_LEADER_REQUIRED'
    assert setup == before

    for difficulty in ('easy', 'unknown'):
        with pytest.raises(CoopCombatError) as difficulty_error:
            _journey(
                setup,
                101,
                f'setup-bad-{difficulty}',
                'setup_start',
                {'difficulty': difficulty},
            )
        assert difficulty_error.value.code == 'UNSUPPORTED_COOP_DIFFICULTY'
        assert setup == before

    corrupt = deepcopy(setup)
    corrupt['room']['difficulties'] = ['hard', 'normal']
    with pytest.raises(CoopCombatError) as corrupt_error:
        validate_coop_live_state(corrupt)
    assert corrupt_error.value.code == 'INVALID_COOP_SETUP'


@pytest.mark.parametrize('blessing_id', COOP_OPENING_BLESSING_IDS)
def test_each_supported_opening_blessing_applies_only_to_the_acting_seat(blessing_id):
    opening = _opening_state()
    private = opening['room_states_by_player']['0']
    private['options'] = [
        blessing_id,
        *[item for item in COOP_OPENING_BLESSING_IDS if item != blessing_id][:2],
    ]
    validate_coop_live_state(opening)
    before = deepcopy(opening)

    state, events, receipt = _journey(
        opening,
        101,
        f'blessing-{blessing_id}-0001',
        'opening_choose',
        {'room_id': opening['room']['id'], 'option_id': blessing_id},
    )

    assert opening == before
    assert state['phase'] == 'room'
    assert state['players']['1'] == before['players']['1']
    assert state['players']['0']['blessing'] == blessing_id
    assert state['players']['0']['blessings'] == [blessing_id]
    assert state['room_states_by_player']['0']['status'] == 'resolved'
    assert state['room_states_by_player']['1']['status'] == 'pending'
    assert receipt['actor_seat'] == 0
    assert events == [{
        'type': 'coop_opening_resolved',
        'actor_seat': 0,
        'room_id': state['room']['id'],
        'stage': 1,
        'action_sequence': 2,
        'event_index': 0,
    }]

    player = state['players']['0']
    before_player = before['players']['0']
    added_cards = player['deck'][len(before_player['deck']):]
    if blessing_id == 'max_health':
        assert player['max_health'] == before_player['max_health'] + 15
        assert player['health'] == before_player['health']
        assert added_cards == []
    elif blessing_id == 'gold':
        assert player['gold'] == before_player['gold'] + 100
        assert added_cards == []
    elif blessing_id == 'rare_card':
        assert len(added_cards) == 1
        assert STORY_CARDS[added_cards[0]['def_id']]['rarity'] == 'ultra'
    else:
        assert player['gold'] == before_player['gold'] + 250
        assert [card['def_id'] for card in added_cards] == ['basic', 'rose']


def test_private_opening_projection_and_last_choice_atomically_start_route_vote():
    opening = _opening_state()
    leader_private = deepcopy(opening['room_states_by_player']['0'])
    member_private = deepcopy(opening['room_states_by_player']['1'])

    leader_snapshot = project_coop_state_for_viewer(opening, 101)
    member_snapshot = project_coop_state_for_viewer(opening, 202)
    assert leader_snapshot['room_state']['options'] == leader_private['options']
    assert member_snapshot['room_state']['options'] == member_private['options']
    assert 'room_states_by_player' not in leader_snapshot
    assert 'room_states_by_player' not in member_snapshot

    after_leader, leader_events, _ = _journey(
        opening,
        101,
        'opening-choice-leader',
        'opening_choose',
        {
            'room_id': opening['room']['id'],
            'option_id': leader_private['options'][0],
        },
    )
    member_waiting = project_coop_state_for_viewer(after_leader, 202)
    assert after_leader['phase'] == 'room'
    assert member_waiting['room_state']['selected_option'] is None
    assert member_waiting['room_state']['seats'] == [
        {'seat': 0, 'resolved': True},
        {'seat': 1, 'resolved': False},
    ]
    assert all('option_id' not in event for event in leader_events)

    room_id = after_leader['room']['id']
    final, events, _ = _journey(
        after_leader,
        202,
        'opening-choice-member',
        'opening_choose',
        {'room_id': room_id, 'option_id': member_private['options'][0]},
    )
    assert final['phase'] == 'map'
    assert final['combat'] is None
    assert final['current_floor'] == 1
    assert final['coop_progression']['encounter_index'] == 0
    assert final['coop_progression']['completed_combat_ids'] == []
    assert final['coop_progression']['completed_node_ids'] == [final['current_node_id']]
    assert final['coordination']['map_vote']['option_node_ids']
    assert {event['type'] for event in events} == {
        'coop_opening_resolved',
        'coop_route_vote_started',
    }
    validate_coop_live_state(final)


def test_opening_rejects_stale_room_foreign_option_and_repeat_without_mutation():
    opening = _opening_state()
    before = deepcopy(opening)
    member_options = opening['room_states_by_player']['1']['options']
    foreign_option = next(
        option for option in COOP_OPENING_BLESSING_IDS if option not in member_options
    )

    for action_id, payload, expected_code in (
        (
            'opening-stale-room',
            {'room_id': 'opening:stale:blessing', 'option_id': member_options[0]},
            'STALE_COOP_ROOM',
        ),
        (
            'opening-foreign-option',
            {'room_id': opening['room']['id'], 'option_id': foreign_option},
            'INVALID_OPENING_OPTION',
        ),
    ):
        with pytest.raises(CoopCombatError) as error:
            _journey(opening, 202, action_id, 'opening_choose', payload)
        assert error.value.code == expected_code
        assert opening == before

    resolved, _, _ = _journey(
        opening,
        202,
        'opening-valid-member',
        'opening_choose',
        {'room_id': opening['room']['id'], 'option_id': member_options[0]},
    )
    resolved_before = deepcopy(resolved)
    with pytest.raises(CoopCombatError) as repeated:
        _journey(
            resolved,
            202,
            'opening-repeat-member',
            'opening_choose',
            {'room_id': opening['room']['id'], 'option_id': member_options[0]},
        )
    assert repeated.value.code == 'OPENING_ALREADY_RESOLVED'
    assert resolved == resolved_before


def test_hard_and_lunatic_modifiers_match_the_explicit_coop_contract():
    normal = _first_combat_state('normal')
    hard = _first_combat_state('hard')
    lunatic = _first_combat_state('lunatic')

    normal_enemy = normal['combat']['enemies'][0]
    hard_enemy = hard['combat']['enemies'][0]
    lunatic_enemy = lunatic['combat']['enemies'][0]
    assert hard_enemy['max_health'] == normal_enemy['max_health']
    assert hard_enemy['intent']['amount'] == normal_enemy['intent']['amount']
    soldier = STORY_ENEMIES['soldier_ant']
    assert normal_enemy['max_health'] == (soldier['max_health'] * 3 + 1) // 2
    assert lunatic_enemy['max_health'] == (soldier['lunatic_max_health'] * 3 + 1) // 2
    assert normal_enemy['intent']['amount'] == soldier['moves'][0]['effects'][0]['amount']
    assert lunatic_enemy['intent']['amount'] == soldier['moves'][0]['effects'][0]['lunatic_amount']

    for state, expected_gold in ((normal, 15), (hard, 11), (lunatic, 11)):
        reward = deepcopy(state)
        for enemy in reward['combat']['enemies']:
            enemy['health'] = 0
        reward['combat']['turn'] = COOP_COMBAT_ENDED
        reward['combat']['outcome'] = 'victory'
        reward['coordination']['combat_ready_seats'] = []
        reward['coordination']['combat_ready_round'] = None
        advance_coop_after_victory(reward, run_seed=SEED)
        assert reward['phase'] == 'reward'
        assert reward['shared_reward']['gold_each'] == expected_gold
        assert all(
            item['gold'] == expected_gold
            for item in reward['rewards_by_player'].values()
        )
        validate_coop_live_state(reward)

    for card_id in ('bone', 'stinger', 'leaf', 'mjolnir'):
        normal_price = _shop_card_price(card_id, 'normal')
        expected_hard_price = (normal_price * 11 + 9) // 10
        assert _shop_card_price(card_id, 'hard') == expected_hard_price
        assert _shop_card_price(card_id, 'lunatic') == expected_hard_price


def test_mage_coop_starter_magic_and_character_pool_use_shared_content():
    seed = 'coop-mage-opening'
    source = build_initial_coop_story_state(seed, MEMBERS, character_id='mage')
    assert source['character_id'] == 'mage'
    for player in source['players'].values():
        assert player['character_id'] == 'mage'
        assert player['relics'] == ['magic_source']
        assert [card['def_id'] for card in player['deck']].count('basic') == 5
        assert [card['def_id'] for card in player['deck']].count('rose') == 5
        assert [card['def_id'] for card in player['deck']].count('mage_basic') == 1

    state = _first_combat_state('normal', seed, 'mage')
    assert all(
        seat_state['magic'] == 1
        for seat_state in state['combat']['seat_states'].values()
    )

    seat_state = state['combat']['seat_states']['0']
    seat_state['hand'].append({
        'instance_id': 'coop-mage-coffee-0001',
        'def_id': 'mage_coffee',
        'upgraded': False,
        'upgrade_level': 0,
    })
    state, events, _ = _play_combat_card(
        state,
        101,
        'coop-mage-coffee-action',
        seat_state['hand'][-1],
        run_seed=seed,
    )
    assert state['combat']['seat_states']['0']['magic'] == 5
    assert any(event['type'] == 'coop_magic_gained' for event in events)

    mage_basic = _move_combat_card_to_hand(state, 0, 'mage_basic')
    target = state['combat']['enemies'][0]
    before = target['health']
    state, _, _ = _play_combat_card(
        state,
        101,
        'coop-mage-basic-action',
        mage_basic,
        target['id'],
        seed,
    )
    assert state['combat']['seat_states']['0']['magic'] == 3
    assert state['combat']['enemies'][0]['health'] == before - 13

    reward = deepcopy(state)
    for enemy in reward['combat']['enemies']:
        enemy['health'] = 0
    reward['combat']['turn'] = COOP_COMBAT_ENDED
    reward['combat']['outcome'] = 'victory'
    reward['coordination']['combat_ready_seats'] = []
    reward['coordination']['combat_ready_round'] = None
    advance_coop_after_victory(reward, run_seed=seed)
    assert reward['phase'] == 'reward'
    assert all(
        STORY_CARDS[option['card_id']]['owner'] == 'mage'
        for private in reward['rewards_by_player'].values()
        for option in private['options']
    )
    validate_coop_live_state(reward)

    corrupted = deepcopy(reward)
    corrupted['rewards_by_player']['0']['options'][0]['card_id'] = 'bone'
    with pytest.raises(CoopCombatError) as wrong_character_reward:
        validate_coop_live_state(corrupted)
    assert wrong_character_reward.value.code == 'INVALID_COOP_REWARD'


def test_mage_electric_damage_applies_then_consumes_static_in_coop():
    seed = 'coop-mage-electric'
    state = _first_combat_state('normal', seed, 'mage')
    target = state['combat']['enemies'][0]
    target['health'] = target['max_health'] = 100
    target['shield'] = 0
    target['static'] = 0
    seat_state = state['combat']['seat_states']['0']
    seat_state['magic'] = 4
    card = {
        'instance_id': 'coop-mage-lightning-0001',
        'def_id': 'mage_lightning',
        'upgraded': False,
        'upgrade_level': 0,
    }
    seat_state['hand'].append(card)

    state, events, _ = _play_combat_card(
        state,
        101,
        'coop-mage-lightning-action',
        card,
        run_seed=seed,
    )

    assert state['combat']['seat_states']['0']['magic'] == 0
    assert state['combat']['enemies'][0]['health'] == 86
    assert state['combat']['enemies'][0]['static'] == 0
    assert [event['type'] for event in events if 'static' in event['type']] == [
        'coop_static_applied',
        'coop_static_triggered',
    ]


def test_compiled_soldier_ant_executes_canonical_move_cycle_and_public_state():
    state = _first_combat_state('normal')
    enemy = state['combat']['enemies'][0]
    assert enemy['def_id'] == 'soldier_ant'
    assert enemy['content_source'] == 'story_content'
    assert enemy['move_index'] == 0
    assert enemy['intent']['move_name'] == STORY_ENEMIES['soldier_ant']['moves'][0]['name']

    def ready(current, user_id, action_id):
        return apply_coop_combat_command(
            current,
            authenticated_user_id=user_id,
            action_id=action_id,
            action_type='combat_ready',
            payload={},
            run_seed=SEED,
            combat_id=current['combat']['id'],
            combat_round=current['combat']['round'],
            expected_sequence=current['coordination']['action_sequence'],
            hero_action_resolver=resolve_intro_coop_action,
            round_start_resolver=prepare_intro_coop_round,
            enemy_action_resolver=resolve_compiled_coop_enemy_action,
        )

    state = ready(state, 101, 'compiled-enemy-ready-1')[0]
    state, events, _ = ready(state, 202, 'compiled-enemy-ready-2')
    enemy = state['combat']['enemies'][0]
    assert enemy['shield'] == 8
    assert enemy['move_index'] == 1
    assert enemy['intent']['amount'] == 14
    assert any(event['type'] == 'enemy_shield_gained' for event in events)

    state = ready(state, 101, 'compiled-enemy-ready-3')[0]
    before = state['combat']['enemies'][0]['health']
    state, events, _ = ready(state, 202, 'compiled-enemy-ready-4')
    enemy = state['combat']['enemies'][0]
    assert enemy['health'] == before - 14
    assert enemy['move_index'] == 2
    assert enemy['intent']['kind'] == 'idle'
    assert any(event['type'] == 'enemy_self_damage' for event in events)

    state = ready(state, 101, 'compiled-enemy-ready-5')[0]
    state = ready(state, 202, 'compiled-enemy-ready-6')[0]
    enemy = state['combat']['enemies'][0]
    assert enemy['power'] == 3
    assert enemy['shield'] == 20
    assert enemy['move_index'] == 0
    assert enemy['intent']['amount'] == 9

    public = project_coop_state_for_viewer(state, 101)['combat']['enemies'][0]
    assert public['shield'] == 20
    assert public['power'] == 3
    assert public['intent']['move_name'] == STORY_ENEMIES['soldier_ant']['moves'][0]['name']
    assert 'content_source' not in public
