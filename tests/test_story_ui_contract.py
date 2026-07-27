from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORY_JS = (ROOT / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')
STORY_CSS = (ROOT / 'static' / 'css' / 'story.css').read_text(encoding='utf-8')
STORY_TEMPLATE = (ROOT / 'templates' / 'story.html').read_text(encoding='utf-8')
INDEX_TEMPLATE = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
RESOURCE_ORBS_JS = (ROOT / 'static' / 'js' / 'resource_orbs.js').read_text(encoding='utf-8')


def test_story_damage_floats_describe_lost_health():
    player_branch = STORY_JS.split(
        "} else if (event.type === 'player_damage') {",
        1,
    )[1].split(
        "} else if (event.type === 'enemy_damage') {",
        1,
    )[0]
    enemy_branch = STORY_JS.split(
        "} else if (event.type === 'enemy_damage') {",
        1,
    )[1].split(
        "} else if (event.type === 'enemy_gain') {",
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
