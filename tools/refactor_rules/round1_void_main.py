# -*- coding: utf-8 -*-
"""Round 1 rewrites for ``mods/Void Card Addition.gtnmod`` (agent rd1_void_main).

Converted card-specific ops (data only, no engine changes):

* ``void_antimatter_damage``          -> conditional exile tag + ``deal_damage``
* ``void_exile_target_hand``          -> ``for_each`` over the target hand + fragile status
* ``void_magic_corruption``           -> ``add_equipment_to_zone`` + ``equipment_prop_set``
* ``void_magic_wing_damage``          -> spend M into a var + ``deal_damage`` with scaled hits
* ``void_puppeteer``                  -> ``var_set`` on the target player var
* ``void_satan_swap``                 -> snapshots + ``player_prop_set`` + ``player_prop_set``

Not converted (capability gaps, see ``.codex-tmp/round1/rd1_void_main.md``):
``void_kitty_auto_play``, ``void_quantum_randomize``, ``void_transform_own_cards``,
``void_turn_count_damage``, ``void_magic_relativity_damage_end``.
"""


def _temp(name):
    """Runtime (per-effect) variable reference."""
    return {"op": "var", "name": name}


def _player_var(name, target="self"):
    """Per-player ``custom_vars`` reference (engine-side variable store)."""
    return {"op": "var", "target": target, "name": name}


def _stat(target, stat):
    return {"op": "player_stat", "target": target, "stat": stat}


def _void_antimatter_damage(params):
    # 对目标造成10D；若自己上一张使用的牌为反物质，此牌获得放逐
    # 引擎在打出时会把上一张牌的 def_id 放进 void_current_previous_def_id。
    condition = {
        "op": "or",
        "conditions": [
            {"op": "compare", "a": _player_var("void_current_previous_def_id"),
             "operator": "==", "b": "void:antimatter"},
            {"op": "compare", "a": _player_var("void_current_previous_def_id"),
             "operator": "==", "b": "Antimatter"},
        ],
    }
    return [
        {
            "op": "if",
            "condition": condition,
            "then": [{"op": "add_tag", "card": {"ref": "current_card"}, "tag": "exile", "log": False}],
        },
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": params.get("amount", 10),
        },
    ]


def _void_exile_target_hand(params):
    # 放逐目标所有手牌（崇高牌不可被效果选中，需排除），再施加等量易损
    selectable = {
        "op": "not",
        "condition": {
            "op": "or",
            "conditions": [
                {"op": "card_has_tag", "card": {"ref": "var", "name": "void_hand_card"}, "tag": "sublime"},
                {"op": "card_has_tag", "card": {"ref": "var", "name": "void_hand_card"}, "tag": "vanilla:sublime"},
            ],
        },
    }
    return [
        {"op": "set_var", "name": "void_exiled_hand_count", "value": 0},
        {
            "op": "for_each",
            "var": "void_hand_card",
            "items": {"ref": "zone", "zone": "hand", "target": params.get("target", "target")},
            "steps": [
                {
                    "op": "if",
                    "condition": selectable,
                    "then": [
                        {"op": "move_to_exile", "card": {"ref": "var", "name": "void_hand_card"}, "silent": True},
                        {"op": "add_var", "name": "void_exiled_hand_count", "value": 1},
                    ],
                },
            ],
        },
        {
            "op": "if",
            "condition": {"op": "compare", "a": _temp("void_exiled_hand_count"), "operator": ">", "b": 0},
            "then": [
                {
                    "op": "status_add_named",
                    "status": "jungle:fragile",
                    "amount": _temp("void_exiled_hand_count"),
                    "target": params.get("target", "target"),
                    "log": params.get("log") or "{target}被放逐{amount}张手牌并获得{amount}层易损",
                },
            ],
        },
    ]


def _void_magic_corruption(params):
    # 使目标装备1张效果已经激活的腐化
    # 旧原子只打印卡数据自带的 log（本卡没有），这里 add_equipment_to_zone 会补一条
    # 默认战报“XX获得装备腐化”，见报告“文案-实现差异”一节。
    return [
        {
            "op": "add_equipment_to_zone",
            "card": "Corruption",
            "target": params.get("target", "target"),
            "effect_target": params.get("target", "target"),
            "log": params.get("log") or False,
        },
        {
            "op": "equipment_prop_set",
            "equipment": {"ref": "card_equipment", "card": {"ref": "last_created_card"}},
            "property": "corruption_active",
            "value": 1,
            "log": False,
        },
    ]


def _void_magic_wing_damage(params):
    # 对目标造成4D；自动额外消耗至多4M，每额外消耗1M，额外造成1次4D
    limit = params.get("extra_limit", 4)
    amount = params.get("amount", params.get("per", params.get("base", 4)))
    return [
        {
            "op": "set_var",
            "name": "void_magic_wing_spent",
            "value": {"op": "min", "values": [limit, _stat("self", "magic")]},
        },
        {
            "op": "spend_resource",
            "resource": "magic",
            "amount": _temp("void_magic_wing_spent"),
            "log": False,
        },
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": amount,
            "hits": {"op": "add", "values": [1, _temp("void_magic_wing_spent")]},
        },
    ]


def _void_puppeteer(params):
    # 目标下回合被傀儡架台控制（引擎按 void_puppeteer_pending_turns 结算）
    return [
        {
            "op": "var_set",
            "target": params.get("target", "target"),
            "name": "void_puppeteer_pending_turns",
            "value": {
                "op": "max",
                "values": [1, _player_var("void_puppeteer_pending_turns", params.get("target", "target"))],
            },
        },
    ]


def _void_satan_swap(params):
    # 摧毁自己与目标之间的 H/E/M 交换（数值按各自上限截断）
    def snap(name, stat, target):
        return {"op": "set_var", "name": name, "value": _stat(target, stat)}

    def restore(target, stat, source_var, limit_target):
        return {
            "op": "player_prop_set",
            "target": target,
            "property": stat,
            "value": {"op": "min", "values": [_temp(source_var), _stat(limit_target, "max_" + stat)]},
            "log": False,
        }

    steps = [
        snap("void_satan_self_h", "health", "self"),
        snap("void_satan_self_e", "elixir", "self"),
        snap("void_satan_self_m", "magic", "self"),
        snap("void_satan_target_h", "health", "target"),
        snap("void_satan_target_e", "elixir", "target"),
        snap("void_satan_target_m", "magic", "target"),
    ]
    swap = [
        restore("self", "health", "void_satan_target_h", "self"),
        restore("self", "elixir", "void_satan_target_e", "self"),
        restore("self", "magic", "void_satan_target_m", "self"),
        restore("target", "health", "void_satan_self_h", "target"),
        restore("target", "elixir", "void_satan_self_e", "target"),
        restore("target", "magic", "void_satan_self_m", "target"),
        {"op": "log", "message": params.get("log") or "{source}与{target}交换了H/E/M"},
    ]
    # 旧原子在选择自己为目标时不结算也不打印战报，这里保持同样的短路。
    steps.append(
        {
            "op": "if",
            "condition": {
                "op": "compare",
                "a": {"op": "target_player"},
                "operator": "!=",
                "b": {"op": "source_player"},
            },
            "then": swap,
        }
    )
    return steps


REWRITES = {
    "void_antimatter_damage": _void_antimatter_damage,
    "void_exile_target_hand": _void_exile_target_hand,
    "void_magic_corruption": _void_magic_corruption,
    "void_magic_wing_damage": _void_magic_wing_damage,
    "void_puppeteer": _void_puppeteer,
    "void_satan_swap": _void_satan_swap,
}
