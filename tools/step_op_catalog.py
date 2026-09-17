# -*- coding: utf-8 -*-
"""「添加效果」选择器的数据源：**每个可写步骤 op 的中文名 + 分组 + 最小可运行默认参数**。

背景（Round 101 / 批次 CW）：编辑器原来的「＋ 添加效果」按钮写死插入 ``deal_damage``，
模板库只有 23 条、覆盖 17 个 op——引擎允许写的 **47 个公开原子 + 2 个宏**里，
有 33 个在界面上**根本加不出来**（``request_ui`` / ``player_var_change`` / ``repeat`` …）。

这份目录把"能不能加得出来"补成 100%：

* ``ops[].defaults`` 是**最小可运行**的参数（不是"能过校验就行"——见
  ``.codex-tmp/round101/catalog_runtime_probe.py``：49 个默认参数逐个丢进
  ``run_v2_steps`` 真跑一遍）；
* 旧名宏（``damage`` / ``defer_death_checks``）标 ``hidden``，选择器不显示，但目录里留着，
  保证"可写名单 → 目录"的对拍不会漏；
* 覆盖不到就要报错：``python tools/step_op_catalog.py --check`` 会在
  新增/删除可写 op 时失败，逼着人来补中文名与默认参数（第 7 处表对拍）。

    python tools/step_op_catalog.py            # 写 模组编辑器/src/generated/op-catalog.json
    python tools/step_op_catalog.py --check    # 只校验（目录是否过期、是否覆盖全部可写 op）
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mod_spec_v2  # noqa: E402

DEFAULT_OUT = ROOT.parent / "模组编辑器" / "src" / "generated" / "op-catalog.json"

GROUPS = [
    ("damage", "伤害"),
    ("status", "状态"),
    ("resource", "资源与生命"),
    ("card", "牌与区域"),
    ("equipment", "装备"),
    ("stat", "变量与属性"),
    ("flow", "控制流与随机"),
    ("ui", "界面与提示"),
    ("event", "事件与延迟"),
    ("turn", "回合与收尾"),
    ("tag", "标签"),
]

# op -> (中文名, 分组, 最小可运行默认参数, 适用说明)
CATALOG: dict[str, tuple[str, str, dict, str]] = {
    # ---- 伤害 ----
    "deal_damage": ("造成伤害", "damage", {"target": "target", "amount": 5}, "吃闪避/护甲/暴击，走完整攻击管线"),
    "direct_damage": ("直接伤害（无视闪避）", "damage",
                      {"target": "target", "amount": 3, "damage_type": "magic"}, "魔法/电伤也走这里"),
    "multiply_next_damage": ("下次伤害倍增", "damage", {"multiplier": 2}, "给下一次伤害乘一个倍率"),
    "charge_self_damage": ("自伤蓄力", "damage", {}, "按卡上写的层数自伤蓄力（参数由卡数据决定）"),
    "crit_multiplier_add": ("暴击倍率提升", "damage",
                            {"target": "target", "amount": 0.5, "temporary": False}, "temporary=true 只作用于下一次"),
    # ---- 状态 ----
    "status_op": ("状态操作（加/减/清除）", "status",
                  {"action": "add", "target": "target", "status": "fire", "amount": 2}, "action 也可写 remove/clear"),
    "player_status_layers": ("玩家状态层数", "status",
                             {"target": "self", "status": "fire", "amount": 1}, "直接读写某个状态的层数"),
    # ---- 资源与生命 ----
    "resource_op": ("资源增减（体力/魔力/生命）", "resource",
                    {"resource": "e", "target": "self", "delta": 1}, "resource 认 e / m / health"),
    "health_op": ("生命操作（治疗/扣血/设值）", "resource",
                  {"mode": "heal", "target": "self", "amount": 5}, "mode 认 heal / damage / set"),
    "apply_turn_regen": ("每回合回复", "resource",
                         {"target": "self", "kind": "heal", "power": 1, "turns": 3}, "kind 认 heal / magic"),
    "draw": ("抽牌", "resource", {"target": "self", "count": 1}, "count 可写表达式"),
    "shuffle": ("洗牌", "resource", {"target": "self", "zone": "discard", "to": "deck"}, "把某个区域洗回牌堆"),
    # ---- 牌与区域 ----
    "create_card": ("造一张牌", "card", {"card_id": "Basic", "target": "source", "zone": "hand"}, "card_id 用卡定义 id"),
    "copy_card": ("复制牌", "card", {"target": "self", "count": 1}, "count 可写表达式"),
    "move_card": ("移动牌", "card", {"mode": "discard", "card": {"ref": "current_card"}},
                  "mode 认 give/discard/remove/transform 等；必须写清目的区"),
    "reveal": ("展示牌", "card", {"target": "enemy", "source": "hand", "to": "self"}, "把某个区域亮出来"),
    "pick": ("挑选", "card", {"source": [], "amount": 1}, "通常配合 request 使用（source 写候选集合）"),
    "deck_catalog_pick": ("牌库挑选", "card",
                          {"target": "all_selectable", "source": "source", "pick": 1, "shuffle": "each"},
                          "从牌库里挑牌给玩家"),
    "discard_choice_then_draw": ("弃一张再抽等量", "card", {}, "张数由卡上写的参数决定"),
    "auto_play": ("自动打出", "card", {"card": {"ref": "current_card"}, "mode": "queue"},
                  "mode=queue 进队列；cost 默认 free"),
    "delayed_effect": ("延迟效果", "card",
                       {"target": "self", "duration": 1, "body": [{"op": "log", "message": "延迟效果触发"}]},
                       "duration 是回合数"),
    "snapshot": ("快照存取", "card", {"action": "save", "target": "self", "store": "card_prop_snapshot"},
                 "action 认 save / load（旧 restore 已合并）"),
    # ---- 装备 ----
    "equipment_op": ("装备操作", "equipment", {"mode": "choice", "target": "enemy"},
                     "mode 认 destroy / armor / setup / choice 等"),
    "equipment_prop_change": ("装备属性写值", "equipment",
                              {"mode": "set", "property": "turns_equipped",
                               "equipment": {"ref": "current_equipment"}, "value": 1}, "mode 认 set / add"),
    "cogwheel_return": ("齿轮回收", "equipment", {}, "把本回合用掉的装备收回手里"),
    # ---- 变量与属性 ----
    "add_var": ("变量累加", "stat", {"name": "my_var", "value": 1}, "事件上下文变量，同一步骤链内可见"),
    "set_var": ("变量设值", "stat", {"name": "my_var", "value": 1}, "同上，直接赋值"),
    "player_var_change": ("玩家变量", "stat", {"mode": "set", "target": "self", "name": "my_var", "value": 1},
                          "同一局内保留（含换回合），不跨局"),
    "card_var_change": ("卡牌变量", "stat", {"mode": "set", "name": "my_var", "value": 1}, "写在牌实例上"),
    "card_prop_change": ("卡牌属性", "stat", {"mode": "set", "property": "power", "value": 5},
                         "property 认 power / cost_e / fusion_level 等"),
    "card_prop_add_to_zone": ("区域卡牌属性", "stat",
                              {"target": "self", "zone": "hand", "property": "power", "amount": 1}, "给整片区域的牌加属性"),
    "player_prop_change": ("玩家属性", "stat", {"mode": "set", "target": "self", "property": "health", "value": 60},
                           "未登记的属性名会落 custom_vars"),
    "player_stat_change": ("玩家数值（护甲/闪避）", "stat",
                           {"mode": "add", "target": "self", "stat": "armor", "amount": 3},
                           "stat 认 armor / dodge 等"),
    # ---- 控制流与随机 ----
    "if_else": ("条件分支", "flow",
                {"condition": {"op": "compare", "a": {"op": "last_damage"}, "operator": ">", "b": 0},
                 "then": [{"op": "log", "message": "条件成立"}], "else": []}, "旧名 if 已删除"),
    "repeat": ("重复执行", "flow", {"times": 2, "body": [{"op": "log", "message": "重复执行"}]},
               "times 可写表达式，或改用 until"),
    "for_each": ("对集合循环", "flow", {"targets": "all_enemies", "body": [{"op": "log", "message": "对每个目标"}]},
                 "targets 也可写区域集合"),
    "break": ("跳出循环", "flow", {}, "只写在循环体里"),
    "continue": ("跳过本次循环", "flow", {}, "只写在循环体里"),
    "random": ("随机数/随机取值", "flow", {"min": 1, "max": 3}, "作为步骤时按随机数用；也能当取值表达式"),
    # ---- 界面与提示 ----
    "request_ui": ("弹出窗口", "ui",
                   {"component": {"type": "modal", "title_cn": "请选择",
                                  "controls": [{"id": "choice", "type": "select", "label_cn": "选择",
                                                "options": [{"value": "a", "label_cn": "选项 A"},
                                                            {"value": "b", "label_cn": "选项 B"}]}],
                                  "buttons": [{"id": "confirm", "text_cn": "确定", "role": "confirm"}]},
                    "save_as": "ui_result", "target_player": "source",
                    "on_invalid": "keep", "timeout_ms": 60000},
                   "默认给一个能跑的内联窗口；想复用改成窗口 id，见《自定义窗口写卡指南》"),
    "request": ("让玩家选牌/目标", "ui", {"target": "all_selectable", "min_count": 1},
                "从区域里选牌，选中的牌写进 save_as 变量"),
    "log": ("打一条战报", "ui", {"message": "效果触发"}, "支持 {target}/{amount}/{count} 等占位符"),
    # ---- 事件与延迟 ----
    "on_event": ("监听后续事件", "event",
                 {"trigger": "play", "scope": "owner_turn", "duration": "turn", "target": "self",
                  "body": [{"op": "log", "message": "事件触发"}]}, "触发/响应/收尾族唯一入口"),
    "modify_event_value": ("修改事件数值", "event", {"mode": "add", "value": 1}, "响应窗口里改伤害值等"),
    # ---- 回合与收尾 ----
    "turn_control": ("回合控制", "turn", {"mode": "skip_turn", "target": "enemy", "amount": 1},
                     "mode 认 skip_turn / extra_turn / force_end 等"),
    "defer_game_over": ("延迟游戏结束", "turn",
                        {"body": [{"op": "log", "message": "结算完再判定死亡"}]}, "把死亡判定推到这段效果之后"),
    # ---- 标签 ----
    "tag_op": ("标签操作", "tag", {"action": "add", "card": {"ref": "current_card"}, "tag": "marked"},
               "action 认 add / remove / toggle / clear"),
    # ---- 旧名宏（不显示在选择器里，但目录要对得上）----
    "damage": ("（旧名）造成伤害", "damage", {"target": "target", "amount": 5}, "等价于 deal_damage，老数据用"),
    "defer_death_checks": ("（旧名）延迟死亡判定", "turn",
                           {"body": [{"op": "log", "message": "结算完再判定死亡"}]}, "等价于 defer_game_over，老数据用"),
}

HIDDEN_OPS = {"damage", "defer_death_checks"}


def writable_ops() -> list:
    """写卡数据能用的步骤 op：公开原子 + 宏（**不含**内部处理器）。"""

    return sorted(set(mod_spec_v2.PUBLIC_ATOMS) | set(mod_spec_v2.ATOMIC_OP_MACROS))


def build_catalog() -> dict:
    ops = writable_ops()
    entries = []
    for op in ops:
        label, group, defaults, note = CATALOG.get(op, ("", "", {}, ""))
        entries.append({
            "op": op,
            "label_cn": label,
            "group": group,
            "defaults": defaults,
            "note": note,
            "hidden": op in HIDDEN_OPS,
        })
    return {
        "note": "步骤 op 目录（添加效果选择器用）：中文名 + 分组 + 最小可运行默认参数。"
                "由 tools/step_op_catalog.py 生成，别手改。",
        "source": "tools/step_op_catalog.py",
        "groups": [{"id": gid, "label_cn": label} for gid, label in GROUPS],
        "ops": entries,
    }


def coverage_problems() -> list:
    ops = writable_ops()
    missing = [op for op in ops if op not in CATALOG]
    extra = [op for op in CATALOG if op not in ops]
    empty_label = [op for op in ops if not (CATALOG.get(op) or ("",))[0]]
    bad_group = [op for op in ops
                 if (CATALOG.get(op) or ("", "", {}))[1] not in {gid for gid, _ in GROUPS}]
    problems = []
    if missing:
        problems.append(f"这些可写 op 还没有中文名/默认参数：{missing}")
    if extra:
        problems.append(f"目录里有已不可写的 op（删掉或改成别名）：{extra}")
    if empty_label:
        problems.append(f"这些 op 缺中文名：{empty_label}")
    if bad_group:
        problems.append(f"这些 op 的分组不在 GROUPS 里：{bad_group}")
    return problems


def render() -> str:
    return json.dumps(build_catalog(), ensure_ascii=False, indent=2) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="生成/校验「添加效果」选择器的 op 目录。")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

    problems = coverage_problems()
    out_path = pathlib.Path(args.out)
    text = render()
    if args.check:
        for problem in problems:
            print(f"[失败] {problem}")
        if not out_path.is_file():
            problems.append(f"目录文件不存在：{out_path}（跑一次不带 --check 的命令）")
        elif out_path.read_text(encoding="utf-8") != text:
            problems.append(f"目录文件不是最新的：{out_path}（跑一次不带 --check 的命令）")
        if problems:
            return 1
        visible = len([op for op in writable_ops() if op not in HIDDEN_OPS])
        print(f"op 目录 OK：可写 {len(writable_ops())} 个（选择器显示 "
              f"{visible} 个，隐藏旧名 {len(HIDDEN_OPS)} 个）")
        return 0

    for problem in problems:
        print(f"[警告] {problem}", file=sys.stderr)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    print(f"written: {out_path} ({out_path.stat().st_size} bytes)")
    print(f"可写 op {len(writable_ops())} 个；分组 {len(GROUPS)} 个")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
