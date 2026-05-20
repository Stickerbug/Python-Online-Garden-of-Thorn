LANGS = ('zh', 'en', 'fr', 'pt', 'ru', 'ja')


CARD_I18N = {
    'Basic': {
        'name': {'zh': '基本', 'en': 'Basic', 'fr': 'Base', 'pt': 'Básico', 'ru': 'База', 'ja': '基本'},
        'desc': {'zh': '最基础的攻击。', 'en': 'The most basic attack.', 'fr': 'L’attaque la plus simple.', 'pt': 'O ataque mais simples.', 'ru': 'Самая простая атака.', 'ja': '最も基本的な攻撃。'},
        'effect': {'zh': '造成6D', 'en': 'Deal 6D', 'fr': 'Inflige 6D', 'pt': 'Causa 6D', 'ru': 'Наносит 6D', 'ja': '6Dを与える'},
    },
    'Bone': {
        'name': {'zh': '骨头', 'en': 'Bone', 'fr': 'Os', 'pt': 'Osso', 'ru': 'Кость', 'ja': '骨'},
        'desc': {'zh': '坚固，好用。', 'en': 'Solid and reliable.', 'fr': 'Solide et fiable.', 'pt': 'Firme e confiável.', 'ru': 'Надежная кость.', 'ja': '堅く扱いやすい。'},
        'effect': {'zh': '造成12D', 'en': 'Deal 12D', 'fr': 'Inflige 12D', 'pt': 'Causa 12D', 'ru': 'Наносит 12D', 'ja': '12Dを与える'},
    },
    'Stinger': {
        'name': {'zh': '刺', 'en': 'Stinger', 'fr': 'Dard', 'pt': 'Ferrão', 'ru': 'Жало', 'ja': '針'},
        'desc': {'zh': '一击造成大量伤害。', 'en': 'One heavy strike.', 'fr': 'Une frappe lourde.', 'pt': 'Um golpe pesado.', 'ru': 'Один мощный удар.', 'ja': '重い一撃。'},
        'effect': {'zh': '造成20D', 'en': 'Deal 20D', 'fr': 'Inflige 20D', 'pt': 'Causa 20D', 'ru': 'Наносит 20D', 'ja': '20Dを与える'},
    },
    'Sand': {
        'name': {'zh': '沙子', 'en': 'Sand', 'fr': 'Sable', 'pt': 'Areia', 'ru': 'Песок', 'ja': '砂'},
        'desc': {'zh': '一把沙分成多次伤害。', 'en': 'A handful of small hits.', 'fr': 'Plusieurs petits coups.', 'pt': 'Vários golpes leves.', 'ru': 'Несколько малых ударов.', 'ja': '細かな連続攻撃。'},
        'effect': {'zh': '造成3×4D（精准）', 'en': 'Deal 3×4D (Precision)', 'fr': 'Inflige 3×4D (Précis)', 'pt': 'Causa 3×4D (Precisão)', 'ru': 'Наносит 3×4D (Точно)', 'ja': '3×4D（精密）'},
    },
    'Wing': {
        'name': {'zh': '翅膀', 'en': 'Wing', 'fr': 'Aile', 'pt': 'Asa', 'ru': 'Крыло', 'ja': '翼'},
        'desc': {'zh': '回旋的翅膀连续打击。', 'en': 'A returning double strike.', 'fr': 'Deux coups en retour.', 'pt': 'Dois golpes de retorno.', 'ru': 'Два возвратных удара.', 'ja': '戻る翼の二連撃。'},
        'effect': {'zh': '造成8×2D（精准）', 'en': 'Deal 8×2D (Precision)', 'fr': 'Inflige 8×2D (Précis)', 'pt': 'Causa 8×2D (Precisão)', 'ru': 'Наносит 8×2D (Точно)', 'ja': '8×2D（精密）'},
    },
    'Light': {
        'name': {'zh': '轻', 'en': 'Light', 'fr': 'Léger', 'pt': 'Leve', 'ru': 'Лёгкость', 'ja': '軽'},
        'desc': {'zh': '轻盈，却能连击。', 'en': 'Light, but still sharp.', 'fr': 'Léger mais tranchant.', 'pt': 'Leve, mas cortante.', 'ru': 'Легко, но остро.', 'ja': '軽くても鋭い。'},
        'effect': {'zh': '造成2×2D（精准）', 'en': 'Deal 2×2D (Precision)', 'fr': 'Inflige 2×2D (Précis)', 'pt': 'Causa 2×2D (Precisão)', 'ru': 'Наносит 2×2D (Точно)', 'ja': '2×2D（精密）'},
    },
    'Fang': {
        'name': {'zh': '尖牙', 'en': 'Fang', 'fr': 'Croc', 'pt': 'Presa', 'ru': 'Клык', 'ja': '牙'},
        'desc': {'zh': '汲取伤口中的生命。', 'en': 'Draw life from the wound.', 'fr': 'Draine la vie de la plaie.', 'pt': 'Drena vida da ferida.', 'ru': 'Тянет жизнь из раны.', 'ja': '傷から生命を吸う。'},
        'effect': {'zh': '造成8D；若造成伤害，+4H', 'en': 'Deal 8D; if it hits, +4H', 'fr': 'Inflige 8D; si touche, +4H', 'pt': 'Causa 8D; se acertar, +4H', 'ru': '8D; при попадании +4H', 'ja': '8D。命中時+4H'},
    },
    'Triangle': {
        'name': {'zh': '三角形', 'en': 'Triangle', 'fr': 'Triangle', 'pt': 'Triângulo', 'ru': 'Треугольник', 'ja': '三角形'},
        'desc': {'zh': '层数越高，伤害越高。', 'en': 'Stacks grow its damage.', 'fr': 'Ses charges augmentent les dégâts.', 'pt': 'Acúmulos aumentam o dano.', 'ru': 'Слои повышают урон.', 'ja': '層でダメージ増加。'},
        'effect': {'zh': '造成(6+3×层数)D；命中后三角形+1', 'en': 'Deal (6+3×stacks)D; on hit +1 Triangle', 'fr': '(6+3×couches)D; si touche +1 Triangle', 'pt': '(6+3×camadas)D; acerto +1 Triângulo', 'ru': '(6+3×слои)D; при попадании +1', 'ja': '(6+3×層)D。命中時+1'},
    },
    'MagicBone': {
        'name': {'zh': '魔法骨头', 'en': 'Magic Bone', 'fr': 'Os magique', 'pt': 'Osso Mágico', 'ru': 'Маг. кость', 'ja': '魔法の骨'},
        'desc': {'zh': '魔力凝成的骨头。', 'en': 'A bone shaped by magic.', 'fr': 'Un os formé par magie.', 'pt': 'Um osso feito de magia.', 'ru': 'Кость из магии.', 'ja': '魔力でできた骨。'},
        'effect': {'zh': '造成15D', 'en': 'Deal 15D', 'fr': 'Inflige 15D', 'pt': 'Causa 15D', 'ru': 'Наносит 15D', 'ja': '15Dを与える'},
    },
    'MagicStinger': {
        'name': {'zh': '魔法刺', 'en': 'Magic Stinger', 'fr': 'Dard magique', 'pt': 'Ferrão Mágico', 'ru': 'Маг. жало', 'ja': '魔法の針'},
        'desc': {'zh': '魔力强化的尖刺。', 'en': 'A stinger charged with magic.', 'fr': 'Un dard chargé de magie.', 'pt': 'Um ferrão com magia.', 'ru': 'Жало с магией.', 'ja': '魔力を帯びた針。'},
        'effect': {'zh': '造成30D（精准）', 'en': 'Deal 30D (Precision)', 'fr': 'Inflige 30D (Précis)', 'pt': 'Causa 30D (Precisão)', 'ru': 'Наносит 30D (Точно)', 'ja': '30D（精密）'},
    },
    'Fission': {
        'name': {'zh': '裂变', 'en': 'Fission', 'fr': 'Fission', 'pt': 'Fissão', 'ru': 'Деление', 'ja': '分裂'},
        'desc': {'zh': '把一次攻击分裂为多次。', 'en': 'Split one attack into many.', 'fr': 'Divise une attaque en plusieurs.', 'pt': 'Divide um ataque em vários.', 'ru': 'Делит атаку на части.', 'ja': '攻撃を複数回に分ける。'},
        'effect': {'zh': '选择一张手中攻击牌，裂变层数+2', 'en': 'Choose an attack in hand; Fission +2', 'fr': 'Choisissez une attaque en main; Fission +2', 'pt': 'Escolha um ataque na mão; Fissão +2', 'ru': 'Выберите атаку в руке; Деление +2', 'ja': '手札のThornを選び、分裂+2'},
    },
    'Fusion': {
        'name': {'zh': '聚变', 'en': 'Fusion', 'fr': 'Fusion', 'pt': 'Fusão', 'ru': 'Слияние', 'ja': '融合'},
        'desc': {'zh': '把同名攻击合为一张。', 'en': 'Merge same-name attacks.', 'fr': 'Fusionne des attaques du même nom.', 'pt': 'Funde ataques do mesmo nome.', 'ru': 'Сливает одноимённые атаки.', 'ja': '同名Thornを1枚に融合。'},
        'effect': {'zh': '选择2-3张同名攻击牌，聚变相加，裂变取最大', 'en': 'Choose 2-3 same-name attacks; add Fusion, keep max Fission', 'fr': '2-3 attaques identiques; Fusion s’additionne, Fission max', 'pt': '2-3 ataques iguais; soma Fusão, Fissão máxima', 'ru': '2-3 одинаковые атаки; сложить Слияние, макс. Деление', 'ja': '同名Thorn2-3枚。融合加算、分裂は最大'},
    },
    'Iris': {
        'name': {'zh': '鸢尾', 'en': 'Iris', 'fr': 'Iris', 'pt': 'Íris', 'ru': 'Ирис', 'ja': 'アイリス'},
        'desc': {'zh': '美丽且致命。', 'en': 'Beautiful and deadly.', 'fr': 'Belle et mortelle.', 'pt': 'Bela e mortal.', 'ru': 'Красива и смертельна.', 'ja': '美しく致命的。'},
        'effect': {'zh': '施加10层中毒', 'en': 'Apply 10 Poison', 'fr': 'Applique 10 Poison', 'pt': 'Aplica 10 Veneno', 'ru': '+10 Яд', 'ja': '毒10を付与'},
    },
    'Fire': {
        'name': {'zh': '火', 'en': 'Fire', 'fr': 'Feu', 'pt': 'Fogo', 'ru': 'Огонь', 'ja': '火'},
        'desc': {'zh': '缓慢但持久地燃烧。', 'en': 'Slow, lasting burn.', 'fr': 'Brûlure lente et durable.', 'pt': 'Queima lenta e duradoura.', 'ru': 'Медленное горение.', 'ja': '遅く長く燃える。'},
        'effect': {'zh': '造成2层灼烧', 'en': 'Apply 2 Burn', 'fr': 'Applique 2 Brûlure', 'pt': 'Aplica 2 Queima', 'ru': '+2 Горение', 'ja': '火傷2を付与'},
    },
    'Fries': {
        'name': {'zh': '薯条', 'en': 'Fries', 'fr': 'Frites', 'pt': 'Batatas', 'ru': 'Фри', 'ja': 'フライドポテト'},
        'desc': {'zh': '高热量，补充生命。', 'en': 'High calories, fast healing.', 'fr': 'Calories rapides.', 'pt': 'Calorias rápidas.', 'ru': 'Быстрые калории.', 'ja': '高カロリーで回復。'},
        'effect': {'zh': '+12H', 'en': '+12H', 'fr': '+12H', 'pt': '+12H', 'ru': '+12H', 'ja': '+12H'},
    },
    'Rose': {
        'name': {'zh': '玫瑰', 'en': 'Rose', 'fr': 'Rose', 'pt': 'Rosa', 'ru': 'Роза', 'ja': 'バラ'},
        'desc': {'zh': '花香可以治愈你。', 'en': 'Its scent heals.', 'fr': 'Son parfum soigne.', 'pt': 'Seu aroma cura.', 'ru': 'Аромат лечит.', 'ja': '香りが癒す。'},
        'effect': {'zh': '+7H', 'en': '+7H', 'fr': '+7H', 'pt': '+7H', 'ru': '+7H', 'ja': '+7H'},
    },
    'ManaOrb': {
        'name': {'zh': '魔法球', 'en': 'Mana Orb', 'fr': 'Orbe de mana', 'pt': 'Orbe de Mana', 'ru': 'Сфера маны', 'ja': 'マナオーブ'},
        'desc': {'zh': '孕育魔力的小球。', 'en': 'A small orb of mana.', 'fr': 'Un petit orbe de mana.', 'pt': 'Um pequeno orbe de mana.', 'ru': 'Малый шар маны.', 'ja': '魔力を宿す球。'},
        'effect': {'zh': '+3M', 'en': '+3M', 'fr': '+3M', 'pt': '+3M', 'ru': '+3M', 'ja': '+3M'},
    },
    'Coffee': {
        'name': {'zh': '咖啡', 'en': 'Coffee', 'fr': 'Café', 'pt': 'Café', 'ru': 'Кофе', 'ja': 'コーヒー'},
        'desc': {'zh': '提神，但小心耐受。', 'en': 'A quick boost. Tolerance builds.', 'fr': 'Coup de fouet, puis tolérance.', 'pt': 'Impulso rápido; cria tolerância.', 'ru': 'Бодрит, но слабеет.', 'ja': '覚醒。耐性に注意。'},
        'effect': {'zh': '+1E；首次使用额外+1E', 'en': '+1E; first use +1E more', 'fr': '+1E; première fois +1E', 'pt': '+1E; primeiro uso +1E', 'ru': '+1E; впервые ещё +1E', 'ja': '+1E。初回さらに+1E'},
    },
    'Chilli': {
        'name': {'zh': '辣椒', 'en': 'Chilli', 'fr': 'Piment', 'pt': 'Pimenta', 'ru': 'Чили', 'ja': '唐辛子'},
        'desc': {'zh': '太辣，只能弃牌解辣。', 'en': 'Too hot. Discard to cool down.', 'fr': 'Trop fort. Défaussez.', 'pt': 'Picante demais. Descarte.', 'ru': 'Слишком остро: сбросьте.', 'ja': '辛すぎる。捨ててしのぐ。'},
        'effect': {'zh': '弃1张牌，然后抽1张', 'en': 'Discard 1, then draw 1', 'fr': 'Défaussez 1, puis piochez 1', 'pt': 'Descarte 1, depois compre 1', 'ru': 'Сбросьте 1, затем доберите 1', 'ja': '1枚捨て、1枚引く'},
    },
    'Chromosome': {
        'name': {'zh': '染色体', 'en': 'Chromosome', 'fr': 'Chromosome', 'pt': 'Cromossomo', 'ru': 'Хромосома', 'ja': '染色体'},
        'desc': {'zh': '从弃牌记忆中取回所需。', 'en': 'Recover a card from discard.', 'fr': 'Récupère une carte défaussée.', 'pt': 'Recupera uma carta do descarte.', 'ru': 'Возвращает карту из сброса.', 'ja': '捨て札から回収する。'},
        'effect': {'zh': '从弃牌堆选择1张加入手牌', 'en': 'Choose 1 discard card into hand', 'fr': 'Choisissez 1 carte de défausse en main', 'pt': 'Escolha 1 do descarte para a mão', 'ru': 'Возьмите 1 карту из сброса', 'ja': '捨て札1枚を手札へ'},
    },
    'Sewage': {
        'name': {'zh': '污水', 'en': 'Sewage', 'fr': 'Égout', 'pt': 'Esgoto', 'ru': 'Стоки', 'ja': '汚水'},
        'desc': {'zh': '腐蚀一件装备。', 'en': 'Corrode one equipment.', 'fr': 'Corrode un équipement.', 'pt': 'Corroe um equipamento.', 'ru': 'Разъедает снаряжение.', 'ja': '装備を腐食させる。'},
        'effect': {'zh': '摧毁敌方1件装备', 'en': 'Destroy 1 enemy equipment', 'fr': 'Détruit 1 équipement ennemi', 'pt': 'Destrói 1 equipamento inimigo', 'ru': 'Уничтожить 1 снаряжение врага', 'ja': '敵装備を1つ破壊'},
    },
    'MagicSewage': {
        'name': {'zh': '魔法污水', 'en': 'Magic Sewage', 'fr': 'Égout magique', 'pt': 'Esgoto Mágico', 'ru': 'Маг. стоки', 'ja': '魔法汚水'},
        'desc': {'zh': '全场腐蚀。', 'en': 'Field-wide corrosion.', 'fr': 'Corrosion générale.', 'pt': 'Corrosão no campo.', 'ru': 'Всеобщая коррозия.', 'ja': '全体を腐食。'},
        'effect': {'zh': '摧毁场上所有可摧毁装备', 'en': 'Destroy all destructible equipment', 'fr': 'Détruit tout équipement destructible', 'pt': 'Destrói todo equipamento destrutível', 'ru': 'Уничтожить всё разрушаемое снаряжение', 'ja': '破壊可能な装備を全破壊'},
    },
    'Mimic': {
        'name': {'zh': '拟态', 'en': 'Mimic', 'fr': 'Mimique', 'pt': 'Mímico', 'ru': 'Мимикрия', 'ja': '擬態'},
        'desc': {'zh': '完美模仿。', 'en': 'A perfect imitation.', 'fr': 'Une imitation parfaite.', 'pt': 'Uma imitação perfeita.', 'ru': 'Идеальная имитация.', 'ja': '完全な模倣。'},
        'effect': {'zh': '复制1张手牌加入手牌；下次费用-1', 'en': 'Copy 1 hand card; next cost -1', 'fr': 'Copie 1 carte en main; prochain coût -1', 'pt': 'Copia 1 carta da mão; próximo custo -1', 'ru': 'Скопировать карту руки; след. цена -1', 'ja': '手札1枚をコピー。次回コスト-1'},
    },
    'Yggdrasil': {
        'name': {'zh': '世界树之叶', 'en': 'Yggdrasil', 'fr': 'Yggdrasil', 'pt': 'Yggdrasil', 'ru': 'Yggdrasil', 'ja': 'Yggdrasil'},
        'desc': {'zh': '死亡边缘的复生。', 'en': 'Rebirth at the brink.', 'fr': 'Renaissance au bord de la mort.', 'pt': 'Renascimento no limite.', 'ru': 'Возрождение на грани.', 'ja': '死の際で再生する。'},
        'effect': {'zh': '+20H；致命伤害时，若在手牌，清除己方效果，生命设为5，本回合无敌并放逐', 'en': '+20H; in hand on lethal damage: clear effects, set H to 5, invincible this turn, exile', 'fr': '+20H; en main contre dégâts létaux: nettoie effets, H=5, invincible ce tour, exil', 'pt': '+20H; na mão contra dano letal: limpa efeitos, H=5, invencível neste turno, exila', 'ru': '+20H; в руке при смерт. уроне: очистка эффектов, H=5, неуязв. ход, изгнание', 'ja': '+20H。致命傷時、手札なら効果解除、H=5、このターン無敵、追放'},
    },
    'Leaf': {
        'name': {'zh': '叶子', 'en': 'Leaf', 'fr': 'Feuille', 'pt': 'Folha', 'ru': 'Лист', 'ja': '葉'},
        'desc': {'zh': '基础装备，可治疗也可触发伤害。', 'en': 'Basic equipment: heal or strike.', 'fr': 'Équipement de base: soigne ou frappe.', 'pt': 'Equipamento básico: cura ou golpeia.', 'ru': 'Базовое снаряжение: лечит или бьёт.', 'ja': '基本装備。回復か攻撃。'},
        'effect': {'zh': '友方回合开始+2H', 'en': '+2H at friendly turn start', 'fr': '+2H au début du tour allié', 'pt': '+2H no início do turno aliado', 'ru': '+2H в начале хода союзника', 'ja': '味方ターン開始時+2H'},
        'trigger': {'zh': '装备1回合后可摧毁：造成8D', 'en': 'After 1 turn, destroy: deal 8D', 'fr': 'Après 1 tour, détruire: 8D', 'pt': 'Após 1 turno, destruir: 8D', 'ru': 'После 1 хода уничтожить: 8D', 'ja': '1ターン後に破壊可：8D'},
    },
    'Yucca': {
        'name': {'zh': '丝兰', 'en': 'Yucca', 'fr': 'Yucca', 'pt': 'Yucca', 'ru': 'Юкка', 'ja': 'ユッカ'},
        'desc': {'zh': '更强的叶子。', 'en': 'A stronger leaf.', 'fr': 'Une feuille plus forte.', 'pt': 'Uma folha mais forte.', 'ru': 'Более сильный лист.', 'ja': 'より強い葉。'},
        'effect': {'zh': '友方回合开始+5H', 'en': '+5H at friendly turn start', 'fr': '+5H au début du tour allié', 'pt': '+5H no início do turno aliado', 'ru': '+5H в начале хода союзника', 'ja': '味方ターン開始時+5H'},
    },
    'Disc': {
        'name': {'zh': '圆盘', 'en': 'Disc', 'fr': 'Disque', 'pt': 'Disco', 'ru': 'Диск', 'ja': '円盤'},
        'desc': {'zh': '坚实的护盾。', 'en': 'A solid shield.', 'fr': 'Un bouclier solide.', 'pt': 'Um escudo sólido.', 'ru': 'Прочный щит.', 'ja': '堅い盾。'},
        'effect': {'zh': '+2A', 'en': '+2A', 'fr': '+2A', 'pt': '+2A', 'ru': '+2A', 'ja': '+2A'},
    },
    'Battery': {
        'name': {'zh': '电池', 'en': 'Battery', 'fr': 'Batterie', 'pt': 'Bateria', 'ru': 'Батарея', 'ja': '電池'},
        'desc': {'zh': '被攻击时会反伤。', 'en': 'Shocks back when hit.', 'fr': 'Riposte quand touchée.', 'pt': 'Revida ao ser atingida.', 'ru': 'Бьёт в ответ.', 'ja': '攻撃されると反撃。'},
        'effect': {'zh': '受到物理伤害时，对敌方造成3D', 'en': 'When taking physical damage, deal 3D to enemy', 'fr': 'Quand vous subissez des dégâts physiques, 3D à l’ennemi', 'pt': 'Ao sofrer dano físico, causa 3D ao inimigo', 'ru': 'При физ. уроне наносит врагу 3D', 'ja': '物理ダメージ時、敵に3D'},
    },
    'MagicLeaf': {
        'name': {'zh': '魔法叶', 'en': 'Magic Leaf', 'fr': 'Feuille magique', 'pt': 'Folha Mágica', 'ru': 'Маг. лист', 'ja': '魔法の葉'},
        'desc': {'zh': '用治疗换取魔力。', 'en': 'Turns growth into mana.', 'fr': 'Transforme la croissance en mana.', 'pt': 'Transforma crescimento em mana.', 'ru': 'Даёт ману ростом.', 'ja': '成長を魔力に変える。'},
        'effect': {'zh': '友方回合开始+1M', 'en': '+1M at friendly turn start', 'fr': '+1M au début du tour allié', 'pt': '+1M no início do turno aliado', 'ru': '+1M в начале хода союзника', 'ja': '味方ターン開始時+1M'},
    },
    'MagicYucca': {
        'name': {'zh': '魔法丝兰', 'en': 'Magic Yucca', 'fr': 'Yucca magique', 'pt': 'Yucca Mágica', 'ru': 'Маг. юкка', 'ja': '魔法ユッカ'},
        'desc': {'zh': '生成更多魔力。', 'en': 'Generates more mana.', 'fr': 'Génère plus de mana.', 'pt': 'Gera mais mana.', 'ru': 'Даёт больше маны.', 'ja': 'より多くの魔力を生む。'},
        'effect': {'zh': '友方回合开始+2M', 'en': '+2M at friendly turn start', 'fr': '+2M au début du tour allié', 'pt': '+2M no início do turno aliado', 'ru': '+2M в начале хода союзника', 'ja': '味方ターン開始時+2M'},
    },
    'MagicBattery': {
        'name': {'zh': '魔法电池', 'en': 'Magic Battery', 'fr': 'Batterie magique', 'pt': 'Bateria Mágica', 'ru': 'Маг. батарея', 'ja': '魔法電池'},
        'desc': {'zh': '受击时激发魔力。', 'en': 'Charges mana when hit.', 'fr': 'Charge du mana quand touchée.', 'pt': 'Carrega mana ao ser atingida.', 'ru': 'Заряжает ману при ударе.', 'ja': '被弾時に魔力を充電。'},
        'effect': {'zh': '受到物理伤害时+1M（每回合最多3M）', 'en': 'When taking physical damage, +1M (max 3M/turn)', 'fr': 'Dégâts physiques subis: +1M (max 3M/tour)', 'pt': 'Ao sofrer dano físico: +1M (máx. 3M/turno)', 'ru': 'При физ. уроне +1M (макс. 3M/ход)', 'ja': '物理ダメージ時+1M（各ターン最大3M）'},
    },
    'Powder': {
        'name': {'zh': '粉末', 'en': 'Powder', 'fr': 'Poudre', 'pt': 'Pó', 'ru': 'Порошок', 'ja': '粉末'},
        'desc': {'zh': '加快行动节奏。', 'en': 'Speeds up your tempo.', 'fr': 'Accélère votre rythme.', 'pt': 'Acelera seu ritmo.', 'ru': 'Ускоряет темп.', 'ja': '行動を早める。'},
        'effect': {'zh': '友方回合开始+2E', 'en': '+2E at friendly turn start', 'fr': '+2E au début du tour allié', 'pt': '+2E no início do turno aliado', 'ru': '+2E в начале хода союзника', 'ja': '味方ターン開始時+2E'},
    },
    'GoldenLeaf': {
        'name': {'zh': '黄金叶', 'en': 'Golden Leaf', 'fr': 'Feuille d’or', 'pt': 'Folha Dourada', 'ru': 'Золотой лист', 'ja': '黄金の葉'},
        'desc': {'zh': '带来额外抽牌机会。', 'en': 'Brings extra draws.', 'fr': 'Apporte des pioches bonus.', 'pt': 'Traz compras extras.', 'ru': 'Даёт добор карт.', 'ja': '追加ドローをもたらす。'},
        'effect': {'zh': '回合开始时多抽1张', 'en': 'Draw 1 more at turn start', 'fr': 'Piochez 1 de plus au début du tour', 'pt': 'Compre +1 no início do turno', 'ru': 'В начале хода доберите +1', 'ja': 'ターン開始時さらに1枚引く'},
    },
    'Pincer': {
        'name': {'zh': '螫针', 'en': 'Pincer', 'fr': 'Pince', 'pt': 'Pinça', 'ru': 'Клешня', 'ja': 'ハサミ'},
        'desc': {'zh': '毒素减缓对手行动。', 'en': 'Toxin slows the enemy.', 'fr': 'La toxine ralentit l’ennemi.', 'pt': 'A toxina atrasa o inimigo.', 'ru': 'Токсин замедляет врага.', 'ja': '毒で敵を鈍らせる。'},
        'effect': {'zh': '敌方回合开始时，E回复-1', 'en': 'Enemy E recovery -1 at turn start', 'fr': 'Récupération E ennemie -1 au début du tour', 'pt': 'Recuperação E inimiga -1 no início do turno', 'ru': 'В начале хода врага: восстановление E -1', 'ja': '敵ターン開始時、E回復-1'},
    },
    'Cancer': {
        'name': {'zh': '癌细胞', 'en': 'Cancer Cell', 'fr': 'Cellule cancéreuse', 'pt': 'Célula cancerosa', 'ru': 'Раковая клетка', 'ja': 'がん細胞'},
        'desc': {'zh': '难以根除的恶性细胞。', 'en': 'A malignant cell hard to remove.', 'fr': 'Une cellule maligne tenace.', 'pt': 'Uma célula maligna resistente.', 'ru': 'Злокачественная клетка.', 'ja': '除去困難な悪性細胞。'},
        'effect': {'zh': '对敌方施加1层淬毒', 'en': 'Apply 1 Toxic to enemy', 'fr': 'Applique 1 Toxique à l’ennemi', 'pt': 'Aplica 1 Tóxico ao inimigo', 'ru': 'Врагу +1 Токсин', 'ja': '敵に猛毒1を付与'},
    },
    'Corruption': {
        'name': {'zh': '腐化', 'en': 'Corruption', 'fr': 'Corruption', 'pt': 'Corrupção', 'ru': 'Порча', 'ja': '腐化'},
        'desc': {'zh': '伤敌一千，自损八百。', 'en': 'Power at a dangerous price.', 'fr': 'Puissance à prix élevé.', 'pt': 'Poder por preço alto.', 'ru': 'Сила дорогой ценой.', 'ja': '危険な代償の力。'},
        'effect': {'zh': '自下个敌方回合开始，全场伤害翻倍', 'en': 'From next enemy turn, all damage is doubled', 'fr': 'Dès le prochain tour ennemi, tous les dégâts doublent', 'pt': 'A partir do próximo turno inimigo, todo dano dobra', 'ru': 'Со след. хода врага весь урон ×2', 'ja': '次の敵ターンから全ダメージ2倍'},
    },
    'Mark': {
        'name': {'zh': '标记', 'en': 'Mark', 'fr': 'Marque', 'pt': 'Marca', 'ru': 'Метка', 'ja': 'マーク'},
        'desc': {'zh': '你被标记了。', 'en': 'You have been marked.', 'fr': 'Vous êtes marqué.', 'pt': 'Você foi marcado.', 'ru': 'Вы отмечены.', 'ja': '印を付けられた。'},
        'effect': {'zh': '禁止敌方行动1回合', 'en': 'Enemy cannot act for 1 turn', 'fr': 'L’ennemi ne peut pas agir 1 tour', 'pt': 'Inimigo não age por 1 turno', 'ru': 'Враг пропускает действия на 1 ход', 'ja': '敵は1ターン行動不可'},
        'trigger': {'zh': '装备1回合后可摧毁：敌方下回合不能行动', 'en': 'After 1 turn, destroy: enemy cannot act next turn', 'fr': 'Après 1 tour, détruire: ennemi inactif au prochain tour', 'pt': 'Após 1 turno, destruir: inimigo não age no próximo turno', 'ru': 'После 1 хода уничтожить: враг не действует след. ход', 'ja': '1ターン後に破壊可：次の敵ターン行動不可'},
    },
    'Mine': {
        'name': {'zh': '地雷', 'en': 'Mine', 'fr': 'Mine', 'pt': 'Mina', 'ru': 'Мина', 'ja': '地雷'},
        'desc': {'zh': '危险，但需要准备。', 'en': 'Dangerous, but needs setup.', 'fr': 'Dangereuse, mais lente.', 'pt': 'Perigosa, mas precisa preparo.', 'ru': 'Опасна, но требует подготовки.', 'ja': '危険だが準備が必要。'},
        'effect': {'zh': '下回合造成20D', 'en': 'Deal 20D next turn', 'fr': 'Inflige 20D au prochain tour', 'pt': 'Causa 20D no próximo turno', 'ru': '20D на следующем ходу', 'ja': '次ターン20D'},
        'trigger': {'zh': '装备1回合后可摧毁：造成20D', 'en': 'After 1 turn, destroy: deal 20D', 'fr': 'Après 1 tour, détruire: 20D', 'pt': 'Após 1 turno, destruir: 20D', 'ru': 'После 1 хода уничтожить: 20D', 'ja': '1ターン後に破壊可：20D'},
    },
    'Bubble': {
        'name': {'zh': '泡泡', 'en': 'Bubble', 'fr': 'Bulle', 'pt': 'Bolha', 'ru': 'Пузырь', 'ja': '泡'},
        'desc': {'zh': '闪！', 'en': 'Dodge!', 'fr': 'Esquive !', 'pt': 'Desvie!', 'ru': 'Уклонение!', 'ja': '回避！'},
        'effect': {'zh': '获得1层闪避（敌方使用Thorn时）', 'en': 'Gain 1 Dodge (when enemy uses Thorn)', 'fr': 'Gagne 1 Esquive (quand l’ennemi joue Thorn)', 'pt': 'Ganha 1 Esquiva (quando inimigo usa Thorn)', 'ru': '+1 Уклонение (когда враг играет Thorn)', 'ja': '回避1を得る（敵がThorn使用時）'},
    },
    'Nazar': {
        'name': {'zh': '邪眼护符', 'en': 'Nazar', 'fr': 'Nazar', 'pt': 'Nazar', 'ru': 'Назар', 'ja': 'ナザール'},
        'desc': {'zh': '大幅减免物理伤害。', 'en': 'Greatly reduces physical damage.', 'fr': 'Réduit fortement les dégâts physiques.', 'pt': 'Reduz muito dano físico.', 'ru': 'Сильно снижает физ. урон.', 'ja': '物理ダメージを大きく軽減。'},
        'effect': {'zh': '物理伤害减免（最低到1）；承受两次10点以上物理伤害后消失（敌方使用Thorn时）', 'en': 'Reduce physical damage (min 1); expires after two 10+ physical hits (when enemy uses Thorn)', 'fr': 'Réduit dégâts physiques (min 1); expire après deux coups physiques 10+ (ennemi joue Thorn)', 'pt': 'Reduz dano físico (mín. 1); expira após dois golpes físicos 10+ (inimigo usa Thorn)', 'ru': 'Снижает физ. урон (мин. 1); исчезает после двух ударов 10+ (враг играет Thorn)', 'ja': '物理ダメージ軽減（最小1）。10以上の物理を2回受けると消滅（敵がThorn使用時）'},
    },
    'MagicNazar': {
        'name': {'zh': '魔法邪眼', 'en': 'Magic Nazar', 'fr': 'Nazar magique', 'pt': 'Nazar Mágico', 'ru': 'Маг. назар', 'ja': '魔法ナザール'},
        'desc': {'zh': '保护你的装备。', 'en': 'Protects your equipment.', 'fr': 'Protège votre équipement.', 'pt': 'Protege seu equipamento.', 'ru': 'Защищает снаряжение.', 'ja': '装備を守る。'},
        'effect': {'zh': '获得1层装备保护（敌方摧毁装备时）', 'en': 'Gain 1 Equip Protect (when enemy destroys equipment)', 'fr': 'Gagne 1 Protection d’équipement (destruction ennemie)', 'pt': 'Ganha 1 Proteção de Equip. (destruição inimiga)', 'ru': '+1 Защита снаряжения (при уничтожении врагом)', 'ja': '装備保護1を得る（敵が装備破壊時）'},
    },
    'MagicBubble': {
        'name': {'zh': '魔法泡泡', 'en': 'Magic Bubble', 'fr': 'Bulle magique', 'pt': 'Bolha Mágica', 'ru': 'Маг. пузырь', 'ja': '魔法の泡'},
        'desc': {'zh': '泡泡的魔法版本。', 'en': 'A magical bubble.', 'fr': 'Une bulle magique.', 'pt': 'Uma bolha mágica.', 'ru': 'Магический пузырь.', 'ja': '魔法の泡。'},
        'effect': {'zh': '使敌方技能牌失效（敌方使用Bloom时）', 'en': 'Negate enemy Bloom (when enemy uses Bloom)', 'fr': 'Annule le Bloom ennemi (quand l’ennemi joue Bloom)', 'pt': 'Anula Bloom inimigo (quando inimigo usa Bloom)', 'ru': 'Отменяет Bloom врага (когда враг играет Bloom)', 'ja': '敵のBloomを無効化（敵がBloom使用時）'},
    },
}


OPENING_EVENT_I18N = {
    1: {'name': {'zh': '生命强化', 'en': 'Vital Growth', 'fr': 'Croissance vitale', 'pt': 'Crescimento Vital', 'ru': 'Рост жизни', 'ja': '生命強化'}, 'desc': {'zh': '最大生命值+20', 'en': 'Max health +20', 'fr': 'Santé max +20', 'pt': 'Vida máxima +20', 'ru': 'Макс. здоровье +20', 'ja': '最大H+20'}},
    2: {'name': {'zh': '魔力转化', 'en': 'Mana Conversion', 'fr': 'Conversion de mana', 'pt': 'Conversão de Mana', 'ru': 'Преобразование маны', 'ja': '魔力変換'}, 'desc': {'zh': '选择1-3张牌转化为魔法牌，开局+5M', 'en': 'Convert 1-3 cards into magic cards; start with +5M', 'fr': 'Convertit 1-3 cartes en cartes magiques; départ +5M', 'pt': 'Converte 1-3 cartas em mágicas; início +5M', 'ru': 'Преобразуйте 1-3 карты в магические; старт +5M', 'ja': '1-3枚を魔法カードに変換。開始時+5M'}},
    3: {'name': {'zh': '光之洗礼', 'en': 'Baptism of Light', 'fr': 'Baptême de lumière', 'pt': 'Batismo de Luz', 'ru': 'Крещение светом', 'ja': '光の洗礼'}, 'desc': {'zh': '最多五张牌变为Light（萌芽、共生）', 'en': 'Up to 5 cards become Light (Sprout, Symbiosis)', 'fr': 'Jusqu’à 5 cartes deviennent Light (Germe, Symbiose)', 'pt': 'Até 5 cartas viram Light (Broto, Simbiose)', 'ru': 'До 5 карт становятся Light (Росток, Симбиоз)', 'ja': '最大5枚をLightに変換（萌芽、共生）'}},
    4: {'name': {'zh': '烈焰预兆', 'en': 'Flame Omen', 'fr': 'Présage de flammes', 'pt': 'Presságio Flamejante', 'ru': 'Огненное знамение', 'ja': '炎の兆し'}, 'desc': {'zh': '开局对敌方施加3层灼烧', 'en': 'Apply 3 Burn to enemy at start', 'fr': 'Applique 3 Brûlure à l’ennemi au départ', 'pt': 'Aplica 3 Queima ao inimigo no início', 'ru': 'В начале врагу +3 Горение', 'ja': '開始時、敵に火傷3'}},
    5: {'name': {'zh': '命运抽签', 'en': 'Fated Draw', 'fr': 'Pioche du destin', 'pt': 'Compra do Destino', 'ru': 'Жребий судьбы', 'ja': '運命のドロー'}, 'desc': {'zh': '前二回合开始时抽牌至手牌已满', 'en': 'At the first two turn starts, draw until hand is full', 'fr': 'Aux deux premiers débuts de tour, pioche jusqu’à main pleine', 'pt': 'Nos 2 primeiros turnos, compre até encher a mão', 'ru': 'Первые 2 хода: добор до полной руки', 'ja': '最初の2ターン開始時、手札上限まで引く'}},
    6: {'name': {'zh': '能量涌动', 'en': 'Energy Surge', 'fr': 'Poussée d’énergie', 'pt': 'Surto de Energia', 'ru': 'Всплеск энергии', 'ja': 'エネルギー奔流'}, 'desc': {'zh': '前三回合开始时额外回复2E', 'en': 'At the first three turn starts, recover +2E', 'fr': 'Aux trois premiers débuts de tour, récupère +2E', 'pt': 'Nos 3 primeiros turnos, recupere +2E', 'ru': 'Первые 3 хода: восстановить +2E', 'ja': '最初の3ターン開始時、追加+2E'}},
    7: {'name': {'zh': '先手压制', 'en': 'Opening Pressure', 'fr': 'Pression initiale', 'pt': 'Pressão Inicial', 'ru': 'Начальный нажим', 'ja': '先手圧力'}, 'desc': {'zh': '必定先手，先手多回复3E并抽4张牌', 'en': 'You go first; first player recovers +3E and draws 4', 'fr': 'Vous commencez; le premier joueur récupère +3E et pioche 4', 'pt': 'Você começa; primeiro jogador recupera +3E e compra 4', 'ru': 'Вы ходите первым; первый игрок +3E и 4 карты', 'ja': '必ず先手。先手は+3Eし4枚引く'}},
    8: {'name': {'zh': '绝境求生', 'en': 'Last Stand', 'fr': 'Dernier recours', 'pt': 'Último Recurso', 'ru': 'Последний шанс', 'ja': '背水の生存'}, 'desc': {'zh': '最大生命值-20，将一张牌变为世界树之叶', 'en': 'Max health -20; turn one card into Yggdrasil', 'fr': 'Santé max -20; une carte devient Yggdrasil', 'pt': 'Vida máxima -20; uma carta vira Yggdrasil', 'ru': 'Макс. здоровье -20; 1 карта становится Yggdrasil', 'ja': '最大H-20。1枚をYggdrasilに変換'}},
}


def _fill(field):
    zh = field.get('zh') or field.get('en') or ''
    en = field.get('en') or zh
    return {lang: field.get(lang) or en for lang in LANGS}


def card_text(card_id, fallback):
    data = CARD_I18N.get(card_id)
    if not data:
        return fallback
    return {
        'name_i18n': _fill(data.get('name', {})),
        'description_i18n': _fill(data.get('desc', {})),
        'effect_text_i18n': _fill(data.get('effect', {})),
        'trigger_effect_text_i18n': _fill(data.get('trigger', {'zh': fallback.get('trigger_effect_text', ''), 'en': fallback.get('trigger_effect_text', '')})),
    }


def event_text(event_id, fallback):
    data = OPENING_EVENT_I18N.get(event_id)
    if not data:
        return fallback
    out = dict(fallback)
    out['name_i18n'] = _fill(data.get('name', {}))
    out['desc_i18n'] = _fill(data.get('desc', {}))
    out['name'] = out['name_i18n']['zh']
    out['desc'] = out['desc_i18n']['zh']
    return out


def apply_card_i18n_defaults(card_defs):
    for card_id, text in CARD_I18N.items():
        card = card_defs.get(card_id)
        if not card:
            continue
        name = _fill(text.get('name', {}))
        desc = _fill(text.get('desc', {}))
        effect = _fill(text.get('effect', {}))
        trigger = _fill(text.get('trigger', {}))
        card.name_cn = name['zh']
        card.name_en = name['en']
        card.description = desc['zh']
        card.effect_text = effect['zh']
        if trigger.get('zh'):
            card.trigger_effect_text = trigger['zh']
