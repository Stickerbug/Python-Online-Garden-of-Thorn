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
    'infect': {'name': {'zh': '状态牌', 'en': 'Infect'}, 'color': '#7E9638'},
}

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
            'en': 'When drawn or at the turn boundary, play this automatically if it is playable.',
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
        'description': {'zh': '对所有可选中的敌方单位生效。', 'en': 'Apply the effect to every selectable enemy.'},
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
        'description': {'zh': '跳过层数个可行动回合。', 'en': 'Skip that many actionable turns.'},
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
                    '对目标造成16D；放逐自己1张其他手牌。',
                    effects=(_effect('damage', 16), _effect('choose_exile', 1, exact=True)),
                    upgrade={'description': {'zh': '对目标造成20D；放逐自己至多1张其他手牌。', 'en': 'Deal 20 D; exile up to 1 other card.'},
                             'effects': (_effect('damage', 20), _effect('choose_exile', 1, exact=False))}),
    'bone': _card('Bone', '骨头', 'Bone', 1, 'thorn', 'common',
                  '对目标造成5D；获得5层护盾。',
                  effects=(_effect('damage', 5), _effect('shield', 5)),
                  upgrade={'description': {'zh': '对目标造成7D；获得7层护盾。', 'en': 'Deal 7 D; gain 7 Shield.'},
                           'effects': (_effect('damage', 7), _effect('shield', 7))}),
    'coffee': _card('Coffee', '咖啡', 'Coffee', 1, 'bloom', 'rare',
                    '回复自己2E。', effects=(_effect('elixir', 2),), tags=('exile',),
                    owner='neutral', upgrade={'cost_e': 0}),
    'bur': _card('Bur', '刺果', 'Bur', 1, 'thorn', 'common',
                 '对目标造成7D，并施加1层易伤。',
                 effects=(_effect('damage', 7), _effect('status', 1, status='vulnerable')),
                 upgrade={'description': {'zh': '对目标造成9D，并施加2层易伤。', 'en': 'Deal 9 D and apply 2 Vulnerable.'},
                          'effects': (_effect('damage', 9), _effect('status', 2, status='vulnerable'))}),
    'torch': _card('Torch', '火把', 'Torch', 1, 'thorn', 'common',
                   '对目标造成9D；放逐自己1张其他手牌，然后抽1张牌。',
                   effects=(_effect('damage', 9), _effect('choose_exile', 1, exact=True), _effect('draw', 1)),
                   upgrade={'description': {'zh': '对目标造成11D；放逐自己1张其他手牌，然后抽2张牌。', 'en': 'Deal 11 D; exile 1 other card, then draw 2.'},
                            'effects': (_effect('damage', 11), _effect('choose_exile', 1, exact=True), _effect('draw', 2))}),
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
                   target='self', upgrade={'description': {'zh': '回合开始时获得7层护盾。', 'en': 'At turn start, gain 7 Shield.'},
                                           'effects': (_effect('equipment', 7, script='start_shield'),)}),
    'lightning': _card('Lightning', '闪电', 'Lightning', 1, 'thorn', 'common',
                       '对所有敌人造成3D×2。', tags=('wide',),
                       effects=(_effect('damage', 3, hits=2),),
                       upgrade={'description': {'zh': '对所有敌人造成5D×2。', 'en': 'Deal 5 D twice to all enemies.'},
                                'effects': (_effect('damage', 5, hits=2),)}),
    'magic_torch': _card('Magic Torch', '魔法火把', 'Magic Torch', 2, 'bloom', 'ultra',
                         '放逐全部其他手牌，每放逐1张获得5层护盾。',
                         tags=('exile',), effects=(_effect('exile_hand_for_shield', 5),),
                         upgrade={'description': {'zh': '放逐全部其他手牌，每放逐1张获得7层护盾。', 'en': 'Exile your other hand; gain 7 Shield per card.'},
                                  'effects': (_effect('exile_hand_for_shield', 7),)}),
    'sponge': _card('Sponge', '海绵', 'Sponge', 2, 'root', 'rare',
                    '目标受到伤害时，改为获得等同于伤害向上取整一半的中毒。',
                    target='self', effects=(_effect('equipment', script='sponge'),),
                    upgrade={'cost_e': 1}),
    'mimic': _card('Mimic', '拟态', 'Mimic', 0, 'bloom', 'ultra',
                   '选择自己1张其他手牌，将其复制加入手牌。',
                   owner='neutral', tags=('exile',), effects=(_effect('copy_hand_card', 1),),
                   upgrade={'description': {'zh': '选择自己1张其他手牌，将其带有迅捷1的复制加入手牌。', 'en': 'Copy another card in hand with Swift 1.'},
                            'effects': (_effect('copy_hand_card', 1, swift=1),)}),
    'light': _card('Light', '轻', 'Light', 0, 'thorn', 'common',
                   '对目标造成2D×2；若此牌无放逐，将1张带有放逐的复制洗入抽牌堆。',
                   effects=(_effect('damage', 2, hits=2),), script='light_sprout',
                   upgrade={
                       'description': {
                           'zh': '对目标造成3D×2；若此牌无放逐，将1张带有放逐的复制洗入抽牌堆。',
                           'en': 'Deal 3 D twice; if this has no Exile, shuffle an Exile copy into the draw pile.',
                       },
                       'effects': (_effect('damage', 3, hits=2),),
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
                   '获得14层护盾；放逐自己1张其他手牌，然后抽1张牌。',
                   effects=(_effect('shield', 14), _effect('choose_exile', 1, exact=True), _effect('draw', 1)),
                   upgrade={'description': {'zh': '获得18层护盾；放逐自己至多1张其他手牌，然后抽1张牌。', 'en': 'Gain 18 Shield; exile up to 1 other card, then draw 1.'},
                            'effects': (_effect('shield', 18), _effect('choose_exile', 1, exact=False), _effect('draw', 1))}),
    'heavy': _card('Heavy', '重', 'Heavy', 3, 'thorn', 'ultra',
                   '对目标造成26D；此牌受到的力量加成变为4倍。',
                   tags=('exile',), effects=(_effect('damage', 26, power_scale=4),),
                   upgrade={'description': {'zh': '对目标造成30D；此牌受到的力量加成变为6倍。', 'en': 'Deal 30 D; Power applies 6 times.'},
                            'effects': (_effect('damage', 30, power_scale=6),)}),
    'disc': _card('Disc', '圆盘', 'Disc', 2, 'bloom', 'rare',
                  '本回合受到的物理伤害向下取整减半。',
                  effects=(_effect('temporary_effect', script='disc'),),
                  upgrade={'description': {'zh': '本回合受到的物理伤害向下取整减半；获得5层护盾。', 'en': 'Halve physical damage this turn; gain 5 Shield.'},
                           'effects': (_effect('temporary_effect', script='disc'), _effect('shield', 5))}),
    'salt': _card('Salt', '盐', 'Salt', 1, 'bloom', 'rare',
                  '获得1层闪避；下回合开始时，对生命值最高的敌人造成本次闪避伤害。',
                  owner='neutral', effects=(_effect('salt', 1),),
                  upgrade={'description': {'zh': '获得1层闪避；下回合开始时，对生命值最高的敌人造成本次闪避伤害的2倍。', 'en': 'Gain Evade; next turn deal twice the evaded damage.'},
                           'effects': (_effect('salt', 2),)}),
    'magic_shell': _card('Magic Shell', '魔法贝壳', 'Magic Shell', 1, 'bloom', 'rare',
                         '抽2张牌；获得3层护盾。',
                         effects=(_effect('draw', 2), _effect('shield', 3)),
                         upgrade={'description': {'zh': '抽3张牌；获得4层护盾。', 'en': 'Draw 3; gain 4 Shield.'},
                                  'effects': (_effect('draw', 3), _effect('shield', 4))}),
    'pearl': _card('Pearl', '珍珠', 'Pearl', 2, 'root', 'ultra',
                   '每有1张非轻的牌被放逐，将1张带有保留和放逐的轻加入手牌。',
                   effects=(_effect('equipment', script='pearl'),), target='self',
                   upgrade={'cost_e': 1}),
    'crystal_leaf': _card('Crystal Leaf', '水晶叶', 'Crystal Leaf', 2, 'root', 'rare',
                          '回合开始时获得2层力量。',
                          effects=(_effect('equipment', 2, script='start_power'),), target='self',
                          upgrade={'description': {'zh': '回合开始时获得3层力量。', 'en': 'At turn start, gain 3 Power.'},
                                   'effects': (_effect('equipment', 3, script='start_power'),)}),
    'magic_crystal_leaf': _card('Magic Crystal Leaf', '魔法水晶叶', 'Magic Crystal Leaf', 2, 'bloom', 'rare',
                                '获得4层力量。', effects=(_effect('power', 4),),
                                upgrade={'description': {'zh': '获得6层力量。', 'en': 'Gain 6 Power.'},
                                         'effects': (_effect('power', 6),)}),
    'magic_pearl': _card('Magic Pearl', '魔法珍珠', 'Magic Pearl', 2, 'root', 'ultra',
                         '每有1张牌被放逐，获得1层力量。',
                         effects=(_effect('equipment', script='magic_pearl'),), target='self',
                         upgrade={'cost_e': 1}),
    'magic_acid': _card('Acid', '魔法酸', 'Magic Acid', 2, 'root', 'ultra',
                        '每有1张牌被放逐，抽1张牌。',
                        effects=(_effect('equipment', script='magic_acid'),), target='self',
                        upgrade={'cost_e': 1}),
    'azalea': _card('Azalea', '杜鹃花', 'Azalea', 1, 'bloom', 'common',
                    '获得5层护盾；被放逐时获得3层护盾，并将1张复制加入弃牌堆。',
                    effects=(_effect('shield', 5),), script='azalea',
                    upgrade={'description': {'zh': '获得7层护盾；被放逐时获得4层护盾，并将1张复制加入弃牌堆。', 'en': 'Gain 7 Shield; when exiled gain 4 and add a copy to discard.'},
                             'effects': (_effect('shield', 7),), 'script': 'azalea_plus'}),
    'fusion': _card('Fusion', '聚变', 'Fusion', 1, 'bloom', 'ultra',
                    '本回合下一张攻击牌的伤害变为2倍。',
                    owner='neutral', tags=('exile',), effects=(_effect('next_attack_multiplier', 2),),
                    upgrade={'description': {'zh': '本回合下一张攻击牌的伤害变为3倍。', 'en': 'Your next attack this turn deals triple damage.'},
                             'effects': (_effect('next_attack_multiplier', 3),)}),
    'chromosome': _card('Chromosome', '染色体', 'Chromosome', 1, 'bloom', 'rare',
                        '获得5层护盾；抽1张牌。',
                        effects=(_effect('shield', 5), _effect('draw', 1)),
                        upgrade={'description': {'zh': '获得5层护盾；抽1张牌，然后将弃牌堆1张牌置于抽牌堆顶。', 'en': 'Gain 5 Shield; draw 1, then put a discard on top.'},
                                 'effects': (_effect('shield', 5), _effect('draw', 1), _effect('discard_to_draw_top', 1))}),
    'dna': _card('DNA', 'DNA', 'DNA', 1, 'bloom', 'rare',
                 '获得2层耐力。', effects=(_effect('status_self', 2, status='endurance'),),
                 upgrade={'description': {'zh': '获得3层耐力。', 'en': 'Gain 3 Endurance.'},
                          'effects': (_effect('status_self', 3, status='endurance'),)}),
    'moon_rock': _card('Moon Rock', '月石', 'Moon Rock', 2, 'bloom', 'rare',
                       '获得30层护盾；失去2层力量。',
                       effects=(_effect('shield', 30), _effect('power', -2)),
                       upgrade={'description': {'zh': '获得35层护盾；失去2层力量。', 'en': 'Gain 35 Shield; lose 2 Power.'},
                                'effects': (_effect('shield', 35), _effect('power', -2))}),
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
                    upgrade={'description': {'zh': '对目标造成自己护盾层数×2的D。', 'en': 'Deal D equal to twice your Shield.'},
                             'effects': (_effect('damage_from_shield', 2),)}),
    'powder': _card('Powder', '粉末', 'Powder', 2, 'root', 'rare',
                    '每回合多回复1E。', effects=(_effect('equipment', 1, script='turn_elixir'),), target='self',
                    upgrade={'cost_e': 1}),
    'rna': _card('RNA', 'RNA', 'RNA', 1, 'root', 'rare',
                 '每次对敌人施加易伤时，获得4层护盾。',
                 effects=(_effect('equipment', 4, script='vulnerable_shield'),), target='self',
                 upgrade={'description': {'zh': '每次对敌人施加易伤时，获得6层护盾。', 'en': 'When applying Vulnerable, gain 6 Shield.'},
                          'effects': (_effect('equipment', 6, script='vulnerable_shield'),)}),
    'nuke': _card('Nuke', '核弹', 'Nuke', 'X', 'thorn', 'common',
                  '消耗自己所有E；每消耗1E，对目标造成9D一次。',
                  effects=(_effect('damage_per_elixir', 9),),
                  upgrade={'description': {'zh': '消耗自己所有E；每消耗1E，对目标造成13D一次。', 'en': 'Spend all E; deal 13 D once per E.'},
                           'effects': (_effect('damage_per_elixir', 13),)}),
    'rmb': _card('RMB', '人民币', 'RMB', 2, 'root', 'ultra',
                 '战斗胜利时获得25G。', owner='neutral',
                 effects=(_effect('equipment', 25, script='victory_gold'),), target='self',
                 upgrade={'description': {'zh': '战斗胜利时获得40G。', 'en': 'Gain 40 G after winning combat.'},
                          'effects': (_effect('equipment', 40, script='victory_gold'),)}),
    'magic_bur': _card('Magic Bur', '魔法刺果', 'Magic Bur', 1, 'bloom', 'rare',
                       '对目标施加1层易伤；获得其易伤层数×3的护盾。',
                       target='enemy',
                       effects=(_effect('status', 1, status='vulnerable'), _effect('shield_from_target_status', 3, status='vulnerable')),
                       upgrade={'description': {'zh': '对目标施加2层易伤；获得其易伤层数×3的护盾。', 'en': 'Apply 2 Vulnerable; gain triple its stacks as Shield.'},
                                'effects': (_effect('status', 2, status='vulnerable'), _effect('shield_from_target_status', 3, status='vulnerable'))}),
    'fission': _card('Fission', '裂变', 'Fission', 1, 'bloom', 'ultra',
                     '本回合下一张技能牌额外打出1次，且不额外消耗E。',
                     owner='neutral', effects=(_effect('next_skill_repeats', 1),),
                     upgrade={'description': {'zh': '本回合下一张技能牌额外打出2次，且不额外消耗E。', 'en': 'Play your next skill 2 extra times at no E cost.'},
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
    'fragment': _card('Fragment', '碎片', 'Fragment', 0, 'bloom', 'super',
                      '放逐自己1张其他手牌；获得2层力量。', tags=('exile',),
                      effects=(_effect('choose_exile', 1, exact=True), _effect('power', 2))),
    'rice': _card('Rice', '米', 'Rice', 0, 'thorn', 'super',
                  '对目标造成6D，然后将此牌置于抽牌堆顶。',
                  effects=(_effect('damage', 6),), script='return_draw_top',
                  upgrade={'description': {'zh': '对目标造成9D，然后将此牌置于抽牌堆顶。', 'en': 'Deal 9 D, then put this on top of the draw pile.'},
                           'effects': (_effect('damage', 9),)}),
    'glass': _card('Glass', '玻璃', 'Glass', 0, 'thorn', 'super',
                   '对目标造成3D；下回合开始时将1张复制加入手牌。',
                   effects=(_effect('damage', 3), _effect('delayed_copy', 1)),
                   upgrade={'description': {'zh': '对目标造成5D；下回合开始时将1张复制加入手牌。', 'en': 'Deal 5 D; add a copy next turn.'},
                            'effects': (_effect('damage', 5), _effect('delayed_copy', 1))}),
    'dust': _card('Dust', '灰尘', 'Dust', 0, 'thorn', 'super',
                  '对目标造成3D；获得3层护盾。',
                  effects=(_effect('damage', 3), _effect('shield', 3)),
                  upgrade={'description': {'zh': '对目标造成4D；获得4层护盾。', 'en': 'Deal 4 D; gain 4 Shield.'},
                           'effects': (_effect('damage', 4), _effect('shield', 4))}),
    'leaf': _card('Leaf', '叶子', 'Leaf', 0, 'bloom', 'common',
                  '获得3层护盾。', effects=(_effect('shield', 3),),
                  upgrade={'description': {'zh': '获得5层护盾。', 'en': 'Gain 5 Shield.'},
                           'effects': (_effect('shield', 5),)}),
    'acid': _card('Acid', '酸', 'Acid', 0, 'thorn', 'common',
                  '对目标造成7D；随机放逐自己1张其他手牌。',
                  effects=(_effect('damage', 7), _effect('random_exile', 1)),
                  upgrade={'description': {'zh': '对目标造成10D；随机放逐自己1张其他手牌。', 'en': 'Deal 10 D; randomly exile another card.'},
                           'effects': (_effect('damage', 10), _effect('random_exile', 1))}),
    'pyrite': _card('Pyrite', '黄铁矿', 'Pyrite', 0, 'bloom', 'super',
                    '回复自己2E；放逐自己1张其他手牌。',
                    effects=(_effect('elixir', 2), _effect('choose_exile', 1, exact=True)),
                    upgrade={'description': {'zh': '回复自己3E；放逐自己1张其他手牌。', 'en': 'Recover 3 E; exile another card.'},
                             'effects': (_effect('elixir', 3), _effect('choose_exile', 1, exact=True))}),
    'feather': _card('Feather', '羽毛', 'Feather', 1, 'bloom', 'super',
                     '抽3张牌。', effects=(_effect('draw', 3),),
                     upgrade={'description': {'zh': '抽4张牌。', 'en': 'Draw 4.'},
                              'effects': (_effect('draw', 4),)}),
    'magic_feather': _card('Magic Feather', '魔法羽毛', 'Magic Feather', 1, 'bloom', 'common',
                           '回复自己等同于当前手牌数向下取整一半的E；本回合无法再抽牌。',
                           effects=(_effect('elixir_from_hand', 0.5), _effect('temporary_effect', script='cannot_draw')),
                           upgrade={'cost_e': 0}),
    'bubble': _card('Bubble', '泡泡', 'Bubble', 0, 'bloom', 'rare',
                    '抽3张牌。', owner='neutral', tags=('exile',), effects=(_effect('draw', 3),),
                    upgrade={'description': {'zh': '抽4张牌。', 'en': 'Draw 4.'},
                             'effects': (_effect('draw', 4),)}),
    'magic_bubble': _card('Magic Bubble', '魔法泡泡', 'Magic Bubble', 1, 'bloom', 'rare',
                          '抽牌至手牌上限。', owner='neutral', tags=('exile',),
                          effects=(_effect('draw_to_limit', 0),), upgrade={'cost_e': 0}),
    'mark': _card('Mark', '标记', 'Mark', 2, 'bloom', 'super',
                  '对目标施加1层眩晕。', target='enemy',
                  effects=(_effect('status', 1, status='stun'),), upgrade={'cost_e': 1}),
}


STORY_REWARD_CARD_IDS = tuple(
    card_id
    for card_id, definition in STORY_CARDS.items()
    if definition['rarity'] in ('common', 'rare', 'ultra')
    and definition['type'] not in ('curse', 'infect')
)


def _relic(zh, en, description, rarity='common', script=None, amount=0):
    return {
        'name': {'zh': zh, 'en': en},
        'description': {'zh': description, 'en': description},
        'rarity': rarity,
        'script': script,
        'amount': amount,
    }


STORY_RELICS = {
    'energetic': _relic('精力充沛', 'Energetic', '每完成一层，回复4H。', script='floor_heal', amount=4),
    'ruthless': _relic('无情猛击', 'Ruthless Strike', '战斗开始时获得1层力量。', script='opening_power', amount=1),
    'firm_defense': _relic('坚定防守', 'Firm Defense', '战斗开始时获得1层耐力。', script='opening_endurance', amount=1),
    'fearless_pain': _relic('无惧疼痛', 'Fearless Pain', '每次受到的伤害-1。', script='flat_damage_reduction', amount=1),
    'circulation': _relic('回转', 'Circulation', '商店购买后会补充货品。', rarity='rare', script='shop_restock'),
    'prepared': _relic('未雨绸缪', 'Prepared', '第一回合额外抽2张牌。', script='opening_draw', amount=2),
    'cooldown': _relic('冷却', 'Cooldown', '第一回合可丢弃任意张牌，然后抽等量的牌。', rarity='rare', script='opening_redraw'),
    'accumulate': _relic('厚积薄发', 'Accumulate', '第二回合获得5层暂时力量。', rarity='rare', script='round_power', amount=5),
    'opening_lightning': _relic('开幕雷击', 'Opening Lightning', '战斗开始时对所有敌人造成9D。', rarity='rare', script='opening_damage', amount=9),
    'solid_barrier': _relic('坚固壁垒', 'Solid Barrier', '本场战斗第一次受伤时回复2E。', rarity='rare', script='first_hit_elixir', amount=2),
    'sharpen': _relic('磨刀', 'Sharpen', '获得时升级2张牌。', rarity='rare', script='gain_upgrade', amount=2),
    'blade': _relic('利刃', 'Blade', '本场战斗第一次攻击时，对目标施加1层易伤。', rarity='rare', script='first_attack_vulnerable', amount=1),
    'steady': _relic('稳扎稳打', 'Steady', '所有基础牌的数值+2。', rarity='rare', script='primary_bonus', amount=2),
    'rich': _relic('富裕', 'Rich', '获得时获得200G。', script='gain_gold', amount=200),
    'diligent': _relic('勤学', 'Diligent', '每获得1张新牌，回复5H。', script='gain_card_heal', amount=5),
    'greedy': _relic('贪婪', 'Greedy', '休息区可选择获得150G。', rarity='rare', script='rest_gold', amount=150),
    'body_reinforcement': _relic('肉体强化', 'Body Reinforcement', '获得时最大生命值+10，并回复10H。', script='gain_max_health', amount=10),
    'indomitable': _relic('愈挫愈勇', 'Indomitable', '普通战斗失去超过15H时，随机升级1张牌。', rarity='rare', script='loss_upgrade', amount=15),
    'support': _relic('支援', 'Support', '第一回合少抽1张牌；每回合获得3层护盾。', rarity='rare', script='support', amount=3),
    'bargaining': _relic('讨价还价', 'Bargaining', '商店价格降低30%。', rarity='rare', script='shop_discount', amount=30),
    'world_tree_leaf': _relic('世界树之叶', 'World Tree Leaf', '本次旅程首次死亡时，清除效果并回复至满H。', rarity='ultra', script='revive'),
}


def _move(zh, en, *effects):
    return {'name': {'zh': zh, 'en': en}, 'effects': tuple(effects)}


def _enemy(zh, en, health, moves, *, script=None):
    return {
        'name': {'zh': zh, 'en': en},
        'max_health': health,
        'moves': tuple(moves),
        'script': script,
    }


STORY_ENEMIES = {
    'soldier_ant': _enemy('兵蚁', 'Soldier Ant', 56, (
        _move('啃咬', 'Bite', _effect('damage', 8), _effect('gain_shield', 8)),
        _move('头锤', 'Headbutt', _effect('damage', 16), _effect('self_damage', 16)),
        _move('振翅', 'Flutter', _effect('gain_power', 3), _effect('gain_shield', 12)),
    )),
    'young_ant': _enemy('幼蚁', 'Young Ant', 14, (
        _move('啃咬', 'Bite', _effect('damage', 4), _effect('gain_shield', 6)),
        _move('跳动', 'Jump', _effect('damage', 2, hits=3)),
    )),
    'worker_ant': _enemy('工蚁', 'Worker Ant', 42, (
        _move('鼓舞', 'Inspire', _effect('damage', 4), _effect('allies_power', 1)),
        _move('护卫', 'Guard', _effect('damage', 6), _effect('lowest_ally_shield', 8)),
        _move('狂暴', 'Frenzy', _effect('damage', 3, hits=3)),
    ), script='worker_ant'),
    'bee': _enemy('蜜蜂', 'Bee', 39, (
        _move('花粉', 'Pollen', _effect('player_status', 3, status='broken')),
        _move('撞击', 'Collision', _effect('damage', 8)),
    )),
    'wasp': _enemy('黄蜂', 'Wasp', 31, (
        _move('蓄势待发', 'Ready', _effect('gain_shield', 6), _effect('player_status', 1, status='weak')),
        _move('射击', 'Shot', _effect('damage', 14)),
    )),
    'ladybug': _enemy('瓢虫', 'Ladybug', 41, (
        _move('呵护', 'Care', _effect('allies_heal', 13)),
        _move('保护', 'Protect', _effect('damage', 8), _effect('player_status', 1, status='weak')),
    )),
    'garden_rock': _enemy('岩石', 'Rock', 52, (
        _move('滚动', 'Roll', _effect('gain_status', 1, status='rockfall'), _effect('player_status', 1, status='weak')),
        _move('坚固', 'Solid', _effect('allies_shield', 8)),
    ), script='garden_rock'),
    'dandelion': _enemy('蒲公英', 'Dandelion', 32, (
        _move('种子', 'Seed', _effect('damage', 1, hits=3), _effect('player_status', 1, status='vulnerable')),
        _move('喷发', 'Erupt', _effect('damage', 8), _effect('gain_power', 2), _effect('player_status', 1, status='fragile')),
    )),
    'centipede': _enemy('蜈蚣体节', 'Centipede Segment', 42, (
        _move('扭动', 'Twist', _effect('damage', 2, hits=3)),
        _move('冲击', 'Impact', _effect('damage', 8)),
        _move('防护', 'Protect', _effect('adjacent_shield', 10), _effect('player_status', 1, status='fragile')),
        _move('生长', 'Growth', _effect('gain_power', 2)),
    ), script='centipede'),
    'spider': _enemy('蜘蛛', 'Spider', 47, (
        _move('吐网', 'Web', _effect('player_status', 1, status='weak'), _effect('add_draw_card', 1, card_id='slimed')),
        _move('收网', 'Reel', _effect('damage', 8)),
    )),
    'sunflower': _enemy('向日葵', 'Sunflower', 40, (
        _move('生长', 'Grow', _effect('gain_shield', 20), _effect('gain_power', 3)),
        _move('绽放', 'Bloom', _effect('damage', 2)),
    ), script='persistent_shield'),
    'avocado': _enemy('牛油果', 'Avocado', 76, (
        _move('旋转', 'Spin', _effect('damage', 3, hits=3)),
        _move('膨胀', 'Expand', _effect('damage', 11), _effect('gain_power', 1)),
    ), script='swell'),
    'spider_yuba': _enemy('蜘蛛尤巴', 'Yuba Spider', 102, (
        _move('下劈', 'Chop', _effect('damage', 11), _effect('gain_power', 2)),
        _move('嘲讽', 'Taunt', _effect('gain_shield', 10), _effect('player_status', 3, status='vulnerable')),
        _move('回旋斩', 'Whirlwind', _effect('damage', 3, hits=3)),
    )),
    'digger': _enemy('挖掘者', 'Digger', 173, (
        _move('冲撞', 'Charge', _effect('damage', 12)),
        _move('蓄力', 'Power Up', _effect('gain_power', 2)),
        _move('回旋', 'Sweep', _effect('damage', 5, hits=2)),
    ), script='opening_reflection'),
    'ant_queen': _enemy('蚁后', 'Ant Queen', 142, (
        _move('振奋', 'Inspire', _effect('damage', 5), _effect('allies_power', 2)),
        _move('连劈', 'Combo', _effect('damage', 3, hits=2)),
        _move('产卵', 'Lay Eggs', _effect('summon_to_ant_count', 4, enemy_id='young_ant')),
        _move('滋养', 'Nourish', _effect('consume_allies', 0)),
    ), script='ant_queen'),
    'hive': _enemy('蜂巢', 'Hive', 151, (
        _move('召唤蜜蜂', 'Summon Bee', _effect('summon', 1, enemy_id='bee', move_index=1, wither=3), _effect('self_damage', 30)),
        _move('召唤黄蜂', 'Summon Wasp', _effect('summon', 1, enemy_id='wasp', move_index=0, wither=3), _effect('self_damage', 30)),
        _move('蜂蜜', 'Honey', _effect('self_heal', 15), _effect('player_status', 1, status='fragile'), _effect('player_status', 1, status='vulnerable')),
    ), script='hive'),
}

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
    'spider_yuba': '/static/assets/story-enemies/spider-yuba.svg',
    'digger': '/static/assets/story-enemies/digger.svg',
    'ant_queen': '/static/assets/story-enemies/ant-queen.svg',
    'hive': '/static/assets/story-enemies/hive.svg',
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
            ('spider_yuba',),
            ('avocado',),
        ),
        'boss': (
            ('ant_queen', 'worker_ant', 'young_ant'),
            ('hive', 'bee'),
            ('digger',),
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
        'gold': 0,
        'deck': deck,
        'relics': [],
        'blessing': None,
        'opening_draw_bonus': 0,
        'next_card_serial': len(deck) + 1,
    }


def _find_source(card_defs, source_id):
    if not source_id or not card_defs:
        return None
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
    source_key = str(source_id).lower().replace('_', '').replace(' ', '')
    for key, source in card_defs.items():
        key_value = str(key).split(':')[-1].lower().replace('_', '').replace(' ', '')
        if key_value == source_key:
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
            if image_url:
                definition['image_url'] = image_url
            if upgraded_image_url:
                definition['upgraded_image_url'] = upgraded_image_url
    return {
        'rules': deepcopy(STORY_RULES),
        'rarities': deepcopy(STORY_RARITIES),
        'card_types': deepcopy(STORY_CARD_TYPES),
        'tags': deepcopy(STORY_TAGS),
        'statuses': deepcopy(STORY_STATUSES),
        'blessings': deepcopy(STORY_BLESSINGS),
        'cards': cards,
        'relics': deepcopy(STORY_RELICS),
        'enemies': deepcopy(STORY_ENEMIES),
    }


def validate_story_content():
    errors = []
    card_effect_types = {
        'choose_exile', 'copy_hand_card', 'damage', 'damage_from_shield',
        'damage_per_elixir', 'damage_per_status', 'decaying_shield',
        'delayed_copy', 'discard_to_draw_top', 'draw', 'draw_target_status',
        'draw_to_limit', 'elixir', 'elixir_from_hand', 'equipment',
        'exile_hand_for_shield', 'first_use_power', 'next_attack_multiplier',
        'magic', 'next_skill_repeats', 'power', 'random_exile', 'salt', 'shield',
        'shield_from_target_status', 'status', 'status_self',
        'temporary_cost_down', 'temporary_effect',
    }
    card_scripts = {
        'azalea', 'azalea_plus', 'light_sprout', 'return_draw_top', 'slimed',
        'startled', 'unrelenting',
    }
    equipment_scripts = {
        'cannot_draw', 'disc', 'magic_acid', 'magic_pearl', 'pearl',
        'soul_splitter', 'sponge', 'start_power', 'start_shield',
        'turn_elixir', 'victory_gold', 'vulnerable_shield',
    }
    relic_scripts = {
        'first_attack_vulnerable', 'first_hit_elixir', 'flat_damage_reduction',
        'floor_heal', 'gain_card_heal', 'gain_gold', 'gain_max_health',
        'gain_upgrade', 'loss_upgrade', 'opening_damage', 'opening_draw',
        'opening_endurance', 'opening_power', 'opening_redraw',
        'primary_bonus', 'rest_gold', 'revive', 'round_power',
        'shop_discount', 'shop_restock', 'support',
    }
    enemy_effect_types = {
        'add_draw_card', 'adjacent_shield', 'allies_heal', 'allies_power',
        'allies_shield', 'consume_allies', 'damage', 'gain_power',
        'gain_shield', 'gain_status', 'lowest_ally_shield', 'player_status',
        'self_damage', 'self_heal', 'summon', 'summon_to_ant_count',
    }
    enemy_scripts = {
        'ant_queen', 'centipede', 'garden_rock', 'hive',
        'opening_reflection', 'persistent_shield', 'swell', 'worker_ant',
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
            if status and status not in STORY_STATUSES:
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

    for relic_id, definition in STORY_RELICS.items():
        if definition.get('rarity') not in STORY_RARITIES:
            errors.append(f'{relic_id}: invalid relic rarity')
        if definition.get('script') not in relic_scripts:
            errors.append(f'{relic_id}: unknown relic script {definition.get("script")}')

    for enemy_id, definition in STORY_ENEMIES.items():
        script = definition.get('script')
        if script and script not in enemy_scripts:
            errors.append(f'{enemy_id}: unknown enemy script {script}')
        for move_index, move in enumerate(definition.get('moves') or ()):
            for effect_index, effect in enumerate(move.get('effects') or ()):
                owner = f'{enemy_id}.moves[{move_index}].effects[{effect_index}]'
                effect_type = effect.get('type')
                if effect_type not in enemy_effect_types:
                    errors.append(f'{owner}: unknown effect {effect_type}')
                status = effect.get('status')
                if status and status not in STORY_STATUSES:
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
