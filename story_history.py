# -*- coding: utf-8 -*-
"""故事模式「旅程历史」（设计 2026-10-09）：玩家自查过往旅程。

数据分两层：
- ``story_run_summaries``：列表页专用摘要（结束/弃局时写入，幂等），
  避免为了一个列表去解析几百 KB 的 ``story_runs.state_json``；
- 详情不重复存：直接读 ``story_runs`` 里结束时刻的完整状态快照
  （最终卡组 / 遗物 / 地图路线都在里面），现解析现返回。

写入时机（见 db.py 挂钩）：
- 通关（phase=complete 且 completed=True）→ result='victory'；
- 弃局（abandon_story_run）→ 按快照 phase 区分 result='defeat'（game_over）
  或 'abandoned'。
不设历史上限（对齐杀戮尖塔2 的教训：删旧局是差评重灾区）。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS story_run_summaries (
    run_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    result TEXT NOT NULL CHECK(result IN ('victory', 'defeat', 'abandoned')),
    character_id TEXT NOT NULL DEFAULT 'common_flower',
    difficulty TEXT NOT NULL DEFAULT 'normal',
    journey_mode TEXT NOT NULL DEFAULT 'standard',
    stage_reached INTEGER NOT NULL DEFAULT 1,
    floor_reached INTEGER NOT NULL DEFAULT 1,
    biome TEXT NOT NULL DEFAULT 'garden',
    health INTEGER NOT NULL DEFAULT 0,
    max_health INTEGER NOT NULL DEFAULT 0,
    gold INTEGER NOT NULL DEFAULT 0,
    deck_size INTEGER NOT NULL DEFAULT 0,
    upgrade_count INTEGER NOT NULL DEFAULT 0,
    relic_count INTEGER NOT NULL DEFAULT 0,
    seed TEXT NOT NULL DEFAULT '',
    content_version TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL DEFAULT '',
    ended_at TEXT NOT NULL DEFAULT '',
    duration_seconds INTEGER NOT NULL DEFAULT 0
)
"""

_SUMMARY_COLUMNS = (
    'run_id', 'user_id', 'result', 'character_id', 'difficulty', 'journey_mode',
    'stage_reached', 'floor_reached', 'biome', 'health', 'max_health', 'gold',
    'deck_size', 'upgrade_count', 'relic_count', 'seed', 'content_version',
    'started_at', 'ended_at', 'duration_seconds',
)


def _create_tables(conn) -> None:
    """建表与索引（不提交——调用方负责事务边界）。"""

    conn.execute(SCHEMA_SQL)
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_story_summaries_user_ended '
        'ON story_run_summaries(user_id, ended_at DESC)'
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_story_summaries_user_result '
        'ON story_run_summaries(user_id, result)'
    )


def ensure_schema(conn) -> None:
    _create_tables(conn)
    conn.commit()


def _parse_iso(text) -> Optional[datetime]:
    try:
        value = datetime.fromisoformat(str(text or '').replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


def _summary_from_state(run_id, user_id, state, *, started_at, ended_at, result) -> Dict[str, object]:
    state = state if isinstance(state, dict) else {}
    player = state.get('player') if isinstance(state.get('player'), dict) else {}
    deck = player.get('deck') if isinstance(player.get('deck'), list) else []
    relics = player.get('relics') if isinstance(player.get('relics'), list) else []
    started = _parse_iso(started_at)
    ended = _parse_iso(ended_at)
    duration = int((ended - started).total_seconds()) if started and ended and ended > started else 0
    return {
        'run_id': str(run_id),
        'user_id': int(user_id),
        'result': result,
        'character_id': str(state.get('character_id') or 'common_flower'),
        'difficulty': str(state.get('difficulty') or 'normal'),
        'journey_mode': str(state.get('journey_mode') or 'standard'),
        'stage_reached': int(state.get('stage') or 1),
        'floor_reached': int(state.get('current_floor') or 1),
        'biome': str(state.get('biome') or 'garden'),
        'health': int(player.get('health') or 0),
        'max_health': int(player.get('max_health') or 0),
        'gold': int(player.get('gold') or 0),
        'deck_size': len(deck),
        'upgrade_count': sum(1 for card in deck if isinstance(card, dict) and card.get('upgraded')),
        'relic_count': len(relics),
        'seed': str(state.get('journey_seed') or ''),
        'content_version': str(state.get('content_version') or ''),
        'started_at': str(started_at or ''),
        'ended_at': str(ended_at or ''),
        'duration_seconds': duration,
    }


def record_run_summary_conn(conn, run_id, user_id, state, *, started_at, ended_at, result) -> bool:
    """写入/覆盖一条旅程摘要。调用方负责事务与 commit；幂等（主键=run_id）。"""

    if result not in ('victory', 'defeat', 'abandoned'):
        return False
    _create_tables(conn)
    summary = _summary_from_state(
        run_id, user_id, state,
        started_at=started_at, ended_at=ended_at, result=result,
    )
    conn.execute(
        'INSERT OR REPLACE INTO story_run_summaries ({columns}) VALUES ({marks})'.format(
            columns=', '.join(_SUMMARY_COLUMNS),
            marks=', '.join(['?'] * len(_SUMMARY_COLUMNS)),
        ),
        tuple(summary[column] for column in _SUMMARY_COLUMNS),
    )
    return True


def _row_to_summary(row) -> Dict[str, object]:
    return {column: row[column] for column in _SUMMARY_COLUMNS}


def list_history(conn, user_id, *, limit=20, result=None, character_id=None) -> List[Dict[str, object]]:
    """玩家自己的旅程历史列表（ended_at 倒序）。"""

    _create_tables(conn)
    clauses = ['user_id = ?']
    params = [int(user_id)]
    if result in ('victory', 'defeat', 'abandoned'):
        clauses.append('result = ?')
        params.append(result)
    if character_id:
        clauses.append('character_id = ?')
        params.append(str(character_id))
    params.append(max(1, min(100, int(limit))))
    rows = conn.execute(
        f"SELECT * FROM story_run_summaries WHERE {' AND '.join(clauses)} "
        'ORDER BY ended_at DESC, run_id DESC LIMIT ?',
        params,
    ).fetchall()
    return [_row_to_summary(row) for row in rows]


def get_history_detail(conn, user_id, run_id) -> Optional[Dict[str, object]]:
    """单局详情：摘要 + 结束快照里的最终卡组 / 遗物 / 地图与路线统计。"""

    _create_tables(conn)
    summary_row = conn.execute(
        'SELECT * FROM story_run_summaries WHERE run_id = ? AND user_id = ? LIMIT 1',
        (str(run_id), int(user_id)),
    ).fetchone()
    if summary_row is None:
        return None
    run_row = conn.execute(
        'SELECT state_json FROM story_runs WHERE id = ? AND user_id = ? LIMIT 1',
        (str(run_id), int(user_id)),
    ).fetchone()
    state = {}
    if run_row is not None:
        try:
            state = json.loads(run_row['state_json'] or '{}')
        except (TypeError, ValueError, json.JSONDecodeError):
            state = {}
    player = state.get('player') if isinstance(state.get('player'), dict) else {}
    deck = [
        {
            'def_id': str(card.get('def_id') or ''),
            'upgraded': bool(card.get('upgraded')),
        }
        for card in (player.get('deck') or [])
        if isinstance(card, dict) and card.get('def_id')
    ]
    relics = [str(item) for item in (player.get('relics') or []) if item]
    story_map = state.get('map') if isinstance(state.get('map'), dict) else {}
    visited = []
    current_node_id = str(state.get('current_node_id') or '')
    for floor in story_map.get('floors') or []:
        for node in floor.get('nodes') or []:
            if not isinstance(node, dict):
                continue
            if node.get('status') == 'completed':
                visited.append({
                    'floor': int(node.get('floor') or 0),
                    'type': str(node.get('type') or 'unknown'),
                    'final': False,
                })
    visited.sort(key=lambda item: item['floor'])
    # 终点（战败/结束所在节点）：若尚未计入（房间没打完），补在末尾并标记。
    if current_node_id and not any(
        node.get('id') == current_node_id
        for floor in story_map.get('floors') or []
        for node in (floor.get('nodes') or [])
        if isinstance(node, dict) and node.get('status') == 'completed'
    ):
        for floor in story_map.get('floors') or []:
            for node in floor.get('nodes') or []:
                if isinstance(node, dict) and str(node.get('id') or '') == current_node_id:
                    visited.append({
                        'floor': int(node.get('floor') or 0),
                        'type': str(node.get('type') or 'unknown'),
                        'final': True,
                    })
                    break
    return {
        'summary': _row_to_summary(summary_row),
        'deck': deck,
        'relics': relics,
        'map': {
            'floors': story_map.get('floors') or [],
            'edges': story_map.get('edges') or [],
            'current_node_id': str(state.get('current_node_id') or ''),
        },
        'route': {
            'completed_nodes': sum(1 for item in visited if not item['final']),
            'visited': visited,
        },
    }
