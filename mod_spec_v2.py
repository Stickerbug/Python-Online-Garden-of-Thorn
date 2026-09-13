import hashlib
import json
import re
from typing import Any, Dict, Tuple

from atomic_registry import engine_atomic_ops, merge_public_ops


FORMAT_VERSION = 2
API_VERSION = "2.0"

VALID_CAPABILITIES = {
    "cards",
    "tags",
    "statuses",
    "opening_events",
    "ui_components",
    "ui.modal",
    "ui.choice",
    "ui.visual_limited",
    "patches",
    "compatibility",
    "event_hooks",
    "logic_dsl",
    "logic.basic",
    "logic.advanced",
    "localization",
}

VALID_REGISTRY_KEYS = {
    "cards",
    "tags",
    "statuses",
    "opening_events",
    "ui_components",
    "variables",
    "lists",
}

VALID_UI_COMPONENT_TYPES = {
    "modal",
    "panel",
    "prompt",
    "choice",
    "confirm",
    "player_picker",
    "target_picker",
    "card_picker",
    "equipment_picker",
    "zone_picker",
    "text",
    "dynamic_text",
    "divider",
    "rich_text",
    "button",
    "button_group",
    "input",
    "number",
    "number_input",
    "select",
    "radio_group",
    "checkbox",
    "slider",
    "multi_select",
    "tabs",
    "list",
    "card_preview",
    "stat_display",
    "warning_text",
    "preview_value",
}

_CORE_LOGIC_OPS = {
    "literal",
    "const",
    # Runtime-native ops without an ``_atomic_*`` handler (executed by
    # ``mod_runtime_v2`` itself): the suspended deck picker used by Cicada 3301.
    "deck_catalog_pick",
    "deck_catalog_pick_resume",
    "var",
    "get",
    "set_var",
    "add_var",
    "add",
    "sub",
    "mul",
    "div",
    "min",
    "max",
    "clamp",
    "compare",
    "and",
    "or",
    "not",
    # Round 32 / 批次 AA：``if`` 并进 ``if_else``、``repeat_until`` 并进
    # ``repeat(until=...)``、``for_each_list``/``for_each_selected_card``
    # 并进 ``for_each``；旧名见 REMOVED_ATOMIC_OPS / RENAMED_ATOMIC_OPS。
    "if_else",
    "repeat",
    "for_each",
    "break",
    "continue",
    "random",
    "log",
    # 卡组前缀旧名：Round 12 批次 0 起不再登记"既无实现也无人引用"的名字
    # （清单与理由见 .codex-tmp/round12/rd12.md）；Round 25 把剩下的 66 个
    # （`bio_*` / `jungle_*` / `desert_*` / `arctic_*` / `ocean_*` / `void_*` /
    # `hel_*` 与 `call` / `emit` / `choose` / `mod` / `set` / `ref` / `sequence` /
    # `stop` / `gain_resource`）一并注销，见 .codex-tmp/round25/rd25.md。
    "request_ui",
    # Round 36 / 批次 AD-1：请求族四合一 —— 旧的 ``request_target`` /
    # ``request_card`` / ``request_confirm`` / ``choose_from_zone`` /
    # ``declare_forced_target`` / ``copy_choice_with_discount`` /
    # ``request_reorder_deck`` 并进 ``request``，``type`` 选类别
    # （target / card / confirm / zone / forced_target / discount_copy /
    # reorder_deck）。旧名见 REMOVED_ATOMIC_OPS（写出来是显式报错）。
    "request",
    # Round 37 / 批次 AD-2：监听/收尾/触发四合一 —— ``once_per_play`` /
    # ``register_play_listener`` / ``after_all`` / ``magic_relic_trigger`` 并进
    # ``on_event``（``trigger`` 选 play/this_play/after_all/equipment_trigger）。
    "on_event",
    "deal_damage",
    "damage",
    # Round 32 / 批次 AA：生命族并进 ``health_op``、资源族并进 ``resource_op``、
    # 抽牌族并进 ``draw``（``count`` + ``modifiers``）。旧名见两个旧名表。
    "health_op",
    "resource_op",
    "draw",
    "move_card",
    "create_card",
    "copy_card",
    # Round 33 / 批次 AB：三条 AB 伞原子——``reveal``（揭示：card_set/enemy_hand/hand
    # 三合一）、``shuffle``（洗牌：discard→deck / 打乱手牌）、``snapshot`` 与
    # ``restore``（属性快照 / 开局与回合初还原）。旧名见 REMOVED_ATOMIC_OPS。
    "reveal",
    "shuffle",
    "snapshot",
    "restore",
    # Round 42 / 批次 AF：``transform_card`` 已删除（只播报的占位步骤，
    # 真变换是下面的 ``transform_cards``）。
    # Round 35：批次 AC 的四族（装备/状态/标签/自动打出）迁移收尾，规范名
    # 换成下面的伞原子；旧名进 REMOVED_ATOMIC_OPS（写出来是显式报错）。
    # 参数面见 docs/原子参数表.md 与各 `_atomic_<伞>` 的文档字符串。
    "equipment_op",
    "status_op",
    "tag_op",
    "auto_play",
    # Round 33 / 35：下面这几个旧名字已经退役（进 REMOVED_ATOMIC_OPS，写出来
    # 是显式报错），但它们的 ``_atomic_*`` 处理器**保留**给直接调用者：
    # ``place_as_equip``（formal_logic_runtime 直呼）、``status_add_named`` /
    # ``add_tag`` / ``add_tag_to_zone``（tests 直呼）、``copy_card_instance``
    # （``copy_card`` 伞的 as_instance 段转交 + 测试 spy）、
    # ``give_card_to_hand`` / ``create_copies_to_deck_top``（tests 直呼）。
    # 只有"退役 + 保留处理器"的名字才需要在这里额外登记，其余引擎原子
    # ``_CORE_LOGIC_OPS`` 已经全覆盖。
    "add_tag",
    "add_tag_to_zone",
    "place_as_equip",
    "status_add_named",
    "copy_card_instance",
    "create_copies_to_deck_top",
    "give_card_to_hand",
    "modify_event_value",
    "player_stat",
    "player_property",
    "card_prop",
    "card_property",
    "equipment_prop",
    "equipment_property",
    "count",
    "zone_count",
    # Round 27：区域取牌族补了"随机 N 张"（``zone_random_ids``）；顶部/底部
    # 由同一个 ``zone_top_ids`` 的 ``order`` 参数覆盖（见 docs §3 / §25）。
    "zone_random_ids",
    "equipment_count_targeting",
    "hand_full",
    "floor",
    "ceil",
    "last_damage",
    "event_value",
    "damage_amount",
    "damage_source",
    "target_player",
    "status_stack",
    "card_has_tag",
    "has_tag",
    "has_status",
    "has_status_named",
    "zone_exists",
    "var_compare",
    "direct_damage",
    # Round 42 / 批次 AF：``lifesteal_damage`` / ``triangle_damage`` 已删除——
    # 官方包 ``vanilla:fang`` / ``vanilla:triangle`` 的卡数据早就把这两条机制
    # 写成 ``deal_damage`` + ``health_op`` / ``if_else`` + ``player_var_change``
    # 的通用组合（见 REMOVED_ATOMIC_OPS 的替代 JSON）。
    # Round 24（C 类同形小原子合并）：护甲/闪避族与状态三兄弟、清状态族、
    # 每回合修正族、资源族、全局倍率族各自的旧名一并注销，改由下面的
    # player_stat_change / status_add_named / clear_statuses(preset) /
    # resource_spend 承接；Round 42 / 批次 AF 又把 ``turn_mod_add`` /
    # ``global_mult`` 本身也删了（它们写的字段全仓库零读取方，替代写法 = ``log``）。
    # 旧名见 REMOVED_ATOMIC_OPS（写出来是显式报错，不静默）。
    "player_stat_change",
    # Round 32 / 批次 AA：``equip_reduce_draw`` 并进 ``draw`` 的
    # ``modifiers:[{"type":"sluggish",...}]``。
    # Round 33 / 批次 AC + Round 35 收尾：状态四兄弟并成 ``status_op``
    # （``action`` 选 add/set/remove/clear/settle），标签两兄弟并成 ``tag_op``。
    # ``status_add_named`` 的处理器保留给 tests（登记在上面），其余进
    # REMOVED_ATOMIC_OPS。
    "status_add_named",
    # Round 29 / 批次 X：三个"从某区选一张进手牌"的同形原子合并成一条
    # （``zone`` 选区域）；Round 36 / 批次 AD-1 连同 ``copy_choice_with_discount``
    # 一起并进 ``request`` 伞（``type:"zone"`` / ``type:"discount_copy"``），
    # 旧名进 REMOVED_ATOMIC_OPS。
    # Round 33 / 批次 AB：``reveal_enemy_hand`` / ``reveal_hand_cards`` /
    # ``steal_enemy_card`` / ``shuffle_discard_into_deck`` / ``shuffle_hand`` /
    # ``give_card_to_hand`` / ``give_magic_orb_to_hand`` / ``give_card_to_deck``
    # 已并入 ``reveal`` 与 ``move_card`` / ``shuffle``（旧名进 REMOVED_ATOMIC_OPS）。
    "remove_specific_card",
    # Round 29 / 批次 X：``move_to_*`` 四条"糖"原子并入通用 ``move_card(zone=...)``；
    # ``destroy_random_equip`` / ``destroy_all_equip`` / ``destroy_all_field_equip``
    # 并入 ``equipment_op(mode:"destroy", pick=..., scope=...)``。旧名进
    # REMOVED_ATOMIC_OPS。
    # Round 31 / 批次 Z：Round 29 的兼容垫片（``move_to_hand`` 等六个）与
    # ``destroy_equipment_choice_or_first`` / ``destroy_self_equipment`` /
    # ``destroy_current_equipment`` / ``destroy_all_destroyable_equipment`` 也已
    # 真正删除（destroy 族并进 ``equipment_op`` 的 pick/filter）。
    # Round 35：装备族剩下的五个旧名（``add_equipment_armor`` /
    # ``remove_equip_protection`` / ``add_equipment_to_zone`` / ``for_each_equipment``
    # / ``destroy_equipment``）一并迁进 ``equipment_op`` 的 mode，名字进
    # REMOVED_ATOMIC_OPS；只有 ``place_as_equip`` 的处理器因为
    # formal_logic_runtime 直呼而保留（登记在上面）。
    # Round 42 / 批次 AF：``equip_protection``（counter_equip_protect 的旧别名）
    # 与 ``counter_equip_protect`` 一起退役——装备保护层数由
    # ``player_prop_change(mode:"add", property:"equipment_protection")`` 写。
    # Round 42 / 批次 AF：``emit_event``（含 Round 37 并进来的
    # ``broadcast_event`` / ``trigger_manual``）与 ``action_filter``（含 Round 38
    # 并进来的四条行为过滤原子）都已删除——前者写的"事件"没有任何订阅方，
    # 后者写的四个玩家字段全部由 ``player_prop_change`` / ``status_op`` 覆盖。
    # 旧名与两个伞名都在 REMOVED_ATOMIC_OPS 里给了替代写法。
    # Round 31 / 批次 Z：``set_invincible`` / ``set_untargetable`` /
    # ``untargetable_layers`` 三条玩家状态层数原子并成 ``player_status_layers``
    # （``status`` 选 untargetable/invincible），旧名进 REMOVED_ATOMIC_OPS。
    "player_status_layers",
    # Round 38 / 批次 AD-3：``skip_turn`` / ``extra_turn`` / ``force_end_turn``
    # 三条回合控制原子并成 ``turn_control``（``mode`` 选 end/skip/extra），
    # 旧名进 REMOVED_ATOMIC_OPS（带替代 JSON）。
    "turn_control",
    # Round 42 / 批次 AF：``fission`` / ``fusion`` 已删除——裂变层数是
    # ``card_prop_change(property:"fission_level")``（钳位与 ``fission_count``
    # 同步都在 ``_set_card_property_value`` 里），聚变的整套多卡合并已经是
    # ``vanilla:fusion`` 的卡数据（request + for_each + card_prop_change +
    # move_card）。
    "multiply_next_damage",
    # Round 43 / 批次 AG：``modify_next_cost``（Round 32 由 reduce_next_cost /
    # increase_next_cost 合并而来）已删除——它写的 ``temp_swift_value`` /
    # ``temp_heavy_value`` 本来就在 ``_set_card_property_value`` 的白名单里
    # （带 ``temp_swift`` / ``temp_heavy`` 标签同步），替代写法是
    # ``card_prop_add_to_zone(zone:"hand", property:"temp_heavy_value", amount:N,
    # require_selectable:false, silent:true)``（减费换 ``temp_swift_value``）。
    # Round 42 / 批次 AF：``transform_card``（只播报的占位步骤）已删除。
    # Round 29 / 批次 X：耐久三兄弟并入卡牌属性族
    # （``card_prop_add``/``card_prop_set`` + ``property:"durability"``）。
    # Round 32 / 批次 AA：``swap_health`` 并进 ``health_op(mode:"swap")``。
    # Round 33 / 批次 AB：``swap_hands`` 已并入 ``move_card(mode:"swap_hands")``。
    # Round 42 / 批次 AF：``emit_event`` / ``modify_damage`` 已删除——两者都是
    # "只写一行播报"的步骤（事件总线无订阅方；``formula`` 无读取方），
    # 替代写法是一行 ``log``。
    # Round 29 / 批次 X：玩家自定义变量的五个同形原子合并成
    # ``player_var_change(mode=set|add|sub|mul|div)``；Round 31 起 ``var_set``
    # 兼容垫片也已删除（旧名进 REMOVED_ATOMIC_OPS）。
    "player_var_change",
    # Round 32 / 批次 AA：列表五兄弟并进
    # ``list_modify(list=..., mode=set|append|insert|delete|clear, index=..., value=...)``。
    "list_modify",
    # Round 37 / 批次 AD-2：``timed_effect`` 并进 ``delayed_effect(mode:"timed")``。
    "delayed_effect",
    # Round 41 / 批次 AE-5：``countdown_var`` 已删除（"写初值 + 每次触发减 1" =
    # ``player_var_change(mode:"set")`` + ``delayed_effect(mode:"timed")``）。
    # Round 29 / 批次 X：``player_prop_set`` / ``player_prop_add`` 合并成
    # ``player_prop_change(mode=set|add)``；Round 31 起两个垫片已删除。
    "player_prop_change",
    # Round 29 / 批次 X：``card_var_set`` / ``card_var_add`` 合并成
    # ``card_var_change(mode=set|add)``；Round 31 起两个垫片已删除。
    "card_var_change",
    # Round 42 / 批次 AF：``card_counter`` 已删除——它写的
    # ``card.play_count`` / ``card.equip_turns`` 补进 ``card_prop_change`` 的属性
    # 白名单后就是普通属性写入（``mode:"play"`` → ``add play_count`` …）。
    # Round 31 / 批次 Z：卡牌属性写值族三合一
    # （``card_prop_change(mode=set|add|mul)``，参数与 ``player_prop_change`` 对齐）。
    "card_prop_change",
    # Round 41 / 批次 AE-5：``card_damage_multiply`` 已删除（=
    # ``card_prop_change(mode:"mul", property:"fusion_level", multiplier:N)``）。
    "equipment_prop_set",
    "equipment_prop_add",
    # Round 40 / 批次 AE-4：``discard_hand_by_paid_e``（按本牌实际花费 E 批量
    # 弃手牌）下沉成 ``move_card(mode:"batch", source_zone:…, filter:…)``，
    # 旧名进 REMOVED_ATOMIC_OPS。
    # Round 33 / 批次 AB：两条 ``restore_*_stats`` 已并入
    # ``restore(mode:"turn_start"/"match_start")``。
    # Round 43 / 批次 AG：``counter_pending_attack_damage``（盐式"按待结算攻击的
    # 第一段伤害反弹"）已删除——响应上下文里就能读到 ``first_hit_damage``
    # （``_run_v2_card_event`` 把 extra_context 并进 ``context['vars']``），
    # 替代写法见 REMOVED_ATOMIC_OPS 的完整 JSON。
    "discard_choice_then_draw",
    # Round 42 / 批次 AF：``activate_corruption`` 已删除——同一个 setter 已由
    # ``equipment_prop_set(property:"corruption_active")`` 覆盖，官方包
    # ``vanilla:corruption`` 的卡数据就是这么写的。
    # Round 41 / 批次 AE-5：``response_declare``（返回 None 的空占位步骤）已删除。
    "on_any_turn_start",
    "on_damage_taken",
    "on_discard_owner_turn_start",
    "on_enemy_turn_start",
    "on_equipment_destroy",
    "on_equipment_trigger",
    "on_hand_owner_turn_start",
    "on_hand_owner_turn_end",
    "on_owner_turn_start",
    "on_target_turn_start",
    "on_owner_turn_end",
    # Round 33 / 批次 AC + Round 35：``add_tag`` / ``add_tag_to_zone`` 并成
    # ``tag_op``（``action`` 选 add/remove/toggle/clear，带 zone 即区域级）；
    # 两个旧名的处理器保留给 tests 直呼（登记在上面），公开契约里已退役。
    # Round 41 / 批次 AE-5：``cogwheel_mark`` 半拆成"数据写标志位（``player_var_change``）
    # + 最小收牌例程"，例程原子改名 ``cogwheel_return``（旧名进 RENAMED_ATOMIC_OPS）；
    # ``goggles_enable`` 整个删除，视图权限改由装备标签 ``continuous_deck_reveal``
    # 声明（见 REMOVED_ATOMIC_OPS）。
    "cogwheel_return",
    "honey_control",
    # Round 40 / 批次 AE-2：``assembler_effect``（重构机）下沉成卡数据里的
    # 通用步骤组合（request 选牌 → move_card 放逐 → random_choice 奖励表 →
    # move_card(mode:"give") 造牌 → card_prop_change 迅捷 → status_op 碎片 →
    # log），旧名进 REMOVED_ATOMIC_OPS。
    "apply_turn_regen",
    # Round 33 / 批次 AB：``create_copies_to_deck_top`` 已并入
    # ``copy_card(to_zone:"deck_top", count:N)``。
    # Round 43 / 批次 AG：``plank_immunity``（实现是 ``return None`` 的空步骤）已删除
    # ——木板的机制由装备标签 ``blocks_cheap_attacks`` 承载，卡数据里那一步直接删掉。
    # Round 37 / 批次 AD-2：``magic_relic_trigger`` 并进
    # ``on_event(trigger:"equipment_trigger", effect:"magic_relic")``。
    "electric_web_arm",
    "magic_salt_reflect",
    "grant_temp_swift_highest_e",
    # Round 37 / 批次 AD-2：``delayed_blind_next_turn`` /
    # ``delayed_reveal_hand_next_turn`` 并进
    # ``delayed_effect(mode:"blind"|"reveal_hand")``。

    # 由"卡专用原子 → 通用数据步骤"重构抽出的通用能力。
    # 它们本来就是引擎里可复用的原子，这里补登记以免被误算作长尾。
    "card_prop_add_to_zone",
    # Round 40 / 批次 AE-3：``mark_original_card``（给被响应卡打标记）下沉成
    # ``card_var_change(card:{"ref":"original_card"}, …)``，旧名进
    # REMOVED_ATOMIC_OPS。
    # Round 37 / 批次 AD-2：``once_per_play`` 并进 ``on_event(trigger:"this_play")``。
    # Round 33 / 批次 AB：``copy_card_instance`` 已并入
    # ``copy_card(as_instance:true)`。
    # Round 33 / 批次 AC + Round 35：``auto_play_card`` / ``auto_play_zone_top``
    # 并成 ``auto_play``（``mode`` 选 card/zone_top）；``queue_auto_play``
    # 保持可用（官方包 ``ocean:magic_pearl`` 的步骤形状被测试断言）。
    "charge_self_damage",
    # Round 6a: data declares the "everyone must target me" window (Light
    # Bulb) so the engine no longer reads the pack's custom var directly.
    # Round 36 / 批次 AD-1：并进 ``request(type:"forced_target")``。

    # Round 20: 长尾原子登记（"卡数据仍在用、但没进策展清单"的 22 个）。
    # 它们本来就是引擎里的 _atomic_* 处理器，只是没被策展，导致
    # tools/mod_atom_report.py 一直把它们算作"未登记原子"。
    "absorb_attack_damage",
    "add_charge_to_hand",
    # Round 29 / 批次 X：``card_var_set`` / ``card_var_add`` 已合并成
    # ``card_var_change``（登记在上面的模块族里），这里不再重复登记。
    "crit_multiplier_add",
    "defer_game_over",
    # Round 33 / 批次 AB：``move_cards_to_deck`` 已并入
    # ``move_card(mode:"batch", target_zone:"deck", cards:…)``。
    "queue_auto_play",
    # Round 33 / 批次 AB：``random_zone_card_to_hand`` 已并入
    # ``move_card(mode:"random", source_zone:…, target_zone:"hand")``。
    # Round 37 / 批次 AD-2：``register_play_listener`` 并进
    # ``on_event(trigger:"play")``。
    # Round 33 / 批次 AB：``restore_card_props`` / ``reveal_card_set`` 已并入
    # ``restore(mode:"card_props")`` / ``reveal(mode:"card_set")``。
    "ricochet_attack",
    "set_card_prop_random",
    # Round 33 / 批次 AB：``snapshot_card_props`` 已并入
    # ``snapshot(mode:"card_props")``。
    "transform_cards",

    # Round 20: 上条的姊妹项——被代码/别名表引用（删掉会连带打断已登记
    # 的能力），或仍是某个家族唯一实现，因此保留并补登记。
    #   * gain_dodge：``dodge_permanent`` 的引擎端实现
    #     （game_engine._EFFECT_ALIASES 指过来）。
    #     Round 24 起 ``poison`` / ``burn`` / ``toxic`` / ``add_armor`` /
    #     ``dodge_permanent`` 连同它们的实现名（``apply_poison`` /
    #     ``apply_toxic`` / ``gain_armor`` / ``gain_dodge``）一起并进
    #     ``status_add_named`` / ``player_stat_change``，都进了
    #     REMOVED_ATOMIC_OPS，这里也不再补登记。
    #   * set_untargetable：承接 ``untargetable``。
    #     （Round 42 / 批次 AF：``counter_equip_protect`` 与它的别名
    #     ``equip_protection`` 一起删除——装备保护层数由
    #     ``player_prop_change(mode:"add", property:"equipment_protection")`` 写；
    #     ``block_own_actions`` / ``block_action`` 所在的 ``action_filter`` 也已
    #     删除，替代写法见 REMOVED_ATOMIC_OPS。）
    #   * for_each_target：``for_each_selectable_target`` 与
    #     ``ocean_for_each_selectable_target`` 的规范名（Round 16 统一驱动，
    #     Round 22 起两个旧名一并进 RENAMED_ATOMIC_OPS）。
    #   * on_fatal_invincible_then_die：game_engine.PASSIVE_EFFECT_TYPES 成员。
    #   * record_play_count / record_equip_turns / reset_counter / create_counter /
    #     exile_this / mark_self_damage_source：卡内计数器与放逐自身的通用原子。
    #   * （Round 24 已把 equip_reduce_own_draw / equip_reduce_enemy_draw
    #     合并成 equip_reduce_draw，见下。）
    #   * for_each_equipment：遍历装备的唯一入口（Round 17 未合并进 for_each）。
    #     Round 35 起并进 ``equipment_op(mode:"each")``，名字进
    #     REMOVED_ATOMIC_OPS。
    # Round 29 / 批次 X：``record_play_count`` / ``record_equip_turns`` /
    # ``reset_counter`` 曾合并成 ``card_counter``；Round 42 / 批次 AF 又把
    # ``card_counter`` 删掉，三个旧名在 REMOVED_ATOMIC_OPS 里改指
    # ``card_prop_change``。
    # Round 41 / 批次 AE-5：``create_counter`` 已删除——它写的
    # ``card.custom_counters`` 没有任何读取方；卡内任意计数改用
    # ``card_var_change(mode:"add"|"set", name:…, card:…)``（写 ``card.custom_vars``，
    # 会进 ``to_dict``，取值表达式也能读）。
    # Round 33 / 批次 AB：``exile_this`` 已删除——等价写法
    # ``move_card(zone:"exile", card:{"ref":"current_card"})``。
    # Round 42 / 批次 AF：``mark_self_damage_source`` 已删除——它写的
    # ``self_damage_next`` 全仓库零读取方，替代写法是一行 ``log``。
    # Round 37 / 批次 AD-2：``after_all`` 并进 ``on_event(trigger:"after_all")``。
}

# ---------------------------------------------------------------------------
# Round 25：登记表按"真实执行路径"分五类
# ---------------------------------------------------------------------------
# 以前只有一个 325 条的 ``_CORE_LOGIC_OPS``，把五种完全不同的名字混在一起，
# 参数表只能把它们统统计成"原子"（其实只有 195 个真有 ``_atomic_*`` 实现）。
# 现在每个名字都能通过 :func:`logic_op_group` 查到它属于哪一类：
#
#   ENGINE_ATOM_OPS    引擎 ``game_engine*.GameEngine._atomic_<name>`` 的真原子
#   RUNTIME_STEP_OPS   ``mod_runtime_v2.run_v2_step`` 直接执行的步骤 op（无 ``_atomic_*``）
#   EXPRESSION_OPS     取值表达式算子（``eval_v2_value`` 的 ``op`` 分支）
#   CONDITION_OPS      条件算子（``check_v2_condition`` 的 ``op`` 分支）
#   EVENT_HOOK_OPS     事件时点 / 声明键（引擎 ``_EFFECT_ALIASES``、被动钩子表）
#
# ``_CORE_LOGIC_OPS`` 仍是五类的并集：编辑器 ``op-schema.json``、校验器
# ``mod_validator_v2`` 与 ``tools/*`` 读的都是它，这次拆分不改变任何可用名字。
# 判定口径是**真实分派代码**（不是字符串猜测），复核脚本：
# ``python .codex-tmp/round25/rd25_classify_final.py``。
# 一个名字同时出现在多类时按上面的顺序归类——例如 ``random`` 既是引擎原子
# 也是表达式算子，记在 ENGINE_ATOM_OPS。

# 真原子 = 引擎源码里的 ``_atomic_*`` 处理器（``atomic_registry`` 扫描得到，
# 新增实现自动进这一组，不需要再改本文件）。
ENGINE_ATOM_OPS = frozenset(engine_atomic_ops())

# ``run_v2_step`` 直接执行的步骤 op：运行时原生，引擎没有同名 ``_atomic_*``。
RUNTIME_STEP_OPS = frozenset({
    "add_var",                 # 运行时变量自增（``set_var`` 的加法兄弟）
    "create_card",             # 造一张牌进指定区（无印痕校验，运行时自带）
    "deck_catalog_pick",       # Cicada 3301 的挂起式牌堆挑选（发起）
    "deck_catalog_pick_resume",  # 同上（恢复；没有 ``_atomic_*``）
    "modify_event_value",      # 改写当前事件的 ``event_value``
    "request_ui",              # 弹出 UI 组件并挂起事件
    "set_var",                 # 运行时变量赋值
})

# 取值表达式算子（``eval_v2_value``；写在"数值/文本"参数位置，不是步骤）。
EXPRESSION_OPS = frozenset({
    "add", "sub", "mul", "div", "min", "max", "clamp", "floor", "ceil",
    "count", "get", "var", "const", "literal",
    "player_stat", "player_property", "card_prop", "card_property",
    "equipment_prop", "equipment_property", "equipment_count_targeting",
    "zone_count", "zone_random_ids", "hand_full", "status_stack",
    "last_damage", "damage_amount", "damage_source", "event_value", "target_player",
})

# 条件算子（``check_v2_condition``；只能出现在 ``condition`` / ``run_if`` /
# ``unless`` 这些门控位置）。
CONDITION_OPS = frozenset({
    "and", "or", "not", "compare", "var_compare",
    "has_status", "has_status_named", "has_tag", "card_has_tag", "zone_exists",
})

# 事件时点与声明键：卡数据 ``events`` 里的钩子名，以及引擎 ``_EFFECT_ALIASES``
# 直接改写成实现名的声明写法（``damage`` → ``deal_damage`` 等）。
EVENT_HOOK_OPS = frozenset({
    "on_any_turn_start", "on_damage_taken", "on_discard_owner_turn_start",
    "on_enemy_turn_start", "on_equipment_destroy", "on_equipment_trigger",
    "on_hand_owner_turn_start", "on_hand_owner_turn_end",
    "on_owner_turn_start", "on_owner_turn_end", "on_target_turn_start",
    "damage",
})

# 分类的展示顺序（统计、参数表、报告都用这一份，别在别处再写一遍）。
LOGIC_OP_GROUPS = (
    ("真原子（引擎 `_atomic_*` 实现）", ENGINE_ATOM_OPS),
    ("运行时原生步骤（`run_v2_step`）", RUNTIME_STEP_OPS),
    ("表达式算子（`eval_v2_value`）", EXPRESSION_OPS),
    ("条件算子（`check_v2_condition`）", CONDITION_OPS),
    ("事件与声明键（`events` / `_EFFECT_ALIASES`）", EVENT_HOOK_OPS),
)


def logic_op_group(op: str) -> str:
    """返回 op 属于哪一类（``LOGIC_OP_GROUPS`` 的标签）；不在登记表里返回 ``""``。"""

    for label, names in LOGIC_OP_GROUPS:
        if op in names:
            return label
    return ""


def logic_op_groups(*, include_empty: bool = True) -> Dict[str, set]:
    """``{类名: 该类的登记名集合}``；默认保留空类，方便统计与对账。"""

    out: Dict[str, set] = {}
    for label, names in LOGIC_OP_GROUPS:
        members = set(names) & _CORE_LOGIC_OPS
        if members or include_empty:
            out[label] = members
    return out


# 五类必须恰好铺满登记表（Round 25 起 `tools/atom_parameter_table.py --check`
# 会把这个不变量当失败项；这里只留一份机器可读的差值）。
UNCLASSIFIED_LOGIC_OPS = frozenset(
    _CORE_LOGIC_OPS
    - (
        set(ENGINE_ATOM_OPS)
        | set(RUNTIME_STEP_OPS)
        | set(EXPRESSION_OPS)
        | set(CONDITION_OPS)
        | set(EVENT_HOOK_OPS)
    )
)

# ---------------------------------------------------------------------------
# Round 28 / 方案 A：伤害族词汇表（不合并原子，只统一"名字"）
#
# ``deal_damage``（攻击管线：吃力量/裂变/精准/暴击，走 ``deal_attack_damage``）
# 与 ``direct_damage``（直伤管线：不吃数值修正，走 ``_deal_direct_damage``）
# 仍是两个原子；这里只登记：
#
#   * 每个伤害族原子跑的是哪条管线（``DAMAGE_ATOM_PIPELINES``）；
#   * 每个参数适用哪条管线、有没有等价旧名、默认值差异（``DAMAGE_PARAM_PIPELINES``）。
#
# 两份表都是**声明性的**：校验器用它给"参数写错管线"的友好提示
# （``damage_pipeline_warnings``），``tools/atom_parameter_table.py`` 用它生成
# 《原子参数表》的"适用管线"列。表里没有的键一律不猜：新参数要么登记，
# 要么被参数表的 ``--check`` 显式报"伤害族参数未登记"。
# ---------------------------------------------------------------------------

DAMAGE_PIPELINE_ATTACK = "attack"
DAMAGE_PIPELINE_DIRECT = "direct"

# op → 它实际跑的伤害管线。别名与规范名同管线。
DAMAGE_ATOM_PIPELINES = {
    # 攻击管线
    "deal_damage": DAMAGE_PIPELINE_ATTACK,
    "ricochet_attack": DAMAGE_PIPELINE_ATTACK,
    "damage": DAMAGE_PIPELINE_ATTACK,
    # 直伤管线
    "direct_damage": DAMAGE_PIPELINE_DIRECT,
    "lose_health": DAMAGE_PIPELINE_DIRECT,
    # Round 43 / 批次 AG：``counter_pending_attack_damage`` 已删除（响应上下文里的
    # first_hit_damage + direct_damage 组合替代），所以这里不再登记它的管线；
    # 它的两个专用参数 ``ratio`` / ``multiplier`` 也从参数词汇表里撤下。
}

DAMAGE_PIPELINE_LABELS = {
    DAMAGE_PIPELINE_ATTACK: "攻击管线",
    DAMAGE_PIPELINE_DIRECT: "直伤管线",
}
DAMAGE_PIPELINE_BOTH_LABEL = "两条管线"

# 参数名 → 适用管线 + 等价别名 + 口径说明。
# ``pipelines`` 是 (DAMAGE_PIPELINE_ATTACK, DAMAGE_PIPELINE_DIRECT) 的子集。
DAMAGE_PARAM_PIPELINES = {
    # ---- 两条管线共用（同一个名字、同一份语义）----
    "target": {
        "pipelines": (DAMAGE_PIPELINE_ATTACK, DAMAGE_PIPELINE_DIRECT),
        "note": "选择器按集合解析（all / 列表 / 广域快照）",
    },
    "amount": {
        "pipelines": (DAMAGE_PIPELINE_ATTACK, DAMAGE_PIPELINE_DIRECT),
        "note": "运行时默认 0；引擎默认 6（deal_damage）/ 1（direct_damage）；本表标 ⚠，见附录 C",
    },
    "hits": {
        "pipelines": (DAMAGE_PIPELINE_ATTACK, DAMAGE_PIPELINE_DIRECT),
        "note": "段数（Round 30 起也是 deal_damage_multi 的替代：多段伤害 = 一条 deal_damage + hits）",
    },
    "inherit_extra_hits": {
        "pipelines": (DAMAGE_PIPELINE_ATTACK, DAMAGE_PIPELINE_DIRECT),
        "aliases": ("use_card_extra_hits",),
        "note": "子瓣继承；默认值保持各自现状——攻击 True / 直伤 False",
    },
    "on_hit": {
        "pipelines": (DAMAGE_PIPELINE_ATTACK, DAMAGE_PIPELINE_DIRECT),
        "note": "每次命中的回调步骤（攻击侧每段、直伤侧每次结算）",
    },
    "on_hit_once": {
        "pipelines": (DAMAGE_PIPELINE_ATTACK, DAMAGE_PIPELINE_DIRECT),
        "note": "每个目标只跑一次的回调步骤",
    },
    "log": {
        "pipelines": (DAMAGE_PIPELINE_ATTACK, DAMAGE_PIPELINE_DIRECT),
        "note": "步骤自带战报：false = 不打印本步骤那一行，字符串 = 模板",
    },
    "silent": {
        "pipelines": (DAMAGE_PIPELINE_ATTACK, DAMAGE_PIPELINE_DIRECT),
        "aliases": ("no_log", "hide_log"),
        "note": "silent:true == log:false；只静默步骤自带战报，攻击管线每次命中的结算行仍由伤害管线打印",
    },
    "source": {
        "pipelines": (DAMAGE_PIPELINE_ATTACK, DAMAGE_PIPELINE_DIRECT),
        "note": "攻击=攻击者选择器；直伤=选择器或来源文案（不像选择器时当文案），文案优先写 source_text",
    },
    # ---- 仅攻击管线 ----
    "is_precision": {
        "pipelines": (DAMAGE_PIPELINE_ATTACK,),
        "aliases": ("precision",),
        "note": "精准（消耗闪避）；攻击管线专有",
    },
    "precognition": {"pipelines": (DAMAGE_PIPELINE_ATTACK,), "note": "本次出牌临时精准"},
    "force_crit": {"pipelines": (DAMAGE_PIPELINE_ATTACK,), "note": "强制暴击"},
    "no_luck_crit": {"pipelines": (DAMAGE_PIPELINE_ATTACK,), "note": "不吃幸运的暴击"},
    "crit_bonus_multiplier": {"pipelines": (DAMAGE_PIPELINE_ATTACK,), "note": "暴击倍率加成"},
    "crit_bonus_damage": {"pipelines": (DAMAGE_PIPELINE_ATTACK,), "note": "暴击额外伤害"},
    "ignore_untargetable": {"pipelines": (DAMAGE_PIPELINE_ATTACK,), "note": "无视无法选定"},
    "power_once": {"pipelines": (DAMAGE_PIPELINE_ATTACK,), "note": "只在第一段算力量"},
    "on_crit": {"pipelines": (DAMAGE_PIPELINE_ATTACK,), "note": "暴击回调（攻击侧独有）"},
    "bounce_amount": {"pipelines": (DAMAGE_PIPELINE_ATTACK,), "note": "ricochet_attack 弹射伤害"},
    "bounce_hits": {"pipelines": (DAMAGE_PIPELINE_ATTACK,), "note": "ricochet_attack 弹射段数"},
    "bounces": {
        "pipelines": (DAMAGE_PIPELINE_ATTACK,),
        "aliases": ("repeats",),
        "note": "ricochet_attack 弹射次数",
    },
    "bounces_from_positive_hits": {"pipelines": (DAMAGE_PIPELINE_ATTACK,), "note": "弹射次数取主伤害的命中段数"},
    "inherit_bounce_extra_hits": {"pipelines": (DAMAGE_PIPELINE_ATTACK,), "note": "弹射段数是否继承子瓣"},
    "allow_self": {"pipelines": (DAMAGE_PIPELINE_ATTACK,), "note": "ricochet_attack 是否允许弹到自己"},
    "exclude_previous": {"pipelines": (DAMAGE_PIPELINE_ATTACK,), "note": "ricochet_attack 不连续打同一个目标"},
    "precision_inherit": {"pipelines": (DAMAGE_PIPELINE_ATTACK,), "note": "ricochet_attack 是否继承精准"},
    # Round 42 / 批次 AF：``heal`` / ``heal_percent``（别名 ``ratio``）是
    # ``lifesteal_damage`` 的专有参数，``base`` / ``per_stack`` / ``stack_name`` /
    # ``max_stacks`` 是 ``triangle_damage`` 的专有参数——四个 op 一起删除后这六条
    # 参数登记也一并撤销（回复量改用 ``health_op`` 的 ``amount`` 表达式，
    # 层数改用 ``player_var_change`` 的 ``name`` / ``value``）。
    # Round 30 / 批次 Y：``times`` 随 ``deal_damage_multi`` 一起删除——它是那个
    # 原子独有的旧参数名，规范写法 ``deal_damage`` 只读 ``hits``。
    # ---- 仅直伤管线 ----
    "damage_type": {
        "pipelines": (DAMAGE_PIPELINE_DIRECT,),
        "note": "伤害类型（physical/magic/…）；直伤专有——攻击管线固定按物理攻击结算",
    },
    "damage_tag": {
        "pipelines": (DAMAGE_PIPELINE_DIRECT,),
        "note": "伤害标签（gtn:battery 等）；直伤专有",
    },
    "source_text": {
        "pipelines": (DAMAGE_PIPELINE_DIRECT,),
        "aliases": ("source_name", "label"),
        "note": "战报来源文案，三级回落 source_text→source_name→label；Round 28 起引擎路径同样认这一串",
    },
    "mode": {
        "pipelines": (DAMAGE_PIPELINE_DIRECT,),
        "aliases": ("damage_mode",),
        "note": "伤害步骤的共享键（Round 43 删除 counter_pending_attack_damage 后，由其它"
                "直接写 mode 的伤害步骤继续读；旧写法里的 attack 值请改用 deal_damage）",
    },
    # ---- 等价别名的登记项（与上面 canonical 项同管线；写在卡数据里照跑）----
    "precision": {
        "pipelines": (DAMAGE_PIPELINE_ATTACK,),
        "canonical": "is_precision",
        "note": "is_precision 的等价别名",
    },
    "use_card_extra_hits": {
        "pipelines": (DAMAGE_PIPELINE_ATTACK, DAMAGE_PIPELINE_DIRECT),
        "canonical": "inherit_extra_hits",
        "note": "inherit_extra_hits 的等价别名（Round 28 起卡数据已迁到统一名）",
    },
    "no_log": {
        "pipelines": (DAMAGE_PIPELINE_ATTACK, DAMAGE_PIPELINE_DIRECT),
        "canonical": "silent",
        "note": "silent 的等价别名",
    },
    "hide_log": {
        "pipelines": (DAMAGE_PIPELINE_ATTACK, DAMAGE_PIPELINE_DIRECT),
        "canonical": "silent",
        "note": "silent 的等价别名",
    },
    "source_name": {
        "pipelines": (DAMAGE_PIPELINE_DIRECT,),
        "canonical": "source_text",
        "note": "source_text 的等价别名（三级回落第二级）",
    },
    "label": {
        "pipelines": (DAMAGE_PIPELINE_DIRECT,),
        "canonical": "source_text",
        "note": "source_text 的等价别名（三级回落第三级）",
    },
    "damage_mode": {
        "pipelines": (DAMAGE_PIPELINE_DIRECT,),
        "canonical": "mode",
        "note": "mode 的等价别名",
    },
    "repeats": {
        "pipelines": (DAMAGE_PIPELINE_ATTACK,),
        "canonical": "bounces",
        "note": "bounces 的等价别名（ricochet_attack）",
    },
}

# 等价别名 → 统一名（只用于提示文案，运行时别名表仍在 mod_runtime_v2）。
DAMAGE_PARAM_ALIAS_TARGET = {
    "precision": "is_precision",
    "use_card_extra_hits": "inherit_extra_hits",
    "no_log": "silent",
    "hide_log": "silent",
    "source_name": "source_text",
    "label": "source_text",
    "damage_mode": "mode",
    "repeats": "bounces",
}


def damage_atom_pipeline(op: str) -> str:
    """这个 op 跑哪条伤害管线；不是伤害族返回 ""。"""

    return DAMAGE_ATOM_PIPELINES.get(str(op), "")


def damage_param_pipelines(param: str) -> tuple:
    """这个参数适用哪条管线；未登记返回 ()。"""

    entry = DAMAGE_PARAM_PIPELINES.get(str(param))
    return tuple(entry.get("pipelines") or ()) if entry else ()


def damage_param_label(param: str) -> str:
    """参数的"适用管线"标签：攻击管线 / 直伤管线 / 两条管线 / ""。"""

    pipelines = damage_param_pipelines(param)
    if not pipelines:
        return ""
    if len(pipelines) >= 2:
        return DAMAGE_PIPELINE_BOTH_LABEL
    return DAMAGE_PIPELINE_LABELS[pipelines[0]]


def damage_pipeline_hint(op: str, param: str) -> str:
    """只提示不报错：参数与所在管线不匹配时返回一句中文说明，否则 ""。

    例：``deal_damage`` 里写 ``damage_type``（直伤专有）——运行时与引擎都会
    忽略它，所以这里给一句显式提示，帮助卡数据作者发现写错管线。
    """

    pipeline = damage_atom_pipeline(op)
    if not pipeline:
        return ""
    param = str(param)
    entry = DAMAGE_PARAM_PIPELINES.get(param)
    if entry is None:
        return ""
    pipelines = tuple(entry.get("pipelines") or ())
    if not pipelines or pipeline in pipelines or len(pipelines) >= 2:
        return ""
    canonical = str(entry.get("canonical") or DAMAGE_PARAM_ALIAS_TARGET.get(param, param))
    alias_note = f"（{param} 是 {canonical} 的等价别名）" if canonical != param else ""
    return (
        f"参数 {param}{alias_note} 只适用于{DAMAGE_PIPELINE_LABELS[pipelines[0]]}；"
        f"`{op}` 走的是{DAMAGE_PIPELINE_LABELS[pipeline]}，它会被忽略"
    )


_DAMAGE_STEP_CONTAINERS = (
    "steps", "body", "then", "else", "on_hit", "on_hit_once", "on_crit", "on_cancel",
)


def iter_step_dicts(node: Any):
    """深度优先产出 payload 里所有步骤 dict（嵌套容器口径与运行时一致）。"""

    if isinstance(node, list):
        for item in node:
            yield from iter_step_dicts(item)
        return
    if not isinstance(node, dict):
        return
    op = node.get("op") or node.get("type")
    if isinstance(op, str) and op:
        yield node
        params = node.get("params") if isinstance(node.get("params"), dict) else None
        for container in (node, params):
            if not isinstance(container, dict):
                continue
            for key in _DAMAGE_STEP_CONTAINERS:
                child = container.get(key)
                if isinstance(child, (list, dict)):
                    yield from iter_step_dicts(child)
        return
    for key, value in node.items():
        if key in _DAMAGE_STEP_CONTAINERS or isinstance(value, (dict, list)):
            yield from iter_step_dicts(value)


def damage_pipeline_warnings(payload: Any) -> list:
    """扫一遍 v2 payload，收集"参数写错管线"的友好提示（warning 级，不是错误）。"""

    out: list = []
    seen = set()
    for step in iter_step_dicts(payload):
        op = str(step.get("op") or step.get("type") or "")
        if not damage_atom_pipeline(op):
            continue
        params = step.get("params") if isinstance(step.get("params"), dict) else step
        if not isinstance(params, dict):
            continue
        for key in params:
            hint = damage_pipeline_hint(op, str(key))
            if hint and (op, str(key)) not in seen:
                seen.add((op, str(key)))
                out.append(f"{op}.{key}: {hint}")
    return out

# Round 25：被清理的卡专用旧 op 的"家族指路"文案。替代写法是一串通用步骤
# 组合（不是一个名字），完整对照表在 docs/引擎原子与数据步骤清单.md §8.2。
_FAMILY_HINT = {
    family: f"通用步骤组合（见 docs/引擎原子与数据步骤清单.md §8.2「{family}」）"
    for family in ("Hel", "Arctic", "Bio", "Jungle", "Ocean", "Void")
}


# Round 20: 清理掉的原子（实现与登记都已删除）。老包如果还写这些名字，
# 校验层会给出"已移除 + 替代写法"，运行时 v2 路径也会抛同样的错误，
# 不会静默变成"什么也没发生"。
#
# ``None`` 表示没有等价替代（原本就是空实现或未实现过的声明性名字）。
REMOVED_ATOMIC_OPS = {
    # Round 43 / 批次 AG（"能组合就删"续扫）：3 个原子逐个验证后删除，
    # 替代写法如下。判定证据与"迁移前 / 迁移后"对拍见 `.codex-tmp/round43/rd43.md`。
    #   * 空步骤：实现就是 ``return None``，机制由装备标签承载。
    "plank_immunity": '（无等价步骤：直接删掉这一步）木板机制由装备标签 '
                      'blocks_cheap_attacks 承载——_deal_attack_damage 每段伤害前读 '
                      '_equipment_flag_or_legacy_mark(target, "blocks_cheap_attacks")，'
                      '再看攻击牌是"荆棘牌且实际 E 消耗 ≤ 1"',
    #   * 费用修正：写的字段本来就在 card_prop_change 的白名单属性里。
    "modify_next_cost": '{"op":"card_prop_add_to_zone","target":"target","zone":"hand",'
                        '"property":"temp_heavy_value","amount":1,"require_selectable":false,'
                        '"silent":true}（加费；减费换 property:"temp_swift_value"；'
                        'temp_swift/temp_heavy 标签同步在 _set_card_property_value 里）'
                        '（旧名 increase_next_cost / reduce_next_cost 也改指这条）',
    #   * 反击：反弹输入量在响应上下文里，数据用取值表达式读。
    "counter_pending_attack_damage": '{"op":"if_else","condition":{"op":"compare",'
                                     '"a":{"op":"var","name":"first_hit_damage"},"operator":">","b":0},'
                                     '"then":[{"op":"direct_damage","target":"target",'
                                     '"amount":{"op":"ceil","value":{"op":"mul","a":0.6,'
                                     '"b":{"op":"var","name":"first_hit_damage"}}},'
                                     '"damage_type":"physical","source_text":"盐"}]}'
                                     '（``_run_v2_card_event`` 把 extra_context 并进 '
                                     'context["vars"]，first_hit_damage / first_damage / '
                                     'incoming_damage_parts 都在里面）',
    # Round 42 / 批次 AF（极端收敛："能组合就删"）：14 个原子逐个定论后删除，
    # 替代写法如下。判定依据与 A/B 见 `.codex-tmp/round42/rd42.md`。
    #
    #   * 六条"只播报"的步骤：它们写的字段在引擎、卡数据、序列化与客户端里
    #     **零读取方**，实际行为就是那一行默认战报，所以替代写法是一行 ``log``。
    "transform_card": '{"op":"log","message":"变换<牌名>效果触发"}（原实现只播报；真正的变换是 transform_cards）',
    "modify_damage": '{"op":"log","message":"修改伤害公式：<formula>"}（formula 全仓库无读取方）',
    "emit_event": '{"op":"log","message":"广播事件：<事件名>"}（事件总线无订阅方；要静默写 log:false）',
    "global_mult": '{"op":"log","message":"全场伤害倍率x2"}（global_damage_mult/global_heal_mult/global_cost_mult 零读取方）',
    "turn_mod_add": '{"op":"log","message":"每回合能量回复+1"}（e_regen_mod/m_regen_mod/draw_mod 零读取方）',
    "mark_self_damage_source": '{"op":"log","message":"<目标>下次伤害来源标记为自身"}（self_damage_next 零读取方）',
    #
    #   * 五条"写的字段已有既有写入口"的步骤（官方包里已有同样的数据写法）：
    "activate_corruption": '{"op":"equipment_prop_set","equipment":{"ref":"current_equipment"},"property":"corruption_active","value":1}'
                           '（vanilla:corruption 的卡数据就是这么写的）',
    "counter_equip_protect": '{"op":"player_prop_change","mode":"add","property":"equipment_protection","target":"self","amount":1}',
    "equip_protection": '{"op":"player_prop_change","mode":"add","property":"equipment_protection","target":"self","amount":1}'
                        '（counter_equip_protect 的旧别名，与规范名一起退役）',
    "card_counter": '{"op":"card_prop_change","mode":"add","property":"play_count","amount":1,"card":{"ref":"current_card"}}'
                    '（equip_turns 同理换成 property:"equip_turns"；reset = 两条 mode:"set" value:0）',
    "fission": '{"op":"card_prop_change","mode":"add","property":"fission_level","amount":1,"card":{"ref":"selected_card"}}'
               '（clamp_card_layer 钳位与 fission_count 同步都在 _set_card_property_value 里；'
               '选牌窗口写 request(type:"card")）',
    #
    #   * 三条"两步通用组合"（官方包 vanilla:triangle / vanilla:fang / vanilla:fusion
    #     的卡数据就是这些写法）：
    "lifesteal_damage": '{"op":"deal_damage","target":"enemy","amount":8} + '
                        '{"op":"if_else","condition":{"op":"compare","a":{"op":"last_damage"},"operator":">","b":0},'
                        '"then":[{"op":"health_op","mode":"heal","target":"self","amount":'
                        '{"op":"div","a":{"op":"mul","a":{"op":"last_damage"},"b":8},"b":10}}]}'
                        '（vanilla:fang 的写法：先 deal_damage，再按 last_damage 的比例回复；'
                        '固定回复量就把 amount 换成常量）',
    "triangle_damage": '{"op":"deal_damage","target":"target","amount":{"op":"add","a":6,"b":'
                       '{"op":"mul","a":3,"b":{"op":"var","name":"三角形层数","target":"self"}}}} + '
                       '{"op":"if_else","condition":{"op":"compare","a":{"op":"last_damage"},"operator":">","b":0},'
                       '"then":[{"op":"player_var_change","mode":"set","target":"self","name":"三角形层数",'
                       '"value":{"op":"min","a":4,"b":{"op":"add","a":{"op":"var","name":"三角形层数","target":"self"},"b":1}}}]}'
                       '（vanilla:triangle 的写法：层数读 var、上限用 min、写完由 '
                       '_sync_custom_var_alias 同步 triangle_stacks；状态免疫期间 var 读取自动返回 0）',
    #   * 两条"伞原子"的续接（它们自己也是 Round 37/38 的合并产物，这里一起删）：
    "action_filter": '（按 mode 拆成既有原子）block_own → '
                     '{"op":"player_prop_change","mode":"set","property":"shovel_active","value":1,"target":"self"}；'
                     'block_type → {"op":"player_prop_change","mode":"set","property":"attack_blocked","target":"enemy",'
                     '"value":{"op":"max","a":{"op":"player_property","property":"attack_blocked","target":"enemy"},"b":1}}；'
                     'force_type → 同上 property:"attack_only"；'
                     'negate → {"op":"log","message":"<目标>的<牌型>牌将失效"}（negate_next 零读取方）',
    "fusion": '见官方包 vanilla:fusion 的卡数据（request(type:"card", multi:true, same_name:true) 选 2 张同名攻击牌 → '
              '一组 player_var_change 初始化 __聚变层数合计 / __裂变层数最大值 … → for_each 逐张读 card_prop 求合计与最大值 → '
              'card_prop_change 写回保留的那张 → move_card 把其余张弃掉）；'
              '旧原子里的 count/max_count/fusion_uses_two_cards 就是这几步的参数',
    # Round 39 / 批次 AE：第三只眼下沉为 tag_op(when_tag/unless_tag)。
    "third_eye_precision_or_hidden": "{\"op\": \"tag_op\", \"action\": \"add\", \"card\": \"selected_card\", \"tag\": \"stealth\", \"when_tag\": \"precision\", \"log\": false}",

    # Round 41 / 批次 AE-5（收尾）：5 个长尾原子逐个定论后删除，替代写法如下。
    #   * 护目镜：视图权限下沉成装备标签 ``continuous_deck_reveal``，
    #     引擎按 ``_goggles_view_targets_for`` 读装备的 ``effect_target``。
    "goggles_enable": (
        '{"flags":["continuous_deck_reveal"]} + '
        '{"op":"equipment_op","mode":"place","effect_target":"choice_target"}'
        '（装备在场即生效，与 garden:antennae 的 continuous_hand_reveal 同一套口径）'
    ),
    #   * 卡牌聚变倍率 → card_prop_change(mode:"mul")
    "card_damage_multiply": (
        '{"op":"card_prop_change","mode":"mul","property":"fusion_level",'
        '"multiplier":2,"card":{"ref":"current_card"}}'
    ),
    #   * 倒计时 → "写初值 + 定时减一"两条通用步骤
    "countdown_var": (
        '{"op":"player_var_change","mode":"set","name":"timer","value":3,"target":"self"} + '
        '{"op":"delayed_effect","mode":"timed","trigger":"target_turn_start","duration":3,'
        '"target":"self","body":[{"op":"player_var_change","mode":"sub","name":"timer",'
        '"value":1,"target":"self"}]}'
    ),
    #   * 卡内计数 → card_var_change（写 card.custom_vars，可被取值表达式与 to_dict 读到）
    "create_counter": (
        '{"op":"card_var_change","mode":"add","name":"counter1","value":1,'
        '"card":{"ref":"current_card"}}'
    ),
    #   * 声明响应是返回 None 的空占位步骤，没有等价写法（反制窗口由卡数据
    #     ``response_trigger`` 与引擎响应系统承载）。
    "response_declare": "",

    # Round 24（C 类同形小原子合并）：下面这批名字的形状几乎相同，差异都能被
    # 参数覆盖，已合并成右边给出的规范写法。旧数据写旧名会在校验层与运行时
    # 拿到"已移除 + 替代写法"的显式报错（不静默）。
    #   * 状态三兄弟 → status_add_named（log 模板复刻旧默认战报）
    "poison": '{"op":"status_op","action":"add","status":"poison","target":"enemy","amount":4,"log":"{target}+{amount}中毒"}',
    "burn": '{"op":"status_op","action":"add","status":"burn","target":"enemy","amount":4,"log":"{target}+{amount}灼烧"}',
    "toxic": '{"op":"status_op","action":"add","status":"toxic","target":"enemy","amount":1,"log":"{target}+{amount}淬毒"}',
    "apply_poison": '{"op":"status_op","action":"add","status":"poison","target":"enemy","amount":1,"log":"{target}+{amount}中毒"}',
    "apply_burn": '{"op":"status_op","action":"add","status":"burn","target":"enemy","amount":1,"log":"{target}+{amount}灼烧"}',
    "apply_toxic": '{"op":"status_op","action":"add","status":"toxic","target":"enemy","amount":1,"log":"{target}+{amount}淬毒"}',
    #   * 护甲/闪避族 → player_stat_change（mode 选 add/remove/set，stat 选 armor/dodge）
    "add_armor": '{"op":"player_stat_change","mode":"add","stat":"armor","target":"self","amount":2}',
    "gain_armor": '{"op":"player_stat_change","mode":"add","stat":"armor","target":"self","amount":2}',
    "remove_armor": '{"op":"player_stat_change","mode":"remove","stat":"armor","target":"enemy","amount":2}',
    "set_armor": '{"op":"player_stat_change","mode":"set","stat":"armor","target":"self","amount":0}',
    "dodge_permanent": '{"op":"player_stat_change","mode":"add","stat":"dodge","target":"self","amount":1}',
    "gain_dodge": '{"op":"player_stat_change","mode":"add","stat":"dodge","target":"self","amount":1}',
    "dodge_this": '{"op":"player_stat_change","mode":"add","stat":"dodge","target":"self","amount":1,"log":"{target}获得1层闪避（针对本次攻击）"}',
    #   * 清状态族 → clear_statuses(preset=...)
    "clear_buffs": '{"op":"status_op","action":"clear","preset":"buffs","target":"self"}',
    "clear_debuffs": '{"op":"status_op","action":"clear","preset":"debuffs","target":"self"}',
    "clear_all_effects": '{"op":"status_op","action":"clear","preset":"all","target":"self"}',
    #   * 每回合修正族 → turn_mod_add（Round 42 / 批次 AF 起 turn_mod_add 本身也
    #     删除了：它写的 e_regen_mod/m_regen_mod/draw_mod 零读取方，替代写法是
    #     ``{"op":"log",…}``）
    "mod_e_regen": '{"op":"log","message":"每回合能量回复+1"}（turn_mod_add 已删除：字段零读取方）',
    "mod_m_regen": '{"op":"log","message":"每回合魔力回复+1"}（turn_mod_add 已删除：字段零读取方）',
    "mod_draw": '{"op":"log","message":"每回合抽牌数+1"}（turn_mod_add 已删除：字段零读取方）',
    #   * 资源消耗族 → spend_resource（Round 31：resource_spend 也已删除，
    #     ``spend_resource`` 收 ``target``，要旧默认战报就显式写 log）
    "cost_e": '{"op":"resource_op","resource":"e","mode":"spend","amount":1,"target":"self","log":"{target}消耗{amount}E"}',
    "cost_m": '{"op":"resource_op","resource":"m","mode":"spend","amount":1,"target":"self","log":"{target}消耗{amount}M"}',
    #   * 全场倍率族 → global_mult（Round 42 / 批次 AF 起 global_mult 本身也删除了：
    #     三个 global_*_mult 字段零读取方，替代写法是一行 ``log``）
    "global_damage_mult": '{"op":"log","message":"全场伤害倍率x2"}（global_mult 已删除：字段零读取方）',
    "global_heal_mult": '{"op":"log","message":"全场治疗倍率x2"}（global_mult 已删除：字段零读取方）',
    "global_cost_mult": '{"op":"log","message":"全场费用倍率x2"}（global_mult 已删除：字段零读取方）',
    #   * 卡内标签族 → add_tag(mode=...)
    "tag_add_named": '{"op":"tag_op","action":"add","card":{"ref":"current_card"},"tag":"exile","log":false}',
    "tag_remove_named": '{"op":"tag_op","action":"remove","card":{"ref":"current_card"},"tag":"exile"}',
    #   * 装备减抽族 → draw 的 modifiers（Round 32 / 批次 AA：``equip_reduce_draw``
    #     本身也并进 ``draw`` 了）
    "equip_reduce_own_draw": '{"op":"draw","count":0,"hooks":false,"target":"self","modifiers":[{"type":"sluggish","amount":1,"target":"self"}]}',
    "equip_reduce_enemy_draw": '{"op":"draw","count":0,"hooks":false,"target":"self","modifiers":[{"type":"sluggish","amount":1,"target":"enemy"}]}',
    #   （Round 38 / 批次 AD-3 曾把它们并进 ``action_filter(mode:"block_type")``；
    #   Round 42 / 批次 AF 又把 ``action_filter`` 删了，这里同步成"玩家属性 +
    #   max 表达式"的最终写法——``attack_blocked`` 也是官方包 ``sewers:poo`` /
    #   ``ocean:jelly`` 在用的数据写法。）
    "block_enemy_attacks": (
        '{"op":"player_prop_change","mode":"set","property":"attack_blocked","target":"enemy",'
        '"value":{"op":"max","a":{"op":"player_property","property":"attack_blocked","target":"enemy"},"b":1}}'
    ),
    "counter_block_enemy_attacks": (
        '{"op":"player_prop_change","mode":"set","property":"attack_blocked","target":"enemy",'
        '"value":{"op":"max","a":{"op":"player_property","property":"attack_blocked","target":"enemy"},"b":1}}'
    ),
    "counter_dodge": '{"op":"player_stat_change","mode":"add","stat":"dodge","target":"self","amount":1}',
    "counter_nazar": '{"op":"status_op","action":"add","status":"nazar","target":"self","amount":2}',
    "counter_negate_skill": '{"op":"player_prop_change","mode":"set","property":"negate_next_skill","target":"self","value":1}',
    "counter_set_invincible_then_die": '{"op":"health_op","mode":"fatal","kind":"invincible_die"}',
    "equip_add_toxic": '{"op":"status_op","action":"add","status":"toxic","target":"enemy","amount":1,"log":"{target}+{amount}淬毒"}',
    "equip_on_destroy_remove_poison_damage": None,
    "equip_reduce_enemy_e": '{"op":"player_prop_change","mode":"add","property":"overload","target":"enemy","amount":1}',
    "equip_reduce_own_e": '{"op":"player_prop_change","mode":"add","property":"overload","target":"self","amount":1}',
    "equip_set_health": '{"op":"health_op","mode":"set","target":"self","amount":60}',
    "equip_sponge": '{"op":"player_prop_change","mode":"set","property":"sponge_active","target":"target","value":1}',
    # Round 42 / 批次 AF：``action_filter`` 已删除，改成"玩家属性 + max 表达式"。
    "force_enemy_attacks_only": (
        '{"op":"player_prop_change","mode":"set","property":"attack_only","target":"enemy",'
        '"value":{"op":"max","a":{"op":"player_property","property":"attack_only","target":"enemy"},"b":1}}'
    ),
    "random_move_card_to_hand": '{"op":"move_card","mode":"random","source_zone":"discard","target_zone":"hand","count":1,"target":"self"}',
    "move_random_card_to_hand": '{"op":"move_card","mode":"random","source_zone":"discard","target_zone":"hand","count":1,"target":"self"}',
    "desert_wind_schedule": None,
    "garden_mecha_antennae": '{"op":"reveal","mode":"enemy_hand","target":"target"}',

    # Round 25（登记残留清理）：下面这批卡专用旧 op 在 Round 1/2 就被改写成
    # 通用步骤，卡数据 0 引用，但登记一直没删。它们在 ``_CORE_LOGIC_OPS`` 里的
    # 位置已经注销（写出来是显式报错，不静默）；替代写法按家族列在
    # ``docs/引擎原子与数据步骤清单.md`` §8.2，这里给一句可读的指路。
    "hel_add_luck": _FAMILY_HINT["Hel"],
    "hel_apply_blazing_fire": _FAMILY_HINT["Hel"],
    "hel_blood_dice": _FAMILY_HINT["Hel"],
    "hel_bugatti_draw": _FAMILY_HINT["Hel"],
    "hel_card_attack": _FAMILY_HINT["Hel"],
    "hel_chip_attack": _FAMILY_HINT["Hel"],
    "hel_fire_by_equipment": _FAMILY_HINT["Hel"],
    "hel_lucky_attack": _FAMILY_HINT["Hel"],
    "hel_magic_clover_trigger": _FAMILY_HINT["Hel"],
    "hel_magic_dice_attack": _FAMILY_HINT["Hel"],
    "hel_magic_gunpowder": _FAMILY_HINT["Hel"],
    "hel_trigger_fire_once": _FAMILY_HINT["Hel"],
    "arctic_apply_frost": _FAMILY_HINT["Arctic"],
    "arctic_ice": _FAMILY_HINT["Arctic"],
    "arctic_icicle_shuffle_discard": _FAMILY_HINT["Arctic"],
    "arctic_nuke": _FAMILY_HINT["Arctic"],
    "arctic_snowflake_copy": _FAMILY_HINT["Arctic"],
    "bio_add_shield_conversion": _FAMILY_HINT["Bio"],
    "bio_clear_poison_fire": _FAMILY_HINT["Bio"],
    "jungle_add_maple_to_hand": _FAMILY_HINT["Jungle"],
    "jungle_dianthus_record_use": _FAMILY_HINT["Jungle"],
    "jungle_dianthus_restore_power": _FAMILY_HINT["Jungle"],
    "jungle_monstera_heal_team": _FAMILY_HINT["Jungle"],
    "ocean_add_blood_debt": _FAMILY_HINT["Ocean"],
    "ocean_dead_leaf_slow_if_no_counter": _FAMILY_HINT["Ocean"],
    "ocean_discard_count_damage": _FAMILY_HINT["Ocean"],
    "ocean_random_blind_hand": _FAMILY_HINT["Ocean"],
    "ocean_sapphire_mark": _FAMILY_HINT["Ocean"],
    "ocean_status_tag_damage": _FAMILY_HINT["Ocean"],
    "void_add_card_to_deck": _FAMILY_HINT["Void"],
    "void_add_temp_heavy_to_hand": _FAMILY_HINT["Void"],
    "void_add_void_to_hand": _FAMILY_HINT["Void"],
    "void_antimatter_damage": _FAMILY_HINT["Void"],
    "void_copy_response_card": _FAMILY_HINT["Void"],
    "void_damage_all_except_self": _FAMILY_HINT["Void"],
    "void_dlc_action": _FAMILY_HINT["Void"],
    "void_exile_selected_card": _FAMILY_HINT["Void"],
    "void_exile_target_hand": _FAMILY_HINT["Void"],
    "void_give_selected_hand_flag": _FAMILY_HINT["Void"],
    "void_magic_corruption": _FAMILY_HINT["Void"],
    "void_magic_relativity_damage_end": _FAMILY_HINT["Void"],
    "void_magic_wing_damage": _FAMILY_HINT["Void"],
    "void_move_selected_card": _FAMILY_HINT["Void"],
    "void_puppeteer": _FAMILY_HINT["Void"],
    "void_quantum_randomize": _FAMILY_HINT["Void"],
    "void_satan_swap": _FAMILY_HINT["Void"],
    "void_scythe_damage": _FAMILY_HINT["Void"],
    "void_set_void_all_cards": _FAMILY_HINT["Void"],
    "void_soap_wide_strike": _FAMILY_HINT["Void"],
    "void_toggle_void_hand": _FAMILY_HINT["Void"],
    "void_transform_own_cards": _FAMILY_HINT["Void"],
    "void_turn_count_damage": _FAMILY_HINT["Void"],

    # Round 25：文档里出现过、但从没有任何实现的"保留名"（Round 15 的
    # 长尾审计就把它们记成"文档保留名"）。没有等价替代，写了就是显式报错。
    "call": None,
    "choose": None,
    "emit": None,
    "gain_resource": None,
    "mod": None,
    "ref": None,
    "sequence": None,
    "set": None,
    "stop": None,

    # Round 26（公式型原子拆分）：下面 6 个原子把"从场上算出来的数"写死在实现
    # 里（装备数 / 剩余 M / 牌堆数 / 手牌上限差）。公式已搬进卡数据，实现整个
    # 删除，旧名给"已移除 + 替代写法"的显式报错。完整对照表与 A/B 证据见
    # docs/引擎原子与数据步骤清单.md §24。
    "apply_jungle_status": (
        '{"op":"status_op","action":"add","target":"target","status":"jungle:fragile","amount":1,'
        '"log":"{target}获得{amount}层易损"}'
    ),
    "magic_grapes_damage": (
        '{"op":"direct_damage","target":"target","amount":3,'
        '"hits":{"op":"add","values":[1,{"op":"equipment_count","target":"target"}]},'
        '"source":"电击","damage_type":"magic","damage_tag":"gtn:battery"}'
    ),
    "consume_magic_for_status": (
        '[{"op":"set_var","name":"m","value":{"op":"player_stat","target":"self","stat":"magic"}},'
        '{"op":"if_else","condition":{"op":"compare","a":{"op":"var","name":"m"},"operator":">","b":0},'
        '"then":[{"op":"player_prop_set","target":"self","property":"magic","value":0},'
        '{"op":"status_op","action":"add","target":"target","status":"jungle:toxic_poison",'
        '"amount":{"op":"var","name":"m"}}]}]'
    ),
    "yin_yang_effect": (
        '[{"op":"set_var","name":"n","value":{"op":"deck_count","target":"target"}},'
        '{"op":"move_cards_to_deck","target":"target","cards":"hand","position":"bottom","silent":true},'
        '{"op":"draw","target":"target","count":{"op":"var","name":"n"}}]'
    ),
    "flower_burst": (
        '{"op":"if_else","condition":{"op":"compare","a":{"op":"equipment_prop",'
        '"equipment":"current_equipment","prop":"turns_equipped"},"operator":">=","b":1},'
        '"then":[{"op":"status_op","action":"add","target":"target","status":"poison","amount":16},'
        '{"op":"destroy_current_equipment"}]}'
    ),
    "draw_to_hand_limit": (
        '{"op":"if_else","condition":{"op":"compare","a":{"op":"sub","values":'
        '[{"op":"player_stat","target":"self","stat":"hand_limit"},'
        '{"op":"hand_count","target":"self"}]},"operator":">","b":0},'
        '"then":[{"op":"draw","target":"self","count":...,"log_amount":"requested"}]}'
    ),

    # Round 27（丢弃族：公式/随机 + 尾部取牌 → 取值表达式 + 通用步骤）：这两个
    # 原子的"手牌张数钳位 + 逐张记主动弃牌"语义与 ``move_to_discard`` 完全一致，
    # 缺的只是取值能力，已补成 ``zone_random_ids``（随机 N 张）与
    # ``zone_top_ids`` 的 ``order:"bottom"``（尾部 N 张）；记账统一走
    # ``GameEngine._discard_card_and_note``。N = 请求张数（表达式），
    # 下面两条按"默认参数"写（不写 ``count_as_active_discard`` 时默认 true）。
    "random_discard_from_hand": (
        '[{"op":"set_var","name":"count","value":0},'
        '{"op":"for_each","items":{"op":"zone_random_ids","target":"target","zone":"hand",'
        '"count":N},"as":"pick_iid","steps":['
        '{"op":"move_to_discard","card":{"ref":"card_instance","instance_id":'
        '{"op":"var","name":"pick_iid"}},"count_as_active_discard":true,"silent":true},'
        '{"op":"add_var","name":"count","value":1}]},'
        '{"op":"log","target":"target","message":"{target}随机弃置{count}张手牌"}]'
    ),
    "discard": (
        '[{"op":"for_each","items":{"op":"zone_top_ids","zone":"hand","order":"bottom",'
        '"count":N},"as":"pick_iid","steps":['
        '{"op":"move_card","zone":"discard","card":{"ref":"card_instance","instance_id":'
        '{"op":"var","name":"pick_iid"}},"count_as_active_discard":true,"silent":true}]},'
        '{"op":"log","message":"{source}丢弃{amount}张手牌","amount":N}]'
    ),

    # ------------------------------------------------------------------
    # Round 29 / 批次 X：同形对 + 前缀族 + 状态族复核后的合并
    #
    # 判"合"的每一族都满足三个条件（见 .codex-tmp/round29/rd29.md）：
    # 语义一致、差异能被参数覆盖、逐卡 A/B 等价。替换写法按"最小改动"
    # 写：``mode``/``scope``/``zone`` 覆盖原来的 op 名差异，其余参数照抄。
    # ------------------------------------------------------------------
    #   * 玩家自定义变量五兄弟 → player_var_change(mode=...)
    "var_set": '{"op":"player_var_change","mode":"set","target":"self","name":"var","value":0}',
    "var_add": '{"op":"player_var_change","mode":"add","target":"self","name":"var","value":1}',
    "var_sub": '{"op":"player_var_change","mode":"sub","target":"self","name":"var","value":1}',
    "var_mul": '{"op":"player_var_change","mode":"mul","target":"self","name":"var","value":2}',
    "var_div": '{"op":"player_var_change","mode":"div","target":"self","name":"var","value":2}',
    #   * 玩家属性写值两条 → player_prop_change(mode=...)
    "player_prop_set": '{"op":"player_prop_change","mode":"set","target":"self","property":"health","value":0}',
    "player_prop_add": '{"op":"player_prop_change","mode":"add","target":"self","property":"health","amount":1}',
    #   * 卡牌自定义变量两条 → card_var_change(mode=...)
    "card_var_set": '{"op":"card_var_change","mode":"set","card":{"ref":"current_card"},"name":"var","value":0}',
    "card_var_add": '{"op":"card_var_change","mode":"add","card":{"ref":"current_card"},"name":"var","value":1}',
    #   * 卡内计数器三兄弟 → card_counter(mode=...)（Round 42 / 批次 AF 起
    #     ``card_counter`` 本身也删除，改由卡牌属性族写 ``play_count`` /
    #     ``equip_turns``；这两个字段随后补进了 card_prop_change 的属性白名单）
    "record_play_count": '{"op":"card_prop_change","mode":"add","property":"play_count","amount":1,"card":{"ref":"current_card"}}',
    "record_equip_turns": '{"op":"card_prop_change","mode":"add","property":"equip_turns","amount":1,"card":{"ref":"current_card"}}',
    "reset_counter": '{"op":"card_prop_change","mode":"set","property":"play_count","value":0,"card":{"ref":"current_card"}} + '
                     '{"op":"card_prop_change","mode":"set","property":"equip_turns","value":0,"card":{"ref":"current_card"}}',
    #   * 耐久三兄弟 → 卡牌属性族（property:"durability"，负 amount 即扣）
    "gain_durability": '{"op":"card_prop_add","card":{"ref":"current_card"},"property":"durability","amount":1}',
    "lose_durability": '{"op":"card_prop_add","card":{"ref":"current_card"},"property":"durability","amount":-1}',
    "set_durability": '{"op":"card_prop_set","card":{"ref":"current_card"},"property":"durability","value":3}',
    #   * 摧毁装备四条（含运行时薄封装）→ destroy_equipment(mode=..., scope=...)
    "destroy_random_equip": '{"op":"equipment_op","mode":"destroy","pick":"random","scope":"target","target":"enemy"}',
    "destroy_all_equip": '{"op":"equipment_op","mode":"destroy","pick":"all","scope":"target","target":"enemy"}',
    "destroy_all_field_equip": '{"op":"equipment_op","mode":"destroy","pick":"all","scope":"field"}',
    #   * 取牌三条 → request(type:"zone")
    #     （Round 29 合并成 choose_from_zone，Round 36 / 批次 AD-1 再并进 request 伞）
    "choose_from_deck": '{"op":"request","type":"zone","zone":"deck","target":"self"}',
    "choose_from_discard": '{"op":"request","type":"zone","zone":"discard","target":"self"}',
    "choose_from_exile": '{"op":"request","type":"zone","zone":"exile","target":"self"}',
    #   * 区域移动四条 → move_card(zone=...)
    "move_to_hand": '{"op":"move_card","zone":"hand","card":{"ref":"selected_card"},"target":"self"}',
    "move_to_deck": '{"op":"move_card","zone":"deck","card":{"ref":"current_card"},"position":"top"}',
    "move_to_discard": '{"op":"move_card","zone":"discard","card":{"ref":"current_card"}}',
    "move_to_exile": '{"op":"move_card","zone":"exile","card":{"ref":"current_card"}}',

    # ------------------------------------------------------------------
    # Round 30 / 批次 Y：零用量清理（状态旧写法 + 多段伤害）
    #
    # 这一批删的都是"同一条实现换个名字"的重复语义，官方 20 个包 0 次使用、
    # 编辑器/校验器 0 依赖。旧名写出来仍走同一条"已移除 + 替代写法"报错路径，
    # 替代写法按**能逐字复刻旧默认**的最小写法给（旧状态三兄弟的差别只有
    # "未写 log 时默认播报"，补一个 ``"log":true`` 即可）。
    # ------------------------------------------------------------------
    #   * 状态旧写法三兄弟 → 规范写法 + log:true（旧默认那句战报）
    #     Round 31：``set_status`` 的替代也跟着 ``set_status_named`` 一起并进
    #     ``status_add_named(mode:"set")``。
    "add_status": '{"op":"status_op","action":"add","target":"self","status":"poison","amount":1,"log":true}',
    "set_status": '{"op":"status_op","action":"set","mode":"set","target":"self","status":"poison","amount":1,"log":true}',
    "remove_status": '{"op":"status_op","action":"remove","target":"self","status":"poison","amount":1,"log":true}',
    #   * 多段伤害两条 → deal_damage(hits=N)（Round 28 起 hits 是段数的统一名）
    "deal_damage_multi": '{"op":"deal_damage","target":"enemy","amount":6,"hits":3}',
    "damage_multi": '{"op":"deal_damage","target":"enemy","amount":6,"hits":3}',

    # ------------------------------------------------------------------
    # Round 31 / 批次 Z：真删的兼容垫片 + 真合并的六个族
    #
    # 判据（本批逐条实测）：卡数据 0 引用、编辑器/校验器 0 依赖、没有
    # getattr/字符串调度的动态引用。带参数替代的一条进本表（替代写法是完整
    # JSON），纯改名的进 RENAMED_ATOMIC_OPS。所有名字在两条执行路径上都会拿到
    # "已移除 + 请改用"的显式报错。
    # ------------------------------------------------------------------
    #   * Round 29 留的六个同名兼容垫片（本轮真删；私有调用点见报告）
    "move_to_hand": '{"op":"move_card","zone":"hand","card":{"ref":"selected_card"},"target":"self"}',
    "var_set": '{"op":"player_var_change","mode":"set","target":"self","name":"var","value":0}',
    "player_prop_set": '{"op":"player_prop_change","mode":"set","target":"self","property":"health","value":0}',
    "player_prop_add": '{"op":"player_prop_change","mode":"add","target":"self","property":"health","amount":1}',
    "card_var_set": '{"op":"card_var_change","mode":"set","card":{"ref":"current_card"},"name":"var","value":0}',
    "card_var_add": '{"op":"card_var_change","mode":"add","card":{"ref":"current_card"},"name":"var","value":1}',
    #   * 状态族：clear_status → status_remove_named(amount:"all")；
    #     set_status_named → status_add_named(mode:"set")；
    #     resolve_status_once → settle_status(reduce:N)（默认战报要显式写 log）
    "clear_status": '{"op":"status_op","action":"remove","target":"self","status":"poison","amount":"all","log":"{target}的{status}已清除"}',
    "set_status_named": '{"op":"status_op","action":"set","mode":"set","target":"self","status":"poison","amount":1,"stack":1}',
    "resolve_status_once": '{"op":"status_op","action":"settle","target":"target","status":"fire","reduce":1,"log":"{target}的灼烧结算{amount}点并减少1层"}',
    #   * 玩家状态层数族 → player_status_layers(status=untargetable|invincible)
    "set_untargetable": '{"op":"player_status_layers","status":"untargetable","target":"self","amount":1,"shovel":true}',
    "untargetable_layers": '{"op":"player_status_layers","status":"untargetable","target":"self","amount":1}',
    "set_invincible": '{"op":"player_status_layers","status":"invincible","target":"self"}',
    #   * 摧毁装备族 → destroy_equipment(mode=..., filter=..., record_count=...)
    "destroy_self_equipment": '{"op":"equipment_op","mode":"destroy","pick":"self"}',
    "destroy_current_equipment": '{"op":"equipment_op","mode":"destroy","pick":"self"}',
    "destroy_all_destroyable_equipment": '{"op":"equipment_op","mode":"destroy","pick":"all","target":"both","filter":"destroyable","record_count":true}',
    "destroy_equipment_choice_or_first": '{"op":"equipment_op","mode":"destroy","pick":"choice","target":"enemy"}',
    #   * 卡牌属性写值族 → card_prop_change(mode=set|add|mul)
    "card_prop_set": '{"op":"card_prop_change","mode":"set","card":{"ref":"current_card"},"property":"fusion_level","value":0}',
    "card_prop_add": '{"op":"card_prop_change","mode":"add","card":{"ref":"current_card"},"property":"fusion_level","amount":1}',
    "card_prop_mul": '{"op":"card_prop_change","mode":"mul","card":{"ref":"current_card"},"property":"fusion_level","value":2}',
    #   * 标签族 → add_tag / add_tag_to_zone 的 mode（remove/clear/toggle）
    "remove_tag": '{"op":"tag_op","action":"remove","card":{"ref":"current_card"},"tag":"exile"}',
    "clear_tags": '{"op":"tag_op","action":"clear","card":{"ref":"current_card"}}',
    "remove_tag_from_zone": '{"op":"tag_op","action":"remove","target":"enemy","zone":"hand","tag":"revealed"}',
    "toggle_tag_in_zone": '{"op":"tag_op","action":"toggle","target":"target","zone":"hand","tag":"revealed","log":"{count}张牌切换了{tag}"}',
    #   * 其它：提示 / 造牌 / 消耗 / 区域查看
    "reveal_deck_top": '{"op":"reveal","mode":"card_set","source":"deck","amount":1,"target":"enemy","viewer":"self"}',
    "reveal_tag_hand": '{"op":"reveal","mode":"hand","target":"enemy","viewer":"self","tag":"revealed","mark":true}',
    "put_card_to_deck": '{"op":"move_card","zone":"deck","card":{"ref":"selected_card"},"position":"top"}',
    "give_card_to_discard": '{"op":"create_card","card_id":"card_id","to":"discard","target":"self"}',
    "resource_spend": '{"op":"resource_op","resource":"e","mode":"spend","target":"self","amount":1,"log":"{target}消耗{amount}E"}',
    # Round 32 / 批次 AA（本批五族）：旧名一律带完整替代写法，写出来是
    # "已移除 + 请改用"的显式报错，不静默。
    #   * 生命族 → health_op(mode=heal|lose|set|swap|fatal)
    "heal": '{"op":"health_op","mode":"heal","target":"self","amount":5}',
    "lose_health": '{"op":"health_op","mode":"lose","target":"self","amount":3}',
    "set_health": '{"op":"health_op","mode":"set","target":"self","amount":60}',
    "swap_health": '{"op":"health_op","mode":"swap","target1":"self","target2":"enemy"}',
    "on_fatal_set_health_exile": '{"op":"health_op","mode":"fatal","kind":"exile","health":5}',
    "on_fatal_invincible_then_die": '{"op":"health_op","mode":"fatal","kind":"invincible_die"}',
    #   * 资源族 → resource_op(resource=e|m, delta 正数获得 / 负数消耗)
    "gain_e": '{"op":"resource_op","resource":"e","delta":2,"target":"self"}',
    "gain_m": '{"op":"resource_op","resource":"m","delta":2,"target":"self"}',
    "spend_resource": '{"op":"resource_op","resource":"e","mode":"spend","amount":1,"target":"self","log":"{target}消耗{amount}E"}',
    "coffee_gain_e": '{"op":"resource_op","resource":"e","delta":2,"target":"self","reset_coffee":true,"card_heavy":1,"log":"{target}获得{amount}E；本牌获得1层沉重"}',
    "aura_enemy_elixir_recovery": '{"op":"resource_op","mode":"aura_recovery","resource":"e","amount":1}',
    #   * 费用族 → modify_next_cost(delta 正数加费 / 负数减费)
    "increase_next_cost": '{"op":"card_prop_add_to_zone","target":"self","zone":"hand",'
                          '"property":"temp_heavy_value","amount":N,"require_selectable":false,'
                          '"silent":true}（modify_next_cost 也在 Round 43 删除）',
    "reduce_next_cost": '{"op":"card_prop_add_to_zone","target":"self","zone":"hand",'
                        '"property":"temp_swift_value","amount":N,"require_selectable":false,'
                        '"silent":true}（modify_next_cost 也在 Round 43 删除）',
    #   * 抽牌修正 → draw 的 modifiers
    "equip_reduce_draw": '{"op":"draw","count":0,"hooks":false,"target":"self","modifiers":[{"type":"sluggish","amount":1,"target":"enemy"}]}',
    #   * 控制流 → repeat(until=...) / for_each(bind:"selected_card") / list_modify
    "repeat_until": '{"op":"repeat","until":<停止条件>,"body":[...],"limit":64}',
    "for_each_selected_card": '{"op":"for_each","bind":"selected_card","body":[...]}',
    "list_set": '{"op":"list_modify","list":"<变量名>","mode":"set","value":[...]}',
    "list_append": '{"op":"list_modify","list":"<变量名>","mode":"append","value":<元素>}',
    "list_insert": '{"op":"list_modify","list":"<变量名>","mode":"insert","index":1,"value":<元素>}',
    "list_delete": '{"op":"list_modify","list":"<变量名>","mode":"delete","index":1}',
    "list_clear": '{"op":"list_modify","list":"<变量名>","mode":"clear"}',

    # Round 33 / 批次 AB（区域/复制/揭示/洗牌/快照族）：旧名一律带完整替代
    # 写法，写出来是"已移除 + 请改用"的显式报错，不静默。
    #   * 造牌族 → move_card(mode:"give"|"orb")
    "give_card_to_hand": '{"op":"move_card","mode":"give","target_zone":"hand","card":"<牌id>","amount":1,"target":"self"}',
    "give_card_to_deck": '{"op":"move_card","mode":"give","target_zone":"deck","card":"<牌id>","amount":1,"target":"self","position":"top"}',
    "give_magic_orb_to_hand": '{"op":"move_card","mode":"orb","target_zone":"hand","target":"self"}',
    #   * 区域移动族
    "random_zone_card_to_hand": '{"op":"move_card","mode":"random","source_zone":"discard","target_zone":"hand","count":1,"target":"self"}',
    "move_cards_to_deck": '{"op":"move_card","mode":"batch","target_zone":"deck","cards":"selected_cards","position":"top"}',
    "exile_this": '{"op":"move_card","zone":"exile","card":{"ref":"current_card"}}',
    "steal_enemy_card": '{"op":"move_card","mode":"steal","target":"enemy"}',
    "swap_hands": '{"op":"move_card","mode":"swap_hands","target1":"self","target2":"enemy"}',
    #   * 复制族 → copy_card 的 as_instance / to_zone / count
    "copy_card_instance": '{"op":"copy_card","as_instance":true,"source":{"ref":"current_card"},"target":"self","zone":"hand"}',
    "create_copies_to_deck_top": '{"op":"copy_card","to_zone":"deck_top","count":1,"def_id":"<牌id>","target":"self"}',
    #   * 揭示族 → reveal(mode=card_set|enemy_hand|hand)
    "reveal_card_set": '{"op":"reveal","mode":"card_set","source":"initial_deck","target":"target","viewer":"self"}',
    "reveal_enemy_hand": '{"op":"reveal","mode":"enemy_hand","target":"enemy"}',
    "reveal_hand_cards": '{"op":"reveal","mode":"hand","target":"target","viewer":"self","mark":true}',
    "reveal_hand": '{"op":"reveal","mode":"enemy_hand","target":"enemy"}',
    "garden_show_initial_deck": '{"op":"reveal","mode":"card_set","source":"initial_deck","target":"target","viewer":"self"}',
    #   * 洗牌族 → shuffle(zone=discard|hand)
    "shuffle_discard_into_deck": '{"op":"shuffle","zone":"discard"}',
    "shuffle_hand": '{"op":"shuffle","zone":"hand","target":"self"}',
    #   * 快照族 → snapshot / restore 的 mode
    "snapshot_card_props": '{"op":"snapshot","mode":"card_props","owner":"self","zone":"hand","store":"card_prop_snapshot","property":"cost_e_override"}',
    "restore_card_props": '{"op":"restore","mode":"card_props","owner":"self","store":"card_prop_snapshot"}',
    "restore_match_start_stats": '{"op":"restore","mode":"match_start","target":"self"}',
    "restore_turn_start_stats": '{"op":"restore","mode":"turn_start","target":"self"}',

    # Round 33 / 批次 AC + Round 35 收尾（装备/状态/标签/自动打出四族）：rd33 的
    # 迁移脚本死在半路（旧实现被删、数据只迁了一部分，还有 59 步被写成
    # ``{"op":"add"}`` 的坏形状），Round 35 把数据补齐到伞原子并在这里登记旧名。
    # 同样带完整替代写法，写出来是"已移除 + 请改用"的显式报错。
    #   * 装备族 → equipment_op(mode=place|give|armor|destroy|seal|unprotect|each)
    "place_as_equip": '{"op":"equipment_op","mode":"place","owner":"self","effect_target":"target"}',
    "add_equipment_to_zone": '{"op":"equipment_op","mode":"give","card":"<牌id>","target":"target","effect_target":"target"}',
    "add_equipment_armor": '{"op":"equipment_op","mode":"armor","target":"self","amount":2}',
    "destroy_equipment": '{"op":"equipment_op","mode":"destroy","pick":"choice","target":"enemy"}（pick 选 choice/random/all/self；名字点选用 equipment/card，整场用 scope:"field"，可加 filter:"destroyable" 与 record_count:true）',
    "seal_equipment": '{"op":"equipment_op","mode":"seal","target":"target","amount":1}',
    "remove_equip_protection": '{"op":"equipment_op","mode":"unprotect","target":"target"}',
    "for_each_equipment": '{"op":"equipment_op","mode":"each","target":"target","body":[...]}',
    #   * 状态族 → status_op(action=add|set|remove|clear|settle)
    "status_add_named": '{"op":"status_op","action":"add","status":"<状态id>","amount":1,"target":"self"}（设为 N 层写 mode:"set"）',
    "status_remove_named": '{"op":"status_op","action":"remove","status":"<状态id>","amount":"all","target":"self"}',
    "clear_statuses": '{"op":"status_op","action":"clear","statuses":"all","target":"self"}（名单式清状态写 statuses:[...] 或 preset:buffs/debuffs）',
    "settle_status": '{"op":"status_op","action":"settle","status":"fire","reduce":1,"target":"target"}',
    #   * 标签族 → tag_op(action=add|remove|toggle|clear；带 zone/zones 即区域级)
    "add_tag": '{"op":"tag_op","action":"add","card":{"ref":"current_card"},"tag":"<标签>"}（减/清写 action:remove|clear）',
    "add_tag_to_zone": '{"op":"tag_op","action":"add","target":"enemy","zone":"hand","tag":"<标签>"}（切换写 action:"toggle"）',
    #   * 自动打出族 → auto_play(mode=card|zone_top)；``queue_auto_play`` 保持可用
    "auto_play_card": '{"op":"auto_play","mode":"card","card":{"ref":"last_created_card"},"no_cost":false}',
    "auto_play_zone_top": '{"op":"auto_play","mode":"zone_top","actor":{"ref":"equipment_target"},"zone":"deck","cost":"free"}',

    # Round 36 / 批次 AD-1（请求族四合一）：七个请求类 op 全部并进 ``request``，
    # ``type`` 选类别（target / card / confirm / zone / forced_target /
    # discount_copy / reorder_deck）。扁平写法的 ``type`` 是判别参数
    # （``_effect_params`` 会把它排除在客户端 payload 之外，所以选择窗口的
    # payload 与合并前逐字节一致）；原本就带 ``params`` 的步骤把 ``type`` 写在
    # 顶层、参数体留在 ``params`` 里。
    "request_target": '{"op":"request","type":"target","allowed":"any"}（allowed 选 any/not_self/self/enemy/friendly…；可加 alive_only:false）',
    "request_card": '{"op":"request","type":"card","params":{"choice_type":"choose_card_from_hand","target":"self","zone":"hand"}}（filter/zone/choice_type/multi/min_count… 原样放进 params；也可扁平写在同一层）',
    "request_confirm": '{"op":"request","type":"confirm","params":{"choice_type":"<自定义 key>","options":[…],"cancellable":false}}',
    "choose_from_zone": '{"op":"request","type":"zone","zone":"deck","target":"self"}（zone 选 deck/discard/exile）',
    "declare_forced_target": '{"op":"request","type":"forced_target","target":"self"}',
    "copy_choice_with_discount": '{"op":"request","type":"discount_copy","discount_e":1}（拟态：复制选中的手牌并打折）',
    "request_reorder_deck": '{"op":"request","type":"reorder_deck","target":"enemy","message":"调整对手牌堆顺序"}',

    # Round 37 / 批次 AD-2（延迟族三合一）：``timed_effect`` 与两条
    # ``delayed_*_next_turn`` 并进 ``delayed_effect``，``mode`` 选分支
    # （timed / blind / reveal_hand）。三条分支共用同一张计时表
    # （``_register_timed_effect``），所以 trigger 与触发相位逐字保留。
    "timed_effect": '{"op":"delayed_effect","mode":"timed","trigger":"target_turn_start","duration":1,"target":"target","body":[…]}（trigger 见运行时词表：target_turn_start / target_turn_start_after_status_clear / target_turn_start_after_draw / target_turn_end / owner_turn_start / owner_turn_end / any_turn_start / any_turn_end / friendly_turn_start / enemy_turn_start；once:true 等价 duration:1）',
    "delayed_blind_next_turn": '{"op":"delayed_effect","mode":"blind","target":"target","amount":1}（目标下回合开始、状态清算之后失明并洗牌）',
    "delayed_reveal_hand_next_turn": '{"op":"delayed_effect","mode":"reveal_hand","target":"target"}（目标下回合开始时展示其手牌）',

    # Round 37 / 批次 AD-2（监听族四合一 + 广播族二合一）：``on_event`` 的
    # ``trigger`` 选监听时点（Round 42 / 批次 AF 起底下的 ``emit_event`` 也删除了，
    # 广播写法统一成 ``log``；见上面的 REMOVED 条目）。四条 on_event
    # 分支的实现体逐字沿用旧原子（同一张 ``PLAY_LISTENERS_KEY`` 监听表、同一套
    # ``_once_per_play`` 卡内标记），时点语义不变。
    "once_per_play": '{"op":"on_event","trigger":"this_play","name":"<标识>","body":[…]}（本次出牌内结算一次；同名的 on_event(trigger:"this_play") 共享同一个标记）',
    "register_play_listener": '{"op":"on_event","trigger":"play","target":"target","duration":"turn","scope":"owner_turn","exclude_card_ids":[…],"body":[…]}（拥有者本回合每次出牌后触发；body 里可读 listener_target_id）',
    "after_all": '{"op":"on_event","trigger":"after_all","body":[…]}（也可写成 {"op":"on_event","after":true,"body":[…]}）',
    "magic_relic_trigger": '{"op":"on_event","trigger":"equipment_trigger","effect":"magic_relic"}（消耗队友 2M、自己 +3M；1v1 无队友时按旧行为直接返回）',
    "broadcast_event": '{"op":"log","message":"广播事件：<事件名>"}（emit_event 已删除：事件总线没有订阅方，'
                       '这一步本来就只是播报；要静默写 log:false）',
    "trigger_manual": '（占位步骤原本就没有实现体 = 什么都不做；Round 42 起 emit_event 删除，'
                      '如需保留"什么都不做"的一步，写 {"op":"log","message":"","silent":true} 或不写这一步）',

    # Round 38 / 批次 AD-3（回合控制族三合一）：``mode`` 选分支
    # （end / skip / extra），三个分支的实现体逐字沿用旧原子。
    # ``mode:"end"`` 只给**出牌者**挂标记（旧实现同样忽略 target），真正结束
    # 回合的判定仍在 ``_play_card`` 把本牌整套效果结算完之后——"本牌结算完再
    # 结束"的时点不变；``mode:"skip"`` 沿用 ``skip_turn`` 的层数与状态免疫
    # 判定；``mode:"extra"`` 给目标挂额外回合（卡数据至今 0 步，登记为可用名）。
    "force_end_turn": '{"op":"turn_control","mode":"end"}（本牌结算完之后结束出牌者的回合；旧写法里的 log:false 原样保留，target 一向被忽略）',
    "skip_turn": '{"op":"turn_control","mode":"skip","target":"enemy","amount":1}（目标 +N 层眩晕；target 默认 enemy，走状态免疫判定）',
    "extra_turn": '{"op":"turn_control","mode":"extra","target":"self"}（目标获得一个额外回合；target 默认 self）',

    # Round 38 / 批次 AD-3（行为过滤族四合一）→ Round 42 / 批次 AF：``action_filter``
    # 本身也删除，四个 mode 改写成既有原子（玩家属性 + 取值表达式 + log）：
    "block_own_actions": '{"op":"player_prop_change","mode":"set","property":"shovel_active","value":1,"target":"self"}'
                         '（出牌者本回合无法使用卡牌；官方包 ocean:bubble_bomb 就是这么写的；旧别名 block_action 同此写法）',
    "block_action": '{"op":"player_prop_change","mode":"set","property":"shovel_active","value":1,"target":"self"}'
                    '（block_own_actions 的别名，一起退役）',
    "block_card_type": '{"op":"player_prop_change","mode":"set","property":"attack_blocked","target":"enemy",'
                       '"value":{"op":"max","a":{"op":"player_property","property":"attack_blocked","target":"enemy"},"b":1}}'
                       '（thorn = attack_blocked、bloom = skill_blocked 但该字段零读取方；'
                       '官方包 sewers:poo / ocean:jelly 用 status_op(action:"add") 写同一字段）',
    "force_card_type": '{"op":"player_prop_change","mode":"set","property":"attack_only","target":"enemy",'
                       '"value":{"op":"max","a":{"op":"player_property","property":"attack_only","target":"enemy"},"b":1}}'
                       '（thorn = attack_only；其它牌型旧实现只播报）',
    "nullify_current_card": '{"op":"log","message":"<目标>的<牌型>牌将失效"}（negate_next 全仓库零读取方，'
                            '旧实现也只有"写标记 + 播报"）',

    # Round 40 / 批次 AE-2~4（三个卡专用原子下沉成通用能力/数据）：
    #   * AE-2：``assembler_effect``（重构机）—— 选牌窗口、放逐、随机奖励表
    #     全部改成通用步骤；奖励表本身留在卡数据里（``random_choice`` 的
    #     ``values``），一次掷骰的结果存进上下文变量 ``assembler_reward`` 后
    #     被造牌 / 迅捷 / 碎片 / 战报复用。
    "assembler_effect": (
        '[{"op":"request","type":"card","target":"choice_target","cancellable":false,'
        '"continue_on_cancel":true,"title":"重构机：选择一张手牌放逐",'
        '"filter":{"zone":"hand","exclude_self":true,"require_selectable":true}},'
        '{"op":"move_card","card":{"ref":"selected_card"},"target_zone":"exile","silent":true},'
        '{"op":"log","message":"{source}用重构机放逐了{target}的1张手牌"},'
        '{"op":"if_else","condition":{"op":"compare","a":{"op":"selected_cards_count"},"operator":">","b":0},'
        '"then":[{"op":"set_var","name":"assembler_reward","value":{"op":"random_choice","values":['
        '{"card":"Laser","swift":2,"log":"{source}的重构机：{target}获得激光器"},'
        '{"card":"Sawblade","swift":2,"log":"{source}的重构机：{target}获得锯片"},'
        '{"card":"Fragment","fragment_stacks":2,"log":"{source}的重构机：{target}获得2层碎片和1张碎片"}]}},'
        '{"op":"if_else","condition":{"op":"compare","a":{"op":"get","from":{"op":"var","name":"assembler_reward"},"key":"fragment_stacks"},'
        '"operator":">","b":0},"then":[{"op":"status_op","action":"add","status":"fragment_stacks",'
        '"target":"choice_target","amount":{"op":"get","from":{"op":"var","name":"assembler_reward"},"key":"fragment_stacks"}}]},'
        '{"op":"move_card","mode":"give","card_id":{"op":"get","from":{"op":"var","name":"assembler_reward"},"key":"card"},'
        '"target":"choice_target","target_zone":"hand"},'
        '{"op":"if_else","condition":{"op":"compare","a":{"op":"get","from":{"op":"var","name":"assembler_reward"},"key":"swift"},'
        '"operator":">","b":0},"then":[{"op":"card_prop_change","card":{"ref":"last_created_card"},'
        '"property":"swift_value","mode":"set","value":{"op":"get","from":{"op":"var","name":"assembler_reward"},"key":"swift"}}]},'
        '{"op":"log","message":{"op":"get","from":{"op":"var","name":"assembler_reward"},"key":"log"}}]}]'
    ),
    #   * AE-3：``mark_original_card``（起诉书给"被响应的那张牌"打标记）——
    #     标记改写成被响应牌的 ``custom_vars``（读取方
    #     ``_bio_indictment_converts_damage`` 同步改读 ``custom_vars``）。
    "mark_original_card": (
        '{"op":"card_var_change","card":{"ref":"original_card"},'
        '"name":"_bio_indictment_target_id","mode":"set","value":{"op":"source_player"}}'
        '{"op":"log","message":"{source}的起诉书将所响应攻击牌的伤害转化为护盾"}'
    ),
    #   * AE-4：``discard_hand_by_paid_e``（风）—— 通用能力先在引擎落地
    #     （``move_card(mode:"batch")`` 支持 ``source_zone`` + ``filter`` +
    #     ``owner`` 集合 + ``count_as_active_discard``），原子随之删除。
    "discard_hand_by_paid_e": (
        '{"op":"move_card","mode":"batch","owner":"all_players","source_zone":"hand",'
        '"target_zone":"discard","count_as_active_discard":true,"log":"风吹走了{count}张牌",'
        '"filter":{"require_selectable":false,"exclude_error":true,'
        '"max_cost_e":{"op":"add","values":[{"op":"card_prop","card":"current_card","prop":"paid_e"},1]}}}'
    ),
}

# Round 22：别名收敛——同一概念的旧名已删除（不再登记、也没有运行时别名），
# 卡数据/工具再写这些名字会在校验层与运行时拿到显式报错，映射值是应该改用的
# 规范名。与 ``REMOVED_ATOMIC_OPS`` 的区别：那些名字已经没有等价实现，这边的
# 旧名只是改了称呼，规范名照常可用。
RENAMED_ATOMIC_OPS = {
    # Round 41 / 批次 AE-5：齿轮的"标记"半边下沉成数据（``player_var_change`` 写
    # ``cogwheel_active`` / ``cogwheel_exclude_instance_id``），留在引擎里的收牌
    # 例程改名 ``cogwheel_return``——旧名写出来拿到"已改名 + 规范名"。
    "cogwheel_mark": "cogwheel_return",
    # Round 24：apply_poison / apply_toxic / gain_armor 的"规范名"本身也在
    # C 类合并里注销了，所以它们从本表移到 REMOVED_ATOMIC_OPS（带完整替代写法）。
    "auto_play_queue_add": "queue_auto_play",
    "queue_auto_play_card": "queue_auto_play",
    # Round 35：``auto_play_card`` / ``auto_play_zone_top`` 并进 ``auto_play``
    # （mode 选 card/zone_top），所以它们的"声明旧称"也指到伞原子。
    "kitty_auto_play": "auto_play",
    "bounce_attack": "ricochet_attack",
    # Round 31 / 批次 Z：``for_each_target`` 这条薄转发已删除，两个旧名直接
    # 指到循环族规范名 ``for_each``（``source:"wide_strike_targets"`` +
    # ``bind:"target"`` 就是原来的预设）。
    "ocean_for_each_selectable_target": "for_each",
    "for_each_selectable_target": "for_each",
    "for_each_target": "for_each",
    # Round 33 / 批次 AB：``garden_show_initial_deck`` 从本表移到
    # REMOVED_ATOMIC_OPS（``reveal_card_set`` 本身并进 ``reveal`` 伞了）。
    "set_card_var": "card_var_change",
    # Round 29 / 批次 X：player_prop_set / player_prop_add 合并成
    # player_prop_change(mode=...)，它们的"声明旧称"也一并指到规范名。
    "player_property_set": "player_prop_change",
    "player_property_add": "player_prop_change",
    # Round 25：登记残留里"只是换了称呼"的 5 个——规范名照常可用，旧名给
    # "已改名 + 规范名"的显式报错（其余旧名进 REMOVED_ATOMIC_OPS）。
    "arctic_ricochet_attack": "ricochet_attack",
    "desert_marble_attack": "ricochet_attack",
    "ocean_add_charge_to_hand": "add_charge_to_hand",
    "ocean_mark_auto_play": "queue_auto_play",
    "void_kitty_auto_play": "auto_play",
    # Round 32 / 批次 AA：纯改名（参数面不变）——``if`` 就是"不写 else 的
    # ``if_else``"，``for_each_list`` 的 ``list``/``name`` 参数本来就在
    # ``for_each`` 的统一来源词表里，``draw_cards`` 的默认值与 ``draw`` 相同
    # （要"播报请求值"就显式写 ``log_amount:"requested"``）。
    "if": "if_else",
    "for_each_list": "for_each",
    "draw_cards": "draw",
}

# Every curated core op plus every atomic handler the engine implements, so new
# engine atoms become available to mod v2 content as soon as they exist.
# Round 22: 别名收敛删掉的旧名即使还有 ``_atomic_*`` 实现（如 apply_toxic）
# 也不再对外登记，写出来会拿到 RENAMED_ATOMIC_OPS 的显式报错。
# Round 29: ``REMOVED_ATOMIC_OPS`` 里的名字同样从契约里扣掉——批次 X 给
# ``var_set`` / ``move_to_hand`` / ``player_prop_*`` / ``card_var_*`` 留了同名
# 兼容垫片（老测试与引擎内部直呼私有方法），但它们**不再是对外 op**，
# 卡数据写旧名一律拿到"已移除 + 替代写法"的显式报错。
VALID_LOGIC_OPS = (
    merge_public_ops(_CORE_LOGIC_OPS)
    - set(RENAMED_ATOMIC_OPS)
    - set(REMOVED_ATOMIC_OPS)
)

# --- Round 33 recovery（Round 35 收尾后已删除）------------------------------
# 批次 AB/AC 的代理死在半路时，这里临时把 30 个旧名重新登记回契约，好让
# "实现已被删、数据还在用"的中间态不炸。Round 35 已经把卡数据全部迁到伞原子
# （.codex-tmp/round35/rd35_migrate.py），因此这张临时表删除：
#   * 真删的 15 个名字在 REMOVED_ATOMIC_OPS 里给出"已移除 + 替代写法"；
#   * 处理器保留给 tests / formal_logic_runtime 直呼的 13 个名字同样进
#     REMOVED_ATOMIC_OPS——``VALID_LOGIC_OPS`` 会把它们减掉，所以**不再是对外
#     op**；``_atomic_*`` 处理器只是私有实现（这是 Round 29 起"私有处理器 ≠
#     公开 op"的既有约定，见上面 ``VALID_LOGIC_OPS`` 之前的注释）。
#     代价是 ``tools/mod_atom_report.py`` 的"未登记原子"会数到这些名字——
#     报告里已经按"退役但保留处理器"单列。
#   * ``queue_auto_play`` 保持可用（官方包 ocean:magic_pearl 的步骤形状被
#     tests/test_allcards_balance_14.py 断言），既是 ``_atomic_*`` 又在
#     ``_CORE_LOGIC_OPS`` 里。

VALID_EVENT_HOOKS = {
    "before_play_card",
    "after_play_card",
    "before_damage",
    "modify_damage",
    "after_damage",
    "turn_start",
    "turn_end",
    "before_draw",
    "after_draw",
    "status_added",
    "equipment_destroyed",
    "on_match_start",
    "on_game_start",
    "on_draft_start",
    "on_opening_event",
    "on_turn_start",
    "on_turn_end",
    "on_card_enter_hand",
    "on_card_play",
    "on_card_resolve",
    "on_card_discarded",
    "on_card_exiled",
    "on_equipment_equipped",
    "on_equipment_trigger",
    "on_equipment_destroy",
    "on_damage",
    "on_damage_dealt",
    "on_damage_taken",
    "on_heal",
    "on_resource_spent",
    "on_resource_changed",
    "on_player_stat_changed",
    "on_status_added",
    "on_status_removed",
    "on_tag_added",
    "on_tag_removed",
    "on_response_window",
    "on_choice_window",
}

VALID_PATCH_OPS = {
    "add_tag",
    "remove_tag",
    "append_event_steps",
    "prepend_event_steps",
    "add_ui_style_token",
    "modify_numeric_field",
    "add_description_line",
}

RESERVED_NAMESPACES = {"gtn", "core", "system"}

NAMESPACE_RE = re.compile(r"^[a-z0-9_]+$")
PATH_RE = re.compile(r"^[a-z0-9_]+(?:/[a-z0-9_]+)*$")
RESOURCE_ID_RE = re.compile(r"^([a-z0-9_]+):([a-z0-9_]+(?:/[a-z0-9_]+)*)$")


def is_namespace(value: Any) -> bool:
    return isinstance(value, str) and bool(NAMESPACE_RE.fullmatch(value))


def is_resource_path(value: Any) -> bool:
    return isinstance(value, str) and bool(PATH_RE.fullmatch(value))


def is_namespaced_id(value: Any) -> bool:
    return isinstance(value, str) and bool(RESOURCE_ID_RE.fullmatch(value))


def split_resource_id(value: str) -> Tuple[str, str]:
    match = RESOURCE_ID_RE.fullmatch(value or "")
    if not match:
        raise ValueError(f"非法资源 ID: {value!r}")
    return match.group(1), match.group(2)


def normalize_resource_id(mod_id: str, raw_id: Any) -> str:
    if not isinstance(raw_id, str):
        raise ValueError("资源 ID 必须是字符串")
    raw_id = raw_id.strip()
    if not raw_id:
        raise ValueError("资源 ID 不能为空")
    if is_namespaced_id(raw_id):
        return raw_id
    if ":" in raw_id:
        raise ValueError(f"非法资源 ID: {raw_id}")
    if not is_namespace(mod_id):
        raise ValueError(f"非法模组命名空间: {mod_id}")
    if not is_resource_path(raw_id):
        raise ValueError(f"非法资源路径: {raw_id}")
    return f"{mod_id}:{raw_id}"


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()
