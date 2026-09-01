from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORY_JS = (ROOT / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')
STORY_CSS = (ROOT / 'static' / 'css' / 'story.css').read_text(encoding='utf-8')
STORY_ENGINE = (ROOT / 'story_engine.py').read_text(encoding='utf-8')
SHARED_AFK_CSS = (ROOT / 'static' / 'css' / 'shared-afk.css').read_text(encoding='utf-8')
STORY_TEMPLATE = (ROOT / 'templates' / 'story.html').read_text(encoding='utf-8')
INDEX_TEMPLATE = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
RESOURCE_ORBS_JS = (ROOT / 'static' / 'js' / 'resource_orbs.js').read_text(encoding='utf-8')
KEYBINDINGS_JS = (ROOT / 'static' / 'js' / 'keybindings.js').read_text(encoding='utf-8')


def test_story_damage_floats_describe_lost_health():
    player_branch = STORY_JS.split(
        "} else if (eventType === 'player_damage') {",
        1,
    )[1].split(
        "} else if (eventType === 'enemy_damage') {",
        1,
    )[0]
    enemy_branch = STORY_JS.split(
        "} else if (eventType === 'enemy_damage') {",
        1,
    )[1].split(
        "} else if (eventType === 'enemy_gain') {",
        1,
    )[0]

    assert 'event.amount) || 0)}H' in player_branch
    assert 'event.amount) || 0)}H' in enemy_branch
    assert 'event.amount) || 0)}D' not in player_branch
    assert 'event.amount) || 0)}D' not in enemy_branch


def test_story_lethal_enemy_damage_skips_hit_animation_before_defeat():
    presentation = STORY_JS.split(
        'async function playStoryPresentationEvent(event, nextRun) {',
        1,
    )[1].split(
        'async function playStoryEventSequence(events, nextRun, actionType) {',
        1,
    )[0]
    enemy_damage = presentation.split(
        "} else if (eventType === 'enemy_damage') {",
        1,
    )[1].split(
        "} else if (eventType === 'enemy_gain') {",
        1,
    )[0]

    assert 'event?.lethal === true' in enemy_damage
    assert 'Number(event.after) <= 0' in enemy_damage
    assert 'if (lethal)' in enemy_damage
    assert enemy_damage.index('if (lethal)') < enemy_damage.index("'is-taking-hit'")
    assert 'updateAnimatedEnemyHealth(event, nextRun);' in enemy_damage
    assert 'return;' in enemy_damage


def test_story_player_uses_classic_hurt_mouth_animation():
    assert 'STORY_SKIN_MOUTH_NORMAL_POINTS = Object.freeze([20, 18, 36, 32, 64, 32, 80, 18])' in STORY_JS
    assert 'STORY_SKIN_MOUTH_HURT_POINTS = Object.freeze([20, 26, 36, 12, 64, 12, 80, 26])' in STORY_JS
    assert 'const STORY_SKIN_DAMAGE_HOLD_MS = 3000;' in STORY_JS
    assert 'const duration = 360;' in STORY_JS

    player_branch = STORY_JS.split(
        "} else if (eventType === 'player_damage') {",
        1,
    )[1].split(
        "} else if (eventType === 'enemy_damage') {",
        1,
    )[0]
    assert 'if (Number(event.amount) > 0) triggerStoryPlayerDamageMood();' in player_branch
    assert "renderedAvatar?.classList.remove('skin-mouth-hurt');" in STORY_JS


def test_story_card_types_are_always_rendered_in_english():
    expected_labels = {
        'thorn': 'Thorn',
        'bloom': 'Bloom',
        'root': 'Root',
        'guard': 'Guard',
        'curse': 'Curse',
        'infect': 'Infect',
    }
    for card_type, label in expected_labels.items():
        assert f"{card_type}: '{label}'" in STORY_JS

    assert "typeLabel.textContent = blinded ? '?' : (STORY_CARD_TYPE_LABELS[cardType] || cardType);" in STORY_JS
    assert 'typeLabel.textContent = t.cardTypes?.[cardType] || cardType;' not in STORY_JS


def test_story_map_uses_supplied_icons_for_weighted_room_types():
    for room_type in ('combat', 'elite', 'event', 'rest', 'shop'):
        assert f"{room_type}: '/static/assets/story-room-icons/{room_type}.svg'" in STORY_JS
        assert (ROOT / 'static' / 'assets' / 'story-room-icons' / f'{room_type}.svg').is_file()
    assert "const nodeImageUrl = bossImageUrl || roomIconUrl;" in STORY_JS
    assert 'if (!roomIconUrl) {' in STORY_JS
    assert "bossImageUrl ? 'story-map-boss-icon' : 'story-map-room-icon'" in STORY_JS
    assert 'const nodeImageSize = bossImageUrl ? 40 : STORY_MAP_NODE_RADIUS * 2;' in STORY_JS
    assert '.story-map-room-icon {' in STORY_CSS
    assert '.story-map-node.is-actionable:hover .story-map-room-icon,' in STORY_CSS


def test_story_cards_use_gallery_spacing_tokens():
    assert '--card-effect-padding-y: 6cqi;' in STORY_CSS
    assert '--card-effect-padding-x: 2.5cqi;' in STORY_CSS
    assert '--card-effect-padding-y: 2.9cqi;' in STORY_CSS
    assert (
        'padding: var(--card-effect-padding-y) var(--card-effect-padding-x) '
        'var(--card-effect-padding-bottom, var(--card-effect-padding-y));'
    ) in STORY_CSS
    assert 'padding: 1.5cqi 3cqi 3cqi;' in STORY_CSS
    assert 'border-radius: var(--card-flag-radius);' in STORY_CSS


def test_story_attack_prediction_does_not_change_effect_scale_on_hover():
    assert "if (enablePrediction && cardType === 'thorn')" in STORY_JS
    assert "enablePrediction: true," in STORY_JS
    assert "element.classList.toggle('card-effect-fit-prediction'" not in STORY_JS
    assert "supportsPrediction ? ' supports-prediction' : ''" in STORY_JS
    assert '.card-bottom-zone.supports-prediction' in STORY_CSS
    assert 'font-size: calc(var(--card-effect-font-scale) * .92);' not in STORY_CSS


def test_story_card_effect_fit_keeps_a_readable_floor_and_limits_spacing_shrink():
    fit_branch = STORY_JS.split(
        'function fitStoryCardEffect(cardElement) {',
        1,
    )[1].split(
        'function scheduleStoryCardEffectFit(cardElement) {',
        1,
    )[0]

    assert 'const minimumReadableScale = 0.76;' in fit_branch
    assert 'const minimumSpacingScale = 0.9;' in fit_branch
    assert 'resetStoryCardEffectFit(effect);' in fit_branch
    assert "effect.style.removeProperty('font-size');" in STORY_JS
    assert 'const minimumScale = !overflowed && !predictionTooTall' in fit_branch
    assert 'scale = Math.max(minimumScale, nextScale);' in fit_branch


def test_story_card_typography_matches_gallery_primitives():
    assert "--card-english-font: 5.75cqi;" in STORY_CSS
    assert ":lang(zh) .story-card.card" in STORY_CSS
    assert "-webkit-text-size-adjust: none;" in STORY_CSS
    assert "--font-card: 'Kreadon Demi', 'Kreadon CJK', 'Kreadon', 'Microsoft YaHei', sans-serif;" in STORY_CSS
    assert "document.documentElement.lang = lang;" in STORY_JS


def test_story_rich_text_colors_icon_suffix_multipliers():
    assert r"\[\[icon:([DHEM])\]\]" in STORY_JS
    assert "multiplier.textContent = `×${match[5]}`;" in STORY_JS
    assert "token.append(multiplier);" in STORY_JS
    assert '.story-inline-token {' in STORY_CSS
    assert 'font-weight: 800;' in STORY_CSS


def test_story_event_card_references_render_as_interactive_chips():
    assert r'/\[\[card:([a-z0-9_-]+)\]\]/gi' in STORY_JS
    assert 'function createStoryInlineCardChip(defId)' in STORY_JS
    assert "chip.className = 'story-event-card-chip';" in STORY_JS
    assert 'storyCardElementData.set(chip, card);' in STORY_JS
    assert 'appendStoryRichText(description, options.description);' in STORY_JS
    assert 'appendStoryRichText(description, localize(option?.description));' in STORY_JS
    assert 'appendStoryRichText(item, result);' in STORY_JS
    assert '[[card:unrelenting]]' in STORY_ENGINE
    assert '[[card:fatigued]]' in STORY_ENGINE
    assert '.story-event-card-chip {' in STORY_CSS


def test_story_tiles_and_inline_chips_cover_every_story_card_type_color():
    for card_type in ('thorn', 'bloom', 'root', 'guard', 'curse', 'infect'):
        assert f"{card_type}: 'var(--{card_type})'" in STORY_JS
    assert "tile.style.setProperty('--tile-color', storyCardTypeColor(values.type));" in STORY_JS
    assert "chip.style.setProperty('--story-chip-color', storyCardTypeColor(values.type));" in STORY_JS
    assert '--curse: #704b87;' in STORY_CSS
    assert '--infect: #7e9638;' in STORY_CSS


def test_story_globally_suppresses_context_menu_and_opens_card_terms():
    context_menu_branch = STORY_JS.split(
        "document.addEventListener('contextmenu', (event) => {",
        1,
    )[1].split(
        '});',
        1,
    )[0]
    assert 'event.preventDefault();' in context_menu_branch
    assert "'.story-card.card, .story-pile-tile, .story-event-card-chip'," in context_menu_branch
    assert 'openStoryCardTermsFromElement(cardSourceElement' in context_menu_branch
    assert 'story-card-terms-modal' in STORY_CSS
    assert '<dialog id="story-term-dialog" class="story-term-dialog">' in STORY_TEMPLATE
    assert 'if (!dialog.open) dialog.showModal();' in STORY_JS


def test_story_status_icons_open_term_descriptions():
    assert 'function openStoryStatusTerms(statusKey)' in STORY_JS
    assert 'function attachStoryStatusTermAccess(element, statusKey)' in STORY_JS
    assert 'element.dataset.storyStatusKey = String(statusKey);' in STORY_JS
    assert 'attachStoryStatusTermAccess(chip, item.key);' in STORY_JS
    assert "event.target?.closest?.('[data-story-status-key]')" in STORY_JS
    assert 'openStoryStatusTerms(statusElement.dataset.storyStatusKey);' in STORY_JS
    assert "definition.category === 'action'" in STORY_JS
    assert 't.actionTerms' in STORY_JS
    assert ': t.statusTerms;' in STORY_JS
    assert "kind: 'status'," in STORY_JS
    assert "item.kind === 'trait'" in STORY_JS
    assert 'storyStatusIconUrl(item.id);' in STORY_JS
    assert '.story-status-terms-layout {' in STORY_CSS
    assert '.story-status-terms-icon img {' in STORY_CSS


def test_story_talents_show_their_copy_without_redundant_term_interactions():
    assert 'function renderStoryCodexTalentDetail(record, detail)' in STORY_JS
    assert 'appendStoryRichText(description, localize(record.definition.description));' in STORY_JS
    assert 'function openStoryRelicTerms(relicKey)' not in STORY_JS
    assert 'function attachStoryRelicTermAccess(element, relicKey)' not in STORY_JS
    assert "event.target?.closest?.('[data-story-relic-key]')" not in STORY_JS
    assert "attachStoryRelicTermAccess($('story-chest-relic-name')?.parentElement, room.relic);" not in STORY_JS
    assert 'if (options.relicKey) attachStoryRelicTermAccess(button, options.relicKey);' not in STORY_JS


def test_story_surrender_button_requires_confirmation_and_uses_action():
    assert 'id="story-surrender"' not in STORY_TEMPLATE
    assert 'id="story-settings-surrender"' not in STORY_TEMPLATE
    assert 'id="story-hud-surrender"' in STORY_TEMPLATE
    assert 'id="story-surrender-dialog"' in STORY_TEMPLATE
    assert "storyAction('surrender')" in STORY_JS
    assert "['journey_setup', 'complete', 'game_over'].includes(phase)" in STORY_JS
    assert "'story-surrender-confirm': t.surrender" in STORY_JS
    assert "$('story-hud-surrender')?.addEventListener('click'" in STORY_JS
    assert "dialog.returnValue = 'cancel';" in STORY_JS


def test_story_equipment_matches_classic_orbit_preview_and_terms():
    assert "visual.className = 'story-equipment-visual';" in STORY_JS
    assert "icon.className = 'story-equipment-icon';" in STORY_JS
    assert "image.className = 'story-equipment-image';" in STORY_JS
    assert "item.style.setProperty('--story-equipment-orbit-delay'" in STORY_JS
    assert "item.style.setProperty('--story-equipment-spin-delay'" in STORY_JS
    assert 'storyCardElementData.set(item, card);' in STORY_JS
    assert 'attachStoryEquipmentPreview(item, card);' in STORY_JS
    assert "event.target?.closest?.('.story-equipment')" in STORY_JS
    assert 'animation: storyEquipmentOrbit 20s linear infinite;' in STORY_CSS
    assert 'animation: storyEquipmentCounterOrbit 20s linear infinite;' in STORY_CSS
    assert 'animation: storyEquipmentIconSpin 17.333s linear infinite;' in STORY_CSS
    assert '.story-equipment-preview {' in STORY_CSS
    assert '.story-equipment-preview .story-card.card {' in STORY_CSS
    preview_rule = STORY_CSS.split('.story-equipment-preview {', 1)[1].split('}', 1)[0]
    preview_card_rule = STORY_CSS.split(
        '.story-equipment-preview .story-card.card {',
        1,
    )[1].split('}', 1)[0]
    assert 'width: min(136px, 31vw);' in preview_rule
    assert 'width: 100%;' in preview_card_rule
    assert 'min-width: 0;' in preview_card_rule


def test_story_patch_traits_and_gold_icon_are_visible_ui_assets():
    assert 'function renderTraitsInto(container, traitIds, actor = null)' in STORY_JS
    assert 'const STORY_TRAIT_VALUE_KEYS_FALLBACK = Object.freeze({' in STORY_JS
    assert 'const configured = storyContent?.trait_value_keys;' in STORY_JS
    assert "sturdy: 'sturdy'" in STORY_JS
    assert 'function createStoryTraitChip(traitKey, rawAmount = 0, isStatic = false)' in STORY_JS
    assert 'if (Number(actor?.[effectKey]) > 0 && storyTraitDefinition(traitKey))' in STORY_JS
    assert 'visibleTraitKeys.add(traitKey);' in STORY_JS
    assert 'const traitKey = storyTraitKeyForEffectKey(key);' in STORY_JS
    assert 'traitKey ? createStoryTraitChip(traitKey, amount) : null' in STORY_JS
    assert 'function openStoryTraitTerms(traitKey)' in STORY_JS
    assert 'attachStoryTraitTermAccess(chip, key);' in STORY_JS
    assert 'renderTraitsInto(effects, definition.traits, enemy);' in STORY_JS
    assert "event.target?.closest?.('[data-story-trait-key]')" in STORY_JS
    assert '.story-effect.story-trait {' in STORY_CSS
    assert '.story-term-row-trait {' in STORY_CSS


def test_bandage_beetle_uses_the_bandage_trait_instead_of_yggdrasil():
    assert "bandage: 'bandage'" in STORY_JS
    assert "actor?.def_id === 'bandage_beetle'" not in STORY_JS
    assert 'bandage_triggered || Number(actor?.bandage || 0) <= 0' not in STORY_JS
    assert "key === 'miracle' || key === 'bandage'" in STORY_JS
    gold_url = '/static/assets/story-ui-icons/gold.svg'
    assert gold_url in STORY_TEMPLATE
    assert gold_url in STORY_CSS
    assert "setText('story-shop-mark'" not in STORY_JS
    assert (ROOT / gold_url.removeprefix('/')).is_file()


def test_story_cards_do_not_open_enlarged_hover_previews_and_keep_optional_borders():
    assert 'function showStoryCardHoverPreview(anchor, card)' not in STORY_JS
    assert 'function attachStoryCardHoverPreview(anchor, getCard)' not in STORY_JS
    assert "preview.className = 'story-card-hover-preview';" not in STORY_JS
    assert '.story-card-hover-preview {' not in STORY_CSS
    assert 'Number(card?.modifiers?.charge)' in STORY_JS
    assert "storyTagElement('charge')" in STORY_JS
    assert '.story-hide-card-borders .story-card.card::after {' in STORY_CSS
    assert 'gtn_story_hide_card_borders' in STORY_TEMPLATE
    assert 'gtn_story_hide_card_borders' in INDEX_TEMPLATE
    assert 'settings-story-hide-card-borders' in INDEX_TEMPLATE


def test_story_status_scale_difficulty_labels_and_reward_escape_are_visible():
    status_rule = STORY_CSS.split('.story-effect.story-status {', 1)[1].split('}', 1)[0]
    status_image_rule = STORY_CSS.split('.story-effect.story-status img {', 1)[1].split('}', 1)[0]
    assert 'width: 46.5px;' in status_rule
    assert 'height: 46.5px;' in status_rule
    assert 'width: 34.5px;' in status_image_rule
    assert 'height: 34.5px;' in status_image_rule
    assert "const englishName = String(definition.name?.en || '').trim();" in STORY_JS
    assert '? `${localizedName} ${englishName}`' in STORY_JS
    assert "option: 'claim_gold'" in STORY_JS
    assert "option: 'claim_relic'" in STORY_JS
    assert "option: 'leave'" in STORY_JS
    assert "reward_type: 'leave'" in STORY_JS
    assert 'id="story-reward-leave"' in STORY_TEMPLATE


def test_story_cross_browser_baseline_preserves_cjk_bold_and_disables_button_drift():
    assert '-webkit-text-size-adjust: 100%;' in STORY_CSS
    assert 'text-size-adjust: 100%;' in STORY_CSS
    assert 'font-synthesis: none;' not in STORY_CSS
    assert '-webkit-appearance: none;' in STORY_CSS
    assert 'appearance: none;' in STORY_CSS
    assert '--gtn-card-border-width: clamp(1px, 1.3cqi, 1.7px);' in STORY_CSS


def test_story_modals_use_normal_mode_motion_and_readable_term_layout():
    assert '.story-dialog[open] {' in STORY_CSS
    assert '#modal.active .modal-inner {' in STORY_CSS
    assert '#story-term-dialog[open] .story-card-terms-modal {' in STORY_CSS
    assert '.story-dev-panel:not(.hidden) {' in STORY_CSS
    assert '@keyframes storyModalPopIn {' in STORY_CSS
    assert '@keyframes storyPanelDropIn {' in STORY_CSS
    assert 'width: min(920px, calc(100vw - 32px));' in STORY_CSS
    assert 'grid-template-columns: 220px minmax(0, 1fr);' in STORY_CSS
    assert 'border-left: 4px solid var(--story-blue);' in STORY_CSS
    assert '#story-term-dialog[open] .story-card-terms-modal,' in STORY_CSS


def test_story_surface_blocks_accidental_selection_and_native_image_dragging():
    assert '.story-app {' in STORY_CSS
    assert '-webkit-user-select: none;' in STORY_CSS
    assert 'user-select: none;' in STORY_CSS
    assert ".story-app [contenteditable='true'] {" in STORY_CSS
    assert '-webkit-user-select: text;' in STORY_CSS
    assert 'user-select: text;' in STORY_CSS
    assert '.story-app img {' in STORY_CSS
    assert '-webkit-user-drag: none;' in STORY_CSS
    assert "storyApp?.addEventListener('selectstart'" in STORY_JS
    assert "'input, textarea, select, [contenteditable=\"true\"]'" in STORY_JS
    assert "storyApp?.addEventListener('dragstart'" in STORY_JS
    assert "event.target?.closest?.('img')" in STORY_JS


def test_story_card_terms_switch_between_base_and_upgraded_versions():
    assert 'function storyCardHasUpgrade(card)' in STORY_JS
    assert 'function storyCardAtUpgradeState(card, upgraded)' in STORY_JS
    assert 'renderVersion(Boolean(card.upgraded));' in STORY_JS
    assert "{ upgraded: false, label: t.beforeUpgrade }" in STORY_JS
    assert "{ upgraded: true, label: t.afterUpgrade }" in STORY_JS
    assert "tab.setAttribute('aria-selected', active ? 'true' : 'false');" in STORY_JS
    assert 'const termItems = storyCardTermItems(displayCard);' in STORY_JS
    assert '.story-card-version-tabs {' in STORY_CSS
    assert '.story-card-version-tab.is-active {' in STORY_CSS


def test_enlarged_story_cards_can_switch_with_buttons_wheel_keys_and_swipes():
    assert 'function storyCardTermNavigationFromElement(sourceElement, options = {})' in STORY_JS
    assert 'function navigateStoryCardTerms(direction, options = {})' in STORY_JS
    assert "previous.dataset.storyCardNavDirection = 'previous';" in STORY_JS
    assert "next.dataset.storyCardNavDirection = 'next';" in STORY_JS
    assert "position.setAttribute('aria-live', 'polite');" in STORY_JS
    assert "addEventListener('wheel', handleStoryCardTermWheel, { passive: false })" in STORY_JS
    assert "event.key !== 'ArrowLeft' && event.key !== 'ArrowRight'" in STORY_JS
    assert "'.story-card-version-tabs, input, textarea, select, [contenteditable=\"true\"]'" in STORY_JS
    assert "!['touch', 'pen'].includes(String(event.pointerType || ''))" in STORY_JS
    assert 'Math.abs(deltaX) < 42' in STORY_JS
    assert 'clearStoryCardTermNavigation();' in STORY_JS
    assert '.story-card-terms-preview-column {' in STORY_CSS
    assert 'touch-action: pan-y;' in STORY_CSS
    assert '.story-card-terms-navigation {' in STORY_CSS
    assert '.story-card-terms-nav-button:focus-visible {' in STORY_CSS


def test_story_upgrade_actions_preview_the_upgraded_card_on_hover():
    assert "if (!blinded && options.previewUpgradeOnHover && storyCardIsUpgradable(card))" in STORY_JS
    assert "element.addEventListener('pointerenter'" in STORY_JS
    assert "element.addEventListener('pointerleave'" in STORY_JS
    assert STORY_JS.count('previewUpgradeOnHover: true,') >= 3


def test_story_room_actions_are_separated_into_tabs():
    assert 'id="story-room-tabs"' in STORY_TEMPLATE
    assert 'id="story-room-footer"' in STORY_TEMPLATE
    assert 'function renderStoryRoomTabs(state, definitions)' in STORY_JS
    for tab_id in (
        'rest-heal',
        'rest-upgrade',
        'shop-cards',
        'shop-talents',
        'shop-remove',
        'shop-upgrade',
        'event-actions',
        'event-upgrade',
    ):
        assert f"id: '{tab_id}'" in STORY_JS
    assert 'activeStoryRoomTabKey !== key' in STORY_JS
    assert "button.setAttribute('aria-selected', active ? 'true' : 'false');" in STORY_JS
    assert '.story-room-tabs {' in STORY_CSS
    assert '#story-room-options.story-room-card-grid {' in STORY_CSS
    assert '.story-room-footer:empty {' in STORY_CSS


def test_story_upgrade_tabs_only_show_cards_with_an_upgrade():
    assert "const upgradableCards = (player.deck || [])" in STORY_JS
    assert ".filter((card) => storyCardIsUpgradable(card));" in STORY_JS
    assert STORY_JS.count('appendStoryRoomEmpty(target, t.noUpgradableCards);') == 3


def test_story_equipment_orbits_around_player_portrait():
    avatar_stack = '''<div class="story-avatar-stack">
              <div id="story-player-portrait" class="story-portrait story-player-portrait player-avatar has-skin" aria-label="玩家"></div>
              <div id="story-player-equipment" class="story-equipment-list" aria-label="装备"></div>
            </div>'''

    assert avatar_stack in STORY_TEMPLATE
    assert '.story-avatar-stack {' in STORY_CSS
    assert 'width: var(--story-avatar-width);' in STORY_CSS
    assert '.story-avatar-stack:hover .story-equipment,' in STORY_CSS
    assert '.story-actor-player:hover .story-equipment' not in STORY_CSS


def test_story_player_eyes_follow_the_pointer():
    assert 'function updateStorySkinEyeTracking(clientX, clientY)' in STORY_JS
    assert "'--skin-look-x'," in STORY_JS
    assert "'--skin-look-y'," in STORY_JS
    assert 'updateStorySkinEyeTracking(event.clientX, event.clientY);' in STORY_JS
    assert 'transition: transform 300ms cubic-bezier(.22, .8, .24, 1);' in STORY_CSS


def test_story_shortcut_slots_follow_visual_order_and_active_dialog():
    visibility = STORY_JS.split(
        'function storyElementRendered(element) {',
        1,
    )[1].split(
        'function clearStoryKeyboardFocus() {',
        1,
    )[0]
    selection = STORY_JS.split(
        'function storySelectSlot(slot, options = {}) {',
        1,
    )[1].split(
        'function toggleStoryPile(kind) {',
        1,
    )[0]
    context = STORY_JS.split(
        'function getStoryShortcutContext() {',
        1,
    )[1].split(
        'function dispatchStoryShortcut(',
        1,
    )[0]

    assert 'return storyElementRendered(element) && !element.disabled;' in visibility
    assert 'const dialog = topmostStoryDialog();' in visibility
    assert 'const context = getStoryShortcutContext();' in selection
    assert 'const items = Array.isArray(context?.slots) ? context.slots : [];' in selection
    assert '#story-hand .story-card:not(:disabled)' not in selection
    assert "'.story-card-choice-select-item'," in context
    assert '].filter(storyElementRendered);' in context
    assert "'#story-hand .story-card'," in context
    selected_target_branch = context.split(
        'if (card && !storyCursorCardMode(card)) {',
        1,
    )[0]
    assert 'context.slots = hand.slice(0, 20);' in selected_target_branch
    assert "context.slotLabel = t.hand || '手牌';" in selected_target_branch


def test_story_right_click_cancels_selection_before_opening_terms():
    context_menu = STORY_JS.split(
        "document.addEventListener('contextmenu', (event) => {",
    )[-1].split(
        '});',
        1,
    )[0]

    cancel_check = "if (selectedCombatCardId && activeRun?.state) {"
    card_lookup = 'const cardElement = event.target?.closest?.('
    assert cancel_check in context_menu
    assert 'event.stopImmediatePropagation();' in context_menu
    assert 'cancelStoryCombatSelection(true);' in context_menu
    assert context_menu.index(cancel_check) < context_menu.index(card_lookup)


def test_story_presence_and_status_surfaces_are_wired():
    assert 'class="story-header"' not in STORY_TEMPLATE
    assert 'id="story-back"' in STORY_TEMPLATE
    assert 'id="story-chat-toggle"' in STORY_TEMPLATE
    assert 'id="story-status-bar"' in STORY_TEMPLATE
    assert 'id="story-status-text"' in STORY_TEMPLATE
    assert 'id="story-status-online"' in STORY_TEMPLATE
    assert 'class="story-account"' not in STORY_TEMPLATE
    assert 'id="story-account-label"' not in STORY_TEMPLATE
    assert 'class="story-status-center"' in STORY_TEMPLATE
    assert 'id="story-dev-toggle"' in STORY_TEMPLATE.split(
        '<footer id="story-status-bar"',
        1,
    )[1]
    assert "requestJson('/api/story/presence'" in STORY_JS
    assert 'activity: reportActivity' in STORY_JS
    assert 'Number(payload.story_online_count)' in STORY_JS
    assert '!payload.afk_check && Number.isFinite(nextCheckSeconds)' in STORY_JS
    assert 'startStoryPresence();' in STORY_JS
    assert 'function updateStoryStatusBar()' in STORY_JS
    assert 'grid-template-rows: minmax(0, 1fr) 32px;' in STORY_CSS
    assert '.story-status-bar {' in STORY_CSS
    assert 'background: rgba(0, 0, 0, .05);' in STORY_CSS


def test_story_initial_load_retries_transient_failures_without_retrying_actions():
    assert 'async function requestStoryLoadJson(url)' in STORY_JS
    assert "requestStoryLoadJson('/api/story/content')" in STORY_JS
    assert "requestStoryLoadJson('/api/story/run')" in STORY_JS
    assert 'const retryDelays = [350, 1000];' in STORY_JS
    assert '[408, 429, 502, 503, 504].includes(Number(error.status))' in STORY_JS
    assert "requestJson('/api/story/run/action'" in STORY_JS


def test_story_exit_glyph_is_visually_centered_in_its_button():
    glyph_rule = STORY_CSS.split('.story-exit-glyph {', 1)[1].split('}', 1)[0]
    assert 'position: relative;' in glyph_rule
    assert 'left: 2.8px;' in glyph_rule
    assert 'transform: rotate(45deg);' in glyph_rule


def test_story_enemy_group_enlarges_only_portraits_and_compacts_layout():
    assert "Math.max(.48, Math.min(.82, 1.03 - count * .13))" in STORY_JS
    assert "group.classList.toggle('has-multiple-enemies', count > 1);" in STORY_JS
    group_rule = STORY_CSS.split('.story-enemy-group {', 2)[2].split('}', 1)[0]
    actor_rule = STORY_CSS.split('.story-enemy-group .story-actor {', 1)[1].split('}', 1)[0]
    multi_actor_rule = STORY_CSS.split(
        '.story-enemy-group.has-multiple-enemies .story-actor {',
        1,
    )[1].split('}', 1)[0]
    assert 'gap: clamp(0px, .2vw, 3px);' in group_rule
    assert '--story-avatar-width: clamp(84px, 10vw, 152px);' in actor_rule
    assert '--story-avatar-width: clamp(94px, 11.2vw, 170px);' in multi_actor_rule
    assert '--story-fighter-scale: var(--story-enemy-scale, .82);' in actor_rule
    assert 'calc((var(--story-enemy-count) - 1) * -7px)' in actor_rule


def test_story_journey_setup_is_localized_and_centered():
    assert "journey_setup: '新旅程'" in STORY_JS
    assert "journey_setup: 'New Journey'" in STORY_JS
    assert "name: lang === 'zh' ? '标准旅程' : 'Standard Journey'" in STORY_JS
    assert "name: 'Boss Rush'" in STORY_JS
    assert "(room.modes || ['standard']).forEach((modeId) =>" in STORY_JS
    assert 'mode: selectedMode,' in STORY_JS
    assert '每轮依次经过赐福、3名首领、休息、宝箱与商店。' in STORY_JS
    assert 'Each loop follows Blessing, 3 Bosses, Rest, Chests, and Shop.' in STORY_JS
    assert "storyContent?.curses" not in STORY_JS
    assert "room.boss_rush || state.journey_mode === 'boss_rush'" in STORY_JS
    assert "container?.classList.add('is-journey-setup');" in STORY_JS
    assert "container.classList.remove('is-journey-setup');" in STORY_JS
    setup_rule = STORY_CSS.split(
        '.story-room-browser #story-room-options.is-journey-setup {',
        1,
    )[1].split('}', 1)[0]
    assert 'display: flex;' in setup_rule
    assert 'flex-wrap: wrap;' in setup_rule
    assert 'align-content: safe center;' in setup_rule
    assert 'justify-content: center;' in setup_rule
    assert '#story-room-options.is-journey-setup .story-choice-section-title {' in STORY_CSS
    option_rule = STORY_CSS.split(
        '#story-room-options.is-journey-setup .story-choice-option {',
        1,
    )[1].split('}', 1)[0]
    assert 'justify-items: center;' in option_rule
    assert 'text-align: center;' in option_rule


def test_story_chat_uses_the_shared_t_shortcut_as_a_safe_toggle():
    assert "const chatControl = storyChatOpen ? $('story-chat-input') : $('story-chat-toggle');" in STORY_JS
    assert "addStoryShortcutAction(context, 'focus_chat', [chatControl]);" in STORY_JS
    assert "case 'focus_chat': {" in STORY_JS
    assert 'if (storyChatOpen && input && document.activeElement === input) return false;' in STORY_JS
    assert 'setStoryChatOpen(!storyChatOpen);' in STORY_JS
    assert "defaultBinding: 'KeyT'" in (
        ROOT / 'static' / 'js' / 'keybindings.js'
    ).read_text(encoding='utf-8')


def test_story_afk_check_tracks_interaction_without_counting_heartbeats():
    assert "requestJson('/api/story/afk-check'" in STORY_JS
    assert 'function showStoryAfkCheckOverlay(data = {})' in STORY_JS
    assert 'function bindStoryAfkActivityReporting()' in STORY_JS
    assert "document.addEventListener('keydown', reportStoryAfkActivity" in STORY_JS
    assert "event?.target?.closest?.('#story-afk-check-overlay')" in STORY_JS
    assert 'client_id: STORY_PRESENCE_CLIENT_ID' in STORY_JS
    assert "overlay.className = 'afk-check-overlay';" in STORY_JS
    assert "class=\"afk-check-dialog\"" in STORY_JS
    assert "class=\"afk-check-button\"" in STORY_JS
    assert "classList.toggle('afk-check-ready'" in STORY_JS
    assert "classList.add('afk-check-holding')" in STORY_JS
    assert '.afk-check-overlay {' in SHARED_AFK_CSS
    assert '.afk-check-button.afk-check-ready {' in SHARED_AFK_CSS
    assert '/static/css/shared-afk.css' in STORY_TEMPLATE
    assert '/static/css/shared-afk.css' in INDEX_TEMPLATE


def test_story_surfaces_use_the_regular_ui_border_palette():
    assert '--story-line: #dcdcdc;' in STORY_CSS
    assert '--story-line-soft: #e0e0e0;' in STORY_CSS
    assert '--story-line: #3b4552;' in STORY_CSS
    assert '--story-line-soft: #4a5665;' in STORY_CSS
    assert 'border: 1px solid var(--story-line-soft);' in STORY_CSS
    assert '.story-afk-check-dialog' not in STORY_CSS


def test_story_run_deck_and_talents_remain_available_during_combat():
    assert 'id="story-run-deck"' not in STORY_TEMPLATE
    assert 'id="story-hud-deck"' in STORY_TEMPLATE
    assert 'src="/static/assets/ui-icons/total-pile.svg"' in STORY_TEMPLATE
    assert "runDeck: '总牌库', viewRunDeck: '查看总牌库'" in STORY_JS
    assert "deck: { source: state?.player?.deck, title: t.runDeck, reverse: false }" in STORY_JS
    assert "if (kind === 'deck' && state?.phase === 'combat') return;" not in STORY_JS
    assert "$('story-talent-overview')?.classList.toggle('hidden', runDeckUnavailable);" in STORY_JS
    assert "$('story-hud-deck')?.addEventListener('click', () => openStoryPile('deck'));" in STORY_JS
    assert 'storyPileCardGroups(cards).forEach(({ card, count }) =>' in STORY_JS
    assert 'grid?.append(createStoryPileTile(card, count));' in STORY_JS
    assert "if (key !== 'instance_id') result[key] = normalize(value[key]);" in STORY_JS
    assert "countLabel.textContent = `×${count}`;" in STORY_JS
    assert 'story-pile-order' not in STORY_JS
    assert '.story-pile-count {' in STORY_CSS
    assert '.story-run-deck-command {' in STORY_CSS


def test_story_talent_overview_sits_before_deck_and_is_self_explanatory():
    status_actions = STORY_TEMPLATE.split(
        '<div class="story-status-actions">',
        1,
    )[1].split(
        '</div>',
        1,
    )[0]
    assert 'id="story-talent-overview"' in status_actions
    assert 'id="story-run-deck"' not in status_actions
    assert STORY_TEMPLATE.index('id="story-hud-deck"') < STORY_TEMPLATE.index('id="story-talent-overview"')
    assert 'id="story-talent-overview-label"' in STORY_TEMPLATE
    assert '/static/assets/ui-icons/achievements.svg' in STORY_TEMPLATE
    assert 'function openStoryTalentOverview()' in STORY_JS
    assert 'state.player?.relics' in STORY_JS
    assert 'createStoryTalentOverviewItem(relicKey, index + 1, count)' in STORY_JS
    assert "const item = document.createElement('div');" in STORY_JS
    assert 'appendStoryRichText(description, localize(definition.description));' in STORY_JS
    assert 'attachStoryRelicTermAccess(item, key);' not in STORY_JS
    assert "$('story-talent-overview')?.addEventListener('click', openStoryTalentOverview);" in STORY_JS
    assert "grid?.classList.add('is-talents');" in STORY_JS
    assert '.story-pile-grid.is-talents {' in STORY_CSS
    assert '.story-talent-overview-item {' in STORY_CSS


def test_story_combat_map_is_read_only_and_can_return_to_combat():
    assert 'id="story-combat-map"' not in STORY_TEMPLATE
    assert 'id="story-map-return"' not in STORY_TEMPLATE
    assert 'id="story-hud-map"' in STORY_TEMPLATE
    assert '/static/assets/story-ui-icons/map.svg' in STORY_TEMPLATE
    assert 'const actionable = !options.readOnly && node.status === \'available\';' in STORY_JS
    assert 'renderMap(state.map, state.current_node_id, { readOnly: combatPreview });' in STORY_JS
    assert 'scheduleStoryAutoEnter' not in STORY_JS
    assert "$('story-hud-map')?.addEventListener('click', openStoryCombatMap);" in STORY_JS
    assert 'if (storyMapPreviewOpen)' in STORY_JS
    assert "mapButton?.classList.toggle('is-map-open', mapOpen);" in STORY_JS
    assert '.story-persistent-actions button.is-map-open {' in STORY_CSS


def test_story_map_boss_node_uses_the_frozen_encounter_portrait():
    assert "storyContent?.enemies?.[String(node.boss_def_id || '')]" in STORY_JS
    assert "bossImageUrl ? 'story-map-boss-icon' : 'story-map-room-icon'" in STORY_JS
    assert 'href: nodeImageUrl' in STORY_JS
    assert "bossName" in STORY_JS
    assert "text.textContent = t.roomMarks[node.type] || '?';" in STORY_JS
    assert '.story-map-boss-icon {' in STORY_CSS


def test_story_floor_restart_is_confirmed_and_available_after_combat_failure():
    assert 'id="story-save-open-global"' not in STORY_TEMPLATE
    assert 'id="story-settings-save"' not in STORY_TEMPLATE
    assert 'id="story-hud-save"' in STORY_TEMPLATE
    assert 'id="story-restart-floor"' in STORY_TEMPLATE
    assert 'id="story-restart-floor-dialog"' in STORY_TEMPLATE
    assert "await storyAction('restart_floor', {});" in STORY_JS
    assert "Boolean(state.floor_entry_checkpoint?.state)" in STORY_JS


def test_story_manual_save_delete_is_confirmed_and_refreshes_list():
    assert 'id="story-save-delete-dialog"' in STORY_TEMPLATE
    assert 'id="story-save-delete-confirm"' in STORY_TEMPLATE
    assert 'story-save-row-actions' in STORY_JS
    assert 'story-save-delete' in STORY_JS
    assert '/api/story/run/save/delete' in STORY_JS
    assert 'function deleteManualStorySave(saveId)' in STORY_JS
    assert 'renderManualStorySaves(payload.saves' in STORY_JS
    assert ".story-save-row-actions {" in STORY_CSS


def test_story_manual_saves_cover_every_committed_ui_phase_and_block_animations():
    for phase in (
        'journey_setup', 'easy_relic', 'blessing', 'map', 'combat',
        'room', 'reward', 'stage_choice', 'complete', 'game_over',
    ):
        assert f"'{phase}'" in STORY_JS.split(
            'const STORY_MANUAL_SAVE_STABLE_PHASES = new Set([',
            1,
        )[1].split(']);', 1)[0]
    blocker = STORY_JS.split(
        'function storyManualSaveOperationBlocked(run = activeRun) {',
        1,
    )[1].split(
        'function updateStoryManualSaveControls(run = activeRun) {',
        1,
    )[0]
    assert 'actionInFlight' in blocker
    assert 'cardPlayInFlight' in blocker
    assert 'storyCombatEntranceAnimating' in blocker
    assert 'storyManualSaveInFlight' in blocker
    assert "document.body.dataset.enemyAnimating === 'true'" in blocker
    assert "activeRun.state?.phase !== 'map'" not in STORY_JS
    assert "save.phase || ''" in STORY_JS


def test_story_cards_use_rarity_frames_type_tints_and_blind_concealment():
    assert "'--story-card-rarity-color'" in STORY_JS
    assert "'--story-card-type-color'" in STORY_JS
    assert '--card-border-width: var(--gtn-card-border-width);' in STORY_CSS
    assert 'border: var(--card-border-width) solid var(--card-frame-color);' in STORY_CSS
    type_tint = 'color-mix(in srgb, var(--story-card-type-color) 10%, var(--bg-card));'
    assert STORY_CSS.count(type_tint) >= 2
    assert 'background: rgba(255, 255, 255, .5);' not in STORY_CSS
    assert "const blindActive = Boolean(combat.blind_active);" in STORY_JS
    assert "element.classList.add('card-blinded', 'card-blinded-deep');" in STORY_JS
    assert "appendStoryRichText(description, blinded ? '?' : localize(values.description));" in STORY_JS


def test_empty_exact_exile_selection_skips_the_choice_dialog():
    assert "type === 'choose_exile' && source.length === 0" in STORY_JS
    assert 'if (!spec.source.length && spec.minimum === 0) return false;' in STORY_JS


def test_eternal_cards_are_hidden_from_blessing_transform_choices():
    assert "['remove_card', 'transform_card'].includes(blessing.script)" in STORY_JS
    assert "cardValues(card)?.tags?.includes('eternal')" in STORY_JS


def test_story_keyboard_card_selection_preserves_the_last_pointer_position():
    selection_branch = STORY_JS.split(
        'function selectCombatCard(state, card, event = null) {',
        1,
    )[1].split(
        'function isStoryCardChoiceCandidate(item, sourceCard) {',
        1,
    )[0]

    assert 'Number(event.detail) > 0' in selection_branch
    assert 'storyAimPointer = { x: event.clientX, y: event.clientY };' in selection_branch


def test_story_card_choice_rules_cover_sewage_and_share_candidate_validation():
    selection_branch = STORY_JS.split(
        'function isStoryCardChoiceCandidate(item, sourceCard) {',
        1,
    )[1].split(
        'function setStoryCardChoiceRequired(required) {',
        1,
    )[0]
    playable_branch = STORY_JS.split(
        'function canSatisfyCardSelection(card, combat) {',
        1,
    )[1].split(
        'function storyIntentStatusLabel(status)',
        1,
    )[0]

    assert "['choose_exile', 'copy_hand_card', 'make_card_free', 'active_discard'].includes(type)" in selection_branch
    assert "!(cardValues(item)?.tags || []).includes('sublime')" in selection_branch
    assert 'const spec = cardSelectionSpec(card, combat);' in playable_branch
    assert 'spec.source.length >= spec.minimum' in playable_branch


def test_story_event_and_choice_prose_use_the_loaded_game_font():
    for selector in (
        '.story-event-confirm-result span',
        '.story-event-narrative > p',
        '.story-event-history',
        '.story-choice-option > span:not(.story-choice-mark)',
    ):
        rule = STORY_CSS.split(f'{selector} {{', 1)[1].split('}', 1)[0]
        assert 'font-family: var(--font-main);' in rule
        assert 'system-ui' not in rule


def test_story_resources_use_fixed_tracks_and_shared_classic_compression():
    assert 'const STORY_RESOURCE_SLOT_COUNT = 10;' in STORY_JS
    assert "container.style.setProperty('--story-resource-slots', String(STORY_RESOURCE_SLOT_COUNT));" in STORY_JS
    assert 'globalThis.GTN_RESOURCE_ORBS.buildPreviewChunks(' in STORY_JS
    assert '            slots,\n            10,\n            true,' in STORY_JS
    assert '--story-resource-slots: 10;' in STORY_CSS
    assert 'Math.min(15, Math.max(baseline' not in STORY_JS
    assert 'chunks.slice(0, slots)' not in STORY_JS
    assert 'COMPRESSION_THRESHOLD = 15' in RESOURCE_ORBS_JS
    assert INDEX_TEMPLATE.index('/static/js/resource_orbs.js') < INDEX_TEMPLATE.index('/static/js/game.js')
    assert STORY_TEMPLATE.index('/static/js/resource_orbs.js') < STORY_TEMPLATE.index('/static/js/story.js')


def test_story_refresh_uses_recovery_checkpoints_and_rewards_are_layered():
    assert "action_type: 'resume_node'" not in STORY_JS
    assert 'id="story-reward-claims"' in STORY_TEMPLATE
    assert 'id="story-reward-continue"' in STORY_TEMPLATE
    assert "reward_type: 'gold'" in STORY_JS
    assert "reward_type: 'card'" in STORY_JS
    assert "reward_type: 'relic'" in STORY_JS
    assert "reward_type: 'continue'" in STORY_JS
    assert '.story-reward-claims {' in STORY_CSS


def test_enchantment_book_reward_rendering_stays_inside_reward_view():
    render_reward = STORY_JS.split('function renderReward(state) {', 1)[1].split(
        'function renderTerminal(state) {', 1
    )[0]
    render_run = STORY_JS.split('function renderRun(run) {', 1)[1].split(
        'async function loadRun()', 1
    )[0]

    assert 'if (reward.enchantment_book) {' in render_reward
    assert "reward_type: 'enchantment_book'" in render_reward
    assert 'if (reward.enchantment_book) {' not in render_run


def test_story_persistent_hud_keeps_player_map_deck_and_settings_available():
    for element_id in (
        'story-persistent-hud',
        'story-hud-player-name',
        'story-hud-difficulty',
        'story-hud-location',
        'story-hud-health',
        'story-hud-elixir',
        'story-hud-magic',
        'story-hud-gold',
        'story-hud-map',
        'story-hud-deck',
        'story-hud-save',
        'story-hud-settings',
        'story-hud-surrender',
    ):
        assert f'id="{element_id}"' in STORY_TEMPLATE
    assert 'function renderStoryPersistentHud(run)' in STORY_JS
    assert 'renderStoryPersistentHud(run);' in STORY_JS
    assert "$('story-hud-map')?.addEventListener('click', openStoryCombatMap);" in STORY_JS
    assert "$('story-hud-deck')?.addEventListener('click', () => openStoryPile('deck'));" in STORY_JS
    assert "$('story-hud-save')?.addEventListener('click', openManualStorySaves);" in STORY_JS
    assert "$('story-hud-settings')?.addEventListener('click', openStorySettings);" in STORY_JS
    assert 'manual_save_count' in STORY_JS
    assert 'manual_load_count' in STORY_JS
    assert 'id="story-settings-fullscreen"' in STORY_TEMPLATE
    assert 'id="story-settings-hide-borders"' in STORY_TEMPLATE
    assert 'id="story-settings-speed"' in STORY_TEMPLATE
    assert 'if (!storyMapPreviewOpen || !activeRun?.state) return;' in STORY_JS
    assert '.story-persistent-hud {' in STORY_CSS
    assert '.story-persistent-actions {' in STORY_CSS


def test_story_settings_only_commits_display_preferences_after_confirmation():
    settings = STORY_TEMPLATE.split(
        '<dialog id="story-settings-dialog"',
        1,
    )[1].split('</dialog>', 1)[0]

    assert 'id="story-settings-save"' not in settings
    assert 'id="story-settings-surrender"' not in settings
    assert 'id="story-settings-close"' not in settings
    assert 'id="story-settings-cancel"' in settings
    assert 'id="story-settings-confirm"' in settings
    assert 'value="cancel"' in settings
    assert 'value="confirm"' in settings
    assert 'function commitStorySettingsDraft()' in STORY_JS
    assert "event.target.returnValue === 'confirm'" in STORY_JS
    assert "$('story-settings-hide-borders')?.addEventListener('change'" not in STORY_JS
    assert "$('story-settings-speed')?.addEventListener('change'" not in STORY_JS


def test_story_card_play_unlocks_persistent_hud_after_action_settles():
    perform_card = STORY_JS.split(
        'async function performSelectedCombatCard(',
        1,
    )[1].split(
        'function playSelectedCombatCard(',
        1,
    )[0]
    settled = perform_card.split('cardPlayInFlight = false;', 1)[1]

    assert 'renderStoryPersistentHud(activeRun);' in settled
    assert settled.index('renderStoryPersistentHud(activeRun);') < settled.index(
        'updateStoryManualSaveControls();'
    )


def test_story_character_selector_disable_logic_stays_in_the_coop_control_scope():
    controls = STORY_JS.split(
        'function updateStoryCoopControls() {',
        1,
    )[1].split(
        'function renderStoryCoopParty() {',
        1,
    )[0]
    character_details = STORY_JS.split(
        'function renderStoryCharacterOptions() {',
        1,
    )[1].split(
        'function storyCoopCombatDialogOpen() {',
        1,
    )[0]

    assert "const characterSelect = $('story-coop-character-select');" in controls
    assert 'if (characterSelect) characterSelect.disabled = disabled || !canStart;' in controls
    assert 'if (characterSelect)' not in character_details


def test_story_event_animation_respects_server_sequence_metadata():
    assert '.sort((left, right) => {' in STORY_JS
    assert 'const leftSequence = Number(left.event?.sequence);' in STORY_JS
    assert 'return leftSequence - rightSequence || left.index - right.index;' in STORY_JS
    assert 'function storyEventBatches(sequence)' in STORY_JS
    assert 'String(event?.parallel_group || \'\')' in STORY_JS
    assert 'await Promise.all(' in STORY_JS
    assert 'playStoryPresentationEvent(event, nextRun)' in STORY_JS


def test_story_card_zone_events_have_distinct_play_draw_discard_and_insert_motion():
    assert 'async function animateStoryCardPlayed(event)' in STORY_JS
    assert 'async function animateStoryCardInserted(event)' in STORY_JS
    assert 'function storyCardFlightDimensions(sourceRect)' in STORY_JS
    assert 'Solo and cooperative story presentations deliberately share this path.' in STORY_JS
    assert "wrapper.classList.add('is-playing')" not in STORY_JS
    assert '.story-hand-card.is-playing {' not in STORY_CSS
    assert "eventType === 'card_played'" in STORY_JS
    assert "['card_created', 'cards_created', 'enemy_card_added'].includes(eventType)" in STORY_JS
    assert "await animateStoryPileMove(event, 'discard');" in STORY_JS
    assert 'await animateStoryDraw(event);' in STORY_JS
    assert '.story-card-flight.is-flying {' in STORY_CSS
    assert 'aspect-ratio: var(--story-card-flight-aspect, .72);' in STORY_CSS
    assert '@keyframes storyCardPlayFlight {' in STORY_CSS
    assert '@keyframes storyCardInsertFlight {' in STORY_CSS
    assert '@keyframes storyCardDiscardFlight {' in STORY_CSS
    assert "'card_created': {'motion': 'insert'}" in STORY_ENGINE
    assert "'cards_created': {'motion': 'insert'}" in STORY_ENGINE
    assert "'enemy_card_added': {'motion': 'insert'}" in STORY_ENGINE
    assert "'destination': 'hand'" in STORY_ENGINE
    assert "'actor_id': enemy['id']" in STORY_ENGINE


def test_mechanical_flower_track_orbits_and_resolves_cards_at_the_left_anchor():
    assert 'const STORY_MECHANICAL_TRACK_TRIGGER_ANGLE = -90;' in STORY_JS
    assert 'function renderStoryMechanicalTrack(portrait, enemy)' in STORY_JS
    assert "item.dataset.instanceId = String(card.instance_id || '');" in STORY_JS
    assert 'renderStoryMechanicalTrack(portrait, enemy);' in STORY_JS
    assert 'await animateStoryMechanicalTrackActivation(event);' in STORY_JS
    assert 'await settleAllStoryMechanicalTrackActivations();' in STORY_JS
    assert "wheel.append(item);" in STORY_JS
    assert "item.classList.add('is-leaving');" in STORY_JS
    assert "event.target?.closest?.('.story-mechanical-track-card')" in STORY_JS

    assert '.story-mechanical-track-wheel {' in STORY_CSS
    assert 'transform: rotate(var(--story-mechanical-track-rotation));' in STORY_CSS
    assert 'translateY(calc(-1 * var(--story-mechanical-track-radius)))' in STORY_CSS
    assert '.story-mechanical-track-card.is-at-trigger::after {' in STORY_CSS


def test_story_opening_lightning_stages_and_animates_combat_entrance():
    assert 'function createStoryCombatEntranceRun(run, events)' in STORY_JS
    assert "String(event?.source || '') === 'opening_lightning'" in STORY_JS
    assert 'storyCombatEntranceAnimating = true;' in STORY_JS
    assert 'renderRun(entranceRun);' in STORY_JS
    assert 'await storyNextPaint();' in STORY_JS
    assert 'const strike = animateOpeningLightning(target);' in STORY_JS
    assert "waitForStoryAnimation(target, 'is-opening-lightning-hit', 520)" in STORY_JS
    assert '.story-opening-lightning.is-striking {' in STORY_CSS
    assert '@keyframes storyOpeningLightningStrike {' in STORY_CSS
    assert '@keyframes storyActorLightningHit {' in STORY_CSS


def test_story_enemy_lifecycle_uses_stable_summon_and_defeat_actors():
    assert 'function ensureStorySummonedActor(event, nextRun)' in STORY_JS
    assert "const actor = createEnemyActor(enemy, '');" in STORY_JS
    assert "actor.classList.add('is-presentation-spawn');" in STORY_JS
    assert "eventType === 'enemy_summoned'" in STORY_JS
    assert 'await animateEnemySummon(event, nextRun);' in STORY_JS
    assert "eventType === 'enemy_defeated'" in STORY_JS
    assert 'await animateEnemyDefeat(event);' in STORY_JS
    assert '.story-actor.is-summoning {' in STORY_CSS
    assert '.story-actor.is-defeating {' in STORY_CSS
    assert '.story-actor.is-defeated-complete {' in STORY_CSS
    assert '@keyframes storyEnemySummonActor {' in STORY_CSS
    assert '@keyframes storyEnemyDefeatActor {' in STORY_CSS


def test_story_enemy_intents_render_structured_entries():
    assert 'function createStoryIntentEntry(entry)' in STORY_JS
    assert "item.dataset.intentKind = kind;" in STORY_JS
    assert 'Array.isArray(enemy.intent?.entries)' in STORY_JS
    assert '.story-intent-entries {' in STORY_CSS
    assert '.story-intent-entry.is-attack' in STORY_CSS


def test_story_codex_separates_intent_operations_and_omits_unnamed_blessing_heading():
    assert '.story-codex-intent-entries {' in STORY_CSS
    assert 'column-gap: 11px;' in STORY_CSS
    assert 'row-gap: 7px;' in STORY_CSS
    assert 'border-radius: 7px;' in STORY_CSS
    codex_intent_icon_rule = STORY_CSS.split(
        '.story-codex-intent-entries .story-intent-entry img {',
        1,
    )[1].split('}', 1)[0]
    assert 'width: 1.18em;' in codex_intent_icon_rule
    assert 'height: 1.18em;' in codex_intent_icon_rule
    assert 'flex: 0 0 1.18em;' in codex_intent_icon_rule
    assert 'const nameText = localize(record.definition.name).trim();' in STORY_JS
    assert 'if (nameText) {' in STORY_JS
    assert "if (type === 'clear_status') return { kind: 'clear_status'" in STORY_JS
    assert "} else if (kind === 'clear_status') {" in STORY_JS


def test_story_codex_cross_links_only_discovered_content_and_supports_back_navigation():
    assert 'id="story-codex-back"' in STORY_TEMPLATE
    assert 'let storyCodexHistory = [];' in STORY_JS
    assert 'function storyCodexTargetIsDiscovered(mode, id, kind = \'\')' in STORY_JS
    assert "storyCodexDiscoveredIds('term').has(`${String(kind || '')}:${targetId}`)" in STORY_JS
    assert 'function navigateStoryCodex(mode, id = \'\', options = {})' in STORY_JS
    assert 'function returnStoryCodexHistory()' in STORY_JS
    assert "$('story-codex-back')?.addEventListener('click', returnStoryCodexHistory);" in STORY_JS

    assert 'function storyCodexDefinitionReferences(definition)' in STORY_JS
    assert 'function storyCodexEnemyReferences(record)' in STORY_JS
    assert 'function storyCodexBacklinksForTerm(record)' in STORY_JS
    assert 'appendStoryCodexRelated(intents, storyCodexEnemyReferences(record));' in STORY_JS
    assert 'appendStoryCodexRelated(list, storyCodexBacklinksForTerm(record));' in STORY_JS
    assert 'appendStoryCodexRelated(copy, storyCodexBacklinksForCard(displayCard.def_id));' in STORY_JS
    assert "navigateStoryCodex('terms', traitId" in STORY_JS

    assert '.story-codex-back {' in STORY_CSS
    assert '.story-codex-related {' in STORY_CSS
    assert '.story-codex-reference {' in STORY_CSS
    assert '.story-term-codex-link {' in STORY_CSS
    assert '.story-card.card.is-related-target {' in STORY_CSS


def test_story_presentation_syncs_each_event_and_cannot_block_final_state_render():
    assert 'function syncStoryPresentationEvent(event, nextRun)' in STORY_JS
    assert 'function syncStoryPresentationPatch(patch, nextRun)' in STORY_JS
    assert 'syncStoryPresentationPatch(event.presentation_patch, nextRun);' in STORY_JS
    assert 'syncStoryPresentationEvent(event, nextRun);\n                            await playStoryPresentationEvent' in STORY_JS
    assert 'syncStoryPresentationEvent(event, nextRun);' in STORY_JS
    assert "console.warn('[story] presentation event failed'" in STORY_JS
    assert 'function updateStoryEffectValue(container, key, rawAmount)' in STORY_JS
    assert 'storyCombatEntranceAnimating = false;\n                renderRun(nextRun);' in STORY_JS


def test_story_map_distinguishes_traversed_and_next_edges():
    assert "traversed ? ' is-traversed' : ''" in STORY_JS
    assert "next ? ' is-next' : ''" in STORY_JS
    assert "class: 'story-map-current-marker'" in STORY_JS
    assert '.story-map-edge.is-traversed {' in STORY_CSS
    assert '.story-map-edge.is-next {' in STORY_CSS


def test_story_map_edges_stop_outside_translucent_nodes():
    assert 'const STORY_MAP_NODE_RADIUS = 25;' in STORY_JS
    assert 'const STORY_MAP_EDGE_INSET = STORY_MAP_NODE_RADIUS + 4;' in STORY_JS
    assert 'function mapEdgeSegment(start, end)' in STORY_JS
    assert 'const distance = Math.hypot(dx, dy);' in STORY_JS
    assert 'distance <= STORY_MAP_EDGE_INSET * 2' in STORY_JS
    assert 'const segment = mapEdgeSegment(start, end);' in STORY_JS
    assert 'x1: segment.start.x,' in STORY_JS
    assert 'y1: segment.start.y,' in STORY_JS
    assert 'x2: segment.end.x,' in STORY_JS
    assert 'y2: segment.end.y,' in STORY_JS
    assert 'r: STORY_MAP_NODE_RADIUS,' in STORY_JS


def test_story_permanent_deck_changes_require_explicit_confirmation():
    assert 'id="story-deck-change-dialog"' in STORY_TEMPLATE
    assert 'id="story-deck-change-before"' in STORY_TEMPLATE
    assert 'id="story-deck-change-after"' in STORY_TEMPLATE
    assert 'function openStoryDeckChange({ kind, card, payload, price = 0 })' in STORY_JS
    assert "kind: 'remove'" in STORY_JS
    assert "kind: 'upgrade'" in STORY_JS
    assert "event.target.returnValue !== 'confirm'" in STORY_JS
    assert 'storyAction(pending.actionType, pending.payload);' in STORY_JS
    assert '.story-deck-change-preview {' in STORY_CSS


def test_story_single_card_choices_replace_the_previous_selection():
    assert 'function toggleStoryCardChoice(wrapper, id, maximum)' in STORY_JS
    assert 'if (maximum === 1) {' in STORY_JS
    assert 'selected.clear();' in STORY_JS
    assert "querySelectorAll('.story-card-choice-select-item.is-selected')" in STORY_JS
    assert 'toggleStoryCardChoice(wrapper, id, spec.maximum);' in STORY_JS
    assert 'toggleStoryCardChoice(wrapper, id, maximum);' in STORY_JS


def test_story_high_cost_event_choices_require_confirmation():
    assert 'id="story-event-confirm-dialog"' in STORY_TEMPLATE
    assert 'function openStoryEventConfirmation(option, onConfirm)' in STORY_JS
    assert 'if (option.requires_confirmation)' in STORY_JS
    assert "event.target.returnValue !== 'confirm'" in STORY_JS
    assert '.story-event-confirm-result {' in STORY_CSS


def test_story_event_rooms_support_scene_speaker_history_and_choices():
    assert 'id="story-event-context"' in STORY_TEMPLATE
    assert 'id="story-event-scene"' in STORY_TEMPLATE
    assert 'id="story-event-speaker"' in STORY_TEMPLATE
    assert 'id="story-event-body"' in STORY_TEMPLATE
    assert 'id="story-event-history"' in STORY_TEMPLATE
    assert 'function renderStoryEventContext(room)' in STORY_JS
    assert 'room.choices || room.options || []' in STORY_JS
    assert 'historyEntries.slice(0, -1).slice(-4)' in STORY_JS
    assert '.story-event-context {' in STORY_CSS


def test_story_rest_chest_and_shop_have_dedicated_context_bands():
    for context_id in (
        'story-rest-context',
        'story-chest-context',
        'story-shop-context',
    ):
        assert f'id="{context_id}"' in STORY_TEMPLATE
    for value_id in (
        'story-rest-health-value',
        'story-rest-heal-value',
        'story-chest-gold-value',
        'story-chest-relic-name',
        'story-shop-gold-value',
        'story-shop-remove-value',
        'story-shop-upgrade-value',
    ):
        assert f'id="{value_id}"' in STORY_TEMPLATE
    assert 'function renderStoryRoomContext(state, room)' in STORY_JS
    assert 'renderStoryRoomContext(state, room);' in STORY_JS
    assert "roomView.dataset.roomType = String(room?.type || '');" in STORY_JS
    assert "const isRest = room?.type === 'rest';" in STORY_JS
    assert "const isChest = room?.type === 'chest';" in STORY_JS
    assert "const isShop = room?.type === 'shop';" in STORY_JS
    assert '.story-room-context {' in STORY_CSS
    assert '.story-rest-context {' in STORY_CSS
    assert '.story-chest-context {' in STORY_CSS
    assert '.story-shop-context {' in STORY_CSS


def test_story_room_tabs_remain_visible_when_card_lists_overflow():
    browser_index = STORY_TEMPLATE.index('<div class="story-room-browser">')
    tabs_index = STORY_TEMPLATE.index('id="story-room-tabs"')
    options_index = STORY_TEMPLATE.index('id="story-room-options"')
    footer_index = STORY_TEMPLATE.index('id="story-room-footer"')
    assert browser_index < tabs_index < options_index < footer_index

    room_rule = STORY_CSS.split(
        '#story-room.story-choice-screen {',
        1,
    )[1].split(
        '}',
        1,
    )[0]
    assert 'overflow: hidden;' in room_rule
    assert 'flex-direction: column;' in room_rule
    assert 'justify-content: flex-start;' in room_rule

    browser_rule = STORY_CSS.split(
        '.story-room-browser {\n  width: min(980px',
        1,
    )[1].split(
        '}',
        1,
    )[0]
    assert 'min-height: 0;' in browser_rule
    assert 'flex: 1 1 auto;' in browser_rule

    options_rule = STORY_CSS.split(
        '.story-room-browser #story-room-options {',
        1,
    )[1].split(
        '}',
        1,
    )[0]
    assert 'min-height: 0;' in options_rule
    assert 'overflow-y: auto;' in options_rule
    assert 'align-content: start;' in options_rule
    assert 'align-content: safe center;' in STORY_CSS


def test_story_card_browsers_scroll_vertically_without_overlapping_rows():
    assert "detail.classList.toggle('is-card-browser', storyCodexMode === 'cards');" in STORY_JS
    assert '.story-codex-detail.is-card-browser {' in STORY_CSS
    assert '.story-codex-card-shell {' in STORY_CSS
    assert 'max-height: 100%;' in STORY_CSS
    for selector in (
        '#story-room-options.story-room-card-grid {',
        '.story-card-choice-select-grid {',
        '.story-codex-card-grid {',
    ):
        rule = STORY_CSS.split(selector, 1)[1].split('}', 1)[0]
        assert 'grid-auto-rows: max-content;' in rule
        assert 'overflow-y: auto;' in rule
    assert 'overscroll-behavior: contain;' in STORY_CSS


def test_story_scrollable_lists_keep_position_when_the_same_view_rerenders():
    assert 'const STORY_PRESERVED_SCROLL_SELECTORS = Object.freeze([' in STORY_JS
    for selector in (
        "'#story-room-options'",
        "'#story-reward-options'",
        "'#story-hand'",
        "'#story-pile-grid'",
        "'#story-card-choice-grid'",
        "'[data-story-scroll-key]'",
    ):
        assert selector in STORY_JS
    assert 'function storyRunScrollContext(run = activeRun)' in STORY_JS
    assert 'function captureStoryScrollPositions()' in STORY_JS
    assert 'function restoreStoryScrollPositions(positions)' in STORY_JS
    assert "return `${storyRunScrollContext()}:room-tab:${activeStoryRoomTabId}:${identity}`;" in STORY_JS
    assert "if (identity.startsWith('codex-')) return identity;" in STORY_JS
    assert 'detail.dataset.storyScrollKey = `codex-detail:${storyCodexMode}:${subtype}:${storyCodexSelectedId}`;' in STORY_JS
    assert "grid.dataset.storyScrollKey = 'codex-card-grid';" in STORY_JS
    assert "list.dataset.storyScrollKey = 'codex-enemy-list';" in STORY_JS
    assert "renderCombat(state, false);" in STORY_JS

    for function_name in ('renderCombat', 'renderStoryCodex', 'renderManualStorySaves'):
        branch = STORY_JS.split(f'function {function_name}(', 1)[1]
        assert 'captureStoryScrollPositions()' in branch[:1200]
        assert 'restoreStoryScrollPositions(scrollPositions);' in branch


def test_boss_rush_map_positions_use_the_current_block_floor_range():
    bounds = STORY_JS.split('function storyMapFloorBounds(map) {', 1)[1].split(
        'function mapPoint(',
        1,
    )[0]
    assert 'Math.min(...floorNumbers)' in bounds
    assert 'Math.max(...floorNumbers)' in bounds
    assert 'span: Math.max(1, maximum - minimum)' in bounds

    map_render = STORY_JS.split('function renderMap(map, currentNodeId', 1)[1].split(
        'function currentNode(',
        1,
    )[0]
    assert 'const floorBounds = storyMapFloorBounds(map);' in map_render
    assert 'mapPoint(from, floorBounds)' in map_render
    assert 'mapPoint(to, floorBounds)' in map_render
    assert 'mapPoint(node, floorBounds)' in map_render
    assert 'mapPoint(focusNode, floorBounds)' in map_render


def test_story_codex_uses_explicit_rarity_order():
    expected_order = (
        "'primary'",
        "'common'",
        "'rare'",
        "'ultra'",
        "'super'",
        "'special'",
    )
    order_block = STORY_JS.split(
        'const STORY_RARITY_ORDER = Object.freeze([',
        1,
    )[1].split(']);', 1)[0]
    positions = [order_block.index(rarity) for rarity in expected_order]
    assert positions == sorted(positions)

    card_sort = STORY_JS.split('function storyCodexCardRecords() {', 1)[1].split(
        'function storyCodexFilterActions',
        1,
    )[0]
    assert 'STORY_RARITY_ORDER.indexOf' in card_sort
    assert 'Object.keys(storyContent?.rarities || {})' not in card_sort
    assert "[...rarityCounts.entries()].sort" in STORY_JS


def test_initial_blessing_card_selection_preserves_card_ratio_and_scrolls():
    render_branch = STORY_JS.split('function renderBlessing(state) {', 1)[1].split(
        'function appendStoryChoiceHeading',
        1,
    )[0]
    assert "screen?.classList.remove('is-card-selection');" in render_branch
    assert "screen?.classList.add('is-card-selection');" in render_branch
    grid_rule = STORY_CSS.split('.story-card-choice-grid {', 1)[1].split('}', 1)[0]
    card_rule = STORY_CSS.split(
        '.story-card-choice-grid > .story-card.card {',
        1,
    )[1].split('}', 1)[0]
    selection_rule = STORY_CSS.split(
        '#story-blessing.is-card-selection #story-blessing-options {',
        1,
    )[1].split('}', 1)[0]
    assert 'grid-auto-rows: max-content;' in grid_rule
    assert 'align-items: start;' in grid_rule
    assert 'height: auto;' in card_rule
    assert 'align-self: start;' in card_rule
    assert 'overflow-y: auto;' in selection_rule
    assert 'align-content: start;' in selection_rule


def test_story_untargeted_cards_bypass_only_the_explicit_enemy_target_guard():
    for function_name in ('performSelectedCombatCard', 'playSelectedCombatCard'):
        branch = STORY_JS.split(f'function {function_name}(', 1)[1].split('\n    }', 1)[0]
        guard = branch.split("targetKind === 'enemy'", 1)[1].split(') return;', 1)[0]
        assert '!storyCursorCardMode(card)' in guard
        assert '!storyEnemyIsSelectable(card, targetId' in guard


def test_story_enter_confirms_instead_of_toggling_the_focused_choice():
    dispatch = STORY_JS.split('function dispatchStoryShortcut(', 1)[1].split(
        'window.GTN_SHORTCUT_HOST =',
        1,
    )[0]
    assert "case 'confirm':\n            return confirmStorySurface();" in dispatch
    assert "case 'toggle_focused':\n            return toggleFocusedStoryItem();" in dispatch

    confirm = STORY_JS.split('function confirmStorySurface() {', 1)[1].split(
        'function createStoryShortcutContext(',
        1,
    )[0]
    dialog_confirm = confirm.index(
        "'[value=\"confirm\"]:not(:disabled), .story-command-primary:not(:disabled)'"
    )
    focused_choice = confirm.index('focusedStoryKeyboardItem(dialog)')
    assert dialog_confirm < focused_choice
    assert (
        "if (dialog.querySelector('[value=\"confirm\"], .story-command-primary')) return true;"
        in confirm
    )


def test_story_enter_overrides_native_choice_button_activation_when_confirming():
    host = STORY_JS.split('window.GTN_SHORTCUT_HOST = {', 1)[1].split(
        'async function init()',
        1,
    )[0]
    assert 'shouldOverrideNativeActivation(actionId)' in host
    assert "if (actionId !== 'confirm') return false;" in host
    assert "dialog?.querySelector('[value=\"confirm\"], .story-command-primary')" in host

    keydown = KEYBINDINGS_JS.split('function handleKeydown(event) {', 1)[1].split(
        'function handleKeyup(event)',
        1,
    )[0]
    assert 'host.shouldOverrideNativeActivation?.(action.id, event, focusedButton)' in keydown
    assert '&& !overrideNativeActivation' in keydown


def test_story_explicit_page_confirmation_is_keyboard_reachable():
    assert 'button.dataset.storyConfirmAction = \'1\';' in STORY_JS
    for action in ("storyAction('start_journey'", "storyAction('choose_stage'"):
        action_branch = STORY_JS.split(action, 1)[1][:400]
        assert '{ primary: true }' in action_branch
    assert '.story-reward-actions button:not(:disabled)' in STORY_JS
    assert '#story-room:not(.hidden) .story-room-footer button:not(:disabled)' in STORY_JS
    assert '#story-reward-continue:not(.hidden):not(:disabled)' in STORY_JS


def test_standard_journey_terminal_copy_describes_all_stages():
    assert "journeyCompleteCopy: '你已经穿过了旅程的全部阶段。'" in STORY_JS
    assert '你已经穿过了花园路线。' not in STORY_JS
