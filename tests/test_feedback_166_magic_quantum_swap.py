"""反馈 #166：魔法量子（temporary_swap_costs）在客户端也要真的换费用。

引擎的 ``_card_values`` 会把 E/M 消耗互换，但客户端 ``cardValues`` 只处理了
cost_e_delta / swift / temporary_free_e 等，漏了 temporary_swap_costs 与
temporary_cost_m_delta，于是牌面、资源预览都还是旧费用，玩家看到的就是
「魔法量子没有作用」。
"""

import json
import shutil
import subprocess
from pathlib import Path

from story_content import STORY_CARDS
from story_engine import _card_values

ROOT = Path(__file__).resolve().parents[1]
STORY_JS = (ROOT / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')


def _client_card_values(card):
    """Run the shipped client ``cardValues`` in node with the real story content."""
    node = shutil.which('node')
    assert node, 'node is required for this behaviour test'
    start = STORY_JS.index('    function cardValues(card) {')
    end = STORY_JS.index('\n    }', start) + len('\n    }')
    helper = STORY_JS[start:end]
    cards = {
        key: STORY_CARDS[key]
        for key in ('mage_quantum', 'basic', 'rose', 'corruption')
        if key in STORY_CARDS
    }
    script = f'''
const storyContent = {{ cards: {json.dumps(cards, ensure_ascii=False)}, tags: {{ swift: {{}}, temporary_swift: {{}}, magic_swift: {{}}, temporary_heavy: {{}}, power: {{}}, charge: {{}} }}, relics: {{}} }};
{helper}
const card = {json.dumps(card, ensure_ascii=False)};
console.log(JSON.stringify(cardValues(card)));
'''
    result = subprocess.run(
        [node, '-e', script],
        capture_output=True,
        text=True,
        encoding='utf-8',
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip())


def _card(def_id, modifiers):
    return {
        'def_id': def_id,
        'instance_id': 'probe',
        'upgraded': False,
        'modifiers': modifiers,
    }


def test_magic_quantum_is_a_4m1e_swap_card():
    values = STORY_CARDS['mage_quantum']
    assert values['name']['zh'] == '魔法量子'
    assert [effect['type'] for effect in values['effects']] == ['temporary_swap_costs']
    assert values['cost_e'] == 2 and values['cost_m'] == 0


def test_engine_swaps_costs_for_the_whole_turn():
    values = _card_values(_card('basic', {'temporary_swap_costs': True}))
    base = STORY_CARDS['basic']
    assert base['cost_m'] or True  # 基本是 1E/0M，互换后应为 0E/1M
    assert (values['cost_e'], values['cost_m']) == (base['cost_m'], base['cost_e'])

    values = _card_values(_card('basic', {'temporary_cost_m_delta': 2}))
    assert values['cost_m'] == base['cost_m'] + 2


def test_client_matches_the_engine_for_swap_and_magic_heavy():
    for modifiers in (
        {'temporary_swap_costs': True},
        {'temporary_cost_m_delta': 2},
        {'temporary_swap_costs': True, 'temporary_cost_m_delta': 1},
        {'temporary_swap_costs': True, 'swift': 1},
    ):
        card = _card('basic', modifiers)
        engine_values = _card_values(card)
        client_values = _client_card_values(card)
        assert (client_values['cost_e'], client_values['cost_m']) == (
            int(engine_values['cost_e']),
            int(engine_values['cost_m']),
        ), modifiers
