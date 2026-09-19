"""反馈 #60 / #165：残暴（brutal）重复结算不该再要一次已经用完的卡牌选择。

复现：手牌里有护身符（造成伤害 + 主动丢弃1张牌，exact），残暴遗物在攻击牌击杀
生物后再对随机敌人用一次该牌。重复结算是用空 payload 跑的，于是
``_validate_card_selections`` 把「已经用过的选择」判成没选，整次出牌被
``CARD_SELECTION_REQUIRED``（请选择1张牌）打断——玩家看到的就是「选中了牌还是
提示请选择1张牌、而且打不出去」。
"""

from story_engine import _new_card, _start_combat, apply_story_action
from story_mode import build_initial_story_state

SEED = 'feedback-60-brutal'


def _state_with_brutal_and_amulet():
    state = build_initial_story_state(SEED)
    state, _ = apply_story_action(
        state,
        'start_journey',
        {'biome': 'garden', 'difficulty': 'normal'},
        SEED,
    )
    _start_combat(
        state,
        {'type': 'combat'},
        SEED,
        [],
        encounter_override=[{'def_id': 'soldier_ant'}, {'def_id': 'soldier_ant'}],
    )
    combat = state['combat']
    combat['opening_redraw_pending'] = False
    combat['hand'] = [
        _new_card(state, 'corruption'),
        _new_card(state, 'amulet'),
        _new_card(state, 'basic'),
        _new_card(state, 'rose'),
    ]
    combat['elixir'] = 20
    combat['magic'] = 20
    combat['draw_pile'] = []
    combat['discard_pile'] = []
    combat['enemies'][0]['health'] = 5
    state['player'].setdefault('relics', []).append('brutal')
    return state


def test_brutal_repeat_keeps_the_played_card():
    state = _state_with_brutal_and_amulet()
    combat = state['combat']
    amulet = next(card for card in combat['hand'] if card['def_id'] == 'amulet')
    corruption = next(card for card in combat['hand'] if card['def_id'] == 'corruption')
    first_enemy, second_enemy = combat['enemies'][0], combat['enemies'][1]

    state, events = apply_story_action(
        state,
        'play_card',
        {
            'card_instance_id': amulet['instance_id'],
            'target_id': first_enemy['id'],
            'selected_card_ids': [corruption['instance_id']],
        },
        SEED,
    )

    enemies = {enemy['id']: int(enemy['health']) for enemy in state['combat']['enemies']}
    assert enemies[first_enemy['id']] <= 0
    assert enemies[second_enemy['id']] < int(second_enemy['health'])
    assert any(event.get('type') == 'relic_repeat' for event in events)
    assert all(card['def_id'] != 'amulet' for card in state['combat']['hand'])


def test_brutal_repeat_does_not_ask_for_the_discard_again():
    state = _state_with_brutal_and_amulet()
    combat = state['combat']
    amulet = next(card for card in combat['hand'] if card['def_id'] == 'amulet')
    corruption = next(card for card in combat['hand'] if card['def_id'] == 'corruption')

    state, _events = apply_story_action(
        state,
        'play_card',
        {
            'card_instance_id': amulet['instance_id'],
            'target_id': combat['enemies'][0]['id'],
            'selected_card_ids': [corruption['instance_id']],
        },
        SEED,
    )
    # 重复结算不再排队新的卡牌选择；主动丢弃只发生一次。
    assert state['combat'].get('pending_card_choice') in (None, {})
    assert corruption['instance_id'] not in [
        card['instance_id'] for card in state['combat']['hand']
    ]
