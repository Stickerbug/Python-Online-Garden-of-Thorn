from __future__ import annotations

import json
import os
import zipfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "mods", "Formal Logic Reasoning.gtnmod")


def target_steps(*steps):
    return {
        "on_play": {
            "steps": [
                {"op": "request_target", "allowed": "any"},
                *steps,
            ]
        }
    }


def card(
    card_id,
    name_cn,
    name_en,
    cost_e,
    cost_m,
    card_type,
    count,
    effect_cn,
    flavor_cn,
    *,
    effect_en="",
    flavor_en="",
    flags=None,
    tags=None,
    events=None,
    formal=None,
    quality="Common",
    damage=0,
    hits=1,
    trigger_cost_e=-1,
    trigger_cost_m=0,
    trigger_effect_text="",
):
    result = {
        "id": f"formal_logic:{card_id}",
        "name_cn": name_cn,
        "name_en": name_en,
        "name_i18n": {"zh": name_cn, "en": name_en},
        "cost_e": cost_e,
        "cost_m": cost_m,
        "card_type": card_type,
        "count": count,
        "quality": quality,
        "description": flavor_cn,
        "description_i18n": {"zh": flavor_cn, "en": flavor_en or flavor_cn},
        "effect_text": effect_cn,
        "effect_text_i18n": {"zh": effect_cn, "en": effect_en or effect_cn},
        "flags": list(flags or []),
        "tags": list(tags or []),
        "events": events or {},
        "damage": damage,
        "hits": hits,
    }
    if formal:
        result["formal_logic"] = dict(formal)
    if trigger_cost_e >= 0:
        result["trigger_cost_e"] = trigger_cost_e
        result["trigger_cost_m"] = trigger_cost_m
        result["trigger_effect_text"] = trigger_effect_text
    return result


def theorem(
    card_id,
    formula,
    count,
    substitutions,
    flavor_cn,
    *,
    flavor_en="",
    rebound=True,
    debut_effect="",
    debut_text_cn="",
    debut_text_en="",
    reset_mode="discard",
):
    flags = ["symbiosis", "self_target"]
    if rebound:
        flags.insert(0, "rebound")
    tags = ["debut"] if debut_effect else []
    effect_cn = (
        f"每次打出时，自己获得3层护甲；前{substitutions}次打出时，使目标获得1层代入；"
        "再次打出时，使目标获得1层推理"
    )
    if reset_mode == "discard":
        effect_cn += "；进入弃牌堆后重置"
    else:
        effect_cn += "；推理完成后重置"
    if debut_text_cn:
        effect_cn += f"；登场：{debut_text_cn}"
    effect_en = (
        f"Gain 3 Armor whenever played. The first {substitutions} plays grant the target 1 Substitution; "
        "the next play grants 1 Inference. Reset afterward."
    )
    if debut_text_en:
        effect_en += f" Debut: {debut_text_en}"
    return card(
        card_id,
        formula,
        formula,
        1,
        0,
        "thorn",
        count,
        effect_cn,
        flavor_cn,
        effect_en=effect_en,
        flavor_en=flavor_en,
        flags=flags,
        tags=tags,
        events=target_steps(),
        formal={
            "kind": "theorem",
            "formula": formula,
            "formula_name": True,
            "substitutions": substitutions,
            "armor_each_play": True,
            "armor": 3,
            "reset_mode": reset_mode,
            "special_formula": count == 0,
            "debut_effect": debut_effect,
        },
    )


cards = [
    card(
        "variable_0", "变量$0", "Variable $0", 1, 0, "thorn", 5,
        "对目标造成6[[icon:D]]",
        "醒醒，它不是├$0>$0！",
        effect_en="Deal 6[[icon:D]] to the target.",
        flavor_en="Wake up. It is not ├$0>$0!",
        flags=["self_target"],
        events=target_steps({"op": "deal_damage", "target": "target", "amount": 6}),
        formal={"kind": "value", "formula": "├$0"},
        damage=6,
    ),
    card(
        "variable_1", "变量$1", "Variable $1", 1, 0, "bloom", 5,
        "回复目标5[[icon:H]]",
        "没有$0那么常用，但也差不多了……",
        effect_en="Restore 5[[icon:H]] to the target.",
        flavor_en="Not quite as common as $0, but close enough...",
        events=target_steps({"op": "heal", "target": "target", "amount": 5}),
        formal={"kind": "value", "formula": "├$1"},
    ),
    card(
        "variable_2", "变量$2", "Variable $2", 1, 0, "bloom", 5,
        "回复目标2[[icon:M]]",
        "十分少用，吗？骗你的，要玩推理都给我带上！",
        effect_en="Restore 2[[icon:M]] to the target.",
        flavor_en="Rarely useful? Just kidding. Bring it if you want to reason!",
        events=target_steps({"op": "gain_m", "target": "target", "amount": 2}),
        formal={"kind": "value", "formula": "├$2"},
    ),
    theorem(
        "axiom_k", "├$0>($1>$0)", 4, 2,
        "最基础的推理规则之一，或许有更多的用处。",
        flavor_en="One of the most basic inference rules. It may have more uses.",
    ),
    theorem(
        "axiom_s", "├($0>($1>$2))>(($0>$1)>($0>$2))", 2, 3,
        "你不会真期望靠它来触发最后推理效果吧？",
        flavor_en="You are not really expecting to reach its final inference, are you?",
    ),
    card(
        "contraposition", "($0>$1)├(¬$1>¬$0)", "($0>$1)├(¬$1>¬$0)",
        0, 2, "bloom", 2,
        "选择自己1张结论为蕴含式的手牌置入弃牌堆；将其逆否形式加入手中，保留其状态与标签，并使其获得推理放逐",
        "否！定！爆！炸！",
        effect_en="Discard one implication-formula card from your hand. Add its contraposition to your hand, preserving its state and tags, and grant it Inference Exile.",
        flavor_en="Ne! Ga! Tion! Explosion!",
        flags=["self_only"],
        formal={"kind": "contraposition", "formula": "($0>$1)├(¬$1>¬$0)", "formula_name": True},
    ),
    card(
        "inverse_deduction", "逆演绎元定理", "Inverse Deduction Metatheorem",
        0, 6, "bloom", 2,
        "选择自己1张形如…├$0>($1>…)的手牌放逐；将其变为…，$0├$1>…后加入手中（├右侧至少有1个变量）",
        "对了吗？哦对的对的对的。",
        effect_en="Exile one card in your hand of the form ...├$0>($1>...). Add it back as ...,$0├$1>... (at least one variable must remain right of ├).",
        flavor_en="Is it right? Oh yes, yes it is.",
        flags=["self_only", "exile"],
        formal={"kind": "inverse_deduction"},
    ),
    card(
        "mp", "mp", "mp", 2, 0, "root", 2,
        "装备1回合后可触发：选择自己手中2张可合一的公式牌，以mp生成1张定理牌并加入手中；随后摧毁此装备",
        "让让，我赶时间。",
        effect_en="After 1 equipped turn, trigger to choose 2 unifiable formula cards in your hand and generate their modus-ponens theorem; then destroy this equipment.",
        flavor_en="Move. I am in a hurry.",
        flags=["self_only"],
        events={
            "on_equipment_trigger": {
                "max_uses_per_turn": 1,
                "steps": [{"op": "log", "message": ""}],
            }
        },
        formal={"kind": "mp"},
        trigger_cost_e=0,
        trigger_effect_text="选择2张公式牌执行mp",
    ),
    card(
        "deduction_metatheorem", "演绎元定理", "Deduction Metatheorem",
        3, 0, "guard", 2,
        "响应目标的代入被清除或其使用逆演绎元定理：改变对应公式；若无法改变，则使本次逆演绎元定理失效",
        "错了吗？哦对的对的对的。",
        effect_en="Respond when a target clears Substitution or uses Inverse Deduction Metatheorem: alter the affected formula; if it cannot be altered, invalidate that inverse deduction.",
        flavor_en="Is it wrong? Oh yes, yes it is.",
        formal={"kind": "deduction_response"},
    ),
    card(
        "macro", "宏定义", "Macro Definition", 0, 0, "bloom", 2,
        "选择自己1张手牌放逐并将1张复制加入弃牌堆；自动装备对应的不可摧毁宏。宏每回合可触发1次，生成1张具有虚无与原标签、但不产生数值效果的代理牌；代理牌每打出1次，之后生成的代理牌获得1层沉重",
        "烂记性不如好笔头。",
        effect_en="Exile a card from your hand and put a copy in your discard pile, then equip its indestructible Macro. Once per turn, the Macro creates a Void proxy with the original tags but no numeric effects. Each proxy play adds 1 Heavy to future proxies.",
        flavor_en="The faintest ink is better than the best memory.",
        flags=["self_only"],
        formal={"kind": "macro"},
    ),
    card(
        "generalization", "条件概括元定理", "Generalization Metatheorem",
        0, 0, "thorn", 1,
        "使目标所有符合条件的公式牌获得全称量词，持续至其回合结束；再选择另1名非其队友的目标，使其获得等同于被改变牌数的血债",
        "├∀NaN：最帅。",
        effect_en="Universally quantify every eligible formula card owned by the target until that target's turn ends. Then choose another non-teammate target to gain Blood Debt equal to the number of changed cards.",
        flavor_en="├∀NaN: the coolest.",
        flags=["self_target"],
        events=target_steps(),
        formal={"kind": "generalization"},
    ),
    theorem(
        "identity", "├$0>$0", 0, 1,
        "醒醒，是├$0>$0！",
        flavor_en="Wake up. This one is ├$0>$0!",
        debut_effect="double_first_card",
        debut_text_cn="本回合打出的第1张牌额外结算1次",
        debut_text_en="The first card played this turn resolves one additional time.",
    ),
    theorem(
        "double_negation_intro", "├$0>¬¬$0", 0, 1,
        "是否定爆炸大人，我们有救了。",
        flavor_en="Lord Negation Explosion is here. We are saved.",
        rebound=False,
        debut_effect="zero_e",
        debut_text_cn="选择自己1张手牌，将其E消耗永久改为0；本场对局若此牌已登场过，改为持续至本回合结束",
        debut_text_en="Choose a card in your hand and permanently set its E cost to 0. After the first Debut this match, this lasts until turn end instead.",
        reset_mode="after_inference",
    ),
    theorem(
        "double_negation_elim", "├¬¬$0>$0", 0, 1,
        "我说某个回转共生大人无敌了，你耳朵聋吗？",
        flavor_en="I said a certain Rebound-Symbiosis lord is invincible. Are you deaf?",
        rebound=False,
        debut_effect="zero_em",
        debut_text_cn="选择自己1张手牌，将其E与M消耗永久改为0；本场对局若此牌已登场过，改为持续至本回合结束",
        debut_text_en="Choose a card in your hand and permanently set both costs to 0. After the first Debut this match, this lasts until turn end instead.",
        reset_mode="after_inference",
    ),
    theorem(
        "explosion", "$0，¬$0├$1", 0, 2,
        "命运抽签：所以呢？",
        flavor_en="Fate Draw: So what?",
        rebound=False,
        debut_effect="play_from_pool",
        debut_text_cn="从总牌库中选择1张牌打出",
        debut_text_en="Choose and play a card from the complete card pool.",
        reset_mode="after_inference",
    ),
    theorem(
        "transitivity", "$0>$1，$1>$2├$0>$2", 0, 3,
        "一条直线通向结论。",
        flavor_en="A straight line leads to the conclusion.",
        debut_effect="heal_5",
        debut_text_cn="回复自己5H",
        debut_text_en="Restore 5H to yourself.",
        reset_mode="after_inference",
    ),
    theorem(
        "exchange", "├($0>($1>$2))>($1>($0>$2))", 0, 3,
        "交换前提的顺序。",
        flavor_en="Exchange the order of the premises.",
        rebound=False,
        debut_effect="gain_and_swap",
        debut_text_cn="自己的H增加向上取整(当前H/10)，E与M各增加1；再选择其中2项交换当前值",
        debut_text_en="Increase H by ceil(current H/10) and gain 1 E and 1 M, then swap the current values of two of them.",
        reset_mode="after_inference",
    ),
    card(
        "generated_theorem", "生成定理", "Generated Theorem", 1, 0, "thorn", 0,
        "按公式依次完成代入与推理",
        "推理所得。",
        effect_en="Complete substitution and inference according to this formula.",
        flavor_en="Derived by inference.",
        flags=["rebound", "symbiosis", "self_target", "exile"],
        events=target_steps(),
        formal={"kind": "theorem", "formula_name": True, "reset_mode": "after_inference"},
    ),
    card(
        "macro_equipment", "宏", "Macro", 0, 0, "root", 0,
        "每回合可触发1次：生成对应代理牌",
        "被写下的定义。",
        effect_en="Once per turn, create the linked proxy card.",
        flavor_en="A definition written down.",
        flags=["indestructible", "self_only"],
        events={
            "on_equipment_trigger": {
                "max_uses_per_turn": 1,
                "steps": [{"op": "log", "message": ""}],
            }
        },
        formal={"kind": "macro_equipment"},
        trigger_cost_e=0,
        trigger_effect_text="生成对应代理牌",
    ),
]


data = {
    "format_version": 2,
    "manifest": {
        "id": "formal_logic",
        "name": "Formal Logic Reasoning",
        "name_cn": "形式逻辑推理模组",
        "name_en": "Formal Logic Reasoning",
        "version": "1.0.0",
        "api_version": "2.0",
        "author": "NaN",
        "description": "以公式代入、推理和元定理为核心的娱乐模组。",
        "description_en": "An entertainment mod centered on formula substitution, inference, and metatheorems.",
        "category": "entertainment",
        "capabilities": [
            "cards", "tags", "statuses", "opening_events",
            "ui_components", "ui.modal", "ui.choice",
            "logic.basic", "logic.advanced",
        ],
        "default_language": "zh",
    },
    "registries": {
        "tags": [
            {
                "id": "formal_logic:debut",
                "name_cn": "登场",
                "name_en": "Debut",
                "description": "进入手牌时触发登场效果。",
                "description_i18n": {
                    "zh": "进入手牌时触发登场效果。",
                    "en": "Triggers its Debut effect when it enters your hand.",
                },
                "color": "#E6A23C",
            },
            {
                "id": "formal_logic:inference_exile",
                "name_cn": "推理放逐",
                "name_en": "Inference Exile",
                "description": "完成此牌的推理后，放逐此牌。",
                "description_i18n": {
                    "zh": "完成此牌的推理后，放逐此牌。",
                    "en": "Exile this card after completing its inference.",
                },
                "color": "#8754C7",
            },
        ],
        "statuses": [
            {
                "id": "formal_logic:substitution",
                "name_cn": "代入",
                "name_en": "Substitution",
                "description": "打出的下一张牌会替换来源公式中从左到右第1个未代入变量；随后清除代入。代入失败也会清除。",
                "description_i18n": {
                    "zh": "打出的下一张牌会替换来源公式中从左到右第1个未代入变量；随后清除代入。代入失败也会清除。",
                    "en": "The next card played replaces the first unbound variable in the source formula, then Substitution clears. It also clears on failure.",
                },
                "color": "#4F83CC",
                "visible": True,
                "stacking": "unique",
            },
            {
                "id": "formal_logic:inference",
                "name_cn": "推理",
                "name_en": "Inference",
                "description": "接下来打出的牌依次与来源公式待推理项比较；全部符合且前提、消耗与目标均满足时，自动打出结论牌。失败后清除推理。",
                "description_i18n": {
                    "zh": "接下来打出的牌依次与来源公式待推理项比较；全部符合且前提、消耗与目标均满足时，自动打出结论牌。失败后清除推理。",
                    "en": "Subsequent plays are matched against the source formula in order. If all items, premises, costs, and targets are valid, its conclusion is played automatically. Clears on failure.",
                },
                "color": "#B56BC7",
                "visible": True,
                "stacking": "unique",
            },
        ],
        "cards": cards,
        "opening_events": [
            {
                "id": "formal_logic:great_mathematician",
                "name_cn": "大数学家",
                "name_en": "Great Mathematician",
                "description": "选牌阶段中，形式逻辑推理模组牌的出现权重变为5倍；每回合可以少抽1张牌，改为从该模组选择1张牌加入手中。",
                "description_i18n": {
                    "zh": "选牌阶段中，形式逻辑推理模组牌的出现权重变为5倍；每回合可以少抽1张牌，改为从该模组选择1张牌加入手中。",
                    "en": "Formal Logic cards have 5x draft weight. Once per turn, you may draw 1 fewer card and choose a Formal Logic card to add to your hand.",
                },
                "position": 3,
                "events": {"on_apply": {"steps": []}},
            }
        ],
        "ui_components": [],
    },
    "patches": [],
    "compatibility": [],
    "event_hooks": [],
}


def locale_document(language):
    use_chinese = language == "zh"
    card_rows = {}
    for item in cards:
        i18n_name = item.get("name_i18n", {})
        i18n_effect = item.get("effect_text_i18n", {})
        i18n_description = item.get("description_i18n", {})
        card_rows[item["id"]] = {
            "name": i18n_name.get("zh" if use_chinese else "en", item.get("name_cn") if use_chinese else item.get("name_en")),
            "effect_text": i18n_effect.get("zh" if use_chinese else "en", item.get("effect_text", "")),
            "description": i18n_description.get("zh" if use_chinese else "en", item.get("description", "")),
        }
    return {
        "manifest": {
            "name": "形式逻辑推理模组" if use_chinese else "Formal Logic Reasoning",
            "description": (
                "以公式代入、推理和元定理为核心的娱乐模组。"
                if use_chinese
                else "An entertainment mod centered on formula substitution, inference, and metatheorems."
            ),
        },
        "cards": card_rows,
    }


def main():
    payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    temporary = f"{OUTPUT}.tmp"
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr("mod.json", payload)
        for language in ("zh", "en", "fr", "ja"):
            locale = locale_document(language)
            archive.writestr(
                f"locales/{language}.json",
                json.dumps(locale, ensure_ascii=False, indent=2).encode("utf-8"),
            )
    os.replace(temporary, OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
