from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _game_js():
    return (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')


def test_feedback_99_entertainment_checkbox_uses_saved_preference():
    js = _game_js()
    assert 'casualUnlockMode && !entertainment ? unlockedForMode : !disabled.includes(filename)' in js


def test_feedback_112_thorn_dew_reason_parses_all_multipliers():
    js = _game_js()
    assert r'const factorRe = /([^\s×]+)×([\d.]+)/g;' in js
    assert "'衰减': lt(" in js


def test_feedback_105_and_115_internal_flags_are_hidden():
    js = _game_js()
    assert "auto_play_no_queue: 'auto_play_no_queue'" in js
    assert 'const INTERNAL_CARD_FLAG_SET = new Set([' in js
    assert "'mark:'" in js
    assert 'isInternalCardFlag(normalized)' in js
    assert 'Object.keys(CARD_FLAG_STYLES).filter(flag => shouldDisplayCardFlag(flag, { showSystemFlags: false }))' in js


def test_feedback_108_trigger_target_follows_equipment_effect_target():
    js = _game_js()
    assert 'cardHasSelfOnlyFlag(cardInst || {}, cardDef)' not in js
    assert 'targetId = cardHasSelfOnlyFlag(cardInst, cardDef)' not in js
    assert js.count('equipmentTriggerUsesEffectTarget(cardDef)') >= 5


def test_feedback_114_flavor_text_skips_bare_terms():
    js = _game_js()
    assert 'colorizeCardText(descriptionText, { terms: false })' in js
    assert 'if (options.terms !== false) {' in js
