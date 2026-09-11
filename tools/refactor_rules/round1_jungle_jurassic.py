# -*- coding: utf-8 -*-
"""Round 1 规则：丛林 DLC + 侏罗包（子代理 rd1_jungle_jurassic）。

只写"现有通用能力表达得了"的原子；表达不了的留缺口，见
`.codex-tmp/round1/rd1_jungle_jurassic.md`。

已转换：
- jurassic_acid                  丢弃所选 2 张并抽 2 张；目标随机丢弃至多 2 张
- jurassic_magic_fang            7D，每 3 点实际伤害吸取 1M
- jurassic_magic_soil_on_equip   使用魔法土时回复目标 40H（上限加成由装备本身派生）
- jurassic_torch                 9D，可丢弃至多 1 张手牌并抽对应张牌
- jurassic_magic_torch           14D，丢弃全部其他手牌，每张造成 3 电伤并回 1M

缺口（未写规则）：jungle_monstera_heal_team、jungle_dianthus_record_use、
jungle_dianthus_restore_power、jurassic_random_deck_to_hand。
"""

def _magic_fang(params):
    """7D；每造成 3 点实际伤害，回复自己 1M 并使目标失去 1M。"""
    transfer = {
        "op": "floor",
        "value": {"op": "div", "values": [{"op": "last_damage"}, 3]},
    }
    return [
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": params.get("amount", 7),
            "hits": params.get("hits", 1),
            # 原原子在命中后一次性结算：transfer = dealt // 3。
            "on_hit_once": [
                {"op": "gain_m", "target": "self", "amount": transfer},
                {
                    "op": "gain_m",
                    "target": params.get("target", "target"),
                    # 负数即"失去"：通用 gain_m 会做 max(0, magic + amount)。
                    "amount": {"op": "mul", "values": [-1, transfer]},
                },
            ],
        },
    ]


def _acid(params):
    """丢弃自己 2 张其他手牌并抽 2 张牌；使目标随机丢弃至多 2 张手牌。"""
    return [
        {
            # 原原子在"选不到正好 2 张"时整体不结算（连目标随机丢弃也不发生）。
            "op": "if",
            "condition": {
                "op": "compare",
                "a": {"op": "selected_cards_count"},
                "operator": "==",
                "b": 2,
            },
            "then": [
                {
                    "op": "for_each_selected_card",
                    "body": [
                        {
                            "op": "move_to_discard",
                            "card": {"ref": "chosen_card"},
                            "silent": True,
                        },
                    ],
                },
                {
                    "op": "draw_cards",
                    "target": "self",
                    "amount": {"op": "selected_cards_count"},
                },
                {
                    # Round 27：``random_discard_from_hand`` 原子已拆成
                    # "取值表达式 + 通用步骤"（§25），规则同步成新写法。
                    "op": "set_var",
                    "name": "count",
                    "value": 0,
                },
                {
                    "op": "for_each",
                    "items": {
                        "op": "zone_random_ids",
                        "target": params.get("target", "target"),
                        "zone": "hand",
                        "count": 2,
                    },
                    "as": "acid_discard_iid",
                    "steps": [
                        {
                            "op": "move_to_discard",
                            "card": {
                                "ref": "card_instance",
                                "instance_id": {"op": "var", "name": "acid_discard_iid"},
                            },
                            "count_as_active_discard": True,
                            "silent": True,
                        },
                        {"op": "add_var", "name": "count", "value": 1},
                    ],
                },
                {
                    "op": "log",
                    "target": params.get("target", "target"),
                    "message": "{source}丢弃{amount}张并抽{amount}张牌；{target}随机丢弃{count}张牌",
                    "amount": 2,
                },
            ],
        },
    ]


def _magic_soil_on_equip(params):
    """使用时回复目标 40H（H/M 上限加成由装备派生，place_as_equip 已刷新）。"""
    return [
        {
            "op": "heal",
            "target": params.get("target", "target"),
            "amount": 40,
        },
    ]


def _torch(params):
    """9D；可以丢弃自己至多 1 张其他手牌，并抽对应张牌。"""
    return [
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": params.get("amount", 9),
            "hits": params.get("hits", 1),
        },
        {
            "op": "if",
            "condition": {
                "op": "compare",
                "a": {"op": "selected_cards_count"},
                "operator": ">",
                "b": 0,
            },
            "then": [
                {
                    "op": "for_each_selected_card",
                    "body": [
                        {
                            "op": "move_to_discard",
                            "card": {"ref": "chosen_card"},
                            "silent": True,
                        },
                    ],
                },
                {
                    "op": "draw_cards",
                    "target": "self",
                    "amount": {"op": "selected_cards_count"},
                },
            ],
        },
    ]


def _magic_torch(params):
    """14D；丢弃自己所有其他手牌；每丢弃 1 张，造成 3 电伤并回复自己 1M。"""
    return [
        {
            "op": "deal_damage",
            "target": params.get("target", "target"),
            "amount": params.get("amount", 14),
            "hits": params.get("hits", 1),
        },
        {
            "op": "for_each_list",
            "list": {"ref": "zone_list", "target": "self", "zone": "hand"},
            "body": [
                {
                    "op": "move_to_discard",
                    "card": {"ref": "var", "name": "item"},
                    "silent": True,
                },
                {"op": "gain_m", "target": "self", "amount": 1},
                {
                    "op": "direct_damage",
                    "target": params.get("target", "target"),
                    "amount": 3,
                    "source": "魔法火把电伤",
                    "damage_type": "magic",
                    "damage_tag": "battery",
                },
            ],
        },
    ]


REWRITES = {
    "jurassic_magic_fang": _magic_fang,
    "jurassic_acid": _acid,
    "jurassic_magic_soil_on_equip": _magic_soil_on_equip,
    "jurassic_torch": _torch,
    "jurassic_magic_torch": _magic_torch,
}
