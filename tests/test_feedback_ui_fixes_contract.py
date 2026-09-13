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


def test_feedback_106_sapphire_asks_target_outside_2v2():
    js = _game_js()
    assert "if (['sapphire', 'ocean:sapphire'].includes(cardId)) {" in js
    assert "return gs.mode === '2v2';" in js


def test_feedback_102_card_data_follows_room_snapshot_and_unknown_ids_are_visible():
    js = _game_js()
    assert 'stateMods && (isSpectating || isPvpMatchFlowActive())' in js
    assert 'function getUnknownCardDisplayDef' in js
    assert 'cardDef.__unknown_card_def' in js


def test_feedback_118_minimal_hand_uses_measured_available_height():
    js = _game_js()
    assert 'function measureMinimalHandAvailableHeight' in js
    assert 'const minimumLogHeight = 110;' in js
    assert 'measureMinimalHandAvailableHeight(container, viewportHeight)' in js
    assert '        availableHeight,\n' in js


def test_feedback_126_spectate_controls_stay_clickable_when_pushed_out():
    js = _game_js()
    css = (ROOT / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')
    assert 'function refreshSpectateControlsPlacement' in js
    assert 'spectate-controls-floating' in js
    assert 'refreshSpectateControlsPlacement();' in js
    assert 'window.setTimeout(refreshSpectateControlsPlacement, 80);' in js
    assert '.game-container.mode-spectate #spectate-controls.spectate-controls-floating' in css
    assert '  position: fixed;' in css


def test_gallery_official_entertainment_tabs_show_enable_states():
    js = _game_js()
    css = (ROOT / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')
    assert 'function isGalleryVisibleCardDef' in js
    assert 'let galleryModTab' in js
    assert 'data-gallery-mod-tab="official"' in js
    assert 'data-gallery-mod-tab="entertainment"' in js
    assert 'gallery-mod-state-row' in js
    assert 'ensureGalleryModCategories' in js
    assert "getDisabledMods('casual_1v1')" in js
    assert "getDisabledMods('ranked_1v1')" in js
    assert 'filter(id => isGalleryVisibleCardDef(defs[id]))' in js
    assert '.gallery-mod-tabs' in css
    assert '.gallery-mod-state' in css


def test_solo_training_has_mod_settings_entry():
    js = _game_js()
    html = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
    assert 'id="btn-solo-mods"' in html
    assert 'soloMods' in html
    assert "$('btn-solo-mods')" in js
    assert 'openSettings({ hideServer: true });' in js
    assert "getVisibleViewId() === 'view-solo'" in js
    assert 'renderSoloBuilder();' in js


def test_feedback_114_flavor_text_skips_bare_terms():
    js = _game_js()
    assert 'colorizeCardText(descriptionText, { terms: false })' in js
    assert 'if (options.terms !== false) {' in js
