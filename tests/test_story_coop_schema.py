import copy
import json

import pytest

from story_coop import (
    COOP_STORY_DEFAULT_RULES,
    COOP_STORY_MAX_PLAYERS,
    COOP_STORY_MIN_PLAYERS,
    COOP_STORY_MVP_MAX_PLAYERS,
    COOP_STORY_SCHEMA_VERSION,
    CoopStoryStateError,
    build_initial_coop_story_state,
    coop_story_default_rules,
    story_seat_for_user,
    upgrade_v9_solo_story_state,
    validate_story_state_v10,
)
from story_mode import STORY_SCHEMA_VERSION, build_initial_story_state


MEMBERS = [
    {
        'user_id': 101,
        'username': 'thorn-one',
        'display_name': 'Thorn One',
        'seat': 99,
        'role_type': 'admin',
        'secret': 'must-not-enter-state',
    },
    {
        'user_id': 202,
        'username': 'bloom-two',
        'display_name': 'Bloom Two',
        'seat': 88,
        'session_token': 'must-not-enter-state',
    },
]


def test_coop_schema_contract_constants_and_rules_are_stable():
    assert COOP_STORY_SCHEMA_VERSION == 10
    assert COOP_STORY_MIN_PLAYERS == 2
    assert COOP_STORY_MVP_MAX_PLAYERS == 2
    assert COOP_STORY_MAX_PLAYERS == 4
    assert COOP_STORY_DEFAULT_RULES['turn_model'] == 'shared_hero_phase'
    assert COOP_STORY_DEFAULT_RULES['action_ordering'] == 'server_serialized'
    assert COOP_STORY_DEFAULT_RULES['route_vote_policy'] == 'seeded_random'
    assert COOP_STORY_DEFAULT_RULES['reward_scope'] == 'per_player'
    assert COOP_STORY_DEFAULT_RULES['gold_scope'] == 'per_player'
    assert COOP_STORY_DEFAULT_RULES['allow_mid_combat_join'] is False
    assert COOP_STORY_DEFAULT_RULES['post_combat_revive_ratio'] == pytest.approx(0.20)

    first = coop_story_default_rules()
    second = coop_story_default_rules()
    first['turn_model'] = 'changed-locally'
    assert second['turn_model'] == 'shared_hero_phase'


def test_initial_coop_state_has_shared_run_and_private_player_states():
    state = build_initial_coop_story_state('coop-seed', MEMBERS)

    assert validate_story_state_v10(state, expected_mode='coop')
    assert state['schema_version'] == 10
    assert state['mode'] == 'coop'
    assert 'player' not in state
    assert 'reward' not in state
    assert state['shared_reward'] is None
    assert state['rewards_by_player'] is None
    assert state['party']['leader_seat'] == 0
    assert state['party']['max_players'] == 2
    assert list(state['players']) == ['0', '1']
    assert state['coordination'] == {
        'action_sequence': 0,
        'action_receipts': {},
        'combat_ready_seats': [],
        'combat_ready_round': None,
        'map_vote': None,
        'room_decision': None,
    }
    assert state['map']['floors']
    assert state['rng_streams'] == {}
    json.dumps(state, ensure_ascii=False)

    first_player = state['players']['0']
    second_player = state['players']['1']
    assert first_player == second_player
    assert first_player is not second_player
    assert first_player['deck'] is not second_player['deck']
    first_player['health'] = 1
    first_player['deck'][0]['upgraded'] = True
    assert second_player['health'] != 1
    assert second_player['deck'][0]['upgraded'] is False


def test_initial_coop_state_is_deterministic_and_does_not_mutate_inputs():
    members = copy.deepcopy(MEMBERS)
    before = copy.deepcopy(members)

    first = build_initial_coop_story_state('same-seed', members)
    second = build_initial_coop_story_state('same-seed', members)

    assert first == second
    assert members == before
    public_members = first['party']['members']
    assert [member['seat'] for member in public_members] == [0, 1]
    assert public_members[0]['party_role'] == 'leader'
    assert public_members[1]['party_role'] == 'member'
    for member in public_members:
        assert set(member) == {
            'seat',
            'user_id',
            'username',
            'display_name',
            'membership_status',
            'party_role',
        }


@pytest.mark.parametrize('max_players', [0, 1, 2.5, 5, True, '2', 'invalid'])
def test_initial_coop_state_rejects_invalid_max_players(max_players):
    with pytest.raises(CoopStoryStateError) as exc_info:
        build_initial_coop_story_state('invalid-max', MEMBERS, max_players=max_players)
    assert exc_info.value.code == 'INVALID_MAX_PLAYERS'


def test_initial_coop_state_enforces_member_count_and_unique_accounts():
    with pytest.raises(CoopStoryStateError) as too_few:
        build_initial_coop_story_state('too-few', MEMBERS[:1])
    assert too_few.value.code == 'INVALID_MEMBER_COUNT'

    with pytest.raises(CoopStoryStateError) as too_many_for_room:
        build_initial_coop_story_state(
            'too-many',
            MEMBERS + [{'user_id': 303, 'username': 'root-three'}],
            max_players=2,
        )
    assert too_many_for_room.value.code == 'INVALID_MEMBER_COUNT'

    duplicate = copy.deepcopy(MEMBERS)
    duplicate[1]['user_id'] = duplicate[0]['user_id']
    with pytest.raises(CoopStoryStateError) as duplicate_member:
        build_initial_coop_story_state('duplicate', duplicate)
    assert duplicate_member.value.code == 'DUPLICATE_MEMBER'


def test_schema_supports_four_members_while_mvp_default_remains_two():
    members = MEMBERS + [
        {'user_id': 303, 'username': 'root-three'},
        {'user_id': 404, 'username': 'guard-four'},
    ]

    state = build_initial_coop_story_state('four-player-contract', members, max_players=4)

    assert validate_story_state_v10(state, expected_mode='coop')
    assert state['party']['max_players'] == 4
    assert list(state['players']) == ['0', '1', '2', '3']


def test_v9_solo_upgrade_is_non_mutating_and_wraps_one_seat():
    legacy = build_initial_story_state('legacy-solo')
    legacy['reward'] = {'source': 'test', 'claims': {'gold': False}}
    before = copy.deepcopy(legacy)

    upgraded = upgrade_v9_solo_story_state(legacy, MEMBERS[0])

    assert legacy == before
    assert legacy['schema_version'] == STORY_SCHEMA_VERSION
    assert validate_story_state_v10(upgraded, expected_mode='solo')
    assert upgraded['schema_version'] == 10
    assert upgraded['mode'] == 'solo'
    assert upgraded['party']['max_players'] == 1
    assert upgraded['party']['leader_seat'] == 0
    assert list(upgraded['players']) == ['0']
    assert upgraded['players']['0'] == legacy['player']
    assert upgraded['players']['0'] is not legacy['player']
    assert upgraded['rewards_by_player']['0'] == legacy['reward']
    assert story_seat_for_user(upgraded, 101) == 0
    assert story_seat_for_user(upgraded, 999) is None


def test_v9_solo_upgrade_rejects_in_combat_state_without_mutating_it():
    legacy = build_initial_story_state('legacy-combat')
    legacy['combat'] = {'turn': 'player'}
    before = copy.deepcopy(legacy)

    with pytest.raises(CoopStoryStateError) as exc_info:
        upgrade_v9_solo_story_state(legacy, MEMBERS[0])

    assert exc_info.value.code == 'COMBAT_MIGRATION_UNSUPPORTED'
    assert legacy == before


def test_v9_solo_upgrade_rejects_unknown_schema():
    legacy = build_initial_story_state('legacy-unknown')
    legacy['schema_version'] = 8

    with pytest.raises(CoopStoryStateError) as exc_info:
        upgrade_v9_solo_story_state(legacy, MEMBERS[0])

    assert exc_info.value.code == 'UNSUPPORTED_SCHEMA_VERSION'


def test_v10_validation_rejects_duplicate_member_identity_and_bad_seats():
    state = build_initial_coop_story_state('invalid-v10-layout', MEMBERS)
    duplicate = copy.deepcopy(state)
    duplicate['party']['members'][1]['user_id'] = 101
    with pytest.raises(CoopStoryStateError) as duplicate_error:
        validate_story_state_v10(duplicate)
    assert duplicate_error.value.code == 'DUPLICATE_MEMBER'

    invalid_seat = copy.deepcopy(state)
    invalid_seat['party']['members'][1]['seat'] = 'not-a-seat'
    with pytest.raises(CoopStoryStateError) as seat_error:
        validate_story_state_v10(invalid_seat)
    assert seat_error.value.code == 'INVALID_SEAT_LAYOUT'

    boolean_seat = copy.deepcopy(state)
    boolean_seat['party']['members'][1]['seat'] = True
    with pytest.raises(CoopStoryStateError) as boolean_seat_error:
        validate_story_state_v10(boolean_seat)
    assert boolean_seat_error.value.code == 'INVALID_SEAT_LAYOUT'

    mismatched_mode = copy.deepcopy(state)
    mismatched_mode['party']['mode'] = 'solo'
    with pytest.raises(CoopStoryStateError) as mode_error:
        validate_story_state_v10(mismatched_mode)
    assert mode_error.value.code == 'STORY_MODE_MISMATCH'


def test_v10_validation_rejects_invalid_coordination_counters_and_ready_seats():
    state = build_initial_coop_story_state('invalid-coordination', MEMBERS)

    invalid_sequence = copy.deepcopy(state)
    invalid_sequence['coordination']['action_sequence'] = True
    with pytest.raises(CoopStoryStateError) as sequence_error:
        validate_story_state_v10(invalid_sequence)
    assert sequence_error.value.code == 'INVALID_ACTION_SEQUENCE'

    duplicate_ready = copy.deepcopy(state)
    duplicate_ready['coordination']['combat_ready_seats'] = [0, 0]
    with pytest.raises(CoopStoryStateError) as ready_error:
        validate_story_state_v10(duplicate_ready)
    assert ready_error.value.code == 'INVALID_COMBAT_READY_STATE'

    invalid_round = copy.deepcopy(state)
    invalid_round['coordination']['combat_ready_round'] = 0
    with pytest.raises(CoopStoryStateError) as round_error:
        validate_story_state_v10(invalid_round)
    assert round_error.value.code == 'INVALID_COMBAT_READY_STATE'


@pytest.mark.parametrize('schema_version', [True, 10.0, '10'])
def test_v10_validation_requires_strict_integer_schema_version(schema_version):
    state = build_initial_coop_story_state('strict-schema-version', MEMBERS)
    state['schema_version'] = schema_version

    with pytest.raises(CoopStoryStateError) as exc_info:
        validate_story_state_v10(state)

    assert exc_info.value.code == 'INVALID_SCHEMA_VERSION'


@pytest.mark.parametrize('field_value', [True, 2.0, '2'])
def test_v10_validation_requires_strict_integer_max_players(field_value):
    state = build_initial_coop_story_state('strict-max-players', MEMBERS)
    state['party']['max_players'] = field_value

    with pytest.raises(CoopStoryStateError) as exc_info:
        validate_story_state_v10(state)

    assert exc_info.value.code == 'INVALID_MEMBER_COUNT'


@pytest.mark.parametrize('field_value', [True, 0.0, '0'])
def test_v10_validation_requires_strict_integer_leader_seat(field_value):
    state = build_initial_coop_story_state('strict-leader-seat', MEMBERS)
    state['party']['leader_seat'] = field_value

    with pytest.raises(CoopStoryStateError) as exc_info:
        validate_story_state_v10(state)

    assert exc_info.value.code == 'INVALID_LEADER_SEAT'


def test_v10_validation_rejects_non_public_member_fields():
    state = build_initial_coop_story_state('public-member-fields', MEMBERS)
    state['party']['members'][0]['session_token'] = 'must-never-be-persisted'

    with pytest.raises(CoopStoryStateError) as exc_info:
        validate_story_state_v10(state)

    assert exc_info.value.code == 'INVALID_MEMBER_FIELDS'


@pytest.mark.parametrize(
    ('member_index', 'field', 'value', 'code'),
    [
        (0, 'party_role', 'member', 'INVALID_PARTY_ROLE'),
        (1, 'party_role', 'leader', 'INVALID_PARTY_ROLE'),
        (0, 'membership_status', 'left', 'INVALID_MEMBERSHIP_STATUS'),
        (0, 'username', ' thorn-one ', 'INVALID_MEMBER_USERNAME'),
        (1, 'display_name', '', 'INVALID_MEMBER_DISPLAY_NAME'),
    ],
)
def test_v10_validation_rejects_noncanonical_public_member_values(
    member_index,
    field,
    value,
    code,
):
    state = build_initial_coop_story_state('member-value-contract', MEMBERS)
    state['party']['members'][member_index][field] = value

    with pytest.raises(CoopStoryStateError) as exc_info:
        validate_story_state_v10(state)

    assert exc_info.value.code == code
