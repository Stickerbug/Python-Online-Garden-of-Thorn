from story_content import STORY_CARDS, STORY_ENCOUNTERS, STORY_ENEMIES, STORY_TRAITS
from story_engine import (
    _advance_enemy_move,
    _encounter_specs,
    _enemy_physical_damage,
    _enemy_raw_damage,
    _is_card_playable,
    _next_enemy_move,
    _new_card,
    _resolve_enemy_death_hooks,
    _selectable_enemy_targets,
    _start_combat,
    _turn_elixir_baseline,
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


def test_bush_cycles_summon_moves_and_uses_nutrients_above_summon_cap():
    state, _ = _combat('bush-cycle', 'bush')
    combat = state['combat']
    bush = _enemy(state, 'bush')
    moves = STORY_ENEMIES['bush']['moves']

    def chosen_index(step, live_summon_ids):
        bush['move_step'] = step
        bush['last_move_index'] = None
        combat['enemies'] = [bush] + [
            {
                'id': f'fake-{summon_id}-{index}',
                'def_id': summon_id,
                'health': 1,
                'max_health': 1,
            }
            for index, summon_id in enumerate(live_summon_ids)
        ]
        move = _next_enemy_move(state, bush)
        return moves.index(move)

    # 1→抖落（召唤1只萤火虫）
    assert chosen_index(0, []) == 0
    # 2→吸引会把召唤物增加到3，因此本轮改用养分
    assert chosen_index(1, ['jungle_firefly']) == 2
    # 3→养分
    assert chosen_index(2, ['jungle_firefly']) == 2
    # 回到 1→抖落（召唤物只有1个，仍可召唤）
    assert chosen_index(3, ['jungle_firefly']) == 0
    # 已有2个召唤物时吸引会超过上限，改用养分
    assert chosen_index(4, ['jungle_firefly', 'jungle_fly']) == 2


def test_strive_grants_elixir_against_elite_bush_and_legacy_elite_combat():
    state = build_initial_story_state('strive-bush')
    state['player']['relics'].append('strive')
    state['biome'] = 'jungle'
    events = []

    _start_combat(
        state,
        {'type': 'elite'},
        'strive-bush',
        events,
        encounter_override=[{'def_id': 'bush'}],
    )

    assert state['combat']['reward_room_type'] == 'elite'
    assert state['combat']['elixir'] == state['player']['max_elixir'] + 1

    # Existing runs created before reward_room_type was persisted still infer it
    # from the active map node on later turns.
    elite_node = state['map']['floors'][0]['nodes'][0]
    elite_node['type'] = 'elite'
    state['current_node_id'] = elite_node['id']
    state['combat'].pop('reward_room_type')

    assert _turn_elixir_baseline(state) == state['player']['max_elixir'] + 1


def test_new_psionic_terms_use_new_internal_keys_without_renaming_soul_splitter():
    assert STORY_TRAITS['psionic_connection']['name']['zh'] == '灵能链接'
    assert STORY_TRAITS['psionic_connection']['name']['en'] == 'Psionic Connection'
    assert STORY_TRAITS['psionic_sustain']['name']['zh'] == '灵能绑定'
    assert STORY_TRAITS['psionic_sustain']['name']['en'] == 'Psionic Binding'
    assert STORY_TRAITS['psionic_fountain']['name']['zh'] == '灵能源泉'
    assert STORY_TRAITS['psionic_fountain']['name']['en'] == 'Psionic Fountain'
    assert 'soul_bound' not in STORY_TRAITS
    assert 'soul_fountain' not in STORY_TRAITS
    assert STORY_CARDS['soul_splitter']['name']['zh'] == '灵魂分裂'
    assert STORY_ENEMIES['termite_overmind']['moves'][1]['name']['zh'] == '灵能爆发'
    assert STORY_ENEMIES['termite_overmind']['moves'][1]['name']['en'] == 'Psionic Burst'


def test_termite_resolve_moves_are_not_part_of_the_normal_cycle():
    assert STORY_ENEMIES['termite_soldier']['move_order'] == (0, 1, 2)
    assert STORY_ENEMIES['termite_overmind']['move_order'] == (0, 1)


def _jungle_normal_draws(seed, battles):
    state = build_initial_story_state(seed)
    state['biome'] = 'jungle'
    state['stage'] = 2
    drawn = []
    for battle in range(battles):
        specs = _encounter_specs(state, 'combat', f'{seed}:{battle}')
        drawn.append(tuple(spec['def_id'] for spec in specs))
        state['stage_normal_battles'] = int(state.get('stage_normal_battles') or 0) + 1
    return drawn


def test_jungle_simple_pool_no_longer_guarantees_the_firefly_encounter():
    """反馈 #68：丛林简单怪池只有3条，旧实现把它们当轮换袋逐个抽空，
    于是每次进丛林都 100% 撞上萤火虫遭遇；改为按权重随机后应当“可能不出”。
    """

    runs = [_jungle_normal_draws(f'jungle-firefly-{index}', 3) for index in range(160)]
    firefly_runs = [
        drawn for drawn in runs
        if any('jungle_firefly' in enemy_ids for enemy_ids in drawn)
    ]

    assert 0 < len(firefly_runs) < len(runs)
    simple_ids = {
        tuple(
            entry.get('def_id') if isinstance(entry, dict) else entry
            for entry in encounter
        )
        for encounter in STORY_ENCOUNTERS['jungle']['simple']
    }
    assert all(enemy_ids in simple_ids for drawn in runs for enemy_ids in drawn)


def test_jungle_normal_encounters_do_not_repeat_back_to_back():
    drawn = _jungle_normal_draws('jungle-no-immediate-repeat', 12)

    assert drawn
    assert all(first != second for first, second in zip(drawn, drawn[1:]))


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
    assert _is_card_playable(state, first) is True
    assert _is_card_playable(state, second) is False


def test_mechanical_crab_super_beam_countdown_tracks_its_four_move_cycle():
    state, _ = _combat('mechanical-crab', 'mechanical_crab')
    crab = _enemy(state, 'mechanical_crab')
    countdowns = []

    for move_index in (0, 1, 2, 3):
        _advance_enemy_move(state, crab, move_index, 'mechanical-crab')
        countdowns.append(crab['super_beam'])

    assert countdowns == [4, 3, 2, 5]
