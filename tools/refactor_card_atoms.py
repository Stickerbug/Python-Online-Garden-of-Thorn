# -*- coding: utf-8 -*-
"""Replace card-specific engine atoms with generic data steps.

Each entry rewrites the ``events`` steps of every card that calls the listed
card-specific op. The replacement uses only generic atomic ops (plus optional
``log`` templates so battle-log wording stays the same). Run repeatedly: the
script is idempotent and skips packages whose cards already use the new steps.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import pathlib
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"

LUCK_STATUS = "hel:luck"


def status_step(status: str, amount, target: str, log: str) -> dict:
    return {"op": "status_add_named", "status": status, "amount": amount, "target": target, "log": log}


# op name -> builder(params) -> replacement steps
GENERIC_STEP_REWRITES = {
    "hel_add_luck": lambda params: [
        status_step(LUCK_STATUS, params.get("amount", 1), params.get("target", "self"),
                    "{target}获得{amount}层幸运"),
    ],
    "hel_apply_blazing_fire": lambda params: [
        status_step("hel:blazing_fire", params.get("amount", 1), params.get("target", "target"),
                    "{target}获得{amount}层烈火"),
    ],
    "hel_bugatti_draw": lambda params: [
        {
            "op": "draw_to_hand_limit",
            "target": params.get("target", "target"),
            "log": "{target}因布加迪抽至手牌上限，抽了{amount}张牌",
        },
    ],
    "hel_fire_by_equipment": lambda params: [
        {
            "op": "status_add_named",
            "status": "fire",
            "amount": {"op": "add", "values": [2, {"op": "equipment_count", "target": "target"}]},
            "target": params.get("target", "target"),
            "log": "{target}+{amount}层灼烧",
        },
    ],
    "hel_magic_gunpowder": lambda params: [
        {
            "op": "gain_m",
            "target": "self",
            "amount": {"op": "player_stat", "target": params.get("target", "target"), "stat": "fire"},
            "log": "{target}回复{amount}M",
        },
    ],
    "hel_deliverance_attack": lambda params: [
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": {
                "op": "add",
                "values": [
                    params.get("base", 2),
                    {
                        "op": "mul",
                        "values": [
                            params.get("per_card", 2),
                            {"op": "player_stat", "target": params.get("target", "target"), "stat": "hand_count"},
                        ],
                    },
                ],
            },
        },
    ],
    "arctic_apply_frost": lambda params: [
        status_step("arctic:frost", params.get("amount", 1), params.get("target", "target"),
                    "{target}获得{amount}层霜冻"),
    ],
    "jungle_root_gain": lambda params: [
        status_step("jungle:root_status", params.get("amount", 2), params.get("target", "self"),
                    "{target}获得{amount}层树根"),
        {
            "op": "equipment_prop_add",
            "property": "jungle_root_layers",
            "amount": params.get("amount", 2),
        },
    ],
    "jungle_root_remove_owned": lambda params: [
        {
            "op": "status_add_named",
            "status": "jungle:root_status",
            "target": params.get("target", "self"),
            "amount": {
                "op": "sub",
                "values": [0, {"op": "equipment_prop", "equipment": "current_equipment",
                               "property": "jungle_root_layers"}],
            },
            "log": False,
        },
        {"op": "equipment_prop_set", "property": "jungle_root_layers", "value": 0},
    ],
    "jungle_add_maple_to_hand": lambda params: [
        {
            "op": "give_card_to_hand",
            "card": "Maple",
            "target": params.get("target", "self"),
            "log": "{target}将1张[[card:Maple|flag=symbiosis|flag=exile|flag=void]]加入手中",
        },
        {"op": "add_tag", "card": {"ref": "last_created_card"}, "tag": "symbiosis", "log": False},
        {"op": "add_tag", "card": {"ref": "last_created_card"}, "tag": "exile", "log": False},
        {"op": "add_tag", "card": {"ref": "last_created_card"}, "tag": "void", "log": False},
    ],
    "bio_add_extra_healing": lambda params: [
        status_step("bio:extra_healing", params.get("amount", 1), params.get("target", "target"),
                    "{target}获得{amount}层额外回复"),
    ],
    "bio_add_shield_conversion": lambda params: [
        status_step("bio:shield_conversion", params.get("amount", 1), params.get("target", "target"),
                    "{target}获得{amount}层护盾转化"),
    ],
    "bio_sugar_attack": lambda params: [
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": params.get("amount", 2),
            "hits": params.get("hits", 6),
        },
        {"op": "heal", "target": params.get("target", "target"), "amount": 20},
    ],
    "ocean_discard_count_damage": lambda params: [
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": {
                "op": "add",
                "values": [
                    params.get("base", 2),
                    {
                        "op": "mul",
                        "values": [
                            params.get("per", 1),
                            {"op": "player_var", "target": "source", "name": "ocean_active_discards"},
                        ],
                    },
                ],
            },
        },
    ],
    "desert_magic_yggdrasil": lambda params: [
        {
            "op": "give_card_to_hand",
            "card": "Yggdrasil",
            "target": params.get("target", "target"),
            "log": "{target}获得1张世界树之叶",
        },
    ],
    "sewers_chitin_turn_start": lambda params: [
        {
            "op": "if",
            "condition": {
                "op": "compare",
                "a": {"op": "status_stack", "target": params.get("target", "target"), "status": "nazar"},
                "operator": "==",
                "b": 0,
            },
            "then": [
                status_step("nazar", 1, params.get("target", "target"), "{target}获得1层邪眼"),
            ],
        },
    ],
    "sewers_neurotoxin": lambda params: [
        status_step("poison", 7, params.get("target", "target"), "{target}+7层中毒"),
        {
            "op": "if",
            "condition": {
                "op": "compare",
                "a": {"op": "status_stack", "target": params.get("target", "target"), "status": "poison"},
                "operator": ">=",
                "b": 22,
            },
            "then": [status_step("stunned", 1, params.get("target", "target"), "{target}+1层眩晕")],
            "else": [status_step("weakness", 1, params.get("target", "target"), "{target}+1层虚弱")],
        },
    ],
    "garden_coal_attack": lambda params: [
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": {
                "op": "add",
                "values": [8, {"op": "mul", "values": [2, {"op": "player_stat", "target": "source", "stat": "fire"}]}],
            },
        },
    ],
    "garden_kale_attack": lambda params: [
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": params.get("amount", 14),
        },
        {
            "op": "if",
            "condition": {
                "op": "and",
                "values": [
                    {"op": "compare", "a": {"op": "last_damage"}, "operator": ">", "b": 0},
                    {
                        "op": "compare",
                        "a": {"op": "mul", "values": [
                            5, {"op": "player_stat", "target": params.get("target", "target"), "stat": "health"},
                        ]},
                        "operator": "<=",
                        "b": {"op": "player_stat", "target": params.get("target", "target"), "stat": "max_health"},
                    },
                ],
            },
            "then": [
                {
                    "op": "deal_damage",
                    "target": params.get("target", "target"),
                    "amount": params.get("amount", 14),
                },
            ],
        },
    ],
    "jurassic_antler": lambda params: [
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": params.get("amount", 6),
            "hits": {"op": "add", "values": [
                1, {"op": "equipment_count", "target": params.get("target", "target")},
            ]},
        },
    ],
    "jurassic_pyrite_draw": lambda params: [
        {
            "op": "draw",
            "target": "self",
            "amount": {
                "op": "add",
                "values": [
                    1,
                    {"op": "floor", "value": {
                        "op": "div",
                        "values": [
                            {"op": "player_stat", "target": params.get("target", "target"), "stat": "fire"},
                            3,
                        ],
                    }},
                ],
            },
            "log": "{target}因黄铁矿抽{amount}张牌",
        },
    ],
    "void_scythe_damage": lambda params: [
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": {
                "op": "sub",
                "values": [
                    params.get("base", 40),
                    {
                        "op": "mul",
                        "values": [
                            params.get("per_hand", 5),
                            {"op": "player_stat", "target": "source", "stat": "hand_count"},
                        ],
                    },
                ],
            },
        },
    ],
    "void_add_void_to_hand": lambda params: [
        {
            "op": "give_card_to_hand",
            "card": "Void",
            "target": params.get("target", "self"),
            "log": "{target}将1张[[card:Void]]加入手中",
        },
    ],
    "hel_chip_attack": lambda params: [
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": params.get("amount", 6),
            "no_luck_crit": True,
        },
    ],
    "hel_blood_dice": lambda params: [
        {
            "op": "status_add_named",
            "status": LUCK_STATUS,
            "amount": params.get("luck", 10),
            "target": params.get("target", "target"),
            "log": "{target}获得{amount}层幸运",
        },
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": params.get("damage", 6),
            "force_crit": True,
        },
    ],
    "hel_magic_dice_attack": lambda params: [
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": 6,
            "on_crit": [
                {
                    "op": "direct_damage",
                    "target": params.get("target", "target"),
                    "amount": {
                        "op": "mul",
                        "values": [2, {"op": "status_stack", "target": "source", "status": LUCK_STATUS}],
                    },
                    "damage_type": "magic",
                    "damage_tag": "battery",
                },
                {"op": "status_remove_named", "status": LUCK_STATUS, "target": "source"},
            ],
        },
    ],
    "hel_magic_clover_trigger": lambda params: [
        {
            "op": "crit_multiplier_add",
            "amount": 1,
            "temporary": True,
            "target": params.get("target", "target"),
        },
        {
            "op": "status_add_named",
            "status": LUCK_STATUS,
            "amount": 8,
            "target": params.get("target", "target"),
            "log": "{target}本回合暴击倍率+1×并获得8层幸运",
        },
    ],
    "hel_trigger_fire_once": lambda params: [
        {
            "op": "resolve_status_once",
            "status": "fire",
            "reduce": params.get("reduce", 1),
            "target": params.get("target", "target"),
        },
    ],
    "jurassic_oil_turn_start": lambda params: [
        {
            "op": "resolve_status_once",
            "status": "fire",
            "reduce": 1,
            "target": params.get("target", "target"),
            "log": "{target}的石油使灼烧结算{amount}点并减少1层",
        },
    ],
    "desert_wind_schedule": lambda params: [
        {
            "op": "timed_effect",
            "trigger": "target_turn_start_after_draw",
            "duration": 1,
            "target": params.get("target", "target"),
            "body": [
                {
                    "op": "discard_hand_by_paid_e",
                    "target": "all_players",
                    "threshold": {
                        "op": "add",
                        "values": [{"op": "card_prop", "card": "current_card", "prop": "paid_e"}, 1],
                    },
                },
            ],
        },
    ],
    "ocean_status_tag_damage": lambda params: [
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": {
                "op": "add",
                "values": [
                    params.get("base", 30),
                    {
                        "op": "mul",
                        "values": [
                            params.get("per_status", 10),
                            {"op": "status_count", "target": params.get("target", "target")},
                        ],
                    },
                    {
                        "op": "mul",
                        "values": [
                            params.get("per_tag", 10),
                            {"op": "count", "of": {"op": "card_prop", "card": "current_card", "prop": "flags"}},
                        ],
                    },
                ],
            },
        },
    ],
    "ocean_dead_leaf_slow_if_no_counter": lambda params: [
        {
            "op": "if",
            "condition": {
                "op": "compare",
                "a": {"op": "counter_cards_in_hand", "target": params.get("target", "target")},
                "operator": "==",
                "b": 0,
            },
            "then": [
                {
                    "op": "status_add_named",
                    "status": "sluggish",
                    "amount": params.get("amount", 1),
                    "target": params.get("target", "target"),
                    "log": "{target}获得{amount}层迟缓",
                },
            ],
        },
    ],
    "bio_high_yield_bond": lambda params: [
        {
            "op": "deal_damage",
            "target": "self",
            "amount": 25,
            "ignore_untargetable": True,
            "log": "{target}受到25D、获得10层负债并回复10E",
        },
        {"op": "status_add_named", "status": "bio:debt", "amount": 10, "target": "self", "log": False},
        {"op": "gain_e", "target": "self", "amount": 10, "log": False},
    ],
    "bio_antibody_attack": lambda params: [
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": 0,
            "on_hit": [
                {
                    "op": "status_add_named",
                    "status": "jungle:fragile",
                    "amount": 1,
                    "target": params.get("target", "target"),
                    "log": "{target}获得1层易损",
                },
            ],
        },
    ],
    "sewers_broccoli_attack": lambda params: [
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": 10,
        },
        {
            "op": "if",
            "condition": {"op": "play_was_countered"},
            "then": [
                {
                    "op": "deal_damage",
                    "target": params.get("target", "target"),
                    "amount": 3,
                    "hits": 2,
                },
            ],
        },
    ],
    "sewers_iodine_trigger": lambda params: [
        {"op": "destroy_self_equipment"},
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": 12,
        },
        {
            "op": "status_add_named",
            "status": "poison",
            "amount": 12,
            "target": params.get("target", "target"),
            "log": "{target}+12层中毒",
        },
    ],
    "sewers_lotus_heal": lambda params: [
        {
            "op": "heal",
            "target": params.get("target", "target"),
            "amount": {
                "op": "max",
                "values": [
                    0,
                    {
                        "op": "sub",
                        "values": [
                            10,
                            {"op": "status_stack", "target": params.get("target", "target"), "status": "poison"},
                        ],
                    },
                ],
            },
        },
        {
            "op": "status_remove_named",
            "status": "poison",
            "target": params.get("target", "target"),
            "log": False,
        },
    ],
    "sewers_activate_light_bulb": lambda params: [
        {"op": "var_set", "name": "sewers_light_bulb_active", "value": 1, "target": "self"},
    ],
    "jurassic_clear_self_power": lambda params: [
        {
            "op": "card_prop_set",
            "card": {"ref": "current_card"},
            "property": "power_value",
            "value": 0,
        },
    ],
    "arctic_ice": lambda params: [
        {
            "op": "heal",
            "target": params.get("target", "target"),
            "amount": {
                "op": "max",
                "values": [
                    0,
                    {
                        "op": "sub",
                        "values": [
                            15,
                            {
                                "op": "mul",
                                "values": [
                                    5,
                                    {
                                        "op": "min",
                                        "values": [
                                            {"op": "status_stack", "target": params.get("target", "target"),
                                             "status": "fire"},
                                            3,
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        },
        {
            "op": "status_add_named",
            "status": "fire",
            "amount": {
                "op": "mul",
                "values": [
                    -1,
                    {
                        "op": "min",
                        "values": [
                            {"op": "status_stack", "target": params.get("target", "target"), "status": "fire"},
                            3,
                        ],
                    },
                ],
            },
            "target": params.get("target", "target"),
            "log": False,
        },
    ],
    "bio_ransom_money": lambda params: [
        {
            "op": "move_to_discard",
            "card": {"ref": "selected_card"},
            "target": "self",
            "log": "{target}将所选的牌从放逐区加入弃牌堆",
        },
    ],
    "bio_job_application": lambda params: [
        {
            "op": "list_append",
            "name": "bio_job_application_pending",
            "item": {"op": "source_player"},
            "target": params.get("target", "target"),
        },
        {
            "op": "log",
            "message": "{target}下个回合无法指向出牌者",
        },
    ],
    "sewers_basil_turn_start": lambda params: [
        {
            "op": "if",
            "condition": {
                "op": "compare",
                "a": {
                    "op": "mul",
                    "values": [100, {"op": "player_stat", "target": params.get("target", "target"), "stat": "health"}],
                },
                "operator": "<=",
                "b": {
                    "op": "mul",
                    "values": [40, {"op": "player_stat", "target": params.get("target", "target"), "stat": "max_health"}],
                },
            },
            "then": [
                {
                    "op": "heal",
                    "target": params.get("target", "target"),
                    "amount": 8,
                    "log": "{target}的罗勒回复{amount}H",
                },
            ],
            "else": [
                {
                    "op": "heal",
                    "target": params.get("target", "target"),
                    "amount": 3,
                    "log": "{target}的罗勒回复{amount}H",
                },
            ],
        },
    ],
}

# Card-specific overrides: the same card-specific op can need different data
# depending on which card calls it.
CARD_OP_REWRITES = {
    "Domino": {
        "hel_lucky_attack": lambda params: [
            {
                "op": "deal_damage",
                "target": params.get("target", "target"),
                "amount": params.get("amount", 6),
                "precognition": True,
                "crit_bonus_multiplier": 2,
            },
        ],
    },
    "Dice": {
        "hel_lucky_attack": lambda params: [
            {
                "op": "deal_damage",
                "target": params.get("target", "target"),
                "amount": params.get("amount", 6),
                "crit_bonus_damage": 3,
            },
        ],
    },
    "Poker Card": {
        "hel_card_attack": lambda params: [
            {
                "op": "var_set",
                "name": "hel_card_suit",
                "value": {
                    "op": "choice_value",
                    "key": "hel_suit",
                    "default": {"op": "random_choice", "values": ["heart", "diamond", "spade", "club"]},
                },
            },
            {
                "op": "deal_damage",
                "target": params.get("target", "target"),
                "amount": params.get("amount", 8),
                "crit_bonus_damage": {
                    "op": "mul",
                    "values": [
                        6,
                        {
                            "op": "compare",
                            "a": {"op": "player_var", "target": "source", "name": "hel_card_suit"},
                            "operator": "==",
                            "b": "diamond",
                        },
                    ],
                },
                "on_crit": [
                    {
                        "op": "if",
                        "condition": {
                            "op": "and",
                            "values": [
                                {
                                    "op": "compare",
                                    "a": {"op": "player_var", "target": "source", "name": "hel_card_suit"},
                                    "operator": "==",
                                    "b": "heart",
                                },
                                {
                                    "op": "compare",
                                    "a": {
                                        "op": "mul",
                                        "values": [
                                            2,
                                            {"op": "player_stat", "target": "source", "stat": "health"},
                                        ],
                                    },
                                    "operator": "<",
                                    "b": {"op": "player_stat", "target": "source", "stat": "max_health"},
                                },
                            ],
                        },
                        "then": [
                            {"op": "heal", "target": "source", "amount": 7, "log": "{target}的纸牌♥回复7H"},
                        ],
                    },
                    {
                        "op": "if",
                        "condition": {
                            "op": "compare",
                            "a": {"op": "player_var", "target": "source", "name": "hel_card_suit"},
                            "operator": "==",
                            "b": "spade",
                        },
                        "then": [
                            {"op": "draw", "target": "source", "amount": 1, "log": "{target}的纸牌♠抽1张牌"},
                        ],
                    },
                    {
                        "op": "if",
                        "condition": {
                            "op": "compare",
                            "a": {"op": "player_var", "target": "source", "name": "hel_card_suit"},
                            "operator": "==",
                            "b": "club",
                        },
                        "then": [
                            {
                                "op": "status_add_named",
                                "status": "poison",
                                "amount": 3,
                                "target": params.get("target", "target"),
                                "log": "{target}+3中毒",
                            },
                        ],
                    },
                ],
            },
        ],
    },
}

# --- generic bulk-zone primitives -------------------------------------------
# ``card_prop_add_to_zone`` / ``toggle_tag_in_zone`` / ``add_tag_to_zone`` are
# reusable engine atoms, so every "all cards in one zone gain layers" effect is
# plain data instead of a card-named handler.
def _temp_heavy_steps(params):
    kind = str(params.get("kind", "e") or "e").lower()
    if kind == "m":
        prop, tag = "temp_magic_heavy_value", "temp_magic_heavy"
    else:
        prop, tag = "temp_heavy_value", "temp_heavy"
    return [{
        "op": "card_prop_add_to_zone",
        "target": params.get("target", "self"),
        "zone": "hand",
        "property": prop,
        "amount": params.get("amount", 1),
        "tag": tag,
        "log": False,
    }]


GENERIC_STEP_REWRITES.update({
    "ocean_random_blind_hand": lambda params: [
        {
            "op": "card_prop_add_to_zone",
            "target": params.get("target", "target"),
            "zone": "hand",
            "property": "hand_blind_turns",
            "amount": 1,
            "mode": "max",
            "tag": "ocean_blinded",
            "count": params.get("count", 3),
            "random": True,
            "log": "{target}的{count}张手牌被蒙蔽",
        },
        {"op": "shuffle_hand", "target": params.get("target", "target"), "log": False},
    ],
    "bio_indictment_response": lambda params: [{
        "op": "mark_original_card",
        "marker": "_bio_indictment_target_id",
        "value": "self",
        "log": "{source}的起诉书将所响应攻击牌的伤害转化为护盾",
    }],
    "bio_diamond_attack": lambda params: [{
        "op": "deal_damage",
        "target": params.get("target", "target"),
        "amount": params.get("amount", 10),
        "on_hit_once": [{
            "op": "if",
            "condition": {
                "op": "not",
                "condition": {
                    "op": "card_has_modifier",
                    "card": "current_card",
                    "modifier": "bio_diamond_copy",
                },
            },
            "then": _copy_self_steps(
                params,
                source="pre_play_snapshot",
                flags=["wide_strike", "self_target", "exile", "swift"],
                setup_modifiers=["bio_diamond_copy"],
                fission_level=3,
                swift_value=2,
            ) + [{
                "op": "auto_play_card",
                "card": {"ref": "last_created_card"},
                "no_cost": False,
                "log": "{target}的钻石额外打出一张复制",
            }],
        }],
    }],
    "bio_electron_missile": lambda params: [{
        "op": "deal_damage",
        "target": params.get("target", "target"),
        "amount": params.get("amount", 3),
        "on_hit_once": [{
            "op": "card_prop_add_to_zone",
            "target": "target",
            "zone": "hand",
            "property": "charge_value",
            "amount": 1,
            "tag": "charge",
            "count": params.get("max_cards", "all"),
            "random": True,
            "log": False,
        }],
    }],
    "sewers_quartz": lambda params: [{
        "op": "card_prop_add_to_zone",
        "target": "self",
        "zone": "hand",
        "property": "temp_swift_value",
        "amount": 1,
        "tag": "temp_swift",
        "log": "{target}的{count}张手牌获得暂时迅捷:{amount}",
    }],
    "void_add_temp_heavy_to_hand": _temp_heavy_steps,
    "jurassic_add_power_to_hand": lambda params: [{
        "op": "card_prop_add_to_zone",
        "target": params.get("target", "target"),
        "zone": "hand",
        "property": "power_value",
        "amount": params.get("amount", 3),
        "card_type": "thorn",
        "tag": "power",
        "log": "{target}的{count}张攻击牌获得{amount}层威力",
    }],
    "void_soap_wide_strike": lambda params: [
        {
            "op": "add_tag_to_zone",
            "target": params.get("target", "target"),
            "zone": zone,
            "tag": "wide_strike",
            "card_type": "thorn",
            "silent": True,
        }
        for zone in ("hand", "deck", "discard")
    ],
    "void_toggle_void_hand": lambda params: [{
        "op": "toggle_tag_in_zone",
        "target": params.get("target", "target"),
        "zone": "hand",
        "tag": "void",
        "log": False,
    }],
    "void_give_selected_hand_flag": lambda params: [{
        "op": "add_tag",
        "card": {"ref": "selected_card"},
        "tag": params.get("flag", "floating"),
        "log": False,
    }],
    "bio_clear_poison_fire": lambda params: [{
        "op": "clear_status",
        # Cyanide Pill is a wide-strike play: clear every chosen target, not
        # just the primary one.
        "target": "wide_strike_targets" if params.get("target", "target") in ("target", None) else params["target"],
        "status": status,
        "log": params.get("log", False) if status == "poison" else False,
    } for status in ("poison", "burn")],
    "void_add_card_to_deck": lambda params: [{
        "op": "give_card_to_deck",
        "target": params.get("target", "target"),
        "card": params.get("def_id", "void:air"),
        "position": params.get("position", "top"),
        "flags": params.get("flags", []),
        "log": False,
    }],
    "void_damage_all_except_self": lambda params: [{
        "op": "deal_damage",
        "target": "all_others",
        "amount": params.get("amount", 25),
    }],
    "jurassic_amulet": lambda params: [
        {
            "op": "for_each_selected_card",
            "body": [{
                "op": "move_to_discard",
                "card": {"ref": "chosen_card"},
                "log": False,
            }],
        },
        {
            "op": "log",
            "msg": "{target}丢弃{amount}张牌",
            "amount": {"op": "selected_cards_count"},
        },
        {
            "op": "card_prop_add_to_zone",
            "target": params.get("target", "target"),
            "zone": "hand",
            "property": "power_value",
            "amount": 5,
            "card_type": "thorn",
            "tag": "power",
            "log": False,
        },
    ],
    "desert_topaz_apply": lambda params: [],
    "jurassic_magic_rock": lambda params: [{
        "op": "deal_damage",
        "target": params.get("target", "target"),
        "amount": params.get("amount", 5),
        "on_hit": [
            {"op": "add_tag", "card": "current_card", "tag": "return_to_hand", "log": False},
            {
                "op": "apply_jungle_status",
                "target": "target",
                "status": "jungle:fragile",
                "amount": 1,
                "label": "易损",
                "log": False,
            },
            {
                "op": "log",
                "msg": "{target}获得1层易损，{name}回到手中",
            },
        ],
    }],
    "jurassic_blood_turn_start": lambda params: [
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "source": params.get("target", "target"),
            "amount": params.get("amount", 5),
            "ignore_untargetable": True,
            "log": False,
        },
        {
            "op": "draw",
            "target": params.get("target", "target"),
            "amount": 2,
            "log": "{target}因血受到伤害并抽{amount}张牌",
        },
    ],
    "void_set_void_all_cards": lambda params: [
        {
            "op": "add_tag_to_zone" if params.get("enabled", True) else "remove_tag_from_zone",
            "target": params.get("target", "self"),
            "zone": zone,
            "tag": "void",
            "silent": True,
        }
        for zone in ("hand", "deck", "discard", "exile")
    ],
    "void_exile_selected_card": lambda params: [
        {"op": "move_to_exile", "card": {"ref": "selected_card"}, "silent": True},
    ] + ([{
        "op": "give_card_to_deck" if params.get("zone") == "deck" else "give_card_to_hand",
        "target": params.get("target", "target"),
        "card": params["add_def_id"],
        "position": "random",
        "log": False,
    }] if params.get("add_def_id") else []),
    "void_move_selected_card": lambda params: [{
        "op": {
            "deck_top": "move_to_deck",
            "deck_random": "move_to_deck",
            "hand": "move_to_hand",
            "exile": "move_to_exile",
            "discard": "move_to_discard",
        }.get(str(params.get("to_zone", "discard")), "move_to_discard"),
        "card": {"ref": "selected_card"},
        "target": params.get("target", "target"),
        "position": "random" if params.get("to_zone") == "deck_random" else "top",
        "silent": True,
    }],
    "void_copy_response_card": lambda params: [
        {"op": "copy_card", "card": {"ref": "original_card"}, "log": False},
        {"op": "add_tag", "card": {"ref": "last_created_card"}, "tag": "exile", "log": False},
    ],
    "sewers_iodine_turn_start": lambda params: [{
        "op": "heal",
        "target": "all_selectable",
        "amount": 5,
        "log": "{source}的碘使{target}回复{amount}H",
    }],
    "ocean_charge_self_damage": lambda params: [{
        "op": "once_per_play",
        "key": "ocean_charge",
        "steps": [{
            "op": "direct_damage",
            "target": "self",
            "amount": {"op": "card_prop", "card": "current_card", "property": "charge_value"},
            "source": "电荷",
            "damage_type": "magic",
            "damage_tag": "gtn:battery",
        }],
    }],
    "ocean_add_charge_to_hand": lambda params: [
        {
            "op": "if",
            "condition": {
                "op": "compare",
                "a": {"op": "last_damage"},
                "operator": ">",
                "b": 0,
            },
            "then": [{
                "op": "card_prop_add_to_zone",
                "target": params.get("target", "target"),
                "zone": "hand",
                "property": "charge_value",
                "amount": params.get("amount", 3),
                "tag": "charge",
                "count": params.get("count", "all"),
                "random": True,
                "log": "{target}的{count}张手牌获得{amount}层电荷",
            }],
        },
    ] if params.get("require_hit") else [{
        "op": "card_prop_add_to_zone",
        "target": params.get("target", "target"),
        "zone": "hand",
        "property": "charge_value",
        "amount": params.get("amount", 3),
        "tag": "charge",
        "count": params.get("count", "all"),
        "random": True,
        "log": "{target}的{count}张手牌获得{amount}层电荷",
    }],
})

def _player_status(status, amount, target="play_targets", log=False):
    return {"op": "status_add_named", "status": status, "amount": amount, "target": target, "log": log}


def _self_damage(amount, source):
    return {
        "op": "direct_damage",
        "target": "self",
        "amount": amount,
        "source": source,
        "damage_type": "physical",
        "damage_tag": "gtn:physical",
    }


def _bomb_attack_steps(params, statuses, amount_key="damage", status_key="fire"):
    amount = params.get(amount_key, 6)
    require_hit = bool(params.get("require_hit"))
    resolved = [
        {"op": "status_add_named", "status": status, "amount": amount_value,
         "target": "play_targets", "log": False}
        for status, amount_value in statuses
    ]
    damage = {"op": "deal_damage", "target": "target", "amount": amount}
    if require_hit:
        # ``on_hit_once`` fires once per damaged player; plain ``on_hit`` would
        # repeat the status for every extra hit the card has.
        damage["on_hit_once"] = list(resolved)
        return [damage]
    return [damage] + resolved


def _void_dlc_action_steps(params):
    action = str(params.get("action") or "")
    builder = VOID_ACTION_REWRITES.get(action)
    if builder is None:
        return [{"op": "void_dlc_action", **params}]
    return builder(params)


# ``void_dlc_action`` is a pocket of named actions; each entry below replaces the
# action with generic data steps.
VOID_ACTION_REWRITES = {
    "bomb_attack": lambda params: _bomb_attack_steps(params, [("overload", 1), ("weakness", 1)]),
    "fire_bomb_attack": lambda params: _bomb_attack_steps(params, [("fire", params.get("fire", params.get("blaze", 3)))]),
    "magic_bomb_attack": lambda params: [
        {"op": "deal_damage", "target": "target", "amount": params.get("damage", 20)},
        _player_status("skip_turn", 1),
    ],
    "dvd_attack": lambda params: _bomb_attack_steps(params, [("fire", 1)]),
    "pipe_bomb_attack": lambda params: [
        {"op": "deal_damage", "target": "target", "amount": params.get("damage", 16)},
    ] + ([{"op": "turn_control", "mode": "end", "target": "self", "log": False}] if params.get("end_turn") else []),
    "dvd_return": lambda params: [
        {"op": "move_to_hand", "card": "current_card", "target": "self", "silent": True},
        {"op": "log", "msg": "{target}的{name}回到手中"},
    ],
    "fan_turn_start": lambda params: [],
    "schizo_turn_start": lambda params: [],
    "add_void_to_hand": lambda params: [
        {"op": "give_card_to_hand", "target": "self", "card": "void:void",
         "overflow": "discard", "missing": "skip", "log": False},
    ],
    "apply_status": lambda params: [
        _player_status(params.get("status", ""), params.get("amount", 1)),
    ],
    "one_ring": lambda params: [
        _player_status("hel:blazing_fire", params.get("blaze", 2)),
        _player_status("fire", params.get("fire", 1)),
    ],
    "comb_statuses": lambda params: [
        _player_status("hel:blazing_fire", 1),
        _player_status("fire", 1),
        _player_status("jungle:toxic_poison", 1),
        _player_status("poison", 1),
    ],
    "magic_slime_ball": lambda params: [
        _player_status("skip_turn", 1),
        _player_status("sluggish", 1, target="self"),
    ],
    "blood_scythe": lambda params: [
        {"op": "deal_damage", "target": "target", "amount": params.get("target_damage", 40)},
        _self_damage(params.get("self_damage", 4), "血镰刀"),
    ],
    "hexagram": lambda params: [
        {"op": "deal_damage", "target": "target", "amount": params.get("target_damage", 20)},
        _player_status("fire", params.get("fire", 10)),
        _self_damage(params.get("self_damage", 5), "六芒星"),
    ],
    "magic_blood_scythe": lambda params: [
        _player_status("fire", 3, target="self"),
        _player_status("arctic:frost", 3, target="self"),
        _player_status("poison", 3, target="self"),
        {"op": "deal_damage", "target": "target", "amount": params.get("damage", 50)},
    ],
    "plasma_attack": lambda params: [
        _player_status("poison", params.get("amount", 4)),
        _player_status("fire", params.get("amount", 4)),
        {
            "op": "card_prop_add_to_zone",
            "target": "play_targets",
            "zone": "hand",
            "property": "charge_value",
            "amount": params.get("amount", 4),
            "tag": "charge",
            "count": 1,
            "random": True,
            "log": False,
        },
        {"op": "deal_damage", "target": "target", "amount": params.get("damage", 4)},
        {
            "op": "direct_damage",
            "target": "target",
            "amount": params.get("electric", 4),
            "source": "等离子体电伤",
            "damage_type": "magic",
            "damage_tag": "gtn:battery",
        },
    ],
    "charge_hand": lambda params: [{
        "op": "card_prop_add_to_zone",
        "target": "play_targets",
        "zone": "hand",
        "property": "charge_value",
        "amount": params.get("amount", 1),
        "tag": "charge",
        "require_selectable": False,
        "log": "{target}的所有手牌获得{amount}层电荷",
    }],
    "fan_play": lambda params: [
        _player_status("fire", 2),
        {"op": "resolve_status_once", "status": "fire", "target": "play_targets", "reduce": 1, "log": False},
        {"op": "gain_e", "target": "play_targets", "amount": 4,
         "log": "{target}因扇子获得{amount}E"},
    ],
    "horn_response": lambda params: [{
        "op": "deal_damage",
        "target": "all_enemies",
        "amount": params.get("damage", 10),
    }],
    "magic_nut_attack": lambda params: [
        {"op": "var_set", "name": "nut_e_spent",
         "value": {"op": "player_stat", "target": "self", "stat": "elixir"}},
        {"op": "spend_resource", "resource": "elixir", "amount": {"op": "var", "name": "nut_e_spent"}, "log": False},
        {"op": "deal_damage", "target": "target",
         "amount": {"op": "add", "values": [
             params.get("base", 10),
             {"op": "mul", "values": [params.get("per_e", 5), {"op": "var", "name": "nut_e_spent"}]},
         ]}},
    ],
    "magic_blood_scythe_exile": lambda params: [{
        "op": "if",
        "condition": {"op": "compare", "a": {"op": "hand_count", "target": "self"}, "operator": "<=", "b": 0},
        "then": [_player_status("bio:debt", 1, target="self")],
        "else": [{
            "op": "for_each_list",
            "name": "item",
            "list": {"ref": "zone_list", "target": "self", "zone": "hand"},
            "limit": 2,
            "body": [{"op": "move_to_exile", "card": {"ref": "var", "name": "item"}, "silent": True}],
        }],
    }],
}

# ``void_dlc_action`` dispatches on its ``action`` parameter.
GENERIC_STEP_REWRITES["void_dlc_action"] = _void_dlc_action_steps


def _copy_self_steps(params, **overrides):
    """Shared skeleton of the "copy my own instance" card effects."""
    step = {
        "op": "copy_card_instance",
        "source": params.get("source", "current_card"),
        "target": params.get("target", "self"),
        "zone": "hand",
        "fission_level": params.get("fission_level", 3),
        "swift_value": params.get("swift_value", 3),
        "unique_copy_penalty": True,
        "hand_full": "discard",
        "log": False,
    }
    step.update(overrides)
    return [step]


GENERIC_STEP_REWRITES.update({
    "arctic_snowflake_copy": lambda params: [{
        "op": "if",
        "condition": {"op": "not", "condition": {"op": "card_has_tag", "card": "current_card", "tag": "wide_strike"}},
        "then": _copy_self_steps(
            params,
            flags=["wide_strike", "arctic:ready", "exile"],
            fission_level={"op": "max", "values": [
                3, {"op": "card_prop", "card": "current_card", "prop": "fission_level"}]},
            swift_value={"op": "max", "values": [
                3, {"op": "card_prop", "card": "current_card", "prop": "swift_value"}]},
        ),
    }],
    "arctic_icicle_shuffle_discard": lambda params: _copy_self_steps(
        params,
        zone="discard",
        position="random",
        reset_after_play=True,
        flags=[],
        fission_level=None,
        swift_value=None,
    ),
    "arctic_pinecone_copy": lambda params: [{
        "op": "if",
        "condition": {
            "op": "not",
            "condition": {"op": "card_has_modifier", "card": "current_card", "modifier": "arctic_pinecone_copy"},
        },
        "then": _copy_self_steps(
            params,
            source="pre_play_snapshot",
            flags=["wide_strike", "self_target", "exile", "swift"],
            setup_modifiers=["arctic_pinecone_copy"],
            swift_value={"op": "max", "values": [
                2, {"op": "card_prop", "card": "current_card", "prop": "swift_value"}]},
        ) + [{
            "op": "auto_play_card",
            "card": {"ref": "last_created_card"},
            "no_cost": False,
            "empty_selection_ok": True,
            "log": "{target}的松果额外打出一张复制",
        }],
    }],
})


# --- rule modules -----------------------------------------------------------
# Extra rewrite rules may live in ``tools/refactor_rules/*.py``, one module per
# package.  Every module exposes ``REWRITES = {op_name: builder}`` with the same
# signature as ``GENERIC_STEP_REWRITES``, so work on different packages never has
# to edit this file (and can therefore run in parallel).  Rules defined inline
# above win over module rules for the same op name.
SKIPPED_RULE_MODULES: list = []


def _load_rule_modules() -> None:
    directory = ROOT / "tools" / "refactor_rules"
    if not directory.is_dir():
        return
    import importlib.util

    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location("gtn_refactor_rules_%s" % path.stem, path)
        if spec is None or spec.loader is None:
            SKIPPED_RULE_MODULES.append((path.name, "no import loader"))
            continue
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # pragma: no cover - authoring aid
            SKIPPED_RULE_MODULES.append((path.name, repr(exc)))
            continue
        rules = getattr(module, "REWRITES", None)
        if not isinstance(rules, dict):
            SKIPPED_RULE_MODULES.append((path.name, "no REWRITES dict"))
        else:
            for op, builder in rules.items():
                if not callable(builder):
                    SKIPPED_RULE_MODULES.append((path.name, "non-callable rule for %s" % op))
                    continue
                GENERIC_STEP_REWRITES.setdefault(op, builder)
        # ``CARD_REWRITES`` allows per-card overrides (card name -> {op: builder}),
        # which is how a module expresses "this op behaves differently for one
        # card" (for example a ``self_target`` wide-strike card that must hit
        # every selectable player instead of the enemies only).
        card_rules = getattr(module, "CARD_REWRITES", None)
        if isinstance(card_rules, dict):
            for card_name, entries in card_rules.items():
                if not isinstance(entries, dict):
                    SKIPPED_RULE_MODULES.append((path.name, "bad CARD_REWRITES for %s" % card_name))
                    continue
                bucket = CARD_OP_REWRITES.setdefault(str(card_name), {})
                for op, builder in entries.items():
                    if not callable(builder):
                        SKIPPED_RULE_MODULES.append(
                            (path.name, "non-callable card rule %s/%s" % (card_name, op))
                        )
                        continue
                    bucket[op] = builder
        elif card_rules is not None:
            SKIPPED_RULE_MODULES.append((path.name, "bad CARD_REWRITES table"))


_load_rule_modules()


# Cards whose whole event set can be swapped for a generic op.
CARD_STEP_OVERRIDES = {}


def rewrite_step(step: dict, card_name: str = "") -> list:
    if not isinstance(step, dict):
        return [step]
    op = str(step.get("op") or step.get("type") or "")
    builder = (CARD_OP_REWRITES.get(card_name) or {}).get(op) or GENERIC_STEP_REWRITES.get(op)
    if builder is None:
        return [step]
    params = step.get("params")
    if not isinstance(params, dict):
        params = {k: v for k, v in step.items() if k not in ("op", "type", "params")}
    return builder(params)


def rewrite_steps(steps, card_name: str = "") -> list:
    out = []
    for step in steps or []:
        for new_step in rewrite_step(step, card_name):
            normalise_step(new_step, card_name)
            for key in ("then", "else", "body", "steps", "on_hit", "on_crit", "on_cancel"):
                child = new_step.get(key)
                if isinstance(child, list):
                    new_step[key] = rewrite_steps(child, card_name)
            params_block = new_step.get("params")
            if isinstance(params_block, dict):
                for key in ("then", "else", "body", "steps", "on_hit", "on_crit", "on_cancel"):
                    child = params_block.get(key)
                    if isinstance(child, list):
                        params_block[key] = rewrite_steps(child, card_name)
            out.append(new_step)
    return out


# Cards created by converted steps must keep the original "overflow into the
# discard pile" behaviour of PlayerState.add_to_hand.
OVERFLOW_GIVE_CARDS = {"Yggdrasil", "Maple", "Void"}


def normalise_step(step: dict, card_name: str = "") -> None:
    if not isinstance(step, dict):
        return
    if step.get("op") == "give_card_to_hand" and step.get("card") in OVERFLOW_GIVE_CARDS:
        step.setdefault("overflow", "discard")
    if card_name == "Dice" and step.get("op") == "deal_damage":
        # Dice adds a flat +3D to its critical hit (was hardcoded in the engine).
        step.setdefault("crit_bonus_damage", 3)


def rewrite_events(events, card_name: str = "") -> bool:
    changed = False
    if not isinstance(events, dict):
        return False
    before = copy.deepcopy(events)
    for name, entry in events.items():
        if isinstance(entry, dict) and isinstance(entry.get("steps"), list):
            new_steps = rewrite_steps(entry.get("steps"), card_name)
            if new_steps != entry.get("steps"):
                entry["steps"] = new_steps
                changed = True
        elif isinstance(entry, list):
            new_steps = rewrite_steps(entry, card_name)
            if new_steps != entry:
                events[name] = new_steps
                changed = True
    # Nested rewrites mutate child dicts in place, so compare against a snapshot
    # instead of trusting the identity of the rewritten lists.
    return changed or before != events


def write_package(path: pathlib.Path, members: dict) -> None:
    handle, temp_name = tempfile.mkstemp(suffix=".gtnmod", dir=str(path.parent))
    os.close(handle)
    temp_path = pathlib.Path(temp_name)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for name, content in members.items():
                zf.writestr(name, content)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="Rewrite card-specific engine atoms into generic steps.")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="GLOB",
        help="only rewrite package files matching this glob (repeatable), e.g. --only 'Arctic*'",
    )
    args = parser.parse_args()
    total = 0
    packages = [
        path
        for path in sorted(MODS.glob("*.gtnmod"))
        if not args.only or any(path.match(pattern) for pattern in args.only)
    ]
    for path in packages:
        with zipfile.ZipFile(path, "r") as zf:
            members = {item.filename: zf.read(item.filename) for item in zf.infolist()}
        data = json.loads(members["mod.json"].decode("utf-8-sig"))
        changed = []
        for card in data.get("registries", {}).get("cards", []) or []:
            card_name = str(card.get("name_en") or "")
            for key in ("events", "v2_events"):
                if rewrite_events(card.get(key), card_name):
                    changed.append(card.get("name_en") or card.get("id"))
        if not changed:
            continue
        members["mod.json"] = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        write_package(path, members)
        total += len(set(changed))
        print("refactored", path.name, "->", ", ".join(sorted(set(changed))))
    print("packages scanned", len(packages), "| total cards", total)
    for name, reason in SKIPPED_RULE_MODULES:
        print("WARNING: skipped rule module %s (%s)" % (name, reason), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
