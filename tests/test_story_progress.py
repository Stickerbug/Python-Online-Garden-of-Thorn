import copy
from unittest import mock

import app as gtn
import db
from story_coop import build_initial_coop_story_state
from story_coop_live import prepare_coop_stage1_setup, validate_coop_live_state
from story_mode import STORY_CONTENT_VERSION, build_initial_story_state
from story_progress import (
    build_story_progress_payload,
    story_character_is_unlocked,
    story_coop_unlock_intersection,
    story_journey_is_unlocked,
)


def test_unlock_chain_and_per_character_difficulty_rules():
    empty = build_story_progress_payload()
    assert story_character_is_unlocked(empty, 'common_flower') is True
    assert story_character_is_unlocked(empty, 'mage') is False
    assert story_journey_is_unlocked(empty, 'common_flower', 'easy', 'standard')
    assert story_journey_is_unlocked(empty, 'common_flower', 'normal', 'standard')
    assert not story_journey_is_unlocked(empty, 'common_flower', 'hard', 'standard')
    assert not story_journey_is_unlocked(empty, 'common_flower', 'normal', 'boss_rush')

    normal_clear = build_story_progress_payload([{
        'character_id': 'common_flower',
        'difficulty': 'normal',
        'standard_clears': 1,
    }])
    assert story_character_is_unlocked(normal_clear, 'mage') is True
    assert story_journey_is_unlocked(
        normal_clear, 'common_flower', 'hard', 'standard'
    )
    assert not story_journey_is_unlocked(
        normal_clear, 'common_flower', 'lunatic', 'standard'
    )

    hard_clear = build_story_progress_payload([{
        'character_id': 'common_flower',
        'difficulty': 'hard',
        'standard_clears': 1,
    }])
    assert story_journey_is_unlocked(
        hard_clear, 'common_flower', 'lunatic', 'standard'
    )
    assert story_journey_is_unlocked(
        hard_clear, 'common_flower', 'normal', 'boss_rush'
    )


def test_coop_unlocks_are_the_intersection_of_every_member():
    leader = build_story_progress_payload([
        {
            'character_id': 'common_flower',
            'difficulty': 'normal',
            'standard_clears': 1,
        },
        {
            'character_id': 'common_flower',
            'difficulty': 'hard',
            'standard_clears': 1,
        },
    ])
    member = build_story_progress_payload([{
        'character_id': 'common_flower',
        'difficulty': 'normal',
        'standard_clears': 1,
    }])
    intersection = story_coop_unlock_intersection(
        {11: leader, 12: member}, 'common_flower'
    )
    assert intersection['difficulties'] == ['easy', 'normal', 'hard']
    assert intersection['modes'] == ['standard']

    source = build_initial_coop_story_state('progress-intersection', [
        {'user_id': 11, 'username': 'Leader'},
        {'user_id': 12, 'username': 'Member'},
    ])
    setup = prepare_coop_stage1_setup(
        source,
        available_difficulties=intersection['difficulties'],
    )
    assert setup['room']['difficulties'] == ['normal', 'hard']
    assert validate_coop_live_state(setup) is True


def test_story_completion_is_idempotent_and_solo_commit_records_it(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'story-progress.sqlite3'))
    db.init_db()
    user, error = db.create_user('StoryProgressT', 'Aa1!aaaa')
    assert error is None

    state = build_initial_story_state('story-progress')
    run, created = db.create_story_run(
        user['id'], 'story-progress', STORY_CONTENT_VERSION, state,
    )
    assert created is True
    complete = copy.deepcopy(state)
    complete['phase'] = 'complete'
    complete['completed'] = True
    complete['difficulty'] = 'normal'
    complete['journey_mode'] = 'standard'
    updated, outcome = db.commit_story_run_action(
        user['id'], run['id'], 1, 'finish-story-progress', 'resolve_room', {}, complete,
    )
    assert outcome == 'committed'
    assert updated['state']['phase'] == 'complete'

    progress = db.get_story_progress(user['id'])
    common = progress['characters']['common_flower']
    assert common['clears']['normal']['standard'] == 1
    assert common['difficulties']['hard'] is True
    assert progress['characters']['mage']['unlocked'] is True

    assert db.record_story_completion(
        'solo', run['id'], user['id'], 'common_flower', 'normal', 'standard'
    ) is False
    assert (
        db.get_story_progress(user['id'])['characters']['common_flower']
        ['clears']['normal']['standard']
        == 1
    )


def test_start_journey_rejects_locked_difficulty_before_reducer():
    client = gtn.app.test_client()
    state = build_initial_story_state('locked-story-difficulty')
    run = {
        'id': 'locked-story-run',
        'state_version': 1,
        'content_version': STORY_CONTENT_VERSION,
        'compatible': True,
        'seed': 'locked-story-difficulty',
        'state': state,
    }
    progress = build_story_progress_payload()
    with (
        mock.patch.object(gtn, '_require_account_json', return_value=(41, 'Tester', None)),
        mock.patch.object(gtn, 'get_story_run_action', return_value=None),
        mock.patch.object(gtn, '_current_story_run', return_value=run),
        mock.patch.object(gtn, '_story_progress_without_blocking', return_value=progress),
        mock.patch.object(gtn, 'apply_story_action') as apply_action,
    ):
        response = client.post('/api/story/run/action', json={
            'run_id': run['id'],
            'state_version': 1,
            'action_id': 'locked-hard-start',
            'action_type': 'start_journey',
            'payload': {'biome': 'garden', 'difficulty': 'hard', 'mode': 'standard'},
        })

    assert response.status_code == 409
    assert response.get_json()['code'] == 'STORY_DIFFICULTY_LOCKED'
    apply_action.assert_not_called()


def test_story_ui_consumes_progress_for_character_and_journey_locks():
    script = open('static/js/story.js', encoding='utf-8').read()
    stylesheet = open('static/css/story.css', encoding='utf-8').read()
    assert 'let storyProgress = null;' in script
    assert 'payload.progress' in script
    assert 'storyJourneyDifficultyUnlocked' in script
    assert 'storyJourneyModeUnlocked' in script
    assert "button.classList.toggle('is-locked', playable && !unlocked)" in script
    assert '.story-character-option.is-locked' in stylesheet
