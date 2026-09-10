# -*- coding: utf-8 -*-
"""Missing EN/FR/JA rewrites for the official packages.

Chinese stays authoritative. These entries cover the cards that still shipped
English text inside their French/Japanese slots (and a few cards whose English
slot still held Chinese).
"""

CARD_TEXTS = {
    # ---------------------------------------------------------- Factory DLC
    "Lithium": {
        "en": "Deal 5[[icon:electric_damage]] to the target when played and at the equipment owner's turn start.",
        "fr": "Infligez 5[[icon:electric_damage]] à la cible à l'utilisation et au début du tour du propriétaire de l'équipement.",
        "ja": "使用時と装備保持者のターン開始時、対象に5[[icon:electric_damage]]を与える。",
    },
    "Bomb": {
        "fr": "Infligez 6[[icon:D]] à la cible. En cas de touche, appliquez-lui 1 Surcharge et 1 Faiblesse.",
        "ja": "対象に6[[icon:D]]を与える。命中時、対象に過負荷を1、虚弱を1与える。",
    },
    "Fire Bomb": {
        "fr": "Infligez 16[[icon:D]] à la cible et appliquez-lui 3[[icon:F]].",
        "ja": "対象に16[[icon:D]]を与え、対象に[[icon:F]]を3与える。",
    },
    "Magic Bomb": {
        "fr": "Infligez 20[[icon:D]] à la cible et appliquez-lui 1 Étourdissement.",
        "ja": "対象に20[[icon:D]]を与え、対象にスタンを1与える。",
    },
    "Magic Fire Bomb": {
        "fr": "Infligez 2[[icon:D]] à la cible. En cas de touche, appliquez-lui 1[[icon:F]].",
        "ja": "対象に2[[icon:D]]を与える。命中時、対象に[[icon:F]]を1与える。",
    },
    "Pipe Bomb": {
        "fr": "Utilisable seulement si votre main compte un nombre impair de cartes. Infligez 16[[icon:D]] à la cible, puis terminez votre tour. Lorsqu'elle est exilée par le Vide, ajoutez 1 [[card:Void]] à votre main.",
        "ja": "手札が奇数のときだけ使用できる。対象に16[[icon:D]]を与え、その後自分のターンを終了する。虚無により追放された時、[[card:Void]]を1枚手札に加える。",
    },
    # ------------------------------------------------------------- Void DLC
    "DVD": {
        "fr": "Infligez 4[[icon:D]] à la cible. En cas de touche, appliquez-lui 1[[icon:F]]. Au début de votre prochain tour, si cette carte est encore dans votre défausse, elle revient dans votre main.",
        "ja": "対象に4[[icon:D]]を与える。命中時、対象に[[icon:F]]を1与える。次の自分のターン開始時、このカードがまだ捨て札にあるなら手札に戻る。",
    },
    "Fan": {
        "fr": "Appliquez 2[[icon:F]] à la cible, puis résolvez une fois son [[icon:F]]. La cible récupère 4[[icon:E]].",
        "ja": "対象に[[icon:F]]を2与え、その後対象の[[icon:F]]を1回解決する。対象は4[[icon:E]]を回復する。",
    },
    "Capacitor": {
        "fr": "Appliquez 3 Charge à toutes les cartes de la main de la cible.",
        "ja": "対象の手札すべてに電荷を3与える。",
    },
    "Plasma": {
        "fr": "Appliquez 4[[icon:P]] et 4[[icon:F]] à la cible, appliquez 4 Charge à 1 carte au hasard de sa main, puis infligez-lui 4[[icon:D]] puis 4[[icon:electric_damage]]. Lorsqu'elle est exilée par le Vide, ajoutez 1 [[card:Void]] à votre main.",
        "ja": "対象に[[icon:P]]を4、[[icon:F]]を4与え、その手札1枚にランダムで電荷を4与え、その後対象に4[[icon:D]]、4[[icon:electric_damage]]の順に与える。虚無により追放された時、[[card:Void]]を1枚手札に加える。",
    },
    "Attractor": {
        "fr": "Appliquez 1 Attaque seule à la cible. Lorsqu'elle est exilée par le Vide, ajoutez 1 [[card:Void]] à votre main.",
        "ja": "対象に攻撃のみを1与える。虚無により追放された時、[[card:Void]]を1枚手札に加える。",
    },
    "Magic Slime Ball": {
        "fr": "Appliquez 1 Étourdissement à la cible et 1 Lenteur à vous-même. Les copies exilées de cette carte gagnent Rapidité magique:2. Lorsqu'elle est exilée par le Vide, ajoutez 1 [[card:Void]] à votre main.",
        "ja": "対象にスタンを1、自分に遅鈍を1与える。このカードの追放コピーは魔力迅捷:2を得る。虚無により追放された時、[[card:Void]]を1枚手札に加える。",
    },
    "Void Mark": {
        "fr": "Après 1 tour équipé, peut être déclenché : choisissez une cible et appliquez-lui 3 Cécité. Lorsque cette carte est exilée par le Vide, ajoutez 1 [[card:Void]] à votre main.",
        "ja": "1ターン装備した後、発動できる：対象を1つ選び、失明を3与える。虚無により追放された時、[[card:Void]]を1枚手札に加える。",
    },
    "Cicada 3301": {
        "fr": "Toutes les cibles sélectionnables gagnent 3 Cécité au début de leur prochain tour, puis défaussez 2 autres cartes de votre main. Choisissez ensuite : exiler la main de toutes les cibles ; ranimer toutes les cibles avec 5% de leur [[icon:H]] maximum et 1 tour d'Invincible ; ou réorganiser le deck de chaque cible et en choisir 1 carte par cible à ajouter à votre main. Lorsqu'elle est exilée par le Vide, ajoutez 1 [[card:Void]] à votre main.",
        "ja": "すべての選択可能な対象は次のターン開始時に失明を3獲得し、その後自分は他の手札を2枚捨てる。さらに選択する：すべての対象の手札を追放する；すべての対象を復活させ、[[icon:H]]を上限の5%にし、1ターンの無敵を与える；またはすべての対象の山札を並べ替え、それぞれから1枚選んで自分の手札に加える。虚無により追放された時、[[card:Void]]を1枚手札に加える。",
    },
    "Thorn": {
        "fr": "Infligez 6[[icon:D]] à la cible et appliquez-lui 1 Brasier. Lorsque des dégâts réels sont infligés, jouez 1 [[card:HeatedThorn]] supplémentaire (Frappe large, Auto-ciblage, Fission:3).",
        "ja": "対象に6[[icon:D]]を与え、対象に烈火を1与える。実際にダメージを与えた時、[[card:HeatedThorn]]を追加で1枚使用する（広域打撃、自刃、分裂:3）。",
    },
    "Magic Copper Rod": {
        "fr": "Quand la cible devrait subir des dégâts, si le propriétaire de l'équipement peut dépenser 1[[icon:M]], il absorbe automatiquement ces dégâts. À la place, répartissez des Charges égales à ces dégâts, arrondies au supérieur, sur toutes les cartes de la main de la cible.",
        "ja": "対象がダメージを受ける時、装備保持者が1[[icon:M]]を支払えるなら、そのダメージを自動で吸収する。代わりに、そのダメージ量を切り上げて対象の手札すべてに電荷として均等に分ける。",
    },
    "Nut": {
        "fr": "Utilisable seulement si vous avez une autre carte de même nom en main. Infligez 14[[icon:D]] à la cible.",
        "ja": "自分の手札に同名カードがあるときだけ使用できる。対象に14[[icon:D]]を与える。",
    },
    "Comb": {
        "fr": "Appliquez 1 Brasier, 1[[icon:F]], 1 Poison toxique et 1[[icon:P]] à la cible. Lorsqu'elle est exilée par le Vide, ajoutez 1 [[card:Void]] à votre main.",
        "ja": "対象に烈火を1、[[icon:F]]を1、猛毒を1、[[icon:P]]を1与える。虚無により追放された時、[[card:Void]]を1枚手札に加える。",
    },
    "Magic Nut": {
        "fr": "Utilisable seulement si toutes les cartes de votre deck ont des noms différents. Dépensez tout votre [[icon:E]] et infligez (10 + montant dépensé × 5)[[icon:D]] à la cible.",
        "ja": "自分の山札のすべてのカード名が重複していないときだけ使用できる。自分の[[icon:E]]をすべて消費し、対象に(10+消費量×5)[[icon:D]]を与える。",
    },
    "The One Ring": {
        "fr": "Appliquez 2 Brasier et 1[[icon:F]] à la cible.",
        "ja": "対象に烈火を2、[[icon:F]]を1与える。",
    },
    "Eyeball": {
        "fr": "Tant qu'il existe, la cible ne peut cibler que le propriétaire de l'équipement.",
        "ja": "存在中、対象は装備保持者しか指定できない。",
    },
    "Magic Stardust": {
        "fr": "Résolvez immédiatement le [[icon:P]] de la cible. Si elle n'a pas de [[icon:P]], appliquez-lui d'abord un [[icon:P]] égal à ses charges de Poison toxique et résolvez-le. Si elle n'a pas de Poison toxique, appliquez d'abord 1 Poison toxique avant de vérifier.",
        "ja": "対象の[[icon:P]]を即座に解決する。対象に[[icon:P]]がない場合、まず猛毒の層数に等しい[[icon:P]]を与えて解決する。猛毒がない場合、先に猛毒を1与えてから判定する。",
    },
    "Blood Scythe": {
        "fr": "Infligez-vous 20[[icon:D]], puis 40[[icon:D]] à la cible. Lorsqu'elle est exilée par le Vide, ajoutez 1 [[card:Void]] à votre main.",
        "ja": "自分に20[[icon:D]]を与え、その後対象に40[[icon:D]]を与える。虚無により追放された時、[[card:Void]]を1枚手札に加える。",
    },
    "Magic Blood Scythe": {
        "fr": "Appliquez-vous 3[[icon:F]], 3 Givre et 3[[icon:P]], puis infligez 50[[icon:D]] à la cible. Lorsqu'elle est exilée par le Vide, exilez en plus jusqu'à 2 cartes de votre main ; sinon gagnez 1 Dette, puis ajoutez 1 [[card:Void]] à votre main.",
        "ja": "自分に[[icon:F]]を3、霜を3、[[icon:P]]を3与え、その後対象に50[[icon:D]]を与える。虚無により追放された時、追加で自分の手札を最大2枚追放する。追放できない場合、負債を1獲得し、[[card:Void]]を1枚手札に加える。",
    },
    # -------------------------------------------------------------- Bio DLC
    "Cyanide Pill": {
        "en": "Remove all [[icon:P]] and [[icon:F]] from the target.",
        "fr": "Retirez tout le [[icon:P]] et le [[icon:F]] de la cible.",
        "ja": "対象の[[icon:P]]と[[icon:F]]をすべて取り除く。",
    },
    "Stem Cell": {
        "en": "When the target actually loses [[icon:H]], this equipment gains that many stacks. After being equipped for 1 turn, you may spend 6[[icon:M]] to trigger: destroy this equipment and restore ceil(this equipment's stacks × 75%)[[icon:H]] to the target.",
        "fr": "Quand la cible perd réellement des [[icon:H]], cet équipement gagne autant de charges. Après 1 tour équipé, vous pouvez dépenser 6[[icon:M]] pour déclencher : détruisez cet équipement et rendez à la cible arrondi supérieur(charges de cet équipement × 75%)[[icon:H]].",
        "ja": "対象が実際に[[icon:H]]を失うたび、この装備は失われた量に等しい層数を獲得する。1ターン装備した後、6[[icon:M]]を消費して発動できる：この装備を破壊し、対象の[[icon:H]]を切り上げ(この装備の層数×75%)回復する。",
    },
    "Mitochondria": {
        "en": "Apply 2 Shield Conversion to the target.",
        "fr": "Appliquez 2 Conversion de bouclier à la cible.",
        "ja": "対象に護盾転化を2与える。",
    },
    "Mask": {
        "fr": "La cible ne subit plus de dégâts provenant d'effets spéciaux.",
        "ja": "対象は特殊効果によるダメージを受けなくなる。",
    },
    "Magic Mask": {
        "fr": "La cible n'est plus affectée par les interférences des effets spéciaux.",
        "ja": "対象は特殊効果による干渉を受けなくなる。",
    },
    # -------------------------------------------------- Formal Logic Reasoning
    "Variable $0": {
        "fr": "Infligez 6[[icon:D]] à la cible.",
        "ja": "対象に6[[icon:D]]を与える。",
    },
    "Variable $1": {
        "fr": "Rendez 5[[icon:H]] à la cible.",
        "ja": "対象の[[icon:H]]を5回復する。",
    },
    "Variable $2": {
        "fr": "Rendez 2[[icon:M]] à la cible.",
        "ja": "対象の[[icon:M]]を2回復する。",
    },
}

# Cards that share the same textual pattern except for the number of plays
# before Inference is granted.
FORMAL_LOGIC_REPEAT = {
    "├$0>($1>$0)": 2,
    "├($0>($1>$2))>(($0>$1)>($0>$2))": 3,
}

FORMAL_LOGIC_DEBUT = {
    "├$0>$0": {
        "fr": "Début : la 1re carte jouée ce tour se résout une fois de plus.",
        "ja": "登場：このターンに使用した最初のカードがもう1回解決される。",
    },
    "├$0>¬¬$0": {
        "fr": "Début : choisissez 1 carte de votre main et fixez définitivement son coût en E à 0. Si cette carte a déjà fait son Début dans la partie, l'effet ne dure que jusqu'à la fin du tour.",
        "ja": "登場：自分の手札を1枚選び、そのEコストを永続的に0にする。この対局で既に登場している場合、代わりにこのターン終了まで持続する。",
    },
    "├¬¬$0>$0": {
        "fr": "Début : choisissez 1 carte de votre main et fixez définitivement ses coûts en E et en M à 0. Si cette carte a déjà fait son Début dans la partie, l'effet ne dure que jusqu'à la fin du tour.",
        "ja": "登場：自分の手札を1枚選び、そのEとMのコストを永続的に0にする。この対局で既に登場している場合、代わりにこのターン終了まで持続する。",
    },
    "$0，¬$0├$1": {
        "fr": "Début : choisissez et jouez 1 carte depuis la réserve complète de cartes.",
        "ja": "登場：全カードプールから1枚選んで使用する。",
    },
    "$0>$1，$1>$2├$0>$2": {
        "fr": "Début : rendez-vous 5[[icon:H]].",
        "ja": "登場：自分の[[icon:H]]を5回復する。",
    },
    "├($0>($1>$2))>($1>($0>$2))": {
        "fr": "Début : augmentez votre [[icon:H]] de arrondi supérieur([[icon:H]] actuel/10), gagnez 1[[icon:E]] et 1[[icon:M]], puis échangez les valeurs actuelles de deux d'entre eux.",
        "ja": "登場：自分の[[icon:H]]を切り上げ(現在の[[icon:H]]/10)増やし、[[icon:E]]と[[icon:M]]を1ずつ獲得する。その後、そのうち2つの現在値を交換する。",
    },
}

FORMAL_LOGIC_OTHER = {
    "($0>$1)├(¬$1>¬$0)": {
        "fr": "Défaussez 1 carte de votre main dont la conclusion est une implication. Ajoutez sa contraposition à votre main en conservant son état et ses tags, et donnez-lui Exil par inférence.",
        "ja": "結論が含意式である自分の手札を1枚選んで捨て札に置く。その対偶を状態とタグを保ったまま手札に加え、推理追放を与える。",
    },
    "Inverse Deduction Metatheorem": {
        "fr": "Exilez 1 carte de votre main de la forme ...├$0>($1>...). Ajoutez-la à votre main sous la forme ...,$0├$1>... (au moins une variable doit rester à droite de ├).",
        "ja": "自分の手札から…├$0>($1>…)の形のカードを1枚追放する。…，$0├$1>…に変えて手札に加える（├の右側に変数が1つ以上必要）。",
    },
    "mp": {
        "fr": "Après 1 tour équipé, déclenchez : choisissez 2 cartes formule unifiables dans votre main, générez leur théorème par modus ponens et ajoutez-le à votre main ; détruisez ensuite cet équipement.",
        "ja": "1ターン装備した後に発動できる：自分の手札から合一可能な公式カードを2枚選び、mpで定理カードを1枚生成して手札に加える。その後この装備を破壊する。",
    },
    "Deduction Metatheorem": {
        "fr": "Réagissez quand la Substitution de la cible est retirée ou qu'elle utilise le Métathéorème d'inverse déduction : modifiez la formule concernée ; si c'est impossible, annulez cette inverse déduction.",
        "ja": "対象の代入が解除された時、または対象が逆演繹メタ定理を使用した時、対応する公式を変更する。変更できない場合、その逆演繹を無効にする。",
    },
    "Macro Definition": {
        "fr": "Exilez 1 carte de votre main et placez 1 copie dans votre défausse ; équipez automatiquement la Macro indestructible correspondante. Une fois par tour, la Macro crée une carte proxy avec Vide et les tags d'origine, mais sans effet numérique. Chaque utilisation d'un proxy donne 1 Lourdeur aux futurs proxies.",
        "ja": "自分の手札を1枚追放し、複製を1枚捨て札に置く。対応する破壊不可のマクロを自動装備する。マクロは1ターンに1回発動でき、虚無と元のタグを持ち数値効果を生まない代理カードを1枚生成する。代理カードを使用するたび、以降に生成される代理カードは重化を1獲得する。",
    },
    "Generalization Metatheorem": {
        "fr": "Donnez à toutes les cartes de la cible un quantificateur universel jusqu'à la fin de son tour ; les cartes qui ne peuvent pas substituer la variable quantifiée sont désactivées. Choisissez ensuite une autre cible qui n'est pas son coéquipier pour qu'elle gagne une Dette de sang égale au nombre de cartes modifiées.",
        "ja": "対象のすべてのカードに全称量化子を与え、対象のターン終了まで持続する。量化変数を代入できないカードはこの間無効になる。その後、対象の味方ではない別の対象を1つ選び、変更された枚数に等しい血の負債を与える。",
    },
    "Generated Theorem": {
        "fr": "Effectuez la substitution et l'inférence dans l'ordre indiqué par la formule.",
        "ja": "公式に従い、代入と推理を順に行う。",
    },
    "Macro": {
        "fr": "Une fois par tour : créez la carte proxy correspondante.",
        "ja": "1ターンに1回発動できる：対応する代理カードを生成する。",
    },
}


def formal_repeat_text(name):
    """Return the FR/JA text for the 'first N plays grant Substitution' cards."""
    count = FORMAL_LOGIC_REPEAT.get(name)
    if count is None:
        return None
    fr = (
        "Gagnez 3 Bouclier à chaque utilisation. Les %d premières utilisations donnent 1 Substitution à la cible ; "
        "l'utilisation suivante donne 1 Inférence. Réinitialisé ensuite." % count
    )
    ja = (
        "使用するたび、自分は護盾を3獲得する。最初の%d回の使用では対象に代入を1、"
        "その次の使用では推理を1与える。その後リセットされる。" % count
    )
    return {"fr": fr, "ja": ja}


def formal_debut_text(name):
    """Combine the shared 'first N plays' clause with a card's Debut effect."""
    debut = FORMAL_LOGIC_DEBUT.get(name)
    if debut is None:
        return None
    count = 1 if name in ("├$0>$0", "├$0>¬¬$0", "├¬¬$0>$0") else (
        2 if name == "$0，¬$0├$1" else 3
    )
    reset_fr = "Réinitialisé ensuite." if name == "├$0>$0" else "Réinitialisé après l'inférence."
    reset_ja = "その後リセットされる。" if name == "├$0>$0" else "推理の完了後にリセットされる。"
    fr = (
        "Gagnez 3 Bouclier à chaque utilisation. Les %d premières utilisations donnent 1 Substitution à la cible ; "
        "l'utilisation suivante donne 1 Inférence. %s %s" % (count, reset_fr, debut["fr"])
    )
    ja = (
        "使用するたび、自分は護盾を3獲得する。最初の%d回の使用では対象に代入を1、"
        "その次の使用では推理を1与える。%s %s" % (count, reset_ja, debut["ja"])
    )
    return {"fr": fr, "ja": ja}


def lookup(name):
    for source in (
        CARD_TEXTS,
        FORMAL_LOGIC_OTHER,
    ):
        if name in source:
            return source[name]
    return formal_repeat_text(name) or formal_debut_text(name)


FORMAL_LOGIC_REPEAT = dict(FORMAL_LOGIC_REPEAT)

# Cards whose old machine translations were wrong enough to be replaced even
# though their slots were not duplicates of the English text.
CARD_TEXTS.update({
    "Third Eye": {
        "en": "Choose 1 attack card in your hand; if it already has Precision, give it Stealth, otherwise give it Precision.",
        "fr": "Choisissez 1 carte d'attaque dans votre main ; si elle a déjà Précision, donnez-lui Furtif, sinon donnez-lui Précision.",
        "ja": "自分の手札から攻撃カードを1枚選ぶ。すでに精度を持つ場合、隠密を与える。そうでない場合、精度を与える。",
    },
    "Singularity": {
        "en": "When equipped, every card of yours and of the target gains Void; each time a card is exiled by Void in play, deal 2[[icon:electric_damage]] to the target.",
        "fr": "À l'équipement, toutes vos cartes et celles de la cible gagnent Vide ; chaque fois qu'une carte est exilée par le Vide, infligez 2[[icon:electric_damage]] à la cible.",
        "ja": "装備時、自分と対象のすべてのカードは虚無を獲得する。場でカードが虚無により追放されるたび、対象に2[[icon:electric_damage]]を与える。",
    },
    "Magic Dice": {
        "en": "Deal 6[[icon:D]] to the target; if this damage is a critical hit, spend all of your remaining Luck and deal 2[[icon:electric_damage]] to the target for each stack spent.",
        "fr": "Infligez 6[[icon:D]] à la cible ; si ces dégâts sont un coup critique, dépensez toute votre Chance restante et infligez 2[[icon:electric_damage]] à la cible par charge dépensée.",
        "ja": "対象に6[[icon:D]]を与える。このダメージがクリティカルになった場合、自分の残りの運をすべて消費し、消費した1層につき対象に2[[icon:electric_damage]]を与える。",
    },
})

# Formal logic cards whose icon markup was missing in the Chinese source too,
# so all four languages are rewritten together.
CARD_TEXTS.update({
    "$0>$1，$1>$2├$0>$2": {
        "zh": "每次打出时，自己获得3层护盾；前3次打出时，使目标获得1层代入；再次打出时，使目标获得1层推理；推理完成后重置；登场：回复自己5[[icon:H]]",
        "en": "Gain 3 Shield whenever played. The first 3 plays grant the target 1 Substitution; the next play grants 1 Inference. Reset afterward. Debut: Restore 5[[icon:H]] to yourself.",
        "fr": "Gagnez 3 Bouclier à chaque utilisation. Les 3 premières utilisations donnent 1 Substitution à la cible ; l'utilisation suivante donne 1 Inférence. Réinitialisé après l'inférence. Début : rendez-vous 5[[icon:H]].",
        "ja": "使用するたび、自分は護盾を3獲得する。最初の3回の使用では対象に代入を1、その次の使用では推理を1与える。推理の完了後にリセットされる。登場：自分の[[icon:H]]を5回復する。",
    },
    "├($0>($1>$2))>($1>($0>$2))": {
        "zh": "每次打出时，自己获得3层护盾；前3次打出时，使目标获得1层代入；再次打出时，使目标获得1层推理；推理完成后重置；登场：自己的[[icon:H]]增加向上取整(当前[[icon:H]]/10)，[[icon:E]]与[[icon:M]]各增加1；再选择其中2项交换当前值",
        "en": "Gain 3 Shield whenever played. The first 3 plays grant the target 1 Substitution; the next play grants 1 Inference. Reset afterward. Debut: Increase [[icon:H]] by ceil(current [[icon:H]]/10) and gain 1[[icon:E]] and 1[[icon:M]], then swap the current values of two of them.",
        "fr": "Gagnez 3 Bouclier à chaque utilisation. Les 3 premières utilisations donnent 1 Substitution à la cible ; l'utilisation suivante donne 1 Inférence. Réinitialisé après l'inférence. Début : augmentez votre [[icon:H]] de arrondi supérieur([[icon:H]] actuel/10), gagnez 1[[icon:E]] et 1[[icon:M]], puis échangez les valeurs actuelles de deux d'entre eux.",
        "ja": "使用するたび、自分は護盾を3獲得する。最初の3回の使用では対象に代入を1、その次の使用では推理を1与える。推理の完了後にリセットされる。登場：自分の[[icon:H]]を切り上げ(現在の[[icon:H]]/10)増やし、[[icon:E]]と[[icon:M]]を1ずつ獲得する。その後、そのうち2つの現在値を交換する。",
    },
})

# Icon/Chip placeholders must match across languages, so these keep every
# language in sync with the Chinese source.
CARD_TEXTS.update({
    "Soil": {
        "zh": "使目标[[icon:H]]上限+40，回复目标40[[icon:H]]；向目标抽牌堆洗入5张[[card:Dust]]",
        "en": "Increase the target's [[icon:H]] maximum by 40 and restore 40[[icon:H]] to the target; shuffle 5 [[card:Dust]] into the target's deck.",
        "fr": "Augmentez de 40 le maximum de [[icon:H]] de la cible et rendez 40[[icon:H]] à la cible ; mélangez 5 [[card:Dust]] dans le deck de la cible.",
        "ja": "対象の[[icon:H]]上限を+40し、対象の[[icon:H]]を40回復する。対象の山札に[[card:Dust]]を5枚混ぜる。",
    },
    "Stem Cell": {
        "en": "When the target actually loses [[icon:H]], this equipment gains stacks equal to the [[icon:H]] lost. After being equipped for 1 turn, you may spend 6[[icon:M]] to trigger: destroy this equipment and restore ceil(this equipment's stacks × 75%)[[icon:H]] to the target.",
        "fr": "Quand la cible perd réellement des [[icon:H]], cet équipement gagne autant de charges que les [[icon:H]] perdus. Après 1 tour équipé, vous pouvez dépenser 6[[icon:M]] pour déclencher : détruisez cet équipement et rendez à la cible arrondi supérieur(charges de cet équipement × 75%)[[icon:H]].",
        "ja": "対象が実際に[[icon:H]]を失うたび、この装備は失われた[[icon:H]]に等しい層数を獲得する。1ターン装備した後、6[[icon:M]]を消費して発動できる：この装備を破壊し、対象の[[icon:H]]を切り上げ(この装備の層数×75%)回復する。",
    },
})

FORCE_NAMES = {
    "Third Eye", "Singularity", "Magic Dice", "Soil", "Stem Cell",
    "$0>$1，$1>$2├$0>$2", "├($0>($1>$2))>($1>($0>$2))",
}


ALL_NAMES = sorted(
    set(CARD_TEXTS) | set(FORMAL_LOGIC_REPEAT) | set(FORMAL_LOGIC_DEBUT) | set(FORMAL_LOGIC_OTHER)
)
