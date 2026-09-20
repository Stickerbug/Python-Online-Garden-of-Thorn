# -*- coding: utf-8 -*-
"""官方状态内置表（Round 107 / 批次 DE，方案 B）。

17 条官方状态原先由 7 个官方包各自在 ``mod.json`` 的 ``registries.statuses``
里声明（外加 ``locales/*.json`` 的 ``statuses`` 文案）。包声明＝多个来源，
任何一处漏改都会让图鉴 / 提示 / 编辑器下拉对不上；而
``jungle:turn_heal_turns`` / ``jungle:turn_magic_turns`` 的 ``events`` 是**行为**，
删掉声明会直接改玩法。

方案 B：声明收进引擎单表（本文件），包内声明删除。于是

* 文案 / 颜色 / 图标只有一份（中文是权威；客户端同步表是
  ``static/js/game.js`` 的 ``CORE_STATUS_DEFS``，由 ``tools/official_status_table.py``
  对拍，两边不一致就报错）；
* 引擎行为（两条回合回复的 ``events``）不再依赖包，删包声明也不会掉功能；
* 编辑器下拉 / 图鉴 / 战斗内状态提示都从内置表取，官方包只剩卡牌数据。

形式逻辑的 ``formal_logic:substitution`` / ``formal_logic:inference`` 按用户要求
继续留在包内，不进本表。
"""

from __future__ import annotations

import copy
from typing import Dict, Iterable, List, Optional

# 行为字段也属于状态定义的一部分：max_stack / decay / events 等由引擎按同一份
# 声明执行。官方状态先迁移「不依赖数值修改钩子」的那部分（层数上限、自然衰减），
# 标签与改伤害/费用/治疗量的特殊效果仍由后续批次迁移。
_FIELDS = {"id", "alias", "name_i18n", "desc_i18n", "color", "icon",
           "stacking", "visible", "events", "package",
           "max_stack", "decay", "decay_timing", "decay_log",
           "keep_when_zero", "show_stack", "stack_keys", "modifiers"}

OFFICIAL_STATUSES: tuple = (
    {
        "id": "arctic:frost",
        "alias": "frost",
        "package": "Arctic Cards Addition",
        "name_i18n": {"zh": "霜冻", "en": "Frost", "fr": "Gel", "ja": "凍結"},
        "desc_i18n": {
            "zh": "上限为60层；每有10层，卡牌E消耗+1。自己回合结束时层数向下取整减半。",
            "en": "Maximum 60 stacks; every 10 stacks increases a card's E cost by 1. "
                  "At the end of your turn, halve the stacks rounded down.",
            "fr": "Maximum 60 charges ; tous les 10 cumuls, le coût E des cartes augmente de 1. "
                  "À la fin de votre tour, divisez les cumuls par deux en arrondissant à l'inférieur.",
            "ja": "上限60層；10層ごとにカードのEコストが1増える。"
                  "自分のターン終了時、層数を切り捨てで半減する。",
        },
        "color": "#4E9DCC",
        "icon": "frost",
        "stacking": "stack",
        "visible": True,
        "max_stack": 60,
        "stack_keys": ["arctic:frost", "frost", "霜冻"],
        "decay": {"timing": "turn_end", "mode": "half", "log": "zero"},
        # 每 10 层卡牌 E 消耗 +1；旧实现在 ``_get_extra_e_for_card`` 里写死。
        "events": {
            "on_cost": {
                "priority": 10,
                "steps": [
                    {
                        "op": "add_var",
                        "name": "cost_extra",
                        "value": {
                            "op": "div",
                            "values": [{"op": "status_stack", "status": "arctic:frost"}, 10],
                            "round": "floor",
                        },
                    }
                ],
            },
        },
    },
    {
        "id": "bio:debt",
        "alias": "debt",
        "package": "Bio Cards Addition",
        "name_i18n": {"zh": "负债", "en": "Debt", "fr": "Dette", "ja": "負債"},
        "desc_i18n": {
            "zh": "自己回合开始时，在正常回复[[icon:E]]后失去1[[icon:E]]，然后层数-1。",
            "en": "At the start of your turn, lose 1[[icon:E]] after normal [[icon:E]] recovery, "
                  "then remove 1 stack.",
            "fr": "Au début de votre tour, après la récupération normale de [[icon:E]], "
                  "perdez 1[[icon:E]], puis retirez 1 charge.",
            "ja": "自分のターン開始時、通常の[[icon:E]]回復後に1[[icon:E]]を失い、その後1層減少します。",
        },
        "color": "#B36B32",
        "icon": "debt",
        "stacking": "stack",
        "visible": True,
        "stack_keys": ["bio:debt", "debt", "负债"],
        # 「正常回 E 之后失去 1E，再减 1 层」——旧实现是引擎函数
        # ``_bio_apply_debt_after_recovery``，现在由回合阶段事件执行。
        "events": {
            "on_turn_start_after_recovery": [
                {
                    "op": "if_else",
                    "condition": {
                        "op": "compare",
                        "a": {"op": "status_stack", "status": "status_immune"},
                        "operator": "==",
                        "b": 0,
                    },
                    "then": [
                        {
                            "op": "resource_op",
                            "resource": "e",
                            "target": "self",
                            "delta": -1,
                            "log": "{source}的负债使其失去1E",
                            "log_positive_only": True,
                        }
                    ],
                    "else": [],
                },
                {
                    "op": "status_op",
                    "action": "remove",
                    "status": "bio:debt",
                    "amount": 1,
                    "log": False,
                    "bypass_mask": True,
                },
            ],
        },
    },
    {
        "id": "bio:extra_healing",
        "alias": "extra_healing",
        "package": "Bio Cards Addition",
        "name_i18n": {"zh": "额外回复", "en": "Extra Healing",
                      "fr": "Soin supplémentaire", "ja": "追加回復"},
        "desc_i18n": {
            "zh": "每次回复[[icon:H]]后，额外回复等同于层数的[[icon:H]]；不自动减少。",
            "en": "After recovering [[icon:H]], recover additional [[icon:H]] equal to its stacks. "
                  "Does not decay.",
            "fr": "Après avoir récupéré des [[icon:H]], récupérez des [[icon:H]] supplémentaires "
                  "égaux aux charges. Ne diminue pas automatiquement.",
            "ja": "[[icon:H]]を回復した後、層数と同じ値の[[icon:H]]を追加で回復します。自然減少しません。",
        },
        "color": "#D56A9B",
        "icon": "extra_healing",
        "stacking": "stack",
        "visible": True,
        "stack_keys": ["bio:extra_healing", "extra_healing", "额外回复"],
        # 旧实现是治疗回调里的 ``_bio_status_value(player_id, 'extra_healing')``。
        # 现在由 ``on_heal_pre`` 修改本次治疗量；触发点在 heal_block 之后、
        # shield_conversion 之前，与旧顺序逐字一致。
        "events": {
            "on_heal_pre": {
                "priority": 10,
                "steps": [
                    {
                        "op": "add_var",
                        "name": "heal_amount",
                        "value": {"op": "status_stack", "status": "bio:extra_healing"},
                    }
                ],
            },
        },
    },
    {
        "id": "bio:shield_conversion",
        "alias": "shield_conversion",
        "package": "Bio Cards DLC",
        "name_i18n": {"zh": "护盾转化", "en": "Shield Conversion",
                      "fr": "Conversion de bouclier", "ja": "シールド変換"},
        "desc_i18n": {
            "zh": "下次将回复[[icon:H]]时，若原回复量大于0，改为获得(原回复量×护盾转化层数)层护盾，"
                  "然后清空护盾转化。",
            "en": "The next time [[icon:H]] would be restored, if the original amount is greater than 0, "
                  "gain Shield equal to (original amount × Shield Conversion stacks) instead, "
                  "then clear Shield Conversion.",
            "fr": "La prochaine fois que des [[icon:H]] devraient être récupérés, si la quantité initiale "
                  "est supérieure à 0, gagnez à la place un Bouclier égal à (quantité initiale × charges "
                  "de Conversion de bouclier), puis retirez toutes ses charges.",
            "ja": "次に[[icon:H]]を回復する時、元の回復量が0より大きければ、代わりに"
                  "(元の回復量×シールド変換の層数)のシールドを得て、その後シールド変換を全て消去します。",
        },
        "color": "#2E7D7D",
        "icon": "shield_conversion",
        "stacking": "stack",
        "visible": True,
        "stack_keys": ["bio:shield_conversion", "shield_conversion", "护盾转化"],
        # 治疗量修正：先让额外回复（priority 10）加完，再把整段回复转成护盾。
        "events": {
            "on_heal_pre": {
                "priority": 20,
                "steps": [
                    {
                        "op": "set_var",
                        "name": "conversion_stacks",
                        "value": {"op": "status_stack", "status": "bio:shield_conversion"},
                    },
                    {
                        "op": "if_else",
                        "condition": {
                            "op": "compare",
                            "a": {"op": "var", "name": "conversion_stacks"},
                            "operator": ">",
                            "b": 0,
                        },
                        "then": [
                            {
                                "op": "set_var",
                                "name": "converted_heal",
                                "value": {"op": "var", "name": "heal_amount"},
                            },
                            {
                                "op": "set_var",
                                "name": "converted_shield",
                                "value": {
                                    "op": "mul",
                                    "values": [
                                        {"op": "var", "name": "heal_amount"},
                                        {"op": "var", "name": "conversion_stacks"},
                                    ],
                                },
                            },
                            {"op": "set_var", "name": "heal_amount", "value": 0},
                            {
                                "op": "status_op",
                                "action": "add",
                                "status": "jungle:shield",
                                "target": "self",
                                "amount": {"op": "var", "name": "converted_shield"},
                                "log": False,
                                "bypass_mask": True,
                            },
                            {
                                "op": "status_op",
                                "action": "remove",
                                "status": "bio:shield_conversion",
                                "log": False,
                                "bypass_mask": True,
                            },
                            {
                                "op": "log",
                                "message": "{source}的护盾转化将{converted_heal}H转化为{converted_shield}层护盾",
                            },
                        ],
                        "else": [],
                    },
                ],
            },
        },
    },
    {
        "id": "hel:luck",
        "alias": "luck",
        "package": "Hel Cards Addition",
        "name_i18n": {"zh": "幸运", "en": "Luck", "fr": "Chance", "ja": "幸運"},
        "desc_i18n": {
            "zh": "即将造成一段[[icon:D]]时，若幸运层数不少于该段减伤前伤害，则消耗等量幸运，"
                  "使该段伤害暴击。",
            "en": "Before a single hit of [[icon:D]] is dealt, if its stacks are at least that hit's "
                  "pre-mitigation damage, consume that many stacks to make the hit critical.",
            "fr": "Avant qu'un coup de [[icon:D]] ne soit infligé, si ses charges sont au moins égales "
                  "aux dégâts avant réduction de ce coup, consommez autant de charges pour rendre ce "
                  "coup critique.",
            "ja": "[[icon:D]]を1回与える直前に、幸運の層数がその1回の軽減前ダメージ以上なら、"
                  "同じ層数を消費してそのダメージを暴击させます。",
        },
        "color": "#63B85C",
        "icon": "luck",
        "stacking": "stack",
        "visible": True,
        "stack_keys": ["hel:luck", "luck", "幸运"],
        # 暴击判定：减甲之前、闪避预测也跑同一份声明（dry-run）。
        # force_crit / no_luck_crit 来自当前伤害牌的内部标记。
        "events": {
            "on_damage_roll": {
                "priority": 10,
                "steps": [
                    {
                        "op": "set_var",
                        "name": "luck_stacks",
                        "value": {"op": "status_stack", "status": "hel:luck"},
                    },
                    {
                        "op": "if_else",
                        "condition": {
                            "op": "or",
                            "conditions": [
                                {"op": "var", "name": "force_crit"},
                                {
                                    "op": "and",
                                    "conditions": [
                                        {"op": "not", "condition": {"op": "var", "name": "no_luck_crit"}},
                                        {
                                            "op": "compare",
                                            "a": {"op": "var", "name": "luck_stacks"},
                                            "operator": ">=",
                                            "b": {"op": "var", "name": "damage_amount"},
                                        },
                                    ],
                                },
                            ],
                        },
                        "then": [
                            {
                                "op": "if_else",
                                "condition": {"op": "not", "condition": {"op": "var", "name": "force_crit"}},
                                "then": [
                                    {
                                        "op": "status_op",
                                        "action": "remove",
                                        "status": "hel:luck",
                                        "amount": {"op": "var", "name": "damage_amount"},
                                        "log": False,
                                        "bypass_mask": True,
                                    }
                                ],
                                "else": [],
                            },
                            {
                                "op": "set_var",
                                "name": "damage_amount",
                                "value": {
                                    "op": "add",
                                    "values": [
                                        {
                                            "op": "ceil",
                                            "value": {
                                                "op": "mul",
                                                "values": [
                                                    {"op": "var", "name": "damage_amount"},
                                                    {"op": "var", "name": "crit_multiplier"},
                                                ],
                                            },
                                        },
                                        {"op": "var", "name": "crit_bonus_damage"},
                                    ],
                                },
                            },
                            {"op": "set_var", "name": "is_crit", "value": True},
                        ],
                        "else": [],
                    },
                ],
            },
        },
    },
    {
        "id": "hel:blazing_fire",
        "alias": "blazing_fire",
        "package": "Hel Cards Addition",
        "name_i18n": {"zh": "烈火", "en": "Blazing Fire", "fr": "Feu ardent", "ja": "烈火"},
        "desc_i18n": {
            "zh": "自己回合开始时，对自己施加等同于烈火层数的[[icon:F]]；不自动减少。",
            "en": "At the start of your turn, apply [[icon:F]] equal to its stacks to yourself. "
                  "Does not decay.",
            "fr": "Au début de votre tour, appliquez-vous [[icon:F]] égal à ses charges. "
                  "Ne diminue pas automatiquement.",
            "ja": "自分のターン開始時、層数と同じ[[icon:F]]を自分に付与します。自然減少しません。",
        },
        "color": "#FF5D2E",
        "icon": "blazing_fire",
        "stacking": "stack",
        "visible": True,
        "stack_keys": ["hel:blazing_fire", "blazing_fire", "烈火"],
        # 自己回合开始（状态伤害结算前）把层数转成灼烧。旧实现是引擎函数
        # ``_hel_apply_blazing_fire_turn_start``。
        "events": {
            "on_turn_start_before_status_damage": [
                {
                    "op": "set_var",
                    "name": "blazing_fire_stacks",
                    "value": {"op": "status_stack", "status": "hel:blazing_fire"},
                },
                {
                    "op": "if_else",
                    "condition": {
                        "op": "compare",
                        "a": {"op": "var", "name": "blazing_fire_stacks"},
                        "operator": ">",
                        "b": 0,
                    },
                    "then": [
                        {
                            "op": "status_op",
                            "action": "add",
                            "status": "fire",
                            "target": "self",
                            "amount": {"op": "var", "name": "blazing_fire_stacks"},
                            "log": False,
                            "bypass_mask": True,
                        },
                        {"op": "log", "message": "{source}的烈火施加{blazing_fire_stacks}层灼烧"},
                    ],
                    "else": [],
                },
            ],
        },
    },
    {
        "id": "jungle:fragile",
        "alias": "fragile",
        "package": "Jungle Cards Addition",
        "name_i18n": {"zh": "易损", "en": "Fragile", "fr": "Fragile", "ja": "脆弱"},
        "desc_i18n": {
            "zh": "护甲降低对应层数；若护甲被降到负数，会让受到的物理伤害增加。自己回合开始时清除。",
            "en": "Reduces armor by its stacks. Negative armor increases physical damage taken. "
                  "Clears at your turn start.",
            "fr": "Réduit l'armure de ses charges. Une armure négative augmente les dégâts physiques "
                  "reçus. Disparaît au début de votre tour.",
            "ja": "護甲を層数分減らします。護甲が負なら受ける物理ダメージが増えます。"
                  "自分ターン開始時に消えます。",
        },
        "color": "#8E5A2A",
        "icon": "fragile",
        "stacking": "stack",
        "visible": True,
        "stack_keys": ["jungle:fragile", "fragile"],
        "decay": {"timing": "turn_start", "mode": "clear"},
        # 护甲按层数扣减；旧实现在伤害管线里写 ``root_armor - fragile``。
        "modifiers": {"armor": {"op": "sub", "value": {"op": "stack"}}},
    },
    {
        "id": "jungle:shield",
        "alias": "shield",
        "package": "Jungle Cards Addition",
        "name_i18n": {"zh": "护盾", "en": "Shield", "fr": "Bouclier", "ja": "シールド"},
        "desc_i18n": {
            "zh": "受到伤害时先消耗护盾层数抵扣等量伤害，包括魔法伤害。自己回合开始时层数减半。",
            "en": "When damage would be taken, consume stacks to block that much damage first, "
                  "including magic damage. Halves at your turn start.",
            "fr": "Quand des dégâts devraient être subis, consomme ses charges pour en bloquer autant, "
                  "y compris les dégâts magiques. Est divisé par deux au début de votre tour.",
            "ja": "ダメージを受ける時、まず層数を消費して同量のダメージを防ぎます（魔法ダメージも含む）。"
                  "自分ターン開始時に半減します。",
        },
        "color": "#66A6A6",
        "icon": "shield",
        "stacking": "stack",
        "visible": True,
        "stack_keys": ["jungle:shield", "shield"],
        # 减甲/拿扎尔之后的伤害在此被护盾抵扣；旧实现在
        # ``_apply_universal_damage_shields`` 里写死。
        "events": {
            "on_damage_pre": {
                "priority": 10,
                "steps": [
                    {
                        "op": "set_var",
                        "name": "shield_absorb",
                        "value": {
                            "op": "min",
                            "values": [
                                {"op": "status_stack", "status": "jungle:shield"},
                                {"op": "var", "name": "damage_amount"},
                            ],
                        },
                    },
                    {
                        "op": "if_else",
                        "condition": {
                            "op": "compare",
                            "a": {"op": "var", "name": "shield_absorb"},
                            "operator": ">",
                            "b": 0,
                        },
                        "then": [
                            {
                                "op": "set_var",
                                "name": "damage_amount",
                                "value": {
                                    "op": "max",
                                    "values": [
                                        0,
                                        {
                                            "op": "sub",
                                            "values": [
                                                {"op": "var", "name": "damage_amount"},
                                                {"op": "var", "name": "shield_absorb"},
                                            ],
                                        },
                                    ],
                                },
                            },
                            {
                                "op": "status_op",
                                "action": "remove",
                                "status": "jungle:shield",
                                "amount": {"op": "var", "name": "shield_absorb"},
                                "log": False,
                                "bypass_mask": True,
                            },
                            {"op": "log", "message": "{source}的护盾抵扣{shield_absorb}点伤害"},
                        ],
                        "else": [],
                    },
                ],
            },
        },
    },
    {
        "id": "jungle:turn_heal_turns",
        "alias": "turn_heal_turns",
        "package": "Jungle Cards Addition",
        "name_i18n": {"zh": "回合回复", "en": "Turn Heal", "fr": "Soin de tour", "ja": "ターン回復"},
        "desc_i18n": {
            "zh": "回合回复:X;Y：出现时及自己回合开始时回复Y[[icon:H]]，然后X-1；X为0时移除。",
            "en": "Shown as Turn Heal:X;Y. When applied and at your turn start, heal Y H, "
                  "then X decreases by 1. Removed at X=0.",
            "fr": "Affiché Soin de tour:X;Y. À l'application et au début de votre tour, soigne Y H, "
                  "puis X diminue de 1. Retiré à X=0.",
            "ja": "回合回复:X;Y と表示。付与時とターン開始時にY H回復し、Xが1減ります。X=0で消えます。",
        },
        "color": "#F48FB1",
        "icon": "turn_heal",
        "stacking": "stack",
        "visible": True,
        "events": {
            "on_turn_start": [
                {"op": "set_var", "name": "regen_power",
                 "value": {"op": "status_stack", "status": "jungle:turn_heal_power"}},
                {"op": "if_else",
                 "condition": {"op": "compare",
                               "a": {"op": "status_stack", "status": "jungle:turn_heal_power",
                                     "ignore_immunity": True},
                               "operator": ">", "b": 0},
                 "then": [
                     {"op": "if_else",
                      "condition": {"op": "compare",
                                    "a": {"op": "status_stack", "status": "status_immune"},
                                    "operator": "==", "b": 0},
                      "then": [
                          {"op": "health_op", "mode": "heal", "target": "self",
                           "amount": {"op": "var", "name": "regen_power"}, "log": False},
                          {"op": "log", "message": "{source}的回合回复：+{regen_power}H"},
                      ],
                      "else": []},
                     {"op": "status_op", "action": "remove", "status": "jungle:turn_heal_turns",
                      "amount": 1, "log": False},
                     {"op": "if_else",
                      "condition": {"op": "compare",
                                    "a": {"op": "status_stack", "status": "jungle:turn_heal_turns",
                                          "ignore_immunity": True},
                                    "operator": "<=", "b": 0},
                      "then": [{"op": "status_op", "action": "clear",
                                "status": "jungle:turn_heal_power", "log": False}],
                      "else": []},
                 ],
                 "else": []},
            ],
            "on_apply": [
                {"op": "if_else",
                 "condition": {"op": "compare",
                               "a": {"op": "status_stack", "status": "jungle:turn_heal_power",
                                     "ignore_immunity": True},
                               "operator": ">", "b": 0},
                 "then": [
                     {"op": "set_var", "name": "regen_power",
                      "value": {"op": "status_stack", "status": "jungle:turn_heal_power",
                                "ignore_immunity": True}},
                     {"op": "set_var", "name": "regen_turns",
                      "value": {"op": "status_stack", "status": "jungle:turn_heal_turns",
                                "ignore_immunity": True}},
                     {"op": "set_var", "name": "regen_remaining",
                      "value": {"op": "floor",
                                "value": {"op": "sub",
                                          "values": [{"op": "var", "name": "regen_turns"}, 0]}}},
                     {"op": "if_else",
                      "condition": {"op": "compare",
                                    "a": {"op": "status_stack", "status": "status_immune"},
                                    "operator": "==", "b": 0},
                      "then": [
                          {"op": "health_op", "mode": "heal", "target": "self",
                           "amount": {"op": "var", "name": "regen_power"}, "log": False},
                          {"op": "log",
                           "message": "{source}获得回合回复：{regen_remaining};{regen_power}，+{regen_power}H"},
                      ],
                      "else": [
                          {"op": "log",
                           "message": "{source}获得回合回复：{regen_remaining};{regen_power}"},
                      ]},
                 ],
                 "else": []},
            ],
        },
    },
    {
        "id": "jungle:turn_magic_turns",
        "alias": "turn_magic_turns",
        "package": "Jungle Cards Addition",
        "name_i18n": {"zh": "魔力回合回复", "en": "Turn Magic Regen",
                      "fr": "Régénération magique", "ja": "魔力ターン回復"},
        "desc_i18n": {
            "zh": "魔力回合回复:X;Y：出现时及自己回合开始时回复Y[[icon:M]]，然后X-1；X为0时移除。",
            "en": "Shown as Turn Magic Regen:X;Y. When applied and at turn start, recover Y M, "
                  "then X decreases by 1. Removed at X=0.",
            "fr": "Affiché Régénération magique:X;Y. À l'application et au début du tour, récupère Y M, "
                  "puis X diminue de 1. Retiré à X=0.",
            "ja": "魔力回合回复:X;Y と表示。付与時とターン開始時にY M回復し、Xが1減ります。X=0で消えます。",
        },
        "color": "#6C5CE7",
        "icon": "turn_magic",
        "stacking": "stack",
        "visible": True,
        "events": {
            "on_turn_start": [
                {"op": "set_var", "name": "regen_power",
                 "value": {"op": "status_stack", "status": "jungle:turn_magic_power"}},
                {"op": "if_else",
                 "condition": {"op": "compare",
                               "a": {"op": "status_stack", "status": "jungle:turn_magic_power",
                                     "ignore_immunity": True},
                               "operator": ">", "b": 0},
                 "then": [
                     {"op": "if_else",
                      "condition": {"op": "compare",
                                    "a": {"op": "status_stack", "status": "status_immune"},
                                    "operator": "==", "b": 0},
                      "then": [
                          {"op": "resource_op", "resource": "m", "target": "self",
                           "delta": {"op": "var", "name": "regen_power"}, "log": False},
                          {"op": "log", "message": "{source}的魔力回合回复：+{regen_power}M"},
                      ],
                      "else": []},
                     {"op": "status_op", "action": "remove", "status": "jungle:turn_magic_turns",
                      "amount": 1, "log": False},
                     {"op": "if_else",
                      "condition": {"op": "compare",
                                    "a": {"op": "status_stack", "status": "jungle:turn_magic_turns",
                                          "ignore_immunity": True},
                                    "operator": "<=", "b": 0},
                      "then": [{"op": "status_op", "action": "clear",
                                "status": "jungle:turn_magic_power", "log": False}],
                      "else": []},
                 ],
                 "else": []},
            ],
            "on_apply": [
                {"op": "if_else",
                 "condition": {"op": "compare",
                               "a": {"op": "status_stack", "status": "jungle:turn_magic_power",
                                     "ignore_immunity": True},
                               "operator": ">", "b": 0},
                 "then": [
                     {"op": "set_var", "name": "regen_power",
                      "value": {"op": "status_stack", "status": "jungle:turn_magic_power",
                                "ignore_immunity": True}},
                     {"op": "set_var", "name": "regen_turns",
                      "value": {"op": "status_stack", "status": "jungle:turn_magic_turns",
                                "ignore_immunity": True}},
                     {"op": "set_var", "name": "regen_remaining",
                      "value": {"op": "floor",
                                "value": {"op": "sub",
                                          "values": [{"op": "var", "name": "regen_turns"}, 0]}}},
                     {"op": "if_else",
                      "condition": {"op": "compare",
                                    "a": {"op": "status_stack", "status": "status_immune"},
                                    "operator": "==", "b": 0},
                      "then": [
                          {"op": "resource_op", "resource": "m", "target": "self",
                           "delta": {"op": "var", "name": "regen_power"}, "log": False},
                          {"op": "log",
                           "message": "{source}获得魔力回合回复：{regen_remaining};{regen_power}，+{regen_power}M"},
                      ],
                      "else": [
                          {"op": "log",
                           "message": "{source}获得魔力回合回复：{regen_remaining};{regen_power}"},
                      ]},
                 ],
                 "else": []},
            ],
        },
    },
    {
        "id": "jungle:root_status",
        "alias": "root_status",
        "package": "Jungle Cards Addition",
        "name_i18n": {"zh": "树根", "en": "Root", "fr": "Racine", "ja": "根"},
        "desc_i18n": {
            "zh": "树根层数显示在对应装备上，并计入目标护甲；目标受到[[icon:D]]时，对应装备减少1层树根。",
            "en": "Increases armor. Loses 1 stack when physical damage is taken. The Root equipment that "
                  "created it clears its own stacks when leaving play.",
            "fr": "Augmente l'armure. Perd 1 charge quand des dégâts physiques sont subis. "
                  "L'équipement Racine qui l'a créé retire ses propres charges en quittant le jeu.",
            "ja": "護甲を増やします。物理ダメージを受けると1層減ります。"
                  "生成元のRoot装備が離場すると対応分を消します。",
        },
        "color": "#6E8B3D",
        "icon": "root_status",
        "stacking": "stack",
        "visible": True,
        "stack_keys": ["jungle:root_status", "jungle:root", "root_status"],
        # 护甲按层数增加；受击时扣装备层数的部分仍留在引擎里（要找到对应装备）。
        "modifiers": {"armor": {"op": "add", "value": {"op": "stack"}}},
    },
    {
        "id": "jungle:toxic_poison",
        "alias": "toxic_poison",
        "package": "Jungle Cards Addition",
        "name_i18n": {"zh": "剧毒", "en": "Toxic Poison", "fr": "Poison virulent", "ja": "劇毒"},
        "desc_i18n": {
            "zh": "中毒结算后，对自己施加等同于剧毒层数的[[icon:P]]；不自动减少。",
            "en": "After Poison resolves, applies that many additional P.",
            "fr": "Après la résolution du Poison, applique autant de P supplémentaires.",
            "ja": "毒の解決後、同じ層数のPを追加付与します。",
        },
        "color": "#5E8C31",
        "icon": "toxic_poison",
        "stacking": "stack",
        "visible": True,
        # 卡数据历史上两种写法都用过（``jungle:toxic_poison`` / ``toxic_poison``），
        # 声明层数键后，读取与增删都会归并到第一个键。
        "stack_keys": ["jungle:toxic_poison", "toxic_poison", "剧毒"],
        "events": {
            "on_poison_resolved": [
                {
                    "op": "set_var",
                    "name": "toxic_poison_stacks",
                    "value": {"op": "status_stack", "status": "jungle:toxic_poison"},
                },
                {
                    "op": "if_else",
                    "condition": {
                        "op": "compare",
                        "a": {"op": "var", "name": "toxic_poison_stacks"},
                        "operator": ">",
                        "b": 0,
                    },
                    "then": [
                        {
                            "op": "status_op",
                            "action": "add",
                            "status": "poison",
                            "target": "self",
                            "amount": {"op": "var", "name": "toxic_poison_stacks"},
                            "log": False,
                            "bypass_mask": True,
                        },
                        {"op": "log", "message": "{source}的剧毒施加{toxic_poison_stacks}层中毒"},
                    ],
                    "else": [],
                },
            ],
        },
    },
    {
        "id": "jungle:turn_heal_power",
        "alias": "turn_heal_power",
        "package": "Jungle Cards Addition",
        "name_i18n": {"zh": "回合回复量", "en": "Turn Heal Power",
                      "fr": "Puissance de soin de tour", "ja": "ターン回復量"},
        "desc_i18n": {
            "zh": "由「回合回复 / 魔力回合回复」携带的每次回复量（内部使用）。",
            "en": "Internal stack carried by Turn Heal / Turn Magic Regen (the per-turn amount).",
            "fr": "Charge interne portée par Soin de tour / Régénération magique "
                  "(la quantité par tour).",
            "ja": "「ターン回復 / 魔力ターン回復」が持つ内部層数（1回あたりの回復量）。",
        },
        "color": "",
        "icon": "turn_heal",
        "stacking": "stack",
        "visible": False,
    },
    {
        "id": "jungle:turn_magic_power",
        "alias": "turn_magic_power",
        "package": "Jungle Cards Addition",
        "name_i18n": {"zh": "魔力回合回复量", "en": "Turn Magic Power",
                      "fr": "Puissance de régénération magique", "ja": "魔力ターン回復量"},
        "desc_i18n": {
            "zh": "由「回合回复 / 魔力回合回复」携带的每次回复量（内部使用）。",
            "en": "Internal stack carried by Turn Heal / Turn Magic Regen (the per-turn amount).",
            "fr": "Charge interne portée par Soin de tour / Régénération magique "
                  "(la quantité par tour).",
            "ja": "「ターン回復 / 魔力ターン回復」が持つ内部層数（1回あたりの回復量）。",
        },
        "color": "",
        "icon": "turn_magic",
        "stacking": "stack",
        "visible": False,
    },
    {
        "id": "ocean:blood_debt",
        "alias": "blood_debt",
        "package": "Ocean Cards Addition",
        "name_i18n": {"zh": "血债", "en": "Blood Debt", "fr": "Dette de sang", "ja": "血債"},
        "desc_i18n": {
            "zh": "受到[[icon:D]]时清除；攻击者获得等同于血债层数的[[icon:E]]。",
            "en": "When physical damage is taken, this effect clears and the attacker gains E equal "
                  "to its stacks.",
            "fr": "Quand des dégâts physiques sont subis, cet effet disparaît et l'attaquant gagne E "
                  "égal aux charges.",
            "ja": "物理ダメージを受けるとこの効果は消え、攻撃者は層数分のEを得ます。",
        },
        "color": "#8E1B2A",
        "icon": "blood_debt",
        "stacking": "stack",
        "visible": True,
        "stack_keys": ["ocean:blood_debt", "blood_debt", "血债"],
        # 受到物理伤害时清除，攻击者按层数获得 E；事件在受击者身上跑，
        # 「攻击者」用 ``event_source`` 选择器取。
        "events": {
            "on_damage_taken": {
                "priority": 10,
                "steps": [
                    {
                        "op": "set_var",
                        "name": "blood_debt_stacks",
                        "value": {"op": "status_stack", "status": "ocean:blood_debt"},
                    },
                    {
                        "op": "if_else",
                        "condition": {
                            "op": "and",
                            "conditions": [
                                {"op": "damage_type", "type_name": "physical"},
                                {
                                    "op": "compare",
                                    "a": {"op": "var", "name": "blood_debt_stacks"},
                                    "operator": ">",
                                    "b": 0,
                                },
                            ],
                        },
                        "then": [
                            {
                                "op": "status_op",
                                "action": "remove",
                                "status": "ocean:blood_debt",
                                "log": False,
                                "bypass_mask": True,
                            },
                            {
                                "op": "resource_op",
                                "resource": "e",
                                "target": "event_source",
                                "delta": {"op": "var", "name": "blood_debt_stacks"},
                                "log": False,
                            },
                            {
                                "op": "log",
                                "message": "{source}的血债解除，{event_source_name}获得{blood_debt_stacks}E",
                            },
                        ],
                        "else": [],
                    },
                ],
            },
        },
    },
    {
        "id": "ocean:unable_counter",
        "alias": "unable_counter",
        "package": "Ocean Cards Addition",
        "name_i18n": {"zh": "无法反制", "en": "Unable to Counter",
                      "fr": "Contre impossible", "ja": "反制不能"},
        "desc_i18n": {
            "zh": "从左到右将层数张反制牌置入弃牌堆，然后减少对应层数。若层数不为0，"
                  "抽到反制牌时自动将其置入弃牌堆并降低层数。",
            "en": "Discards counter cards from left to right equal to its stacks, then reduces those "
                  "stacks. If stacks remain, drawn counter cards are discarded and reduce stacks.",
            "fr": "Défausse de gauche à droite autant de contres que de charges, puis réduit ces charges. "
                  "S'il en reste, les contres piochés sont défaussés et réduisent les charges.",
            "ja": "層数分だけ左から反制牌を弃牌に置き、その分層数を減らします。"
                  "層数が残る間、引いた反制牌も弃牌に置かれ層数が減ります。",
        },
        "color": "#536878",
        "icon": "",
        "stacking": "stack",
        "visible": True,
        "stack_keys": ["ocean:unable_counter", "unable_counter", "无法反制"],
        # 抽到/入手反制牌时自动弃掉并 -1 层；旧实现在
        # ``_apply_unable_counter_to_entering_card`` 里写死。
        "events": {
            "on_card_added_to_hand": {
                "priority": 10,
                "steps": [
                    {
                        "op": "set_var",
                        "name": "unable_counter_block",
                        "value": {
                            "op": "min",
                            "values": [
                                {"op": "status_stack", "status": "ocean:unable_counter"},
                                1,
                            ],
                        },
                    },
                    {
                        "op": "if_else",
                        "condition": {
                            "op": "and",
                            "conditions": [
                                {"op": "var", "name": "is_counter_card"},
                                {
                                    "op": "compare",
                                    "a": {"op": "var", "name": "unable_counter_block"},
                                    "operator": ">",
                                    "b": 0,
                                },
                            ],
                        },
                        "then": [
                            {
                                "op": "move_card",
                                "card": {"ref": "current_card"},
                                "zone": "discard",
                                "count_as_active_discard": False,
                                "silent": True,
                            },
                            {
                                "op": "status_op",
                                "action": "remove",
                                "status": "ocean:unable_counter",
                                "amount": {"op": "var", "name": "unable_counter_block"},
                                "log": False,
                                "bypass_mask": True,
                            },
                            {
                                "op": "log",
                                "message": "{source}因无法反制将{card_name}置入弃牌堆",
                            },
                        ],
                        "else": [],
                    },
                ],
            },
        },
    },
    {
        "id": "sewers:sealed",
        "alias": "sealed",
        "package": "Sewers Cards DLC",
        "name_i18n": {"zh": "尘封", "en": "Sealed", "fr": "Scellé", "ja": "封印"},
        "desc_i18n": {
            "zh": "存在时，此装备的效果不生效、不能触发，且已装备回合数不增加；装备护甲仍然生效。"
                  "装备拥有者回合开始时，先跳过本次应执行的效果，再减少1层。",
            "en": "While present, this equipment's effects are inactive, it cannot be triggered, and its "
                  "equipped-turn count does not increase; Equipment Armor remains active. At the start of "
                  "its owner's turn, skip its effects for that start, then remove 1 stack.",
            "fr": "Tant que cet effet est présent, les effets de cet équipement sont inactifs, il ne peut "
                  "pas être déclenché et son nombre de tours équipés n'augmente pas ; l'Armure "
                  "d'équipement reste active. Au début du tour de son propriétaire, ignorez ses effets de "
                  "ce début de tour, puis retirez 1 cumul.",
            "ja": "存在する間、この装備の効果は発動せず、手動発動もできず、装備ターン数も増えない。"
                  "装備アーマーは有効。装備者のターン開始時、その開始時効果を無効にした後、1層減少する。",
        },
        "color": "#8C6B43",
        "icon": "",
        "stacking": "stack",
        "visible": True,
    },
)


def _validate() -> None:
    seen = set()
    for entry in OFFICIAL_STATUSES:
        extra = set(entry) - _FIELDS
        if extra:
            raise AssertionError(f"{entry.get('id')}: 未登记的字段 {sorted(extra)}")
        missing = {"id", "alias", "name_i18n", "desc_i18n", "color", "icon",
                   "stacking", "visible", "package"} - set(entry)
        if missing:
            raise AssertionError(f"{entry.get('id')}: 缺字段 {sorted(missing)}")
        if entry["id"] in seen:
            raise AssertionError(f"重复状态 id：{entry['id']}")
        seen.add(entry["id"])
        for field in ("name_i18n", "desc_i18n"):
            langs = set(entry[field])
            if not {"zh", "en"} <= langs:
                raise AssertionError(f"{entry['id']}.{field} 缺 zh/en：{sorted(langs)}")


_validate()

_BY_ID: Dict[str, dict] = {str(item["id"]): item for item in OFFICIAL_STATUSES}
_BY_ALIAS: Dict[str, dict] = {str(item["alias"]).lower(): item for item in OFFICIAL_STATUSES}


def status_ids(include_internal: bool = True) -> List[str]:
    """内置状态 id（``include_internal=False`` 时跳过 ``visible:false`` 的内部层）。"""

    return [
        str(item["id"]) for item in OFFICIAL_STATUSES
        if include_internal or item.get("visible", True)
    ]


def get_status(status_id: str) -> Optional[dict]:
    """按 id 或短别名取一条内置状态。"""

    text = str(status_id or "").strip()
    if not text:
        return None
    return _BY_ID.get(text) or _BY_ALIAS.get(text.lower())


def status_words() -> set:
    """词表：id + 短别名 + 四语言名字（小写），供"状态 id 必须认得"的对拍用。"""

    words = set()
    for item in OFFICIAL_STATUSES:
        words.add(str(item["id"]).strip().lower())
        words.add(str(item["alias"]).strip().lower())
        for value in (item.get("name_i18n") or {}).values():
            if value:
                words.add(str(value).strip().lower())
    return words


_ENGINE_DEFS: Optional[Dict[str, dict]] = None


def engine_status_def(status_id: str) -> Optional[dict]:
    """引擎内部取内置状态定义（缓存；调用方只读，不要改返回值）。"""

    global _ENGINE_DEFS
    if _ENGINE_DEFS is None:
        _ENGINE_DEFS = engine_status_defs()
    entry = get_status(status_id)
    if entry is None:
        return None
    return _ENGINE_DEFS.get(str(entry["id"]))


def engine_status_defs() -> Dict[str, dict]:
    """引擎 ``v2_status_defs`` 形状：``{id: {...含 events...}}``（深拷贝）。"""

    out: Dict[str, dict] = {}
    for item in OFFICIAL_STATUSES:
        payload = {
            "id": item["id"],
            "name_cn": item["name_i18n"]["zh"],
            "name_en": item["name_i18n"]["en"],
            "name_i18n": dict(item["name_i18n"]),
            "description": item["desc_i18n"]["zh"],
            "description_i18n": dict(item["desc_i18n"]),
            "color": item["color"],
            "icon": item["icon"],
            "stacking": item["stacking"],
            "visible": item["visible"],
            "source": "builtin",
        }
        for key in ("max_stack", "decay", "decay_timing", "decay_log",
                    "keep_when_zero", "show_stack", "stack_keys", "modifiers"):
            if item.get(key) not in (None, ""):
                payload[key] = copy.deepcopy(item[key])
        if item.get("events"):
            payload["events"] = copy.deepcopy(item["events"])
        out[str(item["id"])] = payload
    return out


def client_defs() -> List[dict]:
    """客户端 ``CORE_STATUS_DEFS`` 的形状（id / i18n / 颜色 / 图标 / 可见性）。"""

    return [
        {
            "id": item["id"],
            "alias": item["alias"],
            "name_i18n": dict(item["name_i18n"]),
            "description_i18n": dict(item["desc_i18n"]),
            "color": item["color"],
            "icon": item["icon"],
            "stacking": item["stacking"],
            "visible": item["visible"],
        }
        for item in OFFICIAL_STATUSES
    ]


def declaring_packages() -> Iterable[str]:
    """曾经声明过这些状态的官方包名（迁移工具与报告用）。"""

    return sorted({str(item["package"]) for item in OFFICIAL_STATUSES})
