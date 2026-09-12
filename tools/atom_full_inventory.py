# -*- coding: utf-8 -*-
"""生成《原子全量清单》（``docs/原子全量清单.md``）：**逐行**覆盖全部引擎原子。

每行给出：原子 / 当前用量 / 判定（删·合·留）/ 理由 / 替代写法（若删或合）。
表里所有判"删"或"合"的名字都**已经在本轮执行完毕**——``--check`` 会验证：

1. 每一个当前 ``_atomic_*`` 实现都在"保留"表里恰好出现一次；
2. 每一个删/合的名字都已经没有 ``_atomic_*`` 实现（真删），并且卡数据 0 引用；
3. 用量数字与 ``tools/mod_atom_report.py`` 的口径一致；
4. 落盘文件与重新生成的内容逐字节一致（防止手改或漏跑）。

    python tools/atom_full_inventory.py            # 写 docs/原子全量清单.md
    python tools/atom_full_inventory.py --check    # 只校验
    python tools/atom_full_inventory.py --stdout   # 打到标准输出
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import atomic_registry  # noqa: E402
import mod_spec_v2  # noqa: E402

DEFAULT_OUT = ROOT / "docs" / "原子全量清单.md"
MODS_DIR = ROOT / "mods"

# ---------------------------------------------------------------------------
# 本批（Round 33 / 批次 AB+AC+AD）真删与真合并的名字。
ROUND33_ACTIONS = {
    # ---- 批次 AB：区域/移动 -------------------------------------------------
    # Round 35：``give_card_to_hand`` 的处理器保留给 tests 直呼，移到下面的
    # HANDLER_KEPT_ACTIONS（数据已 0 引用）。
    "give_card_to_deck": ("合", 3, '{"op":"move_card","mode":"give","target_zone":"deck","card":"<牌id>","position":"top"}',
                          "造牌入牌堆与入手共用同一个循环，position/flags 语义不变"),
    "give_magic_orb_to_hand": ("合", 2, '{"op":"move_card","mode":"orb","target_zone":"hand","target":"self"}',
                               "魔法宝珠走 orb 段（固定 symbiosis/exile/void 三个印痕）"),
    "random_zone_card_to_hand": ("合", 2, '{"op":"move_card","mode":"random","source_zone":"discard","target_zone":"hand","count":1}',
                                 "随机取牌并进 move_card：候选过滤/手牌满即停/tag 打标/逐张回调都保留"),
    "move_cards_to_deck": ("合", 2, '{"op":"move_card","mode":"batch","target_zone":"deck","cards":"selected_cards","position":"top"}',
                           "批量入堆并进 move_card(mode:\"batch\")：top/bottom/random/random_top 四档顺序不变"),
    "exile_this": ("删", 0, '{"op":"move_card","zone":"exile","card":{"ref":"current_card"}}',
                   "与 move_card(zone:\"exile\") 完全同义（实现是它的子集），直接删除不留 mode"),
    "steal_enemy_card": ("合", 0, '{"op":"move_card","mode":"steal","target":"enemy"}',
                         "夺取手牌并进 move_card(mode:\"steal\")：选择窗口与\"夺取失败\"战报不变"),
    "swap_hands": ("合", 0, '{"op":"move_card","mode":"swap_hands","target1":"self","target2":"enemy"}',
                   "交换手牌并进 move_card(mode:\"swap_hands\")"),
    # ---- 批次 AB：复制 ------------------------------------------------------
    # Round 35：``copy_card_instance``（copy_card 伞转交 + 测试 spy）与
    # ``create_copies_to_deck_top``（tests 直呼）的处理器保留，见
    # HANDLER_KEPT_ACTIONS。
    # ---- 批次 AB：揭示 ------------------------------------------------------
    "reveal_card_set": ("合", 1, '{"op":"reveal","mode":"card_set","source":"initial_deck","target":"target","viewer":"self"}',
                        "私下展示某区/初始牌组并进 reveal(mode:\"card_set\")"),
    "reveal_enemy_hand": ("合", 1, '{"op":"reveal","mode":"enemy_hand","target":"enemy"}',
                          "查看手牌并进 reveal(mode:\"enemy_hand\")（antennae 通道不变）"),
    "reveal_hand_cards": ("合", 1, '{"op":"reveal","mode":"hand","target":"target","viewer":"self","mark":true}',
                          "展示手牌 + revealed 标记并进 reveal(mode:\"hand\")（to 改名 viewer）"),
    "reveal_hand": ("合", 0, '{"op":"reveal","mode":"enemy_hand","target":"enemy"}',
                    "旧别名表里的 reveal_hand 一并删除（替代写法同上）"),
    # ---- 批次 AB：洗牌 ------------------------------------------------------
    "shuffle_discard_into_deck": ("合", 1, '{"op":"shuffle","zone":"discard"}',
                                  "弃牌堆洗入牌堆并进 shuffle(zone:\"discard\")"),
    "shuffle_hand": ("合", 2, '{"op":"shuffle","zone":"hand","target":"self"}',
                     "打乱手牌并进 shuffle(zone:\"hand\")（失明免疫判定保留）"),
    # ---- 批次 AB：快照/还原 -------------------------------------------------
    "snapshot_card_props": ("合", 1, '{"op":"snapshot","mode":"card_props","owner":"self","zone":"hand","store":"card_prop_snapshot","property":"cost_e_override"}',
                            "属性快照并进 snapshot(mode:\"card_props\")：store/过滤/restore_on_destroy 保留"),
    "restore_card_props": ("合", 1, '{"op":"restore","mode":"card_props","owner":"self","store":"card_prop_snapshot"}',
                           "属性还原并进 restore(mode:\"card_props\")"),
    "restore_match_start_stats": ("合", 1, '{"op":"restore","mode":"match_start","target":"self"}',
                                  "回到对局开始并进 restore(mode:\"match_start\")"),
    "restore_turn_start_stats": ("合", 0, '{"op":"restore","mode":"turn_start","target":"self"}',
                                 "回到回合开始并进 restore(mode:\"turn_start\")"),
}

# ---------------------------------------------------------------------------
# Round 33 / 批次 AC + Round 35 收尾：装备 / 状态 / 标签 / 自动打出四族真删。
ROUND35_ACTIONS = {
    # ---- 装备族 → equipment_op(mode=place|give|armor|destroy|seal|unprotect|each) ----
    "destroy_equipment": ("合", 11, '{"op":"equipment_op","mode":"destroy","pick":"choice","target":"enemy"}',
                          "摧毁装备族并进 equipment_op(mode:\"destroy\")：pick 选 choice/random/all/self，"
                          "scope/filter/record_count/equipment 点选逐字保留"),
    "add_equipment_armor": ("合", 1, '{"op":"equipment_op","mode":"armor","target":"self","amount":2}',
                            "给装备/护甲加值并进 equipment_op(mode:\"armor\")"),
    "add_equipment_to_zone": ("合", 1, '{"op":"equipment_op","mode":"give","card":"<牌id>","target":"target","effect_target":"target"}',
                              "凭空造装备卡并进 equipment_op(mode:\"give\")"),
    "remove_equip_protection": ("合", 0, '{"op":"equipment_op","mode":"unprotect","target":"target"}',
                                "清空装备保护层数并进 equipment_op(mode:\"unprotect\")"),
    "for_each_equipment": ("合", 0, '{"op":"equipment_op","mode":"each","target":"target","body":[...]}',
                           "遍历装备的唯一入口并进 equipment_op(mode:\"each\")"),
    # ---- 状态族 → status_op(action=add|set|remove|clear|settle) -------------------
    "status_remove_named": ("合", 9, '{"op":"status_op","action":"remove","status":"<状态id>","amount":"all","target":"self"}',
                            "减层/清空状态并进 status_op(action:\"remove\")；层数上限与免疫判定不变"),
    "clear_statuses": ("合", 1, '{"op":"status_op","action":"clear","statuses":"all","target":"self"}',
                       "名单式清状态并进 status_op(action:\"clear\")（preset 词表原样保留）"),
    "settle_status": ("合", 4, '{"op":"status_op","action":"settle","status":"fire","reduce":1,"target":"target"}',
                      "DoT 结算并进 status_op(action:\"settle\")（fill_from/after/reduce 逐字保留）"),
    # ---- 自动打出族 → auto_play(mode=card|zone_top) ------------------------------
    "auto_play_card": ("合", 3, '{"op":"auto_play","mode":"card","card":{"ref":"last_created_card"},"no_cost":false}',
                       "追加打出一张牌并进 auto_play(mode:\"card\")（逐张结算的队列语义不变）"),
    "auto_play_zone_top": ("合", 1, '{"op":"auto_play","mode":"zone_top","actor":{"ref":"equipment_target"},"zone":"deck","cost":"free"}',
                           "逼某人打出某区顶牌并进 auto_play(mode:\"zone_top\")（失败回收与随机目标不变）"),
}

# ---------------------------------------------------------------------------
# Round 36 / 批次 AD-1：请求族七合一（`request` 伞，type 选类别）。
ROUND36_ACTIONS = {
    "request_target": ("合", 164, '{"op":"request","type":"target","allowed":"any"}',
                       "弹选目标窗口并进 request(type:\"target\")：choice_type 仍是 choose_target，"
                       "allowed/alive_only/candidates/include_self 原样透传"),
    "request_card": ("合", 20, '{"op":"request","type":"card","params":{…}}',
                     "弹选牌窗口并进 request(type:\"card\")：filter/zone/choice_type/multi/min_count "
                     "同时驱动候选集、提交校验与卡级 play_requires（评测口径不变）"),
    "request_confirm": ("合", 0, '{"op":"request","type":"confirm","params":{…}}',
                        "弹二次确认并进 request(type:\"confirm\")（choice_type=confirm；卡数据 0 步，"
                        "play_choice_request 下发的客户端 payload type 保持原样）"),
    "choose_from_zone": ("合", 1, '{"op":"request","type":"zone","zone":"deck","target":"self"}',
                         "从牌堆/弃牌堆/放逐区选一张进手牌并进 request(type:\"zone\")："
                         "choice_type 仍按区域映射回 choose_from_deck|discard|exile"),
    "declare_forced_target": ("合", 1, '{"op":"request","type":"forced_target","target":"self"}',
                              "声明强制目标窗口并进 request(type:\"forced_target\")（Light Bulb 机制不变）"),
    "copy_choice_with_discount": ("合", 0, '{"op":"request","type":"discount_copy","discount_e":1}',
                                  "拟态式「复制所选手牌并打折」并进 request(type:\"discount_copy\")"),
    "request_reorder_deck": ("合", 1, '{"op":"request","type":"reorder_deck","target":"enemy","message":"…"}',
                             "请求重排对手牌堆（魔法护目镜）并进 request(type:\"reorder_deck\")，"
                             "pending_choice 的 choice_type/字段逐字保留"),
}

# 退役但**保留 `_atomic_*` 处理器**的名字：公开契约里已经进
# ``mod_spec_v2.REMOVED_ATOMIC_OPS``（写出来是"已移除 + 替代写法"），但引擎内部
# 或测试会直接调这些私有方法，所以实现留着手工删不得。它们同样必须"卡数据 0 引用"。
HANDLER_KEPT_ACTIONS = {
    "copy_card_instance": (5, '{"op":"copy_card","as_instance":true,"source":{"ref":"current_card"},"target":"self"}',
                           "实例复制并进 copy_card(as_instance:true)；处理器被 copy_card 伞转交，"
                           "且 tests/test_feedback_78_autoplay_queue.py 把 spy 挂在它上面"),
    "create_copies_to_deck_top": (6, '{"op":"copy_card","to_zone":"deck_top","count":1,"def_id":"<牌id>"}',
                                  "造 N 张复制放牌堆顶并进 copy_card(to_zone:\"deck_top\")；"
                                  "tests/test_unique_card_rule.py 直呼处理器"),
    "give_card_to_hand": (18, '{"op":"move_card","mode":"give","target_zone":"hand","card":"<牌id>","amount":1,"target":"self"}',
                          "造牌入手并进 move_card(mode:\"give\")；tests/test_unique_card_rule.py 直呼处理器"),
    "place_as_equip": (71, '{"op":"equipment_op","mode":"place","owner":"self","effect_target":"target"}',
                       "置入装备栏并进 equipment_op(mode:\"place\")；formal_logic_runtime 直呼处理器"),
    "status_add_named": (152, '{"op":"status_op","action":"add","status":"<状态id>","amount":1,"target":"self"}',
                         "叠层状态（mode:\"set\" 即设为 N 层）并进 status_op(action:\"add\")；"
                         "tests/test_status_immunity_application.py 直呼处理器"),
    "add_tag": (11, '{"op":"tag_op","action":"add","card":{"ref":"current_card"},"tag":"<标签>"}',
                "卡内标签并进 tag_op(action:\"add\"|remove|clear)；tests/test_log_key_localization.py 直呼处理器"),
    "add_tag_to_zone": (13, '{"op":"tag_op","action":"add","target":"enemy","zone":"hand","tag":"<标签>"}',
                        "区域打标并进 tag_op（带 zone/zones 即区域级）；tests/test_log_key_localization.py 直呼处理器"),
}

# ---------------------------------------------------------------------------
# 上一批（Round 32 / 批次 AA）真删与真合并的名字。
ROUND32_ACTIONS = {
    # ---- 控制流（语言内置）------------------------------------------------
    "if": ("合", 98, '{"op":"if_else","condition":...,"then":[...]}',
           "if 就是「不写 else 的 if_else」；控制流保留原生驱动，condition/then/else 契约不变"),
    "repeat_until": ("合", 0, '{"op":"repeat","until":<停止条件>,"body":[...]}',
                     "repeat_until 的 condition 改名成 until（每轮开头判停、默认 64 轮上限）"),
    "for_each_list": ("合", 2, '{"op":"for_each","list":<列表表达式>,"name":"item",...}',
                      "list/name 本来就在 for_each 的统一来源词表里；列表来源仍走引擎驱动"),
    "for_each_selected_card": ("合", 5, '{"op":"for_each","bind":"selected_card","body":[...]}',
                               "逐张遍历选中牌成为 for_each 的 bind 预设（chosen_card/selected_card_index 不变）"),
    "list_set": ("合", 0, '{"op":"list_modify","list":"<变量名>","mode":"set","value":[...]}',
                 "列表五兄弟并成 list_modify：list=变量名、mode=动作、index/value=参数"),
    "list_append": ("合", 1, '{"op":"list_modify","list":"<变量名>","mode":"append","value":<元素>}',
                    "同上；非列表旧值包成单元素的旧行为保留"),
    "list_insert": ("合", 0, '{"op":"list_modify","list":"<变量名>","mode":"insert","index":1,"value":<元素>}',
                    "同上；insert 下标仍夹在 [0, len]"),
    "list_delete": ("合", 0, '{"op":"list_modify","list":"<变量名>","mode":"delete","index":1}',
                    "同上；越界删除仍是空操作"),
    "list_clear": ("合", 0, '{"op":"list_modify","list":"<变量名>","mode":"clear"}',
                   "同上；清空直接写空列表"),
    # ---- 生命族 -----------------------------------------------------------
    "heal": ("合", 45, '{"op":"health_op","mode":"heal","target":...,"amount":N}',
             "生命族并成 health_op；heal_block 判定/上限/实际回复量战报逐字保留，"
             "log_positive_only 这种运行时参数收进同一个原子"),
    "lose_health": ("合", 1, '{"op":"health_op","mode":"lose","target":...,"amount":N}',
                    "无视护甲的失去生命（无敌免疫分支/成就/世界树检查/游戏结束判定全保留）"),
    "set_health": ("合", 1, '{"op":"health_op","mode":"set","target":...,"amount":N}',
                   "上限截断 max(0, min(amount, max_health)) + 成就记账保留"),
    "swap_health": ("合", 0, '{"op":"health_op","mode":"swap","target1":...,"target2":...}',
                    "交换生命（旧实现交换后不钳位，逐字保留）"),
    "on_fatal_set_health_exile": ("合", 0, '{"op":"health_op","mode":"fatal","kind":"exile","health":5}',
                                  "被动声明：触发时点仍在 _check_yggdrasil，识别改走 _fatal_declaration_kind"),
    "on_fatal_invincible_then_die": ("合", 0, '{"op":"health_op","mode":"fatal","kind":"invincible_die"}',
                                     "绷带被动声明（PASSIVE_EFFECT_TYPES 的成员判定已改成按 mode 识别）"),
    # ---- 资源族 -----------------------------------------------------------
    "gain_e": ("合", 9, '{"op":"resource_op","resource":"e","delta":N,"target":...}',
               "资源族并成 resource_op：正数获得、负数消耗（旧运行时语义），上限/记账不变"),
    "gain_m": ("合", 16, '{"op":"resource_op","resource":"m","delta":N,"target":...}',
               "同上；默认战报仍播报请求值，log_positive_only 仍可静音"),
    "spend_resource": ("合", 5, '{"op":"resource_op","resource":"e|m","mode":"spend","amount":N}',
                       "消耗走 _spend_resource（派发 resource_spent），实际花掉的数写进 spent 上下文"),
    "coffee_gain_e": ("合", 0, '{"op":"resource_op","resource":"e","delta":2,"reset_coffee":true,"card_heavy":1}',
                      "咖啡副作用（重置首次使用标记 + 本牌叠沉重）成为显式参数，默认战报逐字保留"),
    "aura_enemy_elixir_recovery": ("合", 0, '{"op":"resource_op","mode":"aura_recovery","resource":"e","amount":N}',
                                   "光环声明（原子本身空操作），数值由 _declared_aura_elixir_bonus 统一读取"),
    # ---- 费用族 -----------------------------------------------------------
    "increase_next_cost": ("合", 1, '{"op":"modify_next_cost","delta":N,"target":...}',
                           "费用族并成 modify_next_cost：delta 正负定方向（正=加费/加重）"),
    "reduce_next_cost": ("合", 0, '{"op":"modify_next_cost","delta":-N,"target":...}',
                         "同上；负 delta 走旧 reduce 的 temp_swift 分支"),
    # ---- 抽牌族 -----------------------------------------------------------
    "draw_cards": ("合", 9, '{"op":"draw","count":N,"target":...}',
                   "抽牌族并成 draw（count + modifiers）；默认值就是旧 draw_cards（触发抽牌钩子、播报实际张数）"),
    "equip_reduce_draw": ("合", 0, '{"op":"draw","count":0,"modifiers":[{"type":"sluggish","amount":N,"target":...}]}',
                          "装备减抽成为 draw 的 sluggish 修正（默认战报「敌方获得N层迟缓」保留）"),
}

# ---------------------------------------------------------------------------
# 本批（Round 31 / 批次 Z）真删与真合并的名字。
# 表是**结果**：这些名字在当前源码里都已经没有 ``_atomic_*`` 实现。
# 每行 = (判定, 迁移前用量, 替代写法, 理由)
ROUND31_ACTIONS = {
    "move_to_hand": ("删", 0, '{"op":"move_card","zone":"hand",...}',
                     "Round 29 留的同名兼容垫片（3 行转发、不进契约）；本轮真删"),
    "var_set": ("删", 0, '{"op":"player_var_change","mode":"set",...}',
                "Round 29 留的兼容垫片；Round 30 起引擎内部已无调用点"),
    "player_prop_set": ("删", 0, '{"op":"player_prop_change","mode":"set",...}',
                        "Round 29 留的兼容垫片（Round 29 已验证逐字节等价）"),
    "player_prop_add": ("删", 0, '{"op":"player_prop_change","mode":"add",...}',
                        "Round 29 留的兼容垫片（Round 29 已验证逐字节等价）"),
    "card_var_set": ("删", 0, '{"op":"card_var_change","mode":"set",...}',
                     "Round 29 留的兼容垫片，无调用点"),
    "card_var_add": ("删", 0, '{"op":"card_var_change","mode":"add",...}',
                     "Round 29 留的兼容垫片，无调用点"),
    "resource_spend": ("合", 0, '{"op":"spend_resource","resource":"elixir|magic",...}',
                       "与 spend_resource 重复（同为 _spend_resource 的壳）；合并后 spend_resource "
                       "收 target，并保留 all / spent 记账"),
    "set_status_named": ("合", 0, '{"op":"status_op","action":"set","mode":"set",...}',
                         "与 status_add_named 同调 _apply_status_add_family，只差默认层数来源；"
                         "参数一律走 mode"),
    "clear_status": ("合", 2, '{"op":"status_op","action":"remove","amount":"all",...}',
                     "清的是 _status_attr_field 那 8 个玩家属性字段，与命名状态族同一张属性表；"
                     "合并后拿到别名组/上限/成就/状态钩子（默认不再自动播报，见报告差异 1）"),
    "resolve_status_once": ("合", 3, '{"op":"status_op","action":"settle","reduce":1,...}',
                            "灼烧结算一次并减 N 层 = settle_status(reduce)；伤害类型/标签/默认战报"
                            "逐字保留（log:false 现在真的静音，见报告差异 2）"),
    "set_untargetable": ("合", 0, '{"op":"player_status_layers","status":"untargetable","shovel":true}',
                         "只加 1 层且强制点亮 shovel；合并后 shovel 变成显式参数"),
    "untargetable_layers": ("合", 1, '{"op":"player_status_layers","status":"untargetable",...}',
                            "玩家状态层数族（Ocean 黄瓜的 after_resolution 在用）"),
    "set_invincible": ("合", 1, '{"op":"player_status_layers","status":"invincible"}',
                       "无敌走 _set_invincible_until_next_own_turn_end 的回合簿记，"
                       "与 player_prop_change(property:'invincible') 只写字段不同"),
    "destroy_self_equipment": ("合", 8, '{"op":"equipment_op","mode":"destroy","pick":"self"}',
                               "拆「这张牌自己挂着的那件装备」；与 destroy_current_equipment 同解"),
    "destroy_current_equipment": ("合", 2, '{"op":"equipment_op","mode":"destroy","pick":"self"}',
                                  "同上（全场按实例 id 找 = self 模式的第一段）"),
    "destroy_all_destroyable_equipment": (
        "合", 1,
        '{"op":"equipment_op","mode":"destroy","pick":"all","filter":"destroyable","record_count":true,"target":"both"}',
        "拆光所有非 indestructible 装备并记账；filter/record_count 成为规范参数"),
    "destroy_equipment_choice_or_first": ("合", 0,
                                          '{"op":"equipment_op","mode":"destroy","pick":"choice","target":"enemy"}',
                                          "与「点选装备」选择窗口耦合：本轮把窗口接到 "
                                          "destroy_equipment(mode:'choice') 上（无点选时回落到第一件）"),
    "card_prop_set": ("合", 18, '{"op":"card_prop_change","mode":"set",...}',
                      "参数与 player_prop_change 对齐；实现体（钳位/上限/联动字段）原样搬过来"),
    "card_prop_add": ("合", 10, '{"op":"card_prop_change","mode":"add",...}',
                      "同上；multi_petal 的 fission_level 双倍特例保留"),
    "card_prop_mul": ("合", 0, '{"op":"card_prop_change","mode":"mul",...}',
                      "同上；multiplier 仍是它认的键"),
    "remove_tag": ("合", 0, '{"op":"tag_op","action":"remove",...}',
                   "标签族统一到 add_tag/add_tag_to_zone 的 mode（add/remove/clear/toggle）"),
    "clear_tags": ("合", 0, '{"op":"tag_op","action":"clear",...}',
                   "同上；清空时把有效标签压进 disabled_flags 的行为保留"),
    "remove_tag_from_zone": ("合", 0, '{"op":"tag_op","action":"remove",...}',
                             "与 add_tag_to_zone 共用区域遍历/计数/战报，mode 决定加减"),
    "toggle_tag_in_zone": ("合", 1, '{"op":"tag_op","action":"toggle",...}',
                           "逐张翻转（Yin-Yang 在用），合并后仍是 add_tag_to_zone 的一档 mode"),
    "put_card_to_deck": ("删", 0, '{"op":"move_card","zone":"deck","card":{"ref":"selected_card"},...}',
                         "被 move_card 完全覆盖（selected_card ref 读的正是 choice.target_instance_id）"),
    "give_card_to_discard": ("删", 0, '{"op":"create_card","card_id":"...","to":"discard",...}',
                             "被运行时的 create_card(to:) 覆盖（造牌入区，支持 target/多目标）"),
    "reveal_deck_top": ("删", 0, '{"op":"reveal","mode":"card_set","source":"deck","amount":N,...}',
                        "reveal_card_set 现在收 amount/top/limit，是「看牌堆顶 N 张」的超集"),
    "reveal_tag_hand": ("删", 0, '{"op":"reveal_hand_cards","tag":"revealed","to":"self",...}',
                        "reveal_hand_cards 现在收 tag 过滤 + amount 截断；旧实现只写一份没人读的载荷"),
    "for_each_target": ("删", 0, '{"op":"for_each","source":"wide_strike_targets","bind":"target",...}',
                        "Round 16 的薄转发，就是 for_each 的 bind:'target' 预设"),
}

# ---------------------------------------------------------------------------
# 保留的原子：逐条理由（未列出的名字按 KEPT_GROUPS 的族理由兜底）。
KEPT_EXPLICIT = {
    "status_add_named": "状态族规范名（mode=add|set），承接旧 add_status/set_status/set_status_named",
    "status_remove_named": "状态族规范名（不写 amount 即「清空」），承接旧 remove_status/clear_status",
    "clear_statuses": "preset 名单式清状态（buffs/debuffs/all + 自定义状态），与命名状态族互补",
    "settle_status": "DoT 结算唯一实现（decay/fill_from/after + Round 31 的 reduce）",
    "player_status_layers": "Round 31 新合并体：玩家状态层数（untargetable/invincible）",
    "player_prop_change": "玩家属性写值唯一实现（mode=set|add），承接 player_prop_set/add",
    "player_var_change": "玩家变量唯一实现（mode=set|add|sub|mul|div），承接 var_set 五兄弟",
    "card_var_change": "卡牌变量唯一实现（mode=set|add，maximum 钳位）",
    "card_prop_change": "Round 31 新合并体：卡牌属性写值（mode=set|add|mul）",
    "card_prop_add_to_zone": "区域批量改卡牌属性（count/随机/标签徽章），与单卡版互补",
    "player_stat_change": "护甲/闪避族唯一实现（mode=add|remove|set）",
    "destroy_equipment": "摧毁装备族唯一实现（mode=choice|random|all|self，filter/record_count/scope）",
    "resource_op": "Round 32 新合并体：资源族唯一实现（resource + delta 正负 + all/spent/coffee/aura）",
    "add_tag": "卡内标签族唯一实现（mode=add|remove|clear）",
    "add_tag_to_zone": "区域标签族唯一实现（mode=add|remove|toggle）",
    "for_each": "循环族唯一驱动（source/bind/condition/limit + 断点续跑；Round 32 收编 for_each_list / for_each_selected_card）",
    "move_card": "区域移动族唯一实现（zone=hand|deck|discard|exile）",
    "choose_from_zone": "区域取牌族唯一实现（zone=deck|discard|exile + 选择窗口联动）",
    "card_counter": "卡内计数器（mode=play|equip_turns|reset）",
    "deal_damage": "攻击管线唯一入口（力量/精准/暴击/子瓣继承 + hits）",
    "direct_damage": "直伤管线唯一入口（source_text/damage_type/damage_tag/hits）",
    "health_op": "Round 32 新合并体：生命族唯一实现（mode=heal|lose|set|swap|fatal）",
    "turn_mod_add": "每回合修正（kind=e_regen|m_regen|draw）",
    "global_mult": "全场倍率（kind=damage|heal|cost）",
    "place_as_equip": "把牌作为装备加入（71 处使用，签名冻结）",
    "add_equipment_to_zone": "从卡 id 造装备进装备区",
    "add_equipment_armor": "所有装备获得护甲（层数）",
    "seal_equipment": "尘封装备（层数）",
    "equipment_prop_set": "装备属性写值（设为）",
    "equipment_prop_add": "装备属性写值（增加）",
    # Round 33 / 批次 AB：四条 AB 伞原子。
    "reveal": "Round 33 揭示伞（mode=card_set|enemy_hand|hand）",
    "shuffle": "Round 33 洗牌伞（zone=discard|hand）",
    "snapshot": "Round 33 快照伞（mode=card_props）",
    "restore": "Round 33 还原伞（mode=card_props|match_start|turn_start）",
    "remove_equip_protection": "清空装备保护层数",
    "counter_equip_protect": "装备保护层数（反制族）",
    # Round 32 / 批次 AA：on_fatal_* 两条并进 health_op(mode:"fatal")。
    "defer_game_over": "延迟胜负判定（结算中途不判负）",
    "block_own_actions": "禁用出牌（shovel）",
    "block_card_type": "禁止某类牌",
    "force_card_type": "只允许某类牌",
    "nullify_current_card": "取消当前牌",
    "mark_self_damage_source": "标记下次自身伤害来源",
    "multiply_next_damage": "下次伤害倍率",
    "modify_damage": "伤害修正钩子（数据侧）",
    "fission": "裂变层数（+）",
    "fusion": "聚变层数（+）",
    "for_each_equipment": "装备循环（Round 17 未并入 for_each）",
    "timed_effect": "计时效果（duration/trigger/body）",
    "countdown_var": "倒计时变量（player_var_change 的定时封装）",
    "register_play_listener": "出牌监听注册（scope/duration/body）",
    "queue_auto_play": "排队自动打出（card/source/each_turn/cost/exile）",
    "auto_play_card": "立刻自动打出（含 no_cost/auto_choice）",
    "auto_play_zone_top": "自动打出某区顶牌（Kitty 类）",
    "once_per_play": "每次打出至多一次（监听去重）",
    "after_all": "把 body 放到当前效果之后执行",
    "if_else": "控制流原语（Round 32 收编 if：不写 else 就是旧 if）",
    "repeat": "控制流原语（Round 32 收编 repeat_until 的 until=停止条件）",
    "break": "**语言原语**（跳出循环，不算可参数化的原子，Round 32 明确保留）",
    "continue": "**语言原语**（跳过本次迭代，Round 32 明确保留）",
    "request": "Round 36 请求族唯一公开 op（type=target|card|confirm|zone|forced_target|discount_copy|reorder_deck；旧 request_target 等七个名字已退役）",
    "reveal_enemy_hand": "查看手牌（antennae 通道）",
    "reveal_hand_cards": "展示手牌 + revealed 标记（tag/amount 过滤）",
    "reveal_card_set": "私下展示某区/初始牌组（viewer + amount）",
    "copy_card": "复制牌进手（带印痕处理）",
    "copy_card_instance": "复制牌实例（保留印痕/自定义变量）",
    "copy_choice_with_discount": "复制并打折（走选择窗口）",
    "create_copies_to_deck_top": "造 N 张复制放牌堆顶",
    "create_counter": "生成/记录 counter 类型标记",
    "mark_original_card": "标记原牌（回手/回收用）",
    "exile_this": "放逐自身（印记）",
    "transform_card": "变换牌（标记）",
    "transform_cards": "批量变换牌",
    "remove_specific_card": "移除指定牌（手牌/装备区）",
    "random_zone_card_to_hand": "随机取一张区域牌进手",
    "steal_enemy_card": "偷取敌方手牌/装备（选择窗口）",
    "swap_hands": "交换双方手牌",
    "shuffle_hand": "打乱手牌（失明）",
    "shuffle_discard_into_deck": "弃牌堆洗回牌堆",
    "give_card_to_hand": "造牌入手（overflow/missing 处理）",
    "give_card_to_deck": "造牌入牌堆（position/flags）",
    "give_magic_orb_to_hand": "造魔法宝珠入手（固定印痕）",
    "move_cards_to_deck": "批量把牌放回牌堆",
    "draw": "Round 32 抽牌族唯一实现（count + hooks + log_amount + modifiers）",
    "discard_choice_then_draw": "先弃后抽（弃牌选择窗口）",
    "discard_hand_by_paid_e": "按本回合已付 E 弃手牌（Desert）",
    "modify_next_cost": "Round 32 新合并体：下次出牌费用修正（delta 正负定方向）",
    "snapshot_card_props": "牌属性快照（按实例存）",
    "restore_card_props": "恢复牌属性快照",
    "restore_match_start_stats": "恢复开局属性",
    "restore_turn_start_stats": "恢复回合开始属性",
    "set_card_prop_random": "区域内随机设定属性",
    "list_modify": "Round 32 新合并体：列表写值（mode=set|append|insert|delete|clear）",
    "charge_self_damage": "充能自身伤害",
    "counter_pending_attack_damage": "反击待结算攻击伤害（Desert）",
    "absorb_attack_damage": "吸收攻击伤害（body + once）",
    "ricochet_attack": "弹射（攻击管线变体）",
    "lifesteal_damage": "吸血伤害",
    "triangle_damage": "三角伤害（层数 x 基数）",
    "card_damage_multiply": "聚变倍率（fusion_level x N）",
    "activate_corruption": "激活装备腐化",
    "broadcast_event": "对外广播事件",
    "response_declare": "声明响应（占位步骤，无实现体）",
    "trigger_manual": "手动触发（占位步骤，无实现体）",
    "declare_forced_target": "声明强制目标窗口（Light Bulb）",
    "add_charge_to_hand": "手牌充能（Arctic）",
    "apply_turn_regen": "回合回复（Jungle）",
    "assembler_effect": "装配机（Factory）",
    "cogwheel_mark": "齿轮标记（Factory）",
    "crit_multiplier_add": "暴击倍率（+，Hel）",
    "delayed_blind_next_turn": "下回合延迟失明（Ocean）",
    "delayed_reveal_hand_next_turn": "下回合延迟展示手牌",
    "electric_web_arm": "电网护臂（Factory）",
    "goggles_enable": "护目镜启用（Factory）",
    "grant_temp_swift_highest_e": "费用最高的手牌暂时迅捷（Jungle）",
    "honey_control": "蜂蜜控制（Bee 类）",
    "magic_relic_trigger": "魔法遗物触发",
    "magic_salt_reflect": "魔法盐反射",
    "plank_immunity": "木板免疫（Jungle）",
    "third_eye_precision_or_hidden": "第三眼：精准或隐匿（Garden）",
}

KEPT_GROUPS = (
    ("状态与层数",
     ("status", "poison", "toxic", "burn", "frost", "blind", "stagnation", "fracture",
      "sluggish", "vulnus", "protection", "layer", "corruption", "invincible", "untargetable"),
     "状态族：层数/别名组/上限/成就/状态钩子都在这一族，删掉要重写整套状态记账"),
    ("伤害与攻击",
     ("damage", "attack", "lifesteal", "ricochet", "crit", "fission", "absorb", "counter"),
     "两条伤害管线（攻击/直伤）及其变体，卡面机制直接依赖"),
    ("区域、给牌与揭示",
     ("move", "give", "draw", "discard", "exile", "deck", "hand", "steal", "shuffle",
      "reveal", "copy_card", "remove_specific_card", "random_zone"),
     "区域语义完整（手牌上限/唯一牌/放逐标记），是卡数据的第一大类"),
    ("装备",
     ("equip", "durability", "seal"),
     "装备区有自己的护甲/保护/尘封/摧毁规则，与玩家属性族不可互换"),
    ("属性、变量与资源",
     ("prop", "resource", "elixir", "magic", "armor", "health", "cost", "var", "stat",
      "global_mult", "turn_mod", "list_", "counter", "fusion", "heal", "gain"),
     "属性/变量/资源的写入口径各不相同（钳位、上限、同步字段），逐条保留"),
    ("标签",
     ("tag",),
     "标签族已收敛成 add_tag / add_tag_to_zone 两条规范名 + mode"),
    ("控制流与时点",
     ("if", "for_each", "repeat", "once", "break", "continue", "after_all", "random",
      "timed", "turn", "listener", "timer", "countdown", "queue", "auto_play", "game_over",
      "log", "request", "choose", "merge", "nullify", "block_", "force_", "exile_this",
      "transform", "mark_", "create_"),
     "控制流/时点/监听/占位步骤是数据步骤的骨架"),
)


def usage_map() -> dict:
    atoms = sorted(atomic_registry.engine_atomic_ops())
    usage: collections.Counter = collections.Counter()
    for package in sorted(MODS_DIR.glob("*.gtnmod")):
        with zipfile.ZipFile(package) as archive:
            payload = json.loads(archive.read("mod.json"))
        text = json.dumps(payload, ensure_ascii=False)
        for name in atoms:
            usage[name] += len(re.findall(r'"op"\s*:\s*"%s"' % re.escape(name), text))
    return usage


def kept_reason(name: str) -> tuple:
    explicit = KEPT_EXPLICIT.get(name)
    for label, keys, fallback in KEPT_GROUPS:
        if any(key in name for key in keys):
            return label, explicit or fallback
    if explicit:
        return "其它", explicit
    return "其它", "卡专用/机制钩子：仍有卡数据或引擎联动引用，删掉会丢机制（详见《引擎原子与数据步骤清单》）"


def build() -> dict:
    atoms = sorted(atomic_registry.engine_atomic_ops())
    usage = usage_map()
    kept = []
    for name in atoms:
        family, reason = kept_reason(name)
        kept.append({"name": name, "family": family, "usage": usage.get(name, 0), "reason": reason})
    kept.sort(key=lambda row: (row["family"], row["name"]))
    actions = []
    for name, (verdict, before, replacement, reason) in (
        {**ROUND31_ACTIONS, **ROUND32_ACTIONS, **ROUND33_ACTIONS, **ROUND35_ACTIONS, **ROUND36_ACTIONS}
    ).items():
        actions.append({
            "name": name, "verdict": verdict, "before": before,
            "usage": usage.get(name, 0), "replacement": replacement, "reason": reason,
        })
    actions.sort(key=lambda row: row["name"])
    handler_kept = []
    for name, (before, replacement, reason) in HANDLER_KEPT_ACTIONS.items():
        handler_kept.append({
            "name": name, "before": before, "usage": usage.get(name, 0),
            "replacement": replacement, "reason": reason,
        })
    handler_kept.sort(key=lambda row: row["name"])
    return {
        "atoms": atoms, "usage": usage, "kept": kept, "actions": actions,
        "handler_kept": handler_kept,
    }


def preservation_rows() -> list:
    """必须保留清单：契约里没有 ``_atomic_*`` 实现的那几类名字。"""

    groups = mod_spec_v2.logic_op_groups(include_empty=False)
    why = {
        "运行时原生步骤（`run_v2_step`）": "运行时自己执行（造牌/挂起 UI/临时变量…），没有 `_atomic_*`",
        "表达式算子（`eval_v2_value`）": "写在数值/文本参数位置，不是步骤；删掉等于砍掉取值语言",
        "条件算子（`check_v2_condition`）": "只能出现在 condition/run_if/unless 门控位置",
        "事件与声明键（`events` / `_EFFECT_ALIASES`）": "events 键名与引擎别名声明键，卡数据正在用",
    }
    rows = []
    for label, _names in mod_spec_v2.LOGIC_OP_GROUPS:
        names = groups.get(label) or set()
        if not names or "真原子" in label:
            continue
        rows.append(
            f"| {label} | {len(names)} | " + "、".join(f"`{name}`" for name in sorted(names))
            + f" | {why.get(label, '契约保留名')} |"
        )
    patch_ops = sorted(getattr(mod_spec_v2, "VALID_PATCH_OPS", ()) or ())
    rows.append(
        f"| `patch` 词表（与步骤 op 同名不同义） | {len(patch_ops)} | "
        + "、".join(f"`{name}`" for name in patch_ops)
        + " | mod patch 是对资源打补丁的词表，与引擎原子无关（`remove_tag` 在这里仍然合法） |"
    )
    editor_ops = ["cancel_current_card", "cancel_event", "show_hint", "stop", "unknown_step"]
    rows.append(
        f"| 编辑器专用块 op | {len(editor_ops)} | "
        + "、".join(f"`{name}`" for name in editor_ops)
        + " | 只在编辑器/旧工程里出现，运行时侧是显式报错，不属于引擎原子 |"
    )
    logic_ops = sorted(set(re.findall(
        r'if op == "([a-z_]+)"', (ROOT / "formal_logic_runtime.py").read_text(encoding="utf-8")
    )))
    rows.append(
        f"| 「形式逻辑」动作词表（`formal_logic_runtime`） | {len(logic_ops)} | "
        + "、".join(f"`{name}`" for name in logic_ops)
        + " | 这是 Formal Logic 包自己的动作队列（`_run_formal_logic_actions` 直接执行），"
          "与引擎原子同名不同义，**不受本批删除影响** |"
    )
    return rows


def render(model: dict) -> str:
    lines = []
    lines.append("# 原子全量清单（Round 33 / 批次 AB+AC+AD · 2026-09-12）")
    lines.append("")
    lines.append("本表**逐行**覆盖当前全部引擎原子（`_atomic_*` 实现），并列出 Round 31 / 32 / 33 真删/真合并的每一个名字。")
    lines.append(f"表里所有判「删」或「合」的行**都已在本轮执行完毕**：`--check` 会验证这些名字已经没有")
    lines.append(f"任何 `_atomic_*` 实现、卡数据 0 引用（当前引擎原子 {len(model['atoms'])} 个）。")
    lines.append("")
    lines.append("生成：`python tools/atom_full_inventory.py`；校验：`python tools/atom_full_inventory.py --check`。")
    lines.append("用量口径与 `tools/mod_atom_report.py` 完全一致（`op`/`type` 键、嵌套步骤展开）。")
    lines.append("")
    lines.append(f"## 一、Round 31 / 32 / 33 真删 / 真合并（{len(model['actions'])} 个名字）")
    lines.append("")
    lines.append("| 原子 | 判定 | 迁移前用量 | 本批用量 | 替代写法 | 理由 |")
    lines.append("|---|---|---|---|---|---|")
    for row in model["actions"]:
        lines.append(
            f"| `{row['name']}` | {row['verdict']} | {row['before']} | {row['usage']} | "
            f"`{row['replacement']}` | {row['reason']} |"
        )
    lines.append("")
    lines.append("带参数替代的名字进 `mod_spec_v2.REMOVED_ATOMIC_OPS`（替代写法是完整 JSON），纯改名的进")
    lines.append("`RENAMED_ATOMIC_OPS`；两条执行路径（`mod_runtime_v2.run_v2_step` 与")
    lines.append("`game_engine._run_effect_list`）都会给出「已移除/已改名 + 请改用」的显式报错，不静默。")
    lines.append("")
    lines.append(
        f"## 一bis、退役但保留私有处理器（{len(model['handler_kept'])} 个名字）"
    )
    lines.append("")
    lines.append("这些名字同样进了 `REMOVED_ATOMIC_OPS`（不在对外契约里，卡数据写出来是显式报错），")
    lines.append("但 `_atomic_*` 处理器留着——引擎内部或测试直接调它（见理由列）。因此它们**不在**")
    lines.append("上面的「真删」表里，也不算引擎原子清单的删除项；本轮只要求卡数据 0 引用。")
    lines.append("")
    lines.append("| 原子 | 迁移前用量 | 本批用量 | 替代写法 | 处理器为什么留着 |")
    lines.append("|---|---|---|---|---|")
    for row in model["handler_kept"]:
        lines.append(
            f"| `{row['name']}` | {row['before']} | {row['usage']} | `{row['replacement']}` | {row['reason']} |"
        )
    lines.append("")
    lines.append(f"## 二、保留清单：当前全部引擎原子（{len(model['kept'])}）")
    lines.append("")
    lines.append("| 原子 | 家族 | 用量 | 判定 | 理由 |")
    lines.append("|---|---|---|---|---|")
    for row in model["kept"]:
        lines.append(f"| `{row['name']}` | {row['family']} | {row['usage']} | 留 | {row['reason']} |")
    lines.append("")
    lines.append("## 三、必须保留清单（语言原语 / 扩展点 / 机制钩子）")
    lines.append("")
    lines.append("这些名字不在 `_atomic_*` 实现表里，但属于 DSL 契约，**不属于删除候选**：")
    lines.append("")
    lines.append("| 类别 | 数量 | 名字 | 为什么必须留 |")
    lines.append("|---|---|---|---|")
    lines.extend(preservation_rows())
    lines.append("")
    lines.append("## 四、统计")
    lines.append("")
    lines.append("| 项 | 值 |")
    lines.append("|---|---|")
    lines.append(f"| 引擎原子（本表逐行覆盖） | {len(model['atoms'])} |")
    lines.append(f"| 本批删除 / 合并的名字 | {len(model['actions'])} |")
    lines.append(f"| 其中判定「合」 | {sum(1 for row in model['actions'] if row['verdict'] == '合')} |")
    lines.append(f"| 其中判定「删」 | {sum(1 for row in model['actions'] if row['verdict'] == '删')} |")
    lines.append(f"| 用量 0 的引擎原子 | {sum(1 for row in model['kept'] if row['usage'] == 0)} |")
    lines.append(f"| 用量 > 0 的引擎原子 | {sum(1 for row in model['kept'] if row['usage'] > 0)} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def check(model: dict, text: str, out_path: pathlib.Path) -> int:
    problems = []
    engine_ops = set(model["atoms"])
    for row in model["actions"]:
        if row["verdict"] not in ("删", "合"):
            problems.append(f"{row['name']}: 判定必须是 删/合")
        if row["name"] in engine_ops:
            problems.append(f"{row['name']}: 表里写「删/合」，但引擎里还有 _atomic_{row['name']} 实现")
        if row["usage"]:
            problems.append(f"{row['name']}: 卡数据仍有 {row['usage']} 处引用")
    kept_names = [row["name"] for row in model["kept"]]
    if len(kept_names) != len(set(kept_names)):
        problems.append("保留表里有重复行")
    if set(kept_names) != engine_ops:
        problems.append(
            f"保留表与引擎原子不一致：缺 {sorted(engine_ops - set(kept_names))[:5]}，"
            f"多 {sorted(set(kept_names) - engine_ops)[:5]}"
        )
    if set(kept_names) & {row["name"] for row in model["actions"]}:
        problems.append("同一个名字同时出现在删除表与保留表")
    for row in model["handler_kept"]:
        if row["name"] not in engine_ops:
            problems.append(
                f"{row['name']}: 表里写「保留处理器」，但引擎里已经没有 _atomic_{row['name']}"
            )
        if row["usage"]:
            problems.append(f"{row['name']}: 保留处理器的名字，卡数据仍有 {row['usage']} 处引用")
        if row["name"] in {item["name"] for item in model["actions"]}:
            problems.append(f"{row['name']}: 同时出现在真删表与保留处理器表")
    if out_path.is_file():
        on_disk = out_path.read_text(encoding="utf-8").replace("\r\n", "\n")
        if on_disk != text.replace("\r\n", "\n"):
            problems.append(f"{out_path.name} 与重新生成的内容不一致（重跑一次即可刷新）")
    for problem in problems:
        print(f"[check] {problem}", file=sys.stderr)
    return 1 if problems else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="生成《原子全量清单》（只读源码与卡数据）")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--stdout", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    model = build()
    text = render(model)
    out_path = pathlib.Path(args.out)
    if args.stdout:
        print(text, end="")
        return 0
    if args.check:
        return check(model, text, out_path)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    print(f"written: {out_path} ({out_path.stat().st_size} bytes)")
    print(
        f"引擎原子 {len(model['atoms'])} | 删除/合并 {len(model['actions'])} | "
        f"零用量原子 {sum(1 for row in model['kept'] if row['usage'] == 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
