from story_content import STORY_ENEMIES, STORY_RELICS
from story_mode import _HARD_ROOM_WEIGHTS, _NORMAL_ROOM_WEIGHTS
from title_shop_catalog import TITLE_SHOP_CATALOG


def test_data9_room_and_talent_rarity_weights_are_frozen():
    assert dict(_NORMAL_ROOM_WEIGHTS) == {
        'shop': 1,
        'rest': 1,
        'elite': 4,
        'event': 4,
        'combat': 6,
    }
    assert dict(_HARD_ROOM_WEIGHTS) == {
        'shop': 2,
        'rest': 2,
        'elite': 9,
        'event': 6,
        'combat': 12,
    }
    assert all(definition.get('stackable') is True for definition in STORY_RELICS.values())


def test_data9_shark_and_shell_use_two_large_hits():
    shark_bite = STORY_ENEMIES['shark']['moves'][1]['effects'][0]
    assert shark_bite == {
        'type': 'damage',
        'amount': 7,
        'hits': 2,
        'lunatic_amount': 8,
    }

    shell_effects = STORY_ENEMIES['ocean_shell']['moves'][1]['effects']
    assert shell_effects[0] == {
        'type': 'damage',
        'amount': 7,
        'hits': 2,
        'lunatic_amount': 8,
    }
    assert shell_effects[1] == {
        'type': 'gain_power',
        'amount': 2,
        'lunatic_amount': 3,
    }
    assert shell_effects[2] == {
        'type': 'consume_pearls_damage',
        'amount': 7,
        'lunatic_amount': 8,
    }


def test_data9_dealer_title_is_in_the_builtin_catalog():
    dealer = next(item for item in TITLE_SHOP_CATALOG if item['id'] == 'shop:dealer')
    assert dealer == {
        'id': 'shop:dealer',
        'name': '发牌员',
        'price': 40000,
        'weight': 20,
        'style': '{color:#000000}发牌员{/}',
    }
