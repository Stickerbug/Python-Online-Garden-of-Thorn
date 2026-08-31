import contextlib
from unittest import mock

import app as gtn
from db import StoryCoopDataError
from story_progress import build_story_progress_payload


def _bundle(*, status='forming', revision=2, viewer_role='leader', run=None):
    members = [
        {
            'seat': 0,
            'user_id': 41,
            'username': 'StoryLeader',
            'display_name': 'StoryLeader',
            'membership_status': 'active',
            'party_role': 'leader',
        },
        {
            'seat': 1,
            'user_id': 52,
            'username': 'StoryMember',
            'display_name': 'StoryMember',
            'membership_status': 'active',
            'party_role': 'member',
        },
    ]
    return {
        'party': {
            'id': 'a' * 32,
            'status': status,
            'revision': revision,
            'min_players': 2,
            'max_players': 2,
            'members': members,
            'created_at': '2026-08-22T00:00:00Z',
            'updated_at': '2026-08-22T00:00:00Z',
            'closed_at': None,
        },
        'viewer': {
            'seat': 0 if viewer_role == 'leader' else 1,
            'party_role': viewer_role,
            'can_start': viewer_role == 'leader' and status == 'forming',
        },
        'run': run,
    }


@contextlib.contextmanager
def _staff_request_context(*, user_id=41):
    with (
        mock.patch.object(
            gtn,
            '_require_account_json',
            return_value=(user_id, 'StoryLeader', None),
        ),
        mock.patch.object(gtn, 'feedback_is_staff', return_value=True),
        mock.patch.object(gtn, 'STORY_COOP_ENABLED', True),
        mock.patch.object(gtn, 'rate_limiter', return_value=True),
    ):
        yield


def test_all_party_routes_fail_closed_before_storage_for_regular_accounts():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    storage_names = (
        'get_active_story_coop_party',
        'create_story_coop_party',
        'join_story_coop_party',
        'leave_story_coop_party',
        'rotate_story_coop_invite',
        'abandon_story_coop_run',
        'create_story_coop_run',
        'get_story_coop_run_for_member',
        'get_story_coop_action_receipt',
        'commit_story_coop_run_action',
    )
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(
            gtn,
            '_require_account_json',
            return_value=(41, 'RegularPlayer', None),
        ))
        stack.enter_context(mock.patch.object(gtn, 'feedback_is_staff', return_value=False))
        stack.enter_context(mock.patch.object(gtn, 'STORY_COOP_ENABLED', True))
        storage_entered = [
            stack.enter_context(mock.patch.object(gtn, name))
            for name in storage_names
        ]
        responses = [
            client.get('/api/story/coop/party'),
            client.post('/api/story/coop/party', json={}),
            client.post('/api/story/coop/party/join', json={'invite_code': 'x' * 24}),
            client.post(
                '/api/story/coop/party/leave',
                json={'party_id': 'a' * 32, 'party_revision': 1},
            ),
            client.post(
                '/api/story/coop/party/start',
                json={'party_id': 'a' * 32, 'party_revision': 1},
            ),
            client.post(
                '/api/story/coop/party/invite',
                json={'party_id': 'a' * 32, 'party_revision': 1},
            ),
            client.post(
                '/api/story/coop/party/abandon',
                json={'party_id': 'a' * 32, 'party_revision': 1},
            ),
            client.get('/api/story/coop/run/' + ('b' * 32)),
            client.post(
                '/api/story/coop/run/' + ('b' * 32) + '/action',
                json={
                    'party_id': 'a' * 32,
                    'run_id': 'b' * 32,
                    'run_revision': 1,
                    'action_id': 'regular-action-1',
                    'action_type': 'combat_ready',
                    'combat_id': 'combat-1',
                    'combat_round': 1,
                    'expected_sequence': 0,
                    'payload': {},
                },
            ),
        ]

    assert all(response.status_code == 404 for response in responses)
    assert all(response.get_json()['code'] == 'COOP_STORY_DISABLED' for response in responses)
    assert all(response.headers['Cache-Control'] == 'private, no-store' for response in responses)
    for storage_mock in storage_entered:
        storage_mock.assert_not_called()


def test_party_get_and_create_return_private_no_store_envelopes():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    bundle = _bundle()
    with (
        _staff_request_context(),
        mock.patch.object(gtn, 'rate_limiter', return_value=True),
        mock.patch.object(gtn, 'get_active_story_coop_party', return_value=None),
        mock.patch.object(
            gtn,
            'create_story_coop_party',
            return_value=(bundle, 'invite-once-token-value', 'created'),
        ),
    ):
        current = client.get('/api/story/coop/party')
        created = client.post('/api/story/coop/party', json={'seat': 99, 'user_id': 999})

    assert current.status_code == 200
    assert current.get_json()['party'] is None
    payload = created.get_json()
    assert created.status_code == 200
    assert payload['created'] is True
    assert payload['invite_code'] == 'invite-once-token-value'
    assert payload['party']['members'][0]['user_id'] == 41
    assert created.headers['Cache-Control'] == 'private, no-store'


def test_party_create_rejects_non_object_json_before_storage():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    with (
        _staff_request_context(),
        mock.patch.object(gtn, 'rate_limiter', return_value=True) as limiter,
        mock.patch.object(gtn, 'create_story_coop_party') as create_mock,
    ):
        response = client.post('/api/story/coop/party', json=['not', 'an', 'object'])

    assert response.status_code == 400
    assert response.get_json()['code'] == 'INVALID_REQUEST'
    limiter.assert_not_called()
    create_mock.assert_not_called()


def test_join_is_rate_limited_by_account_and_ip_before_lookup():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    with (
        _staff_request_context(),
        mock.patch.object(gtn, 'rate_limiter', return_value=False),
        mock.patch.object(gtn, 'join_story_coop_party') as join_mock,
    ):
        response = client.post(
            '/api/story/coop/party/join',
            json={'invite_code': 'x' * 24},
        )

    assert response.status_code == 429
    assert response.get_json()['code'] == 'COOP_INVITE_RATE_LIMITED'
    join_mock.assert_not_called()


def test_join_maps_invalid_invite_and_never_accepts_actor_fields():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    with (
        _staff_request_context(),
        mock.patch.object(gtn, 'rate_limiter', return_value=True),
        mock.patch.object(
            gtn,
            'join_story_coop_party',
            side_effect=StoryCoopDataError('INVALID_INVITE_CODE', '邀请码格式无效'),
        ) as join_mock,
    ):
        response = client.post(
            '/api/story/coop/party/join',
            json={
                'invite_code': 'bad',
                'user_id': 999,
                'seat': 0,
                'party_role': 'leader',
            },
        )

    assert response.status_code == 400
    assert response.get_json()['code'] == 'INVALID_INVITE_CODE'
    join_mock.assert_called_once_with(41, 'bad')

    with (
        _staff_request_context(),
        mock.patch.object(gtn, 'join_story_coop_party') as malformed_join,
    ):
        malformed = client.post('/api/story/coop/party/join', json=['not', 'an', 'object'])
    assert malformed.status_code == 400
    assert malformed.get_json()['code'] == 'INVALID_REQUEST'
    malformed_join.assert_not_called()


def test_start_builds_state_from_server_party_members_and_maps_success():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    forming = _bundle()

    def create_run_result(*args):
        state = args[5]
        return (_bundle(
            status='active',
            revision=3,
            run={
                'id': 'b' * 32,
                'party_id': 'a' * 32,
                'status': 'active',
                'revision': 1,
                'schema_version': 10,
                'content_version': state['content_version'],
                'seed': args[3],
                'state': state,
            },
        ), 'created')

    with (
        _staff_request_context(),
        mock.patch.object(gtn, 'get_active_story_coop_party', return_value=forming),
        mock.patch.object(gtn.secrets, 'token_hex', return_value='server-seed'),
        mock.patch.object(
            gtn,
            'create_story_coop_run',
            side_effect=create_run_result,
        ) as create_run,
    ):
        response = client.post(
            '/api/story/coop/party/start',
            json={
                'party_id': 'a' * 32,
                'party_revision': 2,
                'members': [{'user_id': 999, 'seat': 0}],
                'seed': 'attacker-seed',
            },
        )

    assert response.status_code == 200
    response_payload = response.get_json()
    assert response_payload['started'] is True
    assert 'seed' not in response_payload['run']
    assert 'state' not in response_payload['run']
    assert response_payload['run']['snapshot']['phase'] == 'journey_setup'
    assert response_payload['run']['snapshot']['combat'] is None
    assert response_payload['run']['snapshot']['room']['biomes'] == ['garden']
    assert response_payload['run']['snapshot']['room']['difficulties'] == ['normal']
    args = create_run.call_args.args
    assert args[:5] == (
        41,
        'a' * 32,
        2,
        'server-seed',
        gtn.COOP_STORY_CONTENT_VERSION,
    )
    generated_state = args[5]
    assert [member['user_id'] for member in generated_state['party']['members']] == [41, 52]
    assert generated_state['party']['leader_seat'] == 0


def test_start_accepts_mage_only_when_every_member_has_unlocked_it():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    forming = _bundle()
    mage_progress = build_story_progress_payload([{
        'character_id': 'common_flower',
        'difficulty': 'normal',
        'standard_clears': 1,
    }])

    def create_run_result(*args):
        state = args[5]
        return (_bundle(
            status='active',
            revision=3,
            run={
                'id': 'b' * 32,
                'party_id': 'a' * 32,
                'status': 'active',
                'revision': 1,
                'schema_version': 10,
                'content_version': state['content_version'],
                'seed': args[3],
                'state': state,
            },
        ), 'created')

    with (
        _staff_request_context(),
        mock.patch.object(gtn, 'get_active_story_coop_party', return_value=forming),
        mock.patch.object(
            gtn,
            'get_story_progress_for_users',
            return_value={41: mage_progress, 52: mage_progress},
        ),
        mock.patch.object(gtn, 'create_story_coop_run', side_effect=create_run_result),
    ):
        response = client.post(
            '/api/story/coop/party/start',
            json={
                'party_id': 'a' * 32,
                'party_revision': 2,
                'character_id': 'mage',
            },
        )

    assert response.status_code == 200
    snapshot = response.get_json()['run']['snapshot']
    assert snapshot['character_id'] == 'mage'
    assert snapshot['room']['difficulties'] == ['normal']

    with (
        _staff_request_context(),
        mock.patch.object(gtn, 'get_active_story_coop_party', return_value=forming),
        mock.patch.object(
            gtn,
            'get_story_progress_for_users',
            return_value={
                41: mage_progress,
                52: build_story_progress_payload(),
            },
        ),
        mock.patch.object(gtn, 'create_story_coop_run') as create_run,
    ):
        locked = client.post(
            '/api/story/coop/party/start',
            json={
                'party_id': 'a' * 32,
                'party_revision': 2,
                'character_id': 'mage',
            },
        )

    assert locked.status_code == 409
    assert locked.get_json()['code'] == 'COOP_STORY_CHARACTER_LOCKED'
    create_run.assert_not_called()


def test_leave_requires_strict_integer_revision_and_maps_version_conflict():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    bundle = _bundle(revision=3)
    with (
        _staff_request_context(),
        mock.patch.object(gtn, 'leave_story_coop_party') as leave_mock,
    ):
        invalid = client.post(
            '/api/story/coop/party/leave',
            json={'party_id': 'a' * 32, 'party_revision': 2.0},
        )
    assert invalid.status_code == 400
    assert invalid.get_json()['code'] == 'INVALID_PARTY_VERSION'
    leave_mock.assert_not_called()

    with (
        _staff_request_context(),
        mock.patch.object(
            gtn,
            'leave_story_coop_party',
            return_value=(bundle, 'version'),
        ),
    ):
        stale = client.post(
            '/api/story/coop/party/leave',
            json={'party_id': 'a' * 32, 'party_revision': 2},
        )
    assert stale.status_code == 409
    assert stale.get_json()['code'] == 'COOP_PARTY_VERSION_OLD'
    assert stale.get_json()['party']['revision'] == 3


def test_invite_rotation_and_active_abandon_have_explicit_lifecycle_responses():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    forming = _bundle(revision=3)
    with (
        _staff_request_context(),
        mock.patch.object(gtn, 'rate_limiter', return_value=True),
        mock.patch.object(
            gtn,
            'rotate_story_coop_invite',
            return_value=(forming, 'rotated-once-token', 'rotated'),
        ) as rotate_mock,
    ):
        rotated = client.post(
            '/api/story/coop/party/invite',
            json={'party_id': 'a' * 32, 'party_revision': 2},
        )
    assert rotated.status_code == 200
    assert rotated.get_json()['rotated'] is True
    assert rotated.get_json()['invite_code'] == 'rotated-once-token'
    rotate_mock.assert_called_once_with(41, 'a' * 32, 2)

    with (
        _staff_request_context(),
        mock.patch.object(
            gtn,
            'abandon_story_coop_run',
            return_value=(None, 'abandoned'),
        ) as abandon_mock,
    ):
        abandoned = client.post(
            '/api/story/coop/party/abandon',
            json={'party_id': 'a' * 32, 'party_revision': 3},
        )
    assert abandoned.status_code == 200
    assert abandoned.get_json() == {
        'success': True,
        'abandoned': True,
        'party': None,
        'viewer': None,
        'run': None,
    }
    abandon_mock.assert_called_once_with(41, 'a' * 32, 3)
