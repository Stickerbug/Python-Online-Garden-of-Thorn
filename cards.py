from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
import random
import copy

ERROR_CARD_ID = 'Error'

CARD_FLAG_ALIASES = {
    'tag_troll_cards:exile': 'exile',
    'troll_cards:exile': 'exile',
    'tag_troll_cards_exile': 'exile',
    'troll_cards_exile': 'exile',
}


def normalize_card_flag(flag: Any) -> str:
    text = str(flag or '').strip()
    if not text:
        return ''
    return CARD_FLAG_ALIASES.get(text.lower(), text)


def normalize_card_flags(flags) -> Set[str]:
    if not flags:
        return set()
    if isinstance(flags, str):
        raw_items = [item.strip() for item in flags.replace(',', ' ').split()]
    elif isinstance(flags, dict):
        raw_items = [item for item, enabled in flags.items() if enabled]
    else:
        raw_items = list(flags)
    return {flag for flag in (normalize_card_flag(item) for item in raw_items) if flag}


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
    effects: List[dict] = field(default_factory=list)
    scripts: Dict[str, Any] = field(default_factory=dict)
    response_title: str = ''
    response_content: str = ''
    v2_events: Dict[str, Any] = field(default_factory=dict)
    v2_resource: Dict[str, Any] = field(default_factory=dict)
    v2_mod_id: str = ''
    image: str = ''
    image_url: str = ''

    @property
    def display_name(self) -> str:
        try:
            from i18n import current_lang
            return self.name_en if current_lang() == 'en_US' else self.name_cn
        except Exception:
            return self.name_cn


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
    fission_level: int = 1
    fusion_level: int = 1
    mimic_discount: int = 0
    fission_hit: int = 0
    bonus_damage: int = 0
    held_turns: int = 0
    return_to_hand_turns: int = 0
    instance_flags: Set[str] = field(default_factory=set)
    disabled_flags: Set[str] = field(default_factory=set)

    def __post_init__(self):
        if not self.def_id:
            self.def_id = ERROR_CARD_ID
            return
        defs = globals().get('CARD_DEFS')
        if isinstance(defs, dict) and defs and self.def_id not in defs:
            self.def_id = ERROR_CARD_ID

    @property
    def card_def(self) -> CardDef:
        return CARD_DEFS.get(self.def_id) or CARD_DEFS[ERROR_CARD_ID]

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
        base = normalize_card_flags(self.card_def.flags)
        added = normalize_card_flags(self.instance_flags)
        disabled = normalize_card_flags(self.disabled_flags)
        return (base | added) - disabled

    def to_dict(self) -> dict:
        return {
            'def_id': self.def_id,
            'instance_id': self.instance_id,
            'cost_e_override': self.cost_e_override,
            'cost_m_override': self.cost_m_override,
            'fission_count': self.fission_count,
            'fusion_multiplier': self.fusion_multiplier,
            'fission_level': self.fission_level,
            'fusion_level': self.fusion_level,
            'mimic_discount': self.mimic_discount,
            'bonus_damage': self.bonus_damage,
            'held_turns': self.held_turns,
            'return_to_hand_turns': self.return_to_hand_turns,
            'instance_flags': list(self.instance_flags) if self.instance_flags else [],
            'disabled_flags': list(self.disabled_flags) if self.disabled_flags else [],
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
            fission_level=max(1, int(d.get('fission_level', d.get('fission_count', 0) + 1))),
            fusion_level=max(1, int(d.get('fusion_level', d.get('fusion_multiplier', 1.0)))),
            mimic_discount=d.get('mimic_discount', 0),
            bonus_damage=max(0, int(d.get('bonus_damage', 0))),
            held_turns=max(0, int(d.get('held_turns', 0))),
            return_to_hand_turns=max(0, int(d.get('return_to_hand_turns', 0))),
            instance_flags=normalize_card_flags(d.get('instance_flags', [])),
            disabled_flags=normalize_card_flags(d.get('disabled_flags', [])),
        )

    def copy(self) -> 'CardInstance':
        c = CardInstance(
            def_id=self.def_id,
            instance_id=_new_instance_id(),
            cost_e_override=self.cost_e_override,
            cost_m_override=self.cost_m_override,
            fission_count=self.fission_count,
            fusion_multiplier=self.fusion_multiplier,
            fission_level=self.fission_level,
            fusion_level=self.fusion_level,
            mimic_discount=self.mimic_discount,
            bonus_damage=self.bonus_damage,
            held_turns=self.held_turns,
            return_to_hand_turns=self.return_to_hand_turns,
            instance_flags=set(self.instance_flags),
            disabled_flags=set(self.disabled_flags),
        )
        return c


CARD_DEFS: Dict[str, CardDef] = {}


def _reg(card_def: CardDef):
    CARD_DEFS[card_def.id] = card_def


_reg(CardDef(ERROR_CARD_ID, 'Error', '错误', 0, 0, 'bloom', 0, 'Common',
             '哎呀，你怎么会看到这张牌？', '这是一个错误，请联系服务器管理员',
             flags={'infinite_exclude'}))


_reg(CardDef('Basic', 'Basic', '基本', 1, 0, 'thorn', 10, 'Common',
             '最基本的卡牌。', '造成6D'))

_reg(CardDef('Bone', 'Bone', '骨头', 2, 0, 'thorn', 5, 'Common',
             '坚固且好用。', '造成12D'))

_reg(CardDef('Stinger', 'Stinger', '刺', 4, 0, 'thorn', 5, 'Common',
             '一击造成大量伤害。', '造成20D', flags={'precision'}))

_reg(CardDef('Sand', 'Sand', '沙子', 2, 0, 'thorn', 5, 'Common',
             '因为是一把，所以可以造成多次伤害。', '造成3D×4（4子瓣）'))

_reg(CardDef('Wing', 'Wing', '翅膀', 3, 0, 'thorn', 5, 'Common',
             '回旋的翅膀连续两次打击对手。', '造成8D×2（2子瓣）'))

_reg(CardDef('Light', 'Light', '轻', 0, 0, 'thorn', 5, 'Common',
             '轻如鸿毛，却能伤人两次。', '造成2D×2（2子瓣）'))

_reg(CardDef('Fang', 'Fang', '尖牙', 2, 0, 'thorn', 5, 'Common',
             '吸取对手的生命来为你回复。', '造成8D; 造成伤害时+4H'))

_reg(CardDef('Triangle', 'Triangle', '三角形', 2, 0, 'thorn', 8, 'Common',
             '量变引起质变。', '造成(6+3×三角形层数)D；造成伤害时获得一层三角形，上限4层'))

_reg(CardDef('MagicBone', 'Magic Bone', '魔法骨头', 0, 4, 'thorn', 5, 'Common',
             '魔力凝聚的骨头，穿透力更强。', '造成15D'))

_reg(CardDef('MagicStinger', 'Magic Stinger', '魔法刺', 0, 8, 'thorn', 5, 'Common',
             '魔力加持的尖刺，威力巨大。', '造成30D', flags={'precision'}))

_reg(CardDef('Fission', 'Fission', '裂变', 0, 0, 'bloom', 2, 'Common',
             '将一次攻击分裂为多次。', '选择一张手中的攻击牌，将其裂变层数增加2',
             flags={'exile', 'self_only'}))

_reg(CardDef('Fusion', 'Fusion', '聚变', 0, 0, 'bloom', 2, 'Common',
             '将相同的攻击聚合为一击。', '选择手中2-3张同名攻击牌，将它们的聚变层数相加，裂变层数取最大值，变为一张牌',
             flags={'exile', 'self_only'}))

_reg(CardDef('Iris', 'Iris', '鸢尾', 3, 0, 'bloom', 3, 'Common',
             '美丽而致命。', '施加10层中毒'))

_reg(CardDef('Fire', 'Fire', '火', 2, 0, 'bloom', 3, 'Common',
             '缓慢但持久地灼烧对手。', '造成2层灼烧'))

_reg(CardDef('Fries', 'Fries', '薯条', 2, 0, 'bloom', 5, 'Common',
             '高热量食品，补充大量生命。', '+12H'))

_reg(CardDef('Rose', 'Rose', '玫瑰', 1, 0, 'bloom', 10, 'Common',
             '这花香可以为你回复生命。', '+7H'))

_reg(CardDef('ManaOrb', 'Mana Orb', '魔法球', 1, 0, 'bloom', 5, 'Common',
             '孕育魔力的小球。', '+3M'))

_reg(CardDef('Coffee', 'Coffee', '咖啡', 0, 0, 'bloom', 5, 'Common',
             '可以用来提神，当然，小心耐药性。', '+1E，第一次使用额外+1E'))

_reg(CardDef('Chilli', 'Chilli', '辣椒', 0, 0, 'bloom', 5, 'Common',
             '太过辛辣，让你不得不用一张牌解辣。', '丢弃一张牌，然后抽一张牌'))

_reg(CardDef('Chromosome', 'Chromosome', '染色体', 2, 0, 'bloom', 2, 'Common',
             '从基因中提取记忆，寻找所需之牌。', '从弃牌堆中选择一张牌将其加入手中'))

_reg(CardDef('Sewage', 'Sewage', '污水', 2, 0, 'bloom', 10, 'Common',
             '腐蚀一切装备。', '摧毁目标一张装备'))

_reg(CardDef('MagicSewage', 'Magic Sewage', '魔法污水', 0, 6, 'bloom', 3, 'Common',
             '至死方休！', '摧毁场上所有装备'))

_reg(CardDef('Mimic', 'Mimic', '拟态', 0, 0, 'bloom', 2, 'Common',
             '完美模仿。', '将一张手牌的复制加入手中，使其下一次打出时费用-1',
             flags={'exile', 'self_only'}))

_reg(CardDef('Yggdrasil', 'Yggdrasil', '世界树之叶', 2, 0, 'bloom', 0, 'Super',
             '神奇的树叶。可以使人死而复生。', '+20H；受到致命伤害时，若在手牌中，则清除自己的所有效果，将生命值设为5，此回合无敌并放逐此牌'))

_reg(CardDef('Leaf', 'Leaf', '叶子', 1, 0, 'root', 5, 'Common',
             '基础的装备之一，可以回复生命亦可造成伤害。',
             '自己回合开始时+2H',
             trigger_cost_e=1, trigger_effect_text='若已装备一回合则可摧毁此装备，造成8D'))

_reg(CardDef('Yucca', 'Yucca', '丝兰', 4, 0, 'root', 5, 'Common',
             '在平缓的回合后积蓄更多生机。', '自己回合开始时+3H；若上个自己的回合造成的实际伤害低于10D，则额外+7H'))

_reg(CardDef('Disc', 'Disc', '圆盘', 3, 0, 'root', 3, 'Common',
             '坚实的护盾，减免来袭的伤害。', '+2A', flags={'non_stackable'}))

_reg(CardDef('Battery', 'Battery', '电池', 3, 0, 'root', 5, 'Common',
             '受击时会漏电。', '受到物理伤害时对攻击者造成3D'))

_reg(CardDef('MagicLeaf', 'Magic Leaf', '魔法叶', 1, 0, 'root', 5, 'Common',
             '不再能造成伤害了，但它可以回复魔力。', '自己回合开始时+1M'))

_reg(CardDef('MagicYucca', 'Magic Yucca', '魔法丝兰', 3, 0, 'root', 5, 'Common',
             '生成更多魔力。', '自己回合开始时+2M'))

_reg(CardDef('MagicBattery', 'Magic Battery', '魔法电池', 3, 0, 'root', 3, 'Common',
             '每次受击都会激发魔力涌动。', '受到物理伤害时+1M(每回合上限3M)'))

_reg(CardDef('Powder', 'Powder', '粉末', 4, 0, 'root', 5, 'Common',
             '使你加快速度的神秘粉末。', '自己回合开始时+2E'))

_reg(CardDef('GoldenLeaf', 'Golden Leaf', '黄金叶', 3, 0, 'root', 5, 'Common',
             '这闪亮的叶子能为你带来额外的抽牌机会。', '手牌爆牌上限+1；自己回合开始时多抽一张牌'))

_reg(CardDef('Pincer', 'Pincer', '螫针', 4, 0, 'root', 3, 'Common',
             '毒素可以减缓对手行动。', '目标回合开始时E回复-1'))

_reg(CardDef('Cancer', 'Cancer', '癌细胞', 4, 0, 'root', 2, 'Common',
             '无法根除的恶性细胞。', '对目标施加1层淬毒', flags={'indestructible'}))

_reg(CardDef('Corruption', 'Corruption', '腐化', 0, 0, 'root', 2, 'Common',
             '伤敌一千，自损八百。', '自下个敌方回合开始，全场所有伤害变为1.5倍（向上取整）', flags={'indestructible', 'self_only'}))

_reg(CardDef('Mark', 'Mark', '标记', 4, 0, 'root', 3, 'Common',
             '你被标记了！', '禁止目标行动一回合',
             trigger_cost_e=0, trigger_effect_text='若已装备一回合则可摧毁此装备，直到目标下回合结束目标禁止行动'))

_reg(CardDef('Mine', 'Mine', '地雷', 3, 0, 'root', 3, 'Common',
             '它很危险，但需要一回合准备。', '下回合造成20D',
             trigger_cost_e=0, trigger_effect_text='若已装备一回合则可摧毁此装备，造成20D'))

_reg(CardDef('Bubble', 'Bubble', '泡泡', 2, 0, 'guard', 10, 'Common',
             '闪！', '获得一层闪避（敌方使用攻击牌时）',
             response_trigger='thorn'))

_reg(CardDef('Nazar', 'Nazar', '邪眼护符', 5, 0, 'guard', 3, 'Common',
             '邪眼的力量似乎为你减免了大部分伤害。', '所有物理伤害减少9(最少减至1)，受到两次10点及以上物理伤害后效果消失（敌方使用攻击牌时）',
             response_trigger='thorn'))

_reg(CardDef('MagicNazar', 'Magic Nazar', '魔法邪眼', 0, 3, 'guard', 3, 'Common',
             '有魔力的护符，保护你的装备不被摧毁。', '获得一层装备保护（自己的装备即将被摧毁时）',
             response_trigger='equipment_destroy'))

_reg(CardDef('MagicBubble', 'Magic Bubble', '魔法泡泡', 0, 4, 'guard', 3, 'Common',
             '泡泡的魔法版本。', '使敌方使用的技能牌失效（敌方使用技能牌时）',
             response_trigger='bloom'))



DRAFT_RATIO = {'thorn': 6, 'bloom': 4, 'root': 3, 'guard': 2}
DRAFT_REROLLS = 3
FIXED_GLOBAL_DRAFT_WEIGHT_RATIOS = {
    # Keep Sewage at a fixed 14% within the Bloom draft pool.
    # The weight is adjusted when extra Bloom mod cards enter the draft pool.
    'Sewage': (14, 100),
}
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


def _effective_draft_weights(allowed_def_ids: Optional[Set[str]] = None) -> Dict[str, float]:
    allowed = {}
    for def_id, card_def in CARD_DEFS.items():
        if def_id == 'Yggdrasil':
            continue
        if allowed_def_ids is not None and def_id not in allowed_def_ids:
            continue
        count = max(0, int(getattr(card_def, 'count', 0) or 0))
        if count <= 0:
            continue
        allowed[def_id] = float(count)

    by_type_fixed = {}
    for def_id in FIXED_GLOBAL_DRAFT_WEIGHT_RATIOS:
        if def_id not in allowed or def_id not in CARD_DEFS:
            continue
        by_type_fixed.setdefault(CARD_DEFS[def_id].card_type, []).append(def_id)

    for card_type, fixed_ids in by_type_fixed.items():
        fixed_ratio_sum = 0.0
        for def_id in fixed_ids:
            numerator, denominator = FIXED_GLOBAL_DRAFT_WEIGHT_RATIOS[def_id]
            if denominator:
                fixed_ratio_sum += max(0.0, float(numerator) / float(denominator))
        other_total = sum(
            weight for def_id, weight in allowed.items()
            if def_id not in fixed_ids and CARD_DEFS.get(def_id) and CARD_DEFS[def_id].card_type == card_type
        )
        if other_total <= 0 or fixed_ratio_sum <= 0 or fixed_ratio_sum >= 1:
            continue
        for def_id in fixed_ids:
            numerator, denominator = FIXED_GLOBAL_DRAFT_WEIGHT_RATIOS[def_id]
            target_ratio = max(0.0, float(numerator) / float(denominator)) if denominator else 0.0
            if target_ratio > 0:
                allowed[def_id] = target_ratio * other_total / (1.0 - fixed_ratio_sum)
    return allowed


def build_draft_pool(allowed_def_ids: Optional[Set[str]] = None) -> List[CardInstance]:
    pool = []
    for def_id, weight in _effective_draft_weights(allowed_def_ids).items():
        card = CardInstance(def_id=def_id)
        card.draft_weight = weight
        pool.append(card)
    return pool


def generate_draft_options(pool: List[CardInstance], card_type: str, count: int = 3, exclude_def_ids: List[str] = None) -> List[CardInstance]:
    type_cards = [c for c in pool if c.card_def.card_type == card_type]
    def weighted_unique_sample(cards: List[CardInstance], sample_count: int) -> List[CardInstance]:
        first_by_id = {}
        weights = {}
        for card in cards:
            if card.def_id not in first_by_id:
                first_by_id[card.def_id] = card
                weights[card.def_id] = 0
            weights[card.def_id] += max(0.0, float(getattr(card, 'draft_weight', 1.0) or 0.0))
        ids = list(first_by_id.keys())
        picked = []
        while ids and len(picked) < sample_count:
            choice = random.choices(ids, weights=[weights[i] for i in ids], k=1)[0]
            picked.append(first_by_id[choice])
            ids.remove(choice)
        return picked

    unique_cards = weighted_unique_sample(type_cards, len(type_cards))
    exclude = set(exclude_def_ids) if exclude_def_ids else set()
    available = [c for c in unique_cards if c.def_id not in exclude]
    if len(available) >= count:
        return weighted_unique_sample([c for c in type_cards if c.def_id not in exclude], count)
    if len(available) > 0:
        needed = count - len(available)
        fallback = [c for c in unique_cards if c.def_id in exclude]
        if fallback:
            return available + weighted_unique_sample([c for c in type_cards if c.def_id in exclude], min(needed, len(fallback)))
        return available
    return weighted_unique_sample(type_cards, min(count, len(unique_cards)))


def create_deck_from_draft(picked_def_ids: List[str], allowed_def_ids: Optional[Set[str]] = None) -> List[CardInstance]:
    deck = []
    for def_id in picked_def_ids:
        if allowed_def_ids is not None and def_id not in allowed_def_ids:
            continue
        deck.append(CardInstance(def_id=def_id))
    random.shuffle(deck)
    return deck
