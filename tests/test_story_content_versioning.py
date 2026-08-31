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


def test_old_solo_run_is_annotated_without_automatic_reset():
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
