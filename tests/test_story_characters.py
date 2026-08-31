from unittest import mock

import pytest

import app as gtn
from story_content import (
    STORY_CARDS,
    STORY_CHARACTERS,
    STORY_CHARACTER_NOT_READY_MESSAGE,
    STORY_RELICS,
    story_content_payload,
)
from story_engine import _start_combat, apply_story_action
from story_mode import build_initial_story_state


def test_all_sheet_characters_are_projected_with_a_stable_unavailable_message():
    payload = story_content_payload()
    assert tuple(payload['characters']) == (
        'common_flower', 'orbiter', 'summoner', 'mage', 'occultist',
    )
    for character_id in ('common_flower', 'mage'):
        assert payload['characters'][character_id]['implementation_status'] == 'playable'
    for character_id in ('orbiter', 'summoner', 'occultist'):
        assert payload['characters'][character_id]['implementation_status'] == 'planned'
        assert (
            payload['characters'][character_id]['unavailable_message']
            == STORY_CHARACTER_NOT_READY_MESSAGE
        )


def test_initial_story_state_records_character_and_rejects_unready_roles():
    state = build_initial_story_state('character-common', 'common_flower')
    assert state['character_id'] == 'common_flower'
    assert state['player']['character_id'] == 'common_flower'

    mage = build_initial_story_state('character-mage', 'mage')
    assert mage['character_id'] == 'mage'
    assert mage['player']['character_id'] == 'mage'
    with pytest.raises(ValueError, match='STORY_CHARACTER_NOT_READY'):
        build_initial_story_state('character-orbiter', 'orbiter')
    with pytest.raises(ValueError, match='UNKNOWN_STORY_CHARACTER'):
        build_initial_story_state('character-unknown', 'future_unknown')


def test_story_run_api_rejects_unready_and_unknown_characters_before_db_write():
    client = gtn.app.test_client()
    with (
        mock.patch.object(gtn, '_require_account_json', return_value=(41, 'Tester', None)),
        mock.patch.object(gtn, '_current_story_run', return_value=None),
        mock.patch.object(gtn, 'create_story_run') as create_run,
    ):
        unready = client.post('/api/story/run', json={'character_id': 'orbiter'})
        unknown = client.post('/api/story/run', json={'character_id': 'future_unknown'})
        malformed = client.post('/api/story/run', json=['common_flower'])

    assert unready.status_code == 409
    assert unready.get_json() == {
        'success': False,
        'error': STORY_CHARACTER_NOT_READY_MESSAGE['zh'],
        'code': 'STORY_CHARACTER_NOT_READY',
        'character_id': 'orbiter',
    }
    assert unknown.status_code == 400
    assert unknown.get_json()['code'] == 'UNKNOWN_STORY_CHARACTER'
    assert malformed.status_code == 400
    assert malformed.get_json()['code'] == 'INVALID_STORY_RUN_REQUEST'
    create_run.assert_not_called()


def test_story_run_api_persists_the_selected_playable_character():
    client = gtn.app.test_client()
    created_run = {
        'id': 'story-character-run',
        'content_version': gtn.STORY_CONTENT_VERSION,
        'state_version': 1,
        'state': {},
    }
    with (
        mock.patch.object(gtn, '_require_account_json', return_value=(41, 'Tester', None)),
        mock.patch.object(gtn, '_current_story_run', return_value=None),
        mock.patch.object(gtn, 'create_story_run', return_value=(created_run, True)) as create_run,
        mock.patch.object(gtn, '_story_run_with_compatibility', side_effect=lambda run: run),
        mock.patch.object(gtn, '_sync_story_discoveries', return_value=[]),
        mock.patch.object(gtn, '_list_story_discoveries_without_blocking', return_value=[]),
    ):
        response = client.post('/api/story/run', json={'character_id': 'common_flower'})

    assert response.status_code == 200
    state = create_run.call_args.args[3]
    assert state['character_id'] == 'common_flower'
    assert state['player']['character_id'] == 'common_flower'


def test_character_selector_is_wired_without_allowing_planned_roles_to_start():
    template = open('templates/story.html', encoding='utf-8').read()
    script = open('static/js/story.js', encoding='utf-8').read()
    stylesheet = open('static/css/story.css', encoding='utf-8').read()

    assert 'id="story-character-options"' in template
    assert 'id="story-character-detail"' in template
    assert 'id="story-character-deck"' in template
    assert 'id="story-character-talents"' in template
    assert 'id="story-character-not-ready"' in template
    assert "definition?.implementation_status || 'planned'" in script
    assert "code='STORY_CHARACTER_NOT_READY'" not in script
    assert 'body: JSON.stringify({ character_id: selectedStoryCharacterId })' in script
    assert 'storyContent?.character_cards?.[item.character_card_id]' in script
    assert 'storyContent?.character_relics?.[relicId]' in script
    assert '.story-character-option.is-planned' in stylesheet
    assert '.story-character-detail' in stylesheet
    assert 'white-space: pre-line' in stylesheet
    assert STORY_CHARACTERS['mage']['name']['zh'] == '魔法师'


def test_confirmed_character_loadouts_and_unlock_chain_are_exposed():
    content = story_content_payload()
    common = content['characters']['common_flower']
    mage = content['characters']['mage']

    assert common['starter_deck'] == (
        {'card_id': 'basic', 'count': 5},
        {'card_id': 'rose', 'count': 4},
        {'card_id': 'amulet', 'count': 1},
    )
    assert common['starter_relics'] == ('energetic',)
    assert mage['starter_deck'] == (
        {'card_id': 'basic', 'count': 5},
        {'card_id': 'rose', 'count': 5},
        {'character_card_id': 'mage_basic', 'count': 1},
    )
    assert mage['starter_relics'] == ('magic_source',)
    assert mage['unlock']['character_id'] == 'common_flower'
    assert mage['unlock']['any_difficulty'] is True
    assert content['character_cards']['mage_basic']['name']['zh'] == '魔法基本'
    assert content['character_relics']['magic_source']['effect_text'] == '回合开始时，回复1M'

    chain = ('common_flower', 'mage', 'orbiter', 'summoner', 'occultist')
    for previous, current in zip(chain, chain[1:]):
        unlock = content['characters'][current]['unlock']
        assert unlock['kind'] == 'complete_journey'
        assert unlock['character_id'] == previous
        assert unlock['any_difficulty'] is True


def test_mage_starter_runtime_is_source_backed_and_playable():
    mage_basic = STORY_CARDS['mage_basic']
    assert mage_basic['owner'] == 'mage'
    assert mage_basic['rarity'] == 'primary'
    assert mage_basic['cost_e'] == 1
    assert mage_basic['cost_m'] == 2
    assert mage_basic['effects'] == ({'type': 'damage', 'amount': 13},)
    assert mage_basic['upgrade']['effects'] == ({'type': 'damage', 'amount': 18},)
    assert STORY_RELICS['magic_source']['script'] == 'turn_magic'
    assert STORY_RELICS['magic_source']['amount'] == 1
    assert STORY_CHARACTERS['mage']['implementation_status'] == 'playable'
    state = build_initial_story_state('mage-loadout-preview', 'mage')
    assert [card['def_id'] for card in state['player']['deck']] == (
        ['basic'] * 5 + ['rose'] * 5 + ['mage_basic']
    )
    assert state['player']['relics'] == ['magic_source']
    assert state['player']['magic'] == 0


def test_magic_source_restores_one_magic_at_combat_and_turn_start():
    state = build_initial_story_state('mage-source-timing')
    state['player']['relics'] = ['magic_source']
    state['player']['magic'] = 0
    events = []
    _start_combat(
        state,
        {'type': 'combat'},
        'mage-source-timing',
        events,
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    assert state['combat']['magic'] == 1
    assert any(
        event.get('type') == 'magic'
        and event.get('before') == 0
        and event.get('after') == 1
        for event in events
    )

    state['player']['health'] = state['player']['max_health'] = 999
    state['combat']['opening_redraw_pending'] = False
    for enemy in state['combat']['enemies']:
        enemy['stun'] = 1
    state, events = apply_story_action(
        state, 'end_turn', {}, 'mage-source-timing-next-turn'
    )
    assert state['combat']['magic'] == 2
    assert any(
        event.get('type') == 'magic'
        and event.get('before') == 1
        and event.get('after') == 2
        for event in events
    )


def test_audited_simple_mage_cards_compile_without_entering_other_character_pools():
    expected = {
        'mage_fries': (
            ({'type': 'heal', 'amount': 7},),
            ({'type': 'heal', 'amount': 10},),
            ('exile',),
        ),
        'mage_coffee': (
            ({'type': 'magic', 'amount': 4},),
            ({'type': 'magic', 'amount': 5},),
            ('exile',),
        ),
        'mage_bone': (
            ({'type': 'damage', 'amount': 9}, {'type': 'shield', 'amount': 6}),
            ({'type': 'damage', 'amount': 12}, {'type': 'shield', 'amount': 8}),
            (),
        ),
        'mage_palm_leaf': (
            ({'type': 'shield', 'amount': 10}, {'type': 'magic', 'amount': 3}),
            ({'type': 'shield', 'amount': 14}, {'type': 'magic', 'amount': 3}),
            (),
        ),
        'mage_bubble_bomb': (
            ({'type': 'damage', 'amount': 14}, {'type': 'status', 'amount': 2, 'status': 'weak'}),
            ({'type': 'damage', 'amount': 17}, {'type': 'status', 'amount': 3, 'status': 'weak'}),
            ('wide',),
        ),
        'mage_rock': (
            ({'type': 'damage', 'amount': 7}, {'type': 'status', 'amount': 2, 'status': 'vulnerable'}),
            ({'type': 'damage', 'amount': 9}, {'type': 'status', 'amount': 3, 'status': 'vulnerable'}),
            (),
        ),
        'mage_missile': (
            ({'type': 'damage', 'amount': 15}, {'type': 'draw', 'amount': 3}),
            ({'type': 'damage', 'amount': 17}, {'type': 'draw', 'amount': 4}),
            ('ready',),
        ),
        'mage_rose': (
            ({'type': 'shield', 'amount': 9},),
            ({'type': 'shield', 'amount': 12},),
            (),
        ),
    }
    from story_content import STORY_REWARD_CARD_IDS, STORY_SHOP_CARD_IDS

    for card_id, (effects, upgraded_effects, tags) in expected.items():
        card = STORY_CARDS[card_id]
        assert card['owner'] == 'mage'
        assert card['effects'] == effects
        assert card['upgrade']['effects'] == upgraded_effects
        assert card['tags'] == tags
        assert card_id not in STORY_REWARD_CARD_IDS
        assert card_id not in STORY_SHOP_CARD_IDS


def test_mage_fries_uses_authoritative_healing_and_exile_flow():
    state = build_initial_story_state('mage-fries-runtime')
    events = []
    _start_combat(
        state,
        {'type': 'combat'},
        'mage-fries-runtime',
        events,
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    combat = state['combat']
    combat['opening_redraw_pending'] = False
    state['player']['health'] = 40
    combat['elixir'] = 10
    combat['magic'] = 10
    fries = {'instance_id': 'mage-fries-test', 'def_id': 'mage_fries', 'upgraded': False}
    combat['hand'] = [fries]

    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': fries['instance_id']},
        'mage-fries-runtime-play',
    )
    assert state['player']['health'] == 47
    assert state['combat']['magic'] == 8
    assert state['combat']['exile_pile'][-1]['def_id'] == 'mage_fries'
    assert any(
        event.get('type') == 'heal'
        and event.get('amount') == 7
        and event.get('source') == 'mage_fries'
        for event in events
    )
