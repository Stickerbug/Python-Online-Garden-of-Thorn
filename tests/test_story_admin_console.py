import re

import db
from story_admin import execute_story_admin_command, validate_story_run_state
from story_engine import apply_story_action
from story_mode import STORY_CONTENT_VERSION, build_initial_story_state


def _token(result):
    assert result['success'], result['output']
    match = re.search(r'确认令牌：([0-9a-f]{16})', result['output'])
    assert match, result['output']
    return match.group(1)


def _story_account(tmp_path, monkeypatch, username='StoryAdminTester'):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / f'{username}.sqlite3'))
    db.init_db()
    user, error = db.create_user(username, 'Aa1!aaaa')
    assert error is None
    seed = f'admin-console-{username}'
    state = build_initial_story_state(seed)
    state, _ = apply_story_action(
        state,
        'start_journey',
        {'biome': 'garden', 'difficulty': 'normal', 'mode': 'standard'},
        seed,
    )
    state['blessing_options'] = ['max_health']
    state, _ = apply_story_action(
        state,
        'choose_blessing',
        {'blessing_id': 'max_health'},
        seed,
    )
    run, created = db.create_story_run(user['id'], seed, STORY_CONTENT_VERSION, state)
    assert created is True
    return user, run


def _preview_confirm(parts):
    preview = execute_story_admin_command([*parts, 'preview'], actor='test-admin')
    token = _token(preview)
    confirmed = execute_story_admin_command(
        [*parts, f'confirm={token}'],
        actor='test-admin',
    )
    assert confirmed['success'], confirmed['output']
    return confirmed


def test_resource_mutation_requires_preview_and_is_audited(tmp_path, monkeypatch):
    user, run = _story_account(tmp_path, monkeypatch)

    missing_gate = execute_story_admin_command(
        ['resource', 'set', user['username'], 'gold', '321'],
        actor='test-admin',
    )
    assert missing_gate['success'] is False
    assert 'preview' in missing_gate['output']

    confirmed = _preview_confirm(
        ['resource', 'set', user['username'], 'gold', '321'],
    )
    assert '操作号：SAM-' in confirmed['output']
    updated = db.get_active_story_run(user['id'])
    assert updated['state']['player']['gold'] == 321
    assert updated['state_version'] == run['state_version'] + 1
    with db.get_db_connection() as connection:
        audit = connection.execute(
            'SELECT * FROM story_admin_mutations WHERE user_id = ?',
            (user['id'],),
        ).fetchone()
    assert audit is not None
    assert audit['target_kind'] == 'run'
    assert audit['before_revision'] == run['state_version']
    assert audit['after_revision'] == run['state_version'] + 1


def test_stale_confirmation_token_cannot_overwrite_newer_story_state(tmp_path, monkeypatch):
    user, _run = _story_account(tmp_path, monkeypatch, 'StoryAdminStale')
    parts = ['resource', 'set', user['username'], 'gold', '444']
    token = _token(execute_story_admin_command([*parts, 'preview']))
    _preview_confirm(['resource', 'set', user['username'], 'health', '70'])

    stale = execute_story_admin_command([*parts, f'confirm={token}'])
    assert stale['success'] is False
    assert '重新 preview' in stale['output']
    assert db.get_active_story_run(user['id'])['state']['player']['gold'] != 444


def test_cards_relics_and_books_preserve_valid_save_and_checkpoint_values(tmp_path, monkeypatch):
    user, _run = _story_account(tmp_path, monkeypatch, 'StoryInventory')
    _preview_confirm(['card', 'add', user['username'], 'basic', 'count=2'])
    _preview_confirm(['card', 'upgrade', user['username'], 'basic', 'count=1'])
    _preview_confirm(['relic', 'add', user['username'], 'energetic', 'count=2'])
    _preview_confirm(['book', 'add', user['username'], 'sharp', 'count=1'])

    run = db.get_active_story_run(user['id'])
    state = run['state']
    assert len([card for card in state['player']['deck'] if card['def_id'] == 'basic']) == 7
    assert any(card['def_id'] == 'basic' and card['upgraded'] for card in state['player']['deck'])
    assert state['player']['relics'].count('energetic') == 3
    assert state['player']['enchantment_books'][0]['book_id'] == 'sharp'
    assert validate_story_run_state(state) == []


def test_jump_can_rebuild_stage_and_enter_floor_or_stage_blessing(tmp_path, monkeypatch):
    user, _run = _story_account(tmp_path, monkeypatch, 'StoryAdminJump')
    _preview_confirm([
        'jump', 'stage', user['username'], '2', 'floor=5', 'node=1',
    ])
    jumped = db.get_active_story_run(user['id'])['state']
    assert jumped['stage'] == 2
    assert jumped['biome'] == 'jungle'
    assert jumped['current_floor'] == 5
    assert jumped['current_node_id'].startswith('s2-f05-')
    assert jumped['phase'] in {'combat', 'room', 'reward'}
    assert jumped['floor_entry_checkpoint']['node_id'] == jumped['current_node_id']
    assert validate_story_run_state(jumped) == []

    _preview_confirm(['jump', 'stage', user['username'], '3'])
    stage_three = db.get_active_story_run(user['id'])['state']
    assert stage_three['stage'] == 3
    assert stage_three['biome'] == 'factory'
    assert stage_three['current_floor'] == 1
    assert stage_three['phase'] == 'blessing'
    assert stage_three['blessing_options']

    _preview_confirm([
        'jump', 'node', user['username'], 's2-f06-n0',
    ])
    by_id = db.get_active_story_run(user['id'])['state']
    assert by_id['stage'] == 2
    assert by_id['current_floor'] == 6
    assert by_id['current_node_id'] == 's2-f06-n0'


def test_audit_undo_refuses_intervening_play_and_restores_latest_mutation(tmp_path, monkeypatch):
    user, _run = _story_account(tmp_path, monkeypatch, 'StoryAdminUndo')
    confirmed = _preview_confirm(
        ['resource', 'set', user['username'], 'gold', '500'],
    )
    operation_id = re.search(r'操作号：(SAM-[0-9a-f]+)', confirmed['output']).group(1)
    preview = execute_story_admin_command(['audit', 'undo', operation_id, 'preview'])
    token = _token(preview)
    undone = execute_story_admin_command(['audit', 'undo', operation_id, f'confirm={token}'])
    assert undone['success'], undone['output']
    assert db.get_active_story_run(user['id'])['state']['player']['gold'] == 99

    second = _preview_confirm(
        ['resource', 'set', user['username'], 'gold', '600'],
    )
    second_id = re.search(r'操作号：(SAM-[0-9a-f]+)', second['output']).group(1)
    run = db.get_active_story_run(user['id'])
    changed = run['state']
    changed['player']['health'] -= 1
    _updated, status = db.commit_story_run_action(
        user['id'], run['id'], run['state_version'],
        'intervening-play-action', 'test', {}, changed,
    )
    assert status == 'committed'
    refused = execute_story_admin_command(['audit', 'undo', second_id, 'preview'])
    assert refused['success'] is False
    assert '又发生了变化' in refused['output']


def test_progress_and_discovery_mutations_are_undoable(tmp_path, monkeypatch):
    user, _run = _story_account(tmp_path, monkeypatch, 'StoryAdminMeta')
    progress = _preview_confirm([
        'progress', 'set', user['username'], 'common_flower', 'normal',
        'standard', '1',
    ])
    progress_id = re.search(r'操作号：(SAM-[0-9a-f]+)', progress['output']).group(1)
    assert db.get_story_progress(user['id'])['characters']['common_flower']['clears']['normal']['standard'] == 1

    discovery = _preview_confirm([
        'discovery', 'add', user['username'], 'card', 'basic',
        'variant=upgraded',
    ])
    discovery_id = re.search(r'操作号：(SAM-[0-9a-f]+)', discovery['output']).group(1)
    assert any(item['content_id'] == 'basic' and item['variant'] == 'upgraded' for item in db.list_story_discoveries(user['id']))

    _preview_confirm(['audit', 'undo', discovery_id])
    assert not any(item['content_id'] == 'basic' and item['variant'] == 'upgraded' for item in db.list_story_discoveries(user['id']))
    _preview_confirm(['audit', 'undo', progress_id])
    assert db.get_story_progress(user['id'])['characters']['common_flower']['clears']['normal']['standard'] == 0


def test_manual_save_console_commands_create_and_load(tmp_path, monkeypatch):
    user, _run = _story_account(tmp_path, monkeypatch, 'StoryAdminSave')
    _preview_confirm(['save', 'create', user['username']])
    run = db.get_active_story_run(user['id'])
    saves = db.list_story_manual_saves(user['id'], run['id'])
    assert len(saves) == 1
    save_id = saves[0]['id']
    copied = _preview_confirm(['save', 'copy', user['username'], str(save_id)])
    saves = db.list_story_manual_saves(user['id'], run['id'])
    assert len(saves) == 2
    assert [item['slot_index'] for item in saves] == [0, 1]
    copy_operation_id = re.search(r'操作号 (SAM-[0-9a-f]+)', copied['output']).group(1)
    _preview_confirm(['audit', 'undo', copy_operation_id])
    saves = db.list_story_manual_saves(user['id'], run['id'])
    assert len(saves) == 1

    _preview_confirm(['resource', 'set', user['username'], 'gold', '777'])
    assert db.get_active_story_run(user['id'])['state']['player']['gold'] == 777
    _preview_confirm(['save', 'load', user['username'], str(save_id)])
    assert db.get_active_story_run(user['id'])['state']['player']['gold'] == 99


def test_abandon_is_audited_and_can_be_safely_undone(tmp_path, monkeypatch):
    user, _run = _story_account(tmp_path, monkeypatch, 'StoryAbandon')
    result = _preview_confirm(['run', 'abandon', user['username']])
    operation_id = re.search(r'操作号：(SAM-[0-9a-f]+)', result['output']).group(1)
    assert db.get_active_story_run(user['id']) is None

    _preview_confirm(['audit', 'undo', operation_id])
    restored = db.get_active_story_run(user['id'])
    assert restored is not None
    assert restored['status'] == 'active'


def test_content_lookup_and_coop_absence_fail_cleanly(tmp_path, monkeypatch):
    user, _run = _story_account(tmp_path, monkeypatch, 'StoryAdminLookup')
    content = execute_story_admin_command(['content', 'list', 'book', 'sharp'])
    assert content['success']
    assert 'sharp' in content['output']
    coop = execute_story_admin_command(['coop', 'validate', user['username']])
    assert coop['success'] is False
    assert '未找到协作故事旅程' in coop['output']
