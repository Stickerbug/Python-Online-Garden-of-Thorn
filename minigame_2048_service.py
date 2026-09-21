# -*- coding: utf-8 -*-
"""2048 小游戏的服务端：云存档 + 增量同步 + 排行榜 + 每周冠军荆露。

规则核心在 ``minigame_2048.py``（纯函数）；这一层只做持久化、验证编排、
排行榜窗口与结算。**不信任客户端自报的分数/棋盘/身份**：分数一律由服务端
重放得出，账号一律取自会话。

设计要点（对应验收用例 5、7、8、10–14）：

* 一局 = ``(seed, ops)``；库里只存"检查点 + 增量"，验证从检查点重放；
* 幂等：``(game_id, op_index)`` 唯一索引 + ``from_index`` 重叠判定，
  重复批次/乱序批次不会重复计分，也不会把存档改回去；
* 只有**相对该局已验证进度的真实增长**才写新记录（刷新 14 天窗口），
  重复上传同一个分数、纯读取、不加分的移动都不刷新；
* 排行榜每账号一行，先总分降序、再最高方块降序，完全相同并列；
* 结算按 UTC+8 周一 00:00 的**固定截止点**取滚动 14 天窗口，
  奖期行与荆露入账在同一事务里写，``UNIQUE(period_key, user_id)`` 防重复发奖。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import minigame_2048 as g

try:  # 仓库内导入才用 db 层（测试会传自己的连接）
    import db as db_module
except Exception:  # pragma: no cover - 极端环境下只影响默认连接
    db_module = None

GAME_KEY = "2048"
GAME_TITLE = "2048"
CHAMPION_POOL = 300
CHAMPION_MIN_ACCOUNTS = 3
RULES_WINDOW_DAYS = 14
DEFAULT_LEADERBOARD_LIMIT = 100
MAX_SYNC_OPS = 4096
CHECKPOINT_EVERY = 64
CZ_TZ = timezone(timedelta(hours=8))
SYNC_SOURCES = ("online", "offline")
FEATURE_EPOCH_CZ = datetime(2026, 9, 20, 0, 0, tzinfo=CZ_TZ)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS minigame_2048_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    game_uid TEXT NOT NULL UNIQUE,
    seed INTEGER NOT NULL,
    rules_version INTEGER NOT NULL DEFAULT 1,
    save_version INTEGER NOT NULL DEFAULT 1,
    ops TEXT NOT NULL DEFAULT '',
    op_index INTEGER NOT NULL DEFAULT 0,
    checkpoint_index INTEGER NOT NULL DEFAULT 0,
    checkpoint_cells TEXT NOT NULL DEFAULT '[]',
    checkpoint_score INTEGER NOT NULL DEFAULT 0,
    checkpoint_rng_state INTEGER NOT NULL DEFAULT 0,
    score INTEGER NOT NULL DEFAULT 0,
    max_tile INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    reached_2048 INTEGER NOT NULL DEFAULT 0,
    continued INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'online',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_mg2048_games_user ON minigame_2048_games(user_id, status);
CREATE TABLE IF NOT EXISTS minigame_2048_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    game_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    max_tile INTEGER NOT NULL,
    op_index INTEGER NOT NULL,
    rules_version INTEGER NOT NULL,
    verified_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'online',
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mg2048_records_game_op
    ON minigame_2048_records(game_id, op_index);
CREATE INDEX IF NOT EXISTS idx_mg2048_records_window
    ON minigame_2048_records(rules_version, verified_at, score DESC, max_tile DESC);
CREATE TABLE IF NOT EXISTS minigame_2048_periods (
    period_key TEXT PRIMARY KEY,
    cutoff_at TEXT NOT NULL,
    participants INTEGER NOT NULL DEFAULT 0,
    pool INTEGER NOT NULL DEFAULT 0,
    winners_json TEXT NOT NULL DEFAULT '[]',
    amounts_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS minigame_2048_rewards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_key TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(period_key, user_id)
);
CREATE TABLE IF NOT EXISTS minigame_2048_prefs (
    user_id INTEGER PRIMARY KEY,
    decline_invites INTEGER NOT NULL DEFAULT 0,
    show_numbers INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS minigame_2048_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    game_id INTEGER,
    kind TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL
);
"""


def ensure_schema(conn) -> None:
    """幂等建表（``db.init_db`` 会调用；测试用临时库也直接调）。"""

    conn.executescript(SCHEMA_SQL)


def now_iso(now=None) -> str:
    if now is None:
        now = datetime.now(timezone.utc)
    if isinstance(now, str):
        return now
    return now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(text) -> Optional[datetime]:
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _audit(conn, user_id, game_id, kind: str, detail) -> None:
    conn.execute(
        "INSERT INTO minigame_2048_audit (user_id, game_id, kind, detail, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, game_id, str(kind)[:60],
         json.dumps(detail, ensure_ascii=False)[:2000], now_iso()),
    )


# ---------------------------------------------------------------- 权限


def role_name(profile) -> str:
    if not isinstance(profile, dict):
        return ""
    return str(profile.get("role_type") or profile.get("role") or "").strip().lower()


def can_access_minigame(user_id=None, username="") -> bool:
    """内测门槛：**服务端真实角色** staff / admin 才放行（不信客户端自报）。"""

    if db_module is None:
        return False
    identifier = username or user_id
    if not identifier:
        return False
    try:
        profile = db_module.get_user_role_profile(identifier) if username else \
            db_module.get_user_role_profile(user_id)
    except Exception:
        return False
    return role_name(profile) in ("staff", "admin")


# ---------------------------------------------------------------- 存档


def _game_state(row) -> Dict[str, object]:
    if row is None:
        return {}
    return {
        "game_id": int(row["id"]),
        "game_uid": row["game_uid"],
        "user_id": int(row["user_id"]),
        "seed": int(row["seed"]),
        "rules_version": int(row["rules_version"]),
        "save_version": int(row["save_version"]),
        "ops": row["ops"] or "",
        "op_index": int(row["op_index"]),
        "checkpoint_index": int(row["checkpoint_index"]),
        "checkpoint_cells": json.loads(row["checkpoint_cells"] or "[]"),
        "checkpoint_score": int(row["checkpoint_score"]),
        "checkpoint_rng_state": int(row["checkpoint_rng_state"] or 0),
        "score": int(row["score"]),
        "max_tile": int(row["max_tile"]),
        "status": row["status"],
        "reached_2048": bool(row["reached_2048"]),
        "continued": bool(row["continued"]),
        "source": row["source"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _active_game(conn, user_id: int):
    return conn.execute(
        "SELECT * FROM minigame_2048_games WHERE user_id = ? AND status = 'active'"
        " ORDER BY id DESC LIMIT 1",
        (int(user_id),),
    ).fetchone()


def _progress_at(conn, game_id: int) -> Tuple[int, int]:
    """已验证进度 ``(op_index, score)``。"""

    row = conn.execute(
        "SELECT op_index, score FROM minigame_2048_records WHERE game_id = ?"
        " ORDER BY op_index DESC LIMIT 1",
        (int(game_id),),
    ).fetchone()
    if row is None:
        return 0, 0
    return int(row["op_index"]), int(row["score"])


def _replay_state(state: Dict[str, object]) -> Dict[str, object]:
    """按"检查点 + 尾巴"还原当前棋盘。"""

    seed = int(state["seed"])
    checkpoint_index = int(state["checkpoint_index"])
    ops = str(state["ops"])
    tail = ops[checkpoint_index: int(state["op_index"])]
    if checkpoint_index <= 0:
        return g.replay(seed, ops[: int(state["op_index"])])
    cells = list(state["checkpoint_cells"]) or None
    rng_state = int(state["checkpoint_rng_state"] or 0)
    if not cells or not rng_state:                     # 旧档/退化：从种子重放
        return g.replay(seed, ops[: int(state["op_index"])])
    checkpoint = {
        "seed": seed,
        "rng_state": rng_state,
        "cells": cells,
        "score": int(state["checkpoint_score"]),
    }
    return g.replay(seed, tail, start_state=checkpoint)


def create_game(conn, user_id: int, *, seed=None, source: str = "online", now=None,
                game_uid: Optional[str] = None) -> Dict[str, object]:
    """开新局：关闭旧活动局（旧局记录与未同步操作都保留，不被删除）。"""

    source = source if source in SYNC_SOURCES else "online"
    stamp = now_iso(now)
    if seed is None:
        seed = g.seed_from_text(f"{user_id}:{stamp}:{os.urandom(8).hex()}")
    seed_value = g.normalize_seed(seed)
    initial = g.initial_state(seed_value)
    uid = str(game_uid or "").strip() or f"{int(user_id)}-{seed_value:x}"
    # 同一账号拿同一个种子重开时（例如"重新开始"带上同一个客户端种子），
    # 默认 uid 会撞上历史局的 UNIQUE 约束 → 这里补随机后缀，保证每次开新局都是新局。
    if conn.execute("SELECT 1 FROM minigame_2048_games WHERE game_uid = ?", (uid,)).fetchone():
        while True:
            candidate = f"{uid}-{os.urandom(4).hex()}"
            if not conn.execute("SELECT 1 FROM minigame_2048_games WHERE game_uid = ?",
                                (candidate,)).fetchone():
                uid = candidate
                break
    conn.execute(
        "UPDATE minigame_2048_games SET status='closed', closed_at=?, updated_at=?"
        " WHERE user_id=? AND status='active'",
        (stamp, stamp, int(user_id)),
    )
    conn.execute(
        """INSERT INTO minigame_2048_games
           (user_id, game_uid, seed, rules_version, save_version, ops, op_index,
            checkpoint_index, checkpoint_cells, checkpoint_score, checkpoint_rng_state,
            score, max_tile, status, reached_2048, continued, source, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, '', 0, 0, ?, 0, ?, 0, ?, 'active', 0, 0, ?, ?, ?)""",
        (int(user_id), uid, seed_value, g.RULES_VERSION, g.SAVE_VERSION,
         json.dumps(initial["cells"]), int(initial["rng_state"]),
         g.max_tile(initial["cells"]), source, stamp, stamp),
    )
    conn.commit()
    return load_state(conn, user_id)


def _archive_outdated_game(conn, user_id: int, row, *, now=None) -> bool:
    """规则版本升级后作废旧活动局（最省事：不迁移 4×4 棋盘，直接开新局）。

    旧局本身不删：状态改成 closed，审计里留一条 rules_upgraded，
    旧成绩记录也仍按自己的 rules_version 留在库里（不进新榜）。
    """

    if row is None or int(row["rules_version"]) == g.RULES_VERSION:
        return False
    stamp = now_iso(now)
    conn.execute(
        "UPDATE minigame_2048_games SET status='closed', closed_at=?, updated_at=? WHERE id=?",
        (stamp, stamp, int(row["id"])),
    )
    _audit(conn, user_id, int(row["id"]), "rules_upgraded",
           {"from": int(row["rules_version"]), "to": g.RULES_VERSION})
    conn.commit()
    return True


def load_state(conn, user_id: int, *, create: bool = True) -> Dict[str, object]:
    """读当前活动局（没有就开一局）；顺带给出棋盘快照与已验证进度。"""

    row = _active_game(conn, user_id)
    upgraded = _archive_outdated_game(conn, user_id, row)
    if upgraded:
        row = None
    if row is None:
        if not create:
            return {"game": None, "board": None, "verified": {"op_index": 0, "score": 0},
                    "rules_upgraded": upgraded}
        create_game(conn, user_id)
        row = _active_game(conn, user_id)
    state = _game_state(row)
    board = _replay_state(state)
    verified_index, verified_score = _progress_at(conn, state["game_id"])
    return {
        "game": state,
        "board": board,
        "verified": {"op_index": verified_index, "score": verified_score},
        "rules_upgraded": upgraded,
        "prefs": get_prefs(conn, user_id),
        "rules": {
            "protocol_version": g.PROTOCOL_VERSION,
            "rules_version": g.RULES_VERSION,
            "save_version": g.SAVE_VERSION,
            "rarity_table": g.rarity_table_payload(),
        },
    }


def _checkpoint_after_append(conn, state: Dict[str, object], board: Dict[str, object]) -> None:
    op_index = int(state["op_index"])
    if op_index - int(state["checkpoint_index"]) < CHECKPOINT_EVERY:
        return
    conn.execute(
        "UPDATE minigame_2048_games SET checkpoint_index=?, checkpoint_cells=?,"
        " checkpoint_score=?, checkpoint_rng_state=? WHERE id=?",
        (op_index, json.dumps(board["cells"]), int(board["score"]),
         int(board["rng_state"]), int(state["game_id"])),
    )


def _record_progress(conn, state: Dict[str, object], board: Dict[str, object],
                     *, source: str, now=None) -> Optional[Dict[str, object]]:
    """得分相对已验证进度真实增长时写一条新的已验证记录（刷新窗口）。"""

    verified_index, verified_score = _progress_at(conn, state["game_id"])
    score = int(board["score"])
    if score <= verified_score:
        return None
    stamp = now_iso(now)
    cursor = conn.execute(
        """INSERT OR IGNORE INTO minigame_2048_records
           (user_id, game_id, score, max_tile, op_index, rules_version, verified_at, source, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (int(state["user_id"]), int(state["game_id"]), score, int(board["max_tile"]),
         int(state["op_index"]), int(state["rules_version"]), stamp,
         source if source in SYNC_SOURCES else "online", stamp),
    )
    if not cursor.rowcount:
        return None
    return {"score": score, "max_tile": int(board["max_tile"]), "op_index": int(state["op_index"]),
            "verified_at": stamp, "source": source}


def sync_progress(conn, user_id: int, game_uid: str, from_index: int, ops,
                  *, claimed_score=None, claimed_cells=None, source: str = "online",
                  reached_2048: bool = False, continued=None, now=None,
                  new_game: bool = False, seed=None) -> Dict[str, object]:
    """增量同步：从 ``from_index`` 起补操作，服务端重放验证后再落库。

    返回 ``{"status": "ok"|"conflict"|"gap"|"rejected"|"stale_game", ...}``。
    """

    row = _active_game(conn, user_id)
    if _archive_outdated_game(conn, user_id, row, now=now):
        # 规则升级（4×4 → 5×5 + 合并失败）：旧局作废、直接开新局，
        # 客户端拿到 stale_game 后会用返回的新状态继续（本地老档由它自己丢弃）。
        create_game(conn, user_id, now=now)
        fresh = _active_game(conn, user_id)
        return {"status": "stale_game", "rules_upgraded": True,
                "active_game_uid": str(fresh["game_uid"]) if fresh is not None else ""}
    if row is None and new_game and seed is not None and game_uid:
        # 全新账号/没活动局时的离线开局补传：直接按客户端种子建档。
        create_game(conn, user_id, seed=seed, source=source, now=now, game_uid=str(game_uid))
        row = _active_game(conn, user_id)
    if row is None:
        return {"status": "no_game"}
    state = _game_state(row)
    if game_uid and str(game_uid) != str(state["game_uid"]):
        # 离线开局的补传：客户端带着自己的种子和完整操作来，服务端从起点重放验证。
        if new_game and seed is not None:
            create_game(conn, user_id, seed=seed, source=source, now=now, game_uid=str(game_uid))
            row = _active_game(conn, user_id)
            state = _game_state(row)
            _audit(conn, user_id, state["game_id"], "adopt_client_game",
                   {"game_uid": str(game_uid)[:80], "source": source,
                    "seed": int(g.normalize_seed(seed))})
            conn.commit()
        else:
            _audit(conn, user_id, state["game_id"], "stale_game",
                   {"client": str(game_uid)[:80], "active": state["game_uid"]})
            conn.commit()
            return {"status": "stale_game", "active_game_uid": state["game_uid"]}
    text = g.ops_from_list(ops)
    if len(text) > MAX_SYNC_OPS:
        return {"status": "rejected", "reason": f"单批操作超过上限 {MAX_SYNC_OPS}"}
    try:
        from_index = int(from_index)
    except (TypeError, ValueError):
        return {"status": "rejected", "reason": "from_index 必须是整数"}
    server_index = int(state["op_index"])
    if from_index < 0:
        return {"status": "rejected", "reason": "from_index 不能为负"}
    if from_index > server_index:
        return {"status": "gap", "reason": "客户端起点超过服务端进度，请从服务端进度续传",
                "server_index": server_index}
    if from_index < server_index:
        overlap = server_index - from_index
        applied = str(state["ops"])[from_index:server_index]
        if text[:overlap] != applied:
            _audit(conn, user_id, state["game_id"], "conflict",
                   {"from_index": from_index, "client": text[:64], "server": applied[:64]})
            conn.commit()
            return {"status": "conflict", "reason": "与服务器已接受的分支不一致",
                    "server_index": server_index}
        text = text[overlap:]
    baseline = _replay_state(state)
    if text:
        check = g.verify_submission(
            state["seed"], text,
            start_state={"seed": state["seed"], "rng_state": baseline["rng_state"],
                         "cells": baseline["cells"], "score": baseline["score"]},
            claimed_score=claimed_score, claimed_cells=claimed_cells,
        )
        if not check["ok"]:
            _audit(conn, user_id, state["game_id"], "verify_failed",
                   {"reason": check.get("reason"), "from_index": from_index,
                    "ops": text[:64]})
            conn.commit()
            return {"status": "rejected", "reason": check.get("reason") or "验证失败"}
        board = check["result"]
    else:
        board = baseline
    if int(board["score"]) > 10 ** 12:
        return {"status": "rejected", "reason": "分数超出可信范围"}
    if text:
        new_ops = str(state["ops"]) + text
        conn.execute(
            "UPDATE minigame_2048_games SET ops=?, op_index=?, score=?, max_tile=?,"
            " reached_2048=MAX(reached_2048, ?), continued=COALESCE(?, continued), updated_at=?"
            " WHERE id=?",
            (new_ops, int(state["op_index"]) + len(text),
             int(board["score"]), int(board["max_tile"]),
             1 if reached_2048 or int(board["max_tile"]) >= g.ETERNAL_VALUE else 0,
             (1 if continued else 0) if continued is not None else None,
             now_iso(now), int(state["game_id"])),
        )
        state["ops"] = new_ops
        state["op_index"] = int(state["op_index"]) + len(text)
        state["score"] = int(board["score"])
        state["max_tile"] = int(board["max_tile"])
        _checkpoint_after_append(conn, state, board)
    record = _record_progress(conn, state, board, source=source, now=now)
    conn.commit()
    verified_index, verified_score = _progress_at(conn, state["game_id"])
    return {
        "status": "ok",
        "game_uid": state["game_uid"],
        "op_index": int(state["op_index"]),
        "score": int(board["score"]),
        "max_tile": int(board["max_tile"]),
        "cells": board["cells"],
        "rng_state": int(board["rng_state"]),
        "game_over": bool(board.get("game_over")),
        "reached_2048": bool(state["reached_2048"]),
        "verified": {"op_index": verified_index, "score": verified_score},
        "record": record,
        "applied": len(text),
    }


def restart_game(conn, user_id: int, *, seed=None, source: str = "online", now=None) -> Dict[str, object]:
    """重新开始：关旧局、开新局（旧局记录/未同步操作保留）。"""

    return create_game(conn, user_id, seed=seed, source=source, now=now)


# ---------------------------------------------------------------- 偏好


def get_prefs(conn, user_id: int) -> Dict[str, object]:
    row = conn.execute(
        "SELECT * FROM minigame_2048_prefs WHERE user_id = ?", (int(user_id),)
    ).fetchone()
    if row is None:
        return {"decline_invites": False, "show_numbers": False}
    return {"decline_invites": bool(row["decline_invites"]),
            "show_numbers": bool(row["show_numbers"])}


def set_prefs(conn, user_id: int, *, decline_invites=None, show_numbers=None, now=None) -> Dict[str, object]:
    current = get_prefs(conn, user_id)
    decline = current["decline_invites"] if decline_invites is None else bool(decline_invites)
    numbers = current["show_numbers"] if show_numbers is None else bool(show_numbers)
    conn.execute(
        """INSERT INTO minigame_2048_prefs (user_id, decline_invites, show_numbers, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             decline_invites=excluded.decline_invites,
             show_numbers=excluded.show_numbers,
             updated_at=excluded.updated_at""",
        (int(user_id), 1 if decline else 0, 1 if numbers else 0, now_iso(now)),
    )
    conn.commit()
    return get_prefs(conn, user_id)


def prefs_decline_invites(conn, user_id: int) -> bool:
    """邀请处理处用的查询（服务端判定，不靠前端禁用按钮）。"""

    try:
        return bool(get_prefs(conn, user_id)["decline_invites"])
    except Exception:
        return False


# ---------------------------------------------------------------- 排行榜


def _window_bounds(window: str, now=None) -> Tuple[Optional[datetime], Optional[datetime]]:
    if str(window) not in ("14d", "all"):
        raise ValueError("window 只能是 14d 或 all")
    now_dt = parse_iso(now_iso(now))
    if str(window) == "all":
        return None, None
    return now_dt - timedelta(days=RULES_WINDOW_DAYS), now_dt


def _display_name(row) -> str:
    keys = row.keys() if hasattr(row, "keys") else []
    for key in ("display_name", "nickname", "username"):
        if key in keys and row[key]:
            return str(row[key])
    return ""


def leaderboard(conn, *, window: str = "14d", limit: int = DEFAULT_LEADERBOARD_LIMIT,
                now=None, rules_version: int = g.RULES_VERSION) -> Dict[str, object]:
    """滚动 14 天 / 历史最高：每账号一行，总分降序 + 最高方块降序，全同并列。"""

    start, end = _window_bounds(window, now)
    sql = (
        "SELECT r.id, r.user_id, r.game_id, r.score, r.max_tile, r.op_index,"
        " r.verified_at, r.source, r.rules_version, u.username AS username"
        " FROM minigame_2048_records r JOIN users u ON u.id = r.user_id"
        " WHERE r.rules_version = ? AND r.score > 0"
    )
    params: List[object] = [int(rules_version)]
    if start is not None and end is not None:
        sql += " AND r.verified_at >= ? AND r.verified_at < ?"
        params.extend([now_iso(start), now_iso(end)])
    sql += " ORDER BY r.score DESC, r.max_tile DESC, r.id ASC"
    rows = conn.execute(sql, tuple(params)).fetchall()
    best: Dict[int, Dict[str, object]] = {}
    for row in rows:
        user_id = int(row["user_id"])
        if user_id in best:
            continue
        best[user_id] = {
            "user_id": user_id,
            "username": _display_name(row),
            "score": int(row["score"]),
            "max_tile": int(row["max_tile"]),
            "max_rarity": g.rarity_name(int(row["max_tile"])),
            "verified_at": row["verified_at"],
            "game_id": int(row["game_id"]),
            "op_index": int(row["op_index"]),
            "source": row["source"],
        }
    entries = sorted(
        best.values(),
        key=lambda item: (-int(item["score"]), -int(item["max_tile"]), int(item["user_id"])),
    )
    ranked: List[Dict[str, object]] = []
    previous: Optional[Tuple[int, int]] = None
    rank = 0
    for index, item in enumerate(entries, start=1):
        key = (int(item["score"]), int(item["max_tile"]))
        if key != previous:
            rank = index
            previous = key
        entry = dict(item)
        entry["rank"] = rank
        ranked.append(entry)
    safe_limit = max(0, min(int(limit or 0), 500))
    return {
        "window": window,
        "limit": safe_limit,
        "participants": len(ranked),
        "entries": ranked[:safe_limit] if safe_limit else ranked,
    }


def self_entry(conn, user_id: int, *, window: str = "14d", now=None) -> Optional[Dict[str, object]]:
    """自己的名次；榜外也能查到（验收 7）。"""

    table = leaderboard(conn, window=window, limit=0, now=now)
    for item in table["entries"]:
        if int(item["user_id"]) == int(user_id):
            return item
    return None


# ---------------------------------------------------------------- 每周结算


def period_key_for(cutoff: datetime) -> str:
    return "2048-" + cutoff.astimezone(CZ_TZ).strftime("%Y-%m-%d")


def week_cutoffs(now=None, *, start: Optional[datetime] = None) -> List[datetime]:
    """从功能启用到 ``now`` 之间、**已经到点**的 UTC+8 周一 00:00（含补做）。"""

    now_dt = parse_iso(now_iso(now))
    epoch = (start or FEATURE_EPOCH_CZ).astimezone(CZ_TZ)
    cursor = epoch.replace(hour=0, minute=0, second=0, microsecond=0)
    # 对齐到周一（weekday: 周一=0）
    cursor -= timedelta(days=cursor.weekday())
    cutoff = cursor
    out: List[datetime] = []
    while cutoff <= now_dt.astimezone(CZ_TZ):
        if cutoff > epoch:          # 不追发功能启用之前的奖期
            out.append(cutoff)
        cutoff = cutoff + timedelta(days=7)
    return out


def _split_pool(pool: int, winners: List[int]) -> Dict[int, int]:
    """整数均分，余数按稳定账号 ID 顺序发（不改变并列排名）。"""

    if not winners:
        return {}
    base = int(pool) // len(winners)
    remainder = int(pool) - base * len(winners)
    ordered = sorted(int(item) for item in winners)
    amounts = {user_id: base for user_id in ordered}
    for index in range(remainder):
        amounts[ordered[index]] += 1
    return amounts


def _credit_dew(conn, user_id: int, amount: int, *, period_key: str, reason: str,
                now=None) -> bool:
    """荆露入账（与奖期写在同一个事务里）；重复调用不会重复入账。"""

    cursor = conn.execute(
        "INSERT OR IGNORE INTO minigame_2048_rewards (period_key, user_id, amount, created_at)"
        " VALUES (?, ?, ?, ?)",
        (period_key, int(user_id), int(amount), now_iso(now)),
    )
    if not cursor.rowcount:
        return False
    row = conn.execute("SELECT * FROM users WHERE id = ?", (int(user_id),)).fetchone()
    if row is None:
        conn.execute("DELETE FROM minigame_2048_rewards WHERE period_key=? AND user_id=?",
                     (period_key, int(user_id)))
        return False
    free_before = max(0, int(row["thorn_dew_free"] or 0 )) if "thorn_dew_free" in row.keys() else 0
    paid_before = max(0, int(row["thorn_dew_paid"] or 0)) if "thorn_dew_paid" in row.keys() else 0
    free_after = free_before + int(amount)
    conn.execute("UPDATE users SET thorn_dew_free = ? WHERE id = ?", (free_after, int(user_id)))
    conn.execute(
        """INSERT INTO user_currency_transactions
           (user_id, currency, free_delta, paid_delta, reason, source_type, source_id,
            balance_free_after, balance_paid_after, admin_username, created_at)
           VALUES (?, 'thorn_dew', ?, 0, ?, 'minigame_2048_champion', ?, ?, ?, '', ?)""",
        (int(user_id), int(amount), str(reason)[:300], period_key,
         free_after, paid_before, now_iso(now)),
    )
    return True


def settle_due(conn, *, now=None, pool: int = CHAMPION_POOL,
               min_accounts: int = CHAMPION_MIN_ACCOUNTS) -> List[Dict[str, object]]:
    """结算所有已到点的奖期（补做也走同一条路，用**原截止时点**取榜单）。"""

    results: List[Dict[str, object]] = []
    for cutoff in week_cutoffs(now=now):
        period_key = period_key_for(cutoff)
        existing = conn.execute(
            "SELECT * FROM minigame_2048_periods WHERE period_key = ?", (period_key,)
        ).fetchone()
        window = leaderboard(conn, window="14d", limit=0,
                             now=cutoff.astimezone(timezone.utc))
        participants = int(window["participants"])
        winners = [item for item in window["entries"] if item["rank"] == 1] if participants else []
        amounts = _split_pool(int(pool), [item["user_id"] for item in winners]) if winners else {}
        if existing is None:
            status = "pending" if winners else "skipped"
            reason = "" if winners else "窗口内没有达到资格的成绩"
            if winners and participants < int(min_accounts):
                status = "skipped"
                reason = f"有效账号不足 {int(min_accounts)}（当前 {participants}）"
            conn.execute(
                """INSERT OR IGNORE INTO minigame_2048_periods
                   (period_key, cutoff_at, participants, pool, winners_json, amounts_json,
                    status, reason, created_at, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (period_key, now_iso(cutoff.astimezone(timezone.utc)), participants, int(pool),
                 json.dumps([item["user_id"] for item in winners]), json.dumps(amounts),
                 status, reason, now_iso(now), now_iso(now) if status == "skipped" else None),
            )
            existing = conn.execute(
                "SELECT * FROM minigame_2048_periods WHERE period_key = ?", (period_key,)
            ).fetchone()
        if existing is None:
            continue
        if existing["status"] in ("paid", "skipped"):
            results.append({"period_key": period_key, "status": existing["status"],
                            "participants": int(existing["participants"]), "credited": 0})
            continue
        stored_amounts = json.loads(existing["amounts_json"] or "{}")
        credited = 0
        for raw_user_id, amount in stored_amounts.items():
            if _credit_dew(conn, int(raw_user_id), int(amount), period_key=period_key,
                           reason=f"2048 周冠军（{period_key}）", now=now):
                credited += 1
        conn.execute(
            "UPDATE minigame_2048_periods SET status='paid', completed_at=? WHERE period_key=?",
            (now_iso(now), period_key),
        )
        results.append({"period_key": period_key, "status": "paid",
                        "participants": int(existing["participants"]), "credited": credited,
                        "amounts": stored_amounts})
    conn.commit()
    return results


def period_history(conn, limit: int = 12) -> List[Dict[str, object]]:
    rows = conn.execute(
        "SELECT * FROM minigame_2048_periods ORDER BY cutoff_at DESC LIMIT ?",
        (max(1, min(int(limit or 12), 100)),),
    ).fetchall()
    return [
        {
            "period_key": row["period_key"],
            "cutoff_at": row["cutoff_at"],
            "participants": int(row["participants"]),
            "pool": int(row["pool"]),
            "winners": json.loads(row["winners_json"] or "[]"),
            "amounts": json.loads(row["amounts_json"] or "{}"),
            "status": row["status"],
            "reason": row["reason"] or "",
        }
        for row in rows
    ]
