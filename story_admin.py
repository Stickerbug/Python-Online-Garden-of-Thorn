"""Transactional command-console tooling for solo and cooperative Story saves."""

from contextlib import closing
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
import secrets

import db as db_module
from db import (
    create_story_run,
    find_user_for_admin,
    get_db_connection,
    list_story_manual_saves,
)
from story_content import (
    STORY_BIOMES,
    STORY_BLESSINGS,
    STORY_CARDS,
    STORY_CHARACTERS,
    STORY_DIFFICULTIES,
    STORY_ENEMIES,
    STORY_ENCHANTMENT_BOOKS,
    STORY_RELICS,
    STORY_RULES,
    STORY_STATUSES,
    STORY_TAGS,
    STORY_TRAITS,
)
from story_engine import (
    StoryActionError,
    apply_story_action,
    build_story_admin_jump_state,
)
from story_mode import (
    STORY_CONTENT_VERSION,
    STORY_SCHEMA_VERSION,
    build_initial_story_state,
)
from story_progress import (
    normalize_story_character_id,
    normalize_story_difficulty,
    normalize_story_journey_mode,
)


class StoryAdminError(ValueError):
    pass


_PHASES = {
    'journey_setup', 'easy_relic', 'blessing', 'map', 'combat', 'room',
    'reward', 'stage_choice', 'complete', 'game_over',
}
_RESOURCE_LIMITS = {
    'health': (0, 999999),
    'max_health': (1, 999999),
    'elixir': (0, 2147483647),
    'max_elixir': (0, 2147483647),
    'magic': (0, 2147483647),
    'max_magic': (0, 2147483647),
    'gold': (0, 999999999),
}
_DISCOVERY_CATALOGS = {
    'card': STORY_CARDS,
    'relic': STORY_RELICS,
    'blessing': STORY_BLESSINGS,
    'enemy': STORY_ENEMIES,
    'enchantment_book': STORY_ENCHANTMENT_BOOKS,
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def _hash(value):
    return hashlib.sha256(_json(value).encode('utf-8')).hexdigest()


def _parse_json(raw, label='JSON'):
    try:
        value = json.loads(raw or '{}')
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise StoryAdminError(f'{label} 无法解析：{exc}') from exc
    return value


def _resolve_user(identifier):
    user = find_user_for_admin(identifier)
    if not user:
        raise StoryAdminError(f'未找到账号：{identifier}')
    return user


def _option_parts(parts):
    positional = []
    options = {}
    for token in parts:
        key, separator, value = str(token).partition('=')
        if separator:
            options[key.strip().lower()] = value.strip()
        else:
            positional.append(str(token))
    return positional, options


def _bool_option(value, default=False):
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off'}:
        return False
    raise StoryAdminError(f'布尔参数无效：{value}')


def _int(value, label, minimum=None, maximum=None):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise StoryAdminError(f'{label} 必须是整数') from exc
    if minimum is not None and parsed < minimum:
        raise StoryAdminError(f'{label} 不能小于 {minimum}')
    if maximum is not None and parsed > maximum:
        raise StoryAdminError(f'{label} 不能大于 {maximum}')
    return parsed


def _mutation_gate(parts):
    remaining = []
    mode = None
    confirmation = ''
    for token in parts:
        lowered = str(token).lower()
        if lowered == 'preview':
            if mode:
                raise StoryAdminError('只能指定一次 preview 或 confirm=令牌')
            mode = 'preview'
            continue
        if lowered.startswith('confirm='):
            if mode:
                raise StoryAdminError('只能指定一次 preview 或 confirm=令牌')
            mode = 'confirm'
            confirmation = str(token).split('=', 1)[1].strip().lower()
            continue
        remaining.append(str(token))
    if not mode:
        raise StoryAdminError('写操作必须先使用 preview，再把返回的令牌作为 confirm=令牌提交')
    if mode == 'confirm' and not confirmation:
        raise StoryAdminError('confirm= 后缺少预览令牌')
    return remaining, mode, confirmation


def _confirmation_token(user_id, target_kind, target_id, revision, before, spec):
    payload = {
        'user_id': int(user_id),
        'target_kind': str(target_kind),
        'target_id': str(target_id),
        'revision': revision,
        'before_sha256': _hash(before),
        'spec': spec,
    }
    return hashlib.sha256(_json(payload).encode('utf-8')).hexdigest()[:16]


def _run_row_conn(conn, user_id, run_id=None, active_only=True):
    clauses = ['user_id = ?']
    params = [int(user_id)]
    if run_id:
        clauses.append('id = ?')
        params.append(str(run_id))
    if active_only:
        clauses.append("status = 'active'")
    return conn.execute(
        f"SELECT * FROM story_runs WHERE {' AND '.join(clauses)} "
        'ORDER BY updated_at DESC LIMIT 1',
        tuple(params),
    ).fetchone()


def _run_state(row):
    if row is None:
        raise StoryAdminError('该账号没有符合条件的故事旅程')
    state = _parse_json(row['state_json'], '故事存档')
    if not isinstance(state, dict):
        raise StoryAdminError('故事存档根节点不是对象')
    return state


def _run_summary(row, state=None):
    state = state if isinstance(state, dict) else _run_state(row)
    player = state.get('player') if isinstance(state.get('player'), dict) else {}
    deck = player.get('deck') if isinstance(player.get('deck'), list) else []
    return {
        'run_id': row['id'],
        'status': row['status'],
        'state_version': int(row['state_version']),
        'content_version': row['content_version'],
        'phase': state.get('phase'),
        'stage': state.get('stage'),
        'floor': state.get('current_floor'),
        'node_id': state.get('current_node_id'),
        'biome': state.get('biome'),
        'difficulty': state.get('difficulty'),
        'journey_mode': state.get('journey_mode'),
        'character_id': state.get('character_id') or player.get('character_id'),
        'health': player.get('health'),
        'max_health': player.get('max_health'),
        'gold': player.get('gold'),
        'deck_count': len(deck),
        'updated_at': row['updated_at'],
    }


def _format_mapping(title, value):
    return f'{title}\n{json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)}'


def validate_story_run_state(state, row=None):
    errors = []
    if not isinstance(state, dict):
        return ['存档根节点不是对象']
    if state.get('schema_version') != STORY_SCHEMA_VERSION:
        errors.append(f"schema_version={state.get('schema_version')}，当前应为 {STORY_SCHEMA_VERSION}")
    expected_content = str(row['content_version']) if row is not None else STORY_CONTENT_VERSION
    if str(state.get('content_version') or '') != expected_content:
        errors.append('存档内 content_version 与旅程记录不一致')
    if row is not None and str(row['content_version'] or '') != STORY_CONTENT_VERSION:
        errors.append('旅程内容版本不是当前服务器版本，不允许直接修改')
    if str(state.get('phase') or '') not in _PHASES:
        errors.append(f"未知 phase：{state.get('phase')}")
    player = state.get('player')
    if not isinstance(player, dict):
        errors.append('player 不是对象')
        return errors
    for key, (minimum, maximum) in _RESOURCE_LIMITS.items():
        value = player.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f'player.{key} 必须是整数')
        elif value < minimum or value > maximum:
            errors.append(f'player.{key} 超出 {minimum}-{maximum}')
    if isinstance(player.get('health'), int) and isinstance(player.get('max_health'), int):
        if player['health'] > player['max_health']:
            errors.append('health 大于 max_health')
    if isinstance(player.get('elixir'), int) and isinstance(player.get('max_elixir'), int):
        if player['elixir'] > player['max_elixir']:
            errors.append('elixir 大于 max_elixir')
    if isinstance(player.get('magic'), int) and isinstance(player.get('max_magic'), int):
        if player['magic'] > player['max_magic']:
            errors.append('magic 大于 max_magic')
    deck = player.get('deck')
    if not isinstance(deck, list):
        errors.append('player.deck 不是列表')
    else:
        seen = set()
        for index, card in enumerate(deck):
            if not isinstance(card, dict):
                errors.append(f'deck[{index}] 不是对象')
                continue
            instance_id = str(card.get('instance_id') or '')
            card_id = str(card.get('def_id') or '')
            if not instance_id or instance_id in seen:
                errors.append(f'deck[{index}] 的 instance_id 缺失或重复')
            seen.add(instance_id)
            if card_id not in STORY_CARDS:
                errors.append(f'deck[{index}] 使用未知卡牌 {card_id}')
    relics = player.get('relics')
    if not isinstance(relics, list):
        errors.append('player.relics 不是列表')
    else:
        errors.extend(f'未知天赋/遗物：{item}' for item in relics if item not in STORY_RELICS)
    books = player.get('enchantment_books')
    if not isinstance(books, list):
        errors.append('player.enchantment_books 不是列表')
    else:
        if len(books) > int(STORY_RULES['enchantment_book_slots']):
            errors.append('附魔书数量超过槽位上限')
        seen_books = set()
        for index, book in enumerate(books):
            if not isinstance(book, dict):
                errors.append(f'enchantment_books[{index}] 不是对象')
                continue
            instance_id = str(book.get('instance_id') or '')
            book_id = str(book.get('book_id') or '')
            if not instance_id or instance_id in seen_books:
                errors.append(f'enchantment_books[{index}] 的 instance_id 缺失或重复')
            seen_books.add(instance_id)
            if book_id not in STORY_ENCHANTMENT_BOOKS:
                errors.append(f'enchantment_books[{index}] 使用未知附魔书 {book_id}')
    story_map = state.get('map')
    if not isinstance(story_map, dict):
        errors.append('map 不是对象')
    else:
        floors = story_map.get('floors')
        if not isinstance(floors, list) or not floors:
            errors.append('map.floors 为空或不是列表')
        else:
            nodes = {
                str(node.get('id') or ''): node
                for floor in floors if isinstance(floor, dict)
                for node in (floor.get('nodes') or []) if isinstance(node, dict)
            }
            current_id = str(state.get('current_node_id') or '')
            current = nodes.get(current_id)
            if current is None:
                errors.append('current_node_id 不在地图中')
            elif int(current.get('floor') or 0) != int(state.get('current_floor') or 0):
                errors.append('current_floor 与 current_node_id 不一致')
            if int(story_map.get('stage') or 0) != int(state.get('stage') or 0):
                errors.append('map.stage 与 stage 不一致')
    return errors


def _sync_checkpoint_player_fields(state, fields):
    player = state.get('player') or {}
    for checkpoint_name in ('floor_entry_checkpoint', 'recovery_checkpoint'):
        checkpoint = state.get(checkpoint_name)
        snapshot = checkpoint.get('state') if isinstance(checkpoint, dict) else None
        snapshot_player = snapshot.get('player') if isinstance(snapshot, dict) else None
        if not isinstance(snapshot_player, dict):
            continue
        for field in fields:
            if field in player:
                snapshot_player[field] = deepcopy(player[field])
            else:
                snapshot_player.pop(field, None)


def _insert_audit_conn(
    conn,
    *,
    operation_id,
    actor,
    user_id,
    target_kind,
    target_id,
    action_type,
    spec,
    before,
    after,
    before_revision=None,
    after_revision=None,
):
    conn.execute(
        '''INSERT INTO story_admin_mutations
           (operation_id, actor, user_id, target_kind, target_id, action_type,
            command_json, before_json, after_json, before_revision,
            after_revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (
            operation_id, str(actor or 'adminconsole')[:120], int(user_id),
            str(target_kind), str(target_id), str(action_type), _json(spec),
            _json(before), _json(after), before_revision, after_revision,
            _now_iso(),
        ),
    )


def _run_mutation(user, actor, spec, mutator, mode, confirmation='', run_id=None):
    with closing(get_db_connection()) as conn:
        row = _run_row_conn(conn, user['id'], run_id=run_id, active_only=True)
        before = _run_state(row)
    if str(row['content_version'] or '') != STORY_CONTENT_VERSION:
        raise StoryAdminError('该旅程属于旧内容版本；只能查看或放弃，不能直接修改')
    try:
        after, detail, checkpoint_fields = mutator(deepcopy(before), row)
    except StoryActionError as exc:
        raise StoryAdminError(f'{exc.code}: {exc.message}') from exc
    if checkpoint_fields:
        _sync_checkpoint_player_fields(after, checkpoint_fields)
    errors = validate_story_run_state(after, row)
    if errors:
        raise StoryAdminError('修改后的存档未通过校验：\n- ' + '\n- '.join(errors[:20]))
    token = _confirmation_token(
        user['id'], 'run', row['id'], int(row['state_version']), before, spec,
    )
    if mode == 'preview':
        return {
            'success': True,
            'output': (
                f"预览：{user['username']}｜旅程 {row['id']}｜版本 {row['state_version']}\n"
                f'{detail}\n确认令牌：{token}\n'
                f'执行：/story {spec["command"]} confirm={token}'
            ),
        }
    if confirmation != token:
        raise StoryAdminError('确认令牌无效或存档已经变化，请重新 preview')

    operation_id = f'SAM-{secrets.token_hex(8)}'
    now = _now_iso()
    before_hash = _hash(before)
    with closing(get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        current = _run_row_conn(conn, user['id'], run_id=row['id'], active_only=True)
        if current is None:
            conn.rollback()
            raise StoryAdminError('旅程已不存在或已不再生效')
        current_state = _run_state(current)
        if int(current['state_version']) != int(row['state_version']) or _hash(current_state) != before_hash:
            conn.rollback()
            raise StoryAdminError('存档已变化，请重新 preview')
        sequence_row = conn.execute(
            'SELECT COALESCE(MAX(sequence), 0) + 1 AS value FROM story_run_actions WHERE run_id = ?',
            (row['id'],),
        ).fetchone()
        next_revision = int(current['state_version']) + 1
        conn.execute(
            '''INSERT INTO story_run_actions
               (run_id, sequence, action_id, action_type, payload_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (
                row['id'], int(sequence_row['value']), f'admin-{operation_id}',
                f"admin_{spec.get('kind') or 'mutation'}", _json(spec), now,
            ),
        )
        conn.execute(
            '''UPDATE story_runs
               SET state_json = ?, state_version = ?, updated_at = ?
               WHERE id = ? AND user_id = ? AND status = 'active' ''',
            (_json(after), next_revision, now, row['id'], int(user['id'])),
        )
        _insert_audit_conn(
            conn,
            operation_id=operation_id,
            actor=actor,
            user_id=user['id'],
            target_kind='run',
            target_id=row['id'],
            action_type=spec.get('kind') or 'mutation',
            spec=spec,
            before=before,
            after=after,
            before_revision=int(current['state_version']),
            after_revision=next_revision,
        )
        conn.commit()
    return {
        'success': True,
        'output': (
            f'已完成：{detail}\n操作号：{operation_id}\n'
            f'旅程版本：{row["state_version"]} → {next_revision}\n'
            '若玩家正打开故事模式，其下一次操作会收到版本冲突并刷新存档。'
        ),
        'story_admin_audit': operation_id,
    }


def _next_card(player, card_id, upgraded=False):
    serial = max(1, int(player.get('next_card_serial') or 1))
    existing = {
        str(card.get('instance_id') or '')
        for card in player.get('deck') or [] if isinstance(card, dict)
    }
    while f'sc-{serial:04d}' in existing:
        serial += 1
    player['next_card_serial'] = serial + 1
    return {'instance_id': f'sc-{serial:04d}', 'def_id': card_id, 'upgraded': bool(upgraded)}


def _next_book(player, book_id):
    serial = max(1, int(player.get('next_enchantment_book_serial') or 1))
    existing = {
        str(book.get('instance_id') or '')
        for book in player.get('enchantment_books') or [] if isinstance(book, dict)
    }
    while f'seb-{serial:05d}' in existing:
        serial += 1
    player['next_enchantment_book_serial'] = serial + 1
    return {'instance_id': f'seb-{serial:05d}', 'book_id': book_id}


def _repair_state(state, row):
    from story_engine import _normalize_legacy_story_state

    _normalize_legacy_story_state(state)
    player = state.setdefault('player', {})
    for key, (minimum, maximum) in _RESOURCE_LIMITS.items():
        value = player.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            fallback = minimum
            if key in {'health', 'max_health'}:
                fallback = int(STORY_RULES['starting_health'])
            player[key] = fallback
        player[key] = max(minimum, min(maximum, int(player[key])))
    player['health'] = min(player['health'], player['max_health'])
    player['elixir'] = min(player['elixir'], player['max_elixir'])
    player['magic'] = min(player['magic'], player['max_magic'])
    story_map = state.get('map') if isinstance(state.get('map'), dict) else {}
    nodes = {
        str(node.get('id') or ''): node
        for floor in story_map.get('floors') or [] if isinstance(floor, dict)
        for node in floor.get('nodes') or [] if isinstance(node, dict)
    }
    current = nodes.get(str(state.get('current_node_id') or ''))
    if current is not None:
        state['current_floor'] = int(current.get('floor') or 1)
    state['character_id'] = str(player.get('character_id') or state.get('character_id') or 'common_flower')
    for name in ('floor_entry_checkpoint', 'recovery_checkpoint'):
        checkpoint = state.get(name)
        if checkpoint is not None and not (
            isinstance(checkpoint, dict) and isinstance(checkpoint.get('state'), dict)
        ):
            state.pop(name, None)
    return state


def _execute_run(parts, actor):
    if not parts:
        raise StoryAdminError('用法：story run <list|get|actions|create|validate|repair|recover|abandon> ...')
    action = parts[0].lower()
    if action == 'list':
        if len(parts) < 2:
            raise StoryAdminError('用法：story run list <账号> [all]')
        user = _resolve_user(parts[1])
        include_all = len(parts) > 2 and parts[2].lower() == 'all'
        with closing(get_db_connection()) as conn:
            rows = conn.execute(
                '''SELECT * FROM story_runs WHERE user_id = ?
                   AND (? = 1 OR status = 'active')
                   ORDER BY updated_at DESC LIMIT 30''',
                (int(user['id']), 1 if include_all else 0),
            ).fetchall()
        summaries = [_run_summary(row) for row in rows]
        return {'success': True, 'output': _format_mapping(f"{user['username']} 的故事旅程", summaries)}
    if action == 'get':
        if len(parts) < 2:
            raise StoryAdminError('用法：story run get <账号> [run=旅程ID] [full]')
        positional, options = _option_parts(parts[1:])
        if not positional:
            raise StoryAdminError('用法：story run get <账号> [run=旅程ID] [full]')
        user = _resolve_user(positional[0])
        full = any(item.lower() == 'full' for item in positional[1:])
        with closing(get_db_connection()) as conn:
            row = _run_row_conn(conn, user['id'], options.get('run'), active_only=not bool(options.get('run')))
        state = _run_state(row)
        payload = {'summary': _run_summary(row, state)}
        if full:
            payload['state'] = state
        return {'success': True, 'output': _format_mapping(f"{user['username']} 的故事存档", payload)}
    if action == 'actions':
        positional, options = _option_parts(parts[1:])
        if not positional:
            raise StoryAdminError('用法：story run actions <账号> [数量] [run=旅程ID]')
        user = _resolve_user(positional[0])
        limit = _int(positional[1], '数量', 1, 200) if len(positional) > 1 else 30
        with closing(get_db_connection()) as conn:
            row = _run_row_conn(conn, user['id'], options.get('run'), active_only=not bool(options.get('run')))
            actions = [dict(item) for item in conn.execute(
                '''SELECT sequence, action_id, action_type, payload_json, created_at
                   FROM story_run_actions WHERE run_id=?
                   ORDER BY sequence DESC LIMIT ?''',
                (row['id'], limit),
            ).fetchall()]
        for item in actions:
            item['payload'] = _parse_json(item.pop('payload_json') or '{}', '操作参数')
        return {'success': True, 'output': _format_mapping(f"{user['username']}｜旅程 {row['id']} 的最近操作", actions)}
    if action == 'create':
        gated, mode, confirmation = _mutation_gate(parts[1:])
        positional, options = _option_parts(gated)
        if not positional:
            raise StoryAdminError('用法：story run create <账号> [character=角色] [seed=种子] preview')
        user = _resolve_user(positional[0])
        character_id = str(options.get('character') or 'common_flower')
        if character_id not in STORY_CHARACTERS or STORY_CHARACTERS[character_id].get('implementation_status') != 'playable':
            raise StoryAdminError('角色不存在或尚不可游玩')
        seed = str(options.get('seed') or f'admin-{user["id"]}-{datetime.now(timezone.utc):%Y%m%d}')
        spec = {'command': f'run create {positional[0]} character={character_id} seed={seed}', 'kind': 'run_create', 'character_id': character_id, 'seed': seed}
        with closing(get_db_connection()) as conn:
            active = _run_row_conn(conn, user['id'])
        if active is not None:
            raise StoryAdminError('该账号已有生效中的故事旅程')
        token = _confirmation_token(user['id'], 'run_create', 'new', None, {}, spec)
        if mode == 'preview':
            return {'success': True, 'output': f'预览：为 {user["username"]} 创建角色={character_id}、种子={seed} 的新旅程\n确认令牌：{token}\n执行：/story {spec["command"]} confirm={token}'}
        if confirmation != token:
            raise StoryAdminError('确认令牌无效，请重新 preview')
        state = build_initial_story_state(seed, character_id=character_id)
        run, created = create_story_run(user['id'], seed, STORY_CONTENT_VERSION, state)
        if not created:
            raise StoryAdminError('创建时发现已有生效旅程，请重新检查')
        return {'success': True, 'output': f'已为 {user["username"]} 创建故事旅程 {run["id"]}'}
    if action == 'validate':
        if len(parts) < 2:
            raise StoryAdminError('用法：story run validate <账号> [run=旅程ID]')
        positional, options = _option_parts(parts[1:])
        if not positional:
            raise StoryAdminError('用法：story run validate <账号> [run=旅程ID]')
        user = _resolve_user(positional[0])
        with closing(get_db_connection()) as conn:
            row = _run_row_conn(conn, user['id'], options.get('run'), active_only=not bool(options.get('run')))
        errors = validate_story_run_state(_run_state(row), row)
        output = '校验通过，未发现结构性问题。' if not errors else '校验失败：\n- ' + '\n- '.join(errors)
        return {'success': not errors, 'output': f'{user["username"]}｜{row["id"]}\n{output}'}
    if action in {'repair', 'recover', 'abandon'}:
        gated, mode, confirmation = _mutation_gate(parts[1:])
        positional, options = _option_parts(gated)
        if not positional:
            raise StoryAdminError(f'用法：story run {action} <账号> ... preview')
        user = _resolve_user(positional[0])
        if action == 'repair':
            spec = {'command': f'run repair {positional[0]}', 'kind': 'repair'}
            def mutate(state, row):
                before_errors = validate_story_run_state(state, row)
                repaired = _repair_state(state, row)
                return repaired, f'安全修复结构问题；修复前发现 {len(before_errors)} 项', set()
            return _run_mutation(user, actor, spec, mutate, mode, confirmation, options.get('run'))
        if action == 'recover':
            checkpoint = positional[1].lower() if len(positional) > 1 else 'latest'
            if checkpoint not in {'latest', 'floor'}:
                raise StoryAdminError('恢复类型必须是 latest 或 floor')
            action_type = 'resume_node' if checkpoint == 'latest' else 'restart_floor'
            spec = {'command': f'run recover {positional[0]} {checkpoint}', 'kind': 'recover', 'checkpoint': checkpoint}
            def mutate(state, row):
                updated, _events = apply_story_action(state, action_type, {}, row['seed'])
                return updated, f'恢复到 {checkpoint} 检查点', set()
            return _run_mutation(user, actor, spec, mutate, mode, confirmation, options.get('run'))
        spec = {'command': f'run abandon {positional[0]}', 'kind': 'abandon'}
        with closing(get_db_connection()) as conn:
            row = _run_row_conn(conn, user['id'], options.get('run'))
            state = _run_state(row)
        token = _confirmation_token(user['id'], 'run_abandon', row['id'], int(row['state_version']), state, spec)
        if mode == 'preview':
            return {'success': True, 'output': f'预览：放弃 {user["username"]} 的旅程 {row["id"]}\n确认令牌：{token}\n执行：/story {spec["command"]} confirm={token}'}
        if confirmation != token:
            raise StoryAdminError('确认令牌无效或存档已变化，请重新 preview')
        now = _now_iso()
        operation_id = f'SAM-{secrets.token_hex(8)}'
        before_status = {
            'status': row['status'],
            'updated_at': row['updated_at'],
            'completed_at': row['completed_at'],
        }
        after_status = {
            'status': 'abandoned',
            'updated_at': now,
            'completed_at': now,
        }
        with closing(get_db_connection()) as conn:
            conn.execute('BEGIN IMMEDIATE')
            current = _run_row_conn(conn, user['id'], row['id'])
            if current is None or int(current['state_version']) != int(row['state_version']) or _hash(_run_state(current)) != _hash(state):
                conn.rollback()
                raise StoryAdminError('存档已变化，请重新 preview')
            conn.execute("UPDATE story_runs SET status='abandoned', updated_at=?, completed_at=? WHERE id=?", (now, now, row['id']))
            _insert_audit_conn(
                conn, operation_id=operation_id, actor=actor,
                user_id=user['id'], target_kind='run_status',
                target_id=row['id'], action_type='abandon', spec=spec,
                before=before_status, after=after_status,
                before_revision=int(row['state_version']),
                after_revision=int(row['state_version']),
            )
            conn.commit()
        return {'success': True, 'output': f'已放弃旅程 {row["id"]}\n操作号：{operation_id}', 'story_admin_audit': operation_id}
    raise StoryAdminError(f'未知 story run 子命令：{action}')


def _execute_resource(parts, actor):
    if not parts:
        raise StoryAdminError('用法：story resource <get|set|add> ...')
    action = parts[0].lower()
    if action == 'get':
        if len(parts) < 2:
            raise StoryAdminError('用法：story resource get <账号>')
        user = _resolve_user(parts[1])
        with closing(get_db_connection()) as conn:
            row = _run_row_conn(conn, user['id'])
        player = _run_state(row).get('player') or {}
        values = {key: player.get(key) for key in _RESOURCE_LIMITS}
        return {'success': True, 'output': _format_mapping(f"{user['username']} 的故事资源", values)}
    if action not in {'set', 'add'}:
        raise StoryAdminError(f'未知 story resource 子命令：{action}')
    gated, mode, confirmation = _mutation_gate(parts[1:])
    if len(gated) != 3:
        raise StoryAdminError(f'用法：story resource {action} <账号> <资源> <数值> preview')
    account, resource, raw_value = gated
    resource = resource.lower()
    if resource not in _RESOURCE_LIMITS:
        raise StoryAdminError('资源必须是 health|max_health|elixir|max_elixir|magic|max_magic|gold')
    value = _int(raw_value, '数值', -999999999 if action == 'add' else None, 2147483647)
    user = _resolve_user(account)
    spec = {
        'command': f'resource {action} {account} {resource} {value}',
        'kind': 'resource', 'action': action, 'resource': resource, 'value': value,
    }
    def mutate(state, _row):
        player = state['player']
        old = int(player.get(resource) or 0)
        new = value if action == 'set' else old + value
        minimum, maximum = _RESOURCE_LIMITS[resource]
        if new < minimum or new > maximum:
            raise StoryAdminError(f'{resource} 修改后超出 {minimum}-{maximum}')
        player[resource] = new
        paired_fields = {resource}
        if resource == 'max_health' and int(player.get('health') or 0) > new:
            player['health'] = new
            paired_fields.add('health')
        if resource == 'max_elixir' and int(player.get('elixir') or 0) > new:
            player['elixir'] = new
            paired_fields.add('elixir')
        if resource == 'max_magic' and int(player.get('magic') or 0) > new:
            player['magic'] = new
            paired_fields.add('magic')
        combat = state.get('combat')
        if isinstance(combat, dict) and resource in {'elixir', 'magic'}:
            combat[resource] = new
        return state, f'{resource}: {old} → {new}', paired_fields
    return _run_mutation(user, actor, spec, mutate, mode, confirmation)


def _execute_card(parts, actor):
    if not parts:
        raise StoryAdminError('用法：story card <list|add|remove|upgrade|replace> ...')
    action = parts[0].lower()
    if action == 'list':
        if len(parts) < 2:
            raise StoryAdminError('用法：story card list <账号>')
        user = _resolve_user(parts[1])
        with closing(get_db_connection()) as conn:
            row = _run_row_conn(conn, user['id'])
        deck = (_run_state(row).get('player') or {}).get('deck') or []
        values = [
            {
                'index': index,
                'instance_id': card.get('instance_id'),
                'card_id': card.get('def_id'),
                'upgraded': bool(card.get('upgraded')),
            }
            for index, card in enumerate(deck)
        ]
        return {'success': True, 'output': _format_mapping(f"{user['username']} 的故事牌组", values)}
    gated, mode, confirmation = _mutation_gate(parts[1:])
    positional, options = _option_parts(gated)
    if len(positional) < 2:
        raise StoryAdminError(f'用法：story card {action} <账号> ... preview')
    account = positional[0]
    user = _resolve_user(account)
    if action == 'add':
        card_id = positional[1]
        if card_id not in STORY_CARDS:
            raise StoryAdminError(f'未知故事卡牌：{card_id}')
        count = _int(options.get('count', 1), 'count', 1, 100)
        upgraded = _bool_option(options.get('upgraded'), False)
        if upgraded and not isinstance(STORY_CARDS[card_id].get('upgrade'), dict):
            raise StoryAdminError('该卡牌没有升级版本')
        spec = {'command': f'card add {account} {card_id} count={count} upgraded={str(upgraded).lower()}', 'kind': 'card', 'action': 'add', 'card_id': card_id, 'count': count, 'upgraded': upgraded}
        def mutate(state, _row):
            player = state['player']
            added = [_next_card(player, card_id, upgraded) for _ in range(count)]
            player.setdefault('deck', []).extend(added)
            return state, f'加入 {count} 张 {card_id}' + ('（已升级）' if upgraded else ''), {'deck', 'next_card_serial'}
        return _run_mutation(user, actor, spec, mutate, mode, confirmation)
    if action in {'remove', 'upgrade'}:
        selector = positional[1]
        raw_count = str(options.get('count', 1)).lower()
        count = None if raw_count == 'all' else _int(raw_count, 'count', 1, 1000)
        spec = {'command': f'card {action} {account} {selector} count={raw_count}', 'kind': 'card', 'action': action, 'selector': selector, 'count': raw_count}
        def mutate(state, _row):
            deck = state['player'].setdefault('deck', [])
            matches = [
                card for card in deck
                if selector in {str(card.get('instance_id') or ''), str(card.get('def_id') or '')}
            ]
            selected = matches if count is None else matches[:count]
            if not selected:
                raise StoryAdminError(f'牌组中未找到：{selector}')
            if action == 'remove':
                selected_ids = {id(card) for card in selected}
                deck[:] = [card for card in deck if id(card) not in selected_ids]
                detail = f'删除 {len(selected)} 张匹配 {selector} 的卡牌'
            else:
                for card in selected:
                    if not isinstance(STORY_CARDS.get(str(card.get('def_id') or ''), {}).get('upgrade'), dict):
                        raise StoryAdminError(f'{card.get("def_id")} 没有升级版本')
                    card['upgraded'] = True
                detail = f'升级 {len(selected)} 张匹配 {selector} 的卡牌'
            return state, detail, {'deck'}
        return _run_mutation(user, actor, spec, mutate, mode, confirmation)
    if action == 'replace':
        if len(positional) != 3:
            raise StoryAdminError('用法：story card replace <账号> <实例ID> <新卡牌ID> [upgraded=true] preview')
        instance_id, card_id = positional[1], positional[2]
        if card_id not in STORY_CARDS:
            raise StoryAdminError(f'未知故事卡牌：{card_id}')
        upgraded = _bool_option(options.get('upgraded'), False)
        if upgraded and not isinstance(STORY_CARDS[card_id].get('upgrade'), dict):
            raise StoryAdminError('新卡牌没有升级版本')
        spec = {'command': f'card replace {account} {instance_id} {card_id} upgraded={str(upgraded).lower()}', 'kind': 'card', 'action': 'replace', 'instance_id': instance_id, 'card_id': card_id, 'upgraded': upgraded}
        def mutate(state, _row):
            card = next((item for item in state['player'].get('deck') or [] if str(item.get('instance_id') or '') == instance_id), None)
            if card is None:
                raise StoryAdminError(f'牌组中未找到实例：{instance_id}')
            old = str(card.get('def_id') or '')
            card['def_id'] = card_id
            card['upgraded'] = upgraded
            return state, f'替换 {instance_id}: {old} → {card_id}', {'deck'}
        return _run_mutation(user, actor, spec, mutate, mode, confirmation)
    raise StoryAdminError(f'未知 story card 子命令：{action}')


def _execute_relic(parts, actor, domain='relic'):
    if not parts:
        raise StoryAdminError(f'用法：story {domain} <list|add|remove> ...')
    action = parts[0].lower()
    if action == 'list':
        if len(parts) < 2:
            raise StoryAdminError(f'用法：story {domain} list <账号>')
        user = _resolve_user(parts[1])
        with closing(get_db_connection()) as conn:
            row = _run_row_conn(conn, user['id'])
        relics = (_run_state(row).get('player') or {}).get('relics') or []
        return {'success': True, 'output': _format_mapping(f"{user['username']} 的天赋/遗物", relics)}
    if action not in {'add', 'remove'}:
        raise StoryAdminError(f'未知 story {domain} 子命令：{action}')
    gated, mode, confirmation = _mutation_gate(parts[1:])
    positional, options = _option_parts(gated)
    if len(positional) != 2:
        raise StoryAdminError(f'用法：story {domain} {action} <账号> <天赋或遗物ID> [count=数量] preview')
    account, relic_id = positional
    if relic_id not in STORY_RELICS:
        raise StoryAdminError(f'未知天赋/遗物：{relic_id}')
    count = _int(options.get('count', 1), 'count', 1, 100)
    user = _resolve_user(account)
    spec = {'command': f'{domain} {action} {account} {relic_id} count={count}', 'kind': 'relic', 'action': action, 'relic_id': relic_id, 'count': count}
    def mutate(state, _row):
        relics = state['player'].setdefault('relics', [])
        if action == 'add':
            relics.extend([relic_id] * count)
            changed = count
        else:
            changed = 0
            kept = []
            for item in relics:
                if item == relic_id and changed < count:
                    changed += 1
                else:
                    kept.append(item)
            if not changed:
                raise StoryAdminError(f'未持有天赋/遗物：{relic_id}')
            relics[:] = kept
        return state, f'{"加入" if action == "add" else "删除"} {changed} 个 {relic_id}', {'relics'}
    return _run_mutation(user, actor, spec, mutate, mode, confirmation)


def _execute_book(parts, actor):
    if not parts:
        raise StoryAdminError('用法：story book <list|add|remove> ...')
    action = parts[0].lower()
    if action == 'list':
        if len(parts) < 2:
            raise StoryAdminError('用法：story book list <账号>')
        user = _resolve_user(parts[1])
        with closing(get_db_connection()) as conn:
            row = _run_row_conn(conn, user['id'])
        books = (_run_state(row).get('player') or {}).get('enchantment_books') or []
        return {'success': True, 'output': _format_mapping(f"{user['username']} 的附魔书", books)}
    if action not in {'add', 'remove'}:
        raise StoryAdminError(f'未知 story book 子命令：{action}')
    gated, mode, confirmation = _mutation_gate(parts[1:])
    positional, options = _option_parts(gated)
    if len(positional) != 2:
        raise StoryAdminError(f'用法：story book {action} <账号> <附魔书ID或实例ID> [count=数量] preview')
    account, selector = positional
    count = _int(options.get('count', 1), 'count', 1, 3)
    if action == 'add' and selector not in STORY_ENCHANTMENT_BOOKS:
        raise StoryAdminError(f'未知附魔书：{selector}')
    user = _resolve_user(account)
    spec = {'command': f'book {action} {account} {selector} count={count}', 'kind': 'book', 'action': action, 'selector': selector, 'count': count}
    def mutate(state, _row):
        player = state['player']
        books = player.setdefault('enchantment_books', [])
        if action == 'add':
            limit = int(STORY_RULES['enchantment_book_slots'])
            if len(books) + count > limit:
                raise StoryAdminError(f'附魔书槽位上限为 {limit}；请先删除或减少 count')
            books.extend(_next_book(player, selector) for _ in range(count))
            changed = count
        else:
            matches = [book for book in books if selector in {str(book.get('instance_id') or ''), str(book.get('book_id') or '')}]
            selected = matches[:count]
            if not selected:
                raise StoryAdminError(f'未持有附魔书：{selector}')
            selected_ids = {id(book) for book in selected}
            books[:] = [book for book in books if id(book) not in selected_ids]
            changed = len(selected)
        return state, f'{"加入" if action == "add" else "删除"} {changed} 本 {selector}', {'enchantment_books', 'next_enchantment_book_serial'}
    return _run_mutation(user, actor, spec, mutate, mode, confirmation)


def _execute_jump(parts, actor):
    if not parts:
        raise StoryAdminError('用法：story jump <stage|floor|node> ...')
    action = parts[0].lower()
    if action not in {'stage', 'floor', 'node'}:
        raise StoryAdminError('跳转类型必须是 stage、floor 或 node')
    gated, mode, confirmation = _mutation_gate(parts[1:])
    positional, options = _option_parts(gated)
    if len(positional) < 2:
        raise StoryAdminError(f'用法：story jump {action} <账号> <目标> [stage=N] [biome=ID] [node=N] preview')
    account, target = positional[0], positional[1]
    user = _resolve_user(account)
    stage = None
    floor = None
    node_id = ''
    node_index = _int(options.get('node', 0), 'node', 0, 20)
    if action == 'stage':
        stage = _int(target, 'stage', 1, 3)
        floor = _int(options.get('floor', 1), 'floor', 1, 9999)
    elif action == 'floor':
        floor = _int(target, 'floor', 1, 9999)
        stage = _int(options['stage'], 'stage', 1, 3) if 'stage' in options else None
    else:
        node_id = target
        stage = _int(options['stage'], 'stage', 1, 3) if 'stage' in options else None
        floor = _int(options['floor'], 'floor', 1, 9999) if 'floor' in options else None
        if stage is None:
            inferred = re.match(r'^(?:s|br-b)(\d+)[-]', node_id)
            if inferred:
                stage = _int(inferred.group(1), 'stage', 1, 3)
    biome = str(options.get('biome') or '')
    command = f'jump {action} {account} {target}'
    if stage is not None and action != 'stage':
        command += f' stage={stage}'
    if floor is not None and action != 'floor' and not (action == 'stage' and floor == 1):
        command += f' floor={floor}'
    if biome:
        command += f' biome={biome}'
    if node_index and action != 'node':
        command += f' node={node_index}'
    spec = {'command': command, 'kind': 'jump', 'jump_type': action, 'stage': stage, 'floor': floor, 'node_id': node_id, 'node_index': node_index, 'biome': biome}
    def mutate(state, row):
        updated, _events = build_story_admin_jump_state(
            state, row['seed'], stage=stage, floor=floor, node_id=node_id,
            node_index=node_index, biome=biome,
        )
        return updated, f"跳转到阶段 {updated.get('stage')}、层 {updated.get('current_floor')}、房间 {updated.get('current_node_id')}", set()
    return _run_mutation(user, actor, spec, mutate, mode, confirmation)


def _save_row(user_id, run_id, save_id):
    with closing(get_db_connection()) as conn:
        return conn.execute(
            '''SELECT * FROM story_manual_saves
               WHERE id = ? AND run_id = ? AND user_id = ? LIMIT 1''',
            (int(save_id), str(run_id), int(user_id)),
        ).fetchone()


def _manual_saves_snapshot_conn(conn, user_id, run_id):
    run = conn.execute(
        'SELECT manual_save_count, manual_load_count FROM story_runs WHERE id=? AND user_id=?',
        (str(run_id), int(user_id)),
    ).fetchone()
    rows = [dict(row) for row in conn.execute(
        '''SELECT id, run_id, user_id, slot_index, source_state_version,
                  state_json, stage, floor, node_id, created_at
           FROM story_manual_saves WHERE run_id=? AND user_id=?
           ORDER BY slot_index, id''',
        (str(run_id), int(user_id)),
    ).fetchall()]
    return {
        'manual_save_count': int(run['manual_save_count']) if run else 0,
        'manual_load_count': int(run['manual_load_count']) if run else 0,
        'saves': rows,
    }


def _restore_manual_saves_conn(conn, user_id, run_id, snapshot):
    conn.execute(
        'DELETE FROM story_manual_saves WHERE run_id=? AND user_id=?',
        (str(run_id), int(user_id)),
    )
    for row in (snapshot or {}).get('saves') or []:
        conn.execute(
            '''INSERT INTO story_manual_saves
               (id, run_id, user_id, slot_index, source_state_version,
                state_json, stage, floor, node_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                int(row['id']), str(run_id), int(user_id), int(row['slot_index']),
                int(row['source_state_version']), str(row['state_json']),
                int(row['stage']), int(row['floor']), row.get('node_id'),
                row['created_at'],
            ),
        )
    conn.execute(
        '''UPDATE story_runs SET manual_save_count=?, manual_load_count=?
           WHERE id=? AND user_id=?''',
        (
            int((snapshot or {}).get('manual_save_count') or 0),
            int((snapshot or {}).get('manual_load_count') or 0),
            str(run_id), int(user_id),
        ),
    )


def _execute_save(parts, actor):
    if not parts:
        raise StoryAdminError('用法：story save <list|get|create|load|delete|copy> ...')
    action = parts[0].lower()
    if len(parts) < 2:
        raise StoryAdminError(f'用法：story save {action} <账号> ...')
    if action in {'list', 'get'}:
        positional, options = _option_parts(parts[1:])
        user = _resolve_user(positional[0])
        with closing(get_db_connection()) as conn:
            run = _run_row_conn(conn, user['id'], options.get('run'))
        if action == 'list':
            saves = list_story_manual_saves(user['id'], run['id'])
            return {'success': True, 'output': _format_mapping(f"{user['username']} 的手动存档", saves)}
        if len(positional) < 2:
            raise StoryAdminError('用法：story save get <账号> <存档ID> [run=旅程ID] [full]')
        save = _save_row(user['id'], run['id'], _int(positional[1], '存档ID', 1))
        if save is None:
            raise StoryAdminError('未找到手动存档')
        state = _parse_json(save['state_json'], '手动存档')
        payload = dict(save)
        payload.pop('state_json', None)
        if any(item.lower() == 'full' for item in positional[2:]):
            payload['state'] = state
        else:
            payload['phase'] = state.get('phase')
        return {'success': True, 'output': _format_mapping('手动存档', payload)}
    gated, mode, confirmation = _mutation_gate(parts[1:])
    positional, options = _option_parts(gated)
    if not positional:
        raise StoryAdminError(f'用法：story save {action} <账号> ... preview')
    user = _resolve_user(positional[0])
    with closing(get_db_connection()) as conn:
        run = _run_row_conn(conn, user['id'], options.get('run'))
        run_state = _run_state(run)
    if action == 'create':
        spec = {'command': f'save create {positional[0]}', 'kind': 'save_create'}
        token = _confirmation_token(user['id'], 'save_create', run['id'], int(run['state_version']), run_state, spec)
        if mode == 'preview':
            return {'success': True, 'output': f'预览：从旅程版本 {run["state_version"]} 创建手动存档；最多保留 3 份\n确认令牌：{token}\n执行：/story {spec["command"]} confirm={token}'}
        if confirmation != token:
            raise StoryAdminError('确认令牌无效或旅程已变化，请重新 preview')
        if not db_module._story_manual_save_state_is_stable(run_state):
            raise StoryAdminError('当前阶段不允许创建手动存档')
        snapshot = db_module._story_manual_save_snapshot(run_state)
        operation_id = f'SAM-{secrets.token_hex(8)}'
        now = _now_iso()
        with closing(get_db_connection()) as conn:
            conn.execute('BEGIN IMMEDIATE')
            current_run = _run_row_conn(conn, user['id'], run['id'])
            if current_run is None or int(current_run['state_version']) != int(run['state_version']) or _hash(_run_state(current_run)) != _hash(run_state):
                conn.rollback()
                raise StoryAdminError('旅程已变化，请重新 preview')
            before_saves = _manual_saves_snapshot_conn(conn, user['id'], run['id'])
            conn.execute('DELETE FROM story_manual_saves WHERE run_id=? AND slot_index>=2', (run['id'],))
            conn.execute('UPDATE story_manual_saves SET slot_index=2 WHERE run_id=? AND slot_index=1', (run['id'],))
            conn.execute('UPDATE story_manual_saves SET slot_index=1 WHERE run_id=? AND slot_index=0', (run['id'],))
            conn.execute(
                '''INSERT INTO story_manual_saves
                   (run_id, user_id, slot_index, source_state_version,
                    state_json, stage, floor, node_id, created_at)
                   VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?)''',
                (run['id'], int(user['id']), int(run['state_version']), _json(snapshot), int(snapshot.get('stage') or 1), int(snapshot.get('current_floor') or 1), str(snapshot.get('current_node_id') or ''), now),
            )
            conn.execute('UPDATE story_runs SET manual_save_count=manual_save_count+1, updated_at=? WHERE id=? AND user_id=? AND status=\'active\'', (now, run['id'], int(user['id'])))
            after_saves = _manual_saves_snapshot_conn(conn, user['id'], run['id'])
            _insert_audit_conn(conn, operation_id=operation_id, actor=actor, user_id=user['id'], target_kind='manual_saves', target_id=run['id'], action_type='save_create', spec=spec, before=before_saves, after=after_saves, before_revision=int(run['state_version']), after_revision=int(run['state_version']))
            conn.commit()
        saves = list_story_manual_saves(user['id'], run['id'])
        return {'success': True, 'output': _format_mapping(f'已创建手动存档｜操作号 {operation_id}', saves), 'story_admin_audit': operation_id}
    if action not in {'load', 'delete', 'copy'} or len(positional) < 2:
        raise StoryAdminError('用法：story save <load|delete|copy> <账号> <存档ID> preview')
    save_id = _int(positional[1], '存档ID', 1)
    save = _save_row(user['id'], run['id'], save_id)
    if save is None:
        raise StoryAdminError('未找到手动存档')
    save_state = _parse_json(save['state_json'], '手动存档')
    spec = {'command': f'save {action} {positional[0]} {save_id}', 'kind': f'save_{action}', 'save_id': save_id}
    before = {'run': run_state, 'save': save_state}
    token = _confirmation_token(user['id'], f'save_{action}', save_id, int(run['state_version']), before, spec)
    if mode == 'preview':
        detail = {
            'load': '载入并覆盖当前旅程',
            'delete': '删除该手动存档并压紧槽位',
            'copy': '复制该手动存档为最新槽位，并按最多 3 份轮转',
        }[action]
        return {'success': True, 'output': f'预览：{detail}\n确认令牌：{token}\n执行：/story {spec["command"]} confirm={token}'}
    if confirmation != token:
        raise StoryAdminError('确认令牌无效或旅程/手动存档已变化，请重新 preview')
    current_save = _save_row(user['id'], run['id'], save_id)
    if current_save is None or _hash(_parse_json(current_save['state_json'])) != _hash(save_state):
        raise StoryAdminError('手动存档已变化，请重新 preview')
    if action == 'load':
        restored = db_module._story_manual_save_snapshot(save_state)
        errors = validate_story_run_state(restored, run)
        if errors:
            raise StoryAdminError('手动存档不再兼容当前内容：\n- ' + '\n- '.join(errors))
        operation_id = f'SAM-{secrets.token_hex(8)}'
        now = _now_iso()
        with closing(get_db_connection()) as conn:
            conn.execute('BEGIN IMMEDIATE')
            current_run = _run_row_conn(conn, user['id'], run['id'])
            current_save = conn.execute(
                'SELECT * FROM story_manual_saves WHERE id=? AND run_id=? AND user_id=?',
                (save_id, run['id'], int(user['id'])),
            ).fetchone()
            if (
                current_run is None
                or int(current_run['state_version']) != int(run['state_version'])
                or _hash(_run_state(current_run)) != _hash(run_state)
                or current_save is None
                or _hash(_parse_json(current_save['state_json'])) != _hash(save_state)
            ):
                conn.rollback()
                raise StoryAdminError('旅程或手动存档已变化，请重新 preview')
            if not db_module._story_manual_save_state_is_stable(run_state):
                conn.rollback()
                raise StoryAdminError('当前阶段不允许载入手动存档')
            next_revision = int(current_run['state_version']) + 1
            sequence = conn.execute(
                'SELECT COALESCE(MAX(sequence), 0) + 1 AS value FROM story_run_actions WHERE run_id=?',
                (run['id'],),
            ).fetchone()['value']
            conn.execute(
                'INSERT INTO story_run_actions (run_id, sequence, action_id, action_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (run['id'], int(sequence), f'admin-{operation_id}', 'admin_save_load', _json(spec), now),
            )
            conn.execute(
                '''UPDATE story_runs SET state_json=?, state_version=?,
                          manual_load_count=manual_load_count+1, updated_at=?
                   WHERE id=? AND user_id=? AND status='active' ''',
                (_json(restored), next_revision, now, run['id'], int(user['id'])),
            )
            _insert_audit_conn(
                conn, operation_id=operation_id, actor=actor,
                user_id=user['id'], target_kind='run', target_id=run['id'],
                action_type='save_load', spec=spec, before=run_state,
                after=restored, before_revision=int(current_run['state_version']),
                after_revision=next_revision,
            )
            conn.commit()
        return {
            'success': True,
            'output': f'已载入手动存档 {save_id}；旅程版本现在为 {next_revision}\n操作号：{operation_id}',
            'story_admin_audit': operation_id,
        }
    if action == 'copy':
        now = _now_iso()
        operation_id = f'SAM-{secrets.token_hex(8)}'
        with closing(get_db_connection()) as conn:
            conn.execute('BEGIN IMMEDIATE')
            current_run = _run_row_conn(conn, user['id'], run['id'])
            current_save = conn.execute(
                'SELECT * FROM story_manual_saves WHERE id=? AND run_id=? AND user_id=?',
                (save_id, run['id'], int(user['id'])),
            ).fetchone()
            if (
                current_run is None
                or int(current_run['state_version']) != int(run['state_version'])
                or _hash(_run_state(current_run)) != _hash(run_state)
                or current_save is None
                or _hash(_parse_json(current_save['state_json'])) != _hash(save_state)
            ):
                conn.rollback()
                raise StoryAdminError('旅程或手动存档已变化，请重新 preview')
            before_saves = _manual_saves_snapshot_conn(conn, user['id'], run['id'])
            conn.execute('DELETE FROM story_manual_saves WHERE run_id=? AND slot_index>=2', (run['id'],))
            conn.execute('UPDATE story_manual_saves SET slot_index=2 WHERE run_id=? AND slot_index=1', (run['id'],))
            conn.execute('UPDATE story_manual_saves SET slot_index=1 WHERE run_id=? AND slot_index=0', (run['id'],))
            cursor = conn.execute(
                '''INSERT INTO story_manual_saves
                   (run_id, user_id, slot_index, source_state_version,
                    state_json, stage, floor, node_id, created_at)
                   VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?)''',
                (
                    run['id'], int(user['id']), int(current_save['source_state_version']),
                    str(current_save['state_json']), int(current_save['stage']),
                    int(current_save['floor']), current_save['node_id'], now,
                ),
            )
            copied_save_id = int(cursor.lastrowid)
            conn.execute(
                '''UPDATE story_runs SET manual_save_count=manual_save_count+1,
                          updated_at=? WHERE id=? AND user_id=? AND status='active' ''',
                (now, run['id'], int(user['id'])),
            )
            after_saves = _manual_saves_snapshot_conn(conn, user['id'], run['id'])
            _insert_audit_conn(conn, operation_id=operation_id, actor=actor, user_id=user['id'], target_kind='manual_saves', target_id=run['id'], action_type='save_copy', spec=spec, before=before_saves, after=after_saves, before_revision=int(run['state_version']), after_revision=int(run['state_version']))
            conn.commit()
        saves = list_story_manual_saves(user['id'], run['id'])
        return {'success': True, 'output': _format_mapping(f'已复制为手动存档 {copied_save_id}｜操作号 {operation_id}', saves), 'story_admin_audit': operation_id}
    operation_id = f'SAM-{secrets.token_hex(8)}'
    with closing(get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        current_run = _run_row_conn(conn, user['id'], run['id'])
        current_save = conn.execute('SELECT * FROM story_manual_saves WHERE id=? AND run_id=? AND user_id=?', (save_id, run['id'], int(user['id']))).fetchone()
        if (
            current_run is None
            or int(current_run['state_version']) != int(run['state_version'])
            or _hash(_run_state(current_run)) != _hash(run_state)
            or current_save is None
            or _hash(_parse_json(current_save['state_json'])) != _hash(save_state)
        ):
            conn.rollback()
            raise StoryAdminError('旅程或手动存档已变化，请重新 preview')
        before_saves = _manual_saves_snapshot_conn(conn, user['id'], run['id'])
        conn.execute('DELETE FROM story_manual_saves WHERE id=? AND run_id=? AND user_id=?', (save_id, run['id'], int(user['id'])))
        remaining = conn.execute('SELECT id FROM story_manual_saves WHERE run_id=? AND user_id=? ORDER BY slot_index, created_at DESC, id DESC', (run['id'], int(user['id']))).fetchall()
        for slot_index, item in enumerate(remaining):
            conn.execute('UPDATE story_manual_saves SET slot_index=? WHERE id=?', (slot_index, int(item['id'])))
        after_saves = _manual_saves_snapshot_conn(conn, user['id'], run['id'])
        _insert_audit_conn(conn, operation_id=operation_id, actor=actor, user_id=user['id'], target_kind='manual_saves', target_id=run['id'], action_type='save_delete', spec=spec, before=before_saves, after=after_saves, before_revision=int(run['state_version']), after_revision=int(run['state_version']))
        conn.commit()
    saves = list_story_manual_saves(user['id'], run['id'])
    return {'success': True, 'output': _format_mapping(f'已删除手动存档 {save_id}｜操作号 {operation_id}', saves), 'story_admin_audit': operation_id}


def _progress_rows_conn(conn, user_id):
    return [dict(row) for row in conn.execute(
        '''SELECT character_id, difficulty, standard_clears, boss_rush_clears,
                  first_cleared_at, last_cleared_at
           FROM story_progress WHERE user_id = ?
           ORDER BY character_id, difficulty''',
        (int(user_id),),
    ).fetchall()]


def _execute_progress(parts, actor):
    if not parts:
        raise StoryAdminError('用法：story progress <get|set|add> ...')
    action = parts[0].lower()
    if action == 'get':
        if len(parts) < 2:
            raise StoryAdminError('用法：story progress get <账号>')
        user = _resolve_user(parts[1])
        with closing(get_db_connection()) as conn:
            rows = _progress_rows_conn(conn, user['id'])
        return {'success': True, 'output': _format_mapping(f"{user['username']} 的通关进度", rows)}
    if action not in {'set', 'add'}:
        raise StoryAdminError(f'未知 story progress 子命令：{action}')
    gated, mode, confirmation = _mutation_gate(parts[1:])
    if len(gated) != 5:
        raise StoryAdminError(f'用法：story progress {action} <账号> <角色> <难度> <standard|boss_rush> <数量> preview')
    account, character_raw, difficulty_raw, journey_raw, value_raw = gated
    try:
        character_id = normalize_story_character_id(character_raw)
        difficulty = normalize_story_difficulty(difficulty_raw)
        journey_mode = normalize_story_journey_mode(journey_raw)
    except ValueError as exc:
        raise StoryAdminError(f'角色、难度或模式无效：{exc}') from exc
    value = _int(value_raw, '数量', -999999 if action == 'add' else 0, 999999)
    user = _resolve_user(account)
    column = 'standard_clears' if journey_mode == 'standard' else 'boss_rush_clears'
    target_id = f'{character_id}:{difficulty}:{journey_mode}'
    spec = {'command': f'progress {action} {account} {character_id} {difficulty} {journey_mode} {value}', 'kind': 'progress', 'action': action, 'character_id': character_id, 'difficulty': difficulty, 'journey_mode': journey_mode, 'value': value}
    with closing(get_db_connection()) as conn:
        before_rows = _progress_rows_conn(conn, user['id'])
    current_row = next((row for row in before_rows if row['character_id'] == character_id and row['difficulty'] == difficulty), None)
    old = int((current_row or {}).get(column) or 0)
    new = value if action == 'set' else old + value
    if new < 0 or new > 999999:
        raise StoryAdminError('修改后的通关次数必须在 0-999999 之间')
    after_rows = deepcopy(before_rows)
    after_row = next((row for row in after_rows if row['character_id'] == character_id and row['difficulty'] == difficulty), None)
    now = _now_iso()
    if after_row is None:
        after_row = {'character_id': character_id, 'difficulty': difficulty, 'standard_clears': 0, 'boss_rush_clears': 0, 'first_cleared_at': None, 'last_cleared_at': None}
        after_rows.append(after_row)
    after_row[column] = new
    if int(after_row['standard_clears']) == 0 and int(after_row['boss_rush_clears']) == 0:
        after_rows.remove(after_row)
    elif old == 0 and new > 0:
        after_row['first_cleared_at'] = after_row.get('first_cleared_at') or now
        after_row['last_cleared_at'] = now
    after_rows.sort(key=lambda row: (row['character_id'], row['difficulty']))
    token = _confirmation_token(user['id'], 'progress', target_id, None, before_rows, spec)
    if mode == 'preview':
        return {'success': True, 'output': f'预览：{target_id} {old} → {new}\n确认令牌：{token}\n执行：/story {spec["command"]} confirm={token}\n说明：这是管理修正，不伪造单人或协作旅程的历史来源记录。'}
    if confirmation != token:
        raise StoryAdminError('确认令牌无效或进度已变化，请重新 preview')
    operation_id = f'SAM-{secrets.token_hex(8)}'
    with closing(get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if _hash(_progress_rows_conn(conn, user['id'])) != _hash(before_rows):
            conn.rollback()
            raise StoryAdminError('通关进度已变化，请重新 preview')
        conn.execute('DELETE FROM story_progress WHERE user_id = ?', (int(user['id']),))
        for row in after_rows:
            conn.execute(
                '''INSERT INTO story_progress
                   (user_id, character_id, difficulty, standard_clears,
                    boss_rush_clears, first_cleared_at, last_cleared_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (int(user['id']), row['character_id'], row['difficulty'], int(row['standard_clears']), int(row['boss_rush_clears']), row.get('first_cleared_at'), row.get('last_cleared_at')),
            )
        _insert_audit_conn(conn, operation_id=operation_id, actor=actor, user_id=user['id'], target_kind='progress', target_id=target_id, action_type='progress', spec=spec, before=before_rows, after=after_rows)
        conn.commit()
    return {'success': True, 'output': f'已修改 {target_id}: {old} → {new}\n操作号：{operation_id}', 'story_admin_audit': operation_id}


def _discovery_row_conn(conn, user_id, content_type, content_id, variant):
    row = conn.execute(
        '''SELECT user_id, content_type, content_id, variant, first_run_id,
                  first_seen_at, last_seen_at, seen_count, viewed_at
           FROM story_discoveries
           WHERE user_id=? AND content_type=? AND content_id=? AND variant=?''',
        (int(user_id), content_type, content_id, variant),
    ).fetchone()
    return dict(row) if row is not None else None


def _validate_discovery(content_type, content_id, variant):
    if content_type == 'term':
        term_kind, separator, term_id = content_id.partition(':')
        catalogs = {
            'tag': STORY_TAGS,
            'status': STORY_STATUSES,
            'trait': STORY_TRAITS,
            'resource': {'D': None, 'H': None, 'E': None, 'M': None},
        }
        if not separator or term_kind not in catalogs or term_id not in catalogs[term_kind]:
            raise StoryAdminError('术语 ID 必须形如 tag:ID、status:ID、trait:ID 或 resource:D')
        if variant != 'base':
            raise StoryAdminError('术语只支持 base variant')
        return
    catalog = _DISCOVERY_CATALOGS.get(content_type)
    if catalog is None or content_id not in catalog:
        raise StoryAdminError(f'未知图鉴内容：{content_type}:{content_id}')
    if content_type == 'card' and variant not in {'base', 'upgraded'}:
        raise StoryAdminError('卡牌 variant 必须是 base 或 upgraded')
    if content_type == 'card' and variant == 'upgraded' and not isinstance(STORY_CARDS[content_id].get('upgrade'), dict):
        raise StoryAdminError('该卡牌没有升级版本')
    if content_type == 'enemy' and variant != 'base':
        match = re.fullmatch(r'intent:(\d+)', variant)
        if not match or int(match.group(1)) >= len(STORY_ENEMIES[content_id].get('moves') or ()):
            raise StoryAdminError('生物 variant 必须是 base 或有效的 intent:N')
    if content_type not in {'card', 'enemy'} and variant != 'base':
        raise StoryAdminError('该内容类型只支持 base variant')


def _execute_discovery(parts, actor):
    if not parts:
        raise StoryAdminError('用法：story discovery <list|add|remove|read> ...')
    action = parts[0].lower()
    if action == 'list':
        if len(parts) < 2:
            raise StoryAdminError('用法：story discovery list <账号> [类型]')
        user = _resolve_user(parts[1])
        content_filter = parts[2].lower() if len(parts) > 2 else ''
        with closing(get_db_connection()) as conn:
            rows = [dict(row) for row in conn.execute(
                '''SELECT content_type, content_id, variant, first_seen_at,
                          last_seen_at, seen_count, viewed_at
                   FROM story_discoveries WHERE user_id=?
                   AND (?='' OR content_type=?)
                   ORDER BY content_type, content_id, variant''',
                (int(user['id']), content_filter, content_filter),
            ).fetchall()]
        return {'success': True, 'output': _format_mapping(f"{user['username']} 的故事图鉴发现", rows)}
    if action == 'read':
        gated, mode, confirmation = _mutation_gate(parts[1:])
        if len(gated) != 1:
            raise StoryAdminError('用法：story discovery read <账号> preview')
        user = _resolve_user(gated[0])
        spec = {'command': f'discovery read {gated[0]}', 'kind': 'discovery_read'}
        with closing(get_db_connection()) as conn:
            unread = [dict(row) for row in conn.execute('SELECT content_type, content_id, variant FROM story_discoveries WHERE user_id=? AND viewed_at IS NULL ORDER BY content_type, content_id, variant', (int(user['id']),)).fetchall()]
        token = _confirmation_token(user['id'], 'discovery_read', 'all', None, unread, spec)
        if mode == 'preview':
            return {'success': True, 'output': f'预览：把 {len(unread)} 条故事图鉴发现标为已读\n确认令牌：{token}\n执行：/story {spec["command"]} confirm={token}'}
        if confirmation != token:
            raise StoryAdminError('确认令牌无效或图鉴已变化，请重新 preview')
        with closing(get_db_connection()) as conn:
            conn.execute('UPDATE story_discoveries SET viewed_at=COALESCE(viewed_at, ?) WHERE user_id=?', (_now_iso(), int(user['id'])))
            conn.commit()
        return {'success': True, 'output': f'已把 {len(unread)} 条故事图鉴发现标为已读'}
    if action not in {'add', 'remove'}:
        raise StoryAdminError(f'未知 story discovery 子命令：{action}')
    gated, mode, confirmation = _mutation_gate(parts[1:])
    positional, options = _option_parts(gated)
    if len(positional) != 3:
        raise StoryAdminError(f'用法：story discovery {action} <账号> <类型> <内容ID> [variant=base] preview')
    account, content_type, content_id = positional
    content_type = content_type.lower()
    variant = str(options.get('variant') or 'base').lower()
    _validate_discovery(content_type, content_id, variant)
    user = _resolve_user(account)
    target_id = f'{content_type}:{content_id}:{variant}'
    spec = {'command': f'discovery {action} {account} {content_type} {content_id} variant={variant}', 'kind': 'discovery', 'action': action, 'content_type': content_type, 'content_id': content_id, 'variant': variant}
    with closing(get_db_connection()) as conn:
        before = _discovery_row_conn(conn, user['id'], content_type, content_id, variant)
    if action == 'add' and before is not None:
        raise StoryAdminError('该图鉴内容已经发现')
    if action == 'remove' and before is None:
        raise StoryAdminError('该图鉴内容尚未发现')
    now = _now_iso()
    after = None if action == 'remove' else {'user_id': int(user['id']), 'content_type': content_type, 'content_id': content_id, 'variant': variant, 'first_run_id': None, 'first_seen_at': now, 'last_seen_at': now, 'seen_count': 1, 'viewed_at': None}
    token = _confirmation_token(user['id'], 'discovery', target_id, None, before, spec)
    if mode == 'preview':
        return {'success': True, 'output': f'预览：{action} {target_id}\n确认令牌：{token}\n执行：/story {spec["command"]} confirm={token}'}
    if confirmation != token:
        raise StoryAdminError('确认令牌无效或图鉴已变化，请重新 preview')
    operation_id = f'SAM-{secrets.token_hex(8)}'
    with closing(get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        current = _discovery_row_conn(conn, user['id'], content_type, content_id, variant)
        if _hash(current) != _hash(before):
            conn.rollback()
            raise StoryAdminError('图鉴已变化，请重新 preview')
        if after is None:
            conn.execute('DELETE FROM story_discoveries WHERE user_id=? AND content_type=? AND content_id=? AND variant=?', (int(user['id']), content_type, content_id, variant))
        else:
            conn.execute('''INSERT INTO story_discoveries (user_id, content_type, content_id, variant, first_run_id, first_seen_at, last_seen_at, seen_count, viewed_at) VALUES (?, ?, ?, ?, NULL, ?, ?, 1, NULL)''', (int(user['id']), content_type, content_id, variant, now, now))
        _insert_audit_conn(conn, operation_id=operation_id, actor=actor, user_id=user['id'], target_kind='discovery', target_id=target_id, action_type='discovery', spec=spec, before=before, after=after)
        conn.commit()
    return {'success': True, 'output': f'已{("加入" if action == "add" else "删除")}图鉴内容 {target_id}\n操作号：{operation_id}', 'story_admin_audit': operation_id}


def _restore_progress_rows_conn(conn, user_id, rows):
    conn.execute('DELETE FROM story_progress WHERE user_id = ?', (int(user_id),))
    for row in rows or []:
        conn.execute(
            '''INSERT INTO story_progress
               (user_id, character_id, difficulty, standard_clears,
                boss_rush_clears, first_cleared_at, last_cleared_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (int(user_id), row['character_id'], row['difficulty'], int(row['standard_clears']), int(row['boss_rush_clears']), row.get('first_cleared_at'), row.get('last_cleared_at')),
        )


def _restore_discovery_conn(conn, user_id, spec, row):
    key = (int(user_id), spec['content_type'], spec['content_id'], spec['variant'])
    conn.execute(
        'DELETE FROM story_discoveries WHERE user_id=? AND content_type=? AND content_id=? AND variant=?',
        key,
    )
    if row is not None:
        conn.execute(
            '''INSERT INTO story_discoveries
               (user_id, content_type, content_id, variant, first_run_id,
                first_seen_at, last_seen_at, seen_count, viewed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (int(user_id), row['content_type'], row['content_id'], row['variant'], row.get('first_run_id'), row['first_seen_at'], row['last_seen_at'], int(row.get('seen_count') or 1), row.get('viewed_at')),
        )


def _execute_audit(parts, actor):
    if not parts:
        raise StoryAdminError('用法：story audit <list|show|undo> ...')
    action = parts[0].lower()
    if action == 'list':
        if len(parts) < 2:
            raise StoryAdminError('用法：story audit list <账号> [数量]')
        user = _resolve_user(parts[1])
        limit = _int(parts[2], '数量', 1, 100) if len(parts) > 2 else 20
        with closing(get_db_connection()) as conn:
            rows = [dict(row) for row in conn.execute(
                '''SELECT operation_id, actor, target_kind, target_id,
                          action_type, before_revision, after_revision,
                          created_at, undone_at, undone_by
                   FROM story_admin_mutations WHERE user_id=?
                   ORDER BY created_at DESC, operation_id DESC LIMIT ?''',
                (int(user['id']), limit),
            ).fetchall()]
        return {'success': True, 'output': _format_mapping(f"{user['username']} 的故事管理操作", rows)}
    if action == 'show':
        if len(parts) != 2:
            raise StoryAdminError('用法：story audit show <操作号>')
        with closing(get_db_connection()) as conn:
            row = conn.execute('SELECT * FROM story_admin_mutations WHERE operation_id=?', (parts[1],)).fetchone()
        if row is None:
            raise StoryAdminError('未找到故事管理操作')
        payload = dict(row)
        for key in ('command_json', 'before_json', 'after_json'):
            payload[key[:-5] if key.endswith('_json') else key] = _parse_json(payload.pop(key), key)
        return {'success': True, 'output': _format_mapping(f'故事管理操作 {parts[1]}', payload)}
    if action != 'undo':
        raise StoryAdminError(f'未知 story audit 子命令：{action}')
    gated, mode, confirmation = _mutation_gate(parts[1:])
    if len(gated) != 1:
        raise StoryAdminError('用法：story audit undo <操作号> preview')
    operation_id = gated[0]
    with closing(get_db_connection()) as conn:
        row = conn.execute('SELECT * FROM story_admin_mutations WHERE operation_id=?', (operation_id,)).fetchone()
    if row is None:
        raise StoryAdminError('未找到故事管理操作')
    row = dict(row)
    if row.get('undone_at'):
        raise StoryAdminError(f'该操作已于 {row["undone_at"]} 被撤销')
    if str(row.get('action_type') or '').startswith('undo:'):
        raise StoryAdminError('撤销操作本身不能再次撤销；请撤销它之前对应的新操作')
    before = _parse_json(row['before_json'], '撤销前状态')
    after = _parse_json(row['after_json'], '撤销后状态')
    spec = _parse_json(row['command_json'], '操作参数')
    target_kind = row['target_kind']
    user_id = int(row['user_id'])
    if target_kind == 'run':
        with closing(get_db_connection()) as conn:
            run = _run_row_conn(conn, user_id, row['target_id'], active_only=True)
        if run is None:
            raise StoryAdminError('目标旅程已不再生效，不能自动撤销')
        current = _run_state(run)
        if int(run['state_version']) != int(row['after_revision'] or -1) or _hash(current) != _hash(after):
            raise StoryAdminError('目标旅程在该操作后又发生了变化，拒绝覆盖；请先检查当前存档')
        revision = int(run['state_version'])
        current_value = current
    elif target_kind == 'run_status':
        with closing(get_db_connection()) as conn:
            run = _run_row_conn(conn, user_id, row['target_id'], active_only=False)
            active = _run_row_conn(conn, user_id, active_only=True)
        if run is None:
            raise StoryAdminError('目标旅程已不存在，不能撤销')
        current_value = {
            'status': run['status'],
            'updated_at': run['updated_at'],
            'completed_at': run['completed_at'],
        }
        if _hash(current_value) != _hash(after):
            raise StoryAdminError('旅程状态在该操作后又发生了变化，拒绝覆盖')
        if before.get('status') == 'active' and active is not None and active['id'] != row['target_id']:
            raise StoryAdminError('该账号已有另一段生效旅程，不能恢复旧旅程')
        revision = int(run['state_version'])
    elif target_kind == 'progress':
        with closing(get_db_connection()) as conn:
            current_value = _progress_rows_conn(conn, user_id)
        if _hash(current_value) != _hash(after):
            raise StoryAdminError('通关进度在该操作后又发生了变化，拒绝覆盖')
        revision = None
    elif target_kind == 'manual_saves':
        with closing(get_db_connection()) as conn:
            run = _run_row_conn(conn, user_id, row['target_id'], active_only=True)
            current_value = _manual_saves_snapshot_conn(conn, user_id, row['target_id']) if run is not None else None
        if run is None:
            raise StoryAdminError('目标旅程已不再生效，不能自动撤销手动存档操作')
        if _hash(current_value) != _hash(after):
            raise StoryAdminError('手动存档在该操作后又发生了变化，拒绝覆盖')
        revision = int(run['state_version'])
    elif target_kind == 'discovery':
        with closing(get_db_connection()) as conn:
            current_value = _discovery_row_conn(conn, user_id, spec['content_type'], spec['content_id'], spec['variant'])
        if _hash(current_value) != _hash(after):
            raise StoryAdminError('图鉴数据在该操作后又发生了变化，拒绝覆盖')
        revision = None
    else:
        raise StoryAdminError(f'该操作类型暂不支持撤销：{target_kind}')
    undo_spec = {'command': f'audit undo {operation_id}', 'kind': 'undo', 'source_operation_id': operation_id}
    token = _confirmation_token(user_id, f'undo:{target_kind}', row['target_id'], revision, current_value, undo_spec)
    if mode == 'preview':
        return {'success': True, 'output': f'预览：撤销 {operation_id}（{target_kind}:{row["target_id"]}）\n确认令牌：{token}\n执行：/story audit undo {operation_id} confirm={token}'}
    if confirmation != token:
        raise StoryAdminError('确认令牌无效或目标已变化，请重新 preview')
    undo_id = f'SAM-{secrets.token_hex(8)}'
    now = _now_iso()
    with closing(get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if target_kind == 'run':
            current_row = _run_row_conn(conn, user_id, row['target_id'], active_only=True)
            if current_row is None or int(current_row['state_version']) != int(row['after_revision'] or -1) or _hash(_run_state(current_row)) != _hash(after):
                conn.rollback()
                raise StoryAdminError('目标旅程已变化，请重新 preview')
            validate_errors = validate_story_run_state(before, current_row)
            if validate_errors:
                conn.rollback()
                raise StoryAdminError('原状态已不兼容当前内容版本，不能撤销：\n- ' + '\n- '.join(validate_errors))
            next_revision = int(current_row['state_version']) + 1
            sequence = conn.execute('SELECT COALESCE(MAX(sequence), 0) + 1 AS value FROM story_run_actions WHERE run_id=?', (row['target_id'],)).fetchone()['value']
            conn.execute('INSERT INTO story_run_actions (run_id, sequence, action_id, action_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)', (row['target_id'], int(sequence), f'admin-{undo_id}', 'admin_undo', _json(undo_spec), now))
            conn.execute('UPDATE story_runs SET state_json=?, state_version=?, updated_at=? WHERE id=? AND user_id=? AND status=\'active\'', (_json(before), next_revision, now, row['target_id'], user_id))
            _insert_audit_conn(conn, operation_id=undo_id, actor=actor, user_id=user_id, target_kind='run', target_id=row['target_id'], action_type=f'undo:{operation_id}', spec=undo_spec, before=after, after=before, before_revision=int(current_row['state_version']), after_revision=next_revision)
        elif target_kind == 'run_status':
            current_row = _run_row_conn(conn, user_id, row['target_id'], active_only=False)
            current_status = None if current_row is None else {
                'status': current_row['status'],
                'updated_at': current_row['updated_at'],
                'completed_at': current_row['completed_at'],
            }
            active_row = _run_row_conn(conn, user_id, active_only=True)
            if (
                current_row is None
                or _hash(current_status) != _hash(after)
                or (
                    before.get('status') == 'active'
                    and active_row is not None
                    and active_row['id'] != row['target_id']
                )
            ):
                conn.rollback()
                raise StoryAdminError('旅程状态已变化，请重新 preview')
            conn.execute(
                'UPDATE story_runs SET status=?, updated_at=?, completed_at=? WHERE id=? AND user_id=?',
                (before.get('status'), before.get('updated_at'), before.get('completed_at'), row['target_id'], user_id),
            )
            _insert_audit_conn(conn, operation_id=undo_id, actor=actor, user_id=user_id, target_kind='run_status', target_id=row['target_id'], action_type=f'undo:{operation_id}', spec=undo_spec, before=after, after=before, before_revision=int(current_row['state_version']), after_revision=int(current_row['state_version']))
        elif target_kind == 'progress':
            if _hash(_progress_rows_conn(conn, user_id)) != _hash(after):
                conn.rollback()
                raise StoryAdminError('通关进度已变化，请重新 preview')
            _restore_progress_rows_conn(conn, user_id, before)
            _insert_audit_conn(conn, operation_id=undo_id, actor=actor, user_id=user_id, target_kind='progress', target_id=row['target_id'], action_type=f'undo:{operation_id}', spec=undo_spec, before=after, after=before)
        elif target_kind == 'manual_saves':
            current_row = _run_row_conn(conn, user_id, row['target_id'], active_only=True)
            current_saves = _manual_saves_snapshot_conn(conn, user_id, row['target_id']) if current_row is not None else None
            if current_row is None or _hash(current_saves) != _hash(after):
                conn.rollback()
                raise StoryAdminError('手动存档已变化，请重新 preview')
            _restore_manual_saves_conn(conn, user_id, row['target_id'], before)
            _insert_audit_conn(conn, operation_id=undo_id, actor=actor, user_id=user_id, target_kind='manual_saves', target_id=row['target_id'], action_type=f'undo:{operation_id}', spec=undo_spec, before=after, after=before, before_revision=int(current_row['state_version']), after_revision=int(current_row['state_version']))
        else:
            current = _discovery_row_conn(conn, user_id, spec['content_type'], spec['content_id'], spec['variant'])
            if _hash(current) != _hash(after):
                conn.rollback()
                raise StoryAdminError('图鉴数据已变化，请重新 preview')
            _restore_discovery_conn(conn, user_id, spec, before)
            _insert_audit_conn(conn, operation_id=undo_id, actor=actor, user_id=user_id, target_kind='discovery', target_id=row['target_id'], action_type=f'undo:{operation_id}', spec=undo_spec, before=after, after=before)
        conn.execute('UPDATE story_admin_mutations SET undone_at=?, undone_by=? WHERE operation_id=? AND undone_at IS NULL', (now, str(actor or 'adminconsole')[:120], operation_id))
        conn.commit()
    return {'success': True, 'output': f'已撤销 {operation_id}\n新操作号：{undo_id}', 'story_admin_audit': undo_id}


def _content_catalog(kind):
    catalogs = {
        'card': STORY_CARDS,
        'relic': STORY_RELICS,
        'talent': STORY_RELICS,
        'book': STORY_ENCHANTMENT_BOOKS,
        'enchantment_book': STORY_ENCHANTMENT_BOOKS,
        'character': STORY_CHARACTERS,
        'biome': STORY_BIOMES,
        'difficulty': STORY_DIFFICULTIES,
        'enemy': STORY_ENEMIES,
        'blessing': STORY_BLESSINGS,
    }
    return catalogs.get(str(kind or '').lower())


def story_admin_content_values(kind, needle=''):
    catalog = _content_catalog(kind)
    if catalog is None:
        return []
    needle = str(needle or '').lower()
    values = []
    for content_id, definition in catalog.items():
        names = definition.get('name') if isinstance(definition, dict) else {}
        haystack = ' '.join((str(content_id), str((names or {}).get('zh') or ''), str((names or {}).get('en') or ''))).lower()
        if not needle or needle in haystack:
            values.append(str(content_id))
    return sorted(values)


def _execute_content(parts):
    if not parts or parts[0].lower() != 'list' or len(parts) < 2:
        raise StoryAdminError('用法：story content list <card|relic|book|character|biome|difficulty|enemy|blessing> [搜索]')
    kind = parts[1].lower()
    catalog = _content_catalog(kind)
    if catalog is None:
        raise StoryAdminError(f'未知故事内容类型：{kind}')
    needle = str(parts[2] if len(parts) > 2 else '').lower()
    rows = []
    for content_id in story_admin_content_values(kind, needle):
        definition = catalog[content_id]
        name = definition.get('name') if isinstance(definition, dict) else {}
        rows.append({'id': content_id, 'name_zh': (name or {}).get('zh'), 'name_en': (name or {}).get('en')})
    return {'success': True, 'output': _format_mapping(f'故事内容 {kind}（{len(rows)}）', rows[:200])}


def _execute_coop(parts):
    if not parts:
        raise StoryAdminError('用法：story coop <list|get|validate|repair> ...')
    action = parts[0].lower()
    if action not in {'list', 'get', 'validate', 'repair'}:
        raise StoryAdminError(f'未知 story coop 子命令：{action}')
    if len(parts) < 2:
        raise StoryAdminError(f'用法：story coop {action} <账号> [run=旅程ID]')
    positional, options = _option_parts(parts[1:])
    user = _resolve_user(positional[0])
    with closing(get_db_connection()) as conn:
        rows = conn.execute(
            '''SELECT r.*, p.status AS party_status, m.seat, m.party_role,
                      m.membership_status
               FROM story_coop_runs r
               JOIN story_coop_party_members m ON m.party_id=r.party_id
               JOIN story_coop_parties p ON p.id=r.party_id
               WHERE m.user_id=? AND (?='' OR r.id=?)
               ORDER BY r.updated_at DESC LIMIT 30''',
            (int(user['id']), str(options.get('run') or ''), str(options.get('run') or '')),
        ).fetchall()
    if action == 'list':
        payload = [
            {
                'run_id': row['id'], 'party_id': row['party_id'],
                'run_status': row['status'], 'party_status': row['party_status'],
                'revision': int(row['revision']), 'seat': int(row['seat']),
                'role': row['party_role'], 'membership': row['membership_status'],
                'updated_at': row['updated_at'],
            }
            for row in rows
        ]
        return {'success': True, 'output': _format_mapping(f"{user['username']} 的协作故事旅程", payload)}
    if not rows:
        raise StoryAdminError('未找到协作故事旅程')
    row = rows[0]
    state = _parse_json(row['state_json'], '协作故事存档')
    if action == 'get':
        payload = {
            'run_id': row['id'], 'party_id': row['party_id'],
            'run_status': row['status'], 'party_status': row['party_status'],
            'revision': int(row['revision']), 'content_version': row['content_version'],
            'phase': state.get('phase'), 'stage': state.get('stage'),
            'current_floor': state.get('current_floor'),
        }
        if any(item.lower() == 'full' for item in positional[1:]):
            payload['state'] = state
        return {'success': True, 'output': _format_mapping('协作故事旅程', payload)}
    from story_coop_live import validate_coop_live_state
    try:
        validate_coop_live_state(state)
    except Exception as exc:
        code = getattr(exc, 'code', type(exc).__name__)
        message = getattr(exc, 'message', str(exc))
        if action == 'repair':
            return {'success': False, 'output': f'协作存档校验失败：{code}: {message}\n该问题没有经过证明的无损自动修复方式；命令控制台不会直接改写协作 revision、地图、投票或战斗状态。'}
        return {'success': False, 'output': f'协作存档校验失败：{code}: {message}'}
    if action == 'repair':
        return {'success': True, 'output': '协作存档校验通过，没有需要安全修复的项目。'}
    return {'success': True, 'output': '协作存档校验通过。'}


def execute_story_admin_command(parts, actor='adminconsole'):
    try:
        if not parts:
            raise StoryAdminError('用法：story <run|resource|card|relic|talent|book|jump|save|progress|discovery|content|audit|coop> ...')
        domain = str(parts[0]).lower()
        rest = list(parts[1:])
        handlers = {
            'run': lambda: _execute_run(rest, actor),
            'resource': lambda: _execute_resource(rest, actor),
            'card': lambda: _execute_card(rest, actor),
            'relic': lambda: _execute_relic(rest, actor, 'relic'),
            'talent': lambda: _execute_relic(rest, actor, 'talent'),
            'book': lambda: _execute_book(rest, actor),
            'jump': lambda: _execute_jump(rest, actor),
            'save': lambda: _execute_save(rest, actor),
            'progress': lambda: _execute_progress(rest, actor),
            'discovery': lambda: _execute_discovery(rest, actor),
            'content': lambda: _execute_content(rest),
            'audit': lambda: _execute_audit(rest, actor),
            'coop': lambda: _execute_coop(rest),
        }
        handler = handlers.get(domain)
        if handler is None:
            raise StoryAdminError(f'未知 story 子命令：{domain}')
        return handler()
    except StoryAdminError as exc:
        return {'success': False, 'output': str(exc)}
    except StoryActionError as exc:
        return {'success': False, 'output': f'{exc.code}: {exc.message}'}
