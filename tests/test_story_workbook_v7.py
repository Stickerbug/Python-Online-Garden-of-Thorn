from story_content import STORY_CARDS, STORY_ENEMIES, STORY_RELICS, STORY_TRAITS
from story_engine import (
    _card_values,
    _complete_current_node,
    _gain_relic,
    _is_card_playable,
    _mechanical_track_draw_rotations,
    _new_card,
    _prepare_player_turn_end,
    _start_combat,
    _turn_boundary,
)
from story_mode import (
    STORY_STAGES,
    _HARD_ROOM_WEIGHTS,
    _NORMAL_ROOM_WEIGHTS,
    build_initial_story_state,
    generate_boss_rush_map,
)


def _combat(seed='workbook-v7'):
    state = build_initial_story_state(seed)
    events = []
    _start_combat(
        state,
        {'type': 'combat'},
        seed,
        events,
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    state['combat']['opening_redraw_pending'] = False
    return state


def test_workbook_v7_card_and_relic_balance_values():
    assert STORY_CARDS['antibody']['rarity'] == 'rare'

    jelly = STORY_CARDS['jelly']
    assert jelly['tags'] == ('wide',)
    assert jelly['effects'] == (
        {'type': 'damage', 'amount': 20},
        {'type': 'delayed_player_status', 'amount': 1, 'status': 'attack_blocked'},
    )
    assert jelly['upgrade']['effects'][0]['amount'] == 24

    state = build_initial_story_state('workbook-v7-mjolnir')
    mjolnir = _new_card(state, 'mjolnir')
    assert _card_values(mjolnir)['effects'][0]['amount'] == 14
    mjolnir.update({'upgraded': True, 'upgrade_level': 1})
    assert _card_values(mjolnir)['effects'][0]['amount'] == 19
    mjolnir['upgrade_level'] = 4
    assert _card_values(mjolnir)['effects'][0]['amount'] == 34

    assert STORY_RELICS['return_to_origin']['amount'] == 1.5
    events = []
    _gain_relic(state, 'return_to_origin', 'workbook-v7-origin', events)
    basic = next(card for card in state['player']['deck'] if card['def_id'] == 'basic')
    rose = next(card for card in state['player']['deck'] if card['def_id'] == 'rose')
    assert _card_values(basic)['effects'][0]['amount'] == 9
    assert _card_values(rose)['effects'][0]['amount'] == 7

    # Existing runs stored the old 2x value on each card. Presence of the
    # modifier now opts into the current relic definition instead.
    basic['modifiers']['primary_multiplier'] = 2
    assert _card_values(basic)['effects'][0]['amount'] == 9


def test_statuses_follow_the_workbook_decay_phases():
    state = _combat('workbook-v7-statuses')
    combat = state['combat']
    combat['blockade'] = 2
    combat['attack_blocked'] = 2
    combat['weak'] = 2
    combat['vulnerable'] = 2
    combat['fragile'] = 2
    persistent_at_turn_end = {
        'evade': 2,
        'shield': 11,
        'poison': 6,
        'fire': 4,
        'stagnation': 2,
        'temporary_power': 3,
    }
    combat.update(persistent_at_turn_end)
    attack = _new_card(state, 'basic')
    skill = _new_card(state, 'rose')
    combat['hand'] = [attack, skill]

    assert _is_card_playable(state, attack) is False
    assert _is_card_playable(state, skill) is True

    _prepare_player_turn_end(state, 'workbook-v7-statuses', [])
    assert combat['blockade'] == 2
    assert combat['attack_blocked'] == 1
    assert combat['weak'] == 2
    assert combat['vulnerable'] == 2
    assert combat['fragile'] == 2
    for status, expected in persistent_at_turn_end.items():
        assert combat[status] == expected

    _turn_boundary(state, 'workbook-v7-statuses:next-turn', [])
    assert combat['blockade'] == 2
    assert combat['attack_blocked'] == 1
    assert combat['weak'] == 1
    assert combat['vulnerable'] == 1
    assert combat['fragile'] == 1


def test_mechanical_track_uses_one_bone_and_draw_count_minus_one():
    state = _combat('workbook-v7-track')
    state['combat']['hand'] = [_new_card(state, 'basic') for _ in range(7)]
    assert _mechanical_track_draw_rotations(
        state, {'type': 'draw', 'amount': 1},
    ) == 0
    assert _mechanical_track_draw_rotations(
        state, {'type': 'draw', 'amount': 4},
    ) == 3
    assert _mechanical_track_draw_rotations(
        state, {'type': 'draw_to_limit', 'amount': 0},
    ) == 2
    state['combat']['vulnerable'] = 4
    assert _mechanical_track_draw_rotations(
        state,
        {'type': 'draw_target_status', 'amount': 0, 'status': 'vulnerable'},
    ) == 3

    factory_state = build_initial_story_state('workbook-v7-track-start')
    events = []
    _start_combat(
        factory_state,
        {'type': 'boss'},
        'workbook-v7-track-start',
        events,
        encounter_override=[{'def_id': 'mechanical_flower'}],
    )
    track = factory_state['combat']['enemies'][0]['mechanical_track']
    assert [card['def_id'] for card in track] == ['mjolnir', 'cogwheel', 'bone']


def test_rat_hiding_trait_and_room_weights_match_workbook():
    assert 'hiding' in STORY_ENEMIES['mechanical_rat']['traits']
    assert STORY_TRAITS['hiding']['name']['zh'] == '躲藏'
    assert dict(_NORMAL_ROOM_WEIGHTS) == {
        'shop': 1, 'rest': 1, 'elite': 3, 'event': 3, 'combat': 6,
    }
    assert dict(_HARD_ROOM_WEIGHTS) == {
        'shop': 2, 'rest': 2, 'elite': 8, 'event': 6, 'combat': 12,
    }


def test_boss_rush_cycles_through_standard_stage_biomes():
    state = build_initial_story_state('workbook-v7-boss-rush')
    state['journey_mode'] = 'boss_rush'

    expected = (
        STORY_STAGES[1]['biomes'],
        STORY_STAGES[2]['biomes'],
        STORY_STAGES[0]['biomes'],
    )
    for stage, expected_biomes in zip((1, 2, 3), expected):
        state['stage'] = stage
        state['map'] = generate_boss_rush_map(
            'workbook-v7-boss-rush',
            stage,
            STORY_STAGES[(stage - 1) % len(STORY_STAGES)]['biomes'][0],
            'normal',
        )
        final_node = state['map']['floors'][-1]['nodes'][0]
        final_node['status'] = 'current'
        state['current_node_id'] = final_node['id']
        state['current_floor'] = final_node['floor']

        _complete_current_node(state, [])

        assert state['phase'] == 'stage_choice'
        assert tuple(state['room']['biomes']) == tuple(expected_biomes)
