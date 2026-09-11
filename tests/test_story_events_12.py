from story_events_12 import STORY_EVENTS_12, event_12_action_hint
from story_engine import _resolve_new_event_12
from story_mode import build_initial_story_state


def _scale_run(deck_size=2, health=40):
    state = build_initial_story_state('run-scale', 'common_flower')
    player = state['player']
    player['health'] = health
    player['max_health'] = 80
    player['deck'] = [
        {
            'def_id': 'basic' if index % 2 == 0 else 'bone',
            'instance_id': f'scale-{index}',
            'upgraded': True,
            'upgrade_level': 1,
        }
        for index in range(deck_size)
    ]
    return state


def test_all_18_workbook_events_are_defined():
    assert len(STORY_EVENTS_12) == 18
    assert set(STORY_EVENTS_12) == {
        'crusher_machine', 'library', 'enchanter', 'midas_coin',
        'world_tree_branch', 'endless_marathon', 'herald', 'strange_anvil',
        'bbq', 'titan', 'deep_branch', 'withered_trunk', 'card_machine',
        'secret_passage', 'card_giftpack', 'talent_lottery',
        'scale_judgement', 'bank',
    }


def test_new_events_carry_intro_copy_and_split_option_descriptions():
    for event_id, definition in STORY_EVENTS_12.items():
        assert definition.get('body') and definition['body'].get('zh'), event_id
        assert definition.get('speaker') and definition['speaker'].get('zh'), event_id
        for option in definition.get('options') or ():
            option_id = str(option.get('id') or '')
            if option_id == 'leave':
                continue
            assert option.get('label') and option['label'].get('zh'), (
                f'{event_id}:{option_id}'
            )
            assert option.get('description') and option['description'].get('zh'), (
                f'{event_id}:{option_id}'
            )


def test_option_ids_are_unique_and_leave_has_hint():
    for event_id, definition in STORY_EVENTS_12.items():
        ids = [str(option['id']) for option in definition['options']]
        assert len(ids) == len(set(ids)), event_id
        for option in definition['options']:
            if str(option['id']) == 'leave':
                assert event_12_action_hint(event_id, 'leave') == 'leave'
            else:
                assert event_12_action_hint(event_id, str(option['id']))


def test_action_hint_unknown_is_empty():
    assert event_12_action_hint('missing', 'x') == ''


def test_scale_judgement_offers_a_balance_option_matching_the_workbook():
    options = STORY_EVENTS_12['scale_judgement']['options']
    assert [option['id'] for option in options] == [
        'scale_you', 'scale_cards', 'scale_balance',
    ]
    balance = options[2]
    assert balance['label']['zh'] == '平衡'
    assert '随机降级一张牌' in balance['description']['zh']
    assert '20H' in balance['description']['zh']
    assert event_12_action_hint('scale_judgement', 'scale_balance') == 'scale_balance'


def test_scale_balance_downgrades_exactly_one_card_and_heals_twenty():
    state = _scale_run(deck_size=3, health=40)
    player = state['player']
    events = []

    _resolve_new_event_12(
        state, 'scale_judgement', 'scale_balance', {}, 'scale-seed', events,
    )

    downgraded = [card for card in player['deck'] if not card.get('upgraded')]
    assert len(downgraded) == 1
    assert player['health'] == 60
    assert [event['type'] for event in events].count('heal') == 1


def test_scale_toward_player_grants_exactly_one_fatigued_card():
    state = _scale_run(deck_size=2, health=30)
    player = state['player']
    events = []

    _resolve_new_event_12(
        state, 'scale_judgement', 'scale_you', {}, 'scale-seed', events,
    )

    fatigued = [card for card in player['deck'] if card.get('def_id') == 'fatigued']
    assert len(fatigued) == 1
    assert player['max_health'] == 160
