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
    "set_status_named": ("合", 0, '{"op":"status_add_named","mode":"set",...}',
                         "与 status_add_named 同调 _apply_status_add_family，只差默认层数来源；"
                         "参数一律走 mode"),
    "clear_status": ("合", 2, '{"op":"status_remove_named","amount":"all",...}',
                     "清的是 _status_attr_field 那 8 个玩家属性字段，与命名状态族同一张属性表；"
                     "合并后拿到别名组/上限/成就/状态钩子（默认不再自动播报，见报告差异 1）"),
    "resolve_status_once": ("合", 3, '{"op":"settle_status","reduce":1,...}',
                            "灼烧结算一次并减 N 层 = settle_status(reduce)；伤害类型/标签/默认战报"
                            "逐字保留（log:false 现在真的静音，见报告差异 2）"),
    "set_untargetable": ("合", 0, '{"op":"player_status_layers","status":"untargetable","shovel":true}',
                         "只加 1 层且强制点亮 shovel；合并后 shovel 变成显式参数"),
    "untargetable_layers": ("合", 1, '{"op":"player_status_layers","status":"untargetable",...}',
                            "玩家状态层数族（Ocean 黄瓜的 after_resolution 在用）"),
    "set_invincible": ("合", 1, '{"op":"player_status_layers","status":"invincible"}',
                       "无敌走 _set_invincible_until_next_own_turn_end 的回合簿记，"
                       "与 player_prop_change(property:'invincible') 只写字段不同"),
    "destroy_self_equipment": ("合", 8, '{"op":"destroy_equipment","mode":"self"}',
                               "拆「这张牌自己挂着的那件装备」；与 destroy_current_equipment 同解"),
    "destroy_current_equipment": ("合", 2, '{"op":"destroy_equipment","mode":"self"}',
                                  "同上（全场按实例 id 找 = self 模式的第一段）"),
    "destroy_all_destroyable_equipment": (
        "合", 1,
        '{"op":"destroy_equipment","mode":"all","filter":"destroyable","record_count":true,"target":"both"}',
        "拆光所有非 indestructible 装备并记账；filter/record_count 成为规范参数"),
    "destroy_equipment_choice_or_first": ("合", 0,
                                          '{"op":"destroy_equipment","mode":"choice","target":"enemy"}',
                                          "与「点选装备」选择窗口耦合：本轮把窗口接到 "
                                          "destroy_equipment(mode:'choice') 上（无点选时回落到第一件）"),
    "card_prop_set": ("合", 18, '{"op":"card_prop_change","mode":"set",...}',
                      "参数与 player_prop_change 对齐；实现体（钳位/上限/联动字段）原样搬过来"),
    "card_prop_add": ("合", 10, '{"op":"card_prop_change","mode":"add",...}',
                      "同上；multi_petal 的 fission_level 双倍特例保留"),
    "card_prop_mul": ("合", 0, '{"op":"card_prop_change","mode":"mul",...}',
                      "同上；multiplier 仍是它认的键"),
    "remove_tag": ("合", 0, '{"op":"add_tag","mode":"remove",...}',
                   "标签族统一到 add_tag/add_tag_to_zone 的 mode（add/remove/clear/toggle）"),
    "clear_tags": ("合", 0, '{"op":"add_tag","mode":"clear",...}',
                   "同上；清空时把有效标签压进 disabled_flags 的行为保留"),
    "remove_tag_from_zone": ("合", 0, '{"op":"add_tag_to_zone","mode":"remove",...}',
                             "与 add_tag_to_zone 共用区域遍历/计数/战报，mode 决定加减"),
    "toggle_tag_in_zone": ("合", 1, '{"op":"add_tag_to_zone","mode":"toggle",...}',
                           "逐张翻转（Yin-Yang 在用），合并后仍是 add_tag_to_zone 的一档 mode"),
    "put_card_to_deck": ("删", 0, '{"op":"move_card","zone":"deck","card":{"ref":"selected_card"},...}',
                         "被 move_card 完全覆盖（selected_card ref 读的正是 choice.target_instance_id）"),
    "give_card_to_discard": ("删", 0, '{"op":"create_card","card_id":"...","to":"discard",...}',
                             "被运行时的 create_card(to:) 覆盖（造牌入区，支持 target/多目标）"),
    "reveal_deck_top": ("删", 0, '{"op":"reveal_card_set","source":"deck","amount":N,...}',
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
    "spend_resource": "资源消耗唯一实现（resource/target/amount/all + spent 记账）",
    "add_tag": "卡内标签族唯一实现（mode=add|remove|clear）",
    "add_tag_to_zone": "区域标签族唯一实现（mode=add|remove|toggle）",
    "for_each": "循环族唯一驱动（source/bind/condition/limit + 断点续跑）",
    "move_card": "区域移动族唯一实现（zone=hand|deck|discard|exile）",
    "choose_from_zone": "区域取牌族唯一实现（zone=deck|discard|exile + 选择窗口联动）",
    "card_counter": "卡内计数器（mode=play|equip_turns|reset）",
    "deal_damage": "攻击管线唯一入口（力量/精准/暴击/子瓣继承 + hits）",
    "direct_damage": "直伤管线唯一入口（source_text/damage_type/damage_tag/hits）",
    "heal": "回复唯一入口（heal_block/上限/战报）",
    "gain_e": "获得 E（含上限与记账）",
    "gain_m": "获得 M（含上限与记账）",
    "turn_mod_add": "每回合修正（kind=e_regen|m_regen|draw）",
    "global_mult": "全场倍率（kind=damage|heal|cost）",
    "equip_reduce_draw": "装备减抽（target=self|enemy）",
    "place_as_equip": "把牌作为装备加入（71 处使用，签名冻结）",
    "add_equipment_to_zone": "从卡 id 造装备进装备区",
    "add_equipment_armor": "所有装备获得护甲（层数）",
    "seal_equipment": "尘封装备（层数）",
    "equipment_prop_set": "装备属性写值（设为）",
    "equipment_prop_add": "装备属性写值（增加）",
    "remove_equip_protection": "清空装备保护层数",
    "counter_equip_protect": "装备保护层数（反制族）",
    "on_fatal_invincible_then_die": "致命伤保护（H=1 + 无敌 + 回合末死亡）",
    "on_fatal_set_health_exile": "致命伤改为放逐",
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
    "for_each_selected_card": "选中的每张牌循环",
    "for_each_list": "列表循环（绑定 list item 而不是玩家）",
    "timed_effect": "计时效果（duration/trigger/body）",
    "countdown_var": "倒计时变量（player_var_change 的定时封装）",
    "register_play_listener": "出牌监听注册（scope/duration/body）",
    "queue_auto_play": "排队自动打出（card/source/each_turn/cost/exile）",
    "auto_play_card": "立刻自动打出（含 no_cost/auto_choice）",
    "auto_play_zone_top": "自动打出某区顶牌（Kitty 类）",
    "once_per_play": "每次打出至多一次（监听去重）",
    "after_all": "把 body 放到当前效果之后执行",
    "if_else": "控制流原语（if 的 else 分支）",
    "repeat_until": "控制流原语（重复到条件成立）",
    "break": "控制流原语（跳出循环）",
    "continue": "控制流原语（跳过本次迭代）",
    "request_card": "请求选牌（UI 挂起，164 处使用）",
    "request_target": "请求选目标（UI 挂起，164 处使用）",
    "request_confirm": "请求确认（UI 挂起）",
    "request_reorder_deck": "请求重排牌堆（UI 挂起）",
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
    "swap_health": "交换双方生命",
    "shuffle_hand": "打乱手牌（失明）",
    "shuffle_discard_into_deck": "弃牌堆洗回牌堆",
    "give_card_to_hand": "造牌入手（overflow/missing 处理）",
    "give_card_to_deck": "造牌入牌堆（position/flags）",
    "give_magic_orb_to_hand": "造魔法宝珠入手（固定印痕）",
    "move_cards_to_deck": "批量把牌放回牌堆",
    "draw_cards": "抽牌（含钩子/上限/唯一牌）",
    "discard_choice_then_draw": "先弃后抽（弃牌选择窗口）",
    "discard_hand_by_paid_e": "按本回合已付 E 弃手牌（Desert）",
    "lose_health": "直接失去生命（可击杀）",
    "set_health": "直接设置生命",
    "increase_next_cost": "下次出牌费用修正（+）",
    "reduce_next_cost": "下次出牌费用修正（-）",
    "snapshot_card_props": "牌属性快照（按实例存）",
    "restore_card_props": "恢复牌属性快照",
    "restore_match_start_stats": "恢复开局属性",
    "restore_turn_start_stats": "恢复回合开始属性",
    "set_card_prop_random": "区域内随机设定属性",
    "list_set": "列表原语（set）",
    "list_append": "列表原语（append）",
    "list_insert": "列表原语（insert）",
    "list_delete": "列表原语（delete）",
    "list_clear": "列表原语（clear）",
    "charge_self_damage": "充能自身伤害",
    "counter_pending_attack_damage": "反击待结算攻击伤害（Desert）",
    "absorb_attack_damage": "吸收攻击伤害（body + once）",
    "ricochet_attack": "弹射（攻击管线变体）",
    "lifesteal_damage": "吸血伤害",
    "triangle_damage": "三角伤害（层数 x 基数）",
    "card_damage_multiply": "聚变倍率（fusion_level x N）",
    "activate_corruption": "激活装备腐化",
    "aura_enemy_elixir_recovery": "敌方 E 回复光环修正",
    "broadcast_event": "对外广播事件",
    "response_declare": "声明响应（占位步骤，无实现体）",
    "trigger_manual": "手动触发（占位步骤，无实现体）",
    "declare_forced_target": "声明强制目标窗口（Light Bulb）",
    "add_charge_to_hand": "手牌充能（Arctic）",
    "apply_turn_regen": "回合回复（Jungle）",
    "assembler_effect": "装配机（Factory）",
    "cogwheel_mark": "齿轮标记（Factory）",
    "coffee_gain_e": "咖啡获得 E（Hel）",
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
    for name, (verdict, before, replacement, reason) in ROUND31_ACTIONS.items():
        actions.append({
            "name": name, "verdict": verdict, "before": before,
            "usage": usage.get(name, 0), "replacement": replacement, "reason": reason,
        })
    actions.sort(key=lambda row: row["name"])
    return {"atoms": atoms, "usage": usage, "kept": kept, "actions": actions}


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
    lines.append("# 原子全量清单（Round 31 / 批次 Z · 2026-09-12）")
    lines.append("")
    lines.append("本表**逐行**覆盖当前全部引擎原子（`_atomic_*` 实现），并列出本批真删/真合并的每一个名字。")
    lines.append(f"表里所有判「删」或「合」的行**都已在本轮执行完毕**：`--check` 会验证这些名字已经没有")
    lines.append(f"任何 `_atomic_*` 实现、卡数据 0 引用（当前引擎原子 {len(model['atoms'])} 个）。")
    lines.append("")
    lines.append("生成：`python tools/atom_full_inventory.py`；校验：`python tools/atom_full_inventory.py --check`。")
    lines.append("用量口径与 `tools/mod_atom_report.py` 完全一致（`op`/`type` 键、嵌套步骤展开）。")
    lines.append("")
    lines.append(f"## 一、本批真删 / 真合并（{len(model['actions'])} 个名字）")
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
