"""Authoritative newcomer entitlements and atomic PvP reward settlement."""

import hashlib
import json
import math
import re
from datetime import datetime, timezone

import db
import account_integrity as integrity


def _account(conn, uid):
    row = integrity._user(conn, uid)
    progress = conn.execute('SELECT * FROM pvp_economy_accounts WHERE user_id=?',(uid,)).fetchone()
    valid = max(int(row['games_played'] or 0), int(progress['valid_games'] if progress else 0))
    ranked = int(row['total_ranked_games'] or 0)
    return row, valid, ranked, int(progress['win_streak'] if progress else 0)


def profile_conn(conn, uid):
    uid = integrity._id(uid)
    row, valid, ranked, streak = _account(conn,uid)
    group = integrity._group(conn,uid)
    primary = True
    if group:
        members = [_account(conn,member) for member in integrity._members(conn,group['id'])]
        if members:
            primary = uid == min(members,key=lambda entry:(str(entry[0]['created_at']),int(entry[0]['id'])))[0]['id']
            # One person's allowance is not multiplied by account count. Games
            # already played on any confirmed account consume the shared quota.
            valid = sum(entry[1] for entry in members)
            ranked = sum(entry[2] for entry in members)
    return {'is_newcomer':primary and valid<20,'valid_games':valid,'ranked_games':ranked,
            'reward_multiplier':2 if primary and valid<10 else 1,
            'protected_ranked_remaining':max(0,3-ranked) if primary else 0,
            'title_remaining':max(0,20-valid) if primary else 0,'win_streak':streak,
            'linked_secondary':not primary}


def protected_loss_conn(conn, uid):
    return profile_conn(conn,uid)['protected_ranked_remaining']>0


def _canonical_peer(conn, uid):
    if uid is None:
        return ('guest',0)  # Changing an unregistered nickname never resets repeat decay.
    group=integrity._group(conn,uid)
    return ('group',group['id']) if group else ('user',uid)


def _counts(conn,uid,opponents,start,end):
    group=integrity._group(conn,uid)
    members=integrity._members(conn,group['id']) if group else [uid]
    placeholders=','.join('?' for _ in members)
    rows=conn.execute(f'''SELECT opponent_ids_json FROM pvp_reward_participants
        WHERE user_id IN ({placeholders}) AND played_at>=? AND played_at<?''',(*members,start,end)).fetchall()
    peer_keys={_canonical_peer(conn,other) for other in opponents}
    repeats={key:0 for key in peer_keys}
    for row in rows:
        seen={_canonical_peer(conn,other) for other in json.loads(row['opponent_ids_json'])}
        for key in seen & peer_keys:
            repeats[key]+=1
    legacy=conn.execute(f'''SELECT user_id,source_id FROM user_currency_transactions
        WHERE user_id IN ({placeholders}) AND source_type='match_reward'
        AND source_id NOT LIKE '%:pvp-v1' AND created_at>=? AND created_at<?''',(*members,start,end)).fetchall()
    for receipt in legacy:
        match=re.match(r'match:([0-9]+):u:',receipt['source_id'] or '')
        if not match: continue
        stored=conn.execute('SELECT summary_json FROM matches WHERE id=?',(int(match.group(1)),)).fetchone()
        if not stored: continue
        summary=json.loads(stored['summary_json'] or '{}')
        ids=summary.get('player_ids') or []
        if receipt['user_id'] not in ids: continue
        teams=summary.get('teams') or ([[0,1],[2,3]] if len(ids)==4 else [[0],[1]])
        own=next((side for side,t in enumerate(teams) if ids.index(receipt['user_id']) in t),None)
        if own is None: continue
        seen={_canonical_peer(conn,ids[index]) for index in teams[1-own] if 0<=index<len(ids)}
        for key in seen & peer_keys: repeats[key]+=1
    return len(rows)+len(legacy),max(repeats.values(),default=0)


def _settlement_input(match_id,summary):
    mid=integrity._id(match_id)
    data=dict(summary or {})
    relevant={key:data.get(key) for key in ('mode','match_type','match_mode','player_ids','teams',
        'winner_user_ids','winner_index','result','valid_for_stats','valid_for_ranking',
        'ended_by_surrender','duration_seconds','started_at','ended_at')}
    fingerprint=hashlib.sha256(integrity._json(relevant).encode()).hexdigest()
    key=str(data.get('match_key') or f'match:{mid}')
    return mid,data,key,fingerprint


def settle_conn(conn,match_id,summary,award_time=None):
    """Caller owns an IMMEDIATE transaction; all money/progress commits together."""
    data=dict(summary or {})
    if data.get('result') not in ('win','draw'):
        return {'awarded':[],'skipped':'result'}
    if not data.get('valid_for_stats',data.get('valid_for_ranking',True)):
        return {'awarded':[],'skipped':data.get('ranking_invalid_reason') or 'not_valid'}
    early=bool(data.get('ended_by_surrender')) and int(data.get('duration_seconds') or 0)<60
    if early and not data.get('player_ids'):
        return {'awarded':[],'skipped':'early_surrender'}
    mid,data,key,fingerprint=_settlement_input(match_id,data)
    prior=conn.execute('SELECT * FROM pvp_reward_settlements WHERE settlement_key=? OR match_id=?',(key,mid)).fetchone()
    if prior:
        if prior['request_fingerprint']!=fingerprint:
            return {'awarded':[],'skipped':'settlement_conflict'}
        return {**json.loads(prior['result_json']),'duplicate':True}
    mode=str(data.get('mode') or '')
    if mode not in db.THORN_DEW_MODE_REWARDS:
        return {'awarded':[],'skipped':'unsupported_mode'}
    ids=data.get('player_ids') or []
    required=4 if mode=='2v2' else 2
    if len(ids)!=required or any(uid is not None and (type(uid) is not int or uid<=0) for uid in ids):
        return {'awarded':[],'skipped':'invalid_participants'}
    registered=[uid for uid in ids if uid is not None]
    if len(set(registered))!=len(registered):
        return {'awarded':[],'skipped':'duplicate_player'}
    if not registered:
        return {'awarded':[],'skipped':'no_registered'}
    stored=conn.execute('SELECT player_ids_json FROM matches WHERE id=?',(mid,)).fetchone()
    if not stored or json.loads(stored['player_ids_json'] or '[]')!=ids:
        return {'awarded':[],'skipped':'match_mismatch'}
    teams=data.get('teams') or ([[0,1],[2,3]] if required==4 else [[0],[1]])
    if (not isinstance(teams,list) or len(teams)!=2 or any(not isinstance(t,list) or len(t)!=required//2 for t in teams)
            or any(type(index) is not int for t in teams for index in t)
            or sorted(index for t in teams for index in t)!=list(range(required))):
        return {'awarded':[],'skipped':'invalid_teams'}
    is_draw=data['result']=='draw'
    winners=data.get('winner_user_ids') or []
    if any(type(uid) is not int or uid not in registered for uid in winners):
        return {'awarded':[],'skipped':'unknown_winner'}
    winner_side=data.get('winner_index')
    if winners:
        sides=[i for i,t in enumerate(teams) if set(winners).issubset({ids[index] for index in t})]
        if len(sides)!=1:
            return {'awarded':[],'skipped':'unknown_winner'}
        winner_side=sides[0]
    if not is_draw and (type(winner_side) is not int or winner_side not in (0,1)):
        return {'awarded':[],'skipped':'unknown_winner'}
    when=db._parse_utc_datetime(award_time) if award_time else datetime.now(timezone.utc)
    now=db.utc_iso(when)
    start,end=db._thorn_dew_day_bounds_utc(db._thorn_dew_date(when))
    awards=[]
    conn.execute('INSERT INTO pvp_reward_settlements VALUES (?,?,?,?,?)',(key,mid,fingerprint,'{}',now))
    for uid in registered:
        user,valid,_,streak=_account(conn,uid)
        own=next(i for i,t in enumerate(teams) if any(ids[index]==uid for index in t))
        opponents=[ids[index] for index in teams[1-own]]
        outcome='draw' if is_draw else 'win' if own==winner_side else 'loss'
        next_streak=0 if outcome!='win' else streak if early else min(streak+1,10)
        profile=profile_conn(conn,uid)
        daily_count,same_count=_counts(conn,uid,opponents,start,end)
        multiplier=min(db._thorn_dew_daily_multiplier(daily_count),db._thorn_dew_same_opponent_multiplier(same_count))
        base=100 if outcome=='win' else 60
        if mode not in ('1v1','2v2'):
            base=db.THORN_DEW_MODE_REWARDS[mode]+(db.THORN_DEW_WIN_BONUS if outcome=='win' else 0)
        streak_bonus=10*next_streak if outcome=='win' and not early else 0
        amount=math.floor((base+streak_bonus)*profile['reward_multiplier']*multiplier)
        amount=integrity.reward_amount_conn(conn,uid,amount)
        allowed=integrity.match_reward_allowed_conn(conn,uid,registered,int(data.get('duration_seconds') or 0),same_count)
        if early or not allowed:
            amount=0
            if outcome=='win': next_streak=streak
        # Preserve pre-P7 currency receipts: rollout must not issue an old match
        # again simply because its new settlement record does not exist yet.
        old_receipt=conn.execute("SELECT 1 FROM user_currency_transactions WHERE user_id=? AND source_type='match_reward' AND source_id LIKE ?",(uid,f'match:{mid}:u:{uid}:%')).fetchone()
        if old_receipt:
            continue
        conn.execute('''INSERT INTO pvp_economy_accounts VALUES (?,?,?,?) ON CONFLICT(user_id) DO UPDATE
            SET valid_games=excluded.valid_games,win_streak=excluded.win_streak''',(uid,valid+1,next_streak,now))
        free=max(0,int(user['thorn_dew_free'] or 0))+amount
        paid=max(0,int(user['thorn_dew_paid'] or 0))
        reason=f'有效对局奖励 {mode} {outcome}；基础{base} 连胜+{streak_bonus} 新人×{profile["reward_multiplier"]} 衰减×{multiplier:g}'
        source=f'match:{mid}:u:{uid}:pvp-v1'
        conn.execute('UPDATE users SET thorn_dew_free=? WHERE id=?',(free,uid))
        conn.execute('''INSERT INTO user_currency_transactions
            (user_id,currency,free_delta,paid_delta,reason,source_type,source_id,balance_free_after,balance_paid_after,admin_username,created_at)
            VALUES (?,'thorn_dew',?,0,?,'match_reward',?,?,?,'',?)''',(uid,amount,reason,source,free,paid,now))
        conn.execute('INSERT INTO pvp_reward_participants VALUES (?,?,?,?,?,?)',(key,uid,integrity._json(opponents),amount,outcome,now))
        if not early:
            awards.append({'user_id':uid,'amount':amount,'multiplier':multiplier,'reason':reason,
                           'base':base,'streak_bonus':streak_bonus,'newcomer_multiplier':profile['reward_multiplier']})
    result={'awarded':awards,'skipped':'early_surrender' if early else None}
    conn.execute('UPDATE pvp_reward_settlements SET result_json=? WHERE settlement_key=?',(integrity._json(result),key))
    return result


def award_match(match_id,summary,award_time=None):
    with integrity._transaction() as conn:
        return settle_conn(conn,match_id,summary,award_time)
