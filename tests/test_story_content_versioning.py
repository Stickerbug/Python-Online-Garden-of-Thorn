import copy
import json
from unittest import mock

import app as gtn
import db
from story_mode import STORY_CONTENT_VERSION, build_initial_story_state
from story_content_model import STORY_CONTENT_FINGERPRINT


def _legacy_run():
    state = build_initial_story_state('legacy-story-version')
    state['content_version'] = 'story-redesign-8'
    return {
        'id': 'legacy-story-run',
        'user_id': 41,
        'status': 'active',
        'seed': 'legacy-story-version',
        'content_version': 'story-redesign-8',
        'state_version': 7,
        'state': state,
    }


def test_current_solo_content_version_is_bound_to_the_normalized_catalog():
    assert STORY_CONTENT_VERSION == (
        f'story-redesign-10-{STORY_CONTENT_FINGERPRINT[:12]}'
    )
    state = build_initial_story_state('content-fingerprint')
    assert state['content_version'] == STORY_CONTENT_VERSION


def test_story_contract_migration_clears_progress_but_preserves_discoveries(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'story-contract-reset.sqlite3'))
    db.init_db('solo-v1', 'coop-v1')
    user, error = db.create_user('ContractReset', 'Aa1!aaaa')
    assert error is None
    user_id = int(user['id'])
    now = db.utc_now()
    party_id = 'a' * 32
    run_id = 'solo-old-run'
    coop_run_id = 'b' * 32
    with db.get_db_connection() as conn:
        conn.execute(
            '''INSERT INTO story_runs
               (id, user_id, status, seed, content_version, state_version,
                state_json, created_at, updated_at)
               VALUES (?, ?, 'active', 'seed', 'solo-v1', 1, ?, ?, ?)''',
            (run_id, user_id, json.dumps({'content_version': 'solo-v1'}), now, now),
        )
        conn.execute(
            '''INSERT INTO story_run_actions
               (run_id, sequence, action_id, action_type, payload_json, created_at)
               VALUES (?, 1, 'action-1', 'test', '{}', ?)''',
            (run_id, now),
        )
        conn.execute(
            '''INSERT INTO story_manual_saves
               (run_id, user_id, slot_index, source_state_version, state_json,
                stage, floor, created_at)
               VALUES (?, ?, 0, 1, ?, 1, 1, ?)''',
            (run_id, user_id, json.dumps({'content_version': 'solo-v1'}), now),
        )
        conn.execute(
            '''INSERT INTO story_progress
               (user_id, character_id, difficulty, standard_clears,
                boss_rush_clears, first_cleared_at, last_cleared_at)
               VALUES (?, 'common_flower', 'normal', 1, 0, ?, ?)''',
            (user_id, now, now),
        )
        conn.execute(
            '''INSERT INTO story_progress_completions
               (source_kind, source_id, user_id, character_id, difficulty,
                journey_mode, completed_at)
               VALUES ('solo', ?, ?, 'common_flower', 'normal', 'standard', ?)''',
            (run_id, user_id, now),
        )
        conn.execute(
            '''INSERT INTO story_discoveries
               (user_id, content_type, content_id, variant, first_run_id,
                first_seen_at, last_seen_at, seen_count)
               VALUES (?, 'card', 'Basic', 'base', ?, ?, ?, 1)''',
            (user_id, run_id, now, now),
        )
        conn.execute(
            '''INSERT INTO story_coop_parties
               (id, status, max_players, invite_code_hash, revision,
                created_at, updated_at)
               VALUES (?, 'forming', 2, ?, 1, ?, ?)''',
            (party_id, 'c' * 64, now, now),
        )
        conn.execute(
            '''INSERT INTO story_coop_party_members
               (party_id, user_id, seat, party_role, membership_status, joined_at)
               VALUES (?, ?, 0, 'leader', 'active', ?)''',
            (party_id, user_id, now),
        )
        conn.execute(
            '''INSERT INTO story_coop_runs
               (id, party_id, status, schema_version, seed, content_version,
                revision, state_json, created_at, updated_at)
               VALUES (?, ?, 'active', 10, 'coop-seed', 'coop-v1', 1, '{}', ?, ?)''',
            (coop_run_id, party_id, now, now),
        )
        conn.execute(
            '''INSERT INTO story_coop_run_actions
               (party_id, run_id, sequence, action_id, actor_user_id, actor_seat,
                action_type, request_fingerprint, payload_json, receipt_json,
                resulting_revision, created_at)
               VALUES (?, ?, 1, 'coop-action-1', ?, 0, 'test', ?, '{}', '{}', 2, ?)''',
            (party_id, coop_run_id, user_id, 'd' * 64, now),
        )
        conn.commit()

    db.init_db('solo-v1', 'coop-v1')
    with db.get_db_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM story_runs').fetchone()[0] == 1
        assert conn.execute('SELECT COUNT(*) FROM story_coop_runs').fetchone()[0] == 1

    db.init_db('solo-v2', 'coop-v1')
    with db.get_db_connection() as conn:
        for table in (
            'story_run_actions',
            'story_manual_saves',
            'story_runs',
            'story_coop_run_actions',
            'story_coop_runs',
            'story_coop_party_members',
            'story_coop_parties',
            'story_progress_completions',
            'story_progress',
        ):
            assert conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM story_discoveries').fetchone()[0] == 1
        contract = conn.execute(
            '''SELECT story_content_version, coop_story_content_version
               FROM story_data_contract_state WHERE id = 1'''
        ).fetchone()
        assert tuple(contract) == ('solo-v2', 'coop-v1')


def test_first_contract_marker_clears_preexisting_story_data_but_keeps_compendium(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'story-first-contract.sqlite3'))
    db.init_db()
    user, error = db.create_user('FirstReset', 'Aa1!aaaa')
    assert error is None
    user_id = int(user['id'])
    now = db.utc_now()
    with db.get_db_connection() as conn:
        conn.execute(
            '''INSERT INTO story_runs
               (id, user_id, status, seed, content_version, state_version,
                state_json, created_at, updated_at)
               VALUES ('pre-marker-run', ?, 'active', 'seed', 'legacy', 1,
                       '{"content_version":"legacy"}', ?, ?)''',
            (user_id, now, now),
        )
        conn.execute(
            '''INSERT INTO story_discoveries
               (user_id, content_type, content_id, variant, first_run_id,
                first_seen_at, last_seen_at, seen_count)
               VALUES (?, 'enemy', 'Yoba', 'base', 'pre-marker-run', ?, ?, 1)''',
            (user_id, now, now),
        )
        conn.commit()

    db.init_db('solo-current', 'coop-current')
    with db.get_db_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM story_runs').fetchone()[0] == 0
        discovery = conn.execute(
            '''SELECT content_type, content_id, first_run_id
               FROM story_discoveries'''
        ).fetchone()
        assert tuple(discovery) == ('enemy', 'Yoba', 'pre-marker-run')


def test_unexpected_old_solo_run_is_still_annotated_fail_closed():
    legacy = _legacy_run()
    with (
        mock.patch.object(gtn, 'get_active_story_run', return_value=legacy),
        mock.patch.object(gtn, 'reset_story_run_map') as reset,
    ):
        result = gtn._current_story_run(41)

    reset.assert_not_called()
    assert result['id'] == legacy['id']
    assert result['content_version'] == 'story-redesign-8'
    assert result['state_version'] == 7
    assert result['compatible'] is False
    assert result['expected_content_version'] == STORY_CONTENT_VERSION
    assert 'compatible' not in legacy


def test_solo_run_requires_row_and_state_content_versions_to_match():
    mismatched = _legacy_run()
    mismatched['content_version'] = STORY_CONTENT_VERSION

    result = gtn._story_run_with_compatibility(mismatched)

    assert result['compatible'] is False
    with mock.patch.object(gtn, 'record_story_discoveries') as record:
        assert gtn._sync_story_discoveries(41, result) == []
    record.assert_not_called()


def test_old_solo_run_rejects_new_actions_but_preserves_state():
    client = gtn.app.test_client()
    run = gtn._story_run_with_compatibility(_legacy_run())
    with (
        mock.patch.object(gtn, '_require_account_json', return_value=(41, 'StoryTester', None)),
        mock.patch.object(gtn, 'get_story_run_action', return_value=None),
        mock.patch.object(gtn, '_current_story_run', return_value=run),
        mock.patch.object(gtn, 'apply_story_action') as apply_action,
    ):
        response = client.post('/api/story/run/action', json={
            'run_id': run['id'],
            'state_version': run['state_version'],
            'action_id': 'legacy-new-action',
            'action_type': 'start_journey',
            'payload': {},
        })

    assert response.status_code == 409
    payload = response.get_json()
    assert payload['code'] == 'STORY_CONTENT_VERSION_OLD'
    assert payload['run']['id'] == run['id']
    assert payload['run']['compatible'] is False
    assert payload['run']['state_version'] == 7
    apply_action.assert_not_called()


def test_duplicate_old_solo_action_remains_idempotently_readable():
    client = gtn.app.test_client()
    run = gtn._story_run_with_compatibility(_legacy_run())
    with (
        mock.patch.object(gtn, '_require_account_json', return_value=(41, 'StoryTester', None)),
        mock.patch.object(gtn, 'get_story_run_action', return_value={'action_id': 'legacy-retry'}),
        mock.patch.object(gtn, '_current_story_run', return_value=run),
        mock.patch.object(gtn, '_list_story_discoveries_without_blocking', return_value=[]),
    ):
        response = client.post('/api/story/run/action', json={
            'run_id': run['id'],
            'state_version': run['state_version'],
            'action_id': 'legacy-retry',
            'action_type': 'choose_blessing',
            'payload': {'blessing_id': 'max_health'},
        })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['duplicate'] is True
    assert payload['run']['compatible'] is False


def test_old_solo_run_rejects_manual_save_and_load_before_db_mutation():
    client = gtn.app.test_client()
    run = gtn._story_run_with_compatibility(_legacy_run())
    requests = (
        ('/api/story/run/save', {
            'run_id': run['id'],
            'state_version': run['state_version'],
        }),
        ('/api/story/run/load', {
            'run_id': run['id'],
            'state_version': run['state_version'],
            'save_id': 1,
        }),
    )
    with (
        mock.patch.object(gtn, '_require_account_json', return_value=(41, 'StoryTester', None)),
        mock.patch.object(gtn, '_current_story_run', return_value=run),
        mock.patch.object(gtn, 'create_story_manual_save') as create_save,
        mock.patch.object(gtn, 'load_story_manual_save') as load_save,
    ):
        responses = [client.post(path, json=body) for path, body in requests]

    assert [response.status_code for response in responses] == [409, 409]
    assert all(
        response.get_json()['code'] == 'STORY_CONTENT_VERSION_OLD'
        for response in responses
    )
    create_save.assert_not_called()
    load_save.assert_not_called()


def test_story_commit_rejects_cross_content_state(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'story-content-version.sqlite3'))
    db.init_db()
    user, error = db.create_user('VersionCommit', 'Aa1!aaaa')
    assert error is None
    state = build_initial_story_state('story-content-version')
    run, created = db.create_story_run(
        user['id'], 'story-content-version', STORY_CONTENT_VERSION, state,
    )
    assert created is True

    next_state = copy.deepcopy(state)
    next_state['content_version'] = 'future-story-content'
    current, outcome = db.commit_story_run_action(
        user['id'], run['id'], run['state_version'],
        'cross-content-action', 'test', {}, next_state,
    )

    assert outcome == 'content_version'
    assert current['state_version'] == 1
    assert current['state']['content_version'] == STORY_CONTENT_VERSION
    assert db.get_story_run_action(user['id'], run['id'], 'cross-content-action') is None


def test_manual_save_cannot_cross_content_versions(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'story-save-content-version.sqlite3'))
    db.init_db()
    user, error = db.create_user('VersionSave', 'Aa1!aaaa')
    assert error is None
    state = build_initial_story_state('story-save-content-version')
    state['phase'] = 'map'
    state['room'] = None
    run, _ = db.create_story_run(
        user['id'], 'story-save-content-version', STORY_CONTENT_VERSION, state,
    )
    saves, outcome = db.create_story_manual_save(user['id'], run['id'], 1)
    assert outcome == 'saved'

    with db.get_db_connection() as conn:
        row = conn.execute(
            'SELECT state_json FROM story_manual_saves WHERE id = ?',
            (saves[0]['id'],),
        ).fetchone()
        old_state = json.loads(row['state_json'])
        old_state['content_version'] = 'story-redesign-8'
        conn.execute(
            'UPDATE story_manual_saves SET state_json = ? WHERE id = ?',
            (json.dumps(old_state, ensure_ascii=False), saves[0]['id']),
        )
        conn.commit()

    current, outcome = db.load_story_manual_save(
        user['id'], run['id'], saves[0]['id'], run['state_version'],
    )
    assert outcome == 'content_version'
    assert current['state_version'] == run['state_version']
    assert current['state']['content_version'] == STORY_CONTENT_VERSION


def test_story_ui_uses_explicit_old_version_replacement():
    template = open('templates/story.html', encoding='utf-8').read()
    script = open('static/js/story.js', encoding='utf-8').read()

    assert 'id="story-version-old"' in template
    assert 'id="story-version-old-restart"' in template
    assert "'story-version-old'" in script
    assert 'run.compatible === false' in script
    assert 'resetMap(true)' not in script
    assert "addEventListener('click', replaceLegacyRun)" in script
