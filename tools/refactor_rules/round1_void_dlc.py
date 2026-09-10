# -*- coding: utf-8 -*-
"""Round 1 rewrite rules for ``mods/Void Cards DLC.gtnmod`` (agent rd1_void_dlc).

Only the branches of ``void_dlc_action`` that the *existing* generic capabilities
can express are converted here. The other branches stay untouched and are
documented as capability gaps in ``.codex-tmp/round1/rd1_void_dlc.md``.

Values (``damage`` and friends) always come from the original card parameters so
the rule keeps working if the mod data is retuned.
"""

from __future__ import annotations

import sys

# Marker that stops the spawned copy from spawning yet another copy. The engine
# read ``card.custom_vars['void_dlc_no_heated_thorn_spawn']``; ``setup_modifiers``
# is the generic equivalent (``card_has_modifier`` checks it) and it survives on
# the copied instance exactly like the old marker did.
NO_RESPAWN_MODIFIER = "void_dlc_no_heated_thorn_spawn"


def _heated_thorn_steps(params):
    """``cards:void:thorn_missile``.

    zh: 对目标造成6[[icon:D]]并对其施加1层烈火；造成实际伤害时，
        额外打出1张[[card:HeatedThorn]]（广域打击）（自刃）（裂变:3）。
    """
    damage = params.get("damage", 6)
    return [{
        "op": "deal_damage",
        "target": params.get("target", "target"),
        "amount": damage,
        "on_hit_once": [
            {
                "op": "status_add_named",
                "status": "hel:blazing_fire",
                "amount": params.get("blaze", 1),
                "target": params.get("status_target", "target"),
                "log": False,
            },
            {
                "op": "if",
                "condition": {
                    "op": "not",
                    "condition": {
                        "op": "card_has_modifier",
                        "card": "current_card",
                        "modifier": NO_RESPAWN_MODIFIER,
                    },
                },
                "then": [
                    {
                        "op": "copy_card_instance",
                        "source": "current_card",
                        "target": "self",
                        "zone": "hand",
                        "flags": ["wide_strike", "self_target"],
                        "setup_modifiers": [NO_RESPAWN_MODIFIER],
                        "fission_level": params.get("fission_level", 3),
                        "hand_full": "discard",
                        "log": False,
                    },
                    {
                        "op": "auto_play_card",
                        "card": {"ref": "last_created_card"},
                        "no_cost": False,
                        "empty_selection_ok": True,
                        "log": False,
                    },
                ],
            },
        ],
    }]


def _heated_thorn_builder(params):
    if str(params.get("action") or "") == "heated_thorn":
        return _heated_thorn_steps(params)
    return [{"op": "void_dlc_action", **params}]


# ``void_dlc_action`` already has an inline generic builder that dispatches on
# its ``action`` parameter and leaves unknown actions untouched, which shadows
# any module rule with the same op name.  The tool also honours per-card
# overrides (``CARD_OP_REWRITES``, keyed by ``name_en``) that are applied before
# the generic table, so the converted branch is registered for its card here.
REWRITES = {
    # Kept for documentation/forward compatibility; the inline builder for
    # ``void_dlc_action`` wins over this entry (see the comment below).
    "void_dlc_action": _heated_thorn_builder,
}


def _register_card_override() -> None:
    """Register the converted branch through the tool's per-card override table.

    ``tools/refactor_card_atoms.py`` owns an inline builder for
    ``void_dlc_action`` that dispatches on ``action`` and passes unknown actions
    through untouched, and inline builders are resolved before module rules.
    The tool also consults ``CARD_OP_REWRITES`` (keyed by ``name_en``) *before*
    the generic table, but that dict is built before rule modules are imported,
    so the override has to be attached after the fact through the already
    imported parent module.
    """
    parent = sys.modules.get("gtn_refactor_rules___parent__")
    if parent is None:
        # ``_load_rule_modules`` imports every rule module from the same
        # process that owns ``tools/refactor_card_atoms.py``; find it by file.
        for module in list(sys.modules.values()):
            filename = getattr(module, "__file__", "") or ""
            if filename.endswith("refactor_card_atoms.py"):
                parent = module
                break
    if parent is None:
        return
    table = getattr(parent, "CARD_OP_REWRITES", None)
    if isinstance(table, dict):
        table.setdefault("Thorn", {})["void_dlc_action"] = _heated_thorn_builder


_register_card_override()
