"""Server-owned reputation, teammate reports and account association rules.

Only keyed, opaque identity digests enter this module.  Account IDs are taken
from the authenticated server context; HTTP callers never choose deltas or
association verdicts.  Every mutation owns one SQLite IMMEDIATE transaction.
"""

import hashlib
import json
import math
import re
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone

import db


BJ = timezone(timedelta(hours=8))
RULE_VERSION = '1'
IDENTITY_WINDOW_DAYS = 30
SHARED_NETWORK_USERS = 8


class IntegrityRuleError(ValueError):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code, self.status = code, status


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _time(value=None):
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    if isinstance(value, datetime):
        result = value
    else:
        try:
            result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except (TypeError, ValueError):
            raise IntegrityRuleError('INVALID_TIME', '时间格式无效')
    if result.tzinfo is None:
        raise IntegrityRuleError('INVALID_TIME', '时间必须包含时区')
    return result.astimezone(timezone.utc).replace(microsecond=0)


def _iso(value):
    return value.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def _id(value):
    if isinstance(value, bool):
        raise IntegrityRuleError('INVALID_ID', '编号无效')
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise IntegrityRuleError('INVALID_ID', '编号无效')
    if result <= 0 or str(value).strip() != str(result):
        raise IntegrityRuleError('INVALID_ID', '编号无效')
    return result


@contextmanager
def _transaction():
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise


def _user(conn, uid):
    row = conn.execute('SELECT * FROM users WHERE id = ? AND deleted_at IS NULL', (uid,)).fetchone()
    if row is None:
        raise IntegrityRuleError('USER_NOT_FOUND', '账号不存在', 404)
    return row


def initialize_user_conn(conn, uid, now=None):
    """Called in the same transaction as registration (and by lazy writes)."""
    now = _time(now)
    row = _user(conn, uid)
    today = now.astimezone(BJ).date().isoformat()
    value = max(0, min(100, int(row['reputation'] if row['reputation'] is not None else 85)))
    conn.execute(
        '''UPDATE users SET reputation = ?,
           reputation_initialized_at = COALESCE(reputation_initialized_at, ?),
           reputation_last_recovery_date = COALESCE(reputation_last_recovery_date, ?)
           WHERE id = ?''', (value, _iso(now), today, uid),
    )
    conn.execute(
        '''INSERT OR IGNORE INTO reputation_ledger
           (business_id,user_id,delta,value_before,value_after,reason_code,metadata_json,reputation_date,created_at)
           VALUES (?, ?, 0, ?, ?, 'initialization', '{}', ?, ?)''',
        (f'reputation:init:user:{uid}', uid, value, value, today, _iso(now)),
    )


def _group(conn, uid):
    return conn.execute(
        '''SELECT g.* FROM account_link_groups g JOIN account_link_members m ON m.group_id = g.id
           WHERE m.user_id = ? AND m.status = 'active' AND g.status IN ('confirmed','appealed')''', (uid,),
    ).fetchone()


def _members(conn, group_id):
    return [int(r['user_id']) for r in conn.execute(
        "SELECT m.user_id FROM account_link_members m JOIN users u ON u.id=m.user_id WHERE m.group_id = ? AND m.status = 'active' AND u.deleted_at IS NULL ORDER BY m.user_id",
        (group_id,),
    )]


def profile_conn(conn, uid):
    from pvp_economy import profile_conn as newcomer_profile_conn
    row = _user(conn, uid)
    group = _group(conn, uid)
    value = int(group['reputation'] if group else (row['reputation'] if row['reputation'] is not None else 85))
    level = 'red' if value < 40 else 'orange' if value < 60 else 'yellow' if value < 80 else 'normal'
    linked_band = None
    if group:
        highest = conn.execute(
            '''SELECT MAX(u.total_gr) AS value FROM users u JOIN account_link_members m ON m.user_id=u.id
               WHERE m.group_id=? AND m.status='active' ''', (group['id'],),
        ).fetchone()['value']
        lower = int(math.floor(float(highest or 0) / 50) * 50)
        linked_band = {'min': lower, 'max': lower + 49, 'label': f'{lower}–{lower + 49}'}
    risk = conn.execute(
        '''SELECT state FROM account_link_decisions WHERE (user_id_low=? OR user_id_high=?)
           AND state IN ('suspected','probable') ORDER BY risk_score DESC LIMIT 1''', (uid, uid),
    ).fetchone()
    appeal = conn.execute(
        "SELECT status FROM account_link_appeals WHERE appellant_user_id=? ORDER BY id DESC LIMIT 1", (uid,),
    ).fetchone()
    return {
        'value': value, 'level': level,
        'label': '低信誉用户' if value < 80 else '',
        'can_ranked': value >= 40, 'can_achievements': value >= 60,
        'dew_multiplier': 0 if value < 40 else 0.5 if value < 60 else 1,
        'linked': bool(group), 'link_state': group['status'] if group else risk['state'] if risk else 'none',
        'linked_gr_band': linked_band,
        'appeal_status': appeal['status'] if appeal else None,
        'newcomer': newcomer_profile_conn(conn, uid),
    }


def get_reputation_profile(user_id):
    with closing(db.get_db_connection()) as conn:
        return profile_conn(conn, _id(user_id))


def reward_amount_conn(conn, uid, amount):
    """Only earned/free rewards use this; purchases/refunds/admin grants do not."""
    return int(max(0, int(amount)) * profile_conn(conn, uid)['dew_multiplier'])


def match_reward_allowed_conn(conn, uid, participants, duration_seconds, same_opponent_count):
    for other in participants:
        if other == uid:
            continue
        pair = conn.execute('SELECT state FROM account_link_decisions WHERE user_id_low=? AND user_id_high=?',
                            (min(uid,other),max(uid,other))).fetchone()
        if pair and (pair['state'] in ('confirmed','appealed') or
                     (pair['state']=='probable' and (duration_seconds<60 or same_opponent_count>0))):
            return False
        own_group, other_group = _group(conn,uid), _group(conn,other)
        if own_group and other_group and own_group['id']==other_group['id']:
            return False
    return True


def _change_conn(conn, uid, delta, reason, business_id, now, match_id=None, metadata=None):
    if type(delta) is not int or not -100 <= delta <= 100:
        raise IntegrityRuleError('INVALID_DELTA', '信誉变化无效')
    if not isinstance(business_id, str) or not 1 <= len(business_id) <= 160:
        raise IntegrityRuleError('INVALID_BUSINESS_ID', '业务编号无效')
    initialize_user_conn(conn, uid, now)
    details = dict(metadata or {})
    # Persist the requested semantic operation even when a clamp makes delta=0.
    details.update({'actor_user_id': uid, 'requested_delta': delta})
    serialized = _json(details)
    existing = conn.execute('SELECT * FROM reputation_ledger WHERE business_id=?', (business_id,)).fetchone()
    if existing:
        if existing['reason_code'] != reason or existing['match_id'] != match_id or existing['metadata_json'] != serialized:
            raise IntegrityRuleError('BUSINESS_ID_CONFLICT', '业务编号对应的内容不一致', 409)
        return {**dict(existing), 'duplicate': True}
    group = _group(conn, uid)
    row = _user(conn, uid)
    before = int(group['reputation'] if group else row['reputation'])
    after = max(0, min(100, before + delta))
    gid = int(group['id']) if group else None
    if gid:
        conn.execute('UPDATE account_link_groups SET reputation=?,updated_at=? WHERE id=?', (after, _iso(now), gid))
        conn.execute(
            '''UPDATE users SET reputation=? WHERE id IN
               (SELECT user_id FROM account_link_members WHERE group_id=? AND status='active')''', (after, gid),
        )
    else:
        conn.execute('UPDATE users SET reputation=? WHERE id=?', (after, uid))
    cur = conn.execute(
        '''INSERT INTO reputation_ledger
           (business_id,user_id,link_group_id,delta,value_before,value_after,reason_code,match_id,
            metadata_json,reputation_date,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
        (business_id, None if gid else uid, gid, after-before, before, after, reason, match_id,
         serialized, now.astimezone(BJ).date().isoformat(), _iso(now)),
    )
    return {**dict(conn.execute('SELECT * FROM reputation_ledger WHERE id=?', (cur.lastrowid,)).fetchone()), 'duplicate': False}


def change_reputation(user_id, delta, reason, business_id, *, now=None, match_id=None, metadata=None):
    with _transaction() as conn:
        return _change_conn(conn, _id(user_id), delta, str(reason), business_id, _time(now), match_id, metadata)


def apply_match_penalty(user_id, kind, business_id, *, ranked=False, match_id=None, now=None):
    penalties = {'early_surrender': -2, 'consecutive_timeouts': -5, 'team_report': -5}
    if kind not in penalties:
        raise IntegrityRuleError('INVALID_PENALTY', '处罚类型无效')
    return change_reputation(user_id, penalties[kind] if ranked else -1, kind, business_id,
                             now=now, match_id=match_id, metadata={'ranked': bool(ranked)})


def recover_reputation_daily(*, now=None, user_id=None):
    """Catch up completed Beijing days; one recovery per entity/day, never per login."""
    now = _time(now)
    today = now.astimezone(BJ).date()
    results = []
    with _transaction() as conn:
        ids = [_id(user_id)] if user_id is not None else [r['id'] for r in conn.execute('SELECT id FROM users WHERE deleted_at IS NULL')]
        seen = set()
        for uid in ids:
            initialize_user_conn(conn, uid, now)
            group = _group(conn, uid)
            row = _user(conn, uid)
            gid = group['id'] if group else None
            entity = ('group', gid) if gid else ('user', uid)
            if entity in seen:
                continue
            seen.add(entity)
            last_text = group['last_recovery_date'] if group else row['reputation_last_recovery_date']
            last = datetime.fromisoformat(last_text or today.isoformat()).date()
            member_ids = _members(conn, gid) if gid else [uid]
            for offset in range(1, max(0, (today-last).days) + 1):
                recovery_day = last + timedelta(days=offset)
                activity_day = recovery_day - timedelta(days=1)
                placeholders = ','.join('?' for _ in member_ids)
                entries = conn.execute(
                    f'''SELECT delta,metadata_json FROM reputation_ledger WHERE reputation_date=? AND
                        (user_id IN ({placeholders}) OR link_group_id IN
                         (SELECT group_id FROM account_link_members WHERE user_id IN ({placeholders})))''',
                    (activity_day.isoformat(), *member_ids, *member_ids),
                )
                deduction = any(int(entry['delta']) < 0 or
                                int(json.loads(entry['metadata_json']).get('requested_delta',0)) < 0 for entry in entries)
                current = profile_conn(conn, uid)['value']
                eligible = current < 40
                if not deduction and not eligible and current < 100:
                    start = datetime.combine(activity_day, datetime.min.time(), BJ)
                    matches = conn.execute('SELECT participant_ids_json FROM gr_match_results WHERE played_at>=? AND played_at<?',
                                           (_iso(start), _iso(start+timedelta(days=1))))
                    eligible = any(set(json.loads(m['participant_ids_json'])) & set(member_ids) for m in matches)
                if not deduction and eligible and current < 100:
                    results.append(_change_conn(conn, uid, 5, 'daily_recovery',
                        f'reputation:daily:{entity[0]}:{entity[1]}:{recovery_day.isoformat()}',
                        datetime.combine(recovery_day, datetime.min.time(), BJ),
                        metadata={'activity_date': activity_day.isoformat()}))
            if gid:
                conn.execute('UPDATE account_link_groups SET last_recovery_date=? WHERE id=?', (today.isoformat(), gid))
                conn.execute("UPDATE users SET reputation_last_recovery_date=? WHERE id IN (SELECT user_id FROM account_link_members WHERE group_id=? AND status='active')", (today.isoformat(), gid))
            else:
                conn.execute('UPDATE users SET reputation_last_recovery_date=? WHERE id=?', (today.isoformat(), uid))
    return results


def _match(conn, match_id):
    row = conn.execute('SELECT * FROM matches WHERE id=?', (match_id,)).fetchone()
    if not row:
        raise IntegrityRuleError('MATCH_NOT_FOUND', '对局不存在', 404)
    summary = json.loads(row['summary_json'] or '{}')
    ids = summary.get('player_ids') or json.loads(row['player_ids_json'] or '[]')
    if row['mode'] != '2v2' or len(ids) != 4 or any(type(v) is not int or v <= 0 for v in ids) or len(set(ids)) != 4:
        raise IntegrityRuleError('MATCH_NOT_ELIGIBLE', '仅支持四名注册玩家的2v2对局')
    teams = summary.get('teams', [[0, 1], [2, 3]])
    if not isinstance(teams, list) or len(teams) != 2 or any(not isinstance(t, list) or len(t) != 2 for t in teams):
        raise IntegrityRuleError('INVALID_MATCH_TEAMS', '对局队伍数据无效')
    if any(type(i) is not int for team in teams for i in team) or sorted(i for team in teams for i in team) != [0, 1, 2, 3]:
        raise IntegrityRuleError('INVALID_MATCH_TEAMS', '对局队伍数据无效')
    return row, summary, [[ids[i] for i in team] for team in teams]


def _report_audit(conn, rid, action, actor, old, new, now, reason='', actor_name=''):
    conn.execute('''INSERT INTO team_report_audit
        (team_report_id,action,actor_user_id,actor_name,old_status,new_status,reason,created_at)
        VALUES (?,?,?,?,?,?,?,?)''', (rid, action, actor, actor_name, old, new, reason, _iso(now)))


def _expire_reports(conn, now):
    rows = conn.execute("SELECT id FROM team_reports WHERE status='pending_confirmation' AND confirmation_expires_at<=?", (_iso(now),)).fetchall()
    for row in rows:
        conn.execute("UPDATE team_reports SET status='expired',resolved_at=? WHERE id=?", (_iso(now), row['id']))
        _report_audit(conn, row['id'], 'expire', None, 'pending_confirmation', 'expired', now)
    return len(rows)


def expire_team_reports(*, now=None):
    with _transaction() as conn:
        return _expire_reports(conn, _time(now))


def create_team_report(user_id, match_id, target_user_id, reason, *, now=None):
    uid, mid, target = _id(user_id), _id(match_id), _id(target_user_id)
    now = _time(now)
    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 300:
        raise IntegrityRuleError('INVALID_REASON', '请填写1至300字的举报理由')
    with _transaction() as conn:
        _user(conn, uid)
        _user(conn, target)
        row, summary, teams = _match(conn, mid)
        if uid == target or not any(uid in team and target in team for team in teams):
            raise IntegrityRuleError('NOT_TEAMMATE', '只能举报这场对局中的队友', 403)
        existing = conn.execute('SELECT * FROM team_reports WHERE match_id=? AND reporter_user_id=? AND target_user_id=?', (mid, uid, target)).fetchone()
        if existing:
            if existing['reason_text'] != reason.strip():
                raise IntegrityRuleError('REPORT_CONFLICT', '这场对局已经提交过举报', 409)
            return {**dict(existing), 'duplicate': True}
        if not row['ended_at'] or row['result'] not in ('win','draw','finished'):
            raise IntegrityRuleError('MATCH_NOT_FINISHED', '只能举报已正常结束的对局')
        ended = _time(row['ended_at'])
        if not 0 <= (now-ended).total_seconds() <= 600:
            raise IntegrityRuleError('REPORT_WINDOW_CLOSED', '请在对局结束后10分钟内提交举报', 409)
        cur = conn.execute('''INSERT INTO team_reports
            (match_id,reporter_user_id,target_user_id,reason_text,created_at,confirmation_expires_at)
            VALUES (?,?,?,?,?,?)''', (mid, uid, target, reason.strip(), _iso(now), _iso(ended+timedelta(hours=24))))
        _report_audit(conn, cur.lastrowid, 'create', uid, None, 'pending_confirmation', now, reason.strip())
        return dict(conn.execute('SELECT * FROM team_reports WHERE id=?', (cur.lastrowid,)).fetchone())


def mutate_team_report(user_id, report_id, action, *, now=None):
    uid, rid, now = _id(user_id), _id(report_id), _time(now)
    if action not in ('confirm', 'withdraw'):
        raise IntegrityRuleError('INVALID_ACTION', '举报操作无效')
    with _transaction() as conn:
        _user(conn, uid)
        report = conn.execute('SELECT * FROM team_reports WHERE id=?', (rid,)).fetchone()
        if not report:
            raise IntegrityRuleError('REPORT_NOT_FOUND', '举报不存在', 404)
        _, summary, teams = _match(conn, report['match_id'])
        opponent = any(uid in team and report['target_user_id'] not in team for team in teams)
        if (action == 'withdraw' and uid != report['reporter_user_id']) or (action == 'confirm' and not opponent):
            raise IntegrityRuleError('REPORT_FORBIDDEN', '无权执行此举报操作', 403)
        desired = 'confirmed' if action == 'confirm' else 'withdrawn'
        if report['status'] == desired:
            return {**dict(report), 'duplicate': True}
        if report['status'] != 'pending_confirmation' or _time(report['confirmation_expires_at']) <= now:
            raise IntegrityRuleError('REPORT_CLOSED', '举报已结束或超过24小时确认期', 409)
        if action == 'confirm':
            ranked = summary.get('match_type') == 'ranked'
            _change_conn(conn, report['target_user_id'], -5 if ranked else -1, 'team_report',
                         f'reputation:team-report:{rid}', now, report['match_id'], {'ranked': ranked})
            conn.execute("UPDATE team_reports SET status='confirmed',confirmed_by_user_id=?,confirmed_at=?,resolved_at=? WHERE id=?", (uid, _iso(now), _iso(now), rid))
        else:
            conn.execute("UPDATE team_reports SET status='withdrawn',resolved_at=? WHERE id=?", (_iso(now), rid))
        _report_audit(conn, rid, action, uid, report['status'], desired, now)
        return dict(conn.execute('SELECT * FROM team_reports WHERE id=?', (rid,)).fetchone())


def list_team_reports(user_id=None, *, now=None, admin=False):
    now = _time(now)
    uid = _id(user_id) if user_id is not None else None
    with _transaction() as conn:
        _expire_reports(conn, now)
        if admin:
            _staff(conn, uid)
        else:
            _user(conn, uid)
        scope = '' if admin else '''WHERE (r.reporter_user_id=? OR r.target_user_id=? OR
            (r.status='pending_confirmation' AND EXISTS
                (SELECT 1 FROM matches m, json_each(m.player_ids_json) participant
                 WHERE m.id=r.match_id AND CAST(participant.value AS INTEGER)=?)))'''
        rows = conn.execute('''SELECT r.*, a.username AS reporter_name,b.username AS target_name
            FROM team_reports r JOIN users a ON a.id=r.reporter_user_id JOIN users b ON b.id=r.target_user_id
            ''' + scope + ' ORDER BY r.id DESC LIMIT 300', () if admin else (uid,uid,uid)).fetchall()
        result = []
        for row in rows:
            if admin:
                result.append(dict(row))
                continue
            _, _, teams = _match(conn, row['match_id'])
            can_confirm = row['status'] == 'pending_confirmation' and any(uid in t and row['target_user_id'] not in t for t in teams)
            if uid not in (row['reporter_user_id'], row['target_user_id']) and not can_confirm:
                continue
            result.append({**dict(row), 'can_confirm': can_confirm,
                           'can_withdraw': uid == row['reporter_user_id'] and row['status'] == 'pending_confirmation'})
        return result[:100]


def _staff(conn, uid):
    _user(conn, uid)
    role = conn.execute('SELECT role_type FROM user_roles WHERE user_id=?', (uid,)).fetchone()
    if role is None or role['role_type'] not in ('staff', 'admin'):
        raise IntegrityRuleError('STAFF_REQUIRED', '需要 Staff/Admin 权限', 403)


def revoke_team_report(actor_id, report_id, reason, *, now=None):
    uid, rid, now = _id(actor_id), _id(report_id), _time(now)
    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 500:
        raise IntegrityRuleError('INVALID_REASON', '必须填写撤销理由')
    with _transaction() as conn:
        _staff(conn, uid)
        report = conn.execute('SELECT * FROM team_reports WHERE id=?', (rid,)).fetchone()
        if not report:
            raise IntegrityRuleError('REPORT_NOT_FOUND', '举报不存在', 404)
        if report['status'] == 'revoked':
            return {**dict(report), 'duplicate': True}
        if report['status'] != 'confirmed':
            raise IntegrityRuleError('REPORT_NOT_CONFIRMED', '只能撤销已成立的举报', 409)
        penalty = conn.execute('SELECT delta FROM reputation_ledger WHERE business_id=?', (f'reputation:team-report:{rid}',)).fetchone()
        if not penalty:
            raise IntegrityRuleError('MISSING_PENALTY', '处罚流水缺失，不能自动撤销', 409)
        _change_conn(conn, report['target_user_id'], -int(penalty['delta']), 'team_report_revoked',
                     f'reputation:team-report-revoke:{rid}', now, report['match_id'], {'staff_user_id': uid, 'reason': reason.strip()})
        conn.execute("UPDATE team_reports SET status='revoked',resolved_at=?,resolution_note=? WHERE id=?", (_iso(now), reason.strip(), rid))
        _report_audit(conn, rid, 'revoke', uid, 'confirmed', 'revoked', now, reason.strip())
        return dict(conn.execute('SELECT * FROM team_reports WHERE id=?', (rid,)).fetchone())


def _link_admin_audit(conn, actor, group_id, action, reason, old, new, now):
    name = _user(conn, actor)['username']
    conn.execute('''INSERT INTO account_link_admin_audit
        (group_id,action,actor_user_id,actor_username,reason,old_value_json,new_value_json,created_at)
        VALUES (?,?,?,?,?,?,?,?)''', (group_id, action, actor, name, reason, _json(old), _json(new), _iso(now)))


def _merge_group_conn(conn, ids, score, now, *, explicit=False):
    ids = set(ids)
    groups = {}
    for uid in list(ids):
        initialize_user_conn(conn, uid, now)
        group = _group(conn, uid)
        if group:
            groups[group['id']] = group
            ids.update(_members(conn, group['id']))
    ordered = sorted(ids)
    if not explicit:
        if any(g['status'] == 'appealed' for g in groups.values()):
            return None
        placeholders = ','.join('?' for _ in ids)
        separated = conn.execute(
            f'''SELECT 1 FROM account_link_decisions WHERE state='dismissed'
                AND user_id_low IN ({placeholders}) AND user_id_high IN ({placeholders}) LIMIT 1''',
            (*ordered, *ordered),
        ).fetchone()
        if separated:
            return None
    values = {uid: int(_user(conn, uid)['reputation']) for uid in ordered}
    reputation = min(values.values())
    highest = max(float(_user(conn, uid)['total_gr'] or 0) for uid in ordered)
    today = now.astimezone(BJ).date().isoformat()
    last_recovery = max([today if not groups else '0001-01-01'] +
                        [str(_user(conn,uid)['reputation_last_recovery_date'] or today) for uid in ordered] +
                        [str(g['last_recovery_date'] or today) for g in groups.values()])
    if groups:
        gid = min(groups)
        conn.execute('''UPDATE account_link_groups SET reputation=?,highest_total_gr=?,risk_score=MAX(risk_score,?),
            rule_version=?,last_recovery_date=?,updated_at=? WHERE id=?''', (reputation, highest, score, RULE_VERSION, last_recovery, _iso(now), gid))
    else:
        gid = conn.execute('''INSERT INTO account_link_groups
            (reputation,highest_total_gr,risk_score,rule_version,last_recovery_date,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?)''', (reputation, highest, score, RULE_VERSION, last_recovery, _iso(now), _iso(now))).lastrowid
    for old_gid in groups:
        if old_gid == gid:
            continue
        conn.execute("UPDATE account_link_members SET status='removed',removed_at=? WHERE group_id=? AND status='active'", (_iso(now), old_gid))
        conn.execute("UPDATE account_link_groups SET status='dismissed',closed_at=?,updated_at=? WHERE id=?", (_iso(now), _iso(now), old_gid))
        conn.execute('UPDATE account_link_decisions SET group_id=? WHERE group_id=?', (gid, old_gid))
        conn.execute("UPDATE account_link_appeals SET group_id=? WHERE group_id=? AND status='pending'", (gid, old_gid))
    if conn.execute("SELECT 1 FROM account_link_appeals WHERE group_id=? AND status='pending'", (gid,)).fetchone():
        conn.execute("UPDATE account_link_groups SET status='appealed' WHERE id=?", (gid,))
    for uid in ordered:
        conn.execute('''INSERT INTO account_link_members(group_id,user_id,status,joined_at)
            VALUES (?,?,'active',?) ON CONFLICT(group_id,user_id) DO UPDATE SET status='active',removed_at=NULL''', (gid, uid, _iso(now)))
        conn.execute('UPDATE users SET reputation=?,reputation_last_recovery_date=? WHERE id=?', (reputation, last_recovery, uid))
    member_key = hashlib.sha256(_json(ordered).encode()).hexdigest()[:24]
    conn.execute('''INSERT OR IGNORE INTO reputation_ledger
        (business_id,link_group_id,delta,value_before,value_after,reason_code,metadata_json,reputation_date,created_at)
        VALUES (?,?,0,?,?,'account_link_group',?,?,?)''',
        (f'reputation:group:{gid}:{member_key}', gid, reputation, reputation,
         _json({'members': ordered, 'previous_values': values, 'rule_version': RULE_VERSION}), today, _iso(now)))
    return gid


def _pair_signals(conn, low, high, now):
    cutoff = _iso(now - timedelta(days=IDENTITY_WINDOW_DAYS))
    rows = list(conn.execute('''SELECT user_id,device_hash,network_hash,event_day,is_registration,created_at
        FROM account_identity_events WHERE user_id IN (?,?) AND created_at>=? ORDER BY id''', (low, high, cutoff)))
    a, b = ([r for r in rows if r['user_id'] == uid] for uid in (low, high))
    devices = {r['device_hash'] for r in a if r['device_hash']} & {r['device_hash'] for r in b if r['device_hash']}
    stable_device_days = max((len({r['event_day'] for r in a if r['device_hash']==key} &
                                  {r['event_day'] for r in b if r['device_hash']==key}) for key in devices), default=0)
    networks = {r['network_hash'] for r in a if r['network_hash']} & {r['network_hash'] for r in b if r['network_hash']}
    network_days = max((len({r['event_day'] for r in a if r['network_hash']==key} &
                            {r['event_day'] for r in b if r['network_hash']==key}) for key in networks), default=0)
    shared = False
    for key in networks:
        # Campus/cafe networks are assessed per day, not by an all-time count.
        row = conn.execute('''SELECT COUNT(DISTINCT user_id) AS n FROM account_identity_events
            WHERE network_hash=? AND created_at>=? GROUP BY event_day ORDER BY n DESC LIMIT 1''', (key, cutoff)).fetchone()
        shared = shared or bool(row and row['n'] >= SHARED_NETWORK_USERS)
    registration_overlap = any(
        x['is_registration'] and y['is_registration'] and x['network_hash'] and x['network_hash']==y['network_hash']
        and abs((_time(x['created_at'])-_time(y['created_at'])).total_seconds()) <= 86400 for x in a for y in b)
    # Sustained suspicious play is corroboration only. Normal long games and
    # simply sharing opponents never supply this signal.
    short_days = set()
    short_count = 0
    for match in conn.execute('''SELECT ended_at,summary_json FROM matches
        WHERE ended_at>=? AND duration_seconds>=0 AND duration_seconds<60''', (cutoff,)):
        data = json.loads(match['summary_json'] or '{}')
        participants = data.get('player_ids') or []
        if low in participants and high in participants and data.get('ended_by_surrender'):
            short_count += 1
            short_days.add(_time(match['ended_at']).astimezone(BJ).date().isoformat())
    behavior = short_count >= 4 and len(short_days) >= 3
    users = [_user(conn, uid) for uid in (low, high)]
    games = [int(u['total_ranked_games'] or 0) for u in users]
    rating = (any(1 <= n <= 10 for n in games) and any(n > 10 for n in games)
              and math.floor(float(users[0]['total_gr'] or 0)/50) == math.floor(float(users[1]['total_gr'] or 0)/50))
    score, categories, reasons = 0, set(), []
    def add(points, category, reason):
        nonlocal score
        score += points
        categories.add(category)
        reasons.append({'code': reason, 'points': points})
    if devices:
        add(50, 'device', 'same_server_device_token')
    if stable_device_days >= 3:
        add(25, 'device', 'same_device_three_days')
    network_score = (15 if network_days >= 3 else 0) + (10 if registration_overlap else 0)
    if network_score:
        add(min(5, network_score) if shared else network_score, 'network', 'shared_network_capped' if shared else 'repeated_network_or_registration')
    if behavior:
        add(20, 'behavior', 'repeated_short_surrender_three_days')
    if rating:
        add(10, 'rating', 'new_account_similar_50_gr_band')
    can_confirm = (score >= 90 and len(categories) >= 2 and bool(categories & {'device','behavior'})
                   and (not shared or behavior))
    state = 'confirmed' if can_confirm else 'probable' if score >= 70 else 'suspected' if score >= 40 else 'none'
    facts = {'shared_device': bool(devices), 'stable_device_days': stable_device_days,
             'network_days': network_days, 'shared_network': shared, 'registration_overlap': registration_overlap,
             'short_match_count': short_count, 'short_match_days': len(short_days), 'rating_band_match': rating}
    return score, sorted(categories), reasons, state, facts


def _recompute_pair_conn(conn, low, high, now):
    old = conn.execute('SELECT * FROM account_link_decisions WHERE user_id_low=? AND user_id_high=?', (low, high)).fetchone()
    score, categories, reasons, state, facts = _pair_signals(conn, low, high, now)
    fingerprint = hashlib.sha256(_json({'rule': RULE_VERSION, 'facts': facts}).encode()).hexdigest()
    gid = old['group_id'] if old else None
    # Human separation/appeal is a durable safety override, not a race with the
    # next login. Confirmed membership is not silently revoked as logs age out.
    if old and old['state'] in ('dismissed', 'appealed', 'confirmed'):
        state = old['state']
    if state == 'confirmed':
        new_gid = _merge_group_conn(conn, [low, high], score, now)
        if new_gid is None and not (old and old['state']=='confirmed'):
            state = 'probable'
            reasons.append({'code': 'manual_separation_or_pending_appeal', 'points': 0})
        elif new_gid is not None:
            gid = new_gid
    recompute_id = hashlib.sha256(_json([low, high, fingerprint, state, gid, reasons]).encode()).hexdigest()
    if old and old['recompute_id'] == recompute_id:
        return {**dict(old), 'duplicate': True}
    conn.execute('''INSERT INTO account_link_decisions
        (user_id_low,user_id_high,state,risk_score,categories_json,reasons_json,input_fingerprint,recompute_id,
         rule_version,group_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(user_id_low,user_id_high) DO UPDATE SET state=excluded.state,risk_score=excluded.risk_score,
        categories_json=excluded.categories_json,reasons_json=excluded.reasons_json,input_fingerprint=excluded.input_fingerprint,
        recompute_id=excluded.recompute_id,rule_version=excluded.rule_version,group_id=excluded.group_id,updated_at=excluded.updated_at''',
        (low, high, state, score, _json(categories), _json(reasons), fingerprint, recompute_id, RULE_VERSION, gid, _iso(now), _iso(now)))
    conn.execute('''INSERT OR IGNORE INTO account_link_decision_audit
        (recompute_id,user_id_low,user_id_high,old_state,new_state,risk_score,categories_json,reasons_json,input_fingerprint,rule_version,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)''', (recompute_id, low, high, old['state'] if old else None, state, score,
        _json(categories), _json(reasons), fingerprint, RULE_VERSION, _iso(now)))
    return dict(conn.execute('SELECT * FROM account_link_decisions WHERE user_id_low=? AND user_id_high=?', (low, high)).fetchone())


def recompute_account_links(user_id, *, now=None):
    uid, now = _id(user_id), _time(now)
    with _transaction() as conn:
        _user(conn, uid)
        cutoff = _iso(now-timedelta(days=IDENTITY_WINDOW_DAYS))
        candidates = {r['user_id'] for r in conn.execute('''SELECT DISTINCT other.user_id FROM account_identity_events own
            JOIN account_identity_events other ON other.user_id!=own.user_id AND
              ((own.device_hash!='' AND own.device_hash=other.device_hash) OR
               (own.network_hash!='' AND own.network_hash=other.network_hash))
            JOIN users u ON u.id=other.user_id AND u.deleted_at IS NULL
            WHERE own.user_id=? AND own.created_at>=? AND other.created_at>=?''', (uid, cutoff, cutoff))}
        for row in conn.execute('SELECT user_id_low,user_id_high FROM account_link_decisions WHERE user_id_low=? OR user_id_high=?', (uid, uid)):
            candidates.add(row['user_id_high'] if row['user_id_low']==uid else row['user_id_low'])
        results = []
        for other in sorted(candidates):
            if conn.execute('SELECT 1 FROM users WHERE id=? AND deleted_at IS NULL', (other,)).fetchone():
                results.append(_recompute_pair_conn(conn, min(uid,other), max(uid,other), now))
        return results


def record_identity_event(user_id, device_hash, network_hash, *, source='login', now=None):
    uid, now = _id(user_id), _time(now)
    for value in (device_hash, network_hash):
        if not isinstance(value, str) or (value and not re.fullmatch(r'[a-f0-9]{64}', value)):
            raise IntegrityRuleError('INVALID_IDENTITY_DIGEST', '仅接受服务端生成的标识摘要')
    if source not in ('register','login','session') or not device_hash:
        raise IntegrityRuleError('INVALID_IDENTITY_EVENT', '账号标识事件无效')
    with _transaction() as conn:
        initialize_user_conn(conn, uid, now)
        cursor = conn.execute('''INSERT OR IGNORE INTO account_identity_events
            (user_id,device_hash,network_hash,source,event_day,is_registration,created_at) VALUES (?,?,?,?,?,?,?)''',
            (uid, device_hash, network_hash, source, now.astimezone(BJ).date().isoformat(), int(source=='register'), _iso(now)))
        inserted = cursor.rowcount > 0
    if inserted:
        recompute_account_links(uid, now=now)
    return inserted


def refresh_recent_account_links(*, now=None):
    now = _time(now)
    with closing(db.get_db_connection()) as conn:
        ids = [r['user_id'] for r in conn.execute('''SELECT DISTINCT e.user_id FROM account_identity_events e
            JOIN users u ON u.id=e.user_id WHERE e.created_at>=? AND u.deleted_at IS NULL''',
            (_iso(now-timedelta(days=1)),))]
    for uid in ids:
        recompute_account_links(uid,now=now)
    return len(ids)


def appeal_account_link(user_id, reason, *, now=None):
    uid, now = _id(user_id), _time(now)
    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 500:
        raise IntegrityRuleError('INVALID_REASON', '请填写1至500字的申诉理由')
    with _transaction() as conn:
        _user(conn, uid)
        group = _group(conn, uid)
        if not group:
            raise IntegrityRuleError('NO_ACCOUNT_LINK', '当前没有已确认的账号关联', 409)
        old = conn.execute("SELECT * FROM account_link_appeals WHERE appellant_user_id=? AND group_id=? AND status='pending'", (uid, group['id'])).fetchone()
        if old:
            return {**dict(old), 'duplicate': True}
        cur = conn.execute('INSERT INTO account_link_appeals(group_id,appellant_user_id,reason,created_at) VALUES (?,?,?,?)', (group['id'], uid, reason.strip(), _iso(now)))
        conn.execute("UPDATE account_link_groups SET status='appealed',updated_at=? WHERE id=?", (_iso(now), group['id']))
        conn.execute("UPDATE account_link_decisions SET state='appealed',updated_at=? WHERE group_id=? AND (user_id_low=? OR user_id_high=?) AND state='confirmed'", (_iso(now), group['id'], uid, uid))
        return dict(conn.execute('SELECT * FROM account_link_appeals WHERE id=?', (cur.lastrowid,)).fetchone())


def _unlink_conn(conn, actor, uid, starting_reputation, reason, now):
    if type(starting_reputation) is not int or not 0 <= starting_reputation <= 100:
        raise IntegrityRuleError('INVALID_REPUTATION', '解除关联时必须明确指定0至100的起始信誉')
    group = _group(conn, uid)
    if not group:
        raise IntegrityRuleError('NO_ACCOUNT_LINK', '该账号没有已确认关联', 409)
    gid = group['id']
    old = {'group_id': gid, 'members': _members(conn, gid), 'reputation': group['reputation']}
    conn.execute("UPDATE account_link_members SET status='removed',removed_at=? WHERE group_id=? AND user_id=?", (_iso(now), gid, uid))
    conn.execute("UPDATE account_link_decisions SET state='dismissed',updated_at=? WHERE group_id=? AND (user_id_low=? OR user_id_high=?)", (_iso(now), gid, uid, uid))
    # Keep mirrored reputation until the explicit adjustment is journalled.
    _change_conn(conn, uid, starting_reputation-int(_user(conn,uid)['reputation']), 'account_unlinked',
                 f'reputation:unlink:{gid}:{uid}:{now.timestamp()}:{conn.total_changes}', now,
                 metadata={'staff_user_id': actor, 'reason': reason, 'previous_group_id': gid})
    remaining = _members(conn, gid)
    if len(remaining) < 2:
        conn.execute("UPDATE account_link_members SET status='removed',removed_at=? WHERE group_id=? AND status='active'", (_iso(now), gid))
        conn.execute("UPDATE account_link_groups SET status='dismissed',closed_at=?,updated_at=? WHERE id=?", (_iso(now), _iso(now), gid))
    # Direct staff separation also settles pending appeals for accounts no longer
    # linked; otherwise the UI leaves an appeal that can never be resolved.
    pending = conn.execute("SELECT id,appellant_user_id FROM account_link_appeals WHERE group_id=? AND status='pending'", (gid,)).fetchall()
    for appeal in pending:
        if appeal['appellant_user_id'] == uid or len(remaining) < 2:
            conn.execute("UPDATE account_link_appeals SET status='accepted',resolved_at=?,resolved_by=?,resolution_note=? WHERE id=?", (_iso(now),str(actor),reason,appeal['id']))
            _link_admin_audit(conn,actor,gid,'resolve_appeal',reason,{'appeal_id':appeal['id'],'status':'pending'},{'status':'accepted','via':'unlink'},now)
    if not conn.execute("SELECT 1 FROM account_link_appeals WHERE group_id=? AND status='pending'", (gid,)).fetchone():
        conn.execute("UPDATE account_link_groups SET status='confirmed',updated_at=? WHERE id=? AND status='appealed'", (_iso(now),gid))
        conn.execute("UPDATE account_link_decisions SET state='confirmed',updated_at=? WHERE group_id=? AND state='appealed'", (_iso(now),gid))
    _link_admin_audit(conn, actor, gid, 'unlink', reason, old, {'removed_user_id':uid,'starting_reputation':starting_reputation,'members':remaining}, now)
    return profile_conn(conn, uid)


def admin_unlink_account(actor_id, user_id, starting_reputation, reason, *, now=None):
    actor, uid, now = _id(actor_id), _id(user_id), _time(now)
    if not isinstance(reason,str) or not 1 <= len(reason.strip()) <= 500:
        raise IntegrityRuleError('INVALID_REASON', '必须填写解除关联的理由')
    with _transaction() as conn:
        _staff(conn, actor)
        return _unlink_conn(conn, actor, uid, starting_reputation, reason.strip(), now)


def resolve_account_link_appeal(actor_id, appeal_id, accepted, reason, *, starting_reputation=None, now=None):
    actor, aid, now = _id(actor_id), _id(appeal_id), _time(now)
    if type(accepted) is not bool or not isinstance(reason,str) or not 1 <= len(reason.strip()) <= 500:
        raise IntegrityRuleError('INVALID_RESOLUTION', '申诉处理参数无效')
    with _transaction() as conn:
        _staff(conn, actor)
        appeal = conn.execute('SELECT * FROM account_link_appeals WHERE id=?', (aid,)).fetchone()
        if not appeal:
            raise IntegrityRuleError('APPEAL_NOT_FOUND','申诉不存在',404)
        if appeal['status']!='pending':
            raise IntegrityRuleError('APPEAL_CLOSED','申诉已经处理',409)
        if accepted:
            _unlink_conn(conn, actor, appeal['appellant_user_id'], starting_reputation, reason.strip(), now)
        status = 'accepted' if accepted else 'rejected'
        conn.execute('UPDATE account_link_appeals SET status=?,resolved_at=?,resolved_by=?,resolution_note=? WHERE id=?', (status,_iso(now),str(actor),reason.strip(),aid))
        if not conn.execute("SELECT 1 FROM account_link_appeals WHERE group_id=? AND status='pending'",(appeal['group_id'],)).fetchone():
            conn.execute("UPDATE account_link_groups SET status='confirmed',updated_at=? WHERE id=? AND status='appealed'",(_iso(now),appeal['group_id']))
            conn.execute("UPDATE account_link_decisions SET state='confirmed',updated_at=? WHERE group_id=? AND state='appealed'",(_iso(now),appeal['group_id']))
        if not accepted:  # Acceptance is already audited by the unlink transaction.
            _link_admin_audit(conn,actor,appeal['group_id'],'resolve_appeal',reason.strip(),{'appeal_id':aid,'status':'pending'},{'status':status},now)
        return dict(conn.execute('SELECT * FROM account_link_appeals WHERE id=?',(aid,)).fetchone())


def admin_merge_accounts(actor_id, user_ids, reason, *, now=None):
    actor, now = _id(actor_id), _time(now)
    if not isinstance(user_ids,list) or not 2 <= len(user_ids) <= 10:
        raise IntegrityRuleError('INVALID_MEMBERS','请选择2至10个账号')
    ids=sorted({_id(uid) for uid in user_ids})
    if len(ids)<2 or not isinstance(reason,str) or not 1<=len(reason.strip())<=500:
        raise IntegrityRuleError('INVALID_REASON','必须提供明确的关联证据')
    with _transaction() as conn:
        _staff(conn,actor)
        gid=_merge_group_conn(conn,ids,100,now,explicit=True)
        for index,low in enumerate(ids):
            for high in ids[index+1:]:
                _recompute_pair_conn(conn,low,high,now)
                conn.execute("UPDATE account_link_decisions SET state='confirmed',group_id=?,risk_score=MAX(risk_score,100),reasons_json=?,updated_at=? WHERE user_id_low=? AND user_id_high=?",(gid,_json([{'code':'staff_evidence','points':100}]),_iso(now),low,high))
        _link_admin_audit(conn,actor,gid,'merge',reason.strip(),{}, {'members':_members(conn,gid)},now)
        return {'group_id':gid,'members':_members(conn,gid)}


def list_account_link_cases(actor_id):
    with closing(db.get_db_connection()) as conn:
        _staff(conn,_id(actor_id))
        cases=[]
        for row in conn.execute('''SELECT d.*,a.username AS low_name,b.username AS high_name FROM account_link_decisions d
            JOIN users a ON a.id=d.user_id_low JOIN users b ON b.id=d.user_id_high
            WHERE d.state!='none' ORDER BY d.updated_at DESC LIMIT 200'''):
            cases.append({k:row[k] for k in ('user_id_low','user_id_high','low_name','high_name','state','risk_score','group_id','updated_at')} |
                         {'reasons':json.loads(row['reasons_json']),'categories':json.loads(row['categories_json'])})
        appeals=[dict(r) for r in conn.execute("SELECT * FROM account_link_appeals WHERE status='pending' ORDER BY id LIMIT 100")]
        return {'cases':cases,'appeals':appeals}


def get_account_integrity_center(user_id, *, now=None):
    uid, now = _id(user_id), _time(now)
    recover_reputation_daily(user_id=uid, now=now)
    reports = list_team_reports(uid, now=now)
    with closing(db.get_db_connection()) as conn:
        profile = profile_conn(conn, uid)
        group = _group(conn, uid)
        ledger = [dict(row) for row in conn.execute('''SELECT delta,value_before,value_after,reason_code,created_at
            FROM reputation_ledger WHERE user_id=? OR link_group_id=? ORDER BY id DESC LIMIT 30''', (uid, group['id'] if group else None))]
        reportable = []
        for row in conn.execute("""SELECT id FROM matches WHERE mode='2v2' AND ended_at>=? AND ended_at<=?
            AND EXISTS (SELECT 1 FROM json_each(matches.player_ids_json) participant WHERE CAST(participant.value AS INTEGER)=?)
            ORDER BY id DESC LIMIT 100""", (_iso(now-timedelta(minutes=10)),_iso(now),uid)):
            try:
                match_row, summary, teams = _match(conn,row['id'])
            except IntegrityRuleError:
                continue
            own = next((team for team in teams if uid in team), None)
            if own:
                teammate = next(member for member in own if member != uid)
                target = _user(conn,teammate)
                reportable.append({'match_id':row['id'],'ended_at':match_row['ended_at'],
                    'target_user_id':teammate,'target_name':target['username']})
        role=conn.execute('SELECT role_type FROM user_roles WHERE user_id=?',(uid,)).fetchone()
        return {'profile':profile,'ledger':ledger,'reports':reports,'reportable_matches':reportable,
                'is_staff':bool(role and role['role_type'] in ('staff','admin'))}
