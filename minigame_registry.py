# -*- coding: utf-8 -*-
"""休闲花园 · 小游戏注册表（服务端唯一的一份"有哪些小游戏"的事实）。

目前只登记元数据，**不含玩法**：
- 大厅/休闲花园列表页、presence（在线状态）、对局邀请、返回按钮都从这里读，
  以后加一个小游戏只要在 MINIGAMES 里加一行 + 写自己的页面；
- 是否"真正启用"仍由 app.py 的环境开关决定（例如 MINIGAME_2048_ENABLED），
  注册表里的 ``invite_ready`` 表示这套邀请/在线状态管线已经接好。
"""

from __future__ import annotations

MINIGAMES = {
    '2048': {
        'key': '2048',
        'title': 'Craft Eternal',
        'title_zh': '合成大西瓜',
        'path': '/minigame/2048',
        'invite_ready': True,
    },
    'suika': {
        'key': 'suika',
        'title': '合成大花花',
        'title_zh': '合成大花花',
        'path': '/minigame/suika',
        'invite_ready': True,
    },
}


def minigame_entry(game_key) -> dict:
    """按 key 取注册信息；没登记过返回空字典（调用方据此拒绝）。"""

    key = str(game_key or '').strip()[:32]
    entry = MINIGAMES.get(key)
    return dict(entry) if entry else {}


def is_minigame(game_key) -> bool:
    return bool(minigame_entry(game_key))


def minigame_keys() -> tuple:
    return tuple(MINIGAMES.keys())


def invite_ready(game_key) -> bool:
    """这个小游戏是否已经接好"被邀请进对局"的管线。"""

    entry = minigame_entry(game_key)
    return bool(entry.get('invite_ready'))


def path_of(game_key) -> str:
    return str(minigame_entry(game_key).get('path') or '')


def minigame_hub_back_href(from_key) -> str:
    """休闲花园返回按钮的目标：只认白名单里的来源，其余一律回主页。

    从大厅进来的要回到大厅（并让大厅记住位置），从首页进来的就回首页——
    不接受任意 URL，避免开放重定向。
    """

    key = str(from_key or '').strip().lower()
    if key == 'lobby':
        return '/?enter_lobby=1'
    return '/'


def normalize_from(from_key) -> str:
    key = str(from_key or '').strip().lower()
    return key if key in ('lobby', 'home') else ''


def with_from(path: str, from_key) -> str:
    """给站内链接带上来源标记（白名单外的来源不加）。"""

    key = normalize_from(from_key)
    if not key:
        return path
    joiner = '&' if '?' in path else '?'
    return f'{path}{joiner}from={key}'
