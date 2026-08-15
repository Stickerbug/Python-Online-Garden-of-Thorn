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
    _solid('spectator', '观战', 30000, 'spectator', 20),
    _solid('thunder-god', '雷神', 50000, RARITY_COLORS['unique'], 20),
    _solid('marker-super', 'Marker', 40000, RARITY_COLORS['super'], 10),
    _solid('marker-common', 'Marker', 10000, RARITY_COLORS['common'], 10),
    _solid('warlock', '邪术师', 50000, RARITY_COLORS['epic'], 20),
    _solid('summoner', '召唤师', 50000, '#FF99CC', 20),
    _solid('orbital-warrior', '轨道战士', 50000, '#99CCFF', 20),
    _solid('ordinary-flower', '普通的花花', 50000, RARITY_COLORS['unusual'], 20),
    _solid('started', '我已启动', 20000, RARITY_COLORS['mythic'], 10),
    _solid('wait-start', '等我启动', 5000, '#B2B641', 10),
    _solid('no-juice-handsome', '没汁帅', 20000, RARITY_COLORS['epic'], 10),
    _solid('mere', '区区', 10000, '#B2B641', 10),
    _solid('great-mathematician', '大数学家', 20000, '#C0C0C0', 10),
    _solid('rafflesia', '大王花', 20000, '#FF6666', 10),
    _solid('question-flower', '?!花花!?', 100, RARITY_COLORS['unusual'], 100),
    _solid('old-mage', '老法师', 50000, RARITY_COLORS['mythic'], 10),
    _solid('old-priest', '老牧师', 50000, '#FFFF00', 10),
    _solid('machine-master', '机械大师', 50000, '#A56C09', 10),
    _solid('exchange-no-juice', '兑没汁帅', 40000, RARITY_COLORS['ultra'], 10),
    _solid('enabled', '开了', 30000, '#000000', 10),
    _solid('lol-thorn', 'lol', 15000, '#C0392B', 5),
    _solid('lol-bloom', 'lol', 15000, '#1ABC9C', 5),
    _solid('lol-root', 'lol', 15000, '#8D6E63', 5),
    _solid('lol-guard', 'lol', 15000, '#2980B9', 5),
    _solid('hungry', '我饥饿', 10000, '#660066', 10),
    _solid('cognitive-bias', '认知偏差', 40000, '#33FFFF', 10),
    _solid('echo-form', '回响形态形响回', 40000, '#CCCC00', 10),
    _solid('click-form', '咔咔形态', 40000, '#FF8000', 10),
    _solid('infinite', '我已无限', 60000, '#4C9900', 10),
    _solid('corruption', '腐化', 50000, '#CC0000', 10),
    _solid('five-equals-one', '5=1', 50000, RARITY_COLORS['super'], 20),
    _solid('dark-mercenary', '黑暗之佣', 30000, '#000000', 10),
    _solid('take-good-cards', '好牌多抓', 20000, '#C0392B', 10),
    _solid('take-every-card', '见牌就抓', 20000, '#1ABC9C', 10),
    _solid('avoid-big-monsters', '避战大怪', 20000, '#2980B9', 10),
    _solid('cowards-defend', '懦夫才防', 20000, '#8D6E63', 10),
    _solid('perfect-style', '完美潇洒', 60000, '#E0E0E0', 3),
    _solid('scarlet-destiny', '绯色命运', 60000, '#FF6666', 3),
    _solid('born-dreaming', '梦想天生', 60000, '#FF0000', 3),
    _solid('fantasy', '~幻想~', 30000, '#FF92C9', 3),
    _solid('swordsmith', '铸剑者', 30000, '#FF9933', 10),
    _solid('refuse-death', '赖着不死', 40000, '#D28A2B', 10),
    _styled(
        'you-cannot-beat-me',
        '你打不过我你信吗',
        80000,
        '{gradient:90deg,#644011>#FFEF00}你打不过我你信吗{/}',
        1,
    ),
    _styled(
        'strong',
        '弓虽虽弓',
        30000,
        '{color:#CC0000|id=left}弓虽{/}{color:#00CC00|id=right}虽弓{/}',
        3,
    ),
    _solid('skilled', '熟练入', 60000, RARITY_COLORS['ultra'], 3),
    _solid('superman', '苏泊尔曼', 60000, RARITY_COLORS['super'], 3),
    _styled(
        'moody',
        '情绪多变',
        50000,
        '{color:#0000CC|id=left}情绪{/}{color:#FF0000|id=right}多变{/}',
        10,
    ),
    _solid('divinity', '神格', 50000, '#B266FF', 10),
    _solid('tiger-descends', '猛虎下山', 30000, '#FF8000', 10),
    _solid('creative-ai', '创造性AI', 30000, '#FFFF00', 10),
    _styled(
        'momyx-theme',
        'Momyx',
        1000,
        '{theme:light=#FFFFFF;dark=#000000}Momyx{/}',
        20,
    ),
    _solid('momyx-black', 'Momyx', 30000, '#000000', 20),
    _solid('grand-finale', '华丽收场', 40000, '#00FF80', 10),
    _solid('seven-colors-red', '赤橙黄绿青蓝紫', 10000, '#FF0000', 5),
    _solid('seven-colors-orange', '赤橙黄绿青蓝紫', 10000, '#FF8000', 5),
    _solid('seven-colors-yellow', '赤橙黄绿青蓝紫', 10000, '#FFFF00', 5),
    _solid('seven-colors-green', '赤橙黄绿青蓝紫', 10000, '#00CC00', 5),
    _solid('seven-colors-cyan', '赤橙黄绿青蓝紫', 10000, '#00B7C7', 5),
    _solid('seven-colors-blue', '赤橙黄绿青蓝紫', 10000, '#3478F6', 5),
    _solid('seven-colors-purple', '赤橙黄绿青蓝紫', 10000, '#861FDE', 5),
    _styled('rainbow', '彩虹', 50000, '{rainbow}彩虹{/}', 5),
    _solid('cannot-hold', '绷不住', 20000, '#E6DF7F', 20),
    _solid('newcomer', '新手', 2000, RARITY_COLORS['unusual'], 30),
]


for _index, (_key, _color) in enumerate(RARITY_COLORS.items()):
    TITLE_SHOP_CATALOG.append(
        _solid(f'zorr-{_key}', _key.capitalize(), 5000 + _index * 5000, _color, 20)
    )
