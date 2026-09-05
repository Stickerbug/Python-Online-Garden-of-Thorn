"""Public feedback center (bug tracker and suggestion board).

The module owns issue/comment/vote/private-channel data rules.  It keeps raw
votes but computes effective vote counts against current account-link state so
confirmed/appealed/probable linked alts cannot inflate a count.  Suspected-only
pairs are never treated as the same voter.
"""

from __future__ import annotations

import sqlite3
import re
from contextlib import closing
from datetime import datetime, timedelta, timezone

import account_integrity
import db


PUBLIC_ISSUE_KINDS = {'bug', 'suggestion'}
ISSUE_KEY_PREFIXES = {'bug': 'GB', 'suggestion': 'GS'}
PUBLIC_ISSUE_LINK_RELATIONS = {'related', 'duplicates', 'fix_caused'}
PUBLIC_ISSUE_STATUSES = {
    'bug': frozenset({
        'new', 'needs_info', 'confirmed', 'in_progress',
        'fixed', 'duplicate', 'unreproducible', 'by_design', 'invalid',
    }),
    'suggestion': frozenset({
        'new', 'under_review', 'accepted', 'planned', 'rejected', 'duplicate',
    }),
}
PUBLIC_ISSUE_VOTABLE_STATUSES = {
    'bug': frozenset({'new', 'needs_info', 'confirmed', 'in_progress'}),
    'suggestion': frozenset({'new', 'under_review'}),
}
PUBLIC_ISSUE_CLOSED_STATUSES = {
    'bug': frozenset({
        'fixed', 'duplicate', 'unreproducible', 'by_design', 'invalid',
    }),
    'suggestion': frozenset({'accepted', 'planned', 'rejected', 'duplicate'}),
}
PUBLIC_ISSUE_SORTS = {'recent', 'updated', 'votes', 'priority'}
PUBLIC_ISSUE_PAGE_SIZE = 20
PUBLIC_ISSUE_MAX_PAGE_SIZE = 50

ISSUE_TITLE_MAX = 80
ISSUE_BODY_MAX = 4000
COMMENT_MAX = 1000
PRIVATE_MAX = 2000
NOTE_MAX = 2000
REASON_MAX = 500
COMMENT_EDIT_WINDOW = timedelta(minutes=5)

DELETED_SKIN = db.normalize_skin_config({'primary_color': '#8A8F98'})
CONSOLE_ACTORS = {'adminconsole', 'test-console'}


class PublicFeedbackError(ValueError):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)
        self.status = int(status)


def _utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _positive_id(value, *, label='编号'):
    if isinstance(value, bool):
        raise PublicFeedbackError('INVALID_ID', f'{label}无效')
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise PublicFeedbackError('INVALID_ID', f'{label}无效') from exc
    if parsed <= 0:
        raise PublicFeedbackError('INVALID_ID', f'{label}无效')
    return parsed


def _bounded_text(value, *, label, maximum):
    if not isinstance(value, str):
        raise PublicFeedbackError('INVALID_CONTENT', f'{label}格式无效')
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise PublicFeedbackError('INVALID_CONTENT', f'{label}长度必须为1-{maximum}个字符')
    return normalized


def _issue_row_conn(conn, issue_id, *, include_hidden=False):
    row = conn.execute('SELECT * FROM public_issues WHERE id = ?', (issue_id,)).fetchone()
    if row is None:
        raise PublicFeedbackError('ISSUE_NOT_FOUND', '问题不存在', 404)
    if not include_hidden and not bool(row['visible']):
        raise PublicFeedbackError('ISSUE_NOT_FOUND', '问题不存在', 404)
    return row


def _is_staff_conn(conn, user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return False
    if uid <= 0:
        return False
    row = conn.execute(
        'SELECT role_type, visible FROM user_roles WHERE user_id = ?',
        (uid,),
    ).fetchone()
    if row is None or not bool(row['visible']):
        return False
    return str(row['role_type'] or '').strip().lower() in {'admin', 'staff'}


def _console_allowed_actor(actor):
    if not isinstance(actor, str):
        return False
    if actor in CONSOLE_ACTORS or actor.startswith('adminconsole:'):
        return True
    return False


def _parse_staff_actor(actor):
    """Return (user_id, console_mode). Console callers use reserved id 0."""
    if _console_allowed_actor(actor):
        return 0, True
    return _positive_id(actor, label='操作者'), False


def _staff_or_console_conn(conn, actor):
    if _console_allowed_actor(actor):
        return True
    try:
        uid = int(actor)
    except (TypeError, ValueError):
        return False
    return _is_staff_conn(conn, uid)


def is_public_feedback_staff(user_id):
    with closing(db.get_db_connection()) as conn:
        return _is_staff_conn(conn, user_id)


def _deleted_author_payload(user_id):
    return {
        'id': None,
        'user_id': int(user_id),
        'username': None,
        'player_id': None,
        'deleted': True,
        'skin': dict(DELETED_SKIN),
        'role_type': 'none',
        'role_color': 'neutral',
        'equipped_titles': [],
        'name_style': None,
        'name_color': None,
    }


def _author_payload_conn(conn, user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return _deleted_author_payload(user_id)
    row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
    if uid == 0:
        return {
            'id': 0,
            'user_id': 0,
            'username': 'adminconsole',
            'player_id': None,
            'deleted': False,
            'skin': dict(DELETED_SKIN),
            'role_type': 'admin',
            'role_color': 'admin',
            'equipped_titles': [],
            'name_style': None,
            'name_color': None,
        }
    if row is None or db._user_row_is_deleted(row):
        return _deleted_author_payload(uid)
    base = db._basic_social_user(row, conn)
    user = db.row_to_user(row)
    role = conn.execute('SELECT * FROM user_roles WHERE user_id = ?', (uid,)).fetchone()
    role_type = 'none'
    role_color = db.ROLE_DEFAULTS['none']['color']
    if role is not None and bool(role['visible']):
        candidate = str(role['role_type'] or '').strip().lower()
        if candidate in db.ROLE_TYPES:
            role_type = candidate
            role_color = db.ROLE_DEFAULTS[candidate]['color']
    return {
        'id': uid,
        'user_id': uid,
        'username': str(row['username'] or ''),
        'player_id': base.get('player_id') if base else None,
        'deleted': False,
        'skin': user['skin'],
        'role_type': role_type,
        'role_color': role_color,
        'equipped_titles': list((base or {}).get('equipped_titles') or []),
        'name_style': (base or {}).get('name_style'),
        'name_color': (base or {}).get('name_color'),
    }


def _raw_voter_ids_conn(conn, issue_id):
    rows = conn.execute(
        '''
        SELECT v.user_id
        FROM public_issue_votes v
        JOIN users u ON u.id = v.user_id
        WHERE v.issue_id = ? AND v.active = 1 AND u.deleted_at IS NULL
        ORDER BY v.user_id
        ''',
        (issue_id,),
    ).fetchall()
    return [int(row['user_id']) for row in rows]


def _effective_vote_count_conn(conn, issue_id, author_user_id):
    voter_ids = _raw_voter_ids_conn(conn, issue_id)
    if not voter_ids:
        return 0
    components = account_integrity.voting_entity_components_conn(
        conn,
        voter_ids + [author_user_id],
    )
    count = 0
    for members in components:
        if int(author_user_id) in members:
            continue
        count += 1
    return count


def _own_vote_conn(conn, issue_id, user_id):
    if not user_id:
        return False
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return False
    row = conn.execute(
        '''
        SELECT active FROM public_issue_votes
        WHERE issue_id = ? AND user_id = ?
        ''',
        (issue_id, uid),
    ).fetchone()
    return bool(row and row['active'])


def _comment_count_conn(conn, issue_id):
    row = conn.execute(
        '''
        SELECT COUNT(*) AS count FROM public_issue_comments
        WHERE issue_id = ? AND hidden = 0
        ''',
        (issue_id,),
    ).fetchone()
    return int(row['count'] or 0)


def public_issue_key(kind, issue_id):
    prefix = ISSUE_KEY_PREFIXES.get(str(kind or '').strip().lower())
    if not prefix:
        raise PublicFeedbackError('INVALID_KIND', '问题类型无效')
    return f'{prefix}-{int(issue_id)}'


def _tags_conn(conn, issue_id):
    rows = conn.execute(
        '''
        SELECT tag FROM public_issue_tags
        WHERE issue_id = ? ORDER BY tag ASC
        ''',
        (issue_id,),
    ).fetchall()
    return [str(row['tag']) for row in rows]


def _watcher_count_conn(conn, issue_id):
    row = conn.execute(
        'SELECT COUNT(*) AS count FROM public_issue_watchers WHERE issue_id = ?',
        (issue_id,),
    ).fetchone()
    return int(row['count'] or 0)


def _watching_conn(conn, issue_id, user_id):
    if not user_id:
        return False
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return False
    row = conn.execute(
        '''
        SELECT 1 FROM public_issue_watchers
        WHERE issue_id = ? AND user_id = ?
        LIMIT 1
        ''',
        (issue_id, uid),
    ).fetchone()
    return bool(row)


def _issue_payload_conn(
    conn,
    row,
    *,
    viewer_user_id=None,
    include_body=True,
    include_author=True,
    excerpt_length=180,
):
    issue_id = int(row['id'])
    kind = str(row['kind'])
    payload = {
        'id': issue_id,
        'key': public_issue_key(kind, issue_id),
        'kind': kind,
        'status': str(row['status']),
        'author_user_id': int(row['author_user_id']),
        'title': str(row['title']),
        'replay_id': row['replay_id'],
        'game_version': row['game_version'] if 'game_version' in row.keys() else None,
        'fix_version': row['fix_version'] if 'fix_version' in row.keys() else None,
        'tags': _tags_conn(conn, issue_id),
        'priority': int(row['priority'] or 0),
        'pinned': bool(row['pinned']),
        'sort_order': float(row['sort_order'] or 0),
        'visible': bool(row['visible']),
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
        'status_changed_at': row['status_changed_at'],
        'closed_at': row['closed_at'],
        'comment_count': _comment_count_conn(conn, issue_id),
        'watcher_count': _watcher_count_conn(conn, issue_id),
        'vote_count': _effective_vote_count_conn(conn, issue_id, int(row['author_user_id'])),
    }
    if viewer_user_id is not None:
        payload['own_vote'] = _own_vote_conn(conn, issue_id, viewer_user_id)
        payload['watching'] = _watching_conn(conn, issue_id, viewer_user_id)
    else:
        payload['own_vote'] = False
        payload['watching'] = False
    body = str(row['body'] or '')
    if include_body:
        payload['body'] = body
    else:
        safe_excerpt = body if len(body) <= excerpt_length else body[:excerpt_length]
        payload['body_excerpt'] = safe_excerpt
    if include_author:
        payload['author'] = _author_payload_conn(conn, row['author_user_id'])
    return payload


def create_public_issue(
    author_user_id,
    *,
    kind,
    title,
    body,
    replay_id=None,
    game_version=None,
    normalized_body='',
    risk_level=0,
):
    uid = _positive_id(author_user_id, label='作者')
    kind = str(kind or '').strip().lower()
    if kind not in PUBLIC_ISSUE_KINDS:
        raise PublicFeedbackError('INVALID_KIND', '反馈类型无效')
    title = _bounded_text(title, label='标题', maximum=ISSUE_TITLE_MAX)
    body = _bounded_text(body, label='内容', maximum=ISSUE_BODY_MAX)
    if replay_id in (None, ''):
        replay_id = None
    else:
        replay_id = str(replay_id).strip()
        if len(replay_id) > 40:
            raise PublicFeedbackError('INVALID_REPLAY', '回放编号过长')
    if game_version not in (None, ''):
        game_version = str(game_version).strip()
        if len(game_version) > 80:
            raise PublicFeedbackError('INVALID_VERSION', '版本号无效')
    else:
        game_version = None
    now = _utc_now()
    now_iso = _iso(now)
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        user = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if user is None or db._user_row_is_deleted(user):
            conn.rollback()
            raise PublicFeedbackError('AUTH_REQUIRED', '请先登录账号', 401)
        cursor = conn.execute(
            '''
            INSERT INTO public_issues(
                kind, status, author_user_id, title, body, normalized_body,
                risk_level, replay_id, game_version,
                created_at, updated_at, status_changed_at
            ) VALUES (?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                kind,
                uid,
                title,
                body,
                str(normalized_body or '')[:ISSUE_BODY_MAX * 2],
                max(0, min(5, int(risk_level or 0))),
                replay_id,
                game_version,
                now_iso,
                now_iso,
                now_iso,
            ),
        )
        issue_id = int(cursor.lastrowid)
        conn.execute(
            '''
            INSERT INTO public_issue_status_history(
                issue_id, actor_user_id, from_status, to_status, reason, created_at
            ) VALUES (?, ?, NULL, 'new', NULL, ?)
            ''',
            (issue_id, uid, now_iso),
        )
        row = conn.execute('SELECT * FROM public_issues WHERE id = ?', (issue_id,)).fetchone()
        payload = _issue_payload_conn(conn, row, viewer_user_id=uid)
        conn.execute(
            'UPDATE public_issues SET author_read_at = ? WHERE id = ?',
            (now_iso, issue_id),
        )
        conn.commit()
        return payload


def _sort_sql(sort):
    sort = str(sort or 'priority').strip().lower()
    if sort not in PUBLIC_ISSUE_SORTS:
        sort = 'priority'
    if sort == 'recent':
        return 'p.created_at DESC, p.id DESC'
    if sort == 'updated':
        return 'p.updated_at DESC, p.id DESC'
    if sort == 'votes':
        return '''
            (SELECT COUNT(*) FROM public_issue_votes v
             WHERE v.issue_id = p.id AND v.active = 1) DESC,
            p.created_at DESC, p.id DESC
        '''
    return (
        'p.pinned DESC, '
        'CASE WHEN p.priority = 0 THEN 999 ELSE p.priority END ASC, '
        'p.sort_order ASC, p.created_at DESC, p.id DESC'
    )


def list_public_issues(
    viewer_user_id=None,
    *,
    kind='all',
    status='',
    search='',
    include_hidden=False,
    sort='priority',
    page=1,
    per_page=PUBLIC_ISSUE_PAGE_SIZE,
):
    kind = str(kind or 'all').strip().lower()
    if kind not in PUBLIC_ISSUE_KINDS:
        kind = 'all'
    try:
        page = max(1, int(page))
        per_page = max(1, min(int(per_page), PUBLIC_ISSUE_MAX_PAGE_SIZE))
    except (TypeError, ValueError) as exc:
        raise PublicFeedbackError('INVALID_PAGE', '分页参数无效') from exc
    where = []
    params = []
    if not include_hidden:
        where.append('p.visible = 1')
    if kind in PUBLIC_ISSUE_KINDS:
        where.append('p.kind = ?')
        params.append(kind)
    status_key = str(status or '').strip().lower()
    if status_key:
        allowed = (
            PUBLIC_ISSUE_STATUSES[kind]
            if kind in PUBLIC_ISSUE_STATUSES
            else frozenset().union(*PUBLIC_ISSUE_STATUSES.values())
        )
        if status_key not in allowed:
            raise PublicFeedbackError('INVALID_STATUS', '状态无效')
        where.append('p.status = ?')
        params.append(status_key)
    search_text = str(search or '').strip()
    if search_text:
        escaped = (
            search_text
            .replace('!', '!!')
            .replace('%', '!%')
            .replace('_', '!_')
        )
        where.append("(p.title LIKE ? ESCAPE '!' OR p.body LIKE ? ESCAPE '!')")
        params.extend([f'%{escaped}%', f'%{escaped}%'])
    where_sql = f"WHERE {' AND '.join(where)}" if where else ''
    order_sql = _sort_sql(sort)
    with closing(db.get_db_connection()) as conn:
        total_row = conn.execute(
            f'SELECT COUNT(*) AS count FROM public_issues p {where_sql}',
            params,
        ).fetchone()
        rows = conn.execute(
            f'''
            SELECT p.* FROM public_issues p
            {where_sql}
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
            ''',
            params + [per_page, (page - 1) * per_page],
        ).fetchall()
        items = [
            _issue_payload_conn(
                conn,
                row,
                viewer_user_id=viewer_user_id,
                include_body=False,
            )
            for row in rows
        ]
        if str(sort).lower() == 'votes':
            items.sort(key=lambda item: (-item['vote_count'], -int(item['id'])))
        return {
            'items': items,
            'total': int(total_row['count'] or 0),
            'page': page,
            'per_page': per_page,
            'pages': max(1, (int(total_row['count'] or 0) + per_page - 1) // per_page),
        }


def _status_history_conn(conn, issue_id):
    rows = conn.execute(
        '''
        SELECT * FROM public_issue_status_history
        WHERE issue_id = ?
        ORDER BY id ASC
        ''',
        (issue_id,),
    ).fetchall()
    return [
        {
            'id': int(row['id']),
            'from_status': row['from_status'],
            'to_status': row['to_status'],
            'reason': row['reason'],
            'created_at': row['created_at'],
            'actor': _author_payload_conn(conn, row['actor_user_id']),
        }
        for row in rows
    ]


def _comment_payload_conn(conn, row, *, viewer_user_id=None, now=None):
    now = now or _utc_now()
    comment_id = int(row['id'])
    author_id = int(row['author_user_id'])
    created_at = row['created_at']
    editable = False
    if viewer_user_id is not None:
        try:
            viewer_id = int(viewer_user_id)
        except (TypeError, ValueError):
            viewer_id = None
        if viewer_id == author_id and not bool(row['hidden']):
            try:
                created_dt = datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                editable = (now - created_dt.astimezone(timezone.utc)) <= COMMENT_EDIT_WINDOW
            except (TypeError, ValueError):
                editable = False
    return {
        'id': comment_id,
        'issue_id': int(row['issue_id']),
        'author_user_id': author_id,
        'author': _author_payload_conn(conn, author_id),
        'body': str(row['body']),
        'hidden': bool(row['hidden']),
        'created_at': created_at,
        'edited_at': row['edited_at'],
        'editable': editable,
    }


def _comment_rows_conn(conn, issue_id, *, include_hidden=False):
    rows = conn.execute(
        '''
        SELECT * FROM public_issue_comments
        WHERE issue_id = ?
        ORDER BY id ASC
        ''',
        (issue_id,),
    ).fetchall()
    if include_hidden:
        return rows
    return [row for row in rows if not bool(row['hidden'])]


def _private_messages_conn(conn, issue_id):
    rows = conn.execute(
        '''
        SELECT * FROM public_issue_private_messages
        WHERE issue_id = ?
        ORDER BY id ASC
        ''',
        (issue_id,),
    ).fetchall()
    return [
        {
            'id': int(row['id']),
            'sender_user_id': int(row['sender_user_id']),
            'sender': _author_payload_conn(conn, row['sender_user_id']),
            'message': str(row['message']),
            'created_at': row['created_at'],
        }
        for row in rows
    ]


def _staff_notes_conn(conn, issue_id):
    rows = conn.execute(
        '''
        SELECT * FROM public_issue_staff_notes
        WHERE issue_id = ?
        ORDER BY id ASC
        ''',
        (issue_id,),
    ).fetchall()
    return [
        {
            'id': int(row['id']),
            'staff_user_id': int(row['staff_user_id']),
            'staff': _author_payload_conn(conn, row['staff_user_id']),
            'note': str(row['note']),
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }
        for row in rows
    ]


def _related_issues_conn(conn, issue_id):
    rows = conn.execute(
        '''
        SELECT l.id, l.from_issue_id, l.to_issue_id, l.relation, l.note,
               o.id AS other_id, o.kind, o.status, o.title
        FROM public_issue_links l
        JOIN public_issues o ON o.id = CASE
            WHEN l.from_issue_id = ? THEN l.to_issue_id
            ELSE l.from_issue_id
        END
        WHERE l.from_issue_id = ? OR l.to_issue_id = ?
        ORDER BY l.id ASC
        ''',
        (issue_id, issue_id, issue_id),
    ).fetchall()
    return [
        {
            'link_id': int(row['id']),
            'relation': str(row['relation']),
            'note': row['note'],
            'issue': {
                'id': int(row['other_id']),
                'key': public_issue_key(row['kind'], int(row['other_id'])),
                'kind': str(row['kind']),
                'status': str(row['status']),
                'title': str(row['title']),
            },
        }
        for row in rows
    ]


def get_public_issue(
    viewer_user_id=None,
    issue_id=None,
    *,
    include_hidden=False,
):
    issue_id = _positive_id(issue_id, label='问题')
    try:
        viewer_id = int(viewer_user_id) if viewer_user_id not in (None, '') else None
    except (TypeError, ValueError):
        viewer_id = None
    with closing(db.get_db_connection()) as conn:
        row = _issue_row_conn(conn, issue_id, include_hidden=include_hidden)
        is_staff = _is_staff_conn(conn, viewer_id) if viewer_id else False
        payload = _issue_payload_conn(
            conn,
            row,
            viewer_user_id=viewer_id,
            include_body=True,
        )
        payload['status_history'] = _status_history_conn(conn, issue_id)
        payload['related_issues'] = _related_issues_conn(conn, issue_id)
        rows = _comment_rows_conn(conn, issue_id, include_hidden=is_staff and include_hidden)
        if viewer_id is None and not is_staff:
            rows = rows[:3]
        payload['comments'] = [
            _comment_payload_conn(conn, comment_row, viewer_user_id=viewer_id)
            for comment_row in rows
        ]
        payload['guest_comment_truncated'] = bool(viewer_id is None and payload['comment_count'] > 3)
        payload['can_private'] = (
            is_staff or viewer_id == int(row['author_user_id'])
        )
        payload['private_messages'] = (
            _private_messages_conn(conn, issue_id)
            if payload['can_private']
            else []
        )
        payload['staff_notes'] = _staff_notes_conn(conn, issue_id) if is_staff else []
        payload['is_staff'] = is_staff
        payload['reopen_requests'] = (
            _reopen_requests_conn(conn, issue_id)
            if is_staff
            else []
        )
        payload['not_fixed_submitted'] = False
        if viewer_id:
            submitted = conn.execute(
                '''
                SELECT 1 FROM public_issue_reopen_requests
                WHERE issue_id = ? AND user_id = ? AND status = 'pending'
                LIMIT 1
                ''',
                (issue_id, viewer_id),
            ).fetchone()
            payload['not_fixed_submitted'] = bool(submitted)
        return payload


def post_public_comment(
    author_user_id,
    issue_id,
    body,
    *,
    normalized_body='',
    risk_level=0,
):
    uid = _positive_id(author_user_id, label='作者')
    issue_id = _positive_id(issue_id, label='问题')
    body = _bounded_text(body, label='评论', maximum=COMMENT_MAX)
    now = _utc_now()
    now_iso = _iso(now)
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        issue = _issue_row_conn(conn, issue_id)
        user = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if user is None or db._user_row_is_deleted(user):
            conn.rollback()
            raise PublicFeedbackError('AUTH_REQUIRED', '请先登录账号', 401)
        cursor = conn.execute(
            '''
            INSERT INTO public_issue_comments(
                issue_id, author_user_id, body, normalized_body,
                risk_level, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                issue_id,
                uid,
                body,
                str(normalized_body or '')[:COMMENT_MAX * 2],
                max(0, min(5, int(risk_level or 0))),
                now_iso,
            ),
        )
        conn.execute(
            'UPDATE public_issues SET updated_at = ? WHERE id = ?',
            (now_iso, issue_id),
        )
        if _is_staff_conn(conn, uid):
            conn.execute(
                '''
                UPDATE public_issues
                SET staff_read_at = ?, staff_private_read_at = ?
                WHERE id = ?
                ''',
                (now_iso, now_iso, issue_id),
            )
        row = conn.execute(
            'SELECT * FROM public_issue_comments WHERE id = ?',
            (cursor.lastrowid,),
        ).fetchone()
        payload = _comment_payload_conn(conn, row, viewer_user_id=uid, now=now)
        payload['issue_kind'] = str(issue['kind'])
        payload['issue_status'] = str(issue['status'])
        conn.commit()
        return payload


def _comment_row_conn(conn, comment_id):
    row = conn.execute(
        'SELECT * FROM public_issue_comments WHERE id = ?',
        (comment_id,),
    ).fetchone()
    if row is None:
        raise PublicFeedbackError('COMMENT_NOT_FOUND', '评论不存在', 404)
    return row


def edit_public_comment(actor_user_id, comment_id, body, *, normalized_body='', risk_level=0):
    uid = _positive_id(actor_user_id, label='操作者')
    comment_id = _positive_id(comment_id, label='评论')
    body = _bounded_text(body, label='评论', maximum=COMMENT_MAX)
    now = _utc_now()
    now_iso = _iso(now)
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = _comment_row_conn(conn, comment_id)
        if int(row['author_user_id']) != uid:
            conn.rollback()
            raise PublicFeedbackError('FORBIDDEN', '只能编辑自己的评论', 403)
        if bool(row['hidden']):
            conn.rollback()
            raise PublicFeedbackError('COMMENT_HIDDEN', '评论已被删除', 404)
        try:
            created_dt = datetime.fromisoformat(str(row['created_at']).replace('Z', '+00:00'))
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            can_edit = (now - created_dt.astimezone(timezone.utc)) <= COMMENT_EDIT_WINDOW
        except (TypeError, ValueError):
            can_edit = False
        if not can_edit:
            conn.rollback()
            raise PublicFeedbackError('EDIT_EXPIRED', '评论超过5分钟，不能编辑', 409)
        conn.execute(
            '''
            UPDATE public_issue_comments
            SET body = ?, normalized_body = ?, risk_level = ?, edited_at = ?
            WHERE id = ?
            ''',
            (
                body,
                str(normalized_body or '')[:COMMENT_MAX * 2],
                max(0, min(5, int(risk_level or 0))),
                now_iso,
                comment_id,
            ),
        )
        conn.execute(
            'UPDATE public_issues SET updated_at = ? WHERE id = ?',
            (now_iso, int(row['issue_id'])),
        )
        updated = conn.execute(
            'SELECT * FROM public_issue_comments WHERE id = ?',
            (comment_id,),
        ).fetchone()
        payload = _comment_payload_conn(conn, updated, viewer_user_id=uid, now=now)
        conn.commit()
        return payload


def remove_public_comment(actor_user_id, comment_id):
    uid = _positive_id(actor_user_id, label='操作者')
    comment_id = _positive_id(comment_id, label='评论')
    now = _utc_now()
    now_iso = _iso(now)
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = _comment_row_conn(conn, comment_id)
        is_staff = _is_staff_conn(conn, uid)
        if not is_staff and int(row['author_user_id']) != uid:
            conn.rollback()
            raise PublicFeedbackError('FORBIDDEN', '只能删除自己的评论', 403)
        if not is_staff and bool(row['hidden']):
            conn.rollback()
            raise PublicFeedbackError('COMMENT_HIDDEN', '评论已删除', 404)
        if not is_staff:
            try:
                created_dt = datetime.fromisoformat(str(row['created_at']).replace('Z', '+00:00'))
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                can_delete = (now - created_dt.astimezone(timezone.utc)) <= COMMENT_EDIT_WINDOW
            except (TypeError, ValueError):
                can_delete = False
            if not can_delete:
                conn.rollback()
                raise PublicFeedbackError('DELETE_EXPIRED', '评论超过5分钟，不能删除', 409)
        conn.execute(
            '''
            UPDATE public_issue_comments
            SET hidden = 1, hidden_by_user_id = ?, hidden_at = ?
            WHERE id = ?
            ''',
            (uid, now_iso, comment_id),
        )
        conn.execute(
            'UPDATE public_issues SET updated_at = ? WHERE id = ?',
            (now_iso, int(row['issue_id'])),
        )
        conn.commit()
        return {'deleted': True, 'comment_id': comment_id}


def toggle_public_vote(actor_user_id, issue_id):
    uid = _positive_id(actor_user_id, label='投票者')
    issue_id = _positive_id(issue_id, label='问题')
    now = _utc_now()
    now_iso = _iso(now)
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        issue = _issue_row_conn(conn, issue_id)
        kind = str(issue['kind'])
        status = str(issue['status'])
        author_id = int(issue['author_user_id'])
        user = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if user is None or db._user_row_is_deleted(user):
            conn.rollback()
            raise PublicFeedbackError('AUTH_REQUIRED', '请先登录账号', 401)
        existing = conn.execute(
            'SELECT * FROM public_issue_votes WHERE issue_id = ? AND user_id = ?',
            (issue_id, uid),
        ).fetchone()
        if existing and bool(existing['active']):
            conn.execute(
                '''
                UPDATE public_issue_votes
                SET active = 0, updated_at = ?
                WHERE issue_id = ? AND user_id = ?
                ''',
                (now_iso, issue_id, uid),
            )
            conn.execute(
                '''
                INSERT INTO public_issue_vote_events(
                    issue_id, user_id, action, reason_code, actor_user_id, created_at
                ) VALUES (?, ?, 'remove', NULL, ?, ?)
                ''',
                (issue_id, uid, uid, now_iso),
            )
            conn.commit()
            return {
                'voted': False,
                'vote_count': _effective_vote_count_conn(conn, issue_id, author_id),
            }
        if status not in PUBLIC_ISSUE_VOTABLE_STATUSES[kind]:
            conn.rollback()
            raise PublicFeedbackError('VOTE_CLOSED', '该问题已结束投票', 409)
        if uid == author_id:
            conn.rollback()
            raise PublicFeedbackError('AUTHOR_VOTE_FORBIDDEN', '不能给自己的问题投票', 409)
        voter_ids = _raw_voter_ids_conn(conn, issue_id)
        components = account_integrity.voting_entity_components_conn(
            conn,
            [uid] + voter_ids + [author_id],
        )
        own_component = next(
            (component for component in components if uid in component),
            [uid],
        )
        linked_voter = any(other in voter_ids for other in own_component)
        linked_author = int(author_id) in own_component
        if linked_author:
            reason_code = 'author_group'
        elif linked_voter:
            reason_code = 'linked_voter'
        else:
            reason_code = None
        if reason_code is not None:
            conn.execute(
                '''
                INSERT INTO public_issue_vote_events(
                    issue_id, user_id, action, reason_code, actor_user_id, created_at
                ) VALUES (?, ?, 'blocked', ?, ?, ?)
                ''',
                (issue_id, uid, reason_code, uid, now_iso),
            )
            conn.commit()
            raise PublicFeedbackError(
                'VOTE_LINKED_GROUP',
                '同组账号已投票或与提交者属于同一组，不能重复投票',
                409,
            )
        if existing is None:
            conn.execute(
                '''
                INSERT INTO public_issue_votes(
                    issue_id, user_id, active, created_at, updated_at
                ) VALUES (?, ?, 1, ?, ?)
                ''',
                (issue_id, uid, now_iso, now_iso),
            )
        else:
            conn.execute(
                '''
                UPDATE public_issue_votes
                SET active = 1, updated_at = ?, invalidated_by = NULL, invalidated_at = NULL
                WHERE issue_id = ? AND user_id = ?
                ''',
                (now_iso, issue_id, uid),
            )
        conn.execute(
            '''
            INSERT INTO public_issue_vote_events(
                issue_id, user_id, action, reason_code, actor_user_id, created_at
            ) VALUES (?, ?, 'add', NULL, ?, ?)
            ''',
            (issue_id, uid, uid, now_iso),
        )
        conn.commit()
        return {
            'voted': True,
            'vote_count': _effective_vote_count_conn(conn, issue_id, author_id),
        }


def invalidate_public_vote(staff_user_id, issue_id, target_user_id, *, restore=False):
    staff_id, _ = _parse_staff_actor(staff_user_id)
    issue_id = _positive_id(issue_id, label='问题')
    target_id = _positive_id(target_user_id, label='投票账号')
    now_iso = _iso(_utc_now())
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if not _staff_or_console_conn(conn, staff_user_id):
            conn.rollback()
            raise PublicFeedbackError('FORBIDDEN', '权限不足', 403)
        _issue_row_conn(conn, issue_id)
        row = conn.execute(
            'SELECT * FROM public_issue_votes WHERE issue_id = ? AND user_id = ?',
            (issue_id, target_id),
        ).fetchone()
        if row is None:
            conn.rollback()
            raise PublicFeedbackError('VOTE_NOT_FOUND', '该账号没有投过票', 404)
        if restore:
            if not bool(row['active']):
                conn.execute(
                    '''
                    UPDATE public_issue_votes
                    SET active = 1, updated_at = ?, invalidated_by = NULL, invalidated_at = NULL
                    WHERE issue_id = ? AND user_id = ?
                    ''',
                    (now_iso, issue_id, target_id),
                )
                conn.execute(
                    '''
                    INSERT INTO public_issue_vote_events(
                        issue_id, user_id, action, reason_code, actor_user_id, created_at
                    ) VALUES (?, ?, 'restore', 'staff', ?, ?)
                    ''',
                    (issue_id, target_id, staff_id, now_iso),
                )
            conn.commit()
            return {'restored': True}
        if bool(row['active']):
            conn.execute(
                '''
                UPDATE public_issue_votes
                SET active = 0, updated_at = ?, invalidated_by = ?, invalidated_at = ?
                WHERE issue_id = ? AND user_id = ?
                ''',
                (now_iso, staff_id, now_iso, issue_id, target_id),
            )
            conn.execute(
                '''
                INSERT INTO public_issue_vote_events(
                    issue_id, user_id, action, reason_code, actor_user_id, created_at
                ) VALUES (?, ?, 'invalidate', 'staff', ?, ?)
                ''',
                (issue_id, target_id, staff_id, now_iso),
            )
        conn.commit()
        return {'invalidated': True}


def toggle_public_watch(user_id, issue_id):
    uid = _positive_id(user_id, label='关注者')
    issue_id = _positive_id(issue_id, label='问题')
    now_iso = _iso(_utc_now())
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        _issue_row_conn(conn, issue_id)
        row = conn.execute(
            'SELECT * FROM public_issue_watchers WHERE issue_id = ? AND user_id = ?',
            (issue_id, uid),
        ).fetchone()
        if row:
            conn.execute(
                'DELETE FROM public_issue_watchers WHERE issue_id = ? AND user_id = ?',
                (issue_id, uid),
            )
            watching = False
        else:
            conn.execute(
                '''
                INSERT INTO public_issue_watchers(issue_id, user_id, created_at, last_seen_at)
                VALUES (?, ?, ?, ?)
                ''',
                (issue_id, uid, now_iso, now_iso),
            )
            watching = True
        conn.commit()
        return {
            'watching': watching,
            'watcher_count': _watcher_count_conn(conn, issue_id),
        }


def set_public_issue_tags(staff_user_id, issue_id, tags):
    staff_id, _ = _parse_staff_actor(staff_user_id)
    issue_id = _positive_id(issue_id, label='问题')
    if not isinstance(tags, list) or len(tags) > 12:
        raise PublicFeedbackError('INVALID_TAGS', '标签数量最多12个')
    cleaned = []
    for value in tags:
        tag = str(value or '').strip()
        if not tag or len(tag) > 32 or any(ch.isspace() for ch in tag):
            raise PublicFeedbackError('INVALID_TAG', '标签不能为空、超过32字或包含空格')
        if tag not in cleaned:
            cleaned.append(tag)
    now_iso = _iso(_utc_now())
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if not _staff_or_console_conn(conn, staff_user_id):
            conn.rollback()
            raise PublicFeedbackError('FORBIDDEN', '权限不足', 403)
        _issue_row_conn(conn, issue_id)
        conn.execute('DELETE FROM public_issue_tags WHERE issue_id = ?', (issue_id,))
        conn.executemany(
            'INSERT INTO public_issue_tags(issue_id, tag) VALUES (?, ?)',
            [(issue_id, tag) for tag in cleaned],
        )
        conn.execute(
            'UPDATE public_issues SET updated_at = ? WHERE id = ?',
            (now_iso, issue_id),
        )
        conn.commit()
        return {'issue_id': issue_id, 'tags': _tags_conn(conn, issue_id)}


def link_public_issues(
    staff_user_id,
    from_issue_id,
    to_issue_id,
    relation='related',
    note='',
):
    staff_id, _ = _parse_staff_actor(staff_user_id)
    from_id = _positive_id(from_issue_id, label='来源问题')
    to_id = _positive_id(to_issue_id, label='目标问题')
    relation = str(relation or '').strip().lower()
    if relation not in PUBLIC_ISSUE_LINK_RELATIONS:
        raise PublicFeedbackError('INVALID_RELATION', '关联类型无效')
    if from_id == to_id:
        raise PublicFeedbackError('INVALID_LINK', '不能关联问题自身')
    note = str(note or '').strip()[:300]
    now_iso = _iso(_utc_now())
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if not _staff_or_console_conn(conn, staff_user_id):
            conn.rollback()
            raise PublicFeedbackError('FORBIDDEN', '权限不足', 403)
        _issue_row_conn(conn, from_id, include_hidden=True)
        _issue_row_conn(conn, to_id, include_hidden=True)
        cursor = conn.execute(
            '''
            INSERT INTO public_issue_links(
                from_issue_id, to_issue_id, relation, note,
                created_by_user_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (from_id, to_id, relation, note or None, staff_id or None, now_iso),
        )
        conn.commit()
        return {'link_id': int(cursor.lastrowid), 'from_issue_id': from_id, 'to_issue_id': to_id}


def unlink_public_issue(staff_user_id, link_id):
    staff_id, _ = _parse_staff_actor(staff_user_id)
    link_id = _positive_id(link_id, label='关联')
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if not _staff_or_console_conn(conn, staff_user_id):
            conn.rollback()
            raise PublicFeedbackError('FORBIDDEN', '权限不足', 403)
        cursor = conn.execute(
            'DELETE FROM public_issue_links WHERE id = ?',
            (link_id,),
        )
        if cursor.rowcount == 0:
            conn.rollback()
            raise PublicFeedbackError('LINK_NOT_FOUND', '关联不存在', 404)
        conn.commit()
        return {'removed': True, 'link_id': link_id}


def submit_public_reopen_request(
    user_id,
    issue_id,
    message,
    *,
    replay_id=None,
):
    uid = _positive_id(user_id, label='提交者')
    issue_id = _positive_id(issue_id, label='问题')
    message = _bounded_text(message, label='说明', maximum=1000)
    if replay_id not in (None, ''):
        replay_id = str(replay_id).strip()
        if len(replay_id) > 40:
            raise PublicFeedbackError('INVALID_REPLAY', '回放编号无效')
    else:
        replay_id = None
    now_iso = _iso(_utc_now())
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        issue = _issue_row_conn(conn, issue_id)
        if issue['kind'] != 'bug' or issue['status'] != 'fixed':
            conn.rollback()
            raise PublicFeedbackError('NOT_FIXED_AVAILABLE', '只有已修复的漏洞可以提交“仍未修复”', 409)
        user = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        if user is None or db._user_row_is_deleted(user):
            conn.rollback()
            raise PublicFeedbackError('AUTH_REQUIRED', '请先登录账号', 401)
        pending = conn.execute(
            '''
            SELECT id FROM public_issue_reopen_requests
            WHERE issue_id = ? AND user_id = ? AND status = 'pending'
            LIMIT 1
            ''',
            (issue_id, uid),
        ).fetchone()
        if pending:
            conn.rollback()
            raise PublicFeedbackError('DUPLICATE_REOPEN', '你已提交过“仍未修复”，请等待处理', 409)
        cursor = conn.execute(
            '''
            INSERT INTO public_issue_reopen_requests(
                issue_id, user_id, message, replay_id, status, created_at
            ) VALUES (?, ?, ?, ?, 'pending', ?)
            ''',
            (issue_id, uid, message, replay_id, now_iso),
        )
        conn.commit()
        return {
            'id': int(cursor.lastrowid),
            'issue_id': issue_id,
            'user_id': uid,
            'status': 'pending',
            'created_at': now_iso,
        }


def _reopen_requests_conn(conn, issue_id):
    rows = conn.execute(
        '''
        SELECT * FROM public_issue_reopen_requests
        WHERE issue_id = ? ORDER BY id DESC
        ''',
        (issue_id,),
    ).fetchall()
    return [
        {
            'id': int(row['id']),
            'issue_id': int(row['issue_id']),
            'user_id': int(row['user_id']),
            'author': _author_payload_conn(conn, row['user_id']),
            'message': str(row['message']),
            'replay_id': row['replay_id'],
            'status': str(row['status']),
            'created_at': row['created_at'],
            'reviewed_by_user_id': row['reviewed_by_user_id'],
            'reviewed_at': row['reviewed_at'],
            'review_note': row['review_note'],
        }
        for row in rows
    ]


def review_public_reopen_request(
    staff_user_id,
    request_id,
    action,
    *,
    reason='',
    reopen_status='confirmed',
):
    staff_id, _ = _parse_staff_actor(staff_user_id)
    request_id = _positive_id(request_id, label='请求')
    action = str(action or '').strip().lower()
    if action not in ('accept', 'reject'):
        raise PublicFeedbackError('INVALID_REVIEW', '处理动作无效')
    reason = str(reason or '').strip()[:500]
    now_iso = _iso(_utc_now())
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if not _staff_or_console_conn(conn, staff_user_id):
            conn.rollback()
            raise PublicFeedbackError('FORBIDDEN', '权限不足', 403)
        request = conn.execute(
            '''
            SELECT * FROM public_issue_reopen_requests WHERE id = ?
            ''',
            (request_id,),
        ).fetchone()
        if request is None:
            conn.rollback()
            raise PublicFeedbackError('REOPEN_NOT_FOUND', '请求不存在', 404)
        if request['status'] != 'pending':
            conn.rollback()
            raise PublicFeedbackError('REOPEN_CLOSED', '请求已经处理', 409)
        issue = _issue_row_conn(conn, int(request['issue_id']))
        if action == 'accept':
            if issue['kind'] != 'bug':
                conn.rollback()
                raise PublicFeedbackError('INVALID_REOPEN', '建议不支持重新开启', 400)
            if reopen_status not in ('needs_info', 'confirmed'):
                reopen_status = 'confirmed'
            old_status = str(issue['status'])
            closed_at = None
            conn.execute(
                '''
                UPDATE public_issues
                SET status = ?, status_changed_at = ?, closed_at = NULL, updated_at = ?
                WHERE id = ?
                ''',
                (reopen_status, now_iso, now_iso, int(request['issue_id'])),
            )
            conn.execute(
                '''
                INSERT INTO public_issue_status_history(
                    issue_id, actor_user_id, from_status, to_status, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    int(request['issue_id']),
                    staff_id or 0,
                    old_status,
                    reopen_status,
                    f'重新开启：{reason or request["message"][:120]}',
                    now_iso,
                ),
            )
        conn.execute(
            '''
            UPDATE public_issue_reopen_requests
            SET status = ?, reviewed_by_user_id = ?, reviewed_at = ?, review_note = ?
            WHERE id = ?
            ''',
            (
                'accepted' if action == 'accept' else 'rejected',
                staff_id or 0,
                now_iso,
                reason or None,
                request_id,
            ),
        )
        conn.commit()
        return {
            'request_id': request_id,
            'status': 'accepted' if action == 'accept' else 'rejected',
            'issue_id': int(request['issue_id']),
        }


def set_public_issue_fix_version(staff_user_id, issue_id, fix_version=''):
    staff_id, _ = _parse_staff_actor(staff_user_id)
    issue_id = _positive_id(issue_id, label='问题')
    fix_version = str(fix_version or '').strip()
    if len(fix_version) > 80:
        raise PublicFeedbackError('INVALID_VERSION', '修复版本号无效')
    now_iso = _iso(_utc_now())
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if not _staff_or_console_conn(conn, staff_user_id):
            conn.rollback()
            raise PublicFeedbackError('FORBIDDEN', '权限不足', 403)
        _issue_row_conn(conn, issue_id, include_hidden=True)
        conn.execute(
            '''
            UPDATE public_issues SET fix_version = ?, updated_at = ?
            WHERE id = ?
            ''',
            (fix_version or None, now_iso, issue_id),
        )
        conn.commit()
        return {'issue_id': issue_id, 'fix_version': fix_version or None}


def _public_version_rank(version):
    text = str(version or '').strip()
    match = re.fullmatch(r'(\d{4}-\d{2}-\d{2})(?:-(\d+))?', text)
    if not match:
        return None
    base = tuple(int(part) for part in match.group(1).split('-'))
    return base + (int(match.group(2) or 1),)


def finalize_public_release_fixes(public_version):
    public_version = str(public_version or '').strip()
    rank = _public_version_rank(public_version)
    if not rank:
        return {'changed': 0, 'reason': 'non_public_version'}
    now_iso = _iso(_utc_now())
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        state = conn.execute(
            'SELECT last_version FROM public_release_states WHERE id = 1'
        ).fetchone()
        last_version = state['last_version'] if state else None
        if public_version == last_version:
            conn.rollback()
            return {'changed': 0, 'reason': 'already_finalized'}
        last_rank = _public_version_rank(last_version) if last_version else None
        if last_rank is not None and rank < last_rank:
            conn.rollback()
            return {'changed': 0, 'reason': 'rollback_ignored'}
        cursor = conn.execute(
            '''
            UPDATE public_issues
            SET status = 'fixed', status_changed_at = ?, closed_at = ?,
                fix_version = ?, updated_at = ?
            WHERE kind = 'bug' AND status = 'in_progress' AND visible = 1
            ''',
            (now_iso, now_iso, public_version, now_iso),
        )
        changed = int(cursor.rowcount or 0)
        if changed:
            rows = conn.execute(
                '''
                SELECT id FROM public_issues
                WHERE kind = 'bug' AND fix_version = ? AND status = 'fixed'
                  AND status_changed_at = ?
                ''',
                (public_version, now_iso),
            ).fetchall()
            for row in rows:
                conn.execute(
                    '''
                    INSERT INTO public_issue_status_history(
                        issue_id, actor_user_id, from_status, to_status,
                        reason, created_at
                    ) VALUES (?, 0, 'in_progress', 'fixed', ?, ?)
                    ''',
                    (int(row['id']), f'随版本 {public_version} 发布自动修复', now_iso),
                )
        conn.execute(
            '''
            INSERT INTO public_release_states(id, last_version, last_finalized_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                last_version = excluded.last_version,
                last_finalized_at = excluded.last_finalized_at
            ''',
            (public_version, now_iso),
        )
        conn.commit()
        return {'changed': changed, 'version': public_version}


def _send_private_message(
    actor_user_id,
    issue_id,
    message,
    *,
    normalized_message='',
    risk_level=0,
    kind,
):
    uid = _positive_id(actor_user_id, label='发送者')
    issue_id = _positive_id(issue_id, label='问题')
    message = _bounded_text(message, label='私密补充', maximum=PRIVATE_MAX)
    now = _utc_now()
    now_iso = _iso(now)
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        issue = _issue_row_conn(conn, issue_id)
        is_staff = _is_staff_conn(conn, uid)
        if not is_staff and int(issue['author_user_id']) != uid:
            conn.rollback()
            raise PublicFeedbackError('FORBIDDEN', '只有作者或 Staff 可查看此区', 403)
        cursor = conn.execute(
            '''
            INSERT INTO public_issue_private_messages(
                issue_id, sender_user_id, message, normalized_message,
                risk_level, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                issue_id,
                uid,
                message,
                str(normalized_message or '')[:PRIVATE_MAX * 2],
                max(0, min(5, int(risk_level or 0))),
                now_iso,
            ),
        )
        conn.execute(
            'UPDATE public_issues SET updated_at = ? WHERE id = ?',
            (now_iso, issue_id),
        )
        if is_staff:
            conn.execute(
                '''
                UPDATE public_issues
                SET staff_read_at = ?, staff_private_read_at = ?
                WHERE id = ?
                ''',
                (now_iso, now_iso, issue_id),
            )
        else:
            conn.execute(
                '''
                UPDATE public_issues
                SET author_read_at = ?, author_private_read_at = ?
                WHERE id = ?
                ''',
                (now_iso, now_iso, issue_id),
            )
        row = conn.execute(
            'SELECT * FROM public_issue_private_messages WHERE id = ?',
            (cursor.lastrowid,),
        ).fetchone()
        conn.commit()
        return {
            'id': int(row['id']),
            'issue_id': issue_id,
            'sender_user_id': uid,
            'sender': _author_payload_conn(conn, uid),
            'message': str(row['message']),
            'created_at': row['created_at'],
            'kind': kind,
        }


def send_public_issue_private(actor_user_id, issue_id, message, *, normalized_message='', risk_level=0):
    with closing(db.get_db_connection()) as conn:
        issue = _issue_row_conn(conn, issue_id)
        kind = str(issue['kind'])
    return _send_private_message(
        actor_user_id,
        issue_id,
        message,
        normalized_message=normalized_message,
        risk_level=risk_level,
        kind=kind,
    )


def list_public_issue_private(viewer_user_id, issue_id):
    uid = _positive_id(viewer_user_id, label='查看者')
    issue_id = _positive_id(issue_id, label='问题')
    with closing(db.get_db_connection()) as conn:
        issue = _issue_row_conn(conn, issue_id)
        is_staff = _is_staff_conn(conn, uid)
        if not is_staff and int(issue['author_user_id']) != uid:
            raise PublicFeedbackError('FORBIDDEN', '只有作者或 Staff 可查看此区', 403)
        now_iso = _iso(_utc_now())
        if is_staff:
            conn.execute(
                '''
                UPDATE public_issues
                SET staff_read_at = ?, staff_private_read_at = ?
                WHERE id = ?
                ''',
                (now_iso, now_iso, issue_id),
            )
        else:
            conn.execute(
                '''
                UPDATE public_issues
                SET author_read_at = ?, author_private_read_at = ?
                WHERE id = ?
                ''',
                (now_iso, now_iso, issue_id),
            )
        messages = _private_messages_conn(conn, issue_id)
        conn.commit()
        return {'issue_id': issue_id, 'messages': messages}


def _add_staff_note(actor_user_id, issue_id, note):
    uid, _ = _parse_staff_actor(actor_user_id)
    issue_id = _positive_id(issue_id, label='问题')
    note = _bounded_text(note, label='内部备注', maximum=NOTE_MAX)
    now_iso = _iso(_utc_now())
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if not _staff_or_console_conn(conn, actor_user_id):
            conn.rollback()
            raise PublicFeedbackError('FORBIDDEN', '权限不足', 403)
        _issue_row_conn(conn, issue_id)
        cursor = conn.execute(
            '''
            INSERT INTO public_issue_staff_notes(
                issue_id, staff_user_id, note, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            ''',
            (issue_id, uid, note, now_iso, now_iso),
        )
        row = conn.execute(
            'SELECT * FROM public_issue_staff_notes WHERE id = ?',
            (cursor.lastrowid,),
        ).fetchone()
        conn.commit()
        return {
            'id': int(row['id']),
            'issue_id': issue_id,
            'staff_user_id': uid,
            'staff': _author_payload_conn(conn, uid),
            'note': str(row['note']),
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }


def set_public_issue_status(staff_user_id, issue_id, status, reason=''):
    staff_id, _ = _parse_staff_actor(staff_user_id)
    issue_id = _positive_id(issue_id, label='问题')
    target_status = str(status or '').strip().lower()
    if reason not in (None, ''):
        reason = _bounded_text(reason, label='公开原因', maximum=REASON_MAX)
    else:
        reason = ''
    now = _utc_now()
    now_iso = _iso(now)
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if not _staff_or_console_conn(conn, staff_user_id):
            conn.rollback()
            raise PublicFeedbackError('FORBIDDEN', '权限不足', 403)
        issue = _issue_row_conn(conn, issue_id)
        kind = str(issue['kind'])
        if target_status not in PUBLIC_ISSUE_STATUSES[kind]:
            conn.rollback()
            raise PublicFeedbackError('INVALID_STATUS', '该类型不支持此状态', 400)
        old_status = str(issue['status'])
        closed_at = None
        if target_status in PUBLIC_ISSUE_CLOSED_STATUSES[kind]:
            closed_at = now_iso
        conn.execute(
            '''
            UPDATE public_issues
            SET status = ?, status_changed_at = ?, closed_at = ?, updated_at = ?
            WHERE id = ?
            ''',
            (target_status, now_iso, closed_at, now_iso, issue_id),
        )
        conn.execute(
            '''
            INSERT INTO public_issue_status_history(
                issue_id, actor_user_id, from_status, to_status, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (issue_id, staff_id, old_status, target_status, reason or None, now_iso),
        )
        updated = conn.execute(
            'SELECT * FROM public_issues WHERE id = ?',
            (issue_id,),
        ).fetchone()
        conn.commit()
        return _issue_payload_conn(conn, updated, viewer_user_id=None)


def set_public_issue_priority(staff_user_id, issue_id, *, priority=None, pinned=None, sort_order=None):
    staff_id, _ = _parse_staff_actor(staff_user_id)
    issue_id = _positive_id(issue_id, label='问题')
    if priority is not None:
        if isinstance(priority, bool) or not 0 <= int(priority) <= 5:
            raise PublicFeedbackError('INVALID_PRIORITY', '优先级必须为0-5')
        priority = int(priority)
    if pinned is not None:
        pinned = 1 if bool(pinned) else 0
    if sort_order is not None:
        try:
            sort_order = float(sort_order)
        except (TypeError, ValueError) as exc:
            raise PublicFeedbackError('INVALID_ORDER', '排序值无效') from exc
        if not -1e9 <= sort_order <= 1e9:
            raise PublicFeedbackError('INVALID_ORDER', '排序值超出范围')
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if not _staff_or_console_conn(conn, staff_user_id):
            conn.rollback()
            raise PublicFeedbackError('FORBIDDEN', '权限不足', 403)
        issue = _issue_row_conn(conn, issue_id)
        conn.execute(
            '''
            UPDATE public_issues SET
                priority = COALESCE(?, priority),
                pinned = COALESCE(?, pinned),
                sort_order = COALESCE(?, sort_order),
                updated_at = ?
            WHERE id = ?
            ''',
            (
                priority if priority is not None else issue['priority'],
                pinned if pinned is not None else issue['pinned'],
                sort_order if sort_order is not None else issue['sort_order'],
                _iso(_utc_now()),
                issue_id,
            ),
        )
        updated = conn.execute(
            'SELECT * FROM public_issues WHERE id = ?',
            (issue_id,),
        ).fetchone()
        conn.commit()
        return _issue_payload_conn(conn, updated, viewer_user_id=staff_id or None)


def hide_public_issue(staff_user_id, issue_id, *, hidden=True):
    staff_id, _ = _parse_staff_actor(staff_user_id)
    issue_id = _positive_id(issue_id, label='问题')
    now_iso = _iso(_utc_now())
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if not _staff_or_console_conn(conn, staff_user_id):
            conn.rollback()
            raise PublicFeedbackError('FORBIDDEN', '权限不足', 403)
        _issue_row_conn(conn, issue_id, include_hidden=True)
        conn.execute(
            '''
            UPDATE public_issues SET visible = ?, updated_at = ?
            WHERE id = ?
            ''',
            (1 if not hidden else 0, now_iso, issue_id),
        )
        conn.commit()
        return {'issue_id': issue_id, 'hidden': bool(hidden)}


def hide_public_comment(staff_user_id, comment_id, *, hidden=True):
    staff_id, _ = _parse_staff_actor(staff_user_id)
    comment_id = _positive_id(comment_id, label='评论')
    now_iso = _iso(_utc_now())
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if not _staff_or_console_conn(conn, staff_user_id):
            conn.rollback()
            raise PublicFeedbackError('FORBIDDEN', '权限不足', 403)
        row = _comment_row_conn(conn, comment_id)
        conn.execute(
            '''
            UPDATE public_issue_comments
            SET hidden = ?, hidden_by_user_id = ?, hidden_at = ?
            WHERE id = ?
            ''',
            (1 if hidden else 0, staff_id if hidden else None, now_iso if hidden else None, comment_id),
        )
        conn.execute(
            'UPDATE public_issues SET updated_at = ? WHERE id = ?',
            (now_iso, int(row['issue_id'])),
        )
        conn.commit()
        return {'comment_id': comment_id, 'hidden': bool(hidden)}


def public_feedback_author_unread_count(user_id):
    uid = _positive_id(user_id, label='作者')
    with closing(db.get_db_connection()) as conn:
        rows = conn.execute(
            '''
            SELECT i.id, i.author_read_at
            FROM public_issues i
            WHERE i.author_user_id = ? AND i.visible = 1
            ''',
            (uid,),
        ).fetchall()
        count = 0
        for row in rows:
            issue_id = int(row['id'])
            read_at = row['author_read_at']
            status_unread = conn.execute(
                '''
                SELECT 1 FROM public_issue_status_history
                WHERE issue_id = ?
                  AND (? IS NULL OR created_at > ?)
                LIMIT 1
                ''',
                (issue_id, read_at, read_at),
            ).fetchone()
            if status_unread:
                count += 1
                continue
            private_unread = conn.execute(
                '''
                SELECT 1 FROM public_issue_private_messages
                WHERE issue_id = ? AND sender_user_id <> ?
                  AND (? IS NULL OR created_at > ?)
                LIMIT 1
                ''',
                (issue_id, uid, read_at, read_at),
            ).fetchone()
            if private_unread:
                count += 1
        return count


def public_feedback_staff_unread_count():
    with closing(db.get_db_connection()) as conn:
        rows = conn.execute(
            '''
            SELECT i.id, i.staff_read_at
            FROM public_issues i
            WHERE i.visible = 1
            ''',
        ).fetchall()
        count = 0
        for row in rows:
            issue_id = int(row['id'])
            read_at = row['staff_read_at']
            if read_at is None:
                count += 1
                continue
            activity = conn.execute(
                '''
                SELECT 1
                FROM (
                    SELECT created_at AS ts FROM public_issue_comments
                    WHERE issue_id = ? AND hidden = 0
                    UNION ALL
                    SELECT created_at FROM public_issue_private_messages
                    WHERE issue_id = ?
                    UNION ALL
                    SELECT created_at FROM public_issue_status_history
                    WHERE issue_id = ?
                ) events
                WHERE ts > ?
                LIMIT 1
                ''',
                (issue_id, issue_id, issue_id, read_at),
            ).fetchone()
            if activity:
                count += 1
        pending_reopens = conn.execute(
            '''
            SELECT COUNT(DISTINCT issue_id) AS count
            FROM public_issue_reopen_requests
            WHERE status = 'pending'
            '''
        ).fetchone()
        count += int(pending_reopens['count'] or 0)
        return count


def public_feedback_watcher_unread_count(user_id):
    uid = _positive_id(user_id, label='关注者')
    with closing(db.get_db_connection()) as conn:
        row = conn.execute(
            '''
            SELECT COUNT(DISTINCT i.id) AS count
            FROM public_issue_watchers w
            JOIN public_issues i ON i.id = w.issue_id AND i.visible = 1
            WHERE w.user_id = ?
              AND EXISTS (
                  SELECT 1 FROM public_issue_status_history h
                  WHERE h.issue_id = w.issue_id
                    AND h.created_at > COALESCE(w.last_seen_at, w.created_at)
              )
            ''',
            (uid,),
        ).fetchone()
        return int(row['count'] or 0)


def mark_public_feedback_read(viewer_user_id, issue_id):
    uid = _positive_id(viewer_user_id, label='查看者')
    issue_id = _positive_id(issue_id, label='问题')
    now_iso = _iso(_utc_now())
    with closing(db.get_db_connection()) as conn:
        issue = _issue_row_conn(conn, issue_id)
        watcher = conn.execute(
            '''
            SELECT 1 FROM public_issue_watchers
            WHERE issue_id = ? AND user_id = ?
            LIMIT 1
            ''',
            (issue_id, uid),
        ).fetchone()
        if _is_staff_conn(conn, uid):
            conn.execute(
                '''
                UPDATE public_issues
                SET staff_read_at = ?, staff_private_read_at = ?
                WHERE id = ?
                ''',
                (now_iso, now_iso, issue_id),
            )
        elif int(issue['author_user_id']) == uid:
            conn.execute(
                '''
                UPDATE public_issues
                SET author_read_at = ?, author_private_read_at = ?
                WHERE id = ?
                ''',
                (now_iso, now_iso, issue_id),
            )
        elif watcher:
            conn.execute(
                '''
                UPDATE public_issue_watchers
                SET last_seen_at = ?
                WHERE issue_id = ? AND user_id = ?
                ''',
                (now_iso, issue_id, uid),
            )
        else:
            conn.rollback()
            raise PublicFeedbackError('FORBIDDEN', '权限不足', 403)
        conn.commit()
        return {'marked_read': True, 'issue_id': issue_id}
