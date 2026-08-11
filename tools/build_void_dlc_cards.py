from __future__ import annotations

import copy
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"
ART_SOURCE = ROOT / "新dlc贴图"

LANGUAGES = ("zh", "en", "fr", "ja")


def steps(*items):
    return {"steps": list(items)}


def action(name: str, **params):
    return {"op": "void_dlc_action", "action": name, **params}


def target_event(*items):
    return {"on_play": steps({"op": "request_target", "allowed": "any"}, *items)}


def equip_events(*, self_only: bool = False, extra=None):
    play = [] if self_only else [{"op": "request_target", "allowed": "any"}]
    play.append({"op": "place_as_equip", **({} if self_only else {"effect_target": "target"})})
    events = {"on_play": steps(*play)}
    events.update(extra or {})
    return events


def card(
    namespace: str,
    local_id: str,
    legacy_id: str,
    names: dict,
    cost_e: int,
    cost_m: int,
    card_type: str,
    effect: dict,
    flavor: dict,
    image: str,
    *,
    count: int = 3,
    flags=None,
    tags=None,
    events=None,
    damage: int = 0,
    hits: int = 1,
    copy_count: int = 0,
    charge_value: int = 0,
    response_trigger: str = "",
    trigger_cost_e: int = -1,
    trigger_cost_m: int = 0,
    trigger_effect=None,
):
    result = {
        "id": f"{namespace}:{local_id}",
        "legacy_id": legacy_id,
        "name_cn": names["zh"],
        "name_en": names["en"],
        "name_i18n": dict(names),
        "cost_e": cost_e,
        "cost_m": cost_m,
        "card_type": card_type,
        "count": count,
        "quality": "Unusual",
        "description": flavor["zh"],
        "description_i18n": dict(flavor),
        "effect_text": effect["zh"],
        "effect_text_en": effect["en"],
        "effect_text_i18n": dict(effect),
        "flags": list(flags or []),
        "tags": list(tags or []),
        "response_trigger": response_trigger,
        "trigger_cost_e": trigger_cost_e,
        "trigger_cost_m": trigger_cost_m,
        "trigger_effect_text": (trigger_effect or {}).get("zh", ""),
        "trigger_effect_text_i18n": dict(trigger_effect or {}),
        "events": events or {},
        "assets": {"image": f"card-art/{image}"},
        "damage": damage,
        "hits": hits,
    }
    if copy_count:
        result["copy_count"] = copy_count
    if charge_value:
        result["charge_value"] = charge_value
    return result


def text(zh: str, en: str, fr: str | None = None, ja: str | None = None):
    return {"zh": zh, "en": en, "fr": fr or en, "ja": ja or en}


BIO_CARDS = [
    card(
        "bio", "mask", "Mask",
        text("口罩", "Mask", "Masque", "マスク"),
        1, 0, "root",
        text(
            "存在时，使目标的剧毒和淬毒有效层数各减少1",
            "While present, reduce the target's effective Toxic Poison and Poison Coating stacks by 1 each.",
            "Tant qu'il est présent, réduit de 1 les cumuls effectifs de Poison virulent et d'Enduit toxique de la cible.",
            "存在中、対象の劇毒と淬毒の有効スタックをそれぞれ1減らす",
        ),
        text(
            "它能保护你免受ZARS-CoV-69的侵害，也能减弱其影响。",
            "It protects you from ZARS-CoV-69 and weakens its effects.",
            "Il vous protège du ZARS-CoV-69 et en atténue les effets.",
            "ZARS-CoV-69から身を守り、その影響も弱める。",
        ),
        "mask.svg", flags=["unique"], events=equip_events(),
    ),
    card(
        "bio", "magic_mask", "MagicMask",
        text("魔法口罩", "Magic Mask", "Masque magique", "魔法マスク"),
        0, 2, "root",
        text(
            "存在时，使目标的剧毒、淬毒和失明有效层数各减少1",
            "While present, reduce the target's effective Toxic Poison, Poison Coating, and Blindness stacks by 1 each.",
            "Tant qu'il est présent, réduit de 1 les cumuls effectifs de Poison virulent, d'Enduit toxique et de Cécité de la cible.",
            "存在中、対象の劇毒、淬毒、失明の有効スタックをそれぞれ1減らす",
        ),
        text(
            "减少迷雾对你视角的影响。它也能使你免受ZARS-CoV-69的侵害。",
            "It clears the haze from your vision and protects you from ZARS-CoV-69.",
            "Il dissipe la brume de votre vision et vous protège du ZARS-CoV-69.",
            "視界の霧を薄め、ZARS-CoV-69からも守ってくれる。",
        ),
        "magic mask.svg", flags=["unique"], events=equip_events(),
    ),
]


FACTORY_CARDS = [
    card(
        "factory", "bomb", "Bomb", text("炸弹", "Bomb", "Bombe", "爆弾"),
        4, 0, "thorn",
        text(
            "对目标造成6[[icon:D]]，并对其施加1层超载和1层虚弱",
            "Deal 6[[icon:D]] to the target and apply 1 Overload and 1 Weakness.",
            "Inflige 6[[icon:D]] à la cible et lui applique 1 Surcharge et 1 Faiblesse.",
            "対象に6[[icon:D]]を与え、超载と虚弱を1ずつ付与する",
        ),
        text("轰！！！", "BOOM!!!", "BOUM !!!", "ドカン！！！"),
        "bomb.svg", flags=["wide_strike"], events={"on_play": steps(action("bomb_attack", damage=6))}, damage=6,
    ),
    card(
        "factory", "fire_bomb", "FireBomb", text("火焰炸弹", "Fire Bomb", "Bombe incendiaire", "火炎爆弾"),
        6, 0, "thorn",
        text(
            "对目标造成16[[icon:D]]，并对其施加3层烈火",
            "Deal 16[[icon:D]] to the target and apply 3 Blaze.",
            "Inflige 16[[icon:D]] à la cible et lui applique 3 Feu ardent.",
            "対象に16[[icon:D]]を与え、烈火を3付与する",
        ),
        text("这次的爆炸会让你的敌人着火。", "This explosion sets your enemies ablaze.", "Cette explosion embrase vos ennemis.", "今度の爆発は敵を燃え上がらせる。"),
        "fire bomb.svg", flags=["wide_strike"], events={"on_play": steps(action("fire_bomb_attack", damage=16, blaze=3))}, damage=16,
    ),
    card(
        "factory", "magic_bomb", "MagicBomb", text("魔法炸弹", "Magic Bomb", "Bombe magique", "魔法爆弾"),
        1, 7, "thorn",
        text(
            "对目标造成20[[icon:D]]，并对其施加1层眩晕",
            "Deal 20[[icon:D]] to the target and apply 1 Stun.",
            "Inflige 20[[icon:D]] à la cible et lui applique 1 Étourdissement.",
            "対象に20[[icon:D]]を与え、眩晕を1付与する",
        ),
        text("创造出强力的爆炸，但需要魔法。", "A powerful explosion, fueled by magic.", "Une puissante explosion alimentée par la magie.", "魔力を燃料にした強烈な爆発。"),
        "magic bomb.svg", flags=["rebound", "wide_strike"], events={"on_play": steps(action("magic_bomb_attack", damage=20))}, damage=20,
    ),
    card(
        "factory", "magic_fire_bomb", "MagicFireBomb", text("魔法火焰炸弹", "Magic Fire Bomb", "Bombe incendiaire magique", "魔法火炎爆弾"),
        0, 10, "thorn",
        text(
            "对目标造成20[[icon:D]]，并对其施加5层烈火",
            "Deal 20[[icon:D]] to the target and apply 5 Blaze.",
            "Inflige 20[[icon:D]] à la cible et lui applique 5 Feu ardent.",
            "対象に20[[icon:D]]を与え、烈火を5付与する",
        ),
        text("魔法使它烧得更旺了。", "Magic makes it burn even brighter.", "La magie attise encore ses flammes.", "魔法でさらに激しく燃え上がる。"),
        "magic fire bomb.svg", flags=["wide_strike", "rebound", "revealed"], events={"on_play": steps(action("fire_bomb_attack", damage=20, blaze=5))}, damage=20,
    ),
    card(
        "factory", "pipe_bomb", "PipeBomb", text("管状炸弹", "Pipe Bomb", "Bombe artisanale", "パイプ爆弾"),
        2, 0, "thorn",
        text(
            "每次命中时，随机对目标造成25[[icon:D]]或0[[icon:D]]",
            "On each hit, randomly deal either 25[[icon:D]] or 0[[icon:D]] to the target.",
            "À chaque impact, inflige aléatoirement 25[[icon:D]] ou 0[[icon:D]] à la cible.",
            "各命中時、対象に25[[icon:D]]または0[[icon:D]]をランダムに与える",
        ),
        text("泰德·卡辛斯基为你精心制作:3", "Carefully handcrafted for you by Ted Kaczynski :3", "Soigneusement fabriquée pour vous par Ted Kaczynski :3", "テッド・カジンスキーが心を込めて作りました :3"),
        "pipe bomb.svg", flags=["wide_strike", "self_target"], events={"on_play": steps(action("pipe_bomb_attack", damage=25))}, damage=25,
    ),
]


VOID_CARDS = [
    card(
        "void", "dvd", "DVD", text("光盘", "DVD", "DVD", "DVD"), 2, 0, "thorn",
        text(
            "对目标造成6[[icon:D]]并施加1层[[icon:F]]；下个自己回合开始时，若此牌仍在弃牌堆，则回到手中",
            "Deal 6[[icon:D]] to the target and apply 1[[icon:F]]. At the start of your next turn, return this card to your hand if it is still in your discard pile.",
            "Inflige 6[[icon:D]] à la cible et lui applique 1[[icon:F]]. Au début de votre prochain tour, renvoie cette carte en main si elle est toujours dans votre défausse.",
            "対象に6[[icon:D]]を与え、1[[icon:F]]を付与する。次の自分のターン開始時、このカードが捨て札にあれば手札に戻す",
        ),
        text("包含一些前所未见的外星人录像。", "It contains never-before-seen footage of aliens.", "Il contient des images inédites d'extraterrestres.", "未公開の宇宙人映像が収録されている。"),
        "dvd.svg", events={"on_play": steps(action("dvd_attack", damage=6)), "on_discard_owner_turn_start": steps(action("dvd_return"))}, damage=6,
    ),
    card(
        "void", "fan", "Fan", text("扇子", "Fan", "Éventail", "扇子"), 3, 0, "root",
        text(
            "目标回合开始时，装备拥有者可花费2[[icon:E]]，移除目标1层[[icon:F]]",
            "At the start of the target's turn, the equipment owner may spend 2[[icon:E]] to remove 1[[icon:F]] from the target.",
            "Au début du tour de la cible, le propriétaire peut dépenser 2[[icon:E]] pour retirer 1[[icon:F]] à la cible.",
            "対象のターン開始時、装備者は2[[icon:E]]を消費して対象の[[icon:F]]を1減らせる",
        ),
        text("降低你将受到的燃烧效果。", "It cools the flames waiting for you.", "Il atténue les flammes qui vous attendent.", "迫る炎を少し和らげる。"),
        "fan.svg", flags=["non_stackable"], events=equip_events(extra={"on_owner_turn_start": steps(action("fan_turn_start"))}),
    ),
    card(
        "void", "capacitor", "Capacitor", text("电容器", "Capacitor", "Condensateur", "コンデンサー"), 3, 0, "bloom",
        text("对目标所有手牌施加1层电荷", "Apply 1 Charge to every card in the target's hand.", "Applique 1 Charge à toutes les cartes de la main de la cible.", "対象の全手札に電荷を1付与する"),
        text("我是什么都不会告诉你的！额啊啊啊啊啊——", "I won't tell you anything! AAAAAARGH—", "Je ne vous dirai rien ! AAAAAARGH—", "何も教えないぞ！うわあああああ——"),
        "capacitor.svg", flags=["wide_strike"], tags=["charge"], charge_value=1, events={"on_play": steps(action("charge_hand", amount=1))},
    ),
    card(
        "void", "copper_rod", "CopperRod", text("铜棒", "Copper Rod", "Tige de cuivre", "銅の棒"), 2, 0, "guard",
        text("清除自己所有手牌的电荷，并使所响应的效果失效  响应：自己的手牌将被施加电荷", "Clear all Charge from your hand and negate the responding effect.  Response: Charge would be applied to your hand.", "Retire toute Charge de votre main et annule l'effet correspondant.  Réponse : votre main va recevoir de la Charge.", "自分の全手札の電荷を消去し、対応する効果を無効にする  応答：自分の手札に電荷が付与される時"),
        text("它吸收即将来临的闪电。", "It absorbs the lightning on its way.", "Elle absorbe la foudre qui approche.", "迫り来る雷を吸収する。"),
        "copper rod.svg", response_trigger="hand_charge", events={"on_response": steps(action("copper_rod_response"))},
    ),
    card(
        "void", "plasma", "Plasma", text("等离子体", "Plasma", "Plasma", "プラズマ"), 6, 0, "thorn",
        text("对目标施加2层[[icon:P]]、2层[[icon:F]]，随机为其1张手牌施加2层电荷，再对其依次造成5[[icon:D]]和5[[icon:electric_damage]]", "Apply 2[[icon:P]] and 2[[icon:F]] to the target, apply 2 Charge to a random card in their hand, then deal 5[[icon:D]] and 5[[icon:electric_damage]] in sequence.", "Applique 2[[icon:P]] et 2[[icon:F]] à la cible, applique 2 Charge à une carte aléatoire de sa main, puis inflige successivement 5[[icon:D]] et 5[[icon:electric_damage]].", "対象に2[[icon:P]]と2[[icon:F]]を付与し、手札1枚にランダムで電荷2を付与した後、5[[icon:D]]と5[[icon:electric_damage]]を順に与える"),
        text("物质的极热状态。", "Matter in an extremely hot state.", "La matière dans un état extrêmement chaud.", "物質の超高温状態。"),
        "plasma.svg", flags=["void", "unique"], events={"on_play": steps(action("plasma_attack"))}, damage=5,
    ),
    card(
        "void", "attractor", "Attractor", text("吸引器", "Attractor", "Attracteur", "引力装置"), 1, 0, "bloom",
        text("对目标施加1层仅攻击", "Apply 1 Attack Only to the target.", "Applique 1 Attaque uniquement à la cible.", "対象に仅攻击を1付与する"),
        text("吸引你的敌人来攻击你。", "It draws your enemies into attacking you.", "Il attire vos ennemis et les pousse à vous attaquer.", "敵を引き寄せ、攻撃へと誘う。"),
        "attractor.svg", events=target_event(action("apply_status", status="attack_only", amount=1)),
    ),
    card(
        "void", "magic_slime_ball", "MagicSlimeBall", text("魔法黏液球", "Magic Slime Ball", "Boule de slime magique", "魔法スライムボール"), 1, 6, "thorn",
        text("对目标施加1层眩晕，对自己施加1层迟缓；此牌的放逐副本获得魔力迅捷2", "Apply 1 Stun to the target and 1 Sluggish to yourself. Exiled copies of this card gain Magic Swift 2.", "Applique 1 Étourdissement à la cible et 1 Lenteur à vous-même. Les copies bannies de cette carte gagnent Célérité magique 2.", "対象に眩晕1、自分に迟缓1を付与する。このカードの放逐コピーは魔力迅捷2を得る"),
        text("这个版本有负击退，额呃呃呃呃呃——", "This version has negative knockback—urrghhh—", "Cette version a un recul négatif—euurgh—", "この型はノックバックが逆向きだ、うぐぐぐ——"),
        "magic slime ball.svg", flags=["uncancellable", "copy", "void"], events={"on_play": steps(action("magic_slime_ball"))}, copy_count=2,
    ),
    card(
        "void", "mysterious_orb", "MysteriousOrb", text("球", "Mysterious Orb", "Orbe mystérieux", "謎の球体"), 2, 1, "thorn",
        text("对目标造成10[[icon:D]]", "Deal 10[[icon:D]] to the target.", "Inflige 10[[icon:D]] à la cible.", "対象に10[[icon:D]]を与える"),
        text("这里面似乎有许多未知的外星科技……", "It seems packed with unknown alien technology...", "Elle semble renfermer une technologie extraterrestre inconnue…", "未知の異星技術が詰まっているようだ……"),
        "mysterious orb.svg", flags=["rebound", "symbiosis", "unique", "sublime"], events={"on_play": steps({"op": "deal_damage", "target": "target", "amount": 10})}, damage=10,
    ),
    card(
        "void", "schizo", "Schizo", text("精神分裂症", "Schizo", "Schizo", "スキゾ"), 3, 5, "root",
        text("自己回合开始时，可花费2[[icon:M]]，选择一个目标，展示其所有手牌并对其造成10[[icon:D]]", "At the start of your turn, you may spend 2[[icon:M]] to choose a target, reveal their entire hand, and deal 10[[icon:D]] to them.", "Au début de votre tour, vous pouvez dépenser 2[[icon:M]] pour choisir une cible, révéler toute sa main et lui infliger 10[[icon:D]].", "自分のターン開始時、2[[icon:M]]を消費して対象を1人選び、その全手札を公開して10[[icon:D]]を与えられる"),
        text("拿上它，你就是21st Century Schizoid Man。", "Take it, and you are the 21st Century Schizoid Man.", "Prenez-le, et vous serez le 21st Century Schizoid Man.", "手にすれば、君も21st Century Schizoid Man。"),
        "schizo.svg", flags=["indestructible", "sewers:confusion", "self_only"], events=equip_events(self_only=True, extra={"on_owner_turn_start": steps(action("schizo_turn_start"))}),
    ),
    card(
        "void", "illuminati_triangle", "IlluminatiTriangle", text("光明会三角", "Illuminati Triangle", "Triangle des Illuminati", "イルミナティ・トライアングル"), 0, 0, "thorn",
        text("对目标造成5[[icon:D]]，再从所有官方模组状态中随机选择5种，各对其施加1层；本回合结束时移除本牌施加的这些层数", "Deal 5[[icon:D]] to the target, then randomly choose 5 statuses from all official mods and apply 1 of each. Remove the stacks applied by this card at the end of this turn.", "Inflige 5[[icon:D]] à la cible, puis choisit aléatoirement 5 états parmi tous les mods officiels et en applique 1 de chaque. Retire les cumuls appliqués par cette carte à la fin de ce tour.", "対象に5[[icon:D]]を与え、全公式MODの状態からランダムに5種を選んで1ずつ付与する。このカードが付与した分はこのターン終了時に取り除く"),
        text("能够对敌人施加各种状态。", "It can inflict all manner of statuses.", "Il peut infliger toutes sortes d'états.", "ありとあらゆる状態を与えられる。"),
        "illuminati triangle.svg", events={"on_play": steps(action("illuminati_triangle", damage=5, status_count=5))}, damage=5,
    ),
    card(
        "void", "void_mark", "VoidMark", text("虚空标记", "Void Mark", "Marque du Néant", "虚空の印"), 4, 0, "root",
        text("已装备1回合时，可触发：选择一个目标，对其施加3层失明", "After being equipped for 1 turn, it may trigger: choose a target and apply 3 Blindness.", "Après avoir été équipé pendant 1 tour, peut se déclencher : choisissez une cible et appliquez-lui 3 Cécité.", "装備から1ターン経過後、発動可能：対象を1人選び、失明を3付与する"),
        text("从虚无之中诞生，也将归为虚无。", "Born from the void, destined to return to it.", "Née du Néant, destinée à y retourner.", "虚無より生まれ、いずれ虚無へ還る。"),
        "void mark.svg", flags=["void", "revealed", "self_only"], events=equip_events(self_only=True, extra={"on_equipment_trigger": steps({"op": "request_target", "allowed": "any"}, action("apply_status", status="blind", amount=3))}), trigger_cost_e=0, trigger_effect=text("选择一个目标，对其施加3层失明", "Choose a target and apply 3 Blindness.", "Choisissez une cible et appliquez-lui 3 Cécité.", "対象を1人選び、失明を3付与する"),
    ),
    card(
        "void", "cicada_3301", "Cicada3301", text("蝉3301", "Cicada 3301", "Cicada 3301", "Cicada 3301"), 7, 0, "bloom",
        text("对所有目标施加3层失明，再丢弃自己2张其他手牌；然后选择：清空一个目标的手牌；复活一个目标并使其[[icon:H]]变为上限的5%；或重排所有敌方抽牌堆，再使每名存活己方玩家从中选择1张牌加入自己手中", "Apply 3 Blindness to every player, then discard 2 other cards from your hand. Choose one: clear a target's hand; revive a target at 5% of maximum [[icon:H]]; or shuffle every enemy draw pile, then let each living ally choose 1 card from them to add to their own hand.", "Applique 3 Cécité à tous les joueurs, puis défausse 2 autres cartes de votre main. Choisissez : vider la main d'une cible ; ranimer une cible à 5 % de son [[icon:H]] maximum ; ou mélanger toutes les pioches ennemies, puis laisser chaque allié vivant y choisir 1 carte à ajouter à sa main.", "全員に失明を3付与し、自分の他の手札を2枚捨てる。その後1つ選ぶ：対象1人の手札を空にする；対象1人を最大[[icon:H]]の5%で復活させる；または全敵の山札を並べ直し、生存中の味方がそこから1枚ずつ自分の手札に加える"),
        text("我们将允许您加入我们的组织直至3301年。", "We will allow you to join our organization until the year 3301.", "Nous vous permettrons de rejoindre notre organisation jusqu'en 3301.", "3301年まで、我々の組織への参加を認めよう。"),
        "cicada 3301.svg", flags=["revealed", "self_only"], events={"on_play": steps(action("cicada_3301"))},
    ),
    card(
        "void", "thorn_missile", "HeatedThorn", text("棘刺", "Thorn", "Épine", "棘"), 4, 0, "thorn",
        text("对目标造成6[[icon:D]]并施加1层烈火；造成实际伤害时，额外打出1张[[card:HeatedThorn]]（广域打击）（裂变:3）", "Deal 6[[icon:D]] to the target and apply 1 Blaze. When actual damage is dealt, additionally play 1 [[card:HeatedThorn]] with Wide Strike and Fission 3.", "Inflige 6[[icon:D]] à la cible et lui applique 1 Feu ardent. Après avoir infligé des dégâts réels, joue en plus 1 [[card:HeatedThorn]] avec Frappe étendue et Fission 3.", "対象に6[[icon:D]]を与え、烈火を1付与する。実ダメージを与えた時、広域打击と裂变3を持つ[[card:HeatedThorn]]を1枚追加で打ち出す"),
        text("一个被加热了的自分裂导弹。", "A heated, self-splitting missile.", "Un missile chauffé qui se divise tout seul.", "熱せられた自己分裂ミサイル。"),
        "thorn.svg", events={"on_play": steps(action("heated_thorn", damage=6))}, damage=6,
    ),
    card(
        "void", "magic_copper_rod", "MagicCopperRod", text("魔法铜棒", "Magic Copper Rod", "Tige de cuivre magique", "魔法の銅棒"), 2, 0, "root",
        text("目标将受到一次[[icon:electric_damage]]时，装备拥有者可花费1[[icon:M]]吸收该次伤害，并使目标所有手牌的电荷减少1层", "When the target would take one [[icon:electric_damage]] hit, the equipment owner may spend 1[[icon:M]] to absorb it and reduce Charge on every card in the target's hand by 1.", "Quand la cible va subir un impact de [[icon:electric_damage]], le propriétaire peut dépenser 1[[icon:M]] pour l'absorber et réduire de 1 la Charge de chaque carte de la main de la cible.", "対象が1回の[[icon:electric_damage]]を受ける時、装備者は1[[icon:M]]を消費してそのダメージを吸収し、対象の全手札の電荷を1減らせる"),
        text("它会像棉花一样吸收即将来临的闪电。", "It soaks up incoming lightning like cotton.", "Elle absorbe la foudre comme du coton.", "綿のように迫る雷を吸い取る。"),
        "magic copper rod.svg", flags=["floating"], events=equip_events(),
    ),
    card(
        "void", "nut", "Nut", text("橡果", "Nut", "Gland", "ドングリ"), 8, 0, "thorn",
        text("对目标造成25[[icon:D]]；自己的手牌、抽牌堆、弃牌堆和放逐区中，每有1张额外的橡果，此牌的基础[[icon:E]]消耗向下取整减半", "Deal 25[[icon:D]] to the target. For each additional Nut in your hand, draw pile, discard pile, or exile, halve this card's base [[icon:E]] cost, rounded down.", "Inflige 25[[icon:D]] à la cible. Pour chaque Gland supplémentaire dans votre main, pioche, défausse ou bannissement, réduit de moitié le coût de base en [[icon:E]] de cette carte, arrondi à l'inférieur.", "対象に25[[icon:D]]を与える。自分の手札・山札・捨て札・放逐にある追加の橡果1枚につき、このカードの基本[[icon:E]]消費を切り捨てで半分にする"),
        text("似乎不适合单打独斗。", "It does not seem suited to fighting alone.", "Il ne semble pas fait pour combattre seul.", "単独で戦うのには向いていないようだ。"),
        "nut.svg", flags=["exile", "unique"], events={"on_play": steps({"op": "deal_damage", "target": "target", "amount": 25})}, damage=25,
    ),
    card(
        "void", "comb", "Comb", text("梳子", "Comb", "Peigne", "くし"), 8, 4, "bloom",
        text("对目标施加1层烈火、1层[[icon:F]]、1层剧毒和1层[[icon:P]]", "Apply 1 Blaze, 1[[icon:F]], 1 Toxic Poison, and 1[[icon:P]] to the target.", "Applique 1 Feu ardent, 1[[icon:F]], 1 Poison virulent et 1[[icon:P]] à la cible.", "対象に烈火1、[[icon:F]]1、剧毒1、[[icon:P]]1を付与する"),
        text("花是秃头，这一点可真是太可惜了。", "It is a shame that flowers are bald.", "Quel dommage que les fleurs soient chauves.", "花が禿げているのは本当に残念だ。"),
        "comb.svg", flags=["unique", "void"], events=target_event(action("comb_statuses")),
    ),
    card(
        "void", "stardust", "Stardust", text("星尘", "Stardust", "Poussière d'étoile", "星屑"), 3, 0, "bloom",
        text("对目标施加1层剧毒", "Apply 1 Toxic Poison to the target.", "Applique 1 Poison virulent à la cible.", "対象に剧毒を1付与する"),
        text("诞生于星辰之间。", "Born among the stars.", "Née parmi les étoiles.", "星々の間で生まれた。"),
        "stardust.svg", flags=["wide_strike"], events={"on_play": steps(action("apply_status", status="jungle:toxic_poison", amount=1))},
    ),
    card(
        "void", "magic_nut", "MagicNut", text("魔法坚果", "Magic Nut", "Gland magique", "魔法ドングリ"), 0, 5, "thorn",
        text("消耗自己所有[[icon:E]]，对目标造成(10+消耗量×3)[[icon:D]]", "Spend all your [[icon:E]] and deal (10 + amount spent × 3)[[icon:D]] to the target.", "Dépense tout votre [[icon:E]] et inflige (10 + quantité dépensée × 3)[[icon:D]] à la cible.", "自分の全[[icon:E]]を消費し、対象に(10+消費量×3)[[icon:D]]を与える"),
        text("它会随你的力量而变强。", "It grows stronger with your power.", "Il se renforce avec votre puissance.", "力に応じて強くなる。"),
        "magic nut.svg", flags=["unique"], events={"on_play": steps(action("magic_nut_attack"))}, damage=10,
    ),
    card(
        "void", "one_ring", "OneRing", text("戒指", "The One Ring", "L'Anneau Unique", "一つの指輪"), 8, 0, "bloom",
        text("对目标施加3层烈火和1层[[icon:F]]", "Apply 3 Blaze and 1[[icon:F]] to the target.", "Applique 3 Feu ardent et 1[[icon:F]] à la cible.", "対象に烈火3と[[icon:F]]1を付与する"),
        text("索伦之戒。", "Sauron's Ring.", "L'Anneau de Sauron.", "サウロンの指輪。"),
        "one ring.svg", flags=["sewers:confusion"], events=target_event(action("one_ring")),
    ),
    card(
        "void", "eyeball", "Eyeball", text("眼球", "Eyeball", "Œil", "眼球"), 3, 0, "root",
        text("存在时，随机选择玩家目标时，若本装备的目标可选，则改为选择该目标", "While present, random player targeting chooses this equipment's target whenever that target is selectable.", "Tant qu'il est présent, les choix aléatoires de joueur désignent la cible de cet équipement si elle peut être choisie.", "存在中、プレイヤーをランダムに選ぶ時、この装備の対象が選択可能ならその対象を選ぶ"),
        text("能够让你的花瓣打得更准。", "It helps your petals aim more accurately.", "Il aide vos pétales à viser plus juste.", "花びらの狙いを正確にする。"),
        "eyeball.svg", events=equip_events(),
    ),
    card(
        "void", "magic_stardust", "MagicStardust", text("魔法星尘", "Magic Stardust", "Poussière d'étoile magique", "魔法の星屑"), 0, 1, "bloom",
        text("令目标的[[icon:P]]立即结算1次，再令其剧毒立即结算1次；若目标没有剧毒，先施加1层；若目标没有[[icon:P]]，先施加等同于剧毒层数的[[icon:P]]", "Immediately resolve the target's [[icon:P]] once, then resolve their Toxic Poison once. If they have no Toxic Poison, apply 1 first; if they have no [[icon:P]], first apply [[icon:P]] equal to their Toxic Poison stacks.", "Résout immédiatement une fois le [[icon:P]] de la cible, puis une fois son Poison virulent. Si elle n'a pas de Poison virulent, applique-en d'abord 1 ; si elle n'a pas de [[icon:P]], applique d'abord autant de [[icon:P]] que ses cumuls de Poison virulent.", "対象の[[icon:P]]を1回即時結算し、その後剧毒を1回結算する。剧毒がなければ先に1付与し、[[icon:P]]がなければ剧毒スタック数と同量の[[icon:P]]を先に付与する"),
        text("魔法放大了它的辐射性。", "Magic magnifies its radioactivity.", "La magie amplifie sa radioactivité.", "魔法が放射性を増幅した。"),
        "magic stardust.svg", flags=["unique", "rebound", "wide_strike"], events={"on_play": steps(action("magic_stardust"))},
    ),
    card(
        "void", "horn", "Horn", text("角", "Horn", "Corne", "角笛"), 3, 0, "guard",
        text("对所有敌方目标造成10[[icon:D]]，不使所响应伤害失效  响应：自己将受到无来源或来源为自己的伤害", "Deal 10[[icon:D]] to every enemy without negating the responding damage.  Response: you would take source-less or self-sourced damage.", "Inflige 10[[icon:D]] à tous les ennemis sans annuler les dégâts correspondants.  Réponse : vous allez subir des dégâts sans source ou provenant de vous-même.", "対応するダメージを無効化せず、全敵に10[[icon:D]]を与える  応答：自分が無來源または自分由来のダメージを受ける時"),
        text("冲击！", "Charge!", "Chargez !", "突撃！"),
        "horn.svg", flags=["wide_strike"], response_trigger="self_or_sourceless_damage", events={"on_response": steps(action("horn_response", damage=10))}, damage=10,
    ),
    card(
        "void", "blood_scythe", "BloodScythe", text("血镰刀", "Blood Scythe", "Faux sanglante", "血の大鎌"), 4, 0, "thorn",
        text("对目标造成40[[icon:D]]，再对自己造成4[[icon:D]]；因虚无被放逐时，将1张[[card:Void]]加入手中", "Deal 40[[icon:D]] to the target, then 4[[icon:D]] to yourself. When exiled by Void, add 1 [[card:Void]] to your hand.", "Inflige 40[[icon:D]] à la cible, puis 4[[icon:D]] à vous-même. Lorsqu'elle est bannie par Néant, ajoute 1 [[card:Void]] à votre main.", "対象に40[[icon:D]]、その後自分に4[[icon:D]]を与える。虚无で放逐された時、[[card:Void]]を1枚手札に加える"),
        text("沾满了鲜血，不再会变弱。", "Drenched in blood, it will never weaken again.", "Trempée de sang, elle ne faiblira plus jamais.", "血に染まり、もう弱くなることはない。"),
        "blood scythe.svg", flags=["precision", "void"], events={"on_play": steps(action("blood_scythe", target_damage=40, self_damage=4)), "on_void_exile": steps(action("add_void_to_hand"))}, damage=40,
    ),
    card(
        "void", "magic_blood_scythe", "MagicBloodScythe", text("魔法血镰刀", "Magic Blood Scythe", "Faux sanglante magique", "魔法の血鎌"), 2, 8, "thorn",
        text("对自己施加3层[[icon:F]]、霜冻和[[icon:P]]，再对目标造成50[[icon:D]]；因虚无被放逐时，额外放逐自己至多2张手牌；若没有可放逐的手牌，则获得1层负债", "Apply 3[[icon:F]], 3 Frost, and 3[[icon:P]] to yourself, then deal 50[[icon:D]] to the target. When exiled by Void, additionally exile up to 2 cards from your hand; if none can be exiled, gain 1 Debt.", "Appliquez-vous 3[[icon:F]], 3 Gel et 3[[icon:P]], puis infligez 50[[icon:D]] à la cible. Lorsqu'elle est bannie par Néant, bannissez en plus jusqu'à 2 cartes de votre main ; si aucune ne peut l'être, gagnez 1 Dette.", "自分に[[icon:F]]3、霜冻3、[[icon:P]]3を付与し、その後対象に50[[icon:D]]を与える。虚无で放逐された時、自分の手札をさらに最大2枚放逐する。放逐できる手札がなければ负债を1得る"),
        text("将你置于冰毒火债四重天，但造成疯狂的伤害。", "Ice, poison, fire, and debt—four torments for absurd damage.", "Glace, poison, feu et dette : quatre tourments pour des dégâts insensés.", "氷・毒・炎・借金の四重苦、その代わりに狂気の火力。"),
        "magic blood scythe.svg", flags=["precision", "void"], events={"on_play": steps(action("magic_blood_scythe", damage=50)), "on_void_exile": steps(action("magic_blood_scythe_exile"))}, damage=50,
    ),
    card(
        "void", "hexagram", "Hexagram", text("六芒星", "Hexagram", "Hexagramme", "六芒星"), 5, 10, "thorn",
        text("对目标造成20[[icon:D]]并施加10层[[icon:F]]，再对自己造成5[[icon:D]]", "Deal 20[[icon:D]] to the target and apply 10[[icon:F]], then deal 5[[icon:D]] to yourself.", "Inflige 20[[icon:D]] à la cible et lui applique 10[[icon:F]], puis vous inflige 5[[icon:D]].", "対象に20[[icon:D]]を与えて[[icon:F]]を10付与し、その後自分に5[[icon:D]]を与える"),
        text("恶魔的盛宴。", "A devil's feast.", "Le festin du démon.", "悪魔の宴。"),
        "hexagram.svg", flags=["unique", "revealed"], events={"on_play": steps(action("hexagram", target_damage=20, self_damage=5, fire=10))}, damage=20,
    ),
]


ART_FILES = {
    "mask.svg": "口罩.svg",
    "magic mask.svg": "魔法口罩.svg",
    "bomb.svg": "炸弹.svg",
    "fire bomb.svg": "火焰炸弹.svg",
    "magic bomb.svg": "魔法炸弹.svg",
    "magic fire bomb.svg": "魔法火焰炸弹.svg",
    "pipe bomb.svg": "管状炸弹.svg",
    "dvd.svg": "光盘.svg",
    "fan.svg": "扇子.svg",
    "capacitor.svg": "电容器.svg",
    "copper rod.svg": "铜棒.svg",
    "plasma.svg": "等离子体.svg",
    "attractor.svg": "吸引器.svg",
    "magic slime ball.svg": "魔法粘液球.svg",
    "mysterious orb.svg": "球.svg",
    "schizo.svg": "精神分裂症.svg",
    "illuminati triangle.svg": "光明会三角.svg",
    "void mark.svg": "虚空标记.svg",
    "cicada 3301.svg": "cicada 3301.svg",
    "thorn.svg": "棘刺.svg",
    "magic copper rod.svg": "魔法铜棒.svg",
    "comb.svg": "梳子.svg",
    "stardust.svg": "星尘.svg",
    "one ring.svg": "戒指.svg",
    "eyeball.svg": "眼球.svg",
    "magic stardust.svg": "魔法星尘.svg",
    "horn.svg": "角.svg",
    "blood scythe.svg": "血镰刀.svg",
    "magic blood scythe.svg": "魔法血镰刀.svg",
    "hexagram.svg": "六芒星.svg",
    "magic nut.svg": "魔法橡果.svg",
}


def parse_length(value: str | None) -> float:
    match = re.match(r"\s*([0-9.]+)", str(value or ""))
    return float(match.group(1)) if match else 100.0


def normalized_svg(source: Path, *, palette: dict | None = None) -> bytes:
    raw = source.read_text(encoding="utf-8-sig")
    for old, new in (palette or {}).items():
        raw = raw.replace(old, new)
    root = ET.fromstring(raw)
    view_box = root.attrib.get("viewBox", "").replace(",", " ").split()
    if len(view_box) == 4:
        x, y, width, height = [float(value) for value in view_box]
    else:
        x = y = 0.0
        width = parse_length(root.attrib.get("width"))
        height = parse_length(root.attrib.get("height"))
    width = max(0.001, width)
    height = max(0.001, height)
    scale = min(82.0 / width, 82.0 / height)
    offset_x = (100.0 - width * scale) / 2.0 - x * scale
    offset_y = (100.0 - height * scale) / 2.0 - y * scale

    namespace = "{http://www.w3.org/2000/svg}"
    group = ET.Element(f"{namespace}g", {"transform": f"translate({offset_x:.6f} {offset_y:.6f}) scale({scale:.6f})"})
    preserved = []
    graphics = []
    for child in list(root):
        root.remove(child)
        if child.tag in (f"{namespace}defs", f"{namespace}title", f"{namespace}desc"):
            preserved.append(child)
        else:
            graphics.append(child)
    for child in preserved:
        root.append(child)
    for child in graphics:
        group.append(child)
    root.append(group)
    root.attrib.pop("style", None)
    root.set("width", "100")
    root.set("height", "100")
    root.set("viewBox", "0 0 100 100")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def art_payloads():
    missing = [source for source in ART_FILES.values() if not (ART_SOURCE / source).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing DLC art: {', '.join(missing)}")
    payload = {
        output: normalized_svg(ART_SOURCE / source)
        for output, source in ART_FILES.items()
    }
    payload["nut.svg"] = normalized_svg(
        ART_SOURCE / "魔法橡果.svg",
        palette={
            "#fd9345": "#9A6A35",
            "#d0752a": "#60401F",
            "#44ecd0": "#86C24D",
            "#2ecaaf": "#4D812A",
        },
    )
    return payload


def manifest(mod_id: str, resource_namespace: str, name: str, name_cn: str, author: str, description: str):
    return {
        "id": mod_id,
        "resource_namespace": resource_namespace,
        "name": name,
        "name_en": name,
        "name_cn": name_cn,
        "version": "1.0.0",
        "api_version": "2.0",
        "author": author,
        "description": description,
        "capabilities": ["cards", "logic.basic", "logic.advanced"],
        "default_language": "zh",
        "dependencies": [],
        "optional_dependencies": [],
        "load_after": [],
        "load_before": [],
    }


def locale_document(cards, package_names, language, base=None):
    document = copy.deepcopy(base or {})
    document["manifest"] = {
        "name": package_names.get(language, package_names["en"]),
        "description": package_names.get(f"{language}_description", package_names["en_description"]),
    }
    translated_cards = document.setdefault("cards", {})
    for item in cards:
        translated_cards[item["id"]] = {
            "name": item.get("name_i18n", {}).get(language, item["name_en"]),
            "effect_text": item.get("effect_text_i18n", {}).get(
                language,
                item.get("effect_text_en", item.get("effect_text", "")),
            ),
            "description": item.get("description_i18n", {}).get(language, item["description"]),
            "trigger_effect_text": item.get("trigger_effect_text_i18n", {}).get(language, item.get("trigger_effect_text", "")),
        }
    return document


def package_document(manifest_data, cards):
    return {
        "format_version": 2,
        "manifest": manifest_data,
        "registries": {
            "tags": [],
            "statuses": [],
            "cards": cards,
            "opening_events": [],
            "ui_components": [],
        },
        "patches": [],
        "compatibility": [],
        "event_hooks": [],
    }


def write_package(path: Path, document: dict, names: dict, assets: dict[str, bytes], *,
                  base_locales=None, extra_members=None):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr("mod.json", json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8"))
        cards = document["registries"]["cards"]
        for language in LANGUAGES:
            archive.writestr(
                f"locales/{language}.json",
                json.dumps(
                    locale_document(cards, names, language, (base_locales or {}).get(language)),
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8"),
            )
        for name, content in sorted(assets.items()):
            archive.writestr(f"card-art/{name}", content)
        for name, content in sorted((extra_members or {}).items()):
            archive.writestr(name, content)
    os.replace(temporary, path)


def read_package(path: Path):
    with zipfile.ZipFile(path, "r") as archive:
        members = {info.filename: archive.read(info.filename) for info in archive.infolist()}
    return json.loads(members["mod.json"].decode("utf-8-sig")), members


def rewrite_factory_parent():
    path = MODS / "Factory Cards Addition.gtnmod"
    document, members = read_package(path)
    document["manifest"]["version"] = "1.0.0"
    document["manifest"]["author"] = "Eric"
    document["registries"]["cards"] = [
        row for row in document["registries"]["cards"]
        if row.get("legacy_id") != "Lithium" and row.get("id") != "factory:lithium"
    ]
    members.pop("card-art/Lithium.svg", None)
    for language in LANGUAGES:
        key = f"locales/{language}.json"
        if key not in members:
            continue
        locale = json.loads(members[key].decode("utf-8-sig"))
        (locale.get("cards") or {}).pop("factory:lithium", None)
        members[key] = json.dumps(locale, ensure_ascii=False, indent=2).encode("utf-8")
    members["mod.json"] = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
    handle, temp_name = tempfile.mkstemp(suffix=".gtnmod", dir=path.parent)
    os.close(handle)
    temp = Path(temp_name)
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, content in members.items():
                archive.writestr(name, content)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def lithium_from_parent_snapshot():
    # Capture the merged card before the first split. Later runs read it back
    # from the generated DLC so the builder remains idempotent.
    document, members = read_package(MODS / "Factory Cards Addition.gtnmod")
    lithium = next(
        (row for row in document["registries"]["cards"] if row.get("legacy_id") == "Lithium"),
        None,
    )
    art = members.get("card-art/Lithium.svg")
    if lithium is None or art is None:
        dlc_document, dlc_members = read_package(MODS / "Factory Cards DLC.gtnmod")
        lithium = next(row for row in dlc_document["registries"]["cards"] if row.get("legacy_id") == "Lithium")
        art = dlc_members["card-art/Lithium.svg"]
    return copy.deepcopy(lithium), art


def update_bio_dlc(assets):
    path = MODS / "Bio Cards DLC.gtnmod"
    document, members = read_package(path)
    document["manifest"]["author"] = "huanxiang0273, Eric, XinYu, AArcC"
    existing = {row.get("id"): row for row in document["registries"]["cards"]}
    for row in BIO_CARDS:
        existing[row["id"]] = row
    document["registries"]["cards"] = list(existing.values())
    selected_assets = {
        name: content for name, content in assets.items()
        if name in {"mask.svg", "magic mask.svg"}
    }
    names = {
        "zh": "生化卡DLC包", "en": "Bio Cards DLC", "fr": "DLC de cartes bio", "ja": "生化カードDLC",
        "en_description": "Additional cards for Bio Cards Addition.",
    }
    status_translations = {
        "zh": {
            "name": "护盾转化",
            "description": "下次将回复[[icon:H]]时，若原回复量大于0，改为获得(原回复量×护盾转化层数)层护盾，然后清空护盾转化。",
        },
        "en": {
            "name": "Shield Conversion",
            "description": "The next time [[icon:H]] would be restored, if the original amount is greater than 0, gain Shield equal to (original amount × Shield Conversion stacks) instead, then clear Shield Conversion.",
        },
        "fr": {
            "name": "Conversion de bouclier",
            "description": "La prochaine fois que des [[icon:H]] devraient être récupérés, si la quantité initiale est supérieure à 0, gagnez à la place un Bouclier égal à (quantité initiale × charges de Conversion de bouclier), puis retirez toutes ses charges.",
        },
        "ja": {
            "name": "シールド変換",
            "description": "次に[[icon:H]]を回復する時、元の回復量が0より大きければ、代わりに(元の回復量×シールド変換の層数)のシールドを得て、その後シールド変換を全て消去します。",
        },
    }
    base_locales = {}
    for language in LANGUAGES:
        key = f"locales/{language}.json"
        base = json.loads(members[key].decode("utf-8-sig")) if key in members else {}
        base.setdefault("statuses", {})["bio:shield_conversion"] = status_translations[language]
        base_locales[language] = base
    status_icon = members.get("status-icons/shield_conversion.svg")
    if status_icon is None:
        status_icon = (ROOT / "static" / "assets" / "status-icons" / "shield_conversion.svg").read_bytes()
    write_package(path, document, names, {
        **{
            name.removeprefix("card-art/"): content
            for name, content in members.items()
            if name.startswith("card-art/")
        },
        **selected_assets,
    }, base_locales=base_locales, extra_members={
        "status-icons/shield_conversion.svg": status_icon,
    })


def main():
    assets = art_payloads()
    lithium, lithium_art = lithium_from_parent_snapshot()

    factory_cards = [lithium, *FACTORY_CARDS]
    factory_doc = package_document(
        manifest("factory_dlc", "factory", "Factory Cards DLC", "工厂卡DLC包", "Eric, XinYu, AArcC", "工厂主题卡牌扩展。"),
        factory_cards,
    )
    factory_names = {
        "zh": "工厂卡DLC包", "en": "Factory Cards DLC", "fr": "DLC de cartes d'usine", "ja": "工場カードDLC",
        "en_description": "Additional cards for Factory Cards Addition.",
    }
    factory_art_names = {row["assets"]["image"].split("/")[-1] for row in FACTORY_CARDS}
    write_package(
        MODS / "Factory Cards DLC.gtnmod",
        factory_doc,
        factory_names,
        {"Lithium.svg": lithium_art, **{name: assets[name] for name in factory_art_names}},
    )

    void_doc = package_document(
        manifest("void_dlc", "void", "Void Cards DLC", "虚空卡DLC包", "Eric, AArcC", "虚空主题卡牌扩展。"),
        VOID_CARDS,
    )
    void_names = {
        "zh": "虚空卡DLC包", "en": "Void Cards DLC", "fr": "DLC de cartes du Néant", "ja": "虚空カードDLC",
        "en_description": "Additional cards for Void Card Addition.",
    }
    void_art_names = {row["assets"]["image"].split("/")[-1] for row in VOID_CARDS}
    write_package(MODS / "Void Cards DLC.gtnmod", void_doc, void_names, {name: assets[name] for name in void_art_names})

    update_bio_dlc(assets)
    rewrite_factory_parent()
    print("Built Bio, Factory, and Void DLC packages.")


if __name__ == "__main__":
    main()
