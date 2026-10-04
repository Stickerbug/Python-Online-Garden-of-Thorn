# -*- coding: utf-8 -*-
"""段位系统（设计 2026-10-02）。

花阶分（GR/ELO）继续在后台运行但不再对玩家展示；玩家看到的是段位：
11 个大段（Craft Eternal 稀有度顺序）× 4 个小段（basic/sewage/disc/
golden nazar，由低到高）共 44 个段位。段位分只在 0 与该段上限之间变动；
到上限后再两连胜升段，到 0 后再败一局降段。

本模块只放纯函数与常量；数据库读写与结算 worker 在 db.py / app.py。
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

# Craft Eternal 稀有度顺序（minigame_2048.RARITY_TABLE 同序），低 → 高。
MAJOR_TIERS: Tuple[str, ...] = (
    'common', 'unusual', 'rare', 'epic', 'legendary', 'mythic',
    'ultra', 'super', 'omega', 'unique', 'eternal',
)
# 小段由低到高；图标用同名卡面（Basic/Sewage/Disc/GoldenNazar）。
SUB_TIERS: Tuple[str, ...] = ('basic', 'sewage', 'disc', 'golden_nazar')

RANK_COUNT = len(MAJOR_TIERS) * len(SUB_TIERS)          # 44

# 各大段的段位分上限；未列出的默认 _DEFAULT_CAP。
_MAJOR_CAPS: Dict[str, int] = {
    'common': 20,
    'unusual': 30,
    'rare': 50,
    'epic': 100,
    'legendary': 200,
    'mythic': 200,
    'ultra': 200,
    'super': 200,
    'omega': 200,
    'unique': 500,
    'eternal': 1000,
}
_DEFAULT_CAP = 200

WIN_BASE = 5
LOSS_BASE = 3
MIN_CHANGE = 1
MAX_WIN = 10     # 平衡 2026-10-02：胜利加分上限（封顶后再吃倍率）
MAX_LOSS = 5     # 失败扣分上限
DAILY_DOUBLE_GAMES = 5      # 每日前 5 局计分对局，胜利加分翻倍
BEIJING_TZ_OFFSET_HOURS = 8

# 存量换算：当前赛季花阶分 → 初始段位。
# 1000（初始分）= common basic 0 分；每高出 10 分升 1 个小段；零头按比例
# 折成段位分；不足 1000 一律 common basic 0 分。
MIGRATION_GR_BASELINE = 1000.0
MIGRATION_GR_PER_SUBTIER = 10.0

# 重算 2026-10-04：花阶分直线换算 + 小段行进成本。
# P = (花阶分 − 800) × 4；小段 k（1 基）在 P 空间的起点 =
# 阶梯累计分 start(k) + 10 × (k−1)——即每升过一个小段，P 要多付 10 分。
# 落位小段 k* 后的段位分 = P − 起点(k*)。与 2026-10-04 逐档样表
# （800→Common Basic 0/20 … 1300→Mythic Basic 200/200）全部吻合。
RECALC_GR_BASELINE = 800.0
RECALC_GR_SLOPE = 4.0
RECALC_SUBTIER_COST = 10.0


def _ladder_starts() -> List[int]:
    """前缀和：start[k] = 小段 k 的阶梯起点分（1 基，start[1] = 0）。

    惰性初始化：rank_cap 定义在本文件更靠后的位置。
    """
    global _LADDER_STARTS
    if _LADDER_STARTS is not None:
        return _LADDER_STARTS
    starts = [0] * (RANK_COUNT + 1)
    for tier_index in range(2, RANK_COUNT + 1):
        starts[tier_index] = starts[tier_index - 1] + rank_cap(tier_index - 1)
    _LADDER_STARTS = starts
    return starts


_LADDER_STARTS = None


def ladder_start(tier_index: int) -> int:
    """小段 k 的阶梯起点分（该段 0 分对应的绝对段位分）。"""
    return _ladder_starts()[clamp_tier(tier_index)]


def ladder_total() -> int:
    """整个 44 段天梯的满分（绝对段位分上限）。"""
    starts = _ladder_starts()
    return starts[RANK_COUNT] + rank_cap(RANK_COUNT)


def absolute_to_tier(absolute_points: int) -> Tuple[int, int]:
    """绝对段位分 → (段位序号, 段内分)。"""
    starts = _ladder_starts()
    ceiling = starts[RANK_COUNT] + rank_cap(RANK_COUNT)
    value = max(0, min(ceiling, int(absolute_points or 0)))
    for tier_index in range(1, RANK_COUNT + 1):
        cap = rank_cap(tier_index)
        if value < starts[tier_index] + cap or tier_index == RANK_COUNT:
            return tier_index, value - starts[tier_index]
    return RANK_COUNT, rank_cap(RANK_COUNT)


def tier_to_absolute(tier_index: int, points: int) -> int:
    """(段位序号, 段内分) → 绝对段位分。"""
    tier_index = clamp_tier(tier_index)
    points = max(0, min(rank_cap(tier_index), int(points or 0)))
    return _ladder_starts()[tier_index] + points


def recalc_from_gr(season_gr: float) -> Tuple[int, int]:
    """2026-10-04 重算口径：花阶分 → (段位序号, 段内分)。

    P = (花阶分 − 800) × 4，向下取整到 0；小段 k 在 P 空间占据
    [start(k) + 10×(k−1), start(k) + 10×(k−1) + cap(k))。
    """
    try:
        gr = float(season_gr or 0.0)
    except (TypeError, ValueError):
        gr = 0.0
    starts = _ladder_starts()
    total = max(0, int(round((gr - RECALC_GR_BASELINE) * RECALC_GR_SLOPE)))
    cost = int(RECALC_SUBTIER_COST)
    for tier_index in range(1, RANK_COUNT + 1):
        offset = starts[tier_index] + cost * (tier_index - 1)
        cap = rank_cap(tier_index)
        if tier_index == RANK_COUNT:
            return tier_index, max(0, min(cap, total - offset))
        next_offset = starts[tier_index + 1] + cost * tier_index
        # 边界看下一段的调整起点：本段与本段满分之间的空隙按满段处理
        # （样表：ELO 1300 → P 2000 = mythic basic 200/200，而非 sewage 0）。
        if total < next_offset:
            return tier_index, max(0, min(cap, total - offset))
    return RANK_COUNT, rank_cap(RANK_COUNT)


def decompose(tier_index: int) -> Tuple[int, int]:
    """1 基段位序号 → (大段下标, 小段下标)，均 0 基。"""
    tier_index = int(tier_index)
    if not 1 <= tier_index <= RANK_COUNT:
        raise ValueError(f'段位序号必须在 1-{RANK_COUNT} 之间：{tier_index}')
    return divmod(tier_index - 1, len(SUB_TIERS))


def compose(major_i: int, sub_i: int) -> int:
    """(大段下标, 小段下标) → 1 基段位序号。"""
    if not 0 <= major_i < len(MAJOR_TIERS):
        raise ValueError(f'大段下标越界：{major_i}')
    if not 0 <= sub_i < len(SUB_TIERS):
        raise ValueError(f'小段下标越界：{sub_i}')
    return major_i * len(SUB_TIERS) + sub_i + 1


def clamp_tier(tier_index: int) -> int:
    return max(1, min(RANK_COUNT, int(tier_index or 1)))


def rank_cap(tier_index: int) -> int:
    major_i, _ = decompose(clamp_tier(tier_index))
    return _MAJOR_CAPS.get(MAJOR_TIERS[major_i], _DEFAULT_CAP)


def rank_label(tier_index: int) -> str:
    major_i, sub_i = decompose(clamp_tier(tier_index))
    return f'{MAJOR_TIERS[major_i]} {SUB_TIERS[sub_i]}'


def rank_major(tier_index: int) -> str:
    return MAJOR_TIERS[decompose(clamp_tier(tier_index))[0]]


def rank_sub_tier(tier_index: int) -> str:
    return SUB_TIERS[decompose(clamp_tier(tier_index))[1]]


def gr_to_rank(season_gr: float) -> Tuple[int, int]:
    """存量花阶分换算初始 (段位序号, 段位分)。"""
    try:
        gr = float(season_gr or 0.0)
    except (TypeError, ValueError):
        gr = 0.0
    above = gr - MIGRATION_GR_BASELINE
    if above <= 0:
        return 1, 0
    steps = int(above // MIGRATION_GR_PER_SUBTIER)
    remainder = above - steps * MIGRATION_GR_PER_SUBTIER
    tier_index = clamp_tier(1 + steps)
    if remainder <= 0:
        return tier_index, 0
    points = int(round(rank_cap(tier_index) * remainder / MIGRATION_GR_PER_SUBTIER))
    return tier_index, max(0, min(rank_cap(tier_index), points))


def opponent_correction(own_tier: int, opponent_tier_avg: float) -> float:
    """段位修正 = 对方段位 - 己方段位（每小段记 1；2v2 取对方平均，可为小数）。"""
    return float(opponent_tier_avg) - float(own_tier)


def match_gain(own_tier: int, opponent_tier_avg: float, special_total: float = 0.0) -> int:
    """胜利加分：5 + 段位修正 + 特殊修正，至少 1。"""
    raw = WIN_BASE + opponent_correction(own_tier, opponent_tier_avg) + float(special_total or 0.0)
    return max(MIN_CHANGE, min(MAX_WIN, _round_half_up(raw)))


def match_loss(own_tier: int, opponent_tier_avg: float, special_total: float = 0.0) -> int:
    """失败扣分：3 - 段位修正 - 特殊修正，至少 1（返回正数）。"""
    raw = LOSS_BASE - opponent_correction(own_tier, opponent_tier_avg) - float(special_total or 0.0)
    return max(MIN_CHANGE, min(MAX_LOSS, _round_half_up(raw)))


def _round_half_up(value: float) -> int:
    return int(math.floor(value + 0.5))


def apply_match_result(
    tier_index: int,
    points: int,
    streak: int,
    *,
    outcome: str,
    opponent_tier_avg: float,
    special_total: float = 0.0,
    daily_double: bool = False,
    double_card: bool = False,
    loss_shield: bool = False,
) -> Dict[str, object]:
    """一局计分对局后的段位变化（纯函数）。

    outcome: 'win' | 'loss' | 'draw'。
    升段：段位分已在上限，再累计 2 连胜 → 升一段、归 0。
    降段：段位分已在 0，再输一局 → 降一段、置为新段上限（最低段不再降）。
    平局：分不变，连胜清零。
    daily_double: 每日前 5 局的胜利加分 ×2（封顶 +10 之后再乘）。
    double_card: 双倍卡——同上 ×2；与每日双倍共存时合计 ×3（设计 2026-10-02）。
    loss_shield: 保分卡——本局失败不扣分、不降段（连胜照旧清零）。
    common 大段失败不掉分（含降段）；unusual 扣分减半向上取整。
    """
    tier_index = clamp_tier(tier_index)
    cap = rank_cap(tier_index)
    points = max(0, min(cap, int(points or 0)))
    streak = max(0, int(streak or 0))
    outcome = str(outcome or '').lower()
    result: Dict[str, object] = {
        'tier_index': tier_index,
        'points': points,
        'streak': streak,
        'changed': False,
        'promoted': False,
        'demoted': False,
        'delta': 0,
        'daily_double': False,
    }
    if outcome == 'draw':
        if streak:
            result['streak'] = 0
            result['changed'] = True
        return result
    if outcome == 'win':
        gain = match_gain(tier_index, opponent_tier_avg, special_total)
        multiplier = 3 if (daily_double and double_card) else 2 if (daily_double or double_card) else 1
        if multiplier > 1:
            gain *= multiplier
            result['daily_double'] = daily_double
            result['double_card'] = double_card
        was_at_cap = points >= cap
        new_points = min(cap, points + gain)
        result['delta'] = new_points - points
        result['points'] = new_points
        result['changed'] = True
        if was_at_cap and new_points >= cap:
            # 已在上限后的连胜计数：第 2 胜升段。
            new_streak = streak + 1
            if new_streak >= 2:
                if tier_index >= RANK_COUNT:
                    result['streak'] = 0     # 最高段封顶，不再累计
                else:
                    result['tier_index'] = tier_index + 1
                    result['points'] = 0
                    result['streak'] = 0
                    result['promoted'] = True
            else:
                result['streak'] = new_streak
        else:
            result['streak'] = 0
        return result
    if outcome == 'loss':
        major = rank_major(tier_index)
        if loss_shield:
            result['shielded'] = True
            result['streak'] = 0
            result['changed'] = bool(streak)
            return result
        if major == 'common':
            result['streak'] = 0
            result['changed'] = bool(streak)
            return result
        loss = match_loss(tier_index, opponent_tier_avg, special_total)
        if major == 'unusual':
            loss = max(1, math.ceil(loss / 2))
        was_at_zero = points <= 0
        new_points = max(0, points - loss)
        result['delta'] = new_points - points
        result['points'] = new_points
        result['streak'] = 0
        result['changed'] = True
        if was_at_zero and new_points <= 0 and tier_index > 1:
            result['tier_index'] = tier_index - 1
            result['points'] = rank_cap(tier_index - 1)
            result['demoted'] = True
        return result
    return result


def monthly_settlement_tier(tier_index: int) -> int:
    """月度结算的掉段：basic → 前一个大段的 basic；非 basic → 本大段 basic。"""
    tier_index = clamp_tier(tier_index)
    major_i, sub_i = decompose(tier_index)
    if sub_i == 0:
        if major_i == 0:
            return tier_index
        return compose(major_i - 1, 0)
    return compose(major_i, 0)


def settlement_reward_dew(tier_index: int) -> int:
    """月度结算荆露：段位序号 × 1000（common basic = 1 × 1000）。"""
    return clamp_tier(tier_index) * 1000


def beijing_day_key(utc_dt) -> str:
    """UTC datetime → 北京自然日键（YYYY-MM-DD）。"""
    from datetime import timedelta
    return (utc_dt + timedelta(hours=BEIJING_TZ_OFFSET_HOURS)).strftime('%Y-%m-%d')


def beijing_month_key(utc_dt) -> str:
    from datetime import timedelta
    return (utc_dt + timedelta(hours=BEIJING_TZ_OFFSET_HOURS)).strftime('%Y-%m')


def opponent_tier_average(tier_indices: List[int]) -> float:
    """对方段位均值（2v2 = 两名对手的平均；1v1 单值）。"""
    values = [clamp_tier(v) for v in (tier_indices or []) if v]
    if not values:
        return 1.0
    return sum(values) / len(values)


def rank_payload(tier_index: int, points: int, *, streak: int = 0) -> Dict[str, object]:
    """对玩家展示的段位载荷。"""
    tier_index = clamp_tier(tier_index)
    cap = rank_cap(tier_index)
    return {
        'tier_index': tier_index,
        'tier': rank_major(tier_index),
        'sub_tier': rank_sub_tier(tier_index),
        'label': rank_label(tier_index),
        'points': max(0, min(cap, int(points or 0))),
        'cap': cap,
        'streak': max(0, int(streak or 0)),
        'color': MAJOR_COLOR.get(rank_major(tier_index), '#7F8C8D'),
    }


# 大段填充色：与 Craft Eternal RARITY_TABLE 的 bg 一致（客户端徽章用）。
MAJOR_COLOR: Dict[str, str] = {
    'common': '#7EEF6D',
    'unusual': '#FFE65D',
    'rare': '#4D52E3',
    'epic': '#861FDE',
    'legendary': '#DE1F1F',
    'mythic': '#1FDBDE',
    'ultra': '#FF2B75',
    'super': '#2BFFA3',
    'omega': '#F329D9',
    'unique': '#555555',
    'eternal': '#EEEEEE',
}

SUB_TIER_ICON_CARD: Dict[str, str] = {
    'basic': 'Basic',
    'sewage': 'Sewage',
    'disc': 'Disc',
    'golden_nazar': 'GoldenNazar',
}
