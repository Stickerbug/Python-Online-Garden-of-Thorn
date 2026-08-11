import copy
from pathlib import Path

import pytest

from story_content import (
    STORY_BLESSINGS,
    STORY_CARD_IMAGE_URLS,
    STORY_CARDS,
    STORY_CARD_TYPES,
    STORY_ENCOUNTERS,
    STORY_ENEMIES,
    STORY_ENEMY_IMAGE_URLS,
    STORY_PLAYER_ATTACK_EFFECT_TYPES,
    STORY_RARITIES,
    STORY_RELICS,
    STORY_REWARD_CARD_IDS,
    STORY_STATUS_IMAGE_URLS,
    STORY_STATUSES,
    STORY_TRAITS,
    initial_story_player,
    validate_story_content,
)
from story_engine import (
    StoryActionError,
    _draw_cards,
    _enemy_intent,
    _enemy_physical_damage,
    _gain_elixir,
    _gain_magic,
    _new_card,
    _refresh_combat_projections,
    _start_combat,
    apply_story_action,
)
from story_mode import (
    STORY_FLOOR_COUNT,
    build_initial_story_state,
    generate_boss_rush_map,
    generate_story_map,
)


def _journey_state(seed='story-test', difficulty='normal', biome='garden'):
    state = build_initial_story_state(seed)
    state, _ = apply_story_action(
        state,
        'start_journey',
        {'biome': biome, 'difficulty': difficulty},
        seed,
    )
    state['blessing_options'] = list(STORY_BLESSINGS)
    return state


def _begin_combat(seed='story-test'):
    state = _journey_state(seed)
    state, _ = apply_story_action(
        state,
        'choose_blessing',
        {'blessing_id': 'max_health'},
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


def test_story_disc_halves_enemy_physical_damage_until_next_player_turn():
    state = build_initial_story_state('story-disc')
    _start_combat(
        state,
        {'type': 'combat'},
        'story-disc',
        [],
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    combat = state['combat']
    combat['hand'] = []
    combat['draw_pile'] = []
    combat['discard_pile'] = []
    combat['elixir'] = 10
    state['player']['health'] = 80
    disc = _inject_hand_card(state, 'disc')

    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': disc['instance_id']},
        'story-disc-play',
    )
    assert state['combat']['disc_active'] is True

    state, events = apply_story_action(state, 'end_turn', {}, 'story-disc-end')

    damage_events = [
        event for event in events
        if event.get('type') == 'player_damage'
    ]
    assert damage_events[0]['amount'] == 3
    assert state['player']['health'] == 77
    assert state['combat']['disc_active'] is False


def test_story_resources_can_exceed_legacy_display_maximums():
    state, _ = _begin_combat('unbounded-story-resources')
    events = []
    original_elixir = state['combat']['elixir']
    original_magic = state['combat']['magic']
    _gain_elixir(state, 25000, events)
    _gain_magic(state, 25000, events)
    assert state['combat']['elixir'] == original_elixir + 25000
    assert state['combat']['magic'] == original_magic + 25000
    assert state['combat']['elixir'] > state['player']['max_elixir']
    assert state['combat']['magic'] > state['player']['max_magic']
    assert any(
        event.get('type') == 'elixir'
        and event.get('amount') == 25000
        and event.get('before') == original_elixir
        and event.get('after') == original_elixir + 25000
        for event in events
    )
    assert any(
        event.get('type') == 'magic'
        and event.get('amount') == 25000
        and event.get('before') == original_magic
        and event.get('after') == original_magic + 25000
        for event in events
    )


def test_story_resources_reset_to_turn_baselines_instead_of_carrying_over():
    seed = 'story-resource-reset'
    state, _ = _begin_combat(seed)
    state['combat']['opening_redraw_pending'] = False
    state['combat']['elixir'] = 41
    state['combat']['magic'] = 29
    state['player']['max_elixir'] = 7
    state['player']['magic'] = 3
    state['player']['health'] = state['player']['max_health'] = 999
    for enemy in state['combat']['enemies']:
        enemy['stun'] = 1

    state, _ = apply_story_action(state, 'end_turn', {}, seed)

    assert state['phase'] == 'combat'
    assert state['combat']['elixir'] == 7
    assert state['combat']['magic'] == 3


def test_story_surrender_directly_ends_run_without_revive():
    seed = 'story-surrender'
    state, _ = _begin_combat(seed)
    state['player']['health'] = 17
    state['player']['relics'].append('world_tree_leaf')

    state, events = apply_story_action(state, 'surrender', {}, seed)

    assert state['phase'] == 'game_over'
    assert state['player']['health'] == 0
    assert state.get('recovery_checkpoint') is None
    assert state['combat'].get('turn') == 'ended'
    assert any(event.get('type') == 'story_surrender' for event in events)
    assert any(event.get('type') == 'game_over' for event in events)
    assert not any(event.get('type') == 'revive' for event in events)


def test_story_draw_reshuffles_discard_during_the_same_draw_action():
    seed = 'story-mid-draw-reshuffle'
    state, _ = _begin_combat(seed)
    combat = state['combat']
    combat['hand'] = []
    first = _new_card(state, 'basic')
    second = _new_card(state, 'rose')
    third = _new_card(state, 'heavy')
    combat['draw_pile'] = [first]
    combat['discard_pile'] = [second, third]
    events = []

    drawn = _draw_cards(state, 3, seed, events)

    assert set(drawn) == {
        first['instance_id'],
        second['instance_id'],
        third['instance_id'],
    }
    assert combat['draw_pile'] == []
    assert combat['discard_pile'] == []
    assert any(event.get('type') == 'reshuffle' for event in events)
    assert any(event.get('type') == 'draw' and event.get('count') == 3 for event in events)


def test_story_content_is_valid_and_reward_pool_excludes_special_cards():
    validate_story_content()
    assert len(STORY_CARDS) >= 60
    assert len(STORY_BLESSINGS) == 8
    assert all(not item['name']['zh'] for item in STORY_BLESSINGS.values())
    assert STORY_CARDS['startled']['type'] == 'curse'
    assert STORY_CARDS['slimed']['type'] == 'infect'
    assert STORY_CARDS['mark']['rarity'] == 'super'
    assert STORY_CARDS['mark']['owner'] == 'neutral'
    assert 'exile' in STORY_CARDS['mark']['tags']
    initial_player = initial_story_player()
    assert initial_player['relics'] == ['energetic']
    assert initial_player['gold'] == 99
    assert STORY_RELICS['energetic']['script'] == 'floor_heal'


def test_story_attack_effect_types_share_one_calculation_contract():
    attack_effect_types = {
        str(effect.get('type') or '')
        for definition in STORY_CARDS.values()
        if definition.get('type') == 'thorn'
        for effect in (
            tuple(definition.get('effects') or ())
            + tuple((definition.get('upgrade') or {}).get('effects') or ())
        )
        if str(effect.get('type') or '').startswith('damage')
    }
    assert attack_effect_types == set(STORY_PLAYER_ATTACK_EFFECT_TYPES)


def test_story_infect_filter_uses_the_short_status_label():
    assert STORY_CARD_TYPES['infect']['name']['zh'] == '状态'


def test_story_statuses_use_their_dedicated_icons():
    expected = {
        'entangle': '/static/assets/story-status-icons/entangle.svg',
        'evil_eye': '/static/assets/status-icons/nazar.svg',
        'temporary_power': '/static/assets/story-status-icons/temporary-power.svg',
        'vulnerable': '/static/assets/story-status-icons/vulnerable.svg',
        'fragile': '/static/assets/story-status-icons/fragile.svg',
    }
    for status_id, image_url in expected.items():
        assert STORY_STATUS_IMAGE_URLS[status_id] == image_url
        assert STORY_STATUSES[status_id]['image_url'] == image_url
        assert (Path(__file__).resolve().parents[1] / image_url.removeprefix('/')).is_file()
    for trait_id in ('sturdy', 'hidden'):
        image_url = STORY_TRAITS[trait_id]['image_url']
        assert (Path(__file__).resolve().parents[1] / image_url.removeprefix('/')).is_file()
    for enemy_id in ('crab', 'turtle'):
        image_url = STORY_ENEMY_IMAGE_URLS[enemy_id]
        assert (Path(__file__).resolve().parents[1] / image_url.removeprefix('/')).is_file()
    assert all(
        STORY_CARDS[card_id]['type'] not in ('curse', 'infect')
        and STORY_CARDS[card_id]['rarity'] not in ('super', 'special')
        for card_id in STORY_REWARD_CARD_IDS
    )


def test_immediate_blessings_apply_the_latest_defined_rewards():
    seed = 'story-blessing-immediate'

    health_state = _journey_state(seed)
    initial_health = health_state['player']['health']
    initial_max_health = health_state['player']['max_health']
    health_state, _ = apply_story_action(
        health_state,
        'choose_blessing',
        {'blessing_id': 'max_health'},
        seed,
    )
    assert health_state['player']['max_health'] == initial_max_health + 15
    assert health_state['player']['health'] == initial_health
    assert health_state['player']['blessings'] == ['max_health']

    rare_state = _journey_state(seed)
    initial_deck_size = len(rare_state['player']['deck'])
    rare_state, rare_events = apply_story_action(
        rare_state,
        'choose_blessing',
        {'blessing_id': 'rare_card'},
        seed,
    )
    gained_rare = next(
        event for event in rare_events
        if event.get('type') == 'card_gained'
    )
    assert len(rare_state['player']['deck']) == initial_deck_size + 1
    assert STORY_CARDS[gained_rare['card_id']]['rarity'] == 'rare'

    gold_state = _journey_state(seed)
    gold_state, _ = apply_story_action(
        gold_state,
        'choose_blessing',
        {'blessing_id': 'gold'},
        seed,
    )
    assert gold_state['player']['gold'] == 199

    relic_state = _journey_state(seed)
    relic_state, _ = apply_story_action(
        relic_state,
        'choose_blessing',
        {'blessing_id': 'relic_and_fatigue'},
        seed,
    )
    assert len(relic_state['player']['relics']) == 2
    assert relic_state['player']['deck'][-1]['def_id'] == 'fatigued'

    wealth_state = _journey_state(seed)
    wealth_state, _ = apply_story_action(
        wealth_state,
        'choose_blessing',
        {'blessing_id': 'wealth_and_basics'},
        seed,
    )
    assert wealth_state['player']['gold'] == 349
    assert [card['def_id'] for card in wealth_state['player']['deck'][-2:]] == [
        'basic',
        'rose',
    ]


def test_blessing_can_transform_or_remove_the_selected_deck_instance():
    seed = 'story-blessing-deck-change'
    transform_state = _journey_state(seed)
    selected = transform_state['player']['deck'][0]
    selected['upgraded'] = True
    selected['modifiers'] = {'temporary': 3}
    instance_id = selected['instance_id']
    original_def_id = selected['def_id']
    transform_state, events = apply_story_action(
        transform_state,
        'choose_blessing',
        {
            'blessing_id': 'transform_card',
            'card_instance_id': instance_id,
        },
        seed,
    )
    transformed = next(
        card for card in transform_state['player']['deck']
        if card['instance_id'] == instance_id
    )
    assert transformed['def_id'] != original_def_id
    assert transformed['upgraded'] is False
    assert 'modifiers' not in transformed
    assert any(event.get('type') == 'card_transformed' for event in events)

    remove_state = _journey_state(seed)
    removed = remove_state['player']['deck'][0]
    initial_size = len(remove_state['player']['deck'])
    remove_state, events = apply_story_action(
        remove_state,
        'choose_blessing',
        {
            'blessing_id': 'remove_card',
            'card_instance_id': removed['instance_id'],
        },
        seed,
    )
    assert len(remove_state['player']['deck']) == initial_size - 1
    assert all(
        card['instance_id'] != removed['instance_id']
        for card in remove_state['player']['deck']
    )
    assert any(
        event.get('type') == 'card_removed'
        and event.get('source') == 'blessing'
        for event in events
    )


def test_double_card_reward_blessing_resolves_two_complete_reward_rounds():
    seed = 'story-blessing-double-reward'
    state = _journey_state(seed)
    state, _ = apply_story_action(
        state,
        'choose_blessing',
        {'blessing_id': 'double_card_reward'},
        seed,
    )
    assert state['phase'] == 'reward'
    assert state['reward']['source'] == 'blessing'
    assert state['reward']['round_index'] == 1
    assert state['reward']['round_total'] == 2
    assert state['player']['blessings'] == ['double_card_reward']

    first_card_id = state['reward']['cards'][0]['card_id']
    state, _ = apply_story_action(
        state,
        'choose_reward',
        {'reward_type': 'card', 'card_id': first_card_id},
        seed,
    )
    state, events = apply_story_action(
        state,
        'choose_reward',
        {'reward_type': 'continue'},
        seed,
    )
    assert state['phase'] == 'reward'
    assert state['reward']['round_index'] == 2
    assert any(
        event.get('type') == 'blessing_card_reward_started'
        and event.get('round_index') == 2
        for event in events
    )

    state, _ = apply_story_action(
        state,
        'choose_reward',
        {'reward_type': 'card', 'card_id': ''},
        seed,
    )
    state, _ = apply_story_action(
        state,
        'choose_reward',
        {'reward_type': 'continue'},
        seed,
    )
    assert state['phase'] == 'map'
    assert state['reward'] is None
    assert any(
        node['status'] == 'available'
        for floor in state['map']['floors']
        for node in floor['nodes']
    )


def test_updated_story_card_balance_matches_the_latest_design():
    assert STORY_CARDS['coffee']['effects'][0]['amount'] == 3
    assert STORY_CARDS['bur']['effects'][0]['amount'] == 6
    assert STORY_CARDS['shell']['upgrade']['cost_e'] == 1
    assert STORY_CARDS['sponge']['cost_e'] == 1
    assert STORY_CARDS['sponge']['upgrade']['cost_e'] == 0
    assert STORY_CARDS['light']['effects'][0] == {
        'type': 'damage',
        'amount': 3,
        'hits': 2,
    }
    assert STORY_CARDS['light']['upgrade']['effects'][0]['amount'] == 4
    assert 'exile' not in STORY_CARDS['heavy']['tags']
    assert STORY_CARDS['magic_shell']['effects'][1]['amount'] == 4
    assert STORY_CARDS['crystal_leaf']['cost_e'] == 3
    assert STORY_CARDS['crystal_leaf']['effects'][0]['amount'] == 2
    assert STORY_CARDS['magic_crystal_leaf']['type'] == 'root'
    assert STORY_CARDS['magic_crystal_leaf']['effects'][0]['amount'] == 3
    assert STORY_CARDS['dna']['type'] == 'root'
    assert STORY_CARDS['chromosome']['effects'][0]['amount'] == 7
    assert STORY_CARDS['moon_rock']['upgrade']['effects'][1]['amount'] == -1
    assert STORY_CARDS['nuke']['rarity'] == 'rare'
    assert STORY_CARDS['rmb']['effects'][0]['amount'] == 15
    assert STORY_CARDS['rmb']['upgrade']['effects'][0]['amount'] == 25
    assert STORY_CARDS['bubble']['rarity'] == 'ultra'
    assert STORY_CARDS['magic_bubble']['rarity'] == 'ultra'
    for card_id in ('rice', 'glass', 'dust', 'pyrite', 'feather'):
        assert STORY_CARDS[card_id]['rarity'] == 'rare'


def test_updated_story_relic_and_garden_enemy_balance():
    assert STORY_RELICS['bargaining']['amount'] == 50
    assert STORY_RELICS['world_tree_leaf']['rarity'] == 'special'
    assert STORY_RELICS['dandelion_blessing']['amount'] == 7
    assert STORY_ENEMIES['soldier_ant']['moves'][0]['effects'][0]['amount'] == 6
    assert STORY_ENEMIES['soldier_ant']['moves'][1]['effects'][0]['amount'] == 14
    assert STORY_ENEMIES['young_ant']['max_health'] == 11
    assert STORY_ENEMIES['worker_ant']['max_health'] == 32
    assert STORY_ENEMIES['wasp']['moves'][0]['effects'][0]['amount'] == 6
    assert STORY_ENEMIES['wasp']['moves'][0]['effects'][0]['lunatic_amount'] == 8
    assert STORY_ENEMIES['centipede']['max_health'] == 52
    assert STORY_ENEMIES['avocado']['moves'][0]['name']['en'] == 'Expand'
    assert STORY_ENEMIES['avocado']['moves'][0]['effects'][1]['amount'] == 2
    assert STORY_ENEMIES['spider_yoba']['moves'][1]['effects'][0]['amount'] == 13
    assert STORY_ENEMIES['digger']['max_health'] == 198
    assert STORY_ENEMIES['digger']['moves'][1]['effects'][0]['amount'] == 3
    assert STORY_ENEMIES['ant_queen']['max_health'] == 152
    assert STORY_ENEMIES['ant_queen']['moves'][2]['effects'][0]['amount'] == 5
    assert STORY_ENEMIES['ant_queen']['moves'][3]['effects'][0]['amount'] == 2
    assert STORY_ENEMIES['hive']['max_health'] == 172
    assert STORY_ENEMIES['hive']['moves'][0]['effects'][0]['wither'] == 4
    assert STORY_ENCOUNTERS['garden']['boss'][0] == (
        'ant_queen',
        'worker_ant',
        'young_ant',
        'young_ant',
    )


def test_story_rarity_default_colors():
    assert {
        rarity: definition['color']
        for rarity, definition in STORY_RARITIES.items()
    } == {
        'primary': '#7EEF6D',
        'common': '#FFE65D',
        'rare': '#861FDE',
        'ultra': '#FF2B75',
        'super': '#2BFFA3',
    }


def test_story_card_descriptions_do_not_end_with_full_stops():
    for card_id, definition in STORY_CARDS.items():
        descriptions = [definition.get('description')]
        descriptions.append((definition.get('upgrade') or {}).get('description'))
        for description in descriptions:
            if isinstance(description, dict):
                for language, text in description.items():
                    assert not str(text).rstrip().endswith(('。', '.')), (
                        card_id,
                        language,
                        text,
                    )


def test_every_story_enemy_has_a_packaged_image():
    project_root = Path(__file__).resolve().parents[1]
    for enemy_id, definition in STORY_ENEMIES.items():
        image_url = definition.get('image_url')
        assert image_url, enemy_id
        assert image_url.startswith('/static/assets/story-enemies/'), enemy_id
        assert (project_root / image_url.removeprefix('/')).is_file(), enemy_id


def test_story_patch_card_status_and_trait_images_are_packaged():
    project_root = Path(__file__).resolve().parents[1]
    image_groups = (
        (STORY_CARD_IMAGE_URLS, STORY_CARDS),
        (STORY_STATUS_IMAGE_URLS, STORY_STATUSES),
        (
            {
                trait_id: definition['image_url']
                for trait_id, definition in STORY_TRAITS.items()
            },
            STORY_TRAITS,
        ),
    )
    referenced_urls = set()
    for image_urls, definitions in image_groups:
        for definition_id, image_url in image_urls.items():
            assert image_url not in referenced_urls, definition_id
            referenced_urls.add(image_url)
            assert (project_root / image_url.removeprefix('/')).is_file(), definition_id
            if definitions is not None:
                assert definitions[definition_id]['image_url'] == image_url

    assert len(STORY_CARD_IMAGE_URLS) >= 16
    assert len(STORY_STATUS_IMAGE_URLS) >= 9
    assert len(STORY_TRAITS) >= 19


def test_story_enemy_traits_reference_defined_visual_terms():
    expected = {
        'centipede': ('adjacent',),
        'sunflower': ('sturdy',),
        'avocado': ('swell',),
        'ant_queen': ('nourish',),
        'hive': ('summon_after_death',),
    }
    for enemy_id, trait_ids in expected.items():
        assert STORY_ENEMIES[enemy_id]['traits'] == trait_ids
        assert all(trait_id in STORY_TRAITS for trait_id in trait_ids)


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


def test_boss_rush_map_is_a_ten_floor_global_single_route_block():
    story_map = generate_boss_rush_map(
        'boss-rush-map',
        block=3,
        biome='desert',
        difficulty='hard',
    )

    assert story_map['mode'] == 'boss_rush'
    assert story_map['floor_offset'] == 20
    assert story_map['floor_count'] == 30
    assert [floor['floor'] for floor in story_map['floors']] == list(range(21, 31))
    assert all(floor['width'] == 1 for floor in story_map['floors'])
    assert len(story_map['edges']) == 9
    assert all(
        node['status'] == 'locked'
        for floor in story_map['floors']
        for node in floor['nodes']
    )
    assert all(
        node.get('enemy_health_multiplier') == 3
        for floor in story_map['floors']
        for node in floor['nodes']
        if node['type'] == 'elite'
    )


def test_boss_rush_opens_after_ten_card_rewards_and_one_talent():
    seed = 'boss-rush-opening'
    state = build_initial_story_state(seed)
    initial_deck_size = len(state['player']['deck'])
    initial_relic_count = len(state['player']['relics'])

    state, _ = apply_story_action(
        state,
        'start_journey',
        {'biome': 'garden', 'difficulty': 'normal', 'mode': 'boss_rush'},
        seed,
    )

    assert state['journey_mode'] == 'boss_rush'
    assert state['phase'] == 'reward'
    assert state['reward']['source'] == 'boss_rush_start_cards'
    assert state['reward']['round_total'] == 10
    assert state['map']['floors'][0]['nodes'][0]['status'] == 'locked'

    for round_index in range(1, 11):
        reward = state['reward']
        assert reward['round_index'] == round_index
        choice = reward['cards'][0]
        card_id = choice.get('card_id') if isinstance(choice, dict) else choice
        state, _ = apply_story_action(
            state,
            'choose_reward',
            {'reward_type': 'card', 'card_id': card_id},
            seed,
        )
        state, _ = apply_story_action(
            state,
            'choose_reward',
            {'reward_type': 'continue'},
            seed,
        )

    assert len(state['player']['deck']) == initial_deck_size + 10
    assert state['phase'] == 'reward'
    assert state['reward']['source'] == 'boss_rush_start_relic'
    relic_id = state['reward']['relic']
    state, _ = apply_story_action(
        state,
        'choose_reward',
        {'reward_type': 'relic', 'relic_id': relic_id},
        seed,
    )
    state, _ = apply_story_action(
        state,
        'choose_reward',
        {'reward_type': 'continue'},
        seed,
    )

    assert state['phase'] == 'map'
    assert state['current_floor'] == 1
    assert state['map']['floors'][0]['nodes'][0]['status'] == 'available'
    assert len(state['player']['relics']) == initial_relic_count + 1


def test_boss_rush_stage_choice_stacks_curses_and_advances_endlessly():
    seed = 'boss-rush-loop'
    state = build_initial_story_state(seed)
    state['journey_mode'] = 'boss_rush'
    state['difficulty'] = 'normal'
    state['curses'] = {'vitality': 1}

    for block in (2, 3):
        state['phase'] = 'stage_choice'
        state['room'] = {
            'type': 'stage_choice',
            'stage': block,
            'biomes': ['garden'],
            'curses': ['vitality'],
            'allow_repeated_curses': True,
            'boss_rush': True,
        }
        state, events = apply_story_action(
            state,
            'choose_stage',
            {'biome': 'garden', 'curse_id': 'vitality'},
            seed,
        )

        first_node = state['map']['floors'][0]['nodes'][0]
        assert state['phase'] == 'map'
        assert state['stage'] == block
        assert state['current_floor'] == (block - 1) * 10 + 1
        assert state['map']['floor_count'] == block * 10
        assert first_node['status'] == 'available'
        assert state['curses']['vitality'] == block
        assert any(
            event.get('type') == 'stage_started'
            and event.get('mode') == 'boss_rush'
            and event.get('curse_stacks') == block
            for event in events
        )


def test_lunatic_stage_three_gate_boss_completes_without_reward():
    seed = 'lunatic-gate-boss'
    state = build_initial_story_state(seed)
    state['stage'] = 3
    state['biome'] = 'garden'
    state['difficulty'] = 'lunatic'
    state['journey_mode'] = 'standard'
    state['map'] = generate_story_map(seed, stage=3, biome='garden', difficulty='lunatic')
    node = state['map']['floors'][15]['nodes'][0]
    assert node['floor'] == 16
    assert node['type'] == 'boss'
    node['status'] = 'current'
    state['current_floor'] = node['floor']
    state['current_node_id'] = node['id']
    starting_gold = state['player']['gold']
    events = []
    _start_combat(
        state,
        node,
        seed,
        events,
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    state['combat']['opening_redraw_pending'] = False
    state['combat']['draw_pile'] = []
    state['combat']['discard_pile'] = []
    state['combat']['exile_pile'] = []
    target = state['combat']['enemies'][0]
    target['health'] = 1
    target['shield'] = 0
    state['combat']['hand'] = [_new_card(state, 'basic')]

    state, events = apply_story_action(
        state,
        'play_card',
        {
            'card_instance_id': state['combat']['hand'][0]['instance_id'],
            'target_id': target['id'],
        },
        seed,
    )

    assert state['phase'] == 'map'
    assert state['reward'] is None
    assert state['combat'] is None
    assert state['player']['gold'] == starting_gold
    completed_node = next(
        item
        for floor in state['map']['floors']
        for item in floor['nodes']
        if item['id'] == node['id']
    )
    assert completed_node['status'] == 'completed'
    assert any(
        event.get('type') == 'combat_victory'
        and event.get('source') == 'lunatic_gate_boss'
        and event.get('gold') == 0
        for event in events
    )


def test_entering_a_new_stage_restores_all_health():
    state = build_initial_story_state('stage-heal')
    state['player']['max_health'] = 120
    state['player']['health'] = 17
    state['phase'] = 'stage_choice'
    state['room'] = {
        'type': 'stage_choice',
        'stage': 2,
        'biomes': ['jungle'],
    }

    state, events = apply_story_action(
        state,
        'choose_stage',
        {'biome': 'jungle', 'curse_id': 'vitality'},
        'stage-heal',
    )

    assert state['stage'] == 2
    assert state['player']['health'] == 120
    assert any(
        event.get('type') == 'heal'
        and event.get('amount') == 103
        and event.get('source') == 'stage_transition'
        for event in events
    )


def test_a_complete_three_stage_journey_can_reach_the_terminal_state():
    seed = 'full-journey'
    state = build_initial_story_state(seed)
    action_count = 0

    while state.get('phase') not in ('complete', 'game_over'):
        action_count += 1
        assert action_count < 1000
        operations = state.get('pending_deck_operations') or []
        if operations:
            operation = operations[0]
            minimum = int(operation.get('minimum', operation.get('count')) or 0)
            state, _ = apply_story_action(
                state,
                'resolve_deck_operation',
                {'selected_card_ids': operation.get('candidate_ids', [])[:minimum]},
                seed,
            )
            continue
        state['player']['health'] = max(100000, int(state['player']['health']))
        state['player']['max_health'] = max(
            100000,
            int(state['player']['max_health']),
        )
        state['player']['gold'] = max(100000, int(state['player']['gold']))
        phase = state['phase']

        if phase == 'journey_setup':
            state, _ = apply_story_action(
                state,
                'start_journey',
                {'biome': 'garden', 'difficulty': 'normal'},
                seed,
            )
            state['blessing_options'] = list(STORY_BLESSINGS)
        elif phase == 'blessing':
            state, _ = apply_story_action(
                state,
                'choose_blessing',
                {'blessing_id': state['blessing_options'][0]},
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
            reward_payload = {}
            if (
                'grab_every_card' in state['player'].get('relics', [])
                and state['reward'].get('cards')
            ):
                first_reward = state['reward']['cards'][0]
                reward_payload['card_id'] = (
                    first_reward.get('card_id')
                    if isinstance(first_reward, dict)
                    else first_reward
                )
            state, _ = apply_story_action(
                state,
                'choose_reward',
                reward_payload,
                seed,
            )
        elif phase == 'room':
            room = state['room']
            raw_options = list(room.get('options', []))
            options = [
                option.get('id') if isinstance(option, dict) else option
                for option in raw_options
            ]
            preferred = {
                'rest': 'heal',
                'chest': 'claim',
                'shop': 'leave',
            }.get(room.get('type'))
            if room.get('type') == 'event':
                raw_option = next(
                    (
                        value for value in raw_options
                        if not isinstance(value, dict) or not value.get('selection')
                    ),
                    raw_options[0],
                )
                option = raw_option.get('id') if isinstance(raw_option, dict) else raw_option
            else:
                option = preferred if preferred in options else next(
                    (
                        value for value in ('pass_by', 'leave', 'escape', 'observe')
                        if value in options
                    ),
                    options[0],
                )
            room_payload = {'option': option}
            if room.get('event_id') == 'card_trader' and option == 'trade_card':
                room_payload['card_instance_id'] = room['trade_candidates'][0]
            state, _ = apply_story_action(
                state,
                'resolve_room',
                room_payload,
                seed,
            )
        elif phase == 'stage_choice':
            state, _ = apply_story_action(
                state,
                'choose_stage',
                {
                    'biome': state['room']['biomes'][0],
                    'curse_id': state['room']['curses'][0],
                },
                seed,
            )
        else:
            raise AssertionError(f'Unhandled story phase: {phase}')

    assert state['phase'] == 'complete'
    assert state['stage'] == 3
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


def test_exact_hand_selection_is_server_validated_and_actively_discarded():
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
    state, events = apply_story_action(
        state,
        'play_card',
        {
            'card_instance_id': card['instance_id'],
            'target_id': target['id'],
            'selected_card_ids': [other['instance_id']],
        },
        'selection',
    )
    assert any(item['instance_id'] == other['instance_id'] for item in state['combat']['discard_pile'])
    assert any(
        event.get('type') == 'card_discarded'
        and event.get('card_instance_id') == other['instance_id']
        and event.get('reason') == 'active'
        for event in events
    )


def test_sewage_makes_hand_free_without_an_initial_card_choice():
    state, _ = _begin_combat('sewage-selection')
    state['combat']['elixir'] = 10
    sewage = _inject_hand_card(state, 'sewage')
    selected = _inject_hand_card(state, 'basic')

    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': sewage['instance_id']},
        'sewage-selection',
    )
    selected_after = next(
        card for card in state['combat']['hand']
        if card['instance_id'] == selected['instance_id']
    )
    assert state['combat']['sewage_active'] is True
    assert selected_after['modifiers']['temporary_free_e'] is True
    assert any(
        card['instance_id'] == sewage['instance_id']
        for card in state['combat']['exile_pile']
    )
    assert not any(event.get('type') == 'card_choice_required' for event in events)


def test_exact_story_card_choices_reject_sublime_cards_as_candidates():
    state, _ = _begin_combat('sublime-selection')
    state['combat']['elixir'] = 10
    amulet = _inject_hand_card(state, 'amulet')
    sublime = _inject_hand_card(state, 'mark')
    ordinary = _inject_hand_card(state, 'basic')
    state['combat']['hand'] = [amulet, sublime, ordinary]
    target = state['combat']['enemies'][0]

    with pytest.raises(StoryActionError) as error:
        apply_story_action(
            state,
            'play_card',
            {
                'card_instance_id': amulet['instance_id'],
                'target_id': target['id'],
                'selected_card_ids': [sublime['instance_id']],
            },
            'sublime-selection',
        )
    assert error.value.code == 'INVALID_CARD_SELECTION'


def test_end_turn_runs_enemy_actions_and_starts_a_fresh_player_turn():
    state, _ = _begin_combat('turn-cycle')
    state, events = apply_story_action(state, 'end_turn', {}, 'turn-cycle')
    assert state['phase'] in ('combat', 'game_over')
    assert any(event['type'] == 'enemy_action' for event in events)
    if state['phase'] == 'combat':
        assert state['combat']['turn'] == 'player'
        assert state['combat']['round'] == 2
        assert len(state['combat']['hand']) <= 10


def test_salt_returns_the_next_actual_damage_to_its_source_immediately():
    seed = 'salt-retaliation'
    state, _ = _begin_combat(seed)
    combat = state['combat']
    enemy = combat['enemies'][0]
    enemy.update({
        'def_id': 'soldier_ant',
        'name': {'zh': '兵蚁', 'en': 'Soldier Ant'},
        'health': 56,
        'max_health': 56,
        'shield': 0,
        'power': 0,
        'move_index': 0,
    })
    combat['enemies'] = [enemy]
    combat['hand'] = []
    combat['elixir'] = 10
    salt = _inject_hand_card(state, 'salt')

    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': salt['instance_id']},
        seed,
    )
    assert state['combat']['shield'] == 3
    assert state['combat']['salt_multipliers'] == [1]

    player_health = state['player']['health']
    enemy_health = state['combat']['enemies'][0]['health']
    state, events = apply_story_action(state, 'end_turn', {}, seed)

    assert state['player']['health'] == player_health - 3
    assert state['combat']['enemies'][0]['health'] == enemy_health - 3
    assert state['combat']['salt_multipliers'] == []
    returned = next(
        event
        for event in events
        if event.get('type') == 'enemy_damage' and event.get('source') == 'salt'
    )
    assert returned['amount'] == 3


def test_fission_does_not_consume_or_repeat_on_another_fission():
    seed = 'fission-excludes-itself'
    state, _ = _begin_combat(seed)
    combat = state['combat']
    combat['hand'] = []
    combat['elixir'] = 10
    first = _inject_hand_card(state, 'fission')
    second = _inject_hand_card(state, 'fission')
    rose = _inject_hand_card(state, 'rose')

    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': first['instance_id']},
        seed,
    )
    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': second['instance_id']},
        seed,
    )
    assert state['combat']['next_skill_repeats'] == 1

    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': rose['instance_id']},
        seed,
    )
    assert state['combat']['shield'] == 10
    assert state['combat']['next_skill_repeats'] == 0


def test_dandelion_seed_can_be_planted_at_a_rest_site():
    seed = 'plant-dandelion'
    state = _journey_state(seed)
    seed_card = _new_card(state, 'dandelion_seed')
    state['player']['deck'].append(seed_card)
    state['phase'] = 'room'
    state['room'] = {
        'type': 'rest',
        'options': ['plant_dandelion'],
    }

    state, events = apply_story_action(
        state,
        'resolve_room',
        {'option': 'plant_dandelion'},
        seed,
    )

    assert all(
        card['instance_id'] != seed_card['instance_id']
        for card in state['player']['deck']
    )
    assert 'dandelion_blessing' in state['player']['relics']
    assert any(
        event.get('type') == 'card_removed'
        and event.get('source') == 'plant_dandelion'
        for event in events
    )
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
    assert state['combat']['shield'] == 7


def test_yin_yang_shuffles_the_other_hand_and_draws_one_extra_card():
    seed = 'yin-yang'
    state, _ = _begin_combat(seed)
    combat = state['combat']
    combat['hand'] = []
    combat['draw_pile'] = []
    combat['discard_pile'] = []
    yin_yang = _inject_hand_card(state, 'yin_yang')
    others = [
        _inject_hand_card(state, 'basic'),
        _inject_hand_card(state, 'rose'),
    ]
    for card_id in ('bone', 'rock', 'triangle'):
        combat['draw_pile'].append(_new_card(state, card_id))

    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': yin_yang['instance_id']},
        seed,
    )

    assert len(state['combat']['hand']) == 3
    assert yin_yang in state['combat']['exile_pile']
    assert any(event.get('type') == 'hand_shuffled' for event in events)
    assert all(
        card not in state['combat']['discard_pile']
        for card in others
    )


def test_occultist_life_choice_loses_thirty_percent_max_health():
    seed = 'occultist-life'
    state = _journey_state(seed)
    state['phase'] = 'room'
    state['room'] = {
        'type': 'event',
        'event_id': 'occultist',
        'options': ['occult_life'],
    }
    state['player']['max_health'] = 100
    state['player']['health'] = 100

    state, _ = apply_story_action(
        state,
        'resolve_room',
        {'option': 'occult_life'},
        seed,
    )

    assert state['player']['max_health'] == 70
    assert state['player']['health'] == 70
    assert 'world_tree_leaf' in state['player']['relics']


def test_turn_start_resets_elixir_and_magic_instead_of_carrying_them():
    state, _ = _begin_combat('turn-resources')
    state['player']['health'] = 999
    state['player']['max_health'] = 999
    state['combat']['elixir'] = 7
    state['combat']['magic'] = 14

    state, events = apply_story_action(state, 'end_turn', {}, 'turn-resources')

    assert state['phase'] == 'combat'
    assert state['combat']['elixir'] == state['player']['max_elixir'] == 3
    assert state['combat']['magic'] == state['player']['magic'] == 0
    assert any(
        event.get('type') == 'elixir'
        and event.get('amount') == 3
        and event.get('before') == 0
        and event.get('after') == 3
        for event in events
    )


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
    damage = [event for event in events if event['type'] == 'enemy_damage']
    assert len(damage) == 3
    assert [event['hit_index'] for event in damage] == [1, 2, 3]
    assert all(event['hit_count'] == 3 for event in damage)
    assert before - state['combat']['enemies'][0]['health'] == 27


def test_nuke_at_zero_elixir_deals_no_damage():
    state, _ = _begin_combat('nuke-zero')
    state['combat']['elixir'] = 0
    card = _inject_hand_card(state, 'nuke')
    target = state['combat']['enemies'][0]
    before = target['health']

    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': target['id']},
        'nuke-zero',
    )

    assert state['combat']['elixir'] == 0
    assert state['combat']['enemies'][0]['health'] == before
    assert not any(event['type'] == 'enemy_damage' for event in events)
    assert any(event['type'] == 'card_played' for event in events)


def test_nuke_damage_and_prediction_receive_fusion_multiplier():
    state, _ = _begin_combat('nuke-fusion')
    state['combat']['elixir'] = 2
    state['combat']['next_attack_multiplier'] = 2
    card = _inject_hand_card(state, 'nuke')
    target = state['combat']['enemies'][0]
    target['shield'] = 0
    before = target['health']
    _refresh_combat_projections(state)

    prediction = state['combat']['damage_predictions'][card['instance_id']]
    assert prediction['by_target'][target['id']]['hits'] == [18, 18]
    assert prediction['by_target'][target['id']]['total'] == 36

    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': target['id']},
        'nuke-fusion',
    )

    damage = [event for event in events if event['type'] == 'enemy_damage']
    assert [event['amount'] for event in damage] == [18, 18]
    assert before - state['combat']['enemies'][0]['health'] == 36
    assert state['combat']['next_attack_multiplier'] == 1


def test_enemy_dodge_consumes_one_stack_per_multihit_segment():
    state, _ = _begin_combat('story-enemy-dodge-multihit')
    enemy = state['combat']['enemies'][0]
    enemy.update({
        'health': 100,
        'max_health': 100,
        'shield': 0,
        'evade': 1,
        'hidden': 0,
        'evil_eye': 0,
        'vulnerable': 0,
    })
    events = []

    dealt = _enemy_physical_damage(
        state,
        enemy,
        5,
        3,
        events,
        'dodge-test',
        values={'tags': ()},
    )

    damage = [event for event in events if event.get('type') == 'enemy_damage']
    assert dealt == 10
    assert enemy['health'] == 90
    assert enemy['evade'] == 0
    assert [event['amount'] for event in damage] == [0, 5, 5]
    assert [event['hit_index'] for event in damage] == [1, 2, 3]


def test_multiple_enemy_dodge_stacks_each_prevent_one_multihit_segment():
    state, _ = _begin_combat('story-enemy-dodge-stacks')
    enemy = state['combat']['enemies'][0]
    enemy.update({
        'health': 100,
        'max_health': 100,
        'shield': 0,
        'evade': 2,
        'hidden': 0,
        'evil_eye': 0,
        'vulnerable': 0,
    })
    events = []

    dealt = _enemy_physical_damage(
        state,
        enemy,
        5,
        3,
        events,
        'dodge-stack-test',
        values={'tags': ()},
    )

    damage = [event for event in events if event.get('type') == 'enemy_damage']
    assert dealt == 5
    assert enemy['health'] == 95
    assert enemy['evade'] == 0
    assert [event['amount'] for event in damage] == [0, 0, 5]


def test_precision_consumes_one_enemy_dodge_stack_and_halves_only_that_hit():
    state, _ = _begin_combat('story-enemy-precision-dodge')
    enemy = state['combat']['enemies'][0]
    enemy.update({
        'health': 100,
        'max_health': 100,
        'shield': 0,
        'evade': 1,
        'hidden': 0,
        'evil_eye': 0,
        'vulnerable': 0,
    })
    events = []

    dealt = _enemy_physical_damage(
        state,
        enemy,
        5,
        2,
        events,
        'precision-dodge-test',
        values={'tags': ('precise',)},
    )

    damage = [event for event in events if event.get('type') == 'enemy_damage']
    assert dealt == 8
    assert enemy['health'] == 92
    assert enemy['evade'] == 0
    assert [event['amount'] for event in damage] == [3, 5]


def test_story_damage_prediction_consumes_dodge_per_hit():
    state, _ = _begin_combat('story-dodge-prediction')
    card = _inject_hand_card(state, 'lightning')
    enemy = state['combat']['enemies'][0]
    enemy.update({
        'health': 100,
        'max_health': 100,
        'shield': 0,
        'evade': 1,
        'hidden': 0,
        'evil_eye': 0,
        'vulnerable': 0,
    })

    _refresh_combat_projections(state)

    prediction = state['combat']['damage_predictions'][card['instance_id']]
    assert prediction['by_target'][enemy['id']]['hits'] == [0, 3]
    assert prediction['by_target'][enemy['id']]['total'] == 3


def test_player_damage_applies_power_before_multiplier_and_vulnerable_last():
    seed = 'story-player-damage-order'
    state, _ = _begin_combat(seed)
    state['combat']['power'] = 3
    state['combat']['next_attack_multiplier'] = 2
    card = _inject_hand_card(state, 'basic')
    target = state['combat']['enemies'][0]
    target['health'] = target['max_health'] = 999
    target['shield'] = 0
    target['vulnerable'] = 1
    _refresh_combat_projections(state)

    prediction = state['combat']['damage_predictions'][card['instance_id']]
    assert prediction['by_target'][target['id']]['hits'] == [27]

    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': target['id']},
        seed,
    )
    damage = [event for event in events if event['type'] == 'enemy_damage']
    assert [event['amount'] for event in damage] == [27]


def test_acid_actively_discarding_azalea_runs_azalea_effect():
    seed = 'story-acid-azalea'
    state, _ = _begin_combat(seed)
    acid = _new_card(state, 'acid')
    azalea = _new_card(state, 'azalea')
    state['combat']['hand'] = [acid, azalea]
    target = state['combat']['enemies'][0]
    target['health'] = target['max_health'] = 999
    state['combat']['shield'] = 0

    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': acid['instance_id'], 'target_id': target['id']},
        seed,
    )

    assert state['combat']['shield'] == 3
    assert any(
        card['instance_id'] == azalea['instance_id']
        for card in state['combat']['discard_pile']
    )
    assert any(
        event.get('type') == 'card_discarded'
        and event.get('card_instance_id') == azalea['instance_id']
        and event.get('reason') == 'active'
        for event in events
    )


def test_cutter_damage_and_prediction_receive_fusion_multiplier():
    state, _ = _begin_combat('cutter-fusion')
    state['combat']['shield'] = 12
    state['combat']['next_attack_multiplier'] = 2
    card = _inject_hand_card(state, 'cutter')
    target = state['combat']['enemies'][0]
    target['health'] = 200
    target['max_health'] = 200
    target['shield'] = 0
    _refresh_combat_projections(state)

    prediction = state['combat']['damage_predictions'][card['instance_id']]
    assert prediction['by_target'][target['id']]['hits'] == [24]
    assert prediction['by_target'][target['id']]['total'] == 24

    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': target['id']},
        'cutter-fusion',
    )

    damage = [event for event in events if event['type'] == 'enemy_damage']
    assert [event['amount'] for event in damage] == [24]
    assert state['combat']['enemies'][0]['health'] == 176
    assert state['combat']['next_attack_multiplier'] == 1


def test_status_count_attack_uses_shared_fusion_calculation():
    state, _ = _begin_combat('antler-fusion')
    state['combat']['next_attack_multiplier'] = 2
    card = _inject_hand_card(state, 'antler')
    target = state['combat']['enemies'][0]
    target['health'] = 200
    target['max_health'] = 200
    target['shield'] = 0
    for status in (
        'power',
        'temporary_power',
        'endurance',
        'weak',
        'vulnerable',
        'fragile',
        'evade',
        'poison',
        'stun',
        'reflection',
        'wither',
        'broken',
        'rockfall',
    ):
        target[status] = 0
    target['poison'] = 1
    _refresh_combat_projections(state)

    prediction = state['combat']['damage_predictions'][card['instance_id']]
    assert prediction['by_target'][target['id']]['hits'] == [12]

    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': target['id']},
        'antler-fusion',
    )

    damage = [event for event in events if event['type'] == 'enemy_damage']
    assert [event['amount'] for event in damage] == [12]
    assert state['combat']['enemies'][0]['health'] == 188


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
    state['combat']['shield'] = 2
    health = state['player']['health']
    card = _inject_hand_card(state, 'basic')
    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': enemy['id']},
        'broken-duration',
    )
    assert state['player']['health'] == health - 1
    assert state['combat']['shield'] == 0
    broken_damage = next(
        event
        for event in events
        if event.get('type') == 'player_damage' and event.get('source') == 'broken'
    )
    target_damage_index = next(
        index
        for index, event in enumerate(events)
        if event.get('type') == 'enemy_damage'
    )
    broken_damage_index = events.index(broken_damage)
    assert target_damage_index < broken_damage_index
    assert broken_damage['amount'] == 1
    assert broken_damage['history'] == [{
        'before': health,
        'after': health - 1,
        'blocked': 2,
    }]
    assert broken_damage['presentation_patch']['combat']['effects']['shield'] == 0
    assert broken_damage['presentation_patch']['player']['health'] == health - 1


def test_player_shield_also_blocks_poison_damage():
    state, _ = _begin_combat('poison-shield')
    combat = state['combat']
    combat['shield'] = 3
    combat['poison'] = 5
    for enemy in combat['enemies']:
        enemy['stun'] = 1
    health = state['player']['health']

    state, events = apply_story_action(
        state,
        'end_turn',
        {},
        'poison-shield',
    )

    assert state['player']['health'] == health - 2
    assert state['combat']['poison'] == 2
    poison_damage = next(
        event
        for event in events
        if event.get('type') == 'player_damage' and event.get('source') == 'poison'
    )
    assert poison_damage['amount'] == 2
    assert poison_damage['history'] == [{
        'before': health,
        'after': health - 2,
        'blocked': 3,
    }]
    assert poison_damage['presentation_patch']['combat']['effects']['shield'] == 0
    assert any(
        event.get('presentation_patch', {}).get('combat', {}).get('effects', {}).get('poison') == 2
        for event in events
    )


def test_broken_damage_defeats_player_even_when_the_card_kills_last_enemy():
    state, _ = _begin_combat('broken-double-defeat')
    enemy = state['combat']['enemies'][0]
    enemy['health'] = 1
    enemy['shield'] = 0
    enemy['reflection'] = 0
    state['combat']['enemies'] = [enemy]
    state['combat']['broken'] = 3
    state['combat']['shield'] = 0
    state['player']['health'] = 2
    card = _inject_hand_card(state, 'basic')

    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': enemy['id']},
        'broken-double-defeat',
    )

    assert state['player']['health'] == 0
    assert state['phase'] == 'game_over'
    assert 'recovery_checkpoint' not in state
    assert any(event.get('type') == 'game_over' for event in events)
    assert not any(event.get('type') == 'combat_victory' for event in events)
    terminal_state = copy.deepcopy(state)
    with pytest.raises(StoryActionError) as error:
        apply_story_action(state, 'end_turn', {}, 'broken-double-defeat')
    assert error.value.code == 'END_TURN_NOT_ALLOWED'
    assert state == terminal_state


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
        'max_health': 172,
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
    assert wasps[0]['wither'] == 4
    assert any(event['type'] == 'enemy_death_trigger' for event in events)
    defeat = next(event for event in events if event['type'] == 'enemy_defeated')
    summon = next(event for event in events if event['type'] == 'enemy_summoned')
    assert defeat['enemy_id'] == enemy['id']
    assert defeat['presentation']['motion'] == 'defeat'
    assert summon['actor_id'] == enemy['id']
    assert summon['target_ids'] == [wasps[0]['id']]
    assert summon['enemy']['id'] == wasps[0]['id']
    assert summon['enemy']['health'] == wasps[0]['max_health']
    assert summon['presentation']['motion'] == 'summon'
    assert defeat['sequence'] < summon['sequence']


def test_enemy_defeat_events_are_emitted_once_and_parallelized():
    seed = 'enemy-defeat-contract'
    state, _ = _begin_combat(seed)
    state['combat']['opening_redraw_pending'] = False
    first = state['combat']['enemies'][0]
    first['health'] = 1
    first['shield'] = 0
    second = copy.deepcopy(first)
    second['id'] = 'enemy-defeat-2'
    state['combat']['enemies'] = [first, second]
    card = _inject_hand_card(state, 'lightning')

    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id']},
        seed,
    )

    defeats = [
        event for event in events
        if event.get('type') == 'enemy_defeated'
    ]
    assert state['phase'] == 'reward'
    assert [event['enemy_id'] for event in defeats] == [first['id'], second['id']]
    assert len({event['enemy_id'] for event in defeats}) == 2
    assert len({event['parallel_group'] for event in defeats}) == 1
    assert defeats[0]['parallel_group'] is not None
    assert all(event['actor_id'] == 'player' for event in defeats)
    assert all(event['source_card_instance_id'] == card['instance_id'] for event in defeats)
    assert all(event['source_definition_id'] == card['def_id'] for event in defeats)
    assert all(event['after'] == 0 for event in defeats)
    assert all(event['presentation']['motion'] == 'defeat' for event in defeats)


def test_cooldown_relic_blocks_actions_until_opening_redraw_is_resolved():
    seed = 'cooldown'
    state = _journey_state(seed)
    state['player']['relics'].append('cooldown')
    state, _ = apply_story_action(state, 'choose_blessing', {'blessing_id': 'max_health'}, seed)
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


def test_opening_lightning_emits_parallel_damage_for_combat_entrance():
    seed = 'opening-lightning-animation'
    state = _journey_state(seed)
    state['player']['relics'].append('opening_lightning')
    state, _ = apply_story_action(state, 'choose_blessing', {'blessing_id': 'max_health'}, seed)
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
    damage_events = [
        event
        for event in events
        if event.get('type') == 'enemy_damage'
        and event.get('source') == 'opening_lightning'
    ]
    assert damage_events
    assert len(damage_events) == len(state['combat']['enemies'])
    assert all(event.get('amount') == 9 for event in damage_events)
    assert all(event.get('parallel_group') == 'opening_lightning' for event in damage_events)


def test_occultist_event_adds_the_defined_cards_and_completes():
    seed = 'occultist-event'
    state = _journey_state(seed)
    state, _ = apply_story_action(state, 'choose_blessing', {'blessing_id': 'max_health'}, seed)
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
    state = _journey_state(seed)
    state, _ = apply_story_action(state, 'choose_blessing', {'blessing_id': 'max_health'}, seed)
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
    assert [enemy['def_id'] for enemy in state['combat']['enemies']] == ['spider_yoba']
    assert state['combat']['enemies'][0]['health'] == 51


def test_yoba_spider_identifiers_and_asset_use_the_correct_spelling():
    obsolete_id = 'spider_' + 'yu' + 'ba'
    assert obsolete_id not in STORY_ENEMIES
    assert obsolete_id not in STORY_ENEMY_IMAGE_URLS
    assert STORY_ENEMIES['spider_yoba']['name']['en'] == 'Yoba Spider'
    image_url = STORY_ENEMY_IMAGE_URLS['spider_yoba']
    assert image_url.endswith('/spider-yoba.svg')
    assert (Path(__file__).resolve().parents[1] / image_url.lstrip('/')).is_file()


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


def test_refresh_checkpoint_restores_the_initial_combat_state():
    seed = 'combat-checkpoint'
    state, _ = _begin_combat(seed)
    checkpoint = state.get('recovery_checkpoint')
    assert checkpoint
    assert checkpoint['kind'] == 'combat_entry'
    expected_combat = copy.deepcopy(checkpoint['state']['combat'])

    state['combat']['round'] = 99
    state['combat']['elixir'] = 0
    state['player']['health'] = 1

    state, events = apply_story_action(state, 'resume_node', {}, seed)

    assert state['combat'] == expected_combat
    assert state['recovery_checkpoint']['kind'] == 'combat_entry'
    assert any(event.get('type') == 'checkpoint_restored' for event in events)


def test_exile_pile_survives_turn_boundary_and_refresh_recovery():
    seed = 'persistent-exile-checkpoint'
    state, _ = _begin_combat(seed)
    combat = state['combat']
    combat['opening_redraw_pending'] = False
    target = combat['enemies'][0]
    mark = _inject_hand_card(state, 'mark')

    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': mark['instance_id'], 'target_id': target['id']},
        seed,
    )
    assert [card['instance_id'] for card in state['combat']['exile_pile']] == [
        mark['instance_id'],
    ]
    assert state['recovery_checkpoint']['kind'] == 'combat_progress'

    state, _ = apply_story_action(state, 'end_turn', {}, seed)
    assert state['combat']['round'] == 2
    assert [card['instance_id'] for card in state['combat']['exile_pile']] == [
        mark['instance_id'],
    ]
    assert state['recovery_checkpoint']['kind'] == 'combat_progress'

    state['combat']['exile_pile'] = []
    state, _ = apply_story_action(state, 'resume_node', {}, seed)
    assert state['combat']['round'] == 2
    assert [card['instance_id'] for card in state['combat']['exile_pile']] == [
        mark['instance_id'],
    ]


def test_event_progress_checkpoint_restores_the_latest_stable_stage():
    seed = 'event-progress-checkpoint'
    state = _journey_state(seed)
    state, _ = apply_story_action(
        state,
        'choose_blessing',
        {'blessing_id': 'max_health'},
        seed,
    )
    lottery_choice = {
        'id': 'lottery_draw',
        'label': {'zh': '抽奖', 'en': 'Draw'},
        'description': {'zh': '花费50G。', 'en': 'Pay 50 G.'},
    }
    state['phase'] = 'room'
    state['player']['gold'] = 200
    state['room'] = {
        'type': 'event',
        'event_id': 'mystery_lottery',
        'attempts': 0,
        'stage_id': 'intro',
        'history': [],
        'choices': [lottery_choice],
        'options': [lottery_choice],
    }

    state, _ = apply_story_action(
        state,
        'resolve_room',
        {'option': 'lottery_draw'},
        seed,
    )
    expected_gold = state['player']['gold']
    expected_health = state['player']['health']
    assert state['room']['attempts'] == 1
    assert state['room']['stage_id'] == 'attempt_1'
    assert len(state['room']['history']) == 1
    assert state['recovery_checkpoint']['kind'] == 'room_progress'

    state['room']['attempts'] = 99
    state['player']['gold'] = 999
    state['player']['health'] = 1
    state, _ = apply_story_action(state, 'resume_node', {}, seed)

    assert state['room']['attempts'] == 1
    assert state['room']['stage_id'] == 'attempt_1'
    assert state['player']['gold'] == expected_gold
    assert state['player']['health'] == expected_health


def test_shop_progress_checkpoint_does_not_restore_a_removed_card():
    seed = 'shop-progress-checkpoint'
    state = _journey_state(seed)
    state, _ = apply_story_action(
        state,
        'choose_blessing',
        {'blessing_id': 'max_health'},
        seed,
    )
    removed = state['player']['deck'][0]
    state['phase'] = 'room'
    state['player']['gold'] = 100
    state['room'] = {
        'type': 'shop',
        'options': ['remove_card', 'leave'],
        'cards': [],
        'relics': [],
        'remove_price': 25,
        'upgrade_price': 25,
    }

    state, _ = apply_story_action(
        state,
        'resolve_room',
        {
            'option': 'remove_card',
            'card_instance_id': removed['instance_id'],
        },
        seed,
    )
    assert all(
        card['instance_id'] != removed['instance_id']
        for card in state['player']['deck']
    )
    assert state['player']['gold'] == 75
    assert state['recovery_checkpoint']['kind'] == 'room_progress'

    state['player']['deck'].append(copy.deepcopy(removed))
    state['player']['gold'] = 999
    state, _ = apply_story_action(state, 'resume_node', {}, seed)

    assert all(
        card['instance_id'] != removed['instance_id']
        for card in state['player']['deck']
    )
    assert state['player']['gold'] == 75


def test_legacy_reward_state_does_not_grant_its_gold_twice():
    seed = 'legacy-layered-reward'
    state = _journey_state(seed)
    state, _ = apply_story_action(
        state,
        'choose_blessing',
        {'blessing_id': 'max_health'},
        seed,
    )
    state['phase'] = 'reward'
    state['player']['gold'] = 75
    state['reward'] = {
        'gold': 75,
        'cards': [],
        'relic': None,
        'room_type': 'combat',
    }

    state, _ = apply_story_action(state, 'choose_reward', {}, seed)

    assert state['player']['gold'] == 75
    assert state['phase'] == 'map'


def test_legacy_combat_without_checkpoint_remains_playable():
    seed = 'legacy-combat-without-checkpoint'
    state, _ = _begin_combat(seed)
    state.pop('recovery_checkpoint', None)
    state.pop('presentation_event_counter', None)
    state['combat']['opening_redraw_pending'] = False
    target = state['combat']['enemies'][0]
    card = _inject_hand_card(state, 'basic')

    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': target['id']},
        seed,
    )

    assert state['phase'] in ('combat', 'reward')
    assert events
    assert all(event['event_id'].startswith('story-event-') for event in events)
    assert int(state['presentation_event_counter']) == len(events)


def test_layered_rewards_are_claimed_once_and_survive_checkpoint_restore():
    seed = 'layered-reward'
    state = build_initial_story_state(seed)
    state['phase'] = 'reward'
    state['reward'] = {
        'gold': 18,
        'cards': [{'card_id': 'basic', 'upgraded': False}],
        'relic': None,
        'room_type': 'combat',
        'claims': {'gold': False, 'card': False, 'relic': True},
        'selected_card_id': None,
        'card_skipped': False,
    }
    initial_gold = state['player']['gold']

    state, events = apply_story_action(
        state,
        'choose_reward',
        {'reward_type': 'gold'},
        seed,
    )
    assert state['phase'] == 'reward'
    assert state['player']['gold'] == initial_gold + 18
    assert state['reward']['claims']['gold'] is True
    assert state['recovery_checkpoint']['kind'] == 'reward_progress'
    assert any(
        event.get('type') == 'reward_claimed'
        and event.get('reward_type') == 'gold'
        for event in events
    )

    state['player']['gold'] += 999
    state, _ = apply_story_action(state, 'resume_node', {}, seed)
    assert state['player']['gold'] == initial_gold + 18

    with pytest.raises(StoryActionError) as exc_info:
        apply_story_action(
            state,
            'choose_reward',
            {'reward_type': 'gold'},
            seed,
        )
    assert exc_info.value.code == 'REWARD_ALREADY_CLAIMED'

    state, _ = apply_story_action(
        state,
        'choose_reward',
        {'reward_type': 'card'},
        seed,
    )
    assert state['reward']['card_skipped'] is True
    state, _ = apply_story_action(
        state,
        'choose_reward',
        {'reward_type': 'continue'},
        seed,
    )
    assert state['phase'] == 'map'
    assert 'recovery_checkpoint' not in state


@pytest.mark.parametrize('claim_option', ('claim_gold', 'claim_relic'))
def test_chest_rewards_can_be_claimed_independently_or_left_behind(claim_option):
    seed = f'optional-chest:{claim_option}'
    state = _journey_state(seed)
    state, _ = apply_story_action(
        state,
        'choose_blessing',
        {'blessing_id': 'max_health'},
        seed,
    )
    node = next(
        node
        for floor in state['map']['floors']
        for node in floor['nodes']
        if node['status'] == 'available'
    )
    node['type'] = 'chest'
    state, _ = apply_story_action(
        state,
        'enter_node',
        {'node_id': node['id']},
        seed,
    )
    state['room']['relic'] = 'ruthless'
    initial_gold = state['player']['gold']
    initial_relics = list(state['player']['relics'])
    room_gold = state['room']['gold']

    state, events = apply_story_action(
        state,
        'resolve_room',
        {'option': claim_option},
        seed,
    )

    assert state['phase'] == 'room'
    assert state['room']['claims'][claim_option.removeprefix('claim_')] is True
    if claim_option == 'claim_gold':
        assert state['player']['gold'] == initial_gold + room_gold
        assert state['player']['relics'] == initial_relics
    else:
        assert state['player']['gold'] == initial_gold
        assert len(state['player']['relics']) == len(initial_relics) + 1
    assert any(
        event.get('type') == 'chest_claimed'
        and event.get('reward_type') == claim_option.removeprefix('claim_')
        for event in events
    )

    state, events = apply_story_action(
        state,
        'resolve_room',
        {'option': 'leave'},
        seed,
    )
    assert state['phase'] == 'map'
    assert any(event.get('type') == 'room_left' for event in events)


def test_directly_leaving_a_reward_skips_every_unclaimed_part():
    seed = 'optional-combat-reward'
    state, _ = _begin_combat(seed)
    initial_gold = state['player']['gold']
    initial_deck_size = len(state['player']['deck'])
    initial_relics = list(state['player']['relics'])
    state['phase'] = 'reward'
    state['combat'] = None
    state['reward'] = {
        'gold': 40,
        'cards': [{'card_id': 'basic', 'upgraded': False}],
        'relic': 'ruthless',
        'claims': {'gold': False, 'card': False, 'relic': False},
        'room_type': 'combat',
    }

    state, events = apply_story_action(
        state,
        'choose_reward',
        {'reward_type': 'leave'},
        seed,
    )

    assert state['phase'] == 'map'
    assert state['player']['gold'] == initial_gold
    assert len(state['player']['deck']) == initial_deck_size
    assert state['player']['relics'] == initial_relics
    reward_left = next(event for event in events if event.get('type') == 'reward_left')
    assert set(reward_left['skipped']) == {'gold', 'card', 'relic'}


def test_story_events_expose_order_and_card_source_metadata():
    seed = 'presentation-contract'
    state, _ = _begin_combat(seed)
    state['combat']['opening_redraw_pending'] = False
    target = state['combat']['enemies'][0]
    target['health'] = 999
    target['max_health'] = 999
    card = _inject_hand_card(state, 'basic')

    _, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': target['id']},
        seed,
    )

    assert [event['sequence'] for event in events] == list(range(1, len(events) + 1))
    assert len({event['event_id'] for event in events}) == len(events)
    assert all(isinstance(event.get('target_ids'), list) for event in events)
    assert all(event.get('kind') == event.get('type') for event in events)
    assert all('hit_index' in event and 'hit_count' in event for event in events)
    assert all('before' in event and 'after' in event for event in events)
    assert all('parallel_group' in event for event in events)
    assert all(isinstance(event.get('presentation'), dict) for event in events)
    damage = next(event for event in events if event.get('type') == 'enemy_damage')
    assert damage['source_card_instance_id'] == card['instance_id']
    assert damage['source_definition_id'] == card['def_id']
    assert damage['actor_id'] == 'player'
    assert damage['before'] == 999
    assert damage['after'] < damage['before']


def test_wide_multihit_events_parallelize_matching_hits_only():
    seed = 'presentation-parallel'
    state, _ = _begin_combat(seed)
    state['combat']['opening_redraw_pending'] = False
    first = state['combat']['enemies'][0]
    first['health'] = first['max_health'] = 999
    second = copy.deepcopy(first)
    second['id'] = 'enemy-parallel-2'
    state['combat']['enemies'] = [first, second]
    card = _inject_hand_card(state, 'lightning')

    _, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id']},
        seed,
    )

    damage = [event for event in events if event.get('type') == 'enemy_damage']
    assert len(damage) == 4
    groups_by_hit = {
        hit_index: {
            event['parallel_group']
            for event in damage
            if event['hit_index'] == hit_index
        }
        for hit_index in (1, 2)
    }
    assert all(len(groups) == 1 and None not in groups for groups in groups_by_hit.values())
    assert groups_by_hit[1] != groups_by_hit[2]
    assert {
        tuple(event['target_ids'])
        for event in damage
        if event['hit_index'] == 1
    } == {(first['id'],), (second['id'],)}


def test_enemy_intent_uses_structured_entries_and_current_damage_modifiers():
    state, _ = _begin_combat('structured-intent')
    enemy = state['combat']['enemies'][0]
    definition = STORY_ENEMIES[enemy['def_id']]
    move_index = next(
        index
        for index, move in enumerate(definition['moves'])
        if any(effect.get('type') == 'damage' for effect in move['effects'])
    )
    move = definition['moves'][move_index]
    damage_effect = next(effect for effect in move['effects'] if effect.get('type') == 'damage')
    enemy['move_index'] = move_index
    enemy['power'] = 4
    state['combat']['vulnerable'] = 1

    intent = _enemy_intent(state, enemy)
    attack = next(entry for entry in intent['entries'] if entry['kind'] == 'attack')
    expected = int((int(damage_effect['amount']) + 4) * 1.5)

    assert attack['amount'] == expected
    assert attack['hits'] == int(damage_effect.get('hits') or 1)
    assert attack['target'] == 'player'
    assert attack['summary'] in intent['summary']


def test_summon_intent_names_the_enemy_that_will_be_summoned():
    state, _ = _begin_combat('summon-intent-name')
    enemy = state['combat']['enemies'][0]
    enemy['def_id'] = 'hive'
    enemy['name'] = STORY_ENEMIES['hive']['name']
    enemy['move_index'] = 0

    intent = _enemy_intent(state, enemy)
    summon = next(entry for entry in intent['entries'] if entry['kind'] == 'summon')

    assert summon['enemy_id'] == 'bee'
    assert summon['enemy_name'] == STORY_ENEMIES['bee']['name']
    assert summon['amount'] == 1
    assert '蜜蜂' in intent['summary']


def test_clear_status_intent_is_structured_instead_of_leaking_internal_effect_name():
    state, _ = _begin_combat('clear-status-intent')
    enemy = state['combat']['enemies'][0]
    enemy['def_id'] = 'cactus'
    enemy['name'] = STORY_ENEMIES['cactus']['name']
    enemy['forced_move_index'] = 1

    intent = _enemy_intent(state, enemy)
    clear = next(entry for entry in intent['entries'] if entry['kind'] == 'clear_status')

    assert clear['status'] == 'reflection'
    assert 'clear_status' not in intent['summary']
