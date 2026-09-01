import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

import account_integrity as integrity
import db


NOW = datetime(2026, 9, 1, 4, tzinfo=timezone.utc)


@pytest.fixture
def accounts(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'integrity.sqlite3'))
    db.init_db()
    with db.get_db_connection() as conn:
        for uid in range(1, 11):
            conn.execute('INSERT INTO users(id,username,username_lower,password_hash,created_at) VALUES (?,?,?,?,?)',
                         (uid, f'user{uid}', f'user{uid}', 'unused', integrity._iso(NOW)))
            integrity.initialize_user_conn(conn, uid, NOW)
        conn.execute("INSERT INTO user_roles(user_id,role_type,role_key,title,color,sort_order,can_direct_friend,chat_exempt,visible,created_at,updated_at) VALUES (10,'staff','staff','','neutral',1,0,0,1,?,?)", (integrity._iso(NOW),integrity._iso(NOW)))
        conn.commit()
    return list(range(1, 11))


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def identify(uid, day=0, device='shared', network='home', source='login'):
    return integrity.record_identity_event(uid, digest(device), digest(network), source=source, now=NOW+timedelta(days=day))


def link_pair():
    for day in range(3):
        identify(1, day)
        identify(2, day)


def match(ended=NOW, ranked=True):
    return db.save_match_summary({'mode':'2v2','match_type':'ranked' if ranked else 'casual',
        'player_ids':[1,2,3,4],'players':['a','b','c','d'],'teams':[[0,1],[2,3]],
        'started_at':integrity._iso(ended-timedelta(minutes=5)), 'ended_at':integrity._iso(ended),
        'duration_seconds':300,'result':'win','winner_index':0})


def test_initialization_and_immutable_business_id(accounts):
    assert integrity.get_reputation_profile(1)['value'] == 85
    first = integrity.change_reputation(1,-5,'test','test:1',now=NOW)
    again = integrity.change_reputation(1,-5,'test','test:1',now=NOW+timedelta(hours=1))
    assert first['value_after'] == again['value_after'] == 80
    assert again['duplicate']
    with pytest.raises(integrity.IntegrityRuleError, match='不一致'):
        integrity.change_reputation(1,-2,'test','test:1',now=NOW)
    integrity.change_reputation(1,100,'test','max',now=NOW)
    assert integrity.get_reputation_profile(1)['value'] == 100
    with db.get_db_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM reputation_ledger WHERE business_id='test:1'").fetchone()[0] == 1


@pytest.mark.parametrize('value,level,ranked,achievements,multiplier',[
    (80,'normal',True,True,1),(79,'yellow',True,True,1),(60,'yellow',True,True,1),
    (59,'orange',True,False,.5),(40,'orange',True,False,.5),(39,'red',False,False,0)])
def test_thresholds_and_reward_scaling(accounts,value,level,ranked,achievements,multiplier):
    integrity.change_reputation(1,value-85,'test','set',now=NOW)
    profile=integrity.get_reputation_profile(1)
    assert (profile['level'],profile['can_ranked'],profile['can_achievements'],profile['dew_multiplier']) == (level,ranked,achievements,multiplier)
    with db.get_db_connection() as conn:
        assert integrity.reward_amount_conn(conn,1,45) == int(45*multiplier)
        definition=next(d for d in db.ACHIEVEMENT_DEFS if int(d.get('target') or 1)==1)
        result=db._unlock_achievement_conn(conn,1,definition['id'])
        assert bool(result) == achievements


def test_daily_recovery_beijing_boundary_and_under40_exception(accounts):
    integrity.change_reputation(1,-55,'test','low',now=NOW)
    # Sep 2 00:00 Beijing: yesterday had a penalty, so no recovery.
    assert integrity.recover_reputation_daily(user_id=1,now=datetime(2026,9,1,16,tzinfo=timezone.utc)) == []
    assert integrity.recover_reputation_daily(user_id=1,now=datetime(2026,9,2,15,59,59,tzinfo=timezone.utc)) == []
    result=integrity.recover_reputation_daily(user_id=1,now=datetime(2026,9,2,16,tzinfo=timezone.utc))
    assert len(result)==1 and result[0]['value_after']==35
    assert integrity.recover_reputation_daily(user_id=1,now=datetime(2026,9,2,16,tzinfo=timezone.utc)) == []
    integrity.recover_reputation_daily(user_id=1,now=NOW+timedelta(days=8))
    assert integrity.get_reputation_profile(1)['value']==40
    assert integrity.recover_reputation_daily(user_id=2,now=NOW+timedelta(days=8)) == []


def test_daily_recovery_requires_ranked_participation(accounts):
    with db.get_db_connection() as conn:
        conn.execute('''INSERT INTO gr_match_results(season_id,played_at,participant_ids_json,team_a_ids_json,team_b_ids_json,total_deltas_json,season_deltas_json,before_json,after_json)
            VALUES ('R1',?,'[1,2]','[1]','[2]','{}','{}','{}','{}')''',(integrity._iso(NOW),))
        conn.commit()
    integrity.recover_reputation_daily(now=NOW+timedelta(days=1))
    assert integrity.get_reputation_profile(1)['value']==90
    assert integrity.get_reputation_profile(3)['value']==85


def test_casual_penalty_cap(accounts):
    integrity.apply_match_penalty(1,'consecutive_timeouts','casual',ranked=False,now=NOW)
    integrity.apply_match_penalty(2,'consecutive_timeouts','ranked',ranked=True,now=NOW)
    assert integrity.get_reputation_profile(1)['value']==84
    assert integrity.get_reputation_profile(2)['value']==80


@pytest.mark.parametrize('ranked,penalty',[(True,5),(False,1)])
def test_teammate_report_permissions_confirm_revoke(accounts,ranked,penalty):
    mid=match(ranked=ranked)
    with pytest.raises(integrity.IntegrityRuleError):
        integrity.create_team_report(1,mid,3,'bad',now=NOW)
    report=integrity.create_team_report(1,mid,2,'挂机',now=NOW+timedelta(minutes=10))
    with pytest.raises(integrity.IntegrityRuleError):
        integrity.mutate_team_report(1,report['id'],'confirm',now=NOW+timedelta(minutes=11))
    assert integrity.list_team_reports(3,now=NOW+timedelta(minutes=11))[0]['can_confirm']
    integrity.mutate_team_report(3,report['id'],'confirm',now=NOW+timedelta(minutes=11))
    assert integrity.mutate_team_report(4,report['id'],'confirm',now=NOW+timedelta(minutes=12))['duplicate']
    assert integrity.get_reputation_profile(2)['value']==85-penalty
    with pytest.raises(integrity.IntegrityRuleError):
        integrity.revoke_team_report(1,report['id'],'bad',now=NOW)
    integrity.revoke_team_report(10,report['id'],'确认误报',now=NOW+timedelta(hours=1))
    assert integrity.get_reputation_profile(2)['value']==85
    assert integrity.revoke_team_report(10,report['id'],'确认误报',now=NOW+timedelta(hours=1))['duplicate']


def test_report_expiry_withdraw_and_windows(accounts):
    mid=match()
    with pytest.raises(integrity.IntegrityRuleError):
        integrity.create_team_report(1,mid,2,'late',now=NOW+timedelta(seconds=601))
    report=integrity.create_team_report(1,mid,2,'test',now=NOW)
    assert integrity.expire_team_reports(now=NOW+timedelta(hours=24))==1
    assert integrity.expire_team_reports(now=NOW+timedelta(hours=24))==0
    with pytest.raises(integrity.IntegrityRuleError):
        integrity.mutate_team_report(3,report['id'],'confirm',now=NOW+timedelta(hours=24))
    mid=match()
    report=integrity.create_team_report(1,mid,2,'test',now=NOW)
    integrity.mutate_team_report(1,report['id'],'withdraw',now=NOW)
    with pytest.raises(integrity.IntegrityRuleError):
        integrity.mutate_team_report(3,report['id'],'confirm',now=NOW)


def test_automatic_link_needs_independent_signals_and_shares_reputation(accounts):
    for day in range(3):
        identify(1,day,network='a')
        identify(2,day,network='b')
    assert not integrity.get_reputation_profile(1)['linked']
    assert integrity.get_reputation_profile(1)['link_state']=='probable'
    for day in range(3):
        identify(1,day,network='home')
        identify(2,day,network='home')
    assert integrity.get_reputation_profile(1)['linked']
    assert integrity.get_reputation_profile(1)['linked_gr_band']=={'min':1000,'max':1049,'label':'1000–1049'}
    integrity.change_reputation(1,-5,'test','group-penalty',now=NOW+timedelta(days=3))
    assert integrity.get_reputation_profile(1)['value']==integrity.get_reputation_profile(2)['value']==80
    with db.get_db_connection() as conn:
        row=conn.execute("SELECT * FROM reputation_ledger WHERE business_id='group-penalty'").fetchone()
        assert row['user_id'] is None and row['link_group_id'] is not None
    assert integrity.recompute_account_links(1,now=NOW+timedelta(days=3))[0]['duplicate']


def test_campus_network_alone_never_confirms(accounts):
    for day in range(3):
        for uid in accounts:
            identify(uid,day,device=f'own-{uid}',network='campus',source='register' if day==0 else 'login')
    for uid in accounts:
        integrity.recompute_account_links(uid,now=NOW+timedelta(days=2))
        assert not integrity.get_reputation_profile(uid)['linked']
    with db.get_db_connection() as conn:
        assert conn.execute('SELECT MAX(risk_score) FROM account_link_decisions').fetchone()[0] <= 5


def test_no_raw_identity_and_idempotent_recompute(accounts):
    with pytest.raises(integrity.IntegrityRuleError):
        integrity.record_identity_event(1,'token','192.0.2.1',now=NOW)
    identify(1)
    identify(2)
    with db.get_db_connection() as conn:
        before=conn.execute('SELECT COUNT(*) FROM account_link_decision_audit').fetchone()[0]
    assert not identify(2)
    integrity.recompute_account_links(2,now=NOW)
    with db.get_db_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM account_link_decision_audit').fetchone()[0]==before


def test_appeal_unlink_requires_staff_and_survives_login(accounts):
    link_pair()
    appeal=integrity.appeal_account_link(1,'家庭共用设备',now=NOW+timedelta(days=3))
    assert integrity.get_reputation_profile(1)['link_state']=='appealed'
    assert integrity.appeal_account_link(1,'再次说明',now=NOW+timedelta(days=3))['duplicate']
    with pytest.raises(integrity.IntegrityRuleError):
        integrity.resolve_account_link_appeal(2,appeal['id'],True,'no',starting_reputation=85,now=NOW)
    integrity.resolve_account_link_appeal(10,appeal['id'],True,'核实独立玩家',starting_reputation=85,now=NOW+timedelta(days=4))
    identify(1,5)
    identify(2,5)
    assert not integrity.get_reputation_profile(1)['linked']
    with db.get_db_connection() as conn:
        assert conn.execute('SELECT state FROM account_link_decisions WHERE user_id_low=1 AND user_id_high=2').fetchone()[0]=='dismissed'
        assert conn.execute('SELECT COUNT(*) FROM account_link_admin_audit').fetchone()[0]==2


def test_manual_merge_and_reputation_not_client_controlled(accounts):
    with pytest.raises(integrity.IntegrityRuleError):
        integrity.admin_merge_accounts(1,[1,2],'evidence',now=NOW)
    result=integrity.admin_merge_accounts(10,[1,2],'明确证据',now=NOW)
    assert result['members']==[1,2]
    assert integrity.get_reputation_profile(2)['linked']
    with pytest.raises(integrity.IntegrityRuleError):
        integrity.admin_unlink_account(10,1,True,'reason',now=NOW)


def test_new_registration_has_initial_ledger(accounts):
    user,error=db.create_user('NewPlayer','Good-password-42')
    assert error is None
    with db.get_db_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM reputation_ledger WHERE business_id=?',(f'reputation:init:user:{user["id"]}',)).fetchone()[0]==1


def test_shared_computer_and_rating_still_need_behavior_on_campus(accounts):
    with db.get_db_connection() as conn:
        conn.execute('UPDATE users SET total_ranked_games=1 WHERE id=1')
        conn.execute('UPDATE users SET total_ranked_games=20 WHERE id=2')
        conn.commit()
    for day in range(3):
        for uid in accounts:
            identify(uid,day,device='shared-lab-browser',network='campus')
    for uid in accounts:
        integrity.recompute_account_links(uid,now=NOW+timedelta(days=2))
        assert not integrity.get_reputation_profile(uid)['linked']


def test_zero_reputation_violation_still_blocks_daily_recovery(accounts):
    integrity.change_reputation(1,-85,'test','zero',now=NOW)
    integrity.recover_reputation_daily(user_id=1,now=NOW+timedelta(days=1))
    integrity.apply_match_penalty(1,'early_surrender','at-zero',now=NOW+timedelta(days=1))
    assert integrity.recover_reputation_daily(user_id=1,now=NOW+timedelta(days=2)) == []


def test_group_recovery_is_once_and_merged_day_deduction_is_preserved(accounts):
    integrity.change_reputation(1,-55,'test','low',now=NOW)
    integrity.admin_merge_accounts(10,[1,2],'evidence',now=NOW)
    integrity.recover_reputation_daily(now=NOW+timedelta(days=1))
    assert integrity.get_reputation_profile(2)['value']==30
    integrity.recover_reputation_daily(now=NOW+timedelta(days=2))
    assert integrity.get_reputation_profile(2)['value']==35


def test_api_permissions_strict_body_and_no_private_identity(accounts,monkeypatch):
    import app as gtn
    monkeypatch.setattr(gtn,'DB_AVAILABLE',True)
    monkeypatch.setattr(gtn,'rate_limiter',lambda *a,**kw:True)
    monkeypatch.setattr(gtn,'_get_ip_ban_status_cached',lambda ip:{'banned':False})
    identity={'id':1}
    monkeypatch.setattr(gtn,'_require_account_json',lambda:(identity['id'],f'user{identity["id"]}',None))
    monkeypatch.setattr(gtn.socketio,'start_background_task',lambda *a,**kw:None)
    client=gtn.app.test_client()
    mid=match(ended=datetime.now(timezone.utc))
    response=client.post('/api/account-integrity/team-reports',json={'match_id':mid,'target_user_id':2,'reason':'挂机','actor_user_id':3})
    assert response.status_code==400
    response=client.post('/api/account-integrity/team-reports',json={'match_id':mid,'target_user_id':2,'reason':'挂机'})
    assert response.status_code==200
    rid=response.json['report']['id']
    assert client.post(f'/api/account-integrity/team-reports/{rid}/confirm',json={}).status_code==403
    identity['id']=3
    assert client.post(f'/api/account-integrity/team-reports/{rid}/confirm',json={}).status_code==200
    assert client.get('/api/account-integrity/staff').status_code==403
    assert client.post('/api/account-integrity/staff/merge',json={'user_ids':[1,2],'reason':'forged'}).status_code==403
    identity['id']=10
    assert client.get('/api/account-integrity/staff').status_code==200
    response=client.get('/api/account-integrity')
    serialized=response.get_data(as_text=True)
    assert response.headers['Cache-Control']=='private, no-store'
    for forbidden in ('device_hash','network_hash','input_fingerprint','highest_total_gr','password_hash'):
        assert forbidden not in serialized
    assert client.post('/api/account-integrity/appeal',json={'reason':'x'},headers={'Origin':'https://evil.invalid'}).status_code==403


def test_signed_device_cookie_reuses_only_valid_server_token(accounts,monkeypatch):
    import app as gtn
    monkeypatch.setenv('GTN_ACCOUNT_LINK_HMAC_KEY','test-only-not-a-real-secret')
    calls=[]
    monkeypatch.setattr(integrity,'record_identity_event',lambda *args,**kwargs:calls.append((args,kwargs)))
    def prepare(cookie=''):
        with gtn.app.test_request_context('/api/auth/me',base_url='https://game.test',headers={'Cookie':f'gtn_device={cookie}'},environ_base={'REMOTE_ADDR':'192.0.2.1'}):
            gtn._prepare_account_identity({'id':1},'session')
            response=gtn._attach_account_device_cookie(gtn.jsonify({'ok':True}))
            return response.headers['Set-Cookie'].split(';')[0].split('=',1)[1],response.headers['Set-Cookie']
    cookie,header=prepare('attacker-controlled.invalid')
    same,_=prepare(cookie)
    changed,_=prepare(cookie[:-1] + ('a' if cookie[-1]!='a' else 'b'))
    assert same==cookie and changed!=cookie
    assert 'HttpOnly' in header and 'Secure' in header and 'SameSite=Lax' in header
    assert calls[0][0][1]==calls[1][0][1]
    assert all(len(call[0][i])==64 for call in calls for i in (1,2))
    assert '192.0.2.1' not in str(calls)


def test_ranked_gate_reads_database_not_client_reputation(accounts,monkeypatch):
    import app as gtn
    monkeypatch.setattr(gtn,'DB_AVAILABLE',True)
    integrity.change_reputation(1,-46,'test','below40',now=NOW)
    metadata={'user_id':1,'is_registered_user':True,'reputation':100,'mod_source':'official'}
    assert gtn.ranked_match_eligibility([metadata])==(False,'low_reputation')


def test_concurrent_same_penalty_and_report_only_apply_once(accounts):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:integrity.apply_match_penalty(1,'early_surrender','same',ranked=True,now=NOW),range(2)))
    assert sorted(r['duplicate'] for r in results)==[False,True]
    assert integrity.get_reputation_profile(1)['value']==83
    report=integrity.create_team_report(1,match(),2,'test',now=NOW)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda uid:integrity.mutate_team_report(uid,report['id'],'confirm',now=NOW),[3,4]))
    assert sorted(r.get('duplicate',False) for r in results)==[False,True]
    assert integrity.get_reputation_profile(2)['value']==80


def test_direct_unlink_resolves_appeals_and_restores_remaining_group(accounts):
    integrity.admin_merge_accounts(10,[1,2,3],'evidence',now=NOW)
    appeal=integrity.appeal_account_link(1,'shared browser',now=NOW)
    integrity.admin_unlink_account(10,1,85,'verified separate person',now=NOW)
    assert not integrity.get_reputation_profile(1)['linked']
    assert integrity.get_reputation_profile(2)['link_state']=='confirmed'
    with db.get_db_connection() as conn:
        assert conn.execute('SELECT status FROM account_link_appeals WHERE id=?',(appeal['id'],)).fetchone()[0]=='accepted'


def test_report_confirmation_window_starts_at_match_end(accounts):
    report=integrity.create_team_report(1,match(),2,'test',now=NOW+timedelta(minutes=9))
    with pytest.raises(integrity.IntegrityRuleError, match='24小时'):
        integrity.mutate_team_report(3,report['id'],'confirm',now=NOW+timedelta(hours=24))


def test_report_list_scopes_before_global_limit(accounts):
    own=integrity.create_team_report(1,match(),2,'own',now=NOW)
    with db.get_db_connection() as conn:
        for i in range(305):
            mid=db.save_match_summary({'mode':'2v2','match_type':'casual','player_ids':[5,6,7,8],
                'players':['e','f','g','h'],'teams':[[0,1],[2,3]],'started_at':integrity._iso(NOW),
                'ended_at':integrity._iso(NOW),'duration_seconds':300,'result':'win'})
            # Separate write transactions avoid holding a connection lock while saving matches.
            integrity.create_team_report(5,mid,6,'unrelated',now=NOW)
    assert integrity.list_team_reports(3,now=NOW)[0]['id']==own['id']


def test_reputation_failure_does_not_replace_existing_socket(accounts,monkeypatch):
    import app as gtn
    from unittest.mock import patch
    with (patch.object(gtn,'_current_account_user',return_value={'id':1,'username':'user1'}),
          patch.object(gtn,'rate_limiter',return_value=True),
          patch.object(integrity,'get_reputation_profile',side_effect=RuntimeError('offline'))):
        client=gtn.socketio.test_client(gtn.app)
        try:
            client.emit('login',{'nickname':'user1','account_login':True})
            events=client.get_received()
            assert any(event['name']=='login_fail' for event in events)
            assert not any(event['name']=='login_ok' for event in events)
        finally:
            if client.is_connected(): client.disconnect()
