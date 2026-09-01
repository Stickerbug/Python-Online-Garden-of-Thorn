from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json

import pytest

import db
import account_integrity as integrity
import pvp_economy as economy


NOW=datetime(2026,9,1,4,tzinfo=timezone.utc)


@pytest.fixture
def accounts(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'DB_PATH',str(tmp_path/'economy.sqlite3'))
    db.init_db()
    with db.get_db_connection() as conn:
        for uid in range(1,9):
            conn.execute('''INSERT INTO users(id,username,username_lower,password_hash,created_at,gr_season_id)
                VALUES (?,?,?,?,?,?)''',(uid,f'eco{uid}',f'eco{uid}','unused',integrity._iso(NOW),db.current_gr_season()['id']))
            integrity.initialize_user_conn(conn,uid,NOW)
        conn.commit()


def game(ids=(1,2),win=0,*,key=None,early=False,ranked=False,day=0):
    mode='2v2' if len(ids)==4 else '1v1'
    teams=[[0,1],[2,3]] if len(ids)==4 else [[0],[1]]
    ended=NOW+timedelta(days=day)
    data={'mode':mode,'match_type':'ranked' if ranked else 'casual',
          'match_mode':f'{"ranked" if ranked else "casual"}_{mode}','player_ids':list(ids),
          'players':[f'eco{uid}' for uid in ids],'teams':teams,'winner_index':win,
          'winner_user_ids':[] if win==-1 else [ids[index] for index in teams[win]],
          'result':'draw' if win==-1 else 'win','valid_for_stats':True,'valid_for_ranking':ranked,
          'started_at':integrity._iso(ended-timedelta(seconds=10 if early else 300)),
          'ended_at':integrity._iso(ended),'duration_seconds':10 if early else 300,'ended_by_surrender':early}
    if key: data['match_key']=key
    return db.save_match_summary(data),data


def profile(uid):
    with db.get_db_connection() as conn:
        return economy.profile_conn(conn,uid)


def award(ids=(1,2),win=0,**kwargs):
    mid,data=game(ids,win,**kwargs)
    return db.award_match_thorn_dew(mid,data,award_time=data['ended_at'])


def balances():
    with db.get_db_connection() as conn:
        return [row[0] for row in conn.execute('SELECT thorn_dew_free FROM users ORDER BY id')]


@pytest.mark.parametrize('ranked',[True,False])
@pytest.mark.parametrize('ids',[(1,2),(1,2,3,4)])
def test_newcomer_base_rewards_and_no_title_double_multiplier(accounts,ids,ranked):
    result=award(ids,ranked=ranked)
    amounts={row['user_id']:row['amount'] for row in result['awarded']}
    assert amounts[1]==220  # (100 + first-win bonus 10) * 2, not *4.
    assert amounts[ids[-1]]==120
    assert profile(1)['valid_games']==1
    assert profile(1)['win_streak']==1


def test_bonus_tenth_game_and_title_twentieth_boundaries(accounts):
    for n in range(1,22):
        result=award(win=-1,day=n)
        assert result['awarded'][0]['amount']==(120 if n<=10 else 60)
        assert profile(1)['is_newcomer']==(n<20)
    assert profile(1)['title_remaining']==0


def test_win_streak_caps_and_draw_loss_reset(accounts):
    for n in range(12):
        result=award(day=n)
        assert result['awarded'][0]['streak_bonus']==min(n+1,10)*10
    award(win=-1,day=12)
    assert profile(1)['win_streak']==0
    assert award(day=13)['awarded'][0]['streak_bonus']==10
    award(win=1,day=14)
    assert profile(1)['win_streak']==0


def test_early_surrender_no_rewards_and_breaks_loser_streak(accounts):
    award()
    before=balances()
    result=award(win=1,early=True)
    assert result=={'awarded':[],'skipped':'early_surrender'}
    assert balances()==before
    assert profile(1)['win_streak']==0
    assert profile(2)['win_streak']==0


@pytest.mark.parametrize('value,amount',[(60,220),(59,110),(40,110),(39,0)])
def test_reputation_applies_after_all_bonuses(accounts,value,amount):
    integrity.change_reputation(1,value-85,'test','set',now=NOW)
    assert award()['awarded'][0]['amount']==amount


def test_reconnect_retry_conflict_and_concurrent_settlement(accounts):
    mid,data=game(key='server-room:4:2')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:db.award_match_thorn_dew(mid,data,award_time=data['ended_at']),range(2)))
    assert sorted(bool(r.get('duplicate')) for r in results)==[False,True]
    assert balances()[:2]==[220,120]
    assert profile(1)['valid_games']==1
    duplicate_mid=db.save_match_summary(data)
    assert db.award_match_thorn_dew(duplicate_mid,data)['duplicate']
    assert db.award_match_thorn_dew(mid,{**data,'winner_user_ids':[2]})['skipped']=='settlement_conflict'
    assert profile(1)['win_streak']==1


def test_two_vs_two_counts_real_opponents_not_teammates(accounts):
    for n in range(8):
        # Same opponent, alternating our teammate and their teammate.
        result=award((1,2 if n%2 else 5,3,4 if n%2 else 6),win=-1)
        assert result['awarded'][0]['multiplier']==1
    assert award((1,7,3,8),win=-1)['awarded'][0]['multiplier']==.8


def test_confirmed_secondary_loses_newcomer_but_suspected_does_not(accounts):
    for uid in (1,2):
        integrity.record_identity_event(uid,'a'*64,'b'*64,now=NOW)
    assert profile(2)['reward_multiplier']==2
    for day in (1,2):
        for uid in (1,2):
            integrity.record_identity_event(uid,'a'*64,'b'*64,now=NOW+timedelta(days=day))
    assert profile(1)['reward_multiplier']==2
    assert profile(2)['linked_secondary']
    assert not profile(2)['is_newcomer']
    assert profile(2)['reward_multiplier']==1
    assert profile(2)['protected_ranked_remaining']==0
    assert award((1,2))['awarded'][0]['amount']==0


def test_first_three_ranked_losses_protected_and_preview_agrees(accounts):
    for n in range(4):
        preview=db.preview_gr_match_result('1v1',[1,2],viewer_user_id=2)
        assert (preview['viewer']['loss_delta']==0)==(n<3)
        mid,data=game(ranked=True,day=n)
        result=db.apply_gr_match_result(mid,data)
        assert (result['season_deltas']['2']==0)==(n<3)
        assert (result['total_deltas']['2']==0)==(n<3)
        assert (2 in result['newcomer_protected_user_ids'])==(n<3)
        db.apply_gr_match_result(mid,data)
        assert profile(2)['ranked_games']==n+1


def test_ranked_two_vs_two_protects_each_newcomer(accounts):
    mid,data=game((1,2,3,4),ranked=True)
    result=db.apply_gr_match_result(mid,data)
    assert result['newcomer_protected_user_ids']==[3,4]
    assert result['season_deltas']['3']==result['season_deltas']['4']==0


def test_legacy_ranked_games_do_not_reset_protection(accounts):
    with db.get_db_connection() as conn:
        conn.execute("UPDATE users SET gr_season_id='S202608',total_ranked_games=25,games_played=30 WHERE id=2")
        conn.commit()
    db.ensure_current_gr_season([2])
    assert profile(2)['protected_ranked_remaining']==0
    assert not profile(2)['is_newcomer']


def test_preview_does_not_write_and_matches_actual_award(accounts):
    mid,data=game()
    before=balances()
    with db.get_db_connection() as conn:
        estimated=db._estimate_match_thorn_dew_awards_for_conn(conn,mid,data,award_time=data['ended_at'])
        assert conn.execute('SELECT COUNT(*) FROM pvp_reward_settlements').fetchone()[0]==0
    assert balances()==before
    assert db.award_match_thorn_dew(mid,data,award_time=data['ended_at'])==estimated


def test_failed_settlement_rolls_back_money_and_progress(accounts,monkeypatch):
    original=integrity.reward_amount_conn
    def fail_second(conn,uid,amount):
        if uid==2: raise RuntimeError('simulated failure')
        return original(conn,uid,amount)
    monkeypatch.setattr(integrity,'reward_amount_conn',fail_second)
    with pytest.raises(RuntimeError): award()
    assert balances()==[0]*8
    assert profile(1)['valid_games']==0
    with db.get_db_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM pvp_reward_settlements').fetchone()[0]==0


def test_old_currency_receipt_cannot_be_paid_again(accounts):
    mid,data=game()
    with db.get_db_connection() as conn:
        conn.execute("INSERT INTO user_currency_transactions(user_id,currency,free_delta,paid_delta,reason,source_type,source_id,balance_free_after,balance_paid_after,created_at) VALUES (1,'thorn_dew',45,0,'old','match_reward',?,45,0,?)",(f'match:{mid}:u:1:opp:old',integrity._iso(NOW)))
        conn.execute('UPDATE users SET thorn_dew_free=45 WHERE id=1')
        conn.commit()
    result=db.award_match_thorn_dew(mid,data)
    assert 1 not in [r['user_id'] for r in result['awarded']]
    assert balances()[0]==45


def test_guest_nickname_changes_use_one_repeat_bucket(accounts):
    for n in range(9):
        mid,data=game()
        data['player_ids']=[1,None]
        data['players']=['eco1',f'guest{n}']
        data['winner_user_ids']=[1]
        mid=db.save_match_summary(data)
        result=db.award_match_thorn_dew(mid,data,award_time=data['ended_at'])
        assert result['awarded'][0]['multiplier']==(1 if n<8 else .8)


def test_public_badge_has_no_private_newcomer_history(accounts):
    import app as gtn
    source={'nickname':'eco1','reputation_profile':integrity.get_reputation_profile(1)}
    fields=gtn.special_public_fields(source)
    assert fields['reputation_profile']['newcomer']=={'is_newcomer':True}
    serialized=json.dumps(fields)
    assert 'ranked_games' not in serialized
    assert 'linked_secondary' not in serialized


def test_system_newcomer_title_is_not_an_equipment_choice(accounts):
    payload,error=db.set_user_equipped_titles(1,[])
    assert error is None
    assert profile(1)['is_newcomer']
    _,error=db.set_user_equipped_titles(1,['system_newcomer'])
    assert error is not None
    assert profile(1)['is_newcomer']


def test_frontend_shows_newcomer_and_current_economy_rules():
    from pathlib import Path
    source=(Path(__file__).resolve().parents[1]/'static/js/game.js').read_text(encoding='utf-8')
    assert "profile?.newcomer?.is_newcomer === true" in source
    assert '20场后移除新人头衔' in source
    assert '胜利100，失败或平局60' in source


def test_rating_rebuild_keeps_original_newcomer_protection(accounts):
    mid,data=game(ranked=True)
    result=db.apply_gr_match_result(mid,data)
    assert result['season_deltas']['2']==0
    for _ in range(2):
        db.rebuild_gr_from_matches(dry_run=False)
        with db.get_db_connection() as conn:
            stored=json.loads(conn.execute('SELECT summary_json FROM matches WHERE id=?',(mid,)).fetchone()[0])
            assert stored['gr_result']['newcomer_protected_user_ids']==[2]
            assert stored['gr_result']['season_deltas']['2']==0
