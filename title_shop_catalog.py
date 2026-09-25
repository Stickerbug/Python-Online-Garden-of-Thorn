"""Built-in title shop inventory.

The shop reads this catalog at database initialization so production does not
depend on the development workbook being present.
"""


RARITY_COLORS = {
    'common': '#7EEF6D',
    'unusual': '#FFE65D',
    'rare': '#4D52E3',
    'epic': '#861FDE',
    'legendary': '#DE1F1F',
    'mythic': '#1FDBDE',
    'ultra': '#FF2B75',
    'super': '#2BFFA3',
    'omega': '#F329D9',
    'eternal': '#EEEEEE',
    'unique': '#555555',
}


def _solid(title_id, name, price, color, weight):
    return {
        'id': f'shop:{title_id}',
        'name': name,
        'price': int(price),
        'weight': int(weight),
        'style': f'{{color:{color}}}{name}{{/}}',
    }


def _styled(title_id, name, price, style, weight):
    return {
        'id': f'shop:{title_id}',
        'name': name,
        'price': int(price),
        'weight': int(weight),
        'style': style,
    }


TITLE_SHOP_CATALOG = [
    _solid('spectator', '观战', 15000, 'spectator', 20),
    _solid('thunder-god', '雷神', 25000, RARITY_COLORS['unique'], 20),
    _solid('marker-super', 'Marker', 20000, RARITY_COLORS['super'], 10),
    _solid('marker-common', 'Marker', 5000, RARITY_COLORS['common'], 10),
    _solid('warlock', '邪术师', 25000, RARITY_COLORS['epic'], 20),
    _solid('summoner', '召唤师', 25000, '#FF99CC', 20),
    _solid('orbital-warrior', '轨道战士', 25000, '#99CCFF', 20),
    _solid('ordinary-flower', '普通的花花', 25000, RARITY_COLORS['unusual'], 20),
    _solid('started', '我已启动', 10000, RARITY_COLORS['mythic'], 10),
    _solid('wait-start', '等我启动', 2500, '#B2B641', 10),
    _solid('no-juice-handsome', '没汁帅', 10000, RARITY_COLORS['epic'], 10),
    _solid('mere', '区区', 5000, '#B2B641', 10),
    _solid('great-mathematician', '大数学家', 10000, '#C0C0C0', 10),
    _solid('rafflesia', '大王花', 10000, '#FF6666', 10),
    _solid('question-flower', '?!花花!?', 50, RARITY_COLORS['unusual'], 100),
    _solid('old-mage', '老法师', 25000, RARITY_COLORS['mythic'], 10),
    _solid('old-priest', '老牧师', 25000, '#FFFF00', 10),
    _solid('machine-master', '机械大师', 25000, '#A56C09', 10),
    _solid('exchange-no-juice', '兑没汁帅', 20000, RARITY_COLORS['ultra'], 10),
    _solid('enabled', '开了', 15000, '#000000', 10),
    _solid('lol-thorn', 'lol', 7500, '#C0392B', 5),
    _solid('lol-bloom', 'lol', 7500, '#1ABC9C', 5),
    _solid('lol-root', 'lol', 7500, '#8D6E63', 5),
    _solid('lol-guard', 'lol', 7500, '#2980B9', 5),
    _solid('hungry', '我饥饿', 5000, '#660066', 10),
    _solid('cognitive-bias', '认知偏差', 20000, '#33FFFF', 10),
    _solid('echo-form', '回响形态形响回', 20000, '#CCCC00', 10),
    _solid('click-form', '咔咔形态', 20000, '#FF8000', 10),
    _solid('infinite', '我已无限', 30000, '#4C9900', 10),
    _solid('corruption', '腐化', 25000, '#CC0000', 10),
    _solid('five-equals-one', '5=1', 25000, RARITY_COLORS['super'], 20),
    _solid('dark-mercenary', '黑暗之佣', 15000, '#000000', 10),
    _solid('take-good-cards', '好牌多抓', 10000, '#C0392B', 10),
    _solid('take-every-card', '见牌就抓', 10000, '#1ABC9C', 10),
    _solid('avoid-big-monsters', '避战大怪', 10000, '#2980B9', 10),
    _solid('cowards-defend', '懦夫才防', 10000, '#8D6E63', 10),
    _solid('perfect-style', '完美潇洒', 30000, '#E0E0E0', 3),
    _solid('scarlet-destiny', '绯色命运', 30000, '#FF6666', 3),
    _solid('born-dreaming', '梦想天生', 30000, '#FF0000', 3),
    _solid('fantasy', '~幻想~', 15000, '#FF92C9', 3),
    _solid('swordsmith', '铸剑者', 15000, '#FF9933', 10),
    _solid('refuse-death', '赖着不死', 20000, '#D28A2B', 10),
    _styled(
        'you-cannot-beat-me',
        '你打不过我你信吗',
        40000,
        '{gradient:90deg,#644011>#FFEF00}你打不过我你信吗{/}',
        1,
    ),
    _styled(
        'strong',
        '弓虽虽弓',
        15000,
        '{color:#CC0000|id=left}弓虽{/}{color:#00CC00|id=right}虽弓{/}',
        3,
    ),
    _solid('skilled', '熟练入', 30000, RARITY_COLORS['ultra'], 3),
    _solid('superman', '苏泊尔曼', 30000, RARITY_COLORS['super'], 3),
    _styled(
        'moody',
        '情绪多变',
        25000,
        '{color:#0000CC|id=left}情绪{/}{color:#FF0000|id=right}多变{/}',
        10,
    ),
    _solid('divinity', '神格', 25000, '#B266FF', 10),
    _solid('tiger-descends', '猛虎下山', 15000, '#FF8000', 10),
    _solid('creative-ai', '创造性AI', 15000, '#FFFF00', 10),
    _styled(
        'momyx-theme',
        'Momyx',
        500,
        '{theme:light=#FFFFFF;dark=#000000}Momyx{/}',
        20,
    ),
    _solid('momyx-black', 'Momyx', 15000, '#000000', 20),
    _solid('grand-finale', '华丽收场', 20000, '#00FF80', 10),
    _solid('seven-colors-red', '赤橙黄绿青蓝紫', 5000, '#FF0000', 5),
    _solid('seven-colors-orange', '赤橙黄绿青蓝紫', 5000, '#FF8000', 5),
    _solid('seven-colors-yellow', '赤橙黄绿青蓝紫', 5000, '#FFFF00', 5),
    _solid('seven-colors-green', '赤橙黄绿青蓝紫', 5000, '#00CC00', 5),
    _solid('seven-colors-cyan', '赤橙黄绿青蓝紫', 5000, '#00B7C7', 5),
    _solid('seven-colors-blue', '赤橙黄绿青蓝紫', 5000, '#3478F6', 5),
    _solid('seven-colors-purple', '赤橙黄绿青蓝紫', 5000, '#861FDE', 5),
    _styled('rainbow', '彩虹', 25000, '{rainbow}彩虹{/}', 5),
    _solid('cannot-hold', '绷不住', 10000, '#E6DF7F', 20),
    _solid('newcomer', '新手', 1000, RARITY_COLORS['unusual'], 30),
    _solid('dealer', '发牌员', 20000, '#000000', 20),
]


for _index, (_key, _color) in enumerate(RARITY_COLORS.items()):
    TITLE_SHOP_CATALOG.append(
        _solid(f'zorr-{_key}', _key.capitalize(), 5000 + _index * 5000, _color, 20)
    )
