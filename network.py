import json
import socket
import threading
from typing import Optional, Callable, Dict, Any


class NetworkMessage:
    def __init__(self, msg_type: str, data: Dict[str, Any] = None):
        self.msg_type = msg_type
        self.data = data or {}

    def to_json(self) -> str:
        return json.dumps({'type': self.msg_type, 'data': self.data}, ensure_ascii=False)

    @staticmethod
    def from_json(s: str) -> 'NetworkMessage':
        try:
            d = json.loads(s)
            return NetworkMessage(d.get('type', ''), d.get('data', {}))
        except json.JSONDecodeError:
            return NetworkMessage('error', {'raw': s})


class MessageBuffer:
    def __init__(self):
        self.buffer = ''

    def feed(self, data: str):
        self.buffer += data

    def get_messages(self):
        messages = []
        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            line = line.strip()
            if line:
                messages.append(NetworkMessage.from_json(line))
        return messages


class NetworkConnection:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buffer = MessageBuffer()
        self.lock = threading.Lock()
        self.connected = True

    def send(self, msg: NetworkMessage):
        if not self.connected:
            return
        try:
            data = msg.to_json() + '\n'
            with self.lock:
                self.sock.sendall(data.encode('utf-8'))
        except (ConnectionError, OSError):
            self.connected = False

    def receive(self) -> Optional[NetworkMessage]:
        messages = self._receive_all()
        return messages[0] if messages else None

    def _receive_all(self):
        messages = self.buffer.get_messages()
        if messages:
            return messages
        try:
            self.sock.settimeout(0.1)
            data = self.sock.recv(65536)
            if not data:
                self.connected = False
                return []
            self.buffer.feed(data.decode('utf-8'))
            return self.buffer.get_messages()
        except socket.timeout:
            return []
        except (ConnectionError, OSError):
            self.connected = False
            return []

    def receive_all(self):
        return self._receive_all()

    def close(self):
        self.connected = False
        try:
            self.sock.close()
        except:
            pass


def send_message(sock: socket.socket, msg: NetworkMessage):
    data = msg.to_json() + '\n'
    try:
        sock.sendall(data.encode('utf-8'))
    except (ConnectionError, OSError):
        pass


def create_server(host: str, port: int) -> socket.socket:
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(2)
    return server_sock


def connect_to_server(host: str, port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
    except (AttributeError, OSError):
        pass
    return sock


DEFAULT_PORT = 416
