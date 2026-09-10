import pytest

import app as gtn
import db
import mod_unlocks


def test_official_unlock_progression_thresholds():
    guest = mod_unlocks.guest_state()
    assert guest['unlocked_official'] == [mod_unlocks.VANILLA_MOD_FILENAME]
    assert not guest['fixed_unlocked']
    assert not guest['entertainment_unlocked']

    fixed = mod_unlocks.compute_state(10, ())
    assert fixed['fixed_unlocked']
    assert fixed['unspent_choices'] == 0
    assert fixed['entertainment_unlocked'] is False
    assert set(fixed['fixed_mods']) == {
        'Garden Cards Addition.gtnmod',
        'Factory Cards Addition.gtnmod',
        'Desert Cards Addition.gtnmod',
        'Jungle Cards Addition.gtnmod',
        'Ocean Cards Addition.gtnmod',
    }

    twenty = mod_unlocks.compute_state(20, ())
    assert twenty['entertainment_unlocked']
    assert twenty['community_unlocked']
    assert twenty['unspent_choices'] == 1
    assert 'Void Card Addition.gtnmod' in twenty['choice_candidates']

    chosen = mod_unlocks.compute_state(20, ('Void Card Addition.gtnmod',))
    assert 'Void Card Addition.gtnmod' in chosen['unlocked_official']
    assert chosen['unspent_choices'] == 0


def test_surplus_entitlements_auto_unlock_everything_without_choices():
    state = mod_unlocks.compute_state(70, ())
    assert state['all_official_unlocked']
    assert state['unspent_choices'] == 0
    assert state['choice_candidates'] == []
    assert all(name in state['unlocked_official'] for name in state['remaining_mods'])


def test_choose_unlock_persists_and_validates(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'unlock.sqlite3'))
    db.init_db()
    with db.get_db_connection() as conn:
        conn.execute(
            '''INSERT INTO users(id, username, username_lower, password_hash, created_at)
               VALUES (1, 'unlocker', 'unlocker', 'unused', ?)''',
            (db.utc_now(),),
        )
        conn.execute('UPDATE users SET games_played = 20 WHERE id = 1')
        conn.commit()

    state = mod_unlocks.load_state(1)
    assert state['unspent_choices'] == 1
    with pytest.raises(ValueError):
        mod_unlocks.choose_unlock(1, 'Vanilla Cards.gtnmod')
    updated = mod_unlocks.choose_unlock(1, 'Void Card Addition.gtnmod')
    assert 'Void Card Addition.gtnmod' in updated['unlocked_official']
    assert updated['unspent_choices'] == 0
    with pytest.raises(ValueError):
        mod_unlocks.choose_unlock(1, 'Hel Cards Addition.gtnmod')
    assert 'Void Card Addition.gtnmod' in mod_unlocks.load_state(1)['unlocked_official']


def _fake_player(user_id, state, *, match_mode='casual_1v1'):
    engine_mode, match_type, canonical = gtn.pvp_match_mode_parts(match_mode)
    return {
        'nickname': f'P{user_id}',
        'user_id': user_id,
        'is_registered_user': True,
        'mode': engine_mode,
        'match_type': match_type,
        'match_mode': canonical,
        'mod_unlock_state': state,
        'entertainment_mods': [],
        'community_mods': [],
        'mod_source': 'official',
        'preferred_disabled_mods': [],
    }


def test_casual_room_draw_intersects_unlocks_and_applies_bans(monkeypatch):
    states = {
        101: mod_unlocks.compute_state(20, ('Void Card Addition.gtnmod',)),
        102: mod_unlocks.compute_state(20, ('Hel Cards Addition.gtnmod',)),
    }
    # Both accounts share the fixed five; only those are in the intersection.
    sids = ['sid-a', 'sid-b']
    for index, sid in enumerate(sids):
        state = states[101 + index]
        player = _fake_player(101 + index, state)
        player['room_id'] = None
        player['status'] = 'in_game'
        gtn.players[sid] = player
    monkeypatch.setattr(gtn.mod_unlocks, 'load_state', lambda uid: states[int(uid)])
    room = gtn.GameRoom(99001, sids, None, mode='1v1', match_mode='casual_1v1')
    room.engine.player_names = ['A', 'B']
    gtn.rooms[room.room_id] = room
    try:
        for sid in sids:
            gtn.players[sid]['room_id'] = room.room_id
        gtn.start_casual_room_or_event_select(room)
        assert room.mod_draw_active
        assert room.mod_draw_candidates
        assert set(room.mod_draw_candidates).issubset(set(states[101]['fixed_mods']))
        room.mod_draw_bans[0] = [room.mod_draw_candidates[0]]
        assert gtn._complete_mod_draw_locked(room)
        assert room.mod_draw_active is False
        assert room.mod_draw_candidates == []
        assert room.casual_final_official_mods
        banned_name = room.mod_draw_last_result['banned_mods'][0]
        assert banned_name not in room.casual_final_official_mods
    finally:
        gtn.rooms.pop(room.room_id, None)
        for sid in sids:
            gtn.players.pop(sid, None)


def test_guest_casual_room_skips_to_vanilla(monkeypatch):
    sid_a, sid_b = 'guest-a', 'guest-b'
    for sid in (sid_a, sid_b):
        gtn.players[sid] = {
            'nickname': sid,
            'user_id': None,
            'is_registered_user': False,
            'mode': '1v1',
            'match_type': 'casual',
            'match_mode': 'casual_1v1',
            'mod_unlock_state': mod_unlocks.guest_state(),
            'entertainment_mods': [],
            'community_mods': [],
            'mod_source': 'official',
            'preferred_disabled_mods': [],
            'room_id': None,
            'status': 'in_game',
        }
    room = gtn.GameRoom(99002, [sid_a, sid_b], None, mode='1v1', match_mode='casual_1v1')
    room.engine.player_names = ['A', 'B']
    gtn.rooms[room.room_id] = room
    try:
        for sid in (sid_a, sid_b):
            gtn.players[sid]['room_id'] = room.room_id
        gtn.start_casual_room_or_event_select(room)
        assert not room.mod_draw_active
        assert room.casual_final_official_mods == []
        assert room.engine.phase in ('event_select',)
    finally:
        gtn.rooms.pop(room.room_id, None)
        for sid in (sid_a, sid_b):
            gtn.players.pop(sid, None)


def test_ban_limits_and_local_mode_gate():
    one_v_one = gtn.GameRoom(99003, ['a', 'b'], None, mode='1v1', match_mode='casual_1v1')
    two_v_two = gtn.GameRoom(99004, ['a', 'b', 'c', 'd'], None, mode='2v2', match_mode='casual_2v2')
    assert gtn.mod_draw_ban_limit(one_v_one) == 2
    assert gtn.mod_draw_ban_limit(two_v_two) == 1
    pending = _fake_player(1, mod_unlocks.compute_state(20, ()))
    assert gtn.mod_unlock_required_for_match_mode(pending, 'casual_1v1')
    pending['match_mode'] = 'ranked_1v1'
    assert not gtn.mod_unlock_required_for_match_mode(pending, 'ranked_1v1')


def test_mod_draw_socket_updates_and_submits(monkeypatch):
    clients = [gtn.socketio.test_client(gtn.app), gtn.socketio.test_client(gtn.app)]
    room_map = gtn.socketio.server.manager.rooms["/"][None]
    sids = [
        next(key for key, value in room_map.items() if value == client.eio_sid)
        for client in clients
    ]
    states = {
        301: mod_unlocks.compute_state(20, ('Void Card Addition.gtnmod',)),
        302: mod_unlocks.compute_state(20, ('Hel Cards Addition.gtnmod',)),
    }
    monkeypatch.setattr(gtn.mod_unlocks, 'load_state', lambda uid: states[int(uid)])
    for index, sid in enumerate(sids):
        player = _fake_player(301 + index, states[301 + index])
        player.update({'room_id': None, 'status': 'in_game'})
        gtn.players[sid] = player
    room = gtn.GameRoom(99101, sids, None, mode='1v1', match_mode='casual_1v1')
    room.engine.player_names = ['A', 'B']
    gtn.rooms[room.room_id] = room
    try:
        for sid in sids:
            gtn.players[sid]['room_id'] = room.room_id
        gtn.start_casual_room_or_event_select(room)
        assert room.mod_draw_active
        for client in clients:
            client.get_received()
        first_candidate = room.mod_draw_candidates[0]
        clients[0].emit('mod_draw_update_bans', {'bans': [first_candidate]})
        assert room.mod_draw_bans[0] == [first_candidate]
        clients[0].emit('mod_draw_submit', {'bans': [first_candidate]})
        clients[1].emit('mod_draw_submit', {'bans': []})
        assert not room.mod_draw_active
        assert first_candidate not in room.casual_final_official_mods
        assert room.engine.phase == 'event_select'
    finally:
        gtn.rooms.pop(room.room_id, None)
        for sid in sids:
            gtn.players.pop(sid, None)
        for client in clients:
            client.disconnect()


def test_casual_invite_creates_mod_draw_room(monkeypatch):
    clients = [gtn.socketio.test_client(gtn.app), gtn.socketio.test_client(gtn.app)]
    room_map = gtn.socketio.server.manager.rooms["/"][None]
    sids = [
        next(key for key, value in room_map.items() if value == client.eio_sid)
        for client in clients
    ]
    states = {
        401: mod_unlocks.compute_state(20, ('Void Card Addition.gtnmod',)),
        402: mod_unlocks.compute_state(20, ('Hel Cards Addition.gtnmod',)),
    }
    monkeypatch.setattr(gtn.mod_unlocks, 'load_state', lambda uid: states[int(uid)])
    for index, sid in enumerate(sids):
        player = _fake_player(401 + index, states[401 + index])
        player.update({
            'status': 'lobby',
            'room_id': None,
            'beta_mode': False,
            'loadout_hash': 'casual-shared-preference',
        })
        gtn.players[sid] = player
    gtn.invites[sids[0]] = sids[1]
    created_room = None
    try:
        clients[1].emit('accept_invite', {'inviter_sid': sids[0]})
        created_room = next(
            (
                room for room in gtn.rooms.values()
                if set(room.player_sids) == set(sids)
            ),
            None,
        )
        assert created_room is not None
        assert created_room.match_mode == 'casual_1v1'
        assert created_room.mod_draw_active
    finally:
        if created_room is not None:
            gtn.rooms.pop(created_room.room_id, None)
        for sid in sids:
            gtn.players.pop(sid, None)
            gtn.invites.pop(sid, None)
        for client in clients:
            client.disconnect()


def test_casual_2v2_team_match_starts_mod_draw(monkeypatch):
    clients = [gtn.socketio.test_client(gtn.app) for _ in range(4)]
    room_map = gtn.socketio.server.manager.rooms["/"][None]
    sids = [
        next(key for key, value in room_map.items() if value == client.eio_sid)
        for client in clients
    ]
    states = {
        501 + index: mod_unlocks.compute_state(70, ())
        for index in range(4)
    }
    monkeypatch.setattr(gtn.mod_unlocks, 'load_state', lambda uid: states[int(uid)])
    for index, sid in enumerate(sids):
        player = _fake_player(501 + index, states[501 + index], match_mode='casual_2v2')
        player.update({
            'status': 'lobby',
            'room_id': None,
            'beta_mode': False,
            'loadout_hash': 'casual-2v2-shared-preference',
        })
        gtn.players[sid] = player
    gtn.teams[sids[0]] = {'leader': sids[0], 'members': [sids[0], sids[1]]}
    gtn.teams[sids[1]] = gtn.teams[sids[0]]
    gtn.teams[sids[2]] = {'leader': sids[2], 'members': [sids[2], sids[3]]}
    gtn.teams[sids[3]] = gtn.teams[sids[2]]
    created_room = None
    try:
        clients[2].emit('accept_team_match', {'from_leader': sids[0]})
        created_room = next(
            (
                room for room in gtn.rooms.values()
                if set(room.player_sids) == set(sids)
            ),
            None,
        )
        assert created_room is not None
        assert created_room.match_mode == 'casual_2v2'
        assert created_room.mod_draw_active
        assert len(created_room.mod_draw_candidates) == 5
    finally:
        if created_room is not None:
            gtn.rooms.pop(created_room.room_id, None)
        for sid in sids:
            gtn.players.pop(sid, None)
            gtn.teams.pop(sid, None)
        for client in clients:
            client.disconnect()


def test_casual_rematch_redraws_and_blocks_on_pending_choice(monkeypatch):
    clients = [gtn.socketio.test_client(gtn.app), gtn.socketio.test_client(gtn.app)]
    room_map = gtn.socketio.server.manager.rooms["/"][None]
    sids = [
        next(key for key, value in room_map.items() if value == client.eio_sid)
        for client in clients
    ]
    ready_states = {
        601: mod_unlocks.compute_state(70, ()),
        602: mod_unlocks.compute_state(70, ()),
    }
    monkeypatch.setattr(gtn.mod_unlocks, 'load_state', lambda uid: ready_states[int(uid)])
    for index, sid in enumerate(sids):
        player = _fake_player(601 + index, ready_states[601 + index])
        player.update({'status': 'in_game', 'room_id': None})
        gtn.players[sid] = player
    room = gtn.GameRoom(99102, sids, None, mode='1v1', match_mode='casual_1v1')
    room.engine.player_names = ['A', 'B']
    room.engine.phase = 'game_over'
    room.engine.game_over = True
    room.casual_shared_mod_profile = {
        'entertainment_mods': [],
        'community_mods': [],
        'mod_source': 'official',
    }
    gtn.rooms[room.room_id] = room
    try:
        for sid in sids:
            gtn.players[sid]['room_id'] = room.room_id
        clients[0].emit('rematch', {})
        clients[1].emit('rematch', {})
        assert room.mod_draw_active
        assert room.match_seq == 2
    finally:
        gtn.rooms.pop(room.room_id, None)
        for sid in sids:
            gtn.players.pop(sid, None)
        for client in clients:
            client.disconnect()
