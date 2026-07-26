from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORY_JS = (ROOT / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')
STORY_CSS = (ROOT / 'static' / 'css' / 'story.css').read_text(encoding='utf-8')


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
