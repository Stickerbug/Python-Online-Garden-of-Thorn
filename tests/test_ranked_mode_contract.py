import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import app as gtn
import db


ROOT = Path(__file__).resolve().parents[1]


def _registered_player(user_id, *, match_mode='ranked_1v1', entertainment=None, mod_source='official'):
    engine_mode, match_type, canonical = gtn.pvp_match_mode_parts(match_mode)
    return {
        'nickname': f'Player {user_id}',
        'user_id': user_id,
        'is_registered_user': True,
        'mode': engine_mode,
        'match_type': match_type,
        'match_mode': canonical,
        'mod_source': mod_source,
        'entertainment_mods': list(entertainment or []),
    }


def test_match_mode_normalization_keeps_legacy_clients_casual():
    assert gtn.normalize_pvp_match_mode('1v1') == 'casual_1v1'
    assert gtn.normalize_pvp_match_mode('2v2') == 'casual_2v2'
    assert gtn.pvp_match_mode_parts('ranked_2v2') == ('2v2', 'ranked', 'ranked_2v2')
    assert set(gtn.RANKED_MATCH_MODES) == {'ranked_1v1', 'ranked_2v2'}


def test_room_snapshots_canonical_match_mode_and_rejects_topology_mismatch():
    room = gtn.GameRoom(97001, ['a', 'b'], None, mode='1v1', match_mode='ranked_1v1')
    assert room.mode == '1v1'
    assert room.match_type == 'ranked'
    assert room.match_mode == 'ranked_1v1'
    assert gtn.room_replay_data(room)['match_mode'] == 'ranked_1v1'

    try:
        gtn.GameRoom(97002, ['a', 'b'], None, mode='1v1', match_mode='ranked_2v2')
    except ValueError as exc:
        assert '引擎模式' in str(exc)
    else:
        raise AssertionError('mismatched topology must be rejected')


def test_ranked_eligibility_is_fail_closed_for_guests_and_mods():
    eligible = [_registered_player(1), _registered_player(2)]
    assert gtn.ranked_match_eligibility(eligible) == (True, '')
    assert gtn.ranked_match_eligibility([eligible[0], {'nickname': 'guest'}])[1] == 'guest_participant'
    assert gtn.ranked_match_eligibility([
        eligible[0],
        _registered_player(2, entertainment=['fun']),
    ])[1] == 'entertainment_mod'
    assert gtn.ranked_match_eligibility([
        eligible[0],
        _registered_player(2, mod_source='community'),
    ])[1] == 'community_mod'


def test_guest_cannot_switch_into_ranked_lobby():
    client = gtn.socketio.test_client(gtn.app)
    sid = None
    try:
        client.emit('login', {'nickname': 'RankedGateGuest', 'match_mode': 'ranked_1v1'})
        login = next(event['args'][0] for event in client.get_received() if event['name'] == 'login_ok')
        sid = login['sid']
        assert login['match_mode'] == 'casual_1v1'
        client.emit('set_mode', {'match_mode': 'ranked_1v1'})
        errors = [event['args'][0] for event in client.get_received() if event['name'] == 'server_error']
        assert errors and errors[-1]['reason'] == 'guest_participant'
        assert gtn.players[sid]['match_mode'] == 'casual_1v1'
    finally:
        if client.is_connected():
            client.disconnect()
        if sid:
            with gtn._lock:
                gtn.players.pop(sid, None)


def test_ranked_silently_disables_entertainment_mods_and_restores_casual_preference():
    entertainment_mods = sorted(gtn.entertainment_mod_filenames())
    assert entertainment_mods, 'the contract requires at least one entertainment mod fixture'
    target_mod = entertainment_mods[0]
    preferred_disabled = [
        filename for filename in gtn.default_disabled_mods()
        if filename != target_mod
    ]
    client = gtn.socketio.test_client(gtn.app)
    sid = None
    try:
        client.emit('login', {
            'nickname': 'RankedModGate',
            'match_mode': 'casual_1v1',
            'disabled_mods': preferred_disabled,
        })
        login = next(event['args'][0] for event in client.get_received() if event['name'] == 'login_ok')
        sid = login['sid']
        with gtn._lock:
            player = gtn.players[sid]
            player['is_registered_user'] = True
            player['user_id'] = 991337
            player['reputation'] = 85
            assert target_mod in player['entertainment_mods']
            assert target_mod not in player['preferred_disabled_mods']

        with patch.object(gtn, 'DB_AVAILABLE', False):
            client.emit('set_mode', {'match_mode': 'ranked_1v1'})
            ranked_events = client.get_received()
            assert not [event for event in ranked_events if event['name'] == 'server_error']
            with gtn._lock:
                player = gtn.players[sid]
                assert player['match_mode'] == 'ranked_1v1'
                assert player['entertainment_mods'] == []
                assert set(entertainment_mods).issubset(player['disabled_mods'])
                assert target_mod not in player['preferred_disabled_mods']

            client.emit('update_mod_settings', {
                'request_id': 'ranked-entertainment-silent',
                'client_revision': 0,
                'disabled_mods': preferred_disabled,
                'mod_source': 'official',
            })
            update = next(
                event['args'][0]
                for event in client.get_received()
                if event['name'] == 'mod_settings_updated'
            )
            assert update['ok'] is True
            assert update['details']['ranked_downgraded'] is False
            assert target_mod in update['disabled_mods']
            assert target_mod not in update['preferred_disabled_mods']

            client.emit('set_mode', {'match_mode': 'casual_1v1'})
            client.get_received()
            with gtn._lock:
                player = gtn.players[sid]
                assert player['match_mode'] == 'casual_1v1'
                assert target_mod in player['entertainment_mods']
                assert target_mod not in player['disabled_mods']
                assert target_mod not in player['preferred_disabled_mods']
    finally:
        if client.is_connected():
            client.disconnect()
        if sid:
            with gtn._lock:
                gtn.players.pop(sid, None)


def test_only_explicit_ranked_room_is_valid_for_rating():
    def make_room(match_mode):
        room = gtn.GameRoom(97003, ['a', 'b'], None, mode='1v1', match_mode=match_mode)
        room.engine.game_over = True
        room.started_at = time.time() - gtn.RANKING_MIN_DURATION_SECONDS - 5
        room._valid_action_counts = {
            0: gtn.RANKING_MIN_ACTIONS_PER_SIDE,
            1: gtn.RANKING_MIN_ACTIONS_PER_SIDE,
        }
        room.store_player_profile('a', 0, _registered_player(1, match_mode=match_mode))
        room.store_player_profile('b', 1, _registered_player(2, match_mode=match_mode))
        return room

    casual = make_room('casual_1v1')
    ranked = make_room('ranked_1v1')
    assert gtn.is_room_valid_for_ranking(casual) == (False, 'casual_match')
    assert gtn.is_room_valid_for_stats(casual) is True
    assert gtn.is_room_valid_for_ranking(ranked) == (True, '')

    ranked.started_at = time.time()
    ranked._valid_action_counts = {}
    ranked._ended_by_surrender = True
    assert gtn.is_room_valid_for_ranking(ranked) == (True, '')
    assert gtn.is_room_valid_for_stats(ranked) is True
    assert db.award_match_thorn_dew(1, {
        'result': 'win',
        'valid_for_stats': True,
        'ended_by_surrender': True,
        'duration_seconds': 59,
    }) == {'awarded': [], 'skipped': 'early_surrender'}


def test_database_rating_layer_rejects_casual_even_if_flag_is_forged():
    result = db.apply_gr_match_result(123, {
        'mode': '1v1',
        'match_type': 'casual',
        'match_mode': 'casual_1v1',
        'valid_for_ranking': True,
    })
    assert result == {'applied': False, 'reason': 'casual_match'}


def test_ranked_games_are_not_advertised_as_spectatable():
    room_id = 97004
    room = SimpleNamespace(
        room_id=room_id,
        mode='1v1',
        match_type='ranked',
        match_mode='ranked_1v1',
        beta_mode=False,
        player_sids=['a', 'b'],
        player_profiles={
            'a': _registered_player(1),
            'b': _registered_player(2),
        },
        disconnected_players={},
        engine=SimpleNamespace(phase='action', round_num=2),
    )
    original = gtn.rooms.get(room_id)
    gtn.rooms[room_id] = room
    try:
        game = next(item for item in gtn.get_ongoing_games(False) if item['room_id'] == room_id)
        assert game['ranked'] is True
        assert game['match_mode'] == 'ranked_1v1'
        assert game['can_spectate'] is False
        assert game['spectate_disabled_reason'] == 'ranked_no_spectators'
    finally:
        if original is None:
            gtn.rooms.pop(room_id, None)
        else:
            gtn.rooms[room_id] = original


def test_ranked_spectate_request_is_rejected_before_joining_room():
    client = gtn.socketio.test_client(gtn.app)
    room_id = 97005
    sid = None
    room = SimpleNamespace(
        room_id=room_id,
        match_seq=1,
        created_at=1,
        mode='1v1',
        match_type='ranked',
        match_mode='ranked_1v1',
        beta_mode=False,
        player_sids=[],
        spectators=[],
        engine=SimpleNamespace(phase='action', player_names=[]),
    )
    try:
        client.emit('login', {'nickname': 'RankedSpecGuest', 'mode': '1v1'})
        login = next(event['args'][0] for event in client.get_received() if event['name'] == 'login_ok')
        sid = login['sid']
        with gtn._lock:
            gtn.rooms[room_id] = room
        client.emit('spectate', {'room_id': room_id})
        errors = [event['args'][0] for event in client.get_received() if event['name'] == 'server_error']
        assert errors and errors[-1]['reason'] == 'ranked_no_spectators'
        assert gtn.players[sid]['status'] == 'lobby'
        assert sid not in room.spectators
    finally:
        if client.is_connected():
            client.disconnect()
        with gtn._lock:
            if sid:
                gtn.players.pop(sid, None)
            gtn.rooms.pop(room_id, None)


def test_lobby_ui_exposes_four_core_match_modes_and_keeps_special_modes_casual():
    template = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
    source = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
    for match_mode in (
        'casual_1v1',
        'casual_2v2',
        'ranked_1v1',
        'ranked_2v2',
        'casual_urf',
        'casual_random_deck',
    ):
        assert f'data-mode="{match_mode}"' in template
    assert "match_mode: preferredMode" in source
    assert "isRankedMatchMode(currentMode)" in source
    assert "socket.emit('set_mode', { mode: engineModeForMatchMode(newMode), match_mode: newMode })" in source
    assert "function entertainmentModsAvailableInSettings()" in source
    assert "kind === 'entertainment'" in source
    assert "!entertainmentAvailable" in source
    assert "preferred_disabled_mods" in source


def test_new_ranked_era_archives_legacy_rating_and_starts_from_zero_games(tmp_path):
    old_path = db.DB_PATH
    db.DB_PATH = str(tmp_path / 'ranked-era.sqlite3')
    try:
        db.init_db()
        user, error = db.create_user('RankedEraUser', 'Aa1!aaaa')
        assert error is None
        with db.get_db_connection() as conn:
            conn.execute(
                '''
                UPDATE users
                SET season_gr = 1375, total_gr = 1420, highest_gr = 1500,
                    season_ranked_games = 31, total_ranked_games = 85,
                    gr_season_id = 'S202608'
                WHERE id = ?
                ''',
                (user['id'],),
            )
            conn.commit()
        season = {
            'id': 'R1-S202609',
            'name': 'R1 · 2026-09',
            'starts_at': '2026-08-31T16:00:00Z',
            'ends_at': '2026-09-30T15:59:59Z',
            'next_starts_at': '2026-09-30T16:00:00Z',
        }
        with patch.object(db, 'current_gr_season', return_value=season):
            db.ensure_current_gr_season([user['id']])
            db.ensure_current_gr_season([user['id']])
        with db.get_db_connection() as conn:
            current = conn.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()
            archives = conn.execute(
                'SELECT * FROM gr_rating_archives WHERE user_id = ?',
                (user['id'],),
            ).fetchall()
        assert current['season_gr'] == db.GR_INITIAL
        assert current['total_gr'] == db.GR_INITIAL
        assert current['season_ranked_games'] == 0
        assert current['total_ranked_games'] == 0
        assert current['highest_gr'] == 1500
        assert current['gr_season_id'] == season['id']
        assert len(archives) == 1
        assert archives[0]['season_gr'] == 1375
        assert archives[0]['total_gr'] == 1420
        assert archives[0]['total_ranked_games'] == 85
    finally:
        db.DB_PATH = old_path


def test_ranked_settlement_is_idempotent_and_conflicting_retry_is_rejected(tmp_path):
    old_path = db.DB_PATH
    db.DB_PATH = str(tmp_path / 'ranked-settlement.sqlite3')
    try:
        db.init_db()
        user_a, error_a = db.create_user('RankedSettleA', 'Aa1!aaaa')
        user_b, error_b = db.create_user('RankedSettleB', 'Aa1!aaaa')
        assert error_a is None and error_b is None
        summary = {
            'mode': '1v1',
            'match_type': 'ranked',
            'match_mode': 'ranked_1v1',
            'players': ['RankedSettleA', 'RankedSettleB'],
            'player_ids': [user_a['id'], user_b['id']],
            'winner_user_ids': [user_a['id']],
            'winner_index': 0,
            'result': 'win',
            'valid_for_ranking': True,
            'started_at': '2026-08-31T12:00:00Z',
            'ended_at': '2026-08-31T12:01:00Z',
            'duration_seconds': 60,
        }
        match_id = db.save_match_summary(summary)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = list(pool.map(
                lambda _: db.apply_gr_match_result(match_id, summary),
                range(2),
            ))
        conflict = db.apply_gr_match_result(match_id, {**summary, 'winner_index': 1, 'winner_user_ids': [user_b['id']]})
        assert first['applied'] is True and second['applied'] is True
        assert sorted(bool(item.get('duplicate')) for item in (first, second)) == [False, True]
        assert conflict == {'applied': False, 'reason': 'settlement_conflict'}
        with db.get_db_connection() as conn:
            users = conn.execute(
                'SELECT id, total_ranked_games FROM users WHERE id IN (?, ?) ORDER BY id',
                (user_a['id'], user_b['id']),
            ).fetchall()
            settlements = conn.execute('SELECT * FROM gr_match_settlements').fetchall()
        assert [row['total_ranked_games'] for row in users] == [1, 1]
        assert len(settlements) == 1
    finally:
        db.DB_PATH = old_path


def test_ranked_2v2_settlement_updates_each_account_once(tmp_path):
    old_path = db.DB_PATH
    db.DB_PATH = str(tmp_path / 'ranked-settlement-2v2.sqlite3')
    try:
        db.init_db()
        users = []
        for index in range(4):
            user, error = db.create_user(f'RankedTeam{index}', 'Aa1!aaaa')
            assert error is None
            users.append(user)
        ids = [user['id'] for user in users]
        summary = {
            'mode': '2v2',
            'match_type': 'ranked',
            'match_mode': 'ranked_2v2',
            'players': [user['username'] for user in users],
            'player_ids': ids,
            'winner_user_ids': ids[:2],
            'winner_index': 0,
            'result': 'win',
            'valid_for_ranking': True,
            'started_at': '2026-09-01T00:00:00Z',
            'ended_at': '2026-09-01T00:01:00Z',
            'duration_seconds': 60,
        }
        match_id = db.save_match_summary(summary)
        first = db.apply_gr_match_result(match_id, summary)
        duplicate = db.apply_gr_match_result(match_id, summary)
        assert first['applied'] is True
        assert duplicate['duplicate'] is True
        with db.get_db_connection() as conn:
            rows = conn.execute(
                f"SELECT total_ranked_games FROM users WHERE id IN ({','.join(['?'] * 4)})",
                ids,
            ).fetchall()
        assert [row['total_ranked_games'] for row in rows] == [1, 1, 1, 1]
    finally:
        db.DB_PATH = old_path
