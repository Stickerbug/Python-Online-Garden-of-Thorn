import copy

import pytest

import story_engine
from story_content import (
    STORY_BLESSINGS,
    STORY_BOSS_RELIC_IDS,
    STORY_CARDS,
    STORY_ENCOUNTERS,
    STORY_ENEMIES,
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
    state['curses'] = {'vitality': 1, 'affliction': 2}
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


def test_legacy_ward_curse_is_merged_into_affliction_for_existing_runs():
    state = _started_state('legacy-ward', biome='desert')
    state['curses'] = {'ward': 1}
    _start_combat(
        state,
        {'type': 'combat'},
        'legacy-ward',
        [],
        encounter_override=[{'def_id': 'cactus'}],
    )
    assert state['combat']['enemies'][0]['negative_status_immunity'] == 3


def test_legacy_ward_curse_is_persistently_normalized_on_the_next_action():
    state = _started_state('legacy-ward-normalization', biome='desert')
    state['curses'] = {'affliction': 2, 'ward': 1}

    state, _ = apply_story_action(
        state,
        'dev_set_values',
        {'gold': state['player']['gold']},
        'legacy-ward-normalization',
    )

    assert state['curses'] == {'affliction': 3}


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
        for index in range(10)
    ]
    assert len(set(event_ids)) == 10

    repeated = _make_story_event(state, 'event-draw-bag:reset')['event_id']
    assert repeated in set(event_ids)
    assert len(state['encounter_history']['event']) == 1


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


def test_exact_exile_card_remains_playable_when_no_other_card_can_be_selected():
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

    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': amulet['instance_id'], 'target_id': target['id']},
        'empty-exile-selection',
    )

    updated_target = state['combat']['enemies'][0]
    assert updated_target['health'] == 983
    assert [card['instance_id'] for card in state['combat']['discard_pile']] == [
        amulet['instance_id'],
    ]


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


def test_affliction_applies_one_random_negative_status_after_each_enemy_action():
    state = _started_state('affliction-action')
    state['curses'] = {'affliction': 2}
    _start_combat(
        state,
        {'type': 'combat'},
        'affliction-action',
        [],
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    state['player']['health'] = state['player']['max_health'] = 999
    state['combat']['opening_redraw_pending'] = False

    _end_turn(state, 'affliction-action:turn', [])

    assert sum(
        int(state['combat'].get(status) or 0)
        for status in ('weak', 'fragile', 'vulnerable')
    ) == 2


def test_wreckage_summons_its_assigned_enemy_regardless_of_death_source():
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
    assert crab['health'] == crab['max_health']
    assert any(
        event.get('type') == 'enemy_death_trigger'
        and event.get('script') == 'wreckage'
        for event in events
    )


def test_numeric_relics_stack_but_rule_toggle_relics_remain_unique():
    state = _started_state('stacking-relics')
    events = []
    _gain_relic(state, 'ruthless', 'stacking-relics:1', events)
    _gain_relic(state, 'ruthless', 'stacking-relics:2', events)
    _gain_relic(state, 'circulation', 'stacking-relics:3', events)
    _gain_relic(state, 'circulation', 'stacking-relics:4', events)

    assert state['player']['relics'].count('ruthless') == 2
    assert state['player']['relics'].count('circulation') == 1
    _start_combat(
        state,
        {'type': 'combat'},
        'stacking-relics',
        [],
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    assert state['combat']['power'] == 2


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


def test_a_curse_cannot_be_selected_again_on_a_later_stage():
    state = _started_state('unique-stage-curse')
    state['phase'] = 'stage_choice'
    state['curses'] = {'affliction': 1}
    state['room'] = {
        'type': 'stage_choice',
        'stage': 2,
        'biomes': ['desert'],
        'curses': ['affliction'],
    }

    with pytest.raises(StoryActionError) as exc_info:
        apply_story_action(
            state,
            'choose_stage',
            {'biome': 'desert', 'curse_id': 'affliction'},
            'unique-stage-curse',
        )
    assert exc_info.value.code == 'CURSE_ALREADY_SELECTED'
