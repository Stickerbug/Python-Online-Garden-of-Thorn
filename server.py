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
from mod_loader import merge_mod_cards_to_card_defs

try:
    merge_mod_cards_to_card_defs()
except Exception:
    pass

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
        self.disconnected_players: Dict[int, dict] = {}
        self.reconnect_timers: Dict[int, threading.Timer] = {}

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
                    if msg.msg_type not in ('ping', 'pong'):
                        server_print(f"[服务器] 收到消息: pid={pid}, type={msg.msg_type}")
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
        ip = msg.data.get('ip', '') or (conn.addr[0] if hasattr(conn, 'addr') else '')
        with self._lock:
            for p in self.players.values():
                if p['nickname'] == name:
                    conn.send(NetworkMessage('login_fail', {'reason': '昵称已被使用'}))
                    return None
            reconnect_room = None
            reconnect_pid = None
            for room in self.rooms.values():
                for dc_pid, dc_info in room.disconnected_players.items():
                    if dc_info['nickname'] == name and dc_info['ip'] == ip:
                        reconnect_room = room
                        reconnect_pid = dc_pid
                        break
                if reconnect_room:
                    break
            pid = self._next_pid
            self._next_pid += 1
            mods_info = msg.data.get('mods', {'hash': '', 'mods': [], 'count': 0})
            initial_status = 'reconnecting' if reconnect_room else 'lobby'
            self.players[pid] = {
                'nickname': name,
                'conn': conn,
                'room_id': None,
                'status': initial_status,
                'mods': mods_info,
            }
        if reconnect_room:
            conn.send(NetworkMessage('reconnect_available', {
                'room_id': reconnect_room.room_id,
                'old_pid': reconnect_pid,
                'opponent_nickname': self._get_opponent_nickname(reconnect_room, reconnect_pid),
            }))
        conn.send(NetworkMessage('login_ok', {'player_id': pid, 'nickname': name}))
        server_print(f"[服务器] 玩家 {name}(ID:{pid}) 已登录 (状态: {initial_status})")
        self._broadcast_lobby()
        return pid

    def _get_opponent_nickname(self, room: GameRoom, dc_pid: int) -> str:
        for other_pid in room.player_ids:
            if other_pid != dc_pid and other_pid in self.players:
                return self.players[other_pid]['nickname']
        return ''

    def _handle_disconnect(self, pid: int):
        with self._lock:
            if pid not in self.players:
                return
            player = self.players[pid]
            room_id = player['room_id']
            nickname = player['nickname']
            ip = player['conn'].addr[0] if hasattr(player['conn'], 'addr') else ''
            if room_id is not None and room_id in self.rooms:
                room = self.rooms[room_id]
                pidx = room.player_index(pid)
                if pidx >= 0 and room.engine.phase not in ('game_over',):
                    room.disconnected_players[pid] = {
                        'nickname': nickname,
                        'ip': ip,
                        'player_index': pidx,
                        'disconnect_time': time.time(),
                    }
                    for other_pid in room.player_ids:
                        if other_pid != pid and other_pid in self.players:
                            remaining = 120
                            self.players[other_pid]['conn'].send(
                                NetworkMessage('opponent_disconnected', {
                                    'reconnect_timeout': remaining,
                                    'opponent_nickname': nickname,
                                }))
                    timer = threading.Timer(120.0, self._reconnect_timeout, args=[room_id, pid])
                    room.reconnect_timers[pid] = timer
                    timer.daemon = True
                    timer.start()
                    del self.players[pid]
                    server_print(f"[服务器] 玩家 {nickname}(ID:{pid}) 断开连接，2分钟内可重连")
                    self._broadcast_lobby()
                    return
                for other_pid in room.player_ids:
                    if other_pid != pid and other_pid in self.players:
                        self.players[other_pid]['conn'].send(
                            NetworkMessage('opponent_disconnected', {}))
                        self.players[other_pid]['room_id'] = None
                        self.players[other_pid]['status'] = 'lobby'
                for t in room.reconnect_timers.values():
                    t.cancel()
                del self.rooms[room_id]
            for inv_pid, target_pid in list(self.invites.items()):
                if inv_pid == pid or target_pid == pid:
                    del self.invites[inv_pid]
            del self.players[pid]
        server_print(f"[服务器] 玩家ID:{pid} 断开连接")
        self._broadcast_lobby()

    def _reconnect_timeout(self, room_id: int, pid: int):
        with self._lock:
            if room_id not in self.rooms:
                return
            room = self.rooms[room_id]
            if pid not in room.disconnected_players:
                return
            dc_info = room.disconnected_players.pop(pid)
            server_print(f"[服务器] 玩家 {dc_info['nickname']} 重连超时，对局关闭")
            for other_pid in room.player_ids:
                if other_pid != pid and other_pid in self.players:
                    self.players[other_pid]['conn'].send(
                        NetworkMessage('opponent_disconnected', {'timeout': True}))
                    self.players[other_pid]['room_id'] = None
                    self.players[other_pid]['status'] = 'lobby'
            for t in room.reconnect_timers.values():
                t.cancel()
            del self.rooms[room_id]
            for p in self.players.values():
                if p['status'] == 'reconnecting' and p['nickname'] == dc_info['nickname']:
                    p['status'] = 'lobby'
                    p['conn'].send(NetworkMessage('reconnect_timeout', {}))
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
            elif msg.msg_type == 'reconnect_accept':
                self._handle_reconnect_accept(pid, msg)
            elif msg.msg_type == 'reconnect_decline':
                self._handle_reconnect_decline(pid, msg)
            elif msg.msg_type == 'chat':
                self._handle_chat(pid, msg)
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
        if pid in self.invites:
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
        accepter = self.players[pid]
        if inviter['status'] != 'lobby' or accepter['status'] != 'lobby':
            return
        inviter_mods = inviter.get('mods', {'hash': '', 'mods': [], 'count': 0})
        accepter_mods = accepter.get('mods', {'hash': '', 'mods': [], 'count': 0})
        if inviter_mods.get('hash', '') != accepter_mods.get('hash', ''):
            inviter_mod_names = ', '.join(inviter_mods.get('mods', [])) or '无'
            accepter_mod_names = ', '.join(accepter_mods.get('mods', [])) or '无'
            inviter['conn'].send(NetworkMessage('mod_mismatch', {
                'your_mods': inviter_mod_names, 'opponent_mods': accepter_mod_names}))
            accepter['conn'].send(NetworkMessage('mod_mismatch', {
                'your_mods': accepter_mod_names, 'opponent_mods': inviter_mod_names}))
            return
        room_id = self._next_room
        self._next_room += 1
        room = GameRoom(room_id, [inviter_pid, pid])
        self.rooms[room_id] = room
        inviter['room_id'] = room_id
        inviter['status'] = 'in_game'
        accepter['room_id'] = room_id
        accepter['status'] = 'in_game'
        room.engine.player_names = [inviter['nickname'], accepter['nickname']]
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

    def _handle_chat(self, pid: int, msg: NetworkMessage):
        player = self.players.get(pid)
        if not player or player['room_id'] is None:
            return
        room = self.rooms.get(player['room_id'])
        if not room:
            return
        text = msg.data.get('text', '')[:200]
        if not text.strip():
            return
        nickname = player['nickname']
        chat_msg = NetworkMessage('chat', {'nickname': nickname, 'text': text})
        for other_pid in room.player_ids:
            if other_pid in self.players:
                self.players[other_pid]['conn'].send(chat_msg)
        for spid in room.spectators:
            if spid in self.players:
                self.players[spid]['conn'].send(chat_msg)

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

    def _handle_reconnect_accept(self, pid: int, msg: NetworkMessage):
        try:
            with self._lock:
                server_print(f"[服务器] 处理 reconnect_accept: pid={pid}")
                player = self.players.get(pid)
                if not player:
                    server_print(f"[服务器] reconnect_accept 失败: 玩家 {pid} 不存在")
                    return
                room_id = msg.data.get('room_id')
                old_pid = msg.data.get('old_pid')
                server_print(f"[服务器] reconnect_accept: room_id={room_id}, old_pid={old_pid}, nickname={player['nickname']}")
                if room_id is None or room_id not in self.rooms:
                    server_print(f"[服务器] reconnect_accept 失败: 房间 {room_id} 不存在")
                    player['status'] = 'lobby'
                    return
                room = self.rooms[room_id]
                server_print(f"[服务器] 房间 disconnected_players: {list(room.disconnected_players.keys())}")
                if old_pid not in room.disconnected_players:
                    server_print(f"[服务器] reconnect_accept 失败: old_pid {old_pid} 不在 disconnected_players 中")
                    player['status'] = 'lobby'
                    return
                dc_info = room.disconnected_players[old_pid]
                if dc_info['nickname'] != player['nickname']:
                    server_print(f"[服务器] reconnect_accept 失败: 昵称不匹配 dc_nickname={dc_info['nickname']}, player_nickname={player['nickname']}")
                    player['status'] = 'lobby'
                    return
                if old_pid in room.reconnect_timers:
                    room.reconnect_timers[old_pid].cancel()
                    del room.reconnect_timers[old_pid]
                room.player_ids[dc_info['player_index']] = pid
                if old_pid in room.draft_ready:
                    room.draft_ready[pid] = room.draft_ready.pop(old_pid)
                del room.disconnected_players[old_pid]
                player['room_id'] = room_id
                player['status'] = 'in_game'
                for other_pid in room.player_ids:
                    if other_pid != pid and other_pid in self.players:
                        self.players[other_pid]['conn'].send(
                            NetworkMessage('opponent_reconnected', {}))
                server_print(f"[服务器] 玩家 {player['nickname']} 重连成功")
                server_print(f"[服务器] 重连: 发送游戏状态给玩家 {pid}, 阶段: {room.engine.phase}")
                self._send_game_state_to(room, dc_info['player_index'])
        except Exception as e:
            server_print(f"[服务器] reconnect_accept 异常: {e}")
            import traceback
            traceback.print_exc()
            with self._lock:
                player = self.players.get(pid)
                if player and player['status'] == 'reconnecting':
                    player['status'] = 'lobby'
        self._broadcast_lobby()

    def _handle_reconnect_decline(self, pid: int, msg: NetworkMessage):
        with self._lock:
            room_id = msg.data.get('room_id')
            old_pid = msg.data.get('old_pid')
            if room_id is None or room_id not in self.rooms:
                if pid in self.players:
                    self.players[pid]['status'] = 'lobby'
                return
            room = self.rooms[room_id]
            if old_pid in room.disconnected_players:
                if old_pid in room.reconnect_timers:
                    room.reconnect_timers[old_pid].cancel()
                    del room.reconnect_timers[old_pid]
                del room.disconnected_players[old_pid]
            for other_pid in room.player_ids:
                if other_pid != pid and other_pid in self.players:
                    self.players[other_pid]['conn'].send(
                        NetworkMessage('opponent_disconnected', {'timeout': True}))
                    self.players[other_pid]['room_id'] = None
                    self.players[other_pid]['status'] = 'lobby'
            for t in room.reconnect_timers.values():
                t.cancel()
            del self.rooms[room_id]
            if pid in self.players:
                self.players[pid]['status'] = 'lobby'
        server_print(f"[服务器] 玩家拒绝重连，对局关闭")
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
            names = []
            for pidx, p in enumerate(room.player_ids):
                names.append(self.players.get(p, {}).get('nickname', f'玩家{pidx+1}'))
            room.engine.player_names = names
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
                        if played_def.card_type == 'thorn':
                            trigger_types.append('attack')
                        elif played_def.card_type == 'bloom':
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
            if pid not in self.players:
                continue
            state = room.engine.get_public_state(pidx)
            state['your_id'] = pidx
            opp_pidx = 1 - pidx
            opp_pid = room.player_ids[opp_pidx]
            if opp_pid in self.players:
                state['opponent_name'] = self.players[opp_pid]['nickname']
            else:
                state['opponent_name'] = '?'
            self.players[pid]['conn'].send(NetworkMessage('state_update', state))
        self._broadcast_spectate_state(room)

    def _send_game_state_to(self, room: GameRoom, player_idx: int):
        pid = room.player_ids[player_idx]
        phase = room.engine.phase
        if pid not in self.players:
            return
        self.players[pid]['conn'].send(NetworkMessage('game_phase', {'phase': phase}))
        if phase == 'event_select':
            self._send_event_state_to(room, player_idx)
        elif phase == 'draft':
            self._send_draft_state_to(room, player_idx)
        else:
            state = room.engine.get_public_state(player_idx)
            state['your_id'] = player_idx
            opp_pidx = 1 - player_idx
            opp_pid = room.player_ids[opp_pidx]
            if opp_pid in self.players:
                state['opponent_name'] = self.players[opp_pid]['nickname']
            else:
                state['opponent_name'] = '?'
            self.players[pid]['conn'].send(NetworkMessage('state_update', state))

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
            "  set <p> <k> <v>  设置玩家属性(p=0/1, k=h/e/m/armor/dodge/poison/burn/toxic/vulnerable/nazar/mark)",
            "  give <p> <card>  给玩家加牌(p=0/1)",
            "  hand <p>      查看玩家手牌及标签(p=0/1)",
            "  deck <p>      查看玩家抽牌堆(p=0/1)",
            "  equip <p>     查看玩家装备(p=0/1)",
            "  discard <p>   查看玩家弃牌堆(p=0/1)",
            "  status <p>    查看玩家详细状态(p=0/1)",
            "  del <p> <idx> 删除玩家手牌中指定编号的牌",
            "  delcard <p> <card> 删除玩家手牌中指定卡牌(按ID或中文名)",
            "  delequip <p> <idx> 删除玩家装备中指定编号的装备",
            "  deldeck <p> <idx>  删除玩家抽牌堆中指定编号的牌",
            "  deldiscard <p> <idx> 删除玩家弃牌堆中指定编号的牌",
            "  card <p> <idx>  查看玩家手牌中指定编号的卡牌详情及标签",
            "  search <keyword> 搜索卡牌定义(按ID或中文名)",
            "  shuffle <p>    洗玩家抽牌堆",
            "  move <p> <from> <idx> <to> 移动卡牌(from/to:hand/deck/discard/equip)",
            "  exile <p>      查看玩家放逐区",
            "  addpoison <p> <n> 给玩家加n层毒",
            "  addburn <p> <n> 给玩家加n层灼烧",
            "  addvulnerable <p> <n> 给玩家加n层易伤",
            "  addtoxic <p> <n> 给玩家加n层淬毒",
            "  heal <p> <n>  治疗玩家n点生命",
            "  damage <p> <n> 对玩家造成n点伤害",
            "  rename <p> <name> 修改玩家昵称",
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
        elif key == 'armor':
            ps.armor = val
        elif key == 'dodge':
            ps.dodge = val
        elif key == 'poison':
            ps.poison = val
        elif key == 'burn':
            ps.burn = val
        elif key == 'toxic':
            ps.toxic = val
        elif key == 'vulnerable':
            ps.vulnerable = val
        elif key == 'nazar':
            ps.nazar = val
        elif key == 'mark':
            ps.mark = val
        else:
            return (f"未知的属性：{key}", _arg_offset(args, 1), len(parts[1]), "可用: h/e/m/armor/dodge/poison/burn/toxic/vulnerable/nazar/mark")
        self._broadcast_game_state(room)
        return f"{name}(P{pidx}) {key}={val}"

    def cmd_give(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if len(parts) < 2:
            return ("不完整的命令：give", 0, 0, "用法: give <0|1> <卡牌ID或中文名>")
        try:
            pidx = int(parts[0])
        except ValueError:
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        if pidx not in (0, 1):
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        card_query = ' '.join(parts[1:])
        card_id = None
        for def_id, cdef in CARD_DEFS.items():
            if def_id.lower() == card_query.lower() or cdef.name_cn == card_query:
                card_id = def_id
                break
        if card_id is None:
            return (f"未知的卡牌：{card_query}", _arg_offset(args, 1), len(card_query), None)
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

    def _parse_pidx(self, args: str, cmd_name: str):
        parts = args.strip().split()
        if not parts:
            return None, ("不完整的命令：" + cmd_name, 0, 0, f"用法: {cmd_name} <0|1>")
        try:
            pidx = int(parts[0])
        except ValueError:
            return None, (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        if pidx not in (0, 1):
            return None, (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        return pidx, None

    def cmd_hand(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        pidx, err = self._parse_pidx(args, 'hand')
        if err:
            return err
        e = room.engine
        ps = e.players[pidx]
        name = self._player_name_in_room(room, pidx)
        lines = [f"=== {name}(P{pidx}) 手牌 ({len(ps.hand)}张) ==="]
        for i, card in enumerate(ps.hand):
            cdef = CARD_DEFS.get(card.def_id, CardDef('', '', '', 0, 0, '', 0, '', '', ''))
            flags_str = ''
            if card.instance_flags:
                flags_str = f' [{",".join(card.instance_flags)}]'
            lines.append(f"  [{i}] {cdef.name_cn}({card.def_id}) E={cdef.cost_e} M={cdef.cost_m} {cdef.card_type}{flags_str}")
        return '\n'.join(lines)

    def cmd_deck(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        pidx, err = self._parse_pidx(args, 'deck')
        if err:
            return err
        e = room.engine
        ps = e.players[pidx]
        name = self._player_name_in_room(room, pidx)
        lines = [f"=== {name}(P{pidx}) 抽牌堆 ({len(ps.deck)}张) ==="]
        for i, card in enumerate(ps.deck):
            cdef = CARD_DEFS.get(card.def_id, CardDef('', '', '', 0, 0, '', 0, '', '', ''))
            lines.append(f"  [{i}] {cdef.name_cn}({card.def_id})")
        return '\n'.join(lines)

    def cmd_equip(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        pidx, err = self._parse_pidx(args, 'equip')
        if err:
            return err
        e = room.engine
        ps = e.players[pidx]
        name = self._player_name_in_room(room, pidx)
        lines = [f"=== {name}(P{pidx}) 装备 ({len(ps.equipment)}张) ==="]
        for i, card in enumerate(ps.equipment):
            cdef = CARD_DEFS.get(card.def_id, CardDef('', '', '', 0, 0, '', 0, '', '', ''))
            flags_str = ''
            if card.instance_flags:
                flags_str = f' [{",".join(card.instance_flags)}]'
            lines.append(f"  [{i}] {cdef.name_cn}({card.def_id}){flags_str}")
        return '\n'.join(lines)

    def cmd_discard(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        pidx, err = self._parse_pidx(args, 'discard')
        if err:
            return err
        e = room.engine
        ps = e.players[pidx]
        name = self._player_name_in_room(room, pidx)
        lines = [f"=== {name}(P{pidx}) 弃牌堆 ({len(ps.discard)}张) ==="]
        for i, card in enumerate(ps.discard):
            cdef = CARD_DEFS.get(card.def_id, CardDef('', '', '', 0, 0, '', 0, '', '', ''))
            lines.append(f"  [{i}] {cdef.name_cn}({card.def_id})")
        return '\n'.join(lines)

    def cmd_status(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        pidx, err = self._parse_pidx(args, 'status')
        if err:
            return err
        e = room.engine
        ps = e.players[pidx]
        name = self._player_name_in_room(room, pidx)
        lines = [f"=== {name}(P{pidx}) 详细状态 ==="]
        lines.append(f"  生命: {ps.health}/{ps.max_health} (基础最大:{ps.base_max_health})")
        lines.append(f"  药剂: {ps.elixir}/{ps.max_elixir}")
        lines.append(f"  魔力: {ps.magic}/{ps.max_magic}")
        lines.append(f"  护甲: {ps.armor}  闪避: {ps.dodge}")
        lines.append(f"  中毒: {ps.poison}  灼烧: {ps.burn}  淬毒: {ps.toxic}")
        lines.append(f"  脆弱: {ps.vulnerable}  邪眼: {ps.nazar}  标记: {ps.mark}")
        lines.append(f"  无敌: {ps.invincible}  不可选中: {ps.untargetable}")
        lines.append(f"  手牌: {len(ps.hand)}  抽牌堆: {len(ps.deck)}  弃牌堆: {len(ps.discard)}  装备: {len(ps.equipment)}")
        if ps.enemy_draw_reduction:
            lines.append(f"  敌方少抽牌: {ps.enemy_draw_reduction}")
        if ps.enemy_e_reduction:
            lines.append(f"  敌方少回E: {ps.enemy_e_reduction}")
        if ps.cannot_attack:
            lines.append(f"  无法攻击: 剩余{ps.cannot_attack}回合")
        if ps.attack_only:
            lines.append(f"  只能攻击: 剩余{ps.attack_only}回合")
        if ps.cannot_act:
            lines.append(f"  无法行动: 剩余{ps.cannot_act}回合")
        return '\n'.join(lines)

    def cmd_del(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if len(parts) < 2:
            return ("不完整的命令：del", 0, 0, "用法: del <0|1> <手牌编号>")
        try:
            pidx = int(parts[0])
        except ValueError:
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        if pidx not in (0, 1):
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        try:
            idx = int(parts[1])
        except ValueError:
            return (f"无效的编号：{parts[1]}", _arg_offset(args, 1), len(parts[1]), "编号必须是数字")
        e = room.engine
        ps = e.players[pidx]
        name = self._player_name_in_room(room, pidx)
        if idx < 0 or idx >= len(ps.hand):
            return f"编号超出范围(0-{len(ps.hand)-1})"
        card = ps.hand.pop(idx)
        cdef = CARD_DEFS.get(card.def_id, CardDef('', '', '', 0, 0, '', 0, '', '', ''))
        self._broadcast_game_state(room)
        return f"已删除 {name}(P{pidx}) 的 [{idx}] {cdef.name_cn}"

    def cmd_delcard(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if len(parts) < 2:
            return ("不完整的命令：delcard", 0, 0, "用法: delcard <0|1> <卡牌ID或中文名>")
        try:
            pidx = int(parts[0])
        except ValueError:
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        if pidx not in (0, 1):
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        card_query = ' '.join(parts[1:])
        e = room.engine
        ps = e.players[pidx]
        name = self._player_name_in_room(room, pidx)
        found = []
        for i, card in enumerate(ps.hand):
            cdef = CARD_DEFS.get(card.def_id)
            if card.def_id.lower() == card_query.lower() or (cdef and cdef.name_cn == card_query):
                found.append(i)
        if not found:
            return f"未在手牌中找到: {card_query}"
        if len(found) == 1:
            card = ps.hand.pop(found[0])
            cdef = CARD_DEFS.get(card.def_id, CardDef('', '', '', 0, 0, '', 0, '', '', ''))
            self._broadcast_game_state(room)
            return f"已删除 {name}(P{pidx}) 的 {cdef.name_cn}"
        idx = found[0]
        card = ps.hand.pop(idx)
        cdef = CARD_DEFS.get(card.def_id, CardDef('', '', '', 0, 0, '', 0, '', '', ''))
        self._broadcast_game_state(room)
        return f"找到{len(found)}张，已删除 {name}(P{pidx}) 的第1张 {cdef.name_cn}"

    def cmd_addpoison(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if len(parts) < 2:
            return ("不完整的命令：addpoison", 0, 0, "用法: addpoison <0|1> <层数>")
        try:
            pidx = int(parts[0])
        except ValueError:
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        if pidx not in (0, 1):
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        try:
            n = int(parts[1])
        except ValueError:
            return (f"无效的层数：{parts[1]}", _arg_offset(args, 1), len(parts[1]), "层数必须是数字")
        e = room.engine
        ps = e.players[pidx]
        ps.poison += n
        name = self._player_name_in_room(room, pidx)
        self._broadcast_game_state(room)
        return f"{name}(P{pidx}) +{n}层中毒(当前:{ps.poison})"

    def cmd_addburn(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if len(parts) < 2:
            return ("不完整的命令：addburn", 0, 0, "用法: addburn <0|1> <层数>")
        try:
            pidx = int(parts[0])
        except ValueError:
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        if pidx not in (0, 1):
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        try:
            n = int(parts[1])
        except ValueError:
            return (f"无效的层数：{parts[1]}", _arg_offset(args, 1), len(parts[1]), "层数必须是数字")
        e = room.engine
        ps = e.players[pidx]
        ps.burn += n
        name = self._player_name_in_room(room, pidx)
        self._broadcast_game_state(room)
        return f"{name}(P{pidx}) +{n}层灼烧(当前:{ps.burn})"

    def cmd_heal(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if len(parts) < 2:
            return ("不完整的命令：heal", 0, 0, "用法: heal <0|1> <数值>")
        try:
            pidx = int(parts[0])
        except ValueError:
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        if pidx not in (0, 1):
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        try:
            n = int(parts[1])
        except ValueError:
            return (f"无效的数值：{parts[1]}", _arg_offset(args, 1), len(parts[1]), "数值必须是数字")
        e = room.engine
        ps = e.players[pidx]
        ps.health = min(ps.max_health, ps.health + n)
        name = self._player_name_in_room(room, pidx)
        self._broadcast_game_state(room)
        return f"{name}(P{pidx}) 治疗{n}点(当前:{ps.health}/{ps.max_health})"

    def cmd_damage(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if len(parts) < 2:
            return ("不完整的命令：damage", 0, 0, "用法: damage <0|1> <数值>")
        try:
            pidx = int(parts[0])
        except ValueError:
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        if pidx not in (0, 1):
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        try:
            n = int(parts[1])
        except ValueError:
            return (f"无效的数值：{parts[1]}", _arg_offset(args, 1), len(parts[1]), "数值必须是数字")
        e = room.engine
        ps = e.players[pidx]
        ps.health = max(0, ps.health - n)
        name = self._player_name_in_room(room, pidx)
        e._check_game_over()
        self._broadcast_game_state(room)
        return f"{name}(P{pidx}) 受到{n}点伤害(当前:{ps.health}/{ps.max_health})"

    def cmd_card(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if len(parts) < 2:
            return ("不完整的命令：card", 0, 0, "用法: card <0|1> <手牌编号>")
        pidx, err = self._parse_pidx(args, 'card')
        if err:
            return err
        try:
            idx = int(parts[1])
        except ValueError:
            return (f"无效的编号：{parts[1]}", _arg_offset(args, 1), len(parts[1]), "编号必须是数字")
        e = room.engine
        ps = e.players[pidx]
        name = self._player_name_in_room(room, pidx)
        if idx < 0 or idx >= len(ps.hand):
            return f"编号超出范围(0-{len(ps.hand)-1})"
        card = ps.hand[idx]
        cdef = CARD_DEFS.get(card.def_id, CardDef('', '', '', 0, 0, '', 0, '', '', ''))
        lines = [f"=== {name}(P{pidx}) 手牌[{idx}] {cdef.name_cn} ==="]
        lines.append(f"  ID: {card.def_id}")
        lines.append(f"  中文名: {cdef.name_cn}  英文名: {cdef.name_en}")
        lines.append(f"  类型: {cdef.card_type}  品质: {cdef.quality}")
        lines.append(f"  费用: E={card.cost_e} M={card.cost_m} (原始: E={cdef.cost_e} M={cdef.cost_m})")
        lines.append(f"  描述: {cdef.description}")
        if cdef.effect_text:
            lines.append(f"  效果文本: {cdef.effect_text}")
        if cdef.flags:
            lines.append(f"  定义标签: {', '.join(cdef.flags)}")
        if card.instance_flags:
            lines.append(f"  实例标签: {', '.join(card.instance_flags)}")
        if cdef.effects:
            lines.append(f"  原子效果({len(cdef.effects)}个):")
            for ei, eff in enumerate(cdef.effects):
                lines.append(f"    [{ei}] {eff.get('type', '?')}: {eff}")
        if card.fission_count > 0:
            lines.append(f"  裂变次数: {card.fission_count}")
        if card.fusion_multiplier != 1.0:
            lines.append(f"  聚变倍率: {card.fusion_multiplier}")
        if card.mimic_discount > 0:
            lines.append(f"  拟态减费: {card.mimic_discount}")
        if card.cost_e_override is not None or card.cost_m_override is not None:
            lines.append(f"  费用覆盖: E={card.cost_e_override} M={card.cost_m_override}")
        if cdef.trigger_cost_e >= 0:
            lines.append(f"  触发费用: {cdef.trigger_cost_e}E")
        if cdef.trigger_effect_text:
            lines.append(f"  触发效果: {cdef.trigger_effect_text}")
        if cdef.response_trigger:
            lines.append(f"  反制触发: {cdef.response_trigger}")
        return '\n'.join(lines)

    def cmd_delequip(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if len(parts) < 2:
            return ("不完整的命令：delequip", 0, 0, "用法: delequip <0|1> <装备编号>")
        pidx, err = self._parse_pidx(args, 'delequip')
        if err:
            return err
        try:
            idx = int(parts[1])
        except ValueError:
            return (f"无效的编号：{parts[1]}", _arg_offset(args, 1), len(parts[1]), "编号必须是数字")
        e = room.engine
        ps = e.players[pidx]
        name = self._player_name_in_room(room, pidx)
        if idx < 0 or idx >= len(ps.equipment):
            return f"编号超出范围(0-{len(ps.equipment)-1})"
        card = ps.equipment.pop(idx)
        cdef = CARD_DEFS.get(card.def_id, CardDef('', '', '', 0, 0, '', 0, '', '', ''))
        self._broadcast_game_state(room)
        return f"已删除 {name}(P{pidx}) 的装备[{idx}] {cdef.name_cn}"

    def cmd_deldeck(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if len(parts) < 2:
            return ("不完整的命令：deldeck", 0, 0, "用法: deldeck <0|1> <编号>")
        pidx, err = self._parse_pidx(args, 'deldeck')
        if err:
            return err
        try:
            idx = int(parts[1])
        except ValueError:
            return (f"无效的编号：{parts[1]}", _arg_offset(args, 1), len(parts[1]), "编号必须是数字")
        e = room.engine
        ps = e.players[pidx]
        name = self._player_name_in_room(room, pidx)
        if idx < 0 or idx >= len(ps.deck):
            return f"编号超出范围(0-{len(ps.deck)-1})"
        card = ps.deck.pop(idx)
        cdef = CARD_DEFS.get(card.def_id, CardDef('', '', '', 0, 0, '', 0, '', '', ''))
        self._broadcast_game_state(room)
        return f"已删除 {name}(P{pidx}) 牌堆[{idx}] {cdef.name_cn}"

    def cmd_deldiscard(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if len(parts) < 2:
            return ("不完整的命令：deldiscard", 0, 0, "用法: deldiscard <0|1> <编号>")
        pidx, err = self._parse_pidx(args, 'deldiscard')
        if err:
            return err
        try:
            idx = int(parts[1])
        except ValueError:
            return (f"无效的编号：{parts[1]}", _arg_offset(args, 1), len(parts[1]), "编号必须是数字")
        e = room.engine
        ps = e.players[pidx]
        name = self._player_name_in_room(room, pidx)
        if idx < 0 or idx >= len(ps.discard):
            return f"编号超出范围(0-{len(ps.discard)-1})"
        card = ps.discard.pop(idx)
        cdef = CARD_DEFS.get(card.def_id, CardDef('', '', '', 0, 0, '', 0, '', '', ''))
        self._broadcast_game_state(room)
        return f"已删除 {name}(P{pidx}) 弃牌堆[{idx}] {cdef.name_cn}"

    def cmd_search(self, args: str):
        keyword = args.strip()
        if not keyword:
            return ("不完整的命令：search", 0, 0, "用法: search <关键词>")
        results = []
        for def_id, cdef in CARD_DEFS.items():
            if keyword.lower() in def_id.lower() or keyword in cdef.name_cn:
                results.append((def_id, cdef))
        if not results:
            return f"未找到匹配 '{keyword}' 的卡牌"
        lines = [f"=== 搜索结果: '{keyword}' ({len(results)}张) ==="]
        for def_id, cdef in results:
            lines.append(f"  {cdef.name_cn}({def_id}) E={cdef.cost_e} M={cdef.cost_m} {cdef.card_type} {cdef.quality}")
        return '\n'.join(lines)

    def cmd_shuffle(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        pidx, err = self._parse_pidx(args, 'shuffle')
        if err:
            return err
        e = room.engine
        ps = e.players[pidx]
        name = self._player_name_in_room(room, pidx)
        import random
        random.shuffle(ps.deck)
        self._broadcast_game_state(room)
        return f"已洗 {name}(P{pidx}) 的抽牌堆({len(ps.deck)}张)"

    def cmd_move(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if len(parts) < 4:
            return ("不完整的命令：move", 0, 0, "用法: move <0|1> <from> <idx> <to>\n  from/to: hand/deck/discard/equip")
        try:
            pidx = int(parts[0])
        except ValueError:
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        if pidx not in (0, 1):
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        from_loc = parts[1].lower()
        try:
            idx = int(parts[2])
        except ValueError:
            return (f"无效的编号：{parts[2]}", _arg_offset(args, 2), len(parts[2]), "编号必须是数字")
        to_loc = parts[3].lower()
        valid_locs = ('hand', 'deck', 'discard', 'equip')
        if from_loc not in valid_locs:
            return (f"无效的来源：{from_loc}", _arg_offset(args, 1), len(parts[1]), f"可用: {'/'.join(valid_locs)}")
        if to_loc not in valid_locs:
            return (f"无效的目标：{to_loc}", _arg_offset(args, 3), len(parts[3]), f"可用: {'/'.join(valid_locs)}")
        e = room.engine
        ps = e.players[pidx]
        name = self._player_name_in_room(room, pidx)
        src_map = {'hand': ps.hand, 'deck': ps.deck, 'discard': ps.discard, 'equip': ps.equipment}
        src = src_map[from_loc]
        if idx < 0 or idx >= len(src):
            return f"{from_loc}编号超出范围(0-{len(src)-1})"
        card = src.pop(idx)
        if to_loc == 'equip':
            from game_engine import EquipmentInstance
            eq = EquipmentInstance(card.def_id)
            ps.equipment.append(eq)
        else:
            dst_map = {'hand': ps.hand, 'deck': ps.deck, 'discard': ps.discard}
            dst_map[to_loc].append(card)
        cdef = CARD_DEFS.get(card.def_id, CardDef('', '', '', 0, 0, '', 0, '', '', ''))
        self._broadcast_game_state(room)
        return f"已移动 {name}(P{pidx}) 的 {cdef.name_cn}: {from_loc}[{idx}] -> {to_loc}"

    def cmd_exile(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        pidx, err = self._parse_pidx(args, 'exile')
        if err:
            return err
        e = room.engine
        ps = e.players[pidx]
        name = self._player_name_in_room(room, pidx)
        lines = [f"=== {name}(P{pidx}) 放逐区 ({len(ps.exile)}张) ==="]
        for i, card in enumerate(ps.exile):
            cdef = CARD_DEFS.get(card.def_id, CardDef('', '', '', 0, 0, '', 0, '', '', ''))
            lines.append(f"  [{i}] {cdef.name_cn}({card.def_id})")
        return '\n'.join(lines)

    def cmd_addvulnerable(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if len(parts) < 2:
            return ("不完整的命令：addvulnerable", 0, 0, "用法: addvulnerable <0|1> <层数>")
        pidx, err = self._parse_pidx(args, 'addvulnerable')
        if err:
            return err
        try:
            n = int(parts[1])
        except ValueError:
            return (f"无效的层数：{parts[1]}", _arg_offset(args, 1), len(parts[1]), "层数必须是数字")
        e = room.engine
        ps = e.players[pidx]
        ps.vulnerable += n
        name = self._player_name_in_room(room, pidx)
        self._broadcast_game_state(room)
        return f"{name}(P{pidx}) +{n}层易伤(当前:{ps.vulnerable})"

    def cmd_addtoxic(self, args: str):
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        parts = args.strip().split()
        if len(parts) < 2:
            return ("不完整的命令：addtoxic", 0, 0, "用法: addtoxic <0|1> <层数>")
        pidx, err = self._parse_pidx(args, 'addtoxic')
        if err:
            return err
        try:
            n = int(parts[1])
        except ValueError:
            return (f"无效的层数：{parts[1]}", _arg_offset(args, 1), len(parts[1]), "层数必须是数字")
        e = room.engine
        ps = e.players[pidx]
        ps.toxic += n
        name = self._player_name_in_room(room, pidx)
        self._broadcast_game_state(room)
        return f"{name}(P{pidx}) +{n}层淬毒(当前:{ps.toxic})"

    def cmd_rename(self, args: str):
        parts = args.strip().split()
        if len(parts) < 2:
            return ("不完整的命令：rename", 0, 0, "用法: rename <0|1> <新昵称>")
        try:
            pidx = int(parts[0])
        except ValueError:
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        if pidx not in (0, 1):
            return (f"无效的玩家索引：{parts[0]}", 0, len(parts[0]), "玩家索引必须是0或1")
        new_name = ' '.join(parts[1:])
        room = self._get_selected_room()
        if not room:
            return self._no_room_error()
        pid = room.player_ids[pidx]
        old_name = self._player_name_in_room(room, pidx)
        with self._lock:
            if pid in self.players:
                self.players[pid]['nickname'] = new_name
        room.engine.player_names[pidx] = new_name
        self._broadcast_game_state(room)
        return f"已将 P{pidx} 昵称从 '{old_name}' 改为 '{new_name}'"

    def _player_name_in_room(self, room, pidx):
        pid = room.player_ids[pidx]
        p = self.players.get(pid)
        return p['nickname'] if p else f'P{pidx}'

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
        'hand': 'cmd_hand',
        'deck': 'cmd_deck',
        'equip': 'cmd_equip',
        'discard': 'cmd_discard',
        'status': 'cmd_status',
        'del': 'cmd_del',
        'delcard': 'cmd_delcard',
        'addpoison': 'cmd_addpoison',
        'addburn': 'cmd_addburn',
        'addvulnerable': 'cmd_addvulnerable',
        'addtoxic': 'cmd_addtoxic',
        'heal': 'cmd_heal',
        'damage': 'cmd_damage',
        'card': 'cmd_card',
        'delequip': 'cmd_delequip',
        'deldeck': 'cmd_deldeck',
        'deldiscard': 'cmd_deldiscard',
        'search': 'cmd_search',
        'shuffle': 'cmd_shuffle',
        'move': 'cmd_move',
        'exile': 'cmd_exile',
        'rename': 'cmd_rename',
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
