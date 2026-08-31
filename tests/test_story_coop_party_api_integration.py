import contextlib
from unittest import mock

import pytest

import app as gtn
import db


@pytest.fixture()
def coop_api_database(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'coop-api.sqlite3'))
    db.init_db()
    return tmp_path


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


def test_full_staff_party_http_lifecycle_uses_authoritative_database(
    coop_api_database,
):
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    leader_id = _insert_staff('HttpLeader', 'admin')
    member_id = _insert_staff('HttpMember', 'staff')

    with _as_staff(leader_id, 'HttpLeader'):
        created = client.post('/api/story/coop/party', json={'seat': 99})
    assert created.status_code == 200
    created_payload = created.get_json()
    invite_code = created_payload['invite_code']
    assert created_payload['party']['members'][0]['user_id'] == leader_id
    assert created_payload['party']['members'][0]['seat'] == 0
    assert created.headers['Cache-Control'] == 'private, no-store'

    with _as_staff(member_id, 'HttpMember'):
        joined = client.post(
            '/api/story/coop/party/join',
            json={
                'invite_code': invite_code,
                'user_id': leader_id,
                'seat': 0,
                'party_role': 'leader',
            },
        )
    assert joined.status_code == 200
    joined_payload = joined.get_json()
    assert joined_payload['viewer']['seat'] == 1
    assert joined_payload['viewer']['party_role'] == 'member'
    assert [member['user_id'] for member in joined_payload['party']['members']] == [
        leader_id,
        member_id,
    ]

    party_id = joined_payload['party']['id']
    party_revision = joined_payload['party']['revision']
    with _as_staff(member_id, 'HttpMember'):
        forbidden = client.post(
            '/api/story/coop/party/start',
            json={'party_id': party_id, 'party_revision': party_revision},
        )
    assert forbidden.status_code == 403
    assert forbidden.get_json()['code'] == 'COOP_PARTY_LEADER_REQUIRED'

    with _as_staff(leader_id, 'HttpLeader'):
        started = client.post(
            '/api/story/coop/party/start',
            json={
                'party_id': party_id,
                'party_revision': party_revision,
                'seed': 'client-must-not-control-this',
                'members': [{'user_id': 999, 'seat': 0}],
            },
        )
    assert started.status_code == 200
    started_payload = started.get_json()
    assert started_payload['started'] is True
    assert started_payload['party']['status'] == 'active'
    assert started_payload['run']['schema_version'] == 10
    assert 'seed' not in started_payload['run']
    assert 'state' not in started_payload['run']
    assert started_payload['run']['snapshot']['phase'] == 'journey_setup'
    assert started_payload['run']['snapshot']['combat'] is None
    assert started_payload['run']['snapshot']['room']['difficulties'] == ['normal']
    assert [
        member['user_id']
        for member in started_payload['run']['snapshot']['party']['members']
    ] == [leader_id, member_id]

    with _as_staff(member_id, 'HttpMember'):
        member_view = client.get('/api/story/coop/party')
    assert member_view.status_code == 200
    assert member_view.get_json()['run']['id'] == started_payload['run']['id']

    with _as_staff(member_id, 'HttpMember'):
        abandoned = client.post(
            '/api/story/coop/party/abandon',
            json={
                'party_id': party_id,
                'party_revision': started_payload['party']['revision'],
            },
        )
    assert abandoned.status_code == 200
    assert abandoned.get_json()['abandoned'] is True

    for user_id, username in ((leader_id, 'HttpLeader'), (member_id, 'HttpMember')):
        with _as_staff(user_id, username):
            current = client.get('/api/story/coop/party')
        assert current.status_code == 200
        assert current.get_json() == {
            'success': True,
            'party': None,
            'viewer': None,
            'run': None,
        }

    with db.get_db_connection() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM story_coop_parties WHERE status = 'active'"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM story_coop_runs WHERE status = 'active'"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM story_coop_party_members WHERE membership_status = 'active'"
        ).fetchone()[0] == 0
