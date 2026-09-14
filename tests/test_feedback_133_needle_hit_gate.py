"""反馈 #133：针「命中时施加无法反制」必须真的等命中，被闪避时不施加。"""

from pathlib import Path

from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]


def test_needle_status_effect_is_gated_by_hit():
    mod = load_mod(str(ROOT / 'mods' / 'Ocean Cards Addition.gtnmod'))
    assert not mod.errors, mod.errors
    needle = next(card for card in mod.cards if str(card.id) == 'Needle')

    steps = needle.v2_events['on_play']['steps']
    damage = next(step for step in steps if step.get('op') == 'deal_damage')
    gated = list(damage.get('on_hit_once') or []) + list(damage.get('on_hit') or [])

    assert any(
        step.get('op') == 'status_op' and step.get('status') == 'ocean:unable_counter'
        for step in gated
    ), '无法反制必须挂在命中回调里'
    assert not [
        step for step in steps if step.get('op') == 'status_op'
    ], '顶层不应再有未命中门控的状态步骤'
