"""Data definitions for the server-authoritative story mode.

The story engine intentionally consumes this file instead of multiplayer card
definitions. Story cards share artwork with multiplayer cards where possible,
but their balance and rules are independent.
"""

from copy import deepcopy


STORY_RULES = {
    'starting_health': 80,
    'starting_elixir': 3,
    'starting_magic': 0,
    'max_magic': 10,
    'resource_cap': None,
    'draw_per_turn': 5,
    'hand_limit': 10,
    'stage_floor_count': 16,
}

STORY_BIOMES = {
    'garden': {
        'name': {'zh': '花园', 'en': 'Garden'},
        'color': '#54A866',
    },
    'desert': {
        'name': {'zh': '沙漠', 'en': 'Desert'},
        'color': '#D5A13E',
    },
    'ocean': {
        'name': {'zh': '海洋', 'en': 'Ocean'},
        'color': '#3A94C8',
    },
}

STORY_DIFFICULTIES = {
    'easy': {
        'name': {'zh': '简单', 'en': 'Easy'},
        'abbreviation': {'zh': 'E', 'en': 'E'},
        'description': {
            'zh': '使用普通地图，并在初始赐福前从3项简单难度天赋中选择1项',
            'en': 'Use the Normal map and choose 1 of 3 Easy talents before the starting blessing',
        },
    },
    'normal': {
        'name': {'zh': '普通', 'en': 'Normal'},
        'abbreviation': {'zh': 'N', 'en': 'N'},
        'description': {
            'zh': '使用标准地图、奖励与生物强度',
            'en': 'Standard map, rewards, and enemy strength',
        },
    },
    'hard': {
        'name': {'zh': '困难', 'en': 'Hard'},
        'abbreviation': {'zh': 'H', 'en': 'H'},
        'description': {
            'zh': '危险房间更多，金币和升级牌更少，商店价格更高',
            'en': 'More dangerous rooms, less gold and fewer upgraded cards, with higher shop prices',
        },
    },
    'lunatic': {
        'name': {'zh': '疯狂', 'en': 'Lunatic'},
        'abbreviation': {'zh': 'L', 'en': 'L'},
        'description': {
            'zh': '继承困难规则，且生物的H、伤害与行动更强',
            'en': 'Includes Hard rules and strengthens enemy H, damage, and actions',
        },
    },
}

STORY_CURSES = {
    'vitality': {
        'name': {'zh': '旺盛', 'en': 'Vitality'},
        'description': {
            'zh': '所有生物的H上限增加150%',
            'en': 'All enemies gain 150% maximum H',
        },
    },
    'aggression': {
        'name': {'zh': '凶猛', 'en': 'Aggression'},
        'description': {
            'zh': '所有生物的攻击伤害增加80%',
            'en': 'All enemies deal 80% more attack damage',
        },
    },
    'affliction': {
        'name': {'zh': '苦难', 'en': 'Affliction'},
        'description': {
            'zh': '所有生物在战斗开始时获得3层负面状态免疫；每名生物每次行动后，随机对玩家方施加1层虚弱、脆弱或易伤',
            'en': 'All enemies start combat with 3 Negative Status Immunity; after each enemy action, apply 1 random Weak, Fragile, or Vulnerable to the player',
        },
    },
}

STORY_RARITIES = {
    'primary': {'name': {'zh': '基础', 'en': 'Primary'}, 'color': '#7EEF6D'},
    'common': {'name': {'zh': '普通', 'en': 'Common'}, 'color': '#FFE65D'},
    'rare': {'name': {'zh': '稀有', 'en': 'Rare'}, 'color': '#861FDE'},
    'ultra': {'name': {'zh': '究极', 'en': 'Ultra'}, 'color': '#FF2B75'},
    'super': {'name': {'zh': '超级', 'en': 'Super'}, 'color': '#2BFFA3'},
}

STORY_CARD_TYPES = {
    'thorn': {'name': {'zh': '攻击', 'en': 'Thorn'}, 'color': '#C64343'},
    'bloom': {'name': {'zh': '技能', 'en': 'Bloom'}, 'color': '#3D8E5B'},
    'root': {'name': {'zh': '装备', 'en': 'Root'}, 'color': '#8A6337'},
    'guard': {'name': {'zh': '反制', 'en': 'Guard'}, 'color': '#496FA8'},
    'curse': {'name': {'zh': '诅咒', 'en': 'Curse'}, 'color': '#704B87'},
    'infect': {'name': {'zh': '状态', 'en': 'Infect'}, 'color': '#7E9638'},
}

STORY_PLAYER_ATTACK_EFFECT_TYPES = frozenset({
    'damage',
    'damage_per_active_discard',
    'damage_per_status',
    'damage_from_shield',
    'damage_per_elixir',
})

STORY_TAGS = {
    'precise': {
        'name': {'zh': '精准', 'en': 'Precise'},
        'description': {'zh': '精准攻击无法被闪避。', 'en': 'Precise attacks cannot be evaded.'},
    },
    'exile': {
        'name': {'zh': '放逐', 'en': 'Exile'},
        'description': {'zh': '打出后进入放逐区。', 'en': 'Exile this card after it is played.'},
    },
    'ready': {
        'name': {'zh': '蓄势待发', 'en': 'Ready'},
        'description': {
            'zh': '进入手牌或回合开始时，若满足使用条件则自动打出。',
            'en': 'When drawn or at turn start, play this automatically if it is playable.',
        },
    },
    'unplayable': {
        'name': {'zh': '禁止', 'en': 'Unplayable'},
        'description': {'zh': '无法打出。', 'en': 'This card cannot be played.'},
    },
    'retain': {
        'name': {'zh': '保留', 'en': 'Retain'},
        'description': {'zh': '回合结束时保留在手牌中。', 'en': 'Keep this card in hand at end of turn.'},
    },
    'void': {
        'name': {'zh': '虚无', 'en': 'Void'},
        'description': {'zh': '回合结束时若仍在手牌中，则将其放逐。', 'en': 'If this remains in hand at end of turn, exile it.'},
    },
    'wide': {
        'name': {'zh': '广域打击', 'en': 'Wide Strike'},
        'description': {'zh': '对所有可选中的生物生效。', 'en': 'Apply the effect to every selectable creature.'},
    },
    'recovery': {
        'name': {'zh': '恢复', 'en': 'Recovery'},
        'description': {
            'zh': '经过指定场数的战斗后，将此牌从牌组中永久移除。',
            'en': 'Permanently remove this card from the deck after the specified number of battles.',
        },
    },
    'sublime': {
        'name': {'zh': '崇高', 'en': 'Sublime'},
        'description': {
            'zh': '无法被除打出外的行为选中。',
            'en': 'Cannot be selected by anything except being played.',
        },
    },
    'eternal': {
        'name': {'zh': '永恒', 'en': 'Eternal'},
        'description': {
            'zh': '无法从牌组中删除。',
            'en': 'Cannot be removed from the deck.',
        },
    },
    'charge': {
        'name': {'zh': '电荷', 'en': 'Charge'},
        'description': {
            'zh': '打出时对自己造成等同于层数的电伤。',
            'en': 'When played, deal electric damage to yourself equal to its stacks.',
        },
    },
}

STORY_STATUSES = {
    'shield': {
        'name': {'zh': '护盾', 'en': 'Shield'},
        'description': {'zh': '抵扣等量伤害；回合开始时清空。', 'en': 'Blocks an equal amount of damage, then clears at turn start.'},
    },
    'power': {
        'name': {'zh': '力量', 'en': 'Power'},
        'description': {'zh': '每层使每次物理伤害+1。', 'en': 'Each stack adds 1 to each physical hit.'},
    },
    'temporary_power': {
        'name': {'zh': '暂时力量', 'en': 'Temporary Power'},
        'description': {'zh': '等同力量，回合结束时清空。', 'en': 'Acts as Power and clears at end of turn.'},
    },
    'endurance': {
        'name': {'zh': '耐力', 'en': 'Endurance'},
        'description': {'zh': '从卡牌获得护盾时，每层使护盾+1。', 'en': 'Each stack adds 1 Shield gained from cards.'},
    },
    'weak': {
        'name': {'zh': '虚弱', 'en': 'Weak'},
        'description': {'zh': '造成的物理伤害向下取整减少25%；回合开始时-1层。', 'en': 'Deal 25% less physical damage; lose 1 at turn start.'},
    },
    'vulnerable': {
        'name': {'zh': '易伤', 'en': 'Vulnerable'},
        'description': {'zh': '受到的物理伤害向下取整增加50%；回合开始时-1层。', 'en': 'Take 50% more physical damage; lose 1 at turn start.'},
    },
    'fragile': {
        'name': {'zh': '脆弱', 'en': 'Fragile'},
        'description': {'zh': '从卡牌获得的护盾向下取整减少25%；回合开始时-1层。', 'en': 'Gain 25% less Shield from cards; lose 1 at turn start.'},
    },
    'evade': {
        'name': {'zh': '闪避', 'en': 'Evade'},
        'description': {'zh': '受到攻击时消耗1层并免除该次攻击；回合开始时-1层。', 'en': 'Spend 1 to evade an attack; lose 1 at turn start.'},
    },
    'poison': {
        'name': {'zh': '中毒', 'en': 'Poison'},
        'description': {'zh': '回合开始时受到层数点伤害，然后层数向下取整减半。', 'en': 'At turn start, take damage equal to stacks, then halve stacks.'},
    },
    'stun': {
        'name': {'zh': '眩晕', 'en': 'Stun'},
        'description': {
            'zh': '跳过层数个可行动回合；眩晕是一种行动，不属于状态。',
            'en': 'Skip that many actionable turns; Stun is an action, not a status.',
        },
        'category': 'action',
    },
    'reflection': {
        'name': {'zh': '反射', 'en': 'Reflection'},
        'description': {'zh': '每次受到攻击时，对攻击者造成层数点伤害。', 'en': 'When attacked, deal damage equal to stacks to the attacker.'},
    },
    'wither': {
        'name': {'zh': '凋萎', 'en': 'Wither'},
        'description': {'zh': '回合结束时-1层；层数消失后死亡。', 'en': 'Lose 1 at turn end; die when it expires.'},
    },
    'broken': {
        'name': {'zh': '破损', 'en': 'Broken'},
        'description': {
            'zh': '每打出1张牌，受到等同于层数的伤害；自己的行动回合结束时清空。',
            'en': 'Take damage equal to its stacks whenever you play a card; clear it after your action turn.',
        },
    },
    'rockfall': {
        'name': {'zh': '落石', 'en': 'Rockfall'},
        'description': {
            'zh': '行动开始时造成等同于层数的D，然后获得2层落石。',
            'en': 'At action start, deal D equal to its stacks, then gain 2 Rockfall.',
        },
    },
    'blind': {
        'name': {'zh': '失明', 'en': 'Blind'},
        'description': {
            'zh': '隐藏手牌信息；回合开始时-1层。',
            'en': 'Hide hand information; lose 1 stack at turn start.',
        },
    },
    'entangle': {
        'name': {'zh': '缠绕', 'en': 'Entangle'},
        'description': {
            'zh': '回合结束时受到等同于层数的伤害，然后清空。',
            'en': 'At turn end, take damage equal to its stacks, then clear it.',
        },
    },
    'negative_status_immunity': {
        'name': {'zh': '负面状态免疫', 'en': 'Negative Status Immunity'},
        'description': {
            'zh': '抵消下一次受到的负面状态，每次抵消后-1层。',
            'en': 'Negate the next negative-status application, then lose 1 stack.',
        },
    },
    'evil_eye': {
        'name': {'zh': '邪眼', 'en': 'Evil Eye'},
        'description': {
            'zh': '受到不超过9D的物理伤害时改为受到1D；受到至少10D时使其-9D并消耗1层。',
            'en': 'Physical damage up to 9 becomes 1; damage of at least 10 is reduced by 9 and consumes 1 stack.',
        },
    },
}

STORY_STATUS_IMAGE_URLS = {
    'entangle': '/static/assets/story-status-icons/entangle.svg',
    'endurance': '/static/assets/story-status-icons/endurance.svg',
    'evil_eye': '/static/assets/status-icons/nazar.svg',
    'negative_status_immunity': '/static/assets/status-icons/status_immune.svg',
    'power': '/static/assets/story-status-icons/power.svg',
    'reflection': '/static/assets/story-status-icons/reflection.svg',
    'rockfall': '/static/assets/story-status-icons/rockfall.svg',
    'temporary_power': '/static/assets/story-status-icons/temporary-power.svg',
    'vulnerable': '/static/assets/story-status-icons/vulnerable.svg',
    'fragile': '/static/assets/story-status-icons/fragile.svg',
    'wither': '/static/assets/story-status-icons/wither.svg',
}

for _status_id, _image_url in STORY_STATUS_IMAGE_URLS.items():
    STORY_STATUSES[_status_id]['image_url'] = _image_url


STORY_TRAITS = {
    'adjacent': {
        'name': {'zh': '紧连', 'en': 'Linked'},
        'description': {
            'zh': '受到伤害时，相邻体节受到本次实际伤害向下取整一半的伤害。',
            'en': 'When damaged, adjacent segments take half the actual damage, rounded down.',
        },
        'image_url': '/static/assets/story-trait-icons/adjacent.svg',
    },
    'nourish': {
        'name': {'zh': '滋养', 'en': 'Nourish'},
        'description': {
            'zh': 'H低于40%时触发一次：击杀所有生物；每击杀1个，获得2层力量，并回复其H上限的H。',
            'en': 'Once below 40% H, defeat all allies; gain 2 Power and heal their maximum H for each.',
        },
        'image_url': '/static/assets/story-trait-icons/nourish.svg',
    },
    'sturdy': {
        'name': {'zh': '坚固', 'en': 'Sturdy'},
        'description': {
            'zh': '护盾不会自然清空；回合结束时-1层。',
            'en': 'Shield does not clear naturally; lose 1 stack at turn end.',
        },
        'image_url': '/static/assets/story-trait-icons/sturdy.svg',
    },
    'summon_after_death': {
        'name': {'zh': '死后召唤', 'en': 'Death Summon'},
        'description': {
            'zh': '死亡后召唤1只初始行动为“射击”的黄蜂，并使其获得4层凋萎。',
            'en': 'On death, summon a Wasp starting with Shot and give it 4 Wither.',
        },
        'image_url': '/static/assets/story-trait-icons/summon-after-death.svg',
    },
    'swell': {
        'name': {'zh': '胀大', 'en': 'Swell'},
        'description': {
            'zh': '每次受到攻击时，获得1层暂时力量。',
            'en': 'Gain 1 Temporary Power whenever attacked.',
        },
        'image_url': '/static/assets/story-trait-icons/swell.svg',
    },
    'miracle': {
        'name': {'zh': '奇迹', 'en': 'Miracle'},
        'description': {
            'zh': '玩家打出第2张牌前，消耗1次并获得1层闪避。',
            'en': 'Before the player plays their second card, spend 1 use to gain 1 Evade.',
        },
        'image_url': '/static/assets/story-trait-icons/miracle.svg',
    },
    'bandage': {
        'name': {'zh': '绷带', 'en': 'Bandage'},
        'description': {
            'zh': '首次受到致命伤害时保留1H，获得1回合无敌，并将下一次行动改为狂乱攻击。',
            'en': 'The first lethal hit leaves 1 H, grants Invincibility for one turn, and changes the next action to Frenzied Strike.',
        },
        'image_url': '/static/assets/status-icons/bandage.svg',
    },
    'chaos': {
        'name': {'zh': '紊乱', 'en': 'Chaos'},
        'description': {
            'zh': '受到攻击后，随机切换为另一个意图。',
            'en': 'After being attacked, switch to a different random intent.',
        },
        'image_url': '/static/assets/story-trait-icons/chaos.svg',
    },
    'shelter': {
        'name': {'zh': '庇护', 'en': 'Shelter'},
        'description': {
            'zh': '回合结束时，若本回合未受到实际伤害，使所有生物获得等同于层数的护盾。',
            'en': 'At turn end, if undamaged this turn, all enemies gain Shield equal to its stacks.',
        },
        'image_url': '/static/assets/story-trait-icons/shelter.svg',
    },
    'frenzied': {
        'name': {'zh': '狂暴', 'en': 'Frenzied'},
        'description': {
            'zh': '根据层数改变行动或召唤效果。',
            'en': 'Changes actions or summons according to its stacks.',
        },
        'image_url': '/static/assets/story-trait-icons/frenzied.svg',
    },
    'hidden': {
        'name': {'zh': '隐形', 'en': 'Hidden'},
        'description': {
            'zh': '单次受到的伤害最多为1；回合结束时-1层。',
            'en': 'Take at most 1 damage per hit; lose 1 stack at turn end.',
        },
        'image_url': '/static/assets/story-trait-icons/hidden.svg',
    },
    'turn_shield': {
        'name': {'zh': '回合护盾', 'en': 'Turn Shield'},
        'description': {
            'zh': '回合开始时获得等同于层数的护盾。',
            'en': 'At turn start, gain Shield equal to its stacks.',
        },
        'image_url': '/static/assets/story-trait-icons/turn-shield-turns.svg',
    },
    'charging_up': {
        'name': {'zh': '蓄力', 'en': 'Charging Up'},
        'description': {
            'zh': '下一次攻击伤害增加等同于层数的数值，随后清空。',
            'en': 'The next attack gains damage equal to its stacks, then clears it.',
        },
        'image_url': '/static/assets/story-trait-icons/charging-up.svg',
    },
    'charged': {
        'name': {'zh': '带电', 'en': 'Charged'},
        'description': {
            'zh': '受到攻击时，使玩家所有手牌获得等同于层数的电荷。',
            'en': 'When attacked, add Charge equal to its stacks to every card in the player hand.',
        },
        'image_url': '/static/assets/story-trait-icons/charged.svg',
    },
    'proliferation': {
        'name': {'zh': '增生', 'en': 'Proliferation'},
        'description': {
            'zh': '有其他生物死亡时，回复所有生物等同于层数的H，使其获得等同于层数的护盾和1层坚固。',
            'en': 'When another enemy dies, heal all enemies and grant them Shield equal to its stacks, plus 1 Sturdy.',
        },
        'image_url': '/static/assets/story-trait-icons/proliferation.svg',
    },
    'regeneration': {
        'name': {'zh': '再生', 'en': 'Regeneration'},
        'description': {
            'zh': '回合开始时，回复等同于层数的H。',
            'en': 'At turn start, heal H equal to its stacks.',
        },
        'image_url': '/static/assets/status-icons/turn_heal.svg',
    },
    'vampire': {
        'name': {'zh': '吸血', 'en': 'Vampire'},
        'description': {
            'zh': '造成生命值伤害时，回复等同于实际伤害乘以层数的H。',
            'en': 'After dealing H damage, heal for actual damage multiplied by its stacks.',
        },
        'image_url': '/static/assets/story-trait-icons/vampire.svg',
    },
    'bloodthirsty': {
        'name': {'zh': '嗜血', 'en': 'Bloodthirsty'},
        'description': {
            'zh': '每次造成生命值伤害后，获得1层力量。',
            'en': 'Gain 1 Power whenever this deals H damage.',
        },
        'image_url': '/static/assets/story-trait-icons/bloodthirsty.svg',
    },
    'limb_survival': {
        'name': {'zh': '断臂求生', 'en': 'Surviving with a Lost Limb'},
        'description': {
            'zh': 'H低于30%时触发断臂，最多5次。',
            'en': 'Use Severed Limb below 30% H, up to 5 times.',
        },
        'image_url': '/static/assets/story-trait-icons/surviving-with-a-lost-limb.svg',
    },
    'yggdrasil_power': {
        'name': {'zh': '世界树之力', 'en': 'Power of Yggdrasil'},
        'description': {
            'zh': '首次死亡时，跳过1次行动后以满H复活，并获得1回合无敌。',
            'en': 'On the first death, revive at full H after skipping one action and become invincible for one round.',
        },
        'image_url': '/static/assets/story-trait-icons/the-power-of-yggdrasil.svg',
    },
    'brittle': {
        'name': {'zh': '易碎', 'en': 'Brittle'},
        'description': {
            'zh': '若并非因爆裂死亡，死后召唤的生物H减半，并获得1层眩晕。',
            'en': 'If not defeated by Burst, its death summon has half H and gains 1 Stun.',
        },
        'image_url': '/static/assets/story-trait-icons/brittle.svg',
    },
}


STORY_BLESSINGS = {
    'max_health': {
        'name': {'zh': '', 'en': ''},
        'description': {'zh': '最大生命值+15', 'en': 'Gain 15 maximum H'},
        'script': 'gain_max_health',
        'amount': 15,
        'order': 1,
    },
    'rare_card': {
        'name': {'zh': '', 'en': ''},
        'description': {'zh': '获得随机1张稀有牌', 'en': 'Gain 1 random Rare card'},
        'script': 'gain_random_rare_card',
        'amount': 1,
        'order': 2,
    },
    'gold': {
        'name': {'zh': '', 'en': ''},
        'description': {'zh': '获得100G', 'en': 'Gain 100 G'},
        'script': 'gain_gold',
        'amount': 100,
        'order': 3,
    },
    'relic_and_fatigue': {
        'name': {'zh': '', 'en': ''},
        'description': {'zh': '获得随机1个天赋，将1张疲劳加入牌组', 'en': 'Gain 1 random talent and add 1 Fatigued to your deck'},
        'script': 'gain_relic_and_fatigue',
        'amount': 1,
        'order': 4,
    },
    'transform_card': {
        'name': {'zh': '', 'en': ''},
        'description': {'zh': '变化1张牌', 'en': 'Transform 1 card'},
        'script': 'transform_card',
        'selection': 'deck_card',
        'order': 5,
    },
    'double_card_reward': {
        'name': {'zh': '', 'en': ''},
        'description': {'zh': '获得2次卡牌奖励', 'en': 'Gain 2 card rewards'},
        'script': 'card_rewards',
        'amount': 2,
        'order': 6,
    },
    'remove_card': {
        'name': {'zh': '', 'en': ''},
        'description': {'zh': '删除1张牌', 'en': 'Remove 1 card'},
        'script': 'remove_card',
        'selection': 'deck_card',
        'order': 7,
    },
    'wealth_and_basics': {
        'name': {'zh': '', 'en': ''},
        'description': {'zh': '获得250G，将1张基本和1张玫瑰加入牌组', 'en': 'Gain 250 G and add 1 Basic and 1 Rose to your deck'},
        'script': 'wealth_and_basics',
        'amount': 250,
        'order': 8,
    },
}


def _story_card_description(value):
    if isinstance(value, dict):
        return {
            key: _story_card_description(text)
            for key, text in value.items()
        }
    if not isinstance(value, str):
        return value
    text = value.rstrip()
    while text.endswith(('。', '.')):
        text = text[:-1].rstrip()
    return text


def _card(
    source_card_id,
    zh,
    en,
    cost_e,
    card_type,
    rarity,
    description,
    *,
    cost_m=0,
    effects=(),
    upgrade=None,
    tags=(),
    target=None,
    owner='primary',
    flavor='',
    script=None,
):
    description = _story_card_description(description)
    definition = {
        'source_card_id': source_card_id,
        'name': {'zh': zh, 'en': en},
        'type': card_type,
        'rarity': rarity,
        'owner': owner,
        'cost_e': cost_e,
        'cost_m': cost_m,
        'description': {'zh': description, 'en': description},
        'effects': tuple(effects),
        'tags': tuple(tags),
        'target': target or ('enemy' if card_type in ('thorn', 'guard') else 'self'),
    }
    if flavor:
        definition['flavor'] = {'zh': flavor, 'en': flavor}
    if upgrade:
        normalized_upgrade = deepcopy(upgrade)
        if 'description' in normalized_upgrade:
            normalized_upgrade['description'] = _story_card_description(
                normalized_upgrade['description']
            )
        definition['upgrade'] = normalized_upgrade
    if script:
        definition['script'] = script
    return definition


def _effect(effect_type, amount=0, **values):
    return {'type': effect_type, 'amount': amount, **values}


STORY_CARDS = {
    'basic': _card('Basic', '基本', 'Basic', 1, 'thorn', 'primary',
                   '对目标造成6D。', effects=(_effect('damage', 6),),
                   upgrade={'description': {'zh': '对目标造成9D。', 'en': 'Deal 9 D.'},
                            'effects': (_effect('damage', 9),)}),
    'rose': _card('Rose', '玫瑰', 'Rose', 1, 'bloom', 'primary',
                  '获得5层护盾。', effects=(_effect('shield', 5),),
                  upgrade={'description': {'zh': '获得8层护盾。', 'en': 'Gain 8 Shield.'},
                           'effects': (_effect('shield', 8),)}),
    'amulet': _card('Amulet', '护身符', 'Amulet', 2, 'thorn', 'primary',
                    '对目标造成16D；主动丢弃自己1张其他手牌。',
                    effects=(_effect('damage', 16), _effect('active_discard', 1, exact=True)),
                    upgrade={'description': {'zh': '对目标造成20D；主动丢弃自己至多1张其他手牌。', 'en': 'Deal 20 D; actively discard up to 1 other card.'},
                             'effects': (_effect('damage', 20), _effect('active_discard', 1, exact=False))}),
    'enchanted_amulet': _card(
        None,
        '附魔护身符',
        'Enchanted Amulet',
        1,
        'thorn',
        'super',
        '对目标造成20D；主动丢弃自己至多2张其他手牌，然后抽等量的牌。',
        effects=(
            _effect('damage', 20),
            _effect('active_discard', 2, exact=False),
            _effect('draw_selected', 0),
        ),
        upgrade={
            'description': {
                'zh': '对目标造成25D；主动丢弃自己至多3张其他手牌，然后抽等量的牌。',
                'en': 'Deal 25 D; actively discard up to 3 other cards, then draw that many.',
            },
            'effects': (
                _effect('damage', 25),
                _effect('active_discard', 3, exact=False),
                _effect('draw_selected', 0),
            ),
        },
    ),
    'bone': _card('Bone', '骨头', 'Bone', 1, 'thorn', 'common',
                  '对目标造成5D；获得5层护盾。',
                  effects=(_effect('damage', 5), _effect('shield', 5)),
                  upgrade={'description': {'zh': '对目标造成7D；获得7层护盾。', 'en': 'Deal 7 D; gain 7 Shield.'},
                           'effects': (_effect('damage', 7), _effect('shield', 7))}),
    'coffee': _card('Coffee', '咖啡', 'Coffee', 1, 'bloom', 'rare',
                    '回复自己3E。', effects=(_effect('elixir', 3),), tags=('exile',),
                    owner='neutral', upgrade={'cost_e': 0}),
    'bur': _card('Bur', '刺果', 'Bur', 1, 'thorn', 'common',
                 '对目标造成6D，并施加1层易伤。',
                 effects=(_effect('damage', 6), _effect('status', 1, status='vulnerable')),
                 upgrade={'description': {'zh': '对目标造成8D，并施加2层易伤。', 'en': 'Deal 8 D and apply 2 Vulnerable.'},
                          'effects': (_effect('damage', 8), _effect('status', 2, status='vulnerable'))}),
    'torch': _card('Torch', '火把', 'Torch', 1, 'thorn', 'common',
                   '对目标造成9D；主动丢弃自己1张其他手牌，然后抽1张牌。',
                   effects=(_effect('damage', 9), _effect('active_discard', 1, exact=True), _effect('draw', 1)),
                   upgrade={'description': {'zh': '对目标造成11D；主动丢弃自己1张其他手牌，然后抽2张牌。', 'en': 'Deal 11 D; actively discard 1 other card, then draw 2.'},
                            'effects': (_effect('damage', 11), _effect('active_discard', 1, exact=True), _effect('draw', 2))}),
    'antibody': _card('Antibody', '抗体', 'Antibody', 1, 'bloom', 'common',
                      '对目标施加1层易伤，然后抽等同于其易伤层数的牌。',
                      effects=(_effect('status', 1, status='vulnerable'), _effect('draw_target_status', status='vulnerable')),
                      target='enemy',
                      upgrade={'description': {'zh': '对目标施加2层易伤，然后抽等同于其易伤层数的牌。', 'en': 'Apply 2 Vulnerable, then draw that many cards.'},
                               'effects': (_effect('status', 2, status='vulnerable'), _effect('draw_target_status', status='vulnerable'))}),
    'rock': _card('Rock', '岩石', 'Rock', 1, 'thorn', 'common',
                  '对目标造成8D，并施加1层虚弱。',
                  effects=(_effect('damage', 8), _effect('status', 1, status='weak')),
                  upgrade={'description': {'zh': '对目标造成11D，并施加1层虚弱。', 'en': 'Deal 11 D and apply 1 Weak.'},
                           'effects': (_effect('damage', 11), _effect('status', 1, status='weak'))}),
    'triangle': _card('Triangle', '三角形', 'Triangle', 1, 'thorn', 'rare',
                      '对目标造成3D；获得1层力量。',
                      effects=(_effect('damage', 3), _effect('power', 1)),
                      upgrade={'description': {'zh': '对目标造成3D；获得1层力量；本局第一次使用时额外获得1层力量。', 'en': 'Deal 3 D; gain 1 Power, plus 1 the first time.'},
                               'effects': (_effect('damage', 3), _effect('power', 1), _effect('first_use_power', 1))}),
    'sand': _card('Sand', '沙子', 'Sand', 1, 'thorn', 'ultra',
                  '对目标造成1D×5。', effects=(_effect('damage', 1, hits=5),),
                  upgrade={'description': {'zh': '对目标造成1D×7。', 'en': 'Deal 1 D 7 times.'},
                           'effects': (_effect('damage', 1, hits=7),)}),
    'shell': _card('Shell', '贝壳', 'Shell', 2, 'root', 'ultra',
                   '回合开始时获得5层护盾。', effects=(_effect('equipment', 5, script='start_shield'),),
                   target='self', upgrade={'cost_e': 1}),
    'lightning': _card('Lightning', '闪电', 'Lightning', 1, 'thorn', 'common',
                       '对所有生物造成3D×2。', tags=('wide',),
                       effects=(_effect('damage', 3, hits=2),),
                       upgrade={'description': {'zh': '对所有生物造成5D×2。', 'en': 'Deal 5 D twice to all creatures.'},
                                'effects': (_effect('damage', 5, hits=2),)}),
    'magic_torch': _card('Magic Torch', '魔法火把', 'Magic Torch', 2, 'bloom', 'ultra',
                         '主动丢弃全部其他手牌，每丢弃1张获得4层护盾。',
                         effects=(_effect('active_discard_all'), _effect('shield_selected', 4)),
                         upgrade={'description': {'zh': '主动丢弃全部其他手牌，每丢弃1张获得6层护盾。', 'en': 'Actively discard your other hand; gain 6 Shield per card.'},
                                  'effects': (_effect('active_discard_all'), _effect('shield_selected', 6))}),
    'sponge': _card('Sponge', '海绵', 'Sponge', 1, 'root', 'rare',
                    '目标受到伤害时，改为获得等同于伤害向上取整一半的中毒。',
                    target='self', effects=(_effect('equipment', script='sponge'),),
                    upgrade={'cost_e': 0}),
    'mimic': _card('Mimic', '拟态', 'Mimic', 0, 'bloom', 'ultra',
                   '选择自己1张其他手牌，将其复制加入手牌。',
                   owner='neutral', tags=('exile',), effects=(_effect('copy_hand_card', 1),),
                   upgrade={'description': {'zh': '选择自己1张其他手牌，将其带有迅捷1的复制加入手牌。', 'en': 'Copy another card in hand with Swift 1.'},
                            'effects': (_effect('copy_hand_card', 1, swift=1),)}),
    'light': _card('Light', '轻', 'Light', 0, 'thorn', 'ultra',
                   '对目标造成3D×2；若此牌无放逐，将1张带有放逐的复制洗入抽牌堆。',
                   effects=(_effect('damage', 3, hits=2),), script='light_sprout',
                   upgrade={
                       'description': {
                           'zh': '对目标造成4D×2；若此牌无放逐，将1张带有放逐的复制洗入抽牌堆。',
                           'en': 'Deal 4 D twice; if this has no Exile, shuffle an Exile copy into the draw pile.',
                       },
                       'effects': (_effect('damage', 4, hits=2),),
                   }),
    'missile': _card('Missile', '导弹', 'Missile', 1, 'thorn', 'rare',
                     '对目标造成10D；抽1张牌。', tags=('ready',),
                     effects=(_effect('damage', 10), _effect('draw', 1)),
                     upgrade={'description': {'zh': '对目标造成12D；抽2张牌。', 'en': 'Deal 12 D; draw 2.'},
                              'effects': (_effect('damage', 12), _effect('draw', 2))}),
    'antler': _card('Antler', '角骨', 'Antler', 1, 'thorn', 'rare',
                    '目标每有1种状态，对其造成6D一次。',
                    effects=(_effect('damage_per_status', 6, base_hits=0),),
                    upgrade={'description': {'zh': '对目标造成6D；目标每有1种状态，额外造成6D一次。', 'en': 'Deal 6 D, plus once per target status.'},
                             'effects': (_effect('damage_per_status', 6, base_hits=1),)}),
    'stinger': _card('Stinger', '刺', 'Stinger', 3, 'thorn', 'rare',
                     '对目标造成32D。', tags=('precise',), effects=(_effect('damage', 32),),
                     upgrade={'description': {'zh': '对目标造成44D。', 'en': 'Deal 44 D.'},
                              'effects': (_effect('damage', 44),)}),
    'fries': _card('Fries', '薯条', 'Fries', 2, 'bloom', 'rare',
                   '获得14层护盾；主动丢弃自己1张其他手牌。',
                   effects=(_effect('shield', 14), _effect('active_discard', 1, exact=True)),
                   upgrade={'description': {'zh': '获得18层护盾；主动丢弃自己至多1张其他手牌，然后抽1张牌。', 'en': 'Gain 18 Shield; actively discard up to 1 other card, then draw 1.'},
                            'effects': (_effect('shield', 18), _effect('active_discard', 1, exact=False), _effect('draw', 1))}),
    'heavy': _card('Heavy', '重', 'Heavy', 3, 'thorn', 'ultra',
                   '对目标造成26D；此牌受到的力量加成变为4倍。',
                   effects=(_effect('damage', 26, power_scale=4),),
                   upgrade={'description': {'zh': '对目标造成30D；此牌受到的力量加成变为6倍。', 'en': 'Deal 30 D; Power applies 6 times.'},
                            'effects': (_effect('damage', 30, power_scale=6),)}),
    'disc': _card('Disc', '圆盘', 'Disc', 2, 'bloom', 'rare',
                  '本回合受到的物理伤害向下取整减半。',
                  effects=(_effect('temporary_effect', script='disc'),),
                  upgrade={'description': {'zh': '本回合受到的物理伤害向下取整减半；获得5层护盾。', 'en': 'Halve physical damage this turn; gain 5 Shield.'},
                           'effects': (_effect('temporary_effect', script='disc'), _effect('shield', 5))}),
    'salt': _card('Salt', '盐', 'Salt', 1, 'bloom', 'rare',
                  '获得3层护盾；将下一次受到的实际伤害等量返还给伤害来源。',
                  effects=(_effect('shield', 3), _effect('salt', 1)),
                  upgrade={
                      'description': {
                          'zh': '获得6层护盾；将下一次受到的实际伤害等量返还给伤害来源。',
                          'en': 'Gain 6 Shield; return the next actual damage taken to its source.',
                      },
                      'effects': (_effect('shield', 6), _effect('salt', 1)),
                  }),
    'magic_shell': _card('Magic Shell', '魔法贝壳', 'Magic Shell', 1, 'bloom', 'rare',
                         '抽2张牌；获得4层护盾。',
                         effects=(_effect('draw', 2), _effect('shield', 4)),
                         upgrade={'description': {'zh': '抽3张牌；获得4层护盾。', 'en': 'Draw 3; gain 4 Shield.'},
                                  'effects': (_effect('draw', 3), _effect('shield', 4))}),
    'pearl': _card('Pearl', '珍珠', 'Pearl', 2, 'root', 'ultra',
        '每主动丢弃1张牌，对随机生物造成3D。',
                   effects=(_effect('equipment', script='pearl'),), target='self',
                   upgrade={'cost_e': 1}),
    'crystal_leaf': _card('Crystal Leaf', '水晶叶', 'Crystal Leaf', 3, 'root', 'ultra',
                           '回合开始时获得2层力量。',
                          effects=(_effect('equipment', 2, script='start_power'),), target='self',
                          upgrade={'cost_e': 2}),
    'magic_crystal_leaf': _card('Magic Crystal Leaf', '魔法水晶叶', 'Magic Crystal Leaf', 2, 'root', 'rare',
                                '获得3层力量。', effects=(_effect('power', 3),),
                                upgrade={'description': {'zh': '获得5层力量。', 'en': 'Gain 5 Power.'},
                                         'effects': (_effect('power', 5),)}),
    'magic_pearl': _card('Magic Pearl', '魔法珍珠', 'Magic Pearl', 2, 'root', 'ultra',
                         '每主动丢弃1张牌，获得2层护盾。',
                         effects=(_effect('equipment', 2, script='magic_pearl'),), target='self',
                         upgrade={'description': {'zh': '每主动丢弃1张牌，获得3层护盾。', 'en': 'Whenever you actively discard a card, gain 3 Shield.'},
                                  'effects': (_effect('equipment', 3, script='magic_pearl'),)}),
    'magic_acid': _card('Magic Acid', '魔法酸', 'Magic Acid', 0, 'bloom', 'rare',
                        '主动丢弃自己任意张其他手牌，然后抽等量的牌。',
                        effects=(_effect('active_discard', 99, exact=False), _effect('draw_selected', 0)),
                        upgrade={'description': {'zh': '主动丢弃自己任意张其他手牌，然后抽丢弃数量+1张牌。', 'en': 'Actively discard any number of other cards, then draw that many plus 1.'},
                                 'effects': (_effect('active_discard', 99, exact=False), _effect('draw_selected', 1))}),
    'azalea': _card('Azalea', '杜鹃花', 'Azalea', 1, 'bloom', 'common',
                    '获得5层护盾；被主动丢弃时获得3层护盾。',
                    effects=(_effect('shield', 5),), script='azalea',
                    upgrade={'description': {'zh': '获得7层护盾；被主动丢弃时获得4层护盾。', 'en': 'Gain 7 Shield; when actively discarded, gain 4 Shield.'},
                             'effects': (_effect('shield', 7),), 'script': 'azalea_plus'}),
    'fusion': _card('Fusion', '聚变', 'Fusion', 1, 'bloom', 'ultra',
                    '本回合下一次攻击伤害变为2倍。',
                    owner='neutral', tags=('exile',), effects=(_effect('next_attack_multiplier', 2),),
                    upgrade={'description': {'zh': '本回合下一次攻击伤害变为3倍。', 'en': 'Your next attack damage this turn is tripled.'},
                             'effects': (_effect('next_attack_multiplier', 3),)}),
    'chromosome': _card('Chromosome', '染色体', 'Chromosome', 1, 'bloom', 'rare',
                        '获得7层护盾；抽1张牌。',
                        effects=(_effect('shield', 7), _effect('draw', 1)),
                        upgrade={'description': {'zh': '获得7层护盾；抽1张牌，然后将弃牌堆1张牌置于抽牌堆顶。', 'en': 'Gain 7 Shield; draw 1, then put a discard on top.'},
                                 'effects': (_effect('shield', 7), _effect('draw', 1), _effect('discard_to_draw_top', 1))}),
    'dna': _card('DNA', 'DNA', 'DNA', 1, 'root', 'rare',
                 '获得2层耐力。', effects=(_effect('status_self', 2, status='endurance'),),
                 upgrade={'description': {'zh': '获得3层耐力。', 'en': 'Gain 3 Endurance.'},
                          'effects': (_effect('status_self', 3, status='endurance'),)}),
    'moon_rock': _card('Moon Rock', '月石', 'Moon Rock', 2, 'bloom', 'rare',
                       '获得30层护盾；失去2层力量。',
                       effects=(_effect('shield', 30), _effect('power', -2)),
                       upgrade={'description': {'zh': '获得35层护盾；失去1层力量。', 'en': 'Gain 35 Shield; lose 1 Power.'},
                                'effects': (_effect('shield', 35), _effect('power', -1))}),
    'ice': _card('Ice', '冰', 'Ice', 1, 'bloom', 'rare',
                 '获得13层护盾，然后此牌获得的护盾-5。',
                 effects=(_effect('decaying_shield', 13, decay=5),),
                 upgrade={'description': {'zh': '获得16层护盾，然后此牌获得的护盾-5。', 'en': 'Gain 16 Shield; this card loses 5 Shield value.'},
                          'effects': (_effect('decaying_shield', 16, decay=5),)}),
    'soul_splitter': _card('Soul Splitter', '灵魂分裂', 'Soul Splitter', 3, 'root', 'ultra',
                           '每个正常回合结束后，额外进行1个只能打出1张牌的回合。',
                           effects=(_effect('equipment', 1, script='soul_splitter'),), target='self',
                           upgrade={'description': {'zh': '每个正常回合结束后，额外进行1个只能打出2张牌的回合。', 'en': 'After each normal turn, take an extra turn limited to 2 cards.'},
                                    'effects': (_effect('equipment', 2, script='soul_splitter'),)}),
    'cutter': _card('Cutter', '锯齿', 'Cutter', 1, 'thorn', 'common',
                     '对目标造成等同于自己护盾层数的D。',
                     effects=(_effect('damage_from_shield', 1),),
                     upgrade={'description': {'zh': '对目标造成(自己护盾层数+4)D。', 'en': 'Deal D equal to your Shield plus 4.'},
                              'effects': (_effect('damage_from_shield', 1, bonus=4),)}),
    'powder': _card('Powder', '粉末', 'Powder', 2, 'root', 'rare',
                    '每回合多回复1E。', effects=(_effect('equipment', 1, script='turn_elixir'),), target='self',
                    upgrade={'cost_e': 1}),
    'rna': _card('RNA', 'RNA', 'RNA', 1, 'root', 'rare',
                 '每次对生物施加易伤时，获得4层护盾。',
                 effects=(_effect('equipment', 4, script='vulnerable_shield'),), target='self',
                 upgrade={'description': {'zh': '每次对生物施加易伤时，获得6层护盾。', 'en': 'When applying Vulnerable, gain 6 Shield.'},
                          'effects': (_effect('equipment', 6, script='vulnerable_shield'),)}),
    'nuke': _card('Nuke', '核弹', 'Nuke', 'X', 'thorn', 'rare',
                  '消耗自己所有E；每消耗1E，对目标造成9D一次。',
                  effects=(_effect('damage_per_elixir', 9),),
                  upgrade={'description': {'zh': '消耗自己所有E；每消耗1E，对目标造成13D一次。', 'en': 'Spend all E; deal 13 D once per E.'},
                           'effects': (_effect('damage_per_elixir', 13),)}),
    'rmb': _card('RMB', '人民币', 'RMB', 2, 'root', 'ultra',
                 '战斗胜利时获得15G。', owner='neutral',
                 effects=(_effect('equipment', 15, script='victory_gold'),), target='self',
                 upgrade={'description': {'zh': '战斗胜利时获得25G。', 'en': 'Gain 25 G after winning combat.'},
                          'effects': (_effect('equipment', 25, script='victory_gold'),)}),
    'magic_bur': _card('Magic Bur', '魔法刺果', 'Magic Bur', 1, 'bloom', 'rare',
                        '对目标施加1层易伤；获得其易伤层数×3的护盾。',
                        target='enemy', tags=('exile',),
                       effects=(_effect('status', 1, status='vulnerable'), _effect('shield_from_target_status', 3, status='vulnerable')),
                       upgrade={'description': {'zh': '对目标施加2层易伤；获得其易伤层数×3的护盾。', 'en': 'Apply 2 Vulnerable; gain triple its stacks as Shield.'},
                                'effects': (_effect('status', 2, status='vulnerable'), _effect('shield_from_target_status', 3, status='vulnerable'))}),
    'fission': _card('Fission', '裂变', 'Fission', 1, 'bloom', 'ultra',
                     '本回合下一张非裂变技能牌打出2次，且不额外消耗E。',
                     owner='neutral', effects=(_effect('next_skill_repeats', 1),),
                     upgrade={'description': {'zh': '本回合下一张非裂变技能牌打出3次，且不额外消耗E。', 'en': 'Play your next non-Fission skill 3 times at no extra E cost.'},
                              'effects': (_effect('next_skill_repeats', 2),)}),
    'cotton': _card('Cotton', '棉花', 'Cotton', 2, 'bloom', 'ultra',
                    '获得10层护盾；本回合手中所有技能牌E花费-1，最低为1E。',
                    owner='neutral', effects=(_effect('shield', 10), _effect('temporary_cost_down', 1, scope='bloom', minimum=1)),
                    upgrade={'description': {'zh': '获得10层护盾；本回合所有手牌E花费-1，最低为1E。', 'en': 'Gain 10 Shield; all cards cost 1 less E this turn, minimum 1.'},
                             'effects': (_effect('shield', 10), _effect('temporary_cost_down', 1, scope='all', minimum=1))}),
    'startled': _card(None, '惊吓', 'Startled', 0, 'curse', 'special',
                      '回合结束时若在手牌中，获得1层易伤。', tags=('unplayable',),
                      effects=(), script='startled'),
    'fatigued': _card(None, '疲劳', 'Fatigued', 0, 'curse', 'special',
                      '无法打出；回合结束时若在手牌中，将其放逐。',
                      tags=('unplayable', 'void'), effects=()),
    'slimed': _card(None, '黏着', 'Slimed', 1, 'infect', 'special',
                    '抽到时随机丢弃自己1张其他手牌；放逐。', tags=('exile',),
                    effects=(), script='slimed'),
    'injury': _card(None, '受伤', 'Injury', 0, 'curse', 'special',
                    '无法打出。', tags=('unplayable',), effects=()),
    'unrelenting': _card(None, '无情', 'Unrelenting', 0, 'curse', 'special',
                        '回合结束时若在手牌中，获得1层虚弱。', tags=('unplayable',),
                        effects=(), script='unrelenting'),
    'fragment': _card('Fragment', '碎片', 'Fragment', 0, 'bloom', 'common',
                      '获得1层力量。', tags=('exile',), effects=(_effect('power', 1),),
                      upgrade={
                          'description': {'zh': '丢弃自己1张其他手牌；获得2层力量。', 'en': 'Discard another card; gain 2 Power.'},
                          'effects': (_effect('active_discard', 1, exact=True), _effect('power', 2)),
                      }),
    'rice': _card('Rice', '米', 'Rice', 0, 'thorn', 'rare',
                  '对目标造成6D，然后将此牌置于抽牌堆顶。',
                  owner='neutral', effects=(_effect('damage', 6),), script='return_draw_top',
                  upgrade={'description': {'zh': '对目标造成9D，然后将此牌置于抽牌堆顶。', 'en': 'Deal 9 D, then put this on top of the draw pile.'},
                           'effects': (_effect('damage', 9),)}),
    'glass': _card('Glass', '玻璃', 'Glass', 0, 'thorn', 'rare',
                   '对目标造成3D；下回合开始时将1张复制加入手牌。',
                   owner='neutral', effects=(_effect('damage', 3), _effect('delayed_copy', 1)),
                   upgrade={'description': {'zh': '对目标造成5D；下回合开始时将1张复制加入手牌。', 'en': 'Deal 5 D; add a copy next turn.'},
                            'effects': (_effect('damage', 5), _effect('delayed_copy', 1))}),
    'dust': _card('Dust', '灰尘', 'Dust', 0, 'thorn', 'rare',
                  '对目标造成3D；获得3层护盾。',
                  owner='neutral', effects=(_effect('damage', 3), _effect('shield', 3)),
                  upgrade={'description': {'zh': '对目标造成4D；获得4层护盾。', 'en': 'Deal 4 D; gain 4 Shield.'},
                           'effects': (_effect('damage', 4), _effect('shield', 4))}),
    'leaf': _card('Leaf', '叶子', 'Leaf', 0, 'bloom', 'common',
                  '获得3层护盾。', effects=(_effect('shield', 3),),
                  upgrade={'description': {'zh': '获得5层护盾。', 'en': 'Gain 5 Shield.'},
                           'effects': (_effect('shield', 5),)}),
    'acid': _card('Acid', '酸', 'Acid', 0, 'thorn', 'common',
                  '对目标造成7D；随机主动丢弃自己1张其他手牌。',
                  effects=(_effect('damage', 7), _effect('random_active_discard', 1)),
                  upgrade={'description': {'zh': '对目标造成10D；随机主动丢弃自己1张其他手牌。', 'en': 'Deal 10 D; randomly actively discard another card.'},
                           'effects': (_effect('damage', 10), _effect('random_active_discard', 1))}),
    'pyrite': _card('Pyrite', '黄铁矿', 'Pyrite', 0, 'bloom', 'rare',
                    '回复自己2E；随机主动丢弃自己2张其他手牌。',
                    effects=(_effect('elixir', 2), _effect('random_active_discard', 2, exact=True)),
                    upgrade={'description': {'zh': '回复自己2E；主动丢弃自己2张其他手牌。', 'en': 'Recover 2 E; actively discard 2 other cards.'},
                             'effects': (_effect('elixir', 2), _effect('active_discard', 2, exact=True))}),
    'feather': _card('Feather', '羽毛', 'Feather', 1, 'bloom', 'rare',
                     '抽3张牌。', effects=(_effect('draw', 3),),
                     upgrade={'description': {'zh': '抽4张牌。', 'en': 'Draw 4.'},
                              'effects': (_effect('draw', 4),)}),
    'magic_feather': _card('Magic Feather', '魔法羽毛', 'Magic Feather', 2, 'bloom', 'common',
                           '回复自己等同于当前手牌数向下取整一半的E；本回合无法再抽牌。',
                           effects=(_effect('elixir_from_hand', 0.5), _effect('temporary_effect', script='cannot_draw')),
                           upgrade={'cost_e': 1}),
    'bubble': _card('Bubble', '泡泡', 'Bubble', 0, 'bloom', 'ultra',
                    '抽3张牌。', owner='neutral', tags=('exile',), effects=(_effect('draw', 3),),
                    upgrade={'description': {'zh': '抽4张牌。', 'en': 'Draw 4.'},
                             'effects': (_effect('draw', 4),)}),
    'magic_bubble': _card('Magic Bubble', '魔法泡泡', 'Magic Bubble', 1, 'bloom', 'ultra',
                          '抽牌至手牌上限。', owner='neutral', tags=('exile',),
                          effects=(_effect('draw_to_limit', 0),), upgrade={'cost_e': 0}),
    'mark': _card('Mark', '标记', 'Mark', 2, 'bloom', 'super',
                  '将目标的下一次意图改为眩晕。', owner='neutral', tags=('exile', 'sublime'), target='enemy',
                  effects=(_effect('status', 1, status='stun'),), upgrade={'cost_e': 1}),
    'dandelion_seed': _card('Dandelion', '蒲公英种子', 'Dandelion Seed', 0, 'infect', 'special',
                            '可在休息区种植：永久移除此牌，并获得蒲公英加护。',
                            owner='neutral', tags=('unplayable',), effects=()),
    'yin_yang': _card('Yin-Yang', '阴阳', 'Yin-Yang', 0, 'bloom', 'special',
                      '将自己全部其他手牌洗入抽牌堆，然后抽等同于洗入数量+1的牌。',
                      owner='neutral', tags=('exile',), effects=(_effect('shuffle_hand_redraw', 1),),
                      upgrade={
                          'description': {
                              'zh': '将自己全部其他手牌洗入抽牌堆，然后抽等同于洗入数量+2的牌。',
                              'en': 'Shuffle your other hand into the draw pile, then draw that many plus 2.',
                          },
                          'effects': (_effect('shuffle_hand_redraw', 2),),
                      }),
    'sewage': _card(
        'Sewage',
        '污水',
        'Sewage',
        3,
        'bloom',
        'rare',
        '本回合打出卡牌不消耗E；每打出1张牌，随机主动丢弃自己1张其他手牌。',
        tags=('exile',),
        effects=(_effect('temporary_effect', script='sewage'),),
        upgrade={
            'cost_e': 2,
            'description': {
                'zh': '本回合打出卡牌不消耗E；每打出1张牌，随机主动丢弃自己1张其他手牌。',
                'en': 'Cards cost no E this turn; whenever you play one, randomly actively discard another card.',
            },
        },
    ),
    'mjolnir': _card(
        'Mjolnir', '雷神之锤', 'Mjolnir', 2, 'thorn', 'rare',
        '对目标造成14D；此牌可无限升级。',
        effects=(_effect('damage', 14),),
        upgrade={
            'infinite': True,
            'description': {'zh': '对目标造成18D；此牌可无限升级。', 'en': 'Deal 18 D. This card can be upgraded indefinitely.'},
            'effects': (_effect('damage', 18),),
        },
    ),
    'chilly': _card(
        'Chilly', '辣椒', 'Chilly', 1, 'bloom', 'rare',
        '抽1张牌并获得2层暂时力量；若抽到攻击牌，回复自己1E。',
        effects=(_effect('draw_attack_power', 1, power=2, elixir=1),),
        upgrade={
            'description': {'zh': '抽1张牌并获得3层暂时力量；若抽到攻击牌，回复自己1E。', 'en': 'Draw 1 and gain 3 Temporary Power; if it is an Attack, recover 1 E.'},
            'effects': (_effect('draw_attack_power', 1, power=3, elixir=1),),
        },
    ),
    'jelly': _card(
        'Jelly', '果冻', 'Jelly', 2, 'thorn', 'rare',
        '对目标造成24D；失去2层力量。',
        effects=(_effect('damage', 24), _effect('power', -2)),
        upgrade={
            'description': {'zh': '对目标造成30D；失去2层力量。', 'en': 'Deal 30 D; lose 2 Power.'},
            'effects': (_effect('damage', 30), _effect('power', -2)),
        },
    ),
    'nitro': _card(
        'Nitro', '氮气', 'Nitro', 3, 'bloom', 'ultra',
        '对目标造成10D；结束当前回合并立即进入1个完整的额外回合，额外回合开始时获得3层破损。',
        tags=('exile',), target='enemy',
        effects=(_effect('damage', 10), _effect('immediate_extra_turn', 3)),
        upgrade={
            'description': {'zh': '对目标造成14D；结束当前回合并立即进入1个完整的额外回合，额外回合开始时获得2层破损。', 'en': 'Deal 14 D; end this turn and immediately take a full extra turn, gaining 2 Broken at its start.'},
            'effects': (_effect('damage', 14), _effect('immediate_extra_turn', 2)),
        },
    ),
    'cogwheel': _card(
        'Cogwheel', '齿轮', 'Cogwheel', 1, 'bloom', 'rare',
        '抽2张牌；每抽到1张攻击牌，获得2层暂时力量。',
        effects=(_effect('draw_attack_power', 2, power=2),),
        upgrade={
            'description': {'zh': '抽3张牌；每抽到1张攻击牌，获得2层暂时力量。', 'en': 'Draw 3; gain 2 Temporary Power for each Attack drawn.'},
            'effects': (_effect('draw_attack_power', 3, power=2),),
        },
    ),
    'chloroplast': _card(
        'Chloroplast', '叶绿体', 'Chloroplast', 0, 'bloom', 'rare',
        '获得4层护盾；将1张叶绿体加入弃牌堆。',
        effects=(_effect('shield', 4), _effect('create_discard_copy')),
        upgrade={
            'description': {'zh': '获得6层护盾；将1张已升级的叶绿体加入弃牌堆。', 'en': 'Gain 6 Shield; add an upgraded Chloroplast to the discard pile.'},
            'effects': (_effect('shield', 6), _effect('create_discard_copy')),
        },
    ),
    'beeswax': _card(
        'Beeswax', '蜜蜡', 'Beeswax', 1, 'bloom', 'ultra',
        '获得8层护盾；此牌同时受到力量与耐力加成。',
        effects=(_effect('shield_with_power', 8),),
        upgrade={
            'description': {'zh': '获得11层护盾；此牌同时受到力量与耐力加成。', 'en': 'Gain 11 Shield; both Power and Endurance increase it.'},
            'effects': (_effect('shield_with_power', 11),),
        },
    ),
    'bamboo': _card(
        'Bamboo', '竹子', 'Bamboo', 2, 'bloom', 'ultra',
        '对目标造成8D；打出后，此牌在本次旅程中永久获得3点伤害。',
        tags=('exile',), target='enemy',
        effects=(_effect('damage', 8), _effect('permanent_damage_growth', 3)),
        upgrade={
            'description': {'zh': '对目标造成11D；打出后，此牌在本次旅程中永久获得4点伤害。', 'en': 'Deal 11 D; after playing, this card permanently gains 4 damage for this journey.'},
            'effects': (_effect('damage', 11), _effect('permanent_damage_growth', 4)),
        },
    ),
    'corn': _card(
        'Corn', '玉米', 'Corn', 2, 'thorn', 'rare',
        '对目标造成14D；若本回合主动丢弃过牌，回复自己2E。',
        effects=(_effect('damage', 14), _effect('elixir_if_active_discard', 2)),
        upgrade={
            'description': {'zh': '对目标造成18D；若本回合主动丢弃过牌，回复自己2E。', 'en': 'Deal 18 D; if you actively discarded this turn, recover 2 E.'},
            'effects': (_effect('damage', 18), _effect('elixir_if_active_discard', 2)),
        },
    ),
    'maple': _card(
        'Maple', '枫叶', 'Maple', 1, 'thorn', 'rare',
        '对随机生物造成5D；本回合每主动丢弃2张牌，额外造成1次。',
        target='self', effects=(_effect('random_damage_per_discards', 5, divisor=2),),
        upgrade={
            'description': {'zh': '对随机生物造成7D；本回合每主动丢弃2张牌，额外造成1次。', 'en': 'Deal 7 D to a random creature, plus once per 2 cards actively discarded this turn.'},
            'effects': (_effect('random_damage_per_discards', 7, divisor=2),),
        },
    ),
    'assembler': _card(
        'Assembler', '重构机', 'Assembler', 2, 'bloom', 'ultra',
        '从3张完全随机的牌中选择1张加入手牌；其获得迅捷99、放逐与虚无。',
        owner='neutral', effects=(_effect('choose_random_generated', 3),),
        upgrade={
            'description': {'zh': '从3张完全随机的已升级牌中选择1张加入手牌；其获得迅捷99、放逐与虚无。', 'en': 'Choose 1 of 3 fully random upgraded cards to add to hand with Swift 99, Exile, and Void.'},
            'effects': (_effect('choose_random_generated', 3, upgraded=True),),
        },
    ),
    'redemption_money': _card(
        'Redemption Money', '赎身钱', 'Redemption Money', 0, 'bloom', 'rare',
        '失去5H；选择放逐区1张牌加入手牌，使其获得虚无与放逐。',
        owner='neutral', tags=('exile',),
        effects=(_effect('lose_health', 5), _effect('recover_exiled', 1, exact=True)),
        upgrade={
            'description': {'zh': '失去2H；选择放逐区1张牌加入手牌，使其获得虚无与放逐。', 'en': 'Lose 2 H; return 1 card from exile to hand with Void and Exile.'},
            'effects': (_effect('lose_health', 2), _effect('recover_exiled', 1, exact=True)),
        },
    ),
    'antennae': _card(
        'Antennae', '触角', 'Antennae', 1, 'bloom', 'rare',
        '查看抽牌堆顶5张牌，选择其中2张加入手牌，其余置入弃牌堆。',
        owner='neutral', tags=('exile',), effects=(_effect('inspect_draw_choose', 5, choose=2),),
        upgrade={
            'description': {'zh': '查看抽牌堆顶6张牌，选择其中3张加入手牌，其余置入弃牌堆。', 'en': 'Look at the top 6 cards; put 3 into hand and the rest into discard.'},
            'effects': (_effect('inspect_draw_choose', 6, choose=3),),
        },
    ),
    'sunflower_card': _card(
        'Sunflower', '向日葵', 'Sunflower', 2, 'bloom', 'rare',
        '获得12层护盾与1层坚固。',
        effects=(_effect('shield', 12), _effect('status_self', 1, status='sturdy')),
        upgrade={
            'description': {'zh': '获得18层护盾与1层坚固。', 'en': 'Gain 18 Shield and 1 Sturdy.'},
            'effects': (_effect('shield', 18), _effect('status_self', 1, status='sturdy')),
        },
    ),
    'wind': _card(
        'Wind', '风', 'Wind', 0, 'bloom', 'rare',
        '主动丢弃自己所有当前E花费大于0的其他手牌，然后抽等量的牌。',
        effects=(_effect('active_discard_all', filter='positive_e'), _effect('draw_selected', 0)),
        upgrade={
            'description': {'zh': '主动丢弃自己所有当前E花费大于0的其他手牌，然后抽丢弃数量+1张牌。', 'en': 'Actively discard all other cards costing more than 0 E, then draw that many plus 1.'},
            'effects': (_effect('active_discard_all', filter='positive_e'), _effect('draw_selected', 1)),
        },
    ),
    'ankh': _card(
        'Ankh', '安卡', 'Ankh', 1, 'root', 'rare',
        '回合结束时，最多保留3点剩余E。',
        owner='neutral', effects=(_effect('equipment', 3, script='retain_elixir'),), target='self',
        upgrade={'cost_e': 0},
    ),
    'trident': _card(
        'Trident', '三叉戟', 'Trident', 3, 'root', 'ultra',
        '每抽5张牌，获得1层力量。',
        effects=(_effect('equipment', 5, script='draw_power'),), target='self',
        upgrade={
            'description': {'zh': '每抽4张牌，获得1层力量。', 'en': 'Gain 1 Power for every 4 cards drawn.'},
            'effects': (_effect('equipment', 4, script='draw_power'),),
        },
    ),
    'magic_trident': _card(
        'Magic Trident', '魔法三叉戟', 'Magic Trident', 1, 'thorn', 'ultra',
        '对目标造成(8+本场战斗主动丢弃牌数)D。',
        effects=(_effect('damage_per_active_discard', 8),),
        upgrade={
            'description': {'zh': '对目标造成(12+本场战斗主动丢弃牌数)D。', 'en': 'Deal D equal to 12 plus cards actively discarded this combat.'},
            'effects': (_effect('damage_per_active_discard', 12),),
        },
    ),
    'magic_yin_yang': _card(
        'Magic Yin-Yang', '魔法阴阳', 'Magic Yin-Yang', 0, 'bloom', 'ultra',
        '对调自己的抽牌堆与弃牌堆，然后抽2张牌。',
        owner='neutral', tags=('exile',), effects=(_effect('swap_piles_draw', 2),),
        upgrade={
            'description': {'zh': '对调自己的抽牌堆与弃牌堆，然后抽2张牌；保留。', 'en': 'Swap your draw and discard piles, then draw 2. Retain.'},
            'tags': ('exile', 'retain'),
            'effects': (_effect('swap_piles_draw', 2),),
        },
    ),
    'magic_assembler': _card(
        'Magic Assembler', '魔法重构机', 'Magic Assembler', 1, 'root', 'ultra',
        '自己回合开始时，将1张随机技能牌加入手牌。',
        effects=(_effect('equipment', script='start_random_bloom'),), target='self',
        upgrade={
            'description': {'zh': '自己回合开始时，将1张随机已升级的技能牌加入手牌。', 'en': 'At turn start, add a random upgraded Skill to hand.'},
            'effects': (_effect('equipment', script='start_random_bloom', upgraded=True),),
        },
    ),
    'magic_chilly': _card(
        'Magic Chilly', '魔法辣椒', 'Magic Chilly', 1, 'bloom', 'rare',
        '抽4张牌，然后主动丢弃自己4张手牌；不足则全部丢弃。',
        effects=(_effect('draw_then_discard', 4, discard=4),),
        upgrade={
            'description': {'zh': '抽6张牌，然后主动丢弃自己5张手牌；不足则全部丢弃。', 'en': 'Draw 6, then actively discard 5 cards, or all of them if fewer are available.'},
            'effects': (_effect('draw_then_discard', 6, discard=5),),
        },
    ),
    'mushroom': _card(
        'Mushroom', '蘑菇', 'Mushroom', 2, 'bloom', 'rare',
        '获得30层护盾；下回合开始时获得12层中毒。',
        effects=(_effect('shield', 30), _effect('delayed_player_status', 12, status='poison')),
        upgrade={
            'description': {'zh': '获得30层护盾；下回合开始时获得8层中毒。', 'en': 'Gain 30 Shield; gain 8 Poison at the start of your next turn.'},
            'effects': (_effect('shield', 30), _effect('delayed_player_status', 8, status='poison')),
        },
    ),
    'puppeteer': _card(
        'Puppeteer', '傀儡架台', 'Puppeteer', 0, 'bloom', 'rare',
        '抽3张牌；下回合少抽2张牌。',
        effects=(_effect('draw', 3), _effect('next_turn_draw', -2)),
        upgrade={
            'description': {'zh': '抽3张牌；下回合少抽1张牌。', 'en': 'Draw 3; draw 1 fewer card next turn.'},
            'effects': (_effect('draw', 3), _effect('next_turn_draw', -1)),
        },
    ),
    'seed': _card(
        'Seed', '种子', 'Seed', 3, 'bloom', 'rare',
        '回复自己2E；此牌在本次旅程中永久获得1层迅捷。',
        effects=(_effect('elixir', 2), _effect('permanent_swift', 1)),
        upgrade={
            'cost_e': 2,
            'description': {'zh': '回复自己2E；此牌在本次旅程中永久获得1层迅捷。', 'en': 'Recover 2 E; this card permanently gains 1 Swift for this journey.'},
            'effects': (_effect('elixir', 2), _effect('permanent_swift', 1)),
        },
    ),
    'sand_dust': _card(
        None,
        '沙尘',
        'Sand Dust',
        0,
        'infect',
        'special',
        '无法打出；回合结束时若仍在手牌中，将其放逐。',
        tags=('unplayable', 'void'),
    ),
    'confused': _card(
        None,
        '迷惑',
        'Confused',
        0,
        'infect',
        'special',
        '无法打出。',
        tags=('unplayable',),
    ),
    'static_electricity': _card(
        None,
        '静电',
        'Static Electricity',
        0,
        'infect',
        'special',
        '抽到时，使自己所有手牌获得1层电荷；回合结束时若仍在手牌中，将其放逐。',
        tags=('unplayable', 'void'),
        script='static_electricity',
    ),
    'corruption': _card(
        'Corruption',
        '腐化',
        'Corruption',
        1,
        'curse',
        'special',
        '回合结束时若仍在手牌中，受到3D；打出后放逐。',
        tags=('exile', 'void', 'eternal'),
        effects=(),
        script='corruption',
    ),
}

STORY_CARD_IMAGE_URLS = {
    'confused': '/static/assets/story-card-art/confused.svg',
    'dandelion_seed': '/static/assets/story-card-art/dandelion-seed.svg',
    'enchanted_amulet': '/static/assets/story-card-art/enchanted-amulet.svg',
    'fatigued': '/static/assets/story-card-art/fatigued.svg',
    'injury': '/static/assets/story-card-art/injury.svg',
    'magic_acid': '/static/assets/story-card-art/magic-acid.svg',
    'magic_assembler': '/static/assets/story-card-art/magic-assembler.svg',
    'magic_feather': '/static/assets/story-card-art/magic-feather.svg',
    'magic_shell': '/static/assets/story-card-art/magic-shell.svg',
    'moon_rock': '/static/assets/story-card-art/moon-rock.svg',
    'rmb': '/static/assets/story-card-art/rmb.svg',
    'shell': '/static/assets/story-card-art/shell.svg',
    'sand_dust': '/static/assets/story-card-art/sand-dust.svg',
    'slimed': '/static/assets/story-card-art/slimed.svg',
    'soul_splitter': '/static/assets/story-card-art/soul-splitter.svg',
    'startled': '/static/assets/story-card-art/startled.svg',
    'static_electricity': '/static/assets/story-card-art/static-electricity.svg',
    'unrelenting': '/static/assets/story-card-art/unrelenting.svg',
}

for _card_id, _image_url in STORY_CARD_IMAGE_URLS.items():
    STORY_CARDS[_card_id]['image_url'] = _image_url
    STORY_CARDS[_card_id]['upgraded_image_url'] = _image_url


STORY_REWARD_CARD_IDS = tuple(
    card_id
    for card_id, definition in STORY_CARDS.items()
    if definition['rarity'] in ('common', 'rare', 'ultra')
    and definition['type'] not in ('curse', 'infect')
    and definition.get('owner') == 'primary'
)


STORY_SHOP_CARD_IDS = tuple(
    card_id
    for card_id, definition in STORY_CARDS.items()
    if definition['rarity'] in ('common', 'rare', 'ultra')
    and definition['type'] not in ('curse', 'infect')
)


def _relic(
    zh,
    en,
    description,
    rarity='common',
    script=None,
    amount=0,
    stackable=None,
    shop_excluded=False,
):
    if stackable is None:
        stackable = rarity != 'special'
    return {
        'name': {'zh': zh, 'en': en},
        'description': {'zh': description, 'en': description},
        'rarity': rarity,
        'script': script,
        'amount': amount,
        'stackable': bool(stackable),
        'shop_excluded': bool(shop_excluded),
    }


STORY_RELICS = {
    'energetic': _relic(
        '精力充沛',
        'Energetic',
        '每经过1层，回复4H。',
        rarity='special',
        script='floor_heal',
        amount=4,
    ),
    'ruthless': _relic('无情猛击', 'Ruthless Strike', '战斗开始时获得1层力量。', script='opening_power', amount=1),
    'firm_defense': _relic('坚定防守', 'Firm Defense', '战斗开始时获得1层耐力。', script='opening_endurance', amount=1),
    'fearless_pain': _relic('无惧疼痛', 'Fearless Pain', '每次即将失去H时，失去量-1。', script='flat_damage_reduction', amount=1),
    'circulation': _relic('回转', 'Circulation', '商店购买后会补充货品。', rarity='rare', script='shop_restock', stackable=False),
    'prepared': _relic('未雨绸缪', 'Prepared', '第一回合额外抽2张牌。', script='opening_draw', amount=2),
    'cooldown': _relic('冷却', 'Cooldown', '第一回合可丢弃任意张牌，然后抽等量的牌。', rarity='rare', script='opening_redraw', stackable=False),
    'accumulate': _relic('厚积薄发', 'Accumulate', '第二回合获得5层暂时力量。', rarity='rare', script='round_power', amount=5),
    'opening_lightning': _relic('开幕雷击', 'Opening Lightning', '战斗开始时对所有生物造成9D。', rarity='rare', script='opening_damage', amount=9),
    'solid_barrier': _relic('坚固壁垒', 'Solid Barrier', '本场战斗第一次受伤时回复2E。', rarity='rare', script='first_hit_elixir', amount=2),
    'sharpen': _relic('磨刀', 'Sharpen', '获得时升级2张牌。', rarity='rare', script='gain_upgrade', amount=2),
    'blade': _relic('利刃', 'Blade', '本场战斗第一次攻击时，对目标施加1层易伤。', rarity='rare', script='first_attack_vulnerable', amount=1),
    'steady': _relic('稳扎稳打', 'Steady', '所有基础牌的数值+2。', rarity='rare', script='primary_bonus', amount=2),
    'rich': _relic(
        '富裕',
        'Rich',
        '获得时获得200G。',
        script='gain_gold',
        amount=200,
        shop_excluded=True,
    ),
    'diligent': _relic('勤学', 'Diligent', '每获得1张新牌，回复5H。', script='gain_card_heal', amount=5),
    'greedy': _relic('贪婪', 'Greedy', '休息区可选择获得150G。', rarity='rare', script='rest_gold', amount=150),
    'body_reinforcement': _relic('肉体强化', 'Body Reinforcement', '获得时最大生命值+10，并回复10H。', script='gain_max_health', amount=10),
    'indomitable': _relic('愈挫愈勇', 'Indomitable', '普通战斗失去超过15H时，随机升级1张牌。', rarity='rare', script='loss_upgrade', amount=15),
    'support': _relic('支援', 'Support', '第一回合少抽1张牌；每回合获得3层护盾。', rarity='special', script='support', amount=3),
    'bargaining': _relic('讨价还价', 'Bargaining', '商店价格降低50%。', rarity='rare', script='shop_discount', amount=50, stackable=False),
    'world_tree_leaf': _relic('世界树之叶', 'World Tree Leaf', '本次旅程首次死亡时，清除效果并回复至满H。', rarity='special', script='revive'),
    'dandelion_blessing': _relic('蒲公英加护', 'Dandelion Blessing', '战斗开始时获得7层护盾。', rarity='special', script='opening_shield', amount=7),
    'coward_defense': _relic('懦夫才防', 'Cowardly Defense', '每回合多回复1E；卡牌奖励和商店中不再出现技能牌。', rarity='special', script='boss_no_bloom', amount=1),
    'return_to_origin': _relic('返璞归真', 'Return to Origin', '所有基础牌的基础数值变为2倍。', rarity='special', script='primary_multiplier', amount=2),
    'last_stand': _relic('破釜沉舟', 'Last Stand', '每回合多回复1E；无法回复H。', rarity='special', script='boss_no_heal', amount=1),
    'quantized': _relic('量子化', 'Quantized', '每回合多回复2E；抽到牌时，其E花费随机变为0至3E。', rarity='special', script='quantized_cost', amount=2),
    'dizzy_relic': _relic('眩晕', 'Dizzy', '每回合多回复2E；回合开始时获得1层失明。', rarity='special', script='boss_blind', amount=2),
    'uranium': _relic('铀', 'Uranium', '每回合多回复1E；回合开始时获得4层中毒。', rarity='special', script='boss_poison', amount=1),
    'strive': _relic('奋发图强', 'Strive', '精英与首领战中，每回合多回复1E。', rarity='special', script='elite_boss_elixir', amount=1),
    'gluttony': _relic('暴食', 'Gluttony', '每经过1层，H上限+2。', rarity='special', script='floor_max_health', amount=2),
    'frugal': _relic('节俭', 'Frugal', '每回合多回复1E；经过商店时直接跳过。', rarity='special', script='skip_shop', amount=1),
    'avoid_elite': _relic('避战大怪', 'Avoid the Elite', '每回合多回复1E；精英房改为无奖励的困难普通战斗。', rarity='special', script='avoid_elite', amount=1),
    'grab_every_card': _relic('见牌就抓', 'Grab Every Card', '每回合多回复1E并多抽1张牌；无法跳过卡牌奖励或删除牌。', rarity='special', script='must_take_cards', amount=1),
    'cognitive_bias': _relic('认知偏差', 'Cognitive Bias', '每回合多回复2E；回合结束时使每回合E-1，最低为1E。', rarity='special', script='decaying_elixir', amount=2),
    'pollen_relic': _relic('花粉', 'Pollen', '每回合多回复1E；回合开始时获得1层破损。', rarity='special', script='boss_broken', amount=1),
    'frenzy_relic': _relic('狂乱', 'Frenzy', '造成的伤害变为2倍；手中有攻击牌时，只能打出攻击牌。', rarity='special', script='boss_frenzy', amount=2),
    'web_relic': _relic('网', 'Web', '每回合多回复1E；每回合完成初始抽牌后无法再抽牌。', rarity='special', script='boss_no_extra_draw', amount=1),
    'first_strike': _relic('先发制人', 'First Strike', '第一回合额外获得2E并多抽2张牌。', rarity='special', script='first_round_boost', amount=2),
    'fast_learning': _relic('快速学习', 'Fast Learning', '每次升级牌时，额外升级1张牌。', rarity='special', script='extra_upgrade', amount=1),
    'peaceful_mind': _relic('心如止水', 'Peaceful Mind', '获得时删除自己至多3张牌。', rarity='special', script='gain_remove', amount=3),
    'phoenix': _relic('凤凰天翔', 'Phoenix', '抵消每场战斗第一次生命值损失。', rarity='special', script='first_health_loss_immunity', amount=1),
    'sword_strategy': _relic('亮剑妙计', 'Sword Strategy', '每打出1张攻击牌，获得2层护盾。', rarity='special', script='attack_shield', amount=2),
    'perfection': _relic('致臻化境', 'Perfection', '获得时，将牌组中的1张护身符变为附魔护身符。', rarity='special', script='enchant_starter', amount=1),
    'easy_miracle': _relic('奇迹', 'Miracle', '每回合多回复1E。', rarity='special', script='turn_elixir', amount=1),
    'easy_peace': _relic('安宁', 'Tranquility', '回合开始时回复3H。', rarity='special', script='turn_heal', amount=3),
    'easy_study': _relic('勤学精进', 'Diligent Study', '之后获得的牌均已升级。', rarity='special', script='gained_cards_upgraded'),
    'easy_tiger': _relic('猛虎下山', 'Tiger Descends', '每回合多抽2张牌。', rarity='special', script='turn_draw', amount=2),
    'easy_godhood': _relic('神格', 'Divinity', '战斗开始时获得3E；未使用的E保留至下回合。', rarity='special', script='retain_elixir', amount=3),
    'consolation': _relic('安慰', 'Consolation', '获得时H上限+1。', rarity='special', script='gain_max_health_only', amount=1, stackable=True),
}


STORY_EASY_RELIC_IDS = (
    'easy_miracle',
    'easy_peace',
    'easy_study',
    'easy_tiger',
    'easy_godhood',
)

STORY_BOSS_RELIC_IDS = tuple(
    relic_id
    for relic_id, relic in STORY_RELICS.items()
    if str(relic.get('script') or '').startswith('boss_')
    or relic_id in {
        'coward_defense', 'return_to_origin', 'last_stand', 'quantized',
        'strive', 'gluttony', 'frugal', 'avoid_elite', 'grab_every_card',
        'cognitive_bias', 'first_strike', 'fast_learning', 'peaceful_mind',
        'phoenix', 'sword_strategy', 'perfection',
    }
)


def _move(zh, en, *effects):
    return {'name': {'zh': zh, 'en': en}, 'effects': tuple(effects)}


def _enemy(
    zh,
    en,
    health,
    moves,
    *,
    script=None,
    traits=(),
    initial=None,
    lunatic_health=None,
):
    definition = {
        'name': {'zh': zh, 'en': en},
        'max_health': health,
        'moves': tuple(moves),
        'script': script,
        'traits': tuple(traits),
    }
    if initial:
        definition['initial'] = deepcopy(initial)
    if lunatic_health is not None:
        definition['lunatic_max_health'] = int(lunatic_health)
    return definition


STORY_ENEMIES = {
    'soldier_ant': _enemy('兵蚁', 'Soldier Ant', 56, (
        _move('啃咬', 'Bite', _effect('damage', 6), _effect('gain_shield', 8)),
        _move('头锤', 'Headbutt', _effect('damage', 14), _effect('self_damage', 14)),
        _move('振翅', 'Flutter', _effect('gain_power', 3), _effect('gain_shield', 12)),
    )),
    'young_ant': _enemy('幼蚁', 'Young Ant', 11, (
        _move('啃咬', 'Bite', _effect('damage', 4), _effect('gain_shield', 6)),
        _move('跳动', 'Jump', _effect('damage', 2, hits=3)),
    )),
    'worker_ant': _enemy('工蚁', 'Worker Ant', 32, (
        _move('鼓舞', 'Inspire', _effect('damage', 4), _effect('allies_power', 1)),
        _move('护卫', 'Guard', _effect('damage', 6), _effect('lowest_ally_shield', 8)),
        _move('狂暴', 'Frenzy', _effect('damage', 3, hits=3)),
    ), script='worker_ant'),
    'bee': _enemy('蜜蜂', 'Bee', 39, (
        _move('花粉', 'Pollen', _effect('player_status', 3, status='broken')),
        _move('撞击', 'Collision', _effect('damage', 8)),
    )),
    'wasp': _enemy('黄蜂', 'Wasp', 31, (
        _move('蓄势待发', 'Ready', _effect('gain_shield', 6)),
        _move('射击', 'Shot', _effect('damage', 14)),
    )),
    'ladybug': _enemy('瓢虫', 'Ladybug', 41, (
        _move('呵护', 'Care', _effect('allies_heal', 13)),
        _move('保护', 'Protect', _effect('damage', 8), _effect('player_status', 1, status='weak')),
    )),
    'garden_rock': _enemy('岩石', 'Rock', 48, (
        _move('滚动', 'Roll', _effect('gain_status', 1, status='rockfall'), _effect('player_status', 1, status='weak')),
        _move('坚固', 'Solid', _effect('allies_shield', 8)),
    ), script='garden_rock'),
    'dandelion': _enemy('蒲公英', 'Dandelion', 32, (
        _move('种子', 'Seed', _effect('damage', 1, hits=3), _effect('player_status', 1, status='vulnerable')),
        _move('喷发', 'Erupt', _effect('damage', 8), _effect('gain_power', 2), _effect('player_status', 1, status='fragile')),
    )),
    'centipede': _enemy('蜈蚣体节', 'Centipede Segment', 52, (
        _move('扭动', 'Twist', _effect('damage', 2, hits=3)),
        _move('冲击', 'Impact', _effect('damage', 8)),
        _move('防护', 'Protect', _effect('adjacent_shield', 10), _effect('player_status', 1, status='fragile')),
        _move('生长', 'Growth', _effect('gain_power', 2)),
    ), script='centipede', traits=('adjacent',)),
    'spider': _enemy('蜘蛛', 'Spider', 47, (
        _move('吐网', 'Web', _effect('player_status', 1, status='weak'), _effect('add_draw_card', 1, card_id='slimed')),
        _move('收网', 'Reel', _effect('damage', 8)),
    )),
    'sunflower': _enemy('向日葵', 'Sunflower', 40, (
        _move('生长', 'Grow', _effect('gain_shield', 20), _effect('gain_power', 3)),
        _move('绽放', 'Bloom', _effect('damage', 2)),
    ), script='persistent_shield', traits=('sturdy',)),
    'avocado': _enemy('牛油果', 'Avocado', 76, (
        _move('膨胀', 'Expand', _effect('damage', 11), _effect('gain_power', 2)),
        _move('旋转', 'Spin', _effect('damage', 3, hits=3)),
    ), script='swell', traits=('swell',)),
    'spider_yoba': _enemy('蜘蛛尤巴', 'Yoba Spider', 102, (
        _move('下劈', 'Chop', _effect('damage', 11), _effect('gain_power', 2)),
        _move('嘲讽', 'Taunt', _effect('gain_shield', 13), _effect('player_status', 3, status='vulnerable')),
        _move('回旋斩', 'Whirlwind', _effect('damage', 3, hits=3)),
    )),
    'digger': _enemy('挖掘者', 'Digger', 198, (
        _move('冲撞', 'Charge', _effect('damage', 12)),
        _move('蓄力', 'Power Up', _effect('gain_power', 3)),
        _move('回旋', 'Sweep', _effect('damage', 5, hits=2)),
    ), script='opening_reflection'),
    'ant_queen': _enemy('蚁后', 'Ant Queen', 152, (
        _move('振奋', 'Inspire', _effect('damage', 5), _effect('allies_power', 2)),
        _move('连劈', 'Combo', _effect('damage', 3, hits=2)),
        _move('产卵', 'Lay Eggs', _effect('summon_to_ant_count', 5, enemy_id='young_ant')),
        _move('滋养', 'Nourish', _effect('consume_allies', 2)),
    ), script='ant_queen', traits=('nourish',)),
    'hive': _enemy('蜂巢', 'Hive', 172, (
        _move('召唤蜜蜂', 'Summon Bee', _effect('summon', 1, enemy_id='bee', move_index=1, wither=4), _effect('self_damage', 30)),
        _move('召唤黄蜂', 'Summon Wasp', _effect('summon', 1, enemy_id='wasp', move_index=0, wither=4), _effect('self_damage', 30)),
        _move('蜂蜜', 'Honey', _effect('self_heal', 15), _effect('player_status', 1, status='fragile'), _effect('player_status', 1, status='vulnerable')),
    ), script='hive', traits=('summon_after_death',)),
}

# Lunatic uses the values after the slash in the design sheet. Effects that do
# not list a second value intentionally keep their Normal/Hard value.
_GARDEN_LUNATIC_HEALTH = {
    'soldier_ant': 62,
    'young_ant': 14,
    'worker_ant': 35,
    'bee': 43,
    'wasp': 35,
    'ladybug': 47,
    'garden_rock': 54,
    'dandelion': 36,
    'centipede': 59,
    'spider': 53,
    'sunflower': 44,
    'avocado': 85,
    'spider_yoba': 111,
    'digger': 212,
    'ant_queen': 165,
    'hive': 195,
}
for _enemy_id, _health in _GARDEN_LUNATIC_HEALTH.items():
    STORY_ENEMIES[_enemy_id]['lunatic_max_health'] = _health

_GARDEN_LUNATIC_AMOUNTS = {
    ('soldier_ant', 0, 0): 8, ('soldier_ant', 0, 1): 10,
    ('soldier_ant', 1, 0): 16, ('soldier_ant', 1, 1): 16,
    ('soldier_ant', 2, 0): 4,
    ('young_ant', 0, 0): 5, ('young_ant', 0, 1): 7,
    ('young_ant', 1, 0): 3,
    ('worker_ant', 0, 0): 5, ('worker_ant', 1, 0): 7,
    ('worker_ant', 1, 1): 9, ('worker_ant', 2, 0): 4,
    ('bee', 1, 0): 10,
    ('wasp', 0, 0): 8, ('wasp', 1, 0): 17,
    ('ladybug', 0, 0): 15, ('ladybug', 1, 0): 9,
    ('garden_rock', 0, 0): 3, ('garden_rock', 1, 0): 10,
    ('dandelion', 1, 0): 9,
    ('centipede', 1, 0): 10, ('centipede', 2, 0): 13,
    ('spider', 1, 0): 10,
    ('sunflower', 0, 1): 4, ('sunflower', 1, 0): 3,
    ('avocado', 0, 0): 13,
    ('spider_yoba', 0, 0): 13, ('spider_yoba', 1, 0): 17,
    ('digger', 0, 0): 14, ('digger', 2, 0): 6,
    ('ant_queen', 0, 0): 7, ('ant_queen', 1, 0): 4,
}
for (_enemy_id, _move_index, _effect_index), _amount in _GARDEN_LUNATIC_AMOUNTS.items():
    STORY_ENEMIES[_enemy_id]['moves'][_move_index]['effects'][_effect_index]['lunatic_amount'] = _amount

STORY_ENEMIES['worker_ant']['moves'][2]['effects'] += (_effect('gain_power', 1),)
STORY_ENEMIES['sunflower']['initial'] = {'sturdy': 99}
STORY_ENEMIES['digger']['initial'] = {'reflection': 2}
STORY_ENEMIES['digger']['lunatic_initial'] = {'reflection': 3}
STORY_ENEMIES['ant_queen']['move_order'] = (0, 1, 2)
STORY_ENEMIES['ant_queen']['lunatic_move_order'] = (0, 2, 1)
STORY_ENEMIES['hive']['moves'] = (
    _move('召唤蜜蜂', 'Summon Bee', _effect('summon', 1, enemy_id='bee', move_index=1, wither=4), _effect('self_damage', 30)),
    _move('召唤黄蜂', 'Summon Wasp', _effect('summon', 1, enemy_id='wasp', move_index=0, wither=4), _effect('self_damage', 30)),
    _move('蜂蜜', 'Honey', _effect('self_heal', 30, lunatic_amount=40), _effect('gain_frenzy', 1)),
)

STORY_ENEMIES.update({
    'cicada': _enemy('蝉', 'Cicada', 33, (
        _move('扬尘', 'Dust Up', _effect('damage', 8, lunatic_amount=10), _effect('player_status', 1, status='weak')),
        _move('冲撞', 'Charge', _effect('damage', 11, lunatic_amount=12), _effect('gain_power', 2, lunatic_amount=3)),
    ), traits=('miracle',), initial={'miracle': 3}, lunatic_health=37),
    'sandstorm': _enemy('沙尘暴', 'Sandstorm', 51, (
        _move('旋转', 'Spin', _effect('damage', 3, hits=3)),
        _move('吸取', 'Absorb', _effect('damage', 6, lunatic_amount=8), _effect('gain_power', 1)),
        _move('凝聚', 'Condense', _effect('gain_shield', 12, lunatic_amount=15), _effect('self_heal', 6, lunatic_amount=9)),
    ), script='random_intent', traits=('chaos',), lunatic_health=57),
    'palm_tree': _enemy('棕榈树', 'Palm Tree', 36, (
        _move('固守', 'Hold Fast', _effect('gain_shield', 9, lunatic_amount=11), _effect('player_status', 1, status='weak')),
        _move('旋转', 'Spin', _effect('damage', 2, hits=3)),
    ), traits=('shelter',), initial={'shelter': 8}, lunatic_health=40),
    'cactus': _enemy('仙人掌', 'Cactus', 27, (
        _move('聚刺', 'Gather Spines', _effect('gain_status', 2, status='reflection')),
        _move('发射', 'Launch', _effect('damage', 14, lunatic_amount=17), _effect('clear_status', 0, status='reflection')),
    ), initial={'reflection': 2}, lunatic_health=31),
    'sandstone': _enemy('砂岩', 'Sandstone', 31, (
        _move('滚动', 'Roll', _effect('damage', 8, lunatic_amount=9)),
        _move('粉碎', 'Shatter', _effect('damage', 17, lunatic_amount=20), _effect('self_kill')),
    ), initial={'vulnerable': 1}, lunatic_health=35),
    'bandage_beetle': _enemy('甲虫', 'Bandage Beetle', 62, (
        _move('撕咬', 'Bite', _effect('damage', 12, lunatic_amount=14)),
        _move('头槌', 'Headbutt', _effect('damage', 8, lunatic_amount=10), _effect('player_status', 1, status='vulnerable')),
        _move('狂乱攻击', 'Frenzied Strike', _effect('damage', 20, lunatic_amount=23)),
    ), script='bandage_beetle', traits=('bandage',), initial={'bandage': 1}, lunatic_health=71),
    'scorpion': _enemy('蝎子', 'Scorpion', 42, (
        _move('迷惑', 'Confound', _effect('gain_shield', 8, lunatic_amount=11), _effect('player_status', 2, status='weak')),
        _move('蛰针', 'Sting', _effect('damage', 8, lunatic_amount=9), _effect('player_status', 3, status='poison', lunatic_amount=4)),
    ), lunatic_health=47),
    'tumbleweed': _enemy('风滚草', 'Tumbleweed', 44, (
        _move('滚动', 'Roll', _effect('damage', 6, lunatic_amount=8), _effect('player_status', 1, status='weak')),
        _move('扬沙', 'Scatter Sand', _effect('add_draw_card', 2, card_id='sand_dust')),
    ), lunatic_health=49),
    'rain_frog': _enemy('雨蛙', 'Rain Frog', 110, (
        _move('集沙', 'Gather Sand', _effect('damage', 13, lunatic_amount=15), _effect('player_status', 1, status='sturdy')),
        _move('蓄力', 'Power Up', _effect('gain_power', 4, lunatic_amount=5)),
        _move('冲刺', 'Dash', _effect('damage', 26, lunatic_amount=29)),
    ), lunatic_health=119),
    'nazar_beetle': _enemy('邪眼甲虫', 'Nazar Beetle', 89, (
        _move('蓄力', 'Power Up', _effect('gain_power', 2, lunatic_amount=3), _effect('gain_shield', 12, lunatic_amount=14), _effect('clear_status', 0, status='evil_eye')),
        _move('凝视', 'Gaze', _effect('damage', 16, lunatic_amount=18), _effect('gain_status', 1, status='evil_eye')),
    ), initial={'evil_eye': 1}, lunatic_health=95),
    'fossil': _enemy('化石', 'Fossil', 76, (
        _move('沉睡', 'Slumber', _effect('gain_charging', 5, lunatic_amount=6)),
        _move('惊醒', 'Awaken', _effect('damage', 14, lunatic_amount=16), _effect('gain_power', 3)),
    ), script='fossil', traits=('turn_shield', 'charging_up'), initial={'turn_shield': 10}, lunatic_health=84),
    'shiny_ladybug': _enemy('闪亮瓢虫', 'Shiny Ladybug', 132, (
        _move('迷幻', 'Dazzle', _effect('player_status', 1, status='weak'), _effect('add_draw_card', 1, card_id='confused'), _effect('gain_shield', 14, lunatic_amount=17)),
        _move('再生', 'Regenerate', _effect('self_heal', 14, lunatic_amount=17), _effect('gain_power', 3, lunatic_amount=4)),
        _move('狂怒', 'Rage', _effect('damage', 16, lunatic_amount=17)),
        _move('腐化', 'Corruption', _effect('gain_power', 10, lunatic_amount=12), _effect('self_kill', trigger_survival=True)),
    ), script='shiny_ladybug', traits=('yggdrasil_power',), lunatic_health=144),
    'worm': _enemy('蠕虫', 'Worm', 197, (
        _move('冲撞', 'Ram', _effect('damage', 12, lunatic_amount=15)),
        _move('追击', 'Pursue', _effect('gain_power', 3, lunatic_amount=4), _effect('gain_shield', 20, lunatic_amount=24)),
        _move('吞下', 'Swallow', _effect('damage', 18, lunatic_amount=21), _effect('stun_if_player_shield')),
        _move('消化', 'Digest', _effect('player_status', 7, status='poison', lunatic_amount=9)),
    ), script='worm', lunatic_health=214),
    'desert_centipede': _enemy('沙漠蜈蚣体节', 'Desert Centipede Segment', 59, (
        _move('泼沙', 'Throw Sand', _effect('gain_shield', 10, lunatic_amount=12), _effect('add_draw_card', 1, card_id='sand_dust')),
        _move('潜地', 'Burrow', _effect('damage', 10, lunatic_amount=12), _effect('gain_hidden', 2)),
        _move('沙潮', 'Sand Tide', _effect('damage', 2, hits=3, lunatic_hits=4), _effect('gain_power', 2)),
        _move('狂暴', 'Frenzy', _effect('damage', 4, hits=3, lunatic_hits=4)),
    ), script='desert_centipede', lunatic_health=65),

    'ocean_bubble': _enemy('泡泡', 'Bubble', 11, (
        _move('膨胀', 'Inflate', _effect('gain_charging', 4, lunatic_amount=5)),
        _move('爆炸', 'Explode', _effect('damage', 7, lunatic_amount=9), _effect('self_kill', reason='burst')),
    ), script='ocean_bubble', traits=('charging_up',), initial={'shield': 10}, lunatic_health=13),
    'crab': _enemy('螃蟹', 'Crab', 57, (
        _move('蓄力', 'Power Up', _effect('gain_power', 4)),
        _move('猛击', 'Slam', _effect('damage', 9, lunatic_amount=11)),
    ), initial={'shield': 6}, lunatic_health=63),
    'lily_pad': _enemy('睡莲', 'Lily Pad', 33, (
        _move('旋转', 'Spin', _effect('damage', 2, hits=3, lunatic_hits=4)),
        _move('漂浮', 'Float', _effect('gain_shield', 12, lunatic_amount=20), _effect('gain_power', 1)),
    ), traits=('proliferation',), initial={'proliferation': 10}, lunatic_health=37),
    'waterspout': _enemy('水龙卷', 'Waterspout', 23, (
        _move('涡旋', 'Vortex', _effect('player_status', 2, status='weak'), _effect('player_status', 2, status='fragile')),
        _move('洋流', 'Current', _effect('summon', 1, enemy_id='ocean_bubble')),
        _move('解离', 'Dissolve', _effect('self_kill')),
    ), script='waterspout', lunatic_health=28),
    'urchin': _enemy('海胆', 'Urchin', 42, (
        _move('蓄力', 'Power Up', _effect('gain_power', 1), _effect('clear_status', 0, status='reflection')),
        _move('喷射', 'Jet', _effect('damage', 4, hits=2, lunatic_amount=5), _effect('gain_status', 2, status='reflection', lunatic_amount=3)),
    ), initial={'reflection': 2}, lunatic_health=47),
    'turtle': _enemy('海龟', 'Turtle', 69, (
        _move('吐泡', 'Spit Bubble', _effect('summon', 1, enemy_id='ocean_bubble'), _effect('gain_power', 2)),
        _move('盾击', 'Shield Bash', _effect('damage', 10, lunatic_amount=12), _effect('allies_shield', 10, lunatic_amount=12), _effect('player_status', 1, status='weak')),
    ), initial={'shield': 10}, lunatic_health=76),
    'electric_eel': _enemy('电鳗', 'Electric Eel', 62, (
        _move('放电', 'Discharge', _effect('damage', 9, lunatic_amount=11), _effect('delayed_hand_charge', 1)),
        _move('生长', 'Grow', _effect('self_heal', 9, lunatic_amount=13), _effect('gain_charged', 1)),
    ), traits=('charged',), initial={'charged': 2}, lunatic_health=71),
    'leech': _enemy('水蛭', 'Leech', 56, (
        _move('吸食', 'Suck', _effect('damage', 12, lunatic_amount=13), _effect('gain_power', 2)),
        _move('扭动', 'Twist', _effect('damage', 3, hits=3)),
    ), traits=('vampire',), initial={'vampire': 2}, lunatic_health=59),
    'shark': _enemy('鲨鱼', 'Shark', 86, (
        _move('追猎', 'Hunt', _effect('damage', 9, lunatic_amount=12), _effect('player_status', 1, status='vulnerable'), _effect('gain_power', 1)),
        _move('撕咬', 'Bite', _effect('damage', 2, hits=7, lunatic_hits=8)),
    ), traits=('bloodthirsty',), lunatic_health=93),
    'ocean_shell': _enemy('贝壳', 'Shell', 114, (
        _move('吐出', 'Spit Out', _effect('damage', 11, lunatic_amount=13), _effect('summon', 1, enemy_id='ocean_pearl')),
        _move('拉回', 'Pull Back', _effect('damage', 2, hits=7, lunatic_hits=8), _effect('gain_power', 2, lunatic_amount=3), _effect('consume_pearls_damage', 7, lunatic_amount=8)),
    ), script='ocean_shell', lunatic_health=125),
    'ocean_pearl': _enemy('珍珠', 'Pearl', 11, (
        _move('闪耀', 'Shine', _effect('allies_power', 1)),
    ), lunatic_health=13),
    'starfish': _enemy('海星', 'Starfish', 87, (
        _move('猛击', 'Slam', _effect('damage', 12, lunatic_amount=14), _effect('gain_power', 1)),
        _move('抽打', 'Lash', _effect('damage', 4, hits=3, lunatic_amount=5)),
        _move('断臂', 'Sever Limb', _effect('lose_max_health_percent', 20), _effect('heal_to_full')),
    ), script='starfish', traits=('limb_survival',), initial={'regenerations': 999, 'regeneration': 5}, lunatic_health=95),
    'jellyfish': _enemy('水母', 'Jellyfish', 176, (
        _move('麻痹', 'Paralyze', _effect('damage', 10, lunatic_amount=12), _effect('player_status', 1, status='weak')),
        _move('发电', 'Generate', _effect('add_draw_card', 2, card_id='static_electricity'), _effect('gain_power', 2, lunatic_amount=3)),
        _move('放电', 'Discharge', _effect('damage', 11, lunatic_amount=13), _effect('delayed_hand_charge', 1)),
    ), traits=('charged',), initial={'charged': 1}, lunatic_health=190),
    'squid': _enemy('鱿鱼', 'Squid', 218, (
        _move('紧缠', 'Constrict', _effect('damage', 8), _effect('player_status', 3, status='entangle')),
        _move('喷墨', 'Ink', _effect('delayed_player_status', 1, status='blind'), _effect('gain_power', 2)),
        _move('蛮力', 'Brute Force', _effect('damage', 5, hits=2), _effect('player_status', 1, status='weak')),
    )),
    'shipwreck': _enemy('沉船', 'Shipwreck', 196, (
        _move('晃动', 'Rock', _effect('summon_wreckage', 3)),
        _move('震击', 'Shock', _effect('damage', 18, lunatic_amount=20)),
        _move('沉默', 'Silence', _effect('player_status', 1, status='weak'), _effect('gain_shield', 18, lunatic_amount=24)),
        _move('喷发', 'Erupt', _effect('damage', 2, hits=8, lunatic_hits=9), _effect('gain_power', 3)),
    ), script='shipwreck', initial={'shield': 20}, lunatic_health=212),
    'wreckage': _enemy('残骸', 'Debris', 11, (
        _move('爆裂', 'Burst', _effect('self_kill', reason='burst')),
    ), script='wreckage', traits=('brittle',), lunatic_health=13),
})

# Explicit move orders preserve repeated moves without encoding them as
# duplicate definitions. Encounter-specific ``move_index`` still controls the
# first action for enemies that use the ordinary sequential order.
STORY_ENEMIES['cactus']['move_order'] = (0, 0, 1)
STORY_ENEMIES['cactus']['lunatic_initial'] = {'reflection': 3}
STORY_ENEMIES['palm_tree']['lunatic_initial'] = {'shelter': 10}
STORY_ENEMIES['cicada']['lunatic_initial'] = {'miracle': 5}
STORY_ENEMIES['bandage_beetle']['move_order'] = (0, 1)
STORY_ENEMIES['hive']['move_order'] = (0, 1, 2)
STORY_ENEMIES['fossil']['move_order'] = (0,)
STORY_ENEMIES['fossil']['lunatic_initial'] = {'turn_shield': 12}
STORY_ENEMIES['shiny_ladybug']['move_order'] = (0, 1, 0, 1, 0, 1, 3)
STORY_ENEMIES['worm']['move_order'] = (0, 1, 2)
STORY_ENEMIES['desert_centipede']['move_order'] = (0, 1, 2)
STORY_ENEMIES['ocean_bubble']['move_order'] = (0, 0, 1)
STORY_ENEMIES['ocean_bubble']['lunatic_initial'] = {'shield': 20}
STORY_ENEMIES['crab']['lunatic_initial'] = {'shield': 12}
STORY_ENEMIES['lily_pad']['lunatic_initial'] = {'proliferation': 15}
STORY_ENEMIES['waterspout']['move_order'] = (0, 1, 0, 2)
STORY_ENEMIES['urchin']['lunatic_initial'] = {'reflection': 3}
STORY_ENEMIES['turtle']['lunatic_initial'] = {'shield': 20}
STORY_ENEMIES['leech']['lunatic_initial'] = {'vampire': 3}
STORY_ENEMIES['ocean_shell']['move_order'] = (0, 0, 1)
STORY_ENEMIES['starfish']['move_order'] = (0, 1)
STORY_ENEMIES['starfish']['lunatic_initial'] = {'regenerations': 1, 'regeneration': 7}
STORY_ENEMIES['shipwreck']['lunatic_initial'] = {'shield': 50}

STORY_ENEMY_IMAGE_URLS = {
    'soldier_ant': '/static/assets/story-enemies/soldier-ant.svg',
    'young_ant': '/static/assets/story-enemies/young-ant.svg',
    'worker_ant': '/static/assets/story-enemies/worker-ant.svg',
    'bee': '/static/assets/story-enemies/bee.svg',
    'wasp': '/static/assets/story-enemies/wasp.svg',
    'ladybug': '/static/assets/story-enemies/ladybug.svg',
    'garden_rock': '/static/assets/story-enemies/garden-rock.svg',
    'dandelion': '/static/assets/story-enemies/dandelion.svg',
    'centipede': '/static/assets/story-enemies/centipede-body.svg',
    'spider': '/static/assets/story-enemies/spider.svg',
    'sunflower': '/static/assets/story-enemies/sunflower.svg',
    'avocado': '/static/assets/story-enemies/avocado.svg',
    'spider_yoba': '/static/assets/story-enemies/spider-yoba.svg',
    'digger': '/static/assets/story-enemies/digger.svg',
    'ant_queen': '/static/assets/story-enemies/ant-queen.svg',
    'hive': '/static/assets/story-enemies/hive.svg',
    'cicada': '/static/assets/story-enemies/cicada.svg',
    'sandstorm': '/static/assets/story-enemies/sandstorm.svg',
    'palm_tree': '/static/assets/story-enemies/palm-tree.svg',
    'cactus': '/static/assets/story-enemies/cactus.svg',
    'sandstone': '/static/assets/story-enemies/sandstone.svg',
    'bandage_beetle': '/static/assets/story-enemies/bandage-beetle.svg',
    'scorpion': '/static/assets/story-enemies/scorpion.svg',
    'tumbleweed': '/static/assets/story-enemies/tumbleweed.svg',
    'rain_frog': '/static/assets/story-enemies/rain-frog.svg',
    'nazar_beetle': '/static/assets/story-enemies/nazar-beetle.svg',
    'fossil': '/static/assets/story-enemies/fossil.svg',
    'shiny_ladybug': '/static/assets/story-enemies/shiny-ladybug.svg',
    'worm': '/static/assets/story-enemies/worm.svg',
    'desert_centipede': '/static/assets/story-enemies/desert-centipede-body.svg',
    'ocean_bubble': '/static/assets/story-enemies/bubble.svg',
    'crab': '/static/assets/story-enemies/crab.svg',
    'lily_pad': '/static/assets/story-enemies/lily-pad.svg',
    'waterspout': '/static/assets/story-enemies/waterspout.svg',
    'urchin': '/static/assets/story-enemies/urchin.svg',
    'turtle': '/static/assets/story-enemies/turtle.svg',
    'electric_eel': '/static/assets/story-enemies/electric-eel.svg',
    'leech': '/static/assets/story-enemies/leech.svg',
    'shark': '/static/assets/story-enemies/shark.svg',
    'ocean_shell': '/static/assets/story-enemies/shell.svg',
    'ocean_pearl': '/static/assets/story-enemies/pearl.svg',
    'starfish': '/static/assets/story-enemies/starfish.svg',
    'jellyfish': '/static/assets/story-enemies/jellyfish.svg',
    'squid': '/static/assets/story-enemies/squid.svg',
    'shipwreck': '/static/assets/story-enemies/shipwreck.svg',
    'wreckage': '/static/assets/story-enemies/wreckage.svg',
}

for _enemy_id, _image_url in STORY_ENEMY_IMAGE_URLS.items():
    STORY_ENEMIES[_enemy_id]['image_url'] = _image_url


STORY_ENCOUNTERS = {
    'garden': {
        'simple': (
            ('soldier_ant',),
            ('worker_ant', 'young_ant'),
            ('bee', 'young_ant'),
        ),
        'hard': (
            ('bee', 'wasp'),
            ('garden_rock', 'young_ant', 'young_ant'),
            ('garden_rock', 'wasp'),
            ('dandelion', 'wasp'),
            ('sunflower', 'worker_ant', 'young_ant'),
            ('ladybug', 'worker_ant', 'young_ant'),
            ('spider', 'wasp'),
            ('dandelion', 'soldier_ant'),
        ),
        'elite': (
            ({'def_id': 'centipede', 'move_index': 0}, {'def_id': 'centipede', 'move_index': 1},
             {'def_id': 'centipede', 'move_index': 2}, {'def_id': 'centipede', 'move_index': 3}),
            ('spider_yoba',),
            ('avocado',),
        ),
        'boss': (
            ('ant_queen', 'worker_ant', 'young_ant', 'young_ant'),
            ('hive', 'bee'),
            ('digger',),
        ),
    },
    'desert': {
        'simple': (
            ('cicada',),
            ('sandstorm',),
            ('palm_tree', 'cactus'),
        ),
        'hard': (
            ('palm_tree', 'sandstone', 'cactus'),
            ('palm_tree', 'cicada'),
            ('sandstorm', 'tumbleweed'),
            ('palm_tree', 'sandstone', 'scorpion'),
            ('bandage_beetle',),
            ('cactus', 'cicada', 'sandstone'),
            ({'def_id': 'cicada', 'move_index': 0}, {'def_id': 'cicada', 'move_index': 1}),
        ),
        'elite': (
            ('nazar_beetle',),
            ('fossil',),
            ('rain_frog',),
        ),
        'boss': (
            (
                {'def_id': 'desert_centipede', 'move_index': 0, 'move_step': 0, 'hidden': 1},
                {'def_id': 'desert_centipede', 'move_index': 1, 'move_step': 1},
                {'def_id': 'desert_centipede', 'move_index': 2, 'move_step': 2, 'hidden': 2},
            ),
            ('worm',),
            ('shiny_ladybug',),
        ),
    },
    'ocean': {
        'simple': (
            ('lily_pad', 'waterspout'),
            ('crab',),
            ('urchin',),
        ),
        'hard': (
            ('lily_pad', 'lily_pad', 'waterspout'),
            ({'def_id': 'crab', 'move_index': 0}, {'def_id': 'crab', 'move_index': 1}),
            ('turtle', 'waterspout'),
            ('electric_eel',),
            ('leech', 'ocean_bubble'),
            (
                {'def_id': 'urchin', 'move_index': 0},
                {'def_id': 'urchin', 'move_index': 1},
                'waterspout',
            ),
            ('urchin', 'turtle'),
        ),
        'elite': (
            ('shark',),
            ('starfish',),
            ('ocean_shell',),
        ),
        'boss': (
            ('squid',),
            ('jellyfish',),
            ('shipwreck',),
        ),
    },
}


def initial_story_player():
    deck_ids = ('basic',) * 5 + ('rose',) * 4 + ('amulet',)
    deck = [
        {'instance_id': f'sc-{index:04d}', 'def_id': def_id, 'upgraded': False}
        for index, def_id in enumerate(deck_ids, start=1)
    ]
    return {
        'health': STORY_RULES['starting_health'],
        'max_health': STORY_RULES['starting_health'],
        'elixir': STORY_RULES['starting_elixir'],
        'max_elixir': STORY_RULES['starting_elixir'],
        'magic': STORY_RULES['starting_magic'],
        'max_magic': STORY_RULES['max_magic'],
        'gold': 99,
        'deck': deck,
        'relics': ['energetic'],
        'blessing': None,
        'blessings': [],
        'opening_draw_bonus': 0,
        'next_card_serial': len(deck) + 1,
    }


def _find_source(card_defs, source_id):
    if not source_id or not card_defs:
        return None
    def normalize(value):
        return ''.join(ch for ch in str(value).lower() if ch.isalnum())

    candidates = (
        source_id,
        str(source_id).lower(),
        str(source_id).replace(' ', '_'),
        str(source_id).lower().replace(' ', '_'),
    )
    for candidate in candidates:
        source = card_defs.get(candidate)
        if source is not None:
            return source
    source_key = normalize(source_id)
    source_aliases = {
        'chilly': 'chilli',
        'magicchilly': 'magicchilli',
        'magicacid': 'acid',
        'redemptionmoney': 'ransommoney',
        'magicassembler': 'assembler',
    }
    alias_key = source_aliases.get(source_key, source_key)
    for key, source in card_defs.items():
        key_value = normalize(str(key).split(':')[-1])
        if key_value == source_key or key_value == alias_key:
            return source
    return None


def story_content_payload(card_defs=None):
    cards = deepcopy(STORY_CARDS)
    if card_defs:
        for definition in cards.values():
            source = _find_source(card_defs, definition.get('source_card_id'))
            if source is None:
                continue
            image_url = str(getattr(source, 'image_url', '') or getattr(source, 'image', '') or '')
            upgraded_image_url = str(
                getattr(source, 'upgraded_image_url', '')
                or getattr(source, 'upgraded_image', '')
                or image_url
            )
            if image_url and not definition.get('image_url'):
                definition['image_url'] = image_url
            if upgraded_image_url and not definition.get('upgraded_image_url'):
                definition['upgraded_image_url'] = upgraded_image_url
            if not definition.get('flavor'):
                source_flavor = getattr(source, 'description_i18n', None)
                if isinstance(source_flavor, dict) and any(source_flavor.values()):
                    definition['flavor'] = deepcopy(source_flavor)
                else:
                    source_flavor = str(getattr(source, 'description', '') or '').strip()
                    if source_flavor:
                        definition['flavor'] = {'zh': source_flavor, 'en': source_flavor}
    return {
        'rules': deepcopy(STORY_RULES),
        'biomes': deepcopy(STORY_BIOMES),
        'difficulties': deepcopy(STORY_DIFFICULTIES),
        'curses': deepcopy(STORY_CURSES),
        'rarities': deepcopy(STORY_RARITIES),
        'card_types': deepcopy(STORY_CARD_TYPES),
        'tags': deepcopy(STORY_TAGS),
        'statuses': deepcopy(STORY_STATUSES),
        'traits': deepcopy(STORY_TRAITS),
        'blessings': deepcopy(STORY_BLESSINGS),
        'cards': cards,
        'relics': deepcopy(STORY_RELICS),
        'boss_relic_ids': list(STORY_BOSS_RELIC_IDS),
        'easy_relic_ids': list(STORY_EASY_RELIC_IDS),
        'enemies': deepcopy(STORY_ENEMIES),
    }


def validate_story_content():
    errors = []
    card_effect_types = {
        'active_discard', 'active_discard_all',
        'choose_exile', 'copy_hand_card', 'decaying_shield',
        'choose_random_generated', 'create_discard_copy',
        'delayed_copy', 'delayed_player_status', 'discard_to_draw_top',
        'draw', 'draw_attack_power', 'draw_target_status', 'draw_then_discard',
        'draw_selected', 'draw_to_limit', 'elixir', 'elixir_from_hand', 'equipment',
        'elixir_if_active_discard',
        'exile_hand_for_shield', 'first_use_power', 'next_attack_multiplier',
        'immediate_extra_turn', 'inspect_draw_choose', 'lose_health',
        'magic', 'make_card_free', 'next_skill_repeats', 'next_turn_draw',
        'permanent_damage_growth', 'permanent_swift', 'power',
        'random_active_discard', 'random_damage_per_discards', 'random_exile',
        'recover_exiled', 'salt', 'shield', 'shield_from_target_status',
        'shield_selected', 'shield_with_power', 'shuffle_hand_redraw',
        'status', 'status_self', 'swap_piles_draw', 'temporary_cost_down',
        'temporary_effect',
    }
    card_effect_types.update(STORY_PLAYER_ATTACK_EFFECT_TYPES)
    card_scripts = {
        'azalea', 'azalea_plus', 'light_sprout', 'return_draw_top', 'slimed',
        'startled', 'static_electricity', 'unrelenting', 'corruption',
    }
    equipment_scripts = {
        'cannot_draw', 'disc', 'magic_acid', 'magic_pearl', 'pearl',
        'draw_power', 'retain_elixir', 'sewage', 'soul_splitter', 'sponge',
        'start_power', 'start_random_bloom', 'start_shield', 'turn_elixir',
        'victory_gold', 'vulnerable_shield',
    }
    relic_scripts = {
        'attack_shield', 'avoid_elite', 'boss_blind', 'boss_broken', 'boss_frenzy',
        'boss_no_bloom', 'boss_no_extra_draw', 'boss_no_heal', 'boss_poison',
        'decaying_elixir', 'elite_boss_elixir', 'enchant_starter',
        'extra_upgrade', 'first_attack_vulnerable', 'first_health_loss_immunity',
        'first_hit_elixir', 'first_round_boost', 'flat_damage_reduction',
        'floor_heal', 'gain_card_heal', 'gain_gold', 'gain_max_health',
        'gain_max_health_only', 'gained_cards_upgraded',
        'floor_max_health', 'gain_remove', 'gain_upgrade', 'loss_upgrade',
        'must_take_cards', 'opening_damage', 'opening_draw',
        'opening_endurance', 'opening_power', 'opening_redraw',
        'opening_shield', 'no_resource_retention', 'primary_bonus',
        'primary_multiplier', 'quantized_cost',
        'rest_gold', 'revive', 'round_power', 'skip_shop',
        'retain_elixir', 'shop_discount', 'shop_restock', 'support',
        'turn_draw', 'turn_elixir', 'turn_heal',
    }
    enemy_effect_types = {
        'add_draw_card', 'adjacent_shield', 'allies_heal', 'allies_power',
        'allies_shield', 'clear_status', 'consume_allies',
        'consume_pearls_damage', 'damage', 'delayed_hand_charge',
        'delayed_player_status', 'gain_charged', 'gain_charging',
        'gain_frenzy', 'gain_hidden', 'gain_power',
        'gain_shield', 'gain_status', 'gain_sturdy', 'heal_to_full',
        'lose_max_health_percent', 'lowest_ally_shield', 'player_status',
        'self_damage', 'self_heal', 'self_kill',
        'stun_if_player_shield', 'summon', 'summon_to_ant_count',
        'summon_wreckage',
    }
    enemy_scripts = {
        'ant_queen', 'bandage_beetle', 'centipede', 'desert_centipede',
        'fossil', 'garden_rock', 'hive', 'ocean_bubble', 'ocean_shell',
        'opening_reflection', 'persistent_shield', 'random_intent',
        'sandstone', 'shiny_ladybug', 'shipwreck', 'starfish', 'swell',
        'waterspout', 'worker_ant', 'worm', 'wreckage',
    }

    def validate_cost(owner, key, value):
        if value == 'X':
            return
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f'{owner}: invalid {key} {value!r}')

    def validate_card_effects(owner, effects):
        for index, effect in enumerate(effects or ()):
            effect_owner = f'{owner}.effects[{index}]'
            effect_type = effect.get('type')
            if effect_type not in card_effect_types:
                errors.append(f'{effect_owner}: unknown effect {effect_type}')
            status = effect.get('status')
            if status and status not in STORY_STATUSES and status not in STORY_TRAITS:
                errors.append(f'{effect_owner}: unknown status {status}')
            script = effect.get('script')
            if script and script not in equipment_scripts:
                errors.append(f'{effect_owner}: unknown script {script}')

    for card_id, definition in STORY_CARDS.items():
        if definition.get('type') not in STORY_CARD_TYPES:
            errors.append(f'{card_id}: invalid type')
        if definition.get('rarity') not in STORY_RARITIES and definition.get('rarity') != 'special':
            errors.append(f'{card_id}: invalid rarity')
        if definition.get('target') not in ('self', 'enemy'):
            errors.append(f'{card_id}: invalid target {definition.get("target")}')
        validate_cost(card_id, 'cost_e', definition.get('cost_e'))
        validate_cost(card_id, 'cost_m', definition.get('cost_m'))
        for tag in definition.get('tags', ()):
            if tag not in STORY_TAGS:
                errors.append(f'{card_id}: unknown tag {tag}')
        script = definition.get('script')
        if script and script not in card_scripts:
            errors.append(f'{card_id}: unknown script {script}')
        validate_card_effects(card_id, definition.get('effects'))

        upgrade = definition.get('upgrade') or {}
        if 'cost_e' in upgrade:
            validate_cost(f'{card_id}.upgrade', 'cost_e', upgrade['cost_e'])
        if 'cost_m' in upgrade:
            validate_cost(f'{card_id}.upgrade', 'cost_m', upgrade['cost_m'])
        for tag in upgrade.get('tags', ()):
            if tag not in STORY_TAGS:
                errors.append(f'{card_id}.upgrade: unknown tag {tag}')
        upgrade_script = upgrade.get('script')
        if upgrade_script and upgrade_script not in card_scripts:
            errors.append(f'{card_id}.upgrade: unknown script {upgrade_script}')
        validate_card_effects(f'{card_id}.upgrade', upgrade.get('effects'))

    for card_id in STORY_REWARD_CARD_IDS:
        if card_id not in STORY_CARDS:
            errors.append(f'{card_id}: unknown reward card')
            continue
        definition = STORY_CARDS[card_id]
        if definition['type'] in ('curse', 'infect') or definition['rarity'] in ('super', 'special'):
            errors.append(f'{card_id}: illegal reward card')
        if definition.get('owner') != 'primary':
            errors.append(f'{card_id}: non-primary reward card')

    for card_id in STORY_SHOP_CARD_IDS:
        if card_id not in STORY_CARDS:
            errors.append(f'{card_id}: unknown shop card')
            continue
        definition = STORY_CARDS[card_id]
        if definition['type'] in ('curse', 'infect') or definition['rarity'] in ('super', 'special'):
            errors.append(f'{card_id}: illegal shop card')

    for relic_id, definition in STORY_RELICS.items():
        if definition.get('rarity') not in STORY_RARITIES and definition.get('rarity') != 'special':
            errors.append(f'{relic_id}: invalid relic rarity')
        if definition.get('script') not in relic_scripts:
            errors.append(f'{relic_id}: unknown relic script {definition.get("script")}')

    for enemy_id, definition in STORY_ENEMIES.items():
        script = definition.get('script')
        if script and script not in enemy_scripts:
            errors.append(f'{enemy_id}: unknown enemy script {script}')
        for trait in definition.get('traits', ()):
            if trait not in STORY_TRAITS:
                errors.append(f'{enemy_id}: unknown trait {trait}')
        for move_index, move in enumerate(definition.get('moves') or ()):
            for effect_index, effect in enumerate(move.get('effects') or ()):
                owner = f'{enemy_id}.moves[{move_index}].effects[{effect_index}]'
                effect_type = effect.get('type')
                if effect_type not in enemy_effect_types:
                    errors.append(f'{owner}: unknown effect {effect_type}')
                status = effect.get('status')
                if status and status not in STORY_STATUSES and status not in STORY_TRAITS:
                    errors.append(f'{owner}: unknown status {status}')
                summoned_enemy = effect.get('enemy_id')
                if summoned_enemy and summoned_enemy not in STORY_ENEMIES:
                    errors.append(f'{owner}: unknown enemy {summoned_enemy}')
                card_id = effect.get('card_id')
                if card_id and card_id not in STORY_CARDS:
                    errors.append(f'{owner}: unknown card {card_id}')

    for region, encounter_groups in STORY_ENCOUNTERS.items():
        for room_type, encounters in encounter_groups.items():
            if room_type not in ('simple', 'hard', 'elite', 'boss'):
                errors.append(f'encounters[{region}]: invalid room {room_type}')
            for encounter in encounters:
                for enemy_entry in encounter:
                    enemy_id = (
                        enemy_entry.get('def_id')
                        if isinstance(enemy_entry, dict)
                        else enemy_entry
                    )
                    if enemy_id not in STORY_ENEMIES:
                        errors.append(
                            f'encounters[{region}].{room_type}: unknown enemy {enemy_id}'
                        )
    if errors:
        raise ValueError('Invalid story content: ' + '; '.join(errors))


validate_story_content()
