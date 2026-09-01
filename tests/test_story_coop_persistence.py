import copy
import concurrent.futures
import hashlib
import json
import sqlite3

import pytest

import db
from story_coop import build_initial_coop_story_state
from story_coop_combat import COOP_COMBAT_ENDED, _canonical_request_fingerprint
from story_coop_live import (
    COOP_STORY_CONTENT_VERSION,
    advance_coop_after_victory,
    apply_coop_journey_command,
    prepare_coop_stage1_setup,
    start_coop_stage1_opening,
)
from story_mode import build_initial_story_state


@pytest.fixture()
def isolated_story_db(tmp_path, monkeypatch):
    database_path = tmp_path / 'story-coop.sqlite3'
    monkeypatch.setattr(db, 'DB_PATH', str(database_path))
    db.init_db()
    return database_path


def _insert_user(username, *, role='staff', banned=False, deleted=False):
    now = db.utc_now()
    with db.get_db_connection() as conn:
        cursor = conn.execute(
            '''INSERT INTO users
               (username, username_lower, password_hash, created_at, banned,
                deleted_at)
               VALUES (?, ?, 'test-hash', ?, ?, ?)''',
            (
                username,
                username.lower(),
                now,
                1 if banned else 0,
                now if deleted else None,
            ),
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


def _forming_party():
    leader_id = _insert_user('coop-leader', role='admin')
    member_id = _insert_user('coop-member', role='staff')
    leader_bundle, invite_code, create_outcome = db.create_story_coop_party(leader_id)
    assert create_outcome == 'created'
    member_bundle, join_outcome = db.join_story_coop_party(member_id, invite_code)
    assert join_outcome == 'joined'
    return leader_id, member_id, leader_bundle, member_bundle, invite_code


def _started_party():
    leader_id, member_id, _, member_bundle, invite_code = _forming_party()
    party = member_bundle['party']
    state = build_initial_coop_story_state(
        'coop-persistence-seed',
        party['members'],
        max_players=party['max_players'],
    )
    bundle, outcome = db.create_story_coop_run(
        leader_id,
        party['id'],
        party['revision'],
        'coop-persistence-seed',
        state['content_version'],
        state,
    )
    assert outcome == 'created'
    return leader_id, member_id, bundle, invite_code


def _completed_current_journey_state(seed, members, leader_id, member_id):
    state = prepare_coop_stage1_setup(
        build_initial_coop_story_state(seed, members),
    )
    state, _ = start_coop_stage1_opening(
        state,
        run_seed=seed,
        difficulty='normal',
    )
    action_serial = 0

    def action(user_id, action_type, payload):
        nonlocal state, action_serial
        action_serial += 1
        state, _, _ = apply_coop_journey_command(
            state,
            authenticated_user_id=user_id,
            action_id=f'persistence-full-{action_serial:04d}',
            action_type=action_type,
            payload=payload,
            run_seed=seed,
            expected_sequence=state['coordination']['action_sequence'],
        )

    for seat, user_id in ((0, leader_id), (1, member_id)):
        private = state['room_states_by_player'][str(seat)]
        action(user_id, 'opening_choose', {
            'room_id': state['room']['id'],
            'option_id': private['options'][0],
        })
    for _ in range(900):
        phase = state['phase']
        if phase == 'complete':
            return state
        if phase == 'combat':
            for enemy in state['combat']['enemies']:
                enemy['health'] = 0
            state['combat']['turn'] = COOP_COMBAT_ENDED
            state['combat']['outcome'] = 'victory'
            state['coordination']['combat_ready_seats'] = []
            state['coordination']['combat_ready_round'] = None
            advance_coop_after_victory(state, run_seed=seed)
        elif phase == 'reward':
            for seat, user_id in ((0, leader_id), (1, member_id)):
                reward = state['rewards_by_player'][str(seat)]
                action(user_id, 'reward_choose', {
                    'reward_id': reward['reward_id'],
                    'card_id': '',
                })
        elif phase == 'map':
            vote = state['coordination']['map_vote']
            node_id = vote['option_node_ids'][0]
            for user_id in (leader_id, member_id):
                action(user_id, 'map_vote', {
                    'vote_id': vote['vote_id'],
                    'node_id': node_id,
                })
        elif phase == 'room':
            room_type = state['room']['type']
            room_id = state['room']['id']
            for seat, user_id in ((0, leader_id), (1, member_id)):
                private = state['room_states_by_player'][str(seat)]
                if room_type == 'opening':
                    action(user_id, 'opening_choose', {
                        'room_id': room_id,
                        'option_id': private['options'][0],
                    })
                else:
                    choice = 'leave' if 'leave' in private['options'] else private['options'][0]
                    action(user_id, 'room_choose', {
                        'room_id': room_id,
                        'choice': choice,
                    })
        elif phase == 'stage_complete':
            room_id = state['room']['id']
            for user_id in (leader_id, member_id):
                action(user_id, 'stage_ready', {'room_id': room_id})
        else:
            raise AssertionError(f'unexpected cooperative journey phase {phase}')
    raise AssertionError('cooperative journey did not reach complete')


def _combat_receipt(
    *,
    action_id,
    action_type,
    actor_user_id,
    actor_seat,
    sequence,
    combat_id,
    combat_round,
    payload,
):
    envelope = {
        'actor_seat': actor_seat,
        'combat_id': combat_id,
        'combat_round': combat_round,
        'action_type': action_type,
        'payload': payload,
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            envelope,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(',', ':'),
        ).encode('utf-8')
    ).hexdigest()
    return {
        'action_id': action_id,
        'actor_user_id': actor_user_id,
        'actor_seat': actor_seat,
        'action_type': action_type,
        'combat_id': combat_id,
        'combat_round': combat_round,
        'action_sequence': sequence,
        'request_fingerprint': fingerprint,
    }


def _generic_receipt(
    *,
    action_id,
    action_type,
    actor_user_id,
    actor_seat,
    sequence,
    payload,
    **extra,
):
    envelope = {
        'actor_seat': actor_seat,
        'action_type': action_type,
        'payload': payload,
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            envelope,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(',', ':'),
        ).encode('utf-8')
    ).hexdigest()
    return {
        'action_id': action_id,
        'action_type': action_type,
        'actor_user_id': actor_user_id,
        'actor_seat': actor_seat,
        'action_sequence': sequence,
        'request_fingerprint': fingerprint,
        **extra,
    }


def test_schema_is_additive_and_enforces_party_identity(isolated_story_db):
    with db.get_db_connection() as conn:
        tables = {
            row['name']
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert {
            'story_runs',
            'story_run_actions',
            'story_coop_parties',
            'story_coop_party_members',
            'story_coop_runs',
            'story_coop_run_actions',
        } <= tables

        now = db.utc_now()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                '''INSERT INTO story_coop_parties
                   (id, status, max_players, invite_code_hash, revision,
                    created_at, updated_at)
                   VALUES (?, 'forming', 1, ?, 1, ?, ?)''',
                ('f' * 32, '0' * 64, now, now),
            )


def test_create_and_join_store_only_invite_hash_and_assign_server_seats(
    isolated_story_db,
):
    leader_id = _insert_user('hash-leader', role='admin')
    member_id = _insert_user('hash-member', role='staff')
    third_id = _insert_user('hash-third', role='staff')

    leader_bundle, invite_code, outcome = db.create_story_coop_party(leader_id)

    assert outcome == 'created'
    assert invite_code and len(invite_code) >= 20
    assert leader_bundle['viewer'] == {
        'seat': 0,
        'party_role': 'leader',
        'can_start': False,
    }
    assert leader_bundle['party']['members'][0]['user_id'] == leader_id
    assert set(leader_bundle['party']['members'][0]) == {
        'seat',
        'user_id',
        'username',
        'display_name',
        'membership_status',
        'party_role',
    }

    with db.get_db_connection() as conn:
        row = conn.execute(
            'SELECT invite_code_hash FROM story_coop_parties WHERE id = ?',
            (leader_bundle['party']['id'],),
        ).fetchone()
        assert row['invite_code_hash'] == hashlib.sha256(invite_code.encode()).hexdigest()
        assert invite_code not in json.dumps(dict(row))

    member_bundle, join_outcome = db.join_story_coop_party(member_id, invite_code)
    assert join_outcome == 'joined'
    assert member_bundle['viewer']['seat'] == 1
    assert member_bundle['viewer']['party_role'] == 'member'
    assert member_bundle['party']['revision'] == 2
    assert [member['seat'] for member in member_bundle['party']['members']] == [0, 1]

    repeated, repeat_outcome = db.join_story_coop_party(member_id, invite_code)
    assert repeat_outcome == 'existing'
    assert repeated['party']['id'] == member_bundle['party']['id']

    full_bundle, full_outcome = db.join_story_coop_party(third_id, invite_code)
    assert full_bundle is None
    assert full_outcome == 'full'

    existing, repeated_code, repeated_create = db.create_story_coop_party(leader_id)
    assert repeated_create == 'existing'
    assert repeated_code is None
    assert existing['party']['id'] == leader_bundle['party']['id']


def test_concurrent_create_and_last_seat_claim_have_single_winners(
    isolated_story_db,
):
    leader_id = _insert_user('race-leader', role='admin')
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        create_results = list(executor.map(lambda _: db.create_story_coop_party(leader_id), range(2)))
    assert sorted(result[2] for result in create_results) == ['created', 'existing']
    party_ids = {result[0]['party']['id'] for result in create_results}
    assert len(party_ids) == 1
    invite_code = next(result[1] for result in create_results if result[1])

    contender_ids = [
        _insert_user('race-member-a', role='staff'),
        _insert_user('race-member-b', role='staff'),
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        join_results = list(executor.map(
            lambda user_id: db.join_story_coop_party(user_id, invite_code),
            contender_ids,
        ))
    assert sorted(result[1] for result in join_results) == ['full', 'joined']
    with db.get_db_connection() as conn:
        active_count = conn.execute(
            '''SELECT COUNT(*) FROM story_coop_party_members
               WHERE party_id = ? AND membership_status = 'active' ''',
            (next(iter(party_ids)),),
        ).fetchone()[0]
    assert active_count == 2


def test_ineligible_accounts_cannot_create_join_or_start(isolated_story_db):
    ordinary_id = _insert_user('ordinary-member', role='contributor')
    assert db.create_story_coop_party(ordinary_id) == (None, None, 'ineligible')

    leader_id, member_id, _, member_bundle, invite_code = _forming_party()
    with db.get_db_connection() as conn:
        conn.execute(
            "UPDATE user_roles SET role_type = 'contributor' WHERE user_id = ?",
            (member_id,),
        )
        conn.commit()

    state = build_initial_coop_story_state(
        'role-recheck',
        member_bundle['party']['members'],
    )
    result, outcome = db.create_story_coop_run(
        leader_id,
        member_bundle['party']['id'],
        member_bundle['party']['revision'],
        'role-recheck',
        state['content_version'],
        state,
    )
    assert outcome == 'member_ineligible'
    assert result['party']['status'] == 'forming'
    with db.get_db_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM story_coop_runs').fetchone()[0] == 0

    outsider_id = _insert_user('ordinary-joiner', role='contributor')
    assert db.join_story_coop_party(outsider_id, invite_code) == (None, 'ineligible')


def test_forming_leave_dissolves_party_and_releases_all_memberships(
    isolated_story_db,
):
    leader_id, member_id, _, member_bundle, _ = _forming_party()
    party = member_bundle['party']

    result, outcome = db.leave_story_coop_party(
        member_id,
        party['id'],
        party['revision'],
    )

    assert result is None
    assert outcome == 'left'
    assert db.get_active_story_coop_party(leader_id) is None
    assert db.get_active_story_coop_party(member_id) is None
    with db.get_db_connection() as conn:
        party_row = conn.execute(
            'SELECT * FROM story_coop_parties WHERE id = ?',
            (party['id'],),
        ).fetchone()
        assert party_row['status'] == 'abandoned'
        assert party_row['closed_at']
        statuses = conn.execute(
            '''SELECT membership_status FROM story_coop_party_members
               WHERE party_id = ? ORDER BY seat''',
            (party['id'],),
        ).fetchall()
        assert [row['membership_status'] for row in statuses] == ['left', 'left']

    replacement, replacement_code, replacement_outcome = db.create_story_coop_party(
        leader_id
    )
    assert replacement_outcome == 'created'
    assert replacement_code
    assert replacement['party']['id'] != party['id']


def test_start_is_leader_only_versioned_and_idempotent(isolated_story_db):
    leader_id, member_id, _, member_bundle, _ = _forming_party()
    party = member_bundle['party']
    state = build_initial_coop_story_state('start-once', party['members'])

    with pytest.raises(db.StoryCoopDataError) as metadata_error:
        db.create_story_coop_run(
            leader_id,
            party['id'],
            party['revision'],
            'start-once',
            'mismatched-content-version',
            state,
        )
    assert metadata_error.value.code == 'INVALID_RUN_METADATA'

    member_result, member_outcome = db.create_story_coop_run(
        member_id,
        party['id'],
        party['revision'],
        'start-once',
        state['content_version'],
        state,
    )
    assert member_outcome == 'leader_required'
    assert member_result['run'] is None

    stale_result, stale_outcome = db.create_story_coop_run(
        leader_id,
        party['id'],
        party['revision'] - 1,
        'start-once',
        state['content_version'],
        state,
    )
    assert stale_outcome == 'version'
    assert stale_result['party']['revision'] == party['revision']

    started, start_outcome = db.create_story_coop_run(
        leader_id,
        party['id'],
        party['revision'],
        'start-once',
        state['content_version'],
        state,
    )
    assert start_outcome == 'created'
    assert started['party']['status'] == 'active'
    assert started['party']['revision'] == party['revision'] + 1
    assert started['run']['schema_version'] == 10
    assert started['run']['revision'] == 1
    assert started['run']['state'] == json.loads(json.dumps(state, ensure_ascii=False))

    repeated, repeat_outcome = db.create_story_coop_run(
        leader_id,
        party['id'],
        party['revision'],
        'start-once',
        state['content_version'],
        state,
    )
    assert repeat_outcome == 'existing'
    assert repeated['run']['id'] == started['run']['id']
    with db.get_db_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM story_coop_runs').fetchone()[0] == 1

    leave_result, leave_outcome = db.leave_story_coop_party(
        member_id,
        party['id'],
        started['party']['revision'],
    )
    assert leave_outcome == 'already_started'
    assert leave_result['run']['id'] == started['run']['id']


def test_leader_can_rotate_lost_invite_without_storing_plaintext(isolated_story_db):
    leader_id = _insert_user('rotate-leader', role='admin')
    member_id = _insert_user('rotate-member', role='staff')
    bundle, first_code, outcome = db.create_story_coop_party(leader_id)
    assert outcome == 'created'

    rotated, second_code, rotate_outcome = db.rotate_story_coop_invite(
        leader_id,
        bundle['party']['id'],
        bundle['party']['revision'],
    )

    assert rotate_outcome == 'rotated'
    assert second_code and second_code != first_code
    assert rotated['party']['revision'] == bundle['party']['revision'] + 1
    assert db.join_story_coop_party(member_id, first_code) == (None, 'not_found')
    joined, join_outcome = db.join_story_coop_party(member_id, second_code)
    assert join_outcome == 'joined'
    assert joined['viewer']['seat'] == 1
    with db.get_db_connection() as conn:
        stored_hash = conn.execute(
            'SELECT invite_code_hash FROM story_coop_parties WHERE id = ?',
            (bundle['party']['id'],),
        ).fetchone()['invite_code_hash']
    assert stored_hash == hashlib.sha256(second_code.encode('utf-8')).hexdigest()
    assert first_code not in stored_hash and second_code not in stored_hash


def test_active_run_abandon_releases_every_membership_atomically(isolated_story_db):
    leader_id, member_id, bundle, _ = _started_party()
    party_id = bundle['party']['id']
    run_id = bundle['run']['id']

    result, outcome = db.abandon_story_coop_run(
        member_id,
        party_id,
        bundle['party']['revision'],
    )

    assert result is None
    assert outcome == 'abandoned'
    assert db.get_active_story_coop_party(leader_id) is None
    assert db.get_active_story_coop_party(member_id) is None
    with db.get_db_connection() as conn:
        party = conn.execute(
            'SELECT status, closed_at FROM story_coop_parties WHERE id = ?',
            (party_id,),
        ).fetchone()
        run = conn.execute(
            'SELECT status, completed_at, revision FROM story_coop_runs WHERE id = ?',
            (run_id,),
        ).fetchone()
        memberships = conn.execute(
            '''SELECT membership_status, left_at FROM story_coop_party_members
               WHERE party_id = ? ORDER BY seat''',
            (party_id,),
        ).fetchall()
    assert party['status'] == 'abandoned' and party['closed_at']
    assert run['status'] == 'abandoned' and run['completed_at']
    assert run['revision'] == 2
    assert all(row['membership_status'] == 'left' and row['left_at'] for row in memberships)

    replacement, invite_code, replacement_outcome = db.create_story_coop_party(member_id)
    assert replacement_outcome == 'created'
    assert invite_code
    assert replacement['party']['id'] != party_id


def test_actor_aware_action_commit_is_exactly_once_and_cas_guarded(
    isolated_story_db,
):
    leader_id, member_id, bundle, _ = _started_party()
    party_id = bundle['party']['id']
    run = bundle['run']
    context = {'combat_id': 'combat-db-1', 'combat_round': 1}
    first_payload = {'value': 1}
    first_receipt = _combat_receipt(
        action_id='shared-action-id',
        action_type='test_action',
        actor_user_id=leader_id,
        actor_seat=0,
        sequence=1,
        payload=first_payload,
        **context,
    )
    assert first_receipt['request_fingerprint'] == _canonical_request_fingerprint(
        0,
        context['combat_id'],
        context['combat_round'],
        'test_action',
        first_payload,
    )

    first_state = copy.deepcopy(run['state'])
    first_state['coordination']['action_sequence'] = 1
    committed, receipt, outcome = db.commit_story_coop_run_action(
        leader_id,
        party_id,
        run['id'],
        1,
        'shared-action-id',
        'test_action',
        first_payload,
        first_receipt,
        first_state,
        request_context=context,
    )
    assert outcome == 'committed'
    assert committed['revision'] == 2
    assert receipt == first_receipt

    duplicate, duplicate_receipt, duplicate_outcome = db.commit_story_coop_run_action(
        leader_id,
        party_id,
        run['id'],
        1,
        'shared-action-id',
        'test_action',
        {'value': 1},
        {'ignored': True},
        first_state,
        request_context=context,
    )
    assert duplicate_outcome == 'duplicate'
    assert duplicate['revision'] == 2
    assert duplicate_receipt == receipt

    conflict, conflict_receipt, conflict_outcome = db.commit_story_coop_run_action(
        leader_id,
        party_id,
        run['id'],
        1,
        'shared-action-id',
        'test_action',
        {'value': 999},
        {},
        first_state,
        request_context=context,
    )
    assert conflict_outcome == 'action_conflict'
    assert conflict['revision'] == 2
    assert conflict_receipt == receipt

    different_combat, _, different_combat_outcome = db.commit_story_coop_run_action(
        leader_id,
        party_id,
        run['id'],
        1,
        'shared-action-id',
        'test_action',
        first_payload,
        {},
        first_state,
        request_context={'combat_id': 'combat-db-2', 'combat_round': 1},
    )
    assert different_combat_outcome == 'action_conflict'
    assert different_combat['revision'] == 2

    second_state = copy.deepcopy(committed['state'])
    second_state['coordination']['action_sequence'] = 2
    second_payload = {'value': 2}
    second_receipt_input = _combat_receipt(
        action_id='shared-action-id',
        action_type='test_action',
        actor_user_id=member_id,
        actor_seat=1,
        sequence=2,
        payload=second_payload,
        **context,
    )
    second, second_receipt, second_outcome = db.commit_story_coop_run_action(
        member_id,
        party_id,
        run['id'],
        2,
        'shared-action-id',
        'test_action',
        second_payload,
        second_receipt_input,
        second_state,
        request_context=context,
    )
    assert second_outcome == 'committed'
    assert second['revision'] == 3
    assert second_receipt == second_receipt_input

    stale_state = copy.deepcopy(second['state'])
    stale_state['coordination']['action_sequence'] = 3
    stale, stale_receipt, stale_outcome = db.commit_story_coop_run_action(
        leader_id,
        party_id,
        run['id'],
        1,
        'new-stale-action',
        'test_action',
        {},
        {},
        stale_state,
    )
    assert stale_outcome == 'version'
    assert stale['revision'] == 3
    assert stale_receipt is None

    stored = db.get_story_coop_action_receipt(
        leader_id,
        party_id,
        'shared-action-id',
    )
    assert stored['receipt'] == receipt
    with db.get_db_connection() as conn:
        rows = conn.execute(
            '''SELECT actor_user_id, sequence, resulting_revision
               FROM story_coop_run_actions ORDER BY sequence'''
        ).fetchall()
        assert [tuple(row) for row in rows] == [
            (leader_id, 1, 2),
            (member_id, 2, 3),
        ]


def test_concurrent_actions_from_same_revision_commit_only_once(isolated_story_db):
    leader_id, member_id, bundle, _ = _started_party()
    next_state = copy.deepcopy(bundle['run']['state'])
    next_state['coordination']['action_sequence'] = 1

    def submit(user_id, action_id):
        payload = {'from': user_id}
        actor_seat = 0 if user_id == leader_id else 1
        return db.commit_story_coop_run_action(
            user_id,
            bundle['party']['id'],
            bundle['run']['id'],
            1,
            action_id,
            'test_action',
            payload,
            _generic_receipt(
                action_id=action_id,
                action_type='test_action',
                actor_user_id=user_id,
                actor_seat=actor_seat,
                sequence=1,
                payload=payload,
            ),
            next_state,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(submit, leader_id, 'race-action-one'),
            executor.submit(submit, member_id, 'race-action-two'),
        ]
        results = [future.result() for future in futures]

    assert sorted(result[2] for result in results) == ['committed', 'version']
    with db.get_db_connection() as conn:
        run = conn.execute(
            'SELECT revision FROM story_coop_runs WHERE id = ?',
            (bundle['run']['id'],),
        ).fetchone()
        action_count = conn.execute(
            'SELECT COUNT(*) FROM story_coop_run_actions'
        ).fetchone()[0]
    assert run['revision'] == 2
    assert action_count == 1


def test_coop_tables_do_not_modify_existing_solo_run(isolated_story_db):
    leader_id = _insert_user('solo-and-coop', role='admin')
    solo_state = build_initial_story_state('solo-preserved')
    solo_run, created = db.create_story_run(
        leader_id,
        'solo-preserved',
        'story-test-v1',
        solo_state,
    )
    assert created is True
    before = copy.deepcopy(solo_run)

    bundle, invite_code, outcome = db.create_story_coop_party(leader_id)
    assert outcome == 'created'
    assert invite_code
    assert bundle['party']['status'] == 'forming'

    after = db.get_active_story_run(leader_id)
    assert after == before


def test_corrupt_persisted_v10_state_fails_closed(isolated_story_db):
    leader_id, _, bundle, _ = _started_party()
    with db.get_db_connection() as conn:
        conn.execute(
            "UPDATE story_coop_runs SET state_json = '{}' WHERE id = ?",
            (bundle['run']['id'],),
        )
        conn.commit()

    with pytest.raises(db.StoryCoopDataError) as exc_info:
        db.get_active_story_coop_run(leader_id, bundle['party']['id'])
    assert exc_info.value.code == 'CORRUPT_COOP_STORY_STATE'


def test_action_commit_cannot_overwrite_corrupt_current_state(isolated_story_db):
    leader_id, _, bundle, _ = _started_party()
    next_state = copy.deepcopy(bundle['run']['state'])
    next_state['coordination']['action_sequence'] = 1
    with db.get_db_connection() as conn:
        conn.execute(
            "UPDATE story_coop_runs SET state_json = '{}' WHERE id = ?",
            (bundle['run']['id'],),
        )
        conn.commit()

    with pytest.raises(db.StoryCoopDataError) as exc_info:
        db.commit_story_coop_run_action(
            leader_id,
            bundle['party']['id'],
            bundle['run']['id'],
            1,
            'corrupt-guard-action',
            'test_action',
            {},
            {},
            next_state,
        )
    assert exc_info.value.code == 'CORRUPT_COOP_STORY_STATE'
    with db.get_db_connection() as conn:
        row = conn.execute(
            'SELECT revision, state_json FROM story_coop_runs WHERE id = ?',
            (bundle['run']['id'],),
        ).fetchone()
        action_count = conn.execute(
            'SELECT COUNT(*) FROM story_coop_run_actions'
        ).fetchone()[0]
    assert row['revision'] == 1
    assert row['state_json'] == '{}'
    assert action_count == 0


def test_persisted_receipt_missing_authoritative_fields_fails_closed(
    isolated_story_db,
):
    leader_id, _, bundle, _ = _started_party()
    payload = {'value': 1}
    next_state = copy.deepcopy(bundle['run']['state'])
    next_state['coordination']['action_sequence'] = 1
    receipt = _generic_receipt(
        action_id='receipt-integrity-id',
        action_type='test_action',
        actor_user_id=leader_id,
        actor_seat=0,
        sequence=1,
        payload=payload,
    )
    _, _, outcome = db.commit_story_coop_run_action(
        leader_id,
        bundle['party']['id'],
        bundle['run']['id'],
        1,
        'receipt-integrity-id',
        'test_action',
        payload,
        receipt,
        next_state,
    )
    assert outcome == 'committed'
    with db.get_db_connection() as conn:
        conn.execute(
            "UPDATE story_coop_run_actions SET receipt_json = '{\"result\":\"tampered\"}'"
        )
        conn.commit()

    with pytest.raises(db.StoryCoopDataError) as exc_info:
        db.get_story_coop_action_receipt(
            leader_id,
            bundle['party']['id'],
            'receipt-integrity-id',
        )
    assert exc_info.value.code == 'CORRUPT_COOP_ACTION_RECEIPT'


def test_terminal_commit_closes_party_and_duplicate_survives_membership_release(
    isolated_story_db,
):
    terminal_phase = 'game_over'
    leader_id, _, bundle, _ = _started_party()
    party_id = bundle['party']['id']
    run_id = bundle['run']['id']
    terminal_state = copy.deepcopy(bundle['run']['state'])
    terminal_state['phase'] = terminal_phase
    terminal_state['coordination']['action_sequence'] = 1
    terminal_payload = {'reason': 'test'}
    receipt_input = _generic_receipt(
        action_id=f'terminal-{terminal_phase}-id',
        action_type='test_terminal',
        actor_user_id=leader_id,
        actor_seat=0,
        sequence=1,
        payload=terminal_payload,
        result='party-defeated',
    )

    completed, receipt, outcome = db.commit_story_coop_run_action(
        leader_id,
        party_id,
        run_id,
        1,
        f'terminal-{terminal_phase}-id',
        'test_terminal',
        terminal_payload,
        receipt_input,
        terminal_state,
    )

    assert outcome == 'committed'
    assert receipt == receipt_input
    assert completed['status'] == 'completed'
    assert completed['completed_at']
    assert db.get_active_story_coop_party(leader_id) is None

    duplicate, duplicate_receipt, duplicate_outcome = db.commit_story_coop_run_action(
        leader_id,
        party_id,
        run_id,
        1,
        f'terminal-{terminal_phase}-id',
        'test_terminal',
        terminal_payload,
        {'ignored': True},
        terminal_state,
    )
    assert duplicate_outcome == 'duplicate'
    assert duplicate['status'] == 'completed'
    assert duplicate_receipt == receipt_input


def test_stage_complete_commit_keeps_run_and_party_active(isolated_story_db):
    leader_id, _, bundle, _ = _started_party()
    party_id = bundle['party']['id']
    run_id = bundle['run']['id']
    stage_state = copy.deepcopy(bundle['run']['state'])
    stage_state['phase'] = 'stage_complete'
    stage_state['coordination']['action_sequence'] = 1
    payload = {'room_id': 'stage-complete:1'}
    receipt_input = _generic_receipt(
        action_id='stage-complete-active-id',
        action_type='stage_ready',
        actor_user_id=leader_id,
        actor_seat=0,
        sequence=1,
        payload=payload,
    )

    updated, _, outcome = db.commit_story_coop_run_action(
        leader_id,
        party_id,
        run_id,
        1,
        'stage-complete-active-id',
        'stage_ready',
        payload,
        receipt_input,
        stage_state,
    )

    assert outcome == 'committed'
    assert updated['status'] == 'active'
    assert updated['completed_at'] is None
    assert db.get_active_story_coop_party(leader_id)['run']['status'] == 'active'


def test_full_coop_clear_records_each_member_once_in_terminal_transaction(
    isolated_story_db,
):
    leader_id, member_id, _, member_bundle, _ = _forming_party()
    party = member_bundle['party']
    party_id = party['id']
    seed = 'coop-full-persistence-seed'
    initial_state = prepare_coop_stage1_setup(
        build_initial_coop_story_state(seed, party['members']),
    )
    bundle, create_outcome = db.create_story_coop_run(
        leader_id,
        party_id,
        party['revision'],
        seed,
        COOP_STORY_CONTENT_VERSION,
        initial_state,
    )
    assert create_outcome == 'created'
    run_id = bundle['run']['id']
    completed_state = _completed_current_journey_state(
        seed,
        party['members'],
        leader_id,
        member_id,
    )
    completed_state['coordination']['action_sequence'] = 1
    payload = {'room_id': 'stage-complete:3'}
    receipt_input = _generic_receipt(
        action_id='full-coop-clear-id',
        action_type='stage_ready',
        actor_user_id=leader_id,
        actor_seat=0,
        sequence=1,
        payload=payload,
    )

    completed, receipt, outcome = db.commit_story_coop_run_action(
        leader_id,
        party_id,
        run_id,
        1,
        'full-coop-clear-id',
        'stage_ready',
        payload,
        receipt_input,
        completed_state,
    )

    assert outcome == 'committed'
    assert completed['status'] == 'completed'
    assert receipt == receipt_input
    with db.get_db_connection() as conn:
        completions = conn.execute(
            '''SELECT source_kind, source_id, user_id
               FROM story_progress_completions
               WHERE source_kind = 'coop' AND source_id = ?
               ORDER BY user_id''',
            (run_id,),
        ).fetchall()
        progress = conn.execute(
            '''SELECT user_id, standard_clears
               FROM story_progress
               WHERE character_id = 'common_flower' AND difficulty = 'normal'
               ORDER BY user_id'''
        ).fetchall()
    assert [int(row['user_id']) for row in completions] == sorted([leader_id, member_id])
    assert all(str(row['source_id']) == run_id for row in completions)
    assert [
        (int(row['user_id']), int(row['standard_clears']))
        for row in progress
    ] == [(user_id, 1) for user_id in sorted([leader_id, member_id])]

    duplicate, duplicate_receipt, duplicate_outcome = db.commit_story_coop_run_action(
        leader_id,
        party_id,
        run_id,
        1,
        'full-coop-clear-id',
        'stage_ready',
        payload,
        {'ignored': True},
        completed_state,
    )
    assert duplicate_outcome == 'duplicate'
    assert duplicate['status'] == 'completed'
    assert duplicate_receipt == receipt_input
    with db.get_db_connection() as conn:
        assert conn.execute(
            '''SELECT COUNT(*) AS total FROM story_progress_completions
               WHERE source_kind = 'coop' AND source_id = ?''',
            (run_id,),
        ).fetchone()['total'] == 2


def test_story_coop_action_fingerprint_distinguishes_json_boolean_and_number():
    numeric = db.story_coop_action_fingerprint(0, 'room_submit', {'value': 1})
    boolean = db.story_coop_action_fingerprint(0, 'room_submit', {'value': True})

    assert numeric != boolean
