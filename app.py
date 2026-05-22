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
from game_engine_2v2 import GameEngine2v2
from cards import (
    CardInstance, CARD_DEFS, DRAFT_RATIO, DECK_SIZE, build_draft_pool, generate_draft_options,
    INITIAL_HEALTH, INITIAL_ELIXIR, INITIAL_MAGIC, FIRST_PLAYER_ELIXIR,
    SECOND_PLAYER_HEALTH, INITIAL_HAND_SIZE, FIRST_PLAYER_HAND_SIZE,
)
from mod_loader import merge_mod_cards_to_card_defs, load_all_mods, save_mod, Mod
from card_i18n import apply_card_i18n_defaults, card_text, event_text

BASE_CARD_IDS = set(CARD_DEFS.keys())

try:
    merged = merge_mod_cards_to_card_defs()
    apply_card_i18n_defaults(CARD_DEFS)
    print(f'[startup] mods loaded, merged {len(merged)} cards')
except Exception as e:
    apply_card_i18n_defaults(CARD_DEFS)
    print(f'[startup] mod loading failed: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'garden_of_thorn_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

_lock = threading.Lock()
_next_room_id = 0

players = {}
rooms = {}
invites = {}
solo_sessions = {}
teams = {}
pending_team_matches = {}


class GameRoom:
    def __init__(self, room_id, player_sids, allowed_card_ids=None, mode='1v1'):
        self.room_id = room_id
        self.player_sids = list(player_sids)
        self.mode = mode
        if mode == '2v2':
            self.engine = GameEngine2v2()
        else:
            self.engine = GameEngine()
        self.engine.allowed_card_ids = set(allowed_card_ids) if allowed_card_ids is not None else None
        self.spectators = []
        self.disconnected_players = {}
        self.reconnect_timers = {}
        self._rematch_votes = set()
        self.team_assignments = None
        if mode == '2v2' and len(player_sids) == 4:
            self.team_assignments = [[0, 1], [2, 3]]

    def player_index(self, sid):
        if sid in self.player_sids:
            return self.player_sids.index(sid)
        return -1


def _display_width(s):
    w = 0
    for ch in s:
        if ('\u4e00' <= ch <= '\u9fff' or '\u3040' <= ch <= '\u30ff' or
                '\uac00' <= ch <= '\ud7af' or '\uff00' <= ch <= '\uffef' or
                '\u2000' <= ch <= '\u206f'):
            w += 2
        else:
            w += 1
    return w


def sanitize_nickname(raw):
    name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', raw)
    name = re.sub(r'[\u3000\s]+', '', name)
    name = re.sub(r'[^\w\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\-]', '', name)
    return name.strip()


def validate_nickname(name):
    if not name or _display_width(name) > 16:
        return False
    if re.match(r'^[\d]+$', name):
        return False
    if re.match(r'^[\-_]+$', name):
        return False
    if re.search(r'[\-_]{2,}', name):
        return False
    return True


def normalize_disabled_mods(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [x.strip() for x in value.split(',') if x.strip()]
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return []


def get_allowed_card_ids(disabled_mods=None):
    disabled = set(normalize_disabled_mods(disabled_mods))
    allowed = set(BASE_CARD_IDS)
    for mod in load_all_mods():
        if mod.errors:
            continue
        if mod.filename in disabled:
            continue
        for card in mod.cards:
            if card.id in CARD_DEFS:
                allowed.add(card.id)
    return allowed


def get_lobby_list():
    lobby = []
    for sid, p in players.items():
        if p['status'] == 'lobby':
            lobby.append({'sid': sid, 'nickname': p['nickname'], 'mode': p.get('mode', '1v1')})
    return lobby


def get_ongoing_games():
    games = []
    for rid, room in rooms.items():
        phase = room.engine.phase
        if phase in ('action', 'draw', 'response', 'choice', 'playing', 'draft', 'event_select'):
            player_names = []
            for s in room.player_sids:
                if s in players:
                    player_names.append(players[s]['nickname'])
                elif s in room.disconnected_players:
                    player_names.append(room.disconnected_players[s]['nickname'])
                else:
                    player_names.append('?')
            both_disconnected = all(s in room.disconnected_players for s in room.player_sids)
            game_info = {
                'room_id': rid,
                'player1': player_names[0] if len(player_names) > 0 else '?',
                'player2': player_names[1] if len(player_names) > 1 else '?',
                'round': room.engine.round_num,
                'phase': phase,
                'both_disconnected': both_disconnected,
                'mode': room.mode,
            }
            if room.mode == '2v2':
                game_info['player3'] = player_names[2] if len(player_names) > 2 else '?'
                game_info['player4'] = player_names[3] if len(player_names) > 3 else '?'
            games.append(game_info)
    return games


def broadcast_lobby():
    lobby_list = get_lobby_list()
    ongoing = get_ongoing_games()
    team_list = []
    seen_teams = set()
    for sid, team in teams.items():
        team_id = id(team)
        if team_id not in seen_teams:
            seen_teams.add(team_id)
            team_list.append({
                'leader': team['leader'],
                'members': [players[ms]['nickname'] for ms in team['members'] if ms in players],
                'member_sids': team['members'],
            })
    for sid, p in players.items():
        if p['status'] == 'lobby':
            socketio.emit('lobby_update', {
                'players': lobby_list,
                'your_sid': sid,
                'ongoing_games': ongoing,
                'teams': team_list,
                'your_team': teams[sid]['members'] if sid in teams else None,
                'your_team_leader': teams[sid]['leader'] if sid in teams else None,
                'your_mode': p.get('mode', '1v1'),
            }, room=sid)
    print("[server] debug")


def send_draft_state(room, pidx):
    sid = room.player_sids[pidx]
    if sid not in players:
        return
    engine = room.engine
    options = engine.draft_options[pidx]
    picks = engine.draft_picks[pidx]
    rerolls = engine.draft_rerolls[pidx]
    others_picks_count = {}
    if room.mode == '2v2':
        for i in range(4):
            if i != pidx:
                others_picks_count[i] = len(engine.draft_picks[i])
    else:
        opp_pidx = 1 - pidx
        others_picks_count[opp_pidx] = len(engine.draft_picks[opp_pidx])
    socketio.emit('draft_state', {
        'options': [c.to_dict() for c in options],
        'picks': picks,
        'rerolls': rerolls,
        'round': len(picks) + 1,
        'total_rounds': DECK_SIZE,
        'others_picks_count': others_picks_count,
        'mode': room.mode,
        'player_names': engine.player_names,
    }, room=sid)


def send_event_state(room, pidx):
    sid = room.player_sids[pidx]
    if sid not in players:
        return
    engine = room.engine
    events = engine.opening_event_options[pidx]
    others_selected = {}
    if room.mode == '2v2':
        for i in range(4):
            if i != pidx:
                others_selected[i] = engine.opening_event_picks[i] is not None
    else:
        opp_idx = 1 - pidx
        others_selected[opp_idx] = engine.opening_event_picks[opp_idx] is not None
    socketio.emit('event_select', {
        'events': events,
        'others_selected': others_selected,
        'my_pick': engine.opening_event_picks[pidx],
        'magic_options': engine.opening_event_magic_options[pidx],
        'draft_picks': engine.draft_picks[pidx],
        'mode': room.mode,
        'player_names': engine.player_names,
    }, room=sid)


def broadcast_game_state(room):
    for pidx, sid in enumerate(room.player_sids):
        if sid not in players:
            continue
        state = room.engine.get_public_state(pidx)
        state['your_id'] = pidx
        state['mode'] = room.mode
        if room.mode == '2v2':
            engine = room.engine
            teammate_id = engine.get_teammate(pidx)
            enemy_ids = engine.get_all_enemies(pidx)
            state['your_name'] = players[sid]['nickname'] if sid in players else '?'
            if teammate_id >= 0 and teammate_id < len(room.player_sids):
                tm_sid = room.player_sids[teammate_id]
                state['teammate_name'] = players[tm_sid]['nickname'] if tm_sid in players else '?'
            state['opponent_names'] = []
            for eid in enemy_ids:
                if eid < len(room.player_sids):
                    e_sid = room.player_sids[eid]
                    state['opponent_names'].append(players[e_sid]['nickname'] if e_sid in players else '?')
        else:
            opp_pidx = 1 - pidx
            opp_sid = room.player_sids[opp_pidx]
            if opp_sid in players:
                state['opponent_name'] = players[opp_sid]['nickname']
            else:
                state['opponent_name'] = '?'
            state['your_name'] = players[sid]['nickname'] if sid in players else '?'
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
        state['mode'] = room.mode
        if room.mode == '2v2':
            engine = room.engine
            teammate_id = engine.get_teammate(pidx)
            enemy_ids = engine.get_all_enemies(pidx)
            state['your_name'] = players[sid]['nickname'] if sid in players else '?'
            if teammate_id >= 0 and teammate_id < len(room.player_sids):
                tm_sid = room.player_sids[teammate_id]
                state['teammate_name'] = players[tm_sid]['nickname'] if tm_sid in players else '?'
            state['opponent_names'] = []
            for eid in enemy_ids:
                if eid < len(room.player_sids):
                    e_sid = room.player_sids[eid]
                    state['opponent_names'].append(players[e_sid]['nickname'] if e_sid in players else '?')
        else:
            opp_pidx = 1 - pidx
            opp_sid = room.player_sids[opp_pidx]
            if opp_sid in players:
                state['opponent_name'] = players[opp_sid]['nickname']
            else:
                state['opponent_name'] = '?'
            state['your_name'] = players[sid]['nickname'] if sid in players else '?'
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


def _build_solo_card(entry):
    if isinstance(entry, dict):
        card = CardInstance(def_id=entry.get('def_id'))
        card.instance_flags = set(entry.get('instance_flags', []))
        card.disabled_flags = set(entry.get('disabled_flags', []))
        return card
    return CardInstance(def_id=entry)


def _reset_player_for_solo(ps, deck_entries, is_first):
    ps.health = INITIAL_HEALTH if is_first else SECOND_PLAYER_HEALTH
    ps.max_health = ps.health
    ps.base_max_health = ps.health
    ps.elixir = FIRST_PLAYER_ELIXIR if is_first else INITIAL_ELIXIR
    ps.max_elixir = 10
    ps.magic = INITIAL_MAGIC
    ps.max_magic = 10
    ps.armor = 0
    ps.poison = 0
    ps.fire = 0
    ps.vulnerable = 0
    ps.toxic = 0
    ps.triangle_stacks = 0
    ps.dodge = 0
    ps.nazar_active = False
    ps.nazar_big_hits = 0
    ps.equipment_protection = 0
    ps.magic_battery_m_this_turn = 0
    ps.coffee_first_use = True
    ps.invincible = False
    ps.skip_turn = False
    ps.damage_multiplier = 1.0
    ps.bandage_active = False
    ps.bandage_death_pending = False
    ps.attack_blocked = 0
    ps.untargetable = False
    ps.sponge_active = False
    ps.shovel_active = False
    ps.attack_only = 0
    ps.enemy_draw_reduction = 0
    ps.enemy_e_reduction = 0
    ps.hand = []
    ps.deck = []
    for entry in deck_entries:
        def_id = entry.get('def_id') if isinstance(entry, dict) else entry
        if def_id in CARD_DEFS:
            ps.deck.append(_build_solo_card(entry))
    ps.discard = []
    ps.exile = []
    ps.equipment = []
    ps.cards_played_this_turn = {}
    ps.negate_next_skill = False
    ps.is_first_player = is_first


def create_solo_engine(deck0, deck1, event0=None, event1=None, sub0=None, sub1=None):
    engine = GameEngine()
    engine.player_names = ['Player A', 'Player B']
    engine.phase = 'playing'
    force_first = [idx for idx, event_id in enumerate((event0, event1)) if event_id == 7]
    engine.first_player = force_first[0] if len(force_first) == 1 else 0
    engine.current_player = engine.first_player
    engine.round_num = 1
    engine.opening_event_picks = [event0, event1]
    engine.opening_event_sub_choices = [sub0, sub1]
    engine.log = []
    engine.pending_response = None
    engine.pending_choice = None
    _reset_player_for_solo(engine.players[0], deck0, engine.first_player == 0)
    _reset_player_for_solo(engine.players[1], deck1, engine.first_player == 1)
    for i in range(2):
        if engine.opening_event_picks[i] is not None:
            engine._apply_opening_event(i)
    for i in range(2):
        if i == engine.first_player:
            hand_size = FIRST_PLAYER_HAND_SIZE
            if engine.opening_event_picks[i] == 7 and len(force_first) == 1:
                hand_size = 4
                engine.players[i].elixir += 3
            engine.players[i].draw_cards(hand_size)
        else:
            engine.players[i].draw_cards(INITIAL_HAND_SIZE)
    engine.log_msg(f"单人训练场开始！{engine.pn(engine.first_player)}先手。")
    engine.log_msg(f"=== 第{engine.round_num}回合 ===")
    engine._start_player_turn(engine.first_player)
    return engine


def send_solo_state(sid, perspective=None):
    engine = solo_sessions.get(sid)
    if not engine:
        return
    if perspective is None:
        perspective = engine.current_player if not engine.game_over else 0
    state = engine.get_public_state(perspective)
    state['your_id'] = perspective
    state['your_name'] = 'Player A' if perspective == 0 else 'Player B'
    state['opponent_name'] = 'Player B' if perspective == 0 else 'Player A'
    state['solo'] = True
    socketio.emit('solo_state', state, room=sid)


def emit_solo_response_request(sid, engine, pidx, played_card):
    opp_pidx = 1 - pidx
    played_def = CARD_DEFS.get(played_card.get('def_id', ''), None)
    trigger_types = []
    if played_def:
        if played_def.card_type == 'thorn':
            trigger_types.append('thorn')
        elif played_def.card_type == 'bloom':
            trigger_types.append('bloom')
        if played_def.id in ('Sewage', 'MagicSewage'):
            trigger_types.append('equipment_destroy')
    counter_cards = []
    for tt in trigger_types:
        counter_cards.extend(engine.get_counter_cards(opp_pidx, tt))
    socketio.emit('response_request', {
        'card': played_card,
        'counter_cards': [c.to_dict() for c in counter_cards],
    }, room=sid)


def broadcast_spectate_state(room):
    for spid in room.spectators:
        if spid not in players:
            continue
        perspective = players[spid].get('spectate_perspective', 0)
        state = room.engine.get_public_state(for_player=perspective)
        state['spectating'] = True
        state['spectate_perspective'] = perspective
        for i, psid in enumerate(room.player_sids):
            state[f'player{i + 1}_name'] = players[psid]['nickname'] if psid in players else room.disconnected_players.get(psid, {}).get('nickname', '?')
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
    fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'fonts')
    mimetype = 'font/woff2' if filename.endswith('.woff2') else None
    response = send_from_directory(fonts_dir, filename, mimetype=mimetype)
    if filename.endswith('.woff2') or filename.endswith('.ttf'):
        response.headers['Cache-Control'] = 'public, max-age=604800'
    return response


@app.route('/api/cards')
def api_cards():
    allowed_card_ids = get_allowed_card_ids(request.args.get('disabled_mods', ''))
    result = {}
    for def_id, card_def in CARD_DEFS.items():
        if def_id not in allowed_card_ids:
            continue
        card_payload = {
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
        card_payload.update(card_text(def_id, card_payload))
        result[def_id] = card_payload
    return jsonify(result)


@app.route('/api/opening-events')
def api_opening_events():
    events = []
    for event_id in sorted(GameEngine.OPENING_EVENTS.keys()):
        events.append(event_text(event_id, dict(GameEngine.OPENING_EVENTS[event_id])))
    return jsonify({
        'events': events,
        'magic_pool': list(GameEngine.MAGIC_CARD_POOL),
    })


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
        return jsonify({'success': False, 'error': 'invalid data'}), 400
    mod = Mod(data.get('filepath', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mods', 'new_mod.json')))
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
                    p_names.append('(离线玩家)')
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
            return jsonify({'success': False, 'error': 'player not found'}), 404
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
    socketio.emit('kicked', {'reason': 'kicked by admin'}, room=sid)
    broadcast_lobby()
    return jsonify({'success': True, 'nickname': nickname})


@app.route('/api/admin/broadcast', methods=['POST'])
def admin_broadcast():
    data = request.get_json(force=True)
    msg = data.get('message', '')
    if not msg.strip():
        return jsonify({'success': False, 'error': 'empty message'}), 400
    socketio.emit('server_broadcast', {'message': msg})
    return jsonify({'success': True})


@app.route('/api/admin/room/<int:room_id>/skip', methods=['POST'])
def admin_skip(room_id):
    with _lock:
        if room_id not in rooms:
            return jsonify({'success': False, 'error': 'room not found'}), 404
        room = rooms[room_id]
        e = room.engine
        if e.game_over:
            return jsonify({'success': False, 'error': 'game already over'}), 400
        if e.phase in ('action', 'draw'):
            e._end_player_turn(e.current_player)
            broadcast_game_state(room)
            return jsonify({'success': True, 'phase': e.phase, 'current_player': e.current_player})
        return jsonify({'success': False, 'error': f'cannot skip during phase {e.phase}'}), 400


@app.route('/api/admin/room/<int:room_id>/endgame', methods=['POST'])
def admin_endgame(room_id):
    data = request.get_json(force=True)
    winner = data.get('winner', 0)
    if winner not in (0, 1):
        return jsonify({'success': False, 'error': 'winner must be 0 or 1'}), 400
    with _lock:
        if room_id not in rooms:
            return jsonify({'success': False, 'error': 'room not found'}), 404
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
            return jsonify({'success': False, 'error': 'room not found'}), 404
        room = rooms[room_id]
        e = room.engine
        if e.phase not in ('draft', 'event_select'):
            return jsonify({'success': False, 'error': f'cannot fill draft during phase {e.phase}'}), 400
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
        return jsonify({'success': False, 'error': 'player must be 0 or 1'}), 400
    with _lock:
        if room_id not in rooms:
            return jsonify({'success': False, 'error': 'room not found'}), 404
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
            return jsonify({'success': False, 'error': f'unknown attribute {key}'}), 400
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
    print("[server] debug")


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
                emit('server_error', {'message': 'Operation failed'})
    except Exception as e:
        print("[server] debug")
        import traceback
        traceback.print_exc()


@socketio.on('login')
def on_login(data):
    global _next_room_id
    sid = request.sid
    raw_name = data.get('nickname', '')
    name = sanitize_nickname(raw_name)
    if not validate_nickname(name):
        emit('login_fail', {'reason': 'Invalid nickname. Use 1-16 display-width characters; avoid pure numbers, pure symbols, or repeated -/_.'})
        return
    with _lock:
        for p in players.values():
            if p['nickname'] == name:
                emit('login_fail', {'reason': 'Nickname already exists'})
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
        disabled_mods = normalize_disabled_mods(data.get('disabled_mods', []))
        preferred_mode = data.get('mode', '1v1')
        if preferred_mode not in ('1v1', '2v2'):
            preferred_mode = '1v1'
        import hashlib as _hl
        _h = _hl.sha256()
        all_mods = load_all_mods()
        active_mods = []
        for mod in sorted(all_mods, key=lambda m: m.filename):
            if mod.filename in disabled_mods or mod.errors:
                continue
            active_mods.append(mod.info.name if mod.info else mod.filename)
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
            'disabled_mods': disabled_mods,
            'allowed_card_ids': get_allowed_card_ids(disabled_mods),
            'mode': preferred_mode,
        }
    if reconnect_room:
        emit('reconnect_available', {
            'room_id': reconnect_room.room_id,
            'old_sid': reconnect_old_sid,
            'opponent_nickname': reconnect_room.engine.player_names[1 - reconnect_room.disconnected_players[reconnect_old_sid]['player_index']] if reconnect_old_sid in reconnect_room.disconnected_players else '?',
        })
    join_room(sid)
    emit('login_ok', {'sid': sid, 'nickname': name})
    print("[server] debug")
    broadcast_lobby()


@socketio.on('form_team')
def on_form_team(data):
    sid = request.sid
    target_sid = data.get('target_sid')
    with _lock:
        if sid not in players or target_sid not in players:
            return
        if players[sid]['status'] != 'lobby' or players[target_sid]['status'] != 'lobby':
            return
        if players[sid].get('mode') != '2v2' or players[target_sid].get('mode') != '2v2':
            return
        if sid in teams or target_sid in teams:
            return
        socketio.emit('team_invite', {'from_sid': sid, 'from_name': players[sid]['nickname']}, room=target_sid)


@socketio.on('set_mode')
def on_set_mode(data):
    sid = request.sid
    mode = data.get('mode', '1v1')
    with _lock:
        if sid not in players:
            return
        if mode not in ('1v1', '2v2'):
            return
        players[sid]['mode'] = mode
        if mode == '1v1' and sid in teams:
            team = teams[sid]
            leader = team['leader']
            members = list(team['members'])
            keys_to_remove = [k for k in pending_team_matches if k[0] == leader or k[1] == leader]
            for k in keys_to_remove:
                del pending_team_matches[k]
            for member_sid in members:
                if member_sid in teams:
                    del teams[member_sid]
                if member_sid in players:
                    socketio.emit('team_disbanded', {}, room=member_sid)
        broadcast_lobby()


@socketio.on('accept_team')
def on_accept_team(data):
    sid = request.sid
    leader_sid = data.get('from_sid')
    with _lock:
        if sid not in players or leader_sid not in players:
            return
        if players[sid]['status'] != 'lobby' or players[leader_sid]['status'] != 'lobby':
            return
        if sid in teams or leader_sid in teams:
            return
        team_id = f"team_{leader_sid}"
        teams[leader_sid] = {'members': [leader_sid, sid], 'leader': leader_sid}
        teams[sid] = teams[leader_sid]
        for member_sid in [leader_sid, sid]:
            socketio.emit('team_formed', {
                'team_id': team_id,
                'members': [players[ms]['nickname'] for ms in teams[leader_sid]['members']],
                'member_sids': teams[leader_sid]['members'],
                'leader': leader_sid,
            }, room=member_sid)
        broadcast_lobby()


@socketio.on('decline_team')
def on_decline_team(data):
    sid = request.sid
    leader_sid = data.get('from_sid')
    with _lock:
        if leader_sid not in players:
            return
        socketio.emit('team_declined', {'from_name': players[sid]['nickname'] if sid in players else '?'}, room=leader_sid)


@socketio.on('leave_team')
def on_leave_team(data=None):
    sid = request.sid
    with _lock:
        if sid not in teams:
            return
        team = teams[sid]
        leader = team['leader']
        members = list(team['members'])
        keys_to_remove = [k for k in pending_team_matches if k[0] == leader or k[1] == leader]
        for k in keys_to_remove:
            del pending_team_matches[k]
        for member_sid in members:
            if member_sid in teams:
                del teams[member_sid]
            if member_sid in players:
                socketio.emit('team_disbanded', {}, room=member_sid)
        broadcast_lobby()


@socketio.on('invite_team')
def on_invite_team(data):
    sid = request.sid
    target_team_leader = data.get('target_team_leader')
    with _lock:
        if sid not in teams or target_team_leader not in teams:
            return
        my_team = teams[sid]
        target_team = teams[target_team_leader]
        my_team_all_2v2 = all(players.get(ms, {}).get('mode') == '2v2' for ms in my_team['members'] if ms in players)
        target_team_all_2v2 = all(players.get(ms, {}).get('mode') == '2v2' for ms in target_team['members'] if ms in players)
        if not my_team_all_2v2 or not target_team_all_2v2:
            return
        match_key = (min(my_team['leader'], target_team['leader']),
                     max(my_team['leader'], target_team['leader']))
        if match_key in pending_team_matches:
            return
        pending_team_matches[match_key] = True
        for member_sid in target_team['members']:
            if member_sid in players:
                socketio.emit('team_match_invite', {
                    'from_leader': my_team['leader'],
                    'from_team': [players[ms]['nickname'] for ms in my_team['members'] if ms in players],
                    'from_team_sids': my_team['members'],
                }, room=member_sid)


@socketio.on('accept_team_match')
def on_accept_team_match(data):
    global _next_room_id
    sid = request.sid
    from_leader = data.get('from_leader')
    with _lock:
        if sid not in teams or from_leader not in teams:
            return
        my_team = teams[sid]
        other_team = teams[from_leader]
        if sid not in my_team['members']:
            return
        if from_leader not in other_team['members']:
            return
        match_key = (min(my_team['leader'], other_team['leader']),
                     max(my_team['leader'], other_team['leader']))
        pending_team_matches.pop(match_key, None)
        for member_sid in my_team['members']:
            if member_sid != sid and member_sid in players:
                socketio.emit('team_match_accepted', {}, room=member_sid)
        all_sids = other_team['members'] + my_team['members']
        for s in all_sids:
            if s not in players or players[s]['status'] != 'lobby':
                return
        room_id = _next_room_id
        _next_room_id += 1
        allowed = None
        first_sid = all_sids[0]
        if first_sid in players and players[first_sid].get('allowed_card_ids'):
            allowed = players[first_sid]['allowed_card_ids']
        room = GameRoom(room_id, all_sids, allowed, mode='2v2')
        rooms[room_id] = room
        for s in all_sids:
            players[s]['status'] = 'in_game'
            players[s]['room_id'] = room_id
            join_room(room_id)
            if s in teams:
                del teams[s]
        room.engine.player_names = [players[s]['nickname'] for s in all_sids]
        room.engine.start_draft()
        for i, s in enumerate(all_sids):
            send_draft_state(room, i)
        broadcast_lobby()


@socketio.on('decline_team_match')
def on_decline_team_match(data):
    sid = request.sid
    from_leader = data.get('from_leader')
    with _lock:
        if from_leader not in teams:
            return
        other_team = teams[from_leader]
        my_team = teams.get(sid)
        if my_team:
            match_key = (min(my_team['leader'], other_team['leader']),
                         max(my_team['leader'], other_team['leader']))
            pending_team_matches.pop(match_key, None)
        for member_sid in other_team['members']:
            if member_sid in players:
                socketio.emit('team_match_declined', {'from_name': players[sid]['nickname'] if sid in players else '?'}, room=member_sid)


@socketio.on('disconnect')
def on_disconnect():
    global _next_room_id
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        solo_sessions.pop(sid, None)
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
    print("[server] debug")
    with _lock:
        if sid not in players or target_sid not in players:
            print("[server] debug")
            emit('server_error', {'message': 'Operation failed'})
            return
        if sid == target_sid:
            return
        if sid in invites:
            print("[server] debug")
            return
        target = players[target_sid]
        if target['status'] != 'lobby':
            emit('server_error', {'message': 'Operation failed'})
            return
        inviter = players[sid]
        if inviter.get('mode', '1v1') != '1v1' or target.get('mode', '1v1') != '1v1':
            emit('server_error', {'message': 'Operation failed'})
            return
        if inviter.get('mods_hash') != target.get('mods_hash'):
            inviter_mods = inviter.get('mods_list', [])
            target_mods = target.get('mods_list', [])
            inviter_label = ', '.join(inviter_mods) if inviter_mods else 'no mods'
            target_label = ', '.join(target_mods) if target_mods else 'no mods'
            emit('server_error', {'message': 'Operation failed'})
            return
        invites[sid] = target_sid
        inviter_name = players[sid]['nickname']
        print("[server] debug")
        result = socketio.emit('invite_received', {
            'inviter_sid': sid,
            'inviter_name': inviter_name,
        }, room=target_sid)
        print("[server] debug")

        def _invite_timeout(inviter_sid):
            with _lock:
                if inviter_sid in invites:
                    del invites[inviter_sid]
                    print("[server] debug")

        timer = threading.Timer(30.0, _invite_timeout, args=[sid])
        timer.daemon = True
        timer.start()


@socketio.on('accept_invite')
def on_accept_invite(data):
    global _next_room_id
    sid = request.sid
    inviter_sid = data.get('inviter_sid')
    print("[server] debug")
    with _lock:
        if inviter_sid not in players or sid not in players:
            print("[server] debug")
            return
        if inviter_sid not in invites or invites[inviter_sid] != sid:
            print("[server] debug")
            return
        del invites[inviter_sid]
        inviter = players[inviter_sid]
        accepter = players[sid]
        if inviter['status'] != 'lobby' or accepter['status'] != 'lobby':
            return
        room_id = _next_room_id
        _next_room_id += 1
        allowed_card_ids = inviter.get('allowed_card_ids') or get_allowed_card_ids(inviter.get('disabled_mods', []))
        room = GameRoom(room_id, [inviter_sid, sid], allowed_card_ids)
        rooms[room_id] = room
        inviter['room_id'] = room_id
        inviter['status'] = 'in_game'
        accepter['room_id'] = room_id
        accepter['status'] = 'in_game'
        room.engine.player_names = [inviter['nickname'], accepter['nickname']]
        room.engine.start_draft()
        print("[server] debug")
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
        spectating_room = player.get('spectating_room')
        text = data.get('text', '')[:200]
        if not text.strip():
            return
        nickname = player['nickname']
        is_spectator = player.get('status') == 'spectating'
        chat_data = {'nickname': nickname, 'text': text, 'is_spectator': is_spectator}
        if room_id is not None and room_id in rooms:
            room = rooms[room_id]
            for other_sid in room.player_sids:
                if other_sid in players:
                    socketio.emit('chat', chat_data, room=other_sid)
            for spid in room.spectators:
                if spid in players:
                    socketio.emit('chat', chat_data, room=spid)
        elif spectating_room is not None and spectating_room in rooms:
            room = rooms[spectating_room]
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
            emit('server_error', {'message': 'Operation failed'})


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


@socketio.on('solo_start')
def on_solo_start(data):
    sid = request.sid
    deck0 = data.get('deck0', []) if data else []
    deck1 = data.get('deck1', []) if data else []
    event0 = data.get('event0') if data else None
    event1 = data.get('event1') if data else None
    sub0 = data.get('sub0') if data else None
    sub1 = data.get('sub1') if data else None
    if len(deck0) != DECK_SIZE or len(deck1) != DECK_SIZE:
        emit('server_error', {'message': 'Operation failed'})
        return
    allowed_card_ids = get_allowed_card_ids([])
    if sid in players:
        allowed_card_ids = players[sid].get('allowed_card_ids') or allowed_card_ids
    def _valid_entry(entry):
        def_id = entry.get('def_id') if isinstance(entry, dict) else entry
        return def_id in CARD_DEFS and def_id in allowed_card_ids
    if any(not _valid_entry(entry) for entry in deck0 + deck1):
        emit('server_error', {'message': 'Operation failed'})
        return
    with _lock:
        solo_sessions[sid] = create_solo_engine(deck0, deck1, event0, event1, sub0, sub1)
        if sid in players:
            players[sid]['status'] = 'solo'
        socketio.emit('game_phase', {'phase': 'playing', 'solo': True}, room=sid)
        send_solo_state(sid)


@socketio.on('solo_play_card')
def on_solo_play_card(data):
    sid = request.sid
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            emit('server_error', {'message': 'Operation failed'})
            return
        pidx = engine.current_player
        result = engine.play_card(pidx, data.get('card_instance_id'), data.get('choice'))
        if result.get('needs_response'):
            send_solo_state(sid, 1 - pidx)
            emit_solo_response_request(sid, engine, pidx, result['card'])
        elif result.get('needs_choice'):
            send_solo_state(sid)
            socketio.emit('choice_request', {
                'choice_type': result['choice_type'],
                'card': result['card'],
            }, room=sid)
        elif result.get('success'):
            send_solo_state(sid)
        else:
            emit('server_error', {'message': 'Operation failed'})


@socketio.on('solo_response')
def on_solo_response(data):
    sid = request.sid
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            return
        responder = 1 - engine.pending_response['player_id'] if engine.pending_response else engine.current_player
        engine.handle_response(responder, data.get('card_instance_id') if data else None)
        send_solo_state(sid)


@socketio.on('solo_resolve_choice')
def on_solo_resolve_choice(data):
    sid = request.sid
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            return
        pidx = engine.pending_choice.get('player_id', engine.current_player) if engine.pending_choice else engine.current_player
        engine.resolve_choice(pidx, data.get('choice') if data else None)
        send_solo_state(sid)


@socketio.on('solo_use_trigger')
def on_solo_use_trigger(data):
    sid = request.sid
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            return
        result = engine.use_trigger(engine.current_player, data.get('equipment_instance_id'))
        if not result.get('success'):
            emit('server_error', {'message': 'Operation failed'})
        send_solo_state(sid)


@socketio.on('solo_end_turn')
def on_solo_end_turn(data=None):
    sid = request.sid
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine:
            return
        result = engine.end_turn(engine.current_player)
        if not result.get('success'):
            emit('server_error', {'message': 'Operation failed'})
        send_solo_state(sid)


@socketio.on('solo_set_next_draw')
def on_solo_set_next_draw(data):
    sid = request.sid
    def_ids = []
    if data:
        if isinstance(data.get('def_ids'), list):
            def_ids = [x for x in data.get('def_ids') if x]
        elif data.get('def_id'):
            def_ids = [data.get('def_id')]
    with _lock:
        engine = solo_sessions.get(sid)
        if not engine or not def_ids:
            return
        ps = engine.players[engine.current_player]
        picked = []
        for did in def_ids:
            idx2 = next((i for i, c in enumerate(ps.deck) if c.def_id == did), -1)
            if idx2 >= 0:
                picked.append(ps.deck.pop(idx2))
        if not picked:
            emit('server_error', {'message': 'Operation failed'})
            return
        for c in reversed(picked):
            ps.deck.insert(0, c)
        names = '、'.join([c.name_cn for c in picked])
        engine.log_msg(f"训练场：{engine.pn(engine.current_player)} 设置下次抽牌：{names}")
        send_solo_state(sid)
        return
        idx = next((i for i, c in enumerate(ps.deck) if c.def_id == def_id), -1)
        if idx < 0:
            emit('server_error', {'message': 'Operation failed'})
            return
        card = ps.deck.pop(idx)
        ps.deck.insert(0, card)
        engine.log_msg(f"训练场：{engine.pn(engine.current_player)} 设置下次抽牌：{card.name_cn}")
        send_solo_state(sid)


@socketio.on('solo_pause')
def on_solo_pause(data=None):
    sid = request.sid
    solo_sessions.pop(sid, None)
    if sid in players:
        players[sid]['status'] = 'lobby'
    socketio.emit('solo_paused', {}, room=sid)


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
        target_player_id = data.get('target_player_id', -1)
        if card_instance_id is None:
            return
        if room.mode == '2v2':
            result = engine.play_card(pidx, card_instance_id, target_player_id=target_player_id, choice=choice)
        else:
            result = engine.play_card(pidx, card_instance_id, choice)
        if result.get('needs_ally_consent'):
            broadcast_game_state(room)
            target_pidx = result.get('target_player_id')
            if isinstance(target_pidx, int) and 0 <= target_pidx < len(room.player_sids):
                target_sid = room.player_sids[target_pidx]
                if target_sid in players:
                    socketio.emit('ally_consent_request', {
                        'card': result.get('card'),
                        'from_player': pidx,
                        'from_name': players[sid]['nickname'],
                    }, room=target_sid)
        elif result.get('needs_response'):
            broadcast_game_state(room)
            played_card = result['card']
            played_def = CARD_DEFS.get(played_card.get('def_id', ''), None)
            trigger_types = []
            if played_def:
                if played_def.card_type == 'thorn':
                    trigger_types.append('thorn')
                elif played_def.card_type == 'bloom':
                    trigger_types.append('bloom')
                if played_def.id in ('Sewage', 'MagicSewage'):
                    trigger_types.append('equipment_destroy')
            if room.mode == '2v2':
                by_responder = {}
                for c in (engine.pending_response or {}).get('counter_cards', []):
                    by_responder.setdefault(c.get('responder_id'), []).append(c)
                for responder_id, counter_cards in by_responder.items():
                    if isinstance(responder_id, int) and 0 <= responder_id < len(room.player_sids):
                        r_sid = room.player_sids[responder_id]
                        if r_sid in players:
                            socketio.emit('response_request', {
                                'card': played_card,
                                'counter_cards': counter_cards,
                            }, room=r_sid)
            else:
                opp_pidx = 1 - pidx
                counter_cards = []
                for tt in trigger_types:
                    counter_cards.extend(engine.get_counter_cards(opp_pidx, tt))
                opp_sid = room.player_sids[opp_pidx]
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
                'target_player_id': result.get('target_player_id'),
            })
        elif result.get('success'):
            broadcast_game_state(room)
        else:
            emit('server_error', {'message': 'Operation failed'})


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


@socketio.on('ally_consent_response')
def on_ally_consent_response(data):
    sid = request.sid
    with _lock:
        if sid not in players:
            return
        player = players[sid]
        room_id = player.get('room_id')
        if room_id is None or room_id not in rooms:
            return
        room = rooms[room_id]
        if room.mode != '2v2':
            return
        pidx = room.player_index(sid)
        if pidx < 0:
            return
        accepted = bool(data.get('accepted')) if data else False
        result = room.engine.handle_ally_consent(pidx, accepted)
        if result.get('needs_response'):
            broadcast_game_state(room)
            played_card = result['card']
            by_responder = {}
            for c in (room.engine.pending_response or {}).get('counter_cards', []):
                by_responder.setdefault(c.get('responder_id'), []).append(c)
            for responder_id, counter_cards in by_responder.items():
                if isinstance(responder_id, int) and 0 <= responder_id < len(room.player_sids):
                    r_sid = room.player_sids[responder_id]
                    if r_sid in players:
                        socketio.emit('response_request', {
                            'card': played_card,
                            'counter_cards': counter_cards,
                        }, room=r_sid)
        elif result.get('needs_choice'):
            broadcast_game_state(room)
            requester_sid = room.player_sids[result.get('player_id', room.engine.current_player)] if result.get('player_id') is not None else sid
            socketio.emit('choice_request', {
                'choice_type': result['choice_type'],
                'card': result['card'],
                'target_player_id': result.get('target_player_id'),
            }, room=requester_sid)
        else:
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
        target_player_id = data.get('target_player_id', -1)
        if room.mode == '2v2':
            result = engine.use_trigger(pidx, equipment_instance_id, target_player_id=target_player_id)
        else:
            result = engine.use_trigger(pidx, equipment_instance_id)
        if result.get('success'):
            broadcast_game_state(room)
        else:
            emit('server_error', {'message': 'Operation failed'})


@socketio.on('end_turn')
def on_end_turn(data):
    sid = request.sid
    print("[server] debug")
    try:
        with _lock:
            if sid not in players:
                print("[server] debug")
                emit('server_error', {'message': 'Operation failed'})
                return
            player = players[sid]
            room_id = player.get('room_id')
            if room_id is None or room_id not in rooms:
                print("[server] debug")
                emit('server_error', {'message': 'Operation failed'})
                return
            room = rooms[room_id]
            pidx = room.player_index(sid)
            if pidx < 0:
                print("[server] debug")
                emit('server_error', {'message': 'Operation failed'})
                return
            engine = room.engine
            print("[server] debug")
            result = engine.end_turn(pidx)
            print("[server] debug")
            broadcast_game_state(room)
            if not result.get('success'):
                emit('server_error', {'message': 'Operation failed'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("[server] debug")
        emit('server_error', {'message': 'Operation failed'})


@socketio.on('surrender')
def on_surrender(data):
    sid = request.sid
    try:
        with _lock:
            if sid not in players:
                emit('server_error', {'message': 'Operation failed'})
                return
            player = players[sid]
            room_id = player.get('room_id')
            if room_id is None or room_id not in rooms:
                emit('server_error', {'message': 'Operation failed'})
                return
            room = rooms[room_id]
            pidx = room.player_index(sid)
            if pidx < 0:
                emit('server_error', {'message': 'Operation failed'})
                return
            engine = room.engine
            result = engine.surrender(pidx)
            if result.get('success'):
                broadcast_game_state(room)
                for psid in room.player_sids:
                    if psid in players:
                        socketio.emit('game_phase', {'phase': 'game_over'}, room=psid)
            else:
                emit('server_error', {'message': 'Operation failed'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("[server] debug")
        emit('server_error', {'message': 'Operation failed'})


@socketio.on('rematch')
def on_rematch(data=None):
    sid = request.sid
    try:
        with _lock:
            if sid not in players:
                print("[server] debug")
                return
            player = players[sid]
            room_id = player.get('room_id')
            if room_id is None or room_id not in rooms:
                print("[server] debug")
                return
            room = rooms[room_id]
            room._rematch_votes.add(sid)
            print("[server] debug")
            for other_sid in room.player_sids:
                if other_sid != sid and other_sid in players:
                    socketio.emit('rematch_requested', {'player_name': player['nickname']}, room=other_sid)
            if len(room._rematch_votes) == len(room.player_sids):
                print("[server] debug")
                room._rematch_votes = set()
                room.engine = GameEngine2v2() if room.mode == '2v2' else GameEngine()
                names = []
                for pidx, psid in enumerate(room.player_sids):
                    if psid in players:
                        names.append(players[psid]['nickname'])
                    else:
                        names.append(f'Player {pidx + 1}')
                room.engine.player_names = names
                room.engine.start_draft()
                for pidx in range(len(room.player_sids)):
                    psid = room.player_sids[pidx]
                    if psid in players:
                        socketio.emit('game_phase', {'phase': 'draft'}, room=psid)
                        send_draft_state(room, pidx)
                print("[server] debug")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("[server] debug")


@socketio.on('return_lobby')
def on_return_lobby(data=None):
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
            emit('server_error', {'message': 'Operation failed'})
            return
        room_id = data.get('room_id')
        if room_id is None or room_id not in rooms:
            emit('server_error', {'message': 'Operation failed'})
            return
        room = rooms[room_id]
        phase = room.engine.phase
        if phase in ('draft', 'event_select'):
            emit('server_error', {'message': 'Operation failed'})
            return
        if phase not in ('action', 'draw', 'playing', 'response', 'choice'):
            emit('server_error', {'message': 'Operation failed'})
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
    for i, psid in enumerate(room.player_sids):
        state[f'player{i + 1}_name'] = players[psid]['nickname'] if psid in players else room.disconnected_players.get(psid, {}).get('nickname', '?')
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
def on_leave_spectate(data=None):
    sid = request.sid
    print("[server] debug")
    with _lock:
        _handle_leave_spectate_internal(sid)
    broadcast_lobby()


@socketio.on('switch_spectate_perspective')
def on_switch_spectate_perspective(data=None):
    sid = request.sid
    print("[server] debug")
    with _lock:
        if sid not in players:
            print("[server] debug")
            return
        player = players[sid]
        room_id = player.get('spectating_room')
        if room_id is None or room_id not in rooms:
            print("[server] debug")
            return
        current = player.get('spectate_perspective', 0)
        player['spectate_perspective'] = (current + 1) % max(1, len(room.player_sids))
        print("[server] debug")
        room = rooms[room_id]
        _send_spectate_state_internal(sid, room)


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
