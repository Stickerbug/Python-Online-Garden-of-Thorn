# -*- coding: utf-8 -*-
"""故事模式通关奖励（设计 2026-09-26）。

分数 = 基础分 × 难度乘区 × SL惩罚 × 无SL奖励，1 分 = 1 荆露。

基础分：
- 每通过一个阶段 +100；通过全部 3 阶段额外 +100
- 每打一层精英 +30，每打一层小怪 +10
- 每 5 金币 +1，每有一张卡 +3，每有一个天赋 +5，每有一本附魔书 +10

乘区：
- 难度：easy 0.5 / normal 1.0 / hard 1.5 / lunatic 2.0
- SL 惩罚：Max(100 - 读档次数, 80) / 100（读档次数取 story_runs.manual_load_count）
- 无 SL 奖励：读档次数为 0 时 ×1.5
"""

import json
import math


DIFFICULTY_MULTIPLIERS = {
    'easy': 0.5,
    'normal': 1.0,
    'hard': 1.5,
    'lunatic': 2.0,
}
STORY_STAGES_TOTAL = 3
SL_PENALTY_FLOOR = 80
NO_SL_BONUS = 1.5
POINTS = {
    'stage': 100,
    'all_stages_bonus': 100,
    'elite': 30,
    'normal': 10,
    'gold_per': 5,
    'gold_points': 1,
    'card': 3,
    'talent': 5,
    'enchantment_book': 10,
}


def compute_base_score(state):
    """从旅程终态统计基础分（字段全部来自 state 现有结构）。

    - 阶段：state.stage（已到达的阶段号），3 阶段通关（completed）额外 +100
    - 小怪：state.normal_battles（引擎逐局累加）
    - 精英：state.encounter_history.elite 各区域列表长度之和（遇到一次记一项）
    - 金币：state.player.gold（每 5G +1）
    - 卡：state.player.deck 张数；天赋：state.player.relics（引擎把天赋存 relics）
    - 附魔书：state.player.enchantment_books / state.enchantment_books
    """
    state = state if isinstance(state, dict) else {}
    player = state.get('player') if isinstance(state.get('player'), dict) else {}
    completed = state.get('completed') is True
    stages = int(state.get('stage') or 1)

    # 「每通过一个阶段」：completed 时 stage=已通过的阶段数；未通关时
    # stage 是当前所处阶段（尚未通过），按 stages-1 计。
    score = POINTS['stage'] * max(0, stages if completed else stages - 1)
    if completed and stages >= STORY_STAGES_TOTAL:
        score += POINTS['all_stages_bonus']

    normals = int(state.get('normal_battles') or 0)
    score += POINTS['normal'] * normals

    encounter = state.get('encounter_history') if isinstance(state.get('encounter_history'), dict) else {}
    elite_history = encounter.get('elite') if isinstance(encounter.get('elite'), dict) else {}
    elites = sum(len(v) for v in elite_history.values() if isinstance(v, list))
    score += POINTS['elite'] * elites

    gold = int(player.get('gold') or 0)
    score += (gold // POINTS['gold_per']) * POINTS['gold_points']
    deck = player.get('deck') or []
    score += POINTS['card'] * len(deck)
    talents = player.get('relics') or player.get('talents') or []
    score += POINTS['talent'] * len(talents)
    books = (
        player.get('enchantment_books')
        or state.get('enchantment_books')
        or state.get('books')
        or []
    )
    score += POINTS['enchantment_book'] * len(books)
    return score


def compute_multiplier(load_count):
    load_count = max(0, int(load_count or 0))
    sl_penalty = max(100 - load_count, SL_PENALTY_FLOOR) / 100
    no_sl = NO_SL_BONUS if load_count == 0 else 1.0
    return sl_penalty * no_sl


def compute_score(state, difficulty, load_count):
    base = compute_base_score(state)
    difficulty_mult = DIFFICULTY_MULTIPLIERS.get(str(difficulty or '').lower(), 1.0)
    total = base * difficulty_mult * compute_multiplier(load_count)
    return int(math.floor(total)), int(base)


def settle_story_clear_conn(conn, *, user_id, run_id, state):
    """通关事务内：清银行 → 算分 → 发荆露 → 记账。

    conn 由调用方持有 IMMEDIATE 事务。
    开发模式（#331）：本次旅程用过任何 dev_* 操作则不发荆露——开发模式可以
    直接改金币/塞卡/跳层，正常算分等于无限刷荆露。
    """
    from db import _thorn_dew_now  # noqa: F401  (保持与 db 模块一致的时间源)

    state = state if isinstance(state, dict) else {}
    difficulty = str(state.get('difficulty') or 'normal')
    player = state.get('player') if isinstance(state.get('player'), dict) else {}

    # 1) 银行存款清零（设计：做了这个系统后清除玩家在银行的存款）
    row = conn.execute(
        'SELECT deposit FROM story_bank_accounts WHERE user_id = ?', (int(user_id),),
    ).fetchone()
    bank_before = int(row['deposit'] or 0) if row is not None else 0
    if bank_before > 0:
        conn.execute('UPDATE story_bank_accounts SET deposit = 0 WHERE user_id = ?', (int(user_id),))

    # 2) 读档次数（SL）取 story_runs.manual_load_count
    run_row = conn.execute(
        'SELECT manual_load_count FROM story_runs WHERE id = ?', (str(run_id or ''),),
    ).fetchone()
    load_count = int(run_row['manual_load_count'] or 0) if run_row is not None else 0

    # 2.5) 开发模式检测：旅程动作日志里出现过 dev_* 操作
    dev_row = conn.execute(
        "SELECT COUNT(*) AS n FROM story_run_actions "
        "WHERE run_id = ? AND substr(action_type, 1, 4) = 'dev_'",
        (str(run_id or ''),),
    ).fetchone()
    dev_used = int(dev_row['n'] or 0) > 0 if dev_row is not None else False

    # 3) 分数与荆露（开发模式不发）
    total, base = compute_score(state, difficulty, load_count)
    difficulty_mult = DIFFICULTY_MULTIPLIERS.get(str(difficulty or '').lower(), 1.0)
    if dev_used:
        total = 0
    if total > 0:
        user_row = conn.execute(
            'SELECT thorn_dew_free, thorn_dew_paid FROM users WHERE id = ?', (int(user_id),),
        ).fetchone()
        if user_row is not None:
            free = max(0, int(user_row['thorn_dew_free'] or 0)) + total
            paid = max(0, int(user_row['thorn_dew_paid'] or 0))
            conn.execute('UPDATE users SET thorn_dew_free = ? WHERE id = ?', (free, int(user_id)))
            conn.execute(
                '''
                INSERT INTO user_currency_transactions
                    (user_id, currency, free_delta, paid_delta, reason, source_type, source_id,
                     balance_free_after, balance_paid_after, admin_username, created_at)
                VALUES (?, 'thorn_dew', ?, 0, ?, 'story_clear', ?, ?, ?, '', datetime('now'))
                ''',
                (
                    int(user_id), total,
                    f'故事通关奖励 难度{difficulty}×{difficulty_mult:g} 基础{base} SL×{compute_multiplier(load_count):g}',
                    f'story:{run_id}',
                    free, paid,
                ),
            )

    # 4) 分数留档（神秘人物事件用：伤害 = 本次得分）
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS story_reward_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            run_id TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            base_score INTEGER NOT NULL,
            total_score INTEGER NOT NULL,
            load_count INTEGER NOT NULL,
            bank_cleared INTEGER NOT NULL DEFAULT 0,
            dev_used INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        ''',
    )
    # 旧库补列（#331 上线时生产库已存在该表）
    try:
        conn.execute('ALTER TABLE story_reward_ledger ADD COLUMN dev_used INTEGER NOT NULL DEFAULT 0')
    except Exception:
        pass  # 列已存在
    conn.execute(
        '''
        INSERT INTO story_reward_ledger
            (user_id, run_id, difficulty, base_score, total_score, load_count, bank_cleared, dev_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            int(user_id), str(run_id or ''), difficulty,
            int(base), int(total), int(load_count), 1 if bank_before > 0 else 0,
            1 if dev_used else 0,
        ),
    )
    return {
        'total': total,
        'base': base,
        'difficulty': difficulty,
        'load_count': load_count,
        'bank_cleared': bank_before,
        'dev_used': dev_used,
    }
