"""Persistent announcements, polls, changelog drafts, and operations audit."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

import db


COMMUNITY_CLOSED_POLL_RETENTION_DAYS = 7


class CommunityOpsError(ValueError):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)
        self.status = int(status)


def _utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _parse_timestamp(value, *, label, required=True, default=None):
    raw = str(value or '').strip()
    if not raw:
        if default is not None:
            return default
        if required:
            raise CommunityOpsError('INVALID_SCHEDULE', f'{label}不能为空')
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError as exc:
        raise CommunityOpsError('INVALID_SCHEDULE', f'{label}格式无效') from exc
    if parsed.tzinfo is None:
        raise CommunityOpsError('INVALID_SCHEDULE', f'{label}必须包含时区')
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _bounded_text(value, *, label, maximum):
    if not isinstance(value, str):
        raise CommunityOpsError('INVALID_CONTENT', f'{label}格式无效')
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise CommunityOpsError('INVALID_CONTENT', f'{label}长度必须为1-{maximum}个字符')
    return normalized


def _positive_id(value, *, label='编号'):
    if isinstance(value, bool):
        raise CommunityOpsError('INVALID_ID', f'{label}无效')
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise CommunityOpsError('INVALID_ID', f'{label}无效') from exc
    if parsed <= 0:
        raise CommunityOpsError('INVALID_ID', f'{label}无效')
    return parsed


def _actor_fields(actor):
    actor = actor if isinstance(actor, dict) else {}
    user_id = actor.get('user_id')
    if user_id not in (None, ''):
        user_id = _positive_id(user_id, label='操作账号')
    else:
        user_id = None
    username = str(actor.get('username') or 'adminconsole').strip()[:80] or 'adminconsole'
    role = str(actor.get('role_type') or 'adminconsole').strip().lower()[:32] or 'adminconsole'
    return user_id, username, role


def _insert_audit(conn, actor, action, object_type, object_id, detail=None, *, now=None):
    actor_user_id, actor_username, actor_role = _actor_fields(actor)
    created_at = _iso(now or _utc_now())
    conn.execute(
        '''
        INSERT INTO community_ops_audit(
            actor_user_id, actor_username, actor_role, action,
            object_type, object_id, detail_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            actor_user_id,
            actor_username,
            actor_role,
            str(action or '')[:64],
            str(object_type or '')[:32],
            str(object_id or '')[:80],
            json.dumps(detail or {}, ensure_ascii=False, separators=(',', ':'), sort_keys=True),
            created_at,
        ),
    )


def _announcement_payload(row):
    if row is None:
        return None
    payload = dict(row)
    payload['id'] = int(payload['id'])
    payload['pinned'] = bool(payload.get('pinned'))
    payload.pop('created_by', None)
    payload.pop('updated_by', None)
    return payload


def _effective_poll_state(row, now):
    state = str(row['state'] if isinstance(row, sqlite3.Row) else row.get('state') or '')
    if state in {'draft', 'retracted', 'closed'}:
        return state
    starts_at = _parse_timestamp(row['starts_at'], label='开始时间')
    ends_at = _parse_timestamp(row['ends_at'], label='结束时间')
    if now < starts_at:
        return 'scheduled'
    if now >= ends_at:
        return 'closed'
    return 'active'


def _poll_payload(conn, row, *, viewer_user_id=None, reveal_results=False, now=None):
    if row is None:
        return None
    now = now or _utc_now()
    poll_id = int(row['id'])
    effective_state = _effective_poll_state(row, now)
    option_rows = conn.execute(
        '''
        SELECT o.id, o.position, o.label, COUNT(v.user_id) AS vote_count
        FROM community_poll_options o
        LEFT JOIN community_poll_votes v
            ON v.poll_id = o.poll_id AND v.option_id = o.id
        WHERE o.poll_id = ?
        GROUP BY o.id, o.position, o.label
        ORDER BY o.position ASC
        ''',
        (poll_id,),
    ).fetchall()
    selected_option_id = None
    if viewer_user_id:
        selected = conn.execute(
            'SELECT option_id FROM community_poll_votes WHERE poll_id = ? AND user_id = ?',
            (poll_id, int(viewer_user_id)),
        ).fetchone()
        if selected is not None:
            selected_option_id = int(selected['option_id'])
    show_counts = bool(reveal_results or effective_state == 'closed')
    options = []
    total_votes = 0
    for option in option_rows:
        vote_count = int(option['vote_count'] or 0)
        total_votes += vote_count
        item = {
            'id': int(option['id']),
            'position': int(option['position']),
            'label': str(option['label']),
        }
        if show_counts:
            item['vote_count'] = vote_count
        options.append(item)
    ends_at = _parse_timestamp(row['ends_at'], label='结束时间')
    reminder_hours = int(row['reminder_hours'])
    reminder_due = bool(
        viewer_user_id
        and selected_option_id is None
        and effective_state == 'active'
        and ends_at - now <= timedelta(hours=reminder_hours)
    )
    payload = {
        'id': poll_id,
        'question': str(row['question']),
        'state': str(row['state']),
        'effective_state': effective_state,
        'starts_at': str(row['starts_at']),
        'ends_at': str(row['ends_at']),
        'reminder_hours': reminder_hours,
        'options': options,
        'total_votes': total_votes,
        'selected_option_id': selected_option_id,
        'reminder_due': reminder_due,
        'can_vote': bool(viewer_user_id and effective_state == 'active' and selected_option_id is None),
        'created_at': str(row['created_at']),
        'updated_at': str(row['updated_at']),
        'published_at': row['published_at'],
        'closed_at': row['closed_at'],
        'retracted_at': row['retracted_at'],
    }
    return payload


def get_community_feed(viewer_user_id=None, *, can_manage=False):
    now = _utc_now()
    now_iso = _iso(now)
    closed_cutoff = _iso(now - timedelta(days=COMMUNITY_CLOSED_POLL_RETENTION_DAYS))
    with closing(db.get_db_connection()) as conn:
        announcements = conn.execute(
            '''
            SELECT * FROM community_announcements
            WHERE state = 'published'
              AND starts_at <= ?
              AND (ends_at IS NULL OR ends_at > ?)
            ORDER BY pinned DESC, starts_at DESC, id DESC
            LIMIT 30
            ''',
            (now_iso, now_iso),
        ).fetchall()
        polls = conn.execute(
            '''
            SELECT * FROM community_polls
            WHERE (
                state = 'published' AND starts_at <= ? AND ends_at > ?
            ) OR (
                state IN ('published', 'closed') AND ends_at <= ? AND ends_at >= ?
            )
            ORDER BY starts_at DESC, id DESC
            LIMIT 20
            ''',
            (now_iso, now_iso, now_iso, closed_cutoff),
        ).fetchall()
        poll_payloads = [
            _poll_payload(conn, row, viewer_user_id=viewer_user_id, now=now)
            for row in polls
        ]
    return {
        'announcements': [_announcement_payload(row) for row in announcements],
        'polls': poll_payloads,
        'viewer': {
            'authenticated': bool(viewer_user_id),
            'can_vote': bool(viewer_user_id),
            'can_manage': bool(can_manage),
        },
        'server_time': now_iso,
    }


def get_community_poll(poll_id, viewer_user_id=None, *, reveal_results=False):
    poll_id = _positive_id(poll_id, label='投票编号')
    with closing(db.get_db_connection()) as conn:
        row = conn.execute('SELECT * FROM community_polls WHERE id = ?', (poll_id,)).fetchone()
        return _poll_payload(
            conn,
            row,
            viewer_user_id=viewer_user_id,
            reveal_results=reveal_results,
        )


def create_community_announcement(
    actor,
    *,
    title,
    body,
    starts_at=None,
    ends_at=None,
    pinned=False,
    publish=False,
    changelog_draft=False,
):
    title = _bounded_text(title, label='公告标题', maximum=120)
    body = _bounded_text(body, label='公告正文', maximum=4000)
    now = _utc_now()
    start = _parse_timestamp(starts_at, label='开始时间', default=now)
    end = _parse_timestamp(ends_at, label='结束时间', required=False)
    if end is not None and end <= start:
        raise CommunityOpsError('INVALID_SCHEDULE', '结束时间必须晚于开始时间')
    actor_user_id, _, _ = _actor_fields(actor)
    state = 'published' if publish else 'draft'
    now_iso = _iso(now)
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        cursor = conn.execute(
            '''
            INSERT INTO community_announcements(
                title, body, state, pinned, starts_at, ends_at,
                created_by, updated_by, created_at, updated_at, published_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                title,
                body,
                state,
                1 if pinned else 0,
                _iso(start),
                _iso(end) if end else None,
                actor_user_id,
                actor_user_id,
                now_iso,
                now_iso,
                now_iso if publish else None,
            ),
        )
        announcement_id = int(cursor.lastrowid)
        if changelog_draft:
            conn.execute(
                '''
                INSERT INTO community_changelog_drafts(
                    announcement_id, title, body, status, created_by, created_at, updated_at
                ) VALUES (?, ?, ?, 'pending', ?, ?, ?)
                ''',
                (announcement_id, title, body, actor_user_id, now_iso, now_iso),
            )
        _insert_audit(
            conn,
            actor,
            'announcement_create',
            'announcement',
            announcement_id,
            {
                'state': state,
                'pinned': bool(pinned),
                'starts_at': _iso(start),
                'ends_at': _iso(end) if end else None,
                'changelog_draft': bool(changelog_draft),
            },
            now=now,
        )
        row = conn.execute(
            'SELECT * FROM community_announcements WHERE id = ?',
            (announcement_id,),
        ).fetchone()
        conn.commit()
        return _announcement_payload(row)


def mutate_community_announcement(actor, announcement_id, action, *, starts_at=None, ends_at=None):
    announcement_id = _positive_id(announcement_id, label='公告编号')
    action = str(action or '').strip().lower()
    if action not in {'publish', 'schedule', 'retract', 'pin', 'unpin'}:
        raise CommunityOpsError('INVALID_ACTION', '公告操作无效')
    now = _utc_now()
    now_iso = _iso(now)
    actor_user_id, _, _ = _actor_fields(actor)
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute(
            'SELECT * FROM community_announcements WHERE id = ?',
            (announcement_id,),
        ).fetchone()
        if row is None:
            conn.rollback()
            raise CommunityOpsError('ANNOUNCEMENT_NOT_FOUND', '公告不存在', 404)
        current_state = str(row['state'])
        changed = True
        detail = {'previous_state': current_state}
        if action in {'publish', 'schedule'}:
            if current_state == 'retracted':
                conn.rollback()
                raise CommunityOpsError('INVALID_STATE', '已撤回公告不能重新发布', 409)
            if action == 'schedule' and not str(starts_at or '').strip():
                conn.rollback()
                raise CommunityOpsError('INVALID_SCHEDULE', '定时发布必须填写开始时间')
            start = _parse_timestamp(
                starts_at,
                label='开始时间',
                required=action == 'schedule',
                default=_parse_timestamp(row['starts_at'], label='开始时间'),
            )
            end = _parse_timestamp(
                ends_at if ends_at not in (None, '') else row['ends_at'],
                label='结束时间',
                required=False,
            )
            if end is not None and end <= start:
                conn.rollback()
                raise CommunityOpsError('INVALID_SCHEDULE', '结束时间必须晚于开始时间')
            conn.execute(
                '''
                UPDATE community_announcements
                SET state = 'published', starts_at = ?, ends_at = ?, updated_by = ?,
                    updated_at = ?, published_at = COALESCE(published_at, ?), retracted_at = NULL
                WHERE id = ?
                ''',
                (_iso(start), _iso(end) if end else None, actor_user_id, now_iso, now_iso, announcement_id),
            )
            detail.update({'state': 'published', 'starts_at': _iso(start), 'ends_at': _iso(end) if end else None})
        elif action == 'retract':
            changed = current_state != 'retracted'
            conn.execute(
                '''
                UPDATE community_announcements
                SET state = 'retracted', updated_by = ?, updated_at = ?, retracted_at = ?
                WHERE id = ?
                ''',
                (actor_user_id, now_iso, now_iso, announcement_id),
            )
            detail['state'] = 'retracted'
        else:
            pinned = action == 'pin'
            changed = bool(row['pinned']) != pinned
            conn.execute(
                'UPDATE community_announcements SET pinned = ?, updated_by = ?, updated_at = ? WHERE id = ?',
                (1 if pinned else 0, actor_user_id, now_iso, announcement_id),
            )
            detail['pinned'] = pinned
        if changed:
            _insert_audit(
                conn,
                actor,
                f'announcement_{action}',
                'announcement',
                announcement_id,
                detail,
                now=now,
            )
        updated = conn.execute(
            'SELECT * FROM community_announcements WHERE id = ?',
            (announcement_id,),
        ).fetchone()
        conn.commit()
        return _announcement_payload(updated), not changed


def create_community_poll(
    actor,
    *,
    question,
    options,
    starts_at=None,
    ends_at=None,
    reminder_hours=24,
    publish=False,
):
    question = _bounded_text(question, label='投票问题', maximum=240)
    if not isinstance(options, list) or not 2 <= len(options) <= 8:
        raise CommunityOpsError('INVALID_OPTIONS', '投票必须包含2-8个选项')
    labels = [_bounded_text(value, label='投票选项', maximum=160) for value in options]
    if len({label.casefold() for label in labels}) != len(labels):
        raise CommunityOpsError('INVALID_OPTIONS', '投票选项不能重复')
    if isinstance(reminder_hours, bool):
        raise CommunityOpsError('INVALID_REMINDER', '提醒窗口必须为1-168小时')
    try:
        reminder_hours = int(reminder_hours)
    except (TypeError, ValueError) as exc:
        raise CommunityOpsError('INVALID_REMINDER', '提醒窗口必须为1-168小时') from exc
    if not 1 <= reminder_hours <= 168:
        raise CommunityOpsError('INVALID_REMINDER', '提醒窗口必须为1-168小时')
    now = _utc_now()
    start = _parse_timestamp(starts_at, label='开始时间', default=now)
    end = _parse_timestamp(ends_at, label='结束时间')
    if end <= start:
        raise CommunityOpsError('INVALID_SCHEDULE', '结束时间必须晚于开始时间')
    actor_user_id, _, _ = _actor_fields(actor)
    now_iso = _iso(now)
    state = 'published' if publish else 'draft'
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        cursor = conn.execute(
            '''
            INSERT INTO community_polls(
                question, state, starts_at, ends_at, reminder_hours,
                created_by, updated_by, created_at, updated_at, published_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                question,
                state,
                _iso(start),
                _iso(end),
                reminder_hours,
                actor_user_id,
                actor_user_id,
                now_iso,
                now_iso,
                now_iso if publish else None,
            ),
        )
        poll_id = int(cursor.lastrowid)
        conn.executemany(
            'INSERT INTO community_poll_options(poll_id, position, label) VALUES (?, ?, ?)',
            [(poll_id, index, label) for index, label in enumerate(labels)],
        )
        _insert_audit(
            conn,
            actor,
            'poll_create',
            'poll',
            poll_id,
            {
                'state': state,
                'starts_at': _iso(start),
                'ends_at': _iso(end),
                'reminder_hours': reminder_hours,
                'option_count': len(labels),
            },
            now=now,
        )
        row = conn.execute('SELECT * FROM community_polls WHERE id = ?', (poll_id,)).fetchone()
        result = _poll_payload(conn, row, reveal_results=True, now=now)
        conn.commit()
        return result


def mutate_community_poll(actor, poll_id, action, *, starts_at=None, ends_at=None):
    poll_id = _positive_id(poll_id, label='投票编号')
    action = str(action or '').strip().lower()
    if action not in {'publish', 'schedule', 'close', 'retract'}:
        raise CommunityOpsError('INVALID_ACTION', '投票操作无效')
    now = _utc_now()
    now_iso = _iso(now)
    actor_user_id, _, _ = _actor_fields(actor)
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT * FROM community_polls WHERE id = ?', (poll_id,)).fetchone()
        if row is None:
            conn.rollback()
            raise CommunityOpsError('POLL_NOT_FOUND', '投票不存在', 404)
        current_state = str(row['state'])
        changed = True
        detail = {'previous_state': current_state}
        if action in {'publish', 'schedule'}:
            if current_state in {'closed', 'retracted'}:
                conn.rollback()
                raise CommunityOpsError('INVALID_STATE', '已结束或撤回的投票不能重新发布', 409)
            if action == 'schedule' and not str(starts_at or '').strip():
                conn.rollback()
                raise CommunityOpsError('INVALID_SCHEDULE', '定时发布必须填写开始时间')
            start = _parse_timestamp(
                starts_at,
                label='开始时间',
                required=action == 'schedule',
                default=_parse_timestamp(row['starts_at'], label='开始时间'),
            )
            end = _parse_timestamp(
                ends_at if ends_at not in (None, '') else row['ends_at'],
                label='结束时间',
            )
            if end <= start:
                conn.rollback()
                raise CommunityOpsError('INVALID_SCHEDULE', '结束时间必须晚于开始时间')
            conn.execute(
                '''
                UPDATE community_polls
                SET state = 'published', starts_at = ?, ends_at = ?, updated_by = ?,
                    updated_at = ?, published_at = COALESCE(published_at, ?),
                    closed_at = NULL, retracted_at = NULL
                WHERE id = ?
                ''',
                (_iso(start), _iso(end), actor_user_id, now_iso, now_iso, poll_id),
            )
            detail.update({'state': 'published', 'starts_at': _iso(start), 'ends_at': _iso(end)})
        elif action == 'close':
            if current_state == 'retracted':
                conn.rollback()
                raise CommunityOpsError('INVALID_STATE', '已撤回投票不能关闭', 409)
            changed = current_state != 'closed'
            conn.execute(
                '''
                UPDATE community_polls
                SET state = 'closed', updated_by = ?, updated_at = ?, closed_at = ?
                WHERE id = ?
                ''',
                (actor_user_id, now_iso, now_iso, poll_id),
            )
            detail['state'] = 'closed'
        else:
            changed = current_state != 'retracted'
            conn.execute(
                '''
                UPDATE community_polls
                SET state = 'retracted', updated_by = ?, updated_at = ?, retracted_at = ?
                WHERE id = ?
                ''',
                (actor_user_id, now_iso, now_iso, poll_id),
            )
            detail['state'] = 'retracted'
        if changed:
            _insert_audit(
                conn,
                actor,
                f'poll_{action}',
                'poll',
                poll_id,
                detail,
                now=now,
            )
        updated = conn.execute('SELECT * FROM community_polls WHERE id = ?', (poll_id,)).fetchone()
        result = _poll_payload(conn, updated, reveal_results=True, now=now)
        conn.commit()
        return result, not changed


def cast_community_poll_vote(user_id, poll_id, option_id):
    user_id = _positive_id(user_id, label='账号编号')
    poll_id = _positive_id(poll_id, label='投票编号')
    option_id = _positive_id(option_id, label='选项编号')
    now = _utc_now()
    now_iso = _iso(now)
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT * FROM community_polls WHERE id = ?', (poll_id,)).fetchone()
        if row is None or str(row['state']) in {'draft', 'retracted'}:
            conn.rollback()
            raise CommunityOpsError('POLL_NOT_FOUND', '投票不存在', 404)
        if _effective_poll_state(row, now) != 'active':
            conn.rollback()
            raise CommunityOpsError('POLL_NOT_ACTIVE', '投票尚未开始或已经结束', 409)
        option = conn.execute(
            'SELECT id FROM community_poll_options WHERE poll_id = ? AND id = ?',
            (poll_id, option_id),
        ).fetchone()
        if option is None:
            conn.rollback()
            raise CommunityOpsError('INVALID_OPTION', '投票选项无效')
        existing = conn.execute(
            'SELECT option_id FROM community_poll_votes WHERE poll_id = ? AND user_id = ?',
            (poll_id, user_id),
        ).fetchone()
        duplicate = False
        if existing is not None:
            if int(existing['option_id']) != option_id:
                conn.rollback()
                raise CommunityOpsError('POLL_ALREADY_VOTED', '每个账号只能选择一次，投票后不能改票', 409)
            duplicate = True
        else:
            conn.execute(
                '''
                INSERT INTO community_poll_votes(poll_id, user_id, option_id, created_at)
                VALUES (?, ?, ?, ?)
                ''',
                (poll_id, user_id, option_id, now_iso),
            )
        updated = conn.execute('SELECT * FROM community_polls WHERE id = ?', (poll_id,)).fetchone()
        result = _poll_payload(conn, updated, viewer_user_id=user_id, now=now)
        conn.commit()
        return result, duplicate


def list_community_ops_workspace(*, audit_limit=100):
    try:
        audit_limit = max(1, min(int(audit_limit), 300))
    except (TypeError, ValueError):
        audit_limit = 100
    now = _utc_now()
    with closing(db.get_db_connection()) as conn:
        announcements = conn.execute(
            'SELECT * FROM community_announcements ORDER BY id DESC LIMIT 100'
        ).fetchall()
        polls = conn.execute('SELECT * FROM community_polls ORDER BY id DESC LIMIT 100').fetchall()
        changelog = conn.execute(
            '''
            SELECT id, announcement_id, title, body, status, created_at, updated_at
            FROM community_changelog_drafts
            ORDER BY id DESC LIMIT 100
            '''
        ).fetchall()
        audit = conn.execute(
            'SELECT * FROM community_ops_audit ORDER BY id DESC LIMIT ?',
            (audit_limit,),
        ).fetchall()
        return {
            'announcements': [_announcement_payload(row) for row in announcements],
            'polls': [
                _poll_payload(conn, row, reveal_results=True, now=now)
                for row in polls
            ],
            'changelog_drafts': [dict(row) for row in changelog],
            'audit': [
                {
                    **{key: value for key, value in dict(row).items() if key != 'detail_json'},
                    'detail': json.loads(row['detail_json'] or '{}'),
                }
                for row in audit
            ],
            'server_time': _iso(now),
        }


def mutate_community_changelog_draft(actor, draft_id, action):
    draft_id = _positive_id(draft_id, label='更新日志草稿编号')
    action = str(action or '').strip().lower()
    if action != 'discard':
        raise CommunityOpsError('INVALID_ACTION', '更新日志草稿操作无效')
    now = _utc_now()
    now_iso = _iso(now)
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute(
            'SELECT * FROM community_changelog_drafts WHERE id = ?',
            (draft_id,),
        ).fetchone()
        if row is None:
            conn.rollback()
            raise CommunityOpsError('DRAFT_NOT_FOUND', '更新日志草稿不存在', 404)
        duplicate = str(row['status']) == 'discarded'
        if not duplicate:
            conn.execute(
                "UPDATE community_changelog_drafts SET status = 'discarded', updated_at = ? WHERE id = ?",
                (now_iso, draft_id),
            )
            _insert_audit(
                conn,
                actor,
                'changelog_draft_discard',
                'changelog_draft',
                draft_id,
                {'announcement_id': int(row['announcement_id'])},
                now=now,
            )
        updated = conn.execute(
            'SELECT id, announcement_id, title, body, status, created_at, updated_at '
            'FROM community_changelog_drafts WHERE id = ?',
            (draft_id,),
        ).fetchone()
        conn.commit()
        return dict(updated), duplicate
