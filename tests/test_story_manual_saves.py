import copy

import db
from story_engine import apply_story_action
from story_mode import STORY_CONTENT_VERSION, build_initial_story_state


def _map_state(seed):
    state = build_initial_story_state(seed)
    state, _ = apply_story_action(
        state,
        'start_journey',
        {'biome': 'garden', 'difficulty': 'normal'},
        seed,
    )
    state['blessing_options'] = ['max_health']
    state, _ = apply_story_action(
        state,
        'choose_blessing',
        {'blessing_id': 'max_health'},
        seed,
    )
    assert state['phase'] == 'map'
    return state


def test_manual_story_saves_roll_three_slots_and_restore_rng(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'story-saves.sqlite3'))
    db.init_db()
    user, error = db.create_user('StorySaveTester', 'Aa1!aaaa')
    assert error is None

    seed = 'manual-save-seed'
    original = _map_state(seed)
    original['player']['health'] = 91
    original['rng_counter'] = 7
    original['last_events'] = [{'type': 'transient'}]
    original['recovery_checkpoint'] = {'kind': 'transient'}
    run, created = db.create_story_run(
        user['id'], seed, STORY_CONTENT_VERSION, original,
    )
    assert created is True

    saves, outcome = db.create_story_manual_save(user['id'], run['id'], 1)
    assert outcome == 'saved'
    assert [item['slot_index'] for item in saves] == [0]

    second = copy.deepcopy(original)
    second['player']['health'] = 72
    second['rng_counter'] = 21
    run, outcome = db.commit_story_run_action(
        user['id'], run['id'], 1, 'save-test-2', 'test', {}, second,
    )
    assert outcome == 'committed'
    saves, outcome = db.create_story_manual_save(
        user['id'], run['id'], run['state_version'],
    )
    assert outcome == 'saved'
    assert [item['slot_index'] for item in saves] == [0, 1]

    third = copy.deepcopy(second)
    third['player']['health'] = 44
    third['rng_counter'] = 34
    run, outcome = db.commit_story_run_action(
        user['id'], run['id'], run['state_version'],
        'save-test-3', 'test', {}, third,
    )
    assert outcome == 'committed'
    saves, outcome = db.create_story_manual_save(
        user['id'], run['id'], run['state_version'],
    )
    assert outcome == 'saved'
    assert [item['slot_index'] for item in saves] == [0, 1, 2]

    oldest = next(item for item in saves if item['slot_index'] == 2)
    restored, outcome = db.load_story_manual_save(
        user['id'], run['id'], oldest['id'], run['state_version'],
    )
    assert outcome == 'loaded'
    assert restored['state_version'] == run['state_version'] + 1
    assert restored['state']['phase'] == 'map'
    assert restored['state']['player']['health'] == 91
    assert restored['state']['rng_counter'] == 7
    assert restored['state']['last_events'] == []
    assert 'recovery_checkpoint' not in restored['state']


def test_manual_story_save_delete_compacts_remaining_slots(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'story-save-delete.sqlite3'))
    db.init_db()
    user, error = db.create_user('SaveDeleteT', 'Aa1!aaaa')
    assert error is None

    seed = 'manual-save-delete'
    state = _map_state(seed)
    run, _ = db.create_story_run(user['id'], seed, STORY_CONTENT_VERSION, state)
    for health in (91, 72, 44):
        state = copy.deepcopy(state)
        state['player']['health'] = health
        run, outcome = db.commit_story_run_action(
            user['id'], run['id'], run['state_version'],
            f'save-delete-health-{health}', 'test', {}, state,
        )
        assert outcome == 'committed'
        saves, outcome = db.create_story_manual_save(
            user['id'], run['id'], run['state_version'],
        )
        assert outcome == 'saved'
    assert [item['slot_index'] for item in saves] == [0, 1, 2]

    middle = next(item for item in saves if item['slot_index'] == 1)
    saves, outcome = db.delete_story_manual_save(user['id'], run['id'], middle['id'])

    assert outcome == 'deleted'
    assert [item['slot_index'] for item in saves] == [0, 1]
    assert all(item['id'] != middle['id'] for item in saves)

    saves, outcome = db.delete_story_manual_save(user['id'], run['id'], middle['id'])
    assert outcome == 'save_not_found'
    assert [item['slot_index'] for item in saves] == [0, 1]


def test_manual_story_save_and_load_are_rejected_outside_map(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'story-save-phase.sqlite3'))
    db.init_db()
    user, error = db.create_user('StoryPhaseTester', 'Aa1!aaaa')
    assert error is None
    seed = 'manual-save-phase'
    state = _map_state(seed)
    run, _ = db.create_story_run(user['id'], seed, STORY_CONTENT_VERSION, state)
    saves, outcome = db.create_story_manual_save(user['id'], run['id'], 1)
    assert outcome == 'saved'

    combat_state = copy.deepcopy(state)
    combat_state['phase'] = 'combat'
    run, outcome = db.commit_story_run_action(
        user['id'], run['id'], 1, 'phase-test', 'test', {}, combat_state,
    )
    assert outcome == 'committed'

    current, outcome = db.create_story_manual_save(
        user['id'], run['id'], run['state_version'],
    )
    assert outcome == 'phase'
    assert current['state']['phase'] == 'combat'

    current, outcome = db.load_story_manual_save(
        user['id'], run['id'], saves[0]['id'], run['state_version'],
    )
    assert outcome == 'phase'
    assert current['state']['phase'] == 'combat'
