import contextlib
import copy
import json
from unittest import mock

import pytest

import app as gtn
import db
import story_coop_live


@pytest.fixture()
def coop_combat_api(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'coop-combat-api.sqlite3'))
    db.init_db()
    gtn.app.config.update(TESTING=True)
    return gtn.app.test_client()


def _insert_staff(username, role):
    now = db.utc_now()
    with db.get_db_connection() as conn:
        cursor = conn.execute(
            '''INSERT INTO users
               (username, username_lower, password_hash, created_at)
               VALUES (?, ?, 'test-hash', ?)''',
            (username, username.lower(), now),
        )
        user_id = int(cursor.lastrowid)
        conn.execute(
            '''INSERT INTO user_roles
               (user_id, role_type, role_key, title, color, sort_order,
                can_direct_friend, chat_exempt, visible, created_at, updated_at)
               VALUES (?, ?, ?, '', 'neutral', 99, 0, 0, 1, ?, ?)''',
            (user_id, role, role, now, now),
        )
        conn.commit()
    return user_id


@contextlib.contextmanager
def _as_staff(user_id, username):
    with (
        mock.patch.object(
            gtn,
            '_require_account_json',
            return_value=(user_id, username, None),
        ),
        mock.patch.object(gtn, 'feedback_is_staff', return_value=True),
        mock.patch.object(gtn, 'STORY_COOP_ENABLED', True),
        mock.patch.object(gtn, 'rate_limiter', return_value=True),
    ):
        yield


def _create_setup_party(client):
    leader_id = _insert_staff('CombatLeader', 'admin')
    member_id = _insert_staff('CombatMember', 'staff')
    with _as_staff(leader_id, 'CombatLeader'):
        created = client.post('/api/story/coop/party', json={}).get_json()
    with _as_staff(member_id, 'CombatMember'):
        joined = client.post(
            '/api/story/coop/party/join',
            json={'invite_code': created['invite_code']},
        ).get_json()
    with (
        _as_staff(leader_id, 'CombatLeader'),
        mock.patch.object(gtn.secrets, 'token_hex', return_value='c' * 32),
    ):
        response = client.post(
            '/api/story/coop/party/start',
            json={
                'party_id': joined['party']['id'],
                'party_revision': joined['party']['revision'],
            },
        )
    assert response.status_code == 200
    started = response.get_json()
    assert started['run']['snapshot']['phase'] == 'journey_setup'
    return leader_id, member_id, started


def _start_party(client):
    leader_id, member_id, started = _create_setup_party(client)
    run = started['run']

    with _as_staff(leader_id, 'CombatLeader'):
        setup = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=_journey_action_body(
                run,
                'setup-flow-0001',
                'setup_start',
                {'difficulty': 'normal'},
            ),
        )
    assert setup.status_code == 200
    run = setup.get_json()['run']

    leader_room = run['snapshot']['room_state']
    with _as_staff(leader_id, 'CombatLeader'):
        leader_opening = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=_journey_action_body(
                run,
                'setup-flow-0002',
                'opening_choose',
                {
                    'room_id': leader_room['room_id'],
                    'option_id': leader_room['options'][0],
                },
            ),
        )
    assert leader_opening.status_code == 200

    with _as_staff(member_id, 'CombatMember'):
        member_run = client.get(f'/api/story/coop/run/{run["id"]}').get_json()['run']
        member_room = member_run['snapshot']['room_state']
        member_opening = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=_journey_action_body(
                member_run,
                'setup-flow-0003',
                'opening_choose',
                {
                    'room_id': member_room['room_id'],
                    'option_id': member_room['options'][0],
                },
            ),
        )
    assert member_opening.status_code == 200
    run = member_opening.get_json()['run']
    target_node_id = run['snapshot']['map_vote']['options'][0]['node_id']

    with _as_staff(leader_id, 'CombatLeader'):
        leader_run = client.get(f'/api/story/coop/run/{run["id"]}').get_json()['run']
        leader_vote = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=_journey_action_body(
                leader_run,
                'setup-flow-0004',
                'map_vote',
                {
                    'vote_id': leader_run['snapshot']['map_vote']['vote_id'],
                    'node_id': target_node_id,
                },
            ),
        )
    assert leader_vote.status_code == 200

    with _as_staff(member_id, 'CombatMember'):
        member_run = client.get(f'/api/story/coop/run/{run["id"]}').get_json()['run']
        member_vote = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=_journey_action_body(
                member_run,
                'setup-flow-0005',
                'map_vote',
                {
                    'vote_id': member_run['snapshot']['map_vote']['vote_id'],
                    'node_id': target_node_id,
                },
            ),
        )
    assert member_vote.status_code == 200
    result = member_vote.get_json()
    with _as_staff(leader_id, 'CombatLeader'):
        result['run'] = client.get(f'/api/story/coop/run/{run["id"]}').get_json()['run']
    return leader_id, member_id, result


def _action_body(run, action_id, action_type, payload):
    snapshot = run['snapshot']
    combat = snapshot['combat']
    return {
        'party_id': run['party_id'],
        'run_id': run['id'],
        'run_revision': run['revision'],
        'action_id': action_id,
        'action_type': action_type,
        'combat_id': combat['id'],
        'combat_round': combat['round'],
        'expected_sequence': snapshot['action_sequence'],
        'payload': payload,
    }


def _journey_action_body(run, action_id, action_type, payload):
    return {
        'party_id': run['party_id'],
        'run_id': run['id'],
        'run_revision': run['revision'],
        'action_id': action_id,
        'action_type': action_type,
        'expected_sequence': run['snapshot']['action_sequence'],
        'payload': payload,
    }


def _first_playable_card_payload(run, seat):
    snapshot = run['snapshot']
    player = next(item for item in snapshot['players'] if item['seat'] == seat)
    card = next((item for item in player['hand'] if item['def_id'] == 'basic'), None)
    if card is not None:
        return {
            'card_instance_id': card['instance_id'],
            'target_enemy_id': snapshot['combat']['enemies'][0]['id'],
        }
    card = next(item for item in player['hand'] if item['def_id'] == 'rose')
    return {'card_instance_id': card['instance_id']}


def _assert_no_server_state(payload):
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for forbidden in (
        '"seed"',
        '"state"',
        '"rng_streams"',
        '"action_receipts"',
        '"draw_pile"',
        '"request_fingerprint"',
    ):
        assert forbidden not in serialized


def _install_personal_or_shared_room(user_id, run_id, room_type):
    raw_run = db.get_story_coop_run_for_member(user_id, run_id)
    state = raw_run['state']
    nodes = story_coop_live._coop_map_nodes(state)
    combat_node_id = state['current_node_id']
    completed_combat = copy.deepcopy(state['combat'])
    room_node_id = story_coop_live._coop_outgoing_node_ids(state, combat_node_id)[0]
    for node in nodes.values():
        if node.get('status') in {'available', 'current'}:
            node['status'] = 'locked'
    nodes[combat_node_id]['status'] = 'completed'
    nodes[room_node_id]['status'] = 'current'
    nodes[room_node_id]['type'] = room_type
    state['current_node_id'] = room_node_id
    state['current_floor'] = int(nodes[room_node_id]['floor'])
    state['combat'] = None
    state['last_combat'] = {
        'id': completed_combat['id'],
        'encounter_id': completed_combat['encounter_id'],
        'outcome': 'victory',
        'round': 1,
    }
    state['coop_progression']['completed_combat_ids'] = [completed_combat['id']]
    state['coop_progression']['completed_node_ids'].append(combat_node_id)
    state['coordination']['combat_ready_seats'] = []
    state['coordination']['combat_ready_round'] = None
    if room_type == 'chest':
        story_coop_live._start_coop_chest_room(
            state,
            room_node_id,
            str(raw_run['seed']),
        )
    elif room_type == 'event':
        story_coop_live._start_coop_event_room(
            state,
            room_node_id,
            str(raw_run['seed']),
        )
    else:
        raise AssertionError(f'unsupported test room {room_type}')
    story_coop_live.validate_coop_live_state(state)
    with db.get_db_connection() as conn:
        conn.execute(
            'UPDATE story_coop_runs SET state_json = ? WHERE id = ?',
            (
                json.dumps(
                    state,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(',', ':'),
                ),
                run_id,
            ),
        )
        conn.commit()
    return state


def _install_final_boss_combat(user_id, run_id):
    raw_run = db.get_story_coop_run_for_member(user_id, run_id)
    state = raw_run['state']
    nodes = story_coop_live._coop_map_nodes(state)
    already_completed_nodes = list(state['coop_progression']['completed_node_ids'])
    path = [state['current_node_id']]
    while int(nodes[path[-1]]['floor']) < int(state['map']['floor_count']):
        outgoing = story_coop_live._coop_outgoing_node_ids(state, path[-1])
        assert outgoing
        path.append(outgoing[0])
    boss_node_id = path[-1]
    assert nodes[boss_node_id]['type'] == 'boss'
    for node in nodes.values():
        node['status'] = 'locked'
    for node_id in already_completed_nodes:
        nodes[node_id]['status'] = 'completed'
    for node_id in path[:-1]:
        nodes[node_id]['status'] = 'completed'
    nodes[boss_node_id]['status'] = 'current'
    completed_combat_ids = []
    for node_id in path[:-1]:
        node = nodes[node_id]
        if node['type'] in {'combat', 'elite', 'boss'}:
            completed_combat_ids.append(f'garden-route-{node_id}')
    state['current_node_id'] = boss_node_id
    state['current_floor'] = int(nodes[boss_node_id]['floor'])
    state['phase'] = 'map'
    state['combat'] = None
    state['room'] = {'type': 'map_vote'}
    state['shared_reward'] = None
    state['rewards_by_player'] = None
    state['room_states_by_player'] = None
    state['completed_stage'] = None
    state['coordination']['map_vote'] = None
    state['coordination']['room_decision'] = None
    state['coordination']['combat_ready_seats'] = []
    state['coordination']['combat_ready_round'] = None
    state['coop_progression']['completed_node_ids'] = [
        *already_completed_nodes,
        *path[:-1],
    ]
    state['coop_progression']['completed_combat_ids'] = completed_combat_ids
    state['coop_progression']['encounter_index'] = len(completed_combat_ids)
    state['last_combat'] = {
        'id': completed_combat_ids[-1],
        'encounter_id': 'test-prior-encounter',
        'outcome': 'victory',
        'round': 1,
    }
    state, _ = story_coop_live._start_coop_combat_for_node(
        state,
        boss_node_id,
        str(raw_run['seed']),
    )
    boss = state['combat']['enemies'][0]
    boss['health'] = 6
    seat_state = state['combat']['seat_states']['0']
    basic = next(
        card
        for zone_name in ('hand', 'draw_pile', 'discard_pile')
        for card in seat_state[zone_name]
        if card['def_id'] == 'basic'
    )
    for zone_name in ('draw_pile', 'discard_pile'):
        if basic in seat_state[zone_name]:
            seat_state[zone_name].remove(basic)
            seat_state['hand'].append(basic)
    story_coop_live.validate_coop_live_state(state)
    with db.get_db_connection() as conn:
        conn.execute(
            'UPDATE story_coop_runs SET state_json = ? WHERE id = ?',
            (
                json.dumps(
                    state,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(',', ':'),
                ),
                run_id,
            ),
        )
        conn.commit()
    return basic['instance_id'], boss['id']


def test_setup_and_private_opening_use_authoritative_ledger_and_projection(
    coop_combat_api,
):
    client = coop_combat_api
    leader_id, member_id, started = _create_setup_party(client)
    run = started['run']
    assert run['snapshot']['room']['difficulties'] == ['normal']
    assert run['snapshot']['progression']['encounter_index'] == 0

    member_body = _journey_action_body(
        run,
        'setup-member-0001',
        'setup_start',
        {'difficulty': 'normal'},
    )
    with _as_staff(member_id, 'CombatMember'):
        forbidden = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=member_body,
        )
    assert forbidden.status_code == 403
    assert forbidden.get_json()['code'] == 'COOP_PARTY_LEADER_REQUIRED'
    assert forbidden.get_json()['run']['revision'] == run['revision']

    setup_body = _journey_action_body(
        run,
        'setup-leader-0001',
        'setup_start',
        {'difficulty': 'normal'},
    )
    with _as_staff(leader_id, 'CombatLeader'):
        opened = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=setup_body,
        )
        duplicate_setup = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=setup_body,
        )
        changed_setup = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json={
                **setup_body,
                'payload': {'difficulty': 'hard'},
            },
        )
    assert opened.status_code == 200
    leader_run = opened.get_json()['run']
    assert leader_run['snapshot']['phase'] == 'room'
    assert leader_run['snapshot']['difficulty'] == 'normal'
    assert leader_run['snapshot']['room_state']['type'] == 'opening'
    assert len(leader_run['snapshot']['room_state']['options']) == 3
    assert duplicate_setup.status_code == 200
    assert duplicate_setup.get_json()['duplicate'] is True
    assert changed_setup.status_code == 409
    assert changed_setup.get_json()['code'] == 'ACTION_ID_CONFLICT'

    with _as_staff(member_id, 'CombatMember'):
        member_run = client.get(f'/api/story/coop/run/{run["id"]}').get_json()['run']
    leader_options = leader_run['snapshot']['room_state']['options']
    member_options = member_run['snapshot']['room_state']['options']
    assert len(member_options) == 3
    assert 'room_states_by_player' not in json.dumps(leader_run, ensure_ascii=False)
    assert 'room_states_by_player' not in json.dumps(member_run, ensure_ascii=False)

    leader_choice_body = _journey_action_body(
        leader_run,
        'opening-leader-0001',
        'opening_choose',
        {
            'room_id': leader_run['snapshot']['room_state']['room_id'],
            'option_id': leader_options[0],
        },
    )
    with _as_staff(leader_id, 'CombatLeader'):
        leader_choice = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=leader_choice_body,
        )
        duplicate_choice = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=leader_choice_body,
        )
    assert leader_choice.status_code == 200
    assert duplicate_choice.status_code == 200
    assert duplicate_choice.get_json()['duplicate'] is True
    assert leader_choice.get_json()['run']['snapshot']['phase'] == 'room'

    with _as_staff(member_id, 'CombatMember'):
        member_waiting = client.get(f'/api/story/coop/run/{run["id"]}').get_json()['run']
    waiting_room = member_waiting['snapshot']['room_state']
    assert waiting_room['options'] == member_options
    assert waiting_room['selected_option'] is None
    assert waiting_room['seats'] == [
        {'seat': 0, 'resolved': True},
        {'seat': 1, 'resolved': False},
    ]
    assert all('option_id' not in event for event in member_waiting['snapshot']['last_events'])

    foreign_option = next(
        option
        for option in story_coop_live.COOP_OPENING_BLESSING_IDS
        if option not in member_options
    )
    invalid_body = _journey_action_body(
        member_waiting,
        'opening-member-bad',
        'opening_choose',
        {'room_id': waiting_room['room_id'], 'option_id': foreign_option},
    )
    with _as_staff(member_id, 'CombatMember'):
        invalid = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=invalid_body,
        )
    assert invalid.status_code == 400
    assert invalid.get_json()['code'] == 'INVALID_OPENING_OPTION'
    assert invalid.get_json()['run']['revision'] == member_waiting['revision']

    valid_body = _journey_action_body(
        member_waiting,
        'opening-member-0001',
        'opening_choose',
        {'room_id': waiting_room['room_id'], 'option_id': member_options[0]},
    )
    with _as_staff(member_id, 'CombatMember'):
        map_started = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=valid_body,
        )
    assert map_started.status_code == 200
    final_run = map_started.get_json()['run']
    assert final_run['snapshot']['phase'] == 'map'
    assert final_run['snapshot']['combat'] is None
    assert final_run['snapshot']['current_floor'] == 1
    assert final_run['snapshot']['progression']['completed_node_count'] == 1
    assert final_run['snapshot']['progression']['encounter_index'] == 0
    assert final_run['snapshot']['map_vote']['options']
    _assert_no_server_state(map_started.get_json())


def test_start_get_action_duplicate_and_stale_conflict_are_authoritative(coop_combat_api):
    client = coop_combat_api
    leader_id, member_id, started = _start_party(client)
    run = started['run']

    assert run['snapshot']['phase'] == 'combat'
    assert run['snapshot']['viewer_seat'] == 0
    assert len(run['snapshot']['players']) == 2
    assert len({
        card['instance_id']
        for player in run['snapshot']['players']
        for card in player['hand']
    }) == sum(len(player['hand']) for player in run['snapshot']['players'])
    _assert_no_server_state(started)

    with _as_staff(member_id, 'CombatMember'):
        member_get = client.get(f'/api/story/coop/run/{run["id"]}')
    assert member_get.status_code == 200
    member_run = member_get.get_json()['run']
    assert member_run['snapshot']['viewer_seat'] == 1
    _assert_no_server_state(member_get.get_json())

    payload = _first_playable_card_payload(run, 0)
    action_body = _action_body(run, 'http-action-0001', 'play_card', payload)
    with _as_staff(leader_id, 'CombatLeader'):
        committed = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=action_body,
        )
    assert committed.status_code == 200
    committed_payload = committed.get_json()
    assert committed_payload['duplicate'] is False
    assert committed_payload['events']
    assert committed_payload['receipt']['actor_seat'] == 0
    assert committed_payload['run']['revision'] == run['revision'] + 1
    assert committed_payload['run']['snapshot']['action_sequence'] == (
        run['snapshot']['action_sequence'] + 1
    )
    _assert_no_server_state(committed_payload)

    with _as_staff(leader_id, 'CombatLeader'):
        duplicate = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=action_body,
        )
    assert duplicate.status_code == 200
    assert duplicate.get_json()['duplicate'] is True
    assert duplicate.get_json()['events'] == []
    assert duplicate.get_json()['run']['revision'] == committed_payload['run']['revision']

    conflicting_body = copy.deepcopy(action_body)
    conflicting_body['payload']['unsupported_retry_change'] = True
    with _as_staff(leader_id, 'CombatLeader'):
        conflict = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=conflicting_body,
        )
    assert conflict.status_code == 409
    assert conflict.get_json()['code'] == 'ACTION_ID_CONFLICT'

    stale_body = copy.deepcopy(action_body)
    stale_body['action_id'] = 'http-action-0002'
    with _as_staff(leader_id, 'CombatLeader'):
        stale = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=stale_body,
        )
    assert stale.status_code == 409
    assert stale.get_json()['code'] == 'COOP_RUN_VERSION_OLD'
    assert stale.get_json()['run']['revision'] == committed_payload['run']['revision']


def test_action_rejects_forged_authority_and_non_member(coop_combat_api):
    client = coop_combat_api
    leader_id, _, started = _start_party(client)
    outsider_id = _insert_staff('CombatOutsider', 'staff')
    run = started['run']
    payload = _first_playable_card_payload(run, 0)
    action_body = _action_body(run, 'http-forged-001', 'play_card', payload)

    top_level_forgery = {**action_body, 'actor_seat': 1, 'damage': 9999}
    with _as_staff(leader_id, 'CombatLeader'):
        forged = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=top_level_forgery,
        )
    assert forged.status_code == 400
    assert forged.get_json()['code'] == 'FORGED_ACTION_STATE'

    nested_forgery = copy.deepcopy(action_body)
    nested_forgery['action_id'] = 'http-forged-002'
    nested_forgery['payload']['actor_seat'] = 1
    with _as_staff(leader_id, 'CombatLeader'):
        forged_actor = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=nested_forgery,
        )
    assert forged_actor.status_code == 400
    assert forged_actor.get_json()['code'] == 'FORGED_ACTOR'

    with _as_staff(outsider_id, 'CombatOutsider'):
        missing_get = client.get(f'/api/story/coop/run/{run["id"]}')
        missing_action = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json={**action_body, 'action_id': 'http-outsider-1'},
        )
    assert missing_get.status_code == 404
    assert missing_get.get_json()['code'] == 'COOP_RUN_NOT_FOUND'
    assert missing_action.status_code == 404
    assert missing_action.get_json()['code'] == 'COOP_RUN_NOT_FOUND'


def test_terminal_action_remains_readable_to_both_historical_members(coop_combat_api):
    client = coop_combat_api
    leader_id, member_id, started = _start_party(client)
    run_id = started['run']['id']
    raw_run = db.get_story_coop_run_for_member(leader_id, run_id)
    state = raw_run['state']
    state['players']['0']['health'] = 0
    state['players']['1']['health'] = 1
    with db.get_db_connection() as conn:
        conn.execute(
            'UPDATE story_coop_runs SET state_json = ? WHERE id = ?',
            (
                json.dumps(
                    state,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(',', ':'),
                ),
                run_id,
            ),
        )
        conn.commit()

    with _as_staff(member_id, 'CombatMember'):
        current = client.get(f'/api/story/coop/run/{run_id}').get_json()['run']
        second_ready_body = _action_body(current, 'http-ready-0002', 'combat_ready', {})
        terminal = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=second_ready_body,
        )
    assert terminal.status_code == 200
    terminal_run = terminal.get_json()['run']
    assert terminal_run['status'] == 'completed'
    assert terminal_run['snapshot']['phase'] == 'game_over'
    assert terminal_run['snapshot']['combat']['outcome'] == 'defeat'

    for user_id, username in (
        (leader_id, 'CombatLeader'),
        (member_id, 'CombatMember'),
    ):
        with _as_staff(user_id, username):
            historical = client.get(f'/api/story/coop/run/{run_id}')
            current_party = client.get('/api/story/coop/party')
        assert historical.status_code == 200
        assert historical.get_json()['run']['snapshot']['combat']['outcome'] == 'defeat'
        assert current_party.get_json()['party'] is None

    with _as_staff(member_id, 'CombatMember'):
        duplicate = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=second_ready_body,
        )
    assert duplicate.status_code == 200
    assert duplicate.get_json()['duplicate'] is True
    assert duplicate.get_json()['events'] == []
    assert duplicate.get_json()['run']['status'] == 'completed'


def test_corrupt_current_content_version_fails_closed_on_action(coop_combat_api):
    client = coop_combat_api
    leader_id, _, started = _start_party(client)
    run = started['run']
    raw_run = db.get_story_coop_run_for_member(leader_id, run['id'])
    raw_run['state']['content_version'] = 'corrupt-content-version'
    with db.get_db_connection() as conn:
        conn.execute(
            'UPDATE story_coop_runs SET state_json = ? WHERE id = ?',
            (
                json.dumps(
                    raw_run['state'],
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(',', ':'),
                ),
                run['id'],
            ),
        )
        conn.commit()

    action_body = _action_body(
        run,
        'http-corrupt-001',
        'combat_ready',
        {},
    )
    with _as_staff(leader_id, 'CombatLeader'):
        response = client.post(
            f'/api/story/coop/run/{run["id"]}/action',
            json=action_body,
        )
    assert response.status_code == 503
    assert response.get_json()['code'] == 'COOP_STORY_DATA_UNAVAILABLE'


def test_rest_room_actions_are_viewer_scoped_idempotent_and_use_the_shared_ledger(
    coop_combat_api,
):
    client = coop_combat_api
    leader_id, member_id, started = _start_party(client)
    run_id = started['run']['id']
    raw_run = db.get_story_coop_run_for_member(leader_id, run_id)
    state = raw_run['state']
    nodes = story_coop_live._coop_map_nodes(state)
    combat_node_id = state['current_node_id']
    completed_combat = copy.deepcopy(state['combat'])
    rest_node_id = story_coop_live._coop_outgoing_node_ids(state, combat_node_id)[0]
    for node in nodes.values():
        if node.get('status') in {'available', 'current'}:
            node['status'] = 'locked'
    nodes[combat_node_id]['status'] = 'completed'
    nodes[rest_node_id]['status'] = 'current'
    nodes[rest_node_id]['type'] = 'rest'
    state['current_node_id'] = rest_node_id
    state['current_floor'] = int(nodes[rest_node_id]['floor'])
    state['combat'] = None
    state['last_combat'] = {
        'id': completed_combat['id'],
        'encounter_id': completed_combat['encounter_id'],
        'outcome': 'victory',
        'round': 1,
    }
    state['coop_progression']['completed_combat_ids'] = [completed_combat['id']]
    state['coop_progression']['completed_node_ids'].append(combat_node_id)
    state['coordination']['combat_ready_seats'] = []
    state['coordination']['combat_ready_round'] = None
    state['players']['0']['health'] = 30
    story_coop_live._start_coop_rest_room(state, rest_node_id)
    story_coop_live.validate_coop_live_state(state)
    with db.get_db_connection() as conn:
        conn.execute(
            'UPDATE story_coop_runs SET state_json = ? WHERE id = ?',
            (
                json.dumps(
                    state,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(',', ':'),
                ),
                run_id,
            ),
        )
        conn.commit()

    with _as_staff(leader_id, 'CombatLeader'):
        leader_run = client.get(f'/api/story/coop/run/{run_id}').get_json()['run']
    leader_room = leader_run['snapshot']['room_state']
    assert leader_run['snapshot']['phase'] == 'room'
    assert leader_room['status'] == 'pending'
    assert set(leader_room['options']) == {'heal', 'upgrade', 'leave'}
    assert 'deck' in leader_room
    _assert_no_server_state(leader_run)

    heal_body = _journey_action_body(
        leader_run,
        'http-rest-heal-1',
        'room_choose',
        {'room_id': leader_room['room_id'], 'choice': 'heal'},
    )
    with _as_staff(leader_id, 'CombatLeader'):
        healed = client.post(f'/api/story/coop/run/{run_id}/action', json=heal_body)
        duplicate = client.post(f'/api/story/coop/run/{run_id}/action', json=heal_body)
    assert healed.status_code == 200
    assert healed.get_json()['run']['snapshot']['phase'] == 'room'
    assert healed.get_json()['run']['snapshot']['room_state']['status'] == 'resolved'
    assert duplicate.status_code == 200
    assert duplicate.get_json()['duplicate'] is True
    assert duplicate.get_json()['events'] == []

    with _as_staff(member_id, 'CombatMember'):
        member_run = client.get(f'/api/story/coop/run/{run_id}').get_json()['run']
    member_room = member_run['snapshot']['room_state']
    member_card = next(card for card in member_room['deck'] if not card.get('upgraded'))
    upgrade_body = _journey_action_body(
        member_run,
        'http-rest-upgrade-1',
        'room_choose',
        {
            'room_id': member_room['room_id'],
            'choice': 'upgrade',
            'card_instance_id': member_card['instance_id'],
        },
    )
    with _as_staff(member_id, 'CombatMember'):
        advanced = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=upgrade_body,
        )
    assert advanced.status_code == 200
    advanced_run = advanced.get_json()['run']
    assert advanced_run['snapshot']['phase'] == 'map'
    assert advanced_run['snapshot']['room_state'] is None
    assert advanced_run['snapshot']['map_vote'] is not None
    assert any(event['type'] == 'coop_route_vote_started' for event in advanced.get_json()['events'])
    raw_advanced = db.get_story_coop_run_for_member(member_id, run_id)['state']
    upgraded = next(
        card
        for card in raw_advanced['players']['1']['deck']
        if card['instance_id'] == member_card['instance_id']
    )
    assert upgraded['upgraded'] is True


def test_personal_shop_api_accepts_only_server_offer_identity(coop_combat_api):
    client = coop_combat_api
    leader_id, _, started = _start_party(client)
    run_id = started['run']['id']
    raw_run = db.get_story_coop_run_for_member(leader_id, run_id)
    state = raw_run['state']
    nodes = story_coop_live._coop_map_nodes(state)
    combat_node_id = state['current_node_id']
    completed_combat = copy.deepcopy(state['combat'])
    shop_node_id = story_coop_live._coop_outgoing_node_ids(state, combat_node_id)[0]
    for node in nodes.values():
        if node.get('status') in {'available', 'current'}:
            node['status'] = 'locked'
    nodes[combat_node_id]['status'] = 'completed'
    nodes[shop_node_id]['status'] = 'current'
    nodes[shop_node_id]['type'] = 'shop'
    state['current_node_id'] = shop_node_id
    state['current_floor'] = int(nodes[shop_node_id]['floor'])
    state['combat'] = None
    state['last_combat'] = {
        'id': completed_combat['id'],
        'encounter_id': completed_combat['encounter_id'],
        'outcome': 'victory',
        'round': 1,
    }
    state['coop_progression']['completed_combat_ids'] = [completed_combat['id']]
    state['coop_progression']['completed_node_ids'].append(combat_node_id)
    state['coordination']['combat_ready_seats'] = []
    state['coordination']['combat_ready_round'] = None
    story_coop_live._start_coop_shop_room(
        state,
        shop_node_id,
        str(raw_run['seed']),
    )
    story_coop_live.validate_coop_live_state(state)
    with db.get_db_connection() as conn:
        conn.execute(
            'UPDATE story_coop_runs SET state_json = ? WHERE id = ?',
            (
                json.dumps(
                    state,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(',', ':'),
                ),
                run_id,
            ),
        )
        conn.commit()

    with _as_staff(leader_id, 'CombatLeader'):
        run = client.get(f'/api/story/coop/run/{run_id}').get_json()['run']
    room = run['snapshot']['room_state']
    offer = next(item for item in room['offers'] if item['price'] <= room['gold'])
    body = _journey_action_body(
        run,
        'http-shop-buy-1',
        'shop_buy',
        {'room_id': room['room_id'], 'offer_id': offer['offer_id']},
    )
    with _as_staff(leader_id, 'CombatLeader'):
        bought = client.post(f'/api/story/coop/run/{run_id}/action', json=body)
        duplicate = client.post(f'/api/story/coop/run/{run_id}/action', json=body)
    assert bought.status_code == 200
    bought_payload = bought.get_json()
    assert bought_payload['run']['snapshot']['room_state']['gold'] == room['gold'] - offer['price']
    purchased = next(
        item
        for item in bought_payload['run']['snapshot']['room_state']['offers']
        if item['offer_id'] == offer['offer_id']
    )
    assert purchased['status'] == 'purchased'
    assert duplicate.status_code == 200
    assert duplicate.get_json()['duplicate'] is True
    _assert_no_server_state(bought_payload)

    forged = _journey_action_body(
        bought_payload['run'],
        'http-shop-forged-price',
        'shop_buy',
        {
            'room_id': room['room_id'],
            'offer_id': room['offers'][1]['offer_id'],
            'price': 0,
        },
    )
    with _as_staff(leader_id, 'CombatLeader'):
        rejected = client.post(f'/api/story/coop/run/{run_id}/action', json=forged)
    assert rejected.status_code == 400
    assert rejected.get_json()['code'] == 'INVALID_ACTION_PAYLOAD'


def test_personal_chest_api_redacts_other_seat_amount_and_rejects_forged_gold(
    coop_combat_api,
):
    client = coop_combat_api
    leader_id, member_id, started = _start_party(client)
    run_id = started['run']['id']
    state = _install_personal_or_shared_room(leader_id, run_id, 'chest')
    leader_amount = state['room_states_by_player']['0']['gold']
    member_amount = state['room_states_by_player']['1']['gold']

    with _as_staff(leader_id, 'CombatLeader'):
        leader_run = client.get(f'/api/story/coop/run/{run_id}').get_json()['run']
    with _as_staff(member_id, 'CombatMember'):
        member_run = client.get(f'/api/story/coop/run/{run_id}').get_json()['run']
    assert leader_run['snapshot']['room_state']['gold'] == leader_amount
    assert member_run['snapshot']['room_state']['gold'] == member_amount
    assert 'room_states_by_player' not in json.dumps(leader_run, ensure_ascii=False)
    assert 'room_states_by_player' not in json.dumps(member_run, ensure_ascii=False)

    forged = _journey_action_body(
        leader_run,
        'http-chest-forged-gold',
        'room_choose',
        {
            'room_id': leader_run['snapshot']['room_state']['room_id'],
            'choice': 'claim_gold',
            'gold': 99999,
        },
    )
    with _as_staff(leader_id, 'CombatLeader'):
        rejected = client.post(f'/api/story/coop/run/{run_id}/action', json=forged)
    assert rejected.status_code == 400
    assert rejected.get_json()['code'] == 'INVALID_ACTION_PAYLOAD'

    accepted_body = _journey_action_body(
        leader_run,
        'http-chest-claim-1',
        'room_choose',
        {
            'room_id': leader_run['snapshot']['room_state']['room_id'],
            'choice': 'claim_gold',
        },
    )
    with _as_staff(leader_id, 'CombatLeader'):
        accepted = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=accepted_body,
        )
    assert accepted.status_code == 200
    payload = accepted.get_json()
    claim_event = next(
        event for event in payload['events']
        if event['type'] == 'coop_chest_gold_claimed'
    )
    assert 'amount' not in claim_event
    assert payload['run']['snapshot']['room_state']['status'] == 'resolved'
    _assert_no_server_state(payload)


def test_shared_event_api_hides_votes_and_requires_consensus_before_effects(
    coop_combat_api,
):
    client = coop_combat_api
    leader_id, member_id, started = _start_party(client)
    run_id = started['run']['id']
    _install_personal_or_shared_room(leader_id, run_id, 'event')

    with _as_staff(leader_id, 'CombatLeader'):
        leader_run = client.get(f'/api/story/coop/run/{run_id}').get_json()['run']
    room = leader_run['snapshot']['room_state']
    first_body = _journey_action_body(
        leader_run,
        'http-event-vote-leader',
        'room_choose',
        {'room_id': room['room_id'], 'choice': 'mend'},
    )
    with _as_staff(leader_id, 'CombatLeader'):
        first = client.post(f'/api/story/coop/run/{run_id}/action', json=first_body)
    assert first.status_code == 200
    first_payload = first.get_json()
    assert first_payload['run']['snapshot']['phase'] == 'room'
    assert first_payload['run']['snapshot']['room_state']['seats'][0]['submitted'] is True
    assert all('choice' not in event for event in first_payload['events'])
    assert 'votes_by_seat' not in json.dumps(first_payload, ensure_ascii=False)

    forged_effect = _journey_action_body(
        first_payload['run'],
        'http-event-forged-effect',
        'room_choose',
        {
            'room_id': room['room_id'],
            'choice': 'risk',
            'gold': 99999,
        },
    )
    with _as_staff(member_id, 'CombatMember'):
        rejected = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=forged_effect,
        )
    assert rejected.status_code == 400
    assert rejected.get_json()['code'] == 'INVALID_ACTION_PAYLOAD'

    member_body = _journey_action_body(
        first_payload['run'],
        'http-event-vote-member',
        'room_choose',
        {'room_id': room['room_id'], 'choice': 'risk'},
    )
    with _as_staff(member_id, 'CombatMember'):
        split = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=member_body,
        )
    assert split.status_code == 200
    split_payload = split.get_json()
    assert split_payload['run']['snapshot']['phase'] == 'room'
    assert split_payload['run']['snapshot']['room_state']['seats'] == [
        {'seat': 0, 'submitted': False},
        {'seat': 1, 'submitted': False},
    ]
    assert [event['type'] for event in split_payload['events']] == [
        'coop_event_vote_cast',
        'coop_event_consensus_required',
    ]
    assert all('choice' not in event for event in split_payload['events'])

    with _as_staff(leader_id, 'CombatLeader'):
        retry_leader_run = client.get(f'/api/story/coop/run/{run_id}').get_json()['run']
        retry_leader = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=_journey_action_body(
                retry_leader_run,
                'http-event-retry-leader',
                'room_choose',
                {'room_id': room['room_id'], 'choice': 'mend'},
            ),
        )
    assert retry_leader.status_code == 200
    with _as_staff(member_id, 'CombatMember'):
        retry_member_run = client.get(f'/api/story/coop/run/{run_id}').get_json()['run']
        resolved = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=_journey_action_body(
                retry_member_run,
                'http-event-retry-member',
                'room_choose',
                {'room_id': room['room_id'], 'choice': 'mend'},
            ),
        )
    assert resolved.status_code == 200
    resolved_payload = resolved.get_json()
    assert resolved_payload['run']['snapshot']['phase'] == 'map'
    event = next(event for event in resolved_payload['events'] if event['type'] == 'coop_event_resolved')
    assert event['choice'] == 'mend'
    assert event['reason'] == 'unanimous'
    _assert_no_server_state(resolved_payload)


def test_final_boss_action_keeps_run_active_until_both_members_start_stage_two(
    coop_combat_api,
):
    client = coop_combat_api
    leader_id, member_id, started = _start_party(client)
    run_id = started['run']['id']
    card_instance_id, boss_id = _install_final_boss_combat(leader_id, run_id)

    with _as_staff(leader_id, 'CombatLeader'):
        current = client.get(f'/api/story/coop/run/{run_id}').get_json()['run']
        body = _action_body(
            current,
            'http-stage1-boss-final',
            'play_card',
            {
                'card_instance_id': card_instance_id,
                'target_enemy_id': boss_id,
            },
        )
        completed = client.post(f'/api/story/coop/run/{run_id}/action', json=body)
    assert completed.status_code == 200
    completed_payload = completed.get_json()
    completed_run = completed_payload['run']
    assert completed_run['status'] == 'active'
    assert completed_run['snapshot']['phase'] == 'stage_complete'
    assert completed_run['snapshot']['progression']['completed_stage'] == 1
    assert any(
        event['type'] == 'coop_stage_completed'
        for event in completed_payload['events']
    )
    _assert_no_server_state(completed_payload)

    with _as_staff(member_id, 'CombatMember'):
        historical = client.get(f'/api/story/coop/run/{run_id}')
        party = client.get('/api/story/coop/party')
    assert historical.status_code == 200
    assert historical.get_json()['run']['snapshot']['phase'] == 'stage_complete'
    assert party.get_json()['party']['status'] == 'active'

    with _as_staff(leader_id, 'CombatLeader'):
        duplicate = client.post(f'/api/story/coop/run/{run_id}/action', json=body)
    assert duplicate.status_code == 200
    assert duplicate.get_json()['duplicate'] is True
    assert duplicate.get_json()['events'] == []

    room_id = completed_run['snapshot']['room']['id']
    with _as_staff(leader_id, 'CombatLeader'):
        current = client.get(f'/api/story/coop/run/{run_id}').get_json()['run']
        leader_ready = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=_journey_action_body(
                current,
                'http-stage1-ready-leader',
                'stage_ready',
                {'room_id': room_id},
            ),
        )
    assert leader_ready.status_code == 200
    assert leader_ready.get_json()['run']['snapshot']['phase'] == 'stage_complete'

    with _as_staff(member_id, 'CombatMember'):
        current = client.get(f'/api/story/coop/run/{run_id}').get_json()['run']
        member_ready = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=_journey_action_body(
                current,
                'http-stage1-ready-member',
                'stage_ready',
                {'room_id': room_id},
            ),
        )
    assert member_ready.status_code == 200
    stage_two = member_ready.get_json()['run']
    assert stage_two['status'] == 'active'
    assert stage_two['snapshot']['phase'] == 'room'
    assert stage_two['snapshot']['room']['type'] == 'opening'
    assert stage_two['snapshot']['stage'] == 2
    assert stage_two['snapshot']['biome'] == 'jungle'


def test_reward_route_vote_and_followup_combat_share_one_authoritative_action_log(coop_combat_api):
    client = coop_combat_api
    leader_id, member_id, started = _start_party(client)
    run_id = started['run']['id']
    raw_run = db.get_story_coop_run_for_member(leader_id, run_id)
    state = raw_run['state']
    seat_state = state['combat']['seat_states']['0']
    basic = next(
        card
        for zone_name in ('hand', 'draw_pile')
        for card in seat_state[zone_name]
        if card['def_id'] == 'basic'
    )
    if basic not in seat_state['hand']:
        seat_state['draw_pile'].remove(basic)
        seat_state['hand'].append(basic)
    state['combat']['enemies'][0]['health'] = 6
    for enemy in state['combat']['enemies'][1:]:
        enemy['health'] = 0
    target_enemy_id = state['combat']['enemies'][0]['id']
    with db.get_db_connection() as conn:
        conn.execute(
            'UPDATE story_coop_runs SET state_json = ? WHERE id = ?',
            (
                json.dumps(
                    state,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(',', ':'),
                ),
                run_id,
            ),
        )
        conn.commit()

    with _as_staff(leader_id, 'CombatLeader'):
        current = client.get(f'/api/story/coop/run/{run_id}').get_json()['run']
        victory = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=_action_body(
                current,
                'journey-win-0001',
                'play_card',
                {
                    'card_instance_id': basic['instance_id'],
                    'target_enemy_id': target_enemy_id,
                },
            ),
        )
    assert victory.status_code == 200
    reward_run = victory.get_json()['run']
    assert reward_run['snapshot']['phase'] == 'reward'
    assert reward_run['snapshot']['combat'] is None
    assert reward_run['snapshot']['reward']['status'] == 'pending'
    assert len(reward_run['snapshot']['reward']['options']) == 3
    _assert_no_server_state(victory.get_json())

    leader_reward = reward_run['snapshot']['reward']
    leader_card_id = leader_reward['options'][0]['card_id']
    leader_reward_body = _journey_action_body(
        reward_run,
        'journey-reward-0001',
        'reward_choose',
        {
            'reward_id': leader_reward['reward_id'],
            'card_id': leader_card_id,
        },
    )
    with _as_staff(leader_id, 'CombatLeader'):
        leader_choice = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=leader_reward_body,
        )
        duplicate_choice = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=leader_reward_body,
        )
    assert leader_choice.status_code == 200
    assert leader_choice.get_json()['run']['snapshot']['phase'] == 'reward'
    assert leader_choice.get_json()['run']['snapshot']['reward']['status'] == 'resolved'
    assert duplicate_choice.status_code == 200
    assert duplicate_choice.get_json()['duplicate'] is True
    assert duplicate_choice.get_json()['events'] == []

    with _as_staff(member_id, 'CombatMember'):
        member_view = client.get(f'/api/story/coop/run/{run_id}').get_json()['run']
    assert member_view['snapshot']['reward']['status'] == 'pending'
    assert member_view['snapshot']['reward']['selected_card_id'] is None
    assert leader_card_id not in json.dumps(
        member_view['snapshot']['last_events'],
        ensure_ascii=False,
    )
    member_reward = member_view['snapshot']['reward']
    with _as_staff(member_id, 'CombatMember'):
        map_started = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=_journey_action_body(
                member_view,
                'journey-reward-0002',
                'reward_choose',
                {'reward_id': member_reward['reward_id'], 'card_id': ''},
            ),
        )
    assert map_started.status_code == 200
    map_run = map_started.get_json()['run']
    assert map_run['snapshot']['phase'] == 'map'
    assert len(map_run['snapshot']['map_vote']['options']) >= 2
    assert not any('node_id' in item for item in map_run['snapshot']['map_vote']['seats'])

    vote = map_run['snapshot']['map_vote']
    first_node = vote['options'][0]['node_id']
    second_node = vote['options'][1]['node_id']
    with _as_staff(leader_id, 'CombatLeader'):
        first_vote = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=_journey_action_body(
                map_run,
                'journey-route-0001',
                'map_vote',
                {'vote_id': vote['vote_id'], 'node_id': first_node},
            ),
        )
    assert first_vote.status_code == 200
    waiting_run = first_vote.get_json()['run']
    assert waiting_run['snapshot']['phase'] == 'map'
    assert waiting_run['snapshot']['map_vote']['viewer_node_id'] == first_node

    with _as_staff(member_id, 'CombatMember'):
        member_waiting = client.get(f'/api/story/coop/run/{run_id}').get_json()['run']
        second_vote_body = _journey_action_body(
            member_waiting,
            'journey-route-0002',
            'map_vote',
            {
                'vote_id': member_waiting['snapshot']['map_vote']['vote_id'],
                'node_id': second_node,
            },
        )
        second_combat = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=second_vote_body,
        )
    assert second_combat.status_code == 200
    second_run = second_combat.get_json()['run']
    assert second_run['snapshot']['phase'] == 'combat'
    assert second_run['snapshot']['current_floor'] == 3
    assert second_run['snapshot']['combat']['enemies']
    assert second_run['snapshot']['combat']['id'].startswith('garden-route-')
    assert all(
        event['action_sequence'] == second_run['snapshot']['action_sequence']
        for event in second_combat.get_json()['events']
    )
    _assert_no_server_state(second_combat.get_json())

    raw_second = db.get_story_coop_run_for_member(leader_id, run_id)['state']
    assert any(card['def_id'] == leader_card_id for card in raw_second['players']['0']['deck'])
    assert not any(card['def_id'] == leader_card_id for card in raw_second['players']['1']['deck'])
    all_zone_cards = [
        card
        for zone_name in ('hand', 'draw_pile', 'discard_pile', 'exile_pile')
        for card in raw_second['combat']['seat_states']['0'][zone_name]
    ]
    assert any(card['def_id'] == leader_card_id for card in all_zone_cards)

    second_seat = raw_second['combat']['seat_states']['0']
    finisher = next(
        card
        for zone_name in ('hand', 'draw_pile', 'discard_pile')
        for card in second_seat[zone_name]
        if card['def_id'] == 'basic'
    )
    for zone_name in ('draw_pile', 'discard_pile'):
        if finisher in second_seat[zone_name]:
            second_seat[zone_name].remove(finisher)
            second_seat['hand'].append(finisher)
    final_enemy = raw_second['combat']['enemies'][0]
    final_enemy['health'] = 6
    for enemy in raw_second['combat']['enemies'][1:]:
        enemy['health'] = 0
    with db.get_db_connection() as conn:
        conn.execute(
            'UPDATE story_coop_runs SET state_json = ? WHERE id = ?',
            (
                json.dumps(
                    raw_second,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(',', ':'),
                ),
                run_id,
            ),
        )
        conn.commit()
    with _as_staff(leader_id, 'CombatLeader'):
        before_final = client.get(f'/api/story/coop/run/{run_id}').get_json()['run']
        final_body = _action_body(
            before_final,
            'journey-final-0001',
            'play_card',
            {
                'card_instance_id': finisher['instance_id'],
                'target_enemy_id': final_enemy['id'],
            },
        )
        completed = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=final_body,
        )
    assert completed.status_code == 200
    completed_run = completed.get_json()['run']
    assert completed_run['status'] == 'active'
    assert completed_run['snapshot']['phase'] == 'reward'
    assert completed_run['snapshot']['combat'] is None
    assert completed_run['snapshot']['progression']['completed'] is False
    assert any(
        event['type'] == 'coop_rewards_started'
        for event in completed.get_json()['events']
    )
    with _as_staff(member_id, 'CombatMember'):
        historical = client.get(f'/api/story/coop/run/{run_id}')
        active_party = client.get('/api/story/coop/party')
    assert historical.status_code == 200
    assert historical.get_json()['run']['snapshot']['phase'] == 'reward'
    assert active_party.get_json()['party']['status'] == 'active'
    with _as_staff(leader_id, 'CombatLeader'):
        duplicate_final = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=final_body,
        )
    assert duplicate_final.status_code == 200
    assert duplicate_final.get_json()['duplicate'] is True
    assert duplicate_final.get_json()['events'] == []

    forged_context = copy.deepcopy(
        _journey_action_body(
            map_run,
            'journey-forged-context',
            'map_vote',
            {'vote_id': vote['vote_id'], 'node_id': first_node},
        )
    )
    forged_context['combat_id'] = 'stale-combat'
    forged_context['combat_round'] = 1
    with _as_staff(leader_id, 'CombatLeader'):
        rejected = client.post(
            f'/api/story/coop/run/{run_id}/action',
            json=forged_context,
        )
    assert rejected.status_code == 400
    assert rejected.get_json()['code'] == 'INVALID_ACTION_REQUEST'
