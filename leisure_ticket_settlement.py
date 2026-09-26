# -*- coding: utf-8 -*-
"""休闲花园游玩期奖励：按本期内最高合成档位发荆露（每会话每档只发一次）。

档位（设计 2026-09-26）：
- 2048（CE）：Eternal(2048)→2000，Unique(1024)→500，Omega(512)→50 荆露
- suika（CF）：Player(第10档)→1000，Mecha Flower(第9档)→250，Shiny Ladybug(第8档)→50 荆露
- 「本局达到过的最高档」：不要求存活到结算。
- 发放走 thorn_dew_free 流水（reason 标注休闲花园）。
"""

import db

# 2048：方块值 -> (奖励荆露, 渠道档位名)。数值取自 minigame_2048.RARITY_TABLE。
CE_TIER_REWARDS = (
    (2048, 2000, 'Eternal'),
    (1024, 500, 'Unique'),
    (512, 50, 'Omega'),
)

# suika：档位下标 -> (奖励荆露, 渠道档位名)。下标对应 suika_core.TIERS（0 起）。
CF_TIER_REWARDS = (
    (10, 1000, 'Player'),
    (9, 250, 'Mecha Flower'),
    (8, 50, 'Shiny Ladybug'),
)


def _grant_dew(conn, user_id, amount, reason):
    row = conn.execute(
        'SELECT thorn_dew_free, thorn_dew_paid FROM users WHERE id = ?', (int(user_id),),
    ).fetchone()
    if row is None:
        return False
    free = max(0, int(row['thorn_dew_free'] or 0)) + int(amount)
    paid = max(0, int(row['thorn_dew_paid'] or 0))
    conn.execute('UPDATE users SET thorn_dew_free = ? WHERE id = ?', (free, int(user_id)))
    conn.execute(
        '''
        INSERT INTO user_currency_transactions
            (user_id, currency, free_delta, paid_delta, reason, source_type, source_id,
             balance_free_after, balance_paid_after, admin_username, created_at)
        VALUES (?, 'thorn_dew', ?, 0, ?, 'leisure_reward', ?, ?, ?, '', datetime('now'))
        ''',
        (int(user_id), int(amount), reason, f'leisure:{reason}', free, paid),
    )
    return True


def _table(conn):
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS leisure_play_sessions (
            user_id INTEGER PRIMARY KEY,
            started_at TEXT NOT NULL,
            elapsed_seconds REAL NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            best_score_ce INTEGER NOT NULL DEFAULT 0,
            best_tier_ce INTEGER NOT NULL DEFAULT 0,
            best_score_cf INTEGER NOT NULL DEFAULT 0,
            best_tier_cf INTEGER NOT NULL DEFAULT 0,
            rewards_granted TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        )
        ''',
    )


def record_result_and_grant(user_id, game_key, score, best_tier):
    """记录成绩；若本会话首次达到某奖励档则发放对应荆露。返回发放摘要。"""
    score = max(0, int(score or 0))
    best_tier = max(0, int(best_tier or 0))
    is_ce = str(game_key or '') == '2048'
    rewards = CE_TIER_REWARDS if is_ce else CF_TIER_REWARDS
    granted_list = []
    with db.get_db_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        _table(conn)
        row = conn.execute(
            'SELECT * FROM leisure_play_sessions WHERE user_id = ?', (int(user_id),),
        ).fetchone()
        if row is None:
            conn.rollback()
            return {'granted': [], 'recorded': False}
        score_col = 'best_score_ce' if is_ce else 'best_score_cf'
        tier_col = 'best_tier_ce' if is_ce else 'best_tier_cf'
        old_score = int(row[score_col] or 0)
        old_tier = int(row[tier_col] or 0)
        conn.execute(
            f'UPDATE leisure_play_sessions SET {score_col} = ?, {tier_col} = ?, updated_at = datetime(\'now\') WHERE user_id = ?',
            (max(score, old_score), max(best_tier, old_tier), int(user_id)),
        )
        already = set(str(row['rewards_granted'] or '').split(',')) - {''}
        game_tag = 'ce' if is_ce else 'cf'
        for tier_value, amount, tier_name in rewards:
            reached = best_tier >= tier_value if is_ce else best_tier >= tier_value
            key = f'{game_tag}:{tier_value}'
            if not reached or key in already:
                continue
            reason = f'休闲花园奖励 {tier_name}'
            if _grant_dew(conn, user_id, amount, reason):
                already.add(key)
                granted_list.append({'tier': tier_name, 'tier_value': tier_value, 'amount': amount})
        conn.execute(
            'UPDATE leisure_play_sessions SET rewards_granted = ?, updated_at = datetime(\'now\') WHERE user_id = ?',
            (','.join(sorted(already)), int(user_id)),
        )
        conn.commit()
    return {'granted': granted_list, 'recorded': True}
