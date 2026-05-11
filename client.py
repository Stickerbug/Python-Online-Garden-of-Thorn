import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import socket
import re
import sys
import os
import json
import wcwidth
from typing import Optional, Dict, List
from network import (
    NetworkMessage, NetworkConnection, connect_to_server, DEFAULT_PORT
)
from cards import CardInstance, CardDef, CARD_DEFS

DISCOVERY_PORT = 4160

import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
FONT_CN = '思源黑体 Kreadon'
FONT_EN_BOLD = 'Kreadon Demi'

def _load_fonts():
    for fname in ['思源黑体-Kreadon.ttf', 'Kreadon-Demi.ttf']:
        fpath = os.path.join(FONT_DIR, fname)
        if os.path.exists(fpath):
            try:
                ctypes.windll.gdi32.AddFontResourceExW(fpath, 0x10, 0)
            except Exception:
                pass

_load_fonts()

BASE_WIDTH = 1600
SCALE = 1.0

COLORS = {
    'elixir': '#F1C40F', 'elixir_text': '#9A7D0A', 'elixir_bg': '#FEF9E7',
    'magic': '#3498DB', 'magic_text': '#1A5276', 'magic_bg': '#EBF5FB',
    'health': '#2ECC71', 'health_text': '#1E8449', 'health_bg': '#E8F8F5',
    'heal': '#F48FB1', 'heal_text': '#C2185B', 'heal_bg': '#FCE4EC',
    'armor': '#95A5A6', 'armor_text': '#515A5A', 'armor_bg': '#F2F3F4',
    'damage': '#C0392B', 'damage_bg': '#FDEDEC',
    'poison': '#8E44AD', 'poison_bg': '#F4ECF7',
    'fire': '#E67E22', 'fire_bg': '#FEF5E7',
    'banish': '#6C3483', 'banish_bg': '#F4ECF7',
    'non_stack': '#34495E', 'non_stack_bg': '#EAECEE',
    'indestructible': '#D4AC0D', 'indestructible_bg': '#FEF9E7',
    'vulnus': '#7B241C', 'vulnus_bg': '#FDEDEC',
    'void_c': '#37474F', 'void_bg': '#ECEFF1',
    'adhere': '#6D4C41', 'adhere_bg': '#EFEBE9',
    'precise': '#546E7A', 'precise_bg': '#ECEFF1',
    'thorn': '#C0392B', 'thorn_bg': '#FDEDEC',
    'root': '#8D6E63', 'root_bg': '#EFEBE9',
    'bloom': '#1ABC9C', 'bloom_bg': '#E8F8F5',
    'guard': '#2980B9', 'guard_bg': '#EBF5FB',
    'bg_page': '#F5F5F0', 'bg_card': '#FFFFFF',
    'text_primary': '#2C3E50', 'text_secondary': '#7F8C8D',
    'border_color': '#DCDCDC',
}

CARD_TYPE_COLORS = {
    'attack': COLORS['damage'],
    'skill': COLORS['magic'],
    'equipment': COLORS['armor'],
    'counter': COLORS['bloom'],
}

CARD_FLAGS = {
    'precision': ('精准', COLORS['precise'], COLORS['precise_bg']),
    'exile': ('放逐', COLORS['banish'], COLORS['banish_bg']),
    'non_stackable': ('不可叠加', COLORS['non_stack'], COLORS['non_stack_bg']),
    'indestructible': ('不可摧毁', COLORS['indestructible'], COLORS['indestructible_bg']),
}


def _scale():
    return SCALE


def _f(base_size: int) -> int:
    return max(8, int(base_size * SCALE))


def _fc(base_size: int) -> int:
    return max(1, int(base_size * SCALE))


def _font(size_fn, base_size: int, bold: bool = False) -> tuple:
    family = FONT_EN_BOLD if bold else FONT_CN
    size = size_fn(base_size)
    if bold:
        return (family, size, "bold")
    return (family, size)


def _p(base_px: int) -> int:
    return max(1, int(base_px * SCALE))


def CARD_W():
    return int(182 * SCALE)


def CARD_H():
    return int(254 * SCALE)


def CARD_BACK_W():
    return int(90 * SCALE)


def CARD_BACK_H():
    return int(127 * SCALE)


def BAR_W():
    return int(140 * SCALE)


def BAR_H():
    return int(24 * SCALE)


class GameClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Garden of Thorn 荆棘花园")
        self.root.geometry("1600x1000")
        self.root.minsize(800, 600)
        self.root.resizable(True, True)
        self.root.configure(bg=COLORS['bg_page'])
        self._last_scale = 1.0
        self._resize_after_id = None
        self.root.bind('<Configure>', self._on_window_resize)
        self.conn: Optional[NetworkConnection] = None
        self.player_id: int = -1
        self.room_index: int = -1
        self.nickname: str = ''
        self.game_state: dict = {}
        self.draft_state: dict = {}
        self.lobby_players: list = []
        self.phase: str = 'connecting'
        self.response_pending: bool = False
        self.response_data: dict = {}
        self.choice_pending: bool = False
        self.choice_data: dict = {}
        self._running = True
        self._dragging = False
        self._drag_card_id = None
        self._drag_card = None
        self._drag_total_e = 0
        self._drag_total_m = 0
        self._ghost = None
        self._drag_source_widget = None
        self._drag_placeholder = None
        self._response_timer_id = None
        self._pass_btn = None
        self._response_countdown = 0
        self._pending_play_card = None
        self._build_ui()

    def connect_and_login(self, host: str, port: int, nickname: str):
        self._clear_content()
        self._update_status("正在连接服务器...")
        tk.Label(self.content_frame, text="⏳ 连接中...",
                 font=_font(_f, 18), bg=COLORS['bg_page'],
                 fg=COLORS['magic']).pack(expand=True)
        self.root.update()

        def _do_connect():
            try:
                sock = connect_to_server(host, port)
                self.conn = NetworkConnection(sock)
                self.nickname = nickname
                self.conn.send(NetworkMessage('login', {'nickname': nickname}))
                recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
                recv_thread.start()
            except Exception as e:
                self.root.after(0, self._on_connect_fail, str(e))

        threading.Thread(target=_do_connect, daemon=True).start()

    def _on_connect_fail(self, error_msg: str):
        self._clear_content()
        self._update_status("连接失败")
        tk.Label(self.content_frame, text=f"❌ 连接失败\n{error_msg}",
                 font=_font(_f, 16), bg=COLORS['bg_page'],
                 fg=COLORS['damage']).pack(pady=30)
        tk.Button(self.content_frame, text="返回", font=_font(_f, 14),
                  command=self._back_to_main_menu, bg=COLORS['armor_bg'],
                  fg=COLORS['armor_text'], width=16, height=2).pack(pady=10)

    def _on_disconnected(self):
        self._running = False
        if self.conn:
            self.conn.close()
            self.conn = None
        self._clear_content()
        self._update_status("连接断开")
        tk.Label(self.content_frame, text="⚠ 与服务器的连接已断开",
                 font=_font(_f, 16), bg=COLORS['bg_page'],
                 fg=COLORS['damage']).pack(pady=30)
        tk.Button(self.content_frame, text="返回", font=_font(_f, 14),
                  command=self._back_to_main_menu, bg=COLORS['armor_bg'],
                  fg=COLORS['armor_text'], width=16, height=2).pack(pady=10)

    def _show_login_ui(self):
        self._clear_content()
        self._update_status("Garden of Thorn 荆棘花园")
        self._discovered_servers = {}
        self._discovery_running = False
        frame = tk.Frame(self.content_frame, padx=40, pady=20, bg=COLORS['bg_page'])
        frame.pack(expand=True)
        tk.Label(frame, text="Garden of Thorn", font=_font(_f, 24, True),
                 fg=COLORS['damage'], bg=COLORS['bg_page']).pack(pady=(10, 0))
        tk.Label(frame, text="荆棘花园", font=_font(_f, 18),
                 fg=COLORS['text_primary'], bg=COLORS['bg_page']).pack(pady=(0, 5))
        tk.Label(frame, text="局域网联机卡牌对战", font=_font(_f, 12),
                 fg=COLORS['text_secondary'], bg=COLORS['bg_page']).pack(pady=5)
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        nick_frame = tk.Frame(frame, bg=COLORS['bg_page'])
        nick_frame.pack(fill=tk.X, pady=5)
        tk.Label(nick_frame, text="昵称:", font=_font(_f, 13),
                 fg=COLORS['text_primary'], bg=COLORS['bg_page']).pack(side=tk.LEFT, padx=5)
        self.nick_entry = tk.Entry(nick_frame, font=_font(_f, 13), width=18,
                                   bg=COLORS['bg_card'], fg=COLORS['text_primary'])
        self.nick_entry.pack(side=tk.LEFT, padx=5)
        if self.nickname:
            self.nick_entry.insert(0, self.nickname)
        self._nick_error_label = tk.Label(nick_frame, text="", font=_font(_f, 10),
                                          fg=COLORS['damage'], bg=COLORS['bg_page'])
        self._nick_error_label.pack(side=tk.LEFT, padx=5)
        server_frame = tk.Frame(frame, bg=COLORS['bg_page'])
        server_frame.pack(fill=tk.X, pady=10)
        tk.Label(server_frame, text="服务器:", font=_font(_f, 13),
                 fg=COLORS['text_primary'], bg=COLORS['bg_page']).pack(side=tk.LEFT, padx=5)
        self.ip_entry = tk.Entry(server_frame, font=_font(_f, 13), width=18,
                                 bg=COLORS['bg_card'], fg=COLORS['text_primary'])
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(server_frame, text=f":{DEFAULT_PORT}", font=_font(_f, 13),
                 fg=COLORS['text_secondary'], bg=COLORS['bg_page']).pack(side=tk.LEFT)
        tk.Button(frame, text="进入大厅", font=_font(_f, 14),
                  command=self._on_login_connect, width=22, height=2,
                  bg=COLORS['health_bg'], fg=COLORS['health'],
                  relief=tk.RAISED, bd=2).pack(pady=15)
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        disc_frame = tk.Frame(frame, bg=COLORS['bg_page'])
        disc_frame.pack(fill=tk.X, pady=5)
        self._scan_btn = tk.Button(disc_frame, text="扫描局域网", font=_font(_f, 12),
                                   command=self._start_discovery,
                                   bg=COLORS['magic_bg'], fg=COLORS['magic_text'],
                                   width=14)
        self._scan_btn.pack(side=tk.LEFT, padx=5)
        self._disc_status = tk.Label(disc_frame, text="", font=_font(_f, 10),
                                     fg=COLORS['text_secondary'], bg=COLORS['bg_page'])
        self._disc_status.pack(side=tk.LEFT, padx=5)
        self._disc_listbox = tk.Listbox(frame, font=_font(_f, 11), height=4,
                                        bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                                        selectbackground=COLORS['bloom_bg'],
                                        selectforeground=COLORS['bloom'])
        self._disc_listbox.pack(fill=tk.X, pady=5)
        self._disc_listbox.bind('<Double-Button-1>', self._on_discovered_select)
        tk.Label(frame, text="双击列表中的服务器可自动填入IP",
                 font=_font(_f, 9),
                 fg=COLORS['text_secondary'], bg=COLORS['bg_page']).pack(pady=2)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"
        tk.Label(frame, text=f"本机IP: {local_ip}",
                 font=_font(_f, 11),
                 fg=COLORS['text_secondary'], bg=COLORS['bg_page']).pack(pady=5)
        tk.Label(frame, text="请先运行 server.py 启动服务器",
                 font=_font(_f, 10),
                 fg=COLORS['magic_text'], bg=COLORS['bg_page']).pack(pady=3)

    def _start_discovery(self):
        if self._discovery_running:
            return
        self._discovery_running = True
        self._discovered_servers = {}
        self._disc_listbox.delete(0, tk.END)
        self._scan_btn.config(state=tk.DISABLED)
        self._disc_status.config(text="扫描中...")
        threading.Thread(target=self._discovery_listen, daemon=True).start()

    def _discovery_listen(self):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind(('', DISCOVERY_PORT))
            sock.settimeout(1.0)
            deadline = time.time() + 6
            while time.time() < deadline and self._discovery_running:
                try:
                    data, addr = sock.recvfrom(1024)
                    info = json.loads(data.decode('utf-8'))
                    server_ip = addr[0]
                    server_port = info.get('port', DEFAULT_PORT)
                    key = f"{server_ip}:{server_port}"
                    if key not in self._discovered_servers:
                        self._discovered_servers[key] = {
                            'ip': server_ip,
                            'port': server_port,
                            'players': info.get('players', 0),
                            'rooms': info.get('rooms', 0),
                        }
                        self.root.after(0, self._update_discovery_list)
                except socket.timeout:
                    continue
                except Exception:
                    continue
        except Exception as e:
            print(f"发现服务错误: {e}")
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass
        self._discovery_running = False
        self.root.after(0, lambda: self._scan_btn.config(state=tk.NORMAL))
        self.root.after(0, lambda: self._disc_status.config(
            text=f"扫描完成，发现{len(self._discovered_servers)}个服务器"))

    def _update_discovery_list(self):
        self._disc_listbox.delete(0, tk.END)
        for key, srv in self._discovered_servers.items():
            label = f"{srv['ip']}:{srv['port']}  (玩家:{srv['players']} 房间:{srv['rooms']})"
            self._disc_listbox.insert(tk.END, label)

    def _on_discovered_select(self, event):
        sel = self._disc_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        keys = list(self._discovered_servers.keys())
        if idx < len(keys):
            srv = self._discovered_servers[keys[idx]]
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, srv['ip'])

    def _show_nick_error(self, msg: str):
        self._nick_error_label.config(text=msg)
        self.root.after(3000, lambda: self._nick_error_label.config(text=""))

    def _on_login_connect(self):
        raw_nick = self.nick_entry.get().strip()
        nickname = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', raw_nick)
        nickname = re.sub(r'[\u3000\s]+', '', nickname).strip()
        if not nickname:
            self._show_nick_error("请输入昵称")
            return
        display_width = wcwidth.wcswidth(nickname)
        if display_width < 0 or display_width > 12:
            self._show_nick_error(f"宽度{display_width}，最大12")
            return
        if '--' in nickname or '__' in nickname:
            self._show_nick_error("不能连续两个-或_")
            return
        ip = self.ip_entry.get().strip()
        if not ip:
            self._show_nick_error("请输入服务器IP")
            return
        self._running = True
        self.connect_and_login(ip, DEFAULT_PORT, nickname)

    def _back_to_main_menu(self):
        self._running = False
        if self.conn:
            self.conn.close()
            self.conn = None
        self.player_id = -1
        self.room_index = -1
        self.game_state = {}
        self.draft_state = {}
        self.lobby_players = []
        self.phase = 'connecting'
        self.response_pending = False
        self.choice_pending = False
        self._clear_content()
        self._show_login_ui()

    def _recv_loop(self):
        last_ping = time.time()
        while self._running and self.conn and self.conn.connected:
            try:
                messages = self.conn.receive_all()
                for msg in messages:
                    if msg.msg_type == 'pong':
                        continue
                    self.root.after(0, self._handle_message, msg)
                now = time.time()
                if now - last_ping > 15:
                    self._send(NetworkMessage('ping', {}))
                    last_ping = now
            except Exception as e:
                print(f"接收错误: {e}")
                break
            time.sleep(0.01)
        if self._running and self.phase not in ('connecting',):
            self.root.after(0, self._on_disconnected)

    def _handle_message(self, msg: NetworkMessage):
        try:
            if msg.msg_type == 'login_ok':
                self.player_id = msg.data['player_id']
                self.nickname = msg.data.get('nickname', self.nickname)
                self._update_status(f"已登录为 {self.nickname}")
            elif msg.msg_type == 'login_fail':
                self._clear_content()
                self._update_status("登录失败")
                tk.Label(self.content_frame,
                         text=f"❌ 登录失败\n{msg.data.get('reason', '昵称无效')}",
                         font=_font(_f, 16), bg=COLORS['bg_page'],
                         fg=COLORS['damage']).pack(pady=30)
                tk.Button(self.content_frame, text="返回主菜单",
                          font=_font(_f, 14),
                          command=self._back_to_main_menu,
                          bg=COLORS['armor_bg'], fg=COLORS['armor_text'],
                          width=16, height=2).pack(pady=10)
                return
            elif msg.msg_type == 'lobby_update':
                self.lobby_players = msg.data.get('players', [])
                self.player_id = msg.data.get('your_id', self.player_id)
                self.phase = 'lobby'
                self._show_lobby_ui()
            elif msg.msg_type == 'invite_received':
                self._show_invite_dialog(msg.data)
            elif msg.msg_type == 'invite_declined':
                messagebox.showinfo("邀请", "对方拒绝了你的邀请")
                self._update_status(f"大厅 | {self.nickname}")
            elif msg.msg_type == 'opponent_disconnected':
                messagebox.showinfo("提示", "对手已断开连接，返回大厅")
                self._send(NetworkMessage('return_lobby', {}))
            elif msg.msg_type == 'game_phase':
                self.phase = msg.data.get('phase', '')
                if self.phase == 'draft':
                    self._show_draft_ui()
                elif self.phase == 'playing':
                    self._clear_content()
                    self._update_status("游戏加载中...")
            elif msg.msg_type == 'event_select':
                self.phase = 'event_select'
                self.event_select_data = msg.data
                self._show_event_select_ui()
            elif msg.msg_type == 'draft_state':
                self.draft_state = msg.data
                self._update_draft_ui()
            elif msg.msg_type == 'state_update':
                self.game_state = msg.data
                self.phase = msg.data.get('phase', '')
                if 'your_id' in msg.data:
                    self.room_index = msg.data['your_id']
                self._update_game_ui()
            elif msg.msg_type == 'response_request':
                self.response_pending = True
                self.response_data = msg.data
                self._show_response_ui()
            elif msg.msg_type == 'choice_request':
                self.choice_pending = True
                self.choice_data = msg.data
                if self._pending_play_card:
                    self._clear_pending_card()
                self._show_choice_ui()
            elif msg.msg_type == 'error':
                self._update_status(f"错误: {msg.data.get('message', '')}")
                if self._pending_play_card:
                    self._clear_pending_card()
            elif msg.msg_type == 'server_broadcast':
                self._update_status(f"[服务器] {msg.data.get('message', '')}")
            elif msg.msg_type == 'rematch_requested':
                self._rematch_pending = True
                self._show_rematch_request(msg.data)
        except Exception as e:
            print(f"处理消息错误: {e}")
            import traceback
            traceback.print_exc()

    def _is_my_turn(self):
        gs = self.game_state
        if not gs:
            return False
        ri = self.room_index if self.room_index >= 0 else self.player_id
        if ri < 0:
            return False
        phase = gs.get('phase', '')
        if phase not in ('action',):
            return False
        return gs.get('current_player') == ri

    def _send(self, msg: NetworkMessage):
        if self.conn and self.conn.connected:
            self.conn.send(msg)

    def _on_window_resize(self, event):
        global SCALE
        if event.widget != self.root:
            return
        w = event.width
        new_scale = max(0.5, min(3.0, w / BASE_WIDTH))
        if abs(new_scale - self._last_scale) < 0.01:
            return
        if hasattr(self, '_resize_after_id') and self._resize_after_id:
            self.root.after_cancel(self._resize_after_id)
        self._resize_after_id = self.root.after(50, lambda: self._apply_resize(new_scale))

    def _apply_resize(self, new_scale):
        global SCALE
        self._last_scale = new_scale
        SCALE = new_scale
        self._resize_after_id = None
        if self.phase in ('playing', 'action', 'draw') and self.game_state:
            self._build_game_ui()
            self._update_game_ui()
        elif self.phase == 'draft' and self.draft_state:
            self._show_draft_ui()
        elif self.phase == 'event_select' and hasattr(self, 'event_select_data') and self.event_select_data:
            self._show_event_select_ui()
        elif self.phase == 'game_over':
            self._show_game_over()

    def _build_ui(self):
        self.main_frame = tk.Frame(self.root, bg=COLORS['bg_page'])
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.status_label = tk.Label(self.main_frame, text="Garden of Thorn 荆棘花园",
                                     font=_font(_f, 13, True),
                                     bg=COLORS['bg_page'], fg=COLORS['text_primary'])
        self.status_label.pack(side=tk.TOP, fill=tk.X, padx=10, pady=4)
        self.content_frame = tk.Frame(self.main_frame, bg=COLORS['bg_page'])
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        self._show_login_ui()

    def _update_status(self, text: str):
        self.status_label.config(text=text)

    def _clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def _show_lobby_ui(self):
        self._clear_content()
        self._update_status(f"大厅 | {self.nickname}")
        frame = tk.Frame(self.content_frame, bg=COLORS['bg_page'], padx=40, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(frame, text="在线玩家", font=_font(_f, 16, True),
                 fg=COLORS['text_primary'], bg=COLORS['bg_page']).pack(pady=10)
        list_frame = tk.Frame(frame, bg=COLORS['bg_card'], relief=tk.SUNKEN, bd=1)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        canvas = tk.Canvas(list_frame, bg=COLORS['bg_card'], highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        inner = tk.Frame(canvas, bg=COLORS['bg_card'])
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        others = [p for p in self.lobby_players if p['player_id'] != self.player_id]
        if not others:
            tk.Label(inner, text="暂无其他在线玩家，等待中...",
                     font=_font(_f, 12), fg=COLORS['text_secondary'],
                     bg=COLORS['bg_card']).pack(pady=20, padx=40)
        for p in others:
            row = tk.Frame(inner, bg=COLORS['bg_card'])
            row.pack(fill=tk.X, padx=10, pady=4)
            tk.Label(row, text=p['nickname'], font=_font(_f, 13),
                     fg=COLORS['text_primary'], bg=COLORS['bg_card']).pack(side=tk.LEFT, padx=10)
            tk.Button(row, text="邀请对局", font=_font(_f, 11),
                      bg=COLORS['bloom_bg'], fg=COLORS['bloom'],
                      command=lambda pid=p['player_id']: self._on_invite(pid)).pack(side=tk.RIGHT, padx=10)
        tk.Label(frame, text=f"在线人数: {len(self.lobby_players)}",
                 font=_font(_f, 11), fg=COLORS['text_secondary'],
                 bg=COLORS['bg_page']).pack(pady=10)
        tk.Button(frame, text="返回主界面", font=_font(_f, 12),
                  bg=COLORS['armor_bg'], fg=COLORS['armor_text'],
                  command=self._back_to_login, width=14).pack(pady=10)

    def _on_invite(self, target_id: int):
        self._send(NetworkMessage('invite', {'target_id': target_id}))
        self._update_status("邀请已发送，等待对方回应...")

    def _back_to_login(self):
        if self.conn and self.conn.connected:
            self.conn.close()
        self.conn = None
        self.player_id = None
        self.phase = 'login'
        self.game_state = None
        self.draft_state = None
        self.lobby_players = []
        self._running = False
        self._show_login_ui()

    def _show_invite_dialog(self, data: dict):
        inviter_name = data.get('inviter_name', '?')
        inviter_id = data.get('inviter_id', -1)
        result = messagebox.askyesno("收到邀请",
                                     f"{inviter_name} 邀请你进行对局！\n是否接受？")
        if result:
            self._send(NetworkMessage('accept_invite', {'inviter_id': inviter_id}))
        else:
            self._send(NetworkMessage('decline_invite', {'inviter_id': inviter_id}))

    def _make_bar(self, parent, label, color, bg_color):
        f = tk.Frame(parent, bg=COLORS['bg_page'])
        f.pack(side=tk.LEFT, padx=4)
        tk.Label(f, text=label, font=_font(_f, 10, True),
                 fg=color, bg=COLORS['bg_page']).pack(side=tk.LEFT)
        c = tk.Canvas(f, width=BAR_W(), height=BAR_H(), bg=bg_color,
                      highlightthickness=1, highlightbackground=COLORS['border_color'])
        c.pack(side=tk.LEFT, padx=2)
        bar = c.create_rectangle(1, 1, BAR_W(), BAR_H(), fill=color, outline='')
        txt_stroke = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            t = c.create_text(BAR_W() // 2 + dx, BAR_H() // 2 + dy, text="", font=_font(_f, 9, True), fill=color)
            txt_stroke.append(t)
        txt_bg = c.create_text(BAR_W() // 2, BAR_H() // 2, text="", font=_font(_f, 9, True),
                               fill=color)
        txt_fg = c.create_text(BAR_W() // 2, BAR_H() // 2, text="", font=_font(_f, 9, True),
                               fill='white')
        return c, bar, txt_stroke, txt_bg, txt_fg

    def _update_bar(self, canvas, bar, txt_stroke, txt_bg, txt_fg, cur, mx):
        ratio = max(0, min(1, cur / mx)) if mx > 0 else 0
        fill_w = max(1, int(BAR_W() * ratio))
        canvas.coords(bar, 1, 1, fill_w, BAR_H())
        text_str = f"{cur}/{mx}"
        cx, cy = BAR_W() // 2, BAR_H() // 2
        for i, (dx, dy) in enumerate([(-1, 0), (1, 0), (0, -1), (0, 1)]):
            canvas.itemconfig(txt_stroke[i], text=text_str)
            canvas.coords(txt_stroke[i], cx + dx, cy + dy)
        canvas.itemconfig(txt_bg, text=text_str)
        canvas.itemconfig(txt_fg, text=text_str)
        canvas.coords(txt_bg, cx, cy)
        canvas.coords(txt_fg, cx, cy)
        canvas.delete('bar_clip')
        for t in txt_stroke:
            canvas.tag_lower(t)
        canvas.tag_lower(txt_bg)
        canvas.tag_raise(bar, txt_bg)
        canvas.tag_raise(txt_fg, bar)
        if fill_w < BAR_W() - 1:
            clip = canvas.create_rectangle(fill_w, 0, BAR_W(), BAR_H(),
                                           fill=canvas['bg'], outline='', tags='bar_clip')
            canvas.tag_raise(clip, txt_fg)

    def _build_game_ui(self):
        self._clear_content()
        self.game_frame = tk.Frame(self.content_frame, bg=COLORS['bg_page'])
        self.game_frame.pack(fill=tk.BOTH, expand=True)
        gs = self.game_state or {}
        opp_name = gs.get('opponent_name', '对手')
        opp_frame = tk.LabelFrame(self.game_frame, text=f" {opp_name} ",
                                  font=_font(_f, 11, True),
                                  bg=COLORS['bg_page'], fg=COLORS['damage'])
        opp_frame.pack(fill=tk.X, padx=10, pady=3)
        self.opp_panel = tk.Frame(opp_frame, bg=COLORS['bg_page'])
        self.opp_panel.pack(fill=tk.X, padx=8, pady=2)
        self.opp_hand_frame = tk.Frame(opp_frame, bg=COLORS['bg_page'])
        self.opp_hand_frame.pack(fill=tk.X, padx=8, pady=2)
        self.opp_equip_frame = tk.Frame(opp_frame, bg=COLORS['bg_page'])
        self.opp_equip_frame.pack(fill=tk.X, padx=8, pady=2)
        log_frame = tk.LabelFrame(self.game_frame, text=" 战斗日志 ",
                                  font=_font(_f, 11, True),
                                  bg=COLORS['bg_page'], fg=COLORS['text_primary'])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=3)
        self.log_text = tk.Text(log_frame, height=8, font=_font(_f, 10),
                                state=tk.DISABLED, wrap=tk.WORD,
                                bg=COLORS['bg_card'], fg=COLORS['text_primary'])
        log_scroll = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        for tag, color in [('damage', COLORS['damage']), ('heal', COLORS['heal_text']),
                           ('poison', COLORS['poison']), ('fire', COLORS['fire']),
                           ('elixir', COLORS['elixir_text']), ('magic', COLORS['magic_text'])]:
            self.log_text.tag_configure(tag, foreground=color)
        self.log_text.tag_configure('round', foreground=COLORS['text_primary'],
                                    font=_font(_f, 10, True))
        you_frame = tk.LabelFrame(self.game_frame, text=f" {self.nickname} ",
                                  font=_font(_f, 11, True),
                                  bg=COLORS['bg_page'], fg=COLORS['health'])
        you_frame.pack(fill=tk.X, padx=10, pady=3)
        self.you_panel = tk.Frame(you_frame, bg=COLORS['bg_page'])
        self.you_panel.pack(fill=tk.X, padx=8, pady=2)
        self.you_equip_frame = tk.Frame(you_frame, bg=COLORS['bg_page'])
        self.you_equip_frame.pack(fill=tk.X, padx=8, pady=2)
        hand_play_frame = tk.Frame(you_frame, bg=COLORS['bg_page'])
        hand_play_frame.pack(fill=tk.X, padx=8, pady=4)
        self.hand_frame = tk.Frame(hand_play_frame, bg=COLORS['bg_page'])
        self.hand_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.play_zone = tk.Frame(hand_play_frame, bg=COLORS['bg_page'],
                                  relief=tk.GROOVE, bd=2, width=int(162*SCALE))
        self.play_zone.pack(side=tk.LEFT, fill=tk.Y, padx=8)
        self.play_zone.pack_propagate(False)
        self.play_zone_label = tk.Label(self.play_zone, text="拖牌\n至此\n出牌",
                                        font=_font(_f, 12, True),
                                        fg=COLORS['text_secondary'], bg=COLORS['bg_page'])
        self.play_zone_label.pack(expand=True)
        btn_frame = tk.Frame(you_frame, bg=COLORS['bg_page'])
        btn_frame.pack(fill=tk.X, padx=8, pady=3)
        self.end_turn_btn = tk.Button(btn_frame, text="结束回合",
                                      font=_font(_f, 13, True),
                                      command=self._on_end_turn, state=tk.DISABLED,
                                      bg=COLORS['damage_bg'], fg=COLORS['damage'],
                                      width=14)
        self.end_turn_btn.pack(side=tk.LEFT, padx=8)
        tk.Button(btn_frame, text="查看牌堆", font=_font(_f, 11),
                  command=self._view_deck, bg=COLORS['magic_bg'], fg=COLORS['magic_text'],
                  width=10).pack(side=tk.LEFT, padx=4)
        self.response_frame = tk.Frame(self.game_frame, bg=COLORS['bg_page'])
        self.response_frame.pack(fill=tk.X, padx=10, pady=3)
        self.opp_h_canvas, self.opp_h_bar, self.opp_h_stroke, self.opp_h_txt_bg, self.opp_h_txt_fg = self._make_bar(self.opp_panel, 'H', COLORS['health'], COLORS['health_bg'])
        self.opp_e_canvas, self.opp_e_bar, self.opp_e_stroke, self.opp_e_txt_bg, self.opp_e_txt_fg = self._make_bar(self.opp_panel, 'E', COLORS['elixir'], COLORS['elixir_bg'])
        self.opp_m_canvas, self.opp_m_bar, self.opp_m_stroke, self.opp_m_txt_bg, self.opp_m_txt_fg = self._make_bar(self.opp_panel, 'M', COLORS['magic'], COLORS['magic_bg'])
        self.opp_status_frame = tk.Frame(self.opp_panel, bg=COLORS['bg_page'])
        self.opp_status_frame.pack(side=tk.LEFT, padx=8)
        self.opp_info_label = tk.Label(self.opp_panel, text="", font=_font(_f, 10),
                                       fg=COLORS['text_secondary'], bg=COLORS['bg_page'])
        self.opp_info_label.pack(side=tk.RIGHT, padx=4)
        self.you_h_canvas, self.you_h_bar, self.you_h_stroke, self.you_h_txt_bg, self.you_h_txt_fg = self._make_bar(self.you_panel, 'H', COLORS['health'], COLORS['health_bg'])
        self.you_e_canvas, self.you_e_bar, self.you_e_stroke, self.you_e_txt_bg, self.you_e_txt_fg = self._make_bar(self.you_panel, 'E', COLORS['elixir'], COLORS['elixir_bg'])
        self.you_m_canvas, self.you_m_bar, self.you_m_stroke, self.you_m_txt_bg, self.you_m_txt_fg = self._make_bar(self.you_panel, 'M', COLORS['magic'], COLORS['magic_bg'])
        self.you_status_frame = tk.Frame(self.you_panel, bg=COLORS['bg_page'])
        self.you_status_frame.pack(side=tk.LEFT, padx=8)
        self.you_info_label = tk.Label(self.you_panel, text="", font=_font(_f, 10),
                                       fg=COLORS['text_secondary'], bg=COLORS['bg_page'])
        self.you_info_label.pack(side=tk.RIGHT, padx=4)

    def _update_game_ui(self):
        if self.phase == 'game_over':
            self._show_game_over()
            return
        if not hasattr(self, 'game_frame') or not self.game_frame.winfo_exists():
            self._build_game_ui()
        if self._pending_play_card and not self.response_pending:
            self._clear_pending_card()
        gs = self.game_state or {}
        you = gs.get('you', {})
        opp = gs.get('opponent', {})
        try:
            self._update_bar(self.opp_h_canvas, self.opp_h_bar, self.opp_h_stroke, self.opp_h_txt_bg, self.opp_h_txt_fg,
                             opp.get('health', 0), opp.get('max_health', 100))
            self._update_bar(self.opp_e_canvas, self.opp_e_bar, self.opp_e_stroke, self.opp_e_txt_bg, self.opp_e_txt_fg,
                             opp.get('elixir', 0), opp.get('max_elixir', 10))
            self._update_bar(self.opp_m_canvas, self.opp_m_bar, self.opp_m_stroke, self.opp_m_txt_bg, self.opp_m_txt_fg,
                             opp.get('magic', 0), opp.get('max_magic', 10))
            self._update_status_tags(self.opp_status_frame, opp)
            self.opp_info_label.config(text=f"手牌:{opp.get('hand_count', 0)} 牌堆:{opp.get('deck_count', 0)}")
        except Exception:
            pass
        try:
            self._update_bar(self.you_h_canvas, self.you_h_bar, self.you_h_stroke, self.you_h_txt_bg, self.you_h_txt_fg,
                             you.get('health', 0), you.get('max_health', 100))
            self._update_bar(self.you_e_canvas, self.you_e_bar, self.you_e_stroke, self.you_e_txt_bg, self.you_e_txt_fg,
                             you.get('elixir', 0), you.get('max_elixir', 10))
            self._update_bar(self.you_m_canvas, self.you_m_bar, self.you_m_stroke, self.you_m_txt_bg, self.you_m_txt_fg,
                             you.get('magic', 0), you.get('max_magic', 10))
            self._update_status_tags(self.you_status_frame, you)
            self.you_info_label.config(text=f"手牌:{you.get('hand_count', 0)} 牌堆:{you.get('deck_count', 0)} 弃牌:{you.get('discard_count', 0)}")
        except Exception:
            pass
        try:
            self._update_opp_hand(opp.get('hand_count', 0))
            self._update_equipment_display(opp, self.opp_equip_frame, False)
        except Exception:
            pass
        try:
            self._update_hand(you)
            self._update_equipment_display(you, self.you_equip_frame, True)
        except Exception:
            pass
        try:
            self._update_log(gs.get('log', []))
        except Exception:
            pass
        try:
            is_my_turn = self._is_my_turn()
            self.end_turn_btn.config(state=tk.NORMAL if is_my_turn else tk.DISABLED)
            if is_my_turn:
                self.play_zone.config(bg=COLORS['bloom_bg'], relief=tk.SOLID)
                self.play_zone_label.config(fg=COLORS['bloom'], bg=COLORS['bloom_bg'])
            else:
                self.play_zone.config(bg=COLORS['bg_page'], relief=tk.GROOVE)
                self.play_zone_label.config(fg=COLORS['text_secondary'], bg=COLORS['bg_page'])
        except Exception:
            is_my_turn = False
        phase = gs.get('phase', '')
        if phase == 'action':
            turn_text = '你的回合' if is_my_turn else '对手回合'
        elif phase == 'draw':
            turn_text = '抽牌阶段'
        elif phase == 'game_over':
            turn_text = '游戏结束'
        else:
            turn_text = '等待中'
        self._update_status(f"回合 {gs.get('round_num', 0)} | {turn_text}")

    def _update_status_tags(self, frame, player_data):
        for w in frame.winfo_children():
            w.destroy()
        tags = []
        p = player_data.get('poison', 0)
        f = player_data.get('fire', 0)
        v = player_data.get('vulnerable', 0)
        tri = player_data.get('triangle_stacks', 0)
        d = player_data.get('dodge', 0)
        n = player_data.get('nazar_active', False)
        n_hits = player_data.get('nazar_big_hits', 0)
        inv = player_data.get('invincible', False)
        sk = player_data.get('skip_turn', False)
        ep = player_data.get('equipment_protection', 0)
        if p > 0: tags.append(('中毒', str(p), COLORS['poison'], COLORS['poison_bg']))
        if f > 0: tags.append(('灼烧', str(f), COLORS['fire'], COLORS['fire_bg']))
        if v > 0: tags.append(('易伤', str(v), COLORS['vulnus'], COLORS['vulnus_bg']))
        if tri > 0: tags.append(('三角形', str(tri), COLORS['non_stack'], COLORS['non_stack_bg']))
        if d > 0: tags.append(('闪避', str(d), COLORS['guard'], COLORS['guard_bg']))
        if n: tags.append(('邪眼', f'{n_hits}/2', COLORS['magic'], COLORS['magic_bg']))
        if ep > 0: tags.append(('装保', str(ep), COLORS['indestructible'], COLORS['indestructible_bg']))
        if inv: tags.append(('无敌', '', COLORS['elixir'], COLORS['elixir_bg']))
        if sk: tags.append(('眩晕', '', COLORS['damage'], COLORS['damage_bg']))
        for name, val, fg, bg in tags:
            text = f"{name}:{val}" if val else name
            tk.Label(frame, text=text, font=_font(_f, 9),
                     fg=fg, bg=bg, padx=3, pady=1, relief=tk.GROOVE).pack(side=tk.LEFT, padx=2)

    def _update_opp_hand(self, count):
        for w in self.opp_hand_frame.winfo_children():
            w.destroy()
        for _ in range(count):
            f = tk.Frame(self.opp_hand_frame, bg=COLORS['armor_bg'],
                         width=CARD_BACK_W(), height=CARD_BACK_H(),
                         relief=tk.RAISED, bd=1,
                         highlightbackground=COLORS['armor_text'], highlightthickness=1)
            f.pack(side=tk.LEFT, padx=_p(3), pady=_p(2))
            f.pack_propagate(False)
            tk.Label(f, text="?", font=_font(_fc, 14, True),
                     fg=COLORS['armor_text'], bg=COLORS['armor_bg']).pack(expand=True)

    def _update_hand(self, player_data):
        for w in self.hand_frame.winfo_children():
            w.destroy()
        hand = player_data.get('hand', [])
        is_my_turn = self._is_my_turn()
        for card_dict in hand:
            try:
                card = CardInstance.from_dict(card_dict)
                card_def = card.card_def
                dup = self.game_state.get('you', {}).get('cards_played_this_turn', {}).get(card.def_id, 0)
                total_e = card.cost_e + dup
                total_m = card.cost_m
                type_str = {'attack': 'Thorn', 'skill': 'Bloom', 'equipment': 'Root', 'counter': 'Guard'}.get(card.card_type, '?')
                type_color = CARD_TYPE_COLORS.get(card.card_type, COLORS['text_primary'])
                cf = tk.Frame(self.hand_frame, bg=COLORS['bg_card'], width=CARD_W(), height=CARD_H(),
                              relief=tk.RAISED, bd=2,
                              highlightbackground=type_color, highlightthickness=2)
                cf.pack(side=tk.LEFT, padx=_p(4), pady=_p(2))
                cf.pack_propagate(False)
                top_row = tk.Frame(cf, bg=COLORS['bg_card'])
                top_row.pack(fill=tk.X, padx=_p(2), pady=(_p(2), 0))
                e_r = _p(38)
                e_canvas = tk.Canvas(top_row, width=e_r, height=e_r, bg=COLORS['bg_card'],
                                     highlightthickness=0)
                e_canvas.pack(side=tk.LEFT)
                e_canvas.create_oval(1, 1, e_r - 1, e_r - 1, fill=COLORS['elixir_bg'],
                                     outline=COLORS['elixir'], width=1)
                e_canvas.create_text(e_r // 2, e_r // 2, text=str(total_e),
                                     font=_font(_fc, 14, True), fill=COLORS['elixir_text'])
                m_r = _p(38)
                m_canvas = tk.Canvas(top_row, width=m_r, height=m_r, bg=COLORS['bg_card'],
                                     highlightthickness=0)
                m_canvas.pack(side=tk.RIGHT)
                m_canvas.create_oval(1, 1, m_r - 1, m_r - 1, fill=COLORS['magic_bg'],
                                     outline=COLORS['magic'], width=1)
                m_canvas.create_text(m_r // 2, m_r // 2, text=str(total_m),
                                     font=_font(_fc, 14, True), fill=COLORS['magic_text'])
                tk.Label(cf, text=f"{card_def.name_cn}", font=_font(_fc, 10, True),
                         fg=type_color, bg=COLORS['bg_card']).pack(pady=(_p(1), 0))
                tk.Label(cf, text=f"[{type_str}]", font=_font(_fc, 8),
                         fg=type_color, bg=COLORS['bg_card']).pack()
                tk.Label(cf, text=card_def.effect_text, font=_font(_fc, 7),
                         fg=COLORS['text_secondary'], bg=COLORS['bg_card'],
                         wraplength=CARD_W() - _p(6)).pack(pady=(0, _p(2)))
                flags_to_show = [f for f in card.flags if f in CARD_FLAGS]
                if flags_to_show:
                    flags_frame = tk.Frame(cf, bg=COLORS['bg_card'])
                    flags_frame.pack(pady=(0, _p(2)))
                    for flag in flags_to_show:
                        label, fg_color, bg_color = CARD_FLAGS[flag]
                        tk.Label(flags_frame, text=label, font=_font(_fc, 7),
                                 fg=fg_color, bg=bg_color, relief=tk.GROOVE, bd=1,
                                 padx=_p(2)).pack(side=tk.LEFT, padx=_p(1))
                if is_my_turn and card.card_type != 'counter':
                    drag_data = (card, total_e, total_m)
                    for child in cf.winfo_children():
                        child.bind('<ButtonPress-1>', lambda e, cid=card.instance_id, dd=drag_data: self._on_card_press(e, cid, dd))
                        child.bind('<B1-Motion>', lambda e, cid=card.instance_id, dd=drag_data: self._on_card_drag(e, cid, dd))
                        child.bind('<ButtonRelease-1>', lambda e, cid=card.instance_id: self._on_card_release(e, cid))
                        child.configure(cursor='hand2')
                    cf.bind('<ButtonPress-1>', lambda e, cid=card.instance_id, dd=drag_data: self._on_card_press(e, cid, dd))
                    cf.bind('<B1-Motion>', lambda e, cid=card.instance_id, dd=drag_data: self._on_card_drag(e, cid, dd))
                    cf.bind('<ButtonRelease-1>', lambda e, cid=card.instance_id: self._on_card_release(e, cid))
                else:
                    for child in cf.winfo_children():
                        try:
                            child.configure(fg=COLORS['text_secondary'])
                        except tk.TclError:
                            pass
                    if card.card_type == 'counter':
                        cf.configure(highlightbackground=COLORS['text_secondary'])
            except Exception as ex:
                print(f"渲染手牌错误: {ex}, card_dict={card_dict}")
                continue

    def _on_card_press(self, event, card_id, drag_data):
        card, total_e, total_m = drag_data
        self._dragging = True
        self._drag_card_id = card_id
        self._drag_card = card
        self._drag_total_e = total_e
        self._drag_total_m = total_m
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        w = event.widget
        self._drag_source_widget = w.master if hasattr(w, 'master') and isinstance(w.master, tk.Frame) and w.master.master == self.hand_frame else w

    def _insert_placeholder(self, after_widget=None):
        target_key = id(after_widget) if after_widget and after_widget.winfo_exists() else 0
        if self._drag_placeholder and self._drag_placeholder.winfo_exists():
            current_siblings = self.hand_frame.winfo_children()
            try:
                idx = current_siblings.index(self._drag_placeholder)
                prev = current_siblings[idx - 1] if idx > 0 else None
                current_key = id(prev) if prev and prev != self._drag_placeholder else 0
                if current_key == target_key:
                    return
            except ValueError:
                pass
            self._drag_placeholder.destroy()
        self._drag_placeholder = tk.Frame(self.hand_frame, bg=COLORS['border_color'],
                                          width=CARD_W(), height=CARD_H(),
                                          relief=tk.GROOVE, bd=2)
        self._drag_placeholder.pack_propagate(False)
        if after_widget and after_widget.winfo_exists():
            self._drag_placeholder.pack(side=tk.LEFT, padx=_p(4), pady=_p(2), after=after_widget)
        else:
            first = self.hand_frame.winfo_children()[0] if self.hand_frame.winfo_children() else None
            if first:
                self._drag_placeholder.pack(side=tk.LEFT, padx=_p(4), pady=_p(2), before=first)
            else:
                self._drag_placeholder.pack(side=tk.LEFT, padx=_p(4), pady=_p(2))

    def _on_card_drag(self, event, card_id, drag_data):
        if not self._dragging:
            return
        dx = abs(event.x_root - self._drag_start_x)
        dy = abs(event.y_root - self._drag_start_y)
        if dx + dy < 8:
            return
        if self._ghost is None:
            card, total_e, total_m = drag_data
            card_def = card.card_def
            self._ghost = tk.Toplevel(self.root)
            self._ghost.overrideredirect(True)
            try:
                self._ghost.attributes('-alpha', 0.80)
            except:
                pass
            type_color = CARD_TYPE_COLORS.get(card_def.card_type, COLORS['text_primary'])
            type_str = {'attack': 'Thorn', 'skill': 'Bloom', 'equipment': 'Root', 'counter': 'Guard'}.get(card_def.card_type, '?')
            gf = tk.Frame(self._ghost, bg=COLORS['bg_card'], width=CARD_W(), height=CARD_H(),
                          relief=tk.RAISED, bd=2,
                          highlightbackground=type_color, highlightthickness=2)
            gf.pack()
            gf.pack_propagate(False)
            top_row = tk.Frame(gf, bg=COLORS['bg_card'])
            top_row.pack(fill=tk.X, padx=_p(2), pady=(_p(2), 0))
            e_r = _p(38)
            e_canvas = tk.Canvas(top_row, width=e_r, height=e_r, bg=COLORS['bg_card'],
                                 highlightthickness=0)
            e_canvas.pack(side=tk.LEFT)
            e_canvas.create_oval(1, 1, e_r - 1, e_r - 1, fill=COLORS['elixir_bg'],
                                 outline=COLORS['elixir'], width=1)
            e_canvas.create_text(e_r // 2, e_r // 2, text=str(total_e),
                                 font=_font(_fc, 14, True), fill=COLORS['elixir_text'])
            m_r = _p(38)
            m_canvas = tk.Canvas(top_row, width=m_r, height=m_r, bg=COLORS['bg_card'],
                                 highlightthickness=0)
            m_canvas.pack(side=tk.RIGHT)
            m_canvas.create_oval(1, 1, m_r - 1, m_r - 1, fill=COLORS['magic_bg'],
                                 outline=COLORS['magic'], width=1)
            m_canvas.create_text(m_r // 2, m_r // 2, text=str(total_m),
                                 font=_font(_fc, 14, True), fill=COLORS['magic_text'])
            tk.Label(gf, text=card_def.name_cn, font=_font(_fc, 10, True),
                     fg=type_color, bg=COLORS['bg_card']).pack(pady=(_p(1), 0))
            tk.Label(gf, text=f"[{type_str}]", font=_font(_fc, 8),
                     fg=type_color, bg=COLORS['bg_card']).pack()
            tk.Label(gf, text=card_def.effect_text, font=_font(_fc, 7),
                     fg=COLORS['text_secondary'], bg=COLORS['bg_card'],
                     wraplength=CARD_W() - _p(6)).pack(pady=(0, _p(2)))
            flags_to_show = [f for f in card.flags if f in CARD_FLAGS]
            if flags_to_show:
                flags_frame = tk.Frame(gf, bg=COLORS['bg_card'])
                flags_frame.pack(pady=(0, _p(2)))
                for flag in flags_to_show:
                    label, fg_color, bg_color = CARD_FLAGS[flag]
                    tk.Label(flags_frame, text=label, font=_font(_fc, 7),
                             fg=fg_color, bg=bg_color, relief=tk.GROOVE, bd=1,
                             padx=_p(2)).pack(side=tk.LEFT, padx=_p(1))
            if self._drag_source_widget and self._drag_source_widget.winfo_exists():
                self._insert_placeholder(self._drag_source_widget)
                try:
                    self._drag_source_widget.pack_forget()
                except:
                    pass
        self._ghost.geometry(f"+{event.x_root - CARD_W() // 2}+{event.y_root - CARD_H() // 2}")
        try:
            children = [c for c in self.hand_frame.winfo_children()
                        if c != self._drag_placeholder and c.winfo_exists()]
            if children:
                best_after = None
                for child in children:
                    cx = child.winfo_rootx() + child.winfo_width() // 2
                    if event.x_root > cx:
                        best_after = child
                    else:
                        break
                self._insert_placeholder(best_after)
        except:
            pass
        try:
            if self.play_zone.winfo_exists():
                px1 = self.play_zone.winfo_rootx()
                py1 = self.play_zone.winfo_rooty()
                px2 = px1 + self.play_zone.winfo_width()
                py2 = py1 + self.play_zone.winfo_height()
                if px1 <= event.x_root <= px2 and py1 <= event.y_root <= py2:
                    self.play_zone.config(bg=COLORS['bloom'], relief=tk.SOLID)
                    self.play_zone_label.config(bg=COLORS['bloom'], fg='white')
                else:
                    if self._is_my_turn():
                        self.play_zone.config(bg=COLORS['bloom_bg'], relief=tk.SOLID)
                        self.play_zone_label.config(bg=COLORS['bloom_bg'], fg=COLORS['bloom'])
        except:
            pass

    def _can_play_card_client(self, card_dict) -> bool:
        gs = self.game_state or {}
        you = gs.get('you', {})
        if gs.get('phase', '') != 'action':
            return False
        if not self._is_my_turn():
            return False
        card = CardInstance.from_dict(card_dict)
        if card.card_type == 'counter':
            return False
        elixir = you.get('elixir', 0)
        magic = you.get('magic', 0)
        dup = you.get('cards_played_this_turn', {}).get(card.def_id, 0)
        total_e = card.cost_e + dup
        if total_e > elixir:
            return False
        if card.cost_m > magic:
            return False
        return True

    def _on_card_release(self, event, card_id):
        if not self._dragging:
            return
        self._dragging = False
        played = False
        try:
            if self.play_zone.winfo_exists():
                px1 = self.play_zone.winfo_rootx()
                py1 = self.play_zone.winfo_rooty()
                px2 = px1 + self.play_zone.winfo_width()
                py2 = py1 + self.play_zone.winfo_height()
                if px1 <= event.x_root <= px2 and py1 <= event.y_root <= py2:
                    played = True
        except:
            pass
        if self._ghost:
            self._ghost.destroy()
            self._ghost = None
        if played and card_id is not None:
            card_dict = None
            for c_dict in self.game_state.get('you', {}).get('hand', []):
                if c_dict.get('instance_id') == card_id:
                    card_dict = c_dict
                    break
            can_play = self._can_play_card_client(card_dict) if card_dict else False
            if can_play:
                success = self._play_card(card_id)
                if success:
                    if self._drag_placeholder and self._drag_placeholder.winfo_exists():
                        self._drag_placeholder.destroy()
                    self._drag_placeholder = None
                    self._drag_source_widget = None
                else:
                    self._restore_drag_card()
            else:
                self._update_status("无法出牌：条件不满足")
                self._restore_drag_card()
        else:
            self._restore_drag_card()
        if self._is_my_turn():
            self.play_zone.config(bg=COLORS['bloom_bg'], relief=tk.SOLID)
            self.play_zone_label.config(bg=COLORS['bloom_bg'], fg=COLORS['bloom'])
        else:
            self.play_zone.config(bg=COLORS['bg_page'], relief=tk.GROOVE)
            self.play_zone_label.config(bg=COLORS['bg_page'], fg=COLORS['text_secondary'])
        self._drag_card_id = None
        self._drag_card = None
        self._drag_total_e = 0
        self._drag_total_m = 0

    def _restore_drag_card(self):
        if self._drag_source_widget and self._drag_source_widget.winfo_exists():
            if self._drag_placeholder and self._drag_placeholder.winfo_exists():
                try:
                    self._drag_source_widget.pack(side=tk.LEFT, padx=_p(4), pady=_p(2),
                                                  after=self._drag_placeholder)
                except:
                    self._drag_source_widget.pack(side=tk.LEFT, padx=_p(4), pady=_p(2))
            else:
                self._drag_source_widget.pack(side=tk.LEFT, padx=_p(4), pady=_p(2))
        if self._drag_placeholder and self._drag_placeholder.winfo_exists():
            self._drag_placeholder.destroy()
        self._drag_placeholder = None
        self._drag_source_widget = None

    def _show_pending_card_in_play_zone(self):
        if not self._pending_play_card:
            return
        if not hasattr(self, 'play_zone') or not self.play_zone.winfo_exists():
            return
        for w in self.play_zone.winfo_children():
            w.destroy()
        card_def = self._pending_play_card
        type_color = CARD_TYPE_COLORS.get(card_def.card_type, COLORS['text_primary'])
        type_str = {'attack': 'Thorn', 'skill': 'Bloom', 'equipment': 'Root', 'counter': 'Guard'}.get(card_def.card_type, '?')
        tk.Label(self.play_zone, text=f"{card_def.name_cn}",
                 font=_font(_fc, 9, True), fg=type_color,
                 bg=COLORS['bloom_bg']).pack(pady=(4, 0))
        tk.Label(self.play_zone, text=f"[{type_str}]",
                 font=_font(_fc, 7), fg=type_color,
                 bg=COLORS['bloom_bg']).pack()
        tk.Label(self.play_zone, text="等待反制...",
                 font=_font(_fc, 8), fg=COLORS['damage'],
                 bg=COLORS['bloom_bg']).pack(pady=(2, 4))
        self.play_zone.config(bg=COLORS['bloom_bg'])

    def _clear_pending_card(self):
        self._pending_play_card = None
        if not hasattr(self, 'play_zone') or not self.play_zone.winfo_exists():
            return
        for w in self.play_zone.winfo_children():
            w.destroy()
        if self._is_my_turn():
            self.play_zone.config(bg=COLORS['bloom_bg'], relief=tk.SOLID)
            self.play_zone_label = tk.Label(self.play_zone, text="拖牌\n至此\n出牌",
                                            font=_font(_f, 12, True),
                                            fg=COLORS['bloom'], bg=COLORS['bloom_bg'])
        else:
            self.play_zone.config(bg=COLORS['bg_page'], relief=tk.GROOVE)
            self.play_zone_label = tk.Label(self.play_zone, text="拖牌\n至此\n出牌",
                                            font=_font(_f, 12, True),
                                            fg=COLORS['text_secondary'], bg=COLORS['bg_page'])
        self.play_zone_label.pack(expand=True)

    def _play_card(self, card_instance_id) -> bool:
        card = None
        for c_dict in self.game_state.get('you', {}).get('hand', []):
            if c_dict.get('instance_id') == card_instance_id:
                card = CardInstance.from_dict(c_dict)
                break
        if card is None:
            return False
        choice = self._get_card_choice(card)
        if choice is False:
            return False
        self._pending_play_card = card.card_def
        self._show_pending_card_in_play_zone()
        self._send(NetworkMessage('play_card', {'card_instance_id': card_instance_id, 'choice': choice}))
        return True

    def _get_card_choice(self, card):
        if card.def_id == 'Fission':
            attacks = [c for c in self.game_state.get('you', {}).get('hand', [])
                       if CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).card_type == 'attack'
                       and c.get('instance_id') != card.instance_id]
            if not attacks:
                messagebox.showinfo("提示", "手中没有攻击牌可以作为裂变目标")
                return False
            options = [f"{CARD_DEFS.get(a.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn}" for a in attacks]
            sel = self._simple_choice("选择裂变目标", options)
            if sel is None:
                return False
            return {'target_instance_id': attacks[sel].get('instance_id')}
        elif card.def_id == 'Fusion':
            attacks = [c for c in self.game_state.get('you', {}).get('hand', [])
                       if CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).card_type == 'attack'
                       and c.get('instance_id') != card.instance_id]
            same_name_groups: Dict[str, list] = {}
            for a in attacks:
                same_name_groups.setdefault(a.get('def_id', ''), []).append(a)
            valid_groups = {k: v for k, v in same_name_groups.items() if len(v) >= 2}
            if not valid_groups:
                messagebox.showinfo("提示", "手中没有足够的同名攻击牌")
                return False
            group_options = [f"{CARD_DEFS.get(k, CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn} x{len(v)}" for k, v in valid_groups.items()]
            sel = self._simple_choice("选择聚变卡组", group_options)
            if sel is None:
                return False
            group_key = list(valid_groups.keys())[sel]
            group = valid_groups[group_key][:3]
            return {'target_instance_ids': [c.get('instance_id') for c in group]}
        elif card.def_id == 'Mimic':
            others = [c for c in self.game_state.get('you', {}).get('hand', [])
                      if c.get('instance_id') != card.instance_id]
            if not others:
                messagebox.showinfo("提示", "手中没有其他卡牌")
                return False
            options = [f"{CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn}" for c in others]
            sel = self._simple_choice("选择拟态目标", options)
            if sel is None:
                return False
            return {'target_instance_id': others[sel].get('instance_id')}
        elif card.def_id == 'Chromosome':
            discard = self.game_state.get('you', {}).get('discard', [])
            if not discard:
                messagebox.showinfo("提示", "弃牌堆为空")
                return False
            options = [f"{CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn}" for c in discard]
            sel = self._simple_choice("从弃牌堆选择一张牌", options)
            if sel is None:
                return False
            return {'target_def_id': discard[sel].get('def_id')}
        elif card.def_id == 'Sewage':
            opp_eq = self.game_state.get('opponent', {}).get('equipment', [])
            destroyable = [e for e in opp_eq if 'indestructible' not in CARD_DEFS.get(
                e.get('card_instance', {}).get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '', flags=set())).flags]
            if not destroyable:
                messagebox.showinfo("提示", "敌方没有可摧毁的装备")
                return False
            options = [f"{CARD_DEFS.get(e.get('card_instance', {}).get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn}" for e in destroyable]
            sel = self._simple_choice("选择要摧毁的装备", options)
            if sel is None:
                return False
            return {'target_instance_id': destroyable[sel].get('card_instance', {}).get('instance_id')}
        elif card.def_id == 'Chilli':
            others = [c for c in self.game_state.get('you', {}).get('hand', [])
                      if c.get('instance_id') != card.instance_id]
            if others:
                options = [f"{CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn}" for c in others]
                sel = self._simple_choice("选择要丢弃的牌", options)
                if sel is None:
                    return False
                return {'target_instance_id': others[sel].get('instance_id')}
            return None
        return None

    def _simple_choice(self, title: str, options: list) -> Optional[int]:
        if not options:
            return None
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("440x520")
        dialog.configure(bg=COLORS['bg_page'])
        dialog.transient(self.root)
        dialog.grab_set()
        result = [None]
        selected = tk.IntVar(value=-1)

        def on_ok():
            val = selected.get()
            if val >= 0:
                result[0] = val
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=COLORS['bg_page'])
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=8)
        tk.Button(btn_frame, text="确定", command=on_ok,
                  font=_font(_f, 12), bg=COLORS['health_bg'],
                  fg=COLORS['health_text'], width=8).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="取消", command=on_cancel,
                  font=_font(_f, 12), bg=COLORS['damage_bg'],
                  fg=COLORS['damage'], width=8).pack(side=tk.RIGHT, padx=6)

        scroll_frame = tk.Frame(dialog, bg=COLORS['bg_page'])
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        canvas = tk.Canvas(scroll_frame, bg=COLORS['bg_page'], highlightthickness=0)
        scrollbar = tk.Scrollbar(scroll_frame, orient=tk.VERTICAL, command=canvas.yview)
        inner = tk.Frame(canvas, bg=COLORS['bg_page'])
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        for i, opt in enumerate(options):
            rb = tk.Radiobutton(inner, text=opt, variable=selected, value=i,
                                font=_font(_f, 12), anchor='w',
                                bg=COLORS['bg_page'], fg=COLORS['text_primary'],
                                selectcolor=COLORS['bloom_bg'],
                                activebackground=COLORS['bloom_bg'],
                                activeforeground=COLORS['text_primary'],
                                indicatoron=True)
            rb.pack(fill=tk.X, padx=8, pady=3)
        dialog.lift()
        dialog.focus_force()
        dialog.wait_window()
        return result[0]

    def _update_equipment_display(self, player_data, frame, is_my_equipment):
        for w in frame.winfo_children():
            w.destroy()
        equipment = player_data.get('equipment', [])
        for eq_dict in equipment:
            card = CardInstance.from_dict(eq_dict.get('card_instance', {}))
            turns = eq_dict.get('turns_equipped', 0)
            card_def = card.card_def
            corruption = eq_dict.get('corruption_active', False)
            label_text = f"{card_def.name_cn}(装{turns}回合)"
            if corruption:
                label_text += " [腐化]"
            bg_color = COLORS['bg_card']
            fg_color = COLORS['armor_text']
            if 'indestructible' in card_def.flags:
                fg_color = COLORS['indestructible']
                bg_color = COLORS['indestructible_bg']
            if card_def.trigger_cost_e >= 0 and is_my_equipment and turns >= 1:
                btn = tk.Button(frame, text=f"{label_text} 触发:{card_def.trigger_cost_e}E",
                                font=_font(_f, 9), bg=bg_color, fg=fg_color,
                                command=lambda eid=card.instance_id: self._on_use_trigger(eid))
                btn.pack(side=tk.LEFT, padx=3)
            else:
                tk.Label(frame, text=label_text, font=_font(_f, 10),
                         fg=fg_color, bg=bg_color, relief=tk.GROOVE, padx=6, pady=3).pack(side=tk.LEFT, padx=3)

    def _update_log(self, log: list):
        if not hasattr(self, 'log_text') or not self.log_text.winfo_exists():
            return
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        for line in log:
            tag = ''
            if '伤害' in line or 'D' in line:
                tag = 'damage'
            elif '+H' in line or '回复' in line:
                tag = 'heal'
            elif '中毒' in line:
                tag = 'poison'
            elif '灼烧' in line:
                tag = 'fire'
            elif '+E' in line or '能量' in line:
                tag = 'elixir'
            elif '+M' in line or '魔力' in line:
                tag = 'magic'
            elif '===' in line:
                tag = 'round'
            self.log_text.insert(tk.END, line + '\n', tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _on_use_trigger(self, equipment_instance_id):
        self._send(NetworkMessage('use_trigger', {'equipment_instance_id': equipment_instance_id}))

    def _on_end_turn(self):
        self._send(NetworkMessage('end_turn', {}))

    def _view_deck(self):
        deck = self.game_state.get('you', {}).get('deck', [])
        if not deck:
            messagebox.showinfo("牌堆", "牌堆为空")
            return
        from collections import Counter
        counts = Counter()
        for c in deck:
            cd = CARD_DEFS.get(c.get('def_id', ''), None)
            if cd:
                counts[cd.name_cn] += 1
        lines = [f"牌堆共{len(deck)}张："]
        for name, cnt in sorted(counts.items()):
            lines.append(f"  {name} ×{cnt}")
        dialog = tk.Toplevel(self.root)
        dialog.title("查看牌堆")
        dialog.geometry("300x400")
        dialog.configure(bg=COLORS['bg_page'])
        dialog.transient(self.root)
        dialog.grab_set()
        txt = tk.Text(dialog, font=_font(_f, 12), bg=COLORS['bg_card'],
                      fg=COLORS['text_primary'], state=tk.NORMAL, wrap=tk.WORD)
        txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        txt.insert(tk.END, '\n'.join(lines))
        txt.config(state=tk.DISABLED)
        tk.Button(dialog, text="关闭", command=dialog.destroy,
                  font=_font(_f, 12), bg=COLORS['damage_bg'], fg=COLORS['damage'],
                  width=8).pack(pady=8)

    def _show_response_ui(self):
        if not hasattr(self, 'response_frame') or not self.response_frame.winfo_exists():
            self._on_respond(None)
            return
        for w in self.response_frame.winfo_children():
            w.destroy()
        card_dict = self.response_data.get('card', {})
        card_def = CARD_DEFS.get(card_dict.get('def_id', ''), None)
        card_name = card_def.name_cn if card_def else card_dict.get('def_id', '?')
        trigger_desc = ''
        if card_def:
            if card_def.card_type == 'attack':
                trigger_desc = '敌方使用了攻击牌'
            elif card_def.card_type == 'skill':
                trigger_desc = '敌方使用了技能牌'
            if card_def.id in ('Sewage', 'MagicSewage'):
                trigger_desc += '，且即将摧毁装备'
        tk.Label(self.response_frame, text=f"⚠ {trigger_desc}：{card_name}",
                 font=_font(_f, 12, True), fg=COLORS['damage'],
                 bg=COLORS['bg_page']).pack(side=tk.LEFT, padx=8)
        you = self.game_state.get('you', {})
        my_elixir = you.get('elixir', 0)
        my_magic = you.get('magic', 0)
        counter_cards = self.response_data.get('counter_cards', [])
        has_affordable = False
        for cc in counter_cards:
            cc_def = CARD_DEFS.get(cc.get('def_id', ''), None)
            if cc_def and cc_def.cost_e <= my_elixir and cc_def.cost_m <= my_magic:
                has_affordable = True
                break
        for cc in counter_cards:
            cc_def = CARD_DEFS.get(cc.get('def_id', ''), None)
            if cc_def:
                can_afford = cc_def.cost_e <= my_elixir and cc_def.cost_m <= my_magic
                cost_str = f"{cc_def.cost_e}E" if cc_def.cost_m == 0 else f"{cc_def.cost_e}E/{cc_def.cost_m}M"
                btn_text = f"使用 {cc_def.name_cn} ({cost_str})"
                if not can_afford:
                    btn_text += " [资源不足]"
                btn = tk.Button(self.response_frame,
                                text=btn_text,
                                font=_font(_f, 11),
                                bg=COLORS['bloom_bg'] if can_afford else COLORS['non_stack_bg'],
                                fg=COLORS['bloom'] if can_afford else COLORS['non_stack'],
                                state=tk.NORMAL if can_afford else tk.DISABLED,
                                command=lambda cid=cc.get('instance_id'): self._on_respond(cid))
                btn.pack(side=tk.LEFT, padx=4)
        self._response_countdown = 5 if has_affordable else 3
        self._pass_btn = tk.Button(self.response_frame,
                                   text=f"不反制 ({self._response_countdown})",
                                   font=_font(_f, 11),
                                   bg=COLORS['damage_bg'], fg=COLORS['damage'],
                                   command=lambda: self._on_respond(None))
        self._pass_btn.pack(side=tk.LEFT, padx=8)
        self._response_timer_id = self.root.after(1000, self._tick_response_countdown)

    def _tick_response_countdown(self):
        self._response_countdown -= 1
        if self._response_countdown <= 0:
            self._on_respond(None)
            return
        if hasattr(self, '_pass_btn') and self._pass_btn and self._pass_btn.winfo_exists():
            self._pass_btn.config(text=f"不反制 ({self._response_countdown})")
            self._response_timer_id = self.root.after(1000, self._tick_response_countdown)

    def _on_respond(self, card_instance_id):
        if hasattr(self, '_response_timer_id') and self._response_timer_id:
            self.root.after_cancel(self._response_timer_id)
            self._response_timer_id = None
        self._pass_btn = None
        self.response_pending = False
        for w in self.response_frame.winfo_children():
            w.destroy()
        self._send(NetworkMessage('response', {'card_instance_id': card_instance_id}))

    def _show_choice_ui(self):
        choice_type = self.choice_data.get('choice_type', '')
        card_dict = self.choice_data.get('card', {})
        card_def = CARD_DEFS.get(card_dict.get('def_id', ''), None)
        card_name = card_def.name_cn if card_def else '?'
        choice_result = None
        if choice_type == 'choose_attack_from_hand':
            attacks = [c for c in self.game_state.get('you', {}).get('hand', [])
                       if CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).card_type == 'attack']
            if not attacks:
                messagebox.showinfo("提示", "手中没有攻击牌")
            else:
                options = [f"{CARD_DEFS.get(a.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn}" for a in attacks]
                sel = self._simple_choice(f"为{card_name}选择攻击牌", options)
                if sel is not None and 0 <= sel < len(attacks):
                    choice_result = {'target_instance_id': attacks[sel].get('instance_id')}
        elif choice_type == 'choose_enemy_equipment':
            opp_eq = self.game_state.get('opponent', {}).get('equipment', [])
            if not opp_eq:
                messagebox.showinfo("提示", "敌方没有装备")
            else:
                options = [f"{CARD_DEFS.get(e.get('card_instance', {}).get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn}" for e in opp_eq]
                sel = self._simple_choice(f"为{card_name}选择目标装备", options)
                if sel is not None and 0 <= sel < len(opp_eq):
                    choice_result = {'target_instance_id': opp_eq[sel].get('card_instance', {}).get('instance_id')}
        elif choice_type == 'choose_card_to_discard':
            other_cards = self.game_state.get('you', {}).get('hand', [])
            if not other_cards:
                pass
            else:
                options = [f"{CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn}" for c in other_cards]
                sel = self._simple_choice(f"为{card_name}选择丢弃的牌", options)
                if sel is not None and 0 <= sel < len(other_cards):
                    choice_result = {'target_instance_id': other_cards[sel].get('instance_id')}
        elif choice_type == 'choose_card_from_deck':
            deck = self.game_state.get('you', {}).get('deck', [])
            if not deck:
                messagebox.showinfo("提示", "牌堆为空")
            else:
                options = [f"{CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn}" for c in deck]
                sel = self._simple_choice(f"为{card_name}从牌堆选牌", options)
                if sel is not None and 0 <= sel < len(deck):
                    choice_result = {'target_def_id': deck[sel].get('def_id')}
        elif choice_type == 'choose_card_from_discard':
            discard = self.game_state.get('you', {}).get('discard', [])
            if not discard:
                messagebox.showinfo("提示", "弃牌堆为空")
            else:
                options = [f"{CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn}" for c in discard]
                sel = self._simple_choice(f"为{card_name}从弃牌堆选牌", options)
                if sel is not None and 0 <= sel < len(discard):
                    choice_result = {'target_def_id': discard[sel].get('def_id')}
        elif choice_type == 'choose_same_attacks_from_hand':
            attacks = [c for c in self.game_state.get('you', {}).get('hand', [])
                       if CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).card_type == 'attack']
            same_name_groups: Dict[str, list] = {}
            for a in attacks:
                same_name_groups.setdefault(a.get('def_id', ''), []).append(a)
            valid_groups = {k: v for k, v in same_name_groups.items() if len(v) >= 2}
            if not valid_groups:
                messagebox.showinfo("提示", "手中没有足够的同名攻击牌")
            else:
                group_options = [f"{CARD_DEFS.get(k, CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn} x{len(v)}" for k, v in valid_groups.items()]
                sel = self._simple_choice(f"为{card_name}选择攻击牌组", group_options)
                if sel is not None:
                    group_key = list(valid_groups.keys())[sel]
                    group = valid_groups[group_key][:3]
                    choice_result = {'target_instance_ids': [c.get('instance_id') for c in group]}
        elif choice_type == 'choose_card_from_hand':
            other_cards = self.game_state.get('you', {}).get('hand', [])
            if not other_cards:
                pass
            else:
                options = [f"{CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn}" for c in other_cards]
                sel = self._simple_choice(f"为{card_name}选择手牌", options)
                if sel is not None and 0 <= sel < len(other_cards):
                    choice_result = {'target_instance_id': other_cards[sel].get('instance_id')}
        self._send(NetworkMessage('resolve_choice', {'choice': choice_result}))
        self.choice_pending = False

    def _show_event_select_ui(self):
        self._clear_content()
        self._update_status("选择开局事件")
        data = self.event_select_data
        events = data.get('events', [])
        opp_selected = data.get('opponent_selected', False)
        my_pick = data.get('my_pick', None)

        outer = tk.Frame(self.content_frame, bg=COLORS['bg_page'])
        outer.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(outer, bg=COLORS['bg_page'], highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=COLORS['bg_page'])
        scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas_win_id = canvas.create_window((0, 0), window=scroll_frame, anchor='center')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _center_scroll_frame(event=None):
            cw = canvas.winfo_width()
            fw = scroll_frame.winfo_reqwidth()
            x = max(0, (cw - fw) // 2)
            canvas.coords(canvas_win_id, x, 0)

        canvas.bind('<Configure>', lambda e: (_center_scroll_frame(), canvas.configure(scrollregion=canvas.bbox('all'))))

        frame = tk.Frame(scroll_frame, bg=COLORS['bg_page'], padx=40, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="⚔ 选择开局事件 ⚔", font=_font(_f, 20, True),
                 fg=COLORS['damage'], bg=COLORS['bg_page']).pack(pady=(10, 5))
        tk.Label(frame, text="选择一个事件影响本局游戏", font=_font(_f, 12),
                 fg=COLORS['text_secondary'], bg=COLORS['bg_page']).pack(pady=(0, 15))

        if my_pick is not None:
            event_name = '?'
            for ev in events:
                if ev and ev.get('id') == my_pick:
                    event_name = ev.get('name', '?')
                    break
            tk.Label(frame, text=f"✓ 你已选择: {event_name}", font=_font(_f, 16, True),
                     fg=COLORS['health'], bg=COLORS['health_bg'],
                     relief=tk.GROOVE, padx=20, pady=10).pack(pady=15)
            if not opp_selected:
                tk.Label(frame, text="⏳ 等待对手选择...", font=_font(_f, 14),
                         fg=COLORS['magic_text'], bg=COLORS['bg_page']).pack(pady=10)
            else:
                tk.Label(frame, text="✓ 对手已选择", font=_font(_f, 14),
                         fg=COLORS['health'], bg=COLORS['bg_page']).pack(pady=10)
            return

        opp_status = "✓ 对手已选择" if opp_selected else "⏳ 对手选择中..."
        tk.Label(frame, text=opp_status, font=_font(_f, 11),
                 fg=COLORS['health'] if opp_selected else COLORS['text_secondary'],
                 bg=COLORS['bg_page']).pack(pady=(0, 10))

        events_frame = tk.Frame(frame, bg=COLORS['bg_page'])
        events_frame.pack(pady=10)

        for i, event in enumerate(events):
            if event is None:
                continue
            eid = event.get('id')
            name = event.get('name', '?')
            desc = event.get('desc', '')

            pos_labels = {1: 'Ⅰ', 2: 'Ⅱ', 3: 'Ⅲ'}
            pos_label = pos_labels.get(i + 1, '?')

            card_bg = COLORS['bg_card']
            border_color = COLORS['magic']
            if eid == 1:
                border_color = COLORS['health']
            elif eid in (2, 3, 8):
                border_color = COLORS['magic']
            elif eid in (4, 5, 6, 7):
                border_color = COLORS['fire']

            ef = tk.Frame(events_frame, bg=card_bg, relief=tk.RAISED, bd=2,
                          highlightbackground=border_color, highlightthickness=3,
                          width=int(320 * SCALE), height=int(240 * SCALE))
            ef.pack(side=tk.LEFT, padx=int(15 * SCALE), pady=10)
            ef.pack_propagate(False)

            header = tk.Frame(ef, bg=border_color, height=int(40 * SCALE))
            header.pack(fill=tk.X)
            header.pack_propagate(False)
            tk.Label(header, text=f" {pos_label} {name}", font=_font(_f, 14, True),
                     fg='white', bg=border_color, anchor='center').pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

            desc_label = tk.Label(ef, text=desc, font=_font(_f, 11),
                                  fg=COLORS['text_primary'], bg=card_bg,
                                  wraplength=int(280 * SCALE), justify=tk.LEFT)
            desc_label.pack(padx=12, pady=(10, 5), anchor='w')

            select_btn = tk.Button(ef, text="选择此事件", font=_font(_f, 11, True),
                                   bg=COLORS['bloom_bg'], fg=COLORS['bloom'],
                                   activebackground=COLORS['bloom'],
                                   activeforeground='white',
                                   relief=tk.RAISED, bd=2,
                                   command=lambda e=eid: self._on_event_select(e))
            select_btn.pack(pady=(5, 10))

            for child in ef.winfo_children():
                if child != select_btn:
                    child.bind('<Button-1>', lambda ev, e=eid: self._on_event_select(e))
                    try:
                        child.configure(cursor='hand2')
                    except tk.TclError:
                        pass

    def _on_event_select(self, event_id):
        data = self.event_select_data
        sub_choice = None

        if event_id == 2:
            magic_options = data.get('magic_options', [])
            draft_picks = data.get('draft_picks', [])
            if magic_options:
                magic_choice = self._show_magic_card_choice(magic_options)
                if magic_choice is None:
                    return
                if draft_picks:
                    card_choice = self._show_card_conversion_choice(
                        draft_picks, 3, f"选择要转化为魔法牌的牌（最多3张）")
                    if card_choice is None:
                        return
                    sub_choice = {
                        'convert_def_id': magic_choice['convert_def_id'],
                        'convert_def_ids': card_choice['convert_def_ids'],
                    }
                else:
                    sub_choice = magic_choice
        elif event_id == 3:
            draft_picks = data.get('draft_picks', [])
            if draft_picks:
                sub_choice = self._show_light_conversion_choice(draft_picks)
                if sub_choice is None:
                    return

        self._send(NetworkMessage('select_opening_event', {
            'event_id': event_id,
            'sub_choice': sub_choice,
        }))
        self._update_status("已选择事件，等待对手...")

    def _show_magic_card_choice(self, magic_options):
        options = []
        for def_id in magic_options:
            card_def = CARD_DEFS.get(def_id)
            if card_def:
                options.append(f"{card_def.name_cn} ({card_def.cost_e}E/{card_def.cost_m}M) {card_def.effect_text}")
        if not options:
            return None
        sel = self._simple_choice("选择一种魔法牌（最多3张牌将转化为该牌）", options)
        if sel is None:
            return None
        return {'convert_def_id': magic_options[sel]}

    def _show_light_conversion_choice(self, draft_picks):
        return self._show_card_conversion_choice(draft_picks, 5, "选择要转化为Light的牌（最多5张）")

    def _show_card_conversion_choice(self, draft_picks, max_count, title):
        from collections import Counter
        counts = Counter(draft_picks)

        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry(f"{int(520*SCALE)}x{int(600*SCALE)}")
        dialog.configure(bg=COLORS['bg_page'])
        dialog.transient(self.root)
        dialog.grab_set()

        result = [None]

        tk.Label(dialog, text=title, font=_font(_f, 14, True),
                 fg=COLORS['magic_text'], bg=COLORS['bg_page']).pack(pady=(12, 4))
        tk.Label(dialog, text=f"每种牌可选择转化数量，最多共{max_count}张", font=_font(_f, 10),
                 fg=COLORS['text_secondary'], bg=COLORS['bg_page']).pack(pady=(0, 8))

        scroll_frame = tk.Frame(dialog, bg=COLORS['bg_page'])
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)
        canvas = tk.Canvas(scroll_frame, bg=COLORS['bg_page'], highlightthickness=0)
        scrollbar = tk.Scrollbar(scroll_frame, orient=tk.VERTICAL, command=canvas.yview)
        inner = tk.Frame(canvas, bg=COLORS['bg_page'])
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        card_entries = []
        for def_id, count in sorted(counts.items(), key=lambda x: CARD_DEFS.get(x[0], CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn):
            if def_id == 'Light' and max_count == 5:
                continue
            card_def = CARD_DEFS.get(def_id)
            if not card_def:
                continue
            cf = tk.Frame(inner, bg=COLORS['bg_card'], relief=tk.GROOVE, bd=1)
            cf.pack(fill=tk.X, padx=8, pady=3)

            type_color = CARD_TYPE_COLORS.get(card_def.card_type, COLORS['text_primary'])
            tk.Label(cf, text=f"{card_def.name_cn}", font=_font(_f, 12, True),
                     fg=type_color, bg=COLORS['bg_card']).pack(side=tk.LEFT, padx=(8, 4))
            tk.Label(cf, text=f"x{count}", font=_font(_f, 11),
                     fg=COLORS['text_secondary'], bg=COLORS['bg_card']).pack(side=tk.LEFT, padx=4)

            var = tk.IntVar(value=0)
            max_convert = min(count, max_count)
            spin = tk.Spinbox(cf, from_=0, to=max_convert, textvariable=var,
                              width=3, font=_font(_f, 11), state='readonly')
            spin.pack(side=tk.RIGHT, padx=8)
            tk.Label(cf, text="转化:", font=_font(_f, 10),
                     fg=COLORS['text_secondary'], bg=COLORS['bg_card']).pack(side=tk.RIGHT)
            card_entries.append((def_id, var, count))

        count_label = tk.Label(dialog, text=f"已选: 0/{max_count}", font=_font(_f, 12, True),
                               fg=COLORS['magic_text'], bg=COLORS['bg_page'])
        count_label.pack(pady=4)

        def update_count(*args):
            total = sum(v.get() for _, v, _ in card_entries)
            color = COLORS['damage'] if total > max_count else COLORS['magic_text']
            count_label.config(text=f"已选: {total}/{max_count}", fg=color)

        for _, var, _ in card_entries:
            var.trace_add('write', update_count)

        def on_ok():
            total = sum(v.get() for _, v, _ in card_entries)
            if total > max_count:
                messagebox.showwarning("提示", f"最多选择{max_count}张", parent=dialog)
                return
            selected = []
            for def_id, var, _ in card_entries:
                for _ in range(var.get()):
                    selected.append(def_id)
            result[0] = {'convert_def_ids': selected} if selected else None
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=COLORS['bg_page'])
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=8)
        tk.Button(btn_frame, text="确定", command=on_ok,
                  font=_font(_f, 12), bg=COLORS['health_bg'],
                  fg=COLORS['health_text'], width=8).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="取消", command=on_cancel,
                  font=_font(_f, 12), bg=COLORS['damage_bg'],
                  fg=COLORS['damage'], width=8).pack(side=tk.RIGHT, padx=6)

        dialog.lift()
        dialog.focus_force()
        dialog.wait_window()
        return result[0]

    def _show_draft_ui(self):
        self._clear_content()
        self._update_status("选牌阶段")
        self.draft_frame = tk.Frame(self.content_frame, bg=COLORS['bg_page'])
        self.draft_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        tk.Label(self.draft_frame, text="选牌阶段", font=_font(_f, 16, True),
                 bg=COLORS['bg_page'], fg=COLORS['text_primary']).pack(pady=8)
        self.draft_info = tk.Label(self.draft_frame, text="", font=_font(_f, 12),
                                   bg=COLORS['bg_page'], fg=COLORS['text_secondary'])
        self.draft_info.pack(pady=4)
        self.draft_options_frame = tk.Frame(self.draft_frame, bg=COLORS['bg_page'])
        self.draft_options_frame.pack(pady=10)
        self.draft_picks_label = tk.Label(self.draft_frame, text="已选: ", font=_font(_f, 12),
                                          bg=COLORS['bg_page'], fg=COLORS['text_primary'])
        self.draft_picks_label.pack(pady=5)
        self.draft_reroll_btn = tk.Button(self.draft_frame, text="重选", font=_font(_f, 12),
                                          command=self._on_draft_reroll,
                                          bg=COLORS['magic_bg'], fg=COLORS['magic_text'])
        self.draft_reroll_btn.pack(pady=5)

    def _update_draft_ui(self):
        if self.phase not in ('draft',):
            return
        if not hasattr(self, 'draft_frame') or not self.draft_frame.winfo_exists():
            self._show_draft_ui()
        ds = self.draft_state
        round_num = ds.get('round', 1)
        total = ds.get('total_rounds', 15)
        rerolls = ds.get('rerolls', 0)
        opp_count = ds.get('opponent_picks_count', 0)
        my_count = len(ds.get('picks', []))
        self.draft_info.config(text=f"第 {round_num}/{total} 轮 | 重选次数: {rerolls} | 对手已选: {opp_count}张")
        for w in self.draft_options_frame.winfo_children():
            w.destroy()
        if my_count >= total:
            tk.Label(self.draft_options_frame, text="已选完15张牌，等待对手...",
                     font=_font(_f, 14), fg=COLORS['health'],
                     bg=COLORS['bg_page']).pack(pady=20)
        else:
            for opt_dict in ds.get('options', []):
                card = CardInstance.from_dict(opt_dict)
                card_def = card.card_def
                type_color = CARD_TYPE_COLORS.get(card.card_type, COLORS['text_primary'])
                btn_text = (f"{card_def.name_cn} ({card_def.name_en})\n"
                            f"费用: {card_def.cost_e}E/{card_def.cost_m}M\n"
                            f"{card_def.effect_text}\n{card_def.description}")
                tk.Button(self.draft_options_frame, text=btn_text,
                          font=_font(_f, 10), width=32, height=8,
                          wraplength=int(240*SCALE), bg=COLORS['bg_card'], fg=type_color,
                          relief=tk.RAISED, bd=2,
                          command=lambda d=card.def_id: self._on_draft_pick(d)).pack(side=tk.LEFT, padx=8, pady=4)
        picks = ds.get('picks', [])
        picks_cn = [CARD_DEFS.get(pid, CardDef('', '', pid, 0, 0, '', 0, '', '', '')).name_cn for pid in picks]
        self.draft_picks_label.config(text=f"已选({len(picks)}): {', '.join(picks_cn)}")
        self.draft_reroll_btn.config(state=tk.NORMAL if rerolls > 0 and my_count < total else tk.DISABLED)

    def _on_draft_pick(self, def_id):
        self._send(NetworkMessage('draft_pick', {'def_id': def_id}))

    def _on_draft_reroll(self):
        self._send(NetworkMessage('draft_reroll', {}))

    def _show_game_over(self):
        self._rematch_pending = False
        self._rematch_sent = False
        self._clear_content()
        ri = self.room_index if self.room_index >= 0 else self.player_id
        winner = self.game_state.get('winner', -1)
        if winner == ri:
            text, color, bg = "你赢了！", COLORS['health'], COLORS['health_bg']
        else:
            text, color, bg = "你输了...", COLORS['damage'], COLORS['damage_bg']
        tk.Label(self.content_frame, text=text, font=_font(_f, 28, True),
                 fg=color, bg=bg).pack(expand=True, pady=20)
        log = self.game_state.get('log', [])
        if log:
            lt = tk.Text(self.content_frame, height=10, font=_font(_f, 10),
                         state=tk.DISABLED, bg=COLORS['bg_card'], fg=COLORS['text_primary'])
            lt.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
            lt.config(state=tk.NORMAL)
            for line in log:
                lt.insert(tk.END, line + '\n')
            lt.config(state=tk.DISABLED)
        self._gameover_btn_frame = tk.Frame(self.content_frame, bg=COLORS['bg_page'])
        self._gameover_btn_frame.pack(pady=15)
        self._rematch_btn = tk.Button(self._gameover_btn_frame, text="申请再来一局",
                                      font=_font(_f, 14, True),
                                      command=self._on_rematch, bg=COLORS['bloom_bg'],
                                      fg=COLORS['bloom'], width=16, height=2)
        self._rematch_btn.pack(side=tk.LEFT, padx=10)
        tk.Button(self._gameover_btn_frame, text="返回大厅", font=_font(_f, 14, True),
                  command=self._on_return_lobby, bg=COLORS['armor_bg'], fg=COLORS['armor_text'],
                  width=14, height=2).pack(side=tk.LEFT, padx=10)

    def _show_rematch_request(self, data):
        self._rematch_pending = True
        if hasattr(self, '_rematch_btn') and self._rematch_btn and self._rematch_btn.winfo_exists():
            self._rematch_btn.config(text="同意再来一局", command=self._on_accept_rematch,
                                     bg=COLORS['health_bg'], fg=COLORS['health_text'])
        self._update_status("对手申请再来一局！")

    def _on_rematch(self):
        self._rematch_sent = True
        self._send(NetworkMessage('rematch', {}))
        if hasattr(self, '_rematch_btn') and self._rematch_btn and self._rematch_btn.winfo_exists():
            self._rematch_btn.config(text="已申请...", state=tk.DISABLED)
        self._update_status("已发送再战请求，等待对方同意...")

    def _on_accept_rematch(self):
        self._send(NetworkMessage('rematch', {}))
        self._update_status("已同意再战，等待开始...")

    def _on_return_lobby(self):
        self._send(NetworkMessage('return_lobby', {}))

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        self._running = False
        if hasattr(self, '_response_timer_id') and self._response_timer_id:
            self.root.after_cancel(self._response_timer_id)
            self._response_timer_id = None
        if self.conn:
            self.conn.close()
        self.root.destroy()
