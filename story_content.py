"""Data definitions for the server-authoritative story mode.

The story engine intentionally consumes this file instead of multiplayer card
definitions. Story cards share artwork with multiplayer cards where possible,
but their balance and rules are independent.
"""

from copy import deepcopy

from story_character_content import (
    STORY_CHARACTER_CARD_DESIGNS,
    STORY_CHARACTER_RELIC_DESIGNS,
)


STORY_RULES = {
    'starting_health': 80,
    'starting_elixir': 3,
    'starting_magic': 0,
    'max_magic': 10,
    'resource_cap': None,
    'draw_per_turn': 5,
    'hand_limit': 10,
    'stage_floor_count': 16,
    'enchantment_book_slots': 3,
    'rare_card_pity_initial': -0.05,
    'rare_card_pity_cap': 0.40,
}

STORY_CHARACTER_NOT_READY_MESSAGE = {
    'zh': '这名角色还没准备好呢\n请期待开发组更新',
    'en': 'This character is not ready yet.\nPlease look forward to a future update.',
}

STORY_CHARACTERS = {
    'common_flower': {
        'name': {'zh': '普通的花花', 'en': 'Common Flower'},
        'design': '力量+易伤+抽牌+弃牌；不再使用消耗机制。',
        'implementation_status': 'playable',
        'starter_deck': (
            {'card_id': 'basic', 'count': 5},
            {'card_id': 'rose', 'count': 4},
            {'card_id': 'amulet', 'count': 1},
        ),
        'starter_relics': ('energetic',),
        'unlock': {
            'kind': 'default',
            'description': {'zh': '默认解锁', 'en': 'Unlocked by default'},
        },
    },
    'orbiter': {
        'name': {'zh': '轨道使', 'en': 'Orbiter'},
        'design': (
            '轨道机制：轨道X将牌置于耐久为X的轨道；旋转会顺时针旋转轨道、'
            '触发转到的花瓣并使其耐久-1；每回合结束自动旋转一次。'
        ),
        'implementation_status': 'planned',
        'unlock': {
            'kind': 'complete_journey',
            'character_id': 'mage',
            'any_difficulty': True,
            'description': {
                'zh': '使用魔法师以任意难度通关全部阶段后解锁',
                'en': 'Complete every stage with Mage on any difficulty',
            },
        },
        'unavailable_message': deepcopy(STORY_CHARACTER_NOT_READY_MESSAGE),
    },
    'summoner': {
        'name': {'zh': '召唤师', 'en': 'Summoner'},
        'design': (
            '拥有3个召唤槽；召唤物具有被动、主动和特殊效果；回合结束触发被动；'
            '号令X依次触发首个召唤物的主动并移至队尾；溢出召唤物会被牺牲。'
        ),
        'implementation_status': 'planned',
        'unlock': {
            'kind': 'complete_journey',
            'character_id': 'orbiter',
            'any_difficulty': True,
            'description': {
                'zh': '使用轨道使以任意难度通关全部阶段后解锁',
                'en': 'Complete every stage with Orbiter on any difficulty',
            },
        },
        'unavailable_message': deepcopy(STORY_CHARACTER_NOT_READY_MESSAGE),
    },
    'mage': {
        'name': {'zh': '魔法师', 'en': 'Mage'},
        'design': '以魔力支付专属卡牌，并通过魔力源泉在每回合开始时回复1M。',
        'implementation_status': 'playable',
        'starter_deck': (
            {'card_id': 'basic', 'count': 5},
            {'card_id': 'rose', 'count': 5},
            {'character_card_id': 'mage_basic', 'count': 1},
        ),
        'starter_relics': ('magic_source',),
        'unlock': {
            'kind': 'complete_journey',
            'character_id': 'common_flower',
            'any_difficulty': True,
            'description': {
                'zh': '使用普通的花花以任意难度通关全部阶段后解锁',
                'en': 'Complete every stage with Common Flower on any difficulty',
            },
        },
        'unavailable_message': deepcopy(STORY_CHARACTER_NOT_READY_MESSAGE),
    },
    'occultist': {
        'name': {'zh': '邪术师', 'en': 'Occultist'},
        'design': '腐化、各类异常效果、放逐与放血。',
        'implementation_status': 'planned',
        'unlock': {
            'kind': 'complete_journey',
            'character_id': 'summoner',
            'any_difficulty': True,
            'description': {
                'zh': '使用召唤师以任意难度通关全部阶段后解锁',
                'en': 'Complete every stage with Summoner on any difficulty',
            },
        },
        'unavailable_message': deepcopy(STORY_CHARACTER_NOT_READY_MESSAGE),
    },
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
    'jungle': {
        'name': {'zh': '丛林', 'en': 'Jungle'},
        'color': '#2E9A58',
    },
    'factory': {
        'name': {'zh': '工厂', 'en': 'Factory'},
        'color': '#68717A',
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
    'innate': {
        'name': {'zh': '固有', 'en': 'Innate'},
        'description': {
            'zh': '战斗开始时，这张牌必定出现在初始手牌中。',
            'en': 'This card is guaranteed to appear in the opening hand.',
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
    'overload': {
        'name': {'zh': '超载', 'en': 'Overload'},
        'description': {
            'zh': '己方回合开始时扣除至多等同层数的E，然后清空。',
            'en': 'At turn start, lose up to that much E, then clear it.',
        },
    },
    'magic_overload': {
        'name': {'zh': '魔力超载', 'en': 'Magic Overload'},
        'description': {
            'zh': '己方回合开始时扣除至多等同层数的M，然后清空。',
            'en': 'At turn start, lose up to that much M, then clear it.',
        },
    },
    'static': {
        'name': {'zh': '静电', 'en': 'Static'},
        'description': {
            'zh': '受到电击伤害时消耗全部静电，并使该次伤害增加等同于原层数的数值。',
            'en': 'Electric damage consumes all Static and adds its former stacks to that hit.',
        },
    },
    'untargetable': {
        'name': {'zh': '隐形', 'en': 'Invisible'},
        'description': {
            'zh': '敌方攻击无法命中；自己的下个回合开始时减少1层。',
            'en': 'Enemy attacks cannot hit; lose 1 stack at the start of your next turn.',
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
            'zh': '回合结束时受到等同于层数的伤害。',
            'en': 'At turn end, take damage equal to its stacks.',
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

STORY_STATUSES.update({
    'toxic_poison': {
        'name': {'zh': '剧毒', 'en': 'Toxic Poison'},
        'description': {
            'zh': '中毒结算后，获得等同于层数的中毒。',
            'en': 'After Poison resolves, gain Poison equal to its stacks.',
        },
    },
    'stagnation': {
        'name': {'zh': '滞留', 'en': 'Stagnation'},
        'description': {
            'zh': '存在时，中毒结算后不会减半；回合结束时-1层。',
            'en': 'Poison does not halve after resolving; lose 1 stack at turn end.',
        },
    },
    'bleed': {
        'name': {'zh': '流血', 'en': 'Bleed'},
        'description': {
            'zh': '打出攻击牌结算后受到等同于层数的伤害，然后层数向下取整减半。',
            'en': 'After playing an Attack, take damage equal to its stacks, then halve them.',
        },
    },
    'fire': {
        'name': {'zh': '灼烧', 'en': 'Burn'},
        'description': {
            'zh': '回合开始时受到等同于层数的伤害。',
            'en': 'At turn start, take damage equal to its stacks.',
        },
    },
    'blockade': {
        'name': {'zh': '封锁', 'en': 'Blockade'},
        'description': {
            'zh': '前X个奇数栏的手牌无法打出；不会自然减少层数。',
            'en': 'The first X odd-numbered hand slots cannot be played. Its stacks do not decay naturally.',
        },
    },
    'attack_blocked': {
        'name': {'zh': '禁攻', 'en': 'Attack Blocked'},
        'description': {
            'zh': '存在时，无法打出攻击牌；回合结束时-1层。',
            'en': 'Attack cards cannot be played. Lose 1 stack at turn end.',
        },
    },
    'fragment': {
        'name': {'zh': '碎片', 'en': 'Fragment'},
        'description': {
            'zh': '供重构机的特殊行动消耗。',
            'en': 'Consumed by the Reconstructor\'s special actions.',
        },
    },
    'magic_shield_disabled': {
        'name': {'zh': '魔力护盾失效', 'en': 'Magic Shield Disabled'},
        'description': {
            'zh': '存在时，魔力护盾不生效；玩家回合结束时清除。',
            'en': 'Magic Shield does not work while present; clears at the end of the player turn.',
        },
    },
})

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
    'toxic_poison': '/static/assets/status-icons/toxic_poison.svg',
    'stagnation': '/static/assets/status-icons/stagnation.svg',
    'bleed': '/static/assets/status-icons/bleed.svg',
    'fire': '/static/assets/status-icons/fire.svg',
    'blockade': '/static/assets/story-status-icons/blockade.svg',
    'attack_blocked': '/static/assets/status-icons/attack_blocked.svg',
    'fragment': '/static/assets/status-icons/fragment.svg',
    'magic_shield_disabled': '/static/assets/story-status-icons/magic-shield-disabled.svg',
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

STORY_TRAITS.update({
    'psionic_connection': {
        'name': {'zh': '灵能链接', 'en': 'Psionic Connection'},
        'description': {
            'zh': '一名具有灵能链接的生物受到伤害时，所有存活的灵能链接生物均摊该次伤害。',
            'en': 'When one connected creature takes damage, all living creatures with Psionic Connection split it evenly.',
        },
    },
    'psionic_sustain': {
        'name': {'zh': '灵能绑定', 'en': 'Psionic Binding'},
        'description': {
            'zh': '白蚁丘存活时，H不会低于1；降至1H时眩晕2次，随后回复至满H。',
            'en': 'While a Termite Mound lives, H cannot fall below 1; at 1 H, become stunned twice, then heal to full.',
        },
    },
    'psionic_fountain': {
        'name': {'zh': '灵能源泉', 'en': 'Psionic Fountain'},
        'description': {
            'zh': '战斗开始时，使所有白蚁失去灵能链接并获得灵能绑定；死亡后令其立刻使用决意。',
            'en': 'At combat start, replace termite Psionic Connection with Psionic Binding; on death, make them use Resolve immediately.',
        },
    },
    'nest_instinct': {
        'name': {'zh': '巢穴本能', 'en': 'Nest Instinct'},
        'description': {
            'zh': '被攻击时，所有生物获得1层暂时力量；生物因灵能绑定复活时，所有生物获得1层力量。',
            'en': 'When attacked, all creatures gain 1 Temporary Power; a Psionic Binding revival gives all creatures 1 Power.',
        },
    },
    'endurance_shell': {
        'name': {'zh': '叶甲', 'en': 'Leaf Carapace'},
        'description': {
            'zh': '玩家每打出1张技能牌，获得等同于层数的护盾。',
            'en': 'Whenever the player plays a Skill, gain Shield equal to its stacks.',
        },
    },
    'toxic_conversion': {
        'name': {'zh': '毒素转化', 'en': 'Toxic Conversion'},
        'description': {
            'zh': '其他单位死亡时获得其全部中毒；自己的中毒结算改为回复等量H。',
            'en': 'Gain all Poison from another unit when it dies; your Poison heals the same amount instead.',
        },
    },
    'bulb': {
        'name': {'zh': '灯泡', 'en': 'Bulb'},
        'description': {
            'zh': '存在时，原本可指向生物的牌只能指向具有灯泡的生物。',
            'en': 'While present, cards that target creatures can target only creatures with Bulb.',
        },
    },
    'hard_shell': {
        'name': {'zh': '硬壳', 'en': 'Hard Shell'},
        'description': {
            'zh': '受到的物理伤害减少等同于层数的数值。',
            'en': 'Reduce incoming physical damage by its stacks.',
        },
    },
    'obstacle': {
        'name': {'zh': '障碍', 'en': 'Obstacle'},
        'description': {
            'zh': '死亡时，使玩家的封锁减少等同于层数的层数。',
            'en': 'On death, remove Blockade from the player equal to its stacks.',
        },
    },
    'segments': {
        'name': {'zh': '体节', 'en': 'Segments'},
        'description': {
            'zh': '死亡时，若层数大于0，召唤1个体节层数-1的同名生物。',
            'en': 'On death, if above 0, summon another copy with 1 fewer Segment.',
        },
    },
    'magic_shield': {
        'name': {'zh': '魔力护盾', 'en': 'Magic Shield'},
        'description': {
            'zh': '受到伤害时，每消耗1M抵消等同于层数的伤害。',
            'en': 'When damaged, spend 1 M to block damage equal to its stacks.',
        },
    },
    'magic_blessing': {
        'name': {'zh': '魔力加护', 'en': 'Magic Blessing'},
        'description': {
            'zh': '以自身的魔力供魔力护盾和特殊行动使用。',
            'en': 'Stores M for Magic Shield and special actions.',
        },
    },
    'magic_reflection': {
        'name': {'zh': '魔力反射', 'en': 'Magic Reflection'},
        'description': {
            'zh': '受到攻击时，消耗1层并获得1M。',
            'en': 'When attacked, spend 1 stack to gain 1 M.',
        },
    },
    'electric_web': {
        'name': {'zh': '电网', 'en': 'Electric Web'},
        'description': {
            'zh': '玩家在回合内每抽1张牌，获得1层缠绕；回合结束时-1层。',
            'en': 'Whenever the player draws during their turn, apply 1 Entangle; lose 1 stack at turn end.',
        },
    },
    'super_beam': {
        'name': {'zh': '超能光束', 'en': 'Super Beam'},
        'description': {
            'zh': '回合结束时-1层；层数结束时使用超能光束。',
            'en': 'Lose 1 stack at turn end; use Super Beam when the countdown ends.',
        },
    },
    'toxic_reflection': {
        'name': {'zh': '剧毒反射', 'en': 'Toxic Reflection'},
        'description': {
            'zh': '每次受到攻击时，对玩家施加等同于层数的中毒。',
            'en': 'Whenever attacked, apply Poison to the player equal to its stacks.',
        },
    },
    'reconstruction': {
        'name': {'zh': '重构', 'en': 'Reconstruction'},
        'description': {
            'zh': '获得碎片时随机改变意图；玩家上回合未使用工厂废料时使用自分解，但不会连续使用。',
            'en': 'Randomize intent when gaining Fragment. If the player did not use Factory Waste last turn, use Self-Disassembly, but never twice in a row.',
        },
    },
    'integration': {
        'name': {'zh': '整合', 'en': 'Integration'},
        'description': {
            'zh': '拥有至少5层碎片时，下一次行动改为雷神之锤。',
            'en': 'At 5 or more Fragment, the next action becomes Mjolnir.',
        },
    },
    'scrap': {
        'name': {'zh': '废料', 'en': 'Scrap'},
        'description': {
            'zh': '行动开始时，将1张工厂废料加入玩家手牌。',
            'en': 'At action start, add 1 Factory Waste to the player hand.',
        },
    },
    'disc': {
        'name': {'zh': '圆盘', 'en': 'Disc'},
        'description': {
            'zh': '受到的物理伤害除以层数，向下取整；回合结束时-1层。',
            'en': 'Divide incoming physical damage by its stacks, rounded down. Lose 1 stack at turn end.',
        },
    },
    'machine_learning': {
        'name': {'zh': '机器学习', 'en': 'Machine Learning'},
        'description': {
            'zh': '玩家回合开始时，对随机2张手牌施加虚无；抽牌阶段结束后，之后抽到的牌均获得虚无。因虚无被放逐的牌进入机械轨道。',
            'en': 'At player turn start, give Void to 2 random cards in hand. Cards drawn after the draw phase gain Void, and cards exiled by Void enter the Mechanical Track.',
        },
    },
    'mechanical_track': {
        'name': {'zh': '机械轨道', 'en': 'Mechanical Track'},
        'description': {
            'zh': '初始含1张雷神之锤、1张齿轮与1张骨头。每次行动转动2次，依次触发轨道顶牌；初始牌移至轨道底，其他牌被消耗。抽牌改为额外转动（抽牌数-1）次，回复E改为获得等量力量。',
            'en': 'Starts with 1 Mjolnir, 1 Cogwheel, and 1 Bone. Each action rotates twice and resolves the top card. Starting cards move to the bottom; other cards are consumed. Drawing becomes one fewer extra rotation than the draw count, and recovering E grants that much Power.',
        },
    },
    'recycling': {
        'name': {'zh': '回收', 'en': 'Recycling'},
        'description': {
            'zh': '轨道顶牌的基础伤害与护盾之和小于10，且不含抽牌效果时，不触发该牌：将其消耗，获得1层力量并额外转动1次。',
            'en': 'If the top card has less than 10 total base damage and Shield and cannot draw, consume it without resolving, gain 1 Power, and rotate once more.',
        },
    },
    'electronic_shield': {
        'name': {'zh': '电子护盾', 'en': 'Electronic Shield'},
        'description': {
            'zh': '获得护盾时，对玩家造成等量伤害。',
            'en': 'Whenever this creature gains Shield, deal the same amount of damage to the player.',
        },
    },
    'toxic_pressure': {
        'name': {'zh': '剧毒压力', 'en': 'Toxic Pressure'},
        'description': {
            'zh': '死亡时，对玩家施加等同于层数的剧毒。',
            'en': 'On death, apply Toxic Poison to the player equal to its stacks.',
        },
    },
    'pressure': {
        'name': {'zh': '压力', 'en': 'Pressure'},
        'description': {
            'zh': '死亡时，对玩家造成等同于层数的伤害。',
            'en': 'On death, deal damage to the player equal to its stacks.',
        },
    },
    'injured_summon': {
        'name': {'zh': '受伤召唤', 'en': 'Injured Summon'},
        'description': {
            'zh': '每累计受到层数点生命值伤害，召唤1个烟，并重新累计。',
            'en': 'After taking H damage equal to its stacks in total, summon 1 Smoke and begin counting again.',
        },
    },
    'cover': {
        'name': {'zh': '掩体', 'en': 'Cover'},
        'description': {
            'zh': '不会死亡；机械鼠藏入后，受到伤害时使其失去隐形。',
            'en': 'Cannot die. When a Mechanical Rat hides here, taking damage removes its Hidden.',
        },
    },
    'hiding': {
        'name': {'zh': '躲藏', 'en': 'Hiding'},
        'description': {
            'zh': '回合结束时，随机选择1个损坏机器躲藏（不展示所选目标）并获得1层隐形；该损坏机器受到伤害时失去隐形。',
            'en': 'At turn end, secretly hide in a random Broken Machine and gain 1 Hidden. Lose Hidden when that machine takes damage.',
        },
        'image_url': '/static/assets/story-trait-icons/hiding.svg',
    },
})

STORY_TRAIT_VALUE_KEYS = {
    'sturdy': 'sturdy',
    'shelter': 'shelter',
    'hidden': 'hidden',
    'turn_shield': 'turn_shield',
    'charging_up': 'charging',
    'charged': 'charged',
    'frenzied': 'frenzy',
    'proliferation': 'proliferation',
    'regeneration': 'regeneration',
    'vampire': 'vampire',
    'limb_survival': 'regenerations',
    'bandage': 'bandage',
    'miracle': 'miracle',
    'psionic_connection': 'psionic_connection',
    'psionic_sustain': 'psionic_sustain',
    'endurance_shell': 'endurance_shell',
    'bulb': 'bulb',
    'hard_shell': 'hard_shell',
    'obstacle': 'obstacle',
    'segments': 'segments',
    'magic_shield': 'magic_shield',
    'magic_blessing': 'magic',
    'magic_reflection': 'magic_reflection',
    'electric_web': 'electric_web',
    'super_beam': 'super_beam',
    'toxic_reflection': 'toxic_reflection',
    'disc': 'disc',
    'toxic_pressure': 'toxic_pressure',
    'pressure': 'pressure',
    'injured_summon': 'injured_summon',
}

STORY_TRAIT_ZERO_VISIBLE = frozenset({'bandage', 'miracle', 'magic_blessing'})

STORY_TRAIT_IMAGE_URLS = {
    'psionic_connection': '/static/assets/story-trait-icons/psionic-connection.svg',
    'psionic_sustain': '/static/assets/story-trait-icons/psionic-binding.svg',
    'psionic_fountain': '/static/assets/story-trait-icons/psionic-fountain.svg',
    'nest_instinct': '/static/assets/story-trait-icons/nest-instinct.svg',
    'endurance_shell': '/static/assets/story-trait-icons/leaf-carapace.svg',
    'toxic_conversion': '/static/assets/story-trait-icons/toxic-conversion.svg',
    'bulb': '/static/assets/story-trait-icons/bulb.svg',
    'hard_shell': '/static/assets/story-trait-icons/hard-shell.svg',
    'obstacle': '/static/assets/story-trait-icons/obstacle.svg',
    'segments': '/static/assets/story-trait-icons/segments.svg',
    'magic_shield': '/static/assets/story-trait-icons/magic-shield.svg',
    'magic_blessing': '/static/assets/story-trait-icons/magic-blessing.svg',
    'magic_reflection': '/static/assets/story-trait-icons/magic-reflection.svg',
    'electric_web': '/static/assets/story-trait-icons/electric-web.svg',
    'super_beam': '/static/assets/story-trait-icons/super-beam.svg',
    'toxic_reflection': '/static/assets/story-trait-icons/toxic-reflection.svg',
    'reconstruction': '/static/assets/story-trait-icons/reconstruction.svg',
    'integration': '/static/assets/story-trait-icons/integration.svg',
    'scrap': '/static/assets/story-trait-icons/scrap.svg',
    'disc': '/static/assets/story-trait-icons/disc.svg',
    'machine_learning': '/static/assets/story-trait-icons/machine-learning.svg',
    'mechanical_track': '/static/assets/story-trait-icons/mechanical-track.svg',
    'recycling': '/static/assets/story-trait-icons/recycling.svg',
    'electronic_shield': '/static/assets/story-trait-icons/electronic-shield.svg',
    'toxic_pressure': '/static/assets/story-trait-icons/toxic-pressure.svg',
    'pressure': '/static/assets/story-trait-icons/pressure.svg',
    'injured_summon': '/static/assets/story-trait-icons/injured-summon.svg',
    'cover': '/static/assets/story-trait-icons/cover.svg',
}

for _trait_id, _image_url in STORY_TRAIT_IMAGE_URLS.items():
    STORY_TRAITS[_trait_id]['image_url'] = _image_url


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
        'description': {'zh': '获得随机1张究级牌', 'en': 'Gain 1 random Ultra card'},
        'script': 'gain_random_ultra_card',
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


# Static event definitions live beside cards, relics and enemies so every
# story executor can consume the same authored content.  Dynamic solo-only
# events are still assembled by ``story_engine`` until their multi-step rules
# have an equally strict shared contract.
STORY_EVENTS = {
    'coop_garden_crossroads': {
        'title': {'zh': '岔路上的园丁车', 'en': "Gardener's Cart"},
        'description': {
            'zh': '一辆废弃园丁车挡在路边。你必须决定如何利用剩余物资。',
            'en': 'An abandoned gardener cart offers a difficult choice.',
        },
        'speaker': {'zh': '废弃园丁车', 'en': "Gardener's Cart"},
        'portrait': '+',
        'biomes': ('garden',),
        'modes': ('solo', 'coop'),
        'coop': {
            'enabled': True,
            'policy': 'unanimous_required',
            'effect_scope': 'all_players',
        },
        'options': (
            {
                'id': 'mend',
                'label': {'zh': '修整工具', 'en': 'Mend the Tools'},
                'description': {
                    'zh': '回复15H。',
                    'en': 'Recover 15 H.',
                },
                'effects': ({'type': 'heal', 'amount': 15},),
            },
            {
                'id': 'supplies',
                'label': {'zh': '搜集物资', 'en': 'Gather Supplies'},
                'description': {
                    'zh': '获得30G。',
                    'en': 'Gain 30 G.',
                },
                'effects': ({'type': 'gold', 'amount': 30},),
            },
            {
                'id': 'risk',
                'label': {'zh': '冒险拆解', 'en': 'Risky Salvage'},
                'description': {
                    'zh': '失去8H（最低保留1H），并获得60G。',
                    'en': 'Lose 8 H, but not below 1 H, and gain 60 G.',
                },
                'effects': (
                    {'type': 'health_loss', 'amount': 8, 'nonlethal': True},
                    {'type': 'gold', 'amount': 60},
                ),
                'requires_confirmation': True,
                'risky': True,
            },
        ),
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


def _character_card(
    card_id,
    *,
    effects=(),
    upgrade_effects=(),
    tags=(),
    upgrade_tags=None,
    upgrade_cost_e=None,
    upgrade_cost_m=None,
    script=None,
    upgrade_script=None,
    target=None,
):
    """Compile one audited character design into the executable card shape."""

    design = STORY_CHARACTER_CARD_DESIGNS[card_id]
    rarity = 'primary' if design.get('rarity') == 'starter' else design['rarity']
    upgrade = None
    if design.get('upgrade_text'):
        upgrade = {
            'description': {
                'zh': design['upgrade_text'],
                'en': design['upgrade_text'],
            },
            'effects': tuple(upgrade_effects),
        }
        if upgrade_tags is not None:
            upgrade['tags'] = tuple(upgrade_tags)
        if upgrade_cost_e is not None:
            upgrade['cost_e'] = max(0, int(upgrade_cost_e))
        if upgrade_cost_m is not None:
            upgrade['cost_m'] = max(0, int(upgrade_cost_m))
        if upgrade_script is not None:
            upgrade['script'] = upgrade_script
    return _card(
        None,
        design['name']['zh'],
        design['name'].get('en') or design['name']['zh'],
        int(design.get('cost_e') or 0),
        design['card_type'],
        rarity,
        design['base_text'],
        cost_m=int(design.get('cost_m') or 0),
        effects=tuple(effects),
        upgrade=upgrade,
        tags=tuple(tags),
        owner=design['character_id'],
        script=script,
        target=target,
    )


STORY_CARDS = {
    'basic': _card('Basic', '基本', 'Basic', 1, 'thorn', 'primary',
                   '对目标造成6D。', effects=(_effect('damage', 6),),
                   upgrade={'description': {'zh': '对目标造成9D。', 'en': 'Deal 9 D.'},
                            'effects': (_effect('damage', 9),)}),
    'rose': _card('Rose', '玫瑰', 'Rose', 1, 'bloom', 'primary',
                  '获得5层护盾。', effects=(_effect('shield', 5),),
                  upgrade={'description': {'zh': '获得8层护盾。', 'en': 'Gain 8 Shield.'},
                           'effects': (_effect('shield', 8),)}),
    'mage_basic': _character_card(
        'mage_basic',
        effects=(_effect('damage', 13),),
        upgrade_effects=(_effect('damage', 18),),
    ),
    'mage_fries': _character_card(
        'mage_fries',
        effects=(_effect('heal', 7),),
        upgrade_effects=(_effect('heal', 10),),
        tags=('exile',),
    ),
    'mage_coffee': _character_card(
        'mage_coffee',
        effects=(_effect('magic', 4),),
        upgrade_effects=(_effect('magic', 5),),
        tags=('exile',),
    ),
    'mage_bone': _character_card(
        'mage_bone',
        effects=(_effect('damage', 9), _effect('shield', 6)),
        upgrade_effects=(_effect('damage', 12), _effect('shield', 8)),
    ),
    'mage_palm_leaf': _character_card(
        'mage_palm_leaf',
        effects=(_effect('shield', 10), _effect('magic', 3)),
        upgrade_effects=(_effect('shield', 14), _effect('magic', 3)),
    ),
    'mage_bubble_bomb': _character_card(
        'mage_bubble_bomb',
        effects=(_effect('damage', 14), _effect('status', 2, status='weak')),
        upgrade_effects=(_effect('damage', 17), _effect('status', 3, status='weak')),
        tags=('wide',),
    ),
    'mage_rock': _character_card(
        'mage_rock',
        effects=(_effect('damage', 7), _effect('status', 2, status='vulnerable')),
        upgrade_effects=(_effect('damage', 9), _effect('status', 3, status='vulnerable')),
    ),
    'mage_missile': _character_card(
        'mage_missile',
        effects=(_effect('damage', 15), _effect('draw', 3)),
        upgrade_effects=(_effect('damage', 17), _effect('draw', 4)),
        tags=('ready',),
    ),
    'mage_rose': _character_card(
        'mage_rose',
        effects=(_effect('shield', 9),),
        upgrade_effects=(_effect('shield', 12),),
    ),
    'mage_orange': _character_card(
        'mage_orange',
        effects=(_effect('damage', 5),),
        upgrade_effects=(_effect('damage', 7),),
        script='return_draw_top',
        upgrade_script='return_draw_top',
    ),
    'mage_coral': _character_card(
        'mage_coral',
        effects=(
            _effect('damage', 17),
            _effect('create_draw_top_copies', 2, magic_swift=1, force_void=True),
        ),
        upgrade_effects=(
            _effect('damage', 22),
            _effect('create_draw_top_copies', 2, magic_swift=1, upgraded=True),
        ),
        tags=('exile',),
    ),
    'mage_leaf': _character_card(
        'mage_leaf',
        effects=(_effect('equipment', 1, script='magic_regeneration'),),
        upgrade_effects=(_effect('equipment', 1, script='magic_regeneration'),),
        upgrade_cost_e=0,
    ),
    'mage_compass': _character_card(
        'mage_compass',
        effects=(_effect('retrieve_from_piles', 1),),
        upgrade_effects=(_effect('retrieve_from_piles', 1),),
        tags=('exile',),
        upgrade_tags=('exile', 'innate'),
    ),
    'mage_blood_blade': _character_card(
        'mage_blood_blade',
        effects=(_effect('magic', 2), _effect('status_self', 1, status='broken')),
        upgrade_effects=(_effect('magic', 3), _effect('status_self', 1, status='broken')),
        script='return_draw_top',
        upgrade_script='return_draw_top',
    ),
    'mage_cotton': _character_card(
        'mage_cotton',
        effects=(_effect('equipment', 4, script='magic_shield'),),
        upgrade_effects=(_effect('equipment', 4, script='magic_shield'),),
        upgrade_tags=('innate',),
    ),
    'mage_sunflower': _character_card(
        'mage_sunflower',
        effects=(_effect('equipment', 2, script='elixir_spend_magic', magic=1),),
        upgrade_effects=(_effect('equipment', 2, script='elixir_spend_magic', magic=1),),
        upgrade_cost_e=0,
    ),
    'mage_quantum': _character_card(
        'mage_quantum',
        effects=(_effect('temporary_swap_costs'),),
        upgrade_effects=(_effect('temporary_swap_costs'),),
        tags=('void', 'exile'),
        upgrade_tags=('exile',),
    ),
    'mage_wing': _character_card(
        'mage_wing',
        effects=(_effect('magic_extra_hits', 9, max_extra=4),),
        upgrade_effects=(_effect('magic_extra_hits', 12, max_extra=4),),
    ),
    'mage_dahlia': _character_card(
        'mage_dahlia',
        effects=(
            _effect('magic', 1),
            _effect('equipment', 3, script='magic_recovery', power=1),
        ),
        upgrade_effects=(
            _effect('magic', 1),
            _effect('equipment', 4, script='magic_recovery', power=1),
        ),
    ),
    'mage_soil': _character_card(
        'mage_soil',
        effects=(_effect('shield', 32), _effect('overload', 1)),
        upgrade_effects=(_effect('shield', 40), _effect('overload', 1)),
        tags=('exile',),
    ),
    'mage_tentacle': _character_card(
        'mage_tentacle',
        effects=(_effect('equipment', 1, script='turn_draw'),),
        upgrade_effects=(_effect('equipment', 1, script='turn_draw'),),
        upgrade_tags=('innate',),
    ),
    'mage_seed': _character_card(
        'mage_seed',
        effects=(_effect('self_magic_swift', 1), _effect('magic', 4)),
        upgrade_effects=(_effect('self_magic_swift', 1), _effect('magic', 5)),
    ),
    'mage_tomato': _character_card(
        'mage_tomato',
        effects=(_effect('magic_spent_damage', 13),),
        upgrade_effects=(_effect('magic_spent_damage', 18),),
    ),
    'mage_stick': _character_card(
        'mage_stick',
        effects=(_effect('magic_enemy_count', 2),),
        upgrade_effects=(_effect('magic_enemy_count', 3),),
    ),
    'mage_iodine': _character_card(
        'mage_iodine',
        effects=(_effect('equipment', 7, script='end_electric_all'),),
        upgrade_effects=(_effect('equipment', 7, script='end_electric_all'),),
        upgrade_cost_e=0,
    ),
    'mage_basil': _character_card(
        'mage_basil',
        effects=(_effect('conditional_magic', 2, zero_amount=4),),
        upgrade_effects=(_effect('conditional_magic', 2, zero_amount=6),),
    ),
    'mage_balsam': _character_card(
        'mage_balsam',
        effects=(_effect('generate_magic_cards', 3),),
        upgrade_effects=(_effect('generate_magic_cards', 3, upgraded=True),),
    ),
    'mage_lightning': _character_card(
        'mage_lightning',
        effects=(_effect('electric_damage', 7, hits=2),),
        upgrade_effects=(_effect('electric_damage', 10, hits=2),),
        tags=('wide',),
    ),
    'mage_shovel': _character_card(
        'mage_shovel',
        effects=(_effect('untargetable', 1),),
        upgrade_effects=(_effect('untargetable', 1),),
        tags=('void', 'exile'),
        upgrade_tags=('exile',),
    ),
    'mage_sponge': _character_card(
        'mage_sponge',
        effects=(_effect('magic', 8), _effect('magic_overload', 12)),
        upgrade_effects=(_effect('magic', 8), _effect('magic_overload', 12)),
        upgrade_tags=('retain',),
    ),
    'mage_pearl': _character_card(
        'mage_pearl',
        effects=(_effect('consume_magic_draw', 7, max_magic=10),),
        upgrade_effects=(_effect('consume_magic_draw', 10, max_magic=10),),
        tags=('exile',),
        upgrade_tags=(),
    ),
    'mage_blueberry': _character_card(
        'mage_blueberry',
        effects=(_effect('equipment', 5, script='electric_on_m_card'),),
        upgrade_effects=(_effect('equipment', 5, script='electric_on_m_card'),),
        upgrade_cost_e=1,
    ),
    'mage_battery_delayed': _character_card(
        'mage_battery_delayed',
        effects=(_effect('equipment', 2, script='delayed_magic'),),
        upgrade_effects=(_effect('equipment', 2, script='delayed_magic'),),
        upgrade_cost_e=0,
    ),
    'mage_serration': _character_card(
        'mage_serration',
        effects=(_effect('turn_damage_multiplier', 2),),
        upgrade_effects=(_effect('turn_damage_multiplier', 2),),
        upgrade_tags=('retain',),
    ),
    'mage_starfish': _character_card(
        'mage_starfish',
        effects=(_effect('shield', 7), _effect('magic', 2)),
        upgrade_effects=(_effect('shield', 10), _effect('magic', 2)),
        script='requires_no_last_turn_damage',
        upgrade_script='requires_no_last_turn_damage',
    ),
    'mage_honey_shield': _character_card(
        'mage_honey_shield',
        effects=(_effect('shield_remaining_magic', 12),),
        upgrade_effects=(_effect('shield_remaining_magic', 16),),
    ),
    'mage_constellation': _character_card(
        'mage_constellation',
        effects=(_effect('damage', 34), _effect('temporary_magic_heavy', 1)),
        upgrade_effects=(_effect('damage', 42), _effect('temporary_magic_heavy', 1)),
    ),
    'mage_mask': _character_card(
        'mage_mask',
        effects=(_effect('magic_spend_shield_turn', 3),),
        upgrade_effects=(_effect('magic_spend_shield_turn', 3),),
        tags=('exile',),
        upgrade_tags=(),
    ),
    'mage_wind': _character_card(
        'mage_wind',
        effects=(_effect('discard_nonmagic_draw_magic', 0),),
        upgrade_effects=(_effect('discard_nonmagic_draw_magic', 1),),
    ),
    'mage_chromosome': _character_card(
        'mage_chromosome',
        effects=(_effect('equipment', 2, script='magic_gain_shield'),),
        upgrade_effects=(_effect('equipment', 3, script='magic_gain_shield'),),
    ),
    'mage_beeswax': _character_card(
        'mage_beeswax',
        effects=(_effect('shield_damage_halved', 1), _effect('shield', 5)),
        upgrade_effects=(_effect('shield_damage_halved', 1), _effect('shield', 8)),
    ),
    'mage_balloon': _character_card(
        'mage_balloon',
        effects=(_effect('draw_then_topdeck', 3, choose=2),),
        upgrade_effects=(_effect('draw_then_topdeck', 4, choose=2),),
    ),
    'mage_air': _character_card(
        'mage_air',
        effects=(_effect('multiply_shield', 2),),
        upgrade_effects=(_effect('multiply_shield', 3),),
    ),
    'mage_rmb': _character_card(
        'mage_rmb',
        effects=(_effect('next_combat_magic', 2),),
        upgrade_effects=(_effect('next_combat_magic', 2),),
        upgrade_tags=('retain',),
    ),
    'capacitor': _character_card(
        'capacitor',
        effects=(_effect('equipment', 50, script='static_boost'),),
        upgrade_effects=(_effect('equipment', 75, script='static_boost'),),
    ),
    'battery': _character_card(
        'battery',
        effects=(_effect('equipment', 4, script='static_on_attacked'),),
        upgrade_effects=(_effect('equipment', 6, script='static_on_attacked'),),
    ),
    'plasma': _character_card(
        'plasma',
        effects=(_effect('electric_damage', 6, hits=5),),
        upgrade_effects=(_effect('electric_damage', 8, hits=5),),
    ),
    'ruby': _character_card(
        'ruby',
        effects=(_effect('equipment', 8, script='static_damage'),),
        upgrade_effects=(_effect('equipment', 11, script='static_damage'),),
    ),
    'mage_ruby': _character_card(
        'mage_ruby',
        effects=(_effect('equipment', 3, script='static_shield'),),
        upgrade_effects=(_effect('equipment', 4, script='static_shield'),),
    ),
    'mage_capacitor': _character_card(
        'mage_capacitor',
        effects=(_effect('equipment', 1, script='static_magic'),),
        upgrade_effects=(_effect('equipment', 1, script='static_magic'),),
        upgrade_tags=('innate',),
    ),
    'copper_rod': _character_card(
        'copper_rod',
        effects=(_effect('shield', 8), _effect('static', 3)),
        upgrade_effects=(_effect('shield', 10), _effect('static', 6)),
        target='enemy',
    ),
    'mage_copper_rod': _character_card(
        'mage_copper_rod',
        effects=(_effect('multiply_static', 2),),
        upgrade_effects=(_effect('multiply_static', 3),),
        target='enemy',
    ),
    'mage_lithium': _character_card(
        'mage_lithium',
        effects=(_effect('equipment', 1, script='static_draw'),),
        upgrade_effects=(_effect('equipment', 1, script='static_draw'),),
        upgrade_cost_e=1,
    ),
    'electronic_missile': _character_card(
        'electronic_missile',
        effects=(_effect('electric_damage', 9), _effect('draw', 2)),
        upgrade_effects=(_effect('electric_damage', 11), _effect('draw', 3)),
        tags=('ready',),
    ),
    'mage_electronic_missile': _character_card(
        'mage_electronic_missile',
        effects=(_effect('electric_damage', 5), _effect('draw', 1)),
        upgrade_effects=(_effect('electric_damage', 7), _effect('draw', 1)),
        tags=('ready',),
        upgrade_tags=('ready',),
        script='return_draw_top',
        upgrade_script='return_draw_top',
    ),
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
                 '对目标造成8D，并施加1层易伤。',
                 effects=(_effect('damage', 8), _effect('status', 1, status='vulnerable')),
                 upgrade={'description': {'zh': '对目标造成8D，并施加2层易伤。', 'en': 'Deal 8 D and apply 2 Vulnerable.'},
                          'effects': (_effect('damage', 8), _effect('status', 2, status='vulnerable'))}),
    'torch': _card('Torch', '火把', 'Torch', 1, 'thorn', 'common',
                   '对目标造成9D；主动丢弃自己1张其他手牌，然后抽1张牌。',
                   effects=(_effect('damage', 9), _effect('active_discard', 1, exact=True), _effect('draw', 1)),
                   upgrade={'description': {'zh': '对目标造成11D；主动丢弃自己1张其他手牌，然后抽2张牌。', 'en': 'Deal 11 D; actively discard 1 other card, then draw 2.'},
                            'effects': (_effect('damage', 11), _effect('active_discard', 1, exact=True), _effect('draw', 2))}),
    'antibody': _card('Antibody', '抗体', 'Antibody', 1, 'bloom', 'rare',
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
                        tags=('exile',),
                        effects=(_effect('active_discard', 99, exact=False), _effect('draw_selected', 0)),
                        upgrade={'description': {'zh': '主动丢弃自己任意张其他手牌，然后抽等量的牌。', 'en': 'Actively discard any number of other cards, then draw the same number.'},
                                 'tags': (),
                                 'effects': (_effect('active_discard', 99, exact=False), _effect('draw_selected', 0))}),
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
            'description': {'zh': '对目标造成19D；此牌可无限升级。', 'en': 'Deal 19 D. This card can be upgraded indefinitely.'},
            'effects': (_effect('damage', 19),),
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
        '对目标造成20D；下回合开始时获得1层禁攻。',
        tags=('wide',),
        effects=(
            _effect('damage', 20),
            _effect('delayed_player_status', 1, status='attack_blocked'),
        ),
        upgrade={
            'description': {'zh': '对目标造成24D；下回合开始时获得1层禁攻。', 'en': 'Deal 24 D; gain 1 Attack Blocked at the start of your next turn.'},
            'effects': (
                _effect('damage', 24),
                _effect('delayed_player_status', 1, status='attack_blocked'),
            ),
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
        'Bamboo', '竹子', 'Bamboo', 2, 'thorn', 'ultra',
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
        '主动丢弃自己所有当前E花费大于0的其他手牌，然后抽等量的当前0E牌。',
        effects=(_effect('active_discard_all', filter='positive_e'), _effect('draw_selected', 0, filter='zero_e')),
        upgrade={
            'description': {'zh': '主动丢弃自己所有当前E花费大于0的其他手牌，然后抽丢弃数量+1张当前0E牌。', 'en': 'Actively discard all other cards currently costing more than 0 E, then draw that many plus 1 cards currently costing 0 E.'},
            'effects': (_effect('active_discard_all', filter='positive_e'), _effect('draw_selected', 1, filter='zero_e')),
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
        '回复自己2E；此牌获得1层迅捷。',
        effects=(_effect('elixir', 2), _effect('self_swift', 1)),
        upgrade={
            'cost_e': 2,
            'description': {'zh': '回复自己2E；此牌获得1层迅捷。', 'en': 'Recover 2 E; this card gains 1 Swift.'},
            'effects': (_effect('elixir', 2), _effect('self_swift', 1)),
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
    'factory_waste': _card(
        None,
        '工厂废料',
        'Factory Waste',
        1,
        'infect',
        'special',
        '回合结束时若仍在手牌中，受到8D；打出时，使重构机获得1层碎片和1层力量。',
        tags=('exile',),
        effects=(),
        script='factory_waste',
    ),
}

STORY_CARD_IMAGE_URLS = {
    'capacitor': '/static/assets/story-card-art/capacitor.svg',
    'confused': '/static/assets/story-card-art/confused.svg',
    'copper_rod': '/static/assets/story-card-art/copper-rod.svg',
    'dandelion_seed': '/static/assets/story-card-art/dandelion-seed.svg',
    'enchanted_amulet': '/static/assets/story-card-art/enchanted-amulet.svg',
    'fatigued': '/static/assets/story-card-art/fatigued.svg',
    'injury': '/static/assets/story-card-art/injury.svg',
    'mage_balsam': '/static/assets/story-card-art/mage-balsam.svg',
    'mage_basic': '/static/assets/story-card-art/mage-basic.svg',
    'mage_basil': '/static/assets/story-card-art/mage-basil.svg',
    'mage_beeswax': '/static/assets/story-card-art/mage-beeswax.svg',
    'mage_blood_blade': '/static/assets/story-card-art/mage-blood-blade.svg',
    'mage_blueberry': '/static/assets/story-card-art/mage-blueberry.svg',
    'mage_bubble_bomb': '/static/assets/story-card-art/mage-bubble-bomb.svg',
    'mage_capacitor': '/static/assets/story-card-art/mage-capacitor.svg',
    'mage_copper_rod': '/static/assets/story-card-art/mage-copper-rod.svg',
    'mage_honey_shield': '/static/assets/story-card-art/mage-honey-shield.svg',
    'mage_iodine': '/static/assets/story-card-art/mage-iodine.svg',
    'mage_lithium': '/static/assets/story-card-art/mage-lithium.svg',
    'mage_missile': '/static/assets/story-card-art/mage-missile.svg',
    'mage_palm_leaf': '/static/assets/story-card-art/mage-palm-leaf.svg',
    'mage_quantum': '/static/assets/story-card-art/mage-quantum.svg',
    'mage_rmb': '/static/assets/story-card-art/mage-rmb.svg',
    'mage_rose': '/static/assets/story-card-art/mage-rose.svg',
    'mage_ruby': '/static/assets/story-card-art/mage-ruby.svg',
    'mage_shovel': '/static/assets/story-card-art/mage-shovel.svg',
    'mage_sponge': '/static/assets/story-card-art/mage-sponge.svg',
    'mage_starfish': '/static/assets/story-card-art/mage-starfish.svg',
    'mage_stick': '/static/assets/story-card-art/mage-stick.svg',
    'mage_sunflower': '/static/assets/story-card-art/mage-sunflower.svg',
    'mage_wind': '/static/assets/story-card-art/mage-wind.svg',
    'magic_acid': '/static/assets/story-card-art/magic-acid.svg',
    'magic_assembler': '/static/assets/story-card-art/magic-assembler.svg',
    'magic_feather': '/static/assets/story-card-art/magic-feather.svg',
    'magic_shell': '/static/assets/story-card-art/magic-shell.svg',
    'moon_rock': '/static/assets/story-card-art/moon-rock.svg',
    'plasma': '/static/assets/story-card-art/plasma.svg',
    'rmb': '/static/assets/story-card-art/rmb.svg',
    'shell': '/static/assets/story-card-art/shell.svg',
    'sand_dust': '/static/assets/story-card-art/sand-dust.svg',
    'slimed': '/static/assets/story-card-art/slimed.svg',
    'soul_splitter': '/static/assets/story-card-art/soul-splitter.svg',
    'startled': '/static/assets/story-card-art/startled.svg',
    'static_electricity': '/static/assets/story-card-art/static-electricity.svg',
    'factory_waste': '/static/assets/story-card-art/factory-waste.svg',
    'unrelenting': '/static/assets/story-card-art/unrelenting.svg',
}

STORY_CARD_UPGRADED_IMAGE_URLS = {
    'mage_basic': '/static/assets/story-card-art/mage-basic-upgraded.svg',
}

for _card_id, _image_url in STORY_CARD_IMAGE_URLS.items():
    STORY_CARDS[_card_id]['image_url'] = _image_url
    STORY_CARDS[_card_id]['upgraded_image_url'] = STORY_CARD_UPGRADED_IMAGE_URLS.get(
        _card_id,
        _image_url,
    )


def _enchantment_book(zh, en, description_zh, description_en, rarity, script,
                      *, target='none', amount=0, character_id=None, image=''):
    return {
        'name': {'zh': zh, 'en': en},
        'description': {'zh': description_zh, 'en': description_en},
        'rarity': rarity,
        'script': script,
        'target': target,
        'amount': amount,
        'character_id': character_id,
        'image_url': f'/static/assets/story-enchantment-books/{image}',
    }


STORY_ENCHANTMENT_BOOKS = {
    'sharp': _enchantment_book('锋利', 'Sharpness', '选择一张手中的攻击牌，使其在本场战斗中获得威力15。', 'Choose an Attack in hand. It gains 15 Potency for this combat.', 'common', 'damage_bonus', target='attack_card', amount=15, image='sharp.svg'),
    'protection': _enchantment_book('保护', 'Protection', '选择一张手中的技能牌，使其在本场战斗中获得牢固8；使用后清空。', 'Choose a Skill in hand. It gains 8 Firmness for this combat, cleared after use.', 'common', 'shield_bonus_once', target='skill_card', amount=8, image='defend.svg'),
    'durability': _enchantment_book('耐久', 'Durability', '选择一张手中的放逐牌，使其在本场战斗中失去放逐。', 'Choose an Exile card in hand. It loses Exile for this combat.', 'ultra', 'remove_exile', target='exile_card', image='durability.svg'),
    'efficiency': _enchantment_book('效率', 'Efficiency', '选择一张手中的牌，使其在本场战斗中获得迅捷1。', 'Choose a card in hand. It gains Swift 1 for this combat.', 'rare', 'swift', target='card', amount=1, image='efficiency.svg'),
    'underwater_rapid_digging': _enchantment_book('水下速掘', 'Underwater Rapid Digging', '选择一张手中的牌，使其在本回合获得暂时迅捷3。', 'Choose a card in hand. It gains Temporary Swift 3 this turn.', 'rare', 'temporary_swift', target='card', amount=3, image='underwater rapid digging.svg'),
    'sweeping_blade': _enchantment_book('横扫之刃', 'Sweeping Blade', '选择一张手中的攻击牌，使其在本场战斗中获得广域打击。', 'Choose an Attack in hand. It gains Wide Strike for this combat.', 'rare', 'wide', target='attack_card', image='sweeping blade.svg'),
    'armor_break': _enchantment_book('破甲', 'Armor Break', '选择一张手中的攻击牌，使其在本场战斗中获得破甲：使用时先清除目标护盾，再结算后续效果。', 'Choose an Attack in hand. It breaks the target Shield before resolving its effects.', 'rare', 'armor_break', target='attack_card', image='armor break.svg'),
    'attract_lightning': _enchantment_book('引雷', 'Attract Lightning', '选择一张手中的攻击牌，使其在本场战斗中获得电击威力15。仅限魔法师。', 'Choose an Attack in hand. It gains 15 Electric Potency for this combat. Mage only.', 'common', 'electric_damage', target='attack_card', amount=15, character_id='mage', image='attract lightning.svg'),
    'binding_curse': _enchantment_book('绑定诅咒', 'Binding Curse', '选择3张手中的牌，使其在本场战斗中获得保留。', 'Choose 3 cards in hand. They gain Retain for this combat.', 'rare', 'retain', target='three_cards', image='binding curse.svg'),
    'vanishing_curse': _enchantment_book('消失诅咒', 'Vanishing Curse', '选择任意张手中的牌，使其在本场战斗中获得放逐与虚无。', 'Choose any number of cards in hand. They gain Exile and Void for this combat.', 'rare', 'exile_void', target='any_cards', image='vanishing curse.svg'),
    'dense': _enchantment_book('致密', 'Dense', '选择一张手中的攻击牌，使其在本回合获得暂时沉重1，并在本场战斗中获得威力30。', 'Choose an Attack in hand. It gains Temporary Heavy 1 this turn and 30 Potency for this combat.', 'rare', 'dense', target='attack_card', amount=30, image='dense.svg'),
    'charge': _enchantment_book('突进', 'Charge', '选择一张手中的牌，使其下一次使用时抽牌至手牌满。', 'Choose a card in hand. The next time it is used, draw until the hand is full.', 'rare', 'draw_to_full_once', target='card', image='charge.svg'),
    'magic_yggdrasil': _enchantment_book('魔法世界树之叶', 'Magic Yggdrasil Leaf', '受到致命伤害时自动消耗：免疫该次伤害，无敌一回合并获得再生8。', 'Automatically consumed on lethal damage: prevent it, become invincible for one round, and gain 8 Regeneration.', 'ultra', 'lethal_guard', amount=8, image='magic yggdrasil.svg'),
    'fall_cushioning': _enchantment_book('摔落缓冲', 'Fall Cushioning', '选择一张手中的牌，使其下一次使用时获得1层圆盘。', 'Choose a card in hand. The next time it is used, gain 1 Disc.', 'common', 'disc_once', target='card', amount=1, image='fall cushioning.svg'),
    'flame_bonus': _enchantment_book('火焰附加', 'Flame Bonus', '选择一张手中的攻击牌，使其下一次命中时施加8层灼烧。', 'Choose an Attack in hand. Its next hit applies 8 Burn.', 'rare', 'fire_on_hit_once', target='attack_card', amount=8, image='flame bonus.svg'),
    'fire_protection': _enchantment_book('火焰保护', 'Fire Protection', '选择一张手中的牌，使其下一次使用时获得3层负面状态免疫。', 'Choose a card in hand. The next time it is used, gain 3 Negative Status Immunity.', 'rare', 'immunity_once', target='card', amount=3, image='fire protection.svg'),
    'puncture': _enchantment_book('穿刺', 'Puncture', '选择一张手中的攻击牌，使其在本场战斗中击杀敌人时随机对另一名敌人再使用一次。', 'Choose an Attack in hand. When it kills an enemy this combat, use it again on another random enemy.', 'rare', 'repeat_on_kill', target='attack_card', image='puncture.svg'),
    'unlimited': _enchantment_book('无限', 'Unlimited', '选择一本你持有的附魔书，获得它的复制。', 'Choose an enchantment book you own and gain a copy of it.', 'ultra', 'copy_book', target='book', image='unlimited.svg'),
    'repel': _enchantment_book('击退', 'Repel', '选择一张手中的牌，使其下一次使用时对目标施加4层虚弱。', 'Choose a card in hand. The next time it is used, apply 4 Weak to the target.', 'rare', 'weak_once', target='card', amount=4, image='repel.svg'),
    'snatch': _enchantment_book('抢夺', 'Snatch', '选择一张手中的攻击牌，使其在本场战斗中击杀敌人时令战斗结束后的卡牌奖励翻倍。', 'Choose an Attack in hand. If it kills an enemy this combat, double the post-combat card reward.', 'ultra', 'double_reward_on_kill', target='attack_card', image='snatch.svg'),
    'loyalty': _enchantment_book('忠诚', 'Loyalty', '选择一张手中的非0E0M牌，使其在本场战斗中获得回转。', 'Choose a non-zero-cost card in hand. It returns to hand after use for this combat.', 'ultra', 'rebound', target='cost_card', image='loyalty.svg'),
    'experience_patch': _enchantment_book('经验修补', 'Experience Patch', '选择一张手中的牌，使其在本场战斗中改为用1H支付一点花费。', 'Choose a card in hand. For this combat, pay 1 H for one point of its cost.', 'rare', 'health_cost', target='cost_card', amount=1, image='experience patch.svg'),
    'multiple_shots': _enchantment_book('多重射击', 'Multiple Shots', '选择一张手中的牌，使其下一次使用时再使用一次。', 'Choose a card in hand. The next time it is used, use it one additional time.', 'ultra', 'repeat_once', target='card', amount=1, image='multiple shots.svg'),
    'strength': _enchantment_book('力量', 'Strength', '选择一张手中的牌，使其下一次使用时获得3力量。', 'Choose a card in hand. The next time it is used, gain 3 Power.', 'rare', 'power_once', target='card', amount=3, image='strength.svg'),
    'impact': _enchantment_book('冲击', 'Impact', '选择一张手中的牌，使其下一次使用时对目标施加2层虚弱和2层易伤。', 'Choose a card in hand. The next time it is used, apply 2 Weak and 2 Vulnerable to the target.', 'rare', 'impact_once', target='card', amount=2, image='impact.svg'),
    'rapids': _enchantment_book('激流', 'Rapids', '选择一张手中的牌，使其下一次使用时从抽牌堆和弃牌堆分别选择1张牌加入手中。', 'Choose a card in hand. The next time it is used, choose 1 card each from draw and discard piles and add them to hand.', 'rare', 'retrieve_once', target='card', image='rapids.svg'),
    'thorns': _enchantment_book('荆棘', 'Thorns', '选择一张手中的牌，使其下一次使用时获得3层反射。', 'Choose a card in hand. The next time it is used, gain 3 Reflection.', 'rare', 'reflection_once', target='card', amount=3, image='thorns.svg'),
    'wind_blast': _enchantment_book('风爆', 'Wind Blast', '选择一张手中的牌，使其下一次使用时对目标施加4层易伤。', 'Choose a card in hand. The next time it is used, apply 4 Vulnerable to the target.', 'rare', 'vulnerable_once', target='card', amount=4, image='wind blast.svg'),
    'warp': _enchantment_book('传送器', 'Warp', '逃离一场非首领战斗，失去10H且不获得奖励。', 'Escape a non-boss combat, lose 10 H, and receive no reward.', 'rare', 'escape', amount=10, image='warp.svg'),
}


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
    and definition.get('owner') in ('primary', 'neutral')
)


def story_reward_card_ids(character_id='common_flower'):
    owner = 'primary' if str(character_id or 'common_flower') == 'common_flower' else str(character_id)
    return tuple(
        card_id
        for card_id, definition in STORY_CARDS.items()
        if definition['rarity'] in ('common', 'rare', 'ultra')
        and definition['type'] not in ('curse', 'infect')
        and definition.get('owner') == owner
    )


def story_shop_card_ids(character_id='common_flower'):
    owner = 'primary' if str(character_id or 'common_flower') == 'common_flower' else str(character_id)
    return tuple(
        card_id
        for card_id, definition in STORY_CARDS.items()
        if definition['rarity'] in ('common', 'rare', 'ultra')
        and definition['type'] not in ('curse', 'infect')
        and definition.get('owner') in (owner, 'neutral')
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
    # Every talent may stack, including character and boss talents that are
    # normally unique. This public field must mirror the engine rule.
    stackable = True
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
    'magic_source': _relic(
        STORY_CHARACTER_RELIC_DESIGNS['magic_source']['name']['zh'],
        STORY_CHARACTER_RELIC_DESIGNS['magic_source']['name'].get('en')
        or STORY_CHARACTER_RELIC_DESIGNS['magic_source']['name']['zh'],
        STORY_CHARACTER_RELIC_DESIGNS['magic_source']['effect_text'],
        rarity='special',
        script='turn_magic',
        amount=1,
        stackable=False,
        shop_excluded=True,
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
    'blade': _relic('利刃', 'Blade', '本场战斗第一次造成伤害后，对目标施加1层易伤。', rarity='rare', script='first_attack_vulnerable', amount=1),
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
    'world_tree_leaf': _relic('世界树之叶', 'World Tree Leaf', '每片世界树之叶可在本次旅程中抵消1次死亡，清除效果并回复至满H。', rarity='special', script='revive'),
    'dandelion_blessing': _relic('蒲公英加护', 'Dandelion Blessing', '战斗开始时获得7层护盾。', rarity='special', script='opening_shield', amount=7),
    'coward_defense': _relic('懦夫才防', 'Cowardly Defense', '每回合多回复1E；卡牌奖励和商店中不再出现技能牌。', rarity='special', script='boss_no_bloom', amount=1),
    'return_to_origin': _relic('返璞归真', 'Return to Origin', '所有基础牌的基础数值变为1.5倍。', rarity='special', script='primary_multiplier', amount=1.5),
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
    lunatic_initial=None,
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
    if lunatic_initial:
        definition['lunatic_initial'] = deepcopy(lunatic_initial)
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
        _move('膨胀', 'Inflate', _effect('gain_status', 4, status='pressure', lunatic_amount=5)),
        _move('爆炸', 'Explode', _effect('damage', 7, lunatic_amount=9), _effect('self_kill', reason='burst')),
    ), script='ocean_bubble', traits=('pressure',), initial={'shield': 10}, lunatic_health=13),
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
        _move('撕咬', 'Bite', _effect('damage', 7, hits=2, lunatic_amount=8)),
    ), traits=('bloodthirsty',), lunatic_health=93),
    'ocean_shell': _enemy('贝壳', 'Shell', 114, (
        _move('吐出', 'Spit Out', _effect('damage', 11, lunatic_amount=13), _effect('summon', 1, enemy_id='ocean_pearl')),
        _move('拉回', 'Pull Back', _effect('damage', 7, hits=2, lunatic_amount=8), _effect('gain_power', 2, lunatic_amount=3), _effect('consume_pearls_damage', 7, lunatic_amount=8)),
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

# Stage 2: Jungle. These definitions follow the latest development workbook.
STORY_ENEMIES.update({
    'termite_soldier': _enemy('白兵蚁', 'Soldier Termite', 56, (
        _move('啃咬', 'Bite', _effect('damage', 6, lunatic_amount=8), _effect('gain_shield', 8, lunatic_amount=10)),
        _move('头锤', 'Headbutt', _effect('damage', 14, lunatic_amount=16), _effect('self_damage', 14, lunatic_amount=16)),
        _move('振翅', 'Flutter', _effect('gain_power', 3, lunatic_amount=4), _effect('gain_shield', 12)),
        _move('决意', 'Resolve', _effect('damage', 20, lunatic_amount=23), _effect('self_kill')),
    ), traits=('psionic_connection',), initial={'psionic_connection': 1}, lunatic_health=62),
    'termite_worker': _enemy('白工蚁', 'Worker Termite', 32, (
        _move('鼓舞', 'Inspire', _effect('damage', 4, lunatic_amount=5), _effect('allies_power', 1)),
        _move('护卫', 'Guard', _effect('damage', 6, lunatic_amount=7), _effect('lowest_ally_shield', 8, lunatic_amount=9)),
        _move('狂暴', 'Frenzy', _effect('damage', 3, hits=3, lunatic_amount=4), _effect('gain_power', 1)),
        _move('决意', 'Resolve', _effect('damage', 16, lunatic_amount=19), _effect('self_kill')),
    ), script='termite_worker', traits=('psionic_connection',), initial={'psionic_connection': 1}, lunatic_health=35),
    'termite_overmind': _enemy('白蚁主宰者', 'Termite Overmind', 79, (
        _move('心神震慑', 'Mind Shock', _effect('player_status', 1, status='weak'), _effect('player_status', 1, status='blockade')),
        _move('灵能爆发', 'Psionic Burst', _effect('damage', 4, hits=3, lunatic_amount=5)),
        _move('决意', 'Resolve', _effect('damage', 23, lunatic_amount=26), _effect('self_kill')),
    ), traits=('psionic_connection',), initial={'psionic_connection': 1}, lunatic_health=86),
    'leafbug': _enemy('叶虫', 'Leafbug', 36, (
        _move('干扰', 'Interfere', _effect('gain_shield', 8, lunatic_amount=10), _effect('player_status', 1, status='weak')),
        _move('盾击', 'Shield Bash', _effect('damage_from_shield', 6, divisor=4, lunatic_amount=7)),
    ), traits=('endurance_shell', 'sturdy'), initial={'shield': 10, 'sturdy': 99, 'endurance_shell': 5},
       lunatic_initial={'shield': 15, 'endurance_shell': 7}, lunatic_health=39),
    'dark_ladybug': _enemy('深色瓢虫', 'Dark Ladybug', 84, (
        _move('毒气', 'Poison Gas', _effect('player_status', 3, status='poison', lunatic_amount=5), _effect('player_status', 2, status='stagnation')),
        _move('撞击', 'Collision', _effect('damage', 14, lunatic_amount=17), _effect('player_status', 4, status='poison')),
    ), lunatic_health=91),
    'jungle_firefly': _enemy('萤火虫', 'Firefly', 74, (
        _move('吸引', 'Attract', _effect('gain_status', 3, status='reflection', lunatic_amount=4), _effect('gain_status', 1, status='bulb')),
        _move('放电', 'Discharge', _effect('damage', 4, hits=3, lunatic_amount=5), _effect('gain_power', 2)),
    ), traits=('bulb',), lunatic_health=81),
    'jungle_wasp': _enemy('胡蜂', 'Wasp', 43, (
        _move('蓄势', 'Ready', _effect('gain_shield', 11, lunatic_amount=14)),
        _move('毒针', 'Poison Needle', _effect('damage', 13, lunatic_amount=15), _effect('player_status', 5, status='poison', lunatic_amount=6)),
    ), lunatic_health=47),
    'jungle_fly': _enemy('苍蝇', 'Fly', 46, (
        _move('误导', 'Mislead', _effect('allies_status', 1, status='evade')),
        _move('撞击', 'Collision', _effect('damage', 7, lunatic_amount=9)),
    ), script='jungle_fly', initial={'evade': 1}, lunatic_initial={'evade': 2}, lunatic_health=51),
    'jungle_mushroom': _enemy('蘑菇', 'Mushroom', 36, (
        _move('毒素治疗', 'Poison Heal', _effect('allies_heal', 12, lunatic_amount=14), _effect('allies_shield', 12, lunatic_amount=14), _effect('allies_status', 6, status='poison', lunatic_amount=7)),
        _move('爆裂', 'Burst', _effect('consume_status_damage', 0, status='poison', divisor=4, lunatic_divisor=3)),
    ), script='jungle_mushroom', traits=('toxic_conversion',), initial={'shield': 20},
       lunatic_initial={'shield': 35}, lunatic_health=40),
    'pumpkin': _enemy('南瓜', 'Pumpkin', 54, (
        _move('撞击', 'Collision', _effect('damage', 12, lunatic_amount=14), _effect('gain_power', 1)),
        _move('狂击', 'Frenzy', _effect('damage', 7, hits=2, lunatic_amount=8)),
    ), script='pumpkin', traits=('sturdy',), initial={'shield': 54, 'sturdy': 99},
       lunatic_initial={'shield': 59}, lunatic_health=59),
    'snail': _enemy('蜗牛', 'Snail', 89, (
        _move('缩壳', 'Retract Shell', _effect('gain_status', 2, status='hard_shell', lunatic_amount=3), _effect('gain_power', 3, lunatic_amount=4)),
        _move('冲刺', 'Sprint', _effect('damage', 19, lunatic_amount=22), _effect('clear_status', 0, status='hard_shell')),
    ), traits=('hard_shell',), initial={'hard_shell': 2}, lunatic_initial={'hard_shell': 3}, lunatic_health=96),
    'bush': _enemy('灌木', 'Bush', 156, (
        _move('抖落', 'Shake Off', _effect('summon', 1, enemy_id='jungle_firefly', health_percent=50)),
        _move('吸引', 'Attract', _effect('summon', 1, enemy_id='jungle_fly', health_percent=50), _effect('summon', 1, enemy_id='leafbug', health_percent=50)),
        _move('养分', 'Nutrients', _effect('allies_power', 2, lunatic_amount=3), _effect('allies_heal', 20, lunatic_amount=24)),
    ), traits=('turn_shield', 'sturdy', 'shelter'), initial={'turn_shield': 5, 'sturdy': 99, 'shelter': 15},
       lunatic_initial={'turn_shield': 7, 'shelter': 20}, lunatic_health=170),
    'spider_cave': _enemy('蜘蛛洞', 'Spider Cave', 110, (
        _move('散网', 'Scatter Web', _effect('add_draw_card', 2, card_id='slimed'), _effect('player_status', 1, status='weak')),
        _move('召唤', 'Summon', _effect('summon', 1, enemy_id='spider'), _effect('gain_frenzy', 1)),
    ), script='spider_cave', traits=('sturdy', 'frenzied'), initial={'shield': 40, 'sturdy': 99},
       lunatic_initial={'shield': 50}, lunatic_health=119),
    'stickbug': _enemy('竹节虫', 'Stickbug', 164, (
        _move('发射', 'Launch', _effect('summon', 3, enemy_id='stick')),
        _move('生长', 'Growth', _effect('self_heal', 12, lunatic_amount=15), _effect('gain_power', 3, lunatic_amount=4)),
        _move('砸击', 'Smash', _effect('damage', 20, lunatic_amount=22)),
    ), script='stickbug', lunatic_health=180),
    'stick': _enemy('树枝', 'Stick', 14, (
        _move('防守', 'Defense', _effect('gain_shield', 8, lunatic_amount=10)),
    ), traits=('obstacle',), initial={'shield': 12, 'obstacle': 1},
       lunatic_initial={'shield': 14}, lunatic_health=16),
    'termite_mound': _enemy('白蚁丘', 'Termite Mound', 221, (
        _move('固守', 'Hold Fast', _effect('gain_shield', 12, lunatic_amount=15)),
        _move('号令', 'Command', _effect('allies_power', 1)),
    ), script='termite_mound', traits=('psionic_fountain', 'nest_instinct'), lunatic_health=238),
    'evil_centipede': _enemy('邪恶蜈蚣', 'Evil Centipede', 113, (
        _move('毒噬', 'Poison Bite', _effect('damage', 12), _effect('player_status', 1, status='toxic_poison', lunatic_amount=2)),
        _move('毒气', 'Poison Gas', _effect('player_status', 3, status='poison', lunatic_amount=4), _effect('player_status', 1, status='stagnation')),
        _move('毒爆', 'Poison Burst', _effect('damage_from_player_status', 6, status='poison', lunatic_amount=7), _effect('gain_power', 3, lunatic_amount=4)),
    ), script='evil_centipede', traits=('segments',), initial={'segments': 2},
       lunatic_initial={'segments': 3}, lunatic_health=97),
    'magic_firefly': _enemy('魔法萤火虫', 'Magic Firefly', 308, (
        _move('吸引', 'Attract', _effect('damage', 15, lunatic_amount=18), _effect('gain_status', 2, status='magic_reflection'), _effect('gain_status', 1, status='bulb'), _effect('disable_magic_shield', 1)),
        _move('魔法球', 'Magic Orb', _effect('gain_magic', 5, lunatic_amount=6), _effect('gain_power', 2, lunatic_amount=3)),
        _move('魔法尖刺', 'Magic Spike', _effect('consume_magic_damage', 12, multiplier=2, lunatic_amount=16)),
    ), script='magic_firefly', traits=('magic_shield', 'magic_blessing', 'magic_reflection', 'bulb'),
       initial={'magic_shield': 5, 'magic': 10}, lunatic_initial={'magic_shield': 6}, lunatic_health=331),
})

# Stage 3: Factory.
STORY_ENEMIES.update({
    'mechanical_flower': _enemy('机械花', 'Mechanical Flower', 456, (
        _move('机械轨道', 'Mechanical Track'),
    ), script='mechanical_flower', traits=(
        'machine_learning', 'mechanical_track', 'recycling',
        'electronic_shield',
    ), lunatic_health=480),
    'mechanical_spider': _enemy('机械蜘蛛', 'Mechanical Spider', 64, (
        _move('放电', 'Discharge', _effect('add_draw_card', 2, card_id='static_electricity')),
        _move('猛扑', 'Pounce', _effect('damage', 12, lunatic_amount=15), _effect('gain_power', 3)),
    ), traits=('electric_web',), initial={'electric_web': 2}, lunatic_health=70),
    'mechanical_crab': _enemy('机械螃蟹', 'Mechanical Crab', 189, (
        _move('连击', 'Combo', _effect('damage', 7, hits=3, lunatic_amount=8)),
        _move('冲击', 'Impact', _effect('damage', 16, lunatic_amount=18), _effect('gain_shield', 30, lunatic_amount=40)),
        _move('充能', 'Charge', _effect('gain_power', 4, lunatic_amount=5)),
        _move('超能光束', 'Super Beam', _effect('damage', 28, lunatic_amount=32), _effect('gain_status', 1, status='vulnerable'), _effect('gain_status', 1, status='stun')),
    ), script='mechanical_crab', traits=('super_beam',), initial={'super_beam': 4}, lunatic_health=210),
    'uranium_barrel': _enemy('铀桶', 'Uranium Barrel', 120, (
        _move('辐射', 'Radiation', _effect('player_status', 3, status='toxic_poison', lunatic_amount=4)),
        _move('幻光', 'Phantom Light', _effect('player_status', 1, status='toxic_poison', lunatic_amount=2), _effect('gain_status', 1, status='bulb')),
    ), script='uranium_barrel', traits=('toxic_reflection', 'bulb'), initial={'toxic_reflection': 2},
       lunatic_initial={'toxic_reflection': 3}, lunatic_health=133),
    'reconstructor_enemy': _enemy('重构机', 'Reconstructor', 504, (
        _move('锯片', 'Saw', _effect('damage', 17, lunatic_amount=19), _effect('player_status', 3, status='bleed', lunatic_amount=4)),
        _move('激光器', 'Laser', _effect('damage', 6, hits=3, lunatic_amount=7), _effect('player_status', 2, status='fire', lunatic_amount=3)),
        _move('碎片', 'Fragment', _effect('gain_power', 1, lunatic_amount=2), _effect('gain_status', 1, status='fragment', lunatic_amount=2), _effect('gain_shield', 50, lunatic_amount=60)),
        _move('自分解', 'Self-Disassembly', _effect('self_damage', 50), _effect('gain_status', 4, status='fragment', lunatic_amount=5), _effect('gain_power', 4, lunatic_amount=5)),
        _move('雷神之锤', 'Mjolnir', _effect('damage', 20, hits=2, lunatic_amount=22), _effect('consume_status', 5, status='fragment')),
    ), script='reconstructor_enemy', traits=('reconstruction', 'integration', 'scrap'),
       initial={'reconstructor_turns_processed': 0, 'missed_factory_waste_last_turn': False},
       lunatic_health=532),
    'mechanical_wasp': _enemy('机械胡蜂', 'Mechanical Wasp', 189, (
        _move('组装', 'Assemble', _effect('summon', 1, enemy_id='mechanical_missile')),
        _move('改装打击', 'Modified Strike', _effect('damage', 11, lunatic_amount=13), _effect('named_allies_power', 3, enemy_id='mechanical_missile', lunatic_amount=4)),
        _move('维修', 'Repair', _effect('heal_named_ally_percent', 50, enemy_id='mechanical_missile'), _effect('named_allies_power', 1, enemy_id='mechanical_missile', lunatic_amount=2)),
        _move('狂暴', 'Frenzy', _effect('damage', 4, hits=5, lunatic_amount=5), _effect('gain_power', 1)),
    ), script='mechanical_wasp', traits=('disc',), initial={'disc': 2}, lunatic_health=203),
    'mechanical_missile': _enemy('机械导弹', 'Mechanical Missile', 102, (
        _move('发射', 'Launch', _effect('damage', 10, lunatic_amount=11)),
        _move('自毁', 'Self-Destruct', _effect('damage', 35, lunatic_amount=41), _effect('self_kill')),
    ), script='mechanical_missile', lunatic_health=114),
    'smoke': _enemy('烟雾', 'Smoke', 44, (
        _move('瘴气', 'Miasma', _effect('player_status', 5, status='poison', lunatic_amount=7)),
        _move('闷燃', 'Smolder', _effect('gain_status', 2, status='toxic_pressure')),
    ), script='smoke', traits=('toxic_pressure',), initial={'toxic_pressure': 2},
       lunatic_initial={'toxic_pressure': 3}, lunatic_health=47),
    'brick_pile': _enemy('砖堆', 'Brick Pile', 69, (
        _move('阻碍', 'Obstruct', _effect('allies_shield', 16, lunatic_amount=20)),
    ), script='brick_pile', traits=('obstacle',), initial={'obstacle': 2},
       lunatic_health=75),
    'mechanical_rat': _enemy('机械鼠', 'Mechanical Rat', 232, (
        _move('伏击', 'Ambush', _effect('damage', 19, lunatic_amount=22), _effect('player_status', 1, status='weak')),
        _move('强袭', 'Assault', _effect('damage', 26, lunatic_amount=30), _effect('gain_power', 2)),
    ), script='mechanical_rat', traits=('hiding',), initial={'hidden': 1}, lunatic_health=254),
    'broken_machine': _enemy('损坏机器', 'Broken Machine', 1, (),
        script='broken_machine', traits=('cover',)),
    'chimney': _enemy('烟囱', 'Chimney', 456, (
        _move('喷射', 'Jet', _effect('summon', 1, enemy_id='smoke'), _effect('player_status', 5, status='poison')),
        _move('燃烧', 'Combustion', _effect('damage_from_player_status', 16, status='toxic_poison', lunatic_amount=21), _effect('halve_player_status', 0, status='toxic_poison')),
    ), script='chimney', traits=('injured_summon',),
       initial={'injured_summon': 100}, lunatic_health=489),
    'generator': _enemy('发电机', 'Generator', 321, (
        _move('反射护盾', 'Reflective Shield', _effect('gain_status', 4, status='reflection', lunatic_amount=5), _effect('gain_shield', 40, lunatic_amount=50)),
        _move('漏电', 'Leakage', _effect('damage', 22, lunatic_amount=26), _effect('all_cards_charge', 2)),
        _move('发电', 'Generate', _effect('gain_status', 3, status='reflection', lunatic_amount=4), _effect('gain_shield', 40, lunatic_amount=50)),
    ), script='generator', lunatic_health=345),
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
for _enemy_id in (
    'leafbug', 'dark_ladybug',
    'jungle_firefly', 'jungle_wasp', 'snail', 'bush', 'termite_mound',
    'magic_firefly', 'mechanical_spider',
):
    STORY_ENEMIES[_enemy_id]['move_order'] = tuple(range(len(STORY_ENEMIES[_enemy_id]['moves'])))
STORY_ENEMIES['termite_soldier']['move_order'] = (0, 1, 2)
STORY_ENEMIES['termite_overmind']['move_order'] = (0, 1)
STORY_ENEMIES['jungle_mushroom']['move_order'] = (0, 1)
STORY_ENEMIES['mechanical_crab']['move_order'] = (0, 1, 2, 3)
STORY_ENEMIES['smoke']['move_order'] = (0, 1)
STORY_ENEMIES['brick_pile']['move_order'] = (0,)
STORY_ENEMIES['chimney']['move_order'] = (0, 0, 1)
STORY_ENEMIES['generator']['move_order'] = (0, 1, 2)

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
    'termite_soldier': '/static/assets/story-enemies/soldier-termite.svg',
    'termite_worker': '/static/assets/story-enemies/worker-termite.svg',
    'termite_overmind': '/static/assets/story-enemies/termite-overmind.svg',
    'leafbug': '/static/assets/story-enemies/leafbug.svg',
    'dark_ladybug': '/static/assets/story-enemies/dark-ladybug.svg',
    'jungle_firefly': '/static/assets/story-enemies/jungle-firefly.svg',
    'jungle_wasp': '/static/assets/story-enemies/jungle-wasp.svg',
    'jungle_fly': '/static/assets/story-enemies/jungle-fly.svg',
    'jungle_mushroom': '/static/assets/story-enemies/jungle-mushroom.svg',
    'pumpkin': '/static/assets/story-enemies/pumpkin.svg',
    'snail': '/static/assets/story-enemies/snail.svg',
    'bush': '/static/assets/story-enemies/jungle-bush.svg',
    'spider_cave': '/static/assets/story-enemies/spider-cave.svg',
    'stickbug': '/static/assets/story-enemies/stickbug.svg',
    'stick': '/static/assets/story-enemies/stick.svg',
    'termite_mound': '/static/assets/story-enemies/termite-mound.svg',
    'evil_centipede': '/static/assets/story-enemies/evil-centipede-head.svg',
    'magic_firefly': '/static/assets/story-enemies/magic-firefly.svg',
    'mechanical_spider': '/static/assets/story-enemies/mechanical-spider.svg',
    'mechanical_crab': '/static/assets/story-enemies/mechanical-crab.svg',
    'uranium_barrel': '/static/assets/story-enemies/uranium-barrel.svg',
    'mechanical_flower': '/static/assets/story-enemies/mechanical-flower.svg',
    'reconstructor_enemy': '/static/assets/story-enemies/reconstructor.svg',
    'mechanical_wasp': '/static/assets/story-enemies/mechanical-wasp.svg',
    'mechanical_missile': '/static/assets/story-enemies/mechanical-missile.svg',
    'smoke': '/static/assets/story-enemies/smoke.svg',
    'brick_pile': '/static/assets/story-enemies/brick-pile.svg',
    'mechanical_rat': '/static/assets/story-enemies/mechanical-rat.svg',
    'broken_machine': '/static/assets/story-enemies/broken-machine.svg',
    'chimney': '/static/assets/story-enemies/chimney.svg',
    'generator': '/static/assets/story-enemies/generator.svg',
}

for _enemy_id, _image_url in STORY_ENEMY_IMAGE_URLS.items():
    STORY_ENEMIES[_enemy_id]['image_url'] = _image_url

STORY_ENEMIES['evil_centipede']['segment_image_url'] = (
    '/static/assets/story-enemies/evil-centipede-body.svg'
)


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
    'jungle': {
        'simple': (
            ({'def_id': 'termite_soldier', 'move_index': 0}, {'def_id': 'termite_soldier', 'move_index': 2}),
            ('pumpkin',),
            ('jungle_firefly',),
        ),
        'hard': (
            ('jungle_fly', 'jungle_firefly'),
            ('dark_ladybug', 'jungle_wasp'),
            ({'def_id': 'jungle_mushroom', 'move_index': 0}, {'def_id': 'jungle_fly', 'move_index': 0}, {'def_id': 'jungle_fly', 'move_index': 1}),
            ('snail',),
            ('jungle_firefly', 'leafbug'),
            ('pumpkin', 'leafbug'),
            ('jungle_firefly', 'jungle_wasp'),
            ('dark_ladybug', 'jungle_fly'),
            ('termite_overmind', 'termite_worker', 'termite_worker'),
        ),
        'elite': (
            ('stickbug',),
            ('bush',),
            ('spider_cave',),
        ),
        'boss': (
            ('termite_overmind', 'termite_soldier', 'termite_worker', 'termite_mound'),
            ('evil_centipede',),
            ('magic_firefly',),
        ),
    },
    'factory': {
        'simple': (
            ('mechanical_crab',),
            ('uranium_barrel', 'mechanical_spider'),
            ('uranium_barrel', 'smoke'),
            ('brick_pile', 'uranium_barrel'),
            ('brick_pile', 'mechanical_spider', 'smoke'),
        ),
        'hard': (
            ('mechanical_crab', 'uranium_barrel'),
            ('mechanical_crab', 'mechanical_spider'),
            ('uranium_barrel', 'smoke', 'smoke'),
            ('brick_pile', 'brick_pile', 'mechanical_crab'),
            ('smoke', 'smoke', 'mechanical_crab'),
        ),
        'elite': (
            ('mechanical_wasp',),
            ('broken_machine', 'broken_machine', 'broken_machine', 'mechanical_rat'),
            ('generator',),
        ),
        'boss': (
            ('reconstructor_enemy',),
            ('mechanical_flower',),
            ('chimney', 'smoke'),
        ),
    },
}


def initial_story_player(character_id='common_flower'):
    character_id = str(character_id or 'common_flower')
    character = STORY_CHARACTERS.get(character_id)
    if not isinstance(character, dict):
        raise ValueError('UNKNOWN_STORY_CHARACTER')
    if character.get('implementation_status') != 'playable':
        raise ValueError('STORY_CHARACTER_NOT_READY')
    deck_ids = []
    for entry in character.get('starter_deck') or ():
        card_id = str(
            entry.get('card_id') or entry.get('character_card_id') or ''
        )
        count = max(0, int(entry.get('count') or 0))
        if not card_id or card_id not in STORY_CARDS or count <= 0:
            raise ValueError('INVALID_STORY_CHARACTER_LOADOUT')
        deck_ids.extend([card_id] * count)
    starter_relics = list(character.get('starter_relics') or ())
    if not deck_ids or any(relic_id not in STORY_RELICS for relic_id in starter_relics):
        raise ValueError('INVALID_STORY_CHARACTER_LOADOUT')
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
        'relics': starter_relics,
        'blessing': None,
        'blessings': [],
        'opening_draw_bonus': 0,
        'next_card_serial': len(deck) + 1,
        'character_id': character_id,
        'enchantment_books': [],
        'next_enchantment_book_serial': 1,
    }


def story_combat_starting_magic(player):
    """Reset battle-only magic and consume an explicit one-combat bonus."""

    baseline = max(0, int(STORY_RULES.get('starting_magic') or 0))
    if not isinstance(player, dict):
        return baseline
    # ``player.magic`` remains in the save schema for compatibility and admin
    # inspection, but ordinary combat magic must never become a run resource.
    player['magic'] = baseline
    bonus = max(0, int(player.pop('next_combat_magic_bonus', 0) or 0))
    return baseline + bonus


def _find_source(card_defs, source_id=None, source_names=()):
    if not card_defs:
        return None

    def normalize(value):
        return ''.join(ch for ch in str(value).lower() if ch.isalnum())

    if source_id:
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

    if isinstance(source_names, dict):
        source_names = source_names.values()
    elif isinstance(source_names, str):
        source_names = (source_names,)
    wanted_names = {normalize(name) for name in source_names if normalize(name)}
    if not wanted_names:
        return None

    matches = []
    matched_source_ids = set()
    for source in card_defs.values():
        candidate_names = {
            normalize(getattr(source, 'name_cn', '')),
            normalize(getattr(source, 'name_en', '')),
        }
        localized_names = getattr(source, 'name_i18n', None)
        if isinstance(localized_names, dict):
            candidate_names.update(
                normalize(name) for name in localized_names.values()
            )
        candidate_names.discard('')
        if not wanted_names.intersection(candidate_names):
            continue
        source_identity = str(getattr(source, 'id', '') or id(source))
        if source_identity in matched_source_ids:
            continue
        matched_source_ids.add(source_identity)
        matches.append(source)

    # A duplicated localized name must not silently bind the wrong card art.
    if len(matches) == 1:
        return matches[0]
    return None


def story_content_payload(card_defs=None):
    cards = deepcopy(STORY_CARDS)
    if card_defs:
        for definition in cards.values():
            source = _find_source(
                card_defs,
                definition.get('source_card_id'),
                definition.get('name') or {},
            )
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
        'characters': deepcopy(STORY_CHARACTERS),
        'character_cards': deepcopy(STORY_CHARACTER_CARD_DESIGNS),
        'character_relics': deepcopy(STORY_CHARACTER_RELIC_DESIGNS),
        'biomes': deepcopy(STORY_BIOMES),
        'difficulties': deepcopy(STORY_DIFFICULTIES),
        'rarities': deepcopy(STORY_RARITIES),
        'card_types': deepcopy(STORY_CARD_TYPES),
        'tags': deepcopy(STORY_TAGS),
        'statuses': deepcopy(STORY_STATUSES),
        'traits': deepcopy(STORY_TRAITS),
        'trait_value_keys': deepcopy(STORY_TRAIT_VALUE_KEYS),
        'trait_zero_visible': sorted(STORY_TRAIT_ZERO_VISIBLE),
        'blessings': deepcopy(STORY_BLESSINGS),
        'events': deepcopy(STORY_EVENTS),
        'cards': cards,
        'relics': deepcopy(STORY_RELICS),
        'boss_relic_ids': list(STORY_BOSS_RELIC_IDS),
        'easy_relic_ids': list(STORY_EASY_RELIC_IDS),
        'enemies': deepcopy(STORY_ENEMIES),
        'enchantment_books': deepcopy(STORY_ENCHANTMENT_BOOKS),
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
        'heal', 'immediate_extra_turn', 'inspect_draw_choose', 'lose_health',
        'magic', 'make_card_free', 'next_skill_repeats', 'next_turn_draw',
        'permanent_damage_growth', 'permanent_swift', 'power', 'self_swift',
        'random_active_discard', 'random_damage_per_discards', 'random_exile',
        'recover_exiled', 'salt', 'shield', 'shield_from_target_status',
        'shield_selected', 'shield_with_power', 'shuffle_hand_redraw',
        'status', 'status_self', 'swap_piles_draw', 'temporary_cost_down',
        'temporary_effect',
        'conditional_magic', 'consume_magic_draw', 'create_draw_top_copies',
        'magic_extra_hits', 'magic_spent_damage',
        'discard_nonmagic_draw_magic', 'draw_then_topdeck', 'electric_damage',
        'generate_magic_cards', 'magic_enemy_count', 'magic_overload',
        'multiply_shield', 'multiply_static', 'next_combat_magic', 'overload',
        'retrieve_from_piles', 'self_magic_swift', 'shield_damage_halved',
        'shield_remaining_magic', 'static', 'temporary_magic_heavy',
        'temporary_swap_costs', 'turn_damage_multiplier', 'untargetable',
        'magic_spend_shield_turn',
    }
    card_effect_types.update(STORY_PLAYER_ATTACK_EFFECT_TYPES)
    card_scripts = {
        'azalea', 'azalea_plus', 'light_sprout', 'return_draw_top', 'slimed',
        'startled', 'static_electricity', 'unrelenting', 'corruption',
        'factory_waste', 'requires_no_last_turn_damage',
    }
    equipment_scripts = {
        'cannot_draw', 'disc', 'magic_acid', 'magic_pearl', 'pearl',
        'draw_power', 'retain_elixir', 'sewage', 'soul_splitter', 'sponge',
        'start_power', 'start_random_bloom', 'start_shield', 'turn_elixir',
        'victory_gold', 'vulnerable_shield',
        'delayed_magic', 'electric_on_m_card', 'elixir_spend_magic',
        'end_electric_all', 'magic_gain_shield', 'magic_recovery',
        'magic_regeneration', 'magic_shield', 'magic_spend_shield',
        'static_boost', 'static_damage', 'static_draw', 'static_magic',
        'static_shield',
        'static_on_attacked', 'turn_draw',
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
        'turn_draw', 'turn_elixir', 'turn_heal', 'turn_magic',
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
        'summon_wreckage', 'allies_status', 'consume_magic_damage',
        'consume_status', 'consume_status_damage', 'damage_from_player_status',
        'damage_from_shield', 'disable_magic_shield', 'gain_magic',
        'heal_named_ally_percent', 'named_allies_power',
        'all_cards_charge', 'halve_player_status',
    }
    enemy_scripts = {
        'ant_queen', 'bandage_beetle', 'centipede', 'desert_centipede',
        'fossil', 'garden_rock', 'hive', 'ocean_bubble', 'ocean_shell',
        'opening_reflection', 'persistent_shield', 'random_intent',
        'sandstone', 'shiny_ladybug', 'shipwreck', 'starfish', 'swell',
        'waterspout', 'worker_ant', 'worm', 'wreckage',
        'termite_worker', 'jungle_fly', 'jungle_mushroom', 'pumpkin',
        'spider_cave', 'stickbug', 'termite_mound', 'evil_centipede',
        'magic_firefly', 'mechanical_crab', 'uranium_barrel',
        'reconstructor_enemy', 'mechanical_wasp', 'mechanical_missile',
        'mechanical_flower', 'smoke', 'brick_pile', 'mechanical_rat',
        'broken_machine', 'chimney', 'generator',
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

    book_scripts = {
        'damage_bonus', 'shield_bonus_once', 'remove_exile', 'swift',
        'temporary_swift', 'wide', 'armor_break', 'electric_damage',
        'retain', 'exile_void', 'dense', 'draw_to_full_once', 'lethal_guard',
        'disc_once', 'fire_on_hit_once', 'immunity_once', 'repeat_on_kill',
        'copy_book', 'weak_once', 'double_reward_on_kill', 'rebound',
        'health_cost', 'repeat_once', 'power_once', 'impact_once',
        'retrieve_once', 'reflection_once', 'vulnerable_once', 'escape',
    }
    for book_id, definition in STORY_ENCHANTMENT_BOOKS.items():
        if definition.get('rarity') not in ('common', 'rare', 'ultra'):
            errors.append(f'{book_id}: invalid enchantment book rarity')
        if definition.get('script') not in book_scripts:
            errors.append(f'{book_id}: invalid enchantment book script')

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
    event_effect_types = {'gold', 'heal', 'health_loss'}
    for event_id, definition in STORY_EVENTS.items():
        if not isinstance(definition, dict):
            errors.append(f'events[{event_id}]: invalid definition')
            continue
        if not definition.get('title') or not definition.get('description'):
            errors.append(f'events[{event_id}]: missing presentation')
        if not set(definition.get('biomes') or ()).issubset(STORY_BIOMES):
            errors.append(f'events[{event_id}]: unknown biome')
        if not set(definition.get('modes') or ()).issubset({'solo', 'coop'}):
            errors.append(f'events[{event_id}]: invalid mode')
        option_ids = []
        for index, option in enumerate(definition.get('options') or ()):
            owner = f'events[{event_id}].options[{index}]'
            if not isinstance(option, dict) or not option.get('id'):
                errors.append(f'{owner}: invalid option')
                continue
            option_ids.append(str(option['id']))
            for effect_index, effect in enumerate(option.get('effects') or ()):
                effect_owner = f'{owner}.effects[{effect_index}]'
                if not isinstance(effect, dict):
                    errors.append(f'{effect_owner}: invalid effect')
                    continue
                if effect.get('type') not in event_effect_types:
                    errors.append(f'{effect_owner}: unknown effect')
                if (
                    not isinstance(effect.get('amount'), int)
                    or isinstance(effect.get('amount'), bool)
                    or int(effect.get('amount') or 0) < 0
                ):
                    errors.append(f'{effect_owner}: invalid amount')
        if not option_ids or len(option_ids) != len(set(option_ids)):
            errors.append(f'events[{event_id}]: invalid option ids')
    if errors:
        raise ValueError('Invalid story content: ' + '; '.join(errors))


validate_story_content()
