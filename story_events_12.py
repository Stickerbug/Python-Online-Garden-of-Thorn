"""Solo event data for Garden of Thorn 卡牌数据12, workbook sheet 爬塔事件设计 rows 13-31.

Each event carries option ids and a compact action hint consumed by story_engine.
The workbook remains the authoritative Chinese design text; English labels are
working localizations.
"""


def _opts(*items):
    parsed = []
    for item in items:
        option = {
            'id': str(item[0]),
            'label': {'zh': str(item[1]), 'en': str(item[2] if len(item) > 2 and item[2] else item[1])},
            'action_hint': str(item[3]) if len(item) > 3 else '',
            'needs_confirmation': bool(item[4]) if len(item) > 4 else True,
            'selection': str(item[5]) if len(item) > 5 and item[5] else '',
        }
        if len(item) > 6 and isinstance(item[6], dict) and (item[6].get('zh') or item[6].get('en')):
            option['description'] = {
                'zh': str(item[6].get('zh') or ''),
                'en': str(item[6].get('en') or item[6].get('zh') or ''),
            }
        parsed.append(option)
    return tuple(parsed)


STORY_EVENTS_12 = {
    'crusher_machine': {
        'stage': (3, 3),
        'title': {'zh': '裂解机', 'en': 'Crusher Machine'},
        'body': {
            'zh': '你发现了一台奇怪的裂解机，齿轮间隐约传出分解与重组的声音。',
            'en': 'You find a strange crusher machine, humming with the sound of dismantling and reassembly.',
        },
        'speaker': {'zh': '裂解机', 'en': 'Crusher Machine'},
        'options': _opts(
            ('copy_card', '分解一张卡牌', 'Decompose a Card', 'copy_card_many', True, 'copy', {
                'zh': '选择1张牌复制4次，并获得2张玫瑰与2张基本',
                'en': 'Choose a card, copy it 4 times, and gain 2 Rose and 2 Basic cards',
            }),
            ('decompose_self', '尝试分解自己', 'Decompose Yourself', 'lose_max_health_percent_and_remove', True, '', {
                'zh': '失去30%最大生命值，删除3张牌',
                'en': 'Lose 30% of maximum H and remove 3 cards',
            }),
            ('leave', '还是不要乱动为好', 'Leave It Alone', 'leave'),
        ),
    },
    'library': {
        'stage': None,
        'title': {'zh': '图书馆', 'en': 'Library'},
        'body': {
            'zh': '你来到了一个图书馆，空气中飘着旧纸与魔法的味道。',
            'en': 'You enter a library where old paper and faint magic linger in the air.',
        },
        'speaker': {'zh': '图书馆', 'en': 'Library'},
        'options': _opts(
            ('take_books', '把书带走', 'Take the Books', 'gain_enchantment_books', False, '', {
                'zh': '获得2本随机附魔书',
                'en': 'Gain 2 random enchantment books',
            }),
            ('study', '研读书本', 'Study the Books', 'upgrade_random_cards', True, 'upgrade', {
                'zh': '选择一张牌升级',
                'en': 'Upgrade a chosen card',
            }),
            ('use_magic', '利用魔咒的力量', 'Use the Magic', 'lose_book_remove_card', True, '', {
                'zh': '失去一本附魔书，删除一张牌',
                'en': 'Lose an enchantment book and remove a card',
            }),
            ('leave', '离开', 'Leave', 'leave'),
        ),
    },
    'enchanter': {
        'stage': (2, 3),
        'requires_books': 2,
        'title': {'zh': '附魔师', 'en': 'Enchanter'},
        'body': {
            'zh': '你见到了一个附魔师，他正仔细端详着手中的附魔书。',
            'en': 'You meet an enchanter carefully studying the enchantment books in hand.',
        },
        'speaker': {'zh': '附魔师', 'en': 'Enchanter'},
        'options': _opts(
            ('enchant', '用附魔书附魔装备', 'Enchant Equipment', 'books_to_upgrades', True, '', {
                'zh': '失去所有附魔书，每失去一本就升级一张牌',
                'en': 'Spend all enchantment books and upgrade one card per book',
            }),
            ('take_book', '带走一本书', 'Take a Book', 'gain_enchantment_books', False, '', {
                'zh': '获得一本随机稀有附魔书',
                'en': 'Gain a random rare enchantment book',
            }),
        ),
    },
    'midas_coin': {
        'stage': None,
        'requires_health_gt': 6,
        'title': {'zh': '迈达斯金币', 'en': 'Midas Coin'},
        'body': {
            'zh': '你遇到一块明显被诅咒的金币，看起来它会同化周围所有的物质。',
            'en': 'You find a clearly cursed gold coin that seems to assimilate everything around it.',
        },
        'speaker': {'zh': '迈达斯金币', 'en': 'Midas Coin'},
        'options': _opts(
            ('touch', '伸手触碰', 'Touch the Coin', 'midas_touch', True, '', {
                'zh': '失去1点最大生命值，获得60金币；可以反复选择，第二次失去5点，第三次及以后每次失去10点',
                'en': 'Lose 1 maximum H and gain 60 G. Repeatable; the second touch costs 5 and later touches cost 10',
            }),
            ('smash', '砸碎金币', 'Smash the Coin', 'health_loss_6', True, '', {
                'zh': '受到6D',
                'en': 'Take 6 D',
            }),
        ),
    },
    'world_tree_branch': {
        'stage': None,
        'title': {'zh': '世界树之枝', 'en': 'World Tree Branch'},
        'body': {
            'zh': '你遇到了一根巨树的枝干，它散发着生命的能量。',
            'en': 'You find a great tree branch radiating the energy of life.',
        },
        'speaker': {'zh': '世界树之枝', 'en': 'World Tree Branch'},
        'options': _opts(
            ('bless', '接受祝福', 'Accept the Blessing', 'heal_29', True, '', {
                'zh': '回复29H',
                'en': 'Recover 29 H',
            }),
            ('break_branch', '折下枝干', 'Break the Branch', 'corruption_and_gold', True, '', {
                'zh': '获得一张[[card:corruption]]和273G',
                'en': 'Gain a [[card:corruption]] and 273 G',
            }),
        ),
    },
    'endless_marathon': {
        'stage': (1, 1),
        'title': {'zh': '无尽马拉松', 'en': 'Endless Marathon'},
        'body': {
            'zh': '你奋力向世界树奔去，突然发现身后追来一个紫色的人。他很快超过你，经过时还大喊：“你跑不过我你信吗”。你被激怒了，拼尽全力追了上去，他对你的能力感到诧异，并决定教你点什么。',
            'en': 'You sprint toward the World Tree until a purple runner overtakes you, shouting, "You cannot outrun me!" Angered, you chase him down; impressed, he decides to teach you something.',
        },
        'speaker': {'zh': '紫色跑者', 'en': 'Purple Runner'},
        'options': _opts(
            ('learn', '请教技巧', 'Ask for Tips', 'gain_training', True, '', {
                'zh': '学习天赋[[talent:training]]',
                'en': 'Learn the [[talent:training]] talent',
            }),
            ('eat_chocolate', '吃下巧乐兹', 'Eat the Chocolate', 'full_heal_max_health_loss', True, '', {
                'zh': '回复所有血量，最大生命值-10',
                'en': 'Heal to full and lose 10 maximum H',
            }),
        ),
    },
    'herald': {
        'stage': (2, 3),
        'title': {'zh': '神使', 'en': 'Herald'},
        'body': {
            'zh': '你遇到了一位神使，正向你揭示神谕。',
            'en': 'You meet a herald who reveals a prophecy to you.',
        },
        'speaker': {'zh': '神使', 'en': 'Herald'},
        'options': _opts(
            ('accept', '完全接受', 'Accept Fully', 'transform_all_by_type', True, '', {
                'zh': '变化你所有的卡牌（只会变成同种类型）',
                'en': 'Transform all of your cards, keeping each card type',
            }),
            ('resist', '尝试对抗', 'Resist', 'transform_two_and_fatigued', True, '', {
                'zh': '变化2张牌，获得一张[[card:fatigued]]',
                'en': 'Transform 2 cards and gain a [[card:fatigued]]',
            }),
        ),
    },
    'strange_anvil': {
        'stage': None,
        'title': {'zh': '奇怪铁砧', 'en': 'Strange Anvil'},
        'body': {
            'zh': '你遇到一个奇怪的铁砧，表面残留着无数被砸过的痕迹。',
            'en': 'You find a strange anvil covered with countless old strike marks.',
        },
        'speaker': {'zh': '奇怪铁砧', 'en': 'Strange Anvil'},
        'options': _opts(
            ('upgrade', '利用它强化花瓣', 'Use the Anvil', 'anvil_upgrade', True, 'upgrade', {
                'zh': '选择一张牌升级；第一次成功率80%，之后每次-20%。失败时铁砧爆炸，删除该牌并受到16D',
                'en': 'Choose a card to upgrade. First attempt has 80% success, dropping 20% each time; failure destroys the card and deals 16 D',
            }),
            ('leave', '离开', 'Leave', 'leave'),
        ),
    },
    'bbq': {
        'stage': (1, 1),
        'title': {'zh': '篝火烧烤', 'en': 'Campfire BBQ'},
        'body': {
            'zh': '你看到一群花花聚在一起吃烧烤，老板招呼你一起过去吃。',
            'en': 'You see a group of flowers enjoying a barbecue and the owner waves you over.',
        },
        'speaker': {'zh': '烧烤摊老板', 'en': 'BBQ Owner'},
        'options': _opts(
            ('eat_bug', '吃掉烤虫子', 'Eat the Roasted Bug', 'heal_20_30', True, '', {
                'zh': '回复20-30H',
                'en': 'Recover 20-30 H',
            }),
            ('steal', '偷钱', 'Steal the Money', 'gold_40_60', True, '', {
                'zh': '获得40-60G',
                'en': 'Gain 40-60 G',
            }),
        ),
    },
    'titan': {
        'stage': (3, 3),
        'title': {'zh': '泰坦', 'en': 'Titan'},
        'body': {
            'zh': '你见到了一个自称泰坦的巨大生物，他好像掌握着什么能力。',
            'en': 'You meet a huge creature calling itself a Titan; it seems to command a strange power.',
        },
        'speaker': {'zh': '泰坦', 'en': 'Titan'},
        'options': _opts(
            ('forge', '锻造', 'Forge', 'forge_two_cards', True, '', {
                'zh': '选取2张同类型的卡聚合为一张独特卡牌',
                'en': 'Forge two same-type cards into one unique card',
            }),
            ('hammer', '捶打', 'Hammer', 'upgrade_random_cards', True, '', {
                'zh': '随机升级3张牌',
                'en': 'Upgrade 3 random cards',
            }),
        ),
    },
    'deep_branch': {
        'stage': (2, 2),
        'title': {'zh': '枝干深处', 'en': 'Deep in the Branches'},
        'body': {
            'zh': '世界树茂密的枝干中似乎藏着什么秘密。',
            'en': 'Something seems hidden deep among the World Tree\'s branches.',
        },
        'speaker': {'zh': '枝干深处', 'en': 'Deep Branches'},
        'options': _opts(
            ('near', '翻找近处', 'Search Nearby', 'random_ultra_card', True, '', {
                'zh': '获得一张随机的Ultra卡',
                'en': 'Gain a random Ultra card',
            }),
            ('far', '翻找远处', 'Search Farther', 'lose_16_gain_relic', True, '', {
                'zh': '失去16H，获得一个随机天赋',
                'en': 'Lose 16 H and gain a random talent',
            }),
        ),
    },
    'withered_trunk': {
        'stage': None,
        'title': {'zh': '凋萎的世界树残块', 'en': 'Withered Trunk'},
        'body': {
            'zh': '行进途中，你发现了凋萎的世界树残块，你觉得自己应该做点什么。',
            'en': 'On the road you find a withered piece of the World Tree and feel you should do something with it.',
        },
        'speaker': {'zh': '凋萎的世界树残块', 'en': 'Withered Trunk'},
        'options': _opts(
            ('eat', '吃下', 'Eat It', 'heal_and_random_card', True, '', {
                'zh': '回复15H，随机获得一张卡牌',
                'en': 'Recover 15 H and gain a random card',
            }),
            ('use_corruption', '利用腐败之力', 'Use the Corruption', 'health_loss_and_remove', True, 'remove', {
                'zh': '失去8H，选择一张牌删除',
                'en': 'Lose 8 H and remove a chosen card',
            }),
            ('leave', '离开', 'Leave', 'leave'),
        ),
    },
    'card_machine': {
        'stage': None,
        'requires_gold': 75,
        'title': {'zh': '卡牌制作机', 'en': 'Card Machine'},
        'body': {
            'zh': '你发现了一个卡牌制作机，屏幕提示：先选择类型，再选择稀有度，最后从3张牌中挑选1张。',
            'en': 'You find a card machine. It prompts you to choose a type, then a rarity, then pick 1 of 3 cards.',
        },
        'speaker': {'zh': '卡牌制作机', 'en': 'Card Machine'},
        'options': _opts(
            ('machine_type_root', '制作装备牌', 'Make an Equipment Card', 'machine_choose_type', True, '', {
                'zh': '基础费用25G，随后选择稀有度',
                'en': 'Base cost 25 G; then choose a rarity',
            }),
            ('machine_type_thorn', '制作攻击牌', 'Make an Attack Card', 'machine_choose_type', True, '', {
                'zh': '随后选择稀有度',
                'en': 'Then choose a rarity',
            }),
            ('machine_type_bloom', '制作技能牌', 'Make a Skill Card', 'machine_choose_type', True, '', {
                'zh': '随后选择稀有度',
                'en': 'Then choose a rarity',
            }),
            ('leave', '离开', 'Leave', 'leave'),
        ),
    },
    'secret_passage': {
        'stage': None,
        'title': {'zh': '密道', 'en': 'Secret Passage'},
        'body': {
            'zh': '你发现了一条密道，似乎通向宝藏，但它会让你无法很好地使用花瓣。',
            'en': 'You find a secret passage toward treasure, but it will hamper your use of petals.',
        },
        'speaker': {'zh': '密道', 'en': 'Secret Passage'},
        'options': _opts(
            ('enter', '穿过密道', 'Enter the Passage', 'secret_passage_reward', True, '', {
                'zh': '下次战斗奖励翻倍，但下次战斗开始时获得99层虚弱',
                'en': 'Double the next battle reward, but start the next battle with 99 Weak',
            }),
            ('rest', '原地休息', 'Rest Here', 'heal_16', True, '', {
                'zh': '回复16H',
                'en': 'Recover 16 H',
            }),
            ('leave', '离开', 'Leave', 'leave'),
        ),
    },
    'card_giftpack': {
        'stage': None,
        'requires_gold': 50,
        'title': {'zh': '卡牌大礼包', 'en': 'Card Gift Pack'},
        'body': {
            'zh': '商人正在降价甩卖卡牌：5张随机卡牌，其中有2张普通、2张稀有和1张究极。',
            'en': 'A merchant is clearing out cards: 5 random cards with 2 Common, 2 Rare, and 1 Ultra.',
        },
        'speaker': {'zh': '甩卖商人', 'en': 'Clearance Merchant'},
        'options': _opts(
            ('buy', '买下大礼包', 'Buy the Gift Pack', 'buy_giftpack', True, '', {
                'zh': '花费50G，获得这五张牌',
                'en': 'Pay 50 G and gain all five cards',
            }),
            ('leave', '离开', 'Leave', 'leave'),
        ),
    },
    'talent_lottery': {
        'stage': None,
        'requires_gold': 150,
        'title': {'zh': '天赋抽奖', 'en': 'Talent Lottery'},
        'body': {
            'zh': '你遇到了一个抽奖机，上面写着150G一次。',
            'en': 'You find a lottery machine that reads 150 G per draw.',
        },
        'speaker': {'zh': '天赋抽奖机', 'en': 'Talent Lottery Machine'},
        'options': _opts(
            ('talent_draw', '抽奖', 'Draw', 'talent_draw', True, '', {
                'zh': '花费150G查看一个随机天赋；不满意可花费50G刷新',
                'en': 'Pay 150 G to view a random talent; refresh it for 50 G if unsatisfied',
            }),
            ('leave', '离开', 'Leave', 'leave'),
        ),
    },
    'scale_judgement': {
        'stage': None,
        'requires_upgraded': 5,
        'title': {'zh': '天平的审判', 'en': 'Scale Judgement'},
        'body': {
            'zh': '你遇见了一座神秘的天平，托盘上仿佛放着你的生命与卡牌。',
            'en': 'You find a mysterious scale whose trays seem to hold your life and your cards.',
        },
        'speaker': {'zh': '神秘天平', 'en': 'Mysterious Scale'},
        'options': _opts(
            ('scale_you', '让天平倾向你', 'Tip the Scale to You', 'scale_toward_player', True, '', {
                'zh': '降级所有卡牌，翻倍最大生命值，获得2张[[card:fatigued]]',
                'en': 'Downgrade all cards, double maximum H, and gain 2 [[card:fatigued]]',
            }),
            ('scale_cards', '让天平倾向卡牌', 'Tip the Scale to Your Cards', 'scale_toward_cards', True, '', {
                'zh': '升级所有牌，减半最大生命值',
                'en': 'Upgrade all cards and halve maximum H',
            }),
        ),
    },
    'bank': {
        'stage': None,
        'requires_gold': 50,
        'title': {'zh': '银行', 'en': 'Bank'},
        'body': {
            'zh': '你遇到一座银行。',
            'en': 'You find a bank.',
        },
        'speaker': {'zh': '银行职员', 'en': 'Bank Clerk'},
        'options': _opts(
            ('deposit', '存钱', 'Deposit', 'bank_deposit', True, '', {
                'zh': '存入一半金币，存款增加该值的两倍（跨局继承）',
                'en': 'Deposit half of your gold; the deposit grows to twice that amount and persists across runs',
            }),
            ('withdraw', '取款', 'Withdraw', 'bank_withdraw', True, '', {
                'zh': '获得所有存款，并将存款清空',
                'en': 'Take all deposited gold and clear the deposit',
            }),
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
