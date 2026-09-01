from pathlib import Path

import pytest

from story_content import STORY_CARDS, STORY_ENCOUNTERS, STORY_ENEMIES, STORY_TRAITS
from story_engine import (
    StoryActionError,
    _check_combat_end,
    _draw_cards,
    _enemy_raw_damage,
    _finish_combat,
    _gain_shield,
    _mechanical_flower_turn,
    _new_card,
    _notify_exiled,
    _resolve_enemy_effect,
    _start_combat,
    apply_story_action,
)
from story_mode import build_initial_story_state, generate_boss_rush_map


def _factory_combat(enemy_ids, seed='factory-v6'):
    state = build_initial_story_state(seed)
    state['stage'] = 3
    state['biome'] = 'factory'
    state['difficulty'] = 'normal'
    events = []
    _start_combat(
        state,
        {'type': 'combat'},
        seed,
        events,
        encounter_override=[{'def_id': enemy_id} for enemy_id in enemy_ids],
    )
    return state, events


def _enemy(state, def_id):
    return next(
        enemy for enemy in state['combat']['enemies']
        if enemy['def_id'] == def_id
    )


def test_factory_v6_content_and_images_are_registered():
    project_root = Path(__file__).resolve().parents[1]
    expected_enemies = {
        'mechanical_flower', 'smoke', 'brick_pile', 'mechanical_rat',
        'broken_machine', 'chimney', 'generator',
    }
    for enemy_id in expected_enemies:
        definition = STORY_ENEMIES[enemy_id]
        assert (project_root / definition['image_url'].removeprefix('/')).is_file()

    expected_trait_images = {
        'toxic_pressure': 'toxic-pressure.svg',
        'psionic_sustain': 'psionic-binding.svg',
        'hiding': 'hiding.svg',
        'cover': 'cover.svg',
        'injured_summon': 'injured-summon.svg',
    }
    for trait_id, filename in expected_trait_images.items():
        image_url = STORY_TRAITS[trait_id]['image_url']
        assert image_url.endswith(filename)
        assert (project_root / image_url.removeprefix('/')).is_file()

    assert STORY_TRAITS['psionic_sustain']['name'] == {
        'zh': '灵能绑定',
        'en': 'Psionic Binding',
    }
    assert STORY_ENEMIES['chimney']['traits'] == ('injured_summon',)
    assert STORY_ENEMIES['chimney']['initial']['injured_summon'] == 100

    factory_groups = STORY_ENCOUNTERS['factory']
    encountered = {
        spec if isinstance(spec, str) else spec['def_id']
        for group in factory_groups.values()
        for encounter in group
        for spec in encounter
    }
    assert expected_enemies <= encountered
    assert STORY_CARDS['bamboo']['type'] == 'thorn'
    assert 'exile' in STORY_CARDS['factory_waste']['tags']
    assert any(
        effect['type'] == 'self_swift'
        for effect in STORY_CARDS['seed']['effects']
    )


def test_obstacles_apply_and_remove_their_own_blockade_stacks():
    state, _ = _factory_combat(['brick_pile', 'soldier_ant'], 'brick-blockade')
    brick = _enemy(state, 'brick_pile')
    assert state['combat']['blockade'] == 2

    events = []
    _enemy_raw_damage(state, brick, 999, events, 'test', player_caused=True)
    _check_combat_end(state, 'brick-blockade', events)

    assert state['combat']['blockade'] == 0
    assert any(
        event.get('type') == 'status_decay'
        and event.get('status') == 'blockade'
        and event.get('source') == 'obstacle'
        for event in events
    )


def test_smoke_death_applies_toxic_pressure_to_the_player():
    state, _ = _factory_combat(['smoke', 'soldier_ant'], 'smoke-pressure')
    smoke = _enemy(state, 'smoke')
    events = []

    _enemy_raw_damage(state, smoke, 999, events, 'test', player_caused=True)
    _check_combat_end(state, 'smoke-pressure', events)

    assert state['combat']['toxic_poison'] == 2
    assert any(
        event.get('type') == 'status'
        and event.get('status') == 'toxic_poison'
        and event.get('source') == 'smoke'
        for event in events
    )


def test_broken_machine_reveals_its_rat_and_does_not_block_victory():
    state, _ = _factory_combat(
        ['broken_machine', 'broken_machine', 'mechanical_rat'],
        'rat-cover',
    )
    cover = _enemy(state, 'broken_machine')
    rat = _enemy(state, 'mechanical_rat')
    rat['hidden'] = 1
    rat['hidden_cover_id'] = cover['id']
    events = []

    _enemy_raw_damage(state, cover, 20, events, 'test', player_caused=True)
    assert cover['health'] == 1
    assert rat['hidden'] == 0

    _enemy_raw_damage(state, rat, 999, events, 'test', player_caused=True)
    assert _check_combat_end(state, 'rat-cover', events) is True
    assert state['phase'] == 'reward'
    assert cover['health'] == 1


def test_chimney_summons_smoke_for_each_100_health_damage():
    state, _ = _factory_combat(['chimney', 'soldier_ant'], 'chimney-smoke')
    chimney = _enemy(state, 'chimney')
    assert chimney['injured_summon'] == 100
    events = []

    _enemy_raw_damage(state, chimney, 60, events, 'test', player_caused=True)
    assert not [enemy for enemy in state['combat']['enemies'] if enemy['def_id'] == 'smoke']
    _enemy_raw_damage(state, chimney, 145, events, 'test', player_caused=True)

    smokes = [enemy for enemy in state['combat']['enemies'] if enemy['def_id'] == 'smoke']
    assert len(smokes) == 2
    assert chimney['smoke_damage_progress'] == 5


def test_generator_charges_cards_in_every_player_pile():
    state, _ = _factory_combat(['generator'], 'generator-charge')
    combat = state['combat']
    cards = [_new_card(state, 'basic') for _ in range(5)]
    combat['hand'] = [cards[0]]
    combat['draw_pile'] = [cards[1]]
    combat['discard_pile'] = [cards[2]]
    combat['exile_pile'] = [cards[3]]
    combat['equipment'] = [cards[4]]
    generator = _enemy(state, 'generator')
    events = []

    _resolve_enemy_effect(
        state,
        generator,
        {'type': 'all_cards_charge', 'amount': 2},
        {'name': {'zh': '漏电', 'en': 'Leakage'}},
        'generator-charge',
        events,
    )

    assert all(card['modifiers']['charge'] == 2 for card in cards)
    assert any(event.get('type') == 'all_cards_charged' for event in events)


def test_mechanical_flower_captures_void_cards_and_recycles_weak_cards():
    state, _ = _factory_combat(['mechanical_flower'], 'mechanical-track')
    combat = state['combat']
    flower = _enemy(state, 'mechanical_flower')
    assert [card['def_id'] for card in flower['mechanical_track']] == [
        'mjolnir', 'cogwheel', 'bone',
    ]

    captured = _new_card(state, 'basic')
    captured.setdefault('modifiers', {})['force_void'] = True
    combat['exile_pile'].append(captured)
    events = []
    _notify_exiled(state, captured, events, 'mechanical-track')

    assert captured not in combat['exile_pile']
    assert flower['mechanical_track'][0] is captured
    assert captured['track_captured'] is True

    health_before = state['player']['health']
    _gain_shield(state, 7, events, source='test', enemy=flower)
    assert flower['shield'] == 7
    assert state['player']['health'] == health_before - 7

    _mechanical_flower_turn(state, flower, 'mechanical-track', events)
    assert captured not in flower['mechanical_track']
    assert [card['def_id'] for card in flower['mechanical_track']] == [
        'mjolnir', 'cogwheel', 'bone',
    ]
    assert flower['power'] >= 1
    assert any(event.get('type') == 'mechanical_track_recycled' for event in events)

    combat['hand'] = []
    combat['draw_pile'] = [_new_card(state, 'rose')]
    combat['draw_phase_complete'] = True
    _draw_cards(state, 1, 'mechanical-track-draw', events)
    assert combat['hand'][0]['modifiers']['force_void'] is True


def test_mechanical_flower_marks_normal_draw_and_captures_two_cards():
    seed = 'mechanical-track-normal-draw'
    state, _ = _factory_combat(['mechanical_flower'], seed)
    combat = state['combat']
    marked = [
        card for card in combat['hand']
        if (card.get('modifiers') or {}).get('force_void')
    ]
    assert len(combat['hand']) == 5
    assert len(marked) == 2

    marked_ids = {card['instance_id'] for card in marked}
    next_state, events = apply_story_action(state, 'end_turn', {}, seed)
    captured_ids = {
        event['card_instance_id']
        for event in events
        if event.get('type') == 'mechanical_track_captured'
    }
    assert captured_ids == marked_ids
    assert not marked_ids.intersection(
        card['instance_id'] for card in next_state['combat']['exile_pile']
    )


def test_boss_rush_boss_grants_two_complete_elite_rewards():
    seed = 'boss-rush-double-elite'
    state = build_initial_story_state(seed)
    state['journey_mode'] = 'boss_rush'
    state['difficulty'] = 'normal'
    state['map'] = generate_boss_rush_map(seed, 1, 'garden', 'normal')
    boss_node = state['map']['floors'][1]['nodes'][0]
    boss_node['status'] = 'current'
    state['current_node_id'] = boss_node['id']
    state['current_floor'] = boss_node['floor']
    state['phase'] = 'combat'
    state['combat'] = {'equipment': [], 'damage_taken': 0}
    events = []

    _finish_combat(state, seed, events)
    assert state['reward']['source'] == 'boss_rush_boss_elite'
    assert state['reward']['round_index'] == 1
    assert state['reward']['round_total'] == 2
    assert state['reward']['gold'] > 0
    assert state['reward']['cards']
    assert state['reward']['relics']

    state['reward']['claims'] = {
        'gold': True,
        'card': True,
        'relic': True,
        'enchantment_book': True,
    }
    state, _ = apply_story_action(
        state,
        'choose_reward',
        {'reward_type': 'continue'},
        seed,
    )
    assert state['reward']['source'] == 'boss_rush_boss_elite'
    assert state['reward']['round_index'] == 2

    state['reward']['claims'] = {
        'gold': True,
        'card': True,
        'relic': True,
        'enchantment_book': True,
    }
    state, _ = apply_story_action(
        state,
        'choose_reward',
        {'reward_type': 'continue'},
        seed,
    )
    assert state['phase'] == 'map'
    assert boss_node['id'] == state['map']['floors'][1]['nodes'][0]['id']
    assert state['map']['floors'][1]['nodes'][0]['status'] == 'completed'
    assert state['map']['floors'][2]['nodes'][0]['status'] == 'available'


def test_boss_rush_starting_card_rewards_cannot_be_skipped_or_left():
    seed = 'boss-rush-mandatory-cards'
    state = build_initial_story_state(seed)
    state, _ = apply_story_action(
        state,
        'start_journey',
        {'biome': 'garden', 'difficulty': 'normal', 'mode': 'boss_rush'},
        seed,
    )

    for payload in (
        {'reward_type': 'card'},
        {'reward_type': 'leave'},
    ):
        with pytest.raises(StoryActionError) as error:
            apply_story_action(state, 'choose_reward', payload, seed)
        assert error.value.code == 'CARD_REWARD_REQUIRED'
