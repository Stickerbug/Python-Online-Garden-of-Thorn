from pathlib import Path

import pytest

from story_content import (
    STORY_CARDS,
    STORY_ENEMIES,
    STORY_REWARD_CARD_IDS,
    validate_story_content,
)
from story_engine import (
    StoryActionError,
    _gain_elixir,
    _gain_magic,
    _new_card,
    apply_story_action,
)
from story_mode import STORY_FLOOR_COUNT, build_initial_story_state, generate_story_map


def _begin_combat(seed='story-test'):
    state = build_initial_story_state(seed)
    state, _ = apply_story_action(
        state,
        'choose_blessing',
        {'blessing_id': 'titan'},
        seed,
    )
    node = next(
        node
        for floor in state['map']['floors']
        for node in floor['nodes']
        if node['status'] == 'available'
    )
    state, events = apply_story_action(
        state,
        'enter_node',
        {'node_id': node['id']},
        seed,
    )
    return state, events


def _inject_hand_card(state, def_id, upgraded=False):
    card = _new_card(state, def_id, upgraded)
    state['combat']['hand'].append(card)
    return card


def test_story_resources_can_exceed_legacy_display_maximums():
    state, _ = _begin_combat('unbounded-story-resources')
    events = []
    _gain_elixir(state, 25000, events)
    _gain_magic(state, 25000, events)
    assert state['combat']['elixir'] > state['player']['max_elixir']
    assert state['combat']['magic'] > state['player']['max_magic']
    assert {'type': 'elixir', 'amount': 25000} in events
    assert {'type': 'magic', 'amount': 25000} in events


def test_story_content_is_valid_and_reward_pool_excludes_special_cards():
    validate_story_content()
    assert len(STORY_CARDS) >= 60
    assert STORY_CARDS['startled']['type'] == 'curse'
    assert STORY_CARDS['slimed']['type'] == 'infect'
    assert STORY_CARDS['mark']['rarity'] == 'super'
    assert all(
        STORY_CARDS[card_id]['type'] not in ('curse', 'infect')
        and STORY_CARDS[card_id]['rarity'] not in ('super', 'special')
        for card_id in STORY_REWARD_CARD_IDS
    )


def test_every_story_enemy_has_a_packaged_image():
    project_root = Path(__file__).resolve().parents[1]
    for enemy_id, definition in STORY_ENEMIES.items():
        image_url = definition.get('image_url')
        assert image_url, enemy_id
        assert image_url.startswith('/static/assets/story-enemies/'), enemy_id
        assert (project_root / image_url.removeprefix('/')).is_file(), enemy_id


def test_story_map_has_sixteen_floors_no_early_elites_and_no_crossing_edges():
    story_map = generate_story_map('map-test', stage=1, biome='garden')
    assert len(story_map['floors']) == STORY_FLOOR_COUNT
    assert story_map['floors'][0]['nodes'][0]['type'] == 'blessing'
    assert story_map['floors'][-1]['nodes'][0]['type'] == 'boss'
    assert all(
        node['type'] != 'elite'
        for floor in story_map['floors'][:6]
        for node in floor['nodes']
    )
    nodes = {
        node['id']: node
        for floor in story_map['floors']
        for node in floor['nodes']
    }
    by_floor = {}
    for edge in story_map['edges']:
        source = nodes[edge['from']]
        target = nodes[edge['to']]
        by_floor.setdefault(source['floor'], []).append((source, target))
    for edges in by_floor.values():
        for index, (left_source, left_target) in enumerate(edges):
            for right_source, right_target in edges[index + 1:]:
                assert (
                    (left_source['x'] - right_source['x'])
                    * (left_target['x'] - right_target['x'])
                ) >= 0


def test_a_complete_four_stage_journey_can_reach_the_terminal_state():
    seed = 'full-journey'
    state = build_initial_story_state(seed)
    action_count = 0

    while state.get('phase') not in ('complete', 'game_over'):
        action_count += 1
        assert action_count < 1000
        state['player']['health'] = max(100000, int(state['player']['health']))
        state['player']['max_health'] = max(
            100000,
            int(state['player']['max_health']),
        )
        phase = state['phase']

        if phase == 'blessing':
            blessing_id = 'titan' if int(state['stage']) == 1 else 'oracle'
            state, _ = apply_story_action(
                state,
                'choose_blessing',
                {'blessing_id': blessing_id},
                seed,
            )
        elif phase == 'map':
            node = next(
                node
                for floor in state['map']['floors']
                for node in floor['nodes']
                if node['status'] == 'available'
            )
            state, _ = apply_story_action(
                state,
                'enter_node',
                {'node_id': node['id']},
                seed,
            )
        elif phase == 'combat':
            combat = state['combat']
            if combat.get('opening_redraw_pending'):
                state, _ = apply_story_action(
                    state,
                    'opening_redraw',
                    {'selected_card_ids': []},
                    seed,
                )
                continue
            combat['turn'] = 'player'
            combat['card_play_limit'] = None
            combat['elixir'] = 999
            combat['magic'] = 999
            target = next(
                enemy for enemy in combat['enemies']
                if int(enemy['health']) > 0
            )
            target['health'] = 1
            target['shield'] = 0
            target['reflection'] = 0
            card = _new_card(state, 'basic')
            combat['hand'].append(card)
            state, _ = apply_story_action(
                state,
                'play_card',
                {
                    'card_instance_id': card['instance_id'],
                    'target_id': target['id'],
                },
                seed,
            )
        elif phase == 'reward':
            state, _ = apply_story_action(state, 'choose_reward', {}, seed)
        elif phase == 'room':
            room = state['room']
            options = [
                option.get('id') if isinstance(option, dict) else option
                for option in room.get('options', [])
            ]
            preferred = {
                'rest': 'heal',
                'chest': 'claim',
                'shop': 'leave',
            }.get(room.get('type'))
            option = preferred if preferred in options else next(
                (
                    value for value in ('pass_by', 'leave', 'escape', 'observe')
                    if value in options
                ),
                options[0],
            )
            state, _ = apply_story_action(
                state,
                'resolve_room',
                {'option': option},
                seed,
            )
        elif phase == 'stage_choice':
            state, _ = apply_story_action(
                state,
                'choose_stage',
                {'biome': state['room']['biomes'][0]},
                seed,
            )
        else:
            raise AssertionError(f'Unhandled story phase: {phase}')

    assert state['phase'] == 'complete'
    assert state['stage'] == 4
    assert state['completed'] is True


def test_first_battle_supports_multiple_enemies_and_explicit_targeting():
    state, events = _begin_combat('multi-target')
    assert state['phase'] == 'combat'
    assert 1 <= len(state['combat']['enemies']) <= 4
    assert events[-1]['type'] == 'combat_start'
    while len(state['combat']['enemies']) < 2:
        state['combat']['enemies'].append({
            **state['combat']['enemies'][0],
            'id': f"enemy-{len(state['combat']['enemies']) + 1}",
        })
    card = _inject_hand_card(state, 'basic')
    first, second = state['combat']['enemies'][:2]
    first_health = first['health']
    second_health = second['health']
    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': second['id']},
        'multi-target',
    )
    assert state['combat']['enemies'][0]['health'] == first_health
    assert state['combat']['enemies'][1]['health'] == second_health - 6


def test_wide_strike_hits_every_living_enemy():
    state, _ = _begin_combat('wide-strike')
    while len(state['combat']['enemies']) < 2:
        state['combat']['enemies'].append({
            **state['combat']['enemies'][0],
            'id': f"enemy-{len(state['combat']['enemies']) + 1}",
        })
    card = _inject_hand_card(state, 'lightning')
    before = [enemy['health'] for enemy in state['combat']['enemies']]
    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id']},
        'wide-strike',
    )
    after = [enemy['health'] for enemy in state['combat']['enemies']]
    assert after == [value - 6 for value in before]


def test_exact_hand_selection_is_server_validated_and_exiled():
    state, _ = _begin_combat('selection')
    card = _inject_hand_card(state, 'amulet')
    other = next(item for item in state['combat']['hand'] if item is not card)
    target = state['combat']['enemies'][0]
    with pytest.raises(StoryActionError) as error:
        apply_story_action(
            state,
            'play_card',
            {'card_instance_id': card['instance_id'], 'target_id': target['id']},
            'selection',
        )
    assert error.value.code == 'CARD_SELECTION_REQUIRED'
    state, _ = apply_story_action(
        state,
        'play_card',
        {
            'card_instance_id': card['instance_id'],
            'target_id': target['id'],
            'selected_card_ids': [other['instance_id']],
        },
        'selection',
    )
    assert any(item['instance_id'] == other['instance_id'] for item in state['combat']['exile_pile'])


def test_end_turn_runs_enemy_actions_and_starts_a_fresh_player_turn():
    state, _ = _begin_combat('turn-cycle')
    state, events = apply_story_action(state, 'end_turn', {}, 'turn-cycle')
    assert state['phase'] in ('combat', 'game_over')
    assert any(event['type'] == 'enemy_action' for event in events)
    if state['phase'] == 'combat':
        assert state['combat']['turn'] == 'player'
        assert state['combat']['round'] == 2
        assert len(state['combat']['hand']) <= 10


def test_nuke_spends_all_elixir_and_hits_once_per_point():
    state, _ = _begin_combat('nuke')
    state['combat']['elixir'] = 3
    card = _inject_hand_card(state, 'nuke')
    target = state['combat']['enemies'][0]
    before = target['health']
    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': target['id']},
        'nuke',
    )
    assert state['combat']['elixir'] == 0
    damage = next(event for event in events if event['type'] == 'enemy_damage')
    assert damage['hits'] == 3
    assert before - state['combat']['enemies'][0]['health'] == 27


def test_enemy_applied_broken_survives_until_the_player_uses_it():
    state, _ = _begin_combat('broken-duration')
    enemy = state['combat']['enemies'][0]
    enemy.update({
        'def_id': 'bee',
        'name': {'zh': '蜜蜂', 'en': 'Bee'},
        'health': 39,
        'max_health': 39,
        'move_index': 0,
    })
    state['combat']['enemies'] = [enemy]
    state, _ = apply_story_action(state, 'end_turn', {}, 'broken-duration')
    assert state['combat']['broken'] == 3
    health = state['player']['health']
    card = _inject_hand_card(state, 'basic')
    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': enemy['id']},
        'broken-duration',
    )
    assert state['player']['health'] == health - 3


def test_rockfall_grows_and_triggers_before_the_rock_action():
    state, _ = _begin_combat('rockfall')
    enemy = state['combat']['enemies'][0]
    enemy.update({
        'def_id': 'garden_rock',
        'name': {'zh': '岩石', 'en': 'Rock'},
        'health': 52,
        'max_health': 52,
        'move_index': 0,
        'rockfall': 0,
    })
    state['combat']['enemies'] = [enemy]
    state, _ = apply_story_action(state, 'end_turn', {}, 'rockfall')
    assert state['combat']['enemies'][0]['rockfall'] == 3
    health = state['player']['health']
    state, events = apply_story_action(state, 'end_turn', {}, 'rockfall')
    assert state['player']['health'] == health - 3
    assert any(event.get('source') == '落石' for event in events)
    assert state['combat']['enemies'][0]['move_index'] == 1


def test_hive_death_summons_a_withering_wasp_instead_of_ending_combat():
    state, _ = _begin_combat('hive-death')
    enemy = state['combat']['enemies'][0]
    enemy.update({
        'def_id': 'hive',
        'name': {'zh': '蜂巢', 'en': 'Hive'},
        'health': 1,
        'max_health': 151,
        'move_index': 0,
    })
    state['combat']['enemies'] = [enemy]
    card = _inject_hand_card(state, 'basic')
    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': enemy['id']},
        'hive-death',
    )
    wasps = [
        item for item in state['combat']['enemies']
        if item['def_id'] == 'wasp' and item['health'] > 0
    ]
    assert state['phase'] == 'combat'
    assert len(wasps) == 1
    assert wasps[0]['move_index'] == 1
    assert wasps[0]['wither'] == 3
    assert any(event['type'] == 'enemy_death_trigger' for event in events)


def test_cooldown_relic_blocks_actions_until_opening_redraw_is_resolved():
    seed = 'cooldown'
    state = build_initial_story_state(seed)
    state['player']['relics'].append('cooldown')
    state, _ = apply_story_action(state, 'choose_blessing', {'blessing_id': 'titan'}, seed)
    node = next(
        node
        for floor in state['map']['floors']
        for node in floor['nodes']
        if node['status'] == 'available'
    )
    state, _ = apply_story_action(state, 'enter_node', {'node_id': node['id']}, seed)
    assert state['combat']['opening_redraw_pending'] is True
    card = state['combat']['hand'][0]
    target = state['combat']['enemies'][0]
    with pytest.raises(StoryActionError) as error:
        apply_story_action(
            state,
            'play_card',
            {'card_instance_id': card['instance_id'], 'target_id': target['id']},
            seed,
        )
    assert error.value.code == 'CARD_NOT_PLAYABLE'
    selected = [item['instance_id'] for item in state['combat']['hand'][:2]]
    state, events = apply_story_action(
        state,
        'opening_redraw',
        {'selected_card_ids': selected},
        seed,
    )
    assert state['combat']['opening_redraw_pending'] is False
    assert any(event['type'] == 'opening_redraw_resolved' for event in events)


def test_occultist_event_adds_the_defined_cards_and_completes():
    seed = 'occultist-event'
    state = build_initial_story_state(seed)
    state, _ = apply_story_action(state, 'choose_blessing', {'blessing_id': 'titan'}, seed)
    state['phase'] = 'room'
    state['room'] = {
        'type': 'event',
        'event_id': 'occultist',
        'options': ['occult_power'],
    }
    state, events = apply_story_action(
        state,
        'resolve_room',
        {'option': 'occult_power'},
        seed,
    )
    gained = [event.get('card_id') for event in events if event['type'] == 'card_gained']
    assert gained.count('mark') == 1
    assert gained.count('startled') == 2
    assert state['phase'] == 'map'


def test_creature_struggle_starts_the_selected_custom_encounter():
    seed = 'creature-event'
    state = build_initial_story_state(seed)
    state, _ = apply_story_action(state, 'choose_blessing', {'blessing_id': 'titan'}, seed)
    state['phase'] = 'room'
    state['room'] = {
        'type': 'event',
        'event_id': 'creature_struggle',
        'options': ['fight_help_spider'],
    }
    state, _ = apply_story_action(
        state,
        'resolve_room',
        {'option': 'fight_help_spider'},
        seed,
    )
    assert state['phase'] == 'combat'
    assert state['combat']['event_resolution'] == 'fight_help_spider'
    assert [enemy['def_id'] for enemy in state['combat']['enemies']] == ['spider_yuba']
    assert state['combat']['enemies'][0]['health'] == 51


def test_light_only_sprouts_one_exile_copy_from_a_non_exile_card():
    seed = 'light-sprout'
    state, _ = _begin_combat(seed)
    combat = state['combat']
    combat['hand'] = []
    combat['draw_pile'] = []
    combat['discard_pile'] = []
    combat['elixir'] = 10
    enemy = combat['enemies'][0]
    enemy['health'] = 999
    enemy['max_health'] = 999

    light = _inject_hand_card(state, 'light')
    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': light['instance_id'], 'target_id': enemy['id']},
        seed,
    )
    generated = state['combat']['draw_pile']
    assert len(generated) == 1
    assert generated[0]['def_id'] == 'light'
    assert generated[0]['modifiers']['force_exile'] is True

    state['combat']['hand'].append(state['combat']['draw_pile'].pop())
    copied_light = state['combat']['hand'][0]
    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': copied_light['instance_id'], 'target_id': enemy['id']},
        seed,
    )
    assert state['combat']['draw_pile'] == []
    assert [card['def_id'] for card in state['combat']['exile_pile']] == ['light']
