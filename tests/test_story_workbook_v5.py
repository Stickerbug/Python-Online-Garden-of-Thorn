import re
import zipfile
from pathlib import Path

from story_content import (
    STORY_CARDS,
    STORY_ENEMIES,
    STORY_ENEMY_IMAGE_URLS,
)
from story_engine import (
    _advance_enemy_move,
    _enemy_turn,
    _enemy_intent,
    _new_card,
    _next_enemy_move,
    _start_combat,
    _turn_boundary,
    apply_story_action,
)
from story_mode import build_initial_story_state


ROOT = Path(__file__).resolve().parents[1]


def _combat(seed, enemy_id):
    state = build_initial_story_state(seed)
    events = []
    _start_combat(
        state,
        {'type': 'combat'},
        seed,
        events,
        encounter_override=[{'def_id': enemy_id}],
    )
    return state, state['combat']['enemies'][0]


def test_latest_workbook_card_changes_are_encoded_in_card_data():
    magic_acid = STORY_CARDS['magic_acid']
    assert magic_acid['tags'] == ('exile',)
    assert magic_acid['upgrade']['tags'] == ()
    assert magic_acid['effects'][-1] == {
        'type': 'draw_selected',
        'amount': 0,
    }
    assert magic_acid['upgrade']['effects'][-1] == {
        'type': 'draw_selected',
        'amount': 0,
    }

    wind = STORY_CARDS['wind']
    assert wind['effects'][-1]['filter'] == 'zero_e'
    assert wind['effects'][-1]['amount'] == 0
    assert wind['upgrade']['effects'][-1]['filter'] == 'zero_e'
    assert wind['upgrade']['effects'][-1]['amount'] == 1


def test_wind_draws_only_cards_currently_costing_zero_elixir():
    seed = 'workbook-v5-wind'
    state, enemy = _combat(seed, 'soldier_ant')
    combat = state['combat']
    combat['opening_redraw_pending'] = False
    combat['elixir'] = 20
    enemy['health'] = enemy['max_health'] = 999

    wind = _new_card(state, 'wind')
    positive_a = _new_card(state, 'basic')
    positive_b = _new_card(state, 'rose')
    zero_a = _new_card(state, 'light')
    nonmatching = _new_card(state, 'heavy')
    zero_b = _new_card(state, 'leaf')
    combat['hand'] = [wind, positive_a, positive_b]
    combat['draw_pile'] = [zero_a, nonmatching, zero_b]
    combat['discard_pile'] = []

    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': wind['instance_id']},
        seed,
    )

    assert {card['instance_id'] for card in state['combat']['hand']} == {
        zero_a['instance_id'],
        zero_b['instance_id'],
    }
    assert state['combat']['draw_pile'] == [nonmatching]


def test_reconstructor_uses_previous_turn_waste_rule_without_repeating_itself():
    state, enemy = _combat('workbook-v5-reconstructor', 'reconstructor_enemy')
    enemy.update({
        'fragment': 0,
        'missed_factory_waste_last_turn': True,
        'last_move_index': 2,
        'move_index': 0,
    })

    move = _next_enemy_move(state, enemy)
    assert STORY_ENEMIES['reconstructor_enemy']['moves'].index(move) == 3

    _advance_enemy_move(state, enemy, 3, 'workbook-v5-reconstructor')
    enemy['missed_factory_waste_last_turn'] = True
    next_move = _next_enemy_move(state, enemy)
    assert STORY_ENEMIES['reconstructor_enemy']['moves'].index(next_move) in {0, 1, 2}


def test_reconstructor_intent_does_not_change_at_a_generic_turn_boundary():
    state, enemy = _combat('workbook-v5-reconstructor-boundary', 'reconstructor_enemy')
    enemy.update({
        'fragment': 0,
        'missed_factory_waste_last_turn': False,
        'last_move_index': 1,
        'move_index': 2,
    })

    _turn_boundary(state, 'workbook-v5-reconstructor-boundary', [], extra=True)

    assert enemy['move_index'] == 2
    assert enemy['last_move_index'] == 1
    assert enemy['missed_factory_waste_last_turn'] is False


def test_bleed_resolves_and_halves_after_the_attack_finishes():
    seed = 'workbook-v5-bleed'
    state, enemy = _combat(seed, 'soldier_ant')
    combat = state['combat']
    combat['opening_redraw_pending'] = False
    combat['elixir'] = 20
    combat['bleed'] = 5
    enemy['health'] = enemy['max_health'] = 999
    attack = _new_card(state, 'basic')
    combat['hand'] = [attack]
    combat['draw_pile'] = []
    combat['discard_pile'] = []
    health_before = int(state['player']['health'])

    state, events = apply_story_action(
        state,
        'play_card',
        {
            'card_instance_id': attack['instance_id'],
            'target_id': enemy['id'],
        },
        seed,
    )

    assert state['player']['health'] == health_before - 5
    assert state['combat']['bleed'] == 2
    relevant = [
        (event.get('type'), event.get('source'), event.get('status'))
        for event in events
        if event.get('type') in {'enemy_damage', 'player_damage', 'status_decay'}
    ]
    assert relevant[:3] == [
        ('enemy_damage', '基本', None),
        ('player_damage', 'bleed', None),
        ('status_decay', None, 'bleed'),
    ]


def test_mechanical_wasp_disc_decays_only_after_its_own_turn():
    state, enemy = _combat('workbook-v5-disc', 'mechanical_wasp')
    assert enemy['disc'] == 2

    events = []
    _turn_boundary(state, 'workbook-v5-disc:extra-player-turn', events, extra=True)
    assert enemy['disc'] == 2

    _enemy_turn(state, 'workbook-v5-disc:enemy-turn', events)
    assert enemy['disc'] == 1
    assert [
        (event['before'], event['after'])
        for event in events
        if event.get('type') == 'status_decay' and event.get('status') == 'disc'
    ] == [(2, 1)]


def test_mechanical_wasp_disc_still_decays_when_its_action_is_skipped():
    state, enemy = _combat('workbook-v5-disc-stunned', 'mechanical_wasp')
    enemy['stun'] = 1

    events = []
    _enemy_turn(state, 'workbook-v5-disc-stunned:enemy-turn', events)

    assert enemy['disc'] == 1
    assert any(
        event.get('type') == 'enemy_skipped' and event.get('enemy_id') == enemy['id']
        for event in events
    )


def test_every_enemy_intent_uses_localized_structured_information():
    for enemy_id, definition in STORY_ENEMIES.items():
        state, enemy = _combat(f'workbook-v5-intent:{enemy_id}', enemy_id)
        for move_index in range(len(definition['moves'])):
            enemy['forced_move_index'] = move_index
            intent = _enemy_intent(state, enemy)
            assert intent['entries']
            assert not re.search(r'[A-Za-z]{2,}', intent['summary']), (
                enemy_id,
                move_index,
                intent['summary'],
            )
            for entry in intent['entries']:
                if entry.get('kind') == 'special':
                    assert entry.get('label') or entry.get('effect_type') in {
                        'lose_max_health_percent',
                    }


def test_latest_monster_names_special_intents_and_reconstructor_art_are_visible():
    assert STORY_ENEMIES['termite_worker']['moves'][0]['name'] == {
        'zh': '鼓舞',
        'en': 'Inspire',
    }
    expected_move_names = {
        'stickbug': ('发射', '生长', '砸击'),
        'termite_mound': ('固守', '号令'),
        'evil_centipede': ('毒噬', '毒气', '毒爆'),
        'mechanical_crab': ('连击', '冲击', '充能', '超能光束'),
        'uranium_barrel': ('辐射', '幻光'),
        'reconstructor_enemy': ('锯片', '激光器', '碎片', '自分解', '雷神之锤'),
        'mechanical_wasp': ('组装', '改装打击', '维修', '狂暴'),
        'mechanical_missile': ('发射', '自毁'),
    }
    for enemy_id, expected in expected_move_names.items():
        assert tuple(
            move['name']['zh'] for move in STORY_ENEMIES[enemy_id]['moves']
        ) == expected

    state, overmind = _combat('workbook-v5-blockade', 'termite_overmind')
    overmind['forced_move_index'] = 0
    assert '封锁' in _enemy_intent(state, overmind)['summary']

    state, magic_firefly = _combat('workbook-v5-magic-firefly', 'magic_firefly')
    magic_firefly['forced_move_index'] = 0
    firefly_intent = _enemy_intent(state, magic_firefly)
    assert '魔力反射' in firefly_intent['summary']
    assert '魔力护盾失效' in firefly_intent['summary']

    state, cave = _combat('workbook-v5-frenzy-name', 'spider_cave')
    cave['forced_move_index'] = 1
    assert '狂暴' in _enemy_intent(state, cave)['summary']

    state, fossil = _combat('workbook-v5-charging-name', 'fossil')
    fossil['forced_move_index'] = 0
    assert '蓄力' in _enemy_intent(state, fossil)['summary']

    image_url = STORY_ENEMY_IMAGE_URLS['reconstructor_enemy']
    image_path = ROOT / 'static' / image_url.removeprefix('/static/').replace('/', '\\')
    assert image_url == '/static/assets/story-enemies/reconstructor-card.svg'
    assert image_path.is_file()
    with zipfile.ZipFile(ROOT / 'mods' / 'Factory Cards Addition.gtnmod') as package:
        assert image_path.read_bytes() == package.read('card-art/Assembler.svg')
