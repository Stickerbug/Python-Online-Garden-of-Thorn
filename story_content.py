"""Small, data-driven content set for the playable story-mode alpha."""

from copy import deepcopy


STORY_RULES = {
    'starting_health': 80,
    'starting_elixir': 3,
    'starting_magic': 0,
    'max_magic': 10,
    'draw_per_turn': 5,
    'hand_limit': 10,
}

STORY_BLESSINGS = {
    'titan': {
        'name': {'zh': '泰坦', 'en': 'Titan'},
        'description': {'zh': '最大生命值+20，并回复20H。', 'en': 'Gain 20 maximum H and recover 20 H.'},
    },
    'oracle': {
        'name': {'zh': '神谕', 'en': 'Oracle'},
        'description': {'zh': '每场战斗开局额外抽1张牌。', 'en': 'Draw 1 additional card at the start of each battle.'},
    },
}

STORY_CARDS = {
    'basic': {
        'source_card_id': 'Basic',
        'name': {'zh': '基本', 'en': 'Basic'},
        'type': 'thorn', 'rarity': 'basic', 'cost_e': 1, 'cost_m': 0,
        'description': {'zh': '对目标造成6D。', 'en': 'Deal 6 D to the target.'},
        'effects': ({'type': 'damage', 'amount': 6},),
        'upgrade': {
            'description': {'zh': '对目标造成9D。', 'en': 'Deal 9 D to the target.'},
            'effects': ({'type': 'damage', 'amount': 9},),
        },
    },
    'rose': {
        'source_card_id': 'Rose',
        'name': {'zh': '玫瑰', 'en': 'Rose'},
        'type': 'bloom', 'rarity': 'basic', 'cost_e': 1, 'cost_m': 0,
        'description': {'zh': '获得5层护盾。', 'en': 'Gain 5 Shield.'},
        'effects': ({'type': 'shield', 'amount': 5},),
        'upgrade': {
            'description': {'zh': '获得8层护盾。', 'en': 'Gain 8 Shield.'},
            'effects': ({'type': 'shield', 'amount': 8},),
        },
    },
    'bone': {
        'source_card_id': 'Bone',
        'name': {'zh': '骨头', 'en': 'Bone'},
        'type': 'thorn', 'rarity': 'common', 'cost_e': 1, 'cost_m': 0,
        'description': {'zh': '对目标造成5D；获得5层护盾。', 'en': 'Deal 5 D; gain 5 Shield.'},
        'effects': ({'type': 'damage', 'amount': 5}, {'type': 'shield', 'amount': 5}),
        'upgrade': {
            'description': {'zh': '对目标造成7D；获得7层护盾。', 'en': 'Deal 7 D; gain 7 Shield.'},
            'effects': ({'type': 'damage', 'amount': 7}, {'type': 'shield', 'amount': 7}),
        },
    },
    'bur': {
        'source_card_id': 'Bur',
        'name': {'zh': '刺果', 'en': 'Bur'},
        'type': 'thorn', 'rarity': 'common', 'cost_e': 1, 'cost_m': 0,
        'description': {'zh': '对目标造成7D，并施加1层易损。', 'en': 'Deal 7 D and apply 1 Vulnerable.'},
        'effects': ({'type': 'damage', 'amount': 7}, {'type': 'enemy_status', 'status': 'vulnerable', 'amount': 1}),
        'upgrade': {
            'description': {'zh': '对目标造成9D，并施加2层易损。', 'en': 'Deal 9 D and apply 2 Vulnerable.'},
            'effects': ({'type': 'damage', 'amount': 9}, {'type': 'enemy_status', 'status': 'vulnerable', 'amount': 2}),
        },
    },
    'rock': {
        'source_card_id': 'Rock',
        'name': {'zh': '岩石', 'en': 'Rock'},
        'type': 'thorn', 'rarity': 'common', 'cost_e': 1, 'cost_m': 0,
        'description': {'zh': '对目标造成8D，并施加1层虚弱。', 'en': 'Deal 8 D and apply 1 Weak.'},
        'effects': ({'type': 'damage', 'amount': 8}, {'type': 'enemy_status', 'status': 'weak', 'amount': 1}),
        'upgrade': {
            'description': {'zh': '对目标造成11D，并施加1层虚弱。', 'en': 'Deal 11 D and apply 1 Weak.'},
            'effects': ({'type': 'damage', 'amount': 11}, {'type': 'enemy_status', 'status': 'weak', 'amount': 1}),
        },
    },
    'triangle': {
        'source_card_id': 'Triangle',
        'name': {'zh': '三角形', 'en': 'Triangle'},
        'type': 'thorn', 'rarity': 'rare', 'cost_e': 1, 'cost_m': 0,
        'description': {'zh': '对目标造成3D；获得1层力量。', 'en': 'Deal 3 D; gain 1 Power.'},
        'effects': ({'type': 'damage', 'amount': 3}, {'type': 'power', 'amount': 1}),
        'upgrade': {
            'description': {'zh': '对目标造成5D；获得1层力量。', 'en': 'Deal 5 D; gain 1 Power.'},
            'effects': ({'type': 'damage', 'amount': 5}, {'type': 'power', 'amount': 1}),
        },
    },
    'coffee': {
        'source_card_id': 'Coffee',
        'name': {'zh': '咖啡', 'en': 'Coffee'},
        'type': 'bloom', 'rarity': 'rare', 'cost_e': 1, 'cost_m': 0,
        'description': {'zh': '回复自己2E；放逐。', 'en': 'Recover 2 E; Exile.'},
        'effects': ({'type': 'elixir', 'amount': 2},),
        'exile': True,
        'upgrade': {'cost_e': 0},
    },
    'sand': {
        'source_card_id': 'Sand',
        'name': {'zh': '沙子', 'en': 'Sand'},
        'type': 'thorn', 'rarity': 'rare', 'cost_e': 1, 'cost_m': 0,
        'description': {'zh': '对目标造成1D×5。', 'en': 'Deal 1 D 5 times.'},
        'effects': ({'type': 'damage', 'amount': 1, 'hits': 5},),
        'upgrade': {
            'description': {'zh': '对目标造成1D×7。', 'en': 'Deal 1 D 7 times.'},
            'effects': ({'type': 'damage', 'amount': 1, 'hits': 7},),
        },
    },
}

STORY_REWARD_CARD_IDS = ('bone', 'bur', 'rock', 'triangle', 'coffee', 'sand', 'rose')

STORY_RELICS = {
    'energetic': {
        'name': {'zh': '精力充沛', 'en': 'Energetic'},
        'description': {'zh': '每完成一层，回复4H。', 'en': 'Recover 4 H after completing a floor.'},
    },
}

STORY_ENEMIES = {
    'soldier_ant': {
        'name': {'zh': '兵蚁', 'en': 'Soldier Ant'},
        'max_health': 56,
        'moves': (
            {'name': {'zh': '啃咬', 'en': 'Bite'}, 'effects': ({'type': 'damage', 'amount': 8},)},
            {'name': {'zh': '冲撞', 'en': 'Charge'}, 'effects': ({'type': 'damage', 'amount': 16}, {'type': 'self_damage', 'amount': 16})},
            {'name': {'zh': '振翅', 'en': 'Flutter'}, 'effects': ({'type': 'gain_power', 'amount': 3},)},
        ),
    },
    'veteran_ant': {
        'name': {'zh': '强壮兵蚁', 'en': 'Veteran Ant'},
        'max_health': 72,
        'moves': (
            {'name': {'zh': '啃咬', 'en': 'Bite'}, 'effects': ({'type': 'damage', 'amount': 11},)},
            {'name': {'zh': '冲撞', 'en': 'Charge'}, 'effects': ({'type': 'damage', 'amount': 18}, {'type': 'self_damage', 'amount': 12})},
            {'name': {'zh': '振翅', 'en': 'Flutter'}, 'effects': ({'type': 'gain_power', 'amount': 4},)},
        ),
    },
    'spider_yuba': {
        'name': {'zh': '蜘蛛尤巴', 'en': 'Yuba Spider'},
        'max_health': 102,
        'moves': (
            {'name': {'zh': '下劈', 'en': 'Chop'}, 'effects': ({'type': 'damage', 'amount': 11}, {'type': 'gain_power', 'amount': 2})},
            {'name': {'zh': '嘲讽', 'en': 'Taunt'}, 'effects': ({'type': 'gain_shield', 'amount': 10}, {'type': 'player_status', 'status': 'vulnerable', 'amount': 3})},
            {'name': {'zh': '回旋斩', 'en': 'Whirlwind'}, 'effects': ({'type': 'damage', 'amount': 3, 'hits': 3},)},
        ),
    },
    'digger': {
        'name': {'zh': '挖掘者', 'en': 'Digger'},
        'max_health': 173,
        'moves': (
            {'name': {'zh': '冲撞', 'en': 'Charge'}, 'effects': ({'type': 'damage', 'amount': 12},)},
            {'name': {'zh': '蓄力', 'en': 'Power Up'}, 'effects': ({'type': 'gain_power', 'amount': 2},)},
            {'name': {'zh': '回旋', 'en': 'Sweep'}, 'effects': ({'type': 'damage', 'amount': 5, 'hits': 2},)},
        ),
    },
}


def initial_story_player():
    deck_ids = ('basic',) * 5 + ('rose',) * 4 + ('bone',)
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
        'gold': 0,
        'deck': deck,
        'relics': [],
        'blessing': None,
        'opening_draw_bonus': 0,
        'next_card_serial': len(deck) + 1,
    }


def story_content_payload(card_defs=None):
    cards = deepcopy(STORY_CARDS)
    if card_defs:
        for definition in cards.values():
            source = card_defs.get(definition.get('source_card_id'))
            if source is None:
                continue
            image_url = str(
                getattr(source, 'image_url', '')
                or getattr(source, 'image', '')
                or ''
            )
            upgraded_image_url = str(
                getattr(source, 'upgraded_image_url', '')
                or getattr(source, 'upgraded_image', '')
                or image_url
            )
            if image_url:
                definition['image_url'] = image_url
            if upgraded_image_url:
                definition['upgraded_image_url'] = upgraded_image_url
    return {
        'rules': deepcopy(STORY_RULES),
        'blessings': deepcopy(STORY_BLESSINGS),
        'cards': cards,
        'relics': deepcopy(STORY_RELICS),
    }
