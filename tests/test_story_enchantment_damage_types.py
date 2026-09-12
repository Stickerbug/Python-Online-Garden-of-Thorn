"""反馈 #103 / #116：附魔书的加成要覆盖派生伤害与所有护盾类型。

#103 锋利（damage_bonus）原本只并进 ``type == 'damage'``，核弹
（damage_per_elixir）、锯齿（damage_from_shield）等派生伤害完全吃不到；
#116 保护（shield_bonus_once）原本只并进 ``type == 'shield'``，蜂蜡
（shield_with_power）与冰（decaying_shield）同样吃不到。
"""

from story_content import STORY_ENCHANTMENT_BOOKS
from story_engine import (
    _card_values,
    _gain_enchantment_book,
    _new_card,
    _player_attack_effect_segment,
    _start_combat,
    apply_story_action,
)
from story_mode import build_initial_story_state

SHARP_BONUS = next(
    int(definition.get('amount') or 0)
    for definition in STORY_ENCHANTMENT_BOOKS.values()
    if definition.get('script') == 'damage_bonus'
)
PROTECTION_BONUS = next(
    int(definition.get('amount') or 0)
    for definition in STORY_ENCHANTMENT_BOOKS.values()
    if definition.get('script') == 'shield_bonus_once'
)


def _combat_state(seed, enemies=None):
    state = build_initial_story_state(seed)
    _start_combat(
        state,
        {'type': 'combat'},
        seed,
        [],
        encounter_override=enemies or [{'def_id': 'soldier_ant'}],
    )
    state['combat']['hand'] = []
    state['combat']['draw_pile'] = []
    state['combat']['discard_pile'] = []
    state['combat']['elixir'] = 99
    state['combat']['magic'] = 99
    return state


def _enchanted_card(state, card_id, book_id, seed):
    card = _new_card(state, card_id)
    state['combat']['hand'].append(card)
    book = _gain_enchantment_book(state, book_id, [], source='test')
    state, _ = apply_story_action(
        state,
        'use_enchantment_book',
        {
            'book_instance_id': book['instance_id'],
            'card_instance_id': card['instance_id'],
        },
        seed,
    )
    return state, state['combat']['hand'][-1]


def _effect(values, effect_type):
    return next(
        effect for effect in values['effects'] if effect.get('type') == effect_type
    )


def _enemy_damage_total(events):
    return sum(
        int(event.get('amount') or 0)
        for event in events
        if event.get('type') == 'enemy_damage'
    )


def test_sharp_power_applies_to_every_nuke_elixir_segment():
    """反馈 #103：核弹每消耗 1E 的一段都应该是 9+15。"""
    state = _combat_state('sharp-nuke', enemies=[{'def_id': 'chimney'}])
    state, card = _enchanted_card(state, 'nuke', 'sharp', 'sharp-nuke-use')
    enemy = state['combat']['enemies'][0]
    effect = _effect(_card_values(card), 'damage_per_elixir')

    assert _player_attack_effect_segment(
        state, effect, enemy, {'x_cost': 3}
    ) == (9 + SHARP_BONUS, 3)

    state['combat']['elixir'] = 3
    health_before = int(enemy['health'])
    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': enemy['id']},
        'sharp-nuke-play',
    )

    enemy = state['combat']['enemies'][0]
    assert _enemy_damage_total(events) == (9 + SHARP_BONUS) * 3
    assert int(enemy['health']) == health_before - (9 + SHARP_BONUS) * 3


def test_sharp_power_stays_flat_on_shield_scaled_attacks():
    """反馈 #103：锯齿按护盾层数结算，锋利加的是固定伤害而不是倍数。"""
    state = _combat_state('sharp-cutter')
    state['combat']['shield'] = 10
    state, card = _enchanted_card(state, 'cutter', 'sharp', 'sharp-cutter-use')
    enemy = state['combat']['enemies'][0]
    effect = _effect(_card_values(card), 'damage_from_shield')

    assert effect['amount'] == 1
    assert effect['bonus'] == SHARP_BONUS
    assert _player_attack_effect_segment(state, effect, enemy, {}) == (
        10 + SHARP_BONUS,
        1,
    )


def test_sharp_power_applies_to_multihit_damage_as_before():
    """回归：锋利→沙子仍然是每段 2+15、共 4 段。"""
    state = _combat_state('sharp-sand', enemies=[{'def_id': 'chimney'}])
    state, card = _enchanted_card(state, 'sand', 'sharp', 'sharp-sand-use')
    enemy = state['combat']['enemies'][0]
    effect = _effect(_card_values(card), 'damage')

    assert _player_attack_effect_segment(state, effect, enemy, {}) == (
        2 + SHARP_BONUS,
        4,
    )

    health_before = int(enemy['health'])
    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': enemy['id']},
        'sharp-sand-play',
    )

    enemy = state['combat']['enemies'][0]
    assert _enemy_damage_total(events) == (2 + SHARP_BONUS) * 4
    assert int(enemy['health']) == health_before - (2 + SHARP_BONUS) * 4


def test_sharp_power_applies_to_status_scaled_attacks():
    """反馈 #103：角骨按目标状态数结算，每段同样吃 15 点锋利。"""
    state = _combat_state('sharp-antler')
    state, card = _enchanted_card(state, 'antler', 'sharp', 'sharp-antler-use')
    enemy = state['combat']['enemies'][0]
    enemy['vulnerable'] = 3
    effect = _effect(_card_values(card), 'damage_per_status')

    assert _player_attack_effect_segment(state, effect, enemy, {}) == (
        5 + SHARP_BONUS,
        1,
    )


def test_sharp_power_applies_to_active_discard_scaled_attacks():
    """反馈 #103：魔法三叉戟的（8+本场主动弃牌）也要吃锋利。"""
    state = _combat_state('sharp-trident')
    state['combat']['active_discards_this_combat'] = 2
    state, card = _enchanted_card(
        state, 'magic_trident', 'sharp', 'sharp-trident-use'
    )
    enemy = state['combat']['enemies'][0]
    effect = _effect(_card_values(card), 'damage_per_active_discard')

    assert _player_attack_effect_segment(state, effect, enemy, {}) == (
        8 + SHARP_BONUS + 2,
        1,
    )


def test_protection_bonus_applies_to_beeswax_power_shield():
    """反馈 #116：保护→蜂蜡，9+8 之后再叠力量与耐力。"""
    state = _combat_state('protection-beeswax')
    state['combat']['power'] = 2
    state['combat']['endurance'] = 3
    state, card = _enchanted_card(
        state, 'beeswax', 'protection', 'protection-beeswax-use'
    )
    values = _card_values(card)
    effect = _effect(values, 'shield_with_power')

    assert effect['amount'] == 9 + PROTECTION_BONUS

    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id']},
        'protection-beeswax-play',
    )

    assert state['combat']['shield'] == 9 + PROTECTION_BONUS + 2 + 3


def test_protection_bonus_applies_to_decaying_ice_shield():
    """反馈 #116：保护→冰，13+8 且不影响这张牌自身的 -5 衰减。"""
    state = _combat_state('protection-ice')
    state, card = _enchanted_card(state, 'ice', 'protection', 'protection-ice-use')
    values = _card_values(card)
    effect = _effect(values, 'decaying_shield')

    assert effect['amount'] == 13 + PROTECTION_BONUS

    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id']},
        'protection-ice-play',
    )

    assert state['combat']['shield'] == 13 + PROTECTION_BONUS
    played = state['combat']['discard_pile'][-1]
    assert played['modifiers']['shield_value_delta'] == -5


def test_protection_bonus_keeps_working_for_plain_shield_cards():
    """回归：保护→叶绿体仍然是 5+8。"""
    state = _combat_state('protection-chloroplast')
    state, card = _enchanted_card(
        state, 'chloroplast', 'protection', 'protection-chloroplast-use'
    )

    effect = _effect(_card_values(card), 'shield')
    assert effect['amount'] == 5 + PROTECTION_BONUS

    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id']},
        'protection-chloroplast-play',
    )

    assert state['combat']['shield'] == 5 + PROTECTION_BONUS
