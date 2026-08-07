import copy

from story_content import STORY_BLESSINGS, STORY_CARDS, STORY_ENEMIES
from story_engine import (
    _boss_relic_choices,
    _check_combat_end,
    _enemy_physical_damage,
    _gain_relic,
    _make_story_event,
    _next_enemy_move,
    _reward_choices,
    _start_combat,
    _turn_boundary,
    apply_story_action,
)
from story_mode import build_initial_story_state, generate_story_map


def _started_state(seed='story-redesign', difficulty='normal', biome='garden'):
    state = build_initial_story_state(seed)
    state, _ = apply_story_action(
        state,
        'start_journey',
        {'biome': biome, 'difficulty': difficulty},
        seed,
    )
    return state


def _event_state(event_id, seed='event-state'):
    original = _started_state(seed)
    for index in range(500):
        state = copy.deepcopy(original)
        room = _make_story_event(state, f'{seed}:{index}')
        if room.get('event_id') != event_id:
            continue
        state['phase'] = 'room'
        state['room'] = room
        return state
    raise AssertionError(f'event was never generated: {event_id}')


def test_journey_setup_offers_three_blessings_and_applies_hard_start():
    state = _started_state('hard-setup', difficulty='hard')
    assert state['phase'] == 'blessing'
    assert len(state['blessing_options']) == 3
    assert len(set(state['blessing_options'])) == 3
    assert set(state['blessing_options']) <= set(STORY_BLESSINGS)
    assert [card['def_id'] for card in state['player']['deck']].count('corruption') == 1


def test_second_floor_uses_the_general_non_crossing_connection_rules():
    for index in range(100):
        story_map = generate_story_map(f'floor-two-{index}', 1, 'garden')
        first_floor = story_map['floors'][0]['nodes']
        second_floor = story_map['floors'][1]['nodes']
        outgoing = [
            edge for edge in story_map['edges']
            if edge['from'] == first_floor[0]['id']
        ]
        assert {edge['to'] for edge in outgoing} == {node['id'] for node in second_floor}


def test_enemy_builder_applies_lunatic_values_and_stacking_curses():
    state = _started_state('curse-enemy', difficulty='lunatic', biome='desert')
    state['curses'] = {'vitality': 1, 'ward': 2}
    _start_combat(
        state,
        {'type': 'combat'},
        'curse-enemy',
        [],
        encounter_override=[{'def_id': 'cactus'}],
    )
    enemy = state['combat']['enemies'][0]
    assert enemy['max_health'] == STORY_ENEMIES['cactus']['lunatic_max_health'] * 3
    assert enemy['reflection'] == 3
    assert enemy['negative_status_immunity'] == 6


def test_repeated_enemy_move_orders_are_not_limited_to_two_entries():
    state = _started_state('move-order', biome='ocean')
    _start_combat(
        state,
        {'type': 'combat'},
        'move-order',
        [],
        encounter_override=[{'def_id': 'waterspout'}],
    )
    enemy = state['combat']['enemies'][0]
    order = []
    for step in range(4):
        enemy['move_step'] = step
        order.append(STORY_ENEMIES['waterspout']['moves'].index(_next_enemy_move(state, enemy)))
    assert order == [0, 1, 0, 2]


def test_bandage_and_shiny_ladybug_survival_rules_are_distinct():
    state = _started_state('enemy-survival', biome='desert')
    _start_combat(
        state,
        {'type': 'boss'},
        'enemy-survival',
        [],
        encounter_override=[
            {'def_id': 'bandage_beetle'},
            {'def_id': 'shiny_ladybug'},
        ],
    )
    beetle, ladybug = state['combat']['enemies']
    events = []
    _enemy_physical_damage(state, beetle, 999, 1, events, 'test')
    _enemy_physical_damage(state, ladybug, 999, 1, events, 'test')
    assert beetle['health'] == 1
    assert beetle['forced_move_index'] == 2
    assert ladybug['health'] == 1
    assert ladybug['yggdrasil_revive_pending'] is True
    assert ladybug['invincible'] == 1


def test_turn_boundary_resolves_shelter_sturdy_and_delayed_charge():
    state = _started_state('boundary-effects', biome='desert')
    _start_combat(
        state,
        {'type': 'combat'},
        'boundary-effects',
        [],
        encounter_override=[{'def_id': 'palm_tree'}, {'def_id': 'rain_frog'}],
    )
    state['player']['health'] = state['player']['max_health'] = 999
    state['combat']['enemies'][1]['shield'] = 7
    state['combat']['enemies'][1]['sturdy'] = 1
    state['combat']['delayed_hand_charge'] = 2
    events = []
    _turn_boundary(state, 'boundary-effects', events)
    palm, frog = state['combat']['enemies'][:2]
    assert palm['shield'] >= palm['shelter']
    assert frog['shield'] >= 7 + palm['shelter']
    assert frog['sturdy'] == 0
    assert all(card.get('modifiers', {}).get('charge') == 2 for card in state['combat']['hand'])


def test_story_event_pool_contains_the_new_event_rooms():
    expected = {
        'auction',
        'hive_visit',
        'adventure_master',
        'dandelion_seed_event',
        'farm',
        'card_trader',
    }
    seen = set()
    original = _started_state('event-pool')
    for index in range(500):
        state = copy.deepcopy(original)
        seen.add(_make_story_event(state, f'event-pool:{index}')['event_id'])
    assert expected <= seen


def test_auction_upgrade_charges_gold_and_uses_the_shared_upgrade_path():
    state = _event_state('auction', 'auction-upgrade')
    state['player']['gold'] = 100
    card = next(
        card for card in state['player']['deck']
        if STORY_CARDS[card['def_id']].get('upgrade')
    )
    state, events = apply_story_action(
        state,
        'resolve_room',
        {'option': 'auction_honey', 'card_instance_id': card['instance_id']},
        'auction-upgrade',
    )
    upgraded = next(item for item in state['player']['deck'] if item['instance_id'] == card['instance_id'])
    assert upgraded['upgraded'] is True
    assert state['player']['gold'] == 90
    assert any(event['type'] == 'card_upgraded' for event in events)


def test_adventure_master_runs_two_separate_card_rewards():
    state = _event_state('adventure_master', 'adventure-rewards')
    state, _ = apply_story_action(
        state,
        'resolve_room',
        {'option': 'adventure_learn'},
        'adventure-rewards',
    )
    assert state['phase'] == 'reward'
    assert state['reward']['round_index'] == 1
    assert state['reward']['round_total'] == 2
    first_card = state['reward']['cards'][0]['card_id']
    state, _ = apply_story_action(
        state,
        'choose_reward',
        {'reward_type': 'card', 'card_id': first_card},
        'adventure-rewards',
    )
    state, _ = apply_story_action(
        state,
        'choose_reward',
        {'reward_type': 'continue'},
        'adventure-rewards',
    )
    assert state['phase'] == 'reward'
    assert state['reward']['round_index'] == 2
    second_card = state['reward']['cards'][0]['card_id']
    state, _ = apply_story_action(
        state,
        'choose_reward',
        {'reward_type': 'card', 'card_id': second_card},
        'adventure-rewards',
    )
    state, _ = apply_story_action(
        state,
        'choose_reward',
        {'reward_type': 'continue'},
        'adventure-rewards',
    )
    assert state['phase'] == 'map'


def test_card_trader_only_accepts_displayed_cards_and_charges_for_primary_cards():
    state = _event_state('card_trader', 'card-trader')
    state['player']['gold'] = 100
    candidate_id = state['room']['trade_candidates'][0]
    card = next(item for item in state['player']['deck'] if item['instance_id'] == candidate_id)
    original_def_id = card['def_id']
    expected_gold = 50 if STORY_CARDS[original_def_id]['rarity'] == 'primary' else 100
    state, _ = apply_story_action(
        state,
        'resolve_room',
        {'option': 'trade_card', 'card_instance_id': candidate_id},
        'card-trader',
    )
    transformed = next(item for item in state['player']['deck'] if item['instance_id'] == candidate_id)
    assert transformed['def_id'] != original_def_id
    assert state['player']['gold'] == expected_gold


def test_boss_relics_offer_three_choices_and_interactive_relics_queue_work():
    state = _started_state('boss-relics')
    choices = _boss_relic_choices(state, 'boss-relics')
    assert len(choices) == 3
    assert len(set(choices)) == 3

    events = []
    _gain_relic(state, 'sharpen', 'boss-relics', events)
    operation = state['pending_deck_operations'][0]
    assert operation['kind'] == 'upgrade'
    assert operation['minimum'] == operation['maximum'] == 2
    state, _ = apply_story_action(
        state,
        'resolve_deck_operation',
        {'selected_card_ids': operation['candidate_ids'][:2]},
        'boss-relics',
    )
    assert sum(bool(card.get('upgraded')) for card in state['player']['deck']) >= 2


def test_cowardly_defense_filters_bloom_rewards_and_peaceful_mind_is_optional():
    state = _started_state('boss-restrictions')
    state['player']['relics'].append('coward_defense')
    for index in range(20):
        choices = _reward_choices(state, f'boss-restrictions:{index}')
        assert all(STORY_CARDS[item['card_id']]['type'] != 'bloom' for item in choices)

    events = []
    _gain_relic(state, 'peaceful_mind', 'boss-restrictions', events)
    operation = state['pending_deck_operations'][0]
    assert operation['kind'] == 'remove'
    assert operation['minimum'] == 0
    state, _ = apply_story_action(
        state,
        'resolve_deck_operation',
        {'selected_card_ids': []},
        'boss-restrictions',
    )
    assert 'pending_deck_operations' not in state
