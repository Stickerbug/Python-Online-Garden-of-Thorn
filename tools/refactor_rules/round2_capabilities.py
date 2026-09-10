# -*- coding: utf-8 -*-
"""Round 2 conversions that only need the generic capabilities added in Batch A.

Every rule here replaces a card-specific ``_atomic_*`` op with generic data
steps; the engine handlers themselves stay in place until root removes them
(after the A/B probes prove equivalence).
"""

from __future__ import annotations


def _relativity_steps(params: dict) -> list:
    """``void_turn_count_damage``: 6 + 4 x cards played this turn (excluding self)."""

    base = params.get("base", 6)
    per = params.get("per", 4)
    played = {"op": "cards_played_this_turn", "target": "source", "exclude_current": True}
    if per < 0:
        amount = {
            "op": "max",
            "values": [0, {"op": "add", "values": [base, {"op": "mul", "values": [per, played]}]}],
        }
    else:
        amount = {"op": "add", "values": [base, {"op": "mul", "values": [per, played]}]}
    return [{"op": "deal_damage", "target": params.get("target", "target"), "amount": amount}]


def _magic_relativity_steps(params: dict) -> list:
    """``void_magic_relativity_damage_end``: the same damage, then end the turn."""

    return _relativity_steps(params) + [{"op": "force_end_turn"}]


def _magic_stardust_steps(params: dict) -> list:
    """``void_dlc_action`` / ``magic_stardust``: resolve poison, refilling from toxic."""

    return [
        {
            "op": "settle_status",
            # The card is a wide strike: the old branch settled every chosen
            # target, which is what the engine's own wide-strike target list
            # returns (a plain "target" collapses to one player).
            "target": params.get("target", "wide_strike_targets"),
            "status": "poison",
            "fill_from": {
                "status": "jungle:toxic_poison",
                "ensure": 1,
                "when_empty": True,
                "refill": True,
            },
            "log": False,
        }
    ]


ILLUMINATI_STATUSES = (
    "poison", "fire", "toxic", "dodge", "sluggish", "overload", "foresight",
    "fracture", "stagnation", "blind", "heal_block", "weakness", "bleed",
    "attack_blocked", "attack_only", "magic_blocked", "skip_turn",
    "jungle:fragile", "jungle:shield", "jungle:turn_heal_turns",
    "jungle:turn_magic_turns", "jungle:toxic_poison", "ocean:blood_debt",
    "ocean:unable_counter", "arctic:frost", "hel:luck", "hel:blazing_fire",
    "bio:debt", "bio:extra_healing", "bio:shield_conversion",
)


def _illuminati_triangle_steps(params: dict) -> list:
    """``void_dlc_action`` / ``illuminati_triangle``.

    Heal the target, apply every status except Status Immunity / Untargetable,
    then clear them all again at the end of the target's next turn (the Chinese
    card text is the authority; the old branch cleared at the caster's turn end).
    """

    target = params.get("target", "target")
    steps = [
        {
            "op": "heal",
            "target": target,
            "amount": params.get("heal", 20),
            "log": "{target}回复{amount}H",
        }
    ]
    steps.extend(
        {
            "op": "status_add_named",
            "status": status,
            "amount": 1,
            "target": target,
            "log": False,
        }
        for status in ILLUMINATI_STATUSES
    )
    steps.append(
        {
            "op": "timed_effect",
            "trigger": "target_turn_end",
            "target": target,
            "effects": [
                {"op": "clear_statuses", "target": "target", "statuses": "all", "log": False}
            ],
            "log": False,
        }
    )
    return steps


def _blood_chromosome_steps(params: dict) -> list:
    """``bio_activate_blood_chromosome``: pull discard cards until the hand is full."""

    return [
        {
            "op": "defer_game_over",
            "body": [
                {
                    "op": "random_zone_card_to_hand",
                    "target": "self",
                    "zone": "discard",
                    "count": 200,
                    "tag": "symbiosis",
                    "per_card": [
                        {
                            "op": "direct_damage",
                            "target": "self",
                            "amount": 2,
                            "source_text": "血染色体",
                        }
                    ],
                    "log": "{source}的血染色体完成抽牌",
                }
            ],
        }
    ]


def _ocean_add_blood_debt_steps(params: dict) -> list:
    """``ocean_add_blood_debt``: attacker gains blood debt when the owner is hurt.

    The old atom only fired for positive physical damage and wrote the debt onto
    the damage source; both parts are generic conditions now.
    """

    conditions = []
    if params.get("require_physical_damage"):
        conditions.append({"op": "damage_type_is", "damage_type": "physical"})
    conditions.append({"op": "compare", "a": {"op": "damage_amount"}, "operator": ">", "b": 0})
    return [
        {
            "op": "if",
            "condition": conditions[0] if len(conditions) == 1 else {"op": "and", "conditions": conditions},
            "then": [
                {
                    "op": "status_add_named",
                    "status": "ocean:blood_debt",
                    "amount": params.get("amount", 1),
                    # Inside ``on_damage_taken`` the debt goes to the attacker:
                    # "source"/"target" resolve to the listener, so the damage
                    # source selector is the faithful translation.
                    "target": "damage_source",
                    "log": "{target}+{amount}层血债",
                }
            ],
        }
    ]


def _jurassic_random_deck_to_hand_steps(params: dict) -> list:
    """``jurassic_random_deck_to_hand``: random deck card into hand, gains symbiosis."""

    return [
        {
            "op": "random_zone_card_to_hand",
            "target": params.get("target", "target"),
            "zone": "deck",
            "count": 1,
            "tag": "symbiosis",
            "log": "{target}将抽牌堆中随机1张牌加入手中并使其获得共生",
            "empty_log": "{target}的抽牌堆没有可选牌",
        }
    ]


def _desert_magic_compass_steps(params: dict) -> list:
    """``desert_magic_compass``: shuffle the chosen discard cards onto the deck top."""

    return [
        {
            "op": "move_cards_to_deck",
            "cards": "selected_cards",
            "owner": "self",
            "position": "random_top",
            "log": "{source}将{count}张弃牌随机置于抽牌堆顶",
        }
    ]


def _sewers_seal_target_equipment_steps(params: dict) -> list:
    """``sewers_seal_target_equipment``: seal every piece of the target's equipment."""

    return [
        {
            "op": "seal_equipment",
            "target": params.get("target", "target"),
            "amount": params.get("amount", 1),
        }
    ]


REWRITES = {
    "void_turn_count_damage": _relativity_steps,
    "void_magic_relativity_damage_end": _magic_relativity_steps,
    "bio_activate_blood_chromosome": _blood_chromosome_steps,
    "ocean_add_blood_debt": _ocean_add_blood_debt_steps,
    "jurassic_random_deck_to_hand": _jurassic_random_deck_to_hand_steps,
    "desert_magic_compass": _desert_magic_compass_steps,
    "sewers_seal_target_equipment": _sewers_seal_target_equipment_steps,
}


# ``void_dlc_action`` is shared by every Void DLC branch, so the stardust branch is
# registered per card (a card-level rule wins over the shared op rule).
CARD_REWRITES = {
    "Magic Stardust": {
        "void_dlc_action": _magic_stardust_steps,
    },
    "Illuminati Triangle": {
        "void_dlc_action": _illuminati_triangle_steps,
    },
}
