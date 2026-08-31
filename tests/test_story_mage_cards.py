from pathlib import Path

import pytest

from story_character_content import STORY_CHARACTER_CARD_DESIGNS
from story_content import (
    STORY_CARDS,
    STORY_CARD_IMAGE_URLS,
    STORY_CARD_UPGRADED_IMAGE_URLS,
    STORY_REWARD_CARD_IDS,
    STORY_SHOP_CARD_IDS,
    story_reward_card_ids,
    story_shop_card_ids,
)
from story_engine import _start_combat, apply_story_action
from story_mode import build_initial_story_state


MAGE_CARD_IDS = tuple(STORY_CHARACTER_CARD_DESIGNS)
ROOT = Path(__file__).resolve().parents[1]


def test_supplied_mage_and_neutral_card_art_is_bound_to_stable_card_ids():
    expected = {
        'capacitor', 'copper_rod', 'plasma',
        'mage_balsam', 'mage_basic', 'mage_basil', 'mage_beeswax',
        'mage_blood_blade', 'mage_blueberry', 'mage_bubble_bomb',
        'mage_capacitor', 'mage_copper_rod', 'mage_honey_shield',
        'mage_iodine', 'mage_lithium', 'mage_missile', 'mage_palm_leaf',
        'mage_quantum', 'mage_rmb', 'mage_rose', 'mage_ruby',
        'mage_shovel', 'mage_sponge', 'mage_starfish', 'mage_stick',
        'mage_sunflower', 'mage_wind',
    }
    assert expected <= STORY_CARD_IMAGE_URLS.keys()
    for card_id in expected:
        image_url = STORY_CARD_IMAGE_URLS[card_id]
        assert image_url.startswith('/static/assets/story-card-art/')
        assert (ROOT / image_url.removeprefix('/')).is_file()
        assert STORY_CARDS[card_id]['image_url'] == image_url
        assert STORY_CARDS[card_id]['upgraded_image_url']

    assert STORY_CARD_UPGRADED_IMAGE_URLS == {
        'mage_basic': '/static/assets/story-card-art/mage-basic-upgraded.svg',
    }
    assert STORY_CARDS['mage_basic']['upgraded_image_url'].endswith(
        '/mage-basic-upgraded.svg'
    )
    assert (
        ROOT
        / STORY_CARDS['mage_basic']['upgraded_image_url'].removeprefix('/')
    ).is_file()


def _combat_state(seed='mage-card-test'):
    state = build_initial_story_state(seed)
    state['player']['health'] = 9999
    state['player']['max_health'] = 9999
    events = []
    _start_combat(
        state,
        {'type': 'combat'},
        seed,
        events,
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    combat = state['combat']
    combat['opening_redraw_pending'] = False
    combat['elixir'] = 100
    combat['magic'] = 100
    combat['damage_taken_last_turn'] = 0
    combat['draw_pile'] = [
        {'instance_id': f'{seed}-draw-basic', 'def_id': 'basic', 'upgraded': False},
        {'instance_id': f'{seed}-draw-magic', 'def_id': 'mage_basic', 'upgraded': False},
    ]
    combat['discard_pile'] = [
        {'instance_id': f'{seed}-discard', 'def_id': 'rose', 'upgraded': False},
    ]
    enemy = combat['enemies'][0]
    enemy['health'] = enemy['max_health'] = 1_000_000
    enemy['static'] = 0
    return state


def _play(state, card_id, *, upgraded=False, suffix='play'):
    combat = state['combat']
    card = {
        'instance_id': f'{card_id}-{int(upgraded)}-{suffix}',
        'def_id': card_id,
        'upgraded': bool(upgraded),
    }
    filler = {
        'instance_id': f'{card_id}-{int(upgraded)}-{suffix}-filler',
        'def_id': 'basic',
        'upgraded': False,
    }
    combat['hand'] = [card, filler]
    payload = {
        'card_instance_id': card['instance_id'],
        'target_enemy_id': combat['enemies'][0]['id'],
    }
    return apply_story_action(
        state,
        'play_card',
        payload,
        f'{card_id}-{int(upgraded)}-{suffix}',
    )


def test_every_authored_mage_card_has_one_executable_source_backed_definition():
    assert len(MAGE_CARD_IDS) == 55
    assert len(set(MAGE_CARD_IDS)) == 55
    for card_id, authored in STORY_CHARACTER_CARD_DESIGNS.items():
        card = STORY_CARDS[card_id]
        assert card['owner'] == 'mage'
        assert card['name']['zh'] == authored['name']['zh']
        assert card['name']['en'] == (authored['name']['en'] or authored['name']['zh'])
        assert card['cost_e'] == authored['cost_e']
        assert card['cost_m'] == authored['cost_m']
        assert card['type'] == authored['card_type']
        assert card['rarity'] == ('primary' if authored['rarity'] == 'starter' else authored['rarity'])
        assert card['description']['zh'] == authored['base_text'].rstrip().rstrip('。.').rstrip()
        assert card['upgrade']['description']['zh'] == authored['upgrade_text'].rstrip().rstrip('。.').rstrip()


def test_character_card_pools_are_isolated_and_keep_neutral_shop_cards():
    mage_rewards = set(story_reward_card_ids('mage'))
    mage_shop = set(story_shop_card_ids('mage'))
    common_rewards = set(story_reward_card_ids('common_flower'))
    common_shop = set(story_shop_card_ids('common_flower'))

    assert mage_rewards == {
        card_id for card_id in MAGE_CARD_IDS
        if STORY_CARDS[card_id]['rarity'] != 'primary'
    }
    assert set(STORY_REWARD_CARD_IDS) == common_rewards
    assert not mage_rewards & common_rewards
    assert set(STORY_SHOP_CARD_IDS) == common_shop
    assert mage_rewards <= mage_shop
    assert any(STORY_CARDS[card_id]['owner'] == 'neutral' for card_id in mage_shop)
    assert not any(STORY_CARDS[card_id]['owner'] == 'primary' for card_id in mage_shop)


@pytest.mark.parametrize('card_id', MAGE_CARD_IDS)
@pytest.mark.parametrize('upgraded', (False, True))
def test_every_mage_card_resolves_without_an_unimplemented_effect(card_id, upgraded):
    state = _combat_state(f'mage-smoke-{card_id}-{int(upgraded)}')
    state, events = _play(state, card_id, upgraded=upgraded)
    assert state['phase'] == 'combat'
    assert any(
        event.get('type') == 'card_played' and event.get('def_id') == card_id
        for event in events
    )


def test_electric_damage_applies_then_consumes_static_authoritatively():
    state = _combat_state('mage-electric')
    combat = state['combat']
    enemy = combat['enemies'][0]
    before = enemy['health']

    state, first_events = _play(state, 'electronic_missile', suffix='first')
    enemy = state['combat']['enemies'][0]
    assert enemy['health'] == before
    assert enemy['static'] == 6
    assert any(event.get('type') == 'electric_damage' and event.get('static_applied') == 6 for event in first_events)

    state, second_events = _play(state, 'mage_electronic_missile', suffix='second')
    enemy = state['combat']['enemies'][0]
    assert enemy['static'] == 0
    assert enemy['health'] == before - 10
    assert any(event.get('type') == 'electric_damage' and event.get('amount') == 10 for event in second_events)


def test_capacitor_and_static_trigger_equipment_share_one_resolution_chain():
    state = _combat_state('mage-static-equipment')
    combat = state['combat']
    combat['equipment'] = [
        {'instance_id': 'cap', 'def_id': 'capacitor', 'upgraded': False},
        {'instance_id': 'ruby', 'def_id': 'ruby', 'upgraded': False},
        {'instance_id': 'mage-ruby', 'def_id': 'mage_ruby', 'upgraded': False},
        {'instance_id': 'mage-cap', 'def_id': 'mage_capacitor', 'upgraded': False},
        {'instance_id': 'lithium', 'def_id': 'mage_lithium', 'upgraded': False},
    ]
    combat['magic'] = 1
    combat['shield'] = 0
    enemy = combat['enemies'][0]
    before = enemy['health']

    state, _ = _play(state, 'mage_electronic_missile', suffix='prime')
    enemy = state['combat']['enemies'][0]
    assert enemy['static'] == 6

    state['combat']['magic'] = 1
    state, trigger_events = _play(state, 'mage_electronic_missile', suffix='trigger')
    combat = state['combat']
    enemy = combat['enemies'][0]
    # Lithium draws the previous Ready missile after the trigger. It resolves
    # immediately and primes the same target with a fresh six Static.
    assert enemy['static'] == 6
    assert enemy['health'] == before - 18
    assert combat['shield'] == 3
    # Mage Capacitor restores 1 M; the Ready missile drawn by Lithium spends it.
    assert combat['magic'] == 0
    electric_events = [
        event for event in trigger_events if event.get('type') == 'electric_damage'
    ]
    assert any(event.get('amount') == 10 for event in electric_events)
    assert any(event.get('static_applied') == 6 for event in electric_events)


def test_magic_and_overload_resources_are_uncapped_and_settle_at_turn_start():
    state = _combat_state('mage-resource-settlement')
    combat = state['combat']
    combat['magic'] = 250
    combat['elixir'] = 40
    combat['overload'] = 3
    combat['magic_overload'] = 5
    combat['opening_redraw_pending'] = False
    for enemy in combat['enemies']:
        enemy['stun'] = 1

    state, _ = apply_story_action(state, 'end_turn', {}, 'mage-resource-settlement-next')
    combat = state['combat']
    assert combat['overload'] == 0
    assert combat['magic_overload'] == 0
    assert combat['magic'] >= 245
    assert combat['elixir'] >= 0
    assert combat['magic'] > 10


def test_innate_mage_upgrades_are_kept_on_top_of_the_opening_draw_pile():
    state = build_initial_story_state('mage-innate')
    state['player']['deck'] = [
        {'instance_id': 'normal', 'def_id': 'basic', 'upgraded': False},
        {'instance_id': 'cotton', 'def_id': 'mage_cotton', 'upgraded': True},
        {'instance_id': 'tentacle', 'def_id': 'mage_tentacle', 'upgraded': True},
        {'instance_id': 'mage-cap', 'def_id': 'mage_capacitor', 'upgraded': True},
    ]
    events = []
    _start_combat(
        state,
        {'type': 'combat'},
        'mage-innate',
        events,
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    opening_ids = {card['def_id'] for card in state['combat']['hand']}
    assert {'mage_cotton', 'mage_tentacle', 'mage_capacitor'} <= opening_ids
