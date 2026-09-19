"""反馈 #170：牌堆/弃牌/放逐的分组要按「实际显示出来的样子」算。

``cardChoiceIdentity`` 是选牌逻辑用的身份（包含持有回合、额外命中、费用覆盖、
拟态折扣等实例差异），拿它给牌堆分组会把看起来完全一样的牌拆成两条。
"""

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')


def test_pile_views_group_by_displayed_content():
    assert 'function cardPileDisplayIdentity(' in GAME_JS
    # 牌堆查看与开局牌堆展示都必须用显示身份分组
    assert GAME_JS.count('cardPileDisplayIdentity(') >= 3
    assert 'const key = cardPileDisplayIdentity(c, pilePlayer);' in GAME_JS
    assert 'const key = cardPileDisplayIdentity(card, targetState);' in GAME_JS
    # 分组键里不能再出现实例专用的记账字段
    display_identity = GAME_JS[
        GAME_JS.index('function cardPileDisplayIdentity('):
        GAME_JS.index('function cardPileDisplayIdentity(') + 900
    ]
    for instance_only in ('bonus_damage', 'held_turns', 'mimic_discount', 'setup_modifiers'):
        assert instance_only not in display_identity


def _run_node(script: str):
    node = shutil.which('node')
    assert node, 'node is required for this behaviour test'
    result = subprocess.run(
        [node, '-e', script],
        capture_output=True,
        text=True,
        encoding='utf-8',
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_display_identity_ignores_instance_only_differences():
    start = GAME_JS.index('function cardPileDisplayIdentity(')
    end = GAME_JS.index('\n}', start) + 2
    helper = GAME_JS[start:end]
    script = f'''
function getCardDef(defId) {{ return {{ id: defId, name_cn: defId }}; }}
function getUnknownCardDisplayDef() {{ return null; }}
function getCardInstanceName(card) {{ return card.def_id; }}
function getCardDisplayCosts(card) {{ return {{ totalE: Number(card.cost_e || 0), totalM: 0 }}; }}
function getCardDisplayCostELabel(card, def, numeric) {{ return String(numeric); }}
function getCardArtUrl(card) {{ return card.image_url || ''; }}
function buildInstanceOnlyFlagHtml(card) {{ return (card.instance_flags || []).join(','); }}
{helper}
const base = {{ def_id: 'Basic', cost_e: 1 }};
const played = {{ ...base, held_turns: 3, bonus_damage: 2, mimic_discount: 1, setup_modifiers: ['x'] }};
const fused = {{ ...base, instance_flags: ['power'], cost_e: 2 }};
const other = {{ def_id: 'Bone', cost_e: 1 }};
console.log(JSON.stringify({{
    sameKey: cardPileDisplayIdentity(base) === cardPileDisplayIdentity(played),
    flagSplit: cardPileDisplayIdentity(base) !== cardPileDisplayIdentity(fused),
    defSplit: cardPileDisplayIdentity(base) !== cardPileDisplayIdentity(other),
}}));
'''
    payload = json.loads(_run_node(script))
    assert payload == {'sameKey': True, 'flagSplit': True, 'defSplit': True}
