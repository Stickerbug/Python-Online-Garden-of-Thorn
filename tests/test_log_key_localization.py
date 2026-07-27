from pathlib import Path

from cards import CardInstance
from game_engine import GameEngine


ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')


def test_add_tag_to_zone_log_uses_chinese_zone_and_tag_names():
    engine = GameEngine()
    engine.player_names = ['甲', '乙']
    source = CardInstance('Basic')
    engine.players[1].hand = [CardInstance('Basic'), CardInstance('Bone')]

    engine._atomic_add_tag_to_zone(
        0,
        source,
        {'target': 'enemy', 'zone': 'hand', 'tag': 'revealed'},
        None,
        None,
        {},
    )

    assert engine.log[-1] == '甲使乙手牌中的2张牌获得被揭示标签'
    assert all('revealed' not in line and 'hand区' not in line for line in engine.log)


def test_generic_tag_logs_use_builtin_and_custom_chinese_names():
    engine = GameEngine()
    card = CardInstance('Basic')
    engine.v2_tag_defs = {
        'test:custom_tag': {
            'id': 'test:custom_tag',
            'name_i18n': {'zh': '自定义标签', 'en': 'Custom Tag'},
        },
    }

    engine._atomic_add_tag(
        0,
        card,
        {'tag': 'symbiosis', 'card': {'ref': 'current_card'}},
        None,
        None,
        {},
    )
    engine._atomic_add_tag(
        0,
        card,
        {'tag': 'test:custom_tag', 'card': {'ref': 'current_card'}},
        None,
        None,
        {},
    )

    assert engine.log[-2].endswith('获得共生标签')
    assert engine.log[-1].endswith('获得自定义标签')


def test_magic_nazar_status_aliases_are_forced_to_the_core_localized_term():
    assert "raw === '魔法邪眼'" in GAME_JS
    assert "comparable === 'magic_nazar'" in GAME_JS
    assert "comparable.endsWith(':magic_nazar')" in GAME_JS
    assert "customDef && key !== 'magic_nazar'" in GAME_JS
    assert "customCount('magic_nazar', 'Magic Nazar', '魔法邪眼', 'vanilla:magic_nazar')" in GAME_JS
