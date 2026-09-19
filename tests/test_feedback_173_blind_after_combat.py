"""反馈 #173：战斗结束（奖励/结算）后不该继续被失明遮住牌库。"""

from pathlib import Path

from story_engine import _finish_combat, _start_combat, apply_story_action
from story_mode import build_initial_story_state

ROOT = Path(__file__).resolve().parents[1]
SEED = 'feedback-173-blind'


def _combat_state():
    state = build_initial_story_state(SEED)
    state, _ = apply_story_action(
        state,
        'start_journey',
        {'biome': 'garden', 'difficulty': 'normal'},
        SEED,
    )
    _start_combat(state, {'type': 'combat'}, SEED, [], encounter_override=[{'def_id': 'soldier_ant'}])
    state['combat']['opening_redraw_pending'] = False
    return state


def test_finish_combat_clears_blind():
    state = _combat_state()
    state['combat']['blind_active'] = True
    state['combat']['blind'] = 2

    _finish_combat(state, SEED, [])

    assert state['combat']['blind_active'] is False
    assert state['phase'] == 'reward'


def test_client_only_applies_blind_during_combat():
    source = (ROOT / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')
    assert (
        "const blindActive = Boolean(state?.phase === 'combat' && combat && combat.blind_active);"
        in source
    )
