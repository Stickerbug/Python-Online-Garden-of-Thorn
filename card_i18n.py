import re


LANGS = ('zh', 'en', 'fr', 'pt', 'ru', 'ja')


def card_id_to_english(card_id):
    text = str(card_id or '').replace('_', ' ').replace('-', ' ')
    text = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', text)
    text = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _t(zh, en, fr, pt, ru, ja):
    return {'zh': zh, 'en': en, 'fr': fr, 'pt': pt, 'ru': ru, 'ja': ja}


CARD_I18N = {
    'Basic': {
        'name': _t('基本', 'Basic', 'Base', 'Básico', 'База', '基本'),
        'desc': _t('最基本的卡牌。', 'The most basic card.', 'La carte la plus basique.', 'A carta mais básica.', 'Самая базовая карта.', '最も基本的なカード。'),
        'effect': _t('造成6D', 'Deal 6D', 'Inflige 6D', 'Causa 6D', 'Наносит 6D', '6Dを与える'),
    },
    'Bone': {
        'name': _t('骨头', 'Bone', 'Os', 'Osso', 'Кость', '骨'),
        'desc': _t('坚固且好用。', 'Solid and easy to use.', 'Solide et pratique.', 'Firme e fácil de usar.', 'Прочная и удобная.', '丈夫で扱いやすい。'),
        'effect': _t('造成12D', 'Deal 12D', 'Inflige 12D', 'Causa 12D', 'Наносит 12D', '12Dを与える'),
    },
    'Stinger': {
        'name': _t('刺', 'Stinger', 'Dard', 'Ferrão', 'Жало', '針'),
        'desc': _t('一击造成大量伤害。它真的很尖锐。', 'A single strike that deals heavy damage. It is very sharp.', 'Un seul coup inflige de lourds dégâts. Il est vraiment acéré.', 'Um golpe único causa muito dano. É muito afiado.', 'Один удар наносит большой урон. Оно очень острое.', '一撃で大ダメージを与える。本当に鋭い。'),
        'effect': _t('造成20D', 'Deal 20D', 'Inflige 20D', 'Causa 20D', 'Наносит 20D', '20Dを与える'),
    },
    'Fission': {
        'name': _t('裂变', 'Fission', 'Fission', 'Fissão', 'Деление', '分裂'),
        'desc': _t('将一次攻击分裂为多次。', 'Split one attack into multiple hits.', 'Divise une attaque en plusieurs coups.', 'Divide um ataque em vários golpes.', 'Делит одну атаку на несколько ударов.', '1回の攻撃を複数回に分裂させる。'),
        'effect': _t('选择一张手中的攻击牌，将其裂变层数增加2', 'Choose one attack card in hand; increase its Fission by 2', 'Choisissez une carte d’attaque en main ; augmentez sa Fission de 2', 'Escolha uma carta de ataque na mão; aumente a Fissão dela em 2', 'Выберите карту атаки в руке; увеличьте её Деление на 2', '手札の攻撃カード1枚を選び、分裂を2増やす'),
    },
    'Fusion': {
        'name': _t('聚变', 'Fusion', 'Fusion', 'Fusão', 'Слияние', '融合'),
        'desc': _t('将相同的攻击聚合为一击。', 'Fuse identical attacks into one strike.', 'Fusionne des attaques identiques en une frappe.', 'Funde ataques iguais em um golpe.', 'Сливает одинаковые атаки в один удар.', '同じ攻撃を一撃へ融合する。'),
        'effect': _t('选择手中2-3张同名攻击牌，将它们的聚变层数相加，裂变层数取最大值，变为一张牌', 'Choose 2-3 same-name attack cards in hand; add their Fusion, keep the highest Fission, and turn them into one card', 'Choisissez 2-3 cartes d’attaque du même nom en main ; additionnez leur Fusion, gardez la Fission la plus élevée, et transformez-les en une carte', 'Escolha 2-3 cartas de ataque com o mesmo nome na mão; some a Fusão, mantenha a maior Fissão e transforme-as em uma carta', 'Выберите 2-3 одноимённые карты атаки в руке; сложите их Слияние, оставьте наибольшее Деление и превратите их в одну карту', '手札の同名攻撃カード2-3枚を選び、融合を合計し、分裂は最大値を取り、1枚のカードにする'),
    },
    'Sand': {
        'name': _t('沙子', 'Sand', 'Sable', 'Areia', 'Песок', '砂'),
        'desc': _t('因为是一把，所以可以造成多次伤害。', 'A handful of sand, so it can deal damage multiple times.', 'Comme c’est une poignée, elle peut infliger plusieurs dégâts.', 'Por ser um punhado, pode causar dano várias vezes.', 'Это горсть песка, поэтому урон наносится несколько раз.', 'ひとつかみなので複数回ダメージを与えられる。'),
        'effect': _t('造成3D×4（4子瓣）', 'Deal 3D×4 (4 petals)', 'Inflige 3D×4 (4 pétales)', 'Causa 3D×4 (4 pétalas)', 'Наносит 3D×4 (4 лепестка)', '3D×4（4子弁）を与える'),
    },
    'Wing': {
        'name': _t('翅膀', 'Wing', 'Aile', 'Asa', 'Крыло', '翼'),
        'desc': _t('回旋的翅膀连续两次打击对手。', 'A spinning wing strikes the opponent twice in succession.', 'Une aile tournoyante frappe deux fois de suite.', 'Uma asa giratória atinge o oponente duas vezes seguidas.', 'Вращающееся крыло дважды подряд бьёт противника.', '旋回する翼が相手を2回連続で打つ。'),
        'effect': _t('造成8D×2（2子瓣）', 'Deal 8D×2 (2 petals)', 'Inflige 8D×2 (2 pétales)', 'Causa 8D×2 (2 pétalas)', 'Наносит 8D×2 (2 лепестка)', '8D×2（2子弁）を与える'),
    },
    'Light': {
        'name': _t('轻', 'Light', 'Léger', 'Leve', 'Лёгкость', '軽'),
        'desc': _t('轻如鸿毛，却能伤人两次。太轻了所以不需要消耗能量。', 'As light as a feather, yet it can hurt twice. It is so light that it costs no energy.', 'Léger comme une plume, mais capable de blesser deux fois. Si léger qu’il ne coûte aucune énergie.', 'Leve como uma pluma, mas fere duas vezes. É tão leve que não custa energia.', 'Лёгкая как перо, но ранит дважды. Настолько лёгкая, что не требует энергии.', '羽のように軽いが、2回傷つけられる。軽すぎるのでエネルギーを消費しない。'),
        'effect': _t('造成2D×2（2子瓣）', 'Deal 2D×2 (2 petals)', 'Inflige 2D×2 (2 pétales)', 'Causa 2D×2 (2 pétalas)', 'Наносит 2D×2 (2 лепестка)', '2D×2（2子弁）を与える'),
    },
    'Fang': {
        'name': _t('尖牙', 'Fang', 'Croc', 'Presa', 'Клык', '牙'),
        'desc': _t('吸取对手的生命来为你回复。', 'Drain the opponent’s life to heal yourself.', 'Draine la vie de l’adversaire pour vous soigner.', 'Drena a vida do oponente para curar você.', 'Высасывает жизнь противника, исцеляя вас.', '相手の生命を吸い取り、自分を回復する。'),
        'effect': _t('造成8D; 造成伤害时+4H', 'Deal 8D; if damage is dealt, +4H', 'Inflige 8D ; si des dégâts sont infligés, +4H', 'Causa 8D; se causar dano, +4H', 'Наносит 8D; если урон нанесён, +4H', '8Dを与える。ダメージを与えた時+4H'),
    },
    'Iris': {
        'name': _t('鸢尾', 'Iris', 'Iris', 'Íris', 'Ирис', 'アイリス'),
        'desc': _t('美丽而致命。', 'Beautiful and deadly.', 'Belle et mortelle.', 'Bela e mortal.', 'Красива и смертельна.', '美しく致命的。'),
        'effect': _t('施加10层P', 'Apply 10 Poison', 'Applique 10 Poison', 'Aplica 10 Veneno', 'Накладывает 10 Яда', '毒10を付与'),
    },
    'Fire': {
        'name': _t('火', 'Fire', 'Feu', 'Fogo', 'Огонь', '火'),
        'desc': _t('缓慢但持久地灼烧对手。', 'Slowly but persistently burns the opponent.', 'Brûle lentement mais durablement l’adversaire.', 'Queima o oponente lenta e persistentemente.', 'Медленно, но долго обжигает противника.', 'ゆっくりだが長く相手を焼く。'),
        'effect': _t('造成2层F', 'Apply 2 Burn', 'Applique 2 Brûlure', 'Aplica 2 Queima', 'Накладывает 2 Горения', '灼焼2を付与'),
    },
    'Triangle': {
        'name': _t('三角形', 'Triangle', 'Triangle', 'Triângulo', 'Треугольник', '三角形'),
        'desc': _t('量变引起质变。', 'Quantitative change leads to qualitative change.', 'Le changement quantitatif mène au changement qualitatif.', 'Mudança quantitativa leva a mudança qualitativa.', 'Количество переходит в качество.', '量の変化が質の変化を生む。'),
        'effect': _t('造成(6+3×三角形层数)D；造成伤害时获得一层三角形，上限4层', 'Deal (6+3×Triangle stacks)D; when damage is dealt, gain 1 Triangle stack, up to 4', 'Inflige (6+3×charges de Triangle)D ; si des dégâts sont infligés, gagne 1 charge de Triangle, max 4', 'Causa (6+3×camadas de Triângulo)D; ao causar dano, ganha 1 camada de Triângulo, máximo 4', 'Наносит (6+3×слои Треугольника)D; при нанесении урона получает 1 слой Треугольника, максимум 4', '(6+3×三角形層数)Dを与える。ダメージを与えた時、三角形を1層得る。上限4層'),
    },
    'Fries': {
        'name': _t('薯条', 'Fries', 'Frites', 'Batatas fritas', 'Картофель фри', 'フライドポテト'),
        'desc': _t('高热量食品，补充大量生命。隐隐约约地写着“M”？', 'High-calorie food that restores a lot of health. Is there a faint “M” on it?', 'Un aliment très calorique qui restaure beaucoup de vie. Un “M” y est-il vaguement inscrit ?', 'Comida altamente calórica que restaura muita vida. Há um “M” meio apagado?', 'Калорийная еда, восстанавливающая много здоровья. Кажется, там написано «M»?', '高カロリー食品で大量に生命を回復する。うっすら“M”と書いてある？'),
        'effect': _t('+12H', '+12H', '+12H', '+12H', '+12H', '+12H'),
    },
    'Rose': {
        'name': _t('玫瑰', 'Rose', 'Rose', 'Rosa', 'Роза', 'バラ'),
        'desc': _t('这花香可以为你回复生命。', 'Its fragrance can restore your health.', 'Son parfum peut restaurer votre vie.', 'Seu aroma pode restaurar sua vida.', 'Её аромат восстанавливает здоровье.', 'その香りが生命を回復する。'),
        'effect': _t('+7H', '+7H', '+7H', '+7H', '+7H', '+7H'),
    },
    'Leaf': {
        'name': _t('叶子', 'Leaf', 'Feuille', 'Folha', 'Лист', '葉'),
        'desc': _t('基础的装备之一，可以回复生命亦可造成伤害。', 'One of the basic equipments; it can restore health and also deal damage.', 'Un équipement de base ; il peut restaurer de la vie et infliger des dégâts.', 'Um equipamento básico; pode restaurar vida e também causar dano.', 'Базовое снаряжение: лечит и может наносить урон.', '基本装備のひとつ。生命を回復し、ダメージも与えられる。'),
        'effect': _t('自己回合开始时+2H 触发：1E，若已装备一回合则可摧毁此装备，造成8D', 'At your turn start +2H. Trigger: 1E; if equipped for one turn, you may destroy this equipment to deal 8D', 'Au début de votre tour +2H. Déclenchement : 1E ; si équipé depuis un tour, vous pouvez détruire cet équipement pour infliger 8D', 'No início do seu turno +2H. Acionar: 1E; se equipado por um turno, você pode destruir este equipamento para causar 8D', 'В начале вашего хода +2H. Активация: 1E; если снаряжено один ход, можно уничтожить это снаряжение и нанести 8D', '自分のターン開始時+2H。発動：1E。1ターン装備済みならこの装備を破壊して8Dを与えられる'),
        'trigger': _t('若已装备一回合则可摧毁此装备，造成8D', 'If equipped for one turn, you may destroy this equipment to deal 8D', 'Si équipé depuis un tour, vous pouvez détruire cet équipement pour infliger 8D', 'Se equipado por um turno, você pode destruir este equipamento para causar 8D', 'Если снаряжено один ход, можно уничтожить это снаряжение и нанести 8D', '1ターン装備済みならこの装備を破壊して8Dを与えられる'),
    },
    'Yucca': {
        'name': _t('丝兰', 'Yucca', 'Yucca', 'Yucca', 'Юкка', 'ユッカ'),
        'desc': _t('在平缓的回合后积蓄更多生机。', 'Stores extra vitality after a low-impact turn.', 'Accumule plus de vitalité après un tour peu offensif.', 'Acumula vitalidade extra após um turno de baixo impacto.', 'Накапливает больше жизненной силы после спокойного хода.', '穏やかなターンの後、さらに生命力を蓄える。'),
        'effect': _t('自己回合开始时+3H；若上个自己的回合造成的实际伤害低于10D，则额外+7H', 'At your turn start +3H; if your last turn dealt less than 10D actual damage, +7H more', 'Au début de votre tour +3H ; si votre tour précédent a infligé moins de 10D réels, +7H en plus', 'No início do seu turno +3H; se seu turno anterior causou menos de 10D reais, +7H extra', 'В начале вашего хода +3H; если в прошлый ваш ход было нанесено меньше 10D фактического урона, дополнительно +7H', '自分のターン開始時+3H。前の自分のターンで実際に与えたダメージが10D未満なら、追加で+7H'),
    },
    'Disc': {
        'name': _t('圆盘', 'Disc', 'Disque', 'Disco', 'Диск', '円盤'),
        'desc': _t('坚实的护盾，减免来袭的伤害。', 'A solid shield that reduces incoming damage.', 'Un bouclier solide qui réduit les dégâts reçus.', 'Um escudo sólido que reduz dano recebido.', 'Прочный щит, уменьшающий входящий урон.', '堅固な盾。受けるダメージを軽減する。'),
        'effect': _t('+2A', '+2A', '+2A', '+2A', '+2A', '+2A'),
    },
    'Battery': {
        'name': _t('电池', 'Battery', 'Batterie', 'Bateria', 'Батарея', '電池'),
        'desc': _t('受击时会漏电。', 'Leaks electricity when hit.', 'Fuit de l’électricité lorsqu’elle est touchée.', 'Vaza eletricidade quando atingida.', 'При ударе даёт утечку тока.', '攻撃されると漏電する。'),
        'effect': _t('受到物理伤害时，对攻击者造成3电伤', 'When taking physical damage, deal 3 electric damage to the attacker', 'Quand vous subissez des dégâts physiques, inflige 3 dégâts électriques à l’attaquant', 'Ao sofrer dano físico, causa 3 de dano elétrico ao atacante', 'При получении физического урона наносит атакующему 3 электрического урона', '物理ダメージを受けた時、攻撃者に3電撃ダメージを与える'),
    },
    'Bubble': {
        'name': _t('泡泡', 'Bubble', 'Bulle', 'Bolha', 'Пузырь', '泡'),
        'desc': _t('闪！', 'Dodge!', 'Esquive !', 'Desvie!', 'Уклонение!', '回避！'),
        'effect': _t('获得一层闪避 响应：敌方使用攻击牌', 'Gain 1 Dodge. Response: enemy uses an attack card', 'Gagne 1 Esquive. Réponse : l’ennemi joue une carte d’attaque', 'Ganha 1 Esquiva. Resposta: inimigo usa uma carta de ataque', 'Получить 1 Уклонение. Ответ: враг использует карту атаки', '回避を1層得る。反応：敵が攻撃カードを使用'),
    },
    'Nazar': {
        'name': _t('邪眼护符', 'Nazar', 'Nazar', 'Nazar', 'Назар', 'ナザール'),
        'desc': _t('邪眼的力量似乎为你减免了大部分伤害。', 'The power of the evil eye seems to reduce most of the damage for you.', 'Le pouvoir du mauvais œil semble réduire la majeure partie des dégâts.', 'O poder do mau-olhado parece reduzir a maior parte do dano.', 'Сила сглаза, кажется, снижает большую часть урона.', '邪眼の力が大半のダメージを軽減してくれるようだ。'),
        'effect': _t('所有物理伤害减少9(最少减至1)，受到两次10点及以上物理伤害后效果消失 响应：敌方使用攻击牌', 'Reduce all physical damage by 9 (minimum 1); expires after taking two physical hits of 10 or more. Response: enemy uses an attack card', 'Réduit tous les dégâts physiques de 9 (minimum 1) ; expire après avoir subi deux coups physiques de 10 ou plus. Réponse : l’ennemi joue une carte d’attaque', 'Reduz todo dano físico em 9 (mínimo 1); expira após sofrer dois golpes físicos de 10 ou mais. Resposta: inimigo usa uma carta de ataque', 'Уменьшает весь физический урон на 9 (минимум до 1); исчезает после двух физических ударов по 10 или больше. Ответ: враг использует карту атаки', '全ての物理ダメージを9減らす（最低1）。10以上の物理ダメージを2回受けると効果消失。反応：敵が攻撃カードを使用'),
    },
    'MagicLeaf': {
        'name': _t('魔法叶', 'Magic Leaf', 'Feuille magique', 'Folha Mágica', 'Магический лист', '魔法の葉'),
        'desc': _t('不再能造成伤害了，但它可以回复魔力。', 'It can no longer deal damage, but it can restore magic.', 'Elle ne peut plus infliger de dégâts, mais elle peut restaurer de la magie.', 'Não causa mais dano, mas pode restaurar magia.', 'Больше не наносит урон, но восстанавливает магию.', 'もうダメージは与えられないが、魔力を回復できる。'),
        'effect': _t('自己回合开始时+1M', 'At your turn start +1M', 'Au début de votre tour +1M', 'No início do seu turno +1M', 'В начале вашего хода +1M', '自分のターン開始時+1M'),
    },
    'ManaOrb': {
        'name': _t('魔法球', 'Mana Orb', 'Orbe de mana', 'Orbe de Mana', 'Сфера маны', 'マナオーブ'),
        'desc': _t('孕育魔力的小球。', 'A small orb that nurtures magic.', 'Un petit orbe qui nourrit la magie.', 'Uma pequena esfera que nutre magia.', 'Малый шар, питающий магию.', '魔力を宿す小さな球。'),
        'effect': _t('+3M', '+3M', '+3M', '+3M', '+3M', '+3M'),
    },
    'MagicYucca': {
        'name': _t('魔法丝兰', 'Magic Yucca', 'Yucca magique', 'Yucca Mágica', 'Магическая юкка', '魔法ユッカ'),
        'desc': _t('生成更多魔力。', 'Generates more magic.', 'Génère plus de magie.', 'Gera mais magia.', 'Создаёт больше магии.', 'より多くの魔力を生む。'),
        'effect': _t('自己回合开始时+2M', 'At your turn start +2M', 'Au début de votre tour +2M', 'No início do seu turno +2M', 'В начале вашего хода +2M', '自分のターン開始時+2M'),
    },
    'MagicBattery': {
        'name': _t('魔法电池', 'Magic Battery', 'Batterie magique', 'Bateria Mágica', 'Магическая батарея', '魔法電池'),
        'desc': _t('每次受击都会激发魔力涌动。', 'Each hit triggers a surge of magic.', 'Chaque coup déclenche un afflux de magie.', 'Cada golpe desperta uma onda de magia.', 'Каждый удар вызывает всплеск магии.', '攻撃を受けるたび魔力の高まりを引き起こす。'),
        'effect': _t('装备后，受到物理伤害时+1M(每回合上限3M)', 'After equipped, when taking physical damage, +1M (max 3M each turn)', 'Une fois équipée, quand vous subissez des dégâts physiques, +1M (max 3M par tour)', 'Depois de equipada, ao sofrer dano físico, +1M (máx. 3M por turno)', 'После снаряжения при получении физического урона +1M (макс. 3M за ход)', '装備後、物理ダメージを受けた時+1M（各ターン上限3M）'),
    },
    'MagicNazar': {
        'name': _t('魔法邪眼', 'Magic Nazar', 'Nazar magique', 'Nazar Mágico', 'Магический назар', '魔法ナザール'),
        'desc': _t('有魔力的护符，保护你的装备不被摧毁。', 'A magical amulet that protects your equipment from destruction.', 'Une amulette magique qui protège votre équipement de la destruction.', 'Um amuleto mágico que protege seu equipamento da destruição.', 'Магический амулет, защищающий снаряжение от уничтожения.', '魔力を持つ護符。装備が破壊されるのを防ぐ。'),
        'effect': _t('获得一层装备保护 响应：自己的装备即将被摧毁', 'Gain 1 Equip Protect. Response: your equipment is about to be destroyed', 'Gagne 1 Protection d’équipement. Réponse : votre équipement va être détruit', 'Ganha 1 Proteção de Equipamento. Resposta: seu equipamento está prestes a ser destruído', 'Получить 1 Защиту снаряжения. Ответ: ваше снаряжение вот-вот будет уничтожено', '装備保護を1層得る。反応：自分の装備が破壊されそうな時'),
    },
    'MagicBone': {
        'name': _t('魔法骨头', 'Magic Bone', 'Os magique', 'Osso Mágico', 'Магическая кость', '魔法の骨'),
        'desc': _t('魔力凝聚的骨头，穿透力更强。', 'A bone condensed from magic, with stronger penetration.', 'Un os condensé par la magie, plus pénétrant.', 'Um osso condensado por magia, com maior penetração.', 'Кость, сжатая магией, с большей пробивной силой.', '魔力で凝縮された骨。貫通力が高い。'),
        'effect': _t('造成15D', 'Deal 15D', 'Inflige 15D', 'Causa 15D', 'Наносит 15D', '15Dを与える'),
    },
    'MagicStinger': {
        'name': _t('魔法刺', 'Magic Stinger', 'Dard magique', 'Ferrão Mágico', 'Магическое жало', '魔法の針'),
        'desc': _t('魔力加持的尖刺，威力巨大。', 'A magic-empowered spike with tremendous force.', 'Une pointe renforcée par la magie, d’une grande puissance.', 'Um espinho fortalecido por magia, de enorme potência.', 'Шип, усиленный магией, с огромной мощью.', '魔力で強化された尖った針。威力は巨大。'),
        'effect': _t('造成30D', 'Deal 30D', 'Inflige 30D', 'Causa 30D', 'Наносит 30D', '30Dを与える'),
    },
    'Mimic': {
        'name': _t('拟态', 'Mimic', 'Mimique', 'Mímico', 'Мимикрия', '擬態'),
        'desc': _t('完美模仿。', 'A perfect imitation.', 'Une imitation parfaite.', 'Uma imitação perfeita.', 'Идеальная имитация.', '完全な模倣。'),
        'effect': _t('将一张手牌的复制加入手中，使其下一次打出时费用-1', 'Add a copy of one hand card to your hand; its next play costs -1', 'Ajoutez à votre main une copie d’une carte en main ; son prochain jeu coûte -1', 'Adicione à sua mão uma cópia de uma carta da mão; da próxima vez que for jogada, custa -1', 'Добавьте в руку копию одной карты из руки; её следующий розыгрыш стоит -1', '手札1枚のコピーを手札に加え、次に出す時のコストを-1する'),
    },
    'Coffee': {
        'name': _t('咖啡', 'Coffee', 'Café', 'Café', 'Кофе', 'コーヒー'),
        'desc': _t('可以用来提神，当然，小心耐药性。', 'It can wake you up. Of course, beware of tolerance.', 'Peut vous réveiller. Bien sûr, attention à la tolérance.', 'Pode despertar você. Claro, cuidado com a tolerância.', 'Бодрит. Но, конечно, остерегайтесь привыкания.', '眠気覚ましに使える。当然、耐性には注意。'),
        'effect': _t('+1E，第一次使用额外+1E', '+1E; first use grants an extra +1E', '+1E ; la première utilisation donne +1E supplémentaire', '+1E; o primeiro uso concede +1E extra', '+1E; первое использование даёт ещё +1E', '+1E。初回使用時さらに+1E'),
    },
    'Powder': {
        'name': _t('粉末', 'Powder', 'Poudre', 'Pó', 'Порошок', '粉末'),
        'desc': _t('使你加快速度的神秘粉末，不要去想它到底是什么。', 'A mysterious powder that speeds you up. Do not think too hard about what it is.', 'Une poudre mystérieuse qui vous accélère. Ne réfléchissez pas trop à ce que c’est.', 'Um pó misterioso que acelera você. Melhor não pensar demais no que ele é.', 'Таинственный порошок, ускоряющий вас. Лучше не думать, что это такое.', '速度を上げる謎の粉末。それが何なのかは考えない方がいい。'),
        'effect': _t('自己回合开始时+2E', 'At your turn start +2E', 'Au début de votre tour +2E', 'No início do seu turno +2E', 'В начале вашего хода +2E', '自分のターン開始時+2E'),
    },
    'GoldenLeaf': {
        'name': _t('黄金叶', 'Golden Leaf', 'Feuille d’or', 'Folha Dourada', 'Золотой лист', '黄金の葉'),
        'desc': _t('这闪亮的叶子能为你带来额外的抽牌机会。', 'This shining leaf brings you extra draw opportunities.', 'Cette feuille brillante vous offre des occasions de pioche supplémentaires.', 'Esta folha brilhante traz compras extras.', 'Этот сияющий лист даёт дополнительные возможности добора.', 'この輝く葉は追加のドロー機会をもたらす。'),
        'effect': _t('手牌爆牌上限+1；自己回合开始时多抽一张牌', 'Hand overflow limit +1; draw one extra card at your turn start', 'Limite de main +1 ; piochez une carte supplémentaire au début de votre tour', 'Limite de mão +1; compre uma carta extra no início do seu turno', 'Лимит переполнения руки +1; в начале вашего хода доберите одну карту', '手札上限+1。自分のターン開始時に追加で1枚引く'),
    },
    'Chromosome': {
        'name': _t('染色体', 'Chromosome', 'Chromosome', 'Cromossomo', 'Хромосома', '染色体'),
        'desc': _t('从基因中提取记忆，寻找所需之牌。', 'Extract memory from genes to find the card you need.', 'Extrait des souvenirs des gènes pour trouver la carte voulue.', 'Extrai memórias dos genes para encontrar a carta necessária.', 'Извлекает память из генов, чтобы найти нужную карту.', '遺伝子から記憶を取り出し、必要なカードを探す。'),
        'effect': _t('从牌堆中选择一张牌将其加入手中', 'Choose one card from the deck and add it to your hand', 'Choisissez une carte du deck et ajoutez-la à votre main', 'Escolha uma carta do deck e adicione-a à mão', 'Выберите карту из колоды и добавьте её в руку', '山札からカード1枚を選び、手札に加える'),
    },
    'Sewage': {
        'name': _t('污水', 'Sewage', 'Eaux usées', 'Esgoto', 'Стоки', '汚水'),
        'desc': _t('腐蚀一切装备。', 'Corrodes all equipment.', 'Corrode tout équipement.', 'Corrói todo equipamento.', 'Разъедает любое снаряжение.', 'あらゆる装備を腐食させる。'),
        'effect': _t('摧毁目标一张装备', 'Destroy one target equipment', 'Détruit un équipement de la cible', 'Destrói um equipamento do alvo', 'Уничтожить одно снаряжение цели', '対象の装備1つを破壊する'),
    },
    'Pincer': {
        'name': _t('螫针', 'Pincer', 'Pince', 'Pinça', 'Клешня', '毒針'),
        'desc': _t('毒素可以减缓对手行动，但小心别划伤自己。', 'Toxin can slow the opponent, but be careful not to scratch yourself.', 'La toxine peut ralentir l\'adversaire, mais attention à ne pas vous égratigner.', 'A toxina pode atrasar o oponente, mas cuidado para não se arranhar.', 'Токсин замедляет противника, но не поцарапайтесь сами.', '毒素は相手の行動を遅らせるが、自分を傷つけないよう注意。'),
        'effect': _t('装备时，每回合对目标施加1层超载', 'When equipped, apply 1 Overload to the target each turn', 'Quand équipé, applique 1 Surcharge à la cible chaque tour', 'Quando equipado, aplica 1 Sobrecarga ao alvo a cada turno', 'При снаряжении накладывает на цель 1 Перегрузку каждый ход', '装備時、毎ターン対象に過負荷1を付与'),
    },
    'Cancer': {
        'name': _t('癌细胞', 'Cancer', 'Cellule cancéreuse', 'Célula cancerosa', 'Раковая клетка', 'がん細胞'),
        'desc': _t('无法根除的恶性细胞。', 'A malignant cell that cannot be eradicated.', 'Une cellule maligne impossible à éradiquer.', 'Uma célula maligna impossível de erradicar.', 'Злокачественная клетка, которую невозможно искоренить.', '根絶できない悪性細胞。'),
        'effect': _t('对目标施加1层淬毒', 'Apply 1 Toxic to the target', 'Applique 1 Toxique à la cible', 'Aplica 1 Tóxico ao alvo', 'Накладывает на цель 1 Токсин', '対象に淬毒1を付与'),
    },
    'Yggdrasil': {
        'name': _t('世界树之叶', 'Yggdrasil', 'Arbre-Monde', 'Árvore-Mundo', 'Мировое древо', '世界樹'),
        'desc': _t('神奇的树叶。可以使人死而复生。', 'A wondrous leaf that can bring the dead back to life.', 'Une feuille merveilleuse qui peut ramener les morts à la vie.', 'Uma folha milagrosa capaz de trazer alguém de volta da morte.', 'Чудесный лист, способный вернуть мёртвого к жизни.', '死者を蘇らせることができる不思議な葉。'),
        'effect': _t('+20H；受到致命伤害时若在手牌中，则清除自己的所有效果，将生命值设为5，此回合无敌并放逐此牌', '+20H; when taking lethal damage, if this is in hand, clear your effects, set health to 5, become invincible this turn, and exile this card', '+20H ; lorsque vous subissez des dégâts mortels, si cette carte est en main, nettoie vos effets, fixe la vie à 5, rend invincible ce tour et exile cette carte', '+20H; ao sofrer dano letal, se estiver na mão, limpa seus efeitos, define a vida como 5, fica invencível neste turno e exila esta carta', '+20H; при смертельном уроне, если карта в руке, очистить ваши эффекты, установить здоровье на 5, стать неуязвимым на этот ход и изгнать эту карту', '+20H。致命ダメージを受ける時、手札にあるなら自分の効果を全て解除し、生命を5にし、このターン無敵になり、このカードを放逐する'),
    },
    'Corruption': {
        'name': _t('腐化', 'Corruption', 'Corruption', 'Corrupção', 'Порча', '腐化'),
        'desc': _t('伤敌一千，自损八百。', 'Hurt the enemy badly, but hurt yourself too.', 'Blesser lourdement l’ennemi, au prix de vos propres blessures.', 'Fere muito o inimigo, mas também fere você.', 'Сильно ранит врага, но и вам достаётся.', '敵を大きく傷つけるが、自分も傷つく。'),
        'effect': _t('自下个敌方回合开始，全场所有伤害变为1.5倍（向上取整）', 'Starting from the next enemy turn, all damage on the field is multiplied by 1.5 (rounded up)', 'À partir du prochain tour ennemi, tous les dégâts du terrain sont multipliés par 1,5 (arrondis au supérieur)', 'A partir do próximo turno inimigo, todo dano no campo é multiplicado por 1,5 (arredondado para cima)', 'Со следующего хода врага весь урон на поле умножается на 1,5 (округление вверх)', '次の敵ターンから、場の全てのダメージは1.5倍（切り上げ）になる'),
    },
    'Chilli': {
        'name': _t('辣椒', 'Chilli', 'Piment', 'Pimenta', 'Чили', '唐辛子'),
        'desc': _t('太过辛辣，让你不得不用一张牌解辣。', 'So spicy that you have to use a card to cool down.', 'Si piquant que vous devez utiliser une carte pour calmer le feu.', 'Tão picante que você precisa usar uma carta para aliviar.', 'Настолько острый, что приходится тратить карту, чтобы остудить жар.', '辛すぎて、カード1枚で辛さをしのぐしかない。'),
        'effect': _t('丢弃一张牌，然后抽一张牌', 'Discard one card, then draw one card', 'Défaussez une carte, puis piochez une carte', 'Descarte uma carta, depois compre uma carta', 'Сбросьте одну карту, затем доберите одну карту', 'カード1枚を捨て、その後1枚引く'),
    },
    'MagicSewage': {
        'name': _t('魔法污水', 'Magic Sewage', 'Eaux usées magiques', 'Esgoto Mágico', 'Магические стоки', '魔法汚水'),
        'desc': _t('至死方休！', 'It stops only at death.', 'Cela ne s’arrête qu’à la mort.', 'Só para com a morte.', 'Остановится только со смертью.', '死ぬまで止まらない！'),
        'effect': _t('摧毁场上所有装备', 'Destroy all equipment on the field', 'Détruit tous les équipements sur le terrain', 'Destrói todo equipamento em campo', 'Уничтожить всё снаряжение на поле', '場の全ての装備を破壊する'),
    },
    'MagicBubble': {
        'name': _t('魔法泡泡', 'Magic Bubble', 'Bulle magique', 'Bolha Mágica', 'Магический пузырь', '魔法の泡'),
        'desc': _t('泡泡的魔法版本。', 'The magical version of Bubble.', 'La version magique de Bulle.', 'A versão mágica de Bolha.', 'Магическая версия Пузыря.', '泡の魔法版。'),
        'effect': _t('使敌方下次使用的技能牌失效 响应：敌方使用技能牌', 'Negate the next enemy skill card. Response: enemy uses a skill card', 'Annule la prochaine carte de compétence ennemie. Réponse : l’ennemi joue une carte de compétence', 'Anula a próxima carta de habilidade inimiga. Resposta: inimigo usa uma carta de habilidade', 'Отменяет следующую карту навыка врага. Ответ: враг использует карту навыка', '敵が次に使用する技能カードを無効化する。反応：敵が技能カードを使用'),
    },
    'Mark': {
        'name': _t('标记', 'Mark', 'Marque', 'Marca', 'Метка', '標記'),
        'desc': _t('你被标记了！', 'You have been marked!', 'Vous avez été marqué !', 'Você foi marcado!', 'Вы отмечены!', 'あなたは標的にされた！'),
        'effect': _t('装备一回合后可触发，0E，直到目标下回合结束禁止目标行动', 'Can be triggered after being equipped for one turn, 0E: the target cannot act until its next turn ends', 'Peut être déclenché après avoir été équipé pendant un tour, 0E : jusqu’à la fin du prochain tour de la cible, la cible ne peut pas agir', 'Pode ser acionado após ficar equipado por um turno, 0E: até o fim do próximo turno do alvo, o alvo não pode agir', 'Можно активировать после одного хода в снаряжении, 0E: до конца следующего хода цели цель не может действовать', '1ターン装備後に発動可、0E：対象の次のターン終了まで、対象は行動できない'),
        'trigger': _t('直到目标下回合结束禁止目标行动', 'The target cannot act until its next turn ends', 'Jusqu’à la fin du prochain tour de la cible, la cible ne peut pas agir', 'Até o fim do próximo turno do alvo, o alvo não pode agir', 'До конца следующего хода цели цель не может действовать', '対象の次のターン終了まで、対象は行動できない'),
    },
    'Mine': {
        'name': _t('地雷', 'Mine', 'Mine', 'Mina', 'Мина', '地雷'),
        'desc': _t('它很危险，但需要一回合准备。', 'It is dangerous, but needs one turn to prepare.', 'Elle est dangereuse, mais nécessite un tour de préparation.', 'É perigosa, mas precisa de um turno de preparo.', 'Опасна, но требует один ход подготовки.', '危険だが、準備に1ターン必要。'),
        'effect': _t('装备一回合后可触发，0E，造成20D', 'Can be triggered after being equipped for one turn, 0E: deal 20D', 'Peut être déclenché après avoir été équipé pendant un tour, 0E : inflige 20D', 'Pode ser acionado após ficar equipado por um turno, 0E: causa 20D', 'Можно активировать после одного хода в снаряжении, 0E: нанести 20D', '1ターン装備後に発動可、0E：20Dを与える'),
        'trigger': _t('造成20D', 'Deal 20D', 'Inflige 20D', 'Causa 20D', 'Наносит 20D', '20Dを与える'),
    },
}


OPENING_EVENT_I18N = {
    1: {
        'name': _t('生命强化', 'Life Reinforcement', 'Renforcement vital', 'Reforço Vital', 'Усиление жизни', '生命強化'),
        'desc': _t('最大生命值+20', 'Max health +20', 'Santé max +20', 'Vida máxima +20', 'Макс. здоровье +20', '最大生命値+20'),
    },
    2: {
        'name': _t('魔力转化', 'Magic Conversion', 'Conversion magique', 'Conversão Mágica', 'Преобразование магии', '魔力変換'),
        'desc': _t('将最多3张牌转化为[[card:ManaOrb|flag=sprout|flag=symbiosis]]', 'Convert up to 3 cards into [[card:ManaOrb|flag=sprout|flag=symbiosis]]', 'Transforme jusqu’à 3 cartes en [[card:ManaOrb|flag=sprout|flag=symbiosis]]', 'Transforma até 3 cartas em [[card:ManaOrb|flag=sprout|flag=symbiosis]]', 'Превратите до 3 карт в [[card:ManaOrb|flag=sprout|flag=symbiosis]]', '最大3枚のカードを[[card:ManaOrb|flag=sprout|flag=symbiosis]]に変化させる'),
    },
    3: {
        'name': _t('光之洗礼', 'Baptism of Light', 'Baptême de lumière', 'Batismo de Luz', 'Крещение светом', '光の洗礼'),
        'desc': _t('将最多五张牌转化为Light：[[card:Light|flag=sprout|flag=symbiosis]]', 'Convert up to five cards into Light: [[card:Light|flag=sprout|flag=symbiosis]]', 'Transforme jusqu’à cinq cartes en Light : [[card:Light|flag=sprout|flag=symbiosis]]', 'Transforma até cinco cartas em Light: [[card:Light|flag=sprout|flag=symbiosis]]', 'Превратите до пяти карт в Light: [[card:Light|flag=sprout|flag=symbiosis]]', '最大5枚のカードをLight：[[card:Light|flag=sprout|flag=symbiosis]]に変化させる'),
    },
    8: {
        'name': _t('绝境求生', 'Last Stand', 'Dernier recours', 'Último Recurso', 'Последний шанс', '背水の生存'),
        'desc': _t('最大生命值-20，对局开始将一张牌变化为世界树之叶', 'Max health -20; at game start, transform one card into Yggdrasil', 'Santé max -20 ; au début de la partie, transforme une carte en Arbre-Monde', 'Vida máxima -20; no início da partida, transforma uma carta em Árvore-Mundo', 'Макс. здоровье -20; в начале игры превратите одну карту в Мировое древо', '最大生命値-20。対局開始時、カード1枚を世界樹に変化させる'),
    },
    4: {
        'name': _t('烈焰预兆', 'Flame Omen', 'Présage de flammes', 'Presságio Flamejante', 'Огненное знамение', '烈炎の兆し'),
        'desc': _t('开局对所有敌方玩家施加2层灼烧', 'At game start, apply 2 Burn to all enemy players', 'Au début de la partie, applique 2 Brûlure à tous les joueurs ennemis', 'No início da partida, aplica 2 Queima a todos os jogadores inimigos', 'В начале игры наложите 2 Горения на всех вражеских игроков', '開始時、敵プレイヤー全員に灼焼2を付与'),
    },
    5: {
        'name': _t('命运抽签', 'Fated Draw', 'Pioche du destin', 'Compra do Destino', 'Жребий судьбы', '運命のドロー'),
        'desc': _t('少抽1张牌，然后从总抽牌库选择1张牌洗入牌库', 'Draw 1 fewer card, then choose 1 card from the full draft pool and shuffle it into your deck', 'Piochez 1 carte de moins, puis choisissez 1 carte dans la réserve complète et mélangez-la dans votre deck', 'Compre 1 carta a menos, depois escolha 1 carta do conjunto completo e embaralhe-a no seu deck', 'Возьмите на 1 карту меньше, затем выберите 1 карту из общего пула и замешайте её в колоду', '1枚少なく引き、その後全体カードプールから1枚を選んで山札に混ぜる'),
    },
    6: {
        'name': _t('能量涌动', 'Energy Surge', 'Poussée d’énergie', 'Surto de Energia', 'Всплеск энергии', 'エネルギー奔流'),
        'desc': _t('前三回合开始时额外回复2E', 'At the start of the first three turns, recover an extra 2E', 'Au début des trois premiers tours, récupérez 2E supplémentaires', 'No início dos três primeiros turnos, recupere 2E extra', 'В начале первых трёх ходов восстановите дополнительно 2E', '最初の3ターン開始時、追加で2E回復'),
    },
    7: {
        'name': _t('先手压制', 'Opening Pressure', 'Pression initiale', 'Pressão Inicial', 'Стартовое давление', '先手圧制'),
        'desc': _t('必定先手(对面未选同事件时)，先手多回复3E抽4张牌', 'You go first unless the opponent chose the same event; the first player recovers 3E more and draws 4 cards', 'Vous commencez sauf si l’adversaire a choisi le même événement ; le premier joueur récupère 3E de plus et pioche 4 cartes', 'Você começa, a menos que o oponente tenha escolhido o mesmo evento; o primeiro jogador recupera 3E a mais e compra 4 cartas', 'Вы ходите первым, если противник не выбрал то же событие; первый игрок восстанавливает на 3E больше и берёт 4 карты', '相手が同じイベントを選んでいなければ必ず先手。先手は追加で3E回復し、4枚引く'),
    },
    9: {
        'name': _t('多重瓣', 'Multi-Petal', 'Multi-pétale', 'Multi-Pétala', 'Много лепестков', '多重子弁'),
        'desc': _t('所有有不少于2子瓣的卡牌+1子瓣，最大生命值+10', 'Cards with at least 2 petals gain +1 petal; max health +10', 'Les cartes avec au moins 2 pétales gagnent +1 pétale ; santé max +10', 'Cartas com pelo menos 2 pétalas ganham +1 pétala; vida máxima +10', 'Карты с минимум 2 лепестками получают +1 лепесток; макс. здоровье +10', '2子弁以上のカードは子弁+1。最大生命値+10'),
    },
    10: {
        'name': _t('魔力加速', 'Magic Acceleration', 'Accélération magique', 'Aceleração Mágica', 'Ускорение магии', '魔力加速'),
        'desc': _t('最大生命值-10，打出一张不消耗M的牌回复1M', 'Max health -10; after playing a card that costs no M, recover 1M', 'Santé max -10 ; après avoir joué une carte qui ne coûte pas de M, récupérez 1M', 'Vida máxima -10; depois de jogar uma carta que não custa M, recupere 1M', 'Макс. здоровье -10; после розыгрыша карты без затрат M восстановите 1M', '最大生命値-10。Mを消費しないカードを1枚使用した後、1M回復'),
    },
}


def _fill(field):
    zh = field.get('zh') or field.get('en') or ''
    en = field.get('en') or zh
    return {lang: field.get(lang) or en for lang in LANGS}


def card_text(card_id, fallback):
    data = CARD_I18N.get(card_id)
    if not data:
        out = dict(fallback)
        name = _fill({
            'zh': fallback.get('name_cn') or fallback.get('name_en') or card_id_to_english(card_id),
            'en': fallback.get('name_en') or card_id_to_english(card_id),
        })
        out['name_en'] = name['en']
        out['name_i18n'] = name
        return out
    name = _fill(data.get('name', {}))
    name['en'] = fallback.get('name_en') or name.get('en') or card_id_to_english(card_id)
    return {
        'name_i18n': name,
        'description_i18n': _fill(data.get('desc', {})),
        'effect_text_i18n': _fill(data.get('effect', {})),
        'trigger_effect_text_i18n': _fill(data.get('trigger', {
            'zh': data.get('effect', {}).get('zh', fallback.get('trigger_effect_text', '')),
            'en': data.get('effect', {}).get('en', fallback.get('trigger_effect_text', '')),
        })),
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
    for card_id, card in card_defs.items():
        if not getattr(card, 'name_en', ''):
            card.name_en = card_id_to_english(card_id)
