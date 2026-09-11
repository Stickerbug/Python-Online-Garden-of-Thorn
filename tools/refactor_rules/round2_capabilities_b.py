# -*- coding: utf-8 -*-
"""Round 2 / Batch B + C9 conversions (queue, kitty, ricochet).

These rules replace the card-specific auto-play queue, the void Kitty atom and
the two ricochet atomics with the generic capabilities added in the same batch
(``queue_auto_play``, ``auto_play_zone_top``, ``ricochet_attack``).

The Sapphire conversion (generic ``request_card`` filter) lives here as well:
it needs per-card rules because ``request_card`` is a shared op.
"""

from __future__ import annotations

AUTO_PLAY_MARKER = "auto_play_no_queue"


def _queue_guard_steps(params: dict) -> list:
    """Pearl / Magic Pearl: keep the "do not trigger this effect again" guard.

    The engine marks every queued copy with the queue marker, so the guard is
    expressed with the generic marker instead of the historical
    ``ocean_no_auto`` flag.
    """

    condition = params.get("condition")
    if isinstance(condition, dict):
        inner = condition.get("value")
        if isinstance(inner, dict) and str(inner.get("tag")) == "ocean_no_auto":
            condition = {**condition, "value": {**inner, "tag": AUTO_PLAY_MARKER}}
    step = {"op": "if", "condition": condition, "then": params.get("then", [])}
    if params.get("else") is not None:
        step["else"] = params.get("else")
    return [step]


def _pearl_queue_steps(params: dict) -> list:
    """``ocean_mark_auto_play`` on Pearl: queue one exiled copy per play."""

    return [
        {
            "op": "queue_auto_play",
            "card": {"ref": "current_card"},
            "source": "snapshot",
            "target": params.get("target", "target"),
            "each_turn": True,
            "cost": "normal",
            "exile": True,
            "swift_value": params.get("swift_value", 1),
        }
    ]


def _magic_pearl_queue_steps(params: dict) -> list:
    """``ocean_mark_auto_play`` on Magic Pearl: the target is chosen at trigger time."""

    return [
        {
            "op": "queue_auto_play",
            "card": {"ref": "current_card"},
            "source": "snapshot",
            "target": {"ref": "lowest_health_enemy"},
            "each_turn": True,
            "cost": "normal",
            "exile": True,
            "magic_swift_value": params.get("magic_swift_value", 3),
        }
    ]


def _kitty_steps(params: dict) -> list:
    """``void_kitty_auto_play``: the equipment target plays their deck top for free."""

    return [
        {
            "op": "auto_play_zone_top",
            "actor": {"ref": "equipment_target"},
            "zone": "deck",
            "require_turn_player": "self",
            "cost": "free",
            "out_of_turn": True,
            "auto_resolve_choices": True,
            "random_target": True,
            "enter_hand_trigger": False,
            "on_failure": "return",
            "log": "小猫使{actor}自动打出{card}",
        }
    ]


def _carrot_steps(params: dict) -> list:
    """``arctic_ricochet_attack``: 1 hit, then 4 non-repeating bounces."""

    amount = params.get("amount", 6)
    return [
        {
            "op": "ricochet_attack",
            "target": params.get("target", "target"),
            "amount": amount,
            "hits": 1,
            "bounce_amount": params.get("bounce_amount", amount),
            "bounce_hits": 1,
            "bounces": params.get("repeats", 4),
            "bounces_from_positive_hits": False,
            "scale_bounces_by_fission": True,
            "allow_self": True,
            "exclude_previous": True,
            "precision_inherit": True,
            "register_secondary_targets": True,
        }
    ]


def _marble_steps(params: dict) -> list:
    """``desert_marble_attack``: one bounce per main-damage segment that landed."""

    return [
        {
            "op": "ricochet_attack",
            "target": params.get("target", "target"),
            "amount": params.get("amount", 9),
            "hits": 1,
            "inherit_extra_hits": True,
            "bounce_amount": params.get("extra_amount", 23),
            "bounce_hits": 1,
            "bounces_from_positive_hits": True,
            "scale_bounces_by_fission": True,
            "allow_self": True,
            "exclude_previous": True,
            "precision_inherit": True,
            "register_secondary_targets": True,
        }
    ]


REWRITES = {
    "void_kitty_auto_play": _kitty_steps,
    "arctic_ricochet_attack": _carrot_steps,
    "desert_marble_attack": _marble_steps,
}


# --- generic card picker filters -------------------------------------------
# The same spec drives the picker candidates, the server side validation and
# the ``play_requires`` gate, so the UI and the engine can never disagree.
SAPPHIRE_ATTACK_FILTER = {
    "zone": "hand",
    "owner": "self",
    "card_type": "thorn",
    "require_selectable": True,
    "exclude_flags": ["unique", "exile"],
    "exclude_self": True,
}

RUBY_ATTACK_FILTER = {
    "zone": "hand",
    "owner": "self",
    "card_type": "thorn",
    "require_selectable": True,
    "exclude_self": True,
    "affordable": True,
    "pay_ratio": 0.5,
    "reserve_source_cost": True,
}


def _sapphire_request_card_steps(params: dict) -> list:
    """Sapphire: pick the target first, then a filtered attack card.

    Idempotent: the old form had no ``filter`` on ``request_card``, so a step
    that already carries the Sapphire filter (and the trailing
    ``request_target`` written by the first pass) must come back untouched --
    otherwise every extra run inserts one more ``request_target``.
    """

    already_migrated = (
        str(params.get("choice_type") or "") == "choose_card_from_hand"
        and params.get("filter") == SAPPHIRE_ATTACK_FILTER
        and bool(params.get("cancellable", True))
    )
    if already_migrated:
        return [{"op": "request_card", "params": dict(params)}]

    return [
        {"op": "request_target", "allowed": "any"},
        {
            "op": "request_card",
            "params": {
                "choice_type": "choose_card_from_hand",
                "cancellable": bool(params.get("cancellable", True)),
                "filter": SAPPHIRE_ATTACK_FILTER,
            },
        },
    ]


def _sapphire_mark_steps(params: dict) -> list:
    """``ocean_sapphire_mark``: queue the exiled card and exile it."""

    return [
        {
            "op": "queue_auto_play",
            "card": {"ref": "selected_card"},
            "source": "instance",
            "target": params.get("target", "target"),
            "each_turn": True,
            "cost": "normal",
            "exile": True,
        },
        {"op": "move_to_exile", "card": {"ref": "selected_card"}, "silent": True},
        {"op": "log", "message": "{source}的蓝宝石放逐1张攻击牌"},
    ]


def _ruby_request_card_steps(params: dict) -> list:
    """Ruby: pick an attack card whose half cost can be paid."""

    return [
        {
            "op": "request_card",
            "params": {
                "choice_type": "choose_card_from_hand",
                "cancellable": bool(params.get("cancellable", False)),
                "target": "self",
                "filter": RUBY_ATTACK_FILTER,
            },
        }
    ]


CARD_REWRITES = {
    "Pearl": {
        "if": _queue_guard_steps,
        "ocean_mark_auto_play": _pearl_queue_steps,
    },
    "Magic Pearl": {
        "if": _queue_guard_steps,
        "ocean_mark_auto_play": _magic_pearl_queue_steps,
    },
    "Sapphire": {
        "request_card": _sapphire_request_card_steps,
        "ocean_sapphire_mark": _sapphire_mark_steps,
    },
    "Ruby": {
        "request_card": _ruby_request_card_steps,
    },
}
