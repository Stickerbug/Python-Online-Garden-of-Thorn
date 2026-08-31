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
    original['rng_streams'] = {
        'card_reward:combat': 2,
        'relic_reward': 1,
    }
    original['last_events'] = [{'type': 'transient'}]
    original['recovery_checkpoint'] = {'kind': 'transient'}
    run, created = db.create_story_run(
        user['id'], seed, STORY_CONTENT_VERSION, original,
    )
    assert created is True

    saves, outcome = db.create_story_manual_save(user['id'], run['id'], 1)
    assert outcome == 'saved'
    assert [item['slot_index'] for item in saves] == [0]
    assert saves[0]['phase'] == 'map'

    second = copy.deepcopy(original)
    second['player']['health'] = 72
    second['rng_counter'] = 21
    second['rng_streams']['card_reward:combat'] = 5
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
    assert restored['state']['rng_streams'] == {
        'card_reward:combat': 2,
        'relic_reward': 1,
    }
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


def test_manual_story_save_and_load_work_across_committed_ui_phases(tmp_path, monkeypatch):
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
    combat_state.update({
        'phase': 'combat',
        'combat': {'id': 'manual-combat', 'turn': 'player'},
        'last_events': [{'type': 'enemy_damage', 'amount': 3}],
    })
    run, outcome = db.commit_story_run_action(
        user['id'], run['id'], 1, 'phase-test', 'test', {}, combat_state,
    )
    assert outcome == 'committed'

    combat_saves, outcome = db.create_story_manual_save(
        user['id'], run['id'], run['state_version'],
    )
    assert outcome == 'saved'
    assert combat_saves[0]['phase'] == 'combat'

    room_state = copy.deepcopy(combat_state)
    room_state.update({
        'phase': 'room',
        'combat': None,
        'room': {'type': 'rest', 'options': ['leave']},
    })
    run, outcome = db.commit_story_run_action(
        user['id'], run['id'], run['state_version'],
        'phase-test-room', 'test', {}, room_state,
    )
    assert outcome == 'committed'

    stale, outcome = db.load_story_manual_save(
        user['id'], run['id'], combat_saves[0]['id'], run['state_version'] - 1,
    )
    assert outcome == 'version'
    assert stale['state']['phase'] == 'room'

    current, outcome = db.load_story_manual_save(
        user['id'], run['id'], combat_saves[0]['id'], run['state_version'],
    )
    assert outcome == 'loaded'
    assert current['state']['phase'] == 'combat'
    assert current['state']['last_events'] == []
    checkpoint = current['state']['recovery_checkpoint']
    assert checkpoint['kind'] == 'manual_combat'
    assert checkpoint['state']['phase'] == 'combat'
    assert 'recovery_checkpoint' not in checkpoint['state']


def test_manual_story_save_rejects_unknown_transient_phase(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'story-save-unstable.sqlite3'))
    db.init_db()
    user, error = db.create_user('StoryUnstable', 'Aa1!aaaa')
    assert error is None
    state = _map_state('manual-save-unstable')
    state['phase'] = 'enemy_resolving'
    run, _ = db.create_story_run(
        user['id'], 'manual-save-unstable', STORY_CONTENT_VERSION, state,
    )

    current, outcome = db.create_story_manual_save(
        user['id'], run['id'], run['state_version'],
    )

    assert outcome == 'phase'
    assert current['state']['phase'] == 'enemy_resolving'


def test_every_committed_story_ui_phase_is_a_manual_save_checkpoint():
    state = _map_state('manual-save-stable-phases')
    for phase in (
        'journey_setup', 'easy_relic', 'blessing', 'map', 'combat',
        'room', 'reward', 'stage_choice', 'complete', 'game_over',
    ):
        candidate = copy.deepcopy(state)
        candidate['phase'] = phase
        assert db._story_manual_save_state_is_stable(candidate) is True
    state['phase'] = 'enemy_resolving'
    assert db._story_manual_save_state_is_stable(state) is False
