"""Casual 1v1/2v2 official-mod unlock progression.

Progression deliberately shares the newcomer "valid PvP games" counter:
linked-account groups pool their valid games, and only registered accounts
participate.  Guests therefore remain on the vanilla official pool.
"""

from __future__ import annotations

from typing import Iterable

import db
import pvp_economy
from mod_loader import load_all_mods, mod_category, sort_mods_for_display


VANILLA_MOD_FILENAME = 'Vanilla Cards.gtnmod'
FIXED_UNLOCK_GAMES = 10
ENTERTAINMENT_UNLOCK_GAMES = 20
CHOICE_INTERVAL_GAMES = 10
FIXED_UNLOCK_COUNT = 5


def official_mod_filenames() -> list[str]:
    """Return healthy official mods in canonical display order."""
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
    return names


def official_layout() -> tuple[list[str], list[str]]:
    """Return ``(fixed_unlock_mods, remaining_official_mods)``."""
    names = official_mod_filenames()
    additions = [name for name in names if name != VANILLA_MOD_FILENAME]
    return additions[:FIXED_UNLOCK_COUNT], additions[FIXED_UNLOCK_COUNT:]


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
    state = compute_state(0, ())
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
    member_ids = _linked_user_ids(conn, uid)
    valid_games = int(pvp_economy.profile_conn(conn, uid).get('valid_games') or 0)
    placeholders = ','.join('?' for _ in member_ids)
    rows = conn.execute(
        f'''
        SELECT mod_filename
        FROM user_mod_unlock_choices
        WHERE user_id IN ({placeholders})
        ORDER BY created_at, mod_filename
        ''',
        tuple(member_ids),
    ).fetchall()
    return compute_state(valid_games, (row['mod_filename'] for row in rows))


def load_state(user_id: int | None) -> dict:
    if not user_id:
        return guest_state()
    with db.get_db_connection() as conn:
        return _state_for_connection(conn, int(user_id))


def choose_unlock(user_id: int, mod_filename: str) -> dict:
    """Persist one official-mod choice and return the refreshed state."""
    uid = int(user_id)
    filename = str(mod_filename or '').strip()
    with db.get_db_connection() as conn:
        # Serialize entitlement spending so two simultaneous clicks cannot
        # consume the same choice allowance twice.
        conn.execute('BEGIN IMMEDIATE')
        state = _state_for_connection(conn, uid)
        if not state.get('has_pending_choice'):
            raise ValueError('当前没有可用的官方模组自选次数')
        if filename not in set(state.get('choice_candidates') or []):
            raise ValueError('该模组当前不可选择')
        conn.execute(
            '''
            INSERT OR IGNORE INTO user_mod_unlock_choices(user_id, mod_filename, created_at)
            VALUES (?, ?, ?)
            ''',
            (uid, filename, db.utc_now()),
        )
        conn.commit()
        return _state_for_connection(conn, uid)
