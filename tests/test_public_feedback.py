from datetime import datetime, timedelta, timezone

import pytest

import account_integrity as integrity
import db
import public_feedback as feedback


NOW = datetime(2026, 9, 5, 4, tzinfo=timezone.utc)


@pytest.fixture
def accounts(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'feedback.sqlite3'))
    db.init_db()
    with db.get_db_connection() as conn:
        for uid in range(1, 11):
            conn.execute(
                '''
                INSERT INTO users(id, username, username_lower, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (uid, f'user{uid}', f'user{uid}', 'unused', integrity._iso(NOW)),
            )
            integrity.initialize_user_conn(conn, uid, NOW)
        conn.execute(
            '''
            INSERT INTO user_roles(
                user_id, role_type, role_key, title, color, sort_order,
                can_direct_friend, chat_exempt, visible, created_at, updated_at
            ) VALUES (10, 'staff', 'staff', '', 'neutral', 1, 0, 0, 1, ?, ?)
            ''',
            (integrity._iso(NOW), integrity._iso(NOW)),
        )
        conn.commit()
    monkeypatch.setattr(feedback, '_utc_now', lambda: NOW)
    return list(range(1, 11))


def create_issue(author=1, kind='bug', title='测试问题', body='问题详细描述'):
    return feedback.create_public_issue(
        author,
        kind=kind,
        title=title,
        body=body,
    )


def insert_pair_decision(low, high, state='probable', risk_score=80):
    with db.get_db_connection() as conn:
        conn.execute(
            '''
            INSERT INTO account_link_decisions(
                user_id_low, user_id_high, state, risk_score, categories_json,
                reasons_json, input_fingerprint, recompute_id, rule_version,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                min(low, high),
                max(low, high),
                state,
                risk_score,
                '[]',
                '[]',
                'test-fingerprint',
                'test-recompute',
                integrity.RULE_VERSION,
                integrity._iso(NOW),
                integrity._iso(NOW),
            ),
        )
        conn.commit()


def insert_confirmed_group(members):
    members = sorted(set(members))
    with db.get_db_connection() as conn:
        cur = conn.execute(
            '''
            INSERT INTO account_link_groups(
                status, reputation, highest_total_gr, risk_score, rule_version,
                created_at, updated_at
            ) VALUES ('confirmed', 85, 0, 100, ?, ?, ?)
            ''',
            (integrity.RULE_VERSION, integrity._iso(NOW), integrity._iso(NOW)),
        )
        group_id = int(cur.lastrowid)
        conn.executemany(
            '''
            INSERT INTO account_link_members(group_id, user_id, status, joined_at)
            VALUES (?, ?, 'active', ?)
            ''',
            [(group_id, uid, integrity._iso(NOW)) for uid in members],
        )
        conn.commit()
        return group_id


def test_create_list_detail_and_initial_read_state(accounts):
    payload = create_issue()
    assert payload['id'] == 1
    assert payload['status'] == 'new'
    assert payload['kind'] == 'bug'
    assert payload['own_vote'] is False
    assert payload['author']['id'] == 1
    listing = feedback.list_public_issues(None)
    assert listing['total'] == 1
    assert listing['items'][0]['body_excerpt'] == '问题详细描述'
    detail = feedback.get_public_issue(None, payload['id'])
    assert detail['body'] == '问题详细描述'
    assert detail['status_history'][0]['to_status'] == 'new'
    assert detail['guest_comment_truncated'] is False
    assert feedback.public_feedback_author_unread_count(1) == 0
    assert feedback.public_feedback_staff_unread_count() == 1


def test_internal_issues_use_gi_keys_and_are_invisible_to_normal_players(accounts):
    with pytest.raises(feedback.PublicFeedbackError, match='只有 Staff'):
        feedback.create_public_issue(
            1,
            kind='internal',
            title='普通玩家不应创建',
            body='x',
        )

    internal = feedback.create_public_issue(
        10,
        kind='internal',
        title='内部追踪项',
        body='只在 Staff 看板展示',
    )
    assert internal['kind'] == 'internal'
    assert internal['key'] == f'GI-{internal["id"]}'

    normal_list = feedback.list_public_issues(1)
    assert all(item['kind'] != 'internal' for item in normal_list['items'])
    staff_list = feedback.list_public_issues(10, kind='internal')
    assert staff_list['total'] == 1
    assert staff_list['items'][0]['key'] == internal['key']

    console_list = feedback.list_public_issues(
        None,
        kind='internal',
        include_hidden=True,
    )
    assert console_list['total'] == 1

    detail = feedback.get_public_issue(10, internal['id'])
    assert detail['body'] == '只在 Staff 看板展示'
    with pytest.raises(feedback.PublicFeedbackError, match='问题不存在'):
        feedback.get_public_issue(1, internal['id'])
    with pytest.raises(feedback.PublicFeedbackError, match='问题不存在'):
        feedback.list_public_issues(1, kind='internal')


def test_internal_issue_status_and_public_actions_are_staff_managed(accounts):
    internal = feedback.create_public_issue(
        10,
        kind='internal',
        title='内部任务',
        body='内部说明',
    )
    with pytest.raises(feedback.PublicFeedbackError, match='只有 Staff'):
        feedback.post_public_comment(1, internal['id'], '普通玩家评论')
    comment = feedback.post_public_comment(10, internal['id'], 'Staff 评论')
    assert comment['issue_kind'] == 'internal'

    feedback.set_public_issue_status(10, internal['id'], 'in_progress', reason='开始')
    updated = feedback.get_public_issue(10, internal['id'])
    assert updated['status'] == 'in_progress'

    with pytest.raises(feedback.PublicFeedbackError, match='不参与投票'):
        feedback.toggle_public_vote(1, internal['id'])
    with pytest.raises(feedback.PublicFeedbackError, match='不支持关注'):
        feedback.toggle_public_watch(10, internal['id'])


def test_comment_create_edit_delete_windows(accounts):
    issue = create_issue()
    comment = feedback.post_public_comment(2, issue['id'], '第一条评论')
    assert comment['editable'] is True
    feedback.edit_public_comment(2, comment['id'], '修改后的评论')
    detail = feedback.get_public_issue(None, issue['id'])
    assert detail['comments'][0]['body'] == '修改后的评论'
    with pytest.raises(feedback.PublicFeedbackError, match='只能编辑自己的评论'):
        feedback.edit_public_comment(3, comment['id'], '不能替别人改')

    feedback.remove_public_comment(2, comment['id'])
    detail = feedback.get_public_issue(None, issue['id'])
    assert detail['comments'] == []

    later_comment = feedback.post_public_comment(2, issue['id'], '第二条评论')
    feedback._utc_now = lambda: NOW + timedelta(minutes=6)
    with pytest.raises(feedback.PublicFeedbackError, match='超过5分钟'):
        feedback.edit_public_comment(2, later_comment['id'], '太晚了')
    with pytest.raises(feedback.PublicFeedbackError, match='超过5分钟'):
        feedback.remove_public_comment(2, later_comment['id'])


def test_guest_comment_preview_is_first_three(accounts):
    issue = create_issue()
    for uid in range(2, 7):
        feedback.post_public_comment(uid, issue['id'], f'评论{uid}')
    guest = feedback.get_public_issue(None, issue['id'])
    assert [c['author_user_id'] for c in guest['comments']] == [2, 3, 4]
    assert guest['guest_comment_truncated'] is True
    assert guest['comment_count'] == 5
    logged = feedback.get_public_issue(5, issue['id'])
    assert len(logged['comments']) == 5


def test_author_cannot_vote_and_vote_toggles(accounts):
    issue = create_issue()
    with pytest.raises(feedback.PublicFeedbackError, match='不能给自己的问题投票'):
        feedback.toggle_public_vote(1, issue['id'])
    result = feedback.toggle_public_vote(2, issue['id'])
    assert result == {'voted': True, 'vote_count': 1}
    result = feedback.toggle_public_vote(2, issue['id'])
    assert result == {'voted': False, 'vote_count': 0}
    detail = feedback.get_public_issue(2, issue['id'])
    assert detail['own_vote'] is False


def test_probable_pair_blocks_vote_and_dedupes(accounts):
    insert_pair_decision(2, 3)
    issue = create_issue()
    feedback.toggle_public_vote(2, issue['id'])
    with pytest.raises(feedback.PublicFeedbackError, match='同组账号'):
        feedback.toggle_public_vote(3, issue['id'])
    assert feedback.get_public_issue(None, issue['id'])['vote_count'] == 1
    assert not integrity.are_same_voting_entity(2, 4)
    assert integrity.are_same_voting_entity(2, 3)


def test_confirmed_group_author_zero_and_realtime_dedupe(accounts):
    insert_confirmed_group([1, 4])
    issue = create_issue()
    with pytest.raises(feedback.PublicFeedbackError, match='同组账号'):
        feedback.toggle_public_vote(4, issue['id'])
    # New voters merge after the fact: effective count dedupes in real time.
    feedback.toggle_public_vote(5, issue['id'])
    feedback.toggle_public_vote(6, issue['id'])
    insert_confirmed_group([5, 6])
    assert feedback.get_public_issue(None, issue['id'])['vote_count'] == 1


def test_suspected_pair_does_not_block(accounts):
    insert_pair_decision(2, 3, state='suspected', risk_score=50)
    issue = create_issue()
    assert feedback.toggle_public_vote(2, issue['id'])['voted'] is True
    assert feedback.toggle_public_vote(3, issue['id'])['voted'] is True
    assert feedback.get_public_issue(None, issue['id'])['vote_count'] == 2


def test_deleted_account_vote_is_not_counted(accounts):
    issue = create_issue()
    feedback.toggle_public_vote(2, issue['id'])
    feedback.toggle_public_vote(3, issue['id'])
    with db.get_db_connection() as conn:
        conn.execute(
            'UPDATE users SET deleted_at = ? WHERE id = ?',
            (integrity._iso(NOW), 3),
        )
        conn.commit()
    assert feedback.get_public_issue(None, issue['id'])['vote_count'] == 1


def test_staff_status_priority_and_vote_lock(accounts):
    issue = create_issue()
    feedback.set_public_issue_status(10, issue['id'], 'confirmed', reason='可复现')
    feedback.set_public_issue_status(10, issue['id'], 'fixed', reason='已修复')
    assert feedback.get_public_issue(None, issue['id'])['status'] == 'fixed'
    with pytest.raises(feedback.PublicFeedbackError, match='已结束投票'):
        feedback.toggle_public_vote(2, issue['id'])
    with pytest.raises(feedback.PublicFeedbackError, match='不支持此状态'):
        feedback.set_public_issue_status(10, issue['id'], 'accepted')
    feedback.set_public_issue_priority(10, issue['id'], priority=2, pinned=True, sort_order=1)
    detail = feedback.get_public_issue(None, issue['id'])
    assert detail['priority'] == 2
    assert detail['pinned'] is True
    assert detail['sort_order'] == 1.0
    with pytest.raises(feedback.PublicFeedbackError, match='权限不足'):
        feedback.set_public_issue_status(2, issue['id'], 'invalid')


def test_suggestion_status_and_private_channel_permissions(accounts):
    issue = create_issue(author=1, kind='suggestion', title='增加新卡包', body='希望增加新卡包')
    assert issue['kind'] == 'suggestion'
    feedback.set_public_issue_status(10, issue['id'], 'accepted', reason='采纳')
    detail = feedback.get_public_issue(None, issue['id'])
    assert detail['status'] == 'accepted'
    with pytest.raises(feedback.PublicFeedbackError, match='只有作者或 Staff'):
        feedback.list_public_issue_private(2, issue['id'])
    feedback._utc_now = lambda: NOW + timedelta(minutes=1)
    msg = feedback.send_public_issue_private(10, issue['id'], '请补充回放编号')
    assert msg['kind'] == 'suggestion'
    assert feedback.public_feedback_author_unread_count(1) == 1
    private = feedback.list_public_issue_private(1, issue['id'])
    assert len(private['messages']) == 1
    assert feedback.public_feedback_author_unread_count(1) == 0


def test_staff_notes_and_hide_actions(accounts):
    issue = create_issue()
    comment = feedback.post_public_comment(2, issue['id'], '可隐藏评论')
    note = feedback._add_staff_note(10, issue['id'], '内部备注')
    assert note['note'] == '内部备注'
    with pytest.raises(feedback.PublicFeedbackError, match='权限不足'):
        feedback._add_staff_note(2, issue['id'], '不行')
    assert feedback.hide_public_issue(10, issue['id'], hidden=True)['hidden'] is True
    with pytest.raises(feedback.PublicFeedbackError, match='问题不存在'):
        feedback.get_public_issue(None, issue['id'])
    assert feedback.get_public_issue(10, issue['id'], include_hidden=True)['id'] == issue['id']
    assert feedback.hide_public_issue(10, issue['id'], hidden=False)['hidden'] is False
    assert feedback.hide_public_comment(10, comment['id'], hidden=True)['hidden'] is True
    detail = feedback.get_public_issue(None, issue['id'])
    assert detail['comments'] == []
    detail_staff = feedback.get_public_issue(10, issue['id'], include_hidden=True)
    assert detail_staff['comments'][0]['hidden'] is True
    assert feedback.hide_public_comment(10, comment['id'], hidden=False)['hidden'] is False


def test_staff_invalidate_vote_and_mark_read(accounts):
    issue = create_issue()
    feedback.toggle_public_vote(2, issue['id'])
    assert feedback.invalidate_public_vote(10, issue['id'], 2)['invalidated'] is True
    assert feedback.get_public_issue(None, issue['id'])['vote_count'] == 0
    assert feedback.invalidate_public_vote(10, issue['id'], 2, restore=True)['restored'] is True
    assert feedback.get_public_issue(None, issue['id'])['vote_count'] == 1
    feedback.mark_public_feedback_read(10, issue['id'])
    assert feedback.public_feedback_staff_unread_count() == 0


def test_deprecated_old_feedback_categories_are_hidden_and_rejected(accounts):
    with db.get_db_connection() as conn:
        cur = conn.execute(
            '''
            INSERT INTO feedback_threads(
                user_id, category, title, status, created_at, updated_at
            ) VALUES (1, 'bug', '旧漏洞', 'open', ?, ?)
            ''',
            (integrity._iso(NOW), integrity._iso(NOW)),
        )
        bug_thread = int(cur.lastrowid)
        cur = conn.execute(
            '''
            INSERT INTO feedback_threads(
                user_id, category, title, status, created_at, updated_at
            ) VALUES (1, 'account', '账号问题', 'open', ?, ?)
            ''',
            (integrity._iso(NOW), integrity._iso(NOW)),
        )
        account_thread = int(cur.lastrowid)
        conn.execute(
            '''
            INSERT INTO feedback_messages(
                thread_id, sender_user_id, sender_name, message, created_at
            ) VALUES (?, 1, 'user1', '旧内容', ?)
            ''',
            (bug_thread, integrity._iso(NOW)),
        )
        conn.execute(
            '''
            INSERT INTO feedback_messages(
                thread_id, sender_user_id, sender_name, message, created_at
            ) VALUES (?, 10, 'user10', '回复', ?)
            ''',
            (account_thread, integrity._iso(NOW)),
        )
        conn.commit()
    listed, _ = db.list_feedback_threads(1)
    assert [item['id'] for item in listed['items']] == [account_thread]
    assert db.feedback_unread_count(1) == 1
    _, error = db.get_feedback_messages(1, bug_thread)
    assert error == '反馈不存在'
    _, error = db.send_feedback_message(1, '新消息', thread_id=bug_thread)
    assert error == '反馈不存在'
    _, error = db.send_feedback_message(1, '新漏洞', category='bug', title='x')
    assert '反馈中心' in error
    _, error = db.send_feedback_message(1, '新账号问题', category='account', title='y')
    assert error is None


def test_list_search_matches_title_or_body(accounts):
    feedback.create_public_issue(1, kind='bug', title='SearchNeedleTitle', body='普通正文')
    feedback.create_public_issue(1, kind='bug', title='另一个标题', body='SearchNeedleBody')
    by_title = feedback.list_public_issues(None, search='SearchNeedleTitle')
    by_body = feedback.list_public_issues(None, search='SearchNeedleBody')
    assert by_title['total'] == 1
    assert by_body['total'] == 1
    assert [item['id'] for item in by_title['items']] != [item['id'] for item in by_body['items']]


def test_issue_key_version_tags_links_watchers_and_release_finalize(accounts):
    first = feedback.create_public_issue(
        1,
        kind='bug',
        title='GB版本测试',
        body='描述',
        game_version='2026-09-05-2',
    )
    second = feedback.create_public_issue(
        1,
        kind='suggestion',
        title='GS建议测试',
        body='建议描述',
        game_version='2026-09-05-2',
    )
    assert first['key'] == 'GB-1'
    assert second['key'] == 'GS-2'
    assert first['game_version'] == '2026-09-05-2'
    detail = feedback.get_public_issue(None, first['id'])
    assert detail['key'] == 'GB-1'

    tags = feedback.set_public_issue_tags(10, first['id'], ['花园', '战斗'])
    assert tags['tags'] == ['战斗', '花园']
    linked = feedback.link_public_issues(10, first['id'], second['id'], relation='related', note='有关')
    detail = feedback.get_public_issue(None, first['id'])
    assert [item['issue']['key'] for item in detail['related_issues']] == ['GS-2']
    assert feedback.unlink_public_issue(10, linked['link_id'])['removed'] is True

    watch = feedback.toggle_public_watch(2, first['id'])
    assert watch['watching'] is True and watch['watcher_count'] == 1
    assert feedback.toggle_public_watch(2, first['id'])['watching'] is False

    feedback.set_public_issue_status(10, first['id'], 'in_progress', reason='开始')
    result = feedback.finalize_public_release_fixes('2026-09-05-3')
    assert result['changed'] == 1
    fixed = feedback.get_public_issue(None, first['id'])
    assert fixed['status'] == 'fixed' and fixed['fix_version'] == '2026-09-05-3'
    assert feedback.finalize_public_release_fixes('2026-09-05-3')['changed'] == 0
    assert feedback.finalize_public_release_fixes('2026-09-05-2')['reason'] == 'rollback_ignored'


def test_not_fixed_request_requires_staff_reopen(accounts):
    issue = create_issue()
    feedback.set_public_issue_status(10, issue['id'], 'in_progress', reason='修复')
    feedback.finalize_public_release_fixes('2026-09-05-3')
    request = feedback.submit_public_reopen_request(2, issue['id'], '仍然会复现', replay_id='R-1')
    assert request['status'] == 'pending'
    with pytest.raises(feedback.PublicFeedbackError, match='等待处理'):
        feedback.submit_public_reopen_request(2, issue['id'], '重复提交')
    assert feedback.public_feedback_staff_unread_count() >= 1
    accepted = feedback.review_public_reopen_request(
        10,
        request['id'],
        'accept',
        reason='证据有效',
    )
    assert accepted['status'] == 'accepted'
    detail = feedback.get_public_issue(None, issue['id'])
    assert detail['status'] == 'confirmed'
    with pytest.raises(feedback.PublicFeedbackError, match='已经处理'):
        feedback.review_public_reopen_request(10, request['id'], 'accept')


def test_notifications_cover_watched_status_updates(accounts):
    issue = create_issue()
    feedback.toggle_public_watch(2, issue['id'])
    feedback._utc_now = lambda: NOW + timedelta(minutes=1)
    feedback.set_public_issue_status(10, issue['id'], 'confirmed', reason='已复现')
    notifications = feedback.public_feedback_notifications(2)
    watched = [item for item in notifications['items'] if item['type'] == 'watched']
    assert any(item['issue']['id'] == issue['id'] for item in watched)
    feedback.mark_public_feedback_read(2, issue['id'])
    assert feedback.public_feedback_watcher_unread_count(2) == 0
