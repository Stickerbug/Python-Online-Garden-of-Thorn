# -*- coding: utf-8 -*-
"""休闲花园 ·「合成大花花」的存档 / 同步 / 榜单 / 周奖。

和 2048 的关键差别：**这是物理游戏，服务端没法逐位重放**（matter.js 跑在浏览器里，
线上服务器也没有 node）。所以这里走"每次分数变化立刻落库 + 启发式校验"：

- 客户端每颗球落定、每次分数增加就上报 `{drop_index, 新增投放, 新总分}`；
- 服务端**立刻保存**（这就是用户要的"直接存分数"，云端存档不丢）；
- 同时用启发式规则判断这条成绩能不能进榜：分数只增不减、单批增量不超过
  "投放数 × 单次上限"、投放间隔不小于 400ms、总分不超过上限；
- 通过 → 写入 `minigame_2048_records`（`game_key='suika'`）计入 14 天滚动榜；
  不通过 → 只存进度，返回 `verified=False`，客户端提示"未通过验证，未计入排行榜"，
  **本地进度保留**，不删档；
- 存档格式仍是 `种子 + 投放序列`，以后服务器装了 node 就能直接升级成完整重放校验。

榜单 / 奖期 / 荆露入账全部复用 2048 那套（`minigame_2048_service`），靠 `game_key`
与 `suika-YYYY-MM-DD` 奖期前缀分账，不额外加表。
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional

import minigame_2048_service as base

GAME_KEY = "suika"
RULES_VERSION = 1
SAVE_VERSION = 1

# 启发式校验阈值（宁可宽一点，避免误伤合法长局；异常量级才拒绝）
MIN_DROP_INTERVAL_MS = 400          # 投放冷却 500ms，留一点抖动余量
MAX_GAIN_PER_DROP = 66 * 4          # 一次投放理论上最多连锁合成出的分数上限（留 4 倍余量）
MAX_TOTAL_SCORE = 10_000_000
MAX_DROPS_PER_SYNC = 4096

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS minigame_suika_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    game_uid TEXT NOT NULL UNIQUE,
    seed INTEGER NOT NULL,
    rules_version INTEGER NOT NULL DEFAULT 1,
    save_version INTEGER NOT NULL DEFAULT 1,
    drops TEXT NOT NULL DEFAULT '[]',
    drop_index INTEGER NOT NULL DEFAULT 0,
    score INTEGER NOT NULL DEFAULT 0,
    max_tier INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    source TEXT NOT NULL DEFAULT 'online',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_mg_suika_games_user ON minigame_suika_games(user_id, status);
"""


def ensure_schema(conn) -> None:
    """建表 + 给共用记录表补 `game_key`（纯增量，老数据默认 '2048'，不影响现有榜单）。"""

    base.ensure_schema(conn)
    conn.executescript(SCHEMA_SQL)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(minigame_2048_records)").fetchall()}
    if "game_key" not in columns:
        conn.execute("ALTER TABLE minigame_2048_records ADD COLUMN game_key TEXT NOT NULL DEFAULT '2048'")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mg_records_game_window"
        " ON minigame_2048_records(game_key, rules_version, verified_at, score DESC, max_tile DESC)"
    )
    conn.commit()


def _game_state(row) -> Optional[Dict[str, object]]:
    if row is None:
        return None
    try:
        drops = json.loads(row["drops"] or "[]")
    except Exception:
        drops = []
    return {
        "game_id": int(row["id"]),
        "game_uid": row["game_uid"],
        "user_id": int(row["user_id"]),
        "seed": int(row["seed"]),
        "rules_version": int(row["rules_version"]),
        "save_version": int(row["save_version"]),
        "drops": drops,
        "drop_index": int(row["drop_index"]),
        "score": int(row["score"]),
        "max_tier": int(row["max_tier"]),
        "status": row["status"],
        "source": row["source"],
        "updated_at": row["updated_at"],
    }


def _active_game(conn, user_id: int):
    return conn.execute(
        "SELECT * FROM minigame_suika_games WHERE user_id = ? AND status = 'active'"
        " ORDER BY id DESC LIMIT 1",
        (int(user_id),),
    ).fetchone()


def _make_uid(user_id: int, now=None) -> str:
    import uuid
    return f"suika-{int(user_id)}-{uuid.uuid4().hex[:16]}"


def create_game(conn, user_id: int, *, seed: int = 1, source: str = "online", now=None) -> Dict[str, object]:
    stamp = base.now_iso(now)
    uid = _make_uid(user_id, now)
    conn.execute(
        "INSERT INTO minigame_suika_games"
        " (user_id, game_uid, seed, rules_version, save_version, drops, drop_index, score, max_tier,"
        "  status, source, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, '[]', 0, 0, 0, 'active', ?, ?, ?)",
        (int(user_id), uid, int(seed) & 0xFFFFFFFF, RULES_VERSION, SAVE_VERSION,
         source if source in base.SYNC_SOURCES else "online", stamp, stamp),
    )
    conn.commit()
    return _game_state(_active_game(conn, user_id))


def load_state(conn, user_id: int, *, source: str = "online", seed: int = 1, now=None) -> Dict[str, object]:
    ensure_schema(conn)
    row = _active_game(conn, user_id)
    if row is None:
        return create_game(conn, user_id, seed=seed, source=source, now=now)
    return _game_state(row)


def restart_game(conn, user_id: int, *, seed: int = 1, source: str = "online", now=None) -> Dict[str, object]:
    ensure_schema(conn)
    stamp = base.now_iso(now)
    conn.execute(
        "UPDATE minigame_suika_games SET status = 'closed', closed_at = ?, updated_at = ?"
        " WHERE user_id = ? AND status = 'active'",
        (stamp, stamp, int(user_id)),
    )
    conn.commit()
    return create_game(conn, user_id, seed=seed, source=source, now=now)


def _normalize_drops(raw) -> List[Dict[str, float]]:
    out: List[Dict[str, float]] = []
    for item in (raw if isinstance(raw, list) else []):
        if isinstance(item, dict):
            t, x = item.get("t"), item.get("x")
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            t, x = item[0], item[1]
        else:
            raise ValueError("投放记录格式不对")
        try:
            time_ms = float(t)
            pos = float(x)
        except (TypeError, ValueError):
            raise ValueError("投放记录不是数字")
        if not (0 <= time_ms <= 24 * 3600 * 1000) or not (0 <= pos <= 4096):
            raise ValueError("投放记录超出范围")
        out.append({"t": round(time_ms, 1), "x": round(pos, 2)})
    return out


def _verify_batch(existing: List[Dict[str, float]], incoming: List[Dict[str, float]],
                  previous_score: int, claimed_score: int) -> tuple:
    """返回 (是否通过, 原因)。只做量级与节奏判断，不做物理重放。"""

    if claimed_score < previous_score:
        return False, "分数不能回退"
    if claimed_score > MAX_TOTAL_SCORE:
        return False, "分数超出合理上限"
    gain = int(claimed_score) - int(previous_score)
    if gain > len(incoming) * MAX_GAIN_PER_DROP:
        return False, "单批分数增长过快"
    merged = list(existing) + list(incoming)
    for index in range(1, len(merged)):
        gap = float(merged[index]["t"]) - float(merged[index - 1]["t"])
        if gap < MIN_DROP_INTERVAL_MS:
            return False, "投放间隔过短"
    return True, ""


def sync_progress(conn, user_id: int, game_uid: str, from_index: int, drops,
                  *, claimed_score=None, claimed_max_tier=None, source: str = "online",
                  now=None) -> Dict[str, object]:
    """把"这一批新增投放 + 新的总分"立刻落库，并按启发式判断能不能计入榜单。"""

    ensure_schema(conn)
    row = _active_game(conn, user_id)
    if row is None or str(row["game_uid"]) != str(game_uid):
        return {"status": "stale_game", "game": load_state(conn, user_id, source=source, now=now)}
    state = _game_state(row)
    start = int(from_index or 0)
    if start > int(state["drop_index"]):
        return {"status": "gap", "expected_index": int(state["drop_index"]), "game": state}
    try:
        incoming = _normalize_drops(drops)
    except ValueError as exc:
        return {"status": "rejected", "reason": str(exc), "game": state}
    if len(incoming) > MAX_DROPS_PER_SYNC:
        return {"status": "rejected", "reason": "一次同步的投放太多", "game": state}

    previous_drops = list(state["drops"])
    if start > len(previous_drops):
        return {"status": "gap", "expected_index": len(previous_drops), "game": state}
    kept = previous_drops[:start]                     # 只认服务端确认过的前缀
    score = int(claimed_score if claimed_score is not None else state["score"])
    max_tier = int(claimed_max_tier if claimed_max_tier is not None else state["max_tier"])
    max_tier = max(0, min(10, max_tier))
    ok, reason = _verify_batch(kept, incoming, int(state["score"]), score)

    stamp = base.now_iso(now)
    # 校验不通过时**连投放也不收**：否则这条异常记录会留在序列里，
    # 之后每一批都会因为"间隔过短"被判不通过，整局再也进不了榜。
    merged = kept + (incoming if ok else [])
    # 投放序列照存（云端存档不丢），但**分数只有校验通过才抬上去**：
    # 被污染的分数如果写进存档，后面的合法上报会被判成"分数回退"，整局都再也进不了榜。
    next_score = int(score) if ok else int(state["score"])
    next_max_tier = int(max_tier) if ok else int(state["max_tier"])
    conn.execute(
        "UPDATE minigame_suika_games SET drops = ?, drop_index = ?, score = ?, max_tier = ?,"
        " source = ?, updated_at = ? WHERE id = ?",
        (json.dumps(merged, separators=(",", ":")), len(merged), next_score,
         next_max_tier, source if source in base.SYNC_SOURCES else "online", stamp, int(state["game_id"])),
    )
    verified_score = None
    if ok:
        verified_row = conn.execute(
            "SELECT MAX(score) AS best FROM minigame_2048_records WHERE game_id = ? AND game_key = ?",
            (int(state["game_id"]), GAME_KEY),
        ).fetchone()
        best = int((verified_row["best"] if verified_row and verified_row["best"] is not None else 0))
        if int(score) > best:
            conn.execute(
                """INSERT OR IGNORE INTO minigame_2048_records
                   (user_id, game_id, score, max_tile, op_index, rules_version, verified_at, source, created_at, game_key)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (int(user_id), int(state["game_id"]), int(score), max_tier, len(merged),
                 RULES_VERSION, stamp, source if source in base.SYNC_SOURCES else "online", stamp, GAME_KEY),
            )
            verified_score = int(score)
    conn.commit()
    fresh = _game_state(_active_game(conn, user_id))
    return {
        "status": "ok",
        "verified": bool(ok),
        "reason": reason,
        "verified_score": verified_score,
        "game": fresh,
    }


# ---------------------------------------------------------------- 榜单 / 周奖（复用 2048 那套）


def leaderboard(conn, *, window: str = "14d", limit: int = base.DEFAULT_LEADERBOARD_LIMIT, now=None):
    ensure_schema(conn)
    return base.leaderboard(conn, window=window, limit=limit, now=now,
                            rules_version=RULES_VERSION, game_key=GAME_KEY)


def self_entry(conn, user_id: int, *, window: str = "14d", now=None):
    ensure_schema(conn)
    return base.self_entry(conn, user_id, window=window, now=now, game_key=GAME_KEY)


def period_history(conn, limit: int = 12):
    ensure_schema(conn)
    return base.period_history(conn, limit=limit, game_key=GAME_KEY)


def settle_due(conn, *, now=None, pool: int = base.CHAMPION_POOL,
               min_accounts: int = base.CHAMPION_MIN_ACCOUNTS):
    ensure_schema(conn)
    return base.settle_due(conn, now=now, pool=pool, min_accounts=min_accounts, game_key=GAME_KEY)
