"""图鉴（include_all_mods）必须保留娱乐模组的卡牌来源信息。

回归：娱乐模组在当前模式被停用时，/api/cards 曾把这些模组整个从来源表里剔除，
前端拿不到 source_mod_* 字段，图鉴“娱乐”页的模组名全部显示为 unknown。
"""

import urllib.parse

import app


def _gallery_cards(disabled_mods):
    client = app.app.test_client()
    query = urllib.parse.urlencode({
        'include_all_mods': '1',
        'disabled_mods': ','.join(disabled_mods),
        'mod_source': 'official',
    })
    response = client.get('/api/cards?' + query)
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict) and payload
    return payload


def test_gallery_cards_keep_entertainment_mod_attribution():
    entertainment = sorted(app.entertainment_mod_filenames())
    assert entertainment, '安装的娱乐模组为空'
    cards = _gallery_cards(entertainment)

    broken = [
        card.get('id')
        for card in cards.values()
        if card.get('v2_mod_id') and not card.get('source_mod_filename')
    ]
    assert broken == []

    dlc_cards = [
        card for card in cards.values()
        if str(card.get('source_mod_filename') or '').endswith('.gtnmod')
    ]
    assert dlc_cards
    for card in dlc_cards:
        assert card.get('source_mod_name_cn') or card.get('source_mod_name_en'), card.get('id')
