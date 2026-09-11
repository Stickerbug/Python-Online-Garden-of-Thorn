import random

import pytest

from story_content import STORY_ENCHANTMENT_BOOKS, STORY_ENEMIES, STORY_RULES
from story_engine import (
    StoryActionError,
    _card_values,
    _gain_enchantment_book,
    _new_card,
    _player_physical_hit,
    _player_raw_damage,
    _resolve_enemy_effect,
    _reward_rarity,
    _start_combat,
    _turn_boundary,
    apply_story_action,
)
from story_mode import build_initial_story_state


def _combat_state(seed='enchantment-books', enemies=None):
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


def _book(state, book_id):
    events = []
    return _gain_enchantment_book(state, book_id, events, source='test')


def _hand_card(state, card_id):
    card = _new_card(state, card_id)
    state['combat']['hand'].append(card)
    return card


def test_all_workbook_enchantment_books_have_story_assets():
    assert len(STORY_ENCHANTMENT_BOOKS) == 29
    assert STORY_RULES['enchantment_book_slots'] == 3
    for definition in STORY_ENCHANTMENT_BOOKS.values():
        assert definition['rarity'] in {'common', 'rare', 'ultra'}
        assert definition['script']
        assert definition['image_url'].startswith('/static/assets/story-enchantment-books/')


def test_book_can_be_discarded_outside_combat():
    state = build_initial_story_state('discard-book')
    book = _book(state, 'sharp')
    state, events = apply_story_action(
        state,
        'discard_enchantment_book',
        {'book_instance_id': book['instance_id']},
        'discard-book',
    )
    assert state['player']['enchantment_books'] == []
    assert any(event['type'] == 'enchantment_book_removed' for event in events)


def test_book_slots_require_an_explicit_replacement():
    state = build_initial_story_state('replace-book')
    held = [_book(state, book_id) for book_id in ('sharp', 'protection', 'efficiency')]
    with pytest.raises(StoryActionError) as exc:
        _gain_enchantment_book(state, 'warp', [], source='test')
    assert exc.value.code == 'ENCHANTMENT_BOOK_SLOTS_FULL'
    gained = _gain_enchantment_book(
        state,
        'warp',
        [],
        source='test',
        replace_instance_id=held[1]['instance_id'],
    )
    assert len(state['player']['enchantment_books']) == 3
    assert gained['book_id'] == 'warp'
    assert held[1] not in state['player']['enchantment_books']


def test_sharp_and_sweeping_books_modify_and_consume():
    state = _combat_state('book-card-modifiers', enemies=[
        {'def_id': 'soldier_ant'},
        {'def_id': 'soldier_ant'},
    ])
    card = _hand_card(state, 'basic')
    sharp = _book(state, 'sharp')
    state, _ = apply_story_action(
        state,
        'use_enchantment_book',
        {'book_instance_id': sharp['instance_id'], 'card_instance_id': card['instance_id']},
        'book-card-modifiers',
    )
    card = state['combat']['hand'][0]
    base_damage = next(
        effect['amount']
        for effect in STORY_ENCHANTMENT_BOOKS.values()
        if effect['script'] == 'damage_bonus'
    )
    assert card['modifiers']['damage_bonus'] == base_damage
    assert state['player']['enchantment_books'] == []

    sweeping = _book(state, 'sweeping_blade')
    state, _ = apply_story_action(
        state,
        'use_enchantment_book',
        {'book_instance_id': sweeping['instance_id'], 'card_instance_id': card['instance_id']},
        'book-card-modifiers-wide',
    )
    values = _card_values(state['combat']['hand'][0])
    assert 'wide' in values['tags']


def test_protection_bonus_is_cleared_after_the_enchanted_card_is_used():
    state = _combat_state('book-protection')
    card = _hand_card(state, 'rose')
    book = _book(state, 'protection')
    state, _ = apply_story_action(
        state,
        'use_enchantment_book',
        {'book_instance_id': book['instance_id'], 'card_instance_id': card['instance_id']},
        'book-protection',
    )
    card = state['combat']['hand'][0]
    expected = sum(
        int(effect.get('amount') or 0)
        for effect in _card_values(card)['effects']
        if effect.get('type') == 'shield'
    )
    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id']},
        'book-protection-play',
    )
    assert state['combat']['shield'] == expected
    played = state['combat']['discard_pile'][-1]
    assert 'enchantment_shield_bonus_once' not in played.get('modifiers', {})


def test_magic_yggdrasil_auto_consumes_on_lethal_damage():
    state = _combat_state('book-yggdrasil')
    state['player']['health'] = 5
    _book(state, 'magic_yggdrasil')
    events = []
    _player_raw_damage(state, 99, events, 'test')
    assert state['player']['health'] == 5
    assert state['combat']['invincible'] == 1
    assert state['combat']['regeneration'] == 8
    assert state['player']['enchantment_books'] == []
    assert any(event['type'] == 'enchantment_book_triggered' for event in events)


def test_fall_cushioning_grants_disc_halving_on_next_use():
    state = _combat_state('book-fall-cushioning')
    state['player']['health'] = 40
    card = _hand_card(state, 'basic')
    book = _book(state, 'fall_cushioning')
    state, _ = apply_story_action(
        state,
        'use_enchantment_book',
        {'book_instance_id': book['instance_id'], 'card_instance_id': card['instance_id']},
        'book-fall-cushioning-use',
    )
    card = state['combat']['hand'][0]
    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id']},
        'book-fall-cushioning-play',
    )
    assert state['combat']['disc_active'] is True

    events = []
    _player_physical_hit(state, 9, state['combat']['enemies'][0], events, 'test')
    assert state['player']['health'] == 40 - 4
    assert state['combat']['shield'] == 0

    # 圆盘是本回合效果：回合边界后失效。
    _turn_boundary(state, 'book-fall-cushioning-boundary', events)
    assert state['combat']['disc_active'] is False
    _player_physical_hit(
        state, 9, state['combat']['enemies'][0], events, 'test-after-boundary'
    )
    assert state['player']['health'] == 40 - 4 - 9


def test_armor_break_clears_shield_before_damage_and_prediction():
    state = _combat_state('book-armor-break')
    enemy = state['combat']['enemies'][0]
    enemy['shield'] = 50
    card = _hand_card(state, 'basic')
    book = _book(state, 'armor_break')
    state, _ = apply_story_action(
        state,
        'use_enchantment_book',
        {'book_instance_id': book['instance_id'], 'card_instance_id': card['instance_id']},
        'book-armor-break-use',
    )
    card = state['combat']['hand'][0]
    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': enemy['id']},
        'book-armor-break-play',
    )
    assert any(
        event['type'] == 'status_cleared'
        and event.get('status') == 'shield'
        and event.get('source') == 'armor_break'
        for event in events
    )
    assert state['combat']['enemies'][0]['health'] < enemy['health']


def test_target_status_enchantment_applies_to_a_skill_card_self_target():
    state = _combat_state('book-self-target-status')
    card = _hand_card(state, 'rose')
    book = _book(state, 'repel')
    state, _ = apply_story_action(
        state,
        'use_enchantment_book',
        {
            'book_instance_id': book['instance_id'],
            'card_instance_id': card['instance_id'],
        },
        'book-self-target-status-use',
    )
    card = state['combat']['hand'][0]
    state, _ = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id']},
        'book-self-target-status-play',
    )
    assert state['combat']['weak'] == 4


def test_card_reward_pity_increments_and_resets():
    state = build_initial_story_state('reward-pity')
    initial = STORY_RULES['rare_card_pity_initial']
    rarity = _reward_rarity(state, 'combat', random.Random(0))
    assert rarity != 'ultra'
    assert state['rare_card_pity_offset'] == pytest.approx(initial + 0.01)
    state['rare_card_pity_offset'] = STORY_RULES['rare_card_pity_cap']
    rarity = _reward_rarity(state, 'combat', random.Random(1))
    assert rarity == 'ultra'
    assert state['rare_card_pity_offset'] == pytest.approx(initial)


def test_lunatic_card_reward_pity_uses_half_increment():
    state = build_initial_story_state('reward-pity-lunatic')
    state['difficulty'] = 'lunatic'
    _reward_rarity(state, 'combat', random.Random(0))
    assert state['rare_card_pity_offset'] == pytest.approx(
        STORY_RULES['rare_card_pity_initial'] + 0.005
    )


def _play_card_by_id(state, instance_id, seed):
    return apply_story_action(
        state,
        'play_card',
        {'card_instance_id': instance_id},
        seed,
    )


def _find_card(state, instance_id):
    for pile in ('discard_pile', 'draw_pile', 'exile_pile', 'hand', 'equipment'):
        for card in state['combat'].get(pile) or []:
            if card.get('instance_id') == instance_id:
                return pile, card
    return None, None


def test_sharp_power_is_consumed_when_the_enchanted_card_is_played():
    """反馈 #52：锋利给的威力属于卡牌威力，打出后应清除。"""
    state = _combat_state('book-sharp-once')
    card = _hand_card(state, 'basic')
    base_damage = next(
        effect['amount']
        for effect in _card_values(card)['effects']
        if effect['type'] == 'damage'
    )
    book = _book(state, 'sharp')
    state, _ = apply_story_action(
        state,
        'use_enchantment_book',
        {
            'book_instance_id': book['instance_id'],
            'card_instance_id': card['instance_id'],
        },
        'book-sharp-once-use',
    )
    card = state['combat']['hand'][0]
    assert card['modifiers']['damage_bonus'] == 15
    assert card['modifiers']['enchantment_labels'] == {'damage_bonus': 'sharp'}
    assert (
        next(
            effect['amount']
            for effect in _card_values(card)['effects']
            if effect['type'] == 'damage'
        )
        == base_damage + 15
    )

    state, _ = _play_card_by_id(
        state, card['instance_id'], 'book-sharp-once-play'
    )

    pile, played = _find_card(state, card['instance_id'])
    assert pile == 'discard_pile'
    assert 'damage_bonus' not in (played.get('modifiers') or {})
    assert 'enchantment_power' not in (played.get('modifiers') or {})
    assert 'enchantment_labels' not in (played.get('modifiers') or {})


def test_stacked_power_books_are_all_consumed_after_the_card_is_played():
    """锋利 + 致密叠在同一张牌上时，两份附魔威力都要清除。"""
    state = _combat_state('book-stacked-power')
    card = _hand_card(state, 'basic')
    for book_id, seed in (('sharp', 'stack-sharp'), ('dense', 'stack-dense')):
        book = _book(state, book_id)
        state, _ = apply_story_action(
            state,
            'use_enchantment_book',
            {
                'book_instance_id': book['instance_id'],
                'card_instance_id': card['instance_id'],
            },
            seed,
        )
    card = state['combat']['hand'][0]
    assert card['modifiers']['damage_bonus'] == 45
    assert card['modifiers']['enchantment_power'] == 45

    state, _ = _play_card_by_id(state, card['instance_id'], 'stack-play')

    _, played = _find_card(state, card['instance_id'])
    assert 'damage_bonus' not in (played.get('modifiers') or {})
    assert 'enchantment_power' not in (played.get('modifiers') or {})


def test_combat_scoped_books_survive_the_enchanted_card_play():
    """非一次性附魔（本场战斗）不受 #52 修复影响。"""
    state = _combat_state('book-efficiency-keeps')
    card = _hand_card(state, 'basic')
    book = _book(state, 'efficiency')
    state, _ = apply_story_action(
        state,
        'use_enchantment_book',
        {
            'book_instance_id': book['instance_id'],
            'card_instance_id': card['instance_id'],
        },
        'book-efficiency-keeps-use',
    )
    card = state['combat']['hand'][0]
    state, _ = _play_card_by_id(
        state, card['instance_id'], 'book-efficiency-keeps-play'
    )
    _, played = _find_card(state, card['instance_id'])
    assert played['modifiers']['swift'] == 1
    assert played['modifiers']['enchantment_labels'] == {'swift': 'efficiency'}


def test_permanent_card_growth_survives_enchanted_power_consumption():
    """竹子这类「永久获得伤害」不能被附魔威力清除逻辑带走。"""
    state = _combat_state('book-sharp-bamboo')
    card = _hand_card(state, 'bamboo')
    book = _book(state, 'sharp')
    state, _ = apply_story_action(
        state,
        'use_enchantment_book',
        {
            'book_instance_id': book['instance_id'],
            'card_instance_id': card['instance_id'],
        },
        'book-sharp-bamboo-use',
    )
    card = state['combat']['hand'][0]
    assert card['modifiers']['damage_bonus'] == 15

    state, _ = _play_card_by_id(
        state, card['instance_id'], 'book-sharp-bamboo-play'
    )

    _, played = _find_card(state, card['instance_id'])
    assert played['modifiers']['damage_bonus'] == 3


def test_magic_yggdrasil_guards_lethal_self_inflicted_health_loss():
    """反馈 #74：附魔书里有 ygg 时，自伤致命也必须触发保护。"""
    state = _combat_state('book-yggdrasil-self-loss')
    state['player']['health'] = 3
    _book(state, 'magic_yggdrasil')
    exiled = _new_card(state, 'basic')
    state['combat']['exile_pile'].append(exiled)
    card = _hand_card(state, 'redemption_money')

    state, events = apply_story_action(
        state,
        'play_card',
        {
            'card_instance_id': card['instance_id'],
            'selected_exile_ids': [exiled['instance_id']],
        },
        'book-yggdrasil-self-loss-play',
    )

    assert state['player']['health'] == 3
    assert state.get('phase') == 'combat'
    assert state['player']['enchantment_books'] == []
    assert any(
        event['type'] == 'enchantment_book_triggered' for event in events
    )


def test_magic_yggdrasil_guards_the_reported_chimney_sequence():
    """反馈 #74 原始场景：24H/51 护盾/56 伤害/60 毒/附魔书含 ygg。"""
    state = _combat_state(
        'book-yggdrasil-chimney',
        enemies=[{'def_id': 'chimney'}, {'def_id': 'smoke'}],
    )
    _book(state, 'magic_yggdrasil')
    state['player']['health'] = 24
    state['combat']['shield'] = 51
    state['combat']['poison'] = 60
    state['combat']['toxic_poison'] = 40
    chimney = next(
        enemy for enemy in state['combat']['enemies']
        if enemy['def_id'] == 'chimney'
    )
    combustion = STORY_ENEMIES['chimney']['moves'][1]
    events = []
    for effect in combustion['effects']:
        _resolve_enemy_effect(
            state, chimney, effect, combustion, 'book-yggdrasil-chimney', events
        )

    # 助燃 = 16 + 40 层剧毒 = 56 伤害，51 护盾挡下 51，实际掉 5H。
    assert state['player']['health'] == 19
    assert state['combat']['shield'] == 0
    events = []
    _turn_boundary(state, 'book-yggdrasil-chimney', events, extra=False)

    assert any(
        event['type'] == 'enchantment_book_triggered' for event in events
    )
    assert state['player']['health'] > 0
    assert state.get('phase') == 'combat'
    assert state['player']['enchantment_books'] == []
