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

# ---------------------------------------------------------------------------
# Round 37 / 批次 AD-2：事件族三合一（`delayed_effect` / `on_event` / `emit_event`）。
ROUND37_ACTIONS = {
    # ---- 延迟族 → delayed_effect(mode=timed|blind|reveal_hand) ----------------
    "timed_effect": ("合", 6,
                     '{"op":"delayed_effect","mode":"timed","trigger":"target_turn_start","duration":1,"target":"target","body":[…]}',
                     "延迟监听并进 delayed_effect(mode:\"timed\")：三条分支共用同一张计时表，"
                     "trigger 词表、触发相位与 duration/once 口径逐字保留"),
    "delayed_blind_next_turn": ("合", 1,
                                '{"op":"delayed_effect","mode":"blind","target":"target","amount":1}',
                                "下回合延迟失明 + 洗牌并进 delayed_effect(mode:\"blind\")"
                                "（相位仍是 target_turn_start_after_status_clear，duration 固定 1）"),
    "delayed_reveal_hand_next_turn": ("合", 0,
                                      '{"op":"delayed_effect","mode":"reveal_hand","target":"target"}',
                                      "下回合延迟展示手牌并进 delayed_effect(mode:\"reveal_hand\")"
                                      "（相位仍是 target_turn_start；卡数据 0 步）"),
    # ---- 监听 / 收尾 / 触发族 → on_event(trigger=play|this_play|after_all|equipment_trigger) ----
    "once_per_play": ("合", 9,
                      '{"op":"on_event","trigger":"this_play","name":"<标识>","body":[…]}',
                      "每次出牌一次并进 on_event(trigger:\"this_play\")：标记仍存在卡实例上，"
                      "随每次出牌清理；为假的 condition 依旧不消耗标记"),
    "register_play_listener": ("合", 1,
                               '{"op":"on_event","trigger":"play","target":"target","duration":"turn","scope":"owner_turn","body":[…]}',
                               "出牌监听注册并进 on_event(trigger:\"play\")：同一张 play_listeners 表，"
                               "scope/duration/exclude_card_ids/once 逐字保留"),
    "after_all": ("合", 0,
                  '{"op":"on_event","trigger":"after_all","body":[…]}（或 {"op":"on_event","after":true,…}）',
                  "收尾控制流并进 on_event(trigger:\"after_all\")：与旧实现一样就地跑 body（卡数据 0 步）"),
    "magic_relic_trigger": ("合", 1,
                            '{"op":"on_event","trigger":"equipment_trigger","effect":"magic_relic"}',
                            "魔法遗物触发并进 on_event(trigger:\"equipment_trigger\")："
                            "消耗队友 2M、自己 +3M；1v1 无队友时按旧行为直接返回"),
    # ---- 广播 / 占位族 → emit_event ----
    "broadcast_event": ("合", 0,
                        '{"op":"emit_event","event":"<事件名>"}',
                        "广播事件并进 emit_event：默认播报\"广播事件：<事件名>\"（卡数据 0 步）"),
    "trigger_manual": ("合", 0,
                       '{"op":"emit_event","event":"manual_trigger","silent":true}',
                       "占位步骤（原本没有实现体）并进 emit_event(silent:true)：同样是\"什么都不做\"，"
                       "但换成可读的事件名（卡数据 0 步）"),
}

# 退役但**保留 `_atomic_*` 处理器**的名字：公开契约里已经进
# ---------------------------------------------------------------------------
# Round 38 / 批次 AD-3：回合控制族三合一（`turn_control` 伞，mode 选分支）。
ROUND38_ACTIONS = {
    "force_end_turn": ("合", 3, '{"op":"turn_control","mode":"end"}',
                       "立刻结束本回合并进 turn_control(mode:\"end\")：标记仍挂在出牌者身上，"
                       "真正结束回合仍在 _play_card 把本牌整套效果结算完之后（\"本牌结算完再结束\"不变）；"
                       "旧实现忽略 target，新分支同样不解析"),
    "skip_turn": ("合", 1, '{"op":"turn_control","mode":"skip","target":"enemy","amount":1}',
                  "跳过目标 N 个回合并进 turn_control(mode:\"skip\")："
                  "层数、状态免疫判定、成就峰值记账与默认战报逐字保留"),
    "extra_turn": ("合", 0, '{"op":"turn_control","mode":"extra","target":"self"}',
                   "额外回合并进 turn_control(mode:\"extra\")（卡数据 0 步，登记为可用分支）"),
    # ---- 行为过滤族 → action_filter(mode=block_own|block_type|force_type|negate) ----
    "block_own_actions": ("合", 0, '{"op":"action_filter","mode":"block_own"}',
                          "禁用出牌（shovel_active）并进 action_filter(mode:\"block_own\")："
                          "只作用于出牌者，旧实现忽略 target，新分支同样不解析"),
    "block_action": ("合", 0, '{"op":"action_filter","mode":"block_own"}',
                     "block_own_actions 的旧别名一起退役（卡数据 0 步）"),
    "block_card_type": ("合", 0, '{"op":"action_filter","mode":"block_type","target":"enemy","card_type":"thorn","duration":1}',
                        "禁止某牌型并进 action_filter(mode:\"block_type\")："
                        "thorn→attack_blocked、bloom→skill_blocked（取较大值），其余牌型只播报"),
    "force_card_type": ("合", 0, '{"op":"action_filter","mode":"force_type","target":"enemy","card_type":"thorn","duration":1}',
                        "强制只能出某牌型并进 action_filter(mode:\"force_type\")：thorn→attack_only，其余牌型只播报"),
    "nullify_current_card": ("合", 0, '{"op":"action_filter","mode":"negate","target":"enemy","card_type":"thorn"}',
                             "使目标下一张某牌型失效并进 action_filter(mode:\"negate\")："
                             "写的 negate_next 全仓库没有读者（合并前后都是只写标记 + 播报）"),
}

# ---------------------------------------------------------------------------
# Round 40 / 批次 AE-2~4：三个卡专用原子下沉成通用能力 / 数据步骤。
ROUND40_ACTIONS = {
    # ---- AE-2：重构机 ----
    "assembler_effect": ("删", 1, '{"op":"request","type":"card","target":"choice_target",…} + '
                                 '{"op":"move_card","card":{"ref":"selected_card"},"target_zone":"exile"} + '
                                 '{"op":"set_var","name":"assembler_reward","value":{"op":"random_choice","values":[…奖励表…]}} + '
                                 '{"op":"status_op","action":"add","status":"fragment_stacks",…} + '
                                 '{"op":"move_card","mode":"give","card_id":{"op":"get","from":{"op":"var","name":"assembler_reward"},"key":"card"},…} + '
                                 '{"op":"card_prop_change","card":{"ref":"last_created_card"},"property":"swift_value",…} + '
                                 '{"op":"log","message":{"op":"get","from":{"op":"var","name":"assembler_reward"},"key":"log"}}',
                         "重构机的\"选目标手牌→放逐→随机奖励\"整条链路搬进卡数据：一次掷骰"
                         "（random_choice 取奖励表项）存进上下文变量后，造牌/迅捷/碎片/战报都从它取值；"
                         "奖励表本身也留在卡数据（引擎兜底表 DEFAULT_ASSEMBLER_REWARDS 一起删除）"),
    # ---- AE-3：起诉书标记 ----
    "mark_original_card": ("合", 1, '{"op":"card_var_change","card":{"ref":"original_card"},"name":"<标记名>","mode":"set","value":{"op":"source_player"}}',
                           "给\"被响应的那张牌\"打标记并进 card_var_change（写进该牌的 custom_vars）："
                           "标记名/值仍由卡数据给，读取方 _bio_indictment_converts_damage 同步改读 custom_vars，"
                           "\"伤害转护盾\"的结算与战报逐字不变"),
    # ---- AE-4：风 ----
    "discard_hand_by_paid_e": ("合", 1, '{"op":"move_card","mode":"batch","owner":"all_players","source_zone":"hand",'
                                       '"target_zone":"discard","filter":{"max_cost_e":…,"exclude_error":true,'
                                       '"require_selectable":false},"count_as_active_discard":true,"log":"风吹走了{count}张牌"}',
                               "按条件批量弃手牌并进 move_card(mode:\"batch\") 的 source_zone 形态："
                               "filter 复用选牌窗口那张规格表（新增 max_cost_e/min_cost_e/exclude_error），"
                               "owner 支持集合选择器（每人各搬自己的区域），弃牌仍走 _discard_card_and_note "
                               "记账（count_as_active_discard），战报只在真的搬走牌时打印"),
}

# ---------------------------------------------------------------------------
# Round 41 / 批次 AE-5（收尾）：两个"半拆"单点原子 + 长尾未使用 op 的逐个定论。
# ---------------------------------------------------------------------------
ROUND41_ACTIONS = {
    # ---- 一、两个"半拆"原子 ----
    "cogwheel_mark": ("合", 1, '{"op":"player_var_change","mode":"set","name":"cogwheel_active","value":true} + '
                              '{"op":"player_var_change","mode":"set","name":"cogwheel_exclude_instance_id",'
                              '"value":{"op":"card_prop","card":{"ref":"current_card"},"property":"instance_id"}} + '
                              '{"op":"cogwheel_return"}',
                      "齿轮的\"标记\"半边下沉成卡数据写玩家变量（开关 + 要排除的实例 id），"
                      "收牌例程（按 cards_played_this_turn_instance_ids 逐张回收、写 symbiosis 实例标签、"
                      "受手牌上限与 excluded_from_cogwheel_return 标签约束）留成最小原子并改名 "
                      "cogwheel_return——旧名进 RENAMED_ATOMIC_OPS，写出来是\"已改名 + 规范名\""),
    "goggles_enable": ("删", 1, '{"flags":["continuous_deck_reveal"]} + '
                                '{"op":"equipment_op","mode":"place","effect_target":"choice_target"}',
                       "护目镜的\"谁能查看牌堆/弃牌堆顺序\"改由装备标签 continuous_deck_reveal 声明，"
                       "引擎 _goggles_view_targets_for 扫装备 + 读 effect_target（与 garden:antennae 的 "
                       "continuous_hand_reveal 同一套口径）；引擎级 _goggles_views 映射一起删除，"
                       "视图权限跟着装备在场与否走（与卡面\"装备在场时\"一致）"),
    # ---- 二、长尾未使用 op 里判定"删"的四条 ----
    "card_damage_multiply": ("删", 0, '{"op":"card_prop_change","mode":"mul","property":"fusion_level",'
                                      '"multiplier":2,"card":{"ref":"current_card"}}',
                             "聚变倍率就是卡牌属性乘法，走同一张 _set_card_property_value 钳位路径"
                             "（fusion_level 上限、fusion_multiplier 同步字段都在里面）"),
    "countdown_var": ("删", 0, '{"op":"player_var_change","mode":"set","name":"timer","value":3,"target":"self"} + '
                               '{"op":"delayed_effect","mode":"timed","trigger":"target_turn_start","duration":3,'
                               '"target":"self","body":[{"op":"player_var_change","mode":"sub","name":"timer",'
                               '"value":1,"target":"self"}]}',
                      "倒计时 = \"写初值\" + \"每次触发减 1\"两条通用步骤；_register_timed_effect 的定时器"
                      "自 Round 37 起已由 delayed_effect(mode:\"timed\") 承接，原子内部本来就是这两步的封装"),
    "create_counter": ("删", 0, '{"op":"card_var_change","mode":"add","name":"counter1","value":1,'
                                '"card":{"ref":"current_card"}}',
                       "它写的 card.custom_counters 在引擎、卡数据、to_dict 与客户端里都没有读取方"
                       "（写进去没人读）；卡内任意计数改用 card_var_change 写 card.custom_vars"),
    "response_declare": ("删", 0, "",
                         "返回 None 的空占位步骤，没有任何行为；反制窗口由卡数据的 response_trigger "
                         "与引擎响应系统承载（bio:indictment 在 Round 40 起也已改用 card_var_change）"),
}

# ---------------------------------------------------------------------------
# Round 43 / 批次 AG（"能组合就删"续扫）：3 个原子逐个验证后删除。
# 判据、迁移与"迁移前 / 迁移后"对拍见 `.codex-tmp/round43/rd43.md`：
#   * 一条空步骤（实现就是 ``return None``，机制由装备标签承载）；
#   * 一条"写的字段本来就在属性白名单里"的费用修正；
#   * 一条"反弹输入量在响应上下文里，数据侧读得到"的反击。
ROUND43_ACTIONS = {
    "plank_immunity": ("删", 1, '（无等价步骤：直接删掉这一步）',
                       "Round 43 / 批次 AG：实现是 ``return None`` 的空步骤；木板机制由装备标签 "
                       "``blocks_cheap_attacks`` 承载——``_deal_attack_damage`` 每段伤害前读 "
                       "``_equipment_flag_or_legacy_mark(target, \"blocks_cheap_attacks\")``，"
                       "再看攻击牌是不是\"荆棘牌且实际 E 消耗 ≤ 1\"。卡数据里该步已删，"
                       "装备在场即生效（与卡面\"装备在场时\"一致），A/B 与定向探针都逐字节相同"),
    "modify_next_cost": ("删", 1, '{"op":"card_prop_add_to_zone","target":"target","zone":"hand",'
                                  '"property":"temp_heavy_value","amount":1,"require_selectable":false,'
                                  '"silent":true}',
                         "Round 43 / 批次 AG：加费/减费写的 ``temp_heavy_value`` / "
                         "``temp_swift_value`` 本来就在 ``_set_card_property_value`` 的属性白名单里"
                         "（连带 ``temp_heavy`` / ``temp_swift`` 实例标签同步）；批量写区域属性用 "
                         "``card_prop_add_to_zone``，减费换 ``property:\"temp_swift_value\"``，"
                         "旧名 increase_next_cost / reduce_next_cost 的替代写法一起改指这条"),
    "counter_pending_attack_damage": ("删", 1, '{"op":"if_else","condition":{"op":"compare",'
                                               '"a":{"op":"var","name":"first_hit_damage"},"operator":">","b":0},'
                                               '"then":[{"op":"direct_damage","target":"target",'
                                               '"amount":{"op":"ceil","value":{"op":"mul","a":0.6,'
                                               '"b":{"op":"var","name":"first_hit_damage"}}},'
                                               '"damage_type":"physical","source_text":"盐"}]}',
                                      "Round 43 / 批次 AG：反弹的输入量就在响应上下文里——"
                                      "``_run_v2_card_event`` 把 ``extra_context`` 原样并进 "
                                      "``context['vars']``（first_hit_damage / first_damage / "
                                      "incoming_damage_parts 都在里面），所以 ceil(first_hit × ratio) "
                                      "与来源文案都能用取值表达式 + ``direct_damage`` 写出来；"
                                      "唯一差异是反射伤害现在会写引擎级 ``_last_damage_value``"
                                      "（与 deal_damage / direct_damage 全族一致，见报告§差异）"),
}

# Round 42 / 批次 AF（极端收敛，"能组合就删"）：15 个名字删除/退役。
# 判据与 A/B 证据见 `.codex-tmp/round42/rd42.md`：六条只播报（写的字段零读取方）、
# 五条写的字段已有既有写入口（官方包已有同写法）、三条两步通用组合
# （vanilla:triangle / vanilla:fang / vanilla:fusion 的卡数据就是这些写法）、
# 一条伞原子按 mode 拆成既有原子。
ROUND42_ACTIONS = {
    # ---- 一、只播报型：写的字段全仓库零读取方，实际行为 = 一行默认战报 ----
    "transform_card": ("删", 0, '{"op":"log","message":"变换<牌名>效果触发"}',
                       "实现只按 card 引用查牌再播报，不写状态；真变换是 transform_cards"),
    "modify_damage": ("删", 0, '{"op":"log","message":"修改伤害公式：<formula>"}',
                      "formula 零读取方（伤害公式来自步骤本身）；events.modify_damage 是另一条 v2 事件钩子键"),
    "emit_event": ("删", 0, '{"op":"log","message":"广播事件：<事件名>"}',
                   "事件总线无订阅方；silent/log:false 的静默语义由 log 步的 log:false 承接"),
    "global_mult": ("删", 0, '{"op":"log","message":"全场伤害倍率x2"}',
                    "global_damage_mult/global_heal_mult/global_cost_mult 零读取方（含客户端）"),
    "turn_mod_add": ("删", 0, '{"op":"log","message":"每回合能量回复+1"}',
                     "e_regen_mod/m_regen_mod/draw_mod 零读取方（回合结算路径不读这三个字段）"),
    "mark_self_damage_source": ("删", 0, '{"op":"log","message":"<目标>下次伤害来源标记为自身"}',
                                "self_damage_next 只被自己写，没有读取方也不进 to_dict"),
    # ---- 二、写的字段已有既有写入口（官方包已有同写法）----
    "activate_corruption": ("删", 0, '{"op":"equipment_prop_set","equipment":{"ref":"current_equipment"},'
                                     '"property":"corruption_active","value":1}',
                            "同一个 setter 已由 equipment_prop_set 覆盖；vanilla:corruption 的卡数据就这么写"),
    "counter_equip_protect": ("删", 0, '{"op":"player_prop_change","mode":"add","property":"equipment_protection",'
                                      '"target":"self","amount":1}',
                              "equipment_protection 本来就在 player_prop_change 白名单里；"
                              "_status_application_blocked 恒 False、成就峰值不统计该字段"),
    "equip_protection": ("删", 0, '{"op":"player_prop_change","mode":"add","property":"equipment_protection",'
                                  '"target":"self","amount":1}',
                         "counter_equip_protect 的旧别名，与规范名一起退役（_EFFECT_ALIASES 条目同步删除）"),
    "card_counter": ("删", 0, '{"op":"card_prop_change","mode":"add","property":"play_count","amount":1,'
                             '"card":{"ref":"current_card"}}',
                     "play_count/equip_turns 是可读卡牌字段（取值形态 + equip_turns 条件算子），"
                     "补进 card_prop_change 白名单后即普通属性写入；reset = 两条 set 0"),
    "fission": ("删", 0, '{"op":"card_prop_change","mode":"add","property":"fission_level","amount":1,'
                         '"card":{"ref":"selected_card"}}',
                "_set_card_property_value 对 fission_level 有钳位并同步 fission_count；"
                "官方包 arctic:nuke / arctic:ruby 已在用同一写法"),
    # ---- 三、两步通用组合（官方包卡数据就是这些写法）----
    "lifesteal_damage": ("删", 0, '{"op":"deal_damage",…} + 门控 last_damage>0 的 '
                                  '{"op":"health_op","mode":"heal","amount":floor(last_damage×比例)}',
                         "vanilla:fang 的卡数据；_would_heal 同步认 health_op(mode:\"heal\")，"
                         "反治疗响应窗口不退化"),
    "triangle_damage": ("删", 0, '{"op":"deal_damage","amount":add(base, mul(per_stack, var("三角形层数")))} + '
                                 '{"op":"if_else",…,"then":[{"op":"player_var_change","mode":"set",'
                                 '"value":min(上限, 层数+1)}]}',
                        "vanilla:triangle 的卡数据；同一条攻击管线、层数走 custom_vars 并由 "
                        "_sync_custom_var_alias 同步 triangle_stacks"),
    "fusion": ("删", 0, '见 vanilla:fusion 的卡数据（request 选同名手牌 → for_each 累计 max/合计 → '
                        'card_prop_change 写回 → move_card 弃牌）',
               "整套多卡聚变已是卡数据；_merge_fusion_card_layers 保留给引擎硬编码 _effect_* 路径"),
    # ---- 四、伞原子按 mode 拆成既有原子 ----
    "action_filter": ("删", 0, 'block_own → player_prop_change(set shovel_active 1)；'
                               'block_type → player_prop_change(set attack_blocked, value:max(现值, duration))；'
                               'force_type → 同上 attack_only；negate → log',
                      "四个 mode 写的字段都在 player_prop_change 白名单里（官方包 ocean:bubble_bomb / "
                      "sewers:poo / ocean:jelly 已在用）；skill_blocked 与 negate_next 零读取方"),
}

# Round 41 / 批次 AE-5：长尾"未使用 op"逐个定论（判定 + 理由 + 替代写法）。
# Round 42 / 批次 AF：其中 15 个名字改判"删"（能组合/字段零读取方），
# 3 个名字维持"留"并补上"为什么数据做不到"的读取方证据。
# 判定取值：留·语言原语 / 留·机制钩子 / 留·伞原子 / 留·事件钩子 / 留·能力扩展点 /
# 删·可下沉 / 删·能力扩展点。凡判"删"的行都必须已经真删（无 `_atomic_*` 实现、
# 名字进 REMOVED/RENAMED 表）——``--check`` 会验证。
# ---------------------------------------------------------------------------
# Round 44 / 批次 AH：弹射从专用原子改成"目标选择器 + 逐段参数"。
#   * 预抽时机、响应/预知可见的目标集合、每一段的伤害/段数、last_damage
#     全部由引擎的弹射链接管；判定与对拍见 `.codex-tmp/round44/rd44.md`。
#   * 三个历史旧名（bounce_attack / arctic_ricochet_attack / desert_marble_attack）
#     一起从 RENAMED_ATOMIC_OPS 挪进 REMOVED_ATOMIC_OPS：替代写法是一个选择器，
#     不再是一个"规范名"，所以不能只写"已改名 + 规范名"。
ROUND44_ACTIONS = {
    "ricochet_attack": ("删", 2, '{"op":"deal_damage","target":{"selector":"bounce","source":"target",'
                                 '"count":4,"exclude_previous":true,"allow_self":true,'
                                 '"prepare_at_play":true},"amount":6,"hits":1,'
                                 '"inherit_extra_hits":false,"per_target_amount":6,'
                                 '"per_target_hits":1,"precision_inherit":true}',
                        "Round 44 / 批次 AH：弹射链 = ``deal_damage`` 的 ``target`` 写成 ``bounce`` "
                        "选择器（``count`` / ``count_from:\"positive_hits\"`` / ``exclude_previous`` / "
                        "``allow_self`` / ``prepare_at_play``），逐段差异用 ``per_target_amount`` / "
                        "``per_target_hits``；``_prepare_bounce_targets`` 的预抽调用点没动，"
                        "所以响应与预知看到的目标集合、战报与 last_damage 与旧原子逐字节相同"),
    "electric_web_arm": ("删", 2,
                         '[{"op":"player_var_change","mode":"add","target":"target",'
                         '"name":"electric_web_draw_damage","value":2},'
                         '{"op":"equipment_prop_set","property":"electric_web_armed_target",'
                         '"value":{"op":"target_player","target":"target"}},'
                         '{"op":"equipment_prop_add","property":"electric_web_armed_amount",'
                         '"amount":2}]',
                         "Round 44 / 批次 AH（目标二）：三条写入都能用已有通用步骤逐字表达"
                         "（玩家 var 走 player_var_change；装备 custom_vars 是 "
                         "equipment_prop_set / equipment_prop_add 的兜底分支，见 "
                         "game_engine.py _set_equipment_property_value 的 else 与 "
                         "_get_equipment_property_value 的末行）。旗标驱动的 "
                         "electric_web_arm_on_place 仍直接调 _apply_electric_web_arm；"
                         "回合驱动的提前执行判据 _effect_tree_contains_action_status "
                         "改认这条通用步骤（写 electric_web_draw_damage 的那一步），"
                         "布网仍在回合初抽牌之前。对拍 25 例 0 差异"),
}

# Round 45 / 批次 AI：``honey_control``（蜜糖控制）并进 ``turn_control`` 的第四个
# mode ``forced_action``——它改的是同一族"下回合的回合帧"（honey_control_turns +
# 自动行动期间的行为开关），与 end/skip/extra 共用一条 ``_atomic_turn_control``；
# 实现体由 ``_turn_control_forced_action`` 逐字承接旧 ``_atomic_honey_control``。
ROUND45_ACTIONS = {
    "honey_control": ("合", 3,
                      '{"op":"turn_control","mode":"forced_action","target":"target","duration":1}',
                      "Round 45 / 批次 AI：``honey_control`` 并进 ``turn_control(mode:\"forced_action\")``。"
                      "参数面逐字保留：``target``（默认 choice_target）/``duration``（至少 1）/"
                      "``forced_target``（解析成玩家 id 存 sewers_cheese_forced_target）/"
                      "``attack_only``（false 写 honey_control_any_card）/``attacks_only``/"
                      "``end_turn_when_stuck``（false 写 honey_control_keep_turn）/``damage_multiplier``/"
                      "``log``；默认文案、``log:false`` 回落与 ``_format_step_log`` 口径不变。"
                      "三张在用卡（garden:honey / garden:beeswax / sewers:cheese）已迁移，"
                      "27 例定向对拍（1v1+2v2）与 704 条全卡 A/B 都是 0 差异"),
}

# Round 46 / 批次 AJ：通用选择器 ``zone_card`` 落地——"按属性取极值的区域选牌"
# 不再是能力缺口，卡专用原子 ``grant_temp_swift_highest_e`` 随之删除。它的三步
# 判定（可选中池 / E 最大且平手取第一张 / 写值同时同步 temp_swift 标签）全部由
# 现有通用步骤 + 新选择器逐字表达；判定与对拍见 `.codex-tmp/round46/rd46.md`。
ROUND46_ACTIONS = {
    "grant_temp_swift_highest_e": (
        "删", 1,
        '[{"op":"card_prop_change","mode":"add","property":"temp_swift_value","amount":3,'
        '"card":{"selector":"zone_card","zone":"hand","owner":"self",'
        '"filter":{"require_selectable":true},'
        '"pick":{"by":"cost_e","mode":"max","tie":"first"},"as":"temp_swift_card"},'
        '"log":"{target}的一张手牌获得暂时迅捷:{amount}"},'
        '{"op":"tag_op","mode":"add","tag":"temp_swift",'
        '"card":{"ref":"temp_swift_card"},"silent":true}]',
        "Round 46 / 批次 AJ：选择器 ``zone_card`` 把 43 轮记下的能力缺口补上——"
        "``filter`` 复用取牌窗口那张规格表（``require_selectable`` 就是旧实现的 "
        "``_card_selectable_by_action`` 池），``pick.by cost_e`` + ``mode max`` + "
        "``tie first`` 就是「取 E 最大、平手取第一张」，``temp_swift_value`` 的写入口"
        "自带 instance_flags.add + disabled_flags.discard（``tag_op`` 那一步把同一件事写明），"
        "``log`` 由 ``card_prop_change`` 渲染 ``{target}``/``{amount}``，挑不到牌时两条写法都不播报；"
        "唯一的在用卡 jungle:magic_rubber 已迁移，定向对拍与 704 条全卡 A/B 都是 0 差异"),
}

# Round 47 / 批次 AK：伤害管线里的两条"响应窗口"原子变数据参数——``on_event``
# 的 ``response`` 分支（``absorb`` / ``reflect``）。窗口该有的引擎语义（伤害落地前
# 消费登记项、付费确认窗口、按实际伤害比例反弹）留在管线里，比例/花费/门控/文案
# 全下沉到步骤参数；判定与对拍见 `.codex-tmp/round47/rd47.md`。
ROUND47_ACTIONS = {
    "absorb_attack_damage": (
        "删", 1,
        '{"op":"on_event","response":"absorb","scope":"responded_card","target":"self",'
        '"once":true,"log":"{source}的铜棒将吸收本次攻击牌伤害","body":[…原 body 步骤原样抄进…]}',
        "Round 47 / 批次 AK：登记式吸收改由 ``on_event(response:\"absorb\")`` 声明——"
        "同一张 ``custom_vars['absorb_attack_damage_events']`` 登记表、同一个 "
        "``_consume_absorb_attack_damage``（在 ``deal_attack_damage`` 里、**伤害落地前**）"
        "消费，``body`` 仍拿 ``absorbed_damage`` / ``absorb_attacker``；"
        "``scope`` / ``once`` / ``duration`` / ``condition`` / ``log`` 参数一个不少。"
        "唯一在用卡 void:copper_rod（避雷针）已迁移，10 例定向对拍与 704 条全卡 A/B 都是 0 差异"),
    "magic_salt_reflect": (
        "删", 1,
        '{"op":"on_event","response":"reflect","damage_kind":"attack","damage_type":"physical",'
        '"ratio":0.5,"cost_m":1,"title":"魔法盐",'
        '"message":"是否支付{cost_m}M，对{attacker}反弹{reflect}D？","ok_text":"支付并反伤",'
        '"cancel_text":"不触发","source_text":"魔法盐反伤",'
        '"log":"{owner}消耗{cost_m}M，魔法盐对{attacker}反弹{amount}D"}',
        "Round 47 / 批次 AK：受伤时的付费反弹窗口改由 ``on_event(response:\"reflect\")`` 声明——"
        "原来写死在这条原子里的比例、魔力花费、物理攻击门控与四段文案，现在是步骤参数"
        "（``damage_kind``/``damage_type`` 留空 = 不限）；窗口仍用 ``choice_type`` "
        "``magic_salt_reflect``（客户端 ``showMagicSaltReflectResponseUI`` 的既有契约，未改 "
        "``static/``），确认后的扣费与直伤管线结算仍在 ``resolve_choice`` 里。"
        "唯一在用卡 desert_cards_addition:magic_salt 已迁移，10 例定向对拍与 704 条全卡 A/B 都是 0 差异"),
}

# Round 48 / 批次 AL：``list_modify`` 并进 ``player_var_change(mode:"set")`` +
# ``collection_op``——``mode:"set"`` 现在也写列表（逐项 ``_serializable_list_item``），
# 五个历史 mode 的替代写法见 ``mod_spec_v2.RENAMED_ATOMIC_OPS``。
# 判定与对拍（bio:job_application，6 例 1v1+2v2）见 `.codex-tmp/round48/rd48.md`。
ROUND48_ACTIONS = {
    "list_modify": (
        "删", 1,
        '{"op":"player_var_change","mode":"set","name":"L","value":'
        '{"op":"collection_op","mode":"concat",'
        '"source":{"op":"player_var","target":"target","name":"L","default":[]},'
        '"values":[<新元素>]}}',
        "Round 48 / 批次 AL：列表写值不再需要专用原子——``player_var_change(mode:\"set\")`` "
        "现在也写列表（列表值逐项走 ``_serializable_list_item``，与 ``list_modify(mode:\"set\")`` "
        "同一口径），拼接/截取由 ``collection_op`` 的 concat 与 slice 组合；"
        "``set`` 直接写整张列表、``clear`` 写 ``[]``、``insert``/``delete`` 用前后两段 slice 包住。"
        "卡数据里 0 处旧写法传列表给 ``player_var_change``（纯加法），唯一在用卡 "
        "bio:job_application 的 6 例定向对拍 0 差异"),
}

# Round 49 / 批次 AM：两条"逐张处理整片区域"的原子下沉 —— 集合来源
# （``for_each`` 的 ``zone_cards``）与两个取值表达式补完后，公式完全落在数据侧。
# 判定与对拍（铜棒 8 例 / 量子 4 例）见 `.codex-tmp/round49/rd49.md`。
ROUND49_ACTIONS = {
    "add_charge_to_hand": (
        "删", 1,
        '{"op":"for_each","as":"charge_hand_card",'
        '"source":{"selector":"zone_cards","zone":"hand","owner":"self",'
        '"filter":{"require_selectable":false}},'
        '"body":[{"op":"card_prop_change","mode":"add","property":"charge_value",'
        '"amount":{"op":"div","values":[<absorbed_damage>,<手牌数>],"round":"ceil"},'
        '"card":{"ref":"charge_hand_card"},"log":false,"run_if":<amount>0>}]} + '
        '{"op":"log","target":"self","total":<absorbed_damage>,"amount":<同一个 amount>,'
        '"message":"{target}的铜棒吸收了{total}点伤害，使每张手牌获得{amount}层电荷"}',
        "Round 49 / 批次 AM：``for_each`` 认集合来源后，\"总量摊到每张手牌\"不再需要"
        "专用原子——``div`` 的新参数 ``round:\"ceil\"`` 给出向上取整的摊分，"
        "``card_prop_change(property:\"charge_value\")`` 的写入口自带 charge 标签同步，"
        "``run_if`` 挡住 amount=0（旧实现在 0 层时什么都不写，写 0 会把标签标成禁用），"
        "战报用一条 ``log`` 补上（``log`` 新增 ``total`` 字段与运行时同一套占位符渲染）。"
        "唯一在用卡 void:copper_rod 的 8 例定向对拍（手牌 0/1/2/3/5、预置电荷、sublime、1v1+2v2）0 差异"),
    "set_card_prop_random": (
        "删", 1,
        '{"op":"for_each","as":"quantum_card",'
        '"source":{"selector":"zone_cards","zone":"hand","owner":{"op":"equipment_target"},'
        '"filter":{"require_selectable":false,"max_base_cost_e":3}},'
        '"body":[{"op":"card_prop_change","mode":"set","property":"cost_e_override",'
        '"value":{"op":"random","min":1,"max":3},"card":{"ref":"quantum_card"},"log":false}]}',
        "Round 49 / 批次 AM：区域过滤走共享规格表的 ``max_base_cost_e``（与旧 ``max_base`` "
        "同一段实现），逐张写随机值改由 ``random`` 取值表达式承担（每次迭代求值，"
        "随机数消耗顺序与旧 ``random.randint`` 相同）；``require_selectable:false`` 对齐"
        "旧实现\"不筛可选中性\"。唯一在用卡 void:quantum 的 4 例定向对拍（含 2v2、空手牌、"
        "高价牌过滤）0 差异"),
}

# Round 50 / 批次 AN：Round 33 的 ``auto_play`` 伞缺的最后一块——
# ``queue_auto_play`` 当时因为"官方包步骤形状被测试断言"而留了实现体，
# 这一批把三处卡数据（pearl / magic_pearl / sapphire）迁到
# ``auto_play(mode:"queue")`` 并同步那两处测试断言，实现体删除。
ROUND50_ACTIONS = {
    "queue_auto_play": (
        "合", 3,
        '{"op":"auto_play","mode":"queue","card":{"ref":"current_card"},"source":"snapshot",'
        '"target":"target","each_turn":true,"cost":"normal","exile":true}',
        "Round 50 / 批次 AN：队列自动打出就是 ``auto_play(mode:\"queue\")`` "
        "（``_atomic_auto_play`` 的 queue 分支本来就是旧实现体），参数一个不动；"
        "旧名进 RENAMED_ATOMIC_OPS，三条声明旧称（auto_play_queue_add / "
        "queue_auto_play_card / ocean_mark_auto_play）一并改指伞写法。"
        "顺手修好了两处因它而烂掉的测试数据（tests/test_allcards_balance_14.py 的"
        "步骤断言、tests/test_ocean_sapphire_playability.py 的镜像步骤）"),
}

UNUSED_OP_VERDICTS = {
    # ---- 语言原语：数据 DSL 的骨架，删了写不了卡 ----
    "break": ("留·语言原语", "`{\"op\":\"break\"}`（循环体内）",
              "循环跳出原语，Round 32 起明确保留（for_each/repeat 的唯一出口）"),
    "continue": ("留·语言原语", "`{\"op\":\"continue\"}`（循环体内）",
                 "跳过本次迭代的原语，与 break 成对；引擎按 ModLoopContinue 处理"),
    # Round 49 / 批次 AM：``random`` 现在有真实用例（void:quantum 的逐张随机
    # 写值走取值表达式分支），所以不再属于"0 引用"定论表；它同时还是
    # ``_atomic_random``（50/50 分支步骤）与随机目标选择器的底层原语。
    "clamp": ("留·语言原语", "`{\"op\":\"clamp\",\"value\":…,\"min\":…,\"max\":…}`",
              "取值表达式算子（eval_v2_value 分支），写卡时的通用钳位"),
    "const": ("留·语言原语", "`{\"op\":\"const\",\"value\":…}`",
              "取值表达式算子：常量包装，编辑器生成的表达式节点"),
    "literal": ("留·语言原语", "`{\"op\":\"literal\",\"value\":…}`",
                "const 的同义算子（同一个分支），旧数据兼容名"),
    "has_status": ("留·语言原语", "`{\"op\":\"has_status\",\"target\":…,\"status\":…}`（condition 位）",
                   "条件算子：判断某状态层数，只能出现在 condition/run_if/unless"),
    "var_compare": ("留·语言原语", "`{\"op\":\"var_compare\",\"left\":…,\"op\":\">\",\"right\":…}`",
                    "条件算子：变量比较，与 compare 同族"),
    "zone_exists": ("留·语言原语", "`{\"op\":\"zone_exists\",\"target\":…,\"zone\":\"deck\"}`",
                    "条件算子：区域非空判断"),
    "equipment_property": ("留·语言原语", "`{\"op\":\"equipment_property\",\"property\":…}`",
                           "取值表达式算子：读装备属性（装备属性族唯一读法）"),
    "equipment_count_targeting": ("留·语言原语", "`{\"op\":\"equipment_count_targeting\",\"equipment_id\":…}`",
                                  "取值表达式算子：统计指向某玩家的装备数"),
    # ---- 运行时步骤与事件钩子 ----
    "modify_event_value": ("留·伞原子", "`{\"op\":\"modify_event_value\",\"value\":…}`",
                           "run_v2_step 原生步骤：改写当前事件的 event_value（事件响应族唯一写入口）"),
    "deck_catalog_pick_resume": ("留·机制钩子", "`{\"op\":\"deck_catalog_pick_resume\"}`",
                                 "Cicada 3301 图鉴选牌的续跑步骤（run_v2_step 原生，与 deck_catalog_pick 成对）"),
    "damage": ("留·事件钩子", "`{\"op\":\"deal_damage\",…}`（旧写法 `damage` 走 _EFFECT_ALIASES）",
               "伤害管线的旧写法入口，_EFFECT_ALIASES 直接指到 deal_damage，不是独立实现"),
    "equip_protection": ("删·可下沉", "`{\"op\":\"player_prop_change\",\"mode\":\"add\",\"property\":\"equipment_protection\",\"amount\":N}`",
                         "Round 42 / 批次 AF：别名与 ``counter_equip_protect`` 一起退役——"
                         "装备保护层数就是玩家属性 ``equipment_protection``，"
                         "``player_prop_change`` 的属性白名单里本来就有它（写出来是显式报错）"),
    "on_any_turn_start": ("留·事件钩子", "`events.{\"on_any_turn_start\":{…}}`",
                          "事件时点声明键：任意玩家回合开始（被动钩子表成员）"),
    "on_damage_taken": ("留·事件钩子", "`events.{\"on_damage_taken\":{…}}`",
                        "事件时点声明键：受到伤害时（血债等监听器的唯一入口）"),
    "on_discard_owner_turn_start": ("留·事件钩子", "`events.{\"on_discard_owner_turn_start\":{…}}`",
                                    "事件时点声明键：在弃牌堆且拥有者回合开始"),
    "on_enemy_turn_start": ("留·事件钩子", "`events.{\"on_enemy_turn_start\":{…}}`",
                            "事件时点声明键：敌方回合开始"),
    "on_equipment_destroy": ("留·事件钩子", "`events.{\"on_equipment_destroy\":{…}}`",
                             "事件时点声明键：装备被摧毁"),
    "on_equipment_trigger": ("留·事件钩子", "`events.{\"on_equipment_trigger\":{…}}` / on_event(trigger:\"equipment_trigger\")",
                             "事件时点声明键：装备触发（引擎 _equipment_trigger_* 系列直读）"),
    "on_hand_owner_turn_end": ("留·事件钩子", "`events.{\"on_hand_owner_turn_end\":{…}}`",
                               "事件时点声明键：在手牌且拥有者回合结束"),
    "on_hand_owner_turn_start": ("留·事件钩子", "`events.{\"on_hand_owner_turn_start\":{…}}`",
                                 "事件时点声明键：在手牌且拥有者回合开始"),
    "on_owner_turn_end": ("留·事件钩子", "`events.{\"on_owner_turn_end\":{…}}`",
                          "事件时点声明键：拥有者回合结束"),
    "on_owner_turn_start": ("留·事件钩子", "`events.{\"on_owner_turn_start\":{…}}`",
                            "事件时点声明键：拥有者回合开始（挂起类卡牌的主入口）"),
    "on_target_turn_start": ("留·事件钩子", "`events.{\"on_target_turn_start\":{…}}`",
                             "事件时点声明键：被指向目标的回合开始（计时器默认相位）"),
    # ---- Round 47 / 批次 AK：新的通用能力 ----
    # （``collection_op`` 已经在用——bio:job_application 的列表追加——所以不在这张
    #  "0 引用"定论表里；``pick`` 还没有卡在用，按"能力扩展点"登记。）
    "pick": ("留·能力扩展点",
             "`{\"op\":\"pick\",\"source\":…,\"as\":\"chosen\",\"count\":1,\"pick\":{…}}`",
             "Round 47 / 批次 AK：自动挑条目并绑定进 ``vars[as]``（不弹窗）——来源/过滤与 "
             "``collection_op`` 共用一套读法，``pick`` 的属性极值口径与 ``zone_card`` 一致。"
             "实现在 ``GameEngine._atomic_pick`` → ``mod_runtime_v2.run_pick_step``。"
             "不叫 ``select``：那是卡数据 UI 组件的 ``type``，同名会被任意位置计数误算"),
    # ---- 伞原子与机制钩子：卡面机制的唯一实现，删掉要重写实现才能加回来 ----
    "action_filter": ("删·可下沉", "`{\"op\":\"player_prop_change\",\"mode\":\"set\",\"property\":\"attack_blocked\","
                                   "\"target\":\"enemy\",\"value\":{\"op\":\"max\",\"a\":{\"op\":\"player_property\","
                                   "\"property\":\"attack_blocked\",\"target\":\"enemy\"},\"b\":1}}`",
                      "Round 42 / 批次 AF：四个 mode 写的都是玩家属性/AI 守卫字段——"
                      "block_own → shovel_active、block_type → attack_blocked、force_type → attack_only "
                      "全在 ``player_prop_change`` 白名单里（官方包 ocean:bubble_bomb / sewers:poo / "
                      "ocean:jelly 已在用同样的写法）；``negate`` 写的 negate_next 零读取方，替代写法为 log；"
                      "``skill_blocked`` 既无读取方也不进 to_dict"),
    "emit_event": ("删·可下沉", "`{\"op\":\"log\",\"message\":\"广播事件：<事件名>\"}`",
                   "Round 42 / 批次 AF：事件总线没有订阅方（``_run_v2_event_hooks`` 是另一套 v2 钩子表），"
                   "这一步的实际行为就是按 silent/log:false 播报一行；旧名 broadcast_event / "
                   "trigger_manual 在 REMOVED_ATOMIC_OPS 里同步改指 log"),
    "activate_corruption": ("删·可下沉", "`{\"op\":\"equipment_prop_set\",\"equipment\":{\"ref\":\"current_equipment\"},"
                                        "\"property\":\"corruption_active\",\"value\":1}`",
                            "Round 42 / 批次 AF：它只是调用同一个 setter（``_set_equipment_property_value`` 的 "
                            "corruption_active 分支），而这条 op 就是 ``equipment_prop_set``；"
                            "官方包 vanilla:corruption 的卡数据已在用同一写法"),
    "card_counter": ("删·可下沉", "`{\"op\":\"card_prop_change\",\"mode\":\"add\",\"property\":\"play_count\","
                                 "\"amount\":1,\"card\":{\"ref\":\"current_card\"}}`",
                     "Round 42 / 批次 AF：play_count / equip_turns 是可读的卡牌字段（``{\"ref\":\"equip_turns\"}`` "
                     "取值与 ``equip_turns`` 条件算子），把它们补进 ``card_prop_change`` 的属性白名单后就是普通"
                     "属性写入；reset = 两条 ``mode:\"set\" value:0``"),
    "charge_self_damage": ("留·机制钩子", "`{\"op\":\"charge_self_damage\"}`",
                           "Round 42 复核、Round 43 再核（含反证）：**不是卡数据步骤，而是引擎在出牌结算"
                           "内部自己调的钩子**——"
                           "``_play_card``（game_engine.py:8154/9096）、响应牌结算（:8486）与 2v2 "
                           "（game_engine_2v2.py:868/1542）都直接调用它，读卡属性 charge_value 并用 "
                           "_once_per_play 的 ocean_charge 标记记账。Round 45 / 批次 AI 的实测反证（"
                           "`.codex-tmp/round45/rd45_probe.py`，1v1+2v2）：带电荷的荆棘牌被**真反制**"
                           "（``on_response.resolution.negate_responded``，所响应牌整段不结算）时，"
                           "被响应卡伤害 0、但引擎钩子仍先扣了 3 点电荷自伤；把同样效果写成数据步骤"
                           "（``on_play`` 里的 ``direct_damage(target:self, amount:3)``）被同一张反制牌"
                           "结算时自伤是 **0**。另外给一张自身没有电荷数据步骤的牌（Honey）实例写 "
                           "``charge_value=3``，打出时照样自伤——机制跟的是**卡实例属性**（任何牌都可能被"
                           "打火机/电容类效果充能），per-card 的数据步骤覆盖不到。按管线型保留"),
    "counter_equip_protect": ("删·可下沉", "`{\"op\":\"player_prop_change\",\"mode\":\"add\","
                                          "\"property\":\"equipment_protection\",\"target\":\"self\",\"amount\":1}`",
                              "Round 42 / 批次 AF：写的字段 equipment_protection 本来就在 "
                              "``player_prop_change`` 的属性白名单里；实现里的 "
                              "``_status_application_blocked`` 恒返回 False、``_note_achievement_status_peak`` "
                              "也不统计该字段，所以合并前后行为一致"),
    "discard_choice_then_draw": ("留·机制钩子", "`{\"op\":\"discard_choice_then_draw\",\"log\":…}`",
                                 "Round 42 复核后保留：默认播报是卡面 ``events.on_play_summary`` 生成的整句"
                                 "（数据步骤读不到该声明）、抽牌走 ``ps.draw_cards`` 而不触发 ``draw`` 的钩子与"
                                 "播报、窗口类型由 ``_choice_type_for_effect`` 按 op 名映射——数据层要等价得先"
                                 "把这些口径都搬出来（本批未做）"),
    "fission": ("删·可下沉", "`{\"op\":\"card_prop_change\",\"mode\":\"add\",\"property\":\"fission_level\","
                            "\"amount\":1,\"card\":{\"ref\":\"selected_card\"}}`",
                "Round 42 / 批次 AF：裂变层数是卡牌属性——``_set_card_property_value`` 对 fission_level 有 "
                "clamp_card_layer 钳位并同步 fission_count，与旧实现逐字一致；官方包 arctic:nuke / "
                "arctic:ruby 已在用 ``card_prop_change(property:\"fission_level\")``"),
    "fusion": ("删·可下沉", "见官方包 ``vanilla:fusion`` 的卡数据（request 选同名手牌 → for_each 累计 "
                            "__聚变层数合计 / __裂变层数最大值 → card_prop_change 写回 → move_card 弃牌）",
               "Round 42 / 批次 AF：整套多卡聚变已经是 ``vanilla:fusion`` 的卡数据步骤（跨卡聚合用 "
               "``for_each`` + 玩家变量累计实现），旧原子的 count/max_count/fusion_uses_two_cards "
               "就是这些步骤的参数；私有助手 _merge_fusion_card_layers 保留给引擎的硬编码 _effect_* 路径"),
    "global_mult": ("删·可下沉", "`{\"op\":\"log\",\"message\":\"全场伤害倍率x2\"}`",
                    "Round 42 / 批次 AF：它写的 global_damage_mult / global_heal_mult / global_cost_mult "
                    "在引擎、卡数据、序列化与客户端里零读取方，实际行为只有那行播报"),
    "lifesteal_damage": ("删·可下沉", "`{\"op\":\"deal_damage\",…}` + 门控在 last_damage>0 的 "
                                     "`{\"op\":\"health_op\",\"mode\":\"heal\",\"amount\":floor(last_damage×比例)}`",
                         "Round 42 / 批次 AF：与 deal_damage 共用同一条攻击管线（_modified_attack_damage + "
                         "deal_attack_damage + 精准继承 + _last_damage_value），官方包 vanilla:fang 的卡数据"
                         "就是这么写的；_would_heal 同步认 health_op(mode:\"heal\")，反治疗判定不退化"),
    "mark_self_damage_source": ("删·可下沉", "`{\"op\":\"log\",\"message\":\"<目标>下次伤害来源标记为自身\"}`",
                                "Round 42 / 批次 AF：它写的 players[i].self_damage_next 全仓库只有一个写入点"
                                "（就是它自己），没有读取方也不进 to_dict"),
    "modify_damage": ("删·可下沉", "`{\"op\":\"log\",\"message\":\"修改伤害公式：<formula>\"}`",
                      "Round 42 / 批次 AF：``formula`` 全仓库零读取方（伤害公式来自步骤本身），"
                      "这一步只有播报；注意 events.modify_damage 是另一条 v2 事件钩子键，不受影响"),
    "multiply_next_damage": ("留·机制钩子", "`{\"op\":\"multiply_next_damage\",\"multiplier\":2}`",
                             "Round 43 复核、Round 45 / 批次 AI 再核（含“现有原子组合不出等价”的实测）：写的 "
                             "``players[i].damage_multiplier`` 是**乘算**累加（``current * multiplier``），"
                             "被攻击管线读取（game_engine.py:2329 / game_engine_2v2.py:2293）并在结算后复位"
                             "（:16833 / 2v2:2296）。Round 45 实测（`.codex-tmp/round45/rd45_probe.py`）："
                             "旧原子 ×2 后基本攻击 8 → **16**，两次 ×2 → **32**（1.0 → 2.0 → 4.0 → 结算后回 1.0）；"
                             "``player_prop_change(mode:\"set\"/\"add\", property:\"damage_multiplier\")` 写不进"
                             "（白名单外，返回 None，字段仍是 1.0，伤害仍是 8）；"
                             "``player_var_change(mode:\"set\", name:\"damage_multiplier\")` 只写 custom_vars，"
                             "伤害管线不读它（伤害仍是 8），``mode:\"mul\"`` 更会按“缺键从 0 起算”写成 0——"
                             "即“两次 ×2 叠加 = ×4”这种浮点乘算语义用现有原子表达不出来"),
    "transform_card": ("删·可下沉", "`{\"op\":\"log\",\"message\":\"变换<牌名>效果触发\"}`",
                       "Round 42 / 批次 AF：实现只按 card 引用查一张牌再播报，不写任何状态；"
                       "真正的变换是 ``transform_cards``（1 处卡数据在用）"),
    "triangle_damage": ("删·可下沉", "`{\"op\":\"deal_damage\",\"amount\":add(base, mul(per_stack, var(\"三角形层数\")))}` + "
                                    "门控 ``last_damage>0`` 的 ``player_var_change(mode:\"set\", value:min(上限, 层数+1))``",
                        "Round 42 / 批次 AF：官方包 vanilla:triangle 的卡数据就是这两步（伤害与 deal_damage "
                        "同管线；层数读 var 写 custom_vars 并由 _sync_custom_var_alias 同步 triangle_stacks；"
                        "状态免疫期间 var 读取自动返回 0）"),
    "turn_mod_add": ("删·可下沉", "`{\"op\":\"log\",\"message\":\"每回合能量回复+1\"}`",
                     "Round 42 / 批次 AF：它写的 e_regen_mod / m_regen_mod / draw_mod 全仓库零读取方"
                     "（引擎里没有读取这三个字段的回合结算路径），实际行为只有那行播报"),
    # ---- 本批真删的 6 个名字（判定 + 替代写法见上表，这里逐条留档） ----
    "cogwheel_mark": ("删·可下沉", "见上表：两条 `player_var_change` + 最小原子 `cogwheel_return`",
                      "半拆：标志位下沉成数据，收牌例程留成最小原子并改名（旧名进 RENAMED_ATOMIC_OPS）"),
    "goggles_enable": ("删·可下沉", "装备标签 `continuous_deck_reveal`（引擎扫装备读 effect_target）",
                       "视图权限改由数据声明，引擎级 _goggles_views 映射删除"),
    "card_damage_multiply": ("删·可下沉", "`{\"op\":\"card_prop_change\",\"mode\":\"mul\",\"property\":\"fusion_level\",…}`",
                             "同形卡牌属性乘法，走同一张钳位/同步字段路径"),
    "countdown_var": ("删·可下沉", "`player_var_change(mode:\"set\")` + `delayed_effect(mode:\"timed\")`",
                      "原子内部本来就是这两步的封装"),
    "create_counter": ("删·能力扩展点", "`{\"op\":\"card_var_change\",\"mode\":\"add\",\"name\":…,\"card\":…}`",
                       "card.custom_counters 全仓库没有任何读取方（写进去没人读），改用 card.custom_vars"),
    "response_declare": ("删·能力扩展点", "（无等价写法：反制窗口由卡数据 response_trigger 声明）",
                         "返回 None 的空占位步骤，删除不影响任何现有卡"),
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
    # Round 48 / 批次 AL：list_modify 本身也已删除，这五条替代写法同步改指
    # player_var_change + collection_op（见 mod_spec_v2.RENAMED_ATOMIC_OPS）。
    "list_set": ("合", 0, '{"op":"player_var_change","mode":"set","name":"<变量名>","value":[...]}'
                          '（Round 48 起 mode:"set" 也写列表）',
                 "列表五兄弟并成 list_modify（Round 32）；Round 48 list_modify 再并进 "
                 "player_var_change + collection_op"),
    "list_append": ("合", 1, '{"op":"player_var_change","mode":"set","name":"L","value":'
                             '{"op":"collection_op","mode":"concat",'
                             '"source":{"op":"player_var","name":"L","default":[]},"values":[<元素>]}}',
                    "同上；非列表旧值按单元素处理的旧行为保留（collection_op 的 concat 认单值）"),
    "list_insert": ("合", 0, '{"op":"player_var_change","mode":"set","name":"L","value":'
                             '{"op":"collection_op","mode":"concat","values":[slice(0,下标-1),[元素],slice(下标-1)]}}',
                    "同上；insert 下标仍夹在 [0, len]（slice 越界天然截断）"),
    "list_delete": ("合", 0, '{"op":"player_var_change","mode":"set","name":"L","value":'
                             '{"op":"collection_op","mode":"concat","values":[slice(0,下标-1),slice(下标)]}}',
                    "同上；越界删除仍是空操作"),
    "list_clear": ("合", 0, '{"op":"player_var_change","mode":"set","name":"L","value":[]}',
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
    "increase_next_cost": ("合", 1, '{"op":"card_prop_add_to_zone","target":...,"zone":"hand",'
                                    '"property":"temp_heavy_value","amount":N,'
                                    '"require_selectable":false,"silent":true}',
                           "费用族先并成 modify_next_cost（delta 正负定方向），Round 43 又把它"
                           "下沉成区域属性写入——temp_heavy_value / temp_swift_value 本来就在"
                           "属性白名单里（含实例标签同步）"),
    "reduce_next_cost": ("合", 0, '{"op":"card_prop_add_to_zone","target":...,"zone":"hand",'
                                  '"property":"temp_swift_value","amount":N,'
                                  '"require_selectable":false,"silent":true}',
                         "同上；减费 = temp_swift_value（Round 43 把 modify_next_cost 也删了）"),
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
    "delayed_effect": "Round 37 延迟族唯一公开 op（mode=timed|blind|reveal_hand；共用计时表 duration/trigger/body）",
    "on_event": "Round 37 监听族唯一公开 op（trigger=play|this_play|after_all|equipment_trigger；承接 once_per_play / register_play_listener / after_all / magic_relic_trigger）",
    "emit_event": "Round 37 广播族唯一公开 op（event + 可选 log/silent；承接 broadcast_event 与占位步骤 trigger_manual）",
    "turn_control": "Round 38 回合控制族唯一公开 op（mode=end|skip|extra；承接 force_end_turn / skip_turn / extra_turn）；"
                    "Round 45 / 批次 AI 起再收 honey_control（mode=forced_action，蜜糖控制：目标下回合被自动控制）",
    "action_filter": "Round 38 行为过滤族唯一公开 op（mode=block_own|block_type|force_type|negate；承接 block_own_actions / block_action / block_card_type / force_card_type / nullify_current_card）",
    "countdown_var": "倒计时变量（player_var_change 的定时封装）",
    # Round 50 / 批次 AN：queue_auto_play 已并进 auto_play(mode:"queue")。
    "auto_play_card": "立刻自动打出（含 no_cost/auto_choice）",
    "auto_play_zone_top": "自动打出某区顶牌（Kitty 类）",
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
    "snapshot_card_props": "牌属性快照（按实例存）",
    "restore_card_props": "恢复牌属性快照",
    "restore_match_start_stats": "恢复开局属性",
    "restore_turn_start_stats": "恢复回合开始属性",
    # Round 49 / 批次 AM：set_card_prop_random 已删除（for_each(zone_cards) +
    # card_prop_change(mode:"set", value:random)）。
    # Round 48 / 批次 AL：list_modify 已删除（列表写值 = player_var_change(set) + collection_op）。
    "charge_self_damage": "充能自身伤害",
    # Round 47 / 批次 AK：absorb_attack_damage / magic_salt_reflect 已删除——
    # 两条响应窗口现在是 ``on_event(response:"absorb"|"reflect", …)`` 的数据参数
    # （判定与对拍见 ROUND47_ACTIONS 与 .codex-tmp/round47/rd47.md）。
    "lifesteal_damage": "吸血伤害",
    "triangle_damage": "三角伤害（层数 x 基数）",
    "card_damage_multiply": "聚变倍率（fusion_level x N）",
    "activate_corruption": "激活装备腐化",
    "response_declare": "声明响应（占位步骤，无实现体）",
    "declare_forced_target": "声明强制目标窗口（Light Bulb）",
    # Round 49 / 批次 AM：add_charge_to_hand 已删除（for_each(zone_cards) +
    # ceil(div(total, 手牌数)) + card_prop_change(charge_value) + log）。
    "apply_turn_regen": "回合回复（Jungle）",
    "cogwheel_mark": "齿轮标记（Factory）",
    "crit_multiplier_add": "Round 43 复核留：写 custom_vars 的 hel_crit_multiplier_turn_bonus 后还要调 "
                           "_hel_sync_crit_multiplier_display 刷新显示变量（值 == 2.0 时删除该键），"
                           "数据侧写不出“舍入到 2 位 + 条件删除”这段同步",
    "delayed_blind_next_turn": "下回合延迟失明（Ocean）",
    "delayed_reveal_hand_next_turn": "下回合延迟展示手牌",
    "goggles_enable": "护目镜启用（Factory）",
    # Round 47 / 批次 AK：见上面 absorb_attack_damage 的说明。
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


def any_position_usage() -> dict:
    """与 ``tools/op_long_tail_report.py`` 同口径：``op`` / ``type`` / ``ref`` 三键全位置计数。"""

    counter: collections.Counter = collections.Counter()
    for package in sorted(MODS_DIR.glob("*.gtnmod")):
        with zipfile.ZipFile(package) as archive:
            payload = json.loads(archive.read("mod.json"))
        text = json.dumps(payload, ensure_ascii=False)
        for name in set(mod_spec_v2.VALID_LOGIC_OPS):
            counter[name] += len(
                re.findall(r'"(?:op|type|ref)"\s*:\s*"%s"' % re.escape(name), text)
            )
    return counter


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
        {**ROUND31_ACTIONS, **ROUND32_ACTIONS, **ROUND33_ACTIONS, **ROUND35_ACTIONS,
         **ROUND36_ACTIONS, **ROUND37_ACTIONS, **ROUND38_ACTIONS, **ROUND40_ACTIONS,
        **ROUND41_ACTIONS, **ROUND42_ACTIONS, **ROUND43_ACTIONS,
        **ROUND44_ACTIONS, **ROUND45_ACTIONS, **ROUND46_ACTIONS,
         **ROUND47_ACTIONS, **ROUND48_ACTIONS, **ROUND49_ACTIONS,
         **ROUND50_ACTIONS}
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
    any_usage = any_position_usage()
    unused_ops = []
    for name, (verdict, replacement, reason) in sorted(UNUSED_OP_VERDICTS.items()):
        unused_ops.append({
            "name": name,
            "verdict": verdict,
            "usage": any_usage.get(name, 0),
            "has_impl": name in set(atoms),
            "replacement": replacement,
            "reason": reason,
        })
    return {
        "atoms": atoms, "usage": usage, "kept": kept, "actions": actions,
        "handler_kept": handler_kept, "unused_ops": unused_ops,
        "any_usage": dict(any_usage),
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
    lines.append("# 原子全量清单（Round 33 → 41 / 批次 AB+AC+AD+AE · 2026-09-13）")
    lines.append("")
    lines.append("本表**逐行**覆盖当前全部引擎原子（`_atomic_*` 实现），并列出 Round 31 / 32 / 33 真删/真合并的每一个名字。")
    lines.append(f"表里所有判「删」或「合」的行**都已在本轮执行完毕**：`--check` 会验证这些名字已经没有")
    lines.append(f"任何 `_atomic_*` 实现、卡数据 0 引用（当前引擎原子 {len(model['atoms'])} 个）。")
    lines.append("")
    lines.append("生成：`python tools/atom_full_inventory.py`；校验：`python tools/atom_full_inventory.py --check`。")
    lines.append("用量口径与 `tools/mod_atom_report.py` 完全一致（`op`/`type` 键、嵌套步骤展开）。")
    lines.append("")
    lines.append(f"## 一、Round 31–41 真删 / 真合并 / 半拆（{len(model['actions'])} 个名字）")
    lines.append("")
    lines.append("| 原子 | 判定 | 迁移前用量 | 本批用量 | 替代写法 | 理由 |")
    lines.append("|---|---|---|---|---|---|")
    for row in model["actions"]:
        replacement = row["replacement"] or "（无等价写法）"
        lines.append(
            f"| `{row['name']}` | {row['verdict']} | {row['before']} | {row['usage']} | "
            f"{replacement} | {row['reason']} |"
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
    lines.append(f"## 二、未使用 op 逐个定论（{len(model['unused_ops'])} 个名字）")
    lines.append("")
    lines.append("Round 41 / 批次 AE-5 给 `tools/op_long_tail_report.py` 报出的每个\"卡数据 0 引用\"名字")
    lines.append("逐个定论：**语言原语**（DSL 骨架）/ **机制钩子**（卡面机制的唯一实现）/ **伞原子** /")
    lines.append("**事件钩子** / **能力扩展点** / **可下沉**（拆成伞原子 + 数据）。判「删·」的行已经在本轮")
    lines.append("真删：既没有 `_atomic_*` 实现，卡数据也 0 引用，名字进 `REMOVED_ATOMIC_OPS` 或")
    lines.append("`RENAMED_ATOMIC_OPS`（写出来是显式报错，不静默）。")
    lines.append("")
    lines.append("| 原子 | 用量 | 判定 | 替代写法 | 理由 |")
    lines.append("|---|---|---|---|---|")
    for row in model["unused_ops"]:
        replacement = row["replacement"] or "（无等价写法）"
        lines.append(
            f"| `{row['name']}` | {row['usage']} | {row['verdict']} | {replacement} | {row['reason']} |"
        )
    lines.append("")
    lines.append(f"## 三、保留清单：当前全部引擎原子（{len(model['kept'])}）")
    lines.append("")
    lines.append("| 原子 | 家族 | 用量 | 判定 | 理由 |")
    lines.append("|---|---|---|---|---|")
    for row in model["kept"]:
        lines.append(f"| `{row['name']}` | {row['family']} | {row['usage']} | 留 | {row['reason']} |")
    lines.append("")
    lines.append("## 四、必须保留清单（语言原语 / 扩展点 / 机制钩子）")
    lines.append("")
    lines.append("这些名字不在 `_atomic_*` 实现表里，但属于 DSL 契约，**不属于删除候选**：")
    lines.append("")
    lines.append("| 类别 | 数量 | 名字 | 为什么必须留 |")
    lines.append("|---|---|---|---|")
    lines.extend(preservation_rows())
    lines.append("")
    lines.append("## 五、统计")
    lines.append("")
    lines.append("| 项 | 值 |")
    lines.append("|---|---|")
    lines.append(f"| 引擎原子（本表逐行覆盖） | {len(model['atoms'])} |")
    lines.append(f"| 本批删除 / 合并的名字 | {len(model['actions'])} |")
    lines.append(f"| 其中判定「合」 | {sum(1 for row in model['actions'] if row['verdict'] == '合')} |")
    lines.append(f"| 其中判定「删」 | {sum(1 for row in model['actions'] if row['verdict'] == '删')} |")
    lines.append(f"| 用量 0 的引擎原子 | {sum(1 for row in model['kept'] if row['usage'] == 0)} |")
    lines.append(f"| 用量 > 0 的引擎原子 | {sum(1 for row in model['kept'] if row['usage'] > 0)} |")
    lines.append(f"| 未使用 op 定论条数 | {len(model['unused_ops'])} |")
    lines.append(
        f"| 其中判定「删·」 | {sum(1 for row in model['unused_ops'] if row['verdict'].startswith('删'))} |"
    )
    lines.append(
        f"| 其中判定「留·」 | {sum(1 for row in model['unused_ops'] if row['verdict'].startswith('留'))} |"
    )
    lines.append("")
    # Round 47 / 批次 AK：三层口径（"原子到底有多少个"的唯一权威回答）。
    public_atoms = sorted(getattr(mod_spec_v2, "PUBLIC_ATOMS", ()) or ())
    internal = sorted(getattr(mod_spec_v2, "INTERNAL_HANDLERS", ()) or ())
    macros = dict(getattr(mod_spec_v2, "ATOMIC_OP_MACROS", {}) or {})
    lines.append("## 六、Round 47 三层口径（公开原子 / 内部处理器 / 宏）")
    lines.append("")
    lines.append("`_CORE_LOGIC_OPS` 是「所有名字」的历史并集（116），想知道原子数量看这三层：")
    lines.append("")
    lines.append("| 层 | 数量 | 说明 |")
    lines.append("|---|---|---|")
    lines.append(f"| 公开原子 `PUBLIC_ATOMS` | {len(public_atoms)} | 卡数据可以写、有真实实现的步骤 op（引擎 "
                 f"{len(model['atoms'])} 个 `_atomic_*` − {len(set(internal) & set(model['atoms']))} 个内部处理器 + "
                 f"{len(mod_spec_v2.RUNTIME_STEP_OPS)} 个运行时原生步骤 − 内部运行步骤） |")
    lines.append(f"| 内部处理器 `INTERNAL_HANDLERS` | {len(internal)} | 名字已退役（写出来显式报错），"
                 f"实现留给引擎内部与老测试直呼 |")
    lines.append(f"| 宏 `ATOMIC_OP_MACROS` | {len(macros)} | " +
                 "、".join(f"`{k}` → `{v}`" for k, v in sorted(macros.items())) + " |")
    lines.append("")
    lines.append("### 6.1 内部处理器逐条（数据写不出来，`--check` 卡住数据引用）")
    lines.append("")
    lines.append("| 名字 | 在引擎里有 `_atomic_*` 实现 | 为什么留 |")
    lines.append("|---|---|---|")
    for name in internal:
        has_handler = "是" if name in set(model["atoms"]) else "否（运行时原生）"
        lines.append(f"| `{name}` | {has_handler} | "
                     f"{'名字已退役（`REMOVED_ATOMIC_OPS` / `RENAMED_ATOMIC_OPS`），实现只服务直呼方' if name in set(model['atoms']) else '运行时自己发出的挂起式牌堆挑选恢复步骤'} |")
    lines.append("")
    lines.append("### 6.2 公开原子全表")
    lines.append("")
    width = 30
    for index in range(0, len(public_atoms), 4):
        chunk = public_atoms[index:index + 4]
        lines.append("  " + "".join(f"`{name}`".ljust(width) for name in chunk).rstrip())
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
    # Round 47 / 批次 AK：三层口径必须铺满引擎原子与运行时原生步骤。
    public_atoms = set(getattr(mod_spec_v2, "PUBLIC_ATOMS", ()) or ())
    internal_handlers = set(getattr(mod_spec_v2, "INTERNAL_HANDLERS", ()) or ())
    macros = set(getattr(mod_spec_v2, "ATOMIC_OP_MACROS", {}) or {})
    layers = (("公开", public_atoms), ("内部", internal_handlers), ("宏", macros))
    covered = set()
    for label, names in layers:
        overlap = covered & names
        if overlap:
            problems.append(f"Round 47 三层口径重叠（{label}）：{sorted(overlap)[:5]}")
        covered |= names
    uncovered = sorted((engine_ops | set(mod_spec_v2.RUNTIME_STEP_OPS)) - covered)
    if uncovered:
        problems.append(f"Round 47 三层口径没铺满步骤 op：{uncovered[:6]}")
    retired_names = set(mod_spec_v2.REMOVED_ATOMIC_OPS) | set(mod_spec_v2.RENAMED_ATOMIC_OPS)
    stray_public = sorted(public_atoms & retired_names)
    if stray_public:
        problems.append(f"公开原子里混进了退役名字：{stray_public[:5]}")
    # 内部处理器只该有两类：退役但有实现的（== handler_kept 表），加上运行时自用步骤。
    expected_internal = {row["name"] for row in model["handler_kept"]} | {"deck_catalog_pick_resume"}
    if internal_handlers != expected_internal:
        problems.append(
            f"内部处理器与预期不一致：缺 {sorted(expected_internal - internal_handlers)[:5]}，"
            f"多 {sorted(internal_handlers - expected_internal)[:5]}"
        )
    # Round 41 / 批次 AE-5：未使用 op 的定论表必须覆盖"当前 0 引用"的每一个登记名，
    # 且判「删·」的行必须真的删干净（没有实现、卡数据 0 引用、名字进退役表）。
    verdict_rows = {row["name"]: row for row in model["unused_ops"]}
    if len(verdict_rows) != len(model["unused_ops"]):
        problems.append("未使用 op 定论表里有重复行")
    zero_usage = sorted(
        name
        for name in set(mod_spec_v2.VALID_LOGIC_OPS)
        if not model["any_usage"].get(name, 0)
    )
    missing = [name for name in zero_usage if name not in verdict_rows]
    if missing:
        problems.append(f"未使用 op 定论表缺行：{missing[:8]}（共 {len(missing)} 个）")
    retired = set(mod_spec_v2.REMOVED_ATOMIC_OPS) | set(mod_spec_v2.RENAMED_ATOMIC_OPS)
    for row in model["unused_ops"]:
        name = row["name"]
        if row["usage"]:
            problems.append(f"{name}: 定论表写 0 引用，但卡数据有 {row['usage']} 处引用")
        if not row["verdict"].startswith(("留·", "删·")):
            problems.append(f"{name}: 判定必须以 留·/删· 开头")
        if row["verdict"].startswith("删·"):
            if row["has_impl"]:
                problems.append(f"{name}: 判定删除，但引擎里还有 _atomic_{name} 实现")
            if name not in retired:
                problems.append(f"{name}: 判定删除，但名字没进 REMOVED/RENAMED 表")
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
