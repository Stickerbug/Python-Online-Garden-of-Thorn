# -*- coding: utf-8 -*-
"""Public registry of atomic effect ops usable by GTN Mod Spec v2 content.

The engine implements every atomic effect as ``GameEngine._atomic_<name>``.
Those handlers are the single source of truth for what a package may call, so
the registry merges the curated core ops declared in :mod:`mod_spec_v2` with
every handler found in the engine modules at import time.

Adding a new ``_atomic_*`` handler therefore makes the op available to mods
without a second registration step, and the module-level cache keeps the scan
cheap.
"""

from __future__ import annotations

import pathlib
import re
from typing import Iterable, Set

ENGINE_MODULES = ("game_engine.py", "game_engine_2v2.py", "game_engine_urf.py")
_HANDLER_RE = re.compile(r"^[ \t]*def _atomic_([A-Za-z0-9_]+)\(", re.MULTILINE)

# Extra public names that are executed by dedicated engine code paths instead of
# an ``_atomic_`` handler (kept explicit so validation stays predictable).
EXTRA_PUBLIC_OPS = (
    # Round 38 / 批次 AD-3：``force_end_turn`` 并进 ``turn_control(mode:"end")``，
    # 由 ``GameEngine._atomic_turn_control`` 承接（真 ``_atomic_*`` 实现），
    # 不再需要在这里额外登记。
    # Round 20: ``desert_wind_schedule`` / ``garden_mecha_antennae`` were
    # declared here without any implementation anywhere in the engine or the v2
    # runtime, so writing them as a step always failed with "unsupported v2 op".
    # They are gone; see ``mod_spec_v2.REMOVED_ATOMIC_OPS`` for the replacements.
    # Round 6a: engine implemented atoms that are also part of the curated
    # spec list; registered here as well so the mod studio schema stays stable
    # even if the ``_atomic_*`` source scan misses a module.
    # Round 36 / 批次 AD-1：``declare_forced_target`` 已并进 ``request`` 伞
    # （``type:"forced_target"``，由 ``_atomic_request`` 承接），不再单独登记。
    # Round 6b: reveal a hand to a viewer and tag the revealed cards (Schizo).
    # Round 33 / 批次 AB：``reveal_hand_cards`` 已并入 ``reveal(mode:"hand")``，
    # 由 ``GameEngine._atomic_reveal`` 承接，不再需要额外登记。
)

_engine_ops_cache: Set[str] | None = None


def engine_atomic_ops() -> Set[str]:
    """Return every atomic op name implemented by the engine modules."""
    global _engine_ops_cache
    if _engine_ops_cache is not None:
        return set(_engine_ops_cache)
    root = pathlib.Path(__file__).resolve().parent
    found: Set[str] = set()
    for name in ENGINE_MODULES:
        path = root / name
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        found.update(_HANDLER_RE.findall(source))
    found.update(EXTRA_PUBLIC_OPS)
    _engine_ops_cache = found
    return set(found)


def merge_public_ops(core_ops: Iterable[str]) -> Set[str]:
    """Merge the curated core op list with the engine's atomic handlers."""
    return set(core_ops) | engine_atomic_ops()


def clear_cache() -> None:
    global _engine_ops_cache
    _engine_ops_cache = None
