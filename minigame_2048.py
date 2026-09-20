# -*- coding: utf-8 -*-
"""2048 小游戏的**规则与验证核心**（纯函数，不碰数据库、不碰 Flask）。

设计要点（对应验收用例 1–4、7、8、10）：

* 棋盘、分数、随机生成全部由 ``(种子, 操作序列)`` 决定，客户端与服务端跑同一套；
* 随机用 32 位 xorshift（两边都能按整数语义实现），**不用** Math.random；
* 操作序列只记方向（``0=左 1=右 2=上 3=下``），一个字符一步；
* 服务端只存"检查点 + 之后的增量"，验证时从检查点重放，不必从头重算整局；
* 稀有度是**显示配置**：合并只看数值，色板/名称改了不影响存档。

客户端实现见 ``static/js/minigame_2048.js``，两边必须给出相同的棋盘、分数、
随机状态与结束判定（测试用同一组种子对拍）。
"""

from __future__ import annotations

import json
from typing import Dict, Iterable, List, Optional, Tuple

BOARD_SIZE = 4
CELL_COUNT = BOARD_SIZE * BOARD_SIZE

PROTOCOL_VERSION = 1
RULES_VERSION = 1        # 规则不兼容变更时 +1（排行榜按版本隔离）
SAVE_VERSION = 1         # 存档结构版本
SPAWN_MIN_VALUE = 2
SPAWN_MIN_RATIO = 90     # 90% 出 2（Common），10% 出 4（Unusual）
SEED_MASK = 0xFFFFFFFF

# 唯一色板（用户给定表；名称不随语言翻译，色板与明暗主题无关）。
RARITY_TABLE: Tuple[Dict[str, object], ...] = (
    {"value": 2, "name": "Common", "bg": "#7EEF6D", "border": "#65BF57", "fg": "#15201B"},
    {"value": 4, "name": "Unusual", "bg": "#FFE65D", "border": "#CCB84A", "fg": "#15201B"},
    {"value": 8, "name": "Rare", "bg": "#4D52E3", "border": "#3E42B6", "fg": "#FFFFFF"},
    {"value": 16, "name": "Epic", "bg": "#861FDE", "border": "#6B19B2", "fg": "#FFFFFF"},
    {"value": 32, "name": "Legendary", "bg": "#DE1F1F", "border": "#B21919", "fg": "#FFFFFF"},
    {"value": 64, "name": "Mythic", "bg": "#1FDBDE", "border": "#19AFB2", "fg": "#15201B"},
    {"value": 128, "name": "Ultra", "bg": "#FF2B75", "border": "#CC225E", "fg": "#15201B"},
    {"value": 256, "name": "Super", "bg": "#2BFFA3", "border": "#22CC82", "fg": "#15201B"},
    {"value": 512, "name": "Omega", "bg": "#F329D9", "border": "#C221AE", "fg": "#15201B"},
    {"value": 1024, "name": "Unique", "bg": "#555555", "border": "#444444", "fg": "#FFFFFF"},
    {"value": 2048, "name": "Eternal", "bg": "#EEEEEE", "border": "#BEBEBE", "fg": "#15201B"},
    {"value": 4096, "name": "Fabled", "bg": "#FF5500", "border": "#CF4500", "fg": "#15201B"},
    {"value": 8192, "name": "Divine", "bg": "#67549C", "border": "#53447E", "fg": "#FFFFFF"},
    {"value": 16384, "name": "Astral", "bg": "#046307", "border": "#035005", "fg": "#FFFFFF"},
    {"value": 32768, "name": "Celestial", "bg": "#00BFFF", "border": "#009BCF", "fg": "#15201B"},
    {"value": 65536, "name": "Galactic", "bg": "#7F0226", "border": "#974D63", "fg": "#FFFFFF"},
    {"value": 131072, "name": "Apotheotic", "bg": "#B3AB56", "border": "#5E4B2C", "fg": "#15201B"},
)

RARITY_BY_VALUE: Dict[int, Dict[str, object]] = {int(item["value"]): item for item in RARITY_TABLE}
ETERNAL_VALUE = 2048

DIRECTIONS = {"left": 0, "right": 1, "up": 2, "down": 3}
DIRECTION_NAMES = ("left", "right", "up", "down")
DIRECTION_CHARS = "lrud"
CHAR_TO_DIRECTION = {char: index for index, char in enumerate(DIRECTION_CHARS)}


class Minigame2048Error(ValueError):
    """规则/协议层面的错误（调用方应转成 4xx，而不是 500）。"""


def rarity_for(value: int) -> Optional[Dict[str, object]]:
    """取显示配置；超出色表的合法数值返回 ``None``（渲染层退回数字显示）。"""

    return RARITY_BY_VALUE.get(int(value))


def rarity_name(value: int) -> str:
    item = rarity_for(value)
    return str(item["name"]) if item else ""


# ---------------------------------------------------------------- 随机数


def seed_from_text(text: str) -> int:
    """稳定地把任意字符串折成一个种子（不用 Python 的 hash，跨进程稳定）。"""

    value = 0x811C9DC5
    for char in str(text or ""):
        value ^= ord(char) & 0xFF
        value = (value * 0x01000193) & SEED_MASK
    return value or 0x9E3779B9


def normalize_seed(seed) -> int:
    try:
        value = int(seed)
    except (TypeError, ValueError):
        raise Minigame2048Error("种子必须是整数")
    value &= SEED_MASK
    if value == 0:
        raise Minigame2048Error("种子不能为 0")
    return value


def rng_next(state: int) -> int:
    """xorshift32：与客户端同一套位运算（Python 侧手动截到 32 位）。"""

    value = int(state) & SEED_MASK
    if value == 0:
        value = 0x9E3779B9
    value ^= (value << 13) & SEED_MASK
    value ^= value >> 17
    value ^= (value << 5) & SEED_MASK
    return value & SEED_MASK


def rng_range(state: int, limit: int) -> Tuple[int, int]:
    """返回 ``(下一次状态, 0..limit-1)``。``limit<=0`` 时返回 0。"""

    nxt = rng_next(state)
    if limit <= 0:
        return nxt, 0
    return nxt, nxt % int(limit)


# ---------------------------------------------------------------- 棋盘


def empty_cells(cells: Iterable[int]) -> List[int]:
    return [index for index, value in enumerate(cells) if not int(value or 0)]


def spawn_tile(cells: List[int], rng_state: int) -> Tuple[List[int], int, Dict[str, int]]:
    """在空格里按 90% / 10% 放一个新块，返回 ``(新棋盘, 新随机状态, 新块信息)``。"""

    empties = empty_cells(cells)
    if not empties:
        return list(cells), rng_state, {}
    rng_state, value_roll = rng_range(rng_state, 100)
    value = SPAWN_MIN_VALUE if value_roll < SPAWN_MIN_RATIO else SPAWN_MIN_VALUE * 2
    rng_state, index_roll = rng_range(rng_state, len(empties))
    cell = empties[index_roll]
    out = list(cells)
    out[cell] = value
    return out, rng_state, {"index": cell, "value": value}


def initial_state(seed) -> Dict[str, object]:
    """开局：两个不同的空格各放一个块（各抽一次数值、一次位置）。"""

    rng_state = normalize_seed(seed)
    cells = [0] * CELL_COUNT
    spawns = []
    for _ in range(2):
        cells, rng_state, info = spawn_tile(cells, rng_state)
        if info:
            spawns.append(info)
    return {
        "seed": normalize_seed(seed),
        "rng_state": rng_state,
        "cells": cells,
        "score": 0,
        "spawns": spawns,
    }


def _merge_line(line: List[int]) -> Tuple[List[int], int, List[Dict[str, int]]]:
    """把一行（已按滑动方向排好）压紧并合并，返回 ``(结果, 得分, 合并明细)``。"""

    packed = [value for value in line if value]
    out: List[int] = []
    gained = 0
    merges: List[Dict[str, int]] = []
    index = 0
    while index < len(packed):
        current = packed[index]
        if index + 1 < len(packed) and packed[index + 1] == current:
            merged = current * 2
            gained += merged
            merges.append({"value": merged, "from": current})
            out.append(merged)
            index += 2
            continue
        out.append(current)
        index += 1
    while len(out) < BOARD_SIZE:
        out.append(0)
    return out, gained, merges


def line_indices(direction: int) -> List[List[int]]:
    """返回"每条线"的格子下标，方向决定线内顺序（滑动方向在前）。"""

    lines: List[List[int]] = []
    for row in range(BOARD_SIZE):
        indexes = [row * BOARD_SIZE + col for col in range(BOARD_SIZE)]
        if direction == DIRECTIONS["right"]:
            indexes.reverse()
        lines.append(indexes)
    if direction in (DIRECTIONS["up"], DIRECTIONS["down"]):
        lines = []
        for col in range(BOARD_SIZE):
            indexes = [row * BOARD_SIZE + col for row in range(BOARD_SIZE)]
            if direction == DIRECTIONS["down"]:
                indexes.reverse()
            lines.append(indexes)
    return lines


def apply_move(cells: List[int], direction: int) -> Dict[str, object]:
    """执行一次方向操作；不做生成，返回棋盘/得分/是否变化/合并明细。"""

    if direction not in range(4):
        raise Minigame2048Error("方向必须是 0..3")
    board = [int(value or 0) for value in cells]
    if len(board) != CELL_COUNT:
        raise Minigame2048Error("棋盘长度必须是 16")
    out = [0] * CELL_COUNT
    gained = 0
    merges: List[Dict[str, int]] = []
    for indexes in line_indices(direction):
        merged_line, line_gain, line_merges = _merge_line([board[index] for index in indexes])
        gained += line_gain
        for offset, index in enumerate(indexes):
            out[index] = merged_line[offset]
        for item in line_merges:
            merges.append(item)
    return {
        "cells": out,
        "gained": gained,
        "changed": out != board,
        "merges": merges,
    }


def max_tile(cells: Iterable[int]) -> int:
    values = [int(value or 0) for value in cells]
    return max(values) if values else 0


def is_game_over(cells: List[int]) -> bool:
    """没有空格 **且** 没有相邻同值才算负；满格但能合并不算。"""

    board = [int(value or 0) for value in cells]
    if any(value == 0 for value in board):
        return False
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            index = row * BOARD_SIZE + col
            value = board[index]
            if col + 1 < BOARD_SIZE and board[index + 1] == value:
                return False
            if row + 1 < BOARD_SIZE and board[index + BOARD_SIZE] == value:
                return False
    return True


# ---------------------------------------------------------------- 一步/整局


def step(state: Dict[str, object], direction: int) -> Dict[str, object]:
    """一次方向操作：无效操作不加分、不生成、不推进随机状态。"""

    cells = [int(value or 0) for value in state["cells"]]
    move = apply_move(cells, direction)
    if not move["changed"]:
        return {
            "cells": cells,
            "score": int(state.get("score") or 0),
            "rng_state": int(state["rng_state"]),
            "gained": 0,
            "spawned": None,
            "changed": False,
            "merges": [],
            "reached_2048": False,
        }
    rng_state, info = state["rng_state"], None
    new_cells, rng_state, info = spawn_tile(list(move["cells"]), int(rng_state))
    score_before = int(state.get("score") or 0)
    score = score_before + int(move["gained"])
    reached = score_before < ETERNAL_VALUE <= max_tile(move["cells"]) or (
        max_tile(cells) < ETERNAL_VALUE <= max_tile(new_cells)
    )
    return {
        "cells": new_cells,
        "score": score,
        "rng_state": rng_state,
        "gained": int(move["gained"]),
        "spawned": info,
        "changed": True,
        "merges": move["merges"],
        "reached_2048": bool(reached),
    }


def replay(seed, ops: Iterable[str], *, up_to: Optional[int] = None,
           start_state: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """按操作序列重放。``ops`` 用 ``l/r/u/d`` 字符表示方向。"""

    state = dict(start_state) if start_state else initial_state(seed)
    index = 0
    reached_flags: List[int] = []
    for char in "".join(ops or ""):
        if up_to is not None and index >= int(up_to):
            break
        direction = CHAR_TO_DIRECTION.get(str(char).lower())
        if direction is None:
            raise Minigame2048Error(f"未知方向字符：{char!r}")
        result = step(state, direction)
        if result["reached_2048"]:
            reached_flags.append(index)
        state = {
            "seed": state.get("seed"),
            "rng_state": result["rng_state"],
            "cells": result["cells"],
            "score": result["score"],
        }
        index += 1
    return {
        "seed": normalize_seed(state.get("seed") or seed),
        "rng_state": int(state["rng_state"]),
        "cells": [int(value or 0) for value in state["cells"]],
        "score": int(state.get("score") or 0),
        "index": index,
        "max_tile": max_tile(state["cells"]),
        "game_over": is_game_over([int(value or 0) for value in state["cells"]]),
        "reached_2048_at": (reached_flags[0] if reached_flags else None),
    }


def ops_from_list(ops: Iterable) -> str:
    """把 ``["left", ...]`` / ``[0, 1, ...]`` / ``"lrud"`` 统一成紧凑字符串。"""

    out = []
    for item in ops or []:
        if isinstance(item, int) or (isinstance(item, str) and item.isdigit()):
            value = int(item)
            if value not in range(4):
                raise Minigame2048Error("方向必须是 0..3")
            out.append(DIRECTION_CHARS[value])
        elif isinstance(item, str):
            text = item.strip().lower()
            if text in DIRECTIONS:
                out.append(DIRECTION_CHARS[DIRECTIONS[text]])
            elif len(text) == 1 and text in CHAR_TO_DIRECTION:
                out.append(text)
            else:
                raise Minigame2048Error(f"未知方向：{item!r}")
        else:
            raise Minigame2048Error(f"未知方向：{item!r}")
    return "".join(out)


def board_digest(cells: Iterable[int], score: int, seed: int, op_index: int = 0) -> str:
    """棋盘摘要：客户端与服务端对拍用（不是安全边界，只用来发现分叉）。"""

    payload = {
        "c": [int(value or 0) for value in cells],
        "s": int(score or 0),
        "k": int(seed or 0),
        "i": int(op_index or 0),
    }
    text = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return seed_from_text(text).to_bytes(4, "big").hex()


def verify_submission(seed, ops, *, from_index: int = 0, start_state: Optional[Dict[str, object]] = None,
                      claimed_score: Optional[int] = None,
                      claimed_cells: Optional[Iterable[int]] = None) -> Dict[str, object]:
    """服务端重放一段操作并核对客户端自报值。

    返回 ``{"ok": bool, ...}``；不合法/对不上时 ``ok=False`` 且带 ``reason``。
    """

    text = ops_from_list(ops) if not isinstance(ops, str) else str(ops)
    try:
        result = replay(seed, text, up_to=None, start_state=start_state)
    except Minigame2048Error as exc:
        return {"ok": False, "reason": str(exc)}
    if from_index and int(from_index) != 0 and start_state is None:
        return {"ok": False, "reason": "从检查点续验时必须带检查点状态"}
    if claimed_score is not None and int(claimed_score) != result["score"]:
        return {"ok": False, "reason": "分数与重放结果不一致", "result": result}
    if claimed_cells is not None:
        cells = [int(value or 0) for value in claimed_cells]
        if cells != result["cells"]:
            return {"ok": False, "reason": "棋盘与重放结果不一致", "result": result}
    return {"ok": True, "result": result}


def rarity_table_payload() -> List[Dict[str, object]]:
    """给前端的色板（名称不翻译，颜色与主题无关）。"""

    return [dict(item) for item in RARITY_TABLE]
