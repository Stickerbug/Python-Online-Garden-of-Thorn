"""单人训练场：按模组折叠的卡牌目录（不再有模组设置，也不看启用状态）。

前端把顺手的牌池换成「全部已安装模组」的目录，服务端也必须按同一口径放行
（否则用娱乐模组的卡配牌会被判成「当前不可用」）。
"""

from pathlib import Path

import app
from cards import CARD_DEFS
from mod_loader import load_all_mods, mod_category

ROOT = Path(__file__).resolve().parents[1]
ENTER = 'Void Cards DLC.gtnmod'
ENTER_CARD = 'DVD'


def test_solo_loadout_ignores_mode_enabled_mods():
    all_mods = app._cached_official_solo_loadout([])
    assert ENTER_CARD in all_mods['allowed_card_ids']
    assert ENTER_CARD in CARD_DEFS

    only_addition = app._cached_official_solo_loadout([ENTER])
    assert ENTER_CARD not in only_addition['allowed_card_ids']

    mods = {mod.filename: mod for mod in load_all_mods()}
    assert mod_category(mods[ENTER]) == 'entertainment'


def test_solo_loadout_covers_every_installed_mod_card():
    loadout = app._cached_official_solo_loadout([])
    allowed = set(loadout['allowed_card_ids'])
    missing = [
        card.id
        for mod in load_all_mods()
        if not mod.errors
        for card in mod.cards
        if card.id in CARD_DEFS and card.id not in allowed
    ]
    assert missing == []


def test_training_ground_has_no_mod_settings_entry():
    html = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
    js = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
    assert 'btn-solo-mods' not in html
    assert "btn-solo-mods" not in js


def test_training_ground_card_browser_groups_by_mod():
    js = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
    assert 'function groupedSoloBrowserSections(query)' in js
    assert 'function appendSoloModSection(list, section, expanded, query)' in js
    assert 'getGalleryCardModMemberships(cd)' in js
    # 目录用「全部模组」的卡牌定义，而不是当前模式启用的那批
    assert 'function soloBrowserCardDefs()' in js
    assert 'return getGalleryCardDefs();' in js
    assert "(phase === 'gallery' || phase === 'solo_edit' || soloMode)" in js
    # 折叠头只显示模组名与数量
    assert 'solo-mod-header' in js
    assert 'solo-mod-caret' in js
    assert 'solo-mod-count' in js
    assert 'solo-mod-cards' in js


def test_training_ground_rows_open_term_guide():
    js = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
    assert 'attachTermIntroToCard(row, { def_id: defId });' in js
    assert 'attachTermIntroToCard(row, { def_id: card.def_id });' in js
    # 右键 = 术语说明（长按走同一条 onShow）
    assert "anchor.addEventListener('contextmenu', (event) => {" in js
    assert 'event.preventDefault();\n        event.stopPropagation();\n        cancel();' in js


def test_training_ground_accordion_styles_exist():
    css = (ROOT / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')
    for selector in (
        '.solo-mod-group',
        '.solo-mod-header',
        '.solo-mod-caret',
        '.solo-mod-name',
        '.solo-mod-count',
        '.solo-mod-cards',
        '.solo-card-empty',
    ):
        assert selector in css
