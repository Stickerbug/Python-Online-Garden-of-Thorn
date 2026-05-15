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
from i18n import t, load_lang, current_lang, get_available_langs, get_lang_display_name

try:
    from mod_loader import merge_mod_cards_to_card_defs
    merge_mod_cards_to_card_defs()
except Exception:
    pass

DISCOVERY_PORT = 4160

import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def _get_resource_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

FONT_DIR = os.path.join(_get_resource_dir(), 'fonts')
FONT_CN = '思源黑体 Kreadon'
FONT_EN_BOLD = 'Kreadon Demi'
_FONT_FALLBACK_CN = 'Microsoft YaHei'
_FONT_FALLBACK_EN = 'Arial'

def _load_fonts():
    loaded = False
    search_dirs = [FONT_DIR]
    if getattr(sys, 'frozen', False):
        exe_font_dir = os.path.join(os.path.dirname(sys.executable), 'fonts')
        if exe_font_dir not in search_dirs:
            search_dirs.append(exe_font_dir)
    for search_dir in search_dirs:
        for fname in ['思源黑体-Kreadon.ttf', 'Kreadon-Demi.ttf']:
            fpath = os.path.join(search_dir, fname)
            if os.path.exists(fpath):
                try:
                    ctypes.windll.gdi32.AddFontResourceExW(fpath, 0x10, 0)
                    loaded = True
                except Exception:
                    pass
    if not loaded:
        global FONT_CN, FONT_EN_BOLD
        FONT_CN = _FONT_FALLBACK_CN
        FONT_EN_BOLD = _FONT_FALLBACK_EN

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
    'thorn': COLORS['damage'],
    'bloom': COLORS['magic'],
    'root': COLORS['armor'],
    'guard': COLORS['bloom'],
}

CARD_FLAG_STYLES = {
    'precision': (COLORS['precise'], COLORS['precise_bg']),
    'exile': (COLORS['banish'], COLORS['banish_bg']),
    'non_stackable': (COLORS['non_stack'], COLORS['non_stack_bg']),
    'indestructible': (COLORS['indestructible'], COLORS['indestructible_bg']),
    'sprout': ('#2ecc71', '#27ae60'),
    'symbiosis': ('#3498db', '#2980b9'),
}

CARD_FLAG_KEYS = {
    'precision': 'flag_precision',
    'exile': 'flag_exile',
    'non_stackable': 'flag_non_stackable',
    'indestructible': 'flag_indestructible',
    'sprout': 'flag_sprout',
    'symbiosis': 'flag_symbiosis',
}


def get_card_flags():
    result = {}
    for flag, (fg, bg) in CARD_FLAG_STYLES.items():
        label = t(CARD_FLAG_KEYS.get(flag, flag))
        result[flag] = (label, fg, bg)
    return result


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
        self.root.title(t('app_title'))
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
        self._dark_mode = False
        self._load_settings()
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
        self._is_spectating = False
        self._spectate_perspective = 0
        self._surrender_pending = False
        self._reconnecting = False
        self._reconnect_pending = False
        self._conn_gen = 0
        self._build_ui()

    def connect_and_login(self, host: str, port: int, nickname: str):
        self._clear_content()
        self._update_status(t('connecting'))
        tk.Label(self.content_frame, text=t('connecting'),
                 font=_font(_f, 18), bg=COLORS['bg_page'],
                 fg=COLORS['magic']).pack(expand=True)
        self.root.update()
        self._running = True
        self.phase = 'connecting'
        self._conn_gen += 1
        conn_gen = self._conn_gen

        def _do_connect():
            try:
                sock = connect_to_server(host, port)
                self.conn = NetworkConnection(sock)
                self.nickname = nickname
                login_data = {'nickname': nickname}
                try:
                    from mod_loader import get_mods_summary
                    login_data['mods'] = get_mods_summary()
                except Exception:
                    login_data['mods'] = {'hash': '', 'mods': [], 'count': 0}
                self.conn.send(NetworkMessage('login', login_data))
                recv_thread = threading.Thread(target=self._recv_loop, args=(conn_gen,), daemon=True)
                recv_thread.start()
            except Exception as e:
                self.root.after(0, self._on_connect_fail, str(e))

        threading.Thread(target=_do_connect, daemon=True).start()

    def _on_connect_fail(self, error_msg: str):
        self._clear_content()
        self._update_status(t('connect_failed', error=''))
        tk.Label(self.content_frame, text=t('connect_failed', error=error_msg),
                 font=_font(_f, 16), bg=COLORS['bg_page'],
                 fg=COLORS['damage']).pack(pady=30)
        tk.Button(self.content_frame, text=t('back'), font=_font(_f, 14),
                  command=self._back_to_main_menu, bg=COLORS['armor_bg'],
                  fg=COLORS['armor_text'], width=16, height=2).pack(pady=10)

    def _on_disconnected(self, conn_gen: int = -1):
        if conn_gen >= 0 and conn_gen != self._conn_gen:
            return
        self._running = False
        if self.conn:
            self.conn.close()
            self.conn = None
        self._reconnecting = False
        self._clear_content()
        self._update_status(t('disconnected'))
        tk.Label(self.content_frame, text=t('disconnected'),
                 font=_font(_f, 16), bg=COLORS['bg_page'],
                 fg=COLORS['damage']).pack(pady=30)
        tk.Button(self.content_frame, text=t('back'), font=_font(_f, 14),
                  command=self._back_to_main_menu, bg=COLORS['armor_bg'],
                  fg=COLORS['armor_text'], width=16, height=2).pack(pady=10)

    def _show_login_ui(self):
        self._clear_content()
        self._update_status(t('app_title'))
        self._discovered_servers = {}
        self._discovery_running = False
        frame = tk.Frame(self.content_frame, padx=40, pady=20, bg=COLORS['bg_page'])
        frame.pack(expand=True)
        tk.Label(frame, text="Garden of Thorn", font=_font(_f, 24, True),
                 fg=COLORS['damage'], bg=COLORS['bg_page']).pack(pady=(10, 0))
        tk.Label(frame, text=t('app_title').split()[-1] if current_lang() == 'zh_CN' else '',
                 font=_font(_f, 18),
                 fg=COLORS['text_primary'], bg=COLORS['bg_page']).pack(pady=(0, 5))
        tk.Label(frame, text=t('subtitle'), font=_font(_f, 12),
                 fg=COLORS['text_secondary'], bg=COLORS['bg_page']).pack(pady=5)
        try:
            from mod_loader import GAME_VERSION
            tk.Label(frame, text=GAME_VERSION, font=_font(_f, 9),
                     fg=COLORS['text_secondary'], bg=COLORS['bg_page']).pack(pady=(0, 5))
        except Exception:
            pass
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        nick_frame = tk.Frame(frame, bg=COLORS['bg_page'])
        nick_frame.pack(fill=tk.X, pady=5)
        tk.Label(nick_frame, text=t('nickname'), font=_font(_f, 13),
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
        tk.Label(server_frame, text=t('server'), font=_font(_f, 13),
                 fg=COLORS['text_primary'], bg=COLORS['bg_page']).pack(side=tk.LEFT, padx=5)
        self.ip_entry = tk.Entry(server_frame, font=_font(_f, 13), width=18,
                                 bg=COLORS['bg_card'], fg=COLORS['text_primary'])
        self.ip_entry.insert(0, getattr(self, '_last_server_ip', '127.0.0.1'))
        self.ip_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(server_frame, text=f":{DEFAULT_PORT}", font=_font(_f, 13),
                 fg=COLORS['text_secondary'], bg=COLORS['bg_page']).pack(side=tk.LEFT)
        tk.Button(frame, text=t('enter_lobby'), font=_font(_f, 14),
                  command=self._on_login_connect, width=22, height=2,
                  bg=COLORS['health_bg'], fg=COLORS['health'],
                  relief=tk.RAISED, bd=2).pack(pady=15)
        tk.Button(frame, text=t('settings'), font=_font(_f, 12),
                  command=self._show_settings_ui,
                  bg=COLORS['bg_card'], fg=COLORS['text_secondary'],
                  width=10).pack(pady=5)
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        disc_frame = tk.Frame(frame, bg=COLORS['bg_page'])
        disc_frame.pack(fill=tk.X, pady=5)
        self._scan_btn = tk.Button(disc_frame, text=t('scan_lan'), font=_font(_f, 12),
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
        tk.Label(frame, text=t('scan_hint'),
                 font=_font(_f, 9),
                 fg=COLORS['text_secondary'], bg=COLORS['bg_page']).pack(pady=2)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"
        tk.Label(frame, text=t('local_ip', ip=local_ip),
                 font=_font(_f, 11),
                 fg=COLORS['text_secondary'], bg=COLORS['bg_page']).pack(pady=5)
        tk.Label(frame, text=t('run_server_hint'),
                 font=_font(_f, 10),
                 fg=COLORS['magic_text'], bg=COLORS['bg_page']).pack(pady=3)

    def _start_discovery(self):
        if self._discovery_running:
            return
        self._discovery_running = True
        self._discovered_servers = {}
        self._disc_listbox.delete(0, tk.END)
        self._scan_btn.config(state=tk.DISABLED)
        self._disc_status.config(text=t('scanning'))
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
            text=t('scan_complete', count=len(self._discovered_servers))))

    def _update_discovery_list(self):
        self._disc_listbox.delete(0, tk.END)
        for key, srv in self._discovered_servers.items():
            label = f"{srv['ip']}:{srv['port']}  {t('server_info', players=srv['players'], rooms=srv['rooms'])}"
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
            self._show_nick_error(t('enter_nickname'))
            return
        display_width = wcwidth.wcswidth(nickname)
        if display_width < 0 or display_width > 12:
            self._show_nick_error(t('nickname_width_max', width=display_width))
            return
        if '--' in nickname or '__' in nickname:
            self._show_nick_error(t('nickname_no_consecutive'))
            return
        ip = self.ip_entry.get().strip()
        if not ip:
            self._show_nick_error(t('enter_server_ip'))
            return
        self._last_server_ip = ip
        self._running = True
        self.connect_and_login(ip, DEFAULT_PORT, nickname)

    def _back_to_main_menu(self):
        self._running = False
        self._reconnecting = False
        self._reconnect_pending = False
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

    def _recv_loop(self, conn_gen: int = 0):
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
        if self._running and self.phase not in ('connecting',) and conn_gen == self._conn_gen:
            self.root.after(0, self._on_disconnected, conn_gen)

    def _handle_message(self, msg: NetworkMessage):
        try:
            if msg.msg_type == 'login_ok':
                self.player_id = msg.data['player_id']
                self.nickname = msg.data.get('nickname', self.nickname)
                self._save_settings()
                self._update_status(t("lobby_status", name=self.nickname))
            elif msg.msg_type == 'login_fail':
                self._clear_content()
                self._update_status(t('login_failed', reason=''))
                tk.Label(self.content_frame,
                         text=t('login_failed', reason=msg.data.get('reason', t('nickname_invalid'))),
                         font=_font(_f, 16), bg=COLORS['bg_page'],
                         fg=COLORS['damage']).pack(pady=30)
                tk.Button(self.content_frame, text=t('back_to_menu'),
                          font=_font(_f, 14),
                          command=self._back_to_main_menu,
                          bg=COLORS['armor_bg'], fg=COLORS['armor_text'],
                          width=16, height=2).pack(pady=10)
                return
            elif msg.msg_type == 'lobby_update':
                self.lobby_players = msg.data.get('players', [])
                self.player_id = msg.data.get('your_id', self.player_id)
                self.lobby_ongoing_games = msg.data.get('ongoing_games', [])
                if self._reconnecting:
                    my_in_lobby = any(p['player_id'] == self.player_id for p in self.lobby_players)
                    if my_in_lobby:
                        self._reconnecting = False
                        self._reconnect_pending = False
                        messagebox.showinfo(t('notice'), t('reconnect_failed_msg'))
                if not self._reconnecting:
                    self.phase = 'lobby'
                    self._show_lobby_ui()
            elif msg.msg_type == 'invite_received':
                self._show_invite_dialog(msg.data)
            elif msg.msg_type == 'invite_declined':
                messagebox.showinfo(t("notice"), t("invite_declined"))
                self._update_status(t('lobby_status', name=self.nickname))
            elif msg.msg_type == 'opponent_disconnected':
                data = msg.data or {}
                timeout = data.get('timeout', False)
                reconnect_timeout = data.get('reconnect_timeout', 0)
                if timeout:
                    messagebox.showinfo(t('notice'), t('opponent_disconnected'))
                    self._send(NetworkMessage('return_lobby', {}))
                elif reconnect_timeout > 0:
                    self._show_opponent_dc_waiting(data)
                else:
                    messagebox.showinfo(t('notice'), t('opponent_disconnected'))
                    self._send(NetworkMessage('return_lobby', {}))
            elif msg.msg_type == 'chat':
                self._on_chat_received(msg.data)
            elif msg.msg_type == 'opponent_reconnected':
                if hasattr(self, '_dc_wait_window') and self._dc_wait_window:
                    try:
                        self._dc_wait_window.destroy()
                    except Exception:
                        pass
                    self._dc_wait_window = None
                messagebox.showinfo(t('notice'), t('opponent_reconnected'))
            elif msg.msg_type == 'reconnect_available':
                self._show_reconnect_prompt(msg.data)
            elif msg.msg_type == 'reconnect_timeout':
                self._reconnecting = False
                self._reconnect_pending = False
                self._clear_content()
                messagebox.showinfo(t('notice'), t('reconnect_timeout_msg'))
                self.phase = 'lobby'
                self._show_lobby_ui()
            elif msg.msg_type == 'mod_mismatch':
                your = msg.data.get('your_mods', '?')
                opp = msg.data.get('opponent_mods', '?')
                messagebox.showerror(t('mod_mismatch_title'),
                                     t('mod_mismatch_msg', your=your, opponent=opp))
            elif msg.msg_type == 'game_phase':
                self.phase = msg.data.get('phase', '')
                self._reconnecting = False
                print(f"[客户端] 收到 game_phase: {self.phase}")
                if self.phase == 'draft':
                    self._show_draft_ui()
                elif self.phase == 'event_select':
                    self._clear_content()
                    self._update_status(t("select_event"))
                else:
                    self._clear_content()
                    self._update_status(t("game_loading"))
            elif msg.msg_type == 'event_select':
                self.phase = 'event_select'
                self.event_select_data = msg.data
                self._show_event_select_ui()
            elif msg.msg_type == 'draft_state':
                self.draft_state = msg.data
                self._update_draft_ui()
            elif msg.msg_type == 'state_update':
                print(f"[客户端] 收到 state_update, phase={msg.data.get('phase', '?')}")
                self.game_state = msg.data
                self.phase = msg.data.get('phase', '')
                self._reconnecting = False
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
                self._update_status(t("error_msg", msg=msg.data.get("message", "")))
                if self._pending_play_card:
                    self._clear_pending_card()
            elif msg.msg_type == 'server_broadcast':
                self._update_status(t("server_broadcast", msg=msg.data.get("message", "")))
            elif msg.msg_type == 'rematch_requested':
                self._rematch_pending = True
                self._show_rematch_request(msg.data)
            elif msg.msg_type == 'spectate_enter':
                self._is_spectating = True
                self._spectate_perspective = 0
                self.phase = 'playing'
                self._build_game_ui()
            elif msg.msg_type == 'spectate_leave':
                self._is_spectating = False
                self._spectate_perspective = 0
                self.phase = 'lobby'
                self._show_lobby_ui()
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
            try:
                self.conn.send(msg)
            except Exception as e:
                print(f"[客户端] 发送异常: {e}")
        else:
            print(f"[客户端] 无法发送 {msg.msg_type}: conn={self.conn is not None}, connected={self.conn.connected if self.conn else 'N/A'}")

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
        self.status_label = tk.Label(self.main_frame, text=t('app_title'),
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
        self._update_status(t('lobby_status', name=self.nickname))
        frame = tk.Frame(self.content_frame, bg=COLORS['bg_page'], padx=40, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(frame, text=t('online_players'), font=_font(_f, 16, True),
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
            tk.Label(inner, text=t('no_other_players'),
                     font=_font(_f, 12), fg=COLORS['text_secondary'],
                     bg=COLORS['bg_card']).pack(pady=20, padx=40)
        for p in others:
            row = tk.Frame(inner, bg=COLORS['bg_card'])
            row.pack(fill=tk.X, padx=10, pady=4)
            tk.Label(row, text=p['nickname'], font=_font(_f, 13),
                     fg=COLORS['text_primary'], bg=COLORS['bg_card']).pack(side=tk.LEFT, padx=10)
            tk.Button(row, text=t('invite'), font=_font(_f, 11),
                      bg=COLORS['bloom_bg'], fg=COLORS['bloom'],
                      command=lambda pid=p['player_id']: self._on_invite(pid)).pack(side=tk.RIGHT, padx=10)
        tk.Label(frame, text=t('online_count', count=len(self.lobby_players)),
                 font=_font(_f, 11), fg=COLORS['text_secondary'],
                 bg=COLORS['bg_page']).pack(pady=10)

        ongoing = getattr(self, 'lobby_ongoing_games', [])
        if ongoing:
            tk.Label(frame, text=t('ongoing_games'), font=_font(_f, 16, True),
                     fg=COLORS['damage'], bg=COLORS['bg_page']).pack(pady=(15, 5))
            games_frame = tk.Frame(frame, bg=COLORS['bg_card'], relief=tk.SUNKEN, bd=1)
            games_frame.pack(fill=tk.X, pady=5)
            for g in ongoing:
                row = tk.Frame(games_frame, bg=COLORS['bg_card'])
                row.pack(fill=tk.X, padx=10, pady=4)
                tk.Label(row, text=t('game_vs', p1=g['player1'], p2=g['player2'], round=g['round']),
                         font=_font(_f, 12), fg=COLORS['text_primary'],
                         bg=COLORS['bg_card']).pack(side=tk.LEFT, padx=10)
                tk.Button(row, text=t('spectate'), font=_font(_f, 11),
                          bg=COLORS['magic_bg'], fg=COLORS['magic_text'],
                          command=lambda rid=g['room_id']: self._on_spectate(rid)).pack(side=tk.RIGHT, padx=10)

        tk.Button(frame, text=t('back_to_main'), font=_font(_f, 12),
                  bg=COLORS['armor_bg'], fg=COLORS['armor_text'],
                  command=self._back_to_login, width=14).pack(pady=10)

    def _on_invite(self, target_id: int):
        self._send(NetworkMessage('invite', {'target_id': target_id}))
        self._update_status(t('invite_sent'))

    def _on_spectate(self, room_id):
        self._send(NetworkMessage('spectate', {'room_id': room_id}))
        self._update_status(t('entering_spectate'))

    def _on_switch_perspective(self):
        self._spectate_perspective = 1 - self._spectate_perspective
        self._send(NetworkMessage('switch_spectate_perspective', {}))

    def _on_leave_spectate(self):
        self._send(NetworkMessage('leave_spectate', {}))

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
        self._reconnecting = False
        self._reconnect_pending = False
        self._show_login_ui()

    def _load_settings(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\GardenOfThorn', 0, winreg.KEY_READ)
            lang = winreg.QueryValueEx(key, 'Language')[0]
            dark = winreg.QueryValueEx(key, 'DarkMode')[0]
            try:
                self.nickname = winreg.QueryValueEx(key, 'Nickname')[0]
            except Exception:
                pass
            try:
                self._last_server_ip = winreg.QueryValueEx(key, 'LastServerIP')[0]
            except Exception:
                self._last_server_ip = '127.0.0.1'
            winreg.CloseKey(key)
            load_lang(lang)
            self._dark_mode = bool(dark)
        except Exception:
            load_lang('zh_CN')
            self._dark_mode = False
            self._last_server_ip = '127.0.0.1'
        self._apply_theme()

    def _save_settings(self):
        try:
            import winreg
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\GardenOfThorn')
            winreg.SetValueEx(key, 'Language', 0, winreg.REG_SZ, current_lang())
            winreg.SetValueEx(key, 'DarkMode', 0, winreg.REG_DWORD, int(self._dark_mode))
            if self.nickname:
                winreg.SetValueEx(key, 'Nickname', 0, winreg.REG_SZ, self.nickname)
            if hasattr(self, '_last_server_ip') and self._last_server_ip:
                winreg.SetValueEx(key, 'LastServerIP', 0, winreg.REG_SZ, self._last_server_ip)
            winreg.CloseKey(key)
        except Exception:
            pass

    def _apply_theme(self):
        global COLORS
        if self._dark_mode:
            COLORS.update({
                'bg_page': '#1a1a2e', 'bg_card': '#16213e', 'text_primary': '#e0e0e0',
                'text_secondary': '#a0a0a0', 'health': '#ff6b6b', 'health_bg': '#2d1f1f',
                'health_text': '#ff6b6b', 'elixir': '#ffd93d', 'elixir_bg': '#2d2d1f',
                'elixir_text': '#ffd93d', 'magic': '#6c5ce7', 'magic_bg': '#1f1f2d',
                'magic_text': '#a29bfe', 'damage': '#ff4757', 'damage_bg': '#2d1f1f',
                'heal_text': '#2ed573', 'poison': '#a29bfe', 'poison_bg': '#1f1f2d',
                'fire': '#ff6348', 'fire_bg': '#2d1f1f', 'armor': '#747d8c',
                'armor_bg': '#2d2d2d', 'armor_text': '#a0a0a0', 'bloom': '#7bed9f',
                'bloom_bg': '#1f2d1f', 'guard': '#70a1ff', 'guard_bg': '#1f1f2d',
                'precise': '#ff6348', 'precise_bg': '#2d1f1f', 'banish': '#a29bfe',
                'banish_bg': '#1f1f2d', 'non_stack': '#ffa502', 'non_stack_bg': '#2d2d1f',
                'indestructible': '#747d8c', 'indestructible_bg': '#2d2d2d',
                'vulnus': '#ff6b6b', 'vulnus_bg': '#2d1f1f', 'border_color': '#3d3d5c',
            })
        else:
            COLORS.update({
                'bg_page': '#F5F5F0', 'bg_card': '#FFFFFF', 'text_primary': '#2C3E50',
                'text_secondary': '#7F8C8D', 'health': '#2ECC71', 'health_bg': '#E8F8F5',
                'health_text': '#1E8449', 'elixir': '#F1C40F', 'elixir_bg': '#FEF9E7',
                'elixir_text': '#9A7D0A', 'magic': '#3498DB', 'magic_bg': '#EBF5FB',
                'magic_text': '#1A5276', 'damage': '#C0392B', 'damage_bg': '#FDEDEC',
                'heal_text': '#C2185B', 'poison': '#8E44AD', 'poison_bg': '#F4ECF7',
                'fire': '#E67E22', 'fire_bg': '#FEF5E7', 'armor': '#95A5A6',
                'armor_bg': '#F2F3F4', 'armor_text': '#515A5A', 'bloom': '#1ABC9C',
                'bloom_bg': '#E8F8F5', 'guard': '#2980B9', 'guard_bg': '#EBF5FB',
                'precise': '#546E7A', 'precise_bg': '#ECEFF1', 'banish': '#6C3483',
                'banish_bg': '#F4ECF7', 'non_stack': '#34495E', 'non_stack_bg': '#EAECEE',
                'indestructible': '#D4AC0D', 'indestructible_bg': '#FEF9E7',
                'vulnus': '#7B241C', 'vulnus_bg': '#FDEDEC', 'border_color': '#DCDCDC',
            })

    def _show_settings_ui(self):
        dialog = tk.Toplevel(self.root)
        dialog.title(t('settings'))
        dialog.geometry(f"{int(400*SCALE)}x{int(350*SCALE)}")
        dialog.configure(bg=COLORS['bg_page'])
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text=t('settings'), font=_font(_f, 18, True),
                 fg=COLORS['text_primary'], bg=COLORS['bg_page']).pack(pady=(15, 10))

        lang_frame = tk.Frame(dialog, bg=COLORS['bg_page'])
        lang_frame.pack(fill=tk.X, padx=20, pady=10)
        tk.Label(lang_frame, text=t('language'), font=_font(_f, 13),
                 fg=COLORS['text_primary'], bg=COLORS['bg_page']).pack(side=tk.LEFT, padx=5)
        lang_var = tk.StringVar(value=current_lang())
        lang_options = get_available_langs()
        lang_display = [get_lang_display_name(l) for l in lang_options]
        lang_menu = ttk.Combobox(lang_frame, textvariable=lang_var,
                                  values=lang_options, state='readonly', width=15)
        lang_menu.pack(side=tk.RIGHT, padx=5)

        theme_frame = tk.Frame(dialog, bg=COLORS['bg_page'])
        theme_frame.pack(fill=tk.X, padx=20, pady=10)
        tk.Label(theme_frame, text=t('theme'), font=_font(_f, 13),
                 fg=COLORS['text_primary'], bg=COLORS['bg_page']).pack(side=tk.LEFT, padx=5)
        theme_var = tk.BooleanVar(value=self._dark_mode)
        theme_text = tk.StringVar(value=t('dark_mode') if self._dark_mode else t('light_mode'))

        def toggle_theme():
            self._dark_mode = theme_var.get()
            theme_text.set(t('dark_mode') if self._dark_mode else t('light_mode'))

        tk.Checkbutton(theme_frame, variable=theme_var, command=toggle_theme,
                       textvariable=theme_text, font=_font(_f, 12),
                       fg=COLORS['text_primary'], bg=COLORS['bg_page'],
                       selectcolor=COLORS['bg_card'], activebackground=COLORS['bg_page']).pack(side=tk.RIGHT, padx=5)

        mod_frame = tk.LabelFrame(dialog, text=t('mods'), font=_font(_f, 12, True),
                                   fg=COLORS['text_primary'], bg=COLORS['bg_page'],
                                   labelanchor='n')
        mod_frame.pack(fill=tk.X, padx=20, pady=10)

        mod_list_frame = tk.Frame(mod_frame, bg=COLORS['bg_page'])
        mod_list_frame.pack(fill=tk.X, padx=5, pady=5)

        mod_vars = {}
        try:
            from mod_loader import load_all_mods, check_conflicts
            all_mods = load_all_mods()
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\GardenOfThorn', 0, winreg.KEY_READ)
                disabled_str = winreg.QueryValueEx(key, 'DisabledMods')[0]
                winreg.CloseKey(key)
                disabled_set = set(disabled_str.split(',')) if disabled_str else set()
            except Exception:
                disabled_set = set()
            for mod in all_mods:
                mod_name = mod.info.name if mod.info else mod.filename
                v = tk.BooleanVar(value=mod.filename not in disabled_set and not mod.errors)
                mod_vars[mod.filename] = v
                err_text = f" ({t('mod_errors', count=len(mod.errors))})" if mod.errors else ""
                tk.Checkbutton(mod_list_frame, text=f"{mod_name}{err_text}",
                               variable=v, font=_font(_f, 10),
                               fg=COLORS['damage'] if mod.errors else COLORS['text_primary'],
                               bg=COLORS['bg_page'], selectcolor=COLORS['bg_card'],
                               activebackground=COLORS['bg_page']).pack(anchor='w')
            if not all_mods:
                tk.Label(mod_list_frame, text=t('no_mods'), font=_font(_f, 10),
                         fg=COLORS['text_secondary'], bg=COLORS['bg_page']).pack()
        except Exception:
            tk.Label(mod_list_frame, text=t('no_mods'), font=_font(_f, 10),
                     fg=COLORS['text_secondary'], bg=COLORS['bg_page']).pack()

        def on_apply():
            new_lang = lang_var.get()
            if new_lang != current_lang():
                load_lang(new_lang)
            self._dark_mode = theme_var.get()
            disabled_list = [fname for fname, v in mod_vars.items() if not v.get()]
            try:
                import winreg
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\GardenOfThorn')
                winreg.SetValueEx(key, 'DisabledMods', 0, winreg.REG_SZ, ','.join(disabled_list))
                winreg.CloseKey(key)
            except Exception:
                pass
            self._apply_theme()
            self._save_settings()
            dialog.destroy()
            self._show_login_ui()

        def on_cancel():
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=COLORS['bg_page'])
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=15)
        tk.Button(btn_frame, text=t('cancel'), command=on_cancel,
                  font=_font(_f, 12), bg=COLORS['bg_card'],
                  fg=COLORS['text_secondary'], width=8).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text=t('ok'), command=on_apply,
                  font=_font(_f, 12), bg=COLORS['health_bg'],
                  fg=COLORS['health'], width=8).pack(side=tk.RIGHT, padx=10)

    def _show_invite_dialog(self, data: dict):
        inviter_name = data.get('inviter_name', '?')
        inviter_id = data.get('inviter_id', -1)
        if hasattr(self, '_pending_invite_id') and self._pending_invite_id == inviter_id:
            return
        self._pending_invite_id = inviter_id
        result = messagebox.askyesno(t('invite_received'),
                                     t('invite_message', name=inviter_name))
        self._pending_invite_id = None
        if result:
            self._send(NetworkMessage('accept_invite', {'inviter_id': inviter_id}))
        else:
            self._send(NetworkMessage('decline_invite', {'inviter_id': inviter_id}))

    def _show_reconnect_prompt(self, data: dict):
        room_id = data.get('room_id')
        old_pid = data.get('old_pid')
        opp_name = data.get('opponent_nickname', '?')
        print(f"[客户端] 收到重连提示: room_id={room_id}, old_pid={old_pid}, opponent={opp_name}")
        if self._reconnect_pending:
            return
        self._reconnect_pending = True
        result = messagebox.askyesno(t('reconnect_title'),
                                     t('reconnect_prompt', opponent=opp_name))
        self._reconnect_pending = False
        print(f"[客户端] 用户选择: {result}")
        if result:
            self._reconnecting = True
            self._clear_content()
            self._update_status(t('reconnecting'))
            tk.Label(self.content_frame, text=t('reconnecting'),
                     font=_font(_f, 18), bg=COLORS['bg_page'],
                     fg=COLORS['magic']).pack(expand=True)
            self._send(NetworkMessage('reconnect_accept', {
                'room_id': room_id, 'old_pid': old_pid}))
            print(f"[客户端] 已发送 reconnect_accept")
        else:
            self._send(NetworkMessage('reconnect_decline', {
                'room_id': room_id, 'old_pid': old_pid}))

    def _show_opponent_dc_waiting(self, data: dict):
        timeout = data.get('reconnect_timeout', 120)
        opp_name = data.get('opponent_nickname', '?')
        self._dc_wait_window = tk.Toplevel(self.root)
        self._dc_wait_window.title(t('opponent_dc_title'))
        self._dc_wait_window.geometry('350x150')
        self._dc_wait_window.resizable(False, False)
        self._dc_wait_window.configure(bg=COLORS['bg_page'])
        self._dc_wait_window.transient(self.root)
        self._dc_wait_window.grab_set()
        lbl = tk.Label(self._dc_wait_window,
                       text=t('opponent_dc_waiting', name=opp_name, time=timeout),
                       font=_font(_f, 14), bg=COLORS['bg_page'],
                       fg=COLORS['text_primary'], wraplength=320)
        lbl.pack(pady=30)
        remaining = [timeout]
        def tick():
            if self._dc_wait_window is None or not self._dc_wait_window.winfo_exists():
                return
            remaining[0] -= 1
            if remaining[0] <= 0:
                try:
                    self._dc_wait_window.destroy()
                except Exception:
                    pass
                self._dc_wait_window = None
                return
            try:
                lbl.config(text=t('opponent_dc_waiting', name=opp_name, time=remaining[0]))
            except Exception:
                return
            self._dc_wait_window.after(1000, tick)
        self._dc_wait_window.after(1000, tick)

    def _make_bar(self, parent, label, color, bg_color):
        f = tk.Frame(parent, bg=COLORS['bg_page'])
        f.pack(side=tk.LEFT, padx=4)
        tk.Label(f, text=label, font=_font(_f, 10, True),
                 fg=color, bg=COLORS['bg_page']).pack(side=tk.LEFT)
        c = tk.Canvas(f, width=BAR_W(), height=BAR_H(), bg=bg_color,
                      highlightthickness=1, highlightbackground=COLORS['border_color'])
        c.pack(side=tk.LEFT, padx=2)
        bar = c.create_rectangle(1, 1, BAR_W(), BAR_H(), fill=color, outline='')
        txt_black = c.create_text(BAR_W() // 2, BAR_H() // 2, text="", font=_font(_f, 9, True), fill='black')
        txt_white = c.create_text(BAR_W() // 2, BAR_H() // 2, text="", font=_font(_f, 9, True), fill='white')
        return c, bar, txt_black, txt_white

    def _update_bar(self, canvas, bar, txt_black, txt_white, cur, mx):
        ratio = max(0, min(1, cur / mx)) if mx > 0 else 0
        fill_w = max(1, int(BAR_W() * ratio))
        canvas.coords(bar, 1, 1, fill_w, BAR_H())
        text_str = f"{cur}/{mx}"
        cx, cy = BAR_W() // 2, BAR_H() // 2
        canvas.itemconfig(txt_black, text=text_str)
        canvas.itemconfig(txt_white, text=text_str)
        canvas.coords(txt_black, cx, cy)
        canvas.coords(txt_white, cx, cy)
        canvas.delete('bar_clip')
        canvas.tag_raise(txt_white, bar)
        if fill_w < BAR_W() - 1:
            clip = canvas.create_rectangle(fill_w, 0, BAR_W(), BAR_H(),
                                           fill=canvas['bg'], outline='', tags='bar_clip')
            canvas.tag_raise(clip, txt_white)
            canvas.tag_raise(txt_black, clip)

    def _build_game_ui(self):
        self._clear_content()
        self.game_frame = tk.Frame(self.content_frame, bg=COLORS['bg_page'])
        self.game_frame.pack(fill=tk.BOTH, expand=True)
        gs = self.game_state or {}
        opp_name = gs.get('opponent_name', t('opponent'))
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
        log_frame = tk.LabelFrame(self.game_frame, text=t('battle_log'),
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
        self.log_text.tag_configure('chat', foreground='#88CCFF',
                                    font=_font(_f, 9))
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
        self.play_zone_label = tk.Label(self.play_zone, text=t("drag_to_play"),
                                        font=_font(_f, 12, True),
                                        fg=COLORS['text_secondary'], bg=COLORS['bg_page'])
        self.play_zone_label.pack(expand=True)
        btn_frame = tk.Frame(you_frame, bg=COLORS['bg_page'])
        btn_frame.pack(fill=tk.X, padx=8, pady=3)
        self.end_turn_btn = tk.Button(btn_frame, text=t('end_turn'),
                                      font=_font(_f, 13, True),
                                      command=self._on_end_turn, state=tk.DISABLED,
                                      bg=COLORS['damage_bg'], fg=COLORS['damage'],
                                      width=14)
        self.end_turn_btn.pack(side=tk.LEFT, padx=8)
        tk.Button(btn_frame, text=t('view_deck'), font=_font(_f, 11),
                  command=self._view_deck, bg=COLORS['magic_bg'], fg=COLORS['magic_text'],
                  width=10).pack(side=tk.LEFT, padx=4)
        self.surrender_btn = tk.Button(btn_frame, text=t('surrender'), font=_font(_f, 11),
                                       command=self._on_surrender,
                                       bg=COLORS['bg_card'], fg=COLORS['text_secondary'],
                                       width=6)
        self.surrender_btn.pack(side=tk.LEFT, padx=4)
        chat_frame = tk.Frame(btn_frame, bg=COLORS['bg_page'])
        chat_frame.pack(side=tk.RIGHT, padx=4)
        self.chat_entry = tk.Entry(chat_frame, font=_font(_f, 10), width=20,
                                   bg=COLORS['bg_card'], fg=COLORS['text_primary'])
        self.chat_entry.pack(side=tk.LEFT, padx=2)
        self.chat_entry.bind('<Return>', self._on_chat_send)
        tk.Button(chat_frame, text=t('send'), font=_font(_f, 10),
                  command=lambda: self._on_chat_send(None),
                  bg=COLORS['magic_bg'], fg=COLORS['magic_text'],
                  width=4).pack(side=tk.LEFT, padx=2)
        self.switch_perspective_btn = tk.Button(btn_frame, text=t('switch_perspective'), font=_font(_f, 11),
                                                 command=self._on_switch_perspective,
                                                 bg=COLORS['magic_bg'], fg=COLORS['magic_text'],
                                                 width=10)
        self.leave_spectate_btn = tk.Button(btn_frame, text=t('leave_spectate'), font=_font(_f, 11),
                                             command=self._on_leave_spectate,
                                             bg=COLORS['damage_bg'], fg=COLORS['damage'],
                                             width=10)
        self.response_frame = tk.Frame(self.game_frame, bg=COLORS['bg_page'])
        self.response_frame.pack(fill=tk.X, padx=10, pady=3)
        self.opp_h_canvas, self.opp_h_bar, self.opp_h_txt_b, self.opp_h_txt_w = self._make_bar(self.opp_panel, 'H', COLORS['health'], COLORS['health_bg'])
        self.opp_e_canvas, self.opp_e_bar, self.opp_e_txt_b, self.opp_e_txt_w = self._make_bar(self.opp_panel, 'E', COLORS['elixir'], COLORS['elixir_bg'])
        self.opp_m_canvas, self.opp_m_bar, self.opp_m_txt_b, self.opp_m_txt_w = self._make_bar(self.opp_panel, 'M', COLORS['magic'], COLORS['magic_bg'])
        self.opp_status_frame = tk.Frame(self.opp_panel, bg=COLORS['bg_page'])
        self.opp_status_frame.pack(side=tk.LEFT, padx=8)
        self.opp_info_label = tk.Label(self.opp_panel, text="", font=_font(_f, 10),
                                       fg=COLORS['text_secondary'], bg=COLORS['bg_page'])
        self.opp_info_label.pack(side=tk.RIGHT, padx=4)
        self.you_h_canvas, self.you_h_bar, self.you_h_txt_b, self.you_h_txt_w = self._make_bar(self.you_panel, 'H', COLORS['health'], COLORS['health_bg'])
        self.you_e_canvas, self.you_e_bar, self.you_e_txt_b, self.you_e_txt_w = self._make_bar(self.you_panel, 'E', COLORS['elixir'], COLORS['elixir_bg'])
        self.you_m_canvas, self.you_m_bar, self.you_m_txt_b, self.you_m_txt_w = self._make_bar(self.you_panel, 'M', COLORS['magic'], COLORS['magic_bg'])
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
            self._update_bar(self.opp_h_canvas, self.opp_h_bar, self.opp_h_txt_b, self.opp_h_txt_w,
                             opp.get('health', 0), opp.get('max_health', 100))
            self._update_bar(self.opp_e_canvas, self.opp_e_bar, self.opp_e_txt_b, self.opp_e_txt_w,
                             opp.get('elixir', 0), opp.get('max_elixir', 10))
            self._update_bar(self.opp_m_canvas, self.opp_m_bar, self.opp_m_txt_b, self.opp_m_txt_w,
                             opp.get('magic', 0), opp.get('max_magic', 10))
            self._update_status_tags(self.opp_status_frame, opp)
            self.opp_info_label.config(text=t('hand_deck_info_opp', hand=opp.get('hand_count', 0), deck=opp.get('deck_count', 0)))
        except Exception:
            pass
        try:
            self._update_bar(self.you_h_canvas, self.you_h_bar, self.you_h_txt_b, self.you_h_txt_w,
                             you.get('health', 0), you.get('max_health', 100))
            self._update_bar(self.you_e_canvas, self.you_e_bar, self.you_e_txt_b, self.you_e_txt_w,
                             you.get('elixir', 0), you.get('max_elixir', 10))
            self._update_bar(self.you_m_canvas, self.you_m_bar, self.you_m_txt_b, self.you_m_txt_w,
                             you.get('magic', 0), you.get('max_magic', 10))
            self._update_status_tags(self.you_status_frame, you)
            self.you_info_label.config(text=t('hand_deck_discard_info', hand=you.get('hand_count', 0), deck=you.get('deck_count', 0), discard=you.get('discard_count', 0)))
        except Exception:
            pass
        try:
            revealed_hand = opp.get('revealed_hand', None)
            self._update_opp_hand(opp.get('hand_count', 0), revealed_hand)
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
            is_spectating = self._is_spectating
            if is_spectating:
                self.end_turn_btn.pack_forget()
                self.surrender_btn.pack_forget()
                self.switch_perspective_btn.pack(side=tk.LEFT, padx=4)
                self.leave_spectate_btn.pack(side=tk.LEFT, padx=4)
                self.play_zone.pack_forget()
                perspective = gs.get('spectate_perspective', 0)
                p1_name = gs.get('player1_name', t('player1'))
                p2_name = gs.get('player2_name', t('player2'))
                self.switch_perspective_btn.config(
                    text=t('switch_to_perspective', name=p2_name if perspective == 0 else p1_name))
            else:
                self.end_turn_btn.config(state=tk.NORMAL if is_my_turn else tk.DISABLED)
                self.end_turn_btn.pack(side=tk.LEFT, padx=8)
                self.surrender_btn.pack(side=tk.LEFT, padx=4)
                self.switch_perspective_btn.pack_forget()
                self.leave_spectate_btn.pack_forget()
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
            turn_text = t('your_turn') if is_my_turn else t('opponent_turn')
        elif phase == 'draw':
            turn_text = t('draw_phase')
        elif phase == 'game_over':
            turn_text = t('game_over')
        else:
            turn_text = t('waiting')
        self._update_status(t('round_status', round=gs.get('round_num', 0), status=turn_text))

    def _update_status_tags(self, frame, player_data):
        for w in frame.winfo_children():
            w.destroy()
        tags = []
        p = player_data.get('poison', 0)
        f = player_data.get('fire', 0)
        tri = player_data.get('triangle_stacks', 0)
        d = player_data.get('dodge', 0)
        n = player_data.get('nazar_active', False)
        n_hits = player_data.get('nazar_big_hits', 0)
        inv = player_data.get('invincible', False)
        sk = player_data.get('skip_turn', False)
        ep = player_data.get('equipment_protection', 0)
        tx = player_data.get('toxic', 0)
        ab = player_data.get('attack_blocked', 0)
        ao = player_data.get('attack_only', 0)
        ut = player_data.get('untargetable', False)
        ba = player_data.get('bandage_active', False)
        sa = player_data.get('sponge_active', False)
        sha = player_data.get('shovel_active', False)
        if p > 0: tags.append((t('status_poison'), str(p), COLORS['poison'], COLORS['poison_bg']))
        if f > 0: tags.append((t('status_fire'), str(f), COLORS['fire'], COLORS['fire_bg']))
        if tx > 0: tags.append((t('status_toxic'), str(tx), '#8e44ad', '#6c3483'))
        if tri > 0: tags.append((t('status_triangle'), str(tri), COLORS['non_stack'], COLORS['non_stack_bg']))
        if d > 0: tags.append((t('status_dodge'), str(d), COLORS['guard'], COLORS['guard_bg']))
        if n: tags.append((t('status_nazar'), f'{n_hits}/2', COLORS['magic'], COLORS['magic_bg']))
        if ep > 0: tags.append((t('status_equip_protect'), str(ep), COLORS['indestructible'], COLORS['indestructible_bg']))
        if inv: tags.append((t('status_invincible'), '', COLORS['elixir'], COLORS['elixir_bg']))
        if sk: tags.append((t('status_stunned'), '', COLORS['damage'], COLORS['damage_bg']))
        if ab > 0: tags.append((t('status_attack_blocked'), str(ab), '#e74c3c', '#c0392b'))
        if ao > 0: tags.append((t('status_attack_only'), str(ao), '#e67e22', '#d35400'))
        if ut: tags.append((t('status_untargetable'), '', '#3498db', '#2980b9'))
        if ba: tags.append((t('status_bandage'), '', '#2ecc71', '#27ae60'))
        if sa: tags.append((t('status_sponge'), '', '#9b59b6', '#8e44ad'))
        if sha: tags.append((t('status_shovel'), '', '#7f8c8d', '#6c7a7d'))
        for name, val, fg, bg in tags:
            text = f"{name}:{val}" if val else name
            tk.Label(frame, text=text, font=_font(_f, 9),
                     fg=fg, bg=bg, padx=3, pady=1, relief=tk.GROOVE).pack(side=tk.LEFT, padx=2)

    def _update_opp_hand(self, count, revealed_hand=None):
        for w in self.opp_hand_frame.winfo_children():
            w.destroy()
        if revealed_hand:
            for card_data in revealed_hand:
                def_id = card_data.get('def_id', '')
                card_def = CARD_DEFS.get(def_id, CardDef('', '', '', 0, 0, '', 0, '', '', ''))
                f = tk.Frame(self.opp_hand_frame, bg=COLORS['bg_card'],
                             width=CARD_BACK_W(), height=CARD_BACK_H(),
                             relief=tk.FLAT, bd=0,
                             highlightbackground=COLORS['border_color'], highlightthickness=1)
                f.pack(side=tk.LEFT, padx=_p(3), pady=_p(2))
                f.pack_propagate(False)
                tk.Label(f, text=card_def.display_name[:4], font=_font(_fc, 9, True),
                         fg=COLORS['text_primary'], bg=COLORS['bg_card']).pack(expand=True)
        else:
            for _ in range(count):
                f = tk.Frame(self.opp_hand_frame, bg=COLORS['armor_bg'],
                             width=CARD_BACK_W(), height=CARD_BACK_H(),
                             relief=tk.FLAT, bd=0,
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
                if 'symbiosis' in card.flags:
                    dup = 0
                total_e = card.cost_e + dup
                total_m = card.cost_m
                type_str = {'thorn': 'Thorn', 'bloom': 'Bloom', 'root': 'Root', 'guard': 'Guard'}.get(card.card_type, '?')
                type_color = CARD_TYPE_COLORS.get(card.card_type, COLORS['text_primary'])
                cf = tk.Frame(self.hand_frame, bg=COLORS['bg_card'], width=CARD_W(), height=CARD_H(),
                              relief=tk.FLAT, bd=0,
                              highlightbackground=type_color, highlightthickness=1)
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
                tk.Label(cf, text=f"{card_def.display_name}", font=_font(_fc, 10, True),
                         fg=type_color, bg=COLORS['bg_card']).pack(pady=(_p(1), 0))
                tk.Label(cf, text=f"[{type_str}]", font=_font(_fc, 8),
                         fg=type_color, bg=COLORS['bg_card']).pack()
                tk.Label(cf, text=card_def.effect_text, font=_font(_fc, 7),
                         fg=COLORS['text_secondary'], bg=COLORS['bg_card'],
                         wraplength=CARD_W() - _p(6)).pack(pady=(0, _p(2)))
                _cf = get_card_flags()
                flags_to_show = [f for f in card.flags if f in _cf]
                if flags_to_show:
                    flags_frame = tk.Frame(cf, bg=COLORS['bg_card'])
                    flags_frame.pack(pady=(0, _p(2)))
                    for flag in flags_to_show:
                        label, fg_color, bg_color = _cf[flag]
                        tk.Label(flags_frame, text=label, font=_font(_fc, 7),
                                 fg=fg_color, bg=bg_color, relief=tk.GROOVE, bd=1,
                                 padx=_p(2)).pack(side=tk.LEFT, padx=_p(1))
                if is_my_turn and card.card_type != 'guard':
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
                    if card.card_type == 'guard':
                        cf.configure(highlightbackground=COLORS['text_secondary'])
            except Exception as ex:
                print(f"渲染手牌错误: {ex}, card_dict={card_dict}")
                continue

    def _on_card_press(self, event, card_id, drag_data):
        if self._is_spectating:
            return
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
            type_str = {'thorn': 'Thorn', 'bloom': 'Bloom', 'root': 'Root', 'guard': 'Guard'}.get(card_def.card_type, '?')
            gf = tk.Frame(self._ghost, bg=COLORS['bg_card'], width=CARD_W(), height=CARD_H(),
                          relief=tk.FLAT, bd=0,
                          highlightbackground=type_color, highlightthickness=1)
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
            tk.Label(gf, text=card_def.display_name, font=_font(_fc, 10, True),
                     fg=type_color, bg=COLORS['bg_card']).pack(pady=(_p(1), 0))
            tk.Label(gf, text=f"[{type_str}]", font=_font(_fc, 8),
                     fg=type_color, bg=COLORS['bg_card']).pack()
            tk.Label(gf, text=card_def.effect_text, font=_font(_fc, 7),
                     fg=COLORS['text_secondary'], bg=COLORS['bg_card'],
                     wraplength=CARD_W() - _p(6)).pack(pady=(0, _p(2)))
            _cf = get_card_flags()
            flags_to_show = [f for f in card.flags if f in _cf]
            if flags_to_show:
                flags_frame = tk.Frame(gf, bg=COLORS['bg_card'])
                flags_frame.pack(pady=(0, _p(2)))
                for flag in flags_to_show:
                    label, fg_color, bg_color = _cf[flag]
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
        if you.get('shovel_active', False):
            return False
        card = CardInstance.from_dict(card_dict)
        if card.card_type == 'guard':
            return False
        if you.get('attack_blocked', 0) > 0 and card.card_type == 'thorn':
            return False
        if you.get('attack_only', 0) > 0 and card.card_type != 'thorn':
            return False
        elixir = you.get('elixir', 0)
        magic = you.get('magic', 0)
        dup = you.get('cards_played_this_turn', {}).get(card.def_id, 0)
        if 'symbiosis' in card.flags:
            dup = 0
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
                self._update_status(t("cannot_play"))
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
        type_str = {'thorn': 'Thorn', 'bloom': 'Bloom', 'root': 'Root', 'guard': 'Guard'}.get(card_def.card_type, '?')
        tk.Label(self.play_zone, text=f"{card_def.display_name}",
                 font=_font(_fc, 9, True), fg=type_color,
                 bg=COLORS['bloom_bg']).pack(pady=(4, 0))
        tk.Label(self.play_zone, text=f"[{type_str}]",
                 font=_font(_fc, 7), fg=type_color,
                 bg=COLORS['bloom_bg']).pack()
        tk.Label(self.play_zone, text=t("waiting_response"),
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
            self.play_zone_label = tk.Label(self.play_zone, text=t("drag_to_play"),
                                            font=_font(_f, 12, True),
                                            fg=COLORS['bloom'], bg=COLORS['bloom_bg'])
        else:
            self.play_zone.config(bg=COLORS['bg_page'], relief=tk.GROOVE)
            self.play_zone_label = tk.Label(self.play_zone, text=t("drag_to_play"),
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
                       if CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).card_type == 'thorn'
                       and c.get('instance_id') != card.instance_id]
            if not attacks:
                messagebox.showinfo(t('notice'), t('no_attack_for_fission'))
                return False
            options = [f"{CARD_DEFS.get(a.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name}" for a in attacks]
            sel = self._simple_choice(t("choose_fission_target"), options)
            if sel is None:
                return False
            return {'target_instance_id': attacks[sel].get('instance_id')}
        elif card.def_id == 'Fusion':
            attacks = [c for c in self.game_state.get('you', {}).get('hand', [])
                       if CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).card_type == 'thorn'
                       and c.get('instance_id') != card.instance_id]
            same_name_groups: Dict[str, list] = {}
            for a in attacks:
                same_name_groups.setdefault(a.get('def_id', ''), []).append(a)
            valid_groups = {k: v for k, v in same_name_groups.items() if len(v) >= 2}
            if not valid_groups:
                messagebox.showinfo(t('notice'), t('no_same_attack_for_fusion'))
                return False
            group_options = [f"{CARD_DEFS.get(k, CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name} x{len(v)}" for k, v in valid_groups.items()]
            sel = self._simple_choice(t("choose_fusion_group"), group_options)
            if sel is None:
                return False
            group_key = list(valid_groups.keys())[sel]
            group = valid_groups[group_key][:3]
            return {'target_instance_ids': [c.get('instance_id') for c in group]}
        elif card.def_id == 'Mimic':
            others = [c for c in self.game_state.get('you', {}).get('hand', [])
                      if c.get('instance_id') != card.instance_id]
            if not others:
                messagebox.showinfo(t("notice"), t("no_other_cards"))
                return False
            options = [f"{CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name}" for c in others]
            sel = self._simple_choice(t("choose_mimic_target"), options)
            if sel is None:
                return False
            return {'target_instance_id': others[sel].get('instance_id')}
        elif card.def_id == 'Chromosome':
            discard = self.game_state.get('you', {}).get('discard', [])
            if not discard:
                messagebox.showinfo(t("notice"), t("discard_empty"))
                return False
            options = [f"{CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name}" for c in discard]
            sel = self._simple_choice(t("choose_from_discard"), options)
            if sel is None:
                return False
            return {'target_def_id': discard[sel].get('def_id')}
        elif card.def_id == 'Sewage':
            opp_eq = self.game_state.get('opponent', {}).get('equipment', [])
            destroyable = [e for e in opp_eq if 'indestructible' not in CARD_DEFS.get(
                e.get('card_instance', {}).get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '', flags=set())).flags]
            if not destroyable:
                messagebox.showinfo(t("notice"), t("no_enemy_equip"))
                return False
            options = [f"{CARD_DEFS.get(e.get('card_instance', {}).get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name}" for e in destroyable]
            sel = self._simple_choice(t("choose_equip_to_destroy"), options)
            if sel is None:
                return False
            return {'target_instance_id': destroyable[sel].get('card_instance', {}).get('instance_id')}
        elif card.def_id == 'Chilli':
            others = [c for c in self.game_state.get('you', {}).get('hand', [])
                      if c.get('instance_id') != card.instance_id]
            if others:
                options = [f"{CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name}" for c in others]
                sel = self._simple_choice(t("choose_card_to_discard"), options)
                if sel is None:
                    return False
                return {'target_instance_id': others[sel].get('instance_id')}
            return None
        return None

    def _simple_choice(self, title: str, options: list, allow_cancel: bool = True) -> Optional[int]:
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
        if allow_cancel:
            tk.Button(btn_frame, text=t("cancel"), command=on_cancel,
                      font=_font(_f, 12), bg=COLORS['damage_bg'],
                      fg=COLORS['damage'], width=8).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text=t("ok"), command=on_ok,
                  font=_font(_f, 12), bg=COLORS['health_bg'],
                  fg=COLORS['health_text'], width=8).pack(side=tk.RIGHT, padx=6)
        if not allow_cancel:
            dialog.protocol("WM_DELETE_WINDOW", lambda: None)

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
            label_text = t('equip_info', name=card_def.display_name, turns=turns)
            if corruption:
                label_text += t('equip_corruption')
            bg_color = COLORS['bg_card']
            fg_color = COLORS['armor_text']
            if 'indestructible' in card_def.flags:
                fg_color = COLORS['indestructible']
                bg_color = COLORS['indestructible_bg']
            if card_def.trigger_cost_e >= 0 and is_my_equipment and turns >= 1:
                btn = tk.Button(frame, text=t('equip_trigger_cost', info=label_text, cost=card_def.trigger_cost_e),
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

    def _on_surrender(self):
        if not self._surrender_pending:
            self._surrender_pending = True
            self.surrender_btn.config(text=t('confirm_surrender'), bg=COLORS['damage_bg'], fg=COLORS['damage'])
            self.root.after(3000, self._reset_surrender_btn)
        else:
            self._surrender_pending = False
            self.surrender_btn.config(text=t('surrender'), bg=COLORS['bg_card'], fg=COLORS['text_secondary'])
            self._send(NetworkMessage('surrender', {}))

    def _on_chat_send(self, _event):
        if hasattr(self, 'chat_entry') and self.chat_entry.winfo_exists():
            text = self.chat_entry.get().strip()
            if text:
                self._send(NetworkMessage('chat', {'text': text}))
                self.chat_entry.delete(0, tk.END)

    def _on_chat_received(self, data):
        nickname = data.get('nickname', '?')
        text = data.get('text', '')
        if hasattr(self, 'log_text') and self.log_text.winfo_exists():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"[{nickname}] {text}\n", 'chat')
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)

    def _reset_surrender_btn(self):
        self._surrender_pending = False
        if hasattr(self, 'surrender_btn') and self.surrender_btn.winfo_exists():
            self.surrender_btn.config(text=t('surrender'), bg=COLORS['bg_card'], fg=COLORS['text_secondary'])

    def _view_deck(self):
        deck = self.game_state.get('you', {}).get('deck', [])
        if not deck:
            messagebox.showinfo(t('view_deck_title'), t('deck_empty'))
            return
        from collections import Counter
        counts = Counter()
        for c in deck:
            cd = CARD_DEFS.get(c.get('def_id', ''), None)
            if cd:
                counts[cd.display_name] += 1
        lines = [t("deck_total", count=len(deck))]
        for name, cnt in sorted(counts.items()):
            lines.append(f"  {name} ×{cnt}")
        dialog = tk.Toplevel(self.root)
        dialog.title(t("view_deck_title"))
        dialog.geometry("300x400")
        dialog.configure(bg=COLORS['bg_page'])
        dialog.transient(self.root)
        dialog.grab_set()
        txt = tk.Text(dialog, font=_font(_f, 12), bg=COLORS['bg_card'],
                      fg=COLORS['text_primary'], state=tk.NORMAL, wrap=tk.WORD)
        txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        txt.insert(tk.END, '\n'.join(lines))
        txt.config(state=tk.DISABLED)
        tk.Button(dialog, text=t("close"), command=dialog.destroy,
                  font=_font(_f, 12), bg=COLORS['damage_bg'], fg=COLORS['damage'],
                  width=8).pack(pady=8)

    def _show_response_ui(self):
        if self._is_spectating:
            return
        if not hasattr(self, 'response_frame') or not self.response_frame.winfo_exists():
            self._on_respond(None)
            return
        for w in self.response_frame.winfo_children():
            w.destroy()
        card_dict = self.response_data.get('card', {})
        card_def = CARD_DEFS.get(card_dict.get('def_id', ''), None)
        card_name = card_def.display_name if card_def else card_dict.get('def_id', '?')
        trigger_desc = ''
        if card_def:
            if card_def.card_type == 'thorn':
                trigger_desc = t('enemy_attack')
            elif card_def.card_type == 'bloom':
                trigger_desc = t('enemy_skill')
            if card_def.id in ('Sewage', 'MagicSewage'):
                trigger_desc += t('enemy_destroy_equip')
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
                btn_text = t('use_card', name=cc_def.display_name, cost=cost_str)
                if not can_afford:
                    btn_text += t('insufficient_resources')
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
                                   text=t("no_counter", countdown=self._response_countdown),
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
            self._pass_btn.config(text=t("no_counter", countdown=self._response_countdown))
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
        if self._is_spectating:
            return
        choice_type = self.choice_data.get('choice_type', '')
        card_dict = self.choice_data.get('card', {})
        card_def = CARD_DEFS.get(card_dict.get('def_id', ''), None)
        card_name = card_def.display_name if card_def else '?'
        choice_result = None
        if choice_type == 'choose_attack_from_hand':
            attacks = [c for c in self.game_state.get('you', {}).get('hand', [])
                       if CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).card_type == 'thorn']
            if not attacks:
                messagebox.showinfo(t("notice"), t("no_attack_cards"))
            else:
                options = [f"{CARD_DEFS.get(a.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name}" for a in attacks]
                sel = self._simple_choice(t('choose_attack_for', name=card_name), options)
                if sel is not None and 0 <= sel < len(attacks):
                    choice_result = {'target_instance_id': attacks[sel].get('instance_id')}
        elif choice_type == 'choose_enemy_equipment':
            opp_eq = self.game_state.get('opponent', {}).get('equipment', [])
            if not opp_eq:
                messagebox.showinfo(t("notice"), t("no_enemy_equipment"))
            else:
                options = [f"{CARD_DEFS.get(e.get('card_instance', {}).get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name}" for e in opp_eq]
                sel = self._simple_choice(t('choose_equip_for', name=card_name), options)
                if sel is not None and 0 <= sel < len(opp_eq):
                    choice_result = {'target_instance_id': opp_eq[sel].get('card_instance', {}).get('instance_id')}
        elif choice_type == 'choose_card_to_discard':
            other_cards = self.game_state.get('you', {}).get('hand', [])
            if not other_cards:
                pass
            else:
                options = [f"{CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name}" for c in other_cards]
                sel = self._simple_choice(t('choose_discard_for', name=card_name), options)
                if sel is not None and 0 <= sel < len(other_cards):
                    choice_result = {'target_instance_id': other_cards[sel].get('instance_id')}
        elif choice_type == 'choose_card_from_deck':
            deck = self.game_state.get('you', {}).get('deck', [])
            if not deck:
                messagebox.showinfo(t("notice"), t("deck_empty"))
            else:
                options = [f"{CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name}" for c in deck]
                sel = self._simple_choice(t('choose_from_deck_for', name=card_name), options)
                if sel is not None and 0 <= sel < len(deck):
                    choice_result = {'target_def_id': deck[sel].get('def_id')}
        elif choice_type == 'choose_card_from_discard':
            discard = self.game_state.get('you', {}).get('discard', [])
            if not discard:
                messagebox.showinfo(t("notice"), t("discard_empty"))
            else:
                options = [f"{CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name}" for c in discard]
                sel = self._simple_choice(t('choose_from_discard_for', name=card_name), options)
                if sel is not None and 0 <= sel < len(discard):
                    choice_result = {'target_def_id': discard[sel].get('def_id')}
        elif choice_type == 'choose_same_attacks_from_hand':
            attacks = [c for c in self.game_state.get('you', {}).get('hand', [])
                       if CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).card_type == 'thorn']
            same_name_groups: Dict[str, list] = {}
            for a in attacks:
                same_name_groups.setdefault(a.get('def_id', ''), []).append(a)
            valid_groups = {k: v for k, v in same_name_groups.items() if len(v) >= 2}
            if not valid_groups:
                messagebox.showinfo(t("notice"), t("no_same_attack_for_fusion"))
            else:
                group_options = [f"{CARD_DEFS.get(k, CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name} x{len(v)}" for k, v in valid_groups.items()]
                sel = self._simple_choice(t('choose_attack_group_for', name=card_name), group_options)
                if sel is not None:
                    group_key = list(valid_groups.keys())[sel]
                    group = valid_groups[group_key][:3]
                    choice_result = {'target_instance_ids': [c.get('instance_id') for c in group]}
        elif choice_type == 'choose_card_from_hand':
            other_cards = self.game_state.get('you', {}).get('hand', [])
            if not other_cards:
                pass
            else:
                options = [f"{CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name}" for c in other_cards]
                sel = self._simple_choice(t('choose_hand_for', name=card_name), options)
                if sel is not None and 0 <= sel < len(other_cards):
                    choice_result = {'target_instance_id': other_cards[sel].get('instance_id')}
        elif choice_type == 'choose_from_deck':
            deck = self.game_state.get('you', {}).get('deck', [])
            if not deck:
                messagebox.showinfo(t("notice"), t("deck_empty"))
            else:
                options = [f"{CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name}" for c in deck]
                sel = self._simple_choice(t('choose_from_deck_for', name=card_name), options)
                if sel is not None and 0 <= sel < len(deck):
                    choice_result = {'target_instance_id': deck[sel].get('instance_id')}
        elif choice_type == 'choose_from_enemy_hand':
            opp_hand = self.game_state.get('opponent', {}).get('hand', [])
            if not opp_hand:
                messagebox.showinfo(t("notice"), t("no_enemy_hand"))
            else:
                options = [f"{CARD_DEFS.get(c.get('def_id', ''), CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name}" for c in opp_hand]
                allow_cancel = not (card_def and 'uncancellable' in card_def.flags)
                sel = self._simple_choice(t('choose_from_enemy_hand_for', name=card_name), options, allow_cancel)
                if sel is not None and 0 <= sel < len(opp_hand):
                    choice_result = {'target_instance_id': opp_hand[sel].get('instance_id')}
                elif not allow_cancel and sel is None:
                    sel = 0
                    choice_result = {'target_instance_id': opp_hand[0].get('instance_id')}
        self._send(NetworkMessage('resolve_choice', {'choice': choice_result}))
        self.choice_pending = False

    def _show_event_select_ui(self):
        self._clear_content()
        self._update_status(t("select_event"))
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

        tk.Label(frame, text=t('select_event'), font=_font(_f, 20, True),
                 fg=COLORS['damage'], bg=COLORS['bg_page']).pack(pady=(10, 5))
        tk.Label(frame, text=t('select_event_desc'), font=_font(_f, 12),
                 fg=COLORS['text_secondary'], bg=COLORS['bg_page']).pack(pady=(0, 15))

        if my_pick is not None:
            event_name = '?'
            for ev in events:
                if ev and ev.get('id') == my_pick:
                    event_name = ev.get('name', '?')
                    break
            tk.Label(frame, text=t('event_selected', name=event_name), font=_font(_f, 16, True),
                     fg=COLORS['health'], bg=COLORS['health_bg'],
                     relief=tk.GROOVE, padx=20, pady=10).pack(pady=15)
            if not opp_selected:
                tk.Label(frame, text=t('waiting_opponent'), font=_font(_f, 14),
                         fg=COLORS['magic_text'], bg=COLORS['bg_page']).pack(pady=10)
            else:
                tk.Label(frame, text=t('opponent_selected'), font=_font(_f, 14),
                         fg=COLORS['health'], bg=COLORS['bg_page']).pack(pady=10)
            return

        opp_status = t('opponent_selected') if opp_selected else t('opponent_selecting')
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

            ef = tk.Frame(events_frame, bg=card_bg, relief=tk.FLAT, bd=0,
                          highlightbackground=border_color, highlightthickness=1,
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

            select_btn = tk.Button(ef, text=t("select_this_event"), font=_font(_f, 11, True),
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
            magic_options_all = data.get('magic_options', [])
            draft_picks = data.get('draft_picks', [])
            if magic_options_all and draft_picks:
                sub_choice = self._show_magic_conversion_flow(magic_options_all, draft_picks)
                if sub_choice is None:
                    return
        elif event_id == 3:
            draft_picks = data.get('draft_picks', [])
            if draft_picks:
                sub_choice = self._show_light_conversion_choice(draft_picks)
                if sub_choice is None:
                    return
        elif event_id == 8:
            draft_picks = data.get('draft_picks', [])
            if draft_picks:
                ygg_choice = self._show_yggdrasil_conversion_choice(draft_picks)
                if ygg_choice is None:
                    return
                sub_choice = ygg_choice

        self._send(NetworkMessage('select_opening_event', {
            'event_id': event_id,
            'sub_choice': sub_choice,
        }))
        self._update_status(t("event_waiting"))

    def _show_magic_conversion_flow(self, magic_options_all, draft_picks):
        from collections import Counter
        counts = Counter(draft_picks)
        card_types = sorted(counts.keys(), key=lambda x: CARD_DEFS.get(x, CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name)
        card_options = []
        for def_id in card_types:
            card_def = CARD_DEFS.get(def_id)
            if card_def:
                card_options.append(f"{card_def.display_name} (x{counts[def_id]})")
        count_options = [str(i) for i in range(1, min(4, len(card_types) + 1))]
        if not count_options:
            return None
        sel = self._simple_choice(t("choose_convert_count"), count_options)
        if sel is None:
            return None
        convert_count = sel + 1
        conversions = []
        remaining_counts = dict(counts)
        for i in range(convert_count):
            if i < len(magic_options_all):
                magic_options = magic_options_all[i]
            else:
                magic_options = magic_options_all[-1] if magic_options_all else []
            magic_options_display = []
            for def_id in magic_options:
                card_def = CARD_DEFS.get(def_id)
                if card_def:
                    magic_options_display.append(f"{card_def.display_name} ({card_def.cost_e}E/{card_def.cost_m}M) {card_def.effect_text}")
            if not magic_options_display:
                break
            magic_sel = self._simple_choice(t("choose_magic_card_n", n=i+1), magic_options_display)
            if magic_sel is None:
                return None
            magic_def = magic_options[magic_sel]
            available_types = [d for d in card_types if remaining_counts.get(d, 0) > 0]
            available_display = []
            for def_id in available_types:
                card_def = CARD_DEFS.get(def_id)
                if card_def:
                    available_display.append(f"{card_def.display_name} (x{remaining_counts[def_id]})")
            if not available_display:
                break
            source_sel = self._simple_choice(t("choose_source_card_n", n=i+1), available_display)
            if source_sel is None:
                return None
            source_def = available_types[source_sel]
            remaining_counts[source_def] = remaining_counts.get(source_def, 0) - 1
            conversions.append({'magic_def_id': magic_def, 'source_def_id': source_def})
        if not conversions:
            return None
        return {'conversions': conversions}

    def _show_light_conversion_choice(self, draft_picks):
        return self._show_card_conversion_choice(draft_picks, 5, t("choose_light_cards"))

    def _show_yggdrasil_conversion_choice(self, draft_picks):
        from collections import Counter
        counts = Counter(draft_picks)
        options = []
        for def_id in sorted(counts.keys(), key=lambda x: CARD_DEFS.get(x, CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name):
            if def_id == 'Yggdrasil':
                continue
            card_def = CARD_DEFS.get(def_id)
            if card_def:
                options.append(f"{card_def.display_name} (x{counts[def_id]})")
        if not options:
            return None
        sel = self._simple_choice(t("choose_yggdrasil_card"), options)
        if sel is None:
            return None
        def_ids = [d for d in sorted(counts.keys(), key=lambda x: CARD_DEFS.get(x, CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name) if d != 'Yggdrasil']
        if sel < len(def_ids):
            return {'yggdrasil_convert_def_id': def_ids[sel]}
        return None

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
        tk.Label(dialog, text=t("convert_per_type", max=max_count), font=_font(_f, 10),
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
        for def_id, count in sorted(counts.items(), key=lambda x: CARD_DEFS.get(x[0], CardDef('', '', '', 0, 0, '', 0, '', '', '')).display_name):
            if def_id == 'Light' and max_count == 5:
                continue
            card_def = CARD_DEFS.get(def_id)
            if not card_def:
                continue
            cf = tk.Frame(inner, bg=COLORS['bg_card'], relief=tk.GROOVE, bd=1)
            cf.pack(fill=tk.X, padx=8, pady=3)

            type_color = CARD_TYPE_COLORS.get(card_def.card_type, COLORS['text_primary'])
            tk.Label(cf, text=f"{card_def.display_name}", font=_font(_f, 12, True),
                     fg=type_color, bg=COLORS['bg_card']).pack(side=tk.LEFT, padx=(8, 4))
            tk.Label(cf, text=f"x{count}", font=_font(_f, 11),
                     fg=COLORS['text_secondary'], bg=COLORS['bg_card']).pack(side=tk.LEFT, padx=4)

            var = tk.IntVar(value=0)
            max_convert = min(count, max_count)
            spin = tk.Spinbox(cf, from_=0, to=max_convert, textvariable=var,
                              width=3, font=_font(_f, 11), state='readonly')
            spin.pack(side=tk.RIGHT, padx=8)
            tk.Label(cf, text=t("convert_label"), font=_font(_f, 10),
                     fg=COLORS['text_secondary'], bg=COLORS['bg_card']).pack(side=tk.RIGHT)
            card_entries.append((def_id, var, count))

        count_label = tk.Label(dialog, text=t("selected_count", current=0, max=max_count), font=_font(_f, 12, True),
                               fg=COLORS['magic_text'], bg=COLORS['bg_page'])
        count_label.pack(pady=4)

        def update_count(*args):
            total = sum(v.get() for _, v, _ in card_entries)
            color = COLORS['damage'] if total > max_count else COLORS['magic_text']
            count_label.config(text=t("selected_count", current=total, max=max_count), fg=color)

        for _, var, _ in card_entries:
            var.trace_add('write', update_count)

        def on_ok():
            total = sum(v.get() for _, v, _ in card_entries)
            if total > max_count:
                messagebox.showwarning(t('notice'), t("max_selection_warning", max=max_count), parent=dialog)
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
        tk.Button(btn_frame, text=t("cancel"), command=on_cancel,
                  font=_font(_f, 12), bg=COLORS['damage_bg'],
                  fg=COLORS['damage'], width=8).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text=t("ok"), command=on_ok,
                  font=_font(_f, 12), bg=COLORS['health_bg'],
                  fg=COLORS['health_text'], width=8).pack(side=tk.RIGHT, padx=6)

        dialog.lift()
        dialog.focus_force()
        dialog.wait_window()
        return result[0]

    def _show_draft_ui(self):
        self._clear_content()
        self._update_status(t("draft_phase"))
        self.draft_frame = tk.Frame(self.content_frame, bg=COLORS['bg_page'])
        self.draft_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        tk.Label(self.draft_frame, text=t("draft_phase"), font=_font(_f, 16, True),
                 bg=COLORS['bg_page'], fg=COLORS['text_primary']).pack(pady=8)
        self.draft_info = tk.Label(self.draft_frame, text="", font=_font(_f, 12),
                                   bg=COLORS['bg_page'], fg=COLORS['text_secondary'])
        self.draft_info.pack(pady=4)
        self.draft_options_frame = tk.Frame(self.draft_frame, bg=COLORS['bg_page'])
        self.draft_options_frame.pack(pady=10)
        self.draft_picks_label = tk.Label(self.draft_frame, text=t("draft_selected"), font=_font(_f, 12),
                                          bg=COLORS['bg_page'], fg=COLORS['text_primary'])
        self.draft_picks_label.pack(pady=5)
        self.draft_reroll_btn = tk.Button(self.draft_frame, text=t("draft_reroll"), font=_font(_f, 12),
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
        if my_count >= total:
            self.draft_info.config(text=t('draft_complete') + f" ({t('draft_opp_count', opp_count=opp_count)})")
        else:
            self.draft_info.config(text=t('draft_info', round=round_num, total=total, rerolls=rerolls, opp_count=opp_count))
        for w in self.draft_options_frame.winfo_children():
            w.destroy()
        if my_count >= total:
            tk.Label(self.draft_options_frame, text=t("draft_waiting"),
                     font=_font(_f, 14), fg=COLORS['health'],
                     bg=COLORS['bg_page']).pack(pady=20)
        else:
            for opt_dict in ds.get('options', []):
                card = CardInstance.from_dict(opt_dict)
                card_def = card.card_def
                type_color = CARD_TYPE_COLORS.get(card.card_type, COLORS['text_primary'])
                btn_text = (f"{card_def.display_name} ({card_def.name_en})\n"
                            f"{t('draft_cost', e=card_def.cost_e, m=card_def.cost_m)}"
                            f"{card_def.effect_text}\n{card_def.description}")
                tk.Button(self.draft_options_frame, text=btn_text,
                          font=_font(_f, 10), width=32, height=8,
                          wraplength=int(240*SCALE), bg=COLORS['bg_card'], fg=type_color,
                          relief=tk.RAISED, bd=2,
                          command=lambda d=card.def_id: self._on_draft_pick(d)).pack(side=tk.LEFT, padx=8, pady=4)
        picks = ds.get('picks', [])
        picks_display = [CARD_DEFS.get(pid, CardDef('', '', pid, 0, 0, '', 0, '', '', '')).display_name for pid in picks]
        self.draft_picks_label.config(text=t('draft_picks', count=len(picks), picks=', '.join(picks_display)))
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
            text, color, bg = t('you_win'), COLORS['health'], COLORS['health_bg']
        else:
            text, color, bg = t('you_lose'), COLORS['damage'], COLORS['damage_bg']
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
        self._rematch_btn = tk.Button(self._gameover_btn_frame, text=t('request_rematch'),
                                      font=_font(_f, 14, True),
                                      command=self._on_rematch, bg=COLORS['bloom_bg'],
                                      fg=COLORS['bloom'], width=16, height=2)
        self._rematch_btn.pack(side=tk.LEFT, padx=10)
        tk.Button(self._gameover_btn_frame, text=t('return_lobby'), font=_font(_f, 14, True),
                  command=self._on_return_lobby, bg=COLORS['armor_bg'], fg=COLORS['armor_text'],
                  width=14, height=2).pack(side=tk.LEFT, padx=10)

    def _show_rematch_request(self, data):
        self._rematch_pending = True
        if hasattr(self, '_rematch_btn') and self._rematch_btn and self._rematch_btn.winfo_exists():
            self._rematch_btn.config(text=t('agree_rematch'), command=self._on_accept_rematch,
                                     bg=COLORS['health_bg'], fg=COLORS['health_text'])
        self._update_status(t('opponent_rematch'))

    def _on_rematch(self):
        self._rematch_sent = True
        self._send(NetworkMessage('rematch', {}))
        if hasattr(self, '_rematch_btn') and self._rematch_btn and self._rematch_btn.winfo_exists():
            self._rematch_btn.config(text=t('rematch_sent'), state=tk.DISABLED)
        self._update_status(t('rematch_waiting'))

    def _on_accept_rematch(self):
        self._send(NetworkMessage('rematch', {}))
        self._update_status(t('rematch_agreed'))

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
