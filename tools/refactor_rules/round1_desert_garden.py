# -*- coding: utf-8 -*-
"""Round 1 卡专用原子改写规则：Desert Cards DLC / Garden Cards DLC / Factory Cards Addition.

子代理 rd1_desert_garden 负责的 8 个卡专用原子。这里只使用通用能力
（mod_runtime_v2 的 op、ADVANCED_ATOMIC_OPS 里的通用原子、以及
tools/refactor_card_atoms.py 中已经出现过的组合写法）。

本模块提供规则的 4 个原子：

* ``desert_emerald_resource``
    装备事件 on_resource_spent 分支：把装备自定义变量当计数器累积，
    每累计 2E 由装备者回复 1M（``equipment_prop_add/set`` + ``gain_m``）。
* ``garden_daisy_attack``
    先以 1 段物理攻击结算 9D，造成实际伤害时用 ``timed_effect`` 注册
    "目标下回合开始时再造成 4D" 的延迟效果（延迟体是通用 ``damage`` 原子）。
* ``garden_mecha_antennae``
    按类型给目标手牌/抽牌堆/弃牌堆/放逐区的牌添加被揭示标签
    （``add_tag_to_zone`` x4），再按通用规则补满抽牌堆
    （``shuffle_discard_into_deck``）。
* ``garden_mecha_antennae_resolve``
    从抽牌堆顶 3 张里取走玩家选中的 1 张（手牌已满时改为弃置），
    其余置入弃牌堆（``for_each`` + ``deck_top_ids`` + ``move_to_hand`` /
    ``move_to_discard``）。

没有规则、记入报告"缺口"的 3 个原子：
``desert_magic_compass``（选中牌随机置于抽牌堆顶）、
``desert_marble_attack``（随机可选中副目标弹射）、
``reveal_card_set``（初始牌组快照与私有展示；Round 22 前的旧名
``garden_show_initial_deck`` 已经删除）。
"""

from __future__ import annotations

EMERALD_COUNTER = "desert_emerald_e_spent"

DAISY_DELAY_LOG = "雏菊造成延迟伤害"

MECHA_TOP_ID_VAR = "mecha_antennae_top_id"
MECHA_PICK_VAR = "mecha_antennae_resolve_pick"
MECHA_PICK_VALID_VAR = "mecha_antennae_resolve_pick_valid"
MECHA_PICK_NAME_VAR = "mecha_antennae_resolve_pick_name"
MECHA_RESOLVE_LOG = "从抽牌堆顶3张中取走{" + MECHA_PICK_NAME_VAR + "}，其余置入弃牌堆"


def _emerald_steps(params):
    """沙漠绿宝石：目标每累计消耗 2E，为装备者回复 1M。"""
    equipment = {"ref": "current_equipment"}
    spent_now = {"op": "var", "name": "amount"}
    # 计数器的读取在每一步执行时才求值：先累加，再按累加后的值算触发次数与余数。
    counter = {"op": "equipment_prop", "equipment": equipment, "property": EMERALD_COUNTER}
    triggers = {"op": "floor", "value": {"op": "div", "a": counter, "b": 2}}
    triggers_var = "desert_emerald_triggers"
    remainder = {
        "op": "sub",
        "values": [counter, {"op": "mul", "values": [{"op": "var", "name": triggers_var}, 2]}],
    }
    return [
        {
            "op": "if",
            "condition": {
                "op": "and",
                "conditions": [
                    {
                        "op": "compare",
                        "a": {"op": "var", "name": "resource"},
                        "operator": "==",
                        "b": "elixir",
                    },
                    {
                        "op": "compare",
                        "a": {"op": "damage_source"},
                        "operator": "==",
                        "b": {"op": "equipment_prop", "equipment": equipment, "property": "effect_target"},
                    },
                ],
            },
            "then": [
                {
                    "op": "equipment_prop_add",
                    "equipment": equipment,
                    "property": EMERALD_COUNTER,
                    "amount": spent_now,
                },
                {
                    "op": "set_var",
                    "name": triggers_var,
                    "value": triggers,
                },
                {
                    "op": "equipment_prop_set",
                    "equipment": equipment,
                    "property": EMERALD_COUNTER,
                    "value": remainder,
                },
                {
                    "op": "if",
                    "condition": {
                        "op": "compare",
                        "a": {"op": "var", "name": triggers_var},
                        "operator": ">",
                        "b": 0,
                    },
                    "then": [
                        {
                            "op": "gain_m",
                            "target": "self",
                            "amount": {"op": "var", "name": triggers_var},
                        },
                    ],
                },
            ],
        }
    ]


def _daisy_steps(params):
    """雏菊：9D 单体攻击；造成实际伤害时登记延迟的 4D。"""
    target = params.get("target", "target")
    amount = params.get("amount", 9)
    delayed_amount = params.get("delayed_amount", 4)
    return [
        {
            "op": "deal_damage",
            "target": target,
            "amount": amount,
            "hits": 1,
            "inherit_extra_hits": False,
        },
        {
            "op": "if",
            "condition": {"op": "compare", "a": {"op": "last_damage"}, "operator": ">", "b": 0},
            "then": [
                {
                    "op": "timed_effect",
                    "trigger": "target_turn_start",
                    "duration": 1,
                    "target": target,
                    "body": [
                        {
                            "op": "damage",
                            "target": "target",
                            "amount": delayed_amount,
                            "log": DAISY_DELAY_LOG,
                        }
                    ],
                }
            ],
        },
    ]


def _mecha_antennae_steps(params):
    """机械触角（前半）：按类型给目标各区域的牌添加被揭示，并补满抽牌堆。"""
    target = params.get("target", "target")
    card_type = params.get("card_type")
    steps = [
        {
            "op": "add_tag_to_zone",
            "target": target,
            "zone": zone,
            "tag": "revealed",
            "card_type": card_type,
        }
        for zone in ("hand", "deck", "discard", "exile")
    ]
    steps.append(
        {
            "op": "if",
            "condition": {
                "op": "and",
                "conditions": [
                    {
                        "op": "compare",
                        "a": {"op": "deck_count", "target": "self"},
                        "operator": "<",
                        "b": 3,
                    },
                    {
                        "op": "compare",
                        "a": {"op": "discard_count", "target": "self"},
                        "operator": ">",
                        "b": 0,
                    },
                ],
            },
            "then": [{"op": "shuffle_discard_into_deck"}],
        }
    )
    return steps


def _mecha_top_card_ref():
    return {
        "ref": "card_instance",
        "instance_id": {"op": "var", "name": MECHA_TOP_ID_VAR},
    }


def _mecha_antennae_resolve_steps(params):
    """机械触角（后半）：抽牌堆顶 3 张取 1 入手，其余弃置。"""
    target = params.get("target", "source")
    top_ids = {"op": "deck_top_ids", "target": target, "count": 3}
    picked_id = params.get(
        "card_id",
        {
            "op": "get",
            "object": {"op": "var", "name": "mecha_antennae_pick"},
            "key": "pick",
            "default": -1,
        },
    )
    matches_pick = {
        "op": "compare",
        "a": {"op": "var", "name": MECHA_TOP_ID_VAR},
        "operator": "==",
        "b": {"op": "var", "name": MECHA_PICK_VAR},
    }
    move_to_discard = {
        "op": "move_to_discard",
        "card": _mecha_top_card_ref(),
        "silent": True,
    }
    move_chosen = {
        "op": "if",
        "condition": {
            "op": "compare",
            "a": {"op": "hand_full", "target": target},
            "operator": "==",
            "b": False,
        },
        "then": [
            {
                "op": "move_to_hand",
                "card": _mecha_top_card_ref(),
                "target": target,
            }
        ],
        "else": [dict(move_to_discard)],
    }
    return [
        {"op": "set_var", "name": MECHA_PICK_VAR, "value": picked_id},
        {"op": "set_var", "name": MECHA_PICK_VALID_VAR, "value": 0},
        {
            "op": "for_each",
            "items": top_ids,
            "as": MECHA_TOP_ID_VAR,
            "steps": [
                {
                    "op": "if",
                    "condition": matches_pick,
                    "then": [{"op": "set_var", "name": MECHA_PICK_VALID_VAR, "value": 1}],
                }
            ],
        },
        {
            "op": "if",
            "condition": {
                "op": "compare",
                "a": {"op": "var", "name": MECHA_PICK_VALID_VAR},
                "operator": "==",
                "b": 0,
            },
            "then": [
                {
                    "op": "set_var",
                    "name": MECHA_PICK_VAR,
                    "value": {"op": "get", "object": top_ids, "key": 0, "default": -1},
                }
            ],
        },
        {
            "op": "for_each",
            "items": top_ids,
            "as": MECHA_TOP_ID_VAR,
            "steps": [
                {
                    "op": "if",
                    "condition": matches_pick,
                    "then": [move_chosen],
                    "else": [dict(move_to_discard)],
                }
            ],
        },
        {
            "op": "set_var",
            "name": MECHA_PICK_NAME_VAR,
            "value": {
                "op": "card_prop",
                "card": {
                    "ref": "card_by_instance_id",
                    "instance_id": {"op": "var", "name": MECHA_PICK_VAR},
                },
                "prop": "name_cn",
            },
        },
        {
            "op": "if",
            "condition": {
                "op": "compare",
                "a": {"op": "var", "name": MECHA_PICK_VAR},
                "operator": ">=",
                "b": 0,
            },
            "then": [{"op": "log", "message": MECHA_RESOLVE_LOG}],
        },
    ]


REWRITES = {
    "desert_emerald_resource": _emerald_steps,
    "garden_daisy_attack": _daisy_steps,
    "garden_mecha_antennae": _mecha_antennae_steps,
    "garden_mecha_antennae_resolve": _mecha_antennae_resolve_steps,
}
