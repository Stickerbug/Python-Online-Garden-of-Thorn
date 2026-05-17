import sys
import os
import re
import time
import json
import random
import threading
import copy

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from game_engine import GameEngine
from cards import CardInstance, CARD_DEFS, DRAFT_RATIO, DECK_SIZE, build_draft_pool, generate_draft_options
from mod_loader import merge_mod_cards_to_card_defs, load_all_mods, save_mod, Mod, get_mods_summary

try:
    merge_mod_cards_to_card_defs()
except Exception:
    pass

app = Flask(__name__)
app.config['SECRET_KEY'] = 'garden_of_thorn_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

_lock = threading.Lock()
_next_room_id = 0

players = {}
rooms = {}
invites = {}


class GameRoom:
    def __init__(self, room_id, player_sids):
        self.room_id = room_id
        self.player_sids = list(player_sids)
        self.engine = GameEngine()
        self.spectators = []
        self.disconnected_players = {}
        self.reconnect_timers = {}
        self._rematch_votes = set()

    def player_index(self, sid):
        if sid in self.player_sids:
            return self.player_sids.index(sid)
        return -1


def sanitize_nickname(raw):
    name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', raw)
    name = re.sub(r'[\u3000\s]+', '', name)
    name = re.sub(r'[^\w\u4e00-\u9fff\-]', '', name)
    return name.strip()


def validate_nickname(name):
    if not name or len(name) > 12:
        return False
    if re.match(r'^[\d]+$', name):
        return False
    if re.match(r'^[\-_]+$', name):
        return False
    if re.search(r'[\-_]{2,}', name):
        return False
    return True


def get_lobby_list():
    lobby = []
    for sid, p in players.items():
        if p['status'] == 'lobby':
            lobby.append({'sid': sid, 'nickname': p['nickname']})
    return lobby


def get_ongoing_games():
    games = []
    for rid, room in rooms.items():
        phase = room.engine.phase
        if phase in ('action', 'draw', 'response', 'choice', 'playing', 'draft', 'event_select'):
            p1_name = '?'
            p2_name = '?'
            if len(room.player_sids) >= 1:
                sid0 = room.player_sids[0]
                if sid0 in players:
                    p1_name = players[sid0]['nickname']
                elif sid0 in room.disconnected_players:
                    p1_name = room.disconnected_players[sid0]['nickname']
            if len(room.player_sids) >= 2:
                sid1 = room.player_sids[1]
                if sid1 in players:
                    p2_name = players[sid1]['nickname']
                elif sid1 in room.disconnected_players:
                    p2_name = room.disconnected_players[sid1]['nickname']
            both_disconnected = all(s in room.disconnected_players for s in room.player_sids[:2])
            games.append({
                'room_id': rid,
                'player1': p1_name,
                'player2': p2_name,
                'round': room.engine.round_num,
                'phase': phase,
                'both_disconnected': both_disconnected,
            })
    return games


def broadcast_lobby():
    lobby_list = get_lobby_list()
    ongoing = get_ongoing_games()
    for sid, p in players.items():
        if p['status'] == 'lobby':
            socketio.emit('lobby_update', {
                'players': lobby_list,
                'your_sid': sid,
                'ongoing_games': ongoing,
            }, room=sid)
    print(f"[服务器] broadcast_lobby: {len(lobby_list)} lobby玩家, {len([p for p in players.values() if p['status'] == 'lobby'])} 接收者")


def send_draft_state(room, pidx):
    sid = room.player_sids[pidx]
    if sid not in players:
        return
    engine = room.engine
    options = engine.draft_options[pidx]
    picks = engine.draft_picks[pidx]
    rerolls = engine.draft_rerolls[pidx]
    opp_pidx = 1 - pidx
    socketio.emit('draft_state', {
        'options': [c.to_dict() for c in options],
        'picks': picks,
        'rerolls': rerolls,
        'round': len(picks) + 1,
        'total_rounds': DECK_SIZE,
        'opponent_picks_count': len(engine.draft_picks[opp_pidx]),
    }, room=sid)


def send_event_state(room, pidx):
    sid = room.player_sids[pidx]
    if sid not in players:
        return
    engine = room.engine
    events = engine.opening_event_options[pidx]
    opp_idx = 1 - pidx
    opp_selected = engine.opening_event_picks[opp_idx] is not None
    socketio.emit('event_select', {
        'events': events,
        'opponent_selected': opp_selected,
        'my_pick': engine.opening_event_picks[pidx],
        'magic_options': engine.opening_event_magic_options[pidx],
        'draft_picks': engine.draft_picks[pidx],
    }, room=sid)


def broadcast_game_state(room):
    for pidx, sid in enumerate(room.player_sids):
        if sid not in players:
            continue
        state = room.engine.get_public_state(pidx)
        state['your_id'] = pidx
        opp_pidx = 1 - pidx
        opp_sid = room.player_sids[opp_pidx]
        if opp_sid in players:
            state['opponent_name'] = players[opp_sid]['nickname']
        else:
            state['opponent_name'] = '?'
        socketio.emit('state_update', state, room=sid)
    broadcast_spectate_state(room)


def send_game_state_to(room, pidx):
    sid = room.player_sids[pidx]
    if sid not in players:
        return
    phase = room.engine.phase
    socketio.emit('game_phase', {'phase': phase}, room=sid)
    if phase == 'event_select':
        send_event_state(room, pidx)
    elif phase == 'draft':
        send_draft_state(room, pidx)
    else:
        state = room.engine.get_public_state(pidx)
        state['your_id'] = pidx
        opp_pidx = 1 - pidx
        opp_sid = room.player_sids[opp_pidx]
        if opp_sid in players:
            state['opponent_name'] = players[opp_sid]['nickname']
        else:
            state['opponent_name'] = '?'
        socketio.emit('state_update', state, room=sid)


def start_event_select(room):
    for pi in range(len(room.player_sids)):
        send_event_state(room, pi)


def start_game(room):
    room.engine.start_game()
    for sid in room.player_sids:
        if sid in players:
            socketio.emit('game_phase', {'phase': 'playing'}, room=sid)
    broadcast_game_state(room)


def broadcast_spectate_state(room):
    for spid in room.spectators:
        if spid not in players:
            continue
        perspective = players[spid].get('spectate_perspective', 0)
        state = room.engine.get_public_state(for_player=perspective)
        state['spectating'] = True
        state['spectate_perspective'] = perspective
        if len(room.player_sids) >= 1 and room.player_sids[0] in players:
            state['player1_name'] = players[room.player_sids[0]]['nickname']
        else:
            state['player1_name'] = '?'
        if len(room.player_sids) >= 2 and room.player_sids[1] in players:
            state['player2_name'] = players[room.player_sids[1]]['nickname']
        else:
            state['player2_name'] = '?'
        socketio.emit('state_update', state, room=spid)


def reconnect_timeout(room_id, old_sid):
    global _next_room_id
    with _lock:
        if room_id not in rooms:
            return
        room = rooms[room_id]
        if old_sid not in room.disconnected_players:
            return
        dc_info = room.disconnected_players.pop(old_sid)
        for other_sid in room.player_sids:
            if other_sid in players:
                socketio.emit('opponent_disconnected', {'timeout': True}, room=other_sid)
                players[other_sid]['room_id'] = None
                players[other_sid]['status'] = 'lobby'
        for t in room.reconnect_timers.values():
            t.cancel()
        del rooms[room_id]
        for sid, p in players.items():
            if p['status'] == 'reconnecting' and p['nickname'] == dc_info['nickname']:
                p['status'] = 'lobby'
                socketio.emit('reconnect_timeout', {}, room=sid)
    broadcast_lobby()


def both_disconnected_cleanup(room_id):
    global _next_room_id
    with _lock:
        if room_id not in rooms:
            return
        room = rooms[room_id]
        for t in room.reconnect_timers.values():
            t.cancel()
        room.reconnect_timers.clear()
        if hasattr(room, 'both_dc_timer'):
            room.both_dc_timer = None
        del rooms[room_id]
    broadcast_lobby()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/fonts/<path:filename>')
def serve_font(filename):
    fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
    return send_from_directory(fonts_dir, filename)


@app.route('/api/cards')
def api_cards():
    result = {}
    for def_id, card_def in CARD_DEFS.items():
        result[def_id] = {
            'id': card_def.id,
            'name_en': card_def.name_en,
            'name_cn': card_def.name_cn,
            'cost_e': card_def.cost_e,
            'cost_m': card_def.cost_m,
            'card_type': card_def.card_type,
            'count': card_def.count,
            'quality': card_def.quality,
            'description': card_def.description,
            'effect_text': card_def.effect_text,
            'flags': list(card_def.flags) if card_def.flags else [],
            'trigger_cost_e': card_def.trigger_cost_e,
            'trigger_effect_text': card_def.trigger_effect_text,
            'response_trigger': card_def.response_trigger,
            'effects': card_def.effects,
        }
    return jsonify(result)


@app.route('/api/mods')
def api_mods():
    mods = load_all_mods()
    result = []
    for mod in mods:
        d = mod.to_dict()
        d['filename'] = mod.filename
        result.append(d)
    return jsonify(result)


@app.route('/api/mods/save', methods=['POST'])
def api_mods_save():
    data = request.get_json(force=True)
    if not data:
        return jsonify({'success': False, 'error': '无效数据'}), 400
    mod = Mod(data.get('filepath', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Python联机版', 'mods', 'new_mod.json')))
    if data.get('info'):
        from mod_loader import ModInfo
        mod.info = ModInfo(data['info'])
    if data.get('cards'):
        from mod_loader import ModCard
        for cd in data['cards']:
            mod.cards.append(ModCard(cd))
    if data.get('events'):
        from mod_loader import ModEvent
        for ed in data['events']:
            mod.events.append(ModEvent(ed))
    try:
        save_mod(mod)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/ls')
def admin_ls():
    with _lock:
        player_list = []
        for sid, p in players.items():
            player_list.append({
                'sid': sid,
                'nickname': p['nickname'],
                'status': p['status'],
                'room_id': p.get('room_id'),
            })
        room_list = []
        for rid, room in rooms.items():
            e = room.engine
            p_names = []
            for psid in room.player_sids:
                if psid in players:
                    p_names.append(players[psid]['nickname'])
                else:
                    p_names.append('(离线)')
            room_list.append({
                'room_id': rid,
                'players': p_names,
                'phase': e.phase,
                'round': e.round_num,
                'spectators': len(room.spectators),
            })
    return jsonify({'players': player_list, 'rooms': room_list})


@app.route('/api/admin/kick', methods=['POST'])
def admin_kick():
    data = request.get_json(force=True)
    sid = data.get('sid', '')
    with _lock:
        if sid not in players:
            return jsonify({'success': False, 'error': '玩家不存在'}), 404
        nickname = players[sid]['nickname']
        room_id = players[sid].get('room_id')
        if room_id is not None and room_id in rooms:
            room = rooms[room_id]
            for other_sid in room.player_sids:
                if other_sid != sid and other_sid in players:
                    socketio.emit('opponent_disconnected', {}, room=other_sid)
                    players[other_sid]['room_id'] = None
                    players[other_sid]['status'] = 'lobby'
            for t in room.reconnect_timers.values():
                t.cancel()
            del rooms[room_id]
        for inv_sid, target_sid in list(invites.items()):
            if inv_sid == sid or target_sid == sid:
                del invites[inv_sid]
        del players[sid]
    socketio.emit('kicked', {'reason': '被管理员踢出'}, room=sid)
    broadcast_lobby()
    return jsonify({'success': True, 'nickname': nickname})


@app.route('/api/admin/broadcast', methods=['POST'])
def admin_broadcast():
    data = request.get_json(force=True)
    msg = data.get('message', '')
    if not msg.strip():
        return jsonify({'success': False, 'error': '消息不能为空'}), 400
    socketio.emit('server_broadcast', {'message': msg})
    return jsonify({'success': True})


@app.route('/api/admin/room/<int:room_id>/skip', methods=['POST'])
def admin_skip(room_id):
    with _lock:
        if room_id not in rooms:
            return jsonify({'success': False, 'error': '房间不存在'}), 404
        room = rooms[room_id]
        e = room.engine
        if e.game_over:
            return jsonify({'success': False, 'error': '游戏已结束'}), 400
        if e.phase in ('action', 'draw'):
            e._end_player_turn(e.current_player)
            broadcast_game_state(room)
            return jsonify({'success': True, 'phase': e.phase, 'current_player': e.current_player})
        return jsonify({'success': False, 'error': f'当前阶段 {e.phase} 无法跳过'}), 400


@app.route('/api/admin/room/<int:room_id>/endgame', methods=['POST'])
def admin_endgame(room_id):
    data = request.get_json(force=True)
    winner = data.get('winner', 0)
    if winner not in (0, 1):
        return jsonify({'success': False, 'error': 'winner必须是0或1'}), 400
    with _lock:
        if room_id not in rooms:
            return jsonify({'success': False, 'error': '房间不存在'}), 404
        room = rooms[room_id]
        e = room.engine
        loser = 1 - winner
        e.players[loser].health = 0
        e._check_game_over()
        broadcast_game_state(room)
        return jsonify({'success': True, 'winner': e.winner})


@app.route('/api/admin/room/<int:room_id>/draftfill', methods=['POST'])
def admin_draftfill(room_id):
    with _lock:
        if room_id not in rooms:
            return jsonify({'success': False, 'error': '房间不存在'}), 404
        room = rooms[room_id]
        e = room.engine
        if e.phase not in ('draft', 'event_select'):
            return jsonify({'success': False, 'error': f'当前不是选牌阶段({e.phase})'}), 400
        filled = 0
        while e.phase == 'draft':
            made_progress = False
            for pidx in range(2):
                if len(e.draft_picks[pidx]) < DECK_SIZE:
                    options = e.draft_options[pidx]
                    if options:
                        pick = options[0]
                        e.draft_pick(pidx, pick.def_id)
                        filled += 1
                        made_progress = True
            if not made_progress:
                break
        if e.phase == 'event_select':
            for pidx in range(2):
                options = e.opening_event_options[pidx]
                if options and options[0]:
                    e.select_opening_event(pidx, options[0]['id'])
            start_game(room)
        return jsonify({'success': True, 'filled': filled})


@app.route('/api/admin/room/<int:room_id>/set', methods=['POST'])
def admin_set_attr(room_id):
    data = request.get_json(force=True)
    pidx = data.get('player', -1)
    key = data.get('key', '')
    val = data.get('value', 0)
    if pidx not in (0, 1):
        return jsonify({'success': False, 'error': 'player必须是0或1'}), 400
    with _lock:
        if room_id not in rooms:
            return jsonify({'success': False, 'error': '房间不存在'}), 404
        room = rooms[room_id]
        e = room.engine
        ps = e.players[pidx]
        attr_map = {
            'h': 'health', 'e': 'elixir', 'm': 'magic',
            'armor': 'armor', 'dodge': 'dodge', 'poison': 'poison',
            'burn': 'fire', 'toxic': 'toxic', 'vulnerable': 'vulnerable',
        }
        attr = attr_map.get(key)
        if not attr or not hasattr(ps, attr):
            return jsonify({'success': False, 'error': f'未知属性: {key}'}), 400
        setattr(ps, attr, val)
        if key == 'h':
            ps.base_max_health = max(ps.base_max_health, val)
            ps.max_health = max(ps.max_health, val)
            e._check_game_over()
        elif key == 'e':
            ps.max_elixir = max(ps.max_elixir, val)
        elif key == 'm':
            ps.max_magic = max(ps.max_magic, val)
        broadcast_game_state(room)
        return jsonify({'success': True})


@socketio.on('connect')
def on_connect():
    sid = request.sid
    join_room(sid)
    print(f"[服务器] Socket连接: sid={sid}")


@socketio.on('draft_reroll')
def on_draft_reroll(data=None):
    sid = request.sid
    try:
        with _lock:
            if sid not in players:
                return
            player = players[sid]
            room_id = player.get('room_id')
            if room_id is None or room_id not in rooms:
                return
            room = rooms[room_id]
            pidx = room.player_index(sid)
            if pidx < 0:
                return
            engine = room.engine
            success = engine.draft_reroll(pidx)
            if success:
                for pi in range(len(room.player_sids)):
                    send_draft_state(room, pi)
            else:
                emit('server_error', {'message': '重选次数已用完'})
    except Exception as e:
        print(f'[REROLL] EXCEPTION: {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()


@socketio.on('login')
def on_login(data):
    global _next_room_id
    sid = request.sid
    raw_name = data.get('nickname', '')
    name = sanitize_nickname(raw_name)
    if not validate_nickname(name):
        emit('login_fail', {'reason': '昵称无效：不能为纯数字、纯符号，且-_不能连续出现'})
        return
    with _lock:
        for p in players.values():
            if p['nickname'] == name:
                emit('login_fail', {'reason': '昵称已被使用'})
                return
        reconnect_room = None
        reconnect_old_sid = None
        for room in rooms.values():
            for dc_sid, dc_info in room.disconnected_players.items():
                if dc_info['nickname'] == name:
                    reconnect_room = room
                    reconnect_old_sid = dc_sid
                    break
            if reconnect_room:
                break
        initial_status = 'reconnecting' if reconnect_room else 'lobby'
        disabled_mods = data.get('disabled_mods', [])
        if isinstance(disabled_mods, str):
            disabled_mods = [x.strip() for x in disabled_mods.split(',') if x.strip()]
        mods_info = get_mods_summary()
        active_mods = [m for m in mods_info['mods'] if m not in disabled_mods]
        from mod_loader import compute_mods_hash
        import hashlib as _hl
        _h = _hl.sha256()
        all_mods = load_all_mods()
        for mod in sorted(all_mods, key=lambda m: m.filename):
            if mod.filename in disabled_mods or mod.errors:
                continue
            try:
                with open(mod.filepath, 'rb') as f:
                    _h.update(f.read())
            except Exception:
                _h.update(mod.filename.encode('utf-8'))
        mods_hash = _h.hexdigest()
        players[sid] = {
            'nickname': name,
            'room_id': None,
            'status': initial_status,
            'mods_hash': mods_hash,
            'mods_list': active_mods,
        }
    if reconnect_room:
        emit('reconnect_available', {
            'room_id': reconnect_room.room_id,
            'old_sid': reconnect_old_sid,
            'opponent_nickname': reconnect_room.engine.player_names[1 - reconnect_room.disconnected_players[reconnect_old_sid]['player_index']] if reconnect_old_sid in reconnect_room.disconnected_players else '?',
        })
    join_room(sid)
    emit('login_ok', {'sid': sid, 'nickname': name})
    print(f"[服务器] 玩家 {name}(sid:{sid}) 已登录 (状态: {initial_status})")
    broadcast_lobby()


@socketio.on('disconnect')
def on_disconnect():
    global _next_room_id
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        nickname = player['nickname']
        if room_id is not None and room_id in rooms:
            room = rooms[room_id]
            pidx = room.player_index(sid)
            if pidx >= 0 and room.engine.phase not in ('game_over',):
                room.disconnected_players[sid] = {
                    'nickname': nickname,
                    'player_index': pidx,
                    'disconnect_time': time.time(),
                }
                for other_sid in room.player_sids:
                    if other_sid != sid and other_sid in players:
                        socketio.emit('opponent_disconnected', {
                            'reconnect_timeout': 120,
                            'opponent_nickname': nickname,
                        }, room=other_sid)
                timer = threading.Timer(120.0, reconnect_timeout, args=[room_id, sid])
                room.reconnect_timers[sid] = timer
                timer.daemon = True
                timer.start()
                both_dc = all(s in room.disconnected_players for s in room.player_sids[:2])
                if both_dc:
                    for t in room.reconnect_timers.values():
                        t.cancel()
                    room.reconnect_timers.clear()
                    room.both_dc_timer = threading.Timer(60.0, both_disconnected_cleanup, args=[room_id])
                    room.both_dc_timer.daemon = True
                    room.both_dc_timer.start()
                del players[sid]
                broadcast_lobby()
                return
            if pidx >= 0 and room.engine.phase == 'game_over':
                room._rematch_votes.discard(sid)
                for other_sid in room.player_sids:
                    if other_sid != sid and other_sid in players:
                        socketio.emit('opponent_disconnected', {'timeout': True}, room=other_sid)
                if not any(s in room.disconnected_players for s in room.player_sids if s != sid):
                    for t in room.reconnect_timers.values():
                        t.cancel()
                    del rooms[room_id]
                else:
                    for other_sid in room.player_sids:
                        if other_sid != sid and other_sid in players:
                            players[other_sid]['room_id'] = None
                            players[other_sid]['status'] = 'lobby'
                    for t in room.reconnect_timers.values():
                        t.cancel()
                    del rooms[room_id]
            if pidx < 0 and player.get('spectating_room') is not None:
                spec_room_id = player['spectating_room']
                if spec_room_id is not None and spec_room_id in rooms:
                    spec_room = rooms[spec_room_id]
                    if sid in spec_room.spectators:
                        spec_room.spectators.remove(sid)
                player['spectating_room'] = None
                player['spectate_perspective'] = 0
        for inv_sid, target_sid in list(invites.items()):
            if inv_sid == sid or target_sid == sid:
                del invites[inv_sid]
        del players[sid]
    broadcast_lobby()


@socketio.on('reconnect_accept')
def on_reconnect_accept(data):
    global _next_room_id
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = data.get('room_id')
        old_sid = data.get('old_sid')
        if room_id is None or room_id not in rooms:
            player['status'] = 'lobby'
            return
        room = rooms[room_id]
        if old_sid not in room.disconnected_players:
            player['status'] = 'lobby'
            return
        dc_info = room.disconnected_players[old_sid]
        if dc_info['nickname'] != player['nickname']:
            player['status'] = 'lobby'
            return
        if old_sid in room.reconnect_timers:
            room.reconnect_timers[old_sid].cancel()
            del room.reconnect_timers[old_sid]
        if hasattr(room, 'both_dc_timer') and room.both_dc_timer:
            room.both_dc_timer.cancel()
            room.both_dc_timer = None
        pidx = dc_info['player_index']
        room.player_sids[pidx] = sid
        del room.disconnected_players[old_sid]
        player['room_id'] = room_id
        player['status'] = 'in_game'
        join_room(sid)
        for other_sid in room.player_sids:
            if other_sid != sid and other_sid in players:
                socketio.emit('opponent_reconnected', {}, room=other_sid)
        send_game_state_to(room, pidx)
    broadcast_lobby()


@socketio.on('reconnect_decline')
def on_reconnect_decline(data):
    global _next_room_id
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = data.get('room_id')
        old_sid = data.get('old_sid')
        if room_id is None or room_id not in rooms:
            player['status'] = 'lobby'
            return
        room = rooms[room_id]
        if old_sid in room.disconnected_players:
            if old_sid in room.reconnect_timers:
                room.reconnect_timers[old_sid].cancel()
                del room.reconnect_timers[old_sid]
            del room.disconnected_players[old_sid]
        for other_sid in room.player_sids:
            if other_sid != sid and other_sid in players:
                socketio.emit('opponent_disconnected', {'timeout': True}, room=other_sid)
                players[other_sid]['room_id'] = None
                players[other_sid]['status'] = 'lobby'
        for t in room.reconnect_timers.values():
            t.cancel()
        del rooms[room_id]
        player['status'] = 'lobby'
    broadcast_lobby()


@socketio.on('invite')
def on_invite(data):
    sid = request.sid
    target_sid = data.get('target_sid')
    print(f"[服务器] 收到invite: sid={sid}, target_sid={target_sid}")
    with _lock:
        if sid not in players or target_sid not in players:
            print(f"[服务器] invite失败: 玩家不存在 sid={sid in players}, target={target_sid in players if target_sid else False}")
            emit('server_error', {'message': '邀请失败，请刷新页面重试'})
            return
        if sid == target_sid:
            return
        if sid in invites:
            print(f"[服务器] invite失败: 已有pending邀请 sid={sid}")
            return
        target = players[target_sid]
        if target['status'] != 'lobby':
            emit('server_error', {'message': '对方正在对局中'})
            return
        inviter = players[sid]
        if inviter.get('mods_hash') != target.get('mods_hash'):
            inviter_mods = inviter.get('mods_list', [])
            target_mods = target.get('mods_list', [])
            inviter_label = ', '.join(inviter_mods) if inviter_mods else '无模组'
            target_label = ', '.join(target_mods) if target_mods else '无模组'
            emit('server_error', {'message': f'模组不一致，无法对局。你的模组: {inviter_label}，对方模组: {target_label}'})
            return
        invites[sid] = target_sid
        inviter_name = players[sid]['nickname']
        print(f"[服务器] invite成功: {inviter_name} -> {target_sid}")
        result = socketio.emit('invite_received', {
            'inviter_sid': sid,
            'inviter_name': inviter_name,
        }, room=target_sid)
        print(f"[服务器] invite_received已发送: room={target_sid}, emit返回={result}")

        def _invite_timeout(inviter_sid):
            with _lock:
                if inviter_sid in invites:
                    del invites[inviter_sid]
                    print(f"[服务器] 邀请超时自动清除: inviter_sid={inviter_sid}")

        timer = threading.Timer(30.0, _invite_timeout, args=[sid])
        timer.daemon = True
        timer.start()


@socketio.on('accept_invite')
def on_accept_invite(data):
    global _next_room_id
    sid = request.sid
    inviter_sid = data.get('inviter_sid')
    print(f"[服务器] 收到accept_invite: sid={sid}, inviter_sid={inviter_sid}")
    with _lock:
        if inviter_sid not in players or sid not in players:
            print(f"[服务器] accept_invite失败: 玩家不存在 inviter={inviter_sid in players if inviter_sid else False}, accepter={sid in players}")
            return
        if inviter_sid not in invites or invites[inviter_sid] != sid:
            print(f"[服务器] accept_invite失败: 邀请不存在或不匹配 invites={invites}")
            return
        del invites[inviter_sid]
        inviter = players[inviter_sid]
        accepter = players[sid]
        if inviter['status'] != 'lobby' or accepter['status'] != 'lobby':
            return
        room_id = _next_room_id
        _next_room_id += 1
        room = GameRoom(room_id, [inviter_sid, sid])
        rooms[room_id] = room
        inviter['room_id'] = room_id
        inviter['status'] = 'in_game'
        accepter['room_id'] = room_id
        accepter['status'] = 'in_game'
        room.engine.player_names = [inviter['nickname'], accepter['nickname']]
        room.engine.start_draft()
        print(f"[服务器] 房间{room_id}创建成功: {inviter['nickname']} vs {accepter['nickname']}, 开始选牌")
        for pidx in range(len(room.player_sids)):
            psid = room.player_sids[pidx]
            socketio.emit('game_phase', {'phase': 'draft'}, room=psid)
            send_draft_state(room, pidx)
    broadcast_lobby()


@socketio.on('decline_invite')
def on_decline_invite(data):
    sid = request.sid
    inviter_sid = data.get('inviter_sid')
    with _lock:
        if inviter_sid in invites and invites[inviter_sid] == sid:
            del invites[inviter_sid]
            if inviter_sid in players:
                socketio.emit('invite_declined', {'target_sid': sid}, room=inviter_sid)


@socketio.on('chat')
def on_chat(data):
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        text = data.get('text', '')[:200]
        if not text.strip():
            return
        nickname = player['nickname']
        chat_data = {'nickname': nickname, 'text': text}
        if room_id is not None and room_id in rooms:
            room = rooms[room_id]
            for other_sid in room.player_sids:
                if other_sid in players:
                    socketio.emit('chat', chat_data, room=other_sid)
            for spid in room.spectators:
                if spid in players:
                    socketio.emit('chat', chat_data, room=spid)
        else:
            for other_sid, other_p in players.items():
                if other_p['status'] == 'lobby':
                    socketio.emit('chat', chat_data, room=other_sid)


@socketio.on('draft_pick')
def on_draft_pick(data):
    global _next_room_id
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        if room_id is None or room_id not in rooms:
            return
        room = rooms[room_id]
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
        def_id = data.get('def_id')
        if not def_id:
            return
        success = engine.draft_pick(pidx, def_id)
        if not success:
            if not engine.draft_options[pidx]:
                engine._generate_draft_options_for_player(pidx)
            success = engine.draft_pick(pidx, def_id)
        if success:
            for pi in range(len(room.player_sids)):
                send_draft_state(room, pi)
            if engine.phase == 'event_select':
                start_event_select(room)
        else:
            emit('server_error', {'message': '选牌失败'})


@socketio.on('select_opening_event')
def on_select_opening_event(data):
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        if room_id is None or room_id not in rooms:
            return
        room = rooms[room_id]
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
        event_id = data.get('event_id')
        sub_choice = data.get('sub_choice')
        if event_id is None:
            return
        success = engine.select_opening_event(pidx, event_id)
        if success:
            if sub_choice:
                engine.opening_event_sub_choices[pidx] = sub_choice
            if engine.both_events_selected():
                start_game(room)
            else:
                for pi in range(len(room.player_sids)):
                    send_event_state(room, pi)


@socketio.on('play_card')
def on_play_card(data):
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        if room_id is None or room_id not in rooms:
            return
        room = rooms[room_id]
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
        card_instance_id = data.get('card_instance_id')
        choice = data.get('choice')
        if card_instance_id is None:
            return
        result = engine.play_card(pidx, card_instance_id, choice)
        if result.get('needs_response'):
            broadcast_game_state(room)
            opp_pidx = 1 - pidx
            opp_sid = room.player_sids[opp_pidx]
            played_card = result['card']
            played_def = CARD_DEFS.get(played_card.get('def_id', ''), None)
            trigger_types = []
            if played_def:
                if played_def.card_type == 'thorn':
                    trigger_types.append('attack')
                elif played_def.card_type == 'bloom':
                    trigger_types.append('skill')
                if played_def.id in ('Sewage', 'MagicSewage'):
                    trigger_types.append('equipment_destroy')
            counter_cards = []
            for tt in trigger_types:
                counter_cards.extend(engine.get_counter_cards(opp_pidx, tt))
            if opp_sid in players:
                socketio.emit('response_request', {
                    'card': played_card,
                    'counter_cards': [c.to_dict() for c in counter_cards],
                }, room=opp_sid)
        elif result.get('needs_choice'):
            broadcast_game_state(room)
            emit('choice_request', {
                'choice_type': result['choice_type'],
                'card': result['card'],
            })
        elif result.get('success'):
            broadcast_game_state(room)
        else:
            emit('server_error', {'message': result.get('error', '出牌失败')})


@socketio.on('response')
def on_response(data):
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        if room_id is None or room_id not in rooms:
            return
        room = rooms[room_id]
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
        card_instance_id = data.get('card_instance_id')
        engine.handle_response(pidx, card_instance_id)
        broadcast_game_state(room)


@socketio.on('resolve_choice')
def on_resolve_choice(data):
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        if room_id is None or room_id not in rooms:
            return
        room = rooms[room_id]
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
        choice = data.get('choice')
        engine.resolve_choice(pidx, choice)
        broadcast_game_state(room)


@socketio.on('use_trigger')
def on_use_trigger(data):
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        if room_id is None or room_id not in rooms:
            return
        room = rooms[room_id]
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        engine = room.engine
        equipment_instance_id = data.get('equipment_instance_id')
        if equipment_instance_id is None:
            return
        result = engine.use_trigger(pidx, equipment_instance_id)
        if result.get('success'):
            broadcast_game_state(room)
        else:
            emit('server_error', {'message': result.get('error', '触发失败')})


@socketio.on('end_turn')
def on_end_turn(data):
    sid = request.sid
    print(f'[服务端] 收到end_turn, sid={sid}')
    try:
        with _lock:
            if sid not in players:
                print(f'[服务端] end_turn: 玩家未找到, sid={sid}')
                emit('server_error', {'message': '玩家未找到'})
                return
            player = players[sid]
            room_id = player.get('room_id')
            if room_id is None or room_id not in rooms:
                print(f'[服务端] end_turn: 未在对局中, room_id={room_id}')
                emit('server_error', {'message': '未在对局中'})
                return
            room = rooms[room_id]
            pidx = room.player_index(sid)
            if pidx < 0:
                print(f'[服务端] end_turn: 玩家不在对局中, pidx={pidx}')
                emit('server_error', {'message': '玩家不在对局中'})
                return
            engine = room.engine
            print(f'[服务端] end_turn: pidx={pidx}, phase={engine.phase}, current_player={engine.current_player}, pending_response={engine.pending_response is not None}')
            result = engine.end_turn(pidx)
            print(f'[服务端] end_turn result: {result}')
            broadcast_game_state(room)
            if not result.get('success'):
                emit('server_error', {'message': result.get('error', '结束回合失败')})
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f'[服务端] end_turn异常: {e}')
        emit('server_error', {'message': f'结束回合出错: {str(e)}'})


@socketio.on('surrender')
def on_surrender(data):
    sid = request.sid
    try:
        with _lock:
            if sid not in players:
                emit('server_error', {'message': '玩家未找到'})
                return
            player = players[sid]
            room_id = player.get('room_id')
            if room_id is None or room_id not in rooms:
                emit('server_error', {'message': '未在对局中'})
                return
            room = rooms[room_id]
            pidx = room.player_index(sid)
            if pidx < 0:
                emit('server_error', {'message': '玩家不在对局中'})
                return
            engine = room.engine
            result = engine.surrender(pidx)
            if result.get('success'):
                broadcast_game_state(room)
                for psid in room.player_sids:
                    if psid in players:
                        socketio.emit('game_phase', {'phase': 'game_over'}, room=psid)
            else:
                emit('server_error', {'message': result.get('error', '投降失败')})
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f'[服务端] surrender异常: {e}')
        emit('server_error', {'message': f'投降出错: {str(e)}'})


@socketio.on('rematch')
def on_rematch(data=None):
    sid = request.sid
    try:
        with _lock:
            if sid not in players:
                print(f'[服务端] rematch: sid {sid[:8]} 不在players中')
                return
            player = players[sid]
            room_id = player.get('room_id')
            if room_id is None or room_id not in rooms:
                print(f'[服务端] rematch: room_id={room_id} 无效, rooms={list(rooms.keys())}')
                return
            room = rooms[room_id]
            room._rematch_votes.add(sid)
            print(f'[服务端] rematch: {player["nickname"]} 投票重赛, 当前投票: {len(room._rematch_votes)}/{len(room.player_sids)}')
            for other_sid in room.player_sids:
                if other_sid != sid and other_sid in players:
                    socketio.emit('rematch_requested', {'player_name': player['nickname']}, room=other_sid)
            if len(room._rematch_votes) == len(room.player_sids):
                print(f'[服务端] rematch: 双方同意重赛, 开始新游戏')
                room._rematch_votes = set()
                room.engine = GameEngine()
                names = []
                for pidx, psid in enumerate(room.player_sids):
                    if psid in players:
                        names.append(players[psid]['nickname'])
                    else:
                        names.append(f'玩家{pidx + 1}')
                room.engine.player_names = names
                room.engine.start_draft()
                for pidx in range(len(room.player_sids)):
                    psid = room.player_sids[pidx]
                    if psid in players:
                        socketio.emit('game_phase', {'phase': 'draft'}, room=psid)
                        send_draft_state(room, pidx)
                print(f'[服务端] rematch: 新游戏已开始, draft_state已发送')
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f'[服务端] rematch异常: {e}')


@socketio.on('return_lobby')
def on_return_lobby(data):
    global _next_room_id
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        if player.get('spectating_room') is not None:
            _handle_leave_spectate_internal(sid)
            return
        room_id = player.get('room_id')
        if room_id is not None and room_id in rooms:
            room = rooms[room_id]
            for other_sid in room.player_sids:
                if other_sid != sid and other_sid in players:
                    socketio.emit('opponent_disconnected', {}, room=other_sid)
                    players[other_sid]['room_id'] = None
                    players[other_sid]['status'] = 'lobby'
            for t in room.reconnect_timers.values():
                t.cancel()
            del rooms[room_id]
        player['room_id'] = None
        player['status'] = 'lobby'
    broadcast_lobby()


@socketio.on('spectate')
def on_spectate(data):
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        if player['status'] != 'lobby':
            emit('server_error', {'message': '只能在大厅观战'})
            return
        room_id = data.get('room_id')
        if room_id is None or room_id not in rooms:
            emit('server_error', {'message': '对局不存在'})
            return
        room = rooms[room_id]
        phase = room.engine.phase
        if phase in ('draft', 'event_select'):
            emit('server_error', {'message': '此对局仍在选牌阶段，暂时无法观战'})
            return
        if phase not in ('action', 'draw', 'playing', 'response', 'choice'):
            emit('server_error', {'message': '该对局当前无法观战'})
            return
        player['status'] = 'spectating'
        player['spectating_room'] = room_id
        player['spectate_perspective'] = 0
        room.spectators.append(sid)
        p1 = '?'
        p2 = '?'
        if len(room.player_sids) > 0:
            sid0 = room.player_sids[0]
            if sid0 in players:
                p1 = players[sid0]['nickname']
            elif sid0 in room.disconnected_players:
                p1 = room.disconnected_players[sid0]['nickname']
        if len(room.player_sids) > 1:
            sid1 = room.player_sids[1]
            if sid1 in players:
                p2 = players[sid1]['nickname']
            elif sid1 in room.disconnected_players:
                p2 = room.disconnected_players[sid1]['nickname']
        emit('spectate_enter', {
            'room_id': room_id,
            'player1': p1,
            'player2': p2,
        })
        _send_spectate_state_internal(sid, room)


def _send_spectate_state_internal(spid, room):
    perspective = players[spid].get('spectate_perspective', 0)
    state = room.engine.get_public_state(for_player=perspective)
    state['spectating'] = True
    state['spectate_perspective'] = perspective
    if len(room.player_sids) >= 1 and room.player_sids[0] in players:
        state['player1_name'] = players[room.player_sids[0]]['nickname']
    else:
        state['player1_name'] = '?'
    if len(room.player_sids) >= 2 and room.player_sids[1] in players:
        state['player2_name'] = players[room.player_sids[1]]['nickname']
    else:
        state['player2_name'] = '?'
    socketio.emit('state_update', state, room=spid)


def _handle_leave_spectate_internal(sid):
    if sid not in players:
        return
    player = players[sid]
    room_id = player.get('spectating_room')
    if room_id is not None and room_id in rooms:
        room = rooms[room_id]
        if sid in room.spectators:
            room.spectators.remove(sid)
    player['spectating_room'] = None
    player['spectate_perspective'] = 0
    player['status'] = 'lobby'
    socketio.emit('spectate_leave', {}, room=sid)


@socketio.on('leave_spectate')
def on_leave_spectate(data):
    sid = request.sid
    with _lock:
        _handle_leave_spectate_internal(sid)
    broadcast_lobby()


@socketio.on('switch_spectate_perspective')
def on_switch_spectate_perspective(data):
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('spectating_room')
        if room_id is None or room_id not in rooms:
            return
        current = player.get('spectate_perspective', 0)
        player['spectate_perspective'] = 1 - current
        room = rooms[room_id]
        _send_spectate_state_internal(sid, room)


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
