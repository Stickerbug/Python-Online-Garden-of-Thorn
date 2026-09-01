from copy import deepcopy
from pathlib import Path

import story_coop_combat
import story_coop_live
from story_coop_combat import damage_coop_party_from_enemy
from story_coop_live import project_coop_state_for_viewer, validate_coop_live_state
from tests.test_story_coop_progression import (
    _current_first_combat_state,
    _current_initial_map_state,
    _current_room_state,
    _journey_action,
)


def _gain(state, seat, book_id):
    events = []
    return story_coop_live._gain_coop_enchantment_book(
        state,
        seat,
        book_id,
        events,
        source='test',
    )


def test_coop_books_are_private_and_can_be_discarded_outside_combat():
    state = _current_initial_map_state()
    book = _gain(state, 0, 'sharp')
    validate_coop_live_state(state)

    leader = project_coop_state_for_viewer(state, 101)
    member = project_coop_state_for_viewer(state, 202)
    assert leader['players'][0]['enchantment_books'] == [book]
    assert leader['players'][1]['enchantment_books'] is None
    assert member['players'][0]['enchantment_books'] is None

    discarded, events, _ = _journey_action(
        state,
        101,
        'discard-coop-book-0001',
        'discard_enchantment_book',
        {'book_instance_id': book['instance_id']},
    )
    assert discarded['players']['0']['enchantment_books'] == []
    assert any(event['type'] == 'coop_enchantment_book_removed' for event in events)


def test_coop_book_can_enchant_a_card_during_combat():
    state = _current_first_combat_state()
    seat_state = state['combat']['seat_states']['0']
    card = next(
        card
        for card in seat_state['hand']
        if story_coop_live._card_values(card)[1]['type'] == 'thorn'
    )
    book = _gain(state, 0, 'sharp')
    events = []
    story_coop_live.resolve_intro_coop_action(
        state,
        0,
        'use_enchantment_book',
        {
            'book_instance_id': book['instance_id'],
            'card_instance_id': card['instance_id'],
        },
        'coop-progression-seed',
        events,
    )
    assert card['modifiers']['damage_bonus'] == 15
    assert state['players']['0']['enchantment_books'] == []
    assert any(event['type'] == 'coop_enchantment_book_used' for event in events)


def test_coop_magic_yggdrasil_prevents_lethal_enemy_damage():
    state = _current_first_combat_state()
    state['players']['0']['health'] = 1
    _gain(state, 0, 'magic_yggdrasil')
    enemy = state['combat']['enemies'][0]
    enemy['intent'] = {'kind': 'attack', 'amount': 99, 'hits': 1, 'target_seat': 0}
    events = []
    damage_coop_party_from_enemy(
        state,
        enemy=enemy,
        amount=99,
        hits=1,
        events=events,
    )
    assert state['players']['0']['health'] == 1
    assert state['players']['0']['enchantment_books'] == []
    assert state['combat']['seat_states']['0']['statuses']['invincible'] == 1
    assert state['combat']['seat_states']['0']['statuses']['regeneration'] == 8


def test_coop_puncture_replays_attack_after_a_kill():
    state = _current_first_combat_state()
    first = state['combat']['enemies'][0]
    first['health'] = 1
    first['shield'] = 0
    second = deepcopy(first)
    second['id'] = f'{first["id"]}-second'
    second['health'] = 1
    state['combat']['enemies'].append(second)
    seat_state = state['combat']['seat_states']['0']
    card = next(
        card
        for card in seat_state['hand']
        if story_coop_live._card_values(card)[1]['type'] == 'thorn'
    )
    card.setdefault('modifiers', {})['enchantment_repeat_on_kill'] = True
    events = []

    story_coop_live.resolve_intro_coop_action(
        state,
        0,
        'play_card',
        {
            'card_instance_id': card['instance_id'],
            'target_enemy_id': first['id'],
        },
        'coop-puncture-seed',
        events,
    )

    assert [enemy['health'] for enemy in state['combat']['enemies']] == [0, 0]
    assert any(event['type'] == 'coop_card_replayed' for event in events)


def test_coop_fire_ticks_before_enemy_action_without_using_shield():
    state = _current_first_combat_state()
    enemy = state['combat']['enemies'][0]
    enemy.update({
        'health': 20,
        'shield': 9,
        'fire': 6,
        'intent': {'kind': 'idle'},
    })
    events = []

    story_coop_combat._resolve_enemy_phase(
        state,
        'coop-fire-seed',
        events,
    )

    assert enemy['health'] == 14
    assert enemy['shield'] == 9
    fire_event = next(event for event in events if event.get('source') == 'fire')
    assert fire_event['amount'] == 6


def test_coop_attract_lightning_uses_static_and_ignores_shield_on_trigger():
    state = _current_first_combat_state()
    enemy = state['combat']['enemies'][0]
    enemy.update({'health': 100, 'shield': 30, 'static': 0})
    cards = [
        card
        for card in state['combat']['seat_states']['0']['hand']
        if story_coop_live._card_values(card)[1]['type'] == 'thorn'
    ]
    assert len(cards) >= 2
    events = []
    for card in cards[:2]:
        card.setdefault('modifiers', {})['enchantment_electric_damage'] = 15
        story_coop_live.resolve_intro_coop_action(
            state,
            0,
            'play_card',
            {
                'card_instance_id': card['instance_id'],
                'target_enemy_id': enemy['id'],
            },
            'coop-electric-book-seed',
            events,
        )

    assert enemy['static'] == 0
    triggered = next(
        event
        for event in events
        if event.get('type') == 'enemy_damage'
        and event.get('source') == 'attract_lightning'
    )
    assert triggered['blocked'] == 0
    assert triggered['amount'] == 30


def test_coop_target_status_enchantment_uses_self_for_skill_and_immunity_blocks_it():
    state = _current_first_combat_state()
    seat_state = state['combat']['seat_states']['0']
    card = next(
        card
        for card in seat_state['hand']
        if story_coop_live._card_values(card)[1]['type'] == 'bloom'
    )
    card.setdefault('modifiers', {})['enchantment_weak_once'] = 4
    seat_state['statuses']['negative_status_immunity'] = 1
    events = []

    story_coop_live.resolve_intro_coop_action(
        state,
        0,
        'play_card',
        {'card_instance_id': card['instance_id']},
        'coop-self-status-seed',
        events,
    )

    assert seat_state['statuses']['negative_status_immunity'] == 0
    assert seat_state['statuses'].get('weak', 0) == 0
    assert any(event['type'] == 'coop_status_blocked' for event in events)


def test_coop_snatch_opens_two_private_card_reward_rounds():
    state = _current_first_combat_state()
    for enemy in state['combat']['enemies']:
        enemy['health'] = 0
    state['combat'].update({
        'turn': story_coop_combat.COOP_COMBAT_ENDED,
        'outcome': 'victory',
        'double_card_reward': True,
    })
    state['coordination']['combat_ready_seats'] = []
    state['coordination']['combat_ready_round'] = None

    story_coop_live.advance_coop_after_victory(
        state,
        run_seed='coop-snatch-seed',
    )
    reward = state['rewards_by_player']['0']
    assert reward['card_round_index'] == 1
    assert reward['card_round_total'] == 2
    first_options = deepcopy(reward['options'])
    events = []
    story_coop_live._resolve_reward_choice(
        state,
        0,
        {
            'reward_id': reward['reward_id'],
            'choice_kind': 'card',
            'card_id': first_options[0]['card_id'],
        },
        'coop-snatch-seed',
        events,
    )
    assert reward['card_status'] == 'pending'
    assert reward['card_round_index'] == 2
    assert reward['options'] != first_options
    assert reward['card_choices'][0]['card_id'] == first_options[0]['card_id']

    story_coop_live._resolve_reward_choice(
        state,
        0,
        {
            'reward_id': reward['reward_id'],
            'choice_kind': 'card',
            'card_id': reward['options'][0]['card_id'],
        },
        'coop-snatch-seed',
        events,
    )
    assert reward['card_status'] == 'resolved'
    assert len(reward['card_choices']) == 2


def test_coop_shop_has_one_book_of_each_rarity_and_can_sell_one():
    state = _current_room_state('shop')
    offers = state['room_states_by_player']['0']['offers']
    books = [offer for offer in offers if offer.get('kind') == 'enchantment_book']
    assert len(books) == 3
    assert {
        story_coop_live.STORY_ENCHANTMENT_BOOKS[offer['book_id']]['rarity']
        for offer in books
    } == {'common', 'rare', 'ultra'}

    common = next(
        offer for offer in books
        if story_coop_live.STORY_ENCHANTMENT_BOOKS[offer['book_id']]['rarity'] == 'common'
    )
    bought, _, _ = _journey_action(
        state,
        101,
        'buy-coop-book-0001',
        'shop_buy',
        {'room_id': state['room']['id'], 'offer_id': common['offer_id']},
    )
    assert bought['players']['0']['enchantment_books'][0]['book_id'] == common['book_id']


def test_pvp_frontend_and_rules_do_not_reference_enchantment_books():
    root = Path(__file__).resolve().parents[1]
    for relative in (
        'static/js/game.js',
        'templates/index.html',
        'game_engine.py',
        'game_engine_2v2.py',
        'pvp_economy.py',
    ):
        text = (root / relative).read_text(encoding='utf-8')
        assert 'enchantment_book' not in text
        assert '附魔书' not in text
