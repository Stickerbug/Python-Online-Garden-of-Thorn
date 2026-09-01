import random

import pytest

from story_content import STORY_ENCHANTMENT_BOOKS, STORY_RULES
from story_engine import (
    StoryActionError,
    _card_values,
    _gain_enchantment_book,
    _new_card,
    _player_raw_damage,
    _reward_rarity,
    _start_combat,
    apply_story_action,
)
from story_mode import build_initial_story_state


def _combat_state(seed='enchantment-books', enemies=None):
    state = build_initial_story_state(seed)
    _start_combat(
        state,
        {'type': 'combat'},
        seed,
        [],
        encounter_override=enemies or [{'def_id': 'soldier_ant'}],
    )
    state['combat']['hand'] = []
    state['combat']['draw_pile'] = []
    state['combat']['discard_pile'] = []
    state['combat']['elixir'] = 99
    state['combat']['magic'] = 99
    return state


def _book(state, book_id):
    events = []
    return _gain_enchantment_book(state, book_id, events, source='test')


def _hand_card(state, card_id):
    card = _new_card(state, card_id)
    state['combat']['hand'].append(card)
    return card


def test_all_workbook_enchantment_books_have_story_assets():
    assert len(STORY_ENCHANTMENT_BOOKS) == 29
    assert STORY_RULES['enchantment_book_slots'] == 3
    for definition in STORY_ENCHANTMENT_BOOKS.values():
        assert definition['rarity'] in {'common', 'rare', 'ultra'}
        assert definition['script']
        assert definition['image_url'].startswith('/static/assets/story-enchantment-books/')


def test_book_can_be_discarded_outside_combat():
    state = build_initial_story_state('discard-book')
    book = _book(state, 'sharp')
    state, events = apply_story_action(
        state,
        'discard_enchantment_book',
        {'book_instance_id': book['instance_id']},
        'discard-book',
    )
    assert state['player']['enchantment_books'] == []
    assert any(event['type'] == 'enchantment_book_removed' for event in events)


def test_book_slots_require_an_explicit_replacement():
    state = build_initial_story_state('replace-book')
    held = [_book(state, book_id) for book_id in ('sharp', 'protection', 'efficiency')]
    with pytest.raises(StoryActionError) as exc:
        _gain_enchantment_book(state, 'warp', [], source='test')
    assert exc.value.code == 'ENCHANTMENT_BOOK_SLOTS_FULL'
    gained = _gain_enchantment_book(
        state,
        'warp',
        [],
        source='test',
        replace_instance_id=held[1]['instance_id'],
    )
    assert len(state['player']['enchantment_books']) == 3
    assert gained['book_id'] == 'warp'
    assert held[1] not in state['player']['enchantment_books']


def test_sharp_and_sweeping_books_modify_and_consume():
    state = _combat_state('book-card-modifiers', enemies=[
        {'def_id': 'soldier_ant'},
        {'def_id': 'soldier_ant'},
    ])
    card = _hand_card(state, 'basic')
    sharp = _book(state, 'sharp')
    state, _ = apply_story_action(
        state,
        'use_enchantment_book',
        {'book_instance_id': sharp['instance_id'], 'card_instance_id': card['instance_id']},
        'book-card-modifiers',
    )
    card = state['combat']['hand'][0]
    base_damage = next(
        effect['amount']
        for effect in STORY_ENCHANTMENT_BOOKS.values()
        if effect['script'] == 'damage_bonus'
    )
    assert card['modifiers']['damage_bonus'] == base_damage
    assert state['player']['enchantment_books'] == []

    sweeping = _book(state, 'sweeping_blade')
    state, _ = apply_story_action(
        state,
        'use_enchantment_book',
        {'book_instance_id': sweeping['instance_id'], 'card_instance_id': card['instance_id']},
        'book-card-modifiers-wide',
    )
    values = _card_values(state['combat']['hand'][0])
    assert 'wide' in values['tags']


def test_protection_bonus_is_cleared_after_the_enchanted_card_is_used():
    state = _combat_state('book-protection')
    card = _hand_card(state, 'rose')
    book = _book(state, 'protection')
    state, _ = apply_story_action(
        state,
        'use_enchantment_book',
        {'book_instance_id': book['instance_id'], 'card_instance_id': card['instance_id']},
        'book-protection',
    )
    card = state['combat']['hand'][0]
    expected = sum(
        int(effect.get('amount') or 0)
        for effect in _card_values(card)['effects']
        if effect.get('type') == 'shield'
    )
    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id']},
        'book-protection-play',
    )
    assert state['combat']['shield'] == expected
    played = state['combat']['discard_pile'][-1]
    assert 'enchantment_shield_bonus_once' not in played.get('modifiers', {})


def test_magic_yggdrasil_auto_consumes_on_lethal_damage():
    state = _combat_state('book-yggdrasil')
    state['player']['health'] = 5
    _book(state, 'magic_yggdrasil')
    events = []
    _player_raw_damage(state, 99, events, 'test')
    assert state['player']['health'] == 5
    assert state['combat']['invincible'] == 1
    assert state['combat']['regeneration'] == 8
    assert state['player']['enchantment_books'] == []
    assert any(event['type'] == 'enchantment_book_triggered' for event in events)


def test_armor_break_clears_shield_before_damage_and_prediction():
    state = _combat_state('book-armor-break')
    enemy = state['combat']['enemies'][0]
    enemy['shield'] = 50
    card = _hand_card(state, 'basic')
    book = _book(state, 'armor_break')
    state, _ = apply_story_action(
        state,
        'use_enchantment_book',
        {'book_instance_id': book['instance_id'], 'card_instance_id': card['instance_id']},
        'book-armor-break-use',
    )
    card = state['combat']['hand'][0]
    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': enemy['id']},
        'book-armor-break-play',
    )
    assert any(
        event['type'] == 'status_cleared'
        and event.get('status') == 'shield'
        and event.get('source') == 'armor_break'
        for event in events
    )
    assert state['combat']['enemies'][0]['health'] < enemy['health']


def test_target_status_enchantment_applies_to_a_skill_card_self_target():
    state = _combat_state('book-self-target-status')
    card = _hand_card(state, 'rose')
    book = _book(state, 'repel')
    state, _ = apply_story_action(
        state,
        'use_enchantment_book',
        {
            'book_instance_id': book['instance_id'],
            'card_instance_id': card['instance_id'],
        },
        'book-self-target-status-use',
    )
    card = state['combat']['hand'][0]
    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id']},
        'book-self-target-status-play',
    )
    assert state['combat']['weak'] == 4


def test_card_reward_pity_increments_and_resets():
    state = build_initial_story_state('reward-pity')
    initial = STORY_RULES['rare_card_pity_initial']
    rarity = _reward_rarity(state, 'combat', random.Random(0))
    assert rarity != 'ultra'
    assert state['rare_card_pity_offset'] == pytest.approx(initial + 0.01)
    state['rare_card_pity_offset'] = STORY_RULES['rare_card_pity_cap']
    rarity = _reward_rarity(state, 'combat', random.Random(1))
    assert rarity == 'ultra'
    assert state['rare_card_pity_offset'] == pytest.approx(initial)


def test_lunatic_card_reward_pity_uses_half_increment():
    state = build_initial_story_state('reward-pity-lunatic')
    state['difficulty'] = 'lunatic'
    _reward_rarity(state, 'combat', random.Random(0))
    assert state['rare_card_pity_offset'] == pytest.approx(
        STORY_RULES['rare_card_pity_initial'] + 0.005
    )
