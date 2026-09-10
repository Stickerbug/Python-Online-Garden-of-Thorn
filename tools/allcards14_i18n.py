# -*- coding: utf-8 -*-
"""Authoritative four-language text for the "All Cards" balance pass (workbook 14).

Chinese follows docs/卡牌描述规范.md and the design clarifications given for
workbook 14. English, French and Japanese are rewritten from the Chinese text
instead of patching stale machine output. Markup such as [[icon:D]] must stay
byte-identical in every language.
"""

CARD_TEXTS = {
    "Coffee": {
        "zh": "回复目标2[[icon:E]]；本牌获得1层沉重",
        "en": "Restore 2[[icon:E]] to the target; this card gains 1 stack of Heavy.",
        "fr": "Rendez 2[[icon:E]] à la cible ; cette carte gagne 1 charge de Lourdeur.",
        "ja": "対象に2[[icon:E]]を回復する。このカードは重化を1獲得する。",
    },
    "Heavy": {
        "zh": "对目标造成36[[icon:D]]；使自己获得1层眩晕",
        "en": "Deal 36[[icon:D]] to the target; you gain 1 Stun.",
        "fr": "Infligez 36[[icon:D]] à la cible ; vous gagnez 1 Étourdissement.",
        "ja": "対象に36[[icon:D]]を与える。自分はスタンを1獲得する。",
    },
    "Shovel": {
        "zh": "使自己获得1层无法选中；结束你的回合",
        "en": "You gain 1 Untargetable; end your turn.",
        "fr": "Vous gagnez 1 Non ciblable ; terminez votre tour.",
        "ja": "自分は対象不可を1獲得する。自分のターンを終了する。",
    },
    "Missile": {
        "zh": "对攻击者造成12[[icon:D]]；抽1张牌  响应：被作为攻击牌目标",
        "en": "Deal 12[[icon:D]] to the attacker; draw 1 card.  Response: Targeted by an attack card.",
        "fr": "Infligez 12[[icon:D]] à l'attaquant ; piochez 1 carte.  Réponse : ciblé par une carte d'attaque.",
        "ja": "攻撃者に12[[icon:D]]を与える。カードを1枚引く。  応答：攻撃カードの対象となる。",
    },
    "Soil": {
        "zh": "使目标[[icon:H]]上限+40，回复目标40[[icon:H]]；向目标抽牌堆洗入5张灰尘",
        "en": "Increase the target's [[icon:H]] maximum by 40 and restore 40[[icon:H]] to the target; shuffle 5 [[card:Dust]] into the target's deck.",
        "fr": "Augmentez de 40 le maximum de [[icon:H]] de la cible et rendez 40[[icon:H]] à la cible ; mélangez 5 [[card:Dust]] dans le deck de la cible.",
        "ja": "対象の[[icon:H]]上限を+40し、対象の[[icon:H]]を40回復する。対象の山札に[[card:Dust]]を5枚混ぜる。",
    },
    "Coal": {
        "zh": "对目标造成(8+2×自己[[icon:F]]层数)[[icon:D]]",
        "en": "Deal (8+2×your [[icon:F]] stacks)[[icon:D]] to the target.",
        "fr": "Infligez (8+2×vos charges de [[icon:F]])[[icon:D]] à la cible.",
        "ja": "対象に(8+2×自分の[[icon:F]]層)[[icon:D]]を与える。",
    },
    "Magic Antennae": {
        "zh": "向自己展示一次目标本局初始牌组中的所有牌；抽1张牌",
        "en": "Reveal every card of the target's starting deck to yourself; draw 1 card.",
        "fr": "Révélez-vous toutes les cartes du deck de départ de la cible ; piochez 1 carte.",
        "ja": "対象の初期デッキのカードをすべて自分に公開する。カードを1枚引く。",
    },
    "Grass": {
        "zh": "可花费1[[icon:E]]，触发：回复目标6[[icon:H]]；每回合至多触发1次",
        "en": "You may spend 1[[icon:E]] to trigger: restore 6[[icon:H]] to the target. At most once per turn.",
        "fr": "Vous pouvez dépenser 1[[icon:E]] pour déclencher : rendez 6[[icon:H]] à la cible. Au plus une fois par tour.",
        "ja": "1[[icon:E]]を消費して発動できる：対象の[[icon:H]]を6回復する。1ターンに1回まで。",
    },
    "Mecha Antennae": {
        "zh": (
            "选择一种类型，使目标所有区域的该类型牌获得被揭示；"
            "从自己抽牌堆顶展示3张牌，选择1张加入自己手中，其余置入自己弃牌堆"
        ),
        "en": (
            "Choose a card type; every card of that type in all of the target's zones becomes Revealed. "
            "Reveal the top 3 cards of your deck, add 1 of them to your hand and put the rest into your discard pile."
        ),
        "fr": (
            "Choisissez un type de carte ; toutes les cartes de ce type dans toutes les zones de la cible deviennent Révélées. "
            "Révélez les 3 cartes du dessus de votre deck, ajoutez-en 1 à votre main et placez le reste dans votre défausse."
        ),
        "ja": (
            "種類を1つ選ぶ。対象のすべての領域にあるその種類のカードは公開される。"
            "自分の山札の上から3枚を公開し、1枚を手札に加え、残りを自分の捨て札に置く。"
        ),
    },
    "Ankh": {
        "zh": (
            "使所有玩家的[[icon:H]]、[[icon:E]]、[[icon:M]]回到各自对局开始时的数值；"
            "已阵亡玩家以死亡时的位置、状态、手牌和牌堆复活；然后自己-2[[icon:E]]"
        ),
        "en": (
            "Return every player's [[icon:H]], [[icon:E]] and [[icon:M]] to their values at the start of the match; "
            "defeated players revive with the position, statuses, hand and deck they had when they died; "
            "then you lose 2[[icon:E]]."
        ),
        "fr": (
            "Ramenez les [[icon:H]], [[icon:E]] et [[icon:M]] de tous les joueurs à leurs valeurs du début de la partie ; "
            "les joueurs vaincus reviennent avec la position, les états, la main et le deck qu'ils avaient à leur mort ; "
            "puis vous perdez 2[[icon:E]]."
        ),
        "ja": (
            "すべてのプレイヤーの[[icon:H]]、[[icon:E]]、[[icon:M]]を対局開始時の値に戻す。"
            "倒れたプレイヤーは死亡時の位置・状態・手札・山札で復活する。その後、自分は2[[icon:E]]を失う。"
        ),
    },
    "Magnet": {
        "zh": "造成2[[icon:electric_damage]]；展示目标所有手牌，从目标手牌中选择1张加入自己手牌",
        "en": "Deal 2[[icon:electric_damage]]; reveal the target's hand, then choose 1 of those cards and add it to your hand.",
        "fr": "Infligez 2[[icon:electric_damage]] ; révélez la main de la cible, puis choisissez-y 1 carte et ajoutez-la à votre main.",
        "ja": "2[[icon:electric_damage]]を与える。対象の手札をすべて公開し、その中から1枚を選んで自分の手札に加える。",
    },
    "Wind": {
        "zh": "目标下回合的回合开始抽牌结算后，丢弃全场所有[[icon:E]]消耗不超过本次实际花费+1的手牌",
        "en": "After the target's next turn-start draw resolves, discard every hand card in play whose [[icon:E]] cost does not exceed this card's actual cost +1.",
        "fr": "Après la pioche de début du prochain tour de la cible, défaussez toutes les cartes en main dont le coût en [[icon:E]] ne dépasse pas le coût réel de cette carte +1.",
        "ja": "対象の次のターン開始時のドロー解決後、今回の実際のコスト+1以下の[[icon:E]]コストを持つ手札をすべて捨てる。",
    },
    "Salt": {
        "zh": "对攻击者造成向上取整(本牌所响应攻击的首次伤害×60%)[[icon:D]]  响应：被作为攻击牌目标",
        "en": "Deal ceil(first damage of the responded attack × 60%)[[icon:D]] to the attacker.  Response: Targeted by an attack card.",
        "fr": "Infligez arrondi supérieur(premiers dégâts de l'attaque répondue × 60%)[[icon:D]] à l'attaquant.  Réponse : ciblé par une carte d'attaque.",
        "ja": "攻撃者に切り上げ(応答した攻撃の最初のダメージ×60%)[[icon:D]]を与える。  応答：攻撃カードの対象となる。",
    },
    "Dizzy": {
        "zh": "装备时和目标回合开始时，使目标获得1层失明；每张装备在目标上的此牌使其造成的伤害+50%",
        "en": "When equipped and at the start of the target's turn, the target gains 1 Blindness; each copy of this equipment on the target increases the damage the target deals by 50%.",
        "fr": "À l'équipement et au début du tour de la cible, la cible gagne 1 Cécité ; chaque copie de cet équipement sur la cible augmente de 50% les dégâts qu'elle inflige.",
        "ja": "装備時と対象のターン開始時、対象は失明を1獲得する。対象に装備されたこのカード1枚につき、対象が与えるダメージが50%増加する。",
    },
    "Marble": {
        "zh": "对目标造成9[[icon:D]]；前述伤害每次造成实际伤害时，随机对除目标外另一名可选中玩家造成23[[icon:D]]",
        "en": "Deal 9[[icon:D]] to the target; each time the preceding damage deals actual damage, deal 23[[icon:D]] to a random other selectable player.",
        "fr": "Infligez 9[[icon:D]] à la cible ; chaque fois que ces dégâts infligent des dégâts réels, infligez 23[[icon:D]] à un autre joueur sélectionnable choisi au hasard.",
        "ja": "対象に9[[icon:D]]を与える。このダメージが実際にダメージを与えるたび、対象以外の選択可能なプレイヤー1人にランダムで23[[icon:D]]を与える。",
    },
    "Citron": {
        "zh": "存在期间，目标打出攻击牌前，使该牌暂时获得精准；若该牌已有精准，则改为暂时获得隐匿",
        "en": "While this equipment exists, before the target plays an attack card, that card temporarily gains Precision; if it already has Precision, it temporarily gains Stealth instead.",
        "fr": "Tant que cet équipement existe, avant que la cible ne joue une carte d'attaque, cette carte gagne temporairement Précision ; si elle a déjà Précision, elle gagne temporairement Furtif à la place.",
        "ja": "存在中、対象が攻撃カードを使用する前に、そのカードは一時的に精度を得る。すでに精度を持つ場合、代わりに一時的に隠密を得る。",
    },
    "Magic Bur": {
        "zh": "对攻击者施加向上取整(本次将受伤害/4)层易损  响应：被作为攻击牌目标",
        "en": "Apply ceil(damage you would take / 4) stacks of Vulnerable to the attacker.  Response: Targeted by an attack card.",
        "fr": "Appliquez arrondi supérieur(dégâts que vous allez subir / 4) charges de Vulnérabilité à l'attaquant.  Réponse : ciblé par une carte d'attaque.",
        "ja": "攻撃者に切り上げ(今回受けるダメージ/4)層の脆弱を与える。  応答：攻撃カードの対象となる。",
    },
    "Magic Rubber": {
        "zh": "使自己手中[[icon:E]]花费最高的一张牌获得暂时迅捷3  响应：被作为攻击牌目标",
        "en": "Give the card in your hand with the highest [[icon:E]] cost Temporary Swift:3.  Response: Targeted by an attack card.",
        "fr": "Donnez Rapidité temporaire:3 à la carte de votre main au coût en [[icon:E]] le plus élevé.  Réponse : ciblé par une carte d'attaque.",
        "ja": "自分の手札の中で最も[[icon:E]]コストが高いカードに一時迅捷:3を与える。  応答：攻撃カードの対象となる。",
    },
    "Rubber": {
        "zh": "攻击者本次攻击结算后，使其手中所有牌获得暂时沉重1  响应：被作为攻击牌目标",
        "en": "After the attacker's attack resolves, give every card in their hand Temporary Heavy:1.  Response: Targeted by an attack card.",
        "fr": "Après la résolution de l'attaque de l'attaquant, donnez Lourdeur temporaire:1 à toutes les cartes de sa main.  Réponse : ciblé par une carte d'attaque.",
        "ja": "攻撃者の攻撃解決後、その手札のすべてのカードに一時鈍重:1を与える。  応答：攻撃カードの対象となる。",
    },
    "Dead Leaf": {
        "zh": "对目标造成6[[icon:D]]；若目标手中没有反制牌，则对目标施加1层迟缓",
        "en": "Deal 6[[icon:D]] to the target; if the target has no counter card in hand, apply 1 Sluggish to the target.",
        "fr": "Infligez 6[[icon:D]] à la cible ; si la cible n'a aucune carte de contre en main, appliquez 1 Lenteur à la cible.",
        "ja": "対象に6[[icon:D]]を与える。対象の手札にカウンターカードがない場合、対象に遅鈍を1与える。",
    },
    "Magic Pearl": {
        "zh": (
            "对目标造成5[[icon:D]]；进入手牌时获得2层威力；"
            "自己回合开始时，若费用满足，自动对[[icon:H]]最低的可选中敌方玩家打出1张放逐复制"
            "（魔力迅捷3，不触发此效果）；本局每打出过1次此牌，就额外打出1张"
        ),
        "en": (
            "Deal 5[[icon:D]] to the target; this card gains 2 Power when it enters your hand. "
            "At the start of your turn, if its cost can be paid, automatically play 1 exiled copy "
            "(Magic Swift:3, does not trigger this effect) against the selectable enemy player with the lowest [[icon:H]]; "
            "play 1 extra copy for each time this card has been played this match."
        ),
        "fr": (
            "Infligez 5[[icon:D]] à la cible ; cette carte gagne 2 Puissance en entrant dans votre main. "
            "Au début de votre tour, si son coût peut être payé, jouez automatiquement 1 copie exilée "
            "(Rapidité magique:3, ne déclenche pas cet effet) contre le joueur ennemi sélectionnable ayant le moins de [[icon:H]] ; "
            "jouez 1 copie supplémentaire par utilisation de cette carte dans la partie."
        ),
        "ja": (
            "対象に5[[icon:D]]を与える。手札に加わったとき、このカードは威力を2獲得する。"
            "自分のターン開始時、コストを支払えるなら、[[icon:H]]が最も低い選択可能な敵プレイヤーに"
            "追放コピー(魔力迅捷:3、この効果を発動しない)を1枚自動で使用する。"
            "この対局でこのカードを使用した回数1回につき、さらに1枚使用する。"
        ),
    },
    "Magic Trident": {
        "zh": "对目标造成18[[icon:D]]；此牌在手牌中时，自己每抽1张牌，此牌获得1层威力",
        "en": "Deal 18[[icon:D]] to the target; while this card is in your hand, it gains 1 Power each time you draw a card.",
        "fr": "Infligez 18[[icon:D]] à la cible ; tant que cette carte est en main, elle gagne 1 Puissance chaque fois que vous piochez une carte.",
        "ja": "対象に18[[icon:D]]を与える。このカードが手札にある間、自分がカードを1枚引くたび、このカードは威力を1獲得する。",
    },
    "Needle": {
        "zh": "对目标造成4[[icon:D]]；命中时，对目标施加1层无法反制",
        "en": "Deal 4[[icon:D]] to the target; when it hits, apply 1 Uncounterable to the target.",
        "fr": "Infligez 4[[icon:D]] à la cible ; en cas de touche, appliquez 1 Incapable de contrer à la cible.",
        "ja": "対象に4[[icon:D]]を与える。命中時、対象に反撃不可を1与える。",
    },
    "Bubble Bomb": {
        "zh": "使攻击者无法行动直到其下回合开始，并对其施加1层眩晕  响应：被作为攻击牌目标",
        "en": "The attacker cannot act until the start of their next turn, and gains 1 Stun.  Response: Targeted by an attack card.",
        "fr": "L'attaquant ne peut pas agir jusqu'au début de son prochain tour et gagne 1 Étourdissement.  Réponse : ciblé par une carte d'attaque.",
        "ja": "攻撃者は次の自分のターン開始時まで行動できず、スタンを1獲得する。  応答：攻撃カードの対象となる。",
    },
    "Nitro": {
        "zh": "使所响应的牌失效，并使其在本次结算后进入放逐区  响应：敌方对自己使用牌",
        "en": "Negate the responded card; after this resolution it enters exile.  Response: An enemy uses a card on you.",
        "fr": "Annulez la carte répondue ; après cette résolution, elle part en exil.  Réponse : un ennemi utilise une carte sur vous.",
        "ja": "応答したカードを無効にする。この解決後、そのカードは追放領域に置かれる。  応答：敵が自分にカードを使用した時",
    },
    "Magic Antimatter": {
        "zh": "所响应的牌生效前，对除自己以外的所有可选中玩家造成25[[icon:D]]  响应：非自己回合将受到致命伤害",
        "en": "Before the responded card takes effect, deal 25[[icon:D]] to every selectable player except yourself.  Response: You would take lethal damage during another player's turn.",
        "fr": "Avant que la carte répondue prenne effet, infligez 25[[icon:D]] à tous les joueurs sélectionnables sauf vous.  Réponse : vous allez subir des dégâts mortels pendant le tour d'un autre joueur.",
        "ja": "応答したカードが効果を発揮する前に、自分以外の選択可能なすべてのプレイヤーに25[[icon:D]]を与える。  応答：自分のターン以外に致命ダメージを受ける時",
    },
    "Illuminati Triangle": {
        "zh": "回复目标20[[icon:H]]，并对目标施加所有类型的状态（除状态免疫和不可选中）；目标下回合结束时，清除其所有状态",
        "en": "Restore 20[[icon:H]] to the target and apply every type of status to the target (except Status Immunity and Untargetable); at the end of the target's next turn, remove all of their statuses.",
        "fr": "Rendez 20[[icon:H]] à la cible et appliquez-lui tous les types d'état (sauf Immunité de statut et Non ciblable) ; à la fin du prochain tour de la cible, retirez tous ses états.",
        "ja": "対象の[[icon:H]]を20回復し、対象に(状態免疫と対象不可を除く)すべての種類の状態を与える。対象の次のターン終了時、対象のすべての状態を解除する。",
    },
    "Copper Rod": {
        "zh": "免受所响应攻击牌的伤害，改为将伤害量向上取整平分为自己所有手牌的电荷。  响应：被作为攻击牌目标",
        "en": "Prevent the damage of the responded attack card; instead, distribute Charge equal to that damage, rounded up, across every card in your hand.  Response: Targeted by an attack card.",
        "fr": "Annulez les dégâts de la carte d'attaque répondue ; à la place, répartissez des Charges égales à ces dégâts, arrondies au supérieur, sur toutes les cartes de votre main.  Réponse : ciblé par une carte d'attaque.",
        "ja": "応答した攻撃カードのダメージを防ぐ。代わりに、そのダメージ量を切り上げて自分の手札すべてに電荷として均等に分ける。  応答：攻撃カードの対象となる。",
    },
    "Horn": {
        "zh": "对所有敌方目标造成10[[icon:D]]，不使所响应伤害失效  响应：自己将受到无来源或来源为自己的伤害",
        "en": "Deal 10[[icon:D]] to every enemy target; the responded damage is not negated.  Response: You would take damage with no source or with yourself as the source.",
        "fr": "Infligez 10[[icon:D]] à toutes les cibles ennemies ; les dégâts répondus ne sont pas annulés.  Réponse : vous allez subir des dégâts sans source ou dont vous êtes la source.",
        "ja": "すべての敵対象に10[[icon:D]]を与える。応答したダメージは無効化されない。  応答：自分が発生源なし、または自分自身が発生源のダメージを受ける時",
    },
    "Domino": {
        "zh": "使自己获得2层幸运；对目标造成6[[icon:D]]；若本次伤害即将暴击，本次获得暂时精准且最终伤害×2",
        "en": "You gain 2 Luck; deal 6[[icon:D]] to the target. If this damage is about to crit, it temporarily gains Precision and its final damage is ×2.",
        "fr": "Vous gagnez 2 Chance ; infligez 6[[icon:D]] à la cible. Si ces dégâts vont être critiques, ils obtiennent temporairement Précision et leurs dégâts finaux sont ×2.",
        "ja": "自分は運を2獲得する。対象に6[[icon:D]]を与える。このダメージがクリティカルになる場合、一時的に精度を得て最終ダメージが×2になる。",
    },
    "Blood Dice": {
        "zh": "对目标造成6[[icon:D]]，使目标获得10层幸运；本次伤害必定暴击且不消耗幸运",
        "en": "Deal 6[[icon:D]] to the target and give the target 10 Luck; this damage always crits and does not consume Luck.",
        "fr": "Infligez 6[[icon:D]] à la cible et donnez-lui 10 Chance ; ces dégâts sont toujours critiques et ne consomment pas de Chance.",
        "ja": "対象に6[[icon:D]]を与え、対象は運を10獲得する。このダメージは必ずクリティカルになり、運を消費しない。",
    },
    "Bugatti": {
        "zh": "装备存在时，目标手牌上限-2；目标回合开始正常抽牌后，抽至其手牌上限",
        "en": "While this equipment exists, the target's hand limit is -2; after the target's normal turn-start draw, they draw up to their hand limit.",
        "fr": "Tant que cet équipement existe, la limite de main de la cible est de -2 ; après la pioche normale de début de tour de la cible, elle pioche jusqu'à sa limite de main.",
        "ja": "装備が存在する間、対象の手札上限は-2。対象のターン開始時の通常ドロー後、対象は手札上限まで引く。",
    },
    "Clover": {
        "zh": "目标回合开始时，使目标获得4层幸运",
        "en": "At the start of the target's turn, the target gains 4 Luck.",
        "fr": "Au début du tour de la cible, la cible gagne 4 Chance.",
        "ja": "対象のターン開始時、対象は運を4獲得する。",
    },
    "Magic Clover": {
        "zh": "使目标本回合暴击倍率+1×并获得8层幸运",
        "en": "The target gains +1× crit multiplier this turn and gains 8 Luck.",
        "fr": "La cible gagne +1× de multiplicateur critique ce tour et gagne 8 Chance.",
        "ja": "対象はこのターンのクリティカル倍率+1×、運を8獲得する。",
    },
    "Broccoli": {
        "zh": "对目标造成10[[icon:D]]；若此牌被反制，则对目标额外造成3[[icon:D]]×2",
        "en": "Deal 10[[icon:D]] to the target; if this card is countered, deal an additional 3[[icon:D]]×2 to the target.",
        "fr": "Infligez 10[[icon:D]] à la cible ; si cette carte est contrée, infligez 3[[icon:D]]×2 supplémentaires à la cible.",
        "ja": "対象に10[[icon:D]]を与える。このカードが反撃された場合、対象に追加で3[[icon:D]]×2を与える。",
    },
    "Clay": {
        "zh": "对目标造成5[[icon:D]]；此牌在手牌中时，自己每受到6点实际伤害，此牌获得1层威力，最多以此方式获得18层威力",
        "en": "Deal 5[[icon:D]] to the target; while this card is in your hand, it gains 1 Power for every 6 actual damage you take, up to 18 Power gained this way.",
        "fr": "Infligez 5[[icon:D]] à la cible ; tant que cette carte est en main, elle gagne 1 Puissance pour chaque 6 dégâts réels que vous subissez, jusqu'à 18 Puissance obtenues ainsi.",
        "ja": "対象に5[[icon:D]]を与える。このカードが手札にある間、自分が実際に6ダメージを受けるたび、このカードは威力を1獲得する（この方法で最大18層）。",
    },
    "Lotus": {
        "zh": "回复目标10[[icon:H]]；目标每有1层[[icon:P]]，本次回复量-1并移除其1层[[icon:P]]，重复至目标没有[[icon:P]]",
        "en": "Restore 10[[icon:H]] to the target; for each 1[[icon:P]] the target has, reduce the healing by 1 and remove 1 of their [[icon:P]], repeating until the target has no [[icon:P]].",
        "fr": "Rendez 10[[icon:H]] à la cible ; pour chaque 1[[icon:P]] de la cible, réduisez les soins de 1 et retirez-lui 1[[icon:P]], en répétant jusqu'à ce que la cible n'ait plus de [[icon:P]].",
        "ja": "対象の[[icon:H]]を10回復する。対象の[[icon:P]]1層ごとに回復量を1減らし、対象の[[icon:P]]を1層取り除く。対象の[[icon:P]]がなくなるまで繰り返す。",
    },
    "Chitin": {
        "zh": "目标回合开始时，若目标没有邪眼，则对目标施加1层邪眼；本装备被摧毁时，清除装备目标的所有邪眼",
        "en": "At the start of the target's turn, if the target has no Nazar, apply 1 Nazar to the target; when this equipment is destroyed, remove all Nazar from the equipment target.",
        "fr": "Au début du tour de la cible, si la cible n'a pas de Nazar, appliquez 1 Nazar à la cible ; lorsque cet équipement est détruit, retirez tous les Nazar de la cible de l'équipement.",
        "ja": "対象のターン開始時、対象がナザールを持たない場合、対象にナザールを1与える。この装備が破壊された時、装備対象のナザールをすべて取り除く。",
    },
    "Blueberries": {
        "zh": "对目标造成1[[icon:D]]×4（4子瓣）；每次造成伤害时，对目标施加3层霜冻",
        "en": "Deal 1[[icon:D]]×4 (4 sub-petals) to the target; each time damage is dealt, apply 3 Frost to the target.",
        "fr": "Infligez 1[[icon:D]]×4 (4 sous-pétales) à la cible ; chaque fois que des dégâts sont infligés, appliquez 3 Givre à la cible.",
        "ja": "対象に1[[icon:D]]×4（4サブ花びら）を与える。ダメージを与えるたび、対象に霜を3与える。",
    },
    "Icicle": {
        "zh": "对目标造成6[[icon:D]]；造成伤害时，对目标施加3层霜冻；将1张[[card:Icicle]]洗入自己弃牌堆",
        "en": "Deal 6[[icon:D]] to the target; when damage is dealt, apply 3 Frost to the target; shuffle 1[[card:Icicle]] into your discard pile.",
        "fr": "Infligez 6[[icon:D]] à la cible ; lorsque des dégâts sont infligés, appliquez 3 Givre à la cible ; mélangez 1[[card:Icicle]] dans votre défausse.",
        "ja": "対象に6[[icon:D]]を与える。ダメージを与えた時、対象に霜を3与える。自分の捨て札に[[card:Icicle]]を1枚混ぜる。",
    },
    "Ruby": {
        "zh": (
            "选择自己手牌中1张可支付实际消耗的攻击牌；"
            "支付其[[icon:E]]和[[icon:M]]实际消耗的1/2（分别向上取整），使其聚变层数+1并获得被揭示；"
            "无法支付时不能选择该牌"
        ),
        "en": (
            "Choose 1 attack card in your hand whose actual cost you can pay; "
            "pay half of its actual [[icon:E]] and [[icon:M]] cost (each rounded up), then it gains 1 Fusion and becomes Revealed. "
            "You cannot choose a card you cannot pay for."
        ),
        "fr": (
            "Choisissez dans votre main 1 carte d'attaque dont vous pouvez payer le coût réel ; "
            "payez la moitié de son coût réel en [[icon:E]] et en [[icon:M]] (arrondie au supérieur pour chacun), puis elle gagne 1 Fusion et devient Révélée. "
            "Vous ne pouvez pas choisir une carte que vous ne pouvez pas payer."
        ),
        "ja": (
            "自分の手札から実際コストを支払える攻撃カードを1枚選ぶ。"
            "その実際の[[icon:E]]と[[icon:M]]コストの1/2（それぞれ切り上げ）を支払い、聚变を1獲得させ、公開する。"
            "支払えないカードは選べない。"
        ),
    },
    "Blood Diamond": {
        "zh": "对目标造成3[[icon:D]]×4（4子瓣）；每次造成实际伤害时，对目标施加1层流血",
        "en": "Deal 3[[icon:D]]×4 (4 sub-petals) to the target; each time actual damage is dealt, apply 1 Bleed to the target.",
        "fr": "Infligez 3[[icon:D]]×4 (4 sous-pétales) à la cible ; chaque fois que des dégâts réels sont infligés, appliquez 1 Saignement à la cible.",
        "ja": "対象に3[[icon:D]]×4（4サブ花びら）を与える。実際にダメージを与えるたび、対象に出血を1与える。",
    },
    "Sugar": {
        "zh": "对目标造成2[[icon:D]]×6（6子瓣）；回复目标20[[icon:H]]",
        "en": "Deal 2[[icon:D]]×6 (6 sub-petals) to the target; restore 20[[icon:H]] to the target.",
        "fr": "Infligez 2[[icon:D]]×6 (6 sous-pétales) à la cible ; rendez 20[[icon:H]] à la cible.",
        "ja": "対象に2[[icon:D]]×6（6サブ花びら）を与える。対象の[[icon:H]]を20回復する。",
    },
    "Blood Chromosome": {
        "zh": (
            "从自己弃牌堆随机将1张牌加入手中，并使其获得共生，然后对自己造成2[[icon:D]]；"
            "重复此过程，直至手牌已满或弃牌堆为空。结算完成后，若自己的[[icon:H]]≤0，再进行死亡结算"
        ),
        "en": (
            "Add 1 random card from your discard pile to your hand and give it Symbiosis, then deal 2[[icon:D]] to yourself; "
            "repeat until your hand is full or your discard pile is empty. After this resolves, if your [[icon:H]] is 0 or less, death is settled then."
        ),
        "fr": (
            "Ajoutez 1 carte au hasard de votre défausse à votre main et donnez-lui Symbiose, puis infligez-vous 2[[icon:D]] ; "
            "répétez jusqu'à ce que votre main soit pleine ou votre défausse vide. Une fois la résolution terminée, si votre [[icon:H]] est ≤0, la mort est résolue à ce moment."
        ),
        "ja": (
            "自分の捨て札からランダムに1枚を手札に加えて共生を与え、自分に2[[icon:D]]を与える。"
            "手札が上限に達するか捨て札が空になるまで繰り返す。解決後、自分の[[icon:H]]が0以下なら、その時点で死亡を処理する。"
        ),
    },
    "Ransom Money": {
        "zh": "选择自己放逐区中1张牌，将其加入弃牌堆",
        "en": "Choose 1 card in your exile and put it into your discard pile.",
        "fr": "Choisissez 1 carte dans votre exil et placez-la dans votre défausse.",
        "ja": "自分の追放領域からカードを1枚選び、捨て札に置く。",
    },
    "Indictment": {
        "zh": "将所响应攻击牌每次造成的物理伤害和电伤分别转化为等量护盾  响应：被作为攻击牌目标",
        "en": "Convert each instance of physical damage and electric damage dealt by the responded attack card into an equal amount of Shield.  Response: Targeted by an attack card.",
        "fr": "Convertissez chaque instance de dégâts physiques et électriques infligés par la carte d'attaque répondue en une quantité de Bouclier équivalente.  Réponse : ciblé par une carte d'attaque.",
        "ja": "応答した攻撃カードが与える物理ダメージと電撃ダメージを、それぞれ同量の護盾に変換する。  応答：攻撃カードの対象となる。",
    },
}
