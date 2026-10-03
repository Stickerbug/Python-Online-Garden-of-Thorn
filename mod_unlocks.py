"""Casual 1v1/2v2 official-mod unlock progression.

Progression deliberately shares the newcomer "valid PvP games" counter:
linked-account groups pool their valid games, and only registered accounts
participate.  Guests therefore remain on the vanilla official pool.
"""

from __future__ import annotations

from typing import Iterable

import db
import pvp_economy
from mod_loader import load_all_mods, mod_category, mods_signature, sort_mods_for_display


VANILLA_MOD_FILENAME = 'Vanilla Cards.gtnmod'
FIXED_UNLOCK_GAMES = 10
ENTERTAINMENT_UNLOCK_GAMES = 20
CHOICE_INTERVAL_GAMES = 10
FIXED_UNLOCK_COUNT = 5

_OFFICIAL_NAMES_CACHE: tuple[tuple, tuple[str, ...]] | None = None
_OFFICIAL_LAYOUT_CACHE: tuple[tuple, tuple[tuple[str, ...], tuple[str, ...]]] | None = None


def official_mod_filenames() -> list[str]:
    """Return healthy official mods in canonical display order.

    Cached by the mods-directory signature: this is called twice per login and
    rebuilding the list walks every package.
    """
    global _OFFICIAL_NAMES_CACHE
    signature = mods_signature()
    cached = _OFFICIAL_NAMES_CACHE
    if cached is not None and cached[0] == signature:
        return list(cached[1])
    names: list[str] = []
    for mod in sort_mods_for_display(load_all_mods()):
        if getattr(mod, 'errors', None):
            continue
        filename = str(getattr(mod, 'filename', '') or '').strip()
        if not filename or mod_category(mod) != 'official':
            continue
        if filename not in names:
            names.append(filename)
    if VANILLA_MOD_FILENAME in names:
        names.remove(VANILLA_MOD_FILENAME)
        names.insert(0, VANILLA_MOD_FILENAME)
    _OFFICIAL_NAMES_CACHE = (signature, tuple(names))
    return names


def official_layout() -> tuple[list[str], list[str]]:
    """Return ``(fixed_unlock_mods, remaining_official_mods)``."""
    global _OFFICIAL_LAYOUT_CACHE
    signature = mods_signature()
    cached = _OFFICIAL_LAYOUT_CACHE
    if cached is not None and cached[0] == signature:
        fixed, remaining = cached[1]
        return list(fixed), list(remaining)
    names = official_mod_filenames()
    additions = [name for name in names if name != VANILLA_MOD_FILENAME]
    fixed = additions[:FIXED_UNLOCK_COUNT]
    remaining = additions[FIXED_UNLOCK_COUNT:]
    _OFFICIAL_LAYOUT_CACHE = (signature, (tuple(fixed), tuple(remaining)))
    return list(fixed), list(remaining)


def compute_state(valid_games: int, chosen_mods: Iterable[str]) -> dict:
    valid = max(0, int(valid_games or 0))
    fixed_mods, remaining_mods = official_layout()
    fixed_unlocked = valid >= FIXED_UNLOCK_GAMES
    entitlements = (
        max(0, valid // CHOICE_INTERVAL_GAMES - 1)
        if fixed_unlocked
        else 0
    )
    remaining_set = set(remaining_mods)
    sanitized_choices: list[str] = []
    seen: set[str] = set()
    for filename in chosen_mods or ():
        name = str(filename or '').strip()
        if not name or name not in remaining_set or name in seen:
            continue
        seen.add(name)
        sanitized_choices.append(name)
    all_official_unlocked = fixed_unlocked and entitlements >= len(remaining_mods)
    if not all_official_unlocked and len(sanitized_choices) > entitlements:
        sanitized_choices = sanitized_choices[:entitlements]
    unlocked_remaining = list(remaining_mods) if all_official_unlocked else sanitized_choices
    unlocked_remaining_set = set(unlocked_remaining)
    unlocked_official = []
    if VANILLA_MOD_FILENAME in official_mod_filenames():
        unlocked_official.append(VANILLA_MOD_FILENAME)
    if fixed_unlocked:
        unlocked_official.extend(fixed_mods)
    unlocked_official.extend(name for name in remaining_mods if name in unlocked_remaining_set)
    choice_candidates = [
        name for name in remaining_mods
        if name not in unlocked_remaining_set
    ]
    unspent_choices = (
        0
        if all_official_unlocked
        else max(0, entitlements - len(sanitized_choices))
    )
    if all_official_unlocked:
        choice_candidates = []
    has_pending_choice = bool(unspent_choices and choice_candidates)
    if not fixed_unlocked:
        next_unlock_games = FIXED_UNLOCK_GAMES
    elif all_official_unlocked:
        next_unlock_games = 0
    else:
        next_unlock_games = (valid // CHOICE_INTERVAL_GAMES + 1) * CHOICE_INTERVAL_GAMES
    return {
        'valid_games': valid,
        'fixed_unlock_games': FIXED_UNLOCK_GAMES,
        'entertainment_unlock_games': ENTERTAINMENT_UNLOCK_GAMES,
        'choice_interval_games': CHOICE_INTERVAL_GAMES,
        'fixed_unlocked': fixed_unlocked,
        'entertainment_unlocked': valid >= ENTERTAINMENT_UNLOCK_GAMES,
        # Community mods stay hidden from players; the entitlement is still
        # tracked so the feature can be re-enabled without a data migration.
        'community_unlocked': valid >= ENTERTAINMENT_UNLOCK_GAMES,
        'fixed_mods': list(fixed_mods),
        'remaining_mods': list(remaining_mods),
        'unlocked_official': unlocked_official,
        'choice_candidates': choice_candidates,
        'chosen_mods': list(sanitized_choices),
        'unspent_choices': int(unspent_choices),
        'next_unlock_games': int(next_unlock_games),
        'all_official_unlocked': bool(all_official_unlocked),
        'has_pending_choice': has_pending_choice,
        'guest': False,
    }


def guest_state() -> dict:
    # 游客无段位（按最低段）：只有 Vanilla 常开（段位制口径）。
    state = rank_tier_state(1)
    state['guest'] = True
    return state


def _linked_user_ids(conn, user_id: int) -> list[int]:
    uid = int(user_id)
    group = conn.execute(
        '''
        SELECT g.id
        FROM account_link_groups g
        JOIN account_link_members m ON m.group_id = g.id
        WHERE m.user_id = ? AND m.status = 'active'
          AND g.status IN ('confirmed', 'appealed')
        LIMIT 1
        ''',
        (uid,),
    ).fetchone()
    if not group:
        return [uid]
    rows = conn.execute(
        '''
        SELECT m.user_id
        FROM account_link_members m
        JOIN users u ON u.id = m.user_id
        WHERE m.group_id = ? AND m.status = 'active' AND u.deleted_at IS NULL
        ORDER BY m.user_id
        ''',
        (int(group['id']),),
    ).fetchall()
    member_ids = [int(row['user_id']) for row in rows]
    return member_ids or [uid]


def _state_for_connection(conn, user_id: int) -> dict:
    uid = int(user_id)
    # 设计 2026-10-02：官方模组解锁改为段位驱动（掉段收回）——
    # Unusual1-4 → 花园/沙漠/丛林/海洋，Rare1 → 工厂，Vanilla 恒开。
    row = conn.execute(
        'SELECT rank_tier FROM users WHERE id = ?',
        (uid,),
    ).fetchone()
    tier = int(row['rank_tier'] or 1) if row is not None else 1
    return rank_tier_state(tier)


# 段位 → 官方包解锁表（达到该 tier 解锁；以当前段位为准，掉段收回）。
RANK_UNLOCK_TABLE: tuple[tuple[int, str], ...] = (
    (5, 'Garden Cards Addition.gtnmod'),    # Unusual 1
    (6, 'Desert Cards Addition.gtnmod'),    # Unusual 2
    (7, 'Jungle Cards Addition.gtnmod'),    # Unusual 3
    (8, 'Ocean Cards Addition.gtnmod'),     # Unusual 4
    (9, 'Factory Cards Addition.gtnmod'),   # Rare 1
)


def rank_tier_state(rank_tier: int) -> dict:
    """段位驱动的解锁状态（与 compute_state 同形，自选流程退役）。"""
    import rank_system as _rank
    tier = max(1, int(rank_tier or 1))
    names = official_mod_filenames()
    required_tier = {name: need for need, name in RANK_UNLOCK_TABLE}
    unlocked: list[str] = []
    if VANILLA_MOD_FILENAME in names:
        unlocked.append(VANILLA_MOD_FILENAME)
    for name in names:
        if name == VANILLA_MOD_FILENAME:
            continue
        need = required_tier.get(name)
        if need is not None and tier >= need:
            unlocked.append(name)
    locked_next = sorted(
        ((need, name) for name, need in required_tier.items() if name not in unlocked),
    )
    return {
        'rank_tier': tier,
        'rank_tier_label': _rank.rank_label(tier),
        'fixed_unlocked': True,
        'entertainment_unlocked': True,
        'community_unlocked': True,
        'fixed_mods': [],
        'remaining_mods': [n for n in names if n not in unlocked and n != VANILLA_MOD_FILENAME],
        'unlocked_official': unlocked,
        'choice_candidates': [],
        'chosen_mods': [],
        'unspent_choices': 0,
        'next_unlock_games': 0,
        'next_unlock_tier': locked_next[0][0] if locked_next else 0,
        'next_unlock_mod': locked_next[0][1] if locked_next else '',
        'all_official_unlocked': not locked_next,
        'has_pending_choice': False,
        'guest': False,
    }


def load_state(user_id: int | None) -> dict:
    if not user_id:
        return guest_state()
    with db.get_db_connection() as conn:
        return _state_for_connection(conn, int(user_id))


def choose_unlock(user_id: int, mod_filename: str) -> dict:
    """段位制（2026-10-02）下官方包不再自选——统一按段位解锁/收回。"""
    raise ValueError('官方模组已改为按段位自动解锁，无需手动选择')
