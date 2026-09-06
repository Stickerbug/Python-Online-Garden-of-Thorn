"""Solo event data for Garden of Thorn 卡牌数据12, workbook sheet 爬塔事件设计 rows 13-31.

Each event carries option ids and a compact action hint consumed by story_engine.
The workbook remains the authoritative Chinese design text; English labels are
working localizations.
"""


def _opts(*items):
    return tuple({
        'id': str(item[0]),
        'label': {'zh': str(item[1]), 'en': str(item[2] if len(item) > 2 and item[2] else item[1])},
        'action_hint': str(item[3]) if len(item) > 3 else '',
        'needs_confirmation': bool(item[4]) if len(item) > 4 else True,
        'selection': str(item[5]) if len(item) > 5 and item[5] else '',
    } for item in items)


STORY_EVENTS_12 = {
    'crusher_machine': {
        'stage': (3, 3),
        'title': {'zh': '裂解机', 'en': 'Crusher Machine'},
        'options': _opts(
            ('copy_card', '尝试分解你的卡牌-选择一张牌并复制4次，获得2张玫瑰2张基本', 'Copy a chosen card 4 times; gain 2 Rose and 2 Basic', 'copy_card_many', True, 'copy'),
            ('decompose_self', '尝试分解自己-失去30%最大生命值，删除3张牌', 'Lose 30% max H and remove 3 cards', 'lose_max_health_percent_and_remove'),
            ('leave', '还是不要乱动为好-什么都不会发生', 'Leave', 'leave'),
        ),
    },
    'library': {
        'stage': None,
        'title': {'zh': '图书馆', 'en': 'Library'},
        'options': _opts(
            ('take_books', '把书带走：获得2本随机附魔书', 'Gain 2 random enchantment books', 'gain_enchantment_books', False),
            ('study', '研读书本-选择一张牌升级', 'Upgrade a chosen card', 'upgrade_random_cards', True, 'upgrade'),
            ('use_magic', '利用魔咒的力量-失去一本附魔书，删除一张牌', 'Lose a book and remove a card', 'lose_book_remove_card', True),
            ('leave', '奇怪的商人，还是不要搭理为好-离开此处', 'Leave', 'leave'),
        ),
    },
    'enchanter': {
        'stage': (2, 3),
        'requires_books': 2,
        'title': {'zh': '附魔师', 'en': 'Enchanter'},
        'options': _opts(
            ('enchant', '使用你的附魔书来附魔装备-失去所有附魔书，每失去一本，升级一张牌', 'Spend books; upgrade a card per book', 'books_to_upgrades'),
            ('take_book', '那一本书走-获得一本随机稀有附魔书', 'Gain a random rare enchantment book', 'gain_enchantment_books', False),
        ),
    },
    'midas_coin': {
        'stage': None,
        'title': {'zh': '迈达斯金币', 'en': 'Midas Coin'},
        'options': _opts(
            ('touch', '伸手触碰-失去1点最大生命值，获得60金币（可以反复选择）', 'Lose 1 max H and gain 60 G', 'midas_touch'),
            ('smash', '砸碎金币-受到6D', 'Take 6 D', 'health_loss_6'),
        ),
    },
    'world_tree_branch': {
        'stage': None,
        'title': {'zh': '世界树之枝', 'en': 'World Tree Branch'},
        'options': _opts(
            ('bless', '接受祝福-回复29H', 'Recover 29 H', 'heal_29'),
            ('break_branch', '折下枝干-获得一张腐化和273G', 'Gain Corruption and 273 G', 'corruption_and_gold'),
        ),
    },
    'endless_marathon': {
        'stage': (1, 1),
        'title': {'zh': '无尽马拉松', 'en': 'Endless Marathon'},
        'options': _opts(
            ('learn', '请教技巧-学习天赋练起来', 'Learn Training talent', 'gain_training'),
            ('eat_chocolate', '吃下巧乐兹-回复所有血量，最大生命值-10', 'Heal fully, lose 10 max H', 'full_heal_max_health_loss'),
        ),
    },
    'herald': {
        'stage': (2, 3),
        'title': {'zh': '神使', 'en': 'Herald'},
        'options': _opts(
            ('accept', '完全接受-变化你的所有卡牌（只会变成同种类型）', 'Transform all cards by type', 'transform_all_by_type'),
            ('resist', '尝试对抗-变化2张牌，获得一张疲劳', 'Transform 2 cards and gain Fatigued', 'transform_two_and_fatigued'),
        ),
    },
    'strange_anvil': {
        'stage': None,
        'title': {'zh': '奇怪铁砧', 'en': 'Strange Anvil'},
        'options': _opts(
            ('upgrade', '利用它强化花瓣-选择一张牌升级', 'Upgrade a chosen card', 'anvil_upgrade', True, 'upgrade'),
            ('leave', '离开', 'Leave', 'leave'),
        ),
    },
    'bbq': {
        'stage': (1, 1),
        'title': {'zh': '篝火烧烤', 'en': 'Campfire BBQ'},
        'options': _opts(
            ('eat_bug', '吃掉烤虫子-回复20-30血量', 'Recover 20-30 H', 'heal_20_30'),
            ('steal', '偷钱-获得40-60G', 'Gain 40-60 G', 'gold_40_60'),
        ),
    },
    'titan': {
        'stage': (3, 3),
        'title': {'zh': '泰坦', 'en': 'Titan'},
        'options': _opts(
            ('forge', '锻造-选取2张同类型卡聚合', 'Forge two cards together', 'forge_two_cards'),
            ('hammer', '捶打-随机升级3张牌', 'Upgrade 3 random cards', 'upgrade_random_cards'),
        ),
    },
    'deep_branch': {
        'stage': (2, 2),
        'title': {'zh': '枝干深处', 'en': 'Deep in the Branches'},
        'options': _opts(
            ('near', '翻找近处-获得一张随机的Ultra卡', 'Gain a random Ultra card', 'random_ultra_card'),
            ('far', '翻找远处-失去16H，获得一个随机天赋', 'Lose 16 H and gain a random talent', 'lose_16_gain_relic'),
        ),
    },
    'withered_trunk': {
        'stage': None,
        'title': {'zh': '凋萎的世界树残块', 'en': 'Withered Trunk'},
        'options': _opts(
            ('eat', '吃下-回复15H，随机获得一张卡牌', 'Heal 15 H and gain a random card', 'heal_and_random_card'),
            ('use_corruption', '利用腐败之力-失去8H，选择一张牌删除', 'Lose 8 H and remove a chosen card', 'health_loss_and_remove', True, 'remove'),
            ('leave', '离开', 'Leave', 'leave'),
        ),
    },
    'card_machine': {
        'stage': None,
        'requires_gold': 75,
        'title': {'zh': '卡牌制作机', 'en': 'Card Machine'},
        'options': _opts(
            ('machine_type_root', '制作装备牌（基础25G）', 'Make an equipment card (base 25 G)', 'machine_choose_type'),
            ('machine_type_thorn', '制作攻击牌', 'Make an attack card', 'machine_choose_type'),
            ('machine_type_bloom', '制作技能牌', 'Make a skill card', 'machine_choose_type'),
            ('leave', '离开', 'Leave', 'leave'),
        ),
    },
    'secret_passage': {
        'stage': None,
        'title': {'zh': '密道', 'en': 'Secret Passage'},
        'options': _opts(
            ('enter', '穿过-下次战斗奖励翻倍，但下次战斗开始获得虚弱99', 'Double next reward; gain Weak 99 next battle', 'secret_passage_reward'),
        ),
    },
    'card_giftpack': {
        'stage': None,
        'requires_gold': 50,
        'title': {'zh': '卡牌大礼包', 'en': 'Card Gift Pack'},
        'options': _opts(
            ('buy', '买下-花费50G，获得五张牌', 'Pay 50 G for five cards', 'buy_giftpack'),
            ('leave', '离开', 'Leave', 'leave'),
        ),
    },
    'talent_lottery': {
        'stage': None,
        'requires_gold': 150,
        'title': {'zh': '天赋抽奖', 'en': 'Talent Lottery'},
        'options': _opts(
            ('talent_draw', '抽-花费150G查看一个随机天赋', 'Pay 150 G to view a random talent', 'talent_draw'),
            ('leave', '离开', 'Leave', 'leave'),
        ),
    },
    'scale_judgement': {
        'stage': None,
        'requires_upgraded': 5,
        'title': {'zh': '天平的审判', 'en': 'Scale Judgement'},
        'options': _opts(
            ('scale_you', '天平倾向你-降级所有卡牌，翻倍最大生命值，获得2张疲劳', 'Downgrade all cards; double max H; gain 2 Fatigued', 'scale_toward_player'),
            ('scale_cards', '天平倾向你的卡牌-升级所有牌，减半最大生命值', 'Upgrade all cards; halve max H', 'scale_toward_cards'),
        ),
    },
    'bank': {
        'stage': None,
        'requires_gold': 50,
        'title': {'zh': '银行', 'en': 'Bank'},
        'options': _opts(
            ('deposit', '存钱-存入一半金币，存款增加这个值的两倍（跨局继承）', 'Deposit half gold, deposit grows 2x', 'bank_deposit'),
            ('withdraw', '取出-获得所有存款，将存款清空', 'Withdraw all deposit', 'bank_withdraw'),
            ('leave', '离开', 'Leave', 'leave'),
        ),
    },
}


def event_12_action_hint(event_id, option_id):
    definition = STORY_EVENTS_12.get(str(event_id))
    if not definition:
        return ''
    legacy = {
        'card_machine': {
            'make_equipment': 'make_equipment',
            'make_attack': 'make_attack',
            'make_skill': 'make_skill',
            'make_rare': 'make_rare',
            'make_ultra': 'make_ultra',
        },
        'talent_lottery': {
            'buy_random_relic': 'buy_random_relic',
        },
        'bbq': {
            'pay_leave': 'pay_30_leave',
            'refuse': 'refuse_pay_weak',
        },
    }
    if str(event_id) in legacy and str(option_id) in legacy[str(event_id)]:
        return legacy[str(event_id)][str(option_id)]
    for option in definition.get('options') or ():
        if str(option.get('id') or '') == str(option_id):
            return str(option.get('action_hint') or '')
    return ''


def event_12_ids():
    return tuple(STORY_EVENTS_12)
