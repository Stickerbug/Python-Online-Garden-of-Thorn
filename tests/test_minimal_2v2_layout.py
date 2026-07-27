from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
STYLE = (ROOT / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')


def css_blocks(selector):
    pattern = re.compile(rf'{re.escape(selector)}\s*\{{([^}}]*)\}}')
    return [match.group(1) for match in pattern.finditer(STYLE)]


def has_declarations(selector, *declarations):
    return any(
        all(declaration in block for declaration in declarations)
        for block in css_blocks(selector)
    )


def test_opponent_hand_and_equipment_share_the_top_edge():
    assert has_declarations('.opp-hand-equip', 'align-items: flex-start;')
    assert has_declarations('.opp-hand-row', 'align-self: flex-start;')
    assert has_declarations('.equip-row', 'align-self: flex-start;')


def test_2v2_equipment_wraps_inside_its_own_column():
    assert has_declarations(
        '.game-container.mode-2v2 .opp-hand-equip',
        'flex-wrap: nowrap;',
        'align-items: flex-start;',
    )
    assert has_declarations(
        '.game-container.mode-2v2 .opp-hand-row',
        'flex: 1 1 auto;',
        'overflow-x: auto;',
    )
    assert has_declarations(
        '.game-container.mode-2v2 .opp-hand-equip > .equip-row',
        'max-width: 48%;',
        'overflow-y: auto;',
    )
