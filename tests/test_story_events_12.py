from story_events_12 import STORY_EVENTS_12, event_12_action_hint


def test_all_18_workbook_events_are_defined():
    assert len(STORY_EVENTS_12) == 18
    assert set(STORY_EVENTS_12) == {
        'crusher_machine', 'library', 'enchanter', 'midas_coin',
        'world_tree_branch', 'endless_marathon', 'herald', 'strange_anvil',
        'bbq', 'titan', 'deep_branch', 'withered_trunk', 'card_machine',
        'secret_passage', 'card_giftpack', 'talent_lottery',
        'scale_judgement', 'bank',
    }


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
