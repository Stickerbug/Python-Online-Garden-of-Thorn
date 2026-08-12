from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import app as gtn
import db
from story_content import (
    STORY_BLESSINGS,
    STORY_CARDS,
    STORY_ENEMIES,
    STORY_RELICS,
    STORY_STATUSES,
    story_content_payload,
)
from story_discovery import collect_story_discoveries
from story_mode import build_initial_story_state


def _keys(discoveries):
    return {
        (
            item['content_type'],
            item['content_id'],
            item.get('variant', 'base'),
        )
        for item in discoveries
    }


def test_initial_discoveries_include_owned_content_but_not_future_map_rooms():
    state = build_initial_story_state('story-discovery-initial')
    keys = _keys(collect_story_discoveries(state))

    assert ('card', 'basic', 'base') in keys
    assert ('card', 'rose', 'base') in keys
    assert ('card', 'amulet', 'base') in keys
    assert ('relic', 'energetic', 'base') in keys
    assert ('term', 'resource:D', 'base') in keys
    assert ('term', 'resource:H', 'base') in keys
    assert not any(content_type == 'enemy' for content_type, _, _ in keys)


def test_visible_reward_and_shop_options_are_discovered_without_being_chosen():
    state = build_initial_story_state('story-discovery-options')
    starter_ids = {card['def_id'] for card in state['player']['deck']}
    card_id = next(card_id for card_id in STORY_CARDS if card_id not in starter_ids)
    relic_id = next(relic_id for relic_id in STORY_RELICS if relic_id != 'energetic')
    state['reward'] = {
        'cards': [{'card_id': card_id, 'upgraded': True}],
        'relics': [relic_id],
    }

    keys = _keys(collect_story_discoveries(state))

    assert ('card', card_id, 'upgraded') in keys
    assert ('relic', relic_id, 'base') in keys
    assert all(card['def_id'] != card_id for card in state['player']['deck'])


def test_enemy_discovery_records_only_the_intent_currently_shown():
    state = build_initial_story_state('story-discovery-enemy')
    enemy_id, definition = next(
        (enemy_id, definition)
        for enemy_id, definition in STORY_ENEMIES.items()
        if len(definition.get('moves') or ()) >= 2
    )
    state['combat'] = {
        'hand': [],
        'draw_pile': [],
        'discard_pile': [],
        'exile_pile': [],
        'equipment': [],
        'enemies': [{
            'id': 'enemy-test',
            'def_id': enemy_id,
            'move_index': 1,
            'health': definition['max_health'],
        }],
    }

    keys = _keys(collect_story_discoveries(state))

    assert ('enemy', enemy_id, 'base') in keys
    assert ('enemy', enemy_id, 'intent:1') in keys
    assert ('enemy', enemy_id, 'intent:0') not in keys


def test_enemy_discovery_prefers_the_projected_intent_over_internal_move_index():
    state = build_initial_story_state('story-discovery-projected-intent')
    enemy_id, definition = next(
        (enemy_id, definition)
        for enemy_id, definition in STORY_ENEMIES.items()
        if len(definition.get('moves') or ()) >= 2
    )
    state['combat'] = {
        'hand': [],
        'draw_pile': [],
        'discard_pile': [],
        'exile_pile': [],
        'equipment': [],
        'enemies': [{
            'id': 'enemy-projected-intent',
            'def_id': enemy_id,
            'move_index': 0,
            'intent': {'name': definition['moves'][1]['name']},
            'health': definition['max_health'],
        }],
    }

    keys = _keys(collect_story_discoveries(state))

    assert ('enemy', enemy_id, 'intent:1') in keys
    assert ('enemy', enemy_id, 'intent:0') not in keys


def test_visible_traits_statuses_and_blessing_options_unlock_their_entries():
    state = build_initial_story_state('story-discovery-terms')
    enemy_id, definition = next(
        (enemy_id, definition)
        for enemy_id, definition in STORY_ENEMIES.items()
        if definition.get('traits')
    )
    status_id = next(iter(STORY_STATUSES))
    blessing_id = next(iter(STORY_BLESSINGS))
    state['combat'] = {
        'hand': [],
        'draw_pile': [],
        'discard_pile': [],
        'exile_pile': [],
        'equipment': [],
        status_id: -2,
        'enemies': [{
            'id': 'enemy-terms',
            'def_id': enemy_id,
            'move_index': 0,
            'health': definition['max_health'],
        }],
    }
    state['blessing_options'] = [blessing_id]

    keys = _keys(collect_story_discoveries(state))

    assert ('blessing', blessing_id, 'base') in keys
    assert ('term', f'status:{status_id}', 'base') in keys
    for trait_id in definition['traits']:
        assert ('term', f'trait:{trait_id}', 'base') in keys


def test_story_discovery_storage_is_idempotent_and_can_mark_unread(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'story-discovery.sqlite3'))
    db.init_db()
    user, error = db.create_user('StoryDiscover', 'Aa1!aaaa')
    assert error is None
    discoveries = [
        {'content_type': 'card', 'content_id': 'basic', 'variant': 'base'},
        {'content_type': 'term', 'content_id': 'resource:D', 'variant': 'base'},
    ]

    inserted = db.record_story_discoveries(user['id'], discoveries, 'run-1')
    assert len(inserted) == 2
    assert all(item['viewed_at'] is None for item in inserted)
    assert db.record_story_discoveries(user['id'], discoveries, 'run-1') == []
    assert len(db.list_story_discoveries(user['id'])) == 2

    assert db.mark_story_discoveries_viewed(user['id']) == 2
    stored = db.list_story_discoveries(user['id'])
    assert all(item['viewed_at'] for item in stored)
    assert db.mark_story_discoveries_viewed(user['id']) == 0


def test_story_compendium_uses_the_existing_story_card_renderer():
    root = Path(__file__).resolve().parents[1]
    template = (root / 'templates' / 'story.html').read_text(encoding='utf-8')
    script = (root / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')
    stylesheet = (root / 'static' / 'css' / 'story.css').read_text(encoding='utf-8')

    assert 'id="story-codex-dialog"' in template
    assert 'data-story-codex-mode="cards"' in template
    assert 'createStoryCard(card, {' in script
    assert 'allowedUpgradeStates' in script
    assert '/api/story/discoveries/read' in script
    assert '@media (max-width: 600px)' in stylesheet
    assert 'grid-template-rows: 112px minmax(0, 1fr);' in stylesheet


def test_story_effect_bar_ignores_missing_status_values():
    root = Path(__file__).resolve().parents[1]
    script = (root / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')

    assert 'if (!Number.isFinite(amount) || amount === 0) return;' in script
    assert 'value.textContent = String(amount);' in script


def test_story_content_inherits_source_card_flavor_text():
    source = SimpleNamespace(
        image_url='',
        image='',
        upgraded_image_url='',
        upgraded_image='',
        description='玫瑰的趣味描述。',
        description_i18n={
            'zh': '玫瑰的趣味描述。',
            'en': 'Rose flavor text.',
        },
    )

    payload = story_content_payload({'Rose': source})

    assert payload['cards']['rose']['flavor'] == source.description_i18n
    assert 'curses' not in payload


def test_story_card_terms_show_rarity_and_plain_flavor_text():
    root = Path(__file__).resolve().parents[1]
    script = (root / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')
    stylesheet = (root / 'static' / 'css' / 'story.css').read_text(encoding='utf-8')

    assert "rarity.className = 'story-card-terms-rarity';" in script
    assert 'flavor.textContent = flavorText;' in script
    assert 'appendStoryRichText(flavor' not in script
    assert '.story-card-terms-rarity {' in stylesheet
    assert '.story-card-terms-flavor {' in stylesheet


def test_duplicate_story_action_rehydrates_discoveries_after_a_lost_response():
    client = gtn.app.test_client()
    run = {
        'id': 'story-run-duplicate',
        'state_version': 3,
        'state': build_initial_story_state('story-run-duplicate'),
    }
    discoveries = [{
        'content_type': 'card',
        'content_id': 'basic',
        'variant': 'base',
        'viewed_at': None,
    }]
    with (
        mock.patch.object(gtn, '_require_account_json', return_value=(41, 'StoryTester', None)),
        mock.patch.object(gtn, 'get_story_run_action', return_value={'action_id': 'retry'}),
        mock.patch.object(gtn, '_current_story_run', return_value=run),
        mock.patch.object(gtn, '_list_story_discoveries_without_blocking', return_value=discoveries),
    ):
        response = client.post('/api/story/run/action', json={
            'run_id': run['id'],
            'state_version': run['state_version'],
            'action_id': 'retry',
            'action_type': 'play_card',
            'payload': {},
        })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['duplicate'] is True
    assert payload['discoveries'] == discoveries
