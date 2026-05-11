from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
import random
import copy


@dataclass
class CardDef:
    id: str
    name_en: str
    name_cn: str
    cost_e: int
    cost_m: int
    card_type: str
    count: int
    quality: str
    description: str
    effect_text: str
    flags: Set[str] = field(default_factory=set)
    trigger_cost_e: int = -1
    trigger_effect_text: str = ''
    response_trigger: str = ''


_next_instance_id = 0


def _new_instance_id():
    global _next_instance_id
    _next_instance_id += 1
    return _next_instance_id


@dataclass
class CardInstance:
    def_id: str
    instance_id: int = field(default_factory=_new_instance_id)
    cost_e_override: Optional[int] = None
    cost_m_override: Optional[int] = None
    fission_count: int = 0
    fusion_multiplier: float = 1.0
    mimic_discount: int = 0

    @property
    def card_def(self) -> CardDef:
        return CARD_DEFS[self.def_id]

    @property
    def name_cn(self) -> str:
        return self.card_def.name_cn

    @property
    def name_en(self) -> str:
        return self.card_def.name_en

    @property
    def cost_e(self) -> int:
        base = self.cost_e_override if self.cost_e_override is not None else self.card_def.cost_e
        return max(0, base - self.mimic_discount)

    @property
    def cost_m(self) -> int:
        return self.cost_m_override if self.cost_m_override is not None else self.card_def.cost_m

    @property
    def card_type(self) -> str:
        return self.card_def.card_type

    @property
    def flags(self) -> Set[str]:
        return self.card_def.flags

    def to_dict(self) -> dict:
        return {
            'def_id': self.def_id,
            'instance_id': self.instance_id,
            'cost_e_override': self.cost_e_override,
            'cost_m_override': self.cost_m_override,
            'fission_count': self.fission_count,
            'fusion_multiplier': self.fusion_multiplier,
            'mimic_discount': self.mimic_discount,
        }

    @staticmethod
    def from_dict(d: dict) -> 'CardInstance':
        return CardInstance(
            def_id=d['def_id'],
            instance_id=d['instance_id'],
            cost_e_override=d.get('cost_e_override'),
            cost_m_override=d.get('cost_m_override'),
            fission_count=d.get('fission_count', 0),
            fusion_multiplier=d.get('fusion_multiplier', 1.0),
            mimic_discount=d.get('mimic_discount', 0),
        )

    def copy(self) -> 'CardInstance':
        c = CardInstance(
            def_id=self.def_id,
            instance_id=_new_instance_id(),
            cost_e_override=self.cost_e_override,
            cost_m_override=self.cost_m_override,
            fission_count=self.fission_count,
            fusion_multiplier=self.fusion_multiplier,
            mimic_discount=self.mimic_discount,
        )
        return c


CARD_DEFS: Dict[str, CardDef] = {}


def _reg(card_def: CardDef):
    CARD_DEFS[card_def.id] = card_def


_reg(CardDef('Basic', 'Basic', '基本', 1, 0, 'attack', 10, 'Common',
             '最基本的卡牌。', '造成6D'))

_reg(CardDef('Bone', 'Bone', '骨头', 2, 0, 'attack', 5, 'Common',
             '坚固且好用。', '造成12D'))

_reg(CardDef('Stinger', 'Stinger', '刺', 4, 0, 'attack', 5, 'Common',
             '一击造成大量伤害。', '造成20D', flags={'precision'}))

_reg(CardDef('Sand', 'Sand', '沙子', 2, 0, 'attack', 5, 'Common',
             '因为是一把，所以可以造成多次伤害。', '造成3×4D（4子瓣）'))

_reg(CardDef('Wing', 'Wing', '翅膀', 3, 0, 'attack', 5, 'Common',
             '回旋的翅膀连续两次打击对手。', '造成8×2D（2子瓣）'))

_reg(CardDef('Light', 'Light', '轻', 0, 0, 'attack', 5, 'Common',
             '轻如鸿毛，却能伤人两次。', '造成2×2D（2子瓣）'))

_reg(CardDef('Fang', 'Fang', '尖牙', 2, 0, 'attack', 5, 'Common',
             '吸取对手的生命来为你回复。', '造成8D; 造成伤害时+4H'))

_reg(CardDef('Triangle', 'Triangle', '三角形', 2, 0, 'attack', 8, 'Common',
             '量变引起质变。', '造成(6+3×三角形层数)D；造成伤害时获得一层三角形'))

_reg(CardDef('MagicBone', 'Magic Bone', '魔法骨头', 0, 4, 'attack', 5, 'Common',
             '魔力凝聚的骨头，穿透力更强。', '造成15D'))

_reg(CardDef('MagicStinger', 'Magic Stinger', '魔法刺', 0, 8, 'attack', 5, 'Common',
             '魔力加持的尖刺，威力巨大。', '造成30D', flags={'precision'}))

_reg(CardDef('Fission', 'Fission', '裂变', 0, 0, 'skill', 2, 'Common',
             '将一次攻击分裂为多次。', '选择一张手中的攻击牌，使其下次打出时额外打出2次但伤害将为1/3（向上取整）',
             flags={'exile'}))

_reg(CardDef('Fusion', 'Fusion', '聚变', 0, 0, 'skill', 2, 'Common',
             '将相同的攻击聚合为一击。', '选择手中2-3张相同的攻击牌，使第一张下次打出时获得伤害增加1-2倍，丢弃余下的'))

_reg(CardDef('Iris', 'Iris', '鸢尾', 3, 0, 'skill', 3, 'Common',
             '美丽而致命。', '施加10层中毒'))

_reg(CardDef('Fire', 'Fire', '火', 3, 0, 'skill', 3, 'Common',
             '缓慢但持久地灼烧对手。', '造成2层灼烧'))

_reg(CardDef('Fries', 'Fries', '薯条', 2, 0, 'skill', 5, 'Common',
             '高热量食品，补充大量生命。', '+12H'))

_reg(CardDef('Rose', 'Rose', '玫瑰', 1, 0, 'skill', 10, 'Common',
             '这花香可以为你回复生命。', '+7H'))

_reg(CardDef('ManaOrb', 'Mana Orb', '魔法球', 1, 0, 'skill', 5, 'Common',
             '孕育魔力的小球。', '+3M'))

_reg(CardDef('Coffee', 'Coffee', '咖啡', 0, 0, 'skill', 5, 'Common',
             '可以用来提神，当然，小心耐药性。', '+1E，第一次使用额外+1E'))

_reg(CardDef('Chilli', 'Chilli', '辣椒', 0, 0, 'skill', 5, 'Common',
             '太过辛辣，让你不得不用一张牌解辣。', '丢弃一张牌，然后抽一张牌'))

_reg(CardDef('Chromosome', 'Chromosome', '染色体', 2, 0, 'skill', 2, 'Common',
             '从基因中提取记忆，寻找所需之牌。', '从弃牌堆中选择一张牌将其加入手中'))

_reg(CardDef('Sewage', 'Sewage', '污水', 2, 0, 'skill', 10, 'Common',
             '腐蚀一切装备。', '摧毁敌方一张装备'))

_reg(CardDef('MagicSewage', 'Magic Sewage', '魔法污水', 0, 6, 'skill', 3, 'Common',
             '至死方休！', '摧毁场上所有装备'))

_reg(CardDef('Mimic', 'Mimic', '拟态', 0, 0, 'skill', 2, 'Common',
             '完美模仿。', '将一张手牌的复制加入手中，使其下一次打出时费用-1',
             flags={'exile'}))

_reg(CardDef('Yggdrasil', 'Yggdrasil', '世界树之叶', 2, 0, 'skill', 2, 'Super',
             '神奇的树叶。可以使人死而复生。', '+20H；受到致命伤害时若在手牌中清除所有效果此回合无敌并放逐此牌'))

_reg(CardDef('Leaf', 'Leaf', '叶子', 1, 0, 'equipment', 5, 'Common',
             '基础的装备之一，可以回复生命亦可造成伤害。',
             '友方回合开始时+2H',
             trigger_cost_e=1, trigger_effect_text='若已装备一回合则摧毁此装备，造成8D'))

_reg(CardDef('Yucca', 'Yucca', '丝兰', 4, 0, 'equipment', 5, 'Common',
             '叶子的加强版。', '友方回合开始时+5H'))

_reg(CardDef('Disc', 'Disc', '圆盘', 3, 0, 'equipment', 3, 'Common',
             '坚实的护盾，减免来袭的伤害。', '+2A', flags={'non_stackable'}))

_reg(CardDef('Battery', 'Battery', '电池', 3, 0, 'equipment', 5, 'Common',
             '受击时会漏电。', '受到物理伤害时对敌方造成3D'))

_reg(CardDef('MagicLeaf', 'Magic Leaf', '魔法叶', 1, 0, 'equipment', 5, 'Common',
             '不再能造成伤害了，但它可以回复魔力。', '友方回合开始时+1M'))

_reg(CardDef('MagicYucca', 'Magic Yucca', '魔法丝兰', 3, 0, 'equipment', 5, 'Common',
             '生成更多魔力。', '友方回合开始时+2M'))

_reg(CardDef('MagicBattery', 'Magic Battery', '魔法电池', 3, 0, 'equipment', 3, 'Common',
             '每次受击都会激发魔力涌动。', '受到物理伤害时+1M(每回合上限3M)'))

_reg(CardDef('Powder', 'Powder', '粉末', 4, 0, 'equipment', 5, 'Common',
             '使你加快速度的神秘粉末。', '友方回合开始时+2E'))

_reg(CardDef('GoldenLeaf', 'Golden Leaf', '黄金叶', 3, 0, 'equipment', 5, 'Common',
             '这闪亮的叶子能为你带来额外的抽牌机会。', '回合开始时多抽一张牌'))

_reg(CardDef('Pincer', 'Pincer', '螫针', 4, 0, 'equipment', 3, 'Common',
             '毒素可以减缓对手行动。', '敌方回合开始时费用回复-1E'))

_reg(CardDef('Cancer', 'Cancer', '癌细胞', 7, 0, 'equipment', 2, 'Common',
             '无法根除的恶性细胞。', '对敌方施加2层易伤', flags={'indestructible'}))

_reg(CardDef('Corruption', 'Corruption', '腐化', 0, 0, 'equipment', 2, 'Common',
             '伤敌一千，自损八百。', '自下个敌方回合开始，全场所有伤害翻倍', flags={'indestructible'}))

_reg(CardDef('Mark', 'Mark', '标记', 4, 0, 'equipment', 3, 'Common',
             '你被标记了！', '禁止敌方行动一回合',
             trigger_cost_e=0, trigger_effect_text='若已装备一回合则摧毁此装备，直到敌方下回合结束敌方禁止行动'))

_reg(CardDef('Mine', 'Mine', '地雷', 3, 0, 'equipment', 3, 'Common',
             '它很危险，但需要一回合准备。', '下回合造成20D',
             trigger_cost_e=0, trigger_effect_text='若已装备一回合则摧毁此装备，造成20D'))

_reg(CardDef('Bubble', 'Bubble', '泡泡', 2, 0, 'counter', 10, 'Common',
             '闪！', '获得一层闪避（敌方使用攻击牌时）',
             response_trigger='attack'))

_reg(CardDef('Nazar', 'Nazar', '邪眼护符', 5, 0, 'counter', 3, 'Common',
             '邪眼的力量似乎为你减免了大部分伤害。', '所有物理伤害减少9(最少减至1)，受到两次10点及以上物理伤害后效果消失（敌方使用攻击牌时）',
             response_trigger='attack'))

_reg(CardDef('MagicNazar', 'Magic Nazar', '魔法邪眼', 0, 3, 'counter', 3, 'Common',
             '有魔力的护符，保护你的装备不被摧毁。', '获得一层装备保护（敌方摧毁装备牌时）',
             response_trigger='equipment_destroy'))

_reg(CardDef('MagicBubble', 'Magic Bubble', '魔法泡泡', 0, 4, 'counter', 3, 'Common',
             '泡泡的魔法版本。', '使敌方使用的技能牌失效（敌方使用技能牌时）',
             response_trigger='skill'))


DRAFT_RATIO = {'attack': 6, 'skill': 4, 'equipment': 3, 'counter': 2}
DRAFT_REROLLS = 3
HAND_LIMIT = 7
DRAW_PER_TURN = 3
ELIXIR_RECOVERY = 5
BASE_MAX_HEALTH = 100
BASE_MAX_ELIXIR = 10
BASE_MAX_MAGIC = 10
INITIAL_HEALTH = 100
INITIAL_ELIXIR = 5
INITIAL_MAGIC = 0
FIRST_PLAYER_ELIXIR = 3
SECOND_PLAYER_HEALTH = 100
DECK_SIZE = 15
INITIAL_HAND_SIZE = 5
FIRST_PLAYER_HAND_SIZE = 4


def build_draft_pool() -> List[CardInstance]:
    pool = []
    for def_id, card_def in CARD_DEFS.items():
        if def_id == 'Yggdrasil':
            continue
        for _ in range(card_def.count):
            pool.append(CardInstance(def_id=def_id))
    return pool


def generate_draft_options(pool: List[CardInstance], card_type: str, count: int = 3) -> List[CardInstance]:
    type_cards = [c for c in pool if c.card_def.card_type == card_type]
    seen_def_ids = set()
    unique_cards = []
    for c in type_cards:
        if c.def_id not in seen_def_ids:
            seen_def_ids.add(c.def_id)
            unique_cards.append(c)
    if len(unique_cards) < count:
        return unique_cards
    return random.sample(unique_cards, count)


def create_deck_from_draft(picked_def_ids: List[str]) -> List[CardInstance]:
    deck = []
    for def_id in picked_def_ids:
        deck.append(CardInstance(def_id=def_id))
    random.shuffle(deck)
    return deck
