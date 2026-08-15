from story_content import STORY_CARDS, STORY_ENEMIES, STORY_TRAITS
from story_engine import (
    _advance_enemy_move,
    _enemy_physical_damage,
    _enemy_raw_damage,
    _is_card_playable,
    _new_card,
    _resolve_enemy_death_hooks,
    _selectable_enemy_targets,
    _start_combat,
)
from story_mode import build_initial_story_state


def _combat(seed, *enemy_ids):
    state = build_initial_story_state(seed)
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
        enemy
        for enemy in state['combat']['enemies']
        if enemy['def_id'] == def_id
    )


def test_new_psionic_terms_use_new_internal_keys_without_renaming_soul_splitter():
    assert STORY_TRAITS['psionic_connection']['name'] == {
        'zh': '灵能链接',
        'en': 'Psionic Connection',
    }
    assert STORY_TRAITS['psionic_sustain']['name'] == {
        'zh': '灵能维系',
        'en': 'Psionic Sustain',
    }
    assert STORY_TRAITS['psionic_fountain']['name'] == {
        'zh': '灵能源泉',
        'en': 'Psionic Fountain',
    }
    assert 'soul_bound' not in STORY_TRAITS
    assert 'soul_fountain' not in STORY_TRAITS
    assert STORY_CARDS['soul_splitter']['name']['zh'] == '灵魂分裂'
    assert STORY_ENEMIES['termite_overmind']['moves'][1]['name'] == {
        'zh': '灵能爆发',
        'en': 'Psionic Burst',
    }


def test_termite_resolve_moves_are_not_part_of_the_normal_cycle():
    assert STORY_ENEMIES['termite_soldier']['move_order'] == (0, 1, 2)
    assert STORY_ENEMIES['termite_overmind']['move_order'] == (0, 1)


def test_psionic_connection_splits_damage_across_connected_termites():
    state, _ = _combat('psionic-connection', 'termite_soldier', 'termite_worker')
    soldier = _enemy(state, 'termite_soldier')
    worker = _enemy(state, 'termite_worker')
    soldier['shield'] = 0
    worker['shield'] = 0
    soldier_before = soldier['health']
    worker_before = worker['health']
    events = []

    dealt = _enemy_physical_damage(
        state,
        soldier,
        9,
        1,
        events,
        'psionic-test',
    )

    assert dealt == 9
    assert soldier_before - soldier['health'] == 5
    assert worker_before - worker['health'] == 4
    assert [event['amount'] for event in events if event['type'] == 'enemy_damage'] == [5, 4]


def test_psionic_sustain_triggers_when_damage_lowers_health_to_exactly_one():
    state, _ = _combat('psionic-sustain', 'termite_soldier', 'termite_mound')
    soldier = _enemy(state, 'termite_soldier')
    soldier.update({'health': 10, 'shield': 0})
    events = []

    dealt = _enemy_physical_damage(
        state,
        soldier,
        9,
        1,
        events,
        'psionic-sustain-test',
    )

    assert dealt == 9
    assert soldier['health'] == 1
    assert soldier['stun'] == 2
    assert soldier['psionic_sustain_revive_pending'] is True
    assert any(
        event.get('type') == 'enemy_survived'
        and event.get('source') == 'psionic_sustain'
        for event in events
    )


def test_termite_mound_death_forces_each_living_termite_to_resolve():
    state, _ = _combat(
        'psionic-fountain',
        'termite_soldier',
        'termite_worker',
        'termite_overmind',
        'termite_mound',
    )
    mound = _enemy(state, 'termite_mound')
    mound['shield'] = 0
    player_before = state['player']['health']
    events = []

    _enemy_raw_damage(state, mound, mound['health'], events, 'test')
    _resolve_enemy_death_hooks(state, 'psionic-fountain', events)

    termites = [
        enemy
        for enemy in state['combat']['enemies']
        if enemy['def_id'] in {
            'termite_soldier',
            'termite_worker',
            'termite_overmind',
        }
    ]
    assert all(enemy['health'] <= 0 for enemy in termites)
    assert player_before - state['player']['health'] == 59
    assert sum(
        event.get('type') == 'enemy_action'
        and event.get('source') == 'psionic_fountain'
        for event in events
    ) == 3


def test_bulb_restricts_targets_while_obstacles_block_hand_slots():
    state, _ = _combat('jungle-targeting', 'jungle_firefly', 'termite_soldier', 'stick')
    combat = state['combat']
    firefly = _enemy(state, 'jungle_firefly')
    soldier = _enemy(state, 'termite_soldier')
    stick = _enemy(state, 'stick')

    firefly['bulb'] = 1
    assert _selectable_enemy_targets(combat, {'type': 'thorn'}) == [firefly]
    assert _selectable_enemy_targets(combat, {'type': 'bloom'}) == [firefly]

    firefly['bulb'] = 0
    assert _selectable_enemy_targets(combat, {'type': 'thorn'}) == [firefly, soldier, stick]
    assert _selectable_enemy_targets(combat, {'type': 'bloom'}) == [firefly, soldier, stick]
    assert combat['blockade'] == 1

    first = _new_card(state, 'basic')
    second = _new_card(state, 'basic')
    combat['hand'] = [first, second]
    combat['elixir'] = 99
    assert _is_card_playable(state, first) is False
    assert _is_card_playable(state, second) is True


def test_mechanical_crab_super_beam_countdown_tracks_its_four_move_cycle():
    state, _ = _combat('mechanical-crab', 'mechanical_crab')
    crab = _enemy(state, 'mechanical_crab')
    countdowns = []

    for move_index in (0, 1, 2, 3):
        _advance_enemy_move(state, crab, move_index, 'mechanical-crab')
        countdowns.append(crab['super_beam'])

    assert countdowns == [3, 2, 1, 4]
