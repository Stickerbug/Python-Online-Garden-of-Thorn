from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORY_JS = (ROOT / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')
STORY_CSS = (ROOT / 'static' / 'css' / 'story.css').read_text(encoding='utf-8')
SHARED_AFK_CSS = (ROOT / 'static' / 'css' / 'shared-afk.css').read_text(encoding='utf-8')
STORY_TEMPLATE = (ROOT / 'templates' / 'story.html').read_text(encoding='utf-8')
INDEX_TEMPLATE = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
RESOURCE_ORBS_JS = (ROOT / 'static' / 'js' / 'resource_orbs.js').read_text(encoding='utf-8')


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

    assert 'typeLabel.textContent = STORY_CARD_TYPE_LABELS[cardType] || cardType;' in STORY_JS
    assert 'typeLabel.textContent = t.cardTypes?.[cardType] || cardType;' not in STORY_JS


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


def test_story_card_typography_matches_gallery_primitives():
    assert "--card-english-font: 5.55cqi;" in STORY_CSS
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


def test_story_globally_suppresses_context_menu_and_opens_card_terms():
    context_menu_branch = STORY_JS.split(
        "document.addEventListener('contextmenu', (event) => {",
        1,
    )[1].split(
        '});',
        1,
    )[0]
    assert 'event.preventDefault();' in context_menu_branch
    assert "event.target?.closest?.('.story-card.card, .story-pile-tile')" in context_menu_branch
    assert 'openStoryCardTerms(card);' in context_menu_branch
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
    assert "title.textContent = t.statusTerms;" in STORY_JS
    assert "kind: 'status'," in STORY_JS
    assert "item.kind === 'trait'" in STORY_JS
    assert 'storyStatusIconUrl(item.id);' in STORY_JS
    assert '.story-status-terms-layout {' in STORY_CSS
    assert '.story-status-terms-icon img {' in STORY_CSS


def test_story_talents_open_term_descriptions_from_every_visible_source():
    assert 'function openStoryRelicTerms(relicKey)' in STORY_JS
    assert 'function attachStoryRelicTermAccess(element, relicKey)' in STORY_JS
    assert 'element.dataset.storyRelicKey = key;' in STORY_JS
    assert "event.target?.closest?.('[data-story-relic-key]')" in STORY_JS
    assert 'openStoryRelicTerms(relicElement.dataset.storyRelicKey);' in STORY_JS
    assert 'title.textContent = t.talentTerms;' in STORY_JS
    assert "kind: 'relic'," in STORY_JS
    assert "attachStoryRelicTermAccess($('story-chest-relic-name')?.parentElement, room.relic);" in STORY_JS
    assert 'if (options.relicKey) attachStoryRelicTermAccess(button, options.relicKey);' in STORY_JS
    assert 'relicKey: item.relic_id,' in STORY_JS
    assert 'reward.relic,' in STORY_JS
    assert '.story-relic-terms-modal {' in STORY_CSS
    assert '.story-term-row-relic {' in STORY_CSS
    assert '.story-term-relic {' in STORY_CSS


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


def test_story_patch_traits_and_gold_icon_are_visible_ui_assets():
    assert 'function renderTraitsInto(container, traitIds, actor = null)' in STORY_JS
    assert 'function openStoryTraitTerms(traitKey)' in STORY_JS
    assert 'attachStoryTraitTermAccess(chip, key);' in STORY_JS
    assert 'renderTraitsInto(effects, definition.traits, enemy);' in STORY_JS
    assert "event.target?.closest?.('[data-story-trait-key]')" in STORY_JS
    assert '.story-effect.story-trait {' in STORY_CSS
    assert '.story-term-row-trait {' in STORY_CSS
    gold_url = '/static/assets/story-ui-icons/gold.svg'
    assert gold_url in STORY_TEMPLATE
    assert gold_url in STORY_CSS
    assert "setText('story-shop-mark'" not in STORY_JS
    assert (ROOT / gold_url.removeprefix('/')).is_file()


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


def test_story_upgrade_actions_preview_the_upgraded_card_on_hover():
    assert "if (options.previewUpgradeOnHover && !card.upgraded && storyCardHasUpgrade(card))" in STORY_JS
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
    assert ".filter((card) => !card.upgraded && storyCardHasUpgrade(card));" in STORY_JS
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


def test_story_right_click_cancels_selection_before_opening_terms():
    context_menu = STORY_JS.split(
        "document.addEventListener('contextmenu', (event) => {",
    )[-1].split(
        '});',
        1,
    )[0]

    cancel_check = "if (selectedCombatCardId && activeRun?.state) {"
    card_lookup = "const cardElement = event.target?.closest?.('.story-card.card, .story-pile-tile');"
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
    assert 'startStoryPresence();' in STORY_JS
    assert 'function updateStoryStatusBar()' in STORY_JS
    assert 'grid-template-rows: minmax(0, 1fr) 32px;' in STORY_CSS
    assert '.story-status-bar {' in STORY_CSS
    assert 'background: rgba(0, 0, 0, .05);' in STORY_CSS


def test_story_exit_glyph_is_visually_centered_in_its_button():
    glyph_rule = STORY_CSS.split('.story-exit-glyph {', 1)[1].split('}', 1)[0]
    assert 'position: relative;' in glyph_rule
    assert 'left: 2.8px;' in glyph_rule
    assert 'transform: rotate(45deg);' in glyph_rule


def test_story_enemy_group_enlarges_only_portraits_and_compacts_layout():
    assert "Math.max(.48, Math.min(.82, 1.03 - count * .13))" in STORY_JS
    group_rule = STORY_CSS.split('.story-enemy-group {', 2)[2].split('}', 1)[0]
    actor_rule = STORY_CSS.split('.story-enemy-group .story-actor {', 1)[1].split('}', 1)[0]
    assert 'gap: clamp(0px, .2vw, 3px);' in group_rule
    assert '--story-avatar-width: clamp(84px, 10vw, 152px);' in actor_rule
    assert '--story-fighter-scale: var(--story-enemy-scale, .82);' in actor_rule
    assert 'calc((var(--story-enemy-count) - 1) * -7px)' in actor_rule


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


def test_story_out_of_combat_deck_reuses_the_pile_viewer():
    assert 'id="story-run-deck"' in STORY_TEMPLATE
    assert 'src="/static/assets/ui-icons/total-pile.svg"' in STORY_TEMPLATE
    assert "runDeck: '总牌库', viewRunDeck: '查看总牌库'" in STORY_JS
    assert "deck: { source: state?.player?.deck, title: t.runDeck, reverse: false }" in STORY_JS
    assert "if (kind === 'deck' && state?.phase === 'combat') return;" in STORY_JS
    assert "['story-loading', 'story-empty', 'story-combat'].includes(name)" in STORY_JS
    assert 'runDeck?.classList.toggle(\'hidden\', runDeckUnavailable);' in STORY_JS
    assert "$('story-run-deck')?.addEventListener('click', () => openStoryPile('deck'));" in STORY_JS
    assert "cards.forEach((card, index) => grid?.append(createStoryPileTile(card, index + 1)));" in STORY_JS
    assert '.story-run-deck-command {' in STORY_CSS


def test_story_talent_overview_sits_before_deck_and_opens_terms():
    status_actions = STORY_TEMPLATE.split(
        '<div class="story-status-actions">',
        1,
    )[1].split(
        '</div>',
        1,
    )[0]
    assert status_actions.index('id="story-talent-overview"') < status_actions.index('id="story-run-deck"')
    assert 'id="story-talent-overview-label"' in STORY_TEMPLATE
    assert '/static/assets/ui-icons/achievements.svg' in STORY_TEMPLATE
    assert 'function openStoryTalentOverview()' in STORY_JS
    assert 'state.player?.relics' in STORY_JS
    assert 'createStoryTalentOverviewItem(relicKey, index + 1)' in STORY_JS
    assert 'attachStoryRelicTermAccess(item, key);' in STORY_JS
    assert 'openStoryRelicTerms(key);' in STORY_JS
    assert "$('story-talent-overview')?.addEventListener('click', openStoryTalentOverview);" in STORY_JS
    assert "grid?.classList.add('is-talents');" in STORY_JS
    assert '.story-pile-grid.is-talents {' in STORY_CSS
    assert '.story-talent-overview-item {' in STORY_CSS


def test_story_keyboard_card_selection_preserves_the_last_pointer_position():
    selection_branch = STORY_JS.split(
        'function selectCombatCard(state, card, event = null) {',
        1,
    )[1].split(
        'function cardSelectionSpec(card) {',
        1,
    )[0]

    assert 'Number(event.detail) > 0' in selection_branch
    assert 'storyAimPointer = { x: event.clientX, y: event.clientY };' in selection_branch


def test_story_resources_use_fixed_tracks_and_shared_classic_compression():
    assert 'const STORY_RESOURCE_SLOT_COUNT = 10;' in STORY_JS
    assert "container.style.setProperty('--story-resource-slots', String(STORY_RESOURCE_SLOT_COUNT));" in STORY_JS
    assert 'globalThis.GTN_RESOURCE_ORBS.buildPreviewChunks(now, cost, slots)' in STORY_JS
    assert '--story-resource-slots: 10;' in STORY_CSS
    assert 'Math.min(15, Math.max(baseline' not in STORY_JS
    assert 'chunks.slice(0, slots)' not in STORY_JS
    assert 'COMPRESSION_THRESHOLD = 15' in RESOURCE_ORBS_JS
    assert INDEX_TEMPLATE.index('/static/js/resource_orbs.js') < INDEX_TEMPLATE.index('/static/js/game.js')
    assert STORY_TEMPLATE.index('/static/js/resource_orbs.js') < STORY_TEMPLATE.index('/static/js/story.js')


def test_story_refresh_uses_recovery_checkpoints_and_rewards_are_layered():
    assert "action_type: 'resume_node'" in STORY_JS
    assert "['combat', 'room', 'reward'].includes(phase)" in STORY_JS
    assert 'id="story-reward-claims"' in STORY_TEMPLATE
    assert 'id="story-reward-continue"' in STORY_TEMPLATE
    assert "reward_type: 'gold'" in STORY_JS
    assert "reward_type: 'card'" in STORY_JS
    assert "reward_type: 'relic'" in STORY_JS
    assert "reward_type: 'continue'" in STORY_JS
    assert '.story-reward-claims {' in STORY_CSS


def test_story_event_animation_respects_server_sequence_metadata():
    assert '.sort((left, right) => {' in STORY_JS
    assert 'const leftSequence = Number(left.event?.sequence);' in STORY_JS
    assert 'return leftSequence - rightSequence || left.index - right.index;' in STORY_JS
    assert 'function storyEventBatches(sequence)' in STORY_JS
    assert 'String(event?.parallel_group || \'\')' in STORY_JS
    assert 'await Promise.all(' in STORY_JS
    assert 'playStoryPresentationEvent(event, nextRun)' in STORY_JS


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
