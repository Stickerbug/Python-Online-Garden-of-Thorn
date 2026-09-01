import copy

import pytest

import story_engine
from story_content import (
    STORY_BLESSINGS,
    STORY_BOSS_RELIC_IDS,
    STORY_CARDS,
    STORY_DIFFICULTIES,
    STORY_EASY_RELIC_IDS,
    STORY_ENCOUNTERS,
    STORY_ENEMIES,
    STORY_EVENTS,
    STORY_RELICS,
    STORY_REWARD_CARD_IDS,
    STORY_RULES,
    STORY_SHOP_CARD_IDS,
    STORY_STATUSES,
)
from story_engine import (
    StoryActionError,
    _activate_player_blind,
    _boss_relic_choices,
    _check_combat_end,
    _encounter_specs,
    _end_turn,
    _enemy_physical_damage,
    _enemy_raw_damage,
    _gain_relic,
    _is_card_playable,
    _make_shop,
    _make_story_event,
    _new_card,
    _next_enemy_move,
    _player_damage,
    _player_raw_damage,
    _resolve_player_death,
    _resolve_enemy_effect,
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


def test_negative_status_immunity_reuses_multiplayer_status_immunity_icon():
    assert STORY_STATUSES['negative_status_immunity']['image_url'] == (
        '/static/assets/status-icons/status_immune.svg'
    )


def test_stun_is_an_action_and_bypasses_negative_status_immunity():
    state = _started_state('stun-action')
    _start_combat(
        state,
        {'type': 'combat'},
        'stun-action',
        [],
        encounter_override=[{'def_id': 'cicada'}],
    )
    enemy = state['combat']['enemies'][0]
    enemy['negative_status_immunity'] = 2
    status_count_before = story_engine._status_count(enemy)
    events = []

    story_engine._apply_status(state, enemy, 'stun', 2, events, source='test')

    assert STORY_STATUSES['stun']['category'] == 'action'
    assert enemy['stun'] == 2
    assert enemy['negative_status_immunity'] == 2
    assert story_engine._status_count(enemy) == status_count_before
    assert any(
        event.get('type') == 'status'
        and event.get('status') == 'stun'
        and event.get('category') == 'action'
        for event in events
    )
    assert not any(event.get('type') == 'status_blocked' for event in events)


def test_miracle_spends_one_visible_use_before_the_second_card_only():
    state = _started_state('miracle-counter', biome='desert')
    _start_combat(
        state,
        {'type': 'combat'},
        'miracle-counter',
        [],
        encounter_override=[{'def_id': 'cicada'}],
    )
    combat = state['combat']
    combat['opening_redraw_pending'] = False
    combat['elixir'] = 99
    combat['hand'] = [
        _new_card(state, 'rose'),
        _new_card(state, 'rose'),
        _new_card(state, 'rose'),
    ]
    first_id, second_id, third_id = [card['instance_id'] for card in combat['hand']]

    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': first_id},
        'miracle-counter:first',
    )
    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': second_id},
        'miracle-counter:second',
    )

    enemy = state['combat']['enemies'][0]
    assert enemy['miracle'] == 2
    assert enemy['evade'] == 1
    miracle_events = [
        event for event in events
        if event.get('effect_kind') == 'miracle'
    ]
    assert len(miracle_events) == 1
    assert miracle_events[0]['before'] == 3
    assert miracle_events[0]['after'] == 2

    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': third_id},
        'miracle-counter:third',
    )
    assert state['combat']['enemies'][0]['miracle'] == 2
    assert not any(event.get('effect_kind') == 'miracle' for event in events)


def test_corruption_is_eternal_and_cannot_be_removed_from_the_deck():
    state = _started_state('eternal-corruption')
    corruption = _new_card(state, 'corruption')

    assert 'eternal' in STORY_CARDS['corruption']['tags']
    with pytest.raises(StoryActionError) as exc_info:
        story_engine._ensure_card_removable(corruption)
    assert exc_info.value.code == 'CARD_ETERNAL'


def test_updated_card_rarities_and_tags_match_the_story_design():
    assert STORY_CARDS['crystal_leaf']['rarity'] == 'ultra'
    assert STORY_CARDS['antibody']['tags'] == ()


def test_journey_setup_offers_three_blessings_and_applies_hard_start():
    state = _started_state('hard-setup', difficulty='hard')
    assert state['phase'] == 'blessing'
    assert len(state['blessing_options']) == 3
    assert len(set(state['blessing_options'])) == 3
    assert set(state['blessing_options']) <= set(STORY_BLESSINGS)
    assert [card['def_id'] for card in state['player']['deck']].count('corruption') == 1


def test_easy_difficulty_uses_normal_map_and_precedes_blessing_with_a_talent():
    assert list(STORY_DIFFICULTIES) == ['easy', 'normal', 'hard', 'lunatic']
    assert [STORY_DIFFICULTIES[key]['abbreviation']['en'] for key in STORY_DIFFICULTIES] == [
        'E', 'N', 'H', 'L',
    ]
    easy_map = generate_story_map('easy-map', 1, 'garden', 'easy')
    normal_map = generate_story_map('easy-map', 1, 'garden', 'normal')
    assert easy_map['floors'] == normal_map['floors']
    assert easy_map['edges'] == normal_map['edges']

    state = _started_state('easy-setup', difficulty='easy')
    assert state['phase'] == 'easy_relic'
    assert len(state['easy_relic_options']) == 3
    assert set(state['easy_relic_options']) <= set(STORY_EASY_RELIC_IDS)
    selected = state['easy_relic_options'][0]
    state, events = apply_story_action(
        state,
        'choose_easy_relic',
        {'relic_id': selected},
        'easy-setup',
    )
    assert state['phase'] == 'blessing'
    assert selected in state['player']['relics']
    assert any(event.get('type') == 'easy_relic_chosen' for event in events)


def test_lunatic_stage_three_has_two_consecutive_boss_floors():
    story_map = generate_story_map('lunatic-stage-three', 3, 'ocean', 'lunatic')
    assert story_map['floor_count'] == 17
    assert len(story_map['floors']) == 17
    assert {node['type'] for node in story_map['floors'][15]['nodes']} == {'boss'}
    assert {node['type'] for node in story_map['floors'][16]['nodes']} == {'boss'}
    assert story_map['floors'][15]['width'] == 1
    assert story_map['floors'][16]['width'] == 1


def test_easy_talents_apply_draw_heal_resource_retention_and_card_upgrades():
    state = _started_state('easy-talents')
    state['player']['relics'].extend([
        'easy_miracle',
        'easy_peace',
        'easy_study',
        'easy_tiger',
        'easy_godhood',
    ])
    state['player']['health'] -= 10
    _start_combat(
        state,
        {'type': 'combat'},
        'easy-talents',
        [],
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    assert state['combat']['elixir'] == state['player']['max_elixir'] + 4
    assert len(state['combat']['hand']) == 7
    assert state['player']['health'] == state['player']['max_health'] - 7

    state['combat']['elixir'] = 2
    _turn_boundary(state, 'easy-talents:next', [])
    assert state['combat']['elixir'] == state['player']['max_elixir'] + 3

    gained = story_engine._gain_deck_card(state, 'heavy', [], source='test')
    assert gained['upgraded'] is True


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


def test_solo_story_unlocks_connected_nodes_and_waits_for_player_choice():
    seed = 'manual-map-choice'
    state = _started_state(seed)
    first_node_id = state['current_node_id']
    state['blessing_options'] = ['max_health']

    state, events = apply_story_action(
        state,
        'choose_blessing',
        {'blessing_id': 'max_health'},
        seed,
    )

    first_choices = {
        edge['to'] for edge in state['map']['edges']
        if edge['from'] == first_node_id
    }
    available = {
        node['id']
        for floor in state['map']['floors']
        for node in floor['nodes']
        if node['status'] == 'available'
    }
    assert state['phase'] == 'map'
    assert len(first_choices) > 1
    assert available == first_choices
    assert not any(event.get('type') == 'node_auto_selected' for event in events)

    second_floor = state['map']['floors'][1]['nodes']
    selected = max(
        second_floor,
        key=lambda node: sum(
            edge['from'] == node['id'] for edge in state['map']['edges']
        ),
    )
    next_choices = {
        edge['to'] for edge in state['map']['edges']
        if edge['from'] == selected['id']
    }
    assert len(next_choices) > 1
    for node in second_floor:
        node['status'] = 'available' if node is selected else 'locked'
    state['current_node_id'] = selected['id']
    state['current_floor'] = selected['floor']
    state['phase'] = 'combat'
    state['combat'] = {'equipment': []}
    edges_before = copy.deepcopy(state['map']['edges'])
    later_events = []

    story_engine._complete_current_node(state, later_events, seed)

    available_next = {
        node['id']
        for node in state['map']['floors'][2]['nodes']
        if node['status'] == 'available'
    }
    assert state['phase'] == 'map'
    assert available_next == next_choices
    assert state['map']['edges'] == edges_before
    assert not any(event.get('type') == 'node_auto_selected' for event in later_events)


def test_enemy_builder_ignores_removed_legacy_run_curses():
    state = _started_state('legacy-curse-enemy', difficulty='lunatic', biome='desert')
    state['curses'] = {'vitality': 1, 'affliction': 2}
    _start_combat(
        state,
        {'type': 'combat'},
        'legacy-curse-enemy',
        [],
        encounter_override=[{'def_id': 'cactus'}],
    )
    enemy = state['combat']['enemies'][0]
    assert enemy['max_health'] == 31
    assert enemy['reflection'] == 3
    assert int(enemy.get('negative_status_immunity') or 0) == 0


def test_removed_run_curses_are_dropped_on_the_next_action():
    state = _started_state('removed-curse-normalization', biome='desert')
    state['curses'] = {'affliction': 2, 'ward': 1}
    state['phase'] = 'stage_choice'
    state['room'] = {
        'type': 'stage_choice',
        'stage': 2,
        'biomes': ['desert'],
        'curses': ['affliction'],
        'allow_repeated_curses': True,
    }

    state, _ = apply_story_action(
        state,
        'choose_stage',
        {'biome': 'desert'},
        'removed-curse-normalization',
    )

    assert 'curses' not in state
    assert state['stage'] == 2


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


def test_desert_centipede_segments_start_on_distinct_intents_and_hidden_values():
    state = _started_state('desert-centipede-opening', biome='desert')
    encounter = STORY_ENCOUNTERS['desert']['boss'][0]
    _start_combat(
        state,
        {'type': 'boss'},
        'desert-centipede-opening',
        [],
        encounter_override=list(encounter),
    )
    enemies = state['combat']['enemies']
    assert [int(enemy.get('hidden') or 0) for enemy in enemies] == [1, 0, 2]
    assert [
        STORY_ENEMIES['desert_centipede']['moves'].index(_next_enemy_move(state, enemy))
        for enemy in enemies
    ] == [0, 1, 2]
    assert STORY_ENEMIES['desert_centipede'].get('traits') == ()


def test_shipwreck_wreckage_keeps_three_distinct_death_summons():
    state = _started_state('shipwreck-wreckage', biome='ocean')
    _start_combat(
        state,
        {'type': 'boss'},
        'shipwreck-wreckage',
        [],
        encounter_override=[{'def_id': 'shipwreck'}],
    )
    shipwreck = state['combat']['enemies'][0]
    move = STORY_ENEMIES['shipwreck']['moves'][0]
    _resolve_enemy_effect(
        state,
        shipwreck,
        move['effects'][0],
        move,
        'shipwreck-wreckage',
        [],
    )
    wreckage = [
        enemy
        for enemy in state['combat']['enemies']
        if enemy['def_id'] == 'wreckage'
    ]
    assert [enemy['death_summon'] for enemy in wreckage] == [
        'crab',
        'lily_pad',
        'urchin',
    ]


def test_fearless_pain_only_reduces_health_loss_after_shield():
    state = _started_state('fearless-pain')
    state['player']['relics'].append('fearless_pain')
    _start_combat(
        state,
        {'type': 'combat'},
        'fearless-pain',
        [],
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    state['player']['health'] = 50
    state['combat']['shield'] = 5
    _player_damage(
        state,
        4,
        2,
        [],
        'test',
        state['combat']['enemies'][0],
    )
    assert state['combat']['shield'] == 0
    assert state['player']['health'] == 48
    _player_raw_damage(state, 4, [], 'test')
    assert state['player']['health'] == 45


def test_frenzy_doubles_attacks_and_requires_attacks_to_be_played_first():
    state = _started_state('frenzy-relic')
    state['player']['relics'].append('frenzy_relic')
    _start_combat(
        state,
        {'type': 'combat'},
        'frenzy-relic',
        [],
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    combat = state['combat']
    combat['opening_redraw_pending'] = False
    enemy = combat['enemies'][0]
    enemy['shield'] = 0
    before = enemy['health']
    _enemy_physical_damage(state, enemy, 4, 1, [], 'test')
    assert before - enemy['health'] == 8
    before = enemy['health']
    _enemy_raw_damage(state, enemy, 3, [], 'test', player_caused=True)
    assert before - enemy['health'] == 6

    attack = _new_card(state, 'basic')
    skill = _new_card(state, 'rose')
    combat['hand'] = [attack, skill]
    combat['elixir'] = combat['magic'] = 99
    assert not _is_card_playable(state, skill)
    combat['hand'].remove(attack)
    assert _is_card_playable(state, skill)
    assert 'frenzy_relic' in STORY_BOSS_RELIC_IDS


def test_stacked_frenzy_multiplies_physical_and_raw_damage_consistently():
    state = _started_state('stacked-frenzy-relic')
    state['player']['relics'].extend(['frenzy_relic', 'frenzy_relic'])
    _start_combat(
        state,
        {'type': 'combat'},
        'stacked-frenzy-relic',
        [],
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    enemy = state['combat']['enemies'][0]
    enemy['shield'] = 0

    before = enemy['health']
    _enemy_physical_damage(state, enemy, 3, 1, [], 'test')
    assert before - enemy['health'] == 12

    before = enemy['health']
    _enemy_raw_damage(state, enemy, 2, [], 'test', player_caused=True)
    assert before - enemy['health'] == 8


def test_bandage_and_shiny_ladybug_survival_rules_are_distinct():
    assert STORY_ENEMIES['bandage_beetle']['traits'] == ('bandage',)
    assert STORY_ENEMIES['shiny_ladybug']['traits'] == ('yggdrasil_power',)
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


def test_soul_splitter_extra_turn_cannot_restore_beetle_bandage():
    state = _started_state('soul-splitter-bandage', biome='desert')
    _start_combat(
        state,
        {'type': 'combat'},
        'soul-splitter-bandage',
        [],
        encounter_override=[{'def_id': 'bandage_beetle'}],
    )
    combat = state['combat']
    combat['opening_redraw_pending'] = False
    splitter = _new_card(state, 'soul_splitter')
    splitter['turns_equipped'] = 1
    combat['equipment'] = [splitter]
    beetle = combat['enemies'][0]
    beetle['health'] = 5

    _enemy_physical_damage(state, beetle, 10, 1, [], 'first lethal')
    assert beetle['bandage'] == 0
    assert beetle['bandage_triggered'] is True

    _end_turn(state, 'soul-splitter-bandage', [])
    assert combat['turn_kind'] == 'extra'
    assert beetle['bandage'] == 0
    assert beetle['invincible'] == 1

    # Extra player turns do not consume the beetle's protected forced action.
    blocked_events = []
    _enemy_physical_damage(state, beetle, 10, 1, blocked_events, 'blocked lethal')
    assert beetle['health'] == 1

    story_engine._enemy_turn(state, 'soul-splitter-bandage', [])
    assert beetle['invincible'] == 0

    # A durable one-use marker also protects migrated or stale states whose
    # numeric counter was accidentally restored.
    beetle['bandage'] = 1
    events = []
    _enemy_physical_damage(state, beetle, 10, 1, events, 'second lethal')
    assert beetle['health'] <= 0
    assert beetle['bandage'] == 0
    assert not any(event.get('type') == 'enemy_survived' for event in events)


def test_turn_boundary_resolves_shelter_without_expiring_new_turn_defenses():
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
    assert frog['sturdy'] == 1
    assert all(card.get('modifiers', {}).get('charge') == 2 for card in state['combat']['hand'])


def test_rain_frog_grants_player_sturdy_that_preserves_shield_for_one_boundary():
    state = _started_state('rain-frog-sturdy', biome='desert')
    _start_combat(
        state,
        {'type': 'combat'},
        'rain-frog-sturdy',
        [],
        encounter_override=[{'def_id': 'rain_frog'}],
    )
    combat = state['combat']
    frog = combat['enemies'][0]
    move = STORY_ENEMIES['rain_frog']['moves'][0]
    events = []

    _resolve_enemy_effect(
        state,
        frog,
        move['effects'][1],
        move,
        'rain-frog-sturdy:effect',
        events,
    )
    combat['shield'] = 9
    _turn_boundary(state, 'rain-frog-sturdy:boundary', events)

    assert combat['sturdy'] == 0
    assert combat['shield'] >= 9
    assert any(
        event.get('type') == 'status'
        and event.get('target_id') == 'player'
        and event.get('status') == 'sturdy'
        for event in events
    )


def test_enemy_action_shield_survives_until_the_next_enemy_turn():
    state = _started_state('enemy-action-shield')
    _start_combat(
        state,
        {'type': 'combat'},
        'enemy-action-shield',
        [],
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    state['player']['health'] = state['player']['max_health'] = 999
    state['combat']['opening_redraw_pending'] = False
    enemy = state['combat']['enemies'][0]
    enemy['move_index'] = 0
    enemy['shield'] = 0

    _end_turn(state, 'enemy-action-shield:first', [])
    assert enemy['shield'] == 8

    _end_turn(state, 'enemy-action-shield:second', [])
    assert enemy['shield'] == 0


def test_story_event_pool_contains_the_new_event_rooms():
    expected = {
        'auction',
        'hive_visit',
        'adventure_master',
        'dandelion_seed_event',
        'farm',
        'card_trader',
        'coop_garden_crossroads',
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
    assert len(state['room']['trade_candidates']) == 3
    assert 'leave' not in {option['id'] for option in state['room']['choices']}
    state, _ = apply_story_action(
        state,
        'resolve_room',
        {'option': 'trade_card', 'card_instance_id': candidate_id},
        'card-trader',
    )
    transformed = next(item for item in state['player']['deck'] if item['instance_id'] == candidate_id)
    assert transformed['def_id'] != original_def_id
    assert state['player']['gold'] == expected_gold
    assert state['phase'] == 'room'
    assert state['room']['stage_id'] == 'result'
    assert state['room']['choices'][0]['id'] == 'trade_continue'
    assert f'[[card:{original_def_id}]]' in state['room']['body']['zh']
    assert f'[[card:{transformed["def_id"]}]]' in state['room']['body']['zh']
    state, _ = apply_story_action(
        state,
        'resolve_room',
        {'option': 'trade_continue'},
        'card-trader',
    )
    assert state['phase'] == 'map'


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
    shop = _make_shop(state, 'boss-restrictions:shop')
    assert all(
        STORY_CARDS[item['card_id']]['type'] != 'bloom'
        for item in shop['cards']
    )

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


def test_normal_rewards_are_primary_but_shops_can_offer_neutral_cards():
    assert STORY_REWARD_CARD_IDS
    assert all(STORY_CARDS[card_id]['owner'] == 'primary' for card_id in STORY_REWARD_CARD_IDS)
    assert any(STORY_CARDS[card_id]['owner'] == 'neutral' for card_id in STORY_SHOP_CARD_IDS)
    state = _started_state('separate-card-pools')
    shop = _make_shop(state, 'separate-card-pools')
    assert any(item['owner'] == 'neutral' for item in shop['cards'])
    assert all(
        STORY_CARDS[item['card_id']]['owner'] == 'primary'
        for item in _reward_choices(state, 'separate-card-pools')
    )


def test_relic_pools_allow_owned_stackable_items_and_shop_excludes_rich():
    state = _started_state('relic-pool-rules')
    assert 'rich' not in story_engine._natural_relic_pool(state, for_shop=True)
    natural_ids = [
        relic_id
        for relic_id, relic in STORY_RELICS.items()
        if relic.get('rarity') != 'special'
    ]
    state['player']['relics'].extend(natural_ids)
    assert story_engine._random_relic(state, 'relic-pool-rules') in natural_ids
    assert _make_shop(state, 'relic-pool-rules')['relics'][0]['relic_id'] in natural_ids

    state['player']['relics'].extend(STORY_BOSS_RELIC_IDS)
    boss_choices = _boss_relic_choices(state, 'relic-pool-rules')
    assert boss_choices
    assert all(relic_id in STORY_BOSS_RELIC_IDS for relic_id in boss_choices)


def test_elite_encounters_do_not_repeat_until_the_biome_pool_is_exhausted():
    state = _started_state('elite-draw-bag', biome='garden')
    pool_size = len(STORY_ENCOUNTERS['garden']['elite'])
    encounters = []
    for index in range(pool_size):
        specs = _encounter_specs(state, 'elite', f'elite-draw-bag:{index}')
        encounters.append(tuple(spec['def_id'] for spec in specs))

    assert len(set(encounters)) == pool_size
    assert len(state['encounter_history']['elite']['garden']) == pool_size

    _encounter_specs(state, 'elite', 'elite-draw-bag:reset')
    assert len(state['encounter_history']['elite']['garden']) == 1


def test_story_events_do_not_repeat_until_every_eligible_event_is_seen():
    state = _started_state('event-draw-bag', biome='garden')
    event_ids = [
        _make_story_event(state, f'event-draw-bag:{index}')['event_id']
        for index in range(11)
    ]
    assert len(set(event_ids)) == 11

    repeated = _make_story_event(state, 'event-draw-bag:reset')['event_id']
    assert repeated in set(event_ids)
    assert len(state['encounter_history']['event']) == 1


def test_authored_garden_crossroads_uses_canonical_definition_and_effects():
    state = _event_state('coop_garden_crossroads', 'shared-garden-event')
    definition = STORY_EVENTS['coop_garden_crossroads']
    assert state['room']['title'] == definition['title']
    assert state['room']['description'] == definition['description']
    state['player']['health'] = 20
    state['player']['gold'] = 0
    state['player']['relics'] = []

    state, events = apply_story_action(
        state,
        'resolve_room',
        {'option': 'risk'},
        'shared-garden-event:resolve',
    )

    assert state['player']['health'] == 12
    assert state['player']['gold'] == 60
    assert any(
        event.get('type') == 'gold_gained'
        and event.get('amount') == 60
        and event.get('source') == 'coop_garden_crossroads'
        for event in events
    )


def test_story_random_streams_isolate_events_and_loot_from_combat_randomness():
    seed = 'isolated-story-random-streams'
    baseline = _started_state(seed)
    noisy = copy.deepcopy(baseline)

    for _ in range(40):
        story_engine._rng(noisy, seed, 'enemy_move:simulated').random()

    assert noisy['rng_counter'] == baseline['rng_counter'] + 40
    assert _reward_choices(noisy, seed, 'combat') == _reward_choices(
        baseline,
        seed,
        'combat',
    )
    assert story_engine._random_relic(noisy, seed) == story_engine._random_relic(
        baseline,
        seed,
    )
    assert _make_story_event(noisy, seed)['event_id'] == _make_story_event(
        baseline,
        seed,
    )['event_id']


def test_story_random_stream_position_is_restored_with_a_save_snapshot():
    seed = 'restored-story-random-streams'
    snapshot = _started_state(seed)

    first = copy.deepcopy(snapshot)
    first_result = {
        'cards': _reward_choices(first, seed, 'elite'),
        'relic': story_engine._random_relic(first, seed),
        'event': _make_story_event(first, seed)['event_id'],
    }

    restored = copy.deepcopy(snapshot)
    restored_result = {
        'cards': _reward_choices(restored, seed, 'elite'),
        'relic': story_engine._random_relic(restored, seed),
        'event': _make_story_event(restored, seed)['event_id'],
    }

    assert restored_result == first_result
    assert restored['rng_streams'] == first['rng_streams']


def test_events_cannot_convert_to_elites_on_the_first_nine_local_floors(monkeypatch):
    original_rng = story_engine._rng

    class FixedRoll:
        @staticmethod
        def random():
            return 0.16

    def rigged_rng(state, seed, namespace):
        if namespace == 'event_room_type':
            state['rng_counter'] = int(state.get('rng_counter') or 0) + 1
            return FixedRoll()
        return original_rng(state, seed, namespace)

    monkeypatch.setattr(story_engine, '_rng', rigged_rng)

    early = _started_state('early-event-conversion')
    early['current_floor'] = 9
    early_events = []
    story_engine._enter_event_node(early, {'type': 'event'}, 'early-event-conversion', early_events)
    assert (early.get('combat') or {}).get('reward_room_type') != 'elite'
    assert not any(
        event.get('type') == 'event_converted' and event.get('room_type') == 'elite'
        for event in early_events
    )

    late = _started_state('late-event-conversion')
    late['current_floor'] = 10
    late_events = []
    story_engine._enter_event_node(late, {'type': 'event'}, 'late-event-conversion', late_events)
    assert late['phase'] == 'combat'
    assert late['combat']['reward_room_type'] == 'elite'


def test_shop_upgrade_and_remove_share_one_service_slot_and_separate_prices():
    remove_state = _started_state('shop-remove-once')
    remove_state['phase'] = 'room'
    remove_state['player']['gold'] = 999
    remove_state['room'] = _make_shop(remove_state, 'shop-remove-once')
    removed = remove_state['player']['deck'][0]
    remove_state, _ = apply_story_action(
        remove_state,
        'resolve_room',
        {'option': 'remove_card', 'card_instance_id': removed['instance_id']},
        'shop-remove-once',
    )
    assert remove_state['room']['service_used'] is True
    assert remove_state['shop_removals'] == 1
    assert remove_state['shop_upgrades'] == 0
    upgradable = next(
        card for card in remove_state['player']['deck']
        if STORY_CARDS[card['def_id']].get('upgrade')
    )
    with pytest.raises(StoryActionError) as exc_info:
        apply_story_action(
            remove_state,
            'resolve_room',
            {'option': 'upgrade_card', 'card_instance_id': upgradable['instance_id']},
            'shop-remove-once',
        )
    assert exc_info.value.code == 'SHOP_SERVICE_ALREADY_USED'
    next_shop = _make_shop(remove_state, 'shop-after-remove')
    assert next_shop['remove_price'] == 100
    assert next_shop['upgrade_price'] == 50

    upgrade_state = _started_state('shop-upgrade-once')
    upgrade_state['phase'] = 'room'
    upgrade_state['player']['gold'] = 999
    upgrade_state['room'] = _make_shop(upgrade_state, 'shop-upgrade-once')
    upgraded = next(
        card for card in upgrade_state['player']['deck']
        if STORY_CARDS[card['def_id']].get('upgrade')
    )
    upgrade_state, _ = apply_story_action(
        upgrade_state,
        'resolve_room',
        {'option': 'upgrade_card', 'card_instance_id': upgraded['instance_id']},
        'shop-upgrade-once',
    )
    assert upgrade_state['room']['service_used'] is True
    assert upgrade_state['shop_removals'] == 0
    assert upgrade_state['shop_upgrades'] == 1
    next_shop = _make_shop(upgrade_state, 'shop-after-upgrade')
    assert next_shop['remove_price'] == 75
    assert next_shop['upgrade_price'] == 75


def test_exact_active_discard_card_is_unplayable_without_another_card():
    state = _started_state('empty-exile-selection')
    _start_combat(
        state,
        {'type': 'combat'},
        'empty-exile-selection',
        [],
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    combat = state['combat']
    combat['opening_redraw_pending'] = False
    combat['draw_pile'] = []
    combat['discard_pile'] = []
    combat['exile_pile'] = []
    amulet = _new_card(state, 'amulet')
    combat['hand'] = [amulet]
    combat['elixir'] = 10
    target = combat['enemies'][0]
    target['health'] = target['max_health'] = 999

    with pytest.raises(StoryActionError) as error:
        apply_story_action(
            state,
            'play_card',
            {'card_instance_id': amulet['instance_id'], 'target_id': target['id']},
            'empty-exile-selection',
        )

    assert error.value.code == 'CARD_NOT_PLAYABLE'
    assert state['combat']['hand'] == [amulet]
    assert target['health'] == 999


def test_upgraded_fragment_discards_other_card_instead_of_exiling_it():
    state = _started_state('upgraded-fragment-discard')
    _start_combat(
        state,
        {'type': 'combat'},
        'upgraded-fragment-discard',
        [],
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    combat = state['combat']
    combat['opening_redraw_pending'] = False
    combat['draw_pile'] = []
    combat['discard_pile'] = []
    combat['exile_pile'] = []
    fragment = _new_card(state, 'fragment', upgraded=True)
    other = _new_card(state, 'basic')
    combat['hand'] = [fragment, other]

    state, events = apply_story_action(
        state,
        'play_card',
        {
            'card_instance_id': fragment['instance_id'],
            'selected_card_ids': [other['instance_id']],
        },
        'upgraded-fragment-discard',
    )

    assert state['combat']['power'] == 2
    assert other in state['combat']['discard_pile']
    assert other not in state['combat']['exile_pile']
    assert fragment in state['combat']['exile_pile']
    assert any(
        event.get('type') == 'card_discarded'
        and event.get('card_instance_id') == other['instance_id']
        and event.get('reason') == 'active'
        for event in events
    )


def test_blind_consumes_one_stack_and_hides_the_entire_player_turn():
    state = _started_state('story-blind-turn')
    _start_combat(
        state,
        {'type': 'combat'},
        'story-blind-turn',
        [],
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    combat = state['combat']
    combat['opening_redraw_pending'] = False
    state['player']['health'] = state['player']['max_health'] = 999
    combat['blind'] = 2
    events = []

    _activate_player_blind(combat, events)
    assert combat['blind_active'] is True
    assert combat['blind'] == 1

    _end_turn(state, 'story-blind-turn:next', events)
    assert state['phase'] == 'combat'
    assert combat['turn'] == 'player'
    assert combat['blind_active'] is True
    assert combat['blind'] == 0


def test_wreckage_non_burst_death_halves_and_stuns_its_assigned_summon():
    state = _started_state('wreckage-death-hook', biome='ocean')
    _start_combat(
        state,
        {'type': 'combat'},
        'wreckage-death-hook',
        [],
        encounter_override=[{'def_id': 'wreckage', 'death_summon': 'crab'}],
    )
    wreckage = state['combat']['enemies'][0]
    wreckage['health'] = 0
    events = []

    assert _check_combat_end(state, 'wreckage-death-hook', events) is False
    crab = next(enemy for enemy in state['combat']['enemies'] if enemy['def_id'] == 'crab')
    assert crab['max_health'] == 29
    assert crab['health'] == crab['max_health']
    assert crab['stun'] == 1
    assert any(
        event.get('type') == 'enemy_death_trigger'
        and event.get('script') == 'wreckage'
        for event in events
    )


def test_wreckage_burst_death_summons_at_full_health_without_stun():
    state = _started_state('wreckage-burst', biome='ocean')
    _start_combat(
        state,
        {'type': 'combat'},
        'wreckage-burst',
        [],
        encounter_override=[{'def_id': 'wreckage', 'death_summon': 'crab'}],
    )
    wreckage = state['combat']['enemies'][0]
    wreckage['health'] = 0
    wreckage['death_reason'] = 'burst'

    assert _check_combat_end(state, 'wreckage-burst', []) is False
    crab = next(enemy for enemy in state['combat']['enemies'] if enemy['def_id'] == 'crab')
    assert crab['max_health'] == STORY_ENEMIES['crab']['max_health']
    assert crab['health'] == crab['max_health']
    assert crab['stun'] == 0


def test_duplicate_relics_stack_instead_of_becoming_consolation():
    state = _started_state('stacking-relics')
    events = []
    health_before = state['player']['health']
    max_health_before = state['player']['max_health']
    _gain_relic(state, 'ruthless', 'stacking-relics:1', events)
    _gain_relic(state, 'ruthless', 'stacking-relics:2', events)
    _gain_relic(state, 'circulation', 'stacking-relics:3', events)
    _gain_relic(state, 'circulation', 'stacking-relics:4', events)

    assert state['player']['relics'].count('ruthless') == 2
    assert state['player']['relics'].count('circulation') == 2
    assert state['player']['relics'].count('consolation') == 0
    assert state['player']['health'] == health_before
    assert state['player']['max_health'] == max_health_before
    _start_combat(
        state,
        {'type': 'combat'},
        'stacking-relics',
        [],
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    assert state['combat']['power'] == 2


def test_stacked_opening_draw_and_support_effects_use_every_talent_copy():
    grab_state = _started_state('stacked-grab-every-card')
    grab_state['player']['relics'].extend(['grab_every_card', 'grab_every_card'])
    _start_combat(
        grab_state,
        {'type': 'combat'},
        'stacked-grab-every-card',
        [],
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    assert len(grab_state['combat']['hand']) == STORY_RULES['draw_per_turn'] + 2

    support_state = _started_state('stacked-support')
    support_state['player']['relics'].extend(['support', 'support'])
    _start_combat(
        support_state,
        {'type': 'combat'},
        'stacked-support',
        [],
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    assert len(support_state['combat']['hand']) == STORY_RULES['draw_per_turn'] - 2
    assert support_state['combat']['shield'] == 6


def test_stacked_bargaining_uses_multiplicative_prices_and_reprices_current_shop():
    class FixedPriceRng:
        @staticmethod
        def uniform(_minimum, _maximum):
            return 1.0

    state = _started_state('stacked-bargaining')
    state['player']['relics'].extend(['bargaining', 'bargaining'])
    assert story_engine._shop_price(state, 100, FixedPriceRng()) == 25

    shop = _make_shop(state, 'stacked-bargaining:shop')
    assert shop['remove_price'] == 18
    assert shop['upgrade_price'] == 12

    purchase_state = _started_state('buy-second-bargaining')
    purchase_state['player']['relics'].append('bargaining')
    purchase_state['player']['gold'] = 10_000
    purchase_state['phase'] = 'room'
    purchase_state['room'] = _make_shop(
        purchase_state,
        'buy-second-bargaining:shop',
    )
    purchased_item = purchase_state['room']['relics'][0]
    purchased_item['relic_id'] = 'bargaining'
    before_prices = {
        item['id']: item['price']
        for collection in ('cards', 'relics', 'enchantment_books')
        for item in purchase_state['room'][collection]
        if item is not purchased_item
    }
    before_remove = purchase_state['room']['remove_price']
    before_upgrade = purchase_state['room']['upgrade_price']

    purchased, _ = apply_story_action(
        purchase_state,
        'resolve_room',
        {'option': 'buy_relic', 'item_id': purchased_item['id']},
        'buy-second-bargaining',
    )

    assert purchased['player']['relics'].count('bargaining') == 2
    assert purchased['room']['remove_price'] == max(1, before_remove // 2)
    assert purchased['room']['upgrade_price'] == max(1, before_upgrade // 2)
    for collection in ('cards', 'relics', 'enchantment_books'):
        for item in purchased['room'][collection]:
            if item['id'] == purchased_item['id']:
                assert item['sold'] is True
            else:
                assert item['price'] == max(1, before_prices[item['id']] // 2)


def test_two_world_tree_leaves_each_prevent_one_death():
    state = _started_state('stacked-world-tree-leaves')
    state['player']['relics'].extend(['world_tree_leaf', 'world_tree_leaf'])
    _start_combat(
        state,
        {'type': 'combat'},
        'stacked-world-tree-leaves',
        [],
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    events = []

    state['player']['health'] = 0
    assert _resolve_player_death(state, events) is False
    state['player']['health'] = 0
    assert _resolve_player_death(state, events) is False
    state['player']['health'] = 0
    assert _resolve_player_death(state, events) is True

    revives = [event for event in events if event.get('type') == 'revive']
    assert [(event['charge'], event['charges']) for event in revives] == [(1, 2), (2, 2)]


def test_restart_floor_restores_the_immutable_node_entry_state_even_after_death():
    seed = 'restart-current-floor'
    state = _started_state(seed)
    state['blessing_options'] = list(STORY_BLESSINGS)
    state, _ = apply_story_action(
        state,
        'choose_blessing',
        {'blessing_id': 'max_health'},
        seed,
    )
    node = next(
        item
        for floor in state['map']['floors']
        for item in floor['nodes']
        if item['status'] == 'available'
    )
    node['type'] = 'combat'
    state, _ = apply_story_action(
        state,
        'enter_node',
        {'node_id': node['id']},
        seed,
    )
    entry = copy.deepcopy(state['floor_entry_checkpoint']['state'])

    state['player']['health'] = 0
    state['combat']['hand'] = []
    state['combat']['draw_pile'] = []
    state['rng_counter'] += 50
    state['phase'] = 'game_over'
    state, events = apply_story_action(state, 'restart_floor', {}, seed)

    def gameplay_state(value):
        result = copy.deepcopy(value)
        result.pop('floor_entry_checkpoint', None)
        result.pop('recovery_checkpoint', None)
        result.pop('presentation_event_counter', None)
        result['last_events'] = []
        return result

    assert gameplay_state(state) == gameplay_state(entry)
    assert state['phase'] == 'combat'
    assert state['floor_entry_checkpoint']['node_id'] == node['id']
    assert state['recovery_checkpoint']['kind'] == 'combat_entry'
    assert any(event.get('type') == 'floor_restarted' for event in events)
