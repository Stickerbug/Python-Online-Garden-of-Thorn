import socket
import threading
import time
import re
import json
import sys
import wcwidth
from typing import Dict, List, Optional
from network import (
    NetworkMessage, NetworkConnection, create_server, DEFAULT_PORT
)
from game_engine import GameEngine
from cards import CardInstance, CARD_DEFS, DRAFT_RATIO, build_draft_pool, generate_draft_options

DISCOVERY_PORT = 4160

def server_print(*args, **kwargs):
    sys.stdout.write('\r' + ' ' * 80 + '\r')
    print(*args, **kwargs)
    sys.stdout.write('> ')
    sys.stdout.flush()


def sanitize(nickname: str) -> str:
    nickname = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', nickname)
    nickname = re.sub(r'[\u3000\s]+', '', nickname)
    nickname = re.sub(r'[^\w\u4e00-\u9fff\-]', '', nickname)
    return nickname.strip()


def validate_nickname(raw_name: str, max_width: int = 12) -> tuple:
    name = sanitize(raw_name)
    if not name:
        return False, 0, name
    if '--' in name or '__' in name:
        return False, 0, name
    display_width = wcwidth.wcswidth(name)
    if display_width < 0:
        return False, 0, name
    return display_width <= max_width, display_width, name


def _arg_offset(args: str, arg_index: int) -> int:
    parts = args.strip().split()
    pos = 0
    stripped = args.lstrip()
    offset = len(args) - len(stripped)
    remaining = stripped
    for i in range(arg_index):
        if i >= len(parts):
            break
        idx = remaining.find(parts[i])
        if idx >= 0:
            offset += idx + len(parts[i])
            remaining = remaining[idx + len(parts[i]):]
    return offset


class GameRoom:
    def __init__(self, room_id: int, player_ids: List[int]):
        self.room_id = room_id
        self.player_ids = player_ids
        self.engine = GameEngine()
        self.draft_ready = {pid: False for pid in player_ids}
        self.spectators: List[int] = []

    def player_index(self, player_id: int) -> int:
        return self.player_ids.index(player_id) if player_id in self.player_ids else -1


class GameServer:
    def __init__(self, host: str = '0.0.0.0', port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.running = False
        self._restarting = False
        self.server_sock = None
        self._lock = threading.Lock()
        self._next_pid = 0
        self._next_room = 0
        self.players: Dict[int, dict] = {}
        self.rooms: Dict[int, GameRoom] = {}
        self.invites: Dict[int, int] = {}
        self._selected_room: Optional[int] = None
        self._broadcast_sock = None

    def start(self):
        self.server_sock = create_server(self.host, self.port)
        self.server_sock.listen(20)
        self.running = True
        server_print(f"[服务器] 监听 {self.host}:{self.port}")
        accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        accept_thread.start()
        broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        broadcast_thread.start()

    def _broadcast_loop(self):
        try:
            self._broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception as e:
            server_print(f"[服务器] 广播socket创建失败: {e}")
            return
        while self.running:
            try:
                info = json.dumps({
                    'port': self.port,
                    'players': len(self.players),
                    'rooms': len(self.rooms),
                })
                self._broadcast_sock.sendto(info.encode('utf-8'), ('<broadcast>', DISCOVERY_PORT))
            except Exception:
                pass
            time.sleep(2)
        if self._broadcast_sock:
            try:
                self._broadcast_sock.close()
            except:
                pass

    def _accept_loop(self):
        while self.running:
            try:
                self.server_sock.settimeout(1.0)
                client_sock, addr = self.server_sock.accept()
                client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                try:
                    client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
                    client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                    client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
                except (AttributeError, OSError):
                    pass
                conn = NetworkConnection(client_sock)
                recv_thread = threading.Thread(target=self._recv_loop, args=(conn,), daemon=True)
                recv_thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    server_print(f"[服务器] 接受连接错误: {e}")

    def _recv_loop(self, conn: NetworkConnection):
        pid = None
        try:
            while self.running and conn.connected:
                messages = conn.receive_all()
                for msg in messages:
                    if msg.msg_type == 'ping':
                        conn.send(NetworkMessage('pong', {}))
                        continue
                    if pid is None:
                        if msg.msg_type == 'login':
                            pid = self._handle_login(conn, msg)
                            if pid is None:
                                conn.close()
                                return
                        continue
                    self._handle_message(pid, msg)
                time.sleep(0.01)
        except Exception as e:
            server_print(f"[服务器] 接收错误: {e}")
        finally:
            if pid is not None:
                self._handle_disconnect(pid)

    def _handle_login(self, conn: NetworkConnection, msg: NetworkMessage) -> Optional[int]:
        raw_name = msg.data.get('nickname', '')
        valid, width, name = validate_nickname(raw_name)
        if not valid or not name:
            conn.send(NetworkMessage('login_fail', {'reason': '昵称无效或过长'}))
            return None
        with self._lock:
            for p in self.players.values():
                if p['nickname'] == name:
                    conn.send(NetworkMessage('login_fail', {'reason': '昵称已被使用'}))
                    return None
            pid = self._next_pid
            self._next_pid += 1
            self.players[pid] = {
                'nickname': name,
                'conn': conn,
                'room_id': None,
                'status': 'lobby',
            }
        conn.send(NetworkMessage('login_ok', {'player_id': pid, 'nickname': name}))
        server_print(f"[服务器] 玩家 {name}(ID:{pid}) 已登录")
        self._broadcast_lobby()
        return pid

    def _handle_disconnect(self, pid: int):
        with self._lock:
            if pid not in self.players:
                return
            player = self.players[pid]
            room_id = player['room_id']
            if room_id is not None and room_id in self.rooms:
                room = self.rooms[room_id]
                for other_pid in room.player_ids:
                    if other_pid != pid and other_pid in self.players:
                        self.players[other_pid]['conn'].send(
                            NetworkMessage('opponent_disconnected', {}))
                        self.players[other_pid]['room_id'] = None
                        self.players[other_pid]['status'] = 'lobby'
                del self.rooms[room_id]
            for inv_pid, target_pid in list(self.invites.items()):
                if inv_pid == pid or target_pid == pid:
                    del self.invites[inv_pid]
            del self.players[pid]
        server_print(f"[服务器] 玩家ID:{pid} 断开连接")
        self._broadcast_lobby()

    def _handle_message(self, pid: int, msg: NetworkMessage):
        with self._lock:
            if msg.msg_type == 'invite':
                self._handle_invite(pid, msg)
            elif msg.msg_type == 'accept_invite':
                self._handle_accept_invite(pid, msg)
            elif msg.msg_type == 'decline_invite':
                self._handle_decline_invite(pid, msg)
            elif msg.msg_type == 'return_lobby':
                self._handle_return_lobby(pid)
            elif msg.msg_type == 'rematch':
                self._handle_rematch(pid)
            elif msg.msg_type == 'spectate':
                self._handle_spectate(pid, msg)
            elif msg.msg_type == 'leave_spectate':
                self._handle_leave_spectate(pid)
            elif msg.msg_type == 'switch_spectate_perspective':
                self._handle_switch_spectate_perspective(pid)
            else:
                player = self.players.get(pid)
                if not player or player['room_id'] is None:
                    return
                room = self.rooms.get(player['room_id'])
                if not room:
                    return
                pidx = room.player_index(pid)
                if pidx < 0:
                    return
                self._handle_game_message(pid, pidx, room, msg)

    def _handle_invite(self, pid: int, msg: NetworkMessage):
        target_pid = msg.data.get('target_id')
        if target_pid is None or target_pid not in self.players:
            return
        if pid == target_pid:
            return
        target = self.players[target_pid]
        if target['status'] != 'lobby':
            self.players[pid]['conn'].send(
                NetworkMessage('error', {'message': '对方正在对局中'}))
            return
        self.invites[pid] = target_pid
        inviter_name = self.players[pid]['nickname']
        target['conn'].send(NetworkMessage('invite_received', {
            'inviter_id': pid,
            'inviter_name': inviter_name,
        }))

    def _handle_accept_invite(self, pid: int, msg: NetworkMessage):
        inviter_pid = msg.data.get('inviter_id')
        if inviter_pid is None or inviter_pid not in self.players:
            return
        if inviter_pid not in self.invites or self.invites[inviter_pid] != pid:
            return
        del self.invites[inviter_pid]
        inviter = self.players[inviter_pid]
        if inviter['status'] != 'lobby' or self.players[pid]['status'] != 'lobby':
            return
        room_id = self._next_room
        self._next_room += 1
        room = GameRoom(room_id, [inviter_pid, pid])
        self.rooms[room_id] = room
        inviter['room_id'] = room_id
        inviter['status'] = 'in_game'
        self.players[pid]['room_id'] = room_id
        self.players[pid]['status'] = 'in_game'
        room.engine.start_draft()
        for pidx, p in enumerate(room.player_ids):
            self.players[p]['conn'].send(NetworkMessage('game_phase', {'phase': 'draft'}))
            self._send_draft_state_to(room, pidx)
        self._broadcast_lobby()

    def _handle_decline_invite(self, pid: int, msg: NetworkMessage):
        inviter_pid = msg.data.get('inviter_id')
        if inviter_pid is not None and inviter_pid in self.invites and self.invites[inviter_pid] == pid:
            del self.invites[inviter_pid]
            if inviter_pid in self.players:
                self.players[inviter_pid]['conn'].send(
                    NetworkMessage('invite_declined', {'target_id': pid}))

    def _handle_return_lobby(self, pid: int):
        player = self.players.get(pid)
        if not player:
            return
        if player.get('spectating_room') is not None:
            self._handle_leave_spectate(pid)
            return
        room_id = player['room_id']
        if room_id is not None and room_id in self.rooms:
            room = self.rooms[room_id]
            for other_pid in room.player_ids:
                if other_pid != pid and other_pid in self.players:
                    self.players[other_pid]['conn'].send(
                        NetworkMessage('opponent_disconnected', {}))
                    self.players[other_pid]['room_id'] = None
                    self.players[other_pid]['status'] = 'lobby'
            del self.rooms[room_id]
        player['room_id'] = None
        player['status'] = 'lobby'
        self._broadcast_lobby()

    def _handle_spectate(self, pid: int, msg: NetworkMessage):
        player = self.players.get(pid)
        if not player or player['status'] != 'lobby':
            self.players[pid]['conn'].send(NetworkMessage('error', {'message': '只能在大厅观战'}))
            return
        room_id = msg.data.get('room_id')
        if room_id is None or room_id not in self.rooms:
            self.players[pid]['conn'].send(NetworkMessage('error', {'message': '对局不存在'}))
            return
        room = self.rooms[room_id]
        phase = room.engine.phase
        if phase not in ('action', 'draw'):
            self.players[pid]['conn'].send(NetworkMessage('error', {'message': '该对局当前无法观战'}))
            return
        player['status'] = 'spectating'
        player['spectating_room'] = room_id
        room.spectators.append(pid)
        p1 = self.players.get(room.player_ids[0], {}).get('nickname', '?')
        p2 = self.players.get(room.player_ids[1], {}).get('nickname', '?')
        self.players[pid]['conn'].send(NetworkMessage('spectate_enter', {
            'room_id': room_id,
            'player1': p1,
            'player2': p2,
        }))
        self._send_spectate_state(pid, room)

    def _handle_leave_spectate(self, pid: int):
        player = self.players.get(pid)
        if not player:
            return
        room_id = player.get('spectating_room')
        if room_id is not None and room_id in self.rooms:
            room = self.rooms[room_id]
            if pid in room.spectators:
                room.spectators.remove(pid)
        player['spectating_room'] = None
        player['spectate_perspective'] = 0
        player['status'] = 'lobby'
        self.players[pid]['conn'].send(NetworkMessage('spectate_leave', {}))
        self._broadcast_lobby()

    def _handle_switch_spectate_perspective(self, pid: int):
        player = self.players.get(pid)
        if not player or player.get('spectating_room') is None:
            return
        room_id = player['spectating_room']
        if room_id not in self.rooms:
            return
        current = player.get('spectate_perspective', 0)
        new_perspective = 1 - current
        player['spectate_perspective'] = new_perspective
        room = self.rooms[room_id]
        self._send_spectate_state(pid, room)

    def _send_spectate_state(self, pid: int, room: GameRoom):
        engine = room.engine
        perspective = self.players[pid].get('spectate_perspective', 0)
        state = engine.get_public_state(for_player=perspective)
        state['spectating'] = True
        state['spectate_perspective'] = perspective
        state['player1_name'] = self.players.get(room.player_ids[0], {}).get('nickname', '?')
        state['player2_name'] = self.players.get(room.player_ids[1], {}).get('nickname', '?')
        self.players[pid]['conn'].send(NetworkMessage('state_update', state))

    def _broadcast_spectate_state(self, room: GameRoom):
        for spid in room.spectators:
            if spid in self.players:
                perspective_data = self.players[spid].get('spectate_perspective', 0)
                engine = room.engine
                state = engine.get_public_state(for_player=perspective_data)
                state['spectating'] = True
                state['spectate_perspective'] = perspective_data
                state['player1_name'] = self.players.get(room.player_ids[0], {}).get('nickname', '?')
                state['player2_name'] = self.players.get(room.player_ids[1], {}).get('nickname', '?')
                self.players[spid]['conn'].send(NetworkMessage('state_update', state))

    def _handle_rematch(self, pid: int):
        player = self.players.get(pid)
        if not player or player['room_id'] is None:
            return
        room = self.rooms.get(player['room_id'])
        if not room:
            return
        if not hasattr(room, '_rematch_votes'):
            room._rematch_votes = set()
        room._rematch_votes.add(pid)
        for other_pid in room.player_ids:
            if other_pid != pid and other_pid in self.players:
                self.players[other_pid]['conn'].send(
                    NetworkMessage('rematch_requested', {'player_name': player['nickname']}))
        if len(room._rematch_votes) == len(room.player_ids):
            room._rematch_votes = set()
            room.engine = GameEngine()
            room.draft_ready = {p: False for p in room.player_ids}
            room.engine.start_draft()
            for pidx, p in enumerate(room.player_ids):
                self.players[p]['conn'].send(NetworkMessage('game_phase', {'phase': 'draft'}))
                self._send_draft_state_to(room, pidx)

    def _handle_game_message(self, pid: int, pidx: int, room: GameRoom, msg: NetworkMessage):
        engine = room.engine
        if msg.msg_type == 'draft_pick':
            def_id = msg.data.get('def_id')
            if def_id:
                success = engine.draft_pick(pidx, def_id)
                if not success:
                    if not engine.draft_options[pidx]:
                        engine._generate_draft_options_for_player(pidx)
                    success = engine.draft_pick(pidx, def_id)
                if success:
                    room.draft_ready[pidx] = True
                    for pi, p in enumerate(room.player_ids):
                        self._send_draft_state_to(room, pi)
                    if engine.phase == 'event_select':
                        self._start_event_select(room)
                else:
                    self.players[pid]['conn'].send(
                        NetworkMessage('error', {'message': '选牌失败'}))
        elif msg.msg_type == 'draft_reroll':
            success = engine.draft_reroll(pidx)
            if success:
                for pi, p in enumerate(room.player_ids):
                    self._send_draft_state_to(room, pi)
            else:
                self.players[pid]['conn'].send(
                    NetworkMessage('error', {'message': '重选次数已用完'}))
        elif msg.msg_type == 'select_opening_event':
            event_id = msg.data.get('event_id')
            sub_choice = msg.data.get('sub_choice')
            if event_id is not None:
                success = engine.select_opening_event(pidx, event_id)
                if success:
                    if sub_choice:
                        engine.opening_event_sub_choices[pidx] = sub_choice
                    if engine.both_events_selected():
                        self._start_game(room)
                    else:
                        for pi, p in enumerate(room.player_ids):
                            self._send_event_state_to(room, pi)
        elif msg.msg_type == 'play_card':
            card_instance_id = msg.data.get('card_instance_id')
            choice = msg.data.get('choice')
            if card_instance_id is not None:
                result = engine.play_card(pidx, card_instance_id, choice)
                if result.get('needs_response'):
                    self._broadcast_game_state(room)
                    opp_pidx = 1 - pidx
                    opp_pid = room.player_ids[opp_pidx]
                    played_card = result['card']
                    played_def = CARD_DEFS.get(played_card.get('def_id', ''), None)
                    trigger_types = []
                    if played_def:
                        if played_def.card_type == 'attack':
                            trigger_types.append('attack')
                        elif played_def.card_type == 'skill':
                            trigger_types.append('skill')
                        if played_def.id in ('Sewage', 'MagicSewage'):
                            trigger_types.append('equipment_destroy')
                    counter_cards = []
                    for tt in trigger_types:
                        counter_cards.extend(engine.get_counter_cards(opp_pidx, tt))
                    self.players[opp_pid]['conn'].send(NetworkMessage('response_request', {
                        'card': played_card,
                        'counter_cards': [c.to_dict() for c in counter_cards],
                    }))
                elif result.get('needs_choice'):
                    self._broadcast_game_state(room)
                    self.players[pid]['conn'].send(NetworkMessage('choice_request', {
                        'choice_type': result['choice_type'],
                        'card': result['card'],
                    }))
                elif result.get('success'):
                    self._broadcast_game_state(room)
                else:
                    self.players[pid]['conn'].send(
                        NetworkMessage('error', {'message': result.get('error', '出牌失败')}))
        elif msg.msg_type == 'response':
            card_instance_id = msg.data.get('card_instance_id')
            engine.handle_response(pidx, card_instance_id)
            self._broadcast_game_state(room)
        elif msg.msg_type == 'resolve_choice':
            choice = msg.data.get('choice')
            engine.resolve_choice(pidx, choice)
            self._broadcast_game_state(room)
        elif msg.msg_type == 'use_trigger':
            equipment_instance_id = msg.data.get('equipment_instance_id')
            if equipment_instance_id is not None:
                result = engine.use_trigger(pidx, equipment_instance_id)
                if result.get('success'):
                    self._broadcast_game_state(room)
                else:
                    self.players[pid]['conn'].send(
                        NetworkMessage('error', {'message': result.get('error', '触发失败')}))
        elif msg.msg_type == 'end_turn':
            result = engine.end_turn(pidx)
            self._broadcast_game_state(room)
            if not result.get('success'):
                self.players[pid]['conn'].send(
                    NetworkMessage('error', {'message': result.get('error', '结束回合失败')}))
        elif msg.msg_type == 'surrender':
            result = engine.surrender(pidx)
            if result.get('success'):
                self._broadcast_game_state(room)
                for p_id in room.player_ids:
                    self.players[p_id]['conn'].send(NetworkMessage('game_phase', {'phase': 'game_over'}))
            else:
                self.players[pid]['conn'].send(
                    NetworkMessage('error', {'message': result.get('error', '投降失败')}))

    def _send_draft_state_to(self, room: GameRoom, pidx: int):
        pid = room.player_ids[pidx]
        engine = room.engine
        options = engine.draft_options[pidx]
        picks = engine.draft_picks[pidx]
        rerolls = engine.draft_rerolls[pidx]
        opp_pidx = 1 - pidx
        self.players[pid]['conn'].send(NetworkMessage('draft_state', {
            'options': [c.to_dict() for c in options],
            'picks': picks,
            'rerolls': rerolls,
            'round': len(picks) + 1,
            'total_rounds': 15,
            'opponent_picks_count': len(engine.draft_picks[opp_pidx]),
        }))

    def _broadcast_game_state(self, room: GameRoom):
        for pidx, pid in enumerate(room.player_ids):
            state = room.engine.get_public_state(pidx)
            state['your_id'] = pidx
            opp_pidx = 1 - pidx
            opp_pid = room.player_ids[opp_pidx]
            state['opponent_name'] = self.players[opp_pid]['nickname']
            self.players[pid]['conn'].send(NetworkMessage('state_update', state))
        self._broadcast_spectate_state(room)

    def _start_event_select(self, room: GameRoom):
        engine = room.engine
        for pi, pid in enumerate(room.player_ids):
            self._send_event_state_to(room, pi)

    def _send_event_state_to(self, room: GameRoom, player_idx: int):
        engine = room.engine
        pid = room.player_ids[player_idx]
        events = engine.opening_event_options[player_idx]
        opp_idx = 1 - player_idx
        opp_selected = engine.opening_event_picks[opp_idx] is not None
        self.players[pid]['conn'].send(NetworkMessage('event_select', {
            'events': events,
            'opponent_selected': opp_selected,
            'my_pick': engine.opening_event_picks[player_idx],
            'magic_options': engine.opening_event_magic_options[player_idx],
            'draft_picks': engine.draft_picks[player_idx],
        }))

    def _start_game(self, room: GameRoom):
        room.engine.start_game()
        for pid in room.player_ids:
            self.players[pid]['conn'].send(NetworkMessage('game_phase', {'phase': 'playing'}))
        self._broadcast_game_state(room)

    def _broadcast_lobby(self):
        lobby_list = []
        for pid, p in self.players.items():
            if p['status'] == 'lobby':
                lobby_list.append({'player_id': pid, 'nickname': p['nickname']})
        ongoing_games = []
        for rid, room in self.rooms.items():
            phase = room.engine.phase
            if phase in ('action', 'draw', 'response', 'choice'):
                p1 = self.players.get(room.player_ids[0], {}).get('nickname', '?')
                p2 = self.players.get(room.player_ids[1], {}).get('nickname', '?')
                ongoing_games.append({
                    'room_id': rid,
                    'player1': p1,
                    'player2': p2,
                    'round': room.engine.round_num,
                })
        for pid, p in self.players.items():
            if p['status'] == 'lobby':
                p['conn'].send(NetworkMessage('lobby_update', {
                    'players': lobby_list,
                    'your_id': pid,
                    'ongoing_games': ongoing_games,
                }))

    def stop(self):
        self.running = False
        for p in self.players.values():
            p['conn'].close()
        if self.server_sock:
            try:
                self.server_sock.close()
            except:
                pass

    def cmd_help(self, _args: str):
        lines = [
            "=== 服务器命令 ===",
            "基础:",
            "  help          显示此帮助",
            "  ls            列出在线玩家和对局",
            "  kick <pid>    踢出玩家(按ID)",
            "  say <msg>     向所有玩家广播消息",
            "  stop          关闭服务器",
            "  restart       重启服务器",
            "",
            "对局(需先 game 选中):",
            "  game [rid]    选中/查看对局(无参=当前选中)",
            "  phase         查看当前阶段",
            "  skip          强制跳过当前阶段/回合",
            "  draftfill     强制随机选完剩余的牌",
            "  endgame <0|1> 强制结束游戏(0=先手胜,1=后手胜)",
            "  set <p> <k> <v>  设置玩家属性(p=0/1, k=h/e/m)",
            "  give <p> <card>  给玩家加牌(p=0/1)",
            "  log           查看最近日志",
        ]
        return '\n'.join(lines)

    def cmd_ls(self, args: str):
        if args.strip():
            return self._extra_args_error("ls", args)
        with self._lock:
            lines = ["--- 在线玩家 ---"]
            if not self.players:
                lines.append("  (无)")
            for pid, p in self.players.items():
                room_str = f" 房间{p['room_id']}" if p['room_id'] is not None else ""
                lines.append(f"  ID:{pid} {p['nickname']} [{p['status']}]{room_str}")
            lines.append("")
            lines.append("--- 对局 ---")
            if not self.rooms:
                lines.append("  (无)")
            for rid, room in self.rooms.items():
                e = room.engine
                sel = " <--" if rid == self._selected_room else ""
                p_names = []
                for pid in room.player_ids:
                    if pid in self.players:
                        p_names.append(self.players[pid]['nickname'])
                    else:
                        p_names.append(f"ID:{pid}(离线)")
                lines.append(f"  房间{rid}: {' vs '.join(p_names)} | 阶段:{e.phase} | 回合:{e.round_num}{sel}")
        return '\n'.join(lines)

    def cmd_kick(self, args: str):
        parts = args.strip().split()
        if not parts:
            return ("不完整的命令：kick", 0, 0, "用法: kick <pid>")
        try:
            pid = int(parts[0])
        except ValueError:
            return (f"无效的pid：{parts[0]}", 0, len(parts[0]), "pid必须是数字")
        with self._lock:
            if pid not in self.players:
                return (f"不存在的玩家pid：{parts[0]}", 0, len(parts[0]), None)
            name = self.players[pid]['nickname']
            self._handle_disconnect(pid)
        return f"已踢出 {name}(ID:{pid})"

    def cmd_say(self, args: str):
        msg = args.strip()
        if not msg:
            return ("不完整的命令：say", 0, 0, "用法: say <消息>")
        with self._lock:
            for p in self.players.values():
                try:
                    p['conn'].send(NetworkMessage('server_broadcast', {'message': msg}))
                except:
                    pass
        return f"已广播: {msg}"

    def cmd_game(self, args: str):
        parts = args.strip().split()
        if not parts:
            with self._lock:
                if len(self.rooms) == 1:
                    self._selected_room = list(self.rooms.keys())[0]
                    return self._room_info(self.rooms[self._selected_room])
                if self._selected_room is None:
                    if not self.rooms:
                        return "当前没有对局"
                    return ("不完整的命令：game", 0, 0, "有多个房间，请指定: game <rid>")
                room = self.rooms.get(self._selected_room)
                if not room:
                    self._selected_room = None
                    return "选中的对局已不存在"
                return self._room_info(room)
        try:
            rid = int(parts[0])
        except ValueError:
            return (f"无效的rid：{parts[0]}", 0, len(parts[0]), "rid必须是数字")
        with self._lock:
            if rid not in self.rooms:
                return (f"不存在的房间rid：{parts[0]}", 0, len(parts[0]), None)
            self._selected_room = rid
            return self._room_info(self.rooms[rid])

    def _room_info(self, room: GameRoom) -> str:
        e = room.engine
        lines = [f"=== 房间 {room.room_id} ==="]
        for i, pid in enumerate(room.player_ids):
            if pid in self.players:
                name = self.players[pid]['nickname']
            else:
                name = f"ID:{pid}(离线)"
            ps = e.players[i]
            lines.append(f"  P{i} {name}: H={ps.health}/{ps.max_health} E={ps.elixir}/{ps.max_elixir} M={ps.magic}/{ps.max_magic} 手牌={len(ps.hand)}")
        lines.append(f"  阶段: {e.phase} | 回合: {e.round_num} | 先手: P{e.first_player} | 当前: P{e.current_player}")
        if e.game_over:
            lines.append(f"  游戏结束! 胜者: P{e.winner}")
        return '\n'.join(lines)

    def _no_room_error(self, cmd_len=0):
        return ("未选中对局", -999, cmd_len, "先用 game <rid> 选中")

    def _extra_args_error(self, cmd_name, args):
        parts = args.strip().split()
        return (f"多余的参数：{parts[0]}", 0, len(parts[0]), f"{cmd_name} 不需要参数")

    def cmd_phase(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        if args.strip():
            return self._extra_args_error("phase", args)
        e = room.engine
        return f"阶段: {e.phase} | 回合: {e.round_num} | 当前行动: P{e.current_player}"

    def cmd_skip(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        if args.strip():
            return self._extra_args_error("skip", args)
        e = room.engine
        if e.game_over:
            return "游戏已结束"
        if e.phase == 'draft':
            return "选牌阶段请用 draftfill"
        if e.phase in ('action', 'draw'):
            e._end_player_turn(e.current_player)
            if e.game_over:
                self._broadcast_game_state(room)
                return f"已跳过P{e.current_player}的回合，游戏结束!"
            self._broadcast_game_state(room)
            return f"已跳过回合，当前: P{e.current_player} 阶段:{e.phase}"
        return f"当前阶段 {e.phase} 无法跳过"

    def cmd_draftfill(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        if args.strip():
            return self._extra_args_error("draftfill", args)
        e = room.engine
        if e.phase not in ('draft', 'event_select'):
            return f"当前不是选牌阶段(当前:{e.phase})"
        filled = 0
        while e.phase == 'draft':
            made_progress = False
            for pidx in range(2):
                if len(e.draft_picks[pidx]) < 15:
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
            self._start_game(room)
        return f"已自动选牌{filled}张，游戏开始!"

    def cmd_endgame(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if not parts:
            return ("不完整的命令：endgame", 0, 0, "用法: endgame <0|1> (0=先手胜, 1=后手胜)")
        try:
            winner = int(parts[0])
        except ValueError:
            return (f"无效的参数：{parts[0]}", 0, len(parts[0]), "参数必须是0或1")
        if winner not in (0, 1):
            return (f"无效的参数：{parts[0]}", 0, len(parts[0]), "参数必须是0或1")
        e = room.engine
        loser = 1 - winner
        e.players[loser].health = 0
        e._check_game_over()
        self._broadcast_game_state(room)
        w_name = self._player_name_in_room(room, winner)
        return f"游戏结束! {w_name}(P{winner})获胜"

    def cmd_set(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if len(parts) < 3:
            return ("不完整的命令：set", 0, 0, "用法: set <0|1> <h|e|m> <值>")
        try:
            pidx = int(parts[0])
        except ValueError:
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        key = parts[1].lower()
        try:
            val = int(parts[2])
        except ValueError:
            return (f"无效的值：{parts[2]}", _arg_offset(args, 2), len(parts[2]), "值必须是数字")
        if pidx not in (0, 1):
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        e = room.engine
        ps = e.players[pidx]
        name = self._player_name_in_room(room, pidx)
        if key == 'h':
            ps.health = val
            ps.base_max_health = max(ps.base_max_health, val)
            ps.max_health = max(ps.max_health, val)
            e._check_game_over()
        elif key == 'e':
            ps.elixir = val
            ps.max_elixir = max(ps.max_elixir, val)
        elif key == 'm':
            ps.magic = val
            ps.max_magic = max(ps.max_magic, val)
        else:
            return (f"未知的属性：{key}", _arg_offset(args, 1), len(parts[1]), "可用: h/e/m")
        self._broadcast_game_state(room)
        return f"{name}(P{pidx}) {key}={val}"

    def cmd_give(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if len(parts) < 2:
            return ("不完整的命令：give", 0, 0, "用法: give <0|1> <卡牌ID>")
        try:
            pidx = int(parts[0])
        except ValueError:
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        if pidx not in (0, 1):
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        card_id = parts[1]
        if card_id not in CARD_DEFS:
            return (f"未知的卡牌：{card_id}", _arg_offset(args, 1), len(parts[1]), None)
        e = room.engine
        ps = e.players[pidx]
        card = CardInstance(def_id=card_id)
        ps.hand.append(card)
        name = self._player_name_in_room(room, pidx)
        self._broadcast_game_state(room)
        return f"已给 {name}(P{pidx}) 一张 {CARD_DEFS[card_id].name_cn}"

    def cmd_log(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        if args.strip():
            return self._extra_args_error("log", args)
        e = room.engine
        if not e.log:
            return "(无日志)"
        return '\n'.join(e.log[-20:])

    def _get_selected_room(self) -> Optional[GameRoom]:
        if self._selected_room is None:
            return None
        with self._lock:
            room = self.rooms.get(self._selected_room)
            if not room:
                self._selected_room = None
                return None
            return room

    def _player_name_in_room(self, room: GameRoom, pidx: int) -> str:
        pid = room.player_ids[pidx]
        with self._lock:
            if pid in self.players:
                return self.players[pid]['nickname']
        return f"ID:{pid}"

    COMMANDS = {
        'help': 'cmd_help',
        'h': 'cmd_help',
        '?': 'cmd_help',
        'ls': 'cmd_ls',
        'list': 'cmd_ls',
        'kick': 'cmd_kick',
        'say': 'cmd_say',
        'game': 'cmd_game',
        'phase': 'cmd_phase',
        'skip': 'cmd_skip',
        'draftfill': 'cmd_draftfill',
        'endgame': 'cmd_endgame',
        'set': 'cmd_set',
        'give': 'cmd_give',
        'log': 'cmd_log',
    }

    def execute_command(self, raw_input: str):
        raw_input = raw_input.strip()
        if not raw_input:
            return None, None, None, None
        parts = raw_input.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        cmd_start = 0
        for i, c in enumerate(raw_input):
            if not c.isspace():
                cmd_start = i
                break
        args_offset = cmd_start + len(parts[0])
        for i in range(args_offset, len(raw_input)):
            if not raw_input[i].isspace():
                args_offset = i
                break
        method_name = self.COMMANDS.get(cmd)
        if method_name is None:
            err_pos = cmd_start
            err_len = len(parts[0])
            msg = f"未知的命令：{cmd}"
            return msg, err_pos, err_len, None
        method = getattr(self, method_name)
        try:
            result = method(args)
            if isinstance(result, tuple) and len(result) >= 3:
                msg, err_pos, err_len = result[0], result[1], result[2]
                extra = result[3] if len(result) > 3 else None
                if err_pos == -999:
                    return msg, cmd_start, len(parts[0]), extra
                return msg, args_offset + err_pos, err_len, extra
            return result, None, None, None
        except Exception as e:
            return f"命令执行错误: {e}", None, None, None


R_LIGHT = '\033[91m'
R_DEEP = '\033[31m'
R_RESET = '\033[0m'


def format_error(raw: str, msg: str, err_pos: int, err_len: int, extra: str = '') -> str:
    if err_pos is None or err_len is None:
        return f"{R_DEEP}{msg}{R_RESET}"
    before = raw[:err_pos]
    err_part = raw[err_pos:err_pos + err_len]
    after = raw[err_pos + err_len:]
    char_pos = err_pos + 1
    line1 = f"{R_DEEP}{msg}，位于第{char_pos}个字符：{R_RESET}"
    line2 = f"{R_LIGHT}{before}{R_DEEP}{err_part}{R_LIGHT}<--[此处]{R_RESET}"
    if extra:
        line3 = f"{R_DEEP}{extra}{R_RESET}"
        return f"{line1}\n{line2}\n{line3}"
    return f"{line1}\n{line2}"


def command_input_loop(server: GameServer):
    while server.running:
        try:
            raw = input('')
            if not raw.strip():
                continue
            if raw.strip().lower() in ('stop', 'shutdown', 'exit', 'quit'):
                server_print("[服务器] 正在关闭...")
                server.stop()
                break
            if raw.strip().lower() == 'restart':
                server_print("[服务器] 正在重启...")
                server._restarting = True
                server.stop()
                time.sleep(1)
                server.__init__()
                server.start()
                server._restarting = False
                server_print("[服务器] 已重启")
                continue
            msg, err_pos, err_len, extra = server.execute_command(raw)
            if msg is not None:
                if err_pos is not None:
                    sys.stdout.write('\r' + ' ' * 80 + '\r')
                    print(format_error(raw, msg, err_pos, err_len, extra or ''))
                    sys.stdout.write('> ')
                    sys.stdout.flush()
                else:
                    sys.stdout.write('\r' + ' ' * 80 + '\r')
                    print(msg)
                    sys.stdout.write('> ')
                    sys.stdout.flush()
        except EOFError:
            break
        except Exception as e:
            sys.stdout.write('\r' + ' ' * 80 + '\r')
            print(f"{R_DEEP}[命令错误] {e}{R_RESET}")
            sys.stdout.write('> ')
            sys.stdout.flush()


if __name__ == '__main__':
    server = GameServer()
    server.start()
    server_print("输入 help 查看可用命令")
    cmd_thread = threading.Thread(target=command_input_loop, args=(server,), daemon=True)
    cmd_thread.start()
    try:
        while server.running or server._restarting:
            time.sleep(0.5)
    except KeyboardInterrupt:
        server.stop()
        sys.stdout.write('\r' + ' ' * 80 + '\r')
        print("[服务器] 服务器已关闭")
