# -*- coding: utf-8 -*-
"""Round 1 rewrite rules for the Bio / Sewers packages (agent ``rd1_bio_sewers``).

Each builder receives the flattened parameters of one card-specific step and
returns the generic steps that replace it.  Only ops that already exist in
``mod_runtime_v2`` / ``ADVANCED_ATOMIC_OPS`` are used; see
``.codex-tmp/round1/rd1_bio_sewers.md`` for the per-atom analysis and for the
abilities that are still missing (recorded as gaps instead of engine edits).
"""

from __future__ import annotations

ELECTRIC_DAMAGE_TYPE = "magic"
ELECTRIC_DAMAGE_TAG = "gtn:battery"


def _compare(a, operator, b):
    return {"op": "compare", "a": a, "operator": operator, "b": b}


def _last_damage():
    return {"op": "last_damage"}


def _choice(key, default):
    return {"op": "choice_value", "key": key, "default": default}


def _player_stat(stat, target="self"):
    return {"op": "player_stat", "target": target, "stat": stat}


def _electric_damage(target, amount, source_text):
    return {
        "op": "direct_damage",
        "target": target,
        "amount": amount,
        "source_text": source_text,
        "damage_type": ELECTRIC_DAMAGE_TYPE,
        "damage_tag": ELECTRIC_DAMAGE_TAG,
    }


def _heal_if_damaged(target, amount):
    """Heal ``target`` only when the damage step above actually dealt damage."""
    return {
        "op": "if",
        "condition": _compare(_last_damage(), ">", 0),
        "then": [{"op": "heal", "target": target, "amount": amount}],
    }


def _blood_knife_steps(params):
    """``bio:blood_knife`` = 7 electric damage to self, then E recovery.

    Card text: 对自己造成7电击伤害；每造成3电击伤害，回复自己1E；
    若实际回复至少1E，此牌回到手中。
    """
    recovered = {"op": "floor", "value": {"op": "div", "a": _last_damage(), "b": 3}}
    missing_elixir = {
        "op": "sub",
        "values": [_player_stat("max_elixir"), _player_stat("elixir")],
    }
    # ``PlayerState.gain_elixir`` caps at ``max_elixir``, and the card only
    # returns to hand when at least one Elixir was actually recovered.
    actually_gained = {"op": "min", "values": [recovered, missing_elixir]}
    return [
        _electric_damage("self", 7, "血刃电伤"),
        {
            "op": "if",
            "condition": _compare(actually_gained, ">=", 1),
            "then": [
                {"op": "gain_e", "target": "self", "amount": actually_gained},
                # The engine returns the played card to hand when it carries the
                # ``return_to_hand`` instance flag.
                {"op": "add_tag", "card": "current_card", "tag": "return_to_hand", "log": False},
            ],
        },
    ]


def _blood_sugar_physical_block(target, hits):
    """``hits`` physical attack segments that heal the damaged player 2H each."""
    return [{
        "op": "deal_damage",
        "target": target,
        "amount": 1,
        "hits": hits,
        "ignore_untargetable": target == "self",
        "on_hit": [{"op": "heal", "target": target, "amount": 2}],
    }]


def _blood_sugar_electric_block(target, hits):
    """``hits`` electric (magic/battery) segments that heal the victim 2H each.

    ``direct_damage`` has no ``hits``/``on_hit`` support yet, so the segments are
    emitted one by one; each one heals only when it actually dealt damage.
    """
    steps = []
    for _ in range(hits):
        steps.append(_electric_damage(target, 1, "血糖电伤"))
        steps.append(_heal_if_damaged(target, 2))
    return steps


def _blood_sugar_steps(params):
    """``bio:blood_sugar`` chooses which side takes the electric damage.

    Card text: 选择1项：分别对目标造成1电击×5并对自己造成1D×5；
    或分别对目标造成1D×5并对自己造成1电击×5。
    每次造成实际伤害时，回复受伤者2H（5子瓣）。
    """
    target = params.get("target", "target")
    raw_hits = params.get("hits", 5)
    try:
        hits = max(0, int(raw_hits))
    except (TypeError, ValueError):
        hits = 5
    electric_target = (
        _blood_sugar_electric_block(target, hits)
        + _blood_sugar_physical_block("self", hits)
    )
    physical_target = (
        _blood_sugar_physical_block(target, hits)
        + _blood_sugar_electric_block("self", hits)
    )
    return [{
        "op": "if",
        "condition": _compare(
            _choice("bio_blood_sugar_mode", "electric_target"),
            "==",
            "electric_target",
        ),
        "then": electric_target,
        "else": physical_target,
    }]


def _blood_diamond_steps(params):
    """``bio:blood_diamond`` = 3 damage x4, 1 Bleed per positive hit.

    Card text: 对目标造成3[[icon:D]]×4（4子瓣）；每次造成实际伤害时，
    对目标施加1层流血。
    """
    target = params.get("target", "target")
    return [{
        "op": "deal_damage",
        "target": target,
        "amount": params.get("amount", 3),
        # ``on_hit`` runs once per positive hit, so every hit that actually
        # dealt damage adds its own Bleed layer.
        "hits": 4,
        "on_hit": [{
            "op": "status_add_named",
            "status": "bleed",
            "amount": 1,
            "target": target,
            "log": "{target}获得{amount}层流血",
        }],
    }]


def _blood_rose_steps(params):
    """``sewers:blood_rose`` = 3 attack damage, delayed Blindness, x5 healing.

    Card text: 对目标造成3[[icon:D]]；命中时，目标下回合开始时获得3层失明；
    回复目标(实际伤害×5)[[icon:H]]。
    """
    target = params.get("target", "target")
    return [
        {
            "op": "deal_damage",
            "target": target,
            "amount": params.get("amount", 3),
            "on_hit_once": [{
                "op": "timed_effect",
                "target": target,
                "trigger": "target_turn_start_after_status_clear",
                "duration": 1,
                "effects": [
                    {"op": "status_add_named", "target": target, "status": "blind", "amount": 3},
                    {"op": "shuffle_hand", "target": target},
                ],
            }],
        },
        {
            "op": "heal",
            "target": target,
            "amount": {"op": "mul", "values": [5, _last_damage()]},
        },
    ]


REWRITES = {
    "bio_activate_blood_knife": _blood_knife_steps,
    "bio_blood_sugar_attack": _blood_sugar_steps,
    "bio_blood_diamond_attack": _blood_diamond_steps,
    "sewers_blood_rose": _blood_rose_steps,
}
